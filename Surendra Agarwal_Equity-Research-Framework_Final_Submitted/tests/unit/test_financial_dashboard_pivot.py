"""Tests for app/ui/pages/financial_dashboard.py's pivot table (year
columns, metric rows) against real Sona BLW data."""

from __future__ import annotations

from pathlib import Path

from app.core.enums import DataStatus, UnitOfMeasure
from app.core.models import MetricResult
from app.ui.pages.financial_dashboard import (
    _format_value,
    _period_sort_key,
    metrics_to_rows,
    pivot_metrics_to_wide_table,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_EXCEL = PROJECT_ROOT / "data" / "sample" / "Sona_BLW_Precis_screener_export.xlsx"


def _metric(name, period, value, unit=UnitOfMeasure.PERCENT, status=DataStatus.OK):
    return MetricResult(
        metric_name=name, formula="f", inputs={}, value=value, unit=unit,
        period=period, status=status,
    )


class TestFormatValue:
    def test_percent_formatted_with_percent_sign(self):
        m = _metric("X", "FY2026", 0.2524, unit=UnitOfMeasure.PERCENT)
        assert _format_value(m) == "25.24%"

    def test_ratio_formatted_with_x_suffix(self):
        m = _metric("X", "FY2026", 0.06, unit=UnitOfMeasure.RATIO)
        assert _format_value(m) == "0.06x"

    def test_not_ok_status_shows_na(self):
        m = _metric("X", "FY2026", None, status=DataStatus.UNAVAILABLE)
        assert _format_value(m) == "N/A"

    def test_none_value_shows_na_even_if_status_ok(self):
        m = _metric("X", "FY2026", None, status=DataStatus.OK)
        assert _format_value(m) == "N/A"


class TestPeriodSortKey:
    def test_standard_fy_periods_sort_chronologically(self):
        periods = ["FY2026", "FY2017", "FY2022"]
        assert sorted(periods, key=_period_sort_key) == ["FY2017", "FY2022", "FY2026"]

    def test_cagr_range_period_sorts_after_standard_periods(self):
        periods = ["FY2026", "FY2023-FY2026", "FY2017"]
        result = sorted(periods, key=_period_sort_key)
        assert result[-1] == "FY2023-FY2026"
        assert result[:2] == ["FY2017", "FY2026"]

    def test_ten_years_sort_correctly_not_lexicographically(self):
        periods = ["FY2099", "FY2100", "FY2017"]
        assert sorted(periods, key=_period_sort_key) == ["FY2017", "FY2099", "FY2100"]


class TestPivotMetricsToWideTable:
    def test_empty_input_returns_empty_dataframe(self):
        df = pivot_metrics_to_wide_table([])
        assert df.empty

    def test_basic_pivot_shape(self):
        metrics = [
            _metric("ROE", "FY2025", 0.10),
            _metric("ROE", "FY2026", 0.11),
            _metric("Debt/Equity", "FY2025", 0.05, unit=UnitOfMeasure.RATIO),
            _metric("Debt/Equity", "FY2026", 0.06, unit=UnitOfMeasure.RATIO),
        ]
        df = pivot_metrics_to_wide_table(metrics)
        assert list(df.index) == ["ROE", "Debt/Equity"]
        assert list(df.columns) == ["FY2025", "FY2026"]
        assert df.loc["ROE", "FY2026"] == "11.00%"
        assert df.loc["Debt/Equity", "FY2025"] == "0.05x"

    def test_metric_row_order_preserves_first_appearance(self):
        metrics = [
            _metric("Z Metric", "FY2026", 0.1),
            _metric("A Metric", "FY2026", 0.2),
        ]
        df = pivot_metrics_to_wide_table(metrics)
        assert list(df.index) == ["Z Metric", "A Metric"]

    def test_missing_cell_shows_blank_not_na_text(self):
        metrics = [
            _metric("Revenue CAGR (3yr)", "FY2023-FY2026", 0.1899),
            _metric("ROE", "FY2026", 0.11),
        ]
        df = pivot_metrics_to_wide_table(metrics)
        assert df.loc["Revenue CAGR (3yr)", "FY2026"] == ""
        assert df.loc["ROE", "FY2023-FY2026"] == ""
        assert df.loc["Revenue CAGR (3yr)", "FY2023-FY2026"] == "18.99%"

    def test_real_sona_blw_fundamentals_pivot(self):
        from app.data.loaders import load_screener_excel
        from app.data.financial_data import build_canonical_statements
        from app.analysis.fundamentals import compute_all_fundamentals

        raw = load_screener_excel(SAMPLE_EXCEL, company_name="Sona BLW Precision Forgings Ltd")
        statements = build_canonical_statements(raw)
        fund_metrics = compute_all_fundamentals(statements)
        df = pivot_metrics_to_wide_table(fund_metrics)

        assert list(df.columns)[:10] == [f"FY{y}" for y in range(2017, 2027)]
        assert list(df.columns)[-1] == "FY2023-FY2026"
        assert df.loc["EBITDA Margin", "FY2026"] == "25.24%"

    def test_duplicate_metric_period_pair_last_write_wins_deterministically(self):
        metrics = [
            _metric("ROE", "FY2026", 0.10),
            _metric("ROE", "FY2026", 0.99),
        ]
        df = pivot_metrics_to_wide_table(metrics)
        assert df.loc["ROE", "FY2026"] == "99.00%"


class TestMetricsToRowsStillWorks:
    def test_long_format_unchanged_in_shape(self):
        metrics = [_metric("ROE", "FY2026", 0.11)]
        rows = metrics_to_rows(metrics)
        assert rows == [{"Metric": "ROE", "Period": "FY2026", "Value": "11.00%", "Status": "ok"}]
