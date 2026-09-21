from __future__ import annotations

import re
from collections.abc import Mapping


TERMINAL_STATUS_PATTERN = re.compile(r"\b(delivered|completed|closed)\b", re.IGNORECASE)
NON_TERMINAL_QUALIFIERS = re.compile(r"\b(estimated|expected|planned|awaiting)\b", re.IGNORECASE)
NEGATED_TERMINAL_PATTERN = re.compile(r"\bnot\s+(?:yet\s+)?(?:delivered|completed|closed)\b", re.IGNORECASE)


def classify_container_state(tracking_result: Mapping) -> str:
    """Classify a tracking row for mutually exclusive dashboard KPIs."""
    if str(tracking_result.get("Tracking Result", "")).strip().casefold() != "success":
        return "Tracking Error"

    status = str(tracking_result.get("Current Status", "") or "").strip()
    if NON_TERMINAL_QUALIFIERS.search(status) or NEGATED_TERMINAL_PATTERN.search(status):
        return "In Transit"
    if TERMINAL_STATUS_PATTERN.search(status):
        return "Arrived / Completed"
    return "In Transit"
