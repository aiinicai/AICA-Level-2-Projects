# ==========================================================
#  Vendor Name Matching
#  Payment file checker: Beneficiary Account Number + IFSC
#  matched against <working folder>\Unique_Vendor_Master.xlsx
#  (default working folder: C:\Day 5)
# ==========================================================
import sys
import os
import re
import subprocess
import importlib
import shutil
import hashlib
import hmac
import json
import time
from datetime import datetime

# ---------- 1. Auto install of required libraries ----------
REQUIRED = [("PyQt5", "PyQt5"), ("openpyxl", "openpyxl"), ("reportlab", "reportlab")]


def ensure_libraries():
    missing = []
    for module, package in REQUIRED:
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(package)
    if missing:
        print("Installing missing libraries: " + ", ".join(missing))
        flags = 0x08000000 if os.name == "nt" else 0
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install"] + missing,
                creationflags=flags,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            importlib.invalidate_caches()
        except Exception:
            print("Auto install failed. Please run this in Command Prompt:")
            print("pip install PyQt5 openpyxl reportlab")
            raise SystemExit(1)


ensure_libraries()

from openpyxl import load_workbook, Workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter
from copy import copy
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QKeySequence, QBrush
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QFrame, QHeaderView, QDialog, QLineEdit, QAbstractItemView, QInputDialog,
)

APP_NAME = "Vendor Name Matching"
# Working folder. Default is C:\Day 5 on Windows. It can be overridden with the
# VENDOR_MATCH_FOLDER environment variable (used by the demo and the tests).
FOLDER = os.environ.get("VENDOR_MATCH_FOLDER") or (
    r"C:\Day 5" if os.name == "nt" else os.path.join(os.path.expanduser("~"), "Day 5"))
MASTER_PATH = os.path.join(FOLDER, "Unique_Vendor_Master.xlsx")
BACKUP_FOLDER = os.path.join(FOLDER, "Master_Backups")
ADMIN_FILE = os.path.join(FOLDER, "Vendor_Master_Admin.json")
PBKDF2_ROUNDS = 200000
MIN_PASSKEY_LENGTH = 6
MAX_BACKUPS = 20
DEFAULT_MASTER_HEADERS = [
    "Debit A/c No.", "Debit Account Name", "Beneficiary Account Name",
    "IFSC Code", "Beneficiary Account Number",
]

GREEN_FILL = PatternFill("solid", start_color="C6EFCE", end_color="C6EFCE")
RED_FILL = PatternFill("solid", start_color="FFC7CE", end_color="FFC7CE")


# ---------- 2. Cleaning helpers ----------
def cell_to_text(value):
    """Convert any cell value to plain text without losing digits."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return repr(value)
    return str(value).strip()


def clean_code(value):
    """Account number or IFSC: trim, upper case, keep letters and digits only."""
    return re.sub(r"[^A-Z0-9]", "", cell_to_text(value).upper())


def clean_name(value):
    """Name: upper case, punctuation removed, Private/Limited unified."""
    text = cell_to_text(value).upper().replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    tokens = []
    for token in text.split():
        if token == "PRIVATE":
            token = "PVT"
        elif token == "LIMITED":
            token = "LTD"
        tokens.append(token)
    return "".join(tokens)


def norm_header(value):
    """Header text reduced to lower case letters and digits only."""
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


# Accepted header spellings (after norm_header), so small differences such as
# "Beneficiary Account No." / "Number" or "Amount (Rs.)" / "Amount" all work.
HEADER_ALIASES = {
    "name": ["beneficiaryaccountname", "beneficiaryname"],
    "ifsc": ["ifsccode", "ifsc", "beneficiaryifsccode", "beneficiaryifsc"],
    "acc": ["beneficiaryaccountnumber", "beneficiaryaccountno", "beneficiaryaccno",
            "beneficiaryacno", "beneficiaryaccount"],
    "sr": ["srno", "slno", "serialno", "srnumber"],
    "amount": ["amount", "amountrs", "amountinr", "amountrupees"],
    "status": ["status"],
    "remarks": ["remarks"],
}
FIELD_LABELS = {
    "name": "Beneficiary Account Name",
    "ifsc": "IFSC Code",
    "acc": "Beneficiary Account Number / No.",
}


def header_map(ws):
    """Map normalised header text to column number (row 1)."""
    result = {}
    for col in range(1, ws.max_column + 1):
        value = ws.cell(row=1, column=col).value
        if value is not None and str(value).strip():
            result.setdefault(norm_header(value), col)
    return result


def find_col(headers, field):
    for alias in HEADER_ALIASES[field]:
        if alias in headers:
            return headers[alias]
    return None


def find_columns(ws, fields, file_label):
    headers = header_map(ws)
    found = {}
    missing = []
    for field in fields:
        col = find_col(headers, field)
        if col is None:
            missing.append(FIELD_LABELS[field])
        else:
            found[field] = col
    if missing:
        present = [str(ws.cell(row=1, column=c).value).strip()
                   for c in range(1, ws.max_column + 1)
                   if ws.cell(row=1, column=c).value is not None]
        raise ValueError(
            "These columns were not found in row 1 of the " + file_label
            + ": " + ", ".join(missing)
            + "\n\nHeaders found in row 1: " + ", ".join(present)
        )
    return found


# ---------- 3. Master file ----------
def load_master():
    if not os.path.exists(MASTER_PATH):
        raise FileNotFoundError(
            "Master file not found at " + MASTER_PATH
            + "\n\nClick 'Edit Vendor Master' to create it.")
    try:
        wb = load_workbook(MASTER_PATH, data_only=True)
    except PermissionError:
        raise PermissionError("Master file is open in Excel. Please close it and try again.")
    ws = wb.active
    cols = find_columns(ws, ["acc", "ifsc", "name"], "master file")
    master = {}
    for r in range(2, ws.max_row + 1):
        acc = clean_code(ws.cell(row=r, column=cols["acc"]).value)
        ifsc = clean_code(ws.cell(row=r, column=cols["ifsc"]).value)
        raw_name = cell_to_text(ws.cell(row=r, column=cols["name"]).value)
        if not acc or not ifsc:
            continue
        entry = master.setdefault((acc, ifsc), {"names": set(), "originals": []})
        entry["names"].add(clean_name(raw_name))
        if raw_name and raw_name not in entry["originals"]:
            entry["originals"].append(raw_name)
    wb.close()
    return master


# ---------- 3b. Master editing (used by the Edit Vendor Master window) ----------
def grid_column(headers, field):
    """Index of a required field (acc / ifsc / name) among the master headers."""
    hm = {}
    for i, h in enumerate(headers):
        if h.strip():
            hm.setdefault(norm_header(h), i)
    for alias in HEADER_ALIASES[field]:
        if alias in hm:
            return hm[alias]
    return None


def read_master_grid():
    """Return (headers, rows) of the master as plain text, for the editor."""
    if not os.path.exists(MASTER_PATH):
        return list(DEFAULT_MASTER_HEADERS), []
    try:
        wb = load_workbook(MASTER_PATH, data_only=True)
    except PermissionError:
        raise PermissionError("Master file is open in Excel. Please close it and try again.")
    ws = wb.active
    headers = []
    for c in range(1, ws.max_column + 1):
        value = ws.cell(row=1, column=c).value
        headers.append(str(value).strip() if value is not None else "")
    while headers and not headers[-1]:
        headers.pop()
    if not headers:
        headers = list(DEFAULT_MASTER_HEADERS)
    rows = []
    for r in range(2, ws.max_row + 1):
        vals = [cell_to_text(ws.cell(row=r, column=c).value) for c in range(1, len(headers) + 1)]
        if any(vals):
            rows.append(vals)
    wb.close()
    return headers, rows


def prune_backups():
    """Keep only the most recent MAX_BACKUPS master backups."""
    try:
        files = sorted(f for f in os.listdir(BACKUP_FOLDER)
                       if f.startswith("Unique_Vendor_Master_backup_") and f.endswith(".xlsx"))
        for old in files[:-MAX_BACKUPS]:
            os.remove(os.path.join(BACKUP_FOLDER, old))
    except OSError:
        pass


def save_master_grid(headers, rows):
    """Write the edited rows to the master. Returns the backup path (or None)."""
    os.makedirs(FOLDER, exist_ok=True)
    backup = None
    if os.path.exists(MASTER_PATH):
        try:
            with open(MASTER_PATH, "r+b"):
                pass
        except PermissionError:
            raise PermissionError("Master file is open in Excel. Please close it and try again.")
        wb = load_workbook(MASTER_PATH)
        ws = wb.active
        os.makedirs(BACKUP_FOLDER, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = os.path.join(BACKUP_FOLDER, "Unique_Vendor_Master_backup_" + stamp + ".xlsx")
        shutil.copy2(MASTER_PATH, backup)
        if ws.max_row >= 2:
            ws.delete_rows(2, ws.max_row)
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Master"
        for c, title in enumerate(headers, start=1):
            ws.cell(row=1, column=c, value=title)
    for r, vals in enumerate(rows, start=2):
        for c, text in enumerate(vals, start=1):
            ws.cell(row=r, column=c, value=text)
    wb.save(MASTER_PATH)
    wb.close()
    if backup:
        prune_backups()
    return backup


def read_upload_grid(path, master_headers):
    """Read a vendor list for bulk upload, arranged in the master's column order.

    Columns are matched by header name (so order does not matter), and the
    account number, IFSC and name columns also accept the usual variations.
    """
    try:
        wb = load_workbook(path, data_only=True)
    except PermissionError:
        raise PermissionError("The upload file is open in Excel. Please close it and try again.")
    ws = wb.active
    find_columns(ws, ["acc", "ifsc", "name"], "upload file")
    imp = header_map(ws)
    ai, ii, ni = (grid_column(master_headers, f) for f in ("acc", "ifsc", "name"))
    if None in (ai, ii, ni):
        raise ValueError("The vendor master does not have the required columns.")
    mapping = []
    for i, header in enumerate(master_headers):
        if i == ai:
            col = find_col(imp, "acc")
        elif i == ii:
            col = find_col(imp, "ifsc")
        elif i == ni:
            col = find_col(imp, "name")
        else:
            col = imp.get(norm_header(header)) if header.strip() else None
        mapping.append(col)
    rows = []
    for r in range(2, ws.max_row + 1):
        vals = [cell_to_text(ws.cell(row=r, column=col).value).strip() if col else ""
                for col in mapping]
        if any(vals):
            rows.append(vals)
    wb.close()
    return rows


def export_master_grid(path, headers, rows):
    """Write the vendor master rows to a new formatted Excel file (values kept as text)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Vendor Master"
    ws.append(headers)
    head_fill = PatternFill("solid", start_color="6A11CB", end_color="6A11CB")
    name_col = grid_column(headers, "name")
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = head_fill
        ws.column_dimensions[get_column_letter(c)].width = 45 if (c - 1) == name_col else 26
    for vals in rows:
        ws.append(vals)
    ws.freeze_panes = "A2"
    wb.save(path)
    wb.close()


# ---------- 3c. Admin passkey (only a salted hash is stored, never the passkey) ----------
def admin_passkey_exists():
    return os.path.exists(ADMIN_FILE)


def save_admin_passkey(passkey):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", passkey.encode("utf-8"), salt, PBKDF2_ROUNDS)
    os.makedirs(FOLDER, exist_ok=True)
    with open(ADMIN_FILE, "w", encoding="utf-8") as f:
        json.dump({"salt": salt.hex(), "hash": digest.hex(), "rounds": PBKDF2_ROUNDS}, f)


def verify_admin_passkey(passkey):
    try:
        with open(ADMIN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        salt = bytes.fromhex(data["salt"])
        expected = bytes.fromhex(data["hash"])
        rounds = int(data["rounds"])
    except Exception:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", passkey.encode("utf-8"), salt, rounds)
    return hmac.compare_digest(digest, expected)


def ask_new_passkey(parent):
    """Ask twice for a new passkey. Returns the passkey, or None if cancelled."""
    while True:
        first, ok = QInputDialog.getText(
            parent, APP_NAME,
            "Set the admin passkey (minimum %d characters):" % MIN_PASSKEY_LENGTH,
            QLineEdit.Password)
        if not ok:
            return None
        if len(first) < MIN_PASSKEY_LENGTH:
            QMessageBox.warning(parent, APP_NAME,
                                "The passkey must be at least %d characters." % MIN_PASSKEY_LENGTH)
            continue
        second, ok = QInputDialog.getText(
            parent, APP_NAME, "Re-enter the passkey to confirm:", QLineEdit.Password)
        if not ok:
            return None
        if first != second:
            QMessageBox.warning(parent, APP_NAME, "The two passkeys do not match. Please try again.")
            continue
        return first


# ---------- 4. Core check ----------
def judge_row(master, raw_name, raw_acc, raw_ifsc):
    """The one rule used everywhere: returns (status, remark) for a payment line."""
    acc = clean_code(raw_acc)
    ifsc = clean_code(raw_ifsc)
    name = clean_name(raw_name)
    if not acc:
        return "Not Matched", "Beneficiary account number is blank"
    if not ifsc:
        return "Not Matched", "IFSC code is blank"
    if not name:
        return "Not Matched", "Beneficiary account name is blank"
    entry = master.get((acc, ifsc))
    if entry is None:
        return "Not Matched", "Account number and IFSC not found in master"
    if name in entry["names"]:
        return "Matched", "Account, IFSC and name agree with master"
    return "Not Matched", "Name differs from master. Master name: " + " / ".join(entry["originals"])


def check_file(payment_path):
    master = load_master()
    try:
        wb = load_workbook(payment_path)
    except PermissionError:
        raise PermissionError("Payment file is open in Excel. Please close it and try again.")
    ws = wb.active
    cols = find_columns(ws, ["name", "ifsc", "acc"], "payment file")
    headers = header_map(ws)

    c_name = cols["name"]
    c_ifsc = cols["ifsc"]
    c_acc = cols["acc"]
    c_sr = find_col(headers, "sr")
    c_amt = find_col(headers, "amount")

    # Status and Remarks columns (use existing ones, else add at the end)
    last = ws.max_column
    c_status = find_col(headers, "status")
    if c_status is None:
        last += 1
        c_status = last
    c_remarks = find_col(headers, "remarks")
    if c_remarks is None:
        last += 1
        c_remarks = last

    style_src = ws.cell(row=1, column=c_amt or c_acc)
    for col, title in ((c_status, "Status"), (c_remarks, "Remarks")):
        cell = ws.cell(row=1, column=col, value=title)
        cell._style = copy(style_src._style)
    ws.column_dimensions[ws.cell(row=1, column=c_status).column_letter].width = 16
    ws.column_dimensions[ws.cell(row=1, column=c_remarks).column_letter].width = 60

    results = []
    matched = not_matched = 0

    for r in range(2, ws.max_row + 1):
        if all(ws.cell(row=r, column=c).value in (None, "") for c in range(1, last + 1)
               if c not in (c_status, c_remarks)):
            continue

        raw_name = cell_to_text(ws.cell(row=r, column=c_name).value)
        raw_acc = cell_to_text(ws.cell(row=r, column=c_acc).value)
        raw_ifsc = cell_to_text(ws.cell(row=r, column=c_ifsc).value)
        status, remark = judge_row(master, raw_name, raw_acc, raw_ifsc)

        ws.cell(row=r, column=c_status, value=status)
        ws.cell(row=r, column=c_remarks, value=remark)
        fill = GREEN_FILL if status == "Matched" else RED_FILL
        for c in range(1, c_remarks + 1):
            ws.cell(row=r, column=c).fill = fill

        if status == "Matched":
            matched += 1
        else:
            not_matched += 1

        results.append({
            "sr": cell_to_text(ws.cell(row=r, column=c_sr).value) if c_sr else str(len(results) + 1),
            "name": raw_name,
            "acc": raw_acc,
            "ifsc": raw_ifsc,
            "amount": cell_to_text(ws.cell(row=r, column=c_amt).value) if c_amt else "",
            "status": status,
            "remarks": remark,
        })

    base = os.path.splitext(os.path.basename(payment_path))[0]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(FOLDER, exist_ok=True)
    out_path = os.path.join(FOLDER, base + "_Checked_" + stamp + ".xlsx")
    wb.save(out_path)
    wb.close()
    return results, matched, not_matched, out_path


# ---------- 4b. Print verified payment file as PDF ----------
class PrintBlocked(Exception):
    """Raised when the payment file is not fully verified, so no PDF may be made."""


def verify_payment_for_print(payment_path):
    """Read the ORIGINAL payment file again and check every line against the master now.

    Returns (headers, rows, verdicts). Nothing is written. The master is read fresh, so a
    change made after the first check is respected.
    """
    master = load_master()
    try:
        wb = load_workbook(payment_path, data_only=True)
    except PermissionError:
        raise PermissionError("Payment file is open in Excel. Please close it and try again.")
    ws = wb.active
    cols = find_columns(ws, ["name", "ifsc", "acc"], "payment file")
    width = ws.max_column
    headers = [cell_to_text(ws.cell(row=1, column=c).value) or "Column %d" % c
               for c in range(1, width + 1)]
    rows, verdicts = [], []
    for r in range(2, ws.max_row + 1):
        values = [cell_to_text(ws.cell(row=r, column=c).value) for c in range(1, width + 1)]
        if not any(values):
            continue
        status, remark = judge_row(master, values[cols["name"] - 1],
                                   values[cols["acc"] - 1], values[cols["ifsc"] - 1])
        rows.append(values)
        verdicts.append((status, remark))
    wb.close()
    return headers, rows, verdicts


def amount_total(headers, rows):
    """Return (column index, total text) for the Amount column, or (None, "") if there is none.

    Raises PrintBlocked if an amount is not a number, because a wrong total must never be printed.
    """
    from decimal import Decimal, InvalidOperation
    idx = None
    for i, h in enumerate(headers):
        if norm_header(h) in HEADER_ALIASES["amount"]:
            idx = i
            break
    if idx is None:
        return None, ""
    total = Decimal(0)
    decimals = False
    for n, row in enumerate(rows, start=2):
        text = row[idx].replace(",", "").replace(" ", "")
        if text.startswith("(") and text.endswith(")"):
            text = "-" + text[1:-1]
        if not text:
            continue                              # a blank amount adds nothing
        try:
            value = Decimal(text)
        except InvalidOperation:
            raise PrintBlocked("Printing is not allowed. The amount in row %d (%s) is not a number, "
                               "so a correct total cannot be shown.\n\nCorrect it and check again."
                               % (n, row[idx]))
        decimals = decimals or value != value.to_integral_value()
        total += value
    return idx, ("{:.2f}".format(total) if decimals else "{:d}".format(int(total)))


def write_landscape_pdf(out_path, headers, rows):
    """Write only the table, on A4 landscape pages, with the headings repeated on every page.

    reportlab writes the page size straight into the file (297 x 210 mm), so the PDF is
    landscape on every computer. The page size is read back from the finished file and
    the PDF is rejected if it is not wider than tall.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from xml.sax.saxutils import escape

    page = landscape(A4)
    margin = 10 * mm
    usable = page[0] - 2 * margin
    n = len(headers)
    size = 9 if n <= 7 else 8 if n <= 10 else 7 if n <= 14 else 6
    head_style = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=size, leading=size + 2)
    cell_style = ParagraphStyle("c", fontName="Helvetica", fontSize=size, leading=size + 2)

    # Column widths: no word (an IFSC code, an account number) is ever broken across lines.
    # Each column gets at least the width of its longest word. Spare width is shared out to
    # the columns whose text would otherwise wrap, and any left over is spread evenly.
    from reportlab.pdfbase.pdfmetrics import stringWidth
    pad = 8
    amt_idx, total_text = amount_total(headers, rows)     # raises PrintBlocked on a bad amount
    full, word = [], []
    for c in range(n):
        texts = [headers[c]] + [r[c] for r in rows]
        if c == amt_idx:
            texts.append(total_text)
        full.append(max(stringWidth(t, "Helvetica", size) for t in texts) + pad)
        word.append(max(stringWidth(w, "Helvetica-Bold" if t is headers[c] else "Helvetica", size)
                        for t in texts for w in (t.split() or [""])) + pad)
    if sum(full) <= usable:
        widths = [w + (usable - sum(full)) / n for w in full]
    elif sum(word) >= usable:
        widths = [w * usable / sum(word) for w in word]      # extreme case: very many columns
    else:
        spare = usable - sum(word)
        want = [f - w for f, w in zip(full, word)]
        widths = [w + spare * x / sum(want) for w, x in zip(word, want)]

    def para(text, style):
        return Paragraph(escape(text).replace("\n", "<br/>"), style)

    data = [[para(h, head_style) for h in headers]]
    data += [[para(v, cell_style) for v in r] for r in rows]
    if amt_idx is not None:
        total_row = [para("", cell_style) for _ in headers]
        label_col = amt_idx - 1 if amt_idx > 0 else amt_idx
        total_row[label_col] = Paragraph("<b>Total</b>", cell_style)
        total_row[amt_idx] = Paragraph("<b>%s</b>" % escape(total_text), cell_style)
        data.append(total_row)
    table = Table(data, colWidths=widths, repeatRows=1)
    style_cmds = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#888888")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6E6E6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    if amt_idx is not None:
        last = len(data) - 1
        style_cmds += [("BACKGROUND", (0, last), (-1, last), colors.HexColor("#F2F2F2")),
                       ("LINEABOVE", (0, last), (-1, last), 1.2, colors.black)]
    table.setStyle(TableStyle(style_cmds))
    doc = SimpleDocTemplate(out_path, pagesize=page, leftMargin=margin, rightMargin=margin,
                            topMargin=margin, bottomMargin=margin, title="Verified Payment File")
    doc.build([table])

    # Read the page size back from the finished file. Never leave a portrait PDF behind.
    with open(out_path, "rb") as f:
        boxes = re.findall(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]", f.read())
    if not boxes or any(float(b[2]) - float(b[0]) <= float(b[3]) - float(b[1]) for b in boxes):
        os.remove(out_path)
        raise RuntimeError("The PDF could not be created in landscape, so it was removed.")


def create_print_pdf(payment_path):
    """Make the PDF only if EVERY line is Matched. Otherwise raise PrintBlocked."""
    if not payment_path or not os.path.isfile(payment_path):
        raise PrintBlocked("Please select and check a payment file first.")
    headers, rows, verdicts = verify_payment_for_print(payment_path)
    if not rows:
        raise PrintBlocked("The payment file has no lines to print.")
    bad = [(i + 2, v) for i, v in enumerate(verdicts) if v[0] != "Matched"]
    if bad:
        lines = ["Row %d: %s" % (r, v[1]) for r, v in bad[:8]]
        more = "\n...and %d more." % (len(bad) - 8) if len(bad) > 8 else ""
        raise PrintBlocked(
            "Printing is not allowed. %d of %d lines are Not Matched.\n\n%s%s\n\n"
            "Correct the payment file or the vendor master, then check again."
            % (len(bad), len(rows), "\n".join(lines), more))

    base = os.path.splitext(os.path.basename(payment_path))[0]
    when = datetime.now()
    os.makedirs(FOLDER, exist_ok=True)
    out_path = os.path.join(FOLDER, base + "_Verified_" + when.strftime("%Y%m%d_%H%M%S") + ".pdf")
    write_landscape_pdf(out_path, headers, rows)
    return out_path, len(rows)


# ---------- 5a. Vendor master editor window ----------
class PasteTable(QTableWidget):
    """Table that accepts Ctrl+V of cells copied from Excel."""

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Paste):
            self.paste_from_clipboard()
        else:
            super().keyPressEvent(event)

    def paste_from_clipboard(self):
        text = QApplication.clipboard().text()
        if not text:
            return
        start_row = max(self.currentRow(), 0)
        start_col = max(self.currentColumn(), 0)
        for i, line in enumerate(text.splitlines()):
            r = start_row + i
            while r >= self.rowCount():
                new_row = self.rowCount()
                self.insertRow(new_row)
                for c in range(self.columnCount()):
                    self.setItem(new_row, c, QTableWidgetItem(""))
            for j, part in enumerate(line.split("\t")):
                c = start_col + j
                if c >= self.columnCount():
                    break
                self.setItem(r, c, QTableWidgetItem(part.strip()))


class MasterEditor(QDialog):
    def __init__(self, parent, headers, rows):
        super().__init__(parent)
        self.headers = headers
        self.dirty = False
        self.key_cols = tuple(grid_column(headers, f) for f in ("acc", "ifsc", "name"))
        self.dup_keys_warned = set()
        self._dup_scheduled = False
        self.setWindowTitle(APP_NAME + " - Edit Unique Vendor Master")
        self.resize(1150, 700)
        self.setStyleSheet("QDialog { background-color: #F3F0FF; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(12)

        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #11998E, stop:0.5 #2575FC, stop:1 #6A11CB); }")
        bl = QVBoxLayout(banner)
        bl.setContentsMargins(24, 14, 24, 14)
        title = QLabel("Edit Unique Vendor Master")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color: white; background: transparent;")
        sub = QLabel(MASTER_PATH)
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet("color: #EAF2FF; background: transparent;")
        bl.addWidget(title)
        bl.addWidget(sub)
        layout.addWidget(banner)

        body = QVBoxLayout()
        body.setContentsMargins(20, 0, 20, 0)
        body.setSpacing(10)
        layout.addLayout(body, 1)

        tools = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by vendor name, account number or IFSC...")
        self.search.setStyleSheet(
            "QLineEdit { padding: 9px; border: 2px solid #C9BFFF; border-radius: 8px;"
            " background: white; font-size: 13px; }")
        self.search.textChanged.connect(self.apply_filter)
        self.btn_add = QPushButton("Add Row")
        self.btn_add.setStyleSheet(MainWindow.button_css("#11998E", "#38EF7D"))
        self.btn_add.clicked.connect(self.add_row)
        self.btn_delete = QPushButton("Delete Selected Row(s)")
        self.btn_delete.setStyleSheet(MainWindow.button_css("#CB2D3E", "#EF473A"))
        self.btn_delete.clicked.connect(self.delete_rows)
        self.btn_upload = QPushButton("Bulk Upload")
        self.btn_upload.setStyleSheet(MainWindow.button_css("#6A11CB", "#2575FC"))
        self.btn_upload.clicked.connect(self.bulk_upload)
        self.btn_download = QPushButton("Download Master")
        self.btn_download.setStyleSheet(MainWindow.button_css("#00B4DB", "#0083B0"))
        self.btn_download.clicked.connect(self.download_master)
        tools.addWidget(self.search, 1)
        tools.addWidget(self.btn_add)
        tools.addWidget(self.btn_delete)
        tools.addWidget(self.btn_upload)
        tools.addWidget(self.btn_download)
        body.addLayout(tools)

        hint = QLabel("Double-click a cell to edit. Press Ctrl+V to paste rows copied from Excel, "
                      "or use Bulk Upload for an Excel file. Changes are applied only when you "
                      "click Save Master.")
        hint.setStyleSheet("color: #4A3F8F; font-size: 12px;")
        hint.setWordWrap(True)
        body.addWidget(hint)

        self.table = PasteTable(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        for c in range(len(headers)):
            self.table.setColumnWidth(c, 190)
        name_col = grid_column(headers, "name")
        if name_col is not None:
            self.table.setColumnWidth(name_col, 420)
        self.table.setStyleSheet(
            "QTableWidget { background: white; alternate-background-color: #F6F2FF;"
            " border: 1px solid #C9BFFF; gridline-color: #E4DEFF; }"
            "QHeaderView::section { background: #6A11CB; color: white; padding: 6px;"
            " border: none; font-weight: bold; }")
        self.fill(rows)
        self.table.itemChanged.connect(self.on_changed)
        body.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color: #4A3F8F; font-size: 13px; font-weight: bold;")
        self.btn_save = QPushButton("Save Master")
        self.btn_save.setStyleSheet(MainWindow.button_css("#FF512F", "#F09819"))
        self.btn_save.clicked.connect(self.save)
        self.btn_close = QPushButton("Close")
        self.btn_close.setStyleSheet(MainWindow.button_css("#8E2DE2", "#F953C6"))
        self.btn_close.clicked.connect(self.close)
        self.btn_passkey = QPushButton("Change Passkey")
        self.btn_passkey.setStyleSheet(MainWindow.button_css("#2193B0", "#6DD5ED"))
        self.btn_passkey.clicked.connect(self.change_passkey)
        self.lbl_dup = QLabel("")
        self.lbl_dup.setStyleSheet("color: #CB2D3E; font-size: 13px; font-weight: bold;")
        bottom.addWidget(self.lbl_count)
        bottom.addWidget(self.lbl_dup)
        bottom.addStretch()
        bottom.addWidget(self.btn_passkey)
        bottom.addWidget(self.btn_save)
        bottom.addWidget(self.btn_close)
        body.addLayout(bottom)
        self.update_count()
        self.refresh_duplicates(warn=False)

    def fill(self, rows):
        self.table.blockSignals(True)
        self.table.setRowCount(len(rows))
        for r, vals in enumerate(rows):
            for c in range(self.table.columnCount()):
                text = vals[c] if c < len(vals) else ""
                self.table.setItem(r, c, QTableWidgetItem(text))
        self.table.blockSignals(False)

    def update_count(self):
        self.lbl_count.setText("Total vendor rows: %d" % self.table.rowCount())

    def on_changed(self, item):
        self.dirty = True
        self.update_count()
        if not self._dup_scheduled:
            self._dup_scheduled = True
            QTimer.singleShot(0, self.run_duplicate_check)

    def run_duplicate_check(self):
        self._dup_scheduled = False
        self.refresh_duplicates(warn=True)

    def cell_text(self, r, c):
        item = self.table.item(r, c)
        return item.text().strip() if item is not None else ""

    def describe_duplicates(self, dups, limit):
        """Plain-language lines describing duplicate rows (row numbers as shown)."""
        ni = self.key_cols[2]
        lines = []
        for rows in dups.values():
            first = rows[0]
            first_name = self.cell_text(first, ni) if ni is not None else ""
            for r in rows[1:]:
                other = self.cell_text(r, ni) if ni is not None else ""
                differs = clean_name(first_name) != clean_name(other)
                lines.append("Row %d has the same account number and IFSC as row %d%s."
                             % (r + 1, first + 1, " but a different vendor name" if differs else ""))
        extra = len(lines) - limit
        lines = lines[:limit]
        if extra > 0:
            lines.append("...and %d more." % extra)
        return lines

    def refresh_duplicates(self, warn=False):
        """Highlight rows that repeat an Account Number + IFSC. Returns the duplicate groups."""
        ai, ii, ni = self.key_cols
        if ai is None or ii is None:
            return {}
        groups = {}
        for r in range(self.table.rowCount()):
            acc = clean_code(self.cell_text(r, ai))
            ifsc = clean_code(self.cell_text(r, ii))
            if acc and ifsc:
                groups.setdefault((acc, ifsc), []).append(r)
        dups = {k: rows for k, rows in groups.items() if len(rows) > 1}
        dup_rows = set(r for rows in dups.values() for r in rows)

        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            first_item = self.table.item(r, 0)
            painted = first_item is not None and first_item.data(Qt.UserRole) == 1
            should = r in dup_rows
            if painted == should:
                continue
            brush = QBrush(QColor("#F8B4B4")) if should else QBrush()
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if item is not None:
                    item.setBackground(brush)
                    item.setData(Qt.UserRole, 1 if should else None)
        self.table.blockSignals(False)

        if dups:
            self.lbl_dup.setText("Warning: %d duplicate row(s), highlighted in red. "
                                 "Remove them before saving." % len(dup_rows))
        else:
            self.lbl_dup.setText("")

        new_keys = [k for k in dups if k not in self.dup_keys_warned]
        self.dup_keys_warned = set(dups.keys())
        if warn and new_keys:
            lines = self.describe_duplicates({k: dups[k] for k in new_keys}, 4)
            QMessageBox.warning(
                self, APP_NAME,
                "Duplicate entry is not allowed.\n\n" + "\n".join(lines)
                + "\n\nPlease correct or delete the highlighted row(s). "
                  "The master cannot be saved while duplicates exist.")
        return dups

    def apply_filter(self, text):
        needle = text.strip().lower()
        for r in range(self.table.rowCount()):
            if not needle:
                self.table.setRowHidden(r, False)
                continue
            hit = False
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if item is not None and needle in item.text().lower():
                    hit = True
                    break
            self.table.setRowHidden(r, not hit)

    def add_row(self):
        self.search.clear()
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c in range(self.table.columnCount()):
            self.table.setItem(r, c, QTableWidgetItem(""))
        self.table.scrollToBottom()
        self.table.setCurrentCell(r, 0)
        self.table.editItem(self.table.item(r, 0))

    def delete_rows(self):
        rows = sorted({i.row() for i in self.table.selectionModel().selectedRows()}, reverse=True)
        if not rows:
            QMessageBox.information(self, APP_NAME, "Click a row to select it, then click Delete.")
            return
        answer = QMessageBox.question(
            self, APP_NAME, "Delete %d selected row(s)?" % len(rows),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        for r in rows:
            self.table.removeRow(r)
        self.dirty = True
        self.update_count()
        self.refresh_duplicates(warn=False)

    def save(self):
        """Save to the master file. Returns True when saved."""
        dups = self.refresh_duplicates(warn=False)
        if dups:
            lines = self.describe_duplicates(dups, 8)
            QMessageBox.critical(
                self, APP_NAME,
                "The master cannot be saved because it has duplicate entries "
                "(same Account Number and IFSC):\n\n" + "\n".join(lines)
                + "\n\nThe duplicate rows are highlighted in red. Please delete or correct them.")
            return False
        rows = self.collect_rows()

        idx = [grid_column(self.headers, f) for f in ("acc", "ifsc", "name")]
        if None in idx:
            QMessageBox.critical(
                self, APP_NAME,
                "The master must have columns for Beneficiary Account Name, IFSC Code and "
                "Beneficiary Account Number. Saving was cancelled.")
            return False
        ai, ii, ni = idx
        incomplete = sum(1 for v in rows if not v[ai] or not v[ii] or not v[ni])
        if incomplete:
            answer = QMessageBox.question(
                self, APP_NAME,
                "%d row(s) have a blank account number, IFSC or name and cannot be used for "
                "matching.\n\nSave anyway?" % incomplete,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return False

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            backup = save_master_grid(self.headers, rows)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, APP_NAME, str(exc))
            return False
        QApplication.restoreOverrideCursor()

        self.fill(rows)
        self.refresh_duplicates(warn=False)
        self.search.clear()
        self.dirty = False
        self.update_count()
        message = "Vendor master saved with %d row(s)." % len(rows)
        if backup:
            message += "\n\nBackup of the previous version:\n" + backup
        QMessageBox.information(self, APP_NAME, message)
        return True

    def collect_rows(self):
        """All non-blank rows currently in the table, as lists of text."""
        rows = []
        for r in range(self.table.rowCount()):
            vals = []
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                vals.append(item.text().strip() if item is not None else "")
            if any(vals):
                rows.append(vals)
        return rows

    def choose_upload_mode(self, count):
        """Ask how to load uploaded rows. Returns 'add', 'replace' or None."""
        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setText(
            "%d vendor row(s) found in the file.\n\n"
            "Add to Existing: new vendors are added and duplicates are skipped.\n"
            "Replace Entire Master: all current rows are removed and the uploaded rows "
            "take their place.\n\n"
            "Nothing is saved until you click Save Master." % count)
        btn_add = box.addButton("Add to Existing", QMessageBox.AcceptRole)
        btn_replace = box.addButton("Replace Entire Master", QMessageBox.DestructiveRole)
        box.addButton("Cancel", QMessageBox.RejectRole)
        box.exec_()
        clicked = box.clickedButton()
        if clicked == btn_add:
            return "add"
        if clicked == btn_replace:
            return "replace"
        return None

    def bulk_upload(self):
        ai, ii, ni = (grid_column(self.headers, f) for f in ("acc", "ifsc", "name"))
        if None in (ai, ii, ni):
            QMessageBox.critical(
                self, APP_NAME,
                "The master must have columns for Beneficiary Account Name, IFSC Code and "
                "Beneficiary Account Number.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Select the vendor list to upload", FOLDER, "Excel Files (*.xlsx)")
        if not path:
            return
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            new_rows = read_upload_grid(path, self.headers)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, APP_NAME, str(exc))
            return
        QApplication.restoreOverrideCursor()
        if not new_rows:
            QMessageBox.information(self, APP_NAME, "The selected file has no vendor rows.")
            return

        mode = self.choose_upload_mode(len(new_rows))
        if mode is None:
            return

        def key_of(vals):
            return (clean_code(vals[ai]), clean_code(vals[ii]))

        invalid = 0
        duplicates = 0
        conflicts = []
        names = {}
        if mode == "replace":
            final_rows = []
        else:
            final_rows = self.collect_rows()
            for vals in final_rows:
                key = key_of(vals)
                if key[0] and key[1]:
                    names.setdefault(key, vals[ni])
        added = 0
        for vals in new_rows:
            if not vals[ai] or not vals[ii] or not vals[ni]:
                invalid += 1
                continue
            key = key_of(vals)
            if key in names:
                if clean_name(names[key]) == clean_name(vals[ni]):
                    duplicates += 1
                else:
                    conflicts.append((vals[ai], vals[ii], names[key], vals[ni]))
                continue
            names[key] = vals[ni]
            final_rows.append(vals)
            added += 1

        self.search.clear()
        self.fill(final_rows)
        self.refresh_duplicates(warn=False)
        self.dirty = True
        self.update_count()
        if mode == "add":
            self.table.scrollToBottom()
        text = (
            "Upload loaded into the editor.\n\n"
            "Vendors added: %d\n"
            "Duplicates skipped (account and IFSC already present): %d\n"
            "Skipped, same account under a different vendor name: %d\n"
            "Rows skipped (blank account number, IFSC or name): %d\n"
            "Total rows now: %d"
            % (added, duplicates, len(conflicts), invalid, self.table.rowCount()))
        if conflicts:
            text += "\n\nDifferent-name conflicts (first %d):" % min(len(conflicts), 5)
            for acc, ifsc, kept, rejected in conflicts[:5]:
                text += "\n- %s / %s: master has '%s', upload has '%s'" % (acc, ifsc, kept, rejected)
        text += "\n\nPlease review, then click Save Master to apply."
        QMessageBox.information(self, APP_NAME, text)

    def download_master(self):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default = os.path.join(FOLDER, "Unique_Vendor_Master_Export_" + stamp + ".xlsx")
        path, _ = QFileDialog.getSaveFileName(
            self, "Download vendor master as", default, "Excel Files (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        if os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(MASTER_PATH)):
            QMessageBox.warning(
                self, APP_NAME,
                "Please choose a different file name. To update the master itself, use Save Master.")
            return
        rows = self.collect_rows()
        try:
            export_master_grid(path, self.headers, rows)
        except PermissionError:
            QMessageBox.critical(
                self, APP_NAME, "Could not write the file. If it is open in Excel, close it and try again.")
            return
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))
            return
        message = "Downloaded %d vendor row(s) to:\n%s" % (len(rows), path)
        if self.dirty:
            message += "\n\nThis file includes your unsaved changes."
        QMessageBox.information(self, APP_NAME, message)

    def change_passkey(self):
        current, ok = QInputDialog.getText(
            self, APP_NAME, "Enter the current admin passkey:", QLineEdit.Password)
        if not ok:
            return
        if not verify_admin_passkey(current):
            QMessageBox.warning(self, APP_NAME, "Incorrect passkey.")
            return
        new = ask_new_passkey(self)
        if new is None:
            return
        try:
            save_admin_passkey(new)
        except OSError as exc:
            QMessageBox.critical(self, APP_NAME, "Could not save the new passkey: " + str(exc))
            return
        QMessageBox.information(self, APP_NAME, "The admin passkey has been changed.")

    def can_close(self):
        if not self.dirty:
            return True
        answer = QMessageBox.question(
            self, APP_NAME, "You have unsaved changes. Save before closing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Save:
            return self.save()
        return answer == QMessageBox.Discard

    def reject(self):
        if self.can_close():
            super().reject()

    def closeEvent(self, event):
        if self.can_close():
            event.accept()
        else:
            event.ignore()


# ---------- 5. Interface ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1150, 700)
        self.out_path = None
        self.payment_path = None
        self.locked_until = 0.0
        self.setStyleSheet("QMainWindow { background-color: #F3F0FF; }")

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(12)

        # Header
        header = QFrame()
        header.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #6A11CB, stop:0.5 #2575FC, stop:1 #00C6FF); }")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(24, 16, 24, 16)
        title = QLabel(APP_NAME)
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setStyleSheet("color: white; background: transparent;")
        sub = QLabel("Payment file vendor verification: Account Number + IFSC against Vendor Master")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet("color: #EAF2FF; background: transparent;")
        hl.addWidget(title)
        hl.addWidget(sub)
        layout.addWidget(header)

        body = QVBoxLayout()
        body.setContentsMargins(20, 0, 20, 0)
        body.setSpacing(12)
        layout.addLayout(body)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_run = QPushButton("Select Payment File and Check")
        self.btn_run.setStyleSheet(self.button_css("#FF512F", "#F09819"))
        self.btn_run.clicked.connect(self.run_check)
        self.btn_open = QPushButton("Open Output Folder")
        self.btn_open.setStyleSheet(self.button_css("#11998E", "#38EF7D"))
        self.btn_open.clicked.connect(self.open_folder)
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setStyleSheet(self.button_css("#8E2DE2", "#F953C6"))
        self.btn_reset.clicked.connect(self.reset_screen)
        self.btn_master = QPushButton("Edit Vendor Master")
        self.btn_master.setStyleSheet(self.button_css("#2193B0", "#6DD5ED"))
        self.btn_master.clicked.connect(self.edit_master)
        self.btn_print = QPushButton("Print Verified PDF")
        self.btn_print.setStyleSheet(self.button_css("#F7971E", "#FFD200"))
        self.btn_print.clicked.connect(self.print_pdf)
        btn_row.addWidget(self.btn_run)
        btn_row.addWidget(self.btn_print)
        btn_row.addWidget(self.btn_reset)
        btn_row.addWidget(self.btn_master)
        btn_row.addWidget(self.btn_open)
        btn_row.addStretch()
        body.addLayout(btn_row)

        # Summary cards
        cards = QHBoxLayout()
        self.card_total, self.val_total = self.make_card("Total Rows", "#6A11CB", "#2575FC")
        self.card_match, self.val_match = self.make_card("Matched", "#11998E", "#38EF7D")
        self.card_not, self.val_not = self.make_card("Not Matched", "#CB2D3E", "#EF473A")
        cards.addWidget(self.card_total)
        cards.addWidget(self.card_match)
        cards.addWidget(self.card_not)
        body.addLayout(cards)

        self.lbl_info = QLabel("Master file: " + MASTER_PATH)
        self.lbl_info.setStyleSheet("color: #4A3F8F; font-size: 12px;")
        self.lbl_info.setWordWrap(True)
        body.addWidget(self.lbl_info)

        self.lbl_print = QLabel("")
        self.lbl_print.setStyleSheet("color: #4A3F8F; font-size: 12px; font-weight: bold;")
        self.lbl_print.setWordWrap(True)
        body.addWidget(self.lbl_print)

        # Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Sr. No.", "Beneficiary Account Name", "Account Number", "IFSC Code",
             "Amount", "Status", "Remarks"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setStretchLastSection(True)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 290)
        self.table.setColumnWidth(2, 190)
        self.table.setColumnWidth(3, 140)
        self.table.setColumnWidth(4, 110)
        self.table.setColumnWidth(5, 120)
        self.table.setStyleSheet(
            "QTableWidget { background: white; border: 1px solid #C9BFFF; gridline-color: #E4DEFF; }"
            "QHeaderView::section { background: #6A11CB; color: white; padding: 6px;"
            " border: none; font-weight: bold; }")
        body.addWidget(self.table, 1)

    @staticmethod
    def button_css(c1, c2):
        return (
            "QPushButton { color: white; font-size: 14px; font-weight: bold; padding: 12px 24px;"
            " border: none; border-radius: 8px;"
            " background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 %s, stop:1 %s); }"
            "QPushButton:hover { background: %s; }" % (c1, c2, c1))

    @staticmethod
    def make_card(title, c1, c2):
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { border-radius: 10px; background: qlineargradient("
            "x1:0,y1:0,x2:1,y2:1, stop:0 %s, stop:1 %s); }" % (c1, c2))
        lay = QVBoxLayout(frame)
        t = QLabel(title)
        t.setStyleSheet("color: white; font-size: 13px; background: transparent;")
        v = QLabel("0")
        v.setStyleSheet("color: white; font-size: 30px; font-weight: bold; background: transparent;")
        lay.addWidget(t)
        lay.addWidget(v)
        return frame, v

    def admin_login(self):
        """Ask for the admin passkey. Returns True only when access is granted."""
        remaining = int(self.locked_until - time.time())
        if remaining > 0:
            QMessageBox.warning(
                self, APP_NAME,
                "Too many incorrect attempts. Please try again in %d seconds." % remaining)
            return False

        if not admin_passkey_exists():
            QMessageBox.information(
                self, APP_NAME,
                "No admin passkey has been set yet.\n\nThe administrator should set it now. "
                "Only people who know this passkey will be able to edit the Vendor Master.")
            new = ask_new_passkey(self)
            if new is None:
                return False
            try:
                save_admin_passkey(new)
            except OSError as exc:
                QMessageBox.critical(self, APP_NAME, "Could not save the passkey: " + str(exc))
                return False
            QMessageBox.information(self, APP_NAME, "Admin passkey saved. Please keep it safe.")
            return True

        for attempt in range(1, 4):
            text, ok = QInputDialog.getText(
                self, APP_NAME,
                "Enter the admin passkey to open the Vendor Master (attempt %d of 3):" % attempt,
                QLineEdit.Password)
            if not ok:
                return False
            if verify_admin_passkey(text):
                return True
            QMessageBox.warning(self, APP_NAME, "Incorrect passkey.")
        self.locked_until = time.time() + 60
        QMessageBox.critical(
            self, APP_NAME, "Three incorrect attempts. Access is locked for 60 seconds.")
        return False

    def edit_master(self):
        if not self.admin_login():
            return
        try:
            headers, rows = read_master_grid()
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))
            return
        if not os.path.exists(MASTER_PATH):
            QMessageBox.information(
                self, APP_NAME,
                "The master file was not found. A new one will be created at:\n"
                + MASTER_PATH + "\n\nAdd the vendors and click Save Master.")
        dialog = MasterEditor(self, headers, rows)
        dialog.exec_()

    def reset_screen(self):
        """Clear results so the next payment file can be checked."""
        self.out_path = None
        self.payment_path = None
        self.lbl_print.setText("")
        self.val_total.setText("0")
        self.val_match.setText("0")
        self.val_not.setText("0")
        self.table.setRowCount(0)
        self.lbl_info.setText("Master file: " + MASTER_PATH)

    def open_folder(self):
        if os.path.isdir(FOLDER):
            if sys.platform.startswith("win"):
                os.startfile(FOLDER)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", FOLDER])
            else:
                subprocess.Popen(["xdg-open", FOLDER])
        else:
            QMessageBox.information(self, APP_NAME, "Folder not found: " + FOLDER)

    def run_check(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Payment File", FOLDER, "Excel Files (*.xlsx)")
        if not path:
            return
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            results, matched, not_matched, out_path = check_file(path)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, APP_NAME, str(exc))
            return
        QApplication.restoreOverrideCursor()

        self.out_path = out_path
        self.payment_path = path
        self.lbl_print.setText(
            "Print Verified PDF is ready: every line is Matched." if results and not_matched == 0
            else "Print Verified PDF is blocked: %d line(s) are Not Matched." % not_matched)
        self.val_total.setText(str(len(results)))
        self.val_match.setText(str(matched))
        self.val_not.setText(str(not_matched))
        self.lbl_info.setText("Checked file saved at: " + out_path)

        self.table.setRowCount(len(results))
        for i, row in enumerate(results):
            values = [row["sr"], row["name"], row["acc"], row["ifsc"],
                      row["amount"], row["status"], row["remarks"]]
            color = QColor("#D5F5E3") if row["status"] == "Matched" else QColor("#FADBD8")
            for j, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setBackground(color)
                if j == 5:
                    item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                self.table.setItem(i, j, item)

        QMessageBox.information(
            self, APP_NAME,
            "Check completed.\n\nTotal rows: %d\nMatched: %d\nNot Matched: %d\n\nSaved at:\n%s"
            % (len(results), matched, not_matched, out_path))


    def print_pdf(self):
        """Make the PDF of the original payment file, only when every line is Matched."""
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            pdf_path, count = create_print_pdf(self.payment_path)
        except PrintBlocked as exc:
            QApplication.restoreOverrideCursor()
            self.lbl_print.setText("Print Verified PDF is blocked. No PDF was created.")
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, APP_NAME, str(exc))
            return
        QApplication.restoreOverrideCursor()
        self.lbl_print.setText("PDF created: " + pdf_path)
        answer = QMessageBox.question(
            self, APP_NAME,
            "PDF created with all %d lines (all Matched).\n\nSaved at:\n%s\n\nOpen it now?"
            % (count, pdf_path))
        if answer == QMessageBox.Yes:
            try:
                if sys.platform.startswith("win"):
                    os.startfile(pdf_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", pdf_path])
                else:
                    subprocess.Popen(["xdg-open", pdf_path])
            except Exception as exc:
                QMessageBox.information(self, APP_NAME, "Could not open the PDF: " + str(exc))


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
