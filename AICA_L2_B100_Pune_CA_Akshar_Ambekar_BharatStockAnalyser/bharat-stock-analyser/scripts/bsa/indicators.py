"""Technical indicators and price statistics. Pure pandas, no network access.

All functions take a pandas Series of prices indexed by date (ascending).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .fmt import num

TRADING_DAYS = 252


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's RSI."""
    delta = s.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss
    out = 100.0 - 100.0 / (1.0 + rs)
    # No losses in the window: RSI is 100 by definition.
    out = out.where(avg_loss != 0, 100.0)
    return out.where(avg_gain.notna())


def macd(s: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    line = ema(s, fast) - ema(s, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def bollinger(s: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    mid = sma(s, n)
    sd = s.rolling(n, min_periods=n).std(ddof=0)
    return pd.DataFrame({"mid": mid, "upper": mid + k * sd, "lower": mid - k * sd})


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def period_return(s: pd.Series, months: int) -> float | None:
    """Percent return over a calendar period ending at the last observation."""
    s = s.dropna()
    if s.empty:
        return None
    end = s.index[-1]
    start_date = end - pd.DateOffset(months=months)
    if s.index[0] > start_date + pd.Timedelta(days=7):
        return None
    start = s.asof(start_date)
    if start is None or not math.isfinite(start) or start <= 0:
        return None
    return (s.iloc[-1] / start - 1.0) * 100.0


def annualised_vol(s: pd.Series, days: int = TRADING_DAYS) -> float | None:
    r = s.dropna().pct_change().dropna().tail(days)
    if len(r) < 20:
        return None
    return float(r.std(ddof=1) * math.sqrt(TRADING_DAYS) * 100.0)


def max_drawdown(s: pd.Series, days: int = TRADING_DAYS) -> float | None:
    """Largest peak-to-trough fall in percent (a negative number) over the window."""
    w = s.dropna().tail(days)
    if len(w) < 2:
        return None
    dd = w / w.cummax() - 1.0
    return float(dd.min() * 100.0)


def beta(stock: pd.Series, bench: pd.Series, days: int = TRADING_DAYS) -> float | None:
    """Beta from daily returns over the window, dates aligned."""
    df = pd.concat([stock, bench], axis=1, join="inner").dropna()
    r = df.pct_change().dropna().tail(days)
    if len(r) < 60:
        return None
    var = r.iloc[:, 1].var(ddof=1)
    if var == 0:
        return None
    return float(r.iloc[:, 0].cov(r.iloc[:, 1]) / var)


def swing_levels(high: pd.Series, low: pd.Series, close: float, lookback: int = 180,
                 window: int = 5, count: int = 2) -> dict:
    """Nearest swing-low supports below and swing-high resistances above the close.

    A swing low is a bar whose low is the minimum of the surrounding +/- window bars.
    Levels within 1.5 percent of each other are merged.
    """
    h, l = high.tail(lookback), low.tail(lookback)
    span = 2 * window + 1
    lows = l[l == l.rolling(span, center=True, min_periods=span).min()].dropna()
    highs = h[h == h.rolling(span, center=True, min_periods=span).max()].dropna()

    def merge(levels: list[float]) -> list[float]:
        out: list[float] = []
        for v in levels:
            if all(abs(v / o - 1.0) > 0.015 for o in out):
                out.append(v)
        return out

    supports = merge(sorted((float(v) for v in lows if v < close), reverse=True))[:count]
    resistances = merge(sorted(float(v) for v in highs if v > close))[:count]
    return {"supports": supports, "resistances": resistances}


def technical_summary(ohlc: pd.DataFrame, bench_close: pd.Series | None = None) -> dict:
    """Compute the indicator set used in the report.

    ohlc needs columns Open, High, Low, Close, Volume (split-adjusted) and 'Adj Close' optional.
    Returns plain numbers plus a list of signal rows (indicator, value, reading, signal).
    """
    close = ohlc["Close"].dropna()
    adj = ohlc["Adj Close"].dropna() if "Adj Close" in ohlc else close
    last = float(close.iloc[-1])

    s20, s50, s200 = sma(close, 20), sma(close, 50), sma(close, 200)
    e20 = ema(close, 20)
    r = rsi(close)
    m = macd(close)
    bb = bollinger(close)
    a = atr(ohlc["High"], ohlc["Low"], close)

    def last_of(series: pd.Series) -> float | None:
        series = series.dropna()
        return num(series.iloc[-1]) if not series.empty else None

    v = {
        "close": last,
        "sma20": last_of(s20),
        "sma50": last_of(s50),
        "sma200": last_of(s200),
        "ema20": last_of(e20),
        "rsi14": last_of(r),
        "macd": last_of(m["macd"]),
        "macd_signal": last_of(m["signal"]),
        "macd_hist": last_of(m["hist"]),
        "bb_upper": last_of(bb["upper"]),
        "bb_lower": last_of(bb["lower"]),
        "atr14": last_of(a),
        "high_52w": num(ohlc["High"].tail(TRADING_DAYS).max()),
        "low_52w": num(ohlc["Low"].tail(TRADING_DAYS).min()),
        "vol_20d_avg": num(ohlc["Volume"].tail(20).mean()),
        "vol_3m_avg": num(ohlc["Volume"].tail(63).mean()),
        "value_3m_avg": num((ohlc["Volume"] * close).tail(63).mean()),
        "volatility_1y": annualised_vol(adj),
        "max_drawdown_1y": max_drawdown(adj),
        "returns": {k: period_return(adj, mth) for k, mth in
                    (("1m", 1), ("3m", 3), ("6m", 6), ("1y", 12), ("3y", 36), ("5y", 60))},
    }
    v["atr_pct"] = (v["atr14"] / last * 100.0) if v["atr14"] else None
    v["pct_from_52w_high"] = (last / v["high_52w"] - 1.0) * 100.0 if v["high_52w"] else None
    v["pct_from_52w_low"] = (last / v["low_52w"] - 1.0) * 100.0 if v["low_52w"] else None
    v["volume_ratio"] = (num(ohlc["Volume"].iloc[-1]) or 0) / v["vol_3m_avg"] if v["vol_3m_avg"] else None

    # Golden or death cross within the last 60 sessions.
    cross = None
    both = pd.concat([s50, s200], axis=1).dropna()
    if len(both) > 1:
        diff = np.sign(both.iloc[:, 0] - both.iloc[:, 1])
        changes = diff[diff.diff().fillna(0) != 0].tail(1)
        if not changes.empty and changes.index[0] >= both.index[-min(60, len(both))]:
            cross = {"type": "golden" if changes.iloc[0] > 0 else "death",
                     "date": changes.index[0].strftime("%d-%b-%Y")}
    v["recent_cross"] = cross

    if bench_close is not None:
        v["beta_1y"] = beta(adj, bench_close)
        v["bench_returns"] = {k: period_return(bench_close, mth) for k, mth in
                              (("1m", 1), ("3m", 3), ("6m", 6), ("1y", 12), ("3y", 36))}
    else:
        v["beta_1y"], v["bench_returns"] = None, {}

    v["levels"] = swing_levels(ohlc["High"], ohlc["Low"], last)
    v["signals"] = _signals(v)
    return v


def _signals(v: dict) -> list[dict]:
    rows = []
    c = v["close"]

    def add(name, value, reading, signal):
        rows.append({"indicator": name, "value": value, "reading": reading, "signal": signal})

    for key, label in (("sma50", "50-day moving average"), ("sma200", "200-day moving average")):
        if v[key]:
            above = c > v[key]
            add(label, v[key], f"Price {'above' if above else 'below'} by {abs(c / v[key] - 1) * 100:.1f}%",
                "Bullish" if above else "Bearish")
    if v["sma50"] and v["sma200"]:
        up = v["sma50"] > v["sma200"]
        add("50-DMA vs 200-DMA", v["sma50"] - v["sma200"],
            "50-DMA above 200-DMA (uptrend structure)" if up else "50-DMA below 200-DMA (downtrend structure)",
            "Bullish" if up else "Bearish")
    if v["rsi14"] is not None:
        r = v["rsi14"]
        if r >= 70:
            reading, sig = "Overbought (70 or above)", "Caution"
        elif r <= 30:
            reading, sig = "Oversold (30 or below)", "Watch for reversal"
        elif r >= 55:
            reading, sig = "Positive momentum", "Bullish"
        elif r <= 45:
            reading, sig = "Weak momentum", "Bearish"
        else:
            reading, sig = "Neutral zone", "Neutral"
        add("RSI (14)", r, reading, sig)
    if v["macd"] is not None and v["macd_signal"] is not None:
        up = v["macd"] > v["macd_signal"]
        add("MACD (12,26,9)", v["macd"], "MACD above signal line" if up else "MACD below signal line",
            "Bullish" if up else "Bearish")
    if v["bb_upper"] and v["bb_lower"]:
        width = v["bb_upper"] - v["bb_lower"]
        pos = (c - v["bb_lower"]) / width * 100 if width else 50
        sig = "Caution" if pos > 95 else ("Watch for reversal" if pos < 5 else "Neutral")
        add("Bollinger band position", pos, f"{pos:.0f}% of the band width", sig)
    if v["pct_from_52w_high"] is not None:
        d = v["pct_from_52w_high"]
        sig = "Bullish" if d > -5 else ("Bearish" if d < -25 else "Neutral")
        add("Distance from 52-week high", d, f"{d:.1f}% from the high", sig)
    if v["volume_ratio"] is not None:
        add("Volume vs 3-month average", v["volume_ratio"], f"{v['volume_ratio']:.2f} times the average",
            "Neutral")
    return rows
