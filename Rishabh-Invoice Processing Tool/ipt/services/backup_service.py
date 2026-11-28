"""Backups: the database (SQLite online-backup API, consistent while IPT runs) plus the company document
folders, in one ZIP. Verify = checksum + SQLite integrity check of the database inside the ZIP.

Restore never overwrites the open database: the backup is verified, a safety backup of the current data is
made, the files are staged in RestorePending/, and the swap happens the next time IPT starts
(apply_pending_restore, called before the database is opened).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from ipt.core import permissions as perms
from ipt.core.context import AppContext
from ipt.db.base import Database
from ipt.db.models import Backup
from ipt.services import audit_service

PENDING = "RestorePending"
MARKER = "restore.json"
SCHEDULES = {"off": None, "daily": timedelta(days=1), "weekly": timedelta(days=7)}


class BackupError(Exception):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def integrity_ok(db_file: Path) -> tuple[bool, str]:
    try:
        con = sqlite3.connect(str(db_file))
        try:
            res = con.execute("PRAGMA integrity_check").fetchone()[0]
            tables = con.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            ver = con.execute("SELECT version FROM schema_version WHERE id=1").fetchone()
        finally:
            con.close()
    except sqlite3.Error as e:
        return False, f"Not a readable IPT database: {e}"
    if res != "ok":
        return False, f"Integrity check failed: {res}"
    return True, f"Integrity check ok · {tables} tables · schema version {ver[0] if ver else '?'}"


def apply_pending_restore(data_root: Path) -> str | None:
    """Called at start-up before the database is opened. Swaps in a staged restore. Returns a message."""
    pending = data_root / PENDING
    marker = pending / MARKER
    if not marker.exists():
        return None
    info = json.loads(marker.read_text(encoding="utf-8"))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    keep = data_root / "Backups" / f"replaced_by_restore_{stamp}"
    keep.mkdir(parents=True, exist_ok=True)
    db = data_root / "ipt.db"
    for suffix in ("", "-wal", "-shm"):
        f = data_root / f"ipt.db{suffix}"
        if f.exists():
            shutil.move(str(f), str(keep / f.name))
    shutil.move(str(pending / "ipt.db"), str(db))
    if (pending / "Companies").exists():
        if (data_root / "Companies").exists():
            shutil.move(str(data_root / "Companies"), str(keep / "Companies"))
        shutil.move(str(pending / "Companies"), str(data_root / "Companies"))
    shutil.rmtree(pending, ignore_errors=True)
    return (f"Data restored from the backup made on {info.get('created', '?')}. "
            f"The data it replaced is kept in {keep}.")


class BackupService:
    def __init__(self, db: Database, data_root: Path, ctx: AppContext, settings=None):
        self.db, self.data_root, self.ctx, self.settings = db, data_root, ctx, settings

    def folder(self) -> Path:
        custom = self.settings.get("backup_folder", "") if self.settings else ""
        p = Path(custom) if custom else self.data_root / "Backups"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _user(self) -> str:
        return self.ctx.user.username if self.ctx.user else "system"

    # ---------------------------------------------------------------- create
    def create(self, kind: str = "manual", progress=None) -> Backup:
        if kind == "manual":
            perms.require(self.ctx.user.role if self.ctx.user else None, "backup.run")
        src = self.db.file_path()
        if src is None or not src.exists():
            raise BackupError("The database file was not found")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = self.folder() / f"IPT_backup_{stamp}_{kind}.zip"
        with tempfile.TemporaryDirectory() as tmp:
            snap = Path(tmp) / "ipt.db"
            if progress:
                progress("Copying the database")
            live, out = sqlite3.connect(str(src)), sqlite3.connect(str(snap))
            try:
                live.backup(out)            # consistent copy even while IPT is writing
            finally:                        # 'with sqlite3.connect' does not close; Windows keeps the file locked
                out.close()
                live.close()
            ok, msg = integrity_ok(snap)
            if not ok:
                raise BackupError("The current database failed its integrity check – backup not made: " + msg)
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(snap, "ipt.db")
                z.writestr("backup.json", json.dumps({"created": datetime.now().isoformat(timespec="seconds"),
                                                      "kind": kind, "by": self._user(), "app": "IPT"}))
                companies = self.data_root / "Companies"
                if companies.exists():
                    if progress:
                        progress("Adding company documents")
                    for f in companies.rglob("*"):
                        if f.is_file():
                            z.write(f, str(Path("Companies") / f.relative_to(companies)))
        b = Backup(path=str(target), kind=kind, size_bytes=target.stat().st_size, sha256=_sha256(target),
                   created_by=self._user())
        with self.db.session() as s:
            s.add(b)
            s.flush()
            audit_service.record(s, self.ctx.user, "backup.create", "backup", b.id,
                                 after={"file": target.name, "kind": kind, "size": b.size_bytes})
        self.verify(b.id)
        self._prune()
        return self.get(b.id)

    def _prune(self) -> None:
        keep = int(self.settings.get("backup_keep", "10")) if self.settings else 10
        with self.db.session() as s:
            auto = list(s.scalars(select(Backup).where(Backup.kind == "scheduled").order_by(Backup.id.desc())))
            for b in auto[keep:]:
                Path(b.path).unlink(missing_ok=True)
                s.delete(b)

    # ---------------------------------------------------------------- list / verify
    def list(self) -> list[Backup]:
        with self.db.session() as s:
            return list(s.scalars(select(Backup).order_by(Backup.id.desc())))

    def get(self, backup_id: int) -> Backup | None:
        with self.db.session() as s:
            return s.get(Backup, backup_id)

    def verify(self, backup_id: int) -> tuple[bool, str]:
        b = self.get(backup_id)
        if b is None:
            raise BackupError("Backup not found")
        p = Path(b.path)
        if not p.exists():
            ok, msg = False, "The backup file is missing"
        elif _sha256(p) != b.sha256:
            ok, msg = False, "The file has changed since it was made (checksum differs)"
        else:
            ok, msg = self._check_zip(p)
        with self.db.session() as s:
            row = s.get(Backup, backup_id)
            row.verified, row.verify_message = ok, msg
        return ok, msg

    @staticmethod
    def _check_zip(p: Path) -> tuple[bool, str]:
        try:
            with zipfile.ZipFile(p) as z:
                bad = z.testzip()
                if bad:
                    return False, f"Damaged file inside the backup: {bad}"
                if "ipt.db" not in z.namelist():
                    return False, "No database inside this ZIP"
                with tempfile.TemporaryDirectory() as tmp:
                    z.extract("ipt.db", tmp)
                    ok, msg = integrity_ok(Path(tmp) / "ipt.db")
                docs = sum(1 for n in z.namelist() if n.startswith("Companies/"))
                return ok, f"{msg} · {docs} document file(s)"
        except zipfile.BadZipFile:
            return False, "Not a valid ZIP file"

    # ---------------------------------------------------------------- restore
    def stage_restore(self, zip_path: Path) -> str:
        """Verify a backup ZIP (from the list or any folder), make a safety backup of the current data and stage
        the restore for the next start. Admin only; the UI asks for confirmation first."""
        perms.require(self.ctx.user.role if self.ctx.user else None, "backup.restore")
        zip_path = Path(zip_path)
        ok, msg = self._check_zip(zip_path)
        if not ok:
            raise BackupError(f"This backup cannot be restored: {msg}")
        safety = self.create("pre-restore")
        pending = self.data_root / PENDING
        shutil.rmtree(pending, ignore_errors=True)
        pending.mkdir(parents=True)
        with zipfile.ZipFile(zip_path) as z:
            meta = json.loads(z.read("backup.json")) if "backup.json" in z.namelist() else {}
            for name in z.namelist():
                if name == "ipt.db" or name.startswith("Companies/"):
                    target = (pending / name).resolve()
                    if pending.resolve() not in target.parents:     # never write outside the staging folder
                        raise BackupError(f"Unsafe path in backup: {name}")
                    z.extract(name, pending)
        (pending / MARKER).write_text(json.dumps({"from": str(zip_path), "created": meta.get("created", "?"),
                                                  "safety_backup": safety.path}), encoding="utf-8")
        with self.db.session() as s:
            audit_service.record(s, self.ctx.user, "backup.restore_staged", "backup", safety.id,
                                 after={"from": str(zip_path), "safety_backup": safety.path})
        return safety.path

    # ---------------------------------------------------------------- schedule
    def due(self) -> bool:
        if self.settings is None:
            return False
        every = SCHEDULES.get(self.settings.get("backup_schedule", "weekly"))
        if every is None:
            return False
        last = next((b for b in self.list() if b.kind in ("scheduled", "manual")), None)
        return last is None or datetime.now() - _local(last.created_at) >= every


def _local(dt: datetime) -> datetime:
    from ipt.core.timefmt import local
    return local(dt) or datetime.min
