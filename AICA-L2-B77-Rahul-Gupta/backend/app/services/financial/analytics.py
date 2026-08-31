"""Deterministic financial analytics — ratios, growth, quality metrics.

Input shape: ``periods`` is an ordered list of period labels (oldest first),
``data`` maps period label → {metric: absolute INR value}.
All calculations are pure Python; the AI never computes these.
"""
from __future__ import annotations

import math
from typing import Any


def _g(data: dict, period: str, metric: str) -> float | None:
    v = data.get(period, {}).get(metric)
    return None if v is None else float(v)


def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b in (None, 0):
        return None
    return a / b


def yoy_growth(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev is None or prev == 0:
        return None
    return (curr - prev) / abs(prev)


def cagr(first: float | None, last: float | None, years: int) -> float | None:
    if first is None or last is None or first <= 0 or last <= 0 or years <= 0:
        return None
    return (last / first) ** (1 / years) - 1


def stddev(values: list[float]) -> float | None:
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return None
    mean = sum(vals) / len(vals)
    return math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1))


def total_debt(data: dict, period: str) -> float | None:
    lt = _g(data, period, "long_term_borrowings") or 0.0
    st = _g(data, period, "short_term_borrowings") or 0.0
    if _g(data, period, "long_term_borrowings") is None and _g(data, period, "short_term_borrowings") is None:
        return None
    return lt + st


def compute_period_ratios(data: dict, periods: list[str], period: str) -> dict[str, float | None]:
    """All ratios for a single period."""
    idx = periods.index(period)
    prev = periods[idx - 1] if idx > 0 else None

    revenue = _g(data, period, "revenue")
    ebitda = _g(data, period, "ebitda")
    ebit = _g(data, period, "ebit")
    pat = _g(data, period, "pat")
    net_worth = _g(data, period, "net_worth")
    debt = total_debt(data, period)
    cfo = _g(data, period, "cfo")
    capex = _g(data, period, "capex")
    inventory = _g(data, period, "inventory")
    receivables = _g(data, period, "receivables")
    payables = _g(data, period, "trade_payables")
    cash = _g(data, period, "cash")
    oca = _g(data, period, "other_current_assets")
    total_assets = _g(data, period, "total_assets")
    material_cost = _g(data, period, "material_cost")
    finance_cost = _g(data, period, "finance_cost")
    tax = _g(data, period, "tax")
    pbt = _g(data, period, "pbt")

    current_assets = None
    if any(v is not None for v in (inventory, receivables, cash, oca)):
        current_assets = (inventory or 0) + (receivables or 0) + (cash or 0) + (oca or 0)
    current_liabilities = None
    st_borrow = _g(data, period, "short_term_borrowings")
    other_liab = _g(data, period, "other_liabilities")
    if any(v is not None for v in (payables, st_borrow, other_liab)):
        current_liabilities = (payables or 0) + (st_borrow or 0) + (other_liab or 0)

    # capital employed = net worth + total debt
    capital_employed = None
    if net_worth is not None:
        capital_employed = net_worth + (debt or 0)

    effective_tax_rate = _safe_div(tax, pbt)
    nopat = None
    if ebit is not None:
        tr = effective_tax_rate if effective_tax_rate is not None else 0.25
        nopat = ebit * (1 - tr)

    receivable_days = _safe_div(receivables, revenue)
    receivable_days = receivable_days * 365 if receivable_days is not None else None
    inventory_days = _safe_div(inventory, material_cost if material_cost else revenue)
    inventory_days = inventory_days * 365 if inventory_days is not None else None
    payable_days = _safe_div(payables, material_cost if material_cost else revenue)
    payable_days = payable_days * 365 if payable_days is not None else None
    ccc = None
    if receivable_days is not None and inventory_days is not None and payable_days is not None:
        ccc = receivable_days + inventory_days - payable_days

    ratios: dict[str, float | None] = {
        "revenue_growth": yoy_growth(revenue, _g(data, prev, "revenue")) if prev else None,
        "ebitda_growth": yoy_growth(ebitda, _g(data, prev, "ebitda")) if prev else None,
        "pat_growth": yoy_growth(pat, _g(data, prev, "pat")) if prev else None,
        "ebitda_margin": _safe_div(ebitda, revenue),
        "ebit_margin": _safe_div(ebit, revenue),
        "pat_margin": _safe_div(pat, revenue),
        "roe": _safe_div(pat, net_worth),
        "roce": _safe_div(ebit, capital_employed),
        "current_ratio": _safe_div(current_assets, current_liabilities),
        "quick_ratio": _safe_div(
            (current_assets - inventory) if current_assets is not None and inventory is not None else None,
            current_liabilities,
        ),
        "debt_equity": _safe_div(debt, net_worth),
        "debt_ebitda": _safe_div(debt, ebitda),
        "asset_turnover": _safe_div(revenue, total_assets),
        "receivable_days": receivable_days,
        "inventory_days": inventory_days,
        "payable_days": payable_days,
        "cash_conversion_cycle": ccc,
        "cfo_pat": _safe_div(cfo, pat),
        "capex_revenue": _safe_div(capex, revenue),
        "interest_coverage": _safe_div(ebit, finance_cost),
        "effective_tax_rate": effective_tax_rate,
        "nopat": nopat,
        "total_debt": debt,
    }
    return ratios


def compute_analytics(data: dict, periods: list[str]) -> dict[str, Any]:
    """Full multi-period analytics package."""
    per_period = {p: compute_period_ratios(data, periods, p) for p in periods}

    revenues = [_g(data, p, "revenue") for p in periods]
    ebitdas = [_g(data, p, "ebitda") for p in periods]
    pats = [_g(data, p, "pat") for p in periods]
    debts = [total_debt(data, p) for p in periods]
    margins = [per_period[p]["ebitda_margin"] for p in periods]

    n_years = len(periods) - 1
    rev_growths = [g for g in (per_period[p]["revenue_growth"] for p in periods) if g is not None]

    summary = {
        "revenue_cagr": cagr(revenues[0], revenues[-1], n_years) if n_years > 0 else None,
        "pat_cagr": cagr(pats[0], pats[-1], n_years) if n_years > 0 else None,
        "ebitda_cagr": cagr(ebitdas[0], ebitdas[-1], n_years) if n_years > 0 else None,
        "latest_revenue_growth": per_period[periods[-1]]["revenue_growth"] if periods else None,
        "latest_ebitda_margin": per_period[periods[-1]]["ebitda_margin"] if periods else None,
        "avg_ebitda_margin": (
            sum(m for m in margins if m is not None) / len([m for m in margins if m is not None])
            if any(m is not None for m in margins) else None
        ),
        "margin_change_pp": (
            (margins[-1] - margins[-2]) if len(margins) >= 2 and margins[-1] is not None and margins[-2] is not None
            else None
        ),
        "revenue_volatility": stddev(rev_growths),
        "earnings_volatility": (
            stddev([g for g in (yoy_growth(pats[i], pats[i - 1]) for i in range(1, len(pats))) if g is not None])
        ),
        "debt_trend": (
            yoy_growth(debts[-1], debts[0]) if len(debts) >= 2 and debts[0] not in (None, 0) and debts[-1] is not None
            else None
        ),
        "working_capital_trend": None,
    }

    # working capital trend: change in (receivables + inventory - payables) vs revenue growth
    def nwc(p):
        r, i, pay = _g(data, p, "receivables"), _g(data, p, "inventory"), _g(data, p, "trade_payables")
        if r is None and i is None and pay is None:
            return None
        return (r or 0) + (i or 0) - (pay or 0)

    nwcs = [nwc(p) for p in periods]
    if len(nwcs) >= 2 and nwcs[0] not in (None, 0) and nwcs[-1] is not None:
        summary["working_capital_trend"] = yoy_growth(nwcs[-1], nwcs[0])

    return {"per_period": per_period, "summary": summary, "periods": periods}
