"""Legal footer and fair-use banner."""
from __future__ import annotations

import json

import streamlit as st

from config.icai_resources import CITATION_METADATA, FAIR_USE_NOTICE


def render_fair_use_banner() -> None:
    st.markdown(f"<div class='fair-use'>{FAIR_USE_NOTICE}</div>", unsafe_allow_html=True)


def render_citation_expander() -> None:
    with st.expander("Structured citation metadata"):
        st.json(CITATION_METADATA)
        st.download_button("Download citation JSON", json.dumps(CITATION_METADATA, indent=2),
                           file_name="icai_citation_metadata.json", mime="application/json")


def render_footer() -> None:
    st.markdown("---")
    render_fair_use_banner()
    render_citation_expander()
