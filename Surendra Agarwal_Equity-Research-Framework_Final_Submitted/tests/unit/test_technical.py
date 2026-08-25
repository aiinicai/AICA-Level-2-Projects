"""Tests for app/analysis/technical.py.

Where possible, reference values are computed independently (a small
pure-Python loop, not by calling the pandas-based implementation under
test with different arguments) so these tests can actually catch an
algebra/sign error, not just confirm internal self-consistency.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from app.core.enums import DataStatus
from app.analysis.technical import (
    compute_all_smas,
    compute_beta,
    compute_bollinger_bands,
    compute_historical_volatility,
    compute_macd,
    compute_relative_strength,
    compute_rsi,
    compute_sma,
    compute_volume_trend,
)


def _independent_wilder_rsi(prices: list[float], period: int) -> float:
    """Pure-Python Wilder RSI, written independently of technical.py's
    pandas implementation, used as ground truth in tests below."""
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]

    alpha = 1.0 / period
    avg_gain = gains[0]
    avg_loss = losses[0]
    for i in range(1, len(gains)):
        avg_gain = (1 - alpha) * avg_gain + alpha * gains[i]
        avg_loss = (1 - alpha) * avg_loss + alpha * losses[i]

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


class TestSma:
    def test_sma_exact_mean(self):
        close = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        result = compute_sma(close, window=5)
        assert result.status == DataStatus.OK
        assert result.value == 30.0

    def test_sma_uses_only_trailing_window(self):
        close = pd.Series([1.0, 1.0, 1.0, 10.0, 20.0, 30.0])
        result = compute_sma(close, window=3)
        assert result.value == round((10.0 + 20.0 + 30.0) / 3, 2)

    def test_sma_insufficient_history(self):
        close = pd.Series([1.0, 2.0])
        result = compute_sma(close, window=20)
        assert result.status == DataStatus.INSUFFICIENT_HISTORY
        assert result.value is None

    def test_compute_all_smas_returns_four_windows(self):
        close = pd.Series(list(range(1, 251)), dtype=float)
        results = compute_all_smas(close)
        assert len(results) == 4
        assert all(r.status == DataStatus.OK for r in results)


class TestRsi:
    def test_rsi_matches_independent_wilder_calc(self):
        prices = [44.0, 44.5, 43.5, 44.5, 45.5, 44.0]
        close = pd.Series(prices)
        expected = _independent_wilder_rsi(prices, period=3)
        result = compute_rsi(close, period=3)
        assert result.status == DataStatus.OK
        assert abs(result.value - round(expected, 2)) < 0.05

    def test_rsi_all_gains_is_100(self):
        # Every period a gain, zero losses -> RSI must be exactly 100.
        close = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0])
        result = compute_rsi(close, period=3)
        assert result.value == 100.0

    def test_rsi_all_losses_is_0(self):
        close = pd.Series([14.0, 13.0, 12.0, 11.0, 10.0])
        result = compute_rsi(close, period=3)
        assert result.value == 0.0

    def test_rsi_insufficient_history(self):
        close = pd.Series([10.0, 11.0])
        result = compute_rsi(close, period=14)
        assert result.status == DataStatus.INSUFFICIENT_HISTORY

    def test_rsi_bounded_between_0_and_100(self):
        rng = np.random.default_rng(42)
        prices = pd.Series(100 + np.cumsum(rng.normal(0, 1, 100)))
        result = compute_rsi(prices, period=14)
        assert result.status == DataStatus.OK
        assert 0.0 <= result.value <= 100.0


class TestMacd:
    def test_macd_matches_independent_ema_calc(self):
        rng = np.random.default_rng(1)
        prices = pd.Series(100 + np.cumsum(rng.normal(0, 1, 60)))
        result = compute_macd(prices, fast=12, slow=26, signal=9)
        assert result.status == DataStatus.OK
        # Independently recompute via pandas ewm with the same formula,
        # written as a separate expression to catch fast/slow ordering bugs.
        ema_fast = prices.ewm(span=12, adjust=False).mean()
        ema_slow = prices.ewm(span=26, adjust=False).mean()
        expected_macd = float((ema_fast - ema_slow).iloc[-1])
        assert abs(result.value - round(expected_macd, 4)) < 1e-9

    def test_macd_insufficient_history(self):
        close = pd.Series([1.0] * 10)
        result = compute_macd(close)
        assert result.status == DataStatus.INSUFFICIENT_HISTORY


class TestBollinger:
    def test_bollinger_middle_equals_sma(self):
        close = pd.Series([float(i) for i in range(1, 21)])  # 1..20
        result = compute_bollinger_bands(close, window=20)
        assert result.status == DataStatus.OK
        assert result.value == round(close.mean(), 2)

    def test_bollinger_insufficient_history(self):
        close = pd.Series([1.0, 2.0])
        result = compute_bollinger_bands(close, window=20)
        assert result.status == DataStatus.INSUFFICIENT_HISTORY


class TestHistoricalVolatility:
    def test_volatility_matches_manual_log_return_std(self):
        prices = pd.Series([100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0, 108.0, 107.0, 110.0, 111.0])
        result = compute_historical_volatility(prices, window=10, trading_days_per_year=252)
        assert result.status == DataStatus.OK
        log_returns = np.log(prices / prices.shift(1)).dropna()
        expected = float(log_returns.tail(10).std()) * (252 ** 0.5)
        assert abs(result.value - round(expected, 4)) < 1e-6

    def test_volatility_insufficient_history(self):
        prices = pd.Series([100.0, 101.0])
        result = compute_historical_volatility(prices, window=20)
        assert result.status == DataStatus.INSUFFICIENT_HISTORY


class TestBeta:
    def test_beta_of_stock_against_itself_is_one(self):
        rng = np.random.default_rng(7)
        prices = pd.Series(100 + np.cumsum(rng.normal(0, 1, 300)))
        result = compute_beta(prices, prices, window=252)
        assert result.status == DataStatus.OK
        assert abs(result.value - 1.0) < 1e-6

    def test_beta_mismatched_lengths_returns_calculation_error(self):
        s1 = pd.Series([1.0, 2.0, 3.0])
        s2 = pd.Series([1.0, 2.0])
        result = compute_beta(s1, s2, window=2)
        assert result.status == DataStatus.CALCULATION_ERROR

    def test_beta_zero_variance_benchmark_returns_calculation_error(self):
        rng = np.random.default_rng(3)
        stock = pd.Series(100 + np.cumsum(rng.normal(0, 1, 260)))
        flat_benchmark = pd.Series([100.0] * 260)  # zero returns -> zero variance
        result = compute_beta(stock, flat_benchmark, window=252)
        assert result.status == DataStatus.CALCULATION_ERROR


class TestRelativeStrength:
    def test_relative_strength_double_the_move(self):
        # Stock doubles (+100%), benchmark up 50% -> RS ratio = 2.0
        stock = pd.Series([100.0] + [100.0] * 61 + [200.0])
        bench = pd.Series([100.0] + [100.0] * 61 + [150.0])
        result = compute_relative_strength(stock, bench, window=62)
        assert result.status == DataStatus.OK
        assert abs(result.value - 2.0) < 1e-6

    def test_relative_strength_zero_benchmark_change_returns_calc_error(self):
        stock = pd.Series([100.0] * 62 + [110.0])
        bench = pd.Series([100.0] * 63)  # flat -> zero change
        result = compute_relative_strength(stock, bench, window=62)
        assert result.status == DataStatus.CALCULATION_ERROR


class TestVolumeTrend:
    def test_volume_trend_exact_ratio(self):
        volume = pd.Series([100.0] * 40 + [200.0] * 20)  # long avg mixes both, short avg is all 200
        result = compute_volume_trend(volume, short_window=20, long_window=60)
        assert result.status == DataStatus.OK
        long_avg = (100.0 * 40 + 200.0 * 20) / 60
        assert abs(result.value - round(200.0 / long_avg, 3)) < 1e-6

    def test_volume_trend_insufficient_history(self):
        volume = pd.Series([100.0] * 10)
        result = compute_volume_trend(volume, short_window=20, long_window=60)
        assert result.status == DataStatus.INSUFFICIENT_HISTORY
