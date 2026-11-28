"""Money helpers. Always Decimal, never float."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

TWO = Decimal("0.01")


def to_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        text = str(value).replace(",", "").replace("\u20b9", "").strip()
        return Decimal(text).quantize(TWO, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None


def format_inr(value: Decimal | None) -> str:
    """Indian digit grouping: 12,34,567.89"""
    if value is None:
        return ""
    q = Decimal(value).quantize(TWO, rounding=ROUND_HALF_UP)
    sign = "-" if q < 0 else ""
    integer, frac = f"{abs(q):.2f}".split(".")
    if len(integer) > 3:
        head, tail = integer[:-3], integer[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        integer = ",".join(groups + [tail])
    return f"{sign}{integer}.{frac}"
