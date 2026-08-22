"""Streamlit Local Web UI for Bank Statement Analyzer.
Dharmjeet & Associates, Chartered Accountants.
"""

import os
import io
import yaml
import streamlit as st
import pandas as pd
import numpy as np

from ingestion import ingest_statement, ingest_multiple_statements_with_diagnostics
from classification import (
    classify_transactions, load_client_profile, save_client_profile,
    add_party_mapping, list_client_profiles, load_classification_rules
)
from analysis import (
    generate_executive_summary, generate_month_wise_summary,
    generate_nature_wise_summary, generate_party_wise_summary,
    generate_cross_tab_summary, generate_top_and_extrema_transactions,
    generate_cash_summary, generate_bank_charges_summary,
    detect_red_flags, analyze_presumptive_tax, validate_running_balances,
    load_thresholds
)
from reports import export_excel_report, export_word_report, export_pdf_report

# Page Configuration
st.set_page_config(
    page_title="Bank Statement Analyzer | Dharmjeet & Associates",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Styling
st.markdown("""
<style>
    .main-header {
        font-size: 26px;
        font-weight: 700;
        color: #1F4E78;
        margin-bottom: 2px;
    }
    .sub-header {
        font-size: 14px;
        color: #595959;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #F8F9FA;
        border-radius: 8px;
        padding: 14px 18px;
        border-left: 4px solid #1F4E78;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .metric-title {
        font-size: 12px;
        font-weight: 600;
        color: #595959;
        text-transform: uppercase;
    }
    .metric-val {
        font-size: 22px;
        font-weight: 700;
        color: #1F4E78;
        margin-top: 4px;
    }
    .flag-card {
        background-color: #FFF2F2;
        border-left: 4px solid #C00000;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "df_analyzed" not in st.session_state:
    st.session_state.df_analyzed = None
if "client_name" not in st.session_state:
    st.session_state.client_name = "Default Client"
if "ingest_diagnostics" not in st.session_state:
    st.session_state.ingest_diagnostics = []

# Header Banner
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown('<div class="main-header">DHARMJEET & ASSOCIATES</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Chartered Accountants | Offline Bank Statement Analyzer & Tax Scrutiny Tool</div>', unsafe_allow_html=True)

with col_h2:
    st.markdown(
        "<div style='text-align: right; padding-top: 8px; color: #2E75B6; font-weight: 600;'>"
        "🔒 100% Offline & Private"
        "</div>",
        unsafe_allow_html=True
    )

st.divider()

# Sidebar: Client Management & File Ingestion
with st.sidebar:
    st.header("📂 Client & Ingestion")
    
    # Client Profile
    saved_profiles = list_client_profiles()
    profile_options = ["Create New Client..."] + saved_profiles
    selected_prof = st.selectbox("Select Client Profile", profile_options, index=1 if saved_profiles else 0)
    
    if selected_prof == "Create New Client...":
        new_client = st.text_input("Enter New Client Name", value="M/s ABC Traders")
        client_name = new_client.strip() or "Client"
    else:
        client_name = selected_prof
    st.session_state.client_name = client_name

    # Load Client Data
    client_profile = load_client_profile(client_name)

    # File Ingestion
    st.subheader("Upload Statements")
    uploaded_files = st.file_uploader(
        "Upload Bank Statements (PDF, Excel, Word, JPEG/PNG Images, CSV)",
        type=["pdf", "xlsx", "xls", "csv", "docx", "png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    pdf_password = st.text_input("PDF Password (if protected)", type="password", help="Enter password if any uploaded PDF is encrypted.")

    # Ingestion Button
    if uploaded_files:
        if st.button("🚀 Ingest & Analyze Statements", type="primary", use_container_width=True):
            with st.spinner("Processing statements with OCR and parsing engine..."):
                file_inputs = []
                for f in uploaded_files:
                    file_inputs.append({
                        "file": f.getvalue(),
                        "filename": f.name,
                        "password": pdf_password.strip() if pdf_password else None
                    })
                
                df_ingested, diagnostics = ingest_multiple_statements_with_diagnostics(file_inputs)
                st.session_state.ingest_diagnostics = diagnostics

                if not df_ingested.empty:
                    df_classified = classify_transactions(df_ingested, client_name=client_name)
                    df_recon, _ = validate_running_balances(df_classified)
                    df_analyzed, _ = detect_red_flags(df_recon, client_name=client_name)
                    st.session_state.df_analyzed = df_analyzed
                    st.success(f"Successfully processed {len(df_analyzed)} transactions from {len(uploaded_files)} file(s)!")
                else:
                    st.error("No valid transactions could be parsed from the uploaded file(s). Check diagnostic details below.")

# Display Ingestion Diagnostics if available
if st.session_state.ingest_diagnostics:
    with st.expander("📋 Ingestion Status & File Diagnostics", expanded=(st.session_state.df_analyzed is None)):
        for diag in st.session_state.ingest_diagnostics:
            if diag["status"] == "SUCCESS":
                st.markdown(f"✅ **{diag['filename']}** ({diag['format']}): {diag['rows_extracted']} transactions extracted ({diag['bank']}).")
            else:
                st.markdown(f"❌ **{diag['filename']}** ({diag['format']}): {diag['message']}")

# Main Application Body
df = st.session_state.df_analyzed

if df is None or df.empty:
    # Landing / Empty State Guidance
    st.info("👋 Welcome! Upload your bank statement files (PDFs, WhatsApp/Scanned JPEG Images, Excel, Word) in the sidebar and click **'Ingest & Analyze Statements'**.")
    
    # Quick Features Cards
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### 🏦 Multi-Bank Normalization")
        st.write("Automatically parses columns and statements from SBI, HDFC, ICICI, Axis, PNB, BOB, Kotak, IDFC, Canara, Union Bank, and others with generic fallback.")
    with c2:
        st.markdown("### 🔍 Tax Scrutiny & Red Flags")
        st.write("Flags PAN cash limits (₹50k), SFT limits (₹10L/₹50L), Section 269SS/269T cash loans, 2-day accommodation reversals, and structuring patterns.")
    with c3:
        st.markdown("### 📑 Client-Ready Reports")
        st.write("Generates comprehensive multi-tab Excel workbooks, narrative Word documents, and letterhead-styled PDFs for ITR filing and scrutiny replies.")

else:
    # Calculations
    exec_sum = generate_executive_summary(df)
    m_sum = generate_month_wise_summary(df)
    nat_cr, nat_dr = generate_nature_wise_summary(df)
    pty_cr, pty_dr = generate_party_wise_summary(df)
    top_ext = generate_top_and_extrema_transactions(df)
    cash_sum = generate_cash_summary(df)
    chg_sum = generate_bank_charges_summary(df)
    df_flagged, red_flag_sum = detect_red_flags(df, client_name=st.session_state.client_name)
    presump_sum = analyze_presumptive_tax(df)
    df_recon, recon_sum = validate_running_balances(df)

    # Top KPI Metrics Row
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Receipts (Cr)</div>
            <div class="metric-val" style="color: #2E7D32;">₹{exec_sum['total_credits']:,.2f}</div>
            <small>{exec_sum['credit_count']:,} transactions</small>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Payments (Dr)</div>
            <div class="metric-val" style="color: #C62828;">₹{exec_sum['total_debits']:,.2f}</div>
            <small>{exec_sum['debit_count']:,} transactions</small>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Net Flow</div>
            <div class="metric-val" style="color: #1F4E78;">₹{exec_sum['net_movement']:,.2f}</div>
            <small>Period Movement</small>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Cash Flow (In / Out)</div>
            <div class="metric-val" style="font-size: 17px;">₹{cash_sum['total_cash_deposits']:,.0f} / ₹{cash_sum['total_cash_withdrawals']:,.0f}</div>
            <small>Net: ₹{cash_sum['net_cash_movement']:,.0f}</small>
        </div>
        """, unsafe_allow_html=True)
    with m5:
        flag_cnt = red_flag_sum['total_flagged_transactions']
        st.markdown(f"""
        <div class="metric-card" style="border-left-color: {'#C00000' if flag_cnt > 0 else '#2E7D32'};">
            <div class="metric-title">Scrutiny Red Flags</div>
            <div class="metric-val" style="color: {'#C00000' if flag_cnt > 0 else '#2E7D32'};">{flag_cnt} Flagged</div>
            <small>Vol: ₹{red_flag_sum['total_flagged_amount']:,.0f}</small>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # Main Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Executive Overview",
        "📅 Month-wise Trends",
        "🏷️ Nature-wise Summary",
        "👥 Party-wise Breakdown",
        "🚨 Scrutiny Red Flags",
        "✏️ Transaction Grid & Rule Learner",
        "⚙️ Rules & Thresholds",
        "📥 Export Reports"
    ])

    # Tab 1: Executive Overview
    with tab1:
        st.subheader("1. Statement Profile & Reconciliation Status")
        col_o1, col_o2 = st.columns(2)
        with col_o1:
            st.markdown(f"""
            - **Client Name:** {st.session_state.client_name}
            - **Statement Period:** {exec_sum['start_date']} to {exec_sum['end_date']}
            - **Total Transactions Analyzed:** {exec_sum['total_transactions']:,}
            - **Banks Detected:** {", ".join(set(exec_sum['banks_list']))}
            - **Accounts Detected:** {", ".join(set(exec_sum['accounts_list']))}
            """)
        with col_o2:
            st.markdown(f"""
            - **Running Balance Reconciliation:** `{'✅ RECONCILED' if recon_sum['status'] == 'RECONCILED' else '⚠️ DISCREPANCIES DETECTED'}`
            - **Discrepant Balance Rows:** {recon_sum['discrepancies_found']}
            - **Bank Charges Incurred:** ₹{chg_sum['total_bank_charges']:,.2f}
            - **Fee Reversals / Refunds Received:** ₹{chg_sum['total_reversals']:,.2f}
            """)

        st.divider()
        st.subheader("2. Section 44AD / 44ADA Presumptive Taxation Assessment")
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            st.metric("Gross Turnover / Receipts", f"₹{presump_sum['total_turnover']:,.2f}")
        with p2:
            st.metric("Digital Receipts %", f"{presump_sum['digital_percentage']:.2f}%")
        with p3:
            st.metric("Sec 44AD Audit Required?", "YES (Audit Req.)" if presump_sum["audit_required_44ad"] else "NO (Eligible)")
        with p4:
            st.metric("Min 44AD Presumptive Profit", f"₹{presump_sum['min_presumptive_income_44ad']:,.2f}")

        st.info(f"📌 **Assessment Note:** {presump_sum['remarks']} Applicable Section 44AD Turnover limit: ₹{presump_sum['sec_44ad_limit_applicable']/10000000:.1f} Crore. Section 44ADA Limit: ₹{presump_sum['sec_44ada_limit_applicable']/100000:.1f} Lakhs.")

    # Tab 2: Month-wise Trends
    with tab2:
        st.subheader("Month-wise & FY Quarter Breakdown")
        if not m_sum.empty:
            chart_df = m_sum.set_index("Month")[["Receipts (Cr)", "Payments (Dr)"]]
            st.bar_chart(chart_df)
        st.dataframe(m_sum, use_container_width=True)

    # Tab 3: Nature-wise Summary
    with tab3:
        col_n1, col_n2 = st.columns(2)
        with col_n1:
            st.subheader("Receipts by Nature Category")
            st.dataframe(nat_cr, use_container_width=True)
            if not nat_cr.empty:
                st.bar_chart(nat_cr.set_index("Nature Category")["Total Amount (INR)"])
                
        with col_n2:
            st.subheader("Payments by Nature Category")
            st.dataframe(nat_dr, use_container_width=True)
            if not nat_dr.empty:
                st.bar_chart(nat_dr.set_index("Nature Category")["Total Amount (INR)"])

    # Tab 4: Party-wise Breakdown
    with tab4:
        st.subheader("Counterparty Analysis")
        p_sub1, p_sub2 = st.tabs(["Top Inward Counterparties (Receipts)", "Top Outward Counterparties (Payments)"])
        with p_sub1:
            st.dataframe(pty_cr, use_container_width=True)
        with p_sub2:
            st.dataframe(pty_dr, use_container_width=True)

    # Tab 5: Scrutiny Red Flags
    with tab5:
        st.subheader(f"Tax Scrutiny Anomaly Signals ({red_flag_sum['total_flagged_transactions']} Flagged Entries)")
        
        if red_flag_sum["categories_summary"]:
            st.write("**Summary of Triggered Rules:**")
            cat_cols = st.columns(len(red_flag_sum["categories_summary"]))
            for idx, (cat, cnt) in enumerate(red_flag_sum["categories_summary"].items()):
                with cat_cols[idx % len(cat_cols)]:
                    st.metric(cat.strip(), f"{cnt} Txns")

        flagged_df = df_flagged[df_flagged["is_flagged"]].copy() if "is_flagged" in df_flagged.columns else pd.DataFrame()
        if not flagged_df.empty:
            st.write("---")
            for _, r in flagged_df.iterrows():
                amt = max(float(r["credit_amount"] or 0.0), float(r["debit_amount"] or 0.0))
                dr_cr = "CREDIT" if r["credit_amount"] > 0 else "DEBIT"
                reasons_str = " • ".join(r["flag_reasons"])
                st.markdown(f"""
                <div class="flag-card">
                    <b>{r['transaction_date']}</b> | <span style="color: {'#2E7D32' if dr_cr == 'CREDIT' else '#C62828'}; font-weight: 700;">{dr_cr} ₹{amt:,.2f}</span> | <b>{r['counterparty_name']}</b> ({r['nature']})<br>
                    <small><i>Narration: {r['description']}</i></small><br>
                    <span style="color: #C00000; font-weight: 600;">🚩 {reasons_str}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ No scrutiny red flags detected based on current thresholds.")

    # Tab 6: Interactive Transaction Grid & Rule Learner
    with tab6:
        st.subheader("Search, Filter, Re-Categorize & Teach Rules")
        st.write("You can search transactions, filter by mode or category, and teach custom party rules to the client's profile.")

        search_kw = st.text_input("🔍 Search Description / Party Name / Amount")
        
        filtered_df = df_flagged.copy()
        if search_kw:
            mask = (
                filtered_df["description"].str.contains(search_kw, case=False, na=False) |
                filtered_df["counterparty_name"].str.contains(search_kw, case=False, na=False) |
                filtered_df["nature"].str.contains(search_kw, case=False, na=False)
            )
            filtered_df = filtered_df[mask]

        st.dataframe(
            filtered_df[[
                "transaction_date", "counterparty_name", "nature", "mode",
                "debit_amount", "credit_amount", "balance", "description", "audit_trail"
            ]],
            use_container_width=True
        )

        st.divider()
        st.subheader("💡 Teach / Map Counterparty Rule for this Client")
        st.write("Permanently link a party name to a specific nature category so future runs classify it automatically:")
        
        col_lr1, col_lr2, col_lr3 = st.columns([2, 2, 1])
        with col_lr1:
            all_parties = sorted(df["counterparty_name"].dropna().unique().tolist())
            selected_party = st.selectbox("Select Counterparty", all_parties)
        with col_lr2:
            nature_options = sorted(list(set(
                [r["category"] for r in load_classification_rules().get("receipts", [])] +
                [r["category"] for r in load_classification_rules().get("payments", [])]
            )))
            selected_nature = st.selectbox("Map to Nature Category", nature_options)
        with col_lr3:
            st.write("")
            st.write("")
            if st.button("💾 Save Mapping", type="primary", use_container_width=True):
                add_party_mapping(st.session_state.client_name, selected_party, selected_nature)
                st.success(f"Saved mapping: '{selected_party}' -> '{selected_nature}' for client '{st.session_state.client_name}'!")
                df_reclass = classify_transactions(st.session_state.df_analyzed, client_name=st.session_state.client_name)
                st.session_state.df_analyzed = df_reclass
                st.rerun()

    # Tab 7: Rules & Thresholds Editor
    with tab7:
        st.subheader("Scrutiny Thresholds & Keyword Rules Configuration")
        col_th1, col_th2 = st.columns(2)
        with col_th1:
            st.write("### Active Audit Thresholds")
            curr_th = load_thresholds()
            st.json(curr_th)
            
        with col_th2:
            st.write("### Client Profile Memory")
            curr_prof = load_client_profile(st.session_state.client_name)
            st.json(curr_prof)

    # Tab 8: Export Reports
    with tab8:
        st.subheader("Download Client-Ready Deliverables")
        st.write("Export all analysis, formatted tables, KPIs, and audit trails in Excel, Word, or PDF format:")

        exp_c1, exp_c2, exp_c3, exp_c4 = st.columns(4)

        # Excel Export
        with exp_c1:
            temp_excel_path = f"output/{st.session_state.client_name}_Summary.xlsx"
            export_excel_report(df_flagged, temp_excel_path, client_name=st.session_state.client_name)
            with open(temp_excel_path, "rb") as f:
                excel_bytes = f.read()
            st.download_button(
                label="📊 Download Excel (.xlsx)",
                data=excel_bytes,
                file_name=f"{st.session_state.client_name}_Bank_Summary.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        # Word Export
        with exp_c2:
            temp_word_path = f"output/{st.session_state.client_name}_Report.docx"
            export_word_report(df_flagged, temp_word_path, client_name=st.session_state.client_name)
            with open(temp_word_path, "rb") as f:
                word_bytes = f.read()
            st.download_button(
                label="📄 Download Word (.docx)",
                data=word_bytes,
                file_name=f"{st.session_state.client_name}_Bank_Report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )

        # PDF Export
        with exp_c3:
            temp_pdf_path = f"output/{st.session_state.client_name}_Report.pdf"
            export_pdf_report(df_flagged, temp_pdf_path, client_name=st.session_state.client_name)
            with open(temp_pdf_path, "rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                label="📑 Download PDF (.pdf)",
                data=pdf_bytes,
                file_name=f"{st.session_state.client_name}_Bank_Report.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        # CSV Export
        with exp_c4:
            csv_str = df_flagged.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📁 Download Raw CSV",
                data=csv_str,
                file_name=f"{st.session_state.client_name}_Transactions.csv",
                mime="text/csv",
                use_container_width=True
            )
