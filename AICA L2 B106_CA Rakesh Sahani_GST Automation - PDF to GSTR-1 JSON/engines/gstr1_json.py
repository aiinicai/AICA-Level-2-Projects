#!/usr/bin/env python3
"""
gstr1_json.py — GSTR-1 summary workbook -> portal JSON + a checking workbook.

Reads SHEET 1 of the summary produced in Step 1 by gst_sales_summary.py
(Sr.no, Date, Invoice no, GST No, Party name, Taxable value, IGST, CGST, SGST,
Invoice value, HSN, Remark) and writes:

  * a JSON file holding the b2b section, for
    Returns Dashboard -> GSTR-1 -> Prepare Offline -> Upload
  * a workbook with the checks, the Table 12 HSN working and the Table 13
    document working, because neither of those travels in the JSON

WHAT IT WILL NOT DO
-------------------
It refuses to build the JSON when something is wrong that only a human can
settle — an invalid GSTIN, an invoice number the portal will reject, or a
B2B row carrying no tax. Those are listed instead. Everything softer is a
warning: the file still gets built, and the warning goes in the workbook.

Runs entirely offline.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ------------------------------------------------------------------ constants

# The rates the portal accepts. A computed rate is snapped to the nearest of
# these, and anything that doesn't land on one is reported rather than guessed.
VALID_RATES = [0, 0.1, 0.25, 1, 1.5, 3, 5, 6, 7.5, 12, 18, 28]

CODEPOINTS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z][A-Z0-9]$")

# Rule 46: up to 16 characters, letters, digits, slash and hyphen only.
INVOICE_NO_RE = re.compile(r"^[A-Za-z0-9/\-]{1,16}$")

WANTED = {
    "sr": ("sr.no", "sr no", "srno", "sr"),
    "date": ("invoice date", "date"),
    "gstin": ("gst no", "gstin", "gst number", "gstin of recipient"),
    "invno": ("invoice no", "invoice number", "inv no"),
    "party": ("party name", "party", "name of party", "recipient"),
    "taxable": ("taxable value", "taxable"),
    "igst": ("igst",),
    "cgst": ("cgst",),
    "sgst": ("sgst",),
    "value": ("invoice value", "total invoice value"),
    "remark": ("remark", "remarks"),
    "hsn": ("hsn", "hsn/sac", "sac", "hsn code"),
    "other": ("other remarks",),
}

THIN = Side(style="thin")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
MONEY = "#,##0.00"


# -------------------------------------------------------------------- helpers

def gstin_is_valid(gstin) -> bool:
    """Verify the 15th check character of a GSTIN."""
    gstin = str(gstin or "").strip().upper()
    if len(gstin) != 15 or not GSTIN_RE.match(gstin):
        return False
    factor, total, mod = 2, 0, len(CODEPOINTS)
    for ch in reversed(gstin[:14]):
        if ch not in CODEPOINTS:
            return False
        val = factor * CODEPOINTS.index(ch)
        factor = 1 if factor == 2 else 2
        total += (val // mod) + (val % mod)
    return CODEPOINTS[(mod - (total % mod)) % mod] == gstin[14]


def num(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").replace("\u20b9", "").strip()
    if text in {"", "-", "--"}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if hasattr(value, "year") and hasattr(value, "month"):
        return value
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def snap_rate(computed):
    """Nearest permitted rate, or None if it isn't close to any of them."""
    if computed is None:
        return None
    best = min(VALID_RATES, key=lambda r: abs(r - computed))
    return best if abs(best - computed) <= 0.15 else None


def r2(value) -> float:
    return round(float(value) + 1e-9, 2)


CANCEL_WORDS = {"CANCEL", "CANCELLED", "CANCELED"}
BLANK_WORDS = {"", "NA", "N/A", "-", "--", "NONE"}


def is_cancelled(rec) -> bool:
    """
    A cancelled invoice, kept in the summary so Table 13 can count it.

    Recognised either by the word Cancel appearing where the GSTIN or the
    remark should be, or by the row being an empty placeholder — no GSTIN,
    no party and no value. Keeping these rows is the right thing to do:
    Table 13 needs the cancelled count, and deleting them loses it.
    """
    gstin = rec["gstin"].upper().strip()
    remark = rec["remark"].upper().strip()
    if gstin in CANCEL_WORDS or remark in CANCEL_WORDS:
        return True
    return (rec["taxable"] == 0 and not rec["party"]
            and gstin in BLANK_WORDS)


# --------------------------------------------------------------------- reading

def find_header(ws):
    """Locate the header row and map our field names onto its columns."""
    for row in range(1, min(ws.max_row, 30) + 1):
        labels = {}
        for col in range(1, ws.max_column + 1):
            text = str(ws.cell(row=row, column=col).value or "").strip().lower()
            text = re.sub(r"\s+", " ", text).rstrip(" :.-")
            if not text:
                continue
            for key, options in WANTED.items():
                if key not in labels and text in options:
                    labels[key] = col
        if {"date", "gstin", "invno", "taxable"} <= set(labels):
            return row, labels
    raise ValueError(
        "That doesn't look like a GST summary sheet — no header row with "
        "Invoice Date, GST No, Invoice No and Taxable Value was found.")


def read_summary(path, sheet_name=None):
    """
    MODIFIED for the PDF -> GSTR-1 pipeline:
    The input is the workbook written by gst_sales_summary.py (Step 1). Its
    invoice data is on SHEET 1, named "Summary". The original code skipped any
    sheet called "Summary", so it never read Step 1's output. Now:
      1. a sheet named explicitly is used;
      2. otherwise SHEET 1 is used;
      3. only if sheet 1 has no recognisable header does it fall back to the
         original search through the other sheets.
    """
    wb = load_workbook(path, data_only=True)
    if sheet_name and sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    else:
        ws = wb.worksheets[0]                       # sheet 1 of the Step 1 file
        try:
            find_header(ws)
        except ValueError:
            ws = next((wb[n] for n in wb.sheetnames
                       if n.strip().lower() not in {"verification log",
                                                    "index", "notes"}), wb.active)

    header_row, cols = find_header(ws)
    records = []
    for row in range(header_row + 1, ws.max_row + 1):
        def cell(key):
            col = cols.get(key)
            return ws.cell(row=row, column=col).value if col else None

        if not any(cell(k) is not None for k in ("invno", "gstin", "taxable")):
            continue
        invno = str(cell("invno") or "").strip()
        if not invno:
            continue

        taxable, igst = num(cell("taxable")), num(cell("igst"))
        cgst, sgst = num(cell("cgst")), num(cell("sgst"))
        # MODIFIED: Step 1 writes Invoice value as a formula (=F+G+H+I). A file
        # that has never been opened in Excel has no cached result, so the cell
        # reads as blank. In that case take taxable + tax, which is exactly
        # what the formula says.
        value = num(cell("value")) or r2(taxable + igst + cgst + sgst)
        records.append({
            "row": row,
            "sr": cell("sr"),
            "date": as_date(cell("date")),
            "raw_date": cell("date"),
            "gstin": str(cell("gstin") or "").strip().upper(),
            "invno": invno,
            "party": str(cell("party") or "").strip(),
            "taxable": taxable,
            "igst": igst,
            "cgst": cgst,
            "sgst": sgst,
            "value": value,
            "remark": str(cell("remark") or "").strip().upper(),
            "hsn": str(cell("hsn") or "").strip(),
        })

    if not records:
        raise ValueError("No invoice rows were found under the header.")
    return ws.title, records


# ------------------------------------------------------------------ validating

class Issue:
    def __init__(self, severity, invno, party, message):
        self.severity = severity      # "Error" stops the JSON; "Warning" doesn't
        self.invno = invno
        self.party = party
        self.message = message

    def as_row(self):
        return [self.severity, self.invno, self.party, self.message]


def build_records(records, supplier_gstin, period, default_rate, rcm_mode):
    """
    Work out the rate, place of supply and tax for every row, and collect
    every problem found. Returns (prepared, issues).
    """
    issues = []
    prepared = []
    supplier_state = supplier_gstin[:2]

    # Cancelled invoices are set aside, not validated and not sent. They are
    # still needed for the Table 13 count, so they are carried through.
    cancelled = []
    live = []
    for rec in records:
        if is_cancelled(rec):
            cancelled.append(rec)
            if rec["taxable"] > 0:
                issues.append(Issue(
                    "Warning", rec["invno"], rec["party"] or "(cancelled)",
                    f"marked cancelled but carries a taxable value of "
                    f"{rec['taxable']:,.2f} — it is being left out of the JSON"))
        else:
            live.append(rec)
    records = live

    seen = defaultdict(list)
    for rec in records:
        seen[rec["invno"].upper()].append(rec)
    for invno, group in seen.items():
        if len(group) > 1:
            issues.append(Issue(
                "Error", invno, group[0]["party"],
                f"appears {len(group)} times in the summary — the portal "
                f"rejects duplicate invoice numbers"))

    for rec in records:
        invno, party = rec["invno"], rec["party"]
        add = lambda sev, msg: issues.append(Issue(sev, invno, party, msg))

        # --- recipient GSTIN ------------------------------------------------
        if not rec["gstin"]:
            add("Error", "no GSTIN — a B2B invoice needs the recipient's GSTIN")
            continue
        if not gstin_is_valid(rec["gstin"]):
            add("Error", f"GSTIN {rec['gstin']} fails the check-digit test")
            continue
        if rec["gstin"] == supplier_gstin:
            add("Error", "recipient GSTIN is the same as the supplier's")

        # --- invoice number -------------------------------------------------
        if not INVOICE_NO_RE.match(invno):
            add("Error",
                f"invoice number '{invno}' is not acceptable — up to 16 "
                f"characters, only letters, digits, / and -")

        # --- date -----------------------------------------------------------
        if rec["date"] is None:
            add("Error", f"invoice date '{rec['raw_date']}' could not be read")
            continue
        if period and rec["date"].strftime("%m%Y") != period:
            add("Warning",
                f"dated {rec['date'].strftime('%d-%m-%Y')}, which is outside "
                f"the return period {period[:2]}-{period[2:]}")

        # --- amounts --------------------------------------------------------
        if rec["taxable"] <= 0:
            add("Error", "taxable value is zero or missing")
            continue

        is_rcm = rec["remark"] == "RCM"
        intra = rec["gstin"][:2] == supplier_state
        tax_present = rec["igst"] or rec["cgst"] or rec["sgst"]

        if rec["igst"] and (rec["cgst"] or rec["sgst"]):
            add("Error", "both IGST and CGST/SGST are charged on one invoice")
            continue
        if rec["cgst"] and rec["sgst"] and abs(rec["cgst"] - rec["sgst"]) > 0.02:
            add("Error", f"CGST {rec['cgst']:.2f} does not equal SGST "
                         f"{rec['sgst']:.2f}")
        if intra and rec["igst"]:
            add("Error", "IGST charged although supplier and recipient are in "
                         "the same state")
        if not intra and (rec["cgst"] or rec["sgst"]):
            add("Error", "CGST/SGST charged although supplier and recipient "
                         "are in different states")

        # --- the rate -------------------------------------------------------
        if tax_present:
            total_tax = rec["igst"] + rec["cgst"] + rec["sgst"]
            rate = snap_rate(total_tax / rec["taxable"] * 100)
            if rate is None:
                add("Error",
                    f"the tax works out to "
                    f"{total_tax / rec['taxable'] * 100:.2f}%, which is not a "
                    f"GST rate — check the figures")
                continue
        elif is_rcm:
            rate = default_rate
        else:
            # A B2B invoice with no tax at all. This is exactly the case where
            # an RCM invoice has been mislabelled, so it is not guessed at.
            add("Error",
                "marked B2B but carries no tax. If it is a reverse-charge "
                "invoice, change the Remark to RCM in the summary and run "
                "again. If it is genuinely exempt or nil-rated, it does not "
                "belong in the B2B table.")
            continue

        # --- tax to declare -------------------------------------------------
        if tax_present:
            iamt, camt, samt = rec["igst"], rec["cgst"], rec["sgst"]
        elif is_rcm and rcm_mode == "computed":
            if intra:
                iamt, camt, samt = 0.0, r2(rec["taxable"] * rate / 200), \
                                   r2(rec["taxable"] * rate / 200)
            else:
                iamt, camt, samt = r2(rec["taxable"] * rate / 100), 0.0, 0.0
        else:
            iamt = camt = samt = 0.0

        # --- invoice value sanity ------------------------------------------
        expected = r2(rec["taxable"] + rec["igst"] + rec["cgst"] + rec["sgst"])
        if rec["value"] and abs(rec["value"] - expected) > 1.0:
            add("Warning",
                f"invoice value {rec['value']:,.2f} does not equal taxable "
                f"plus tax ({expected:,.2f})")

        # --- HSN -------------------------------------------------------------
        if not rec["hsn"]:
            add("Warning", "no HSN/SAC — Table 12 is mandatory for B2B")

        prepared.append({**rec, "rate": rate, "intra": intra, "is_rcm": is_rcm,
                         "iamt": iamt, "camt": camt, "samt": samt,
                         "pos": rec["gstin"][:2]})

    return prepared, cancelled, issues


# ------------------------------------------------------------------- the JSON

def build_json(prepared, supplier_gstin, period, version, gross_turnover=None):
    by_ctin = defaultdict(list)
    for rec in prepared:
        by_ctin[rec["gstin"]].append(rec)

    b2b = []
    for ctin in sorted(by_ctin):
        invoices = []
        for rec in sorted(by_ctin[ctin], key=lambda r: (r["date"], r["invno"])):
            item = {"rt": rec["rate"], "txval": r2(rec["taxable"])}
            if rec["intra"]:
                item["camt"] = r2(rec["camt"])
                item["samt"] = r2(rec["samt"])
            else:
                item["iamt"] = r2(rec["iamt"])
            item["csamt"] = 0

            invoices.append({
                "inum": rec["invno"],
                "idt": rec["date"].strftime("%d-%m-%Y"),
                "val": r2(rec["value"] or (rec["taxable"] + rec["iamt"]
                                           + rec["camt"] + rec["samt"])),
                "pos": rec["pos"],
                "rchrg": "Y" if rec["is_rcm"] else "N",
                "inv_typ": "R",
                "itms": [{"num": 1, "itm_det": item}],
            })
        b2b.append({"ctin": ctin, "inv": invoices})

    payload = {
        "gstin": supplier_gstin,
        "fp": period,
        "version": version,
        "hash": "hash",
        "b2b": b2b,
    }
    if gross_turnover:
        payload["gt"] = r2(gross_turnover)
        payload["cur_gt"] = r2(gross_turnover)
    return payload


# ------------------------------------------------------- the checking workbook

def hsn_summary(prepared):
    """Table 12 working: one line per HSN and rate."""
    buckets = defaultdict(lambda: {"txval": 0.0, "iamt": 0.0, "camt": 0.0,
                                   "samt": 0.0, "count": 0})
    for rec in prepared:
        key = (rec["hsn"] or "(missing)", rec["rate"])
        bucket = buckets[key]
        bucket["txval"] += rec["taxable"]
        bucket["iamt"] += rec["iamt"]
        bucket["camt"] += rec["camt"]
        bucket["samt"] += rec["samt"]
        bucket["count"] += 1
    return sorted(buckets.items(), key=lambda kv: (str(kv[0][0]), kv[0][1]))


def document_series(prepared, cancelled=()):
    """Table 13 working: the invoice range issued, how many were issued and
    how many of those were cancelled."""
    cancelled_nos = {r["invno"] for r in cancelled}
    parsed = []
    for rec in list(prepared) + list(cancelled):
        match = re.match(r"^(\D*)(\d+)(.*)$", rec["invno"])
        if match:
            parsed.append((match.group(1), int(match.group(2)),
                           match.group(3), rec["invno"]))
    if not parsed:
        return None
    numbers = sorted(p[1] for p in parsed)
    present = set(numbers)
    gaps = [n for n in range(min(numbers), max(numbers) + 1)
            if n not in present]
    low = next(p[3] for p in parsed if p[1] == min(numbers))
    high = next(p[3] for p in parsed if p[1] == max(numbers))
    return {"from": low, "to": high, "issued": len(parsed), "gaps": gaps,
            "cancelled": len(cancelled_nos)}


def _head(ws, headers, row=1):
    fill = PatternFill("solid", fgColor="DDEBF7")
    for col, text in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=text)
        cell.font = Font(bold=True, size=10)
        cell.fill = fill
        cell.border = BORDER
        cell.alignment = Alignment(horizontal="center", wrap_text=True)


def _widths(ws, widths):
    for col, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width


def write_report(path, prepared, cancelled, issues, records, supplier_gstin,
                 period, hsn_digits):
    wb = Workbook()

    # ---- 1. checks --------------------------------------------------------
    ws = wb.active
    ws.title = "Checks"
    _head(ws, ["Severity", "Invoice no", "Party", "What to look at"])
    red = Font(color="B23B2E", bold=True, size=10)
    amber = Font(color="9C6500", size=10)
    row = 2
    for issue in sorted(issues, key=lambda i: (i.severity != "Error", i.invno)):
        for col, value in enumerate(issue.as_row(), 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = BORDER
            cell.font = red if issue.severity == "Error" else amber
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        row += 1
    if not issues:
        ws.cell(row=2, column=1, value="Nothing to flag.").font = Font(size=10)
    _widths(ws, [11, 15, 34, 78])
    ws.freeze_panes = "A2"

    # ---- 2. reconciliation ------------------------------------------------
    ws = wb.create_sheet("Reconciliation")
    _head(ws, ["Figure", "In the summary", "In the JSON", "Difference"])

    def total(rows, key):
        return sum(r[key] for r in rows)

    lines = [
        ("Invoice count", len(records), len(prepared)),
        ("Taxable value", total(records, "taxable"), total(prepared, "taxable")),
        ("IGST", total(records, "igst"), total(prepared, "iamt")),
        ("CGST", total(records, "cgst"), total(prepared, "camt")),
        ("SGST", total(records, "sgst"), total(prepared, "samt")),
        ("Invoice value", total(records, "value"), total(prepared, "value")),
    ]
    for i, (label, left, right) in enumerate(lines, start=2):
        ws.cell(row=i, column=1, value=label).font = Font(bold=True, size=10)
        for col, value in ((2, left), (3, right), (4, r2(right - left))):
            cell = ws.cell(row=i, column=col, value=r2(value))
            cell.number_format = "#,##0" if label == "Invoice count" else MONEY
            cell.border = BORDER

    row = len(lines) + 4
    ws.cell(row=row, column=1,
            value="Where the JSON differs from the summary").font = Font(
        bold=True, size=10)
    ws.cell(row=row + 1, column=1,
            value="Rows shown as Error on the Checks sheet are left out of "
                  "the JSON. Reverse-charge rows carry tax computed at the "
                  "applicable rate, which the summary shows as nil — so the "
                  "tax columns are expected to be higher here.").alignment = \
        Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=row + 1, start_column=1, end_row=row + 3,
                   end_column=4)

    row += 5
    ws.cell(row=row, column=1, value="Split by type").font = Font(bold=True,
                                                                 size=10)
    row += 1
    _head(ws, ["Type", "Invoices", "Taxable value", "Tax"], row=row)
    for label, sel in (("Regular (rchrg N)",
                        [r for r in prepared if not r["is_rcm"]]),
                       ("Reverse charge (rchrg Y)",
                        [r for r in prepared if r["is_rcm"]])):
        row += 1
        ws.cell(row=row, column=1, value=label).border = BORDER
        ws.cell(row=row, column=2, value=len(sel)).border = BORDER
        cell = ws.cell(row=row, column=3, value=r2(total(sel, "taxable")))
        cell.number_format, cell.border = MONEY, BORDER
        cell = ws.cell(row=row, column=4,
                       value=r2(total(sel, "iamt") + total(sel, "camt")
                                + total(sel, "samt")))
        cell.number_format, cell.border = MONEY, BORDER
    _widths(ws, [30, 20, 20, 20])

    # ---- 3. Table 12 ------------------------------------------------------
    ws = wb.create_sheet("Table 12 HSN (B2B)")
    ws.cell(row=1, column=1,
            value=f"Key these on the portal — Table 12, B2B tab. HSN must be "
                  f"picked from the dropdown; {hsn_digits} digits minimum for "
                  f"this client.").font = Font(bold=True, size=10)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)
    _head(ws, ["HSN / SAC", "UQC", "Total quantity", "Rate %", "Taxable value",
               "IGST", "CGST", "SGST"], row=3)
    row = 4
    for (hsn, rate), bucket in hsn_summary(prepared):
        values = [hsn, "NA", 0, rate, r2(bucket["txval"]), r2(bucket["iamt"]),
                  r2(bucket["camt"]), r2(bucket["samt"])]
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = BORDER
            if col >= 5:
                cell.number_format = MONEY
        row += 1
    ws.cell(row=row, column=1, value="Total").font = Font(bold=True, size=10)
    for col in range(5, 9):
        letter = get_column_letter(col)
        cell = ws.cell(row=row, column=col,
                       value=f"=SUM({letter}4:{letter}{row - 1})")
        cell.number_format, cell.font = MONEY, Font(bold=True, size=10)
    ws.cell(row=row + 2, column=1,
            value="UQC is NA and quantity 0 because these are services. "
                  "The taxable value here must agree with the B2B tables of "
                  "the return, or the portal raises a Table 12 mismatch."
            ).alignment = Alignment(wrap_text=True)
    ws.merge_cells(start_row=row + 2, start_column=1, end_row=row + 3,
                   end_column=8)
    _widths(ws, [14, 8, 14, 9, 16, 14, 14, 14])

    # ---- 4. Table 13 ------------------------------------------------------
    ws = wb.create_sheet("Table 13 Documents")
    ws.cell(row=1, column=1,
            value="Table 13 does not travel in the JSON — key it on the "
                  "portal.").font = Font(bold=True, size=10)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)
    _head(ws, ["Nature of document", "Sr. no. from", "Sr. no. to",
               "Total issued", "Cancelled"], row=3)
    series = document_series(prepared, cancelled)
    if series:
        for col, value in enumerate(
                ["Invoices for outward supply", series["from"], series["to"],
                 series["issued"], series["cancelled"]], 1):
            ws.cell(row=4, column=col, value=value).border = BORDER
        if series["gaps"]:
            note = ("Numbers still missing from the range: "
                    + ", ".join(str(n) for n in series["gaps"])
                    + ". Table 13 counts every document issued, so add these "
                      "to the summary — a cancelled invoice needs a row with "
                      "'Cancel' in the GST No column, not a deleted row.")
        elif series["cancelled"]:
            note = (f"The series is complete. {series['cancelled']} cancelled "
                    f"invoice(s) were found in the summary and counted above; "
                    f"they are not sent in the JSON.")
        else:
            note = "The series is complete and nothing was cancelled."
        ws.cell(row=6, column=1, value=note).alignment = Alignment(
            wrap_text=True, vertical="top")
        ws.merge_cells(start_row=6, start_column=1, end_row=8, end_column=5)
    _widths(ws, [34, 16, 16, 14, 12])

    wb.save(path)
    return path


# -------------------------------------------------------------------- the run

def generate(summary_path, out_json, out_report, supplier_gstin, period,
             sheet_name=None, default_rate=18.0, rcm_mode="computed",
             version="GST3.2.2", gross_turnover=None, hsn_digits=4):
    """
    Returns a dict of results. Raises ValueError with a readable message when
    the JSON cannot honestly be produced.
    """
    supplier_gstin = str(supplier_gstin).strip().upper()
    if not gstin_is_valid(supplier_gstin):
        raise ValueError(
            f"The supplier GSTIN '{supplier_gstin}' fails the check-digit "
            f"test. Check it before going any further.")

    sheet, records = read_summary(summary_path, sheet_name)
    prepared, cancelled, issues = build_records(
        records, supplier_gstin, period, default_rate, rcm_mode)

    errors = [i for i in issues if i.severity == "Error"]
    warnings = [i for i in issues if i.severity == "Warning"]

    live = [r for r in records if not is_cancelled(r)]
    write_report(out_report, prepared, cancelled, issues, live,
                 supplier_gstin, period, hsn_digits)

    payload = None
    if not errors and prepared:
        payload = build_json(prepared, supplier_gstin, period, version,
                             gross_turnover)
        with open(out_json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, separators=(",", ":"), ensure_ascii=False)

    return {
        "sheet": sheet,
        "read": len(records),
        "cancelled": len(cancelled),
        "included": len(prepared),
        "errors": errors,
        "warnings": warnings,
        "json_written": payload is not None,
        "recipients": len({r["gstin"] for r in prepared}),
        "taxable": sum(r["taxable"] for r in prepared),
        "tax": sum(r["iamt"] + r["camt"] + r["samt"] for r in prepared),
        "rcm_count": sum(1 for r in prepared if r["is_rcm"]),
    }
