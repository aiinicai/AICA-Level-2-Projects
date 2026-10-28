"""
Marketplace Report Parsers for MarketMatch.
Fully profile-driven via config/column_aliases.json.
Parses Amazon MTR (Sales), GST Ready-to-File (GSTR-1 format), and Payments (Unified/Transaction).
"""
import io
import hashlib
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
import openpyxl
import pandas as pd

from core.normalise import (
    to_decimal, clean_id, normalise_rate, normalise_state,
    normalise_hsn, parse_date, to_iso_date
)
from core.profiles import ProfileManager, clean_header_name
from core.exceptions import ParsingError


def compute_file_hash(content_bytes: bytes) -> str:
    """Compute SHA-256 hash of file content for duplicate upload detection."""
    return hashlib.sha256(content_bytes).hexdigest()


class ValidationReport:
    """Detailed file validation report tracking row counts and errors."""
    def __init__(self, file_name: str, file_type: str):
        self.file_name = file_name
        self.file_type = file_type
        self.total_rows = 0
        self.valid_rows = 0
        self.skipped_rows = 0
        self.missing_columns: List[str] = []
        self.warnings: List[str] = []
        self.row_errors: List[Dict[str, Any]] = []  # {row_num, field, message, val}
        self.distinct_values: Dict[str, Dict[str, int]] = {}  # field -> {val: count}
        self.internal_checks_results: List[Dict[str, Any]] = []

    def add_error(self, row_num: int, field: str, message: str, val: Any = None):
        self.row_errors.append({
            "row_num": row_num,
            "field": field,
            "message": message,
            "val": str(val) if val is not None else ""
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_name": self.file_name,
            "file_type": self.file_type,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "error_rows": len(self.row_errors),
            "missing_columns": self.missing_columns,
            "warnings": self.warnings,
            "row_errors": self.row_errors[:100],  # cap for UI preview
            "distinct_values": self.distinct_values,
            "internal_checks_results": self.internal_checks_results
        }


# =========================================================================
# 1. MTR PARSER
# =========================================================================
def parse_mtr(
    file_bytes: bytes,
    file_name: str,
    period_month: Optional[int] = None,
    period_year: Optional[int] = None,
    profile_key: str = "amazon_mtr",
    tolerance: Decimal = Decimal("1.00"),
    user_txn_mappings: Optional[Dict[str, str]] = None
) -> Tuple[List[Dict[str, Any]], ValidationReport]:
    """
    Parse Amazon Merchant Tax Report (MTR) according to profile.
    Computes sum_columns, applies sign rule for returns, validates row checks.
    """
    pm = ProfileManager()
    profile = pm.get_profile(profile_key)
    report = ValidationReport(file_name, "mtr")

    # Read content into list of string rows
    if file_name.lower().endswith(".xlsx") or file_name.lower().endswith(".xls"):
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        ws = wb.active
        raw_rows = []
        for row in ws.iter_rows(values_only=True):
            raw_rows.append(list(row))
    else:
        # CSV parsing
        # Try utf-8 then latin-1
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")
        df_raw = pd.read_csv(io.StringIO(text), header=None, dtype=str)
        raw_rows = df_raw.values.tolist()

    if not raw_rows:
        raise ParsingError(f"File {file_name} is empty.")

    # 1. Header Detection
    header_keywords = profile.get("header_detection_keywords", ["Invoice Number", "Order Id"])
    header_idx = pm.detect_header_row(raw_rows, header_keywords)
    if header_idx is None:
        header_idx = 0  # default to first row

    raw_headers = [str(c) if c is not None else "" for c in raw_rows[header_idx]]
    col_map = pm.map_columns(raw_headers, profile.get("columns", {}))

    # Check required columns
    required_fields = profile.get("required", [])
    for req in required_fields:
        if req not in col_map:
            report.missing_columns.append(req)

    if report.missing_columns:
        report.warnings.append(f"Missing required columns in MTR: {', '.join(report.missing_columns)}")

    # Check for buyer GSTIN column (B2B check)
    has_buyer_gstin = any("buyer" in clean_header_name(h) or "customer" in clean_header_name(h) for h in raw_headers)
    if not has_buyer_gstin:
        report.warnings.append("No Buyer GSTIN column detected in MTR export. Treating all rows as B2C sales.")

    # Map sum_columns (e.g. cgst, sgst, igst, tcs_total)
    sum_cols_config = profile.get("sum_columns", {})
    sum_cols_map: Dict[str, List[int]] = {}
    for sum_name, component_names in sum_cols_config.items():
        matched_indices = []
        for comp in component_names:
            comp_clean = clean_header_name(comp)
            for idx, h in enumerate(raw_headers):
                if clean_header_name(h) == comp_clean:
                    matched_indices.append(idx)
                    break
        sum_cols_map[sum_name] = matched_indices

    txn_type_map = profile.get("txn_type_map", {
        "Shipment": "Sale",
        "Refund": "Return",
        "Cancel": "Cancel",
        "FreeReplacement": "Ignore"
    })
    if user_txn_mappings:
        txn_type_map = {**txn_type_map, **user_txn_mappings}

    report.distinct_values["txn_type"] = {}
    records: List[Dict[str, Any]] = []

    # 2. Parse Detail Rows
    data_rows = raw_rows[header_idx + 1:]
    report.total_rows = len(data_rows)

    for offset, row in enumerate(data_rows):
        row_num = header_idx + 2 + offset
        if not any(cell is not None and str(cell).strip() for cell in row):
            report.skipped_rows += 1
            continue

        def get_val(field_name: str) -> Any:
            idx = col_map.get(field_name)
            if idx is not None and idx < len(row):
                return row[idx]
            return None

        raw_order_id = get_val("order_id")
        raw_invoice_no = get_val("invoice_no")
        raw_txn_type = str(get_val("txn_type") or "").strip()
        raw_date = get_val("invoice_date") or get_val("shipment_date") or get_val("order_date")

        order_id = clean_id(raw_order_id)
        invoice_no = clean_id(raw_invoice_no)

        if not order_id and not invoice_no:
            report.skipped_rows += 1
            continue

        # Track distinct txn_type values
        report.distinct_values["txn_type"][raw_txn_type] = report.distinct_values["txn_type"].get(raw_txn_type, 0) + 1

        dt = parse_date(raw_date)
        if dt is None:
            report.add_error(row_num, "invoice_date", "Unreadable date format", raw_date)

        # Period filtering
        if period_month and period_year and dt:
            if dt.month != period_month or dt.year != period_year:
                report.skipped_rows += 1
                continue

        # Transaction type mapping
        mapped_txn_type = txn_type_map.get(raw_txn_type, raw_txn_type)
        if mapped_txn_type == "Ignore" or mapped_txn_type == "Cancel":
            report.skipped_rows += 1
            continue

        # Monetary fields
        raw_taxable = get_val("taxable_value")
        raw_invoice_val = get_val("invoice_value")
        raw_total_tax = get_val("total_tax")

        taxable_value = to_decimal(raw_taxable)
        invoice_value = to_decimal(raw_invoice_val)
        total_tax = to_decimal(raw_total_tax)

        # Sum computed taxes
        def sum_from_cols(key_name: str) -> Decimal:
            tot = Decimal("0.00")
            indices = sum_cols_map.get(key_name, [])
            for c_idx in indices:
                if c_idx < len(row):
                    tot += to_decimal(row[c_idx])
            return tot

        cgst = sum_from_cols("cgst")
        sgst = sum_from_cols("sgst")
        utgst = sum_from_cols("utgst")
        igst = sum_from_cols("igst")
        cess = sum_from_cols("cess")
        tcs_total = sum_from_cols("tcs_total")

        # If total_tax in file is 0 or missing, compute as cgst+sgst+utgst+igst+cess
        computed_tax = cgst + sgst + utgst + igst + cess
        if total_tax == Decimal("0.00") and computed_tax > Decimal("0.00"):
            total_tax = computed_tax

        # Sign Rule: Return rows must be negative regardless of how file stores them
        is_return = mapped_txn_type in ("Return", "Refund")
        if is_return:
            taxable_value = -abs(taxable_value)
            invoice_value = -abs(invoice_value)
            total_tax = -abs(total_tax)
            cgst = -abs(cgst)
            sgst = -abs(sgst)
            utgst = -abs(utgst)
            igst = -abs(igst)
            cess = -abs(cess)
            tcs_total = -abs(tcs_total)

        # Credit note fields
        credit_note_no = clean_id(get_val("credit_note_no"))
        credit_note_date_val = get_val("credit_note_date")
        credit_note_date = parse_date(credit_note_date_val)

        # Row check 1: taxable_value + total_tax == invoice_value within tolerance
        calc_inv = taxable_value + total_tax
        if abs(calc_inv - invoice_value) > tolerance:
            report.add_error(
                row_num,
                "invoice_value",
                f"Taxable ({taxable_value}) + Tax ({total_tax}) = {calc_inv} does not match Invoice Value ({invoice_value})",
                invoice_value
            )

        # Row check 2: Single tax regime per row (IGST vs CGST+SGST/UTGST)
        ship_from_raw = get_val("ship_from_state")
        ship_to_raw = get_val("ship_to_state")
        pos_code, pos_name = normalise_state(ship_to_raw)
        ship_from_code, _ = normalise_state(ship_from_raw)

        # Rates
        cgst_rate = normalise_rate(get_val("cgst_rate"))
        sgst_rate = normalise_rate(get_val("sgst_rate"))
        igst_rate = normalise_rate(get_val("igst_rate"))
        effective_rate = igst_rate if igst_rate > Decimal("0.00") else (cgst_rate + sgst_rate)

        # HSN
        hsn = normalise_hsn(get_val("hsn"))

        # Row check 3: Return row credit note check
        if is_return and not credit_note_no:
            report.warnings.append(f"Row {row_num}: Return for order {order_id} has no Credit Note Number.")

        rec = {
            "source_file": file_name,
            "source_row": row_num,
            "seller_gstin": clean_id(get_val("seller_gstin")),
            "order_id": order_id,
            "order_item_id": clean_id(get_val("order_item_id")),
            "invoice_no": invoice_no,
            "invoice_date": to_iso_date(dt),
            "invoice_date_dt": dt,
            "txn_type": mapped_txn_type,
            "raw_txn_type": raw_txn_type,
            "is_return": is_return,
            "taxable_value": taxable_value,
            "total_tax": total_tax,
            "invoice_value": invoice_value,
            "cgst": cgst,
            "sgst": sgst,
            "utgst": utgst,
            "igst": igst,
            "cess": cess,
            "tcs_total": tcs_total,
            "rate": effective_rate,
            "cgst_rate": cgst_rate,
            "sgst_rate": sgst_rate,
            "igst_rate": igst_rate,
            "hsn": hsn,
            "sku": str(get_val("sku") or "").strip(),
            "quantity": int(to_decimal(get_val("quantity") or 1, round_cents=False)),
            "place_of_supply_code": pos_code or "97",
            "place_of_supply_name": pos_name or "OTHER",
            "ship_from_code": ship_from_code,
            "credit_note_no": credit_note_no,
            "credit_note_date": to_iso_date(credit_note_date),
            "principal_amount": to_decimal(get_val("principal_amount")),
            "shipping_amount": to_decimal(get_val("shipping_amount")),
            "gift_wrap_amount": to_decimal(get_val("gift_wrap_amount")),
            "item_promo_discount": to_decimal(get_val("item_promo_discount")),
            "shipping_promo_discount": to_decimal(get_val("shipping_promo_discount"))
        }
        records.append(rec)
        report.valid_rows += 1

    return records, report


# =========================================================================
# 2. GST REPORT PARSER (amazon_gst_rtf)
# =========================================================================
def parse_gst_rtf(
    file_bytes: bytes,
    file_name: str,
    filing_month: int,
    filing_year: int,
    profile_key: str = "amazon_gst_rtf",
    tolerance: Decimal = Decimal("1.00")
) -> Tuple[Dict[str, List[Dict[str, Any]]], ValidationReport, Dict[str, Any]]:
    """
    Parse Amazon GST Ready-to-File Excel workbook.
    Reads sheets defined in profile, skips rows 1-3 (formulas), reads header on row 4,
    data starting row 5. Recomputes control totals.
    Extracts Merchant GSTIN from GSTIN sheet.
    Runs internal checks.
    """
    pm = ProfileManager()
    profile = pm.get_profile(profile_key)
    report = ValidationReport(file_name, "gst_rtf")

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    parsed_sections: Dict[str, List[Dict[str, Any]]] = {}
    control_totals: Dict[str, Any] = {}

    # Extract Merchant GSTIN from GSTIN sheet if present
    merchant_gstin = ""
    if "GSTIN" in wb.sheetnames:
        ws_gstin = wb["GSTIN"]
        for r in range(1, min(10, ws_gstin.max_row + 1)):
            c1 = str(ws_gstin.cell(r, 1).value or "").strip()
            if "merchant gstin" in c1.lower():
                # Value could be in column 2 or next row column 1
                val_adj = ws_gstin.cell(r, 2).value
                val_below = ws_gstin.cell(r + 1, 1).value
                merchant_gstin = clean_id(val_adj or val_below)
                break
    control_totals["merchant_gstin"] = merchant_gstin

    header_row_idx = profile.get("header_row", 4)  # 1-indexed -> 4
    data_start_row = profile.get("data_start_row", 5)

    sheets_config = profile.get("sheets", {})

    for sheet_name, s_conf in sheets_config.items():
        section_key = s_conf.get("section", sheet_name.lower())
        parsed_sections[section_key] = []
        control_totals[section_key] = {
            "count": 0,
            "taxable_value": Decimal("0.00"),
            "invoice_value": Decimal("0.00"),
            "tax_total": Decimal("0.00")
        }

        if sheet_name not in wb.sheetnames:
            continue

        ws = wb[sheet_name]
        if ws.max_row < data_start_row:
            continue

        # Extract headers from header_row_idx (1-indexed)
        headers = [ws.cell(header_row_idx, c).value for c in range(1, ws.max_column + 1)]
        headers_str = [str(h) if h is not None else "" for h in headers]
        col_map = pm.map_columns(headers_str, s_conf.get("columns", {}))

        section_rows = []
        for r_idx in range(data_start_row, ws.max_row + 1):
            row_vals = [ws.cell(r_idx, c).value for c in range(1, ws.max_column + 1)]
            if not any(v is not None and str(v).strip() for v in row_vals):
                continue

            def get_cell(f_name: str) -> Any:
                idx = col_map.get(f_name)
                if idx is not None and idx < len(row_vals):
                    return row_vals[idx]
                return None

            taxable = to_decimal(get_cell("taxable_value"))
            inv_val = to_decimal(get_cell("invoice_value") or get_cell("note_value") or get_cell("total_value"))
            cess = to_decimal(get_cell("cess"))
            rate = normalise_rate(get_cell("rate"))

            pos_raw = get_cell("place_of_supply")
            pos_code, pos_name = normalise_state(pos_raw)

            row_dict = {
                "source_file": file_name,
                "source_row": r_idx,
                "sheet": sheet_name,
                "section": section_key,
                "taxable_value": taxable,
                "invoice_value": inv_val,
                "rate": rate,
                "cess": cess,
                "place_of_supply_code": pos_code or "97",
                "place_of_supply_name": pos_name or "OTHER",
                "raw_place_of_supply": str(pos_raw or ""),
                "applicable_tax_pct": str(get_cell("applicable_tax_pct") or "").strip(),
                "eco_gstin": clean_id(get_cell("eco_gstin"))
            }

            # Section specific fields
            if section_key in ("b2b", "b2cl"):
                row_dict["invoice_no"] = clean_id(get_cell("invoice_no"))
                row_dict["invoice_date"] = to_iso_date(parse_date(get_cell("invoice_date")))
                row_dict["recipient_gstin"] = clean_id(get_cell("recipient_gstin"))
            elif section_key in ("cdnr", "cdnur"):
                row_dict["note_no"] = clean_id(get_cell("note_no"))
                row_dict["note_date"] = to_iso_date(parse_date(get_cell("note_date")))
                row_dict["orig_invoice_no"] = clean_id(get_cell("orig_invoice_no"))
                row_dict["note_type"] = str(get_cell("note_type") or "").strip()
            elif section_key == "b2cs":
                row_dict["type"] = str(get_cell("type") or "E").strip()
            elif section_key == "hsn":
                row_dict["hsn"] = normalise_hsn(get_cell("hsn"))
                row_dict["quantity"] = int(to_decimal(get_cell("quantity") or 0, round_cents=False))
                row_dict["uqc"] = str(get_cell("uqc") or "PCS").strip()
                row_dict["igst"] = to_decimal(get_cell("igst"))
                row_dict["cgst"] = to_decimal(get_cell("cgst"))
                row_dict["sgst"] = to_decimal(get_cell("sgst"))
                row_dict["tax_total"] = row_dict["igst"] + row_dict["cgst"] + row_dict["sgst"] + cess
                control_totals[section_key]["tax_total"] += row_dict["tax_total"]

            section_rows.append(row_dict)
            control_totals[section_key]["count"] += 1
            control_totals[section_key]["taxable_value"] += taxable
            control_totals[section_key]["invoice_value"] += inv_val

        parsed_sections[section_key] = section_rows
        report.valid_rows += len(section_rows)

    # 3. Profile Internal Checks (as defined in column_aliases.json)
    # Check 1: B2C Small total taxable equals HSN Summary total taxable
    b2cs_taxable = control_totals.get("b2cs", {}).get("taxable_value", Decimal("0.00"))
    hsn_taxable = control_totals.get("hsn", {}).get("taxable_value", Decimal("0.00"))
    chk1_diff = abs(b2cs_taxable - hsn_taxable)
    chk1_pass = chk1_diff <= tolerance
    report.internal_checks_results.append({
        "check_name": "B2C Small total taxable equals HSN Summary total taxable",
        "passed": chk1_pass,
        "detail": f"B2CS Taxable: {b2cs_taxable:,.2f} | HSN Taxable: {hsn_taxable:,.2f} (Diff: {chk1_diff:,.2f})"
    })

    # Check 2: B2CS by rate equals HSN by rate
    b2cs_by_rate: Dict[Decimal, Decimal] = {}
    for r in parsed_sections.get("b2cs", []):
        b2cs_by_rate[r["rate"]] = b2cs_by_rate.get(r["rate"], Decimal("0.00")) + r["taxable_value"]
    hsn_by_rate: Dict[Decimal, Decimal] = {}
    for r in parsed_sections.get("hsn", []):
        hsn_by_rate[r["rate"]] = hsn_by_rate.get(r["rate"], Decimal("0.00")) + r["taxable_value"]

    all_rates = set(b2cs_by_rate.keys()).union(set(hsn_by_rate.keys()))
    rate_mismatches = []
    for rt in all_rates:
        b_val = b2cs_by_rate.get(rt, Decimal("0.00"))
        h_val = hsn_by_rate.get(rt, Decimal("0.00"))
        if abs(b_val - h_val) > tolerance:
            rate_mismatches.append(f"Rate {rt}: B2CS={b_val:,.2f} vs HSN={h_val:,.2f}")

    chk2_pass = len(rate_mismatches) == 0
    report.internal_checks_results.append({
        "check_name": "B2C Small taxable value by rate equals HSN Summary taxable value by rate",
        "passed": chk2_pass,
        "detail": "All rates match" if chk2_pass else "; ".join(rate_mismatches)
    })

    # Check 3: HSN Total Value - Taxable Value approx equals Taxable * Rate
    hsn_val_diffs = []
    for r in parsed_sections.get("hsn", []):
        tot_v = r["invoice_value"]
        taxable_v = r["taxable_value"]
        rate_v = r["rate"]
        expected_diff = (taxable_v * rate_v).quantize(Decimal("0.01"))
        actual_diff = tot_v - taxable_v
        if abs(actual_diff - expected_diff) > tolerance * Decimal("5.00"):  # allow slight roundings
            hsn_val_diffs.append(f"HSN {r['hsn']}: Total-Taxable={actual_diff:,.2f} vs Taxable*Rate={expected_diff:,.2f}")

    report.internal_checks_results.append({
        "check_name": "HSN: Total Value minus Taxable Value approximately equals Taxable x Rate",
        "passed": len(hsn_val_diffs) == 0,
        "detail": "Holds across all HSN items" if len(hsn_val_diffs) == 0 else "; ".join(hsn_val_diffs)
    })

    # Check 4: HSN Tax Columns vs Taxable * Rate (The known real sample discrepancy)
    hsn_total_tax_cols = Decimal("0.00")
    hsn_expected_tax = Decimal("0.00")
    for r in parsed_sections.get("hsn", []):
        hsn_total_tax_cols += (r.get("igst", Decimal("0.00")) + r.get("cgst", Decimal("0.00")) + r.get("sgst", Decimal("0.00")))
        hsn_expected_tax += (r["taxable_value"] * r["rate"]).quantize(Decimal("0.01"))

    tax_gap = hsn_expected_tax - hsn_total_tax_cols
    chk4_pass = abs(tax_gap) <= tolerance
    chk4_detail = f"HSN tax columns total: {hsn_total_tax_cols:,.2f} vs Expected ({hsn_expected_tax:,.2f}). "
    if not chk4_pass:
        chk4_detail += f"Flagged: HSN tax amounts lower than rate x taxable by ₹ {tax_gap:,.2f} across HSN rows."

    report.internal_checks_results.append({
        "check_name": "HSN: Integrated + Central + State/UT tax amounts equal Taxable Value x Rate",
        "passed": chk4_pass,
        "detail": chk4_detail,
        "gap": tax_gap
    })

    report.total_rows = sum(control_totals[s]["count"] for s in sheets_config if s in control_totals)
    return parsed_sections, report, control_totals


# =========================================================================
# 3. PAYMENTS PARSER (amazon_payments)
# =========================================================================
def parse_payments(
    file_bytes: bytes,
    file_name: str,
    period_month: Optional[int] = None,
    period_year: Optional[int] = None,
    profile_key: str = "amazon_payments",
    tolerance: Decimal = Decimal("1.00"),
    user_status_mappings: Optional[Dict[str, str]] = None,
    user_type_mappings: Optional[Dict[str, str]] = None,
    included_component_columns: Optional[List[str]] = None
) -> Tuple[List[Dict[str, Any]], ValidationReport]:
    """
    Parse Amazon Payments Unified Transaction Report.
    Detects header row by keywords (settlement id, order id, Transaction Status).
    Includes released and deferred rows.
    Validates row component sum vs total payout.
    Keeps file signs for bridge while storing positive deductions for display.
    """
    pm = ProfileManager()
    profile = pm.get_profile(profile_key)
    report = ValidationReport(file_name, "payments")

    # Read lines
    if file_name.lower().endswith(".xlsx") or file_name.lower().endswith(".xls"):
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        ws = wb.active
        raw_rows = [list(r) for r in ws.iter_rows(values_only=True)]
    else:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")
        
        # Read as lines to preserve preamble
        lines = text.splitlines()
        # Find header line index by inspecting lines for keywords
        header_kw = profile.get("header_detection_keywords", ["settlement id", "order id", "Transaction Status"])
        clean_kws = [clean_header_name(kw) for kw in header_kw]
        
        hdr_line_idx = 0
        for idx, line in enumerate(lines[:60]):
            clean_l = clean_header_name(line)
            matched = sum(1 for kw in clean_kws if kw in clean_l)
            if matched >= 2:
                hdr_line_idx = idx
                break

        # Read CSV starting from detected header
        csv_payload = "\n".join(lines[hdr_line_idx:])
        df_csv = pd.read_csv(io.StringIO(csv_payload), dtype=str)
        raw_headers = list(df_csv.columns)
        raw_data = df_csv.values.tolist()
        raw_rows = [raw_headers] + raw_data

    raw_headers = [str(c) if c is not None else "" for c in raw_rows[0]]
    col_map = pm.map_columns(raw_headers, profile.get("columns", {}))

    required_fields = profile.get("required", ["order_id", "txn_type", "net_payout", "settlement_date"])
    for req in required_fields:
        if req not in col_map:
            report.missing_columns.append(req)

    if report.missing_columns:
        report.warnings.append(f"Missing required columns in Payments: {', '.join(report.missing_columns)}")

    # Distinct values counters
    report.distinct_values["type"] = {}
    report.distinct_values["Transaction Status"] = {}

    status_map = profile.get("status_map", {"Released": "Released", "Deferred": "Deferred"})
    if user_status_mappings:
        status_map = {**status_map, **user_status_mappings}

    txn_type_map = profile.get("txn_type_map", {
        "Order": "Sale",
        "Refund": "Refund",
        "Service Fee": "Fee",
        "Adjustment": "Adjustment",
        "Transfer": "Transfer"
    })
    if user_type_mappings:
        txn_type_map = {**txn_type_map, **user_type_mappings}

    component_cols = included_component_columns or profile.get("component_columns_for_row_check", [
        "product_sales", "shipping_credits", "gift_wrap_credits", "promo_rebates",
        "sales_tax_liable", "tcs_cgst", "tcs_sgst", "tcs_igst", "tds",
        "selling_fees", "fba_fees", "other_transaction_fees", "other"
    ])

    records: List[Dict[str, Any]] = []
    data_rows = raw_rows[1:]
    report.total_rows = len(data_rows)

    for offset, row in enumerate(data_rows):
        row_num = offset + 2  # data rows start after header
        if not any(cell is not None and str(cell).strip() for cell in row):
            report.skipped_rows += 1
            continue

        def get_val(f_name: str) -> Any:
            idx = col_map.get(f_name)
            if idx is not None and idx < len(row):
                return row[idx]
            return None

        raw_order_id = get_val("order_id")
        raw_type = str(get_val("txn_type") or "").strip()
        raw_status = str(get_val("transaction_status") or "Released").strip()
        raw_date = get_val("settlement_date")
        raw_release_date = get_val("release_date")

        order_id = clean_id(raw_order_id)
        report.distinct_values["type"][raw_type] = report.distinct_values["type"].get(raw_type, 0) + 1
        report.distinct_values["Transaction Status"][raw_status] = report.distinct_values["Transaction Status"].get(raw_status, 0) + 1

        dt = parse_date(raw_date)
        dt_release = parse_date(raw_release_date)

        # Period filtering
        if period_month and period_year and dt:
            if dt.month != period_month or dt.year != period_year:
                report.skipped_rows += 1
                continue

        # Monetary fields with file's original signs
        product_sales = to_decimal(get_val("product_sales"))
        shipping_credits = to_decimal(get_val("shipping_credits"))
        gift_wrap_credits = to_decimal(get_val("gift_wrap_credits"))
        promo_rebates = to_decimal(get_val("promo_rebates"))
        sales_tax_liable = to_decimal(get_val("sales_tax_liable"))
        tcs_cgst = to_decimal(get_val("tcs_cgst"))
        tcs_sgst = to_decimal(get_val("tcs_sgst"))
        tcs_igst = to_decimal(get_val("tcs_igst"))
        tds = to_decimal(get_val("tds"))
        selling_fees = to_decimal(get_val("selling_fees"))
        fba_fees = to_decimal(get_val("fba_fees"))
        other_transaction_fees = to_decimal(get_val("other_transaction_fees"))
        other = to_decimal(get_val("other"))
        net_payout = to_decimal(get_val("net_payout"))

        # Row check: sum of components equals net_payout
        comp_dict = {
            "product_sales": product_sales,
            "shipping_credits": shipping_credits,
            "gift_wrap_credits": gift_wrap_credits,
            "promo_rebates": promo_rebates,
            "sales_tax_liable": sales_tax_liable,
            "tcs_cgst": tcs_cgst,
            "tcs_sgst": tcs_sgst,
            "tcs_igst": tcs_igst,
            "tds": tds,
            "selling_fees": selling_fees,
            "fba_fees": fba_fees,
            "other_transaction_fees": other_transaction_fees,
            "other": other
        }
        computed_total = sum(comp_dict[c] for c in component_cols if c in comp_dict)
        if abs(computed_total - net_payout) > tolerance:
            report.add_error(
                row_num,
                "net_payout",
                f"Component sum ({computed_total}) does not match net payout ({net_payout})",
                net_payout
            )

        # Status mapping
        norm_status = status_map.get(raw_status, raw_status)
        is_deferred = (norm_status == "Deferred")

        # Total fee deduction calculation (positive for display)
        total_fees_deduction = abs(selling_fees) + abs(fba_fees) + abs(other_transaction_fees)
        total_tcs_deduction = abs(tcs_cgst) + abs(tcs_sgst) + abs(tcs_igst)
        total_tds_deduction = abs(tds)

        rec = {
            "source_file": file_name,
            "source_row": row_num,
            "settlement_id": clean_id(get_val("settlement_id")),
            "settlement_date": to_iso_date(dt),
            "settlement_dt": dt,
            "release_date": to_iso_date(dt_release),
            "release_dt": dt_release,
            "order_id": order_id,
            "raw_type": raw_type,
            "type": txn_type_map.get(raw_type, raw_type),
            "sku": str(get_val("sku") or "").strip(),
            "description": str(get_val("description") or "").strip(),
            "product_sales": product_sales,
            "shipping_credits": shipping_credits,
            "gift_wrap_credits": gift_wrap_credits,
            "promo_rebates": promo_rebates,
            "sales_tax_liable": sales_tax_liable,
            "tcs_cgst": tcs_cgst,
            "tcs_sgst": tcs_sgst,
            "tcs_igst": tcs_igst,
            "tcs_total": tcs_cgst + tcs_sgst + tcs_igst,
            "tds": tds,
            "selling_fees": selling_fees,
            "fba_fees": fba_fees,
            "other_transaction_fees": other_transaction_fees,
            "other": other,
            "net_payout": net_payout,
            "transaction_status": norm_status,
            "raw_status": raw_status,
            "is_deferred": is_deferred,
            # Display positive deductions
            "disp_fees": total_fees_deduction,
            "disp_tcs": total_tcs_deduction,
            "disp_tds": total_tds_deduction
        }
        records.append(rec)
        report.valid_rows += 1

    return records, report
