# -*- coding: utf-8 -*-
"""
File Manager  -  AI Document Organiser
--------------------------------------
Reads scanned bills / PDFs / images / Word files, finds the DATE, TITLE and
NAME (vendor or person) from inside each file, renames it like

        001_2025-04-15_Tax-Invoice_Acme-Traders.pdf
        002_2025-04-30_Bank-Statement_HDFC-Bank.pdf

and sorts the files into folders suggested by the built-in AI engine
(by document type, year and party).

Run directly from IDLE (F5).
- As a .py script  : missing libraries are installed automatically (once).
- As a frozen .exe : installation is skipped (everything is bundled).

OCR for scanned files needs the free Tesseract program installed on the PC
(see Help > OCR Help). Without it, text-based PDFs/Word files still work.
"""

# ----------------------------------------------------------------------------
# 1. BOOTSTRAP: auto-install required libraries (script mode only)
# ----------------------------------------------------------------------------
import sys
import os
import subprocess
import importlib.util

APP_NAME = "File Manager"
APP_VERSION = "1.0"


def _bootstrap():
    """Install missing libraries once. Skipped completely in a packaged .exe."""
    if getattr(sys, "frozen", False):
        return

    marker = os.path.join(os.path.expanduser("~"), ".file_manager_ai_ok")
    packages = [  # (module, pip package, required?)
        ("PyQt5", "PyQt5", True),
        ("pdfplumber", "pdfplumber", True),
        ("requests", "requests", True),
        ("PIL", "Pillow", False),
        ("pytesseract", "pytesseract", False),
    ]
    missing = [(m, p, r) for m, p, r in packages
               if importlib.util.find_spec(m) is None]

    if not missing:
        if not os.path.exists(marker):
            try:
                with open(marker, "w") as f:
                    f.write("ok")
            except OSError:
                pass
        return

    print("%s: installing required libraries (first run only)..." % APP_NAME)
    flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    all_ok = True
    for module, pkg, required in missing:
        cmd = [sys.executable, "-m", "pip", "install"]
        if not in_venv:
            cmd.append("--user")
        cmd.append(pkg)
        try:
            print("  Installing %s ..." % pkg)
            subprocess.check_call(cmd, creationflags=flags)
        except Exception as exc:
            print("  Could not install %s: %s" % (pkg, exc))
            if required:
                all_ok = False
    importlib.invalidate_caches()
    if all_ok:
        try:
            with open(marker, "w") as f:
                f.write("ok")
        except OSError:
            pass
    else:
        print("Some required libraries failed to install. Please run:\n"
              "  pip install PyQt5 pdfplumber requests Pillow pytesseract")


_bootstrap()

# ----------------------------------------------------------------------------
# 2. IMPORTS
# ----------------------------------------------------------------------------
import re
import csv
import json
import html
import shutil
import zipfile
import datetime as dt
import subprocess as _sp

import requests

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QProgressBar, QTextEdit, QFileDialog, QMessageBox,
    QCheckBox, QSpinBox, QGroupBox, QFrame, QAction, QComboBox
)

SUPPORTED_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp",
                 ".docx", ".txt"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
MAX_PAGES_READ = 2          # pages read per PDF (keeps things fast)
DEFAULT_MODEL = "claude-sonnet-5-5"

# Table columns
C_FILE, C_NEW, C_DATE, C_TYPE, C_PARTY, C_FOLDER, C_CONF, C_STATUS = range(8)

STRUCTURES = ["Type", "Type / Year", "Year / Type", "Party / Type", "Type / Party"]


# ----------------------------------------------------------------------------
# 3. KNOWLEDGE BASE FOR THE OFFLINE AI ENGINE
# ----------------------------------------------------------------------------
# (document type, folder name, {keyword: weight})
DOC_TYPES = [
    ("Tax Invoice", "Invoices", {
        "tax invoice": 5, "invoice no": 3, "invoice number": 3, "gstin": 2,
        "hsn": 2, "bill of supply": 3, "invoice date": 2, "sgst": 1,
        "cgst": 1, "igst": 1, "place of supply": 2, "invoice": 1}),
    ("Bank Statement", "Bank Statements", {
        "statement of account": 5, "account statement": 4, "opening balance": 3,
        "closing balance": 3, "ifsc": 2, "narration": 2, "withdrawal": 1,
        "deposit": 1, "cheque no": 1}),
    ("Receipt", "Receipts", {
        "payment receipt": 5, "receipt no": 4, "received with thanks": 5,
        "receipt": 2, "amount received": 3, "payment received": 3}),
    ("Utility Bill", "Bills", {
        "electricity bill": 5, "water bill": 4, "telephone bill": 4,
        "mobile bill": 3, "broadband": 2, "bill date": 2, "units consumed": 3,
        "consumer no": 2, "bill no": 2}),
    ("Purchase Order", "Purchase Orders", {
        "purchase order": 6, "po no": 3, "po number": 3, "delivery date": 1}),
    ("Quotation", "Quotations", {
        "quotation": 5, "proforma invoice": 5, "estimate": 2, "quote no": 3,
        "valid until": 1}),
    ("Agreement", "Agreements", {
        "this agreement": 5, "agreement": 3, "hereinafter": 3, "witnesseth": 4,
        "deed": 3, "memorandum of understanding": 4, "terms and conditions": 1}),
    ("Notice", "Notices", {
        "show cause notice": 6, "demand notice": 5, "notice under section": 5,
        "notice": 2, "intimation": 3, "scrutiny": 3, "reply within": 2,
        "income tax department": 2, "gst department": 2}),
    ("Tax Return", "Tax Returns", {
        "income tax return": 5, "itr-": 4, "acknowledgement number": 4,
        "gstr-": 4, "gstr1": 4, "gstr3b": 4, "return filed": 3,
        "assessment year": 3, "form 26as": 3, "annual information statement": 4}),
    ("TDS Certificate", "TDS Certificates", {
        "form 16": 5, "form 16a": 5, "tds certificate": 5,
        "certificate under section 203": 6, "tan of deductor": 3}),
    ("Salary Slip", "Salary Slips", {
        "salary slip": 6, "payslip": 6, "pay slip": 6, "net pay": 3,
        "basic salary": 3, "employee id": 2, "earnings": 1, "deductions": 1}),
    ("Financial Statement", "Financial Statements", {
        "balance sheet": 5, "profit and loss": 5, "profit & loss": 5,
        "trial balance": 5, "cash flow statement": 4, "schedule iii": 3}),
    ("Identity Proof", "ID Proofs", {
        "aadhaar": 5, "unique identification authority": 5,
        "permanent account number": 5, "passport": 4, "driving licence": 4,
        "election commission": 3}),
    ("Insurance", "Insurance", {
        "policy number": 4, "insurance": 3, "sum assured": 4, "premium": 3,
        "policy schedule": 4}),
    ("Loan Document", "Loans", {
        "loan account": 4, "sanction letter": 5, "loan agreement": 5, "emi": 3,
        "repayment schedule": 4, "amortization": 3}),
    ("Certificate", "Certificates", {
        "this is to certify": 5, "hereby certify": 4, "certificate of": 3,
        "certificate": 2}),
    ("Letter", "Letters", {
        "dear sir": 3, "dear madam": 3, "yours faithfully": 4,
        "yours sincerely": 4, "subject:": 2}),
    ("Resume", "Resumes", {
        "curriculum vitae": 5, "resume": 4, "work experience": 3,
        "objective": 1}),
    ("Report", "Reports", {
        "audit report": 5, "independent auditor": 5, "executive summary": 4,
        "annual report": 4, "report": 1}),
]
TYPE_FOLDER = {name: folder for name, folder, _ in DOC_TYPES}
PERSONAL_TYPES = {"Salary Slip", "Identity Proof", "Resume", "Certificate",
                  "Tax Return"}

KNOWN_BANKS = [
    ("state bank of india", "SBI"), ("hdfc bank", "HDFC Bank"),
    ("icici bank", "ICICI Bank"), ("axis bank", "Axis Bank"),
    ("kotak mahindra", "Kotak Bank"), ("punjab national bank", "PNB"),
    ("bank of baroda", "Bank of Baroda"), ("canara bank", "Canara Bank"),
    ("union bank", "Union Bank"), ("idfc first", "IDFC First Bank"),
    ("yes bank", "Yes Bank"), ("indusind bank", "IndusInd Bank"),
    ("central bank of india", "Central Bank"), ("bank of india", "Bank of India"),
    ("indian bank", "Indian Bank"), ("federal bank", "Federal Bank"),
    ("bandhan bank", "Bandhan Bank"), ("idbi bank", "IDBI Bank"),
]

COMPANY_RE = re.compile(
    r"(?:\b(?:pvt\.?\s*ltd\.?|private\s+limited|limited|ltd\.?|llp|inc\.?|"
    r"corporation|corp\.?|traders?|enterprises?|industries|associates|company|"
    r"stores?|agenc(?:y|ies)|services|solutions|technologies|motors|"
    r"electricals?|hospital|school|college|university|bank|mart|textiles?|"
    r"pharma(?:cy)?|foods?|hotel|restaurant|infra|constructions?)\b)|(?:&\s*co\b)",
    re.I)
SELLER_RE = re.compile(
    r"(?:sold by|billed by|seller|supplier|vendor|issued by|company name|"
    r"name of (?:the )?(?:firm|company|organi[sz]ation))\s*[:\-]\s*(.+)", re.I)
PERSON_RE = re.compile(
    r"(?:employee name|name of (?:the )?(?:employee|assessee|candidate|holder|"
    r"deductee)|assessee name|candidate name|holder name|^name)\s*[:\-]\s*"
    r"([A-Za-z][A-Za-z .']{2,40})", re.I)
BAD_NAME_WORDS = ("invoice", "receipt", "statement", "original", "duplicate",
                  "page ", "gstin", "phone", "email", "e-mail", "www.", "http",
                  "date", "tel:", "mobile", "pan no", "authorised",
                  "signature", "bill to", "ship to", "customer copy")
TITLE_WORDS = re.compile(
    r"\b(invoice|statement|receipt|certificate|agreement|notice|report|bill|"
    r"letter|quotation|order|return|deed|policy|slip|challan|voucher|"
    r"acknowledg(?:e)?ment|form)\b", re.I)
TITLE_REJECT = re.compile(r"\b(no|number|date|dated|total|amount)\b", re.I)

MONTH_NAMES = {}
for _i, _m in enumerate(["january", "february", "march", "april", "may", "june",
                         "july", "august", "september", "october", "november",
                         "december"], 1):
    MONTH_NAMES[_m] = _i
    MONTH_NAMES[_m[:3]] = _i
MONTH_NAMES["sept"] = 9

RE_DMY = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4}|\d{2})\b")
RE_YMD = re.compile(r"\b(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})\b")
RE_DMON = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?[\s\-,/.]+([A-Za-z]{3,9})[\s\-,/.]+(\d{4}|\d{2})\b")
RE_MONDY = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b")
DATE_KEYS = ("invoice date", "bill date", "date of issue", "statement date",
             "receipt date", "dated", "date:", "date of invoice", "issue date",
             "date ", "dt.")


# ----------------------------------------------------------------------------
# 4. HELPER FUNCTIONS
# ----------------------------------------------------------------------------
def open_path(path):
    """Open a file or folder with the default program."""
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        _sp.Popen(["open", path])
    else:
        _sp.Popen(["xdg-open", path])


def clean_part(text, maxlen=40):
    """Make a safe piece of a file name (spaces become hyphens)."""
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", text or "")
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-{2,}", "-", text).strip("-._ ")
    return (text[:maxlen].strip("-._ ")) or "Unknown"


def clean_folder(text):
    """Make a safe folder name (spaces kept)."""
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", text or "")
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text[:50] or "Misc"


def clean_filename(name, ext):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name or "").strip(" .")
    if not name:
        name = "document"
    if ext and not name.lower().endswith(ext.lower()):
        name += ext
    return name[:200]


def unique_path(folder, name):
    base, ext = os.path.splitext(name)
    candidate = os.path.join(folder, name)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(folder, "%s (%d)%s" % (base, counter, ext))
        counter += 1
    return candidate


def natural_key(path):
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", path)]


def collect_files(src, out, recursive):
    """List supported files in src (skipping the output folder)."""
    out_abs = os.path.abspath(out)
    found = []
    if recursive:
        for root, dirs, names in os.walk(src):
            dirs[:] = [d for d in dirs
                       if os.path.abspath(os.path.join(root, d)) != out_abs]
            for n in names:
                found.append(os.path.join(root, n))
    else:
        for n in os.listdir(src):
            p = os.path.join(src, n)
            if os.path.isfile(p):
                found.append(p)
    result = []
    for p in found:
        n = os.path.basename(p)
        if n.startswith(("~$", ".")):
            continue
        if os.path.splitext(n)[1].lower() in SUPPORTED_EXT:
            result.append(p)
    result.sort(key=natural_key)
    return result


# ---- OCR setup -------------------------------------------------------------
def setup_ocr():
    """Return True if pytesseract + the Tesseract program are usable."""
    try:
        import pytesseract
        from PIL import Image  # noqa: F401
    except Exception:
        return False
    candidates = [
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs",
                     "Tesseract-OCR", "tesseract.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            pytesseract.pytesseract.tesseract_cmd = c
            try:
                pytesseract.get_tesseract_version()
                return True
            except Exception:
                continue
    return False


# ---- Text extraction -------------------------------------------------------
def extract_text(path, ocr_ok):
    """Return (text, note) for a file. Never raises."""
    ext = os.path.splitext(path)[1].lower()
    text, note = "", ""
    try:
        if ext == ".pdf":
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                pages = pdf.pages[:MAX_PAGES_READ]
                for p in pages:
                    text += (p.extract_text() or "") + "\n"
                if len(text.strip()) < 30 and ocr_ok and pages:
                    import pytesseract
                    ocr_text = ""
                    for p in pages:
                        img = p.to_image(resolution=200).original
                        ocr_text += pytesseract.image_to_string(img, timeout=60) + "\n"
                    text, note = ocr_text, "OCR"
        elif ext in IMAGE_EXT:
            if ocr_ok:
                import pytesseract
                from PIL import Image
                with Image.open(path) as im:
                    text = pytesseract.image_to_string(im, timeout=60)
                note = "OCR"
            else:
                note = "Image needs OCR (Tesseract not found)"
        elif ext == ".docx":
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml").decode("utf-8", "ignore")
            xml = re.sub(r"</w:p>", "\n", xml)
            text = html.unescape(re.sub(r"<[^>]+>", "", xml))
        elif ext == ".txt":
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read(6000)
    except Exception as exc:
        note = "Read error: %s" % str(exc)[:80]
    return text, note


# ---- Date detection --------------------------------------------------------
def _mk_date(y, m, d):
    try:
        y, m, d = int(y), int(m), int(d)
        if y < 100:
            y += 2000
        if not (1990 <= y <= dt.date.today().year + 1):
            return None
        return dt.date(y, m, d)
    except (ValueError, TypeError):
        return None


def _month_num(name):
    return MONTH_NAMES.get(name.lower().rstrip("."))


def _parse_match(m, kind):
    g = m.groups()
    if kind == "dmy":
        d, mo = int(g[0]), int(g[1])
        if mo > 12 and d <= 12:
            d, mo = mo, d
        return _mk_date(g[2], mo, d)
    if kind == "ymd":
        return _mk_date(g[0], g[1], g[2])
    if kind == "dmon":
        mo = _month_num(g[1])
        return _mk_date(g[2], mo, g[0]) if mo else None
    if kind == "mondy":
        mo = _month_num(g[0])
        return _mk_date(g[2], mo, g[1]) if mo else None
    return None


def find_date(text):
    """Pick the most likely document date (prefers 'Invoice Date', etc.)."""
    cands = []
    for rx, kind in ((RE_DMY, "dmy"), (RE_YMD, "ymd"),
                     (RE_DMON, "dmon"), (RE_MONDY, "mondy")):
        for m in rx.finditer(text):
            d = _parse_match(m, kind)
            if d:
                cands.append((m.start(), d))
    if not cands:
        return None
    best = None
    for pos, d in cands:
        ctx = text[max(0, pos - 35):pos].lower()
        if any(k in ctx for k in ("due", "valid", "expir", "period", "birth", "dob")):
            score = -2
        elif any(k in ctx for k in DATE_KEYS):
            score = 2
        elif "date" in ctx:
            score = 1
        else:
            score = 0
        key = (score, -pos)
        if best is None or key > best[0]:
            best = (key, d)
    return best[1]


# ---- Name / title detection ------------------------------------------------
def _clean_name(s):
    s = re.split(r"\s{2,}|\||\bgstin|\bpan\s*(?:no|:)|\bcin\b|\bph(?:one)?\s*[:.]|\btel\s*[:.]",
                 s, flags=re.I)[0]
    s = re.sub(r"[^\w&.,'()\- ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" ,.-")
    if s.isupper():
        s = s.title()
    return s[:40].strip()


def _valid_name(s):
    s = s.strip()
    if not (3 <= len(s) <= 70):
        return False
    letters = sum(c.isalpha() for c in s)
    if letters < 3 or letters < 0.6 * len(s.replace(" ", "")):
        return False
    low = s.lower()
    return not any(w in low for w in BAD_NAME_WORDS)


def find_party(text, dtype):
    low = text.lower()
    if dtype == "Bank Statement":
        for key, label in KNOWN_BANKS:
            if key in low:
                return label
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    top = lines[:40]
    if dtype in PERSONAL_TYPES:
        for line in top:
            m = PERSON_RE.search(line)
            if m:
                n = _clean_name(m.group(1))
                if _valid_name(n):
                    return n
    for line in top:
        m = SELLER_RE.search(line)
        if m:
            n = _clean_name(m.group(1))
            if _valid_name(n):
                return n
    for line in top[:15]:
        if COMPANY_RE.search(line):
            n = _clean_name(line)
            if _valid_name(n):
                return n
    for line in top[:10]:
        n = _clean_name(line)
        if _valid_name(n) and len(n) >= 4:
            return n
    return ""


def find_title(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines[:15]:
        if (len(line) <= 45 and 1 <= len(line.split()) <= 5
                and not re.search(r"[\d:@/]", line)
                and TITLE_WORDS.search(line)
                and not TITLE_REJECT.search(line)):
            t = re.sub(r"[^A-Za-z &\-]", " ", line)
            t = re.sub(r"\s+", " ", t).strip()
            if t:
                return t.title()
    return ""


def classify(text):
    """Return (type name, folder, score) using weighted keyword matching."""
    low = text.lower()
    head = low[:600]
    best = ("Document", "Needs Review", 0.0)
    for name, folder, kws in DOC_TYPES:
        score = 0.0
        for kw, w in kws.items():
            if kw in head:
                score += w * 1.5
            elif kw in low:
                score += w
        if score > best[2]:
            best = (name, folder, score)
    if best[2] < 3:
        return ("Document", "Needs Review", best[2])
    return best


# ---- Optional online AI (Claude) -------------------------------------------
def ask_claude(text, api_key, model):
    types = ", ".join(t[0] for t in DOC_TYPES)
    prompt = (
        "You are a filing assistant for an Indian chartered accountant. "
        "Read the document text and reply with ONLY a JSON object with keys: "
        "\"doc_type\" (choose one of: %s - or invent a short category name if "
        "none fits), \"title\" (the document's own title, max 5 words), "
        "\"party\" (vendor/issuer name for business documents, or the person's "
        "name for personal documents, max 5 words), \"date\" (main document "
        "date as YYYY-MM-DD, or null). Dates in the text are usually "
        "day/month/year (Indian format).\n\nDOCUMENT TEXT:\n%s"
        % (types, text[:3500]))
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key,
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": model, "max_tokens": 300,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=60)
    resp.raise_for_status()
    data = resp.json()
    out = "".join(b.get("text", "") for b in data.get("content", [])
                  if b.get("type") == "text")
    s, e = out.find("{"), out.rfind("}")
    if s < 0 or e < 0:
        raise ValueError("AI reply was not JSON")
    return json.loads(out[s:e + 1])


# ---- Analyse one file ------------------------------------------------------
def blank_result(path):
    stem, ext = os.path.splitext(os.path.basename(path))
    return {"path": path, "stem": stem, "ext": ext.lower(), "date": None,
            "type": "Document", "title": stem, "party": "",
            "folder": "Needs Review", "confidence": 0, "note": "",
            "ai_failed": False}


def analyze_file(path, ocr_ok, ai_cfg):
    res = blank_result(path)
    text, note = extract_text(path, ocr_ok)
    res["note"] = note
    if not text.strip():
        res["note"] = note or "No readable text found"
        return res

    dtype, folder, score = classify(text)
    res["type"], res["folder"] = dtype, folder
    res["date"] = find_date(text)
    res["party"] = find_party(text, dtype)
    title = find_title(text)
    if title:
        res["title"] = title
    elif dtype != "Document":
        res["title"] = dtype

    conf = min(60, int(score * 5))
    if res["date"]:
        conf += 20
    if res["party"]:
        conf += 19
    res["confidence"] = min(99, conf)

    if ai_cfg:
        try:
            ai = ask_claude(text, ai_cfg["key"], ai_cfg["model"])
            try:
                d = dt.datetime.strptime(str(ai.get("date")), "%Y-%m-%d").date()
                if 1990 <= d.year <= dt.date.today().year + 1:
                    res["date"] = d
            except (ValueError, TypeError):
                pass
            if ai.get("title"):
                res["title"] = str(ai["title"])[:50]
            if ai.get("party"):
                res["party"] = str(ai["party"])[:50]
            t = ai.get("doc_type")
            if t:
                t = str(t).strip()[:40]
                res["type"] = t
                res["folder"] = TYPE_FOLDER.get(t, clean_folder(t))
            res["confidence"] = max(res["confidence"], 85)
            res["note"] = (res["note"] + " AI").strip()
        except Exception as exc:
            res["ai_failed"] = True
            res["note"] = (res["note"] + " AI failed: %s" % str(exc)[:60]).strip()
    return res


# ----------------------------------------------------------------------------
# 5. WORKER THREADS
# ----------------------------------------------------------------------------
class AnalyzeWorker(QThread):
    result = pyqtSignal(dict)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished_scan = pyqtSignal(bool)

    def __init__(self, files, ocr_ok, ai_cfg, parent=None):
        super().__init__(parent)
        self.files = files
        self.ocr_ok = ocr_ok
        self.ai_cfg = ai_cfg
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        total = len(self.files)
        ai_errors = 0
        for i, path in enumerate(self.files):
            if self._cancel:
                break
            self.log.emit("Reading: %s" % os.path.basename(path))
            try:
                res = analyze_file(path, self.ocr_ok, self.ai_cfg)
            except Exception as exc:
                res = blank_result(path)
                res["note"] = "Error: %s" % str(exc)[:80]
                self.log.emit("  Error: %s" % exc)
            if res.get("ai_failed"):
                ai_errors += 1
                if ai_errors >= 3 and self.ai_cfg:
                    self.ai_cfg = None
                    self.log.emit("Online AI failed 3 times - switching to the "
                                  "offline engine for the remaining files.")
            self.result.emit(res)
            self.progress.emit(int((i + 1) * 100 / total))
        self.finished_scan.emit(self._cancel)


class ApplyWorker(QThread):
    status = pyqtSignal(int, str)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished_apply = pyqtSignal(int, int, list, bool)  # ok, failed, actions, cancelled

    def __init__(self, items, move, parent=None):
        super().__init__(parent)
        self.items = items      # dicts: row, src, dest_dir, name
        self.move = move
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        ok = failed = 0
        actions = []
        cancelled = False
        total = len(self.items)
        for i, it in enumerate(self.items):
            if self._cancel:
                cancelled = True
                break
            try:
                os.makedirs(it["dest_dir"], exist_ok=True)
                dest = unique_path(it["dest_dir"], it["name"])
                if os.path.abspath(dest) == os.path.abspath(it["src"]):
                    self.status.emit(it["row"], "Skipped")
                    continue
                if self.move:
                    shutil.move(it["src"], dest)
                else:
                    shutil.copy2(it["src"], dest)
                actions.append((it["row"], it["src"], dest))
                self.status.emit(it["row"], "Moved" if self.move else "Copied")
                self.log.emit("  %s -> %s" % (os.path.basename(it["src"]), dest))
                ok += 1
            except Exception as exc:
                self.status.emit(it["row"], "Failed")
                self.log.emit("  FAILED %s: %s" % (os.path.basename(it["src"]), exc))
                failed += 1
            self.progress.emit(int((i + 1) * 100 / total))
        self.finished_apply.emit(ok, failed, actions, cancelled)


# ----------------------------------------------------------------------------
# 6. STYLESHEET  (white / blue / red)
# ----------------------------------------------------------------------------
STYLE = """
QMainWindow, QWidget#central { background-color: #FFFFFF; }
QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: #1B2A41; }

QLabel#header {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0A3D91, stop:1 #1E7BFF);
    color: #FFFFFF; font-size: 22pt; font-weight: bold; padding: 14px 20px;
}
QLabel#tagline { background: #0A3D91; color: #DCEBFF; padding: 4px 22px 10px 22px; }
QFrame#redline { background-color: #E02424; min-height: 4px; max-height: 4px; }

QGroupBox {
    border: 2px solid #1E7BFF; border-radius: 8px; margin-top: 12px;
    padding: 10px; font-weight: bold; background: #FFFFFF;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #0A3D91; }

QLineEdit, QSpinBox, QComboBox {
    border: 2px solid #B9D3FF; border-radius: 6px; padding: 5px; background: #FFFFFF;
    selection-background-color: #1E7BFF;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 2px solid #1E7BFF; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled { background: #F2F4F8; color: #9AA5B5; }

QPushButton {
    background-color: #1E7BFF; color: #FFFFFF; border: none; border-radius: 8px;
    padding: 8px 16px; font-weight: bold;
}
QPushButton:hover { background-color: #0A5FD6; }
QPushButton:pressed { background-color: #0A3D91; }
QPushButton:disabled { background-color: #C9D6EA; color: #8895AA; }

QPushButton#redBtn { background-color: #E02424; }
QPushButton#redBtn:hover { background-color: #B91818; }
QPushButton#redBtn:pressed { background-color: #8F1010; }
QPushButton#redBtn:disabled { background-color: #EBCFCF; color: #A08888; }

QPushButton#lightBtn { background-color: #EAF2FF; color: #0A3D91; border: 2px solid #1E7BFF; }
QPushButton#lightBtn:hover { background-color: #D3E5FF; }
QPushButton#lightBtn:disabled { background-color: #F2F4F8; color: #9AA5B5; border: 2px solid #D5DCE8; }

QTableWidget {
    border: 2px solid #1E7BFF; border-radius: 6px; gridline-color: #E3ECFB;
    alternate-background-color: #F4F8FF; background: #FFFFFF;
    selection-background-color: #BBD6FF; selection-color: #0A2A66;
}
QHeaderView::section {
    background-color: #0A3D91; color: #FFFFFF; padding: 6px; border: none;
    border-right: 1px solid #1E7BFF; font-weight: bold;
}
QProgressBar {
    border: 2px solid #1E7BFF; border-radius: 8px; text-align: center;
    background: #FFFFFF; height: 20px; font-weight: bold;
}
QProgressBar::chunk { background-color: #1E7BFF; border-radius: 6px; }
QTextEdit {
    border: 2px solid #B9D3FF; border-radius: 6px; background: #FAFCFF;
    font-family: Consolas, 'Courier New', monospace; font-size: 9pt;
}
QStatusBar { background: #0A3D91; color: #FFFFFF; }
QCheckBox { spacing: 6px; }
"""


# ----------------------------------------------------------------------------
# 7. MAIN WINDOW
# ----------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("FileManagerAI", "FileManagerAI")
        self.ocr_ok = setup_ocr()
        self.analyze_worker = None
        self.apply_worker = None
        self.results = []
        self.last_actions = []
        self.last_move = False
        self.last_out = ""

        self.setWindowTitle(APP_NAME)
        self.resize(1250, 840)
        self._build_menu()
        self._build_ui()
        self.setStyleSheet(STYLE)
        self._load_settings()
        self.statusBar().showMessage(
            "Ready  |  OCR for scanned files: %s"
            % ("available" if self.ocr_ok else "not available (see Help > OCR Help)"))

    # ------------------------------------------------------------------ UI --
    def _build_menu(self):
        menu = self.menuBar().addMenu("&Help")
        a1 = QAction("&OCR Help", self)
        a1.triggered.connect(self.show_ocr_help)
        a2 = QAction("&About", self)
        a2.triggered.connect(self.show_about)
        menu.addAction(a1)
        menu.addAction(a2)

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QLabel(APP_NAME)
        header.setObjectName("header")
        tagline = QLabel("AI document organiser: reads your bills and PDFs, "
                         "renames them by date, title and name, and files them in the right folders")
        tagline.setObjectName("tagline")
        redline = QFrame()
        redline.setObjectName("redline")
        root.addWidget(header)
        root.addWidget(tagline)
        root.addWidget(redline)

        body = QVBoxLayout()
        body.setContentsMargins(16, 8, 16, 8)
        body.setSpacing(6)
        root.addLayout(body)

        # --- 1. Folders
        fbox = QGroupBox("1. Folders")
        fl = QVBoxLayout(fbox)
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Source folder (files to organise):"))
        self.src_edit = QLineEdit()
        self.src_edit.setReadOnly(True)
        self.src_btn = QPushButton("Browse...")
        self.src_btn.clicked.connect(self.browse_source)
        self.sub_check = QCheckBox("Include subfolders")
        r1.addWidget(self.src_edit, 1)
        r1.addWidget(self.src_btn)
        r1.addWidget(self.sub_check)
        fl.addLayout(r1)
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Output folder (organised files):"))
        self.out_edit = QLineEdit()
        self.out_edit.setReadOnly(True)
        self.out_btn = QPushButton("Browse...")
        self.out_btn.clicked.connect(self.browse_output)
        self.open_btn = QPushButton("Open Folder")
        self.open_btn.setObjectName("lightBtn")
        self.open_btn.clicked.connect(self.open_output)
        r2.addWidget(self.out_edit, 1)
        r2.addWidget(self.out_btn)
        r2.addWidget(self.open_btn)
        fl.addLayout(r2)
        body.addWidget(fbox)

        # --- 2. Options
        obox = QGroupBox("2. Options")
        ol = QVBoxLayout(obox)
        o1 = QHBoxLayout()
        o1.addWidget(QLabel("Folder structure:"))
        self.struct_combo = QComboBox()
        self.struct_combo.addItems(STRUCTURES)
        o1.addWidget(self.struct_combo)
        o1.addWidget(QLabel("Action:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Copy files (originals kept)", "Move files"])
        o1.addWidget(self.mode_combo)
        o1.addWidget(QLabel("Start numbering at:"))
        self.start_spin = QSpinBox()
        self.start_spin.setRange(1, 99999)
        self.start_spin.setValue(1)
        o1.addWidget(self.start_spin)
        self.chrono_check = QCheckBox("Number by document date")
        o1.addWidget(self.chrono_check)
        o1.addStretch(1)
        ol.addLayout(o1)

        o2 = QHBoxLayout()
        self.ocr_check = QCheckBox("Read scanned files with OCR")
        self.ocr_check.setChecked(self.ocr_ok)
        self.ocr_check.setEnabled(self.ocr_ok)
        if not self.ocr_ok:
            self.ocr_check.setToolTip("Tesseract not found. See Help > OCR Help.")
        o2.addWidget(self.ocr_check)
        o2.addWidget(QLabel("AI engine:"))
        self.ai_combo = QComboBox()
        self.ai_combo.addItems(["Smart Offline AI (private)",
                                "Claude AI Online (needs API key)"])
        self.ai_combo.currentIndexChanged.connect(self._ai_changed)
        o2.addWidget(self.ai_combo)
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("API key (not saved)")
        o2.addWidget(self.key_edit, 1)
        self.model_edit = QLineEdit(DEFAULT_MODEL)
        self.model_edit.setMaximumWidth(180)
        o2.addWidget(self.model_edit)
        ol.addLayout(o2)
        body.addWidget(obox)

        # --- 3. Preview
        pbox = QGroupBox("3. Preview and edit (double-click 'New Name' or 'Folder' to change)")
        pl = QVBoxLayout(pbox)
        tools = QHBoxLayout()
        self.analyze_btn = QPushButton("Analyze Files")
        self.analyze_btn.clicked.connect(self.start_analyze)
        self.refresh_btn = QPushButton("Refresh Names")
        self.refresh_btn.setObjectName("lightBtn")
        self.refresh_btn.setToolTip("Re-apply numbering and folder structure (overwrites manual edits).")
        self.refresh_btn.clicked.connect(self.refresh_names)
        self.sel_all_btn = QPushButton("Select All")
        self.sel_all_btn.setObjectName("lightBtn")
        self.sel_all_btn.clicked.connect(lambda: self.set_all_checked(True))
        self.sel_none_btn = QPushButton("Deselect All")
        self.sel_none_btn.setObjectName("lightBtn")
        self.sel_none_btn.clicked.connect(lambda: self.set_all_checked(False))
        self.view_btn = QPushButton("Open Selected File")
        self.view_btn.setObjectName("lightBtn")
        self.view_btn.clicked.connect(self.open_selected)
        self.export_btn = QPushButton("Export Plan (CSV)")
        self.export_btn.setObjectName("lightBtn")
        self.export_btn.clicked.connect(self.export_plan)
        tools.addWidget(self.analyze_btn)
        tools.addWidget(self.refresh_btn)
        tools.addStretch(1)
        tools.addWidget(self.sel_all_btn)
        tools.addWidget(self.sel_none_btn)
        tools.addWidget(self.view_btn)
        tools.addWidget(self.export_btn)
        pl.addLayout(tools)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Original File", "New Name", "Date", "Type", "Party / Name",
             "Folder", "Confidence", "Status"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked |
                                   QAbstractItemView.EditKeyPressed)
        self.table.verticalHeader().setVisible(False)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setStretchLastSection(True)
        for col, w in ((C_FILE, 200), (C_NEW, 330), (C_DATE, 90), (C_TYPE, 120),
                       (C_PARTY, 150), (C_FOLDER, 150), (C_CONF, 85)):
            self.table.setColumnWidth(col, w)
        pl.addWidget(self.table, 1)
        body.addWidget(pbox, 1)

        # --- 4. Organise
        abox = QGroupBox("4. Organise")
        al = QVBoxLayout(abox)
        ab = QHBoxLayout()
        self.apply_btn = QPushButton("Organize Selected Files")
        self.apply_btn.clicked.connect(self.start_apply)
        self.undo_btn = QPushButton("Undo Last Run")
        self.undo_btn.setObjectName("lightBtn")
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.undo_last)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("redBtn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_work)
        ab.addWidget(self.apply_btn)
        ab.addWidget(self.undo_btn)
        ab.addStretch(1)
        ab.addWidget(self.cancel_btn)
        al.addLayout(ab)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        al.addWidget(self.progress)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(100)
        al.addWidget(self.log_view)
        body.addWidget(abox)

    # ------------------------------------------------------------ settings --
    def _load_settings(self):
        s = self.settings
        self.src_edit.setText(s.value("src", "", type=str))
        self.out_edit.setText(s.value("out", "", type=str))
        i = self.struct_combo.findText(s.value("structure", "Type", type=str))
        self.struct_combo.setCurrentIndex(max(i, 0))
        self.mode_combo.setCurrentIndex(s.value("mode", 0, type=int))
        self.sub_check.setChecked(s.value("sub", False, type=bool))
        self.chrono_check.setChecked(s.value("chrono", False, type=bool))
        self.model_edit.setText(s.value("model", DEFAULT_MODEL, type=str))
        self._ai_changed()

    def _save_settings(self):
        s = self.settings
        s.setValue("src", self.src_edit.text())
        s.setValue("out", self.out_edit.text())
        s.setValue("structure", self.struct_combo.currentText())
        s.setValue("mode", self.mode_combo.currentIndex())
        s.setValue("sub", self.sub_check.isChecked())
        s.setValue("chrono", self.chrono_check.isChecked())
        s.setValue("model", self.model_edit.text().strip())

    def _ai_changed(self):
        online = self.ai_combo.currentIndex() == 1
        self.key_edit.setEnabled(online)
        self.model_edit.setEnabled(online)

    # ------------------------------------------------------------- helpers --
    def add_log(self, text):
        self.log_view.append(text)

    def set_busy(self, busy):
        for w in (self.analyze_btn, self.apply_btn, self.undo_btn,
                  self.src_btn, self.out_btn, self.refresh_btn):
            w.setEnabled(not busy)
        if not busy:
            self.undo_btn.setEnabled(bool(self.last_actions))
        self.cancel_btn.setEnabled(busy)

    def browse_source(self):
        start = self.src_edit.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder", start)
        if folder:
            self.src_edit.setText(folder)
            self._save_settings()

    def browse_output(self):
        start = self.out_edit.text() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", start)
        if folder:
            self.out_edit.setText(folder)
            self._save_settings()

    def open_output(self):
        folder = self.out_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.information(self, APP_NAME, "The output folder does not exist yet.")
            return
        try:
            open_path(folder)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, "Could not open folder:\n%s" % exc)

    def open_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows or rows[0].row() >= len(self.results):
            QMessageBox.information(self, APP_NAME, "Select a row first.")
            return
        try:
            open_path(self.results[rows[0].row()]["path"])
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, "Could not open file:\n%s" % exc)

    def set_all_checked(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        for r in range(self.table.rowCount()):
            self.table.item(r, C_FILE).setCheckState(state)

    # ------------------------------------------------------------- analyze --
    def start_analyze(self):
        src = self.src_edit.text().strip()
        out = self.out_edit.text().strip()
        if not src or not os.path.isdir(src):
            QMessageBox.warning(self, APP_NAME, "Please choose a valid source folder.")
            return
        if not out:
            QMessageBox.warning(self, APP_NAME, "Please choose an output folder.")
            return
        if os.path.abspath(src) == os.path.abspath(out):
            QMessageBox.warning(self, APP_NAME,
                                "Output folder must be different from the source folder.")
            return

        ai_cfg = None
        if self.ai_combo.currentIndex() == 1:
            key = self.key_edit.text().strip()
            if not key:
                QMessageBox.warning(self, APP_NAME, "Enter an API key for Claude AI Online, "
                                    "or choose the Smart Offline AI engine.")
                return
            ans = QMessageBox.question(
                self, APP_NAME,
                "Claude AI Online sends the text of the first pages of each document "
                "to Anthropic's servers.\n\nDo not use it for confidential client "
                "files unless you have permission.\n\nContinue?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ans != QMessageBox.Yes:
                return
            ai_cfg = {"key": key, "model": self.model_edit.text().strip() or DEFAULT_MODEL}

        try:
            files = collect_files(src, out, self.sub_check.isChecked())
        except OSError as exc:
            QMessageBox.critical(self, APP_NAME, "Cannot read the source folder:\n%s" % exc)
            return
        if not files:
            QMessageBox.information(self, APP_NAME,
                                    "No supported files found (PDF, images, DOCX, TXT).")
            return

        self._save_settings()
        self.results = []
        self.table.setRowCount(0)
        self.progress.setValue(0)
        self.add_log("--- Analysis started: %d file(s) ---" % len(files))
        self.statusBar().showMessage("Analyzing...")
        self.set_busy(True)

        ocr_ok = self.ocr_ok and self.ocr_check.isChecked()
        self.analyze_worker = AnalyzeWorker(files, ocr_ok, ai_cfg, self)
        self.analyze_worker.result.connect(self.results.append)
        self.analyze_worker.progress.connect(self.progress.setValue)
        self.analyze_worker.log.connect(self.add_log)
        self.analyze_worker.finished_scan.connect(self.analyze_finished)
        self.analyze_worker.start()

    def analyze_finished(self, cancelled):
        self.set_busy(False)
        self.fill_table()
        msg = "Analysis %s: %d file(s)." % ("cancelled" if cancelled else "complete",
                                           len(self.results))
        self.add_log(msg)
        self.statusBar().showMessage(msg + " Review the plan, then click 'Organize Selected Files'.")

    # ------------------------------------------------------- plan / table ---
    def _numbers(self):
        """Return list of numbers for each result, plus the digit width."""
        start = self.start_spin.value()
        order = list(range(len(self.results)))
        if self.chrono_check.isChecked():
            order.sort(key=lambda i: (self.results[i]["date"] or dt.date.max, i))
        numbers = [0] * len(self.results)
        for n, idx in enumerate(order):
            numbers[idx] = start + n
        width = max(3, len(str(start + max(len(self.results) - 1, 0))))
        return numbers, width

    @staticmethod
    def _build_name(res, number, width):
        date_s = res["date"].isoformat() if res["date"] else "NoDate"
        parts = [("%0*d" % (width, number)), date_s,
                 clean_part(res["title"] or res["stem"], 40),
                 clean_part(res["party"] or "Unknown", 35)]
        return "_".join(parts) + res["ext"]

    def _folder_text(self, res):
        year = str(res["date"].year) if res["date"] else "Undated"
        t = clean_folder(res["folder"])
        p = clean_folder(res["party"] or "Unknown")
        mode = self.struct_combo.currentText()
        parts = {"Type": [t], "Type / Year": [t, year], "Year / Type": [year, t],
                 "Party / Type": [p, t], "Type / Party": [t, p]}.get(mode, [t])
        return "/".join(parts)

    def fill_table(self):
        numbers, width = self._numbers()
        self.table.setRowCount(len(self.results))
        base_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        for r, res in enumerate(self.results):
            def mk(text, editable=False):
                it = QTableWidgetItem(text)
                it.setFlags(base_flags | (Qt.ItemIsEditable if editable else Qt.NoItemFlags))
                return it
            f = mk(os.path.basename(res["path"]))
            f.setFlags(base_flags | Qt.ItemIsUserCheckable)
            f.setCheckState(Qt.Checked)
            f.setToolTip(res["path"])
            self.table.setItem(r, C_FILE, f)
            self.table.setItem(r, C_NEW, mk(self._build_name(res, numbers[r], width), True))
            self.table.setItem(r, C_DATE, mk(res["date"].isoformat() if res["date"] else "-"))
            self.table.setItem(r, C_TYPE, mk(res["type"]))
            self.table.setItem(r, C_PARTY, mk(res["party"] or "-"))
            self.table.setItem(r, C_FOLDER, mk(self._folder_text(res), True))
            conf = mk("%d%%" % res["confidence"])
            if res["confidence"] < 40:
                conf.setForeground(QColor("#E02424"))
            self.table.setItem(r, C_CONF, conf)
            self.table.setItem(r, C_STATUS, mk(res["note"] or "Ready"))

    def refresh_names(self):
        if not self.results:
            return
        numbers, width = self._numbers()
        for r, res in enumerate(self.results):
            self.table.item(r, C_NEW).setText(self._build_name(res, numbers[r], width))
            self.table.item(r, C_FOLDER).setText(self._folder_text(res))
        self.statusBar().showMessage("Names and folders refreshed.")

    def export_plan(self):
        if not self.results:
            QMessageBox.information(self, APP_NAME, "Analyze files first.")
            return
        start = self.out_edit.text().strip() or os.path.expanduser("~")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Plan", os.path.join(start, "file_manager_plan.csv"),
            "CSV files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                w = csv.writer(fh)
                w.writerow(["Original Path", "New Name", "Date", "Type",
                            "Party", "Folder", "Confidence"])
                for r, res in enumerate(self.results):
                    w.writerow([res["path"], self.table.item(r, C_NEW).text(),
                                self.table.item(r, C_DATE).text(), res["type"],
                                res["party"], self.table.item(r, C_FOLDER).text(),
                                self.table.item(r, C_CONF).text()])
            self.add_log("Plan exported: %s" % path)
        except OSError as exc:
            QMessageBox.critical(self, APP_NAME, "Could not save file:\n%s" % exc)

    # --------------------------------------------------------------- apply --
    def start_apply(self):
        if not self.results:
            QMessageBox.information(self, APP_NAME, "Analyze files first.")
            return
        out = self.out_edit.text().strip()
        if not out:
            QMessageBox.warning(self, APP_NAME, "Please choose an output folder.")
            return
        try:
            os.makedirs(out, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(self, APP_NAME, "Cannot use output folder:\n%s" % exc)
            return

        items = []
        for r, res in enumerate(self.results):
            if self.table.item(r, C_FILE).checkState() != Qt.Checked:
                continue
            name = clean_filename(self.table.item(r, C_NEW).text(), res["ext"])
            raw = self.table.item(r, C_FOLDER).text()
            parts = [clean_folder(p) for p in re.split(r"[\\/]+", raw)
                     if p.strip() and p.strip() not in (".", "..")]
            if not parts:
                parts = ["Needs Review"]
            items.append({"row": r, "src": res["path"],
                          "dest_dir": os.path.join(out, *parts), "name": name})
        if not items:
            QMessageBox.information(self, APP_NAME, "No files are ticked.")
            return

        move = self.mode_combo.currentIndex() == 1
        ans = QMessageBox.question(
            self, APP_NAME,
            "%s %d file(s) into:\n%s\n\nContinue?"
            % ("MOVE" if move else "Copy", len(items), out),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if ans != QMessageBox.Yes:
            return

        self._save_settings()
        self.progress.setValue(0)
        self.add_log("--- Organising %d file(s) ---" % len(items))
        self.statusBar().showMessage("Organising...")
        self.set_busy(True)
        self.last_move = move
        self.last_out = out

        self.apply_worker = ApplyWorker(items, move, self)
        self.apply_worker.status.connect(self.update_status)
        self.apply_worker.progress.connect(self.progress.setValue)
        self.apply_worker.log.connect(self.add_log)
        self.apply_worker.finished_apply.connect(self.apply_finished)
        self.apply_worker.start()

    def update_status(self, row, text):
        item = self.table.item(row, C_STATUS)
        if item:
            item.setText(text)
            if text == "Failed":
                item.setForeground(QColor("#E02424"))
            elif text in ("Moved", "Copied"):
                item.setForeground(QColor("#0B7A2E"))

    def apply_finished(self, ok, failed, actions, cancelled):
        self.last_actions = actions
        self.set_busy(False)
        if not cancelled:
            self.progress.setValue(100)
        # Write a log file so every rename can be traced
        if actions:
            try:
                stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                log_path = os.path.join(self.last_out, "File_Manager_log_%s.csv" % stamp)
                with open(log_path, "w", newline="", encoding="utf-8-sig") as fh:
                    w = csv.writer(fh)
                    w.writerow(["Original Path", "New Path", "Action"])
                    for _, src, dest in actions:
                        w.writerow([src, dest, "Move" if self.last_move else "Copy"])
                self.add_log("Log saved: %s" % log_path)
            except OSError:
                pass
        msg = "Finished: %d done, %d failed%s." % (ok, failed, " (cancelled)" if cancelled else "")
        self.add_log(msg)
        self.statusBar().showMessage(msg)
        QMessageBox.information(self, APP_NAME, msg)

    # ---------------------------------------------------------------- undo --
    def undo_last(self):
        if not self.last_actions:
            return
        ans = QMessageBox.question(
            self, APP_NAME,
            "Undo the last run (%d file(s))?\n%s"
            % (len(self.last_actions),
               "Moved files will be returned to their original place."
               if self.last_move else "The copied files will be deleted from the output folder."),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ans != QMessageBox.Yes:
            return
        done = 0
        root = os.path.abspath(self.last_out)
        for row, src, dest in reversed(self.last_actions):
            try:
                if os.path.exists(dest):
                    if self.last_move:
                        folder = os.path.dirname(src)
                        os.makedirs(folder, exist_ok=True)
                        target = src
                        if os.path.exists(target):
                            target = unique_path(folder, os.path.basename(src))
                        shutil.move(dest, target)
                    else:
                        os.remove(dest)
                    done += 1
                self.update_status(row, "Reverted")
                # remove empty folders we created
                d = os.path.dirname(os.path.abspath(dest))
                while d != root and d.startswith(root):
                    try:
                        os.rmdir(d)
                    except OSError:
                        break
                    d = os.path.dirname(d)
            except Exception as exc:
                self.add_log("Undo failed for %s: %s" % (dest, exc))
        self.last_actions = []
        self.undo_btn.setEnabled(False)
        self.add_log("Undo complete: %d file(s) restored." % done)
        self.statusBar().showMessage("Undo complete.")

    # -------------------------------------------------------------- cancel --
    def cancel_work(self):
        for w in (self.analyze_worker, self.apply_worker):
            if w and w.isRunning():
                w.cancel()
        self.add_log("Cancelling...")

    # --------------------------------------------------------------- about --
    def show_ocr_help(self):
        QMessageBox.information(
            self, "OCR Help",
            "Text-based PDFs, Word and text files work without extra software.\n\n"
            "For SCANNED PDFs and photos (JPG/PNG/TIFF) the free Tesseract OCR "
            "program is needed:\n\n"
            "1. Download 'Tesseract OCR' for Windows (UB Mannheim installer).\n"
            "2. Install it in the default folder (C:\\Program Files\\Tesseract-OCR).\n"
            "3. Restart File Manager.\n\n"
            "Status now: %s" % ("OCR is available." if self.ocr_ok else "OCR not found."))

    def show_about(self):
        QMessageBox.about(
            self, "About " + APP_NAME,
            "<h3 style='color:#0A3D91'>%s</h3><p>Version %s</p>"
            "<p>Reads each document, finds its date, title and name, renames it as "
            "<b>001_Date_Title_Name</b> and sorts it into folders suggested by the "
            "built-in AI engine.</p>"
            "<p><span style='color:#E02424'>Always review the preview before organising. "
            "Automatic detection can be wrong.</span></p>" % (APP_NAME, APP_VERSION))

    def closeEvent(self, event):
        self._save_settings()
        for w in (self.analyze_worker, self.apply_worker):
            if w and w.isRunning():
                w.cancel()
                w.wait(3000)
        event.accept()


# ----------------------------------------------------------------------------
# 8. ENTRY POINT
# ----------------------------------------------------------------------------
_window = None  # keep a reference so the window is not garbage-collected


def main():
    global _window
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    except Exception:
        pass
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Segoe UI", 10))
    _window = MainWindow()
    _window.show()
    app.exec_()


if __name__ == "__main__":
    main()
