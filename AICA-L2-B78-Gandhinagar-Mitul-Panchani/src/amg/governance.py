"""Policy engine enforcing governed writes, reads, exports, and deletion.

The write path delegates its maker/checker boundaries to ``memory_service``;
this module owns read-shape discrimination and the traversable export gate.
"""

from __future__ import annotations

import hmac
import re
from typing import Final

from amg.config import get_settings
from amg.models import GuardDecision, RequestShape
from amg.session import Session


EXTRACTION_ATTACK_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bignore\s+(?:all\s+)?(?:previous|prior)\b",
        r"\byou\s+are\s+now\b",
        r"\bdebug\s+mode\b",
        r"\bdeveloper\s+mode\b",
        r"\bprint\s+(?:the\s+)?(?:complete|entire|full|all)\b",
        r"\bdump\s+(?:(?:the|your)\s+)?(?:memory|store|database|everything)\b",
        r"\bno\s+filtering\b",
        r"\ball\s+rows\b",
        r"\bdisregard\s+(?:your\s+)?(?:instructions|rules)\b",
        r"\boverride\b",
        r"\breveal\s+everything\b",
        r"\bsystem\s*:",
    )
]

_LEGITIMATE_EXPORT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bshow\s+me\s+everything\s+you\s+have\s+on\s+me\b",
        r"\bwhat\s+(?:all\s+)?do\s+you\s+know\s+about\s+me\b",
        r"\b(?:full|complete)\s+(?:memory\s+)?export\b",
        r"\bexport\s+(?:all|everything|my\s+(?:data|memories))\b",
    )
)


def classify_request(text: str) -> RequestShape:
    """Distinguish gate-bypass framing from a legitimate broad access request."""

    # Breadth is not hostile. Override/bypass framing is checked first, while
    # a plain broad request is routed to the export gate. Blanket-refusing the
    # latter would defeat the access right that the gate exists to serve.
    if any(pattern.search(text) for pattern in EXTRACTION_ATTACK_PATTERNS):
        return RequestShape.UNSCOPED_DUMP_ATTEMPT
    if any(pattern.search(text) for pattern in _LEGITIMATE_EXPORT_PATTERNS):
        return RequestShape.LEGITIMATE_EXPORT_REQUEST
    return RequestShape.ORDINARY_QUERY


def guard_contextual_query(session: Session, text: str) -> GuardDecision:
    """Return a pure decision for a contextual request before any retrieval."""

    # Identity is part of the boundary even though this pure classifier does
    # not mutate session state.
    _ = session
    shape = classify_request(text)
    if shape is RequestShape.UNSCOPED_DUMP_ATTEMPT:
        return GuardDecision(
            allowed=False,
            shape=shape,
            reason="Instruction-override framing cannot bypass the export gate.",
            audit_event="access_denied",
        )
    # This guard is defense-in-depth. The independent structural top-k cap
    # still applies to every allowed contextual request.
    return GuardDecision(
        allowed=True,
        shape=shape,
        reason="Request may proceed through its bounded or gated path.",
    )


def confirm_export_gate(session: Session, passphrase: str) -> bool:
    """Re-check the fixed demo credential and mark a successful session gate."""

    settings = get_settings()
    candidate = passphrase if isinstance(passphrase, str) else ""
    passed = hmac.compare_digest(candidate, settings.export_passphrase)
    if passed:
        # This fixed phrase is not general-purpose authentication. It exists
        # so the prototype has a real, traversable gate instead of a policy
        # suggestion that callers could simply ignore.
        session.export_confirmed = True
    return passed
