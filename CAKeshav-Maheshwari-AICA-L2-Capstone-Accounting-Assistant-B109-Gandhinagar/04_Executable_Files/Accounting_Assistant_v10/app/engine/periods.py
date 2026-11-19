"""Accounting periods: Indian FY (1 Apr - 31 Mar) and the quick picks used by every period picker."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

QUICK = ["This month", "Last month", "This quarter", "This FY", "Last FY", "Custom"]


@dataclass(frozen=True)
class Period:
    start: date
    end: date
    label: str = ""

    @property
    def frm(self) -> str:
        return self.start.strftime("%Y%m%d")

    @property
    def to(self) -> str:
        return self.end.strftime("%Y%m%d")

    def contains(self, yyyymmdd: str) -> bool:
        return bool(yyyymmdd) and self.frm <= yyyymmdd[:8] <= self.to

    def text(self) -> str:
        return f"{self.start:%d-%m-%Y} to {self.end:%d-%m-%Y}"


def fy_start(d: date) -> date:
    return date(d.year if d.month >= 4 else d.year - 1, 4, 1)


def fy_label(d: date) -> str:
    s = fy_start(d)
    return f"FY {s.year}-{str(s.year + 1)[2:]}"


def _month_end(d: date) -> date:
    nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return nxt - timedelta(days=1)


def quick(name: str, today: date | None = None) -> Period:
    t = today or date.today()
    if name == "This month":
        return Period(date(t.year, t.month, 1), _month_end(t), name)
    if name == "Last month":
        first = date(t.year, t.month, 1) - timedelta(days=1)
        return Period(date(first.year, first.month, 1), first, name)
    if name == "This quarter":                      # Apr-Jun, Jul-Sep, Oct-Dec, Jan-Mar
        qm = ((t.month - 1) // 3) * 3 + 1
        s = date(t.year, qm, 1)
        return Period(s, _month_end(date(t.year, qm + 2, 1)), name)
    if name == "Last FY":
        s = fy_start(t)
        return Period(date(s.year - 1, 4, 1), date(s.year, 3, 31), fy_label(date(s.year - 1, 4, 1)))
    s = fy_start(t)                                  # This FY (default)
    return Period(s, date(s.year + 1, 3, 31), fy_label(t))


def default(today: date | None = None) -> Period:
    return quick("This FY", today)
