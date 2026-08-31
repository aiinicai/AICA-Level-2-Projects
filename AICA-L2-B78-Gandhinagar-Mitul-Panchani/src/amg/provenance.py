"""Provenance and trust tagging after independent checker approval."""

from __future__ import annotations

import re

from amg.models import (
    AssertionType,
    CandidateFact,
    SourceType,
    TaggedFact,
    TrustTier,
)


def tag(candidate: CandidateFact) -> TaggedFact:
    """Normalize subject/provenance fields and calculate the initial trust tier."""

    # Provenance is the maker's explicit claim, not something reconstructed
    # indirectly from assertion shape or optional parent metadata.
    source_type = candidate.source_type
    confirmed_at = getattr(candidate, "confirmed_at", None)
    if source_type is SourceType.USER_STATED:
        trust_tier = TrustTier.STATED
    elif confirmed_at is not None:
        trust_tier = TrustTier.CONFIRMED_INFERENCE
    else:
        trust_tier = TrustTier.UNCONFIRMED_INFERENCE

    return TaggedFact(
        content=candidate.content.strip(),
        subject_key=_snake_case(candidate.subject_key),
        category=candidate.category.strip().casefold(),
        assertion_type=AssertionType(candidate.assertion_type),
        source_type=source_type,
        inferred_from_content=candidate.inferred_from_content,
        confirmed_at=confirmed_at,
        trust_tier=trust_tier,
    )


def _snake_case(value: str) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value.strip())
    normalized = re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")
    return normalized or "general"
