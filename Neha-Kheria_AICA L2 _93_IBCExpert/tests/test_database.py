from __future__ import annotations

import sqlite3

import pytest

from app.core.errors import IntegrityError
from app.db.connection import connect, integrity_check, transaction
from app.db.migrate import migrate


def test_empty_database_migrates_to_current_schema(tmp_path):
    db = connect(tmp_path / "new.sqlite3")
    assert migrate(db) == 3
    tables = {
        row[0]
        for row in db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")
    }
    for required in (
        "clients",
        "matters",
        "documents",
        "legal_provisions",
        "recommendations",
        "trial_state",
        "search_index",
    ):
        assert required in tables
    assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert integrity_check(db) == (True, "ok")


def test_migration_is_idempotent_and_checksum_protected(tmp_path):
    db = connect(tmp_path / "repeat.sqlite3")
    assert migrate(db) == 3
    assert migrate(db) == 3
    db.execute("UPDATE schema_migrations SET checksum='forged' WHERE version=1")
    with pytest.raises(IntegrityError):
        migrate(db)


def test_transactions_rollback(tmp_path):
    db = connect(tmp_path / "rollback.sqlite3")
    migrate(db)
    with pytest.raises(RuntimeError):
        with transaction(db):
            db.execute(
                "INSERT INTO settings(key,value_json,updated_at) VALUES(?,?,?)",
                ("test", "{}", "2026-09-22T00:00:00Z"),
            )
            raise RuntimeError("force rollback")
    assert db.execute("SELECT COUNT(*) FROM settings WHERE key='test'").fetchone()[0] == 0


def test_parameterized_query_blocks_sql_injection(tmp_path):
    db = connect(tmp_path / "injection.sqlite3")
    migrate(db)
    hostile = "x'); DROP TABLE clients; --"
    db.execute(
        "INSERT INTO settings(key,value_json,updated_at) VALUES(?,?,?)",
        (hostile, "{}", "2026-09-22T00:00:00Z"),
    )
    assert db.execute("SELECT key FROM settings WHERE key=?", (hostile,)).fetchone()[0] == hostile
    assert db.execute("SELECT name FROM sqlite_master WHERE name='clients'").fetchone() is not None
