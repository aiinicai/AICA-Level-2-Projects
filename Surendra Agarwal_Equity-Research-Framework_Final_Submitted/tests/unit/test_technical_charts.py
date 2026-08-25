"""Tests for app/ui/pages/technical_dashboard.py's chart builders and
app/analysis/technical.py's new full-series functions."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.analysis.technical import (
    compute_rsi, compute_rsi_series, compute_sma, compute_sma_series,
)
from app.ui.pages.technical_dashboard import (
    build_candlestick_figure, build_rsi_figure, build_volume_figure, format_technical_summary,
)


def _synthetic_ohlcv(n: int = 300, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    open_ = close + rng.normal(0, 0.5, n)
    high = np.maximum(open_, close) + np.abs(rng.normal(0, 0.5, n))
    low = np.minimum(open_, close) - np.abs(rng.normal(0, 0.5, n))
    volume = rng.integers(100_000, 1_000_000, n).astype(float)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=dates)


class TestSeriesVsPointInTimeAgreement:
    def test_sma_series_last_value_matches_point_metric(self):
        df = _synthetic_ohlcv()
        series = compute_sma_series(df["close"], 50)
        point = compute_sma(df["close"], 50)
        # compute_sma() rounds to 2dp for display; series is unrounded.
        assert abs(series.iloc[-1] - point.value) < 0.01

    def test_rsi_series_last_value_matches_point_metric(self):
        df = _synthetic_ohlcv()
        series = compute_rsi_series(df["close"], 14)
        point = compute_rsi(df["close"], 14)
        assert abs(series.iloc[-1] - point.value) < 0.01

    def test_rsi_series_same_length_as_input(self):
        df = _synthetic_ohlcv()
        series = compute_rsi_series(df["close"], 14)
        assert len(series) == len(df)

    def test_rsi_series_warmup_period_is_nan(self):
        df = _synthetic_ohlcv()
        series = compute_rsi_series(df["close"], 14)
        assert pd.isna(series.iloc[0])

    def test_rsi_series_all_gains_is_100_throughout_valid_region(self):
        close = pd.Series(np.arange(100.0, 150.0))
        series = compute_rsi_series(close, period=14)
        valid = series.dropna()
        assert (valid == 100.0).all()

    def test_sma_series_matches_pandas_rolling_directly(self):
        df = _synthetic_ohlcv()
        series = compute_sma_series(df["close"], 20)
        expected = df["close"].rolling(window=20).mean()
        pd.testing.assert_series_equal(series, expected)


class TestBuildCandlestickFigure:
    def test_contains_one_candlestick_trace(self):
        df = _synthetic_ohlcv()
        fig = build_candlestick_figure(df)
        candlestick_traces = [t for t in fig.data if t.type == "candlestick"]
        assert len(candlestick_traces) == 1

    def test_contains_sma_overlay_traces_when_enough_history(self):
        df = _synthetic_ohlcv(n=300)
        fig = build_candlestick_figure(df)
        trace_names = [t.name for t in fig.data]
        assert "SMA 20" in trace_names
        assert "SMA 50" in trace_names
        assert "SMA 100" in trace_names
        assert "SMA 200" in trace_names

    def test_omits_sma_when_insufficient_history_rather_than_faking(self):
        df = _synthetic_ohlcv(n=100)
        fig = build_candlestick_figure(df)
        trace_names = [t.name for t in fig.data]
        assert "SMA 20" in trace_names
        assert "SMA 200" not in trace_names

    def test_candlestick_ohlc_values_match_source_data(self):
        df = _synthetic_ohlcv()
        fig = build_candlestick_figure(df)
        candlestick = next(t for t in fig.data if t.type == "candlestick")
        assert list(candlestick.close) == pytest.approx(df["close"].tolist())

    def test_custom_sma_windows_respected(self):
        df = _synthetic_ohlcv(n=300)
        fig = build_candlestick_figure(df, sma_windows=(10, 30))
        trace_names = [t.name for t in fig.data]
        assert "SMA 10" in trace_names
        assert "SMA 30" in trace_names
        assert "SMA 20" not in trace_names


class TestBuildRsiFigure:
    def test_contains_rsi_trace(self):
        df = _synthetic_ohlcv()
        fig = build_rsi_figure(df)
        assert len(fig.data) == 1
        assert fig.data[0].name == "RSI (14)"

    def test_rsi_values_match_compute_rsi_series(self):
        df = _synthetic_ohlcv()
        fig = build_rsi_figure(df)
        expected = compute_rsi_series(df["close"], 14)
        actual = pd.Series(fig.data[0].y)
        assert actual.iloc[-1] == pytest.approx(expected.iloc[-1])

    def test_yaxis_range_is_0_to_100(self):
        df = _synthetic_ohlcv()
        fig = build_rsi_figure(df)
        assert fig.layout.yaxis.range == (0, 100)

    def test_reference_lines_present(self):
        df = _synthetic_ohlcv()
        fig = build_rsi_figure(df)
        hline_ys = {shape.y0 for shape in fig.layout.shapes}
        assert 70 in hline_ys
        assert 30 in hline_ys


class TestBuildVolumeFigure:
    def test_contains_bar_trace(self):
        df = _synthetic_ohlcv()
        fig = build_volume_figure(df)
        assert fig.data[0].type == "bar"

    def test_volume_values_match_source(self):
        df = _synthetic_ohlcv()
        fig = build_volume_figure(df)
        assert list(fig.data[0].y) == pytest.approx(df["volume"].tolist())

    def test_up_day_colored_green_down_day_colored_red(self):
        df = pd.DataFrame({
            "open": [100.0, 100.0], "high": [105.0, 105.0], "low": [95.0, 95.0],
            "close": [102.0, 98.0],
            "volume": [1000.0, 1000.0],
        })
        fig = build_volume_figure(df)
        colors = fig.data[0].marker.color
        assert colors[0] == "#2ca02c"
        assert colors[1] == "#d62728"


class TestFormatTechnicalSummary:
    def test_formats_ok_metric(self):
        from app.core.enums import DataStatus, UnitOfMeasure
        from app.core.models import MetricResult

        m = MetricResult(metric_name="RSI (14)", formula="f", inputs={}, value=75.42,
                          unit=UnitOfMeasure.RATIO, period="latest", status=DataStatus.OK)
        rows = format_technical_summary([m])
        assert rows[0]["Value"] == "75.42"


class TestRealSonaBLWData:
    def test_candlestick_and_rsi_figures_build_from_real_price_history(self):
        from pathlib import Path
        from app.data.market_data import load_nse_csv_price_history

        project_root = Path(__file__).resolve().parent.parent.parent
        csv_path = project_root / "data" / "sample" / "SONACOMS_NSE_price_history.csv"
        df = load_nse_csv_price_history(csv_path)

        fig = build_candlestick_figure(df)
        assert len(fig.data) == 5

        rsi_fig = build_rsi_figure(df)
        assert rsi_fig.data[0].y[-1] == pytest.approx(75.42, abs=0.01)
