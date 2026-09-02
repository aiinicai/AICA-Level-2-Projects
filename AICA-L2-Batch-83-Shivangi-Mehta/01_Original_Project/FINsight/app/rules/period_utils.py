"""
Shared helpers for turning an engagement's `financial_year` string
("2025-26") into real dates, and for locating a comparable prior-year
engagement — used by more than one accounting rule (depreciation-policy
consistency, provision-reversal consistency) so this logic exists once,
not once per rule (Blueprint Section 1.1's "shared detection logic
lives in one place" principle).

Lives at `app/rules/` (not under `app/rules/accounting/`) because
Audit/Tax/SEBI rules (later stages) will need the same financial-year
arithmetic and are equally not framework-specific.
"""
from __future__ import annotations

from datetime import date

from app.engagement.validation import _FINANCIAL_YEAR_RE


def financial_year_bounds(financial_year: str) -> tuple[date, date] | None:
    """Indian financial year convention (1 April - 31 March), the same
    convention `app/engagement/validation.py::_is_valid_financial_year`
    already validates the *format* of ("2025-26"). Returns None if the
    string isn't in that validated shape — callers should already only
    ever see validated engagement data, but this stays defensive rather
    than raising, consistent with this module's "insufficient data, not
    a crash" philosophy."""
    match = _FINANCIAL_YEAR_RE.match((financial_year or "").strip())
    if not match:
        return None
    start_year = int(match.group(1))
    return date(start_year, 4, 1), date(start_year + 1, 3, 31)


def prior_financial_year(financial_year: str) -> str | None:
    match = _FINANCIAL_YEAR_RE.match((financial_year or "").strip())
    if not match:
        return None
    start_year = int(match.group(1))
    prior_start = start_year - 1
    return f"{prior_start}-{(prior_start + 1) % 100:02d}"


def next_financial_year(financial_year: str) -> str | None:
    """Mirror of prior_financial_year() — added in Stage 9 for
    AUD-SUB-007 (subsequent-period reversal detection), which needs to
    look forward one engagement, not backward. Same "None on unparseable
    input" defensiveness as its sibling above."""
    match = _FINANCIAL_YEAR_RE.match((financial_year or "").strip())
    if not match:
        return None
    start_year = int(match.group(1))
    next_start = start_year + 1
    return f"{next_start}-{(next_start + 1) % 100:02d}"


def days_held_in_period(event_date: date, fy_start: date, fy_end: date) -> int:
    """Days an asset/item was actually within the FY, clamped to the FY
    bounds — e.g. an asset put to use before the FY started counts as
    held for the whole FY, not a negative or over-long span."""
    effective_start = max(event_date, fy_start)
    if effective_start > fy_end:
        return 0
    return (fy_end - effective_start).days + 1


def total_days_in_period(fy_start: date, fy_end: date) -> int:
    return (fy_end - fy_start).days + 1
