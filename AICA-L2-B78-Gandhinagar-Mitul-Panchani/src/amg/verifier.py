"""Write verification enforcing P0 rule 3: checker context isolation."""

from __future__ import annotations

import re

from amg.config import get_settings
from amg.models import CandidateFact, CheckerReasonCode, CheckerVerdict
from amg.providers import get_llm_provider


_STRICT_ONLY_SCREEN = re.compile(
    r"^\s*(?:developer|assistant)\s*:|\bact\s+as\b|\b(?:reveal|dump|exfiltrate)\b.*\b(?:memory|data|store)\b",
    re.IGNORECASE,
)


def verify_candidate(candidate: CandidateFact) -> CheckerVerdict:
    """Verify a candidate without exposing its originating conversation turn."""

    # Strict mode intentionally expands the local screen. Balanced mode leaves
    # emphatic but genuine wording ("remember this: I'm...") to the independent
    # checker instead of treating emphasis as an attack.
    if (
        get_settings().checker_strictness == "strict"
        and _STRICT_ONLY_SCREEN.search(candidate.content)
    ):
        return CheckerVerdict(
            approved=False,
            reason_code=CheckerReasonCode.INSTRUCTION_SHAPED,
            notes="Strict mode rejected broader directive-shaped language.",
        )

    # Passing the original message here would silently destroy the independent
    # second-check property. Only these three candidate fields may cross the
    # call; inference parent text is intentionally excluded too.
    return get_llm_provider().check_candidate(
        candidate.content,
        candidate.assertion_type,
        candidate.source_type,
    )
