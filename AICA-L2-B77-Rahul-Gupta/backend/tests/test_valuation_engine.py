"""Valuation engine tests: FCFF, discounting, terminal value, bridges, weights."""
import pytest

from app.services.valuation.engine import (
    ValuationInputs, adjusted_nav_valuation, dcf_valuation,
    market_multiple_valuation, run_valuation, run_scenarios,
    sensitivity_heatmap, tornado_analysis,
)

CR = 1e7


def make_inputs(**overrides) -> ValuationInputs:
    base = dict(
        base_revenue=11.59 * CR, base_ebitda_margin=0.18,
        base_depreciation_pct=0.03, base_capex_pct=0.05, base_nwc_pct=0.10,
        tax_rate=0.25, revenue_growth=0.16, wacc=0.12, terminal_growth=0.03,
        total_debt=0.42 * CR, cash=0.18 * CR, shares_outstanding=1_000_000,
        ev_ebitda_multiple=8.5, base_pat=1.38 * CR, net_worth=4.62 * CR,
    )
    base.update(overrides)
    return ValuationInputs(**base)


def test_dcf_year1_mechanics():
    inp = make_inputs()
    r = dcf_valuation(inp)
    y1 = r["years"][0]
    rev1 = 11.59 * CR * 1.16
    assert y1["revenue"] == pytest.approx(rev1)
    assert y1["ebitda"] == pytest.approx(rev1 * 0.18)
    ebit = rev1 * 0.18 - rev1 * 0.03
    assert y1["ebit"] == pytest.approx(ebit)
    nopat = ebit * 0.75
    assert y1["nopat"] == pytest.approx(nopat)
    delta_nwc = rev1 * 0.10 - 11.59 * CR * 0.10
    fcff = nopat + rev1 * 0.03 - rev1 * 0.05 - delta_nwc
    assert y1["fcff"] == pytest.approx(fcff)
    assert y1["pv_fcff"] == pytest.approx(fcff / 1.12)


def test_terminal_value_gordon():
    inp = make_inputs()
    r = dcf_valuation(inp)
    fcff5 = r["years"][-1]["fcff"]
    tv = fcff5 * 1.03 / (0.12 - 0.03)
    assert r["terminal_value"] == pytest.approx(tv)
    assert r["pv_terminal"] == pytest.approx(tv / 1.12**5)
    assert r["enterprise_value"] == pytest.approx(r["pv_explicit"] + r["pv_terminal"])


def test_ev_to_equity_bridge():
    r = dcf_valuation(make_inputs())
    assert r["equity_value"] == pytest.approx(
        r["enterprise_value"] - 0.42 * CR + 0.18 * CR)
    assert r["per_share_value"] == pytest.approx(r["equity_value"] / 1_000_000)


def test_wacc_must_exceed_terminal_growth():
    with pytest.raises(ValueError):
        dcf_valuation(make_inputs(wacc=0.03, terminal_growth=0.03))


def test_market_multiple():
    r = market_multiple_valuation(make_inputs())
    ev = 11.59 * CR * 0.18 * 8.5
    assert r["enterprise_value"] == pytest.approx(ev)
    assert r["equity_value"] == pytest.approx(ev - 0.42 * CR + 0.18 * CR)


def test_adjusted_nav_with_schedule():
    inp = make_inputs(nav_adjustments=[
        {"item": "land", "book_value": 1.0 * CR, "adjusted_value": 1.8 * CR, "note": "FMV"},
        {"item": "contingent_liability", "book_value": 0, "adjusted_value": -0.3 * CR, "note": ""},
    ])
    r = adjusted_nav_valuation(inp)
    assert r["equity_value"] == pytest.approx(4.62 * CR + 0.8 * CR - 0.3 * CR)


def test_weighted_central_estimate_and_range():
    r = run_valuation(make_inputs())
    evs = {m: v["enterprise_value"] for m, v in r["methods"].items()}
    expected = sum(evs[m] * r["weights"][m] for m in evs)
    assert r["central_estimate_ev"] == pytest.approx(expected)
    assert r["range_low_ev"] == pytest.approx(min(evs.values()))
    assert r["range_high_ev"] == pytest.approx(max(evs.values()))
    assert sum(r["weights"].values()) == pytest.approx(1.0)


def test_single_method_becomes_central_estimate():
    r = run_valuation(make_inputs(methods=["dcf"]))
    assert r["central_estimate_ev"] == pytest.approx(
        r["methods"]["dcf"]["enterprise_value"])
    assert r["range_low_ev"] == r["range_high_ev"]


def test_scenarios_ordering():
    s = run_scenarios(make_inputs())
    assert s["bear"]["enterprise_value"] < s["base"]["enterprise_value"] < s["bull"]["enterprise_value"]
    assert s["base"]["vs_base_pct"] == pytest.approx(0.0, abs=1e-9)


def test_sensitivity_heatmap_monotonic_in_wacc():
    hm = sensitivity_heatmap(make_inputs())
    row = hm["grid"][0]
    vals = [v for v in row if v is not None]
    assert vals == sorted(vals, reverse=True)  # higher WACC → lower value


def test_tornado_has_spans():
    rows = tornado_analysis(make_inputs())
    assert rows and all(r["span"] >= 0 for r in rows)
    spans = [r["span"] for r in rows]
    assert spans == sorted(spans, reverse=True)
