import pytest

from bsa import fundamentals as fd
from bsa import indicators as ind
from bsa import scoring, valuation


def test_dcf_matches_gordon_when_growth_is_constant():
    # Constant 5% growth for all 10 years and terminal: EV = FCF0 x 1.05 / (0.10 - 0.05) = 21 x FCF0.
    d = valuation.dcf_enterprise_value(100.0, 5.0, 5.0, 10.0)
    assert d["ev"] == pytest.approx(2100.0)


def test_dcf_rejects_wacc_below_growth():
    with pytest.raises(ValueError):
        valuation.dcf_enterprise_value(100.0, 5.0, 8.0, 8.0)


def test_justified_pb():
    assert valuation.justified_pb(15.0, 5.0, 12.0) == pytest.approx(10 / 7)
    assert valuation.justified_pb(4.0, 5.0, 12.0) is None


def test_cost_of_capital_blume_and_floor():
    a = valuation.ASSUMPTIONS
    c = valuation.cost_of_capital(1.0, 100.0, 0.0, a)
    assert c["beta_used"] == pytest.approx(1.0)
    assert c["cost_of_equity"] == pytest.approx(13.5)
    assert c["wacc"] == pytest.approx(13.5)
    low = valuation.cost_of_capital(0.1, 100.0, 900.0, a)
    assert low["beta_used"] == pytest.approx(0.7)       # bounded
    assert low["wacc"] == pytest.approx(10.0)           # floor


def _setup(raw):
    fund = fd.build(raw, financial=False)
    tech = ind.technical_summary(raw.ohlc, raw.bench)
    cmp = raw.info["currentPrice"]
    return fund, tech, cmp


def test_blend_renormalises_and_excludes_outliers(synthetic_raw):
    fund, tech, cmp = _setup(synthetic_raw)
    v = valuation.value(cmp, synthetic_raw.info, fund, tech, {"pe": None, "pb": None})
    included = [m for m in v["methods"] if m["included"]]
    assert sum(m["weight"] for m in included) == pytest.approx(100.0)
    assert v["target"] == pytest.approx(sum(m["value"] * m["weight"] / 100 for m in included))
    # Force the consensus to an outlier and check it is dropped.
    info = dict(synthetic_raw.info, targetMeanPrice=cmp * 5)
    v2 = valuation.value(cmp, info, fund, tech, {"pe": None, "pb": None})
    cons = [m for m in v2["methods"] if m["key"] == "consensus"][0]
    assert not cons["included"] and "outlier" in cons["note"]


def test_forward_eps_cap(synthetic_raw):
    fund, tech, cmp = _setup(synthetic_raw)
    info = dict(synthetic_raw.info, forwardEps=13.31 * 2)
    v = valuation.value(cmp, info, fund, tech, {"pe": 20.0, "pb": None})
    rel = v["methods"][0]
    assert "capped at 1.4x" in rel["inputs"]["Forward EPS (12m)"]


@pytest.mark.parametrize("upside,score,expected", [
    (20.0, 60.0, "BUY"),
    (20.0, 45.0, "HOLD"),     # quality gate
    (10.0, 60.0, "HOLD"),
    (2.0, 30.0, "SELL"),      # weak-stock gate
    (2.0, 40.0, "HOLD"),
    (-10.0, 80.0, "SELL"),
    (15.0, 50.0, "BUY"),      # boundaries are inclusive
    (-5.0, 50.0, "HOLD"),
])
def test_rating_rules(upside, score, expected):
    assert scoring.rating(upside, score, 3, 20.0)["rating"] == expected


def test_rating_without_target():
    r = scoring.rating(None, 70.0, 0, None)
    assert r["rating"] == "HOLD" and r["not_rated_on_valuation"] and r["conviction"] == "Low"


def test_conviction():
    assert scoring.rating(30.0, 70.0, 3, 20.0)["conviction"] == "High"
    assert scoring.rating(30.0, 70.0, 1, None)["conviction"] == "Low"
    assert scoring.rating(30.0, 70.0, 3, 80.0)["conviction"] == "Low"
    assert scoring.rating(30.0, 55.0, 3, 20.0)["conviction"] == "Medium"


def test_lin_and_rsi_score():
    assert scoring.lin(10, 0, 20) == pytest.approx(50.0)
    assert scoring.lin(1.5, 1.5, 0.0) == pytest.approx(0.0)     # reversed scale
    assert scoring.lin(-1, 1.5, 0.0) == pytest.approx(100.0)
    assert scoring.rsi_score(55) == 100.0
    assert scoring.rsi_score(80) == 0.0


def test_scorecard_weights(synthetic_raw):
    fund, tech, cmp = _setup(synthetic_raw)
    v = valuation.value(cmp, synthetic_raw.info, fund, tech, {"pe": None, "pb": None})
    sc = scoring.scorecard(fund, v, tech)
    assert [p["pillar"] for p in sc["pillars"]] == list(scoring.PILLAR_WEIGHTS)
    avail = [p for p in sc["pillars"] if p["score"] is not None]
    expected = sum(p["score"] * p["weight"] for p in avail) / sum(p["weight"] for p in avail)
    assert sc["composite"] == pytest.approx(expected)
    assert 0 <= sc["composite"] <= 100
