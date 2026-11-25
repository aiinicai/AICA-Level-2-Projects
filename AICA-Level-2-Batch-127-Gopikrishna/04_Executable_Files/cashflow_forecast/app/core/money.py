"""Money helpers.

All amounts are ``Decimal``. In the database they are stored as INTEGER minor units
(1 OMR = 1,000 baisa), which makes sums exact and lets SQLite compare them safely.
Rounding is ROUND_HALF_UP to the currency's decimals, done in one place.
"""
from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

DEFAULT_DECIMALS = 3
_THOUSANDS = re.compile(r"[+-]?\d{1,3}(,\d{3})+(\.\d*)?")


def _quantum(decimals: int) -> Decimal:
    return Decimal(1).scaleb(-decimals)


def to_decimal(value) -> Decimal:
    """Parse numbers from Excel/CSV/forms: handles None, '', '1,234.500', '(12.000)'."""
    if value is None:
        return Decimal(0)
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise ValueError("boolean is not an amount")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(repr(value))
    text = str(value).strip().replace(" ", "")
    if text in ("", "-"):
        return Decimal(0)
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    if "," in text:
        # commas are thousands separators only: '1,234.500' yes; '1.234,5' or '12,34' no
        if not _THOUSANDS.fullmatch(text):
            raise ValueError(f"not a valid amount: {value!r} (use '.' for decimals, ',' for thousands)")
        text = text.replace(",", "")
    try:
        d = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"not a valid amount: {value!r}") from exc
    return -d if negative else d


def round_money(value, decimals: int = DEFAULT_DECIMALS) -> Decimal:
    return to_decimal(value).quantize(_quantum(decimals), rounding=ROUND_HALF_UP)


def to_minor(value, decimals: int = DEFAULT_DECIMALS) -> int:
    """Decimal amount -> integer minor units (baisa for OMR)."""
    return int(round_money(value, decimals).scaleb(decimals))


def from_minor(minor: int | None, decimals: int = DEFAULT_DECIMALS) -> Decimal:
    if minor is None:
        return Decimal(0).quantize(_quantum(decimals))
    return Decimal(int(minor)).scaleb(-decimals).quantize(_quantum(decimals))


def fmt_money(value, decimals: int = DEFAULT_DECIMALS) -> str:
    """'1234.5' -> '1,234.500'; negatives shown with a leading minus."""
    return f"{round_money(value, decimals):,.{decimals}f}"
