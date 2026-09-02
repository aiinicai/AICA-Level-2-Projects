"""
Paise <-> rupee conversion (Blueprint Correction #7).

Every monetary field in the schema is stored as `INTEGER` paise. This
module is the one place that translates between that storage format and
what a human types into / reads from a form — no other module should
do its own rupee-paise arithmetic.

Pure functions, no Flask/SQLAlchemy dependency, so they're directly
unit-testable.
"""
from __future__ import annotations

import re

_ALLOWED_INPUT_CHARS = re.compile(r"[^0-9.]")


class CurrencyParseError(ValueError):
    """Raised when a form value cannot be parsed as a rupee amount."""


def rupees_to_paise(raw_value) -> int | None:
    """Parse a rupee amount (string, int, or float) into integer paise.

    Accepts common Indian-CA-friendly input: plain numbers, comma
    thousands/lakh separators ("12,34,567.89"), a leading currency
    symbol, or surrounding whitespace. Blank / None input returns None
    (meaning "not provided" — these fields are nullable per Section
    2.13, not defaulted to zero). Negative amounts are rejected — none
    of the fields this feeds (turnover, materiality) are meaningfully
    negative, and a negative value more likely indicates a data-entry
    mistake, or later a validation gap in Data Quality would need to
    catch it separately.
    """
    if raw_value is None:
        return None
    if isinstance(raw_value, (int, float)):
        text = str(raw_value)
    else:
        text = str(raw_value).strip()
    if text == "":
        return None

    text = text.replace("₹", "").replace(",", "").strip()
    if not _ALLOWED_INPUT_CHARS.sub("", text) == text:
        raise CurrencyParseError(f"Not a valid rupee amount: {raw_value!r}")
    if text.count(".") > 1:
        raise CurrencyParseError(f"Not a valid rupee amount: {raw_value!r}")

    try:
        rupees = float(text)
    except ValueError as exc:
        raise CurrencyParseError(f"Not a valid rupee amount: {raw_value!r}") from exc

    if rupees < 0:
        raise CurrencyParseError(f"Amount must not be negative: {raw_value!r}")

    # Round to the nearest paisa before converting to avoid float drift
    # (e.g. 19.99 * 100 landing on 1998.9999999999998).
    return round(rupees * 100)


def paise_to_rupees_float(paise: int | None) -> float | None:
    """Raw float rupee value — used to prefill form inputs, not display."""
    if paise is None:
        return None
    return paise / 100


def paise_to_display(paise: int | None, *, blank: str = "—") -> str:
    """Format paise as an Indian-grouped rupee string, e.g. 123456789
    paise -> "₹12,34,567.89". Returns `blank` for None (nullable
    fields must never silently render as "₹0.00" — that would claim a
    figure that was never entered)."""
    if paise is None:
        return blank

    negative = paise < 0
    rupees, remainder_paise = divmod(abs(paise), 100)
    integer_part = _indian_group(str(rupees))
    formatted = f"₹{integer_part}.{remainder_paise:02d}"
    return f"-{formatted}" if negative else formatted


def _indian_group(digits: str) -> str:
    """Group a non-negative integer's digit string Indian-style: last 3
    digits, then groups of 2 (e.g. "1234567" -> "12,34,567")."""
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail
