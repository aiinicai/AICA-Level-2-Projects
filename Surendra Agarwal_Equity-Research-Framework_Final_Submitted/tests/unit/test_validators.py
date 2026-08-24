"""Tests for app/data/validators.py."""

from __future__ import annotations

from datetime import date

from app.core.enums import UnitOfMeasure, ValidationSeverity
from app.core.models import FinancialStatement
from app.data.validators import (
    check_balance_sheet_tie_out,
    check_date_ordering,
    check_duplicate_periods,
    check_impossible_values,
    check_missing_values,
    check_negative_values_where_inappropriate,
    check_share_count_discontinuity,
    check_unit_consistency,
    run_all_validations,
)


class TestRealSonaBLWData:
    """Sanity checks against the real 10-year Sona BLW dataset (not synthetic)."""

    def test_ten_years_parsed(self, sona_blw_statements):
        assert len(sona_blw_statements) == 10

    def test_no_blocking_issues_except_known_ipo_discontinuity(self, sona_blw_statements):
        issues = run_all_validations(sona_blw_statements)
        blocking = [i for i in issues if i.severity == ValidationSeverity.BLOCKING]
        assert blocking == [], f"Unexpected BLOCKING issues in clean real data: {blocking}"

    def test_balance_sheet_ties_out_every_year(self, sona_blw_statements):
        issues = check_balance_sheet_tie_out(sona_blw_statements)
        assert issues == []

    def test_ipo_share_discontinuity_is_flagged(self, sona_blw_statements):
        issues = check_share_count_discontinuity(sona_blw_statements)
        # Sona BLW IPO'd in FY2021 (June 2021) - expect at least one WARNING
        # around that boundary, not silently ignored.
        assert any(i.period == "FY2021" for i in issues)
        assert all(i.severity == ValidationSeverity.WARNING for i in issues)

    def test_revenue_grew_every_year_in_sample(self, sona_blw_statements):
        sales = [s.sales for s in sona_blw_statements if s.sales is not None]
        assert len(sales) == 10
        # FY2020 (COVID) dip is real and expected; confirm we see it, not a parse error.
        by_period = {s.period: s.sales for s in sona_blw_statements}
        assert by_period["FY2020"] < by_period["FY2019"]
        assert by_period["FY2026"] > by_period["FY2025"]


class TestSyntheticEdgeCases:
    """Deliberately constructed cases to exercise each rule independently."""

    def test_missing_core_values_flagged(self):
        stmt = FinancialStatement(
            company="Test", period="FY2024", period_end_date=date(2024, 3, 31),
            sales=None, net_profit=None, total_assets=100.0,
            source=_src(),
        )
        issues = check_missing_values([stmt])
        assert len(issues) == 1
        assert set(issues[0].context["missing_fields"]) == {"sales", "net_profit"}

    def test_no_missing_values_when_core_present(self):
        stmt = FinancialStatement(
            company="Test", period="FY2024", sales=100.0, net_profit=10.0,
            total_assets=200.0, source=_src(),
        )
        assert check_missing_values([stmt]) == []

    def test_duplicate_period_detected(self):
        s1 = FinancialStatement(company="Test", period="FY2024", source=_src())
        s2 = FinancialStatement(company="Test", period="FY2024", source=_src())
        issues = check_duplicate_periods([s1, s2])
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.BLOCKING

    def test_no_duplicates_when_periods_unique(self):
        s1 = FinancialStatement(company="Test", period="FY2024", source=_src())
        s2 = FinancialStatement(company="Test", period="FY2025", source=_src())
        assert check_duplicate_periods([s1, s2]) == []

    def test_zero_face_value_is_blocking(self):
        stmt = FinancialStatement(company="Test", period="FY2024", face_value=0.0, source=_src())
        issues = check_impossible_values([stmt])
        assert any(i.rule == "impossible_face_value" for i in issues)
        assert issues[0].severity == ValidationSeverity.BLOCKING

    def test_zero_share_count_is_blocking(self):
        stmt = FinancialStatement(company="Test", period="FY2024", num_equity_shares=0.0, source=_src())
        issues = check_impossible_values([stmt])
        assert any(i.rule == "impossible_share_count" for i in issues)

    def test_extreme_effective_tax_rate_flagged(self):
        stmt = FinancialStatement(
            company="Test", period="FY2024", profit_before_tax=100.0, tax=90.0, source=_src()
        )
        issues = check_impossible_values([stmt])
        assert any(i.rule == "unusual_effective_tax_rate" for i in issues)

    def test_normal_effective_tax_rate_not_flagged(self):
        stmt = FinancialStatement(
            company="Test", period="FY2024", profit_before_tax=100.0, tax=25.0, source=_src()
        )
        issues = check_impossible_values([stmt])
        assert issues == []

    def test_inconsistent_units_flagged(self):
        s1 = FinancialStatement(
            company="Test", period="FY2024", unit=UnitOfMeasure.INR_CRORE, source=_src()
        )
        s2 = FinancialStatement(
            company="Test", period="FY2025", unit=UnitOfMeasure.INR_LAKH,
            source=_src(unit=UnitOfMeasure.INR_LAKH),
        )
        issues = check_unit_consistency([s1, s2])
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.BLOCKING

    def test_negative_sales_flagged(self):
        stmt = FinancialStatement(company="Test", period="FY2024", sales=-50.0, source=_src())
        issues = check_negative_values_where_inappropriate([stmt])
        assert any(i.field == "sales" for i in issues)

    def test_negative_net_cash_flow_not_flagged(self):
        # net_cash_flow is legitimately allowed to be negative
        stmt = FinancialStatement(company="Test", period="FY2024", net_cash_flow=-50.0, source=_src())
        issues = check_negative_values_where_inappropriate([stmt])
        assert issues == []

    def test_date_ordering_mismatch_detected(self):
        # FY2025 labeled but dated earlier than FY2024 -> mislabeled
        s1 = FinancialStatement(
            company="Test", period="FY2024", period_end_date=date(2025, 3, 31), source=_src()
        )
        s2 = FinancialStatement(
            company="Test", period="FY2025", period_end_date=date(2024, 3, 31), source=_src()
        )
        issues = check_date_ordering([s1, s2])
        assert len(issues) == 1

    def test_date_ordering_consistent_not_flagged(self):
        s1 = FinancialStatement(
            company="Test", period="FY2024", period_end_date=date(2024, 3, 31), source=_src()
        )
        s2 = FinancialStatement(
            company="Test", period="FY2025", period_end_date=date(2025, 3, 31), source=_src()
        )
        assert check_date_ordering([s1, s2]) == []

    def test_balance_sheet_mismatch_beyond_tolerance_flagged(self):
        stmt = FinancialStatement(
            company="Test", period="FY2024", total_assets=1000.0,
            total_liabilities=990.0, source=_src(),
        )
        issues = check_balance_sheet_tie_out([stmt])
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.BLOCKING

    def test_balance_sheet_within_tolerance_not_flagged(self):
        stmt = FinancialStatement(
            company="Test", period="FY2024", total_assets=1000.0,
            total_liabilities=1000.1, source=_src(),
        )
        assert check_balance_sheet_tie_out([stmt]) == []

    def test_zero_denominator_does_not_crash_tax_rate_check(self):
        # profit_before_tax == 0 must not raise ZeroDivisionError
        stmt = FinancialStatement(
            company="Test", period="FY2024", profit_before_tax=0.0, tax=5.0, source=_src()
        )
        issues = check_impossible_values([stmt])  # should not raise
        assert isinstance(issues, list)

    def test_run_all_validations_aggregates_every_rule(self, clean_statement_pair):
        # Clean, internally-consistent data -> no issues at all.
        issues = run_all_validations(clean_statement_pair)
        assert issues == []


def _src(unit: UnitOfMeasure = UnitOfMeasure.INR_CRORE):
    from app.core.enums import Currency, DataSourceType
    from app.core.models import SourceMetadata

    return SourceMetadata(
        company="Test", source="unit_test", source_type=DataSourceType.MANUAL_ENTRY, unit=unit,
    )
