"""
AuditVault - Admin Panel Module
User Account Management, Password Resets, and Support Impersonation ("Switch User")
with permanent, immutable audit logging.
"""

from pathlib import Path
from datetime import datetime
import streamlit as st
import pandas as pd

from models import User, Engagement, AuditTrailEntry, Client
from auth import (
    is_admin, hash_password, reset_user_password, impersonate_user
)
from utils import log_audit_action, current_indian_date_str


def render_admin_panel(db):
    """Render administrative user controls."""
    if not is_admin():
        st.error("⛔ Access Denied. Administrator privileges required.")
        return

    admin_user = db.query(User).filter(User.user_id == st.session_state.user_id).first()

    st.markdown("## ⚙️ Administration & Security Panel")
    st.markdown("*Manage user credentials, reset passwords, and conduct support impersonation.*")
    st.markdown("<hr style='margin: 8px 0 16px 0; border-color: rgba(100,116,139,0.2);'>", unsafe_allow_html=True)

    # Sub-tabs
    tab_users, tab_create, tab_impersonate, tab_reset = st.tabs([
        "👥 Active Users Directory",
        "➕ Create New User",
        "🎭 Impersonate / Switch User",
        "🔑 Reset User Password"
    ])

    # =====================================================================
    # TAB 1: USER DIRECTORY
    # =====================================================================
    with tab_users:
        st.markdown("### 📋 System Users")
        users = db.query(User).order_by(User.role, User.name).all()

        user_rows = []
        for u in users:
            user_rows.append({
                "User ID": u.user_id,
                "Username": u.username,
                "Full Name": u.name,
                "Role": u.role,
                "Designation": u.designation or "-",
                "Email": u.email,
                "Phone": u.phone or "-"
            })
        st.dataframe(pd.DataFrame(user_rows), use_container_width=True, hide_index=True)

    # =====================================================================
    # TAB 2: CREATE NEW USER
    # =====================================================================
    with tab_create:
        st.markdown("### ➕ Create New User Account")
        st.caption("Administrators can provision Managers and Engagement Team Members (Auditors).")

        with st.form("create_user_form", clear_on_submit=True):
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                new_username = st.text_input("Username *", placeholder="e.g. auditor.suresh")
                new_name = st.text_input("Full Name *", placeholder="e.g. Suresh Iyer")
                new_role = st.selectbox("Role *", ["Manager", "Team Member"])
                new_designation = st.text_input("Designation", placeholder="e.g. Senior Internal Auditor")

            with col_u2:
                new_email = st.text_input("Official Email *", placeholder="e.g. suresh.iyer@firm.com")
                new_phone = st.text_input("Phone Number", placeholder="e.g. +91 98765 43210")
                new_age = st.number_input("Age", min_value=18, max_value=80, value=28)
                new_password = st.text_input("Temporary Password *", type="password", placeholder="Enter secure password")

            submit_create = st.form_submit_button("Create User Account 🚀", type="primary")

        if submit_create:
            if not new_username.strip() or not new_name.strip() or not new_email.strip() or not new_password.strip():
                st.error("Please fill in all mandatory fields (Username, Name, Email, Password).")
            else:
                # Check uniqueness
                exists = db.query(User).filter(
                    (User.username == new_username.strip()) | (User.email == new_email.strip())
                ).first()
                if exists:
                    st.error("Username or email already exists in AuditVault.")
                else:
                    new_u = User(
                        username=new_username.strip().lower(),
                        password_hash=hash_password(new_password.strip()),
                        name=new_name.strip(),
                        age=int(new_age),
                        designation=new_designation.strip(),
                        email=new_email.strip().lower(),
                        phone=new_phone.strip(),
                        role=new_role,
                        is_first_login=True
                    )
                    db.add(new_u)
                    db.commit()

                    log_audit_action(
                        session=db,
                        action_type="CREATE_USER",
                        target_entity="User",
                        target_id=new_u.username,
                        description=f"Admin '{admin_user.name}' created new user account '{new_u.username}' with role '{new_u.role}'.",
                        user_id=admin_user.user_id,
                        acting_user_name=admin_user.name
                    )
                    st.success(f"User account for '{new_u.name}' ({new_u.username}) successfully created!")
                    st.rerun()

    # =====================================================================
    # TAB 3: IMPERSONATE / SWITCH USER (ROLE 1 CORE FEATURE)
    # =====================================================================
    with tab_impersonate:
        st.markdown("### 🎭 Support Impersonation (\"Switch User\")")
        st.markdown("""
        **Administrative Support Tool:**
        Switch seamlessly into any Manager or Engagement Team Member account to assist with troubleshooting,
        inspecting view permissions, or resolving workflow issues.
        """)

        st.warning("""
        ⚠️ **MANDATORY AUDIT RULE:**
        Every switch into a user account is recorded in the immutable audit trail:
        `"Admin X accessed AuditVault as User Y at [timestamp]"`
        Any subsequent audit changes will retain your true administrator identity.
        """)

        # Non-admin users list
        targetable_users = db.query(User).filter(User.role != "Admin").order_by(User.role, User.name).all()
        user_choice_map = {f"{u.name} ({u.role} - @{u.username})": u for u in targetable_users}

        selected_label = st.selectbox(
            "Select User Account to Impersonate:",
            list(user_choice_map.keys())
        )

        target_user = user_choice_map.get(selected_label)

        if st.button(f"Switch into {target_user.name}'s Account 🚀", type="primary"):
            impersonate_user(target_user, db)
            st.rerun()

    # =====================================================================
    # TAB 4: PASSWORD RESET
    # =====================================================================
    with tab_reset:
        st.markdown("### 🔑 Reset User Password")
        all_non_admins = db.query(User).filter(User.role != "Admin").all()
        reset_map = {f"{u.name} (@{u.username})": u.user_id for u in all_non_admins}

        sel_user_to_reset = st.selectbox("Select User", list(reset_map.keys()))
        new_pwd = st.text_input("Enter New Password", type="password", key="reset_pwd_inp")

        if st.button("Reset Password 🔐", type="primary"):
            if not new_pwd.strip():
                st.error("Please enter a new password.")
            else:
                target_uid = reset_map[sel_user_to_reset]
                success, msg = reset_user_password(db, target_uid, new_pwd.strip(), admin_user)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
