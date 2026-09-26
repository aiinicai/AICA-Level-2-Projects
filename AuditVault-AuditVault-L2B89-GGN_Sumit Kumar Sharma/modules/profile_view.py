"""
AuditVault - User Profile & System Preferences
Edit user personal details (Name, Age, Designation, Email, Phone),
update password, toggle theme (Light / Dark), and relaunch guided product tour.
"""

import streamlit as st
from models import User
from auth import hash_password, verify_password
from utils import log_audit_action


def render_profile_page(db):
    """Render the user profile and preferences view."""
    user_id = st.session_state.get("user_id")
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        st.error("User profile could not be found.")
        return

    st.markdown("## 👤 User Profile & Workspace Settings")
    st.markdown("*Manage your personal credentials, contact information, and AuditVault theme preferences.*")
    st.markdown("<hr style='margin: 8px 0 16px 0; border-color: rgba(100,116,139,0.2);'>", unsafe_allow_html=True)

    c_left, c_right = st.columns([3, 2])

    with c_left:
        st.markdown("### 📋 Personal & Professional Details")
        with st.form("profile_edit_form"):
            uname_disp = st.text_input("Username", value=user.username, disabled=True)
            role_disp = st.text_input("Role", value=user.role, disabled=True)
            
            p_name = st.text_input("Full Name *", value=user.name)
            p_desig = st.text_input("Designation", value=user.designation or "")
            p_email = st.text_input("Official Email *", value=user.email)
            p_phone = st.text_input("Contact Phone", value=user.phone or "")
            p_age = st.number_input("Age", min_value=18, max_value=85, value=user.age or 30)

            save_profile_btn = st.form_submit_button("Update Profile Details 💾", type="primary")

        if save_profile_btn:
            if not p_name.strip() or not p_email.strip():
                st.error("Name and Email are mandatory fields.")
            else:
                user.name = p_name.strip()
                user.designation = p_desig.strip()
                user.email = p_email.strip()
                user.phone = p_phone.strip()
                user.age = int(p_age)
                db.commit()

                st.session_state.name = user.name
                st.session_state.email = user.email

                log_audit_action(
                    session=db,
                    action_type="EDIT_PROFILE",
                    target_entity="User",
                    target_id=user.username,
                    description=f"User '{user.name}' updated profile details.",
                    user_id=user.user_id,
                    acting_user_name=user.name,
                    true_admin_id=st.session_state.true_admin_id,
                    true_admin_name=st.session_state.true_admin_name
                )
                st.success("Profile details updated successfully!")
                st.rerun()

    with c_right:
        st.markdown("### 🎨 Visual Theme & Interface")
        current_theme = st.session_state.get("theme", user.theme_preference or "light")
        theme_choice = st.radio(
            "Interface Theme Preference:",
            ["Light Mode ☀️", "Dark Mode 🌙", "System Default 💻"],
            index=0 if current_theme == "light" else (1 if current_theme == "dark" else 2)
        )

        theme_code = "light"
        if "Dark" in theme_choice:
            theme_code = "dark"
        elif "System" in theme_choice:
            theme_code = "system"

        if st.button("Apply Theme Setting 🎨"):
            st.session_state.theme = theme_code
            user.theme_preference = theme_code
            db.commit()
            st.rerun()

        st.markdown("<hr style='margin: 16px 0; border-color: rgba(100,116,139,0.15);'>", unsafe_allow_html=True)

        st.markdown("### 🧭 Product Walkthrough")
        st.caption("Relaunch the interactive guided tour for your current role.")
        if st.button("Relaunch Guided Tour 🚀"):
            st.session_state.show_tour = True
            st.session_state.tour_step_idx = 0
            st.rerun()

        st.markdown("<hr style='margin: 16px 0; border-color: rgba(100,116,139,0.15);'>", unsafe_allow_html=True)

        st.markdown("### 🔐 Change Password")
        with st.form("change_pwd_form"):
            curr_pwd = st.text_input("Current Password", type="password")
            new_pwd = st.text_input("New Password", type="password")
            confirm_pwd = st.text_input("Confirm New Password", type="password")
            submit_pwd = st.form_submit_button("Update Password 🔒")

        if submit_pwd:
            if not verify_password(user.password_hash, curr_pwd):
                st.error("Current password is incorrect.")
            elif new_pwd != confirm_pwd:
                st.error("New passwords do not match.")
            elif len(new_pwd.strip()) < 6:
                st.error("New password must be at least 6 characters.")
            else:
                user.password_hash = hash_password(new_pwd.strip())
                db.commit()
                st.success("Password updated successfully!")
