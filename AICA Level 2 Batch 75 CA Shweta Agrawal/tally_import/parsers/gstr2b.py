"""
GSTR-2B parser (invoice + note sheets).

Real GSTR-2B reconciliation exports (unlike the locked spec's idealised column
list) carry a 2-row title block above the header, use "Invoice No"/"Invoice
Date" (or "Note No"/"Note Date" on the note sheet) rather than a combined
"Invoice/Note No" column, and split invoices and credit/debit notes across
separate sheet tabs ("invoice", "note", ...). This parser reads every sheet in
the workbook, locates the real header row by searching for "Supplier Name",
and normalises column-name variants before extracting rows.

One Purchase voucher per row; RC=Yes flagged separately for RCM treatment.
"""
from __future__ import annotations

import json

import pandas as pd

from .common import new_row

TAX_COLS = ["IGST", "CGST", "SGST", "CESS"]

# canonical field -> accepted header spellings (checked case/space-insensitively)
COLUMN_ALIASES = {
    "supplier": ["supplier name"],
    "gstin": ["gstin"],
    "doc_no": ["invoice no", "note no", "invoice/note no"],
    "doc_date": ["invoice date", "note date", "invoice/note date"],
    "taxable": ["taxable value"],
    "rc": ["rc", "rc flag"],
    "remark": ["remark/matching criteria", "remark/match", "remark"],
}


def _norm(s) -> str:
    return " ".join(str(s).strip().lower().split())


def _find_header_row(raw: pd.DataFrame) -> int | None:
    """Scan the first ~10 rows for one containing 'Supplier Name'."""
    for i in range(min(10, len(raw))):
        row_vals = [_norm(v) for v in raw.iloc[i].tolist()]
        if "supplier name" in row_vals:
            return i
    return None


def _resolve_columns(columns) -> dict:
    """Maps canonical field name -> actual column label present in this sheet."""
    norm_to_actual = {_norm(c): c for c in columns}
    resolved = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in norm_to_actual:
                resolved[field] = norm_to_actual[alias]
                break
    return resolved


def _parse_sheet(raw: pd.DataFrame, sheet_name: str) -> list[dict]:
    header_row = _find_header_row(raw)
    if header_row is None:
        return []  # not a data sheet (e.g. a summary/cover tab) -- skip quietly

    df = raw.iloc[header_row + 1:].copy()
    df.columns = raw.iloc[header_row].tolist()
    df = df.reset_index(drop=True)

    cols = _resolve_columns(df.columns)
    required = ["supplier", "gstin", "doc_no", "doc_date", "taxable"]
    missing = [f for f in required if f not in cols]
    if missing:
        raise ValueError(
            f"GSTR-2B sheet '{sheet_name}': could not find columns for {missing} "
            f"(looked for header row containing 'Supplier Name'). Found columns: {list(df.columns)}"
        )

    rows = []
    for _, r in df.iterrows():
        taxable_raw = r.get(cols["taxable"])
        date_raw = r.get(cols["doc_date"])
        if pd.isna(taxable_raw) or pd.isna(date_raw):
            continue

        taxable = float(taxable_raw)
        tax_legs = []
        for col in TAX_COLS:
            actual = next((c for c in df.columns if _norm(c) == col.lower()), None)
            if actual is not None and not pd.isna(r.get(actual)) and float(r.get(actual) or 0) != 0:
                tax_legs.append([col, float(r[actual])])

        def _s(val) -> str:
            return "" if pd.isna(val) else str(val).strip()

        rc_flag = _s(r.get(cols.get("rc"))).lower() in ("y", "yes", "true", "1")
        remark = _s(r.get(cols.get("remark")))
        doc_no = _s(r.get(cols["doc_no"]))
        supplier = _s(r.get(cols["supplier"]))
        gstin = _s(r.get(cols["gstin"]))
        # Some GSTR-2B exports leave Supplier Name blank and only carry the GSTIN.
        # Fall back to the GSTIN itself as the vendor identifier so ledger
        # matching/creation still has something usable -- rename in Tally later
        # once the legal name is known.
        vendor_key = supplier or gstin

        rows.append(new_row(
            source="GSTR2B",
            date=pd.to_datetime(date_raw, dayfirst=True).date(),
            voucher_type="Purchase",
            narration=f"GSTR-2B [{sheet_name}] {doc_no} | {remark}".strip(" |"),
            reference=doc_no,
            contra_raw=vendor_key,
            gstin=gstin,
            rc_flag=rc_flag,
            itc_eligible=True,
            taxable_value=taxable,
            tax_json=json.dumps(tax_legs),
            amount=taxable + sum(a for _, a in tax_legs),
        ))
    return rows


def parse_workbook(file_obj, engine: str) -> list[dict]:
    """file_obj: a file-like object (already positioned at 0). engine: 'openpyxl' or 'xlrd'."""
    sheets = pd.read_excel(file_obj, sheet_name=None, header=None, engine=engine)
    rows: list[dict] = []
    errors: list[str] = []
    for name, raw in sheets.items():
        try:
            rows.extend(_parse_sheet(raw, name))
        except ValueError as e:
            errors.append(str(e))
    if not rows and errors:
        raise ValueError(" | ".join(errors))
    return rows
