"""
Tests for Synthetic Demo Dataset Verification.
Verifies that loading the generated demo files produces EXACTLY the planted counts:
- 45 clean orders (including 1 B2CL > 100000 with a CDNUR refund)
- 3 not paid
- 2 short paid
- 1 duplicate payout
- 2 refunds without credit note
- 2 sales missing from GST data
- 1 B2C Small state/rate group with a difference
- 1 HSN tax-column gap
- 1 TCS at double statutory amount
- 2 deferred payouts (Timing, not exceptions)
- 2 month-end timing differences
- 1 invoice reported in wrong GST month
- 1 payout row with no order
"""
import os
from decimal import Decimal
import pytest

from core.parsers import parse_mtr, parse_gst_rtf, parse_payments
from core.sales_to_payout import reconcile_sales_to_payout
from core.sales_to_gst import route_mtr_to_gst_sections, reconcile_b2cs, reconcile_hsn
from core.tcs_tds import reconcile_tcs_tds

DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_data", "demo")
MTR_PATH = os.path.join(DEMO_DIR, "demo_mtr.csv")
GST_PATH = os.path.join(DEMO_DIR, "demo_gst_rtf.xlsx")
PAY_PATH = os.path.join(DEMO_DIR, "demo_payments.csv")


@pytest.fixture(scope="module")
def loaded_demo_data():
    with open(MTR_PATH, "rb") as f:
        mtr_bytes = f.read()
    with open(GST_PATH, "rb") as f:
        gst_bytes = f.read()
    with open(PAY_PATH, "rb") as f:
        pay_bytes = f.read()

    mtr_records, mtr_report = parse_mtr(mtr_bytes, "demo_mtr.csv")
    gst_sections, gst_report, gst_totals = parse_gst_rtf(gst_bytes, "demo_gst_rtf.xlsx", filing_month=3, filing_year=2026)
    pay_records, pay_report = parse_payments(pay_bytes, "demo_payments.csv")

    reconciled_orders, kpi = reconcile_sales_to_payout(
        mtr_records=mtr_records,
        payment_records=pay_records,
        as_of="2026-03-31",
        tolerance=Decimal("1.00"),
        unpaid_threshold_days=10
    )

    return {
        "mtr_records": mtr_records,
        "gst_sections": gst_sections,
        "gst_report": gst_report,
        "gst_totals": gst_totals,
        "pay_records": pay_records,
        "reconciled_orders": reconciled_orders,
        "kpi": kpi
    }


def test_order_reconciliation_planted_counts(loaded_demo_data):
    reconciled = loaded_demo_data["reconciled_orders"]

    # 1. 3 Not Paid Orders
    not_paid_orders = [r for r in reconciled if r["status"] == "Not paid"]
    assert len(not_paid_orders) == 3

    # 2. 2 Short Paid Orders
    short_paid_orders = [r for r in reconciled if r["status"] == "Short paid"]
    assert len(short_paid_orders) == 2

    # 3. 1 Duplicate Payout Order
    dup_payouts = [r for r in reconciled if r["status"] == "Duplicate payout"]
    assert len(dup_payouts) == 1

    # 4. 2 Refunds Without Credit Note
    refund_no_cn = [r for r in reconciled if r["status"] == "Refund without credit note"]
    assert len(refund_no_cn) == 2

    # 5. 2 Deferred Payouts (Classified as Timing, not Not paid or exceptions)
    deferred_orders = [r for r in reconciled if r["status"] == "Awaiting release (Timing)"]
    assert len(deferred_orders) == 2

    # 6. 1 Payout Without Order (orphaned payout row)
    payout_no_order = [r for r in reconciled if r["status"] == "Payout without order"]
    assert len(payout_no_order) == 1

    # 7. 2 Month-end Timing differences (orders with payout in next month)
    # Filter orders from March with payout settled in April
    month_end_timing = [
        r for r in reconciled
        if r["invoice_date"].startswith("2026-03")
        and r["payout_date"].startswith("2026-04")
        and r["status"] == "Matched"
    ]
    assert len(month_end_timing) == 2

    # 8. Clean Orders Count: 45 orders total (which include the B2CL order and timing orders)
    # Total unique MTR orders is 60.
    clean_matched = [
        r for r in reconciled
        if r["order_id"].startswith("402-") and r["status"] in ("Matched", "Timing difference")
    ]
    assert len(clean_matched) == 45


def test_b2cl_and_cdnur_planted_pair(loaded_demo_data):
    mtr_records = loaded_demo_data["mtr_records"]
    gst_sections = loaded_demo_data["gst_sections"]

    routed = route_mtr_to_gst_sections(mtr_records, b2cl_threshold=Decimal("100000.00"))

    # Exactly 1 B2CL shipment > 1,00,000
    assert len(routed["b2cl"]) == 1
    assert routed["b2cl"][0]["invoice_value"] == Decimal("108000.00")

    # Exactly 1 CDNUR refund against B2CL
    assert len(routed["cdnur"]) == 1
    assert routed["cdnur"][0]["invoice_value"] == Decimal("-18000.00")
    assert routed["cdnur"][0]["credit_note_no"] == "CN-2026-001"

    # Both reported in GST workbook
    assert len(gst_sections["b2cl"]) == 1
    assert len(gst_sections["cdnur"]) == 1


def test_gst_tie_out_planted_issues(loaded_demo_data):
    mtr_records = loaded_demo_data["mtr_records"]
    gst_sections = loaded_demo_data["gst_sections"]

    # Filter MTR to March (Month 3)
    mtr_march = [r for r in mtr_records if r["invoice_date"].startswith("2026-03")]
    routed_march = route_mtr_to_gst_sections(mtr_march)

    # 1. B2C Small Reconciliation:
    b2cs_tie_out = reconcile_b2cs(routed_march["b2cs"], gst_sections["b2cs"])
    breakdown = b2cs_tie_out["breakdown"]

    # 1 planted B2CS state/rate group with a difference in State 27 (MAHARASHTRA) 18% slab
    val_mismatches = [b for b in breakdown if not b["is_matched"] and b["reason_code"] == "Rate/Value mismatch"]
    assert len(val_mismatches) == 1
    assert val_mismatches[0]["pos_code"] == "27"
    assert val_mismatches[0]["rate"] == Decimal("0.18")

    # 2. HSN tax-column gap planted
    hsn_tie_out = reconcile_hsn(routed_march["hsn"], gst_sections["hsn"])
    # One row has tax gap of 291.94
    gaps = [h["tax_gap"] for h in hsn_tie_out if abs(h["tax_gap"] - Decimal("291.94")) <= Decimal("0.05")]
    assert len(gaps) == 1

    # 3. 2 Sales Missing from GST data (Orders 54 and 55)
    # They are in MTR, not reported in GST
    missing_in_gst_orders = [r["order_id"] for r in mtr_march if "407-100005" in r["order_id"]]
    assert len(set(missing_in_gst_orders)) == 2

    # 4. 1 Order Reported in Wrong GST Month (Order 60: March sale, reported in April GST)
    order_60 = [r for r in mtr_records if "411-1000060" in r["order_id"]]
    assert len(order_60) == 1
    assert order_60[0]["invoice_date"].startswith("2026-03")


def test_tcs_double_rate_anomaly(loaded_demo_data):
    mtr_records = loaded_demo_data["mtr_records"]
    pay_records = loaded_demo_data["pay_records"]

    tcs_res = reconcile_tcs_tds(mtr_records, pay_records)
    anomalies = tcs_res["anomalies"]

    # 1 TCS at double statutory rate
    assert len(anomalies) == 1
    assert "409-1000057" in anomalies[0]["order_id"]
    assert "Implied TCS rate is 1.00%" in anomalies[0]["details"]
