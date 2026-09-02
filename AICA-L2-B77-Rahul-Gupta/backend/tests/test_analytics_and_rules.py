"""Analytics (CAGR, margins) + accounting validation + rules-engine tests."""
import pytest

from app.rules import evaluate_rules
from app.services.financial.analytics import cagr, compute_analytics
from app.services.financial.validation import validate_all

CR = 1e7

DATA = {
    "FY2022-23": {"revenue": 6.10 * CR, "ebitda": 0.96 * CR, "pat": 0.57 * CR,
                  "pbt": 0.76 * CR, "tax": 0.19 * CR, "net_worth": 2.72 * CR,
                  "total_assets": 4.43 * CR, "total_liabilities": 1.71 * CR,
                  "cfo": 0.71 * CR, "receivables": 0.92 * CR,
                  "opening_cash": 0.14 * CR, "closing_cash": 0.28 * CR,
                  "cfi": -0.52 * CR, "cff": -0.05 * CR},
    "FY2023-24": {"revenue": 8.05 * CR, "ebitda": 1.41 * CR, "pat": 0.87 * CR,
                  "pbt": 1.17 * CR, "tax": 0.30 * CR, "net_worth": 3.44 * CR,
                  "total_assets": 5.60 * CR, "total_liabilities": 2.16 * CR,
                  "cfo": 0.95 * CR, "receivables": 1.28 * CR,
                  "opening_cash": 0.28 * CR, "closing_cash": 0.35 * CR,
                  "cfi": -0.62 * CR, "cff": -0.26 * CR},
    "FY2024-25": {"revenue": 11.59 * CR, "ebitda": 2.17 * CR, "pat": 1.38 * CR,
                  "pbt": 1.85 * CR, "tax": 0.47 * CR, "net_worth": 4.62 * CR,
                  "total_assets": 7.15 * CR, "total_liabilities": 2.53 * CR,
                  "cfo": 1.15 * CR, "receivables": 1.90 * CR,
                  "opening_cash": 0.35 * CR, "closing_cash": 0.18 * CR,
                  "cfi": -0.85 * CR, "cff": -0.47 * CR},
}
PERIODS = list(DATA.keys())


def test_cagr():
    assert cagr(100, 200, 2) == pytest.approx(0.41421356)
    assert cagr(6.10, 11.59, 2) == pytest.approx((11.59 / 6.10) ** 0.5 - 1)
    assert cagr(0, 100, 2) is None


def test_analytics_summary():
    a = compute_analytics(DATA, PERIODS)
    s = a["summary"]
    assert s["latest_revenue_growth"] == pytest.approx(11.59 / 8.05 - 1, rel=1e-6)
    assert s["latest_ebitda_margin"] == pytest.approx(2.17 / 11.59, rel=1e-6)
    latest = a["per_period"]["FY2024-25"]
    assert latest["cfo_pat"] == pytest.approx(1.15 / 1.38, rel=1e-6)
    assert latest["pat_margin"] == pytest.approx(1.38 / 11.59, rel=1e-6)


def test_validation_passes_on_coherent_books():
    v = validate_all(DATA, PERIODS)
    assert v["ok"], [c for c in v["checks"] if c["status"] == "fail"]


def test_validation_catches_broken_balance_sheet():
    broken = {p: dict(m) for p, m in DATA.items()}
    broken["FY2024-25"]["total_assets"] = 9.99 * CR
    v = validate_all(broken, PERIODS)
    assert not v["ok"]
    fails = [c["code"] for c in v["checks"] if c["status"] == "fail"]
    assert "BS_EQUATION" in fails


def test_rev_growth_rule_triggers_at_44_pct():
    a = compute_analytics(DATA, PERIODS)
    triggers = evaluate_rules(a)
    codes = [t["rule_code"] for t in triggers]
    assert "REV_GROWTH_HIGH" in codes
    trig = next(t for t in triggers if t["rule_code"] == "REV_GROWTH_HIGH")
    assert trig["observed_value"] == pytest.approx(0.43975, rel=1e-3)
    assert trig["severity"] == "high"


def test_no_false_debt_trigger():
    a = compute_analytics(DATA, PERIODS)
    codes = [t["rule_code"] for t in evaluate_rules(a)]
    assert "DEBT_EQUITY_HIGH" not in codes


def test_fact_based_customer_concentration_rule():
    a = compute_analytics(DATA, PERIODS)
    codes = [t["rule_code"] for t in evaluate_rules(a, {"largest_customer_share": 0.30})]
    assert "CUSTOMER_CONCENTRATION" in codes
