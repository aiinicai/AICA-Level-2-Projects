import numpy as np
import pandas as pd
import pytest

from bsa import indicators as ind


def _series(values, start="2025-01-01"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


def test_sma_and_ema():
    s = _series(range(1, 11))
    assert ind.sma(s, 5).iloc[-1] == pytest.approx(8.0)
    assert np.isnan(ind.sma(s, 5).iloc[3])
    e = ind.ema(_series([10.0] * 30), 12)
    assert e.iloc[-1] == pytest.approx(10.0)


def test_rsi_extremes_and_midpoint():
    up = _series(np.arange(1, 60))
    assert ind.rsi(up).iloc[-1] == pytest.approx(100.0)
    down = _series(np.arange(60, 1, -1))
    assert ind.rsi(down).iloc[-1] == pytest.approx(0.0)
    zigzag = _series([100 + (1 if i % 2 else -1) for i in range(200)])
    assert ind.rsi(zigzag).iloc[-1] == pytest.approx(50.0, abs=3)


def test_macd_zero_for_flat_series():
    m = ind.macd(_series([50.0] * 60))
    assert m["macd"].iloc[-1] == pytest.approx(0.0)
    assert m["hist"].iloc[-1] == pytest.approx(0.0)


def test_max_drawdown_hand_checked():
    s = _series([100, 120, 60, 90])
    assert ind.max_drawdown(s) == pytest.approx(-50.0)


def test_beta_of_series_against_itself_and_double():
    rng = np.random.default_rng(1)
    bench = _series(100 * np.exp(rng.normal(0, 0.01, 300).cumsum()))
    assert ind.beta(bench, bench) == pytest.approx(1.0)
    levered = _series(100 * (1 + 2 * bench.pct_change().fillna(0)).cumprod().values)
    assert ind.beta(levered, bench) == pytest.approx(2.0, rel=1e-6)


def test_period_return_uses_calendar_offset():
    idx = pd.date_range("2025-01-01", "2026-01-01", freq="D")
    s = pd.Series(np.linspace(100, 200, len(idx)), index=idx)
    assert ind.period_return(s, 12) == pytest.approx(100.0)
    assert ind.period_return(s, 36) is None  # not enough history


def test_swing_levels():
    lows = [10, 9, 8, 7, 6, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 11, 12, 13, 14, 15]
    low = _series(lows)
    high = low + 1
    lv = ind.swing_levels(high, low, close=12.5, lookback=200, window=3)
    assert 10.0 in lv["supports"] and 5.0 in lv["supports"]
    assert lv["resistances"] == [16.0]


def test_technical_summary_signals(synthetic_raw):
    t = ind.technical_summary(synthetic_raw.ohlc, synthetic_raw.bench)
    assert t["sma200"] is not None and t["rsi14"] is not None
    assert t["returns"]["1y"] is not None
    names = [s["indicator"] for s in t["signals"]]
    assert "RSI (14)" in names and "MACD (12,26,9)" in names
