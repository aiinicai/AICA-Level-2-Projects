"""
AuditVault - Engagements Management Module
Create new engagements with Indian date format support, flexible 8-digit date auto-parsing,
Engagement Letter upload, team assignment, and role-based access filtering.
"""

import streamlit as st
from datetime import datetime, date
from pathlib import Path

from models import Engagement, Client, Team, TeamMemberMapping, EngagementTeamAssignment, User
from utils import (
    format_indian_date, parse_indian_date, normalize_indian_date_input,
    format_indian_currency, format_indian_number, current_indian_date_str,
    get_engagement_letter_dir, save_uploaded_file, log_audit_action, is_overdue
)
from styles import render_status_badge, render_kpi_card
from auth import is_manager, is_admin, is_team_member


def render_engagements_page(db):
    """Main entry point for Engagements management."""
    role = st.session_state.get("role")
    user_id = st.session_state.get("user_id")

    st.markdown("## 📁 Audit Engagements Workspace")
    st.markdown("*Create, track, and administer end-to-end audit lifecycles.*")
    st.markdown("<hr style='margin: 8px 0 16px 0; border-color: rgba(100,116,139,0.2);'>", unsafe_allow_html=True)

    # Top action bar: New Engagement (Manager only)
    c_search, c_filter, c_btn = st.columns([3, 2, 2])
    with c_search:
        search_query = st.text_input("🔍 Search engagements", placeholder="Search by Client, Title, or Code...").strip().lower()
    with c_filter:
        status_filter = st.selectbox(
            "Status Filter",
            ["All", "Draft", "Assigned", "In Progress", "Under Review", "Completed"]
        )
    with c_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        show_create_modal = False
        if is_manager():
            if st.button("➕ New Engagement", type="primary"):
                st.session_state.show_create_engagement = True

    # Engagement Creation Form Section
    if st.session_state.get("show_create_engagement", False) and is_manager():
        render_create_engagement_form(db, user_id)

    # Query engagements based on role
    query = db.query(Engagement)
    if is_manager():
        query = query.filter(Engagement.manager_id == user_id)
    elif is_team_member():
        assigned_ids = [
            a.engagement_id for a in db.query(EngagementTeamAssignment).filter(
                EngagementTeamAssignment.user_id == user_id
            ).all()
        ]
        query = query.filter(Engagement.engagement_id.in_(assigned_ids))

    all_engs = query.order_by(Engagement.created_at.desc()).all()

    # Apply search and status filters
    filtered_engs = []
    for eng in all_engs:
        if status_filter != "All" and eng.status != status_filter:
            continue
        if search_query:
            match_str = f"{eng.engagement_code} {eng.title} {eng.client.name} {eng.process_under_audit}".lower()
            if search_query not in match_str:
                continue
        filtered_engs.append(eng)

    st.markdown(f"**Showing {len(filtered_engs)} of {len(all_engs)} Engagements**")

    if not filtered_engs:
        st.info("No engagements found matching your criteria.")
        return

    # Render Engagement Cards
    for eng in filtered_engs:
        with st.container():
            render_engagement_card(db, eng)


def render_engagement_card(db, eng: Engagement):
    """Render a card-based view for an engagement with action buttons."""
    badge_html = render_status_badge(eng.status)
    budget_fmt = format_indian_currency(eng.estimated_budget)

    # Team members list
    assigned_members = [a.user.name for a in eng.team_assignments]
    team_names = ", ".join(assigned_members) if assigned_members else "No team assigned yet"

    c_left, c_right = st.columns([4, 2])
    with c_left:
        st.markdown(f"### {eng.title}")
        st.markdown(
            f"**Code:** `{eng.engagement_code}` | **Client:** **{eng.client.name}** | {badge_html}",
            unsafe_allow_html=True
        )
        st.markdown(f"**Process:** {eng.process_under_audit} | **Audit Period:** `{eng.audit_period_start}` to `{eng.audit_period_end}`")
        st.caption(f"👥 **Team:** {team_names} | 💰 **Estimated Budget:** {budget_fmt}")
        if eng.deadline:
            overdue_flag, days = is_overdue(eng.deadline)
            if overdue_flag and eng.status != "Completed":
                st.markdown(f"<span style='color: #EF4444; font-weight: 700;'>⚠️ OVERDUE by {days} days (Deadline was {eng.deadline})</span>", unsafe_allow_html=True)
            else:
                st.caption(f"🗓️ Target Deadline: {eng.deadline}")

    with c_right:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Open Workspace 📂", key=f"card_open_{eng.engagement_id}", type="primary"):
            st.session_state.selected_engagement_id = eng.engagement_id
            st.session_state.active_page = "Engagement Hub"
            st.rerun()

        # Manager quick actions
        if is_manager() and eng.status in ["Draft", "Assigned"]:
            with st.expander("Assign / Reassign Team", expanded=False):
                render_team_assignment_widget(db, eng)

    st.markdown("<hr style='margin: 12px 0; border-color: rgba(100,116,139,0.15);'>", unsafe_allow_html=True)


# =====================================================================
# 2. NEW ENGAGEMENT CREATION FORM (STEP 1)
# =====================================================================

def render_create_engagement_form(db, manager_id: int):
    """
    Step 1: Engagement Creation Form
    Manager logs in -> clicks New Engagement -> uploads Engagement Letter -> fills form:
    Client Name, Process/Area under Audit, Audit Period (Indian date picker / 8-digit auto-parser),
    Scope, Areas Covered -> Saves (status: Draft).
    """
    st.markdown("### 📝 Create New Audit Engagement")
    st.markdown("*Define engagement parameters, upload signed engagement letter, and specify audit scope.*")

    clients = db.query(Client).order_by(Client.name).all()
    client_names = [c.name for c in clients]
    client_names.append("+ Add New Client...")

    # Auto-generate next engagement code
    last_eng = db.query(Engagement).order_by(Engagement.engagement_id.desc()).first()
    next_num = (last_eng.engagement_id + 1) if last_eng else 1
    default_code = f"ENG-{datetime.now().year}-{next_num:03d}"

    with st.form("create_engagement_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            eng_code = st.text_input("Engagement Code *", value=default_code)
            title = st.text_input("Engagement Title *", placeholder="e.g. Internal Financial Controls Audit FY26-27")
            selected_client = st.selectbox("Client / Auditee Name *", client_names)
            
            # Quick client details if new
            new_client_name = ""
            new_client_industry = ""
            if selected_client == "+ Add New Client...":
                new_client_name = st.text_input("New Client Legal Name *", placeholder="e.g. Reliance Retail Ltd.")
                new_client_industry = st.text_input("Industry / Sector", placeholder="e.g. Retail & FMCG")

            process = st.text_input("Process / Area under Audit *", placeholder="e.g. Revenue Recognition & Accounts Receivable")

        with c2:
            st.markdown("##### 🗓️ Audit Period (DD-MM-YYYY)")
            st.caption("Pick dates via calendar or type 8 digits (e.g., 01042026 auto-formats to 01-04-2026)")
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                period_start_input = st.text_input("Period Start Date *", value="01-04-2026")
            with col_p2:
                period_end_input = st.text_input("Period End Date *", value="30-06-2026")

            deadline_input = st.text_input("Audit Completion Deadline", value="31-10-2026")
            
            budget_raw = st.number_input("Estimated Audit Fee / Budget (INR ₹)", min_value=0.0, value=1500000.0, step=50000.0)
            st.caption(f"Formatted: **{format_indian_currency(budget_raw)}** (Indian numbering system)")

        st.markdown("##### 📄 Engagement Scope & Areas Covered")
        scope = st.text_area("Audit Scope", placeholder="Describe standard compliance scope, testing depth, sampling methodology...")
        areas = st.text_area("Specific Areas / Sub-processes Covered", placeholder="e.g. Order Booking, Credit Approval, Invoicing, Collection Reconciliations")

        st.markdown("##### 📎 Upload Engagement Letter (PDF, Word, or Scanned Document)")
        uploaded_letter = st.file_uploader(
            "Upload Engagement Letter",
            type=["pdf", "docx", "doc", "txt", "png", "jpg"],
            help="The signed engagement charter between the firm and client."
        )

        submit_btn = st.form_submit_button("Save Engagement as Draft 💾", type="primary")

    if submit_btn:
        # Validate inputs
        if not eng_code.strip() or not title.strip() or not process.strip():
            st.error("Please fill in all mandatory fields (Engagement Code, Title, Process).")
            return

        # Normalize and validate Indian dates
        norm_start = normalize_indian_date_input(period_start_input)
        norm_end = normalize_indian_date_input(period_end_input)
        norm_deadline = normalize_indian_date_input(deadline_input)

        if not parse_indian_date(norm_start) or not parse_indian_date(norm_end):
            st.error("Invalid date format for Audit Period. Please enter valid DD-MM-YYYY dates.")
            return

        # Handle Client resolution
        client_obj = None
        if selected_client == "+ Add New Client...":
            if not new_client_name.strip():
                st.error("Please provide a name for the new client.")
                return
            client_obj = Client(name=new_client_name.strip(), industry=new_client_industry.strip())
            db.add(client_obj)
            db.commit()
        else:
            client_obj = db.query(Client).filter(Client.name == selected_client).first()

        # Create Engagement record
        new_eng = Engagement(
            engagement_code=eng_code.strip(),
            client_id=client_obj.client_id,
            title=title.strip(),
            process_under_audit=process.strip(),
            audit_period_start=norm_start,
            audit_period_end=norm_end,
            scope=scope.strip(),
            areas_covered=areas.strip(),
            estimated_budget=float(budget_raw),
            deadline=norm_deadline,
            status="Draft",
            manager_id=manager_id,
            is_locked=False
        )
        db.add(new_eng)
        db.commit()

        # Handle uploaded engagement letter
        if uploaded_letter:
            letter_dir = get_engagement_letter_dir(new_eng.engagement_id)
            target_path = letter_dir / uploaded_letter.name
            save_uploaded_file(uploaded_letter, target_path)
            new_eng.engagement_letter_filename = uploaded_letter.name
            new_eng.engagement_letter_path = str(target_path)
            db.commit()

        # Log to immutable audit trail
        log_audit_action(
            session=db,
            action_type="CREATE_ENGAGEMENT",
            target_entity="Engagement",
            target_id=new_eng.engagement_code,
            description=f"Created new engagement '{new_eng.title}' for client '{client_obj.name}' with status Draft.",
            user_id=st.session_state.user_id,
            acting_user_name=st.session_state.name,
            true_admin_id=st.session_state.true_admin_id,
            true_admin_name=st.session_state.true_admin_name
        )

        st.success(f"Engagement [{new_eng.engagement_code}] successfully created as Draft! You can now assign team members.")
        st.session_state.show_create_engagement = False
        st.session_state.selected_engagement_id = new_eng.engagement_id
        st.rerun()

    if st.button("Cancel", key="cancel_create_eng"):
        st.session_state.show_create_engagement = False
        st.rerun()


# =====================================================================
# 3. TEAM ASSIGNMENT WIDGET (STEP 2)
# =====================================================================

def render_team_assignment_widget(db, eng: Engagement):
    """
    Step 2: Team Assignment (Manager)
    Manager selects a team or creates an assignment -> updates status to Assigned.
    """
    teams = db.query(Team).all()
    team_options = {t.name: t.team_id for t in teams}
    team_options["Custom Team Selection"] = None

    selected_team_name = st.selectbox(
        "Select Team Group",
        list(team_options.keys()),
        key=f"team_select_{eng.engagement_id}"
    )

    all_auditors = db.query(User).filter(User.role == "Team Member").all()
    auditor_dict = {f"{u.name} ({u.designation or 'Auditor'})": u.user_id for u in all_auditors}

    # Pre-select members if team group selected
    default_selected = []
    selected_team_id = team_options.get(selected_team_name)
    if selected_team_id:
        team_members = db.query(TeamMemberMapping).filter(TeamMemberMapping.team_id == selected_team_id).all()
        member_user_ids = [tm.user_id for tm in team_members]
        default_selected = [k for k, v in auditor_dict.items() if v in member_user_ids]

    assigned_auditors = st.multiselect(
        "Assigned Auditors",
        options=list(auditor_dict.keys()),
        default=default_selected,
        key=f"auditor_multi_{eng.engagement_id}"
    )

    if st.button("Confirm Team Assignment 👥", key=f"btn_assign_{eng.engagement_id}", type="primary"):
        if not assigned_auditors:
            st.warning("Please select at least one team member.")
            return

        # Clear existing assignments
        db.query(EngagementTeamAssignment).filter(
            EngagementTeamAssignment.engagement_id == eng.engagement_id
        ).delete()

        # Add new assignments
        assigned_names = []
        for idx, item in enumerate(assigned_auditors):
            u_id = auditor_dict[item]
            u_obj = db.query(User).get(u_id)
            assigned_names.append(u_obj.name)
            assignment = EngagementTeamAssignment(
                engagement_id=eng.engagement_id,
                team_id=selected_team_id,
                user_id=u_id,
                role_in_audit="Lead Auditor" if idx == 0 else "Field Auditor"
            )
            db.add(assignment)

        # Update engagement status to Assigned if currently Draft
        if eng.status == "Draft":
            eng.status = "Assigned"

        db.commit()

        log_audit_action(
            session=db,
            action_type="TEAM_ASSIGNMENT",
            target_entity="Engagement",
            target_id=eng.engagement_code,
            description=f"Assigned team [{', '.join(assigned_names)}] to engagement '{eng.title}'. Status updated to Assigned.",
            user_id=st.session_state.user_id,
            acting_user_name=st.session_state.name,
            true_admin_id=st.session_state.true_admin_id,
            true_admin_name=st.session_state.true_admin_name
        )
        st.success(f"Team successfully assigned! Status is now '{eng.status}'.")
        st.rerun()
