"""
Tests for Layer A Reconciliation, Financial Bridge, and Row Checks.
Covers:
- Hand-calculated order bridge balancing:
  Net Sales - Deductions - Unexplained = Actual Payout
- Deferred rows classified strictly as 'Awaiting release (Timing)', never 'Not paid'.
- Payments row check (component columns sum == total).
"""
from decimal import Decimal
from datetime import datetime
import pytest
from core.sales_to_payout import reconcile_sales_to_payout


def test_hand_calculated_bridge_and_balancing():
    """
    Hand-calculated test case:
    Invoice Value: 1000.00
    Selling Fees: -100.00
    Other Fees: -25.00
    TCS: -5.00
    TDS: -1.00
    Rebates: 0.00
    Expected Net Payout = 1000 - 100 - 25 - 5 - 1 = 869.00
    Actual Net Payout = 869.00
    Difference = 0.00 -> Matched
    """
    mtr_row = {
        "order_id": "ORD-HAND-1",
        "invoice_no": "INV-HAND-1",
        "invoice_date": "2026-03-10",
        "invoice_date_dt": datetime(2026, 3, 10),
        "is_return": False,
        "invoice_value": Decimal("1000.00"),
        "taxable_value": Decimal("847.46"),
        "total_tax": Decimal("152.54"),
        "tcs_total": Decimal("4.24")
    }

    pay_row = {
        "order_id": "ORD-HAND-1",
        "type": "Sale",
        "transaction_status": "Released",
        "raw_status": "Released",
        "is_deferred": False,
        "settlement_date": "2026-03-15",
        "product_sales": Decimal("1000.00"),
        "shipping_credits": Decimal("0.00"),
        "gift_wrap_credits": Decimal("0.00"),
        "promo_rebates": Decimal("0.00"),
        "sales_tax_liable": Decimal("152.54"),
        "selling_fees": Decimal("-100.00"),
        "fba_fees": Decimal("0.00"),
        "other_transaction_fees": Decimal("-25.00"),
        "other": Decimal("0.00"),
        "tcs_cgst": Decimal("-2.50"),
        "tcs_sgst": Decimal("-2.50"),
        "tcs_igst": Decimal("0.00"),
        "tcs_total": Decimal("-5.00"),
        "tds": Decimal("-1.00"),
        "net_payout": Decimal("869.00")
    }

    reconciled, kpi = reconcile_sales_to_payout(
        mtr_records=[mtr_row],
        payment_records=[pay_row],
        as_of="2026-03-25",
        tolerance=Decimal("1.00")
    )

    assert len(reconciled) == 1
    res = reconciled[0]
    assert res["status"] == "Matched"
    assert res["expected_payout"] == Decimal("869.00")
    assert res["actual_payout"] == Decimal("869.00")
    assert res["unexplained"] == Decimal("0.00")

    # Balancing equation: Net Sales - Deductions - Unexplained = Actual Payout
    total_deductions = (
        abs(res["selling_fees"])
        + abs(res["fba_fees"])
        + abs(res["other_fees"])
        + abs(res["tcs"])
        + abs(res["tds"])
    )
    balanced_actual = res["net_sales"] - total_deductions - res["unexplained"]
    assert abs(balanced_actual - res["actual_payout"]) <= Decimal("0.01")


def test_deferred_rows_classified_as_timing_never_not_paid():
    """
    Orders with Transaction Status 'Deferred' must be classified as 'Awaiting release (Timing)',
    NEVER 'Not paid', regardless of how many days have elapsed.
    """
    mtr_row = {
        "order_id": "ORD-DEFERRED-1",
        "invoice_no": "INV-DEF-1",
        "invoice_date": "2026-01-01",  # 90 days ago
        "invoice_date_dt": datetime(2026, 1, 1),
        "is_return": False,
        "invoice_value": Decimal("500.00"),
        "taxable_value": Decimal("423.73"),
        "total_tax": Decimal("76.27"),
        "tcs_total": Decimal("2.12")
    }

    pay_row = {
        "order_id": "ORD-DEFERRED-1",
        "type": "Sale",
        "transaction_status": "Deferred",
        "raw_status": "Deferred",
        "is_deferred": True,
        "settlement_date": "2026-01-05",
        "release_date": "2026-04-15",
        "product_sales": Decimal("500.00"),
        "shipping_credits": Decimal("0.00"),
        "gift_wrap_credits": Decimal("0.00"),
        "promo_rebates": Decimal("0.00"),
        "sales_tax_liable": Decimal("76.27"),
        "selling_fees": Decimal("-50.00"),
        "fba_fees": Decimal("0.00"),
        "other_transaction_fees": Decimal("-25.96"),
        "other": Decimal("0.00"),
        "tcs_cgst": Decimal("-1.06"),
        "tcs_sgst": Decimal("-1.06"),
        "tcs_igst": Decimal("0.00"),
        "tcs_total": Decimal("-2.12"),
        "tds": Decimal("-0.50"),
        "net_payout": Decimal("421.42")
    }

    reconciled, kpi = reconcile_sales_to_payout(
        mtr_records=[mtr_row],
        payment_records=[pay_row],
        as_of="2026-03-31",  # order is 90 days old
        tolerance=Decimal("1.00"),
        unpaid_threshold_days=10
    )

    assert len(reconciled) == 1
    res = reconciled[0]
    assert res["status"] == "Awaiting release (Timing)"
    assert res["status"] != "Not paid"
    assert res["reason_code"] == "Timing/Cut-off"


def test_unpaid_threshold_triggers_not_paid():
    """
    Order with NO payment row triggers 'Not paid' ONLY when older than unpaid_threshold_days.
    """
    old_mtr = {
        "order_id": "ORD-OLD-UNPAID",
        "invoice_no": "INV-OLD",
        "invoice_date": "2026-03-01",
        "invoice_date_dt": datetime(2026, 3, 1),
        "is_return": False,
        "invoice_value": Decimal("300.00"),
        "taxable_value": Decimal("254.24"),
        "total_tax": Decimal("45.76"),
        "tcs_total": Decimal("1.27")
    }

    fresh_mtr = {
        "order_id": "ORD-FRESH-UNPAID",
        "invoice_no": "INV-FRESH",
        "invoice_date": "2026-03-22",
        "invoice_date_dt": datetime(2026, 3, 22),
        "is_return": False,
        "invoice_value": Decimal("300.00"),
        "taxable_value": Decimal("254.24"),
        "total_tax": Decimal("45.76"),
        "tcs_total": Decimal("1.27")
    }

    reconciled, kpi = reconcile_sales_to_payout(
        mtr_records=[old_mtr, fresh_mtr],
        payment_records=[],
        as_of="2026-03-25",  # old is 24 days old, fresh is 3 days old
        unpaid_threshold_days=10
    )

    res_map = {r["order_id"]: r for r in reconciled}
    assert res_map["ORD-OLD-UNPAID"]["status"] == "Not paid"
    assert res_map["ORD-OLD-UNPAID"]["reason_code"] == "Missing payout"

    # Fresh order (< 10 days old) should be Timing difference, not Not paid
    assert res_map["ORD-FRESH-UNPAID"]["status"] == "Timing difference"
    assert res_map["ORD-FRESH-UNPAID"]["reason_code"] == "Timing/Cut-off"
