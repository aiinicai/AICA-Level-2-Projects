"""
app.py
Audit Analytics & Journal Entry Testing Tool
Designed for Indian CA Firms complying with SA 240, SA 315, SA 330 and CARO 2020.
Runs 100% locally and offline on Windows.
"""

from datetime import datetime, time
import io
import pandas as pd
import streamlit as st

from analytics import (
    DEFAULT_AUDIT_KEYWORDS,
    DEFAULT_SENSITIVE_ACCOUNTS,
    generate_audit_sample,
    perform_benford_analysis,
    run_journal_entry_tests,
    validate_materiality,
)
from ingestion import (
    CANONICAL_COLUMNS,
    generate_synthetic_audit_dataset,
    load_file,
    process_and_standardize_data,
    suggest_column_mappings,
)
from memo import generate_pdf_conclusion_memo
from workpapers import build_excel_workpaper

# Set Streamlit Page Config
st.set_page_config(
    page_title="Audit Analytics & JE Testing Tool",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CA-Themed CSS
st.markdown(
    """
    <style>
    .main-header {
        font-size: 24px;
        font-weight: 700;
        color: #1B365D;
        margin-bottom: 2px;
    }
    .sub-header {
        font-size: 13px;
        color: #555555;
        margin-bottom: 16px;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 12px;
        text-align: center;
    }
    .metric-value {
        font-size: 20px;
        font-weight: 700;
        color: #1B365D;
    }
    .metric-label {
        font-size: 11px;
        color: #64748B;
        text-transform: uppercase;
        font-weight: 600;
    }
    .badge-high {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .badge-med {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .badge-low {
        background-color: #DCFCE7;
        color: #166534;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Initialize Session State
if "raw_df" not in st.session_state:
    st.session_state.raw_df = None
if "std_df" not in st.session_state:
    st.session_state.std_df = None
if "diagnostics" not in st.session_state:
    st.session_state.diagnostics = None
if "flags_df" not in st.session_state:
    st.session_state.flags_df = None
if "sample_df" not in st.session_state:
    st.session_state.sample_df = None
if "benford_result" not in st.session_state:
    st.session_state.benford_result = None
if "review_records" not in st.session_state:
    st.session_state.review_records = {}


# =====================================================================
# SIDEBAR: Engagement Setup & Materiality Configuration
# =====================================================================
st.sidebar.markdown("### ⚖️ Engagement Setup")
company_name = st.sidebar.text_input(
    "Company / Entity Name", value="Apex Manufacturing India Ltd"
)
engagement_name = st.sidebar.text_input(
    "Engagement Title", value="Statutory Audit Under Companies Act 2013"
)

fy_options = ["FY 2023-24", "FY 2024-25", "FY 2022-23", "Custom FY"]
fy_selected = st.sidebar.selectbox("Financial Year (Apr - Mar)", fy_options)

fy_year_map = {
    "FY 2023-24": (2023, datetime(2023, 4, 1), datetime(2024, 3, 31)),
    "FY 2024-25": (2024, datetime(2024, 4, 1), datetime(2025, 3, 31)),
    "FY 2022-23": (2022, datetime(2022, 4, 1), datetime(2023, 3, 31)),
    "Custom FY": (2023, datetime(2023, 4, 1), datetime(2024, 3, 31)),
}
fy_year_num, fy_start_dt, fy_end_dt = fy_year_map[fy_selected]

col_s1, col_s2 = st.sidebar.columns(2)
with col_s1:
    prepared_by = st.text_input("Prepared By", value="CA Sneha Sharma")
with col_s2:
    reviewed_by = st.text_input("Reviewed By", value="CA Rajesh Verma, FCA")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Materiality Benchmarks (SA 320)")
om_input = st.sidebar.number_input(
    "Overall Materiality (OM) ₹",
    value=10000000.0,
    step=500000.0,
    format="%.2f",
    help="Materiality for the financial statements as a whole.",
)
pm_input = st.sidebar.number_input(
    "Performance Materiality (PM) ₹",
    value=7000000.0,
    step=500000.0,
    format="%.2f",
    help="Cutoff for testing high-value JEs (typically 50-75% of OM).",
)
ctt_input = st.sidebar.number_input(
    "Clearly Trivial Threshold (CTT) ₹",
    value=350000.0,
    step=50000.0,
    format="%.2f",
    help="Threshold below which misstatements are clearly trivial (typically 1-5% of OM).",
)

# Materiality Validation Banner
mat_val = validate_materiality(om_input, pm_input, ctt_input)
if not mat_val["is_valid"]:
    for err in mat_val["errors"]:
        st.sidebar.error(f"⚠️ {err}")
elif mat_val["warnings"]:
    for w in mat_val["warnings"]:
        st.sidebar.warning(f"ℹ️ {w}")
else:
    st.sidebar.success("✅ Materiality hierarchy is valid.")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Standard On Auditing (SA) 240, SA 315, SA 330 & CARO 2020 Compliance Engine."
)
st.sidebar.caption("🔒 100% Offline Local Processing - No External API Calls.")


# =====================================================================
# MAIN WINDOW: Title & Navigation Tabs
# =====================================================================
st.markdown(
    '<div class="main-header">Audit Analytics & Journal Entry Testing Tool</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="sub-header">Statutory Audit Platform for Indian CA Firms | SA 240 Management Override & Fraud Risk Testing</div>',
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4 = st.tabs([
    "📁 1. Data Ingestion & Mapping",
    "🔍 2. JE Testing & Benford Analysis",
    "📋 3. Audit Sampling & Review",
    "📑 4. Workpapers & Conclusion Memo",
])


# =====================================================================
# TAB 1: DATA INGESTION & MAPPING
# =====================================================================
with tab1:
    st.markdown("#### Step 1: Upload General Ledger / Journal Voucher Dump")
    st.markdown(
        "Upload client exported General Ledger or Journal Voucher dump (Excel/CSV) from **Tally Prime, Zoho Books, SAP, Oracle, Busy**, or load synthetic test data."
    )

    col_up1, col_up2 = st.columns([3, 1])
    with col_up1:
        uploaded_file = st.file_uploader(
            "Upload Ledger File (.xlsx, .xls, .csv)", type=["xlsx", "xls", "csv"]
        )
    with col_up2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("⚡ Load Synthetic Data", use_container_width=True):
            with st.spinner("Generating authentic Indian GL audit dataset..."):
                syn_df = generate_synthetic_audit_dataset(
                    fy_year=fy_year_num, num_entries=350
                )
                st.session_state.raw_df = syn_df
                st.success("✅ Synthetic GL dataset (350+ entries) loaded successfully!")

    if uploaded_file is not None:
        try:
            f_ext = uploaded_file.name.split(".")[-1]
            raw_data = load_file(uploaded_file, file_type=f_ext)
            st.session_state.raw_df = raw_data
            st.success(f"✅ Loaded {uploaded_file.name} ({len(raw_data)} rows).")
        except Exception as e:
            st.error(f"Error loading file: {e}")

    # Column Mapping Section
    if st.session_state.raw_df is not None:
        raw_df = st.session_state.raw_df
        st.markdown("---")
        st.markdown("#### Column Mapping Assistant")
        st.caption(
            "Verify and confirm column assignments. Heuristic auto-mapping has detected likely columns from accounting software headers."
        )

        columns_list = [None] + list(raw_df.columns)
        suggested = suggest_column_mappings(list(raw_df.columns))

        map_cols_1, map_cols_2, map_cols_3 = st.columns(3)
        user_mapping = {}

        with map_cols_1:
            for k in ["voucher_date", "posting_date", "voucher_number"]:
                label = CANONICAL_COLUMNS[k]
                default_idx = (
                    columns_list.index(suggested[k])
                    if suggested.get(k) in columns_list
                    else 0
                )
                user_mapping[k] = st.selectbox(
                    f"{label} *",
                    options=columns_list,
                    index=default_idx,
                    key=f"map_{k}",
                )

        with map_cols_2:
            for k in ["account_name", "debit", "credit"]:
                label = CANONICAL_COLUMNS[k]
                default_idx = (
                    columns_list.index(suggested[k])
                    if suggested.get(k) in columns_list
                    else 0
                )
                user_mapping[k] = st.selectbox(
                    f"{label} *",
                    options=columns_list,
                    index=default_idx,
                    key=f"map_{k}",
                )

        with map_cols_3:
            for k in ["narration", "created_by", "approved_by", "voucher_type"]:
                label = CANONICAL_COLUMNS[k]
                default_idx = (
                    columns_list.index(suggested[k])
                    if suggested.get(k) in columns_list
                    else 0
                )
                user_mapping[k] = st.selectbox(
                    f"{label}",
                    options=columns_list,
                    index=default_idx,
                    key=f"map_{k}",
                )

        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("🚀 Process & Reconcile Data", type="primary"):
            with st.spinner("Standardizing rows and verifying trial balance reconciliation..."):
                std_data, diag = process_and_standardize_data(
                    raw_df, user_mapping, fy_start=fy_start_dt, fy_end=fy_end_dt
                )
                st.session_state.std_df = std_data
                st.session_state.diagnostics = diag
                st.success("✅ Data standardization and integrity checks completed!")

    # Data Integrity & Reconciliation Card
    if st.session_state.diagnostics is not None and st.session_state.std_df is not None:
        diag = st.session_state.diagnostics
        std_df = st.session_state.std_df

        st.markdown("---")
        st.markdown("#### Population Integrity & Debit-Credit Reconciliation")

        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.metric("Total Records Imported", f"{diag['total_rows']:,}")
        with m2:
            st.metric("Total Debit Amount", f"₹ {diag['total_debit']:,.2f}")
        with m3:
            st.metric("Total Credit Amount", f"₹ {diag['total_credit']:,.2f}")
        with m4:
            st.metric("Net Difference", f"₹ {diag['difference']:,.2f}")
        with m5:
            if diag["is_balanced"]:
                st.markdown(
                    "<div class='metric-card'><div class='metric-label'>Status</div><div class='metric-value' style='color:#166534;'>BALANCED ✅</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div class='metric-card'><div class='metric-label'>Status</div><div class='metric-value' style='color:#991B1B;'>DISCREPANCY ❌</div></div>",
                    unsafe_allow_html=True,
                )

        # Integrity Diagnostics Sub-Cards
        st.markdown("<br/>", unsafe_allow_html=True)
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.info(f"Invalid / Unparseable Dates: **{diag['invalid_dates_count']}**")
        with s2:
            st.info(f"Duplicate Row Lines: **{diag['duplicate_rows_count']}**")
        with s3:
            st.info(f"Unbalanced Vouchers (Dr != Cr): **{diag['unbalanced_vouchers_count']}**")
        with s4:
            st.info(f"Vouchers Outside FY Dates: **{diag['out_of_fy_count']}**")

        with st.expander("🔍 View Imported Data Preview (First 50 Rows with Source Row Index)", expanded=False):
            preview_cols = [
                "source_row_index",
                "Voucher Number",
                "parsed_voucher_date",
                "Account/Ledger Name",
                "parsed_debit",
                "parsed_credit",
                "Narration",
                "Created By",
                "Approved By",
            ]
            st.dataframe(
                std_df[preview_cols].head(50),
                use_container_width=True,
                hide_index=True,
            )


# =====================================================================
# TAB 2: JE TESTING & BENFORD ANALYSIS
# =====================================================================
with tab2:
    if st.session_state.std_df is None:
        st.warning("⚠️ Please complete Step 1 (Data Ingestion & Reconciliation) first.")
    else:
        st.markdown("#### Step 2: Journal Entry Red-Flag Tests (SA 240 / SA 330)")
        st.markdown(
            "Configure audit test criteria and run automated analytics to detect high-risk anomalies, management override indicators, and statistical outliers."
        )

        with st.expander("⚙️ Configure Audit Test Parameters & Thresholds", expanded=False):
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                b_start = st.time_input("Business Hours Start", value=time(9, 0))
                b_end = st.time_input("Business Hours End", value=time(19, 0))
                round_options = st.multiselect(
                    "Round-Value Multiples (₹)",
                    options=[50000.0, 100000.0, 500000.0, 1000000.0, 2500000.0],
                    default=[100000.0, 500000.0, 1000000.0],
                )
            with t_col2:
                auth_thresh = st.multiselect(
                    "Authorization Thresholds (₹)",
                    options=[250000.0, 500000.0, 1000000.0, 2500000.0, 5000000.0],
                    default=[500000.0, 1000000.0, 2500000.0, 5000000.0],
                )
                margin_pct = st.slider("Threshold Margin Window (%)", 1.0, 15.0, 5.0)

            c_col1, c_col2 = st.columns(2)
            with c_col1:
                custom_kw_input = st.text_area(
                    "Suspicious Audit Keywords (Comma-separated)",
                    value=", ".join(DEFAULT_AUDIT_KEYWORDS),
                )
            with c_col2:
                custom_sens_input = st.text_area(
                    "Sensitive / High-Risk Account Patterns (Comma-separated)",
                    value=", ".join(DEFAULT_SENSITIVE_ACCOUNTS),
                )

            # Test Toggles
            st.markdown("##### Active Test Toggles")
            chk_cols = st.columns(5)
            active_tests = {}
            test_names = [
                ("test_1", "1. Sunday Postings"),
                ("test_2", "2. Off-Hours"),
                ("test_3", "3. Backdated Cutoff"),
                ("test_4", "4. Round Values"),
                ("test_5", "5. Below Threshold"),
                ("test_6", "6. Blank/Generic"),
                ("test_7", "7. Audit Keywords"),
                ("test_8", "8. Exceeding PM"),
                ("test_9", "9. Sensitive A/cs"),
                ("test_10", "10. Admin Anomaly"),
            ]
            for i, (tid, tlabel) in enumerate(test_names):
                with chk_cols[i % 5]:
                    active_tests[tid] = st.checkbox(tlabel, value=True, key=f"chk_{tid}")

        # Execute Test Button
        if st.button("⚡ Run Journal Entry Tests & Benford Analysis", type="primary"):
            kw_list = [k.strip() for k in custom_kw_input.split(",") if k.strip()]
            sens_list = [s.strip() for s in custom_sens_input.split(",") if s.strip()]

            with st.spinner("Executing 10 audit red-flag tests..."):
                enriched_df, flags_df = run_journal_entry_tests(
                    st.session_state.std_df,
                    pm=pm_input,
                    start_business_hour=b_start,
                    end_business_hour=b_end,
                    round_multiples=round_options,
                    auth_thresholds=auth_thresh,
                    threshold_margin_pct=margin_pct,
                    custom_keywords=kw_list,
                    custom_sensitive_accounts=sens_list,
                    enabled_tests=active_tests,
                )
                st.session_state.std_df = enriched_df
                st.session_state.flags_df = flags_df

            with st.spinner("Computing Benford's Law First-Digit logarithmic distribution..."):
                ben_res = perform_benford_analysis(st.session_state.std_df["amount"])
                st.session_state.benford_result = ben_res

            st.success(f"✅ Testing complete! Identified {len(flags_df)} audit flags across population.")

        # Display Flag Metrics & Results
        if st.session_state.flags_df is not None:
            flags_df = st.session_state.flags_df
            high_f = len(flags_df[flags_df["risk_level"] == "High"])
            med_f = len(flags_df[flags_df["risk_level"] == "Medium"])
            low_f = len(flags_df[flags_df["risk_level"] == "Low"])
            flagged_val = flags_df["amount"].sum()
            pop_val = st.session_state.diagnostics["total_debit"]
            pop_pct = (flagged_val / pop_val * 100) if pop_val > 0 else 0.0

            st.markdown("---")
            st.markdown("#### Audit Exception Metrics")
            k1, k2, k3, k4, k5 = st.columns(5)
            with k1:
                st.metric("Total Flags Identified", len(flags_df))
            with k2:
                st.markdown(
                    f"<div class='metric-card'><div class='metric-label'>High Risk</div><div class='metric-value' style='color:#991B1B;'>{high_f}</div></div>",
                    unsafe_allow_html=True,
                )
            with k3:
                st.markdown(
                    f"<div class='metric-card'><div class='metric-label'>Medium Risk</div><div class='metric-value' style='color:#92400E;'>{med_f}</div></div>",
                    unsafe_allow_html=True,
                )
            with k4:
                st.markdown(
                    f"<div class='metric-card'><div class='metric-label'>Low Risk</div><div class='metric-value' style='color:#166534;'>{low_f}</div></div>",
                    unsafe_allow_html=True,
                )
            with k5:
                st.metric("Flagged Population Value", f"{pop_pct:.1f}%")

            # Charts Row
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("##### Exceptions by Audit Test Name")
                test_counts = flags_df["test_name"].value_counts()
                st.bar_chart(test_counts)
            with c2:
                st.markdown("##### Top Flagged Account Heads")
                acct_counts = flags_df["account_name"].value_counts().head(8)
                st.bar_chart(acct_counts)

            # Detailed Flag Explorer Table
            st.markdown("##### Flagged Transactions Explorer")
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                risk_filter = st.selectbox("Filter by Risk Level", ["All", "High", "Medium", "Low"])
            with filter_col2:
                test_filter = st.selectbox(
                    "Filter by Test Name", ["All"] + sorted(list(flags_df["test_name"].unique()))
                )

            filtered_flags = flags_df.copy()
            if risk_filter != "All":
                filtered_flags = filtered_flags[filtered_flags["risk_level"] == risk_filter]
            if test_filter != "All":
                filtered_flags = filtered_flags[filtered_flags["test_name"] == test_filter]

            st.dataframe(
                filtered_flags[[
                    "source_row_index",
                    "voucher_number",
                    "voucher_date",
                    "account_name",
                    "amount",
                    "risk_level",
                    "test_name",
                    "reason",
                    "audit_procedure",
                ]],
                use_container_width=True,
                hide_index=True,
            )

        # Benford Analysis Display
        if st.session_state.benford_result is not None:
            ben_res = st.session_state.benford_result
            st.markdown("---")
            st.markdown("#### First-Digit Benford's Law Analysis (SA 240 / SA 520)")

            b_col1, b_col2 = st.columns([2, 1])
            with b_col1:
                sum_df = ben_res["summary_df"]
                chart_df = sum_df.set_index("Digit")[["Observed Proportion (%)", "Expected Proportion (%)"]]
                st.bar_chart(chart_df)

            with b_col2:
                st.markdown("##### Statistical Parameters")
                st.write(f"• **Sample Count (N):** {ben_res['sample_size']:,}")
                st.write(f"• **Degrees of Freedom:** {ben_res['degrees_of_freedom']}")
                chi_val = ben_res["chi2_stat"]
                p_val = ben_res["p_value"]
                st.write(f"• **Chi-Square (χ²):** {chi_val:.3f}" if chi_val is not None and not pd.isna(chi_val) else "• **Chi-Square (χ²):** N/A")
                st.write(f"• **p-value:** {p_val:.4f}" if p_val is not None and not pd.isna(p_val) else "• **p-value:** N/A")

                if ben_res["conforms"]:
                    st.success("✅ **H0 Accepted:** Population conforms to Benford's Law (p ≥ 0.05).")
                else:
                    st.warning("⚠️ **H0 Rejected:** Population statistically deviates from Benford's Law (p < 0.05).")

            st.info(ben_res["limitation_note"])


# =====================================================================
# TAB 3: AUDIT SAMPLING & REVIEW
# =====================================================================
with tab3:
    if st.session_state.std_df is None or st.session_state.flags_df is None:
        st.warning("⚠️ Please complete Steps 1 & 2 before performing audit sampling.")
    else:
        st.markdown("#### Step 3: Stratified Audit Sampling & Auditor Review Schedule")
        st.markdown(
            "In accordance with **SA 530** (*Audit Sampling*) and **SA 330**, sampling is partitioned into **Stratum 1 (Items > PM)**, "
            "**Stratum 2 (Targeted High-Risk Exceptions)**, and **Stratum 3 (Representative Random Sample)**."
        )

        with st.expander("⚙️ Configure Sampling Strategy", expanded=True):
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.markdown("**Stratum 1: Key Items (> PM)**")
                st.caption(f"100% substantive testing of all entries exceeding PM (₹ {pm_input:,.2f}).")
            with sc2:
                inc_high_risk = st.checkbox("Include Stratum 2 (Targeted High-Risk Items)", value=True)
                st.caption("Includes all transactions flagged as High Risk in Step 2.")
            with sc3:
                rand_size = st.number_input("Stratum 3: Representative Random Sample Size", min_value=5, max_value=100, value=20)
                rand_seed = st.number_input("Random Generator Seed", min_value=1, max_value=9999, value=42)

            if st.button("🎲 Generate Stratified Audit Sample", type="primary"):
                sample_res = generate_audit_sample(
                    st.session_state.std_df,
                    st.session_state.flags_df,
                    pm=pm_input,
                    sample_high_risk=inc_high_risk,
                    random_sample_size=rand_size,
                    random_seed=rand_seed,
                )
                st.session_state.sample_df = sample_res
                st.success(f"✅ Generated sample of {len(sample_res)} vouchers across 3 strata without duplicates!")

        # Display Sample & Working Review Editor
        if st.session_state.sample_df is not None and not st.session_state.sample_df.empty:
            sample_df = st.session_state.sample_df
            st.markdown("---")
            st.markdown(f"#### Vouching & Auditor Review Working Schedule ({len(sample_df)} Sampled Items)")
            st.caption("Update auditor observations, management explanations, tick marks, and final dispositions below. Records persist in the session.")

            # Form to update review notes
            for idx, item in sample_df.iterrows():
                s_idx = int(item["source_row_index"])
                existing_rev = st.session_state.review_records.get(s_idx, {})

                with st.expander(
                    f"Row #{s_idx} | Vch: {item['voucher_number']} | ₹ {item['amount']:,.2f} | {item['account_name']} [{item['risk_level']} Risk]",
                    expanded=False,
                ):
                    c_info1, c_info2 = st.columns(2)
                    with c_info1:
                        st.write(f"• **Voucher Date:** {item['voucher_date']}")
                        st.write(f"• **Selection Stratum:** {item['stratum']}")
                        st.write(f"• **Selection Method:** {item['selection_method']}")
                    with c_info2:
                        st.write(f"• **Debit:** ₹ {item.get('debit', 0.0):,.2f} | **Credit:** ₹ {item.get('credit', 0.0):,.2f}")
                        st.write(f"• **Narration:** {item['narration']}")

                    st.markdown("---")
                    r_col1, r_col2 = st.columns(2)
                    with r_col1:
                        obs = st.text_area(
                            "Auditor Observations",
                            value=existing_rev.get("auditor_observations", "Vouched with original supporting tax invoice and delivery challan. Arithmetic accuracy verified."),
                            key=f"obs_{s_idx}",
                        )
                        mgmt_exp = st.text_area(
                            "Management Explanation",
                            value=existing_rev.get("management_explanation", "Routine operational expenditure incurred in ordinary course of business per approved budget."),
                            key=f"mgmt_{s_idx}",
                        )
                    with r_col2:
                        doc_ref = st.text_input(
                            "Supporting Document Ref",
                            value=existing_rev.get("supporting_document_ref", f"INV/{s_idx:04d} dt {item['voucher_date']}"),
                            key=f"doc_{s_idx}",
                        )
                        ticks = st.text_input(
                            "Audit Tick Marks",
                            value=existing_rev.get("audit_tick_marks", "^, V, B, A"),
                            key=f"tick_{s_idx}",
                        )
                        disp = st.selectbox(
                            "Final Disposition",
                            ["Satisfactory", "Exception Noted", "Inquiry Required", "Unresolved"],
                            index=["Satisfactory", "Exception Noted", "Inquiry Required", "Unresolved"].index(
                                existing_rev.get("final_disposition", "Satisfactory")
                            ),
                            key=f"disp_{s_idx}",
                        )
                        status = st.selectbox(
                            "Review Status",
                            ["Cleared", "Open", "In Review", "Escalated"],
                            index=["Cleared", "Open", "In Review", "Escalated"].index(
                                existing_rev.get("review_status", "Cleared")
                            ),
                            key=f"status_{s_idx}",
                        )

                    # Update session dictionary
                    st.session_state.review_records[s_idx] = {
                        "source_row_index": s_idx,
                        "auditor_observations": obs,
                        "management_explanation": mgmt_exp,
                        "supporting_document_ref": doc_ref,
                        "audit_tick_marks": ticks,
                        "final_disposition": disp,
                        "review_status": status,
                    }

            st.success("✅ Review observations and tick marks are up to date and saved.")


# =====================================================================
# TAB 4: WORKPAPERS & CONCLUSION MEMO
# =====================================================================
with tab4:
    if st.session_state.std_df is None or st.session_state.flags_df is None:
        st.warning("⚠️ Please complete previous steps to generate workpapers and conclusion memo.")
    else:
        st.markdown("#### Step 4: Export Deliverables (Excel Work Paper & PDF Audit Memo)")
        st.markdown(
            "Generate formal, audit-file deliverables complying with ICAI documentation requirements, SA 230 (*Audit Documentation*), and CARO 2020."
        )

        eng_meta = {
            "company_name": company_name,
            "engagement_name": engagement_name,
            "financial_year": fy_selected,
            "audit_period": f"{fy_start_dt.strftime('%d-%b-%Y')} to {fy_end_dt.strftime('%d-%b-%Y')}",
            "prepared_by": prepared_by,
            "reviewed_by": reviewed_by,
            "om": om_input,
            "pm": pm_input,
            "ctt": ctt_input,
        }

        # Deliverable 1: Excel Work Paper Package
        st.markdown("---")
        st.markdown("### 📊 1. CA-Firm Excel Work Paper Package (`WP_JE_Testing_FY202X-XX.xlsx`)")
        st.caption(
            "Features 5 structured sheets: Index & Objective, Methodology & Criteria, Testing Summary, Sample Testing Schedule, and Benford Analysis."
        )

        # Ensure sample_df exists
        if st.session_state.sample_df is None:
            st.session_state.sample_df = generate_audit_sample(
                st.session_state.std_df,
                st.session_state.flags_df,
                pm=pm_input,
                sample_high_risk=True,
                random_sample_size=20,
            )

        review_list = list(st.session_state.review_records.values())

        try:
            excel_bytes = build_excel_workpaper(
                engagement_info=eng_meta,
                diagnostics=st.session_state.diagnostics,
                flags_df=st.session_state.flags_df,
                sample_df=st.session_state.sample_df,
                benford_result=st.session_state.benford_result or {},
                review_data=review_list,
            )

            file_yr_label = fy_selected.replace(" ", "_")
            excel_filename = f"WP_JE_Testing_{file_yr_label}.xlsx"

            st.download_button(
                label=f"📥 Download Excel Work Paper ({excel_filename})",
                data=excel_bytes,
                file_name=excel_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )
        except Exception as e:
            st.error(f"Error compiling Excel workpaper: {e}")

        # Deliverable 2: PDF Audit Conclusion Memo
        st.markdown("---")
        st.markdown("### 📄 2. Formal PDF Audit Conclusion Memo (SA 240 / SA 330 / CARO 2020)")
        st.caption(
            "The auditor must choose and approve the final conclusion. Flags do NOT automatically constitute fraud or reportable CARO issues."
        )

        memo_col1, memo_col2 = st.columns(2)
        with memo_col1:
            concl_choice = st.selectbox(
                "Final Audit Conclusion Choice *",
                options=["Satisfactory", "Unresolved Exceptions", "Potential Material Misstatement", "Inconclusive"],
                index=0,
                help="Select the formal audit conclusion reached by the engagement team.",
            )
            auditor_memo_text = st.text_area(
                "Auditor Conclusion & Evaluation Narrative",
                value="The engagement team has completed automated red-flag testing and substantive vouching of high-risk and sample journal entries. Management explanations were verified against underlying third-party documents. We conclude that controls over journal entries are operating effectively and no uncorrected material misstatements or fraudulent overrides were identified.",
                height=120,
            )
        with memo_col2:
            caro_text = st.text_area(
                "CARO 2020 Reporting Assessment",
                value="Based on testing of non-routine journal entries, no diversion of borrowed funds (Clause 3(ix)) or unrecorded transactions (Clause 3(viii)) were identified. No whistle-blower complaints or fraud occurrences under Clause 3(xi) were noted.",
                height=60,
            )
            unres_text = st.text_input("Unresolved Matters", value="None outstanding as of report date.")
            impact_text = st.text_input("Financial Statement Impact", value="Nil. No adjustments required.")

        try:
            pdf_bytes = generate_pdf_conclusion_memo(
                engagement_info=eng_meta,
                diagnostics=st.session_state.diagnostics,
                flags_df=st.session_state.flags_df,
                sample_df=st.session_state.sample_df,
                benford_result=st.session_state.benford_result or {},
                conclusion_choice=concl_choice,
                auditor_final_memo=auditor_memo_text,
                caro_implications=caro_text,
                unresolved_matters=unres_text,
                financial_impact=impact_text,
            )

            pdf_filename = f"Audit_Conclusion_Memo_JE_{file_yr_label}.pdf"
            st.download_button(
                label=f"📥 Download PDF Conclusion Memo ({pdf_filename})",
                data=pdf_bytes,
                file_name=pdf_filename,
                mime="application/pdf",
                type="primary",
            )
        except Exception as e:
            st.error(f"Error compiling PDF memo: {e}")
