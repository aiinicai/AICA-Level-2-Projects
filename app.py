import streamlit as st
import pandas as pd
import datetime
import os

# Import core modules
import database as db
import auth
import notifications
import analytics
import reports

# Import View Modules
from views.dashboard_view import render_dashboard
from views.assignments_view import render_assignments
from views.update_status_view import render_update_status
from views.new_allocation_view import render_new_allocation
from views.critical_view import render_critical
from views.intelligence_view import render_intelligence
from views.documents_view import render_documents
from views.excel_view import render_excel_module
from views.reports_view import render_reports
from views.reminders_view import render_reminders
from views.admin_view import render_user_management, render_settings

# Page configuration
st.set_page_config(
    page_title="GS Stock Audit Tracker",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Corporate CSS Theme (Clean White & Navy Blue)
st.markdown("""
<style>
    .main {
        background-color: #F8FAFC;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .ca-header {
        background: linear-gradient(135deg, #1E3A8A 0%, #1E40AF 100%);
        padding: 20px 25px;
        border-radius: 10px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .ca-header h1 {
        margin: 0;
        font-size: 24px;
        font-weight: 700;
        color: #FFFFFF;
    }
    .ca-header p {
        margin: 5px 0 0 0;
        font-size: 13px;
        color: #DBEAFE;
    }
    .kpi-card {
        background: #FFFFFF;
        border-radius: 10px;
        padding: 16px 14px;
        border-left: 5px solid #1E3A8A;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: transform 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .kpi-title {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        color: #64748B;
        letter-spacing: 0.5px;
    }
    .kpi-value {
        font-size: 24px;
        font-weight: 700;
        color: #0F172A;
        margin: 4px 0 2px 0;
    }
    .kpi-subtitle {
        font-size: 11px;
        color: #94A3B8;
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        text-align: center;
    }
    .badge-completed { background-color: #DEF7EC; color: #03543F; }
    .badge-delayed { background-color: #FDE8E8; color: #9B1C1C; }
    .badge-progress { background-color: #E1EFFE; color: #1E429F; }
    .badge-pending { background-color: #FEF08A; color: #713F12; }
    .badge-critical { background-color: #FEE2E2; color: #B91C1C; border: 1px solid #F87171; }
</style>
""", unsafe_allow_html=True)

# Initialize Database & Default Data
db.init_db()
auth.create_default_users()

# Session State
if "user" not in st.session_state:
    st.session_state.user = None

def login(username, password):
    user = auth.authenticate_user(username, password)
    if user:
        st.session_state.user = user
        st.toast(f"Welcome back, {user['full_name']}!", icon="👋")
        st.rerun()
    else:
        st.error("Invalid Username or Password. Please try again.")

def logout():
    st.session_state.user = None
    st.rerun()

# ----------------- LOGIN SCREEN -----------------
if not st.session_state.user:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; margin-bottom: 25px;">
            <div style="font-size: 48px;">🏛️</div>
            <h2 style="color: #1E3A8A; margin-bottom: 5px;">GS Stock Audit Tracker</h2>
            <h4 style="color: #475569; font-weight: normal; margin-top: 0;">Bank Stock Audit Monitoring & Tracking System</h4>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            st.subheader("🔐 Secure Sign In")
            demo_user = st.selectbox(
                "⚡ Quick Fill Demo Credentials:",
                [
                    "-- Select Demo User --",
                    "Partner (CA Gaurav Chaudhary) [User: partner / Pass: admin123]",
                    "Team Member (Priya Verma) [User: priya / Pass: priya123]",
                    "Team Member (Amit Gupta) [User: amit / Pass: amit123]",
                    "Team Member (Sneha Patel) [User: sneha / Pass: sneha123]"
                ]
            )
            
            uname_val, pwd_val = "", ""
            if "partner" in demo_user.lower():
                uname_val, pwd_val = "partner", "admin123"
            elif "priya" in demo_user.lower():
                uname_val, pwd_val = "priya", "priya123"
            elif "amit" in demo_user.lower():
                uname_val, pwd_val = "amit", "amit123"
            elif "sneha" in demo_user.lower():
                uname_val, pwd_val = "sneha", "sneha123"
                
            username = st.text_input("Username", value=uname_val, placeholder="Enter username")
            password = st.text_input("Password", value=pwd_val, type="password", placeholder="Enter password")
            
            if st.button("Sign In to Dashboard", type="primary", use_container_width=True):
                login(username, password)
                
            st.markdown("""
            <div style="margin-top: 15px; font-size: 12px; color: #64748B; text-align: center;">
                🔒 Protected by End-to-End Encryption & Role-Based Access Control
            </div>
            """, unsafe_allow_html=True)
    st.stop()

# ----------------- AUTHENTICATED APPLICATION -----------------
current_user = st.session_state.user
is_partner = (current_user.get("role") == "Partner")
current_user_name = current_user.get("full_name")

# Header
st.markdown(f"""
<div class="ca-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1>🏛️ GS STOCK AUDIT TRACKER</h1>
            <p>Empowering CA Gaurav Chaudhary & Team with Real-Time Assignment Visibility, AI Delay Prediction & Bank Compliance</p>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 14px; font-weight: bold; color: #FEF08A;">👤 {current_user_name}</div>
            <div style="font-size: 12px; color: #BFDBFE;">Role: <span style="background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 12px;">{current_user.get('role')}</span></div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar Menu
with st.sidebar:
    st.markdown(f"### 📋 GS Stock Audit Tracker")
    st.markdown(f"**Logged in as:** `{current_user['username']}`")
    st.markdown("---")
    
    menu_options = [
        "📊 Partner Dashboard",
        "📋 All Assignments & Search",
        "✏️ Quick Status Update",
        "➕ New Audit Allocation",
        "⚠️ Critical & Pending Items",
        "📈 Intelligence & Analytics",
        "📁 Document Management",
        "📤 Excel Import & Migration",
        "📥 Export Reports (Excel/PDF)",
        "🔔 Reminders & Escalations",
        "📜 Audit Trail & Logs"
    ]
    
    if is_partner:
        menu_options.append("👥 User Management")
        menu_options.append("⚙️ System Settings")
        
    choice = st.radio("Go to:", menu_options, index=0)
    
    st.markdown("---")
    if st.button("🚪 Sign Out", use_container_width=True):
        logout()
        
    st.markdown("""
    <div style="margin-top: 30px; font-size: 11px; color: #94A3B8; text-align: center;">
        GS Stock Audit Tracker v2.5<br>
        Lead Partner: CA Gaurav Chaudhary<br>
        © 2026 GS Stock Audit Solutions
    </div>
    """, unsafe_allow_html=True)

# Fetch user-scoped assignments
all_assignments = db.get_all_assignments(
    user_role="Partner" if is_partner else "Team Member",
    team_person_name=None if is_partner else current_user.get("full_name")
)

# Route to View
if choice == "📊 Partner Dashboard":
    render_dashboard(all_assignments)
elif choice == "📋 All Assignments & Search":
    render_assignments(all_assignments)
elif choice == "✏️ Quick Status Update":
    render_update_status(all_assignments, current_user_name)
elif choice == "➕ New Audit Allocation":
    render_new_allocation(current_user_name)
elif choice == "⚠️ Critical & Pending Items":
    render_critical(all_assignments)
elif choice == "📈 Intelligence & Analytics":
    render_intelligence(all_assignments)
elif choice == "📁 Document Management":
    render_documents(all_assignments, current_user_name)
elif choice == "📤 Excel Import & Migration":
    render_excel_module(current_user_name)
elif choice == "📥 Export Reports (Excel/PDF)":
    render_reports(all_assignments, current_user_name)
elif choice == "🔔 Reminders & Escalations":
    render_reminders(all_assignments)
elif choice == "📜 Audit Trail & Logs":
    st.subheader("📜 Activity Audit Trail & Compliance Log")
    st.markdown("Complete, tamper-evident record of all user actions, status transitions, and data modifications.")
    logs = db.get_activity_logs(limit=150)
    if logs:
        st.dataframe(pd.DataFrame(logs)[["id", "timestamp", "user_name", "borrower_name", "action", "old_value", "new_value"]], use_container_width=True, height=450)
    else:
        st.info("No activity logged yet.")
elif choice == "👥 User Management" and is_partner:
    render_user_management(current_user)
elif choice == "⚙️ System Settings" and is_partner:
    render_settings()
