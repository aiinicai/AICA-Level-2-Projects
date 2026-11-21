"""
Net Asset Report — legacy export engine  (desktop app for Chartered Accountants)
-----------------------------------------------------------------------
- Enter applicant details
- Add assets by type
- Generates the "Independent Practitioner's Certificate on Net Assets"
- Integrated UDIN Generation via Selenium Automation (Auto Form Fill)
- Live Exchange Rate Fetching
- Smart Date Syncing (Universal)
- Multi-CA Profile Manager
- Local PDF/JPEG document intake with review before importing

Install Python dependencies:
    pip install openpyxl python-docx reportlab pillow selenium pymupdf

For OCR of JPEGs/scanned PDF pages, install Tesseract OCR for Windows separately.
"""

import os
import sys
import json
import math
import re
import time
import datetime
import subprocess
from runtime_io import run_hidden
import threading
import urllib.request
import webbrowser
import tempfile
import traceback
import shutil
import platform
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "Net Asset Report"
HERE = os.path.dirname(os.path.abspath(__file__))
PROFILES_FILE = os.path.join(os.path.expanduser("~"), ".networth_ca_profiles.json")
OCR_SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".networth_ocr_settings.json")


CURRENCIES = [
    "None",
    "AUD - Australian Dollars",
    "CAD - Canadian Dollars",
    "USD - US Dollars",
    "GBP - British Pounds",
    "NZD - New Zealand Dollars",
    "EUR - Euros",
    "SGD - Singapore Dollars",
    "AED - UAE Dirhams",
]

RELATIONS = ["Self", "Father", "Mother", "Parents", "Spouse", "Husband", "Wife",
             "Brother", "Sister", "Son", "Daughter", "Grandfather", "Grandmother",
             "Father-in-law", "Mother-in-law"]

SECTION_LABELS = {"A": "A - Non-Current", "B": "B - Current", "C": "C - Liability"}


# ======================================================================
# Number & Date Helpers
# ======================================================================
def format_smart_date(d_str, sep="."):
    raw = re.sub(r'\D', '', d_str)
    if not raw:
        return d_str
    if len(raw) == 4:
        raw += str(datetime.date.today().year)
    elif len(raw) == 6:
        raw = raw[:4] + "20" + raw[4:]
    
    if len(raw) == 8:
        return f"{raw[:2]}{sep}{raw[2:4]}{sep}{raw[4:]}"
    return d_str

_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
         "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
         "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two(n):
    if n < 20:
        return _ONES[n]
    return _TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")


def _three(n):
    h, r = divmod(n, 100)
    parts = []
    if h:
        parts.append(_ONES[h] + " Hundred")
    if r:
        parts.append(_two(r))
    return " ".join(parts)


def indian_words(n):
    n = int(n)
    if n == 0:
        return "Zero"
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, n = divmod(n, 1000)
    parts = []
    if crore:
        parts.append(indian_words(crore) + " Crore")
    if lakh:
        parts.append(_two(lakh) + " Lakh")
    if thousand:
        parts.append(_two(thousand) + " Thousand")
    if n:
        parts.append(_three(n))
    return " ".join(parts)


def intl_words(n):
    n = int(n)
    if n == 0:
        return "Zero"
    parts = []
    for value, name in ((10 ** 12, "Trillion"), (10 ** 9, "Billion"),
                        (10 ** 6, "Million"), (1000, "Thousand")):
        q, n = divmod(n, value)
        if q:
            parts.append((intl_words(q) if q >= 1000 else _three(q)) + " " + name)
    if n:
        parts.append(_three(n))
    return ", ".join(parts)


def fmt_inr(x):
    neg = x < 0
    whole, dec = f"{abs(x):.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups) + "," + tail
    return ("-" if neg else "") + whole + "." + dec


def fmt_acct(x):
    if abs(x) < 0.005:
        return "-"
    return f"{x:,.2f}" if x > 0 else f"({abs(x):,.2f})"


BOLD_ON, BOLD_OFF = "\x01", "\x02"


def mark(text, bold=True):
    return f"{BOLD_ON}{text}{BOLD_OFF}" if bold and text else text


def strip_marks(text):
    return (text or "").replace(BOLD_ON, "").replace(BOLD_OFF, "")


def segments(text):
    out, buf, bold = [], "", False
    for ch in text or "":
        if ch in (BOLD_ON, BOLD_OFF):
            if buf:
                out.append((buf, bold))
            buf, bold = "", ch == BOLD_ON
        else:
            buf += ch
    if buf:
        out.append((buf, bold))
    return out


def parse_amount(text):
    text = (text or "").replace(",", "").replace("Rs.", "").replace("₹", "").replace("Fetching...", "").strip()
    return float(text) if text else 0.0


# ======================================================================
# Asset / liability categories
# ======================================================================
def _v(f, k):
    value = (f.get(k) or "").strip() or "________"
    return mark(value, f.get("_bold", {}).get(k, False))


def _held(f, prefix="held in the name of"):
    holder = _v(f, "holder")
    rel = f.get("relation") or "Self"
    if rel == "Self":
        return f"{prefix} {holder} (Applicant)"
    if 'Applicant' in rel or 'not confirmed' in rel.lower():
        return f"{prefix} {holder} ({_v(f, 'relation')})"
    return f"{prefix} {holder} ({_v(f, 'relation')} of Applicant)"


BANK_NOTE = "(As per signed Bank Statement by the bank's authorized signatory)"

HOLDER_FIELDS = [("holder", "Held in the name of", "text", None),
                 ("relation", "Relation with applicant", "relation", None)]

CATS = {
    "Immovable Property": dict(
        kind="asset", section="A",
        fields=[("nature", "Nature of property", "combo",
                 ["Agriculture Land", "Residential House", "Residential Flat", "Residential Plot", "Vacant Plot",
                  "Commercial Property", "Shop", "Industrial Property"])]
        + HOLDER_FIELDS +
        [("location", "Located at (full address)", "text", None),
         ("valuer", "Valuer (issued by)", "text", None),
         ("val_date", "Valuation report date", "text", None)],
        desc=lambda f: f"Immovable Property in the nature of {_v(f, 'nature')} {_held(f)}, "
                       f"located at {_v(f, 'location')}.",
        note=lambda f: "(Valuation is based on Valuation Report of the abovesaid immovable property "
                       f"produced to me by the applicant, as issued by {_v(f, 'valuer')}, "
                       f"dated {_v(f, 'val_date')})"),

    "Jewellery": dict(
        kind="asset", section="A",
        fields=[("details", "Jewellery details", "combo",
                 ["Gold Ornaments weighing ____ grams", "Gold & Diamond Ornaments weighing ____ grams",
                  "Silver Ornaments weighing ____ grams"])]
        + HOLDER_FIELDS +
        [("valuer", "Valuer (issued by)", "text", None),
         ("val_date", "Valuation report date", "text", None)],
        desc=lambda f: f"Jewellery in the nature of {_v(f, 'details')}, {_held(f)}.",
        note=lambda f: "(Valuation is based on Valuation Report of the abovesaid jewellery produced "
                       f"to me by the applicant, as issued by {_v(f, 'valuer')}, dated {_v(f, 'val_date')})"),

    "Bank Account (Savings / Current)": dict(
        kind="asset", section="B",
        fields=[("acc_type", "Account type", "combo", ["Saving", "Current"]),
                ("acno", "Account number", "text", None),
                ("as_on", "Balance as on (date)", "text", None),
                ("bank", "Bank name", "text", None)] + HOLDER_FIELDS,
        desc=lambda f: f"{_v(f, 'acc_type')} Account Balance (A/c No. {_v(f, 'acno')}) as on "
                       f"{_v(f, 'as_on')} with {_v(f, 'bank')}, {_held(f)}.",
        note=lambda f: BANK_NOTE),

    "Fixed Deposit": dict(
        kind="asset", section="B",
        fields=[("acno", "FD account number", "text", None),
                ("as_on", "Balance as on (date)", "text", None),
                ("bank", "Bank name", "text", None)] + HOLDER_FIELDS,
        desc=lambda f: f"Fixed Deposit Account Balance (A/c No. {_v(f, 'acno')}) as on "
                       f"{_v(f, 'as_on')} with {_v(f, 'bank')}, {_held(f)}.",
        note=lambda f: BANK_NOTE),

    "Vehicle": dict(
        kind="asset", section="B",
        fields=[("vtype", "Vehicle type", "combo", ["Car", "Motorcycle", "Scooter", "Tractor", "Truck"])]
        + HOLDER_FIELDS +
        [("vno", "Vehicle number", "text", None),
         ("reg_date", "Date of registration", "text", None),
         ("basis", "Valuation basis", "combo",
          ["Approximate Market Value (no valuation report)", "Valuation Report"]),
         ("val_date", "Value as on / report date", "text", None),
         ("valuer", "Valuer (only if valuation report)", "text", None)],
        desc=lambda f: f"Vehicle ({_v(f, 'vtype')}), {_held(f)}, Vehicle Number - {_v(f, 'vno')}, "
                       f"date of registration being {_v(f, 'reg_date')}.",
        note=lambda f: (f"(Valuation is based on Valuation Report of the abovesaid vehicle produced to me "
                        f"by the applicant, as issued by {_v(f, 'valuer')}, dated {_v(f, 'val_date')})")
        if (f.get("basis") or "").startswith("Valuation")
        else (f"(Valuation is based on Approximate Market Value as on {_v(f, 'val_date')} as provided "
              "to me by the applicant. No valuation Report has been provided to me, hence I don’t "
              "certify the correctness of the same)")),

    "Shares / Mutual Funds": dict(
        kind="asset", section="A",
        fields=[("itype", "Investment type", "combo",
                 ["Shares", "Mutual Funds", "Shares & Mutual Funds", "Bonds / Debentures"]),
                ("account", "Demat A/c / Folio No.", "text", None),
                ("dp", "Depository / AMC / Broker", "text", None),
                ("as_on", "Value as on (date)", "text", None)] + HOLDER_FIELDS,
        desc=lambda f: f"Investment in {_v(f, 'itype')} held in Demat A/c / Folio No. {_v(f, 'account')} "
                       f"with {_v(f, 'dp')} as on {_v(f, 'as_on')}, {_held(f)}.",
        note=lambda f: f"(Valuation is based on market value as per Statement of Holdings issued by "
                       f"{_v(f, 'dp')} as on {_v(f, 'as_on')})"),

    "PPF / NSC / Post Office": dict(
        kind="asset", section="A",
        fields=[("scheme", "Scheme", "combo",
                 ["Public Provident Fund (PPF)", "National Savings Certificate (NSC)",
                  "Kisan Vikas Patra (KVP)", "Post Office Deposit", "Sukanya Samriddhi Account"]),
                ("acno", "Account / Certificate No.", "text", None),
                ("as_on", "Balance as on (date)", "text", None),
                ("inst", "Bank / Post Office", "text", None)] + HOLDER_FIELDS,
        desc=lambda f: f"{_v(f, 'scheme')} Balance (A/c No. {_v(f, 'acno')}) as on {_v(f, 'as_on')} "
                       f"with {_v(f, 'inst')}, {_held(f)}.",
        note=lambda f: f"(As per Passbook / Statement issued by {_v(f, 'inst')})"),

    "Life Insurance (Surrender Value)": dict(
        kind="asset", section="A",
        fields=[("pno", "Policy number", "text", None),
                ("insurer", "Insurer", "text", None),
                ("as_on", "Surrender value as on", "text", None)] + HOLDER_FIELDS,
        desc=lambda f: f"Surrender Value of Life Insurance Policy (Policy No. {_v(f, 'pno')}) with "
                       f"{_v(f, 'insurer')} as on {_v(f, 'as_on')}, {_held(f)}.",
        note=lambda f: f"(As per Surrender Value Certificate issued by {_v(f, 'insurer')})"),

    "Other Asset": dict(kind="asset", section="B", fields=[], desc=None, note=None),

    "Cash in Hand": dict(
        kind="asset", section="B", fields=[], desc=None, note=None),

    "Bank Loan": dict(
        kind="liability", section="C",
        fields=[("ltype", "Loan type", "combo",
                 ["Home", "Car", "Education", "Personal", "Gold", "Agriculture", "Business",
                  "Kisan Credit Card (KCC)", "Loan Against Property"]),
                ("acno", "Loan account number", "text", None),
                ("as_on", "Outstanding as on (date)", "text", None),
                ("bank", "Bank / NBFC", "text", None)] + HOLDER_FIELDS,
        desc=lambda f: f"{_v(f, 'ltype')} Loan (A/c No. {_v(f, 'acno')}) outstanding as on "
                       f"{_v(f, 'as_on')} with {_v(f, 'bank')}, {_held(f, 'in the name of')}.",
        note=lambda f: "(As per Loan Account Statement issued by the bank)"),

    "Credit Card": dict(
        kind="liability", section="C",
        fields=[("card", "Card number (last 4 digits)", "text", None),
                ("as_on", "Outstanding as on (date)", "text", None),
                ("bank", "Card issuer", "text", None)] + HOLDER_FIELDS,
        desc=lambda f: f"Credit Card Outstanding (Card No. XXXX-XXXX-XXXX-{_v(f, 'card')}) as on "
                       f"{_v(f, 'as_on')} with {_v(f, 'bank')}, {_held(f, 'in the name of')}.",
        note=lambda f: "(As per Credit Card Statement issued by the bank)"),

    "Other Liability": dict(kind="liability", section="C", fields=[], desc=None, note=None),
}

ASSET_CATS = [k for k, v in CATS.items() if v["kind"] == "asset"]
LIAB_CATS = [k for k, v in CATS.items() if v["kind"] == "liability"]


# ======================================================================
# Certificate content (shared by Excel / Word / PDF)
# ======================================================================
PROCEDURES = [
    ("a)", "Obtained documents viz. original deeds / valuation report to verify the value of property "
           "(residential flat/ commercial property, i.e. immoveable property) forming part of the net assets."),
    ("b)", "Obtained invoices and bank statements to verify the value of movable property."),
    ("c)", "Obtained bank statements to verify the bank balances in savings/ current accounts, fixed deposits."),
    ("d)", "Obtained demat statement of the depository, to verify the investments held in the nature of "
           "the shares / mutual funds."),
    ("e)", "Obtained valuation report of the Jewellery mentioned in the statement, to verify the value of the same."),
    ("f)", "Obtained the loan statements to verify the loan from Bank including mortgage, forming part of liabilities."),
    ("g)", "Obtained the Credit Card balance statements to verify the credit card related liability."),
    ("h)", "We have obtained confirmations from the parties mentioned in the loan given to (assets)/ "
           "loan taken from (liabilities), in the statement."),
    ("i)", "Performed necessary inquiries with the Individual and obtained necessary clarification, "
           "from the individual."),
]


def build_content(d):
    a, s = d["app"], d["settings"]
    female = a["title"] in ("Ms.", "Mrs.", "Miss")
    his, him = ("her", "her") if female else ("his", "him")
    bolds = a.get("_bold", {})

    def A(k):
        return mark(a.get(k, ""), bolds.get(k, False))

    T = f"{A('title')} {A('name')}".strip()
    co_title = a.get("co_title", "")
    co_name = a.get("co_name", "").strip()
    co_full = mark(f"{co_title} {co_name}".strip(), True)
    co_parent = f", {a.get('co_relation') or 'S/o'} {a.get('co_parent')}" if a.get("co_parent") else ""
    co_passport = f", bearing Passport No. {a.get('co_passport')}" if a.get("co_passport") else ""
    co_address = f", residing at {a.get('co_address')}" if a.get("co_address") else ""
    parties = (f"{T} and {co_full} (Co-applicant){co_parent}{co_passport}{co_address}"
               if co_name else T)
    stmt = A("statement_date")

    parent = f", {A('relation')} {A('parent')}" if a.get("parent") else ""
    passport = f", bearing Passport No. {A('passport')}" if a.get("passport") else ""
    address = f", residing at {A('address')}" if a.get("address") else ""

    secs = {"A": [], "B": [], "C": []}
    for it in d["items"]:
        secs[it["section"]].append(it)
    tot = {k: round(sum(i["amount"] for i in v), 2) for k, v in secs.items()}
    nw = round(tot["A"] + tot["B"] - tot["C"], 2)

    neg = " (Negative)" if nw < 0 else ""
    words = [f"Net Assets of the applicant(s) are Rs. {fmt_inr(nw)}/- (Indian Rupees "
             f"{indian_words(abs(nw))}{neg} Approximately)"]
    cur = a.get("currency", "None")
    rate = parse_amount(a.get("rate", ""))
    fx_value = None
    if cur != "None" and rate > 0:
        code, cname = cur.split(" - ", 1)
        fx_value = nw / rate
        words.append(f"Net Assets of the applicant(s) are {code} {abs(fx_value):,.2f}/- "
                     f"({intl_words(abs(fx_value))} {cname}{neg} Approximately)")

    return dict(
        settings=s, app=a, his=his, totals=tot, nw=nw, fx_value=fx_value,
        title="INDEPENDENT PRACTITIONER’S CERTIFICATE ON NET ASSETS",
        intro=[
            f"This Report is issued in accordance with the terms of our engagement letter/ agreement dated "
            f"{A('engagement_date')}",
            f'We have been requested by {parties} ("Applicant(s)"){parent}{passport}{address}, to issue a Certificate '
            f"on the net assets of the Applicant(s).",
            f"The accompanying Statement of Net Assets as at {stmt} (the “Statement”) of {parties}, "
            f"as prepared by the Applicant(s), contains the details of their assets and liabilities for submission "
            f"to {A('authority')} in connection with {A('purpose')}.",
            "The Statement has been initialled by us for identification purposes only.",
        ],
        summary=[("1", "Non Current Investments (Annexure - A)", tot["A"], "A"),
                 ("2", "Current Investments (Annexure - B)", tot["B"], "B"),
                 ("3", "Less : Total Liabilities (Annexure - C)", tot["C"], "C")],
        words=words,
        date_line=f"DATE : {A('cert_date')}",
        udin_line=f"UDIN: {A('udin')}",
        resp_head="INDIVIDUAL'S RESPONSIBILITY FOR THE STATEMENT",
        resp=[
            f"The preparation of the accompanying Statement is the responsibility of the applicant {T}, "
            "including the maintenance of all relevant supporting records and documents. This responsibility "
            "also includes the design, implementation and maintenance of internal control relevant to the "
            "preparation and presentation of the Statement and applying an appropriate basis of preparation; "
            "and making estimates that are reasonable in the circumstances.",
            f"The applicant is also responsible for submitting all the details including the original deeds, "
            f"documents, records of {his} assets and liabilities as at {stmt}.",
        ],
        prac_head="PRACTITIONER'S RESPONSIBILITY FOR THE STATEMENT",
        prac=[
            "Pursuant to the requirements of visa application, it is our responsibility to provide limited "
            "assurance as to whether the Statement presented to us is in agreement with the details referred "
            f"in original deeds, documents, records of {his} assets and liabilities etc.",
            "The procedures performed in a limited assurance engagement vary in nature and timing from, and "
            "are less in extent than for, a reasonable assurance engagement; and consequently, the level of "
            "assurance obtained in a limited assurance engagement is substantially lower than the assurance "
            "that would have been obtained had a reasonable assurance engagement been performed.",
            "Accordingly, we have performed the following procedures in relation to the Statement presented "
            "to us as were considered appropriate in the circumstances, including verification of relevant "
            "supporting documents and records as applicable and enumerated in the Detailed Net Asset "
            "Statement of Applicant :",
        ],
        procedures=PROCEDURES,
        relied="We have relied upon the information and supporting details furnished in substantiation of "
               "the statement.",
        standards=[
            "We have conducted our examination of the Statement in accordance with the Guidance Note on "
            "Reports or Certificates for Special Purposes (Revised 2016) issued by the Institute of Chartered "
            "Accountants of India (“ICAI”). The Guidance Note requires that we comply with the ethical "
            "requirements of the Code of Ethics issued by the ICAI.",
            "We have complied with the relevant applicable requirements of the Standard on Quality Control "
            "(SQC) 1, Quality Control for Firms that Perform Audits and Reviews of Historical Financial "
            "Information, and Other Assurance and Related Services Engagements.",
            "The Income Details referred in the Certificate (if any) have been compiled from the Income Tax "
            "Returns filed by the applicant. We categorically state that we haven't verified the financials "
            "of the client, nor have we audited or reviewed them. Our scope is just to report the figures as "
            "filed on Income Tax Portal.",
        ],
        concl_head="CONCLUSION",
        concl="Based on the procedures carried out as mentioned above, and according to the information and "
              "explanations given to us, nothing has come to our attention that causes us to believe that the "
              "particulars mentioned in the Statement, which is prepared by the applicant and initialled by us "
              "for identification purpose, is not in accordance with the documentary evidence made available "
              f"for verification as set out in original deeds, documents, records of {his} assets and "
              "liabilities etc.",
        restr_head="RESTRICTION ON USE",
        restr="This Certificate has been issued at the request of the applicant solely for the purpose of "
              "submission to immigration or embassy for visa application purposes. This Certificate should not "
              "be used for any other purpose or by any person other than the addressee of this Certificate. "
              "Accordingly, we do not accept or assume any liability or any duty of care for any other purpose "
              "or to any other person to whom this Certificate is shown or into whose hands it may come "
              "without our prior consent in writing.",
        enclosure="Enclosure: Detailed Statement of Net Assets of the applicant(s)",
        detail_title="DETAILED COMPUTATION OF NET ASSETS OF THE APPLICANT(S)",
        sections=[
            ("A", "", "(A) NON-CURRENT INVESTMENTS", secs["A"], "TOTAL (A) :", tot["A"]),
            ("B", "", "(B) CURRENT INVESTMENTS", secs["B"], "TOTAL (B) :", tot["B"]),
            ("C", "Less: ", "(C) LIABILITIES", secs["C"], "TOTAL (C) :", tot["C"]),
        ],
        signature=[f"FOR {s['firm_name']}", s["firm_type"], f"FRN NO. {s['frn']}"],
        signatory=[s["partner"], f"({s['designation']})", f"M. NO. {s['mno']}"],
        place=f"PLACE: {s['place']}",
    )


def logo_file(s):
    p = s.get("logo_path") or ""
    return p if p and os.path.isfile(p) else None


# ======================================================================
# Excel export 
# ======================================================================
def export_excel(c, path):
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side
    from openpyxl.worksheet.pagebreak import Break
    from openpyxl.worksheet.properties import PageSetupProperties
    from openpyxl.cell.rich_text import CellRichText, TextBlock
    from openpyxl.cell.text import InlineFont

    ACCT = '_(* #,##0.00_);_(* \\(#,##0.00\\);_(* "-"??_);_(@_)'
    WIDTHS = dict(A=13.43, B=5.86, C=8.71, D=7.86, E=9.71, F=7.86, G=21.14, H=23.43, I=27.29, J=30.86)
    COLS = "ABCDEFGHIJ"
    s = c["settings"]

    wb = Workbook()
    ws = wb.active
    ws.title = "Net Asset Report"
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 60
    for k, w in WIDTHS.items():
        ws.column_dimensions[k].width = w

    thin, medium, double = Side(style="thin"), Side(style="medium"), Side(style="double")

    def F(size=16, bold=False, ul=False):
        return Font(name="Arial", size=size, bold=bold, underline="single" if ul else None)

    def put(row, col, text, size=16, bold=False, ul=False):
        cell = ws.cell(row, col)
        segs = segments(text)
        if not bold and any(b_ for _t, b_ in segs):
            cell.value = CellRichText([TextBlock(InlineFont(rFont="Arial", sz=size, b=b_,
                                                            u="single" if ul else None), t_)
                                       for t_, b_ in segs])
        else:
            cell.value = strip_marks(text)
        cell.font = F(size, bold, ul)
        return cell

    class St:
        r = 1
        used = 0.0

    PAGE_LIMIT = 1240.0

    def height(h):
        ws.row_dimensions[St.r].height = h
        St.used += h

    def nxt(h=20.25):
        height(h)
        St.r += 1

    def need(h):
        if St.used + h > PAGE_LIMIT:
            page_break()

    def page_break():
        ws.row_breaks.append(Break(id=St.r - 1))
        St.used = 0
        letterhead()

    def letterhead():
        start = St.r
        rows = [(s["firm_name"], 28, True, True, 35.25), (s["firm_type"], 28, True, True, 34.5),
                (None, 0, False, False, 12), (s["address1"], 20, False, False, 25.5),
                (s["address2"], 20, False, False, 25.5), ("Email: " + s["email"], 20, True, False, 26.25),
                ("Contact: " + s["contact"], 20, True, False, 26.25)]
        for text, size, b, u, h in rows:
            if text:
                cell = ws.cell(St.r, 10, text)
                cell.font = F(size, b, u)
                cell.alignment = Alignment(horizontal="right", vertical="center")
            nxt(h)
        for col in range(1, 11):
            ws.cell(St.r - 1, col).border = Border(bottom=medium)
        lg = logo_file(s)
        if lg:
            try:
                from openpyxl.drawing.image import Image as XLImage
                img = XLImage(lg)
                ratio = 140 / img.height
                img.height, img.width = 140, int(img.width * ratio)
                img.anchor = f"A{start + 1}"
                ws.add_image(img)
            except Exception:
                pass
        nxt(20)

    def cpl(first, last, size, bold):
        width = sum(WIDTHS[COLS[i]] for i in range(COLS.index(first), COLS.index(last) + 1))
        return width * 0.70 * 16 / size * (0.92 if bold else 1)

    def est_height(text, first, last, size, bold):
        per = cpl(first, last, size, bold)
        lines = sum(max(1, math.ceil(len(seg) * 1.02 / per)) for seg in strip_marks(text).split("\n"))
        return min(409, lines * size * 1.35 + 4)

    def box(row, c1, c2, top=thin, bottom=thin, left=thin, right=thin):
        i1, i2 = COLS.index(c1) + 1, COLS.index(c2) + 1
        for col in range(i1, i2 + 1):
            ws.cell(row, col).border = Border(top=top, bottom=bottom,
                                              left=left if col == i1 else None,
                                              right=right if col == i2 else None)

    def para(text, num=None, bold=False, size=16, ul=False, first="B", last="J",
             align="justify", gap=True, keep_extra=0):
        h = est_height(text, first, last, size, bold)
        need(h + keep_extra)
        if num is not None:
            cell = ws.cell(St.r, 1, num)
            cell.font = F(16, True)
            cell.alignment = Alignment(horizontal="center", vertical="top")
        cell = put(St.r, COLS.index(first) + 1, text, size, bold, ul)
        cell.alignment = Alignment(horizontal=align, vertical="top", wrap_text=True)
        if first != last:
            ws.merge_cells(f"{first}{St.r}:{last}{St.r}")
        nxt(h)
        if gap:
            nxt(12)

    def date_udin(left, right, size=16):
        need(22)
        put(St.r, 1, left, size, True)
        put(St.r, 9, right, size, True)
        nxt()

    def signature(size=16):
        need(15 * 22)
        for t in c["signature"]:
            ws.cell(St.r, 2, t).font = F(size, True)
            nxt(21)
        for _ in range(4):
            nxt(21)
        for t in c["signatory"]:
            ws.cell(St.r, 2, t).font = F(size, True)
            nxt(21)
        nxt()
        put(St.r, 2, c["udin_line"], size, True)
        put(St.r, 9, c["date_line"], size, True)
        nxt(21)
        ws.cell(St.r, 2, c["place"]).font = F(size, True)
        nxt(21)

    if s.get("letterhead_first_page", True):
        letterhead()
    else:
        for _ in range(9):
            nxt(21)
    para(c["title"], bold=True, size=18, ul=True, first="A", last="J", align="center")
    for n, t in enumerate(c["intro"], 1):
        para(t, num=n)
    para("NET ASSET REPORT", bold=True, size=20, ul=True, first="A", last="J",
         align="center", gap=False)
    for col in range(1, 11):
        ws.cell(St.r - 1, col).border = Border(top=medium, bottom=medium)

    r = St.r
    ws.cell(r, 1, "S. No.").font = F(16, True)
    ws.cell(r, 1).alignment = Alignment(horizontal="center")
    ws.cell(r, 2, "PARTICULARS").font = F(16, True)
    ws.merge_cells(f"B{r}:I{r}")
    ws.cell(r, 10, "AMOUNT (in Rs.)").font = F(16, True)
    ws.cell(r, 10).alignment = Alignment(horizontal="center")
    box(r, "A", "A"); box(r, "B", "I", top=medium); box(r, "J", "J")
    nxt(21)
    summary_rows = {}
    for num, label, _amt, key in c["summary"]:
        r = St.r
        ws.cell(r, 1, int(num)).font = F(16, num == "1")
        ws.cell(r, 1).alignment = Alignment(horizontal="center")
        ws.cell(r, 2, label).font = F(16)
        ws.merge_cells(f"B{r}:I{r}")
        cell = ws.cell(r, 10)
        cell.font = F(16)
        cell.number_format = ACCT
        box(r, "A", "A"); box(r, "B", "I"); box(r, "J", "J")
        summary_rows[key] = r
        nxt(24)
    r = St.r
    ws.cell(r, 2, "Net Assets of the Applicant(s) (1+2-3)").font = F(18, True)
    ws.cell(r, 2).alignment = Alignment(horizontal="right")
    ws.merge_cells(f"B{r}:I{r}")
    cell = ws.cell(r, 10, f"=J{summary_rows['A']}+J{summary_rows['B']}"+(f"-J{summary_rows['C']}" if 'C' in summary_rows else ''))
    cell.font = F(18, True)
    cell.number_format = ACCT
    box(r, "A", "A", bottom=medium); box(r, "B", "I", bottom=medium); box(r, "J", "J", bottom=medium)
    nxt(24)
    nxt()
    for w in c["words"]:
        para(w, bold=True, first="A", last="J")
    nxt()
    date_udin(c["date_line"], c["udin_line"])

    page_break()
    para(c["resp_head"], num=5, bold=True, ul=True, align="left")
    para(c["resp"][0])
    para(c["resp"][1], bold=True)
    para(c["prac_head"], num=6, bold=True, ul=True, align="left")
    for t in c["prac"]:
        para(t)
    for lbl, t in c["procedures"]:
        para(f"{lbl} {t}", gap=False)
    nxt(12)
    para(c["relied"])
    date_udin(c["date_line"], c["udin_line"])

    page_break()
    for t in c["standards"]:
        para(t)
    para(c["concl_head"], num=7, bold=True, ul=True, align="left")
    para(c["concl"])
    para(c["restr_head"], num=8, bold=True, ul=True, align="left")
    para(c["restr"])
    signature()
    nxt()
    nxt()
    ws.cell(St.r, 2, c["enclosure"]).font = F(16)
    nxt()

    page_break()
    para("DETAILED COMPUTATION OF NET-WORTH OF \nTHE APPLICANT", bold=True, size=22, ul=True,
         first="A", last="J", align="center")
    r = St.r
    ws.cell(r, 1, "S.No.").font = F(16, True)
    ws.cell(r, 1).alignment = Alignment(horizontal="center")
    ws.cell(r, 2, "Particulars").font = F(16, True)
    ws.merge_cells(f"B{r}:I{r}")
    ws.cell(r, 10, "Amount (in Rs.)").font = F(16, True)
    ws.cell(r, 10).alignment = Alignment(horizontal="center")
    box(r, "A", "A"); box(r, "B", "I"); box(r, "J", "J")
    nxt(21)
    nxt()

    total_rows = {}
    for key, prefix, head, items, total_lbl, _tot in c["sections"]:
        need(70)
        if prefix:
            ws.cell(St.r, 1, prefix).font = F(16, True)
        ws.cell(St.r, 2, head).font = F(16, True, True)
        nxt()
        nxt()
        first_row = St.r
        if not items:
            ws.cell(St.r, 2, "NIL").font = F(16)
            cell = ws.cell(St.r, 10, 0)
            cell.font = F(16, True)
            cell.number_format = ACCT
            box(St.r, "J", "J")
            total_rows[key] = St.r
            nxt()
            nxt()
            continue
        for n, it in enumerate(items, 1):
            h1 = est_height(it["desc"], "B", "I", 16, False)
            h2 = est_height(it["note"], "B", "I", 17, True) if it["note"] else 0
            need(h1 + h2 + 20)
            ws.cell(St.r, 1, n).font = F(16, True)
            ws.cell(St.r, 1).alignment = Alignment(horizontal="center", vertical="top")
            cell = put(St.r, 2, it["desc"], 16)
            cell.alignment = Alignment(horizontal="justify", vertical="top", wrap_text=True)
            ws.merge_cells(f"B{St.r}:I{St.r}")
            cell = ws.cell(St.r, 10, it["amount"])
            cell.font = F(16)
            cell.number_format = ACCT
            cell.alignment = Alignment(horizontal="right", vertical="top")
            nxt(h1)
            if it["note"]:
                cell = put(St.r, 2, it["note"], 17, True, True)
                cell.alignment = Alignment(horizontal="justify", vertical="top", wrap_text=True)
                ws.merge_cells(f"B{St.r}:I{St.r}")
                nxt(h2)
            nxt()
        last_row = St.r - 1
        need(25)
        ws.cell(St.r, 9, f"{total_lbl}   (Rs.)").font = F(16, True)
        ws.cell(St.r, 9).alignment = Alignment(horizontal="right")
        cell = ws.cell(St.r, 10, f"=SUM(J{first_row}:J{last_row})")
        cell.font = F(16, True)
        cell.number_format = ACCT
        cell.alignment = Alignment(horizontal="right")
        box(St.r, "J", "J")
        total_rows[key] = St.r
        nxt(23)
        nxt()

    need(30)
    nxt()
    ws.cell(St.r, 9, "NET ASSETS (A+B-D)   (Rs.)").font = F(18, True)
    ws.cell(St.r, 9).alignment = Alignment(horizontal="right")
    cell = ws.cell(St.r, 10, f"=J{total_rows['A']}+J{total_rows['B']}-J{total_rows['C']}")
    cell.font = F(19, True)
    cell.number_format = ACCT
    cell.alignment = Alignment(horizontal="right")
    ws.cell(St.r, 10).border = Border(top=thin, bottom=double, left=thin, right=thin)
    nxt(24.75)
    nxt()
    signature(size=14)

    for key, row in summary_rows.items():
        ws.cell(row, 10).value = f"=J{total_rows[key]}"

    ws.print_area = f"A1:J{St.r}"
    ws.page_setup.paperSize = 9
    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_margins.left = ws.page_margins.right = 0.7
    ws.page_margins.top = ws.page_margins.bottom = 0.75
    wb.save(path)


# ======================================================================
# Word export
# ======================================================================
def export_word(c, path):
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    s = c["settings"]
    JUST, LEFT, RIGHT, CENTER = (WD_ALIGN_PARAGRAPH.JUSTIFY, WD_ALIGN_PARAGRAPH.LEFT,
                                 WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.CENTER)
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
    sec.left_margin = sec.right_margin = Inches(0.8)
    sec.top_margin, sec.bottom_margin = Inches(0.6), Inches(0.7)
    sec.header_distance = Inches(0.35)
    TEXT_W = 8.27 - 1.6

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    def border_el(tag, **sides):
        el = OxmlElement(tag)
        for side, val in sides.items():
            b = OxmlElement(f"w:{side}")
            b.set(qn("w:val"), val[0])
            b.set(qn("w:sz"), str(val[1]))
            b.set(qn("w:space"), "0")
            b.set(qn("w:color"), "000000")
            el.append(b)
        return el

    def cell_border(cell, **sides):
        tcPr = cell._tc.get_or_add_tcPr()
        tcPr.append(border_el("w:tcBorders", **sides))

    def para_border_bottom(p, val="single", sz=12):
        pPr = p._p.get_or_add_pPr()
        pPr.append(border_el("w:pBdr", bottom=(val, sz)))

    def run(p, text, bold=False, ul=False, size=None):
        r = None
        for seg, seg_bold in segments(text):
            r = p.add_run(seg)
            r.bold, r.underline = (bold or seg_bold), ul
            if size:
                r.font.size = Pt(size)
        return r

    def set_widths(table, widths):
        table.autofit = False
        tblPr = table._tbl.tblPr
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        tblPr.append(layout)
        tblW = tblPr.find(qn("w:tblW"))
        if tblW is None:
            tblW = OxmlElement("w:tblW")
            tblPr.append(tblW)
        tblW.set(qn("w:w"), str(int(sum(widths) * 1440)))
        tblW.set(qn("w:type"), "dxa")
        for gc, w in zip(table._tbl.tblGrid.findall(qn("w:gridCol")), widths):
            gc.set(qn("w:w"), str(int(w * 1440)))
        for row in table.rows:
            for cell, w in zip(row.cells, widths):
                cell.width = Inches(w)

    def fill_letterhead(header):
        first = header.paragraphs[0]._p
        first.getparent().remove(first)
        tbl = header.add_table(rows=1, cols=2, width=Inches(TEXT_W))
        set_widths(tbl, [1.4, TEXT_W - 1.4])
        lc, rc = tbl.rows[0].cells
        lg = logo_file(s)
        if lg:
            lc.paragraphs[0].add_run().add_picture(lg, height=Inches(1.0))
        lines = [(s["firm_name"], 18, True, True), (s["firm_type"], 14, True, True),
                 (s["address1"], 10, False, False), (s["address2"], 10, False, False),
                 ("Email: " + s["email"], 10, True, False), ("Contact: " + s["contact"], 10, True, False)]
        for i, (t, size, b, u) in enumerate(lines):
            p = rc.paragraphs[0] if i == 0 else rc.add_paragraph()
            p.alignment = RIGHT
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            run(p, t, b, u, size)
        rule = header.add_paragraph()
        rule.paragraph_format.space_after = Pt(0)
        para_border_bottom(rule, "single", 12)

    if s.get("letterhead_first_page", True):
        fill_letterhead(sec.header)
    else:
        sec.different_first_page_header_footer = True
        fill_letterhead(sec.header)
        sp = sec.first_page_header.paragraphs[0]
        sp.paragraph_format.space_before = Inches(1.25)

    brk = {"on": False}

    def page_break():
        brk["on"] = True

    def take_break(p):
        if brk["on"]:
            p.paragraph_format.page_break_before = True
            brk["on"] = False

    def P(text="", bold=False, ul=False, align=JUST, size=None, indent=0.45, after=6):
        p = doc.add_paragraph()
        take_break(p)
        p.alignment = align
        p.paragraph_format.left_indent = Inches(indent)
        p.paragraph_format.space_after = Pt(after)
        if text:
            run(p, text, bold, ul, size)
        return p

    def numbered(num, text, bold=False, ul=False, align=JUST):
        p = doc.add_paragraph()
        take_break(p)
        p.alignment = align
        pf = p.paragraph_format
        pf.left_indent, pf.first_line_indent = Inches(0.45), Inches(-0.45)
        pf.tab_stops.add_tab_stop(Inches(0.45))
        run(p, f"{num}.\t", True)
        run(p, text, bold, ul)
        return p

    def date_udin(left, right):
        p = doc.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(Inches(TEXT_W), WD_TAB_ALIGNMENT.RIGHT)
        p.paragraph_format.space_before = Pt(12)
        run(p, f"{left}\t{right}", True)

    def signature():
        P("", indent=0, after=0)
        for t in c["signature"]:
            P(t, bold=True, align=LEFT, indent=0, after=0)
        from signature_asset import word_signature
        word_signature(doc,s)
        if not s.get("signature_enabled"):
            for _ in range(3):P("", indent=0, after=0)
        for t in c["signatory"]:
            P(t, bold=True, align=LEFT, indent=0, after=0)
        p = doc.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(Inches(TEXT_W), WD_TAB_ALIGNMENT.RIGHT)
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(0)
        run(p, f"{c['udin_line']}\t{c['date_line']}", True)
        P(c["place"], bold=True, align=LEFT, indent=0)

    P(c["title"], bold=True, ul=True, align=CENTER, size=14, indent=0, after=12)
    for n, t in enumerate(c["intro"], 1):
        numbered(n, t)
    P("NET ASSET REPORT", bold=True, ul=True, align=CENTER, size=13, indent=0, after=6)

    t = doc.add_table(rows=1, cols=3)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for cell, txt, al in zip(hdr, ["S. No.", "PARTICULARS", "AMOUNT (in Rs.)"], [CENTER, LEFT, CENTER]):
        cell.paragraphs[0].alignment = al
        run(cell.paragraphs[0], txt, True)
    for num, label, amt, _k in c["summary"]:
        row = t.add_row().cells
        row[0].paragraphs[0].alignment = CENTER
        run(row[0].paragraphs[0], num)
        run(row[1].paragraphs[0], label)
        row[2].paragraphs[0].alignment = RIGHT
        run(row[2].paragraphs[0], fmt_acct(amt))
    row = t.add_row().cells
    merged = row[0].merge(row[1])
    merged.paragraphs[0].alignment = RIGHT
    run(merged.paragraphs[0], "Net Assets of the Applicant(s) (1+2-3)", True, size=12)
    row[2].paragraphs[0].alignment = RIGHT
    run(row[2].paragraphs[0], fmt_acct(c["nw"]), True, size=12)
    set_widths(t, [0.8, 4.27, 1.6])
    for r_ in t.rows:
        for cell in r_.cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(3)
                p.paragraph_format.space_before = Pt(3)

    P("", indent=0)
    for w in c["words"]:
        P(w, bold=True, indent=0, after=10)
    date_udin(c["date_line"], c["udin_line"])

    page_break()
    numbered(5, c["resp_head"], True, True, LEFT)
    P(c["resp"][0])
    P(c["resp"][1], bold=True)
    numbered(6, c["prac_head"], True, True, LEFT)
    for t_ in c["prac"]:
        P(t_)
    for lbl, t_ in c["procedures"]:
        p = doc.add_paragraph()
        p.alignment = JUST
        pf = p.paragraph_format
        pf.left_indent, pf.first_line_indent = Inches(0.8), Inches(-0.35)
        pf.tab_stops.add_tab_stop(Inches(0.8))
        pf.space_after = Pt(2)
        run(p, f"{lbl}\t{t_}")
    P("", after=0)
    P(c["relied"])
    date_udin(c["date_line"], c["udin_line"])

    page_break()
    for t_ in c["standards"]:
        P(t_)
    numbered(7, c["concl_head"], True, True, LEFT)
    P(c["concl"])
    numbered(8, c["restr_head"], True, True, LEFT)
    P(c["restr"])
    signature()
    P(c["enclosure"], align=LEFT, indent=0)

    page_break()
    P(c["detail_title"], bold=True, ul=True, align=CENTER, size=14, indent=0, after=10)
    t = doc.add_table(rows=1, cols=3)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    box = dict(top=("single", 6), bottom=("single", 6), left=("single", 6), right=("single", 6))
    for cell, txt, al in zip(t.rows[0].cells, ["S.No.", "Particulars", "Amount (in Rs.)"],
                             [CENTER, LEFT, CENTER]):
        cell.paragraphs[0].alignment = al
        run(cell.paragraphs[0], txt, True)
        cell_border(cell, **box)
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trPr.append(th)

    def new_row(space_before=4):
        row_ = t.add_row()
        cs = OxmlElement("w:cantSplit")
        cs.set(qn("w:val"), "true")
        row_._tr.get_or_add_trPr().append(cs)
        cells = row_.cells
        for cell in cells:
            cell.paragraphs[0].paragraph_format.space_before = Pt(space_before)
        return cells

    for key, prefix, head, items, total_lbl, total in c["sections"]:
        row = new_row(10)
        if prefix:
            run(row[0].paragraphs[0], prefix.strip(), True)
        run(row[1].paragraphs[0], head, True, True)
        if not items:
            row = new_row()
            run(row[1].paragraphs[0], "NIL")
            row[2].paragraphs[0].alignment = RIGHT
            run(row[2].paragraphs[0], fmt_acct(0), True)
            cell_border(row[2], **box)
            continue
        for n, it in enumerate(items, 1):
            row = new_row(6)
            row[0].paragraphs[0].alignment = CENTER
            run(row[0].paragraphs[0], str(n), True)
            p = row[1].paragraphs[0]
            p.alignment = JUST
            run(p, it["desc"])
            if it["note"]:
                p2 = row[1].add_paragraph()
                p2.alignment = JUST
                run(p2, it["note"], True, True, 10)
            row[2].paragraphs[0].alignment = RIGHT
            run(row[2].paragraphs[0], fmt_acct(it["amount"]))
        row = new_row(6)
        row[1].paragraphs[0].alignment = RIGHT
        run(row[1].paragraphs[0], f"{total_lbl}  (Rs.)", True)
        row[2].paragraphs[0].alignment = RIGHT
        run(row[2].paragraphs[0], fmt_acct(total), True)
        cell_border(row[2], **box)

    row = new_row(14)
    row[1].paragraphs[0].alignment = RIGHT
    run(row[1].paragraphs[0], "NET ASSETS (A+B-D)  (Rs.)", True, size=12)
    row[2].paragraphs[0].alignment = RIGHT
    run(row[2].paragraphs[0], fmt_acct(c["nw"]), True, size=12)
    cell_border(row[2], top=("single", 6), left=("single", 6), right=("single", 6), bottom=("double", 6))
    set_widths(t, [0.6, 4.57, 1.5])

    signature()
    doc.save(path)


# ======================================================================
# PDF export
# ======================================================================
def _pdf_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.fonts import addMapping
    win = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    candidates = [
        [os.path.join(win, f) for f in ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf")],
        ["/System/Library/Fonts/Supplemental/" + f for f in
         ("Arial.ttf", "Arial Bold.ttf", "Arial Italic.ttf", "Arial Bold Italic.ttf")],
        ["/Library/Fonts/" + f for f in ("Arial.ttf", "Arial Bold.ttf", "Arial Italic.ttf", "Arial Bold Italic.ttf")],
        ["/usr/share/fonts/truetype/msttcorefonts/" + f for f in
         ("Arial.ttf", "Arial_Bold.ttf", "Arial_Italic.ttf", "Arial_Bold_Italic.ttf")],
        ["/usr/share/fonts/truetype/liberation/" + f for f in
         ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf", "LiberationSans-Italic.ttf",
          "LiberationSans-BoldItalic.ttf")],
    ]
    for files in candidates:
        if all(os.path.isfile(f) for f in files):
            try:
                names = ["CertFont", "CertFont-Bold", "CertFont-Italic", "CertFont-BoldItalic"]
                for n, f in zip(names, files):
                    if n not in pdfmetrics.getRegisteredFontNames():
                        pdfmetrics.registerFont(TTFont(n, f))
                addMapping("CertFont", 0, 0, names[0])
                addMapping("CertFont", 1, 0, names[1])
                addMapping("CertFont", 0, 1, names[2])
                addMapping("CertFont", 1, 1, names[3])
                return names[0], names[1]
            except Exception:
                continue
    return "Helvetica", "Helvetica-Bold"


def export_pdf(c, path):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                    PageBreak, KeepTogether)
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from xml.sax.saxutils import escape

    s = c["settings"]
    REG, BOLD = _pdf_fonts()
    W, H = A4
    LM = RM = 0.75 * inch
    FRAME_W = W - LM - RM
    TOP = 148

    base = ParagraphStyle("base", fontName=REG, fontSize=10, leading=13.6, alignment=TA_JUSTIFY,
                          spaceAfter=6)
    st = {
        "body": base,
        "left": ParagraphStyle("left", parent=base, alignment=TA_LEFT),
        "center": ParagraphStyle("center", parent=base, alignment=TA_CENTER),
        "right": ParagraphStyle("right", parent=base, alignment=TA_RIGHT, spaceAfter=0),
        "cell": ParagraphStyle("cell", parent=base, spaceAfter=0),
        "note": ParagraphStyle("note", parent=base, fontSize=9.5, leading=13, spaceAfter=0, spaceBefore=3),
        "title": ParagraphStyle("title", parent=base, fontName=BOLD, fontSize=13, leading=17,
                                alignment=TA_CENTER, spaceAfter=12),
    }

    def e(t):
        return escape(t).replace(BOLD_ON, "<b>").replace(BOLD_OFF, "</b>")

    def b(t, ul=False):
        t = e(t)
        return f"<b><u>{t}</u></b>" if ul else f"<b>{t}</b>"

    def letterhead(cv, _doc):
        cv.saveState()
        xr = W - RM
        top = H - 30
        y = top - 18
        lines = [(s["firm_name"], BOLD, 17, True, 0), (s["firm_type"], BOLD, 13, True, 18),
                 (s["address1"], REG, 9.5, False, 17), (s["address2"], REG, 9.5, False, 12),
                 ("Email: " + s["email"], BOLD, 9.5, False, 13), ("Contact: " + s["contact"], BOLD, 9.5, False, 12)]
        for text, font, size, ul, dy in lines:
            y -= dy
            cv.setFont(font, size)
            cv.drawRightString(xr, y, text)
            if ul:
                w = stringWidth(text, font, size)
                cv.setLineWidth(0.8)
                cv.line(xr - w, y - 2, xr, y - 2)
        lg = logo_file(s)
        if lg:
            try:
                cv.drawImage(lg, LM, y - 6, width=95, height=top - y + 6,
                             preserveAspectRatio=True, anchor="w", mask="auto")
            except Exception:
                pass
        cv.setLineWidth(1.4)
        cv.line(LM, y - 12, W - RM, y - 12)
        cv.restoreState()

    def first_page(cv, d_):
        if s.get("letterhead_first_page", True):
            letterhead(cv, d_)

    story = []

    def numbered(num, markup):
        t = Table([[Paragraph(f"<b>{num}.</b>", st["cell"]), Paragraph(markup, st["cell"])]],
                  colWidths=[30, FRAME_W - 30])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 0)]))
        story.append(t)

    def body(markup, style="body"):
        ps = ParagraphStyle("ind", parent=st[style], leftIndent=30)
        story.append(Paragraph(markup, ps))

    def two_col(left, right):
        t = Table([[Paragraph(left, st["left"]), Paragraph(right, st["right"])]],
                  colWidths=[FRAME_W / 2, FRAME_W / 2])
        t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        return t

    def signature():
        parts = [Spacer(1, 8)]
        parts += [Paragraph(b(t), ParagraphStyle("sig", parent=st["left"], spaceAfter=1)) for t in c["signature"]]
        from signature_asset import pdf_signature
        image=pdf_signature(s)
        parts.append(image if image is not None else Spacer(1, 40))
        parts += [Paragraph(b(t), ParagraphStyle("sig", parent=st["left"], spaceAfter=1)) for t in c["signatory"]]
        parts.append(Spacer(1, 8))
        parts.append(two_col(b(c["udin_line"]), b(c["date_line"])))
        parts.append(Paragraph(b(c["place"]), st["left"]))
        story.append(KeepTogether(parts))

    story.append(Paragraph(f"<u>{e(c['title'])}</u>", st["title"]))
    for n, t in enumerate(c["intro"], 1):
        numbered(n, e(t))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<u>NET ASSET REPORT</u>",
                           ParagraphStyle("h", parent=st["title"], fontSize=12, spaceAfter=6)))
    data = [[Paragraph(b("S. No."), st["center"]), Paragraph(b("PARTICULARS"), st["cell"]),
             Paragraph(b("AMOUNT (in Rs.)"), st["center"])]]
    for num, label, amt, _k in c["summary"]:
        data.append([Paragraph(num, st["center"]), Paragraph(e(label), st["cell"]),
                     Paragraph(fmt_acct(amt), st["right"])])
    big = ParagraphStyle("big", parent=st["right"], fontName=BOLD, fontSize=11.5)
    data.append([Paragraph("Net Assets of the Applicant(s) (1+2-3)", big), "", Paragraph(fmt_acct(c["nw"]), big)])
    t = Table(data, colWidths=[55, FRAME_W - 55 - 125, 125])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.6, colors.black),
                           ("SPAN", (0, -1), (1, -1)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(t)
    story.append(Spacer(1, 14))
    for w in c["words"]:
        story.append(Paragraph(b(w), ParagraphStyle("w", parent=base, spaceAfter=10)))
    story.append(Spacer(1, 16))
    story.append(two_col(b(c["date_line"]), b(c["udin_line"])))

    story.append(PageBreak())
    story.append(Paragraph(f"<u>{e(c['detail_title'])}</u>", st["title"]))
    data = [[Paragraph(b("S.No."), st["center"]), Paragraph(b("Particulars"), st["cell"]),
             Paragraph(b("Amount (in Rs.)"), st["center"])]]
    cmds = [("BOX", (0, 0), (0, 0), 0.6, colors.black), ("BOX", (1, 0), (1, 0), 0.6, colors.black),
            ("BOX", (2, 0), (2, 0), 0.6, colors.black), ("VALIGN", (0, 0), (-1, -1), "TOP")]
    for key, prefix, head, items, total_lbl, total in c["sections"]:
        data.append([Paragraph(b(prefix.strip()), st["cell"]) if prefix else "",
                     Paragraph(b(head, True), st["cell"]), ""])
        cmds.append(("TOPPADDING", (0, len(data) - 1), (-1, len(data) - 1), 12))
        if not items:
            data.append(["", Paragraph("NIL", st["cell"]), Paragraph(b(fmt_acct(0)), st["right"])])
            cmds.append(("BOX", (2, len(data) - 1), (2, len(data) - 1), 0.6, colors.black))
            continue
        for n, it in enumerate(items, 1):
            cell = [Paragraph(e(it["desc"]), st["cell"])]
            if it["note"]:
                cell.append(Paragraph(b(it["note"], True), st["note"]))
            data.append([Paragraph(b(str(n)), st["center"]), cell,
                         Paragraph(fmt_acct(it["amount"]), st["right"])])
            cmds.append(("TOPPADDING", (0, len(data) - 1), (-1, len(data) - 1), 8))
        data.append(["", Paragraph(b(f"{total_lbl}  (Rs.)"), st["right"]), Paragraph(b(fmt_acct(total)), st["right"])])
        cmds += [("BOX", (2, len(data) - 1), (2, len(data) - 1), 0.6, colors.black),
                 ("TOPPADDING", (0, len(data) - 1), (-1, len(data) - 1), 8),
                 ("VALIGN", (0, len(data) - 1), (-1, len(data) - 1), "MIDDLE")]
    nwst = ParagraphStyle("nw", parent=st["right"], fontName=BOLD, fontSize=11.5)
    data.append(["", Paragraph("NET ASSETS (A+B-D)  (Rs.)", nwst), Paragraph(fmt_acct(c["nw"]), nwst)])
    r = len(data) - 1
    cmds += [("BOX", (2, r), (2, r), 0.6, colors.black),
             ("LINEBELOW", (2, r), (2, r), 0.6, colors.black, None, None, None, 2, 2),
             ("TOPPADDING", (0, r), (-1, r), 16), ("VALIGN", (0, r), (-1, r), "MIDDLE")]
    t = Table(data, colWidths=[40, FRAME_W - 40 - 115, 115], repeatRows=1)
    t.setStyle(TableStyle(cmds))
    story.append(t)
    story.append(Spacer(1, 10))
    signature()

    # Keep the front summary and annexures together; place certification,
    # responsibility and signature material at the end of the report.
    story.append(PageBreak())
    numbered(5, b(c["resp_head"], True))
    body(e(c["resp"][0]))
    body(b(c["resp"][1]))
    numbered(6, b(c["prac_head"], True))
    for t_ in c["prac"]:
        body(e(t_))
    proc_style = ParagraphStyle("proc", parent=base, leftIndent=56, firstLineIndent=-22, spaceAfter=2)
    for lbl, t_ in c["procedures"]:
        story.append(Paragraph(f"{lbl}&nbsp;&nbsp;{e(t_)}", proc_style))
    story.append(Spacer(1, 6))
    body(e(c["relied"]))
    story.append(Spacer(1, 10))
    for t_ in c["standards"]:
        body(e(t_))
    numbered(7, b(c["concl_head"], True))
    body(e(c["concl"]))
    numbered(8, b(c["restr_head"], True))
    body(e(c["restr"]))
    signature()
    story.append(Spacer(1, 10))
    story.append(Paragraph(e(c["enclosure"]), st["left"]))

    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=LM, rightMargin=RM, topMargin=TOP,
                            bottomMargin=45, title="Net Asset Report",
                            author=s["firm_name"])
    doc.build(story, onFirstPage=first_page, onLaterPages=letterhead)


def open_path(p):
    try:
        if sys.platform.startswith("win"):
            os.startfile(p)  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", p])
        else:
            subprocess.Popen(["xdg-open", p])
    except Exception:
        pass


# ======================================================================
# GUI: Add / edit item dialog
# ======================================================================
class ItemDialog(tk.Toplevel):
    def __init__(self, master, category, item=None, applicant=""):
        super().__init__(master)
        self.cat_name = category
        self.cat = CATS[category]
        self.applicant = applicant
        self.result = None
        self.title(("Edit - " if item else "Add - ") + category)
        self.transient(master)
        self.resizable(True, True)

        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text=category, style="H2.TLabel").grid(row=0, column=0, columnspan=2, sticky="w",
                                                                pady=(0, 10))
        self.vars = {}
        self.bolds = {}
        row = 1
        saved = item["fields"] if item else {}
        saved_bold = item.get("bold", {}) if item else {}
        for key, label, typ, opts in self.cat["fields"]:
            ttk.Label(outer, text=label + ":").grid(row=row, column=0, sticky="w", pady=3, padx=(0, 10))
            default = saved.get(key, "")
            if not item:
                if typ == "combo":
                    default = opts[0]
                elif typ == "relation":
                    default = "Self"
                elif key == "holder":
                    default = applicant
            var = tk.StringVar(value=default)
            if typ == "combo":
                w = ttk.Combobox(outer, textvariable=var, values=opts, width=58)
            elif typ == "relation":
                w = ttk.Combobox(outer, textvariable=var, values=RELATIONS, width=58, state="readonly")
            else:
                w = ttk.Entry(outer, textvariable=var, width=61)
            w.grid(row=row, column=1, sticky="we", pady=3)
            self.vars[key] = var
            var.trace_add("write", lambda *_a, k=key: self.on_field(k))
            
            # Universal Date Formatting (Inside Asset Popups)
            if key in ("as_on", "val_date", "reg_date"):
                w.bind("<FocusOut>", lambda e, k=key: self.on_date_focusout(k))
                
            bvar = tk.BooleanVar(value=bool(saved_bold.get(key, key in {"nature", "details", "holder", "relation"})))
            self.bolds[key] = bvar
            bvar.trace_add("write", lambda *_a, k=key: self.on_field(k))
            row += 1

        if self.cat["kind"] == "asset":
            ttk.Label(outer, text="Show under:").grid(row=row, column=0, sticky="w", pady=3)
            self.section = tk.StringVar(value=SECTION_LABELS[item["section"] if item else self.cat["section"]])
            ttk.Combobox(outer, textvariable=self.section, state="readonly", width=58,
                         values=[SECTION_LABELS["A"] + " Investments (Annexure A)",
                                 SECTION_LABELS["B"] + " Investments (Annexure B)"]
                         ).grid(row=row, column=1, sticky="we", pady=3)
            if not item:
                self.section.set(SECTION_LABELS[self.cat["section"]] + " Investments (Annexure "
                                 + self.cat["section"] + ")")
            else:
                self.section.set(SECTION_LABELS[item["section"]] + " Investments (Annexure "
                                 + item["section"] + ")")
            row += 1
        else:
            self.section = None

        ttk.Label(outer, text="Amount (Rs.):", style="Bold.TLabel").grid(row=row, column=0, sticky="w", pady=6)
        self.amount = tk.StringVar(value=(f"{item['amount']:.2f}" if item else ""))
        ttk.Entry(outer, textvariable=self.amount, width=30, font=("Segoe UI", 11)).grid(
            row=row, column=1, sticky="w", pady=6)
        row += 1

        ttk.Separator(outer).grid(row=row, column=0, columnspan=3, sticky="we", pady=8)
        row += 1
        hint = ("Type the particulars as they should appear in the certificate. "
                "Select any words and press Ctrl+B to make them bold."
                if not self.cat["fields"] else
                "Text below is generated from the fields above. You can edit it, and select any words "
                "and press Ctrl+B to bold / unbold them.")
        ttk.Label(outer, text=hint, style="Hint.TLabel").grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1
        ttk.Label(outer, text="Particulars:").grid(row=row, column=0, sticky="nw", pady=3)
        self.desc = tk.Text(outer, height=4, width=70, wrap="word", font=("Segoe UI", 10))
        self.desc.grid(row=row, column=1, sticky="we", pady=3)
        row += 1
        ttk.Label(outer, text="Note below it\n(bold, underlined):").grid(row=row, column=0, sticky="nw", pady=3)
        self.note = tk.Text(outer, height=3, width=70, wrap="word", font=("Segoe UI", 10))
        self.note.grid(row=row, column=1, sticky="we", pady=3)
        row += 1
        for w in (self.desc, self.note):
            w.tag_configure("b", font=("Segoe UI", 10, "bold"))
            w.bind("<Control-b>", lambda _e, w=w: self.toggle_bold(w))
            w.bind("<Control-B>", lambda _e, w=w: self.toggle_bold(w))

        btns = ttk.Frame(outer)
        btns.grid(row=row, column=0, columnspan=3, sticky="we", pady=(12, 0))
        if self.cat["fields"]:
            ttk.Button(btns, text="Regenerate text from fields", command=self.regenerate).pack(side="left")
        ttk.Button(btns, text="Bold / unbold selected text (Ctrl+B)",
                   command=self.toggle_bold_focused).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(btns, text="Save", style="Accent.TButton", command=self.ok).pack(side="right", padx=6)
        outer.columnconfigure(1, weight=1)

        self.manual = False
        if item:
            self.set_rich(self.desc, item["desc"])
            self.set_rich(self.note, item["note"])
            if self.cat["fields"]:
                gen = dict(saved, _bold=saved_bold)
                self.manual = (item["desc"] != self.cat["desc"](gen) or item["note"] != self.cat["note"](gen))
        else:
            self.regenerate()
        self.desc.bind("<Key>", lambda _e: setattr(self, "manual", True))
        self.note.bind("<Key>", lambda _e: setattr(self, "manual", True))

        self.grab_set()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.wait_window(self)

    def on_date_focusout(self, key):
        val = self.vars[key].get()
        if val:
            fmt = format_smart_date(val, ".")
            self.vars[key].set(fmt)
            self.on_field(key)

    def fields(self):
        return {k: v.get() for k, v in self.vars.items()}

    def bold_flags(self):
        return {k: bool(v.get()) for k, v in self.bolds.items()}

    @staticmethod
    def set_rich(w, text):
        w.delete("1.0", "end")
        for seg, bold in segments(text):
            w.insert("end", seg, ("b",) if bold else ())

    @staticmethod
    def get_rich(w):
        out, bold = [], False
        for kind, value, _idx in w.dump("1.0", "end-1c", text=True, tag=True):
            if kind == "tagon" and value == "b":
                bold = True
            elif kind == "tagoff" and value == "b":
                bold = False
            elif kind == "text":
                out.append(mark(value, bold))
        return "".join(out).replace(BOLD_OFF + BOLD_ON, "").strip()

    def toggle_bold(self, w):
        try:
            a, b = w.index("sel.first"), w.index("sel.last")
        except tk.TclError:
            return "break"
        if "b" in w.tag_names(a):
            w.tag_remove("b", a, b)
        else:
            w.tag_add("b", a, b)
        self.manual = True
        return "break"

    def toggle_bold_focused(self):
        w = self.focus_get()
        self.toggle_bold(w if w in (self.desc, self.note) else self.desc)

    def on_field(self, key):
        if key == "relation":
            rel, holder = self.vars["relation"].get(), self.vars["holder"].get().strip()
            if rel == "Self" and not holder:
                self.vars["holder"].set(self.applicant)
            elif rel != "Self" and holder == self.applicant:
                self.vars["holder"].set("")
        if not self.manual:
            self.regenerate(keep_manual=True)

    def regenerate(self, keep_manual=False):
        if not self.cat["fields"]:
            return
        f = dict(self.fields(), _bold=self.bold_flags())
        self.set_rich(self.desc, self.cat["desc"](f))
        self.set_rich(self.note, self.cat["note"](f))
        if not keep_manual:
            self.manual = False

    def ok(self):
        try:
            amount = parse_amount(self.amount.get())
        except ValueError:
            messagebox.showerror(APP_TITLE, "Please enter a valid amount (numbers only).", parent=self)
            return
        desc = self.get_rich(self.desc)
        if not desc:
            messagebox.showerror(APP_TITLE, "Particulars cannot be empty.", parent=self)
            return
        if "________" in desc and not messagebox.askyesno(
                APP_TITLE, "Some details are still blank (shown as ________). Save anyway?", parent=self):
            return
        if amount <= 0 and not messagebox.askyesno(APP_TITLE, "Amount is zero. Save anyway?", parent=self):
            return
        if self.section is not None:
            section = self.section.get()[0]
        else:
            section = "C"
        self.result = dict(category=self.cat_name, kind=self.cat["kind"], section=section,
                           fields=self.fields(), bold=self.bold_flags(), desc=desc,
                           note=self.get_rich(self.note), amount=round(amount, 2))
        self.destroy()



# ======================================================================
# Local document intake (PDF text + Tesseract OCR for scans/JPEG)
# ======================================================================
def find_tesseract():
    """Find a bundled OCR runtime first, then a user-installed Tesseract."""
    bundled_roots = []
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        bundled_roots.append(os.path.join(meipass, "networth_ocr"))
    bundled_roots.extend([os.path.join(HERE, "networth_ocr"),
                          os.path.join(os.path.dirname(sys.executable), "networth_ocr")])
    candidates = [os.path.join(root, "tesseract.exe") for root in bundled_roots]
    configured = ""
    try:
        with open(OCR_SETTINGS_FILE, "r", encoding="utf-8") as stream:
            configured = json.load(stream).get("tesseract_path", "")
    except Exception:
        pass
    candidates.extend([configured, shutil.which("tesseract"),
                       r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                       r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"])
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return ""

def _run_local_ocr(image_path, tesseract_path, psm=6):
    if not tesseract_path:
        raise RuntimeError("Tesseract OCR is not installed or bundled with this EXE.")
    tessdata_candidates = [
        os.path.join(os.path.dirname(tesseract_path), "tessdata"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(tesseract_path))), "share", "tessdata"),
    ]
    tessdata = next((path for path in tessdata_candidates if os.path.isdir(path)), "")
    command = [tesseract_path, image_path, "stdout"]
    if tessdata:
        command.extend(["--tessdata-dir", tessdata])
    command.extend(["-l", "eng", "--psm", str(psm)])
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(tesseract_path) + os.pathsep + env.get("PATH", "")
    result = run_hidden(command, timeout=120, env=env)
    if result.returncode:
        detail = (result.stderr or result.stdout or "Tesseract did not return text.").strip()
        raise RuntimeError(detail[:500])
    return result.stdout.strip()


def _ocr_text_score(text):
    """Prefer rotations that produce recognizable document labels and words."""
    low = (text or "").lower()
    score = min(len(re.findall(r"\b[a-z]{3,}\b", low)), 60) * 0.25
    for phrase, weight in (
        ("passport no", 12), ("given names", 8), ("surname", 6),
        ("date of birth", 6), ("name of father", 6), ("republic of india", 5),
        ("account number", 6), ("closing balance", 8), ("fixed deposit", 8),
        ("market value", 7), ("valuation report", 8),
        ("computation of income", 10), ("gross total income", 8),
        ("total income", 5), ("acknowledgement number", 8),
    ):
        if phrase in low:
            score += weight
    if re.search(r"P<IND<", (text or "").upper()):
        score += 20
    mrz_lines = [re.sub(r"[^A-Z0-9<]", "", line.upper()) for line in (text or "").splitlines()]
    if any(line.startswith("P<IND<") for line in mrz_lines) and any(
            re.match(r"^[A-Z0-9]{7,9}<", line) and len(line) >= 25 for line in mrz_lines):
        score += 35
    return score


def _ocr_best_orientation(image_path, tesseract_path, fast=False):
    """Read the original scan first; try quarter-turns when it looks sideways or noisy."""
    base_text = _run_local_ocr(image_path, tesseract_path)
    best_text, best_score = base_text, _ocr_text_score(base_text)
    passport_like = bool(re.search(r"passport|P<IND<|given names|surname", base_text, re.I))
    # Bank/valuation scans are usually upright. Re-running every page at
    # three rotations and multiple segmentation modes made large statements
    # take several minutes. Keep the expensive orientation search for likely
    # passports, where it materially improves MRZ/field extraction.
    if fast or (not passport_like and best_score >= 25):
        return best_text
    try:
        from PIL import Image, ImageOps
        with Image.open(image_path) as image:
            image = ImageOps.grayscale(image)
            image = ImageOps.autocontrast(image)
            angles = (0, 90, 270) if passport_like or best_score < 25 else (0,)
            modes = (3, 11) if passport_like or best_score < 25 else (3,)
            for angle in angles:
                rotated = image.rotate(angle, expand=True) if angle else image
                fd, rotated_path = tempfile.mkstemp(prefix="networth_rotate_", suffix=".png")
                os.close(fd)
                try:
                    rotated.save(rotated_path)
                    for psm in modes:
                        text = _run_local_ocr(rotated_path, tesseract_path, psm=psm)
                        score = _ocr_text_score(text)
                        if score > best_score:
                            best_text, best_score = text, score
                finally:
                    try:
                        os.remove(rotated_path)
                    except OSError:
                        pass
    except Exception:
        # Keep the OCR text already obtained if image enhancement is unavailable.
        pass
    return best_text


def read_document_text(path, tesseract_path, progress=None, page_errors=None):
    """Return (page texts, pages OCRed). All processing is local."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg", ".jpeg", ".png"):
        return [_ocr_best_orientation(path, tesseract_path)], 1
    if ext in (".xlsx", ".xlsm"):
        try:
            from openpyxl import load_workbook
            workbook = load_workbook(path, read_only=True, data_only=True, keep_vba=ext == ".xlsm")
            try:
                sheets = []
                for sheet in workbook.worksheets:
                    rows = []
                    for row in sheet.iter_rows(values_only=True):
                        values = [str(value).strip() for value in row if value is not None and str(value).strip()]
                        if values:
                            rows.append(" | ".join(values))
                    if rows:
                        sheets.append(f"SHEET: {sheet.title}\n" + "\n".join(rows))
                return ["\n\n".join(sheets)], 0
            finally:
                workbook.close()
        except Exception as exc:
            raise RuntimeError(f"Could not read this Excel workbook: {exc}") from exc
    if ext != ".pdf":
        raise ValueError("Choose a PDF, JPEG, XLSX, or XLSM file.")
    try:
        import pymupdf as fitz
    except ImportError as exc:
        raise RuntimeError("PDF/image support needs PyMuPDF. Install it with: python -m pip install pymupdf") from exc
    pages, ocr_count = [], 0
    filename_hint = os.path.basename(path).lower()
    administrative_land_record = any(term in filename_hint for term in ("jamabandi", "registry", "khasra", "khatauni", "mutation"))
    with fitz.open(path) as pdf:
        if pdf.needs_pass:
            raise RuntimeError("This PDF is password protected. Open an unlocked copy and retry.")
        for page_no in range(len(pdf)):
            page = pdf.load_page(page_no)
            text = page.get_text("text").strip()
            # OCR only pages with no usable text layer; preserve real selectable text.
            if len(re.sub(r"\s", "", text)) < 24 and not administrative_land_record:
                # Large bank scans are commonly rendered at oversized canvas
                # dimensions.  Use a practical OCR resolution for them while
                # retaining the higher-resolution passport path.
                scale = 3.0 if "passport" in filename_hint else 1.5
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                fd, image_path = tempfile.mkstemp(prefix="networth_ocr_", suffix=".png")
                os.close(fd)
                try:
                    pix.save(image_path)
                    try:
                        text = _ocr_best_orientation(image_path, tesseract_path, fast="passport" not in filename_hint)
                        ocr_count += 1
                    except Exception as exc:
                        if page_errors is None:raise
                        page_errors.append('Page '+str(page_no+1)+' could not be read by OCR: '+str(exc)+'. Other text pages are retained; this import is incomplete.')
                finally:
                    try:
                        os.remove(image_path)
                    except OSError:
                        pass
            pages.append(text)
            if progress:
                progress(page_no + 1, len(pdf))
    return pages, ocr_count


INCOME_FIELDS = [
    ("salary", "Income from salary", ["income from salary", "salary income", "salary"]),
    ("house_property", "Income from house property", ["income from house property", "house property income"]),
    ("business_profession", "Business / profession income", ["income from business or profession", "business or profession income", "business income"]),
    ("capital_gains", "Capital gains", ["income from capital gains", "capital gains"]),
    ("other_sources", "Income from other sources", ["income from other sources", "other sources income"]),
    ("gross_total_income", "Gross total income", ["gross total income"]),
    ("deductions", "Deductions", ["total deductions", "deductions under chapter vi-a", "chapter vi-a deductions"]),
    ("total_income", "Total income", ["total taxable income", "total income"]),
    ("agricultural_income", "Agricultural income", ["agricultural income", "agriculture income"]),
    ("exempt_income", "Exempt income", ["income exempt from tax", "exempt income", "exempted income"]),
]
INCOME_LABELS = {key: (label, aliases) for key, label, aliases in INCOME_FIELDS}


def _label_value(text, labels, value_pattern=r"([^|]{2,})"):
    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        low = clean.lower()
        for label in labels:
            pos = low.find(label.lower())
            if pos >= 0:
                tail = clean[pos + len(label):].strip(" :#=-\t")
                match = re.search(value_pattern, tail)
                if match:
                    value = match.group(1).strip(" :#=-\t")
                    if value:
                        return value
    return ""


def _label_amount(text, labels):
    number = re.compile(r"(?<![A-Za-z])(?:INR|Rs\.?|₹)?\s*\(?\s*(-?\d[\d,]*(?:\.\d{1,2})?)\s*\)?", re.I)
    for line in text.splitlines():
        low = line.lower()
        for label in labels:
            pos = low.find(label.lower())
            if pos < 0:
                continue
            match = number.search(line[pos + len(label):])
            if not match:
                continue
            raw = match.group(1).replace(",", "").replace(" ", "")
            try:
                value = float(raw)
                if "(" in match.group(0):
                    value = -abs(value)
                return value
            except ValueError:
                pass
    return 0.0


def _classify_tax_document(text):
    low = text.lower()
    has_income = any(word in low for word in ("total income", "gross total income", "income from salary", "agricultural income"))
    if not has_income:
        return ""
    if "computation of income" in low or "computation of total income" in low or "income computation" in low:
        return "Computation"
    if any(word in low for word in ("acknowledgement number", "acknowledgment number", "itr-v", "return filed", "income tax return")):
        return "ITR"
    return "Tax document"


def _extract_income_values(text):
    result = {}
    for key, _label, aliases in INCOME_FIELDS:
        amount = _label_amount(text, aliases)
        if amount:
            result[key] = amount
    return result


def _passport_fields(text):
    applicant = {}
    lines = text.splitlines()
    def labelled(patterns):
        for i, line in enumerate(lines):
            for pattern in patterns:
                match = re.search(pattern, line, re.I)
                if not match:
                    continue
                value = (match.group(1) if match.lastindex else "").strip(" :#-\t")
                if not value and i + 1 < len(lines):
                    value = lines[i + 1].strip(" :#-\t")
                value = re.sub(r"\s+", " ", value).strip(" .,:;-_")
                if value and not re.search(r"^(?:name|date|place|address|passport|nationality|sex)\b", value, re.I):
                    return value
        return ""

    # Retain the identity information available on the passport, including
    # fields not printed in the report header.
    details = {
        "surname": labelled([r"surname\s*[:#-]?\s*(.*)"]),
        "given_names": labelled([r"given\s+names?\s*[:#-]?\s*(.*)"]),
        "father_name": labelled([r"name\s+of\s+father\s*[:#-]?\s*(.*)", r"father(?:'s)?\s+name\s*[:#-]?\s*(.*)"]),
        "mother_name": labelled([r"name\s+of\s+mother\s*[:#-]?\s*(.*)", r"mother(?:'s)?\s+name\s*[:#-]?\s*(.*)"]),
        "spouse_name": labelled([r"name\s+of\s+spouse\s*[:#-]?\s*(.*)", r"spouse(?:'s)?\s+name\s*[:#-]?\s*(.*)"]),
        "date_of_birth": labelled([r"date\s+of\s+birth\s*[:#-]?\s*(.*)", r"dob\s*[:#-]?\s*(.*)"]),
        "place_of_birth": labelled([r"place\s+of\s+birth\s*[:#-]?\s*(.*)"]),
        "place_of_issue": labelled([r"place\s+of\s+issue\s*[:#-]?\s*(.*)"]),
        "date_of_issue": labelled([r"date\s+of\s+issue\s*[:#-]?\s*(.*)"]),
        "date_of_expiry": labelled([r"date\s+of\s+expiry\s*[:#-]?\s*(.*)", r"expiry\s+date\s*[:#-]?\s*(.*)"]),
        "nationality": labelled([r"nationality\s*[:#-]?\s*(.*)"]),
        "sex": labelled([r"sex\s*[:#-]?\s*(.*)"]),
        "file_number": labelled([r"file\s*(?:no\.?|number)\s*[:#-]?\s*(.*)"]),
    }
    # The machine-readable zone is more reliable than printed labels after OCR.
    mrz = [re.sub(r"[^A-Z0-9<]", "", line.upper()) for line in lines]
    for index, line in enumerate(mrz):
        if line.startswith("P<IND<") and len(line) >= 12:
            raw_name = line[6:].split("<<<<", 1)[0]
            name_parts = raw_name.split("<<", 1)
            mrz_surname = re.sub(r"<+", " ", name_parts[0]).strip()
            mrz_given = re.sub(r"<+", " ", name_parts[1]).strip() if len(name_parts) > 1 else ""
            details["surname"] = details["surname"] or mrz_surname.title()
            details["given_names"] = details["given_names"] or mrz_given.title()
            name = " ".join(part for part in (mrz_given, mrz_surname) if part)
            name = re.sub(r"\s+", " ", name).strip()
            if name and not re.search(r"\d", name):
                applicant["name"] = name.title()
            for next_line in mrz[index + 1:index + 4]:
                if len(next_line) >= 25 and re.match(r"^[A-Z0-9]{7,9}<", next_line):
                    passport_no = next_line[:9].rstrip("<")
                    if re.fullmatch(r"[A-Z][0-9]{6,8}", passport_no):
                        applicant["passport"] = passport_no
                    if len(next_line) >= 27:
                        details["nationality"] = details["nationality"] or next_line[10:13].replace("<", "")
                        details["date_of_birth"] = details["date_of_birth"] or _mrz_date(next_line[13:19])
                        details["sex"] = details["sex"] or next_line[20:21].replace("<", "")
                        details["date_of_expiry"] = details["date_of_expiry"] or _mrz_date(next_line[21:27], future=True)
                        if len(next_line) >= 42:
                            details["personal_number"] = next_line[28:42].rstrip("<")
                        break
    if not applicant.get("name"):
        full_name = " ".join(p for p in (details["given_names"], details["surname"]) if p)
        if full_name:
            applicant["name"] = full_name
    if "passport" not in applicant:
        for index, line in enumerate(lines):
            if re.search(r"passport\s*(?:no\.?|number)", line, re.I):
                candidates = re.findall(r"\b[A-Z][0-9]{6,8}\b", line.upper())
                for later in lines[index + 1:index + 4]:
                    candidates.extend(re.findall(r"\b[A-Z][0-9]{6,8}\b", later.upper()))
                if candidates:
                    applicant["passport"] = candidates[0]
                    break
    if "passport" not in applicant:
        for line in mrz:
            match = re.match(r"^([A-Z][0-9]{6,8})<", line)
            if match:
                applicant["passport"] = match.group(1)
                break
    applicant["parent"] = details["father_name"] or details["spouse_name"] or details["mother_name"]
    # Passport address lines commonly continue over several rows after the label.
    for index, line in enumerate(lines):
        if re.search(r"\baddress\b", line, re.I) and not re.search(r"old passport|address proof", line, re.I):
            parts = []
            tail = re.split(r"\baddress\b", line, maxsplit=1, flags=re.I)[-1].strip(" :|-")
            if tail and not re.search(r"name of|address proof", tail, re.I):
                parts.append(tail)
            for later in lines[index + 1:index + 6]:
                clean = re.sub(r"\s+", " ", later).strip(" :|-")
                if not clean:
                    continue
                if re.search(r"old passport|file no|passport no|observation|miscellaneous|name of (?:father|mother|spouse)|date of birth|place of birth", clean, re.I):
                    break
                if not re.search(r"name of (?:father|mother|spouse)", clean, re.I):
                    parts.append(clean)
            address = ", ".join(parts).strip(" ,")
            if len(address) >= 8:
                applicant["address"] = address[:180]
                break
    details["address"] = applicant.get("address", "")
    details["passport_number"] = applicant.get("passport", "")
    details["full_name"] = applicant.get("name", "")
    applicant["passport_details"] = {k: v for k, v in details.items() if v}
    return applicant


def _mrz_date(value, future=False):
    if not re.fullmatch(r"\d{6}", value or ""):
        return ""
    yy, mm, dd = int(value[:2]), value[2:4], value[4:6]
    year = 2000 + yy if future or yy <= (datetime.date.today().year % 100) else 1900 + yy
    return f"{dd}.{mm}.{year}"

def _latest_statement_balance(text):
    """Return the balance attached to the latest dated statement row."""
    candidates=[]
    date_pattern=r'(\d{1,2}[-/.]\d{1,2}[-/.](?:19|20)?\d{2})'
    amount_pattern=r'(?:₹|rs\.?|inr\s*)?([\d][\d,]*(?:\.\d{1,2})?)'
    for line_no,line in enumerate(text.splitlines()):
        low=line.casefold()
        if not any(word in low for word in ('balance','closing','available','ledger')):continue
        dates=re.findall(date_pattern,line,re.I);amounts=re.findall(amount_pattern,line,re.I)
        if not dates or not amounts:continue
        try:
            raw=dates[-1].replace('/','-').replace('.','-');parts=raw.split('-')
            year=int(parts[2]);year += 2000 if year<100 else 0
            parsed=datetime.date(year,int(parts[1]),int(parts[0]))
            amount=float(amounts[-1].replace(',',''))
            candidates.append((parsed,line_no,amount,dates[-1]))
        except (ValueError,TypeError):
            continue
    if not candidates:return 0,''
    chosen=max(candidates,key=lambda item:(item[0],item[1]))
    return chosen[2],chosen[3]


def _extract_assets(path, text, applicant, current_applicant):
    low = text.lower()
    bank = _label_value(text, ["bank name", "name of bank", "bank"], r"([^|]{3,})")
    for line in text.splitlines()[:12]:
        clean = re.sub(r"\s+", " ", line).strip(" :|-." )
        if re.search(r"\b(?:state|central|union|indian)\s+bank\b|\bbank\s+of\b|\b(?:hdfc|icici|axis|pnb|canara|kotak|sbi)\b", clean, re.I):
            bank = clean
            break
    account = _label_value(text, ["fixed deposit no", "fd no", "account number", "account no", "a/c no"],
                           r"([A-Z0-9][A-Z0-9/-]{4,})")
    holder = _label_value(text, ["name of customer", "account holder", "customer name", "name of account holder"], r"([^|]{3,})")
    holder = holder or applicant.get("name") or current_applicant
    date = _label_value(text, ["balance as on", "statement date", "as on", "date"],
                        r"([0-3]?\d[-/.][01]?\d[-/.](?:19|20)?\d{2})")
    source = os.path.basename(path)
    assets = []

    def add(category, amount, fields):
        if amount > 0:
            assets.append({"category": category, "amount": amount, "fields": fields,
                           "source": source})

    if any(term in low for term in ("fixed deposit", "term deposit", "maturity amount")):
        amount = _label_amount(text, ["deposit amount", "principal amount", "fixed deposit amount", "amount deposited"])
        if not amount:
            amount = _label_amount(text, ["maturity amount", "balance amount"])
        add("Fixed Deposit", amount, {"acno": account, "as_on": date, "bank": bank,
                                     "holder": holder, "relation": "Self"})
    elif (not any(term in low for term in ("public provident fund", "ppf account", "national savings certificate", "nsc certificate", "kisan vikas patra"))
          and any(term in low for term in ("closing balance", "account statement", "statement of account", "available balance"))):
        statement_amount,statement_date=_latest_statement_balance(text)
        amount = statement_amount or _label_amount(text, ["closing balance", "available balance", "ledger balance", "closing amount"])
        date = statement_date or date
        add("Bank Account (Savings / Current)", amount,
            {"acc_type": "Saving", "acno": account, "as_on": date, "bank": bank,
             "evidence_type": "Bank Statement" if "statement" in low else "Bank Certificate",
             "holder": holder, "relation": "Self"})
    elif any(term in low for term in ("public provident fund", "ppf account", "national savings certificate", "nsc certificate", "kisan vikas patra")):
        amount = _label_amount(text, ["closing balance", "account balance", "current balance", "balance as on", "maturity value"])
        scheme = ("Public Provident Fund (PPF)" if "provident" in low or "ppf" in low else
                  "National Savings Certificate (NSC)" if "nsc" in low or "national savings" in low else
                  "Kisan Vikas Patra (KVP)")
        add("PPF / NSC / Post Office", amount,
            {"scheme": scheme, "acno": account, "as_on": date,
             "inst": bank, "holder": holder, "relation": "Self"})
    elif "surrender value" in low and any(term in low for term in ("insurance", "policy", "life assured")):
        amount = _label_amount(text, ["surrender value", "fund value", "cash value"])
        add("Life Insurance (Surrender Value)", amount,
            {"pno": account, "insurer": bank, "as_on": date,
             "holder": holder, "relation": "Self"})
    elif any(term in low for term in ("property valuation", "immovable property", "market value of property")) or ("valuation report" in low and not any(term in low for term in ("gold", "jewel", "ornament"))):
        amount = _label_amount(text, ["fair market value", "market value of property", "market value", "valuation amount", "value of property", "assessed value"])
        nature = "Agriculture Land" if re.search(r"agricultur|farm|khasra", low) else "Residential House"
        if "flat" in low:
            nature = "Residential Flat"
        elif "plot" in low:
            nature = "Residential Plot"
        elif "commercial" in low or "shop" in low:
            nature = "Commercial Property"
        location = _label_value(text, ["property address", "property location", "located at", "address"], r"([^|]{4,})")
        add("Immovable Property", amount,
            {"nature": nature, "holder": holder, "relation": "Self", "location": location,
             "valuer": _label_value(text, ["valuer", "valuation by", "issued by"], r"([^|]{3,})"),
             "val_date": date})
    elif any(term in low for term in ("vehicle", "registration certificate", "chassis number", "insured declared value")):
        amount = _label_amount(text, ["insured declared value", "market value", "valuation amount", "vehicle value"])
        vtype = "Car" if "car" in low else ("Tractor" if "tractor" in low else "Motorcycle")
        add("Vehicle", amount, {"vtype": vtype, "holder": holder, "relation": "Self",
                                 "vno": _label_value(text, ["registration number", "vehicle no", "registration no"], r"([A-Z0-9 -]{5,})"),
                                 "reg_date": "", "basis": "Approximate Market Value (no valuation report)",
                                 "val_date": date, "valuer": ""})
    elif any(term in low for term in ("jewellery valuation", "jewelry valuation", "gold valuation", "ornaments")):
        amount = _label_amount(text, ["market value", "valuation amount", "total value", "assessed value"])
        add("Jewellery", amount, {"details": "Gold Ornaments weighing ____ grams", "holder": holder,
                                   "relation": "Self", "valuer": "", "val_date": date})
    elif any(term in low for term in ("demat", "mutual fund", "statement of holdings", "portfolio value")):
        amount = _label_amount(text, ["market value", "current value", "portfolio value", "closing value", "total value"])
        add("Shares / Mutual Funds", amount, {"itype": "Shares & Mutual Funds", "account": account,
                                                "dp": bank, "as_on": date, "holder": holder,
                                                "relation": "Self"})
    elif any(term in low for term in ("loan account", "outstanding balance", "loan statement", "credit card statement")):
        amount = _label_amount(text, ["outstanding balance", "total outstanding", "closing balance", "amount due"])
        if amount:
            is_card = "credit card" in low
            category = "Credit Card" if is_card else "Bank Loan"
            fields = ({"card": account[-4:], "as_on": date, "bank": bank, "holder": holder, "relation": "Self"}
                      if is_card else {"ltype": "Personal", "acno": account, "as_on": date, "bank": bank,
                                       "holder": holder, "relation": "Self"})
            add(category, amount, fields)
    return assets

def extract_ca_report_proposals(path, text):
    """Extract editable asset proposals from an already-issued CA report.

    The issued report is treated as source evidence; every extracted amount
    remains reviewable before it is added to the current case.
    """
    low=text.lower(); assets=[]
    if 'net asset report' not in low and 'annexure-a' not in low and 'annexure-b' not in low:
        return assets
    def amount_after(pattern, window=500):
        m=re.search(pattern+r'(.{0,'+str(window)+r'}?)\n\s*([\d][\d,]*\.\d{2})',text,re.I|re.S)
        return float(m[2].replace(',','')) if m else 0
    def add(category,name,amount,fields=None,desc=''):
        if amount>0:assets.append({'category':category,'asset_name':name,'amount':amount,'desc':desc,'fields':fields or {},'amount_candidates':[],'source':os.path.basename(path)})
    applicant=re.search(r'Name of Applicant\s*\n\s*(?:Mr\.|Ms\.|Mrs\.)?\s*([^\n]+)',text,re.I)
    owner=applicant[1].strip() if applicant else ''
    valuer_match=re.search(r'Valued by\s+(.+?)(?:\n|\()',text,re.I)
    valuer_name=valuer_match[1].strip() if valuer_match else ''
    licence_match=re.search(r'(MCB\s*-\s*Lic\.?\s*No\.?\s*[^\)\n]+)',text,re.I)
    if not licence_match:licence_match=re.search(r'((?:Lic\.?|Licence|License)\s*No\.?\s*[^\)\n]+)',text,re.I)
    valuer_licence=licence_match[1].strip() if licence_match else ''
    cash=amount_after(r'Cash in Hand')
    add('Cash in Hand','Cash in Hand',cash,{'holder':owner,'relation':'Self'},'(As per Self Declaration by Party)')
    bank=re.search(r'([A-Z][A-Z ]+Bank\s+A/c\s+No\.\s*[A-Z0-9-]+)',text,re.I)
    if bank:
        ac=re.search(r'No\.\s*([A-Z0-9-]+)',bank[1],re.I)
        amount=amount_after(re.escape(bank[1]))
        add('Bank Account (Savings / Current)',bank[1],amount,{'acno':ac[1] if ac else '','bank':bank[1].split(' A/c',1)[0].strip(),'holder':owner,'relation':'Self','evidence_type':'Bank Statement'},'(As Per Bank Statement as on the date stated in the source report)')
    for label,category in [('Semi Constructed Residential Plot','Immovable Property'),('Vacant Plot','Immovable Property'),('Residential House','Immovable Property')]:
        amount=amount_after(re.escape(label));add(category,label,amount,{'holder':owner,'relation':'Self','valuer_name':valuer_name,'valuer_firm':'','valuer_credentials':valuer_licence},'Valuation details carried from the issued CA report.')
    return assets


def extract_document_proposals(path, page_texts, current_applicant=""):
    text = "\n".join(page_texts)
    lower = text.lower()
    applicant = {}
    patterns = {
        "name": r"(?:applicant name|name of applicant|account holder(?:s)?|holder name|name)\s*[:#-]?\s*([A-Z][A-Z .'-]{2,})",
        "parent": r"(?:father(?:'s)? name|husband(?:'s)? name|father / husband)\s*[:#-]?\s*([A-Z][A-Z .'-]{2,})",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.I)
        if match:
            applicant[key] = re.sub(r"\s+", " ", match.group(1)).strip(" .:-").title()
    passport_details = {}
    if "passport" in lower or "p<ind<" in lower:
        applicant.update({k: v for k, v in _passport_fields(text).items() if v})
        passport_details = applicant.pop("passport_details", {})
    if "address" not in applicant:
        address = _label_value(text, ["residential address", "address of applicant", "address"], r"(.{4,})")
        if address and not re.search(r"passport|bank|branch|email|phone", address, re.I):
            applicant["address"] = address[:180]

    doc_type = _classify_tax_document(text)
    income = _extract_income_values(text) if doc_type else {}
    assets = [] if doc_type else _extract_assets(path, text, applicant, current_applicant)
    if not assets:
        assets = extract_ca_report_proposals(path, text)
    owner_candidate = {}
    if assets:
        source_fields = assets[0].get("fields", {})
        if source_fields.get("holder"):
            owner_candidate = {"name": source_fields.get("holder", ""), "father_name": ""}
    return {"path": path, "text": text, "applicant": applicant, "owner_candidate": owner_candidate,
            "passport_details": passport_details, "assets": assets,
            "income": income, "doc_type": doc_type or "Other document",
            "ocr_pages": 0, "page_count": len(page_texts)}


def _income_comparison(documents):
    itr = next((doc for doc in documents if doc.get("doc_type") == "ITR"), None)
    computation = next((doc for doc in documents if doc.get("doc_type") == "Computation"), None)
    statuses = {id(doc): {} for doc in documents}
    rows = []
    if not itr or not computation:
        return rows, statuses
    for key, label, _aliases in INCOME_FIELDS:
        a, b = itr.get("income", {}).get(key), computation.get("income", {}).get(key)
        if a is None and b is None:
            continue
        if a is None:
            status = "Not found in ITR"
        elif b is None:
            status = "Not found in computation"
        elif abs(float(a) - float(b)) <= 1:
            status = "Matches"
        else:
            status = f"Difference: Rs. {abs(float(a) - float(b)):,.2f}"
        statuses[id(itr)][key] = status
        statuses[id(computation)][key] = status
        rows.append((label, a, b, status))
    return rows, statuses


class DocumentImportReview(tk.Toplevel):
    """Let the user review applicant, asset, and income proposals before import."""
    APPLICANT_FIELDS = [("name", "Applicant full name"), ("parent", "Father's / Husband's name"),
                        ("passport", "Passport No."), ("address", "Residential address")]

    def __init__(self, master, documents):
        super().__init__(master)
        self.result = None
        self.documents = documents
        self.title("Review document data")
        self.transient(master)
        self.geometry("1000x700")
        self.minsize(820, 580)
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Review before importing", style="H2.TLabel").pack(anchor="w")
        ttk.Label(outer, text="OCR can misread scans. Check every value against the original; files are processed locally.",
                  style="Hint.TLabel").pack(anchor="w", pady=(3, 10))
        self.tabs = ttk.Notebook(outer)
        self.tabs.pack(fill="both", expand=True)

        self.app_vars = {}
        applicant_tab = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(applicant_tab, text="Applicant fields")
        ttk.Label(applicant_tab, text="Only checked values will be applied. Confirm replacements for existing values.",
                  style="Hint.TLabel", wraplength=900).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        combined, sources = {}, {}
        for doc in documents:
            if doc.get("passport_details"):
                continue
            for key, value in doc["applicant"].items():
                if value and key not in combined:
                    combined[key], sources[key] = value, os.path.basename(doc["path"])
        for row, (key, label) in enumerate(self.APPLICANT_FIELDS, 1):
            value = combined.get(key, "")
            use, text = tk.BooleanVar(value=bool(value)), tk.StringVar(value=value)
            ttk.Checkbutton(applicant_tab, variable=use).grid(row=row, column=0, sticky="w")
            ttk.Label(applicant_tab, text=label + ":").grid(row=row, column=1, sticky="w", padx=(0, 8), pady=4)
            ttk.Entry(applicant_tab, textvariable=text, width=72).grid(row=row, column=2, sticky="we", pady=4)
            ttk.Label(applicant_tab, text=sources.get(key, "No confident match"), style="Hint.TLabel").grid(row=row, column=3, sticky="w", padx=(8, 0))
            self.app_vars[key] = (use, text)
        applicant_tab.columnconfigure(2, weight=1)

        passports = [doc for doc in documents if doc.get("passport_details")]
        self.passport_vars = []
        if passports:
            passport_tab = ttk.Frame(self.tabs, padding=12)
            self.tabs.add(passport_tab, text="Passports & family")
            ttk.Label(passport_tab,
                      text="Each passport stays separate. Assign the person before importing; all readable identity fields are retained for review.",
                      style="Hint.TLabel", wraplength=900).pack(anchor="w", pady=(0, 8))
            canvas = tk.Canvas(passport_tab, highlightthickness=0)
            sb = ttk.Scrollbar(passport_tab, orient="vertical", command=canvas.yview)
            body = ttk.Frame(canvas)
            body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=body, anchor="nw")
            canvas.configure(yscrollcommand=sb.set)
            canvas.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")
            passport_labels = {
                "full_name": "Full name", "surname": "Surname", "given_names": "Given names",
                "passport_number": "Passport number", "father_name": "Father's name",
                "mother_name": "Mother's name", "spouse_name": "Spouse's name",
                "date_of_birth": "Date of birth", "place_of_birth": "Place of birth",
                "place_of_issue": "Place of issue", "date_of_issue": "Date of issue",
                "date_of_expiry": "Date of expiry", "nationality": "Nationality", "sex": "Sex",
                "file_number": "File number", "personal_number": "Personal number", "address": "Address",
            }
            roles = ["Applicant 1", "Applicant 2", "Father", "Mother", "Spouse", "Brother",
                     "Sister", "Son", "Daughter", "Grandfather", "Grandmother", "Other family member"]
            for doc in passports:
                card = ttk.LabelFrame(body, text=os.path.basename(doc["path"]), padding=8)
                card.pack(fill="x", pady=6)
                role = tk.StringVar(value="Applicant 1" if not self.passport_vars else "Applicant 2")
                ttk.Label(card, text="This passport belongs to:").grid(row=0, column=0, sticky="w")
                ttk.Combobox(card, textvariable=role, values=roles, state="readonly", width=24).grid(
                    row=0, column=1, sticky="w", pady=(0, 6))
                values = {}
                details = doc.get("passport_details", {})
                for row_no, (key, label) in enumerate(passport_labels.items(), 1):
                    value = details.get(key, "")
                    var = tk.StringVar(value=value)
                    ttk.Label(card, text=label + ":").grid(row=row_no, column=0, sticky="w", padx=(0, 8), pady=2)
                    ttk.Entry(card, textvariable=var, width=72).grid(row=row_no, column=1, sticky="ew", pady=2)
                    values[key] = var
                card.columnconfigure(1, weight=1)
                self.passport_vars.append((doc, role, values))

        assets_tab = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(assets_tab, text="Assets & liabilities")
        self.asset_vars = []
        ttk.Label(assets_tab, text="Checked amounts open the existing item editor so you can confirm category and details.",
                  style="Hint.TLabel", wraplength=900).pack(anchor="w", pady=(0, 8))
        canvas = tk.Canvas(assets_tab, highlightthickness=0)
        asset_scroll = ttk.Scrollbar(assets_tab, orient="vertical", command=canvas.yview)
        asset_body = ttk.Frame(canvas)
        asset_body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=asset_body, anchor="nw")
        canvas.configure(yscrollcommand=asset_scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        asset_scroll.pack(side="right", fill="y")
        for doc in documents:
            for asset in doc.get("assets", []):
                row = ttk.Frame(asset_body)
                row.pack(fill="x", pady=4)
                use, amount = tk.BooleanVar(value=True), tk.StringVar(value=f"{asset['amount']:.2f}")
                ttk.Checkbutton(row, text=f"{asset['category']} - {asset['source']}", variable=use).pack(side="left")
                ttk.Label(row, text="Rs.").pack(side="left", padx=(10, 3))
                ttk.Entry(row, textvariable=amount, width=18).pack(side="left")
                self.asset_vars.append((doc, asset, use, amount))
        if not self.asset_vars:
            ttk.Label(asset_body, text="No asset amount was identified confidently. You can still import applicant or tax data.",
                      style="Hint.TLabel").pack(anchor="w", pady=6)

        tax_docs = [doc for doc in documents if doc.get("doc_type") in ("ITR", "Computation", "Tax document")]
        income_tab = ttk.Frame(self.tabs, padding=12)
        if tax_docs:
            self.tabs.add(income_tab, text="ITR vs computation")
        ttk.Label(income_tab, text="Select both the ITR and computation in the file picker to compare matching income heads.",
                  style="Hint.TLabel", wraplength=900).pack(anchor="w", pady=(0, 8))
        comparison, self.comparison_statuses = _income_comparison(tax_docs)
        if tax_docs and comparison:
            table = ttk.Treeview(income_tab, columns=("itr", "comp", "status"), show="tree headings", height=7)
            table.heading("#0", text="Income figure")
            table.heading("itr", text="ITR (Rs.)")
            table.heading("comp", text="Computation (Rs.)")
            table.heading("status", text="Comparison")
            table.column("#0", width=220)
            table.column("itr", width=150, anchor="e")
            table.column("comp", width=170, anchor="e")
            table.column("status", width=300)
            table.pack(fill="x", pady=(0, 10))
            for label, itr, comp, status in comparison:
                table.insert("", "end", text=label,
                             values=("—" if itr is None else f"{itr:,.2f}",
                                     "—" if comp is None else f"{comp:,.2f}", status))
        elif tax_docs:
            ttk.Label(income_tab, text="No ITR/computation pair was recognized in this batch. Import both files together to compare them.",
                      style="Hint.TLabel", wraplength=900).pack(anchor="w", pady=(0, 10))
        if tax_docs:
            ttk.Label(income_tab, text="Confirm these figures before adding them to Tax & Income. Income is kept separate from asset totals.",
                      style="Hint.TLabel", wraplength=900).pack(anchor="w", pady=(0, 8))
        income_canvas = tk.Canvas(income_tab, highlightthickness=0, height=260)
        income_scroll = ttk.Scrollbar(income_tab, orient="vertical", command=income_canvas.yview)
        income_body = ttk.Frame(income_canvas)
        income_body.bind("<Configure>", lambda _e: income_canvas.configure(scrollregion=income_canvas.bbox("all")))
        income_canvas.create_window((0, 0), window=income_body, anchor="nw")
        income_canvas.configure(yscrollcommand=income_scroll.set)
        income_canvas.pack(side="left", fill="both", expand=True)
        income_scroll.pack(side="right", fill="y")
        self.income_vars = []
        for doc in tax_docs:
            for key, value in doc.get("income", {}).items():
                label = INCOME_LABELS.get(key, (key, []))[0]
                row = ttk.Frame(income_body)
                row.pack(fill="x", pady=2)
                use, amount = tk.BooleanVar(value=True), tk.StringVar(value=f"{value:.2f}")
                ttk.Checkbutton(row, variable=use).pack(side="left")
                ttk.Label(row, text=f"{doc['doc_type']} - {label}", width=34).pack(side="left", padx=4)
                ttk.Entry(row, textvariable=amount, width=18).pack(side="left")
                ttk.Label(row, text=os.path.basename(doc["path"]), style="Hint.TLabel").pack(side="left", padx=8)
                self.income_vars.append((doc, key, use, amount))
        if tax_docs and not self.income_vars:
            ttk.Label(income_body, text="No income figures were identified confidently.", style="Hint.TLabel").pack(anchor="w")

        source_tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(source_tab, text="Files read")
        tree = ttk.Treeview(source_tab, columns=("type", "pages", "ocr", "detected"), show="tree headings", height=9)
        for col, title, width in (("#0", "File", 320), ("type", "Classified as", 120), ("pages", "Pages", 60), ("ocr", "OCR pages", 75), ("detected", "Suggested data", 300)):
            tree.heading(col, text=title)
            tree.column(col, width=width, anchor="w" if col in ("#0", "type", "detected") else "center")
        tree.pack(fill="both", expand=True)
        preview_box = ttk.LabelFrame(source_tab, text="Extracted text preview", padding=6)
        preview_box.pack(fill="both", expand=True, pady=(8, 0))
        preview = tk.Text(preview_box, height=9, wrap="word", font=("Segoe UI", 9), state="disabled")
        preview_scroll = ttk.Scrollbar(preview_box, orient="vertical", command=preview.yview)
        preview.configure(yscrollcommand=preview_scroll.set)
        preview.pack(side="left", fill="both", expand=True)
        preview_scroll.pack(side="right", fill="y")
        for index, doc in enumerate(documents):
            found = []
            if doc["applicant"]:
                found.append("applicant fields")
            found.extend(asset["category"] for asset in doc.get("assets", []))
            if doc.get("income"):
                found.append(f"{doc['doc_type']} income figures")
            if not found:
                found.append("text only - review manually")
            tree.insert("", "end", iid=str(index), text=os.path.basename(doc["path"]),
                        values=(doc["doc_type"], doc["page_count"], doc["ocr_pages"], ", ".join(found)))
        def show_preview(_event=None):
            selected = tree.selection()
            if selected:
                doc = documents[int(selected[0])]
                preview.configure(state="normal")
                preview.delete("1.0", "end")
                preview.insert("1.0", doc["text"] or "No readable text was extracted from this file.")
                preview.configure(state="disabled")
        tree.bind("<<TreeviewSelect>>", show_preview)
        if documents:
            tree.selection_set("0")
            show_preview()

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Import selected", style="Accent.TButton", command=self.accept).pack(side="right", padx=6)
        self.grab_set()
        self.wait_window(self)

    def accept(self):
        applicant = {key: text.get().strip() for key, (use, text) in self.app_vars.items()
                     if use.get() and text.get().strip()}
        assets = []
        for doc, asset, use, amount in self.asset_vars:
            if not use.get():
                continue
            try:
                value = parse_amount(amount.get())
            except Exception:
                messagebox.showwarning(APP_TITLE, f"Enter a valid amount for {asset['source']}.", parent=self)
                return
            if value <= 0:
                messagebox.showwarning(APP_TITLE, f"The suggested amount for {asset['source']} must be above zero.", parent=self)
                return
            suggestion = dict(asset)
            suggestion["fields"] = dict(asset["fields"])
            suggestion["amount"] = value
            assets.append(suggestion)
        grouped = {}
        for doc, key, use, amount in self.income_vars:
            if not use.get():
                continue
            try:
                value = parse_amount(amount.get())
            except Exception:
                messagebox.showwarning(APP_TITLE, f"Enter a valid amount for {os.path.basename(doc['path'])}.", parent=self)
                return
            grouped.setdefault(id(doc), {"source": os.path.basename(doc["path"]),
                                         "document_type": doc["doc_type"], "values": {}, "comparison": {}})
            grouped[id(doc)]["values"][key] = value
        selected_records = list(grouped.values())
        itr = next((record for record in selected_records if record["document_type"] == "ITR"), None)
        comp = next((record for record in selected_records if record["document_type"] == "Computation"), None)
        if itr and comp:
            for record in (itr, comp):
                for key in set(itr["values"]) | set(comp["values"]):
                    a, b = itr["values"].get(key), comp["values"].get(key)
                    record["comparison"][key] = ("Not found in ITR" if a is None else "Not found in computation" if b is None
                                                 else "Matches" if abs(a - b) <= 1
                                                 else f"Difference: Rs. {abs(a - b):,.2f}")
        passport_records = []
        for doc, role, values in self.passport_vars:
            details = {key: var.get().strip() for key, var in values.items() if var.get().strip()}
            if details:
                passport_records.append({"role": role.get(), "source": os.path.basename(doc["path"]),
                                         "fields": details})
        self.result = {"applicant": applicant, "passports": passport_records,
                       "assets": assets, "income_records": selected_records}
        self.destroy()


# ======================================================================
# GUI: Main window
# ======================================================================
class App(tk.Tk):
    APP_FIELDS = [
        ("title", "Title", "combo", ["Mr.", "Ms.", "Mrs.", "Miss"]),
        ("name", "Applicant's full name", "text", None),
        ("relation", "Relation", "combo", ["S/o", "D/o", "W/o"]),
        ("parent", "Father's / Husband's name (with Mr.)", "text", None),
        ("passport", "Passport No.", "text", None),
        ("address", "Residential address", "text", None),
        ("co_title", "Second applicant - title", "combo", ["Mr.", "Ms.", "Mrs.", "Miss"]),
        ("co_name", "Second applicant - full name", "text", None),
        ("co_relation", "Second applicant - relation", "combo", ["S/o", "D/o", "W/o"]),
        ("co_parent", "Second applicant - father / spouse name", "text", None),
        ("co_passport", "Second applicant - passport no.", "text", None),
        ("co_address", "Second applicant - residential address", "text", None),
        ("purpose", "Purpose (in connection with)", "combo",
         ["Study Visa", "Visitor Visa", "Tourist Visa", "Work Visa", "Spouse Visa",
          "Dependent Visa", "PR Application", "Business Visa"]),
        ("authority", "For submission to", "text", None),
        ("engagement_date", "Engagement letter date", "text", None),
        ("statement_date", "Net assets as at (statement date)", "text", None),
        ("cert_date", "Certificate date", "text", None),
        ("udin", "UDIN", "text", None),
        ("currency", "Show net assets also in", "readonly", CURRENCIES),
        ("rate", "Exchange rate: 1 unit = Rs.", "text", None),
    ]

    SETTINGS_FIELDS = [
        ("firm_name", "Firm name"), ("firm_type", "Line below firm name"), ("address1", "Address line 1"),
        ("address2", "Address line 2"), ("email", "Email"), ("contact", "Contact"), ("frn", "FRN No."),
        ("partner", "Signing partner"), ("designation", "Designation"), ("mno", "Membership No."),
        ("place", "Place"), ("logo_path", "Logo image (PNG/JPG)"),
        ("icai_id", "ICAI Login ID (MRN)"),
        ("icai_pwd", "ICAI Portal Password"),
    ]

    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x760")
        self.minsize(1000, 640)
        self.load_profiles()
        self.items = []
        self.source_documents = []
        self.income_records = []
        self.family_members = []
        self.passport_records = []
        self.client_file = None
        self._style()

        header = ttk.Frame(self, padding=(16, 12, 16, 4))
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, style="H1.TLabel").pack(side="left")
        ttk.Button(header, text="New", command=self.new_client).pack(side="right", padx=3)
        ttk.Button(header, text="Save client data", command=self.save_client).pack(side="right", padx=3)
        ttk.Button(header, text="Open client data", command=self.open_client).pack(side="right", padx=3)
        ttk.Button(header, text="Import Documents", command=self.import_documents).pack(side="right", padx=3)

        bar = ttk.Frame(self, padding=(16, 6, 16, 12))
        bar.pack(side="bottom", fill="x")

        nb = ttk.Notebook(self)
        self.notebook = nb
        nb.pack(side="top", fill="both", expand=True, padx=12, pady=6)
        
        self.tab_app = ttk.Frame(nb, padding=14)
        self.tab_items = ttk.Frame(nb, padding=10)
        self.tab_tax = ttk.Frame(nb, padding=10)
        self.tab_settings = ttk.Frame(nb, padding=14)
        
        nb.add(self.tab_app, text="  1. Applicant Details  ")
        nb.add(self.tab_items, text="  2. Assets & Liabilities  ")
        nb.add(self.tab_tax, text="  3. Tax & Income  ")
        nb.add(self.tab_settings, text="  Firm Settings  ")
        
        self._build_app_tab()
        self._build_items_tab()
        self._build_tax_tab()
        self._build_settings_tab()

        self.totals_lbl = ttk.Label(bar, text="", style="Bold.TLabel")
        self.totals_lbl.pack(side="left")
        
        ttk.Button(bar, text="Generate UDIN (Auto)", style="Accent.TButton",
                   command=self.trigger_udin_generation).pack(side="left", padx=(15, 5))
                   
        ttk.Button(bar, text="Generate UDIN (Manual)", 
                   command=lambda: webbrowser.open("https://udin.icai.org/")).pack(side="left", padx=5)
                   
        ttk.Button(bar, text="Save as MS Word", style="Accent.TButton",
                   command=lambda: self.export("docx")).pack(side="right", padx=3)
        ttk.Button(bar, text="Save as PDF", style="Accent.TButton",
                   command=lambda: self.export("pdf")).pack(side="right", padx=3)
        ttk.Button(bar, text="Save as Excel", style="Accent.TButton",
                   command=lambda: self.export("xlsx")).pack(side="right", padx=3)
        
        if self.ca_profiles:
            self.profile_cb.set(list(self.ca_profiles.keys())[0])
            self.load_profile()
            
        self.refresh()

    def _style(self):
        st = ttk.Style(self)
        if "clam" in st.theme_names():
            st.theme_use("clam")
        accent = "#1F4E79"
        st.configure("H1.TLabel", font=("Segoe UI", 17, "bold"), foreground=accent)
        st.configure("H2.TLabel", font=("Segoe UI", 12, "bold"), foreground=accent)
        st.configure("Bold.TLabel", font=("Segoe UI", 10, "bold"))
        st.configure("Hint.TLabel", foreground="#666666")
        st.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), foreground="white",
                     background=accent, padding=(12, 6))
        st.map("Accent.TButton", background=[("active", "#163A5C")])
        st.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
        st.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        st.configure("TNotebook.Tab", padding=(10, 6), font=("Segoe UI", 10))

    def fetch_exchange_rate(self, *_args):
        curr_str = self.av["currency"].get()
        if curr_str == "None" or not curr_str:
            self.av["rate"].set("")
            self.refresh_totals()
            return
            
        code = curr_str.split(" - ")[0] 
        self.av["rate"].set("Fetching...")
        
        def do_fetch():
            try:
                url = f"https://api.exchangerate-api.com/v4/latest/{code}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    rate = data.get("rates", {}).get("INR")
                    if rate:
                        self.after(0, lambda: self.av["rate"].set(f"{rate:.2f}"))
                        self.after(0, self.refresh_totals)
            except Exception:
                self.after(0, lambda: self.av["rate"].set(""))
                self.after(0, self.refresh_totals)

        threading.Thread(target=do_fetch, daemon=True).start()

    def on_date_focusout(self, key):
        if key not in ("engagement_date", "statement_date", "cert_date"):
            return
        val = self.av[key].get()
        if not val:
            return
        fmt = format_smart_date(val, ".")
        
        if key == "engagement_date":
            self.av["engagement_date"].set(fmt)
            self.av["statement_date"].set(format_smart_date(val, "-"))
            self.av["cert_date"].set(fmt)
        elif key == "statement_date":
            self.av["statement_date"].set(format_smart_date(val, "-"))
        else:
            self.av[key].set(fmt)

    def _build_app_tab(self):
        self.av = {}
        today = datetime.date.today()
        defaults = dict(title="Mr.", relation="S/o", purpose="Study Visa",
                        authority="immigration or embassy authorities",
                        engagement_date=today.strftime("%d.%m.%Y"),
                        statement_date=today.strftime("%d-%m-%Y"),
                        cert_date=today.strftime("%d.%m.%Y"), currency="None")
        canvas = tk.Canvas(self.tab_app, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_app, orient="vertical", command=canvas.yview)
        frm = ttk.Frame(canvas, padding=(4, 4, 14, 4))
        frm.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frm, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.ab = {}
        for i, (key, label, typ, opts) in enumerate(self.APP_FIELDS, 1):
            ttk.Label(frm, text=label + ":").grid(row=i, column=0, sticky="w", pady=4, padx=(0, 12))
            var = tk.StringVar(value=defaults.get(key, ""))
            if typ == "combo":
                w = ttk.Combobox(frm, textvariable=var, values=opts, width=70)
            elif typ == "readonly":
                w = ttk.Combobox(frm, textvariable=var, values=opts, width=70, state="readonly")
            else:
                w = ttk.Entry(frm, textvariable=var, width=73)
            w.grid(row=i, column=1, sticky="we", pady=4)
            self.av[key] = var
            
            if key in ("engagement_date", "statement_date", "cert_date"):
                w.bind("<FocusOut>", lambda e, k=key: self.on_date_focusout(k))
            
            # Match the supplied report template: identity fields are emphasized
            # automatically; users do not have to guess formatting checkboxes.
            bvar = tk.BooleanVar(value=key in {"name", "parent", "passport", "co_name", "co_parent", "co_passport"})
            self.ab[key] = bvar
            
            if key == "currency":
                var.trace_add("write", self.fetch_exchange_rate)
            elif key == "rate":
                var.trace_add("write", lambda *_a: self.refresh_totals())
                
        n = len(self.APP_FIELDS) + 1
        ttk.Label(frm, text="Names and passport details are emphasized automatically in the report. Dates auto-format on click-out.",
                  style="Hint.TLabel").grid(row=n, column=1, sticky="w", pady=(8, 0))
        frm.columnconfigure(1, weight=1)

    def _build_items_tab(self):
        frm = self.tab_items
        quick = ttk.LabelFrame(frm, text="Quick add", padding=10)
        quick.pack(fill="x", pady=(0, 10))
        ttk.Label(quick, text="Type").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.quick_category = tk.StringVar(value="Cash in Hand")
        category_cb = ttk.Combobox(quick, textvariable=self.quick_category, values=list(CATS), state="readonly",
                                   width=28)
        category_cb.grid(row=0, column=1, sticky="w", padx=(0, 12))
        category_cb.bind("<<ComboboxSelected>>", self.on_quick_category)
        ttk.Label(quick, text="Particulars").grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.quick_particulars = tk.StringVar()
        ttk.Entry(quick, textvariable=self.quick_particulars, width=34).grid(row=0, column=3, sticky="ew", padx=(0, 12))
        ttk.Label(quick, text="Owner").grid(row=0, column=4, sticky="w", padx=(0, 6))
        self.quick_owner = tk.StringVar()
        self.quick_owner_cb = ttk.Combobox(quick, textvariable=self.quick_owner, width=22)
        self.quick_owner_cb.grid(row=0, column=5, sticky="ew", padx=(0, 12))
        ttk.Label(quick, text="Amount (Rs.)").grid(row=1, column=0, sticky="w", pady=(8, 0), padx=(0, 6))
        self.quick_amount = tk.StringVar()
        ttk.Entry(quick, textvariable=self.quick_amount, width=18).grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttk.Label(quick, text="Annexure").grid(row=1, column=2, sticky="w", pady=(8, 0), padx=(0, 6))
        self.quick_section = tk.StringVar(value="B - Current Investments (Annexure B)")
        ttk.Combobox(quick, textvariable=self.quick_section, state="readonly", width=34,
                     values=["A - Non-Current Investments (Annexure A)",
                             "B - Current Investments (Annexure B)",
                             "C - Liability (Annexure C)"]).grid(row=1, column=3, sticky="w", pady=(8, 0))
        ttk.Button(quick, text="Add item", style="Accent.TButton",
                   command=self.add_quick_item).grid(row=1, column=5, sticky="e", pady=(8, 0))
        ttk.Label(quick, text="Add common items here without a popup. Double-click a saved row for advanced details.",
                  style="Hint.TLabel").grid(row=2, column=0, columnspan=6, sticky="w", pady=(8, 0))
        quick.columnconfigure(3, weight=1)
        quick.columnconfigure(5, weight=1)

        right = ttk.Frame(frm)
        right.pack(side="left", fill="both", expand=True)
        cols = ("no", "sec", "type", "particulars", "amount")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", selectmode="browse")
        for col, text, w, anchor in [("no", "#", 40, "center"), ("sec", "Annexure", 120, "w"),
                                     ("type", "Type", 170, "w"), ("particulars", "Particulars", 480, "w"),
                                     ("amount", "Amount (Rs.)", 140, "e")]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=w, anchor=anchor, stretch=(col == "particulars"))
        sb = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tree.bind("<Double-1>", lambda _e: self.edit_item())

        acts = ttk.Frame(frm)
        acts.pack(side="left", fill="y", padx=(10, 0))
        for text, cmd in [("Edit", self.edit_item), ("Duplicate", self.duplicate_item),
                          ("Delete", self.delete_item), (None, None),
                          ("▲ Move up", lambda: self.move_item(-1)), ("▼ Move down", lambda: self.move_item(1))]:
            if text is None:
                ttk.Separator(acts).pack(fill="x", pady=8)
            else:
                ttk.Button(acts, text=text, width=14, command=cmd).pack(fill="x", pady=2)

    def _build_tax_tab(self):
        frm = self.tab_tax
        ttk.Label(frm, text="Imported tax figures", style="H2.TLabel").pack(anchor="w")
        ttk.Label(frm, text="ITR and computation figures are stored separately from assets and are never added to net-asset totals. "
                           "Import both documents together to compare the amounts, including agricultural and exempt income.",
                  style="Hint.TLabel", wraplength=1000).pack(anchor="w", pady=(4, 10))
        columns = ("document", "field", "amount", "comparison")
        self.income_tree = ttk.Treeview(frm, columns=columns, show="headings", selectmode="browse")
        for col, title, width, anchor in [
            ("document", "Source document / type", 300, "w"),
            ("field", "Income figure", 250, "w"),
            ("amount", "Amount (Rs.)", 160, "e"),
            ("comparison", "ITR comparison", 260, "w"),
        ]:
            self.income_tree.heading(col, text=title)
            self.income_tree.column(col, width=width, anchor=anchor)
        self.income_tree.pack(fill="both", expand=True)
        actions = ttk.Frame(frm)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Remove selected tax document", command=self.remove_income_record).pack(side="right")

    def refresh_income_table(self):
        if not hasattr(self, "income_tree"):
            return
        if hasattr(self, "notebook"):
            if self.income_records:
                self.notebook.add(self.tab_tax, text="  3. Tax & Income  ")
            else:
                try:
                    self.notebook.hide(self.tab_tax)
                except tk.TclError:
                    pass
        self.income_tree.delete(*self.income_tree.get_children())
        for record_index, record in enumerate(self.income_records):
            for key, amount in record.get("values", {}).items():
                field = INCOME_LABELS.get(key, (key, []))[0]
                comparison = record.get("comparison", {}).get(key, "Imported; not compared in this batch")
                self.income_tree.insert("", "end", iid=f"{record_index}:{key}",
                                        values=(f"{record.get('document_type', 'Tax document')} - {record.get('source', '')}",
                                                field, f"{float(amount):,.2f}", comparison))

    def remove_income_record(self):
        selected = self.income_tree.selection()
        if not selected:
            return
        try:
            record_index = int(selected[0].split(":", 1)[0])
        except (ValueError, IndexError):
            return
        if 0 <= record_index < len(self.income_records):
            del self.income_records[record_index]
            self.refresh_income_table()

    def load_profiles(self):
        if os.path.exists(PROFILES_FILE):
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                self.ca_profiles = json.load(f)
        else:
            self.ca_profiles = {}
            old_file = os.path.join(os.path.expanduser("~"), ".networth_certificate_settings.json")
            if os.path.exists(old_file):
                try:
                    with open(old_file, "r") as f:
                        old_data = json.load(f)
                        if old_data.get("firm_name"):
                            self.ca_profiles[old_data["firm_name"]] = old_data
                except: pass

    def update_profile_dropdown(self):
        names = list(self.ca_profiles.keys())
        self.profile_cb["values"] = names

    def load_profile(self):
        name = self.profile_cb.get()
        if not name or name not in self.ca_profiles: return
        p = self.ca_profiles[name]
        for k, v in self.sv.items():
            if k in p: v.set(p[k])
        self.lh_first.set(p.get("letterhead_first_page", True))
        
    def clear_ca_form(self):
        for var in self.sv.values():
            var.set("")
        self.lh_first.set(True)

    def get_ca_dict(self):
        d = {k: v.get().strip() for k, v in self.sv.items()}
        d["letterhead_first_page"] = bool(self.lh_first.get())
        return d

    def save_new_profile(self):
        d = self.get_ca_dict()
        name = d.get("firm_name", "").strip()
        if not name:
            messagebox.showerror(APP_TITLE, "Please enter a Firm Name first.")
            return
        self.ca_profiles[name] = d
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.ca_profiles, f, indent=2)
        self.update_profile_dropdown()
        self.profile_cb.set(name)
        messagebox.showinfo(APP_TITLE, f"Profile '{name}' saved as new CA!")

    def update_current_profile(self):
        name = self.profile_cb.get()
        if not name: return self.save_new_profile()
        self.ca_profiles[name] = self.get_ca_dict()
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.ca_profiles, f, indent=2)
        messagebox.showinfo(APP_TITLE, f"Profile '{name}' updated successfully!")

    def _build_settings_tab(self):
        frm = self.tab_settings
        
        prof_frame = ttk.Frame(frm)
        prof_frame.grid(row=0, column=0, columnspan=3, sticky="we", pady=(0, 15))
        ttk.Label(prof_frame, text="Saved CA Profiles:").pack(side="left")
        
        self.profile_cb = ttk.Combobox(prof_frame, state="readonly", width=30)
        self.profile_cb.pack(side="left", padx=10)
        self.update_profile_dropdown()
        
        ttk.Button(prof_frame, text="Load Selected", command=self.load_profile).pack(side="left", padx=2)
        ttk.Button(prof_frame, text="Update Current", command=self.update_current_profile).pack(side="left", padx=2)
        ttk.Button(prof_frame, text="Save as New CA", command=self.save_new_profile).pack(side="left", padx=2)
        ttk.Button(prof_frame, text="Clear Form", command=self.clear_ca_form).pack(side="left", padx=(15,0))
        
        ttk.Separator(frm).grid(row=1, column=0, columnspan=3, sticky="we", pady=(0, 10))

        self.sv = {}
        for i, (key, label) in enumerate(self.SETTINGS_FIELDS, 2):
            ttk.Label(frm, text=label + ":").grid(row=i, column=0, sticky="w", pady=4, padx=(0, 12))
            var = tk.StringVar(value="")
            
            if key == "icai_pwd":
                w = ttk.Entry(frm, textvariable=var, width=80, show="*")
            else:
                w = ttk.Entry(frm, textvariable=var, width=80)
                
            w.grid(row=i, column=1, sticky="we", pady=4)
            self.sv[key] = var
            
        n = len(self.SETTINGS_FIELDS) + 2
        ttk.Button(frm, text="Browse...", command=self.pick_logo).grid(row=n - 1, column=2, padx=6)
        
        self.lh_first = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Print letterhead on the first page too "
                                  "(untick if you print page 1 on pre-printed letterhead)",
                        variable=self.lh_first).grid(row=n, column=1, sticky="w", pady=8)
        
        frm.columnconfigure(1, weight=1)

    def pick_logo(self):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if p:
            self.sv["logo_path"].set(p)

    def applicant_name(self):
        return f"{self.av['title'].get()} {self.av['name'].get()}".strip()

    def on_quick_category(self, _event=None):
        category = self.quick_category.get()
        if category in CATS:
            section = CATS[category]["section"]
            label = {"A": "A - Non-Current Investments (Annexure A)",
                     "B": "B - Current Investments (Annexure B)",
                     "C": "C - Liability (Annexure C)"}[section]
            self.quick_section.set(label)

    def known_people(self):
        people = []
        for name_key, title_key, role in (("name", "title", "Applicant"),
                                          ("co_name", "co_title", "Co-applicant")):
            name = self.av.get(name_key).get().strip() if self.av.get(name_key) else ""
            if name:
                title = self.av.get(title_key).get().strip() if self.av.get(title_key) else ""
                people.append(f"{title} {name}".strip() + (f" ({role})" if role == "Co-applicant" else " (Applicant)"))
        for person in getattr(self, "family_members", []):
            label = person.get("name", "").strip()
            if label:
                people.append(f"{label} ({person.get('role', 'Family member')})")
        return people

    def selected_index(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def add_item(self, cat):
        self.quick_category.set(cat)
        self.quick_particulars.focus_set()

    def add_quick_item(self):
        category = self.quick_category.get().strip()
        if category not in CATS:
            return
        try:
            amount = parse_amount(self.quick_amount.get())
        except ValueError:
            messagebox.showwarning(APP_TITLE, "Enter a valid amount in rupees.")
            return
        if amount <= 0:
            messagebox.showwarning(APP_TITLE, "Enter an amount greater than zero.")
            return
        particulars = self.quick_particulars.get().strip()
        if not particulars:
            particulars = "Cash in hand as per self-declaration" if category == "Cash in Hand" else ""
        if not particulars:
            messagebox.showwarning(APP_TITLE, "Enter short particulars for this item.")
            return
        owner_label = self.quick_owner.get().strip() or (self.known_people() or [self.applicant_name()])[0]
        relation = owner_label.rsplit("(", 1)[1].rstrip(")") if "(" in owner_label else "Self"
        if relation == "Applicant":
            relation = "Self"
        owner = re.sub(r"\s+\([^()]*\)$", "", owner_label)
        section = self.quick_section.get()[0]
        cat = CATS[category]
        desc = mark(category, True) + " — " + particulars + " " + mark(f"(Held by {owner}; {relation})", True)
        note = "(As per self-declaration by the party)" if category == "Cash in Hand" else "(As per supporting documents / information provided by the client)"
        item = {"category": category, "kind": cat["kind"], "section": section,
                "fields": {"holder": owner, "relation": relation},
                "bold": {"holder": True, "relation": True},
                "desc": desc, "note": note, "amount": round(amount, 2)}
        self.items.append(item)
        self.quick_particulars.set("")
        self.quick_amount.set("")
        self.refresh(select=len(self.items) - 1)

    def edit_item(self):
        i = self.selected_index()
        if i is None:
            return
        dlg = ItemDialog(self, self.items[i]["category"], item=self.items[i], applicant=self.applicant_name())
        if dlg.result:
            self.items[i] = dlg.result
            self.refresh(select=i)

    def duplicate_item(self):
        i = self.selected_index()
        if i is None:
            return
        self.items.insert(i + 1, json.loads(json.dumps(self.items[i])))
        self.refresh(select=i + 1)

    def delete_item(self):
        i = self.selected_index()
        if i is None:
            return
        if messagebox.askyesno(APP_TITLE, "Delete the selected entry?"):
            del self.items[i]
            self.refresh()

    def move_item(self, delta):
        i = self.selected_index()
        if i is None:
            return
        j = i + delta
        if 0 <= j < len(self.items):
            self.items[i], self.items[j] = self.items[j], self.items[i]
            self.refresh(select=j)

    def import_documents(self):
        paths = filedialog.askopenfilenames(
            title="Select client documents (select the ITR and computation together)",
            filetypes=[("Supported documents", "*.pdf *.jpg *.jpeg *.xlsx *.xlsm"),
                       ("PDF documents", "*.pdf"), ("JPEG images", "*.jpg *.jpeg"),
                       ("Excel computation", "*.xlsx *.xlsm")])
        if not paths:
            return
        tesseract = find_tesseract()
        if not tesseract:
            if messagebox.askyesno(APP_TITLE,
                    "Local OCR is needed for JPEGs and scanned PDF pages.\n\n"
                    "Browse to tesseract.exe now? Choose No to continue with searchable PDFs only.\n\n"
                    "If needed, install the Windows OCR engine from https://github.com/UB-Mannheim/tesseract/wiki"):
                tesseract = filedialog.askopenfilename(title="Select tesseract.exe",
                                                       filetypes=[("Tesseract OCR", "tesseract.exe"), ("Applications", "*.exe")])
                if not tesseract:
                    return
                try:
                    check = run_hidden([tesseract, "--version"], timeout=15)
                    if check.returncode:
                        raise RuntimeError((check.stderr or check.stdout or "Version check failed").strip())
                    with open(OCR_SETTINGS_FILE, "w", encoding="utf-8") as stream:
                        json.dump({"tesseract_path": tesseract}, stream)
                except Exception as exc:
                    messagebox.showerror(APP_TITLE, f"That file could not run as Tesseract OCR:\n{exc}")
                    return
        self._start_document_import(paths, tesseract)

    def _start_document_import(self, paths, tesseract):
        current_applicant = self.applicant_name()
        progress = tk.Toplevel(self)
        progress.title("Reading client documents")
        progress.transient(self)
        progress.resizable(False, False)
        body = ttk.Frame(progress, padding=18)
        body.pack(fill="both", expand=True)
        label = ttk.Label(body, text="Extracting text locally...", wraplength=440)
        label.pack(fill="x", pady=(0, 10))
        bar = ttk.Progressbar(body, mode="indeterminate", length=420)
        bar.pack(fill="x")
        bar.start(12)
        progress.protocol("WM_DELETE_WINDOW", lambda: None)
        progress.grab_set()

        def work():
            documents, errors = [], []
            for index, path in enumerate(paths, 1):
                try:
                    self.after(0, lambda i=index, n=len(paths), f=os.path.basename(path):
                               label.config(text=f"Reading {i} of {n}: {f}"))
                    def report_page(page_no, page_total, file_name=os.path.basename(path)):
                        self.after(0, lambda p=page_no, total=page_total, name=file_name:
                                   label.config(text=f"Reading {name}: page {p} of {total}"))
                    pages, ocr_count = read_document_text(path, tesseract, report_page)
                    doc = extract_document_proposals(path, pages, current_applicant)
                    doc["ocr_pages"] = ocr_count
                    documents.append(doc)
                except Exception as exc:
                    errors.append(f"{os.path.basename(path)}: {exc}")
            self.after(0, lambda: self._finish_document_import(progress, documents, errors))

        threading.Thread(target=work, daemon=True).start()

    def _finish_document_import(self, progress, documents, errors):
        try:
            progress.grab_release()
            progress.destroy()
        except tk.TclError:
            pass
        if not documents:
            detail = "\n\n".join(errors) if errors else "No documents could be read."
            messagebox.showerror(APP_TITLE, "No document text was extracted.\n\n" + detail +
                                 "\n\nFor scanned documents, install Tesseract OCR and retry.")
            return
        review = DocumentImportReview(self, documents)
        if review.result is not None:
            for key, value in review.result["applicant"].items():
                current = self.av[key].get().strip()
                if current and current != value and not messagebox.askyesno(
                        APP_TITLE, f"Replace the existing {key} value with the value read from the document?"):
                    continue
                self.av[key].set(value)
            for passport in review.result.get("passports", []):
                fields = passport["fields"]
                role = passport["role"]
                self.passport_records.append(passport)
                person_name = fields.get("full_name") or " ".join(
                    part for part in (fields.get("given_names"), fields.get("surname")) if part)
                parent_name = fields.get("father_name") or fields.get("spouse_name") or fields.get("mother_name", "")
                if role == "Applicant 1":
                    updates = {"name": person_name, "passport": fields.get("passport_number", ""),
                               "address": fields.get("address", ""), "parent": parent_name,
                               "title": "Ms." if fields.get("sex", "").upper().startswith("F") else "Mr."}
                elif role == "Applicant 2":
                    updates = {"co_name": person_name, "co_passport": fields.get("passport_number", ""),
                               "co_address": fields.get("address", ""), "co_parent": parent_name,
                               "co_title": "Ms." if fields.get("sex", "").upper().startswith("F") else "Mr."}
                else:
                    self.family_members.append({"name": person_name, "role": role,
                                                "passport_fields": fields,
                                                "source": passport.get("source", "")})
                    continue
                for key, value in updates.items():
                    if value and key in self.av:
                        self.av[key].set(value)
            applicant = self.applicant_name()
            for suggestion in review.result["assets"]:
                category = suggestion["category"]
                cat = CATS[category]
                fields = dict(suggestion["fields"])
                if "holder" in fields and not fields.get("holder"):
                    fields["holder"] = applicant
                default_bold = {field[0]: field[0] in {"nature", "details", "holder", "relation"}
                                for field in cat.get("fields", [])}
                generated = dict(fields, _bold=default_bold)
                item = {"category": category, "kind": cat["kind"], "section": cat["section"],
                        "fields": fields, "amount": suggestion["amount"],
                        "desc": cat["desc"](generated), "note": cat["note"](generated), "bold": default_bold}
                item["bold"] = default_bold
                item["_source_document"] = suggestion["source"]
                self.items.append(item)
            self.income_records.extend(review.result.get("income_records", []))
            self.refresh_people_dropdown()
            for doc in documents:
                if doc["path"] not in self.source_documents:
                    self.source_documents.append(doc["path"])
            self.refresh()
        if errors:
            messagebox.showwarning(APP_TITLE, "Some documents could not be read; others remain available for import:\n\n" +
                                   "\n".join(errors))

    def refresh(self, select=None):
        self.tree.delete(*self.tree.get_children())
        counters = {"A": 0, "B": 0, "C": 0}
        for idx, it in enumerate(self.items):
            counters[it["section"]] += 1
            plain = strip_marks(it["desc"])
            short = plain if len(plain) < 110 else plain[:107] + "…"
            self.tree.insert("", "end", iid=str(idx),
                             values=(counters[it["section"]], SECTION_LABELS[it["section"]],
                                     it["category"], short, f"{it['amount']:,.2f}"))
        if select is not None and 0 <= select < len(self.items):
            self.tree.selection_set(str(select))
            self.tree.see(str(select))
        self.refresh_totals()
        self.refresh_income_table()
        self.refresh_people_dropdown()

    def refresh_people_dropdown(self):
        if not hasattr(self, "quick_owner_cb"):
            return
        people = self.known_people()
        self.quick_owner_cb.configure(values=people)
        if not self.quick_owner.get() and people:
            self.quick_owner.set(people[0])

    def refresh_totals(self):
        tot = {k: sum(i["amount"] for i in self.items if i["section"] == k) for k in "ABC"}
        nw = tot["A"] + tot["B"] - tot["C"]
        text = (f"A: Rs. {fmt_inr(tot['A'])}    B: Rs. {fmt_inr(tot['B'])}    "
                f"C: Rs. {fmt_inr(tot['C'])}    NET ASSETS: Rs. {fmt_inr(nw)}")
        cur = self.av["currency"].get() if hasattr(self, "av") else "None"
        try:
            rate = parse_amount(self.av["rate"].get()) if hasattr(self, "av") else 0
        except ValueError:
            rate = 0
        if cur != "None" and rate > 0:
            text += f"    ≈ {cur.split(' - ')[0]} {nw / rate:,.2f}"
        self.totals_lbl.config(text=text)

    def client_data(self):
        return {"applicant": {k: v.get() for k, v in self.av.items()},
                "applicant_bold": {k: bool(v.get()) for k, v in self.ab.items()},
                "items": self.items, "source_documents": self.source_documents,
                "income_records": self.income_records,
                "family_members": self.family_members, "passport_records": self.passport_records}

    def save_client(self):
        name = self.av["name"].get().strip() or "client"
        p = filedialog.asksaveasfilename(defaultextension=".json", initialfile=f"{name} - net asset report.json",
                                         filetypes=[("Client data", "*.json")])
        if not p:
            return
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.client_data(), f, indent=2, ensure_ascii=False)
        self.client_file = p
        messagebox.showinfo(APP_TITLE, "Client data saved. Use 'Open client data' to revise it later.")

    def open_client(self):
        p = filedialog.askopenfilename(filetypes=[("Client data", "*.json")])
        if not p:
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.get("applicant", {}).items():
                if k in self.av:
                    self.av[k].set(v)
            for k, v in self.ab.items():
                v.set(bool(data.get("applicant_bold", {}).get(k, False)))
            self.items = data.get("items", [])
            self.source_documents = data.get("source_documents", [])
            self.income_records = data.get("income_records", [])
            self.family_members = data.get("family_members", [])
            self.passport_records = data.get("passport_records", [])
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Could not open file:\n{e}")
            return
        self.client_file = p
        self.refresh_people_dropdown()
        self.refresh()

    def new_client(self):
        if (self.items or self.income_records) and not messagebox.askyesno(
                APP_TITLE, "Clear the current client, including imported assets and tax figures, and start a new one?"):
            return
        for k in ("name", "parent", "passport", "address", "co_name", "co_parent",
                  "co_passport", "co_address", "udin", "rate"):
            self.av[k].set("")
        for key, default in (("co_title", "Mr."), ("co_relation", "S/o")):
            self.av[key].set(default)
        self.av["currency"].set("None")
        self.items = []
        self.source_documents = []
        self.income_records = []
        self.family_members = []
        self.passport_records = []
        self.client_file = None
        self.refresh_people_dropdown()
        self.refresh()

    def export(self, kind):
        a = {k: v.get().strip() for k, v in self.av.items()}
        a["_bold"] = {k: bool(v.get()) for k, v in self.ab.items()}
        if not a["name"]:
            messagebox.showwarning(APP_TITLE, "Please enter the applicant's name (tab 1).")
            return
        if not any(i["kind"] == "asset" for i in self.items):
            messagebox.showwarning(APP_TITLE, "Please add at least one asset (tab 2).")
            return
        if a["currency"] != "None":
            try:
                if parse_amount(a["rate"]) <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning(APP_TITLE, "Please enter a valid exchange rate, or set currency to None.")
                return
        content = build_content({"app": a, "items": self.items, "settings": self.get_ca_dict()})
        ext = {"xlsx": ".xlsx", "pdf": ".pdf", "docx": ".docx"}[kind]
        ftype = {"xlsx": ("Excel workbook", "*.xlsx"), "pdf": ("PDF", "*.pdf"),
                 "docx": ("Word document", "*.docx")}[kind]
        p = filedialog.asksaveasfilename(defaultextension=ext,
                                         initialfile=f"Net Asset Report - {a['name']}{ext}",
                                         filetypes=[ftype])
        if not p:
            return
        try:
            self.config(cursor="watch")
            self.update()
            {"xlsx": export_excel, "pdf": export_pdf, "docx": export_word}[kind](content, p)
        except PermissionError:
            messagebox.showerror(APP_TITLE, "Could not save — the file may be open in another program.")
            return
        except ModuleNotFoundError as e:
            pkg = {"reportlab": "reportlab", "openpyxl": "openpyxl", "docx": "python-docx",
                   "PIL": "pillow"}.get(e.name, e.name)
            cmd = f'"{sys.executable}" -m pip install {pkg}'
            self.clipboard_clear()
            self.clipboard_append(cmd)
            messagebox.showerror(APP_TITLE, f"The '{pkg}' package is not installed for this Python.\n\n"
                                            f"Run this in Command Prompt (already copied to clipboard):\n\n{cmd}\n\n"
                                            "Then restart the app.")
            return
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Could not create the file:\n{e}")
            return
        finally:
            self.config(cursor="")
        if messagebox.askyesno(APP_TITLE, f"Saved:\n{p}\n\nOpen it now?"):
            open_path(p)

    def trigger_udin_generation(self):
        client_name = self.av.get("name").get().strip()
        cert_date = self.av.get("cert_date").get().strip()
        icai_id = self.sv.get("icai_id").get().strip()
        pwd = self.sv.get("icai_pwd").get().strip()
        frn = self.sv.get("frn").get().strip()

        has_assets = any(item.get("kind") == "asset" for item in self.items)
        if not all((client_name, cert_date, icai_id, pwd, frn)) or not has_assets:
            # Allow the button to be used without entering applicant/CA data here.
            # In that case open the portal for manual completion and send no app data.
            webbrowser.open("https://udin.icai.org/")
            messagebox.showinfo(APP_TITLE,
                "The UDIN portal has been opened for manual use. No applicant or certificate data was sent.\n\n"
                "Complete the UDIN form in the browser. Automatic form filling is available after the client "
                "name, certificate date, at least one asset, FRN, and ICAI login details are entered in the app.")
            return

        imm_total = sum(i["amount"] for i in self.items if i["category"] == "Immovable Property")
        mov_total = sum(i["amount"] for i in self.items if i["category"] != "Immovable Property" and i["kind"] == "asset")

        data = {
            "mrn": icai_id,
            "pwd": pwd,
            "frn": frn,
            "name": client_name,
            "cert_date": cert_date,
            "imm_total": str(round(imm_total)),
            "mov_total": str(round(mov_total))
        }

        messagebox.showinfo(APP_TITLE, "Chrome will now open. Complete the CAPTCHA and login. "
                                       "The script will fill and submit the UDIN form; complete any portal OTP/confirmation when prompted.")
        threading.Thread(target=self._run_selenium_udin, args=(data,), daemon=True).start()

    def _run_selenium_udin(self, data):
        driver = None
        log_path = os.path.join(tempfile.gettempdir(), "networth_udin_debug.log")
        diagnostic_context = []

        def write_debug_log(exc):
            """Save diagnostic details without writing ICAI credentials to disk."""
            try:
                import selenium
                selenium_version = getattr(selenium, "__version__", "unknown")
            except Exception:
                selenium_version = "not available"
            try:
                with open(log_path, "w", encoding="utf-8") as log:
                    log.write("UDIN automation diagnostic log\n")
                    log.write(f"Time: {datetime.datetime.now().isoformat()}\n")
                    log.write(f"Python: {sys.version}\n")
                    log.write(f"Platform: {platform.platform()}\n")
                    log.write(f"App executable: {sys.executable}\n")
                    log.write(f"Selenium version: {selenium_version}\n")
                    log.write(f"Driver started: {driver is not None}\n")
                    if driver is not None:
                        try:
                            log.write(f"Current page URL (query removed): {driver.current_url.split('?')[0].split('#')[0]}\n")
                            log.write(f"Current page title: {driver.title}\n")
                            controls = []
                            for tag in ("input", "select", "mat-select", "textarea", "button"):
                                for control in driver.find_elements(By.XPATH, f"//{tag}"):
                                    if control.is_displayed():
                                        controls.append((tag, {key: control.get_attribute(key) for key in
                                            ("type", "id", "name", "placeholder", "aria-label")
                                            if control.get_attribute(key)}))
                            log.write(f"Visible controls (attributes only; values omitted): {controls!r}\n")
                        except Exception as info_error:
                            log.write(f"Page details unavailable: {info_error!r}\n")
                    for item in diagnostic_context:
                        log.write(f"\n{item}\n")
                    if driver is not None:
                        try:
                            caps = driver.capabilities or {}
                            log.write(f"Browser: {caps.get('browserName')} {caps.get('browserVersion')}\n")
                            log.write(f"ChromeDriver: {caps.get('chrome', {}).get('chromedriverVersion', 'unknown')}\n")
                            log.write(f"Session created: {bool(driver.session_id)}\n")
                        except Exception as info_error:
                            log.write(f"Browser details unavailable: {info_error!r}\n")
                    log.write(f"Exception type: {type(exc).__module__}.{type(exc).__name__}\n")
                    log.write(f"Exception repr: {exc!r}\n\n")
                    for attr in ("msg", "stacktrace"):
                        value = getattr(exc, attr, None)
                        if value:
                            log.write(f"Selenium {attr}:\n{value}\n\n")
                    log.write("Python traceback:\n")
                    log.write(traceback.format_exc())
                    log.write("\n\nICAI username/password are not included by this logger.\n")
            except Exception:
                pass
            return log_path

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service as ChromeService
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait, Select
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException, WebDriverException

            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-gpu")
            service = ChromeService()
            service.creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            driver = webdriver.Chrome(options=options, service=service)

            def visible_inputs():
                return [field for field in driver.find_elements(By.XPATH, "//input") if field.is_displayed()]

            def input_description(field):
                return {key: field.get_attribute(key) for key in
                        ("type", "id", "name", "placeholder", "aria-label", "autocomplete")
                        if field.get_attribute(key)}

            def find_username():
                fields = visible_inputs()
                # Prefer semantic attributes; older portal markup used name="userName".
                for field in fields:
                    attrs = " ".join((field.get_attribute(key) or "") for key in
                                     ("id", "name", "placeholder", "aria-label", "autocomplete")).lower()
                    if any(word in attrs for word in ("username", "user_name", "memberid", "member_id")):
                        return field
                return next((field for field in fields if (field.get_attribute("type") or "text").lower()
                             in ("text", "email") and "captcha" not in str(input_description(field)).lower()), None)

            wait = WebDriverWait(driver, 30)
            # The UDIN home page redirects to /ICAI, which does not expose the
            # member login inputs. Open the portal's login route directly.
            driver.get("https://udin.icai.org/ICAI/login")
            username_field = find_username()
            if username_field is None:
                # The current ICAI home screen exposes the login form through its Login button.
                login_buttons = driver.find_elements(By.XPATH,
                    "//*[self::a or self::button or @role='button'][normalize-space(translate(., 'LOGIN', 'login'))='login']")
                login_buttons = [button for button in login_buttons if button.is_displayed()]
                if login_buttons:
                    login_buttons[0].click()
                try:
                    username_field = WebDriverWait(driver, 20).until(lambda _d: find_username())
                except TimeoutException:
                    input_details = [input_description(field) for field in visible_inputs()]
                    diagnostic_context.append(f"Login page URL: {driver.current_url}")
                    diagnostic_context.append(f"Login page title: {driver.title}")
                    diagnostic_context.append(f"Visible input attributes: {input_details!r}")
                    diagnostic_context.append("Login button candidates found: " + str(len(login_buttons)))
                    raise RuntimeError("Could not locate the username field after opening the UDIN login page. "
                                       "The diagnostic log now includes the visible page controls.")

            username_field.send_keys(data["mrn"])
            password_fields = [field for field in visible_inputs()
                               if (field.get_attribute("type") or "").lower() == "password"]
            if not password_fields:
                diagnostic_context.append(f"Visible login inputs: {[input_description(field) for field in visible_inputs()]!r}")
                raise RuntimeError("Could not locate the visible password field on the UDIN login form.")
            password_fields[0].send_keys(data["pwd"])

            def field_by_hint(tag, hint):
                needle = hint.lower()
                for field in driver.find_elements(By.XPATH, f"//{tag}"):
                    if not field.is_displayed():
                        continue
                    attrs = " ".join((field.get_attribute(a) or "") for a in
                                     ("id", "name", "placeholder", "aria-label", "title"))
                    field_id = field.get_attribute("id")
                    labels = driver.find_elements(By.XPATH, f"//label[@for='{field_id}']") if field_id else []
                    if needle in (attrs + " " + " ".join(label.text for label in labels)).lower():
                        return field
                raise RuntimeError(f"Could not find the visible {hint} field. The UDIN portal form may have changed.")

            def choose(hint, value):
                control = Select(field_by_hint("select", hint))
                available = [option.text.strip() for option in control.options]
                match = next((text for text in available if text.lower() == value.lower()), None)
                if match is None:
                    raise RuntimeError(f"No {value!r} option for {hint}. Available options: {', '.join(available)}")
                control.select_by_visible_text(match)
                time.sleep(1)  # allow dependent portal dropdowns to refresh

            # The user completes CAPTCHA and clicks Login. A disappeared password
            # field alone is not proof of login (the portal also has a 403 page).
            generate_nav_xpath = (
                "//*[self::a or self::button or @role='button' or @role='menuitem']"
                "[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='generate udin']"
            )
            def login_status(d):
                page_url = d.current_url.lower()
                page_text = d.find_element(By.TAG_NAME, "body").text.lower()
                if "/unauthorized" in page_url or "error 403" in page_text or "not authorized to access" in page_text:
                    return "denied"
                if (any(item.is_displayed() for item in d.find_elements(By.XPATH, generate_nav_xpath))
                        or any(item.is_displayed() for item in d.find_elements(By.XPATH,
                            "//*[contains(translate(normalize-space(.), 'LOGOUT', 'logout'), 'logout')]"))):
                    return "authenticated"
                return False

            try:
                status = WebDriverWait(driver, 300).until(login_status)
            except TimeoutException:
                page_text = driver.find_element(By.TAG_NAME, "body").text[:1500]
                for secret in (data.get("mrn", ""), data.get("pwd", "")):
                    if secret:
                        page_text = page_text.replace(secret, "[redacted]")
                diagnostic_context.append(f"Post-login wait URL: {driver.current_url.split('?')[0].split('#')[0]}")
                diagnostic_context.append(f"Post-login page text: {page_text!r}")
                raise RuntimeError("Login was not confirmed. Complete CAPTCHA and sign in; the portal must show its "
                                   "member dashboard before UDIN generation can continue.")
            if status == "denied":
                diagnostic_context.append(f"Access-denied URL: {driver.current_url.split('?')[0].split('#')[0]}")
                diagnostic_context.append(f"Access-denied page text: {driver.find_element(By.TAG_NAME, 'body').text[:1000]!r}")
                raise RuntimeError("The ICAI portal returned an unauthorized (403) page before login completed. "
                                   "The portal is denying this browser session, so the UDIN form cannot be automated.")

            wait = WebDriverWait(driver, 30)
            try:
                nav_item = wait.until(lambda d: next((item for item in d.find_elements(By.XPATH, generate_nav_xpath)
                                                       if item.is_displayed()), False))
                nav_item.click()
                wait.until(EC.presence_of_element_located((By.XPATH, "//select | //input | //textarea")))
            except TimeoutException:
                diagnostic_context.append(f"After-login URL: {driver.current_url.split('?')[0].split('#')[0]}")
                diagnostic_context.append(f"After-login title: {driver.title}")
                raise RuntimeError("The authenticated dashboard did not expose a Generate UDIN navigation item or form. "
                                   "The portal may have changed or denied access.")

            def choose_autocomplete(field, typed_value, match_text, label):
                field.click()
                try:
                    field.clear()
                    field.send_keys(typed_value)
                except Exception:
                    set_portal_input(field, typed_value)
                option_xpath = "//mat-option | //*[@role='option']"
                try:
                    options_found = WebDriverWait(driver, 10).until(lambda d: [
                        option for option in d.find_elements(By.XPATH, option_xpath) if option.is_displayed()
                    ])
                except TimeoutException:
                    options_found = []
                wanted = match_text.lower()
                option = next((item for item in options_found if wanted in item.text.strip().lower()), None)
                if option is None:
                    available = [item.text.strip() for item in options_found]
                    raise RuntimeError(f"Could not match {label} {match_text!r}. Portal options: {available!r}")
                option.click()
                time.sleep(0.5)

            def set_portal_input(field, value):
                """Set a text control, falling back to Angular-compatible input events."""
                try:
                    field.click()
                    field.clear()
                    field.send_keys(value)
                except Exception:
                    driver.execute_script("""
                        const el = arguments[0], value = arguments[1];
                        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                        setter.call(el, value);
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    """, field, value)

            step_failures = []

            def run_form_step(label, action):
                try:
                    action()
                    diagnostic_context.append(f"UDIN step completed: {label}")
                    return True
                except Exception as step_error:
                    full_error = str(step_error)
                    step_failures.append((label, full_error.split("Stacktrace:", 1)[0].split("(Session info:", 1)[0].strip()))
                    diagnostic_context.append(f"UDIN step failed: {label}: {type(step_error).__name__}: {full_error}")
                    return False

            # Current portal uses Angular Material autocomplete inputs rather than <select>.
            frn_code = data["frn"].strip().split()[0]
            run_form_step("Firm Registration Number", lambda: choose_autocomplete(
                driver.find_element(By.ID, "FRN"), frn_code, frn_code, "FRN"))

            # Certificates is the default category; choose the net worth certificate subtype.
            run_form_step("Certificate type", lambda: choose_autocomplete(
                driver.find_element(By.ID, "certficateType"), "net worth", "net worth", "certificate type"))

            date_value = data["cert_date"].replace(".", "-").replace("/", "-")
            def fill_signing_date():
                date_field = next((field for field in driver.find_elements(By.XPATH, "//input")
                                   if field.is_displayed() and "dd-mm-yyyy" in
                                   (field.get_attribute("placeholder") or "").lower()), None)
                if date_field is None:
                    raise RuntimeError("Could not find the document signing date field (DD-MM-YYYY).")
                set_portal_input(date_field, date_value)
                close_calendar()

            def close_calendar():
                open_picker = any(item.is_displayed() for item in driver.find_elements(
                    By.XPATH, "//*[contains(@class, 'mat-datepicker-content') or contains(@class, 'mat-calendar')]") )
                if not open_picker:
                    return
                toggles = [item for item in driver.find_elements(By.XPATH,
                    "//button[@aria-label='Open calendar']") if item.is_displayed()]
                try:
                    if toggles:
                        toggles[0].click()
                    else:
                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                except Exception:
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)

            run_form_step("Signing date", fill_signing_date)

            # Two mandatory numerical rows are required. Current Angular markup has
            # no <tr>, so pair controls by their explicit placeholders and row container.
            figure_rows = []
            def locate_figure_rows():
                particulars = [field for field in driver.find_elements(By.XPATH, "//input")
                               if field.is_displayed() and (field.get_attribute("placeholder") or "").strip().lower() == "particulars"]
                figures = [field for field in driver.find_elements(By.XPATH, "//input")
                           if field.is_displayed() and (field.get_attribute("placeholder") or "").strip().lower() == "figures in inr"]
                for particular, figure in zip(particulars, figures):
                    row = driver.execute_script("""
                        const p = arguments[0], f = arguments[1];
                        let node = p.parentElement;
                        while (node && node !== document.body) {
                          const inputs = Array.from(node.querySelectorAll('input'));
                          const ps = inputs.filter(x => (x.placeholder || '').trim().toLowerCase() === 'particulars');
                          const fs = inputs.filter(x => (x.placeholder || '').trim().toLowerCase() === 'figures in inr');
                          if (ps.length === 1 && fs.length === 1 && ps[0] === p && fs[0] === f) return node;
                          node = node.parentElement;
                        }
                        return null;
                    """, particular, figure)
                    if row:
                        figure_rows.append((row, particular, figure))
                if len(figure_rows) < 2:
                    diagnostic_context.append(f"Figure table rows found: {len(figure_rows)}")
                    diagnostic_context.append(f"Visible inputs after selecting certificate: {[input_description(f) for f in visible_inputs()]!r}")
                    raise RuntimeError("Could not identify the two required financial figure rows.")

            run_form_step("Locate required figure rows", locate_figure_rows)

            def fill_figure_row(row_index, particular, amount):
                row, particular_field, figure_field = figure_rows[row_index]
                set_portal_input(particular_field, particular)
                set_portal_input(figure_field, amount)
                # The "Actual" text box is the converted-value display; the
                # denomination itself is the separate Angular Material dropdown.
                denominators = [item for item in row.find_elements(By.XPATH,
                    ".//ng-select | .//mat-select | .//select | .//*[@role='combobox'] | .//*[@aria-haspopup='listbox'] | .//button[contains(@class,'select')]")
                    if item.is_displayed()]
                if not denominators:
                    controls = driver.execute_script("""
                        return Array.from(arguments[0].querySelectorAll('*')).map(el => ({
                          tag: el.tagName, role: el.getAttribute('role'),
                          aria: el.getAttribute('aria-label'), popup: el.getAttribute('aria-haspopup'),
                          cls: String(el.className || '').slice(0, 100),
                          text: (el.innerText || '').trim().slice(0, 60)
                        })).filter(x => x.role || x.popup || /select|option|dropdown/i.test(x.cls)).slice(0, 30);
                    """, row)
                    diagnostic_context.append(f"Denomination control DOM: {controls!r}")
                    raise RuntimeError("The denomination dropdown was not visible.")
                denominator = denominators[0]
                if denominator.tag_name.lower() == "ng-select":
                    container = denominator.find_element(By.CSS_SELECTOR, ".ng-select-container")
                    driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", container)
                    try:
                        container.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", container)
                    actual = WebDriverWait(driver, 10).until(lambda d: next((item for item in
                        d.find_elements(By.XPATH, "//ng-dropdown-panel//div[contains(@class,'ng-option')]")
                        if item.is_displayed() and "actual" in item.text.strip().lower()), False))
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", actual)
                    try:
                        actual.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", actual)
                    if "actual" not in denominator.text.strip().lower():
                        raise RuntimeError("The ng-select did not retain the Actual denomination.")
                elif denominator.tag_name.lower() == "select":
                    Select(denominator).select_by_visible_text("Actual")
                else:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", denominator)
                    denominator.click()
                    actual = WebDriverWait(driver, 10).until(lambda d: next((item for item in
                        d.find_elements(By.XPATH, "//mat-option | //*[@role='option'] | //ng-dropdown-panel//div[contains(@class,'ng-option')]")
                        if item.is_displayed() and "actual" in item.text.strip().lower()), False))
                    actual.click()

            if len(figure_rows) >= 2:
                run_form_step("Immovable assets figure", lambda: fill_figure_row(
                    0, "Total Immovable Assets", data["imm_total"]))
                run_form_step("Movable assets figure", lambda: fill_figure_row(
                    1, "Total Movable Assets", data["mov_total"]))

            def fill_document_description():
                close_calendar()
                description = next((field for field in driver.find_elements(By.XPATH, "//textarea")
                                    if field.is_displayed() and "details of the document" in
                                    (field.get_attribute("placeholder") or "").lower()), None)
                if description is None:
                    raise RuntimeError("Could not find the required Document Description field.")
                narration = "Net Asset Report for Embassy Purpose"
                try:
                    description.clear()
                    description.send_keys(narration)
                except Exception:
                    driver.execute_script("""
                        const el = arguments[0], value = arguments[1];
                        const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
                        setter.call(el, value);
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    """, description, narration)

            run_form_step("Document description", fill_document_description)

            if step_failures:
                summary = "\n".join(f"• {label}: {reason}" for label, reason in step_failures)
                log_path = write_debug_log(RuntimeError("Recoverable UDIN form step errors"))
                self.after(0, lambda summary=summary, path=log_path: messagebox.showwarning(APP_TITLE,
                    "Some UDIN fields could not be filled automatically. Chrome is still open, and the other "
                    "steps were attempted. Complete the listed fields manually, then click Send OTP in Chrome.\n\n"
                    f"{summary}\n\nDiagnostic log: {path}"))
                return

            # Deliberate review boundary: do not request an OTP or submit remotely.
            self.after(0, lambda: messagebox.showinfo(APP_TITLE,
                "The UDIN form has been filled for your review. In Chrome, check all values, "
                "click Send OTP yourself, enter/verify the OTP, review the preview, and click Submit. "
                "The app will capture the UDIN only after you complete those steps."))

            WebDriverWait(driver, 600).until(lambda d: "generated successfully" in d.page_source.lower())
            page_text = driver.find_element(By.TAG_NAME, "body").text
            match = re.search(r"\bUDIN\s*:\s*([A-Z0-9]{18})\b", page_text, re.IGNORECASE)
            generated_udin = match.group(1) if match else ""
            if generated_udin:
                self.after(0, lambda value=generated_udin: self.av["udin"].set(value))
            self.after(0, lambda value=generated_udin: messagebox.showinfo(APP_TITLE,
                "UDIN generated successfully." + (f"\n\nUDIN: {value}\nIt has been copied to the UDIN field." if value else
                "\n\nCheck the open Chrome window for the generated UDIN.")))

        except ImportError as e:
            log_path = write_debug_log(e)
            self.after(0, lambda path=log_path: messagebox.showerror(APP_TITLE,
                f"Selenium is not installed or could not be imported.\n\nRun:\n\"{sys.executable}\" -m pip install --upgrade selenium\n\nDiagnostic log:\n{path}"))
        except WebDriverException as e:
            log_path = write_debug_log(e)
            detail = (getattr(e, "msg", "") or str(e)).split("Stacktrace:", 1)[0].strip()
            if not detail or detail.lower() in ("message:", "unknown error"):
                detail = "ChromeDriver could not start a Chrome session."
            self.after(0, lambda detail=detail: messagebox.showerror(APP_TITLE,
                f"UDIN browser automation failed:\n{detail}\n\nFull diagnostic log saved to:\n{log_path}"))
        except Exception as e:
            log_path = write_debug_log(e)
            detail = str(e).split("Stacktrace:", 1)[0].strip() or type(e).__name__
            self.after(0, lambda detail=detail: messagebox.showerror(APP_TITLE,
                f"UDIN automation stopped:\n{detail}" +
                ("\n\nChrome has been left open so you can inspect the portal form." if driver else "") +
                f"\n\nFull diagnostic log saved to:\n{log_path}"))


if __name__ == "__main__":
    raise SystemExit("This is a support library. Start Launch Net Asset Report.vbs or net_asset_report.py.")
