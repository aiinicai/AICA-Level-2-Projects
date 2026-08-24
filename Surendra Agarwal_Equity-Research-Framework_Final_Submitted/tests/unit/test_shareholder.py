"""Tests for app/analysis/shareholder.py."""

from __future__ import annotations

from app.core.enums import DataSourceType, DataStatus, UnitOfMeasure
from app.core.models import FinancialStatement, SourceMetadata
from app.analysis.shareholder import (
    compute_dividend_payout,
    compute_eps,
    compute_promoter_holding,
    compute_promoter_pledge,
)


def _src():
    return SourceMetadata(
        company="Test", source="unit_test", source_type=DataSourceType.MANUAL_ENTRY,
        unit=UnitOfMeasure.INR_CRORE,
    )


class TestEps:
    def test_fy2026_eps_matches_known_real_value(self, sona_blw_statements):
        # Cross-checked against Sona BLW's actual reported EPS (~10.4)
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_eps(fy26)
        assert result.status == DataStatus.OK
        assert 10.0 < result.value < 11.0

    def test_eps_hand_calc_exact(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        expected = (646.42 * 1e7) / 621846890.0
        result = compute_eps(fy26)
        assert result.value == round(expected, 2)

    def test_zero_shares_returns_missing_input_not_infinity(self):
        stmt = FinancialStatement(
            company="Test", period="FY2024", net_profit=100.0, num_equity_shares=0.0, source=_src()
        )
        result = compute_eps(stmt)
        assert result.status == DataStatus.MISSING_INPUT
        assert result.value is None


class TestDividendPayout:
    def test_fy2026_dividend_payout(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_dividend_payout(fy26)
        assert result.status == DataStatus.OK
        assert result.value == round(211.43 / 646.42, 4)

    def test_no_dividend_period_returns_missing_not_zero(self):
        stmt = FinancialStatement(company="Test", period="FY2024", net_profit=100.0, source=_src())
        result = compute_dividend_payout(stmt)
        assert result.status == DataStatus.MISSING_INPUT
        assert result.value is None


class TestPromoterMetricsUnavailable:
    def test_promoter_holding_always_unavailable_from_this_source(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_promoter_holding(fy26)
        assert result.status == DataStatus.UNAVAILABLE
        assert result.value is None
        assert result.data_quality_notes

    def test_promoter_pledge_always_unavailable_from_this_source(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_promoter_pledge(fy26)
        assert result.status == DataStatus.UNAVAILABLE
        assert result.value is None
