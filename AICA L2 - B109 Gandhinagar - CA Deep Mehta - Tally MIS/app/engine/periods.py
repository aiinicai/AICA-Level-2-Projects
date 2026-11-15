"""Date and period helpers (ported from shared/periods.ts). Dates are ISO 'YYYY-MM-DD' strings."""
from __future__ import annotations

import calendar
import math
import re
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple


class DateRange(NamedTuple):
    from_: str
    to: str


def rng(frm: str, to: str) -> DateRange:
    return DateRange(frm, to)


def js_round(x: float) -> int:
    """JavaScript Math.round: halves round up (towards +infinity), unlike Python's banker's rounding."""
    return math.floor(x + 0.5)


def js_to_fixed(x: float, digits: int = 0) -> str:
    """JavaScript Number.toFixed: exact binary value, ties go to the larger number."""
    q = Decimal(1).scaleb(-digits)
    return str(Decimal(x).quantize(q, rounding=ROUND_HALF_UP))


def to_iso(y: int, m: int, d: int) -> str:
    return f"{y:04d}-{m:02d}-{d:02d}"


def parse_iso(s: str) -> tuple[int, int, int]:
    y, m, d = s.split("-")
    return int(y), int(m), int(d)


def is_valid_iso(s: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s or ""):
        return False
    y, m, d = parse_iso(s)
    return 1 <= m <= 12 and 1 <= d <= calendar.monthrange(y, m)[1]


def days_in_month(y: int, m: int) -> int:
    return calendar.monthrange(y, m)[1]


def add_days(iso: str, n: int) -> str:
    return (date.fromisoformat(iso) + timedelta(days=n)).isoformat()


def add_months(iso: str, n: int) -> str:
    y, m, d = parse_iso(iso)
    idx = y * 12 + (m - 1) + n
    ny, nm = idx // 12, idx % 12 + 1
    return to_iso(ny, nm, min(d, days_in_month(ny, nm)))


def days_between(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def range_days(r: DateRange) -> int:
    return days_between(r[0], r[1]) + 1


def month_start(iso: str) -> str:
    y, m, _ = parse_iso(iso)
    return to_iso(y, m, 1)


def month_end(iso: str) -> str:
    y, m, _ = parse_iso(iso)
    return to_iso(y, m, days_in_month(y, m))


class FY(NamedTuple):
    from_: str
    to: str
    label: str
    start_year: int


def fy_of(iso: str, start_month: int = 4) -> FY:
    y, m, _ = parse_iso(iso)
    sy = y if m >= start_month else y - 1
    frm = to_iso(sy, start_month, 1)
    to = add_days(add_months(frm, 12), -1)
    label = f"{sy}" if start_month == 1 else f"FY {sy}-{(sy + 1) % 100:02d}"
    return FY(frm, to, label, sy)


def months_in(r: DateRange) -> list[str]:
    out, cur = [], month_start(r[0])
    while cur <= r[1]:
        out.append(cur)
        cur = add_months(cur, 1)
    return out


_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def month_label(iso: str) -> str:
    y, m, _ = parse_iso(iso)
    return f"{_MON[m - 1]} {str(y)[2:]}"


def fy_quarter(iso: str, start_month: int = 4) -> int:
    _, m, _ = parse_iso(iso)
    return ((m - start_month + 12) % 12) // 3 + 1


def _whole_months(r: DateRange) -> bool:
    return r[0] == month_start(r[0]) and r[1] == month_end(r[1])


def previous_period(r: DateRange) -> DateRange:
    if _whole_months(r):
        n = len(months_in(r))
        return DateRange(add_months(r[0], -n), month_end(add_months(r[0], -1)))
    ln = range_days(r)
    return DateRange(add_days(r[0], -ln), add_days(r[0], -1))


def previous_year(r: DateRange) -> DateRange:
    whole = _whole_months(r)
    return DateRange(add_months(r[0], -12), month_end(add_months(r[1], -12)) if whole else add_months(r[1], -12))


def comparison_range(r: DateRange, mode: str) -> DateRange | None:
    if mode == "none":
        return None
    return previous_year(r) if mode == "previous_year" else previous_period(r)
