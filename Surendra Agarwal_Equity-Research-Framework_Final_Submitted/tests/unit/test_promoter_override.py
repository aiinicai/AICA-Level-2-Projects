"""Tests for manual Promoter Holding/Pledge entry support."""

from __future__ import annotations

from pathlib import Path

from app.core.enums import DataSourceType, DataStatus, UnitOfMeasure
from app.core.models import FinancialStatement, SourceMetadata
from app.analysis.shareholder import (
    compute_all_shareholder_metrics,
    compute_promoter_holding,
    compute_promoter_pledge,
)
from app.ui.pages.company_input import apply_promoter_override

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_EXCEL = PROJECT_ROOT / "data" / "sample" / "Sona_BLW_Precis_screener_export.xlsx"


def _src():
    return SourceMetadata(
        company="Test", source="unit_test", source_type=DataSourceType.MANUAL_ENTRY,
        unit=UnitOfMeasure.INR_CRORE,
    )


class TestFinancialStatementPromoterFields:
    def test_defaults_to_none(self):
        stmt = FinancialStatement(company="Test", period="FY2026", source=_src())
        assert stmt.promoter_holding_pct is None
        assert stmt.promoter_pledge_pct is None

    def test_accepts_explicit_values(self):
        stmt = FinancialStatement(
            company="Test", period="FY2026", promoter_holding_pct=0.55,
            promoter_pledge_pct=0.05, source=_src(),
        )
        assert stmt.promoter_holding_pct == 0.55
        assert stmt.promoter_pledge_pct == 0.05

    def test_loaders_never_populate_these_fields(self, sona_blw_statements):
        assert all(s.promoter_holding_pct is None for s in sona_blw_statements)
        assert all(s.promoter_pledge_pct is None for s in sona_blw_statements)


class TestComputePromoterHolding:
    def test_unset_returns_unavailable(self):
        stmt = FinancialStatement(company="Test", period="FY2026", source=_src())
        result = compute_promoter_holding(stmt)
        assert result.status == DataStatus.UNAVAILABLE
        assert result.value is None
        assert "not manually entered" in result.data_quality_notes[0]

    def test_set_returns_ok_with_manual_entry_note(self):
        stmt = FinancialStatement(
            company="Test", period="FY2026", promoter_holding_pct=0.5992, source=_src(),
        )
        result = compute_promoter_holding(stmt)
        assert result.status == DataStatus.OK
        assert result.value == 0.5992
        assert any("manually entered" in note for note in result.data_quality_notes)

    def test_zero_percent_is_a_valid_value_not_treated_as_unset(self):
        stmt = FinancialStatement(
            company="Test", period="FY2026", promoter_holding_pct=0.0, source=_src(),
        )
        result = compute_promoter_holding(stmt)
        assert result.status == DataStatus.OK
        assert result.value == 0.0


class TestComputePromoterPledge:
    def test_unset_returns_unavailable(self):
        stmt = FinancialStatement(company="Test", period="FY2026", source=_src())
        result = compute_promoter_pledge(stmt)
        assert result.status == DataStatus.UNAVAILABLE

    def test_set_returns_ok(self):
        stmt = FinancialStatement(
            company="Test", period="FY2026", promoter_pledge_pct=0.1, source=_src(),
        )
        result = compute_promoter_pledge(stmt)
        assert result.status == DataStatus.OK
        assert result.value == 0.1


class TestComputeAllShareholderMetrics:
    def test_batch_covers_four_metrics_per_period(self, sona_blw_statements):
        results = compute_all_shareholder_metrics(sona_blw_statements)
        assert len(results) == len(sona_blw_statements) * 4

    def test_eps_and_dividend_unaffected_by_promoter_fields_being_unset(self, sona_blw_statements):
        results = compute_all_shareholder_metrics(sona_blw_statements)
        eps_results = [r for r in results if r.metric_name == "EPS"]
        assert any(r.status == DataStatus.OK for r in eps_results)


class TestApplyPromoterOverride:
    def test_only_latest_period_updated(self, sona_blw_statements):
        updated = apply_promoter_override(sona_blw_statements, 0.5992, 0.0)
        assert len(updated) == len(sona_blw_statements)
        assert all(s.promoter_holding_pct is None for s in updated[:-1])
        assert updated[-1].promoter_holding_pct == 0.5992
        assert updated[-1].promoter_pledge_pct == 0.0

    def test_original_list_not_mutated(self, sona_blw_statements):
        original_latest = sona_blw_statements[-1]
        apply_promoter_override(sona_blw_statements, 0.5992, 0.0)
        assert original_latest.promoter_holding_pct is None

    def test_partial_update_holding_only(self, sona_blw_statements):
        updated = apply_promoter_override(sona_blw_statements, 0.60, None)
        assert updated[-1].promoter_holding_pct == 0.60
        assert updated[-1].promoter_pledge_pct is None

    def test_partial_update_pledge_only(self, sona_blw_statements):
        updated = apply_promoter_override(sona_blw_statements, None, 0.15)
        assert updated[-1].promoter_holding_pct is None
        assert updated[-1].promoter_pledge_pct == 0.15

    def test_both_none_leaves_statement_unchanged(self, sona_blw_statements):
        updated = apply_promoter_override(sona_blw_statements, None, None)
        assert updated[-1].promoter_holding_pct is None
        assert updated[-1].promoter_pledge_pct is None

    def test_empty_statements_list_returns_empty(self):
        assert apply_promoter_override([], 0.5, 0.1) == []

    def test_result_feeds_correctly_into_compute_promoter_holding(self, sona_blw_statements):
        updated = apply_promoter_override(sona_blw_statements, 0.5992, 0.0)
        result = compute_promoter_holding(updated[-1])
        assert result.status == DataStatus.OK
        assert result.value == 0.5992


class TestApplyPromoterDataButtonRealAppInteraction:
    """Regression test for a real bug a user hit: clicking 'Apply
    Promoter Data' via the manual-entry checkbox flow (WITHOUT ever
    uploading/processing a shareholding-pattern CSV in the same run)
    raised UnboundLocalError on compute_all_shareholder_metrics.

    Root cause: company_input.py's render() had a redundant LOCAL
    import of compute_all_shareholder_metrics inside the
    shareholding-CSV-upload branch, even though it was already imported
    at module level. In Python, a name assigned ANYWHERE inside a
    function (including via a local import inside a conditional branch
    that may never execute) is treated as local for the ENTIRE
    function — shadowing the module-level import even in code paths
    that never touch that branch. Removing the redundant local import
    fixed it. This test drives the real UI flow that crashed, not just
    the pure apply_promoter_override function in isolation above.
    """

    def test_apply_promoter_data_without_shareholding_csv_does_not_crash(self):
        import sys
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        from app.core.enums import DataSourceType, ExchangeCode, UnitOfMeasure
        from app.core.models import Company, FinancialStatement, SourceMetadata

        project_root = Path(__file__).resolve().parent.parent.parent
        at = AppTest.from_file(str(project_root / "app" / "main.py"), default_timeout=30)
        at.session_state["company"] = Company(
            name="Sona BLW Precision Forgings Ltd", ticker="SONACOMS", exchange=ExchangeCode.NSE,
        )
        at.session_state["statements"] = [
            FinancialStatement(
                company="Sona BLW", period="FY2026", sales=4123.67, net_profit=646.42,
                num_equity_shares=621846890.0,
                source=SourceMetadata(
                    company="Sona BLW", source="test", source_type=DataSourceType.MANUAL_ENTRY,
                    unit=UnitOfMeasure.INR_CRORE,
                ),
            )
        ]
        at.run()
        assert list(at.exception) == []

        # The exact real scenario: check the "no pledge" box and click
        # Apply, WITHOUT ever interacting with the shareholding CSV uploader.
        checkbox = next(c for c in at.checkbox if "no promoter pledge" in c.label)
        checkbox.check().run()
        assert list(at.exception) == []

        apply_btn = next(b for b in at.button if b.label == "Apply Promoter Data")
        apply_btn.click().run()
        assert list(at.exception) == [], (
            f"Apply Promoter Data crashed: {[str(e) for e in at.exception]}"
        )

        # Confirm the data was actually applied, not just "didn't crash."
        assert at.session_state["statements"][-1].promoter_holding_pct is not None
        assert at.session_state["statements"][-1].promoter_pledge_pct == 0.0
