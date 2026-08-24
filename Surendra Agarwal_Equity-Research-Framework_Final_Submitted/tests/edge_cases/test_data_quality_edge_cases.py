"""Edge-case tests per the spec's required test matrix:
missing data, malformed data, duplicate records, zero/negative
denominators, extreme values.
"""

from __future__ import annotations

from datetime import date

from app.core.enums import Currency, DataSourceType, UnitOfMeasure, ValidationSeverity
from app.core.models import FinancialStatement, SourceMetadata
from app.data.financial_data import build_canonical_statements
from app.data.validators import run_all_validations


def _src(unit=UnitOfMeasure.INR_CRORE):
    return SourceMetadata(
        company="Edge Co", source="edge_case_test", source_type=DataSourceType.MANUAL_ENTRY, unit=unit,
    )


class TestMissingData:
    def test_all_none_statement_produces_no_crash(self):
        stmt = FinancialStatement(company="Edge Co", period="FY2024", source=_src())
        issues = run_all_validations([stmt])
        assert any(i.rule == "missing_core_values" for i in issues)

    def test_partial_data_still_processes_available_fields(self):
        stmt = FinancialStatement(
            company="Edge Co", period="FY2024", sales=100.0, source=_src()
        )
        issues = run_all_validations([stmt])
        # sales present, net_profit/total_assets missing -> WARNING, not a crash
        assert any(i.rule == "missing_core_values" for i in issues)
        assert not any(i.severity == ValidationSeverity.BLOCKING for i in issues)


class TestMalformedData:
    def test_build_canonical_statements_handles_empty_input(self):
        assert build_canonical_statements([]) == []

    def test_negative_total_assets_is_flagged_not_silently_accepted(self):
        stmt = FinancialStatement(company="Edge Co", period="FY2024", total_assets=-500.0, source=_src())
        issues = run_all_validations([stmt])
        assert any(i.field == "total_assets" for i in issues)


class TestDuplicateRecords:
    def test_triplicate_period_counted_correctly(self):
        stmts = [
            FinancialStatement(company="Edge Co", period="FY2024", source=_src()) for _ in range(3)
        ]
        issues = run_all_validations(stmts)
        dup = [i for i in issues if i.rule == "duplicate_period"]
        assert len(dup) == 1
        assert dup[0].context["count"] == 3


class TestZeroAndNegativeDenominators:
    def test_zero_profit_before_tax_does_not_raise(self):
        stmt = FinancialStatement(
            company="Edge Co", period="FY2024", profit_before_tax=0.0, tax=0.0, source=_src()
        )
        # Must not raise ZeroDivisionError anywhere in the validation chain.
        issues = run_all_validations([stmt])
        assert isinstance(issues, list)

    def test_negative_profit_before_tax_with_positive_tax_not_evaluated_for_rate(self):
        # Effective-tax-rate check only fires when PBT > 0 by design;
        # confirm a loss-making period doesn't produce a nonsensical rate flag.
        stmt = FinancialStatement(
            company="Edge Co", period="FY2024", profit_before_tax=-100.0, tax=5.0, source=_src()
        )
        issues = run_all_validations([stmt])
        assert not any(i.rule == "unusual_effective_tax_rate" for i in issues)

    def test_zero_prior_period_shares_does_not_raise_in_discontinuity_check(self):
        from app.data.validators import check_share_count_discontinuity

        s1 = FinancialStatement(
            company="Edge Co", period="FY2023", period_end_date=date(2023, 3, 31),
            num_equity_shares=0.0, source=_src(),
        )
        s2 = FinancialStatement(
            company="Edge Co", period="FY2024", period_end_date=date(2024, 3, 31),
            num_equity_shares=1000.0, source=_src(),
        )
        issues = check_share_count_discontinuity([s1, s2])  # must not raise ZeroDivisionError
        assert isinstance(issues, list)


class TestExtremeValues:
    def test_extremely_large_sales_value_processed_without_overflow(self):
        stmt = FinancialStatement(company="Edge Co", period="FY2024", sales=1e12, source=_src())
        issues = run_all_validations([stmt])
        assert isinstance(issues, list)  # no overflow/crash

    def test_extreme_negative_effective_tax_rate_flagged(self):
        # A large tax credit relative to a small PBT -> effective rate << 0
        stmt = FinancialStatement(
            company="Edge Co", period="FY2024", profit_before_tax=10.0, tax=-50.0, source=_src()
        )
        issues = run_all_validations([stmt])
        assert any(i.rule == "unusual_effective_tax_rate" for i in issues)


class TestUnitConversionCorrectness:
    def test_lakh_converts_correctly_to_crore(self):
        raw_lakh_value = 100.0  # 100 lakh
        # 100 lakh = 1 crore; verify via the same conversion table financial_data.py uses
        from app.data.financial_data import _TO_CRORE

        assert raw_lakh_value * _TO_CRORE[UnitOfMeasure.INR_LAKH] == 1.0

    def test_million_converts_correctly_to_crore(self):
        from app.data.financial_data import _TO_CRORE

        raw_million_value = 10.0  # 10 million
        # 10 million INR = 1 crore INR
        assert round(raw_million_value * _TO_CRORE[UnitOfMeasure.INR_MILLION], 6) == 1.0
