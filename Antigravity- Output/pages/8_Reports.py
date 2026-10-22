"""
Page 8: Reports & Exports (pages/8_Reports.py)
Generates comprehensive multi-sheet Excel reports and CSV exports:
Sheets:
1. Summary bridge
2. Order reconciliation
3. GST tie-out per section
4. TCS-TDS
5. Exceptions
6. Assumptions
"""
import io
import streamlit as st
import pandas as pd

from core.session import init_session_state
from core.db import get_all_settings, get_all_exceptions

init_session_state()
settings = get_all_settings()

st.title("📄 Audit Reports & Exports")
st.markdown("Download comprehensive financial workbooks and discrepancy audit schedules.")

if not st.session_state.order_reconciliation:
    st.info("No reconciliation data available to export. Please load demo data or upload reports.")
    st.stop()

# Helper function to generate multi-sheet Excel file
def generate_audit_excel_workbook() -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: Summary Bridge
        if st.session_state.month_bridge:
            df_mb = pd.DataFrame(st.session_state.month_bridge)
            df_mb.to_excel(writer, sheet_name="Summary bridge", index=False)

        # Sheet 2: Order Reconciliation
        if st.session_state.order_reconciliation:
            df_orders = pd.DataFrame(st.session_state.order_reconciliation)
            # Drop complex objects for clean Excel export
            clean_orders = df_orders.drop(columns=["invoice_date_dt"], errors="ignore")
            clean_orders.to_excel(writer, sheet_name="Order reconciliation", index=False)

        # Sheet 3: GST Tie-Out
        gst_rows = []
        if st.session_state.b2cs_tie_out:
            for b in st.session_state.b2cs_tie_out["breakdown"]:
                gst_rows.append({
                    "Section": "B2C Small",
                    "POS Code": b["pos_code"],
                    "POS Name": b["pos_name"],
                    "Rate": b["rate_display"],
                    "MTR Taxable": float(b["mtr_taxable"]),
                    "GST Taxable": float(b["gst_taxable"]),
                    "Difference": float(b["difference"]),
                    "Status": b["reason_code"]
                })
        if st.session_state.hsn_tie_out:
            for h in st.session_state.hsn_tie_out:
                gst_rows.append({
                    "Section": "HSN Summary",
                    "POS Code": h["hsn"],
                    "POS Name": f"Rate {h['rate_display']}",
                    "Rate": h["rate_display"],
                    "MTR Taxable": float(h["mtr_taxable"]),
                    "GST Taxable": float(h["gst_taxable"]),
                    "Difference": float(h["taxable_difference"]),
                    "Status": h["reason_code"]
                })
        if gst_rows:
            pd.DataFrame(gst_rows).to_excel(writer, sheet_name="GST tie-out per section", index=False)

        # Sheet 4: TCS-TDS
        if st.session_state.tcs_tds_result:
            s = st.session_state.tcs_tds_result["summary"]
            tcs_rows = [
                {"Metric": "Net Taxable Sales (MTR)", "Amount": float(s["mtr_net_taxable"])},
                {"Metric": "Gross Invoice Value (MTR)", "Amount": float(s["mtr_gross_invoice"])},
                {"Metric": "Statutory TCS Expected (0.5%)", "Amount": float(s["expected_tcs_statutory"])},
                {"Metric": "MTR TCS Total", "Amount": float(s["mtr_tcs_total"])},
                {"Metric": "Payments TCS Total", "Amount": float(s["pay_tcs_total"])},
                {"Metric": "TCS Variance (MTR vs Payments)", "Amount": float(s["tcs_mtr_vs_pay"])},
                {"Metric": "Statutory TDS Expected (0.1%)", "Amount": float(s["expected_tds_statutory"])},
                {"Metric": "Payments TDS Total", "Amount": float(s["pay_tds_total"])},
                {"Metric": "TDS Variance (Payments vs Statutory)", "Amount": float(s["tds_pay_vs_statutory"])}
            ]
            pd.DataFrame(tcs_rows).to_excel(writer, sheet_name="TCS-TDS", index=False)

        # Sheet 5: Exceptions
        exceptions = get_all_exceptions()
        if exceptions:
            pd.DataFrame(exceptions).to_excel(writer, sheet_name="Exceptions", index=False)

        # Sheet 6: Assumptions
        assumptions = [
            {"Parameter": "Application Name", "Configured Value": "MarketMatch – Amazon Sales, Payout & GST Reconciliation"},
            {"Parameter": "Rounding Precision", "Configured Value": "Decimal / Paise 2 decimal places (float noise stripped)"},
            {"Parameter": "Currency Format", "Configured Value": "Indian Numbering (₹ 1,23,456.00)"},
            {"Parameter": "Discrepancy Tolerance", "Configured Value": f"₹ {settings['tolerance']}"},
            {"Parameter": "Unpaid Settlement Threshold", "Configured Value": f"{settings['unpaid_threshold_days']} days (unsettled orders within window marked Timing)"},
            {"Parameter": "B2C Large Threshold", "Configured Value": f"₹ {settings['b2cl_threshold']}"},
            {"Parameter": "Statutory TCS Rate", "Configured Value": f"{(settings['tcs_statutory_rate'] * 100):.2f}%"},
            {"Parameter": "Statutory TDS Rate", "Configured Value": f"{(settings['tds_statutory_rate'] * 100):.2f}% (Section 194-O)"},
            {"Parameter": "GST Rate on Marketplace Fees", "Configured Value": f"{(settings['gst_rate_on_fees'] * 100):.2f}%"},
            {"Parameter": "Deferred Row Handling", "Configured Value": "Classified strictly as 'Awaiting release (Timing)', never 'Not paid'"},
            {"Parameter": "HSN Tax Column Gap Notice", "Configured Value": "Observed gap in Amazon GSTR-1 export flagged and explained from MTR sales tax"}
        ]
        pd.DataFrame(assumptions).to_excel(writer, sheet_name="Assumptions", index=False)

    return output.getvalue()


# Generate CSV of exceptions
def generate_exceptions_csv() -> bytes:
    exceptions = get_all_exceptions()
    df_exc = pd.DataFrame(exceptions) if exceptions else pd.DataFrame(columns=["id", "order_id", "recoverable_amount"])
    return df_exc.to_csv(index=False).encode("utf-8")


st.subheader("📥 Download Audit Packages")

col_d1, col_d2 = st.columns(2)

with col_d1:
    st.markdown("### 📊 Comprehensive Excel Reconciliation Workbook")
    st.markdown("""
    Includes 6 complete sheets:
    - **Summary bridge:** Period-wise sales, GST and payout tie-out
    - **Order reconciliation:** Complete Layer A order-level bridge
    - **GST tie-out per section:** B2CS, B2CL, CDNUR, and HSN
    - **TCS-TDS:** Statutory withholding compliance audit
    - **Exceptions:** Detailed log of all open and claimed items
    - **Assumptions:** Configured tolerances, thresholds, and business rules
    """)
    excel_bytes = generate_audit_excel_workbook()
    st.download_button(
        label="Download Full Excel Audit (.xlsx)",
        data=excel_bytes,
        file_name=f"MarketMatch_Reconciliation_{st.session_state.period_year}_{st.session_state.period_month:02d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True
    )

with col_d2:
    st.markdown("### 🚨 Exceptions Schedule (CSV)")
    st.markdown("""
    Export only actionable discrepancies and short-paid orders:
    - Order IDs and invoice numbers
    - Reason codes (Fees, Returns, TCS/TDS, Duplicate, Missing payout)
    - Recoverable claim amounts in INR
    - Resolution lifecycle statuses and Seller Central case IDs
    """)
    csv_bytes = generate_exceptions_csv()
    st.download_button(
        label="Download Exceptions Schedule (.csv)",
        data=csv_bytes,
        file_name=f"MarketMatch_Exceptions_{st.session_state.period_year}_{st.session_state.period_month:02d}.csv",
        mime="text/csv",
        use_container_width=True
    )

st.markdown("<br><hr><small style='color: gray;'>MarketMatch • Demo project. Not tax advice.</small>", unsafe_allow_html=True)
