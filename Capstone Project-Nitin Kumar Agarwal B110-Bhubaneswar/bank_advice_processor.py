#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BANK ADVICE  ->  SAP BANK UPLOADER
===================================
Reads every "FOREIGN EXPORT BILL TRANSACTION TAX INVOICE" (bank advice, .html/.htm,
optionally .pdf) and every bank statement (.xlsx/.xlsm/.csv) found in the INPUT folder,
traces each invoice Bill No. inside the statement's Description column, picks up ONLY the
amounts sitting in the "Withdrawal" column, and appends SAP journal lines to the
"Bank Uploader" workbook in the OUTPUT folder.

For every bill the posting looks like this (same as your sample uploader):
    Dr  Bank Charges      <- withdrawal lines that are commission / charges
    Dr  GST Receivable    <- withdrawal lines that are IGST / CGST / SGST
    Cr  To Bank           <- total of the above

CONTROLS
    1. Amount check   - the "Debit Advice" total of the advice must equal the total of the matching
                        Withdrawal lines of the bank statement, otherwise: NOT POSTED (log + advice
                        moved to  Bank advice\\Not Posted).
    2. Duplicate check- a bill already POSTED in Processing_Log.csv / present as Assignment in the
                        uploader / present in Processed_Register.csv is NEVER added to the uploader
                        again. Its rows are recorded in  Bank advice\\Posted\\Uploader -Posted.xlsx
                        and the advice is moved to  Bank advice\\Posted.
    3. Posted advices - every advice that is posted is moved to  Bank advice\\Posted.
    4. Only NEW bills (that pass check 1) ever reach the uploader.

USAGE
    python bank_advice_processor.py                  (uses the default folders below)
    python bank_advice_processor.py --dry-run        (shows what would be posted, writes nothing)
    python bank_advice_processor.py --input "D:\\x" --output "D:\\y"

Requires:  pip install openpyxl           (optional for PDF invoices:  pip install pdfplumber)
"""
import argparse
import csv
import datetime as dt
import hashlib
import html
import re
import shutil
import sys
from collections import Counter, OrderedDict
from copy import copy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl is not installed.  Run:  pip install openpyxl")

# --------------------------------------------------------------------------------------
# SETTINGS  (edit here if anything changes)
# --------------------------------------------------------------------------------------
DEFAULT_INPUT = r"C:\Users\Kaila\OneDrive\Desktop\PRESENTATION\Presentation 2\Bank advice"
DEFAULT_OUTPUT = r"C:\Users\Kaila\OneDrive\Desktop\PRESENTATION\Presentation 2"
OUTPUT_FILE_PATTERN = "Bank Uploader*.xlsx"      # existing uploader is picked up by this pattern
OUTPUT_FILE_NEW_NAME = "Bank Uploader .xlsx"     # used only if no uploader exists yet
REGISTER_FILE = "Processed_Register.csv"
LOG_FILE = "Processing_Log.csv"
NOT_POSTED_FOLDER = "Not Posted"                 # created inside the INPUT folder
INBOX_FOLDER = "Statements"                      # NEW advices are saved here (inside the INPUT folder)
STATEMENT_ARCHIVE_FOLDER = "Statement Archive"   # app keeps copies of uploaded bank statements here
ADVICE_EXT = (".html", ".htm", ".pdf")
STATEMENT_EXT = (".xlsx", ".xlsm", ".csv")
POSTED_FOLDER = "Posted"                         # created inside the INPUT folder
POSTED_UPLOADER_NEW_NAME = "Uploader -Posted.xlsx"   # kept inside the Posted folder
POSTED_UPLOADER_REGEX = r"uploader.*posted.*\.xlsx"   # an existing file like this is reused
POSTED_EXTRA_HEADERS = ["Remark", "Processed On", "Advice File"]

HEADERS = ["Serial No", "Document Date", "Posting Date", "Period", "Currency", "Reference",
           "Particulars", "Dr/Cr", "Amount in document currency", "Amount in local currency",
           "Assignment", "Text"]

REFERENCE_TEXT = "CHARGES AND GST"
LOCAL_CURRENCY = "INR"
BANK_LINE_PARTICULARS = "To Bank"
CHARGE_PARTICULARS = "Bank Charges"
GST_PARTICULARS = "GST Receivable"
GST_KEYWORDS = ("IGST", "CGST", "SGST", "UTGST", "GST")   # in bank description => GST line
FISCAL_YEAR_START_MONTH = 4                                # April  (Sep -> period 6)

# bank-statement column names (case-insensitive); first match wins
COL_ALIASES = {
    "description": ("description", "narration", "transaction remarks", "particulars"),
    "withdrawal": ("withdrawal", "withdrawals", "withdrawal amt.", "withdrawal amt", "debit"),
    "deposit": ("deposit", "deposits", "deposit amt.", "deposit amt", "credit"),
    "value_date": ("value date",),
    "posted_date": ("txn posted date", "transaction date", "posted date", "date"),
    "txn_id": ("transaction id", "txn id", "transaction no", "utr"),
}

TWO = Decimal("0.01")


# --------------------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------------------
def to_dec(value):
    """Convert cell value to Decimal (2dp) or None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value)).quantize(TWO, ROUND_HALF_UP)
    s = str(value).replace(",", "").strip()
    if not s or s in ("-", "--"):
        return None
    try:
        return Decimal(s).quantize(TWO, ROUND_HALF_UP)
    except InvalidOperation:
        return None


def to_date(value):
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    s = str(value).strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%b-%Y", "%d/%m/%y",
                "%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def norm(text):
    """Upper-case and drop every non-alphanumeric char (robust description matching)."""
    return re.sub(r"[^A-Z0-9]", "", str(text or "").upper())


def sap_date(d):
    return d.strftime("%d.%m.%Y") if d else ""


def fiscal_period(d):
    return ((d.month - FISCAL_YEAR_START_MONTH) % 12) + 1


def fmt_amt(d):
    return f"{d:,.2f}"


class ProcessingError(Exception):
    """A problem the user must fix (file open in Excel, nothing to process, ...)."""


def ensure_writable(path):
    """Stop BEFORE anything is written if a file is open in Excel (Windows locks it)."""
    path = Path(path)
    if path.exists():
        try:
            with open(path, "r+b"):
                pass
        except PermissionError:
            ask_close_excel(path)


def ask_close_excel(path):
    raise ProcessingError(f"Cannot write '{path.name}'. Please close it in Excel and try again.")


# --------------------------------------------------------------------------------------
# 1. INVOICE (bank advice) PARSER
# --------------------------------------------------------------------------------------
BILL_RE = re.compile(r"Our\s+Bill\s+No\.?\s*:?\s*([A-Z0-9]{8,30})", re.I)
BILL_FALLBACK_RE = re.compile(r"\b(\d{4}[A-Z]{3,4}\d{6,9})\b")
EVENT_DATE_RE = re.compile(r"Event\s+Date\s*:?\s*(\d{2}[-/.]\d{2}[-/.]\d{4})", re.I)
CHARGE_RE = re.compile(
    r"([A-Za-z][A-Za-z0-9 \-()%.]*?)\s*:\s*\(rounded off\)\s*([A-Z]{3})\s*([\d,]+(?:\.\d+)?)\s*(DR|CR)",
    re.I)
# the "Debit Advice" block only (ends where "Credit Advice" starts) - never read the credit total
DEBIT_SECTION_RE = re.compile(r"Debit\s+Advice(.*?)(?:Credit\s+Advice|$)", re.I | re.S)
TOTAL_RE = re.compile(r"Total\s*:?\s*([A-Z]{3})\s*([\d,]+(?:\.\d+)?)", re.I)


def html_to_text(raw):
    raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</(p|tr|pre|div)>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    return re.sub(r"[ \t\r\f\v\xa0]+", " ", raw)


def pdf_to_text(path):
    try:
        import pdfplumber
        with pdfplumber.open(str(path)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except ImportError:
        pass
    try:
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    except ImportError:
        print(f"  ! {path.name}: PDF skipped (pip install pdfplumber to read PDFs)")
    return ""


def parse_invoice(path):
    """Return dict(bill, event_date, charges[], debit_total, currency) or None."""
    if path.suffix.lower() == ".pdf":
        text = pdf_to_text(path)
    else:
        text = html_to_text(path.read_text(encoding="utf-8", errors="replace"))
    flat = re.sub(r"\s+", " ", text)
    if not re.search(r"TRANSACTION\s+TAX\s+INVOICE", flat, re.I) and not BILL_RE.search(flat):
        return None
    m = BILL_RE.search(flat) or BILL_FALLBACK_RE.search(flat)
    if not m:
        return None
    bill = m.group(1).upper()
    ev = EVENT_DATE_RE.search(flat)
    charges = [(c.group(1).strip(), c.group(2).upper(), to_dec(c.group(3)), c.group(4).upper())
               for c in CHARGE_RE.finditer(flat)]
    sec = DEBIT_SECTION_RE.search(flat)
    tot = TOTAL_RE.search(sec.group(1)) if sec else None
    return {
        "file": path.name,
        "path": path,
        "bill": bill,
        "event_date": to_date(ev.group(1).replace("/", "-").replace(".", "-")) if ev else None,
        "charges": charges,
        "debit_total": to_dec(tot.group(2)) if tot else None,
        "currency": (tot.group(1).upper() if tot else LOCAL_CURRENCY),
    }


# --------------------------------------------------------------------------------------
# 2. BANK STATEMENT READER
# --------------------------------------------------------------------------------------
def sheets_from_file(path):
    """Yield (sheet_name, rows) where rows is list of tuples."""
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        for ws in wb.worksheets:
            yield ws.title, [tuple(r) for r in ws.iter_rows(values_only=True)]
        wb.close()
    elif ext == ".csv":
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            yield "csv", [tuple(r) for r in csv.reader(fh)]


def find_columns(rows):
    """Locate header row + column indexes. Returns (header_row_index, {field: col}) or None."""
    for i, row in enumerate(rows[:60]):
        low = [str(c).strip().lower() if c is not None else "" for c in row]
        cols = {}
        for field, aliases in COL_ALIASES.items():
            for a in aliases:
                if a in low:
                    cols[field] = low.index(a)
                    break
        if "description" in cols and "withdrawal" in cols:
            return i, cols
    return None


def read_statement_lines(path):
    """Return OrderedDict fingerprint -> list of line dicts (per sheet)."""
    out = []
    for sheet, rows in sheets_from_file(path):
        found = find_columns(rows)
        if not found:
            continue
        hdr, cols = found
        lines = []
        for r_idx in range(hdr + 1, len(rows)):
            row = rows[r_idx]

            def get(f):
                c = cols.get(f)
                return row[c] if c is not None and c < len(row) else None

            desc = get("description")
            if desc is None or not str(desc).strip():
                continue
            lines.append({
                "src": f"{path.name} [{sheet}] row {r_idx + 1}",
                "txn_id": str(get("txn_id") or "").strip(),
                "value_date": to_date(get("value_date")) or to_date(get("posted_date")),
                "desc": str(desc).strip(),
                "withdrawal": to_dec(get("withdrawal")),
                "deposit": to_dec(get("deposit")),
            })
        out.append((f"{path.name} [{sheet}]", lines))
    return out


def merge_sources(sources):
    """Same line present in several sheets/files is counted ONCE (max count per fingerprint)."""
    def fp(l):
        return (l["txn_id"], norm(l["desc"]), l["withdrawal"], l["deposit"], l["value_date"])

    best = {}
    order = OrderedDict()
    for _, lines in sources:
        cnt = Counter(fp(l) for l in lines)
        for k, n in cnt.items():
            best[k] = max(best.get(k, 0), n)
        seen = Counter()
        for l in lines:
            k = fp(l)
            seen[k] += 1
            order.setdefault((k, seen[k]), l)
    return [l for (k, n), l in order.items() if n <= best[k]]


# --------------------------------------------------------------------------------------
# 3. REGISTER / OUTPUT WORKBOOK
# --------------------------------------------------------------------------------------
def line_key(bill, line, occurrence):
    base = f"{bill}|{line['txn_id']}|{norm(line['desc'])}|{line['withdrawal']}|{occurrence}"
    return hashlib.sha1(base.encode()).hexdigest()[:16]


def load_register(path):
    keys = set()
    if path.exists():
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                keys.add(r["key"])
    return keys


def classify(desc):
    u = desc.upper()
    return GST_PARTICULARS if any(k in u for k in GST_KEYWORDS) else CHARGE_PARTICULARS


def open_uploader(out_dir):
    existing = sorted(p for p in out_dir.glob(OUTPUT_FILE_PATTERN) if not p.name.startswith("~$"))
    if existing:
        path = existing[0]
        try:
            wb = openpyxl.load_workbook(path)
        except PermissionError:
            ask_close_excel(path)
        ws = wb.worksheets[0]
    else:
        path = out_dir / OUTPUT_FILE_NEW_NAME
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Bank Uploader"
        ws.append(HEADERS)
    return path, wb, ws


def uploader_state(ws):
    """Highest serial in the uploader + {bill: serial} for every Assignment already in it."""
    max_serial, bills = 0, {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or row[0] is None:
            continue
        try:
            serial = int(row[0])
        except (TypeError, ValueError):
            serial = None
        if serial:
            max_serial = max(max_serial, serial)
        if len(row) > 10 and row[10]:
            bills.setdefault(norm(row[10]), serial)
    return max_serial, bills


def log_posted_bills(log_path):
    """Bill numbers that the Processing Log already shows as POSTED."""
    bills = set()
    if log_path.exists():
        with open(log_path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            for r in csv.reader(fh):
                if len(r) > 3 and r[3].strip().upper() == "POSTED" and r[2].strip():
                    bills.add(norm(r[2]))
    return bills


def register_bills(path):
    bills = set()
    if path.exists():
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if r.get("bill_no"):
                    bills.add(norm(r["bill_no"]))
    return bills


def open_posted_uploader(posted_dir):
    """<input>/Posted/Uploader -Posted.xlsx  (re-uses an existing 'uploader...posted' workbook)."""
    posted_dir.mkdir(exist_ok=True)
    found = sorted(p for p in posted_dir.iterdir()
                   if re.fullmatch(POSTED_UPLOADER_REGEX, p.name, re.I) and not p.name.startswith("~$"))
    if found:
        path = found[0]
        wb = openpyxl.load_workbook(path)
        ws = wb.worksheets[0]
    else:
        path = posted_dir / POSTED_UPLOADER_NEW_NAME
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Uploader Posted"
        ws.append(HEADERS)
    for i, h in enumerate(POSTED_EXTRA_HEADERS, start=len(HEADERS) + 1):
        if ws.cell(row=1, column=i).value != h:
            ws.cell(row=1, column=i, value=h)
            if ws.cell(row=1, column=1).has_style:
                ws.cell(row=1, column=i)._style = copy(ws.cell(row=1, column=1)._style)
    return path, wb, ws


def sap_rows(serial, doc_date, bill, items):
    """items = [(particulars, Decimal amount)]  ->  Dr lines + balancing Cr 'To Bank' line."""
    d_str, period = sap_date(doc_date), fiscal_period(doc_date)
    rows = [[serial, d_str, d_str, period, LOCAL_CURRENCY, REFERENCE_TEXT, part, "Dr",
             float(amt), float(amt), bill, bill] for part, amt in items]
    total = sum((amt for _, amt in items), Decimal("0"))
    rows.append([serial, d_str, d_str, period, LOCAL_CURRENCY, REFERENCE_TEXT, BANK_LINE_PARTICULARS,
                 "Cr", float(total), float(total), bill, bill])
    return rows, total


# --------------------------------------------------------------------------------------
# 4. MAIN
# --------------------------------------------------------------------------------------
def collect_folder_files(in_dir):
    """Advices: <input>\\Statements (inbox) + <input> root.
    Bank statements: same two places (the bank statement usually sits in the input root)."""
    in_dir = Path(in_dir)
    places = [in_dir / INBOX_FOLDER, in_dir]
    files = []
    for d in places:
        if d.is_dir():
            files += sorted(f for f in d.iterdir()
                            if f.is_file() and not f.name.startswith(("~$", ".")))
    advices = [f for f in files if f.suffix.lower() in ADVICE_EXT]
    statements = [f for f in files if f.suffix.lower() in STATEMENT_EXT
                  and not re.fullmatch(POSTED_UPLOADER_REGEX, f.name, re.I)]
    return advices, statements


def run_pipeline(invoice_paths, statement_paths, in_dir, out_dir, dry_run=False, say=print):
    """Core engine used by both the command line and the web app.

    invoice_paths   : bank advice files (.html/.htm/.pdf)
    statement_paths : bank statement files (.xlsx/.xlsm/.csv)
    in_dir          : working folder  (Posted / Not Posted sub-folders live here)
    out_dir         : folder holding Bank Uploader.xlsx, register and log
    Returns dict(results, posted_rows, dup_rows, counts, out_path, posted_uploader_path, warnings).
    """
    in_dir, out_dir = Path(in_dir), Path(out_dir)
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    warnings, results = [], []

    def add_result(inv_file, bill, status, amount, note):
        results.append({"advice": inv_file, "bill": bill, "status": status,
                        "amount": fmt_amt(amount) if isinstance(amount, Decimal) else (amount or ""),
                        "note": note})

    invoices, sources, seen_paths = [], [], set()
    for p in map(Path, invoice_paths):
        key = str(p.resolve())
        if key in seen_paths:
            continue
        seen_paths.add(key)
        try:
            inv = parse_invoice(p) if p.suffix.lower() in (".html", ".htm", ".pdf") else None
        except Exception as e:
            inv = None
            warnings.append(f"Could not read {p.name}: {e}")
        if inv is None:
            add_result(p.name, "", "SKIPPED", "", "Not recognised as a Foreign Export Bill Transaction "
                       "Tax Invoice (bank advice) - ignored")
            continue
        # files inside the working folder (incl. the Statements inbox) are MOVED; others are copied
        try:
            p.resolve().relative_to(in_dir.resolve())
            inv["external"] = False
        except ValueError:
            inv["external"] = True
        invoices.append(inv)
    for p in map(Path, statement_paths):
        try:
            found = read_statement_lines(p)
        except Exception as e:
            found = None
            warnings.append(f"Could not read {p.name}: {e}")
        if found:
            sources.extend(found)
        else:
            warnings.append(f"{p.name}: no sheet with 'Description' and 'Withdrawal' columns - ignored")

    say(f"Working folder: {in_dir}")
    say(f"Advices: {len(invoices)}   Bank statement sheets: {len(sources)}")
    if not invoices:
        raise ProcessingError("No bank advice (invoice) files found to process.")
    if not sources:
        raise ProcessingError("No bank statement with 'Description' and 'Withdrawal' columns found.")

    stmt_lines = merge_sources(sources)
    register_path = out_dir / REGISTER_FILE
    out_path, wb, ws = open_uploader(out_dir)
    max_serial, uploader_bills = uploader_state(ws)

    # a bill counts as ALREADY POSTED if it is in the Processing Log (status POSTED),
    # in the uploader (Assignment) or in the register
    posted_bills = {b_: None for b_ in (log_posted_bills(out_dir / LOG_FILE)
                                        | register_bills(register_path))}
    posted_bills.update(uploader_bills)

    template_row = ws.max_row if ws.max_row >= 2 else None
    serial = max_serial
    new_register, log_rows, posted_rows, dup_rows = [], [], [], []
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    to_move_np, to_move_posted, dup_invoices = [], [], []

    say("-" * 78)
    for inv in invoices:
        bill = inv["bill"]
        nb = norm(bill)
        matches = [l for l in stmt_lines if nb in norm(l["desc"])]
        w_lines = [l for l in matches if l["withdrawal"] and l["withdrawal"] > 0]

        # ---- 1. bill already posted -> NOT to the uploader; record in Uploader-Posted ----------
        if nb in posted_bills:
            orig = posted_bills[nb]
            if w_lines:
                items = [(classify(l["desc"]), l["withdrawal"]) for l in w_lines]
                doc_date = w_lines[0]["value_date"]
            else:   # statement no longer holds it -> use the charges printed on the advice
                items = [(classify(c[0]), c[2]) for c in inv["charges"] if c[3] == "DR" and c[2]]
                doc_date = None
            doc_date = doc_date or inv["event_date"] or dt.date.today()
            remark = ("Bill already posted earlier" + (f" (Serial {orig})" if orig else "")
                      + " - not added to uploader")
            total = sum((a for _, a in items), Decimal("0"))
            if items:
                rows, _ = sap_rows(orig or "", doc_date, bill, items)
                dup_rows.extend(r + [remark, now, inv["file"]] for r in rows)
            msg = (remark + f"; rows recorded in '{POSTED_FOLDER}' folder ({POSTED_UPLOADER_NEW_NAME}), "
                   f"advice moved to '{POSTED_FOLDER}'")
            say(f"{bill}: ALREADY POSTED -> {msg}")
            log_rows.append([now, inv["file"], bill, "ALREADY POSTED", 0, "", msg])
            add_result(inv["file"], bill, "ALREADY POSTED", total, msg)
            dup_invoices.append(inv)
            continue

        # ---- 2. cannot be posted -> NOT POSTED folder ------------------------------------------
        def reject(msg, amount=""):
            say(f"{bill}: NOT POSTED -> {msg}")
            log_rows.append([now, inv["file"], bill, "NOT POSTED", 0, "", msg])
            add_result(inv["file"], bill, "NOT POSTED", amount, msg)
            to_move_np.append(inv)

        if not matches:
            reject("Bill No. not found in the Description column of the bank statement")
            continue
        if not w_lines:
            reject("Bill No. found in statement but no amount in the Withdrawal column - nothing to post")
            continue

        # CONTROL: advice (Debit Advice) total must equal the bank-statement withdrawals
        expected = inv["debit_total"]
        if expected is None:   # fall back to the sum of DR charges printed on the advice
            dr = [c[2] for c in inv["charges"] if c[3] == "DR" and c[2] is not None]
            expected = sum(dr, Decimal("0")) if dr else None
        total_withdrawn = sum((l["withdrawal"] for l in w_lines), Decimal("0"))
        if expected is None:
            reject("could not read the Debit Advice total from the invoice, so it cannot be "
                   "verified against the bank statement")
            continue
        if expected != total_withdrawn:
            reject(f"Amount mismatch: invoice debit total {fmt_amt(expected)} <> bank statement "
                   f"Withdrawal total {fmt_amt(total_withdrawn)} for this bill "
                   f"({len(w_lines)} line(s) found), difference {fmt_amt(expected - total_withdrawn)}. "
                   f"Not posted - invoice moved to '{NOT_POSTED_FOLDER}' folder", expected)
            continue

        # ---- 3. NEW bill, totals match -> post to the uploader ----------------------------------
        serial += 1
        doc_date = w_lines[0]["value_date"] or inv["event_date"] or dt.date.today()
        items = [(classify(l["desc"]), l["withdrawal"]) for l in w_lines]
        rows, cr_total = sap_rows(serial, doc_date, bill, items)
        posted_rows.extend(rows)
        occ = Counter()
        for l in w_lines:
            base = (bill, l["txn_id"], norm(l["desc"]), l["withdrawal"])
            occ[base] += 1
            new_register.append((line_key(bill, l, occ[base]), bill, l, inv["file"], serial))
        posted_bills[nb] = serial
        to_move_posted.append(inv)

        say(f"{bill}: POSTED -> Serial {serial}, {len(w_lines)} line(s), Cr To Bank {fmt_amt(cr_total)}")
        log_rows.append([now, inv["file"], bill, "POSTED", len(w_lines), fmt_amt(cr_total),
                         f"Advice moved to '{POSTED_FOLDER}' folder"])
        add_result(inv["file"], bill, "POSTED", cr_total,
                   f"Serial {serial}: {len(w_lines)} line(s) + Cr To Bank")
    say("-" * 78)

    counts = Counter(r["status"] for r in results)
    posted_uploader_path = in_dir / POSTED_FOLDER / POSTED_UPLOADER_NEW_NAME
    out = {"results": results, "posted_rows": posted_rows, "dup_rows": dup_rows, "counts": dict(counts),
           "out_path": out_path, "posted_uploader_path": posted_uploader_path,
           "warnings": warnings, "dry_run": dry_run}
    if dry_run:
        say(f"PREVIEW ONLY: {len(posted_rows)} row(s) would go to the uploader, {len(dup_rows)} to "
            f"{POSTED_UPLOADER_NEW_NAME}. Nothing written, nothing moved.")
        return out

    # ---- pre-flight: every file we will write must be closed (not open in Excel) ---------------
    posted_dir = in_dir / POSTED_FOLDER
    if dup_rows or to_move_posted or dup_invoices:
        posted_dir.mkdir(exist_ok=True)
    pu_path = pu_wb = pu_ws = None
    if dup_rows:
        try:
            pu_path, pu_wb, pu_ws = open_posted_uploader(posted_dir)
        except PermissionError as e:
            ask_close_excel(Path(getattr(e, "filename", "") or posted_dir / POSTED_UPLOADER_NEW_NAME))
    to_check = [out_dir / LOG_FILE]
    if posted_rows:
        to_check += [out_path, register_path]
    if pu_path:
        to_check.append(pu_path)
    for f in to_check:
        ensure_writable(f)

    # ---- write Uploader-Posted: EVERY already-posted advice of this run is recorded -----------
    if dup_rows:
        out["posted_uploader_path"] = pu_path
        append_rows(pu_ws, dup_rows, pu_ws.max_row if pu_ws.max_row >= 2 else None,
                    len(HEADERS) + len(POSTED_EXTRA_HEADERS))
        try:
            pu_wb.save(pu_path)
        except PermissionError:
            ask_close_excel(pu_path)
        say(f"Uploader-Posted: {len(dup_rows)} row(s) added to {POSTED_FOLDER}\\{pu_path.name}")

    # ---- write uploader (new bills only) ---------------------------------------------------------
    if posted_rows:
        append_rows(ws, posted_rows, template_row, len(HEADERS))
        try:
            wb.save(out_path)
        except PermissionError:
            ask_close_excel(out_path)
        append_csv_compact(register_path, REGISTER_HEADER,
                           [[key, bill, l["txn_id"], sap_date(l["value_date"]), l["desc"],
                             l["withdrawal"], inv_file, l["src"], ser, now]
                            for key, bill, l, inv_file, ser in new_register])

    write_log(out_dir, log_rows)
    move_invoices(in_dir, to_move_posted + dup_invoices, POSTED_FOLDER, say)
    move_invoices(in_dir, to_move_np, NOT_POSTED_FOLDER, say)

    say(f"Uploader     : {len(posted_rows)} row(s) added to {out_path.name}")
    say(f"Register: {register_path.name}   |   Log: {LOG_FILE}")
    return out


def main():
    ap = argparse.ArgumentParser(description="Bank advice + bank statement -> SAP Bank Uploader (automatic run)")
    ap.add_argument("--input", default=DEFAULT_INPUT, help="Bank advice folder (new advices in its 'Statements' sub-folder)")
    ap.add_argument("--output", default=DEFAULT_OUTPUT, help="folder with the Bank Uploader workbook, log and register")
    ap.add_argument("--dry-run", action="store_true", help="show result, write and move nothing")
    args = ap.parse_args()
    in_dir = Path(args.input)
    print("=" * 78)
    print("  BANK ADVICE -> SAP UPLOADER  (automatic run)")
    print(f"  New advices from : {in_dir / INBOX_FOLDER}")
    print(f"  Output folder    : {args.output}")
    print("=" * 78)
    if not in_dir.is_dir():
        print(f"\n  ERROR: folder not found: {in_dir}")
        return 1
    inv_files, stmt_files = collect_folder_files(in_dir)
    if not inv_files:
        print(f"\n  Nothing to do - no new bank advice in '{in_dir / INBOX_FOLDER}'.")
        return 0
    print(f"  Advices found    : {len(inv_files)}")
    print(f"  Bank statement   : {', '.join(f.name for f in stmt_files) or 'NOT FOUND'}\n")
    try:
        out = run_pipeline(inv_files, stmt_files, in_dir, args.output, dry_run=args.dry_run)
    except ProcessingError as e:
        print(f"\n  STOPPED: {e}")
        print("  Nothing was written and no advice was moved.")
        return 2
    c = out["counts"]
    print("\n" + "=" * 78)
    print("  SUMMARY" + ("  (DRY RUN - nothing written or moved)" if args.dry_run else ""))
    print(f"    Posted to uploader       : {c.get('POSTED', 0)}  ({len(out['posted_rows'])} row(s))")
    print(f"    Already posted (blocked) : {c.get('ALREADY POSTED', 0)}  -> recorded in {POSTED_FOLDER}\\{POSTED_UPLOADER_NEW_NAME}")
    print(f"    Not posted               : {c.get('NOT POSTED', 0)}  -> advice moved to '{NOT_POSTED_FOLDER}' (see {LOG_FILE})")
    if c.get("SKIPPED"):
        print(f"    Ignored (not an advice)  : {c['SKIPPED']}")
    for w in out["warnings"]:
        print(f"    ! {w}")
    print("=" * 78)
    return 0


def append_rows(ws, rows, template_row, ncols):
    for r in rows:
        ws.append(r)
        if template_row:
            for c in range(1, ncols + 1):
                src, dst = ws.cell(row=template_row, column=c), ws.cell(row=ws.max_row, column=c)
                if src.has_style:
                    dst._style = copy(src._style)


def move_invoices(in_dir, invoices, folder_name, say=print):
    """Put advice files into <input>/<folder_name> (never overwrites an existing file).
    Files that live in the working folder are MOVED; files uploaded from elsewhere are COPIED."""
    if not invoices:
        return
    dest_dir = in_dir / folder_name
    dest_dir.mkdir(exist_ok=True)
    for inv in invoices:
        src = inv["path"]
        dest = dest_dir / src.name
        if dest.exists():
            dest = dest_dir / f"{src.stem}_{dt.datetime.now():%Y%m%d_%H%M%S}{src.suffix}"
        try:
            if inv.get("external"):
                shutil.copy2(str(src), str(dest))
                say(f"  -> copied '{src.name}' to '{folder_name}' folder")
            else:
                shutil.move(str(src), str(dest))
                say(f"  -> moved '{src.name}' to '{folder_name}' folder")
        except OSError as e:
            say(f"  ! could not move '{src.name}' ({e}) - please move it manually")


REGISTER_HEADER = ["key", "bill_no", "txn_id", "value_date", "description", "withdrawal",
                   "invoice_file", "statement_source", "serial_no", "processed_on"]
LOG_HEADER = ["run_time", "invoice_file", "bill_no", "status", "lines_posted", "cr_total", "notes"]


def append_csv_compact(path, header, new_rows):
    """Append rows in the VERY NEXT row: blank rows (e.g. left after clearing the file in Excel)
    are removed first, and the header is restored if it was deleted."""
    existing = []
    if path.exists():
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            existing = [r for r in csv.reader(fh) if any(str(c).strip() for c in r)]
    if not existing or [c.strip().lower() for c in existing[0]] != [h.lower() for h in header]:
        existing.insert(0, header)
    try:
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerows(existing)
            w.writerows(new_rows)
    except PermissionError:
        print(f"  ! Could not update '{path.name}' - it is open in Excel. "
              f"Close it and run again (uploader was already saved).")


def write_log(out_dir, rows):
    if rows:
        append_csv_compact(out_dir / LOG_FILE, LOG_HEADER, rows)


if __name__ == "__main__":
    sys.exit(main())
