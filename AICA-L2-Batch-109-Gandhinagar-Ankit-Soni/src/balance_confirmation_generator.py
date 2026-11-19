#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 BALANCE CONFIRMATION GENERATOR  -  desktop edition
 -----------------------------------------------------------------------------
 Generates individual Microsoft Word (.docx) balance-confirmation letters from
 an Excel / CSV schedule of party balances, and e-mails each letter to the
 party from the auditor's own mailbox.

 Single file.  Run it with:      python balance_confirmation_generator.py
 Works from IDLE (Run > Run Module) and from a terminal.

 On the FIRST run the script installs the libraries it needs and then starts.
 When packaged with PyInstaller the installer is skipped automatically.

 Everything stays on this computer.  The only outbound connection the program
 ever makes is to your own mail server when you press Send.
===============================================================================
"""

import os
import sys
import subprocess
import importlib
import importlib.util

APP_NAME = "Balance Confirmation Generator"
APP_VERSION = "3.5"

# ---------------------------------------------------------------------------
# SECTION 1 - FIRST-RUN DEPENDENCY INSTALLER
# ---------------------------------------------------------------------------
# Each entry is (import name, pip requirement, what it is used for, required).
# Optional libraries are offered but the program still starts without them.
# ---------------------------------------------------------------------------
# pip is run with --upgrade, so each of these installs the newest release.
# The lower bounds simply rule out versions too old to behave.
REQUIREMENTS = [
    ("PyQt6",    "PyQt6>=6.7",      "the application window",            True),
    ("openpyxl", "openpyxl>=3.1.5", "reading .xlsx workbooks",           True),
    ("reportlab", "reportlab>=4.2",  "exporting the reports to PDF",     True),
    ("xlrd",     "xlrd>=2.0.1",     "reading older .xls workbooks",      False),
    ("keyring",  "keyring>=25.0",   "storing the mail password safely",  False),
    # reading the PDF or scan a party sends back: text layer, then OCR.
    # All three install from pip alone and work offline; the OCR models are
    # inside the rapidocr package.
    ("pymupdf",  "pymupdf>=1.24",   "opening the PDFs parties send back", False),
    ("onnxruntime", "onnxruntime>=1.17", "running the OCR engine",       False),
    ("rapidocr", "rapidocr>=3.0",   "reading scanned and handwritten slips", False),
]

_FROZEN = getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")


def _have(module_name):
    try:
        importlib.import_module(module_name)
        return True
    except Exception:
        return False


def _pip_install(requirement):
    """Install one requirement with the interpreter that is running us."""
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", requirement]
    # Debian/Ubuntu refuse to install into a managed environment without this.
    if sys.platform.startswith("linux"):
        cmd.insert(4, "--break-system-packages")
    creation = 0
    if os.name == "nt":                       # no console flash on Windows
        creation = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=900, creationflags=creation) \
            if creation else \
            subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        return proc.returncode == 0, (proc.stderr or proc.stdout or "").strip()
    except Exception as exc:                  # pip missing, offline, blocked
        return False, str(exc)


def ensure_dependencies():
    """Install anything missing.  Returns the list of optional modules absent."""
    if _FROZEN:
        return [name for name, _, _, req in REQUIREMENTS
                if not req and not _have(name)]

    missing = [(n, r, p, req) for (n, r, p, req) in REQUIREMENTS if not _have(n)]
    if missing:
        line = "=" * 74
        print(line)
        print(" %s %s - first-run setup" % (APP_NAME, APP_VERSION))
        print(line)
        print(" The following libraries are needed and will be installed once:")
        for _, req, purpose, required in missing:
            print("   - %-18s %s%s" % (req, purpose,
                                       "" if required else "  (optional)"))
        print(" This usually takes a minute.  Please keep this window open.")
        print(line)

        for name, req, purpose, required in missing:
            print(" Installing %s ..." % req, flush=True)
            ok, detail = _pip_install(req)
            if ok and _have(name):
                print("   done.")
                continue
            if required:
                print("\n Could not install %s automatically." % req)
                print(" Please open a command prompt and run:\n")
                print("     %s -m pip install %s\n" % (sys.executable, req))
                if detail:
                    print(" Reason reported by pip:")
                    print(" " + detail.splitlines()[-1][:300])
                input("\n Press Enter to close. ")
                sys.exit(1)
            print("   skipped - %s will be unavailable." % purpose)
        print(line)
        print(" Setup finished.  Starting %s ...\n" % APP_NAME, flush=True)

    return [name for name, _, _, req in REQUIREMENTS
            if not req and not _have(name)]


OPTIONAL_MISSING = ensure_dependencies()
HAS_XLRD = "xlrd" not in OPTIONAL_MISSING
HAS_KEYRING = "keyring" not in OPTIONAL_MISSING

# ---------------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------------
import csv
import io
import json
import re
import smtplib
import ssl
import traceback
import base64
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import date, datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

import openpyxl
from PyQt6.QtCore import (QDate, QObject, QRect, QSize, Qt, QThread, QTimer,
                          pyqtSignal)
from PyQt6.QtGui import (QAction, QColor, QFont, QFontDatabase, QIcon, QPainter,
                         QPalette, QPixmap, QTextDocument)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox,
                             QComboBox, QDateEdit, QDialog, QDoubleSpinBox, QGraphicsDropShadowEffect, QDialogButtonBox,
                             QFileDialog, QFormLayout, QFrame, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                             QLayout, QLineEdit, QListWidget, QListWidgetItem,
                             QMainWindow, QMessageBox, QPlainTextEdit,
                             QProgressBar, QPushButton, QScrollArea,
                             QSizePolicy, QSpinBox, QSplitter, QStackedWidget,
                             QStyle, QTableWidget, QTableWidgetItem, QTabWidget,
                             QTextBrowser, QVBoxLayout, QWidget)

if HAS_KEYRING:
    try:
        import keyring
    except Exception:
        HAS_KEYRING = False

# ===========================================================================
# SECTION 2 - LETTER ENGINE
# ---------------------------------------------------------------------------
# Pure logic, no interface code.  Everything the preview shows and everything
# the Word file contains is produced from build_letter_model(), so the two can
# never drift apart.
# ===========================================================================

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

BAD_TOKENS = re.compile(
    r"^(undefined|null|nan|nil|n/a|na|-|--|#n/a|#value!|#ref!)$", re.I)

CATEGORIES = ["Trade Receivable", "Trade Payable",
              "Advance from Customers", "Advance to Vendors"]


# --------------------------------------------------------------- utilities
def clean(value):
    """Normalise any spreadsheet cell into a tidy display string."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, datetime):
        return fmt_date_long(value.date())
    if isinstance(value, date):
        return fmt_date_long(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return ""
        # six places: enough for any balance, and it keeps binary noise such
        # as 7960098.4800000004 out of the preview
        return ("%.6f" % value).rstrip("0").rstrip(".") or "0"
    if isinstance(value, int):
        return str(value)
    text = str(value).replace(" ", " ").strip()
    text = re.sub(r"[ \t]+", " ", text)
    if not text or BAD_TOKENS.match(text):
        return ""
    return text


def to_date(value):
    """Accept a date, datetime, ISO string or common Indian formats."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
                    "%m/%d/%Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(text[:len(text)], pattern).date()
        except ValueError:
            continue
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)),
                        int(match.group(3)))
        except ValueError:
            return None
    return None


def fmt_date_long(value):
    """31 March 2026 - the form used throughout the letters."""
    d = to_date(value)
    if not d:
        return ""
    return "%d %s %d" % (d.day, MONTHS[d.month - 1], d.year)


def iso_date(value):
    d = to_date(value)
    return d.isoformat() if d else ""


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def valid_email(text):
    return bool(EMAIL_RE.match(str(text or "").strip()))


ABBREVIATIONS = {
    "amt": "amount", "bal": "balance", "addr": "address", "ccy": "currency",
    "curr": "currency", "cur": "currency", "a/c": "account", "acc": "account",
    "acct": "account", "nm": "name", "pty": "party", "cust": "customer",
    "vend": "vendor", "supp": "supplier", "o/s": "outstanding",
    "os": "outstanding", "adv": "advance", "mob": "mobile", "ph": "phone",
    "no": "number", "nos": "number", "sr": "serial", "srno": "serial number",
    "desc": "description", "partic": "particulars",
}


def norm_header(text):
    """Fold case, punctuation, spacing and common abbreviations together."""
    value = str(text if text is not None else "").lower()
    value = value.replace(" ", " ")
    value = re.sub(r"[_\-.]", " ", value)
    value = re.sub(r"[^a-z0-9/ ]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = " ".join(ABBREVIATIONS.get(word, word) for word in value.split(" "))
    value = re.sub(r"\be mail\b", "email", value)
    return re.sub(r"\s+", " ", value).strip()


def is_numeric_like(text):
    stripped = re.sub(r"[\s,]", "", str(text))
    stripped = re.sub(r"[₹$€£¥]", "", stripped)
    return bool(stripped) and bool(re.match(r"^-?\(?\d*\.?\d+\)?$", stripped))


def col_letter(index):
    letters, n = "", index + 1
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


# ------------------------------------------------------- header detection
HEADER_TERMS = [
    "party", "name", "address", "amount", "balance", "currency", "category",
    "type", "email", "contact", "vendor", "customer", "supplier", "debtor",
    "creditor", "outstanding", "receivable", "payable", "advance", "nature",
    "classification", "particulars", "account", "city", "state", "pincode",
    "gstin", "code", "serial", "phone", "mobile",
]


def _score_header_row(row):
    cells = [c for c in (clean(v) for v in (row or [])) if c]
    if len(cells) < 2:
        return float("-inf")
    unique, numeric, keywords, longs = set(), 0, 0, 0
    for cell in cells:
        unique.add(cell.lower())
        if is_numeric_like(cell):
            numeric += 1
        if len(cell) > 45:
            longs += 1
        folded = norm_header(cell)
        if any(term in folded for term in HEADER_TERMS):
            keywords += 1
    score = len(cells) + len(unique) * 0.6 + keywords * 4.5
    return score - numeric * 3.5 - longs * 2.5


def detect_header_row(grid):
    """Pick the most likely header row; title rows above it are ignored."""
    limit = min(len(grid), 20)
    best, best_score, second = -1, float("-inf"), float("-inf")
    for r in range(limit):
        has_data_below = any(
            any(clean(c) for c in (grid[k] or []))
            for k in range(r + 1, len(grid)))
        score = (_score_header_row(grid[r]) - r * 0.35) if has_data_below \
            else float("-inf")
        if score > best_score:
            second, best_score, best = best_score, score, r
        elif score > second:
            second = score
    if best < 0:
        return {"index": 0, "confidence": "low", "hits": 0}
    hits = 0
    for cell in (clean(v) for v in (grid[best] or [])):
        if cell and any(t in norm_header(cell) for t in HEADER_TERMS):
            hits += 1
    confident = hits >= 2 and best_score >= second + 3
    return {"index": best, "confidence": "high" if confident else "low",
            "hits": hits}


def build_columns(grid, header_index):
    """Return header labels, the data rows below them and column descriptors."""
    header_row = grid[header_index] if header_index < len(grid) else []
    width = max((len(r or []) for r in grid), default=0)
    headers = [clean(header_row[i]) if i < len(header_row) else ""
               for i in range(width)]
    data_rows = [r for r in grid[header_index + 1:]
                 if any(clean(c) for c in (r or []))]
    seen, columns = {}, []
    for c in range(width):
        values = [clean(r[c]) if c < len(r or []) else "" for r in data_rows]
        filled = [v for v in values if v]
        if not headers[c] and not filled:
            continue                                   # entirely blank column
        label = headers[c] or ("Column " + col_letter(c))
        key = label.lower()
        if key in seen:
            seen[key] += 1
            label = "%s (%d)" % (label, seen[key])
        else:
            seen[key] = 1
        columns.append({"index": c, "header": headers[c], "label": label,
                        "values": values, "filled": len(filled)})
    return {"headers": headers, "data_rows": data_rows, "columns": columns}


# --------------------------------------------------------- column mapping
FIELD_DEFS = {
    "partyName": {
        "label": "Party / Name", "required": True, "multi": False,
        "exact": ["party name", "name of party", "name of the party", "party",
                  "name", "customer name", "vendor name", "supplier name",
                  "account name", "counterparty", "counter party",
                  "legal name", "customer", "vendor", "supplier",
                  "debtor name", "creditor name", "party account", "account"],
        "contains": ["party", "counterparty", "legal name", "account name",
                     "customer", "vendor", "supplier", "debtor", "creditor",
                     "name"],
        "penalty": ["contact", "email", "bank", "file", "user", "city",
                    "state", "employee", "signatory"]},
    "address": {
        "label": "Address", "required": False, "multi": True,
        "exact": ["address", "address 1", "address 2", "address 3",
                  "address line 1", "address line 2", "billing address",
                  "mailing address", "registered address", "location", "city",
                  "state", "pincode", "pin code", "postal code", "zip",
                  "country"],
        "contains": ["address", "location", "city", "state", "pincode",
                     "postal", "zip", "country"],
        "penalty": ["email", "website", "ip"]},
    "amount": {
        "label": "Amount / Balance", "required": False, "multi": False,
        "exact": ["amount", "balance", "outstanding", "closing balance",
                  "balance amount", "receivable", "payable", "advance",
                  "outstanding amount", "closing bal", "amount outstanding",
                  "balance as per books", "net balance", "value"],
        "contains": ["amount", "balance", "outstanding", "receivable",
                     "payable", "advance", "value", "debit", "credit"],
        "penalty": ["number", "gstin", "pan", "invoice number", "code",
                    "serial", "phone", "mobile", "days"]},
    "currency": {
        "label": "Currency", "required": False, "multi": False,
        "exact": ["currency", "currency code", "ccy"],
        "contains": ["currency", "ccy"], "penalty": []},
    "category": {
        "label": "Category", "required": False, "multi": False,
        "exact": ["category", "type", "account type", "nature",
                  "balance type", "classification", "nature of balance",
                  "head", "group"],
        "contains": ["category", "type", "nature", "classification",
                     "balance type", "group", "head"],
        "penalty": ["gst", "tax type", "document type", "file type"]},
    "email": {
        "label": "Email", "required": False, "multi": False,
        "exact": ["email", "email id", "email address", "mail id",
                  "contact email"],
        "contains": ["email", "mail id"], "penalty": []},
    "contactPerson": {
        "label": "Contact person", "required": False, "multi": False,
        "exact": ["contact", "contact person", "contact name", "attention",
                  "kind attention", "attn", "concerned person"],
        "contains": ["contact person", "contact name", "attention", "contact"],
        "penalty": ["email", "number", "phone", "mobile"]},
}
FIELD_ORDER = ["partyName", "amount", "category", "currency", "email",
               "contactPerson", "address"]

ISO_CURRENCIES = ["INR", "USD", "EUR", "GBP", "AED", "SGD", "JPY", "AUD",
                  "CAD", "CHF", "CNY", "HKD", "SAR", "ZAR", "NZD", "SEK",
                  "THB", "MYR", "LKR", "BDT", "NPR"]


def _edge_word_match(folded, term):
    """Whole-word prefix / suffix test, so 'serial number' never matches
    'address' merely because the lengths happen to line up."""
    if not term or len(term) > len(folded):
        return False
    if folded[:len(term)] == term and (
            len(folded) == len(term) or folded[len(term)] == " "):
        return True
    at = len(folded) - len(term)
    return folded[at:] == term and (at == 0 or folded[at - 1] == " ")


def _header_score(definition, header):
    folded = norm_header(header)
    if not folded:
        return 0
    score = 0
    if folded in definition["exact"]:
        score = 100
    if score < 78:
        for term in definition["exact"]:
            if _edge_word_match(folded, term):
                score = max(score, 78)
    if score < 78:
        for term in definition["contains"]:
            if term in folded:
                score = max(score, 55 + min(len(term), 14))
    for term in definition["penalty"]:
        if term in folded:
            score -= 45
    return score


def _value_score(field, values):
    present = [v for v in values if v]
    if not present:
        return 0
    if field == "email":
        hits = sum(1 for v in present if valid_email(v))
        return 85 if hits / len(present) > 0.5 else 0
    if field == "currency":
        hits = sum(1 for v in present if v.upper() in ISO_CURRENCIES)
        return 85 if hits / len(present) > 0.6 else 0
    if field == "category":
        hits = sum(1 for v in present if normalize_category(v))
        return 85 if hits / len(present) > 0.5 else 0
    if field == "amount":
        hits = sum(1 for v in present if parse_amount(v)[0] is not None)
        return 45 if hits / len(present) > 0.75 else 0
    if field == "partyName":
        unique = {v.lower() for v in present}
        texty = sum(1 for v in present
                    if not is_numeric_like(v) and re.search(r"[A-Za-z]", v))
        avg_len = sum(len(v) for v in present) / len(present)
        if (texty / len(present) > 0.85 and
                len(unique) / len(present) > 0.6 and avg_len > 4):
            return 25
    return 0


def detect_mapping(columns):
    """Greedy, conflict-free assignment of spreadsheet columns to fields."""
    candidates = []
    for field in FIELD_ORDER:
        definition = FIELD_DEFS[field]
        for column in columns:
            hs = _header_score(definition, column["header"])
            vs = _value_score(field, column["values"])
            total = hs + (vs * 0.6 if hs > 0 else vs)
            if total > 20:
                candidates.append({"field": field, "col": column["index"],
                                   "score": round(total),
                                   "header": column["label"]})
    candidates.sort(key=lambda c: -c["score"])

    mapping = {f: {"field": f, "label": FIELD_DEFS[f]["label"], "cols": [],
                   "status": "missing", "score": 0, "candidates": []}
               for f in FIELD_ORDER}
    for candidate in candidates:
        mapping[candidate["field"]]["candidates"].append(candidate)

    used = {}
    for candidate in candidates:
        entry = mapping[candidate["field"]]
        if FIELD_DEFS[candidate["field"]]["multi"]:
            if candidate["col"] in used or len(entry["cols"]) >= 4:
                continue
            # further address columns need a solid header match, never a weak one
            if entry["cols"] and candidate["score"] < 70:
                continue
            used[candidate["col"]] = candidate["field"]
            entry["cols"].append(candidate["col"])
            entry["score"] = max(entry["score"], candidate["score"])
        else:
            if entry["cols"] or candidate["col"] in used:
                continue
            used[candidate["col"]] = candidate["field"]
            entry["cols"].append(candidate["col"])
            entry["score"] = candidate["score"]

    for field in FIELD_ORDER:
        entry = mapping[field]
        if not entry["cols"]:
            entry["status"] = "missing"
            continue
        rivals = [c for c in entry["candidates"] if c["col"] != entry["cols"][0]]
        near = rivals[0]["score"] if rivals else 0
        entry["status"] = ("detected"
                           if entry["score"] >= 70 and entry["score"] - near >= 12
                           else "review")
        if entry["score"] >= 95:
            entry["status"] = "detected"
    return mapping


# -------------------------------------------------- category normalisation
_ADV_FROM = [r"advance\s*(amount\s*)?received",
             r"advances?\s*from\s*(customer|client|buyer|debtor|party|parties)",
             r"(customer|client|buyer|debtor)s?\s*advances?",
             r"advances?\s*received\s*from", r"unearned\s*(revenue|income)",
             r"income\s*received\s*in\s*advance", r"advance\s*from\s*cust"]
_ADV_TO = [r"advances?\s*(amount\s*)?paid",
           r"advances?\s*to\s*(vendor|supplier|creditor|contractor|party|parties)",
           r"(vendor|supplier|creditor|contractor)s?\s*advances?",
           r"advances?\s*paid\s*to", r"prepaid\s*to\s*(vendor|supplier)",
           r"advance\s*to\s*vend", r"capital\s*advance"]
_TR_RULES = [r"trade\s*receivable", r"accounts?\s*receivable",
             r"(^|\s)receivables?(\s|$)", r"(^|\s)a\s*r(\s|$)",
             r"(^|\s)ar(\s|$)", r"trade\s*ar(\s|$)", r"(sundry\s*)?debtors?",
             r"(^|\s)customers?(\s|$)", r"(^|\s)dr(\s|$)"]
_TP_RULES = [r"trade\s*payable", r"accounts?\s*payable",
             r"(^|\s)payables?(\s|$)", r"(^|\s)a\s*p(\s|$)",
             r"(^|\s)ap(\s|$)", r"trade\s*ap(\s|$)", r"(sundry\s*)?creditors?",
             r"(^|\s)(vendors?|suppliers?)(\s|$)", r"(^|\s)cr(\s|$)"]


def _any_match(rules, text):
    return any(re.search(rule, text) for rule in rules)


def normalize_category(raw):
    """Map a spreadsheet value onto one of the four categories, or None."""
    text = norm_header(raw)
    if not text:
        return None
    for category in CATEGORIES:
        if text == norm_header(category):
            return category
    if "advance" in text or re.search(r"\bprepaid\b", text) or "unearned" in text:
        if _any_match(_ADV_FROM, text):
            return "Advance from Customers"
        if _any_match(_ADV_TO, text):
            return "Advance to Vendors"
        if re.search(r"receivable|debtor|customer|client|buyer", text):
            return "Advance from Customers"
        if re.search(r"payable|creditor|vendor|supplier", text):
            return "Advance to Vendors"
        return None                       # a bare "Advance" is ambiguous
    if _any_match(_TR_RULES, text):
        return "Trade Receivable"
    if _any_match(_TP_RULES, text):
        return "Trade Payable"
    return None


# -------------------------------------------------------- amount handling
_SYMBOLS = [("₹", "INR"), ("rs.", "INR"), ("rs", "INR"), ("inr", "INR"),
            ("us$", "USD"), ("usd", "USD"), ("$", "USD"), ("€", "EUR"),
            ("eur", "EUR"), ("£", "GBP"), ("gbp", "GBP"),
            ("¥", "JPY"), ("jpy", "JPY"), ("aed", "AED"),
            ("sgd", "SGD"), ("aud", "AUD"), ("cad", "CAD"), ("chf", "CHF")]


def parse_amount(raw):
    """Return (value, currency, note).  Handles 1,25,000 / (5,000) / Rs. / Cr."""
    if raw is None or raw == "":
        return (None, None, None)
    if isinstance(raw, bool):
        return (None, None, None)
    if isinstance(raw, (int, float)):
        value = float(raw)
        if value != value or value in (float("inf"), float("-inf")):
            return (None, None, None)
        return (value, None, None)

    text = str(raw).replace(" ", " ").strip()
    if not text or BAD_TOKENS.match(text):
        return (None, None, None)
    lowered = text.lower()
    currency = next((code for token, code in _SYMBOLS if token in lowered), None)

    negative, note = False, None
    if re.match(r"^\(.*\)$", text):
        negative, text = True, text[1:-1]
    if re.search(r"(^|[\s\d])cr\.?$", text, re.I):
        note, text = "Cr", re.sub(r"cr\.?$", "", text, flags=re.I)
    elif re.search(r"(^|[\s\d])dr\.?$", text, re.I):
        note, text = "Dr", re.sub(r"dr\.?$", "", text, flags=re.I)

    body = re.sub(r"[^0-9.,\-]", "", text)
    if not body:
        return (None, currency, None)
    if re.match(r"^-?\d{1,3}(\.\d{3})+(,\d+)?$", body):     # 1.234.567,89
        body = body.replace(".", "").replace(",", ".")
    else:
        body = body.replace(",", "")
    while body.count(".") > 1:
        body = body.replace(".", "", 1)
    try:
        value = float(body)
    except ValueError:
        return (None, currency, None)
    if negative:
        value = -abs(value)
    return (value, currency, note)


def _group_indian(digits):
    """1,25,000 - last three digits, then pairs."""
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def fmt_amount(value, currency=None):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    sign = "-" if number < 0 else ""
    whole, _, frac = ("%.2f" % abs(number)).partition(".")
    if str(currency or "").upper() == "INR":
        grouped = _group_indian(whole)
    else:
        grouped = "{:,}".format(int(whole))
    return "%s%s.%s" % (sign, grouped, frac)


def amount_label(value, currency=None):
    formatted = fmt_amount(value, currency)
    if formatted is None:
        return None
    prefix = (str(currency).upper() + " ") if currency else ""
    return prefix + formatted


# ------------------------------------------------- audit type and period
# auditors   - how the firm is described in "Our ..., [Firm], are engaged"
# engagement - what follows "are engaged in ... of our financial statements"
AUDIT_TYPES = {
    "Statutory Audit":       ("statutory audit",       "Statutory Auditor",
                              "statutory auditors",    "an audit"),
    "Interim Audit":         ("interim audit",         "Statutory Auditor",
                              "auditors",              "an interim audit"),
    "Special Purpose Audit": ("special purpose audit", "Auditor",
                              "auditors",              "a special purpose audit"),
    "Limited Review":        ("limited review",        "Auditor",
                              "auditors",              "a limited review"),
    "Tax Audit":             ("tax audit",             "Tax Auditor",
                              "tax auditors",          "a tax audit"),
    "Other":                 ("audit",                 "Auditor",
                              "auditors",              "an audit"),
}
AUDIT_TYPE_ORDER = ["Statutory Audit", "Interim Audit", "Special Purpose Audit",
                    "Limited Review", "Tax Audit", "Other"]


def audit_phrase(audit_type, other=""):
    """Lower-case noun phrase, e.g. for a heading or a covering e-mail."""
    if audit_type == "Other":
        text = clean(other)
        if not text:
            return "audit"
        text = re.sub(r"^the\s+", "", text, flags=re.I)
        return text[0].lower() + text[1:] if text[:1].isupper() else text
    return AUDIT_TYPES.get(audit_type, AUDIT_TYPES["Statutory Audit"])[0]


def audit_designation(audit_type):
    return AUDIT_TYPES.get(audit_type, ("", "Auditor"))[1]


def auditors_label(audit_type):
    """'Statutory auditors' / 'auditors' / 'tax auditors'."""
    return AUDIT_TYPES.get(audit_type, AUDIT_TYPES["Statutory Audit"])[2]


def engagement_phrase(audit_type, other=""):
    """What the firm is engaged in: 'an audit', 'a limited review', ..."""
    if audit_type == "Other":
        text = clean(other)
        if not text:
            return "an audit"
        text = re.sub(r"^(a|an|the)\s+", "", text, flags=re.I)
        if text[:1].isupper():
            text = text[0].lower() + text[1:]
        return ("an " if text[:1].lower() in "aeiou" else "a ") + text
    return AUDIT_TYPES.get(audit_type, AUDIT_TYPES["Statutory Audit"])[3]


def period_phrase(basis, as_at, period_start=""):
    """'for the year ended X' or 'for the period from X to Y'."""
    end = fmt_date_long(as_at)
    if not end:
        return ""
    if basis == "period":
        start = fmt_date_long(period_start)
        return ("for the period from %s to %s" % (start, end)) if start \
            else ("for the period ended %s" % end)
    return "for the year ended %s" % end


def period_label(basis, as_at, period_start=""):
    phrase = re.sub(r"^for the ", "", period_phrase(basis, as_at, period_start))
    return phrase[:1].upper() + phrase[1:] if phrase else ""


# --------------------------------------------------------- amount in words
# The confirmation formats carry "(In Words: ... only)".  Rupee amounts use
# the Indian system (lakh, crore); every other currency uses the
# international system (million, billion).
ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
        "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
        "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
        "Eighty", "Ninety"]


def _two_digits(n):
    if n < 20:
        return ONES[n]
    tens = TENS[n // 10]
    return (tens + " " + ONES[n % 10]) if n % 10 else tens


def _three_digits(n):
    parts = []
    if n >= 100:
        parts.append(ONES[n // 100] + " Hundred")
        n %= 100
    if n:
        parts.append(_two_digits(n))
    return " ".join(parts)


def indian_words(n):
    """1,23,45,678 -> 'One Crore Twenty Three Lakh Forty Five Thousand ...'"""
    if n == 0:
        return "Zero"
    parts = []
    crore, n = divmod(n, 10000000)
    lakh, n = divmod(n, 100000)
    thousand, n = divmod(n, 1000)
    if crore:
        parts.append((indian_words(crore) if crore > 999
                      else _three_digits(crore)) + " Crore")
    if lakh:
        parts.append(_three_digits(lakh) + " Lakh")
    if thousand:
        parts.append(_three_digits(thousand) + " Thousand")
    if n:
        parts.append(_three_digits(n))
    return " ".join(parts)


def international_words(n):
    if n == 0:
        return "Zero"
    parts = []
    for size, name in ((10 ** 12, "Trillion"), (10 ** 9, "Billion"),
                       (10 ** 6, "Million"), (1000, "Thousand")):
        unit, n = divmod(n, size)
        if unit:
            parts.append((international_words(unit) if unit > 999
                          else _three_digits(unit)) + " " + name)
    if n:
        parts.append(_three_digits(n))
    return " ".join(parts)


MAJOR_UNITS = {"INR": "Rupees", "USD": "US Dollars", "EUR": "Euros",
               "GBP": "Pounds", "AED": "Dirhams", "SGD": "Singapore Dollars",
               "AUD": "Australian Dollars", "CAD": "Canadian Dollars",
               "JPY": "Yen", "CHF": "Swiss Francs"}
MINOR_UNITS = {"INR": "Paise", "USD": "Cents", "EUR": "Cents", "GBP": "Pence",
               "AED": "Fils", "SGD": "Cents", "AUD": "Cents", "CAD": "Cents",
               "JPY": "", "CHF": "Rappen"}


def amount_in_words(value, currency=None):
    """e.g. 'Rupees One Lakh Twenty Five Thousand only'."""
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    code = str(currency or "").upper()
    negative = number < 0
    whole = int(abs(number) + 1e-9)
    fraction = int(round((abs(number) - whole) * 100))
    if fraction == 100:
        whole += 1
        fraction = 0
    body = indian_words(whole) if code == "INR" else international_words(whole)
    major = MAJOR_UNITS.get(code, code)
    text = ((major + " ") if major else "") + body
    minor = MINOR_UNITS.get(code, "Cents")
    if fraction and minor:
        text += " and " + _two_digits(fraction) + " " + minor
    if negative:
        text = "Minus " + text
    return re.sub(r"\s+", " ", text).strip() + " only"


# ------------------------------------------------------- category wording
# Taken from the firm's own four confirmation formats.  The letter is written
# by the CLIENT COMPANY to the party and signed by the company's own officer;
# the auditors are named as the people the signed reply must go to.
_LONG_DIFFERENCE = (
    "If the amount is not in agreement with your records, please notify our "
    "auditors directly, with a copy to us, of the amount shown by your "
    "records and, if possible, provide full particulars of the difference and "
    "reconciliation to your records.")
_SHORT_DIFFERENCE = (
    "If the amount is not in agreement with your records, please notify our "
    "auditors directly, with a copy to us, of the amount shown by your "
    "records and, if possible, provide full particulars of the difference and "
    "reconciliation to your records.")

CATEGORY_LANGUAGE = {
    "Trade Receivable": {
        "code": "TR",
        "title": "ACCOUNTS RECEIVABLE/DEBTOR CONFIRMATION",
        "party_label": "Customer Name",
        "request": "you confirm directly to them the amount payable by you to us",
        "statement": "a statement of our account in your books as at that date",
        "record_line": "the amount due from you",
        "no_payment": True,                 # debtor format only
        "difference": _LONG_DIFFERENCE,
        "slip": lambda c: "We hereby confirm that the amount payable by us to " + c,
        "meaning": "Client is owed money by the party."},
    "Trade Payable": {
        "code": "TP",
        "title": "ACCOUNTS PAYABLE/CREDITOR CONFIRMATION",
        "party_label": "Vendor Name",
        "request": "you furnish directly to them the amount of our liability "
                   "to you (if any)",
        "statement": "a statement of our account as at that date",
        "record_line": "the amount due to you",
        "no_payment": False,
        "difference": _SHORT_DIFFERENCE,
        "slip": lambda c: "We hereby confirm that the amount receivable by us from " + c,
        "meaning": "Client owes money to the party."},
    "Advance from Customers": {
        "code": "AFC",
        "title": "ADVANCE FROM CUSTOMER",
        "party_label": "Name",
        "request": "you furnish directly to them the amount of advance "
                   "received from you (if any)",
        "statement": "a statement of our account as at that date",
        "record_line": "the advance amount received from you",
        "no_payment": False,
        "difference": _SHORT_DIFFERENCE,
        "slip": lambda c: "We hereby confirm that the advance amount paid by us to " + c,
        "meaning": "Client has received an advance from the party."},
    "Advance to Vendors": {
        "code": "ATV",
        "title": "ADVANCE PAID TO VENDOR",
        "party_label": "Vendor Name",
        "request": "you furnish directly to them the amount of advance paid "
                   "to you (if any)",
        "statement": "a statement of our account as at that date",
        "record_line": "the advance amount paid to you",
        "no_payment": False,
        "difference": _SHORT_DIFFERENCE,
        "slip": lambda c: "We hereby confirm that the advance amount received by us from " + c,
        "meaning": "Client has paid an advance to the party."},
}



# ------------------------------------------------------------ page fitting
BODY_CPL = 92       # characters per line across the 9,638 twip text column


def _wrapped(text, chars_per_line):
    return max(1, -(-len(str(text or "")) // chars_per_line))


# ------------------------------------------------------------- the letter
def build_letter_model(conf):
    """The single source of truth for the preview and the Word document.

    Follows the firm's own confirmation formats:
        (on the letter head of the Company)        <- optional note
        ACCOUNTS RECEIVABLE/DEBTOR CONFIRMATION    <- title, centred, bold
                                        Date: ...  <- right
        Customer Name / [ADDRESS]                  <- left
        Dear Sir,  ... body ...
        [Partner] / [Firm] (Chartered Accountants) / Email Id:
        Yours faithfully / [Company] / Mr. XX / Director / CFO
        We hereby confirm ... + Name and Title / Company / Signature / Date
    """
    language = CATEGORY_LANGUAGE.get(conf.get("category"))
    if not language:
        raise ValueError("Unknown category: %s" % conf.get("category"))

    client = conf.get("client_name", "")
    as_at = conf.get("as_at") or conf.get("year_end")
    date_label = conf.get("year_end_label") or fmt_date_long(as_at)
    firm = conf.get("firm_name", "")
    auditors = auditors_label(conf.get("audit_type"))
    engagement = engagement_phrase(conf.get("audit_type"),
                                   conf.get("audit_type_other"))

    party = [{"text": conf.get("party_name", ""), "bold": False}]
    for line in conf.get("address_lines") or []:
        if line:
            party.append({"text": line, "bold": False})
    if conf.get("contact_person"):
        party.append({"text": "Kind Attn: " + conf["contact_person"],
                      "bold": False})

    label = amount_label(conf.get("amount"), conf.get("currency"))
    words = amount_in_words(conf.get("amount"), conf.get("currency"))
    code = str(conf.get("currency") or "").upper()

    paras = ["Our %s, %s, are engaged in %s of our financial statements. In "
             "connection therewith, they desire that %s as at %s and %s."
             % (auditors, firm, engagement, language["request"], date_label,
                language["statement"])]
    if label is not None:
        paras.append("According to our records, %s as at %s is %s (In Words: %s)"
                     % (language["record_line"], date_label, label, words))
    else:
        paras.append("According to our records, the %s as at %s is as per the "
                     "statement of account enclosed. Kindly confirm the balance "
                     "appearing in your books as at that date."
                     % (language["record_line"], date_label))
    paras.append("After signing your reply, please e-mail this letter directly "
                 "to our auditors at the following e-mail address:")

    emails = [a.get("email") for a in (conf.get("auditors") or [])
              if valid_email(a.get("email"))]
    auditor_block = []
    if conf.get("partner_name"):
        auditor_block.append({"text": conf["partner_name"], "bold": False})
    auditor_block.append({"text": firm + " (Chartered Accountants)",
                          "bold": False})
    auditor_block.append({"text": "Email ID: " + "; ".join(emails),
                          "bold": False})

    closing = [language["difference"]]
    if language["no_payment"]:
        closing.append("This letter is not a request for payment and "
                       "accordingly please do not enclose a cheque or other "
                       "payment with your confirmation.")
    closing.append("We thank you in advance for your co-operation in complying "
                   "with this request and apologise for any inconvenience caused.")

    # the client company signs, not the audit firm
    signature = [{"text": "Yours faithfully", "bold": False},
                 {"text": client, "bold": False}]
    if conf.get("signatory_name"):
        signature.append({"text": conf["signatory_name"], "bold": False,
                          "gap": True})
    if conf.get("signatory_designation"):
        signature.append({"text": conf["signatory_designation"], "bold": False})

    slip = {
        "sentence": "%s as on %s is %s______________"
                    % (language["slip"](client), date_label,
                       (code + " ") if code else ""),
        "rows": ["Name and Title", "Company / Firm", "Signature", "Date"],
    }

    bulk = (len(party) + len(auditor_block) + len(signature)
            + _wrapped(paras[0], BODY_CPL) + _wrapped(paras[1], BODY_CPL)
            + sum(_wrapped(t, BODY_CPL) for t in closing))

    return {
        "letterhead_note": "(on the letter head of the Company)"
                           if conf.get("letterhead_note") else "",
        "title": language["title"],
        "date_line": "Date: " + (conf.get("letter_date_label") or ""),
        "reference_line": ("Ref: " + conf["reference"])
                          if conf.get("reference") and
                          conf.get("print_reference", True) else "",
        "party_block": party,
        "salutation": "Dear Sir,",
        "paras": paras,
        "auditor_block": auditor_block,
        "closing_paras": closing,
        "signature": signature,
        "slip": slip,
        "compact": bulk >= 26,
        "category": conf.get("category"),
    }


# ===========================================================================
# SECTION 3 - WORD (.docx) WRITER
# ---------------------------------------------------------------------------
# A .docx is a ZIP of XML parts.  Writing those parts directly keeps the file
# genuine, needs no third-party document library, and gives exact control over
# row heights and spacing, which is what keeps every letter on one page.
# ===========================================================================

def xml_escape(value):
    text = str("" if value is None else value)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;")
                .replace("'", "&apos;"))


def _run(text, bold=False, italic=False, size=None, color=None):
    """One run of text.  rPr children must follow the schema order."""
    props = ""
    if bold:
        props += "<w:b/>"
    if italic:
        props += "<w:i/>"
    if color:
        props += '<w:color w:val="%s"/>' % color
    if size:
        props += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size, size)
    rpr = ("<w:rPr>%s</w:rPr>" % props) if props else ""
    return ('<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>'
            % (rpr, xml_escape(text)))


def _para(runs, before=0, after=120, line=264, justify=None, indent=0,
          hanging=0, keep_next=False, keep_lines=False, rule=False):
    """One paragraph.  pPr children must follow the schema order."""
    props = ""
    if keep_next:
        props += "<w:keepNext/>"
    if keep_lines:
        props += "<w:keepLines/>"
    if rule:
        props += ('<w:pBdr><w:bottom w:val="single" w:sz="6" w:space="3" '
                  'w:color="9A9A9A"/></w:pBdr>')
    props += ('<w:spacing w:before="%d" w:after="%d" w:line="%d" '
              'w:lineRule="auto"/>' % (before, after, line))
    if indent:
        props += '<w:ind w:left="%d"%s/>' % (
            indent, (' w:hanging="%d"' % hanging) if hanging else "")
    if justify:
        props += '<w:jc w:val="%s"/>' % justify
    return "<w:p><w:pPr>%s</w:pPr>%s</w:p>" % (props, runs or "")


# ---------------------------------------------------------------- layout
def _slip_table(rows, compact=False):
    """Borderless two-column grid: 'Name and Title   :  ______'."""
    borders = "".join(
        '<w:%s w:val="none" w:sz="0" w:space="0" w:color="auto"/>' % side
        for side in ("top", "left", "bottom", "right", "insideH", "insideV"))
    xml = ('<w:tbl><w:tblPr><w:tblW w:w="6600" w:type="dxa"/>'
           '<w:tblBorders>%s</w:tblBorders><w:tblLayout w:type="fixed"/>'
           '<w:tblCellMar><w:left w:w="0" w:type="dxa"/>'
           '<w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
           '<w:tblLook w:val="0000"/></w:tblPr>'
           '<w:tblGrid><w:gridCol w:w="2600"/><w:gridCol w:w="4000"/>'
           '</w:tblGrid>' % borders)
    for label in rows:
        xml += ('<w:tr><w:trPr><w:cantSplit/><w:trHeight w:val="%d" '
                'w:hRule="atLeast"/></w:trPr>'
                '<w:tc><w:tcPr><w:tcW w:w="2600" w:type="dxa"/></w:tcPr>%s</w:tc>'
                '<w:tc><w:tcPr><w:tcW w:w="4000" w:type="dxa"/></w:tcPr>%s</w:tc>'
                '</w:tr>'
                % (300 if compact else 340,
                   _para(_run(label), after=0, line=240),
                   _para(_run(":  ______________________"), after=0, line=240)))
    return xml + "</w:tbl>"


def document_xml(model):
    compact = model.get("compact")
    scale = 0.78 if compact else 1.0

    def sp(value):
        return int(round(value * scale))

    body = ""
    if model.get("letterhead_note"):
        body += _para(_run(model["letterhead_note"]), justify="center",
                      after=sp(40), line=240)
    body += _para(_run(model["title"], bold=True), justify="center",
                  after=sp(260), line=240, keep_next=True)
    body += _para(_run(model["date_line"]), justify="right",
                  after=0 if model.get("reference_line") else sp(60), line=240)
    if model.get("reference_line"):
        # quoted back by the party, and what ties their reply to this letter
        body += _para(_run(model["reference_line"]), justify="right",
                      after=sp(60), line=240)
    last = len(model["party_block"]) - 1
    for i, line in enumerate(model["party_block"]):
        body += _para(_run(line["text"], bold=line["bold"]),
                      after=sp(240) if i == last else 0, line=240)
    body += _para(_run(model["salutation"]), after=sp(200), line=240)
    for i, text in enumerate(model["paras"]):
        body += _para(_run(text), justify="both",
                      after=sp(150 if i == len(model["paras"]) - 1 else 200),
                      keep_next=i == len(model["paras"]) - 1)
    last = len(model["auditor_block"]) - 1
    for i, line in enumerate(model["auditor_block"]):
        body += _para(_run(line["text"], bold=line["bold"]),
                      after=sp(200) if i == last else 0, line=240)
    for text in model["closing_paras"]:
        body += _para(_run(text), justify="both", after=sp(200))
    last = len(model["signature"]) - 1
    for i, line in enumerate(model["signature"]):
        body += _para(_run(line["text"], bold=line["bold"]),
                      before=sp(360) if line.get("gap") else 0,
                      after=sp(420) if i == last else sp(20), line=240,
                      keep_lines=True, keep_next=i < last)
    body += _para(_run(model["slip"]["sentence"]), justify="both",
                  after=sp(160), keep_next=True)
    body += _slip_table(model["slip"]["rows"], compact)
    body += '<w:p><w:pPr><w:spacing w:after="0"/></w:pPr></w:p>'

    margin = 1021 if compact else 1134        # 1.8 cm when tight, else 2 cm
    top = margin if model.get("letterhead_note") else int(round(margin * 1.25))
    body += ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
             '<w:pgMar w:top="%d" w:right="1134" w:bottom="%d" w:left="1134" '
             'w:header="567" w:footer="567" w:gutter="0"/>'
             '<w:cols w:space="708"/><w:docGrid w:linePitch="360"/></w:sectPr>'
             % (top, margin))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/'
            'wordprocessingml/2006/main" xmlns:r="http://schemas.'
            'openxmlformats.org/officeDocument/2006/relationships">'
            '<w:body>%s</w:body></w:document>' % body)


STYLES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/'
    '2006/main"><w:docDefaults><w:rPrDefault><w:rPr>'
    '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Calibri" '
    'w:cs="Calibri"/><w:sz w:val="21"/><w:szCs w:val="21"/>'
    '<w:lang w:val="en-IN"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr>'
    '<w:spacing w:after="120" w:line="264" w:lineRule="auto"/></w:pPr>'
    '</w:pPrDefault></w:docDefaults>'
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
    '<w:name w:val="Normal"/><w:qFormat/></w:style>'
    '<w:style w:type="table" w:default="1" w:styleId="TableNormal">'
    '<w:name w:val="Normal Table"/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/>'
    '<w:tblCellMar><w:top w:w="0" w:type="dxa"/>'
    '<w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/>'
    '<w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>'
    '</w:styles>')

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
    'content-types"><Default Extension="rels" ContentType="application/'
    'vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
    '<Override PartName="/docProps/core.xml" ContentType="application/'
    'vnd.openxmlformats-package.core-properties+xml"/>'
    '<Override PartName="/docProps/app.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>')

PKG_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships"><Relationship Id="rId1" Type="http://schemas.'
    'openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/><Relationship Id="rId2" Type="http://'
    'schemas.openxmlformats.org/package/2006/relationships/metadata/'
    'core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/extended-properties" Target="docProps/app.xml"/>'
    '</Relationships>')

DOC_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships"><Relationship Id="rId1" Type="http://schemas.'
    'openxmlformats.org/officeDocument/2006/relationships/styles" '
    'Target="styles.xml"/></Relationships>')

APP_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/'
    '2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/'
    'officeDocument/2006/docPropsVTypes"><Application>Balance Confirmation '
    'Generator</Application><Company></Company></Properties>')


def core_xml(conf, stamp=None):
    when = stamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    span = period_label(conf.get("basis"),
                        conf.get("as_at") or conf.get("year_end"),
                        conf.get("period_start")) \
        or ("year ended " + (conf.get("year_end_label") or ""))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/'
            'package/2006/metadata/core-properties" xmlns:dc="http://purl.org/'
            'dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:title>%s</dc:title><dc:subject>%s</dc:subject>'
            '<dc:creator>%s</dc:creator><cp:lastModifiedBy>%s'
            '</cp:lastModifiedBy>'
            '<dcterms:created xsi:type="dcterms:W3CDTF">%s</dcterms:created>'
            '<dcterms:modified xsi:type="dcterms:W3CDTF">%s</dcterms:modified>'
            '</cp:coreProperties>'
            % (xml_escape("Balance confirmation — %s — %s"
                          % (conf.get("party_name"), conf.get("category"))),
               xml_escape("%s of %s — %s"
                          % (conf.get("audit_type", "Statutory Audit"),
                             conf.get("client_name"), span)),
               xml_escape(conf.get("firm_name")),
               xml_escape(conf.get("firm_name")), when, when))


def docx_parts(model, conf, stamp=None):
    return {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": PKG_RELS,
        "docProps/core.xml": core_xml(conf, stamp),
        "docProps/app.xml": APP_XML,
        "word/document.xml": document_xml(model),
        "word/_rels/document.xml.rels": DOC_RELS,
        "word/styles.xml": STYLES_XML,
    }


_PART_ORDER = ["[Content_Types].xml", "_rels/.rels", "word/document.xml",
               "word/_rels/document.xml.rels", "word/styles.xml",
               "docProps/core.xml", "docProps/app.xml"]


def docx_bytes(conf, stamp=None):
    """Build one complete .docx in memory and return it as bytes."""
    parts = docx_parts(build_letter_model(conf), conf, stamp)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in _PART_ORDER:
            archive.writestr(name, parts[name])
    return buffer.getvalue()


# ------------------------------------------------------------- file names
_WINDOWS_RESERVED = re.compile(
    r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])$", re.I)


# ---------------------------------------------------------------- the PDF
# The same letter as a PDF: what is e-mailed to the party, and what the client
# prints on its letterhead.  It is drawn from the same model as the Word file,
# so the two always read alike.
_PDF_FONTS = None
_PDF_FONT_FILES = [
    (r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\calibrib.ttf"),
    ("/Library/Fonts/Microsoft/Calibri.ttf",
     "/Library/Fonts/Microsoft/Calibri Bold.ttf"),
    ("/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
     "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf"),
    (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf",
     "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def _pdf_fonts():
    """Calibri where the computer has it, so the PDF matches the Word letter;
    otherwise the nearest face found, and Helvetica if there is none."""
    global _PDF_FONTS
    if _PDF_FONTS:
        return _PDF_FONTS
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for regular, bold in _PDF_FONT_FILES:
        if os.path.exists(regular) and os.path.exists(bold):
            try:
                pdfmetrics.registerFont(TTFont("BCG-Regular", regular))
                pdfmetrics.registerFont(TTFont("BCG-Bold", bold))
                _PDF_FONTS = ("BCG-Regular", "BCG-Bold")
                return _PDF_FONTS
            except Exception:
                continue
    _PDF_FONTS = ("Helvetica", "Helvetica-Bold")
    return _PDF_FONTS


def _pdf_story(model, size, scale):
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    regular, bold_face = _pdf_fonts()
    single, body_lead = size * 1.20, size * 1.32

    def pt(twips):                       # the Word file measures in twentieths
        return twips / 20.0 * scale

    def para(text, bold=False, align=TA_LEFT, after=0, before=0, lead=single,
             keep=False):
        style = ParagraphStyle(
            "p", fontName=bold_face if bold else regular, fontSize=size,
            leading=lead, alignment=align, spaceAfter=pt(after),
            spaceBefore=pt(before), keepWithNext=1 if keep else 0)
        return Paragraph(xml_escape(text), style)

    story = []
    if model.get("letterhead_note"):
        story.append(para(model["letterhead_note"], align=TA_CENTER, after=40))
    story.append(para(model["title"], bold=True, align=TA_CENTER, after=260,
                      keep=True))
    story.append(para(model["date_line"], align=TA_RIGHT,
                      after=0 if model.get("reference_line") else 60))
    if model.get("reference_line"):
        story.append(para(model["reference_line"], align=TA_RIGHT, after=60))
    last = len(model["party_block"]) - 1
    for i, line in enumerate(model["party_block"]):
        story.append(para(line["text"], bold=line["bold"],
                          after=240 if i == last else 0))
    story.append(para(model["salutation"], after=200))
    for i, text in enumerate(model["paras"]):
        final = i == len(model["paras"]) - 1
        story.append(para(text, align=TA_JUSTIFY, lead=body_lead,
                          after=150 if final else 200, keep=final))
    last = len(model["auditor_block"]) - 1
    for i, line in enumerate(model["auditor_block"]):
        story.append(para(line["text"], bold=line["bold"],
                          after=200 if i == last else 0))
    for text in model["closing_paras"]:
        story.append(para(text, align=TA_JUSTIFY, lead=body_lead, after=200))
    last = len(model["signature"]) - 1
    for i, line in enumerate(model["signature"]):
        story.append(para(line["text"], bold=line["bold"],
                          before=360 if line.get("gap") else 0,
                          after=420 if i == last else 20, keep=i < last))
    story.append(para(model["slip"]["sentence"], align=TA_JUSTIFY,
                      lead=body_lead, after=160, keep=True))
    rows = [[para(label), para(":  ______________________")]
            for label in model["slip"]["rows"]]
    grid = Table(rows, colWidths=[130, 200], hAlign="LEFT",
                 rowHeights=[max(single + 2, 17 * scale)] * len(rows))
    grid.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(grid)
    story.append(Spacer(1, 1))
    return story


def pdf_bytes(conf, top_space_cm=0.0):
    """The letter as a one-page A4 PDF.

    top_space_cm leaves the head of the page clear, for printing on the
    client's own letterhead.  The spacing is tightened step by step until the
    letter, slip included, sits on a single page."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate
    model = build_letter_model(conf)
    compact = model.get("compact")
    margin = (1.8 if compact else 2.0) * cm
    top = (margin if model.get("letterhead_note") else margin * 1.25) \
        + max(0.0, float(top_space_cm or 0)) * cm
    payload = b""
    for size, scale in ((10.5, 0.78 if compact else 1.0), (10.5, 0.62),
                        (10.0, 0.5), (9.5, 0.4), (9.0, 0.3), (8.5, 0.22)):
        buffer = io.BytesIO()
        document = SimpleDocTemplate(
            buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=top, bottomMargin=margin,
            title="%s - %s" % (model["title"].title(),
                               conf.get("party_name", "")),
            author=conf.get("client_name", ""),
            subject="Balance confirmation %s" % (conf.get("reference") or ""),
            creator="Balance Confirmation Generator")
        document.build(_pdf_story(model, size, scale))
        payload = buffer.getvalue()
        if document.page <= 1:
            break
    return payload


def pdf_page_count(payload):
    """Pages in a PDF this application wrote (used by the tests and the
    one-page check)."""
    return len(re.findall(rb"/Type\s*/Page[^s]", payload or b""))


def looks_like_pdf(path):
    try:
        with open(path, "rb") as handle:
            return handle.read(5) == b"%PDF-"
    except Exception:
        return False


def match_signed_pdfs(paths, documents):
    """Tie a folder of signed PDFs to the parties they belong to.

    documents: [{id, party_name, category, reference, filename}].
    A file is linked when its name carries the letter's reference code, or the
    party's name (and the category, where the same party has two letters).
    Returns ({document id: path}, [paths that matched nothing or too much])."""
    def squash(text):
        return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())

    linked, loose = {}, []
    for path in paths:
        stem = os.path.splitext(os.path.basename(path))[0]
        flat = squash(stem)
        # an underscore is a word character, so "scan_BCG-7F3K2A" would hide
        # the code from a whole-word search
        reference = find_reference(stem.replace("_", " "))
        hits = [d for d in documents
                if reference and (d.get("reference") or "").upper() == reference]
        if not hits:
            hits = [d for d in documents
                    if squash(os.path.splitext(d.get("filename", ""))[0])
                    and squash(os.path.splitext(d.get("filename", ""))[0])
                    in flat]
        if not hits:
            hits = [d for d in documents
                    if len(squash(d.get("party_name"))) >= 4
                    and squash(d.get("party_name")) in flat]
            if len(hits) > 1:
                narrowed = [d for d in hits if squash(d.get("category")) in flat]
                hits = narrowed or hits
        if len(hits) == 1 and hits[0]["id"] not in linked:
            linked[hits[0]["id"]] = path
        else:
            loose.append(path)
    return linked, loose


def sanitize_filename(text):
    value = re.sub(r'[\\/:*?"<>|]', " ", str("" if text is None else text))
    value = re.sub(r"[\x00-\x1f\x7f]", "", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    if len(value) > 110:
        value = value[:110].strip()
    if not value:
        value = "Party"
    if _WINDOWS_RESERVED.match(value):
        value += "_"
    return value


def unique_filename(base, extension, used):
    name = base + extension
    key = name.lower()
    counter = 1
    while key in used:
        counter += 1
        name = "%s (%d)%s" % (base, counter, extension)
        key = name.lower()
    used.add(key)
    return name


# ===========================================================================
# SECTION 4 - WORKBOOK READER
# ===========================================================================

SAMPLE_TEMPLATE_NAME = "Balance confirmation - sample template.xlsx"
SAMPLE_COLUMNS = [
    # heading, width, required?, what goes in it
    ("Name", 30, "Required", "The party's legal name, exactly as it should "
                             "read on the letter."),
    ("Address line 1", 46, "Optional", "Building, street, area and city."),
    ("Pincode", 11, "Optional", "Joined to the address on the letter."),
    ("State", 18, "Optional", "Joined to the address on the letter."),
    ("Country", 12, "Optional", "Joined to the address on the letter."),
    ("Currency", 11, "Optional", "Three-letter code such as INR or USD. "
                                 "Blank means the default currency in "
                                 "Settings."),
    ("Closing balance", 20, "Recommended", "The balance as per the client's "
                                           "books at the as-at date, as a "
                                           "plain number. No commas, symbols "
                                           "or Dr/Cr needed."),
    ("Category", 26, "Recommended", "Exactly one of: Trade Receivable, Trade "
                                    "Payable, Advance from Customers, "
                                    "Advance to Vendors. Pick it from the "
                                    "drop-down."),
    ("Email ID", 34, "Needed to e-mail", "Where the confirmation request is "
                                         "to be sent. One address per row."),
    ("Contact person", 24, "Optional", "Printed as 'Kind attention' on the "
                                       "letter."),
]
SAMPLE_ROWS = [
    ("ABC Private Limited", "Unit 12, 10th Road, Vile Parle (East), Mumbai",
     400057, "Maharashtra", "India", "INR", 7960098.48, "Trade Receivable",
     "accounts@abc-example.com", "Mr. A. Shah"),
    ("XYZ Suppliers LLP", "Plot 4, Industrial Estate, Okhla Phase II, "
     "New Delhi", 110020, "Delhi", "India", "INR", 3515723.34,
     "Trade Payable", "finance@xyz-example.com", "Ms. R. Gupta"),
    ("Customer P Limited", "5th Floor, Baner Road, Pune", 411045,
     "Maharashtra", "India", "INR", 500000, "Advance from Customers",
     "payables@customerp-example.com", ""),
    ("Vendor Q Industries", "Survey No. 21, GIDC, Vapi", 396195, "Gujarat",
     "India", "INR", 275000, "Advance to Vendors",
     "receivables@vendorq-example.com", ""),
]


def write_sample_template(path):
    """Write the ready-to-fill party listing the application reads without
    any mapping: the headings are the ones its own detection looks for."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    olive = PatternFill("solid", fgColor="5F7232")
    pale = PatternFill("solid", fgColor="F3F5EA")
    thin = Side(style="thin", color="C9CFB4")
    edge = Border(left=thin, right=thin, top=thin, bottom=thin)

    book = Workbook()
    sheet = book.active
    sheet.title = "Party balances"
    for index, (heading, width, _need, _help) in enumerate(SAMPLE_COLUMNS, 1):
        cell = sheet.cell(row=1, column=index, value=heading)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = olive
        cell.border = edge
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.row_dimensions[1].height = 24
    for r, values in enumerate(SAMPLE_ROWS, 2):
        for c, value in enumerate(values, 1):
            cell = sheet.cell(row=r, column=c, value=value if value != ""
                              else None)
            cell.border = edge
            cell.font = Font(italic=True, color="6E755B")
    for r in range(2, 502):
        sheet.cell(row=r, column=7).number_format = "#,##0.00"
        sheet.cell(row=r, column=3).number_format = "0"
    sheet.freeze_panes = "A2"

    categories = DataValidation(
        type="list", formula1='"%s"' % ",".join(CATEGORIES),
        allow_blank=True, showErrorMessage=True,
        errorTitle="Category",
        error="Choose one of the four categories from the list.")
    currencies = DataValidation(
        type="list", formula1='"INR,USD,EUR,GBP,AED,SGD,JPY,AUD,CAD,CHF"',
        allow_blank=True, showErrorMessage=False)
    sheet.add_data_validation(categories)
    sheet.add_data_validation(currencies)
    categories.add("H2:H501")
    currencies.add("F2:F501")

    guide = book.create_sheet("How to fill")
    guide.column_dimensions["A"].width = 22
    guide.column_dimensions["B"].width = 20
    guide.column_dimensions["C"].width = 96
    guide["A1"] = "Balance Confirmation Generator - party listing template"
    guide["A1"].font = Font(bold=True, size=14, color="5F7232")
    steps = [
        "1.  Fill the 'Party balances' sheet, one party per row. The four "
        "rows in grey italics are examples: overwrite or delete them.",
        "2.  Keep the headings in row 1 as they are. The application "
        "recognises them, so no column mapping is needed.",
        "3.  Enter the closing balance as a plain number, as it stands in "
        "the client's books at the as-at date.",
        "4.  A party with balances in two categories takes two rows, one "
        "for each category.",
        "5.  Save the file, then drop it on 03 Import data in the "
        "application.",
    ]
    for offset, line in enumerate(steps, 3):
        guide.cell(row=offset, column=1, value=line)
        guide.merge_cells(start_row=offset, start_column=1,
                          end_row=offset, end_column=3)
    top = len(steps) + 5
    for c, heading in enumerate(("Column", "Needed?", "What goes in it"), 1):
        cell = guide.cell(row=top, column=c, value=heading)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = olive
        cell.border = edge
    for offset, (heading, _w, need, text) in enumerate(SAMPLE_COLUMNS, 1):
        row = top + offset
        for c, value in enumerate((heading, need, text), 1):
            cell = guide.cell(row=row, column=c, value=value)
            cell.border = edge
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if offset % 2 == 0:
                cell.fill = pale
        guide.cell(row=row, column=1).font = Font(bold=True)
    note = top + len(SAMPLE_COLUMNS) + 2
    guide.cell(row=note, column=1, value="Which category?").font = \
        Font(bold=True)
    meanings = [
        ("Trade Receivable", "The party owes the client (debtor / customer)."),
        ("Trade Payable", "The client owes the party (creditor / supplier)."),
        ("Advance from Customers", "The client has received an advance from "
                                   "the party."),
        ("Advance to Vendors", "The client has paid an advance to the "
                               "party."),
    ]
    for offset, (name, meaning) in enumerate(meanings, 1):
        guide.cell(row=note + offset, column=1, value=name)
        guide.cell(row=note + offset, column=3, value=meaning)
    book.save(path)
    return path


def read_workbook(path):
    """Return {sheet name: grid of rows}.  Nothing is written to the source."""
    lower = path.lower()
    if lower.endswith(".csv") or lower.endswith(".txt"):
        return {"CSV": _read_csv(path)}
    if lower.endswith(".xls"):
        if not HAS_XLRD:
            raise RuntimeError(
                "Reading .xls needs the xlrd library, which is not installed. "
                "Re-save the file as .xlsx, or install it with:\n\n"
                "    %s -m pip install xlrd" % sys.executable)
        import xlrd
        book = xlrd.open_workbook(path)
        sheets = {}
        for sheet in book.sheets():
            sheets[sheet.name] = [[sheet.cell_value(r, c)
                                   for c in range(sheet.ncols)]
                                  for r in range(sheet.nrows)]
        return sheets
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sheets = {}
    try:
        for sheet in workbook.worksheets:
            sheets[sheet.title] = [list(row)
                                   for row in sheet.iter_rows(values_only=True)]
    finally:
        workbook.close()
    return sheets


def _read_csv(path):
    """Read a CSV, coping with the encodings Excel commonly writes."""
    raw = open(path, "rb").read()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    width = max((len(r) for r in rows), default=0)
    return [r + [None] * (width - len(r)) for r in rows]


def trim_grid(grid):
    """Drop trailing blank rows so the row count matches what the user sees."""
    trimmed = list(grid or [])
    while trimmed and not any(clean(c) for c in (trimmed[-1] or [])):
        trimmed.pop()
    return trimmed


# ===========================================================================
# SECTION 5 - E-MAIL COMPOSITION
# ===========================================================================

LEGACY_SUBJECT = "Balance confirmation request as at {date} — {client}"
# the reference rides in the subject, so every reply ("Re: ...") carries
# it back even when the party writes nothing else
DEFAULT_SUBJECT = ("Balance confirmation request as at {date} — {client} "
                   "— Ref {reference}")
DEFAULT_BODY = "\n".join([
    "Dear Sir/Madam,",
    "",
    "We are the auditors of {client} and are carrying out {audittype_article} "
    "of its financial statements {period}.",
    "",
    "Please find attached a balance confirmation request issued by {client} in "
    "respect of the {category} balance appearing in its books as at {date}, "
    "being {amount}.",
    "",
    "Kindly sign the attached letter and e-mail it directly to us at:",
    "{auditors}",
    "",
    "Should the amount not agree with your records, please let us know the "
    "balance as per your books together with particulars of the difference.",
    "",
    "We thank you in advance for your co-operation.",
    "",
    "Yours faithfully,",
    "For {firm}",
    "{designation}",
])

PLACEHOLDERS = ["{party}", "{client}", "{audittype}", "{audittype_article}",
                "{period}", "{category}", "{date}", "{amount}", "{words}",
                "{currency}", "{reference}", "{auditors}", "{firm}",
                "{designation}"]


def fill_template(template, conf):
    label = amount_label(conf.get("amount"), conf.get("currency"))
    team = "\n".join(
        "  " + ((a.get("name") + " — ") if a.get("name") else "")
        + a.get("email", "")
        for a in (conf.get("auditors") or []))
    span = period_phrase(conf.get("basis"),
                         conf.get("as_at") or conf.get("year_end"),
                         conf.get("period_start"))
    if not span and conf.get("year_end_label"):
        span = "for the year ended " + conf["year_end_label"]
    replacements = {
        "{party}": conf.get("party_name", ""),
        "{client}": conf.get("client_name", ""),
        "{audittype}": audit_phrase(conf.get("audit_type"),
                                    conf.get("audit_type_other")),
        "{audittype_article}": engagement_phrase(conf.get("audit_type"),
                                                 conf.get("audit_type_other")),
        "{words}": amount_in_words(conf.get("amount"), conf.get("currency")),
        "{period}": span,
        "{category}": conf.get("category", ""),
        "{date}": conf.get("year_end_label", ""),
        "{amount}": "not available" if label is None else label,
        "{currency}": conf.get("currency", ""),
        "{reference}": conf.get("reference", ""),
        "{firm}": conf.get("firm_name", ""),
        "{designation}": conf.get("firm_designation", ""),
        "{auditors}": team,
    }
    text = str(template or "")
    for token, value in replacements.items():
        text = text.replace(token, value)
    return text


def build_email_message(conf, filename, attachment, options):
    """Compose a complete RFC-5322 message with the letter attached - a PDF
    or a Word file, told apart by the file name."""
    message = EmailMessage()
    sender_name = options.get("sender_name") or ""
    sender = options.get("sender", "")
    message["From"] = formataddr((sender_name, sender)) if sender_name else sender
    message["To"] = conf.get("party_email", "")
    team = [a["email"] for a in (conf.get("auditors") or [])
            if valid_email(a.get("email"))]
    if options.get("cc_team", True) and team:
        message["Cc"] = ", ".join(team)
    if options.get("reply_to_team", True) and team:
        message["Reply-To"] = ", ".join(team)
    message["Subject"] = fill_template(
        options.get("subject") or DEFAULT_SUBJECT, conf)
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()
    # marks the message as our own request: a copy of it reaches the mailbox
    # the bridge reads, and must never be mistaken for the party's reply
    message["X-BCG-Request"] = str(conf.get("reference") or "request")
    message.set_content(fill_template(options.get("body") or DEFAULT_BODY, conf))
    is_pdf = str(filename).lower().endswith(".pdf")
    message.add_attachment(
        attachment, maintype="application",
        subtype="pdf" if is_pdf else
        "vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename)
    return message


SMTP_PRESETS = {
    "Gmail / Google Workspace": ("smtp.gmail.com", 587, "starttls"),
    "Outlook / Microsoft 365":  ("smtp.office365.com", 587, "starttls"),
    "Zoho Mail (India)":        ("smtp.zoho.in", 587, "starttls"),
    "Zoho Mail (global)":       ("smtp.zoho.com", 587, "starttls"),
    "Yahoo Mail":               ("smtp.mail.yahoo.com", 587, "starttls"),
    "Other / in-house server":  ("", 587, "starttls"),
}


def smtp_connect(host, port, security, username, password, timeout=45):
    """Open an authenticated SMTP session.  Raises on failure."""
    context = ssl.create_default_context()
    if security == "ssl":
        server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
    else:
        server = smtplib.SMTP(host, port, timeout=timeout)
        server.ehlo()
        if security == "starttls":
            server.starttls(context=context)
            server.ehlo()
    if username:
        server.login(username, password)
    return server


def friendly_smtp_error(exc):
    """Turn an SMTP exception into something an accountant can act on."""
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return ("The mail server rejected the sign-in. For Gmail, Outlook, "
                "Yahoo and Zoho you must use an app password, not your normal "
                "password, and two-factor authentication must be on.")
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "The server refused the recipient address."
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return ("The server refused the From address. It usually has to match "
                "the account you signed in with.")
    if isinstance(exc, smtplib.SMTPConnectError):
        return "Could not connect to the mail server. Check the host and port."
    if isinstance(exc, (TimeoutError, OSError)) and not isinstance(
            exc, smtplib.SMTPException):
        return ("Could not reach the mail server. Check your internet "
                "connection, the host and port, and any firewall.")
    text = str(exc).strip()
    return text[:300] if text else exc.__class__.__name__


# ===========================================================================
# SECTION 5B - REPLIES, MATCHING AND RECONCILIATION
# ---------------------------------------------------------------------------
# A confirmation is sent, the party replies, and the reply has to be tied back
# to the right party and the confirmed figure read out of it.  Everything in
# this section is pure logic over plain dictionaries, so it works the same
# whether the reply arrived through the Gmail bridge, was pulled from a shared
# sheet, or was keyed in by hand.
#
# Reply record (one per message received):
#   {id, received_at, from_email, from_name, subject, body, thread_id,
#    in_reply_to, reference, attachments:[{name, text}], bounced}
#
# Match result added by match_reply():
#   {matched_document, match_method, match_confidence, client_run}
# ===========================================================================

REFERENCE_PREFIX = "BCG"
REFERENCE_RE = re.compile(r"\b" + REFERENCE_PREFIX + r"-([0-9A-HJ-NP-Z]{6})\b",
                          re.I)
# I, O, 0 and 1 are left out so a code read off a printed page is unambiguous
_REF_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def new_reference():
    """A short code printed in the subject and in the letter, e.g. BCG-7F3K2A."""
    import random
    return REFERENCE_PREFIX + "-" + "".join(
        random.choice(_REF_ALPHABET) for _ in range(6))


def find_reference(*texts):
    for text in texts:
        found = REFERENCE_RE.search(str(text or ""))
        if found:
            return (REFERENCE_PREFIX + "-" + found.group(1)).upper()
    return ""


def _norm_name(text):
    """Fold a party name for comparison: case, punctuation and the usual
    company suffixes all fall away."""
    value = str(text or "").lower()
    value = re.sub(r"[^a-z0-9 ]", " ", value)
    value = re.sub(r"\b(private|pvt|limited|ltd|llp|inc|co|company|and|&|the)\b",
                   " ", value)
    return re.sub(r"\s+", " ", value).strip()


def name_similarity(a, b):
    """0-100.  A token-set ratio, so word order and extra words do not matter.
    Written out rather than pulled from a library to keep the file standalone."""
    first, second = _norm_name(a), _norm_name(b)
    if not first or not second:
        return 0
    if first == second:
        return 100
    one, two = set(first.split()), set(second.split())
    shared = one & two
    if not shared:
        return 0
    # Jaccard over tokens, lifted when one name is wholly inside the other
    score = 100.0 * len(shared) / len(one | two)
    if one <= two or two <= one:
        score = max(score, 92.0)
    return int(round(score))


MATCH_THREAD = "thread"
MATCH_REFERENCE = "reference"
MATCH_SENDER = "sender address"
MATCH_NAME = "party name"
MATCH_DOMAIN = "sender's domain"
MATCH_MANUAL = "assigned by hand"
MATCH_NONE = "unmatched"

# a reply the auditor has marked as not being a confirmation for any party
SET_ASIDE = "__set_aside__"

NAME_MATCH_THRESHOLD = 90

# A shared mail service says nothing about which company a sender works for,
# so only a company's own domain is used as evidence of who replied.
PUBLIC_MAIL_DOMAINS = frozenset((
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.in", "yahoo.in",
    "ymail.com", "rocketmail.com", "outlook.com", "outlook.in", "hotmail.com",
    "hotmail.co.in", "live.com", "live.in", "msn.com", "icloud.com",
    "me.com", "mac.com", "aol.com", "rediffmail.com", "rediff.com",
    "zoho.com", "zohomail.com", "zohomail.in", "protonmail.com", "proton.me",
    "pm.me", "gmx.com", "gmx.net", "mail.com", "yandex.com", "yandex.ru",
    "tutanota.com", "fastmail.com", "hey.com", "sify.com", "vsnl.net",
    "vsnl.com", "bsnl.in", "airtelmail.in", "indiatimes.com"))

_ADDRESS_RE = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_LEGAL_SUFFIX = (r"(?:pvt|private|ltd|limited|llp|inc|co|company|corp|"
                 r"corporation|plc|llc|gmbh|bhd)")
_DROPPED_WORDS = r"(?:and|the|co|company|private|pvt|limited|ltd|llp|inc)"


def addresses_in(text):
    """Every e-mail address in a field, lower-cased.  A party's e-mail cell
    may hold more than one address."""
    return {found.lower().rstrip(".")
            for found in _ADDRESS_RE.findall(str(text or ""))}


def document_key(document):
    return document.get("id") or document.get("filename")


def _party_key(document):
    return _norm_name(document.get("party_name")) or str(document_key(document))


def _message_id(value):
    return str(value or "").strip().strip("<>").strip().lower()


def _fold(text):
    return re.sub(r"\s+", " ",
                  re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())).strip()


def _name_pattern(party_name):
    """A pattern that finds a party's name as a whole phrase.

    'ABC Pvt Ltd' must not be found inside 'ABCD' or in the word 'abc' in
    passing, so a one-word name only counts when a legal suffix follows it
    ('ABC Pvt Ltd', 'ABC Limited').  Longer names count as a phrase."""
    tokens = _norm_name(party_name).split()
    if not tokens:
        return None
    joiner = r"(?:\s+" + _DROPPED_WORDS + r")*\s+"
    phrase = joiner.join(re.escape(token) for token in tokens)
    if len(tokens) == 1:
        phrase += r"(?:\s+" + _DROPPED_WORDS + r")*\s+" + _LEGAL_SUFFIX
    return re.compile(r"\b" + phrase + r"\b")


def parties_named_in(text, documents):
    """{party key: [documents]} for every party whose name is written in the
    text.  Where one name sits inside a longer one ('ABC' within 'ABC
    Exports'), only the longer, more specific name counts."""
    folded = _fold(text)
    if not folded:
        return {}
    spans = {}
    for document in documents:
        pattern = _name_pattern(document.get("party_name"))
        if pattern is None:
            continue
        found = [(m.start(), m.end()) for m in pattern.finditer(folded)]
        if found:
            spans.setdefault(_party_key(document), {"spans": found,
                                                    "documents": []})
            spans[_party_key(document)]["documents"].append(document)
    named = {}
    for key, entry in spans.items():
        inside_longer = all(
            any(other_key != key and o_start <= start and end <= o_end and
                (o_end - o_start) > (end - start)
                for other_key, other in spans.items()
                for o_start, o_end in other["spans"])
            for start, end in entry["spans"])
        if not inside_longer:
            named[key] = entry["documents"]
    return named


def _names_of(documents):
    seen, out = set(), []
    for document in documents:
        name = document.get("party_name") or str(document_key(document))
        if name not in seen:
            seen.add(name)
            out.append(name)
    return ", ".join(out)


def _describe(document):
    category = document.get("category") or ""
    return "%s%s" % (document.get("party_name", ""),
                     " (%s)" % category if category else "")


def assess_reply(reply, documents):
    """Work out which sent confirmation a reply answers, on evidence only.

    Two separate questions are asked of every reply:

      who sent it   - the sender's address registered for a party, the
                      party's name written in the party's OWN words (not in
                      our letter quoted underneath), or a company's own
                      domain;
      what it answers - the request it is a reply to (In-Reply-To or the
                      thread), our reference code, or the returned letter.

    The reply is recorded against a party only when the evidence points to
    exactly one confirmation.  Evidence that disagrees, or no evidence at
    all, sends the reply to the exception queue: it is never given to the
    first party on the list, and the order replies arrive in plays no part.

    Returns {document, method, confidence, basis, note, reason, candidates}.
    """
    result = {"document": None, "method": MATCH_NONE, "confidence": 0.0,
              "basis": "", "note": "", "reason": "", "candidates": ""}
    documents = [d for d in documents if document_key(d)]
    by_key = {document_key(d): d for d in documents}

    # -- the auditor's own decision overrides everything
    assigned = str(reply.get("assigned_to") or "")
    if assigned and assigned != SET_ASIDE:
        document = by_key.get(assigned)
        if document is not None:
            who = str(reply.get("decided_by") or "").strip()
            when = fmt_date_long(str(reply.get("decided_at")
                                     or reply.get("assigned_at") or "")[:10])
            basis = "Accepted%s%s for %s" % (
                " by " + who if who else " by hand",
                " on " + when if when else "", _describe(document))
            if reply.get("decision_note"):
                basis += " - " + str(reply["decision_note"])
            result.update(document=document, method=MATCH_MANUAL,
                          confidence=1.0, basis=basis)
            return result
        result["reason"] = ("Assigned by hand to a confirmation that is no "
                            "longer on record - assign it again")
        return result

    subject = str(reply.get("subject") or "")
    body = str(reply.get("body") or "")
    own_words = strip_quoted(body)
    attachment_texts = [str(a.get("text") or "")
                        for a in (reply.get("attachments") or [])]
    sender = next(iter(sorted(addresses_in(reply.get("from_email")))), "")
    bounced = bool(reply.get("bounced")) or looks_like_bounce(reply)

    # ------------------------------------------------ who sent the reply
    sender_hits = [d for d in documents
                   if sender and sender in addresses_in(d.get("email"))]
    domain_hits = []
    if sender and not sender_hits and not bounced:
        domain = sender.rsplit("@", 1)[-1]
        if domain not in PUBLIC_MAIL_DOMAINS:
            domain_hits = [d for d in documents if any(
                address.rsplit("@", 1)[-1] == domain
                for address in addresses_in(d.get("email")))]
    named = {} if bounced else parties_named_in(
        own_words + "\n" + str(reply.get("from_name") or ""), documents)
    name_hits = [d for docs in named.values() for d in docs]

    identity_signals = []
    if sender_hits:
        identity_signals.append(
            (MATCH_SENDER, {_party_key(d) for d in sender_hits},
             "sent from %s, the address on record for %s"
             % (sender, _names_of(sender_hits))))
    if name_hits:
        identity_signals.append(
            (MATCH_NAME, set(named),
             "the reply names %s in the party's own words"
             % _names_of(name_hits)))
    if domain_hits:
        identity_signals.append(
            (MATCH_DOMAIN, {_party_key(d) for d in domain_hits},
             "sent from the domain %s, used only by %s"
             % (sender.rsplit("@", 1)[-1], _names_of(domain_hits))))

    identity, identity_kind = set(), ""
    if identity_signals:
        identity = set(identity_signals[0][1])
        identity_kind = identity_signals[0][0]
        for _kind, parties, _words in identity_signals[1:]:
            identity &= parties
        if not identity:
            result["reason"] = (
                "The evidence of who replied disagrees: %s - decide which "
                "party this reply belongs to"
                % "; ".join(words for _k, _p, words in identity_signals))
            result["candidates"] = _names_of(
                [d for _k, parties, _w in identity_signals
                 for d in documents if _party_key(d) in parties])
            return result
    identity_words = "; ".join(words for _k, _p, words in identity_signals)

    # ------------------------------------------- which letter it answers
    letter, letter_words = {}, []

    def note_letter(found, kind, words):
        for document in found:
            letter.setdefault(document_key(document), (document, kind))
        if found:
            letter_words.append(words % _names_of(found))

    thread = str(reply.get("thread_id") or "").strip()
    parent = _message_id(reply.get("in_reply_to"))
    by_thread = [d for d in documents
                 if (thread and str(d.get("thread_id") or "") == thread) or
                 (parent and _message_id(d.get("message_id")) == parent)]
    note_letter(by_thread, MATCH_THREAD,
                "it is a reply to the request sent to %s")

    explicit_codes = set()
    for text in [subject, own_words] + attachment_texts:
        explicit_codes |= {(REFERENCE_PREFIX + "-" + m).upper()
                           for m in REFERENCE_RE.findall(text)}
    by_code = [d for d in documents
               if str(d.get("reference") or "").upper() in explicit_codes]
    note_letter(by_code, MATCH_REFERENCE,
                "it carries the reference code of the letter to %s")

    strong_letter = dict(letter)
    if not strong_letter:
        # weaker: a code only in the quoted text, the party named on the
        # returned letter, or the failed address inside a bounce
        quoted_codes = {(REFERENCE_PREFIX + "-" + m).upper()
                        for m in REFERENCE_RE.findall(body)}
        if reply.get("reference"):
            quoted_codes.add(str(reply["reference"]).upper())
        by_quoted = [d for d in documents
                     if str(d.get("reference") or "").upper() in quoted_codes]
        note_letter(by_quoted, MATCH_REFERENCE,
                    "the letter to %s is quoted in it")
        on_letter = parties_named_in("\n".join(attachment_texts), documents)
        if len(on_letter) == 1:
            note_letter(list(on_letter.values())[0], MATCH_NAME,
                        "the returned letter is addressed to %s")
        if bounced:
            failed = addresses_in(body)
            note_letter([d for d in documents
                         if addresses_in(d.get("email")) & failed],
                        MATCH_THREAD, "the failed address is the one for %s")

    def choose(document, method, confidence, basis, note=""):
        result.update(document=document, method=method,
                      confidence=confidence, basis=basis, note=note)
        return result

    def basis_of(*parts):
        text = "; ".join(p for p in parts if p)
        return text[:1].upper() + text[1:]

    letter_text = "; ".join(letter_words)

    if identity:
        candidates = [d for d in documents if _party_key(d) in identity]
        if letter:
            within = [d for d in candidates if document_key(d) in letter]
            if len(within) == 1:
                document = within[0]
                method = letter[document_key(document)][1]
                if method == MATCH_NAME:
                    method = identity_kind
                return choose(document, method, 0.97,
                              basis_of(identity_words, letter_text))
            if len(within) > 1:
                result["reason"] = (
                    "The reply could answer more than one confirmation for "
                    "%s (%s) - decide which" % (_names_of(within), ", ".join(
                        d.get("category", "") for d in within)))
                result["candidates"] = "; ".join(_describe(d) for d in within)
                return result
            # who replied and what they replied to point to different parties
            others = [entry[0] for entry in letter.values()]
            parties_in_identity = {_party_key(d) for d in candidates}
            # The sender's own registered address is the one thing that says
            # who is speaking; a reply-all on another party's request says
            # only which e-mail they pressed Reply on.
            if identity_kind == MATCH_SENDER and len(candidates) == 1 and \
                    len(parties_in_identity) == 1:
                document = candidates[0]
                return choose(
                    document, MATCH_SENDER, 0.80,
                    basis_of(identity_words, letter_text),
                    note=("Sent from the address on record for %s, but as a "
                          "reply to the request sent to %s; recorded against "
                          "%s - confirm before relying on it"
                          % (document.get("party_name", ""),
                             _names_of(others),
                             document.get("party_name", ""))))
            result["reason"] = ("Who replied (%s) and what the reply answers "
                                "(%s) point to different parties - decide "
                                "which" % (identity_words, letter_text))
            result["candidates"] = _names_of(candidates + others)
            return result
        if len(candidates) == 1:
            confidence = {MATCH_SENDER: 0.92, MATCH_NAME: 0.75,
                          MATCH_DOMAIN: 0.72}.get(identity_kind, 0.7)
            return choose(candidates[0], identity_kind, confidence,
                          basis_of(identity_words))
        if len({_party_key(d) for d in candidates}) == 1:
            result["reason"] = (
                "%s has %d confirmations (%s) and the reply does not show "
                "which one it answers" % (
                    candidates[0].get("party_name", ""), len(candidates),
                    ", ".join(d.get("category", "") for d in candidates)))
        else:
            result["reason"] = ("The reply could be from more than one party "
                                "(%s) - decide which" % identity_words)
        result["candidates"] = "; ".join(_describe(d) for d in candidates)
        return result

    if len(letter) == 1:
        document, kind = list(letter.values())[0]
        confidence = 0.95 if strong_letter else 0.80
        if kind == MATCH_NAME:
            confidence = 0.70
        return choose(document, kind, confidence, basis_of(letter_text))
    if len(letter) > 1:
        result["reason"] = ("The reply points to more than one letter (%s) "
                            "- decide which" % letter_text)
        result["candidates"] = "; ".join(
            _describe(entry[0]) for entry in letter.values())
        return result

    result["reason"] = (
        "Nothing in the reply shows which party sent it: the sender's "
        "address is not on the party list, it is not a reply to one of the "
        "requests sent, and it carries no reference code or party name")
    return result


def match_reply(reply, documents):
    """Tie one reply to one sent confirmation.

    Returns (document or None, method, confidence 0-1).  See assess_reply
    for the evidence used and for why a reply may be left unmatched."""
    found = assess_reply(reply, documents)
    return found["document"], found["method"], found["confidence"]


# ------------------------------------------------------- reading the figure
# The slip the party completes reads:
#   "We hereby confirm that the amount payable by us to <client> as on
#    <date> is <CCY> ______________"
# and the letter above it STATES the client's own figure ("According to our
# records, the amount due from you ... is INR 35,00,000.00").  So a figure
# equal to the books proves nothing by itself: it may simply be our own
# letter coming back.  Every figure in the reply is therefore collected, and
# one that differs from the books always outranks an echo of the figure sent.
_CCY = r"(?:INR|USD|EUR|GBP|AED|SGD|AUD|CAD|JPY|CHF|Rs\.?|₹|\$|€|£)"
_FIGURE_RE = re.compile(
    r"(?P<ccy>" + _CCY + r")?[ \t]*"
    r"(?P<num>\(?-?\d(?:[\d,.]*\d)?\)?)"
    r"(?P<scale>[ \t]*(?:lakhs?|lacs?|crores?|millions?|thousands?)\b)?",
    re.I)
_SCALES = {"lakh": 1e5, "lac": 1e5, "crore": 1e7, "million": 1e6,
           "thousand": 1e3}
_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep",
           "oct", "nov", "dec")
_KEYWORDS = ("balance", "amount", "outstanding", "payable", "receivable",
             "our books", "our records", "our ledger", "confirm", "advance",
             "due ")
_CONNECTOR_RE = re.compile(
    r"(?:\bis\b|\bof\b|\bbeing\b|\bwas\b|\bas\b|\bto be\b|\bshows?\b|"
    r"\bstands at\b|\bcomes to\b|[:=\-–])\s*$", re.I)
_SLIP_BEFORE_RE = re.compile(r"we\s+hereby\s+confirm[\s\S]{0,240}$", re.I)

# "as per our books" is deliberately absent: it introduces the party's own
# figure as often as it signals agreement
AGREE_WORDS = ["agree", "agreed", "in agreement", "confirmed", "confirm the "
               "balance", "tally", "tallies", "matches", "is correct"]
DISAGREE_WORDS = ["not in agreement", "do not agree", "does not agree",
                  "don't agree", "disagree", "difference", "differs",
                  "mismatch", "not tally", "does not tally", "discrepancy",
                  "not correct", "incorrect", "not matching", "does not match",
                  "do not match"]

BOUNCE_MARKERS = ["mailer-daemon", "postmaster", "delivery status "
                  "notification", "undeliverable", "address not found",
                  "delivery has failed", "returned to sender"]


def looks_like_bounce(reply):
    blob = " ".join([str(reply.get("from_email") or ""),
                     str(reply.get("from_name") or ""),
                     str(reply.get("subject") or ""),
                     str(reply.get("body") or "")]).lower()
    return any(marker in blob for marker in BOUNCE_MARKERS)


def strip_quoted(text):
    """The party's own words: the reply with the quoted original removed.

    A reply normally carries our covering e-mail underneath it, and that
    e-mail states the client's figure.  Read as the party's words, it would
    'confirm' the balance on its own."""
    text = str(text or "").replace("\r\n", "\n")
    cut = re.search(r"^[ \t>]*On\b[^\n]{0,240}(?:\n[^\n]{0,120})?\bwrote:[ \t]*$",
                    text, re.I | re.M)
    if cut:
        text = text[:cut.start()]
    kept = []
    for line in text.split("\n"):
        bare = line.strip()
        if bare.startswith(">"):
            continue
        if re.match(r"^-{2,}\s*(original|forwarded) message\s*-{2,}", bare,
                    re.I):
            break
        if re.match(r"^_{10,}$", bare):                    # Outlook divider
            break
        if kept and re.match(r"^from:\s.+", bare, re.I):   # Outlook header
            break
        kept.append(line)
    return "\n".join(kept).strip()


def _alone_on_line(blob, match):
    """True when a figure is all there is on its line (bar 'Rs', '/-',
    'only' and punctuation)."""
    line_start = blob.rfind("\n", 0, match.start()) + 1
    line_end = blob.find("\n", match.end())
    line = blob[line_start:line_end if line_end >= 0 else len(blob)]
    rest = line.replace(match.group(0), " ", 1)
    rest = re.sub(r"(?i)\b(rs|inr|only|rupees)\b|[\s./\-:=*₹]", "", rest)
    return rest == ""


_WELL_FORMED_RE = re.compile(
    r"^\(?-?(?:\d{1,2}(?:,\d{2})*,\d{3}|\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d{1,2})?\)?$")


def _doubtful_reading(blob, start, end, raw, digits, scale):
    """True when OCR has plainly not read a figure whole.

    Handwriting comes back broken - '25, 00,0.00' for 25,00,000 - and the
    first fragment on its own would be recorded as 25.  A figure is trusted
    only if it is grouped like one and nothing figure-like hangs off it."""
    if not _WELL_FORMED_RE.match(raw):
        return True
    if re.match(r"^\s*[,.]\s*\d|^\s+\d", blob[end:end + 6]):
        return True                       # more digits follow after a gap
    if re.search(r"\d\s*[,.]\s+$|\d\s+[,.]\s*$", blob[max(0, start - 4):start]):
        return True                       # it is the tail of a broken figure
    if len(digits) < 4 and not scale:
        return True                       # '25' is not a balance
    return False


def find_figures(text, source, strict=False):
    """Every monetary figure in a piece of text, with how it was recognised.

    Returns [{amount, currency, confidence, source, kind, note}].  A bare
    number is only accepted where the wording around it says it is a balance;
    dates, pincodes and telephone numbers are left alone."""
    blob = re.sub(r"[ \t]+", " ", str(text or ""))
    found = []
    for match in _FIGURE_RE.finditer(blob):
        raw = match.group("num")
        start, end = match.start("num"), match.end("num")
        lead = blob[max(0, match.start() - 260):match.start()]
        after = blob[end:end + 14].lower()
        symbol = (match.group("ccy") or "").strip()
        scale = (match.group("scale") or "").strip().lower()
        digits = re.sub(r"\D", "", raw)

        # --- things that are not money
        if re.match(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$", raw):   # 31.03.2026
            continue
        if not symbol and start > 1 and blob[start - 1] in "/-.@#" and \
                blob[start - 2].isalnum():                        # 31/03, BCG-7
            continue
        # "25,00,000/-" is how a rupee figure is commonly written, so a
        # trailing "/-" is money; any other slash is a date or a fraction
        if (after[:1] == "/" and not after.startswith("/-")) or \
                after[:1] in ("%", "@") or re.match(r"^-\d", after):
            continue
        if after.strip()[:3] in _MONTHS and len(digits) <= 2:     # 31 March
            continue
        if lead.rstrip().lower()[-3:] in _MONTHS or re.search(
                r"(january|february|march|april|june|july|august|september|"
                r"october|november|december)\s*,?\s*$", lead, re.I):
            if len(digits) <= 4 and "," not in raw:               # March 2026
                continue
        if not symbol and start and blob[start - 1].isalpha():    # ABC123
            continue
        if not symbol and re.match(r"^[a-z]", after):             # 10th road
            continue

        if not symbol and "," not in raw and re.match(r"^[6-9]\d{9}$", raw):
            continue                                              # a mobile

        grouped = bool(re.match(r"^\(?-?\d{1,3}(,\d{2,3})+(\.\d+)?\)?$", raw))
        marked = bool(symbol) or grouped or bool(scale)
        nearby = lead[-90:].lower()

        if _SLIP_BEFORE_RE.search(lead) and \
                re.search(r"\bis\b[\s:]*$", lead):
            kind, confidence = "slip", 0.95
        elif any(word in nearby for word in _KEYWORDS) and (
                marked or (5 <= len(digits) <= 12 and
                           _CONNECTOR_RE.search(lead[-40:]))):
            kind, confidence = "statement", 0.80
        elif symbol and (grouped or scale or len(digits) >= 4):
            kind, confidence = "figure", 0.60
        elif grouped and len(digits) >= 5 and _alone_on_line(blob, match):
            # a reply that is nothing but a figure: weak, but it is the
            # party's own, and a differing one must not be lost
            kind, confidence = "figure", 0.55
        else:
            continue

        value, currency_from_text, note = parse_amount(raw)
        if value is None:
            continue
        for word, factor in _SCALES.items():
            if scale.startswith(word):
                value *= factor
                break
        found.append({
            "amount": value,
            "currency": (currency_from_text or _CURRENCY_FROM_SYMBOL.get(
                symbol.upper().rstrip("."), "")),
            "confidence": confidence, "source": source, "kind": kind,
            "note": note or "",
            "doubtful": bool(strict and _doubtful_reading(
                blob, start, end, raw, digits, scale)),
            "seen": blob[start:end + 12].split("\n")[0].strip(),
        })
    return found


def extract_confirmation(reply, books=None, tolerance=1.0):
    """Read the confirmed figure and the party's stance out of a reply.

    books is the figure our letter carried.  When it is known, a figure in
    the reply that DIFFERS from it is the party's own and always wins; a
    figure that merely repeats it counts as agreement only if the party has
    not said otherwise.

    Returns {amount, currency, confidence, source, stance, confirmed_on,
             signed, note}.  A None amount means nothing could be relied on,
            which sends the reply to the exception queue rather than guessing.
    """
    result = {"amount": None, "currency": "", "confidence": 0.0,
              "source": "", "stance": "", "confirmed_on": "",
              "signed": False, "note": "", "method": ""}

    if reply.get("accepted_amount") is not None:
        # the reviewer read the reply and accepted this figure: it is used
        # exactly, and the trail says who accepted it
        result.update(amount=float(reply["accepted_amount"]), confidence=1.0,
                      source="accepted by %s" % (reply.get("decided_by")
                                                 or "the reviewer"),
                      method="accepted by hand")
        return result

    own_words = strip_quoted(reply.get("body", ""))
    candidates = []
    # the attachment is the signed slip, so it is read before the covering note
    for attachment in (reply.get("attachments") or []):
        by_ocr = "OCR" in str(attachment.get("method") or "")
        for figure in find_figures(attachment.get("text", ""),
                                   attachment.get("name", "attachment"),
                                   strict=by_ocr):
            figure["method"] = attachment.get("method", "")
            candidates.append(figure)
    candidates += find_figures(own_words, "email body")

    # A figure OCR could not read whole is never used.  Nor is one that is
    # out of all proportion to the balance asked about: that is a misread
    # digit or a telephone number, not a confirmation.
    for figure in candidates:
        if "OCR" in str(figure.get("method") or "") and books and \
                not figure["doubtful"]:
            ratio = abs(figure["amount"]) / abs(books)
            if ratio < 0.01 or ratio > 100:
                figure["doubtful"] = True
    doubtful = [c for c in candidates if c.get("doubtful")]
    candidates = [c for c in candidates if not c.get("doubtful")]

    lowered = own_words.lower()
    if any(word in lowered for word in DISAGREE_WORDS):
        result["stance"] = "not in agreement"
    elif any(word in lowered for word in AGREE_WORDS):
        result["stance"] = "agreed"

    chosen = None
    if candidates and books is not None:
        differing = [c for c in candidates
                     if abs(c["amount"] - books) > tolerance]
        if differing:
            # the party's own covering words outrank a figure on a document,
            # because the document may carry our pre-printed amount as well
            differing.sort(key=lambda c: (c["source"] == "email body",
                                          c["confidence"]), reverse=True)
            chosen = dict(differing[0])
            chosen["note"] = "Party states a figure different from the letter"
        elif result["stance"] == "not in agreement":
            result["note"] = ("Party says the balance is not in agreement but "
                              "gives no figure of its own")
        else:
            # Every figure found equals the books.  That is the party's own
            # confirmation only if it sits on the completed slip or in the
            # party's own words; the same figure in the body of the returned
            # letter is merely our own statement coming back.
            own = [c for c in candidates
                   if c["kind"] == "slip" or c["source"] == "email body"]
            if own:
                chosen = max(own, key=lambda c: c["confidence"])
            elif result["stance"] == "agreed":
                chosen = dict(max(candidates, key=lambda c: c["confidence"]))
                chosen["confidence"] = min(chosen["confidence"], 0.70)
                chosen["note"] = ("Party's covering words agree; the figure "
                                  "is the one stated in the letter")
            else:
                result["note"] = ("The letter came back, but the figure the "
                                  "party entered on the slip could not be "
                                  "read - open the reply")
    elif candidates:
        chosen = max(candidates, key=lambda c: c["confidence"])

    # The slip holds something OCR could not make out.  Unless the party has
    # stated its figure in its own words, that is for a person to read.
    unread_slip = [c for c in doubtful if c["kind"] == "slip"]
    if doubtful and (chosen is None or
                     (unread_slip and chosen["source"] != "email body")):
        seen = (unread_slip or doubtful)[0]
        chosen = None
        result["note"] = ("A figure is written on %s but could not be read "
                          "with certainty (OCR saw \"%s\") - open the "
                          "document" % (seen["source"], seen["seen"]))

    if chosen:
        result["method"] = chosen.get("method", "")
        result.update({"amount": chosen["amount"],
                       "currency": chosen["currency"],
                       "confidence": chosen["confidence"],
                       "source": chosen["source"],
                       "note": chosen.get("note", "")})
        if result["stance"] == "not in agreement":
            result["confidence"] = max(0.0, result["confidence"] - 0.05)

    blob = " ".join([str(reply.get("body") or "")] +
                    [str(a.get("text") or "")
                     for a in (reply.get("attachments") or [])]).lower()
    found_date = re.search(r"as on\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4}"
                           r"|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})", blob, re.I)
    if found_date:
        result["confirmed_on"] = iso_date(found_date.group(1))

    if re.search(r"\b(signed|signature|authorised signatory|"
                 r"authorized signatory|stamp|seal)\b", blob):
        result["signed"] = True
        if result["amount"] is not None:
            result["confidence"] = min(1.0, result["confidence"] + 0.02)

    return result


def is_own_request(reply, documents, own_addresses=()):
    """True when a 'reply' is really our own outgoing request.

    The request is copied to the engagement team, so it lands in the very
    mailbox the bridge reads - carrying a letter that states the client's own
    figure.  Counted as a reply it would 'agree' every balance by itself."""
    if reply.get("own_request"):
        return True
    message_id = str(reply.get("message_id") or "").strip()
    if message_id and any(str(d.get("message_id") or "").strip() == message_id
                          for d in documents):
        return True
    sender = str(reply.get("from_email") or "").strip().lower()
    own = {str(a or "").strip().lower() for a in own_addresses if a}
    if sender and sender in own:
        subject = str(reply.get("subject") or "").strip().lower()
        answered = bool(str(reply.get("in_reply_to") or "").strip()) or \
            bool(re.match(r"^(re|fw|fwd)\s*:", subject))
        if not answered:
            return True
    return False


_CURRENCY_FROM_SYMBOL = {"RS": "INR", "₹": "INR", "$": "USD",
                         "€": "EUR", "£": "GBP", "INR": "INR",
                         "USD": "USD", "EUR": "EUR", "GBP": "GBP",
                         "AED": "AED", "SGD": "SGD", "AUD": "AUD",
                         "CAD": "CAD", "JPY": "JPY", "CHF": "CHF"}


# -------------------------------------------------------- reconciliation
STATUS_AGREED = "Matched"
STATUS_VARIANCE = "Mismatch"
STATUS_PENDING = "Pending"
STATUS_RETURNED = "Returned"
STATUS_REVIEW = "Needs Review"
STATUS_NOT_SENT = "Not sent"

STATUS_ORDER = [STATUS_VARIANCE, STATUS_REVIEW, STATUS_RETURNED,
                STATUS_PENDING, STATUS_AGREED, STATUS_NOT_SENT]

DEFAULT_TOLERANCE = 1.0          # INR; a rounding difference is not a variance
DEFAULT_REMINDERS = (15, 30, 45)  # days after sending


def days_between(earlier, later=None):
    start = to_date(earlier)
    if not start:
        return None
    end = to_date(later) if later else date.today()
    return (end - start).days


def reminder_stage(age_days, stages=DEFAULT_REMINDERS):
    """Which reminder is due for a confirmation this old (0 = none yet)."""
    if age_days is None:
        return 0
    due = 0
    for index, threshold in enumerate(sorted(stages), start=1):
        if age_days >= threshold:
            due = index
    return due


def reconcile(document, reply=None, tolerance=DEFAULT_TOLERANCE,
              reminders=DEFAULT_REMINDERS, today=None):
    """Compare one sent confirmation with the reply received for it.

    The sign convention is already handled by the letter wording: whatever the
    category, the party confirms the same balance the client has recorded, so
    the two figures are compared directly and never reversed.
    """
    books = document.get("amount")
    currency = document.get("currency") or ""
    sent_on = document.get("sent_at") or document.get("generated_at")
    age = days_between(sent_on, today)

    row = {
        "document_id": document.get("id") or document.get("filename"),
        "party_name": document.get("party_name", ""),
        "category": document.get("category", ""),
        "email": document.get("email", ""),
        "reference": document.get("reference", ""),
        "filename": document.get("filename", ""),
        "currency": currency,
        "books_amount": books,
        "confirmed_amount": None,
        "variance": None,
        "variance_pct": None,
        "status": STATUS_PENDING,
        "delivery": str(document.get("email_status") or "not sent"),
        "sent_at": sent_on or "",
        "received_at": "",
        "age_days": age,
        "reminder_stage": 0,
        "match_method": "",
        "match_confidence": 0.0,
        "extract_confidence": 0.0,
        "extract_source": "",
        "stance": "",
        "signed": False,
        "message_link": "",
        "note": "",
        # the trail from request to recorded figure, kept on every row
        "reply_id": "",
        "reply_from": "",
        "reply_subject": "",
        "match_basis": "",
        "replies_count": 0,
        "reply_ids": "",
        "reply_name": "",
        "decided_by": "",
        "decided_at": "",
        "decision_note": "",
    }

    delivery = str(document.get("email_status") or "").lower()
    if delivery in ("", "not sent"):
        row["status"] = STATUS_NOT_SENT
        row["note"] = "Letter produced but not e-mailed"
        return row
    if delivery == "failed":
        row["status"] = STATUS_RETURNED
        row["note"] = "Delivery failed"
        return row

    if reply is None:
        row["reminder_stage"] = reminder_stage(age, reminders)
        return row

    row["received_at"] = reply.get("received_at", "")
    row["match_method"] = reply.get("match_method", "")
    row["match_confidence"] = reply.get("match_confidence", 0.0)
    row["message_link"] = reply.get("message_link", "")
    row["reply_id"] = reply.get("id", "")
    row["reply_from"] = reply.get("from_email", "")
    row["reply_subject"] = reply.get("subject", "")
    row["match_basis"] = reply.get("match_basis", "")
    row["reply_name"] = reply.get("from_name", "")
    row["decided_by"] = reply.get("decided_by", "")
    row["decided_at"] = reply.get("decided_at", "")
    row["decision_note"] = reply.get("decision_note", "")

    if reply.get("bounced") or looks_like_bounce(reply):
        row["status"] = STATUS_RETURNED
        row["note"] = "Mail returned undelivered"
        return row

    # always read against the figure our letter carried: the letter coming
    # back must not be mistaken for the party's own confirmation
    extraction = extract_confirmation(reply, books, tolerance)
    row["extract_confidence"] = extraction.get("confidence", 0.0)
    row["extract_source"] = extraction.get("source", "")
    row["stance"] = extraction.get("stance", "")
    row["signed"] = extraction.get("signed", False)
    if extraction.get("currency"):
        row["currency"] = extraction["currency"]

    confirmed = extraction.get("amount")
    if confirmed is None:
        row["status"] = STATUS_REVIEW
        row["note"] = extraction.get("note") or \
            "Reply received but no amount could be read"
        if reply.get("files_error"):
            row["note"] += " - attachment not read: " + \
                str(reply["files_error"])[:160]
        elif reply_has_unread_files(reply):
            row["note"] += " - it has a PDF or scan that has not been read " \
                           "yet (Read attached PDFs)"
        return row

    row["confirmed_amount"] = confirmed
    if books is None:
        row["status"] = STATUS_REVIEW
        row["note"] = "No balance on record to compare with"
        return row

    variance = confirmed - books
    row["variance"] = variance
    row["variance_pct"] = (abs(variance) / abs(books) * 100.0) if books else None
    if abs(variance) <= tolerance:
        row["status"] = STATUS_AGREED
        row["note"] = "Agrees with the books"
    else:
        row["status"] = STATUS_VARIANCE
        row["note"] = "Party confirms %s the books by %s" % (
            "less than" if variance < 0 else "more than",
            fmt_amount(abs(variance), row["currency"]) or abs(variance))
    if "OCR" in str(extraction.get("method") or ""):
        # how the figure was obtained travels with it into every report
        row["note"] += " (read by OCR from %s - check against the document)" \
            % (row["extract_source"] or "the attachment")
    if reply.get("match_note"):
        row["note"] += ". " + reply["match_note"]
    return row


EXCEPTION_UNMATCHED = "unmatched"      # no party could be identified
EXCEPTION_CONFLICT = "conflict"        # replies for one party disagree
EXCEPTION_UNREADABLE = "unreadable"    # matched, but no figure to rely on
EXCEPTION_LEFTOVER = "leftover"        # undecided after another was accepted


def _exception(reason, reply, extraction=None, candidates="",
               party="", kind=EXCEPTION_UNMATCHED, document=None):
    extraction = extraction or {}
    return {
        "kind": kind,
        "reason": reason,
        "from_email": reply.get("from_email", ""),
        "from_name": reply.get("from_name", ""),
        "subject": reply.get("subject", ""),
        "received_at": reply.get("received_at", ""),
        "amount": extraction.get("amount"),
        "currency": extraction.get("currency", ""),
        "confidence": extraction.get("confidence", 0.0),
        "candidates": candidates,
        "party": party,
        "document_id": document_key(document) if document else "",
        "evidence": reply.get("match_basis", ""),
        "reply_id": reply.get("id", ""),
        "message_link": reply.get("message_link", ""),
        "suggested_to": "",
        "suggestion": "",
        "review": "Review",
    }


def suggest_party(entry, documents, tolerance=DEFAULT_TOLERANCE):
    """A match to OFFER the reviewer - never applied without them.

    Returns (document id or "", reason).  The requested balance is itself a
    detail of the request: a reply whose figure is exactly the balance asked
    of one party, and of no other, most likely answers that request."""
    amount = entry.get("amount")
    if amount is not None:
        same = [d for d in documents if d.get("amount") is not None and
                abs(abs(d["amount"]) - abs(amount)) <= tolerance]
        if len(same) == 1:
            return document_key(same[0]), (
                "the figure in the reply equals the balance requested from "
                "%s" % same[0].get("party_name", ""))
    if entry.get("kind") == EXCEPTION_UNREADABLE and entry.get("document_id"):
        return entry["document_id"], (
            "it was matched to %s; only the figure needs your reading"
            % entry.get("party", ""))
    return "", ""


def _arrival(reply):
    return (str(reply.get("received_at") or ""), str(reply.get("id") or ""))


def settle_replies(matched, tolerance=DEFAULT_TOLERANCE):
    """Choose the reply that stands for one confirmation.

    Returns (reply or None, conflict, leftover).

    conflict is a sentence when the replies matched to the party give
    different figures: that is for the reviewer to decide, so neither figure
    is used.  A later reply never silently replaces an earlier one.

    leftover lists replies matched automatically whose figure differs from
    the one the reviewer accepted: they stay in the exception queue until
    each is given to another party or set aside."""
    if not matched:
        return None, "", []
    by_hand = [r for r in matched if r.get("match_method") == MATCH_MANUAL]
    pool = by_hand or list(matched)
    answers = [r for r in pool
               if not (r.get("bounced") or looks_like_bounce(r))]
    if not answers:
        return max(pool, key=_arrival), "", []
    readable = [r for r in answers
                if (r.get("extraction") or {}).get("amount") is not None]
    if not readable:
        return max(answers, key=_arrival), "", []
    first = readable[0]["extraction"]["amount"]
    if all(abs(r["extraction"]["amount"] - first) <= tolerance
           for r in readable):
        chosen = max(readable, key=_arrival)
        leftover = []
        if by_hand:
            leftover = [
                r for r in matched
                if r.get("match_method") != MATCH_MANUAL
                and not (r.get("bounced") or looks_like_bounce(r))
                and (r.get("extraction") or {}).get("amount") is not None
                and abs(r["extraction"]["amount"] - first) > tolerance]
        return chosen, "", sorted(leftover, key=_arrival)
    readable.sort(key=_arrival)
    parts = ["%s on %s from %s" % (
        fmt_amount(r["extraction"]["amount"],
                   r["extraction"].get("currency") or "INR")
        or r["extraction"]["amount"],
        fmt_date_long(str(r.get("received_at") or "")[:10])
        or r.get("received_at") or "an unknown date",
        r.get("from_email") or "an unknown sender") for r in readable]
    return max(readable, key=_arrival), (
        "%d replies matched to this party give different figures (%s) - "
        "decide which one counts" % (len(readable), "; ".join(parts))), []


def build_reconciliation(documents, replies, tolerance=DEFAULT_TOLERANCE,
                         reminders=DEFAULT_REMINDERS, today=None,
                         own_addresses=(), ignored=None, set_aside=None):
    """Match every reply, then reconcile every sent confirmation.

    Returns (rows, exceptions).  Exceptions are replies that could not be tied
    to a party on the evidence, replies whose evidence disagrees, replies
    that disagree with one another, and replies whose figure could not be
    read - they are never folded into the numbers silently.
    """
    by_document, exceptions = {}, []

    for reply in replies:
        if is_own_request(reply, documents, own_addresses):
            if ignored is not None:          # our own letter, not an answer
                ignored.append(reply)
            continue
        if reply.get("assigned_to") == SET_ASIDE:
            if set_aside is not None:        # the reviewer said: not a reply
                set_aside.append(reply)
            continue
        found = assess_reply(reply, documents)
        document = found["document"]
        enriched = dict(reply)
        enriched["match_method"] = found["method"]
        enriched["match_confidence"] = found["confidence"]
        enriched["match_basis"] = found["basis"]
        enriched["match_note"] = found["note"]
        enriched["extraction"] = extract_confirmation(
            reply, document.get("amount") if document else None, tolerance)
        if document is None:
            exceptions.append(_exception(
                found["reason"] or "Sender could not be matched to a party",
                enriched, enriched["extraction"], found["candidates"]))
            continue
        by_document.setdefault(document_key(document), []).append(enriched)

    rows = []
    for document in documents:
        key = document_key(document)
        matched = by_document.get(key, [])
        chosen, conflict, leftover = settle_replies(matched, tolerance)
        row = reconcile(document, chosen, tolerance, reminders, today)
        row["replies_count"] = len(matched)
        row["reply_ids"] = ", ".join(str(r.get("id") or "")
                                     for r in sorted(matched, key=_arrival))
        rows.append(row)
        if conflict:
            row.update(status=STATUS_REVIEW, confirmed_amount=None,
                       variance=None, variance_pct=None, note=conflict,
                       extract_confidence=0.0, extract_source="")
            for reply in sorted(matched, key=_arrival):
                exceptions.append(_exception(
                    "Replies matched to %s disagree - decide which one "
                    "counts" % row["party_name"], reply,
                    reply.get("extraction"), row["party_name"],
                    row["party_name"], EXCEPTION_CONFLICT, document))
        elif row["status"] == STATUS_REVIEW and chosen:
            exceptions.append(_exception(
                row["note"] or STATUS_REVIEW, chosen,
                {"amount": chosen.get("extraction", {}).get("amount"),
                 "currency": row["currency"],
                 "confidence": chosen.get("extraction", {}).get(
                     "confidence", 0.0)},
                row["party_name"], row["party_name"],
                EXCEPTION_UNREADABLE, document))
        for reply in leftover:
            exceptions.append(_exception(
                "The confirmation for %s has been accepted from another "
                "reply (%s). This reply gives a different figure and is "
                "still undecided - give it to the party it belongs to, or "
                "set it aside" % (
                    row["party_name"],
                    fmt_amount(row["confirmed_amount"], row["currency"])
                    or row["confirmed_amount"]),
                reply, reply.get("extraction"), "", "",
                EXCEPTION_LEFTOVER, document))

    names = {document_key(d): d.get("party_name", "") for d in documents}
    for entry in exceptions:
        entry["suggested_to"], entry["suggestion"] = suggest_party(
            entry, documents, tolerance)
        entry["suggested_party"] = names.get(entry["suggested_to"], "")

    rows.sort(key=lambda r: (STATUS_ORDER.index(r["status"])
                             if r["status"] in STATUS_ORDER else 99,
                             r["party_name"].lower()))
    return rows, exceptions


# ------------------------------------------------- received date, as local
_STAMP_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?"
    r"\s*(Z|[+-]\d{2}:?\d{2})$")


def local_stamp(value):
    """A received date as the reviewer's own calendar shows it.

    The bridge's spreadsheet keeps the date as a date cell, and Google
    hands that back as an instant in universal time: midnight on 10
    November in India arrives as '2026-11-09T18:30:00.000Z'.  Reading the
    first ten characters of that shows the day before.  Such a value is
    converted to local time; anything else is returned as it came."""
    text = str(value or "").strip()
    match = _STAMP_RE.match(text)
    if not match:
        return text
    try:
        zone = match.group(3)
        zone = "+00:00" if zone == "Z" else (
            zone if ":" in zone else zone[:3] + ":" + zone[3:])
        instant = datetime.fromisoformat(
            "%sT%s:00%s" % (match.group(1), match.group(2), zone))
        local = instant.astimezone()
    except Exception:
        return text
    if local.hour == 0 and local.minute == 0:
        return local.strftime("%Y-%m-%d")
    return local.strftime("%Y-%m-%d %H:%M")


# --------------------------------------------------- audit-status records
# One record per confirmation that needs following up.  It ties together the
# party, the request that was sent and the reply that came back, and holds
# what the audit team did about the difference.
AUDIT_STATES = ["Open", "Under follow-up", "Explained - no adjustment",
                "Adjustment proposed", "Alternative procedures performed",
                "Closed"]
AUDIT_OPEN_STATES = ("Open", "Under follow-up")
AUDIT_NATURES = ["Not yet determined",
                 "Timing difference - payment in transit",
                 "Timing difference - goods or invoice in transit",
                 "Disputed item", "Error in the client's books",
                 "Error in the party's books",
                 "Reply could not be matched or read", "Other"]


def needs_audit_status(row):
    return row.get("status") in (STATUS_VARIANCE, STATUS_REVIEW)


def audit_record_for(records, document_id):
    for record in records or []:
        if record.get("document_id") == document_id:
            return record
    return None


def audit_snapshot(row):
    """What a record takes from the reconciliation at the moment it is
    saved: the request, the reply and the figures it is following up."""
    return {
        "document_id": row.get("document_id", ""),
        "party_name": row.get("party_name", ""),
        "category": row.get("category", ""),
        "reference": row.get("reference", ""),
        "request_sent_at": row.get("sent_at", ""),
        "request_email": row.get("email", ""),
        "currency": row.get("currency", ""),
        "books_amount": row.get("books_amount"),
        "confirmed_amount": row.get("confirmed_amount"),
        "variance": row.get("variance"),
        "confirmation_status": row.get("status", ""),
        "reply_id": row.get("reply_id", ""),
        "reply_ids": row.get("reply_ids", ""),
        "reply_from": row.get("reply_from", ""),
        "reply_received_at": row.get("received_at", ""),
        "message_link": row.get("message_link", ""),
    }


def attach_audit_status(rows, records):
    """Put each row's follow-up position on the row, for every report."""
    for row in rows:
        record = audit_record_for(records, row.get("document_id"))
        if record:
            row["audit_state"] = record.get("state", "Open")
            row["audit_state_link"] = "Open record: %s" % row["audit_state"]
        elif needs_audit_status(row):
            row["audit_state"] = "Not yet recorded"
            row["audit_state_link"] = "Create record"
        else:
            row["audit_state"] = ""
            row["audit_state_link"] = ""
    return rows


def summarise(rows):
    """Headline figures for the dashboard and the variance report."""
    def total(selector):
        return sum(abs(r["books_amount"]) for r in rows
                   if selector(r) and r["books_amount"] is not None)

    received = [r for r in rows if r["status"] in
                (STATUS_AGREED, STATUS_VARIANCE)]
    requested_value = total(lambda r: r["status"] != STATUS_NOT_SENT)
    confirmed_value = sum(abs(r["books_amount"]) for r in received
                          if r["books_amount"] is not None)
    return {
        "sent": len([r for r in rows if r["status"] != STATUS_NOT_SENT]),
        "received": len(received),
        "agreed": len([r for r in rows if r["status"] == STATUS_AGREED]),
        "variance": len([r for r in rows if r["status"] == STATUS_VARIANCE]),
        "pending": len([r for r in rows if r["status"] == STATUS_PENDING]),
        "returned": len([r for r in rows if r["status"] == STATUS_RETURNED]),
        "review": len([r for r in rows if r["status"] == STATUS_REVIEW]),
        "not_sent": len([r for r in rows if r["status"] == STATUS_NOT_SENT]),
        "requested_value": requested_value,
        # books value of the balances that were answered: the coverage basis
        "confirmed_value": confirmed_value,
        # what the parties themselves confirmed
        "amount_confirmed": sum(abs(r["confirmed_amount"]) for r in received
                                if r["confirmed_amount"] is not None),
        "coverage_pct": (confirmed_value / requested_value * 100.0)
                        if requested_value else 0.0,
        "returned": len([r for r in rows if r["status"] == STATUS_RETURNED]),
        "review": len([r for r in rows if r["status"] == STATUS_REVIEW]),
        "net_variance": sum(r["variance"] for r in rows
                            if r["variance"] is not None),
        "gross_variance": sum(abs(r["variance"]) for r in rows
                              if r["variance"] is not None),
    }


def summarise_by_category(rows):
    """The same figures split by balance category - the working-paper view."""
    out = []
    for category in CATEGORIES:
        subset = [r for r in rows if r["category"] == category]
        if not subset:
            continue
        stats = summarise(subset)
        stats["category"] = category
        stats["parties"] = len(subset)
        out.append(stats)
    return out


# ===========================================================================
#  READING A REPLY'S OWN DOCUMENT
# ---------------------------------------------------------------------------
#  The signed slip is the evidence; the covering e-mail is only a note about
#  it.  So where a reply carries a PDF or a scan, the application opens the
#  file itself: the text layer is read where there is one, and every page is
#  also put through OCR, because a slip that was printed, filled in by hand
#  and scanned has no text layer at all, and a figure written onto a digital
#  PDF sits in an annotation the text layer does not carry.
#
#  Both libraries are optional.  Without them the application still works,
#  on whatever text the bridge could extract, and says what is missing.
# ===========================================================================
READER_MAX_PAGES = 8          # a confirmation is one page; a statement more
READER_DPI = 220              # enough for handwriting, light on memory
READABLE_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff",
                       ".bmp", ".webp")

_OCR_ENGINE = None
_OCR_FAILED = ""


def _pymupdf():
    try:
        import pymupdf                      # the current name
        return pymupdf
    except Exception:
        try:
            import fitz                     # the name older releases used
            return fitz
        except Exception:
            return None


def _ocr_engine():
    """The OCR engine, built once.  Returns None when it is not installed."""
    global _OCR_ENGINE, _OCR_FAILED
    if _OCR_ENGINE is not None or _OCR_FAILED:
        return _OCR_ENGINE
    try:
        import logging
        logging.getLogger("RapidOCR").setLevel(logging.ERROR)
        try:
            from rapidocr import RapidOCR
        except Exception:
            from rapidocr_onnxruntime import RapidOCR
        _OCR_ENGINE = RapidOCR()
        for name in ("RapidOCR", "rapidocr"):          # it logs every call
            logging.getLogger(name).setLevel(logging.ERROR)
            logging.getLogger(name).disabled = True
    except Exception as exc:
        _OCR_FAILED = str(exc) or exc.__class__.__name__
        _OCR_ENGINE = None
    return _OCR_ENGINE


def reader_status():
    """What the application can read for itself, in words for the auditor."""
    # asked on every repaint, so it only looks for the libraries; the engine
    # itself takes seconds to build and is built by the worker that uses it
    def present(module):
        try:
            return importlib.util.find_spec(module) is not None
        except Exception:
            return False
    have_pdf = present("pymupdf") or present("fitz")
    have_ocr = not _OCR_FAILED and present("onnxruntime") and (
        present("rapidocr") or present("rapidocr_onnxruntime"))
    if have_pdf and have_ocr:
        return True, "PDFs and scans are read on this computer (text and OCR)"
    missing = []
    if not have_pdf:
        missing.append("pymupdf")
    if not have_ocr:
        missing.append("rapidocr and onnxruntime")
    return False, ("Not installed: %s. Run  python -m pip install pymupdf "
                   "rapidocr onnxruntime  and start the application again."
                   % " and ".join(missing))


def is_readable_file(name, content_type=""):
    lowered = str(name or "").lower()
    kind = str(content_type or "").lower()
    return lowered.endswith(READABLE_EXTENSIONS) or "pdf" in kind or \
        kind.startswith("image/")


def _ocr_boxes(result):
    """(box, text) pairs out of whichever result shape the engine returns."""
    pairs = []
    boxes = getattr(result, "boxes", None)
    texts = getattr(result, "txts", None)
    if boxes is not None and texts is not None:            # rapidocr 2 and 3
        for box, text in zip(boxes, texts):
            pairs.append((box, text))
        return pairs
    if isinstance(result, tuple) and result and result[0]:   # rapidocr 1
        for item in result[0]:
            pairs.append((item[0], item[1]))
    return pairs


def _lines_from_boxes(pairs):
    """Put OCR fragments back into reading order.

    The engine returns one box per run of text.  A figure written on the
    slip's blank comes back as its own box, so the boxes are grouped into
    lines by their vertical position and each line is read left to right:
    that is what puts the handwritten amount back after the words 'is INR'.
    """
    items = []
    for box, text in pairs:
        text = str(text or "").strip()
        if not text:
            continue
        xs = [float(point[0]) for point in box]
        ys = [float(point[1]) for point in box]
        items.append({"x": min(xs), "y": (min(ys) + max(ys)) / 2.0,
                      "h": max(1.0, max(ys) - min(ys)), "text": text})
    items.sort(key=lambda item: (item["y"], item["x"]))
    lines = []
    for item in items:
        # handwriting sits a little above or below the printed baseline, so
        # the band is generous: 60% of the taller of the two heights
        if lines and abs(item["y"] - lines[-1]["y"]) <= \
                0.6 * max(item["h"], lines[-1]["h"]):
            lines[-1]["items"].append(item)
            count = len(lines[-1]["items"])
            lines[-1]["y"] += (item["y"] - lines[-1]["y"]) / count
            lines[-1]["h"] = max(lines[-1]["h"], item["h"])
        else:
            lines.append({"y": item["y"], "h": item["h"], "items": [item]})
    out = []
    for line in lines:
        line["items"].sort(key=lambda item: item["x"])
        out.append(" ".join(item["text"] for item in line["items"]))
    return "\n".join(out)


def tidy_ocr_text(text):
    """Remove what OCR adds that is not content.

    The rule on a slip's blank comes back as a run of underscores, dots or
    dashes; left in, it would sit between 'is INR' and the figure written
    over it.  Letters commonly mistaken inside a figure are put right only
    where the token is otherwise plainly a grouped number."""
    text = str(text or "")
    text = re.sub(r"[_]{2,}|[.]{4,}|[-—–]{3,}", " ", text)

    def digits_only(match):
        token = match.group(0)
        fixed = (token.replace("O", "0").replace("o", "0")
                 .replace("l", "1").replace("I", "1")
                 .replace("S", "5").replace("B", "8"))
        return fixed
    # e.g. 25,OO,000 or 2S,00,000 - grouped like a figure, digits in the main
    text = re.sub(r"(?<![A-Za-z])(?=[\dOolISB,]*\d)[\dOolISB]{1,3}"
                  r"(?:,[\dOolISB]{2,3})+(?![A-Za-z])", digits_only, text)
    return re.sub(r"[ \t]+", " ", text)


def ocr_image(image):
    """OCR one image (PNG/JPEG bytes, or a numpy array).  Returns text."""
    engine = _ocr_engine()
    if engine is None:
        return ""
    result = engine(image)
    return tidy_ocr_text(_lines_from_boxes(_ocr_boxes(result)))


def read_document(data, name="", content_type=""):
    """Read one attached file.

    Returns {text, method, pages, error}.  method is 'text', 'OCR' or
    'text + OCR', and is carried through to the register so the auditor can
    see how a figure was obtained."""
    result = {"text": "", "method": "", "pages": 0, "error": ""}
    if not data:
        result["error"] = "The file is empty"
        return result
    lowered = str(name or "").lower()
    is_pdf = data[:5] == b"%PDF-" or lowered.endswith(".pdf") or \
        "pdf" in str(content_type or "").lower()

    if not is_pdf:                                   # a photograph or a scan
        if _ocr_engine() is None:
            result["error"] = "OCR is not installed"
            return result
        try:
            result["text"] = ocr_image(data)
            result["method"], result["pages"] = "OCR", 1
        except Exception as exc:
            result["error"] = "The image could not be read: %s" % exc
        return result

    library = _pymupdf()
    if library is None:
        result["error"] = "PDF reading is not installed"
        return result
    try:
        document = library.open(stream=data, filetype="pdf")
    except Exception as exc:
        result["error"] = "The PDF could not be opened: %s" % exc
        return result
    if getattr(document, "needs_pass", False):
        result["error"] = "The PDF is password-protected"
        return result

    layer_parts, ocr_parts = [], []
    have_ocr = _ocr_engine() is not None
    try:
        for number, page in enumerate(document):
            if number >= READER_MAX_PAGES:
                break
            result["pages"] += 1
            layer = (page.get_text("text") or "").strip()
            if layer:
                layer_parts.append(tidy_ocr_text(layer))
            if have_ocr:
                try:
                    # rendered WITH annotations: a figure typed or inked onto
                    # a digital PDF lives there and nowhere else
                    pixmap = page.get_pixmap(dpi=READER_DPI, annots=True)
                    seen = ocr_image(pixmap.tobytes("png"))
                    if seen.strip():
                        ocr_parts.append(seen)
                except Exception as exc:
                    result["error"] = "OCR failed on page %d: %s" % (
                        number + 1, exc)
    finally:
        document.close()

    # the two readings are kept apart, the OCR one first: it is the only one
    # that can hold what was written on the page after it was printed
    parts = []
    if ocr_parts:
        parts.append("\n".join(ocr_parts))
    if layer_parts:
        parts.append("\n".join(layer_parts))
    result["text"] = "\n\n".join(parts).strip()
    result["method"] = " + ".join(
        label for label, present in (("text", layer_parts),
                                     ("OCR", ocr_parts)) if present)
    if not result["text"] and not result["error"]:
        result["error"] = ("Nothing could be read from the PDF" if have_ocr
                           else "The PDF is a scan and OCR is not installed")
    return result


def attachment_entry(name, reading):
    """A reply attachment record built from what the application read."""
    return {"name": name, "text": reading.get("text", ""),
            "method": reading.get("method", ""),
            "pages": reading.get("pages", 0),
            "read_by": "application",
            "error": reading.get("error", "")}


def reply_has_unread_files(reply):
    """True when a reply carries a PDF or image this application has not yet
    opened for itself."""
    if reply.get("files_read") or reply.get("bounced"):
        return False
    names = list(reply.get("files") or [])
    if not names:
        for attachment in reply.get("attachments") or []:
            if attachment.get("read_by") == "application":
                continue
            names += [part.strip() for part in
                      str(attachment.get("name") or "").split(";")]
    return any(is_readable_file(name) for name in names)


def attachment_url(feed_url, message_id):
    """The feed address asking for one message's own files."""
    parts = urllib.parse.urlsplit(feed_url)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query = [(k, v) for k, v in query if k != "message"]
    query.append(("message", message_id))
    return urllib.parse.urlunsplit(parts._replace(
        query=urllib.parse.urlencode(query)))


def fetch_reply_files(feed_url, message_id, timeout=90):
    """Download one reply's PDFs and images from the bridge.

    Returns ([(name, content_type, bytes)], skipped, error)."""
    request = urllib.request.Request(
        attachment_url(feed_url, message_id),
        headers={"User-Agent": "BalanceConfirmationGenerator/" + APP_VERSION,
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
        payload = json.loads(raw)
    except urllib.error.HTTPError as exc:
        return [], [], "the bridge refused the request (HTTP %s)" % exc.code
    except ValueError:
        return [], [], "the bridge returned a page rather than data"
    except Exception as exc:
        return [], [], "could not reach the bridge: %s" % exc
    if not isinstance(payload, dict):
        return [], [], "the bridge sent an unexpected answer"
    if "files" not in payload:
        # an older copy of the script ignores ?message= and sends the feed
        return [], [], ("the bridge script is an older version that cannot "
                        "hand over attachments. Paste the new script into "
                        "the Apps Script project and deploy a new version.")
    if payload.get("error"):
        return [], [], str(payload["error"])
    files = []
    for entry in payload.get("files") or []:
        try:
            data = base64.b64decode(entry.get("data") or "")
        except Exception:
            continue
        files.append((entry.get("name") or "attachment",
                      entry.get("type") or "", data))
    return files, list(payload.get("skipped") or []), ""


# ===========================================================================
# SECTION 5C - REPORTS
# ---------------------------------------------------------------------------
# Each report is built once as a plain table (title, columns, rows, totals)
# and then rendered three ways: on screen, into a formatted workbook, and
# into a PDF.  Building the data once is what keeps the three in agreement.
#
# Column spec: (heading, key, kind) where kind is
#   "text" | "money" | "number" | "date" | "pct" | "status"
#   "link"   - text on paper; on screen a link that opens the related record
#   "action" - on screen only (a Review link); left out of the exports
# ===========================================================================

REPORT_REGISTER = "register"
REPORT_RECEIVED = "received"
REPORT_PENDING = "pending"
REPORT_COMPARISON = "comparison"
REPORT_VARIANCE = "variance"
REPORT_EXCEPTIONS = "exceptions"
REPORT_AUDIT = "audit"

REPORT_TITLES = [
    (REPORT_REGISTER, "Confirmation register",
     "Every party the request was sent to"),
    (REPORT_RECEIVED, "Confirmations received",
     "Replies matched, with the amount confirmed"),
    (REPORT_PENDING, "Pending confirmations",
     "Sent but not yet answered, with ageing"),
    (REPORT_COMPARISON, "Requested vs confirmed",
     "Our books beside the party's reply"),
    (REPORT_VARIANCE, "Consolidated variance report",
     "Differences by category, with coverage"),
    (REPORT_EXCEPTIONS, "Exception queue",
     "Nothing here is counted until you decide it - click Review on a "
     "reply"),
    (REPORT_AUDIT, "Audit status",
     "Follow-up on every mismatch and every reply under review"),
]


def _pct(value):
    return None if value is None else round(value, 2)


def build_report(kind, rows, exceptions, context=None):
    """Return {key, title, subtitle, columns, rows, totals, note}."""
    context = context or {}
    title = dict((k, (t, s)) for k, t, s in REPORT_TITLES)[kind]

    if kind == REPORT_REGISTER:
        columns = [("Party", "party_name", "text"),
                   ("Category", "category", "text"),
                   ("Currency", "currency", "text"),
                   ("Amount as per books", "books_amount", "money"),
                   ("Email", "email", "text"),
                   ("Reference", "reference", "text"),
                   ("Date sent", "sent_at", "date"),
                   ("Delivery", "delivery", "text"),
                   ("Reply from", "reply_from", "text"),
                   ("Reply received", "received_at", "date"),
                   ("Matched on", "match_basis", "text"),
                   ("Amount confirmed", "confirmed_amount", "money"),
                   ("Outcome", "status", "status"),
                   ("Audit status", "audit_state", "link")]
        data = list(rows)
        totals = {"books_amount": sum(abs(r["books_amount"]) for r in data
                                      if r["books_amount"] is not None)}

    elif kind == REPORT_RECEIVED:
        data = [r for r in rows if r["status"] in (STATUS_AGREED,
                                                   STATUS_VARIANCE)]
        columns = [("Party", "party_name", "text"),
                   ("Category", "category", "text"),
                   ("Date received", "received_at", "date"),
                   ("Reply from", "reply_from", "text"),
                   ("Amount confirmed", "confirmed_amount", "money"),
                   ("Matched on", "match_basis", "text"),
                   ("Match confidence", "match_confidence", "pct_unit"),
                   ("Read from", "extract_source", "text"),
                   ("Read confidence", "extract_confidence", "pct_unit"),
                   ("Party's stance", "stance", "text"),
                   ("Outcome", "status", "status")]
        totals = {"confirmed_amount": sum(abs(r["confirmed_amount"])
                                          for r in data
                                          if r["confirmed_amount"] is not None)}

    elif kind == REPORT_PENDING:
        data = [r for r in rows if r["status"] in (STATUS_PENDING,
                                                   STATUS_RETURNED)]
        columns = [("Party", "party_name", "text"),
                   ("Category", "category", "text"),
                   ("Amount as per books", "books_amount", "money"),
                   ("Email", "email", "text"),
                   ("Date sent", "sent_at", "date"),
                   ("Days outstanding", "age_days", "number"),
                   ("Reminder due", "reminder_label", "text"),
                   ("Status", "status", "status")]
        stages = context.get("reminders", DEFAULT_REMINDERS)
        for row in data:
            stage = row.get("reminder_stage", 0)
            row["reminder_label"] = ("%d of %d (%d days)"
                                     % (stage, len(stages),
                                        sorted(stages)[stage - 1])) \
                if stage else "not yet"
        totals = {"books_amount": sum(abs(r["books_amount"]) for r in data
                                      if r["books_amount"] is not None)}

    elif kind == REPORT_COMPARISON:
        data = [r for r in rows if r["status"] != STATUS_NOT_SENT]
        columns = [("Party", "party_name", "text"),
                   ("Category", "category", "text"),
                   ("Currency", "currency", "text"),
                   ("As per client's books", "books_amount", "money"),
                   ("Confirmed by party", "confirmed_amount", "money"),
                   ("Variance (confirmed less books)", "variance", "money"),
                   ("Variance %", "variance_pct", "pct"),
                   ("Status", "status", "status"),
                   ("Audit status", "audit_state", "link"),
                   ("Confirmed by (reply from)", "reply_from", "text"),
                   ("Reply received", "received_at", "date"),
                   ("Remark", "note", "text")]
        totals = {
            "books_amount": sum(abs(r["books_amount"]) for r in data
                                if r["books_amount"] is not None),
            "confirmed_amount": sum(abs(r["confirmed_amount"]) for r in data
                                    if r["confirmed_amount"] is not None),
            "variance": sum(r["variance"] for r in data
                            if r["variance"] is not None),
        }

    elif kind == REPORT_VARIANCE:
        columns = [("Category", "category", "text"),
                   ("Parties", "parties", "number"),
                   ("Value requested", "requested_value", "money"),
                   ("Books value of replies counted", "confirmed_value",
                    "money"),
                   ("Coverage %", "coverage_pct", "pct"),
                   ("Amount confirmed by parties", "amount_confirmed",
                    "money"),
                   ("Matched", "agreed", "number"),
                   ("Mismatch", "variance", "number"),
                   ("Pending", "pending", "number"),
                   ("Returned", "returned", "number"),
                   ("Needs Review", "review", "number"),
                   ("Net difference", "net_variance", "money"),
                   ("Gross difference", "gross_variance", "money")]
        data = summarise_by_category(rows)
        overall = summarise(rows)
        totals = {"parties": sum(d["parties"] for d in data),
                  "requested_value": overall["requested_value"],
                  "confirmed_value": overall["confirmed_value"],
                  "amount_confirmed": overall["amount_confirmed"],
                  "coverage_pct": _pct(overall["coverage_pct"]),
                  "agreed": overall["agreed"],
                  "variance": overall["variance"],
                  "pending": overall["pending"],
                  "returned": overall["returned"],
                  "review": overall["review"],
                  "net_variance": overall["net_variance"],
                  "gross_variance": overall["gross_variance"]}

    elif kind == REPORT_EXCEPTIONS:
        columns = [("Action", "review", "action"),
                   ("Reason", "reason", "text"),
                   ("From", "from_email", "text"),
                   ("Received", "received_at", "date"),
                   ("Amount read", "amount", "money"),
                   ("Suggested party", "suggested_party", "text"),
                   ("Evidence points to", "candidates", "text"),
                   ("Subject", "subject", "text"),
                   ("Name on the reply", "from_name", "text"),
                   ("Confidence", "confidence", "pct_unit")]
        data = list(exceptions)
        totals = {}

    elif kind == REPORT_AUDIT:
        columns = [("Party", "party_name", "text"),
                   ("Category", "category", "text"),
                   ("Reference", "reference", "text"),
                   ("As per client's books", "books_amount", "money"),
                   ("Confirmed by party", "confirmed_amount", "money"),
                   ("Variance", "variance", "money"),
                   ("Confirmation status", "confirmation_status", "status"),
                   ("Follow-up", "state", "link"),
                   ("Nature of difference", "nature", "text"),
                   ("Notes", "notes", "text"),
                   ("Owner", "owner", "text"),
                   ("Reply from", "reply_from", "text"),
                   ("Reply received", "reply_received_at", "date"),
                   ("Opened", "created_at", "date"),
                   ("Last updated", "updated_at", "date")]
        # the record shows the position as it stands NOW, not as it stood
        # when the record was opened
        current = {r.get("document_id"): r for r in rows}
        data = []
        for record in context.get("audit_records") or []:
            if record.get("document_id") not in current:
                continue
            entry = dict(record)
            entry.update(audit_snapshot(current[record["document_id"]]))
            entry["state_link"] = "Open record: %s" % entry.get("state", "")
            data.append(entry)
        data.sort(key=lambda e: (e.get("state") not in AUDIT_OPEN_STATES,
                                 str(e.get("party_name", "")).lower()))
        totals = {"variance": sum(e["variance"] for e in data
                                  if e.get("variance") is not None)}

    else:
        raise ValueError("Unknown report: %s" % kind)

    return {"key": kind, "title": title[0], "subtitle": title[1],
            "columns": columns, "rows": data, "totals": totals,
            "note": context.get("note", "")}


def build_all_reports(rows, exceptions, context=None):
    """Every report as it goes on paper: the screen-only action column is
    left out."""
    reports = [build_report(key, rows, exceptions, context)
               for key, _title, _sub in REPORT_TITLES]
    for report in reports:
        report["columns"] = [column for column in report["columns"]
                             if column[2] != "action"]
    return reports


def format_cell(value, kind, currency="INR"):
    """One value as it should read on screen and on paper."""
    if value is None or value == "":
        return ""
    if kind == "money":
        return fmt_amount(value, currency) or ""
    if kind == "pct":
        return "%.2f%%" % float(value)
    if kind == "pct_unit":
        return "%d%%" % round(float(value) * 100)
    if kind == "date":
        return fmt_date_long(value) or str(value)
    if kind == "number":
        return str(int(value)) if float(value) == int(float(value)) \
            else str(value)
    return str(value)


# ------------------------------------------------------------- Excel export
def write_reports_xlsx(path, reports, heading):
    """One sheet per report, frozen headings, totals, and a cover sheet."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    ink = "FF23281A"
    olive = "FF5F7232"
    band = "FFEFF2E4"
    rule = Side(style="thin", color="FFD5D8C4")

    book = Workbook()
    cover = book.active
    cover.title = "Cover"
    cover["A1"] = heading.get("title", "Balance confirmation reports")
    cover["A1"].font = Font(size=16, bold=True, color=ink)
    line = 3
    for label, value in heading.get("facts", []):
        cover.cell(row=line, column=1, value=label).font = Font(bold=True,
                                                                color=ink)
        cover.cell(row=line, column=2, value=value)
        line += 1
    cover.column_dimensions["A"].width = 30
    cover.column_dimensions["B"].width = 60
    cover.sheet_view.showGridLines = False

    for report in reports:
        sheet = book.create_sheet(report["title"][:31])
        sheet.sheet_view.showGridLines = False
        sheet["A1"] = report["title"]
        sheet["A1"].font = Font(size=13, bold=True, color=ink)
        sheet["A2"] = report["subtitle"]
        sheet["A2"].font = Font(size=10, italic=True, color="FF6E755B")

        head_row = 4
        for index, (heading_text, _key, _kind) in enumerate(report["columns"],
                                                            start=1):
            cell_ = sheet.cell(row=head_row, column=index, value=heading_text)
            cell_.font = Font(bold=True, color="FFFFFFFF", size=10)
            cell_.fill = PatternFill("solid", fgColor=olive)
            cell_.alignment = Alignment(vertical="center", wrap_text=True)
            cell_.border = Border(bottom=rule)

        for offset, row in enumerate(report["rows"]):
            excel_row = head_row + 1 + offset
            currency = row.get("currency") or "INR"
            for index, (_heading, key, kind) in enumerate(report["columns"],
                                                          start=1):
                value = row.get(key)
                cell_ = sheet.cell(row=excel_row, column=index)
                if kind in ("money", "number") and isinstance(value,
                                                              (int, float)):
                    cell_.value = value
                    cell_.number_format = ('#,##0.00' if kind == "money"
                                           else '#,##0')
                    cell_.alignment = Alignment(horizontal="right")
                elif kind == "pct" and isinstance(value, (int, float)):
                    cell_.value = value / 100.0
                    cell_.number_format = '0.00%'
                    cell_.alignment = Alignment(horizontal="right")
                elif kind == "pct_unit" and isinstance(value, (int, float)):
                    cell_.value = value
                    cell_.number_format = '0%'
                    cell_.alignment = Alignment(horizontal="right")
                else:
                    cell_.value = format_cell(value, kind, currency)
                    cell_.alignment = Alignment(horizontal="left",
                                                vertical="top")
                cell_.border = Border(bottom=rule)
                if offset % 2 == 1:
                    cell_.fill = PatternFill("solid", fgColor=band)
                if kind == "status" and value in (STATUS_VARIANCE,
                                                  STATUS_REVIEW):
                    cell_.font = Font(bold=True, color="FF9B3F28")
                elif kind == "status" and value == STATUS_AGREED:
                    cell_.font = Font(bold=True, color="FF3F6B1F")

        if report["totals"]:
            total_row = head_row + 1 + len(report["rows"])
            sheet.cell(row=total_row, column=1, value="Total").font = Font(
                bold=True, color=ink)
            for index, (_heading, key, kind) in enumerate(report["columns"],
                                                          start=1):
                if key in report["totals"]:
                    value = report["totals"][key]
                    cell_ = sheet.cell(row=total_row, column=index)
                    if kind == "pct":
                        cell_.value = (value or 0) / 100.0
                        cell_.number_format = '0.00%'
                    else:
                        cell_.value = value
                        cell_.number_format = ('#,##0.00' if kind == "money"
                                               else '#,##0')
                    cell_.font = Font(bold=True, color=ink)
                    cell_.alignment = Alignment(horizontal="right")
                    cell_.border = Border(top=Side(style="thin", color=olive))

        if not report["rows"]:
            sheet.cell(row=head_row + 1, column=1,
                       value="Nothing to report.").font = Font(italic=True,
                                                               color="FF6E755B")

        for index, (heading_text, key, kind) in enumerate(report["columns"],
                                                          start=1):
            widest = len(heading_text)
            for row in report["rows"]:
                widest = max(widest, len(format_cell(row.get(key), kind,
                                                     row.get("currency")
                                                     or "INR")))
            sheet.column_dimensions[get_column_letter(index)].width = \
                min(46, max(11, widest + 3))
        sheet.freeze_panes = sheet.cell(row=head_row + 1, column=1)

    book.save(path)
    return path


# --------------------------------------------------------------- PDF export
def write_reports_pdf(path, reports, heading):
    """Landscape A4, one report per page, same figures as the workbook."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                                    Spacer, Table, TableStyle)

    ink = colors.HexColor("#23281A")
    olive = colors.HexColor("#5F7232")
    muted = colors.HexColor("#6E755B")
    band = colors.HexColor("#F2F4EA")
    rule = colors.HexColor("#D5D8C4")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("t", parent=styles["Title"], fontSize=15,
                                 textColor=ink, alignment=TA_LEFT,
                                 spaceAfter=2)
    sub_style = ParagraphStyle("s", parent=styles["Normal"], fontSize=9,
                               textColor=muted, spaceAfter=8)
    fact_style = ParagraphStyle("f", parent=styles["Normal"], fontSize=9,
                                textColor=ink, leading=13)
    cell_style = ParagraphStyle("c", parent=styles["Normal"], fontSize=7.5,
                                textColor=ink, leading=9.5)
    head_style = ParagraphStyle("h", parent=styles["Normal"], fontSize=7.5,
                                textColor=colors.white, leading=9.5,
                                fontName="Helvetica-Bold")

    document = SimpleDocTemplate(
        path, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
        title=heading.get("title", "Balance confirmation reports"),
        author=heading.get("author", ""))

    story = [Paragraph(heading.get("title", "Balance confirmation reports"),
                       title_style)]
    facts = "<br/>".join("<b>%s</b>&nbsp;&nbsp;%s" % (label, xml_escape(value))
                         for label, value in heading.get("facts", []))
    if facts:
        story.append(Paragraph(facts, fact_style))
    story.append(Spacer(1, 6 * mm))

    for index, report in enumerate(reports):
        if index:
            story.append(PageBreak())
        story.append(Paragraph(xml_escape(report["title"]), title_style))
        story.append(Paragraph(xml_escape(report["subtitle"]), sub_style))

        head = [Paragraph(xml_escape(h), head_style)
                for h, _k, _t in report["columns"]]
        body = []
        for row in report["rows"]:
            currency = row.get("currency") or "INR"
            body.append([Paragraph(xml_escape(format_cell(row.get(key), kind,
                                                          currency)),
                                   cell_style)
                         for _h, key, kind in report["columns"]])
        if not body:
            body = [[Paragraph("<i>Nothing to report.</i>", cell_style)]
                    + [Paragraph("", cell_style)] * (len(head) - 1)]

        if report["totals"]:
            total_cells = []
            for position, (_h, key, kind) in enumerate(report["columns"]):
                if position == 0:
                    total_cells.append(Paragraph("<b>Total</b>", cell_style))
                elif key in report["totals"]:
                    total_cells.append(Paragraph(
                        "<b>%s</b>" % xml_escape(
                            format_cell(report["totals"][key], kind, "INR")),
                        cell_style))
                else:
                    total_cells.append(Paragraph("", cell_style))
            body.append(total_cells)

        table = Table([head] + body, repeatRows=1, hAlign="LEFT")
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), olive),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, rule),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
        for position in range(1, len(body) + 1):
            if position % 2 == 0:
                style.append(("BACKGROUND", (0, position), (-1, position), band))
        if report["totals"]:
            last = len(body)
            style.append(("LINEABOVE", (0, last), (-1, last), 0.8, olive))
            style.append(("BACKGROUND", (0, last), (-1, last), colors.white))
        table.setStyle(TableStyle(style))
        story.append(table)

    document.build(story)
    return path


# ===========================================================================
# SECTION 6 - LOCAL DATABASE
# ---------------------------------------------------------------------------
# A plain JSON file in the user's application-data folder.  Clients hold
# financial years; each year carries its own audit type and period basis;
# every generation run is recorded against the year.
# ===========================================================================

def app_data_dir():
    if os.name == "nt":
        root = os.environ.get("APPDATA") or os.path.expanduser("~")
        folder = os.path.join(root, "BalanceConfirmationGenerator")
    elif sys.platform == "darwin":
        folder = os.path.expanduser(
            "~/Library/Application Support/BalanceConfirmationGenerator")
    else:
        root = os.environ.get("XDG_DATA_HOME") or os.path.expanduser(
            "~/.local/share")
        folder = os.path.join(root, "BalanceConfirmationGenerator")
    os.makedirs(folder, exist_ok=True)
    return folder


DB_PATH = os.path.join(app_data_dir(), "database.json")
DB_VERSION = 3


def new_id():
    return uuid.uuid4().hex[:12]


def blank_db():
    return {
        "version": DB_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "clients": [],
        "runs": [],
        "replies": [],
        "audit_status": [],      # follow-up records, one for a request
        "settings": {
            "firm_name": "Ankit Soni and Associates",
            "firm_designation": "Statutory Auditor",
            "partner_name": "",
            "last_audit_type": "Statutory Audit",
            "letterhead_note": True,
            "letter_date": "",
            "theme": "dark",
            "auditors": [],
            "default_currency": "INR",
            "variance_tolerance": 1.0,
            "reminder_days": [15, 30, 45],
            # the always-on Gmail bridge: the web-app URL published by the
            # Apps Script, and when it was last read
            "letterhead_space_cm": 0.0,
            "bridge_feed_url": "",
            "bridge_last_sync": "",
            "bridge_sync_on_start": True,
            "last_client_id": None,
            "last_fy_id": None,
            "output_folder": "",
            "mail": {
                "provider": "Gmail / Google Workspace",
                "host": "smtp.gmail.com",
                "port": 587,
                "security": "starttls",
                "username": "",
                "sender": "",
                "sender_name": "",
                "remember_password": False,
                "subject": DEFAULT_SUBJECT,
                "body": DEFAULT_BODY,
                "cc_team": True,
                "reply_to_team": True,
                "delay_ms": 1500,
                "attach_mode": "pdf",
            },
        },
    }


def normalise_db(data):
    """Accept any earlier shape and bring it up to the current version."""
    db = blank_db()
    if isinstance(data, dict):
        db["clients"] = data.get("clients") or []
        db["runs"] = data.get("runs") or []
        db["replies"] = data.get("replies") or []
        db["audit_status"] = data.get("audit_status") or []
        settings = data.get("settings") or {}
        mail = dict(db["settings"]["mail"])
        mail.update(settings.get("mail") or {})
        db["settings"].update(settings)
        db["settings"]["mail"] = mail
    db["settings"].setdefault("auditors", [])

    for client in db["clients"]:
        client.setdefault("id", new_id())
        # the letter is signed by the client's own officer
        client.setdefault("signatory_name", "")
        client.setdefault("signatory_designation", "Director / CFO")
        client.setdefault("created_at", datetime.now().isoformat(
            timespec="seconds"))
        client.setdefault("financial_years", client.pop("financialYears", []))
        for year in client["financial_years"]:
            year.setdefault("id", new_id())
            year.setdefault("year", "")
            year.setdefault("year_end", year.pop("yearEnd", ""))
            # v1 -> v2: audit type and period basis did not exist
            year.setdefault("audit_type", "Statutory Audit")
            year.setdefault("audit_type_other", "")
            if year.get("basis") != "period":
                year["basis"] = "year"
            year.setdefault("period_start", "")
            year.setdefault("period_end", "")
    # v1 -> v2: refresh the stock sentence that hard-coded "statutory audit"
    legacy = ("We are conducting the statutory audit of {client} for the year "
              "ended {date}.")
    body = db["settings"]["mail"].get("body") or ""
    if legacy in body:
        db["settings"]["mail"]["body"] = body.replace(
            legacy, "We are conducting the {audittype} of {client} {period}.")
    # the covering e-mail now says the attached letter is the client's own
    legacy_body = ("Please find attached our balance confirmation request in "
                   "respect of the {category} balance")
    if legacy_body in (db["settings"]["mail"].get("body") or ""):
        db["settings"]["mail"]["body"] = DEFAULT_BODY
        db["settings"]["mail"]["subject"] = DEFAULT_SUBJECT
    # the stock subject now carries the reference code; a subject the
    # auditor wrote themselves is left exactly as it is
    if db["settings"]["mail"].get("subject") == LEGACY_SUBJECT:
        db["settings"]["mail"]["subject"] = DEFAULT_SUBJECT
    db["version"] = DB_VERSION
    return db


def letter_date(db):
    """The date printed at the top of the letter; today unless overridden."""
    saved = db["settings"].get("letter_date")
    return saved if (saved and to_date(saved)) else date.today().isoformat()


def load_db():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as handle:
                return normalise_db(json.load(handle)), None
        except Exception as exc:
            return blank_db(), str(exc)
    return blank_db(), None


def save_db(db):
    """Write through a temporary file so a crash cannot truncate the data."""
    try:
        temp = DB_PATH + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(db, handle, indent=2, ensure_ascii=False)
        os.replace(temp, DB_PATH)
        return True, None
    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------- financial year helpers
def fy_as_at(year):
    """The date every letter confirms balances as on."""
    if not year:
        return ""
    return (year.get("period_end") or "") if year.get("basis") == "period" \
        else (year.get("year_end") or "")


def fy_basis_label(year):
    return "Period end" if (year and year.get("basis") == "period") \
        else "Year end"


def fy_audit_type(year):
    return (year or {}).get("audit_type") or "Statutory Audit"


def fy_audit_ok(year):
    if not year:
        return False
    if fy_audit_type(year) != "Other":
        return True
    return bool(str(year.get("audit_type_other") or "").strip())


def fy_span_text(year):
    return period_label(year.get("basis"), fy_as_at(year),
                        year.get("period_start")) if year else ""


# ===========================================================================
# SECTION 7 - APPEARANCE
# ---------------------------------------------------------------------------
# One olive-green identity in two modes.  Every colour used anywhere in the
# interface is a key in T, so switching mode re-reads the same keys and the
# whole window repaints - there are no colours hard-coded further down.
# ===========================================================================

THEMES = {
    "dark": {
        "name": "dark",
        "window":    "#14170F",   # deepest olive-charcoal
        "surface":   "#1C2014",   # cards and panels
        "raised":    "#252A19",   # inputs, buttons, table rows
        "raised2":   "#2E3420",   # hover
        "line":      "#39402A",
        "line_soft": "#49512F",
        "text":      "#E7EADA",
        "text_soft": "#B3B99F",
        "text_mute": "#959C7E",
        # depth: every raised surface runs light-to-dark, is lit along its
        # top edge and shaded along its bottom one, and casts a shadow
        "card_hi": "#262B1A", "card_lo": "#1A1E12",
        "bevel_hi": "#4B5334", "bevel_lo": "#090B06",
        "btn_hi": "#353C24", "btn_lo": "#20251A",
        "btn_hover_hi": "#3F472B", "btn_hover_lo": "#272D1C",
        "accent_top": "#9BB158", "accent_bot": "#7F9142",
        "accent_edge": "#46521F",
        "well": "#12150D", "well_edge": "#070804",
        "shadow_rgba": (0, 0, 0, 165),
        "accent":      "#7F9142",   # olive
        "accent_hi":   "#93A851",   # olive, lighter
        "accent_deep": "#56642C",
        "accent_text": "#14170F",   # deep ink on olive: 5.2:1
        "on_accent_soft": "#C7D79A",
        "panel_tint": "#20250F",    # selected navigation row
        "ok":    "#8FBF5F", "ok_bg":   "#1E2A12", "ok_line":   "#4C6B28",
        "warn":  "#D9B356", "warn_bg": "#2E2812", "warn_line": "#6E5C22",
        "err":   "#D98A6E", "err_bg":  "#2E1A14", "err_line":  "#70392A",
        "info":  "#8FB3C9", "info_bg": "#15222A", "info_line": "#2F4F60",
        "paper":      "#FBFAF4",   # the letter preview is always paper-white
        "paper_ink":  "#1C1A17",
        "paper_line": "#C9C6B4",
        "shadow": "rgba(0,0,0,.45)",
    },
    "light": {
        "name": "light",
        "window":    "#F4F4EC",
        "surface":   "#FFFFFF",
        "raised":    "#FBFBF5",
        "raised2":   "#F0F1E4",
        "line":      "#DCDCCB",
        "line_soft": "#C7C8B2",
        "text":      "#23281A",
        "text_soft": "#5A6049",
        "text_mute": "#626950",
        "card_hi": "#FFFFFF", "card_lo": "#F0F1E6",
        "bevel_hi": "#FFFFFF", "bevel_lo": "#B4B79C",
        "btn_hi": "#FFFFFF", "btn_lo": "#E4E6D3",
        "btn_hover_hi": "#FFFFFF", "btn_hover_lo": "#D9DCC4",
        "accent_top": "#687D37", "accent_bot": "#4F6027",
        "accent_edge": "#2F3B15",
        "well": "#FFFFFF", "well_edge": "#A9AC90",
        "shadow_rgba": (70, 76, 44, 80),
        "accent":      "#5F7232",
        "accent_hi":   "#71873C",
        "accent_deep": "#44531F",
        "accent_text": "#FFFFFF",
        "on_accent_soft": "#3C4A1C",
        "panel_tint": "#E8EDD6",
        "ok":    "#3F6B1F", "ok_bg":   "#EBF3DF", "ok_line":   "#A9C285",
        "warn":  "#7E610F", "warn_bg": "#FAF1D9", "warn_line": "#D9BE78",
        "err":   "#9B3F28", "err_bg":  "#FAE7E1", "err_line":  "#D9A694",
        "info":  "#2F5A74", "info_bg": "#E6F0F6", "info_line": "#9DC0D4",
        "paper":      "#FFFFFF",
        "paper_ink":  "#1C1A17",
        "paper_line": "#D8D6C8",
        "shadow": "rgba(60,64,40,.16)",
    },
}

# the live palette; apply_theme() swaps its contents in place so that every
# module-level reference stays valid
T = dict(THEMES["dark"])


def set_theme(name):
    T.clear()
    T.update(THEMES.get(name, THEMES["dark"]))
    return T


def is_dark():
    return T.get("name") == "dark"


def style_sheet():
    """Build the whole style sheet from the active palette."""
    tokens = dict(T)
    tokens["card_grad"] = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                           "stop:0 %(card_hi)s, stop:1 %(card_lo)s)" % T)
    tokens["btn_grad"] = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                          "stop:0 %(btn_hi)s, stop:1 %(btn_lo)s)" % T)
    tokens["btn_hover"] = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                           "stop:0 %(btn_hover_hi)s, stop:1 %(btn_hover_lo)s)"
                           % T)
    tokens["btn_down"] = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                          "stop:0 %(btn_lo)s, stop:1 %(btn_hi)s)" % T)
    tokens["accent_grad"] = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                             "stop:0 %(accent_top)s, stop:1 %(accent_bot)s)"
                             % T)
    tokens["accent_down"] = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                             "stop:0 %(accent_bot)s, stop:1 %(accent_top)s)"
                             % T)
    tokens["side_grad"] = ("qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                           "stop:0 %(card_hi)s, stop:1 %(card_lo)s)" % T)
    return """
/* Only the window paints a background.  Anything not styled here stays
   transparent and shows the surface it sits on, so a label never appears as
   a coloured rectangle on a card. */
QWidget { color: %(text)s; font-size: 13px; }
QMainWindow, QDialog, QScrollArea, #TopBar { background: %(window)s; }

/* ---------- sidebar ---------- */
#Sidebar { background: %(side_grad)s; border-right: 2px solid %(bevel_lo)s; }
#BrandMark { color: %(text)s; font-size: 17px; font-weight: 600; }
#BrandTag  { color: %(text_mute)s; font-size: 10px; letter-spacing: 1.4px; }
#NavList { background: transparent; border: 0; outline: 0; }
#NavList::item { color: %(text_soft)s; padding: 9px 10px; margin: 2px 7px;
                 border: 1px solid transparent; border-radius: 9px; }
#NavList::item:hover { background: %(btn_grad)s; color: %(text)s;
                       border: 1px solid %(line_soft)s;
                       border-bottom: 2px solid %(bevel_lo)s; }
#NavList::item:selected { background: %(accent_grad)s; color: %(accent_text)s;
                          border: 1px solid %(accent_top)s;
                          border-bottom: 3px solid %(accent_edge)s; }
#SideFoot { color: %(text_mute)s; font-size: 11px; }

/* ---------- header ---------- */
#TopBar { border-bottom: 2px solid %(bevel_lo)s; }
#PageTitle { color: %(text)s; font-size: 21px; font-weight: 600; }
#PageSub { color: %(text_mute)s; font-size: 12px; }
QLabel[chip="neutral"], QLabel[chip="green"], QLabel[chip="blue"],
QLabel[chip="warn"], QLabel[chip="brass"] {
    border-radius: 11px; padding: 4px 11px; font-size: 11px;
    background: %(raised)s; border: 1px solid %(line_soft)s;
    color: %(text_soft)s; }
QLabel[chip="green"] { background: %(ok_bg)s; border-color: %(ok_line)s;
                       color: %(ok)s; }
QLabel[chip="blue"]  { background: %(info_bg)s; border-color: %(info_line)s;
                       color: %(info)s; }
QLabel[chip="warn"]  { background: %(warn_bg)s; border-color: %(warn_line)s;
                       color: %(warn)s; }
QLabel[chip="brass"] { background: %(ok_bg)s; border-color: %(accent)s;
                       color: %(ok)s; }

/* ---------- cards ---------- */
/* a card is a slab: lit along the top, shaded underneath, and lifted off the
   page by the drop shadow the helper gives it */
#CardDark, #CardLight { background: %(card_grad)s;
                        border: 1px solid %(line)s;
                        border-top: 1px solid %(bevel_hi)s;
                        border-bottom: 3px solid %(bevel_lo)s;
                        border-radius: 14px; }
#CardHeadDark, #CardHeadLight { color: %(text)s; font-size: 15px;
                                font-weight: 600; }
#HintDark, #HintLight { color: %(text_mute)s; font-size: 11.5px; }
#FieldLabelDark, #FieldLabelLight { color: %(text_mute)s; font-size: 10px;
    letter-spacing: 1.1px; font-weight: 600; }
#Rule, #RuleLight { background: %(line)s; max-height: 1px; border: 0; }

/* ---------- inputs ---------- */
/* fields are wells: sunk into the card, darker along the top lip */
QLineEdit, QPlainTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {
    background: %(well)s; border: 1px solid %(line_soft)s;
    border-top: 2px solid %(well_edge)s;
    border-radius: 8px; padding: 6px 8px; color: %(text)s;
    selection-background-color: %(accent)s;
    selection-color: %(accent_text)s; }
QComboBox, QDateEdit { padding-right: 22px; }
QSpinBox, QDoubleSpinBox { padding-right: 18px; }
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid %(accent_hi)s;
    border-top: 2px solid %(accent_hi)s; }
QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled,
QPlainTextEdit:disabled { color: %(text_mute)s; background: %(raised2)s; }
QComboBox QAbstractItemView { background: %(surface)s; color: %(text)s;
    border: 1px solid %(line_soft)s;
    selection-background-color: %(accent)s;
    selection-color: %(accent_text)s; outline: 0; }

/* ---------- buttons ---------- */
/* a button is a key: it stands 3px proud of the card and travels down
   when pressed */
QPushButton { background: %(btn_grad)s; border: 1px solid %(line_soft)s;
    border-top: 1px solid %(bevel_hi)s;
    border-bottom: 3px solid %(bevel_lo)s;
    border-radius: 9px; padding: 6px 14px; color: %(text)s;
    font-weight: 600; }
QPushButton:hover { background: %(btn_hover)s; border-color: %(accent)s;
    border-top-color: %(bevel_hi)s; border-bottom-color: %(bevel_lo)s; }
QPushButton:pressed { background: %(btn_down)s;
    border-top: 3px solid %(bevel_lo)s;
    border-bottom: 1px solid %(line_soft)s; }
QPushButton:disabled { color: %(text_mute)s; border: 1px solid %(line)s;
    border-bottom: 2px solid %(line)s; background: %(raised2)s; }
QPushButton[kind="primary"] { background: %(accent_grad)s;
    border: 1px solid %(accent_top)s;
    border-bottom: 3px solid %(accent_edge)s; color: %(accent_text)s; }
QPushButton[kind="primary"]:hover { background: %(accent_top)s;
    border-color: %(accent_top)s; border-bottom-color: %(accent_edge)s; }
QPushButton[kind="primary"]:pressed { background: %(accent_down)s;
    border-top: 3px solid %(accent_edge)s;
    border-bottom: 1px solid %(accent_top)s; }
QPushButton[kind="primary"]:disabled { background: %(raised2)s;
    color: %(text_mute)s; border: 1px solid %(line)s;
    border-bottom: 2px solid %(line)s; }
QPushButton[kind="blue"] { background: %(info_bg)s; border-color: %(info_line)s;
    border-bottom: 3px solid %(info_line)s; color: %(info)s; }
QPushButton[kind="blue"]:hover { border-color: %(info)s; }
QPushButton[kind="brass"] { background: %(accent_grad)s;
    border: 1px solid %(accent_top)s;
    border-bottom: 3px solid %(accent_edge)s; color: %(accent_text)s; }
QPushButton[kind="brass"]:hover { background: %(accent_top)s; }
QPushButton[kind="brass"]:pressed { background: %(accent_down)s;
    border-top: 3px solid %(accent_edge)s;
    border-bottom: 1px solid %(accent_top)s; }
QPushButton[kind="danger"] { background: transparent;
    border-color: %(err_line)s; color: %(err)s; }
QPushButton[kind="danger"]:hover { background: %(err_bg)s; }
QPushButton[kind="small"] { padding: 4px 9px; font-size: 12px; }
#ThemeToggle { padding: 5px 13px; font-size: 12px;
               border-radius: 14px; background: %(btn_grad)s;
               border: 1px solid %(line_soft)s;
               border-top: 1px solid %(bevel_hi)s;
               border-bottom: 3px solid %(bevel_lo)s; color: %(text_soft)s; }
#ThemeToggle:hover { border-color: %(accent)s; color: %(text)s; }

/* ---------- tables ---------- */
QTableWidget { background: %(well)s;
    alternate-background-color: %(raised2)s;
    gridline-color: %(line)s; border: 1px solid %(line)s; border-radius: 8px;
    color: %(text)s; selection-background-color: %(panel_tint)s;
    selection-color: %(text)s; }
QTableWidget::item { padding: 5px 6px; }
QHeaderView::section { background: %(btn_grad)s; color: %(text_soft)s;
    border: 0; border-bottom: 2px solid %(bevel_lo)s;
    border-right: 1px solid %(line)s; padding: 7px 6px;
    font-size: 11px; font-weight: 600; letter-spacing: 0.6px; }
QTableCornerButton::section { background: %(raised2)s; border: 0; }

/* ---------- misc ---------- */
QProgressBar { background: %(well)s; border: 1px solid %(line_soft)s;
    border-top: 2px solid %(well_edge)s;
    border-radius: 7px; height: 13px; text-align: center;
    color: %(text_soft)s; font-size: 11px; }
QProgressBar::chunk { background: %(accent_grad)s; border-radius: 5px; }
QCheckBox { spacing: 7px; }
QScrollArea { border: 0; }
QScrollBar:vertical { background: %(surface)s; width: 11px; margin: 0; }
QScrollBar::handle:vertical { background: %(line_soft)s; border-radius: 5px;
                              min-height: 30px; }
QScrollBar::handle:vertical:hover { background: %(accent)s; }
QScrollBar:horizontal { background: %(surface)s; height: 11px; }
QScrollBar::handle:horizontal { background: %(line_soft)s; border-radius: 5px;
                                min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: %(accent)s; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QToolTip { background: %(surface)s; color: %(text)s;
           border: 1px solid %(line_soft)s; padding: 5px; }
#StatCard { background: %(card_grad)s; border: 1px solid %(line)s;
            border-top: 1px solid %(bevel_hi)s;
            border-bottom: 3px solid %(bevel_lo)s; border-radius: 12px; }
#StatKey { color: %(text_mute)s; font-size: 10px; letter-spacing: 1px;
           font-weight: 600; }
#StatValue { color: %(text)s; font-size: 24px; font-weight: 600; }
#StatMeta { color: %(text_mute)s; font-size: 11px; }
#NoticeGreen, #NoticeBlue, #NoticeWarn, #NoticeRed {
    border-radius: 7px; padding: 10px 12px; font-size: 12px; }
#NoticeGreen { background: %(ok_bg)s; border: 1px solid %(ok_line)s;
               color: %(ok)s; }
#NoticeBlue  { background: %(info_bg)s; border: 1px solid %(info_line)s;
               color: %(info)s; }
#NoticeWarn  { background: %(warn_bg)s; border: 1px solid %(warn_line)s;
               color: %(warn)s; }
#NoticeRed   { background: %(err_bg)s; border: 1px solid %(err_line)s;
               color: %(err)s; }
QWidget#Pane { background: transparent; }
""" % tokens


def qt_palette():
    """Keep the pieces Qt draws itself (calendar pop-ups, menus) in step."""
    palette = QPalette()
    pairs = [
        (QPalette.ColorRole.Window, T["window"]),
        (QPalette.ColorRole.WindowText, T["text"]),
        (QPalette.ColorRole.Base, T["raised"]),
        (QPalette.ColorRole.AlternateBase, T["raised2"]),
        (QPalette.ColorRole.Text, T["text"]),
        (QPalette.ColorRole.Button, T["raised"]),
        (QPalette.ColorRole.ButtonText, T["text"]),
        (QPalette.ColorRole.Highlight, T["accent"]),
        (QPalette.ColorRole.HighlightedText, T["accent_text"]),
        (QPalette.ColorRole.ToolTipBase, T["surface"]),
        (QPalette.ColorRole.ToolTipText, T["text"]),
        (QPalette.ColorRole.PlaceholderText, T["text_mute"]),
    ]
    for role, colour in pairs:
        palette.setColor(role, QColor(colour))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,
                     QColor(T["text_mute"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText,
                     QColor(T["text_mute"]))
    return palette


def shadow_colour():
    return QColor(*T["shadow_rgba"])


def elevate(widget, blur=26, drop=7):
    """Lift a surface off the page with a soft shadow beneath it."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, drop)
    effect.setColor(shadow_colour())
    widget.setGraphicsEffect(effect)
    return widget


def apply_theme(app, name):
    """Switch mode and repaint everything that is already on screen."""
    set_theme(name)
    app.setPalette(qt_palette())
    app.setStyleSheet(style_sheet())
    for widget in app.allWidgets():
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        effect = widget.graphicsEffect()
        if isinstance(effect, QGraphicsDropShadowEffect):
            effect.setColor(shadow_colour())     # shadows follow the theme
        widget.update()


# ------------------------------------------------------- small UI helpers
class FlowLayout(QLayout):
    """A layout that wraps its items onto the next line when space runs out.
    Used for the status chips so they never get clipped on a small screen."""

    def __init__(self, spacing=7):
        super().__init__()
        self._items = []
        self._space = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._layout(0, 0, width, apply=False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._layout(rect.x(), rect.y(), rect.width(), apply=True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _layout(self, left, top, width, apply):
        x, y, line_height = left, top, 0
        for item in self._items:
            hint = item.sizeHint()
            if x > left and x + hint.width() > left + width:
                x = left
                y += line_height + self._space
                line_height = 0
            if apply:
                item.setGeometry(QRect(x, y, hint.width(), hint.height()))
            x += hint.width() + self._space
            line_height = max(line_height, hint.height())
        return y + line_height - top


def stamp_text(value):
    """An ISO timestamp as '05 Nov 2026, 10:31' for display in a table."""
    text = str(value or "")
    try:
        when = datetime.fromisoformat(text)
    except ValueError:
        return text[:19].replace("T", " ")
    return "%d %s %d, %02d:%02d" % (when.day, MONTHS[when.month - 1][:3],
                                    when.year, when.hour, when.minute)


def pane():
    """A see-through container, so grouping widgets never paints a dark box."""
    holder = QWidget()
    holder.setObjectName("Pane")
    return holder


def h_line(light=False):
    line = QFrame()
    line.setObjectName("RuleLight" if light else "Rule")
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    return line


def field_label(text, light=False):
    label = QLabel(text.upper())
    label.setObjectName("FieldLabelLight" if light else "FieldLabelDark")
    return label


def notice(kind, text):
    """kind: green | blue | warn | red"""
    label = QLabel(text)
    label.setObjectName("Notice" + kind.capitalize())
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.RichText)
    return label


def button(text, kind=None, small=False, tooltip=None):
    btn = QPushButton(text)
    if kind:
        btn.setProperty("kind", kind)
    if small:
        btn.setProperty("kind", kind or "small")
        btn.setStyleSheet("padding: 2px 9px; font-size: 12px; "
                          "border-bottom-width: 2px; border-radius: 7px;")
        # a stylesheet overrides the style's own metrics, so reserve the width
        # the label actually needs or the caption is clipped inside a table
        btn.setMinimumWidth(btn.fontMetrics().horizontalAdvance(text) + 24)
        btn.setFixedHeight(26)
    if tooltip:
        btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def card(title, hint="", light=False):
    """Returns (frame, body layout, header layout) for a titled panel."""
    frame = QFrame()
    frame.setObjectName("CardLight" if light else "CardDark")
    # a card may grow, but is never squeezed below the height of its contents
    frame.setSizePolicy(QSizePolicy.Policy.Preferred,
                        QSizePolicy.Policy.Minimum)
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(16, 13, 16, 15)
    outer.setSpacing(10)
    header = QHBoxLayout()
    header.setSpacing(10)
    heading = QLabel(title)
    heading.setObjectName("CardHeadLight" if light else "CardHeadDark")
    header.addWidget(heading)
    if hint:
        hint_label = QLabel(hint)
        hint_label.setObjectName("HintLight" if light else "HintDark")
        header.addWidget(hint_label)
    header.addStretch(1)
    outer.addLayout(header)
    body = QVBoxLayout()
    body.setSpacing(10)
    outer.addLayout(body)
    elevate(frame)
    return frame, body, header


def stat_card(key, value, meta="", accent=None):
    frame = QFrame()
    frame.setObjectName("StatCard")
    # the accent stripe is resolved now, not at import, so a theme switch
    # rebuilds these cards in the new palette
    frame.setStyleSheet(
        "#StatCard { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        "stop:0 %s, stop:1 %s); border: 1px solid %s; "
        "border-top: 1px solid %s; border-bottom: 3px solid %s; "
        "border-radius: 12px; border-left: 4px solid %s; }"
        % (T["card_hi"], T["card_lo"], T["line"], T["bevel_hi"],
           T["bevel_lo"], accent or T["accent"]))
    elevate(frame, blur=18, drop=5)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 11, 14, 12)
    layout.setSpacing(1)
    key_label = QLabel(key.upper())
    key_label.setObjectName("StatKey")
    key_label.setWordWrap(True)
    value_label = QLabel(str(value))
    value_label.setObjectName("StatValue")
    layout.addWidget(key_label)
    layout.addWidget(value_label)
    if meta:
        meta_label = QLabel(meta)
        meta_label.setObjectName("StatMeta")
        meta_label.setWordWrap(True)
        layout.addWidget(meta_label)
    frame.setMinimumWidth(152)
    frame.setMinimumHeight(86)
    frame.setSizePolicy(QSizePolicy.Policy.Preferred,
                        QSizePolicy.Policy.Minimum)
    return frame


def table(headers, stretch_column=None):
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.verticalHeader().setVisible(False)
    widget.setAlternatingRowColors(True)
    widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    widget.setWordWrap(False)
    # room for the editors and drop-downs that sit inside the rows
    widget.verticalHeader().setDefaultSectionSize(36)
    header = widget.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    if stretch_column is None:
        header.setStretchLastSection(True)
    else:
        # one named column takes up the slack; stretching the last one as
        # well would push a trailing button column off the edge
        header.setStretchLastSection(False)
        header.setSectionResizeMode(stretch_column,
                                    QHeaderView.ResizeMode.Stretch)
    widget.setMinimumHeight(180)
    return widget


def fit_widget_columns(widget, columns):
    """resizeColumnsToContents ignores cell widgets, so size those columns by
    what the embedded buttons actually need."""
    for column in columns:
        needed = 0
        for row in range(widget.rowCount()):
            holder = widget.cellWidget(row, column)
            if holder is not None:
                needed = max(needed, holder.sizeHint().width())
        if needed:
            widget.setColumnWidth(column, needed + 12)


def cell(text, align_right=False, color=None, bold=False):
    value = "" if text is None else str(text)
    item = QTableWidgetItem(value)
    if len(value) > 14:
        item.setToolTip(value)          # the full text, when a column is tight
    if align_right:
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight
                              | Qt.AlignmentFlag.AlignVCenter)
    else:
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft
                              | Qt.AlignmentFlag.AlignVCenter)
    if color:
        item.setForeground(QColor(color))
    if bold:
        font = item.font()
        font.setBold(True)
        item.setFont(font)
    return item


# ===========================================================================
# SECTION 8 - BACKGROUND WORKERS
# ---------------------------------------------------------------------------
# Document building and mail sending run off the interface thread so the
# window never freezes and progress can be reported per party.
# ===========================================================================

class GenerateWorker(QObject):
    progress = pyqtSignal(int, int, str)          # done, total, party
    produced = pyqtSignal(dict)                   # one finished document
    finished = pyqtSignal(int, int)               # ok, failed

    def __init__(self, confs, folder, make_pdf=True, top_space_cm=0.0):
        super().__init__()
        self.confs = confs
        self.folder = folder
        self.make_pdf = make_pdf
        self.top_space_cm = top_space_cm
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        used, ok, failed = set(), 0, 0
        total = len(self.confs)
        for index, conf in enumerate(self.confs):
            if self._stop:
                break
            self.progress.emit(index, total, conf.get("party_name", ""))
            base = "%s - %s" % (sanitize_filename(conf.get("party_name")),
                                sanitize_filename(conf.get("category")))
            filename = unique_filename(base, ".docx", used)
            record = {"id": conf.get("id"), "filename": filename,
                      "conf": conf, "status": "ok", "path": "",
                      "size": 0, "error": ""}
            try:
                payload = docx_bytes(conf)
                record["size"] = len(payload)
                if self.folder:
                    path = os.path.join(self.folder, filename)
                    with open(path, "wb") as handle:
                        handle.write(payload)
                    record["path"] = path
                record["data"] = payload
                ok += 1
                # the PDF is what is e-mailed and what the client prints; a
                # failure here must not cost the Word letter already written
                record.update({"pdf_filename": "", "pdf_path": "",
                               "pdf_data": b"", "pdf_error": ""})
                if self.make_pdf:
                    try:
                        pdf = pdf_bytes(conf, self.top_space_cm)
                        record["pdf_filename"] = filename[:-5] + ".pdf"
                        record["pdf_data"] = pdf
                        if self.folder:
                            pdf_path = os.path.join(self.folder,
                                                    record["pdf_filename"])
                            with open(pdf_path, "wb") as handle:
                                handle.write(pdf)
                            record["pdf_path"] = pdf_path
                    except Exception as exc:
                        record["pdf_error"] = str(exc)[:300]
            except Exception as exc:
                record["status"] = "failed"
                record["error"] = str(exc)[:300]
                record["data"] = b""
                failed += 1
            self.produced.emit(record)
        self.progress.emit(total, total, "")
        self.finished.emit(ok, failed)


class BridgeWorker(QObject):
    """Reads the JSON feed published by the Gmail Apps Script.  It is a single
    HTTPS GET, but it goes off the interface thread so a slow or unreachable
    deployment never freezes the window."""
    finished = pyqtSignal(list, str)              # replies, error

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            request = urllib.request.Request(
                self.url,
                headers={"User-Agent": "BalanceConfirmationGenerator/"
                                       + APP_VERSION,
                         "Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            self.finished.emit(
                [], "the bridge refused the request (HTTP %s). Check that the "
                    "web app is deployed and that this computer is signed in "
                    "to the same Google account." % exc.code)
            return
        except Exception as exc:
            self.finished.emit([], "could not reach the bridge: %s" % exc)
            return
        try:
            payload = json.loads(raw)
        except Exception:
            # a sign-in page comes back as HTML, which is the usual cause
            self.finished.emit(
                [], "the bridge returned a page rather than data. Open the "
                    "feed address in your browser once and sign in, then try "
                    "again.")
            return
        replies = payload.get("replies") if isinstance(payload, dict) \
            else payload
        if not isinstance(replies, list):
            self.finished.emit([], "the bridge did not return a list of "
                                   "replies.")
            return
        self.finished.emit(replies, "")


class DocumentWorker(QObject):
    """Fetches each reply's own PDF or scan from the bridge and reads it on
    this computer - text layer and OCR.  OCR takes several seconds a page, so
    it runs here, off the interface thread, one reply at a time."""
    progress = pyqtSignal(str, list, str, int, int)   # id, entries, error, n, of
    finished = pyqtSignal(int, int)                   # read, failed

    def __init__(self, url, reply_ids):
        super().__init__()
        self.url = url
        self.reply_ids = list(reply_ids)
        self.stop = False

    def run(self):
        done = failed = 0
        total = len(self.reply_ids)
        for number, reply_id in enumerate(self.reply_ids, start=1):
            if self.stop:
                break
            entries, error = [], ""
            try:
                files, skipped, error = fetch_reply_files(self.url, reply_id)
                for name, kind, data in files:
                    if self.stop:
                        break
                    entries.append(attachment_entry(
                        name, read_document(data, name, kind)))
                if not error and not entries:
                    error = "no PDF or image attached" + (
                        " (%s)" % "; ".join(skipped) if skipped else "")
            except Exception as exc:              # one bad file never stops the rest
                error = str(exc) or exc.__class__.__name__
            if error and not entries:
                failed += 1
            else:
                done += 1
            self.progress.emit(reply_id, entries, error, number, total)
        self.finished.emit(done, failed)


class SendWorker(QObject):
    progress = pyqtSignal(int, int, str)
    result = pyqtSignal(str, str, str, str)   # id, status, detail, Message-ID
    finished = pyqtSignal(int, int)

    def __init__(self, jobs, account, options, delay_ms):
        super().__init__()
        self.jobs = jobs                          # [(conf, filename, bytes)]
        self.account = account
        self.options = options
        self.delay_ms = delay_ms
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        sent, failed = 0, 0
        total = len(self.jobs)
        server = None
        try:
            server = smtp_connect(self.account["host"], self.account["port"],
                                  self.account["security"],
                                  self.account["username"],
                                  self.account["password"])
        except Exception as exc:
            for conf, _, _ in self.jobs:
                self.result.emit(conf["id"], "failed",
                                 friendly_smtp_error(exc), "")
            self.finished.emit(0, total)
            return

        try:
            for index, (conf, filename, payload) in enumerate(self.jobs):
                if self._stop:
                    break
                self.progress.emit(index, total, conf.get("party_name", ""))
                try:
                    message = build_email_message(conf, filename, payload,
                                                  self.options)
                    server.send_message(message)
                    sent += 1
                    self.result.emit(conf["id"], "sent", "",
                                     str(message["Message-ID"] or ""))
                except smtplib.SMTPServerDisconnected:
                    try:                                   # one reconnect
                        server = smtp_connect(
                            self.account["host"], self.account["port"],
                            self.account["security"],
                            self.account["username"], self.account["password"])
                        message = build_email_message(conf, filename,
                                                      payload, self.options)
                        server.send_message(message)
                        sent += 1
                        self.result.emit(conf["id"], "sent", "",
                                         str(message["Message-ID"] or ""))
                    except Exception as exc:
                        failed += 1
                        self.result.emit(conf["id"], "failed",
                                         friendly_smtp_error(exc), "")
                except Exception as exc:
                    failed += 1
                    self.result.emit(conf["id"], "failed",
                                     friendly_smtp_error(exc), "")
                if self.delay_ms and index < total - 1:
                    QThread.msleep(int(self.delay_ms))
        finally:
            try:
                if server:
                    server.quit()
            except Exception:
                pass
        self.progress.emit(total, total, "")
        self.finished.emit(sent, failed)


# ===========================================================================
# SECTION 9 - MAIN WINDOW
# ===========================================================================

ATTACH_MODES = [
    ("PDF letter (as generated)", "pdf"),
    ("Signed PDF on the client's letterhead (your own files)", "signed"),
    ("Word letter (.docx)", "docx"),
]
ATTACH_HINTS = {
    "pdf": "Each party receives the PDF of its letter exactly as generated.",
    "signed": "Each party receives the PDF you link to it: the letter printed "
              "on the client's letterhead, signed and scanned. Link a whole "
              "folder at once, or use Choose PDF… on a row. A party with no "
              "signed PDF linked is held back, never sent an unsigned letter "
              "in its place.",
    "docx": "Each party receives the editable Word letter. A PDF is usually "
            "the better choice: it cannot be altered by accident.",
}

NAV_ITEMS = [
    ("WORKSPACE", None),
    ("01  Dashboard", "dashboard"),
    ("02  Client database", "clients"),
    ("ENGAGEMENT", None),
    ("03  Import data", "import"),
    ("04  Review & mapping", "review"),
    ("05  Letter preview", "preview"),
    ("06  Generate", "generate"),
    ("07  Email delivery", "email"),
    ("RECORDS", None),
    ("08  Confirmations received", "recon"),
    ("09  Saved runs", "runs"),
    ("10  Settings", "settings"),
]


class MainWindow(QMainWindow):

    # ------------------------------------------------------------- set-up
    def __init__(self):
        super().__init__()
        self.setWindowTitle("%s  %s" % (APP_NAME, APP_VERSION))

        self.db, load_error = load_db()
        self.active_client_id = self.db["settings"].get("last_client_id")
        self.active_fy_id = self.db["settings"].get("last_fy_id")

        # import state
        self.source_path = ""
        self.sheets = {}
        self.active_sheet = ""
        self.grid = []
        self.header_index = 0
        self.header_confidence = "low"
        self.columns = []
        self.data_rows = []
        self.mapping = None
        self.records = []
        self.row_filter = "all"
        self.exclude_flagged = True
        self.preview_index = 0

        # output state
        self.generated = []
        self.current_run_id = None
        self.gen_thread = None
        self.gen_worker = None
        self.send_thread = None
        self.send_worker = None
        self.bridge_thread = None
        self.bridge_worker = None
        self.reader_thread = None
        self.reader_worker = None
        self.mail_password = ""
        self.queue = {}

        self._building = True
        self._build_ui()
        self._building = False

        self._load_settings_into_widgets()
        saved_mode = self.db["settings"].get("theme")
        apply_theme(QApplication.instance(),
                    saved_mode if saved_mode in THEMES else "dark")
        self.refresh_theme_button()
        self.style_paper()
        self.refresh_all()
        self.go("dashboard")

        if load_error:
            self.toast("The saved database could not be read (%s). Starting "
                       "with an empty one." % load_error[:120], "warn")

        # the bridge has been collecting replies while this computer was off,
        # so read it once the window is up rather than blocking the start
        if self.db["settings"].get("bridge_sync_on_start", True) and \
                (self.db["settings"].get("bridge_feed_url") or "").strip():
            QTimer.singleShot(1200, lambda: self.sync_bridge(quiet=True))

    # ------------------------------------------------------------ chrome
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._build_topbar())

        self.stack = QStackedWidget()
        self.pages = {}
        for key, builder in (("dashboard", self._page_dashboard),
                             ("clients", self._page_clients),
                             ("import", self._page_import),
                             ("review", self._page_review),
                             ("preview", self._page_preview),
                             ("generate", self._page_generate),
                             ("email", self._page_email),
                             ("recon", self._page_recon),
                             ("runs", self._page_runs),
                             ("settings", self._page_settings)):
            page = builder()
            # below this width the page scrolls sideways rather than squashing
            page.setMinimumWidth(880)
            area = QScrollArea()
            area.setWidgetResizable(True)
            area.setWidget(page)
            self.pages[key] = self.stack.count()
            self.stack.addWidget(area)
        right_layout.addWidget(self.stack, 1)

        self.status_strip = QLabel("")
        self.status_strip.setObjectName("SideFoot")
        self.status_strip.setContentsMargins(18, 5, 18, 7)
        right_layout.addWidget(self.status_strip)
        root.addWidget(right, 1)

        # size the window to the screen it opens on, never larger
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        if available:
            width = min(1380, max(1000, available.width() - 80))
            height = min(900, max(620, available.height() - 90))
            self.resize(width, height)
            self.move(available.x() + (available.width() - width) // 2,
                      available.y() + max(0, (available.height() - height) // 2))
        else:
            self.resize(1280, 820)
        self.setMinimumSize(980, 600)

    def _build_sidebar(self):
        bar = QFrame()
        bar.setObjectName("Sidebar")
        bar.setFixedWidth(232)
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        brand = QWidget()
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(16, 18, 16, 14)
        brand_layout.setSpacing(3)
        mark = QLabel("Balance Confirmation")
        mark.setObjectName("BrandMark")
        mark.setWordWrap(True)
        tag = QLabel("AUDIT CONFIRMATION TOOLKIT")
        tag.setObjectName("BrandTag")
        tag.setWordWrap(True)
        brand_layout.addWidget(mark)
        brand_layout.addWidget(tag)
        layout.addWidget(brand)
        layout.addWidget(h_line())

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.nav_keys = {}
        for text, key in NAV_ITEMS:
            item = QListWidgetItem(text)
            if key is None:
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                font = item.font()
                font.setPointSizeF(max(7.5, font.pointSizeF() - 2.0))
                item.setFont(font)
                item.setForeground(QColor(T["text_mute"]))
            else:
                self.nav_keys[self.nav.count()] = key
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._nav_changed)
        layout.addWidget(self.nav, 1)

        foot = QWidget()
        foot_layout = QVBoxLayout(foot)
        foot_layout.setContentsMargins(16, 10, 16, 14)
        foot_layout.setSpacing(3)
        privacy = QLabel("●  Everything stays on this computer")
        privacy.setObjectName("SideFoot")
        privacy.setWordWrap(True)
        self.db_path_label = QLabel("")
        self.db_path_label.setObjectName("SideFoot")
        self.db_path_label.setWordWrap(True)
        self.db_path_label.setToolTip(DB_PATH)
        self.db_path_label.setText("Records: %s" % os.path.basename(DB_PATH))
        foot_layout.addWidget(h_line())
        foot_layout.addWidget(privacy)
        foot_layout.addWidget(self.db_path_label)
        layout.addWidget(foot)
        return bar

    def _build_topbar(self):
        bar = QFrame()
        bar.setObjectName("TopBar")
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(22, 14, 22, 12)
        layout.setSpacing(3)
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        self.page_title = QLabel("Dashboard")
        self.page_title.setObjectName("PageTitle")
        title_row.addWidget(self.page_title)
        title_row.addStretch(1)
        self.theme_button = QPushButton()
        self.theme_button.setObjectName("ThemeToggle")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.setToolTip("Switch between light and dark mode")
        self.theme_button.clicked.connect(self.toggle_theme)
        title_row.addWidget(self.theme_button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.page_sub = QLabel("Generate audit confirmations from Excel")
        self.page_sub.setObjectName("PageSub")
        layout.addLayout(title_row)
        layout.addWidget(self.page_sub)

        chips = FlowLayout(spacing=7)          # wraps instead of clipping
        self.chip_client = QLabel()
        self.chip_audit = QLabel()
        self.chip_date = QLabel()
        self.chip_team = QLabel()
        self.chip_mail = QLabel()
        self.chip_status = QLabel()
        for chip in (self.chip_client, self.chip_audit, self.chip_date,
                     self.chip_team, self.chip_mail, self.chip_status):
            chip.setProperty("chip", "neutral")
            chips.addWidget(chip)
        layout.addLayout(chips)
        return bar

    def _nav_changed(self, row):
        key = self.nav_keys.get(row)
        if key:
            self.go(key)

    # ---------------------------------------------------------- theming
    def toggle_theme(self):
        self.set_mode("light" if is_dark() else "dark")

    def set_mode(self, name):
        apply_theme(QApplication.instance(), name)
        self.db["settings"]["theme"] = name
        self.persist()
        self.refresh_theme_button()
        self.restyle()

    def refresh_theme_button(self):
        self.theme_button.setText("\u25d0  Light mode" if is_dark()
                                  else "\u25d1  Dark mode")

    def restyle(self):
        """Re-apply the handful of inline styles and redraw coloured cells."""
        self.style_paper()
        if hasattr(self, "drop_zone"):
            self.drop_zone.repaint_frame(False)
        for label in (self.header_note, self.map_warning, self.pv_warning,
                      self.mail_state):
            label.setStyleSheet(style_sheet())
        self.refresh_all()
        current = self.stack.currentIndex()
        if current == self.pages["preview"]:
            self.render_preview()
        elif current == self.pages["email"]:
            self.refresh_email()
        elif current == self.pages["settings"]:
            self.refresh_settings()
        elif current == self.pages["runs"]:
            self.refresh_runs()
        elif current == self.pages["generate"]:
            self.refresh_generate()
        elif current == self.pages["recon"]:
            self.refresh_recon()

    def go(self, key):
        self.stack.setCurrentIndex(self.pages[key])
        for row, name in self.nav_keys.items():
            if name == key and self.nav.currentRow() != row:
                self.nav.blockSignals(True)
                self.nav.setCurrentRow(row)
                self.nav.blockSignals(False)
        titles = {
            "dashboard": ("Dashboard", "Everything the generator needs before "
                                       "letters are produced"),
            "clients": ("Client database", "Clients, financial years and "
                                           "saved records on this computer"),
            "import": ("Import data", "Read the party-wise balance schedule"),
            "review": ("Review & mapping", "Confirm the detected columns and "
                                           "categories"),
            "preview": ("Letter preview", "Exactly what the Word file will "
                                          "contain"),
            "generate": ("Generate",
                         "Produce a Word letter and a PDF for each party"),
            "email": ("Email delivery", "Send each letter from your own "
                                        "mailbox"),
            "recon": ("Confirmations received", "Replies reconciled against "
                                                "what was sent"),
            "runs": ("Saved runs", "Every generation, by client and year"),
            "settings": ("Settings", "Engagement, audit team and firm details"),
        }
        title, subtitle = titles.get(key, (key.title(), ""))
        self.page_title.setText(title)
        self.page_sub.setText(subtitle)
        if key == "preview":
            self.render_preview()
        elif key == "generate":
            self.refresh_generate()
        elif key == "email":
            self.refresh_email()
        elif key == "recon":
            self.refresh_recon()
        elif key == "runs":
            self.refresh_runs()
        elif key == "settings":
            self.refresh_settings()
        elif key == "dashboard":
            self.refresh_dashboard()

    # ------------------------------------------------------------ helpers
    def toast(self, text, kind="info"):
        prefix = {"info": "", "ok": "✓  ", "warn": "⚠  ",
                  "err": "✕  "}.get(kind, "")
        colour = {"ok": T["ok"], "warn": T["warn"], "err": T["err"]}.get(
            kind, T["text_soft"])
        self.status_strip.setText(prefix + text)
        self.status_strip.setStyleSheet("color: %s;" % colour)
        QTimer.singleShot(9000, lambda: (
            self.status_strip.setText("")
            if self.status_strip.text() == prefix + text else None))

    def ask(self, title, text, confirm="Confirm", danger=True):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        box.setIcon(QMessageBox.Icon.Warning if danger
                    else QMessageBox.Icon.Question)
        yes = box.addButton(confirm, QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() is yes

    def persist(self):
        ok, error = save_db(self.db)
        if not ok:
            self.toast("The records could not be saved: %s" % error, "err")
        return ok

    def active_client(self):
        for client in self.db["clients"]:
            if client["id"] == self.active_client_id:
                return client
        return None

    def active_fy(self):
        client = self.active_client()
        if not client:
            return None
        for year in client["financial_years"]:
            if year["id"] == self.active_fy_id:
                return year
        return None

    def auditors(self):
        return [a for a in self.db["settings"].get("auditors", [])
                if valid_email(a.get("email"))]

    def mail_settings(self):
        return self.db["settings"]["mail"]

    # =====================================================================
    # PAGE 01 - DASHBOARD
    # =====================================================================
    def _page_dashboard(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        frame, body, header = card(
            "Engagement readiness",
            "Everything the generator needs before letters are produced")
        import_btn = button("Import data")
        import_btn.clicked.connect(lambda: self.go("import"))
        gen_btn = button("Go to generate", "primary")
        gen_btn.clicked.connect(lambda: self.go("generate"))
        header.addWidget(import_btn)
        header.addWidget(gen_btn)
        self.dash_checks = QVBoxLayout()
        self.dash_checks.setSpacing(6)
        body.addLayout(self.dash_checks)
        layout.addWidget(frame)

        frame2, body2, _ = card("Portfolio summary",
                                "Current import, by balance category")
        self.dash_stats = QHBoxLayout()
        self.dash_stats.setSpacing(10)
        body2.addLayout(self.dash_stats)
        layout.addWidget(frame2)

        frame2b, body2b, header2b = card(
            "Confirmations received",
            "Replies reconciled against what was sent")
        open_recon = button("Open the reports")
        open_recon.clicked.connect(lambda: self.go("recon"))
        header2b.addWidget(open_recon)
        self.dash_recon = QHBoxLayout()
        self.dash_recon.setSpacing(10)
        body2b.addLayout(self.dash_recon)
        layout.addWidget(frame2b)

        row = QHBoxLayout()
        row.setSpacing(16)
        frame3, body3, _ = card("How this works")
        steps = QLabel(
            "<ol style='margin-left:-20px; line-height:170%'>"
            "<li>Create the client and its financial year in "
            "<b>Client database</b>.</li>"
            "<li>Choose the <b>type of audit</b> and whether the confirmation "
            "is for a year end or a period end, in <b>Settings</b>.</li>"
            "<li>Add the audit team members who should receive replies.</li>"
            "<li>Import the balance schedule in <b>Import data</b>.</li>"
            "<li>Confirm the detected columns in <b>Review &amp; mapping</b>."
            "</li>"
            "<li>Check one letter in <b>Letter preview</b>, then produce the "
            "files in <b>Generate</b>.</li>"
            "<li>Send them from your own mailbox in <b>Email delivery</b>.</li>"
            "</ol>")
        steps.setWordWrap(True)
        steps.setTextFormat(Qt.TextFormat.RichText)
        body3.addWidget(steps)
        row.addWidget(frame3, 1)

        frame4, body4, _ = card("Data handling")
        body4.addWidget(notice(
            "green", "Your spreadsheet is read on this computer. Nothing is "
                     "uploaded anywhere."))
        body4.addWidget(notice(
            "blue", "Letters, the local records and the preview are all built "
                    "here. Data leaves this computer only when you press "
                    "<b>Send</b> in Email delivery, and then it goes to your "
                    "own mail server."))
        body4.addWidget(notice(
            "warn", "Use an <b>app password</b> for Gmail, Outlook, Yahoo and "
                    "Zoho, never your main account password."))
        body4.addStretch(1)
        row.addWidget(frame4, 1)
        layout.addLayout(row)
        layout.addStretch(1)
        return page

    def _clear(self, layout):
        """Empty a layout completely.  Widgets are detached at once, not just
        scheduled for deletion, so nothing stale is left on screen."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
                continue
            child = item.layout()
            if child is not None:
                self._clear(child)
                child.deleteLater()

    def refresh_dashboard(self):
        checks = self.validation()
        self._clear(self.dash_checks)
        last = len(checks["items"]) - 1
        for index, item in enumerate(checks["items"]):
            soft = (index == last and not item["ok"] and self.exclude_flagged)
            mark = "✓" if item["ok"] else ("!" if soft else "✕")
            colour = T["ok"] if item["ok"] else (T["warn"] if soft
                                                   else T["err"])
            row = QHBoxLayout()
            row.setSpacing(9)
            box = QLabel(mark)
            box.setFixedWidth(18)
            box.setStyleSheet("color:%s; font-weight:700;" % colour)
            text = QLabel("<b>%s</b><br><span style='color:%s; font-size:11px'>"
                          "%s%s</span>"
                          % (item["title"], T["text_mute"], item["detail"],
                             " — these rows will be skipped" if soft
                             else ""))
            text.setWordWrap(True)
            text.setTextFormat(Qt.TextFormat.RichText)
            row.addWidget(box, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(text, 1)
            self.dash_checks.addLayout(row)

        self._clear(self.dash_stats)
        counts = self.category_counts()
        for key, value, meta, accent in (
                ("Rows imported", len(self.records),
                 os.path.basename(self.source_path) if self.source_path
                 else "No file yet", T["accent"]),
                ("Trade Receivable", counts["Trade Receivable"],
                 "Owed to the client", T["accent"]),
                ("Trade Payable", counts["Trade Payable"],
                 "Owed by the client", T["info"]),
                ("Advance from Customers", counts["Advance from Customers"],
                 "Received by the client", T["accent"]),
                ("Advance to Vendors", counts["Advance to Vendors"],
                 "Paid by the client", T["info"]),
                ("Needs review", counts["review"],
                 "Category or name missing", T["warn"]),
                ("Generated", len([g for g in self.generated
                                   if g["status"] == "ok"]),
                 "This session", T["err"])):
            self.dash_stats.addWidget(stat_card(key, value, meta, accent))
        self.dash_stats.addStretch(1)

        # confirmations that have come back, across every run for this year
        rows, _exceptions = build_reconciliation(
            self.sent_documents(), self.stored_replies(),
            tolerance=float(self.db["settings"].get("variance_tolerance",
                                                    DEFAULT_TOLERANCE)),
            reminders=tuple(self.db["settings"].get("reminder_days",
                                                    DEFAULT_REMINDERS)))
        summary = summarise(rows)
        self._clear(self.dash_recon)
        for key, value, meta, accent in (
                ("Sent", summary["sent"], "Confirmations issued", T["accent"]),
                ("Received", summary["received"], "Replies matched", T["info"]),
                ("Matched", summary["agreed"], "No variance", T["ok"]),
                ("With variance", summary["variance"], "Difference found",
                 T["warn"]),
                ("Pending", summary["pending"], "No reply yet",
                 T["text_mute"]),
                ("Coverage", "%.1f%%" % summary["coverage_pct"],
                 "By value of balances", T["accent_hi"])):
            self.dash_recon.addWidget(stat_card(key, value, meta, accent))
        self.dash_recon.addStretch(1)

    # =====================================================================
    # PAGE 02 - CLIENT DATABASE
    # =====================================================================
    def _page_clients(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        top = QHBoxLayout()
        top.setSpacing(16)

        frame, body, _ = card("Add client", "Stored on this computer only",
                              light=True)
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.cl_name = QLineEdit()
        self.cl_name.setPlaceholderText("Example Manufacturing Private Limited")
        self.cl_city = QLineEdit()
        self.cl_city.setPlaceholderText("Mumbai")
        self.cl_code = QLineEdit()
        self.cl_code.setPlaceholderText("EMPL-01")
        self.cl_notes = QLineEdit()
        self.cl_notes.setPlaceholderText("Statutory audit — FY 2026-27")
        for label, widget in (
                ("Client name (as it should appear in the letter)",
                 self.cl_name),
                ("City / place", self.cl_city),
                ("Client code", self.cl_code),
                ("Notes", self.cl_notes)):
            form.addRow(field_label(label, light=True), widget)
        body.addLayout(form)
        add_client = button("+  Add client", "primary")
        add_client.clicked.connect(self.add_client)
        self.cl_name.returnPressed.connect(self.add_client)
        body.addWidget(add_client, 0, Qt.AlignmentFlag.AlignLeft)
        top.addWidget(frame, 1)

        frame2, body2, _ = card("Financial years", "", light=True)
        self.fy_for = QLabel("No client selected")
        self.fy_for.setObjectName("HintLight")
        body2.addWidget(self.fy_for)
        fy_form = QHBoxLayout()
        fy_form.setSpacing(8)
        self.fy_year = QLineEdit()
        self.fy_year.setPlaceholderText("2026-27")
        self.fy_end = QDateEdit()
        self.fy_end.setCalendarPopup(True)
        self.fy_end.setDisplayFormat("dd MMMM yyyy")
        self.fy_end.setDate(QDate(date.today().year + 1, 3, 31))
        left = QVBoxLayout()
        left.addWidget(field_label("Financial year", light=True))
        left.addWidget(self.fy_year)
        right = QVBoxLayout()
        right.addWidget(field_label("Financial year end", light=True))
        right.addWidget(self.fy_end)
        fy_form.addLayout(left, 1)
        fy_form.addLayout(right, 1)
        body2.addLayout(fy_form)
        add_year = button("+  Add year", "primary")
        add_year.clicked.connect(self.add_year)
        body2.addWidget(add_year, 0, Qt.AlignmentFlag.AlignLeft)
        hint = QLabel("The audit type and the year-end or period-end date are "
                      "set per financial year, in Settings.")
        hint.setObjectName("HintLight")
        hint.setWordWrap(True)
        body2.addWidget(hint)
        body2.addWidget(h_line(light=True))
        self.fy_table = table(["Year", "Type of audit", "Confirmation as at",
                               "Runs", ""])
        self.fy_table.setMinimumHeight(150)
        body2.addWidget(self.fy_table)
        top.addWidget(frame2, 1)
        layout.addLayout(top)

        frame3, body3, header3 = card("Clients on this computer", "",
                                      light=True)
        self.cl_count = QLabel("")
        self.cl_count.setObjectName("HintLight")
        header3.addWidget(self.cl_count)
        self.cl_table = table(["Client", "Code", "Years", "Active year",
                               "Added", ""], stretch_column=0)
        body3.addWidget(self.cl_table)
        layout.addWidget(frame3)

        frame4, body4, _ = card("Records file", "Backup and restore")
        self.db_note = QLabel("")
        self.db_note.setObjectName("HintDark")
        self.db_note.setWordWrap(True)
        body4.addWidget(self.db_note)
        buttons = QHBoxLayout()
        buttons.setSpacing(9)
        export_btn = button("Export records (JSON)", "brass")
        export_btn.clicked.connect(self.export_db)
        import_btn = button("Import records…")
        import_btn.clicked.connect(self.import_db)
        folder_btn = button("Open records folder")
        folder_btn.clicked.connect(self.open_db_folder)
        clear_btn = button("Clear all data", "danger")
        clear_btn.clicked.connect(self.clear_db)
        for widget in (export_btn, import_btn, folder_btn, clear_btn):
            buttons.addWidget(widget)
        buttons.addStretch(1)
        body4.addLayout(buttons)
        layout.addWidget(frame4)
        layout.addStretch(1)
        return page

    def add_client(self):
        name = self.cl_name.text().strip()
        if not name:
            self.toast("Enter the client name as it should appear in the "
                       "letter.", "warn")
            self.cl_name.setFocus()
            return
        for client in self.db["clients"]:
            if client["name"].lower() == name.lower():
                self.toast("That client already exists — selecting it.",
                           "info")
                self.set_active_client(client["id"])
                return
        client = {"id": new_id(), "name": name,
                  "city": self.cl_city.text().strip(),
                  "code": self.cl_code.text().strip(),
                  "notes": self.cl_notes.text().strip(),
                  "created_at": datetime.now().isoformat(timespec="seconds"),
                  "financial_years": []}
        self.db["clients"].append(client)
        for widget in (self.cl_name, self.cl_city, self.cl_code, self.cl_notes):
            widget.clear()
        self.set_active_client(client["id"])
        self.toast("Client added: %s" % name, "ok")

    def set_active_client(self, client_id):
        self.active_client_id = client_id
        self.db["settings"]["last_client_id"] = client_id
        client = self.active_client()
        years = client["financial_years"] if client else []
        self.active_fy_id = years[-1]["id"] if years else None
        self.db["settings"]["last_fy_id"] = self.active_fy_id
        self.persist()
        self.refresh_all()

    def set_active_fy(self, fy_id):
        self.active_fy_id = fy_id
        self.db["settings"]["last_fy_id"] = fy_id
        self.persist()
        self.refresh_all()

    def add_year(self):
        client = self.active_client()
        if not client:
            self.toast("Select a client first.", "warn")
            return
        label = self.fy_year.text().strip()
        if not label:
            self.toast("Enter the financial year, for example 2026-27.", "warn")
            return
        if any(y["year"].lower() == label.lower()
               for y in client["financial_years"]):
            self.toast("That financial year already exists for this client.",
                       "warn")
            return
        year = {"id": new_id(), "year": label,
                "year_end": self.fy_end.date().toString("yyyy-MM-dd"),
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "audit_type": self.db["settings"].get("last_audit_type",
                                                      "Statutory Audit"),
                "audit_type_other": "", "basis": "year",
                "period_start": "", "period_end": ""}
        client["financial_years"].append(year)
        self.fy_year.clear()
        self.set_active_fy(year["id"])
        self.toast("Financial year %s added." % label, "ok")

    def refresh_clients(self):
        clients = self.db["clients"]
        self.cl_count.setText("%d client%s" % (len(clients),
                                               "" if len(clients) == 1 else "s"))
        self.cl_table.setRowCount(0)
        for client in clients:
            row = self.cl_table.rowCount()
            self.cl_table.insertRow(row)
            is_active = client["id"] == self.active_client_id
            name = client["name"] + ("   ● active" if is_active else "")
            self.cl_table.setItem(row, 0, cell(name, bold=is_active,
                                               color=T["ok"] if is_active
                                               else None))
            self.cl_table.setItem(row, 1, cell(client.get("code") or "—"))
            self.cl_table.setItem(row, 2, cell(len(client["financial_years"]),
                                               align_right=True))
            active_year = self.active_fy() if is_active else None
            self.cl_table.setItem(row, 3, cell(
                "%s (%s)" % (active_year["year"],
                             fmt_date_long(fy_as_at(active_year)))
                if active_year else "—"))
            created = (client.get("created_at") or "")[:10]
            self.cl_table.setItem(row, 4, cell(created))
            holder = pane()
            box = QHBoxLayout(holder)
            box.setContentsMargins(4, 2, 4, 2)
            box.setSpacing(5)
            select = button("Selected" if is_active else "Select",
                            None if is_active else "primary", small=True)
            select.setEnabled(not is_active)
            select.clicked.connect(
                lambda _, cid=client["id"]: self.set_active_client(cid))
            delete = button("Delete", "danger", small=True)
            delete.clicked.connect(
                lambda _, c=client: self.delete_client(c))
            box.addWidget(select)
            box.addWidget(delete)
            box.addStretch(1)
            self.cl_table.setCellWidget(row, 5, holder)
        self.cl_table.resizeColumnsToContents()
        fit_widget_columns(self.cl_table, [5])

        client = self.active_client()
        self.fy_for.setText("For %s" % client["name"] if client
                            else "No client selected")
        self.fy_table.setRowCount(0)
        for year in (client["financial_years"] if client else []):
            row = self.fy_table.rowCount()
            self.fy_table.insertRow(row)
            is_active = year["id"] == self.active_fy_id
            self.fy_table.setItem(row, 0, cell(
                year["year"] + ("   ●" if is_active else ""),
                bold=is_active, color=T["ok"] if is_active else None))
            audit = fy_audit_type(year)
            if audit == "Other":
                audit = year.get("audit_type_other") or "Other"
            self.fy_table.setItem(row, 1, cell(audit))
            as_at = fy_as_at(year)
            self.fy_table.setItem(row, 2, cell(
                "%s  (%s)" % (fmt_date_long(as_at), fy_basis_label(year))
                if as_at else "— not set —"))
            runs = len([r for r in self.db["runs"] if r.get("fy_id") == year["id"]])
            self.fy_table.setItem(row, 3, cell(runs, align_right=True))
            holder = pane()
            box = QHBoxLayout(holder)
            box.setContentsMargins(4, 2, 4, 2)
            box.setSpacing(5)
            select = button("Selected" if is_active else "Select", small=True)
            select.setEnabled(not is_active)
            select.clicked.connect(
                lambda _, yid=year["id"]: self.set_active_fy(yid))
            delete = button("Delete", "danger", small=True)
            delete.clicked.connect(lambda _, y=year: self.delete_year(y))
            box.addWidget(select)
            box.addWidget(delete)
            box.addStretch(1)
            self.fy_table.setCellWidget(row, 4, holder)
        self.fy_table.resizeColumnsToContents()
        fit_widget_columns(self.fy_table, [4])

        documents = sum(len(r.get("documents", [])) for r in self.db["runs"])
        years = sum(len(c["financial_years"]) for c in self.db["clients"])
        self.db_note.setText(
            "%d clients · %d financial years · %d saved runs · "
            "%d documents recorded<br><span style='font-size:11px'>Stored at "
            "%s</span>" % (len(clients), years, len(self.db["runs"]),
                           documents, DB_PATH))
        self.db_note.setTextFormat(Qt.TextFormat.RichText)

    def delete_client(self, client):
        if not self.ask("Delete client",
                        "Delete %s, its financial years and all saved runs "
                        "for it? This cannot be undone." % client["name"],
                        "Delete client"):
            return
        self.db["clients"] = [c for c in self.db["clients"]
                              if c["id"] != client["id"]]
        self.db["runs"] = [r for r in self.db["runs"]
                           if r.get("client_id") != client["id"]]
        if self.active_client_id == client["id"]:
            self.active_client_id = None
            self.active_fy_id = None
        self.persist()
        self.refresh_all()
        self.toast("Client deleted.", "ok")

    def delete_year(self, year):
        client = self.active_client()
        if not client:
            return
        runs = len([r for r in self.db["runs"] if r.get("fy_id") == year["id"]])
        if not self.ask("Delete financial year",
                        "Delete %s and its %d saved run(s)?"
                        % (year["year"], runs), "Delete year"):
            return
        client["financial_years"] = [y for y in client["financial_years"]
                                     if y["id"] != year["id"]]
        self.db["runs"] = [r for r in self.db["runs"]
                           if r.get("fy_id") != year["id"]]
        if self.active_fy_id == year["id"]:
            self.active_fy_id = (client["financial_years"][0]["id"]
                                 if client["financial_years"] else None)
        self.persist()
        self.refresh_all()
        self.toast("Financial year deleted.", "ok")

    def export_db(self):
        suggested = os.path.join(
            self.db["settings"].get("output_folder") or os.path.expanduser("~"),
            "balance-confirmation-records-%s.json" % date.today().isoformat())
        path, _ = QFileDialog.getSaveFileName(
            self, "Export records", suggested, "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self.db, handle, indent=2, ensure_ascii=False)
            self.toast("Records exported to %s" % path, "ok")
        except Exception as exc:
            self.toast("Export failed: %s" % exc, "err")

    def import_db(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import records", os.path.expanduser("~"),
            "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception as exc:
            self.toast("That file is not valid JSON: %s" % exc, "err")
            return
        if not isinstance(data, dict) or "clients" not in data:
            self.toast("That file is not a Balance Confirmation backup.", "err")
            return

        box = QMessageBox(self)
        box.setWindowTitle("Import records")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText("The backup holds %d clients and %d runs."
                    % (len(data.get("clients") or []),
                       len(data.get("runs") or [])))
        box.setInformativeText(
            "Merge keeps what you already have and adds anything new. "
            "Replace discards the current records.")
        merge = box.addButton("Merge", QMessageBox.ButtonRole.AcceptRole)
        replace = box.addButton("Replace", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked not in (merge, replace):
            return

        incoming = normalise_db(data)
        if clicked is replace:
            self.db = incoming
        else:
            existing = {c["name"].lower(): c for c in self.db["clients"]}
            for client in incoming["clients"]:
                match = existing.get(client["name"].lower())
                if not match:
                    self.db["clients"].append(client)
                    existing[client["name"].lower()] = client
                    continue
                known = {y["year"] for y in match["financial_years"]}
                for year in client["financial_years"]:
                    if year["year"] not in known:
                        match["financial_years"].append(year)
            seen = {r.get("id") for r in self.db["runs"]}
            for run in incoming["runs"]:
                if run.get("id") not in seen:
                    self.db["runs"].append(run)
        self.active_client_id = None
        self.active_fy_id = None
        self.persist()
        self._load_settings_into_widgets()
        self.refresh_all()
        self.toast("Records imported.", "ok")

    def open_db_folder(self):
        folder = app_data_dir()
        try:
            if os.name == "nt":
                os.startfile(folder)                       # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
            self.toast("Opened %s" % folder, "ok")
        except Exception:
            self.toast("The records are at %s" % folder, "info")

    def clear_db(self):
        if not self.ask("Clear all data",
                        "This removes every client, financial year and saved "
                        "run from this computer. Export a backup first if you "
                        "need one.", "Clear everything"):
            return
        self.db = blank_db()
        self.active_client_id = None
        self.active_fy_id = None
        self.persist()
        self._load_settings_into_widgets()
        self.refresh_all()
        self.toast("All local data cleared.", "ok")

    # =====================================================================
    # PAGE 03 - IMPORT DATA
    # =====================================================================
    def _page_import(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        frame, body, _ = card("Open the balance schedule",
                              ".xlsx  ·  .xls  ·  .csv")
        body.addWidget(notice("green", "The file is read on this computer and "
                                       "is never modified or uploaded."))
        self.drop_zone = DropZone(self.load_file)
        body.addWidget(self.drop_zone)
        self.file_status = QLabel("")
        self.file_status.setObjectName("HintDark")
        self.file_status.setWordWrap(True)
        self.file_status.setTextFormat(Qt.TextFormat.RichText)
        body.addWidget(self.file_status)

        self.sheet_row = pane()
        sheet_layout = QHBoxLayout(self.sheet_row)
        sheet_layout.setContentsMargins(0, 4, 0, 0)
        sheet_layout.setSpacing(10)
        left = QVBoxLayout()
        left.setSpacing(4)
        left.addWidget(field_label("Worksheet"))
        self.sheet_combo = QComboBox()
        self.sheet_combo.currentTextChanged.connect(self.on_sheet_changed)
        left.addWidget(self.sheet_combo)
        middle = QVBoxLayout()
        middle.setSpacing(4)
        middle.addWidget(field_label("Header row"))
        self.header_combo = QComboBox()
        self.header_combo.currentIndexChanged.connect(self.on_header_changed)
        middle.addWidget(self.header_combo)
        sheet_layout.addLayout(left, 1)
        sheet_layout.addLayout(middle, 2)
        redetect = button("Re-run detection")
        redetect.clicked.connect(lambda: self.load_sheet(self.active_sheet,
                                                         None))
        sheet_layout.addWidget(redetect, 0, Qt.AlignmentFlag.AlignBottom)
        self.sheet_row.setVisible(False)
        body.addWidget(self.sheet_row)
        self.header_note = QLabel("")
        self.header_note.setWordWrap(True)
        self.header_note.setVisible(False)
        body.addWidget(self.header_note)
        layout.addWidget(frame)

        frame_t, body_t, header_t = card(
            "Sample template",
            "A ready-to-fill Excel file the application reads without mapping")
        download = button("Download sample template (.xlsx)", "primary")
        download.setToolTip("Saves an Excel workbook with the right headings, "
                            "a category drop-down, four example rows and a "
                            "sheet of instructions")
        download.clicked.connect(self.download_sample_template)
        header_t.addWidget(download)
        template_note = QLabel(
            "Give this file to the client, or paste the client's listing into "
            "it. Its headings are <b>Name</b>, <b>Address line 1</b>, "
            "<b>Pincode</b>, <b>State</b>, <b>Country</b>, <b>Currency</b>, "
            "<b>Closing balance</b>, <b>Category</b>, <b>Email ID</b> and "
            "<b>Contact person</b>. Only <b>Name</b> is compulsory; the "
            "category is picked from a drop-down so every row lands on one of "
            "the four letter formats.")
        template_note.setObjectName("HintDark")
        template_note.setTextFormat(Qt.TextFormat.RichText)
        template_note.setWordWrap(True)
        body_t.addWidget(template_note)
        layout.addWidget(frame_t)

        frame2, body2, header2 = card("Worksheet preview", "", light=True)
        self.preview_note = QLabel("Nothing imported yet")
        self.preview_note.setObjectName("HintLight")
        header2.addWidget(self.preview_note)
        self.sheet_table = table([""])
        self.sheet_table.setMinimumHeight(300)
        body2.addWidget(self.sheet_table)
        layout.addWidget(frame2, 1)
        return page

    def download_sample_template(self, _checked=False, path=None):
        """Save the built-in party listing template wherever the user says."""
        if not path:
            start = os.path.join(
                self.db["settings"].get("output_folder") or
                os.path.expanduser("~"), SAMPLE_TEMPLATE_NAME)
            path, _ = QFileDialog.getSaveFileName(
                self, "Save the sample template", start,
                "Excel workbook (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            write_sample_template(path)
        except Exception as exc:
            self.toast("The template could not be saved: %s" % exc, "err")
            return
        self.toast("Sample template saved to %s" % path, "ok")
        return path

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open balance schedule",
            self.db["settings"].get("output_folder") or os.path.expanduser("~"),
            "Spreadsheets (*.xlsx *.xlsm *.xls *.csv);;All files (*)")
        if path:
            self.load_file(path)

    def load_file(self, path):
        if not os.path.exists(path):
            self.toast("That file could not be found.", "err")
            return
        if not re.search(r"\.(xlsx|xlsm|xls|csv)$", path, re.I):
            self.file_status.setText(
                "<span style='color:#eda28e'>Unsupported file type. Choose an "
                ".xlsx, .xls or .csv file.</span>")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            sheets = read_workbook(path)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self.file_status.setText(
                "<span style='color:#eda28e'>%s</span>"
                % str(exc).replace("\n", "<br>"))
            self.toast("The file could not be read.", "err")
            return
        QApplication.restoreOverrideCursor()

        if not sheets:
            self.file_status.setText("<span style='color:#eda28e'>The "
                                     "workbook contains no worksheets.</span>")
            return
        self.source_path = path
        self.sheets = sheets
        with_data = [name for name, grid in sheets.items()
                     if any(any(clean(c) for c in (row or []))
                            for row in grid)]
        first = with_data[0] if with_data else list(sheets)[0]
        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()
        self.sheet_combo.addItems(list(sheets))
        self.sheet_combo.setCurrentText(first)
        self.sheet_combo.blockSignals(False)
        self.sheet_row.setVisible(True)
        self.header_note.setVisible(True)
        self.load_sheet(first, None)

    def on_sheet_changed(self, name):
        if name and not self._building:
            self.load_sheet(name, None)

    def on_header_changed(self, index):
        if index >= 0 and not self._building and self.active_sheet:
            self.load_sheet(self.active_sheet, index)

    def load_sheet(self, name, forced_header):
        if not name or name not in self.sheets:
            return
        self.active_sheet = name
        self.grid = trim_grid(self.sheets[name])
        if not self.grid:
            self.file_status.setText(
                "<span style='color:#eda28e'>Worksheet <b>%s</b> is empty. "
                "Choose another worksheet.</span>" % name)
            self.records, self.mapping, self.columns = [], None, []
            self.data_rows = []
            self.refresh_all()
            return

        detected = detect_header_row(self.grid)
        self.header_index = (detected["index"] if forced_header is None
                             else forced_header)
        self.header_confidence = (detected["confidence"]
                                  if forced_header is None else "high")

        self.header_combo.blockSignals(True)
        self.header_combo.clear()
        for r in range(min(len(self.grid), 25)):
            preview = " | ".join(
                [c for c in (clean(v) for v in (self.grid[r] or [])) if c][:6])
            if len(preview) > 70:
                preview = preview[:70] + "…"
            self.header_combo.addItem("Row %d  —  %s"
                                      % (r + 1, preview or "(blank)"))
        self.header_combo.setCurrentIndex(min(self.header_index,
                                              self.header_combo.count() - 1))
        self.header_combo.blockSignals(False)

        if self.header_confidence == "high":
            self.header_note.setText(
                "Header row detected automatically at <b>row %d</b>. Change it "
                "above if that is not right." % (self.header_index + 1))
            self.header_note.setObjectName("NoticeBlue")
        else:
            self.header_note.setText(
                "The header row could not be identified with confidence — "
                "<b>row %d</b> was assumed. Please check the selection above."
                % (self.header_index + 1))
            self.header_note.setObjectName("NoticeWarn")
        self.header_note.setStyleSheet("")
        self.header_note.setStyleSheet(style_sheet())

        built = build_columns(self.grid, self.header_index)
        self.columns = built["columns"]
        self.data_rows = built["data_rows"]
        self.mapping = detect_mapping(self.columns)
        self.build_records(reset=True)

        size_kb = os.path.getsize(self.source_path) / 1024.0
        self.file_status.setText(
            "<b>%s</b> · %.1f KB · worksheet <b>%s</b> · %d "
            "data rows · %d columns"
            % (os.path.basename(self.source_path), size_kb, name,
               len(self.data_rows), len(self.columns)))
        self.render_sheet_preview()
        self.refresh_all()
        self.toast("%d rows read from %s." % (len(self.data_rows), name), "ok")

    def render_sheet_preview(self):
        rows = self.data_rows[:15]
        self.sheet_table.clear()
        self.sheet_table.setColumnCount(len(self.columns) + 1)
        self.sheet_table.setHorizontalHeaderLabels(
            ["#"] + [c["label"] for c in self.columns])
        self.sheet_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.sheet_table.setItem(r, 0, cell(r + 1, align_right=True,
                                                color=T["text_mute"]))
            for c, column in enumerate(self.columns):
                index = column["index"]
                value = clean(row[index]) if index < len(row) else ""
                self.sheet_table.setItem(r, c + 1, cell(value))
        self.sheet_table.resizeColumnsToContents()
        self.preview_note.setText(
            "Showing %d of %d rows · %d columns"
            % (len(rows), len(self.data_rows), len(self.columns)))

    # =====================================================================
    # RECORDS
    # =====================================================================
    def build_records(self, reset=False):
        if not self.mapping:
            self.records = []
            return
        previous = {} if reset else {r["key"]: r for r in self.records}
        default_currency = (self.db["settings"].get("default_currency")
                            or "INR").upper()
        records = []
        for index, row in enumerate(self.data_rows):
            key = "r%d" % index

            def value_at(col):
                return clean(row[col]) if col < len(row) else ""

            mapping = self.mapping
            name = (value_at(mapping["partyName"]["cols"][0])
                    if mapping["partyName"]["cols"] else "")
            address = []
            for col in mapping["address"]["cols"]:
                text = value_at(col)
                if text:
                    address.extend([p.strip() for p in text.splitlines()
                                    if p.strip()])
            raw_amount = (row[mapping["amount"]["cols"][0]]
                          if mapping["amount"]["cols"]
                          and mapping["amount"]["cols"][0] < len(row) else None)
            amount, currency_from_text, _ = parse_amount(raw_amount)
            currency = (value_at(mapping["currency"]["cols"][0]).upper()
                        if mapping["currency"]["cols"] else "")
            if not currency:
                currency = currency_from_text or default_currency
            category_raw = (value_at(mapping["category"]["cols"][0])
                            if mapping["category"]["cols"] else "")
            email = (value_at(mapping["email"]["cols"][0])
                     if mapping["email"]["cols"] else "")
            contact = (value_at(mapping["contactPerson"]["cols"][0])
                       if mapping["contactPerson"]["cols"] else "")

            earlier = previous.get(key)
            record = {
                "id": earlier["id"] if earlier else new_id(),
                "key": key, "row_index": index,
                "party_name": name, "address_lines": address,
                "contact_person": contact,
                "email": earlier["email"] if earlier
                         and earlier.get("email_edited") else email,
                "email_edited": bool(earlier and earlier.get("email_edited")),
                "amount": amount,
                "currency": currency,
                "category_raw": category_raw,
                "category": earlier["category"] if earlier
                            and earlier.get("category_edited")
                            else normalize_category(category_raw),
                "category_edited": bool(earlier
                                        and earlier.get("category_edited")),
                "include": earlier["include"] if earlier else True,
            }
            self.compute_issues(record)
            records.append(record)
        self.records = records
        self.preview_index = 0

    @staticmethod
    def compute_issues(record):
        issues = []
        if not record["party_name"]:
            issues.append(("miss", "Party name missing"))
        if not record["category"]:
            issues.append(("rev", 'Category "%s" not recognised'
                           % record["category_raw"] if record["category_raw"]
                           else "Category missing"))
        if record["amount"] is None:
            issues.append(("rev", "Balance missing"))
        elif record["amount"] < 0:
            issues.append(("rev", "Negative balance — verify "
                                  "classification"))
        if not record["address_lines"]:
            issues.append(("info", "No address"))
        if record["email"] and not valid_email(record["email"]):
            issues.append(("rev", "Invalid email address"))
        record["issues"] = issues

    @staticmethod
    def is_blocking(record):
        return not record["party_name"] or not record["category"]

    def generable_records(self):
        return [r for r in self.records
                if r["include"] and not self.is_blocking(r)]

    def flagged_count(self):
        return len([r for r in self.records
                    if r["include"] and self.is_blocking(r)])

    def category_counts(self):
        counts = {c: 0 for c in CATEGORIES}
        counts["review"] = 0
        for record in self.records:
            if not record["include"]:
                continue
            if self.is_blocking(record):
                counts["review"] += 1
            else:
                counts[record["category"]] += 1
        return counts

    # =====================================================================
    # PAGE 04 - REVIEW & MAPPING
    # =====================================================================
    def _page_review(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        frame, body, header = card(
            "Detected fields", "Change any column the detector did not get "
                               "right", light=True)
        redetect = button("Re-run detection", small=True)
        redetect.clicked.connect(self.redetect_mapping)
        header.addWidget(redetect)
        self.map_grid = QGridLayout()
        self.map_grid.setSpacing(10)
        for column in range(3):
            self.map_grid.setColumnStretch(column, 1)
        body.addLayout(self.map_grid)
        self.map_warning = QLabel("")
        self.map_warning.setWordWrap(True)
        self.map_warning.setVisible(False)
        body.addWidget(self.map_warning)
        layout.addWidget(frame)

        frame2, body2, _ = card("Category mix",
                                "Flagged rows are not generated until a "
                                "category is chosen")
        self.cat_stats = QHBoxLayout()
        self.cat_stats.setSpacing(10)
        body2.addLayout(self.cat_stats)
        controls = QHBoxLayout()
        controls.setSpacing(12)
        currency_box = QVBoxLayout()
        currency_box.setSpacing(4)
        currency_box.addWidget(field_label("Default currency"))
        self.currency_edit = QLineEdit()
        self.currency_edit.setMaxLength(6)
        self.currency_edit.setFixedWidth(110)
        self.currency_edit.editingFinished.connect(self.on_currency_changed)
        currency_box.addWidget(self.currency_edit)
        filter_box = QVBoxLayout()
        filter_box.setSpacing(4)
        filter_box.addWidget(field_label("Show"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All rows", "Only rows needing attention",
                                    "Only included rows"])
        self.filter_combo.setFixedWidth(250)
        self.filter_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_box.addWidget(self.filter_combo)
        self.exclude_check = QCheckBox("Exclude flagged rows from generation")
        self.exclude_check.setChecked(True)
        self.exclude_check.stateChanged.connect(self.on_exclude_changed)
        controls.addLayout(currency_box)
        controls.addLayout(filter_box)
        controls.addWidget(self.exclude_check, 0, Qt.AlignmentFlag.AlignBottom)
        controls.addStretch(1)
        body2.addLayout(controls)
        layout.addWidget(frame2)

        frame3, body3, header3 = card("Party records", "", light=True)
        self.rec_note = QLabel("0 rows")
        self.rec_note.setObjectName("HintLight")
        header3.addWidget(self.rec_note)
        all_btn = button("Include all", small=True)
        all_btn.clicked.connect(lambda: self.set_all_included(True))
        none_btn = button("Include none", small=True)
        none_btn.clicked.connect(lambda: self.set_all_included(False))
        header3.addWidget(all_btn)
        header3.addWidget(none_btn)
        self.rec_table = table(["Use", "#", "Party", "Address", "Contact",
                                "Party email", "Amount", "Ccy", "Category",
                                "Status"], stretch_column=9)
        self.rec_table.setMinimumHeight(340)
        body3.addWidget(self.rec_table)
        layout.addWidget(frame3, 1)
        return page

    def redetect_mapping(self):
        if not self.columns:
            self.toast("Import a file first.", "warn")
            return
        self.mapping = detect_mapping(self.columns)
        self.build_records(reset=True)
        self.refresh_all()
        self.toast("Detection re-run.", "ok")

    def on_currency_changed(self):
        text = (self.currency_edit.text() or "INR").upper()[:6]
        self.currency_edit.setText(text)
        self.db["settings"]["default_currency"] = text
        self.persist()
        self.build_records()
        self.refresh_all()

    def on_filter_changed(self, index):
        self.row_filter = ["all", "attention", "included"][index]
        self.render_records()

    def on_exclude_changed(self, _state):
        self.exclude_flagged = self.exclude_check.isChecked()
        self.refresh_all()

    def set_all_included(self, included):
        for record in self.records:
            record["include"] = included
        self.refresh_all()

    def render_mapping(self):
        self._clear(self.map_grid)
        if not self.mapping:
            empty = QLabel("Import a file first.")
            empty.setObjectName("HintLight")
            self.map_grid.addWidget(empty, 0, 0)
            self.map_warning.setVisible(False)
            return
        self.map_combos = {}
        for position, field in enumerate(FIELD_ORDER):
            entry = self.mapping[field]
            definition = FIELD_DEFS[field]
            holder = pane()
            box = QVBoxLayout(holder)
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(4)
            status = entry["status"]
            colour = {"detected": T["ok"], "review": T["warn"],
                      "missing": T["err"]}[status]
            label = QLabel(
                "<span style='color:%s; font-size:10px; font-weight:600; "
                "letter-spacing:1.1px'>%s%s</span>  <span style='color:%s; "
                "font-size:10px; font-weight:700'>%s</span>"
                % (T["text_soft"], definition["label"].upper(),
                   " *" if definition["required"] else "", colour,
                   status.upper()))
            label.setTextFormat(Qt.TextFormat.RichText)
            box.addWidget(label)

            if definition["multi"]:
                combo = QListWidget()
                combo.setSelectionMode(
                    QAbstractItemView.SelectionMode.MultiSelection)
                combo.setFixedHeight(86)
                combo.setStyleSheet(
                    "QListWidget { background:%s; border:1px solid %s;"
                    " border-radius:6px; color:%s; }"
                    " QListWidget::item { padding:3px 6px; }"
                    " QListWidget::item:selected { background:%s; color:%s; }"
                    % (T["raised"], T["line_soft"], T["text"],
                       T["accent"], T["accent_text"]))
                for column in self.columns:
                    item = QListWidgetItem(column["label"])
                    item.setData(Qt.ItemDataRole.UserRole, column["index"])
                    combo.addItem(item)
                    if column["index"] in entry["cols"]:
                        item.setSelected(True)
                combo.itemSelectionChanged.connect(
                    lambda f=field, w=combo: self.on_multi_map_changed(f, w))
                box.addWidget(combo)
                hint = QLabel("Ctrl-click to combine several columns — "
                              "each becomes a line of the address.")
            else:
                combo = QComboBox()
                combo.addItem("— none —", -1)
                for column in self.columns:
                    combo.addItem(column["label"], column["index"])
                if entry["cols"]:
                    position_in_list = combo.findData(entry["cols"][0])
                    if position_in_list >= 0:
                        combo.setCurrentIndex(position_in_list)
                combo.currentIndexChanged.connect(
                    lambda _i, f=field, w=combo: self.on_map_changed(f, w))
                box.addWidget(combo)
                sample = self.sample_for(entry["cols"][0]) if entry["cols"] \
                    else ""
                hint = QLabel(("Sample: " + sample) if sample
                              else "No column matched.")
            hint.setObjectName("HintLight")
            hint.setWordWrap(True)
            box.addWidget(hint)
            self.map_combos[field] = combo
            self.map_grid.addWidget(holder, position // 3, position % 3)

        if not self.mapping["partyName"]["cols"]:
            self.map_warning.setText(
                "No party-name column was identified. Choose one above "
                "— letters cannot be produced without it.")
            self.map_warning.setObjectName("NoticeRed")
            self.map_warning.setStyleSheet(style_sheet())
            self.map_warning.setVisible(True)
        else:
            self.map_warning.setVisible(False)

    def sample_for(self, column_index):
        for column in self.columns:
            if column["index"] == column_index:
                values = [v for v in column["values"] if v][:2]
                return " · ".join(values) or "(no values)"
        return ""

    def on_map_changed(self, field, combo):
        if self._building:
            return
        value = combo.currentData()
        self.mapping[field]["cols"] = [] if value in (None, -1) else [value]
        self.mapping[field]["status"] = ("detected"
                                         if self.mapping[field]["cols"]
                                         else "missing")
        self.build_records()
        self.refresh_all()

    def on_multi_map_changed(self, field, widget):
        if self._building:
            return
        self.mapping[field]["cols"] = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in widget.selectedItems()]
        self.mapping[field]["status"] = ("detected"
                                         if self.mapping[field]["cols"]
                                         else "missing")
        self.build_records()
        self.refresh_all()

    def render_cat_stats(self):
        self._clear(self.cat_stats)
        counts = self.category_counts()
        for key, value, meta, accent in (
                ("Trade Receivable", counts["Trade Receivable"],
                 "Owed to the client", T["accent"]),
                ("Trade Payable", counts["Trade Payable"],
                 "Owed by the client", T["info"]),
                ("Advance from Customers", counts["Advance from Customers"],
                 "Received by the client", T["accent"]),
                ("Advance to Vendors", counts["Advance to Vendors"],
                 "Paid by the client", T["info"]),
                ("Needs review", counts["review"],
                 "Not generated until fixed", T["warn"])):
            self.cat_stats.addWidget(stat_card(key, value, meta, accent))
        self.cat_stats.addStretch(1)

    def render_records(self):
        rows = self.records
        if self.row_filter == "attention":
            rows = [r for r in rows
                    if self.is_blocking(r)
                    or any(kind == "rev" for kind, _ in r["issues"])]
        elif self.row_filter == "included":
            rows = [r for r in rows if r["include"]]

        self.rec_table.setRowCount(0)
        for record in rows:
            index = self.rec_table.rowCount()
            self.rec_table.insertRow(index)

            holder = pane()
            box = QHBoxLayout(holder)
            box.setContentsMargins(8, 0, 0, 0)
            check = QCheckBox()
            check.setChecked(record["include"])
            check.stateChanged.connect(
                lambda _s, r=record, c=check: self.on_include_changed(r, c))
            box.addWidget(check)
            box.addStretch(1)
            self.rec_table.setCellWidget(index, 0, holder)

            self.rec_table.setItem(index, 1, cell(record["row_index"] + 1,
                                                  align_right=True,
                                                  color=T["text_mute"]))
            self.rec_table.setItem(index, 2, cell(
                record["party_name"] or "— no name —",
                bold=True,
                color=None if record["party_name"] else T["err"]))
            self.rec_table.setItem(index, 3,
                                   cell(", ".join(record["address_lines"])))
            self.rec_table.setItem(index, 4, cell(record["contact_person"]))

            email = QLineEdit(record["email"] or "")
            email.setPlaceholderText("party@example.com")
            email.editingFinished.connect(
                lambda r=record, w=email: self.on_email_changed(r, w))
            self.rec_table.setCellWidget(index, 5, email)

            label = amount_label(record["amount"], record["currency"])
            self.rec_table.setItem(index, 6, cell(
                fmt_amount(record["amount"], record["currency"])
                if label else "missing", align_right=True,
                color=None if label else T["warn"]))
            self.rec_table.setItem(index, 7, cell(record["currency"]))

            combo = QComboBox()
            combo.addItem("Needs review", "")
            for category in CATEGORIES:
                combo.addItem(category, category)
            if record["category"]:
                combo.setCurrentIndex(combo.findData(record["category"]))
            combo.currentIndexChanged.connect(
                lambda _i, r=record, w=combo: self.on_category_changed(r, w))
            self.rec_table.setCellWidget(index, 8, combo)

            status = "  ".join(text for _kind, text in record["issues"])
            colour = None
            if any(kind == "miss" for kind, _ in record["issues"]):
                colour = T["err"]
            elif any(kind == "rev" for kind, _ in record["issues"]):
                colour = T["warn"]
            self.rec_table.setItem(index, 9, cell(status, color=colour))

            if self.is_blocking(record):
                for column in range(self.rec_table.columnCount()):
                    item = self.rec_table.item(index, column)
                    if item:
                        item.setBackground(QColor(T["warn_bg"]))

        self.rec_table.resizeColumnsToContents()
        self.rec_table.setColumnWidth(5, 190)
        self.rec_table.setColumnWidth(8, 180)
        included = len([r for r in self.records if r["include"]])
        self.rec_note.setText("%d of %d rows shown · %d included"
                              % (len(rows), len(self.records), included))

    def on_include_changed(self, record, check):
        record["include"] = check.isChecked()
        self.refresh_chips()
        self.render_cat_stats()
        self.rec_note.setText(
            "%d of %d rows shown · %d included"
            % (self.rec_table.rowCount(), len(self.records),
               len([r for r in self.records if r["include"]])))

    def on_email_changed(self, record, widget):
        text = widget.text().strip()
        if text == record["email"]:
            return
        record["email"] = text
        record["email_edited"] = True
        self.compute_issues(record)
        self.render_records()
        self.refresh_chips()

    def on_category_changed(self, record, widget):
        if self._building:
            return
        record["category"] = widget.currentData() or None
        record["category_edited"] = True
        self.compute_issues(record)
        self.render_records()
        self.render_cat_stats()
        self.refresh_chips()

    # =====================================================================
    # CONFIRMATION RECORD  -  what both the preview and the DOCX consume
    # =====================================================================
    def to_confirmation(self, record):
        client = self.active_client()
        year = self.active_fy()
        as_at = fy_as_at(year)
        settings = self.db["settings"]
        return {
            "id": record["id"],
            "client_name": client["name"] if client else "",
            "financial_year": year["year"] if year else "",
            "audit_type": fy_audit_type(year),
            "audit_type_other": (year or {}).get("audit_type_other", ""),
            "basis": "period" if (year and year.get("basis") == "period")
                     else "year",
            "period_start": (year or {}).get("period_start", ""),
            "period_end": (year or {}).get("period_end", ""),
            "as_at": as_at,
            "year_end": as_at,
            "year_end_label": fmt_date_long(as_at) if as_at else "",
            "firm_name": settings.get("firm_name") or "the audit firm",
            "firm_designation": settings.get("firm_designation")
                                or "Statutory Auditor",
            "partner_name": settings.get("partner_name", ""),
            "letterhead_note": settings.get("letterhead_note", True),
            "reference": new_reference(),
            "print_reference": settings.get("print_reference", True),
            "letter_date": letter_date(self.db),
            "letter_date_label": fmt_date_long(letter_date(self.db)),
            "signatory_name": client.get("signatory_name", "") if client else "",
            "signatory_designation": (client.get("signatory_designation", "")
                                      if client else ""),
            "party_name": record["party_name"],
            "address_lines": list(record["address_lines"]),
            "contact_person": record["contact_person"],
            "party_email": record["email"],
            "amount": record["amount"],
            "currency": record["currency"],
            "category": record["category"],
            "auditors": [{"name": a["name"], "email": a["email"]}
                         for a in self.auditors()],
        }

    # =====================================================================
    # VALIDATION
    # =====================================================================
    def validation(self):
        client = self.active_client()
        year = self.active_fy()
        team = self.auditors()
        ready = self.generable_records()
        as_at = fy_as_at(year)
        audit_ok = fy_audit_ok(year)
        mapping_ok = bool(self.mapping and self.mapping["partyName"]["cols"])

        items = [
            {"ok": bool(self.source_path), "title": "Spreadsheet imported",
             "detail": ("%s · %d rows"
                        % (os.path.basename(self.source_path),
                           len(self.data_rows))) if self.source_path
                       else "Open an Excel or CSV file in Import data"},
            {"ok": mapping_ok, "title": "Party-name column identified",
             "detail": self.column_label(self.mapping["partyName"]["cols"][0])
                       if mapping_ok
                       else "Choose the column in Review & mapping"},
            {"ok": bool(client), "title": "Client selected",
             "detail": client["name"] if client
                       else "Add or select a client in Client database"},
            {"ok": audit_ok, "title": "Type of audit chosen",
             "detail": (
                 "Add a financial year, then choose the type in Settings"
                 if not year else
                 ('%s — letters open "Our %s, %s, are engaged in %s …"'
                  % (fy_audit_type(year), auditors_label(fy_audit_type(year)),
                     self.db["settings"].get("firm_name") or "[firm]",
                     engagement_phrase(fy_audit_type(year),
                                       year.get("audit_type_other"))))
                 if audit_ok else
                 "Describe the engagement in Settings, or pick a listed type")},
            {"ok": bool(as_at), "title": "%s set" % fy_basis_label(year),
             "detail": ("Add a financial year for the client" if not year
                        else ("%s · %s" % (year["year"],
                                                fy_span_text(year)))
                        if as_at else
                        ("Enter the period end date in Settings"
                         if year.get("basis") == "period"
                         else "Enter the financial year end in Settings"))},
            {"ok": bool(client and str(client.get("signatory_name") or "").strip()),
             "title": "Company signatory named",
             "detail": ("Select a client first" if not client
                        else ("%s, %s" % (client.get("signatory_name"),
                                          client.get("signatory_designation")
                                          or "Director / CFO"))
                        if str(client.get("signatory_name") or "").strip()
                        else "The letter is signed by the client \u2014 add "
                             "the officer in Settings")},
            {"ok": bool(team), "title": "At least one valid audit team email",
             "detail": ("%d address(es): %s"
                        % (len(team), ", ".join(a["email"] for a in team)))
                       if team else "Add a team member in Settings"},
            {"ok": bool(ready), "title": "At least one party ready",
             "detail": ("%d letters will be produced" % len(ready)) if ready
                       else "No row has both a party name and a category"},
            {"ok": self.flagged_count() == 0,
             "title": "Every included row has a valid category",
             "detail": ("%d row(s) need a category or a party name"
                        % self.flagged_count()) if self.flagged_count()
                       else "No rows flagged"},
        ]
        last = len(items) - 1
        hard = [item for index, item in enumerate(items)
                if not item["ok"] and not (index == last
                                           and self.exclude_flagged)]
        return {"items": items, "hard": hard, "ready": not hard,
                "generable": ready}

    def column_label(self, index):
        for column in self.columns:
            if column["index"] == index:
                return column["label"]
        return "Column " + col_letter(index)

    # =====================================================================
    # PAGE 05 - LETTER PREVIEW
    # =====================================================================
    def _page_preview(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(14)

        frame, body, _ = card("Letter preview",
                              "Exactly what the Word file will contain")
        controls = QHBoxLayout()
        controls.setSpacing(9)
        previous = button("‹  Previous", small=True)
        previous.clicked.connect(lambda: self.step_preview(-1))
        self.pv_combo = QComboBox()
        self.pv_combo.setMinimumWidth(420)
        self.pv_combo.currentIndexChanged.connect(self.on_preview_selected)
        nxt = button("Next  ›", small=True)
        nxt.clicked.connect(lambda: self.step_preview(1))
        self.pv_position = QLabel("—")
        self.pv_position.setProperty("chip", "neutral")
        controls.addWidget(previous)
        controls.addWidget(self.pv_combo)
        controls.addWidget(nxt)
        controls.addWidget(self.pv_position)
        controls.addStretch(1)
        body.addLayout(controls)
        self.pv_warning = QLabel("")
        self.pv_warning.setWordWrap(True)
        self.pv_warning.setVisible(False)
        body.addWidget(self.pv_warning)
        layout.addWidget(frame)

        self.paper = QTextBrowser()
        self.paper.setObjectName("Paper")
        self.paper.setOpenExternalLinks(False)
        self.style_paper()
        self.paper.setMinimumHeight(560)
        layout.addWidget(self.paper, 1)
        return page

    def style_paper(self):
        """The letter is a printed page, so it stays paper-coloured in both
        modes; only its frame follows the theme."""
        self.paper.setStyleSheet(
            "QTextBrowser#Paper { background:%s; color:%s; border:1px solid %s;"
            " border-radius:6px; padding:18px 26px; }"
            % (T["paper"], T["paper_ink"], T["paper_line"]))

    def on_preview_selected(self, index):
        if index >= 0 and not self._building:
            self.preview_index = index
            self.render_preview(rebuild_list=False)

    def step_preview(self, delta):
        total = len(self.generable_records())
        if not total:
            return
        self.preview_index = (self.preview_index + delta) % total
        self.render_preview()

    def render_preview(self, rebuild_list=True):
        ready = self.generable_records()
        if self.preview_index >= len(ready):
            self.preview_index = 0
        if rebuild_list:
            self.pv_combo.blockSignals(True)
            self.pv_combo.clear()
            for record in ready:
                self.pv_combo.addItem("%s  —  %s" % (record["party_name"],
                                                          record["category"]))
            if ready:
                self.pv_combo.setCurrentIndex(self.preview_index)
            self.pv_combo.blockSignals(False)
        self.pv_position.setText("%d of %d" % (self.preview_index + 1,
                                               len(ready)) if ready
                                 else "0 of 0")

        client = self.active_client()
        year = self.active_fy()
        warnings = []
        if not client:
            warnings.append("No client selected — the client name will "
                            "be blank.")
        if not year:
            warnings.append("No financial year selected — the date will "
                            "be blank.")
        elif not fy_as_at(year):
            warnings.append(
                "No period end date set — the confirmation date will be "
                "blank." if year.get("basis") == "period"
                else "No financial year end set — the confirmation date "
                     "will be blank.")
        if not self.auditors():
            warnings.append("No audit team email added — the letter has "
                            "nowhere to direct replies.")
        if warnings:
            self.pv_warning.setText("<br>".join(warnings))
            self.pv_warning.setObjectName("NoticeWarn")
            self.pv_warning.setStyleSheet(style_sheet())
            self.pv_warning.setVisible(True)
        else:
            self.pv_warning.setVisible(False)

        if not ready:
            self.paper.setHtml(
                "<div style='color:%s; padding:40px; text-align:center; "
                "font-family:Calibri,sans-serif'>No party is ready to preview. "
                "Check Review &amp; mapping.</div>" % T["text_mute"])
            return
        try:
            model = build_letter_model(self.to_confirmation(
                ready[self.preview_index]))
        except Exception as exc:
            self.paper.setHtml("<div style='color:%s; padding:40px'>%s</div>"
                               % (T["err"], xml_escape(str(exc))))
            return
        self.paper.setHtml(self.letter_html(model))

    @staticmethod
    def letter_html(model):
        """The on-screen letter, built from the same model as the .docx.

        Qt's rich text ignores margins on <div>, so every block is a <p> with
        <br> between its lines - that is what gives the letter its spacing."""
        esc = xml_escape
        compact = model.get("compact")
        gap = 9 if compact else 14

        def block(lines, space_after=None, align=""):
            return ("<p style='margin:0 0 %dpx%s'>%s</p>"
                    % (gap if space_after is None else space_after,
                       ("; text-align:" + align) if align else "",
                       "<br>".join(esc(t) for t in lines)))

        html = ["<div style=\"font-family:Calibri,'Segoe UI',sans-serif; "
                "font-size:14px; line-height:1.45; color:%s\">" % T["paper_ink"]]
        if model["letterhead_note"]:
            html.append("<p style='margin:0 0 2px; text-align:center'>%s</p>"
                        % esc(model["letterhead_note"]))
        html.append("<p style='margin:0 0 %dpx; text-align:center; "
                    "font-weight:700'>%s</p>"
                    % (18 if compact else 24, esc(model["title"])))
        date_lines = [model["date_line"]]
        if model.get("reference_line"):
            date_lines.append(model["reference_line"])
        html.append(block(date_lines, space_after=6, align="right"))
        html.append(block([l["text"] for l in model["party_block"]]))
        html.append(block([model["salutation"]]))
        for index, text in enumerate(model["paras"]):
            html.append("<p style='margin:0 0 %dpx; text-align:justify'>%s</p>"
                        % (6 if index == len(model["paras"]) - 1 else gap,
                           esc(text)))
        html.append(block([l["text"] for l in model["auditor_block"]]))
        for text in model["closing_paras"]:
            html.append("<p style='margin:0 0 %dpx; text-align:justify'>%s</p>"
                        % (gap, esc(text)))
        signature = model["signature"]
        first = [l["text"] for l in signature if not l.get("gap")][:2]
        rest = [l["text"] for l in signature[len(first):]]
        html.append(block(first, space_after=22 if rest else gap))
        if rest:
            html.append(block(rest, space_after=gap))
        html.append("<p style='margin:20px 0 12px; text-align:justify'>%s</p>"
                    % esc(model["slip"]["sentence"]))
        rows = "".join(
            "<tr><td width='34%%' style='padding:3px 0'>%s</td>"
            "<td style='padding:3px 0'>:&nbsp;&nbsp;______________________</td>"
            "</tr>" % esc(label) for label in model["slip"]["rows"])
        html.append("<table width='70%%' cellspacing='0' cellpadding='0' "
                    "style='border-collapse:collapse'>%s</table></div>" % rows)
        return "".join(html)

    # =====================================================================
    # PAGE 06 - GENERATE
    # =====================================================================
    def _page_generate(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        frame, body, header = card("Pre-generation checks", "")
        self.gen_status = QLabel("")
        self.gen_status.setObjectName("HintDark")
        header.addWidget(self.gen_status)
        self.gen_checks = QVBoxLayout()
        self.gen_checks.setSpacing(6)
        body.addLayout(self.gen_checks)
        layout.addWidget(frame)

        frame2, body2, _ = card("Output folder",
                                "Where the Word and PDF letters are written")
        folder_row = QHBoxLayout()
        folder_row.setSpacing(9)
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText(
            "Choose the folder the confirmations should be saved in")
        self.folder_edit.setReadOnly(True)
        choose = button("Choose folder…", "brass")
        choose.clicked.connect(self.choose_output_folder)
        open_folder = button("Open folder")
        open_folder.clicked.connect(self.open_output_folder)
        folder_row.addWidget(self.folder_edit, 1)
        folder_row.addWidget(choose)
        folder_row.addWidget(open_folder)
        body2.addLayout(folder_row)
        hint = QLabel("A sub-folder is created for the client and year, so "
                      "repeat runs never overwrite one another.")
        hint.setObjectName("HintDark")
        hint.setWordWrap(True)
        body2.addWidget(hint)
        layout.addWidget(frame2)

        frame3, body3, _ = card("Generation",
                                "One Word file and one PDF per party")
        self.gen_stats = QHBoxLayout()
        self.gen_stats.setSpacing(10)
        body3.addLayout(self.gen_stats)
        head_row = QHBoxLayout()
        head_row.setSpacing(8)
        head_label = QLabel("Space to leave at the top of the PDF for the "
                            "client's letterhead (cm)")
        head_label.setObjectName("HintDark")
        self.head_space = QDoubleSpinBox()
        self.head_space.setRange(0.0, 8.0)
        self.head_space.setSingleStep(0.5)
        self.head_space.setDecimals(1)
        self.head_space.setFixedWidth(90)
        self.head_space.setToolTip(
            "Leave 0 for plain paper. For pre-printed letterhead, measure the "
            "depth of the printed head and enter it here; the letter still "
            "fits on one page.")
        self.head_space.setValue(float(
            self.db["settings"].get("letterhead_space_cm", 0) or 0))
        self.head_space.valueChanged.connect(self.on_head_space)
        head_row.addWidget(head_label)
        head_row.addWidget(self.head_space)
        head_row.addStretch(1)
        body3.addLayout(head_row)
        buttons = QHBoxLayout()
        buttons.setSpacing(9)
        self.btn_generate = button("Generate letters (Word + PDF)", "primary")
        self.btn_generate.clicked.connect(self.run_generation)
        self.btn_open_output = button("Open output folder")
        self.btn_open_output.clicked.connect(self.open_output_folder)
        self.btn_open_output.setEnabled(False)
        self.btn_email = button("Go to email delivery", "blue")
        self.btn_email.clicked.connect(lambda: self.go("email"))
        self.btn_email.setEnabled(False)
        for widget in (self.btn_generate, self.btn_open_output, self.btn_email):
            buttons.addWidget(widget)
        buttons.addStretch(1)
        body3.addLayout(buttons)
        self.gen_bar = QProgressBar()
        self.gen_bar.setValue(0)
        self.gen_progress = QLabel("Idle")
        self.gen_progress.setObjectName("HintDark")
        body3.addWidget(self.gen_bar)
        body3.addWidget(self.gen_progress)
        layout.addWidget(frame3)

        frame4, body4, header4 = card("Generated files", "", light=True)
        self.gen_count = QLabel("None yet")
        self.gen_count.setObjectName("HintLight")
        header4.addWidget(self.gen_count)
        self.gen_table = table(["#", "File name", "Category", "Balance",
                                "Size", "Status"], stretch_column=1)
        body4.addWidget(self.gen_table)
        layout.addWidget(frame4, 1)
        return page

    def on_head_space(self, value):
        self.db["settings"]["letterhead_space_cm"] = float(value)
        self.persist()

    def choose_output_folder(self):
        start = (self.db["settings"].get("output_folder")
                 or os.path.expanduser("~"))
        folder = QFileDialog.getExistingDirectory(
            self, "Choose the folder for the confirmation letters", start)
        if folder:
            self.db["settings"]["output_folder"] = folder
            self.folder_edit.setText(folder)
            self.persist()
            self.refresh_generate()

    def run_output_folder(self):
        """Per-run sub-folder: <chosen folder>/<client> - <year>."""
        base = self.db["settings"].get("output_folder")
        if not base:
            return ""
        client = self.active_client()
        year = self.active_fy()
        name = sanitize_filename(
            "%s - Balance Confirmations - %s"
            % (client["name"] if client else "Client",
               year["year"] if year else ""))
        return os.path.join(base, name)

    def open_output_folder(self):
        folder = self.run_output_folder() or self.db["settings"].get(
            "output_folder")
        if not folder or not os.path.isdir(folder):
            self.toast("No output folder yet — choose one and generate.",
                       "warn")
            return
        try:
            if os.name == "nt":
                os.startfile(folder)                       # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            self.toast("The files are in %s" % folder, "info")

    def refresh_generate(self):
        checks = self.validation()
        self._clear(self.gen_checks)
        last = len(checks["items"]) - 1
        for index, item in enumerate(checks["items"]):
            soft = (index == last and not item["ok"] and self.exclude_flagged)
            mark = "✓" if item["ok"] else ("!" if soft else "✕")
            colour = T["ok"] if item["ok"] else (T["warn"] if soft
                                                   else T["err"])
            row = QHBoxLayout()
            row.setSpacing(9)
            box = QLabel(mark)
            box.setFixedWidth(18)
            box.setStyleSheet("color:%s; font-weight:700;" % colour)
            text = QLabel("<b>%s</b><br><span style='color:%s; font-size:11px'>"
                          "%s%s</span>"
                          % (item["title"], T["text_mute"], item["detail"],
                             " — these rows will be skipped" if soft
                             else ""))
            text.setWordWrap(True)
            text.setTextFormat(Qt.TextFormat.RichText)
            row.addWidget(box, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(text, 1)
            self.gen_checks.addLayout(row)

        folder = self.db["settings"].get("output_folder") or ""
        self.folder_edit.setText(folder)
        self.gen_status.setText(
            "Ready to Generate" if checks["ready"]
            else "%d item%s need attention" % (len(checks["hard"]),
                                               "" if len(checks["hard"]) == 1
                                               else "s"))
        counts = self.category_counts()
        self._clear(self.gen_stats)
        for key, value, meta, accent in (
                ("Total parties", len(checks["generable"]),
                 "Letters to be produced", T["accent"]),
                ("Trade Receivable", counts["Trade Receivable"], "", T["accent"]),
                ("Trade Payable", counts["Trade Payable"], "", T["info"]),
                ("Advance from Customers", counts["Advance from Customers"],
                 "", T["accent"]),
                ("Advance to Vendors", counts["Advance to Vendors"], "",
                 T["info"]),
                ("Needs review", counts["review"],
                 "Will be skipped" if self.exclude_flagged
                 else "Blocks generation", T["warn"])):
            self.gen_stats.addWidget(stat_card(key, value, meta, accent))
        self.gen_stats.addStretch(1)

        busy = self.gen_thread is not None
        self.btn_generate.setEnabled(checks["ready"] and bool(folder)
                                     and not busy)
        if not folder:
            self.btn_generate.setToolTip("Choose an output folder first.")
        else:
            self.btn_generate.setToolTip("")
        done = [g for g in self.generated if g["status"] == "ok"]
        self.btn_open_output.setEnabled(bool(done))
        self.btn_email.setEnabled(bool(done))
        self.render_generated_table()

    def render_generated_table(self):
        self.gen_table.setRowCount(0)
        for index, record in enumerate(self.generated):
            row = self.gen_table.rowCount()
            self.gen_table.insertRow(row)
            conf = record["conf"]
            self.gen_table.setItem(row, 0, cell(index + 1, align_right=True,
                                                color=T["text_mute"]))
            self.gen_table.setItem(row, 1, cell(record["filename"]))
            self.gen_table.setItem(row, 2, cell(conf["category"]))
            self.gen_table.setItem(row, 3, cell(
                amount_label(conf["amount"], conf["currency"]) or "—",
                align_right=True))
            self.gen_table.setItem(row, 4, cell(
                "%.1f KB" % (record["size"] / 1024.0) if record["size"]
                else "—", align_right=True))
            ok = record["status"] == "ok"
            if ok and record.get("pdf_data"):
                state, tone = "Word + PDF", T["ok"]
            elif ok and record.get("pdf_error"):
                state, tone = "Word only (PDF failed: %s)" \
                    % record["pdf_error"][:60], T["warn"]
            elif ok:
                state, tone = "Generated", T["ok"]
            else:
                state, tone = "Failed: " + record.get("error", ""), T["err"]
            self.gen_table.setItem(row, 5, cell(state, color=tone, bold=True))
        self.gen_table.resizeColumnsToContents()
        produced = len([g for g in self.generated if g["status"] == "ok"])
        self.gen_count.setText("%d of %d produced" % (produced,
                                                      len(self.generated))
                               if self.generated else "None yet")

    def run_generation(self):
        if self.gen_thread:
            return
        checks = self.validation()
        if not checks["ready"]:
            self.toast("Resolve the items listed above before generating.",
                       "warn")
            return
        folder = self.run_output_folder()
        if not folder:
            self.toast("Choose an output folder first.", "warn")
            return
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as exc:
            self.toast("The output folder could not be created: %s" % exc,
                       "err")
            return

        self.generated = []
        self.queue = {}
        self.render_generated_table()
        confs = [self.to_confirmation(r) for r in checks["generable"]]
        self.btn_generate.setEnabled(False)
        self.gen_bar.setValue(0)

        self.gen_thread = QThread(self)
        self.gen_worker = GenerateWorker(
            confs, folder, True,
            float(self.db["settings"].get("letterhead_space_cm", 0) or 0))
        self.gen_worker.moveToThread(self.gen_thread)
        self.gen_thread.started.connect(self.gen_worker.run)
        self.gen_worker.progress.connect(self.on_generate_progress)
        self.gen_worker.produced.connect(self.on_generated)
        self.gen_worker.finished.connect(self.on_generate_finished)
        self.gen_thread.start()

    def on_generate_progress(self, done, total, party):
        self.gen_bar.setMaximum(max(total, 1))
        self.gen_bar.setValue(done)
        self.gen_progress.setText(
            "Generating confirmations…  %d of %d completed  —  %s"
            % (done, total, party) if party
            else "Generating confirmations…  %d of %d completed"
                 % (done, total))

    def on_generated(self, record):
        self.generated.append(record)
        self.render_generated_table()

    def on_generate_finished(self, ok, failed):
        if self.gen_thread:
            self.gen_thread.quit()
            self.gen_thread.wait(4000)
        self.gen_thread = None
        self.gen_worker = None
        folder = self.run_output_folder()
        self.gen_progress.setText(
            "Done — %d generated%s.  Saved in %s"
            % (ok, (", %d failed" % failed) if failed else "", folder))
        self.save_run(folder)
        self.refresh_all()
        self.refresh_generate()
        self.toast("%d confirmation%s generated%s."
                   % (ok, "" if ok == 1 else "s",
                      (", %d failed" % failed) if failed else ""),
                   "warn" if failed else "ok")

    def save_run(self, folder):
        client = self.active_client()
        year = self.active_fy()
        if not client or not year:
            return
        run = {
            "id": new_id(), "client_id": client["id"],
            "client_name": client["name"], "fy_id": year["id"],
            "year": year["year"], "year_end": year.get("year_end", ""),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "audit_type": fy_audit_type(year),
            "audit_type_other": year.get("audit_type_other", ""),
            "basis": year.get("basis", "year"),
            "period_start": year.get("period_start", ""),
            "period_end": year.get("period_end", ""),
            "as_at": fy_as_at(year), "period_label": fy_span_text(year),
            "firm_name": self.db["settings"].get("firm_name", ""),
            "folder": folder,
            "auditors": [{"name": a["name"], "email": a["email"]}
                         for a in self.auditors()],
            "source": {"name": os.path.basename(self.source_path),
                       "sheet": self.active_sheet,
                       "rows": len(self.data_rows)} if self.source_path
                      else None,
            "documents": [{
                "filename": g["filename"],
                "pdf_filename": g.get("pdf_filename", ""),
                "party_name": g["conf"]["party_name"],
                "reference": g["conf"].get("reference", ""),
                "thread_id": "", "message_id": "",
                "category": g["conf"]["category"], "amount": g["conf"]["amount"],
                "currency": g["conf"]["currency"],
                "email": g["conf"].get("party_email", ""),
                "address": ", ".join(g["conf"]["address_lines"]),
                "status": g["status"], "email_status": "not sent",
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            } for g in self.generated],
        }
        self.db["runs"].insert(0, run)
        del self.db["runs"][300:]
        self.current_run_id = run["id"]
        self.persist()

    # =====================================================================
    # PAGE 07 - EMAIL DELIVERY
    # =====================================================================
    def _page_email(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        frame, body, _ = card("Your mailbox",
                              "Letters are sent from your own account")
        body.addWidget(notice(
            "warn", "Use an <b>app password</b>, not your normal password. "
                    "Gmail, Outlook, Yahoo and Zoho all issue one from the "
                    "security page of your account once two-factor "
                    "authentication is on. Nothing is sent anywhere except to "
                    "your own mail server, and every message lands in your "
                    "Sent items."))
        grid = QGridLayout()
        grid.setSpacing(9)

        def add(row, column, label, widget, span=1):
            holder = QVBoxLayout()
            holder.setSpacing(4)
            holder.addWidget(field_label(label))
            holder.addWidget(widget)
            wrapper = pane()
            wrapper.setLayout(holder)
            grid.addWidget(wrapper, row, column, 1, span)

        self.mail_provider = QComboBox()
        self.mail_provider.addItems(list(SMTP_PRESETS))
        self.mail_provider.currentTextChanged.connect(self.on_provider_changed)
        self.mail_host = QLineEdit()
        self.mail_port = QSpinBox()
        self.mail_port.setRange(1, 65535)
        self.mail_port.setValue(587)
        self.mail_security = QComboBox()
        self.mail_security.addItem("STARTTLS (587)", "starttls")
        self.mail_security.addItem("SSL / TLS (465)", "ssl")
        self.mail_security.addItem("None (not recommended)", "none")
        self.mail_username = QLineEdit()
        self.mail_username.setPlaceholderText("you@yourfirm.com")
        self.mail_password_edit = QLineEdit()
        self.mail_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.mail_password_edit.setPlaceholderText("app password")
        self.mail_sender = QLineEdit()
        self.mail_sender.setPlaceholderText("leave blank to use the username")
        self.mail_sender_name = QLineEdit()
        self.mail_sender_name.setPlaceholderText("Ankit Soni and Associates")
        for widget in (self.mail_host, self.mail_username, self.mail_sender,
                       self.mail_sender_name):
            widget.editingFinished.connect(self.save_mail_settings)
        self.mail_port.valueChanged.connect(self.save_mail_settings)
        self.mail_security.currentIndexChanged.connect(self.save_mail_settings)

        add(0, 0, "Provider", self.mail_provider)
        add(0, 1, "SMTP server", self.mail_host)
        add(0, 2, "Port", self.mail_port)
        add(0, 3, "Encryption", self.mail_security)
        add(1, 0, "Username", self.mail_username, 2)
        add(1, 2, "App password", self.mail_password_edit, 2)
        add(2, 0, "From address", self.mail_sender, 2)
        add(2, 1 + 1, "From name", self.mail_sender_name, 2)
        body.addLayout(grid)

        row = QHBoxLayout()
        row.setSpacing(9)
        self.remember_check = QCheckBox(
            "Remember the password in this computer's credential store"
            if HAS_KEYRING else
            "Remember the password (needs the keyring library)")
        self.remember_check.setEnabled(HAS_KEYRING)
        self.remember_check.stateChanged.connect(self.on_remember_changed)
        test_btn = button("Test connection", "brass")
        test_btn.clicked.connect(self.test_connection)
        self.btn_test_mail = button("Send a test letter to myself")
        self.btn_test_mail.clicked.connect(self.send_test_email)
        row.addWidget(self.remember_check)
        row.addStretch(1)
        row.addWidget(test_btn)
        row.addWidget(self.btn_test_mail)
        body.addLayout(row)
        self.mail_state = QLabel("")
        self.mail_state.setWordWrap(True)
        self.mail_state.setVisible(False)
        body.addWidget(self.mail_state)
        layout.addWidget(frame)

        frame2, body2, header2 = card(
            "Message", "Placeholders: " + "  ".join(PLACEHOLDERS), light=True)
        reset = button("Restore default wording", small=True)
        reset.clicked.connect(self.reset_message)
        header2.addWidget(reset)
        body2.addWidget(field_label("Subject", light=True))
        self.mail_subject = QLineEdit()
        self.mail_subject.editingFinished.connect(self.save_mail_settings)
        body2.addWidget(self.mail_subject)
        body2.addWidget(field_label("Body", light=True))
        self.mail_body = QPlainTextEdit()
        self.mail_body.setMinimumHeight(190)
        self.mail_body.textChanged.connect(self.on_body_changed)
        body2.addWidget(self.mail_body)
        options = QHBoxLayout()
        options.setSpacing(16)
        self.cc_check = QCheckBox("Cc the audit team")
        self.cc_check.stateChanged.connect(self.save_mail_settings)
        self.reply_check = QCheckBox("Set Reply-To to the audit team")
        self.reply_check.stateChanged.connect(self.save_mail_settings)
        delay_box = QHBoxLayout()
        delay_box.setSpacing(6)
        delay_label = QLabel("Gap between sends (ms)")
        delay_label.setObjectName("HintLight")
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 20000)
        self.delay_spin.setSingleStep(250)
        self.delay_spin.setFixedWidth(100)
        self.delay_spin.valueChanged.connect(self.save_mail_settings)
        delay_box.addWidget(delay_label)
        delay_box.addWidget(self.delay_spin)
        options.addWidget(self.cc_check)
        options.addWidget(self.reply_check)
        options.addLayout(delay_box)
        options.addStretch(1)
        body2.addLayout(options)
        layout.addWidget(frame2)

        frame3, body3, header3 = card("Send queue", "")
        self.mail_note = QLabel("No documents generated yet")
        self.mail_note.setObjectName("HintDark")
        header3.addWidget(self.mail_note)
        self.btn_send = button("Send all confirmations", "primary")
        self.btn_send.clicked.connect(lambda: self.start_send(False))
        self.btn_retry = button("Retry failed")
        self.btn_retry.clicked.connect(lambda: self.start_send(True))
        self.btn_log = button("Export send log (CSV)")
        self.btn_log.clicked.connect(self.export_send_log)
        for widget in (self.btn_send, self.btn_retry, self.btn_log):
            header3.addWidget(widget)
        attach_row = QHBoxLayout()
        attach_row.setSpacing(9)
        attach_label = QLabel("Attach to each e-mail")
        attach_label.setObjectName("HintDark")
        self.attach_mode = QComboBox()
        for label, key in ATTACH_MODES:
            self.attach_mode.addItem(label, key)
        self.attach_mode.setMinimumWidth(330)
        self.attach_mode.currentIndexChanged.connect(self.on_attach_mode)
        self.btn_link_signed = button("Link signed PDFs from a folder…",
                                      "brass")
        self.btn_link_signed.setToolTip(
            "Pick the folder holding the letters the client printed on its "
            "letterhead, signed and scanned. Each PDF is tied to its party by "
            "the reference code or the party name in the file name.")
        self.btn_link_signed.clicked.connect(self.link_signed_folder)
        attach_row.addWidget(attach_label)
        attach_row.addWidget(self.attach_mode)
        attach_row.addWidget(self.btn_link_signed)
        attach_row.addStretch(1)
        body3.addLayout(attach_row)
        self.attach_hint = QLabel("")
        self.attach_hint.setObjectName("HintDark")
        self.attach_hint.setWordWrap(True)
        body3.addWidget(self.attach_hint)
        self.mail_bar = QProgressBar()
        self.mail_bar.setValue(0)
        self.mail_progress = QLabel("Idle")
        self.mail_progress.setObjectName("HintDark")
        body3.addWidget(self.mail_bar)
        body3.addWidget(self.mail_progress)
        self.mail_table = table(["Party", "Category", "To", "Attachment",
                                 "Status", "Detail", "Signed PDF"],
                                stretch_column=5)
        self.mail_table.setMinimumHeight(260)
        body3.addWidget(self.mail_table)
        layout.addWidget(frame3, 1)
        return page

    def on_provider_changed(self, name):
        if self._building:
            return
        host, port, security = SMTP_PRESETS.get(name, ("", 587, "starttls"))
        if host:
            self.mail_host.setText(host)
            self.mail_port.setValue(port)
            index = self.mail_security.findData(security)
            if index >= 0:
                self.mail_security.setCurrentIndex(index)
        self.save_mail_settings()

    def on_body_changed(self):
        if not self._building:
            self.mail_settings()["body"] = self.mail_body.toPlainText()
            self._mail_save_pending = True
            QTimer.singleShot(600, self._flush_mail_settings)

    def _flush_mail_settings(self):
        if getattr(self, "_mail_save_pending", False):
            self._mail_save_pending = False
            self.persist()

    def save_mail_settings(self):
        # never write the blank start-up state over saved settings: the mail
        # widgets only hold real values once refresh_email() has filled them
        if self._building or not getattr(self, "_mail_loaded", False):
            return
        mail = self.mail_settings()
        mail["provider"] = self.mail_provider.currentText()
        mail["host"] = self.mail_host.text().strip()
        mail["port"] = self.mail_port.value()
        mail["security"] = self.mail_security.currentData()
        mail["username"] = self.mail_username.text().strip()
        mail["sender"] = self.mail_sender.text().strip()
        mail["sender_name"] = self.mail_sender_name.text().strip()
        mail["subject"] = self.mail_subject.text()
        mail["body"] = self.mail_body.toPlainText()
        mail["cc_team"] = self.cc_check.isChecked()
        mail["reply_to_team"] = self.reply_check.isChecked()
        mail["delay_ms"] = self.delay_spin.value()
        mail["remember_password"] = self.remember_check.isChecked()
        self.persist()

    def on_remember_changed(self, _state):
        if self._building:
            return
        self.save_mail_settings()
        if not HAS_KEYRING:
            return
        username = self.mail_username.text().strip()
        password = self.mail_password_edit.text()
        try:
            if self.remember_check.isChecked() and username and password:
                keyring.set_password("BalanceConfirmationGenerator",
                                     username, password)
                self.toast("Password stored in this computer's credential "
                           "store.", "ok")
            elif not self.remember_check.isChecked() and username:
                try:
                    keyring.delete_password("BalanceConfirmationGenerator",
                                            username)
                except Exception:
                    pass
                self.toast("Stored password removed.", "ok")
        except Exception as exc:
            self.toast("The credential store refused: %s" % exc, "warn")

    def reset_message(self):
        self.mail_subject.setText(DEFAULT_SUBJECT)
        self.mail_body.setPlainText(DEFAULT_BODY)
        self.save_mail_settings()
        self.toast("Default wording restored.", "ok")

    def mail_account(self):
        mail = self.mail_settings()
        password = self.mail_password_edit.text()
        if not password and HAS_KEYRING and mail.get("remember_password"):
            try:
                password = keyring.get_password(
                    "BalanceConfirmationGenerator",
                    mail.get("username", "")) or ""
            except Exception:
                password = ""
        return {"host": mail.get("host", ""), "port": int(mail.get("port", 587)),
                "security": mail.get("security", "starttls"),
                "username": mail.get("username", ""), "password": password}

    def mail_options(self):
        mail = self.mail_settings()
        return {"subject": mail.get("subject") or DEFAULT_SUBJECT,
                "body": mail.get("body") or DEFAULT_BODY,
                "cc_team": mail.get("cc_team", True),
                "reply_to_team": mail.get("reply_to_team", True),
                "sender": mail.get("sender") or mail.get("username", ""),
                "sender_name": mail.get("sender_name", "")}

    def mail_ready(self):
        account = self.mail_account()
        missing = []
        if not account["host"]:
            missing.append("the SMTP server")
        if not account["username"]:
            missing.append("the username")
        if not account["password"]:
            missing.append("the app password")
        return (not missing), missing

    def show_mail_state(self, text, kind):
        self.mail_state.setText(text)
        self.mail_state.setObjectName({"green": "NoticeGreen",
                                       "blue": "NoticeBlue",
                                       "warn": "NoticeWarn",
                                       "red": "NoticeRed"}[kind])
        self.mail_state.setStyleSheet(style_sheet())
        self.mail_state.setVisible(True)

    def test_connection(self):
        ready, missing = self.mail_ready()
        if not ready:
            self.show_mail_state("Still needed: %s." % ", ".join(missing),
                                 "warn")
            return
        account = self.mail_account()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            server = smtp_connect(account["host"], account["port"],
                                  account["security"], account["username"],
                                  account["password"], timeout=25)
            server.quit()
            QApplication.restoreOverrideCursor()
            self.show_mail_state(
                "Signed in to <b>%s</b> as <b>%s</b>. Messages will be sent "
                "from this mailbox." % (account["host"], account["username"]),
                "green")
            self.toast("Mail server connection succeeded.", "ok")
            if HAS_KEYRING and self.remember_check.isChecked():
                try:
                    keyring.set_password("BalanceConfirmationGenerator",
                                         account["username"],
                                         account["password"])
                except Exception:
                    pass
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self.show_mail_state(friendly_smtp_error(exc), "red")
            self.toast("Connection failed.", "err")
        self.refresh_email()

    def send_test_email(self):
        ready, missing = self.mail_ready()
        if not ready:
            self.show_mail_state("Still needed: %s." % ", ".join(missing),
                                 "warn")
            return
        done = [g for g in self.generated if g["status"] == "ok"]
        if not done:
            self.toast("Generate at least one letter first.", "warn")
            return
        account = self.mail_account()
        options = dict(self.mail_options())
        record = done[0]
        conf = dict(record["conf"])
        conf["party_email"] = options["sender"] or account["username"]
        options["cc_team"] = False
        options["subject"] = "[TEST] " + options["subject"]
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            server = smtp_connect(account["host"], account["port"],
                                  account["security"], account["username"],
                                  account["password"], timeout=40)
            name, payload, problem = self.attachment_for(record)
            if problem:
                raise ValueError(problem)
            server.send_message(build_email_message(
                conf, name, payload, options))
            server.quit()
            QApplication.restoreOverrideCursor()
            self.show_mail_state("Test letter sent to <b>%s</b>. Check that it "
                                 "arrived, then send the full run."
                                 % conf["party_email"], "green")
            self.toast("Test email sent.", "ok")
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self.show_mail_state(friendly_smtp_error(exc), "red")
            self.toast("Test email failed.", "err")

    # ------------------------------------------------------ what is attached
    def attach_key(self):
        return self.mail_settings().get("attach_mode") or "pdf"

    def on_attach_mode(self, _index=0):
        if self._building:
            return
        self.mail_settings()["attach_mode"] = self.attach_mode.currentData()
        self.persist()
        self.refresh_email()

    def attachment_for(self, record):
        """(file name, bytes, problem) for one party under the chosen mode.
        Nothing is ever substituted silently: where the chosen kind of file is
        missing the problem is returned instead."""
        mode = self.attach_key()
        if mode == "signed":
            path = record.get("signed_path") or ""
            if not path:
                return "", b"", "No signed PDF linked"
            try:
                with open(path, "rb") as handle:
                    data = handle.read()
            except Exception as exc:
                return "", b"", "Signed PDF could not be read: %s" % exc
            if data[:5] != b"%PDF-":
                return "", b"", "The linked file is not a PDF"
            return os.path.basename(path), data, ""
        if mode == "docx":
            if not record.get("data"):
                return "", b"", "Document not available"
            return record["filename"], record["data"], ""
        if not record.get("pdf_data"):               # made on the spot if absent
            try:
                record["pdf_data"] = pdf_bytes(
                    record["conf"],
                    float(self.db["settings"].get("letterhead_space_cm", 0)
                          or 0))
                record["pdf_filename"] = \
                    os.path.splitext(record["filename"])[0] + ".pdf"
            except Exception as exc:
                return "", b"", "PDF could not be produced: %s" % exc
        return record["pdf_filename"], record["pdf_data"], ""

    def attachment_label(self, record):
        mode = self.attach_key()
        if mode == "signed":
            path = record.get("signed_path") or ""
            return os.path.basename(path) if path else "— none linked —"
        if mode == "docx":
            return record["filename"]
        return record.get("pdf_filename") or \
            os.path.splitext(record["filename"])[0] + ".pdf"

    def link_signed_folder(self, _checked=False, folder=None):
        done = [g for g in self.generated if g["status"] == "ok"]
        if not done:
            self.toast("Generate the letters first.", "warn")
            return
        if not folder:
            folder = QFileDialog.getExistingDirectory(
                self, "Folder holding the signed PDFs",
                self.run_output_folder() or os.path.expanduser("~"))
        if not folder:
            return
        try:
            paths = sorted(os.path.join(folder, name)
                           for name in os.listdir(folder)
                           if name.lower().endswith(".pdf"))
        except Exception as exc:
            self.toast("That folder could not be read: %s" % exc, "err")
            return
        # the unsigned PDFs this application wrote are not signed copies,
        # even when the client's scans are saved beside them
        generated = {os.path.normcase(os.path.abspath(g["pdf_path"]))
                     for g in done if g.get("pdf_path")}
        unsigned = [p for p in paths
                    if os.path.normcase(os.path.abspath(p)) in generated]
        paths = [p for p in paths if p not in unsigned and looks_like_pdf(p)]
        documents = [{"id": g["id"], "party_name": g["conf"]["party_name"],
                      "category": g["conf"]["category"],
                      "reference": g["conf"].get("reference", ""),
                      "filename": g["filename"]} for g in done]
        linked, loose = match_signed_pdfs(paths, documents)
        for record in done:
            if record["id"] in linked:
                record["signed_path"] = linked[record["id"]]
        if linked and self.attach_key() != "signed":
            self.mail_settings()["attach_mode"] = "signed"
            self.persist()
        self.refresh_email()
        text = "%d signed PDF%s linked" % (len(linked),
                                           "" if len(linked) == 1 else "s")
        if loose:
            text += ", %d file%s not matched to a party" % (
                len(loose), "" if len(loose) == 1 else "s")
        missing = len(done) - len([g for g in done if g.get("signed_path")])
        if missing:
            text += " · %d part%s still without one" % (
                missing, "y" if missing == 1 else "ies")
        if unsigned:
            text += " · %d unsigned original%s from this run left out" % (
                len(unsigned), "" if len(unsigned) == 1 else "s")
        self.toast(text + ".", "ok" if linked and not loose else "warn")

    def choose_signed_pdf(self, document_id, path=None):
        record = next((g for g in self.generated if g["id"] == document_id),
                      None)
        if not record:
            return
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Signed PDF for %s" % record["conf"]["party_name"],
                os.path.dirname(record.get("signed_path") or "")
                or self.run_output_folder() or os.path.expanduser("~"),
                "PDF files (*.pdf)")
        if not path:
            return
        if not looks_like_pdf(path):
            self.toast("That file is not a PDF.", "err")
            return
        record["signed_path"] = path
        self.refresh_email()

    def build_queue(self):
        existing = self.queue
        self.queue = {}
        for record in self.generated:
            if record["status"] != "ok":
                continue
            earlier = existing.get(record["id"])
            self.queue[record["id"]] = {
                "id": record["id"], "party": record["conf"]["party_name"],
                "category": record["conf"]["category"],
                "to": record["conf"].get("party_email", ""),
                "filename": record["filename"],
                "attachment": self.attachment_label(record),
                "has_attachment": self.attach_key() != "signed"
                                  or bool(record.get("signed_path")),
                "status": earlier["status"] if earlier else (
                    "pending" if valid_email(record["conf"].get("party_email"))
                    else "no email"),
                "detail": earlier["detail"] if earlier else "",
                "sent_at": earlier["sent_at"] if earlier else "",
            }

    def render_mail_table(self):
        self.mail_table.setRowCount(0)
        for entry in self.queue.values():
            row = self.mail_table.rowCount()
            self.mail_table.insertRow(row)
            self.mail_table.setItem(row, 0, cell(entry["party"], bold=True))
            self.mail_table.setItem(row, 1, cell(entry["category"]))
            self.mail_table.setItem(row, 2, cell(entry["to"] or "—"))
            self.mail_table.setItem(row, 3, cell(
                entry["attachment"],
                color=None if entry["has_attachment"] else T["warn"]))
            colour = {"sent": T["ok"], "failed": T["err"],
                      "no email": T["warn"]}.get(entry["status"], T["text_soft"])
            self.mail_table.setItem(row, 4, cell(entry["status"].upper(),
                                                 color=colour, bold=True))
            self.mail_table.setItem(row, 5, cell(entry["detail"]))
            pick = button("Choose PDF…")
            pick.setToolTip("Attach the signed, scanned letter for this party")
            pick.clicked.connect(
                lambda _=False, key=entry["id"]: self.choose_signed_pdf(key))
            self.mail_table.setCellWidget(row, 6, pick)
        self.mail_table.resizeColumnsToContents()
        fit_widget_columns(self.mail_table, [6])

    def refresh_email(self):
        self._building = True
        mail = self.mail_settings()
        index = self.mail_provider.findText(mail.get("provider", ""))
        if index >= 0:
            self.mail_provider.setCurrentIndex(index)
        self.mail_host.setText(mail.get("host", ""))
        self.mail_port.setValue(int(mail.get("port", 587) or 587))
        security = self.mail_security.findData(mail.get("security", "starttls"))
        if security >= 0:
            self.mail_security.setCurrentIndex(security)
        self.mail_username.setText(mail.get("username", ""))
        self.mail_sender.setText(mail.get("sender", ""))
        self.mail_sender_name.setText(mail.get("sender_name", ""))
        self.mail_subject.setText(mail.get("subject") or DEFAULT_SUBJECT)
        if self.mail_body.toPlainText() != (mail.get("body") or DEFAULT_BODY):
            self.mail_body.setPlainText(mail.get("body") or DEFAULT_BODY)
        self.cc_check.setChecked(bool(mail.get("cc_team", True)))
        self.reply_check.setChecked(bool(mail.get("reply_to_team", True)))
        self.delay_spin.setValue(int(mail.get("delay_ms", 1500) or 0))
        mode_index = self.attach_mode.findData(self.attach_key())
        if mode_index >= 0:
            self.attach_mode.setCurrentIndex(mode_index)
        self.remember_check.setChecked(bool(mail.get("remember_password"))
                                       and HAS_KEYRING)
        if (HAS_KEYRING and mail.get("remember_password")
                and not self.mail_password_edit.text()
                and mail.get("username")):
            try:
                stored = keyring.get_password("BalanceConfirmationGenerator",
                                              mail["username"])
                if stored:
                    self.mail_password_edit.setText(stored)
            except Exception:
                pass
        self._building = False
        self._mail_loaded = True

        self.build_queue()
        self.render_mail_table()
        pending = len([q for q in self.queue.values()
                       if q["status"] == "pending"])
        no_address = len([q for q in self.queue.values()
                          if q["status"] == "no email"])
        failed = len([q for q in self.queue.values()
                      if q["status"] == "failed"])
        self.attach_hint.setText(ATTACH_HINTS.get(self.attach_key(), ""))
        self.mail_note.setText(
            "%d documents · %d ready to send%s"
            % (len(self.queue), pending,
               (" · %d without a recipient address" % no_address)
               if no_address else "") if self.queue
            else "No documents generated yet")
        ready, _ = self.mail_ready()
        busy = self.send_thread is not None
        self.btn_send.setEnabled(bool(pending or failed) and ready and not busy)
        self.btn_retry.setEnabled(bool(failed) and ready and not busy)
        self.btn_log.setEnabled(bool(self.queue))
        self.btn_test_mail.setEnabled(
            bool([g for g in self.generated if g["status"] == "ok"]))
        self.refresh_chips()

    def start_send(self, retry_only):
        if self.send_thread:
            return
        ready, missing = self.mail_ready()
        if not ready:
            self.show_mail_state("Still needed: %s." % ", ".join(missing),
                                 "warn")
            return
        wanted = ["failed"] if retry_only else ["pending", "failed"]
        targets = [q for q in self.queue.values() if q["status"] in wanted]
        if not targets:
            self.toast("Nothing to send. Add party email addresses in "
                       "Review & mapping.", "warn")
            return
        account = self.mail_account()
        team = ", ".join(a["email"] for a in self.auditors())
        if not self.ask(
                "Send %d confirmation email%s"
                % (len(targets), "" if len(targets) == 1 else "s"),
                "From: %s\nRecipients: %d parties, each with its own %s."
                "%s\n\nConfirm that the letters have been reviewed. "
                "Emails sent cannot be recalled."
                % (account["username"], len(targets),
                   {"pdf": "PDF letter", "docx": "Word letter",
                    "signed": "signed PDF"}[self.attach_key()],
                   ("\nCc: " + team) if self.cc_check.isChecked() and team
                   else ""),
                "Send now", danger=False):
            return

        by_id = {g["id"]: g for g in self.generated}
        jobs, skipped = [], 0
        for entry in targets:
            record = by_id.get(entry["id"])
            if not record:
                entry["status"] = "failed"
                entry["detail"] = "Document not available"
                continue
            conf = record["conf"]
            if not valid_email(conf.get("party_email")):
                entry["status"] = "no email"
                entry["detail"] = "No valid recipient"
                continue
            name, payload, problem = self.attachment_for(record)
            if problem:
                # held back rather than sent with a different file: the
                # auditor chose what the party is to receive
                if entry["status"] != "failed":
                    entry["status"] = "pending"
                entry["detail"] = "Not sent: " + problem
                skipped += 1
                continue
            jobs.append((conf, name, payload))
        if not jobs:
            self.render_mail_table()
            self.toast("Nothing was sent: %s." % (
                "no signed PDF is linked to these parties"
                if skipped and self.attach_key() == "signed"
                else "no message had a valid recipient and attachment"),
                "warn")
            return

        for conf, _, _ in jobs:
            self.queue[conf["id"]]["status"] = "sending"
            self.queue[conf["id"]]["detail"] = ""
        self.render_mail_table()
        self.btn_send.setEnabled(False)
        self.btn_retry.setEnabled(False)
        self.mail_bar.setValue(0)

        self.send_thread = QThread(self)
        self.send_worker = SendWorker(jobs, account, self.mail_options(),
                                      self.delay_spin.value())
        self.send_worker.moveToThread(self.send_thread)
        self.send_thread.started.connect(self.send_worker.run)
        self.send_worker.progress.connect(self.on_send_progress)
        self.send_worker.result.connect(self.on_send_result)
        self.send_worker.finished.connect(self.on_send_finished)
        self.send_thread.start()

    def on_send_progress(self, done, total, party):
        self.mail_bar.setMaximum(max(total, 1))
        self.mail_bar.setValue(done)
        self.mail_progress.setText(
            "Sending…  %d of %d completed  —  %s" % (done, total,
                                                               party)
            if party else "Sending…  %d of %d completed" % (done, total))

    def on_send_result(self, document_id, status, detail, message_id=""):
        entry = self.queue.get(document_id)
        if entry:
            entry["status"] = status
            entry["detail"] = detail
            entry["sent_at"] = (datetime.now().isoformat(timespec="seconds")
                                if status == "sent" else "")
            self.render_mail_table()
        run = next((r for r in self.db["runs"]
                    if r["id"] == self.current_run_id), None)
        if run and entry:
            for document in run["documents"]:
                if document["filename"] == entry["filename"]:
                    document["email_status"] = status
                    document["email"] = entry["to"]
                    document["email_at"] = datetime.now().isoformat(
                        timespec="seconds")
                    document["sent_at"] = document["email_at"]
                    if message_id:
                        document["message_id"] = message_id

    def on_send_finished(self, sent, failed):
        if self.send_thread:
            self.send_thread.quit()
            self.send_thread.wait(5000)
        self.send_thread = None
        self.send_worker = None
        self.mail_progress.setText(
            "Finished — %d sent%s." % (sent, (", %d failed" % failed)
                                            if failed else ""))
        self.persist()
        self.refresh_email()
        self.toast("%d email%s sent%s." % (sent, "" if sent == 1 else "s",
                                           (", %d failed" % failed) if failed
                                           else ""),
                   "warn" if failed else "ok")

    def export_send_log(self):
        if not self.queue:
            return
        suggested = os.path.join(
            self.db["settings"].get("output_folder") or os.path.expanduser("~"),
            "balance-confirmation-send-log-%s.csv" % date.today().isoformat())
        path, _ = QFileDialog.getSaveFileName(self, "Export send log",
                                              suggested, "CSV files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Party", "Category", "Recipient", "File",
                                 "Status", "Detail", "Sent at"])
                for entry in self.queue.values():
                    writer.writerow([entry["party"], entry["category"],
                                     entry["to"], entry["filename"],
                                     entry["status"], entry["detail"],
                                     entry["sent_at"]])
            self.toast("Send log written to %s" % path, "ok")
        except Exception as exc:
            self.toast("The log could not be written: %s" % exc, "err")

    # =====================================================================
    # PAGE 08 - SAVED RUNS
    # =====================================================================
    def _page_runs(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        frame, body, header = card("Saved runs", "", light=True)
        self.runs_note = QLabel("No runs saved")
        self.runs_note.setObjectName("HintLight")
        header.addWidget(self.runs_note)
        self.runs_table = table(["Date", "Client", "Type of audit",
                                 "Year / period", "Source", "Documents",
                                 "Sent", ""], stretch_column=3)
        self.runs_table.setMinimumHeight(260)
        body.addWidget(self.runs_table)
        layout.addWidget(frame)

        self.run_detail_card, detail_body, detail_header = card(
            "Run detail", "")
        self.run_detail_note = QLabel("")
        self.run_detail_note.setObjectName("HintDark")
        detail_header.addWidget(self.run_detail_note)
        close = button("Close", small=True)
        close.clicked.connect(lambda: self.run_detail_card.setVisible(False))
        detail_header.addWidget(close)
        self.run_detail_table = table(["Party", "Category", "Balance", "File",
                                       "Email", "Delivery"], stretch_column=0)
        detail_body.addWidget(self.run_detail_table)
        self.run_detail_card.setVisible(False)
        layout.addWidget(self.run_detail_card, 1)
        layout.addStretch(1)
        return page

    def refresh_runs(self):
        runs = self.db["runs"]
        self.runs_note.setText("%d run(s) saved" % len(runs) if runs
                               else "No runs saved")
        self.runs_table.setRowCount(0)
        for run in runs:
            row = self.runs_table.rowCount()
            self.runs_table.insertRow(row)
            sent = len([d for d in run.get("documents", [])
                        if d.get("email_status") == "sent"])
            span = run.get("period_label") or period_label(
                run.get("basis"), run.get("as_at") or run.get("year_end"),
                run.get("period_start")) or ""
            audit = run.get("audit_type", "Statutory Audit")
            if audit == "Other":
                audit = run.get("audit_type_other") or "Other"
            self.runs_table.setItem(row, 0, cell(stamp_text(
                run.get("created_at"))))
            self.runs_table.setItem(row, 1, cell(run.get("client_name"),
                                                 bold=True))
            self.runs_table.setItem(row, 2, cell(audit))
            self.runs_table.setItem(row, 3, cell("%s  ·  %s"
                                                 % (run.get("year"), span)))
            source = run.get("source")
            self.runs_table.setItem(row, 4, cell(
                "%s / %s" % (source["name"], source["sheet"]) if source
                else "—"))
            self.runs_table.setItem(row, 5, cell(len(run.get("documents", [])),
                                                 align_right=True))
            self.runs_table.setItem(row, 6, cell(sent, align_right=True))
            holder = pane()
            box = QHBoxLayout(holder)
            box.setContentsMargins(4, 2, 4, 2)
            box.setSpacing(5)
            view = button("View", small=True)
            view.clicked.connect(lambda _, r=run: self.show_run(r))
            folder = button("Folder", small=True)
            folder.clicked.connect(lambda _, r=run: self.open_run_folder(r))
            delete = button("Delete", "danger", small=True)
            delete.clicked.connect(lambda _, r=run: self.delete_run(r))
            for widget in (view, folder, delete):
                box.addWidget(widget)
            box.addStretch(1)
            self.runs_table.setCellWidget(row, 7, holder)
        self.runs_table.resizeColumnsToContents()
        fit_widget_columns(self.runs_table, [7])

    def show_run(self, run):
        self.run_detail_card.setVisible(True)
        audit = run.get("audit_type", "Statutory Audit")
        if audit == "Other":
            audit = run.get("audit_type_other") or "Other"
        span = run.get("period_label") or ""
        self.run_detail_note.setText(
            "%s · %s · %s · %s"
            % (run.get("client_name"), audit, span,
               stamp_text(run.get("created_at"))))
        self.run_detail_table.setRowCount(0)
        for document in run.get("documents", []):
            row = self.run_detail_table.rowCount()
            self.run_detail_table.insertRow(row)
            self.run_detail_table.setItem(row, 0, cell(document["party_name"],
                                                       bold=True))
            self.run_detail_table.setItem(row, 1, cell(document["category"]))
            self.run_detail_table.setItem(row, 2, cell(
                amount_label(document.get("amount"),
                             document.get("currency")) or "—",
                align_right=True))
            self.run_detail_table.setItem(row, 3, cell(document["filename"]))
            self.run_detail_table.setItem(row, 4,
                                          cell(document.get("email") or "—"))
            status = document.get("email_status", "not sent")
            colour = {"sent": T["ok"], "failed": T["err"]}.get(status,
                                                                  T["text_mute"])
            self.run_detail_table.setItem(row, 5, cell(status.upper(),
                                                       color=colour))
        self.run_detail_table.resizeColumnsToContents()

    def open_run_folder(self, run):
        folder = run.get("folder")
        if not folder or not os.path.isdir(folder):
            self.toast("That run's folder is no longer on this computer.",
                       "warn")
            return
        try:
            if os.name == "nt":
                os.startfile(folder)                       # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            self.toast("The files are in %s" % folder, "info")

    def delete_run(self, run):
        if not self.ask("Delete run",
                        "Delete the run of %s for %s? The Word files already "
                        "saved on disk are not affected."
                        % (stamp_text(run.get("created_at")),
                           run.get("client_name")), "Delete run"):
            return
        self.db["runs"] = [r for r in self.db["runs"] if r["id"] != run["id"]]
        self.persist()
        self.refresh_runs()
        self.refresh_clients()
        self.toast("Run deleted.", "ok")

    # =====================================================================
    # PAGE 08 - CONFIRMATIONS RECEIVED
    # ---------------------------------------------------------------------
    # The replies that came back, reconciled against what was sent, with the
    # six reports an auditor puts in the working papers.  Replies reach this
    # page from the saved records; the Gmail bridge writes into the same
    # place, so nothing here has to change when it is connected.
    # =====================================================================
    def _page_recon(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        frame, body, header = card("Position", "")
        self.recon_scope = QLabel("")
        self.recon_scope.setObjectName("HintDark")
        header.addWidget(self.recon_scope)
        refresh = button("Recalculate")
        refresh.clicked.connect(self.refresh_recon)
        sync = button("Sync Gmail bridge", "primary")
        sync.setToolTip(
            "Read the replies the Apps Script has been collecting on Google's "
            "servers since the last sync")
        sync.clicked.connect(lambda: self.sync_bridge())
        import_replies = button("Import replies (JSON)…", "brass")
        import_replies.setToolTip(
            "Load replies from a file you have prepared or downloaded "
            "yourself")
        import_replies.clicked.connect(self.import_replies)
        header.addWidget(refresh)
        header.addWidget(sync)
        header.addWidget(import_replies)

        self.bridge_note = QLabel("")
        self.bridge_note.setObjectName("HintDark")
        body.addWidget(self.bridge_note)

        # the reply's own document: fetched, opened and read on this computer
        reader_row = QHBoxLayout()
        reader_row.setSpacing(8)
        self.btn_read_docs = button("Read attached PDFs (OCR)", "primary")
        self.btn_read_docs.setToolTip(
            "Download each reply's PDF or scan from the bridge and read the "
            "confirmed amount from it on this computer")
        self.btn_read_docs.clicked.connect(
            lambda: self.read_reply_documents(retry=True))
        self.btn_add_pdf = button("Add a reply from a PDF or scan…")
        self.btn_add_pdf.setToolTip(
            "For a confirmation received by post, by hand or on another "
            "mailbox: the file is read and matched to its party")
        self.btn_add_pdf.clicked.connect(lambda: self.add_reply_from_file())
        self.reader_note = QLabel("")
        self.reader_note.setObjectName("HintDark")
        self.reader_note.setWordWrap(True)
        reader_row.addWidget(self.btn_read_docs)
        reader_row.addWidget(self.btn_add_pdf)
        reader_row.addWidget(self.reader_note, 1)
        body.addLayout(reader_row)
        self.recon_stats = QHBoxLayout()
        self.recon_stats.setSpacing(10)
        body.addLayout(self.recon_stats)
        # replies waiting for a decision are never left for the reviewer to
        # stumble on: the page says so and takes them there
        self.btn_queue = button("", "brass")
        self.btn_queue.setToolTip("Open the Exception Queue")
        self.btn_queue.clicked.connect(
            lambda: self.show_report(REPORT_EXCEPTIONS))
        self.btn_queue.setVisible(False)
        queue_row = QHBoxLayout()
        queue_row.addWidget(self.btn_queue)
        queue_row.addStretch(1)
        body.addLayout(queue_row)
        layout.addWidget(frame)

        frame2, body2, header2 = card("Reports", "", light=True)
        self.report_note = QLabel("")
        self.report_note.setObjectName("HintLight")
        header2.addWidget(self.report_note)
        self.btn_assign = button("Review reply…")
        self.btn_assign.setToolTip(
            "Read the selected reply, choose the party and request it "
            "belongs to, and accept the confirmed value - or set it aside")
        self.btn_assign.clicked.connect(self.assign_selected_reply)
        header2.addWidget(self.btn_assign)
        self.btn_audit = button("Audit status…")
        self.btn_audit.setToolTip(
            "Create or open the follow-up record for the selected "
            "confirmation")
        self.btn_audit.clicked.connect(self.audit_selected_row)
        header2.addWidget(self.btn_audit)
        excel = button("Export all to Excel", "primary")
        excel.clicked.connect(self.export_reports_excel)
        pdf = button("Export all to PDF", "blue")
        pdf.clicked.connect(self.export_reports_pdf)
        header2.addWidget(excel)
        header2.addWidget(pdf)

        chooser = QHBoxLayout()
        chooser.setSpacing(8)
        chooser.addWidget(field_label("Report", light=True))
        self.report_combo = QComboBox()
        for key, title, _subtitle in REPORT_TITLES:
            self.report_combo.addItem(title, key)
        self.report_combo.setMinimumWidth(300)
        self.report_combo.currentIndexChanged.connect(self.render_report)
        chooser.addWidget(self.report_combo)
        self.report_subtitle = QLabel("")
        self.report_subtitle.setObjectName("HintLight")
        chooser.addWidget(self.report_subtitle)
        chooser.addStretch(1)
        body2.addLayout(chooser)

        self.report_table = table([""])
        self.report_table.setMinimumHeight(360)
        self.report_table.cellClicked.connect(self.on_report_cell)
        body2.addWidget(self.report_table)
        self.report_totals = QLabel("")
        self.report_totals.setObjectName("HintLight")
        self.report_totals.setWordWrap(True)
        body2.addWidget(self.report_totals)
        layout.addWidget(frame2, 1)
        return page

    # ----------------------------------------------------------- the data
    def sent_documents(self):
        """Every confirmation issued for the active client and year, flattened
        out of the saved runs so repeat runs do not double-count a party."""
        client = self.active_client()
        year = self.active_fy()
        if not client or not year:
            return []
        documents, seen = [], set()
        for run in self.db["runs"]:
            if run.get("client_id") != client["id"] or \
                    run.get("fy_id") != year["id"]:
                continue
            for document in run.get("documents", []):
                key = (document.get("party_name", ""),
                       document.get("category", ""))
                if key in seen:          # a later run supersedes an earlier one
                    continue
                seen.add(key)
                entry = dict(document)
                entry.setdefault("id", document.get("filename"))
                entry.setdefault("sent_at", document.get("email_at")
                                 or document.get("generated_at"))
                documents.append(entry)
        return documents

    def stored_replies(self):
        client = self.active_client()
        year = self.active_fy()
        if not client or not year:
            return []
        return [r for r in self.db.get("replies", [])
                if r.get("client_id") in (None, client["id"])
                and r.get("fy_id") in (None, year["id"])]

    def refresh_recon(self):
        documents = self.sent_documents()
        replies = self.stored_replies()
        for held in replies:    # dates recorded a day early by older builds
            if held.get("received_at"):
                held["received_at"] = local_stamp(held["received_at"])
        settings = self.db["settings"]
        mail = settings.get("mail") or {}
        self.recon_ignored = []
        self.recon_set_aside = []
        self.recon_rows, self.recon_exceptions = build_reconciliation(
            documents, replies,
            tolerance=float(settings.get("variance_tolerance",
                                         DEFAULT_TOLERANCE)),
            reminders=tuple(settings.get("reminder_days", DEFAULT_REMINDERS)),
            # the request is copied to the team, so it comes back through the
            # bridge: our own letter must never be counted as a reply
            own_addresses=(mail.get("username"), mail.get("sender")),
            ignored=self.recon_ignored, set_aside=self.recon_set_aside)
        attach_audit_status(self.recon_rows, self.audit_records())
        self.recon_summary = summarise(self.recon_rows)

        client = self.active_client()
        year = self.active_fy()
        self.recon_scope.setText(
            "%s · %s · %d confirmations issued, %d replies on record%s"
            % (client["name"] if client else "no client",
               year["year"] if year else "no year",
               len(documents), len(replies) - len(self.recon_ignored),
               ((" · %d cop%s of your own request ignored"
                 % (len(self.recon_ignored),
                    "y" if len(self.recon_ignored) == 1 else "ies"))
                if self.recon_ignored else "") +
               ((" · %d set aside" % len(self.recon_set_aside))
                if self.recon_set_aside else ""))
            if client else "Select a client to see its position")

        summary = self.recon_summary
        self._clear(self.recon_stats)
        for key, value, meta, accent in (
                ("Sent", summary["sent"], "Confirmations issued", T["accent"]),
                ("Received", summary["received"], "Replies matched", T["info"]),
                ("Matched", summary["agreed"], "No variance", T["ok"]),
                ("Mismatch", summary["variance"],
                 "Differs from books", T["err"]),
                ("Review", len(self.recon_exceptions),
                 "Replies to decide", T["warn"]),
                ("Pending", summary["pending"], "No reply yet", T["text_mute"]),
                ("Returned", summary["returned"], "Undelivered", T["err"]),
                ("Coverage", "%.1f%%" % summary["coverage_pct"],
                 "By value of balances", T["accent_hi"])):
            self.recon_stats.addWidget(stat_card(key, value, meta, accent))
        self.recon_stats.addStretch(1)
        waiting = len(self.recon_exceptions)
        self.btn_queue.setVisible(bool(waiting))
        self.btn_queue.setText(
            "%d repl%s received but not yet counted - review %s in the "
            "Exception Queue" % (waiting, "y" if waiting == 1 else "ies",
                                 "it" if waiting == 1 else "them"))
        self.refresh_bridge_note()
        self.refresh_reader_note()
        self.render_report()
        self.refresh_chips()

    def current_reports(self):
        if not hasattr(self, "recon_rows"):
            self.recon_rows, self.recon_exceptions = [], []
        return build_all_reports(
            self.recon_rows, self.recon_exceptions, self.report_context())

    def report_context(self):
        return {"reminders": tuple(self.db["settings"].get(
                    "reminder_days", DEFAULT_REMINDERS)),
                "audit_records": self.audit_records()}

    def audit_records(self):
        """Follow-up records for the confirmations of this client and year."""
        keys = {document_key(d) for d in self.sent_documents()}
        return [r for r in self.db.setdefault("audit_status", [])
                if r.get("document_id") in keys]

    def show_report(self, key):
        index = self.report_combo.findData(key)
        if index >= 0:
            self.report_combo.setCurrentIndex(index)
            self.render_report()

    def render_report(self):
        key = self.report_combo.currentData()
        report = build_report(key, getattr(self, "recon_rows", []),
                              getattr(self, "recon_exceptions", []),
                              self.report_context())
        self.current_report = report
        self.report_subtitle.setText(report["subtitle"])
        if hasattr(self, "btn_assign"):
            self.btn_assign.setVisible(key == REPORT_EXCEPTIONS)
            self.btn_audit.setVisible(key in (REPORT_COMPARISON,
                                              REPORT_REGISTER, REPORT_AUDIT))
        headings = [h for h, _k, _t in report["columns"]]
        self.report_table.clear()
        self.report_table.setColumnCount(len(headings))
        self.report_table.setHorizontalHeaderLabels(headings)
        self.report_table.setRowCount(len(report["rows"]))

        tone = {STATUS_AGREED: T["ok"], STATUS_VARIANCE: T["err"],
                STATUS_REVIEW: T["err"], STATUS_RETURNED: T["err"],
                STATUS_PENDING: T["text_mute"], STATUS_NOT_SENT: T["text_mute"]}
        for row_index, row in enumerate(report["rows"]):
            currency = row.get("currency") or "INR"
            for column_index, (_heading, field, kind) in enumerate(
                    report["columns"]):
                value = row.get(field)
                is_link = kind in ("link", "action")
                if is_link:
                    # on screen a link says what clicking it does
                    value = row.get(field + "_link", value)
                text = format_cell(value, kind, currency)
                item = cell(text,
                            align_right=kind in ("money", "number", "pct",
                                                 "pct_unit"),
                            color=(tone.get(value) if kind == "status" else
                                   T["info"] if is_link and text else None),
                            bold=kind == "status")
                if is_link and text:
                    font = item.font()
                    font.setUnderline(True)
                    item.setFont(font)
                    item.setToolTip("Click to open")
                self.report_table.setItem(row_index, column_index, item)
        self.report_table.resizeColumnsToContents()
        # fill the width rather than leaving a bare strip beside the last column
        self.report_table.horizontalHeader().setStretchLastSection(True)

        if report["totals"]:
            parts = []
            for heading, field, kind in report["columns"]:
                if field in report["totals"]:
                    parts.append("%s: %s" % (heading,
                                             format_cell(report["totals"][field],
                                                         kind, "INR")))
            self.report_totals.setText("Total — " + " · ".join(parts))
        else:
            self.report_totals.setText("")
        self.report_note.setText("%d row%s" % (len(report["rows"]),
                                               "" if len(report["rows"]) == 1
                                               else "s"))

    # ------------------------------------------------ links in the reports
    def on_report_cell(self, row_index, column_index):
        report = getattr(self, "current_report", None)
        if not report or row_index >= len(report["rows"]) or \
                column_index >= len(report["columns"]):
            return
        _heading, field, kind = report["columns"][column_index]
        row = report["rows"][row_index]
        if kind == "action" and field == "review":
            self.review_exception(row)
        elif kind == "link" and (row.get(field + "_link") or row.get(field)):
            self.open_audit_status(row)

    def reviewer_names(self):
        names = [str(a.get("name") or "").strip()
                 for a in self.db["settings"].get("auditors", [])]
        last = str(self.db["settings"].get("last_reviewer") or "").strip()
        ordered = ([last] if last else []) + [n for n in names if n != last]
        return [name for name in ordered if name]

    # ------------------------------------------- deciding a reply by hand
    def assign_reply(self, reply_id, target, amount=None, by="", note=""):
        """Record the reviewer's decision on one reply.

        target is a confirmation's id, SET_ASIDE (not a confirmation for any
        party), or "" to hand the reply back to automatic matching.  amount
        is the confirmed value the reviewer accepted.  The decision, who made
        it and when stay on the reply itself, beside the original e-mail's
        id, sender, date and link, so both can be traced later."""
        for reply in self.db.get("replies", []):
            if str(reply.get("id")) != str(reply_id):
                continue
            for field in ("assigned_to", "assigned_at", "accepted_amount",
                          "decided_by", "decided_at", "decision_note"):
                reply.pop(field, None)
            if target:
                stamp = datetime.now().isoformat(timespec="seconds")
                reply["assigned_to"] = target
                reply["assigned_at"] = stamp
                reply["decided_at"] = stamp
                reply["decided_by"] = str(by or "").strip()
                reply["decision_note"] = str(note or "").strip()
                if amount is not None and target != SET_ASIDE:
                    reply["accepted_amount"] = float(amount)
                if reply["decided_by"]:
                    self.db["settings"]["last_reviewer"] = reply["decided_by"]
            self.persist()
            self.refresh_recon()
            return True
        return False

    def assign_selected_reply(self):
        if self.report_combo.currentData() != REPORT_EXCEPTIONS:
            self.toast("Open the Exception Queue and select a reply first.",
                       "warn")
            return
        index = self.report_table.currentRow()
        queue = getattr(self, "recon_exceptions", [])
        if index < 0 or index >= len(queue):
            self.toast("Select a reply in the Exception Queue first.", "warn")
            return
        self.review_exception(queue[index])

    def review_exception(self, entry):
        """Review one reply from the queue and act on the decision."""
        if not entry.get("reply_id"):
            self.toast("That row has no reply to review.", "warn")
            return
        decision = self.choose_party_dialog(entry)
        if decision is None:
            return
        if not isinstance(decision, dict):          # a bare target
            decision = {"target": decision, "amount": entry.get("amount"),
                        "by": "", "note": ""}
        target = decision.get("target", "")
        self.assign_reply(entry["reply_id"], target,
                          decision.get("amount"), decision.get("by", ""),
                          decision.get("note", ""))
        if target == SET_ASIDE:
            self.toast("Reply set aside: it is kept on record but not "
                       "counted.", "ok")
        elif target:
            row = next((r for r in self.recon_rows
                        if r["document_id"] == target), None)
            self.toast("Accepted for %s: %s." % (
                row["party_name"] if row else "the party",
                row["status"] if row else "recorded"), "ok")
        else:
            self.toast("Reply handed back to automatic matching.", "ok")

    def choose_party_dialog(self, entry):
        """The review window for one reply.

        Shows the e-mail as received, offers the party the evidence suggests,
        and takes the reviewer's choice of party and request, the confirmed
        value, their name and a note.  Returns {target, amount, by, note},
        or None if cancelled."""
        reply = next((r for r in self.db.get("replies", [])
                      if str(r.get("id")) == str(entry.get("reply_id"))), {})
        dialog = QDialog(self)
        dialog.setWindowTitle("Review reply")
        dialog.setMinimumWidth(640)
        layout = QVBoxLayout(dialog)

        link = str(entry.get("message_link") or "")
        facts = QLabel(
            "<b>From:</b> %s %s<br><b>Received:</b> %s<br><b>Subject:</b> %s"
            "<br><b>Why it is here:</b> %s%s" % (
                xml_escape(entry.get("from_name") or ""),
                xml_escape("<%s>" % (entry.get("from_email") or "unknown")),
                xml_escape(fmt_date_long(str(entry.get("received_at")
                                             or "")[:10]) or
                           str(entry.get("received_at") or "")),
                xml_escape(entry.get("subject") or ""),
                xml_escape(entry.get("reason") or ""),
                ('<br><a href="%s" style="color: %s;">Open the original '
                 'e-mail</a>' % (xml_escape(link), T["info"]))
                if link else ""))
        facts.setWordWrap(True)
        facts.setOpenExternalLinks(True)
        layout.addWidget(facts)

        words = QPlainTextEdit()
        words.setReadOnly(True)
        words.setPlainText(strip_quoted(str(reply.get("body") or ""))
                           or "(the reply has no text of its own)")
        words.setMaximumHeight(120)
        layout.addWidget(QLabel("What the party wrote:"))
        layout.addWidget(words)

        hint = QLabel("")
        hint.setWordWrap(True)
        if entry.get("suggested_to"):
            hint.setText("<b>Suggested:</b> %s - %s." % (
                xml_escape(entry.get("suggested_party") or ""),
                xml_escape(entry.get("suggestion") or "")))
        elif entry.get("candidates"):
            hint.setText("<b>Evidence points to:</b> %s. No single party "
                         "can be suggested with confidence - choose one."
                         % xml_escape(entry["candidates"]))
        else:
            hint.setText("Nothing in the reply identifies a party - "
                         "choose one.")
        layout.addWidget(hint)

        form = QFormLayout()
        combo = QComboBox()
        combo.addItem("Choose the party and request…", None)
        for document in sorted(self.sent_documents(),
                               key=lambda d: (d.get("party_name", "").lower(),
                                              d.get("category", ""))):
            combo.addItem("%s — %s — %s — books %s" % (
                document.get("party_name", ""), document.get("category", ""),
                document.get("reference", "") or "no reference",
                fmt_amount(document.get("amount"),
                           document.get("currency") or "INR")),
                document_key(document))
        combo.addItem("Set aside — not a confirmation for any party",
                      SET_ASIDE)
        combo.addItem("Return it to automatic matching", "")
        if entry.get("suggested_to"):
            combo.setCurrentIndex(max(0, combo.findData(
                entry["suggested_to"])))
        combo.setObjectName("review_party")
        form.addRow("Belongs to", combo)

        amount = QLineEdit()
        if entry.get("amount") is not None:
            amount.setText("%.2f" % entry["amount"])
        amount.setPlaceholderText("the balance the party confirms")
        amount.setObjectName("review_amount")
        form.addRow("Confirmed value", amount)

        reviewer = QComboBox()
        reviewer.setEditable(True)
        reviewer.addItems(self.reviewer_names())
        if not self.reviewer_names():
            reviewer.setEditText("")
        reviewer.setObjectName("review_by")
        form.addRow("Reviewed by", reviewer)
        note = QLineEdit()
        note.setObjectName("review_note")
        note.setPlaceholderText("optional - why this party, or why set aside")
        form.addRow("Note", note)
        layout.addLayout(form)

        problem = QLabel("")
        problem.setObjectName("review_problem")
        problem.setWordWrap(True)
        problem.setStyleSheet("color: %s;" % T["err"])
        layout.addWidget(problem)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        accept = buttons.addButton("Accept",
                                   QDialogButtonBox.ButtonRole.AcceptRole)
        accept.setObjectName("review_accept")
        layout.addWidget(buttons)
        decision = {}

        def try_accept():
            target = combo.currentData()
            if target is None:
                problem.setText("Choose the party and request this reply "
                                "belongs to, or set it aside.")
                return
            value = None
            if target and target != SET_ASIDE:
                value = parse_amount(amount.text())[0] \
                    if amount.text().strip() else None
                if value is None:
                    problem.setText("Enter the confirmed value as a number, "
                                    "for example 2311786 or 23,11,786.00.")
                    return
            name = reviewer.currentText().strip()
            if target != "" and not name:
                problem.setText("Enter the name of the person reviewing "
                                "this reply.")
                return
            decision.update(target=target, amount=value, by=name,
                            note=note.text().strip())
            dialog.accept()

        accept.clicked.connect(try_accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() != QDialog.DialogCode.Accepted or not decision:
            return None
        return decision

    # ------------------------------------------------ audit-status records
    def audit_selected_row(self):
        report = getattr(self, "current_report", None)
        index = self.report_table.currentRow()
        if not report or index < 0 or index >= len(report["rows"]):
            self.toast("Select a confirmation in the table first.", "warn")
            return
        self.open_audit_status(report["rows"][index])

    def save_audit_status(self, row, state, nature, owner, notes, by=""):
        """Create the follow-up record for a confirmation, or update it.

        The record is tied to the party, the request sent and the reply
        received, and every change is added to its history."""
        records = self.db.setdefault("audit_status", [])
        record = audit_record_for(records, row.get("document_id"))
        stamp = datetime.now().isoformat(timespec="seconds")
        if record is None:
            record = {"id": new_id(), "created_at": stamp,
                      "created_by": str(by or owner or "").strip(),
                      "history": []}
            client, year = self.active_client(), self.active_fy()
            record["client_id"] = client["id"] if client else None
            record["fy_id"] = year["id"] if year else None
            records.append(record)
        record.update(audit_snapshot(row))
        record.update(state=state, nature=nature,
                      owner=str(owner or "").strip(),
                      notes=str(notes or "").strip(), updated_at=stamp)
        record["history"].append({
            "at": stamp, "by": str(by or owner or "").strip(),
            "state": state, "nature": nature,
            "confirmation_status": row.get("status", ""),
            "notes": str(notes or "").strip()})
        self.persist()
        self.refresh_recon()
        return record

    def open_audit_status(self, row):
        # a row of the audit report is the record itself; find the live row
        live = next((r for r in getattr(self, "recon_rows", [])
                     if r["document_id"] == row.get("document_id")), None)
        if live is None:
            self.toast("That confirmation is no longer on record.", "warn")
            return
        record = audit_record_for(self.audit_records(), live["document_id"])
        if record is None and not needs_audit_status(live):
            self.toast("An audit-status record is opened for a Mismatch or "
                       "a reply that Needs Review. %s is %s."
                       % (live["party_name"], live["status"]), "info")
            return
        result = self.audit_status_dialog(live, record)
        if result is None:
            return
        self.save_audit_status(live, result["state"], result["nature"],
                               result["owner"], result["notes"],
                               result["owner"])
        self.toast("Audit status saved for %s: %s."
                   % (live["party_name"], result["state"]), "ok")

    def audit_status_dialog(self, row, record):
        """Create or edit the follow-up record.  Returns {state, nature,
        owner, notes} or None if cancelled."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Audit status - %s" % row["party_name"])
        dialog.setMinimumWidth(620)
        layout = QVBoxLayout(dialog)
        money = lambda value: (fmt_amount(value, row.get("currency") or "INR")
                               if value is not None else "-")
        link = str(row.get("message_link") or "")
        facts = QLabel(
            "<b>Party:</b> %s (%s)<br>"
            "<b>Request:</b> reference %s, sent %s to %s<br>"
            "<b>Reply:</b> %s<br>"
            "<b>As per books:</b> %s &nbsp; <b>Confirmed:</b> %s &nbsp; "
            "<b>Variance:</b> %s<br><b>Confirmation status:</b> %s<br>%s%s"
            % (xml_escape(row["party_name"]), xml_escape(row["category"]),
               xml_escape(row.get("reference") or "-"),
               xml_escape(fmt_date_long(str(row.get("sent_at") or "")[:10])
                          or "-"),
               xml_escape(row.get("email") or "-"),
               xml_escape(("from %s, received %s%s" % (
                   row.get("reply_from") or "unknown sender",
                   fmt_date_long(str(row.get("received_at") or "")[:10])
                   or "date unknown",
                   " (%d replies on record)" % row["replies_count"]
                   if row.get("replies_count", 0) > 1 else ""))
                   if row.get("replies_count") else "none counted yet"),
               xml_escape(money(row.get("books_amount"))),
               xml_escape(money(row.get("confirmed_amount"))),
               xml_escape(money(row.get("variance"))),
               xml_escape(row.get("status", "")),
               xml_escape(row.get("note") or ""),
               ('<br><a href="%s" style="color: %s;">Open the original '
                'e-mail</a>' % (xml_escape(link), T["info"]))
               if link else ""))
        facts.setWordWrap(True)
        facts.setOpenExternalLinks(True)
        layout.addWidget(facts)

        form = QFormLayout()
        state = QComboBox()
        state.addItems(AUDIT_STATES)
        nature = QComboBox()
        nature.addItems(AUDIT_NATURES)
        owner = QComboBox()
        owner.setEditable(True)
        owner.addItems(self.reviewer_names())
        notes = QPlainTextEdit()
        notes.setPlaceholderText(
            "What was found, what was asked of the client or the party, "
            "what evidence was obtained, and the conclusion")
        notes.setMinimumHeight(110)
        if record:
            state.setCurrentIndex(max(0, state.findText(
                record.get("state", ""))))
            nature.setCurrentIndex(max(0, nature.findText(
                record.get("nature", ""))))
            owner.setEditText(record.get("owner", ""))
            notes.setPlainText(record.get("notes", ""))
        elif row.get("status") == STATUS_REVIEW:
            nature.setCurrentIndex(nature.findText(
                "Reply could not be matched or read"))
        state.setObjectName("audit_state")
        nature.setObjectName("audit_nature")
        owner.setObjectName("audit_owner")
        notes.setObjectName("audit_notes")
        form.addRow("Follow-up", state)
        form.addRow("Nature of difference", nature)
        form.addRow("Owner", owner)
        form.addRow("Notes", notes)
        layout.addLayout(form)

        if record and record.get("history"):
            past = QLabel("<b>History</b><br>" + "<br>".join(
                "%s - %s - %s" % (
                    xml_escape(str(h.get("at", "")).replace("T", " ")),
                    xml_escape(h.get("by") or "unnamed"),
                    xml_escape(h.get("state", "")))
                for h in record["history"][-6:]))
            past.setWordWrap(True)
            layout.addWidget(past)

        problem = QLabel("")
        problem.setObjectName("audit_problem")
        problem.setStyleSheet("color: %s;" % T["err"])
        layout.addWidget(problem)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        save = buttons.addButton("Save record",
                                 QDialogButtonBox.ButtonRole.AcceptRole)
        save.setObjectName("audit_save")
        layout.addWidget(buttons)
        result = {}

        def try_save():
            if not owner.currentText().strip():
                problem.setText("Enter who owns this follow-up.")
                return
            result.update(state=state.currentText(),
                          nature=nature.currentText(),
                          owner=owner.currentText().strip(),
                          notes=notes.toPlainText().strip())
            dialog.accept()

        save.clicked.connect(try_save)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() != QDialog.DialogCode.Accepted or not result:
            return None
        return result

    # --------------------------------------------------------- the exports
    def report_heading(self):
        client = self.active_client()
        year = self.active_fy()
        summary = getattr(self, "recon_summary", None) or summarise([])
        facts = [("Client", client["name"] if client else "—"),
                 ("Financial year", year["year"] if year else "—"),
                 ("Confirmations as at",
                  fmt_date_long(fy_as_at(year)) if year else "—"),
                 ("Type of audit", fy_audit_type(year) if year else "—"),
                 ("Audit firm", self.db["settings"].get("firm_name", "")),
                 ("Prepared on", fmt_date_long(date.today())),
                 ("Coverage by value", "%.2f%%" % summary["coverage_pct"])]
        return {"title": "Balance confirmation — reconciliation reports",
                "author": self.db["settings"].get("firm_name", ""),
                "facts": facts}

    def _export_path(self, extension, label):
        client = self.active_client()
        year = self.active_fy()
        base = sanitize_filename("%s - Balance confirmation %s - %s"
                                 % (client["name"] if client else "Client",
                                    label, year["year"] if year else ""))
        start = os.path.join(self.db["settings"].get("output_folder")
                             or os.path.expanduser("~"), base + extension)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save the reports", start,
            ("Excel workbook (*.xlsx)" if extension == ".xlsx"
             else "PDF document (*.pdf)"))
        return path

    def export_reports_excel(self):
        if not getattr(self, "recon_rows", None):
            self.toast("Nothing to report yet — send some confirmations "
                       "first.", "warn")
            return
        path = self._export_path(".xlsx", "reports")
        if not path:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            write_reports_xlsx(path, self.current_reports(),
                               self.report_heading())
            QApplication.restoreOverrideCursor()
            self.toast("Workbook written to %s" % path, "ok")
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self.toast("The workbook could not be written: %s" % exc, "err")

    def export_reports_pdf(self):
        if not getattr(self, "recon_rows", None):
            self.toast("Nothing to report yet — send some confirmations "
                       "first.", "warn")
            return
        path = self._export_path(".pdf", "reports")
        if not path:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            write_reports_pdf(path, self.current_reports(),
                              self.report_heading())
            QApplication.restoreOverrideCursor()
            self.toast("PDF written to %s" % path, "ok")
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self.toast("The PDF could not be written: %s" % exc, "err")

    def import_replies(self):
        """Load replies from a JSON file: a list of reply records, or the
        object the Gmail bridge writes ({"replies": [...]})."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import replies", os.path.expanduser("~"),
            "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:
            self.toast("That file is not valid JSON: %s" % exc, "err")
            return
        incoming = payload.get("replies") if isinstance(payload, dict) \
            else payload
        if not isinstance(incoming, list):
            self.toast("That file does not hold a list of replies.", "err")
            return
        added, seen = self.merge_replies(incoming)
        self.toast("%d new repl%s imported (%d already on record)."
                   % (added, "y" if added == 1 else "ies", seen - added), "ok")

    def merge_replies(self, incoming):
        """Add replies that are not already on record.  Returns the number
        added and the number offered, so both the file import and the bridge
        sync can report the same way."""
        client = self.active_client()
        year = self.active_fy()
        store = self.db.setdefault("replies", [])
        for held in store:      # dates recorded a day early by older builds
            if held.get("received_at"):
                held["received_at"] = local_stamp(held["received_at"])
        known = {r.get("id") for r in store}
        added = offered = 0
        for reply in incoming:
            if not isinstance(reply, dict):
                continue
            offered += 1
            reply = dict(reply)
            reply.setdefault("id", new_id())
            if reply.get("received_at"):
                reply["received_at"] = local_stamp(reply["received_at"])
            if reply["id"] in known:            # never count a reply twice
                # ...but learn what is attached, if the bridge now says so
                if reply.get("files"):
                    for held in store:
                        if held.get("id") == reply["id"] and \
                                not held.get("files"):
                            held["files"] = list(reply["files"])
                continue
            reply.setdefault("client_id", client["id"] if client else None)
            reply.setdefault("fy_id", year["id"] if year else None)
            store.append(reply)
            known.add(reply["id"])
            added += 1
        self.persist()
        self.refresh_recon()
        return added, offered

    # ------------------------------------------------- the always-on bridge
    def sync_bridge(self, quiet=False):
        """Read the feed published by the Gmail Apps Script.  The script
        collects replies on Google's servers while this computer is off; this
        is the one call that brings them across."""
        url = (self.db["settings"].get("bridge_feed_url") or "").strip()
        if not url:
            if not quiet:
                self.toast("No bridge address saved.  Settings > Gmail bridge.",
                           "warn")
            return
        if not url.lower().startswith("https://"):
            if not quiet:
                self.toast("The bridge address must begin with https://",
                           "err")
            return
        if getattr(self, "bridge_thread", None):      # one read at a time
            if not quiet:
                self.toast("The bridge is already being read.", "warn")
            return

        if not quiet:
            self.toast("Reading the bridge…", "info")
        self.bridge_thread = QThread(self)
        self.bridge_worker = BridgeWorker(url)
        self.bridge_worker.moveToThread(self.bridge_thread)
        self.bridge_thread.started.connect(self.bridge_worker.run)
        self.bridge_worker.finished.connect(
            lambda replies, error: self.on_bridge_finished(replies, error,
                                                           quiet))
        self.bridge_thread.start()

    def on_bridge_finished(self, replies, error, quiet):
        thread = getattr(self, "bridge_thread", None)
        if thread:
            thread.quit()
            thread.wait(3000)
        self.bridge_thread = None
        self.bridge_worker = None

        if error:
            if not quiet:
                self.toast("Bridge: %s" % error, "err")
            return
        added, offered = self.merge_replies(replies)
        self.db["settings"]["bridge_last_sync"] = \
            datetime.now().isoformat(timespec="seconds")
        self.persist()
        self.refresh_bridge_note()
        self.refresh_bridge_status()
        # every reply that brought a PDF or a scan is now opened and read
        self.read_reply_documents(quiet=True)
        if quiet and not added:
            return
        self.toast("Bridge synced: %d new repl%s (%d already on record)."
                   % (added, "y" if added == 1 else "ies", offered - added),
                   "ok")

    def refresh_bridge_note(self):
        if not hasattr(self, "bridge_note"):
            return
        url = (self.db["settings"].get("bridge_feed_url") or "").strip()
        stamp = self.db["settings"].get("bridge_last_sync") or ""
        if not url:
            self.bridge_note.setText("Gmail bridge not connected")
        elif stamp:
            self.bridge_note.setText("Bridge last read %s" % stamp_text(stamp))
        else:
            self.bridge_note.setText("Bridge connected, not yet read")

    # ------------------------------------------- reading the reply's document
    def unread_document_replies(self, retry=False):
        """Replies of this engagement whose PDF or scan has not been read."""
        return [r for r in self.stored_replies()
                if reply_has_unread_files(r) and
                (retry or not r.get("files_error"))]

    def refresh_reader_note(self, text=None):
        if not hasattr(self, "reader_note"):
            return
        if text is None:
            ready, words = reader_status()
            waiting = len(self.unread_document_replies(retry=True))
            read = sum(1 for r in self.stored_replies() if r.get("files_read"))
            if ready:
                text = "%s. %d document%s read, %d waiting." % (
                    words, read, "" if read == 1 else "s", waiting)
            else:
                text = words
        self.reader_note.setText(text)

    def read_reply_documents(self, quiet=False, retry=False):
        """Open every unread PDF or scan and take the confirmed amount from
        it.  Runs after each sync, and on demand from the button."""
        if getattr(self, "reader_thread", None):
            if not quiet:
                self.toast("Documents are already being read.", "warn")
            return
        waiting = self.unread_document_replies(retry=retry)
        if not waiting:
            if not quiet:
                self.toast("No reply has a PDF or scan left to read.", "info")
            self.refresh_reader_note()
            return
        ready, words = reader_status()
        if not ready:
            self.refresh_reader_note(words)
            if not quiet:
                self.toast(words, "warn")
            return
        url = (self.db["settings"].get("bridge_feed_url") or "").strip()
        if not url.lower().startswith("https://"):
            if not quiet:
                self.toast("The documents are fetched through the Gmail "
                           "bridge, which is not connected. Use \"Add a reply "
                           "from a PDF or scan\" for a file you hold.", "warn")
            return
        self.btn_read_docs.setEnabled(False)
        self.refresh_reader_note("Reading %d document%s…" % (
            len(waiting), "" if len(waiting) == 1 else "s"))
        self.reader_thread = QThread(self)
        self.reader_worker = DocumentWorker(url, [r["id"] for r in waiting])
        self.reader_worker.moveToThread(self.reader_thread)
        self.reader_thread.started.connect(self.reader_worker.run)
        self.reader_worker.progress.connect(self.on_document_read)
        self.reader_worker.finished.connect(self.on_documents_finished)
        self.reader_thread.start()

    def store_reading(self, reply, entries, error=""):
        """Keep what was read with the reply it belongs to."""
        names = {entry["name"] for entry in entries}
        kept = [a for a in (reply.get("attachments") or [])
                if not (a.get("read_by") == "application" and
                        a.get("name") in names)]
        # what this computer read goes first: it is the fuller reading
        reply["attachments"] = [e for e in entries if e.get("text")] + kept
        problems = [e["name"] + ": " + e["error"] for e in entries
                    if e.get("error") and not e.get("text")]
        if error:
            problems.append(error)
        reply["files_error"] = "; ".join(problems)
        reply["files_read"] = any(e.get("text") for e in entries)
        reply["files_read_at"] = datetime.now().isoformat(timespec="seconds")

    def on_document_read(self, reply_id, entries, error, number, total):
        for reply in self.db.get("replies", []):
            if reply.get("id") == reply_id:
                self.store_reading(reply, entries, error)
                break
        self.refresh_reader_note("Read %d of %d…" % (number, total))

    def on_documents_finished(self, done, failed):
        thread = getattr(self, "reader_thread", None)
        if thread:
            thread.quit()
            thread.wait(5000)
        self.reader_thread = None
        self.reader_worker = None
        self.btn_read_docs.setEnabled(True)
        self.persist()
        self.refresh_recon()
        text = "%d document%s read" % (done, "" if done == 1 else "s")
        if failed:
            text += "; %d could not be read (see the exception queue)" % failed
        self.toast(text + ".", "warn" if failed else "ok")

    def add_reply_from_file(self, path=None):
        """A confirmation that did not come through the mailbox: the file is
        read here and matched to its party by reference code or name."""
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "The confirmation received", "",
                "PDFs and scans (*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp)")
        if not path:
            return None
        ready, words = reader_status()
        if not ready:
            self.toast(words, "warn")
            return None
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except Exception as exc:
            self.toast("The file could not be opened: %s" % exc, "err")
            return None
        name = os.path.basename(path)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            reading = read_document(data, name)
        finally:
            QApplication.restoreOverrideCursor()
        if not reading.get("text"):
            self.toast("Nothing could be read from %s: %s"
                       % (name, reading.get("error") or "no text found"), "err")
            return None
        client, year = self.active_client(), self.active_fy()
        reply = {
            "id": "file-" + new_id(),
            "received_at": date.today().isoformat(),
            "from_email": "", "from_name": "",
            "subject": "Received as a file: " + name,
            "body": "", "thread_id": "", "in_reply_to": "",
            "reference": find_reference(reading["text"]) or "",
            "bounced": False, "manual": True,
            "client_id": client["id"] if client else None,
            "fy_id": year["id"] if year else None,
            "files": [name], "files_read": True, "files_error": "",
            "attachments": [attachment_entry(name, reading)],
        }
        self.db.setdefault("replies", []).append(reply)
        self.persist()
        self.refresh_recon()
        row = next((r for r in self.recon_rows
                    if r.get("extract_source") == name or
                    (reply["reference"] and
                     r.get("reference") == reply["reference"] and
                     r.get("received_at"))), None)
        if row:
            self.toast("%s read (%s) and matched to %s: %s."
                       % (name, reading["method"], row["party_name"],
                          row["status"]), "ok")
        else:
            self.toast("%s was read but could not be matched to a party; it "
                       "is in the exception queue." % name, "warn")
        return reply

    # =====================================================================
    # PAGE 09 - SETTINGS
    # =====================================================================
    def _page_settings(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        top = QHBoxLayout()
        top.setSpacing(16)

        frame, body, _ = card("Engagement", "", light=True)
        body.addWidget(field_label("Active client", light=True))
        self.set_client = QComboBox()
        self.set_client.currentIndexChanged.connect(self.on_set_client)
        body.addWidget(self.set_client)
        body.addWidget(field_label("Financial year", light=True))
        self.set_fy = QComboBox()
        self.set_fy.currentIndexChanged.connect(self.on_set_fy)
        body.addWidget(self.set_fy)
        body.addWidget(h_line(light=True))

        body.addWidget(field_label("Type of audit", light=True))
        self.set_audit_type = QComboBox()
        for name in AUDIT_TYPE_ORDER:
            self.set_audit_type.addItem(
                "Other (describe below)" if name == "Other" else name, name)
        self.set_audit_type.currentIndexChanged.connect(self.on_audit_type)
        body.addWidget(self.set_audit_type)

        self.audit_other_box = pane()
        other_layout = QVBoxLayout(self.audit_other_box)
        other_layout.setContentsMargins(0, 0, 0, 0)
        other_layout.setSpacing(4)
        other_layout.addWidget(field_label("Describe the engagement",
                                           light=True))
        self.set_audit_other = QLineEdit()
        self.set_audit_other.setPlaceholderText(
            "agreed-upon procedures engagement")
        self.set_audit_other.textChanged.connect(self.on_audit_other)
        other_layout.addWidget(self.set_audit_other)
        self.audit_other_hint = QLabel("")
        self.audit_other_hint.setObjectName("HintLight")
        self.audit_other_hint.setWordWrap(True)
        other_layout.addWidget(self.audit_other_hint)
        self.audit_other_box.setVisible(False)
        body.addWidget(self.audit_other_box)

        body.addWidget(field_label("Confirmation is for", light=True))
        self.set_basis = QComboBox()
        self.set_basis.addItem("A financial year end", "year")
        self.set_basis.addItem("A period end (interim / stub period)", "period")
        self.set_basis.currentIndexChanged.connect(self.on_basis)
        body.addWidget(self.set_basis)

        self.year_end_box = pane()
        year_layout = QVBoxLayout(self.year_end_box)
        year_layout.setContentsMargins(0, 0, 0, 0)
        year_layout.setSpacing(4)
        year_layout.addWidget(field_label("Financial year end", light=True))
        self.set_year_end = QDateEdit()
        self.set_year_end.setCalendarPopup(True)
        self.set_year_end.setDisplayFormat("dd MMMM yyyy")
        self.set_year_end.dateChanged.connect(self.on_year_end)
        year_layout.addWidget(self.set_year_end)
        body.addWidget(self.year_end_box)

        self.period_box = pane()
        period_layout = QHBoxLayout(self.period_box)
        period_layout.setContentsMargins(0, 0, 0, 0)
        period_layout.setSpacing(10)
        start_col = QVBoxLayout()
        start_col.setSpacing(4)
        start_col.addWidget(field_label("Period from (optional)", light=True))
        start_row = QHBoxLayout()
        start_row.setSpacing(6)
        self.set_period_start = QDateEdit()
        self.set_period_start.setCalendarPopup(True)
        self.set_period_start.setDisplayFormat("dd MMMM yyyy")
        self.set_period_start.dateChanged.connect(self.on_period_start)
        clear_start = button("Clear", small=True)
        clear_start.clicked.connect(self.clear_period_start)
        start_row.addWidget(self.set_period_start, 1)
        start_row.addWidget(clear_start)
        start_col.addLayout(start_row)
        end_col = QVBoxLayout()
        end_col.setSpacing(4)
        end_col.addWidget(field_label("Period ended on", light=True))
        self.set_period_end = QDateEdit()
        self.set_period_end.setCalendarPopup(True)
        self.set_period_end.setDisplayFormat("dd MMMM yyyy")
        self.set_period_end.dateChanged.connect(self.on_period_end)
        end_col.addWidget(self.set_period_end)
        period_layout.addLayout(start_col, 1)
        period_layout.addLayout(end_col, 1)
        self.period_box.setVisible(False)
        body.addWidget(self.period_box)

        date_row = QHBoxLayout()
        date_row.setSpacing(10)
        date_col = QVBoxLayout()
        date_col.setSpacing(4)
        date_col.addWidget(field_label("Date printed on the letter", light=True))
        self.set_letter_date = QDateEdit()
        self.set_letter_date.setCalendarPopup(True)
        self.set_letter_date.setDisplayFormat("dd MMMM yyyy")
        self.set_letter_date.dateChanged.connect(self.on_letter_date)
        date_col.addWidget(self.set_letter_date)
        self.set_letterhead = QCheckBox(
            "Print \u201c(on the letter head of the Company)\u201d")
        self.set_letterhead.stateChanged.connect(self.on_letterhead)
        date_row.addLayout(date_col, 1)
        date_row.addWidget(self.set_letterhead, 1,
                           Qt.AlignmentFlag.AlignBottom)
        body.addLayout(date_row)

        self.engagement_echo = QLabel("")
        self.engagement_echo.setObjectName("HintLight")
        self.engagement_echo.setWordWrap(True)
        body.addWidget(self.engagement_echo)
        body.addWidget(h_line(light=True))

        signer_row = QHBoxLayout()
        signer_row.setSpacing(10)
        signer_col = QVBoxLayout()
        signer_col.setSpacing(4)
        signer_col.addWidget(field_label("Letter signed by (company officer)",
                                         light=True))
        self.set_signatory = QLineEdit()
        self.set_signatory.setPlaceholderText("Mr. R. Mehta")
        self.set_signatory.textChanged.connect(self.on_signatory)
        signer_col.addWidget(self.set_signatory)
        desig_col = QVBoxLayout()
        desig_col.setSpacing(4)
        desig_col.addWidget(field_label("Officer's designation", light=True))
        self.set_sig_designation = QLineEdit()
        self.set_sig_designation.setPlaceholderText("Director / CFO")
        self.set_sig_designation.textChanged.connect(self.on_signatory_designation)
        desig_col.addWidget(self.set_sig_designation)
        signer_row.addLayout(signer_col, 1)
        signer_row.addLayout(desig_col, 1)
        body.addLayout(signer_row)
        signer_hint = QLabel("The confirmation is issued by the client on its "
                             "own letterhead, so it is signed by the company, "
                             "not by the audit firm. Saved against this client.")
        signer_hint.setObjectName("HintLight")
        signer_hint.setWordWrap(True)
        body.addWidget(signer_hint)
        body.addWidget(h_line(light=True))

        body.addWidget(field_label("Audit firm name", light=True))
        self.set_firm = QLineEdit()
        self.set_firm.setPlaceholderText("Ankit Soni and Associates")
        self.set_firm.textChanged.connect(self.on_firm_changed)
        body.addWidget(self.set_firm)
        firm_hint = QLabel("Printed as the auditors the signed reply must be "
                           "sent to.")
        firm_hint.setObjectName("HintLight")
        firm_hint.setWordWrap(True)
        body.addWidget(firm_hint)
        body.addWidget(field_label("Engagement partner (optional)", light=True))
        self.set_partner = QLineEdit()
        self.set_partner.setPlaceholderText("CA Ankit Soni")
        self.set_partner.textChanged.connect(self.on_partner_changed)
        body.addWidget(self.set_partner)
        body.addWidget(field_label("Designation line (email sign-off)",
                                   light=True))
        self.set_designation = QLineEdit()
        self.set_designation.setPlaceholderText("Statutory Auditor")
        self.set_designation.textChanged.connect(self.on_designation_changed)
        body.addWidget(self.set_designation)
        designation_hint = QLabel("Follows the type of audit unless you type "
                                  "your own.")
        designation_hint.setObjectName("HintLight")
        body.addWidget(designation_hint)
        top.addWidget(frame, 1)

        frame2, body2, _ = card("Audit team",
                                "Replies are directed to these addresses",
                                light=True)
        team_form = QHBoxLayout()
        team_form.setSpacing(8)
        name_col = QVBoxLayout()
        name_col.setSpacing(4)
        name_col.addWidget(field_label("Name", light=True))
        self.aud_name = QLineEdit()
        self.aud_name.setPlaceholderText("M. A")
        name_col.addWidget(self.aud_name)
        email_col = QVBoxLayout()
        email_col.setSpacing(4)
        email_col.addWidget(field_label("Email address", light=True))
        self.aud_email = QLineEdit()
        self.aud_email.setPlaceholderText("a@example.com")
        self.aud_email.returnPressed.connect(self.add_auditor)
        email_col.addWidget(self.aud_email)
        team_form.addLayout(name_col, 1)
        team_form.addLayout(email_col, 1)
        body2.addLayout(team_form)
        add_member = button("+  Add member", "primary")
        add_member.clicked.connect(self.add_auditor)
        body2.addWidget(add_member, 0, Qt.AlignmentFlag.AlignLeft)
        team_hint = QLabel("At least one valid address is required before "
                           "letters can be generated.")
        team_hint.setObjectName("HintLight")
        team_hint.setWordWrap(True)
        body2.addWidget(team_hint)
        body2.addWidget(h_line(light=True))
        self.aud_table = table(["Name", "Email", "Status", ""],
                               stretch_column=1)
        self.aud_table.setMinimumHeight(220)
        body2.addWidget(self.aud_table)
        body2.addStretch(1)
        top.addWidget(frame2, 1)
        layout.addLayout(top)

        frameb, bodyb, headerb = card(
            "Gmail bridge",
            "Collects replies on Google's servers while this computer is off")
        self.bridge_status = QLabel("")
        self.bridge_status.setObjectName("HintDark")
        headerb.addWidget(self.bridge_status)
        sync_now = button("Sync now", "primary")
        sync_now.clicked.connect(lambda: self.sync_bridge())
        headerb.addWidget(sync_now)

        bodyb.addWidget(field_label("Feed address (the Apps Script web-app "
                                    "URL)"))
        self.bridge_url = QLineEdit()
        self.bridge_url.setPlaceholderText(
            "https://script.google.com/macros/s/…/exec")
        self.bridge_url.textChanged.connect(self.on_bridge_url)
        bodyb.addWidget(self.bridge_url)
        self.bridge_start = QCheckBox("Sync automatically when the "
                                      "application starts")
        self.bridge_start.stateChanged.connect(self.on_bridge_start)
        bodyb.addWidget(self.bridge_start)
        bridge_hint = QLabel(
            "Deploy the supplied Apps Script (balance-confirmation-bridge.gs) "
            "in your own Google account as a web app set to <b>Execute as: "
            "Me</b> and <b>Who has access: Only myself</b>, then paste the "
            "deployment URL here.  The script reads unread mail whose subject "
            "carries \"balance confirmation\", records the confirmed figures "
            "in a Google Sheet, and labels what it has processed.  Nothing "
            "leaves your own Google account, and no mail is ever deleted.")
        bridge_hint.setObjectName("HintDark")
        bridge_hint.setTextFormat(Qt.TextFormat.RichText)
        bridge_hint.setWordWrap(True)
        bodyb.addWidget(bridge_hint)
        layout.addWidget(frameb)

        frame3, body3, _ = card("Column mapping in force",
                                "Read-only summary of the current import")
        self.map_summary = QLabel("No import loaded.")
        self.map_summary.setObjectName("HintDark")
        self.map_summary.setTextFormat(Qt.TextFormat.RichText)
        self.map_summary.setWordWrap(True)
        body3.addWidget(self.map_summary)
        layout.addWidget(frame3)
        layout.addStretch(1)
        return page

    # ------------------------------------------------- settings handlers
    def _load_settings_into_widgets(self):
        self._building = True
        settings = self.db["settings"]
        self.set_firm.setText(settings.get("firm_name", ""))
        self.set_designation.setText(settings.get("firm_designation", ""))
        self.currency_edit.setText(settings.get("default_currency", "INR"))
        self.folder_edit.setText(settings.get("output_folder", ""))
        self.bridge_url.setText(settings.get("bridge_feed_url", ""))
        self.bridge_start.setChecked(
            bool(settings.get("bridge_sync_on_start", True)))
        self._building = False
        self.refresh_bridge_status()

    def refresh_bridge_status(self):
        if not hasattr(self, "bridge_status"):
            return
        settings = self.db["settings"]
        url = (settings.get("bridge_feed_url") or "").strip()
        stamp = settings.get("bridge_last_sync") or ""
        count = len(self.db.get("replies", []))
        if not url:
            self.bridge_status.setText("not connected")
        elif stamp:
            self.bridge_status.setText(
                "last read %s · %d repl%s on record"
                % (stamp_text(stamp), count, "y" if count == 1 else "ies"))
        else:
            self.bridge_status.setText("connected, not yet read")
        self.refresh_bridge_note()

    def on_bridge_url(self, text):
        if self._building:
            return
        self.db["settings"]["bridge_feed_url"] = text.strip()
        self.persist()
        self.refresh_bridge_status()

    def on_bridge_start(self, state):
        if self._building:
            return
        self.db["settings"]["bridge_sync_on_start"] = \
            self.bridge_start.isChecked()
        self.persist()

    def on_set_client(self, index):
        if self._building:
            return
        client_id = self.set_client.currentData()
        self.set_active_client(client_id)

    def on_set_fy(self, index):
        if self._building:
            return
        fy_id = self.set_fy.currentData()
        if fy_id:
            self.set_active_fy(fy_id)

    def on_audit_type(self, index):
        if self._building:
            return
        year = self.active_fy()
        if not year:
            return
        previous = fy_audit_type(year)
        year["audit_type"] = self.set_audit_type.currentData()
        self.db["settings"]["last_audit_type"] = year["audit_type"]
        # the signature line follows the engagement unless it was hand-edited
        current = self.db["settings"].get("firm_designation") or ""
        if not current or current == audit_designation(previous):
            self.db["settings"]["firm_designation"] = audit_designation(
                year["audit_type"])
        self.persist()
        self.refresh_all()
        self.refresh_settings()

    def on_audit_other(self, text):
        if self._building:
            return
        year = self.active_fy()
        if not year:
            return
        year["audit_type_other"] = text
        self.audit_other_hint.setText(
            'Written into the letter as "As part of the %s of [client]", so '
            "keep it lower case and in noun form."
            % audit_phrase("Other", text))
        self.persist()
        self.update_engagement_echo()
        self.refresh_chips()

    def on_basis(self, index):
        if self._building:
            return
        year = self.active_fy()
        if not year:
            return
        year["basis"] = self.set_basis.currentData()
        if year["basis"] == "period" and not year.get("period_end"):
            year["period_end"] = year.get("year_end", "")
        self.persist()
        self.refresh_all()
        self.refresh_settings()

    def on_year_end(self, qdate):
        if self._building:
            return
        year = self.active_fy()
        if not year:
            return
        year["year_end"] = qdate.toString("yyyy-MM-dd")
        self.persist()
        self.update_engagement_echo()
        self.refresh_chips()
        self.refresh_clients()

    def on_period_start(self, qdate):
        if self._building:
            return
        year = self.active_fy()
        if not year:
            return
        value = qdate.toString("yyyy-MM-dd")
        if year.get("period_end") and value > year["period_end"]:
            self.toast("The period cannot start after it ends.", "warn")
            return
        year["period_start"] = value
        self.persist()
        self.update_engagement_echo()
        self.refresh_chips()

    def clear_period_start(self):
        year = self.active_fy()
        if not year:
            return
        year["period_start"] = ""
        self.persist()
        self.refresh_settings()
        self.update_engagement_echo()

    def on_period_end(self, qdate):
        if self._building:
            return
        year = self.active_fy()
        if not year:
            return
        value = qdate.toString("yyyy-MM-dd")
        if year.get("period_start") and year["period_start"] > value:
            self.toast("The period cannot end before it starts.", "warn")
            return
        year["period_end"] = value
        self.persist()
        self.update_engagement_echo()
        self.refresh_chips()
        self.refresh_clients()

    def on_letter_date(self, qdate):
        if self._building:
            return
        self.db["settings"]["letter_date"] = qdate.toString("yyyy-MM-dd")
        self.persist()
        self.update_engagement_echo()
        if self.stack.currentIndex() == self.pages["preview"]:
            self.render_preview()

    def on_letterhead(self, _state):
        if self._building:
            return
        self.db["settings"]["letterhead_note"] = self.set_letterhead.isChecked()
        self.persist()
        if self.stack.currentIndex() == self.pages["preview"]:
            self.render_preview()

    def on_signatory(self, text):
        if self._building:
            return
        client = self.active_client()
        if not client:
            return
        client["signatory_name"] = text
        self.persist()
        self.refresh_chips()
        if self.stack.currentIndex() == self.pages["preview"]:
            self.render_preview()

    def on_signatory_designation(self, text):
        if self._building:
            return
        client = self.active_client()
        if not client:
            return
        client["signatory_designation"] = text
        self.persist()
        if self.stack.currentIndex() == self.pages["preview"]:
            self.render_preview()

    def on_partner_changed(self, text):
        if self._building:
            return
        self.db["settings"]["partner_name"] = text
        self.persist()
        if self.stack.currentIndex() == self.pages["preview"]:
            self.render_preview()

    def on_firm_changed(self, text):
        if self._building:
            return
        self.db["settings"]["firm_name"] = text
        self.persist()
        self.refresh_chips()

    def on_designation_changed(self, text):
        if self._building:
            return
        self.db["settings"]["firm_designation"] = text
        self.persist()

    def update_engagement_echo(self):
        year = self.active_fy()
        client = self.active_client()
        if not year:
            self.engagement_echo.setText("")
            return
        as_at = fy_as_at(year)
        span = period_phrase(year.get("basis"), as_at,
                             year.get("period_start"))
        self.engagement_echo.setText(
            'Letters will open “Our %s, %s, are engaged in %s of our '
            'financial statements…” and confirm balances as on %s. '
            "The responding party's own date field is always left blank."
            % (auditors_label(fy_audit_type(year)),
               self.db["settings"].get("firm_name") or "[firm]",
               engagement_phrase(fy_audit_type(year),
                                 year.get("audit_type_other")),
               fmt_date_long(as_at) if as_at else "— not set —"))

    def add_auditor(self):
        email = self.aud_email.text().strip()
        name = self.aud_name.text().strip()
        if not valid_email(email):
            self.toast("Enter a valid email address for the team member.",
                       "warn")
            self.aud_email.setFocus()
            return
        if not name:
            name = email.split("@")[0]
        team = self.db["settings"].setdefault("auditors", [])
        if any(a["email"].lower() == email.lower() for a in team):
            self.toast("That address is already on the team list.", "warn")
            return
        team.append({"id": new_id(), "name": name, "email": email})
        self.aud_name.clear()
        self.aud_email.clear()
        self.persist()
        self.refresh_all()
        self.refresh_settings()
        self.toast("Team member added.", "ok")

    def remove_auditor(self, member):
        self.db["settings"]["auditors"] = [
            a for a in self.db["settings"]["auditors"] if a["id"] != member["id"]]
        self.persist()
        self.refresh_all()
        self.refresh_settings()

    def refresh_settings(self):
        self._building = True
        self.set_client.clear()
        self.set_client.addItem("— select a client —", None)
        for client in self.db["clients"]:
            self.set_client.addItem(client["name"], client["id"])
        index = self.set_client.findData(self.active_client_id)
        self.set_client.setCurrentIndex(max(index, 0))

        client = self.active_client()
        self.set_fy.clear()
        if client and client["financial_years"]:
            for year in client["financial_years"]:
                self.set_fy.addItem(year["year"], year["id"])
            index = self.set_fy.findData(self.active_fy_id)
            self.set_fy.setCurrentIndex(max(index, 0))
        else:
            self.set_fy.addItem("— no financial year —", None)

        year = self.active_fy()
        enabled = year is not None
        index = self.set_audit_type.findData(fy_audit_type(year))
        self.set_audit_type.setCurrentIndex(max(index, 0))
        self.set_audit_type.setEnabled(enabled)
        is_other = fy_audit_type(year) == "Other"
        self.audit_other_box.setVisible(is_other)
        self.set_audit_other.setText((year or {}).get("audit_type_other", ""))
        self.audit_other_hint.setText(
            'Written into the letter as "As part of the %s of [client]", so '
            "keep it lower case and in noun form."
            % audit_phrase("Other", (year or {}).get("audit_type_other", "")))

        basis = "period" if (year and year.get("basis") == "period") else "year"
        self.set_basis.setCurrentIndex(self.set_basis.findData(basis))
        self.set_basis.setEnabled(enabled)
        self.year_end_box.setVisible(basis == "year")
        self.period_box.setVisible(basis == "period")

        today = QDate.currentDate()
        year_end = to_date((year or {}).get("year_end"))
        self.set_year_end.setDate(QDate(year_end.year, year_end.month,
                                        year_end.day) if year_end else today)
        self.set_year_end.setEnabled(enabled)
        start = to_date((year or {}).get("period_start"))
        self.set_period_start.setSpecialValueText("")
        self.set_period_start.setDate(QDate(start.year, start.month, start.day)
                                      if start else today)
        end = to_date((year or {}).get("period_end"))
        self.set_period_end.setDate(QDate(end.year, end.month, end.day)
                                    if end else today)
        self.set_period_start.setEnabled(enabled)
        self.set_period_end.setEnabled(enabled)
        self.update_engagement_echo()

        stamp = to_date(letter_date(self.db)) or date.today()
        self.set_letter_date.setDate(QDate(stamp.year, stamp.month, stamp.day))
        self.set_letterhead.setChecked(
            self.db["settings"].get("letterhead_note", True))
        self.set_signatory.setText(
            client.get("signatory_name", "") if client else "")
        self.set_sig_designation.setText(
            client.get("signatory_designation", "") if client else "")
        self.set_signatory.setEnabled(bool(client))
        self.set_sig_designation.setEnabled(bool(client))
        self.set_firm.setText(self.db["settings"].get("firm_name", ""))
        self.set_partner.setText(self.db["settings"].get("partner_name", ""))
        self.set_designation.setText(
            self.db["settings"].get("firm_designation", ""))
        self._building = False

        team = self.db["settings"].get("auditors", [])
        self.aud_table.setRowCount(0)
        for member in team:
            row = self.aud_table.rowCount()
            self.aud_table.insertRow(row)
            ok = valid_email(member["email"])
            self.aud_table.setItem(row, 0, cell(member["name"], bold=True))
            self.aud_table.setItem(row, 1, cell(member["email"]))
            self.aud_table.setItem(row, 2, cell("VALID" if ok else "INVALID",
                                                color=T["ok"] if ok
                                                else T["err"], bold=True))
            remove = button("Remove", "danger", small=True)
            remove.clicked.connect(lambda _, m=member: self.remove_auditor(m))
            holder = pane()
            box = QHBoxLayout(holder)
            box.setContentsMargins(4, 2, 4, 2)
            box.addWidget(remove)
            box.addStretch(1)
            self.aud_table.setCellWidget(row, 3, holder)
        self.aud_table.resizeColumnsToContents()
        fit_widget_columns(self.aud_table, [3])
        self.render_map_summary()

    def render_map_summary(self):
        if not self.mapping:
            self.map_summary.setText("No import loaded.")
            return
        rows = []
        for field in FIELD_ORDER:
            entry = self.mapping[field]
            labels = ", ".join(self.column_label(c) for c in entry["cols"]) \
                or "—"
            colour = {"detected": T["ok"], "review": T["warn"],
                      "missing": T["err"]}[entry["status"]]
            rows.append(
                "<tr><td style='padding:3px 16px 3px 0; color:%s'>%s</td>"
                "<td style='padding:3px 16px 3px 0'>%s</td>"
                "<td style='padding:3px 0; color:%s'>%s</td></tr>"
                % (T["text_mute"], entry["label"], labels, colour,
                   entry["status"].upper()))
        self.map_summary.setText("<table>%s</table>" % "".join(rows))

    # =====================================================================
    # GLOBAL REFRESH
    # =====================================================================
    def refresh_chips(self):
        client = self.active_client()
        year = self.active_fy()
        team = self.auditors()
        checks = self.validation()
        as_at = fy_as_at(year)
        audit = fy_audit_type(year)
        if audit == "Other":
            audit = (year or {}).get("audit_type_other") or "to be described"

        def paint(widget, text, kind):
            widget.setText(text)
            widget.setProperty("chip", kind)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        paint(self.chip_client,
              "Client:  %s" % (client["name"] if client else "not selected"),
              "green" if client else "warn")
        paint(self.chip_audit, "Audit:  %s" % (audit if year else "not set"),
              "blue" if fy_audit_ok(year) else "warn")
        paint(self.chip_date, "%s:  %s" % (fy_basis_label(year),
                                           fmt_date_long(as_at) if as_at
                                           else "not set"),
              "green" if as_at else "warn")
        paint(self.chip_team, "Team:  %d" % len(team),
              "green" if team else "warn")
        ready_mail, _ = self.mail_ready()
        paint(self.chip_mail, "Mailbox:  %s"
              % (self.mail_settings().get("username") or "not set up"
                 if ready_mail else "not set up"),
              "brass" if ready_mail else "neutral")
        paint(self.chip_status, "Status:  %s"
              % ("Ready to Generate" if checks["ready"]
                 else "%d item%s need attention"
                      % (len(checks["hard"]),
                         "" if len(checks["hard"]) == 1 else "s")),
              "green" if checks["ready"] else "warn")

        for row, key in self.nav_keys.items():
            item = self.nav.item(row)
            base = dict(NAV_ITEMS)
            label = [text for text, k in NAV_ITEMS if k == key][0]
            if key == "import" and self.records:
                label += "   (%d)" % len(self.records)
            elif key == "review" and self.flagged_count():
                label += "   (%d)" % self.flagged_count()
            elif key == "generate":
                done = len([g for g in self.generated if g["status"] == "ok"])
                if done:
                    label += "   (%d)" % done
            elif key == "email":
                pending = len([q for q in self.queue.values()
                               if q["status"] == "pending"])
                if pending:
                    label += "   (%d)" % pending
            item.setText(label)

    def refresh_all(self):
        self.refresh_clients()
        self.render_mapping()
        self.render_cat_stats()
        self.render_records()
        self.refresh_chips()
        current = self.stack.currentIndex()
        if current == self.pages["dashboard"]:
            self.refresh_dashboard()
        elif current == self.pages["preview"]:
            self.render_preview()
        elif current == self.pages["generate"]:
            self.refresh_generate()
        elif current == self.pages["email"]:
            self.refresh_email()
        elif current == self.pages["runs"]:
            self.refresh_runs()
        elif current == self.pages["settings"]:
            self.refresh_settings()

    def closeEvent(self, event):
        if self.gen_thread or self.send_thread:
            if not self.ask("Work in progress",
                            "Documents are still being produced or sent. "
                            "Close anyway?", "Close"):
                event.ignore()
                return
            for worker, thread in ((self.gen_worker, self.gen_thread),
                                   (self.send_worker, self.send_thread)):
                if worker:
                    worker.stop()
                if thread:
                    thread.quit()
                    thread.wait(3000)
        if getattr(self, "reader_thread", None):      # reading can be redone
            self.reader_worker.stop = True
            self.reader_thread.quit()
            self.reader_thread.wait(8000)
        if getattr(self, "bridge_thread", None):      # a read needs no asking
            self.bridge_thread.quit()
            self.bridge_thread.wait(3000)
        self.persist()
        event.accept()


# ---------------------------------------------------------------------------
# Drag-and-drop panel used on the Import page
# ---------------------------------------------------------------------------
class DropZone(QFrame):

    def __init__(self, on_file):
        super().__init__()
        self.on_file = on_file
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(132)
        self.repaint_frame(False)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        title = QLabel("Drop your balance schedule here")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label = title
        title.setStyleSheet("color:%s; font-size:16px;" % T["text"])
        subtitle = QLabel("or click to browse — .xlsx, .xls, .csv")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label = subtitle
        subtitle.setStyleSheet("color:%s; font-size:12px;" % T["text_mute"])
        browse = button("Choose file…", "brass")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(browse)
        row.addStretch(1)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(row)
        layout.addStretch(1)

    def repaint_frame(self, hot):
        if hasattr(self, "title_label"):
            self.title_label.setStyleSheet("color:%s; font-size:16px;" % T["text"])
            self.sub_label.setStyleSheet("color:%s; font-size:12px;" % T["text_mute"])
        # scoped by name: an unscoped QFrame rule would also box in the two
        # labels, a label being a frame itself
        self.setObjectName("DropZone")
        self.setStyleSheet(
            "#DropZone { border: 2px dashed %s; border-radius: 12px; "
            "background: %s; } #DropZone QLabel { border: 0; "
            "background: transparent; }"
            % (T["accent_hi"] if hot else T["line_soft"],
               T["panel_tint"] if hot else T["well"]))

    def _browse(self):
        window = self.window()
        if hasattr(window, "choose_file"):
            window.choose_file()

    def mousePressEvent(self, event):
        self._browse()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.repaint_frame(True)

    def dragLeaveEvent(self, event):
        self.repaint_frame(False)

    def dropEvent(self, event):
        self.repaint_frame(False)
        urls = event.mimeData().urls()
        if urls:
            self.on_file(urls[0].toLocalFile())
            event.acceptProposedAction()


# ===========================================================================
# SECTION 10 - START-UP
# ===========================================================================

def excepthook(kind, value, trace):
    """Never show a raw traceback to the user; log it to the console."""
    traceback.print_exception(kind, value, trace)
    try:
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Unexpected error")
        box.setText("Something went wrong and the action was stopped.")
        box.setInformativeText(str(value)[:400])
        box.setDetailedText("".join(traceback.format_exception(kind, value,
                                                               trace)))
        box.exec()
    except Exception:
        pass


def main():
    sys.excepthook = excepthook
    QApplication.setApplicationName(APP_NAME)
    QApplication.setOrganizationName("Balance Confirmation Generator")
    app = QApplication(sys.argv)
    # Fusion renders identically on Windows, macOS and Linux, so the window
    # looks the same wherever it is opened; the palette keeps the native
    # pieces (calendar pop-ups, menus) in step with the dark theme.
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(T["window"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(T["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(T["raised"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(T["surface"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(T["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(T["raised"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(T["text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(T["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(T["accent_text"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(T["raised"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(T["text"]))
    app.setPalette(palette)
    app.setStyleSheet(style_sheet())
    font = app.font()
    if os.name == "nt":
        font.setFamily("Segoe UI")
    elif sys.platform == "darwin":
        font.setFamily("Helvetica Neue")
    font.setPointSize(10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
