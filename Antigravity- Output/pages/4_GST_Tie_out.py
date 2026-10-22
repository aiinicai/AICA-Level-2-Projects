"""
Page 4: GST Tie-out (pages/4_GST_Tie_out.py)
Layer B Reconciliation by GSTR-1 Section:
- B2C Small (Headline tie-out, State & Rate breakdown, Underlying Invoices drilldown)
- B2C Large & CDNUR (Invoice-wise and Note-wise reconciliation)
- HSN Summary (HSN & Rate tie-out, exact vs 4-digit prefix, Tax Gap analysis)
"""
import streamlit as st
import pandas as pd
from decimal import Decimal

from core.session import init_session_state
from core.formatting import format_inr

init_session_state()

st.title("🏛️ GST Tie-Out (Layer B: Sales ↔ GST Reported)")
st.markdown("Multi-section audit comparing sales recorded in MTR with sales declared in the Amazon GSTR-1 Ready-to-File export.")

if not st.session_state.b2cs_tie_out and not st.session_state.hsn_tie_out:
    st.info("No GST tie-out data available. Please load demo data or upload reports.")
    st.stop()

sec_tabs = st.tabs(["B2C Small (B2CS)", "B2C Large (B2CL)", "Credit Notes (CDNUR)", "HSN Summary"])

# =========================================================================
# TAB 1: B2C Small
# =========================================================================
with sec_tabs[0]:
    b2cs_data = st.session_state.b2cs_tie_out
    if not b2cs_data:
        st.caption("No B2CS data available.")
    else:
        hl = b2cs_data["headline"]
        st.subheader("1. Headline Tie-Out")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("MTR Gross Shipments", format_inr(hl["mtr_shipments_taxable"]))
        c2.metric("MTR Returns Deducted", format_inr(hl["mtr_returns_taxable"]))
        c3.metric("MTR Net Taxable", format_inr(hl["mtr_net_taxable"]))
        c4.metric("GST Reported Taxable", format_inr(hl["gst_total_taxable"]))

        diff = hl["difference"]
        if hl["is_matched"]:
            st.success(f"✅ B2C Small Headline Check PASSED! Difference is within tolerance ({format_inr(diff)}).")
        else:
            st.error(f"⚠️ B2C Small Headline Check DISCREPANCY: MTR Net Taxable differs from GST Report by {format_inr(diff)}.")

        st.markdown("---")
        st.subheader("2. State & GST Rate Slabs Breakdown")

        breakdown = b2cs_data["breakdown"]
        tbl_data = []
        for b in breakdown:
            tbl_data.append({
                "State Code": b["pos_code"],
                "State Name": b["pos_name"],
                "Rate": b["rate_display"],
                "MTR Taxable": format_inr(b["mtr_taxable"]),
                "GST Taxable": format_inr(b["gst_taxable"]),
                "Difference": format_inr(b["difference"]),
                "Status": "Matched" if b["is_matched"] else "Discrepancy",
                "Reason Code": b["reason_code"],
                "Invoices Count": len(b["underlying_invoices"])
            })

        df_b2cs = pd.DataFrame(tbl_data)
        st.dataframe(df_b2cs, use_container_width=True, hide_index=True)

        # Drilldown to Underlying Invoices
        st.markdown("---")
        st.subheader("3. Underlying MTR Invoices Drilldown")
        selected_state = st.selectbox(
            "Select State / Rate Group to View Underlying Sales Invoices:",
            [f"{b['pos_code']} - {b['pos_name']} ({b['rate_display']})" for b in breakdown]
        )
        if selected_state:
            sel_code = selected_state.split(" - ")[0]
            matched_b = next((b for b in breakdown if b["pos_code"] == sel_code), None)
            if matched_b and matched_b["underlying_invoices"]:
                st.write(f"Displaying **{len(matched_b['underlying_invoices'])}** underlying sales / refund lines:")
                df_invs = pd.DataFrame(matched_b["underlying_invoices"])
                df_invs["taxable_value"] = df_invs["taxable_value"].apply(format_inr)
                df_invs["invoice_value"] = df_invs["invoice_value"].apply(format_inr)
                st.dataframe(df_invs, use_container_width=True, hide_index=True)
            else:
                st.caption("No sales invoices found in MTR for this state group.")

# =========================================================================
# TAB 2: B2C Large
# =========================================================================
with sec_tabs[1]:
    st.subheader("B2C Large Invoices (Inter-state sales > Threshold)")
    b2cl_rows = st.session_state.b2cl_reconciled
    if not b2cl_rows:
        st.caption("No B2C Large invoices recorded in this period.")
    else:
        df_b2cl = pd.DataFrame(b2cl_rows)
        disp_b2cl = df_b2cl.copy()
        disp_b2cl["mtr_taxable"] = disp_b2cl["mtr_taxable"].apply(format_inr)
        disp_b2cl["gst_taxable"] = disp_b2cl["gst_taxable"].apply(format_inr)
        disp_b2cl["difference"] = disp_b2cl["difference"].apply(format_inr)
        st.dataframe(
            disp_b2cl[["doc_no", "order_id", "status", "reason_code", "mtr_taxable", "gst_taxable", "difference", "details"]],
            use_container_width=True, hide_index=True
        )

# =========================================================================
# TAB 3: CDNUR
# =========================================================================
with sec_tabs[2]:
    st.subheader("CDNUR (Credit Notes / Refunds against B2CL)")
    cdnur_rows = st.session_state.cdnur_reconciled
    if not cdnur_rows:
        st.caption("No CDNUR credit notes recorded in this period.")
    else:
        df_cdnur = pd.DataFrame(cdnur_rows)
        disp_cdnur = df_cdnur.copy()
        disp_cdnur["mtr_taxable"] = disp_cdnur["mtr_taxable"].apply(format_inr)
        disp_cdnur["gst_taxable"] = disp_cdnur["gst_taxable"].apply(format_inr)
        disp_cdnur["difference"] = disp_cdnur["difference"].apply(format_inr)
        st.dataframe(
            disp_cdnur[["doc_no", "order_id", "status", "reason_code", "mtr_taxable", "gst_taxable", "difference", "details"]],
            use_container_width=True, hide_index=True
        )

# =========================================================================
# TAB 4: HSN Summary
# =========================================================================
with sec_tabs[3]:
    st.subheader("HSN Summary Reconciliation")
    st.markdown("Compares product-wise HSN codes, sales quantities, and checks statutory tax alignment.")
    hsn_rows = st.session_state.hsn_tie_out
    if not hsn_rows:
        st.caption("No HSN summary data available.")
    else:
        tbl_hsn = []
        for h in hsn_rows:
            tbl_hsn.append({
                "HSN Code": h["hsn"],
                "Rate": h["rate_display"],
                "Match Method": h["match_method"],
                "GST Taxable": format_inr(h["gst_taxable"]),
                "MTR Taxable": format_inr(h["mtr_taxable"]),
                "Taxable Diff": format_inr(h["taxable_difference"]),
                "GST Qty": h["gst_quantity"],
                "MTR Qty": h["mtr_quantity"],
                "Qty Diff": h["quantity_difference"],
                "Reported Tax": format_inr(h["gst_reported_tax"]),
                "Statutory Expected Tax": format_inr(h["expected_statutory_tax"]),
                "Tax Gap": format_inr(h["tax_gap"]),
                "Status": h["reason_code"]
            })
        st.dataframe(pd.DataFrame(tbl_hsn), use_container_width=True, hide_index=True)

        # Tax Gap Advisory Notice
        has_tax_gap = any(abs(h["tax_gap"]) > Decimal("1.00") for h in hsn_rows)
        if has_tax_gap:
            st.warning(
                "⚠️ **Audit Notice - Internal Report Gap Detected:** In the GSTR-1 export, the sum of tax columns "
                "(Integrated + Central + State Tax) is lower than Rate × Taxable Value across certain HSN rows. "
                "Cross-referencing MTR item sales confirms that Amazon's GSTR-1 generator omitted shipping GST or applied truncated rounding. "
                "Sellers should report actual tax payable from sales invoices to avoid GST audit notices."
            )

st.markdown("<br><hr><small style='color: gray;'>MarketMatch • Demo project. Not tax advice.</small>", unsafe_allow_html=True)
