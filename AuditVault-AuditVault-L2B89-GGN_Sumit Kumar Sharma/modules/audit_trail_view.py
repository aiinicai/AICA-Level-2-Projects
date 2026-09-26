"""
AuditVault - Immutable Audit Trail Viewer (Manager & Admin Only)
Tamper-proof, append-only chronological log of all system activities,
including logins, edits, uploads, manager locks, reopenings, and admin impersonations.
"""

import io
import pandas as pd
import streamlit as st

from models import AuditTrailEntry, User
from auth import is_manager, is_admin


def render_audit_trail_page(db):
    """Render the immutable audit trail interface."""
    # Enforce permission check: Visible to Manager and Admin only
    if not (is_manager() or is_admin()):
        st.error("⛔ Access Denied. The Audit Trail is restricted to Audit Managers and Administrators.")
        return

    st.markdown("## 📜 Immutable Audit Trail")
    st.markdown("*Non-editable chronological log of all user activities, security events, and engagement modifications.*")
    st.markdown("<hr style='margin: 8px 0 16px 0; border-color: rgba(100,116,139,0.2);'>", unsafe_allow_html=True)

    # Filter Bar
    c_search, c_act, c_user = st.columns([2, 2, 2])
    with c_search:
        search_kw = st.text_input("🔍 Search Description / Target", placeholder="Filter by keyword or code...").strip().lower()

    with c_act:
        action_types = [
            "ALL", "LOGIN", "LOGOUT", "IMPERSONATE", "EXIT_IMPERSONATION",
            "CREATE_ENGAGEMENT", "TEAM_ASSIGNMENT", "IDR_UPLOAD", "EDIT_IDR",
            "RCM_UPLOAD", "EDIT_RCM_LINE", "FINALIZE_RCM", "UPLOAD_WORKING_PAPER",
            "RECORD_OBSERVATION", "REVIEW_LINE_ITEM", "COMPLETE_AUDIT",
            "REOPEN_ENGAGEMENT", "PASSWORD_RESET"
        ]
        selected_action = st.selectbox("Action Type", action_types)

    with c_user:
        all_users = db.query(User).all()
        user_names = ["ALL"] + sorted([u.name for u in all_users])
        selected_user = st.selectbox("Acting User", user_names)

    # Query from append-only table
    query = db.query(AuditTrailEntry)
    if selected_action != "ALL":
        query = query.filter(AuditTrailEntry.action_type == selected_action)
    if selected_user != "ALL":
        query = query.filter(AuditTrailEntry.acting_user_name == selected_user)

    entries = query.order_by(AuditTrailEntry.id.desc()).all()

    # Search filter
    filtered_entries = []
    for e in entries:
        if search_kw:
            comb = f"{e.description} {e.target_entity} {e.target_id} {e.action_type}".lower()
            if search_kw not in comb:
                continue
        filtered_entries.append(e)

    # Metric & Export Bar
    c_count, c_exp = st.columns([4, 2])
    c_count.markdown(f"**Total Audit Records: `{len(filtered_entries)}`** (Showing latest first)")

    with c_exp:
        if filtered_entries:
            csv_data = generate_audit_csv(filtered_entries)
            st.download_button(
                label="📥 Export Audit Trail (CSV)",
                data=csv_data,
                file_name="AuditVault_AuditTrail_Log.csv",
                mime="text/csv"
            )

    st.markdown("<br>", unsafe_allow_html=True)

    if not filtered_entries:
        st.info("No audit trail entries match your filter criteria.")
        return

    # Render entries in a clean, professional timeline table
    table_rows = []
    for e in filtered_entries:
        admin_note = f" (Real Admin: {e.true_admin_name})" if e.true_admin_name else ""
        table_rows.append({
            "Log ID": f"#{e.id:04d}",
            "Timestamp (DD-MM-YYYY)": e.timestamp_str,
            "Action": e.action_type,
            "Target Entity": f"{e.target_entity} [{e.target_id}]" if e.target_id else e.target_entity,
            "Acting User": f"{e.acting_user_name}{admin_note}",
            "Audit Description": e.description
        })

    df_audit = pd.DataFrame(table_rows)

    # Highlight impersonation in the UI
    st.dataframe(
        df_audit,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Log ID": st.column_config.TextColumn("Log ID", width="small"),
            "Timestamp (DD-MM-YYYY)": st.column_config.TextColumn("Timestamp", width="medium"),
            "Action": st.column_config.TextColumn("Event Type", width="medium"),
            "Acting User": st.column_config.TextColumn("User Identity", width="medium"),
            "Audit Description": st.column_config.TextColumn("Action Details", width="large"),
        }
    )

    st.markdown("<hr style='margin: 16px 0; border-color: rgba(100,116,139,0.2);'>", unsafe_allow_html=True)
    st.caption("🔒 **Security Assurance:** The AuditVault audit trail is append-only and cryptographically bound. Records are immutable and cannot be purged or altered by any account.")


def generate_audit_csv(entries) -> bytes:
    """Generate CSV bytes for download."""
    records = []
    for e in entries:
        records.append({
            "Log_ID": e.id,
            "Timestamp": e.timestamp_str,
            "Action_Type": e.action_type,
            "Target_Entity": e.target_entity,
            "Target_ID": e.target_id,
            "Acting_User": e.acting_user_name,
            "True_Admin_ID": e.true_admin_id or "",
            "True_Admin_Name": e.true_admin_name or "",
            "Description": e.description,
            "IP_Address": e.ip_address
        })
    df = pd.DataFrame(records)
    return df.to_csv(index=False).encode("utf-8")
