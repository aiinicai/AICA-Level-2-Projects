"""Custom CSS injection - deliberately minimal, deliberately verified.

.streamlit/config.toml's native theming has exactly one interactive-
color slot (primaryColor) and no separate "accent" slot, so the
Electric Teal half of the "Midnight + Electric Teal" palette can't be
expressed through config.toml alone. Rather than inject a broad CSS
override across many Streamlit sub-elements (fragile across versions,
and impossible to visually verify pixel-by-pixel in this environment),
this applies teal to exactly ONE well-defined, stable touch point:
st.metric()'s value text, via the `stMetricValue` data-testid.

That selector was confirmed to actually exist in the pinned
streamlit==1.41.1 frontend bundle (grepped directly from the installed
package's static JS, not assumed from general Streamlit documentation
which may drift across versions) before being used here.
"""

from __future__ import annotations

import streamlit as st

ELECTRIC_TEAL = "#00A6A6"

_CSS = f"""
<style>
[data-testid="stMetricValue"] {{
    color: {ELECTRIC_TEAL};
}}
</style>
"""


def inject_accent_css() -> None:
    """Call once per page render to apply the Electric Teal accent to
    every st.metric() value on the page."""
    st.markdown(_CSS, unsafe_allow_html=True)
