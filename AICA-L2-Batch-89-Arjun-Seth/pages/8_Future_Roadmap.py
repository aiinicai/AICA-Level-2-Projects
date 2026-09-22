# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Future Enhancements and Developments: the roadmap. A write-up only - nothing on this page is built yet."""
import streamlit as st

from auth_ui import require_login
from core.roadmap import ROADMAP, ROADMAP_INTRO, ROADMAP_TITLE

st.set_page_config(page_title="LeaseIQ Pro - Future Roadmap", page_icon="🧭", layout="wide")
user = require_login()

st.title(ROADMAP_TITLE)
st.caption("(Future Roadmap)")
st.write(ROADMAP_INTRO)

for number, item in enumerate(ROADMAP, start=1):
    with st.container(border=True):
        st.markdown("#### {}. {}".format(number, item["title"]))
        st.write(item["summary"])
        if item["note"]:
            st.caption(item["note"])
        if item["today"]:
            st.markdown("**In this build today:** {}".format(item["today"]))
