"""
Page 9: Settings (pages/9_Settings.py)
Reconciliation settings, tolerance limits, unpaid aging thresholds,
statutory tax rates, and seller profiles with SQLite persistence.
"""
import streamlit as st
from decimal import Decimal

from core.session import init_session_state, run_full_reconciliation
from core.db import get_all_settings, set_setting

init_session_state()
current_settings = get_all_settings()

st.title("⚙️ Reconciliation Settings")
st.markdown("Customize financial tolerances, statutory tax parameters, threshold days, and merchant identity.")

with st.form("settings_form"):
    st.subheader("1. Financial Thresholds & Tolerances")
    c1, c2 = st.columns(2)
    with c1:
        f_tolerance = st.number_input(
            "Rounding Tolerance (₹)",
            value=float(current_settings["tolerance"]),
            min_value=0.0, max_value=50.0, step=0.10,
            help="Differences within this threshold are classified as 'Rounding' rather than discrepancies."
        )
        f_b2cl = st.number_input(
            "B2C Large Threshold (₹)",
            value=float(current_settings["b2cl_threshold"]),
            min_value=10000.0, max_value=500000.0, step=10000.0,
            help="Inter-state B2C sales above this invoice value threshold are routed to B2C Large rather than B2C Small. (Note: Statutory limit should be verified against current CBIC notifications)."
        )

    with c2:
        f_unpaid_days = st.number_input(
            "Unpaid Aging Threshold (Days)",
            value=int(current_settings["unpaid_threshold_days"]),
            min_value=1, max_value=90, step=1,
            help="An order with no payment record is classified as 'Timing' if within this window, and 'Not paid' if older."
        )
        as_of_val = st.text_input(
            "As-Of Reference Date (YYYY-MM-DD)",
            value=str(current_settings["as_of_date"]),
            help="Reference date for aging calculations. Enables reproducible historic audits."
        )

    st.markdown("---")
    st.subheader("2. Statutory Tax Parameters")
    st.caption("Note: Statutory tax withholding rates may change per government notifications and must be verified.")
    c3, c4, c5 = st.columns(3)
    with c3:
        f_tcs_rate = st.number_input(
            "Statutory TCS Rate (%)",
            value=float(current_settings["tcs_statutory_rate"] * 100),
            min_value=0.0, max_value=5.0, step=0.05,
            help="Default is 0.5% (0.25% CGST + 0.25% SGST or 0.5% IGST)."
        )
    with c4:
        f_tds_rate = st.number_input(
            "Statutory TDS Rate (Section 194-O) (%)",
            value=float(current_settings["tds_statutory_rate"] * 100),
            min_value=0.0, max_value=5.0, step=0.05,
            help="Default is 0.1% on Gross e-commerce sales."
        )
    with c5:
        f_gst_fees = st.number_input(
            "GST Rate on Marketplace Fees (%)",
            value=float(current_settings["gst_rate_on_fees"] * 100),
            min_value=0.0, max_value=28.0, step=1.0,
            help="GST charged by Amazon on commission and shipping fees (standard 18%)."
        )

    st.markdown("---")
    st.subheader("3. Merchant Identity (For Dispute Letters)")
    c6, c7 = st.columns(2)
    with c6:
        f_seller_name = st.text_input("Seller Trade Name", value=current_settings["seller_name"])
    with c7:
        f_seller_gstin = st.text_input("Seller GSTIN", value=current_settings["seller_gstin"])

    st.markdown("---")
    btn_save = st.form_submit_button("Save Settings & Apply to Engine", type="primary")

    if btn_save:
        set_setting("tolerance", f"{Decimal(str(f_tolerance)):.2f}")
        set_setting("unpaid_threshold_days", str(f_unpaid_days))
        set_setting("b2cl_threshold", f"{Decimal(str(f_b2cl)):.2f}")
        set_setting("tcs_statutory_rate", str(Decimal(str(f_tcs_rate)) / Decimal("100.00")))
        set_setting("tds_statutory_rate", str(Decimal(str(f_tds_rate)) / Decimal("100.00")))
        set_setting("gst_rate_on_fees", str(Decimal(str(f_gst_fees)) / Decimal("100.00")))
        set_setting("seller_name", f_seller_name.strip())
        set_setting("seller_gstin", f_seller_gstin.strip().upper())
        set_setting("as_of_date", as_of_val.strip())

        st.success("Settings saved successfully! Re-running reconciliations...")
        run_full_reconciliation()
        st.rerun()

st.markdown("<br><hr><small style='color: gray;'>MarketMatch • Demo project. Not tax advice.</small>", unsafe_allow_html=True)
