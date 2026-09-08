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
"""
 AUDIT SAMPLING & FRAUD DETECTION TOOL  (v2)
 Capstone Project - AICA Level 2
 HOW TO RUN THIS FILE (only 2 things needed):
   1) Make sure Python is installed on your computer.
   2) Open Command Prompt in the folder where this file is saved,
      and type:   python app.py
      Then press Enter.  (Or just double-click run.bat on Windows.)

 That's it. This file will automatically:
   - Install every library it needs (only on the first run)
   - Launch the Streamlit web app in your browser automatically

 No manual pip install. No virtual environment. No folder setup.
 Just one file, one command.
"""

import sys
import subprocess
import importlib
import os

# ---------------------------------------------------------------
# STEP A: AUTO-INSTALL ALL REQUIRED LIBRARIES (runs every time,
# but is instant if already installed - it only installs what's
# missing).
# ---------------------------------------------------------------
REQUIRED_PACKAGES = {
    "streamlit": "streamlit",
    "pandas": "pandas",
    "numpy": "numpy",
    "plotly": "plotly",
    "openpyxl": "openpyxl",
    "fpdf2": "fpdf",   # pip name : import name
}

def ensure_packages():
    for pip_name, import_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            print(f"[Setup] Installing missing package: {pip_name} ... please wait.")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", pip_name])

ensure_packages()

# ---------------------------------------------------------------
# STEP B: AUTO-LAUNCH STREAMLIT (so you never have to type
# "streamlit run ..." yourself). If this script was started with
# plain "python app.py", it relaunches itself under Streamlit.
#
# Guard against a double-launch: if someone runs `streamlit run app.py`
# directly instead of `python app.py`, the script is already executing
# inside a live Streamlit server - in that case `st.runtime.exists()`
# is True and we must NOT spawn a second nested `streamlit run` (which
# would just grab the next free port and leave the original tab blank).
# ---------------------------------------------------------------
def _already_running_under_streamlit() -> bool:
    try:
        import streamlit as _st
        return _st.runtime.exists()
    except Exception:
        return False

if os.environ.get("AUDIT_APP_LAUNCHED") != "1" and not _already_running_under_streamlit():
    os.environ["AUDIT_APP_LAUNCHED"] = "1"
    print("[Setup] Launching the app in your browser... (this window must stay open)")
    subprocess.run([sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)])
    sys.exit(0)

# =====================================================================
# FROM THIS POINT ON, THE ACTUAL APPLICATION CODE RUNS INSIDE STREAMLIT
# =====================================================================

import io
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from fpdf import FPDF

# =====================================================================
# 1. INDIAN NUMBER / CURRENCY FORMATTING
# ---------------------------------------------------------------------
# Indian digit grouping is NOT the same as the Western "thousands every
# 3 digits" scheme. After the first 3 digits (from the right), India
# groups in pairs of 2: 1,23,45,678 (not 12,345,678). We implement this
# by hand since pandas/locale support for it is inconsistent across
# machines that may not have an "en_IN" locale installed.
# =====================================================================
def _indian_group(int_part: str) -> str:
    """Group the integer portion of a number using the Indian numbering
    system: last 3 digits together, then pairs of 2 to the left."""
    sign = ""
    if int_part.startswith("-"):
        sign, int_part = "-", int_part[1:]
    if len(int_part) <= 3:
        return sign + int_part
    last3 = int_part[-3:]
    rest = int_part[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return sign + ",".join(parts) + "," + last3


def format_inr(amount, decimals: int = 2, symbol: str = "\u20b9") -> str:
    """Format a number as Indian-style currency, e.g. 1234567.5 -> '₹12,34,567.50'."""
    if amount is None or (isinstance(amount, float) and np.isnan(amount)):
        return "-"
    negative = amount < 0
    amount = abs(float(amount))
    whole = int(amount)
    frac = round(amount - whole, decimals)
    frac_str = f"{frac:.{decimals}f}".split(".")[1] if decimals > 0 else ""
    grouped = _indian_group(str(whole))
    out = f"{symbol}{grouped}" + (f".{frac_str}" if decimals > 0 else "")
    return f"-{out}" if negative else out


def format_inr_compact(amount) -> str:
    """Lakhs/Crores compact display, e.g. 12345678 -> '₹1.23 Cr', 234567 -> '₹2.35 L'.
    Offered as an OPTIONAL alternate display (toggle in the sidebar) since Indian
    audit workpapers commonly quote figures in lakhs/crores for readability."""
    if amount is None or (isinstance(amount, float) and np.isnan(amount)):
        return "-"
    negative = amount < 0
    amount = abs(float(amount))
    if amount >= 1_00_00_000:
        val, suffix = amount / 1_00_00_000, "Cr"
    elif amount >= 1_00_000:
        val, suffix = amount / 1_00_000, "L"
    elif amount >= 1_000:
        val, suffix = amount / 1_000, "K"
    else:
        val, suffix = amount, ""
    out = f"\u20b9{val:,.2f} {suffix}".strip()
    return f"-{out}" if negative else out


def fmt_currency(amount, compact: bool = False) -> str:
    return format_inr_compact(amount) if compact else format_inr(amount)


def fmt_date_ddmmyyyy(d) -> str:
    """Indian reporting convention: DD-MM-YYYY, not the US MM/DD/YYYY."""
    if pd.isna(d):
        return "-"
    return pd.Timestamp(d).strftime("%d-%m-%Y")


# =====================================================================
# 2. SAMPLE DATA GENERATOR (used when user has no file to upload, and
#    also used offline to produce the bundled sample_data.csv)
# =====================================================================
def generate_sample_data(num_rows: int = 500, seed: int = 42) -> pd.DataFrame:
    """Builds a synthetic but realistic-looking population of transactions,
    then deliberately plants a handful of each anomaly type so every fraud
    check and Benford's Law have something genuine to catch in a demo -
    without ever touching a real client's data."""
    random.seed(seed)
    np.random.seed(seed)

    vendor_names = [f"Vendor_{i}" for i in range(1, 26)]
    approvers = ['Rahul Sharma', 'Priya Singh', 'Amit Verma', 'Sunita Rao', 'Vikram Nair']
    start_date = datetime(2024, 4, 1)  # Indian financial year start

    # Log-normal amounts, clustered around a realistic median (~Rs 30,000)
    # but still spanning several orders of magnitude. This is a deliberate
    # balance between two competing needs of the demo data:
    #   - Benford's Law only holds for unmanipulated data that spans
    #     multiple orders of magnitude, so a narrow range (e.g. everything
    #     between 40,000-60,000) would fail the test even with zero
    #     manipulation - a false positive.
    #   - A perfectly log-UNIFORM spread (tried first) satisfies Benford's
    #     Law even better, but is *too* dispersed to look like a real
    #     transaction population: the robust (MAD/IQR) outlier check ended
    #     up flagging roughly a third of all rows simply because the whole
    #     population had no realistic "typical" cluster to be an outlier
    #     from. Log-normal gives a realistic concentration around the
    #     median while its long right tail still spans enough orders of
    #     magnitude for a clean Benford's Law fit.
    amounts = np.random.lognormal(mean=np.log(30000), sigma=1.0, size=num_rows)
    amounts = np.round(np.clip(amounts, 100, None), 2)

    def random_weekday_date():
        # Genuine business transactions happen on weekdays (Mon-Fri) only,
        # so any 500-day span is fine here; the weekend anomalies are
        # planted separately below.
        d = start_date + timedelta(days=random.randint(0, 365))
        while d.weekday() >= 5:
            d = start_date + timedelta(days=random.randint(0, 365))
        return d

    data = []
    for i in range(num_rows):
        voucher_no = f"V{1000 + i}"
        date = random_weekday_date()
        vendor = random.choice(vendor_names)
        amount = float(amounts[i])
        account_head = random.choice(
            ['Office Supplies', 'Travel', 'Consulting', 'Rent', 'Utilities', 'Salaries']
        )
        approver = random.choice(approvers)
        # In a genuine, well-controlled process, the approver and the person
        # who raised the transaction are almost always different people
        # (segregation of duties). We enforce that here and violate it
        # deliberately below for a handful of rows.
        raised_by = random.choice([a for a in approvers if a != approver])
        data.append([voucher_no, date, vendor, amount, account_head, approver, raised_by])

    df = pd.DataFrame(
        data,
        columns=['Voucher_No', 'Date', 'Vendor_Name', 'Amount',
                 'Account_Head', 'Approver', 'Raised_By']
    )

    # ---- Plant a handful of realistic anomalies ----
    dup_rows = df.sample(5, random_state=1).copy()
    df = pd.concat([df, dup_rows], ignore_index=True)

    round_idx = df.sample(8, random_state=2).index
    df.loc[round_idx, 'Amount'] = [50000, 100000, 25000, 75000, 100000, 50000, 30000, 60000]

    thresh_idx = df.sample(6, random_state=3).index
    df.loc[thresh_idx, 'Amount'] = [49999, 49500, 48999, 49800, 49999, 49200]

    sod_idx = df.sample(5, random_state=4).index
    for idx in sod_idx:
        df.loc[idx, 'Raised_By'] = df.loc[idx, 'Approver']

    weekend_idx = df.sample(5, random_state=5).index
    for idx in weekend_idx:
        d = df.loc[idx, 'Date']
        days_to_saturday = (5 - d.weekday()) % 7
        df.loc[idx, 'Date'] = d + timedelta(days=days_to_saturday)

    outlier_idx = df.sample(3, random_state=6).index
    df.loc[outlier_idx, 'Amount'] = [1500000, 1750000, 1999999]

    return df.reset_index(drop=True)


# =====================================================================
# 3. DATA LOADING, COLUMN MAPPING & CLEANING
# ---------------------------------------------------------------------
# IMPORTANT FIX vs the v1 prototype: v1 called df.drop_duplicates() as
# part of "cleaning", which ran BEFORE the duplicate-transaction fraud
# check - so exact duplicate rows (a classic fraud/error red flag) were
# silently deleted and the check could never find them.
#
# The fix here is not to run the check earlier and dedupe later; it is
# to stop silently deleting rows at all. An auditor should never have
# rows removed from the population automatically just because they look
# like duplicates - that decision belongs to the auditor after the
# duplicate check has flagged them. So `clean_data()` below only fixes
# DATA TYPES (parsing dates/amounts) and drops rows that are structurally
# unusable (unparseable date/amount), never rows that are merely repeated.
# The exact same dataframe is then used for BOTH fraud detection AND
# sampling/Benford's Law, so nothing is ever hidden from either step.
#
# COLUMN NAMES ARE NOT REQUIRED TO MATCH EXACTLY. Real-world exports from
# Tally, SAP, QuickBooks, or a plain accounts spreadsheet almost never use
# the exact labels 'Voucher_No' / 'Raised_By' etc. Rather than reject a
# file for using 'Transaction_ID' instead of 'Voucher_No', we auto-detect
# the best matching source column for each field the tool needs (via a
# alias list, then a fuzzy-text fallback) and let the user confirm/adjust
# the mapping before anything is analysed. Only four fields are truly
# required for the tool to function at all (CORE_FIELDS below); the rest
# are optional and individual fraud checks quietly skip themselves if the
# data they need isn't present - see `available_fraud_checks()`.
# =====================================================================
CORE_FIELDS = ['Voucher_No', 'Date', 'Vendor_Name', 'Amount']
OPTIONAL_FIELDS = ['Account_Head', 'Approver', 'Raised_By']
ALL_FIELDS = CORE_FIELDS + OPTIONAL_FIELDS

# Common real-world header spellings for each field we need, used to guess
# a mapping automatically. Matching is case/space/underscore-insensitive
# (see `_normalize_header`), so 'Transaction Date', 'transaction_date' and
# 'TRANSACTIONDATE' all match the same alias below.
COLUMN_ALIASES = {
    'Voucher_No': [
        'voucher_no', 'voucher number', 'voucher', 'voucher id', 'txn_id', 'txnid',
        'transaction_id', 'transaction no', 'transaction number', 'invoice_number',
        'invoice no', 'invoice_no', 'bill_no', 'bill number', 'ref_no', 'reference_no',
        'reference number', 'doc_no', 'document number', 'document no', 'entry_no',
        'journal_no', 'sr_no', 'serial no', 'id',
    ],
    'Date': [
        'date', 'transaction_date', 'txn_date', 'posting_date', 'entry_date',
        'voucher_date', 'invoice_date', 'doc_date', 'document date', 'bill_date',
        'value_date', 'payment_date',
    ],
    'Vendor_Name': [
        'vendor_name', 'vendor', 'payee', 'party_name', 'party', 'supplier',
        'supplier_name', 'beneficiary', 'paid_to', 'account_name', 'creditor',
        'ledger_name',
    ],
    'Amount': [
        'amount', 'amt', 'value', 'transaction_amount', 'net_amount', 'total_amount',
        'invoice_amount', 'debit_amount', 'payment_amount', 'gross_amount', 'txn_amount',
    ],
    'Account_Head': [
        'account_head', 'account', 'ledger', 'ledger_head', 'expense_head', 'department',
        'category', 'head_of_account', 'gl_account', 'cost_center', 'cost_centre',
        'expense_category', 'nature_of_expense',
    ],
    'Approver': [
        'approver', 'approved_by', 'authorised_by', 'authorized_by', 'sanctioned_by',
        'checked_by', 'verified_by', 'signed_off_by',
    ],
    'Raised_By': [
        'raised_by', 'prepared_by', 'created_by', 'entered_by', 'recorded_by',
        'initiated_by', 'requested_by', 'processed_by', 'made_by', 'submitted_by',
    ],
}


def _normalize_header(s: str) -> str:
    return str(s).strip().lower().replace('-', '_').replace(' ', '_')


def suggest_column_mapping(columns) -> dict:
    """For each field the tool needs, guess which uploaded column it
    corresponds to. Returns {field: matched_column_or_None}.

    Pass 1 - exact match against the alias list (fast, unambiguous).
    Pass 2 - anything still unmatched falls back to fuzzy text matching
    (difflib) against the remaining unclaimed columns, which catches
    near-misses like 'Vendor' vs 'Vendor_Nm' or minor typos.
    Each source column can only be claimed by one field, so a very
    generic uploaded file never has two fields silently pointing at the
    same column.
    """
    import difflib
    norm_to_original = {_normalize_header(c): c for c in columns}
    unclaimed = set(norm_to_original.keys())
    mapping = {}

    for field in ALL_FIELDS:
        match = None
        for alias in COLUMN_ALIASES[field]:
            if alias in unclaimed:
                match = norm_to_original[alias]
                unclaimed.discard(alias)
                break
        mapping[field] = match

    for field in ALL_FIELDS:
        if mapping[field] is not None or not unclaimed:
            continue
        close = difflib.get_close_matches(
            _normalize_header(field), list(unclaimed), n=1, cutoff=0.72)
        if not close:
            for alias in COLUMN_ALIASES[field]:
                close = difflib.get_close_matches(alias, list(unclaimed), n=1, cutoff=0.8)
                if close:
                    break
        if close:
            mapping[field] = norm_to_original[close[0]]
            unclaimed.discard(close[0])

    return mapping


def load_data(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    return df


def apply_column_mapping(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Renames the user-confirmed source columns onto our canonical field
    names. Fields left unmapped simply don't appear in the output - every
    downstream function already tolerates missing optional columns."""
    rename = {src: field for field, src in mapping.items() if src}
    out = df.rename(columns=rename)
    keep = [c for c in ALL_FIELDS if c in out.columns]
    return out[keep].copy()


def clean_data(df: pd.DataFrame):
    """Type-coercion only - see module docstring above for why this no
    longer drops duplicate rows. Returns (clean_df, dropped_row_count)."""
    df = df.copy()
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True)
    if 'Amount' in df.columns:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    before = len(df)
    df = df.dropna(subset=[c for c in ['Amount', 'Date'] if c in df.columns])
    dropped = before - len(df)
    for c in ['Voucher_No', 'Vendor_Name', 'Account_Head', 'Approver', 'Raised_By']:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    if 'Account_Head' not in df.columns:
        df['Account_Head'] = 'N/A'
    return df.reset_index(drop=True), dropped


# =====================================================================
# 4. AUDIT SAMPLING METHODS  (SA 530 - Audit Sampling)
# =====================================================================
def random_sampling(df: pd.DataFrame, sample_size: int) -> pd.DataFrame:
    """Simple random sampling: every transaction has an equal chance of
    selection. Use when the population is homogeneous and there's no
    reason to believe risk correlates with any particular attribute."""
    sample_size = min(sample_size, len(df))
    if sample_size <= 0:
        return df.iloc[0:0]
    return df.sample(n=sample_size, random_state=42)


def systematic_sampling(df: pd.DataFrame, sample_size: int) -> pd.DataFrame:
    """Systematic sampling: pick every k-th item after a random start. Fast
    and easy to execute manually, but risky if the population has a hidden
    periodic pattern that lines up with the interval (e.g. every 7th
    voucher happens to be the same recurring vendor)."""
    sample_size = min(sample_size, len(df))
    if sample_size <= 0 or len(df) == 0:
        return df.iloc[0:0]
    interval = max(1, len(df) // sample_size)
    start = random.randint(0, interval - 1) if interval > 1 else 0
    return df.iloc[start::interval].head(sample_size)


def monetary_unit_sampling(df: pd.DataFrame, sample_size: int, amount_col: str = 'Amount'):
    """TRUE Monetary Unit Sampling (a.k.a. Cumulative Monetary Amount /
    dollar-unit sampling) - textbook implementation, not a probability-
    weighted approximation.

    The idea: instead of treating each TRANSACTION as a sampling unit,
    treat each RUPEE as a sampling unit, and select transactions by
    picking evenly-spaced points along the cumulative-amount number line.
    This automatically gives larger transactions a proportionally higher
    chance of selection (a ₹10,00,000 transaction contains 10,00,000
    "rupee units" to land on, a ₹100 transaction only 100) - which is
    exactly the property auditors want when the audit objective is
    "detect material misstatement", since a rupee of error in a large
    balance is just as material as one in a small balance, but the same
    is not true of the transaction *count*.

    Returns (sampled_df, info_dict) where info_dict explains what happened
    (e.g. how many items were "certain selections" because their amount
    alone exceeded the sampling interval).
    """
    work = df[df[amount_col] > 0].copy()
    info = {"certain_selections": 0, "interval": 0.0, "excluded_non_positive": len(df) - len(work)}
    if work.empty:
        return df.iloc[0:0], info

    sample_size = min(sample_size, len(work))
    if sample_size <= 0:
        return df.iloc[0:0], info

    total = float(work[amount_col].sum())
    interval = total / sample_size
    info["interval"] = interval

    rng = np.random.default_rng(42)
    start_point = rng.uniform(0, interval)
    selection_points = start_point + interval * np.arange(sample_size)

    work = work.sort_values(amount_col, kind="mergesort")  # stable order for reproducibility
    cum = work[amount_col].cumsum().values
    positions = np.searchsorted(cum, selection_points, side="left")
    positions = np.clip(positions, 0, len(work) - 1)

    # A transaction whose own amount exceeds the sampling interval is a
    # "certain selection" - it will always be caught however the random
    # start point falls, because it spans more than one full interval.
    info["certain_selections"] = int((work[amount_col] > interval).sum())

    selected_positions = np.unique(positions)
    result = work.iloc[selected_positions].sort_index()
    return result, info


def stratified_sampling(df: pd.DataFrame, sample_size: int, amount_col: str = 'Amount', num_strata: int = 3):
    """Stratified sampling: split the population into value bands (strata)
    first, then sample within each band. Use when the population is NOT
    homogeneous (e.g. a mix of small routine purchases and a few large
    capital items) so that both ends of the value range are represented,
    rather than a plain random sample being dominated by the many small
    items.

    Edge case handled: if the population has too few distinct Amount
    values to form `num_strata` quantile bins (e.g. a tiny dataset, or
    every transaction happening to be the exact same amount),
    pandas.qcut cannot create unique bin edges. We progressively reduce
    the number of strata, and fall back to a single stratum (which
    degrades gracefully to plain random sampling) rather than crashing.
    """
    sample_size = min(sample_size, len(df))
    if sample_size <= 0 or len(df) == 0:
        return df.iloc[0:0]

    dfc = df.copy()
    n_unique = dfc[amount_col].nunique()
    strata_to_try = max(1, min(num_strata, n_unique))
    dfc['Strata'] = 0
    while strata_to_try >= 1:
        try:
            if strata_to_try == 1:
                dfc['Strata'] = 0
                break
            dfc['Strata'] = pd.qcut(dfc[amount_col], q=strata_to_try, labels=False, duplicates='drop')
            break
        except ValueError:
            strata_to_try -= 1

    n_groups = max(1, dfc['Strata'].nunique())
    per_stratum = max(1, sample_size // n_groups)
    parts = []
    for _, group in dfc.groupby('Strata'):
        parts.append(group.sample(min(len(group), per_stratum), random_state=42))
    result = pd.concat(parts) if parts else dfc.head(0)
    result = result.drop(columns='Strata', errors='ignore')

    # Top up / trim to hit the requested sample size as closely as possible
    if len(result) < sample_size:
        remaining = dfc.drop(index=result.index).drop(columns='Strata', errors='ignore')
        top_up = remaining.sample(min(sample_size - len(result), len(remaining)), random_state=42) \
            if len(remaining) else remaining
        result = pd.concat([result, top_up])
    return result.sort_index()


SAMPLING_METHOD_INFO = {
    "Random Sampling": "Every transaction has an equal chance of selection. Best for a "
                        "homogeneous population with no known risk concentration.",
    "Systematic Sampling": "Selects every k-th transaction after a random start. Quick to "
                            "execute, but avoid it if the population may have a hidden "
                            "periodic pattern.",
    "Stratified Sampling": "Splits the population into value bands and samples within each, "
                            "so both small and large transactions are represented instead of "
                            "a plain random sample being dominated by numerous small items.",
    "Monetary Unit Sampling (PPS)": "Selects transactions with probability proportional to "
                                     "their rupee value (Cumulative Monetary Amount method). "
                                     "The standard method when the audit objective is to "
                                     "detect material Rupee misstatement, since it automatically "
                                     "gives large-value transactions a higher chance of being "
                                     "tested.",
}


# =====================================================================
# 5. FRAUD / RED-FLAG DETECTION RULES  (SA 240 - Auditor's Responsibilities
#    Relating to Fraud)
# ---------------------------------------------------------------------
# Every check below returns a copy of the flagged rows plus a
# 'Flag_Reason' column. They are all independently selectable in the UI
# and combined into one Risk_Score per transaction (= number of distinct
# checks a transaction triggered).
# =====================================================================
def check_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Exact duplicate rows (same vendor, amount and date) are a classic
    red flag for either double-payment error or deliberate duplicate
    billing. This check MUST run on the raw/undeduplicated data - see the
    module-3 docstring above for why v1 got this wrong."""
    mask = df.duplicated(subset=['Vendor_Name', 'Amount', 'Date'], keep=False)
    flagged = df[mask].copy()
    flagged['Flag_Reason'] = 'Duplicate Transaction'
    return flagged


def check_threshold_dodging(df: pd.DataFrame, limit: float = 50000, buffer_percent: float = 0.03) -> pd.DataFrame:
    """Transactions clustered just below an approval threshold suggest
    someone may be deliberately splitting or sizing a transaction to
    avoid triggering a higher approval level ('structuring')."""
    lower = limit * (1 - buffer_percent)
    mask = (df['Amount'] >= lower) & (df['Amount'] < limit)
    flagged = df[mask].copy()
    flagged['Flag_Reason'] = 'Threshold Dodging'
    return flagged


def check_round_numbers(df: pd.DataFrame, divisor: float = 5000) -> pd.DataFrame:
    """Genuine invoiced amounts (rate x quantity + taxes) are rarely exact
    round numbers. A cluster of suspiciously round amounts can indicate
    estimated/fabricated entries rather than real invoices."""
    mask = (df['Amount'] % divisor == 0) & (df['Amount'] > 0)
    flagged = df[mask].copy()
    flagged['Flag_Reason'] = 'Round Number Amount'
    return flagged


def check_weekend_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Transactions dated/recorded on a weekend are unusual for a normal
    business process and warrant a closer look at who processed them and
    why."""
    mask = df['Date'].dt.dayofweek >= 5
    flagged = df[mask].copy()
    flagged['Flag_Reason'] = 'Weekend Transaction'
    return flagged


def check_segregation_of_duties(df: pd.DataFrame) -> pd.DataFrame:
    """The person who raises a transaction and the person who approves it
    should never be the same individual - that control is what prevents
    one person from being able to both create and authorise a fraudulent
    payment unchecked."""
    if 'Approver' not in df.columns or 'Raised_By' not in df.columns:
        return df.iloc[0:0].copy()
    mask = df['Approver'] == df['Raised_By']
    flagged = df[mask].copy()
    flagged['Flag_Reason'] = 'Segregation of Duties Violation'
    return flagged


def check_outliers(df: pd.DataFrame, amount_col: str = 'Amount', method: str = 'MAD',
                    z_threshold: float = 3.0, mad_threshold: float = 3.5, iqr_k: float = 1.5) -> pd.DataFrame:
    """Flags statistically unusual transaction amounts. `method` selects
    the statistic used - see the three implementations below for why the
    default is NOT the classic mean/standard-deviation Z-score.

    THE MASKING EFFECT (why classic Z-score is a poor default here):
    Both the mean and the standard deviation are themselves calculated
    FROM the data that may contain the outliers. A single very large
    fraudulent transaction inflates the mean and massively inflates the
    standard deviation (since std is driven by squared deviations), which
    can push that outlier's own Z-score back under the flagging threshold
    - the outlier "masks" itself. MAD (Median Absolute Deviation) and IQR
    (Interquartile Range) are both based on the MEDIAN/quartiles rather
    than the mean, which barely move even if a large chunk of extreme
    values is added - so they resist this masking effect and are the
    methods generally recommended in forensic/audit analytics literature.
    """
    dfx = df.copy()
    vals = dfx[amount_col]

    if method == 'MAD':
        median = vals.median()
        mad = (vals - median).abs().median()
        if mad == 0 or pd.isna(mad):
            return df.iloc[0:0].copy()
        modified_z = 0.6745 * (vals - median) / mad
        mask = modified_z.abs() > mad_threshold
    elif method == 'IQR':
        q1, q3 = vals.quantile(0.25), vals.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0 or pd.isna(iqr):
            return df.iloc[0:0].copy()
        lower, upper = q1 - iqr_k * iqr, q3 + iqr_k * iqr
        mask = (vals < lower) | (vals > upper)
    else:  # 'Z-Score' - classic method, kept for comparison/teaching purposes
        mean, std = vals.mean(), vals.std()
        if std == 0 or pd.isna(std):
            return df.iloc[0:0].copy()
        z = (vals - mean) / std
        mask = z.abs() > z_threshold

    flagged = dfx[mask].copy()
    flagged['Flag_Reason'] = 'Statistical Outlier'
    return flagged


FRAUD_CHECK_INFO = {
    'Duplicates': "Exact repeats of vendor + amount + date - possible double payment or "
                  "duplicate billing.",
    'Threshold Dodging': "Amounts sitting just under an approval limit - possible deliberate "
                          "structuring to avoid a higher sign-off.",
    'Round Numbers': "Suspiciously round amounts that real invoices rarely produce exactly.",
    'Weekend Transactions': "Recorded on a Saturday/Sunday, outside the normal business "
                             "cycle.",
    'Segregation of Duties': "The same person both raised and approved the transaction - a "
                              "broken control.",
    'Statistical Outliers': "Amounts that are unusually large or small compared to the rest "
                             "of the population, using a robust (masking-resistant) method.",
}

# Every check needs Amount at minimum; a few need columns that a real-world
# export may not have mapped (e.g. many accounting exports have no
# 'raised by' equivalent at all, only an approver). Rather than block the
# whole file over one missing column, each check is simply left out of the
# selectable list when its inputs aren't available - the UI explains why.
FRAUD_CHECK_REQUIRES = {
    'Duplicates': ['Vendor_Name', 'Amount', 'Date'],
    'Threshold Dodging': ['Amount'],
    'Round Numbers': ['Amount'],
    'Weekend Transactions': ['Date'],
    'Segregation of Duties': ['Approver', 'Raised_By'],
    'Statistical Outliers': ['Amount'],
}


def available_fraud_checks(df: pd.DataFrame):
    """Splits checks into (available, unavailable) based on which columns
    were actually mapped for this file, so the UI can only offer checks
    that can run and explain why the rest are greyed out."""
    available, unavailable = [], {}
    for name, cols in FRAUD_CHECK_REQUIRES.items():
        missing = [c for c in cols if c not in df.columns]
        if missing:
            unavailable[name] = missing
        else:
            available.append(name)
    return available, unavailable


def run_all_fraud_checks(df: pd.DataFrame, threshold_limit: float = 50000,
                          selected_checks=None, outlier_method: str = 'MAD') -> pd.DataFrame:
    all_checks = {
        'Duplicates': lambda d: check_duplicates(d),
        'Threshold Dodging': lambda d: check_threshold_dodging(d, limit=threshold_limit),
        'Round Numbers': lambda d: check_round_numbers(d),
        'Weekend Transactions': lambda d: check_weekend_transactions(d),
        'Segregation of Duties': lambda d: check_segregation_of_duties(d),
        'Statistical Outliers': lambda d: check_outliers(d, method=outlier_method),
    }
    if selected_checks is None:
        selected_checks = list(all_checks.keys())

    empty_result = df.iloc[0:0].copy()
    empty_result['Flag_Reason'] = pd.Series(dtype='object')
    empty_result['Risk_Score'] = pd.Series(dtype='int')

    pieces = [all_checks[name](df) for name in selected_checks if name in all_checks]
    pieces = [p for p in pieces if len(p) > 0]

    if not pieces:
        return empty_result

    combined = pd.concat(pieces)
    risk_score = combined.groupby('Voucher_No').size().rename('Risk_Score')
    reasons = combined.groupby('Voucher_No')['Flag_Reason'].apply(lambda x: ', '.join(sorted(set(x))))
    base = combined.drop_duplicates(subset='Voucher_No').drop(columns='Flag_Reason')
    final = base.merge(risk_score, on='Voucher_No').merge(reasons, on='Voucher_No')
    final = final.sort_values('Risk_Score', ascending=False).reset_index(drop=True)
    return final


# =====================================================================
# 6. BENFORD'S LAW ANALYSIS  (no scipy dependency needed)
# =====================================================================
CHI_SQUARE_CRITICAL_VALUE_DF8_ALPHA05 = 15.507  # standard statistical table value (df=8, alpha=0.05)


def _first_digit(x):
    s = str(abs(x)).replace('.', '').lstrip('0')
    return int(s[0]) if s else None


def check_benfords_law(df: pd.DataFrame, amount_col: str = 'Amount'):
    """Benford's Law: in many naturally-occurring numerical datasets, the
    leading digit is NOT uniformly distributed - '1' appears first about
    30% of the time, '9' only about 4.6% of the time. Fabricated numbers
    (people inventing amounts) tend to distribute leading digits far more
    evenly, so a significant deviation from the expected Benford curve
    (tested via chi-square) is a recognised red flag for manipulated
    figures - though it is a screening tool, not proof, and needs at
    least several hundred data points and a wide value range to be
    reliable."""
    vals = df[amount_col].dropna()
    vals = vals[vals > 0]
    digits = vals.apply(_first_digit).dropna()
    total = len(digits)

    if total < 30:
        return {
            'actual_distribution': None, 'expected_distribution': None,
            'chi_square_stat': None, 'critical_value': CHI_SQUARE_CRITICAL_VALUE_DF8_ALPHA05,
            'significant_deviation': None, 'insufficient_data': True, 'n': total,
        }

    actual_counts = digits.value_counts().reindex(range(1, 10), fill_value=0).sort_index()
    expected_prop = {d: np.log10(1 + 1 / d) for d in range(1, 10)}
    expected_counts = pd.Series({d: expected_prop[d] * total for d in range(1, 10)}).sort_index()

    chi_stat = float(((actual_counts - expected_counts) ** 2 / expected_counts).sum())
    significant = chi_stat > CHI_SQUARE_CRITICAL_VALUE_DF8_ALPHA05

    return {
        'actual_distribution': actual_counts,
        'expected_distribution': expected_counts,
        'chi_square_stat': chi_stat,
        'critical_value': CHI_SQUARE_CRITICAL_VALUE_DF8_ALPHA05,
        'significant_deviation': significant,
        'insufficient_data': False,
        'n': total,
    }


def plot_benford_chart(actual_dist: pd.Series, expected_dist: pd.Series) -> go.Figure:
    digits = list(range(1, 10))
    fig = go.Figure()
    fig.add_bar(x=digits, y=actual_dist.values, name='Actual',
                marker_color='#0f3d5c', hovertemplate='Digit %{x}<br>Actual count: %{y}<extra></extra>')
    fig.add_bar(x=digits, y=expected_dist.values, name='Expected (Benford)',
                marker_color='#c9a227', hovertemplate='Digit %{x}<br>Expected count: %{y:.1f}<extra></extra>')
    fig.update_layout(
        barmode='group',
        title="Benford's Law - Actual vs Expected First-Digit Distribution",
        xaxis=dict(title='Leading Digit', tickmode='array', tickvals=digits),
        yaxis_title='Count of Transactions',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(t=60, b=40, l=40, r=20),
        height=420,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig


# =====================================================================
# 7. REPORT GENERATION  (all in-memory - no temp files ever touch disk)
# =====================================================================
def _autosize_and_style(ws, df: pd.DataFrame):
    from openpyxl.styles import Font, PatternFill, Alignment
    header_fill = PatternFill(start_color="0F3D5C", end_color="0F3D5C", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col_idx, col_name in enumerate(df.columns, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
        max_len = max([len(str(col_name))] + [len(str(v)) for v in df[col_name].astype(str).head(200)])
        ws.column_dimensions[cell.column_letter].width = min(max(max_len + 2, 10), 45)
    ws.freeze_panes = "A2"


def export_to_excel_bytes(flagged_df: pd.DataFrame, sampled_df: pd.DataFrame, source_df: pd.DataFrame) -> io.BytesIO:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        flagged_out = flagged_df if len(flagged_df) else pd.DataFrame({'Message': ['No flagged transactions found']})
        sampled_out = sampled_df if len(sampled_df) else pd.DataFrame({'Message': ['No sample generated yet']})
        flagged_out.to_excel(writer, sheet_name='Flagged_Transactions', index=False)
        sampled_out.to_excel(writer, sheet_name='Sampled_Transactions', index=False)

        summary = pd.DataFrame({
            'Metric': ['Report Generated', 'Total Transactions Analysed', 'Total Flagged Transactions',
                       'Flagged %'],
            'Value': [datetime.now().strftime('%d-%m-%Y %H:%M'), len(source_df), len(flagged_df),
                      f"{(len(flagged_df) / len(source_df) * 100) if len(source_df) else 0:.2f}%"],
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)

        _autosize_and_style(writer.sheets['Flagged_Transactions'], flagged_out)
        _autosize_and_style(writer.sheets['Sampled_Transactions'], sampled_out)
        _autosize_and_style(writer.sheets['Summary'], summary)
    buffer.seek(0)
    return buffer


# ---- Unicode-safe PDF font handling -----------------------------------
# fpdf2's built-in "helvetica"/"times"/"courier" core fonts are Latin-1
# only and raise an exception the moment a ₹ sign or any non-Latin-1
# vendor name reaches them - a real crash risk on real-world data. The
# correct fix is a Unicode TrueType font. Rather than bundling one more
# binary asset with the submission, we look for a Unicode-capable TTF
# that is already present on the machine (Windows/macOS/Linux all ship
# at least one candidate) and register that with fpdf2. If none can be
# found (a minimal/headless environment), we fall back to the Latin-1
# core font PLUS an ASCII-sanitising text filter, so PDF export still
# NEVER crashes - it just degrades formatting (₹ becomes "Rs.") instead.
_UNICODE_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/SFNSText.ttf",
]
_UNICODE_FONT_BOLD_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _find_first_existing(paths):
    for p in paths:
        if os.path.isfile(p):
            return p
    return None


def _pdf_ascii_safe(text: str) -> str:
    """Fallback sanitiser used only if no Unicode font is available."""
    return (text or "").replace("\u20b9", "Rs. ").encode("latin-1", "replace").decode("latin-1")


class AuditPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.unicode_ok = False
        regular = _find_first_existing(_UNICODE_FONT_CANDIDATES)
        bold = _find_first_existing(_UNICODE_FONT_BOLD_CANDIDATES) or regular
        if regular:
            try:
                self.add_font("Body", "", regular)
                self.add_font("Body", "B", bold)
                self.unicode_ok = True
            except Exception:
                self.unicode_ok = False
        if not self.unicode_ok:
            self.set_font("helvetica", size=12)  # core font fallback

    def set_body_font(self, size=12, bold=False):
        if self.unicode_ok:
            self.set_font("Body", "B" if bold else "", size)
        else:
            self.set_font("helvetica", "B" if bold else "", size)

    def text(self, s: str) -> str:
        return s if self.unicode_ok else _pdf_ascii_safe(s)

    def multi_cell(self, w=0, h=None, text="", *args, **kwargs):
        # fpdf2 leaves `x` at the RIGHT margin after a multi_cell call rather
        # than resetting it to the left margin. Since every call site here
        # uses w=0 ("use the remaining width from the current x position"),
        # the very next multi_cell would then compute an ever-shrinking
        # width and eventually raise "Not enough horizontal space" - this
        # was caught while testing the flagged-transactions list in the
        # PDF export. Resetting x first makes w=0 behave as intended
        # everywhere it's used.
        self.set_x(self.l_margin)
        return super().multi_cell(w, h, text, *args, **kwargs)


def generate_pdf_summary_bytes(total_transactions, flagged_count, sample_method,
                                sample_size, benford_result=None, top_flags: pd.DataFrame = None) -> io.BytesIO:
    pdf = AuditPDF()
    pdf.add_page()

    pdf.set_body_font(18, bold=True)
    pdf.cell(0, 12, text=pdf.text("Audit Sampling & Fraud Detection - Summary Report"), align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_body_font(10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, text=pdf.text(f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}"), align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    pdf.set_body_font(13, bold=True)
    pdf.cell(0, 8, text=pdf.text("Population & Sampling"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_body_font(11)
    pdf.cell(0, 7, text=pdf.text(f"Total Transactions Analysed: {total_transactions:,}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, text=pdf.text(f"Sampling Method Used: {sample_method}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, text=pdf.text(f"Sample Size Drawn: {sample_size}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_body_font(13, bold=True)
    pdf.cell(0, 8, text=pdf.text("Fraud / Red-Flag Detection"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_body_font(11)
    pct = (flagged_count / total_transactions * 100) if total_transactions else 0
    pdf.cell(0, 7, text=pdf.text(f"Total Flagged Transactions: {flagged_count:,} ({pct:.2f}% of population)"), new_x="LMARGIN", new_y="NEXT")

    if top_flags is not None and len(top_flags):
        pdf.ln(2)
        pdf.set_body_font(10, bold=True)
        pdf.cell(0, 6, text=pdf.text("Top flagged transactions (by Risk Score):"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_body_font(9)
        for _, row in top_flags.head(10).iterrows():
            currency = format_inr(row.get('Amount', 0))
            line = f"{row.get('Voucher_No','')}  |  {row.get('Vendor_Name','')}  |  {currency}  |  Risk {row.get('Risk_Score','')}  |  {row.get('Flag_Reason','')}"
            pdf.multi_cell(0, 5, text=pdf.text(line))
    pdf.ln(4)

    if benford_result is not None and not benford_result.get('insufficient_data', True):
        pdf.set_body_font(13, bold=True)
        pdf.cell(0, 8, text=pdf.text("Benford's Law Analysis"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_body_font(11)
        pdf.cell(0, 7, text=pdf.text(f"Chi-Square Statistic: {benford_result['chi_square_stat']:.2f}"), new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, text=pdf.text(f"Critical Value (df=8, 95% confidence): {benford_result['critical_value']}"), new_x="LMARGIN", new_y="NEXT")
        verdict = "Significant deviation detected - amounts may not be naturally occurring (possible manipulation)." \
            if benford_result['significant_deviation'] else "No significant deviation - amounts appear naturally distributed."
        pdf.multi_cell(0, 7, text=pdf.text(f"Conclusion: {verdict}"))

    pdf.ln(6)
    pdf.set_body_font(8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 5, text=pdf.text(
        "This report was produced by a training/capstone audit-sampling tool and does not "
        "constitute a certified statutory audit opinion. All findings require corroboration "
        "by a qualified auditor before being relied upon."))

    out = pdf.output()
    return io.BytesIO(bytes(out))


# =====================================================================
# 8. STREAMLIT USER INTERFACE
# =====================================================================
st.set_page_config(
    page_title="Audit Sampling & Fraud Detection Tool",
    page_icon="\U0001F50E",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------
# Custom CSS - built on Streamlit's own CSS variables so it adapts
# automatically to light/dark mode instead of hard-coding colours.
# ---------------------------------------------------------------
st.markdown("""
<style>
    #MainMenu, footer {visibility: hidden;}
    .block-container {padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1200px;}

    .hero {
        background: linear-gradient(135deg, #0f3d5c 0%, #14283f 100%);
        border-radius: 14px;
        padding: 2rem 2.2rem;
        margin-bottom: 1.6rem;
        color: #f5f7fa;
        box-shadow: 0 6px 18px rgba(0,0,0,0.18);
    }
    .hero h1 {margin: 0 0 0.3rem 0; font-size: 1.9rem; color: #ffffff;}
    .hero p {margin: 0; color: #cdd8e3; font-size: 1.02rem;}
    .hero .badge {
        display: inline-block; background: #c9a227; color: #14283f; font-weight: 700;
        border-radius: 20px; padding: 0.15rem 0.75rem; font-size: 0.75rem; margin-bottom: 0.6rem;
        letter-spacing: 0.03em; text-transform: uppercase;
    }

    .kpi-card {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128,128,128,0.25);
        border-left: 4px solid #c9a227;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        height: 100%;
    }
    .kpi-card .kpi-label {font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; opacity: 0.7;}
    .kpi-card .kpi-value {font-size: 1.55rem; font-weight: 700; margin-top: 0.15rem;}
    .kpi-card .kpi-sub {font-size: 0.75rem; opacity: 0.6; margin-top: 0.1rem;}

    .step-pill {
        display: inline-flex; align-items: center; gap: 0.4rem;
        border-radius: 20px; padding: 0.3rem 0.9rem; font-size: 0.82rem; font-weight: 600;
        margin-right: 0.4rem; margin-bottom: 0.3rem; border: 1px solid rgba(128,128,128,0.3);
    }
    .step-pill.active {background: #0f3d5c; color: #fff; border-color: #0f3d5c;}
    .step-pill.done {background: rgba(201,162,39,0.18); color: #c9a227; border-color: #c9a227;}
    .step-pill.todo {opacity: 0.55;}

    .risk-badge {
        display: inline-block; padding: 0.15rem 0.6rem; border-radius: 12px;
        font-size: 0.78rem; font-weight: 700; color: #fff;
    }
    .risk-high {background: #b3261e;}
    .risk-med {background: #c9871a;}
    .risk-low {background: #4c7a3f;}

    .method-note {
        background: var(--secondary-background-color);
        border-left: 3px solid #0f3d5c;
        border-radius: 6px;
        padding: 0.6rem 0.9rem;
        font-size: 0.87rem;
        margin-bottom: 0.8rem;
    }

    .app-footer {
        margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid rgba(128,128,128,0.25);
        font-size: 0.78rem; opacity: 0.65;
    }
</style>
""", unsafe_allow_html=True)


def kpi_card(label, value, sub=""):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


def risk_badge(score: int) -> str:
    if score >= 3:
        cls, label = "risk-high", "HIGH"
    elif score == 2:
        cls, label = "risk-med", "MEDIUM"
    else:
        cls, label = "risk-low", "LOW"
    return f'<span class="risk-badge {cls}">{label} ({score})</span>'


# ---------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------
st.markdown("""
<div class="hero">
    <div class="badge">AICA Level 2 Capstone</div>
    <h1>\U0001F50E Audit Sampling &amp; Fraud Detection Tool</h1>
    <p>Draw defensible audit samples, run automated fraud red-flag checks, and test for
    manipulated figures with Benford's Law - all from one file, no setup required.</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Sidebar: progress + global display settings
# ---------------------------------------------------------------
STEP_NAMES = ["Data", "Sampling", "Fraud Checks", "Benford's Law", "Reports"]

with st.sidebar:
    st.markdown("### Workflow")
    df_ready = 'df' in st.session_state
    sampled_ready = 'sampled_df' in st.session_state
    flagged_ready = 'flagged_df' in st.session_state
    step_status = [df_ready, sampled_ready, flagged_ready, flagged_ready, sampled_ready and flagged_ready]
    for i, name in enumerate(STEP_NAMES):
        cls = "done" if step_status[i] else "todo"
        icon = "\u2713" if step_status[i] else str(i + 1)
        st.markdown(f'<span class="step-pill {cls}">{icon} &nbsp;{name}</span><br>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Display Settings")
    compact_currency = st.toggle("Use Lakhs / Crores display (e.g. \u20b91.23 Cr)", value=False,
                                  help="Optional Indian compact currency format, alongside the standard "
                                       "\u20b912,34,567.00 grouping used everywhere else.")
    st.markdown("---")
    st.caption("Built for AICA Level 2 capstone submission. Not a certified audit product.")


def C(amount):
    return fmt_currency(amount, compact=compact_currency)


# ---------------------------------------------------------------
# STEP 1: DATA
# ---------------------------------------------------------------
st.header("Step 1 \u00b7 Get Your Data")
col_a, col_b = st.columns([2, 1])
with col_a:
    uploaded_file = st.file_uploader(
        "Upload your transaction file (CSV / XLSX / XLS)",
        type=['csv', 'xlsx', 'xls'],
        help="Any column names are fine - you'll confirm which column means what "
             "after upload. At minimum the tool needs a voucher/ID, a date, a vendor "
             "name and an amount."
    )
with col_b:
    st.write("")
    st.write("Don't have a file handy?")
    use_sample = st.button("\U0001F449 Use Built-in Sample Data", use_container_width=True)

df = None
if uploaded_file is not None:
    try:
        raw_df = load_data(uploaded_file)
        if raw_df.empty or len(raw_df.columns) == 0:
            st.error("This file has no readable data/columns. Please check the file and re-upload.")
        else:
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            suggested = suggest_column_mapping(raw_df.columns)
            needs_attention = any(suggested[f] is None for f in CORE_FIELDS)
            with st.expander(
                "\U0001F517 Confirm column mapping" + (" (needs your input)" if needs_attention else " (auto-detected - click to review)"),
                expanded=needs_attention,
            ):
                st.caption(
                    "This file's column headers don't need to match ours exactly - we've "
                    "guessed the best match for each field below. Adjust anything that "
                    "looks wrong; fields marked '\u2014 Not available \u2014' just mean the "
                    "checks that need them will be skipped."
                )
                mapping = {}
                col_options = ["\u2014 Not available \u2014"] + list(raw_df.columns)
                st.markdown("**Required for the tool to run:**")
                mcols = st.columns(4)
                for i, field in enumerate(CORE_FIELDS):
                    with mcols[i]:
                        default = suggested[field] if suggested[field] in raw_df.columns else None
                        idx = col_options.index(default) if default else 0
                        picked = st.selectbox(field, col_options, index=idx, key=f"colmap_{field}_{file_id}")
                        mapping[field] = None if picked == col_options[0] else picked

                st.markdown("**Optional (enables extra checks / nicer labels):**")
                ocols = st.columns(3)
                optional_hint = {
                    'Account_Head': "used for display only",
                    'Approver': "needed for Segregation of Duties",
                    'Raised_By': "needed for Segregation of Duties",
                }
                for i, field in enumerate(OPTIONAL_FIELDS):
                    with ocols[i]:
                        default = suggested[field] if suggested[field] in raw_df.columns else None
                        idx = col_options.index(default) if default else 0
                        picked = st.selectbox(field, col_options, index=idx, key=f"colmap_{field}_{file_id}",
                                               help=optional_hint.get(field, ""))
                        mapping[field] = None if picked == col_options[0] else picked

            missing_core = [f for f in CORE_FIELDS if mapping[f] is None]
            if missing_core:
                st.error(
                    f"Please map a column for: **{', '.join(missing_core)}** above before this "
                    f"file can be analysed - these four fields are the minimum the tool needs "
                    f"(a unique voucher/ID, a date, a vendor name and an amount)."
                )
            else:
                mapped_df = apply_column_mapping(raw_df, mapping)
                df, dropped = clean_data(mapped_df)
                if len(df) == 0:
                    st.error("Every row in this file failed validation (unparseable Date/Amount). "
                              "Please check the mapped Date and Amount columns.")
                    df = None
                else:
                    msg = f"File loaded successfully. Total usable transactions: **{len(df):,}**."
                    if dropped:
                        msg += f" ({dropped} row(s) dropped - invalid/unparseable Date or Amount.)"
                    skipped = [f for f in OPTIONAL_FIELDS if mapping[f] is None]
                    if skipped:
                        msg += f" Not mapped: {', '.join(skipped)} - related checks will be skipped."
                    st.success(msg)
    except Exception as e:
        st.error(f"Could not read this file: {e}")

if use_sample:
    df = generate_sample_data()
    st.session_state['df'] = df
    for k in ('sampled_df', 'flagged_df', 'benford_result', 'sample_method'):
        st.session_state.pop(k, None)

if df is None and 'df' in st.session_state:
    df = st.session_state['df']
elif df is not None:
    st.session_state['df'] = df

if df is not None:
    with st.expander(f"Preview data ({len(df):,} rows)", expanded=False):
        preview = df.head(10).copy()
        if 'Date' in preview.columns:
            preview['Date'] = preview['Date'].apply(fmt_date_ddmmyyyy)
        if 'Amount' in preview.columns:
            preview['Amount'] = preview['Amount'].apply(C)
        st.dataframe(preview, use_container_width=True)

    # =============================================================
    # STEP 2: SAMPLING
    # =============================================================
    st.header("Step 2 \u00b7 Audit Sampling")
    c1, c2 = st.columns(2)
    with c1:
        method = st.selectbox("Choose a sampling method", list(SAMPLING_METHOD_INFO.keys()))
        st.markdown(f'<div class="method-note">{SAMPLING_METHOD_INFO[method]}</div>', unsafe_allow_html=True)
    with c2:
        max_size = max(1, len(df))
        default_size = min(30, max_size)
        sample_size = st.number_input("Sample size", min_value=1, max_value=max_size, value=default_size)
        if max_size < 5:
            st.caption("\u26a0\ufe0f Very small population - sample results may not be statistically meaningful.")

    if st.button("Run Sampling", type="primary"):
        mus_info = None
        if method == "Random Sampling":
            sampled_df = random_sampling(df, sample_size)
        elif method == "Systematic Sampling":
            sampled_df = systematic_sampling(df, sample_size)
        elif method == "Monetary Unit Sampling (PPS)":
            sampled_df, mus_info = monetary_unit_sampling(df, sample_size)
        else:
            sampled_df = stratified_sampling(df, sample_size)
        st.session_state['sampled_df'] = sampled_df
        st.session_state['sample_method'] = method
        st.session_state['mus_info'] = mus_info

    if 'sampled_df' in st.session_state:
        sdf = st.session_state['sampled_df']
        if len(sdf) == 0:
            st.warning("The sampling run produced zero rows (e.g. no positive-amount transactions "
                       "available for Monetary Unit Sampling). Try another method or check the data.")
        else:
            st.write(f"Sampled **{len(sdf):,}** transactions using **{st.session_state.get('sample_method','')}**:")
            mus_info = st.session_state.get('mus_info')
            if mus_info and mus_info.get('interval', 0) > 0:
                st.caption(
                    f"Sampling interval: {C(mus_info['interval'])} per selection point \u00b7 "
                    f"{mus_info['certain_selections']} transaction(s) were 'certain selections' "
                    f"(amount exceeded the sampling interval)."
                    + (f" \u00b7 {mus_info['excluded_non_positive']} zero/negative-amount row(s) excluded."
                       if mus_info.get('excluded_non_positive') else "")
                )
            show = sdf.copy()
            if 'Date' in show.columns:
                show['Date'] = show['Date'].apply(fmt_date_ddmmyyyy)
            if 'Amount' in show.columns:
                show['Amount'] = show['Amount'].apply(C)
            st.dataframe(show, use_container_width=True)
else:
    st.info("\U0001F446 Upload a file or click 'Use Built-in Sample Data' above to get started.")


# =====================================================================
# STEP 3 & 4: FRAUD DETECTION + BENFORD'S LAW
# =====================================================================
if df is not None:
    st.header("Step 3 \u00b7 Fraud / Red-Flag Detection")

    with st.expander("What does each check look for?", expanded=False):
        for name, desc in FRAUD_CHECK_INFO.items():
            st.markdown(f"**{name}** - {desc}")

    fc1, fc2 = st.columns(2)
    with fc1:
        threshold_limit = st.number_input(
            "Approval threshold limit (\u20b9) for Threshold Dodging check",
            value=50000, step=1000, min_value=0)
    with fc2:
        outlier_method = st.selectbox(
            "Outlier detection method",
            ["MAD (Robust, recommended)", "IQR (Robust)", "Z-Score (Classic)"],
            help="MAD and IQR are based on the median/quartiles, so a few extreme values can't "
                 "distort the very thresholds used to catch them (the 'masking effect' that "
                 "affects the classic mean/std-dev Z-score method)."
        )
    outlier_method_key = {"MAD (Robust, recommended)": "MAD", "IQR (Robust)": "IQR",
                           "Z-Score (Classic)": "Z"}[outlier_method]

    available_checks, unavailable_checks = available_fraud_checks(df)
    if unavailable_checks:
        skipped_desc = "; ".join(
            f"**{name}** (needs {', '.join(cols)})" for name, cols in unavailable_checks.items()
        )
        st.caption(f"ℹ️ Not available for this file - column(s) not mapped: {skipped_desc}.")
    selected_checks = st.multiselect("Select which checks to run", available_checks, default=available_checks)

    if st.button("Run Fraud Detection", type="primary"):
        flagged_df = run_all_fraud_checks(
            df, threshold_limit=threshold_limit, selected_checks=selected_checks,
            outlier_method=outlier_method_key,
        )
        st.session_state['flagged_df'] = flagged_df

    if 'flagged_df' in st.session_state:
        flagged_df = st.session_state['flagged_df']
        flagged_pct = (len(flagged_df) / len(df) * 100) if len(df) else 0

        k1, k2, k3, k4 = st.columns(4)
        with k1: kpi_card("Total Transactions", f"{len(df):,}")
        with k2: kpi_card("Flagged Transactions", f"{len(flagged_df):,}")
        with k3: kpi_card("Flagged %", f"{flagged_pct:.2f}%")
        with k4: kpi_card("Sample Size", f"{len(st.session_state.get('sampled_df', [])):,}" if 'sampled_df' in st.session_state else "-")

        st.write("")
        if len(flagged_df) == 0:
            st.success("\u2705 No anomalies found with the selected checks on this population.")
        else:
            st.write("Flagged transactions (sorted by Risk Score, highest first):")
            disp = flagged_df.copy()
            disp['Risk'] = disp['Risk_Score'].apply(risk_badge)
            if 'Date' in disp.columns:
                disp['Date'] = disp['Date'].apply(fmt_date_ddmmyyyy)
            if 'Amount' in disp.columns:
                disp['Amount'] = disp['Amount'].apply(C)
            cols_order = [c for c in ['Voucher_No', 'Date', 'Vendor_Name', 'Amount', 'Account_Head',
                                       'Approver', 'Raised_By', 'Risk', 'Flag_Reason'] if c in disp.columns]
            st.markdown(
                disp[cols_order].to_html(escape=False, index=False, classes="flagged-table"),
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

            reason_counts = flagged_df['Flag_Reason'].str.split(', ').explode().value_counts()
            gc1, gc2 = st.columns(2)
            with gc1:
                fig_reasons = px.bar(
                    x=reason_counts.values, y=reason_counts.index, orientation='h',
                    labels={'x': 'Number of Transactions', 'y': ''},
                    title="Flagged Transactions by Reason",
                    color_discrete_sequence=['#0f3d5c'],
                )
                fig_reasons.update_layout(height=380, margin=dict(t=50, b=20, l=10, r=10),
                                           paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_reasons, use_container_width=True)
            with gc2:
                fig_amt = px.histogram(
                    df, x='Amount', nbins=40, title="Distribution of Transaction Amounts",
                    color_discrete_sequence=['#c9a227'],
                )
                fig_amt.update_layout(height=380, margin=dict(t=50, b=20, l=10, r=10),
                                       xaxis_title="Amount (\u20b9)", yaxis_title="Number of Transactions",
                                       paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_amt, use_container_width=True)

        # =========================================================
        # STEP 4: BENFORD'S LAW
        # =========================================================
        st.header("Step 4 \u00b7 Benford's Law Analysis")
        benford_result = check_benfords_law(df)
        st.session_state['benford_result'] = benford_result

        if benford_result.get('insufficient_data'):
            st.info(f"Only {benford_result['n']} positive-amount transaction(s) available - "
                    "Benford's Law needs a larger population (typically 100+ values spanning "
                    "several orders of magnitude) to give a statistically meaningful result. "
                    "Skipping this analysis for now.")
        else:
            bc1, bc2, bc3 = st.columns(3)
            with bc1: kpi_card("Chi-Square Statistic", f"{benford_result['chi_square_stat']:.2f}")
            with bc2: kpi_card("Critical Value (95%)", f"{benford_result['critical_value']}")
            with bc3: kpi_card("Sample Size (n)", f"{benford_result['n']:,}")

            st.write("")
            if benford_result['significant_deviation']:
                st.warning("\u26a0\ufe0f Significant deviation from Benford's Law detected - the amounts "
                           "may not be naturally occurring (possible manipulation). This is a "
                           "screening signal, not proof - it warrants deeper investigation.")
            else:
                st.success("\u2705 No significant deviation from Benford's Law - amounts appear naturally distributed.")

            fig = plot_benford_chart(benford_result['actual_distribution'], benford_result['expected_distribution'])
            st.plotly_chart(fig, use_container_width=True)

    # =================================================================
    # STEP 5: DOWNLOAD REPORTS
    # =================================================================
    st.header("Step 5 \u00b7 Download Reports")
    if 'flagged_df' in st.session_state and 'sampled_df' in st.session_state:
        excel_buf = export_to_excel_bytes(
            st.session_state['flagged_df'], st.session_state['sampled_df'], df)
        pdf_buf = generate_pdf_summary_bytes(
            total_transactions=len(df),
            flagged_count=len(st.session_state['flagged_df']),
            sample_method=st.session_state.get('sample_method', 'N/A'),
            sample_size=len(st.session_state['sampled_df']),
            benford_result=st.session_state.get('benford_result'),
            top_flags=st.session_state['flagged_df'],
        )
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("\u2b07\ufe0f Download Excel Report", data=excel_buf,
                                file_name="audit_report.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True)
        with d2:
            st.download_button("\u2b07\ufe0f Download PDF Summary", data=pdf_buf,
                                file_name="summary_report.pdf", mime="application/pdf",
                                use_container_width=True)
    else:
        st.info("Run both 'Run Sampling' (Step 2) and 'Run Fraud Detection' (Step 3) above to unlock report downloads.")

# ---------------------------------------------------------------
# Footer
# ---------------------------------------------------------------
st.markdown("""
<div class="app-footer">
    Audit Sampling &amp; Fraud Detection Tool &middot; AICA Level 2 Capstone Project &middot;
    This is a training/capstone tool, not a certified audit product. Findings must be
    corroborated by a qualified auditor before being relied upon in a statutory audit.
</div>
""", unsafe_allow_html=True)
