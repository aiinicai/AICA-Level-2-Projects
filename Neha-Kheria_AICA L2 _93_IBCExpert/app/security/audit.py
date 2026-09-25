"""Tamper-evident append-only audit chain."""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.errors import IntegrityError
from app.core.time import Clock, SystemClock, to_utc_iso
from app.db.connection import transaction

GENESIS_HASH = "0" * 64


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _entry_hash(key: bytes, entry: dict[str, Any]) -> str:
    return hmac.new(key, _canonical(entry).encode("utf-8"), hashlib.sha256).hexdigest()


@dataclass
class AuditService:
    connection: sqlite3.Connection
    audit_key: bytes
    clock: Clock = SystemClock()

    def __post_init__(self) -> None:
        if len(self.audit_key) != 32:
            raise ValueError("audit key must contain 32 bytes")

    def append(
        self,
        event_type: str,
        summary: str,
        *,
        entity_type: str | None = None,
        entity_id: str | int | None = None,
        user_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> int:
        if not event_type or not summary:
            raise ValueError("event_type and summary are required")
        with transaction(self.connection):
            previous = self.connection.execute(
                "SELECT entry_hash FROM audit_entries ORDER BY id DESC LIMIT 1"
            ).fetchone()
            previous_hash = previous[0] if previous else GENESIS_HASH
            base = {
                "event_uuid": str(uuid.uuid4()),
                "occurred_at": to_utc_iso(self.clock.now()),
                "user_id": user_id,
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": None if entity_id is None else str(entity_id),
                "summary": summary,
                "details_json": _canonical(details or {}),
                "previous_hash": previous_hash,
            }
            digest = _entry_hash(self.audit_key, base)
            cursor = self.connection.execute(
                """
                INSERT INTO audit_entries(
                    event_uuid,occurred_at,user_id,event_type,entity_type,entity_id,
                    summary,details_json,previous_hash,entry_hash
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    base["event_uuid"], base["occurred_at"], base["user_id"],
                    base["event_type"], base["entity_type"], base["entity_id"],
                    base["summary"], base["details_json"], base["previous_hash"], digest,
                ),
            )
            return int(cursor.lastrowid)

    def verify(self) -> tuple[bool, int | None]:
        previous_hash = GENESIS_HASH
        rows = self.connection.execute("SELECT * FROM audit_entries ORDER BY id").fetchall()
        for row in rows:
            if row["previous_hash"] != previous_hash:
                return False, int(row["id"])
            base = {
                "event_uuid": row["event_uuid"],
                "occurred_at": row["occurred_at"],
                "user_id": row["user_id"],
                "event_type": row["event_type"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "summary": row["summary"],
                "details_json": row["details_json"],
                "previous_hash": row["previous_hash"],
            }
            calculated = _entry_hash(self.audit_key, base)
            if not hmac.compare_digest(calculated, row["entry_hash"]):
                return False, int(row["id"])
            previous_hash = row["entry_hash"]
        return True, None

    def assert_valid(self) -> None:
        valid, broken_at = self.verify()
        if not valid:
            raise IntegrityError(f"Audit log integrity failed at entry {broken_at}.")
