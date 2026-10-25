"""
charts.py
=========
Plotly figure builders. Every function takes plain DataFrames / dicts and returns a ``go.Figure``;
no Streamlit code lives here so the charts can be reused in notebooks or reports.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import COLORS, GRADE_BANDS, GRADE_COLORS, PILLAR_WEIGHTS

TEAL, INK, AMBER, PLUM, GREY = COLORS["teal"], COLORS["ink"], "#B45309", "#8B3A62", COLORS["grey"]
RED, GREEN = COLORS["red"], COLORS["green"]
COLORWAY = [TEAL, INK, AMBER, PLUM, GREY]


def _base(fig: go.Figure, title: str, height: int = 340) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, font=dict(size=15)),
        height=height, margin=dict(l=10, r=10, t=50, b=10), colorway=COLORWAY,
        legend=dict(orientation="h", y=-0.18, x=0), hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.25)", zeroline=True, zerolinecolor="rgba(128,128,128,0.4)")
    return fig


def _clean(s: pd.Series) -> pd.Series:
    """inf / -inf (not-meaningful ratios) become gaps in a line instead of breaking the axis."""
    return s.replace([np.inf, -np.inf], np.nan)


def _lines(df: pd.DataFrame, cols: dict, pct: bool = False, suffix: str = "") -> go.Figure:
    fig = go.Figure()
    for col, label in cols.items():
        y = _clean(df[col]) * (100 if pct else 1)
        fig.add_trace(go.Scatter(x=df.index, y=y, name=label, mode="lines+markers",
                                 line=dict(width=2.5), marker=dict(size=8),
                                 hovertemplate=f"%{{y:.2f}}{suffix}"))
    return fig


# --------------------------------------------------------------------------- #
# Tab 1 - trend analysis
# --------------------------------------------------------------------------- #
def revenue_profit_chart(fin: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for col, name in (("revenue", "Revenue"), ("ebitda", "EBITDA"), ("pat", "PAT")):
        fig.add_trace(go.Bar(x=fin.index, y=fin[col], name=name, hovertemplate="₹%{y:,.1f} Cr"))
    fig.update_layout(barmode="group")
    return _base(fig, "Revenue, EBITDA and PAT (₹ Cr)")


def margins_chart(r: pd.DataFrame) -> go.Figure:
    fig = _lines(r, {"ebitda_margin": "EBITDA margin", "opm": "Operating margin (EBIT)", "npm": "Net margin"}, True, "%")
    fig.update_yaxes(ticksuffix="%")
    return _base(fig, "Profitability margins")


def returns_chart(r: pd.DataFrame) -> go.Figure:
    fig = _lines(r, {"roe": "ROE", "roce": "ROCE", "roa": "ROA"}, True, "%")
    fig.update_yaxes(ticksuffix="%")
    return _base(fig, "Return ratios")


def leverage_chart(r: pd.DataFrame, limits, pf: dict) -> go.Figure:
    """Debt/TNW and Debt/EBITDA by year plus the pro-forma (post-loan) point and policy ceilings."""
    fig = _lines(r, {"de": "Debt / TNW", "debt_ebitda": "Debt / EBITDA"}, False, "x")
    x_pf = "Pro-forma"
    for col, val, color in (("de", pf["de"], TEAL), ("debt_ebitda", pf["debt_ebitda"], INK)):
        if np.isfinite(val):
            fig.add_trace(go.Scatter(x=[r.index[-1], x_pf], y=[_clean(r[col]).iloc[-1], val], mode="lines+markers",
                                     line=dict(dash="dot", color=color), marker=dict(symbol="diamond", size=10),
                                     showlegend=False, hovertemplate="%{y:.2f}x"))
    fig.add_hline(y=limits.max_de, line_dash="dash", line_color=TEAL, opacity=0.6,
                  annotation_text=f"D/E limit {limits.max_de:.1f}x", annotation_position="top left")
    fig.add_hline(y=limits.max_debt_ebitda, line_dash="dash", line_color=INK, opacity=0.6,
                  annotation_text=f"Debt/EBITDA limit {limits.max_debt_ebitda:.1f}x", annotation_position="top left")
    return _base(fig, "Leverage trend and pro-forma position (x)")


def coverage_chart(r: pd.DataFrame, limits, pf: dict) -> go.Figure:
    fig = _lines(r, {"icr": "ICR", "dscr": "DSCR"}, False, "x")
    for col, val, color in (("icr", pf["icr"], TEAL), ("dscr", pf["dscr"], INK)):
        if np.isfinite(val):
            fig.add_trace(go.Scatter(x=[r.index[-1], "Pro-forma"], y=[_clean(r[col]).iloc[-1], val],
                                     mode="lines+markers", line=dict(dash="dot", color=color),
                                     marker=dict(symbol="diamond", size=10), showlegend=False,
                                     hovertemplate="%{y:.2f}x"))
    fig.add_hline(y=limits.min_dscr, line_dash="dash", line_color=INK, opacity=0.6,
                  annotation_text=f"Min DSCR {limits.min_dscr:.2f}x", annotation_position="bottom left")
    fig.add_hline(y=limits.min_icr, line_dash="dash", line_color=TEAL, opacity=0.6,
                  annotation_text=f"Min ICR {limits.min_icr:.1f}x", annotation_position="top left")
    return _base(fig, "Coverage trend and pro-forma position (x)")


def working_capital_chart(r: pd.DataFrame) -> go.Figure:
    fig = _lines(r, {"dso": "Debtor days", "dio": "Inventory days", "dpo": "Creditor days", "ccc": "Cash conversion cycle"})
    return _base(fig, "Working-capital cycle (days)")


def cashflow_chart(fin: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for col, name in (("cfo", "Operating cash flow"), ("capex", "Capex"), ("fcf", "Free cash flow")):
        fig.add_trace(go.Bar(x=fin.index, y=fin[col], name=name, hovertemplate="₹%{y:,.1f} Cr"))
    fig.update_layout(barmode="group")
    return _base(fig, "Cash generation vs capex (₹ Cr)")


# --------------------------------------------------------------------------- #
# Tab 3 - debt & exposure
# --------------------------------------------------------------------------- #
def lender_donut(by_lender: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Pie(labels=by_lender.index, values=by_lender["Outstanding"], hole=0.55, sort=False,
                           marker=dict(colors=[TEAL, INK, AMBER, PLUM, GREY, "#4B9CA8", "#A78BFA", "#94A3B8"]),
                           hovertemplate="%{label}: ₹%{value:,.1f} Cr (%{percent})<extra></extra>"))
    fig.update_layout(showlegend=True, legend=dict(orientation="v", x=1.0))
    return _base(fig, "Outstanding debt by lender", 340)


def facility_bar(by_type: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=by_type.index, y=by_type["Sanctioned Limit"], name="Sanctioned"))
    fig.add_trace(go.Bar(x=by_type.index, y=by_type["Outstanding"], name="Outstanding"))
    fig.update_layout(barmode="group")
    return _base(fig, "Facility type: sanctioned vs outstanding (₹ Cr)", 340)


def pro_forma_chart(now: dict, pf: dict, limits) -> go.Figure:
    metrics = [("de", "Debt / TNW", limits.max_de, "max"), ("debt_ebitda", "Debt / EBITDA", limits.max_debt_ebitda, "max"),
               ("icr", "ICR", limits.min_icr, "min"), ("dscr", "DSCR", limits.min_dscr, "min")]
    fig = make_subplots(rows=1, cols=4, subplot_titles=[m[1] for m in metrics])
    for i, (k, _, lim, kind) in enumerate(metrics, start=1):
        vals = [now[k], pf[k]]
        vals = [v if np.isfinite(v) else 0 for v in vals]
        ok = (pf[k] <= lim) if kind == "max" else (pf[k] >= lim)
        fig.add_trace(go.Bar(x=["Current", "Pro-forma"], y=vals, marker_color=[GREY, GREEN if ok else RED],
                             showlegend=False, hovertemplate="%{y:.2f}x"), row=1, col=i)
        fig.add_hline(y=lim, line_dash="dash", line_color=INK, row=1, col=i,
                      annotation_text=f"{'max' if kind == 'max' else 'min'} {lim:.2f}x", annotation_position="top left")
    return _base(fig, "Before vs after the proposed facility (policy limit dashed)", 330)


def repayment_chart(sched: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=sched.index, y=sched["Principal"], name="Principal"))
    fig.add_trace(go.Bar(x=sched.index, y=sched["Interest"], name="Interest"))
    fig.add_trace(go.Scatter(x=sched.index, y=sched["Closing"], name="Closing balance", mode="lines+markers",
                             line=dict(color=AMBER, width=2)))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="Year of facility", dtick=1)
    return _base(fig, "Proposed facility: repayment profile (₹ Cr)", 330)


# --------------------------------------------------------------------------- #
# Tab 4 - scorecard
# --------------------------------------------------------------------------- #
def score_gauge(score: float, grade: str) -> go.Figure:
    steps = []
    bands = sorted(GRADE_BANDS, key=lambda b: b[0])
    for i, (floor, g, _) in enumerate(bands):
        top = bands[i + 1][0] if i + 1 < len(bands) else 100
        steps.append(dict(range=[floor, top], color=GRADE_COLORS[g], line=dict(width=0)))
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score, number=dict(suffix=" / 100", font=dict(size=30)),
        title=dict(text=f"Composite score - Grade {grade}", font=dict(size=15)),
        gauge=dict(axis=dict(range=[0, 100]), bar=dict(color="rgba(0,0,0,0.85)", thickness=0.25),
                   steps=[{**s, "color": s["color"] + "66"} for s in steps])))
    fig.update_layout(height=270, margin=dict(l=20, r=20, t=60, b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def pillar_chart(pillar_scores: dict) -> go.Figure:
    names = list(pillar_scores.keys())
    vals = [pillar_scores[n] for n in names]
    labels = [f"{n} ({PILLAR_WEIGHTS[n] * 100:.0f}%)" for n in names]
    colors = [GREEN if v >= 65 else AMBER if v >= 40 else RED for v in vals]
    fig = go.Figure(go.Bar(x=vals, y=labels, orientation="h", marker_color=colors, text=[f"{v:.0f}" for v in vals],
                           textposition="outside", hovertemplate="%{x:.0f} / 100"))
    fig.update_xaxes(range=[0, 110])
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(hovermode="closest")
    return _base(fig, "Pillar scores (weight)", 270)
