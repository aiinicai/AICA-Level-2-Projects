"""Report exhibits drawn with matplotlib and saved as PNG.

Palette (validated categorical order, light surface):
    series 1 blue   #2a78d6  the stock
    series 2 orange #eb6834  Nifty 50 / second measure
    series 3 aqua   #1baf7a  sector index / third measure
Status colours are reserved for the rating badge and are not used for series.
No chart uses two y-axes; different units go to separate panels.
"""

from __future__ import annotations

import os

os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.path.expanduser("~"), ".cache", "bsa-matplotlib"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from .fmt import CRORE, fmt_num  # noqa: E402

S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0"
NEUTRAL = "#c9c8c2"

plt.rcParams.update({
    "font.size": 8.5,
    "font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "axes.edgecolor": NEUTRAL,
    "axes.labelcolor": INK2,
    "axes.titlesize": 9.5,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": GRID,
    "grid.linewidth": 0.7,
    "xtick.color": INK2,
    "ytick.color": INK2,
    "xtick.major.size": 0,
    "ytick.major.size": 0,
    "legend.frameon": False,
    "legend.fontsize": 8,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})

DPI = 170
_inr_fmt = FuncFormatter(lambda v, _: fmt_num(v, 0, paren=False))


def _save(fig, path: str) -> str:
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    return path


def _legend(ax, ncol: int):
    """Legend in a row above the plot area so it never covers data."""
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=ncol, borderaxespad=0.3, handlelength=1.6,
              columnspacing=1.2)


def _date_axis(ax):
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))


def price_chart(ohlc: pd.DataFrame, sma50: pd.Series, sma200: pd.Series, path: str, years: int = 2) -> str:
    start = ohlc.index[-1] - pd.DateOffset(years=years)
    d = ohlc[ohlc.index >= start]
    fig, (ax, axv) = plt.subplots(2, 1, figsize=(7.2, 3.6), sharex=True, gridspec_kw={"height_ratios": [3.2, 1]})
    ax.plot(d.index, d["Close"], color=S1, lw=1.6, label="Close")
    ax.plot(d.index, sma50.reindex(d.index), color=S2, lw=1.1, label="50-day average")
    ax.plot(d.index, sma200.reindex(d.index), color=S3, lw=1.1, label="200-day average")
    ax.yaxis.set_major_formatter(_inr_fmt)
    ax.set_ylabel("Rs")
    _legend(ax, 3)
    last = d["Close"].iloc[-1]
    ax.annotate(f"Rs {fmt_num(last, 1)}", (d.index[-1], last), xytext=(4, 0), textcoords="offset points",
                color=INK, fontsize=8, va="center")
    axv.bar(d.index, d["Volume"] / 1e5, color=NEUTRAL, width=1.0)
    axv.set_ylabel("Vol (lakh)")
    axv.yaxis.set_major_formatter(_inr_fmt)
    _date_axis(axv)
    return _save(fig, path)


def relative_chart(series: list[tuple[str, pd.Series]], path: str) -> str:
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    colors = [S1, S2, S3]
    end = max(s.index[-1] for _, s in series if not s.empty)
    start = end - pd.DateOffset(years=1)
    for (label, s), c in zip(series, colors):
        s = s[s.index >= start].dropna()
        if s.empty:
            continue
        r = s / s.iloc[0] * 100
        ax.plot(r.index, r.values, color=c, lw=1.6 if c == S1 else 1.2, label=label)
        ax.annotate(f"{r.iloc[-1]:.0f}", (r.index[-1], r.iloc[-1]), xytext=(4, 0), textcoords="offset points",
                    color=INK, fontsize=8, va="center")
    ax.axhline(100, color=NEUTRAL, lw=0.8)
    ax.set_ylabel("Rebased to 100")
    _legend(ax, 3)
    _date_axis(ax)
    return _save(fig, path)


def annual_bars(annual: list[dict], path: str, fin: bool) -> str:
    labels = [r["label"] for r in annual]
    rev = [(r.get("revenue") or 0) / CRORE for r in annual]
    pat = [(r.get("pat") or 0) / CRORE for r in annual]
    x = np.arange(len(labels))
    w = 0.36
    fig, ax = plt.subplots(figsize=(6.0, 2.9))
    ax.bar(x - w / 2 - 0.01, rev, w, color=S1, label="Total income" if fin else "Revenue")
    ax.bar(x + w / 2 + 0.01, pat, w, color=S2, label="Net profit")
    for i, (a, b) in enumerate(zip(rev, pat)):
        ax.annotate(fmt_num(a, 0), (i - w / 2, a), xytext=(0, 2), textcoords="offset points", ha="center",
                    fontsize=7, color=INK2)
        ax.annotate(fmt_num(b, 0), (i + w / 2, b), xytext=(0, 2), textcoords="offset points", ha="center",
                    fontsize=7, color=INK2)
    ax.set_xticks(x, labels)
    ax.yaxis.set_major_formatter(_inr_fmt)
    ax.set_ylabel("Rs crore")
    ax.axhline(0, color=NEUTRAL, lw=0.8)
    _legend(ax, 2)
    return _save(fig, path)


def ratio_lines(annual: list[dict], path: str, fin: bool) -> str:
    labels = [r["label"] for r in annual]
    if fin:
        sets = [("Return on equity", "roe", S1), ("Net profit margin", "pat_margin", S2)]
    else:
        sets = [("Return on equity", "roe", S1), ("Return on capital employed", "roce", S2),
                ("EBITDA margin", "ebitda_margin", S3)]
    fig, ax = plt.subplots(figsize=(6.0, 2.9))
    for name, key, c in sets:
        ys = [r.get(key) for r in annual]
        xs = [i for i, y in enumerate(ys) if y is not None]
        yv = [y for y in ys if y is not None]
        if not yv:
            continue
        ax.plot(xs, yv, color=c, lw=2, marker="o", ms=5, mec="white", mew=1.2, label=name)
        ax.annotate(f"{yv[-1]:.1f}%", (xs[-1], yv[-1]), xytext=(5, 0), textcoords="offset points", fontsize=7.5,
                    color=INK, va="center")
    ax.set_xticks(range(len(labels)), labels)
    ax.set_ylabel("Percent")
    ax.set_xlim(-0.3, len(labels) - 0.4)
    _legend(ax, 3)
    return _save(fig, path)


def quarterly_bars(quarters: list[dict], path: str, fin: bool) -> str:
    labels = [q["label"] for q in quarters]
    rev = [(q.get("revenue") or 0) / CRORE for q in quarters]
    pat = [(q.get("pat") or 0) / CRORE for q in quarters]
    x = np.arange(len(labels))
    w = 0.36
    fig, ax = plt.subplots(figsize=(6.0, 2.9))
    ax.bar(x - w / 2 - 0.01, rev, w, color=S1, label="Total income" if fin else "Revenue")
    ax.bar(x + w / 2 + 0.01, pat, w, color=S2, label="Net profit")
    for i, (a, b) in enumerate(zip(rev, pat)):
        ax.annotate(fmt_num(a, 0), (i - w / 2, a), xytext=(0, 2), textcoords="offset points", ha="center",
                    fontsize=7, color=INK2)
        ax.annotate(fmt_num(b, 0), (i + w / 2, b), xytext=(0, 2), textcoords="offset points", ha="center",
                    fontsize=7, color=INK2)
    ax.set_xticks(x, labels)
    ax.yaxis.set_major_formatter(_inr_fmt)
    ax.set_ylabel("Rs crore")
    ax.axhline(0, color=NEUTRAL, lw=0.8)
    _legend(ax, 2)
    return _save(fig, path)


def football_field(val: dict, tech: dict, path: str) -> str:
    cmp = val["cmp"]
    rows: list[tuple[str, float | None, float | None, float | None]] = []  # label, low, high, point
    rows.append(("52-week range", tech.get("low_52w"), tech.get("high_52w"), None))
    c = val["consensus"]
    if c.get("low") and c.get("high"):
        rows.append(("Analyst target range", c["low"], c["high"], c.get("mean")))
    for m in val["methods"]:
        if m["value"]:
            tag = "" if m["included"] else " (excluded)"
            rows.append((m["name"] + tag, None, None, m["value"]))
    if val.get("target"):
        rows.append(("Blended target", None, None, val["target"]))
    rows = rows[::-1]
    fig, ax = plt.subplots(figsize=(10.0, 0.42 * len(rows) + 1.0))
    for i, (label, lo, hi, pt) in enumerate(rows):
        if lo is not None and hi is not None:
            ax.barh(i, hi - lo, left=lo, height=0.42, color="#cde2fb")
            ax.annotate(fmt_num(lo, 0), (lo, i), xytext=(-4, 0), textcoords="offset points", ha="right",
                        va="center", fontsize=7.5, color=INK2)
            ax.annotate(fmt_num(hi, 0), (hi, i), xytext=(4, 0), textcoords="offset points", ha="left",
                        va="center", fontsize=7.5, color=INK2)
        if pt is not None:
            is_target = label == "Blended target"
            ax.plot(pt, i, marker="D" if is_target else "o", ms=9 if is_target else 7,
                    color=S2 if is_target else S1, mec="white", mew=1.2, zorder=3)
            if lo is None:
                ax.annotate(f"Rs {fmt_num(pt, 0)}", (pt, i), xytext=(8, 0), textcoords="offset points",
                            va="center", fontsize=7.5, color=INK)
    ax.axvline(cmp, color=INK, lw=1)
    ax.annotate(f"CMP Rs {fmt_num(cmp, 0)}", (cmp, len(rows) - 0.5), xytext=(4, 0), textcoords="offset points",
                fontsize=7.5, color=INK)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.xaxis.set_major_formatter(_inr_fmt)
    ax.set_xlabel("Rs per share")
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.set_ylim(-0.6, len(rows) - 0.2)
    return _save(fig, path)


def multiple_history(annual: list[dict], current: float | None, path: str, fin: bool) -> str:
    key, label = ("pb", "P/B (x)") if fin else ("pe", "P/E (x)")
    pts = [(r["label"], r.get(key)) for r in annual if r.get(key)]
    fig, ax = plt.subplots(figsize=(6.0, 2.6))
    if pts:
        xs = range(len(pts))
        ax.bar(xs, [p[1] for p in pts], 0.5, color=S1, label=f"FY-end {label.split()[0]}")
        for i, (_, v) in enumerate(pts):
            ax.annotate(f"{v:.1f}x", (i, v), xytext=(0, 2), textcoords="offset points", ha="center", fontsize=7.5,
                        color=INK2)
        ax.set_xticks(list(xs), [p[0] for p in pts])
    if current:
        ax.axhline(current, color=S2, lw=1.6, label=f"Current {current:.1f}x")
    ax.set_ylabel(label)
    _legend(ax, 2)
    return _save(fig, path)


def scorecard_bars(pillars: list[dict], composite: float | None, path: str) -> str:
    items = [p for p in pillars][::-1]
    fig, ax = plt.subplots(figsize=(6.0, 2.7))
    ys = range(len(items))
    vals = [p["score"] if p["score"] is not None else 0 for p in items]
    ax.barh(list(ys), [100] * len(items), height=0.5, color="#f0efec")
    ax.barh(list(ys), vals, height=0.5, color=S1)
    for i, p in enumerate(items):
        txt = f"{p['score']:.0f}" if p["score"] is not None else "n/a"
        ax.annotate(txt, (vals[i], i), xytext=(4, 0), textcoords="offset points", va="center", fontsize=8, color=INK)
    ax.set_yticks(list(ys), [f"{p['pillar']} ({p['weight']}%)" for p in items])
    if composite is not None:
        ax.axvline(composite, color=S2, lw=1.4)
        ax.annotate(f"Composite {composite:.0f}", (composite, len(items) - 0.45), xytext=(4, 0),
                    textcoords="offset points", fontsize=7.5, color=INK)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Score out of 100")
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    return _save(fig, path)


def momentum_chart(close: pd.Series, rsi: pd.Series, macd: pd.DataFrame, path: str) -> str:
    start = close.index[-1] - pd.DateOffset(years=1)
    r = rsi[rsi.index >= start]
    m = macd[macd.index >= start]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 3.4), sharex=True)
    a1.plot(r.index, r.values, color=S1, lw=1.4, label="RSI (14)")
    a1.axhspan(70, 100, color="#f0efec", lw=0)
    a1.axhspan(0, 30, color="#f0efec", lw=0)
    a1.axhline(70, color=NEUTRAL, lw=0.8)
    a1.axhline(30, color=NEUTRAL, lw=0.8)
    a1.set_ylim(10, 90)
    a1.set_ylabel("RSI")
    a1.annotate("70 overbought", (r.index[0], 72), fontsize=7, color=MUTED)
    a1.annotate("30 oversold", (r.index[0], 23), fontsize=7, color=MUTED)
    _legend(a1, 1)
    a2.bar(m.index, m["hist"], color=[S3 if v >= 0 else S2 for v in m["hist"]], width=1.0, label="Histogram")
    a2.plot(m.index, m["macd"], color=S1, lw=1.3, label="MACD")
    a2.plot(m.index, m["signal"], color=S4, lw=1.1, label="Signal")
    a2.axhline(0, color=NEUTRAL, lw=0.8)
    a2.set_ylabel("MACD")
    _legend(a2, 3)
    _date_axis(a2)
    return _save(fig, path)
