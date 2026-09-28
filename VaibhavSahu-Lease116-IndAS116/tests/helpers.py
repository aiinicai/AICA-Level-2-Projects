"""Independent helpers for tests — deliberately NOT using the engine's maths.

Floating point is acceptable here because these are cross-checks with a ±0.01
tolerance; the engine itself uses Decimal throughout.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal


def xnpv(rate_pct: float, cashflows: list[tuple[date, float]], t0: date) -> float:
    """Excel XNPV equivalent: sum CF / (1+r)^((d - d0)/365)."""
    r = rate_pct / 100.0
    return sum(cf / (1 + r) ** ((d - t0).days / 365.0) for d, cf in cashflows)


def annuity_pv(pmt: float, periodic_rate: float, n: int, due: bool = False) -> float:
    """PV of n level payments; due=True means first payment now (annuity-due)."""
    if periodic_rate == 0:
        return pmt * n
    pv = pmt * (1 - (1 + periodic_rate) ** (-n)) / periodic_rate
    return pv * (1 + periodic_rate) if due else pv


def close(a, b, tol: float = 0.011) -> bool:
    return abs(float(a) - float(b)) <= tol


def assert_close(a, b, tol: float = 0.011, msg: str = ""):
    assert close(a, b, tol), f"{msg} expected {b}, got {a} (tolerance {tol})"


def balanced(postings) -> bool:
    for p in postings:
        dr = sum((l[1] for l in p.lines), Decimal(0))
        cr = sum((l[2] for l in p.lines), Decimal(0))
        if dr != cr:
            return False
    return True


def rows_reconcile(result) -> list[str]:
    errs = []
    for r in result.periods:
        lhs = (r.liab_open + r.liab_additions + r.interest - r.payments + r.liab_remeasurement + r.liab_modification
               - r.liab_derecognised)
        if lhs != r.liab_close:
            errs.append(f"liability {r.period_end}: {lhs} != {r.liab_close}")
        rhs = (r.rou_open + r.rou_additions - r.depreciation - r.impairment + r.rou_remeasurement + r.rou_modification
               - r.rou_derecognised)
        if rhs != r.rou_close:
            errs.append(f"rou {r.period_end}: {rhs} != {r.rou_close}")
        if r.liab_current + r.liab_noncurrent != r.liab_close:
            errs.append(f"split {r.period_end}")
    for a, b in zip(result.periods, result.periods[1:]):
        if a.liab_close != b.liab_open or a.rou_close != b.rou_open:
            errs.append(f"continuity {a.period_end}")
    return errs


def je(postings, event):
    return [p for p in postings if p.event == event]
