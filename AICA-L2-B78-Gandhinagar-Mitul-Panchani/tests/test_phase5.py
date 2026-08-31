"""Phase 5 tests for confirmed, cascading physical erasure."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from amg.audit import verify_chain
from amg.db import connect, init_schema, utc_now_iso
from amg.deletion import collect_cascade, erase, preview_cascade
from amg.memory_service import ingest_turn
from amg.retrieval import contextual_retrieve
from amg.session import new_session
from tests.test_phase3 import _assert_no_content_leak


DIET_TURN = "I'm strictly vegetarian - I don't eat eggs either."


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    connection = connect(tmp_path / "phase5.db")
    init_schema(connection)
    yield connection
    connection.close()


def _insert_memory(conn: sqlite3.Connection, content: str) -> int:
    embedding = conn.execute(
        "INSERT INTO embeddings (vector, model_version) VALUES ('[]', 'test')"
    )
    timestamp = utc_now_iso()
    memory = conn.execute(
        """
        INSERT INTO memories (
            content, subject_key, category, source_type, confirmed_at,
            source_session_id, created_at, last_verified_at, status,
            supersedes_id, embedding_id
        ) VALUES (?, 'test_fact', 'test', 'user_stated', NULL,
                  'seed', ?, ?, 'active', NULL, ?)
        """,
        (content, timestamp, timestamp, int(embedding.lastrowid)),
    )
    assert memory.lastrowid is not None
    return int(memory.lastrowid)


def test_scenario_4_erases_parent_child_embeddings_and_lineage(
    conn: sqlite3.Connection,
) -> None:
    session = new_session()
    report = ingest_turn(conn, session, DIET_TURN)
    written_ids = [
        candidate.memory_id
        for candidate in report.candidates
        if candidate.memory_id is not None
    ]
    assert len(written_ids) == 2
    rows = conn.execute(
        "SELECT id, content, embedding_id FROM memories ORDER BY id"
    ).fetchall()
    contents = [str(row["content"]) for row in rows]
    embedding_ids = [int(row["embedding_id"]) for row in rows]
    parent_id = int(
        conn.execute(
            "SELECT id FROM memories WHERE source_type = 'user_stated'"
        ).fetchone()[0]
    )

    before = contextual_retrieve(conn, session, "vegetarian leather")
    assert {hit.id for hit in before.hits} == set(written_ids)
    preview = preview_cascade(conn, parent_id)
    result = erase(conn, session, parent_id, confirmed=True)

    assert preview.memory_ids == result.plan.memory_ids
    assert set(result.plan.memory_ids) == set(written_ids)
    assert result.chain_valid is True
    assert conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 0
    placeholders = ",".join("?" for _ in embedding_ids)
    assert conn.execute(
        f"SELECT COUNT(*) FROM embeddings WHERE id IN ({placeholders})",
        embedding_ids,
    ).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM derived_from").fetchone()[0] == 0
    assert contextual_retrieve(conn, session, "vegetarian leather").hits == []

    delete_rows = conn.execute(
        "SELECT * FROM audit_log WHERE event_type = 'delete' ORDER BY id"
    ).fetchall()
    assert len(delete_rows) == 2
    _assert_no_content_leak(delete_rows, contents)
    assert verify_chain(conn).valid is True


def test_unconfirmed_erase_mutates_nothing_and_logs_denial(
    conn: sqlite3.Connection,
) -> None:
    ingest_turn(conn, new_session(), DIET_TURN)
    parent_id = int(
        conn.execute(
            "SELECT id FROM memories WHERE source_type = 'user_stated'"
        ).fetchone()[0]
    )
    before_counts = tuple(
        conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("memories", "embeddings", "derived_from")
    )

    result = erase(conn, new_session(), parent_id, confirmed=False)

    after_counts = tuple(
        conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("memories", "embeddings", "derived_from")
    )
    denial = conn.execute(
        "SELECT detail FROM audit_log WHERE event_type = 'access_denied'"
    ).fetchone()
    assert result.erased is False
    assert result.plan.cascade_count == 2
    assert after_counts == before_counts
    assert denial is not None
    assert '"gate":"delete_confirmation"' in denial["detail"]


def test_three_level_chain_cascades_to_arbitrary_depth(
    conn: sqlite3.Connection,
) -> None:
    first = _insert_memory(conn, "A parent fact")
    second = _insert_memory(conn, "A child fact")
    third = _insert_memory(conn, "A grandchild fact")
    conn.executemany(
        "INSERT INTO derived_from (memory_id, parent_memory_id) VALUES (?, ?)",
        [(second, first), (third, second)],
    )
    conn.commit()

    plan = collect_cascade(conn, first)
    result = erase(conn, new_session(), first, confirmed=True)

    assert plan.memory_ids == [first, second, third]
    assert result.plan.cascade_count == 3
    assert conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM derived_from").fetchone()[0] == 0


def test_cyclic_lineage_graph_terminates_and_collects_each_memory_once(
    conn: sqlite3.Connection,
) -> None:
    first = _insert_memory(conn, "Cycle A")
    second = _insert_memory(conn, "Cycle B")
    conn.executemany(
        "INSERT INTO derived_from (memory_id, parent_memory_id) VALUES (?, ?)",
        [(second, first), (first, second)],
    )
    conn.commit()

    plan = collect_cascade(conn, first)
    result = erase(conn, new_session(), first, confirmed=True)

    assert plan.memory_ids == [first, second]
    assert result.erased is True
    assert conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 0
