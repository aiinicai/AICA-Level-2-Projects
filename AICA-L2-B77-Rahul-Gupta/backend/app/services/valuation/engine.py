"""Deterministic valuation engine — DCF (FCFF), Market Multiple, Adjusted NAV,
central estimate, indicative range, scenarios and sensitivity.

Every authoritative number is computed here in Python. The AI layer only
explains these results; it never produces them.

Monetary values are absolute INR throughout.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DEFAULT_WEIGHTS = {"dcf": 0.50, "market_multiple": 0.30, "adjusted_nav": 0.20}
FORECAST_YEARS = 5


@dataclass
class ValuationInputs:
    """Accepted assumptions + locked base financials for the valuation engine."""

    # base (latest normalised actuals, absolute INR)
    base_revenue: float
    base_ebitda_margin: float  # decimal, e.g. 0.18
    base_depreciation_pct: float  # of revenue
    base_capex_pct: float  # of revenue
    base_nwc_pct: float  # net working capital as % of revenue
    tax_rate: float  # decimal

    # forecast assumptions
    revenue_growth: float  # CAGR decimal for forecast window
    wacc: float
    terminal_growth: float

    # bridges
    total_debt: float = 0.0
    cash: float = 0.0
    shares_outstanding: float = 0.0

    # market multiple
    ev_ebitda_multiple: float | None = None
    pe_multiple: float | None = None
    ev_revenue_multiple: float | None = None
    base_pat: float | None = None

    # adjusted NAV
    net_worth: float | None = None
    nav_adjustments: list[dict] = field(default_factory=list)
    # each: {item, book_value, adjusted_value, note}

    method_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    methods: list[str] = field(default_factory=lambda: ["dcf", "market_multiple", "adjusted_nav"])


def dcf_valuation(inp: ValuationInputs) -> dict[str, Any]:
    """5-year FCFF DCF with Gordon terminal value."""
    if inp.wacc <= inp.terminal_growth:
        raise ValueError("WACC must exceed terminal growth rate")

    years = []
    revenue = inp.base_revenue
    prev_nwc = inp.base_nwc_pct * revenue
    pv_sum = 0.0
    fcff_last = 0.0

    for t in range(1, FORECAST_YEARS + 1):
        revenue = revenue * (1 + inp.revenue_growth)
        ebitda = revenue * inp.base_ebitda_margin
        depreciation = revenue * inp.base_depreciation_pct
        ebit = ebitda - depreciation
        tax = max(ebit, 0.0) * inp.tax_rate
        nopat = ebit - tax
        capex = revenue * inp.base_capex_pct
        nwc = revenue * inp.base_nwc_pct
        delta_nwc = nwc - prev_nwc
        prev_nwc = nwc
        fcff = nopat + depreciation - capex - delta_nwc
        discount = (1 + inp.wacc) ** t
        pv = fcff / discount
        pv_sum += pv
        fcff_last = fcff
        years.append({
            "year": t, "revenue": revenue, "ebitda": ebitda,
            "depreciation": depreciation, "ebit": ebit, "tax": tax,
            "nopat": nopat, "capex": capex, "delta_nwc": delta_nwc,
            "fcff": fcff, "discount_factor": 1 / discount, "pv_fcff": pv,
        })

    fcff_terminal = fcff_last * (1 + inp.terminal_growth)
    terminal_value = fcff_terminal / (inp.wacc - inp.terminal_growth)
    pv_terminal = terminal_value / ((1 + inp.wacc) ** FORECAST_YEARS)

    enterprise_value = pv_sum + pv_terminal
    equity_value = enterprise_value - inp.total_debt + inp.cash
    per_share = equity_value / inp.shares_outstanding if inp.shares_outstanding else None

    return {
        "method": "dcf",
        "years": years,
        "pv_explicit": pv_sum,
        "terminal_value": terminal_value,
        "pv_terminal": pv_terminal,
        "terminal_share_of_ev": pv_terminal / enterprise_value if enterprise_value else None,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "per_share_value": per_share,
        "key_driver": f"Discount Rate ({inp.wacc * 100:.1f}%)",
        "assumptions": {
            "revenue_growth": inp.revenue_growth,
            "ebitda_margin": inp.base_ebitda_margin,
            "wacc": inp.wacc,
            "terminal_growth": inp.terminal_growth,
            "tax_rate": inp.tax_rate,
            "capex_pct": inp.base_capex_pct,
            "nwc_pct": inp.base_nwc_pct,
        },
    }


def market_multiple_valuation(inp: ValuationInputs) -> dict[str, Any] | None:
    """EV/EBITDA primary; falls back to EV/Revenue or P/E if provided."""
    base_ebitda = inp.base_revenue * inp.base_ebitda_margin
    detail: dict[str, Any] = {"method": "market_multiple", "components": []}

    ev = None
    used = None
    if inp.ev_ebitda_multiple:
        ev = base_ebitda * inp.ev_ebitda_multiple
        used = f"EV/EBITDA ({inp.ev_ebitda_multiple:.1f}x)"
        detail["components"].append({
            "basis": "EV/EBITDA", "multiple": inp.ev_ebitda_multiple,
            "metric_value": base_ebitda, "enterprise_value": ev,
        })
    elif inp.ev_revenue_multiple:
        ev = inp.base_revenue * inp.ev_revenue_multiple
        used = f"EV/Revenue ({inp.ev_revenue_multiple:.1f}x)"
        detail["components"].append({
            "basis": "EV/Revenue", "multiple": inp.ev_revenue_multiple,
            "metric_value": inp.base_revenue, "enterprise_value": ev,
        })
    elif inp.pe_multiple and inp.base_pat:
        equity = inp.base_pat * inp.pe_multiple
        used = f"P/E ({inp.pe_multiple:.1f}x)"
        detail.update({
            "enterprise_value": equity + inp.total_debt - inp.cash,
            "equity_value": equity,
            "per_share_value": equity / inp.shares_outstanding if inp.shares_outstanding else None,
            "multiple_used": used,
            "key_driver": used,
        })
        return detail

    if ev is None:
        return None
    equity = ev - inp.total_debt + inp.cash
    detail.update({
        "enterprise_value": ev,
        "equity_value": equity,
        "per_share_value": equity / inp.shares_outstanding if inp.shares_outstanding else None,
        "multiple_used": used,
        "key_driver": used,
    })
    return detail


def adjusted_nav_valuation(inp: ValuationInputs) -> dict[str, Any] | None:
    """Book net worth plus explicit asset/liability revaluations."""
    if inp.net_worth is None:
        return None
    total_adjustment = 0.0
    schedule = []
    for adj in inp.nav_adjustments:
        delta = float(adj.get("adjusted_value", 0)) - float(adj.get("book_value", 0))
        total_adjustment += delta
        schedule.append({**adj, "delta": delta})
    equity = inp.net_worth + total_adjustment
    return {
        "method": "adjusted_nav",
        "book_net_worth": inp.net_worth,
        "total_adjustment": total_adjustment,
        "schedule": schedule,
        "nav_type": "Adjusted Tangible",
        "enterprise_value": equity + inp.total_debt - inp.cash,
        "equity_value": equity,
        "per_share_value": equity / inp.shares_outstanding if inp.shares_outstanding else None,
        "key_driver": "Adjusted Tangible NAV",
    }


def run_valuation(inp: ValuationInputs) -> dict[str, Any]:
    """Run all selected methods, weighted central estimate, indicative range."""
    methods: dict[str, dict] = {}
    if "dcf" in inp.methods:
        methods["dcf"] = dcf_valuation(inp)
    if "market_multiple" in inp.methods:
        mm = market_multiple_valuation(inp)
        if mm:
            methods["market_multiple"] = mm
    if "adjusted_nav" in inp.methods:
        nav = adjusted_nav_valuation(inp)
        if nav:
            methods["adjusted_nav"] = nav

    if not methods:
        raise ValueError("No valuation method could be computed")

    # normalise weights over available methods
    raw_weights = {m: inp.method_weights.get(m, 0.0) for m in methods}
    total_w = sum(raw_weights.values())
    if total_w <= 0:
        weights = {m: 1.0 / len(methods) for m in methods}
    else:
        weights = {m: w / total_w for m, w in raw_weights.items()}

    evs = {m: r["enterprise_value"] for m, r in methods.items() if r.get("enterprise_value") is not None}
    eqs = {m: r["equity_value"] for m, r in methods.items() if r.get("equity_value") is not None}

    central_ev = sum(evs[m] * weights[m] for m in evs)
    central_eq = sum(eqs[m] * weights[m] for m in eqs)
    range_low_ev, range_high_ev = min(evs.values()), max(evs.values())
    range_low_eq, range_high_eq = min(eqs.values()), max(eqs.values())

    per_share = central_eq / inp.shares_outstanding if inp.shares_outstanding else None

    return {
        "methods": methods,
        "weights": weights,
        "central_estimate_ev": central_ev,
        "central_estimate_equity": central_eq,
        "range_low_ev": range_low_ev,
        "range_high_ev": range_high_ev,
        "range_low_equity": range_low_eq,
        "range_high_equity": range_high_eq,
        "range_width_pct": (range_high_ev - range_low_ev) / central_ev if central_ev else None,
        "per_share_value": per_share,
        "bridge": {"total_debt": inp.total_debt, "cash": inp.cash,
                   "shares_outstanding": inp.shares_outstanding},
    }


# ---------------------------------------------------------------------------
# Sensitivity & scenarios
# ---------------------------------------------------------------------------

def _clone_with(inp: ValuationInputs, **overrides) -> ValuationInputs:
    from dataclasses import replace
    return replace(inp, **overrides)


def sensitivity_heatmap(inp: ValuationInputs,
                        wacc_values: list[float] | None = None,
                        growth_values: list[float] | None = None,
                        output: str = "equity") -> dict[str, Any]:
    """WACC × terminal-growth grid of DCF values."""
    wacc_values = wacc_values or [0.10, 0.12, 0.14, 0.16]
    growth_values = growth_values or [0.02, 0.03, 0.04, 0.05]
    grid = []
    for g in growth_values:
        row = []
        for w in wacc_values:
            if w <= g:
                row.append(None)
                continue
            r = dcf_valuation(_clone_with(inp, wacc=w, terminal_growth=g))
            row.append(r["equity_value"] if output == "equity" else r["enterprise_value"])
        grid.append(row)
    return {"wacc_values": wacc_values, "growth_values": growth_values,
            "grid": grid, "output": output}


TORNADO_SPEC = [
    ("revenue_growth", "Revenue Growth (CAGR)", 0.02),
    ("ebitda_margin", "EBITDA Margin", 0.02),
    ("ev_ebitda_multiple", "EV / EBITDA Multiple (Exit)", 1.0),
    ("wacc", "WACC", 0.01),
    ("terminal_growth", "Terminal Growth Rate", 0.005),
]


def tornado_analysis(inp: ValuationInputs, output: str = "ev") -> list[dict[str, Any]]:
    """One-at-a-time swing of each driver around base; sorted by impact."""
    base = run_valuation(inp)
    base_val = base["central_estimate_ev"] if output == "ev" else base["central_estimate_equity"]
    key_out = "central_estimate_ev" if output == "ev" else "central_estimate_equity"

    field_map = {
        "revenue_growth": "revenue_growth",
        "ebitda_margin": "base_ebitda_margin",
        "wacc": "wacc",
        "terminal_growth": "terminal_growth",
        "ev_ebitda_multiple": "ev_ebitda_multiple",
    }
    rows = []
    for key, label, delta in TORNADO_SPEC:
        f = field_map[key]
        cur = getattr(inp, f)
        if cur is None:
            continue
        try:
            lo = run_valuation(_clone_with(inp, **{f: cur - delta}))[key_out]
        except ValueError:
            lo = None
        try:
            hi = run_valuation(_clone_with(inp, **{f: cur + delta}))[key_out]
        except ValueError:
            hi = None
        if lo is None and hi is None:
            continue
        span = abs((hi or base_val) - (lo or base_val))
        rows.append({"key": key, "label": label, "delta": delta,
                     "low": lo, "high": hi, "base": base_val, "span": span})
    rows.sort(key=lambda r: r["span"], reverse=True)
    return rows


def assumption_impacts(inp: ValuationInputs, output: str = "ev") -> list[dict[str, Any]]:
    """Directional impact table: +2% growth, +2% margin, −1% WACC, +1x exit, +0.5% terminal."""
    base = run_valuation(inp)
    base_val = base["central_estimate_ev"] if output == "ev" else base["central_estimate_equity"]
    key_out = "central_estimate_ev" if output == "ev" else "central_estimate_equity"
    spec = [
        ("revenue_growth", "Revenue Growth (CAGR)", "revenue_growth", +0.02, "+2%"),
        ("ebitda_margin", "EBITDA Margin", "base_ebitda_margin", +0.02, "+2%"),
        ("wacc", "WACC", "wacc", -0.01, "-1%"),
        ("ev_ebitda_multiple", "EV / EBITDA Multiple (Exit)", "ev_ebitda_multiple", +1.0, "+1.0x"),
        ("terminal_growth", "Terminal Growth Rate", "terminal_growth", +0.005, "+0.5%"),
    ]
    rows = []
    for key, label, f, delta, change in spec:
        cur = getattr(inp, f)
        if cur is None:
            continue
        try:
            new_val = run_valuation(_clone_with(inp, **{f: cur + delta}))[key_out]
        except ValueError:
            continue
        rows.append({
            "key": key, "label": label, "change": change,
            "impact": new_val - base_val,
            "impact_pct": (new_val - base_val) / base_val if base_val else None,
        })
    rows.sort(key=lambda r: abs(r["impact"]), reverse=True)
    return rows


SCENARIO_PRESETS = {
    "bear": {"revenue_growth": -0.06, "ebitda_margin": -0.04, "wacc": +0.02,
             "terminal_growth": -0.01, "ev_ebitda_multiple": -2.0},
    "base": {},
    "bull": {"revenue_growth": +0.06, "ebitda_margin": +0.03, "wacc": -0.02,
             "terminal_growth": +0.01, "ev_ebitda_multiple": +2.0},
}


def scenario_inputs(inp: ValuationInputs, preset: str) -> ValuationInputs:
    deltas = SCENARIO_PRESETS.get(preset, {})
    field_map = {"revenue_growth": "revenue_growth", "ebitda_margin": "base_ebitda_margin",
                 "wacc": "wacc", "terminal_growth": "terminal_growth",
                 "ev_ebitda_multiple": "ev_ebitda_multiple"}
    overrides = {}
    for k, d in deltas.items():
        f = field_map[k]
        cur = getattr(inp, f)
        if cur is None:
            continue
        new = cur + d
        if f == "terminal_growth":
            new = max(new, 0.0)
        if f == "base_ebitda_margin":
            new = max(new, 0.01)
        overrides[f] = new
    # keep WACC > terminal growth
    out = _clone_with(inp, **overrides)
    if out.wacc <= out.terminal_growth:
        out = _clone_with(out, wacc=out.terminal_growth + 0.02)
    return out


def run_scenarios(inp: ValuationInputs) -> dict[str, Any]:
    results = {}
    base = run_valuation(inp)
    for name in ("bear", "base", "bull"):
        s_inp = scenario_inputs(inp, name)
        r = run_valuation(s_inp)
        results[name] = {
            "assumptions": {
                "revenue_growth": s_inp.revenue_growth,
                "ebitda_margin": s_inp.base_ebitda_margin,
                "wacc": s_inp.wacc,
                "terminal_growth": s_inp.terminal_growth,
                "ev_ebitda_multiple": s_inp.ev_ebitda_multiple,
            },
            "enterprise_value": r["central_estimate_ev"],
            "equity_value": r["central_estimate_equity"],
            "vs_base_pct": (
                (r["central_estimate_ev"] - base["central_estimate_ev"]) / base["central_estimate_ev"]
                if base["central_estimate_ev"] else None
            ),
        }
    return results
