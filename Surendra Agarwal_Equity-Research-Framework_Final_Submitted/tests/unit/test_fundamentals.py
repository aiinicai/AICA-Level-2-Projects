"""Tests for app/analysis/fundamentals.py.

Reference values below are hand-computed from the real Sona BLW FY2026
figures (visible directly in the source workbook / prior tool output),
not just "does it run" checks.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.core.enums import Currency, DataSourceType, DataStatus, UnitOfMeasure
from app.core.models import FinancialStatement, SourceMetadata
from app.analysis.fundamentals import (
    compute_asset_turnover,
    compute_current_ratio,
    compute_debt_to_equity,
    compute_ebit,
    compute_ebit_margin,
    compute_ebitda,
    compute_ebitda_margin,
    compute_gross_margin,
    compute_net_debt_to_ebitda,
    compute_pat_cagr,
    compute_pat_margin,
    compute_revenue_cagr,
    compute_roce,
    compute_roe,
)


def _src():
    return SourceMetadata(
        company="Test", source="unit_test", source_type=DataSourceType.MANUAL_ENTRY,
        unit=UnitOfMeasure.INR_CRORE,
    )


class TestEbitdaEbitBackSolve:
    def test_fy2026_ebitda_matches_hand_calc(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        # PBT - OtherIncome + Depreciation + Interest = 857.25 - 95.2 + 259.94 + 18.74
        expected = 857.25 - 95.2 + 259.94 + 18.74
        result = compute_ebitda(fy26)
        assert result.status == DataStatus.OK
        assert result.value == round(expected, 2)

    def test_fy2026_ebit_matches_hand_calc(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        expected_ebitda = 857.25 - 95.2 + 259.94 + 18.74
        expected_ebit = expected_ebitda - 259.94
        result = compute_ebit(fy26)
        assert result.value == round(expected_ebit, 2)

    def test_missing_pbt_returns_missing_input_not_zero(self):
        stmt = FinancialStatement(company="Test", period="FY2024", source=_src())
        result = compute_ebitda(stmt)
        assert result.status == DataStatus.MISSING_INPUT
        assert result.value is None  # never fabricated as 0.0


class TestMargins:
    def test_fy2026_ebitda_margin(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_ebitda_margin(fy26)
        assert result.status == DataStatus.OK
        # 1040.73 / 4123.67
        assert abs(result.value - (1040.73 / 4123.67)) < 1e-4

    def test_fy2026_pat_margin_exact(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_pat_margin(fy26)
        assert result.value == round(646.42 / 4123.67, 4)

    def test_gross_margin_flagged_as_approximation(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_gross_margin(fy26)
        assert result.status == DataStatus.OK
        assert result.data_quality_notes  # must carry the approximation caveat

    def test_zero_sales_does_not_raise_division_error(self):
        stmt = FinancialStatement(company="Test", period="FY2024", sales=0.0, net_profit=10.0, source=_src())
        result = compute_pat_margin(stmt)
        assert result.status == DataStatus.MISSING_INPUT  # 0 treated as falsy/invalid denominator
        assert result.value is None


class TestReturnsRatios:
    def test_fy2026_roe(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        equity = 621.85 + 5219.65
        result = compute_roe(fy26)
        assert result.value == round(646.42 / equity, 4)

    def test_fy2026_roce(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        expected_ebit = (857.25 - 95.2 + 259.94 + 18.74) - 259.94
        capital_employed = 621.85 + 5219.65 + 363.41
        result = compute_roce(fy26)
        assert result.value == round(expected_ebit / capital_employed, 4)
        assert result.data_quality_notes  # approximation caveat present

    def test_roe_missing_equity_returns_missing_input(self):
        stmt = FinancialStatement(company="Test", period="FY2024", net_profit=10.0, source=_src())
        result = compute_roe(stmt)
        assert result.status == DataStatus.MISSING_INPUT


class TestBalanceSheetRatios:
    def test_fy2026_debt_to_equity(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        equity = 621.85 + 5219.65
        result = compute_debt_to_equity(fy26)
        assert result.value == round(363.41 / equity, 4)

    def test_fy2026_net_debt_to_ebitda(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        net_debt = 363.41 - 220.76
        ebitda = 857.25 - 95.2 + 259.94 + 18.74
        result = compute_net_debt_to_ebitda(fy26)
        assert result.value == round(net_debt / ebitda, 4)

    def test_current_ratio_explicitly_not_applicable(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_current_ratio(fy26)
        assert result.status == DataStatus.NOT_APPLICABLE
        assert result.value is None
        assert result.data_quality_notes

    def test_fy2026_asset_turnover(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_asset_turnover(fy26)
        assert result.value == round(4123.67 / 6976.44, 4)

    def test_zero_ebitda_does_not_raise_in_net_debt_ratio(self):
        stmt = FinancialStatement(
            company="Test", period="FY2024", borrowings=100.0, cash_and_bank=10.0,
            profit_before_tax=0.0, other_income=0.0, depreciation=0.0, interest=0.0,
            source=_src(),
        )
        result = compute_net_debt_to_ebitda(stmt)  # EBITDA = 0 -> must not raise ZeroDivisionError
        assert result.status == DataStatus.MISSING_INPUT
        assert result.value is None


class TestGrowthCagr:
    def test_fy2023_to_fy2026_revenue_cagr(self, sona_blw_statements):
        # Sales FY2023=2447.67, FY2026=4123.67, 3-year CAGR
        expected = (4123.67 / 2447.67) ** (1 / 3) - 1
        result = compute_revenue_cagr(sona_blw_statements, years=3)
        assert result.status == DataStatus.OK
        assert abs(result.value - round(expected, 4)) < 1e-4
        assert result.period == "FY2023-FY2026"

    def test_cagr_insufficient_history_returns_status_not_crash(self):
        stmt = FinancialStatement(company="Test", period="FY2024", sales=100.0, source=_src())
        result = compute_revenue_cagr([stmt], years=3)
        assert result.status == DataStatus.MISSING_INPUT

    def test_cagr_across_loss_making_base_year_returns_missing_not_complex_number(self):
        s1 = FinancialStatement(
            company="Test", period="FY2021", period_end_date=date(2021, 3, 31),
            sales=-50.0, source=_src(),
        )
        s2 = FinancialStatement(
            company="Test", period="FY2022", period_end_date=date(2022, 3, 31),
            sales=10.0, source=_src(),
        )
        s3 = FinancialStatement(
            company="Test", period="FY2023", period_end_date=date(2023, 3, 31),
            sales=20.0, source=_src(),
        )
        s4 = FinancialStatement(
            company="Test", period="FY2024", period_end_date=date(2024, 3, 31),
            sales=30.0, source=_src(),
        )
        result = compute_revenue_cagr([s1, s2, s3, s4], years=3)
        assert result.status == DataStatus.MISSING_INPUT  # never a complex/NaN value
        assert result.value is None

    def test_full_10yr_pat_cagr_real_data(self, sona_blw_statements):
        result = compute_pat_cagr(sona_blw_statements, years=9)
        # FY2017=44.87, FY2026=646.42
        expected = (646.42 / 44.87) ** (1 / 9) - 1
        assert result.status == DataStatus.OK
        assert abs(result.value - round(expected, 4)) < 1e-4
