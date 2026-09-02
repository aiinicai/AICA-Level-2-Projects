import sys
import os
from pathlib import Path
import pytest
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import database
import security
from config import DB_PATH

def test_database_connection_and_wal():
    # Verify we can run a simple query
    res = database.execute_query("SELECT 1", fetch="one")
    assert res == (1,)
    
    # Verify WAL journal mode is enabled for SQLite
    if not database.USE_SQLALCHEMY:
        with database._sqlite_connect() as con:
            mode = con.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode.lower() == "wal"
            
            foreign_keys = con.execute("PRAGMA foreign_keys").fetchone()[0]
            assert foreign_keys == 1

def test_session_store_crud():
    test_key = f"test_session_key_{int(datetime.now().timestamp())}"
    test_value = {"user": "admin", "roles": ["admin"], "active": True}
    
    # Save session
    database.save_session(test_key, test_value)
    
    # Load session and assert match
    loaded = database.load_session(test_key)
    assert loaded == test_value
    
    # Clean up
    database.execute_query("DELETE FROM session_store WHERE key=?", (test_key,))
    loaded_after_delete = database.load_session(test_key)
    assert loaded_after_delete is None

def test_notice_store_persistence():
    pan = "ABCDE1234F"
    ay = "2025-26"
    notice_type = "143(2)"
    extraction = '{"issues": ["Issue 1"]}'
    draft = "Filing draft content"
    cover = "Cover note content"
    proc_flags = ["flag1", "flag2"]
    
    row_id = database.persist_notice_store(
        pan=pan,
        ay=ay,
        notice_type=notice_type,
        extraction=extraction,
        draft=draft,
        cover=cover,
        proc_flags=proc_flags,
        risk_score=40,
        success_score=85,
        username="admin"
    )
    
    assert row_id > 0
    
    # Retrieve notice
    row = database.execute_query("SELECT * FROM notice_store WHERE id=?", (row_id,), fetch="one")
    assert row is not None
    # Check structure
    assert row[3] == pan # column indices: id (0), created_at (1), username (2), pan (3)
    assert row[4] == ay
    
    # Clean up
    database.execute_query("DELETE FROM notice_store WHERE id=?", (row_id,))

def test_audit_trail():
    test_action = "TEST_INTEGRATION_ACTION"
    database.write_audit_trail(action=test_action, resource="test_resource", details="test_details", username="test_user")
    
    rows = database.query_dicts("SELECT * FROM audit_trail WHERE action=? ORDER BY id DESC", (test_action,))
    assert len(rows) > 0
    assert rows[0]["username"] == "test_user"
    assert rows[0]["resource"] == "test_resource"
    assert rows[0]["details"] == "test_details"
    
    # Clean up
    database.execute_query("DELETE FROM audit_trail WHERE action=?", (test_action,))

def test_auth_and_lockout():
    # Verify authenticate handles valid logins
    # admin / admin123 is present in secrets.toml
    res = security.authenticate("admin", "admin123")
    assert res is not None
    assert res["username"] == "admin"
    assert res["role"] == "admin"
    assert "token" in res
    
    # Verify invalid login fails
    res_fail = security.authenticate("admin", "wrongpassword")
    assert res_fail is None
