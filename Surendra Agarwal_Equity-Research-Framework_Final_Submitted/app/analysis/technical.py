"""Technical analysis engine — Module 6.

Every indicator is hand-rolled in pandas/numpy rather than pulled from a
third-party `ta`-style library, per the Step 2 architecture decision:
these are simple enough (~10 lines each) that implementing them
directly keeps this layer fully auditable and removes an external
dependency whose internals we can't easily verify. Each function is
unit-tested against a hand-computed reference example (see
tests/unit/test_technical.py), not just "does it run."

Input contract: every function takes a pandas Series/DataFrame of
price data (as returned by app/data/market_data.py's
MarketDataProvider), never a company name or ticker — this module has
no knowledge of how the data was fetched, keeping it independently
testable with synthetic data.
"""

from __future__ import annotations

import pandas as pd

from app.core.enums import DataStatus, UnitOfMeasure
from app.core.models import MetricResult


def _insufficient(metric_name: str, formula: str, required: int, actual: int) -> MetricResult:
    return MetricResult(
        metric_name=metric_name, formula=formula, inputs={"periods_required": float(required), "periods_available": float(actual)},
        value=None, unit=UnitOfMeasure.RATIO, period="latest",
        status=DataStatus.INSUFFICIENT_HISTORY,
        data_quality_notes=[f"Requires at least {required} price observations; only {actual} available."],
    )


# --------------------------------------------------------------------------
# Trend — Simple Moving Averages
# --------------------------------------------------------------------------


def compute_sma_series(close: pd.Series, window: int) -> pd.Series:
    """Full rolling-SMA series (not just the latest point) — used for
    charting. compute_sma() below is a thin wrapper that takes the last
    value of this same series, so the point-in-time metric and the
    charted line can never disagree."""
    return close.rolling(window=window).mean()


def compute_sma(close: pd.Series, window: int) -> MetricResult:
    """Latest Simple Moving Average over `window` periods."""
    metric_name = f"SMA {window}"
    formula = f"mean(close[-{window}:])"
    if len(close) < window:
        return _insufficient(metric_name, formula, window, len(close))
    series = compute_sma_series(close, window)
    value = series.iloc[-1]
    return MetricResult(
        metric_name=metric_name, formula=formula,
        inputs={"window": float(window), "latest_close": float(close.iloc[-1])},
        value=round(float(value), 2), unit=UnitOfMeasure.INR_ABSOLUTE, period="latest",
        status=DataStatus.OK,
    )


def compute_all_smas(close: pd.Series) -> list[MetricResult]:
    return [compute_sma(close, w) for w in (20, 50, 100, 200)]


# --------------------------------------------------------------------------
# Momentum — RSI, MACD
# --------------------------------------------------------------------------


def compute_rsi_series(close: pd.Series, period: int = 14) -> pd.Series:
    """Full Wilder-smoothed RSI series (not just the latest point) —
    used for charting. compute_rsi() below takes the last value of this
    same series, so the point-in-time metric and the charted line can
    never disagree. Periods before `period` observations are NaN
    (Wilder's method needs a warm-up window), matching pandas' own
    min_periods behavior rather than backfilling a guessed value.
    """
    delta = close.diff().dropna()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)

    avg_gain = gains.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # Where avg_loss is exactly 0 (no losses in the smoothing window),
    # RSI is maximally overbought by definition -> 100, not NaN.
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi.reindex(close.index)


def compute_rsi(close: pd.Series, period: int = 14) -> MetricResult:
    """Relative Strength Index, Wilder's smoothing method.

    Formula: RSI = 100 - (100 / (1 + RS)), RS = avg_gain / avg_loss,
    using Wilder's exponential smoothing (alpha = 1/period) rather than
    a simple rolling mean, matching the standard/textbook definition.
    """
    metric_name = f"RSI ({period})"
    formula = "100 - (100 / (1 + avg_gain/avg_loss)), Wilder smoothing"
    if len(close) < period + 1:
        return _insufficient(metric_name, formula, period + 1, len(close))

    series = compute_rsi_series(close, period)
    rsi_value = float(series.iloc[-1])

    delta = close.diff().dropna()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    latest_avg_gain = float(avg_gain.iloc[-1])
    latest_avg_loss = float(avg_loss.iloc[-1])

    return MetricResult(
        metric_name=metric_name, formula=formula,
        inputs={"period": float(period), "avg_gain": round(latest_avg_gain, 4), "avg_loss": round(latest_avg_loss, 4)},
        value=round(float(rsi_value), 2), unit=UnitOfMeasure.RATIO, period="latest", status=DataStatus.OK,
    )


def compute_macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> MetricResult:
    """MACD line, signal line, and histogram at the latest observation."""
    metric_name = "MACD"
    formula = f"EMA({fast}) - EMA({slow}); signal = EMA({signal}) of MACD line"
    min_required = slow + signal
    if len(close) < min_required:
        return _insufficient(metric_name, formula, min_required, len(close))

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return MetricResult(
        metric_name=metric_name, formula=formula,
        inputs={"fast": float(fast), "slow": float(slow), "signal": float(signal)},
        value=round(float(macd_line.iloc[-1]), 4), unit=UnitOfMeasure.INR_ABSOLUTE, period="latest",
        status=DataStatus.OK,
        interpretation=(
            f"signal_line={round(float(signal_line.iloc[-1]), 4)}, "
            f"histogram={round(float(histogram.iloc[-1]), 4)}"
        ),
    )


# --------------------------------------------------------------------------
# Volatility — Bollinger Bands, historical volatility
# --------------------------------------------------------------------------


def compute_bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0) -> MetricResult:
    metric_name = f"Bollinger Bands ({window}, {num_std}sd)"
    formula = "middle=SMA(window); upper/lower = middle +/- num_std * rolling_std(window)"
    if len(close) < window:
        return _insufficient(metric_name, formula, window, len(close))

    middle = close.tail(window).mean()
    std = close.tail(window).std()
    upper = middle + num_std * std
    lower = middle - num_std * std

    return MetricResult(
        metric_name=metric_name, formula=formula,
        inputs={"window": float(window), "num_std": num_std, "latest_close": float(close.iloc[-1])},
        value=round(float(middle), 2), unit=UnitOfMeasure.INR_ABSOLUTE, period="latest", status=DataStatus.OK,
        interpretation=f"upper={round(float(upper), 2)}, lower={round(float(lower), 2)}",
    )


def compute_historical_volatility(close: pd.Series, window: int = 20, trading_days_per_year: int = 252) -> MetricResult:
    """Annualized historical volatility from daily log returns."""
    import numpy as np

    metric_name = f"Historical Volatility ({window}d, annualized)"
    formula = "std(log_returns[-window:]) * sqrt(trading_days_per_year)"
    if len(close) < window + 1:
        return _insufficient(metric_name, formula, window + 1, len(close))

    log_returns = (close / close.shift(1)).apply(lambda x: None if x is None or x <= 0 else __import__("math").log(x)).dropna()
    recent_returns = log_returns.tail(window)
    if len(recent_returns) < 2:
        return _insufficient(metric_name, formula, window + 1, len(close))

    daily_std = float(recent_returns.std())
    annualized = daily_std * (trading_days_per_year ** 0.5)
    return MetricResult(
        metric_name=metric_name, formula=formula,
        inputs={"window": float(window), "daily_std": round(daily_std, 6)},
        value=round(annualized, 4), unit=UnitOfMeasure.PERCENT, period="latest", status=DataStatus.OK,
    )


# --------------------------------------------------------------------------
# Relative performance — beta, relative strength vs benchmark
# --------------------------------------------------------------------------


def compute_beta(stock_close: pd.Series, benchmark_close: pd.Series, window: int = 252) -> MetricResult:
    """Beta = Cov(stock_returns, benchmark_returns) / Var(benchmark_returns).

    Requires aligned (same-index) daily closes for stock and benchmark;
    caller is responsible for supplying already-aligned series (e.g. an
    inner join on date) — this function does not silently reindex/ffill,
    since that could fabricate price continuity that didn't exist.
    """
    metric_name = f"Beta ({window}d)"
    formula = "Cov(stock_returns, benchmark_returns) / Var(benchmark_returns)"
    if len(stock_close) != len(benchmark_close):
        return MetricResult(
            metric_name=metric_name, formula=formula, inputs={}, value=None,
            unit=UnitOfMeasure.RATIO, period="latest", status=DataStatus.CALCULATION_ERROR,
            data_quality_notes=[
                f"Stock series length ({len(stock_close)}) != benchmark series length "
                f"({len(benchmark_close)}). Series must be pre-aligned by date by the caller."
            ],
        )
    if len(stock_close) < window + 1:
        return _insufficient(metric_name, formula, window + 1, len(stock_close))

    stock_returns = stock_close.pct_change().dropna().tail(window)
    bench_returns = benchmark_close.pct_change().dropna().tail(window)
    n = min(len(stock_returns), len(bench_returns))
    stock_returns, bench_returns = stock_returns.tail(n), bench_returns.tail(n)

    covariance = stock_returns.cov(bench_returns)
    variance = bench_returns.var()
    if variance == 0:
        return MetricResult(
            metric_name=metric_name, formula=formula, inputs={"variance": 0.0}, value=None,
            unit=UnitOfMeasure.RATIO, period="latest", status=DataStatus.CALCULATION_ERROR,
            data_quality_notes=["Benchmark return variance is zero over this window; beta undefined."],
        )
    beta = covariance / variance
    return MetricResult(
        metric_name=metric_name, formula=formula,
        inputs={"window": float(window), "covariance": round(float(covariance), 8), "variance": round(float(variance), 8)},
        value=round(float(beta), 3), unit=UnitOfMeasure.RATIO, period="latest", status=DataStatus.OK,
    )


def compute_relative_strength(stock_close: pd.Series, benchmark_close: pd.Series, window: int = 63) -> MetricResult:
    """Relative strength = stock's % change / benchmark's % change over `window` periods."""
    metric_name = f"Relative Strength ({window}d)"
    formula = "stock_pct_change(window) / benchmark_pct_change(window)"
    if len(stock_close) < window + 1 or len(benchmark_close) < window + 1:
        return _insufficient(metric_name, formula, window + 1, min(len(stock_close), len(benchmark_close)))

    stock_change = (stock_close.iloc[-1] / stock_close.iloc[-window - 1]) - 1.0
    bench_change = (benchmark_close.iloc[-1] / benchmark_close.iloc[-window - 1]) - 1.0

    if bench_change == 0:
        return MetricResult(
            metric_name=metric_name, formula=formula, inputs={"benchmark_change": 0.0}, value=None,
            unit=UnitOfMeasure.RATIO, period="latest", status=DataStatus.CALCULATION_ERROR,
            data_quality_notes=["Benchmark change over this window is exactly zero; ratio undefined."],
        )
    value = stock_change / bench_change
    return MetricResult(
        metric_name=metric_name, formula=formula,
        inputs={"window": float(window), "stock_change": round(float(stock_change), 4), "benchmark_change": round(float(bench_change), 4)},
        value=round(float(value), 3), unit=UnitOfMeasure.RATIO, period="latest", status=DataStatus.OK,
    )


# --------------------------------------------------------------------------
# Volume
# --------------------------------------------------------------------------


def compute_volume_trend(volume: pd.Series, short_window: int = 20, long_window: int = 60) -> MetricResult:
    """Ratio of recent average volume to longer-term average volume."""
    metric_name = f"Volume Trend ({short_window}d / {long_window}d)"
    formula = f"mean(volume[-{short_window}:]) / mean(volume[-{long_window}:])"
    if len(volume) < long_window:
        return _insufficient(metric_name, formula, long_window, len(volume))

    short_avg = volume.tail(short_window).mean()
    long_avg = volume.tail(long_window).mean()
    if long_avg == 0:
        return MetricResult(
            metric_name=metric_name, formula=formula, inputs={"long_avg": 0.0}, value=None,
            unit=UnitOfMeasure.RATIO, period="latest", status=DataStatus.CALCULATION_ERROR,
            data_quality_notes=["Long-window average volume is zero; ratio undefined."],
        )
    value = short_avg / long_avg
    return MetricResult(
        metric_name=metric_name, formula=formula,
        inputs={"short_avg_volume": round(float(short_avg), 2), "long_avg_volume": round(float(long_avg), 2)},
        value=round(float(value), 3), unit=UnitOfMeasure.RATIO, period="latest", status=DataStatus.OK,
    )


def compute_all_technical_indicators(
    close: pd.Series, volume: pd.Series | None = None, benchmark_close: pd.Series | None = None
) -> list[MetricResult]:
    """Convenience: compute every indicator that has sufficient data available."""
    results: list[MetricResult] = compute_all_smas(close)
    results.append(compute_rsi(close))
    results.append(compute_macd(close))
    results.append(compute_bollinger_bands(close))
    results.append(compute_historical_volatility(close))
    if volume is not None:
        results.append(compute_volume_trend(volume))
    if benchmark_close is not None:
        results.append(compute_beta(close, benchmark_close))
        results.append(compute_relative_strength(close, benchmark_close))
    return results
