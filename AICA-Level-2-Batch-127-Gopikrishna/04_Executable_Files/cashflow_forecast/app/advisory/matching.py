"""Fuzzy matching (rapidfuzz) for headers and category names. Advisory only: it suggests, a user decides.

Plain WRatio over-scores very short choices (e.g. 'Rent' scored 67.5 against 'Marketing campaign'
because of partial matching). So choices shorter than SHORT_LEN characters are scored with plain
``ratio`` (whole-string similarity) instead.
"""
from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz, utils

SHORT_LEN = 6
SUGGEST_MIN = 70      # below this no suggestion is shown
AUTO_COLUMN_MIN = 92  # column headers (not categories) at or above this are mapped with a warning


@dataclass(frozen=True)
class Suggestion:
    target: object       # e.g. a category id or a column key
    matched_text: str    # the name / alias that matched
    score: float


def score(query: str, choice: str) -> float:
    q, c = utils.default_process(query), utils.default_process(choice)
    if not q or not c:
        return 0.0
    if len(c) < SHORT_LEN or len(q) < SHORT_LEN:
        return float(fuzz.ratio(q, c))
    return float(max(fuzz.WRatio(q, c), fuzz.token_set_ratio(q, c) - 5))


def best_match(query: str, choices: dict[str, object], minimum: float = SUGGEST_MIN) -> Suggestion | None:
    """choices: {text: target}. Returns the best target at or above ``minimum``."""
    best: Suggestion | None = None
    for text, target in choices.items():
        s = score(query, text)
        if best is None or s > best.score:
            best = Suggestion(target, text, round(s, 1))
    return best if best and best.score >= minimum else None
