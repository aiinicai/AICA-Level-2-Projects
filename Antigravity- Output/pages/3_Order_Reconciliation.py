"""
Page 3: Order Reconciliation (pages/3_Order_Reconciliation.py)
Layer A Order-Level Reconciliation.
Grid with status filters, search, and detailed drawer showing full financial bridge.
"""
import streamlit as st
import pandas as pd

from core.session import init_session_state
from core.formatting import format_inr, status_badge_html, reason_badge_html

init_session_state()

st.title("📦 Order Reconciliation (Layer A: Sales ↔ Payments)")
st.markdown("Reconciliation at the individual order level comparing contractual expected net disbursements with actual Amazon settlements.")

if not st.session_state.order_reconciliation:
    st.info("No order reconciliation data available. Please load demo data or upload reports.")
    st.stop()

orders = st.session_state.order_reconciliation

# Filter Controls
col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
all_statuses = sorted(list(set(r["status"] for r in orders)))
with col_f1:
    sel_status = st.multiselect("Filter by Status", all_statuses, default=[])
with col_f2:
    all_reasons = sorted(list(set(r["reason_code"] for r in orders)))
    sel_reason = st.multiselect("Filter by Reason Code", all_reasons, default=[])
with col_f3:
    search_q = st.text_input("Search Order ID or Invoice Number", placeholder="e.g. 402-1000001 or IN-2026-101")

# Apply Filters
filtered_orders = orders
if sel_status:
    filtered_orders = [r for r in filtered_orders if r["status"] in sel_status]
if sel_reason:
    filtered_orders = [r for r in filtered_orders if r["reason_code"] in sel_reason]
if search_q.strip():
    q = search_q.strip().upper()
    filtered_orders = [
        r for r in filtered_orders
        if q in str(r.get("order_id", "")).upper() or q in str(r.get("invoice_no", "")).upper()
    ]

# Summary Bar
st.write(f"Showing **{len(filtered_orders)}** of **{len(orders)}** reconciled orders")

# Display Grid
grid_data = []
for r in filtered_orders:
    grid_data.append({
        "Order ID": r["order_id"],
        "Invoice No": r["invoice_no"],
        "Invoice Date": r["invoice_date"],
        "Status": r["status"],
        "Reason": r["reason_code"],
        "Net Sales": format_inr(r["net_sales"]),
        "Fees": format_inr(abs(r["selling_fees"]) + abs(r["fba_fees"]) + abs(r["other_fees"])),
        "TCS & TDS": format_inr(abs(r["tcs"]) + abs(r["tds"])),
        "Expected Payout": format_inr(r["expected_payout"]),
        "Actual Payout": format_inr(r["actual_payout"]),
        "Difference": format_inr(r["difference"]),
        "Payout Status": r["payout_status"],
        "Settlement Date": r.get("payout_date") or "-"
    })

df_grid = pd.DataFrame(grid_data)
st.dataframe(df_grid, use_container_width=True, hide_index=True)

# Order Audit Detail Drawer
st.markdown("---")
st.subheader("🔍 Order Audit & Financial Bridge Drawer")

selected_oid = st.selectbox(
    "Select an Order to Inspect Complete Financial Bridge:",
    [r["order_id"] for r in filtered_orders],
    index=0 if filtered_orders else None
)

if selected_oid:
    ord_rec = next((r for r in filtered_orders if r["order_id"] == selected_oid), None)
    if ord_rec:
        st.markdown(f"#### Audit Breakdown: Order `{ord_rec['order_id']}`")
        col_badge1, col_badge2, col_badge3 = st.columns(3)
        col_badge1.markdown(f"**Classification:** {status_badge_html(ord_rec['status'])}", unsafe_allow_html=True)
        col_badge2.markdown(f"**Reason Code:** {reason_badge_html(ord_rec['reason_code'])}", unsafe_allow_html=True)
        col_badge3.write(f"**Disbursement Status:** `{ord_rec['payout_status']}`")

        st.info(f"**Audit Note:** {ord_rec['details']}")

        # Bridge Table
        st.markdown("##### Financial Bridge Breakdown")
        bridge_rows = [
            {"Component": "Gross Invoice Value (MTR)", "Amount": format_inr(ord_rec["gross_sales"]), "Effect": "(+)"},
            {"Component": "Returns & Refunds Deducted", "Amount": format_inr(ord_rec["refunds"]), "Effect": "(-)"},
            {"Component": "Net Sales Value", "Amount": format_inr(ord_rec["net_sales"]), "Effect": "Subtotal"},
            {"Component": "Amazon Selling Fees", "Amount": format_inr(abs(ord_rec["selling_fees"])), "Effect": "(-)"},
            {"Component": "Amazon FBA Fees", "Amount": format_inr(abs(ord_rec["fba_fees"])), "Effect": "(-)"},
            {"Component": "Other Transaction Fees", "Amount": format_inr(abs(ord_rec["other_fees"])), "Effect": "(-)"},
            {"Component": "GST on Fees (18%)", "Amount": format_inr(abs(ord_rec["gst_on_fees"])), "Effect": "(-)"},
            {"Component": "TCS (GST Deducted)", "Amount": format_inr(abs(ord_rec["tcs"])), "Effect": "(-)"},
            {"Component": "TDS (Section 194-O)", "Amount": format_inr(abs(ord_rec["tds"])), "Effect": "(-)"},
            {"Component": "Promotional Rebates / Adjustments", "Amount": format_inr(ord_rec["promo_rebates"]), "Effect": "(+/-)"},
            {"Component": "Contractual Expected Net Payout", "Amount": format_inr(ord_rec["expected_payout"]), "Effect": "Target"},
            {"Component": "Actual Amazon Settlement Received", "Amount": format_inr(ord_rec["actual_payout"]), "Effect": "Actual"},
            {"Component": "Discrepancy (Unexplained / Shortfall)", "Amount": format_inr(ord_rec["unexplained"]), "Effect": "Variance"}
        ]
        df_bridge = pd.DataFrame(bridge_rows)
        st.table(df_bridge)

        # Source Records
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.write(f"**Source MTR Rows:** {ord_rec['source_mtr_rows']}")
            st.write(f"Invoice Number: `{ord_rec['invoice_no']}`")
            st.write(f"Invoice Date: `{ord_rec['invoice_date']}`")

        with col_s2:
            st.write(f"**Source Payments Rows:** {ord_rec['source_pay_rows']}")
            st.write(f"Settlement Date: `{ord_rec.get('payout_date') or 'Pending'}`")
            st.write(f"Release Date: `{ord_rec.get('release_date') or 'Pending'}`")

st.markdown("<br><hr><small style='color: gray;'>MarketMatch • Demo project. Not tax advice.</small>", unsafe_allow_html=True)
