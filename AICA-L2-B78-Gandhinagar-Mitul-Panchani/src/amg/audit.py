"""Hash-chained audit logging enforcing P0 rules 1 and 8.

P0 rule 1 keeps memory content out of audit detail. P0 rule 8 makes every
audit row tamper-evident by chaining its SHA-256 hash to the preceding row.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Final, Mapping

from amg.db import utc_now_iso
from amg.models import ChainVerification, EventType


GENESIS_HASH: Final[str] = "0" * 64
SAFE_DETAIL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "subject_key",
        "category",
        "source_type",
        "trust_tier",
        "assertion_type",
        "status",
        "content_sha256",
        "field_changed",
        "reason_code",
        "result_count",
        "top_k",
        "provider",
        "gate",
        "cascade_count",
        "dependent_ids",
        "was_dependent",
    }
)


class AuditDetailViolation(ValueError):
    """Raised when audit detail could contain unapproved information."""


def _event_type_value(event_type: EventType | str) -> str:
    return event_type.value if isinstance(event_type, EventType) else event_type


def _canonical_detail(detail: Mapping[str, object]) -> str:
    try:
        return json.dumps(detail, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise AuditDetailViolation("audit detail must be JSON-serializable") from exc


def compute_row_hash(
    event_type: EventType | str,
    memory_id: int | None,
    actor: str,
    timestamp: str,
    detail_json: str,
    prev_row_hash: str,
) -> str:
    """Compute one audit row's deterministic SHA-256 hash."""

    # Exact UTF-8 preimage: canonical JSON for this object, with keys sorted,
    # no whitespace, and memory_id represented as "" when SQL NULL. The
    # detail value is the already-canonical JSON string stored in the row.
    preimage = json.dumps(
        {
            "actor": actor,
            "detail": detail_json,
            "event_type": _event_type_value(event_type),
            "memory_id": "" if memory_id is None else memory_id,
            "prev_row_hash": prev_row_hash,
            "timestamp": timestamp,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()


def assert_detail_safe(detail: dict[str, object]) -> None:
    """Reject audit detail keys not explicitly approved as structural metadata."""

    disallowed_keys = set(detail) - SAFE_DETAIL_KEYS
    if disallowed_keys:
        names = ", ".join(sorted(disallowed_keys))
        raise AuditDetailViolation(f"disallowed audit detail key(s): {names}")
    _canonical_detail(detail)


def append_event(
    conn: sqlite3.Connection,
    event_type: EventType | str,
    actor: str,
    detail: dict[str, object],
    memory_id: int | None = None,
) -> int:
    """Append one safely filtered event and return its database row id."""

    assert_detail_safe(detail)
    detail_json = _canonical_detail(detail)
    event_type_value = _event_type_value(event_type)
    timestamp = utc_now_iso()
    owns_transaction = not conn.in_transaction

    try:
        # IMMEDIATE takes the write reservation before reading the chain tip,
        # preventing two connections from extending the same tip concurrently.
        if owns_transaction:
            conn.execute("BEGIN IMMEDIATE")
        previous = conn.execute(
            "SELECT row_hash FROM audit_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        prev_row_hash = previous["row_hash"] if previous is not None else GENESIS_HASH
        row_hash = compute_row_hash(
            event_type_value,
            memory_id,
            actor,
            timestamp,
            detail_json,
            prev_row_hash,
        )
        cursor = conn.execute(
            """
            INSERT INTO audit_log (
                event_type, memory_id, actor, timestamp, detail,
                prev_row_hash, row_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type_value,
                memory_id,
                actor,
                timestamp,
                detail_json,
                prev_row_hash,
                row_hash,
            ),
        )
        if owns_transaction:
            conn.commit()
    except Exception:
        if owns_transaction and conn.in_transaction:
            conn.rollback()
        raise

    if cursor.lastrowid is None:
        raise RuntimeError("SQLite did not return an audit row id")
    return int(cursor.lastrowid)


def verify_chain(conn: sqlite3.Connection) -> ChainVerification:
    """Verify hash linkage and row contents in ascending id order."""

    expected_prev_hash = GENESIS_HASH
    rows_checked = 0
    rows = conn.execute("SELECT * FROM audit_log ORDER BY id").fetchall()

    for row in rows:
        rows_checked += 1
        row_id = int(row["id"])
        if row["prev_row_hash"] != expected_prev_hash:
            return ChainVerification(
                valid=False,
                rows_checked=rows_checked,
                broken_at_row_id=row_id,
                reason="previous-row hash linkage does not match",
            )

        expected_row_hash = compute_row_hash(
            row["event_type"],
            row["memory_id"],
            row["actor"],
            row["timestamp"],
            row["detail"],
            row["prev_row_hash"],
        )
        if row["row_hash"] != expected_row_hash:
            return ChainVerification(
                valid=False,
                rows_checked=rows_checked,
                broken_at_row_id=row_id,
                reason="row hash does not match row contents",
            )
        expected_prev_hash = row["row_hash"]

    return ChainVerification(
        valid=True,
        rows_checked=rows_checked,
        broken_at_row_id=None,
        reason="audit chain is valid",
    )


def content_fingerprint(text: str) -> str:
    """Return a content hash without retaining the content itself."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()
