"""Lot calendar.

month_thirds (default): each period is split into lots of ``lot_length_days``, the last lot running to
the period end. A period is a calendar month, or - with an anchor date - runs from the anchor's day in
one month to the day before it in the next (anchor day 5: 5 Nov-4 Dec, lots 5-14, 15-24, 25 Nov-4 Dec).
The number of lots per period is ``30 // lot_length_days`` so every period has the same number of lots
(10 -> 3, 7 -> 4, 15 -> 2). The horizon runs from the current period to the end of period
``horizon_months - 1`` after it.

fixed_days: consecutive lots of ``lot_length_days`` days, ignoring month ends, starting on the anchor
date (repeating every lot length before and after it) or, without an anchor, on the 1st of the as-of
month. The horizon is ``horizon_lots`` lots from the current lot.

Lots that end before the as-of date are ACTUAL (locked). The lot containing the as-of date is CURRENT.
Actual lots are shown only when ``grid_start = month_start`` (earlier lots of the current period).
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

from app.core.config import BusinessDefaults

ACTUAL, CURRENT, FORECAST = "actual", "current", "forecast"


@dataclass(frozen=True)
class Lot:
    start: date
    end: date
    status: str = FORECAST
    period_start: date | None = None     # start of the month / anchored period the lot belongs to
    period_end: date | None = None

    @property
    def month(self) -> date:
        """Grouping key for month totals: the month in which the lot's period starts."""
        return (self.period_start or self.start).replace(day=1)

    @property
    def band(self) -> str:
        """Heading of the lot's period: 'November 2026', or '05 Nov-04 Dec 2026' for an anchored period."""
        ps, pe = self.period_start, self.period_end
        if ps is None or ps.day == 1:
            return f"{self.month:%B %Y}"
        return f"{ps:%d %b}-{pe:%d %b %Y}"

    @property
    def label(self) -> str:
        if self.start.month == self.end.month:
            return f"{self.start:%d}-{self.end:%d} {self.end:%b}"
        return f"{self.start:%d %b}-{self.end:%d %b}"

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def contains(self, d: date) -> bool:
        return self.start <= d <= self.end


def month_end(d: date) -> date:
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


def period_bounds(month: date, anchor_day: int = 1) -> tuple[date, date]:
    """The period starting in ``month``: the calendar month, or anchor day .. day before it next month."""
    first = month.replace(day=anchor_day)
    if anchor_day == 1:
        return first, month_end(month)
    return first, add_months(month, 1).replace(day=anchor_day) - timedelta(days=1)


def month_lots(month: date, length: int, anchor_day: int = 1) -> list[tuple[date, date]]:
    n = max(1, 30 // length)
    first, last = period_bounds(month, anchor_day)
    out = []
    for i in range(n):
        s = first + timedelta(days=i * length)
        e = last if i == n - 1 else s + timedelta(days=length - 1)
        out.append((s, e))
    return out


def build_lots(as_of: date, s: BusinessDefaults) -> list[Lot]:
    """All grid lots in date order: locked actuals (if month_start), current, forecast."""
    spans: list[tuple[date, date, date | None, date | None]] = []
    anchor = s.anchor
    if s.lot_scheme == "month_thirds":
        day = anchor.day if anchor else 1
        first_month = as_of.replace(day=1) if as_of.day >= day else add_months(as_of, -1)
        for k in range(s.horizon_months):
            m = add_months(first_month, k)
            ps, pe = period_bounds(m, day)
            spans += [(a, b, ps, pe) for a, b in month_lots(m, s.lot_length_days, day)]
    else:
        L = s.lot_length_days
        base = anchor or as_of.replace(day=1)
        # first lot shown: the one holding the 1st of the as-of month (earlier lots of the month can be actuals)
        start = base + timedelta(days=((as_of.replace(day=1) - base).days // L) * L)
        while len([x for x in spans if x[1] >= as_of]) < s.horizon_lots:
            e = start + timedelta(days=L - 1)
            spans.append((start, e, None, None))
            start = e + timedelta(days=1)
    lots = []
    for st, en, ps, pe in spans:
        if en < as_of:
            if s.grid_start == "month_start":
                lots.append(Lot(st, en, ACTUAL, ps, pe))
        else:
            lots.append(Lot(st, en, CURRENT if st <= as_of else FORECAST, ps, pe))
    return lots


def forecast_lots(lots: list[Lot]) -> list[Lot]:
    return [lt for lt in lots if lt.status != ACTUAL]


def lot_index(lots: list[Lot], d: date) -> int | None:
    """Index of the lot holding d, or None when d is after the horizon (or before the first lot)."""
    for i, lt in enumerate(lots):
        if lt.contains(d):
            return i
    return None
