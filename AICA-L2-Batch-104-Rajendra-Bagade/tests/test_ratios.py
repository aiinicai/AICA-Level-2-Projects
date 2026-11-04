"""
The eleven Schedule III ratios.

Each ratio is checked against a hand-computed figure, so that a change to
the engine that alters a disclosed ratio fails here rather than in a
client's financial statements.
"""

from __future__ import annotations

import pytest

from auditlens.financials import Figures
from auditlens.ratios import VARIANCE_THRESHOLD, build_schedule, compute_ratios


@pytest.fixture
def simple() -> Figures:
    """A deliberately round set of figures, so every expected value is
    verifiable by hand."""
    f = Figures(financial_year="2024-25")
    f.current_assets = 30_00_000
    f.current_liabilities = 15_00_000
    f.inventories = 8_00_000
    f.trade_receivables = 12_00_000
    f.trade_payables = 6_00_000
    f.shareholders_equity = 50_00_000
    f.long_term_borrowings = 20_00_000
    f.short_term_borrowings = 5_00_000
    f.deferred_tax_liability = 5_00_000
    f.non_current_investments = 10_00_000
    f.revenue_from_operations = 100_00_000
    f.other_income = 2_00_000
    f.cost_of_materials = 60_00_000
    f.employee_benefits = 15_00_000
    f.finance_costs = 3_00_000
    f.depreciation = 4_00_000
    f.other_expenses = 8_00_000
    f.current_tax = 3_00_000
    f.principal_repayments = 2_00_000
    f.income_from_investments = 1_00_000
    return f


def get(results, key):
    return next(r for r in results if r.key == key)


def test_all_eleven_ratios_are_produced(simple):
    results = compute_ratios(simple)
    assert len(results) == 11
    expected = {
        "current_ratio", "debt_equity", "dscr", "roe", "inventory_turnover",
        "receivables_turnover", "payables_turnover", "net_capital_turnover",
        "net_profit", "roce", "roi",
    }
    assert {r.key for r in results} == expected


def test_derived_figures(simple):
    assert simple.total_debt == 25_00_000
    assert simple.total_income == 102_00_000
    assert simple.cogs == 60_00_000
    assert simple.total_expenses == 90_00_000
    assert simple.profit_before_tax == 12_00_000
    assert simple.profit_after_tax == 9_00_000
    assert simple.ebit == 15_00_000
    assert simple.working_capital == 15_00_000
    assert simple.capital_employed == 80_00_000


def test_current_ratio(simple):
    # 30,00,000 / 15,00,000
    assert get(compute_ratios(simple), "current_ratio").value == 2.00


def test_debt_equity_ratio(simple):
    # 25,00,000 / 50,00,000
    assert get(compute_ratios(simple), "debt_equity").value == 0.50


def test_debt_service_coverage_ratio(simple):
    # (9,00,000 + 4,00,000 + 3,00,000) / (3,00,000 + 2,00,000)
    assert get(compute_ratios(simple), "dscr").value == 3.20


def test_return_on_equity_uses_closing_equity_without_a_comparative(simple):
    r = get(compute_ratios(simple), "roe")
    assert r.value == 18.00          # 9,00,000 / 50,00,000
    assert r.unit == "%"
    assert "no comparative" in r.basis


def test_return_on_equity_uses_average_equity_with_a_comparative(simple):
    prior = Figures(financial_year="2023-24")
    prior.shareholders_equity = 40_00_000
    prior.revenue_from_operations = 90_00_000
    r = get(compute_ratios(simple, prior), "roe")
    # 9,00,000 / average of 50,00,000 and 40,00,000
    assert r.value == 20.00
    assert "average" in r.basis


def test_inventory_turnover(simple):
    assert get(compute_ratios(simple), "inventory_turnover").value == 7.50


def test_receivables_turnover_uses_credit_sales(simple):
    simple.credit_sales_ratio = 0.80
    # 80,00,000 / 12,00,000
    assert get(compute_ratios(simple), "receivables_turnover").value == 6.67


def test_payables_turnover_uses_credit_purchases(simple):
    simple.credit_purchase_ratio = 0.50
    # 30,00,000 / 6,00,000
    assert get(compute_ratios(simple), "payables_turnover").value == 5.00


def test_net_capital_turnover(simple):
    assert get(compute_ratios(simple), "net_capital_turnover").value == 6.67


def test_net_profit_ratio(simple):
    assert get(compute_ratios(simple), "net_profit").value == 9.00


def test_return_on_capital_employed(simple):
    # 15,00,000 / 80,00,000
    assert get(compute_ratios(simple), "roce").value == 18.75


def test_return_on_investment(simple):
    # 1,00,000 / 10,00,000
    assert get(compute_ratios(simple), "roi").value == 10.00


def test_negative_working_capital_is_flagged_not_hidden(simple):
    simple.current_liabilities = 40_00_000
    r = get(compute_ratios(simple), "net_capital_turnover")
    assert r.value is not None and r.value < 0
    assert "not meaningful" in r.note


def test_division_by_zero_returns_none_not_an_error(simple):
    simple.shareholders_equity = 0
    r = get(compute_ratios(simple), "debt_equity")
    assert r.value is None
    assert not r.computable


def test_no_investments_is_explained(simple):
    simple.non_current_investments = 0
    r = get(compute_ratios(simple), "roi")
    assert r.value is None
    assert "No investments" in r.note


# --------------------------------------------------------------------------
# The 25 per cent explanation requirement
# --------------------------------------------------------------------------

def test_variance_beyond_25_percent_requires_explanation(simple):
    prior = Figures(financial_year="2023-24")
    prior.current_assets = 20_00_000
    prior.current_liabilities = 15_00_000      # prior current ratio 1.33
    results = compute_ratios(simple, prior)
    r = get(results, "current_ratio")
    assert r.prior_value == 1.33
    assert r.variance == pytest.approx(0.5038, abs=0.001)
    assert r.requires_explanation
    assert r.direction == "increase"


def test_variance_within_25_percent_needs_no_explanation(simple):
    prior = Figures(financial_year="2023-24")
    prior.current_assets = 28_00_000
    prior.current_liabilities = 15_00_000      # prior current ratio 1.87
    r = get(compute_ratios(simple, prior), "current_ratio")
    assert abs(r.variance) < VARIANCE_THRESHOLD
    assert not r.requires_explanation


def test_threshold_is_strictly_above_25_percent(simple):
    prior = Figures(financial_year="2023-24")
    prior.current_assets = 32_00_000
    prior.current_liabilities = 20_00_000      # prior 1.60, current 2.00 = +25.0%
    r = get(compute_ratios(simple, prior), "current_ratio")
    assert r.variance == pytest.approx(0.25, abs=0.0001)
    assert not r.requires_explanation


def test_no_comparative_means_no_variance(simple):
    for r in compute_ratios(simple, None):
        assert r.variance is None
        assert not r.requires_explanation


def test_schedule_on_the_sample_client(engagement):
    sch = engagement.ratios
    assert len(sch.results) == 11
    # The synthetic client is seeded with a sharp profitability improvement.
    keys = {r.key for r in sch.to_explain}
    assert {"roe", "net_profit", "roce"}.issubset(keys)
    rows = sch.as_rows()
    assert len(rows) == 11
    assert all("Ratio" in row and "Numerator" in row for row in rows)
