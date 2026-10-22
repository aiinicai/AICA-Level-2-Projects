"""
Page 5: Month-wise Bridge (pages/5_Month_wise_Bridge.py)
Multi-month comparative financial bridge:
Sales, GST declared, and Payout received side-by-side with explained vs unexplained variance.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core.session import init_session_state
from core.formatting import format_inr

init_session_state()

st.title("📊 Month-wise Comparative Bridge")
st.markdown("Side-by-side reconciliation across multiple filing periods separating explained timing/fee deductions from unexplained discrepancies.")

if not st.session_state.month_bridge:
    st.info("No multi-month data available. Please load demo data or upload reports.")
    st.stop()

mb = st.session_state.month_bridge

# Visual Comparisons
df_mb = pd.DataFrame(mb)

st.subheader("1. Monthly Financial Trends")
fig_trend = go.Figure()

fig_trend.add_trace(go.Bar(
    x=df_mb["period"],
    y=[float(v) for v in df_mb["net_sales"]],
    name="Net Sales (MTR)",
    marker_color="#0d6efd"
))

fig_trend.add_trace(go.Bar(
    x=df_mb["period"],
    y=[float(v) for v in df_mb["payout_total"]],
    name="Total Disbursements",
    marker_color="#198754"
))

fig_trend.add_trace(go.Bar(
    x=df_mb["period"],
    y=[float(v) for v in df_mb["fees_and_taxes"]],
    name="Marketplace Fees & Taxes",
    marker_color="#ffc107"
))

fig_trend.update_layout(
    barmode="group",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(title="Amount in INR (₹)", gridcolor="#e9ecef"),
    margin=dict(l=20, r=20, t=30, b=20)
)
st.plotly_chart(fig_trend, use_container_width=True)

st.markdown("---")
st.subheader("2. Detailed Period-wise Reconciliation Bridge")

disp_mb = df_mb.copy()
disp_mb["gross_sales"] = disp_mb["gross_sales"].apply(format_inr)
disp_mb["refunds"] = disp_mb["refunds"].apply(format_inr)
disp_mb["net_sales"] = disp_mb["net_sales"].apply(format_inr)
disp_mb["gst_taxable"] = disp_mb["gst_taxable"].apply(format_inr)
disp_mb["payout_released"] = disp_mb["payout_released"].apply(format_inr)
disp_mb["payout_deferred"] = disp_mb["payout_deferred"].apply(format_inr)
disp_mb["payout_total"] = disp_mb["payout_total"].apply(format_inr)
disp_mb["fees_and_taxes"] = disp_mb["fees_and_taxes"].apply(format_inr)
disp_mb["explained_difference"] = disp_mb["explained_difference"].apply(format_inr)
disp_mb["unexplained_difference"] = disp_mb["unexplained_difference"].apply(format_inr)

st.dataframe(
    disp_mb,
    use_container_width=True,
    hide_index=True,
    column_config={
        "period": "Period (YYYY-MM)",
        "gross_sales": "Gross Sales",
        "refunds": "Returns",
        "net_sales": "Net Sales",
        "gst_taxable": "GST Reported",
        "payout_released": "Released Payout",
        "payout_deferred": "Deferred Payout",
        "payout_total": "Total Payout",
        "fees_and_taxes": "Fees & Taxes",
        "explained_difference": "Explained Difference",
        "unexplained_difference": "Unexplained Discrepancy"
    }
)

st.markdown("<br><hr><small style='color: gray;'>MarketMatch • Demo project. Not tax advice.</small>", unsafe_allow_html=True)
