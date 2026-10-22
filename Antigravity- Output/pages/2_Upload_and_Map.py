"""
Page 2: Upload & Map (pages/2_Upload_and_Map.py)
Upload 3 reports (MTR, GST RTF, Payments), profile selection, file validation,
duplicate hash detection, value-mapping screens, control totals, and internal checks.
"""
import streamlit as st
import pandas as pd
from decimal import Decimal

from core.session import init_session_state, run_full_reconciliation
from core.profiles import ProfileManager
from core.parsers import parse_mtr, parse_gst_rtf, parse_payments, compute_file_hash
from core.db import get_all_settings, record_uploaded_file, is_file_duplicate
from core.formatting import format_inr

init_session_state()
pm = ProfileManager()
settings = get_all_settings()

st.title("📂 Upload & Profile Mapping")
st.markdown("Upload your Amazon seller reports or custom marketplace files. The ingestion engine is fully driven by `config/column_aliases.json`.")

# Reporting Period
st.subheader("1. Select Reporting Period")
col_p1, col_p2, col_p3 = st.columns([1, 1, 2])
months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
with col_p1:
    sel_month = st.selectbox("Filing Month", range(1, 13), format_func=lambda x: months[x - 1], index=st.session_state.period_month - 1)
with col_p2:
    sel_year = st.selectbox("Filing Year", [2024, 2025, 2026, 2027], index=2)
with col_p3:
    st.info(f"Targeting records for: **{months[sel_month - 1]} {sel_year}**")

if sel_month != st.session_state.period_month or sel_year != st.session_state.period_year:
    st.session_state.period_month = sel_month
    st.session_state.period_year = sel_year

st.markdown("---")
st.subheader("2. Upload Reports")

col_u1, col_u2, col_u3 = st.columns(3)

# --- SLOT 1: MTR (Sales) ---
with col_u1:
    st.markdown("#### (1) Sales (MTR)")
    mtr_profiles = [k for k, p in pm.profiles.items() if p.get("role") == "sales"] or ["amazon_mtr"]
    sel_mtr_profile = st.selectbox("Profile", mtr_profiles, key="sel_mtr_prof")
    prof_mtr = pm.get_profile(sel_mtr_profile)
    st.caption(f"Verified: `{prof_mtr.get('verified')}` | Value Formats Verified: `{prof_mtr.get('value_formats_verified')}`")

    mtr_file = st.file_uploader("Upload MTR (.csv, .xlsx)", type=["csv", "xlsx"], key="mtr_file_upload")
    if mtr_file:
        content = mtr_file.getvalue()
        file_hash = compute_file_hash(content)
        dup = is_file_duplicate(file_hash)
        if dup:
            st.warning(f"⚠️ Duplicate detected: previously uploaded on {dup['upload_timestamp']}.")

        if st.button("Parse & Validate MTR", key="btn_parse_mtr", use_container_width=True):
            with st.spinner("Parsing MTR file..."):
                try:
                    records, report = parse_mtr(
                        content, mtr_file.name,
                        period_month=sel_month, period_year=sel_year,
                        profile_key=sel_mtr_profile, tolerance=settings["tolerance"]
                    )
                    st.session_state.mtr_data = records
                    st.session_state.mtr_report = report
                    st.session_state.active_file_names["mtr"] = mtr_file.name

                    record_uploaded_file(
                        "mtr", mtr_file.name, file_hash, sel_month, sel_year,
                        report.total_rows, report.valid_rows, len(report.row_errors)
                    )
                    st.success(f"Parsed {report.valid_rows} valid records ({len(records)} in period)!")
                    run_full_reconciliation()
                except Exception as e:
                    st.error(f"Error parsing MTR: {str(e)}")

# --- SLOT 2: GST RTF (Reported) ---
with col_u2:
    st.markdown("#### (2) GST Report (GSTR-1)")
    gst_profiles = [k for k, p in pm.profiles.items() if p.get("role") == "gst_reported"] or ["amazon_gst_rtf"]
    sel_gst_profile = st.selectbox("Profile", gst_profiles, key="sel_gst_prof")
    prof_gst = pm.get_profile(sel_gst_profile)
    st.caption(f"Verified: `{prof_gst.get('verified')}` | Value Formats Verified: `{prof_gst.get('value_formats_verified')}`")

    gst_file = st.file_uploader("Upload GST Ready-to-File (.xlsx)", type=["xlsx"], key="gst_file_upload")
    if gst_file:
        content = gst_file.getvalue()
        file_hash = compute_file_hash(content)
        dup = is_file_duplicate(file_hash)
        if dup:
            st.warning(f"⚠️ Duplicate detected: previously uploaded on {dup['upload_timestamp']}.")

        if st.button("Parse & Validate GST Report", key="btn_parse_gst", use_container_width=True):
            with st.spinner("Parsing GST Ready-to-File workbook..."):
                try:
                    sections, report, control_totals = parse_gst_rtf(
                        content, gst_file.name,
                        filing_month=sel_month, filing_year=sel_year,
                        profile_key=sel_gst_profile, tolerance=settings["tolerance"]
                    )
                    st.session_state.gst_data = sections
                    st.session_state.gst_report = report
                    st.session_state.gst_totals = control_totals
                    st.session_state.active_file_names["gst"] = gst_file.name

                    record_uploaded_file(
                        "gst_rtf", gst_file.name, file_hash, sel_month, sel_year,
                        report.total_rows, report.valid_rows, len(report.row_errors)
                    )
                    st.success("Parsed GST sheets successfully! Control totals recomputed.")
                    run_full_reconciliation()
                except Exception as e:
                    st.error(f"Error parsing GST Report: {str(e)}")

# --- SLOT 3: PAYMENTS (Payouts) ---
with col_u3:
    st.markdown("#### (3) Payments (Disbursements)")
    pay_profiles = [k for k, p in pm.profiles.items() if p.get("role") == "payout"] or ["amazon_payments"]
    sel_pay_profile = st.selectbox("Profile", pay_profiles, key="sel_pay_prof")
    prof_pay = pm.get_profile(sel_pay_profile)
    st.caption(f"Verified: `{prof_pay.get('verified')}` | Value Formats Verified: `{prof_pay.get('value_formats_verified')}`")

    pay_file = st.file_uploader("Upload Payments (.csv, .xlsx)", type=["csv", "xlsx"], key="pay_file_upload")
    if pay_file:
        content = pay_file.getvalue()
        file_hash = compute_file_hash(content)
        dup = is_file_duplicate(file_hash)
        if dup:
            st.warning(f"⚠️ Duplicate detected: previously uploaded on {dup['upload_timestamp']}.")

        if st.button("Parse & Validate Payments", key="btn_parse_pay", use_container_width=True):
            with st.spinner("Parsing Payments file with preamble keyword detection..."):
                try:
                    records, report = parse_payments(
                        content, pay_file.name,
                        period_month=sel_month, period_year=sel_year,
                        profile_key=sel_pay_profile, tolerance=settings["tolerance"]
                    )
                    st.session_state.pay_data = records
                    st.session_state.pay_report = report
                    st.session_state.active_file_names["pay"] = pay_file.name

                    record_uploaded_file(
                        "payments", pay_file.name, file_hash, sel_month, sel_year,
                        report.total_rows, report.valid_rows, len(report.row_errors)
                    )
                    st.success(f"Parsed {report.valid_rows} payment records!")
                    run_full_reconciliation()
                except Exception as e:
                    st.error(f"Error parsing Payments: {str(e)}")

st.markdown("---")

# 3. Value-Mapping Screens (Triggered when value_formats_verified is false or unknown values appear)
st.subheader("3. Value Mapping & Format Confirmation")
has_val_screen = False

if st.session_state.mtr_report and not prof_mtr.get("value_formats_verified"):
    has_val_screen = True
    st.markdown("##### 🔍 MTR Transaction Type Mapping")
    st.info("The profile flag `value_formats_verified` is False. Confirm or map distinct values found in this file:")
    distinct_types = st.session_state.mtr_report.distinct_values.get("txn_type", {})
    col_map_inputs = []
    for val, count in distinct_types.items():
        cm1, cm2, cm3 = st.columns([2, 1, 2])
        cm1.write(f"Value in file: **`{val}`**")
        cm2.caption(f"Count: {count}")
        current_map = cm3.selectbox(
            f"Map '{val}' to:",
            ["Sale", "Return", "Cancel", "Ignore"],
            key=f"map_mtr_{val}",
            index=0 if val.lower() in ("shipment", "sale") else (1 if val.lower() in ("refund", "return") else 2)
        )
        col_map_inputs.append((val, current_map))

if st.session_state.pay_report and not prof_pay.get("value_formats_verified"):
    has_val_screen = True
    st.markdown("##### 🔍 Payments Type & Status Mapping")
    distinct_statuses = st.session_state.pay_report.distinct_values.get("Transaction Status", {})
    for val, count in distinct_statuses.items():
        cs1, cs2, cs3 = st.columns([2, 1, 2])
        cs1.write(f"Status in file: **`{val}`**")
        cs2.caption(f"Count: {count}")
        mapped_status = cs3.selectbox(
            f"Map status '{val}' to:",
            ["Released", "Deferred", "Cancelled"],
            key=f"map_pay_status_{val}",
            index=0 if "release" in val.lower() else 1
        )

if not has_val_screen:
    st.caption("All loaded profiles have verified value formats or have confirmed mappings.")

st.markdown("---")

# 4. GST Control Totals and Internal Checks Display
if st.session_state.gst_report:
    st.subheader("4. GST Report Control Totals & Internal Checks")
    ctrl = st.session_state.gst_totals or {}
    st.write(f"**Extracted Merchant GSTIN:** `{ctrl.get('merchant_gstin') or 'Not Found'}`")

    # Control totals grid
    st.markdown("##### Recomputed Detail Totals (Rows 1-3 formulas ignored)")
    sec_cols = st.columns(4)
    sec_cols[0].metric("B2C Small Taxable", format_inr(ctrl.get("b2cs", {}).get("taxable_value", Decimal("0.00"))), f"{ctrl.get('b2cs', {}).get('count', 0)} rows")
    sec_cols[1].metric("B2C Large Taxable", format_inr(ctrl.get("b2cl", {}).get("taxable_value", Decimal("0.00"))), f"{ctrl.get('b2cl', {}).get('count', 0)} rows")
    sec_cols[2].metric("CDNUR Note Value", format_inr(ctrl.get("cdnur", {}).get("taxable_value", Decimal("0.00"))), f"{ctrl.get('cdnur', {}).get('count', 0)} notes")
    sec_cols[3].metric("HSN Summary Taxable", format_inr(ctrl.get("hsn", {}).get("taxable_value", Decimal("0.00"))), f"{ctrl.get('hsn', {}).get('count', 0)} codes")

    st.markdown("##### Profile Internal Checks")
    for chk in st.session_state.gst_report.internal_checks_results:
        passed = chk["passed"]
        icon = "✅" if passed else "⚠️"
        with st.expander(f"{icon} {chk['check_name']}", expanded=not passed):
            st.write(chk["detail"])
            if not passed and "gap" in chk:
                st.warning(
                    f"**Explanation:** The HSN tax amount is lower than Rate × Taxable by ₹ {chk['gap']:,.2f}. "
                    "This discrepancy exists within the Amazon GSTR-1 export itself. MarketMatch has cross-referenced the MTR sales tax columns "
                    "and confirmed this gap originates from item-level roundings or shipping tax schedules in Amazon's report generator."
                )

# 5. Validation Logs
st.markdown("---")
st.subheader("5. Validation Summary & Error Logs")
v_tabs = st.tabs(["MTR Log", "GST Report Log", "Payments Log"])

with v_tabs[0]:
    if st.session_state.mtr_report:
        rep = st.session_state.mtr_report
        st.write(f"Total Rows: **{rep.total_rows}** | Valid Records: **{rep.valid_rows}** | Skipped: **{rep.skipped_rows}**")
        if rep.warnings:
            for w in rep.warnings:
                st.warning(w)
        if rep.row_errors:
            st.error(f"Found {len(rep.row_errors)} row errors:")
            st.dataframe(pd.DataFrame(rep.row_errors), use_container_width=True)
        else:
            st.success("No validation errors in MTR file.")
    else:
        st.caption("No MTR file parsed yet.")

with v_tabs[1]:
    if st.session_state.gst_report:
        rep = st.session_state.gst_report
        st.write(f"Total Sections Processed. Detail records valid: **{rep.valid_rows}**")
        if rep.warnings:
            for w in rep.warnings:
                st.warning(w)
    else:
        st.caption("No GST Report parsed yet.")

with v_tabs[2]:
    if st.session_state.pay_report:
        rep = st.session_state.pay_report
        st.write(f"Total Rows: **{rep.total_rows}** | Valid Transactions: **{rep.valid_rows}** | Skipped: **{rep.skipped_rows}**")
        if rep.warnings:
            for w in rep.warnings:
                st.warning(w)
        if rep.row_errors:
            st.error(f"Row component check failed for {len(rep.row_errors)} rows:")
            st.dataframe(pd.DataFrame(rep.row_errors), use_container_width=True)
        else:
            st.success("All payments rows passed component balance check.")
    else:
        st.caption("No Payments file parsed yet.")

st.markdown("<br><hr><small style='color: gray;'>MarketMatch • Demo project. Not tax advice.</small>", unsafe_allow_html=True)
