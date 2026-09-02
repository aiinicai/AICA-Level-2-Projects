"""Cascading erasure enforcing P0 rule 7.

An embedding is derived data that can partially leak its source content, so
it must be destroyed with the content rather than left behind as an orphan.
"""

from __future__ import annotations

import sqlite3
from collections import deque

from amg import audit
from amg.models import CascadePlan, EraseReport, EventType
from amg.session import Session


def collect_cascade(conn: sqlite3.Connection, memory_id: int) -> CascadePlan:
    """Collect the target and all transitive dependents without mutating data."""

    visited: set[int] = set()
    ordered_ids: list[int] = []
    pending: deque[int] = deque([memory_id])

    while pending:
        current_id = pending.popleft()
        if current_id in visited:
            continue
        visited.add(current_id)
        row = conn.execute(
            "SELECT id FROM memories WHERE id = ?", (current_id,)
        ).fetchone()
        if row is None:
            continue
        ordered_ids.append(current_id)
        children = conn.execute(
            """
            SELECT memory_id
            FROM derived_from
            WHERE parent_memory_id = ?
            ORDER BY memory_id
            """,
            (current_id,),
        ).fetchall()
        pending.extend(int(child["memory_id"]) for child in children)

    if not ordered_ids:
        return CascadePlan(
            target_memory_id=memory_id,
            memory_ids=[],
            embedding_ids=[],
        )

    placeholders = ",".join("?" for _ in ordered_ids)
    rows = conn.execute(
        f"""
        SELECT id, embedding_id
        FROM memories
        WHERE id IN ({placeholders})
        """,
        ordered_ids,
    ).fetchall()
    embeddings_by_memory = {
        int(row["id"]): int(row["embedding_id"]) for row in rows
    }
    return CascadePlan(
        target_memory_id=memory_id,
        memory_ids=ordered_ids,
        embedding_ids=[embeddings_by_memory[item] for item in ordered_ids],
    )


def preview_cascade(conn: sqlite3.Connection, memory_id: int) -> CascadePlan:
    """Return the exact erasure plan shown before user confirmation."""

    return collect_cascade(conn, memory_id)


def erase(
    conn: sqlite3.Connection,
    session: Session,
    memory_id: int,
    confirmed: bool,
) -> EraseReport:
    """Physically erase a confirmed cascade and its embeddings atomically."""

    plan = preview_cascade(conn, memory_id)
    if not confirmed:
        audit_id = audit.append_event(
            conn,
            EventType.ACCESS_DENIED,
            session.actor,
            {"gate": "delete_confirmation"},
        )
        chain = audit.verify_chain(conn)
        return EraseReport(
            confirmed=False,
            erased=False,
            plan=plan,
            audit_row_ids=[audit_id],
            chain_verification=chain,
            reason="Deletion confirmation was not supplied.",
        )

    if not plan.memory_ids:
        chain = audit.verify_chain(conn)
        if not chain.valid:
            raise AssertionError(chain.reason)
        return EraseReport(
            confirmed=True,
            erased=False,
            plan=plan,
            chain_verification=chain,
            reason="The requested memory does not exist.",
        )

    placeholders = ",".join("?" for _ in plan.memory_ids)
    rows = conn.execute(
        f"""
        SELECT id, content, subject_key, source_type
        FROM memories
        WHERE id IN ({placeholders})
        """,
        plan.memory_ids,
    ).fetchall()
    metadata = {int(row["id"]): row for row in rows}
    audit_row_ids: list[int] = []
    owns_transaction = not conn.in_transaction

    try:
        if owns_transaction:
            conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            f"""
            DELETE FROM derived_from
            WHERE memory_id IN ({placeholders})
               OR parent_memory_id IN ({placeholders})
            """,
            [*plan.memory_ids, *plan.memory_ids],
        )
        # A conflict-resolution link is metadata, not a reason to retain erased
        # content. Clearing it avoids an unrelated FK blocking the erasure.
        conn.execute(
            f"UPDATE memories SET supersedes_id = NULL WHERE supersedes_id IN ({placeholders})",
            plan.memory_ids,
        )
        conn.execute(
            f"DELETE FROM memories WHERE id IN ({placeholders})",
            plan.memory_ids,
        )
        embedding_placeholders = ",".join("?" for _ in plan.embedding_ids)
        conn.execute(
            f"DELETE FROM embeddings WHERE id IN ({embedding_placeholders})",
            plan.embedding_ids,
        )

        for erased_id in plan.memory_ids:
            row = metadata[erased_id]
            # Section 12(4)-(5)'s retention-vs-erasure balance is represented
            # by a one-way hash: the trail remains tamper-evident without
            # retaining the erased personal data in the audit log.
            audit_row_ids.append(
                audit.append_event(
                    conn,
                    EventType.DELETE,
                    session.actor,
                    {
                        "subject_key": str(row["subject_key"]),
                        "source_type": str(row["source_type"]),
                        "content_sha256": audit.content_fingerprint(
                            str(row["content"])
                        ),
                        "cascade_count": plan.cascade_count,
                        "was_dependent": erased_id != memory_id,
                    },
                    memory_id=erased_id,
                )
            )
        transaction_chain = audit.verify_chain(conn)
        if not transaction_chain.valid:
            raise AssertionError(transaction_chain.reason)
        if owns_transaction:
            conn.commit()
    except Exception:
        if owns_transaction and conn.in_transaction:
            conn.rollback()
        raise

    chain = audit.verify_chain(conn)
    if not chain.valid:
        raise AssertionError(chain.reason)
    return EraseReport(
        confirmed=True,
        erased=True,
        plan=plan,
        audit_row_ids=audit_row_ids,
        chain_verification=chain,
        reason="The target and all transitive dependents were physically erased.",
    )
