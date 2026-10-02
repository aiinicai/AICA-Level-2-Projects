"""Date arithmetic for MCA compliance: financial years, AGM deadlines, half-years,
DIR-3 KYC cycles and the single due-date convention (see docs/LEGAL_NOTES.md §2).

Pure Python: no Flask, no DB.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Mapping

from dateutil.relativedelta import relativedelta

MARCH31 = (3, 31)


# ---------------------------------------------------------------- due_date --
def due_date(anchor: date, offset: Mapping[str, int] | None) -> date:
    """The one day-count convention used everywhere.

    * ``{"days": N}``  -> anchor + N calendar days (s.9 General Clauses Act:
      the anchor day itself is excluded, so the Nth day after is the last day).
    * ``{"months": N}`` -> anchor + N calendar months via relativedelta
      (day kept, clipped to month end: 31-08 + 6m = 28/29-02).
    * Both -> months first, then days (e.g. LLP Form 8: FY end + 6m + 30d).
    Negative values are allowed (e.g. "21 days before the AGM").
    No weekend/holiday shifting — see :func:`holiday_hint`.
    """
    offset = offset or {}
    unknown = set(offset) - {"days", "months", "years"}
    if unknown:
        raise ValueError(f"Unknown offset keys: {sorted(unknown)}")
    d = anchor + relativedelta(years=offset.get("years", 0), months=offset.get("months", 0))
    return d + timedelta(days=offset.get("days", 0))


def holiday_hint(d: date, holidays: Mapping[date, str] | None = None) -> str | None:
    """Informational only: MCA filing is online, due dates are never shifted."""
    if holidays and d in holidays:
        return f"falls on a holiday ({holidays[d]})"
    if d.weekday() == 6:
        return "falls on a Sunday"
    return None


# ---------------------------------------------------------- financial year --
@dataclass(frozen=True)
class FY:
    start: date
    end: date

    @property
    def key(self) -> str:
        return fy_key_for_end(self.end)

    @property
    def is_long(self) -> bool:
        return (self.end - self.start).days > 366


def fy_key_for_end(end: date) -> str:
    """FY ending 31-03-2027 -> 'FY2026-27' (label by the standard April-March year)."""
    return f"FY{end.year - 1}-{str(end.year)[2:]}"


def standard_fy_end(d: date) -> date:
    """31 March closing the standard (April-March) FY that contains d."""
    return date(d.year if d.month <= 3 else d.year + 1, *MARCH31)


def company_first_fy_end(incorporated: date) -> date:
    """s.2(41): first FY ends on the 31 March following incorporation; if
    incorporated on/after 1 January, on 31 March of the following year.
    Invariant: always 31 March of (incorporation year + 1)."""
    return date(incorporated.year + 1, *MARCH31)


def llp_first_fy_end(incorporated: date, elect_longer: bool) -> date:
    """s.2(1)(l) LLP Act: an LLP registered after 30 September *may* close its
    first FY on 31 March of the year next following. Default: shorter FY.
    Read as: registered 1 Oct - 31 Mar (second half of a FY) — LEGAL_NOTES I11."""
    normal = standard_fy_end(incorporated)
    if elect_longer and llp_election_available(incorporated):
        return date(normal.year + 1, *MARCH31)
    return normal


def llp_election_available(incorporated: date) -> bool:
    return incorporated.month >= 10 or incorporated.month <= 3


def financial_years(incorporated: date, first_end: date, upto: date) -> list[FY]:
    """All FYs from incorporation whose start is on/before ``upto``."""
    fys = [FY(incorporated, first_end)]
    while True:
        nxt_start = fys[-1].end + timedelta(days=1)
        if nxt_start > upto:
            return fys
        fys.append(FY(nxt_start, date(nxt_start.year + 1, *MARCH31)))


def fy_containing(fys: list[FY], d: date) -> FY | None:
    return next((f for f in fys if f.start <= d <= f.end), None)


# ------------------------------------------------------------ half-years --
@dataclass(frozen=True)
class HalfYear:
    start: date
    end: date
    half: int  # 1 = Apr-Sep, 2 = Oct-Mar

    @property
    def key(self) -> str:
        return f"H{self.half}-{fy_key_for_end(standard_fy_end(self.start))}"


def half_years(from_date: date, upto: date) -> list[HalfYear]:
    """Calendar half-years (Apr-Sep, Oct-Mar) overlapping [from_date, upto]."""
    if from_date.month >= 10:
        cur = HalfYear(date(from_date.year, 10, 1), date(from_date.year + 1, 3, 31), 2)
    elif from_date.month <= 3:
        cur = HalfYear(date(from_date.year - 1, 10, 1), date(from_date.year, 3, 31), 2)
    else:
        cur = HalfYear(date(from_date.year, 4, 1), date(from_date.year, 9, 30), 1)
    out = []
    while cur.start <= upto:
        out.append(cur)
        if cur.half == 1:
            cur = HalfYear(date(cur.start.year, 10, 1), date(cur.start.year + 1, 3, 31), 2)
        else:
            cur = HalfYear(date(cur.end.year, 4, 1), date(cur.end.year, 9, 30), 1)
    return out


def march31s_after(incorporated: date, upto: date) -> list[date]:
    """Every 31 March strictly after incorporation, up to ``upto`` (DPT-3 positions)."""
    y = incorporated.year if incorporated < date(incorporated.year, *MARCH31) else incorporated.year + 1
    out = []
    while date(y, *MARCH31) <= upto:
        out.append(date(y, *MARCH31))
        y += 1
    return out


# ------------------------------------------------------------------- AGM --
def agm_deadline(fy: FY, is_first: bool, previous_agm: date | None) -> date:
    """s.96(1): first AGM within 9 months of close of first FY; later AGMs
    within 6 months of FY close and not more than 15 months after the
    previous AGM — whichever is earlier."""
    if is_first:
        return due_date(fy.end, {"months": 9})
    d = due_date(fy.end, {"months": 6})
    if previous_agm is not None:
        d = min(d, due_date(previous_agm, {"months": 15}))
    return d


# ----------------------------------------------------------- DIR-3 KYC --
TRIENNIAL_START = date(2026, 3, 31)       # G.S.R. 943(E) in force
LEGACY_CUTOFF = date(2025, 3, 31)          # DIN held on/before -> legacy cohort
LEGACY_FIRST_DUE = date(2028, 6, 30)       # MCA illustration (a)


def kyc_due(din_allotment_date: date, last_kyc_fy: str | None = None,
            override_first_due: date | None = None) -> date:
    """First triennial DIR-3 KYC Web due date for a DIN (seed interpretation,
    partner-approved 25-09-2026 — LEGAL_NOTES I1):

    * Partner override wins.
    * Legacy DIN (allotted on/before 31-03-2025): 30-06-2028.
    * DIN allotted in FY Y (>= FY 2025-26): 30 June of (Y's closing year + 3)
      — e.g. allotted Jan 2026 (FY 2025-26, closes 2026) -> 30-06-2029.

    ``last_kyc_fy`` is accepted for API stability; interim filings do not
    reset the cycle (MCA illustration (c)), so it does not move the date.
    """
    if override_first_due:
        return override_first_due
    if din_allotment_date <= LEGACY_CUTOFF:
        return LEGACY_FIRST_DUE
    return date(standard_fy_end(din_allotment_date).year + 3, 6, 30)


def kyc_cycle_dues(din_allotment_date: date, upto: date,
                   override_first_due: date | None = None) -> list[date]:
    """First due date and every third year after it, up to (and including the
    first one after) ``upto`` so the next cycle is always visible."""
    d = kyc_due(din_allotment_date, override_first_due=override_first_due)
    out = [d]
    while d <= upto:
        d = date(d.year + 3, 6, 30)
        out.append(d)
    return out


def kyc_cycle_key(due: date) -> str:
    """30-06-2029 -> 'KYC-CYCLE-2026-27..2028-29' (the three FYs it covers)."""
    last_end = due.year
    first_start = last_end - 3
    return f"KYC-CYCLE-{first_start}-{str(first_start + 1)[2:]}..{last_end - 1}-{str(last_end)[2:]}"
