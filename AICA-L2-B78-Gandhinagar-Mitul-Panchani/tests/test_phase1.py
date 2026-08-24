"""Phase 1 tests for schema, configuration plumbing, and audit integrity."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from amg.audit import (  # noqa: E402
    GENESIS_HASH,
    AuditDetailViolation,
    append_event,
    assert_detail_safe,
    compute_row_hash,
    verify_chain,
)
from amg.db import connect, init_schema  # noqa: E402
from amg.models import EventType  # noqa: E402


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    connection = connect(tmp_path / "phase1.db")
    init_schema(connection)
    yield connection
    connection.close()


def _append_three_events(conn: sqlite3.Connection) -> list[int]:
    return [
        append_event(
            conn,
            EventType.WRITE,
            "demo-user",
            {"subject_key": "employer", "content_sha256": "a" * 64},
            memory_id=11,
        ),
        append_event(
            conn,
            EventType.CONTEXTUAL_READ,
            "assistant",
            {"result_count": 1, "top_k": 6, "provider": "local"},
        ),
        append_event(
            conn,
            EventType.UPDATE,
            "demo-user",
            {"field_changed": "status", "status": "flagged_conflict"},
            memory_id=11,
        ),
    ]


def test_schema_creates_all_tables_and_expected_columns(
    conn: sqlite3.Connection,
) -> None:
    expected = {
        "memories": {
            "id",
            "content",
            "subject_key",
            "category",
            "source_type",
            "confirmed_at",
            "source_session_id",
            "created_at",
            "last_verified_at",
            "status",
            "supersedes_id",
            "embedding_id",
        },
        "embeddings": {"id", "vector", "model_version"},
        "derived_from": {"memory_id", "parent_memory_id"},
        "audit_log": {
            "id",
            "event_type",
            "memory_id",
            "actor",
            "timestamp",
            "detail",
            "prev_row_hash",
            "row_hash",
        },
    }
    tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }

    assert expected.keys() <= tables
    for table, expected_columns in expected.items():
        actual_columns = {
            row["name"] for row in conn.execute(f"PRAGMA table_info({table})")
        }
        assert actual_columns == expected_columns


def test_appended_events_form_a_valid_chain(conn: sqlite3.Connection) -> None:
    ids = _append_three_events(conn)

    result = verify_chain(conn)

    assert ids == [1, 2, 3]
    assert result.valid is True
    assert result.rows_checked == 3
    assert result.broken_at_row_id is None


def test_tampered_detail_is_detected_at_modified_row(
    conn: sqlite3.Connection,
) -> None:
    _append_three_events(conn)
    conn.execute(
        "UPDATE audit_log SET detail = ? WHERE id = 2",
        ('{"result_count":99,"top_k":6}',),
    )
    conn.commit()

    result = verify_chain(conn)

    assert result.valid is False
    assert result.broken_at_row_id == 2
    assert result.rows_checked == 2


def test_deleted_middle_row_breaks_chain_linkage(conn: sqlite3.Connection) -> None:
    _append_three_events(conn)
    conn.execute("DELETE FROM audit_log WHERE id = 2")
    conn.commit()

    result = verify_chain(conn)

    assert result.valid is False
    assert result.broken_at_row_id == 3
    assert "linkage" in result.reason


def test_modified_row_hash_is_detected(conn: sqlite3.Connection) -> None:
    _append_three_events(conn)
    conn.execute("UPDATE audit_log SET row_hash = ? WHERE id = 2", ("f" * 64,))
    conn.commit()

    result = verify_chain(conn)

    assert result.valid is False
    assert result.broken_at_row_id == 2


def test_disallowed_detail_is_rejected_and_not_written(
    conn: sqlite3.Connection,
) -> None:
    unsafe_detail = {"content": "User works at Example Corp"}

    with pytest.raises(AuditDetailViolation):
        assert_detail_safe(unsafe_detail)
    with pytest.raises(AuditDetailViolation):
        append_event(conn, EventType.WRITE, "demo-user", unsafe_detail)

    count = conn.execute("SELECT COUNT(*) AS count FROM audit_log").fetchone()
    assert count["count"] == 0


def test_genesis_row_uses_zero_hash(conn: sqlite3.Connection) -> None:
    append_event(
        conn,
        EventType.ACCESS_DENIED,
        "policy-engine",
        {"reason_code": "confirmation_required", "gate": "full_export"},
    )

    row = conn.execute("SELECT prev_row_hash FROM audit_log WHERE id = 1").fetchone()
    assert row["prev_row_hash"] == GENESIS_HASH == "0" * 64


def test_compute_row_hash_is_deterministic_and_covers_every_field() -> None:
    arguments = (
        "write",
        7,
        "demo-user",
        "2026-08-23T10:00:00+00:00",
        '{"category":"profile"}',
        "0" * 64,
    )
    baseline = compute_row_hash(*arguments)

    assert compute_row_hash(*arguments) == baseline

    variations = [
        ("update", *arguments[1:]),
        (arguments[0], 8, *arguments[2:]),
        (*arguments[:2], "assistant", *arguments[3:]),
        (*arguments[:3], "2026-08-23T10:00:01+00:00", *arguments[4:]),
        (*arguments[:4], '{"category":"preferences"}', arguments[5]),
        (*arguments[:5], "1" * 64),
    ]
    assert all(compute_row_hash(*changed) != baseline for changed in variations)

