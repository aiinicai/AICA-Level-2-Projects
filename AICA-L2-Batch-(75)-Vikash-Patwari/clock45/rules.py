"""
clock45.rules
=============
The statutory engine. Everything contestable lives HERE, as data, never as a
constant buried in application code.

Design rules (do not violate these, they are what make the output defensible):
  1. No AI, no heuristics, no randomness in this module. Pure functions.
  2. Every rate and every statute reference is a DATED table entry, so a run
     from last year reproduces last year's number.
  3. Every function that makes a judgement returns the REASON alongside the
     answer. The audit file needs the reasoning, not just the figure.

Verified 9 August 2026. Re-verify before each release and bump RULE_PACK_VERSION.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

RULE_PACK_VERSION = "2026.08.1"

# ---------------------------------------------------------------------------
# 1. RBI Bank Rate, dated.
# ---------------------------------------------------------------------------
# MSMED s.16 interest = 3 x the Bank Rate notified by RBI, compounded monthly.
# NOTE: many published articles quote ~20.25%, which assumes a 6.75% Bank Rate.
# That figure is STALE. As at June 2026 the Bank Rate is 5.50% -> 16.50% p.a.
# Add a row each time the RBI moves; never edit history.
BANK_RATE_TABLE: list[tuple[date, Decimal]] = [
    (date(2020, 5, 22), Decimal("4.25")),
    (date(2022, 5, 4), Decimal("4.65")),
    (date(2022, 6, 8), Decimal("5.15")),
    (date(2022, 8, 5), Decimal("5.65")),
    (date(2022, 9, 30), Decimal("6.15")),
    (date(2022, 12, 7), Decimal("6.50")),
    (date(2023, 2, 8), Decimal("6.75")),
    (date(2025, 6, 6), Decimal("6.00")),
    (date(2025, 10, 1), Decimal("5.75")),
    (date(2025, 12, 5), Decimal("5.50")),
    # Held at 5.50% through the Feb, Apr and Jun 2026 MPC reviews.
]

MSMED_INTEREST_MULTIPLE = Decimal("3")


def bank_rate_on(d: date) -> Decimal:
    """Bank Rate in force on a given date, as a percentage."""
    applicable = [r for eff, r in BANK_RATE_TABLE if eff <= d]
    if not applicable:
        raise ValueError(f"No Bank Rate on record for {d}. Extend BANK_RATE_TABLE.")
    return applicable[-1]


def msmed_rate_on(d: date) -> Decimal:
    """Annual MSMED s.16 interest rate on a given date, as a percentage."""
    return MSMED_INTEREST_MULTIPLE * bank_rate_on(d)


# ---------------------------------------------------------------------------
# 2. Statute map, by tax year.
# ---------------------------------------------------------------------------
# The Income-tax Act, 1961 stands repealed from 1 April 2026 and is replaced by
# the Income-tax Act, 2025. The disallowance provision is carried forward.
# The tool must cite the provision applicable to the year under audit.
STATUTE_MAP: dict[str, dict[str, str]] = {
    "2023-24": {"act": "Income-tax Act, 1961", "section": "43B(h)", "form": "3CD Cl.22"},
    "2024-25": {"act": "Income-tax Act, 1961", "section": "43B(h)", "form": "3CD Cl.22"},
    "2025-26": {"act": "Income-tax Act, 1961", "section": "43B(h)", "form": "3CD Cl.22"},
    "2026-27": {"act": "Income-tax Act, 2025", "section": "37", "form": "3CD Cl.22"},
    "2027-28": {"act": "Income-tax Act, 2025", "section": "37", "form": "3CD Cl.22"},
}


def statute_for(fy: str) -> dict[str, str]:
    if fy not in STATUTE_MAP:
        raise ValueError(
            f"Tax year {fy} is not in STATUTE_MAP. Refusing to guess the "
            f"governing provision — add it explicitly."
        )
    return STATUTE_MAP[fy]


def fy_bounds(fy: str) -> tuple[date, date]:
    """'2025-26' -> (1 Apr 2025, 31 Mar 2026)."""
    start_year = int(fy.split("-")[0])
    return date(start_year, 4, 1), date(start_year + 1, 3, 31)


# ---------------------------------------------------------------------------
# 3. Credit period and the clock.
# ---------------------------------------------------------------------------
STATUTORY_CEILING_DAYS = 45
NO_AGREEMENT_DAYS = 15


@dataclass(frozen=True)
class CreditPeriod:
    days: int
    basis: str
    ceiling_applied: bool = False


def resolve_credit_period(agreement_days: Optional[int]) -> CreditPeriod:
    """
    s.15 MSMED: pay within the period agreed in WRITING, which cannot exceed 45
    days from acceptance. Absent a written agreement, 15 days.

    An agreement stating more than 45 days is not protection: the excess is void
    and 45 is an absolute ceiling. Teams get this wrong constantly.
    """
    if agreement_days is None:
        return CreditPeriod(NO_AGREEMENT_DAYS, "No written agreement on file - 15 days applies")
    if agreement_days > STATUTORY_CEILING_DAYS:
        return CreditPeriod(
            STATUTORY_CEILING_DAYS,
            f"Written agreement states {agreement_days} days; capped at the "
            f"45-day statutory ceiling (excess is void)",
            ceiling_applied=True,
        )
    return CreditPeriod(agreement_days, f"Written agreement - {agreement_days} days")


def days_add(d: date, n: int) -> date:
    from datetime import timedelta

    return d + timedelta(days=n)


def due_date_of(acceptance_date: date, credit: CreditPeriod) -> date:
    """Last day on which payment may be made without consequence."""
    return days_add(acceptance_date, credit.days)


def appointed_day_of(acceptance_date: date, credit: CreditPeriod) -> date:
    """
    s.2(b) MSMED: the day immediately after expiry of the period.
    Interest under s.16 runs FROM this day.
    """
    return days_add(due_date_of(acceptance_date, credit), 1)


# ---------------------------------------------------------------------------
# 4. Interest: compound, monthly rests, rate-segmented.
# ---------------------------------------------------------------------------
def _add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(
        d.day,
        [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28,
         31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1],
    )
    return date(y, m, day)


def _q(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class InterestResult:
    interest: Decimal
    closing_balance: Decimal
    segments: list[dict] = field(default_factory=list)
    note: str = ""


def msmed_interest(
    principal: Decimal, appointed_day: date, upto: date
) -> InterestResult:
    """
    Compound interest with monthly rests from the appointed day to `upto`.

    The rate is looked up for EACH monthly rest, so a period spanning an RBI
    rate change computes correctly. Every rest is returned as a segment so the
    working paper can print the arithmetic — a partner will ask.
    """
    if upto <= appointed_day or principal <= 0:
        return InterestResult(Decimal("0.00"), _q(principal), [], "No interest period")

    balance = principal
    cursor = appointed_day
    segments: list[dict] = []

    while _add_months(cursor, 1) <= upto:
        nxt = _add_months(cursor, 1)
        rate = msmed_rate_on(cursor)
        opening = balance
        balance = balance * (Decimal("1") + rate / Decimal("1200"))
        segments.append(
            {
                "from": cursor, "to": nxt, "basis": "monthly rest",
                "bank_rate_pct": bank_rate_on(cursor), "msmed_rate_pct": rate,
                "opening": _q(opening), "closing": _q(balance),
            }
        )
        cursor = nxt

    residual_days = (upto - cursor).days
    if residual_days > 0:
        rate = msmed_rate_on(cursor)
        opening = balance
        balance = balance * (
            Decimal("1") + rate * Decimal(residual_days) / (Decimal("365") * Decimal("100"))
        )
        segments.append(
            {
                "from": cursor, "to": upto, "basis": f"{residual_days} days pro-rata",
                "bank_rate_pct": bank_rate_on(cursor), "msmed_rate_pct": rate,
                "opening": _q(opening), "closing": _q(balance),
            }
        )

    return InterestResult(
        interest=_q(balance - principal),
        closing_balance=_q(balance),
        segments=segments,
        note="MSMED s.16: three times the RBI Bank Rate, compounded with monthly "
             "rests. Under s.23 this interest is NOT deductible.",
    )


# ---------------------------------------------------------------------------
# 5. The verdict.
# ---------------------------------------------------------------------------
ALLOWED = "ALLOWED"
ALLOWED_NOT_YET_DUE = "ALLOWED_NOT_YET_DUE"
ALLOWED_LATE_INTEREST_ONLY = "ALLOWED_LATE_INTEREST_ONLY"
DISALLOWED = "DISALLOWED"
EXCLUDED = "EXCLUDED"


@dataclass
class Verdict:
    status: str
    reason: str
    unpaid_at_year_end: Decimal = Decimal("0.00")
    disallowance: Decimal = Decimal("0.00")
    interest: Decimal = Decimal("0.00")
    due_date: Optional[date] = None
    appointed_day: Optional[date] = None
    interest_segments: list[dict] = field(default_factory=list)


def assess_invoice(
    *,
    amount: Decimal,
    acceptance_date: date,
    agreement_days: Optional[int],
    payments: list[tuple[date, Decimal]],
    fy: str,
    interest_upto: Optional[date] = None,
) -> Verdict:
    """
    Assess a single payable line.

    `payments` is a list of (date, amount) allocated against this invoice.
    Partial payment is handled: only the balance unpaid at year end is
    disallowed, and interest runs on the running unpaid balance.

    Note on scope: 43B(h) / s.37 has NO proviso permitting payment by the
    return due date. So the disallowance bites on amounts unpaid AS AT 31 March
    where the 15/45-day limit had already expired. Amounts paid late but WITHIN
    the year are deductible in that same year — but still attract s.16 interest,
    which is the exposure almost every tool misses.
    """
    _, year_end = fy_bounds(fy)
    interest_upto = interest_upto or year_end

    credit = resolve_credit_period(agreement_days)
    due = due_date_of(acceptance_date, credit)
    appointed = appointed_day_of(acceptance_date, credit)

    paid_in_time = sum((p for d, p in payments if d <= due), Decimal("0"))
    paid_by_year_end = sum((p for d, p in payments if d <= year_end), Decimal("0"))
    unpaid_at_year_end = max(Decimal("0"), amount - paid_by_year_end)

    # Lateness, not the interest figure, must drive the status. A payment made
    # ON the appointed day is late under s.15 even though the interest period
    # is nil and rounds to zero.
    paid_late = any(d > due for d, _ in payments)

    late_payments = sorted([(d, p) for d, p in payments if d > due and d <= interest_upto])

    # Interest accrues on whatever was outstanding past the appointed day.
    interest_total = Decimal("0.00")
    segments: list[dict] = []
    if due < interest_upto:
        outstanding = amount - paid_in_time
        cursor = appointed
        for pdate, pamt in late_payments:
            if outstanding <= 0:
                break
            r = msmed_interest(outstanding, cursor, pdate)
            interest_total += r.interest
            segments.extend(r.segments)
            outstanding -= pamt
            cursor = pdate
        if outstanding > 0:
            r = msmed_interest(outstanding, cursor, interest_upto)
            interest_total += r.interest
            segments.extend(r.segments)

    if due >= year_end and unpaid_at_year_end > 0:
        return Verdict(
            ALLOWED_NOT_YET_DUE,
            f"Time limit expires {due.isoformat()}, after year end "
            f"{year_end.isoformat()}. Not disallowable this year — carry to next run.",
            unpaid_at_year_end=_q(unpaid_at_year_end),
            due_date=due, appointed_day=appointed,
        )

    if unpaid_at_year_end > 0:
        return Verdict(
            DISALLOWED,
            f"₹{_q(unpaid_at_year_end)} unpaid at {year_end.isoformat()}; "
            f"time limit expired {due.isoformat()} ({credit.basis}). "
            f"Deductible only in the year of actual payment.",
            unpaid_at_year_end=_q(unpaid_at_year_end),
            disallowance=_q(unpaid_at_year_end),
            interest=_q(interest_total),
            due_date=due, appointed_day=appointed, interest_segments=segments,
        )

    if paid_late:
        tail = (
            f"s.16 interest of ₹{_q(interest_total)} accrues and is NOT "
            f"deductible under s.23."
            if interest_total > 0 else
            "Payment fell on the appointed day itself, so the interest period "
            "is nil — but the s.15 breach stands and should be minuted."
        )
        return Verdict(
            ALLOWED_LATE_INTEREST_ONLY,
            f"Paid within the year but after the {credit.days}-day limit "
            f"(due {due.isoformat()}). No disallowance; {tail}",
            interest=_q(interest_total),
            due_date=due, appointed_day=appointed, interest_segments=segments,
        )

    return Verdict(
        ALLOWED,
        f"Paid on or before {due.isoformat()} ({credit.basis}).",
        due_date=due, appointed_day=appointed,
    )
