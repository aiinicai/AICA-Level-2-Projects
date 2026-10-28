"""
MarketMatch – Amazon Sales, Payout & GST Reconciliation
Entry Point & Executive Dashboard.
"""
import streamlit as st
import pandas as pd
from decimal import Decimal

from core.session import init_session_state, load_demo_dataset, clear_all_data, run_full_reconciliation
from core.formatting import format_inr
from core.bridge import compute_waterfall_data, create_waterfall_figure
from core.db import get_all_settings

st.set_page_config(
    page_title="MarketMatch – Amazon Sales, Payout & GST Reconciliation",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_session_state()
settings = get_all_settings()

# Sidebar Setup
with st.sidebar:
    st.title("⚖️ MarketMatch")
    st.caption("Amazon India Marketplace Reconciliation")
    st.markdown("---")

    # Reporting Period Selector
    st.subheader("📅 Active Period")
    c_m, c_y = st.columns(2)
    with c_m:
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        selected_month_idx = st.selectbox("Month", range(1, 13), format_func=lambda x: months[x - 1], index=st.session_state.period_month - 1)
        if selected_month_idx != st.session_state.period_month:
            st.session_state.period_month = selected_month_idx
            run_full_reconciliation()
            st.rerun()

    with c_y:
        selected_year = st.selectbox("Year", [2024, 2025, 2026, 2027], index=2)
        if selected_year != st.session_state.period_year:
            st.session_state.period_year = selected_year
            run_full_reconciliation()
            st.rerun()

    st.markdown("---")
    st.subheader("⚡ Quick Actions")
    col_demo, col_clear = st.columns(2)
    with col_demo:
        if st.button("Load Demo Data", type="primary", use_container_width=True):
            with st.spinner("Loading synthetic dataset..."):
                load_demo_dataset()
            st.success("Demo dataset loaded!")
            st.rerun()

    with col_clear:
        if st.button("Clear Data", use_container_width=True):
            clear_all_data()
            st.info("Reconciliation cleared.")
            st.rerun()

    st.markdown("---")
    st.subheader("📌 Active Dataset")
    if st.session_state.active_file_names.get("mtr"):
        st.write(f"**Sales (MTR):** `{st.session_state.active_file_names['mtr']}`")
        st.write(f"**GST Report:** `{st.session_state.active_file_names['gst'] or 'N/A'}`")
        st.write(f"**Payments:** `{st.session_state.active_file_names['pay'] or 'N/A'}`")
    else:
        st.caption("No files uploaded yet. Upload reports or load demo data.")

    st.markdown("---")
    st.markdown(
        "<small style='color: gray;'>MarketMatch v1.0 • Runs Fully Locally<br><b>Demo project. Not tax advice.</b></small>",
        unsafe_allow_html=True
    )

# Main Dashboard View
st.title("⚖️ Executive Reconciliation Dashboard")
st.markdown("Automated three-way financial audit: **Merchant Tax Report (Sales)** ↔ **GST Ready-to-File (Taxes)** ↔ **Amazon Payments (Disbursements)**.")

# Empty State Notice
if not st.session_state.order_reconciliation:
    st.info("👋 Welcome to MarketMatch! To begin reconciliation, please click **'Load Demo Data'** in the left sidebar, or head over to the **'2 Upload and Map'** page to upload your actual Amazon files.")
    
    st.markdown("### 🔍 How MarketMatch Reconciles Amazon Reports")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("""
        **Layer A: Sales ↔ Payouts**
        - Order-level financial bridge
        - Contractual deductions verification
        - Deferred / Timing classification
        - Short & Unpaid order detection
        """)
    with col_b:
        st.markdown("""
        **Layer B: Sales ↔ GST Reported**
        - GSTR-1 section auto-routing
        - B2C Small state & slab breakdown
        - B2C Large & CDNUR audit
        - HSN summary & tax column checks
        """)
    with col_c:
        st.markdown("""
        **Layer C: TCS & TDS Compliance**
        - MTR TCS vs Payments TCS vs Statutory
        - Section 194-O TDS validation
        - GSTR-8 Table 4 reconciliation
        - Form 26AS matching
        """)
    st.stop()

# Reconciled KPI Metrics
kpi = st.session_state.kpi_summary
gst_totals = st.session_state.gst_totals or {}
b2cs_gst_taxable = gst_totals.get("b2cs", {}).get("taxable_value", Decimal("0.00"))

st.markdown("### 📊 Executive Metrics")
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

# Executive Waterfall Chart
st.subheader("🌊 Executive Waterfall: Sales to Payout Bridge")
waterfall_data = compute_waterfall_data(kpi)
fig_waterfall = create_waterfall_figure(waterfall_data)
st.plotly_chart(fig_waterfall, use_container_width=True)

# Order Status Distribution
st.markdown("---")
st.subheader("📋 Order Status Breakdown")

status_counts = {
    "Matched": kpi["matched_count"],
    "Awaiting release (Timing)": kpi["awaiting_release_count"],
    "Timing difference": kpi["timing_diff_count"],
    "Short paid": kpi["short_paid_count"],
    "Excess paid": kpi["excess_paid_count"],
    "Not paid": kpi["not_paid_count"],
    "Duplicate payout": kpi["duplicate_count"],
    "Payout without order": kpi["payout_without_order_count"]
}

col_p1, col_p2 = st.columns([1, 2])
with col_p1:
    df_status = pd.DataFrame([
        {"Status": k, "Count": v}
        for k, v in status_counts.items() if v > 0
    ])
    st.dataframe(df_status, use_container_width=True, hide_index=True)

with col_p2:
    if not df_status.empty:
        import plotly.express as px
        fig_pie = px.pie(df_status, names="Status", values="Count", title="Order Classification Distribution", hole=0.4)
        fig_pie.update_layout(margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig_pie, use_container_width=True)

# Month-wise Side-by-Side Summary
st.markdown("---")
st.subheader("📅 Month-Wise Difference Table")
if st.session_state.month_bridge:
    df_mb = pd.DataFrame(st.session_state.month_bridge)
    # Format currency columns for display
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

    st.dataframe(
        display_mb,
        use_container_width=True,
        hide_index=True,
        column_config={
            "period": "Reporting Month",
            "gross_sales": "Gross Sales",
            "refunds": "Returns",
            "net_sales": "Net Sales",
            "gst_taxable": "GST Taxable",
            "payout_released": "Released Payout",
            "payout_deferred": "Deferred Payout",
            "payout_total": "Total Payout",
            "fees_and_taxes": "Fees & Taxes",
            "explained_difference": "Explained Diff",
            "unexplained_difference": "Unexplained Diff"
        }
    )
else:
    st.caption("No multi-month data available.")

st.markdown("---")
st.markdown("<small style='color: gray;'>MarketMatch • Demo project. Not tax advice.</small>", unsafe_allow_html=True)
