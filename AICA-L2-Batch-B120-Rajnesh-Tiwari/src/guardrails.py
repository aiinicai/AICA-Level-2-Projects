"""Local pre-flight checks for the AuditSense demonstration app."""

from __future__ import annotations

import re
from collections.abc import Mapping


EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
LONG_NUMBER_PATTERN = re.compile(r"\b\d{12,}\b")
SENSITIVE_LABEL_PATTERN = re.compile(
    r"\b(customer|account|card|iban|passport|national id|emirates id)\s*(number|no\.?|id)\b",
    re.IGNORECASE,
)


def find_sensitive_looking_content(payload: Mapping[str, str]) -> list[str]:
    """Return warnings for obvious sensitive-looking patterns.

    This is a lightweight local check, not a data-loss-prevention system.
    """
    combined = "\n".join(str(value) for value in payload.values() if value)
    warnings: list[str] = []
    if EMAIL_PATTERN.search(combined):
        warnings.append("An email-address pattern was detected.")
    if LONG_NUMBER_PATTERN.search(combined):
        warnings.append("A long numeric identifier pattern was detected.")
    if SENSITIVE_LABEL_PATTERN.search(combined):
        warnings.append("A customer, account, card, or identity-number label was detected.")
    return warnings


def validate_review_input(payload: Mapping[str, str]) -> list[str]:
    """Return blocking local validation messages for the review request."""
    errors: list[str] = []
    required = {
        "title": "Finding title",
        "draft_observation": "Draft observation",
        "evidence": "Available evidence",
    }
    for key, label in required.items():
        if not str(payload.get(key, "")).strip():
            errors.append(f"{label} is required.")
    for key, value in payload.items():
        if len(str(value)) > 8000:
            errors.append(f"{key.replace('_', ' ').title()} is too long; keep it under 8,000 characters.")
    return errors
