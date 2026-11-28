"""Backup: consistent copy + documents, verify, tamper detection, staged restore applied at next start."""
import sqlite3
from pathlib import Path

import pytest

from ipt.services.backup_service import PENDING, BackupError, apply_pending_restore


def test_backup_verify_and_tamper(services, tmp_path):
    (services.data_root / "Companies" / "X").mkdir(parents=True, exist_ok=True)
    (services.data_root / "Companies" / "X" / "bill.pdf").write_bytes(b"%PDF-1.4 test")
    b = services.backups.create()
    assert b.verified and "Integrity check ok" in b.verify_message and "1 document" in b.verify_message
    assert Path(b.path).parent == services.data_root / "Backups"
    with open(b.path, "ab") as f:            # someone changed the file
        f.write(b"junk")
    ok, msg = services.backups.verify(b.id)
    assert not ok and "checksum" in msg


def test_staged_restore_applied_on_next_start(services, tmp_path):
    from ipt.services.company_service import CompanyInput
    b = services.backups.create()
    # change data after the backup
    services.companies.create_company(CompanyInput(name="Made after backup", state_code="27"), services.ctx.user)
    safety = services.backups.stage_restore(Path(b.path))
    assert Path(safety).exists() and (services.data_root / PENDING / "restore.json").exists()
    # IPT closes: release the database, then the next start applies the restore
    db_file = services.db.file_path()
    services.db.engine.dispose()
    root = db_file.parent
    if root != services.data_root:            # tests keep the database next to (not inside) the data folder
        for suffix in ("", "-wal", "-shm"):
            f = Path(str(db_file) + suffix)
            if f.exists():
                f.replace(services.data_root / f"ipt.db{suffix}")
    msg = apply_pending_restore(services.data_root)
    assert "restored" in msg and not (services.data_root / PENDING).exists()
    con = sqlite3.connect(str(services.data_root / "ipt.db"))
    names = [r[0] for r in con.execute("select name from companies")]
    con.close()
    assert "Made after backup" not in names and "ABC Enterprises" in names
    assert any((services.data_root / "Backups").glob("replaced_by_restore_*"))


def test_restore_refuses_bad_file_and_reviewer(services, tmp_path):
    bad = tmp_path / "x.zip"
    bad.write_bytes(b"not a zip")
    with pytest.raises(BackupError):
        services.backups.stage_restore(bad)
    from ipt.core.permissions import PermissionDenied
    services.ctx.user.role = "reviewer"
    with pytest.raises(PermissionDenied):
        services.backups.create()
    services.ctx.user.role = "admin"


def test_schedule_due(services):
    services.settings.set("backup_schedule", "off")
    assert not services.backups.due()
    services.settings.set("backup_schedule", "daily")
    assert services.backups.due()
    services.backups.create("scheduled")
    assert not services.backups.due()
