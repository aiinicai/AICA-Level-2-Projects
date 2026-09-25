"""Scheduled encrypted local backup policy and retention controller.

The scheduler is deliberately local-only. It never uses OS/cloud backup services and never
initiates network traffic. Because the encrypted backup key is derived from the authenticated
master key, automatic backups run only while the application is actively being used by an
authenticated user. A due check is therefore performed on normal authenticated requests.
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path

from app.core.time import Clock, SystemClock, from_utc_iso, to_utc_iso
from app.db.connection import transaction
from app.services.backup import BackupService

_SETTING_KEY = "backup_schedule"
_RUN_LOCK = threading.Lock()


@dataclass(frozen=True)
class BackupPolicy:
    enabled: bool = True
    interval_days: int = 1
    retention: int = 20
    last_run_at: str | None = None
    next_due_at: str | None = None
    last_attempt_at: str | None = None
    last_error: str | None = None

    def validated(self) -> "BackupPolicy":
        if not 1 <= int(self.interval_days) <= 30:
            raise ValueError("Backup interval must be between 1 and 30 days.")
        if not 1 <= int(self.retention) <= 100:
            raise ValueError("Scheduled backup retention must be between 1 and 100 backups.")
        for value in (self.last_run_at, self.next_due_at, self.last_attempt_at):
            if value:
                from_utc_iso(value)
        return self


class BackupScheduleService:
    def __init__(self, connection, backup_service: BackupService, *, clock: Clock | None = None) -> None:
        self.connection = connection
        self.backup_service = backup_service
        self.clock = clock or SystemClock()

    def get_policy(self, *, default_retention: int = 20) -> BackupPolicy:
        row = self.connection.execute("SELECT value_json FROM settings WHERE key=?", (_SETTING_KEY,)).fetchone()
        if row is None:
            return BackupPolicy(retention=max(1, min(100, int(default_retention)))).validated()
        try:
            raw = json.loads(row["value_json"])
            policy = BackupPolicy(
                enabled=bool(raw.get("enabled", True)),
                interval_days=int(raw.get("interval_days", 1)),
                retention=int(raw.get("retention", default_retention)),
                last_run_at=raw.get("last_run_at"),
                next_due_at=raw.get("next_due_at"),
                last_attempt_at=raw.get("last_attempt_at"),
                last_error=raw.get("last_error"),
            )
            return policy.validated()
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Stored backup schedule settings are invalid.") from exc

    def _save(self, policy: BackupPolicy) -> None:
        policy = policy.validated()
        now = to_utc_iso(self.clock.now())
        value = json.dumps(asdict(policy), separators=(",", ":"), sort_keys=True)
        with transaction(self.connection):
            self.connection.execute(
                """INSERT INTO settings(key,value_json,is_sensitive,updated_at) VALUES(?,?,0,?)
                   ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at""",
                (_SETTING_KEY, value, now),
            )

    def update_policy(self, *, enabled: bool, interval_days: int, retention: int, default_retention: int = 20) -> BackupPolicy:
        current = self.get_policy(default_retention=default_retention)
        now = self.clock.now()
        policy = BackupPolicy(
            enabled=bool(enabled),
            interval_days=int(interval_days),
            retention=int(retention),
            last_run_at=current.last_run_at,
            next_due_at=(
                to_utc_iso(now + timedelta(days=int(interval_days)))
                if enabled and current.last_run_at is None
                else (
                    to_utc_iso(from_utc_iso(current.last_run_at) + timedelta(days=int(interval_days)))
                    if enabled and current.last_run_at
                    else None
                )
            ),
            last_attempt_at=current.last_attempt_at,
            last_error=current.last_error,
        ).validated()
        self._save(policy)
        return policy

    def is_due(self, policy: BackupPolicy) -> bool:
        if not policy.enabled:
            return False
        now = self.clock.now()
        if policy.last_attempt_at and policy.last_error:
            # Avoid retrying a failed large backup on every page request. Retry after one hour.
            if now - from_utc_iso(policy.last_attempt_at) < timedelta(hours=1):
                return False
        if not policy.last_run_at:
            return now >= from_utc_iso(policy.next_due_at) if policy.next_due_at else True
        due = from_utc_iso(policy.next_due_at) if policy.next_due_at else from_utc_iso(policy.last_run_at) + timedelta(days=policy.interval_days)
        return now >= due

    def run_now(self, *, default_retention: int = 20) -> dict:
        policy = self.get_policy(default_retention=default_retention)
        return self._run(policy, force=True)

    def run_if_due(self, *, default_retention: int = 20) -> dict:
        exists = self.connection.execute("SELECT 1 FROM settings WHERE key=?", (_SETTING_KEY,)).fetchone() is not None
        if not exists:
            policy = self.update_policy(
                enabled=True, interval_days=1, retention=default_retention, default_retention=default_retention
            )
            return {"ran": False, "reason": "schedule_initialized", "policy": policy}
        policy = self.get_policy(default_retention=default_retention)
        if not self.is_due(policy):
            return {"ran": False, "reason": "not_due", "policy": policy}
        if not _RUN_LOCK.acquire(blocking=False):
            return {"ran": False, "reason": "already_running", "policy": policy}
        try:
            # Re-read after lock in case another request completed the backup.
            policy = self.get_policy(default_retention=default_retention)
            if not self.is_due(policy):
                return {"ran": False, "reason": "not_due", "policy": policy}
            return self._run(policy, force=False)
        finally:
            _RUN_LOCK.release()

    def _run(self, policy: BackupPolicy, *, force: bool) -> dict:
        now = self.clock.now()
        attempt = to_utc_iso(now)
        in_progress = BackupPolicy(
            enabled=policy.enabled,
            interval_days=policy.interval_days,
            retention=policy.retention,
            last_run_at=policy.last_run_at,
            next_due_at=policy.next_due_at,
            last_attempt_at=attempt,
            last_error=None,
        )
        self._save(in_progress)
        try:
            path = self.backup_service.create(label="Automatic scheduled local backup", backup_type="SCHEDULED")
            completed = self.clock.now()
            final = BackupPolicy(
                enabled=policy.enabled,
                interval_days=policy.interval_days,
                retention=policy.retention,
                last_run_at=to_utc_iso(completed),
                next_due_at=to_utc_iso(completed + timedelta(days=policy.interval_days)) if policy.enabled else None,
                last_attempt_at=attempt,
                last_error=None,
            )
            self._save(final)
            deleted = self.apply_retention(policy.retention)
            self.backup_service.audit.append(
                "SCHEDULED_BACKUP_COMPLETED",
                "Completed scheduled encrypted local backup.",
                entity_type="backup",
                details={"path_name": path.name, "retention_deleted": deleted, "forced": force},
            )
            return {"ran": True, "path": path, "deleted": deleted, "policy": final}
        except Exception as exc:
            failed = BackupPolicy(
                enabled=policy.enabled,
                interval_days=policy.interval_days,
                retention=policy.retention,
                last_run_at=policy.last_run_at,
                next_due_at=policy.next_due_at,
                last_attempt_at=attempt,
                last_error=str(exc)[:500],
            )
            self._save(failed)
            raise

    def apply_retention(self, retention: int | None = None) -> int:
        policy = self.get_policy()
        keep = int(retention if retention is not None else policy.retention)
        if not 1 <= keep <= 100:
            raise ValueError("Scheduled backup retention must be between 1 and 100 backups.")
        rows = self.connection.execute(
            """SELECT id,path FROM backups
               WHERE backup_type='SCHEDULED' AND status IN ('VALID','RESTORED')
               ORDER BY created_at DESC, id DESC"""
        ).fetchall()
        deleted = 0
        backup_root = self.backup_service.backup_root.resolve()
        for row in rows[keep:]:
            path = Path(row["path"]).expanduser().resolve()
            try:
                path.relative_to(backup_root)
            except ValueError:
                # Never delete a path outside the application-owned backup directory.
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError:
                continue
            with transaction(self.connection):
                self.connection.execute("UPDATE backups SET status='DELETED' WHERE id=?", (row["id"],))
            deleted += 1
        if deleted:
            self.backup_service.audit.append(
                "BACKUP_RETENTION_APPLIED",
                "Applied scheduled local backup retention policy.",
                entity_type="backup",
                details={"retained": keep, "deleted": deleted},
            )
        return deleted
