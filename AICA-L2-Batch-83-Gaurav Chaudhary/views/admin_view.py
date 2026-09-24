import streamlit as st
import pandas as pd
import database as db
import auth

def render_user_management(current_user):
    st.subheader("👥 User Management & Team Access Control")
    u_col1, u_col2 = st.columns([1, 1])
    with u_col1:
        st.markdown("#### ➕ Add New User / Team Member")
        with st.form("add_user_form"):
            new_uname = st.text_input("Username *", placeholder="e.g. vikask")
            new_pwd = st.text_input("Password *", type="password", placeholder="Enter secure password")
            new_fname = st.text_input("Full Name *", placeholder="e.g. Vikas Kumar (Audit Executive)")
            new_role = st.selectbox("Role *", ["Team Member", "Partner"])
            new_email = st.text_input("Email Address", placeholder="e.g. vikas@ca-firm.com")
            new_mobile = st.text_input("Mobile Number", placeholder="e.g. +91 98444 55667")
            
            if st.form_submit_button("Create User Account", type="primary", use_container_width=True):
                if not new_uname or not new_pwd or not new_fname:
                    st.error("Username, Password, and Full Name are required.")
                else:
                    success = db.save_user(
                        username=new_uname.strip(),
                        password_hash=auth.hash_password(new_pwd),
                        full_name=new_fname.strip(),
                        role=new_role,
                        email=new_email.strip(),
                        mobile=new_mobile.strip(),
                        status="Active"
                    )
                    if success:
                        st.success(f"User account '{new_uname}' created successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to create user. Username might already exist.")
                        
    with u_col2:
        st.markdown("#### 👥 Existing Users")
        users_list = db.get_users()
        if users_list:
            df_users = pd.DataFrame(users_list)[["id", "username", "full_name", "role", "email", "mobile", "status"]]
            st.dataframe(df_users, use_container_width=True)
            
            st.markdown("##### Remove User")
            removable_users = [u for u in users_list if u["username"] != current_user["username"]]
            if removable_users:
                user_to_del = st.selectbox("Select User ID to remove:", [u["id"] for u in removable_users], format_func=lambda x: f"ID #{x} ({next((u['username'] for u in users_list if u['id']==x), '')})")
                if st.button("🗑️ Delete Selected User", type="secondary"):
                    db.delete_user(user_to_del)
                    st.success("User deleted successfully.")
                    st.rerun()
            else:
                st.info("No other removable users.")

def render_settings():
    st.subheader("⚙️ System Configuration & API Gateway Settings")
    with st.form("settings_form"):
        st.markdown("#### 📧 SMTP Email Configuration")
        smtp_host = st.text_input("SMTP Server Host", value=db.get_setting("smtp_host", "smtp.gmail.com"))
        smtp_port = st.text_input("SMTP Server Port", value=db.get_setting("smtp_port", "587"))
        smtp_user = st.text_input("SMTP Username / Email", value=db.get_setting("smtp_user", "audit.desk@ca-firm.com"))
        smtp_pass = st.text_input("SMTP App Password", value=db.get_setting("smtp_pass", ""), type="password")
        smtp_sender = st.text_input("Sender Display Email", value=db.get_setting("smtp_sender", "audit.desk@ca-firm.com"))
        partner_email = st.text_input("Partner Escalation Email", value=db.get_setting("partner_email", "partner@ca-firm.com"))
        
        st.markdown("---")
        st.markdown("#### 📱 WhatsApp / SMS Gateway API Integration")
        wa_url = st.text_input("Gateway Webhook / API URL", value=db.get_setting("whatsapp_api_url", "https://api.whatsapp-gateway.com/send"))
        wa_key = st.text_input("Gateway Auth Token / API Key", value=db.get_setting("whatsapp_api_key", ""), type="password")
        
        st.markdown("---")
        st.markdown("#### ⏱️ Automation Rules")
        inactivity_days = st.number_input("Inactivity Alert Threshold (Days without update)", min_value=1, max_value=30, value=int(db.get_setting("inactivity_days", "3")))
        
        if st.form_submit_button("💾 Save System Settings", type="primary", use_container_width=True):
            db.save_setting("smtp_host", smtp_host.strip())
            db.save_setting("smtp_port", smtp_port.strip())
            db.save_setting("smtp_user", smtp_user.strip())
            db.save_setting("smtp_pass", smtp_pass.strip())
            db.save_setting("smtp_sender", smtp_sender.strip())
            db.save_setting("partner_email", partner_email.strip())
            db.save_setting("whatsapp_api_url", wa_url.strip())
            db.save_setting("whatsapp_api_key", wa_key.strip())
            db.save_setting("inactivity_days", str(inactivity_days))
            st.success("✅ System settings saved successfully!")
