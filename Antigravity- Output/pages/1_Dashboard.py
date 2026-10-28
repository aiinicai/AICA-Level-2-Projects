"""
Dashboard Page (pages/1_Dashboard.py)
Mirrors executive dashboard view for direct sidebar navigation.
"""
import streamlit as st
import pandas as pd
from decimal import Decimal

from core.session import init_session_state
from core.formatting import format_inr
from core.bridge import compute_waterfall_data, create_waterfall_figure
from core.db import get_all_settings

init_session_state()
settings = get_all_settings()

st.title("⚖️ Executive Reconciliation Dashboard")
st.caption(f"Active Reporting Period: {st.session_state.period_year}-{st.session_state.period_month:02d}")

if not st.session_state.order_reconciliation:
    st.info("No data currently loaded. Use the sidebar on the Home page to **'Load Demo Data'** or visit **'2 Upload and Map'** to upload files.")
    st.stop()

kpi = st.session_state.kpi_summary
gst_totals = st.session_state.gst_totals or {}
b2cs_gst_taxable = gst_totals.get("b2cs", {}).get("taxable_value", Decimal("0.00"))

st.markdown("### 📊 Key Performance Indicators")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Net Sales (MTR)", format_inr(kpi["total_net_sales"]))
c2.metric("GST Reported Taxable", format_inr(b2cs_gst_taxable))
c3.metric("Actual Net Payout", format_inr(kpi["total_actual_payout"]))
c4.metric("% Reconciled", f"{kpi['reconciled_pct']}%")

c5, c6, c7, c8 = st.columns(4)
c5.metric("Total Marketplace Fees", format_inr(kpi["total_selling_fees"] + kpi["total_fba_fees"] + kpi["total_other_fees"]))
c6.metric("TCS Deducted", format_inr(kpi["total_tcs"]))
c7.metric("TDS Deducted (194-O)", format_inr(kpi["total_tds"]))
diff_val = kpi["total_unexplained"]
c8.metric("Unexplained Discrepancy", format_inr(diff_val), delta=f"{format_inr(diff_val)}", delta_color="inverse")

st.markdown("---")
st.subheader("🌊 Executive Waterfall: Sales to Payout Bridge")
waterfall_data = compute_waterfall_data(kpi)
fig_waterfall = create_waterfall_figure(waterfall_data)
st.plotly_chart(fig_waterfall, use_container_width=True)

st.markdown("---")
st.subheader("📅 Month-Wise Difference Table")
if st.session_state.month_bridge:
    df_mb = pd.DataFrame(st.session_state.month_bridge)
    display_mb = df_mb.copy()
    display_mb["gross_sales"] = display_mb["gross_sales"].apply(format_inr)
    display_mb["refunds"] = display_mb["refunds"].apply(format_inr)
    display_mb["net_sales"] = display_mb["net_sales"].apply(format_inr)
    display_mb["gst_taxable"] = display_mb["gst_taxable"].apply(format_inr)
    display_mb["payout_released"] = display_mb["payout_released"].apply(format_inr)
    display_mb["payout_deferred"] = display_mb["payout_deferred"].apply(format_inr)
    display_mb["payout_total"] = display_mb["payout_total"].apply(format_inr)
    display_mb["fees_and_taxes"] = display_mb["fees_and_taxes"].apply(format_inr)
    display_mb["explained_difference"] = display_mb["explained_difference"].apply(format_inr)
    display_mb["unexplained_difference"] = display_mb["unexplained_difference"].apply(format_inr)

    st.dataframe(display_mb, use_container_width=True, hide_index=True)

st.markdown("<br><hr><small style='color: gray;'>MarketMatch • Demo project. Not tax advice.</small>", unsafe_allow_html=True)
