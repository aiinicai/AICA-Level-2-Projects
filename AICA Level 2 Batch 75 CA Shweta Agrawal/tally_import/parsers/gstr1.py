"""
GSTR-1 parser -- category-wise reconciliation exports, auto-detected by filename.

B2B, CDNR, CDNUR, Export -> one Sales voucher per invoice/note row (flat table).

B2C Small, NIL-rated -> real-world exports for these are month-by-month
*mismatch reconciliation* reports, not a flat table: each month gets its own
block titled e.g. "B2c Small Mismatch (August)", a repeated header row, one
line per rate/place-of-supply, and a "Total" row with two parallel column
groups -- "As per Books" and "As per data Filed on GSTN". This parser reads
the "As per data Filed on GSTN" Total-row figures per month (that's what's
actually missing from the books and needs importing) and produces one
consolidated Sales voucher per month.

`mode` controls whether parsed rows are staged to post ("source_of_truth")
or staged as cross-check-only (no posting, comparison only).
"""
from __future__ import annotations

import datetime as dt
import json
import re

import pandas as pd

from .common import new_row

TAX_COLS = ["IGST", "CGST", "SGST", "CESS"]

CATEGORY_PATTERNS = {
    "CDNR": r"cdnr",
    "CDNUR": r"cdnur",
    "B2B": r"b2b",
    "EXPORT": r"export",
    "B2CS": r"b2cs|b2c[\s_-]?small|b2c",
    "NIL": r"nil",
}

PER_INVOICE_CATEGORIES = {"B2B", "CDNR", "CDNUR", "EXPORT"}
CONSOLIDATED_CATEGORIES = {"B2CS", "NIL"}

MONTHS = ["january", "february", "march", "april", "may", "june",
          "july", "august", "september", "october", "november", "december"]


def detect_category(filename: str) -> str | None:
    name = filename.lower()
    for cat, pattern in CATEGORY_PATTERNS.items():
        if re.search(pattern, name):
            return cat
    return None


def _tax_legs(r: pd.Series, df_cols) -> list:
    legs = []
    for col in TAX_COLS:
        if col in df_cols and not pd.isna(r.get(col)) and float(r.get(col, 0)) != 0:
            legs.append([col, float(r[col])])
    return legs


def _parse_per_invoice(df: pd.DataFrame, category: str, status: str) -> list[dict]:
    name_col = "Recipient Name" if "Recipient Name" in df.columns else df.columns[0]
    rows = []
    for _, r in df.iterrows():
        if pd.isna(r.get("Taxable Value")) or pd.isna(r.get("Invoice/Note Date")):
            continue
        taxable = float(r["Taxable Value"])
        legs = _tax_legs(r, df.columns)
        rows.append(new_row(
            source="GSTR1",
            date=pd.to_datetime(r["Invoice/Note Date"], dayfirst=True).date(),
            voucher_type="Sales",
            narration=f"GSTR-1 {category} {r.get('Invoice/Note No', '')}",
            reference=str(r.get("Invoice/Note No", "")),
            contra_raw=str(r.get(name_col, "")).strip(),
            gstin=str(r.get("GSTIN", "") or ""),
            taxable_value=taxable,
            tax_json=json.dumps(legs),
            amount=taxable + sum(a for _, a in legs),
            status=status,
        ))
    return rows


def _norm(s) -> str:
    return " ".join(str(s).strip().lower().split()) if not pd.isna(s) else ""


GSTR9_COLUMN_ALIASES = {
    "period": ["period"],
    "gstin": ["gstin"],
    "invoice_no": ["invoice no"],
    "invoice_date": ["invoice date"],
    "note_no": ["note no"],
    "note_date": ["note date"],
    "taxable": ["taxable value"],
    "rate": ["rate of tax", "rate"],
    "igst": ["igst"],
    "cgst": ["cgst"],
    "sgst": ["sgst"],
    "cess": ["cess"],
    "pos": ["pos", "place of supply"],
}


def _find_gstr9_header(raw: pd.DataFrame) -> int | None:
    """Real GSTR-9-derived exports (FORM GSTR-9 -> section 4B/4A etc.) have a
    3-row title block, then a header row starting with 'SNO'."""
    for i in range(min(8, len(raw))):
        v0 = raw.iloc[i, 0]
        if isinstance(v0, str) and v0.strip().upper() == "SNO":
            return i
    return None


def _parse_gstr9_style(raw: pd.DataFrame, category: str, status: str) -> list[dict]:
    header_row = _find_gstr9_header(raw)
    if header_row is None:
        return []

    cols = {_norm(c): idx for idx, c in enumerate(raw.iloc[header_row].tolist())}
    resolved = {}
    for field, aliases in GSTR9_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in cols:
                resolved[field] = cols[alias]
                break

    if "taxable" not in resolved:
        return []  # not this format after all

    def cell(row_series, field):
        idx = resolved.get(field)
        if idx is None or idx >= len(row_series):
            return None
        v = row_series[idx]
        return None if pd.isna(v) else v

    per_invoice_rows = []
    consolidated = {}  # period -> {taxable, igst, cgst, sgst, cess}

    for j in range(header_row + 1, len(raw)):
        r = raw.iloc[j]
        period = cell(r, "period")
        if period is not None and _norm(period) == "total":
            break  # Total row always marks the end of data
        taxable = cell(r, "taxable")
        if taxable is None:
            continue

        invoice_no = cell(r, "invoice_no") or cell(r, "note_no")
        invoice_date = cell(r, "invoice_date") or cell(r, "note_date")

        igst = float(cell(r, "igst") or 0)
        cgst = float(cell(r, "cgst") or 0)
        sgst = float(cell(r, "sgst") or 0)
        cess = float(cell(r, "cess") or 0)

        if invoice_no is not None and invoice_date is not None:
            # per-invoice row (B2B, or a note row sharing this layout)
            legs = [[n, a] for n, a in [("IGST", igst), ("CGST", cgst), ("SGST", sgst), ("CESS", cess)] if a]
            per_invoice_rows.append(new_row(
                source="GSTR1",
                date=pd.to_datetime(invoice_date, dayfirst=True).date(),
                voucher_type="Sales",
                narration=f"GSTR-1 {category} {invoice_no}",
                reference=str(invoice_no),
                contra_raw=str(cell(r, "gstin") or f"{category} Customer {invoice_no}"),
                gstin=str(cell(r, "gstin") or ""),
                taxable_value=float(taxable),
                tax_json=json.dumps(legs),
                amount=float(taxable) + sum(a for _, a in legs),
                status=status,
            ))
        else:
            # no invoice detail (e.g. B2CS rows) -- consolidate by period,
            # summing across rate slabs since the GL effect is the same either way
            key = _norm(period) or "consolidated"
            bucket = consolidated.setdefault(key, {"taxable": 0.0, "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0, "label": period})
            bucket["taxable"] += float(taxable)
            bucket["igst"] += igst
            bucket["cgst"] += cgst
            bucket["sgst"] += sgst
            bucket["cess"] += cess

    rows = per_invoice_rows
    for bucket in consolidated.values():
        legs = [[n, bucket[k]] for n, k in [("IGST", "igst"), ("CGST", "cgst"), ("SGST", "sgst"), ("CESS", "cess")] if bucket[k]]
        rows.append(new_row(
            source="GSTR1",
            date=_period_to_date(bucket["label"]),
            voucher_type="Sales",
            narration=f"GSTR-1 {category} consolidated ({bucket['label']})",
            reference=f"{category}-{bucket['label']}",
            contra_raw=f"{category} Consolidated Customers",
            taxable_value=bucket["taxable"],
            tax_json=json.dumps(legs),
            amount=bucket["taxable"] + sum(a for _, a in legs),
            status=status,
        ))
    return rows


def _period_to_date(period_label) -> dt.date:
    """Period strings look like 'Jan-2026' or 'Nov-2025' -- last day of that month."""
    try:
        ts = pd.to_datetime("01-" + str(period_label), format="%d-%b-%Y")
    except (ValueError, TypeError):
        return dt.date.today()
    year, month = ts.year, ts.month
    next_month = dt.date(year + 1, 1, 1) if month == 12 else dt.date(year, month + 1, 1)
    return next_month - dt.timedelta(days=1)


def _extract_fy_start_year(raw: pd.DataFrame) -> int | None:
    for i in range(min(5, len(raw))):
        val = raw.iloc[i, 0]
        if isinstance(val, str):
            m = re.search(r"F\.?Y\.?:?\s*(\d{4})-(\d{4})", val, re.IGNORECASE)
            if m:
                return int(m.group(1))
    return None


def _month_to_date(month_name: str, fy_start_year: int | None) -> dt.date:
    idx = MONTHS.index(month_name.lower()) + 1  # 1-12
    if fy_start_year is None:
        fy_start_year = dt.date.today().year
    year = fy_start_year if idx >= 4 else fy_start_year + 1  # Apr-Dec vs Jan-Mar
    next_month = dt.date(year + 1, 1, 1) if idx == 12 else dt.date(year, idx + 1, 1)
    return next_month - dt.timedelta(days=1)  # last day of that month


def _find_filed_col_start(raw: pd.DataFrame, header_row: int) -> int | None:
    """The header row has duplicate column names (Taxable Value/IGST/... appear
    once under 'As per Books' and once under 'As per data Filed on GSTN') --
    find where the second (filed) group starts from the super-header row above."""
    for j, val in enumerate(raw.iloc[header_row - 1].tolist()):
        if isinstance(val, str) and "filed" in val.lower():
            return j
    return None


def _parse_mismatch_blocks(raw: pd.DataFrame, category: str, status: str) -> list[dict]:
    fy_start = _extract_fy_start_year(raw)
    rows: list[dict] = []
    n = len(raw)
    i = 0
    while i < n:
        cell = raw.iloc[i, 0]
        if isinstance(cell, str) and "mismatch" in cell.lower():
            m = re.search(r"\(([A-Za-z]+)\)", cell)
            month = m.group(1) if m else None

            header_row = None
            for j in range(i + 1, min(i + 6, n)):
                v0 = raw.iloc[j, 0]
                if isinstance(v0, str) and v0.strip().lower().startswith("srno"):
                    header_row = j
                    break

            if header_row is None or month is None:
                i += 1
                continue

            filed_start = _find_filed_col_start(raw, header_row)
            if filed_start is None:
                i = header_row + 1
                continue

            total_row = None
            for j in range(header_row + 1, min(header_row + 40, n)):
                v2 = raw.iloc[j, 2] if raw.shape[1] > 2 else None
                if isinstance(v2, str) and v2.strip().lower() == "total":
                    total_row = j
                    break
                v0 = raw.iloc[j, 0]
                if isinstance(v0, str) and "mismatch" in v0.lower():
                    break

            if total_row is not None:
                r = raw.iloc[total_row]

                def num(offset: int) -> float:
                    col = filed_start + offset
                    if col >= len(r):
                        return 0.0
                    v = r[col]
                    return 0.0 if pd.isna(v) else float(v)

                taxable = num(0)
                legs = [[name, amt] for offset, name in [(1, "IGST"), (2, "CGST"), (3, "SGST"), (4, "CESS")]
                        if (amt := num(offset)) != 0]

                if taxable or legs:
                    rows.append(new_row(
                        source="GSTR1",
                        date=_month_to_date(month, fy_start),
                        voucher_type="Sales",
                        narration=f"GSTR-1 {category} consolidated ({month}) -- as filed on GSTN",
                        reference=f"{category}-{month}",
                        contra_raw=f"{category} Consolidated Customers",
                        taxable_value=taxable,
                        tax_json=json.dumps(legs),
                        amount=taxable + sum(a for _, a in legs),
                        status=status,
                    ))
            i = (total_row + 1) if total_row is not None else (header_row + 1)
        else:
            i += 1
    return rows


def _parse_consolidated_flat(df: pd.DataFrame, category: str, status: str) -> list[dict]:
    """Fallback for a plain flat consolidated table (Period/Rate/... + Taxable
    Value columns), in case a file doesn't use the mismatch-report format."""
    group_cols = [c for c in ["Period", "Rate", "Place of Supply", "Type"] if c in df.columns]
    if not group_cols:
        df = df.copy()
        df["Period"] = "Consolidated"
        group_cols = ["Period"]

    rows = []
    grouped = df.groupby(group_cols, dropna=False)
    for key, grp in grouped:
        taxable = float(grp["Taxable Value"].sum()) if "Taxable Value" in grp.columns else 0.0
        legs = []
        for col in TAX_COLS:
            if col in grp.columns:
                total = float(grp[col].fillna(0).sum())
                if total != 0:
                    legs.append([col, total])
        key_str = key if isinstance(key, str) else ", ".join(str(k) for k in key)
        rows.append(new_row(
            source="GSTR1",
            date=pd.to_datetime(grp.iloc[0].get("Invoice/Note Date", pd.Timestamp.today()), dayfirst=True).date()
            if "Invoice/Note Date" in grp.columns else pd.Timestamp.today().date(),
            voucher_type="Sales",
            narration=f"GSTR-1 {category} consolidated ({key_str})",
            reference=f"{category}-{key_str}",
            contra_raw=f"{category} Consolidated Customers",
            taxable_value=taxable,
            tax_json=json.dumps(legs),
            amount=taxable + sum(a for _, a in legs),
            status=status,
        ))
    return rows


def parse_workbook(file_obj, filename: str, engine: str | None, mode: str = "source_of_truth") -> list[dict]:
    """Main entry point. engine is 'openpyxl'/'xlrd' for Excel, or None for CSV."""
    category = detect_category(filename)
    if category is None:
        raise ValueError(
            f"Could not auto-detect GSTR-1 category from filename '{filename}'. "
            f"Expected one of: B2B, CDNR, CDNUR, Export, B2CS, NIL in the filename."
        )
    status = "Ready" if mode == "source_of_truth" else "CrossCheckOnly"

    # Try the real-world GSTR-9-derived format first (SNO header, 3-row title
    # block) -- covers both per-invoice (B2B) and no-invoice-detail (B2CS) rows
    # in the same shape, regardless of category.
    raw = pd.read_csv(file_obj, header=None) if engine is None else pd.read_excel(file_obj, header=None, engine=engine)
    rows = _parse_gstr9_style(raw, category, status)
    if rows:
        return rows

    if category in PER_INVOICE_CATEGORIES:
        file_obj.seek(0)
        df = pd.read_csv(file_obj) if engine is None else pd.read_excel(file_obj, engine=engine)
        return _parse_per_invoice(df, category, status)

    # consolidated: try the month-by-month mismatch-report format next
    rows = _parse_mismatch_blocks(raw, category, status)
    if rows:
        return rows

    # fall back to a plain flat table
    file_obj.seek(0)
    df = pd.read_csv(file_obj) if engine is None else pd.read_excel(file_obj, engine=engine)
    return _parse_consolidated_flat(df, category, status)
