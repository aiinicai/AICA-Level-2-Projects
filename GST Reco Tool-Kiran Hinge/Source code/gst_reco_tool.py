"""
GST Reco Tool  (version 1.0)
============================

Builds two formula-linked Excel reconciliation workbooks from Tally and Tax Power exports:

  * GST Reco Output FY<yyyy> - <Client>.xlsx
        Sales Register / Debit Note / Credit Note  vs  GSTR-1 (Tax Power)  vs  GSTR-3B Table 3.1
  * GST Reco Input FY<yyyy> - <Client>.xlsx
        Purchase / Debit Note / Credit Note / Journal Register  vs  GSTR-2B (Tax Power)  vs  GSTR-3B Table 4

Every source sheet is carried into the workbook as an Excel Table. The summaries and the
invoice-level "Reco File" are live formulas (SUMIFS / XLOOKUP / UNIQUE / FILTER), so when
rows in a data sheet are edited, added or pasted the summary and reco update by themselves.
No pivot tables. Needs Microsoft 365 / Excel 2021+ (dynamic array formulas).

HOW TO RUN
----------
First time only (in a command prompt):
    pip install streamlit openpyxl xlsxwriter

Then either:
    python gst_reco_tool.py                 -> opens the tool in your browser
    streamlit run gst_reco_tool.py          -> same thing

Or without the browser screen:
    python gst_reco_tool.py --cli --gstr1 GSTR1.xlsx --gstr3b GSTR3B.xlsx --sales Sales.xlsx
                            --gstr2b GSTR2B.xlsx --purchase Purchase.xlsx --outdir .

INPUT FORMATS (current version - "as exported" layout shared by the firm)
-------------------------------------------------------------------------
  * Tax Power GSTR-1 Section-wise summary   : one sheet per section, title rows, header row
                                              (B2B, B2CL, B2CS, CDNR, CDNUR, EXP, HSN, DOC ...)
  * Tax Power GSTR-2B Section-wise summary  : B2B, CDNR, ISD, IMPG, B2B(Rejected) ...
  * Tax Power GSTR-3B Month-wise annual     : TaxableSupplies (Table 3.1), EligibleITC (Table 4)
  * Tally registers                          : Date | Month | Particulars | Voucher Type |
                                              Voucher No. | GSTIN/UIN | Taxable | IGST | CGST | SGST
    For purchase-side registers, Voucher No. = supplier invoice / note number.

MATCHING RULES (editable values live on the "Settings" sheet of each workbook)
------------------------------------------------------------------------------
  * Invoice key = document class (I = invoice, N = note) + GSTIN + invoice number with spaces,
    / - _ . \\ removed and upper-cased.  Only rows with a GSTIN take part in the invoice reco;
    B2C rows are reconciled through the month-wise summary.
  * Month = return period for GSTR-1 / GSTR-2B rows, Month column (or Date) for Tally rows.
  * Matched if |Taxable diff| <= TolTV (default 10) and each tax head diff <= TolTax (default 1).
  * Tally note registers are added with the sign set on Settings (Sales: DN +1, CN -1;
    Purchase: DN -1, CN -1, Journal +1). GSTR-1/2B notes: Debit +, Credit -.
  * GSTR-2B ITC column excludes reverse-charge rows and rows with ITC Availability = No;
    those are shown in a separate block. Rejected (IMS) sheets are shown separately.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import openpyxl
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

TOOL_VERSION = "1.0"

FY_MONTHS = ["April", "May", "June", "July", "August", "September", "October",
             "November", "December", "January", "February", "March"]
CAL_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]

HEADER_HINTS = {
    "date", "month", "period", "return period", "particulars", "gstin", "gstin/uin",
    "gstin of supplier", "invoice no", "note no", "taxable value", "taxable", "igst", "cgst",
    "sgst", "voucher no.", "voucher no", "voucher type", "pos", "hsn/sac code", "hsn/sac",
    "document type", "receiver name", "trade/legal name", "invoice date", "note date",
    "description", "type", "port code", "bill number",
}
AMOUNT_WORDS = ("taxable", "igst", "cgst", "sgst", "cess", "value", "qty", "quantity",
                "amount", "total", "rate", "supplies")

# Reco status labels (as used in the firm's template).
OUT_STATUS = ["Matched", "Not in R1", "Not in Books", "Difference in TV", "Difference in GST"]
IN_STATUS = ["Matched", "Not in 2B", "Not in Tally", "Difference in TV", "Difference in GST"]


# --------------------------------------------------------------------------------------
# Reading source files
# --------------------------------------------------------------------------------------
@dataclass
class SourceFile:
    """One uploaded workbook, kept as bytes so it can be hashed and re-read."""
    label: str
    name: str
    data: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


@dataclass
class SheetData:
    """A tabular sheet: title rows above, one header row, data rows below."""
    name: str
    title_rows: list[list[Any]]
    title_formulas: dict[tuple[int, int], str]
    header_row: int  # 0-based row index of the header
    headers: list[str]
    rows: list[list[Any]]


@dataclass
class MatrixSheet:
    """A free-form sheet copied cell by cell (used for the GSTR-3B annual summary)."""
    name: str
    cells: list[list[Any]]

    def text(self, r: int, c: int = 0) -> str:
        try:
            v = self.cells[r][c]
        except IndexError:
            return ""
        return "" if v is None else str(v).strip()

    def find_row(self, prefix: str, start: int = 0) -> int | None:
        p = prefix.lower()
        for r in range(start, len(self.cells)):
            if self.text(r).lower().startswith(p):
                return r
        return None

    def month_header_row(self) -> int | None:
        for r in range(len(self.cells)):
            row = [str(v).strip() for v in self.cells[r] if v is not None]
            if "April" in row and "March" in row:
                return r
        return None

    def line_in_section(self, section_prefix: str, line_prefix: str,
                        after: str | None = None) -> int | None:
        """Row of e.g. 'IGST Amount' inside section '(5) All other ITC'."""
        start = 0
        if after:
            a = self.find_row(after)
            if a is None:
                return None
            start = a
        sec = self.find_row(section_prefix, start)
        if sec is None:
            return None
        r = sec + 1
        while r < len(self.cells) and self.text(r):
            if self.text(r).lower().startswith(line_prefix.lower()):
                return r
            r += 1
        return None


def _clean_header(h: Any, i: int) -> str:
    s = "" if h is None else re.sub(r"\s+", " ", str(h)).strip()
    return s or f"Column{i + 1}"


def _dedupe(headers: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for h in headers:
        k = h.lower()
        if k in seen:
            seen[k] += 1
            h = f"{h} ({seen[k]})"
        else:
            seen[k] = 1
        out.append(h)
    return out


_DATE_RE = re.compile(r"^(\d{1,2})[-/.](\d{1,2}|[A-Za-z]{3})[-/.](\d{2}|\d{4})$")
_MON3 = {m[:3].lower(): i + 1 for i, m in enumerate(CAL_MONTHS)}


def _to_date(v: Any) -> Any:
    """Convert dd-mm-yyyy / dd/mm/yy / dd-Mon-yyyy strings to dates; leave others alone."""
    if not isinstance(v, str):
        return v
    m = _DATE_RE.match(v.strip())
    if not m:
        return v
    d, mo, y = m.groups()
    mo_n = int(mo) if mo.isdigit() else _MON3.get(mo.lower())
    y_n = int(y) + (2000 if len(y) == 2 else 0)
    try:
        return dt.datetime(y_n, mo_n, int(d))
    except (TypeError, ValueError):
        return v


def _to_number(v: Any) -> Any:
    if isinstance(v, str):
        s = v.replace(",", "").strip()
        if re.fullmatch(r"-?\d+(\.\d+)?", s):
            return float(s)
    return v


def _load_books(src: SourceFile):
    wb_v = openpyxl.load_workbook(io.BytesIO(src.data), data_only=True, read_only=True)
    wb_f = openpyxl.load_workbook(io.BytesIO(src.data), data_only=False, read_only=True)
    return wb_v, wb_f


def parse_table_sheet(ws_v, ws_f, name: str) -> SheetData | None:
    """Find the header row and read the data rows of one sheet."""
    rows = [list(r) for r in ws_v.iter_rows(values_only=True)]
    hdr_idx = None
    for i, r in enumerate(rows[:30]):
        cells = [str(c).strip().lower() for c in r if c not in (None, "")]
        if len(cells) >= 3 and sum(c in HEADER_HINTS for c in cells) >= 2:
            hdr_idx = i
            break
    if hdr_idx is None:
        return None
    raw = rows[hdr_idx]
    n = max((i + 1 for i, h in enumerate(raw) if h not in (None, "")), default=0)
    headers = _dedupe([_clean_header(h, i) for i, h in enumerate(raw[:n])])

    title_formulas: dict[tuple[int, int], str] = {}
    for ri, r in enumerate(ws_f.iter_rows(max_row=hdr_idx, values_only=True)):
        for ci, v in enumerate(r):
            if isinstance(v, str) and v.startswith("="):
                title_formulas[(ri, ci)] = v

    date_cols = [i for i, h in enumerate(headers) if "date" in h.lower()]
    amt_cols = [i for i, h in enumerate(headers)
                if any(w in h.lower() for w in AMOUNT_WORDS) and "date" not in h.lower()]
    data = []
    for r in rows[hdr_idx + 1:]:
        r = list(r[:n]) + [None] * (n - len(r))
        if all(v is None or (isinstance(v, str) and not v.strip()) for v in r):
            continue
        if any(isinstance(v, str) and v.strip().lower() in ("grand total", "total")
               for v in r[:5]):
            continue
        for i in date_cols:
            r[i] = _to_date(r[i])
        for i in amt_cols:
            r[i] = _to_number(r[i])
        data.append(r)
    title_rows = [list(r) for r in rows[:hdr_idx]]
    return SheetData(name, title_rows, title_formulas, hdr_idx, headers, data)


def read_tabular_workbook(src: SourceFile) -> tuple[list[SheetData], list[str]]:
    wb_v, wb_f = _load_books(src)
    out, skipped = [], []
    for name in wb_v.sheetnames:
        sd = parse_table_sheet(wb_v[name], wb_f[name], name)
        if sd is None:
            skipped.append(name)
        else:
            out.append(sd)
    return out, skipped


def read_3b_sheet(src: SourceFile, kind: str) -> MatrixSheet | None:
    """kind = 'output' (Table 3.1) or 'input' (Table 4)."""
    wb_v, _ = _load_books(src)
    wanted = ("taxablesupplies",) if kind == "output" else ("eligibleitc",)
    marker = "3.1" if kind == "output" else "eligible itc"
    chosen = None
    for name in wb_v.sheetnames:
        if name.replace(" ", "").lower() in wanted:
            chosen = name
            break
    if chosen is None:
        for name in wb_v.sheetnames:
            txt = " ".join(str(v) for r in wb_v[name].iter_rows(max_row=5, values_only=True)
                           for v in r if v is not None).lower()
            if marker in txt:
                chosen = name
                break
    if chosen is None:
        return None
    cells = [list(r) for r in wb_v[chosen].iter_rows(values_only=True)]
    return MatrixSheet(chosen, cells)


# --------------------------------------------------------------------------------------
# Writing helpers
# --------------------------------------------------------------------------------------
def sref(h: str) -> str:
    """Escape a column name for a structured reference."""
    return h.replace("'", "''").replace("[", "'[").replace("]", "']").replace("#", "'#")


def find_col(headers: list[str], *cands: str, exact_only: bool = False) -> str | None:
    low = {h.lower(): h for h in headers}
    for c in cands:
        if c.lower() in low:
            return low[c.lower()]
    if exact_only:
        return None
    for c in cands:
        for h in headers:
            if c.lower() in h.lower():
                return h
    return None


@dataclass
class TableInfo:
    name: str
    sheet: str
    headers: list[str]
    nrows: int
    cols: dict[str, str | None] = field(default_factory=dict)  # role -> header

    def ref(self, role_or_header: str) -> str:
        h = self.cols.get(role_or_header, role_or_header)
        return f"{self.name}[{sref(h)}]"

    def has(self, role: str) -> bool:
        return bool(self.cols.get(role))


def month_formula(x: str) -> str:
    """Excel expression turning a period / month / date cell into a month name."""
    return (f'IF(TRIM({x}&"")="","",IF(ISNUMBER({x}),TEXT({x},"mmmm"),'
            f'IFERROR(INDEX(MonthList,MATCH(LEFT(TRIM({x}),3),MonthAbbr,0)),'
            f'IFERROR(INDEX(MonthList,VALUE(LEFT(TRIM({x}),2))),""))))')


def norm_formula(x: str) -> str:
    s = f'TRIM({x}&"")'
    for ch in (" ", "/", "-", "_", ".", "\\"):
        s = f'SUBSTITUTE({s},"{ch}","")'
    return f"UPPER({s})"


def key_formula(cls: str, gstin: str, no: str) -> str:
    return (f'=IF(OR(TRIM({gstin}&"")="",TRIM({no}&"")=""),"",'
            f'"{cls}|"&UPPER(TRIM({gstin}&""))&"|"&{norm_formula(no)})')


def this_row(h: str) -> str:
    return f"[@[{sref(h)}]]"


class Builder:
    """Wraps an xlsxwriter workbook with the formats and table registry we need."""

    def __init__(self, target):
        self.wb = xlsxwriter.Workbook(target, {
            "strings_to_formulas": False, "strings_to_urls": False,
            "default_date_format": "dd-mm-yyyy", "nan_inf_to_errors": True,
        })
        f = self.wb.add_format
        self.f_title = f({"bold": True, "font_size": 13})
        self.f_bold = f({"bold": True})
        self.f_hdr = f({"bold": True, "bg_color": "#1F4E78", "font_color": "#FFFFFF",
                        "border": 1, "text_wrap": True, "valign": "vcenter", "align": "center"})
        self.f_hdr2 = f({"bold": True, "bg_color": "#DDEBF7", "border": 1, "align": "center"})
        self.f_amt = f({"num_format": "#,##0.00;[Red]-#,##0.00"})
        self.f_amt_b = f({"num_format": "#,##0.00;[Red]-#,##0.00", "bold": True, "top": 1})
        self.f_amt_box = f({"num_format": "#,##0.00;[Red]-#,##0.00", "border": 1})
        self.f_amt_tot = f({"num_format": "#,##0.00;[Red]-#,##0.00", "bold": True, "border": 1,
                            "bg_color": "#F2F2F2"})
        self.f_cnt_box = f({"num_format": "#,##0", "border": 1})
        self.f_txt_box = f({"border": 1})
        self.f_txt_tot = f({"border": 1, "bold": True, "bg_color": "#F2F2F2"})
        self.f_date = f({"num_format": "dd-mm-yyyy;;"})
        self.f_helper_hdr = f({"bold": True, "bg_color": "#FFF2CC"})
        self.f_note = f({"italic": True, "font_color": "#595959"})
        self.f_red = f({"bg_color": "#FFC7CE", "font_color": "#9C0006"})
        self.f_green = f({"bg_color": "#C6EFCE", "font_color": "#006100"})
        self.f_amber = f({"bg_color": "#FFEB9C", "font_color": "#9C5700"})
        self.f_blue = f({"bg_color": "#DDEBF7", "font_color": "#1F4E78"})
        self.f_check = f({"italic": True, "font_color": "#595959", "num_format":
                          "#,##0.00;[Red]-#,##0.00", "border": 1})
        self.tables: dict[str, TableInfo] = {}
        self.warnings: list[str] = []
        self._used_sheet_names: set[str] = set()
        self._used_table_names: set[str] = set()

    # ---- names ------------------------------------------------------------------------
    def sheet_name(self, want: str) -> str:
        base = re.sub(r"[\[\]:*?/\\]", "-", want)[:31]
        name, i = base, 2
        while name.lower() in self._used_sheet_names:
            suffix = f" ({i})"
            name = base[:31 - len(suffix)] + suffix
            i += 1
        self._used_sheet_names.add(name.lower())
        return name

    def table_name(self, want: str) -> str:
        base = "t_" + re.sub(r"[^A-Za-z0-9_]", "_", want)
        name, i = base, 2
        while name.lower() in self._used_table_names:
            name = f"{base}_{i}"
            i += 1
        self._used_table_names.add(name.lower())
        return name

    # ---- data sheets -----------------------------------------------------------------
    def add_data_sheet(self, sd: SheetData, sheet_title: str, key: str,
                       helpers: list[tuple[str, str]], cols: dict[str, str | None]) -> TableInfo:
        """Write one source sheet as an Excel Table plus formula helper columns."""
        ws = self.wb.add_worksheet(self.sheet_name(sheet_title))
        tname = self.table_name(key)
        all_headers = sd.headers + [h for h, _ in helpers]
        hdr = sd.header_row
        ncol = len(all_headers)

        # Title block (as in the source); formulas there become table totals.
        for r, row in enumerate(sd.title_rows):
            for c, v in enumerate(row):
                if (r, c) in sd.title_formulas or v is None:
                    continue
                ws.write(r, c, v, self.f_bold if r == 0 else None)
        numeric = [i for i, h in enumerate(sd.headers)
                   if any(w in h.lower() for w in ("taxable", "igst", "cgst", "sgst", "cess",
                                                    "invoice value", "total value", "note value"))]
        if sd.title_formulas:
            for (r, c), f in sd.title_formulas.items():
                if c < len(sd.headers):
                    fn = "SUBTOTAL(9," if "SUBTOTAL" in f.upper() else "SUM("
                    ws.write_formula(r, c, f"={fn}{tname}[{sref(sd.headers[c])}])", self.f_amt)
        elif hdr >= 1:
            for c in numeric:
                ws.write_formula(hdr - 1, c, f"=SUBTOTAL(9,{tname}[{sref(sd.headers[c])}])",
                                 self.f_amt_b)

        data = sd.rows if sd.rows else [[None] * len(sd.headers)]
        columns = [{"header": h} for h in sd.headers]
        for c in numeric:
            columns[c]["format"] = self.f_amt
        for i, h in enumerate(sd.headers):
            if "date" in h.lower():
                columns[i]["format"] = self.f_date
        for h, formula in helpers:
            columns.append({"header": h, "formula": formula, "header_format": self.f_helper_hdr})
        ws.add_table(hdr, 0, hdr + len(data), ncol - 1, {
            "name": tname, "columns": columns, "data": [list(r) for r in data],
            "style": "Table Style Light 9",
        })
        for i, h in enumerate(all_headers):
            width = 12 if i in numeric else min(max(len(h) + 2, 10), 34)
            if h.lower() in ("particulars", "receiver name", "trade/legal name"):
                width = 32
            ws.set_column(i, i, width)
        ws.freeze_panes(hdr + 1, 0)
        if helpers and hdr >= 1:
            ws.write(hdr - 1, len(sd.headers), "Tool helper columns (formulas)", self.f_note)
        info = TableInfo(tname, ws.get_name(), all_headers, len(sd.rows), cols)
        self.tables[key] = info
        return info

    def add_matrix_sheet(self, ms: MatrixSheet, title: str) -> str:
        ws = self.wb.add_worksheet(self.sheet_name(title))
        for r, row in enumerate(ms.cells):
            for c, v in enumerate(row):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    ws.write_number(r, c, v, self.f_amt)
                else:
                    ws.write(r, c, v, self.f_bold if c == 0 and str(v).startswith(("(", "4", "3"))
                             else None)
        ws.set_column(0, 0, 60)
        ws.set_column(1, 13, 13)
        ws.freeze_panes(0, 1)
        return ws.get_name()

    def close(self):
        self.wb.close()


# --------------------------------------------------------------------------------------
# Sheet-role helpers
# --------------------------------------------------------------------------------------
def tally_role(sheet_name: str) -> str:
    s = sheet_name.lower()
    if "debit" in s:
        return "DN"
    if "credit" in s:
        return "CN"
    if "journal" in s:
        return "JR"
    return "MAIN"


def tally_cols(headers: list[str]) -> dict[str, str | None]:
    return {
        "date": find_col(headers, "Date"),
        "month": find_col(headers, "Month", exact_only=True),
        "name": find_col(headers, "Particulars", "Party Name", "Party"),
        "no": find_col(headers, "Voucher No.", "Voucher No", "Supplier Invoice No",
                       "Invoice No"),
        "gstin": find_col(headers, "GSTIN/UIN", "GSTIN"),
        "tv": find_col(headers, "Taxable Value", "Taxable"),
        "igst": find_col(headers, "IGST"),
        "cgst": find_col(headers, "CGST"),
        "sgst": find_col(headers, "SGST", "UTGST"),
    }


def portal_cols(headers: list[str], note: bool = False) -> dict[str, str | None]:
    return {
        "period": find_col(headers, "Return Period", "Period", exact_only=True),
        "name": find_col(headers, "Receiver Name", "Trade/Legal name"),
        "gstin": find_col(headers, "GSTIN", "GSTIN of supplier", exact_only=True)
        or find_col(headers, "GSTIN"),
        "no": find_col(headers, "Note No" if note else "Invoice No", exact_only=True),
        "date": find_col(headers, "Note Date" if note else "Invoice Date", exact_only=True),
        "note_type": find_col(headers, "Note Type", exact_only=True) if note else None,
        "tv": find_col(headers, "Taxable Value", exact_only=True),
        "igst": find_col(headers, "IGST", exact_only=True),
        "cgst": find_col(headers, "CGST", exact_only=True),
        "sgst": find_col(headers, "SGST", exact_only=True),
        "rc": find_col(headers, "Reverse Charge", exact_only=True),
        "itc": find_col(headers, "ITC Availibility", "ITC Availability"),
    }


def tally_helpers(cols: dict[str, str | None], cls: str) -> list[tuple[str, str]]:
    m = cols.get("month")
    d = cols.get("date")
    if m and d:
        month = (f'=IF(TRIM({this_row(m)}&"")<>"",{month_formula(this_row(m))},'
                 f'IF(ISNUMBER({this_row(d)}),TEXT({this_row(d)},"mmmm"),""))')
    elif m:
        month = "=" + month_formula(this_row(m))
    elif d:
        month = f'=IF(ISNUMBER({this_row(d)}),TEXT({this_row(d)},"mmmm"),"")'
    else:
        month = '=""'
    if cols.get("gstin") and cols.get("no"):
        key = key_formula(cls, this_row(cols["gstin"]), this_row(cols["no"]))
    else:
        key = '=""'
    cols["month_h"] = "Rec Month"
    cols["key"] = "Key"
    return [("Rec Month", month), ("Key", key)]


def portal_helpers(cols: dict[str, str | None], cls: str, flags: bool) -> list[tuple[str, str]]:
    out = []
    p = cols.get("period")
    out.append(("Rec Month", "=" + month_formula(this_row(p)) if p else '=""'))
    cols["month_h"] = "Rec Month"
    if cols.get("gstin") and cols.get("no"):
        out.append(("Key", key_formula(cls, this_row(cols["gstin"]), this_row(cols["no"]))))
        cols["key"] = "Key"
    if cols.get("note_type"):
        out.append(("NT", f'=UPPER(LEFT(TRIM({this_row(cols["note_type"])}&""),1))'))
        cols["nt"] = "NT"
    if flags:
        rc, itc = cols.get("rc"), cols.get("itc")
        rc_t = f'UPPER(LEFT(TRIM({this_row(rc)}&""),1))="Y"' if rc else "FALSE"
        itc_t = f'UPPER(LEFT(TRIM({this_row(itc)}&""),1))="N"' if itc else "FALSE"
        out.append(("Flag", f'=IF({rc_t},"RCM",IF({itc_t},"ITC not available",""))'))
        cols["flag"] = "Flag"
    return out


# --------------------------------------------------------------------------------------
# Formula terms for the summaries
# --------------------------------------------------------------------------------------
@dataclass
class Term:
    table: TableInfo
    role: str                      # tv / igst / cgst / sgst
    sign: str = "+"                # "+", "-" or "+Sign_DN*"
    extra: list[tuple[str, str]] = field(default_factory=list)  # (role, criterion literal)

    def render(self, month_ref: str | None) -> str | None:
        t = self.table
        if not t.has(self.role):
            return None
        crit = []
        if month_ref is not None:
            crit.append(f"{t.ref('month_h')},{month_ref}")
        for role, lit in self.extra:
            if not t.has(role):
                if lit == '""':
                    continue  # "blank" criterion on a missing column: nothing to exclude
                return None
            crit.append(f"{t.ref(role)},{lit}")
        if crit:
            body = f"SUMIFS({t.ref(self.role)},{','.join(crit)})"
        else:
            body = f"SUM({t.ref(self.role)})"
        return f"{self.sign}{body}"


def render_terms(terms: list[Term], month_ref: str | None) -> str:
    parts = [p for p in (t.render(month_ref) for t in terms) if p]
    if not parts:
        return "=0"
    s = "".join(parts)
    if s.startswith("+"):
        s = s[1:]
    return "=" + s


def note_terms(t: TableInfo, role: str, extra: list[tuple[str, str]] | None = None) -> list[Term]:
    extra = extra or []
    if not t.has("nt"):
        return [Term(t, role, "+", extra)]
    return [Term(t, role, "+", extra + [("nt", '"D"')]),
            Term(t, role, "-", extra + [("nt", '"C"')])]


# --------------------------------------------------------------------------------------
# Common sheet writers
# --------------------------------------------------------------------------------------
def write_settings(b: Builder, client: str, fy: str, side: str,
                   sources: list[SourceFile], notes: list[str]) -> None:
    ws = b.wb.add_worksheet(b.sheet_name("Settings"))
    ws.set_column(0, 0, 44)
    ws.set_column(1, 1, 18)
    ws.set_column(3, 3, 4)
    ws.set_column(4, 5, 12)
    ws.write("A1", "Settings (edit the yellow cells - all formulas use them)", b.f_title)
    inp = b.wb.add_format({"bg_color": "#FFF2CC", "border": 1})
    rows = [("Client", client, None), ("Financial year", fy, None),
            ("Tolerance - Taxable value (Rs.)", 10, "TolTV"),
            ("Tolerance - each tax head (Rs.)", 1, "TolTax")]
    if side == "output":
        rows += [("Sign for Sales Debit Note register", 1, "Sign_DN"),
                 ("Sign for Sales Credit Note register", -1, "Sign_CN")]
    else:
        rows += [("Sign for Purchase Debit Note register", -1, "Sign_DN"),
                 ("Sign for Purchase Credit Note register", -1, "Sign_CN"),
                 ("Sign for Journal Register", 1, "Sign_JR")]
    for i, (label, val, name) in enumerate(rows):
        r = 2 + i
        ws.write(r, 0, label)
        ws.write(r, 1, val, inp)
        if name:
            b.wb.define_name(name, f"='{ws.get_name()}'!$B${r + 1}")
    ws.write("E1", "Month", b.f_bold)
    ws.write("F1", "Abbr", b.f_bold)
    for i, m in enumerate(CAL_MONTHS):
        ws.write(1 + i, 4, m)
        ws.write(1 + i, 5, m[:3])
    b.wb.define_name("MonthList", f"='{ws.get_name()}'!$E$2:$E$13")
    b.wb.define_name("MonthAbbr", f"='{ws.get_name()}'!$F$2:$F$13")

    r = 3 + len(rows)
    ws.write(r, 0, "Run information", b.f_title)
    r += 1
    ws.write_row(r, 0, ["Generated on", dt.datetime.now().strftime("%d-%m-%Y %H:%M")])
    ws.write_row(r + 1, 0, ["Tool version", TOOL_VERSION])
    r += 3
    ws.write_row(r, 0, ["Source", "File name", "", "", "", "", "SHA-256"], b.f_bold)
    for s in sources:
        r += 1
        ws.write_row(r, 0, [s.label, s.name, "", "", "", "", s.sha256])
    r += 2
    ws.write(r, 0, "Notes / assumptions", b.f_title)
    for n in notes + b.warnings:
        r += 1
        ws.write(r, 0, n)


def add_status_cf(b: Builder, ws, rng: str, statuses: list[str]) -> None:
    colours = [b.f_green, b.f_red, b.f_red, b.f_amber, b.f_amber]
    for s, f in zip(statuses, colours):
        ws.conditional_format(rng, {"type": "cell", "criteria": "==", "value": f'"{s}"',
                                    "format": f})


def write_reco(b: Builder, ws, books: list[TableInfo], rets: list[TableInfo], side: str,
               client: str, fy: str) -> None:
    """Invoice-level reco built entirely from dynamic-array formulas."""
    ret_label = "GSTR-1" if side == "output" else "GSTR-2B"
    st = OUT_STATUS if side == "output" else IN_STATUS
    ws.write("B1", f"Dealer Name: {client}", b.f_bold)
    ws.write("B2", "GSTIN:")
    ws.write("B3", f"FinYear: {fy}")
    ws.write("E1", "Rows build themselves from the data sheets (Excel 365). Do not type inside "
                   "the coloured formula columns; Remarks2 is free text but rows re-sort when "
                   "data changes.", b.f_note)
    headers = ["Key", "Data Dource", "Trade/Legal name", "GSTIN", "Invoice No", "Invoice Date",
               "Taxable Value", "IGST", "CGST", "SGST", "Remarks1", "Remarks2",
               "Data Dource", "Trade/Legal name", "GSTIN", "Invoice No", "Invoice Date",
               "Taxable Value", "IGST", "CGST", "SGST",
               "Diff TV", "Diff IGST", "Diff CGST", "Diff SGST",
               "Books rows", f"{ret_label} rows", f"{ret_label} month", "Books month"]
    if side == "input":
        headers.append("2B flag")
    ws.write_row(4, 0, headers, b.f_hdr)
    ws.set_row(4, 30)

    bk = [t for t in books if t.has("key")]
    rt = [t for t in rets if t.has("key")]
    if not bk and not rt:
        ws.write("A6", "No GSTIN-wise documents available to reconcile.", b.f_note)
        return

    def vstack(ts: list[TableInfo], role: str) -> str | None:
        ts = [t for t in ts if t.has(role) and t.has("key")]
        if not ts:
            return None
        return "VSTACK(" + ",".join(t.ref(role) for t in ts) + ")", \
               "VSTACK(" + ",".join(t.ref("key") for t in ts) + ")"

    keys_all = "VSTACK(" + ",".join(t.ref("key") for t in bk + rt) + ")"
    A = "ANCHORARRAY(A6)"

    def dyn(col: str, formula: str, fmt=None):
        ws.write_dynamic_array_formula(f"{col}6:{col}6", formula, fmt)

    def lookup(ts: list[TableInfo], role: str, text: bool, present_col: str) -> str:
        v = vstack(ts, role)
        if v is None:
            return f'=IF({A}="","","")'
        vals, keys = v
        x = f'XLOOKUP({A},{keys},{vals},"")'
        if text:
            x += '&""'
        return f'=IF(ANCHORARRAY({present_col}6)>0,{x},"")'

    def sumk(ts: list[TableInfo], role: str) -> str:
        parts = [f"SUMIFS({t.ref(role)},{t.ref('key')},{A})" for t in ts if t.has(role)]
        return f'=IF({A}="",0,' + ("+".join(parts) if parts else "0") + ")"

    def count(ts: list[TableInfo]) -> str:
        parts = [f"COUNTIF({t.ref('key')},{A})" for t in ts]
        return f'=IF({A}="",0,' + ("+".join(parts) if parts else "0") + ")"

    dyn("A", f'=IFERROR(SORT(UNIQUE(FILTER({keys_all},{keys_all}<>""))),"")')
    dyn("Z", count(bk), b.f_cnt_box)
    dyn("AA", count(rt), b.f_cnt_box)
    dyn("B", '=IF(ANCHORARRAY(Z6)>0,"Books","")')
    dyn("M", f'=IF(ANCHORARRAY(AA6)>0,"{ret_label}","")')
    for col, role, txt in (("C", "name", True), ("D", "gstin", True), ("E", "no", True),
                           ("F", "date", False)):
        dyn(col, lookup(bk, role, txt, "Z"), b.f_date if col == "F" else None)
    for col, role, txt in (("N", "name", True), ("O", "gstin", True), ("P", "no", True),
                           ("Q", "date", False)):
        dyn(col, lookup(rt, role, txt, "AA"), b.f_date if col == "Q" else None)
    for col, role in (("G", "tv"), ("H", "igst"), ("I", "cgst"), ("J", "sgst")):
        dyn(col, sumk(bk, role), b.f_amt)
    for col, role in (("R", "tv"), ("S", "igst"), ("T", "cgst"), ("U", "sgst")):
        dyn(col, sumk(rt, role), b.f_amt)
    for col, l, r in (("V", "G", "R"), ("W", "H", "S"), ("X", "I", "T"), ("Y", "J", "U")):
        dyn(col, f'=IF({A}="","",ANCHORARRAY({l}6)-ANCHORARRAY({r}6))', b.f_amt)
    dyn("K", (f'=IF({A}="","",IF(ANCHORARRAY(Z6)=0,"{st[2]}",IF(ANCHORARRAY(AA6)=0,"{st[1]}",'
              f'IF(ABS(ANCHORARRAY(V6))>TolTV,"{st[3]}",'
              f'IF((ABS(ANCHORARRAY(W6))>TolTax)+(ABS(ANCHORARRAY(X6))>TolTax)'
              f'+(ABS(ANCHORARRAY(Y6))>TolTax)>0,"{st[4]}","{st[0]}")))))'))
    dyn("AB", lookup(rt, "month_h", True, "AA"))
    dyn("AC", lookup(bk, "month_h", True, "Z"))
    if side == "input":
        dyn("AD", lookup(rt, "flag", True, "AA"))

    last = 5 + max(sum(t.nrows for t in bk + rt), 1) + 500
    add_status_cf(b, ws, f"K6:K{last}", st)
    # Column formats apply to every spilled row (a cell format would only cover row 6).
    ws.set_column("A:A", 30, b.f_note)
    ws.set_column("B:B", 9)
    ws.set_column("C:C", 28)
    ws.set_column("D:D", 17)
    ws.set_column("E:E", 13)
    ws.set_column("F:F", 11, b.f_date)
    ws.set_column("G:J", 13, b.f_amt)
    ws.set_column("K:K", 17)
    ws.set_column("L:L", 22)
    ws.set_column("M:M", 9)
    ws.set_column("N:N", 28)
    ws.set_column("O:O", 17)
    ws.set_column("P:P", 13)
    ws.set_column("Q:Q", 11, b.f_date)
    ws.set_column("R:Y", 13, b.f_amt)
    ws.set_column("Z:AA", 10, b.f_cnt_box)
    ws.set_column("AB:AD", 14)
    ws.autofilter(4, 0, last, len(headers) - 1)
    ws.freeze_panes(5, 3)


def write_status_block(b: Builder, ws, row: int, reco_sheet: str, statuses: list[str],
                       label_books: str, label_ret: str) -> int:
    q = f"'{reco_sheet}'"
    ws.write(row, 1, "Invoice-level reco status (from Reco File)", b.f_bold)
    ws.write_row(row + 1, 1, ["Status", "Count", f"TV as per {label_books}",
                              f"TV as per {label_ret}"], b.f_hdr2)
    for i, s in enumerate(statuses):
        r = row + 2 + i
        ws.write(r, 1, s, b.f_txt_box)
        ws.write_dynamic_array_formula(
            r, 2, r, 2, f'=COUNTIF(ANCHORARRAY({q}!$K$6),$B{r + 1})', b.f_cnt_box)
        ws.write_dynamic_array_formula(
            r, 3, r, 3, f'=SUMIF(ANCHORARRAY({q}!$K$6),$B{r + 1},ANCHORARRAY({q}!$G$6))',
            b.f_amt_box)
        ws.write_dynamic_array_formula(
            r, 4, r, 4, f'=SUMIF(ANCHORARRAY({q}!$K$6),$B{r + 1},ANCHORARRAY({q}!$R$6))',
            b.f_amt_box)
    r = row + 2 + len(statuses)
    ws.write(r, 1, "Total", b.f_txt_tot)
    for c in (2, 3, 4):
        col = xl_col_to_name(c)
        ws.write_formula(r, c, f"=SUM({col}{row + 3}:{col}{r})", b.f_amt_tot)
    return r + 2


# --------------------------------------------------------------------------------------
# OUTPUT workbook
# --------------------------------------------------------------------------------------
def build_output(target, client: str, fy: str, gstr1: SourceFile | None,
                 gstr3b: SourceFile | None, sales: SourceFile | None) -> list[str]:
    b = Builder(target)
    notes: list[str] = []
    summary = b.wb.add_worksheet(b.sheet_name("Output Summary"))
    # ---- Tally ------------------------------------------------------------------------
    books: list[TableInfo] = []
    book_terms: dict[str, list[Term]] = {r: [] for r in ("tv", "igst", "cgst", "sgst")}
    tally_sheets: list[SheetData] = []
    if sales:
        tally_sheets, skipped = read_tabular_workbook(sales)
        notes += [f"Sales file: sheet '{s}' has no recognisable header - not used."
                  for s in skipped]
    r1_sheets: list[SheetData] = []
    if gstr1:
        r1_sheets, skipped = read_tabular_workbook(gstr1)
        notes += [f"GSTR-1 file: sheet '{s}' has no recognisable header - not used."
                  for s in skipped]
    ms = read_3b_sheet(gstr3b, "output") if gstr3b else None
    if gstr3b and ms is None:
        b.warnings.append("GSTR-3B file: TaxableSupplies (Table 3.1) sheet not found.")

    # Tabs appear in creation order: Summary, Reco File, then the data sheets.
    reco_ws = b.wb.add_worksheet(b.sheet_name("Reco File"))

    for sd in tally_sheets:
        role = tally_role(sd.name)
        cols = tally_cols(sd.headers)
        if not cols["gstin"]:
            b.warnings.append(f"Sales file sheet '{sd.name}': no GSTIN column - "
                              "invoice-level reco not possible for this sheet.")
        cls = "I" if role == "MAIN" else "N"
        helpers = tally_helpers(cols, cls)
        t = b.add_data_sheet(sd, sd.name, f"S_{sd.name}", helpers, cols)
        books.append(t)
        sign = {"MAIN": "+", "DN": "+Sign_DN*", "CN": "+Sign_CN*", "JR": "+"}[role]
        for k in book_terms:
            book_terms[k].append(Term(t, k, sign))

    sheet3b = b.add_matrix_sheet(ms, "GSTR-3B") if ms else None

    rets: list[TableInfo] = []
    r1_terms: dict[str, list[Term]] = {r: [] for r in ("tv", "igst", "cgst", "sgst")}
    section_tv: dict[str, list[Term]] = {}
    for sd in r1_sheets:
        sec = sd.name.strip().upper()
        note = sec in ("CDNR", "CDNUR")
        cols = portal_cols(sd.headers, note=note)
        doc_level = sec in ("B2B", "CDNR")
        helpers = portal_helpers(cols, "N" if note else "I", flags=False)
        if not doc_level:
            helpers = [h for h in helpers if h[0] != "Key"]
            cols.pop("key", None)
        t = b.add_data_sheet(sd, f"GSTR-1 {sd.name}", f"R1_{sd.name}", helpers, cols)
        if doc_level:
            rets.append(t)
        if sec in ("B2B", "B2CL", "B2CS", "EXP"):
            for k in r1_terms:
                r1_terms[k].append(Term(t, k))
            section_tv[sec] = [Term(t, "tv")]
        elif note:
            for k in r1_terms:
                r1_terms[k] += note_terms(t, k)
            section_tv[sec] = note_terms(t, "tv")

    # ---- 3B row lookup ------------------------------------------------------------------
    def r3b(section: str, line: str) -> int | None:
        if not ms:
            return None
        r = ms.line_in_section(section, line)
        if r is None:
            b.warnings.append(f"GSTR-3B: row '{line}' under '{section}' not found.")
        return r

    hdr3b = ms.month_header_row() if ms else None
    rows3b = {
        "tv": [r3b("(a) Outward taxable", "Total Taxable Value"),
               r3b("(b) Outward taxable", "Total Taxable Value")],
        "igst": [r3b("(a) Outward taxable", "IGST"), r3b("(b) Outward taxable", "IGST")],
        "cgst": [r3b("(a) Outward taxable", "CGST")],
        "sgst": [r3b("(a) Outward taxable", "SGST")],
    }

    def f3b(role: str, mref: str | None) -> str:
        if sheet3b is None or hdr3b is None:
            return "=0"
        q = f"'{sheet3b}'"
        parts = []
        for r in rows3b[role]:
            if r is None:
                continue
            if mref is None:
                parts.append(f"SUM({q}!$B${r + 1}:$M${r + 1})")
            else:
                parts.append(f"SUMIF({q}!${hdr3b + 1}:${hdr3b + 1},{mref},{q}!${r + 1}:${r + 1})")
        return "=" + ("+".join(parts) if parts else "0")

    # ---- Reco ---------------------------------------------------------------------------
    reco_name = reco_ws.get_name()
    write_reco(b, reco_ws, books, rets, "output", client, fy)

    # ---- Summary ------------------------------------------------------------------------
    ws = summary
    ws.set_column(0, 0, 2)
    ws.set_column(1, 1, 30)
    ws.set_column(2, 16, 14)
    ws.set_column(6, 6, 3)
    ws.set_column(11, 11, 3)
    ws.write("B2", client, b.f_title)
    ws.write("B3", "GST Reco ", b.f_bold)
    ws.write("C3", f"FY {fy}", b.f_bold)
    ws.write("B5", "Output", b.f_bold)
    ws.write("C5", "As per Tally", b.f_bold)
    ws.write("H5", "As per GSTR 3B", b.f_bold)
    ws.write("M5", "As per GSTR 1", b.f_bold)
    heads = ["Taxable", "IGST", "CGST", "SGST"]
    ws.write("B6", "Month", b.f_hdr2)
    for c0 in (2, 7, 12):
        ws.write_row(5, c0, heads, b.f_hdr2)
    roles = ["tv", "igst", "cgst", "sgst"]
    for i, m in enumerate(FY_MONTHS):
        r = 6 + i
        ws.write(r, 1, m, b.f_txt_box)
        mref = f"$B{r + 1}"
        for j, role in enumerate(roles):
            ws.write_formula(r, 2 + j, render_terms(book_terms[role], mref), b.f_amt_box)
            ws.write_formula(r, 7 + j, f3b(role, mref), b.f_amt_box)
            ws.write_formula(r, 12 + j, render_terms(r1_terms[role], mref), b.f_amt_box)
    ws.write(18, 1, "Total", b.f_txt_tot)
    for c in list(range(2, 6)) + list(range(7, 11)) + list(range(12, 16)):
        col = xl_col_to_name(c)
        ws.write_formula(18, c, f"=SUM({col}7:{col}18)", b.f_amt_tot)
    ws.write(19, 1, "Check: not in any month (should be 0)", b.f_note)
    for j, role in enumerate(roles):
        for c0, expr in ((2, render_terms(book_terms[role], None)), (7, f3b(role, None)),
                         (12, render_terms(r1_terms[role], None))):
            col = xl_col_to_name(c0 + j)
            ws.write_formula(19, c0 + j, f"={expr[1:]}-{col}19", b.f_check)
    ws.conditional_format("C20:P20", {"type": "cell", "criteria": "not between",
                                      "minimum": -1, "maximum": 1, "format": b.f_red})

    ws.write("C22", "Difference in Tally & 3B", b.f_bold)
    ws.write("H22", "Difference in Tally & R1", b.f_bold)
    ws.write("M22", "Difference in 3B & R1", b.f_bold)
    ws.write("B23", "Month", b.f_hdr2)
    for c0 in (2, 7, 12):
        ws.write_row(22, c0, heads, b.f_hdr2)
    for i, m in enumerate(FY_MONTHS):
        r = 23 + i
        src = 7 + i  # excel row of the month in the top block
        ws.write(r, 1, m, b.f_txt_box)
        for j in range(4):
            a, h, mm = (xl_col_to_name(2 + j), xl_col_to_name(7 + j), xl_col_to_name(12 + j))
            ws.write_formula(r, 2 + j, f"=+{a}{src}-{h}{src}", b.f_amt_box)
            ws.write_formula(r, 7 + j, f"=+{a}{src}-{mm}{src}", b.f_amt_box)
            ws.write_formula(r, 12 + j, f"=+{h}{src}-{mm}{src}", b.f_amt_box)
    ws.write(35, 1, "Total", b.f_txt_tot)
    for c in list(range(2, 6)) + list(range(7, 11)) + list(range(12, 16)):
        col = xl_col_to_name(c)
        ws.write_formula(35, c, f"=SUM({col}24:{col}35)", b.f_amt_tot)
    ws.conditional_format("C24:P36", {"type": "cell", "criteria": "not between",
                                      "minimum": -1, "maximum": 1, "format": b.f_red})

    # GSTR-1 taxable value by section (explains the GSTR-1 column).
    row = 38
    ws.write(row, 1, "GSTR-1 taxable value by section (notes: debit +, credit -)", b.f_bold)
    secs = [s for s in ("B2B", "B2CL", "B2CS", "EXP", "CDNR", "CDNUR") if s in section_tv]
    ws.write(row + 1, 1, "Month", b.f_hdr2)
    ws.write_row(row + 1, 2, secs + ["Total"], b.f_hdr2)
    for i, m in enumerate(FY_MONTHS):
        r = row + 2 + i
        ws.write(r, 1, m, b.f_txt_box)
        for j, s in enumerate(secs):
            ws.write_formula(r, 2 + j, render_terms(section_tv[s], f"$B{r + 1}"), b.f_amt_box)
        if secs:
            ws.write_formula(r, 2 + len(secs),
                             f"=SUM(C{r + 1}:{xl_col_to_name(1 + len(secs))}{r + 1})",
                             b.f_amt_tot)
    r = row + 14
    ws.write(r, 1, "Total", b.f_txt_tot)
    for j in range(len(secs) + (1 if secs else 0)):
        col = xl_col_to_name(2 + j)
        ws.write_formula(r, 2 + j, f"=SUM({col}{row + 3}:{col}{r})", b.f_amt_tot)
    row = r + 3
    write_status_block(b, ws, row, reco_name, OUT_STATUS, "Books", "GSTR-1")
    ws.freeze_panes(6, 2)

    notes += [
        "Tally column = Sales Register + Sign_DN x Debit Note + Sign_CN x Credit Note.",
        "GSTR-3B column = Table 3.1(a) + 3.1(b) (CGST/SGST from 3.1(a)).",
        "GSTR-1 column = B2B + B2CL + B2CS + EXP + CDNR + CDNUR (debit notes +, credit -). "
        "Advances (Tables 11A/11B) are carried but not added.",
        "Invoice reco: Books rows with GSTIN vs GSTR-1 B2B and CDNR, by GSTIN + invoice no.",
    ]
    write_settings(b, client, fy, "output",
                   [s for s in (gstr1, gstr3b, sales) if s], notes)
    b.close()
    return b.warnings


# --------------------------------------------------------------------------------------
# INPUT workbook
# --------------------------------------------------------------------------------------
def build_input(target, client: str, fy: str, gstr2b: SourceFile | None,
                gstr3b: SourceFile | None, purchase: SourceFile | None) -> list[str]:
    b = Builder(target)
    notes: list[str] = []
    summary = b.wb.add_worksheet(b.sheet_name("Input Summary"))
    reco_ws = b.wb.add_worksheet(b.sheet_name("Reco File"))

    ms = read_3b_sheet(gstr3b, "input") if gstr3b else None
    if gstr3b and ms is None:
        b.warnings.append("GSTR-3B file: EligibleITC (Table 4) sheet not found.")
    sheet3b = b.add_matrix_sheet(ms, "GSTR-3B ITC") if ms else None

    rets: list[TableInfo] = []
    b2b_terms: dict[str, list[Term]] = {r: [] for r in ("tv", "igst", "cgst", "sgst")}
    excl_terms: dict[str, list[Term]] = {}
    rej_terms: dict[str, list[Term]] = {r: [] for r in ("igst", "cgst", "sgst")}
    if gstr2b:
        sheets, skipped = read_tabular_workbook(gstr2b)
        notes += [f"GSTR-2B file: sheet '{s}' has no recognisable header - not used."
                  for s in skipped]
        for sd in sheets:
            sec = sd.name.replace(" ", "").upper()
            rejected = "REJECT" in sec
            note = sec.startswith("CDNR")
            doc_level = sec in ("B2B", "CDNR")
            cols = portal_cols(sd.headers, note=note)
            helpers = portal_helpers(cols, "N" if note else "I", flags=doc_level)
            if not doc_level:
                helpers = [h for h in helpers if h[0] not in ("Key", "Flag")]
                cols.pop("key", None)
                cols.pop("flag", None)
            t = b.add_data_sheet(sd, f"GSTR-2B {sd.name}", f"B2_{sd.name}", helpers, cols)
            if doc_level:
                rets.append(t)
                elig = [("flag", '""')]
                for k in b2b_terms:
                    b2b_terms[k] += (note_terms(t, k, elig) if note else [Term(t, k, "+", elig)])
                for fl in ("RCM", "ITC not available"):
                    for k in ("igst", "cgst", "sgst"):
                        crit = [("flag", f'"{fl}"')]
                        excl_terms.setdefault(f"{fl}|{k}", []).extend(
                            note_terms(t, k, crit) if note else [Term(t, k, "+", crit)])
            elif rejected and sec.startswith(("B2B", "CDNR")):
                for k in rej_terms:
                    rej_terms[k] += note_terms(t, k) if note else [Term(t, k)]

    books: list[TableInfo] = []
    book_terms: dict[str, list[Term]] = {r: [] for r in ("tv", "igst", "cgst", "sgst")}
    if purchase:
        sheets, skipped = read_tabular_workbook(purchase)
        notes += [f"Purchase file: sheet '{s}' has no recognisable header - not used."
                  for s in skipped]
        for sd in sheets:
            role = tally_role(sd.name)
            cols = tally_cols(sd.headers)
            if not cols["gstin"]:
                b.warnings.append(f"Purchase file sheet '{sd.name}': no GSTIN column - "
                                  "invoice-level reco not possible for this sheet.")
            helpers = tally_helpers(cols, "I" if role in ("MAIN", "JR") else "N")
            t = b.add_data_sheet(sd, sd.name, f"P_{sd.name}", helpers, cols)
            books.append(t)
            sign = {"MAIN": "+", "DN": "+Sign_DN*", "CN": "+Sign_CN*", "JR": "+Sign_JR*"}[role]
            for k in book_terms:
                book_terms[k].append(Term(t, k, sign))

    # ---- 3B rows ------------------------------------------------------------------------
    hdr3b = ms.month_header_row() if ms else None

    def r3b(section: str, line: str, after: str | None = None) -> int | None:
        if not ms:
            return None
        r = ms.line_in_section(section, line, after)
        if r is None:
            b.warnings.append(f"GSTR-3B: row '{line}' under '{section}' not found.")
        return r

    rows3b = {"igst": r3b("(5) All other ITC", "IGST"),
              "cgst": r3b("(5) All other ITC", "CGST"),
              "sgst": r3b("(5) All other ITC", "SGST")}
    other3b = [
        ("4A(1) Import of goods", r3b("(1) Import of goods", "Total ITC")),
        ("4A(2) Import of services", r3b("(2) Import of services", "Total ITC")),
        ("4A(3) Reverse charge", r3b("(3) Inward supplies liable", "Total ITC")),
        ("4A(4) ISD", r3b("(4) Inward supplies from ISD", "Total ITC")),
        ("4B(1) Reversed - Rules 38/42/43 & 17(5)", r3b("(1) As per rules", "Total ITC")),
        ("4B(2) Reversed - Others", r3b("(2) Others", "Total ITC", after="4(B)")),
        ("4(C) Net ITC available", r3b("(C) Net ITC", "Total ITC")),
        ("4D(1) Reclaimed", r3b("(1) ITC reclaimed", "Total ITC")),
        ("4D(2) Ineligible 16(4) / POS", r3b("(2) Ineligible", "Total ITC")),
    ]

    def f3b_row(r: int | None, mref: str | None) -> str:
        if sheet3b is None or hdr3b is None or r is None:
            return "=0"
        q = f"'{sheet3b}'"
        if mref is None:
            return f"=SUM({q}!$B${r + 1}:$M${r + 1})"
        return f"=SUMIF({q}!${hdr3b + 1}:${hdr3b + 1},{mref},{q}!${r + 1}:${r + 1})"

    write_reco(b, reco_ws, books, rets, "input", client, fy)
    reco_name = reco_ws.get_name()

    # ---- Summary ------------------------------------------------------------------------
    ws = summary
    ws.set_column(0, 0, 2)
    ws.set_column(1, 1, 34)
    ws.set_column(2, 16, 14)
    ws.set_column(6, 6, 3)
    ws.set_column(10, 10, 3)
    ws.write("B1", client, b.f_title)
    ws.write("B2", "GST Reco", b.f_bold)
    ws.write("C2", f"FY {fy}", b.f_bold)
    ws.write("B4", "Input", b.f_bold)
    ws.write("C4", "As per Tally", b.f_bold)
    ws.write("H4", "As per GSTR 3B", b.f_bold)
    ws.write("L4", "As per GSTR 2B", b.f_bold)
    ws.write("B5", "Month", b.f_hdr2)
    ws.write_row(4, 2, ["Taxable", "IGST", "CGST", "SGST"], b.f_hdr2)
    ws.write_row(4, 7, ["IGST", "CGST", "SGST"], b.f_hdr2)
    ws.write_row(4, 11, ["Taxable", "IGST", "CGST", "SGST"], b.f_hdr2)
    roles = ["tv", "igst", "cgst", "sgst"]
    for i, m in enumerate(FY_MONTHS):
        r = 5 + i
        ws.write(r, 1, m, b.f_txt_box)
        mref = f"$B{r + 1}"
        for j, role in enumerate(roles):
            ws.write_formula(r, 2 + j, render_terms(book_terms[role], mref), b.f_amt_box)
            ws.write_formula(r, 11 + j, render_terms(b2b_terms[role], mref), b.f_amt_box)
        for j, role in enumerate(roles[1:]):
            ws.write_formula(r, 7 + j, f3b_row(rows3b[role], mref), b.f_amt_box)
    cols_used = list(range(2, 6)) + list(range(7, 10)) + list(range(11, 15))
    ws.write(17, 1, "Total", b.f_txt_tot)
    for c in cols_used:
        col = xl_col_to_name(c)
        ws.write_formula(17, c, f"=SUM({col}6:{col}17)", b.f_amt_tot)
    ws.write(18, 1, "Check: not in any month (should be 0)", b.f_note)
    for j, role in enumerate(roles):
        for c0, expr in ((2, render_terms(book_terms[role], None)),
                         (11, render_terms(b2b_terms[role], None))):
            col = xl_col_to_name(c0 + j)
            ws.write_formula(18, c0 + j, f"={expr[1:]}-{col}18", b.f_check)
    for j, role in enumerate(roles[1:]):
        col = xl_col_to_name(7 + j)
        ws.write_formula(18, 7 + j, f"={f3b_row(rows3b[role], None)[1:]}-{col}18", b.f_check)
    ws.conditional_format("C19:O19", {"type": "cell", "criteria": "not between",
                                      "minimum": -1, "maximum": 1, "format": b.f_red})

    ws.write("C21", "Difference in Tally & 2B", b.f_bold)
    ws.write("H21", "Difference in Tally & 3B", b.f_bold)
    ws.write("L21", "Difference in 3B & 2B", b.f_bold)
    ws.write("B22", "Month", b.f_hdr2)
    ws.write_row(21, 2, ["Taxable", "IGST", "CGST", "SGST"], b.f_hdr2)
    ws.write_row(21, 7, ["IGST", "CGST", "SGST"], b.f_hdr2)
    ws.write_row(21, 11, ["IGST", "CGST", "SGST"], b.f_hdr2)
    for i, m in enumerate(FY_MONTHS):
        r = 22 + i
        s = 6 + i
        ws.write(r, 1, m, b.f_txt_box)
        for j, (a, l) in enumerate(zip("CDEF", "LMNO")):
            ws.write_formula(r, 2 + j, f"=+{a}{s}-{l}{s}", b.f_amt_box)
        for j, (a, h) in enumerate(zip("DEF", "HIJ")):
            ws.write_formula(r, 7 + j, f"=+{a}{s}-{h}{s}", b.f_amt_box)
        for j, (h, l) in enumerate(zip("HIJ", "MNO")):
            ws.write_formula(r, 11 + j, f"=+{h}{s}-{l}{s}", b.f_amt_box)
    ws.write(34, 1, "Total", b.f_txt_tot)
    for c in list(range(2, 6)) + list(range(7, 10)) + list(range(11, 14)):
        col = xl_col_to_name(c)
        ws.write_formula(34, c, f"=SUM({col}23:{col}34)", b.f_amt_tot)
    ws.conditional_format("C23:N35", {"type": "cell", "criteria": "not between",
                                      "minimum": -1, "maximum": 1, "format": b.f_red})

    # GSTR-2B items kept out of the ITC column.
    row = 37
    ws.write(row, 1, "GSTR-2B items NOT included in 'As per GSTR 2B' above", b.f_bold)
    blocks = [("Reverse charge (RCM)", "RCM"), ("ITC not available", "ITC not available")]
    c0s = [2, 7, 11]
    for (label, _), c0 in zip(blocks + [("Rejected in IMS", None)], c0s):
        ws.write(row + 1, c0, label, b.f_bold)
        ws.write_row(row + 2, c0, ["IGST", "CGST", "SGST"], b.f_hdr2)
    ws.write(row + 2, 1, "Month", b.f_hdr2)
    for i, m in enumerate(FY_MONTHS + [None]):
        r = row + 3 + i
        if m is None:
            ws.write(r, 1, "Total", b.f_txt_tot)
            for c0 in c0s:
                for j in range(3):
                    col = xl_col_to_name(c0 + j)
                    ws.write_formula(r, c0 + j, f"=SUM({col}{row + 4}:{col}{r})", b.f_amt_tot)
            break
        ws.write(r, 1, m, b.f_txt_box)
        mref = f"$B{r + 1}"
        for (label, fl), c0 in zip(blocks, c0s):
            for j, k in enumerate(("igst", "cgst", "sgst")):
                ws.write_formula(r, c0 + j, render_terms(excl_terms.get(f"{fl}|{k}", []), mref),
                                 b.f_amt_box)
        for j, k in enumerate(("igst", "cgst", "sgst")):
            ws.write_formula(r, 11 + j, render_terms(rej_terms[k], mref), b.f_amt_box)

    # Other GSTR-3B Table 4 rows (information).
    row = row + 18
    ws.write(row, 1, "Other GSTR-3B Table 4 rows (Total ITC, month-wise)", b.f_bold)
    ws.write(row + 1, 1, "Row", b.f_hdr2)
    ws.write_row(row + 1, 2, FY_MONTHS + ["Total"], b.f_hdr2)
    for i, (label, r3) in enumerate(other3b):
        r = row + 2 + i
        ws.write(r, 1, label, b.f_txt_box)
        for j, m in enumerate(FY_MONTHS):
            ws.write_formula(r, 2 + j, f3b_row(r3, f'"{m}"'), b.f_amt_box)
        ws.write_formula(r, 14, f"=SUM(C{r + 1}:N{r + 1})", b.f_amt_tot)
    row = row + 2 + len(other3b) + 2
    write_status_block(b, ws, row, reco_name, IN_STATUS, "Tally", "GSTR-2B")
    ws.freeze_panes(5, 2)

    notes += [
        "Tally column = Purchase Register + Sign_DN x Debit Note + Sign_CN x Credit Note "
        "+ Sign_JR x Journal Register (signs on this sheet).",
        "GSTR-3B column = Table 4A(5) 'All other ITC'. Other Table 4 rows are listed separately.",
        "GSTR-2B column = B2B + CDNR (debit notes +, credit notes -) excluding reverse-charge "
        "rows and rows with ITC Availability = No; those are shown in a separate block.",
        "Invoice reco: Tally rows with GSTIN vs GSTR-2B B2B and CDNR, by GSTIN + supplier "
        "invoice / note no (Tally Voucher No.).",
    ]
    write_settings(b, client, fy, "input", [s for s in (gstr2b, gstr3b, purchase) if s], notes)
    b.close()
    return b.warnings


# --------------------------------------------------------------------------------------
# Defaults (client / FY) and file naming
# --------------------------------------------------------------------------------------
def guess_client_fy(sales: SourceFile | None, purchase: SourceFile | None,
                    gstr3b: SourceFile | None) -> tuple[str, str]:
    client, fy = "", ""
    for src in (sales, purchase):
        if src and not client:
            wb = openpyxl.load_workbook(io.BytesIO(src.data), read_only=True, data_only=True)
            ws = wb[wb.sheetnames[0]]
            rows = list(ws.iter_rows(max_row=6, values_only=True))
            if rows and rows[0] and rows[0][0]:
                client = str(rows[0][0]).strip()
            for r in rows:
                txt = " ".join(str(v) for v in r if v)
                m = re.search(r"\d{1,2}-[A-Za-z]{3}-(\d{2,4})\s+to\s+\d{1,2}-[A-Za-z]{3}-(\d{2,4})",
                              txt)
                if m and not fy:
                    y1 = int(m.group(1)) % 100
                    fy = f"20{y1:02d}-{(y1 + 1) % 100:02d}"
    if gstr3b and not fy:
        wb = openpyxl.load_workbook(io.BytesIO(gstr3b.data), read_only=True, data_only=True)
        for name in wb.sheetnames:
            for r in wb[name].iter_rows(max_row=3, values_only=True):
                txt = " ".join(str(v) for v in r if v)
                m = re.search(r"(20\d{2})-(20)?(\d{2})", txt)
                if m:
                    fy = f"{m.group(1)}-{m.group(3)}"
                    break
            if fy:
                break
    return client or "Client", fy or "2025-26"


def out_names(client: str, fy: str) -> tuple[str, str]:
    m = re.match(r"(\d{4})-(\d{2,4})", fy)
    tag = f"FY{int(m.group(1)) + 1}" if m else f"FY{fy}"
    safe = re.sub(r'[<>:"/\\|?*]', "", client).strip() or "Client"
    return (f"0. GST Reco Output {tag} - {safe}.xlsx", f"0. GST Reco Input {tag} - {safe}.xlsx")


# --------------------------------------------------------------------------------------
# File-type detection and one-call generation (used by the desktop app)
# --------------------------------------------------------------------------------------
FILE_KINDS = {
    "gstr1": "GSTR-1 (Tax Power)",
    "sales": "Sales register (Tally)",
    "gstr2b": "GSTR-2B (Tax Power)",
    "purchase": "Purchase register (Tally)",
    "gstr3b": "GSTR-3B (Tax Power)",
}


def classify_workbook(data: bytes) -> str | None:
    """Guess which of the five inputs a workbook is, from its sheet names and titles."""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception:  # noqa: BLE001 - not a readable workbook
        return None
    names = [n.replace(" ", "").lower() for n in wb.sheetnames]
    if "taxablesupplies" in names or "eligibleitc" in names:
        return "gstr3b"
    first_text = ""
    for r in wb[wb.sheetnames[0]].iter_rows(max_row=6, values_only=True):
        first_text += " ".join(str(v) for v in r if v is not None) + " "
    first_text = first_text.lower()
    if "gstr-2b" in first_text or any(n in names for n in ("impg", "b2b(rejected)", "isd")):
        return "gstr2b"
    if "gstr-1" in first_text or any(n in names for n in ("b2cs", "hsn", "doc", "advrec")):
        return "gstr1"
    if "annual gstr-3b" in first_text:
        return "gstr3b"
    if any("purchase" in n or "journal" in n for n in names):
        return "purchase"
    if any("sales" in n for n in names):
        return "sales"
    return None


@dataclass
class GenResult:
    label: str
    path: Path
    warnings: list[str]


def generate(outdir: Path, client: str, fy: str, gstr1: SourceFile | None,
             gstr3b: SourceFile | None, sales: SourceFile | None,
             gstr2b: SourceFile | None, purchase: SourceFile | None) -> list[GenResult]:
    """Build whichever workbooks the given files allow. Raises PermissionError with a
    plain message when the target file is open in Excel."""
    out_name, in_name = out_names(client, fy)
    outdir.mkdir(parents=True, exist_ok=True)
    results = []
    jobs = []
    if gstr1 or sales:
        jobs.append(("Output reco", out_name,
                     lambda buf: build_output(buf, client, fy, gstr1, gstr3b, sales)))
    if gstr2b or purchase:
        jobs.append(("Input reco", in_name,
                     lambda buf: build_input(buf, client, fy, gstr2b, gstr3b, purchase)))
    for label, name, fn in jobs:
        buf = io.BytesIO()
        warns = fn(buf)
        path = outdir / name
        try:
            path.write_bytes(buf.getvalue())
        except PermissionError as e:
            raise PermissionError(f"'{name}' is open in Excel. Close it and try again.") from e
        results.append(GenResult(label, path, warns))
    return results


# --------------------------------------------------------------------------------------
# Streamlit screen
# --------------------------------------------------------------------------------------
def preview_rows(src: SourceFile) -> list[dict[str, Any]]:
    """Rows read and totals per sheet, so staff can tie back to the source."""
    out = []
    sheets, _ = read_tabular_workbook(src)
    for sd in sheets:
        tv = find_col(sd.headers, "Taxable Value", "Taxable")
        tax = [find_col(sd.headers, h, exact_only=False) for h in ("IGST", "CGST", "SGST")]

        def tot(h):
            if not h:
                return 0.0
            i = sd.headers.index(h)
            return round(sum(v for r in sd.rows if isinstance((v := r[i]), (int, float))), 2)
        out.append({"File": src.label, "Sheet": sd.name, "Rows": len(sd.rows),
                    "Taxable": tot(tv), "IGST": tot(tax[0]), "CGST": tot(tax[1]),
                    "SGST": tot(tax[2])})
    return out


def run_streamlit() -> None:
    import streamlit as st

    st.set_page_config(page_title="GST Reco Tool", layout="wide")
    st.title("GST Reco Tool")
    st.caption("Upload the Tax Power and Tally exports, then click Generate. "
               "Both workbooks are formula-linked (Excel 365).")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Output (sales)")
        f_r1 = st.file_uploader("GSTR-1 Section-wise Summary (Tax Power)", type=["xlsx"],
                                key="r1")
        f_sales = st.file_uploader("Sales / DN / CN Register (Tally)", type=["xlsx"],
                                   key="sales")
    with c2:
        st.subheader("Input (purchases)")
        f_2b = st.file_uploader("GSTR-2B Section-wise Summary (Tax Power)", type=["xlsx"],
                                key="2b")
        f_pur = st.file_uploader("Purchase / DN / CN / Journal Register (Tally)",
                                 type=["xlsx"], key="pur")
    f_3b = st.file_uploader("GSTR-3B Month-wise Annual Summary (Tax Power) - used for both",
                            type=["xlsx"], key="3b")

    def wrap(f, label):
        return SourceFile(label, f.name, f.getvalue()) if f else None

    r1, sales, b2, pur, g3b = (wrap(f_r1, "GSTR-1"), wrap(f_sales, "Sales register"),
                               wrap(f_2b, "GSTR-2B"), wrap(f_pur, "Purchase register"),
                               wrap(f_3b, "GSTR-3B"))
    if not any((r1, sales, b2, pur, g3b)):
        st.info("Upload at least one file to begin.")
        return

    g_client, g_fy = guess_client_fy(sales, pur, g3b)
    c3, c4 = st.columns(2)
    client = c3.text_input("Client name", g_client)
    fy = c4.text_input("Financial year (e.g. 2025-26)", g_fy)

    with st.expander("Check what was read (rows and totals per sheet)", expanded=True):
        rows = []
        for s in (r1, sales, b2, pur):
            if s:
                try:
                    rows += preview_rows(s)
                except Exception as e:  # noqa: BLE001 - show plain message to staff
                    st.error(f"Could not read {s.label} file '{s.name}': {e}")
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)

    if st.button("Generate reco workbooks", type="primary"):
        out_name, in_name = out_names(client, fy)
        try:
            if r1 or sales or g3b:
                buf = io.BytesIO()
                w = build_output(buf, client, fy, r1, g3b, sales)
                st.session_state["out"] = (out_name, buf.getvalue(), w)
            if b2 or pur or g3b:
                buf = io.BytesIO()
                w = build_input(buf, client, fy, b2, g3b, pur)
                st.session_state["in"] = (in_name, buf.getvalue(), w)
        except Exception as e:  # noqa: BLE001
            st.error(f"Something went wrong while building the workbooks: {e}")

    for k, label in (("out", "Download Output reco"), ("in", "Download Input reco")):
        if k in st.session_state:
            name, data, warns = st.session_state[k]
            st.download_button(f"{label}: {name}", data, file_name=name,
                               mime="application/vnd.openxmlformats-officedocument."
                                    "spreadsheetml.sheet")
            for w in warns:
                st.warning(w)


# --------------------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------------------
def _src(path: str | None, label: str) -> SourceFile | None:
    if not path:
        return None
    p = Path(path)
    return SourceFile(label, p.name, p.read_bytes())


def run_cli(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="GST Reco Tool (command-line mode)")
    ap.add_argument("--cli", action="store_true")
    ap.add_argument("--gstr1")
    ap.add_argument("--gstr3b")
    ap.add_argument("--sales")
    ap.add_argument("--gstr2b")
    ap.add_argument("--purchase")
    ap.add_argument("--client")
    ap.add_argument("--fy")
    ap.add_argument("--outdir", default=".")
    a = ap.parse_args(argv)
    r1, g3b, sales = _src(a.gstr1, "GSTR-1"), _src(a.gstr3b, "GSTR-3B"), _src(a.sales,
                                                                              "Sales register")
    b2, pur = _src(a.gstr2b, "GSTR-2B"), _src(a.purchase, "Purchase register")
    g_client, g_fy = guess_client_fy(sales, pur, g3b)
    client, fy = a.client or g_client, a.fy or g_fy
    out_name, in_name = out_names(client, fy)
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    if r1 or sales or g3b:
        w = build_output(str(outdir / out_name), client, fy, r1, g3b, sales)
        print(f"Written {outdir / out_name}")
        for x in w:
            print("  warning:", x)
    if b2 or pur or g3b:
        w = build_input(str(outdir / in_name), client, fy, b2, g3b, pur)
        print(f"Written {outdir / in_name}")
        for x in w:
            print("  warning:", x)
    return 0


def _in_streamlit() -> bool:
    try:
        from streamlit import runtime
        return runtime.exists()
    except Exception:  # noqa: BLE001
        return False


if __name__ == "__main__":
    if _in_streamlit():
        run_streamlit()
    elif "--cli" in sys.argv:
        sys.exit(run_cli(sys.argv[1:]))
    else:
        import subprocess
        try:
            import streamlit  # noqa: F401
        except ImportError:
            print("Streamlit is not installed. Run:  pip install streamlit openpyxl xlsxwriter")
            sys.exit(1)
        sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", __file__]))
