"""Discount-rate conventions, day-count bases and present-value mathematics.

The engine converts every quoted rate into an *effective annual* rate R and every
date into a year-fraction tau(d) measured from a fixed origin (the commencement
date). Growth between two dates is (1+R)^(tau(d2)-tau(d1)); the discount factor
is the reciprocal. Because discounting (initial PV) and accretion (interest) use
the identical R and tau, a liability schedule always amortises to exactly nil at
the last payment — nothing needs to be plugged (spec sections 7, 9, 32).

Supported bases
---------------
ACT/365F   : tau = actual days / 365 (identical to Excel XNPV / XIRR)
MONTHS/12  : tau = fractional months / 12 (periodic method; with a nominal
             monthly convention one month grows by exactly (1 + r/12))
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from functools import lru_cache

from .calendar_utils import months_between_frac
from .decimal_utils import D, ONE, ZERO, dpow, pct, engine_context


class DayCount(str, Enum):
    ACT_365F = "ACT/365F"
    MONTHLY = "MONTHS/12"


class RateConvention(str, Enum):
    EFFECTIVE_ANNUAL = "EFFECTIVE_ANNUAL"      # quoted rate is the effective annual yield
    NOMINAL_MONTHLY = "NOMINAL_MONTHLY"        # quoted rate compounded monthly (r/12 per month)
    NOMINAL_QUARTERLY = "NOMINAL_QUARTERLY"    # compounded quarterly (r/4)
    NOMINAL_SEMIANNUAL = "NOMINAL_SEMIANNUAL"  # compounded half-yearly (r/2)


_COMPOUNDING = {
    RateConvention.EFFECTIVE_ANNUAL: 1,
    RateConvention.NOMINAL_MONTHLY: 12,
    RateConvention.NOMINAL_QUARTERLY: 4,
    RateConvention.NOMINAL_SEMIANNUAL: 2,
}

DAYCOUNT_LABEL = {
    DayCount.ACT_365F: "Exact dates, Actual/365 (Fixed) — XNPV-consistent",
    DayCount.MONTHLY: "Periodic, months/12 (fractional months by actual days)",
}
CONVENTION_LABEL = {
    RateConvention.EFFECTIVE_ANNUAL: "Effective annual rate",
    RateConvention.NOMINAL_MONTHLY: "Nominal annual rate compounded monthly (rate ÷ 12)",
    RateConvention.NOMINAL_QUARTERLY: "Nominal annual rate compounded quarterly (rate ÷ 4)",
    RateConvention.NOMINAL_SEMIANNUAL: "Nominal annual rate compounded half-yearly (rate ÷ 2)",
}


@engine_context
def effective_annual_rate(rate_percent, convention: RateConvention | str) -> Decimal:
    """Convert a quoted annual rate (in %) to an effective annual rate (decimal)."""
    conv = RateConvention(convention)
    m = _COMPOUNDING[conv]
    r = pct(rate_percent)
    if m == 1:
        return r
    return dpow(ONE + r / Decimal(m), Decimal(m)) - ONE


@dataclass(frozen=True)
class TimeBasis:
    origin: date
    daycount: DayCount = DayCount.ACT_365F

    def tau(self, d: date) -> Decimal:
        return _tau(self.origin, d, self.daycount)


@lru_cache(maxsize=200_000)
def _tau(origin: date, d: date, daycount: DayCount) -> Decimal:
    if daycount == DayCount.ACT_365F:
        return Decimal((d - origin).days) / Decimal(365)
    return months_between_frac(origin, d) / Decimal(12)


@dataclass
class Discounter:
    """Effective annual rate R on a TimeBasis."""

    R: Decimal
    basis: TimeBasis

    @property
    def one_plus_r(self) -> Decimal:
        return ONE + self.R

    @engine_context
    def growth(self, d1: date, d2: date) -> Decimal:
        """Accumulation factor from d1 to d2 (d2 >= d1)."""
        if d1 == d2:
            return ONE
        dt = self.basis.tau(d2) - self.basis.tau(d1)
        return _growth(self.one_plus_r, dt)

    @engine_context
    def df(self, d: date, ref: date) -> Decimal:
        """Discount factor bringing an amount at date d back to date ref."""
        if d == ref:
            return ONE
        dt = self.basis.tau(d) - self.basis.tau(ref)
        return ONE / _growth(self.one_plus_r, dt)

    @engine_context
    def years(self, d: date, ref: date) -> Decimal:
        return self.basis.tau(d) - self.basis.tau(ref)


@lru_cache(maxsize=400_000)
def _growth(one_plus_r: Decimal, dt: Decimal) -> Decimal:
    return dpow(one_plus_r, dt)


@engine_context
def present_value(cashflows: list[tuple[date, Decimal]], discounter: Discounter, ref: date) -> Decimal:
    total = ZERO
    for d, amt in cashflows:
        total += D(amt) * discounter.df(d, ref)
    return total


@engine_context
def solve_rate(cashflows: list[tuple[date, Decimal]], target_pv: Decimal, ref: date,
               basis: TimeBasis, lo: Decimal = Decimal("-0.99"), hi: Decimal = Decimal("10"),
               tol: Decimal = Decimal("1e-18"), max_iter: int = 400) -> Decimal:
    """Find effective annual R such that PV(cashflows at R) == target_pv (bisection).

    Used for: interest rate implicit in the lease (lessor), implied rate on
    opening-balance cut-over, and audit recomputation of a client's rate.
    """
    target = D(target_pv)

    def f(R: Decimal) -> Decimal:
        disc = Discounter(R, basis)
        return present_value(cashflows, disc, ref) - target

    f_lo, f_hi = f(lo), f(hi)
    if f_lo == 0:
        return lo
    if f_hi == 0:
        return hi
    if (f_lo > 0) == (f_hi > 0):
        raise ValueError("Rate cannot be solved: present value does not bracket the target")
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        f_mid = f(mid)
        if abs(f_mid) <= tol or (hi - lo) < tol:
            return mid
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return (lo + hi) / 2


def nominal_from_effective(R: Decimal, convention: RateConvention | str) -> Decimal:
    """Inverse of effective_annual_rate (returns % quoted rate)."""
    conv = RateConvention(convention)
    m = _COMPOUNDING[conv]
    if m == 1:
        return R * 100
    return (dpow(ONE + R, ONE / Decimal(m)) - ONE) * Decimal(m) * 100
