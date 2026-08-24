"""Document quarantine — Module 12 (AI Safety / Zero-Trust Layer).

Uploaded annual reports and other documents are DATA. Text extracted
from them must never be allowed to silently become instructions for
any downstream AI step (Layer 5). This module implements the one
mechanical control this codebase applies before document text is
allowed anywhere near a prompt: pattern-based detection of
instruction-like content, with the matched spans neutralized in place
rather than the whole page being silently dropped (dropping would lose
legitimate surrounding content; silently passing it through would be
the exact failure this module exists to prevent).

This is a best-effort, pattern-level control, not a guarantee. The
authoritative defense is structural, applied at the prompt-construction
layer (app/ai/prompts.py, Milestone 6): document text is always passed
to the LLM as clearly-delimited data, never concatenated into system
instructions. This module is a second, defense-in-depth layer on top
of that — it should not be relied upon as the sole safeguard.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_NEUTRALIZED_MARKER = "[QUARANTINED: instruction-like content removed]"

# Pattern-level detection only. Each pattern targets a *structural* shape
# (an imperative addressed at an AI system, a request to override prior
# instructions, a fake role/system-boundary marker) rather than specific
# wording, so paraphrases are still caught. False positives are expected
# and acceptable here — the cost of over-flagging ordinary business text
# is far lower than the cost of missing a real injection attempt.
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bignore\s+(all\s+)?(the\s+)?(above|previous|prior)\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\bdisregard\s+(all\s+)?(the\s+)?(above|previous|prior)\b", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\s+(a|an)\b", re.IGNORECASE),
    re.compile(r"\bnew\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"\bsystem\s+prompt\s*:", re.IGNORECASE),
    re.compile(r"^\s*(assistant|ai|system)\s*:\s*", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\bact\s+as\s+(if\s+you\s+are\s+)?(a|an)\b.{0,40}\b(ai|assistant|chatbot|model)\b", re.IGNORECASE),
    re.compile(r"\boverride\s+(your|all)\s+(prior\s+)?(instructions?|guidelines?|rules?)\b", re.IGNORECASE),
    re.compile(r"\bdo\s+not\s+(follow|apply)\s+(your|the)\s+(safety\s+)?(guidelines?|instructions?|rules?)\b", re.IGNORECASE),
    re.compile(r"\breveal\s+your\s+(system\s+prompt|instructions)\b", re.IGNORECASE),
]


@dataclass(frozen=True)
class QuarantineResult:
    sanitized_text: str
    flagged: bool
    match_count: int


def scan_and_quarantine(text: str) -> QuarantineResult:
    """Scan `text` for instruction-like patterns and neutralize any
    matches in place.

    Returns the (possibly modified) text alongside a flag and count —
    callers (source_tracker.py) attach this to DocumentEvidence so a
    flagged excerpt remains visible/auditable rather than silently
    altered with no trace.
    """
    if not text:
        return QuarantineResult(sanitized_text=text, flagged=False, match_count=0)

    sanitized = text
    total_matches = 0
    for pattern in _INJECTION_PATTERNS:
        sanitized, n = pattern.subn(_NEUTRALIZED_MARKER, sanitized)
        total_matches += n

    if total_matches:
        logger.warning(
            "Quarantine: neutralized %d instruction-like pattern(s) in document text.",
            total_matches,
        )

    return QuarantineResult(
        sanitized_text=sanitized, flagged=total_matches > 0, match_count=total_matches,
    )
