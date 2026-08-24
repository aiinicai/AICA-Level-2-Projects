"""Contradiction detection enforcing P0 rule 6: similarity NEVER decides."""

from __future__ import annotations

import sqlite3

from amg.config import get_settings
from amg.models import ContradictionResult, EntailmentVerdict, Memory
from amg.providers import get_llm_provider


def _memory_from_row(row: sqlite3.Row) -> Memory:
    return Memory.model_validate(dict(row))


def find_candidates_for_check(
    conn: sqlite3.Connection,
    subject_key: str,
    exclude_id: int | None = None,
) -> list[Memory]:
    """Return every unresolved memory sharing the exact normalized subject key."""

    sql = """
        SELECT *
        FROM memories
        WHERE subject_key = ?
          AND status IN ('active', 'flagged_conflict')
    """
    parameters: list[object] = [subject_key]
    if exclude_id is not None:
        sql += " AND id <> ?"
        parameters.append(exclude_id)
    sql += " ORDER BY id"
    return [
        _memory_from_row(row)
        for row in conn.execute(sql, parameters).fetchall()
    ]


def check_for_contradiction(
    conn: sqlite3.Connection,
    new_content: str,
    subject_key: str,
) -> ContradictionResult:
    """Use an explicit entailment judgment for every same-subject candidate."""

    candidates = find_candidates_for_check(conn, subject_key)
    llm = get_llm_provider()
    threshold = get_settings().contradiction_min_confidence
    conflicts: list[tuple[Memory, EntailmentVerdict]] = []

    # Exact subject_key matching narrows the field cheaply and precisely; the
    # LLM then makes the actual judgment. Similarity alone can miss subtle
    # contradictions and false-positive on facts that are merely related.
    for existing in candidates:
        verdict = llm.check_entailment(new_content, existing.content)
        if verdict.contradicts is True and verdict.confidence >= threshold:
            conflicts.append((existing, verdict))

    return ContradictionResult(
        conflicts=conflicts,
        checked_count=len(candidates),
    )
