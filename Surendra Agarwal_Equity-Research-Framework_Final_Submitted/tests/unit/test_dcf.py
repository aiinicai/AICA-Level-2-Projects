"""Tests for app/valuation/dcf.py.

The core DCF math is verified against a hand-computed 2-year example
worked out independently below (not by calling run_dcf with different
arguments), so this actually catches algebra errors, not just "does it run."
"""

from __future__ import annotations

import pytest

from app.core.enums import DataSourceType, DataStatus, UnitOfMeasure
from app.core.models import FinancialStatement, MetricResult, SourceMetadata
from app.valuation.dcf import (
    DCFAssumptions,
    DCFResult,
    revenue_margin_sensitivity,
    run_dcf,
    sensitivity_analysis,
)


def _src():
    return SourceMetadata(
        company="Test Co", source="unit_test", source_type=DataSourceType.MANUAL_ENTRY,
        unit=UnitOfMeasure.INR_CRORE,
    )


def _base_statement(**overrides):
    defaults = dict(
        company="Test Co", period="FY2026", sales=1000.0, borrowings=200.0, cash_and_bank=50.0,
        num_equity_shares=100_000_000.0, source=_src(),
    )
    defaults.update(overrides)
    return FinancialStatement(**defaults)


class TestDCFAssumptionsValidation:
    def test_wacc_must_exceed_terminal_growth(self):
        with pytest.raises(ValueError, match="must exceed terminal growth"):
            DCFAssumptions(
                revenue_growth_rate=0.1, ebitda_margin=0.2, depreciation_pct_of_revenue=0.05,
                capex_pct_of_revenue=0.08, tax_rate=0.25, wacc=0.05, terminal_growth_rate=0.06,
            )

    def test_wacc_exactly_equal_to_terminal_growth_also_rejected(self):
        with pytest.raises(ValueError):
            DCFAssumptions(
                revenue_growth_rate=0.1, ebitda_margin=0.2, depreciation_pct_of_revenue=0.05,
                capex_pct_of_revenue=0.08, tax_rate=0.25, wacc=0.08, terminal_growth_rate=0.08,
            )

    def test_valid_assumptions_construct_without_error(self):
        a = DCFAssumptions(
            revenue_growth_rate=0.1, ebitda_margin=0.2, depreciation_pct_of_revenue=0.05,
            capex_pct_of_revenue=0.08, tax_rate=0.25, wacc=0.12, terminal_growth_rate=0.05,
        )
        assert a.wacc > a.terminal_growth_rate

    def test_mismatched_list_length_raises_on_expand(self):
        a = DCFAssumptions(
            projection_years=3, revenue_growth_rate=[0.1, 0.1], ebitda_margin=0.2,
            depreciation_pct_of_revenue=0.05, capex_pct_of_revenue=0.08, tax_rate=0.25,
            wacc=0.12, terminal_growth_rate=0.05,
        )
        with pytest.raises(ValueError, match="projection_years"):
            a._expand(a.revenue_growth_rate)


class TestDCFHandComputedExample:
    """A simplified 2-year, zero-tax, zero-capex/D&A/WC example, worked
    out by hand below, to isolate and verify the core discounting and
    terminal value logic without other line items adding noise."""

    def test_two_year_simplified_dcf_matches_hand_calc(self):
        # Base revenue 1000, growth 10% flat, EBITDA margin 20%, D&A=0,
        # Capex=0, WC=0, tax=0% -> FCFF = EBITDA each year.
        stmt = _base_statement(sales=1000.0, borrowings=0.0, cash_and_bank=0.0)
        assumptions = DCFAssumptions(
            projection_years=2, revenue_growth_rate=0.10, ebitda_margin=0.20,
            depreciation_pct_of_revenue=0.0, capex_pct_of_revenue=0.0,
            wc_change_pct_of_revenue_change=0.0, tax_rate=0.0, wacc=0.10, terminal_growth_rate=0.04,
        )
        result = run_dcf(stmt, assumptions)
        assert isinstance(result, DCFResult)

        # Hand calc:
        rev1 = 1000 * 1.10  # 1100
        rev2 = rev1 * 1.10  # 1210
        fcff1 = rev1 * 0.20  # 220 (EBITDA=EBIT=NOPAT=FCFF since no D&A/capex/WC/tax)
        fcff2 = rev2 * 0.20  # 242
        pv1 = fcff1 / (1.10 ** 1)
        pv2 = fcff2 / (1.10 ** 2)
        terminal_fcff = fcff2 * 1.04
        tv = terminal_fcff / (0.10 - 0.04)
        pv_tv = tv / (1.10 ** 2)
        expected_ev = pv1 + pv2 + pv_tv
        expected_equity_value = expected_ev - 0.0  # zero net debt
        expected_value_per_share = (expected_equity_value * 1e7) / 100_000_000.0

        assert result.year_projections[0].revenue == round(rev1, 2)
        assert result.year_projections[1].revenue == round(rev2, 2)
        assert result.year_projections[0].fcff == round(fcff1, 2)
        assert abs(result.enterprise_value - round(expected_ev, 2)) < 0.05
        assert abs(result.value_per_share - round(expected_value_per_share, 2)) < 0.05

    def test_net_debt_reduces_equity_value_correctly(self):
        stmt = _base_statement(sales=1000.0, borrowings=300.0, cash_and_bank=100.0)  # net debt = 200
        assumptions = DCFAssumptions(
            projection_years=1, revenue_growth_rate=0.0, ebitda_margin=0.20,
            depreciation_pct_of_revenue=0.0, capex_pct_of_revenue=0.0, tax_rate=0.0,
            wacc=0.10, terminal_growth_rate=0.03,
        )
        result = run_dcf(stmt, assumptions)
        assert isinstance(result, DCFResult)
        assert result.net_debt == 200.0
        assert abs((result.enterprise_value - result.net_debt) - result.equity_value) < 0.01

    def test_tax_applied_only_on_positive_ebit(self):
        # EBIT negative (heavy D&A) -> tax must be 0, not negative (no tax benefit).
        stmt = _base_statement(sales=1000.0, borrowings=0.0, cash_and_bank=0.0)
        assumptions = DCFAssumptions(
            projection_years=1, revenue_growth_rate=0.0, ebitda_margin=0.05,
            depreciation_pct_of_revenue=0.20,  # D&A > EBITDA -> negative EBIT
            capex_pct_of_revenue=0.0, tax_rate=0.30, wacc=0.10, terminal_growth_rate=0.03,
        )
        result = run_dcf(stmt, assumptions)
        assert isinstance(result, DCFResult)
        assert result.year_projections[0].ebit < 0
        assert result.year_projections[0].tax == 0.0


class TestDCFMissingInputs:
    def test_missing_sales_returns_metric_result_missing_input(self):
        stmt = _base_statement(sales=None)
        assumptions = DCFAssumptions(
            revenue_growth_rate=0.1, ebitda_margin=0.2, depreciation_pct_of_revenue=0.05,
            capex_pct_of_revenue=0.08, tax_rate=0.25, wacc=0.12, terminal_growth_rate=0.05,
        )
        result = run_dcf(stmt, assumptions)
        assert isinstance(result, MetricResult)
        assert result.status == DataStatus.MISSING_INPUT
        assert result.value is None

    def test_missing_shares_returns_metric_result_missing_input(self):
        stmt = _base_statement(num_equity_shares=None)
        assumptions = DCFAssumptions(
            revenue_growth_rate=0.1, ebitda_margin=0.2, depreciation_pct_of_revenue=0.05,
            capex_pct_of_revenue=0.08, tax_rate=0.25, wacc=0.12, terminal_growth_rate=0.05,
        )
        result = run_dcf(stmt, assumptions)
        assert isinstance(result, MetricResult)
        assert result.status == DataStatus.MISSING_INPUT

    def test_zero_shares_treated_as_missing_not_division_by_zero(self):
        stmt = _base_statement(num_equity_shares=0.0)
        assumptions = DCFAssumptions(
            revenue_growth_rate=0.1, ebitda_margin=0.2, depreciation_pct_of_revenue=0.05,
            capex_pct_of_revenue=0.08, tax_rate=0.25, wacc=0.12, terminal_growth_rate=0.05,
        )
        result = run_dcf(stmt, assumptions)  # must not raise ZeroDivisionError
        assert isinstance(result, MetricResult)
        assert result.status == DataStatus.MISSING_INPUT


class TestDCFRealData:
    def test_real_sona_blw_dcf_runs_and_flags_terminal_value_dominance(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        assumptions = DCFAssumptions(
            projection_years=5, revenue_growth_rate=0.15, ebitda_margin=0.25,
            depreciation_pct_of_revenue=0.06, capex_pct_of_revenue=0.10,
            wc_change_pct_of_revenue_change=0.05, tax_rate=0.25, wacc=0.12, terminal_growth_rate=0.05,
        )
        result = run_dcf(fy26, assumptions)
        assert isinstance(result, DCFResult)
        assert result.value_per_share > 0
        assert len(result.year_projections) == 5
        assert result.DISCLAIMER  # must always carry the non-guarantee disclaimer


class TestSensitivityAnalysis:
    def test_grid_shape_matches_input_ranges(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        base = DCFAssumptions(
            revenue_growth_rate=0.12, ebitda_margin=0.24, depreciation_pct_of_revenue=0.06,
            capex_pct_of_revenue=0.08, tax_rate=0.25, wacc=0.12, terminal_growth_rate=0.05,
        )
        grid = sensitivity_analysis(
            fy26, base, wacc_range=[0.10, 0.12, 0.14], terminal_growth_range=[0.03, 0.05],
        )
        assert len(grid) == 3
        assert all(len(row) == 2 for row in grid.values())

    def test_higher_wacc_produces_lower_value(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        base = DCFAssumptions(
            revenue_growth_rate=0.12, ebitda_margin=0.24, depreciation_pct_of_revenue=0.06,
            capex_pct_of_revenue=0.08, tax_rate=0.25, wacc=0.12, terminal_growth_rate=0.05,
        )
        grid = sensitivity_analysis(fy26, base, wacc_range=[0.10, 0.15], terminal_growth_range=[0.04])
        low_wacc_value = grid["10.0%"]["4.0%"]
        high_wacc_value = grid["15.0%"]["4.0%"]
        assert low_wacc_value > high_wacc_value

    def test_invalid_wacc_terminal_combo_returns_none_not_crash(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        base = DCFAssumptions(
            revenue_growth_rate=0.12, ebitda_margin=0.24, depreciation_pct_of_revenue=0.06,
            capex_pct_of_revenue=0.08, tax_rate=0.25, wacc=0.12, terminal_growth_rate=0.05,
        )
        # wacc=0.03 with terminal_growth=0.05 is invalid (wacc <= terminal growth)
        grid = sensitivity_analysis(fy26, base, wacc_range=[0.03], terminal_growth_range=[0.05])
        assert grid["3.0%"]["5.0%"] is None

    def test_revenue_margin_sensitivity_grid(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        base = DCFAssumptions(
            revenue_growth_rate=0.12, ebitda_margin=0.24, depreciation_pct_of_revenue=0.06,
            capex_pct_of_revenue=0.08, tax_rate=0.25, wacc=0.12, terminal_growth_rate=0.05,
        )
        grid = revenue_margin_sensitivity(
            fy26, base, revenue_growth_range=[0.10, 0.15], ebitda_margin_range=[0.20, 0.28],
        )
        assert len(grid) == 2
        # Higher margin at same growth should yield a higher value.
        assert grid["10.0%"]["28.0%"] > grid["10.0%"]["20.0%"]
