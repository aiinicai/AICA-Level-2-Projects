# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Audit Log page (shows the status transitions and the other logged events)."""
import pandas as pd
import streamlit as st

from auth_ui import require_login
from core.workflow import get_user_audit_log
from db.database import get_session

st.set_page_config(page_title="LeaseIQ Pro - Audit Log", page_icon="🧾", layout="wide")
user = require_login("audit")

st.title("Audit Log")

with get_session() as session:
    rows = get_user_audit_log(session, user["user_id"])  # only THIS user's events

if not rows:
    st.info("No audit events yet.")
else:
    frame = pd.DataFrame(rows)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"]).dt.strftime("%d-%b-%Y %H:%M:%S")
    frame = frame.rename(
        columns={
            "timestamp": "Time (UTC)",
            "lease_ref": "Lease",
            "user_email": "User",
            "action": "Action",
            "field_name": "Field",
            "old_value": "From",
            "new_value": "To",
            "details": "Details",
        }
    )
    edited = frame["Action"] == "Field edited"
    for column in ("From", "To"):  # an edited field that was empty shows "(empty)"; other rows just stay blank
        frame[column] = [
            "(empty)" if (is_edit and pd.isna(value)) else ("" if pd.isna(value) else value)
            for is_edit, value in zip(edited, frame[column])
        ]
    frame = frame.fillna("")
    st.dataframe(
        frame[["Time (UTC)", "Lease", "User", "Action", "Field", "From", "To", "Details"]],
        hide_index=True,
        column_config={"Details": st.column_config.TextColumn("Details", width="large")},
    )
