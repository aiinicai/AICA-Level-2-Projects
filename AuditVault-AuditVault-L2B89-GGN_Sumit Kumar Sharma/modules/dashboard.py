"""
AuditVault - Role-Based Analytics Dashboard
Provides personalized KPI metric tiles, Plotly visual charts,
overdue item alerts, and quick-access engagement cards for Managers,
Team Members, and Admins.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from sqlalchemy import or_

from models import Engagement, EngagementTeamAssignment, RCMLineItem, IDRItem, User, Client, AuditTrailEntry, Notification
from utils import (
    format_indian_currency, format_indian_number, format_indian_date,
    is_overdue, parse_indian_date
)
from styles import render_kpi_card, render_status_badge

# Plotly support with fallback
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def render_dashboard(db):
    """Render personalized dashboard according to the current user's role."""
    role = st.session_state.get("role")
    user_id = st.session_state.get("user_id")
    user_name = st.session_state.get("name")

    st.markdown(f"## 📊 {role} Workspace Dashboard")
    st.markdown(f"*Welcome back, **{user_name}** | Real-time Engagement Analytics and Vault Monitoring*")
    st.markdown("<hr style='margin: 8px 0 16px 0; border-color: rgba(100,116,139,0.2);'>", unsafe_allow_html=True)

    if role == "Manager":
        render_manager_dashboard(db, user_id)
    elif role == "Team Member":
        render_team_member_dashboard(db, user_id)
    elif role == "Admin":
        render_admin_dashboard(db, user_id)
    else:
        st.info("Please sign in with valid credentials.")


# =====================================================================
# 1. MANAGER DASHBOARD
# =====================================================================

def render_manager_dashboard(db, manager_id: int):
    """
    Manager Dashboard:
    - All engagements created by manager
    - Status counts: Total, In Progress, Under Review, Completed, Overdue
    - Visual analytics (bar chart of status, workload breakdown)
    - Overdue alerts for IDR and engagement deadlines
    - Actionable cards with completion progress
    """
    engagements = db.query(Engagement).filter(Engagement.manager_id == manager_id).all()
    total_eng = len(engagements)

    draft_count = sum(1 for e in engagements if e.status == "Draft")
    in_progress_count = sum(1 for e in engagements if e.status == "In Progress")
    under_review_count = sum(1 for e in engagements if e.status == "Under Review")
    completed_count = sum(1 for e in engagements if e.status == "Completed")

    # Calculate overdue engagements
    overdue_engagements = []
    for e in engagements:
        if e.status != "Completed" and e.deadline:
            overdue_flag, days = is_overdue(e.deadline)
            if overdue_flag:
                overdue_engagements.append((e, days))

    overdue_count = len(overdue_engagements)

    # Overdue IDR items across manager's engagements
    eng_ids = [e.engagement_id for e in engagements]
    overdue_idrs = (
        db.query(IDRItem)
        .filter(IDRItem.engagement_id.in_(eng_ids), IDRItem.status != "Received")
        .all()
    )
    overdue_idr_list = []
    for idr in overdue_idrs:
        if idr.target_date:
            flag, days = is_overdue(idr.target_date)
            if flag:
                overdue_idr_list.append((idr, days))

    # Top KPI Metrics Cards
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(render_kpi_card("Total Engagements", str(total_eng), "Under your management", "blue"), unsafe_allow_html=True)
    with k2:
        st.markdown(render_kpi_card("In Progress", str(in_progress_count), "Fieldwork active", "teal"), unsafe_allow_html=True)
    with k3:
        st.markdown(render_kpi_card("Under Review", str(under_review_count), "Pending sign-off", "gold"), unsafe_allow_html=True)
    with k4:
        st.markdown(render_kpi_card("Completed", str(completed_count), "Consolidated & Vaulted", "green"), unsafe_allow_html=True)
    with k5:
        st.markdown(render_kpi_card("Overdue Alerts", str(overdue_count + len(overdue_idr_list)), "Action required", "red"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Overdue Alerts Section
    if overdue_engagements or overdue_idr_list:
        with st.expander(f"⚠️ **ATTENTION REQUIRED: {len(overdue_engagements) + len(overdue_idr_list)} Overdue Item(s)**", expanded=True):
            for eng, days in overdue_engagements:
                st.error(f"🔴 **Engagement Overdue:** [{eng.engagement_code}] {eng.title} (Client: {eng.client.name}) - Deadline was **{eng.deadline}** ({days} days overdue!)")
            for idr, days in overdue_idr_list:
                st.warning(f"🟡 **IDR Item Overdue:** [{idr.item_code}] {idr.requirement_description[:80]}... - Target Date: **{idr.target_date}** ({days} days overdue)")

    # Visual Analytics Section
    st.markdown("### 📈 Engagement Analytics")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("##### 📌 Engagements by Status")
        status_data = pd.DataFrame({
            "Status": ["Draft", "In Progress", "Under Review", "Completed", "Overdue"],
            "Count": [draft_count, in_progress_count, under_review_count, completed_count, overdue_count]
        })
        if HAS_PLOTLY:
            fig_bar = px.bar(
                status_data,
                x="Status",
                y="Count",
                color="Status",
                color_discrete_map={
                    "Draft": "#64748B",
                    "In Progress": "#2563EB",
                    "Under Review": "#F59E0B",
                    "Completed": "#10B981",
                    "Overdue": "#EF4444"
                },
                text="Count"
            )
            fig_bar.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                height=260,
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.bar_chart(status_data.set_index("Status"))

    with c2:
        st.markdown("##### 👥 Assigned Audit Team Workload")
        assignments = (
            db.query(EngagementTeamAssignment)
            .filter(EngagementTeamAssignment.engagement_id.in_(eng_ids))
            .all()
        )
        workload_map = {}
        for a in assignments:
            auditor_name = a.user.name
            workload_map[auditor_name] = workload_map.get(auditor_name, 0) + 1

        if workload_map:
            df_work = pd.DataFrame(list(workload_map.items()), columns=["Auditor", "Engagements"])
            if HAS_PLOTLY:
                fig_pie = px.pie(
                    df_work,
                    names="Auditor",
                    values="Engagements",
                    hole=0.45,
                    color_discrete_sequence=["#1E3A8A", "#0D9488", "#F59E0B", "#6366F1", "#EC4899"]
                )
                fig_pie.update_layout(
                    margin=dict(l=20, r=20, t=20, b=20),
                    height=260,
                    paper_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.dataframe(df_work, use_container_width=True)
        else:
            st.info("No team members assigned yet. Assign teams from the Engagements module.")

    st.markdown("<hr style='margin: 16px 0; border-color: rgba(100,116,139,0.2);'>", unsafe_allow_html=True)

    # Active Engagements List with Progress Bars
    st.markdown("### 📁 Managed Engagements Overview")
    if not engagements:
        st.info("You have not created any engagements yet. Click **'Engagements'** in the sidebar to create your first engagement.")
        return

    for eng in engagements:
        with st.container():
            # Calculate completion progress based on RCM items
            rcm_items = eng.rcm_items
            total_rcm = len(rcm_items)
            reviewed_rcm = sum(1 for r in rcm_items if r.review_status == "Reviewed" or r.status == "Reviewed")
            progress_pct = int((reviewed_rcm / total_rcm * 100)) if total_rcm > 0 else (100 if eng.status == "Completed" else 0)

            badge_html = render_status_badge(eng.status)
            budget_str = format_indian_currency(eng.estimated_budget)

            col_info, col_prog, col_btn = st.columns([3, 2, 1])
            with col_info:
                st.markdown(f"#### {eng.title}")
                st.markdown(f"**Code:** `{eng.engagement_code}` | **Client:** **{eng.client.name}** | {badge_html}", unsafe_allow_html=True)
                st.caption(f"Process: {eng.process_under_audit} | Period: {eng.audit_period_start} to {eng.audit_period_end} | Budget: {budget_str}")

            with col_prog:
                st.markdown(f"**RCM Completion: {progress_pct}%** ({reviewed_rcm}/{total_rcm} lines reviewed)")
                st.progress(progress_pct / 100.0)
                if eng.deadline:
                    overdue_flag, days = is_overdue(eng.deadline)
                    if overdue_flag and eng.status != "Completed":
                        st.markdown(f"<span style='color: #EF4444; font-weight: 600;'>⚠️ Overdue by {days} days (Deadline: {eng.deadline})</span>", unsafe_allow_html=True)
                    else:
                        st.caption(f"Target Deadline: {eng.deadline}")

            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Open Vault 📂", key=f"mgr_open_{eng.engagement_id}", type="primary"):
                    st.session_state.selected_engagement_id = eng.engagement_id
                    st.session_state.active_page = "Engagement Hub"
                    st.rerun()

            st.markdown("<hr style='margin: 10px 0; border-color: rgba(100,116,139,0.15);'>", unsafe_allow_html=True)


# =====================================================================
# 2. ENGAGEMENT TEAM MEMBER DASHBOARD
# =====================================================================

def render_team_member_dashboard(db, user_id: int):
    """
    Team Member Dashboard:
    - View ONLY engagements assigned to this user
    - Total assigned engagements, open RCM line items, working papers uploaded
    - Dedicated quick-access cards
    """
    # Fetch assigned engagements
    assigned_records = db.query(EngagementTeamAssignment).filter(EngagementTeamAssignment.user_id == user_id).all()
    eng_ids = [a.engagement_id for a in assigned_records]
    
    engagements = db.query(Engagement).filter(Engagement.engagement_id.in_(eng_ids)).all() if eng_ids else []

    # Count assigned RCM items
    assigned_rcm = db.query(RCMLineItem).filter(
        RCMLineItem.engagement_id.in_(eng_ids),
        or_(RCMLineItem.person_responsible_id == user_id, RCMLineItem.person_responsible_id.is_(None))
    ).all() if eng_ids else []

    open_rcm_count = sum(1 for r in assigned_rcm if r.status != "Reviewed" and r.status != "Closed")
    reviewed_rcm_count = sum(1 for r in assigned_rcm if r.status == "Reviewed")

    # Working papers uploaded by this user
    from models import WorkingPaper
    wp_count = db.query(WorkingPaper).filter(WorkingPaper.uploaded_by_id == user_id).count()

    # KPI Metric Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(render_kpi_card("Assigned Audits", str(len(engagements)), "Your active engagements", "blue"), unsafe_allow_html=True)
    with k2:
        st.markdown(render_kpi_card("Open Controls", str(open_rcm_count), "Testing in progress", "gold"), unsafe_allow_html=True)
    with k3:
        st.markdown(render_kpi_card("Reviewed & Passed", str(reviewed_rcm_count), "Manager sign-off", "green"), unsafe_allow_html=True)
    with k4:
        st.markdown(render_kpi_card("Working Papers", str(wp_count), "Uploaded into Vault", "teal"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not engagements:
        st.info("You have not been assigned to any engagements yet. Your Audit Manager will assign you to upcoming audits.")
        return

    st.markdown("### 📋 My Assigned Engagements")
    for eng in engagements:
        with st.container():
            badge_html = render_status_badge(eng.status)
            rcm_items = [r for r in eng.rcm_items if r.person_responsible_id == user_id or r.person_responsible_id is None]
            total_rcm = len(rcm_items)
            done_rcm = sum(1 for r in rcm_items if r.review_status == "Reviewed")
            pct = int(done_rcm / total_rcm * 100) if total_rcm > 0 else 0

            c_info, c_status, c_btn = st.columns([3, 2, 1])
            with c_info:
                st.markdown(f"#### {eng.title}")
                st.markdown(f"**Code:** `{eng.engagement_code}` | **Client:** **{eng.client.name}** | {badge_html}", unsafe_allow_html=True)
                st.caption(f"Manager: {eng.manager.name} | Period: {eng.audit_period_start} to {eng.audit_period_end} | Deadline: {eng.deadline}")

            with c_status:
                st.markdown(f"**Assigned Controls Progress: {pct}%** ({done_rcm}/{total_rcm} signed off)")
                st.progress(pct / 100.0)
                if eng.is_locked:
                    st.markdown("<span style='color: #4F46E5; font-weight: 600;'>🔒 Finalized & Locked by Manager (Read Only)</span>", unsafe_allow_html=True)

            with c_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Enter Fieldwork 📝", key=f"team_open_{eng.engagement_id}", type="primary"):
                    st.session_state.selected_engagement_id = eng.engagement_id
                    st.session_state.active_page = "Engagement Hub"
                    st.rerun()

            st.markdown("<hr style='margin: 10px 0; border-color: rgba(100,116,139,0.15);'>", unsafe_allow_html=True)


# =====================================================================
# 3. ADMIN DASHBOARD
# =====================================================================

def render_admin_dashboard(db, admin_id: int):
    """
    Admin Dashboard:
    - User account counts (Managers, Auditors)
    - Total engagements across the firm
    - Total audit trail events
    - Quick shortcut to User Management and Impersonation
    """
    total_users = db.query(User).count()
    managers_count = db.query(User).filter(User.role == "Manager").count()
    team_count = db.query(User).filter(User.role == "Team Member").count()
    total_engs = db.query(Engagement).count()
    total_clients = db.query(Client).count()
    total_logs = db.query(AuditTrailEntry).count()

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(render_kpi_card("Total Users", str(total_users), f"{managers_count} Mgrs, {team_count} Auditors", "blue"), unsafe_allow_html=True)
    with k2:
        st.markdown(render_kpi_card("Active Clients", str(total_clients), "Corporate & BFSI", "teal"), unsafe_allow_html=True)
    with k3:
        st.markdown(render_kpi_card("Total Engagements", str(total_engs), "Firm-wide audits", "gold"), unsafe_allow_html=True)
    with k4:
        st.markdown(render_kpi_card("Audit Trail Events", str(total_logs), "Immutable records", "green"), unsafe_allow_html=True)
    with k5:
        st.markdown(render_kpi_card("System Health", "100%", "Vault Secure", "teal"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### 🛡️ Administrative Quick Controls")
    c1, c2 = st.columns(2)
    with c1:
        st.info("🔐 **User Accounts & Impersonation:** Manage user credentials, reset passwords, or switch into user accounts for technical support.")
        if st.button("Go to Admin Panel ⚙️", type="primary"):
            st.session_state.active_page = "Admin Panel"
            st.rerun()
    with c2:
        st.info("📜 **Tamper-Proof Audit Trail:** Inspect real-time logs of logins, file modifications, manager overrides, and administrative actions.")
        if st.button("Inspect Audit Trail 🔍"):
            st.session_state.active_page = "Audit Trail"
            st.rerun()
