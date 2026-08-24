"""Tests for app/valuation/scenarios.py."""

from __future__ import annotations

from app.core.enums import DataSourceType, DataStatus, UnitOfMeasure
from app.core.models import FinancialStatement, SourceMetadata
from app.valuation.dcf import DCFAssumptions, DCFResult
from app.valuation.scenarios import (
    ScenarioSet,
    build_conservative_bear_case,
    build_optimistic_bull_case,
    run_scenarios,
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


def _base_assumptions(**overrides):
    defaults = dict(
        projection_years=5, revenue_growth_rate=0.12, ebitda_margin=0.22,
        depreciation_pct_of_revenue=0.06, capex_pct_of_revenue=0.08,
        wc_change_pct_of_revenue_change=0.03, tax_rate=0.25, wacc=0.12, terminal_growth_rate=0.05,
    )
    defaults.update(overrides)
    return DCFAssumptions(**defaults)


class TestBearBullConstructors:
    def test_bear_case_has_lower_growth_and_margin_than_base(self):
        base = _base_assumptions()
        bear = build_conservative_bear_case(base, growth_haircut=0.05, margin_haircut=0.03)
        assert bear.revenue_growth_rate == base.revenue_growth_rate - 0.05
        assert bear.ebitda_margin == base.ebitda_margin - 0.03

    def test_bull_case_has_higher_growth_and_margin_than_base(self):
        base = _base_assumptions()
        bull = build_optimistic_bull_case(base, growth_uplift=0.04, margin_uplift=0.02)
        assert bull.revenue_growth_rate == base.revenue_growth_rate + 0.04
        assert bull.ebitda_margin == base.ebitda_margin + 0.02

    def test_haircut_never_pushes_growth_negative_below_floor(self):
        base = _base_assumptions(revenue_growth_rate=0.02)
        bear = build_conservative_bear_case(base, growth_haircut=0.10, margin_haircut=0.01)
        assert bear.revenue_growth_rate == 0.0  # floored, not negative

    def test_other_assumptions_unchanged_by_haircut(self):
        base = _base_assumptions()
        bear = build_conservative_bear_case(base, growth_haircut=0.05, margin_haircut=0.03)
        assert bear.wacc == base.wacc
        assert bear.tax_rate == base.tax_rate
        assert bear.terminal_growth_rate == base.terminal_growth_rate


class TestRunScenarios:
    def test_all_three_scenarios_produced(self):
        stmt = _base_statement()
        base = _base_assumptions()
        bear = build_conservative_bear_case(base, growth_haircut=0.06, margin_haircut=0.04)
        bull = build_optimistic_bull_case(base, growth_uplift=0.05, margin_uplift=0.03)
        result = run_scenarios(stmt, bear_assumptions=bear, base_assumptions=base, bull_assumptions=bull)
        assert isinstance(result, ScenarioSet)
        assert isinstance(result.bear, DCFResult)
        assert isinstance(result.base, DCFResult)
        assert isinstance(result.bull, DCFResult)

    def test_bear_less_than_base_less_than_bull(self):
        stmt = _base_statement()
        base = _base_assumptions()
        bear = build_conservative_bear_case(base, growth_haircut=0.06, margin_haircut=0.04)
        bull = build_optimistic_bull_case(base, growth_uplift=0.05, margin_uplift=0.03)
        result = run_scenarios(stmt, bear_assumptions=bear, base_assumptions=base, bull_assumptions=bull)
        assert result.bear.value_per_share < result.base.value_per_share < result.bull.value_per_share

    def test_real_sona_blw_scenarios(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        base = _base_assumptions(revenue_growth_rate=0.15, ebitda_margin=0.25)
        bear = build_conservative_bear_case(base, growth_haircut=0.08, margin_haircut=0.05)
        bull = build_optimistic_bull_case(base, growth_uplift=0.05, margin_uplift=0.02)
        result = run_scenarios(fy26, bear_assumptions=bear, base_assumptions=base, bull_assumptions=bull)
        assert result.bear.value_per_share < result.base.value_per_share < result.bull.value_per_share
        assert result.bear_status_note is None  # no error note when scenario succeeds

    def test_scenario_with_missing_base_data_reports_note_not_crash(self):
        stmt = _base_statement(sales=None)  # will fail run_dcf for all three
        base = _base_assumptions()
        bear = build_conservative_bear_case(base, growth_haircut=0.05, margin_haircut=0.03)
        bull = build_optimistic_bull_case(base, growth_uplift=0.05, margin_uplift=0.03)
        result = run_scenarios(stmt, bear_assumptions=bear, base_assumptions=base, bull_assumptions=bull)
        assert result.bear is None
        assert result.base is None
        assert result.bull is None
        assert result.base_status_note is not None
