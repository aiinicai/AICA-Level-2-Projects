"""100-mark visual progress dashboard with Plotly gauge."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from config.icai_resources import CHAPTERS, MODULES, TOTAL_MARKS


def earned_marks(done: dict[str, bool]) -> float:
    return round(sum(c.marks for c in CHAPTERS if done.get(c.chapter_id)), 1)


def zone_label(marks: float) -> str:
    if marks < 40:
        return "Red zone (below pass mark)"
    if marks < 60:
        return "Amber zone (passing threshold reached)"
    return "Green zone (exemption target)"


def build_gauge(marks: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=marks, number={"suffix": " / 100", "font": {"color": "#0F172A"}},
        title={"text": "Syllabus coverage (marks)", "font": {"color": "#0F172A"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#0F172A"},
            "bar": {"color": "#0F172A"},
            "steps": [
                {"range": [0, 40], "color": "#FCA5A5"},
                {"range": [40, 60], "color": "#FCD34D"},
                {"range": [60, 100], "color": "#86EFAC"},
            ],
            "threshold": {"line": {"color": "#0284C7", "width": 4}, "thickness": 0.8, "value": marks},
        },
    ))
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=60, b=10), paper_bgcolor="#FFFFFF")
    return fig


def render_dashboard() -> None:
    st.subheader("100-Mark Visual Progress Dashboard")
    st.caption("Tick chapters you have completed. Marks are an indicative teaching allocation that sums to 100.0.")
    done: dict[str, bool] = {}
    cols = st.columns(2)
    for i, m in enumerate(MODULES):
        with cols[i % 2]:
            st.markdown(f"**{m.name}** ({m.avg_marks:.1f} M)")
            for c in (c for c in CHAPTERS if c.module_id == m.module_id):
                done[c.chapter_id] = st.checkbox(f"{c.name} ({c.marks:.1f} M)", key=f"chk_{c.chapter_id}")
    marks = earned_marks(done)
    st.plotly_chart(build_gauge(marks), use_container_width=True)
    st.metric("Marks covered", f"{marks:.1f} / {TOTAL_MARKS:.1f}", help=zone_label(marks))
    st.write(zone_label(marks))
    st.caption("Red 0-39 | Amber 40-59 (passing threshold) | Green 60-100 (exemption target). "
               "Coverage is not the same as exam performance.")
