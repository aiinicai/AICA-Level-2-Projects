"""
AuditVault - Client & Team Management Module
Manager & Admin controls for client profiles, team groups (Team 1, Team 2, etc.),
and flexible team member assignments.
"""

import streamlit as st
import pandas as pd
from models import Client, Team, TeamMemberMapping, User, Engagement
from utils import log_audit_action
from auth import is_manager, is_admin


def render_client_team_page(db):
    """Render clients directory and team groupings."""
    if not (is_manager() or is_admin()):
        st.error("⛔ Access restricted to Managers and Administrators.")
        return

    st.markdown("## 🏢 Clients & Team Groupings")
    st.markdown("*Organize auditee client directories and configure cross-functional audit teams.*")
    st.markdown("<hr style='margin: 8px 0 16px 0; border-color: rgba(100,116,139,0.2);'>", unsafe_allow_html=True)

    tab_clients, tab_teams, tab_new_member = st.tabs([
        "🏢 Client Directory",
        "👥 Audit Teams Builder",
        "➕ Add Team Member"
    ])

    # =====================================================================
    # TAB 1: CLIENT DIRECTORY
    # =====================================================================
    with tab_clients:
        st.markdown("### 📋 Client Organizations")
        
        with st.expander("➕ Add New Client Organization", expanded=False):
            with st.form("add_client_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    c_name = st.text_input("Client Legal Name *", placeholder="e.g. Larsen & Toubro Infotech")
                    c_ind = st.text_input("Industry / Domain", placeholder="e.g. Engineering & IT")
                    c_addr = st.text_area("Registered Office Address", placeholder="Street, City, State, PIN")
                with c2:
                    c_spoc = st.text_input("Primary Contact Person", placeholder="e.g. Rajesh Khurana (CFO)")
                    c_email = st.text_input("Contact Email", placeholder="e.g. rkhurana@lti.com")
                    c_phone = st.text_input("Contact Phone", placeholder="e.g. +91 22 6789 0123")

                submit_c = st.form_submit_button("Save Client 💾", type="primary")

            if submit_c:
                if not c_name.strip():
                    st.error("Client name is required.")
                else:
                    new_cl = Client(
                        name=c_name.strip(),
                        industry=c_ind.strip(),
                        address=c_addr.strip(),
                        contact_person=c_spoc.strip(),
                        contact_email=c_email.strip(),
                        contact_phone=c_phone.strip()
                    )
                    db.add(new_cl)
                    db.commit()

                    log_audit_action(
                        session=db,
                        action_type="CREATE_CLIENT",
                        target_entity="Client",
                        target_id=new_cl.name,
                        description=f"Added client profile for '{new_cl.name}'.",
                        user_id=st.session_state.user_id,
                        acting_user_name=st.session_state.name,
                        true_admin_id=st.session_state.true_admin_id,
                        true_admin_name=st.session_state.true_admin_name
                    )
                    st.success(f"Client '{new_cl.name}' added!")
                    st.rerun()

        clients = db.query(Client).order_by(Client.name).all()
        cl_rows = []
        for c in clients:
            cl_rows.append({
                "ID": c.client_id,
                "Client Name": c.name,
                "Industry": c.industry or "-",
                "Primary SPOC": c.contact_person or "-",
                "Email": c.contact_email or "-",
                "Active Audits": len(c.engagements)
            })
        st.dataframe(pd.DataFrame(cl_rows), use_container_width=True, hide_index=True)

    # =====================================================================
    # TAB 2: AUDIT TEAMS BUILDER
    # =====================================================================
    with tab_teams:
        st.markdown("### 👥 Audit Teams (Team 1, Team 2, Team 3, etc.)")
        st.caption("Group audit team members into specialized squads for rapid engagement assignment.")

        with st.expander("➕ Create New Audit Team", expanded=False):
            with st.form("create_team_form", clear_on_submit=True):
                team_title = st.text_input("Team Name *", placeholder="e.g. Team 4 - Forensic & Fraud Risk")
                team_desc = st.text_area("Team Focus / Competencies", placeholder="Specialized in forensic analytics, data dumps, and fraud risk assessments.")
                
                # Auditors multi-select
                auditors = db.query(User).filter(User.role == "Team Member").all()
                aud_options = {f"{u.name} ({u.designation or 'Auditor'})": u.user_id for u in auditors}
                selected_auds = st.multiselect("Select Team Members", list(aud_options.keys()))

                create_team_sub = st.form_submit_button("Create Team 👥", type="primary")

            if create_team_sub:
                if not team_title.strip():
                    st.error("Team name is required.")
                else:
                    new_t = Team(
                        name=team_title.strip(),
                        description=team_desc.strip(),
                        created_by_manager_id=st.session_state.user_id
                    )
                    db.add(new_t)
                    db.commit()

                    for a_label in selected_auds:
                        uid = aud_options[a_label]
                        db.add(TeamMemberMapping(team_id=new_t.team_id, user_id=uid))
                    db.commit()

                    log_audit_action(
                        session=db,
                        action_type="CREATE_TEAM",
                        target_entity="Team",
                        target_id=new_t.name,
                        description=f"Created team group '{new_t.name}' with {len(selected_auds)} members.",
                        user_id=st.session_state.user_id,
                        acting_user_name=st.session_state.name,
                        true_admin_id=st.session_state.true_admin_id,
                        true_admin_name=st.session_state.true_admin_name
                    )
                    st.success(f"Team '{new_t.name}' successfully created!")
                    st.rerun()

        # Existing Teams List
        teams = db.query(Team).all()
        for t in teams:
            with st.container():
                members = [m.user.name for m in t.members]
                mem_str = ", ".join(members) if members else "No members assigned"
                st.markdown(f"#### 🛡️ {t.name}")
                st.markdown(f"*{t.description or 'Standard audit team.'}*")
                st.markdown(f"**Members ({len(members)}):** `{mem_str}`")
                st.markdown("<hr style='margin: 8px 0; border-color: rgba(100,116,139,0.15);'>", unsafe_allow_html=True)

    # =====================================================================
    # TAB 3: ADD TEAM MEMBER (MANAGER / ADMIN PRIVILEGE)
    # =====================================================================
    with tab_new_member:
        st.markdown("### ➕ Register New Engagement Team Member")
        st.caption("Managers can add new auditors and associate them directly with audit squads.")

        with st.form("mgr_add_auditor_form", clear_on_submit=True):
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                aud_uname = st.text_input("Username *", placeholder="e.g. auditor.rahul")
                aud_name = st.text_input("Full Name *", placeholder="e.g. Rahul Sen")
                aud_desig = st.text_input("Designation", placeholder="e.g. Junior Auditor / Article Assistant")
            with col_a2:
                aud_email = st.text_input("Email *", placeholder="e.g. rahul.sen@firm.com")
                aud_phone = st.text_input("Phone", placeholder="e.g. +91 98300 12345")
                aud_pwd = st.text_input("Temporary Password *", type="password", value="auditor123")

            sub_aud = st.form_submit_button("Register Auditor 👤", type="primary")

        if sub_aud:
            if not aud_uname.strip() or not aud_name.strip() or not aud_email.strip():
                st.error("Please fill in Username, Full Name, and Email.")
            else:
                from auth import hash_password
                u_check = db.query(User).filter((User.username == aud_uname.strip()) | (User.email == aud_email.strip())).first()
                if u_check:
                    st.error("Username or email already exists.")
                else:
                    new_aud = User(
                        username=aud_uname.strip().lower(),
                        password_hash=hash_password(aud_pwd.strip()),
                        name=aud_name.strip(),
                        designation=aud_desig.strip(),
                        email=aud_email.strip().lower(),
                        phone=aud_phone.strip(),
                        role="Team Member",
                        is_first_login=True
                    )
                    db.add(new_aud)
                    db.commit()

                    log_audit_action(
                        session=db,
                        action_type="CREATE_USER",
                        target_entity="User",
                        target_id=new_aud.username,
                        description=f"Manager added new auditor '{new_aud.name}' ({new_aud.username}).",
                        user_id=st.session_state.user_id,
                        acting_user_name=st.session_state.name,
                        true_admin_id=st.session_state.true_admin_id,
                        true_admin_name=st.session_state.true_admin_name
                    )
                    st.success(f"Auditor '{new_aud.name}' registered successfully!")
                    st.rerun()
