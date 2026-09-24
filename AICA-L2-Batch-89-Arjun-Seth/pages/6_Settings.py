# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Settings page: appearance (theme and dashboard layout) and display preferences."""
import streamlit as st

from auth_ui import require_login, set_flash, show_flash
from core.formatting import CURRENCY_CODES, NUMBER_FORMATS, currency_label, format_money
from core.themes import LAYOUTS, THEMES
from core.workflow import save_user_preferences
from db.database import get_session
from theme_css import layout_preview_html

st.set_page_config(page_title="LeaseIQ Pro - Settings", page_icon="\u2699\ufe0f", layout="wide")
user = require_login()

st.title("Settings")
show_flash()
st.info("Evaluation edition: the application opens directly as a built-in Evaluator profile, so there is no sign-in and no password to manage.")

# ------------------------------- appearance -------------------------------- #
st.subheader("Appearance")
theme_keys, layout_keys = list(THEMES), list(LAYOUTS)
theme = st.radio(
    "Theme",
    theme_keys,
    index=theme_keys.index(user["theme"]) if user.get("theme") in theme_keys else 0,
    format_func=THEMES.get,
    horizontal=True,
    key="pref_theme",
)
dashboard_layout = st.radio(
    "Dashboard layout",
    layout_keys,
    index=layout_keys.index(user["dashboard_layout"]) if user.get("dashboard_layout") in layout_keys else 0,
    format_func=lambda key: LAYOUTS[key]["label"],
    horizontal=True,
    key="pref_layout",
)
st.caption("The previews below show each layout in the theme you picked. Press 'Save preferences' to apply your choice everywhere.")
for column, key in zip(st.columns(3), layout_keys):
    with column:
        st.markdown(layout_preview_html(key, theme, selected=key == dashboard_layout), unsafe_allow_html=True)
        st.caption(LAYOUTS[key]["description"])

# ---------------------------- display preferences --------------------------- #
st.subheader("Display preferences")
formats = list(NUMBER_FORMATS)
number_format = st.radio(
    "Number format",
    formats,
    index=formats.index(user["number_format"]) if user["number_format"] in formats else 0,
    format_func=lambda key: NUMBER_FORMATS[key],
    key="pref_number_format",
)
default_currency = st.selectbox(
    "Default currency",
    CURRENCY_CODES,
    index=CURRENCY_CODES.index(user["default_currency"]) if user["default_currency"] in CURRENCY_CODES else 0,
    format_func=currency_label,
    key="pref_default_currency",
)
st.caption(
    "Preview: {}  (a lease liability of 5079693.73 shown in this format and currency)".format(
        format_money(5079693.73, default_currency, number_format)
    )
)
st.caption(
    "The number format changes how amounts are SHOWN everywhere; it never changes a calculation. "
    "The default currency is pre-selected when a lease document or bulk file does not state one. "
    "Each lease keeps its own currency (you choose it when you validate the lease), and amounts are "
    "never converted from one currency to another."
)
if st.button("Save preferences", key="save_preferences", type="primary"):
    try:
        with get_session() as session:
            save_user_preferences(session, user["user_id"], number_format, default_currency, theme, dashboard_layout)
    except ValueError as exc:
        st.error(str(exc))
    else:
        set_flash("success", "Preferences saved.")
        st.rerun()
