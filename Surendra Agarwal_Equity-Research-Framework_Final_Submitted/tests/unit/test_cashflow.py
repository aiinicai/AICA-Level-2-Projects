"""Tests for app/analysis/cashflow.py."""

from __future__ import annotations

from app.core.enums import DataSourceType, DataStatus, UnitOfMeasure
from app.core.models import FinancialStatement, SourceMetadata
from app.analysis.cashflow import (
    compute_all_cashflow_metrics,
    compute_capex_estimated,
    compute_cfo,
    compute_cfo_to_pat,
    compute_fcf,
    compute_fcf_conversion,
)


def _src():
    return SourceMetadata(
        company="Test", source="unit_test", source_type=DataSourceType.MANUAL_ENTRY,
        unit=UnitOfMeasure.INR_CRORE,
    )


class TestCfo:
    def test_fy2026_cfo_matches_source(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_cfo(fy26)
        assert result.status == DataStatus.OK
        assert result.value == 614.59

    def test_fy2026_cfo_to_pat(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_cfo_to_pat(fy26)
        assert result.value == round(614.59 / 646.42, 4)

    def test_missing_cfo_returns_missing_input(self):
        stmt = FinancialStatement(company="Test", period="FY2024", source=_src())
        result = compute_cfo(stmt)
        assert result.status == DataStatus.MISSING_INPUT
        assert result.value is None


class TestCapexAndFcf:
    def test_capex_requires_prior_period(self, sona_blw_statements):
        fy17 = next(s for s in sona_blw_statements if s.period == "FY2017")  # earliest, no prior
        result = compute_capex_estimated(fy17, None)
        assert result.status == DataStatus.INSUFFICIENT_HISTORY
        assert result.value is None

    def test_fy2026_capex_matches_hand_calc(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        fy25 = next(s for s in sona_blw_statements if s.period == "FY2025")
        # (NetBlock_end - NetBlock_start) + (CWIP_end - CWIP_start) + Depreciation_end
        expected = (3264.44 - 1757.63) + (92.32 - 170.07) + 259.94
        result = compute_capex_estimated(fy26, fy25)
        assert result.status == DataStatus.OK
        assert result.value == round(expected, 2)

    def test_fy2026_fcf_is_negative_due_to_expansion_capex(self, sona_blw_statements):
        # Known real result: Sona BLW had heavy FY26 capex (Gen3 e-axle
        # facility expansion) -> FCF should come out negative, and this
        # must not be silently "corrected" to a positive number.
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        fy25 = next(s for s in sona_blw_statements if s.period == "FY2025")
        result = compute_fcf(fy26, fy25)
        assert result.status == DataStatus.OK
        assert result.value < 0

    def test_fcf_conversion_negative_when_fcf_negative(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        fy25 = next(s for s in sona_blw_statements if s.period == "FY2025")
        result = compute_fcf_conversion(fy26, fy25)
        assert result.status == DataStatus.OK
        assert result.value < 0

    def test_capex_missing_cwip_returns_missing_input_not_partial_calc(self):
        prior = FinancialStatement(
            company="Test", period="FY2023", net_block=100.0, capital_work_in_progress=None,
            source=_src(),
        )
        curr = FinancialStatement(
            company="Test", period="FY2024", net_block=120.0, capital_work_in_progress=10.0,
            depreciation=5.0, source=_src(),
        )
        result = compute_capex_estimated(curr, prior)
        assert result.status == DataStatus.MISSING_INPUT
        assert result.value is None


class TestBatchHelper:
    def test_compute_all_cashflow_metrics_covers_every_period(self, sona_blw_statements):
        results = compute_all_cashflow_metrics(sona_blw_statements)
        # 5 metrics per period x 10 periods
        assert len(results) == 50

    def test_earliest_period_capex_and_fcf_are_insufficient_history(self, sona_blw_statements):
        results = compute_all_cashflow_metrics(sona_blw_statements)
        fy17_capex = [
            r for r in results
            if r.metric_name == "Capex (estimated)" and r.period == "FY2017"
        ]
        assert len(fy17_capex) == 1
        assert fy17_capex[0].status == DataStatus.INSUFFICIENT_HISTORY
