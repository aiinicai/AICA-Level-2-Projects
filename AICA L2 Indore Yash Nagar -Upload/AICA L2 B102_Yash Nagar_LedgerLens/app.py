"""LedgerLens: entry point. Run with:  python -m streamlit run app.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from ui import theme  # noqa: E402

st.set_page_config(page_title=theme.APP_NAME, page_icon="\U0001f50d", layout="wide", initial_sidebar_state="expanded")
theme.inject_css()
st.logo(str(ROOT / "ui" / "logo.svg"), size="large")

pages = {
    "": [st.Page("ui/home.py", title="Home", icon=":material/home:", default=True)],
    "Tools": [
        st.Page("ui/statements.py", title="Financial Statements Builder", icon=":material/description:", url_path="statements"),
        st.Page("ui/day_book.py", title="Day Book Audit", icon=":material/fact_check:", url_path="day-book"),
    ],
    "Setup": [st.Page("ui/settings.py", title="Settings & AI", icon=":material/tune:", url_path="settings")],
}
st.navigation(pages).run()
