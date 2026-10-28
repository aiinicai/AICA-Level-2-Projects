"""Shared look and small UI helpers for every page."""
from __future__ import annotations

import streamlit as st

APP_NAME = "LedgerLens"
TAGLINE = "Tally books in. Reviewed Schedule III statements out."

CSS = """
<style>
:root { --ll-primary:#0F766E; --ll-ink:#0F172A; --ll-muted:#64748B; --ll-line:#E2E8F0; --ll-soft:#F1F5F9; }
.block-container { padding-top: 2.2rem; max-width: 1280px; }
h1, h2, h3 { letter-spacing: -0.01em; color: var(--ll-ink); }
h2 { margin-top: 1.6rem; }
[data-testid="stMetric"] { background:#F8FAFC; border:1px solid var(--ll-line); padding:12px 16px; border-radius:12px; }
[data-testid="stMetricLabel"] p { color: var(--ll-muted); font-size: .82rem; }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] > div, [data-testid="stMetricLabel"] p,
[data-testid="stMetricValue"], [data-testid="stMetricValue"] > div, [data-testid="stMetricValue"] p { white-space: normal !important; overflow: visible !important;
  text-overflow: clip !important; overflow-wrap: break-word; word-break: normal; hyphens: none; line-height: 1.2; }
[data-testid="stMetricValue"] { font-size: 1.4rem; }
[data-testid="stSidebar"] { border-right: 1px solid var(--ll-line); }
.stDeployButton { display:none; }
div[data-testid="stExpander"] { border:1px solid var(--ll-line); border-radius:12px; }
.ll-hero { background: linear-gradient(135deg,#0F766E 0%,#134E4A 100%); color:#fff; padding:34px 38px; border-radius:18px; margin-bottom:22px; }
.ll-hero h1 { color:#fff; font-size:2.5rem; margin:0 0 4px 0; }
.ll-hero p { color:#CCFBF1; font-size:1.12rem; margin:0; }
.ll-chip { display:inline-block; background:rgba(255,255,255,.14); color:#fff; padding:4px 12px; border-radius:999px; font-size:.82rem; margin:14px 8px 0 0; }
.ll-card { border:1px solid var(--ll-line); border-radius:14px; padding:18px 20px 8px 20px; background:#fff; min-height:285px; }
.ll-card h3 { margin:0 0 6px 0; font-size:1.15rem; }
.ll-card p { color:#334155; font-size:.93rem; }
.ll-steps { display:flex; gap:8px; flex-wrap:wrap; margin:4px 0 14px 0; }
.ll-step { padding:5px 13px; border-radius:999px; font-size:.82rem; border:1px solid var(--ll-line); background:#fff; color:var(--ll-muted); }
.ll-step.done { background:#ECFDF5; border-color:#A7F3D0; color:#065F46; }
.ll-step.warn { background:#FFFBEB; border-color:#FDE68A; color:#92400E; }
.ll-step.now { background:#F0FDFA; border-color:#5EEAD4; color:#0F766E; font-weight:600; }
.ll-badge { display:inline-block; padding:3px 11px; border-radius:999px; font-size:.8rem; }
.ll-badge.on { background:#ECFDF5; color:#065F46; border:1px solid #A7F3D0; }
.ll-badge.off { background:#F1F5F9; color:#475569; border:1px solid #CBD5E1; }
.ll-sub { color:var(--ll-muted); margin-top:-6px; margin-bottom:10px; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def header(title: str, subtitle: str, icon: str = "") -> None:
    st.title(f"{icon} {title}".strip())
    st.markdown(f"<div class='ll-sub'>{subtitle}</div>", unsafe_allow_html=True)


TICK, WARN = "✓ ", "⚠ "


def stepper(steps: list[tuple[str, str]]) -> None:
    """steps: (label, state) with state done | warn | now | todo."""
    marks = {"done": TICK, "warn": WARN}
    chips = "".join(f"<span class='ll-step {state}'>{marks.get(state, '')}{i}. {label}</span>"
                    for i, (label, state) in enumerate(steps, start=1))
    st.markdown(f"<div class='ll-steps'>{chips}</div>", unsafe_allow_html=True)


def safe_link(path: str, label: str, icon: str | None = None) -> None:
    """A link to another page. Falls back to plain text when the page is not registered (a page run on its own)."""
    try:
        st.page_link(path, label=label, icon=icon)
    except Exception:
        st.caption(label)
