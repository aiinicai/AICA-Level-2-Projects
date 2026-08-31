"""Governed write spine implementing ARCHITECTURE.md section 3.3.

The maker receives one direct turn, the isolated checker approves or rejects
each candidate, provenance is tagged, explicit entailment checks precede the
write, embeddings and same-turn lineage are stored, and every terminal branch
is appended to the hash-chained audit log.
"""

from __future__ import annotations

import json
import sqlite3

from amg import audit, contradiction, extraction, provenance, verifier
from amg.db import utc_now_iso
from amg.models import (
    CandidateFact,
    CandidateIngestResult,
    EventType,
    IngestReport,
    Memory,
    MemoryStatus,
    ProviderUse,
    SourceType,
    TrustTier,
)
from amg.providers import (
    get_embedding_provider,
    last_provider_report,
)
from amg.session import Session


def _provider_use(operation: str) -> ProviderUse | None:
    report = last_provider_report().get(operation)
    return ProviderUse.model_validate(report) if report is not None else None


def _fallback_used(calls: dict[str, ProviderUse]) -> bool:
    return any(call.was_fallback for call in calls.values())


def _memory_from_row(row: sqlite3.Row) -> Memory:
    return Memory.model_validate(dict(row))


def _ordered_candidates(candidates: list[CandidateFact]) -> list[tuple[int, CandidateFact]]:
    indexed = list(enumerate(candidates))
    return sorted(
        indexed,
        key=lambda item: item[1].source_type is SourceType.AI_INFERRED,
    )


def ingest_turn(
    conn: sqlite3.Connection,
    session: Session,
    user_text: str,
) -> IngestReport:
    """Carry one direct user turn through every governed write-path stage."""

    # This is intentionally the only maker argument. Session state, retrieval
    # results, and prior chat cannot cross the P0 extraction boundary.
    proposed = extraction.propose_candidates(user_text)
    maker_provider = _provider_use("maker")
    outcomes: list[CandidateIngestResult] = []
    all_audit_ids: list[int] = []
    written_by_content: dict[str, int] = {}
    owns_transaction = not conn.in_transaction

    try:
        if owns_transaction:
            conn.execute("BEGIN IMMEDIATE")

        for original_index, candidate in _ordered_candidates(proposed):
            calls: dict[str, ProviderUse] = {}
            verdict = verifier.verify_candidate(candidate)
            checker_provider = _provider_use("checker")
            if checker_provider is not None:
                calls["checker"] = checker_provider

            fingerprint = audit.content_fingerprint(candidate.content)
            if not verdict.approved:
                audit_id = audit.append_event(
                    conn,
                    EventType.WRITE_REJECTED,
                    session.actor,
                    {
                        "assertion_type": candidate.assertion_type.value,
                        "reason_code": verdict.reason_code.value,
                        "content_sha256": fingerprint,
                    },
                )
                all_audit_ids.append(audit_id)
                outcomes.append(
                    CandidateIngestResult(
                        candidate_index=original_index,
                        assertion_type=candidate.assertion_type,
                        source_type=candidate.source_type,
                        subject_key=candidate.subject_key,
                        category=candidate.category,
                        content_sha256=fingerprint,
                        outcome="rejected",
                        reason_code=verdict.reason_code.value,
                        reason=verdict.notes,
                        audit_row_ids=[audit_id],
                        provider_calls=calls,
                        fallback_used=_fallback_used(calls),
                    )
                )
                continue

            tagged = provenance.tag(candidate)
            if (
                tagged.inferred_from_content is not None
                and tagged.inferred_from_content not in written_by_content
            ):
                # An inference cannot outlive a parent that the same governed
                # turn refused. Audit the disposition instead of either
                # orphaning the child or rolling back the parent's rejection.
                audit_id = audit.append_event(
                    conn,
                    EventType.WRITE_REJECTED,
                    session.actor,
                    {
                        "assertion_type": tagged.assertion_type.value,
                        "reason_code": "parent_not_written",
                        "content_sha256": fingerprint,
                    },
                )
                all_audit_ids.append(audit_id)
                outcomes.append(
                    CandidateIngestResult(
                        candidate_index=original_index,
                        assertion_type=tagged.assertion_type,
                        source_type=tagged.source_type,
                        subject_key=tagged.subject_key,
                        category=tagged.category,
                        content_sha256=fingerprint,
                        outcome="rejected",
                        reason_code="parent_not_written",
                        reason=(
                            "The inferred fact's same-turn parent was not committed."
                        ),
                        audit_row_ids=[audit_id],
                        provider_calls=calls,
                        fallback_used=_fallback_used(calls),
                    )
                )
                continue

            contradiction_result = contradiction.check_for_contradiction(
                conn,
                tagged.content,
                tagged.subject_key,
            )
            if contradiction_result.checked_count:
                entailment_provider = _provider_use("entailment")
                if entailment_provider is not None:
                    calls["entailment"] = entailment_provider

            status = (
                MemoryStatus.FLAGGED_CONFLICT
                if contradiction_result.conflicts
                else MemoryStatus.ACTIVE
            )
            embedding_provider = get_embedding_provider()
            vectors = embedding_provider.embed_documents([tagged.content])
            embedding_report = _provider_use("embedding_documents")
            if embedding_report is not None:
                calls["embedding"] = embedding_report
            if len(vectors) != 1:
                raise RuntimeError("embedding provider returned an unexpected vector count")

            model_version = (
                embedding_report.model
                if embedding_report is not None
                else embedding_provider.model_version
            )
            provider_name = (
                embedding_report.provider_name
                if embedding_report is not None
                else "local"
            )
            embedding_cursor = conn.execute(
                "INSERT INTO embeddings (vector, model_version) VALUES (?, ?)",
                (json.dumps(vectors[0], separators=(",", ":")), model_version),
            )
            if embedding_cursor.lastrowid is None:
                raise RuntimeError("SQLite did not return an embedding id")
            embedding_id = int(embedding_cursor.lastrowid)
            timestamp = utc_now_iso()
            memory_cursor = conn.execute(
                """
                INSERT INTO memories (
                    content, subject_key, category, source_type, confirmed_at,
                    source_session_id, created_at, last_verified_at, status,
                    supersedes_id, embedding_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    tagged.content,
                    tagged.subject_key,
                    tagged.category,
                    tagged.source_type.value,
                    tagged.confirmed_at,
                    session.session_id,
                    timestamp,
                    timestamp,
                    status.value,
                    embedding_id,
                ),
            )
            if memory_cursor.lastrowid is None:
                raise RuntimeError("SQLite did not return a memory id")
            memory_id = int(memory_cursor.lastrowid)
            candidate_audit_ids: list[int] = []

            for existing, _ in contradiction_result.conflicts:
                if existing.status is MemoryStatus.FLAGGED_CONFLICT:
                    continue
                conn.execute(
                    """
                    UPDATE memories
                    SET status = ?, last_verified_at = ?
                    WHERE id = ?
                    """,
                    (
                        MemoryStatus.FLAGGED_CONFLICT.value,
                        timestamp,
                        existing.id,
                    ),
                )
                flag_audit_id = audit.append_event(
                    conn,
                    EventType.UPDATE,
                    session.actor,
                    {
                        "field_changed": "status",
                        "status": MemoryStatus.FLAGGED_CONFLICT.value,
                        "subject_key": tagged.subject_key,
                    },
                    memory_id=existing.id,
                )
                candidate_audit_ids.append(flag_audit_id)
                all_audit_ids.append(flag_audit_id)

            if tagged.inferred_from_content is not None:
                parent_id = written_by_content.get(tagged.inferred_from_content)
                if parent_id is None:
                    raise ValueError(
                        "inferred candidate parent was not written earlier in this turn"
                    )
                conn.execute(
                    """
                    INSERT INTO derived_from (memory_id, parent_memory_id)
                    VALUES (?, ?)
                    """,
                    (memory_id, parent_id),
                )

            written_by_content.setdefault(tagged.content, memory_id)
            write_audit_id = audit.append_event(
                conn,
                EventType.WRITE,
                session.actor,
                {
                    "subject_key": tagged.subject_key,
                    "category": tagged.category,
                    "source_type": tagged.source_type.value,
                    "trust_tier": tagged.trust_tier.value,
                    "status": status.value,
                    "content_sha256": fingerprint,
                    "provider": provider_name,
                },
                memory_id=memory_id,
            )
            candidate_audit_ids.append(write_audit_id)
            all_audit_ids.append(write_audit_id)
            conflict_ids = [
                existing.id for existing, _ in contradiction_result.conflicts
            ]
            outcomes.append(
                CandidateIngestResult(
                    candidate_index=original_index,
                    assertion_type=tagged.assertion_type,
                    source_type=tagged.source_type,
                    subject_key=tagged.subject_key,
                    category=tagged.category,
                    content_sha256=fingerprint,
                    outcome="written",
                    reason_code=(
                        "conflict_detected" if conflict_ids else "approved"
                    ),
                    reason=(
                        "; ".join(
                            verdict.reason
                            for _, verdict in contradiction_result.conflicts
                        )
                        if conflict_ids
                        else "No qualifying contradiction was found."
                    ),
                    memory_id=memory_id,
                    status=status,
                    trust_tier=tagged.trust_tier,
                    checked_count=contradiction_result.checked_count,
                    conflict_memory_ids=conflict_ids,
                    audit_row_ids=candidate_audit_ids,
                    provider_calls=calls,
                    fallback_used=_fallback_used(calls),
                )
            )

        if owns_transaction:
            conn.commit()
    except Exception:
        if owns_transaction and conn.in_transaction:
            conn.rollback()
        raise

    report_calls = {
        "maker": maker_provider,
        **{
            f"candidate_{outcome.candidate_index}_{operation}": provider
            for outcome in outcomes
            for operation, provider in outcome.provider_calls.items()
        },
    }
    fallback_used = any(
        provider is not None and provider.was_fallback
        for provider in report_calls.values()
    )
    return IngestReport(
        session_id=session.session_id,
        candidate_count=len(proposed),
        written_count=sum(outcome.outcome == "written" for outcome in outcomes),
        rejected_count=sum(outcome.outcome == "rejected" for outcome in outcomes),
        candidates=outcomes,
        audit_row_ids=all_audit_ids,
        maker_provider=maker_provider,
        fallback_used=fallback_used,
    )


def confirm_inference(
    conn: sqlite3.Connection,
    session: Session,
    memory_id: int,
) -> Memory:
    """Confirm one AI inference, raise its trust tier, and audit the update."""

    row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
    if row is None:
        raise ValueError(f"memory {memory_id} does not exist")
    memory = _memory_from_row(row)
    if memory.source_type is not SourceType.AI_INFERRED:
        raise ValueError("only an AI-inferred memory can be confirmed")
    if memory.confirmed_at is not None:
        raise ValueError("inference is already confirmed")

    timestamp = utc_now_iso()
    owns_transaction = not conn.in_transaction
    try:
        if owns_transaction:
            conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE memories SET confirmed_at = ?, last_verified_at = ? WHERE id = ?",
            (timestamp, timestamp, memory_id),
        )
        audit.append_event(
            conn,
            EventType.UPDATE,
            session.actor,
            {
                "field_changed": "confirmed_at",
                "trust_tier": TrustTier.CONFIRMED_INFERENCE.value,
            },
            memory_id=memory_id,
        )
        if owns_transaction:
            conn.commit()
    except Exception:
        if owns_transaction and conn.in_transaction:
            conn.rollback()
        raise
    updated = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
    assert updated is not None
    return _memory_from_row(updated)


def resolve_conflict(
    conn: sqlite3.Connection,
    session: Session,
    keep_id: int,
    supersede_id: int,
) -> tuple[Memory, Memory]:
    """Resolve a flagged pair by activating the keeper and superseding the other."""

    if keep_id == supersede_id:
        raise ValueError("keeper and superseded memory must be different rows")
    rows = conn.execute(
        "SELECT * FROM memories WHERE id IN (?, ?) ORDER BY id",
        (keep_id, supersede_id),
    ).fetchall()
    if len(rows) != 2:
        raise ValueError("both conflict memories must exist")
    memories = {int(row["id"]): _memory_from_row(row) for row in rows}
    if any(
        memory.status is not MemoryStatus.FLAGGED_CONFLICT
        for memory in memories.values()
    ):
        raise ValueError("both memories must be flagged conflicts")

    timestamp = utc_now_iso()
    owns_transaction = not conn.in_transaction
    try:
        if owns_transaction:
            conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            UPDATE memories
            SET status = ?, supersedes_id = ?, last_verified_at = ?
            WHERE id = ?
            """,
            (MemoryStatus.ACTIVE.value, supersede_id, timestamp, keep_id),
        )
        conn.execute(
            """
            UPDATE memories
            SET status = ?, last_verified_at = ?
            WHERE id = ?
            """,
            (MemoryStatus.SUPERSEDED.value, timestamp, supersede_id),
        )
        audit.append_event(
            conn,
            EventType.UPDATE,
            session.actor,
            {
                "field_changed": "status,supersedes_id",
                "status": MemoryStatus.ACTIVE.value,
            },
            memory_id=keep_id,
        )
        audit.append_event(
            conn,
            EventType.UPDATE,
            session.actor,
            {
                "field_changed": "status",
                "status": MemoryStatus.SUPERSEDED.value,
            },
            memory_id=supersede_id,
        )
        if owns_transaction:
            conn.commit()
    except Exception:
        if owns_transaction and conn.in_transaction:
            conn.rollback()
        raise

    keep_row = conn.execute("SELECT * FROM memories WHERE id = ?", (keep_id,)).fetchone()
    superseded_row = conn.execute(
        "SELECT * FROM memories WHERE id = ?", (supersede_id,)
    ).fetchone()
    assert keep_row is not None and superseded_row is not None
    return _memory_from_row(keep_row), _memory_from_row(superseded_row)


def get_flagged_conflicts(
    conn: sqlite3.Connection,
    subject_key: str | None = None,
) -> list[Memory]:
    """Return unresolved conflicts, optionally limited to one subject key."""

    sql = "SELECT * FROM memories WHERE status = ?"
    parameters: list[object] = [MemoryStatus.FLAGGED_CONFLICT.value]
    if subject_key is not None:
        sql += " AND subject_key = ?"
        parameters.append(subject_key)
    sql += " ORDER BY subject_key, id"
    return [
        _memory_from_row(row)
        for row in conn.execute(sql, parameters).fetchall()
    ]
