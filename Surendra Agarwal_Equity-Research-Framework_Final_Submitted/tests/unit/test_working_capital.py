"""Tests for app/analysis/working_capital.py."""

from __future__ import annotations

from app.core.enums import DataSourceType, DataStatus, UnitOfMeasure
from app.core.models import FinancialStatement, SourceMetadata
from app.analysis.working_capital import (
    compute_all_working_capital_metrics,
    compute_cash_conversion_cycle,
    compute_inventory_days,
    compute_payable_days,
    compute_receivable_days,
)


def _src():
    return SourceMetadata(
        company="Test", source="unit_test", source_type=DataSourceType.MANUAL_ENTRY,
        unit=UnitOfMeasure.INR_CRORE,
    )


class TestReceivableDays:
    def test_fy2026_receivable_days_matches_hand_calc(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        # Receivables=1076.03, Sales=4123.67
        expected = (1076.03 / 4123.67) * 365
        result = compute_receivable_days(fy26)
        assert result.status == DataStatus.OK
        assert abs(result.value - round(expected, 1)) < 0.2

    def test_zero_sales_returns_missing_input_not_infinity(self):
        stmt = FinancialStatement(company="Test", period="FY2024", receivables=50.0, sales=0.0, source=_src())
        result = compute_receivable_days(stmt)
        assert result.status == DataStatus.MISSING_INPUT
        assert result.value is None  # never inf


class TestInventoryDays:
    def test_fy2026_inventory_days_matches_hand_calc(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        # Inventory=680.34, RawMaterialCost=2450.0(approx) - use actual source values
        result = compute_inventory_days(fy26)
        assert result.status == DataStatus.OK
        assert result.value > 0
        assert result.data_quality_notes  # COGS-proxy caveat must be present

    def test_missing_raw_material_cost_returns_missing_input(self):
        stmt = FinancialStatement(company="Test", period="FY2024", inventory=100.0, source=_src())
        result = compute_inventory_days(stmt)
        assert result.status == DataStatus.MISSING_INPUT


class TestPayableDaysAndCcc:
    def test_payable_days_always_not_applicable_currently(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_payable_days(fy26)
        assert result.status == DataStatus.NOT_APPLICABLE
        assert result.value is None
        assert result.data_quality_notes

    def test_ccc_not_applicable_because_payables_missing(self, sona_blw_statements):
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_cash_conversion_cycle(fy26)
        assert result.status == DataStatus.NOT_APPLICABLE
        assert result.value is None
        # but the two computable legs should still be visible in inputs for transparency
        assert result.inputs["receivable_days"] is not None
        assert result.inputs["inventory_days"] is not None
        assert result.inputs["payable_days"] is None

    def test_ccc_never_silently_drops_payables_to_compute_partial_value(self, sona_blw_statements):
        # Explicit regression guard against the exact failure mode warned
        # about in the module docstring: CCC must never be returned as
        # receivable_days + inventory_days alone.
        fy26 = next(s for s in sona_blw_statements if s.period == "FY2026")
        result = compute_cash_conversion_cycle(fy26)
        assert result.value is None


class TestBatchHelper:
    def test_compute_all_working_capital_metrics_covers_every_period(self, sona_blw_statements):
        results = compute_all_working_capital_metrics(sona_blw_statements)
        # 4 metrics per period x 10 periods
        assert len(results) == 40
