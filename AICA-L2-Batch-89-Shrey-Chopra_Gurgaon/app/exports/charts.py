"""
charts.py
---------
Shared chart-generation helpers for the Excel and PDF exports: a
variance "bridge" (waterfall) chart walking from the prior-period total
to the current-period total by entity, and a severity-distribution bar
chart. Rendered once with matplotlib and embedded as PNG images so both
export formats show the identical, presentation-grade chart a Big 4
close-review deck would use.

Kept UI-agnostic on purpose — no Flask, no openpyxl/reportlab imports —
so it can be unit tested or reused standalone.
"""

from __future__ import annotations

import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

NAVY = "#14213D"
NAVY_LIGHT = "#1F335A"
GOLD = "#C9A227"
GREEN = "#1E7A46"
RED = "#B00020"
GREY = "#8FA0B3"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "#D6DBE2",
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "grid.color": "#E3E6EA",
    "grid.linewidth": 0.6,
    "axes.axisbelow": True,
})


def _fig_to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def _fmt_compact(x, _pos=None):
    ax = abs(x)
    if ax >= 1_000_000:
        return f"${x/1_000_000:,.1f}M"
    if ax >= 1_000:
        return f"${x/1_000:,.0f}K"
    return f"${x:,.0f}"


def _wrap_label(name: str, width: int = 14) -> str:
    import textwrap
    return "\n".join(textwrap.wrap(name, width=width, max_lines=2, placeholder="…"))


def waterfall_chart(entity_deltas: dict, prior_total: float, current_total: float, title: str = "Net Variance Bridge") -> bytes:
    """entity_deltas: {entity_name: net_variance_usd}, ordered as given."""
    labels = ["Prior\nTotal"] + [_wrap_label(k) for k in entity_deltas.keys()] + ["Current\nTotal"]
    n = len(labels)

    fig, ax = plt.subplots(figsize=(max(7.5, n * 1.55), 4.3))

    cumulative = prior_total
    bottoms = [0.0]
    heights = [prior_total]
    colors = [NAVY]

    for delta in entity_deltas.values():
        if delta >= 0:
            bottoms.append(cumulative)
            heights.append(delta)
            colors.append(GREEN)
        else:
            bottoms.append(cumulative + delta)
            heights.append(-delta)
            colors.append(RED)
        cumulative += delta

    bottoms.append(0.0)
    heights.append(current_total)
    colors.append(NAVY_LIGHT)

    x = range(n)
    bars = ax.bar(x, heights, bottom=bottoms, color=colors, width=0.62, zorder=3, edgecolor="white", linewidth=0.5)

    # Connector lines between bars for the classic bridge look
    running = prior_total
    for i, delta in enumerate(entity_deltas.values(), start=1):
        ax.plot([i - 0.5 + 0.31, i + 0.5 - 0.31], [running, running], color="#B7BFC9", linewidth=0.9, zorder=2)
        running += delta

    for i, (h, b) in enumerate(zip(heights, bottoms)):
        val = h if i in (0, n - 1) else (h if colors[i] == GREEN else -h)
        ax.text(i, b + h + (max(heights) * 0.02 if h >= 0 else -max(heights) * 0.02),
                _fmt_compact(val), ha="center",
                va="bottom" if colors[i] != RED or i in (0, n - 1) else "top",
                fontsize=8.5, fontweight="bold", color="#14213D")

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8, linespacing=1.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_compact))
    ax.set_title(title, fontsize=12, fontweight="bold", color=NAVY, loc="left", pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.margins(y=0.22)
    ax.tick_params(axis="x", pad=6)
    fig.tight_layout()
    return _fig_to_png(fig)


def severity_bar_chart(counts: dict, title: str = "Flagged Lines by Severity") -> bytes:
    """counts: {'high': n, 'elevated': n, 'standard': n} in display order."""
    sev_colors = {"high": "#F8696B", "elevated": "#FFC96B", "standard": "#B7BFC9"}
    labels = [k.capitalize() for k in counts.keys()]
    values = list(counts.values())
    colors = [sev_colors.get(k, GREY) for k in counts.keys()]

    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    bars = ax.barh(labels, values, color=colors, zorder=3, height=0.55)
    for bar, v in zip(bars, values):
        ax.text(bar.get_width() + max(values + [1]) * 0.02, bar.get_y() + bar.get_height() / 2,
                str(v), va="center", fontsize=9.5, fontweight="bold", color=NAVY)
    ax.set_title(title, fontsize=11.5, fontweight="bold", color=NAVY, loc="left", pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.set_xticks([])
    ax.invert_yaxis()
    fig.tight_layout()
    return _fig_to_png(fig)


def entity_totals(rows) -> tuple[dict, float, float]:
    """rows: iterable of dicts with entity/prior_amount/current_amount.
    Returns (deltas_by_entity, prior_total, current_total)."""
    by_entity = {}
    for d in rows:
        e = d["entity"]
        by_entity.setdefault(e, {"prior": 0.0, "current": 0.0})
        by_entity[e]["prior"] += d["prior_amount"]
        by_entity[e]["current"] += d["current_amount"]
    deltas = {e: v["current"] - v["prior"] for e, v in by_entity.items()}
    prior_total = sum(v["prior"] for v in by_entity.values())
    current_total = sum(v["current"] for v in by_entity.values())
    return deltas, prior_total, current_total


def severity_counts(rows) -> dict:
    counts = {"high": 0, "elevated": 0, "standard": 0}
    for d in rows:
        sev = d.get("severity")
        if sev in counts:
            counts[sev] += 1
    return counts
