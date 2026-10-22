"""
Session State and App-Wide Data Lifecycle Management for MarketMatch.
Provides centralized helpers for loading data, running reconciliations,
handling demo data, and syncing with SQLite.
"""
import os
import streamlit as st

from core.db import init_db, get_all_settings, get_external_figures, upsert_exception
from core.parsers import parse_mtr, parse_gst_rtf, parse_payments
from core.sales_to_payout import reconcile_sales_to_payout
from core.sales_to_gst import (
    route_mtr_to_gst_sections, reconcile_b2cs,
    reconcile_b2cl_and_cdnur, reconcile_hsn
)
from core.tcs_tds import reconcile_tcs_tds
from core.bridge import compute_month_wise_bridge

DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_data", "demo")


def init_session_state():
    """Ensure database and session state keys are initialized."""
    init_db()

    defaults = {
        "period_month": 3,
        "period_year": 2026,
        "mtr_data": None,
        "gst_data": None,
        "gst_totals": None,
        "pay_data": None,
        "mtr_report": None,
        "gst_report": None,
        "pay_report": None,
        "order_reconciliation": None,
        "kpi_summary": None,
        "b2cs_tie_out": None,
        "b2cl_reconciled": None,
        "cdnur_reconciled": None,
        "hsn_tie_out": None,
        "tcs_tds_result": None,
        "month_bridge": None,
        "demo_loaded": False,
        "active_file_names": {"mtr": None, "gst": None, "pay": None}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def load_demo_dataset():
    """Load the synthetic demo dataset and trigger full reconciliation."""
    mtr_path = os.path.join(DEMO_DIR, "demo_mtr.csv")
    gst_path = os.path.join(DEMO_DIR, "demo_gst_rtf.xlsx")
    pay_path = os.path.join(DEMO_DIR, "demo_payments.csv")

    if not os.path.exists(mtr_path) or not os.path.exists(gst_path) or not os.path.exists(pay_path):
        from sample_data.demo.generate_demo_data import generate_all_demo_data
        generate_all_demo_data()

    with open(mtr_path, "rb") as f:
        mtr_bytes = f.read()
    with open(gst_path, "rb") as f:
        gst_bytes = f.read()
    with open(pay_path, "rb") as f:
        pay_bytes = f.read()

    settings = get_all_settings()

    # Parse MTR
    mtr_records, mtr_report = parse_mtr(
        mtr_bytes, "demo_mtr.csv",
        period_month=st.session_state.period_month,
        period_year=st.session_state.period_year,
        tolerance=settings["tolerance"]
    )
    # Parse GST RTF
    gst_sections, gst_report, gst_totals = parse_gst_rtf(
        gst_bytes, "demo_gst_rtf.xlsx",
        filing_month=st.session_state.period_month,
        filing_year=st.session_state.period_year,
        tolerance=settings["tolerance"]
    )
    # Parse Payments
    pay_records, pay_report = parse_payments(
        pay_bytes, "demo_payments.csv",
        period_month=st.session_state.period_month,
        period_year=st.session_state.period_year,
        tolerance=settings["tolerance"]
    )

    st.session_state.mtr_data = mtr_records
    st.session_state.mtr_report = mtr_report
    st.session_state.gst_data = gst_sections
    st.session_state.gst_report = gst_report
    st.session_state.gst_totals = gst_totals
    st.session_state.pay_data = pay_records
    st.session_state.pay_report = pay_report
    st.session_state.demo_loaded = True
    st.session_state.active_file_names = {
        "mtr": "demo_mtr.csv",
        "gst": "demo_gst_rtf.xlsx",
        "pay": "demo_payments.csv"
    }

    run_full_reconciliation()


def clear_all_data():
    """Clear in-memory reconciliation data."""
    st.session_state.mtr_data = None
    st.session_state.gst_data = None
    st.session_state.gst_totals = None
    st.session_state.pay_data = None
    st.session_state.mtr_report = None
    st.session_state.gst_report = None
    st.session_state.pay_report = None
    st.session_state.order_reconciliation = None
    st.session_state.kpi_summary = None
    st.session_state.b2cs_tie_out = None
    st.session_state.b2cl_reconciled = None
    st.session_state.cdnur_reconciled = None
    st.session_state.hsn_tie_out = None
    st.session_state.tcs_tds_result = None
    st.session_state.month_bridge = None
    st.session_state.demo_loaded = False
    st.session_state.active_file_names = {"mtr": None, "gst": None, "pay": None}


def run_full_reconciliation():
    """Run all 3 layers of reconciliation and persist exceptions to DB."""
    if not st.session_state.mtr_data and not st.session_state.pay_data:
        return

    settings = get_all_settings()
    mtr_data = st.session_state.mtr_data or []
    gst_data = st.session_state.gst_data or {"b2cs": [], "b2cl": [], "cdnur": [], "hsn": [], "b2b": [], "cdnr": []}
    pay_data = st.session_state.pay_data or []

    # 1. Layer A: Sales to Payout
    reconciled_orders, kpi_summary = reconcile_sales_to_payout(
        mtr_records=mtr_data,
        payment_records=pay_data,
        as_of=settings["as_of_date"],
        tolerance=settings["tolerance"],
        unpaid_threshold_days=settings["unpaid_threshold_days"],
        gst_rate_on_fees=settings["gst_rate_on_fees"]
    )
    st.session_state.order_reconciliation = reconciled_orders
    st.session_state.kpi_summary = kpi_summary

    # 2. Layer B: Sales to GST reported
    routed = route_mtr_to_gst_sections(mtr_data, b2cl_threshold=settings["b2cl_threshold"])
    st.session_state.b2cs_tie_out = reconcile_b2cs(routed["b2cs"], gst_data.get("b2cs", []), tolerance=settings["tolerance"])
    st.session_state.b2cl_reconciled = reconcile_b2cl_and_cdnur(routed["b2cl"], gst_data.get("b2cl", []), is_cdnur=False, tolerance=settings["tolerance"])
    st.session_state.cdnur_reconciled = reconcile_b2cl_and_cdnur(routed["cdnur"], gst_data.get("cdnur", []), is_cdnur=True, tolerance=settings["tolerance"])
    st.session_state.hsn_tie_out = reconcile_hsn(routed["hsn"], gst_data.get("hsn", []), tolerance=settings["tolerance"])

    # 3. Layer C: TCS and TDS
    period_key = f"{st.session_state.period_year}-{st.session_state.period_month:02d}"
    ext = get_external_figures(period_key)
    st.session_state.tcs_tds_result = reconcile_tcs_tds(
        mtr_records=mtr_data,
        payment_records=pay_data,
        tcs_statutory_rate=settings["tcs_statutory_rate"],
        tds_statutory_rate=settings["tds_statutory_rate"],
        gstr8_net_taxable=ext["gstr8_net_taxable"],
        gstr8_tcs=ext["gstr8_tcs"],
        form26as_tds=ext["form26as_tds"],
        tolerance=settings["tolerance"]
    )

    # 4. Month Bridge
    st.session_state.month_bridge = compute_month_wise_bridge(
        mtr_records=mtr_data,
        gst_sections=gst_data,
        payment_records=pay_data,
        order_reconciliation=reconciled_orders
    )

    # 5. Sync exceptions to SQLite
    for ord_res in reconciled_orders:
        if ord_res["status"] in ("Short paid", "Not paid", "Duplicate payout", "Refund without credit note", "Payout without order"):
            rec_amt = abs(ord_res["difference"])
            upsert_exception(
                exc_id=f"EXC-{ord_res['order_id']}",
                order_id=ord_res["order_id"],
                invoice_no=ord_res["invoice_no"],
                reason_code=ord_res["reason_code"],
                description=ord_res["details"],
                recoverable_amount=float(rec_amt),
                status="Open",
                source_ref=ord_res["status"]
            )
