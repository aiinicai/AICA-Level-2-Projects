"""Phase 9: encrypted backups and restore."""
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db import reset_engine, session_scope
from app.models import AuditLog, User
from app.services import backup as B
from app.services.auth import create_user
from tests.test_phase6_web import PW, app_client, csrf_of, login  # noqa: F401  (fixtures)


@pytest.fixture
def data(engine):
    with session_scope() as db:
        create_user(db, "keeper", PW, "admin", must_change_password=False)
    s = get_settings()
    s.uploads_dir.mkdir(parents=True, exist_ok=True)
    (s.uploads_dir / "2026" / "file1.xlsx").parent.mkdir(parents=True, exist_ok=True)
    (s.uploads_dir / "2026" / "file1.xlsx").write_bytes(b"PK synthetic upload")
    return s


def test_backup_is_encrypted_and_restores_everything(data):
    s = data
    path = B.create_backup(s)
    raw = path.read_bytes()
    assert raw.startswith(B.MAGIC) and b"keeper" not in raw and b"synthetic upload" not in raw   # not readable
    m, files = B.open_backup(path, s.backup_passphrase)
    assert m["users"] == 1 and "uploads/2026/file1.xlsx" in files
    # damage the data after the backup ...
    with session_scope() as db:
        create_user(db, "later", PW, "viewer")
    (s.uploads_dir / "2026" / "file1.xlsx").unlink()
    reset_engine()
    safety = B.restore_backup(path, s)
    reset_engine()
    with session_scope() as db:
        assert [u.username for u in db.scalars(select(User))] == ["keeper"]
    assert (s.uploads_dir / "2026" / "file1.xlsx").read_bytes() == b"PK synthetic upload"
    _, before = B.open_backup(safety, s.backup_passphrase)                 # the restore can be undone
    assert "uploads/2026/file1.xlsx" not in before


def test_wrong_passphrase_or_tampering_is_refused(data):
    s = data
    path = B.create_backup(s)
    with pytest.raises(B.BackupError, match="wrong passphrase"):
        B.open_backup(path, "not-the-passphrase")
    raw = bytearray(path.read_bytes())
    raw[-10] ^= 1
    path.write_bytes(bytes(raw))
    with pytest.raises(B.BackupError, match="changed or damaged"):
        B.open_backup(path, s.backup_passphrase)
    other = path.with_name("x.cffbak")
    other.write_bytes(b"hello")
    with pytest.raises(B.BackupError, match="not a Cash Flow Forecast backup"):
        B.open_backup(other, s.backup_passphrase)


def test_keep_newest_and_copy_folder(data, tmp_path, monkeypatch):
    monkeypatch.setenv("CFF_BACKUP_KEEP", "2")
    monkeypatch.setenv("CFF_BACKUP_COPY_DIR", str(tmp_path / "share"))
    get_settings.cache_clear()
    s = get_settings()
    for _ in range(3):
        B.create_backup(s)
    assert len(B.list_backups(s)) == 2 and B.backed_up_today(s)
    assert len(list((tmp_path / "share").glob("*.cffbak"))) == 3


def test_backups_page_admin_only(app_client):
    c = app_client
    login(c, "prep1")
    assert c.get("/admin/backups").status_code == 403
    c.post("/logout", data={"csrf_token": csrf_of(c.get("/forecast").text)})
    login(c, "admin1")
    page = c.get("/admin/backups").text
    assert "No backups yet" in page and "backup passphrase" in page
    r = c.post("/admin/backups", data={"csrf_token": csrf_of(page)}, follow_redirects=True)
    assert "Backup saved" in r.text
    name = r.text.split("Backup saved: ")[1].split(".cffbak")[0] + ".cffbak"
    d = c.get(f"/admin/backups/{name}")
    assert d.status_code == 200 and d.content.startswith(B.MAGIC)
    assert c.get("/admin/backups/..%2Fcashflow.db").status_code in (403, 404)
    with session_scope() as db:
        acts = {a.action for a in db.scalars(select(AuditLog))}
        assert {"backup.create", "backup.download"} <= acts


def test_console_backup_verify_and_url(engine, capsys):
    from app.cli import main
    main(["backup"])
    path = capsys.readouterr().out.split("Backup written: ")[1].strip()
    main(["verify-backup", path])
    assert "database integrity ok" in capsys.readouterr().out
    main(["url"])
    assert capsys.readouterr().out.strip() == "http://localhost:8000"
