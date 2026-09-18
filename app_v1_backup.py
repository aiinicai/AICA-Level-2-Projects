"""
=====================================================================
 AUDIT SAMPLING & FRAUD DETECTION TOOL
 Capstone Project - AICA Level 2
=====================================================================
 HOW TO RUN THIS FILE (only 2 things needed):
   1) Make sure Python is installed on your computer.
   2) Open Command Prompt in the folder where this file is saved,
      and type:   python app.py
      Then press Enter.

 That's it. This file will automatically:
   - Install every library it needs (only on the first run)
   - Launch the Streamlit web app in your browser automatically

 No manual pip install. No virtual environment. No folder setup.
 Just one file, one command.
=====================================================================
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
    "matplotlib": "matplotlib",
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
# ---------------------------------------------------------------
if os.environ.get("AUDIT_APP_LAUNCHED") != "1":
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
import matplotlib.pyplot as plt
import streamlit as st
from fpdf import FPDF

# ---------------------------------------------------------------
# 1. SAMPLE DATA GENERATOR (used when user has no file to upload)
# ---------------------------------------------------------------
def generate_sample_data(num_rows=500, seed=42):
    random.seed(seed)
    np.random.seed(seed)

    vendor_names = [f"Vendor_{i}" for i in range(1, 26)]
    approvers = ['Rahul Sharma', 'Priya Singh', 'Amit Verma', 'Sunita Rao', 'Vikram Nair']
    start_date = datetime(2024, 4, 1)

    # Log-uniform amounts across several orders of magnitude -> realistic,
    # naturally follows Benford's Law before anomalies are planted.
    log_min, log_max = np.log10(100), np.log10(999999)
    log_amounts = np.random.uniform(log_min, log_max, num_rows)
    amounts = np.round(10 ** log_amounts, 2)

    def random_weekday_date():
        # Genuine business transactions happen on weekdays (Mon-Fri) only.
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
        # who raised the transaction are almost always different people.
        raised_by = random.choice([a for a in approvers if a != approver])
        data.append([voucher_no, date, vendor, amount, account_head, approver, raised_by])

    df = pd.DataFrame(
        data,
        columns=['Voucher_No', 'Date', 'Vendor_Name', 'Amount',
                 'Account_Head', 'Approver', 'Raised_By']
    )

    # ---- Plant a handful of realistic anomalies so the tool has
    # something genuine to catch during a demo ----
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


# ---------------------------------------------------------------
# 2. DATA LOADING & CLEANING
# ---------------------------------------------------------------
REQUIRED_COLUMNS = ['Voucher_No', 'Date', 'Vendor_Name', 'Amount',
                     'Account_Head', 'Approver', 'Raised_By']

def load_data(uploaded_file):
    if uploaded_file.name.lower().endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    return df

def clean_data(df):
    df = df.drop_duplicates().copy()
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    if 'Amount' in df.columns:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    df = df.dropna(subset=[c for c in ['Amount', 'Date'] if c in df.columns])
    return df.reset_index(drop=True)

def validate_columns(df):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return missing


# ---------------------------------------------------------------
# 3. AUDIT SAMPLING METHODS
# ---------------------------------------------------------------
def random_sampling(df, sample_size):
    sample_size = min(sample_size, len(df))
    return df.sample(n=sample_size, random_state=42)

def systematic_sampling(df, sample_size):
    sample_size = min(sample_size, len(df))
    interval = max(1, len(df) // sample_size)
    return df.iloc[::interval].head(sample_size)

def monetary_unit_sampling(df, sample_size, amount_col='Amount'):
    sample_size = min(sample_size, len(df))
    weights = df[amount_col].clip(lower=0.01)
    weights = weights / weights.sum()
    sampled_idx = np.random.choice(df.index, size=sample_size, replace=False, p=weights)
    return df.loc[sampled_idx]

def stratified_sampling(df, sample_size, amount_col='Amount', num_strata=3):
    sample_size = min(sample_size, len(df))
    dfc = df.copy()
    try:
        dfc['Strata'] = pd.qcut(dfc[amount_col], q=num_strata, labels=False, duplicates='drop')
    except ValueError:
        dfc['Strata'] = 0
    n_groups = max(1, dfc['Strata'].nunique())
    per_stratum = max(1, sample_size // n_groups)
    parts = []
    for _, group in dfc.groupby('Strata'):
        parts.append(group.sample(min(len(group), per_stratum), random_state=42))
    result = pd.concat(parts) if parts else dfc.head(0)
    return result.drop(columns='Strata', errors='ignore')


# ---------------------------------------------------------------
# 4. FRAUD / RED-FLAG DETECTION RULES
# ---------------------------------------------------------------
def check_duplicates(df):
    mask = df.duplicated(subset=['Vendor_Name', 'Amount', 'Date'], keep=False)
    flagged = df[mask].copy()
    flagged['Flag_Reason'] = 'Duplicate Transaction'
    return flagged

def check_threshold_dodging(df, limit=50000, buffer_percent=0.03):
    lower = limit * (1 - buffer_percent)
    mask = (df['Amount'] >= lower) & (df['Amount'] < limit)
    flagged = df[mask].copy()
    flagged['Flag_Reason'] = 'Threshold Dodging'
    return flagged

def check_round_numbers(df, divisor=5000):
    mask = (df['Amount'] % divisor == 0) & (df['Amount'] > 0)
    flagged = df[mask].copy()
    flagged['Flag_Reason'] = 'Round Number Amount'
    return flagged

def check_weekend_transactions(df):
    mask = df['Date'].dt.dayofweek >= 5
    flagged = df[mask].copy()
    flagged['Flag_Reason'] = 'Weekend Transaction'
    return flagged

def check_segregation_of_duties(df):
    if 'Approver' not in df.columns or 'Raised_By' not in df.columns:
        return df.iloc[0:0].copy()
    mask = df['Approver'] == df['Raised_By']
    flagged = df[mask].copy()
    flagged['Flag_Reason'] = 'Segregation of Duties Violation'
    return flagged

def check_outliers(df, amount_col='Amount', z_threshold=3):
    mean = df[amount_col].mean()
    std = df[amount_col].std()
    if std == 0 or pd.isna(std):
        return df.iloc[0:0].copy()
    dfx = df.copy()
    dfx['Z'] = (dfx[amount_col] - mean) / std
    flagged = dfx[dfx['Z'].abs() > z_threshold].copy()
    flagged['Flag_Reason'] = 'Statistical Outlier'
    return flagged.drop(columns='Z')

def run_all_fraud_checks(df, threshold_limit=50000, selected_checks=None):
    all_checks = {
        'Duplicates': lambda d: check_duplicates(d),
        'Threshold Dodging': lambda d: check_threshold_dodging(d, limit=threshold_limit),
        'Round Numbers': lambda d: check_round_numbers(d),
        'Weekend Transactions': lambda d: check_weekend_transactions(d),
        'Segregation of Duties': lambda d: check_segregation_of_duties(d),
        'Statistical Outliers': lambda d: check_outliers(d),
    }
    if selected_checks is None:
        selected_checks = list(all_checks.keys())

    pieces = [all_checks[name](df) for name in selected_checks if name in all_checks]
    pieces = [p for p in pieces if len(p) > 0]

    if not pieces:
        return df.iloc[0:0].copy().assign(Risk_Score=[], Flag_Reason=[])

    combined = pd.concat(pieces)
    risk_score = combined.groupby('Voucher_No').size().rename('Risk_Score')
    reasons = combined.groupby('Voucher_No')['Flag_Reason'].apply(lambda x: ', '.join(sorted(set(x))))
    base = combined.drop_duplicates(subset='Voucher_No').drop(columns='Flag_Reason')
    final = base.merge(risk_score, on='Voucher_No').merge(reasons, on='Voucher_No')
    final = final.sort_values('Risk_Score', ascending=False).reset_index(drop=True)
    return final


# ---------------------------------------------------------------
# 5. BENFORD'S LAW ANALYSIS (no scipy dependency needed)
# ---------------------------------------------------------------
CHI_SQUARE_CRITICAL_VALUE_DF8_ALPHA05 = 15.507  # standard statistical table value

def _first_digit(x):
    s = str(abs(x)).replace('.', '').lstrip('0')
    return int(s[0]) if s else None

def check_benfords_law(df, amount_col='Amount'):
    vals = df[amount_col].dropna()
    vals = vals[vals > 0]
    digits = vals.apply(_first_digit).dropna()
    actual_counts = digits.value_counts().reindex(range(1, 10), fill_value=0).sort_index()

    total = len(digits)
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
    }

def plot_benford_chart(actual_dist, expected_dist):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    digits = list(range(1, 10))
    ax.bar([d - 0.2 for d in digits], actual_dist.values, width=0.4, label='Actual', color='#1f77b4')
    ax.bar([d + 0.2 for d in digits], expected_dist.values, width=0.4, label='Expected (Benford)', color='#ff7f0e')
    ax.set_xlabel('Leading Digit')
    ax.set_ylabel('Count of Transactions')
    ax.set_title("Benford's Law: Actual vs Expected First-Digit Distribution")
    ax.set_xticks(digits)
    ax.legend()
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------
# 6. REPORT GENERATION (all in-memory, no disk folders needed)
# ---------------------------------------------------------------
def export_to_excel_bytes(flagged_df, sampled_df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        (flagged_df if len(flagged_df) else pd.DataFrame({'Message': ['No flagged transactions found']})) \
            .to_excel(writer, sheet_name='Flagged_Transactions', index=False)
        (sampled_df if len(sampled_df) else pd.DataFrame({'Message': ['No sample generated yet']})) \
            .to_excel(writer, sheet_name='Sampled_Transactions', index=False)
    buffer.seek(0)
    return buffer

def generate_pdf_summary_bytes(total_transactions, flagged_count, sample_method, benford_result=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=16)
    pdf.cell(0, 10, text="Audit Sampling & Fraud Detection - Summary Report", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("helvetica", size=12)
    pdf.cell(0, 8, text=f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, text=f"Total Transactions Analyzed: {total_transactions}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, text=f"Total Flagged Transactions: {flagged_count}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, text=f"Sampling Method Used: {sample_method}", new_x="LMARGIN", new_y="NEXT")
    if benford_result is not None:
        pdf.ln(4)
        pdf.set_font("helvetica", size=13)
        pdf.cell(0, 8, text="Benford's Law Analysis", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", size=12)
        pdf.cell(0, 8, text=f"Chi-Square Statistic: {benford_result['chi_square_stat']:.2f}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, text=f"Critical Value (95% confidence): {benford_result['critical_value']}", new_x="LMARGIN", new_y="NEXT")
        verdict = "Significant deviation detected (possible manipulation)" \
            if benford_result['significant_deviation'] else "No significant deviation (amounts look natural)"
        pdf.multi_cell(0, 8, text=f"Conclusion: {verdict}")
    out = pdf.output()
    return io.BytesIO(bytes(out))


# =====================================================================
# 7. STREAMLIT USER INTERFACE
# =====================================================================
st.set_page_config(page_title="Audit Sampling & Fraud Detection Tool", layout="wide")
st.title("🔍 Audit Sampling & Fraud Detection Tool")
st.caption("AICA Level 2 Capstone Project")
st.markdown(
    "Upload a transaction file (CSV/Excel) **or** use the built-in sample data "
    "to try out audit sampling and automated fraud red-flag detection."
)

# ---- Data source selection ----
st.header("Step 0: Get Your Data")
col_a, col_b = st.columns(2)
with col_a:
    uploaded_file = st.file_uploader(
        "Upload your transaction file",
        type=['csv', 'xlsx', 'xls'],
        help="Required columns: Voucher_No, Date, Vendor_Name, Amount, Account_Head, Approver, Raised_By"
    )
with col_b:
    st.write("Don't have a file handy?")
    use_sample = st.button("👉 Use Built-in Sample Data Instead")

df = None
if uploaded_file is not None:
    try:
        raw_df = load_data(uploaded_file)
        missing_cols = validate_columns(raw_df)
        if missing_cols:
            st.error(f"Your file is missing required columns: {missing_cols}. "
                     f"Please fix the file or use the sample data instead.")
        else:
            df = clean_data(raw_df)
            st.success(f"File loaded and cleaned successfully. Total transactions: {len(df)}")
    except Exception as e:
        st.error(f"Could not read the file: {e}")

if use_sample:
    df = generate_sample_data()
    st.session_state['df'] = df

if df is None and 'df' in st.session_state:
    df = st.session_state['df']
elif df is not None:
    st.session_state['df'] = df

if df is not None:
    st.dataframe(df.head(10), use_container_width=True)

    # ---- Sampling ----
    st.header("Step 1: Audit Sampling")
    c1, c2 = st.columns(2)
    with c1:
        method = st.selectbox(
            "Choose a sampling method",
            ["Random Sampling", "Systematic Sampling", "Monetary Unit Sampling", "Stratified Sampling"]
        )
    with c2:
        sample_size = st.number_input("Sample size", min_value=5, max_value=max(5, len(df)), value=min(30, len(df)))

    if st.button("Run Sampling"):
        if method == "Random Sampling":
            sampled_df = random_sampling(df, sample_size)
        elif method == "Systematic Sampling":
            sampled_df = systematic_sampling(df, sample_size)
        elif method == "Monetary Unit Sampling":
            sampled_df = monetary_unit_sampling(df, sample_size)
        else:
            sampled_df = stratified_sampling(df, sample_size)
        st.session_state['sampled_df'] = sampled_df
        st.session_state['sample_method'] = method

    if 'sampled_df' in st.session_state:
        st.write(f"Sampled {len(st.session_state['sampled_df'])} transactions "
                 f"using **{st.session_state.get('sample_method','')}**:")
        st.dataframe(st.session_state['sampled_df'], use_container_width=True)

    # ---- Fraud Detection ----
    st.header("Step 2: Fraud / Red-Flag Detection")
    threshold_limit = st.number_input("Approval threshold limit (₹) for Threshold Dodging check",
                                       value=50000, step=1000)
    all_check_names = ['Duplicates', 'Threshold Dodging', 'Round Numbers',
                        'Weekend Transactions', 'Segregation of Duties', 'Statistical Outliers']
    selected_checks = st.multiselect("Select which checks to run", all_check_names, default=all_check_names)

    if st.button("Run Fraud Detection"):
        flagged_df = run_all_fraud_checks(df, threshold_limit=threshold_limit, selected_checks=selected_checks)
        st.session_state['flagged_df'] = flagged_df

    if 'flagged_df' in st.session_state:
        flagged_df = st.session_state['flagged_df']
        m1, m2 = st.columns(2)
        m1.metric("Total Transactions", len(df))
        m2.metric("Flagged Transactions", len(flagged_df))

        if len(flagged_df) == 0:
            st.success("✅ No anomalies found with the selected checks.")
        else:
            st.write("Flagged transactions (sorted by Risk Score, highest first):")
            st.dataframe(flagged_df, use_container_width=True)

        # ---- Benford's Law ----
        st.subheader("📈 Benford's Law Analysis")
        benford_result = check_benfords_law(df)
        st.session_state['benford_result'] = benford_result
        bc1, bc2 = st.columns(2)
        bc1.metric("Chi-Square Statistic", f"{benford_result['chi_square_stat']:.2f}")
        bc2.metric("Critical Value (95% confidence)", f"{benford_result['critical_value']}")
        if benford_result['significant_deviation']:
            st.warning("⚠️ Significant deviation from Benford's Law detected — the amounts may not "
                       "be naturally occurring (possible manipulation). Worth deeper investigation.")
        else:
            st.success("✅ No significant deviation from Benford's Law — amounts appear naturally distributed.")
        fig = plot_benford_chart(benford_result['actual_distribution'], benford_result['expected_distribution'])
        st.pyplot(fig)

    # ---- Downloads ----
    st.header("Step 3: Download Reports")
    if 'flagged_df' in st.session_state and 'sampled_df' in st.session_state:
        excel_buf = export_to_excel_bytes(st.session_state['flagged_df'], st.session_state['sampled_df'])
        pdf_buf = generate_pdf_summary_bytes(
            total_transactions=len(df),
            flagged_count=len(st.session_state['flagged_df']),
            sample_method=st.session_state.get('sample_method', 'N/A'),
            benford_result=st.session_state.get('benford_result')
        )
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("⬇️ Download Excel Report", data=excel_buf,
                                file_name="audit_report.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with d2:
            st.download_button("⬇️ Download PDF Summary", data=pdf_buf,
                                file_name="summary_report.pdf", mime="application/pdf")
    else:
        st.info("Run both 'Run Sampling' and 'Run Fraud Detection' above to unlock report downloads.")

else:
    st.info("👆 Upload a file or click 'Use Built-in Sample Data' above to get started.")
