"""Executable, asserting evidence for the nine capstone demo scenarios."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from typing import Any

from amg import audit
from amg.config import get_settings
from amg.deletion import erase, preview_cascade
from amg.demo.persona import (
    SCENARIO_1,
    SCENARIO_2,
    SCENARIO_2B,
    SCENARIO_3,
    SCENARIO_4,
    SCENARIO_5A,
    SCENARIO_5B,
    SCENARIO_6A,
    SCENARIO_6B,
    SESSION_1,
)
from amg.memory_service import confirm_inference, ingest_turn
from amg.models import ScenarioResult, TrustTier
from amg.retrieval import contextual_retrieve, full_export
from amg.session import Session, new_session


Evidence = list[dict[str, Any]]
ScenarioBody = Callable[[list[str], Evidence], None]


def _audit_count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0])


def _check(
    evidence: Evidence,
    assertion: str,
    expected: object,
    actual: object,
    condition: bool,
) -> None:
    evidence.append(
        {"assertion": assertion, "expected": expected, "actual": actual}
    )
    assert condition, f"{assertion}: expected {expected!r}, observed {actual!r}"


def _run(
    conn: sqlite3.Connection,
    definition: dict[str, object],
    body: ScenarioBody,
) -> ScenarioResult:
    before = _audit_count(conn)
    steps: list[str] = []
    evidence: Evidence = []
    passed = True
    try:
        body(steps, evidence)
    except Exception as exc:
        passed = False
        evidence.append(
            {
                "assertion": "scenario completed without an exception",
                "expected": True,
                "actual": f"{type(exc).__name__}: {exc}",
            }
        )
    return ScenarioResult(
        id=str(definition["id"]),
        title=str(definition["title"]),
        what_it_proves=str(definition["what_it_proves"]),
        steps=steps,
        passed=passed,
        evidence=evidence,
        audit_rows_written=max(0, _audit_count(conn) - before),
    )


def _direct_memory(conn: sqlite3.Connection, text: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM memories WHERE content = ? ORDER BY id LIMIT 1", (text,)
    ).fetchone()


def seed_session_one(conn: sqlite3.Connection) -> tuple[Session, list[object]]:
    """Write the two scripted establishing turns once, in one real session."""

    session = new_session()
    reports: list[object] = []
    for turn in SESSION_1["inputs"]:
        assert isinstance(turn, str)
        if _direct_memory(conn, turn) is None:
            reports.append(ingest_turn(conn, session, turn))
    return session, reports


def scenario_1_continuity(conn: sqlite3.Connection) -> ScenarioResult:
    def body(steps: list[str], evidence: Evidence) -> None:
        seed_session_one(conn)
        employer_text = str(SESSION_1["inputs"][0])
        stored = _direct_memory(conn, employer_text)
        assert stored is not None
        fresh = new_session()
        steps.append(
            f"Before: session 1 memory was written by {stored['source_session_id']}."
        )
        result = contextual_retrieve(conn, fresh, str(SCENARIO_1["inputs"][0]))
        match = next((hit for hit in result.hits if hit.content == employer_text), None)
        steps.append(
            f"After: fresh session {fresh.session_id} retrieved {len(result.hits)} bounded hit(s)."
        )
        _check(
            evidence,
            "fresh session differs from the source session",
            True,
            fresh.session_id != stored["source_session_id"],
            fresh.session_id != stored["source_session_id"],
        )
        _check(evidence, "employer fact was retrieved", True, match is not None, match is not None)
        assert match is not None
        _check(evidence, "provenance remained user_stated", "user_stated", match.source_type.value, match.source_type.value == "user_stated")
        _check(evidence, "source session remained intact", stored["source_session_id"], match.source_session_id, match.source_session_id == stored["source_session_id"])
        _check(evidence, "creation timestamp remained intact", stored["created_at"], match.created_at, match.created_at == stored["created_at"])

    return _run(conn, SCENARIO_1, body)


def scenario_2_contradiction(conn: sqlite3.Connection) -> ScenarioResult:
    def body(steps: list[str], evidence: Evidence) -> None:
        seed_session_one(conn)
        old_text = str(SESSION_1["inputs"][0])
        old = _direct_memory(conn, old_text)
        assert old is not None
        fresh = new_session()
        before_count = int(conn.execute("SELECT COUNT(*) FROM memories WHERE subject_key = 'employer'").fetchone()[0])
        steps.append(f"Before: {before_count} employer fact existed; a new zero-history session began.")
        report = ingest_turn(conn, fresh, str(SCENARIO_2["inputs"][0]))
        rows = conn.execute("SELECT * FROM memories WHERE subject_key = 'employer' ORDER BY id").fetchall()
        steps.append(f"After: {len(rows)} employer rows remain, with conflict flags visible.")
        _check(evidence, "scenario used a fresh session", True, fresh.session_id != old["source_session_id"], fresh.session_id != old["source_session_id"])
        _check(evidence, "both employer facts were retained", before_count + 1, len(rows), len(rows) == before_count + 1)
        statuses = [str(row["status"]) for row in rows]
        _check(evidence, "old and new facts are flagged", ["flagged_conflict"] * len(rows), statuses, bool(rows) and all(status == "flagged_conflict" for status in statuses))
        reasons = [item.reason_code for item in report.candidates]
        _check(evidence, "explicit entailment produced a conflict", "conflict_detected", reasons, "conflict_detected" in reasons)
        updates = conn.execute("SELECT detail FROM audit_log WHERE event_type = 'update' ORDER BY id DESC").fetchall()
        flagged = any(json.loads(str(row["detail"])).get("status") == "flagged_conflict" for row in updates)
        _check(evidence, "conflict flag was audited", True, flagged, flagged)

    return _run(conn, SCENARIO_2, body)


def scenario_2b_additive(conn: sqlite3.Connection) -> ScenarioResult:
    def body(steps: list[str], evidence: Evidence) -> None:
        seed_session_one(conn)
        audit_start = _audit_count(conn)
        steps.append("Before: related employer facts exist, so entailment must discriminate.")
        report = ingest_turn(conn, new_session(), str(SCENARIO_2B["inputs"][0]))
        office = _direct_memory(conn, str(SCENARIO_2B["inputs"][0]))
        new_updates = conn.execute(
            "SELECT detail FROM audit_log WHERE id > ? AND event_type = 'update'", (audit_start,)
        ).fetchall()
        steps.append("After: the Peelamedu detail was written as an active additive fact.")
        _check(evidence, "additive fact was written", True, office is not None, office is not None)
        assert office is not None
        _check(evidence, "additive fact remains active", "active", office["status"], office["status"] == "active")
        _check(evidence, "candidate was approved", "approved", report.candidates[0].reason_code, report.candidates[0].reason_code == "approved")
        flag_updates = [json.loads(str(row["detail"])) for row in new_updates if json.loads(str(row["detail"])).get("status") == "flagged_conflict"]
        _check(evidence, "no new conflict flag was written", 0, len(flag_updates), not flag_updates)

    return _run(conn, SCENARIO_2B, body)


def scenario_3_provenance(conn: sqlite3.Connection) -> ScenarioResult:
    def body(steps: list[str], evidence: Evidence) -> None:
        seed_session_one(conn)
        inferred = conn.execute(
            "SELECT * FROM memories WHERE source_type = 'ai_inferred' ORDER BY id"
        ).fetchall()
        unconfirmed = [row for row in inferred if row["confirmed_at"] is None]
        steps.append(f"Before: {len(unconfirmed)} inference(s) are visibly unconfirmed and lowest trust.")
        _check(evidence, "both session-1 inferences are present", 2, len(inferred), len(inferred) >= 2)
        _check(evidence, "both begin unconfirmed", 2, len(unconfirmed), len(unconfirmed) >= 2)
        target_id = int(unconfirmed[0]["id"])
        updated = confirm_inference(conn, new_session(), target_id)
        steps.append(f"After: inference {target_id} has a confirmation timestamp and raised trust tier.")
        _check(evidence, "confirmation timestamp was set", "non-null", updated.confirmed_at, updated.confirmed_at is not None)
        tier = TrustTier.CONFIRMED_INFERENCE if updated.confirmed_at else TrustTier.UNCONFIRMED_INFERENCE
        _check(evidence, "trust tier rose", "confirmed_inference", tier.value, tier is TrustTier.CONFIRMED_INFERENCE)
        event = conn.execute("SELECT detail FROM audit_log WHERE memory_id = ? AND event_type = 'update' ORDER BY id DESC LIMIT 1", (target_id,)).fetchone()
        actual_tier = json.loads(str(event["detail"])).get("trust_tier") if event else None
        _check(evidence, "confirmation was audited", "confirmed_inference", actual_tier, actual_tier == "confirmed_inference")

    return _run(conn, SCENARIO_3, body)


def scenario_4_erasure(conn: sqlite3.Connection) -> ScenarioResult:
    def body(steps: list[str], evidence: Evidence) -> None:
        seed_session_one(conn)
        dietary = _direct_memory(conn, str(SESSION_1["inputs"][1]))
        assert dietary is not None
        target_id = int(dietary["id"])
        plan = preview_cascade(conn, target_id)
        content_by_id = {
            int(row["id"]): str(row["content"])
            for row in conn.execute(
                f"SELECT id, content FROM memories WHERE id IN ({','.join('?' for _ in plan.memory_ids)})",
                plan.memory_ids,
            ).fetchall()
        }
        steps.append(f"Before: cascade preview identifies {plan.cascade_count} memories and {len(plan.embedding_ids)} embeddings.")
        result = erase(conn, new_session(), target_id, confirmed=True)
        retrieved = contextual_retrieve(conn, new_session(), "vegetarian leather")
        remaining_ids = {hit.id for hit in retrieved.hits}
        memory_count = int(conn.execute(
            f"SELECT COUNT(*) FROM memories WHERE id IN ({','.join('?' for _ in plan.memory_ids)})", plan.memory_ids
        ).fetchone()[0])
        embedding_count = int(conn.execute(
            f"SELECT COUNT(*) FROM embeddings WHERE id IN ({','.join('?' for _ in plan.embedding_ids)})", plan.embedding_ids
        ).fetchone()[0])
        delete_rows = conn.execute(
            "SELECT detail FROM audit_log WHERE event_type = 'delete' ORDER BY id DESC LIMIT ?", (plan.cascade_count,)
        ).fetchall()
        serialized_details = " ".join(str(row["detail"]) for row in delete_rows).casefold()
        leaked = [content for content in content_by_id.values() if content.casefold() in serialized_details]
        chain = audit.verify_chain(conn)
        steps.append("After: content and vectors are physically absent; the retained structural audit chain verifies.")
        _check(evidence, "cascade includes parent and dependent", 2, plan.cascade_count, plan.cascade_count == 2)
        _check(evidence, "erased memories are absent from retrieval", [], sorted(remaining_ids.intersection(plan.memory_ids)), not remaining_ids.intersection(plan.memory_ids))
        _check(evidence, "memory rows were physically erased", 0, memory_count, memory_count == 0)
        _check(evidence, "embedding rows were physically erased", 0, embedding_count, embedding_count == 0)
        _check(evidence, "delete audit detail contains no erased content", [], leaked, not leaked)
        _check(evidence, "hash chain verifies after erasure", True, chain.model_dump(mode="json"), chain.valid)
        _check(evidence, "erase service reported success", True, result.erased, result.erased)

    return _run(conn, SCENARIO_4, body)


def scenario_5a_extraction_attack(conn: sqlite3.Connection) -> ScenarioResult:
    def body(steps: list[str], evidence: Evidence) -> None:
        seed_session_one(conn)
        contents = [str(row["content"]) for row in conn.execute("SELECT content FROM memories").fetchall()]
        steps.append("Before: governed memories exist, but the request uses instruction-override dump framing.")
        result = contextual_retrieve(conn, new_session(), str(SCENARIO_5A["inputs"][0]))
        response = result.model_dump_json().casefold()
        leaked = [content for content in contents if content.casefold() in response]
        steps.append("After: access is denied, zero hits are returned, and denial is audited.")
        _check(evidence, "attack was refused", False, result.allowed, not result.allowed)
        _check(evidence, "refusal returned no hits", 0, len(result.hits), not result.hits)
        _check(evidence, "refusal leaked no memory content", [], leaked, not leaked)
        event = conn.execute("SELECT event_type FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        actual_event = str(event["event_type"]) if event else None
        _check(evidence, "denial was audited", "access_denied", actual_event, actual_event == "access_denied")

    return _run(conn, SCENARIO_5A, body)


def scenario_5b_legitimate_export(conn: sqlite3.Connection) -> ScenarioResult:
    def body(steps: list[str], evidence: Evidence) -> None:
        seed_session_one(conn)
        expected = int(conn.execute("SELECT COUNT(*) FROM memories WHERE status NOT IN ('deleted', 'superseded')").fetchone()[0])
        steps.append(f"Before: {expected} live rows sit behind the explicit passphrase gate.")
        result = full_export(conn, new_session(), get_settings().export_passphrase)
        steps.append(f"After: the confirmed gate returned all {len(result.memories)} live rows.")
        _check(evidence, "confirmed export succeeded", True, result.succeeded, result.succeeded)
        _check(evidence, "complete live record returned", expected, len(result.memories), len(result.memories) == expected)
        event = conn.execute("SELECT event_type FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        actual_event = str(event["event_type"]) if event else None
        _check(evidence, "full export was audited", "full_export", actual_event, actual_event == "full_export")

    return _run(conn, SCENARIO_5B, body)


def scenario_6a_poisoning(conn: sqlite3.Connection) -> ScenarioResult:
    def body(steps: list[str], evidence: Evidence) -> None:
        seed_session_one(conn)
        before = int(conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0])
        reports = []
        steps.append("Before: two adversarial turns are sent independently through maker and checker.")
        for text in SCENARIO_6A["inputs"]:
            reports.append(ingest_turn(conn, new_session(), str(text)))
        after = int(conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0])
        rejected = sum(report.rejected_count for report in reports)
        reasons = [candidate.reason_code for report in reports for candidate in report.candidates]
        steps.append("After: both candidates stop at the checker and only structural rejection evidence remains.")
        _check(evidence, "both poisoning candidates were rejected", 2, rejected, rejected == 2)
        _check(evidence, "no poisoning memory was written", before, after, before == after)
        _check(evidence, "instruction-shaped attempt was identified", True, "instruction_shaped" in reasons, "instruction_shaped" in reasons)
        _check(evidence, "hypothetical attempt was identified", True, "hypothetical_framing" in reasons, "hypothetical_framing" in reasons)
        recent = conn.execute("SELECT detail FROM audit_log WHERE event_type = 'write_rejected' ORDER BY id DESC LIMIT 2").fetchall()
        details = " ".join(str(row["detail"]) for row in recent).casefold()
        leaked = [str(text) for text in SCENARIO_6A["inputs"] if str(text).casefold() in details]
        _check(evidence, "rejection audit contains no candidate content", [], leaked, not leaked)

    return _run(conn, SCENARIO_6A, body)


def scenario_6b_genuine_statement(conn: sqlite3.Connection) -> ScenarioResult:
    def body(steps: list[str], evidence: Evidence) -> None:
        seed_session_one(conn)
        text = str(SCENARIO_6B["inputs"][0])
        steps.append("Before: a genuine direct self-statement follows the adversarial attempts.")
        report = ingest_turn(conn, new_session(), text)
        row = _direct_memory(conn, text)
        steps.append("After: the checker approves it and the write completes normally.")
        _check(evidence, "genuine statement was written", 1, report.written_count, report.written_count == 1)
        _check(evidence, "genuine statement was not rejected", 0, report.rejected_count, report.rejected_count == 0)
        _check(evidence, "qualification memory exists", True, row is not None, row is not None)
        assert row is not None
        _check(evidence, "source type is user_stated", "user_stated", row["source_type"], row["source_type"] == "user_stated")
        _check(evidence, "subject key is normalized", "professional_qualification", row["subject_key"], row["subject_key"] == "professional_qualification")

    return _run(conn, SCENARIO_6B, body)


SCENARIO_FUNCTIONS: dict[str, Callable[[sqlite3.Connection], ScenarioResult]] = {
    "1": scenario_1_continuity,
    "2": scenario_2_contradiction,
    "2b": scenario_2b_additive,
    "3": scenario_3_provenance,
    "4": scenario_4_erasure,
    "5a": scenario_5a_extraction_attack,
    "5b": scenario_5b_legitimate_export,
    "6a": scenario_6a_poisoning,
    "6b": scenario_6b_genuine_statement,
}


def run_all(conn: sqlite3.Connection) -> list[ScenarioResult]:
    """Run the exact nine scenarios in defense order against one persistent store."""

    seed_session_one(conn)
    return [function(conn) for function in SCENARIO_FUNCTIONS.values()]
