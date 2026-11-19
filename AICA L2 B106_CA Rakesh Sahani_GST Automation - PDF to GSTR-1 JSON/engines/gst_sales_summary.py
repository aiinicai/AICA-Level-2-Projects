#!/usr/bin/env python3
"""
gst_sales_summary.py — Sales invoice PDFs -> GSTR-1 working summary
===================================================================

Reads every sales invoice PDF in a folder, pulls the invoice-level totals from
the tax summary table at the foot of each invoice, and writes one formatted
Excel summary plus an exceptions sheet.

RUNS ENTIRELY OFFLINE. No network calls. Nothing leaves this machine.

    pip install pdfplumber openpyxl
    python gst_sales_summary.py --folder ./invoices --out June-2026-Summary.xlsx

Useful flags:
    --period 06-2026     Flag invoices dated outside this month
    --debug              Print every field extracted from each PDF

DESIGN NOTE
-----------
Totals come from the "Tax Rate / Taxable Amt. / CGST Amt. / SGST Amt." table at
the bottom of the invoice, not from summing line items. That table already
carries the invoice-level totals, matching how the summary is prepared by hand.
The table's header row is parsed each time to work out which tax columns are
present, so intra-state (CGST/SGST) and inter-state (IGST) invoices both work
without a separate template.
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

try:
    import pdfplumber
except ImportError:
    sys.exit("Missing dependency. Run:  pip install pdfplumber openpyxl")

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

GSTIN_RE = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z][A-Z0-9])\b")
AMOUNT_RE = re.compile(r"^-?[\d,]+\.\d{2}$")
CODEPOINTS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana", "07": "Delhi",
    "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
    "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra",
    "29": "Karnataka", "30": "Goa", "31": "Lakshadweep", "32": "Kerala",
    "33": "Tamil Nadu", "34": "Puducherry", "35": "Andaman and Nicobar",
    "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
}


# ----------------------------------------------------------------- helpers

def to_amount(text):
    """'1,886.67' -> 1886.67 ; '-' or '' -> 0.0"""
    if text is None:
        return 0.0
    t = str(text).strip().replace(",", "").replace("`", "")
    if t in {"", "-", "--"}:
        return 0.0
    t = t.replace("(", "-").replace(")", "")
    try:
        return float(t)
    except ValueError:
        return 0.0


def gstin_is_valid(gstin):
    """Verify the 15th check character of a GSTIN."""
    if not gstin or len(gstin) != 15:
        return False
    if not GSTIN_RE.fullmatch(gstin):
        return False
    factor, total, mod = 2, 0, len(CODEPOINTS)
    for ch in reversed(gstin[:14]):
        if ch not in CODEPOINTS:
            return False
        val = factor * CODEPOINTS.index(ch)
        factor = 1 if factor == 2 else 2
        total += (val // mod) + (val % mod)
    return CODEPOINTS[(mod - (total % mod)) % mod] == gstin[14]


def parse_invoice_date(text):
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def rows_by_line(words, tolerance=3):
    """Group pdfplumber words into visual lines, each sorted left to right."""
    lines = defaultdict(list)
    for w in words:
        key = None
        for existing in lines:
            if abs(existing - w["top"]) <= tolerance:
                key = existing
                break
        lines[key if key is not None else round(w["top"], 1)].append(w)
    return [sorted(v, key=lambda x: x["x0"]) for _, v in sorted(lines.items())]


# ------------------------------------------------------- tax summary table

def extract_tax_table(lines):
    """
    Locate the 'Tax Rate | Taxable Amt. | CGST Amt. | SGST Amt. | Total Tax'
    block and return per-rate totals.

    The header may wrap across two or three visual lines, so header words are
    gathered from the 'Tax Rate' line plus the following two, then ordered by
    x-position to establish the column sequence. Data rows are matched to that
    sequence positionally, which handles IGST-only invoices unchanged.
    """
    header_idx = None
    for i, line in enumerate(lines):
        joined = " ".join(w["text"] for w in line)
        if re.match(r"^\s*Tax\s+Rate\b", joined):
            header_idx = i
            break
    if header_idx is None:
        return None

    header_words = []
    for line in lines[header_idx:header_idx + 3]:
        joined = " ".join(w["text"] for w in line)
        if re.match(r"^\s*\d+(\.\d+)?%", joined):
            break
        header_words.extend(line)
    header_words.sort(key=lambda w: w["x0"])

    columns, current = [], []
    for w in header_words:
        token = w["text"].rstrip(".")
        if token in {"Amt", "Tax", "Rate"} and current:
            current.append(token)
        else:
            if current:
                columns.append((" ".join(current), current_x))
            current, current_x = [token], w["x0"]
    if current:
        columns.append((" ".join(current), current_x))

    labels = []
    for name, _ in columns:
        up = name.upper()
        if "RATE" in up and "TAXABLE" not in up:
            labels.append("rate")
        elif "TAXABLE" in up:
            labels.append("taxable")
        elif "IGST" in up:
            labels.append("igst")
        elif "CGST" in up:
            labels.append("cgst")
        elif "SGST" in up or "UTGST" in up:
            labels.append("sgst")
        elif "CESS" in up:
            labels.append("cess")
        elif "TOTAL" in up:
            labels.append("total_tax")
        else:
            labels.append("other")

    result = {"taxable": 0.0, "igst": 0.0, "cgst": 0.0, "sgst": 0.0,
              "cess": 0.0, "rates": [], "rate_rows": 0}

    for line in lines[header_idx + 1:header_idx + 12]:
        tokens = [w["text"] for w in line]
        if not tokens or not re.match(r"^\d+(\.\d+)?%$", tokens[0]):
            continue
        if len(tokens) != len(labels):
            # Column count mismatch — record it so the caller can flag it.
            result.setdefault("warnings", []).append(
                f"tax table row has {len(tokens)} values for {len(labels)} columns")
            continue
        result["rate_rows"] += 1
        for label, tok in zip(labels, tokens):
            if label == "rate":
                result["rates"].append(tok)
            elif label in ("taxable", "igst", "cgst", "sgst", "cess"):
                result[label] += to_amount(tok)
    return result if result["rate_rows"] else result


# ------------------------------------------------------------- extraction

def extract_invoice(path, debug=False):
    rec = {"file": os.path.basename(path), "notes": []}

    all_words, page_texts = [], []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_texts.append(page.extract_text() or "")
            all_words.append(page.extract_words())
    text = "\n".join(page_texts)
    flat = re.sub(r"\s+", " ", text)

    # --- header fields -----------------------------------------------
    m = re.search(r"Invoice\s*No\.?\s*:?\s*([A-Za-z0-9\-/]+)", flat)
    rec["invoice_no"] = m.group(1) if m else ""

    m = re.search(r"Dated\s*:?\s*([\d]{1,2}[-/.][\w]{1,3}[-/.][\d]{2,4})", flat)
    rec["date"] = parse_invoice_date(m.group(1)) if m else None

    m = re.search(r"Reverse\s*Charge\s*:?\s*([YN])\b", flat, re.I)
    rec["rc_flag"] = m.group(1).upper() if m else ""

    m = re.search(r"Place\s*of\s*Supply\s*:?\s*([A-Za-z .]+?)\s*\((\d{2})\)", flat)
    if m:
        rec["pos_state"], rec["pos_code"] = m.group(1).strip(), m.group(2)
    else:
        rec["pos_state"], rec["pos_code"] = "", ""

    # --- party name -----------------------------------------------------
    # "Billed to" and "Shipped to" sit side by side and usually carry the same
    # text, so the name is isolated by x-position: take only words to the left
    # of the "Shipped to" column, on the first content line below "Billed to".
    rec["party"] = ""
    for page_words in all_words:
        billed = next((w for w in page_words
                       if w["text"].strip().lower().startswith("billed")), None)
        if not billed:
            continue
        shipped = next((w for w in page_words
                        if w["text"].strip().lower().startswith("shipped")
                        and abs(w["top"] - billed["top"]) < 6), None)
        right_edge = (shipped["x0"] - 5) if shipped else 10_000

        for line in rows_by_line(page_words):
            if line[0]["top"] <= billed["top"] + 2:
                continue
            left = [w["text"] for w in line if w["x0"] < right_edge]
            candidate = " ".join(left).strip(" :")
            if not candidate:
                continue
            if re.match(r"^GSTIN", candidate, re.I):
                break
            rec["party"] = candidate
            break
        if rec["party"]:
            break

    # --- GSTINs -------------------------------------------------------
    m = re.search(r"GSTIN\s*/\s*UIN\s*:?\s*([0-9A-Z]{15})", flat)
    rec["party_gstin"] = m.group(1) if m else ""
    m = re.search(r"(?<!/ UIN )GSTIN\s*:\s*([0-9A-Z]{15})", flat)
    rec["supplier_gstin"] = m.group(1) if m else ""
    if not rec["party_gstin"]:
        found = GSTIN_RE.findall(flat)
        others = [g for g in found if g != rec["supplier_gstin"]]
        if others:
            rec["party_gstin"] = others[0]

    # --- HSN / SAC: read the column band under the HSN/SAC header -----
    rec["hsn"] = ""
    hsn_codes = []
    for page_words in all_words:
        hdr = next((w for w in page_words if "HSN" in w["text"].upper()), None)
        if not hdr:
            continue
        lo, hi = hdr["x0"] - 12, hdr["x1"] + 12
        for w in page_words:
            if w["top"] > hdr["top"] + 2 and lo <= w["x0"] <= hi:
                tok = w["text"].strip()
                if re.fullmatch(r"\d{4,8}", tok):
                    hsn_codes.append(tok)
    if hsn_codes:
        uniq = sorted(set(hsn_codes), key=hsn_codes.index)
        rec["hsn"] = uniq[0]
        if len(uniq) > 1:
            rec["notes"].append(f"multiple HSN/SAC on invoice: {', '.join(uniq)}")

    # --- totals from the tax summary table ----------------------------
    lines = []
    for page_words in all_words:
        lines.extend(rows_by_line(page_words))
    tax = extract_tax_table(lines)

    if tax and tax["rate_rows"]:
        rec.update({k: tax[k] for k in ("taxable", "igst", "cgst", "sgst", "cess")})
        rec["rate"] = ", ".join(tax["rates"])
        if tax["rate_rows"] > 1:
            rec["notes"].append(f"multiple tax rates ({rec['rate']}) — totals combined")
        rec["notes"].extend(tax.get("warnings", []))
    else:
        # No tax table: typical of an RCM / nil-rated invoice.
        rec.update({"taxable": 0.0, "igst": 0.0, "cgst": 0.0,
                    "sgst": 0.0, "cess": 0.0, "rate": ""})
        m = re.search(r"Grand\s*Total\s*[`₹]?\s*([\d,]+\.\d{2})", flat)
        if m:
            rec["taxable"] = to_amount(m.group(1))
            rec["notes"].append("no tax table found — taxable taken from Grand Total")
        else:
            rec["notes"].append("could not locate totals — CHECK MANUALLY")

    # --- grand total printed on the invoice ---------------------------
    m = re.search(r"Grand\s*Total\s*[`₹]?\s*([\d,]+\.\d{2})", flat)
    rec["printed_total"] = to_amount(m.group(1)) if m else None

    # MODIFIED: accept "Rounded Off (+)" as well as "(-)" - the invoice prints
    # "Add : Rounded Off (+)" when the total is rounded up.
    m = re.search(r"Rounded\s*Off\s*\(?[-+]?\)?\s*([\d,]+\.\d{2})", flat, re.I)
    rec["rounding"] = to_amount(m.group(1)) if m else 0.0

    rec["tax_total"] = rec["igst"] + rec["cgst"] + rec["sgst"] + rec["cess"]
    rec["invoice_value"] = round(rec["taxable"] + rec["tax_total"], 2)

    # --- RCM determination --------------------------------------------
    no_tax = rec["tax_total"] == 0
    rule_rcm = no_tax and rec["taxable"] > 0
    rec["is_rcm"] = rule_rcm or rec["rc_flag"] == "Y"
    if rec["rc_flag"] == "Y" and not rule_rcm:
        rec["notes"].append("invoice marked Reverse Charge = Y but tax was charged")
    if rule_rcm and rec["rc_flag"] == "N":
        rec["notes"].append("no tax charged but invoice shows Reverse Charge = N "
                            "— treated as RCM per summary rule")
    rec["remark"] = "RCM" if rec["is_rcm"] else ""

    if debug:
        print(f"\n--- {rec['file']}")
        for k in ("invoice_no", "date", "party", "party_gstin", "hsn", "rate",
                  "taxable", "cgst", "sgst", "igst", "invoice_value",
                  "printed_total", "rc_flag", "remark"):
            print(f"    {k:>15}: {rec.get(k)}")
    return rec


# ------------------------------------------------------------ validation

def validate(records, period=None):
    issues = []

    def add(rec, severity, msg):
        issues.append({"Invoice no": rec.get("invoice_no", ""),
                       "File": rec["file"], "Severity": severity, "Issue": msg})

    seen = {}
    for rec in records:
        for note in rec["notes"]:
            add(rec, "Review", note)

        if not rec["invoice_no"]:
            add(rec, "Error", "invoice number not found")
        if rec["date"] is None:
            add(rec, "Error", "invoice date not found")
        if rec["taxable"] <= 0:
            add(rec, "Error", "taxable value is zero or missing")

        # tax arithmetic
        if rec["cgst"] or rec["sgst"]:
            if abs(rec["cgst"] - rec["sgst"]) > 0.02:
                add(rec, "Error", f"CGST {rec['cgst']:.2f} != SGST {rec['sgst']:.2f}")
            if rec["igst"]:
                add(rec, "Error", "both IGST and CGST/SGST charged on one invoice")

        # printed grand total vs taxable + tax
        if rec["printed_total"] is not None and rec["taxable"] > 0:
            diff = rec["invoice_value"] - rec["printed_total"]
            if abs(diff) > 0.005:
                if abs(abs(diff) - abs(rec["rounding"])) < 0.02:
                    add(rec, "Info",
                        f"invoice value {rec['invoice_value']:.2f} vs printed grand "
                        f"total {rec['printed_total']:.2f} — rounding off "
                        f"{rec['rounding']:.2f}")
                else:
                    add(rec, "Error",
                        f"invoice value {rec['invoice_value']:.2f} does not tie to "
                        f"printed grand total {rec['printed_total']:.2f}")

        # GSTIN
        if rec["party_gstin"]:
            if not gstin_is_valid(rec["party_gstin"]):
                add(rec, "Error", f"recipient GSTIN {rec['party_gstin']} fails checksum")
            elif rec["pos_code"] and rec["party_gstin"][:2] != rec["pos_code"]:
                add(rec, "Review",
                    f"recipient GSTIN state {rec['party_gstin'][:2]} differs from "
                    f"place of supply {rec['pos_code']} — verify IGST vs CGST/SGST")
        elif not rec["is_rcm"]:
            add(rec, "Review", "no recipient GSTIN found (B2C?)")

        # intra vs inter state
        sup, pos = rec.get("supplier_gstin", ""), rec["pos_code"]
        if sup and pos:
            intra = sup[:2] == pos
            if intra and rec["igst"] > 0:
                add(rec, "Error", "IGST charged on an intra-state supply")
            if not intra and (rec["cgst"] > 0 or rec["sgst"] > 0):
                add(rec, "Error", "CGST/SGST charged on an inter-state supply")

        # period
        if period and rec["date"]:
            if rec["date"].strftime("%m-%Y") != period:
                add(rec, "Error", f"invoice dated {rec['date']} is outside period {period}")

        # duplicates
        key = str(rec["invoice_no"]).strip().upper()
        if key:
            if key in seen:
                add(rec, "Error", f"duplicate invoice number, also in {seen[key]}")
            else:
                seen[key] = rec["file"]

    # sequence gaps
    nums = sorted({int(r["invoice_no"]) for r in records
                   if str(r["invoice_no"]).strip().isdigit()})
    if len(nums) > 1:
        missing = [n for n in range(nums[0], nums[-1] + 1) if n not in nums]
        if missing:
            issues.append({
                "Invoice no": "", "File": "(all)", "Severity": "Review",
                "Issue": "invoice numbers missing from the sequence: "
                         + ", ".join(map(str, missing))})
    return issues


# ---------------------------------------------------------------- output

IND = '[>=10000000]##\\,##\\,##\\,##0.00;[>=100000]##\\,##\\,##0.00;##,##0.00;"-"'
THIN = Side(style="thin", color="808080")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

HEADERS = ["Sr.no", "Date", "Invoice no", "GST No", "Party name",
           "Taxable value", "IGST", "CGST", "SGST", "Invoice value",
           "HSN", "Remark"]


def write_excel(records, issues, out_path, period):
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"

    hdr_font = Font(name="Arial", bold=True, size=10)
    body = Font(name="Arial", size=10)
    fill = PatternFill("solid", fgColor="DDEBF7")

    for c, h in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font, cell.fill, cell.border = hdr_font, fill, BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center")

    records = sorted(records, key=lambda r: (
        r["date"] or datetime.max.date(),
        int(r["invoice_no"]) if str(r["invoice_no"]).isdigit() else 0))

    row = 2
    for i, rec in enumerate(records, 1):
        values = [
            i,
            rec["date"],
            int(rec["invoice_no"]) if str(rec["invoice_no"]).isdigit() else rec["invoice_no"],
            rec["party_gstin"],
            rec["party"],
            rec["taxable"],
            rec["igst"],
            rec["cgst"],
            rec["sgst"],
            rec["invoice_value"],
            rec["hsn"],
            rec["remark"],
        ]
        for c, v in enumerate(values, 1):
            cell = ws.cell(row=row, column=c, value=v)
            cell.font, cell.border = body, BORDER
            if c == 2:
                cell.number_format = "DD/MM/YYYY"
                cell.alignment = Alignment(horizontal="center")
            elif c in (6, 7, 8, 9, 10):
                cell.number_format = IND
            elif c in (1, 3, 11):
                cell.alignment = Alignment(horizontal="center")
        # Invoice value as a live formula, not a pasted number
        ws.cell(row=row, column=10).value = f"=F{row}+G{row}+H{row}+I{row}"
        if rec["remark"] == "RCM":
            for c in range(1, len(HEADERS) + 1):
                ws.cell(row=row, column=c).fill = PatternFill(
                    "solid", fgColor="FCE4D6")
        row += 1

    last = row - 1
    total_row = row + 1
    tc = ws.cell(row=total_row, column=5, value="Total")
    tc.font = Font(name="Arial", bold=True, size=10)
    tc.border = BORDER
    for c in (6, 7, 8, 9, 10):
        col = get_column_letter(c)
        cell = ws.cell(row=total_row, column=c,
                       value=f"=SUM({col}2:{col}{last})")
        cell.font = Font(name="Arial", bold=True, size=10)
        cell.number_format = IND
        cell.border = BORDER

    widths = [6, 12, 11, 20, 34, 15, 11, 12, 12, 15, 10, 10]
    for c, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(HEADERS))}{last}"

    # ---- exceptions sheet
    ex = wb.create_sheet("Exceptions")
    for c, h in enumerate(["Severity", "Invoice no", "File", "Issue"], 1):
        cell = ex.cell(row=1, column=c, value=h)
        cell.font, cell.fill, cell.border = hdr_font, fill, BORDER
    order = {"Error": 0, "Review": 1, "Info": 2}
    for r, issue in enumerate(sorted(issues, key=lambda x: order.get(x["Severity"], 3)), 2):
        for c, key in enumerate(["Severity", "Invoice no", "File", "Issue"], 1):
            cell = ex.cell(row=r, column=c, value=issue[key])
            cell.font, cell.border = body, BORDER
        if issue["Severity"] == "Error":
            ex.cell(row=r, column=1).fill = PatternFill("solid", fgColor="FFC7CE")
    for c, w in enumerate([10, 12, 34, 95], 1):
        ex.column_dimensions[get_column_letter(c)].width = w
    ex.freeze_panes = "A2"
    if not issues:
        ex.cell(row=2, column=4, value="No exceptions found.").font = body

    # ---- run notes
    nt = wb.create_sheet("Run Notes")
    supplier = next((r.get("supplier_gstin") for r in records
                     if r.get("supplier_gstin")), "")
    info = [
        ("Generated on", datetime.now().strftime("%d-%m-%Y %H:%M")),
        ("Period", period or "not specified"),
        ("Supplier GSTIN", supplier),
        ("Invoices processed", len(records)),
        ("RCM invoices", sum(1 for r in records if r["remark"] == "RCM")),
        ("Errors", sum(1 for i in issues if i["Severity"] == "Error")),
        ("Items to review", sum(1 for i in issues if i["Severity"] == "Review")),
        ("", ""),
        ("Invoice value basis", "Taxable + IGST + CGST + SGST (before rounding off)"),
        ("Totals source", "Tax summary table at the foot of each invoice"),
        ("Reminder", "Review the Exceptions sheet before filing."),
    ]
    for r, (k, v) in enumerate(info, 1):
        nt.cell(row=r, column=1, value=k).font = Font(name="Arial", bold=True, size=10)
        nt.cell(row=r, column=2, value=v).font = body
    nt.column_dimensions["A"].width = 22
    nt.column_dimensions["B"].width = 60

    wb.save(out_path)


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True, help="Folder containing invoice PDFs")
    ap.add_argument("--out", default="GST-Sales-Summary.xlsx")
    ap.add_argument("--period", default=None, help="Expected period as MM-YYYY, e.g. 06-2026")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(args.folder):
        sys.exit(f"Folder not found: {args.folder}")

    # Listing the directory once and filtering by extension avoids the
    # duplicate-match problem that two globs ("*.pdf" and "*.PDF") cause on
    # case-insensitive filesystems such as Windows, where both patterns match
    # the same file and every invoice would be processed twice.
    seen_paths, pdfs = set(), []
    for name in sorted(os.listdir(args.folder), key=str.lower):
        if not name.lower().endswith(".pdf"):
            continue
        full = os.path.join(args.folder, name)
        if not os.path.isfile(full):
            continue
        key = os.path.normcase(os.path.abspath(full))
        if key in seen_paths:
            continue
        seen_paths.add(key)
        pdfs.append(full)

    if not pdfs:
        sys.exit(f"No PDFs found in {args.folder}")

    print(f"Reading {len(pdfs)} invoice(s) from {args.folder}")
    records = []
    for path in pdfs:
        try:
            records.append(extract_invoice(path, debug=args.debug))
        except Exception as exc:
            print(f"  FAILED: {os.path.basename(path)} — {exc}")
            records.append({
                "file": os.path.basename(path), "invoice_no": "", "date": None,
                "party": "EXTRACTION FAILED", "party_gstin": "", "hsn": "",
                "taxable": 0.0, "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0,
                "invoice_value": 0.0, "printed_total": None, "rounding": 0.0,
                "tax_total": 0.0, "rc_flag": "", "is_rcm": False, "remark": "",
                "rate": "", "pos_code": "", "pos_state": "", "supplier_gstin": "",
                "notes": [f"extraction failed: {exc}"]})

    issues = validate(records, args.period)
    write_excel(records, issues, args.out, args.period)

    errors = sum(1 for i in issues if i["Severity"] == "Error")
    reviews = sum(1 for i in issues if i["Severity"] == "Review")
    taxable = sum(r["taxable"] for r in records)
    value = sum(r["invoice_value"] for r in records)

    print(f"\nWritten: {args.out}")
    print(f"  Invoices     : {len(records)}")
    print(f"  Taxable value: {taxable:,.2f}")
    print(f"  Invoice value: {value:,.2f}")
    print(f"  RCM invoices : {sum(1 for r in records if r['remark'] == 'RCM')}")
    print(f"  Errors       : {errors}")
    print(f"  To review    : {reviews}")
    if errors:
        print("\n  Open the Exceptions sheet before using this summary.")


if __name__ == "__main__":
    main()
