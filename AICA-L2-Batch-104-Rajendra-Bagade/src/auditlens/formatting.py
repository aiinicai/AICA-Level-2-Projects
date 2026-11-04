"""
Indian number formatting.

Amounts in an Indian workpaper are grouped in the lakh/crore convention --
5,00,00,000 rather than 50,000,000 -- and a report that gets this wrong
reads as foreign to every user of it.
"""

from __future__ import annotations


def inr(amount: float | int | None, *, decimals: int = 2, prefix: str = "") -> str:
    """Format a number in the Indian digit grouping convention.

    >>> inr(50000000)
    '5,00,00,000.00'
    >>> inr(-125000, decimals=0, prefix="Rs ")
    'Rs -1,25,000'
    """
    if amount is None:
        return "-"

    negative = amount < 0
    whole, _, fraction = f"{abs(float(amount)):.{decimals}f}".partition(".")

    # The last three digits group together; everything before them in twos.
    if len(whole) > 3:
        last_three = whole[-3:]
        rest = whole[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        grouped = ",".join(groups) + "," + last_three
    else:
        grouped = whole

    out = grouped + (f".{fraction}" if fraction else "")
    return f"{prefix}{'-' if negative else ''}{out}"


def in_lakhs(amount: float | None, decimals: int = 2) -> str:
    """Express an amount in lakhs, as management accounts usually do."""
    if amount is None:
        return "-"
    return f"{amount / 1_00_000:,.{decimals}f} lakh"


def in_crores(amount: float | None, decimals: int = 2) -> str:
    if amount is None:
        return "-"
    return f"{amount / 1_00_00_000:,.{decimals}f} crore"


def compact(amount: float | None) -> str:
    """Pick the unit a reader would use out loud for this magnitude."""
    if amount is None:
        return "-"
    magnitude = abs(amount)
    if magnitude >= 1_00_00_000:
        return f"Rs {in_crores(amount)}"
    if magnitude >= 1_00_000:
        return f"Rs {in_lakhs(amount)}"
    return inr(amount, decimals=0, prefix="Rs ")
