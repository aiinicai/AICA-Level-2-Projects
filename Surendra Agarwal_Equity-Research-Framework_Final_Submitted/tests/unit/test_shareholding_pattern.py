"""Tests for app/data/loaders.py's NSE shareholding-pattern loader and
app/analysis/risk.py's declining-promoter-holding governance rule.

Uses the real Sona BLW shareholding-pattern CSV (a genuine NSE
corporate-filing export) - the promoter holding decline from 67.18% to
28.02% over FY2022-FY2026 is real, disclosed data, not synthetic.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.core.enums import ConfidenceLevel, RiskCategory, RiskSeverity, TrendDirection
from app.core.exceptions import DataIntegrityError
from app.core.models import TrendResult
from app.data.loaders import (
    apply_shareholding_history_to_statements,
    load_nse_shareholding_pattern_csv,
    load_screener_excel,
)
from app.data.financial_data import build_canonical_statements
from app.analysis.risk import _rule_declining_promoter_holding, detect_financial_risks
from app.analysis.trends import compute_multi_period_trend

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_EXCEL = PROJECT_ROOT / "data" / "sample" / "Sona_BLW_Precis_screener_export.xlsx"
SAMPLE_SHAREHOLDING_CSV = PROJECT_ROOT / "data" / "sample" / "SONACOMS_shareholding_pattern.csv"


@pytest.fixture(scope="module")
def real_shareholding_records():
    return load_nse_shareholding_pattern_csv(SAMPLE_SHAREHOLDING_CSV)


@pytest.fixture(scope="module")
def real_statements_with_shareholding(real_shareholding_records):
    raw = load_screener_excel(SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd")
    statements = build_canonical_statements(raw)
    updated, match_count = apply_shareholding_history_to_statements(statements, real_shareholding_records)
    return updated, match_count


class TestLoadNseShareholdingPatternCsv:
    def test_parses_all_real_filings(self, real_shareholding_records):
        assert len(real_shareholding_records) == 21

    def test_sorted_ascending_by_date(self, real_shareholding_records):
        dates = [r["as_on_date"] for r in real_shareholding_records]
        assert dates == sorted(dates)

    def test_percentages_converted_to_0_1_scale(self, real_shareholding_records):
        for r in real_shareholding_records:
            assert 0.0 <= r["promoter_pct"] <= 1.0
            assert 0.0 <= r["public_pct"] <= 1.0

    def test_known_latest_value_matches_source(self, real_shareholding_records):
        latest = real_shareholding_records[-1]
        assert latest["as_on_date"] == date(2026, 6, 30)
        assert latest["promoter_pct"] == pytest.approx(0.2801, abs=1e-4)

    def test_known_earliest_value_matches_source(self, real_shareholding_records):
        earliest = real_shareholding_records[0]
        assert earliest["as_on_date"] == date(2021, 9, 30)
        assert earliest["promoter_pct"] == pytest.approx(0.673, abs=1e-4)

    def test_fiscal_year_end_dates_present_in_source(self, real_shareholding_records):
        fy_end_dates = {date(2022, 3, 31), date(2023, 3, 31), date(2024, 3, 31),
                         date(2025, 3, 31), date(2026, 3, 31)}
        found_dates = {r["as_on_date"] for r in real_shareholding_records}
        assert fy_end_dates <= found_dates

    def test_missing_file_raises(self):
        with pytest.raises(DataIntegrityError):
            load_nse_shareholding_pattern_csv(Path("/nonexistent/fake.csv"))

    def test_missing_required_column_raises(self, tmp_path):
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("COMPANY,SOMETHING\nTest,1\n")
        with pytest.raises(DataIntegrityError, match="missing expected column"):
            load_nse_shareholding_pattern_csv(bad_csv)

    def test_unparseable_date_row_skipped_not_crashed(self, tmp_path):
        content = (
            'COMPANY,"PROMOTER & PROMOTER GROUP (A)","PUBLIC (B)","AS ON DATE"\n'
            'Test,50.0,50.0,not-a-date\n'
            'Test,60.0,40.0,31-MAR-2026\n'
        )
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(content)
        records = load_nse_shareholding_pattern_csv(csv_path)
        assert len(records) == 1
        assert records[0]["promoter_pct"] == 0.60


class TestApplyShareholdingHistoryToStatements:
    def test_exact_matches_applied(self, real_statements_with_shareholding):
        updated, match_count = real_statements_with_shareholding
        assert match_count == 5

    def test_non_matching_periods_stay_none(self, real_statements_with_shareholding):
        updated, _ = real_statements_with_shareholding
        early_periods = [s for s in updated if s.period in ("FY2017", "FY2018", "FY2019", "FY2020", "FY2021")]
        assert len(early_periods) == 5
        assert all(s.promoter_holding_pct is None for s in early_periods)

    def test_known_fy2022_value_matches_source(self, real_statements_with_shareholding):
        updated, _ = real_statements_with_shareholding
        fy2022 = next(s for s in updated if s.period == "FY2022")
        assert fy2022.promoter_holding_pct == pytest.approx(0.6718, abs=1e-4)

    def test_known_fy2026_value_matches_source(self, real_statements_with_shareholding):
        updated, _ = real_statements_with_shareholding
        fy2026 = next(s for s in updated if s.period == "FY2026")
        assert fy2026.promoter_holding_pct == pytest.approx(0.2802, abs=1e-4)

    def test_pledge_never_set_by_this_loader(self, real_statements_with_shareholding):
        updated, _ = real_statements_with_shareholding
        assert all(s.promoter_pledge_pct is None for s in updated)

    def test_original_statements_not_mutated(self):
        raw = load_screener_excel(SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd")
        original = build_canonical_statements(raw)
        original_fy2022 = next(s for s in original if s.period == "FY2022")
        records = load_nse_shareholding_pattern_csv(SAMPLE_SHAREHOLDING_CSV)
        apply_shareholding_history_to_statements(original, records)
        assert original_fy2022.promoter_holding_pct is None

    def test_empty_records_matches_nothing(self):
        raw = load_screener_excel(SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd")
        statements = build_canonical_statements(raw)
        updated, match_count = apply_shareholding_history_to_statements(statements, [])
        assert match_count == 0
        assert all(s.promoter_holding_pct is None for s in updated)


class TestDecliningPromoterHoldingRiskRule:
    def test_real_decline_flagged_as_governance_risk(self, real_statements_with_shareholding):
        updated, _ = real_statements_with_shareholding
        periods = [s.period for s in updated]
        values = [s.promoter_holding_pct for s in updated]
        trend = compute_multi_period_trend("Promoter Holding", periods, values, higher_is_better=True)

        risks = detect_financial_risks([], [trend])
        promoter_risks = [r for r in risks if r.category == RiskCategory.GOVERNANCE]
        assert len(promoter_risks) == 1
        assert promoter_risks[0].severity == RiskSeverity.HIGH
        assert "declined" in promoter_risks[0].description

    def test_not_flagged_as_financial_category(self, real_statements_with_shareholding):
        updated, _ = real_statements_with_shareholding
        periods = [s.period for s in updated]
        values = [s.promoter_holding_pct for s in updated]
        trend = compute_multi_period_trend("Promoter Holding", periods, values, higher_is_better=True)
        risks = detect_financial_risks([], [trend])
        assert not any(r.category == RiskCategory.FINANCIAL for r in risks)

    def test_improving_promoter_holding_not_flagged(self):
        trend = TrendResult(
            metric_name="Promoter Holding", periods=["FY24", "FY25", "FY26"],
            values=[0.40, 0.45, 0.50], direction=TrendDirection.IMPROVING,
        )
        result = _rule_declining_promoter_holding(trend)
        assert result is None

    def test_unrelated_metric_name_not_matched(self):
        trend = TrendResult(
            metric_name="Sales", periods=["FY24", "FY25", "FY26"],
            values=[100.0, 90.0, 80.0], direction=TrendDirection.DETERIORATING,
            significance=ConfidenceLevel.HIGH,
        )
        result = _rule_declining_promoter_holding(trend)
        assert result is None
        risks = detect_financial_risks([], [trend])
        assert any(r.category == RiskCategory.FINANCIAL for r in risks)

    def test_evidence_id_links_to_trend(self, real_statements_with_shareholding):
        updated, _ = real_statements_with_shareholding
        periods = [s.period for s in updated]
        values = [s.promoter_holding_pct for s in updated]
        trend = compute_multi_period_trend("Promoter Holding", periods, values, higher_is_better=True)
        result = _rule_declining_promoter_holding(trend)
        assert result.evidence_ids == [trend.trend_id]
