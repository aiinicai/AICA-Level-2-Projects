"""
BOI Account Opening Audit & Document Scrutiny System
Main Streamlit Application Entrypoint
"""

import streamlit as st
from data_manager import get_default_accounts
from views.scrutiny_view import render_scrutiny_view
from views.dashboard_view import render_dashboard_view
from views.export_view import render_export_view
from views.guide_view import render_guide_view

# Streamlit Page Config
st.set_page_config(
    page_title="BOI Account Opening Audit & Document Scrutiny System",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Styling with Bank of India Theme Palette
CUSTOM_CSS = """
<style>
    /* Main Theme Variables */
    :root {
        --boi-navy: #0B2545;
        --boi-blue: #133E68;
        --boi-orange: #E65100;
        --boi-light-bg: #F4F7FB;
        --boi-card-border: #E2E8F0;
        --boi-text-dark: #0F172A;
    }

    /* Top Demo Banner */
    .demo-banner {
        background: linear-gradient(90deg, #E65100 0%, #F57C00 100%);
        color: #FFFFFF;
        padding: 10px 16px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 13.5px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(230, 81, 0, 0.2);
    }

    /* Page Titles */
    .page-title {
        font-size: 26px;
        font-weight: 800;
        color: #0B2545;
        margin-bottom: 2px;
        letter-spacing: -0.5px;
    }
    .page-subtitle {
        font-size: 14px;
        color: #64748B;
        margin-bottom: 20px;
    }

    /* Sidebar Customization */
    [data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
    
    .sidebar-brand {
        background: #0B2545;
        color: white;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 20px;
        text-align: center;
    }
    .sidebar-brand h3 {
        color: #FFFFFF;
        margin: 0;
        font-size: 17px;
        font-weight: 700;
    }
    .sidebar-brand p {
        color: #93C5FD;
        margin: 4px 0 0 0;
        font-size: 11.5px;
    }

    .auditor-badge {
        background-color: #EFF6FF;
        border: 1px solid #BFDBFE;
        padding: 10px;
        border-radius: 6px;
        margin-top: 15px;
        font-size: 12px;
        color: #1E40AF;
    }

    /* Metrics Styling */
    [data-testid="stMetricValue"] {
        font-size: 22px !important;
        font-weight: 700 !important;
        color: #0B2545 !important;
    }

    /* Button Styling */
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_app_state():
    """Initializes session state with synthetic accounts if not already present."""
    if "accounts" not in st.session_state:
        st.session_state["accounts"] = get_default_accounts()
    if "auditor_pf" not in st.session_state:
        st.session_state["auditor_pf"] = "PF-849201"
    if "auditor_name" not in st.session_state:
        st.session_state["auditor_name"] = "Vikas M. Kulkarni (Chief Manager - Audit)"
    if "current_selected_account_id" not in st.session_state:
        st.session_state["current_selected_account_id"] = st.session_state["accounts"][0]["account_id"]


def main():
    init_app_state()

    # -------------------------------------------------------------
    # Top Sticky Training & Synthetic Data Banner
    # -------------------------------------------------------------
    st.markdown("""
    <div class="demo-banner">
        ⚠️ <strong>TRAINING & CONCURRENT AUDIT DEMO MODE</strong> — All customer names, account numbers, CKYC records, and branch details are 100% synthetic/dummy data. Never input real customer PII or banking credentials.
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Sidebar Navigation & Auditor Details
    # -------------------------------------------------------------
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-brand">
            <h3>🏛️ Bank of India</h3>
            <p>Concurrent Audit & Document Scrutiny System</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 🧭 Audit Navigation")
        nav_options = [
            "📄 Document Scrutiny & Approval",
            "📈 Audit Summary Dashboard",
            "📥 Export Audit Report",
            "📖 About & Checklist Guide"
        ]

        # Check if navigation was set programmatically
        nav_index = 0
        if "nav_menu" in st.session_state:
            for idx, opt in enumerate(nav_options):
                if st.session_state["nav_menu"] in opt:
                    nav_index = idx
                    break

        selected_nav = st.radio(
            "Select Module:",
            nav_options,
            index=nav_index,
            label_visibility="collapsed"
        )
        st.session_state["nav_menu"] = selected_nav

        st.markdown("---")
        
        # Auditor Profile Details
        st.markdown(f"""
        <div class="auditor-badge">
            <strong>👤 Concurrent Auditor Profile:</strong><br>
            Name: <strong>{st.session_state['auditor_name']}</strong><br>
            PF Code: <strong>{st.session_state['auditor_pf']}</strong><br>
            Zone: <strong>Mumbai South Zonal Audit Office</strong>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### ⚙️ Demo Controls")
        if st.button("🔄 Reset Demo Data to Default", use_container_width=True, help="Re-initializes all dummy accounts to initial demonstration state"):
            st.session_state["accounts"] = get_default_accounts()
            st.session_state["current_selected_account_id"] = st.session_state["accounts"][0]["account_id"]
            st.toast("Synthetic demo datasets reset successfully!", icon="🔄")
            st.rerun()

        st.caption("Version 1.0.0 | Python 3.14 + Streamlit")

    # -------------------------------------------------------------
    # Page Router
    # -------------------------------------------------------------
    if "Document Scrutiny" in selected_nav:
        render_scrutiny_view()
    elif "Dashboard" in selected_nav:
        render_dashboard_view()
    elif "Export" in selected_nav:
        render_export_view()
    elif "About" in selected_nav or "Guide" in selected_nav:
        render_guide_view()


if __name__ == "__main__":
    main()
