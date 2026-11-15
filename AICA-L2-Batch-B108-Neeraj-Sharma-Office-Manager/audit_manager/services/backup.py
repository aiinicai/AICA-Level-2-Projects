"""Backups: one .zip holding the database and the logo. Download it, or save it to a folder (for example a Google Drive,
OneDrive or pen-drive folder on the host PC) by hand or automatically once a day. Restores are applied at the next start."""
import io
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from ..config import data_dir
from ..models import FirmSetting, db

DB_NAME = "auditmanager.db"
PREFIX = "OfficeManager-backup-"
WHEN = {"off": "Do not back up automatically", "daily": "Once a day", "open": "Every time the app is opened",
        "close": "Every time the app is closed", "open_close": "On opening and on closing"}
PENDING = "restore_pending.zip"


class BackupError(Exception):
    pass


def _db_copy_bytes() -> bytes:
    """A consistent copy of the live database, safe while staff are working."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
    src, dst = sqlite3.connect(str(data_dir() / DB_NAME)), sqlite3.connect(tmp_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    try:
        return Path(tmp_path).read_bytes()
    finally:
        os.unlink(tmp_path)


def make_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(DB_NAME, _db_copy_bytes())
        uploads = data_dir() / "uploads"
        if uploads.is_dir():
            for f in uploads.iterdir():
                if f.is_file():
                    z.write(f, "uploads/" + f.name)
        key = data_dir() / "mail.key"
        if key.exists():  # needed to read the saved email password and client portal passwords after a restore
            z.write(key, "mail.key")
        z.writestr("README.txt", "Office Manager backup made " + datetime.now().strftime("%d %b %Y %H:%M") +
                   "\nRestore it from Settings > Backup > Restore. It includes the key that unlocks saved passwords, so keep this file private.\n")
    return buf.getvalue()


def file_name() -> str:
    return f"{PREFIX}{datetime.now():%Y%m%d-%H%M%S}.zip"


def check_folder(folder: str) -> Path:
    path = Path(os.path.expandvars(os.path.expanduser(folder.strip().strip('"'))))
    if not path.is_absolute():
        raise BackupError("Give the full folder path, for example D:\\Backups or G:\\My Drive\\Office Manager.")
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".am-write-test"
        probe.write_text("ok")
        probe.unlink()
    except OSError:
        raise BackupError(f"Cannot write to {path}. Check that the drive is connected and the folder exists on the host PC.")
    return path


def to_folder(auto: bool = False) -> Path:
    folder = FirmSetting.get("backup_folder") or ""
    if not folder:
        raise BackupError("Choose a backup folder first.")
    try:
        path = check_folder(folder)
        target = path / file_name()
        target.write_bytes(make_zip())
        keep = max(1, int(FirmSetting.get("backup_keep") or 14))
        old = sorted(path.glob(PREFIX + "*.zip"), key=lambda f: f.name, reverse=True)[keep:]
        for f in old:
            try:
                f.unlink()
            except OSError:
                pass
    except (BackupError, OSError) as e:
        FirmSetting.put("backup_last_result", f"FAILED {datetime.now():%d %b %Y %H:%M}: {e}")
        db.session.commit()
        raise BackupError(str(e))
    FirmSetting.put("backup_last_at", datetime.now().strftime("%Y-%m-%d"))
    FirmSetting.put("backup_last_result", f"OK {datetime.now():%d %b %Y %H:%M} ({'automatic' if auto else 'manual'}): {target}")
    db.session.commit()
    return target


def when() -> str:
    w = FirmSetting.get("backup_when") or "off"
    return w if w in WHEN else "off"


def auto_if_due() -> bool:
    """Daily mode: once a day, if a folder is set."""
    if when() != "daily" or not FirmSetting.get("backup_folder"):
        return False
    if FirmSetting.get("backup_last_at") == datetime.now().strftime("%Y-%m-%d"):
        return False
    try:
        to_folder(auto=True)
        return True
    except BackupError:
        return False


def _on(event: str) -> bool:
    if event not in when() or not FirmSetting.get("backup_folder"):
        return False
    try:
        to_folder(auto=True)
        return True
    except BackupError:
        return False


def on_open() -> bool:
    return _on("open")


def on_close() -> bool:
    return _on("close")


def _valid_db(raw: bytes) -> bool:
    if not raw.startswith(b"SQLite format 3"):
        return False
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp.write(raw)
    try:
        con = sqlite3.connect(tmp.name)
        try:
            names = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
            ok = con.execute("pragma integrity_check").fetchone()[0] == "ok"
        finally:
            con.close()
        return ok and {"user", "client", "firm_setting"} <= names
    except sqlite3.Error:
        return False
    finally:
        os.unlink(tmp.name)


def stage_restore(raw: bytes) -> None:
    """Check an uploaded backup and park it; it replaces the live data the next time the app starts."""
    if raw.startswith(b"SQLite format 3"):  # an older plain .db backup
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(DB_NAME, raw)
        raw = buf.getvalue()
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if DB_NAME not in z.namelist():
                raise BackupError("That file is not an Office Manager backup.")
            if not _valid_db(z.read(DB_NAME)):
                raise BackupError("The database inside that backup is damaged or is not from Office Manager.")
    except zipfile.BadZipFile:
        raise BackupError("That file is not an Office Manager backup.")
    (data_dir() / PENDING).write_bytes(raw)


def pending_restore() -> bool:
    return (data_dir() / PENDING).exists()


def cancel_restore() -> None:
    (data_dir() / PENDING).unlink(missing_ok=True)


def apply_pending_restore() -> str | None:
    """Called at start-up, before the database is opened. The current data is kept as a safety copy."""
    base = data_dir()
    pending = base / PENDING
    if not pending.exists():
        return None
    live = base / DB_NAME
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        with zipfile.ZipFile(pending) as z:
            if live.exists():
                shutil.copy2(live, base / f"before-restore-{stamp}.db")
            for extra in (DB_NAME + "-wal", DB_NAME + "-shm"):
                (base / extra).unlink(missing_ok=True)
            live.write_bytes(z.read(DB_NAME))
            if "mail.key" in z.namelist():
                (base / "mail.key").write_bytes(z.read("mail.key"))
            for name in z.namelist():
                if name.startswith("uploads/") and not name.endswith("/") and "/" not in name[len("uploads/"):] and ".." not in name:
                    (base / "uploads").mkdir(exist_ok=True)
                    (base / "uploads" / os.path.basename(name)).write_bytes(z.read(name))
    finally:
        pending.unlink(missing_ok=True)
    return stamp
