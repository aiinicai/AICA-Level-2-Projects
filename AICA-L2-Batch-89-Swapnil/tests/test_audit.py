"""Golden tests 19 and 22: append-only, hash-chained audit log; online backup."""
import shutil
import sqlite3

import pytest

import cli
from app.audit import GENESIS, verify_chain


def raw(db_file):
    return sqlite3.connect(db_file)


# ------------------------------------------------------------ golden 19
def test_g19_raw_sql_update_and_delete_refused(app, as_role):
    as_role("partner")                                   # adds a LOGIN row
    con = raw(app.config["DB_FILE"])
    n = con.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    assert n > 0
    with pytest.raises(sqlite3.IntegrityError, match="audit_log is append-only"):
        con.execute("UPDATE audit_log SET actor_name = 'someone else' WHERE id = 1")
    with pytest.raises(sqlite3.IntegrityError, match="audit_log is append-only"):
        con.execute("DELETE FROM audit_log WHERE id = 1")
    with pytest.raises(sqlite3.IntegrityError, match="audit_log is append-only"):
        con.execute("DELETE FROM audit_log")
    assert con.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == n
    rep = verify_chain(con)
    assert rep.ok and rep.rows == n
    con.close()


def test_g19_tampered_copy_reports_broken_link(app, as_role, tmp_path):
    c = as_role("partner")
    c.get("/entities/1")                                 # a few more rows
    copy = tmp_path / "tampered.db"
    shutil.copy(app.config["DB_FILE"], copy)
    con = raw(copy)
    con.execute("DROP TRIGGER audit_log_no_update")      # an attacker with file access
    con.execute("UPDATE audit_log SET actor_name = 'Someone Else' WHERE id = 3")
    con.commit()
    rep = verify_chain(con)
    assert not rep.ok and rep.broken_id == 3 and "altered" in rep.message
    con.execute("DROP TRIGGER audit_log_no_delete")
    con.execute("UPDATE audit_log SET actor_name = (SELECT actor_name FROM audit_log WHERE id = 3) WHERE id = 3")
    con.execute("DELETE FROM audit_log WHERE id = 5")
    con.commit()
    rep2 = verify_chain(con)
    assert not rep2.ok and rep2.broken_id == 3                # first broken link is still reported first
    con.close()
    # the original is untouched and still verifies
    con = raw(app.config["DB_FILE"])
    assert verify_chain(con).ok
    con.close()


def test_chain_structure(q):
    rows = q(lambda s, M: s.query(M.AuditLog).order_by(M.AuditLog.id).all())
    assert rows[0].prev_hash == GENESIS
    assert all(b.prev_hash == a.row_hash for a, b in zip(rows, rows[1:]))


def test_owner_verify_button(as_role, q):
    r = as_role("owner").post("/admin/audit/verify", follow_redirects=True)
    assert b"Audit chain intact" in r.data
    assert q(lambda s, M: s.query(M.AuditLog).filter_by(action="AUDIT_CHAIN_VERIFIED").count()) == 1


def test_audit_written_in_same_transaction(app, q):
    """A failed request leaves neither the change nor an audit row behind."""
    from app import audit
    from app.models import Entity, db
    with app.app_context():
        n = db.session.query(audit.AuditLog).count()
        e = db.session.get(Entity, 1)
        e.name = "Changed"
        audit.record(db.session, audit.SYSTEM, "ENTITY_UPDATED", "entity", 1, 1, after={"name": "Changed"})
        db.session.rollback()
        assert db.session.query(audit.AuditLog).count() == n
        assert db.session.get(Entity, 1).name == "Alpha Janak Pvt Ltd"


def test_audit_csv_export(as_role):
    r = as_role("manager").get("/admin/audit.csv")
    assert r.status_code == 200 and r.mimetype == "text/csv"
    assert r.data.decode().splitlines()[0].startswith("id,ts,actor_name")


# ------------------------------------------------------------ golden 22
def test_g22_backup_while_running_is_restorable(app, as_role, tmp_path):
    c = as_role("partner")
    assert c.get("/").status_code == 200                  # server has open connections (WAL mode)
    dest = cli.backup_sqlite(app.config["DB_FILE"], tmp_path / "backups")
    con = raw(dest)
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    triggers = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    assert {"audit_log_no_update", "audit_log_no_delete"} <= triggers
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        con.execute("DELETE FROM audit_log")
    assert verify_chain(con).ok
    n_entities = con.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    con.close()
    # restore into a new location and boot the app from it
    from app import create_app
    restored = tmp_path / "restored.db"
    src, dst = raw(dest), raw(restored)
    src.backup(dst)
    src.close()
    dst.close()
    a2 = create_app(DATABASE_URL="sqlite:///" + restored.as_posix(), TESTING=True, SESSION_COOKIE_SECURE=False,
                    WTF_CSRF_ENABLED=False)
    from app.models import Entity, db
    with a2.app_context():
        assert db.session.query(Entity).count() == n_entities == 8
    db.session.remove()
    db.engine.dispose()


def test_backup_rejects_db_without_triggers(tmp_path):
    bad = tmp_path / "bad.db"
    con = raw(bad)
    con.execute("CREATE TABLE x (id INTEGER)")
    con.commit()
    con.close()
    with pytest.raises(RuntimeError, match="verification failed"):
        cli.backup_sqlite(bad, tmp_path / "out")
