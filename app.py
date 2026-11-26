"""
AI CFO Enterprise Platform - premium executive dashboard, multi-agent AI CFO, RAG, OCR, predictive cash analytics and board reporting.
Run:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="AI CFO Enterprise Platform", page_icon="■", layout="wide", initial_sidebar_state="expanded")

from ui import theme  # noqa: E402
from ui.common import ai_cfg, ensure_review, get_world  # noqa: E402
from views import ai_cfo, cash, dashboard, documents, knowledge, reports, settings, statements, units, working_capital  # noqa: E402

PAGES = {
    "Executive Dashboard": dashboard, "Business Units": units, "Financial Statements": statements, "Working Capital": working_capital,
    "Cash & Scenarios": cash, "AI CFO": ai_cfo, "Policy Knowledge (RAG)": knowledge, "Document Intelligence (OCR)": documents,
    "Board Pack & Reports": reports, "Data & Settings": settings,
}


def main():
    theme.inject()
    with st.sidebar:
        st.markdown('<div class="brand"><div class="t1">AI CFO Enterprise Platform</div><div class="t2">Virtual CFO &middot; Decision support</div></div>', unsafe_allow_html=True)
        page = st.radio("Navigation", list(PAGES), label_visibility="collapsed", key="nav")
        st.markdown("---")
    world, msgs = get_world()
    with st.sidebar:
        if world is not None:
            st.markdown(f"**{world.fm.company}**")
            st.caption(f"Period: {world.period:%B %Y}  |  AI: {ai_cfg().mode}")
        for w in (msgs or {}).get("warnings", [])[:3]:
            st.caption("Note: " + w)
    if world is None:
        theme.hero("AI CFO Enterprise Platform", "Load data to begin", [])
        for e in msgs.get("errors", []):
            st.error(e)
        settings.render(None, None)
        return
    if page == "Data & Settings":
        settings.render(world, None)
        return
    review = ensure_review(world)
    PAGES[page].render(world, review)


main()
