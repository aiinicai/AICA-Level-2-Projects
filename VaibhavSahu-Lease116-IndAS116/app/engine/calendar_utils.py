"""Calendar arithmetic for lease accounting.

Conventions used by the engine
------------------------------
* A *date* used as a point in time means the START of that day.
* A period that "ends" on date E (inclusive) closes at the start of E + 1 day.
* Month arithmetic always works from an anchor date so that anniversaries do not
  drift (31-Jan + 1 month = 28/29-Feb, + 2 months = 31-Mar).
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterator

ONE_DAY = timedelta(days=1)


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def add_months(anchor: date, months: int) -> date:
    """Add whole months to an anchor date, clamping to month-end where needed."""
    total = anchor.year * 12 + (anchor.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    day = min(anchor.day, days_in_month(year, month))
    return date(year, month, day)


def add_months_eom(anchor: date, months: int) -> date:
    """Add months; if anchor is a month-end the result is the month-end too."""
    res = add_months(anchor, months)
    if anchor.day == days_in_month(anchor.year, anchor.month):
        return month_end(res)
    return res


def month_end(d: date) -> date:
    return date(d.year, d.month, days_in_month(d.year, d.month))


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def next_day(d: date) -> date:
    return d + ONE_DAY


def prev_day(d: date) -> date:
    return d - ONE_DAY


def days_between(a: date, b: date) -> int:
    return (b - a).days


def whole_months_between(origin: date, d: date) -> int:
    """Largest w with add_months(origin, w) <= d (w may be negative)."""
    w = (d.year - origin.year) * 12 + (d.month - origin.month)
    # adjust so that add_months(origin, w) <= d < add_months(origin, w+1)
    while add_months(origin, w) > d:
        w -= 1
    while add_months(origin, w + 1) <= d:
        w += 1
    return w


def months_between_frac(origin: date, d: date) -> Decimal:
    """Fractional months from origin to d: whole months + remaining days / days in that month-period."""
    w = whole_months_between(origin, d)
    start = add_months(origin, w)
    nxt = add_months(origin, w + 1)
    span = (nxt - start).days
    rem = (d - start).days
    return Decimal(w) + (Decimal(rem) / Decimal(span) if span else Decimal(0))


def month_ends_between(start: date, end: date) -> list[date]:
    """All month-end dates E with start <= E <= end."""
    out = []
    cur = month_end(start)
    while cur <= end:
        out.append(cur)
        cur = month_end(cur + ONE_DAY)
    return out


def period_ends_between(start: date, end: date, months_per_period: int = 1, fy_start_month: int = 4) -> list[date]:
    """Reporting period ends (monthly / quarterly / half-yearly / annual aligned to FY)."""
    ends = month_ends_between(start, end)
    if months_per_period == 1:
        return ends
    out = []
    for e in ends:
        offset = (e.month - fy_start_month) % 12  # 0 for first month of FY
        if (offset + 1) % months_per_period == 0:
            out.append(e)
    if ends and (not out or out[-1] != ends[-1]) and ends[-1] == end:
        out.append(ends[-1])
    return out


def fy_of(d: date, fy_start_month: int = 4) -> tuple[date, date]:
    """Financial year containing d (Indian FY April–March by default)."""
    if d.month >= fy_start_month:
        start = date(d.year, fy_start_month, 1)
    else:
        start = date(d.year - 1, fy_start_month, 1)
    end = add_months(start, 12) - ONE_DAY
    return start, end


def fy_label(d: date, fy_start_month: int = 4) -> str:
    s, e = fy_of(d, fy_start_month)
    if fy_start_month == 1:
        return f"CY {s.year}"
    return f"FY {s.year}-{str(e.year)[-2:]}"


def iter_days(a: date, b: date) -> Iterator[date]:
    cur = a
    while cur < b:
        yield cur
        cur += ONE_DAY


def month_weight(a: date, b: date) -> Decimal:
    """Weight of the half-open interval [a, b) in 'months', each calendar month = 1
    split pro-rata by days. Used for the equal-monthly depreciation convention."""
    if b <= a:
        return Decimal(0)
    total = Decimal(0)
    cur = a
    while cur < b:
        me_next = month_end(cur) + ONE_DAY  # start of next month
        seg_end = min(me_next, b)
        dim = days_in_month(cur.year, cur.month)
        total += Decimal((seg_end - cur).days) / Decimal(dim)
        cur = seg_end
    return total


def parse_date(value) -> date | None:
    """Accept date / ISO string / DD-MM-YYYY / DD/MM/YYYY (Indian format)."""
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if "T" in s:
        s = s.split("T", 1)[0]
    for sep in ("-", "/", "."):
        parts = s.split(sep)
        if len(parts) == 3:
            a, b, c = parts
            try:
                if len(a) == 4:  # ISO yyyy-mm-dd
                    return date(int(a), int(b), int(c))
                if len(c) == 4:  # dd-mm-yyyy (Indian)
                    return date(int(c), int(b), int(a))
                if len(c) == 2:  # dd-mm-yy
                    return date(2000 + int(c), int(b), int(a))
            except ValueError:
                return None
    raise ValueError(f"Unrecognised date: {value!r}")
