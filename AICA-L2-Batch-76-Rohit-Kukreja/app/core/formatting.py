"""Indian numbering and date conventions. Build Prompt v2 §12.

This is the *only* place these are implemented. The database stores numeric
values and raw dates; formatting happens here, on the way out. The prototype
stored the FY end date as free text and interpolated it verbatim into 34
sentences, which is why every one of them had to be corrected by hand.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

RUPEE = "₹"


class DateStyle(StrEnum):
    """How dates render. A firm setting, not a per-document choice."""

    UI = "ui"  # 15-Aug-2026
    LONG = "long"  # 31st March, 2025
    NUMERIC = "numeric"  # 31.03.2025


class AmountsIn(StrEnum):
    """Drives the unit caption and the divisor."""

    UNITS = "units"
    THOUSANDS = "thousands"
    LAKHS = "lakhs"
    CRORES = "crores"


_DIVISOR: dict[AmountsIn, int] = {
    AmountsIn.UNITS: 1,
    AmountsIn.THOUSANDS: 1_000,
    AmountsIn.LAKHS: 100_000,
    AmountsIn.CRORES: 10_000_000,
}

_CAPTION: dict[AmountsIn, str] = {
    AmountsIn.UNITS: "",
    AmountsIn.THOUSANDS: "Thousands",
    AmountsIn.LAKHS: "Lakhs",
    AmountsIn.CRORES: "Crores",
}

_MONTHS: tuple[str, ...] = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


# --------------------------------------------------------------------------
# Numbers
# --------------------------------------------------------------------------


def group_indian(value: Decimal | int | str) -> str:
    """Lakh/crore grouping: 12543000 -> '1,25,43,000'.

    Western grouping would give '12,543,000', which is wrong in every Indian
    statutory document.
    """
    amount = Decimal(str(value))
    negative = amount < 0
    quantised = abs(amount).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    digits = str(quantised)

    if len(digits) <= 3:
        grouped = digits
    else:
        last_three = digits[-3:]
        rest = digits[:-3]
        parts: list[str] = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        grouped = ",".join([*parts, last_three])

    return f"-{grouped}" if negative else grouped


def rupees(value: Decimal | int | str, *, symbol: bool = True) -> str:
    """`₹1,25,43,000`."""
    grouped = group_indian(value)
    return f"{RUPEE}{grouped}" if symbol else grouped


def unit_caption(amounts_in: AmountsIn) -> str:
    """`Amount in ₹ Lakhs`, or an empty string when amounts are in units."""
    caption = _CAPTION[amounts_in]
    return f"Amount in {RUPEE} {caption}" if caption else f"Amount in {RUPEE}"


def scale(value: Decimal | int | str, amounts_in: AmountsIn) -> Decimal:
    """Divide by the reporting unit. Rounds to two places."""
    amount = Decimal(str(value)) / _DIVISOR[amounts_in]
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


_ONES: tuple[str, ...] = (
    "",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Eleven",
    "Twelve",
    "Thirteen",
    "Fourteen",
    "Fifteen",
    "Sixteen",
    "Seventeen",
    "Eighteen",
    "Nineteen",
)
_TENS: tuple[str, ...] = (
    "",
    "",
    "Twenty",
    "Thirty",
    "Forty",
    "Fifty",
    "Sixty",
    "Seventy",
    "Eighty",
    "Ninety",
)


def _under_hundred(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (f" {_ONES[ones]}" if ones else "")


def _under_thousand(n: int) -> str:
    hundreds, rest = divmod(n, 100)
    parts: list[str] = []
    if hundreds:
        parts.append(f"{_ONES[hundreds]} Hundred")
    if rest:
        parts.append(_under_hundred(rest))
    return " ".join(parts)


def in_words(value: Decimal | int | str, *, prefix: str = "Rupees") -> str:
    """`Rupees One Crore Twenty Five Lakh Forty Three Thousand Only`.

    Uses the Indian scale — crore, lakh, thousand — not million/billion.
    """
    amount = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    negative = amount < 0
    n = int(abs(amount))

    if n == 0:
        return f"{prefix} Zero Only"

    crore, rest = divmod(n, 10_000_000)
    lakh, rest = divmod(rest, 100_000)
    thousand, hundreds = divmod(rest, 1_000)

    parts: list[str] = []
    if crore:
        parts.append(f"{_under_thousand(crore)} Crore")
    if lakh:
        parts.append(f"{_under_hundred(lakh)} Lakh")
    if thousand:
        parts.append(f"{_under_hundred(thousand)} Thousand")
    if hundreds:
        parts.append(_under_thousand(hundreds))

    words = " ".join(parts)
    sign = "Minus " if negative else ""
    return f"{prefix} {sign}{words} Only"


# --------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------


def _ordinal(day: int) -> str:
    if 11 <= day <= 13:
        return f"{day}th"
    return f"{day}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th') }"


def format_date(value: date, style: DateStyle = DateStyle.UI) -> str:
    match style:
        case DateStyle.UI:
            return f"{value.day:02d}-{_MONTHS[value.month - 1][:3]}-{value.year}"
        case DateStyle.LONG:
            return f"{_ordinal(value.day)} {_MONTHS[value.month - 1]}, {value.year}"
        case DateStyle.NUMERIC:
            return f"{value.day:02d}.{value.month:02d}.{value.year}"


def financial_year(fy_end: date) -> str:
    """`FY 2025-26` from a 31 March year end."""
    start_year = fy_end.year - 1 if fy_end.month <= 3 else fy_end.year
    return f"FY {start_year}-{str(start_year + 1)[-2:]}"


def fy_end_from_start_year(start_year: int) -> date:
    """31 March of the following calendar year."""
    return date(start_year + 1, 3, 31)
