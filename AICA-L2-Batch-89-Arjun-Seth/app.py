# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""LeaseIQ Pro - entry point (evaluation edition).

Run with:  streamlit run app.py
There is no sign-in: the application opens directly on the Dashboard.
"""
import streamlit as st

from db.database import init_db

st.set_page_config(page_title="LeaseIQ Pro", page_icon="\U0001F4CA")
init_db()  # creates the local database file on the first run
st.switch_page("pages/1_Dashboard.py")
