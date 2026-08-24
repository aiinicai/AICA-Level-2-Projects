"""Retrieval boundary enforcing P0 rules 4 and 5.

P0 rule 4 hard-caps contextual retrieval with no full-store code path. P0
rule 5 keeps full export in a separate operation reachable only through the
confirmation gate; combining these operations behind a flag would create the
back door that this boundary exists to prevent.
"""

from __future__ import annotations

import json
import math
import sqlite3

from amg import audit, governance
from amg.config import get_settings
from amg.models import (
    ContextualResult,
    EventType,
    ExportResult,
    Memory,
    ProviderUse,
    RetrievalHit,
    SourceType,
    TrustTier,
)
from amg.providers import get_embedding_provider, last_provider_report
from amg.session import Session


def _trust_tier(source_type: str, confirmed_at: str | None) -> TrustTier:
    if source_type == SourceType.USER_STATED.value:
        return TrustTier.STATED
    if confirmed_at is not None:
        return TrustTier.CONFIRMED_INFERENCE
    return TrustTier.UNCONFIRMED_INFERENCE


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    """Show the complete brute-force cosine calculation in plain Python."""

    if len(left) != len(right):
        raise ValueError("stored and query embedding dimensions do not match")
    dot_product = sum(a * b for a, b in zip(left, right, strict=True))
    left_magnitude = math.sqrt(sum(value * value for value in left))
    right_magnitude = math.sqrt(sum(value * value for value in right))
    if left_magnitude == 0.0 or right_magnitude == 0.0:
        return 0.0
    similarity = dot_product / (left_magnitude * right_magnitude)
    # Floating-point roundoff can put mathematically exact matches a few ulps
    # outside cosine's [-1, 1] range.
    return max(-1.0, min(1.0, similarity))


def _provider_use() -> ProviderUse | None:
    report = last_provider_report().get("embedding_query")
    return ProviderUse.model_validate(report) if report is not None else None


def contextual_retrieve(
    conn: sqlite3.Connection,
    session: Session,
    query: str,
) -> ContextualResult:
    """Return only the configured small contextual slice of live memories."""

    decision = governance.guard_contextual_query(session, query)
    if not decision.allowed:
        audit_id = audit.append_event(
            conn,
            EventType.ACCESS_DENIED,
            session.actor,
            {"gate": "contextual_query_guard"},
        )
        return ContextualResult(
            allowed=False,
            hits=[],
            reason=decision.reason,
            audit_row_id=audit_id,
        )

    settings = get_settings()
    provider = get_embedding_provider()
    query_vector = provider.embed_query(query)
    provider_use = _provider_use()
    rows = conn.execute(
        """
        SELECT m.*, e.vector
        FROM memories AS m
        JOIN embeddings AS e ON e.id = m.embedding_id
        WHERE m.status NOT IN ('deleted', 'superseded')
        """
    ).fetchall()
    scored: list[RetrievalHit] = []
    for row in rows:
        stored_vector = json.loads(str(row["vector"]))
        similarity = _cosine_similarity(query_vector, stored_vector)
        memory_data = {key: row[key] for key in row.keys() if key != "vector"}
        scored.append(
            RetrievalHit(
                **memory_data,
                trust_tier=_trust_tier(
                    str(row["source_type"]), row["confirmed_at"]
                ),
                similarity=similarity,
            )
        )
    scored.sort(key=lambda hit: (-hit.similarity, hit.id))

    # The absence of a size parameter is the enforcement: callers cannot ask
    # for more than this settings-owned cap because there is no way to express
    # an override. Slicing happens here, inside the security boundary.
    hits = scored[: settings.contextual_top_k]
    provider_name = (
        provider_use.provider_name if provider_use else provider.model_version
    )
    audit_id = audit.append_event(
        conn,
        EventType.CONTEXTUAL_READ,
        session.actor,
        {
            "result_count": len(hits),
            "top_k": settings.contextual_top_k,
            "provider": provider_name,
        },
    )
    return ContextualResult(
        allowed=True,
        hits=hits,
        reason="Bounded contextual retrieval completed.",
        provider=provider_use,
        audit_row_id=audit_id,
    )


def full_export(
    conn: sqlite3.Connection,
    session: Session,
    passphrase: str,
) -> ExportResult:
    """Return the complete live record only after the explicit export gate."""

    if not governance.confirm_export_gate(session, passphrase):
        audit_id = audit.append_event(
            conn,
            EventType.ACCESS_DENIED,
            session.actor,
            {"gate": "export_passphrase"},
        )
        return ExportResult(
            succeeded=False,
            memories=[],
            reason="The export passphrase was not confirmed.",
            audit_row_id=audit_id,
        )

    rows = conn.execute(
        """
        SELECT *
        FROM memories
        WHERE status NOT IN ('deleted', 'superseded')
        ORDER BY id
        """
    ).fetchall()
    memories = [Memory.model_validate(dict(row)) for row in rows]
    audit_id = audit.append_event(
        conn,
        EventType.FULL_EXPORT,
        session.actor,
        {"result_count": len(memories)},
    )
    # This successful branch is required for the Section 11 access right; a
    # gate that could only refuse would be a compliance failure of its own.
    return ExportResult(
        succeeded=True,
        memories=memories,
        reason="The confirmed full export completed.",
        audit_row_id=audit_id,
    )
