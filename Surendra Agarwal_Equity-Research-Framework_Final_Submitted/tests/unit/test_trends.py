"""Tests for app/analysis/trends.py."""

from __future__ import annotations

import pytest

from app.core.enums import ConfidenceLevel, TrendDirection
from app.core.models import MetricResult
from app.analysis.trends import (
    compute_multi_period_trend,
    compute_multi_period_trend_from_metric_results,
    compute_period_over_period,
)


class TestPeriodOverPeriod:
    def test_improving_when_higher_is_better_and_value_rises(self):
        result = compute_period_over_period("Revenue", "FY2025", 100.0, "FY2026", 120.0, higher_is_better=True)
        assert result.direction == TrendDirection.IMPROVING
        assert result.absolute_change == 20.0
        assert result.percentage_change == 0.2

    def test_deteriorating_when_higher_is_better_and_value_falls(self):
        result = compute_period_over_period("Revenue", "FY2025", 100.0, "FY2026", 80.0, higher_is_better=True)
        assert result.direction == TrendDirection.DETERIORATING

    def test_deteriorating_when_lower_is_better_and_value_rises(self):
        # e.g. Debt/Equity rising is bad
        result = compute_period_over_period("Debt/Equity", "FY2025", 0.2, "FY2026", 0.5, higher_is_better=False)
        assert result.direction == TrendDirection.DETERIORATING

    def test_improving_when_lower_is_better_and_value_falls(self):
        result = compute_period_over_period("Debt/Equity", "FY2025", 0.5, "FY2026", 0.2, higher_is_better=False)
        assert result.direction == TrendDirection.IMPROVING

    def test_small_change_within_flat_threshold_is_stable(self):
        result = compute_period_over_period("Revenue", "FY2025", 100.0, "FY2026", 101.0, higher_is_better=True)
        assert result.direction == TrendDirection.STABLE

    def test_missing_value_is_insufficient_data_not_crash(self):
        result = compute_period_over_period("Revenue", "FY2025", None, "FY2026", 100.0)
        assert result.direction == TrendDirection.INSUFFICIENT_DATA
        assert result.absolute_change is None

    def test_zero_prior_value_returns_insufficient_data_not_infinity(self):
        result = compute_period_over_period("Revenue", "FY2025", 0.0, "FY2026", 100.0)
        assert result.direction == TrendDirection.INSUFFICIENT_DATA
        assert result.percentage_change is None

    def test_explanation_only_populated_with_evidence(self):
        # Without evidence_ids, explanation must be dropped even if text is passed —
        # this is the "never infer causation without evidence" guard.
        result = compute_period_over_period(
            "Revenue", "FY2025", 100.0, "FY2026", 120.0,
            explanation="New product launch drove growth", evidence_ids=None,
        )
        assert result.potential_explanation is None
        assert result.evidence_ids == []

    def test_explanation_populated_when_evidence_supplied(self):
        result = compute_period_over_period(
            "Revenue", "FY2025", 100.0, "FY2026", 120.0,
            explanation="New product launch drove growth", evidence_ids=["ev_123"],
        )
        assert result.potential_explanation == "New product launch drove growth"
        assert result.evidence_ids == ["ev_123"]

    def test_significance_high_for_large_swing(self):
        result = compute_period_over_period("Revenue", "FY2025", 100.0, "FY2026", 150.0)
        assert result.significance == ConfidenceLevel.HIGH

    def test_significance_low_for_small_swing(self):
        result = compute_period_over_period("Revenue", "FY2025", 100.0, "FY2026", 104.0)
        assert result.significance == ConfidenceLevel.LOW


class TestMultiPeriodTrendSynthetic:
    def test_all_up_legs_is_improving(self):
        result = compute_multi_period_trend(
            "Revenue", ["FY23", "FY24", "FY25", "FY26"], [100.0, 110.0, 125.0, 140.0],
            higher_is_better=True,
        )
        assert result.direction == TrendDirection.IMPROVING

    def test_all_down_legs_is_deteriorating(self):
        result = compute_multi_period_trend(
            "Revenue", ["FY23", "FY24", "FY25", "FY26"], [140.0, 125.0, 110.0, 100.0],
            higher_is_better=True,
        )
        assert result.direction == TrendDirection.DETERIORATING

    def test_flat_series_is_stable(self):
        result = compute_multi_period_trend(
            "Revenue", ["FY23", "FY24", "FY25", "FY26"], [100.0, 101.0, 99.5, 100.5],
            higher_is_better=True,
        )
        assert result.direction == TrendDirection.STABLE

    def test_one_reversal_amid_growth_is_mixed_not_smoothed(self):
        # This is the exact behavior the module docstring calls out:
        # one significant down leg amid otherwise-up legs -> MIXED,
        # not silently classified as "IMPROVING despite one bad year."
        result = compute_multi_period_trend(
            "Revenue", ["FY22", "FY23", "FY24", "FY25", "FY26"],
            [100.0, 120.0, 90.0, 130.0, 150.0], higher_is_better=True,
        )
        assert result.direction == TrendDirection.MIXED

    def test_lower_is_better_all_down_is_improving(self):
        result = compute_multi_period_trend(
            "Debt/Equity", ["FY23", "FY24", "FY25", "FY26"], [0.8, 0.6, 0.4, 0.2],
            higher_is_better=False,
        )
        assert result.direction == TrendDirection.IMPROVING

    def test_single_data_point_is_insufficient_data(self):
        result = compute_multi_period_trend("Revenue", ["FY26"], [100.0])
        assert result.direction == TrendDirection.INSUFFICIENT_DATA

    def test_all_none_is_insufficient_data(self):
        result = compute_multi_period_trend("Revenue", ["FY24", "FY25", "FY26"], [None, None, None])
        assert result.direction == TrendDirection.INSUFFICIENT_DATA

    def test_gap_in_series_bridges_across_none(self):
        # FY24 missing entirely -> should still classify FY23->FY25->FY26 as one trajectory.
        result = compute_multi_period_trend(
            "Revenue", ["FY23", "FY24", "FY25", "FY26"], [100.0, None, 120.0, 140.0],
            higher_is_better=True,
        )
        assert result.direction == TrendDirection.IMPROVING

    def test_mismatched_lengths_raises_value_error(self):
        with pytest.raises(ValueError):
            compute_multi_period_trend("Revenue", ["FY25", "FY26"], [100.0, 110.0, 120.0])

    def test_overall_pct_change_uses_first_and_last_valid_not_adjacent(self):
        result = compute_multi_period_trend(
            "Revenue", ["FY23", "FY24", "FY25", "FY26"], [100.0, 999.0, 999.0, 200.0],
            higher_is_better=True,
        )
        assert result.percentage_change == 1.0  # (200-100)/100, from FIRST to LAST value


class TestMultiPeriodTrendRealSonaBLW:
    def test_real_revenue_trend_is_mixed_due_to_covid_dip(self, sona_blw_statements):
        periods = [s.period for s in sona_blw_statements]
        sales = [s.sales for s in sona_blw_statements]
        result = compute_multi_period_trend("Sales", periods, sales, higher_is_better=True)
        # FY2019->FY2020 is a real, significant revenue drop (COVID) amid
        # otherwise strong growth -> must be MIXED, not smoothed to IMPROVING.
        assert result.direction == TrendDirection.MIXED

    def test_real_revenue_overall_change_reflects_full_period_growth(self, sona_blw_statements):
        periods = [s.period for s in sona_blw_statements]
        sales = [s.sales for s in sona_blw_statements]
        result = compute_multi_period_trend("Sales", periods, sales, higher_is_better=True)
        # FY2017=503.3, FY2026=4123.67 -> massive real growth over the period.
        assert result.percentage_change > 5.0
        assert result.significance == ConfidenceLevel.HIGH

    def test_from_metric_results_convenience_wrapper(self, sona_blw_statements):
        from app.analysis.fundamentals import compute_pat_margin

        results = [compute_pat_margin(s) for s in sona_blw_statements]
        trend = compute_multi_period_trend_from_metric_results(results, higher_is_better=True)
        assert trend.metric_name == "PAT Margin"
        assert trend.direction in (
            TrendDirection.IMPROVING, TrendDirection.STABLE,
            TrendDirection.DETERIORATING, TrendDirection.MIXED,
        )

    def test_from_metric_results_empty_list_raises(self):
        with pytest.raises(ValueError):
            compute_multi_period_trend_from_metric_results([])

    def test_from_metric_results_skips_non_ok_status_as_none(self):
        from app.core.enums import DataStatus, UnitOfMeasure

        results = [
            MetricResult(metric_name="X", formula="f", inputs={}, value=100.0,
                         unit=UnitOfMeasure.INR_CRORE, period="FY24", status=DataStatus.OK),
            MetricResult(metric_name="X", formula="f", inputs={}, value=None,
                         unit=UnitOfMeasure.INR_CRORE, period="FY25", status=DataStatus.MISSING_INPUT),
            MetricResult(metric_name="X", formula="f", inputs={}, value=140.0,
                         unit=UnitOfMeasure.INR_CRORE, period="FY26", status=DataStatus.OK),
        ]
        trend = compute_multi_period_trend_from_metric_results(results, higher_is_better=True)
        assert trend.values == [100.0, None, 140.0]
        assert trend.direction == TrendDirection.IMPROVING  # bridges across the gap
