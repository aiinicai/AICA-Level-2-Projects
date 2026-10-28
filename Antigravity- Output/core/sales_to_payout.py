"""
Layer A: Order-Level Sales to Payout Reconciliation for MarketMatch.
Builds the financial bridge per order:
  Invoice Value - Refunds - Fees - GST on Fees - TCS - TDS +/- Adjustments/Rebates = Expected Net Payout
Compares with Actual Net Payout.
Handles Deferred rows strictly as 'Awaiting release (Timing)', never 'Not paid'.
Applies unpaid_threshold_days to identify true 'Not paid' orders.
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from core.normalise import clean_id, parse_date


def reconcile_sales_to_payout(
    mtr_records: List[Dict[str, Any]],
    payment_records: List[Dict[str, Any]],
    as_of: Optional[str] = None,
    tolerance: Decimal = Decimal("1.00"),
    unpaid_threshold_days: int = 10,
    gst_rate_on_fees: Decimal = Decimal("0.18")
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Perform Layer A Order-Level Reconciliation.
    Pure function: no Streamlit code.
    as_of: Date string YYYY-MM-DD or None (defaults to today).
    """
    if as_of:
        ref_dt = parse_date(as_of) or datetime.utcnow()
    else:
        ref_dt = datetime.utcnow()

    # 1. Aggregate MTR records by order_id
    mtr_by_order: Dict[str, Dict[str, Any]] = {}
    for r in mtr_records:
        oid = clean_id(r.get("order_id"))
        if not oid:
            continue
        if oid not in mtr_by_order:
            mtr_by_order[oid] = {
                "order_id": oid,
                "invoice_no": r.get("invoice_no") or "",
                "invoice_date": r.get("invoice_date") or "",
                "invoice_date_dt": r.get("invoice_date_dt"),
                "sales_count": 0,
                "refunds_count": 0,
                "gross_invoice_value": Decimal("0.00"),
                "refunds_value": Decimal("0.00"),
                "net_invoice_value": Decimal("0.00"),
                "taxable_value": Decimal("0.00"),
                "total_tax": Decimal("0.00"),
                "tcs_sales": Decimal("0.00"),
                "has_refund_without_cn": False,
                "items": []
            }
        
        mtr_by_order[oid]["items"].append(r)
        if r["is_return"]:
            mtr_by_order[oid]["refunds_count"] += 1
            # Refunds are stored negative, take abs for separate tracking
            mtr_by_order[oid]["refunds_value"] += abs(r["invoice_value"])
            mtr_by_order[oid]["net_invoice_value"] += r["invoice_value"]  # negative reduces net
            mtr_by_order[oid]["taxable_value"] += r["taxable_value"]
            mtr_by_order[oid]["total_tax"] += r["total_tax"]
            mtr_by_order[oid]["tcs_sales"] += r["tcs_total"]
            if not r.get("credit_note_no"):
                mtr_by_order[oid]["has_refund_without_cn"] = True
        else:
            mtr_by_order[oid]["sales_count"] += 1
            mtr_by_order[oid]["gross_invoice_value"] += r["invoice_value"]
            mtr_by_order[oid]["net_invoice_value"] += r["invoice_value"]
            mtr_by_order[oid]["taxable_value"] += r["taxable_value"]
            mtr_by_order[oid]["total_tax"] += r["total_tax"]
            mtr_by_order[oid]["tcs_sales"] += r["tcs_total"]
            if not mtr_by_order[oid]["invoice_no"] and r.get("invoice_no"):
                mtr_by_order[oid]["invoice_no"] = r["invoice_no"]
            if not mtr_by_order[oid]["invoice_date"] and r.get("invoice_date"):
                mtr_by_order[oid]["invoice_date"] = r["invoice_date"]
                mtr_by_order[oid]["invoice_date_dt"] = r.get("invoice_date_dt")

    # 2. Aggregate Payments records by order_id
    pay_by_order: Dict[str, Dict[str, Any]] = {}
    unmatched_payments: List[Dict[str, Any]] = []

    for p in payment_records:
        oid = clean_id(p.get("order_id"))
        if not oid:
            unmatched_payments.append(p)
            continue

        if oid not in pay_by_order:
            pay_by_order[oid] = {
                "order_id": oid,
                "rows_count": 0,
                "released_count": 0,
                "deferred_count": 0,
                "selling_fees": Decimal("0.00"),
                "fba_fees": Decimal("0.00"),
                "other_transaction_fees": Decimal("0.00"),
                "other_fees": Decimal("0.00"),
                "tcs_cgst": Decimal("0.00"),
                "tcs_sgst": Decimal("0.00"),
                "tcs_igst": Decimal("0.00"),
                "tcs_total": Decimal("0.00"),
                "tds": Decimal("0.00"),
                "promo_rebates": Decimal("0.00"),
                "actual_net_payout": Decimal("0.00"),
                "released_payout": Decimal("0.00"),
                "deferred_payout": Decimal("0.00"),
                "latest_settlement_date": p.get("settlement_date"),
                "latest_release_date": p.get("release_date"),
                "has_deferred": False,
                "raw_statuses": set(),
                "records": []
            }

        po = pay_by_order[oid]
        po["records"].append(p)
        po["rows_count"] += 1
        po["raw_statuses"].add(p.get("raw_status", ""))

        if p.get("is_deferred"):
            po["deferred_count"] += 1
            po["has_deferred"] = True
            po["deferred_payout"] += p["net_payout"]
        else:
            po["released_count"] += 1
            po["released_payout"] += p["net_payout"]

        po["actual_net_payout"] += p["net_payout"]
        po["selling_fees"] += p["selling_fees"]
        po["fba_fees"] += p["fba_fees"]
        po["other_transaction_fees"] += p["other_transaction_fees"]
        po["other_fees"] += p["other"]
        po["tcs_cgst"] += p["tcs_cgst"]
        po["tcs_sgst"] += p["tcs_sgst"]
        po["tcs_igst"] += p["tcs_igst"]
        po["tcs_total"] += p["tcs_total"]
        po["tds"] += p["tds"]
        po["promo_rebates"] += p["promo_rebates"]

        if p.get("settlement_date") and (not po["latest_settlement_date"] or p["settlement_date"] > po["latest_settlement_date"]):
            po["latest_settlement_date"] = p["settlement_date"]
        if p.get("release_date") and (not po["latest_release_date"] or p["release_date"] > po["latest_release_date"]):
            po["latest_release_date"] = p["release_date"]

    # 3. Match Orders and Build Financial Bridge
    all_order_ids = set(mtr_by_order.keys()).union(set(pay_by_order.keys()))
    reconciled_orders: List[Dict[str, Any]] = []

    kpi_summary = {
        "total_orders": len(all_order_ids),
        "matched_count": 0,
        "short_paid_count": 0,
        "excess_paid_count": 0,
        "awaiting_release_count": 0,
        "not_paid_count": 0,
        "duplicate_count": 0,
        "timing_diff_count": 0,
        "payout_without_order_count": len(unmatched_payments),
        "total_gross_sales": Decimal("0.00"),
        "total_refunds": Decimal("0.00"),
        "total_net_sales": Decimal("0.00"),
        "total_selling_fees": Decimal("0.00"),
        "total_fba_fees": Decimal("0.00"),
        "total_other_fees": Decimal("0.00"),
        "total_gst_on_fees": Decimal("0.00"),
        "total_tcs": Decimal("0.00"),
        "total_tds": Decimal("0.00"),
        "total_expected_payout": Decimal("0.00"),
        "total_actual_payout": Decimal("0.00"),
        "total_unexplained": Decimal("0.00")
    }

    for oid in sorted(all_order_ids):
        m = mtr_by_order.get(oid)
        p = pay_by_order.get(oid)

        # Case A: Payout exists but NO Order in MTR
        if not m and p:
            rec = {
                "order_id": oid,
                "invoice_no": "N/A",
                "invoice_date": "",
                "status": "Payout without order",
                "reason_code": "Missing in GST" if p["actual_net_payout"] > 0 else "Unexplained",
                "gross_sales": Decimal("0.00"),
                "refunds": Decimal("0.00"),
                "net_sales": Decimal("0.00"),
                "selling_fees": p["selling_fees"],
                "fba_fees": p["fba_fees"],
                "other_fees": p["other_transaction_fees"] + p["other_fees"],
                "gst_on_fees": Decimal("0.00"),
                "tcs": p["tcs_total"],
                "tds": p["tds"],
                "promo_rebates": p["promo_rebates"],
                "expected_payout": Decimal("0.00"),
                "actual_payout": p["actual_net_payout"],
                "difference": p["actual_net_payout"],
                "unexplained": p["actual_net_payout"],
                "payout_status": "Released" if p["released_count"] > 0 else "Deferred",
                "payout_date": p.get("latest_settlement_date") or "",
                "release_date": p.get("latest_release_date") or "",
                "source_mtr_rows": 0,
                "source_pay_rows": p["rows_count"],
                "details": "Payout received in payments file with no corresponding sale in MTR."
            }
            reconciled_orders.append(rec)
            kpi_summary["total_actual_payout"] += p["actual_net_payout"]
            kpi_summary["total_unexplained"] += p["actual_net_payout"]
            continue

        # Case B: Order in MTR exists
        gross_sales = m["gross_invoice_value"]
        refunds = m["refunds_value"]
        net_sales = m["net_invoice_value"]
        inv_date_dt = m.get("invoice_date_dt")

        kpi_summary["total_gross_sales"] += gross_sales
        kpi_summary["total_refunds"] += refunds
        kpi_summary["total_net_sales"] += net_sales

        # Deductions from payments if payment row exists
        selling_fees = p["selling_fees"] if p else Decimal("0.00")
        fba_fees = p["fba_fees"] if p else Decimal("0.00")
        other_fees = (p["other_transaction_fees"] + p["other_fees"]) if p else Decimal("0.00")
        tcs = p["tcs_total"] if p else Decimal("0.00")
        tds = p["tds"] if p else Decimal("0.00")
        promo_rebates = p["promo_rebates"] if p else Decimal("0.00")

        # Note: If payments file already accounted for GST within fees, we track expected fees + tax
        gst_on_fees = Decimal("0.00")

        # Expected Net Payout per prompt bridge:
        # Expected Net = Invoice value - Refunds - Fees - GST on fees - TCS - TDS +/- Adjustments/Rebates
        # Note: In payments file, selling_fees, fba_fees, tcs, tds are stored negative.
        # Adding negative numbers is subtracting deductions!
        if p:
            expected_payout = (
                net_sales
                - abs(selling_fees)
                - abs(fba_fees)
                - abs(other_fees)
                - gst_on_fees
                - abs(tcs)
                - abs(tds)
                + promo_rebates
            )
            actual_payout = p["actual_net_payout"]
            diff = actual_payout - expected_payout
            unexplained = diff if abs(diff) > tolerance else Decimal("0.00")
        else:
            expected_payout = net_sales
            actual_payout = Decimal("0.00")
            diff = -net_sales
            unexplained = -net_sales

        kpi_summary["total_selling_fees"] += abs(selling_fees)
        kpi_summary["total_fba_fees"] += abs(fba_fees)
        kpi_summary["total_other_fees"] += abs(other_fees)
        kpi_summary["total_tcs"] += abs(tcs)
        kpi_summary["total_tds"] += abs(tds)
        kpi_summary["total_expected_payout"] += expected_payout
        kpi_summary["total_actual_payout"] += actual_payout
        kpi_summary["total_unexplained"] += unexplained

        # 4. Status and Reason Code Classification
        status = "Unexplained"
        reason_code = "Unexplained"
        details = ""

        # Check for Refund without Credit Note first
        if m.get("has_refund_without_cn"):
            status = "Refund without credit note"
            reason_code = "Returns/Refunds"
            details = "MTR return record is missing credit note number/date."

        elif not p:
            # Order has NO payment record
            order_age_days = (ref_dt - inv_date_dt).days if inv_date_dt else 999
            if order_age_days > unpaid_threshold_days:
                status = "Not paid"
                reason_code = "Missing payout"
                details = f"Unsettled after {order_age_days} days (threshold {unpaid_threshold_days} days). No payment or deferred record found."
                kpi_summary["not_paid_count"] += 1
            else:
                status = "Timing difference"
                reason_code = "Timing/Cut-off"
                details = f"Recent order ({order_age_days} days old), within settlement threshold window."
                kpi_summary["timing_diff_count"] += 1

        elif p.get("has_deferred") and p.get("released_count") == 0:
            # Transaction Status is Deferred
            status = "Awaiting release (Timing)"
            reason_code = "Timing/Cut-off"
            details = f"Payment status is Deferred. Scheduled release date: {p.get('latest_release_date') or 'Pending'}. NOT an unpaid exception."
            kpi_summary["awaiting_release_count"] += 1

        elif p.get("released_count") > 1 and actual_payout > expected_payout * Decimal("1.80"):
            # Duplicate payout detected
            status = "Duplicate payout"
            reason_code = "Duplicate"
            details = f"Multiple settlement records ({p['released_count']}) found resulting in duplicate disbursement."
            kpi_summary["duplicate_count"] += 1

        elif abs(diff) <= tolerance:
            status = "Matched"
            reason_code = "Rounding" if diff != Decimal("0.00") else "Fees"
            details = "Order fully reconciled within tolerance."
            kpi_summary["matched_count"] += 1

        elif diff < -tolerance:
            status = "Short paid"
            reason_code = "Fees"
            details = f"Actual payout is short by INR {abs(diff):,.2f} after standard fee and tax deductions."
            kpi_summary["short_paid_count"] += 1

        elif diff > tolerance:
            status = "Excess paid"
            reason_code = "Fees"
            details = f"Actual payout exceeds expected payout by INR {diff:,.2f}."
            kpi_summary["excess_paid_count"] += 1

        rec = {
            "order_id": oid,
            "invoice_no": m.get("invoice_no") or "N/A",
            "invoice_date": m.get("invoice_date") or "",
            "status": status,
            "reason_code": reason_code,
            "gross_sales": gross_sales,
            "refunds": refunds,
            "net_sales": net_sales,
            "selling_fees": selling_fees,
            "fba_fees": fba_fees,
            "other_fees": other_fees,
            "gst_on_fees": gst_on_fees,
            "tcs": tcs,
            "tds": tds,
            "promo_rebates": promo_rebates,
            "expected_payout": expected_payout,
            "actual_payout": actual_payout,
            "difference": diff,
            "unexplained": unexplained,
            "payout_status": "Deferred" if (p and p.get("has_deferred") and p.get("released_count") == 0) else ("Released" if p else "Unpaid"),
            "payout_date": p.get("latest_settlement_date") if p else "",
            "release_date": p.get("latest_release_date") if p else "",
            "source_mtr_rows": len(m["items"]),
            "source_pay_rows": p["rows_count"] if p else 0,
            "details": details
        }
        reconciled_orders.append(rec)

    # Add orphaned payment rows (without any order ID)
    for p in unmatched_payments:
        rec = {
            "order_id": "ORPHAN-PAYMENT",
            "invoice_no": "N/A",
            "invoice_date": "",
            "status": "Payout without order",
            "reason_code": "Unexplained",
            "gross_sales": Decimal("0.00"),
            "refunds": Decimal("0.00"),
            "net_sales": Decimal("0.00"),
            "selling_fees": p["selling_fees"],
            "fba_fees": p["fba_fees"],
            "other_fees": p["other_transaction_fees"] + p["other"],
            "gst_on_fees": Decimal("0.00"),
            "tcs": p["tcs_total"],
            "tds": p["tds"],
            "promo_rebates": p["promo_rebates"],
            "expected_payout": Decimal("0.00"),
            "actual_payout": p["net_payout"],
            "difference": p["net_payout"],
            "unexplained": p["net_payout"],
            "payout_status": p.get("transaction_status", "Released"),
            "payout_date": p.get("settlement_date", ""),
            "release_date": p.get("release_date", ""),
            "source_mtr_rows": 0,
            "source_pay_rows": 1,
            "details": f"Payment record of type '{p.get('type')}' without Order ID ({p.get('description')})."
        }
        reconciled_orders.append(rec)
        kpi_summary["total_actual_payout"] += p["net_payout"]
        kpi_summary["total_unexplained"] += p["net_payout"]

    # Calculate reconciliation rate percentage
    matched_total = sum(1 for r in reconciled_orders if r["status"] in ("Matched", "Awaiting release (Timing)"))
    reconciled_pct = (Decimal(matched_total) / Decimal(len(reconciled_orders)) * Decimal("100.00")) if reconciled_orders else Decimal("100.00")
    kpi_summary["reconciled_pct"] = reconciled_pct.quantize(Decimal("0.1"))

    return reconciled_orders, kpi_summary
