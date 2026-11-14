"""Import a real society's records: blank template, validation and loading.

The tool reads one Excel workbook whose sheet names and column headers follow the
template produced by ``build_template``. Validation runs before the audit tests so
the auditor sees exactly what is missing or malformed instead of a stack trace.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .loaders import DATE_COLS

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "raw" / "society_data.xlsx"

# Sheets the audit tests read. Optional sheets may be absent or empty.
REQUIRED_SHEETS = ["Members", "Maintenance_Bills", "Receipts", "Bank_Statement", "Vendors", "Expenses", "Fund_Balances", "Compliance_Master"]
OPTIONAL_SHEETS = ["Other_Income"]

SHEET_HELP = {
    "Members": "One row per flat: flat_no, wing, floor, flat_type, carpet_area_sqft, member_name, occupancy (Self/Tenant), car_parking, committee_member, opening_arrears at the start of the year. PAN only in masked form.",
    "Maintenance_Bills": "One row per monthly bill per flat with each bill head (property_tax, water_charges, sinking_fund, repair_fund, service_charges, non_occupancy_charges, parking_charges, interest_on_arrears, gst_charged, bill_total). bill_month as Apr-2025.",
    "Receipts": "Every receipt from members: receipt_no, flat_no, receipt_date, amount, mode (NEFT/UPI/Cheque/Cash), reference, against_bill.",
    "Bank_Statement": "The society's bank statement for the year: txn_date, narration, debit, credit, ref, balance. Export from net banking and keep the columns in this order.",
    "Vendors": "Vendor master with vendor_code, vendor_name, category, entity_type (Individual/Firm/Company), masked PAN, address and the TDS section that applies (194C/194J/194I or blank).",
    "Expenses": "Every payment voucher: voucher_no, vendor_code, vendor_name, category, invoice_no, invoice_date, payment_date, description, taxable_value, gst_on_invoice, gross_amount, tds_deducted, net_paid, payment_mode, approved_by.",
    "Other_Income": "Non-member income: date, head (bank interest, rent of hoarding, etc.), nature, gross_amount, tds, mutual (Y/N), section_hint. Optional.",
    "Fund_Balances": "Two columns item / amount: closing balances of the sinking fund, repair fund, earmarked fixed deposits and the general fund. Items must start with the same words as in the template.",
    "Compliance_Master": "Two columns item / value: dates and facts for the compliance calendar (last AGM, last election, structural audit, insurance expiry, lift licence, TDS returns filed, advance tax paid...).",
}

REQUIRED_DATE_COLS = DATE_COLS


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def template_columns() -> dict[str, list[str]]:
    """Header row of each sheet, taken from the sample workbook so the contract is always exact."""
    xl = pd.read_excel(SAMPLE, sheet_name=None, nrows=0)
    return {k: list(v.columns) for k, v in xl.items() if k in REQUIRED_SHEETS + OPTIONAL_SHEETS}


def build_template(include_examples: bool = True) -> bytes:
    """Blank workbook with an Instructions sheet, the exact headers, and two example rows per sheet."""
    cols = template_columns()
    sample = pd.read_excel(SAMPLE, sheet_name=None) if include_examples else {}
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        rows = [("HOW TO FILL THIS TEMPLATE", ""), ("", ""),
                ("1.", "Keep the sheet names and column headers exactly as given. Add rows; do not rename or reorder columns."),
                ("2.", "Dates as real Excel dates (dd-mm-yyyy). Amounts as plain numbers without commas or the Rs sign."),
                ("3.", "flat_no must match between Members, Maintenance_Bills and Receipts (e.g. A-101)."),
                ("4.", "Delete the example rows (marked EXAMPLE in the first column where possible) before uploading."),
                ("5.", "Other_Income is optional. Minutes go in a separate zip of .txt files, one meeting per file, named MC_01_2025-04-13.txt or AGM_2025-09-28.txt."),
                ("6.", "Personal data: upload masked PANs only (first and last character). Mobile numbers are not needed for any test."),
                ("", "")] + [(k, v) for k, v in SHEET_HELP.items()]
        pd.DataFrame(rows, columns=["Sheet", "What goes here"]).to_excel(xw, sheet_name="Instructions", index=False)
        for sheet, header in cols.items():
            df = pd.DataFrame(columns=header)
            if include_examples and sheet in sample and sheet not in ("Fund_Balances", "Compliance_Master"):
                df = sample[sheet].head(2).copy()
            elif include_examples and sheet in sample:
                df = sample[sheet].copy()   # keep the full list of items: their names are the contract
                df["amount" if "amount" in df.columns else "value"] = ""
            df.to_excel(xw, sheet_name=sheet, index=False)
        ws = xw.book["Instructions"]
        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["B"].width = 120
        for sheet, header in cols.items():
            w = xw.book[sheet]
            for i, h in enumerate(header, 1):
                w.column_dimensions[w.cell(row=1, column=i).column_letter].width = max(12, min(28, len(h) + 4))
    return buf.getvalue()


def validate_workbook(data: bytes) -> ValidationReport:
    rep = ValidationReport()
    try:
        xl = pd.read_excel(io.BytesIO(data), sheet_name=None)
    except Exception as exc:
        rep.errors.append(f"The file could not be read as an Excel workbook: {exc}")
        return rep
    cols = template_columns()
    for sheet in REQUIRED_SHEETS:
        if sheet not in xl:
            rep.errors.append(f"Sheet '{sheet}' is missing.")
    for sheet, header in cols.items():
        if sheet not in xl:
            if sheet in OPTIONAL_SHEETS:
                rep.warnings.append(f"Optional sheet '{sheet}' not provided; income-tax computation will assume no non-member income.")
            continue
        df = xl[sheet]
        missing = [c for c in header if c not in df.columns]
        extra = [c for c in df.columns if c not in header and not str(c).startswith("Unnamed")]
        if missing:
            rep.errors.append(f"Sheet '{sheet}' is missing column(s): {', '.join(missing)}.")
        if extra:
            rep.warnings.append(f"Sheet '{sheet}' has extra column(s) that will be ignored: {', '.join(map(str, extra))}.")
        rep.summary[sheet] = int(len(df))
        if sheet in REQUIRED_SHEETS and len(df) == 0:
            rep.errors.append(f"Sheet '{sheet}' has no rows.")
        for c in REQUIRED_DATE_COLS.get(sheet, []):
            if c in df.columns and len(df):
                bad = pd.to_datetime(df[c], errors="coerce").isna() & df[c].notna()
                if bad.any():
                    rep.errors.append(f"Sheet '{sheet}', column '{c}': {int(bad.sum())} value(s) are not dates (first bad row {int(bad.idxmax()) + 2}).")
    if rep.errors:
        return rep
    members = xl["Members"]; bills = xl["Maintenance_Bills"]; receipts = xl["Receipts"]; expenses = xl["Expenses"]; vendors = xl["Vendors"]
    flats = set(members.flat_no.astype(str))
    if members.flat_no.duplicated().any():
        rep.errors.append("Members: duplicate flat_no values: " + ", ".join(map(str, members.flat_no[members.flat_no.duplicated()].unique()[:10])))
    for name, df in (("Maintenance_Bills", bills), ("Receipts", receipts)):
        unknown = sorted(set(df.flat_no.astype(str)) - flats)
        if unknown:
            rep.errors.append(f"{name}: {len(unknown)} flat_no value(s) not in Members (e.g. {', '.join(unknown[:5])}).")
    unknown_v = sorted(set(expenses.vendor_code.astype(str)) - set(vendors.vendor_code.astype(str)))
    if unknown_v:
        rep.warnings.append(f"Expenses: {len(unknown_v)} vendor_code value(s) not in Vendors (e.g. {', '.join(unknown_v[:5])}); TDS tests treat them as 'Others'.")
    for name, df, col in (("Maintenance_Bills", bills, "bill_total"), ("Receipts", receipts, "amount"), ("Expenses", expenses, "gross_amount")):
        if not pd.api.types.is_numeric_dtype(df[col]):
            rep.errors.append(f"{name}: column '{col}' must be numeric (remove commas, 'Rs' and blanks).")
    if "bill_month" in bills.columns and len(bills):
        months = bills.bill_month.astype(str).str.match(r"^[A-Za-z]{3}-\d{4}$")
        if not months.all():
            rep.errors.append(f"Maintenance_Bills: bill_month must look like Apr-2025 ({int((~months).sum())} row(s) differ).")
    needed_funds = ["Sinking Fund", "Repair", "Earmarked", "General"]
    items = " | ".join(xl["Fund_Balances"]["item"].astype(str))
    for n in needed_funds:
        if n.lower() not in items.lower():
            rep.warnings.append(f"Fund_Balances: no item containing '{n}'; the related fund test will report zero.")
    if receipts.amount.sum() > 0 and bills.bill_total.sum() > 0:
        ratio = receipts.amount.sum() / bills.bill_total.sum()
        if ratio < 0.3 or ratio > 1.5:
            rep.warnings.append(f"Receipts total is {ratio:.0%} of billing. Check that both sheets cover the same year.")
    return rep


def save_upload(workbook: bytes, minutes_zip: bytes | None, target: Path) -> Path:
    import zipfile
    target.mkdir(parents=True, exist_ok=True)
    (target / "society_data.xlsx").write_bytes(workbook)
    if minutes_zip:
        with zipfile.ZipFile(io.BytesIO(minutes_zip)) as z:
            (target / "minutes").mkdir(exist_ok=True)
            for n in z.namelist():
                if n.lower().endswith(".txt") and not n.startswith("__MACOSX"):
                    (target / "minutes" / Path(n).name).write_bytes(z.read(n))
    return target
