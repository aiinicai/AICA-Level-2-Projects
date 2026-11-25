"""Encrypted backups of the database and the uploaded files, and restore.

Backup file (``cff_backup_YYYYMMDD-HHMMSS.cffbak``):
    b"CFFBAK1\\n" + 16-byte salt + Fernet token
The token encrypts a ZIP holding ``cashflow.db`` (a consistent copy made with SQLite's backup API,
safe while the app is running), the ``uploads/`` folder and ``manifest.json`` (SHA-256 of every file).
The key is derived from the backup passphrase (CFF_BACKUP_PASSPHRASE, or instance/backup.key) with
scrypt. Fernet = AES-128-CBC + HMAC-SHA256, so a changed or damaged file is detected, not restored.

Keep a copy of the passphrase away from the server: without it a backup cannot be opened.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from app import __version__
from app.core.config import Settings, get_settings

MAGIC = b"CFFBAK1\n"
SUFFIX = ".cffbak"


class BackupError(RuntimeError):
    pass


@dataclass
class BackupInfo:
    path: Path
    created: datetime
    size: int


def _key(passphrase: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=2 ** 15, r=8, p=1)
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def create_backup(s: Settings | None = None, note: str = "") -> Path:
    """Write an encrypted backup to the backups folder (and the copy folder, if set). Returns its path."""
    s = s or get_settings()
    s.backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    with tempfile.TemporaryDirectory() as tmp:
        db_copy = Path(tmp) / "cashflow.db"
        src = sqlite3.connect(s.database_path)
        dst = sqlite3.connect(db_copy)
        try:
            src.backup(dst)                                  # consistent copy, even while the app runs
        finally:
            dst.close()
            src.close()
        files: dict[str, bytes] = {"cashflow.db": db_copy.read_bytes()}
        if s.uploads_dir.exists():
            for p in sorted(s.uploads_dir.rglob("*")):
                if p.is_file():
                    files["uploads/" + p.relative_to(s.uploads_dir).as_posix()] = p.read_bytes()
    manifest = {"app_version": __version__, "created": datetime.now().isoformat(timespec="seconds"),
                "note": note, "files": {k: _sha(v) for k, v in files.items()}}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
        z.writestr("manifest.json", json.dumps(manifest, indent=1))
    salt = os.urandom(16)
    token = Fernet(_key(s.backup_passphrase, salt)).encrypt(buf.getvalue())
    out, n = s.backups_dir / f"cff_backup_{stamp}{SUFFIX}", 1
    while out.exists():                                      # two backups in the same second
        n += 1
        out = s.backups_dir / f"cff_backup_{stamp}-{n}{SUFFIX}"
    tmp_out = out.with_suffix(".part")
    tmp_out.write_bytes(MAGIC + salt + token)
    tmp_out.replace(out)
    if s.backup_copy_dir:
        try:
            s.backup_copy_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(out, s.backup_copy_dir / out.name)
        except OSError as exc:
            raise BackupError(f"Backup saved in {out}, but the copy to {s.backup_copy_dir} failed: {exc}")
    prune(s)
    return out


def prune(s: Settings | None = None) -> int:
    """Keep the newest ``backup_keep`` backups in the backups folder; delete older ones."""
    s = s or get_settings()
    old = list_backups(s)[s.backup_keep:]
    for b in old:
        b.path.unlink(missing_ok=True)
    return len(old)


def list_backups(s: Settings | None = None) -> list[BackupInfo]:
    s = s or get_settings()
    if not s.backups_dir.exists():
        return []
    out = [BackupInfo(p, datetime.fromtimestamp(p.stat().st_mtime), p.stat().st_size)
           for p in s.backups_dir.glob(f"cff_backup_*{SUFFIX}")]
    return sorted(out, key=lambda b: b.path.name, reverse=True)


def open_backup(path: Path, passphrase: str) -> tuple[dict, dict[str, bytes]]:
    """Decrypt and check a backup. Returns (manifest, files). Raises BackupError."""
    raw = Path(path).read_bytes()
    if not raw.startswith(MAGIC):
        raise BackupError("This is not a Cash Flow Forecast backup file.")
    salt, token = raw[len(MAGIC):len(MAGIC) + 16], raw[len(MAGIC) + 16:]
    try:
        data = Fernet(_key(passphrase, salt)).decrypt(token)
    except InvalidToken:
        raise BackupError("The backup cannot be opened: wrong passphrase, or the file has been changed or damaged.")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        manifest = json.loads(z.read("manifest.json"))
        files = {n: z.read(n) for n in z.namelist() if n != "manifest.json"}
    for name, digest in manifest["files"].items():
        if name not in files or _sha(files[name]) != digest:
            raise BackupError(f"The backup is incomplete or damaged ({name}).")
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "check.db"
        p.write_bytes(files["cashflow.db"])
        con = sqlite3.connect(p)
        try:
            ok = con.execute("PRAGMA integrity_check").fetchone()[0]
            users = con.execute("SELECT count(*) FROM user").fetchone()[0]
        finally:
            con.close()
    if ok != "ok":
        raise BackupError(f"The database in the backup failed its integrity check: {ok}")
    manifest["users"] = users
    return manifest, files


def restore_backup(path: Path, s: Settings | None = None) -> Path:
    """Replace the database and uploads with the backup. Stop the app first.
    The current state is backed up first (so a restore can itself be undone). Returns that safety backup."""
    s = s or get_settings()
    manifest, files = open_backup(path, s.backup_passphrase)          # check everything before touching data
    safety = create_backup(s, note=f"automatic, before restoring {Path(path).name}")
    for suffix in ("-wal", "-shm"):
        Path(str(s.database_path) + suffix).unlink(missing_ok=True)
    tmp_db = s.database_path.with_suffix(".restoring")
    tmp_db.write_bytes(files["cashflow.db"])
    tmp_db.replace(s.database_path)
    if s.uploads_dir.exists():
        shutil.rmtree(s.uploads_dir)
    s.uploads_dir.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        if name.startswith("uploads/"):
            target = (s.uploads_dir / name[len("uploads/"):]).resolve()
            if s.uploads_dir.resolve() not in target.parents:      # never write outside uploads/
                raise BackupError(f"Unsafe path in backup: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return safety


def backed_up_today(s: Settings | None = None) -> bool:
    today = datetime.now().strftime("%Y%m%d")
    return any(b.path.name.startswith(f"cff_backup_{today}") for b in list_backups(s))
