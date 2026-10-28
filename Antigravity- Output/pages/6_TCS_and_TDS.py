"""
Page 6: TCS & TDS Compliance (pages/6_TCS_and_TDS.py)
Layer C Compliance:
- TCS: MTR vs Payments vs Statutory 0.5%
- TDS: Payments vs Statutory 0.1% (Section 194-O)
- User-entered GSTR-8 (Table 4) and Form 26AS matching with local persistence.
- Specific order-level TCS rate anomaly detection.
"""
import streamlit as st
import pandas as pd
from decimal import Decimal

from core.session import init_session_state, run_full_reconciliation
from core.formatting import format_inr
from core.db import get_all_settings, get_external_figures, set_external_figures

init_session_state()
settings = get_all_settings()

st.title("🛡️ TCS & TDS Compliance (Layer C)")
st.markdown("Statutory tax reconciliation ensuring marketplace tax credits reported by Amazon match withholding schedules.")

if not st.session_state.tcs_tds_result:
    st.info("No tax reconciliation data available. Please load demo data or upload reports.")
    st.stop()

tcs_tds = st.session_state.tcs_tds_result
summary = tcs_tds["summary"]
breakdown = tcs_tds["breakdown"]
period_key = f"{st.session_state.period_year}-{st.session_state.period_month:02d}"

# 1. TCS Overview
st.subheader("1. TCS (Tax Collected at Source - GST)")
st.caption(f"Configured statutory TCS rate: {(settings['tcs_statutory_rate'] * 100):.2f}% (0.25% CGST + 0.25% SGST or 0.5% IGST). Note: Statutory rates change and must be verified.")

col_t1, col_t2, col_t3, col_t4 = st.columns(4)
col_t1.metric("Net Taxable Sales", format_inr(summary["mtr_net_taxable"]))
col_t2.metric("Statutory TCS Target", format_inr(summary["expected_tcs_statutory"]))
col_t3.metric("TCS in MTR Invoices", format_inr(summary["mtr_tcs_total"]))
col_t4.metric("TCS in Payments File", format_inr(summary["pay_tcs_total"]))

tcs_mtr_vs_pay = summary["tcs_mtr_vs_pay"]
if abs(tcs_mtr_vs_pay) <= settings["tolerance"]:
    st.success(f"✅ TCS Check: MTR TCS matches Payments TCS within tolerance ({format_inr(tcs_mtr_vs_pay)}).")
else:
    st.error(f"⚠️ TCS Discrepancy: MTR TCS differs from Payments TCS by {format_inr(tcs_mtr_vs_pay)}.")

st.markdown("##### Payments TCS Breakdown")
c_cgst, c_sgst, c_igst = st.columns(3)
c_cgst.write(f"**TCS-CGST:** {format_inr(breakdown['pay_tcs_cgst'])}")
c_sgst.write(f"**TCS-SGST:** {format_inr(breakdown['pay_tcs_sgst'])}")
c_igst.write(f"**TCS-IGST:** {format_inr(breakdown['pay_tcs_igst'])}")

st.markdown("---")

# 2. TDS Overview
st.subheader("2. TDS under Section 194-O (Income Tax)")
st.caption(f"Configured statutory TDS rate: {(settings['tds_statutory_rate'] * 100):.2f}% on Gross Sales.")

col_d1, col_d2, col_d3 = st.columns(3)
col_d1.metric("Gross Sales (MTR)", format_inr(summary["mtr_gross_invoice"]))
col_d2.metric("Statutory TDS Target (0.1%)", format_inr(summary["expected_tds_statutory"]))
col_d3.metric("TDS Deducted in Payments", format_inr(summary["pay_tds_total"]))

tds_diff = summary["tds_pay_vs_statutory"]
if abs(tds_diff) <= settings["tolerance"]:
    st.success(f"✅ TDS Check: Payments TDS matches Section 194-O statutory expectation within tolerance ({format_inr(tds_diff)}).")
else:
    st.warning(f"⚠️ TDS Variance: Payments TDS differs from statutory expectation by {format_inr(tds_diff)}.")

st.markdown("---")

# 3. External Portal Tie-Out (GSTR-8 and Form 26AS)
st.subheader("3. External Portal Figures Tie-Out")
st.markdown("Enter filed monthly figures from the GST Portal (**GSTR-8 Table 4**) and Income Tax Portal (**Form 26AS**) to verify Amazon's actual government deposits:")

ext_vals = get_external_figures(period_key)

with st.form("ext_portal_form"):
    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        f_net_taxable = st.number_input("GSTR-8 Net Taxable Supplies (₹)", value=float(ext_vals["gstr8_net_taxable"]), step=100.0)
    with col_e2:
        f_gstr8_tcs = st.number_input("GSTR-8 TCS Credit Deposited (₹)", value=float(ext_vals["gstr8_tcs"]), step=10.0)
    with col_e3:
        f_26as_tds = st.number_input("Form 26AS TDS Deposited (₹)", value=float(ext_vals["form26as_tds"]), step=10.0)

    btn_save_ext = st.form_submit_button("Save & Update Portal Tie-Out")
    if btn_save_ext:
        set_external_figures(
            period_key,
            Decimal(str(f_net_taxable)),
            Decimal(str(f_gstr8_tcs)),
            Decimal(str(f_26as_tds))
        )
        st.success("Portal figures updated!")
        run_full_reconciliation()
        st.rerun()

# Verification Status
if ext_vals["gstr8_tcs"] > Decimal("0.00"):
    gstr8_diff = summary["pay_tcs_total"] - ext_vals["gstr8_tcs"]
    if abs(gstr8_diff) <= settings["tolerance"]:
        st.success(f"✅ GSTR-8 Tie-Out PASSED: Payments TCS matches GSTR-8 deposited TCS within tolerance ({format_inr(gstr8_diff)}).")
    else:
        st.error(f"⚠️ GSTR-8 Discrepancy: Amazon deducted {format_inr(summary['pay_tcs_total'])} in payouts but deposited {format_inr(ext_vals['gstr8_tcs'])} on GST portal (Variance: {format_inr(gstr8_diff)}).")

if ext_vals["form26as_tds"] > Decimal("0.00"):
    tds_26as_diff = summary["pay_tds_total"] - ext_vals["form26as_tds"]
    if abs(tds_26as_diff) <= settings["tolerance"]:
        st.success(f"✅ Form 26AS Tie-Out PASSED: Payments TDS matches Form 26AS credit within tolerance ({format_inr(tds_26as_diff)}).")
    else:
        st.error(f"⚠️ Form 26AS Discrepancy: Amazon deducted {format_inr(summary['pay_tds_total'])} TDS but deposited {format_inr(ext_vals['form26as_tds'])} (Variance: {format_inr(tds_26as_diff)}).")

st.markdown("---")

# 4. Order-Level TCS/TDS Anomalies
st.subheader("4. Order-Level Rate Anomalies")
anomalies = tcs_tds.get("anomalies", [])
if anomalies:
    st.error(f"Detected **{len(anomalies)}** order(s) where TCS deducted does not match statutory rates:")
    df_anom = pd.DataFrame(anomalies)
    df_anom["taxable_value"] = df_anom["taxable_value"].apply(format_inr)
    df_anom["tcs_deducted"] = df_anom["tcs_deducted"].apply(format_inr)
    df_anom["expected_tcs"] = df_anom["expected_tcs"].apply(format_inr)
    df_anom["difference"] = df_anom["difference"].apply(format_inr)
    st.dataframe(df_anom, use_container_width=True, hide_index=True)
else:
    st.success("No order-level TCS or TDS rate anomalies detected.")

st.markdown("<br><hr><small style='color: gray;'>MarketMatch • Demo project. Not tax advice.</small>", unsafe_allow_html=True)
