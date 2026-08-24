"""Tests for app/valuation/multiples.py."""

from __future__ import annotations

from app.core.enums import DataSourceType, DataStatus, UnitOfMeasure
from app.core.models import FinancialStatement, SourceMetadata
from app.valuation.multiples import (
    compute_all_multiples,
    compute_enterprise_value,
    compute_ev_ebitda,
    compute_ev_sales,
    compute_market_cap,
    compute_pb,
    compute_pe,
)


def _src():
    return SourceMetadata(
        company="Test", source="unit_test", source_type=DataSourceType.MANUAL_ENTRY,
        unit=UnitOfMeasure.INR_CRORE,
    )


class TestMarketCapAndEV:
    def test_fy2026_market_cap_matches_hand_calc(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_market_cap(fy26)
        assert result.status == DataStatus.OK
        expected = (481.5 * 621846890.0) / 1e7
        assert abs(result.value - round(expected, 2)) < 0.5

    def test_fy2026_enterprise_value_matches_hand_calc(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        market_cap = compute_market_cap(fy26).value
        result = compute_enterprise_value(fy26)
        assert result.status == DataStatus.OK
        expected = market_cap + (363.41 - 220.76)
        assert abs(result.value - round(expected, 2)) < 0.5

    def test_missing_price_returns_missing_input(self):
        stmt = FinancialStatement(company="Test", period="FY2024", num_equity_shares=1000.0, source=_src())
        result = compute_market_cap(stmt)
        assert result.status == DataStatus.MISSING_INPUT
        assert result.value is None


class TestPE:
    def test_fy2026_pe_matches_hand_calc(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_pe(fy26)
        assert result.status == DataStatus.OK
        eps = (646.42 * 1e7) / 621846890.0
        expected_pe = 481.5 / eps
        assert abs(result.value - round(expected_pe, 2)) < 0.1

    def test_zero_eps_returns_missing_input_not_infinity(self):
        stmt = FinancialStatement(
            company="Test", period="FY2024", price=100.0, net_profit=0.0,
            num_equity_shares=1000.0, source=_src(),
        )
        result = compute_pe(stmt)
        assert result.status == DataStatus.MISSING_INPUT
        assert result.value is None


class TestEvEbitda:
    def test_fy2026_ev_ebitda_matches_hand_calc(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        ev = compute_enterprise_value(fy26).value
        ebitda = 857.25 - 95.2 + 259.94 + 18.74
        result = compute_ev_ebitda(fy26)
        assert result.status == DataStatus.OK
        assert abs(result.value - round(ev / ebitda, 2)) < 0.05


class TestPB:
    def test_fy2026_pb_matches_hand_calc(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        book_value_per_share = ((621.85 + 5219.65) * 1e7) / 621846890.0
        result = compute_pb(fy26)
        assert result.status == DataStatus.OK
        assert abs(result.value - round(481.5 / book_value_per_share, 2)) < 0.05

    def test_negative_book_value_returns_calculation_error(self):
        stmt = FinancialStatement(
            company="Test", period="FY2024", price=100.0, equity_share_capital=10.0,
            reserves=-500.0, num_equity_shares=1_000_000.0, source=_src(),
        )
        result = compute_pb(stmt)
        assert result.status == DataStatus.CALCULATION_ERROR
        assert result.value is None


class TestEvSales:
    def test_fy2026_ev_sales_matches_hand_calc(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        ev = compute_enterprise_value(fy26).value
        result = compute_ev_sales(fy26)
        assert result.status == DataStatus.OK
        assert abs(result.value - round(ev / 4123.67, 2)) < 0.05


class TestBatchHelper:
    def test_compute_all_multiples_returns_six_metrics(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        results = compute_all_multiples(fy26)
        assert len(results) == 6
        assert all(r.status == DataStatus.OK for r in results)

    def test_years_without_price_return_missing_input(self, sona_blw_statements):
        fy17 = next(s for s in sona_blw_statements if s.period == "FY2017")  # no price in source
        results = compute_all_multiples(fy17)
        pe_result = next(r for r in results if r.metric_name == "P/E")
        assert pe_result.status == DataStatus.MISSING_INPUT
