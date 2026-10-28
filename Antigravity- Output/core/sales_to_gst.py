"""
Routing of Sales (MTR) Rows to GST Sections and Layer B Reconciliation.
Routes sales to B2B, B2CL, B2CS, CDNUR, CDNR, and HSN Summary.
Reconciles MTR sales against Amazon GST Ready-to-File (GSTR-1 format) report.
"""
from decimal import Decimal
from typing import Dict, Any, List, Tuple
from core.normalise import clean_id, match_hsn, rate_to_display_percent


def route_mtr_to_gst_sections(
    mtr_records: List[Dict[str, Any]],
    b2cl_threshold: Decimal = Decimal("100000.00")
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Route parsed MTR records into GSTR-1 sections:
    - B2B: Buyer has GSTIN (if present)
    - CDNR: Credit notes for B2B
    - B2CL: B2C, Inter-state, Invoice Value > b2cl_threshold
    - CDNUR: Credit notes / refunds for B2CL
    - B2CS: All other B2C shipments and returns
    - HSN: All transactions grouped for HSN summary
    """
    sections: Dict[str, List[Dict[str, Any]]] = {
        "b2b": [],
        "cdnr": [],
        "b2cl": [],
        "cdnur": [],
        "b2cs": [],
        "hsn": []
    }

    # First pass: identify B2CL invoices so refunds can route to CDNUR
    b2cl_invoice_nos = set()
    b2cl_order_ids = set()

    for r in mtr_records:
        if r["is_return"]:
            continue
        # B2C inter-state check
        is_interstate = (r.get("ship_from_code") != r.get("place_of_supply_code"))
        inv_val = abs(r["invoice_value"])
        if is_interstate and inv_val > b2cl_threshold:
            if r.get("invoice_no"):
                b2cl_invoice_nos.add(r["invoice_no"])
            if r.get("order_id"):
                b2cl_order_ids.add(r["order_id"])

    for r in mtr_records:
        # Check buyer gstin for B2B
        buyer_gstin = r.get("buyer_gstin")
        is_return = r["is_return"]

        if buyer_gstin:
            if is_return:
                sections["cdnr"].append(r)
            else:
                sections["b2b"].append(r)
        else:
            # B2C Routing
            if is_return:
                # Check if refund corresponds to B2CL
                orig_inv = r.get("invoice_no")
                ord_id = r.get("order_id")
                if orig_inv in b2cl_invoice_nos or ord_id in b2cl_order_ids or abs(r["invoice_value"]) > b2cl_threshold:
                    sections["cdnur"].append(r)
                else:
                    sections["b2cs"].append(r)
            else:
                is_interstate = (r.get("ship_from_code") != r.get("place_of_supply_code"))
                if is_interstate and abs(r["invoice_value"]) > b2cl_threshold:
                    sections["b2cl"].append(r)
                else:
                    sections["b2cs"].append(r)

        # All rows contribute to HSN summary
        sections["hsn"].append(r)

    return sections


def reconcile_b2cs(
    mtr_b2cs_rows: List[Dict[str, Any]],
    gst_b2cs_rows: List[Dict[str, Any]],
    tolerance: Decimal = Decimal("1.00")
) -> Dict[str, Any]:
    """
    Layer B: Reconcile B2C Small.
    Headline check: MTR (Shipments minus Returns) total taxable == GST B2CS total taxable.
    Detailed tie-out: Grouped by (place_of_supply_code, rate).
    Lists underlying MTR invoices for discrepancies.
    """
    # 1. Headline Totals
    mtr_shipments_taxable = sum((r["taxable_value"] for r in mtr_b2cs_rows if not r["is_return"]), Decimal("0.00"))
    mtr_returns_taxable = sum((abs(r["taxable_value"]) for r in mtr_b2cs_rows if r["is_return"]), Decimal("0.00"))
    mtr_net_taxable = sum((r["taxable_value"] for r in mtr_b2cs_rows), Decimal("0.00"))

    gst_total_taxable = sum((r["taxable_value"] for r in gst_b2cs_rows), Decimal("0.00"))
    headline_diff = mtr_net_taxable - gst_total_taxable
    headline_matched = abs(headline_diff) <= tolerance

    # 2. Group MTR by (place_of_supply_code, rate)
    mtr_groups: Dict[Tuple[str, Decimal], Dict[str, Any]] = {}
    for r in mtr_b2cs_rows:
        key = (r["place_of_supply_code"], r["rate"])
        if key not in mtr_groups:
            mtr_groups[key] = {
                "pos_code": r["place_of_supply_code"],
                "pos_name": r["place_of_supply_name"],
                "rate": r["rate"],
                "taxable_value": Decimal("0.00"),
                "invoices": [],
                "count": 0
            }
        mtr_groups[key]["taxable_value"] += r["taxable_value"]
        mtr_groups[key]["invoices"].append({
            "invoice_no": r.get("invoice_no"),
            "order_id": r.get("order_id"),
            "taxable_value": r["taxable_value"],
            "invoice_value": r["invoice_value"],
            "txn_type": r["txn_type"]
        })
        mtr_groups[key]["count"] += 1

    # 3. Group GST report rows by (place_of_supply_code, rate)
    gst_groups: Dict[Tuple[str, Decimal], Dict[str, Any]] = {}
    for r in gst_b2cs_rows:
        key = (r["place_of_supply_code"], r["rate"])
        if key not in gst_groups:
            gst_groups[key] = {
                "pos_code": r["place_of_supply_code"],
                "pos_name": r["place_of_supply_name"],
                "rate": r["rate"],
                "taxable_value": Decimal("0.00"),
                "raw_place_of_supply": r.get("raw_place_of_supply", "")
            }
        gst_groups[key]["taxable_value"] += r["taxable_value"]

    # 4. Compare Groups
    all_keys = set(mtr_groups.keys()).union(set(gst_groups.keys()))
    comparison_table: List[Dict[str, Any]] = []

    for key in sorted(all_keys, key=lambda k: (k[0], k[1])):
        pos_code, rate = key
        m_grp = mtr_groups.get(key)
        g_grp = gst_groups.get(key)

        m_taxable = m_grp["taxable_value"] if m_grp else Decimal("0.00")
        g_taxable = g_grp["taxable_value"] if g_grp else Decimal("0.00")
        pos_name = (m_grp["pos_name"] if m_grp else (g_grp["pos_name"] if g_grp else pos_code))

        diff = m_taxable - g_taxable
        is_matched = abs(diff) <= tolerance

        reason = "Matched"
        if not is_matched:
            if m_taxable > Decimal("0.00") and g_taxable == Decimal("0.00"):
                reason = "Missing in GST"
            elif m_taxable == Decimal("0.00") and g_taxable > Decimal("0.00"):
                reason = "Timing/Cut-off"
            else:
                reason = "Rate/Value mismatch"

        comparison_table.append({
            "pos_code": pos_code,
            "pos_name": pos_name,
            "rate": rate,
            "rate_display": rate_to_display_percent(rate),
            "mtr_taxable": m_taxable,
            "gst_taxable": g_taxable,
            "difference": diff,
            "is_matched": is_matched,
            "reason_code": reason,
            "underlying_invoices": m_grp["invoices"] if m_grp else []
        })

    return {
        "headline": {
            "mtr_shipments_taxable": mtr_shipments_taxable,
            "mtr_returns_taxable": mtr_returns_taxable,
            "mtr_net_taxable": mtr_net_taxable,
            "gst_total_taxable": gst_total_taxable,
            "difference": headline_diff,
            "is_matched": headline_matched
        },
        "breakdown": comparison_table
    }


def reconcile_b2cl_and_cdnur(
    mtr_rows: List[Dict[str, Any]],
    gst_rows: List[Dict[str, Any]],
    is_cdnur: bool = False,
    tolerance: Decimal = Decimal("1.00")
) -> List[Dict[str, Any]]:
    """
    Invoice-wise / Note-wise reconciliation for B2C Large and CDNUR.
    Flags:
    - missing in GST
    - missing in sales
    - taxable value difference
    - rate difference
    - place-of-supply difference
    """
    match_key_mtr = "credit_note_no" if is_cdnur else "invoice_no"
    match_key_gst = "note_no" if is_cdnur else "invoice_no"

    gst_map = {clean_id(r.get(match_key_gst)): r for r in gst_rows if clean_id(r.get(match_key_gst))}
    mtr_map = {clean_id(r.get(match_key_mtr)): r for r in mtr_rows if clean_id(r.get(match_key_mtr))}

    all_keys = set(gst_map.keys()).union(set(mtr_map.keys()))
    results = []

    for doc_no in all_keys:
        m = mtr_map.get(doc_no)
        g = gst_map.get(doc_no)

        if m and not g:
            results.append({
                "doc_no": doc_no,
                "order_id": m.get("order_id"),
                "status": "Missing in GST",
                "reason_code": "Missing in GST",
                "mtr_taxable": m["taxable_value"],
                "gst_taxable": Decimal("0.00"),
                "difference": m["taxable_value"],
                "mtr_rate": m["rate"],
                "gst_rate": None,
                "mtr_pos": m["place_of_supply_code"],
                "gst_pos": None,
                "details": "Present in MTR sales but absent in GST report."
            })
        elif g and not m:
            results.append({
                "doc_no": doc_no,
                "order_id": g.get("orig_invoice_no", ""),
                "status": "Missing in Sales",
                "reason_code": "Timing/Cut-off",
                "mtr_taxable": Decimal("0.00"),
                "gst_taxable": g["taxable_value"],
                "difference": -g["taxable_value"],
                "mtr_rate": None,
                "gst_rate": g["rate"],
                "mtr_pos": None,
                "gst_pos": g["place_of_supply_code"],
                "details": "Reported in GST but not found in current month sales."
            })
        else:
            diff = m["taxable_value"] - g["taxable_value"]
            reasons = []
            if abs(diff) > tolerance:
                reasons.append("Rate/Value mismatch")
            if m["rate"] != g["rate"]:
                reasons.append("Rate difference")
            if m["place_of_supply_code"] != g["place_of_supply_code"]:
                reasons.append("Place-of-supply")

            status = "Matched" if not reasons else reasons[0]
            results.append({
                "doc_no": doc_no,
                "order_id": m.get("order_id"),
                "status": status,
                "reason_code": status if status != "Rate difference" else "Rate/Value mismatch",
                "mtr_taxable": m["taxable_value"],
                "gst_taxable": g["taxable_value"],
                "difference": diff,
                "mtr_rate": m["rate"],
                "gst_rate": g["rate"],
                "mtr_pos": m["place_of_supply_code"],
                "gst_pos": g["place_of_supply_code"],
                "details": ", ".join(reasons) if reasons else "Fully matched"
            })

    return results


def reconcile_hsn(
    mtr_rows: List[Dict[str, Any]],
    gst_hsn_rows: List[Dict[str, Any]],
    tolerance: Decimal = Decimal("1.00")
) -> List[Dict[str, Any]]:
    """
    Reconcile HSN Summary.
    MTR aggregated by (HSN, rate) net of refunds.
    Matches GST HSN exact first, then on first 4 digits.
    Compares taxable value, quantity, and tax amounts.
    """
    # 1. Aggregate MTR by (hsn, rate)
    mtr_hsn_map: Dict[Tuple[str, Decimal], Dict[str, Any]] = {}
    for r in mtr_rows:
        hsn = r.get("hsn") or "UNKNOWN"
        rate = r["rate"]
        key = (hsn, rate)
        if key not in mtr_hsn_map:
            mtr_hsn_map[key] = {
                "hsn": hsn,
                "rate": rate,
                "quantity": 0,
                "taxable_value": Decimal("0.00"),
                "total_tax": Decimal("0.00"),
                "cgst": Decimal("0.00"),
                "sgst": Decimal("0.00"),
                "igst": Decimal("0.00")
            }
        mtr_hsn_map[key]["quantity"] += r.get("quantity", 1)
        mtr_hsn_map[key]["taxable_value"] += r["taxable_value"]
        mtr_hsn_map[key]["total_tax"] += r["total_tax"]
        mtr_hsn_map[key]["cgst"] += r.get("cgst", Decimal("0.00"))
        mtr_hsn_map[key]["sgst"] += r.get("sgst", Decimal("0.00"))
        mtr_hsn_map[key]["igst"] += r.get("igst", Decimal("0.00"))

    results = []
    matched_mtr_keys = set()

    for g in gst_hsn_rows:
        g_hsn = g.get("hsn", "")
        g_rate = g["rate"]
        g_taxable = g["taxable_value"]
        g_qty = g.get("quantity", 0)
        g_tax = g.get("tax_total", Decimal("0.00"))

        # Find matching MTR key
        matched_m = None
        match_method = "none"

        # Try exact
        if (g_hsn, g_rate) in mtr_hsn_map:
            matched_m = mtr_hsn_map[(g_hsn, g_rate)]
            match_method = "exact"
            matched_mtr_keys.add((g_hsn, g_rate))
        else:
            # Try 4-digit prefix match with same rate
            for (m_hsn, m_rate), m_data in mtr_hsn_map.items():
                if (m_hsn, m_rate) in matched_mtr_keys:
                    continue
                if m_rate == g_rate:
                    is_m, method = match_hsn(m_hsn, g_hsn)
                    if is_m:
                        matched_m = m_data
                        match_method = method
                        matched_mtr_keys.add((m_hsn, m_rate))
                        break

        m_taxable = matched_m["taxable_value"] if matched_m else Decimal("0.00")
        m_qty = matched_m["quantity"] if matched_m else 0
        m_tax = matched_m["total_tax"] if matched_m else Decimal("0.00")

        taxable_diff = m_taxable - g_taxable
        qty_diff = m_qty - g_qty
        is_taxable_matched = abs(taxable_diff) <= tolerance

        # Expected statutory tax vs reported tax in GST
        expected_statutory_tax = (g_taxable * g_rate).quantize(Decimal("0.01"))
        tax_gap = expected_statutory_tax - g_tax

        reason = "Matched" if is_taxable_matched else "Rate/Value mismatch"
        if not matched_m:
            reason = "Missing in Sales"

        results.append({
            "hsn": g_hsn,
            "rate": g_rate,
            "rate_display": rate_to_display_percent(g_rate),
            "match_method": match_method,
            "gst_taxable": g_taxable,
            "mtr_taxable": m_taxable,
            "taxable_difference": taxable_diff,
            "gst_quantity": g_qty,
            "mtr_quantity": m_qty,
            "quantity_difference": qty_diff,
            "gst_reported_tax": g_tax,
            "expected_statutory_tax": expected_statutory_tax,
            "tax_gap": tax_gap,
            "mtr_tax": m_tax,
            "reason_code": reason
        })

    # Add any MTR HSN groups that were not matched to any GST row
    for (m_hsn, m_rate), m_data in mtr_hsn_map.items():
        if (m_hsn, m_rate) not in matched_mtr_keys:
            results.append({
                "hsn": m_hsn,
                "rate": m_rate,
                "rate_display": rate_to_display_percent(m_rate),
                "match_method": "none",
                "gst_taxable": Decimal("0.00"),
                "mtr_taxable": m_data["taxable_value"],
                "taxable_difference": m_data["taxable_value"],
                "gst_quantity": 0,
                "mtr_quantity": m_data["quantity"],
                "quantity_difference": m_data["quantity"],
                "gst_reported_tax": Decimal("0.00"),
                "expected_statutory_tax": Decimal("0.00"),
                "tax_gap": Decimal("0.00"),
                "mtr_tax": m_data["total_tax"],
                "reason_code": "Missing in GST"
            })

    return results
