"""Maker extraction enforcing P0 rule 2: current direct user text is its only input."""

from __future__ import annotations

from amg.models import CandidateFact
from amg.providers import get_llm_provider


def propose_candidates(user_text: str) -> list[CandidateFact]:
    """Propose memory candidates from exactly one direct user turn."""

    # This narrow signature IS the enforcement mechanism: there is no parameter
    # through which retrieved memories, session history, or tool output can reach
    # the maker.
    return get_llm_provider().extract_candidates(user_text)
