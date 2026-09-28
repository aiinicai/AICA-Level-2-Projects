#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AOM DPDP Audit Suite
====================
Standalone Tkinter desktop app for audit automation under the
Digital Personal Data Protection Act, 2023 (DPDP Act).

  Tab 1  Synthetic PDF Generator    -> Sample_Audit_Document_01.pdf ... _10.pdf (10 vendors)
  Tab 2  DPDP True Redaction Engine -> Redacted_Audit_Document_01.pdf ... _10.pdf (batch)
         (redact -> apply -> RASTERISE every page at 300 DPI -> verify 0 text)
  Tab 3  Data Extractor             -> Audit_Working_Paper.csv (all documents combined)

  10-minute evaluation timer.

Run:      python aom_dpdp_audit_suite.py
Headless: python aom_dpdp_audit_suite.py --selftest   (runs all three engines, no GUI)

Dependencies (auto-installed on first run if missing): PyMuPDF, reportlab
"""

import csv
import importlib
import os
import queue
import re
import site
import subprocess
import sys
import threading
import datetime
import random

# --------------------------------------------------------------------------------------
# Paths & constants
# --------------------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SAMPLE_PDF = "Sample_Audit_Document.pdf"
REDACTED_PDF = "Redacted_Audit_Document.pdf"
WORKING_PAPER_CSV = "Audit_Working_Paper.csv"

APP_NAME = "AOM DPDP Audit Suite"
LICENSE_TEXT = "AOM Professional License - Evaluation Mode"
TRIAL_SECONDS = 10 * 60   # 10-minute evaluation
FLATTEN_DPI = 300

PRIMARY = "#1e3a8a"
PRIMARY_HOVER = "#1d4ed8"
PRIMARY_DARK = "#172554"

# --------------------------------------------------------------------------------------
# Dependency bootstrap
# --------------------------------------------------------------------------------------
fitz = None  # PyMuPDF, bound by load_dependencies()


IMPORT_ERRORS = {}


def _try_import_pymupdf():
    for name in ("pymupdf", "fitz"):
        try:
            mod = importlib.import_module(name)
            if hasattr(mod, "open") and hasattr(mod, "Document"):
                IMPORT_ERRORS.pop("PyMuPDF", None)
                return mod
        except ModuleNotFoundError as e:
            if e.name not in (name, None):
                IMPORT_ERRORS["PyMuPDF"] = f"{type(e).__name__}: {e}"
        except Exception as e:  # installed but cannot load (e.g. DLL blocked)
            IMPORT_ERRORS["PyMuPDF"] = f"{type(e).__name__}: {e}"
    return None


def _has_reportlab():
    try:
        importlib.import_module("reportlab.platypus")
        IMPORT_ERRORS.pop("reportlab", None)
        return True
    except ModuleNotFoundError as e:
        if not (e.name or "").startswith("reportlab"):
            IMPORT_ERRORS["reportlab"] = f"{type(e).__name__}: {e}"
        return False
    except Exception as e:
        IMPORT_ERRORS["reportlab"] = f"{type(e).__name__}: {e}"
        return False


def console_python():
    """pythonw.exe (double-click launch) has no stdout, which breaks pip. Use python.exe beside it."""
    exe = sys.executable
    folder, name = os.path.split(exe)
    if name.lower().startswith("pythonw"):
        candidate = os.path.join(folder, name[:6] + name[7:])  # pythonw.exe -> python.exe
        if os.path.exists(candidate):
            return candidate
    return exe


PIP_ERROR = ""


def load_dependencies():
    """Import PyMuPDF + reportlab, pip-installing them if missing. Returns list of failures."""
    global fitz
    missing = []
    if _try_import_pymupdf() is None:
        missing.append("PyMuPDF")
    if not _has_reportlab():
        missing.append("reportlab")

    global PIP_ERROR
    missing = [m for m in missing if m not in IMPORT_ERRORS]
    if missing:
        try:
            print(f"[setup] Installing missing packages: {', '.join(missing)} ...")
        except Exception:
            pass  # pythonw has no console
        base = [console_python(), "-m", "pip", "install", "--disable-pip-version-check",
                "--no-input", "--progress-bar", "off"]
        run_kw = dict(stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                      text=True, timeout=600)
        if sys.platform.startswith("win"):
            run_kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        for extra in ([], ["--user"], ["--break-system-packages"]):
            try:
                res = subprocess.run(base + extra + missing, **run_kw)
                if res.returncode == 0:
                    PIP_ERROR = ""
                    break
                PIP_ERROR = res.stdout or ""
            except Exception as e:
                PIP_ERROR = f"{type(e).__name__}: {e}"
        try:  # a --user install may not be on sys.path yet
            user_site = site.getusersitepackages()
            if user_site and user_site not in sys.path:
                sys.path.append(user_site)
        except Exception:
            pass
        importlib.invalidate_caches()

    fitz = _try_import_pymupdf()
    failures = []
    if fitz is None:
        failures.append("PyMuPDF")
    if not _has_reportlab():
        failures.append("reportlab")
    return failures


# --------------------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------------------
def fmt_inr(amount):
    """Indian digit grouping: 508950 -> 5,08,950.00"""
    whole, dec = f"{amount:.2f}".split(".")
    last3, rest = whole[-3:], whole[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ",".join(parts + [last3]) + "." + dec


def open_path(path):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def _noop(*_a, **_k):
    pass


# --------------------------------------------------------------------------------------
# ENGINE 1 - Synthetic voucher generator (10 different vendors)
# --------------------------------------------------------------------------------------
COMPANY = {
    "name": "AOM Industries Private Limited",
    "addr": "Plot 14, MIDC Industrial Area, Andheri (East), Mumbai 400093",
    "state": "27",  # Maharashtra - decides CGST+SGST vs IGST
}

# name, PAN entity type (P=proprietor, F=firm/LLP, C=company), contact person, address,
# GST state code, bank & branch, IFSC bank code, (line item 1, line item 2), (TDS section, rate)
VENDOR_BOOK = [
    ("Shree Ganesh Engineering Works", "P", "Rakesh Kumar Sharma",
     "Gala No. 7, Saki Naka Industrial Estate, Mumbai 400072", "27",
     "HDFC Bank Ltd, Andheri East Branch", "HDFC",
     ("Fabrication of MS structural frames", "Installation & commissioning charges"), ("194C", None)),
    ("Sai Krupa Logistics", "P", "Sunita Prakash Patil",
     "Shop 12, Turbhe MIDC, Navi Mumbai 400705", "27",
     "State Bank of India, Vashi Branch", "SBIN",
     ("Transportation of raw material - Pune to Mumbai", "Loading & unloading charges"), ("194C", None)),
    ("Techvista Solutions LLP", "F", "Anand Venkatesh Iyer",
     "4th Floor, Prestige Towers, MG Road, Bengaluru 560001", "29",
     "ICICI Bank Ltd, MG Road Branch", "ICIC",
     ("Annual maintenance of ERP servers", "On-site technical support (40 hours)"), ("194J", 0.02)),
    ("Maruti Electricals", "P", "Harish Chandra Mehta",
     "12, Lamington Road, Grant Road, Mumbai 400007", "27",
     "Kotak Mahindra Bank, Grant Road Branch", "KKBK",
     ("Supply & fitting of LED panels", "Rewiring of production floor"), ("194C", None)),
    ("Greenleaf Housekeeping Services Pvt Ltd", "C", "Priya Suresh Nair",
     "Unit 3, Kohinoor City, Kurla (West), Mumbai 400070", "27",
     "Axis Bank Ltd, BKC Branch", "UTIB",
     ("Housekeeping services - September 2026", "Pest control services"), ("194C", None)),
    ("Bharat Packaging Industries", "F", "Mohammed Irfan Shaikh",
     "Plot 88, Bhiwandi Industrial Area, Thane 421302", "27",
     "Bank of Baroda, Bhiwandi Branch", "BARB",
     ("Job work - printing & die cutting of cartons", "Lamination charges"), ("194C", None)),
    ("Kaveri Civil Contractors", "P", "Suresh Babu Reddy",
     "H.No. 4-12, Kukatpally, Hyderabad 500072", "36",
     "Canara Bank, Kukatpally Branch", "CNRB",
     ("Civil work - warehouse flooring", "Waterproofing of terrace"), ("194C", None)),
    ("Apex Security Services Pvt Ltd", "C", "Vikram Singh Rathore",
     "C-44, Sector 18, Noida 201301", "09",
     "Punjab National Bank, Sector 18 Branch", "PUNB",
     ("Security guards - September 2026", "Supervisor & patrolling charges"), ("194C", None)),
    ("Nandini Catering Co.", "P", "Lakshmi Narayanan",
     "22, Anna Salai, Chennai 600002", "33",
     "Indian Bank, Anna Salai Branch", "IDIB",
     ("Canteen services - September 2026", "Festival lunch arrangement"), ("194C", None)),
    ("Orbit IT Hardware", "F", "Deepak Kumar Gupta",
     "Shop 21, Nehru Place, New Delhi 110019", "07",
     "IDFC FIRST Bank, Nehru Place Branch", "IDFB",
     ("Laptops - 5 nos", "Networking switches & cabling"), ("N/A - purchase of goods", 0.0)),
]
MAX_DOCS = len(VENDOR_BOOK)

_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven",
         "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two(n):
    return _ONES[n] if n < 20 else _TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")


def _three(n):
    parts = []
    if n // 100:
        parts.append(_ONES[n // 100] + " Hundred")
    if n % 100:
        parts.append(_two(n % 100))
    return " ".join(parts)


def inr_words(amount):
    """Indian system: 508950 -> Rupees Five Lakh Eight Thousand Nine Hundred Fifty Only"""
    total_paise = int(round(amount * 100))
    rupees, paise = divmod(total_paise, 100)
    parts = []
    crore, rupees = divmod(rupees, 10 ** 7)
    lakh, rupees = divmod(rupees, 10 ** 5)
    thousand, rest = divmod(rupees, 1000)
    if crore:
        parts.append(_three(crore) + " Crore")
    if lakh:
        parts.append(_two(lakh) + " Lakh")
    if thousand:
        parts.append(_two(thousand) + " Thousand")
    if rest:
        parts.append(_three(rest))
    text = "Rupees " + (" ".join(parts) if parts else "Zero")
    if paise:
        text += " and " + _two(paise) + " Paise"
    return text + " Only"


def build_profile(n):
    """Deterministic synthetic data for voucher n (1-based). All identifiers are fictitious."""
    name, etype, contact, addr, state, bank, bankcode, items, (section, rate) = VENDOR_BOOK[(n - 1) % MAX_DOCS]
    rng = random.Random(20260928 + n)
    L = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    D = "0123456789"
    pick = lambda chars, k: "".join(rng.choice(chars) for _ in range(k))  # noqa: E731

    if n == 1:  # keep the reference values from the original brief
        pan, aadhaar = "ABCDE1234F", "9876 5432 1098"
    else:
        pan = pick(L, 3) + etype + name[0].upper() + pick(D, 4) + pick(L, 1)
        a = str(rng.randint(2, 9)) + pick(D, 11)
        aadhaar = f"{a[:4]} {a[4:8]} {a[8:]}"
    m = str(rng.randint(6, 9)) + pick(D, 9)
    mobile = f"+91 {m[:5]} {m[5:]}"
    account = str(rng.randint(1, 9)) + pick(D, rng.randint(10, 15))
    ifsc = bankcode + "0" + pick(D, 6)
    gstin = state + pan + str(rng.randint(1, 3)) + "Z" + pick(L + D, 1)
    initials = "".join(w[0] for w in re.findall(r"[A-Za-z]+", name) if w[0].isupper())[:4]

    d1, d2 = sorted(rng.sample(range(1, 21), 2))
    amt1 = rng.randrange(40, 380) * 1000.0
    amt2 = rng.randrange(8, 120) * 500.0
    if rate is None:  # 194C: 1% individual/HUF, 2% others
        rate = 0.01 if etype == "P" else 0.02
    return {
        "doc_no": n,
        "company": COMPANY["name"],
        "company_addr": COMPANY["addr"],
        "voucher_no": f"PV/2026-27/{900 + n * 7:04d}",
        "voucher_date": f"{min(d2 + 5, 30):02d}-Sep-2026",
        "vendor_name": name,
        "entity": {"P": "Proprietorship", "F": "Partnership / LLP", "C": "Private Limited Company"}[etype],
        "proprietor": contact,
        "contact_role": "Proprietor" if etype == "P" else "Authorised Signatory",
        "vendor_addr": addr,
        "pan": pan,
        "aadhaar": aadhaar,
        "mobile": mobile,
        "gstin": gstin,
        "bank_name": bank,
        "account_no": account,
        "ifsc": ifsc,
        "account_type": "Current Account",
        "utr": pick(D, 12),
        "invoices": [
            (f"{initials}/INV/{rng.randint(100, 999):04d}", f"{d1:02d}-Sep-2026", items[0], amt1),
            (f"{initials}/INV/{rng.randint(100, 999):04d}", f"{d2:02d}-Sep-2026", items[1], amt2),
        ],
        "gst_rate": 0.18,
        "interstate": state != COMPANY["state"],
        "tds_section": section,
        "tds_rate": rate,
    }


def sample_name(n):
    return f"Sample_Audit_Document_{n:02d}.pdf"


def generate_voucher(path, profile=None, progress=_noop):
    """Build one realistic Vendor Payment Voucher PDF containing synthetic PII."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    d = profile or build_profile(1)
    progress(0.1, "Laying out voucher ...")
    primary = colors.HexColor(PRIMARY)
    light = colors.HexColor("#e0e7ff")
    grid = colors.HexColor("#94a3b8")

    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12)
    small = ParagraphStyle("small", parent=body, fontSize=7.5, leading=10, textColor=colors.HexColor("#475569"))
    h_company = ParagraphStyle("hc", parent=body, fontName="Helvetica-Bold", fontSize=15, textColor=colors.white, leading=18)
    h_addr = ParagraphStyle("ha", parent=body, fontSize=8.5, textColor=colors.HexColor("#c7d2fe"))
    h_title = ParagraphStyle("ht", parent=body, fontName="Helvetica-Bold", fontSize=12, textColor=colors.white, alignment=TA_RIGHT)
    section = ParagraphStyle("sec", parent=body, fontName="Helvetica-Bold", fontSize=10, textColor=primary, spaceBefore=6, spaceAfter=3)

    def grid_table(rows, widths, header=True):
        t = Table(rows, colWidths=widths)
        style = [
            ("GRID", (0, 0), (-1, -1), 0.6, grid),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        if header:
            style += [
                ("BACKGROUND", (0, 0), (-1, 0), primary),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        t.setStyle(TableStyle(style))
        return t

    story = []
    W = A4[0] - 30 * mm

    head = Table(
        [[[Paragraph(d["company"], h_company), Paragraph(d["company_addr"], h_addr)],
          [Paragraph("VENDOR PAYMENT VOUCHER", h_title)]]],
        colWidths=[W * 0.62, W * 0.38],
    )
    head.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), primary),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [head, Spacer(1, 6)]
    story.append(Paragraph(
        f"<b>Voucher No:</b> {d['voucher_no']} &nbsp;&nbsp;&nbsp; <b>Voucher Date:</b> {d['voucher_date']}"
        f" &nbsp;&nbsp;&nbsp; <b>Payment Mode:</b> NEFT &nbsp;&nbsp;&nbsp; <b>Cost Centre:</b> Plant-II", body))

    story.append(Paragraph("A. Vendor Details (Personal Data under DPDP Act, 2023)", section))
    story.append(grid_table([
        ["Particulars", "Details"],
        ["Vendor Name", f"{d['vendor_name']}  ({d['entity']})"],
        [d["contact_role"], d["proprietor"]],
        ["Address", d["vendor_addr"]],
        ["PAN Number", d["pan"]],
        ["Aadhaar Number", d["aadhaar"]],
        ["Mobile Number", d["mobile"]],
        ["GSTIN", d["gstin"]],
    ], [W * 0.3, W * 0.7]))

    story.append(Paragraph("B. Beneficiary Bank Details", section))
    story.append(grid_table([
        ["Particulars", "Details"],
        ["Bank & Branch", d["bank_name"]],
        ["Bank Account Number", d["account_no"]],
        ["IFSC Code", d["ifsc"]],
        ["Account Type", d["account_type"]],
        ["UTR / Payment Reference", d["utr"]],
    ], [W * 0.3, W * 0.7]))

    progress(0.4, "Computing GST / TDS ...")
    gross = sum(i[3] for i in d["invoices"])
    gst = round(gross * d["gst_rate"], 2)
    invoice_total = gross + gst
    tds = round(gross * d["tds_rate"], 2)
    net = invoice_total - tds

    story.append(Paragraph("C. Invoices Settled", section))
    inv_rows = [["Invoice #", "Invoice Date", "Description", "Taxable Value (INR)"]]
    for inv in d["invoices"]:
        inv_rows.append([inv[0], inv[1], inv[2], fmt_inr(inv[3])])
    inv_t = grid_table(inv_rows, [W * 0.2, W * 0.16, W * 0.42, W * 0.22])
    inv_t.setStyle(TableStyle([("ALIGN", (3, 0), (3, -1), "RIGHT")]))
    story.append(inv_t)

    gst_label = "Add: IGST 18%" if d["interstate"] else "Add: GST (CGST 9% + SGST 9%)"
    if d["tds_rate"]:
        tds_row = [f"Less: TDS u/s {d['tds_section']}", f"{d['tds_rate'] * 100:g}% on taxable value", fmt_inr(tds)]
    else:
        tds_row = ["Less: TDS", d["tds_section"], fmt_inr(0)]
    story.append(Paragraph("D. Payment Computation", section))
    comp = grid_table([
        ["Component", "Basis", "Amount (INR)"],
        ["Gross Taxable Value", "As per invoices", fmt_inr(gross)],
        [gst_label, "18% on taxable value", fmt_inr(gst)],
        ["Invoice Total", "", fmt_inr(invoice_total)],
        tds_row,
        ["Payment Amount (Net Payable)", "", fmt_inr(net)],
    ], [W * 0.42, W * 0.33, W * 0.25])
    comp.setStyle(TableStyle([
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("BACKGROUND", (0, -1), (-1, -1), light),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(comp)
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>Amount in words:</b> {inr_words(net)}", body))
    story.append(Spacer(1, 4))
    tds_text = f"after deduction of TDS u/s {d['tds_section']}" if d["tds_rate"] else "no TDS applicable"
    story.append(Paragraph(
        f"<b>Narration:</b> Being payment released to {d['vendor_name']} ({d['contact_role']} "
        f"{d['proprietor']}, PAN {d['pan']}) against invoices {d['invoices'][0][0]} and "
        f"{d['invoices'][1][0]}, {tds_text}. Vendor KYC verified with Aadhaar {d['aadhaar']}; "
        f"payment advice sent to {d['mobile']}. Credited to A/c {d['account_no']} (IFSC {d['ifsc']}).", body))

    story.append(Paragraph("E. Authorisation", section))
    appr = Table(
        [["Prepared by", "Checked by", "Approved by", "Received by"],
         ["\n", "\n", "\n", "\n"],
         ["Accounts Executive", "Finance Manager", "CFO", "Vendor / Authorised Signatory"]],
        colWidths=[W / 4] * 4,
    )
    appr.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, grid), ("INNERGRID", (0, 0), (-1, -1), 0.6, grid),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("BACKGROUND", (0, 0), (-1, 0), light),
    ]))
    story.append(appr)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "SYNTHETIC TEST DATA - generated by AOM DPDP Audit Suite for redaction testing. "
        "All names, identifiers and account numbers are fictitious.", small))

    def on_page(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(15 * mm, 10 * mm, f"{d['company']}  |  {d['voucher_no']}")
        canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {doc_.page}")
        canvas.restoreState()

    progress(0.7, "Writing PDF ...")
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=14 * mm, bottomMargin=16 * mm,
                            title="Vendor Payment Voucher", author=d["company"],
                            subject=f"Payment voucher {d['voucher_no']}")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    progress(1.0, "Done")
    return {"path": path, "vendor": d["vendor_name"], "voucher_no": d["voucher_no"],
            "pan": d["pan"], "net": net}


def generate_batch(out_dir, count=MAX_DOCS, progress=_noop):
    """Generate `count` different vouchers: Sample_Audit_Document_01.pdf ... _NN.pdf"""
    count = max(1, min(int(count), MAX_DOCS))
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for n in range(1, count + 1):
        progress((n - 1) / count, f"Generating voucher {n}/{count} ...")
        path = os.path.join(out_dir, sample_name(n))
        results.append(generate_voucher(path, build_profile(n)))
    progress(1.0, "Done")
    return results



# --------------------------------------------------------------------------------------
# ENGINE 2 - DPDP true redaction (redact -> apply -> rasterise -> verify)
# --------------------------------------------------------------------------------------
PII_CATEGORIES = {
    "pan": ("PAN Numbers", [
        r"[A-Z]{5}[0-9]{4}[A-Z]",   # also caught inside a GSTIN (chars 3-12)
    ]),
    "aadhaar_phone": ("Aadhaar / Phone", [
        r"(?<![\d])[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?![\d])",          # Aadhaar (12 digits)
        r"(?:\+91[ -]?|(?<![\d]))[6-9]\d{4}[ -]?\d{5}(?![\d])",       # Indian mobile
    ]),
    "bank": ("Bank Details", [
        r"[A-Z]{4}0[A-Z0-9]{6}",                  # IFSC
        r"(?<![\d])\d{9,18}(?![\d])",             # Account / UTR numbers
    ]),
}


def find_pii(text, categories):
    """Return list of (category_key, matched_string), de-duplicated, in document order."""
    hits, seen = [], set()
    for key in categories:
        for pattern in PII_CATEGORIES[key][1]:
            for m in re.finditer(pattern, text):
                s = m.group(0).strip()
                if s and (key, s) not in seen:
                    seen.add((key, s))
                    hits.append((key, s))
    return hits


def mask(s):
    s = s.strip()
    return s[:2] + "*" * max(len(s) - 4, 2) + s[-2:] if len(s) > 4 else "****"


def redact_pdf(src, dst, categories, dpi=FLATTEN_DPI, progress=_noop):
    """
    True redaction:
      1. Locate PII text and its coordinates on every page.
      2. Add black redaction annotations and APPLY them (glyphs are removed from the content stream).
      3. Rasterise each page to a {dpi} DPI bitmap and rebuild the PDF from images only,
         so no text layer, fonts, hidden objects, annotations or metadata survive.
      4. Re-open the output and verify zero extractable characters remain.
    """
    if not categories:
        raise ValueError("Select at least one PII category.")
    if os.path.abspath(src) == os.path.abspath(dst):
        raise ValueError("Output file must be different from the source file.")

    src_doc = fitz.open(src)
    if src_doc.needs_pass:
        raise ValueError("The PDF is password-protected. Remove the password and retry.")
    out = fitz.open()
    counts = {k: 0 for k in categories}
    log = []
    n = len(src_doc)
    all_hits = set()

    for pno in range(n):
        page = src_doc[pno]
        progress(pno / n, f"Page {pno + 1}/{n}: scanning for PII ...")
        text = page.get_text("text")
        for key, s in find_pii(text, categories):
            rects = page.search_for(s)
            if not rects:  # PDF whitespace may differ from extracted text: redact token by token
                rects = [r for tok in s.split() for r in page.search_for(tok)]
            for r in rects:
                page.add_redact_annot(r, fill=(0, 0, 0))
            if rects:
                counts[key] += len(rects)
                all_hits.add(s)
                log.append((pno + 1, PII_CATEGORIES[key][0], mask(s), len(rects)))

        # Step 2: apply redactions - removes underlying text/vector/image pixels under the boxes
        page.apply_redactions()

        # Step 3: flatten - render to bitmap and rebuild page from the image only
        progress((pno + 0.5) / n, f"Page {pno + 1}/{n}: rasterising at {dpi} DPI ...")
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        new_page = out.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, pixmap=pix)
        pix = None

    src_doc.close()
    out.set_metadata({})           # scrub author / title / subject / producer
    try:
        out.del_xml_metadata()
    except Exception:
        pass
    progress(0.97, "Saving flattened PDF ...")
    out.save(dst, garbage=4, deflate=True, clean=True)
    out.close()

    # Step 4: verification
    v = fitz.open(dst)
    residual_chars = sum(len(p.get_text("text").strip()) for p in v)
    fonts = sum(len(p.get_fonts()) for p in v)
    pages_out = len(v)
    v.close()
    leaked = [h for h in all_hits if residual_chars and h in open(dst, "rb").read().decode("latin-1", "ignore")]
    progress(1.0, "Done")
    return {
        "path": dst,
        "pages": pages_out,
        "counts": counts,
        "log": log,
        "residual_chars": residual_chars,
        "fonts": fonts,
        "leaked": leaked,
        "dpi": dpi,
        "size_kb": os.path.getsize(dst) / 1024,
    }


def redacted_name(src):
    base = os.path.basename(src)
    return "Redacted_" + base[len("Sample_"):] if base.startswith("Sample_") else "Redacted_" + base


def redact_batch(files, out_dir, categories, dpi=FLATTEN_DPI, progress=_noop):
    """Run true redaction on every file; output Redacted_*.pdf in out_dir."""
    if not files:
        raise ValueError("Add at least one PDF to redact.")
    os.makedirs(out_dir, exist_ok=True)
    results, n = [], len(files)
    for i, src in enumerate(files):
        dst = os.path.join(out_dir, redacted_name(src))
        sub = lambda f, m, i=i: progress((i + f) / n, f"[{i + 1}/{n}] {os.path.basename(src)} - {m}")  # noqa: E731
        try:
            r = redact_pdf(src, dst, categories, dpi=dpi, progress=sub)
            r["src"] = src
        except Exception as e:
            r = {"src": src, "path": dst, "error": f"{type(e).__name__}: {e}"}
        results.append(r)
    progress(1.0, "Done")
    return results


# --------------------------------------------------------------------------------------
# ENGINE 3 - Working-paper extractor (one combined CSV for many PDFs)
# --------------------------------------------------------------------------------------
CSV_COLUMNS = ["Document", "Page", "Source", "Record", "Field", "Value"]


def _clean(v):
    return re.sub(r"\s+", " ", str(v)).strip() if v is not None else ""


def extract_rows(src):
    """Return (rows, tables, pages, text_pages) for one PDF. Rows exclude the Document column."""
    doc = fitz.open(src)
    rows, table_count, text_pages = [], 0, 0
    for pno in range(len(doc)):
        page = doc[pno]
        if page.get_text("text").strip():
            text_pages += 1
        table_boxes = []
        if hasattr(page, "find_tables"):
            try:
                for t in page.find_tables().tables:
                    data = [[_clean(c) for c in r] for r in t.extract()]
                    data = [r for r in data if any(r)]
                    if not data:
                        continue
                    table_count += 1
                    table_boxes.append(fitz.Rect(t.bbox))
                    header = data[0]
                    label = f"Table {table_count}"
                    two_col_kv = len(header) == 2
                    for ri, r in enumerate(data[1:], 1):
                        if two_col_kv:
                            if r[0] or r[1]:
                                rows.append([pno + 1, label, ri, r[0], r[1]])
                        else:
                            for ci, cell in enumerate(r):
                                field = header[ci] if ci < len(header) and header[ci] else f"Col {ci + 1}"
                                if cell:
                                    rows.append([pno + 1, label, ri, field, cell])
            except Exception:
                pass
        for b in page.get_text("blocks"):
            rect, text = fitz.Rect(b[:4]), b[4]
            if any(rect.intersects(tb) for tb in table_boxes):
                continue
            for m in re.finditer(r"([A-Z][A-Za-z /&().#-]{1,40}?):\s*(.+?)(?=\s{2,}[A-Z][A-Za-z /&().#-]{1,40}?:|$)",
                                 text.replace("\n", "  ")):
                k, v = _clean(m.group(1)), _clean(m.group(2))
                if k and v and len(v) < 400:
                    rows.append([pno + 1, "Header / Narrative", "", k, v])
    pages = len(doc)
    doc.close()
    return rows, table_count, pages, text_pages


def extract_to_csv(files, dst, progress=_noop):
    """Extract tables and 'Label: value' fields from every PDF into one CSV working paper."""
    if isinstance(files, str):
        files = [files]
    if not files:
        raise ValueError("Add at least one PDF to extract.")
    all_rows, per_doc, n = [], [], len(files)
    for i, src in enumerate(files):
        progress(i / n, f"[{i + 1}/{n}] Extracting {os.path.basename(src)} ...")
        name = os.path.basename(src)
        try:
            rows, tables, pages, text_pages = extract_rows(src)
            all_rows += [[name] + r for r in rows]
            per_doc.append({"file": name, "records": len(rows), "tables": tables,
                            "pages": pages, "text_pages": text_pages})
        except Exception as e:
            per_doc.append({"file": name, "error": f"{type(e).__name__}: {e}"})
    with open(dst, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        w.writerows(all_rows)
    progress(1.0, "Done")
    return {"path": dst, "rows": all_rows, "docs": per_doc,
            "tables": sum(d.get("tables", 0) for d in per_doc),
            "text_pages": sum(d.get("text_pages", 0) for d in per_doc)}



# --------------------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------------------
PALETTES = {
    "light": dict(
        bg="#f1f5f9", surface="#ffffff", surface2="#e2e8f0", field="#ffffff", fg="#0f172a",
        muted="#475569", border="#cbd5e1", title=PRIMARY, tab="#e2e8f0", disabled="#94a3b8",
        callout_bg="#fef3c7", callout_fg="#78350f", status_bg="#e2e8f0",
        ok="#15803d", warn="#b45309", err="#b91c1c", log_bg="#f8fafc",
    ),
    "dark": dict(
        bg="#0b1220", surface="#111a2e", surface2="#1e293b", field="#0f172a", fg="#e2e8f0",
        muted="#94a3b8", border="#334155", title="#93c5fd", tab="#1e293b", disabled="#334155",
        callout_bg="#422006", callout_fg="#fde68a", status_bg="#0f172a",
        ok="#4ade80", warn="#fbbf24", err="#f87171", log_bg="#0a1020",
    ),
}


def build_app():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    FONT = "Segoe UI" if sys.platform.startswith("win") else ("Helvetica Neue" if sys.platform == "darwin" else "DejaVu Sans")
    MONO = "Consolas" if sys.platform.startswith("win") else ("Menlo" if sys.platform == "darwin" else "DejaVu Sans Mono")

    class AuditApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title(APP_NAME)
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            w, h = min(1200, int(sw * 0.92)), min(840, int(sh * 0.88))
            self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")
            self.minsize(980, 660)
            self.theme = "light"
            self.style = ttk.Style(self)
            try:
                self.style.theme_use("clam")
            except tk.TclError:
                pass
            self.q = queue.Queue()
            self.busy = False
            self.expired = False
            self.remaining = TRIAL_SECONDS
            self.action_buttons = []
            self.logs = []
            self.listboxes = []

            existing = [os.path.join(BASE_DIR, sample_name(n)) for n in range(1, MAX_DOCS + 1)]
            existing = [p for p in existing if os.path.isfile(p)]
            self.gen_dir = tk.StringVar(value=BASE_DIR)
            self.gen_count = tk.IntVar(value=MAX_DOCS)
            self.red_files = list(existing)
            self.red_dir = tk.StringVar(value=BASE_DIR)
            self.ext_files = list(existing)
            self.ext_out = tk.StringVar(value=os.path.join(BASE_DIR, WORKING_PAPER_CSV))
            self.cat_vars = {k: tk.BooleanVar(value=True) for k in PII_CATEGORIES}
            self.status = tk.StringVar(value="Ready")
            self.last_redacted = []

            self._build_header()
            self._build_statusbar()
            self._build_tabs()
            self.apply_theme()
            self.after(80, self._poll_queue)
            self.after(1000, self._tick)

        # ---------------- layout ----------------
        def _build_header(self):
            self.header = tk.Frame(self, bg=PRIMARY)
            self.header.pack(fill="x")
            # right side is packed FIRST so it keeps its full width when the window is narrow
            right = tk.Frame(self.header, bg=PRIMARY)
            right.pack(side="right", padx=16, pady=10)
            self.theme_btn = tk.Button(right, text="☾  Dark", command=self.toggle_theme, relief="flat",
                                       bg=PRIMARY_DARK, fg="white", activebackground=PRIMARY_HOVER,
                                       activeforeground="white", bd=0, padx=12, pady=6,
                                       font=(FONT, 9, "bold"), cursor="hand2")
            self.theme_btn.pack(side="right", padx=(12, 0))
            lic = tk.Frame(right, bg=PRIMARY_DARK, padx=14, pady=6)
            lic.pack(side="right")
            tk.Label(lic, text=LICENSE_TEXT, bg=PRIMARY_DARK, fg="white",
                     font=(FONT, 9, "bold")).pack(anchor="e")
            self.timer_lbl = tk.Label(lic, text="", bg=PRIMARY_DARK, fg="#bfdbfe", font=(MONO, 10, "bold"))
            self.timer_lbl.pack(anchor="e")
            self.timer_bar = tk.Canvas(lic, height=4, width=260, bg="#0f1a45", highlightthickness=0)
            self.timer_bar.pack(anchor="e", pady=(3, 0))
            self._draw_timer()

            left = tk.Frame(self.header, bg=PRIMARY)
            left.pack(side="left", padx=18, pady=10, fill="x", expand=True)
            tk.Label(left, text="◆ " + APP_NAME, bg=PRIMARY, fg="white",
                     font=(FONT, 16, "bold"), anchor="w").pack(anchor="w")
            tk.Label(left, text="Audit automation  ·  DPDP Act, 2023 compliant true redaction",
                     bg=PRIMARY, fg="#c7d2fe", font=(FONT, 9), anchor="w").pack(anchor="w")

        def _build_statusbar(self):
            bar = ttk.Frame(self, style="Status.TFrame")
            bar.pack(fill="x", side="bottom")
            ttk.Label(bar, textvariable=self.status, style="Status.TLabel").pack(side="left")
            ttk.Label(bar, text=f"Output folder: {BASE_DIR}", style="Status.TLabel").pack(side="right")

        def _build_tabs(self):
            self.nb = ttk.Notebook(self)
            self.nb.pack(fill="both", expand=True, padx=14, pady=(10, 6))
            self._tab_generator()
            self._tab_redaction()
            self._tab_extractor()

        def _card(self, parent, title, subtitle=None):
            card = ttk.Frame(parent, style="Card.TFrame", padding=16)
            ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w")
            if subtitle:
                ttk.Label(card, text=subtitle, style="Muted.TLabel", wraplength=1000,
                          justify="left").pack(anchor="w", pady=(2, 8))
            return card

        def _path_row(self, parent, label, var, mode, filetypes=None, default_name=None):
            row = ttk.Frame(parent, style="Card.TFrame")
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, style="Card.TLabel", width=16).pack(side="left")
            ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True, padx=(0, 8))

            def browse():
                cur = var.get()
                init_dir = cur if mode == "dir" else (os.path.dirname(cur) or BASE_DIR)
                if mode == "dir":
                    p = filedialog.askdirectory(initialdir=init_dir)
                else:
                    p = filedialog.asksaveasfilename(initialdir=init_dir, initialfile=default_name,
                                                     filetypes=filetypes,
                                                     defaultextension=filetypes[0][1][1:])
                if p:
                    var.set(os.path.normpath(p))
            ttk.Button(row, text="Browse…", style="Secondary.TButton", command=browse).pack(side="left")

        def _file_list(self, parent, label, files):
            """Listbox of PDFs with Add / Remove / Clear. `files` is a python list kept in sync."""
            row = ttk.Frame(parent, style="Card.TFrame")
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, style="Card.TLabel", width=16).pack(side="left", anchor="n")
            box_wrap = ttk.Frame(row, style="Card.TFrame")
            box_wrap.pack(side="left", fill="x", expand=True, padx=(0, 8))
            lb = tk.Listbox(box_wrap, height=5, selectmode="extended", relief="flat", bd=0,
                            highlightthickness=1, activestyle="none", font=(FONT, 9))
            sb = ttk.Scrollbar(box_wrap, orient="vertical", command=lb.yview)
            lb.configure(yscrollcommand=sb.set)
            lb.pack(side="left", fill="x", expand=True)
            sb.pack(side="right", fill="y")
            self.listboxes.append(lb)
            count_lbl = ttk.Label(row, text="", style="Muted.TLabel", width=10)

            def refresh():
                lb.delete(0, "end")
                for f in files:
                    lb.insert("end", os.path.basename(f))
                count_lbl.configure(text=f"{len(files)} file(s)")

            def add():
                paths = filedialog.askopenfilenames(initialdir=BASE_DIR, filetypes=[("PDF files", "*.pdf")])
                for p in paths:
                    p = os.path.normpath(p)
                    if p not in files:
                        files.append(p)
                refresh()

            def remove():
                for i in sorted(lb.curselection(), reverse=True):
                    del files[i]
                refresh()

            def clear():
                files.clear()
                refresh()

            btns = ttk.Frame(row, style="Card.TFrame")
            btns.pack(side="left", anchor="n")
            ttk.Button(btns, text="Add PDFs…", style="Secondary.TButton", command=add).pack(fill="x")
            ttk.Button(btns, text="Remove", style="Secondary.TButton", command=remove).pack(fill="x", pady=3)
            ttk.Button(btns, text="Clear", style="Secondary.TButton", command=clear).pack(fill="x")
            count_lbl.pack(side="left", anchor="n", padx=(8, 0))
            refresh()
            return refresh

        def _log_box(self, parent, height=10):
            wrap = ttk.Frame(parent, style="Card.TFrame")
            wrap.pack(fill="both", expand=True, pady=(10, 0))
            txt = tk.Text(wrap, height=height, wrap="word", relief="flat", bd=0, padx=10, pady=8,
                          font=(MONO, 9), state="disabled", highlightthickness=1)
            sb = ttk.Scrollbar(wrap, orient="vertical", command=txt.yview)
            txt.configure(yscrollcommand=sb.set)
            txt.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")
            self.logs.append(txt)
            return txt

        def log(self, txt, msg, tag=None):
            txt.configure(state="normal")
            stamp = datetime.datetime.now().strftime("%H:%M:%S")
            txt.insert("end", f"[{stamp}] ", "muted")
            txt.insert("end", msg + "\n", tag)
            txt.see("end")
            txt.configure(state="disabled")

        def _action(self, parent, text, cmd):
            b = ttk.Button(parent, text=text, command=cmd, style="Primary.TButton")
            b.pack(side="left", padx=(0, 8))
            self.action_buttons.append(b)
            return b

        # ---------------- TAB 1 ----------------
        def _tab_generator(self):
            tab = ttk.Frame(self.nb, padding=14)
            self.nb.add(tab, text="  1 · Synthetic PDF Generator  ")
            card = self._card(tab, "Synthetic Vendor Payment Vouchers",
                              f"Creates up to {MAX_DOCS} different, audit-grade payment vouchers (different vendors, "
                              "entity types, states, GST/IGST, TDS sections and amounts) populated with fictitious "
                              "personal data: vendor name, invoice #, PAN, Aadhaar, mobile, bank account, IFSC and "
                              "payment amount.")
            card.pack(fill="both", expand=True)
            self._path_row(card, "Output folder", self.gen_dir, "dir")
            row = ttk.Frame(card, style="Card.TFrame")
            row.pack(fill="x", pady=4)
            ttk.Label(row, text="Documents", style="Card.TLabel", width=16).pack(side="left")
            ttk.Spinbox(row, from_=1, to=MAX_DOCS, textvariable=self.gen_count, width=6,
                        state="readonly").pack(side="left")
            ttk.Label(row, text=f"  →  {sample_name(1)} … {sample_name(MAX_DOCS)}",
                      style="Muted.TLabel").pack(side="left")

            btns = ttk.Frame(card, style="Card.TFrame")
            btns.pack(fill="x", pady=(10, 0))
            self._action(btns, "Generate Sample PDFs", self.do_generate)
            ttk.Button(btns, text="Open Folder", style="Secondary.TButton",
                       command=lambda: self._open(self.gen_dir.get())).pack(side="left")
            self.gen_progress = ttk.Progressbar(card, mode="determinate", maximum=1.0)
            self.gen_progress.pack(fill="x", pady=(12, 0))
            self.gen_log = self._log_box(card)
            self.log(self.gen_log, "Ready. Choose how many documents and click 'Generate Sample PDFs'.", "muted")

        def do_generate(self):
            out_dir = self.gen_dir.get().strip() or BASE_DIR
            count = self.gen_count.get()
            self.gen_progress["value"] = 0

            def done(res):
                self.log(self.gen_log, f"Created {len(res)} voucher(s) in {out_dir}", "ok")
                for r in res:
                    self.log(self.gen_log, f"   {os.path.basename(r['path']):<32} {r['vendor'][:34]:<35} "
                                           f"PAN {r['pan']}   Net INR {fmt_inr(r['net'])}")
                self.log(self.gen_log, "All files were added to Tab 2 and Tab 3.", "muted")
                paths = [r["path"] for r in res]
                self.red_files[:] = paths
                self.ext_files[:] = list(paths)
                self.refresh_red()
                self.refresh_ext()
            self.run_task(generate_batch, (out_dir, count), done, self.gen_log, self.gen_progress)

        # ---------------- TAB 2 ----------------
        def _tab_redaction(self):
            tab = ttk.Frame(self.nb, padding=14)
            self.nb.add(tab, text="  2 · DPDP True Redaction  ")
            card = self._card(tab, "DPDP True Redaction Engine (batch)",
                              "Finds personal data by pattern, burns black redaction boxes into each page, then "
                              "flattens every page to a 300 DPI image and rebuilds each PDF from those images.")
            card.pack(fill="both", expand=True)
            ttk.Label(card, style="Callout.TLabel", wraplength=1000, justify="left",
                      text="⚠  TRUE REDACTION, NOT MASKING.  A black rectangle drawn over text leaves the text "
                           "copy-pasteable underneath. This engine (1) deletes the matched glyphs from the content "
                           "stream, (2) rasterises each page at 300 DPI so no text layer, fonts, hidden objects or "
                           "metadata survive, and (3) re-opens every output to verify that zero extractable "
                           "characters remain.").pack(fill="x", pady=(0, 8))
            self.refresh_red = self._file_list(card, "Source PDFs", self.red_files)
            self._path_row(card, "Output folder", self.red_dir, "dir")

            cats = ttk.Frame(card, style="Card.TFrame")
            cats.pack(fill="x", pady=(8, 4))
            ttk.Label(cats, text="Redact", style="Card.TLabel", width=16).pack(side="left")
            for key, (label, _) in PII_CATEGORIES.items():
                ttk.Checkbutton(cats, text=label, variable=self.cat_vars[key],
                                style="Card.TCheckbutton").pack(side="left", padx=(0, 22))
            ttk.Label(cats, text=f"Flatten: {FLATTEN_DPI} DPI  ·  Output: Redacted_*.pdf",
                      style="Muted.TLabel").pack(side="right")

            btns = ttk.Frame(card, style="Card.TFrame")
            btns.pack(fill="x", pady=(8, 0))
            self._action(btns, f"Redact & Flatten All ({FLATTEN_DPI} DPI)", self.do_redact)
            ttk.Button(btns, text="Open Output Folder", style="Secondary.TButton",
                       command=lambda: self._open(self.red_dir.get())).pack(side="left")
            ttk.Button(btns, text="Open First Redacted PDF", style="Secondary.TButton",
                       command=lambda: self._open(self.last_redacted[0] if self.last_redacted else
                                                  os.path.join(self.red_dir.get(), "Redacted_Audit_Document_01.pdf"))
                       ).pack(side="left", padx=(8, 0))
            self.red_progress = ttk.Progressbar(card, mode="determinate", maximum=1.0)
            self.red_progress.pack(fill="x", pady=(10, 0))
            self.red_log = self._log_box(card, height=8)
            self.log(self.red_log, "Add PDFs (or generate them in Tab 1), tick PII categories, then run.", "muted")

        def do_redact(self):
            files = [f for f in self.red_files if os.path.isfile(f)]
            cats = [k for k, v in self.cat_vars.items() if v.get()]
            if not files:
                return messagebox.showwarning(APP_NAME, "No source PDFs found.\n\nGenerate them in Tab 1 or use 'Add PDFs…'.")
            if not cats:
                return messagebox.showwarning(APP_NAME, "Tick at least one PII category.")
            out_dir = self.red_dir.get().strip() or BASE_DIR
            self.red_progress["value"] = 0
            self.log(self.red_log, f"Redacting {len(files)} file(s) · " +
                     ", ".join(PII_CATEGORIES[c][0] for c in cats), "head")

            def done(results):
                ok_files, verified, areas = [], 0, 0
                for r in results:
                    name = os.path.basename(r["src"])
                    if "error" in r:
                        self.log(self.red_log, f"   ✗ {name}: {r['error']}", "err")
                        continue
                    total = sum(r["counts"].values())
                    areas += total
                    clean = r["residual_chars"] == 0 and r["fonts"] == 0
                    verified += clean
                    ok_files.append(r["path"])
                    detail = ", ".join(f"{PII_CATEGORIES[k][0]} {v}" for k, v in r["counts"].items())
                    self.log(self.red_log, f"   {'✓' if clean else '!'} {os.path.basename(r['path']):<34} "
                                           f"{total:>2} areas ({detail}) · {r['size_kb']:.0f} KB",
                             "ok" if clean else "err")
                    if total == 0:
                        self.log(self.red_log, f"     No PII matched in {name} (scanned PDF? OCR it first).", "warn")
                self.last_redacted = ok_files
                self.log(self.red_log, f"VERIFIED {verified}/{len(results)} file(s): 0 extractable characters, "
                                       f"0 fonts. {areas} areas redacted in total.",
                         "ok" if verified == len(results) else "err")
            self.run_task(redact_batch, (files, out_dir, cats), done, self.red_log, self.red_progress)

        # ---------------- TAB 3 ----------------
        def _tab_extractor(self):
            tab = ttk.Frame(self.nb, padding=14)
            self.nb.add(tab, text="  3 · Working Paper Extractor  ")
            card = self._card(tab, "Data Extractor for Working Papers (batch)",
                              "Detects ruled tables and 'Label: value' fields in every PDF and writes one combined "
                              "CSV (Document · Page · Source · Record · Field · Value) ready for pivoting in Excel.")
            card.pack(fill="both", expand=True)
            self.refresh_ext = self._file_list(card, "Source PDFs", self.ext_files)
            self._path_row(card, "Save CSV as", self.ext_out, "save", [("CSV files", "*.csv")], WORKING_PAPER_CSV)
            btns = ttk.Frame(card, style="Card.TFrame")
            btns.pack(fill="x", pady=(8, 0))
            self._action(btns, "Extract All to CSV", self.do_extract)
            ttk.Button(btns, text="Open CSV", style="Secondary.TButton",
                       command=lambda: self._open(self.ext_out.get())).pack(side="left")
            self.ext_summary = ttk.Label(btns, text="", style="Muted.TLabel")
            self.ext_summary.pack(side="right")

            tv_wrap = ttk.Frame(card, style="Card.TFrame")
            tv_wrap.pack(fill="both", expand=True, pady=(10, 0))
            self.tree = ttk.Treeview(tv_wrap, columns=CSV_COLUMNS, show="headings", height=12)
            widths = {"Document": 220, "Page": 50, "Source": 90, "Record": 60, "Field": 200, "Value": 380}
            for c in CSV_COLUMNS:
                self.tree.heading(c, text=c)
                self.tree.column(c, width=widths[c], anchor="w", stretch=(c == "Value"))
            vsb = ttk.Scrollbar(tv_wrap, orient="vertical", command=self.tree.yview)
            self.tree.configure(yscrollcommand=vsb.set)
            self.tree.pack(side="left", fill="both", expand=True)
            vsb.pack(side="right", fill="y")

        def do_extract(self):
            files = [f for f in self.ext_files if os.path.isfile(f)]
            dst = self.ext_out.get().strip()
            if not files:
                return messagebox.showwarning(APP_NAME, "No source PDFs found.\n\nGenerate them in Tab 1 or use 'Add PDFs…'.")

            def done(res):
                self.tree.delete(*self.tree.get_children())
                for i, r in enumerate(res["rows"]):
                    self.tree.insert("", "end", values=r, tags=("odd" if i % 2 else "even",))
                errs = [d for d in res["docs"] if "error" in d]
                self.ext_summary.configure(
                    text=f"{len(res['rows'])} records · {len(res['docs'])} file(s) · {res['tables']} tables"
                         f"{' · ' + str(len(errs)) + ' error(s)' if errs else ''}  →  {os.path.basename(res['path'])}")
                if errs:
                    messagebox.showwarning(APP_NAME, "Some files could not be read:\n\n" +
                                           "\n".join(f"{d['file']}: {d['error']}" for d in errs))
                if res["text_pages"] == 0:
                    messagebox.showinfo(APP_NAME, "These PDFs have no text layer (e.g. flattened redacted files "
                                                  "or scans), so nothing could be extracted. That is the expected "
                                                  "proof of a true redaction; use OCR if you need the visible text.")
                self.set_status(f"Working paper saved: {res['path']}")
            self.run_task(extract_to_csv, (files, dst), done, None)

        # ---------------- task runner ----------------
        def run_task(self, fn, args, on_done, log_widget, bar=None):
            if self.expired:
                return self._expired_msg()
            if self.busy:
                return messagebox.showinfo(APP_NAME, "A task is already running.")
            self.busy = True
            self._set_buttons(False)
            self.config(cursor="watch")

            def on_progress(frac, msg):
                if bar is not None:
                    bar["value"] = frac
                self.set_status(msg)

            def finish(res, err):
                self.busy = False
                self.config(cursor="")
                if not self.expired:
                    self._set_buttons(True)
                if err is not None:
                    self.set_status("Error")
                    if log_widget is not None:
                        self.log(log_widget, f"ERROR: {err}", "err")
                    messagebox.showerror(APP_NAME, f"{type(err).__name__}: {err}")
                else:
                    self.set_status("Completed")
                    on_done(res)

            def worker():
                try:
                    res = fn(*args, progress=lambda f, m: self.q.put((on_progress, (f, m))))
                    self.q.put((finish, (res, None)))
                except Exception as e:  # surfaced in UI
                    self.q.put((finish, (None, e)))
            threading.Thread(target=worker, daemon=True).start()

        def _poll_queue(self):
            try:
                while True:
                    func, args = self.q.get_nowait()
                    func(*args)
            except queue.Empty:
                pass
            self.after(80, self._poll_queue)

        def _set_buttons(self, enabled):
            for b in self.action_buttons:
                b.state(["!disabled"] if enabled else ["disabled"])

        def set_status(self, msg):
            self.status.set(msg)

        def _open(self, path):
            try:
                open_path(path)
            except FileNotFoundError:
                messagebox.showwarning(APP_NAME, f"Not found yet:\n{path}")
            except Exception as e:
                messagebox.showerror(APP_NAME, str(e))

        # ---------------- trial timer ----------------
        def _draw_timer(self):
            m, s = divmod(self.remaining, 60)
            warn = self.remaining <= 60
            if self.expired:
                self.timer_lbl.configure(text="Evaluation expired", fg="#fca5a5")
            else:
                self.timer_lbl.configure(text=f"Trial time left  {m:02d}:{s:02d}",
                                         fg="#fcd34d" if warn else "#bfdbfe")
            c = self.timer_bar
            c.delete("all")
            w = int(c["width"]) * self.remaining / TRIAL_SECONDS
            c.create_rectangle(0, 0, w, 4, fill="#f59e0b" if warn else "#60a5fa", width=0)

        def _tick(self):
            if self.remaining > 0:
                self.remaining -= 1
            if self.remaining == 0:
                self.expired = True
                self._draw_timer()
                self._set_buttons(False)
                self.set_status("Evaluation period ended - actions disabled")
                self._expired_msg()
                return
            self._draw_timer()
            self.after(1000, self._tick)

        def _expired_msg(self):
            mins = TRIAL_SECONDS // 60
            messagebox.showinfo(APP_NAME, f"The {mins}-minute evaluation period has ended.\n\n"
                                          "Restart the application to evaluate again, or activate an "
                                          "AOM Professional License for unrestricted use.")

        # ---------------- theming ----------------
        def toggle_theme(self):
            self.theme = "dark" if self.theme == "light" else "light"
            self.theme_btn.configure(text="☀  Light" if self.theme == "dark" else "☾  Dark")
            self.apply_theme()

        def apply_theme(self):
            p = PALETTES[self.theme]
            s = self.style
            self.configure(bg=p["bg"])
            s.configure(".", background=p["bg"], foreground=p["fg"], font=(FONT, 10),
                        fieldbackground=p["field"], bordercolor=p["border"], troughcolor=p["surface2"])
            s.configure("TFrame", background=p["bg"])
            s.configure("Card.TFrame", background=p["surface"], bordercolor=p["border"], relief="solid", borderwidth=1)
            s.configure("Status.TFrame", background=p["status_bg"])
            s.configure("TLabel", background=p["bg"], foreground=p["fg"])
            s.configure("Card.TLabel", background=p["surface"], foreground=p["fg"])
            s.configure("CardTitle.TLabel", background=p["surface"], foreground=p["title"], font=(FONT, 13, "bold"))
            s.configure("Muted.TLabel", background=p["surface"], foreground=p["muted"], font=(FONT, 9))
            s.configure("Status.TLabel", background=p["status_bg"], foreground=p["muted"], padding=(14, 5), font=(FONT, 9))
            s.configure("Callout.TLabel", background=p["callout_bg"], foreground=p["callout_fg"],
                        padding=10, font=(FONT, 9, "bold"))
            s.configure("TNotebook", background=p["bg"], borderwidth=0, tabmargins=(0, 4, 0, 0))
            s.configure("TNotebook.Tab", background=p["tab"], foreground=p["muted"], padding=(16, 9),
                        font=(FONT, 10, "bold"), borderwidth=0)
            s.map("TNotebook.Tab",
                  background=[("selected", p["surface"]), ("active", p["surface2"])],
                  foreground=[("selected", p["title"])])
            s.configure("Primary.TButton", background=PRIMARY, foreground="white", padding=(18, 9),
                        font=(FONT, 10, "bold"), borderwidth=0, focusthickness=0)
            s.map("Primary.TButton",
                  background=[("disabled", p["disabled"]), ("pressed", PRIMARY_DARK), ("active", PRIMARY_HOVER)],
                  foreground=[("disabled", p["muted"])])
            s.configure("Secondary.TButton", background=p["surface2"], foreground=p["fg"], padding=(14, 7),
                        borderwidth=1, bordercolor=p["border"], focusthickness=0)
            s.map("Secondary.TButton", background=[("active", p["border"])])
            s.configure("TEntry", fieldbackground=p["field"], foreground=p["fg"], insertcolor=p["fg"],
                        bordercolor=p["border"], lightcolor=p["border"], darkcolor=p["border"], padding=6)
            s.map("TEntry", bordercolor=[("focus", PRIMARY_HOVER)], lightcolor=[("focus", PRIMARY_HOVER)])
            s.configure("TSpinbox", fieldbackground=p["field"], foreground=p["fg"], background=p["surface2"],
                        arrowcolor=p["fg"], bordercolor=p["border"], padding=4)
            s.map("TSpinbox", fieldbackground=[("readonly", p["field"])], foreground=[("readonly", p["fg"])])
            s.configure("Card.TCheckbutton", background=p["surface"], foreground=p["fg"], font=(FONT, 10),
                        indicatorbackground=p["field"], indicatorforeground="white")
            s.map("Card.TCheckbutton", background=[("active", p["surface"])],
                  indicatorbackground=[("selected", PRIMARY), ("!selected", p["field"])])
            s.configure("Treeview", background=p["field"], fieldbackground=p["field"], foreground=p["fg"],
                        rowheight=24, bordercolor=p["border"], font=(FONT, 9))
            s.configure("Treeview.Heading", background=PRIMARY, foreground="white", font=(FONT, 9, "bold"),
                        relief="flat", padding=6)
            s.map("Treeview", background=[("selected", PRIMARY_HOVER)], foreground=[("selected", "white")])
            s.map("Treeview.Heading", background=[("active", PRIMARY_HOVER)])
            s.configure("Horizontal.TProgressbar", troughcolor=p["surface2"], background=PRIMARY,
                        bordercolor=p["border"], lightcolor=PRIMARY, darkcolor=PRIMARY, thickness=8)
            s.configure("Vertical.TScrollbar", background=p["surface2"], troughcolor=p["surface"],
                        bordercolor=p["surface"], arrowcolor=p["muted"])
            self.tree.tag_configure("odd", background=p["log_bg"])
            self.tree.tag_configure("even", background=p["field"])
            for lb in self.listboxes:
                lb.configure(bg=p["log_bg"], fg=p["fg"], selectbackground=PRIMARY_HOVER,
                             selectforeground="white", highlightbackground=p["border"],
                             highlightcolor=p["border"])
            for t in self.logs:
                t.configure(bg=p["log_bg"], fg=p["fg"], insertbackground=p["fg"],
                            selectbackground=PRIMARY_HOVER, highlightbackground=p["border"],
                            highlightcolor=p["border"])
                t.tag_configure("ok", foreground=p["ok"])
                t.tag_configure("warn", foreground=p["warn"])
                t.tag_configure("err", foreground=p["err"])
                t.tag_configure("muted", foreground=p["muted"])
                t.tag_configure("head", foreground=p["title"], font=(MONO, 9, "bold"))

    return AuditApp


# --------------------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------------------
def selftest():
    pr = lambda f, m: None  # noqa: E731
    gen = generate_batch(BASE_DIR, MAX_DOCS, pr)
    print(f"Generated {len(gen)} vouchers")
    files = [g["path"] for g in gen]
    red = redact_batch(files, BASE_DIR, list(PII_CATEGORIES), progress=pr)
    good = 0
    for r in red:
        if "error" in r:
            print("  ERROR", r["src"], r["error"])
            continue
        clean = r["residual_chars"] == 0 and r["fonts"] == 0 and sum(r["counts"].values()) >= 6
        good += clean
        print(f"  {os.path.basename(r['path']):<34} areas={sum(r['counts'].values()):>2} "
              f"residual={r['residual_chars']} fonts={r['fonts']} {'OK' if clean else 'CHECK'}")
    ext = extract_to_csv(files, os.path.join(BASE_DIR, WORKING_PAPER_CSV), pr)
    print(f"Extracted {len(ext['rows'])} records from {len(ext['docs'])} files -> {ext['path']}")
    ok = good == len(files) and len(ext["rows"]) > 0
    print("SELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1



def main():
    try:  # crisp rendering on Windows high-DPI screens
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    splash = None
    if "--selftest" not in sys.argv and (_try_import_pymupdf() is None or not _has_reportlab()):
        try:
            import tkinter as _tk
            splash = _tk.Tk()
            splash.title(APP_NAME)
            splash.configure(bg=PRIMARY)
            splash.geometry("420x120")
            _tk.Label(splash, text="Installing required components (PyMuPDF, reportlab)…\n"
                                   "First run only. This can take a minute.",
                      bg=PRIMARY, fg="white", font=("Segoe UI", 10), justify="center").pack(expand=True)
            splash.update()
        except Exception:
            splash = None

    failures = load_dependencies()
    if splash is not None:
        try:
            splash.destroy()
        except Exception:
            pass
    if "--selftest" in sys.argv:
        if failures:
            print("Missing packages:", failures)
            for k, v in IMPORT_ERRORS.items():
                print(f"  {k} is installed but failed to load -> {v}")
            return 1
        return selftest()

    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        print("Tkinter is not available in this Python installation. "
              "Install the python3-tk package (Linux) or use the python.org installer.")
        return 1

    blocked = {k: v for k, v in IMPORT_ERRORS.items() if k in failures}
    if blocked:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(APP_NAME, "Required packages are installed but Windows could not load them:\n\n" +
                             "\n".join(f"{k}: {v[:200]}" for k, v in blocked.items()) +
                             "\n\nThis is usually Smart App Control or antivirus blocking an unsigned "
                             "component (e.g. _extra.pyd). Allow it in Windows Security > App & browser "
                             "control, or run the app on a machine without that restriction.")
        root.destroy()
        return 1

    if failures:
        root = tk.Tk()
        root.withdraw()
        py = "py" if sys.platform.startswith("win") else os.path.basename(console_python())
        detail = ""
        if PIP_ERROR:
            tail = [ln for ln in PIP_ERROR.strip().splitlines() if ln.strip()][-4:]
            detail = "\n\npip reported:\n" + "\n".join(t[:140] for t in tail)
        messagebox.showerror(APP_NAME, "Could not install required packages: " + ", ".join(failures) +
                             "\n\nOpen Command Prompt and run:\n\n"
                             f"    {py} -m pip install " + " ".join(failures) +
                             "\n\nthen start the app again." + detail)
        root.destroy()
        return 1

    App = build_app()
    App().mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
