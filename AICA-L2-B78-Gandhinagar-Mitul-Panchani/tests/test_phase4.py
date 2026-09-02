"""Phase 4 tests for explicit, similarity-independent contradiction checks."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from amg.audit import verify_chain
from amg.contradiction import check_for_contradiction, find_candidates_for_check
from amg.config import get_settings
from amg.db import connect, init_schema, utc_now_iso
from amg.memory_service import get_flagged_conflicts, ingest_turn, resolve_conflict
from amg.models import EntailmentVerdict, MemoryStatus
from amg.providers.llm_stub import StubProvider
from amg.session import new_session


EMPLOYER_TURN = (
    "I work as a financial controller at Northwind Textiles in Coimbatore."
)
NEW_EMPLOYER_TURN = "Actually I've moved on - I'm at Silverline Logistics now."
OFFICE_DETAIL_TURN = "Our office is in the Peelamedu area."


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    connection = connect(tmp_path / "phase4.db")
    init_schema(connection)
    yield connection
    connection.close()


def test_scenario_2_preserves_and_flags_both_employers(
    conn: sqlite3.Connection,
) -> None:
    session = new_session()
    ingest_turn(conn, session, EMPLOYER_TURN)
    report = ingest_turn(conn, session, NEW_EMPLOYER_TURN)

    employers = conn.execute(
        "SELECT * FROM memories WHERE subject_key = 'employer' ORDER BY id"
    ).fetchall()
    assert len(employers) == 2
    assert {row["status"] for row in employers} == {
        MemoryStatus.FLAGGED_CONFLICT.value
    }
    assert all(row["content"] for row in employers)
    assert report.candidates[0].reason_code == "conflict_detected"
    assert {memory.id for memory in get_flagged_conflicts(conn, "employer")} == {
        int(row["id"]) for row in employers
    }

    flag_events = conn.execute(
        "SELECT * FROM audit_log WHERE event_type = 'update'"
    ).fetchall()
    assert flag_events
    assert any(
        json.loads(row["detail"]).get("status") == "flagged_conflict"
        for row in flag_events
    )
    assert verify_chain(conn).valid is True


def test_scenario_2b_additive_detail_remains_active(
    conn: sqlite3.Connection,
) -> None:
    session = new_session()
    ingest_turn(conn, session, EMPLOYER_TURN)
    report = ingest_turn(conn, session, OFFICE_DETAIL_TURN)

    statuses = [
        row["status"]
        for row in conn.execute("SELECT status FROM memories").fetchall()
    ]
    office = conn.execute(
        "SELECT * FROM memories WHERE content LIKE '%Peelamedu%'"
    ).fetchone()
    assert office is not None
    assert office["status"] == MemoryStatus.ACTIVE.value
    assert report.candidates[0].reason_code == "approved"
    assert MemoryStatus.FLAGGED_CONFLICT.value not in statuses
    assert not get_flagged_conflicts(conn)


def test_stub_confidences_empirically_separate_scenarios_2_and_2b(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AMG_CONTRADICTION_MIN_CONFIDENCE", raising=False)
    get_settings.cache_clear()
    stub = StubProvider()
    conflict = stub.check_entailment(NEW_EMPLOYER_TURN, EMPLOYER_TURN)
    additive = stub.check_entailment(OFFICE_DETAIL_TURN, EMPLOYER_TURN)
    threshold = get_settings().contradiction_min_confidence

    assert conflict.contradicts is True
    assert conflict.confidence == 0.96
    assert additive.contradicts is False
    assert additive.confidence == 0.94
    assert conflict.contradicts is True
    assert conflict.confidence >= threshold
    # Decision 002: the explicit false entailment boolean, not a synthetic
    # confidence midpoint, is what correctly excludes this additive detail.
    assert additive.contradicts is False


def _insert_memory(conn: sqlite3.Connection, content: str) -> None:
    embedding = conn.execute(
        "INSERT INTO embeddings (vector, model_version) VALUES ('[]', 'test')"
    )
    timestamp = utc_now_iso()
    conn.execute(
        """
        INSERT INTO memories (
            content, subject_key, category, source_type, confirmed_at,
            source_session_id, created_at, last_verified_at, status,
            supersedes_id, embedding_id
        ) VALUES (?, 'employer', 'professional', 'user_stated', NULL,
                  'seed', ?, ?, 'active', NULL, ?)
        """,
        (content, timestamp, timestamp, int(embedding.lastrowid)),
    )
    conn.commit()


def test_every_same_subject_candidate_gets_an_entailment_call(
    conn: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _insert_memory(conn, "I work at Northwind Textiles.")
    _insert_memory(conn, "Our office is in Coimbatore.")
    calls: list[tuple[str, str]] = []

    class CountingLLM:
        def check_entailment(
            self, new_fact: str, existing_fact: str
        ) -> EntailmentVerdict:
            calls.append((new_fact, existing_fact))
            return EntailmentVerdict(
                contradicts=False,
                confidence=0.94,
                reason="additive",
            )

    monkeypatch.setattr(
        "amg.contradiction.get_llm_provider", lambda: CountingLLM()
    )
    candidates = find_candidates_for_check(conn, "employer")
    result = check_for_contradiction(
        conn,
        OFFICE_DETAIL_TURN,
        "employer",
    )

    # No embedding provider, cosine function, or vector table is consulted by
    # this path: the explicit entailment call count equals the SQL candidates.
    assert result.checked_count == len(candidates) == len(calls) == 2
    assert result.conflicts == []


def test_resolve_conflict_sets_replacement_links_and_audits(
    conn: sqlite3.Connection,
) -> None:
    session = new_session()
    ingest_turn(conn, session, EMPLOYER_TURN)
    ingest_turn(conn, session, NEW_EMPLOYER_TURN)
    employer_ids = [
        int(row["id"])
        for row in conn.execute(
            "SELECT id FROM memories WHERE subject_key = 'employer' ORDER BY id"
        ).fetchall()
    ]
    old_id, new_id = employer_ids
    keeper, superseded = resolve_conflict(conn, session, new_id, old_id)

    assert keeper.status is MemoryStatus.ACTIVE
    assert keeper.supersedes_id == old_id
    assert superseded.status is MemoryStatus.SUPERSEDED
    update_rows = conn.execute(
        "SELECT * FROM audit_log WHERE event_type = 'update' ORDER BY id"
    ).fetchall()
    assert any(row["memory_id"] == new_id for row in update_rows)
    assert any(row["memory_id"] == old_id for row in update_rows)
    assert verify_chain(conn).valid is True
