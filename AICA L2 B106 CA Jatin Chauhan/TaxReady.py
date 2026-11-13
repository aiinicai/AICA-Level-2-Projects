"""
TaxReady - By CA Jatin Chauhan  |  Know your tax before you file
(single-file PyQt desktop utility for Windows).

What it does
------------
* Accepts PAN, e-Filing password, Financial Year and a download folder.
* Decrypts the downloaded AIS locally, computes a tentative income-tax review (old vs new
  regime) and saves ONLY the Word report in the client folder (the downloaded and decrypted
  AIS files are deleted).
* Optionally emails that Word report to the client through Gmail - after the user has
  reviewed the computation, or automatically when review is switched off.
* Maintains a local client register and download/email activity history.
* Imports and exports client details, including a blank password template column.
* Opens a visible Chrome/Edge/Chromium browser using Playwright.
* Logs in to the official Income-tax e-Filing portal.
* Navigates to Annual Information Statement (AIS), selects the FY and
  requests the AIS JSON download.
* Pauses for CAPTCHA/manual portal confirmation (CAPTCHA is never bypassed).
* Detects the completed download, validates it and saves it with an audit-
  friendly filename.

Security
--------
Saved e-Filing passwords are encrypted with Windows DPAPI and can be decrypted
only by the same Windows user account. Passwords are never printed, placed in
logs, exported to CSV, or stored in the temporary browser profile.
Gmail uses its 16-character App Password over encrypted SMTP. The App Password
is protected with Windows DPAPI. A fresh temporary browser profile is removed
after each run.

Run from IDLE: open this file and press F5 (Run Module).
"""

# ---------------------------------------------------------------------------
# Dependency bootstrap: only Python's standard library is used before this.
# ---------------------------------------------------------------------------
import base64
import csv
import ctypes
import importlib.util
import json
import mimetypes
import os
import re
import shutil
import smtplib
import socket
import sqlite3
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import zipfile
from datetime import date, datetime
from email.message import EmailMessage
from html import escape
from pathlib import Path
from ctypes import wintypes
from urllib.parse import urljoin


REQUIRED_PACKAGES = {
    "PyQt6": "PyQt6>=6.7,<7",
    "playwright": "playwright>=1.49,<2",
    "docx": "python-docx",
    "matplotlib": "matplotlib",
    "Crypto": "pycryptodome",
}


def _show_bootstrap_error(message):
    """Show an installation failure even when launched from IDLE."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("TaxReady - setup failed", message)
        root.destroy()
    except Exception:
        print(message)


def ensure_dependencies():
    missing = [spec for module, spec in REQUIRED_PACKAGES.items()
               if importlib.util.find_spec(module) is None]
    if not missing:
        return

    print("AIS Auto Downloader: installing required Python libraries...")
    command = [
        sys.executable, "-m", "pip", "install", "--upgrade",
        "--disable-pip-version-check", *missing,
    ]
    try:
        subprocess.check_call(command)
        importlib.invalidate_caches()
    except Exception as exc:
        manual = (
            f'"{sys.executable}" -m pip install --upgrade PyQt6 playwright python-docx matplotlib pycryptodome'
        )
        message = (
            "Automatic library installation could not finish.\n\n"
            f"Reason: {exc}\n\n"
            "Run this command in Command Prompt, then reopen the file:\n"
            f"{manual}"
        )
        _show_bootstrap_error(message)
        raise SystemExit(1)


ensure_dependencies()

from PyQt6.QtCore import QObject, QSettings, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# =====================================================================================
# EMBEDDED 1/2: AIS DECRYPTOR (from AIS_Decryptor.py) - runs locally, nothing is sent anywhere
# =====================================================================================
import hashlib
from Crypto.Cipher import AES


PASSWORD_MIDDLE = "GQ39%*g"


PBKDF2_ITERATIONS = 1000


def load_encrypted_payload(filepath):
    """Return (iv, salt, [ciphertext candidates]) from the encrypted file."""
    raw = Path(filepath).read_text(encoding="utf-8-sig").strip()

    # Some tools export the encrypted AIS string as a JSON string.
    if len(raw) >= 2 and raw.startswith('"') and raw.endswith('"'):
        raw = json.loads(raw)
    raw = "".join(raw.split())  # remove stray whitespace / line breaks

    if len(raw) < 64:
        raise ValueError(
            "Encrypted AIS file is too short.\n"
            "Expected: IV (32 hex) + salt (32 hex) + ciphertext."
        )

    try:
        iv = bytes.fromhex(raw[:32])
        salt = bytes.fromhex(raw[32:64])
    except ValueError:
        raise ValueError(
            "The first 64 characters of the file must be hexadecimal (IV + salt).\n"
            "This does not look like an encrypted AIS utility JSON file."
        )

    body = raw[64:]
    candidates = []
    # A hex string is also valid Base64, so keep both interpretations and let
    # the decryption step decide which one is correct.
    try:
        candidates.append(base64.b64decode(body, validate=True))
    except Exception:
        pass
    try:
        candidates.append(bytes.fromhex(body))
    except ValueError:
        pass

    candidates = [c for c in candidates if c and len(c) % AES.block_size == 0]
    if not candidates:
        raise ValueError("Ciphertext is empty or is not valid Base64 / hexadecimal data.")
    return iv, salt, candidates


def password_candidates(pan, dob, password_middle=None, password=None):
    if password:
        return [password]
    lower_pan, upper_pan = pan.lower(), pan.upper()
    if password_middle:
        options = [f"{lower_pan}{password_middle}{dob}"]
    else:
        options = [
            f"{lower_pan}{PASSWORD_MIDDLE}{dob}",
            f"{lower_pan}{dob}",
            f"{upper_pan}{dob}",
        ]
    unique = []
    for item in options:
        if item not in unique:
            unique.append(item)
    return unique


def _decrypt_once(iv, salt, ciphertext, password):
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt,
                              PBKDF2_ITERATIONS, dklen=32)
    padded = AES.new(key, AES.MODE_CBC, iv).decrypt(ciphertext)

    # PKCS#7 un-padding with validation
    pad_len = padded[-1]
    if pad_len < 1 or pad_len > 16 or padded[-pad_len:] != bytes([pad_len]) * pad_len:
        raise ValueError("bad padding")
    text = padded[:-pad_len].decode("utf-8-sig")
    return json.loads(text)  # must be valid JSON to count as success


def decrypt_ais_file(filepath, pan, dob, password_middle=None, password=None):
    """Decrypt and return the parsed JSON data (dict / list)."""
    iv, salt, ciphertexts = load_encrypted_payload(filepath)
    for pwd in password_candidates(pan, dob, password_middle, password):
        for ct in ciphertexts:
            try:
                return _decrypt_once(iv, salt, ct, pwd)
            except Exception:
                continue
    raise ValueError(
        "Decryption failed.\n"
        "Please check your PAN and Date of Birth, and make sure the file is the "
        "encrypted AIS JSON downloaded from the portal.\n"
        "If needed, use the Advanced options."
    )


# =====================================================================================
# EMBEDDED 2/2: INCOME TAX CALCULATOR ENGINE + WORD REPORT (from Income_Tax_Calculator_from_AIS.py)
# Estimate for information only; not tax advice. Nothing is ever filed.
# =====================================================================================
import datetime as _dt
import io
import math
from decimal import Decimal, ROUND_HALF_UP
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

CALC_APP_NAME = "TaxReady"

D = Decimal
DISCLAIMER = ("Estimate for information only; not tax advice; verify against the official "
              "Income Tax portal and consult a CA before filing.")

# =====================================================================================
# 1. STYLE CONSTANTS  (every colour / font / size of the Word report lives here)
# =====================================================================================
NAVY, STEEL, BODY, GREY = "1F3864", "2E5597", "262626", "7F7F7F"
LIGHT_BLUE, AMBER, AMBER_EDGE = "DEEAF6", "FFF2CC", "BF9000"
ALT_ROW, BORDER, CHART_LIGHT, WHITE = "F2F2F2", "BFBFBF", "9DC3E6", "FFFFFF"
BAND_SUB = "BDD7EE"                    # light blue text on navy band / dark tiles
CHART_EXTRA = ["5B9BD5", "7F7F7F", "A5A5A5"]   # extra heads (salary, house property, winnings)
FONT_BODY, FONT_HEAD = "Calibri", "Cambria"
PAGE_W_CM, PAGE_H_CM = 21.0, 29.7
MARGIN_TB_CM, MARGIN_LR_CM = 2.54, 2.2
CONTENT_W_CM = 16.6
SZ_BODY, SZ_TABLE, SZ_TABLE_WIDE, SZ_NOTE = 11, 10, 9, 9
RUPEE = "₹"
ZWSP = "​"


# =====================================================================================
# 2. RULES (versioned, per year).  Seeded values -- status "VERIFY" until checked
#    against the Finance Acts.  Keep ONE entry per year.
# =====================================================================================
_OLD_SLABS = {"gen": [(250000, 0), (500000, 5), (1000000, 20), (None, 30)],
              "sr": [(300000, 0), (500000, 5), (1000000, 20), (None, 30)],
              "ssr": [(500000, 0), (1000000, 20), (None, 30)]}
_NEW_20 = [(250000, 0), (500000, 5), (750000, 10), (1000000, 15), (1250000, 20), (1500000, 25), (None, 30)]
_NEW_23 = [(300000, 0), (600000, 5), (900000, 10), (1200000, 15), (1500000, 20), (None, 30)]
_NEW_24 = [(300000, 0), (700000, 5), (1000000, 10), (1200000, 15), (1500000, 20), (None, 30)]
_NEW_25 = [(400000, 0), (800000, 5), (1200000, 10), (1600000, 15), (2000000, 20), (2400000, 25), (None, 30)]
_CG_OLD = {"111A": 15, "112A": 10, "112": 20}
_CG_NEW = {"111A": 20, "112A": 12.5, "112": 12.5}
SURCHARGE_STEPS = [(5000000, 10), (10000000, 15), (20000000, 25), (50000000, 37)]
CESS_PCT = 4
CG_SPLIT_DATE = _dt.date(2024, 7, 23)

_SRC_GENERIC = ["Income Tax Department - Tax slabs and rates for the year (VERIFY)",
                "Finance Act of the relevant year (VERIFY)"]
_SRC_2526 = ["Income Tax Department - Salaried Individuals for AY 2026-27",
             "Finance Bill 2025 Memorandum"]


def _year(fy, new_slabs, new_std, new_rebate, new_rebate_max, cg_mode, cap_new, sp_rebate_new, sources):
    start = int(fy[:4])
    ay = "%d-%02d" % (start + 1, (start + 2) % 100)
    act = "2025" if start >= 2026 else "1961"
    return {"fy": fy, "ay": ay, "act": act, "start": start,
            "label": ("Tax Year %s (Income-tax Act, 2025)" % fy) if act == "2025"
            else "FY %s (AY %s) (Income-tax Act, 1961)" % (fy, ay),
            "new": {"slabs": new_slabs, "std": new_std, "rebate_limit": new_rebate,
                    "rebate_max": new_rebate_max, "rebate_special": sp_rebate_new,
                    "marginal_relief": start >= 2023, "sur_cap": cap_new},
            "old": {"slabs": _OLD_SLABS, "std": 50000, "rebate_limit": 500000, "rebate_max": 12500,
                    "rebate_special": True, "marginal_relief": False, "sur_cap": 37},
            "cg_mode": cg_mode,
            "cg_exempt": 100000 if cg_mode == "old" else 125000,
            "sources": sources, "status": "VERIFY - entered from public sources, not yet checked against the Finance Act; re-check before filing",
            "last_verified": None}


RULES = {
    "2020-21": _year("2020-21", _NEW_20, 0, 500000, 12500, "old", 37, True, _SRC_GENERIC),
    "2021-22": _year("2021-22", _NEW_20, 0, 500000, 12500, "old", 37, True, _SRC_GENERIC),
    "2022-23": _year("2022-23", _NEW_20, 0, 500000, 12500, "old", 37, True, _SRC_GENERIC),
    "2023-24": _year("2023-24", _NEW_23, 50000, 700000, 25000, "old", 25, True, _SRC_GENERIC),
    "2024-25": _year("2024-25", _NEW_24, 75000, 700000, 25000, "split", 25, True, _SRC_GENERIC),
    "2025-26": _year("2025-26", _NEW_25, 75000, 1200000, 60000, "new", 25, False, _SRC_2526),
    "2026-27": _year("2026-27", _NEW_25, 75000, 1200000, 60000, "new", 25, False, _SRC_2526),
}
# Section crosswalk (1961 -> 2025).  Only mappings given in the brief are filled; others = VERIFY.
SECTION_XWALK = {"115BAC": "202", "TDS (192/194x)": "393 (table)", "111A": "VERIFY", "112A": "VERIFY",
                 "112": "VERIFY", "87A": "VERIFY", "115BB": "VERIFY"}


def get_rules(fy):
    if fy not in RULES:
        raise KeyError("No rules file for FY %s. Add an entry to RULES (slabs, rebate, CG rates) before computing." % fy)
    return RULES[fy]


# =====================================================================================
# 3. NUMBER HELPERS
# =====================================================================================
def q0(x):
    return int(D(str(x)).quantize(D("1"), rounding=ROUND_HALF_UP))


def r10(x):
    return int((D(str(x)) / 10).quantize(D("1"), rounding=ROUND_HALF_UP)) * 10


def inr_group(n):
    n = q0(n)
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return sign + s


def money(n, sym=RUPEE):
    if n is None:
        return "-"
    v = q0(n)
    return ("-" if v < 0 else "") + sym + inr_group(abs(v))


def pct(rate):
    r = D(str(rate))
    return "0%" if r == 0 else "%.2f%%" % r


def parse_amt(s):
    if s is None:
        return None
    t = str(s).replace(",", "").strip()
    if t == "":
        return None
    try:
        return D(t)
    except Exception:
        return None


def mask_pan(pan):
    pan = (pan or "").strip().upper()
    return "XXXXX" + pan[5:] if len(pan) == 10 else "XXXXXXXXXX"


def parse_date(s):
    try:
        return _dt.datetime.strptime(str(s).strip(), "%d/%m/%Y").date()
    except Exception:
        return None


# =====================================================================================
# 4. AIS PARSER (portal JSON, "jsonVersion 15")  + classification
# =====================================================================================
HEAD_LABELS = {"salary": "Salary", "hp": "Income from house property", "cg": "Capital gains",
               "business": "Business/profession", "other": "Other sources",
               "winnings": "Winnings (s.115BB)", "info": "Not income (information only)",
               "unclassified": "Unclassified", "tcs": "TCS (credit only)"}
INCOME_HEADS = ["salary", "hp", "cg", "business", "other", "winnings"]
BUSINESS_SECS = {"194C", "194D", "194G", "194H", "194J", "194J(A)", "194J(B)", "194O", "194M", "194Q", "194R",
                 "194T"}      # 194T: salary, remuneration, commission, bonus or interest paid by a firm to a partner (s.28(v))
OTHER_SECS = {"194A", "193", "194", "194K", "192A", "194EE"}
LOTTERY_SECS = {"194B", "194BA", "194BB"}
INFO_SECS = {"194N", "194IA", "194IB_PURCHASE"}


def norm_code(code):
    return re.sub(r"\s+", "", str(code or "")).upper()


def classify(code, category="", desc=""):
    """Map an AIS information code to a head.  Anything unknown -> 'unclassified' (never guessed)."""
    c = norm_code(code)
    t = (str(code) + " " + str(category) + " " + str(desc)).upper()
    if c.startswith("TCS"):
        return "tcs"
    if c.startswith("TDS-"):
        s = c[4:]
        if s == "192":
            return "salary"
        if s.startswith("194I") and s != "194IA":
            return "hp"
        if s in BUSINESS_SECS:
            return "business"
        if s in OTHER_SECS:
            return "other"
        if s in LOTTERY_SECS:
            return "winnings"
        if s in INFO_SECS:
            return "info"
        return "unclassified"
    if c.startswith("SFT"):
        if c.startswith("SFT-015") or c.startswith("SFT-016"):
            return "other"
        if re.match(r"SFT-0?17", c):
            return "cg" if ("SALE" in t) else "info"
        return "info"          # remaining SFT reports (cash deposits, credit card, property ...)
    return "unclassified"


def _find(fields, *names):
    for n in names:
        if n in fields:
            return fields.index(n)
    return None


def _cell(row, idx):
    return row[idx] if (idx is not None and idx < len(row)) else None


def _l2_rows(el):
    l2 = el.get("l2") or {}
    cols = l2.get("columnLabel") or []
    out = []
    for r in l2.get("columnData") or []:
        out.append({cols[i]: r[i] for i in range(min(len(cols), len(r)))})
    return out


def _status_text(status, feedback):
    parts = [str(x).strip() for x in (status, feedback) if x not in (None, "")]
    return " / ".join(p for p in parts if p)


def parse_ais_json(path):
    """Portal JSON -> common-schema dict: meta + records[] + challans[] + refunds[]."""
    with open(path, "r", encoding="utf-8-sig") as fh:
        data = json.load(fh)
    pa = data.get("partA", {})
    pa_map = dict(zip(pa.get("columnLabel", []), pa.get("columnData", [])))
    hdr = (data.get("header", {}).get("columnData") or [""])[0]
    pan = pa_map.get("Permanent Account Number (PAN)") or data.get("metadata", {}).get("loggedInPan", "")
    ais = {"pan": pan, "name": pa_map.get("Name of Assessee", ""), "dob": pa_map.get("Date of Birth", ""),
           "fy": hdr, "records": [], "challans": [], "refunds": [], "warnings": [],
           "source_file": os.path.basename(path)}
    rid = 0
    for sec in data.get("partB", {}).get("sections", []):
        key = sec.get("sectionKey")
        elements = list(sec.get("elements") or [])
        for sub in sec.get("subSections") or []:
            elements += sub.get("elements") or []
        if key == "paymentOfTaxes":
            for el in elements:
                labels = el.get("columnLabel") or []
                for n, r in enumerate(el.get("columnData") or []):
                    m = dict(zip(labels, r))
                    ais["challans"].append({
                        "minor": str(m.get("Minor Head", "")), "total": parse_amt(m.get("Total (A+B+C+D)")) or D(0),
                        "bsr": m.get("BSR Code"), "date": m.get("Date Of Deposit"),
                        "serial": m.get("Challan Serial Number"), "ref": "Part B3, row %d" % (n + 1)})
            continue
        if key == "demandAndRefund":
            for el in elements:
                labels = el.get("columnLabel") or []
                for r in el.get("columnData") or []:
                    ais["refunds"].append(dict(zip(labels, r)))
            continue
        part = {"tdsTcs": "Part B1", "sft": "Part B2", "other-info": "Part B7"}.get(key, key)
        for ei, el in enumerate(elements):
            l2rows = _l2_rows(el)
            if not l2rows:
                continue
            l2 = l2rows[0]
            code, category = l2.get("Information Code", ""), l2.get("Information Category", el.get("title", ""))
            desc, source = l2.get("Information Description", ""), l2.get("Information Source", "")
            head = classify(code, category, desc)
            l1src = el.get("l1Src") or "-"
            base = {"code": code, "category": category, "desc": desc, "source_name": source, "l1src": l1src, "head": head,
                    "catcode": l2.get("Information Category Code") or default_catcode(code, category),
                    "l2_amount": parse_amt(l2.get("Amount")), "elem": (part, ei)}
            l1 = el.get("l1")
            if head == "cg" and l1 and "salesConsideration" in [x["field"] for x in l1.get("columnLabel", [])]:
                # one record per transaction: sale consideration AND purchase cost exactly as shown in AIS
                lab = [x["field"] for x in l1["columnLabel"]]
                ix = {k: _find(lab, k) for k in ("transferDate", "securityName", "securityClass", "assetType", "quantity",
                                                 "salesConsideration", "costOfAcquisition", "fmvValue", "status", "transFeedback")}
                for rn, r in enumerate(l1["columnData"]):
                    rid += 1
                    st = _cell(r, ix["status"])
                    sale = parse_amt(_cell(r, ix["salesConsideration"])) or D(0)
                    cost = parse_amt(_cell(r, ix["costOfAcquisition"]))
                    dt = parse_date(_cell(r, ix["transferDate"]))
                    cls_, asset = _cell(r, ix["securityClass"]), _cell(r, ix["assetType"])
                    ais["records"].append(dict(
                        base, id=rid, ref="%s, element %d, row %d" % (part, ei + 1, rn + 1), count=1, amount=sale,
                        deducted=D(0), status_text=_status_text(st, _cell(r, ix["transFeedback"])),
                        active=(str(st or "Active").lower() != "inactive"), date=_cell(r, ix["transferDate"]),
                        derived=None if cost is None else sale - cost, rowcg=True, cost=cost,
                        sec_name=_cell(r, ix["securityName"]), sec_class=cls_, asset_type=asset,
                        qty=parse_amt(_cell(r, ix["quantity"])), fmv=parse_amt(_cell(r, ix["fmvValue"])),
                        cg_sec=cg_section(cls_, asset), bucket="pre" if (dt and dt < CG_SPLIT_DATE) else "post", dup=False))
                continue
            if head == "cg":                     # no transaction rows: one record per element, AIS-derived gain
                rid += 1
                txt = " ".join(str(x) for x in (l2.get("Qualifies For"), code, desc, category)).upper()
                sec_t = "111A" if "111A" in txt else "112A" if "112A" in txt else None
                if sec_t is None:
                    sec_t = "112" if "LONG" in txt else "STG" if "SHORT" in txt else None
                dates = []
                if l1:
                    lab = [x["field"] for x in l1.get("columnLabel", [])]
                    di = _find(lab, "dateOfSale", "transactionDate", "saleDate", "reportedOn")
                    dates = [parse_date(_cell(r, di)) for r in l1.get("columnData", [])]
                    dates = [d for d in dates if d]
                rec = dict(base, id=rid, ref="%s, element %d" % (part, ei + 1), count=int(parse_amt(l2.get("Count")) or 1),
                           amount=parse_amt(l2.get("Amount")) or D(0), deducted=D(0), status_text="Active",
                           active=True, date=None, derived=parse_amt(l2.get("Derived Amount")), cg_sec=sec_t,
                           bucket="post" if (not dates or max(dates) >= CG_SPLIT_DATE) else "pre", dup=False)
                ais["records"].append(rec)
                continue
            if l1 and l1.get("columnData"):
                lab = [x["field"] for x in l1.get("columnLabel", [])]
                i_amt = _find(lab, "amtPaid", "marketPurchase")
                i_ded = _find(lab, "amountDeducted", "amountCollected", "taxCollected")
                i_st, i_fb = _find(lab, "status"), _find(lab, "transFeedback")
                i_dt = _find(lab, "transactionDate", "reportedOn")
                for rn, r in enumerate(l1["columnData"]):
                    rid += 1
                    st = _cell(r, i_st)
                    ais["records"].append(dict(
                        base, id=rid, ref="%s, element %d, row %d" % (part, ei + 1, rn + 1), count=1,
                        amount=parse_amt(_cell(r, i_amt)) or D(0), deducted=parse_amt(_cell(r, i_ded)) or D(0),
                        status_text=_status_text(st, _cell(r, i_fb)), active=(str(st or "Active").lower() != "inactive"),
                        date=_cell(r, i_dt), derived=None, cg_sec=None, bucket=None, dup=False))
            else:                                # summary-only element
                rid += 1
                ais["records"].append(dict(
                    base, id=rid, ref="%s, element %d (summary)" % (part, ei + 1),
                    count=int(parse_amt(l2.get("Count")) or 1), amount=parse_amt(l2.get("Amount")) or D(0),
                    deducted=D(0), status_text=str(l2.get("Qualifies For") or ""), active=True, date=None,
                    derived=None, cg_sec=None, bucket=None, dup=False))
    # reconcile every AIS summary line (the system-processed value) with the active rows that make it up
    byel = {}
    for r in ais["records"]:
        byel.setdefault(r["elem"], []).append(r)
    for rows in byel.values():
        l2a, act = rows[0]["l2_amount"], sum((x["amount"] for x in rows if x["active"]), D(0))
        # only income lines matter; information-only reports (deposits, purchases ...) are not part of the tax
        if l2a is not None and abs(act - l2a) > 1 and rows[0]["head"] in INCOME_HEADS:
            ais["warnings"].append("Reconcile: the AIS summary for %s (%s) shows %s but its active rows add up to %s." %
                                   (rows[0]["code"], rows[0]["category"], money(l2a), money(act)))
    _flag_duplicates(ais["records"])
    return ais


# ---- flat CSV / XLSX layout (one row per AIS line) ------------------------------------------


def default_catcode(code, category=""):
    """AIS 'Information Category Code' when the file does not carry it: the same income reported through
    TDS and through SFT shares one code, so it is counted once (system-processed value)."""
    c = norm_code(code)
    s = c[4:] if c.startswith("TDS-") else ""
    if s == "194A" or c.startswith("SFT-016(TD)") or c.startswith("SFT-016(RD)"):
        return "IND"
    if c.startswith("SFT-016(SB)"):
        return "INS"
    if c.startswith("SFT-015") or s in ("194", "194K"):
        return "DIV"
    return str(category or code).upper()[:30]


def cg_section(sec_class, asset_type):
    """Capital-gain section from the AIS security class and holding type (VERIFY for debt funds / unlisted shares)."""
    c, a = str(sec_class or "").upper(), str(asset_type or "").upper()
    lt, st = "LONG" in a, "SHORT" in a
    equity = (("EQUITY" in c and "UNLISTED" not in c and ("LISTED" in c or "MUTUAL" in c or "ORIENTED" in c or "ETF" in c))
              or "BUSINESS TRUST" in c or "REIT" in c or "INVIT" in c)
    if equity:
        return "112A" if lt else ("111A" if st else None)
    return "112" if lt else ("STG" if st else None)












def _flag_duplicates(records):
    """Probable duplicates: same code+source+date+amount repeated, or SFT interest/dividend that repeats a TDS amount."""
    seen = {}
    for r in records:
        if r["head"] in ("cg",) or r["amount"] == 0:
            continue
        seen.setdefault((r["code"], r["l1src"], r["date"], r["amount"]), []).append(r)
    for lst in seen.values():
        if len(lst) > 1:
            for r in lst:
                r["dup"] = True
    # (the same income reported by both TDS and SFT is handled in dedup_sources: counted once)


# =====================================================================================
# 5. GROUPS (what the user reviews)  -- one group = category/code/source/status
# =====================================================================================
def flag_text(r):
    t = r["status_text"]
    if r["dup"]:
        t = (t + " / " if t else "") + "possible duplicate row"
    return t


def build_groups(ais, include_inactive=False):
    groups = {}
    for r in ais["records"]:
        key = (r["category"], r["code"], r["l1src"], flag_text(r), r["head"] == "cg", r["cg_sec"], r["bucket"])
        g = groups.get(key)
        if g is None:
            g = {"key": key, "category": r["category"], "code": r["code"], "source": r["l1src"],
                 "flags": flag_text(r), "head": r["head"], "orig_head": r["head"], "count": 0,
                 "amount": D(0), "deducted": D(0), "derived": D(0), "derived_missing": False,
                 "cg_sec": r["cg_sec"], "bucket": r["bucket"], "override": None, "rec_ids": [], "dup": r["dup"],
                 "active": r["active"], "include": False, "credit": False,
                 "catcode": r.get("catcode"), "dedup": ""}
            groups[key] = g
        g["count"] += r["count"]
        g["amount"] += r["amount"]
        g["deducted"] += r["deducted"]
        g["rec_ids"].append(r["id"])
        if r["head"] == "cg":
            if r["derived"] is None:
                g["derived_missing"] = True
            else:
                g["derived"] += r["derived"]
    out = sorted(groups.values(), key=lambda g: (g["category"], g["code"], g["flags"]))
    refresh_defaults(out, include_inactive)
    return out


def apply_default_flags(g, include_inactive):
    ok = g["active"] or include_inactive
    g["include"] = bool(ok and g["head"] in INCOME_HEADS)
    g["credit"] = bool(ok and g["deducted"] > 0)


def dedup_sources(groups):
    """System-processed value: the same income reported through TDS *and* through SFT (same AIS Information
    Category Code, e.g. IND = interest from deposit) is one income. The higher family total is taken once
    (a tie keeps TDS, which also carries the tax credit); the other family is shown but not added."""
    fams = {}
    for g in groups:
        g["dedup"], g["dedup_info"] = "", None
        if g["head"] in INCOME_HEADS and g["head"] != "cg" and g["catcode"] and g["active"] and g["include"]:
            fam = "TDS" if norm_code(g["code"]).startswith("TDS") else "SFT"
            fams.setdefault(g["catcode"], {}).setdefault(fam, []).append(g)
    for cat, f in fams.items():
        if len(f) < 2:
            continue
        tot = {k: sum((x["amount"] for x in v), D(0)) for k, v in f.items()}
        keep = max(tot, key=lambda k: (tot[k], k == "TDS"))
        for k, v in f.items():
            if k != keep:
                for g in v:
                    g["include"] = False
                    g["dedup_info"] = (keep, tot[keep])
                    g["dedup"] = ("Not added to income: %s (%s) is the same income already reported through %s "
                                  "(%s) - the system-processed value is counted once." %
                                  (g["code"], money(g["amount"]), keep, money(tot[keep])))


def refresh_defaults(groups, include_inactive):
    for g in groups:
        apply_default_flags(g, include_inactive)
    dedup_sources(groups)


# =====================================================================================
# 6. TAX ENGINE
# =====================================================================================
def slab_tax(slabs, income):
    income, prev, total, rows = D(income), D(0), D(0), []
    for upper, rate in slabs:
        if income <= prev:
            break
        top = D(upper) if upper is not None else None
        seg_top = income if top is None else min(income, top)
        taxable = seg_top - prev
        tax = taxable * D(str(rate)) / 100
        rows.append({"frm": prev, "to": top, "taxable": taxable, "rate": D(str(rate)), "tax": tax})
        total += tax
        if top is None:
            break
        prev = top
    return total, rows


def surcharge_rate(income, cap=37):
    r = 0
    for th, rt in SURCHARGE_STEPS:
        if D(income) > th:
            r = rt
    return min(r, cap)


def setoff_capital_gains(items, bf_stcl=0, bf_ltcl=0):
    """items: [{sec, bucket, gain, rate}] -> (positive items after set-off, unabsorbed STCL, unabsorbed LTCL).
    Current-year STCL vs ST then LT gains; LTCL vs LT gains only; then brought-forward losses (VERIFY order)."""
    items = [dict(i, gain=D(i["gain"])) for i in items]
    st = [i for i in items if i["sec"] in ("111A", "STG")]
    lt = [i for i in items if i["sec"] in ("112A", "112")]

    def pool(lst, positive_only=True):
        return sorted([i for i in lst if i["gain"] > 0], key=lambda x: -x["rate"])

    def absorb(lst, amount):
        amount = D(amount)
        for i in pool(lst):
            if amount <= 0:
                break
            use = min(i["gain"], amount)
            i["gain"] -= use
            amount -= use
        return amount

    st_loss = -sum((i["gain"] for i in st if i["gain"] < 0), D(0))
    lt_loss = -sum((i["gain"] for i in lt if i["gain"] < 0), D(0))
    for i in items:
        if i["gain"] < 0:
            i["gain"] = D(0)
    st_loss = absorb(st, st_loss)
    lt_loss = absorb(lt, lt_loss)
    st_loss = absorb(lt, st_loss)
    st_left = absorb(st, D(bf_stcl))
    st_left = absorb(lt, st_left)
    lt_left = absorb(lt, D(bf_ltcl))
    return [i for i in items if i["gain"] > 0], st_loss + st_left, lt_loss + lt_left


def compute_regime(rules, regime, p):
    """p: inc{head:Decimal}, cg_items[], resident(bool), age('gen'|'sr'|'ssr'), ded(Decimal)."""
    R = rules[regime]
    slabs = R["slabs"]["sr" if False else (p["age"] if (regime == "old" and p["resident"]) else "gen")] \
        if isinstance(R["slabs"], dict) else R["slabs"]
    inc = {k: D(v) for k, v in p["inc"].items()}
    cgm = rules["cg_mode"]
    rate_tab = {"pre": _CG_OLD, "post": _CG_NEW}
    items = []
    for it in p["cg_items"]:
        b = it.get("bucket") or "post"
        if cgm == "old":
            b = "pre"
        elif cgm == "new":
            b = "post"
        if it.get("rate") is not None:
            rate = D(str(it["rate"]))                      # explicit rate (e.g. property with indexation = 20%)
        else:
            rate = D(str(rate_tab[b].get(it["sec"], 0))) if it["sec"] != "STG" else D(30)
        items.append({"sec": it["sec"], "bucket": b, "gain": D(it["gain"]), "rate": rate})
    cg_total_derived = sum((i["gain"] for i in items), D(0))
    items, st_unabs, lt_unabs = setoff_capital_gains(items, p.get("bf_stcl", 0), p.get("bf_ltcl", 0))
    stg_slab = sum((i["gain"] for i in items if i["sec"] == "STG"), D(0))
    # ordinary income ---------------------------------------------------------------
    salary = inc.get("salary", D(0))
    hp = inc.get("hp", D(0))
    if regime == "old":     # s.71B: house-property loss set off against other heads up to Rs 2,00,000 (old regime only)
        hp = max(hp - min(D(p.get("so_interest", 0)), D(200000)), D(-200000))
    else:                   # new regime: no set-off of house-property loss
        hp = max(hp, D(0))
    gross_ord = salary + hp + inc.get("business", D(0)) + inc.get("other", D(0)) + stg_slab
    std = min(salary, D(R["std"]))
    ded = D(p.get("ded_old" if regime == "old" else "ded_new", 0))
    ord_taxable = max(D(0), gross_ord - std - ded)
    exemption = D(slabs[0][0]) if slabs and slabs[0][1] == 0 else D(0)
    shortfall = max(D(0), exemption - ord_taxable) if p["resident"] else D(0)
    # special-rate income -------------------------------------------------------------
    thr_left = D(rules["cg_exempt"])
    order = sorted([i for i in items if i["sec"] != "STG"],
                   key=lambda i: ({"111A": 0, "112A": 1, "112": 2}[i["sec"]], -i["rate"]))
    for i in order:                                  # 112A threshold first (higher rate first)
        i["thr"] = D(0)
    for i in sorted([x for x in order if x["sec"] == "112A"], key=lambda x: -x["rate"]):
        use = min(i["gain"], thr_left)
        i["thr"] = use
        thr_left -= use
    for i in order:
        i["exm"] = min(i["gain"] - i["thr"], shortfall)
        shortfall -= i["exm"]
        i["taxable"] = i["gain"] - i["thr"] - i["exm"]
        i["tax"] = i["taxable"] * i["rate"] / 100
    both = len({i["bucket"] for i in order}) > 1
    sp_rows = []
    for sec in ("111A", "112A", "112"):
        for b in ("pre", "post"):
            sel = [i for i in order if i["sec"] == sec and i["bucket"] == b]
            if not sel:
                continue
            lab = "Section " + sec + ((" (before 23-Jul-2024)" if b == "pre" else " (on/after 23-Jul-2024)") if both or cgm == "split" else "")
            sp_rows.append({"sec": sec, "bucket": b, "label": lab, "gain": sum((i["gain"] for i in sel), D(0)),
                            "exm": sum((i["exm"] for i in sel), D(0)), "thr": sum((i["thr"] for i in sel), D(0)),
                            "taxable": sum((i["taxable"] for i in sel), D(0)), "tax": sum((i["tax"] for i in sel), D(0))})
    win = inc.get("winnings", D(0))
    if win > 0:
        sp_rows.append({"sec": "115BB", "bucket": "post", "label": "Section 115BB (winnings)", "gain": win, "exm": D(0),
                        "thr": D(0), "taxable": win, "tax": win * 30 / 100})
    special_tax = sum((r["tax"] for r in sp_rows), D(0))
    special_taxable = sum((r["taxable"] for r in sp_rows), D(0))
    # slab tax --------------------------------------------------------------------------
    slab_total, slab_rows = slab_tax(slabs, ord_taxable)
    total_income = ord_taxable + special_taxable
    # rebate 87A ---------------------------------------------------------------------------
    rebate = D(0)
    if p["resident"] and R["rebate_limit"] and total_income <= R["rebate_limit"]:
        base = slab_total + (special_tax if R["rebate_special"] else D(0))
        rebate = min(D(R["rebate_max"]), base)
    elif p["resident"] and R["marginal_relief"] and R["rebate_limit"]:
        base = slab_total + (special_tax if R["rebate_special"] else D(0))
        cap = total_income - D(R["rebate_limit"])
        if base > cap:
            rebate = min(base - cap, slab_total + (special_tax if R["rebate_special"] else D(0)))
            rebate = min(rebate, D(R["rebate_max"]) if False else rebate)
    rebate = min(rebate, slab_total + special_tax)
    after_rebate = slab_total + special_tax - rebate
    # surcharge with marginal relief ----------------------------------------------------------
    cap = R["sur_cap"]
    rate = surcharge_rate(total_income, cap)
    surcharge = D(0)
    if rate:
        normal_after = max(D(0), slab_total - rebate)
        surcharge = normal_after * rate / 100 + special_tax * min(rate, 15) / 100
        thr = max(t for t, _ in SURCHARGE_STEPS if total_income > t)
        prev_rate = surcharge_rate(thr, cap)
        norm_at_thr = max(D(0), D(thr) - special_taxable)
        tax_thr = slab_tax(slabs, norm_at_thr)[0] + special_tax
        tax_thr_total = tax_thr + tax_thr * prev_rate / 100
        allowed = tax_thr_total + (total_income - D(thr))
        if after_rebate + surcharge > allowed:
            surcharge = max(D(0), allowed - after_rebate)
    cess = (after_rebate + surcharge) * CESS_PCT / 100
    gross_tax = r10(after_rebate + surcharge + cess)
    return {"regime": regime, "gross_ord": gross_ord, "std": std, "ded": ded, "ord_taxable": ord_taxable,
            "salary": salary, "hp": hp, "business": inc.get("business", D(0)), "other": inc.get("other", D(0)),
            "slab_tax": slab_total, "slab_rows": slab_rows, "special_tax": special_tax, "special_rows": sp_rows,
            "rebate": rebate, "surcharge": surcharge, "cess": cess, "gross_tax": gross_tax,
            "total_income": total_income, "cg_total_derived": cg_total_derived, "stg_slab": stg_slab,
            "unabsorbed_stcl": st_unabs, "unabsorbed_ltcl": lt_unabs, "shortfall_left": shortfall}


def age_group(dob_text, fy):
    d = parse_date(dob_text)
    if not d:
        return "gen"
    end = _dt.date(int(fy[:4]) + 1, 3, 31)
    age = end.year - d.year - ((end.month, end.day) < (d.month, d.day))
    return "ssr" if age >= 80 else "sr" if age >= 60 else "gen"


AGE_LABEL = {"gen": "Below 60", "sr": "Senior (60-79)", "ssr": "Super senior (80+)"}


# Cost Inflation Index by financial year (VERIFY against the CBDT notifications)
CII = {"2001-02": 100, "2002-03": 105, "2003-04": 109, "2004-05": 113, "2005-06": 117, "2006-07": 122,
       "2007-08": 129, "2008-09": 137, "2009-10": 148, "2010-11": 167, "2011-12": 184, "2012-13": 200,
       "2013-14": 220, "2014-15": 240, "2015-16": 254, "2016-17": 264, "2017-18": 272, "2018-19": 280,
       "2019-20": 289, "2020-21": 301, "2021-22": 317, "2022-23": 331, "2023-24": 348, "2024-25": 363,
       "2025-26": 376}
BIZ_SCHEMES = ["AIS as reported", "44AD", "44ADA", "44AE", "Books (receipts - expenses)"]
MANUAL_DEFAULTS = {"hp_rent": 0, "hp_muni": 0, "hp_int": 0, "hp_so_int": 0,
                   "biz_scheme": "AIS as reported", "biz_receipts": 0, "biz_digital": 0, "biz_exp": 0,
                   "ae_light": 0, "ae_heavy": 0,
                   "prop_on": False, "prop_sale": 0, "prop_cost": 0, "prop_improve": 0, "prop_exp": 0,
                   "prop_cost_fy": "2015-16", "prop_long": True, "prop_before_jul24": True,
                   "prop_pre_sale": False, "prop_exempt": 0}


def default_profile(ais):
    p = {"resident": "Resident", "age_choice": "Auto", "ded_old": 0, "ded_new": 0, "bf_stcl": 0, "bf_ltcl": 0,
         "include_inactive": False, "regime_choice": "Auto", "filing_note": ""}
    p.update(MANUAL_DEFAULTS)
    p["cg_cost"] = {}          # user-entered purchase cost per capital-gain record id
    return p


def rec_gain(r, prof):
    """(gain, cost_not_shown) for one capital-gain record: sale consideration less the purchase cost shown in AIS;
    a user-entered cost overrides it. Cost 0 / blank is flagged, never invented."""
    ov = (prof.get("cg_cost") or {}).get(str(r["id"]))
    if r.get("rowcg"):
        cost = D(ov) if ov is not None else r["cost"]
        if cost is None:
            return None, False
        return r["amount"] - cost, cost == 0
    return r["derived"], False


def property_item(rules, prof, resident=True):
    """User-entered sale of land/building -> (capital-gain item, info) or (None, None).
    Long term: 20% with indexation vs 12.5% without (resident, acquired before 23-Jul-2024: lower tax chosen)."""
    sale = D(prof["prop_sale"])
    if not prof["prop_on"] or sale <= 0:
        return None, None
    cost = D(prof["prop_cost"]) + D(prof["prop_improve"])
    net_sale = sale - D(prof["prop_exp"])
    info = {"sale": sale, "cost": cost, "label": "Long term / property (user input)", "option": "", "note": ""}
    if not prof["prop_long"]:
        info.update(label="Short term / property (user input)", gain=net_sale - cost, note="Held up to 24 months: taxed at slab rates.")
        return {"sec": "STG", "bucket": "post", "gain": net_sale - cost}, info
    exempt = min(D(prof["prop_exempt"]), D(100000000))          # s.54/54F cap Rs 10 crore (VERIFY)
    cm = rules["cg_mode"]
    bucket = "pre" if cm == "old" else "post" if cm == "new" else ("pre" if prof["prop_pre_sale"] else "post")
    cii_s, cii_a = CII.get(rules["fy"]), CII.get(prof["prop_cost_fy"])
    idx_gain = None
    if cii_s and cii_a:
        idx_gain = net_sale - cost * D(cii_s) / D(cii_a) - exempt
    plain_gain = net_sale - cost - exempt
    if bucket == "pre":
        if idx_gain is None:
            idx_gain, info["note"] = plain_gain, "CII unavailable: indexation not applied (VERIFY)."
        item = {"sec": "112", "bucket": "pre", "gain": idx_gain, "rate": 20}
        info.update(option="20% with indexation (transfer before 23-Jul-2024)", gain=idx_gain)
    elif idx_gain is not None and prof["prop_before_jul24"] and resident:
        tax_a, tax_b = max(D(0), idx_gain) * 20 / 100, max(D(0), plain_gain) * D("12.5") / 100
        if tax_a < tax_b:
            item = {"sec": "112", "bucket": "post", "gain": idx_gain, "rate": 20}
            info.update(option="20%% with indexation (lower tax than 12.5%% without: %s vs %s)" % (money(tax_a), money(tax_b)), gain=idx_gain)
        else:
            item = {"sec": "112", "bucket": "post", "gain": plain_gain, "rate": D("12.5")}
            info.update(option="12.5%% without indexation (lower or equal tax than 20%% with indexation: %s vs %s)" % (money(tax_b), money(tax_a)), gain=plain_gain)
    else:
        item = {"sec": "112", "bucket": "post", "gain": plain_gain, "rate": D("12.5")}
        info.update(option="12.5% without indexation", gain=plain_gain)
    return item, info


def apply_manual(inc, prof, rules, cg_items):
    """Apply user inputs for house property, presumptive/books business and property sale.
    Mutates inc and cg_items.  Returns (notes, warnings, property_info)."""
    notes, warns = [], []
    if any(prof[k] for k in ("hp_rent", "hp_muni", "hp_int")):
        rent = D(prof["hp_rent"]) or inc["hp"]
        nav = max(D(0), rent - D(prof["hp_muni"]))
        inc["hp"] = nav - nav * 30 / 100 - D(prof["hp_int"])
        notes.append("User input: house property income %s = rent %s less municipal tax %s, less 30%% standard "
                     "deduction (s.24(a)) and interest %s (s.24(b))." %
                     (money(inc["hp"]), money(rent), money(prof["hp_muni"]), money(prof["hp_int"])))
    if prof["hp_so_int"]:
        notes.append("User input: self-occupied property interest %s (limit Rs 2,00,000; old regime only)." % money(prof["hp_so_int"]))
    scheme = prof["biz_scheme"]
    receipts = D(prof["biz_receipts"]) or inc["business"]
    if scheme == "44AD":
        dig = min(D(prof["biz_digital"]), receipts)
        inc["business"] = dig * 6 / 100 + (receipts - dig) * 8 / 100
        notes.append("User input: business income %s under s.44AD (6%% on digital receipts %s, 8%% on the rest of %s)." %
                     (money(inc["business"]), money(dig), money(receipts)))
        if receipts > 20000000:
            warns.append("Receipts %s exceed the s.44AD limit (Rs 2 crore; Rs 3 crore if cash receipts are within 5%%) - VERIFY eligibility." % money(receipts))
    elif scheme == "44ADA":
        inc["business"] = receipts * 50 / 100
        notes.append("User input: professional income %s under s.44ADA (50%% of receipts %s)." % (money(inc["business"]), money(receipts)))
        if receipts > 5000000:
            warns.append("Receipts %s exceed the s.44ADA limit (Rs 50 lakh; Rs 75 lakh if cash receipts are within 5%%) - VERIFY eligibility." % money(receipts))
    elif scheme == "44AE":
        inc["business"] = D(prof["ae_light"]) * 7500 + D(prof["ae_heavy"]) * 1000
        notes.append("User input: transport income %s under s.44AE (Rs 7,500 per light vehicle-month; Rs 1,000 per tonne-month for heavy vehicles) - VERIFY rates." % money(inc["business"]))
    elif scheme.startswith("Books"):
        inc["business"] = receipts - D(prof["biz_exp"])
        notes.append("User input: books-based business income %s = receipts %s less expenses %s." %
                     (money(inc["business"]), money(receipts), money(prof["biz_exp"])))
    if scheme != "AIS as reported":
        notes.append("Business receipts taken as %s; the user must confirm they are business receipts, not AIS reporting overlaps." % money(receipts))
    if receipts > 10000000 and scheme in ("AIS as reported", "Books (receipts - expenses)"):
        warns.append("Gross receipts %s exceed Rs 1 crore: tax audit under s.44AB may apply (Rs 3 crore if cash transactions are within 5%%) - VERIFY." % money(receipts))
    item, prop = property_item(rules, prof, prof.get("resident", "Resident") == "Resident")
    if item:
        cg_items.append(item)
        notes.append("User input: property sale - consideration %s, cost %s: %s; gain %s." %
                     (money(prop["sale"]), money(prop["cost"]), prop["option"] or prop["note"], money(prop["gain"])))
        if prof["prop_exempt"]:
            notes.append("User input: s.54/54F exemption of %s was deducted; check the conditions and time limits." % money(prof["prop_exempt"]))
    return notes, warns, prop


def compute_case(case):
    ais, groups, prof = case["ais"], case["groups"], case["profile"]
    rules = get_rules(ais["fy"])
    inc = {h: D(0) for h in INCOME_HEADS}
    cnt = {h: 0 for h in INCOME_HEADS}
    cg_items, cg_rows, cg_missing = [], [], 0
    recs = {r["id"]: r for r in ais["records"]}
    ovs = prof.get("cg_cost") or {}
    cg_tx, cg_zero_rows, cg_zero_sale, fmv_rows = [], 0, D(0), 0
    for g in groups:
        if g["head"] == "cg" and g["include"]:
            gains = []
            for rid_ in g["rec_ids"]:
                rr = recs[rid_]
                gv, zero = rec_gain(rr, prof)
                gains.append(gv)
                if rr.get("rowcg"):
                    user = str(rr["id"]) in ovs
                    cg_tx.append({"id": rr["id"], "date": rr["date"], "name": rr.get("sec_name"), "cls": rr.get("sec_class"),
                                  "asset": rr.get("asset_type"), "sec": g["cg_sec"], "qty": rr.get("qty"), "sale": rr["amount"],
                                  "cost": D(ovs[str(rr["id"])]) if user else rr["cost"], "gain": gv, "zero": zero, "user": user})
                    if zero:
                        cg_zero_rows += 1
                        cg_zero_sale += rr["amount"]
                    if rr.get("fmv"):
                        fmv_rows += 1
            gain = D(g["override"]) if g["override"] is not None else (None if any(x is None for x in gains) else sum(gains, D(0)))
            g["gain_used"] = gain
            cg_rows.append(g)
            if gain is None or g["cg_sec"] is None:
                cg_missing += g["count"]
                continue
            cg_items.append({"sec": g["cg_sec"], "bucket": g["bucket"], "gain": gain})
        elif g["include"] and g["head"] in INCOME_HEADS and g["head"] != "cg":
            inc[g["head"]] += g["amount"]
            cnt[g["head"]] += g["count"]
    cg_cnt = sum(g["count"] for g in cg_rows)
    notes, warns, prop = apply_manual(inc, dict(prof), rules, cg_items)
    resident = prof["resident"] == "Resident"
    age = age_group(ais["dob"], ais["fy"]) if prof["age_choice"] == "Auto" else \
        {"Below 60": "gen", "Senior (60-79)": "sr", "Super senior (80+)": "ssr"}[prof["age_choice"]]
    p = {"inc": inc, "cg_items": cg_items, "resident": resident, "age": age, "ded_old": prof["ded_old"],
         "ded_new": prof["ded_new"], "bf_stcl": prof["bf_stcl"], "bf_ltcl": prof["bf_ltcl"],
         "so_interest": prof["hp_so_int"]}
    old, new = compute_regime(rules, "old", p), compute_regime(rules, "new", p)
    # taxes paid ----------------------------------------------------------------------------
    paid_rows, zero_rows = [], 0
    tmap = {}
    for g in groups:
        if g["code"] and (norm_code(g["code"]).startswith("TDS") or norm_code(g["code"]).startswith("TCS")):
            if not g["credit"]:
                if g["deducted"] == 0 and (g["active"] or prof["include_inactive"]):
                    zero_rows += g["count"]
                continue
            typ = "TCS" if norm_code(g["code"]).startswith("TCS") else "TDS"
            tmap[(typ, g["code"], g["source"], g["flags"])] = (g["count"], g["deducted"])
    zero_rows += sum(g["count"] for g in groups if g["code"] and norm_code(g["code"]).startswith(("TDS", "TCS"))
                     and g["credit"] and g["deducted"] == 0)
    chal = {}
    for c in ais["challans"]:
        m = c["minor"].lower()
        typ = "Advance tax" if "advance" in m else "Self-assessment tax" if "self" in m else \
            "Regular assessment tax" if "regular" in m else "Tax paid (" + c["minor"] + ")"
        n, a = chal.get(typ, (0, D(0)))
        chal[typ] = (n + 1, a + c["total"])
    for typ in ("Advance tax", "Self-assessment tax", "Regular assessment tax"):
        if typ in chal and chal[typ][1] != 0:
            paid_rows.append([typ, "-", "-", "-", chal[typ][0], chal[typ][1]])
    for typ, (n, a) in chal.items():
        if typ not in ("Advance tax", "Self-assessment tax", "Regular assessment tax") and a != 0:
            paid_rows.append([typ, "-", "-", "-", n, a])
    for (typ, code, src, flags), (n, a) in sorted(tmap.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][3])):
        if a != 0:
            paid_rows.append([typ, code, src, flags or "-", n, a])
        else:
            zero_rows += n
    paid_total = sum((r[5] for r in paid_rows), D(0))
    better = "new" if new["gross_tax"] <= old["gross_tax"] else "old"
    chosen = better if prof["regime_choice"] == "Auto" else prof["regime_choice"].lower()
    res = {"old": old, "new": new, "better": better, "chosen": chosen, "paid_total": paid_total,
           "paid_rows": paid_rows, "zero_credit_rows": zero_rows, "inc": inc, "cnt": cnt, "cg_cnt": cg_cnt,
           "cg_missing_rows": cg_missing, "age": age, "rules": rules, "cg_groups": cg_rows,
           "manual_notes": notes, "warnings": warns, "property": prop, "cg_tx": cg_tx, "cg_cost_zero_rows": cg_zero_rows,
           "cg_cost_zero_sale": cg_zero_sale, "cg_fmv_rows": fmv_rows, "recon_notes": list(ais["warnings"])}
    for rg in ("old", "new"):
        r = res[rg]
        diff = paid_total - D(r["gross_tax"])
        r["paid"] = paid_total
        r["net_payable"] = r10(-diff) if diff < 0 else 0
        r["refund"] = r10(diff) if diff > 0 else 0
    c = res[chosen]
    res["kpi_income"] = r10(c["total_income"])      # total income after exemptions/deductions, rounded to Rs 10 (s.288A)
    res["tax_diff"] = abs(old["gross_tax"] - new["gross_tax"])
    return res


# =====================================================================================
# 7. WORD REPORT  (python-docx, all styling through the constants + helpers below)
# =====================================================================================
def _rgb(hexs):
    return RGBColor.from_string(hexs)


def _set_rfonts(el_rpr, name):
    rf = el_rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        el_rpr.insert(0, rf)
    for a in list(rf.attrib):
        del rf.attrib[a]
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), name)


_RPR_AFTER_SPACING = ("w:w", "w:kern", "w:position", "w:sz", "w:szCs", "w:highlight", "w:u", "w:effect", "w:bdr",
                      "w:shd", "w:fitText", "w:vertAlign", "w:rtl", "w:cs", "w:em", "w:lang", "w:eastAsianLayout",
                      "w:specVanish", "w:oMath")


def style_run(run, size=None, bold=None, italic=None, color=None, font=None, spacing=None, caps=None):
    f = run.font
    if size is not None:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    if color:
        f.color.rgb = _rgb(color)
    if caps:
        f.all_caps = True
    rpr = run._element.get_or_add_rPr()
    _set_rfonts(rpr, font or FONT_BODY)
    if spacing:
        sp = OxmlElement("w:spacing")
        sp.set(qn("w:val"), str(int(spacing)))
        rpr.insert_element_before(sp, *_RPR_AFTER_SPACING)
    return run


def style_font(style, name, size=None, bold=None, color=None, italic=None):
    rpr = style.element.get_or_add_rPr()
    _set_rfonts(rpr, name)
    if size is not None:
        style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    if color:
        style.font.color.rgb = _rgb(color)


_PPR_AFTER_BDR = ("w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap", "w:overflowPunct",
                  "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd", "w:snapToGrid",
                  "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
                  "w:textDirection", "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl", "w:divId",
                  "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange")


def bottom_border(ppr_owner_pPr, color=NAVY, sz=6, space=1):
    bd = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", str(sz)), ("w:space", str(space)), ("w:color", color)):
        b.set(qn(k), v)
    bd.append(b)
    ppr_owner_pPr.insert_element_before(bd, *_PPR_AFTER_BDR)


_TCPR_AFTER = {"borders": ("w:shd", "w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark"),
               "shd": ("w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark"),
               "mar": ("w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark")}


def shade(cell, fill):
    tcpr = cell._tc.get_or_add_tcPr()
    for old in tcpr.findall(qn("w:shd")):
        tcpr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcpr.insert_element_before(shd, *_TCPR_AFTER["shd"])


def cell_borders(cell, **edges):
    """edges: top/left/bottom/right = (size_eighths_pt, colour) or None for no border."""
    tcpr = cell._tc.get_or_add_tcPr()
    for old in tcpr.findall(qn("w:tcBorders")):
        tcpr.remove(old)
    tb = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        e = OxmlElement("w:" + edge)
        spec = edges.get(edge)
        if spec:
            e.set(qn("w:val"), "single")
            e.set(qn("w:sz"), str(spec[0]))
            e.set(qn("w:color"), spec[1])
        else:
            e.set(qn("w:val"), "nil")
        e.set(qn("w:space"), "0")
        tb.append(e)
    tcpr.insert_element_before(tb, *_TCPR_AFTER["borders"])


def cell_margins(cell, top=0, bottom=0, left=0, right=0):
    tcpr = cell._tc.get_or_add_tcPr()
    for old in tcpr.findall(qn("w:tcMar")):
        tcpr.remove(old)
    mar = OxmlElement("w:tcMar")
    for k, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        e = OxmlElement("w:" + k)
        e.set(qn("w:w"), str(int(v * 20)))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tcpr.insert_element_before(mar, *_TCPR_AFTER["mar"])


def set_cell_width(cell, cm):
    cell.width = Cm(cm)


def repeat_header(row):
    trpr = row._tr.get_or_add_trPr()
    e = OxmlElement("w:tblHeader")
    trpr.append(e)


def cant_split(row):
    trpr = row._tr.get_or_add_trPr()
    trpr.insert(0, OxmlElement("w:cantSplit"))


_TBLPR_AFTER_BORDERS = ("w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook", "w:tblCaption", "w:tblDescription")
_TBLPR_AFTER_MAR = ("w:tblLook", "w:tblCaption", "w:tblDescription")
_TBLPR_AFTER_IND = ("w:tblBorders", "w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook", "w:tblCaption")


def table_setup(table, widths_cm, border=(4, BORDER), pad=(4.5, 6), indent=True):
    """Fixed layout, full width, grid + cell widths, borders and padding at table level."""
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tblpr = table._tbl.tblPr
    total = sum(widths_cm)
    w = tblpr.find(qn("w:tblW"))
    if w is None:
        w = OxmlElement("w:tblW")
        tblpr.append(w)
    w.set(qn("w:type"), "dxa")
    w.set(qn("w:w"), str(int(total / 2.54 * 1440)))
    if indent:
        ind = OxmlElement("w:tblInd")
        ind.set(qn("w:w"), str(int(pad[1] * 20)))
        ind.set(qn("w:type"), "dxa")
        tblpr.insert_element_before(ind, *_TBLPR_AFTER_IND)
    tb = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement("w:" + edge)
        if border:
            e.set(qn("w:val"), "single")
            e.set(qn("w:sz"), str(border[0]))
            e.set(qn("w:color"), border[1])
        else:
            e.set(qn("w:val"), "nil")
        e.set(qn("w:space"), "0")
        tb.append(e)
    tblpr.insert_element_before(tb, *_TBLPR_AFTER_BORDERS)
    mar = OxmlElement("w:tblCellMar")
    for k, v in (("top", pad[0]), ("left", pad[1]), ("bottom", pad[0]), ("right", pad[1])):
        e = OxmlElement("w:" + k)
        e.set(qn("w:w"), str(int(v * 20)))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tblpr.insert_element_before(mar, *_TBLPR_AFTER_MAR)
    for i, cm in enumerate(widths_cm):
        table.columns[i].width = Cm(cm)
    for row in table.rows:
        for i, cm in enumerate(widths_cm):
            set_cell_width(row.cells[i], cm)


def para_format(p, align=None, before=0, after=0, line=1.0, keep_next=False, keep_together=True):
    pf = p.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(before), Pt(after), line
    pf.keep_with_next = keep_next
    pf.keep_together = keep_together
    if align is not None:
        p.alignment = align


def add_field(paragraph, instr, **fmt):
    def mk(kind):
        r = paragraph.add_run()
        style_run(r, **fmt)
        fc = OxmlElement("w:fldChar")
        fc.set(qn("w:fldCharType"), kind)
        r._element.append(fc)
        return r
    mk("begin")
    r = paragraph.add_run()
    style_run(r, **fmt)
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = " %s " % instr
    r._element.append(it)
    mk("separate")
    r = paragraph.add_run("1")
    style_run(r, **fmt)
    mk("end")


def rich_runs(paragraph, text, **fmt):
    """**bold** markers in the source text stay bold."""
    for i, part in enumerate(re.split(r"\*\*", text)):
        if part:
            f = dict(fmt)
            if i % 2 == 1:
                f["bold"] = True
            style_run(paragraph.add_run(part), **f)


def cell_text(cell, text, align="L", size=SZ_TABLE, bold=False, color=BODY, keep_next=False, font=None):
    text = "-" if text is None or str(text).strip() == "" or str(text) == "None" else str(text)
    p = cell.paragraphs[0]
    para_format(p, {"L": WD_ALIGN_PARAGRAPH.LEFT, "R": WD_ALIGN_PARAGRAPH.RIGHT,
                    "C": WD_ALIGN_PARAGRAPH.CENTER}[align], keep_next=keep_next)
    style_run(p.add_run(text), size=size, bold=bold, color=color, font=font)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    return p


def _soft(s):
    """Allow clean wraps in long underscore codes without changing what is shown."""
    s = str(s)
    return s.replace("_", "_" + ZWSP) if len(s) > 12 else s


class ReportBuilder:
    def __init__(self):
        self.doc = Document()
        self.table_no = 0
        self.h1 = 0
        self.h2 = 0
        self._setup()

    # -- document set-up ----------------------------------------------------------------
    def _setup(self):
        d = self.doc
        sec = d.sections[0]
        sec.page_width, sec.page_height = Cm(PAGE_W_CM), Cm(PAGE_H_CM)
        sec.top_margin = sec.bottom_margin = Cm(MARGIN_TB_CM)
        sec.left_margin = sec.right_margin = Cm(MARGIN_LR_CM)
        sec.header_distance = sec.footer_distance = Cm(1.25)
        dd = d.styles.element.find(qn("w:docDefaults"))
        if dd is not None:
            rpr = dd.find(qn("w:rPrDefault") + "/" + qn("w:rPr"))
            if rpr is not None:
                _set_rfonts(rpr, FONT_BODY)
        n = d.styles["Normal"]
        style_font(n, FONT_BODY, SZ_BODY, color=BODY)
        n.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        n.paragraph_format.line_spacing = 1.15
        n.paragraph_format.space_after = Pt(6)
        n.paragraph_format.space_before = Pt(0)
        h1 = d.styles["Heading 1"]
        style_font(h1, FONT_HEAD, 14, bold=True, color=NAVY)
        pf = h1.paragraph_format
        pf.space_before, pf.space_after, pf.keep_with_next, pf.alignment = Pt(16), Pt(7), True, WD_ALIGN_PARAGRAPH.LEFT
        bottom_border(h1.element.get_or_add_pPr())
        h2 = d.styles["Heading 2"]
        style_font(h2, FONT_BODY, 12, bold=True, color=STEEL)
        pf = h2.paragraph_format
        pf.space_before, pf.space_after, pf.keep_with_next, pf.alignment = Pt(10), Pt(4), True, WD_ALIGN_PARAGRAPH.LEFT
        lb = d.styles["List Bullet"]
        style_font(lb, FONT_BODY, SZ_BODY, color=BODY)
        lb.paragraph_format.space_after = Pt(2)
        lb.paragraph_format.line_spacing = 1.1
        lb.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    def header_footer(self, masked_pan, fy_label):
        sec = self.doc.sections[0]
        for st in ("Header", "Footer"):                      # drop the template's own centre/right tab stops
            self.doc.styles[st].paragraph_format.tab_stops.clear_all()
        hp = sec.header.paragraphs[0]
        para_format(hp, WD_ALIGN_PARAGRAPH.LEFT, after=0)
        hp.paragraph_format.tab_stops.add_tab_stop(Cm(CONTENT_W_CM), WD_TAB_ALIGNMENT.RIGHT)
        style_run(hp.add_run("AIS Tax Review  |  %s  |  FY %s" % (masked_pan, fy_label)), size=9, color=NAVY)
        style_run(hp.add_run("\tConfidential"), size=9, bold=True, color=NAVY)
        bottom_border(hp._p.get_or_add_pPr(), NAVY, 4, 4)
        fp = sec.footer.paragraphs[0]
        para_format(fp, WD_ALIGN_PARAGRAPH.CENTER, after=2)
        style_run(fp.add_run("Page "), size=9, color=GREY)
        add_field(fp, "PAGE", size=9, color=GREY)
        style_run(fp.add_run(" of "), size=9, color=GREY)
        add_field(fp, "NUMPAGES", size=9, color=GREY)
        f2 = sec.footer.add_paragraph()
        para_format(f2, WD_ALIGN_PARAGRAPH.CENTER)
        style_run(f2.add_run("Preliminary working paper based on AIS data only. Not a filed return or tax opinion."),
                  size=8, color=GREY)

    # -- text helpers ---------------------------------------------------------------------
    def heading1(self, text):
        self.h1 += 1
        self.h2 = 0
        return self.doc.add_paragraph("%d.  %s" % (self.h1, text), style="Heading 1")

    def heading2(self, text):
        self.h2 += 1
        return self.doc.add_paragraph("%d.%d  %s" % (self.h1, self.h2, text), style="Heading 2")

    def para(self, text, keep_next=False):
        p = self.doc.add_paragraph(style="Normal")
        rich_runs(p, text, size=SZ_BODY, color=BODY)
        p.paragraph_format.keep_with_next = keep_next
        return p

    def note(self, text, keep_next=False, before=3):
        p = self.doc.add_paragraph(style="Normal")
        para_format(p, WD_ALIGN_PARAGRAPH.LEFT, before=before, after=6, line=1.1, keep_next=keep_next)
        rich_runs(p, text, size=SZ_NOTE, italic=True, color=GREY)
        return p

    def bullet(self, text):
        p = self.doc.add_paragraph(style="List Bullet")
        rich_runs(p, text, size=SZ_BODY, color=BODY)
        return p

    def caption(self, text):
        self.table_no += 1
        p = self.doc.add_paragraph(style="Normal")
        para_format(p, WD_ALIGN_PARAGRAPH.LEFT, before=4, after=3, keep_next=True)
        style_run(p.add_run("Table %d: %s" % (self.table_no, text)), size=10, bold=True, color=NAVY)

    # -- the one reusable table function -----------------------------------------------------
    def add_table(self, widths_cm, header, rows, aligns, size=SZ_TABLE, bold_rows=(), flag_rows=(), caption=None,
                  flag_note=None):
        if caption:
            self.caption(caption)
        t = self.doc.add_table(rows=1 + len(rows), cols=len(widths_cm))
        table_setup(t, widths_cm)
        keep_chain = len(rows) <= 30
        hdr = t.rows[0]
        repeat_header(hdr)
        cant_split(hdr)
        for i, h in enumerate(header):
            c = hdr.cells[i]
            shade(c, NAVY)
            cell_text(c, h, aligns[i], size, True, WHITE, keep_next=True)
        for ri, row in enumerate(rows):
            tr = t.rows[ri + 1]
            cant_split(tr)
            last = ri == len(rows) - 1
            fill = ALT_ROW if ri % 2 == 0 else WHITE
            bold = ri in bold_rows
            if ri in flag_rows:
                fill = AMBER
            if bold:
                fill = LIGHT_BLUE
            for ci, val in enumerate(row):
                c = tr.cells[ci]
                shade(c, fill)
                cell_text(c, _soft(val) if isinstance(val, str) else val, aligns[ci], size, bold,
                          keep_next=(keep_chain and not last))
        if flag_rows and flag_note:
            self.note(flag_note)
        elif flag_rows and not getattr(self, "_dup_noted", False):      # explained once, not under every table
            self._dup_noted = True
            self.note("Amber shading marks rows flagged as possible duplicate rows; they are retained in the "
                      "computation unless excluded on the review screen.")
        return t

    # -- first page blocks ---------------------------------------------------------------------
    def title_band(self, fy_label, subtitle):
        t = self.doc.add_table(rows=1, cols=1)
        table_setup(t, [CONTENT_W_CM], border=None, pad=(16, 20))
        c = t.rows[0].cells[0]
        shade(c, NAVY)
        cell_borders(c)
        p = c.paragraphs[0]
        para_format(p, WD_ALIGN_PARAGRAPH.LEFT, after=6)
        style_run(p.add_run("TAX REVIEW  |  FY %s" % fy_label), size=10, bold=True, color=BAND_SUB, spacing=40)
        for line in ("Annual Information Statement", "Tax Review"):
            p = c.add_paragraph()
            para_format(p, WD_ALIGN_PARAGRAPH.LEFT, after=0, line=1.05)
            style_run(p.add_run(line), size=22, bold=True, color=WHITE, font=FONT_HEAD)
        p = c.add_paragraph()
        para_format(p, WD_ALIGN_PARAGRAPH.LEFT, before=6, after=0)
        style_run(p.add_run(subtitle), size=11, color=WHITE)

    def confidential(self):
        p = self.doc.add_paragraph()
        para_format(p, WD_ALIGN_PARAGRAPH.RIGHT, before=4, after=6)
        style_run(p.add_run("STRICTLY PRIVATE & CONFIDENTIAL"), size=8, bold=True, color=NAVY)

    def details_table(self, pairs):
        t = self.doc.add_table(rows=len(pairs), cols=2)
        table_setup(t, [4.2, CONTENT_W_CM - 4.2])
        for i, (k, v) in enumerate(pairs):
            a, b = t.rows[i].cells
            cant_split(t.rows[i])
            shade(a, ALT_ROW)
            cell_text(a, k, "L", SZ_TABLE, True, NAVY, keep_next=True)
            cell_text(b, v, "L", SZ_TABLE, True, BODY, keep_next=True)

    def callout(self, title, text=None, bullets=None):
        p0 = self.doc.add_paragraph()
        para_format(p0, before=0, after=0, line=0.5)
        t = self.doc.add_table(rows=1, cols=1)
        table_setup(t, [CONTENT_W_CM], border=None, pad=(6, 8))
        cant_split(t.rows[0])
        c = t.rows[0].cells[0]
        shade(c, AMBER)
        cell_borders(c, left=(24, AMBER_EDGE))
        p = c.paragraphs[0]
        para_format(p, WD_ALIGN_PARAGRAPH.LEFT, after=2, keep_next=False)   # row is cantSplit; no chain to what follows
        style_run(p.add_run(title), size=10, bold=True, color=NAVY)
        if text:
            p = c.add_paragraph()
            para_format(p, WD_ALIGN_PARAGRAPH.JUSTIFY)
            style_run(p.add_run(text), size=10, color=BODY)
        for b in bullets or []:                               # real Word bullets inside the box
            p = c.add_paragraph(style="List Bullet")
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            rich_runs(p, b, size=9.5, color=BODY)

    def kpi_tiles(self, tiles):
        """tiles: 8 tuples (label, value, dark?) -> 4 x 2 grid."""
        w = CONTENT_W_CM / 4
        t = self.doc.add_table(rows=2, cols=4)
        table_setup(t, [w] * 4, border=(24, WHITE), pad=(7, 7))
        for i, (label, value, dark) in enumerate(tiles):
            c = t.rows[i // 4].cells[i % 4]
            cant_split(t.rows[i // 4])
            shade(c, NAVY if dark else LIGHT_BLUE)
            p = c.paragraphs[0]
            para_format(p, WD_ALIGN_PARAGRAPH.LEFT, after=3, keep_next=True)
            style_run(p.add_run(label.upper()), size=7.5, bold=True, color=BAND_SUB if dark else STEEL, spacing=20)
            p2 = c.add_paragraph()
            para_format(p2, WD_ALIGN_PARAGRAPH.LEFT, keep_next=(i < 4))
            style_run(p2.add_run(value), size=14, bold=True, color=WHITE if dark else NAVY, font=FONT_HEAD)
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    def picture(self, png_bytes, width_cm=14):
        p = self.doc.add_paragraph()
        para_format(p, WD_ALIGN_PARAGRAPH.CENTER, before=2, after=2, keep_next=True)
        p.add_run().add_picture(io.BytesIO(png_bytes), width=Cm(width_cm))


def make_donut(heads, total):
    """heads: [(label, amount, hex)]  -> PNG bytes (dpi 200, white background)."""
    for fam in (["Calibri", "Segoe UI", "DejaVu Sans"],):
        plt.rcParams["font.family"] = fam
    vals = [float(a) for _, a, _ in heads]
    fig, ax = plt.subplots(figsize=(8, 3.9), dpi=200, facecolor="white")
    wedges, _ = ax.pie(vals, startangle=90, counterclock=False, colors=["#" + c for _, _, c in heads],
                       wedgeprops=dict(width=0.45, edgecolor="white", linewidth=1.5))
    tot = sum(vals)
    small = 0
    for w, v in zip(wedges, vals):
        frac = v / tot
        ang = math.radians((w.theta1 + w.theta2) / 2)
        if frac >= 0.10:
            ax.text(0.775 * math.cos(ang), 0.775 * math.sin(ang), "%.1f%%" % (frac * 100), ha="center",
                    va="center", color="white", fontsize=10, fontweight="bold")
        else:
            x, y = math.cos(ang), math.sin(ang)
            dx = (-0.3 if small % 2 else 0.3) if abs(x) < 0.5 else 0.0     # stagger neighbouring small slices
            small += 1
            ax.annotate("%.1f%%" % (frac * 100), xy=(0.97 * x, 0.97 * y), xytext=(1.32 * x + dx, 1.32 * y + 0.04 * small),
                        ha="left" if (x + dx) >= 0 else "right", va="center", fontsize=9, color="#" + NAVY,
                        arrowprops=dict(arrowstyle="-", color="#" + GREY, lw=0.8))
    ax.text(0, 0.1, "AIS income mix", ha="center", va="center", fontsize=11, fontweight="bold", color="#" + NAVY)
    ax.text(0, -0.13, money(total), ha="center", va="center", fontsize=11, color="#" + STEEL)
    handles = [plt.matplotlib.patches.Patch(color="#" + c, label="%s (%s)" % (l, money(a))) for l, a, c in heads]
    leg = fig.legend(handles=handles, loc="center right", frameon=False, title="Head (amount)", fontsize=9,
                     title_fontsize=9)
    plt.setp(leg.get_title(), color="#" + NAVY, fontweight="bold")
    ax.set_xlim(-1.7, 1.7)
    ax.set_ylim(-1.15, 1.6)
    ax.set_aspect("equal")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.96, bottom=0.04)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def group_rows(groups, heads, cols=("category", "code", "source", "flags")):
    """Aggregate included groups of the given heads -> table rows [cat, code, src, flags, count, amount]."""
    out = []
    for g in groups:
        if g["head"] in heads and g["include"]:
            out.append([g["category"], g["code"], g["source"], g["flags"], g["count"], g["amount"]])
    return out


W6 = [3.1, 2.5, 2.6, 3.4, 1.6, 3.4]
W6_HIGH = [2.9, 2.4, 4.7, 1.9, 1.2, 3.5]
AL6 = ["L", "L", "L", "L", "R", "R"]


def _six_table(rb, rows, caption, first_hdr="Category", src_hdr="Information source", widths=None, total=False):
    hdr = [first_hdr, "Code", src_hdr, "Status / flags", "AIS rows", "Amount"]
    flag = [i for i, r in enumerate(rows) if "possible duplicate row" in str(r[3])]
    body = [[r[0], r[1], r[2], r[3], str(r[4]), money(r[5])] for r in rows]
    bold = []
    if total and rows:
        body.append(["Total", "-", "-", "-", str(sum(r[4] for r in rows)), money(sum((r[5] for r in rows), D(0)))])
        bold = [len(body) - 1]
    rb.add_table(widths or W6, hdr, body, AL6, size=SZ_TABLE_WIDE, bold_rows=bold, flag_rows=flag, caption=caption)


def clean_security(name):
    """'LODHA DEVELOPERS LIMITED#NEW EQUITY SHARES ... (INE670K01029)' -> 'LODHA DEVELOPERS LIMITED (INE670K01029)'.
    The full AIS wording stays in the Excel workbook and the classified JSON."""
    s = str(name or "-")
    m = re.search(r"\(([A-Z]{2}[A-Z0-9]{9}\d)\)\s*$", s)
    base = re.split(r"\s*#|\s*-\s*EQUITY|\s+-\s|-\s", s)[0].strip() or s
    return "%s (%s)" % (base, m.group(1)) if m else base


def review_points(case, res):
    """Short list of the items a reviewer must look at first (shown on page 1)."""
    groups, prof = case["groups"], case["profile"]
    pts = []
    if res["cg_cost_zero_rows"]:
        pts.append("**%d sale(s)** of securities show no purchase cost in AIS (sale value %s): the gain was taken as the "
                   "full sale value. Enter the cost if it is known." % (res["cg_cost_zero_rows"], money(res["cg_cost_zero_sale"])))
    if res["cg_missing_rows"]:
        pts.append("**Data missing in AIS** for %d capital-gains row(s): they are excluded until the gain is entered." % res["cg_missing_rows"])
    p194t = [g for g in groups if norm_code(g["code"]) == "TDS-194T" and g["include"]]
    if p194t:
        pts.append("**Partner receipts %s** (TDS-194T) are taxed as business income. Confirm the amount against the firm's "
                   "statement; capital withdrawals are not income." % money(sum((g["amount"] for g in p194t), D(0))))
    dd = [g for g in groups if g.get("dedup_info")]
    if dd:
        pts.append("**Counted once:** %s of interest/dividend reported through both TDS and SFT was not added again." %
                   money(sum((g["amount"] for g in dd), D(0))))
    inactive = [g for g in groups if not g["active"]]
    if inactive and not prof["include_inactive"]:
        pts.append("**%d Inactive AIS row(s)** (%s) were excluded from income and tax credits." %
                   (sum(g["count"] for g in inactive), money(sum((g["amount"] for g in inactive), D(0)))))
    un = [g for g in groups if g["head"] == "unclassified"]
    if un:
        pts.append("**%d AIS item(s) are unclassified** (%s) and are not in income: classify them on the review screen." %
                   (sum(g["count"] for g in un), money(sum((g["amount"] for g in un), D(0)))))
    pts += res["warnings"][:2] + res["recon_notes"][:2]
    if res["manual_notes"]:
        pts.append("User inputs were applied (house property, business method or property sale); see the assumptions section.")
    return pts[:7]


def build_report(case, res, outdir, extra_log=None):
    ais, groups, prof, rules = case["ais"], case["groups"], case["profile"], res["rules"]
    mask = mask_pan(ais["pan"])
    fy = ais["fy"]
    rb = ReportBuilder()
    d = rb.doc
    rb.header_footer(mask, fy)
    c = res[res["chosen"]]
    old, new = res["old"], res["new"]
    better_lbl = "New" if res["better"] == "new" else "Old"
    # ---- first page -------------------------------------------------------------------------
    rb.title_band(fy, "Tentative computation based on AIS data only")
    rb.confidential()
    is25 = rules["act"] == "2025"
    rb.details_table([("Client", ais["name"] or "-"), ("PAN (masked)", mask),
                      ("Tax year" if is25 else "Financial year", fy),
                      ("Governing law" if is25 else "Assessment year", "Income-tax Act, 2025" if is25 else rules["ay"]),
                      ("Date prepared", _dt.date.today().strftime("%d %B %Y")),
                      ("Status", "Tentative / reconcile")])
    rb.callout("Important", "This is a preliminary tax review prepared from AIS-derived information. It is not a "
                            "filed return and must be reconciled with Form 26AS and supporting records.")
    rb.heading1("Executive summary")
    rb.kpi_tiles([("Tentative total income", money(res["kpi_income"]), False),
                  ("Better regime", better_lbl, True),
                  ("Gross tax", money(c["gross_tax"]), False),
                  ("Taxes paid per AIS", money(res["paid_total"]), False),
                  ("Net tax payable", money(c["net_payable"]), False),
                  ("Refund indicated", money(c["refund"]), True),
                  ("Tax difference", money(res["tax_diff"]), False),
                  ("Status", "Tentative / reconcile", False)])
    rb.note("Old regime: gross tax %s, refund %s.  New regime: gross tax %s, refund %s." %
            (money(old["gross_tax"]), money(old["refund"]), money(new["gross_tax"]), money(new["refund"])), before=5)
    pts = review_points(case, res)
    if pts:
        rb.callout("Points to review", bullets=pts)
    # ---- income -------------------------------------------------------------------------------
    inc, cnt = res["inc"], res["cnt"]
    cg_amt = c["cg_total_derived"]
    head_rows = []
    for h in ("salary", "hp", "cg", "business", "other", "winnings"):
        if h == "cg":
            head_rows.append([HEAD_LABELS[h], res["cg_cnt"] + (1 if res["property"] else 0), cg_amt])
        elif h == "winnings" and inc[h] == 0:
            continue
        else:
            head_rows.append([HEAD_LABELS[h], cnt[h], inc[h]])
    rb.heading1("Income reported in AIS")
    palette = {"cg": NAVY, "business": STEEL, "other": CHART_LIGHT}
    extra = iter(CHART_EXTRA)
    chart = [(lab, amt, palette.get({v: k for k, v in HEAD_LABELS.items()}[lab], None) or next(extra, GREY))
             for lab, n, amt in head_rows if amt > 0]
    tot_chart = sum((a for _, a, _ in chart), D(0))
    if chart:
        rb.picture(make_donut(chart, tot_chart), 14)
    rb.note("Chart uses AIS-reported ordinary income and AIS-derived taxable capital gains; purchase values are excluded.",
            before=0)
    body = [[r[0], str(r[1]), money(r[2])] for r in head_rows]
    body.append(["Total", str(sum(r[1] for r in head_rows)), money(sum((r[2] for r in head_rows), D(0)))])
    rb.add_table([7.0, 4.8, 4.8], ["Head of income", "AIS rows", "Summary amount"], body, ["L", "R", "R"],
                 bold_rows=[len(body) - 1], caption="Income by head as reported in AIS")
    rb.note("Capital gains show AIS-derived gain, not gross sale consideration. Full transaction-level data remains "
            "available in the classified JSON.")
    # capital gains
    rb.heading2("Capital gains")
    sp = {r["sec"] + r["bucket"]: r for r in c["special_rows"]}
    cgt = {}
    for g in res["cg_groups"]:
        k = (g["cg_sec"], g["bucket"])
        e = cgt.setdefault(k, {"n": 0, "sale": D(0), "gain": D(0), "missing": 0})
        e["n"] += g["count"]
        e["sale"] += g["amount"]
        gain = g["gain_used"]
        if gain is None or g["cg_sec"] is None:
            e["missing"] += g["count"]
        else:
            e["gain"] += D(gain)
    names = {"111A": "Short term / section 111A", "112A": "Long term / section 112A", "112": "Long term / section 112",
             "STG": "Short term / slab rate", None: "Manual treatment required"}
    cg_body = []
    for (sec, bucket), e in sorted(cgt.items(), key=lambda kv: (["111A", "112A", "112", "STG", None].index(kv[0][0]), kv[0][1] or "")):
        row = sp.get((sec or "") + (bucket or ""))
        taxable = row["taxable"] if row else (e["gain"] if sec == "STG" else None)
        tax = row["tax"] if row else None
        lab = names[sec] + ((" (before 23-Jul-2024)" if bucket == "pre" else " (on/after 23-Jul-2024)")
                            if rules["cg_mode"] == "split" and sec else "")
        cg_body.append([lab, str(e["n"]), money(e["sale"]), money(e["gain"]) if sec else "-",
                        money(taxable) if taxable is not None else "-", money(tax) if tax is not None else "-"])
    if res["property"]:
        pr = res["property"]
        cg_body.append([pr["label"], "1", money(pr["sale"]), money(pr["gain"]), "-", "-"])
    if cg_body:
        rb.add_table([4.4, 1.8, 2.6, 2.6, 2.6, 2.6], ["Type", "AIS rows", "Sale consideration", "Derived gain",
                     "Taxable gain", "Tax"], cg_body, ["L", "R", "R", "R", "R", "R"], size=SZ_TABLE_WIDE,
                     caption="Capital gains derived from AIS")
    else:
        rb.note("No capital-gains rows are included.")
    # other heads
    secs = [("salary", "Salary", "salary"), ("hp", "Income from house property", "house property"),
            ("business", "Business/profession", "business"), ("other", "Other sources", "other sources"),
            ("winnings", "Winnings (s.115BB)", "winnings")]
    for h, title, cap in secs:
        rows = group_rows(groups, [h])
        if not rows and h in ("salary", "hp", "winnings"):
            continue
        rb.heading2(title)
        if rows:
            _six_table(rb, rows, "AIS rows mapped to %s" % cap, total=True)
        else:
            rb.note("No rows are included under this head.")
    # ---- taxes paid ------------------------------------------------------------------------------
    rb.heading1("Taxes already paid / credited")
    if res["paid_rows"]:
        rows = [[r[0], r[1], r[2], r[3], str(r[4]), money(r[5])] for r in res["paid_rows"]]
        rows.append(["Total", "-", "-", "-", str(sum(r[4] for r in res["paid_rows"])), money(res["paid_total"])])
        flag = [i for i, r in enumerate(rows[:-1]) if "possible duplicate row" in str(r[3])]
        rb.add_table(W6, ["Type", "Code", "Source", "Status / flags", "AIS rows", "Amount"], rows, AL6,
                     size=SZ_TABLE_WIDE, bold_rows=[len(rows) - 1], flag_rows=flag,
                     caption="Tax deducted, collected or paid as per AIS")
    else:
        rb.note("No tax credits are reported in the AIS rows included.")
    if res["zero_credit_rows"]:
        rb.note("%d AIS tax rows with zero reported credit are omitted from this summary; they remain available in "
                "the classified JSON." % res["zero_credit_rows"])
    # ---- high value / unclassified -----------------------------------------------------------------
    rb.heading1("High-value transactions requiring explanation")
    hv = [[g["category"], g["code"], g["source"], g["flags"], g["count"], g["amount"]] for g in groups
          if g["head"] == "info" and g["amount"] > 0]
    if hv:
        _six_table(rb, hv, "Specified financial transactions reported for information", first_hdr="Category",
                   src_hdr="Source", widths=W6_HIGH)
    else:
        rb.note("None reported in the AIS file.")
    rb.heading1("Unclassified items requiring manual review")
    un = [[g["category"], g["code"], g["source"], g["flags"], g["count"], g["amount"]] for g in groups
          if g["head"] == "unclassified"]
    if un:
        _six_table(rb, un, "AIS items not mapped to a head of income", src_hdr="Source")
    else:
        rb.note("None.")
    # ---- computation ---------------------------------------------------------------------------------
    rb.heading1("Tentative tax computation")
    lines = [("Gross ordinary income", "gross_ord"), ("Standard deduction", "std"), ("Other deductions", "ded"),
             ("Ordinary taxable income", "ord_taxable"), ("Slab tax", "slab_tax"), ("Special-rate tax", "special_tax"),
             ("Rebate under section 87A", "rebate"), ("Surcharge", "surcharge"), ("Health & education cess", "cess"),
             ("Gross tax liability", "gross_tax"), ("Taxes paid per AIS", "paid"), ("Net tax payable", "net_payable"),
             ("Refund indicated", "refund")]
    body = [[lab, money(old[k]), money(new[k])] for lab, k in lines]
    bold = [i for i, (lab, _) in enumerate(lines) if lab in ("Gross tax liability", "Net tax payable", "Refund indicated")]
    rb.add_table([7.0, 4.8, 4.8], ["Particulars", "Old regime", "New regime"], body, ["L", "R", "R"],
                 bold_rows=bold, caption="Old regime versus new regime")
    for reg, title in (("old", "Old-regime slab working"), ("new", "New-regime slab working")):
        rb.heading2(title)
        r = res[reg]
        rows = [[money(s["frm"]), money(s["to"]) if s["to"] is not None else "Above", money(s["taxable"]),
                 pct(s["rate"]), money(s["tax"])] for s in r["slab_rows"]]
        if rows:
            rows.append(["Total", "-", money(sum(q0(s["taxable"]) for s in r["slab_rows"])), "-",
                         money(sum(q0(s["tax"]) for s in r["slab_rows"]))])
            rb.add_table([3.3] * 5 if False else [3.4, 3.4, 3.4, 2.6, 3.8], ["From", "To", "Taxable", "Rate", "Tax"],
                         rows, ["R", "R", "R", "R", "R"], bold_rows=[len(rows) - 1],
                         caption="%s slab working" % ("Old-regime" if reg == "old" else "New-regime"))
        else:
            rb.note("No ordinary taxable income.")
    rb.heading2("Special-rate income working")
    if c["special_rows"]:
        rows = [[r["label"], money(r["gain"]), money(r["exm"]), money(r["thr"]), money(r["taxable"]), money(r["tax"])]
                for r in c["special_rows"]]
        rb.add_table([4.4, 2.6, 2.4, 2.4, 2.4, 2.4], ["Category", "AIS-derived gain", "Basic exemption",
                     "Section threshold", "Taxable", "Tax"], rows, ["L", "R", "R", "R", "R", "R"], size=SZ_TABLE_WIDE,
                     caption="Special-rate income (%s regime)" % ("new" if res["chosen"] == "new" else "old"))
    else:
        rb.note("No special-rate income.")
    # ---- documents -------------------------------------------------------------------------------------
    rb.heading1("Documents required to finalise the ITR")
    rb.para("Preliminary checklist generated deterministically from the AIS categories present:", keep_next=True)
    heads_present = {g["head"] for g in groups if g["include"]}
    cats_text = " ".join((g["category"] + " " + g["code"]).upper() for g in groups if g["include"])
    docs = ["Form 26AS and complete AIS/TIS for the financial year",
            "All bank statements and year-end interest certificates",
            "Tax-payment challans and evidence of advance/self-assessment tax"]
    if "salary" in heads_present:
        docs.append("Form 16 / Form 12BA and salary slips")
    if "hp" in heads_present:
        docs.append("Rent agreements, municipal tax receipts and home-loan interest certificate")
    if "cg" in heads_present:
        docs += ["Broker capital-gains statement with STCG/LTCG split",
                 "Demat ledger, contract notes and acquisition-cost evidence"]
    if "business" in heads_present:
        docs += ["Books, trial balance, profit & loss account and balance sheet",
                 "GST returns/reconciliation and business bank statements"]
    if "other" in heads_present:
        if "INTEREST" in cats_text:
            docs.append("Bank/deposit interest certificates")
        docs.append("Dividend and other-income statements")
    if "winnings" in heads_present:
        docs.append("Winning statements and TDS certificates for lottery/game winnings")
    if any(g["head"] == "info" and g["amount"] > 0 for g in groups):
        docs.append("Source-of-funds explanation and supporting documents for high-value transactions")
    if any(norm_code(g["code"]) == "TDS-194T" and g["include"] for g in groups):
        docs.append("Partnership deed, partner's capital account and the firm's statement of remuneration / interest paid")
    if res["property"]:
        docs.append("Sale deed, purchase deed, indexation workings and transfer-expense bills for the property sale")
    for t in docs:
        rb.bullet(t)
    # ---- assumptions -------------------------------------------------------------------------------------
    rb.heading1("Assumptions, reconciliation and disclaimer")
    ass = ["Amounts are taken from AIS without netting or assuming undocumented deductions.",
           "Compare with Form 26AS, bank statements, Form 16, capital-gains reports and tax challans. This report uses "
           "AIS-derived amounts only.",
           "Verify residential status, regime eligibility, brought-forward losses, exemptions, Chapter VI-A deductions "
           "and foreign assets separately.",
           "This report is an advisory working paper, not a filed income-tax return or tax opinion."]
    if any(g["dup"] and g["include"] for g in groups):
        ass.append("AIS contains possible duplicate rows. They were retained in the computation and require "
                   "reconciliation in the classified JSON.")
    if res["cg_cnt"]:
        ass += ["AIS-derived capital gains assume the AIS holding classification and market-sale information are "
                "correct; reconcile with the broker capital-gains statement.",
                "Special-rate amounts require reconciliation with capital-gains statements, acquisition cost, losses "
                "and section eligibility.",
                "Tentative listed-equity gains were derived from AIS sale consideration less AIS cost for %d row(s)."
                % res["cg_cnt"]]
    if res["cg_cost_zero_rows"]:
        ass.append("**Data missing in AIS:** the purchase cost is not shown for %d capital-gains row(s) (sale "
                   "consideration %s); the gain was taken as the full consideration. Enter the cost on the Capital "
                   "Gains screen if it is available (bonus shares and gifted holdings may genuinely have nil cost)." %
                   (res["cg_cost_zero_rows"], money(res["cg_cost_zero_sale"])))
    if res["cg_fmv_rows"]:
        ass.append("AIS shows the 31-Jan-2018 fair market value for %d row(s); grandfathering was not applied - the "
                   "purchase cost is taken exactly as shown in AIS (VERIFY)." % res["cg_fmv_rows"])
    p194t = [g for g in groups if norm_code(g["code"]) == "TDS-194T" and g["include"]]
    if p194t:
        ass.append("Receipts from a partnership firm (TDS-194T, %s) were treated as business income (partner "
                   "remuneration / interest, s.28(v)). Confirm against the firm's partner statement: capital "
                   "withdrawals and the share of profit (exempt under s.10(2A)) are not income, and the firm's "
                   "deduction limits do not change the amount taxed in your hands (VERIFY)." %
                   money(sum((g["amount"] for g in p194t), D(0))))
    dd = {}
    for g in groups:
        if g.get("dedup_info"):
            dd.setdefault(g["dedup_info"], []).append("%s %s" % (g["code"], money(g["amount"])))
    for (keep, tot), items in dd.items():
        ass.append("Counted once (system-processed value): %s repeat income already reported through %s (%s) and were "
                   "not added to income." % ("; ".join(items), keep, money(tot)))
    ass += res["recon_notes"]
    inactive = [g for g in groups if not g["active"]]
    if inactive and not prof["include_inactive"]:
        ass.append("%d Inactive AIS row(s) totalling %s were excluded from income and tax credits (toggle on the "
                   "profile screen)." % (sum(g["count"] for g in inactive), money(sum((g["amount"] for g in inactive), D(0)))))
    elif inactive:
        ass.append("%d Inactive AIS row(s) were INCLUDED in income and tax credits by user choice." %
                   sum(g["count"] for g in inactive))
    if res["cg_missing_rows"]:
        ass.append("**Data missing in AIS** for %d capital-gains row(s): they are excluded until the gain is entered." %
                   res["cg_missing_rows"])
    ov = [g for g in groups if g["override"] is not None]
    if ov:
        ass.append("User input: capital-gain amount overridden for %d group(s)." % len(ov))
    if prof["ded_old"] or prof["ded_new"]:
        ass.append("User input: deductions of %s (old regime) and %s (new regime) were entered manually." %
                   (money(prof["ded_old"]), money(prof["ded_new"])))
    if prof["bf_stcl"] or prof["bf_ltcl"]:
        ass.append("User input: brought-forward short-term loss %s and long-term loss %s were set off." %
                   (money(prof["bf_stcl"]), money(prof["bf_ltcl"])))
    chg = [g for g in groups if g["head"] != g["orig_head"]]
    if chg:
        ass.append("User input: %d AIS group(s) were re-classified to a different head." % len(chg))
    if is25:
        ass.append("Section numbers follow the Income-tax Act, 1961; Income-tax Act, 2025 equivalents are VERIFY "
                   "(new regime 115BAC -> 202; TDS provisions -> 393).")
    ass += res["manual_notes"]
    ass += ["**Flag:** " + w for w in res["warnings"]]
    ass.append("Tax rates and thresholds applied for this year: %s." % rules["status"])
    res["_assumptions"] = ass
    for t in ass:
        rb.bullet(t)
    rb.heading2("Rate sources")
    for s in rules["sources"]:
        rb.bullet(s)
    rb.para("Official source URLs are retained in the tax-computation JSON.")
    if res["cg_tx"]:                                       # annexure: every sale with the purchase cost used
        rb.heading1("Annexure: capital gains by transaction")
        order = {"111A": 0, "112A": 1, "112": 2, "STG": 3}
        lab = {"111A": "111A", "112A": "112A", "112": "112", "STG": "Slab"}
        txs = sorted(res["cg_tx"], key=lambda t: (order.get(t["sec"], 9), parse_date(t["date"]) or _dt.date.min))
        rows = []
        for t in txs:
            cost = "-" if t["cost"] is None else money(t["cost"]) + (" (user)" if t["user"] else "")
            rows.append([t["date"] or "-", clean_security(t["name"]), lab.get(t["sec"], "Manual"),
                         "-" if t["qty"] is None else inr_group(t["qty"]), money(t["sale"]), cost,
                         "-" if t["gain"] is None else money(t["gain"])])
        flag = [i for i, t in enumerate(txs) if (t["zero"] or t["cost"] is None) and not t["user"]]
        rb.add_table([2.3, 5.5, 1.4, 1.2, 2.1, 2.0, 2.1], ["Date", "Security", "Section", "Qty", "Sale value",
                     "Purchase cost", "Gain / (loss)"], rows, ["L", "L", "L", "R", "R", "R", "R"], size=SZ_TABLE_WIDE,
                     flag_rows=flag, caption="Capital gains by transaction (sale value less purchase cost per AIS)",
                     flag_note="Amber rows: purchase cost not shown in AIS; the gain equals the sale value. Section totals "
                               "are in the capital-gains table above.")
    cp = d.core_properties
    cp.author, cp.title, cp.comments, cp.subject = CALC_APP_NAME, "AIS Tax Review FY %s" % fy, "", ""
    cp.last_modified_by = CALC_APP_NAME
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "%s_%s_AIS_report.docx" % (mask, fy))
    d.save(path)
    return path


def export_json(case, res, outdir):
    mask = mask_pan(case["ais"]["pan"])
    fy = case["ais"]["fy"]

    def enc(o):
        if isinstance(o, D):
            return str(o)
        if isinstance(o, (_dt.date, _dt.datetime)):
            return o.isoformat()
        return str(o)
    classified = {"pan_masked": mask, "fy": fy, "law": res["rules"]["label"], "groups": case["groups"],
                  "records": [{k: v for k, v in r.items()} for r in case["ais"]["records"]],
                  "challans": case["ais"]["challans"]}
    comp = {"pan_masked": mask, "fy": fy, "law": res["rules"]["label"], "rules_status": res["rules"]["status"],
            "rate_sources": res["rules"]["sources"], "profile": case["profile"],
            "result": {k: res[k] for k in ("old", "new", "better", "chosen", "paid_total", "paid_rows",
                                           "zero_credit_rows", "kpi_income", "tax_diff")},
            "disclaimer": DISCLAIMER}
    p1 = os.path.join(outdir, "%s_%s_classified.json" % (mask, fy))
    p2 = os.path.join(outdir, "%s_%s_tax_computation.json" % (mask, fy))
    for pth, obj in ((p1, classified), (p2, comp)):
        with open(pth, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=1, default=enc)
    return p1, p2




def parse_ais(path):
    return parse_ais_json(path)


def new_case(path):
    ais = parse_ais(path)
    prof = default_profile(ais)
    return {"path": path, "ais": ais, "profile": prof, "groups": build_groups(ais, prof["include_inactive"])}


def review_summary(case, res):
    """Plain data for the review dialog (sent to the window as JSON)."""
    c = res[res["chosen"]]
    old, new = res["old"], res["new"]
    lines = [("Gross ordinary income", "gross_ord"), ("Standard deduction", "std"), ("Other deductions", "ded"),
             ("Ordinary taxable income", "ord_taxable"), ("Slab tax", "slab_tax"), ("Special-rate tax", "special_tax"),
             ("Rebate under section 87A", "rebate"), ("Surcharge", "surcharge"), ("Health & education cess", "cess"),
             ("Gross tax liability", "gross_tax"), ("Taxes paid per AIS", "paid"), ("Net tax payable", "net_payable"),
             ("Refund indicated", "refund")]
    return {"name": case["ais"]["name"] or "-", "pan": mask_pan(case["ais"]["pan"]), "fy": case["ais"]["fy"],
            "law": res["rules"]["label"],
            "kpis": [["Tentative total income", money(res["kpi_income"])],
                     ["Better regime", "New" if res["better"] == "new" else "Old"],
                     ["Gross tax", money(c["gross_tax"])], ["Taxes paid per AIS", money(res["paid_total"])],
                     ["Net tax payable", money(c["net_payable"])], ["Refund indicated", money(c["refund"])]],
            "lines": [[lab, money(old[k]), money(new[k])] for lab, k in lines],
            "points": [re.sub(r"\*\*", "", p) for p in review_points(case, res)],
            "result": (["Tax payable", money(c["net_payable"]), "payable"] if c["net_payable"] else
                       ["Refund indicated", money(c["refund"]), "refund"] if c["refund"] else
                       ["Tax payable / refund", "Nil", "nil"])}


# ======================== END OF EMBEDDED CODE ========================



APP_NAME = "TaxReady - By CA Jatin Chauhan"
APP_TAGLINE = "Know your tax before you file"
SETTINGS_APP_NAME = "AIS Auto Downloader"      # unchanged on purpose: keeps saved Gmail / theme settings
APP_VERSION = "6.1"
PORTAL_HOME = "https://www.incometax.gov.in/iec/foportal/"
PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
FY_PATTERN = re.compile(r"^(20[0-9]{2})-([0-9]{2})$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 465
GMAIL_SENDER_SETTING = "gmail/sender_email"
GMAIL_PASSWORD_SETTING = "gmail/app_password_dpapi"


def valid_financial_year(value):
    match = FY_PATTERN.fullmatch(value.strip())
    return bool(match and int(match.group(2)) == (int(match.group(1)) + 1) % 100)


def safe_filename(value):
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", value).strip(" .")
    return value[:180] or "AIS_download"


def unique_path(path):
    if not path.exists():
        return path
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.with_name(f"{path.stem}_{stamp}{path.suffix}")


def normalize_app_password(value):
    return re.sub(r"\s+", "", str(value or ""))


def verify_gmail_smtp(sender_email, app_password):
    sender_email = sender_email.strip()
    app_password = normalize_app_password(app_password)
    if not EMAIL_PATTERN.fullmatch(sender_email):
        raise ValueError("Enter a valid sender Gmail address.")
    if len(app_password) != 16:
        raise ValueError("The Google App Password must contain exactly 16 characters.")
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(
        GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, context=context, timeout=30
    ) as smtp:
        smtp.login(sender_email, app_password)


class AutomationWorker(QObject):
    progress = pyqtSignal(int, str)
    log = pyqtSignal(str)
    manual_action = pyqtSignal(str)
    finished = pyqtSignal(str)
    email_failed = pyqtSignal(str, str)
    review_needed = pyqtSignal(str, object)
    profile_captured = pyqtSignal(str)
    failed = pyqtSignal(str)
    stopped = pyqtSignal()

    def __init__(
        self,
        pan,
        password,
        financial_year,
        output_root,
        email_enabled=False,
        client_email="",
        sender_email="",
        gmail_app_password="",
        client_name="",
        review_before_email=True,
    ):
        super().__init__()
        self.pan = pan
        self.password = password
        self.financial_year = financial_year
        self.output_root = Path(output_root)
        self.email_enabled = email_enabled
        self.client_email = client_email
        self.sender_email = sender_email
        self.gmail_app_password = normalize_app_password(gmail_app_password)
        self.client_name = client_name.strip()
        self.date_of_birth = ""
        self.fallback_dob = ""            # DOB typed in the client details (used only if the portal capture fails)
        self.review_before_email = bool(review_before_email)
        self.email_status = "Not requested"
        self._work_dir = None             # temporary folder for the download / decrypted data (always deleted)
        self._case = None                 # computed case (handed to the review window)
        self._summary = {}                # key figures used in the email
        self._review_event = threading.Event()
        self._review_ok = False
        self.stop_event = threading.Event()
        self._context = None
        self._browser_connection = None
        self._browser_process = None

    def request_stop(self):
        self.stop_event.set()

    def _check_stop(self):
        if self.stop_event.is_set():
            raise InterruptedError("Stopped by user")

    def _status(self, percent, message):
        self._check_stop()
        self.progress.emit(percent, message)
        self.log.emit(f"{datetime.now():%H:%M:%S}  {message}")

    @staticmethod
    def _first_visible(page, selectors, timeout_ms=25_000):
        deadline = time.monotonic() + timeout_ms / 1000
        last_error = None
        while time.monotonic() < deadline:
            for selector in selectors:
                try:
                    locator = page.locator(selector).first
                    if locator.count() and locator.is_visible():
                        return locator
                except Exception as exc:
                    last_error = exc
            page.wait_for_timeout(250)
        raise PlaywrightTimeoutError(
            "Expected portal control was not visible. "
            f"Checked: {', '.join(selectors[:4])}. {last_error or ''}"
        )

    @staticmethod
    def _fill_first(page, selectors, value, timeout_ms=25_000):
        field = AutomationWorker._first_visible(page, selectors, timeout_ms)
        field.fill(value)
        return field

    @staticmethod
    def _click_first(page, selectors, timeout_ms=25_000):
        control = AutomationWorker._first_visible(page, selectors, timeout_ms)
        control.click()
        return control

    def _launch_browser(self, playwright, profile_dir):
        # Start the installed browser normally and then attach Playwright through
        # Chrome DevTools Protocol. This keeps Chrome's normal Windows sandbox
        # enabled and avoids Playwright's default --no-sandbox launch flag, which
        # is rejected by the Income-tax portal on some systems.
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            (Path(program_files) / "Google/Chrome/Application/chrome.exe", "Google Chrome"),
            (Path(program_files_x86) / "Google/Chrome/Application/chrome.exe", "Google Chrome"),
            (Path(local_app_data) / "Google/Chrome/Application/chrome.exe", "Google Chrome"),
            (Path(program_files) / "Microsoft/Edge/Application/msedge.exe", "Microsoft Edge"),
            (Path(program_files_x86) / "Microsoft/Edge/Application/msedge.exe", "Microsoft Edge"),
        ]
        seen = set()
        errors = []

        for executable, label in candidates:
            key = str(executable).lower()
            if key in seen or not executable.is_file():
                continue
            seen.add(key)
            try:
                self.log.emit(f"Opening {label} with the Windows security sandbox enabled...")
                port_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                port_socket.bind(("127.0.0.1", 0))
                port = port_socket.getsockname()[1]
                port_socket.close()
                command = [
                    str(executable),
                    f"--remote-debugging-port={port}",
                    "--remote-debugging-address=127.0.0.1",
                    f"--user-data-dir={profile_dir}",
                    "--start-maximized",
                    "--disable-notifications",
                    "--disable-popup-blocking",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "about:blank",
                ]
                creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                self._browser_process = subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creation_flags,
                )

                connect_deadline = time.monotonic() + 25
                last_connect_error = None
                while time.monotonic() < connect_deadline:
                    self._check_stop()
                    if self._browser_process.poll() is not None:
                        raise RuntimeError(f"{label} closed before the connection was ready")
                    try:
                        self._browser_connection = playwright.chromium.connect_over_cdp(
                            f"http://127.0.0.1:{port}", timeout=3_000
                        )
                        break
                    except Exception as exc:
                        last_connect_error = exc
                        time.sleep(0.25)
                if self._browser_connection is None:
                    raise RuntimeError(
                        f"Could not connect to {label}'s secure browser session: {last_connect_error}"
                    )
                if not self._browser_connection.contexts:
                    raise RuntimeError(f"{label} did not create a browser context")
                return self._browser_connection.contexts[0]
            except Exception as exc:
                errors.append(f"{label}: {exc}")
                if self._browser_connection is not None:
                    try:
                        self._browser_connection.close()
                    except Exception:
                        pass
                    self._browser_connection = None
                if self._browser_process is not None:
                    try:
                        self._browser_process.terminate()
                    except Exception:
                        pass
                    self._browser_process = None

        raise RuntimeError(
            "Google Chrome or Microsoft Edge could not be started securely. "
            "Close other automated portal windows and retry.\n" + "\n".join(errors)
        )

    def _login(self, context, page):
        self._status(8, "Opening the official Income-tax e-Filing homepage")
        page.goto(PORTAL_HOME, wait_until="domcontentloaded", timeout=90_000)

        # Do not open the internal eportal login URL directly. The portal first
        # establishes session cookies and routing information on its public
        # homepage; bypassing that step can return a plain "Permission Denied".
        body_text = page.locator("body").inner_text(timeout=15_000).lower()
        if "permission denied" in body_text:
            raise RuntimeError(
                "The public Income-tax homepage returned Permission Denied. Close all automated "
                "portal windows, wait one minute and retry without VPN/proxy."
            )

        self._status(12, "Starting login from the public portal homepage")
        existing_pages = set(context.pages)
        self._click_first(page, [
            'button:has-text("Login")',
            'a:has-text("Login")',
            'a[href*="login" i]',
            'text="Login"',
        ], timeout_ms=35_000)

        # Login normally opens in the same tab, but accept a new tab if the
        # portal changes its routing.
        login_page = page
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            self._check_stop()
            new_pages = [candidate for candidate in context.pages if candidate not in existing_pages]
            candidates = list(reversed(new_pages)) + [page]
            for candidate in candidates:
                try:
                    candidate.wait_for_load_state("domcontentloaded", timeout=1_500)
                except Exception:
                    pass
                try:
                    if (
                        "login" in candidate.url.lower()
                        or candidate.locator('input[formcontrolname="userName"]').count()
                        or candidate.locator('input[placeholder*="User ID" i]').count()
                    ):
                        login_page = candidate
                        break
                except Exception:
                    continue
            if login_page is not page or "login" in login_page.url.lower():
                break
            page.wait_for_timeout(300)

        login_page.bring_to_front()
        page = login_page
        try:
            denied_text = page.locator("body").inner_text(timeout=8_000).lower()
            if "permission denied" in denied_text:
                raise RuntimeError(
                    "The Income-tax portal denied the login session. The revised utility no longer "
                    "uses the direct login URL or --no-sandbox. Close this browser and retry once."
                )
        except RuntimeError:
            raise
        except Exception:
            pass

        self._status(16, "Entering PAN")
        self._fill_first(page, [
            'input[formcontrolname="userName"]',
            'input[name="userName"]',
            'input[placeholder*="User ID" i]',
            'input[placeholder*="PAN" i]',
            'input[type="text"]',
        ], self.pan)
        self._click_first(page, [
            'button:has-text("Continue")',
            'button:has-text("Proceed")',
            'input[type="submit"]',
        ])

        self._status(25, "Confirming secure-access message")
        try:
            checkbox = self._first_visible(page, [
                'input[type="checkbox"]',
                '[role="checkbox"]',
            ], timeout_ms=15_000)
            checked = checkbox.get_attribute("aria-checked") == "true"
            if not checked:
                try:
                    checked = checkbox.is_checked()
                except Exception:
                    checked = False
            if not checked:
                checkbox.click()
        except Exception:
            self.log.emit("Secure-access checkbox was not shown; continuing.")

        self._status(32, "Entering password securely")
        self._fill_first(page, [
            'input[formcontrolname="password"]',
            'input[name="password"]',
            'input[type="password"]',
        ], self.password)
        self._click_first(page, [
            'button:has-text("Continue")',
            'button:has-text("Login")',
            'button:has-text("Proceed")',
            'input[type="submit"]',
        ])

        # Two portal-specific responses can appear after valid credentials:
        # 1. A transient "Request is not authenticated" message. The portal
        #    accepts the same request when Continue is clicked again.
        # 2. A Dual Login dialog, which must be confirmed with "Login Here".
        authentication_retries = 0
        authentication_retry_deadline = time.monotonic() + 5 * 60
        dual_login_clicks = 0
        page.wait_for_timeout(1_500)

        while True:
            self._check_stop()
            response_deadline = time.monotonic() + 8
            error_still_visible = False
            quiet_rounds = 0
            login_completed = False

            # Wait for the result of the current Continue click. The old error
            # banner can remain in the DOM for several seconds even after the
            # next request has been submitted, so do not count it immediately
            # as a new failure.
            while time.monotonic() < response_deadline:
                self._check_stop()
                try:
                    visible_text = page.locator("body").inner_text(timeout=2_000).lower()
                    current_url = page.url.lower()
                except Exception:
                    page.wait_for_timeout(500)
                    continue

                dual_login_visible = (
                    "dual login detected" in visible_text
                    or "session is currently active in another" in visible_text
                )
                if dual_login_visible:
                    if dual_login_clicks >= 3:
                        raise RuntimeError(
                            "The Dual Login dialog did not close after selecting Login Here. "
                            "Close the other active e-Filing session and retry."
                        )
                    dual_login_clicks += 1
                    self.log.emit("Dual Login Detected; selecting Login Here.")
                    self._click_first(page, [
                        'button:has-text("Login Here")',
                        '[role="button"]:has-text("Login Here")',
                        'text="Login Here"',
                    ], timeout_ms=12_000)
                    page.wait_for_timeout(2_000)
                    continue

                # Stop retrying as soon as dashboard/navigation content is
                # available, even if the old error banner has not yet been
                # removed from the page's DOM.
                dashboard_visible = any(token in visible_text for token in (
                    "pending actions", "annual information statement", "view ais",
                    "file income tax forms", "dashboard"
                ))
                if "login" not in current_url and dashboard_visible:
                    login_completed = True
                    break

                error_still_visible = "request is not authenticated" in visible_text
                if error_still_visible:
                    quiet_rounds = 0
                else:
                    quiet_rounds += 1
                    if quiet_rounds >= 5:
                        break
                page.wait_for_timeout(500)

            if login_completed or not error_still_visible:
                break

            if time.monotonic() >= authentication_retry_deadline:
                raise RuntimeError(
                    "The portal continued to report 'Request is not authenticated' for five "
                    "minutes. Close other e-Filing sessions, wait one minute and try again."
                )

            authentication_retries += 1
            self.log.emit(
                f"Portal still reports Request is not authenticated; waiting and clicking "
                f"Continue again (retry {authentication_retries})."
            )
            page.wait_for_timeout(1_500)
            self._click_first(page, [
                'button:has-text("Continue")',
                'button:has-text("Login")',
                'input[type="submit"]',
            ], timeout_ms=15_000)
            page.wait_for_timeout(2_500)

        self._status(40, "Waiting for the taxpayer dashboard")
        try:
            page.wait_for_url(lambda url: "login" not in url.lower(), timeout=120_000)
        except PlaywrightTimeoutError:
            # The portal sometimes retains a route containing 'login' after rendering
            # the dashboard. Visible dashboard text is a stronger fallback signal.
            self._first_visible(page, [
                'text=Dashboard',
                'text=Services',
                'text=Annual Information Statement',
                'text=e-File',
            ], timeout_ms=30_000)

        body_text = page.locator("body").inner_text(timeout=10_000).lower()
        if any(text in body_text for text in (
            "invalid password", "incorrect password", "invalid user id", "account is locked"
        )):
            raise RuntimeError("The portal rejected the PAN/password. Please verify the credentials.")
        return page

    @staticmethod
    def _extract_date_of_birth(page):
        input_selectors = [
            'input[formcontrolname*="dob" i]',
            'input[formcontrolname*="dateOfBirth" i]',
            'input[name*="dob" i]',
            'input[name*="dateOfBirth" i]',
            'input[id*="dob" i]',
            'input[id*="dateOfBirth" i]',
        ]
        for selector in input_selectors:
            try:
                locator = page.locator(selector).first
                if locator.count():
                    candidate = locator.input_value(timeout=1_500)
                    normalized = normalize_date_of_birth(candidate)
                    if normalized:
                        return normalized
            except Exception:
                continue
        try:
            page_text = page.locator("body").inner_text(timeout=8_000)
        except Exception:
            return ""
        labelled_date = re.search(
            r"(?:date\s*of\s*birth|d\.?\s*o\.?\s*b\.?)"
            r"\s*(?:[:\-]|\r?\n)?\s*"
            r"("
            r"\d{1,2}[./-]\d{1,2}[./-]\d{4}"
            r"|\d{4}[./-]\d{1,2}[./-]\d{1,2}"
            r"|\d{1,2}(?:\s+|-)\w{3,9}(?:\s+|-)\d{4}"
            r")",
            page_text,
            re.IGNORECASE,
        )
        return normalize_date_of_birth(labelled_date.group(1)) if labelled_date else ""

    def _capture_date_of_birth(self, context, page, progress=44):
        """Best-effort DOB capture; a portal layout change must not stop AIS download."""
        if self.date_of_birth:
            return
        if progress is not None:
            self._status(progress, "Capturing taxpayer date of birth")
        profile_page = None
        try:
            date_of_birth = self._extract_date_of_birth(page)
            if not date_of_birth:
                profile_selectors = [
                    'a:has-text("My Profile")',
                    'a[href*="my-profile" i]',
                    'a[href*="profile" i]',
                ]

                def profile_href():
                    for selector in profile_selectors:
                        try:
                            locator = page.locator(selector)
                            for index in range(min(locator.count(), 8)):
                                href = locator.nth(index).get_attribute("href")
                                if href:
                                    return href
                        except Exception:
                            continue
                    return ""

                href = profile_href()
                if not href:
                    for selector in (
                        'button[aria-label*="profile" i]',
                        '[role="button"][aria-label*="account" i]',
                        'button[title*="profile" i]',
                        'img[alt*="profile" i]',
                    ):
                        try:
                            control = page.locator(selector).first
                            if control.count() and control.is_visible():
                                control.click()
                                page.wait_for_timeout(800)
                                break
                        except Exception:
                            continue
                    href = profile_href()

                if href:
                    profile_page = context.new_page()
                    profile_page.goto(
                        urljoin(page.url, href),
                        wait_until="domcontentloaded",
                        timeout=45_000,
                    )
                    profile_page.wait_for_timeout(1_500)
                    try:
                        personal_details = profile_page.locator(
                            'text="Personal Details"'
                        ).first
                        if personal_details.count() and personal_details.is_visible():
                            personal_details.click()
                            profile_page.wait_for_timeout(1_000)
                    except Exception:
                        pass
                    date_of_birth = self._extract_date_of_birth(profile_page)

            if date_of_birth:
                self.date_of_birth = date_of_birth
                self.profile_captured.emit(date_of_birth)
                self.log.emit("Taxpayer date of birth captured and sent to the client database.")
            else:
                self.log.emit(
                    "Date of birth was not visible on the current portal/profile layout; "
                    "the AIS download will continue."
                )
        except Exception as exc:
            self.log.emit(
                "Date of birth capture was unavailable; continuing the AIS download. "
                + str(exc)[:180]
            )
        finally:
            if profile_page is not None:
                try:
                    profile_page.close()
                except Exception:
                    pass

    def _open_ais_portal(self, context, page):
        self._status(48, "Opening Annual Information Statement (AIS)")
        old_pages = set(context.pages)

        # Route 1: dashboard AIS card / quick link. The exact accessible name
        # differs between portal releases, so cover text, title, aria-label and
        # href-based variants.
        ais_clicked = False
        dashboard_selectors = [
            'text="Annual Information Statement (AIS)"',
            'text="Annual Information Statement"',
            'a[href*="ais" i]',
            '[aria-label*="Annual Information Statement" i]',
            '[title*="Annual Information Statement" i]',
            'a:has-text("Annual Information Statement")',
            'button:has-text("Annual Information Statement")',
            '[role="button"]:has-text("Annual Information Statement")',
            'text="View AIS"',
            'a:has-text("View AIS")',
            'button:has-text("View AIS")',
            'a:has-text("AIS")',
            'button:has-text("AIS")',
        ]
        try:
            self._click_first(page, dashboard_selectors, timeout_ms=20_000)
            ais_clicked = True
            self.log.emit("Opened AIS from the dashboard link/card.")
        except Exception:
            pass

        # Route 2: Services > Annual Information Statement (AIS).
        if not ais_clicked:
            self.log.emit("AIS quick link not visible; trying the Services menu.")
            try:
                self._click_first(page, [
                    'button:has-text("Services")',
                    'a:has-text("Services")',
                    '[role="button"]:has-text("Services")',
                    '[role="menuitem"]:has-text("Services")',
                    'text="Services"',
                ], timeout_ms=15_000)
                self._click_first(page, [
                    'text="Annual Information Statement (AIS)"',
                    'text="Annual Information Statement"',
                    '[role="menuitem"]:has-text("Annual Information Statement")',
                    'a:has-text("Annual Information Statement")',
                    'text="View AIS"',
                ], timeout_ms=20_000)
                ais_clicked = True
                self.log.emit("Opened AIS from the Services menu.")
            except Exception:
                pass

        # Route 3: e-File > Income Tax Returns > View AIS.
        if not ais_clicked:
            self.log.emit("Services route not visible; trying e-File > Income Tax Returns > View AIS.")
            try:
                self._click_first(page, [
                    'button:has-text("e-File")',
                    'a:has-text("e-File")',
                    '[role="button"]:has-text("e-File")',
                    '[role="menuitem"]:has-text("e-File")',
                    'text="e-File"',
                ], timeout_ms=15_000)
                self._click_first(page, [
                    'text="Income Tax Returns"',
                    'a:has-text("Income Tax Returns")',
                    'button:has-text("Income Tax Returns")',
                    '[role="menuitem"]:has-text("Income Tax Returns")',
                ], timeout_ms=15_000)
                self._click_first(page, [
                    'text="View AIS"',
                    'a:has-text("View AIS")',
                    'button:has-text("View AIS")',
                    '[role="menuitem"]:has-text("View AIS")',
                    'text="Annual Information Statement (AIS)"',
                ], timeout_ms=20_000)
                ais_clicked = True
                self.log.emit("Opened AIS through e-File > Income Tax Returns > View AIS.")
            except Exception as exc:
                raise RuntimeError(
                    "Could not find the AIS link after login using the Dashboard, Services, or "
                    "e-File routes. Confirm that the taxpayer dashboard is fully loaded and retry."
                ) from exc

        self._status(55, "Confirming redirect to the AIS Compliance Portal")
        try:
            self._click_first(page, [
                'button:has-text("Proceed")',
                'button:has-text("Continue")',
                'a:has-text("Proceed")',
            ], timeout_ms=20_000)
        except Exception:
            self.log.emit("Proceed prompt was not shown; checking the redirected page.")

        # The Proceed action opens the AIS Compliance Portal in a new tab. Wait
        # for that tab explicitly, select it, and do not continue on the e-Filing
        # dashboard by mistake.
        deadline = time.monotonic() + 90
        ais_page = page
        found_ais_page = False
        while time.monotonic() < deadline:
            self._check_stop()
            new_pages = [candidate for candidate in context.pages if candidate not in old_pages]
            candidates = list(reversed(new_pages)) + [page]
            for candidate in candidates:
                try:
                    candidate.wait_for_load_state("domcontentloaded", timeout=2_000)
                except Exception:
                    pass
                try:
                    url = candidate.url.lower()
                    title = (candidate.title() or "").lower()
                    if any(token in url for token in ("ais", "insight", "complianceportal")) or (
                        "annual information statement" in title
                    ):
                        ais_page = candidate
                        found_ais_page = True
                        break
                except Exception:
                    continue
            if found_ais_page:
                break
            page.wait_for_timeout(500)

        if not found_ais_page:
            raise RuntimeError(
                "The AIS link was clicked, but the AIS Compliance Portal did not open in a new tab. "
                "Please allow pop-ups for incometax.gov.in and retry."
            )
        ais_page.bring_to_front()
        self.log.emit(f"Switched to the AIS portal tab: {ais_page.url}")
        return ais_page

    def _open_ais_tab_beside_instructions(self, page):
        """Follow the revised SOP: Instructions page -> adjacent AIS tab."""
        self._status(60, "Clicking the AIS tab beside Instructions")
        self.log.emit("Revised SOP step: click AIS tab adjacent to Instructions.")

        # Do not use a global "AIS" text or href selector: the blue top ribbon
        # also contains an AIS menu. Every selector below is anchored to the
        # lower tab strip that contains the adjacent Instructions item.
        adjacent_tab_selectors = [
            "xpath=//*[@role='tablist'][.//*[normalize-space(.)='Instructions']]//*[normalize-space(.)='AIS']",
            "xpath=//*[contains(concat(' ',normalize-space(@class),' '),' nav-tabs ')][.//*[normalize-space(.)='Instructions']]//*[normalize-space(.)='AIS']",
            "xpath=//*[normalize-space(.)='Instructions']/following-sibling::*[normalize-space(.)='AIS']",
            "xpath=//*[normalize-space(.)='Instructions']/parent::*/following-sibling::*//*[normalize-space(.)='AIS']",
            "xpath=(//*[normalize-space(.)='Instructions']/ancestor::*[self::ul or self::nav or @role='tablist'][1]//*[normalize-space(.)='AIS'])[1]",
        ]
        tab = self._first_visible(page, adjacent_tab_selectors, timeout_ms=30_000)
        self.log.emit("Located the lower AIS tab through its Instructions-tab relationship.")
        tab.click()

        # The Compliance Portal is a single-page application. Verify that the
        # route leaves /instructions before searching for the FY dropdown.
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            self._check_stop()
            try:
                current_url = page.url.lower()
                selected = tab.get_attribute("aria-selected") == "true"
                if "/instructions" not in current_url or selected:
                    self.log.emit(f"AIS tab opened successfully: {page.url}")
                    return
            except Exception:
                pass
            page.wait_for_timeout(500)

        # One DOM-click retry handles portal overlays that sometimes absorb the
        # first pointer click while the Instructions page is still rendering.
        try:
            tab.evaluate("element => element.click()")
        except Exception:
            pass
        page.wait_for_timeout(2_000)
        if "/instructions" in page.url.lower():
            raise RuntimeError(
                "The AIS tab beside Instructions was found but did not open. "
                "Wait for the Instructions page to finish loading and retry."
            )
        self.log.emit(f"AIS tab opened successfully after retry: {page.url}")

    def _open_annual_information_statement_form_168(self, page):
        """AIS Home -> Annual Information Statement (AIS - Form 168) card."""
        self._status(63, "Opening Annual Information Statement (AIS - Form 168)")
        self.log.emit("Revised SOP step: open Annual Information Statement (AIS - Form 168) card.")

        card = self._first_visible(page, [
            "xpath=//*[normalize-space(.)='Annual Information Statement (AIS - Form 168)']",
            "xpath=//*[contains(normalize-space(.),'Annual Information Statement') and contains(normalize-space(.),'AIS - Form 168') and not(.//*[contains(normalize-space(.),'AIS - Form 168')])]",
            'text=/Annual Information Statement\\s*\\(AIS\\s*-\\s*Form\\s*168\\)/i',
            '[role="button"]:has-text("Annual Information Statement"):has-text("Form 168")',
        ], timeout_ms=30_000)
        self.log.emit("Located the Annual Information Statement (AIS - Form 168) tile text.")
        card.click()

        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            self._check_stop()
            try:
                heading = page.locator('text=/Annual Information Statement\\s*-\\s*Form\\s*168/i').first
                download = page.locator('button:has-text("Download")').first
                fy_control = page.locator('select, [role="combobox"], button:has-text("F.Y.")').first
                if (
                    (heading.count() and heading.is_visible())
                    and (
                        (download.count() and download.is_visible())
                        or (fy_control.count() and fy_control.is_visible())
                    )
                ):
                    self.log.emit("Annual Information Statement - Form 168 detail page opened.")
                    return
            except Exception:
                pass
            page.wait_for_timeout(500)

        raise RuntimeError(
            "The Annual Information Statement (AIS - Form 168) card was clicked, but its detail "
            "page did not open."
        )

    def _select_financial_year(self, page):
        self._status(67, f"Selecting F.Y. {self.financial_year} on Form 168")
        expected_label = f"F.Y. {self.financial_year}"

        # The revised portal shows this control only after opening Form 168. For
        # a native <select>, choose the option whose label contains the requested
        # year because the displayed label is "F.Y. 2025-26", not "2025-26".
        for selector in ('select[formcontrolname*="financial" i]', 'select'):
            try:
                controls = page.locator(selector)
                for index in range(controls.count()):
                    control = controls.nth(index)
                    if not control.is_visible():
                        continue
                    option_texts = control.locator("option").all_text_contents()
                    matching_label = next(
                        (text.strip() for text in option_texts if self.financial_year in text),
                        None,
                    )
                    if matching_label:
                        control.select_option(label=matching_label)
                        page.wait_for_timeout(1_000)
                        self.log.emit(f"Selected {matching_label} from the Form 168 F.Y. dropdown.")
                        return
            except Exception:
                continue

        # Custom Bootstrap/Angular dropdown variant shown in the revised SOP.
        try:
            control = self._first_visible(page, [
                'button:has-text("F.Y.")',
                '[role="combobox"]:has-text("F.Y.")',
                '[aria-haspopup="listbox"]:has-text("F.Y.")',
                '[class*="dropdown" i]:has-text("F.Y.")',
            ], timeout_ms=20_000)
            control.click()
            option = self._first_visible(page, [
                f'[role="option"]:has-text("{expected_label}")',
                f'li:has-text("{expected_label}")',
                f'a:has-text("{expected_label}")',
                f'text="{expected_label}"',
                f'text="{self.financial_year}"',
            ], timeout_ms=15_000)
            option.click()
            page.wait_for_timeout(1_000)
            self.log.emit(f"Selected {expected_label} from the Form 168 F.Y. dropdown.")
            return
        except Exception as exc:
            raise RuntimeError(
                f"{expected_label} was not available on the Form 168 F.Y. dropdown."
            ) from exc

    def _choose_json_and_start_download(self, page, downloads):
        """Select the JSON row/card in the download dialog and start it."""
        self._status(83, "Selecting JSON in the AIS download window")

        # Wait for the portal overlay. AIS releases have used Bootstrap,
        # Angular Material and ng-bootstrap containers, so accept each form.
        dialog = None
        dialog_deadline = time.monotonic() + 25
        dialog_selectors = [
            '[role="dialog"]',
            'mat-dialog-container',
            'ngb-modal-window',
            '.modal-content',
            '.cdk-overlay-pane',
            '[class*="modal-content" i]',
        ]
        while time.monotonic() < dialog_deadline and dialog is None:
            self._check_stop()
            for selector in dialog_selectors:
                try:
                    candidates = page.locator(selector)
                    for index in range(candidates.count()):
                        candidate = candidates.nth(index)
                        if candidate.is_visible():
                            dialog = candidate
                            break
                except Exception:
                    continue
                if dialog is not None:
                    break
            if dialog is None:
                page.wait_for_timeout(400)

        scope = dialog if dialog is not None else page
        if dialog is not None:
            self.log.emit("AIS download dialog detected.")
        else:
            self.log.emit("No separate dialog container detected; checking the visible page overlay.")

        # Locate JSON by visible text or by attributes/icons used by the portal.
        json_marker = self._first_visible(scope, [
            'text=/\\bJSON\\b/i',
            '[aria-label*="JSON" i]',
            '[title*="JSON" i]',
            '[value*="JSON" i]',
            '[data-format*="JSON" i]',
            'img[src*="json" i]',
            'input[type="radio"][value*="json" i]',
        ], timeout_ms=25_000)

        # Select/check the JSON choice first. Clicking a text marker is safe:
        # browser click events bubble to its card/radio-label container.
        try:
            tag_name = json_marker.evaluate("element => element.tagName.toLowerCase()")
            input_type = (json_marker.get_attribute("type") or "").lower()
            if tag_name == "input" and input_type in ("radio", "checkbox"):
                json_marker.check()
            else:
                json_marker.click()
        except Exception:
            json_marker.evaluate("element => element.click()")
        self.log.emit("JSON format selected in the AIS download window.")
        page.wait_for_timeout(800)

        if downloads:
            return

        # Some portal builds put a separate download icon/button in the same
        # JSON row. Search the nearest containers before using the dialog-wide
        # Download/Proceed control.
        started = False
        for level in range(1, 7):
            try:
                container = json_marker.locator(
                    f"xpath=ancestor::*[self::div or self::li or self::tr or self::section][{level}]"
                )
                if not container.count():
                    continue
                controls = container.locator(
                    'button, a, [role="button"], [aria-label*="download" i], [title*="download" i]'
                )
                for index in range(controls.count()):
                    control = controls.nth(index)
                    if not control.is_visible() or not control.is_enabled():
                        continue
                    descriptor = " ".join(filter(None, [
                        control.inner_text(timeout=1_000).strip(),
                        control.get_attribute("aria-label"),
                        control.get_attribute("title"),
                    ])).lower()
                    # In a JSON-specific row an icon-only button is also valid.
                    if "download" in descriptor or controls.count() == 1:
                        control.click()
                        started = True
                        self.log.emit("Activated the download control in the JSON row.")
                        break
                if started:
                    break
            except Exception:
                continue

        if not started and not downloads:
            try:
                action = self._first_visible(scope, [
                    'button:has-text("Download")',
                    '[role="button"]:has-text("Download")',
                    'button:has-text("Proceed")',
                    '[role="button"]:has-text("Proceed")',
                    '[aria-label*="download" i]',
                    '[title*="download" i]',
                ], timeout_ms=12_000)
                action.click()
                started = True
                self.log.emit("Activated the download dialog action for JSON.")
            except Exception as exc:
                raise RuntimeError(
                    "JSON was selected, but its Download/Proceed control was not available."
                ) from exc

        # Confirm that the action produced either a CAPTCHA screen or an
        # immediate download before telling the user to enter CAPTCHA.
        result_deadline = time.monotonic() + 30
        while time.monotonic() < result_deadline:
            self._check_stop()
            if downloads:
                return
            try:
                body_text = page.locator("body").inner_text(timeout=2_000).lower()
                captcha_control = page.locator(
                    'input[formcontrolname*="captcha" i], input[name*="captcha" i], '
                    'input[id*="captcha" i], img[alt*="captcha" i], img[src*="captcha" i]'
                )
                if "captcha" in body_text or (
                    captcha_control.count() and captcha_control.first.is_visible()
                ):
                    self.log.emit("CAPTCHA screen opened after selecting JSON.")
                    return
            except Exception:
                pass
            page.wait_for_timeout(500)

        raise RuntimeError(
            "JSON was selected and its download action was clicked, but the CAPTCHA screen did "
            "not appear."
        )

    def _request_download(self, page):
        downloads = []
        def watch(candidate):
            candidate.on("download", lambda item: downloads.append(item))

        for candidate in page.context.pages:
            watch(candidate)
        page.context.on("page", watch)

        self._status(76, "Clicking Download on Annual Information Statement - Form 168")
        self._click_first(page, [
            'button:has-text("Download")',
            '[role="button"]:has-text("Download")',
            'a:has-text("Download")',
            '[aria-label*="Download AIS" i]',
            'button:has-text("Download AIS/TIS")',
            'text="Download AIS/TIS"',
        ], timeout_ms=30_000)

        self._choose_json_and_start_download(page, downloads)

        if downloads:
            self.log.emit("AIS JSON download started without an additional CAPTCHA prompt.")
            return downloads[-1]

        # The SOP and portal guide show CAPTCHA/manual confirmation at this point.
        # Registering the download listener before the JSON click ensures that both
        # immediate and post-CAPTCHA downloads are captured.
        self.manual_action.emit(
            "The AIS portal may now show a CAPTCHA. Please enter the CAPTCHA in the "
            "browser and click Proceed/Download there. Keep this app open; it will "
            "detect and save the file automatically."
        )
        self._status(88, "Waiting for CAPTCHA confirmation and the portal download")

        deadline = time.monotonic() + 12 * 60
        while time.monotonic() < deadline and not downloads:
            self._check_stop()
            try:
                page.wait_for_timeout(500)
            except Exception:
                # A popup/new tab may be handling the download; pump all pages.
                for candidate in page.context.pages:
                    try:
                        candidate.wait_for_timeout(100)
                    except Exception:
                        pass
            body = ""
            try:
                body = page.locator("body").inner_text(timeout=1_000).lower()
            except Exception:
                pass
            if "activity history" in body and any(
                token in body for token in ("request submitted", "being generated", "in progress")
            ):
                raise RuntimeError(
                    "The portal accepted a large-file generation request. Open Activity History "
                    "after the file becomes available and run the utility again to download it."
                )

        if not downloads:
            raise RuntimeError(
                "No download was received within 12 minutes. Check whether CAPTCHA was submitted "
                "and whether the portal placed the file in Activity History."
            )
        return downloads[-1]

    def _save_and_validate(self, download):
        self._status(94, "Saving and checking the AIS download")
        suggested = safe_filename(download.suggested_filename)
        suffix = Path(suggested).suffix.lower() or ".json"
        if suffix not in (".json", ".zip"):
            suffix = ".json"

        folder = self._work_dir            # temporary: only the Word report is kept in the client folder
        folder.mkdir(parents=True, exist_ok=True)
        filename = f"{self.pan}_FY{self.financial_year}_AIS_{date.today():%Y%m%d}{suffix}"
        target = unique_path(folder / filename)
        download.save_as(str(target))

        if not target.is_file() or target.stat().st_size == 0:
            raise RuntimeError("The portal download was empty or could not be saved.")

        validation_status = "DOWNLOADED"
        if target.suffix.lower() == ".json":
            try:
                with target.open("r", encoding="utf-8-sig") as stream:
                    parsed = json.load(stream)
                if not isinstance(parsed, (dict, list)):
                    raise ValueError("Unexpected JSON root type")
                validation_status = "PLAIN_JSON_VALID"
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                # AIS JSON downloads can be encrypted by the Income-tax portal.
                # Such files intentionally cannot be parsed by json.load() until
                # they are opened/decrypted by the authorised AIS utility.  Keep
                # the file unless it is clearly an HTML/error page returned by
                # the portal instead of a download.
                prefix = target.read_bytes()[:8192].lstrip().lower()
                html_markers = (
                    b"<!doctype html",
                    b"<html",
                    b"<head",
                    b"<body",
                )
                error_markers = (
                    b"permission denied",
                    b"access denied",
                    b"request is not authenticated",
                )
                looks_like_html = any(prefix.startswith(marker) for marker in html_markers)
                html_error = b"<html" in prefix and any(
                    marker in prefix for marker in error_markers
                )
                if looks_like_html or html_error:
                    target.unlink(missing_ok=True)
                    raise RuntimeError(
                        "The portal returned an HTML/error page instead of the AIS file. "
                        "Please keep the browser session open and retry."
                    )

                validation_status = "ENCRYPTED_AIS_JSON_ACCEPTED"
                self.log.emit(
                    "Downloaded .json contains encrypted/non-plain AIS data. "
                    "It will be decrypted locally in the next step."
                )
        else:
            try:
                with zipfile.ZipFile(target) as archive:
                    members = archive.infolist()
                    if not members:
                        raise ValueError("ZIP has no files")
                    # AIS packages may be password-protected. Test every member
                    # that is not encrypted; the encrypted members are still
                    # structurally checked by ZipFile while reading the directory.
                    for member in members:
                        if member.flag_bits & 0x1:
                            continue
                        with archive.open(member) as stream:
                            while stream.read(1024 * 1024):
                                pass
            except Exception as exc:
                target.unlink(missing_ok=True)
                raise RuntimeError(f"Downloaded ZIP validation failed: {exc}") from exc
            validation_status = "ZIP_VALID"

        self.log.emit(f"AIS download validated ({validation_status}).")
        return target

    def _send_report_email(self, attachment_path):
        """Send the Word tax review through Gmail SMTP (designed HTML + plain-text alternative)."""
        self._status(98, f"Emailing the tax review to {self.client_email}")
        summary = self._summary or {}
        kp = {label: value for label, value in (summary.get("kpis") or [])}
        res_label, res_value, res_kind = (summary.get("result") or ["Tax payable / refund", "-", "nil"])
        total_income = kp.get("Tentative total income", "-")
        gross_tax = kp.get("Gross tax", "-")
        paid = kp.get("Taxes paid per AIS", "-")
        regime = kp.get("Better regime", "-")

        message = EmailMessage()
        message["From"] = self.sender_email
        message["To"] = self.client_email
        message["Subject"] = f"Your Preliminary Income Tax Review - FY {self.financial_year}"
        greeting_name = self.client_name or "Client"
        message.set_content(
            f"Dear {greeting_name},\n\n"
            f"Please find attached your preliminary income tax review for Financial Year "
            f"{self.financial_year}, prepared from your Annual Information Statement (AIS).\n\n"
            "KEY FIGURES\n"
            f"  Tentative total income : {total_income}\n"
            f"  Better regime          : {regime}\n"
            f"  Gross tax              : {gross_tax}\n"
            f"  Taxes paid (per AIS)   : {paid}\n"
            f"  {res_label:<22} : {res_value}\n\n"
            "This is a working paper based on AIS data only. It is not a filed return or a tax "
            "opinion and must be reconciled with Form 26AS and your records before filing. "
            "Please contact me if you notice any discrepancy.\n\n"
            "Warm regards,\nCA Jatin Chauhan\nTaxReady - Know your tax before you file\n\n"
            "Confidentiality notice: This email and its attachment are intended only for "
            "the named recipient."
        )
        safe_name = escape(greeting_name)
        safe_fy = escape(self.financial_year)
        safe_file = escape(attachment_path.name)
        banner_bg, banner_fg, banner_edge = {
            "refund": ("#dcfce7", "#166534", "#22c55e"),
            "payable": ("#fee2e2", "#991b1b", "#ef4444"),
        }.get(res_kind, ("#e0e7ff", "#3730a3", "#6366f1"))

        def tile(label, value, colour):
            return (
                f'<td width="50%" style="padding:6px;">'
                f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
                f'style="background:#f8fafc;border:1px solid #e2e8f0;border-left:5px solid {colour};'
                f'border-radius:10px;"><tr><td style="padding:12px 14px;">'
                f'<div style="font-size:11px;letter-spacing:.8px;text-transform:uppercase;color:#64748b;'
                f'font-weight:700;">{escape(label)}</div>'
                f'<div style="font-size:20px;font-weight:800;color:#0f172a;margin-top:3px;">{escape(value)}</div>'
                f'</td></tr></table></td>'
            )
        tiles = (
            f'<tr>{tile("Tentative total income", total_income, "#2563eb")}'
            f'{tile("Better regime", regime, "#7c3aed")}</tr>'
            f'<tr>{tile("Gross tax", gross_tax, "#f97316")}'
            f'{tile("Taxes paid (per AIS)", paid, "#0d9488")}</tr>'
        )
        html_body = f"""\
<!doctype html>
<html>
<body style="margin:0;padding:0;background:#eef2f9;font-family:'Segoe UI',Arial,sans-serif;color:#172033;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
         style="background:#eef2f9;padding:28px 12px;">
    <tr><td align="center">
      <table role="presentation" width="640" cellspacing="0" cellpadding="0"
             style="width:100%;max-width:640px;background:#ffffff;border-radius:18px;
                    overflow:hidden;box-shadow:0 10px 32px rgba(15,23,42,.12);">
        <tr>
          <td style="padding:30px 34px;background-color:#1d4ed8;
                     background-image:linear-gradient(135deg,#1e3a8a 0%,#2563eb 55%,#7c3aed 100%);color:#ffffff;">
            <div style="font-size:12px;letter-spacing:1.6px;text-transform:uppercase;
                        opacity:.9;font-weight:700;">TaxReady &nbsp;|&nbsp; Preliminary Income Tax Review</div>
            <div style="font-size:30px;line-height:38px;font-weight:800;margin-top:6px;">
              Your tax review is ready
            </div>
            <div style="margin-top:12px;">
              <span style="display:inline-block;background:rgba(255,255,255,.18);border-radius:20px;
                           padding:5px 14px;font-size:13px;font-weight:600;">Financial Year {safe_fy}</span>
            </div>
          </td>
        </tr>
        <tr>
          <td style="padding:30px 34px 6px;font-size:15px;line-height:24px;">
            <p style="margin:0 0 14px;">Dear <strong>{safe_name}</strong>,</p>
            <p style="margin:0 0 6px;">
              Please find attached your preliminary income tax review for Financial Year
              <strong>{safe_fy}</strong>, prepared from your Annual Information Statement (AIS).
              Here are the key figures at a glance:
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:6px 28px 0;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">{tiles}</table>
          </td>
        </tr>
        <tr>
          <td style="padding:10px 34px 0;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
                   style="background:{banner_bg};border:1px solid {banner_edge};border-radius:12px;">
              <tr>
                <td style="padding:14px 18px;font-size:13px;font-weight:700;color:{banner_fg};
                           letter-spacing:.6px;text-transform:uppercase;">{escape(res_label)}</td>
                <td align="right" style="padding:14px 18px;font-size:24px;font-weight:800;color:{banner_fg};">
                  {escape(res_value)}</td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding:20px 34px 4px;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
                   style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;">
              <tr>
                <td style="padding:14px 18px;">
                  <div style="font-size:11px;color:#1e40af;text-transform:uppercase;
                              letter-spacing:.8px;font-weight:700;">Attached file</div>
                  <div style="font-size:15px;color:#172033;font-weight:700;margin-top:3px;">
                    &#128206; {safe_file}
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding:14px 34px 6px;">
            <div style="background:#fff7e0;border-left:4px solid #f59e0b;border-radius:6px;
                        padding:12px 14px;font-size:13px;line-height:20px;color:#5b4310;">
              This is a working paper based on AIS data only. It is not a filed return or a tax
              opinion, and it must be reconciled with Form 26AS and your records before filing.
              Please contact me if you notice any discrepancy.
            </div>
          </td>
        </tr>
        <tr>
          <td style="padding:20px 34px 30px;font-size:15px;line-height:23px;">
            <div style="border-top:1px solid #e5e7eb;padding-top:18px;">
              Warm regards,<br>
              <span style="display:inline-block;margin-top:6px;font-size:20px;font-weight:800;
                           color:#1e3a8a;letter-spacing:.2px;">CA Jatin Chauhan</span>
              <div style="width:46px;height:3px;background:#7c3aed;border-radius:2px;margin-top:6px;"></div>
              <div style="font-size:12px;color:#64748b;margin-top:8px;">TaxReady - Know your tax before you file</div>
            </div>
          </td>
        </tr>
        <tr>
          <td style="padding:16px 34px;background:#f8fafc;color:#64748b;font-size:11px;line-height:17px;">
            Confidentiality notice: This email and its attachment are intended only for the named
            recipient. Please notify the sender if received in error.
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
        message.add_alternative(html_body, subtype="html")

        mime_type, _ = mimetypes.guess_type(attachment_path.name)
        if mime_type and "/" in mime_type:
            main_type, sub_type = mime_type.split("/", 1)
        else:
            main_type, sub_type = "application", "octet-stream"
        message.add_attachment(
            attachment_path.read_bytes(),
            maintype=main_type,
            subtype=sub_type,
            filename=attachment_path.name,
        )

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, context=context, timeout=45
        ) as smtp:
            smtp.login(self.sender_email, self.gmail_app_password)
            smtp.send_message(message)
        self.log.emit(f"Tax review email sent successfully to {self.client_email}.")

    # ---- decrypt -> compute -> Word report -------------------------------------------------
    def _read_ais_data(self, target):
        """Return the AIS as a dict: plain JSON as-is, otherwise decrypted locally."""
        dob_digits = re.sub(r"\D", "", self.date_of_birth or self.fallback_dob or "")
        if len(dob_digits) != 8:
            raise RuntimeError(
                "The date of birth could not be read from the portal, so the AIS cannot be decrypted. "
                "Enter the date of birth (DD-MM-YYYY) in the client details and run again."
            )
        if target.suffix.lower() == ".zip":
            with zipfile.ZipFile(target) as archive:
                members = [m for m in archive.infolist() if m.filename.lower().endswith(".json")]
                if not members:
                    raise RuntimeError("The downloaded ZIP does not contain a JSON file.")
                raw = None
                passwords = [None] + [p.encode("utf-8") for p in password_candidates(self.pan, dob_digits)]
                for pwd in passwords:
                    try:
                        raw = archive.read(members[0], pwd=pwd)
                        break
                    except Exception:
                        continue
                if raw is None:
                    raise RuntimeError(
                        "The password-protected ZIP could not be opened with the PAN and date of birth."
                    )
            inner = self._work_dir / "from_zip.json"
            inner.write_bytes(raw)
            target = inner
        try:
            with target.open("r", encoding="utf-8-sig") as stream:
                data = json.load(stream)
            if isinstance(data, dict):
                return data
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            pass
        return decrypt_ais_file(str(target), self.pan, dob_digits)

    def _keep_download(self, target):
        """If decryption or the computation fails, keep the downloaded file so the portal download is not lost."""
        try:
            folder = self.output_root / self.pan / self.financial_year
            folder.mkdir(parents=True, exist_ok=True)
            kept = unique_path(folder / f"{self.pan}_FY{self.financial_year}_AIS_{date.today():%Y%m%d}{target.suffix}")
            shutil.copy2(target, kept)
            return kept
        except Exception:
            return None

    def _decrypt_and_prepare_report(self, target):
        try:
            self._status(95, "Decrypting the AIS file on this computer")
            data = self._read_ais_data(target)
            plain = self._work_dir / "ais_plain.json"
            with plain.open("w", encoding="utf-8") as stream:
                json.dump(data, stream)
            self._status(96, "Computing income and tax (old vs new regime)")
            case = new_case(str(plain))
            ais = case["ais"]
            if ais["pan"] and ais["pan"].upper() != self.pan:
                raise RuntimeError("The downloaded AIS belongs to a different PAN than the one entered.")
            if ais["fy"] and ais["fy"] != self.financial_year:
                raise RuntimeError(
                    f"The downloaded AIS is for FY {ais['fy']}, but FY {self.financial_year} was selected."
                )
            result = compute_case(case)
            self._status(97, "Preparing the Word report")
            report_dir = self._work_dir / "report"
            built = Path(build_report(case, result, str(report_dir)))
            self._case = case
            self._summary = review_summary(case, result)
            folder = self.output_root / self.pan / self.financial_year
            folder.mkdir(parents=True, exist_ok=True)
            final = unique_path(folder / built.name)
            shutil.move(str(built), str(final))
            plain.unlink(missing_ok=True)
            return final
        except InterruptedError:
            raise
        except Exception as exc:
            kept = self._keep_download(target)
            tail = (
                f"\n\nThe downloaded AIS file was kept at:\n{kept}" if kept else ""
            )
            raise RuntimeError(f"The tax review could not be prepared: {exc}{tail}") from exc

    def provide_review_decision(self, accepted, summary=None):
        """Called from the window thread when the user answers the review dialog."""
        if summary:
            self._summary = summary           # figures after the user's edits
        self._review_ok = bool(accepted)
        self._review_event.set()

    def _wait_for_review(self):
        while not self._review_event.wait(0.4):
            self._check_stop()
        return self._review_ok

    def _safe_error_text(self, exc):
        details = str(exc).strip() or exc.__class__.__name__
        if self.password:
            details = details.replace(self.password, "[PASSWORD HIDDEN]")
        if self.gmail_app_password:
            details = details.replace(self.gmail_app_password, "[GMAIL APP PASSWORD HIDDEN]")
        return details

    def _close_browser(self):
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        if self._browser_connection is not None:
            try:
                self._browser_connection.close()
            except Exception:
                pass
            self._browser_connection = None
        if self._browser_process is not None:
            try:
                self._browser_process.terminate()
                self._browser_process.wait(timeout=5)
            except Exception:
                try:
                    self._browser_process.kill()
                except Exception:
                    pass
            self._browser_process = None

    def run(self):
        profile_dir = tempfile.mkdtemp(prefix="ais_browser_")
        self._work_dir = Path(tempfile.mkdtemp(prefix="ais_work_"))
        try:
            with sync_playwright() as playwright:
                self._status(2, "Starting secure browser session")
                self._context = self._launch_browser(playwright, profile_dir)
                page = self._context.pages[0] if self._context.pages else self._context.new_page()
                page = self._login(self._context, page)
                self._capture_date_of_birth(self._context, page)
                ais_page = self._open_ais_portal(self._context, page)
                self._capture_date_of_birth(self._context, ais_page, progress=None)
                self._open_ais_tab_beside_instructions(ais_page)
                self._open_annual_information_statement_form_168(ais_page)
                self._select_financial_year(ais_page)
                download = self._request_download(ais_page)
                target = self._save_and_validate(download)
                self._close_browser()          # the portal session is no longer needed

            # 1) decrypt locally  2) compute tax  3) save only the Word report
            report = self._decrypt_and_prepare_report(target)

            # 4) optional review before the email; 5) otherwise the email goes out automatically
            send = self.email_enabled
            self.email_status = "Not requested"
            if send and self.review_before_email:
                self._status(97, "Waiting for your review of the computation")
                self.review_needed.emit(str(report), self._case)
                send = self._wait_for_review()
                if not send:
                    self.email_status = "Skipped after review"
                    self.log.emit("Email not sent: the computation review was not approved.")
            if send:
                try:
                    self._send_report_email(report)
                    self.email_status = "Sent"
                except Exception as exc:
                    details = self._safe_error_text(exc)
                    self.log.emit("Email technical detail: " + details)
                    self.email_failed.emit(str(report), details)
                    return
            completion = {
                "Sent": "Tax review saved and emailed successfully",
                "Skipped after review": "Tax review saved; email not sent after review",
            }.get(self.email_status, "Tax review saved successfully")
            self._status(100, completion)
            self.finished.emit(str(report))
        except InterruptedError:
            self.stopped.emit()
        except Exception as exc:
            details = self._safe_error_text(exc)
            self.log.emit("Technical detail: " + details)
            self.failed.emit(details)
        finally:
            self.password = ""
            self.gmail_app_password = ""
            self._close_browser()
            shutil.rmtree(profile_dir, ignore_errors=True)
            if self._work_dir is not None:      # downloaded + decrypted AIS never stay on disk
                shutil.rmtree(self._work_dir, ignore_errors=True)


APP_DATA_DIR = Path(os.environ.get("APPDATA") or Path.home()) / "AIS Auto Downloader"
CLIENT_DATABASE_PATH = APP_DATA_DIR / "clients.db"
_KEEP = object()
_DPAPI_ENTROPY = b"AIS Auto Downloader client vault v1"


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _make_data_blob(data):
    buffer = ctypes.create_string_buffer(data, len(data))
    blob = _DataBlob(
        len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))
    )
    return blob, buffer


def _dpapi_call(action, data):
    if os.name != "nt":
        raise RuntimeError("Saved passwords require Windows DPAPI.")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    blob_pointer = ctypes.POINTER(_DataBlob)
    if action == "protect":
        function = crypt32.CryptProtectData
        function.argtypes = [
            blob_pointer,
            wintypes.LPCWSTR,
            blob_pointer,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            blob_pointer,
        ]
    else:
        function = crypt32.CryptUnprotectData
        function.argtypes = [
            blob_pointer,
            ctypes.c_void_p,
            blob_pointer,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            blob_pointer,
        ]
    function.restype = wintypes.BOOL
    input_blob, input_buffer = _make_data_blob(data)
    entropy_blob, entropy_buffer = _make_data_blob(_DPAPI_ENTROPY)
    output_blob = _DataBlob()
    if action == "protect":
        succeeded = function(
            ctypes.byref(input_blob),
            "AIS Auto Downloader",
            ctypes.byref(entropy_blob),
            None,
            None,
            0x1,
            ctypes.byref(output_blob),
        )
    else:
        succeeded = function(
            ctypes.byref(input_blob),
            None,
            ctypes.byref(entropy_blob),
            None,
            None,
            0x1,
            ctypes.byref(output_blob),
        )
    if not succeeded:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(
            ctypes.cast(output_blob.pbData, ctypes.c_void_p), output_blob.cbData
        )
    finally:
        kernel32.LocalFree(ctypes.cast(output_blob.pbData, ctypes.c_void_p))


def protect_password(password):
    return _dpapi_call("protect", password.encode("utf-8"))


def unprotect_password(encrypted):
    return _dpapi_call("unprotect", bytes(encrypted)).decode("utf-8")


def normalize_date_of_birth(value):
    value = str(value or "").strip()
    if not value:
        return ""
    cleaned = re.sub(r"\s+", " ", value.replace(".", "-").replace("/", "-"))
    formats = (
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d %b %Y",
        "%d %B %Y",
    )
    for date_format in formats:
        try:
            parsed = datetime.strptime(cleaned, date_format)
            return parsed.strftime("%d-%m-%Y")
        except ValueError:
            continue
    return ""


class ClientStore:
    """SQLite client register with DPAPI-encrypted passwords and AIS history."""

    def __init__(
        self,
        path=CLIENT_DATABASE_PATH,
        protect=protect_password,
        unprotect=unprotect_password,
    ):
        self.path = Path(path)
        self._protect = protect
        self._unprotect = unprotect
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def _connect(self):
        connection = sqlite3.connect(str(self.path), timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _create_schema(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    pan TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    email TEXT NOT NULL DEFAULT '',
                    download_folder TEXT NOT NULL DEFAULT '',
                    date_of_birth TEXT NOT NULL DEFAULT '',
                    password_enc BLOB,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS activity_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER,
                    client_name TEXT NOT NULL DEFAULT '',
                    pan TEXT NOT NULL,
                    financial_year TEXT NOT NULL,
                    event_time TEXT NOT NULL,
                    file_path TEXT NOT NULL DEFAULT '',
                    download_status TEXT NOT NULL,
                    email_to TEXT NOT NULL DEFAULT '',
                    email_status TEXT NOT NULL DEFAULT '',
                    details TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);
                CREATE INDEX IF NOT EXISTS idx_history_pan ON activity_history(pan);
                CREATE INDEX IF NOT EXISTS idx_history_time ON activity_history(event_time);
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(clients)").fetchall()
            }
            migrations = {
                "email": "ALTER TABLE clients ADD COLUMN email TEXT NOT NULL DEFAULT ''",
                "download_folder": (
                    "ALTER TABLE clients ADD COLUMN download_folder "
                    "TEXT NOT NULL DEFAULT ''"
                ),
                "updated_at": (
                    "ALTER TABLE clients ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''"
                ),
                "date_of_birth": (
                    "ALTER TABLE clients ADD COLUMN date_of_birth "
                    "TEXT NOT NULL DEFAULT ''"
                ),
                "password_enc": "ALTER TABLE clients ADD COLUMN password_enc BLOB",
            }
            for column, sql in migrations.items():
                if column not in columns:
                    connection.execute(sql)
            connection.execute(
                "UPDATE clients SET updated_at = created_at "
                "WHERE updated_at IS NULL OR updated_at = ''"
            )

    @staticmethod
    def _now():
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def list_clients(self, search=""):
        term = search.strip()
        sql = (
            "SELECT id, name, pan, email, download_folder, date_of_birth, "
            "CASE WHEN password_enc IS NULL THEN 0 ELSE 1 END AS has_password, "
            "created_at, updated_at "
            "FROM clients"
        )
        params = ()
        if term:
            sql += " WHERE name LIKE ? OR pan LIKE ? OR email LIKE ?"
            like = f"%{term}%"
            params = (like, like, like)
        sql += " ORDER BY name COLLATE NOCASE, pan"
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(sql, params).fetchall()]

    def get_client(self, client_id):
        if not client_id:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, pan, email, download_folder, date_of_birth, "
                "CASE WHEN password_enc IS NULL THEN 0 ELSE 1 END AS has_password, "
                "created_at, updated_at "
                "FROM clients WHERE id = ?",
                (client_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_client_by_pan(self, pan):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, pan, email, download_folder, date_of_birth, "
                "CASE WHEN password_enc IS NULL THEN 0 ELSE 1 END AS has_password, "
                "created_at, updated_at FROM clients WHERE pan = ? COLLATE NOCASE",
                (pan.strip().upper(),),
            ).fetchone()
        return dict(row) if row else None

    def save_client(
        self,
        name,
        pan,
        email="",
        download_folder="",
        date_of_birth="",
        password=_KEEP,
        client_id=None,
    ):
        now = self._now()
        name = name.strip()
        pan = pan.strip().upper()
        email = email.strip()
        download_folder = download_folder.strip()
        date_of_birth = normalize_date_of_birth(date_of_birth)
        password_enc = (
            self._protect(password) if password is not _KEEP and password else None
        )
        with self._connect() as connection:
            if client_id:
                if password is _KEEP:
                    connection.execute(
                        "UPDATE clients SET name = ?, pan = ?, email = ?, "
                        "download_folder = ?, date_of_birth = ?, updated_at = ? "
                        "WHERE id = ?",
                        (
                            name,
                            pan,
                            email,
                            download_folder,
                            date_of_birth,
                            now,
                            client_id,
                        ),
                    )
                else:
                    connection.execute(
                        "UPDATE clients SET name = ?, pan = ?, email = ?, "
                        "download_folder = ?, date_of_birth = ?, password_enc = ?, "
                        "updated_at = ? WHERE id = ?",
                        (
                            name,
                            pan,
                            email,
                            download_folder,
                            date_of_birth,
                            password_enc,
                            now,
                            client_id,
                        ),
                    )
                return int(client_id)
            cursor = connection.execute(
                "INSERT INTO clients "
                "(name, pan, email, download_folder, date_of_birth, password_enc, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    pan,
                    email,
                    download_folder,
                    date_of_birth,
                    password_enc,
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def upsert_client(
        self,
        name,
        pan,
        email="",
        download_folder="",
        date_of_birth="",
        password=_KEEP,
    ):
        existing = None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM clients WHERE pan = ? COLLATE NOCASE", (pan.strip(),)
            ).fetchone()
            existing = int(row["id"]) if row else None
        return self.save_client(
            name,
            pan,
            email,
            download_folder,
            date_of_birth,
            password,
            existing,
        )

    def load_password(self, client_id):
        if not client_id:
            return ""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT password_enc FROM clients WHERE id = ?", (client_id,)
            ).fetchone()
        if not row or row["password_enc"] is None:
            return ""
        return self._unprotect(row["password_enc"])

    def update_date_of_birth(self, client_id, date_of_birth):
        normalized = normalize_date_of_birth(date_of_birth)
        if not client_id or not normalized:
            return
        with self._connect() as connection:
            connection.execute(
                "UPDATE clients SET date_of_birth = ?, updated_at = ? WHERE id = ?",
                (normalized, self._now(), client_id),
            )

    def delete_client(self, client_id):
        with self._connect() as connection:
            connection.execute("DELETE FROM clients WHERE id = ?", (client_id,))

    def add_history(
        self,
        client_id,
        client_name,
        pan,
        financial_year,
        file_path,
        download_status,
        email_to="",
        email_status="",
        details="",
    ):
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO activity_history "
                "(client_id, client_name, pan, financial_year, event_time, file_path, "
                "download_status, email_to, email_status, details) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    client_id,
                    client_name.strip(),
                    pan.strip().upper(),
                    financial_year.strip(),
                    self._now(),
                    str(file_path or ""),
                    download_status,
                    email_to.strip(),
                    email_status,
                    str(details or "")[:2000],
                ),
            )

    def list_history(self, limit=500):
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT event_time, client_name, pan, financial_year, download_status, "
                "email_to, email_status, file_path, details "
                "FROM activity_history ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in rows]

    def clear_history(self):
        """Delete every activity-history record (clients and files are not touched)."""
        with self._connect() as connection:
            connection.execute("DELETE FROM activity_history")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.worker = None
        self.gmail_connected_email = ""
        self._gmail_app_password = ""
        self._last_progress = 0
        self._active_run = None
        self._selected_client_id = None
        self._batch = None                 # state of a multi-client run (None when idle)
        self._batch_checked = set()        # client ids ticked on the Batch tab
        self.client_store = ClientStore()
        self._settings = QSettings("AIS Automation", SETTINGS_APP_NAME)
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setMinimumSize(1120, 640)
        self.resize(1180, 720)
        self._build_ui()
        self._restore_gmail_settings()
        saved_theme = self._settings.value("theme", "Light", type=str)
        if saved_theme not in THEMES:
            saved_theme = "Light"
        self.theme_combo.setCurrentText(saved_theme)
        self._apply_theme(saved_theme)
        self._set_status_badge("READY", "ready")
        self._update_workflow(0)
        self._refresh_client_list()

    def _build_ui(self):
        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        side_panel = QFrame(objectName="sidePanel")
        side_panel.setFixedWidth(320)
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(24, 26, 24, 22)
        side_layout.setSpacing(18)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(12)
        logo = QFrame(objectName="logoBadge")
        logo.setFixedSize(44, 44)
        logo_layout = QVBoxLayout(logo)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_text = QLabel("TR", objectName="logoText")
        logo_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(logo_text)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        brand_title = QLabel("TaxReady", objectName="sideTitle")
        brand_title.setWordWrap(True)
        brand_tag = QLabel(APP_TAGLINE + "\nBy CA Jatin Chauhan", objectName="sideTag")
        brand_tag.setWordWrap(True)
        brand_text.addWidget(brand_title)
        brand_text.addWidget(brand_tag)
        brand_row.addWidget(logo)
        brand_row.addLayout(brand_text, 1)
        side_layout.addLayout(brand_row)

        side_layout.addWidget(QLabel("WORKFLOW", objectName="workflowHeading"))
        workflow_specs = [
            (2, "Secure browser", "Protected Chrome or Edge session"),
            (8, "Portal sign-in", "PAN and e-Filing authentication"),
            (48, "AIS Compliance Portal", "Open the AIS service securely"),
            (63, "Form 168 and F.Y.", "Choose statement and financial year"),
            (76, "JSON and CAPTCHA", "Request JSON and complete CAPTCHA"),
            (94, "Save and validate", "Verify the AIS download"),
            (95, "Decrypt AIS", "Decrypt locally on this computer"),
            (96, "Tax computation", "Income, tax, old vs new regime"),
            (98, "Report and email", "Word report; email after review"),
        ]
        self.workflow_steps = []
        steps_host = QWidget(objectName="stepHost")
        steps_layout = QVBoxLayout(steps_host)
        steps_layout.setContentsMargins(0, 0, 4, 0)
        steps_layout.setSpacing(6)
        for number, (threshold, title, subtitle) in enumerate(workflow_specs, 1):
            row = StepRow(number, title, subtitle)
            self.workflow_steps.append((threshold, row))
            steps_layout.addWidget(row)
        steps_layout.addStretch(1)
        steps_scroll = QScrollArea(objectName="stepScroll")
        steps_scroll.setWidgetResizable(True)
        steps_scroll.setFrameShape(QFrame.Shape.NoFrame)
        steps_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        steps_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;} QWidget#stepHost{background:transparent;}")
        steps_scroll.viewport().setStyleSheet("background:transparent;")
        steps_scroll.setWidget(steps_host)
        side_layout.addWidget(steps_scroll, 1)
        privacy = QFrame(objectName="privacyCard")
        privacy_layout = QVBoxLayout(privacy)
        privacy_layout.setContentsMargins(14, 12, 14, 12)
        privacy_layout.setSpacing(5)
        privacy.setMinimumHeight(96)
        privacy_layout.addWidget(QLabel("Privacy first", objectName="privacyTitle"))
        privacy_text = QLabel(
            "Saved passwords use Windows account encryption. CAPTCHA and portal "
            "security checks are never bypassed.",
            objectName="privacyText",
        )
        privacy_text.setWordWrap(True)
        privacy_layout.addWidget(privacy_text)
        side_layout.addWidget(privacy)
        side_layout.addWidget(QLabel(f"Version {APP_VERSION}", objectName="versionLabel"))
        root_layout.addWidget(side_panel)

        scroll = QScrollArea(objectName="mainScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget(objectName="mainContent")
        content.setMinimumWidth(640)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 28, 40, 24)
        content_layout.setSpacing(18)

        header = QHBoxLayout()
        header.setSpacing(20)
        header_text = QVBoxLayout()
        header_text.setSpacing(4)
        page_title = QLabel("TaxReady", objectName="pageTitle")
        page_title.setWordWrap(True)
        header_text.addWidget(page_title)
        page_subtitle = QLabel(
            APP_TAGLINE + "  |  AIS download → decrypt → tax computation → Word report → email",
            objectName="pageSubtitle",
        )
        page_subtitle.setWordWrap(True)
        header_text.addWidget(page_subtitle)
        header.addLayout(header_text, 1)
        theme_block = QVBoxLayout()
        theme_block.setSpacing(4)
        theme_block.addWidget(QLabel("Theme", objectName="smallLabel"))
        self.theme_combo = QComboBox(objectName="themeCombo")
        self.theme_combo.addItems(list(THEMES))
        self.theme_combo.setFixedHeight(34)
        self.theme_combo.setMinimumWidth(150)
        self.theme_combo.currentTextChanged.connect(self._change_theme)
        theme_block.addWidget(self.theme_combo)
        header.addLayout(theme_block)
        self.status_badge = QLabel("READY", objectName="statusPill")
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setFixedHeight(30)
        self.status_badge.setMinimumWidth(132)
        header.addWidget(self.status_badge, 0, Qt.AlignmentFlag.AlignBottom)
        content_layout.addLayout(header)

        self.client_card = QFrame(objectName="clientCard")
        self.client_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        client_layout = QVBoxLayout(self.client_card)
        client_layout.setContentsMargins(24, 20, 24, 20)
        client_layout.setSpacing(12)
        client_heading = QHBoxLayout()
        client_title_block = QVBoxLayout()
        client_title_block.setSpacing(2)
        client_title_block.addWidget(QLabel("Client database", objectName="cardTitle"))
        client_title_block.addWidget(
            QLabel(
                "Reuse client details and a Windows-encrypted e-Filing password.",
                objectName="cardCaption",
            )
        )
        client_heading.addLayout(client_title_block, 1)
        self.history_button = QPushButton("Activity history", objectName="ghostButton")
        self.history_button.setFixedHeight(40)
        self.history_button.clicked.connect(self._show_history)
        client_heading.addWidget(self.history_button)
        client_layout.addLayout(client_heading)

        client_grid = QGridLayout()
        client_grid.setHorizontalSpacing(12)
        client_grid.setVerticalSpacing(8)
        client_grid.setColumnStretch(0, 2)
        client_grid.setColumnStretch(1, 2)
        client_grid.setColumnStretch(2, 3)
        client_grid.addWidget(QLabel("Client name", objectName="fieldLabel"), 0, 0)
        client_grid.addWidget(QLabel("Find saved client", objectName="fieldLabel"), 0, 1)
        client_grid.addWidget(QLabel("Saved clients", objectName="fieldLabel"), 0, 2)
        self.client_name_input = QLineEdit()
        self.client_name_input.setPlaceholderText("Client / taxpayer name")
        self.client_name_input.setFixedHeight(44)
        client_grid.addWidget(self.client_name_input, 1, 0)
        self.client_search_input = QLineEdit()
        self.client_search_input.setPlaceholderText("Search name, PAN or email")
        self.client_search_input.setFixedHeight(44)
        self.client_search_input.textChanged.connect(self._refresh_client_list)
        client_grid.addWidget(self.client_search_input, 1, 1)
        self.client_combo = QComboBox()
        self.client_combo.setFixedHeight(44)
        self.client_combo.currentIndexChanged.connect(self._load_selected_client)
        client_grid.addWidget(self.client_combo, 1, 2)
        client_grid.addWidget(
            QLabel("Date of Birth", objectName="fieldLabel"), 2, 0
        )
        self.date_of_birth_input = QLineEdit()
        self.date_of_birth_input.setPlaceholderText("DD-MM-YYYY (captured after login)")
        self.date_of_birth_input.setFixedHeight(44)
        client_grid.addWidget(self.date_of_birth_input, 3, 0)
        password_security_hint = QLabel(
            "The password is stored only as Windows DPAPI-encrypted data and is not "
            "included in CSV exports.",
            objectName="inlineHint",
        )
        password_security_hint.setWordWrap(True)
        client_grid.addWidget(password_security_hint, 3, 1, 1, 2)
        client_layout.addLayout(client_grid)

        client_actions = QHBoxLayout()
        client_actions.setSpacing(8)
        for text, name, handler in (
            ("New", "ghostButton", self._new_client),
            ("Save client", "secondaryButton", self._save_client),
            ("Delete", "dangerSoftButton", self._delete_client),
            ("Import CSV", "ghostButton", self._import_clients_csv),
            ("Export CSV", "ghostButton", self._export_clients_csv),
        ):
            button = QPushButton(text, objectName=name)
            button.setFixedHeight(40)
            button.clicked.connect(handler)
            client_actions.addWidget(button)
        client_actions.addStretch(1)
        self.database_path_label = QLabel(
            "Database: clients.db (local)", objectName="inlineHint"
        )
        self.database_path_label.setToolTip(str(self.client_store.path))
        client_actions.addWidget(self.database_path_label)
        client_layout.addLayout(client_actions)
        content_layout.addWidget(self.client_card)

        self.form_card = QFrame(objectName="formCard")
        self.form_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        form_layout = QVBoxLayout(self.form_card)
        form_layout.setContentsMargins(24, 22, 24, 22)
        form_layout.setSpacing(16)
        form_layout.addWidget(QLabel("Taxpayer details", objectName="cardTitle"))
        form_layout.addWidget(
            QLabel(
                "Enter the taxpayer and download information below.",
                objectName="cardCaption",
            )
        )
        details_grid = QGridLayout()
        details_grid.setHorizontalSpacing(18)
        details_grid.setVerticalSpacing(14)
        details_grid.setColumnStretch(0, 1)
        details_grid.setColumnStretch(1, 1)

        pan_block = QWidget()
        pan_layout = QVBoxLayout(pan_block)
        pan_layout.setContentsMargins(0, 0, 0, 0)
        pan_layout.setSpacing(6)
        pan_layout.addWidget(QLabel("PAN / User ID", objectName="fieldLabel"))
        self.pan_input = QLineEdit()
        self.pan_input.setPlaceholderText("ABCDE1234F")
        self.pan_input.setMaxLength(10)
        self.pan_input.setFixedHeight(44)
        self.pan_input.textChanged.connect(
            lambda value: self.pan_input.setText(value.upper())
            if value != value.upper()
            else None
        )
        pan_layout.addWidget(self.pan_input)
        details_grid.addWidget(pan_block, 0, 0)

        password_block = QWidget()
        password_layout = QVBoxLayout(password_block)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(6)
        password_layout.addWidget(QLabel("e-Filing password", objectName="fieldLabel"))
        password_row = QHBoxLayout()
        password_row.setSpacing(8)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Saved securely when you click Save client")
        self.password_input.setFixedHeight(44)
        self.show_password = QPushButton("Show", objectName="ghostButton")
        self.show_password.setCheckable(True)
        self.show_password.setFixedSize(78, 44)
        self.show_password.toggled.connect(self._toggle_password)
        password_row.addWidget(self.password_input, 1)
        password_row.addWidget(self.show_password)
        password_layout.addLayout(password_row)
        details_grid.addWidget(password_block, 0, 1)

        fy_block = QWidget()
        fy_layout = QVBoxLayout(fy_block)
        fy_layout.setContentsMargins(0, 0, 0, 0)
        fy_layout.setSpacing(6)
        fy_layout.addWidget(QLabel("Financial Year", objectName="fieldLabel"))
        self.fy_combo = QComboBox()
        current_start = (
            date.today().year if date.today().month >= 4 else date.today().year - 1
        )
        years = [
            f"{year}-{(year + 1) % 100:02d}"
            for year in range(current_start, 2017, -1)
        ]
        self.fy_combo.addItems(years)
        self.fy_combo.setFixedHeight(44)
        fy_layout.addWidget(self.fy_combo)
        details_grid.addWidget(fy_block, 1, 0)

        folder_block = QWidget()
        folder_layout = QVBoxLayout(folder_block)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(6)
        folder_layout.addWidget(QLabel("Download folder", objectName="fieldLabel"))
        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self.folder_input = QLineEdit(
            str(Path.home() / "Documents" / "AIS_Downloads")
        )
        self.folder_input.setFixedHeight(44)
        self.folder_input.setCursorPosition(0)
        self.folder_browse_button = QPushButton("Browse", objectName="secondaryButton")
        self.folder_browse_button.setFixedSize(92, 44)
        self.folder_browse_button.clicked.connect(self._choose_folder)
        folder_row.addWidget(self.folder_input, 1)
        folder_row.addWidget(self.folder_browse_button)
        folder_layout.addLayout(folder_row)
        details_grid.addWidget(folder_block, 1, 1)

        dob_block = QWidget()
        dob_layout = QVBoxLayout(dob_block)
        dob_layout.setContentsMargins(0, 0, 0, 0)
        dob_layout.setSpacing(6)
        dob_layout.addWidget(QLabel("Date of birth (DD-MM-YYYY)", objectName="fieldLabel"))
        self.dob_input = QLineEdit()
        self.dob_input.setPlaceholderText("e.g. 15-06-1990 - needed to decrypt the AIS")
        self.dob_input.setMaxLength(12)
        self.dob_input.setFixedHeight(44)
        dob_layout.addWidget(self.dob_input)
        details_grid.addWidget(dob_block, 2, 0)
        dob_hint = QLabel(
            "Type it here when the client is not saved. If left blank, the app tries to read it "
            "from the portal after login.",
            objectName="inlineHint",
        )
        dob_hint.setWordWrap(True)
        details_grid.addWidget(dob_hint, 2, 1, Qt.AlignmentFlag.AlignBottom)
        # keep this box and the one in the client database in step
        self.dob_input.textChanged.connect(
            lambda text: self._mirror_text(self.dob_input, self.date_of_birth_input)
        )
        self.date_of_birth_input.textChanged.connect(
            lambda text: self._mirror_text(self.date_of_birth_input, self.dob_input)
        )
        form_layout.addLayout(details_grid)

        email_panel = QFrame(objectName="emailPanel")
        email_layout = QVBoxLayout(email_panel)
        email_layout.setContentsMargins(16, 14, 16, 14)
        email_layout.setSpacing(10)
        email_top = QHBoxLayout()
        self.email_enabled = QCheckBox(
            "Email the Word tax review to the client through Gmail"
        )
        self.email_enabled.setChecked(True)
        email_top.addWidget(self.email_enabled)
        email_top.addStretch(1)
        self.gmail_connection_status = QLabel(
            "Gmail status: Not configured", objectName="gmailStatus"
        )
        email_top.addWidget(self.gmail_connection_status)
        email_layout.addLayout(email_top)
        self.review_before_email = QCheckBox(
            "Let me review and edit the computation before the email is sent "
            "(untick to send automatically)"
        )
        self.review_before_email.setChecked(True)
        email_layout.addWidget(self.review_before_email)
        email_grid = QGridLayout()
        email_grid.setHorizontalSpacing(18)
        email_grid.setVerticalSpacing(6)
        email_grid.setColumnStretch(0, 1)
        email_grid.setColumnStretch(1, 0)
        email_grid.addWidget(QLabel("Client email ID", objectName="fieldLabel"), 0, 0)
        email_grid.addWidget(QLabel("Gmail connection", objectName="fieldLabel"), 0, 1)
        self.client_email_input = QLineEdit()
        self.client_email_input.setPlaceholderText("client@example.com")
        self.client_email_input.setFixedHeight(44)
        email_grid.addWidget(self.client_email_input, 1, 0)
        self.open_gmail_settings_button = QPushButton(
            "Open Gmail Settings", objectName="ghostButton"
        )
        self.open_gmail_settings_button.setFixedHeight(44)
        self.open_gmail_settings_button.clicked.connect(
            lambda: self.main_tabs.setCurrentWidget(self.gmail_settings_scroll)
        )
        email_grid.addWidget(self.open_gmail_settings_button, 1, 1)
        email_layout.addLayout(email_grid)
        gmail_hint = QLabel(
            "Configure the sender Gmail and 16-character App Password once in the "
            "Gmail Settings tab.",
            objectName="inlineHint",
        )
        gmail_hint.setWordWrap(True)
        email_layout.addWidget(gmail_hint)
        form_layout.addWidget(email_panel)
        self.email_enabled.toggled.connect(self.client_email_input.setEnabled)
        self.email_enabled.toggled.connect(self.review_before_email.setEnabled)

        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        self.start_button = QPushButton(
            "Download AIS && Prepare Tax Review", objectName="primaryButton"
        )
        self.start_button.setFixedHeight(50)
        self.start_button.clicked.connect(self._start)
        self.stop_button = QPushButton("Stop", objectName="dangerButton")
        self.stop_button.setFixedSize(110, 50)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._stop)
        action_row.addWidget(self.start_button, 1)
        action_row.addWidget(self.stop_button)
        form_layout.addLayout(action_row)
        content_layout.addWidget(self.form_card)

        self.progress_card = QFrame(objectName="progressCard")
        self.progress_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        progress_layout = QVBoxLayout(self.progress_card)
        progress_layout.setContentsMargins(22, 18, 22, 18)
        progress_layout.setSpacing(8)
        progress_layout.addWidget(QLabel("CURRENT STAGE", objectName="stageCaption"))
        self.status_label = QLabel("Ready to start", objectName="statusLabel")
        self.status_label.setWordWrap(True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ready")
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(18)
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)
        content_layout.addWidget(self.progress_card)

        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("Activity log", objectName="sectionTitle"))
        log_header.addStretch(1)
        log_header.addWidget(
            QLabel("Passwords are never written here", objectName="activityHint")
        )
        content_layout.addLayout(log_header)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText(
            "Progress messages will appear here. Passwords are never logged."
        )
        self.log_box.setMinimumHeight(150)
        self.log_box.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        content_layout.addWidget(self.log_box, 1)
        footer = QLabel(
            "Uses the official Income-tax portal. Portal layouts can change; this utility uses "
            "multiple safe fallbacks and reports the exact stage if navigation changes.",
            objectName="footer",
        )
        footer.setWordWrap(True)
        content_layout.addWidget(footer)
        scroll.setWidget(content)

        self.gmail_settings_scroll = QScrollArea(objectName="mainScroll")
        self.gmail_settings_scroll.setWidgetResizable(True)
        self.gmail_settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.gmail_settings_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        gmail_content = QWidget(objectName="mainContent")
        gmail_content.setMinimumWidth(640)
        gmail_page_layout = QVBoxLayout(gmail_content)
        gmail_page_layout.setContentsMargins(40, 28, 40, 24)
        gmail_page_layout.setSpacing(18)
        gmail_page_layout.addWidget(QLabel("Gmail Settings", objectName="pageTitle"))
        gmail_subtitle = QLabel(
            "Configure the sender account once using a Google App Password.",
            objectName="pageSubtitle",
        )
        gmail_subtitle.setWordWrap(True)
        gmail_page_layout.addWidget(gmail_subtitle)

        self.gmail_settings_card = QFrame(objectName="formCard")
        self.gmail_settings_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        gmail_card_layout = QVBoxLayout(self.gmail_settings_card)
        gmail_card_layout.setContentsMargins(24, 22, 24, 22)
        gmail_card_layout.setSpacing(16)
        gmail_card_layout.addWidget(
            QLabel("Sender Gmail connection", objectName="cardTitle")
        )
        gmail_card_caption = QLabel(
            "The App Password is encrypted with Windows DPAPI and is never written "
            "to logs, client records or CSV exports.",
            objectName="cardCaption",
        )
        gmail_card_caption.setWordWrap(True)
        gmail_card_layout.addWidget(gmail_card_caption)
        gmail_grid = QGridLayout()
        gmail_grid.setHorizontalSpacing(16)
        gmail_grid.setVerticalSpacing(8)
        gmail_grid.setColumnStretch(0, 1)
        gmail_grid.setColumnStretch(1, 1)
        gmail_grid.addWidget(QLabel("Sender Gmail ID", objectName="fieldLabel"), 0, 0)
        gmail_grid.addWidget(
            QLabel("16-character Google App Password", objectName="fieldLabel"),
            0,
            1,
        )
        self.gmail_sender_input = QLineEdit()
        self.gmail_sender_input.setPlaceholderText("youraccount@gmail.com")
        self.gmail_sender_input.setFixedHeight(44)
        gmail_grid.addWidget(self.gmail_sender_input, 1, 0)
        gmail_password_row = QHBoxLayout()
        gmail_password_row.setSpacing(8)
        self.gmail_app_password_input = QLineEdit()
        self.gmail_app_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gmail_app_password_input.setPlaceholderText(
            "Enter once, or leave blank to use the saved password"
        )
        self.gmail_app_password_input.setFixedHeight(44)
        self.show_gmail_password = QPushButton("Show", objectName="ghostButton")
        self.show_gmail_password.setCheckable(True)
        self.show_gmail_password.setFixedSize(78, 44)
        self.show_gmail_password.toggled.connect(self._toggle_gmail_password)
        gmail_password_row.addWidget(self.gmail_app_password_input, 1)
        gmail_password_row.addWidget(self.show_gmail_password)
        gmail_grid.addLayout(gmail_password_row, 1, 1)
        gmail_card_layout.addLayout(gmail_grid)

        gmail_action_row = QHBoxLayout()
        gmail_action_row.setSpacing(10)
        self.gmail_connect_button = QPushButton(
            "Save && Verify Gmail", objectName="primaryButton"
        )
        self.gmail_connect_button.setFixedHeight(50)
        self.gmail_connect_button.clicked.connect(self._connect_gmail)
        self.gmail_clear_button = QPushButton(
            "Remove saved connection", objectName="dangerSoftButton"
        )
        self.gmail_clear_button.setFixedHeight(50)
        self.gmail_clear_button.clicked.connect(self._clear_gmail_settings)
        gmail_action_row.addWidget(self.gmail_connect_button, 1)
        gmail_action_row.addWidget(self.gmail_clear_button)
        gmail_card_layout.addLayout(gmail_action_row)
        self.gmail_tab_status = QLabel(
            "Gmail is not configured.", objectName="gmailStatus"
        )
        self.gmail_tab_status.setWordWrap(True)
        gmail_card_layout.addWidget(self.gmail_tab_status)
        gmail_page_layout.addWidget(self.gmail_settings_card)

        gmail_help = QFrame(objectName="emailPanel")
        gmail_help_layout = QVBoxLayout(gmail_help)
        gmail_help_layout.setContentsMargins(18, 16, 18, 16)
        gmail_help_layout.setSpacing(7)
        gmail_help_layout.addWidget(
            QLabel("How this connection works", objectName="cardTitle")
        )
        help_text = QLabel(
            "1. Enter the Gmail address that will send the tax review.\n"
            "2. Enter the 16-character Google App Password without spaces.\n"
            "3. Click Save & Verify Gmail.\n"
            "4. Future emails will use the saved encrypted connection automatically.\n\n"
            "The normal Gmail account password is not required.",
            objectName="cardCaption",
        )
        help_text.setWordWrap(True)
        gmail_help_layout.addWidget(help_text)
        gmail_page_layout.addWidget(gmail_help)
        gmail_page_layout.addStretch(1)
        self.gmail_settings_scroll.setWidget(gmail_content)

        self.main_tabs = QTabWidget(objectName="mainTabs")
        self.main_tabs.addTab(scroll, "Single Client")
        self.main_tabs.addTab(self._build_batch_tab(), "Batch - multiple clients")
        self.main_tabs.addTab(self.gmail_settings_scroll, "Gmail Settings")
        self.main_tabs.addTab(self._build_about_tab(), "About && Help")
        self.main_tabs.currentChanged.connect(self._on_main_tab_changed)
        root_layout.addWidget(self.main_tabs, 1)
        self._add_shadow(self.client_card)
        self._add_shadow(self.form_card)
        self._add_shadow(self.progress_card)
        self._add_shadow(self.gmail_settings_card)

    # ------------------------------------------------------------------ batch (multiple clients)
    def _build_batch_tab(self):
        self.batch_page = QScrollArea(objectName="mainScroll")
        self.batch_page.setWidgetResizable(True)
        self.batch_page.setFrameShape(QFrame.Shape.NoFrame)
        self.batch_page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget(objectName="mainContent")
        content.setMinimumWidth(640)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 28, 40, 24)
        layout.setSpacing(16)
        layout.addWidget(QLabel("Batch run - several clients", objectName="pageTitle"))
        caption = QLabel(
            "Tick the saved clients below. The app downloads each AIS, prepares the tax review and emails it, "
            "one client after another, using each client's saved password, email and folder. You complete the "
            "CAPTCHA in the browser for every client.",
            objectName="pageSubtitle",
        )
        caption.setWordWrap(True)
        layout.addWidget(caption)

        pick = QFrame(objectName="formCard")
        pick_layout = QVBoxLayout(pick)
        pick_layout.setContentsMargins(24, 20, 24, 20)
        pick_layout.setSpacing(12)
        pick_layout.addWidget(QLabel("1. Choose the clients", objectName="cardTitle"))
        options = QHBoxLayout()
        options.setSpacing(18)
        fy_box = QVBoxLayout()
        fy_box.setSpacing(4)
        fy_box.addWidget(QLabel("Financial Year (same for all)", objectName="fieldLabel"))
        self.batch_fy = QComboBox()
        for index in range(self.fy_combo.count()):
            self.batch_fy.addItem(self.fy_combo.itemText(index))
        self.batch_fy.setCurrentText(self.fy_combo.currentText())
        self.batch_fy.setFixedHeight(40)
        self.batch_fy.setMinimumWidth(130)
        fy_box.addWidget(self.batch_fy)
        options.addLayout(fy_box)
        checks = QVBoxLayout()
        checks.setSpacing(6)
        self.batch_email = QCheckBox("Email each client's Word tax review (to the email saved for that client)")
        self.batch_email.setChecked(True)
        self.batch_review = QCheckBox("Let me review and edit each computation before its email is sent")
        self.batch_review.setChecked(True)
        self.batch_continue = QCheckBox("Carry on with the next client if one fails")
        self.batch_continue.setChecked(True)
        self.batch_email.toggled.connect(self.batch_review.setEnabled)
        for box in (self.batch_email, self.batch_review, self.batch_continue):
            checks.addWidget(box)
        options.addLayout(checks, 1)
        pick_layout.addLayout(options)

        tools = QHBoxLayout()
        tools.setSpacing(8)
        self.batch_search = QLineEdit()
        self.batch_search.setPlaceholderText("Search name, PAN or email")
        self.batch_search.setFixedHeight(40)
        self.batch_search.textChanged.connect(lambda _text: self._batch_refresh_clients())
        select_all = QPushButton("Select all", objectName="secondaryButton")
        select_none = QPushButton("Clear selection", objectName="ghostButton")
        for button in (select_all, select_none):
            button.setFixedHeight(40)
        select_all.clicked.connect(lambda: self._batch_set_all(True))
        select_none.clicked.connect(lambda: self._batch_set_all(False))
        self.batch_count = QLabel("0 client(s) selected", objectName="gmailStatus")
        tools.addWidget(self.batch_search, 1)
        tools.addWidget(select_all)
        tools.addWidget(select_none)
        tools.addWidget(self.batch_count)
        pick_layout.addLayout(tools)

        self.batch_table = QTableWidget(0, 6)
        self.batch_table.setHorizontalHeaderLabels(["", "Client", "PAN", "Email", "Password", "Date of birth"])
        self.batch_table.verticalHeader().setVisible(False)
        self.batch_table.setAlternatingRowColors(True)
        self.batch_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.batch_table.setMinimumHeight(260)
        self.batch_table.horizontalHeader().setStretchLastSection(True)
        self.batch_table.itemChanged.connect(self._batch_item_changed)
        pick_layout.addWidget(self.batch_table)
        hint = QLabel(
            "Clients without a saved password cannot be tick-selected. Add the password in the Single Client tab "
            "(Save client).",
            objectName="inlineHint",
        )
        hint.setWordWrap(True)
        pick_layout.addWidget(hint)
        layout.addWidget(pick)

        run = QFrame(objectName="formCard")
        run_layout = QVBoxLayout(run)
        run_layout.setContentsMargins(24, 20, 24, 20)
        run_layout.setSpacing(12)
        run_layout.addWidget(QLabel("2. Run and results", objectName="cardTitle"))
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.batch_start = QPushButton("Start batch", objectName="primaryButton")
        self.batch_start.setFixedHeight(46)
        self.batch_start.clicked.connect(self._batch_start_clicked)
        self.batch_stop = QPushButton("Stop", objectName="dangerButton")
        self.batch_stop.setFixedSize(110, 46)
        self.batch_stop.setEnabled(False)
        self.batch_stop.clicked.connect(self._stop)
        buttons.addWidget(self.batch_start, 1)
        buttons.addWidget(self.batch_stop)
        run_layout.addLayout(buttons)
        self.batch_status = QLabel("Idle. Tick clients and click Start batch.", objectName="inlineHint")
        self.batch_status.setWordWrap(True)
        run_layout.addWidget(self.batch_status)
        self.batch_progress = QProgressBar()
        self.batch_progress.setFixedHeight(18)
        self.batch_progress.setRange(0, 100)
        run_layout.addWidget(self.batch_progress)
        self.batch_results = QTableWidget(0, 5)
        self.batch_results.setHorizontalHeaderLabels(["Client", "PAN", "Result", "Email", "Report / note"])
        self.batch_results.verticalHeader().setVisible(False)
        self.batch_results.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.batch_results.setMinimumHeight(200)
        self.batch_results.horizontalHeader().setStretchLastSection(True)
        run_layout.addWidget(self.batch_results)
        layout.addWidget(run)
        layout.addStretch(1)
        self.batch_page.setWidget(content)
        self._batch_refresh_clients()
        return self.batch_page

    def _build_about_tab(self):
        page = QScrollArea(objectName="mainScroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.Shape.NoFrame)
        page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget(objectName="mainContent")
        content.setMinimumWidth(640)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 28, 40, 24)
        layout.setSpacing(16)
        layout.addWidget(QLabel("TaxReady", objectName="pageTitle"))
        sub = QLabel(f"{APP_TAGLINE}   |   Version {APP_VERSION}   |   By CA Jatin Chauhan", objectName="pageSubtitle")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        card = QFrame(objectName="formCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(10)
        card_layout.addWidget(QLabel("What TaxReady does", objectName="cardTitle"))
        what = QLabel(
            "TaxReady gives your client an early estimate of the tax payable, so the client is ready for the "
            "payment and has time to arrange the funds.\n\n"
            "1.  Downloads the client's AIS from the Income Tax portal (you complete the CAPTCHA).\n"
            "2.  Decrypts it on this computer.\n"
            "3.  Computes the tax - old and new regime - and prepares a Word report.\n"
            "4.  Lets you review and edit the figures.\n"
            "5.  Emails the Word report to the client through Gmail.",
            objectName="cardCaption",
        )
        what.setWordWrap(True)
        card_layout.addWidget(what)
        layout.addWidget(card)

        start = QFrame(objectName="formCard")
        start_layout = QVBoxLayout(start)
        start_layout.setContentsMargins(24, 20, 24, 20)
        start_layout.setSpacing(10)
        start_layout.addWidget(QLabel("Quick start", objectName="cardTitle"))
        steps = QLabel(
            "1.  Gmail Settings tab: enter your Gmail address and a Google App Password, then Save & Verify Gmail "
            "(only needed for emailing).\n"
            "2.  Single Client tab: enter the client's name, PAN, e-Filing password, date of birth and email, "
            "then Save client.\n"
            "3.  Choose the Financial Year and the folder, then click Download AIS & Prepare Tax Review.\n"
            "4.  Complete the CAPTCHA in the browser window that opens.\n"
            "5.  Check the figures in the review window, then Send email.\n\n"
            "For many clients use the Batch - multiple clients tab.",
            objectName="cardCaption",
        )
        steps.setWordWrap(True)
        start_layout.addWidget(steps)
        manual = QPushButton("Open the user manual", objectName="primaryButton")
        manual.setFixedHeight(46)
        manual.clicked.connect(self._open_manual)
        start_layout.addWidget(manual)
        layout.addWidget(start)

        notice = QFrame(objectName="emailPanel")
        notice_layout = QVBoxLayout(notice)
        notice_layout.setContentsMargins(18, 16, 18, 16)
        notice_layout.setSpacing(6)
        notice_layout.addWidget(QLabel("Important", objectName="cardTitle"))
        text = QLabel(
            DISCLAIMER + "\n\nTaxReady never files a return. Client data stays on this computer: the client "
            f"register is stored in\n{CLIENT_DATABASE_PATH}",
            objectName="cardCaption",
        )
        text.setWordWrap(True)
        notice_layout.addWidget(text)
        layout.addWidget(notice)
        layout.addStretch(1)
        page.setWidget(content)
        return page

    def _open_manual(self):
        here = Path(__file__).resolve().parent
        names = ("TaxReady_User_Manual.pdf", "TaxReady_User_Manual.docx")
        for folder in (here / "docs", here):
            for name in names:
                candidate = folder / name
                if candidate.is_file():
                    try:
                        os.startfile(str(candidate))          # Windows
                    except Exception as exc:
                        QMessageBox.warning(self, "User manual", f"Could not open the manual:\n{exc}")
                    return
        QMessageBox.information(
            self,
            "User manual",
            "The user manual was not found next to this program.\n\nKeep TaxReady_User_Manual.pdf in the same "
            "folder as TaxReady.py, or in a folder called docs beside it.",
        )

    def _on_main_tab_changed(self, index):
        if self.main_tabs.widget(index) is self.batch_page and self._batch is None:
            self._batch_refresh_clients()

    def _batch_refresh_clients(self):
        clients = self.client_store.list_clients(self.batch_search.text())
        table = self.batch_table
        table.blockSignals(True)
        table.setRowCount(len(clients))
        for row, client in enumerate(clients):
            box = QTableWidgetItem("")
            if client["has_password"]:
                box.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                box.setCheckState(
                    Qt.CheckState.Checked if client["id"] in self._batch_checked else Qt.CheckState.Unchecked
                )
            else:
                box.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self._batch_checked.discard(client["id"])
            box.setData(Qt.ItemDataRole.UserRole, client["id"])
            table.setItem(row, 0, box)
            cells = [client["name"], client["pan"], client["email"] or "-",
                     "Saved" if client["has_password"] else "Not saved", client["date_of_birth"] or "-"]
            for column, text in enumerate(cells, start=1):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                if column == 4 and not client["has_password"]:
                    item.setForeground(QColor("#B42318"))
                table.setItem(row, column, item)
        table.resizeColumnsToContents()
        table.blockSignals(False)
        self._batch_update_count()

    def _batch_item_changed(self, item):
        if item.column() != 0:
            return
        client_id = item.data(Qt.ItemDataRole.UserRole)
        if item.checkState() == Qt.CheckState.Checked:
            self._batch_checked.add(client_id)
        else:
            self._batch_checked.discard(client_id)
        self._batch_update_count()

    def _batch_set_all(self, checked):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.batch_table.rowCount()):
            item = self.batch_table.item(row, 0)
            if item is not None and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(state)

    def _batch_update_count(self):
        self.batch_count.setText(f"{len(self._batch_checked)} client(s) selected")

    def _batch_start_clicked(self):
        if self._batch is not None or self.worker is not None:
            QMessageBox.information(self, "Run in progress", "A download is already running.")
            return
        clients = [c for c in self.client_store.list_clients("") if c["id"] in self._batch_checked]
        if not clients:
            QMessageBox.warning(self, "No clients selected", "Tick at least one client first.")
            return
        email_on = self.batch_email.isChecked()
        if email_on and (not self.gmail_connected_email or not self._gmail_app_password):
            QMessageBox.warning(
                self, "Configure Gmail first",
                "Emailing is switched on but Gmail is not connected. Open the Gmail Settings tab and click "
                "Save & Verify Gmail, or untick the email option.",
            )
            self.main_tabs.setCurrentWidget(self.gmail_settings_scroll)
            return
        fy = self.batch_fy.currentText()
        answer = QMessageBox.question(
            self, "Start batch",
            f"Process {len(clients)} client(s) for FY {fy}, one after another?\n\n"
            "A browser window opens for each client and you complete the CAPTCHA for each. "
            + ("Each Word review is emailed" + (" after your review." if self.batch_review.isChecked() else " automatically.")
               if email_on else "Emails are switched off; only the Word reports are saved."),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._batch = {
            "queue": clients, "index": -1, "fy": fy, "email": email_on,
            "review": self.batch_review.isChecked(), "continue": self.batch_continue.isChecked(),
            "cancel": False, "done": set(), "tally": {}, "folder_backup": self.folder_input.text(),
        }
        self.batch_results.setRowCount(0)
        self.batch_start.setEnabled(False)
        self.batch_stop.setEnabled(True)
        self.batch_table.setEnabled(False)
        self.start_button.setEnabled(False)
        self._batch_next()

    def _batch_next(self):
        b = self._batch
        if b is None:
            return
        b["index"] += 1
        if b["cancel"] or b["index"] >= len(b["queue"]):
            self._batch_finish()
            return
        client = b["queue"][b["index"]]
        self.batch_progress.setValue(0)
        self.batch_status.setText(f"Client {b['index'] + 1} of {len(b['queue'])}: {client['name']} - starting")
        reason = self._batch_prepare(client)
        if reason:
            self._batch_skip(client, reason)
            QTimer.singleShot(0, self._batch_next)
            return
        self._start()
        if self.worker is None:                       # the run did not start
            self._batch_skip(client, "The run could not be started. Check the client details.")
            QTimer.singleShot(0, self._batch_next)

    def _batch_prepare(self, client):
        """Fill the normal form from the saved client. Returns a reason when the client must be skipped."""
        b = self._batch
        pan = client["pan"].strip().upper()
        if not PAN_PATTERN.fullmatch(pan):
            return "The saved PAN is not valid."
        try:
            password = self.client_store.load_password(client["id"])
        except Exception:
            password = ""
        if not password:
            return "No saved e-Filing password (none saved, or Windows could not decrypt it)."
        email = (client.get("email") or "").strip()
        if b["email"] and not EMAIL_PATTERN.fullmatch(email):
            return "No valid email ID saved for this client."
        folder = (client.get("download_folder") or "").strip() or b["folder_backup"].strip()
        try:
            Path(folder).mkdir(parents=True, exist_ok=True)
            probe = Path(folder) / ".ais_write_test"
            probe.write_text("test", encoding="utf-8")
            probe.unlink()
        except Exception as exc:
            return f"The download folder is not writable: {exc}"
        self._selected_client_id = client["id"]
        self.client_name_input.setText(client["name"])
        self.pan_input.setText(pan)
        self.password_input.setText(password)
        self.fy_combo.setCurrentText(b["fy"])
        self.folder_input.setText(folder)
        self.dob_input.setText(client.get("date_of_birth") or "")
        self.client_email_input.setText(email)
        self.email_enabled.setChecked(b["email"])
        self.review_before_email.setChecked(b["review"])
        return ""

    def _batch_add_result(self, client, result, email_status, note):
        b = self._batch
        b["done"].add(b["index"])
        b["tally"][result] = b["tally"].get(result, 0) + 1
        if email_status == "Sent":
            b["tally"]["Emailed"] = b["tally"].get("Emailed", 0) + 1
        self._batch_results_row(client, result, email_status, note)

    def _batch_results_row(self, client, result, email_status, note):
        table = self.batch_results
        row = table.rowCount()
        table.insertRow(row)
        for column, text in enumerate([client["name"], client["pan"], result, email_status or "-", str(note or "")]):
            item = QTableWidgetItem(text)
            if column == 2:
                colour = {"Completed": "#15703d", "Failed": "#B42318", "Skipped": "#9a6700", "Stopped": "#667085"}
                item.setForeground(QColor(colour.get(result.split(" -")[0], "#1F3864")))
            table.setItem(row, column, item)
        table.scrollToBottom()
        table.resizeColumnsToContents()

    def _batch_record(self, result, email_status="", note=""):
        b = self._batch
        self._batch_add_result(b["queue"][b["index"]], result, email_status, note)

    def _batch_skip(self, client, reason):
        try:
            self.client_store.add_history(
                client["id"], client["name"], client["pan"], self._batch["fy"], "", "Skipped",
                client.get("email", "") if self._batch["email"] else "", "Not attempted", reason,
            )
        except Exception:
            pass
        self._batch_add_result(client, "Skipped", "-", reason)

    def _batch_finish(self):
        b = self._batch
        if b is None:
            return
        for index, client in enumerate(b["queue"]):          # clients never reached (batch stopped early)
            if index not in b["done"]:
                b["tally"]["Not run"] = b["tally"].get("Not run", 0) + 1
                self._batch_results_row(client, "Not run", "-", "The batch was stopped before this client.")
        tally = b["tally"]
        self.folder_input.setText(b["folder_backup"])
        self.password_input.clear()
        self._batch = None
        self.batch_start.setEnabled(True)
        self.batch_stop.setEnabled(False)
        self.batch_table.setEnabled(True)
        self.start_button.setEnabled(True)
        summary = (
            f"Completed: {tally.get('Completed', 0) + tally.get('Completed - email failed', 0)}   |   "
            f"Emailed: {tally.get('Emailed', 0)}   |   Failed: {tally.get('Failed', 0)}   |   "
            f"Skipped: {tally.get('Skipped', 0)}   |   Not run: {tally.get('Not run', 0)}"
        )
        self.batch_status.setText("Batch finished.  " + summary)
        self.batch_progress.setValue(100)
        self._set_status_badge("COMPLETED", "completed")
        QMessageBox.information(
            self, "Batch finished",
            summary.replace("   |   ", "\n") + "\n\nEach Word report is in its client's folder. "
            "The results table on this tab lists every client.",
        )

    def _refresh_client_list(self, search_text=None):
        search = (
            search_text
            if isinstance(search_text, str)
            else self.client_search_input.text()
        )
        selected_id = self._selected_client_id
        clients = self.client_store.list_clients(search)
        self.client_combo.blockSignals(True)
        self.client_combo.clear()
        self.client_combo.addItem("Select a saved client", None)
        selected_index = 0
        for client in clients:
            label = f'{client["name"]}  |  {client["pan"]}'
            if client["email"]:
                label += f'  |  {client["email"]}'
            self.client_combo.addItem(label, client["id"])
            if client["id"] == selected_id:
                selected_index = self.client_combo.count() - 1
        self.client_combo.setCurrentIndex(selected_index)
        self.client_combo.blockSignals(False)

    def _load_selected_client(self, index):
        client_id = self.client_combo.itemData(index)
        if not client_id:
            self._selected_client_id = None
            return
        client = self.client_store.get_client(client_id)
        if not client:
            return
        self._selected_client_id = client["id"]
        self.client_name_input.setText(client["name"])
        self.pan_input.setText(client["pan"])
        self.client_email_input.setText(client["email"])
        self.date_of_birth_input.setText(client["date_of_birth"])
        if client["download_folder"]:
            self.folder_input.setText(client["download_folder"])
        try:
            self.password_input.setText(self.client_store.load_password(client_id))
        except Exception as exc:
            self.password_input.clear()
            QMessageBox.warning(
                self,
                "Saved password unavailable",
                "The saved password could not be decrypted by this Windows account. "
                "Enter it again and click Save client.\n\n"
                f"Technical detail: {exc}",
            )
        self.status_label.setText(f'Loaded saved client: {client["name"]}')

    def _new_client(self):
        self._selected_client_id = None
        self.client_combo.blockSignals(True)
        self.client_combo.setCurrentIndex(0)
        self.client_combo.blockSignals(False)
        self.client_name_input.clear()
        self.pan_input.clear()
        self.password_input.clear()
        self.client_email_input.clear()
        self.date_of_birth_input.clear()
        self.client_name_input.setFocus()

    def _save_client(self):
        name = self.client_name_input.text().strip()
        pan = self.pan_input.text().strip().upper()
        email = self.client_email_input.text().strip()
        folder = self.folder_input.text().strip()
        password = self.password_input.text()
        date_of_birth_text = self.date_of_birth_input.text().strip()
        date_of_birth = normalize_date_of_birth(date_of_birth_text)
        if not name:
            QMessageBox.warning(self, "Client name required", "Enter the client name.")
            self.client_name_input.setFocus()
            return
        if not PAN_PATTERN.fullmatch(pan):
            QMessageBox.warning(self, "Check PAN", "Enter a valid 10-character PAN.")
            self.pan_input.setFocus()
            return
        if email and not EMAIL_PATTERN.fullmatch(email):
            QMessageBox.warning(self, "Check client email", "Enter a valid email ID.")
            self.client_email_input.setFocus()
            return
        if date_of_birth_text and not date_of_birth:
            QMessageBox.warning(
                self,
                "Check Date of Birth",
                "Enter the Date of Birth in DD-MM-YYYY format.",
            )
            self.date_of_birth_input.setFocus()
            return
        try:
            client_id = self.client_store.save_client(
                name=name,
                pan=pan,
                email=email,
                download_folder=folder,
                date_of_birth=date_of_birth,
                password=password if password else _KEEP,
                client_id=self._selected_client_id,
            )
        except sqlite3.IntegrityError:
            QMessageBox.warning(
                self,
                "PAN already saved",
                "This PAN already exists in the client database. Select that client "
                "from the list before editing it.",
            )
            return
        except Exception as exc:
            QMessageBox.critical(self, "Could not save client", str(exc))
            return
        self._selected_client_id = client_id
        self.client_search_input.clear()
        self._refresh_client_list()
        QMessageBox.information(
            self,
            "Client saved",
            "Client details were saved successfully. The e-Filing password is "
            "protected with Windows account encryption.",
        )

    def _delete_client(self):
        client_id = self._selected_client_id
        client = self.client_store.get_client(client_id)
        if not client:
            QMessageBox.warning(
                self, "Select a client", "Select a saved client to delete."
            )
            return
        answer = QMessageBox.question(
            self,
            "Delete client",
            f'Delete {client["name"]} ({client["pan"]}) from the client database?\n\n'
            "Existing activity history will be retained.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.client_store.delete_client(client_id)
        except Exception as exc:
            QMessageBox.critical(self, "Could not delete client", str(exc))
            return
        self._new_client()
        self._refresh_client_list()

    @staticmethod
    def _csv_value(row, *names):
        normalized = {
            str(key).strip().lower().replace(" ", "_"): str(value or "").strip()
            for key, value in row.items()
            if key is not None
        }
        for name in names:
            value = normalized.get(name)
            if value:
                return value
        return ""

    def _import_clients_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import client database CSV", str(Path.home()), "CSV files (*.csv)"
        )
        if not path:
            return
        imported = 0
        passwords_imported = 0
        skipped = []
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                if not reader.fieldnames:
                    raise ValueError("The CSV file has no header row.")
                for line_number, row in enumerate(reader, 2):
                    name = self._csv_value(row, "client_name", "name", "taxpayer_name")
                    pan = self._csv_value(row, "pan", "pan_number").upper()
                    email = self._csv_value(row, "email", "client_email", "email_id")
                    date_of_birth_text = self._csv_value(
                        row, "date_of_birth", "dob", "birth_date"
                    )
                    date_of_birth = normalize_date_of_birth(date_of_birth_text)
                    password = self._csv_value(
                        row, "password", "e_filing_password", "efiling_password"
                    )
                    folder = self._csv_value(
                        row, "download_folder", "folder", "ais_download_folder"
                    )
                    if not name or not PAN_PATTERN.fullmatch(pan):
                        skipped.append(f"Row {line_number}: client name or PAN is invalid")
                        continue
                    if email and not EMAIL_PATTERN.fullmatch(email):
                        skipped.append(f"Row {line_number}: email is invalid")
                        continue
                    if date_of_birth_text and not date_of_birth:
                        skipped.append(
                            f"Row {line_number}: Date of Birth is invalid"
                        )
                        continue
                    self.client_store.upsert_client(
                        name=name,
                        pan=pan,
                        email=email,
                        download_folder=folder,
                        date_of_birth=date_of_birth,
                        password=password if password else _KEEP,
                    )
                    if password:
                        passwords_imported += 1
                    imported += 1
        except Exception as exc:
            QMessageBox.critical(self, "CSV import failed", str(exc))
            return
        self._refresh_client_list()
        note = f"Imported or updated {imported} client record(s)."
        if passwords_imported:
            note += (
                f"\n\n{passwords_imported} password(s) were encrypted in the database. "
                "The source CSV still contains readable passwords; secure or delete that "
                "source file after confirming the import."
            )
        if skipped:
            preview = "\n".join(skipped[:8])
            more = f"\n...and {len(skipped) - 8} more." if len(skipped) > 8 else ""
            note += f"\n\nSkipped {len(skipped)} row(s):\n{preview}{more}"
        QMessageBox.information(self, "CSV import complete", note)

    def _export_clients_csv(self):
        default_path = Path.home() / "Documents" / "AIS_Client_Database.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export client database CSV", str(default_path), "CSV files (*.csv)"
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as csv_file:
                writer = csv.DictWriter(
                    csv_file,
                    fieldnames=[
                        "Client Name",
                        "PAN",
                        "Email",
                        "Date of Birth",
                        "Password",
                        "Download Folder",
                    ],
                )
                writer.writeheader()
                for client in self.client_store.list_clients():
                    writer.writerow(
                        {
                            "Client Name": client["name"],
                            "PAN": client["pan"],
                            "Email": client["email"],
                            "Date of Birth": client["date_of_birth"],
                            "Password": "",
                            "Download Folder": client["download_folder"],
                        }
                    )
        except Exception as exc:
            QMessageBox.critical(self, "CSV export failed", str(exc))
            return
        QMessageBox.information(
            self,
            "CSV export complete",
            f"Client database exported to:\n\n{path}\n\n"
            "The Password column is intentionally blank. It can be completed before "
            "a future import, but readable-password CSV files should be secured.",
        )

    @staticmethod
    def _mirror_text(source, target):
        if target.text() != source.text():
            target.setText(source.text())

    def _show_history(self):
        rows = self.client_store.list_history()
        dialog = QDialog(self)
        dialog.setWindowTitle("Activity history")
        dialog.resize(1080, 540)
        layout = QVBoxLayout(dialog)
        heading = QLabel(
            "Latest 500 activity events", objectName="cardTitle"
        )
        layout.addWidget(heading)
        table = QTableWidget(len(rows), 9)
        table.setHorizontalHeaderLabels(
            [
                "Date / time",
                "Client",
                "PAN",
                "F.Y.",
                "Download",
                "Email to",
                "Email status",
                "File",
                "Details",
            ]
        )
        for row_index, row in enumerate(rows):
            values = [
                row["event_time"],
                row["client_name"],
                row["pan"],
                row["financial_year"],
                row["download_status"],
                row["email_to"],
                row["email_status"],
                row["file_path"],
                row["details"],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value or ""))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row_index, column, item)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(table, 1)
        close_button = QPushButton("Close", objectName="secondaryButton")
        close_button.setFixedHeight(40)
        close_button.clicked.connect(dialog.accept)
        clear_button = QPushButton("Clear history", objectName="dangerSoftButton")
        clear_button.setFixedHeight(40)
        clear_button.setEnabled(bool(rows))

        def clear_history():
            answer = QMessageBox.question(
                dialog,
                "Clear activity history",
                "Delete ALL activity history records?\n\nSaved clients and the Word reports are not "
                "affected. This cannot be undone.",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            try:
                self.client_store.clear_history()
            except Exception as exc:
                QMessageBox.warning(dialog, "Clear history", f"Could not clear the history:\n{exc}")
                return
            table.setRowCount(0)
            heading.setText("Activity history cleared")
            clear_button.setEnabled(False)

        clear_button.clicked.connect(clear_history)
        button_row = QHBoxLayout()
        button_row.addWidget(clear_button)
        button_row.addStretch(1)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)
        dialog.exec()

    def _record_history(
        self, file_path, download_status, email_status="", details=""
    ):
        run = self._active_run
        if not run:
            return
        try:
            self.client_store.add_history(
                run["client_id"],
                run["client_name"],
                run["pan"],
                run["financial_year"],
                file_path,
                download_status,
                run["client_email"] if run["email_enabled"] else "",
                email_status,
                details,
            )
        except Exception as exc:
            self.log_box.append(f"Could not update activity history: {exc}")

    def _on_profile_captured(self, date_of_birth):
        normalized = normalize_date_of_birth(date_of_birth)
        if not normalized:
            return
        self.date_of_birth_input.setText(normalized)
        client_id = self._active_run["client_id"] if self._active_run else None
        if client_id:
            try:
                self.client_store.update_date_of_birth(client_id, normalized)
                self.log_box.append("Date of birth saved in the selected client record.")
            except Exception as exc:
                self.log_box.append(f"Could not save the captured Date of Birth: {exc}")
        else:
            self.log_box.append(
                "Date of birth captured. Click Save client after completion to retain it."
            )

    def _toggle_password(self, checked):
        self.password_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self.show_password.setText("Hide" if checked else "Show")

    def _add_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 9)
        shadow.setColor(QColor("#1f293326"))
        widget.setGraphicsEffect(shadow)

    def _change_theme(self, theme_name):
        if theme_name not in THEMES:
            return
        self._settings.setValue("theme", theme_name)
        self._apply_theme(theme_name)

    def _apply_theme(self, theme_name):
        palette = dict(THEMES[theme_name])
        asset_dir = Path(tempfile.gettempdir()) / "ais_modern_ui"
        asset_dir.mkdir(parents=True, exist_ok=True)
        chevron_path = asset_dir / ("chevron_" + re.sub(r"[^a-z0-9]+", "_", theme_name.lower()) + ".svg")
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="8" '
            'viewBox="0 0 12 8"><path d="M1 1.5 6 6.5 11 1.5" fill="none" '
            f'stroke="{palette["chevron_color"]}" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round"/></svg>'
        )
        chevron_path.write_text(svg, encoding="utf-8")
        palette["chevron"] = chevron_path.as_posix()
        style = STYLE_TEMPLATE
        for token, value in palette.items():
            style = style.replace(f"@{token}@", value)
        self.setStyleSheet(style)
        shadow_color = QColor(palette["shadow"])
        for card in (
            self.client_card,
            self.form_card,
            self.progress_card,
            self.gmail_settings_card,
        ):
            effect = card.graphicsEffect()
            if isinstance(effect, QGraphicsDropShadowEffect):
                effect.setColor(shadow_color)
        self._repolish(self.status_badge)
        for _, step in self.workflow_steps:
            step.refresh_style()

    @staticmethod
    def _repolish(widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def _set_status_badge(self, text, state):
        self.status_badge.setText(text)
        self.status_badge.setProperty("state", state)
        self._repolish(self.status_badge)

    def _update_workflow(self, percent, error=False):
        self._last_progress = percent
        thresholds = [threshold for threshold, _ in self.workflow_steps]
        active_index = None
        for index, threshold in enumerate(thresholds):
            next_threshold = (
                thresholds[index + 1] if index + 1 < len(thresholds) else 100
            )
            if threshold <= percent < next_threshold:
                active_index = index
                break
        for index, (threshold, row) in enumerate(self.workflow_steps):
            if percent >= 100:
                state = "done"
            elif percent < threshold:
                state = "pending"
            elif active_index == index:
                state = "error" if error else "active"
            else:
                state = "done"
            row.set_state(state)

    def _choose_folder(self):
        chosen = QFileDialog.getExistingDirectory(
            self, "Choose AIS download folder", self.folder_input.text()
        )
        if chosen:
            self.folder_input.setText(chosen)

    def _restore_gmail_settings(self):
        sender = self._settings.value(GMAIL_SENDER_SETTING, "", type=str).strip()
        encrypted_text = self._settings.value(
            GMAIL_PASSWORD_SETTING, "", type=str
        ).strip()
        self.gmail_sender_input.setText(sender)
        if sender and encrypted_text:
            try:
                encrypted = base64.b64decode(encrypted_text.encode("ascii"))
                self._gmail_app_password = unprotect_password(encrypted)
                self.gmail_connected_email = sender
                self.gmail_connection_status.setText(f"Gmail configured: {sender}")
                self.gmail_tab_status.setText(
                    f"Saved Gmail connection: {sender}. The App Password is "
                    "Windows-encrypted and ready for automatic email."
                )
                return
            except Exception as exc:
                self.gmail_tab_status.setText(
                    "The saved Gmail App Password could not be decrypted by this "
                    f"Windows account. Enter it again and verify. Details: {exc}"
                )
        self._gmail_app_password = ""
        self.gmail_connected_email = ""
        self.gmail_connection_status.setText("Gmail status: Not configured")

    def _toggle_gmail_password(self, checked):
        self.gmail_app_password_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self.show_gmail_password.setText("Hide" if checked else "Show")

    def _connect_gmail(self):
        sender = self.gmail_sender_input.text().strip()
        entered_password = normalize_app_password(
            self.gmail_app_password_input.text()
        )
        app_password = entered_password or self._gmail_app_password
        self.gmail_connect_button.setEnabled(False)
        self.gmail_tab_status.setText("Verifying Gmail SMTP connection...")
        self.gmail_connection_status.setText("Gmail status: Verifying...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            verify_gmail_smtp(sender, app_password)
            if entered_password:
                encrypted = protect_password(entered_password)
                self._settings.setValue(
                    GMAIL_PASSWORD_SETTING,
                    base64.b64encode(encrypted).decode("ascii"),
                )
            self._settings.setValue(GMAIL_SENDER_SETTING, sender)
            self._settings.sync()
            self._gmail_app_password = app_password
            self.gmail_connected_email = sender
            self.gmail_app_password_input.clear()
            self.gmail_connection_status.setText(f"Gmail connected: {sender}")
            self.gmail_tab_status.setText(
                f"Gmail verified successfully: {sender}. Future tax-review emails will "
                "use this saved connection automatically."
            )
            QMessageBox.information(
                self,
                "Gmail connected",
                f"AIS Auto Downloader can now send email from:\n\n{sender}\n\n"
                "The App Password has been saved with Windows encryption.",
            )
        except Exception as exc:
            self.gmail_connection_status.setText(
                "Gmail status: Connection not verified"
            )
            self.gmail_tab_status.setText(f"Gmail verification failed: {exc}")
            QMessageBox.critical(
                self,
                "Gmail connection failed",
                f"{exc}\n\nConfirm the sender Gmail address, use the 16-character "
                "Google App Password without spaces, and ensure internet access.",
            )
        finally:
            QApplication.restoreOverrideCursor()
            self.gmail_connect_button.setEnabled(True)

    def _clear_gmail_settings(self):
        answer = QMessageBox.question(
            self,
            "Remove Gmail connection",
            "Remove the saved sender Gmail and encrypted App Password?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._settings.remove(GMAIL_SENDER_SETTING)
        self._settings.remove(GMAIL_PASSWORD_SETTING)
        self._settings.sync()
        self._gmail_app_password = ""
        self.gmail_connected_email = ""
        self.gmail_sender_input.clear()
        self.gmail_app_password_input.clear()
        self.gmail_connection_status.setText("Gmail status: Not configured")
        self.gmail_tab_status.setText("Gmail is not configured.")

    def _validate(self):
        pan = self.pan_input.text().strip().upper()
        password = self.password_input.text()
        fy = self.fy_combo.currentText().strip()
        folder = self.folder_input.text().strip()
        email_enabled = self.email_enabled.isChecked()
        client_email = self.client_email_input.text().strip()
        if not PAN_PATTERN.fullmatch(pan):
            QMessageBox.warning(self, "Check PAN", "Enter a valid 10-character PAN.")
            self.pan_input.setFocus()
            return None
        if not password:
            QMessageBox.warning(
                self, "Password required", "Enter the e-Filing password."
            )
            self.password_input.setFocus()
            return None
        if not valid_financial_year(fy):
            QMessageBox.warning(
                self, "Check Financial Year", "Select a valid Financial Year."
            )
            return None
        if not folder:
            QMessageBox.warning(
                self, "Folder required", "Choose a download folder."
            )
            return None
        try:
            Path(folder).mkdir(parents=True, exist_ok=True)
            test_file = Path(folder) / ".ais_write_test"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
        except Exception as exc:
            QMessageBox.critical(
                self, "Folder not writable", f"Choose another folder.\n\n{exc}"
            )
            return None
        if email_enabled:
            if not EMAIL_PATTERN.fullmatch(client_email):
                QMessageBox.warning(
                    self, "Check client email", "Enter a valid client email ID."
                )
                self.client_email_input.setFocus()
                return None
            if not self.gmail_connected_email or not self._gmail_app_password:
                QMessageBox.warning(
                    self,
                    "Configure Gmail first",
                    "Open the Gmail Settings tab, enter the sender Gmail and "
                    "16-character Google App Password, then click Save & Verify Gmail.",
                )
                self.main_tabs.setCurrentWidget(self.gmail_settings_scroll)
                self.gmail_connect_button.setFocus()
                return None
        return pan, password, fy, folder, email_enabled, client_email

    def _start(self):
        values = self._validate()
        if not values:
            return
        pan, password, fy, folder, email_enabled, client_email = values
        dob_text = self.dob_input.text().strip()
        if dob_text and not normalize_date_of_birth(dob_text) and not self._batch:
            QMessageBox.warning(
                self, "Check date of birth", "Enter the date of birth as DD-MM-YYYY, e.g. 15-06-1990."
            )
            self.dob_input.setFocus()
            return
        if not dob_text and not self._batch:
            box = QMessageBox(self)
            box.setWindowTitle("Date of birth not entered")
            box.setIcon(QMessageBox.Icon.Question)
            box.setText(
                "The date of birth is needed to decrypt the downloaded AIS.\n\n"
                "The app will try to read it from the portal after login. If that fails, the "
                "download is kept but no tax review can be prepared.\n\nEnter it now?"
            )
            enter_now = box.addButton("Enter date of birth", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Continue - read it from the portal", QMessageBox.ButtonRole.ActionRole)
            box.exec()
            if box.clickedButton() is enter_now:
                self.dob_input.setFocus()
                return
        selected_client = self.client_store.get_client(self._selected_client_id)
        if not selected_client or selected_client["pan"].upper() != pan:
            selected_client = self.client_store.get_client_by_pan(pan)
        selected_client_id = (
            selected_client["id"]
            if selected_client and selected_client["pan"].upper() == pan
            else None
        )
        self._active_run = {
            "client_id": selected_client_id,
            "client_name": (
                selected_client["name"]
                if selected_client
                else self.client_name_input.text().strip()
            ),
            "pan": pan,
            "financial_year": fy,
            "client_email": client_email,
            "email_enabled": email_enabled,
        }
        self.client_card.setEnabled(False)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.pan_input.setEnabled(False)
        self.password_input.setEnabled(False)
        self.fy_combo.setEnabled(False)
        self.folder_input.setEnabled(False)
        self.email_enabled.setEnabled(False)
        self.review_before_email.setEnabled(False)
        self.client_email_input.setEnabled(False)
        self.gmail_settings_card.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Starting.")
        self.status_label.setText("Starting secure browser session")
        self.log_box.clear()
        self._last_progress = 0
        self._set_status_badge("RUNNING", "running")
        self._update_workflow(0)
        self.thread = QThread(self)
        self.worker = AutomationWorker(
            pan,
            password,
            fy,
            folder,
            email_enabled,
            client_email,
            self.gmail_connected_email,
            self._gmail_app_password,
            self._active_run["client_name"],
            self.review_before_email.isChecked(),
        )
        self.worker.fallback_dob = normalize_date_of_birth(self.dob_input.text())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self.log_box.append)
        self.worker.manual_action.connect(self._on_manual_action)
        self.worker.profile_captured.connect(self._on_profile_captured)
        self.worker.finished.connect(self._on_success)
        self.worker.email_failed.connect(self._on_email_failure)
        self.worker.review_needed.connect(self._on_review_needed)
        self.worker.failed.connect(self._on_failure)
        self.worker.stopped.connect(self._on_stopped)
        self.worker.finished.connect(self.thread.quit)
        self.worker.email_failed.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.worker.stopped.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _stop(self):
        if self._batch:
            self._batch["cancel"] = True        # no further clients after the current one
            self.batch_status.setText("Stopping the batch...")
        if self.worker:
            self.stop_button.setEnabled(False)
            self.status_label.setText("Stopping safely.")
            self.worker.request_stop()

    def _on_progress(self, percent, message):
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(f"{percent}%")
        self.status_label.setText(message)
        self._set_status_badge("RUNNING", "running")
        self._update_workflow(percent)
        if self._batch and 0 <= self._batch["index"] < len(self._batch["queue"]):
            b = self._batch
            self.batch_progress.setValue(percent)
            self.batch_status.setText(
                f"Client {b['index'] + 1} of {len(b['queue'])}: {b['queue'][b['index']]['name']} - {message}"
            )

    def _on_manual_action(self, message):
        self.status_label.setText("Manual CAPTCHA action required in the browser")
        self._set_status_badge("ACTION NEEDED", "action")
        QMessageBox.information(self, "Complete CAPTCHA in browser", message)

    def _on_review_needed(self, path, case):
        """The worker waits here until the user approves or declines the email."""
        self.status_label.setText("Waiting for your review of the computation")
        self._set_status_badge("ACTION NEEDED", "action")
        dialog = ReviewDialog(case, path, self.client_email_input.text().strip(), self)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        if self.worker is not None:
            self.worker.provide_review_decision(accepted, dialog.final_summary)
        self._set_status_badge("RUNNING", "running")

    def _on_success(self, path):
        self.password_input.clear()
        email_status = (getattr(self.worker, "email_status", "") or "Not requested")
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Completed")
        emailed_to = (
            self.client_email_input.text().strip() if email_status == "Sent" else ""
        )
        self.status_label.setText(
            {
                "Sent": "Tax review saved and emailed successfully",
                "Skipped after review": "Tax review saved; email not sent after review",
            }.get(email_status, "Tax review saved successfully")
        )
        self._set_status_badge("COMPLETED", "completed")
        self._update_workflow(100)
        self._record_history(path, "Completed", email_status)
        if self._batch:                                   # batch: no pop-up, record and go on to the next client
            self._batch_record("Completed", email_status, path)
            self._reset_controls()
            QTimer.singleShot(600, self._batch_next)
            return
        email_note = {
            "Sent": f"\n\nEmail sent successfully to: {emailed_to}",
            "Skipped after review": "\n\nThe email was not sent because the review was not approved.",
        }.get(email_status, "")
        QMessageBox.information(
            self,
            "Tax review complete",
            f"The Word tax review was saved to:\n\n{path}{email_note}\n\n"
            "Only the Word file is kept. The downloaded and decrypted AIS files were deleted. "
            "This is an estimate from AIS data only - not tax advice.",
        )
        self._reset_controls()

    def _on_email_failure(self, path, message):
        self.password_input.clear()
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Report saved - email not sent")
        self.status_label.setText("The report was saved, but Gmail could not send the email")
        self._set_status_badge("FAILED", "failed")
        self._update_workflow(100)
        self._record_history(path, "Completed", "Failed", message)
        if self._batch:
            self._batch_record("Completed - email failed", "Failed", f"{path}  ({message.splitlines()[0][:120]})")
            self._reset_controls()
            QTimer.singleShot(600, self._batch_next)
            return
        QMessageBox.warning(
            self,
            "Report saved but email not sent",
            f"The Word tax review is safely saved at:\n\n{path}\n\n"
            f"Gmail error:\n{message}\n\n"
            "Click Connect / Verify Gmail again and check the internet connection. "
            "The income-tax download and the computation do not need to be repeated; "
            "attach the saved Word file to an email manually if needed.",
        )
        self._reset_controls()

    def _on_failure(self, message):
        self.password_input.clear()
        self.progress_bar.setFormat("Stopped with an error")
        self.status_label.setText("Could not complete the AIS download")
        self._set_status_badge("FAILED", "failed")
        self._update_workflow(self._last_progress, error=True)
        self._record_history("", "Failed", "Not attempted", message)
        if self._batch:
            self._batch_record("Failed", "-", message.strip().splitlines()[0][:200] if message.strip() else "Unknown error")
            if not self._batch["continue"]:
                self._batch["cancel"] = True
            self._reset_controls()
            QTimer.singleShot(600, self._batch_next)
            return
        QMessageBox.critical(
            self,
            "AIS download not completed",
            f"{message}\n\nPasswords are never written to the activity log. Any saved "
            "client password remains protected by Windows encryption. Review the progress "
            "log for the last completed stage.",
        )
        self._reset_controls()

    def _on_stopped(self):
        self.password_input.clear()
        self.progress_bar.setFormat("Stopped")
        self.status_label.setText("Stopped safely by user")
        self._set_status_badge("STOPPED", "stopped")
        self._update_workflow(self._last_progress)
        self._record_history("", "Stopped", "Not attempted", "Stopped by user")
        if self._batch:
            self._batch_record("Stopped", "-", "Stopped by user")
            self._batch["cancel"] = True
            self._reset_controls()
            QTimer.singleShot(300, self._batch_next)
            return
        self._reset_controls()

    def _reset_controls(self):
        self.client_card.setEnabled(True)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.pan_input.setEnabled(True)
        self.password_input.setEnabled(True)
        self.fy_combo.setEnabled(True)
        self.folder_input.setEnabled(True)
        self.email_enabled.setEnabled(True)
        email_on = self.email_enabled.isChecked()
        self.client_email_input.setEnabled(email_on)
        self.review_before_email.setEnabled(email_on)
        self.gmail_settings_card.setEnabled(True)
        self.worker = None
        self.thread = None
        self._active_run = None
        if self._batch:
            self.start_button.setEnabled(False)           # the batch starts the runs, not the button

    def closeEvent(self, event):
        if self._batch:
            self._batch["cancel"] = True
        if self.worker is not None:
            answer = QMessageBox.question(
                self,
                "Download in progress",
                "Stop the current browser session and close the app?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.worker.request_stop()
        event.accept()


class ReviewDialog(QDialog):
    """Review AND edit the tax computation. The email goes out only if the user clicks Send."""

    HEADS = ["salary", "hp", "business", "other", "winnings", "info", "unclassified"]

    def __init__(self, case, report_path, client_email, parent=None):
        super().__init__(parent)
        self.case = case
        self.report_path = str(report_path)
        self.client_email = client_email
        self.dirty = False
        self.final_summary = None
        self._busy = True
        self.res = compute_case(case)
        self._last_inactive = bool(case["profile"]["include_inactive"])
        self.setWindowTitle("Review and edit the tax computation")
        self.setModal(True)
        # fit the window to the screen so the buttons at the bottom are always visible
        screen = parent.screen() if parent is not None else QApplication.primaryScreen()
        avail = screen.availableGeometry()
        width = min(1120, avail.width() - 30)
        height = max(420, min(800, avail.height() - 90))
        self.setMinimumSize(min(860, width), min(500, height))
        self.resize(width, height)
        self.move(avail.x() + (avail.width() - width) // 2, avail.y() + 8)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)
        self.head = QLabel()
        self.head.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(self.head)
        self.tabs = QTabWidget(objectName="mainTabs")
        root.addWidget(self.tabs, 1)
        self._build_summary_tab()
        self._build_income_tab()
        self._build_cg_tab()
        self._build_inputs_tab()
        self._load_inputs()
        self.status = QLabel("Review the figures. Edit any tab if something needs correcting - the totals update instantly.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        note = QLabel(
            f"The email with the Word report goes to <b>{escape(client_email)}</b> only if you click "
            "<b>Send email</b>. The Word report is already saved in the client folder either way, and "
            "is refreshed with your edits."
        )
        note.setTextFormat(Qt.TextFormat.RichText)
        note.setWordWrap(True)
        root.addWidget(note)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        open_button = QPushButton("Open Word report", objectName="ghostButton")
        open_button.clicked.connect(self._open_report)
        update_button = QPushButton("Update Word report", objectName="secondaryButton")
        update_button.clicked.connect(self._regenerate)
        skip_button = QPushButton("Do not send email", objectName="dangerSoftButton")
        skip_button.clicked.connect(self.reject)
        send_button = QPushButton("Send email", objectName="primaryButton")
        send_button.setDefault(True)
        send_button.clicked.connect(self._send)
        for button in (open_button, update_button, skip_button, send_button):
            button.setFixedHeight(42)
        buttons.addWidget(open_button)
        buttons.addWidget(update_button)
        buttons.addStretch(1)
        buttons.addWidget(skip_button)
        buttons.addWidget(send_button)
        root.addLayout(buttons)
        self._busy = False
        self._fill_income()
        self._fill_cg()
        self._refresh_summary()

    # ---------------------------------------------------------------- summary tab
    def _build_summary_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(10)
        grid = QGridLayout()
        grid.setSpacing(8)
        colours = ["#2E5597", "#7B3FE4", "#00A896", "#F77F00", "#E63946", "#1F3864"]
        self.kpi_labels = []
        for i in range(6):
            card = QFrame()
            card.setStyleSheet(
                f"QFrame{{background:{colours[i]};border-radius:10px;}}QLabel{{color:white;background:transparent;}}"
            )
            box = QVBoxLayout(card)
            box.setContentsMargins(12, 8, 12, 8)
            top, val = QLabel(), QLabel()
            top.setStyleSheet("font-size:10px;font-weight:700;")
            val.setStyleSheet("font-size:18px;font-weight:700;")
            box.addWidget(top)
            box.addWidget(val)
            self.kpi_labels.append((top, val))
            grid.addWidget(card, i // 3, i % 3)
        lay.addLayout(grid)
        self.cmp_table = QTableWidget(13, 3)
        self.cmp_table.setHorizontalHeaderLabels(["Particulars", "Old regime", "New regime"])
        self.cmp_table.verticalHeader().setVisible(False)
        self.cmp_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.cmp_table.horizontalHeader().setStretchLastSection(True)
        self.cmp_table.setColumnWidth(0, 360)
        self.cmp_table.setColumnWidth(1, 220)
        lay.addWidget(self.cmp_table, 1)
        self.points_box = QLabel()
        self.points_box.setTextFormat(Qt.TextFormat.RichText)
        self.points_box.setWordWrap(True)
        self.points_box.setStyleSheet("background:#FFF2CC;color:#1F3864;border-left:5px solid #BF9000;padding:8px;")
        lay.addWidget(self.points_box)
        self.tabs.addTab(page, "Summary")

    def _refresh_summary(self):
        summary = review_summary(self.case, self.res)
        self.head.setText(
            f"<span style='font-size:17px;font-weight:700'>{escape(summary['name'])}</span><br>"
            f"PAN {escape(summary['pan'])} &nbsp;|&nbsp; {escape(summary['law'])}"
        )
        for (top, val), (label, value) in zip(self.kpi_labels, summary["kpis"]):
            top.setText(label.upper())
            val.setText(value)
        bold = ("Gross tax liability", "Net tax payable", "Refund indicated")
        for r, (label, old, new) in enumerate(summary["lines"]):
            for c, text in enumerate((label, old, new)):
                item = QTableWidgetItem(text)
                if c:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if label in bold:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setBackground(QColor("#DEEAF6"))
                    item.setForeground(QColor("#1F3864"))
                self.cmp_table.setItem(r, c, item)
        pts = summary["points"]
        self.points_box.setVisible(bool(pts))
        self.points_box.setText(
            "<b>Points to review</b><ul style='margin-top:2px'>" + "".join(f"<li>{escape(p)}</li>" for p in pts) + "</ul>"
        )

    # ---------------------------------------------------------------- AIS income tab
    def _build_income_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        tip = QLabel(
            "Each line is a group of AIS rows. Change its head, or untick Income / Credit to leave it out. "
            "Greyed rows were counted once (the same income is reported through TDS and SFT)."
        )
        tip.setWordWrap(True)
        lay.addWidget(tip)
        self.income_table = QTableWidget(0, 10)
        self.income_table.setHorizontalHeaderLabels(
            ["Head", "Category", "Code", "Source", "Status / flags", "Rows", "Amount", "TDS/TCS", "Income", "Credit"]
        )
        self.income_table.setAlternatingRowColors(True)
        self.income_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        lay.addWidget(self.income_table, 1)
        self.tabs.addTab(page, "AIS income")

    def _fill_income(self):
        groups = self.case["groups"]
        table = self.income_table
        self._busy = True
        table.setRowCount(len(groups))
        for r, g in enumerate(groups):
            opts = ["cg"] if g["orig_head"] == "cg" else list(self.HEADS)
            if g["head"] not in opts:
                opts.append(g["head"])
            combo = QComboBox()
            for h in opts:
                combo.addItem(HEAD_LABELS[h], h)
            combo.setCurrentIndex(opts.index(g["head"]))
            combo.currentIndexChanged.connect(lambda _i, gg=g, cc=combo: self._head_changed(gg, cc))
            table.setCellWidget(r, 0, combo)
            vals = [g["category"], g["code"], g["source"], g["flags"] or "-", str(g["count"]),
                    money(g["amount"], "Rs "), money(g["deducted"], "Rs ")]
            for ci, text in enumerate(vals):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if ci >= 4:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if g["dup"]:
                    item.setBackground(QColor("#FFF2CC"))
                    item.setForeground(QColor("#5b4310"))
                if not g["active"]:
                    item.setForeground(QColor("#888888"))
                if g.get("dedup"):
                    item.setToolTip(g["dedup"])
                    item.setForeground(QColor("#6C757D"))
                    item.setBackground(QColor("#E3EAF6"))
                table.setItem(r, ci + 1, item)
            for col, key in ((8, "include"), (9, "credit")):
                box = QCheckBox()
                box.setChecked(bool(g[key]))
                box.toggled.connect(lambda state, gg=g, kk=key: self._flag_changed(gg, kk, state))
                table.setCellWidget(r, col, box)
        table.resizeColumnsToContents()
        self._busy = False

    def _head_changed(self, group, combo):
        if self._busy:
            return
        group["head"] = combo.currentData()
        group["include"] = group["head"] in INCOME_HEADS
        self._changed(rebuild_income=True)

    def _flag_changed(self, group, key, state):
        if self._busy:
            return
        group[key] = bool(state)
        self._changed()

    # ---------------------------------------------------------------- capital gains tab
    def _build_cg_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        tip = QLabel(
            "One row per sale: gain = sale value less the purchase cost shown in AIS. Red rows show no purchase "
            "cost in AIS (gain = full sale value) - type the cost in the 'Purchase cost' column if you know it."
        )
        tip.setWordWrap(True)
        lay.addWidget(tip)
        self.cg_table = QTableWidget(0, 9)
        self.cg_table.setHorizontalHeaderLabels(
            ["Transfer date", "Security", "Holding", "Section", "Quantity", "Sale value",
             "Purchase cost (editable)", "Gain / (loss)", "Flag"]
        )
        self.cg_table.itemChanged.connect(self._cg_edited)
        lay.addWidget(self.cg_table, 1)
        self.tabs.addTab(page, "Capital gains")

    def _fill_cg(self):
        tx = self.res["cg_tx"]
        table = self.cg_table
        self._busy = True
        table.setRowCount(len(tx))
        names = {"111A": "Short term / 111A", "112A": "Long term / 112A", "112": "Long term / 112",
                 "STG": "Short term / slab", None: "Manual treatment"}
        for r, t in enumerate(tx):
            bad = t["cost"] is None or t["zero"]
            flag = "User input" if t["user"] else ("Cost not shown in AIS" if bad else "OK")
            vals = [t["date"] or "-", clean_security(t["name"]), t["asset"] or "-", names.get(t["sec"], "Manual treatment"),
                    "" if t["qty"] is None else str(q0(t["qty"])), money(t["sale"], "Rs "),
                    "" if t["cost"] is None else str(q0(t["cost"])),
                    "-" if t["gain"] is None else money(t["gain"], "Rs "), flag]
            for ci, text in enumerate(vals):
                item = QTableWidgetItem(text)
                if ci != 6:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                else:
                    item.setData(Qt.ItemDataRole.UserRole, t["id"])
                if ci >= 4 and ci != 8:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if bad and not t["user"]:
                    item.setBackground(QColor("#FFC9C9"))
                    item.setForeground(QColor("#7a0f0f"))
                elif ci == 8:
                    item.setBackground(QColor("#CFF5E7") if flag == "OK" else QColor("#FFE8A3"))
                    item.setForeground(QColor("#1F3864"))
                table.setItem(r, ci, item)
        table.resizeColumnsToContents()
        self._busy = False

    def _cg_edited(self, item):
        if self._busy or item.column() != 6:
            return
        rid = item.data(Qt.ItemDataRole.UserRole)
        if rid is None:
            return
        costs = self.case["profile"].setdefault("cg_cost", {})
        text = item.text().replace(",", "").strip()
        try:
            if text:
                costs[str(rid)] = int(Decimal(text))
            else:
                costs.pop(str(rid), None)
        except Exception:
            costs.pop(str(rid), None)
        self._changed()

    # ---------------------------------------------------------------- additional inputs + profile tab
    def _build_inputs_tab(self):
        self.iw = {}

        def num(key):
            box = QDoubleSpinBox()
            box.setDecimals(0)
            box.setRange(0, 1e12)
            box.setSingleStep(1000)
            box.setGroupSeparatorShown(True)
            box.valueChanged.connect(lambda _v: self._changed())
            self.iw[key] = box
            return box

        def check(key, text):
            box = QCheckBox(text)
            box.toggled.connect(lambda _s: self._changed())
            self.iw[key] = box
            return box

        def combo(key, items):
            box = QComboBox()
            box.addItems(items)
            box.currentIndexChanged.connect(lambda _i: self._changed())
            self.iw[key] = box
            return box
        groups = [
            ("Taxpayer profile and deductions", [
                ("Residential status", combo("resident", ["Resident", "RNOR", "Non-resident"])),
                ("Age group used", combo("age_choice", ["Auto", "Below 60", "Senior (60-79)", "Super senior (80+)"])),
                ("Regime used in the report", combo("regime_choice", ["Auto", "Old", "New"])),
                ("", check("include_inactive", "Include 'Inactive' AIS rows in income and tax credits")),
                ("Old-regime deductions, Chapter VI-A (Rs)", num("ded_old")),
                ("New-regime deductions, e.g. 80CCD(2) (Rs)", num("ded_new")),
                ("Brought-forward short-term capital loss (Rs)", num("bf_stcl")),
                ("Brought-forward long-term capital loss (Rs)", num("bf_ltcl"))]),
            ("House property", [
                ("Rent received (0 = use AIS amount)", num("hp_rent")), ("Municipal taxes paid", num("hp_muni")),
                ("Interest on loan, let-out property s.24(b)", num("hp_int")),
                ("Interest, self-occupied property (cap Rs 2,00,000; old regime)", num("hp_so_int"))]),
            ("Business / profession", [
                ("Computation method", combo("biz_scheme", BIZ_SCHEMES)),
                ("Gross receipts (0 = use AIS business amount)", num("biz_receipts")),
                ("of which received digitally (44AD at 6%)", num("biz_digital")),
                ("Expenses (books-based method)", num("biz_exp")),
                ("44AE: light goods vehicle-months", num("ae_light")),
                ("44AE: heavy vehicle tonne-months", num("ae_heavy"))]),
            ("Sale of land / building", [
                ("", check("prop_on", "Include a property sale")), ("Sale consideration", num("prop_sale")),
                ("Cost of acquisition", num("prop_cost")), ("Cost of improvement", num("prop_improve")),
                ("Transfer expenses", num("prop_exp")),
                ("Financial year of acquisition (for CII)", combo("prop_cost_fy", sorted(CII))),
                ("", check("prop_long", "Held more than 24 months (long term)")),
                ("", check("prop_before_jul24", "Acquired before 23-Jul-2024 (20% indexed vs 12.5% choice)")),
                ("", check("prop_pre_sale", "Sold before 23-Jul-2024 (FY 2024-25 only)")),
                ("Exemption claimed s.54 / 54F (cap Rs 10 crore)", num("prop_exempt"))]),
        ]
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setSpacing(14)
        for title, fields in groups:
            body_layout.addWidget(QLabel(title, objectName="cardTitle"))
            form = QFormLayout()
            form.setHorizontalSpacing(24)
            for label, widget in fields:
                form.addRow(label, widget)
            body_layout.addLayout(form)
        body_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(body)
        self.tabs.addTab(scroll, "Inputs and deductions")

    def _load_inputs(self):
        profile = self.case["profile"]
        for key, widget in self.iw.items():
            if isinstance(widget, QCheckBox):
                widget.setChecked(bool(profile[key]))
            elif isinstance(widget, QComboBox):
                widget.setCurrentText(str(profile[key]))
            else:
                widget.setValue(float(profile[key]))

    def _read_inputs(self):
        profile = self.case["profile"]
        for key, widget in self.iw.items():
            if isinstance(widget, QCheckBox):
                profile[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                profile[key] = widget.currentText()
            else:
                profile[key] = int(widget.value())
        if profile["include_inactive"] != self._last_inactive:
            self._last_inactive = profile["include_inactive"]
            refresh_defaults(self.case["groups"], profile["include_inactive"])
            QTimer.singleShot(0, self._fill_income)

    # ---------------------------------------------------------------- recompute / report / buttons
    def _changed(self, rebuild_income=False):
        if self._busy:
            return
        self._read_inputs()
        try:
            self.res = compute_case(self.case)
        except Exception as exc:
            self.status.setText(f"Could not recompute: {exc}")
            return
        self.dirty = True
        self.status.setText("Computation updated. The Word report is refreshed when you click Update, Open or Send.")
        self._refresh_summary()
        QTimer.singleShot(0, self._fill_cg)
        if rebuild_income:
            QTimer.singleShot(0, self._fill_income)

    def _regenerate(self):
        """Rebuild the Word report from the edited computation, replacing the saved file."""
        folder = Path(tempfile.mkdtemp(prefix="ais_review_"))
        try:
            built = Path(build_report(self.case, self.res, str(folder)))
            shutil.copy2(built, self.report_path)
            self.dirty = False
            self.status.setText("Word report updated with your edits.")
            return True
        except PermissionError:
            QMessageBox.warning(
                self, "Word report is open",
                "The saved Word report is open in Word. Close it and try again.",
            )
            return False
        except Exception as exc:
            QMessageBox.warning(self, "Update report", f"Could not update the Word report:\n{exc}")
            return False
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def _open_report(self):
        if self.dirty and not self._regenerate():
            return
        try:
            os.startfile(self.report_path)          # Windows
        except Exception as exc:
            QMessageBox.warning(self, "Open report", f"Could not open the report:\n{exc}")

    def _send(self):
        if self.dirty and not self._regenerate():
            return
        self.final_summary = review_summary(self.case, self.res)
        self.accept()

    def reject(self):
        """'Do not send' or closing the window: keep the edits in the saved Word report."""
        if self.dirty:
            self._regenerate()
        self.final_summary = review_summary(self.case, self.res)
        super().reject()


class StepRow(QFrame):
    def __init__(self, number, title, subtitle, parent=None):
        super().__init__(parent)
        self.number = number
        self.setObjectName("stepRow")
        self.setProperty("state", "pending")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 9)
        layout.setSpacing(12)
        self.setMinimumHeight(60)
        self.badge = QLabel(str(number), objectName="stepBadge")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setFixedSize(30, 30)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        self.title_label = QLabel(title, objectName="stepTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setMinimumHeight(18)
        self.subtitle_label = QLabel(subtitle, objectName="stepSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setMinimumHeight(16)
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.subtitle_label)
        layout.addWidget(self.badge)
        layout.addLayout(text_layout, 1)
        self.set_state("pending")

    def set_state(self, state):
        self.setProperty("state", state)
        self.badge.setProperty("state", state)
        self.title_label.setProperty("state", state)
        self.subtitle_label.setProperty("state", state)
        self.badge.setText(
            "✓" if state == "done" else "!" if state == "error" else str(self.number)
        )
        self.refresh_style()

    def refresh_style(self):
        for widget in (self, self.badge, self.title_label, self.subtitle_label):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()


_LIGHT = {
    "bg": "#f4f7fb", "surface": "#ffffff", "surface_alt": "#f8fafc",
    "text": "#172033", "muted": "#667085", "border": "#d9e2ef",
    "input_bg": "#ffffff", "primary_start": "#6d3df5",
    "primary_end": "#2563eb", "primary_hover": "#4f46e5",
    "secondary_bg": "#e8efff", "secondary_hover": "#d9e5ff",
    "secondary_text": "#2948a3", "ghost_bg": "#f0f3f8",
    "ghost_hover": "#e3e8f0", "ghost_text": "#344054",
    "danger": "#e11d48", "danger_hover": "#be123c",
    "danger_soft": "#fff0f3", "danger_text": "#b42318",
    "progress_bg": "#d8e2f2", "progress_text": "#172033",
    "log_bg": "#101827", "log_text": "#b8f7d4", "log_border": "#1f2937",
    "scroll_track": "#edf1f7", "scroll_handle": "#b9c6da",
    "scroll_hover": "#91a4c0", "pill_ready_bg": "#e8eef8",
    "pill_ready_text": "#475467", "pill_running_bg": "#e8efff",
    "pill_running_text": "#2455c3", "pill_action_bg": "#fff4d8",
    "pill_action_text": "#9a6700", "pill_completed_bg": "#dcfce7",
    "pill_completed_text": "#15703d", "pill_failed_bg": "#fee2e2",
    "pill_failed_text": "#b42318", "pill_stopped_bg": "#edf0f5",
    "pill_stopped_text": "#475467", "side_start": "#151a2f",
    "side_end": "#202a48", "side_text": "#f8fafc",
    "side_muted": "#aebbd0", "side_card": "rgba(255, 255, 255, 0.07)",
    "step_pending_bg": "rgba(255, 255, 255, 0.04)", "step_pending_border": "#73809a",
    "step_pending_text": "#b8c3d6", "step_active_start": "#7652f5",
    "step_active_end": "#2585ee", "step_active_text": "#ffffff",
    "step_done_bg": "#1fbf78", "step_done_text": "#ffffff",
    "step_error_bg": "#ef4444", "step_error_text": "#ffffff",
    "chevron_color": "#667085", "chevron": "", "shadow": "#261f2933",
}
_DARK_OVERRIDES = {
    "bg": "#0b1020", "surface": "#151c2f", "surface_alt": "#1b2438",
    "text": "#eef2ff", "muted": "#9daac0", "border": "#2b3852",
    "input_bg": "#11192a", "secondary_bg": "#253557",
    "secondary_hover": "#30456f", "secondary_text": "#dbe7ff",
    "ghost_bg": "#202b42", "ghost_hover": "#2b3852",
    "ghost_text": "#e3e9f4", "danger_soft": "#401b29",
    "danger_text": "#fecdd3", "progress_bg": "#27344c",
    "progress_text": "#eef2ff", "scroll_track": "#111827",
    "scroll_handle": "#3d4d69", "scroll_hover": "#536885",
    "pill_ready_bg": "#27344c", "pill_ready_text": "#c6d0df",
    "pill_running_bg": "#223c70", "pill_running_text": "#c9dcff",
    "pill_action_bg": "#4b3915", "pill_action_text": "#ffe3a1",
    "pill_completed_bg": "#173c2a", "pill_completed_text": "#a7f3d0",
    "pill_failed_bg": "#4a2027", "pill_failed_text": "#fecaca",
    "pill_stopped_bg": "#27344c", "pill_stopped_text": "#c6d0df",
    "chevron_color": "#aebbd0", "shadow": "#66000000",
}
_OCEAN_OVERRIDES = {
    "bg": "#eaf7fb", "surface_alt": "#f0fbfd", "text": "#113548",
    "muted": "#557483", "border": "#bcdde6", "input_bg": "#fbfeff",
    "primary_start": "#0f8fa8", "primary_hover": "#087f96",
    "secondary_bg": "#dff5f8", "secondary_hover": "#ccecf1",
    "secondary_text": "#0f6073", "ghost_bg": "#e9f6f8",
    "ghost_hover": "#d8eef2", "ghost_text": "#28596a",
    "progress_bg": "#cce8ee", "progress_text": "#113548",
    "scroll_track": "#e1f1f4", "scroll_handle": "#8fc5d0",
    "scroll_hover": "#67adbb", "pill_ready_bg": "#e0f1f4",
    "pill_ready_text": "#3e6570", "pill_running_bg": "#d8f3f6",
    "pill_running_text": "#08798f", "pill_action_bg": "#fff2cc",
    "pill_action_text": "#8c6500", "pill_completed_bg": "#d8f6e8",
    "pill_completed_text": "#12653c", "pill_failed_bg": "#ffe0e5",
    "pill_failed_text": "#a91d3d", "pill_stopped_bg": "#dfecee",
    "pill_stopped_text": "#3e6570", "chevron_color": "#557483",
    "shadow": "#2e14566b",
}
_EMERALD = {
    "bg": "#effaf4", "surface_alt": "#f3fcf7", "text": "#0f2e22", "muted": "#4f6f61", "border": "#c4e6d3",
    "input_bg": "#fbfffd", "primary_start": "#059669", "primary_end": "#0d9488", "primary_hover": "#047857",
    "secondary_bg": "#d9f5e6", "secondary_hover": "#c5eed9", "secondary_text": "#0b6b47",
    "ghost_bg": "#e7f7ee", "ghost_hover": "#d5f0e1", "ghost_text": "#265a44", "progress_bg": "#cdebdc",
    "progress_text": "#0f2e22", "scroll_track": "#e0f3e9", "scroll_handle": "#8fcfad", "scroll_hover": "#66bb91",
    "side_start": "#052e22", "side_end": "#0b4a3a", "step_active_start": "#10b981", "step_active_end": "#0d9488",
    "chevron_color": "#4f6f61", "shadow": "#2e0b4a3a",
}
_ROYAL = {
    "bg": "#f6f1fd", "surface_alt": "#faf6ff", "text": "#2a1450", "muted": "#6c5a8a", "border": "#e0d3f3",
    "input_bg": "#fdfbff", "primary_start": "#7c3aed", "primary_end": "#c026d3", "primary_hover": "#6d28d9",
    "secondary_bg": "#ece2fb", "secondary_hover": "#e0d0f8", "secondary_text": "#5b21b6",
    "ghost_bg": "#f0e9fb", "ghost_hover": "#e5daf7", "ghost_text": "#4a2f78", "progress_bg": "#e0d3f3",
    "progress_text": "#2a1450", "scroll_track": "#eee6fa", "scroll_handle": "#c3a8ee", "scroll_hover": "#a98be0",
    "side_start": "#1e0f3d", "side_end": "#3b1a6e", "step_active_start": "#8b5cf6", "step_active_end": "#d946ef",
    "chevron_color": "#6c5a8a", "shadow": "#2e3b1a6e",
}
_SUNSET = {
    "bg": "#fff5ec", "surface_alt": "#fff9f3", "text": "#3a1d0b", "muted": "#8a6246", "border": "#f3d9c3",
    "input_bg": "#fffdfb", "primary_start": "#f97316", "primary_end": "#e11d48", "primary_hover": "#ea580c",
    "secondary_bg": "#ffe8d4", "secondary_hover": "#ffdcbf", "secondary_text": "#9a3d07",
    "ghost_bg": "#fdeedd", "ghost_hover": "#f9e0c9", "ghost_text": "#6b3a1c", "progress_bg": "#f5dcc6",
    "progress_text": "#3a1d0b", "scroll_track": "#fbeadb", "scroll_handle": "#e8b891", "scroll_hover": "#dc9d6c",
    "side_start": "#3a1408", "side_end": "#6a2410", "step_active_start": "#f97316", "step_active_end": "#e11d48",
    "chevron_color": "#8a6246", "shadow": "#2e6a2410",
}
_ROSE = {
    "bg": "#fdf2f4", "surface_alt": "#fff7f8", "text": "#3b1220", "muted": "#8a5a68", "border": "#f2d4db",
    "input_bg": "#fffcfc", "primary_start": "#db2777", "primary_end": "#e5874b", "primary_hover": "#be185d",
    "secondary_bg": "#fde3e9", "secondary_hover": "#fbd3dc", "secondary_text": "#9d174d",
    "ghost_bg": "#fbebee", "ghost_hover": "#f7dce2", "ghost_text": "#6b2a3d", "progress_bg": "#f3d7de",
    "progress_text": "#3b1220", "scroll_track": "#fae6ea", "scroll_handle": "#e8aebb", "scroll_hover": "#da8fa1",
    "side_start": "#3b0f22", "side_end": "#6b1d3d", "step_active_start": "#ec4899", "step_active_end": "#f59e0b",
    "chevron_color": "#8a5a68", "shadow": "#2e6b1d3d",
}
_MIDNIGHT = {
    "bg": "#070b1a", "surface": "#0f1730", "surface_alt": "#152040", "border": "#26335a", "input_bg": "#0b1226",
    "primary_start": "#3b82f6", "primary_end": "#22d3ee", "primary_hover": "#2563eb",
    "secondary_bg": "#1c2c57", "secondary_hover": "#273b73", "secondary_text": "#cfe2ff",
    "ghost_bg": "#18244a", "ghost_hover": "#22315f", "side_start": "#050816", "side_end": "#0d1a3f",
    "step_active_start": "#3b82f6", "step_active_end": "#22d3ee",
}
_GRAPHITE = {
    "bg": "#121212", "surface": "#1c1c1f", "surface_alt": "#242428", "text": "#f3f4f6", "muted": "#a1a1aa",
    "border": "#34343a", "input_bg": "#18181b", "primary_start": "#d97706", "primary_end": "#ea580c",
    "primary_hover": "#c2410c", "secondary_bg": "#33333a", "secondary_hover": "#40404a",
    "secondary_text": "#fde68a", "ghost_bg": "#2a2a30", "ghost_hover": "#36363e", "ghost_text": "#e5e7eb",
    "progress_bg": "#34343a", "side_start": "#0c0c0e", "side_end": "#1f1f24", "step_active_start": "#f59e0b",
    "step_active_end": "#ea580c", "scroll_track": "#18181b", "scroll_handle": "#4b4b55", "scroll_hover": "#63636f",
}
THEMES = {
    "Light": _LIGHT,
    "Dark": {**_LIGHT, **_DARK_OVERRIDES},
    "Ocean": {**_LIGHT, **_OCEAN_OVERRIDES},
    "Emerald": {**_LIGHT, **_EMERALD},
    "Royal Purple": {**_LIGHT, **_ROYAL},
    "Sunset": {**_LIGHT, **_SUNSET},
    "Rose Gold": {**_LIGHT, **_ROSE},
    "Midnight": {**_LIGHT, **_DARK_OVERRIDES, **_MIDNIGHT},
    "Graphite": {**_LIGHT, **_DARK_OVERRIDES, **_GRAPHITE},
}

STYLE_TEMPLATE = """
QMainWindow, QDialog, QWidget#root, QWidget#mainContent { background-color: @bg@; }
QWidget { color: @text@; font-family: "Segoe UI"; font-size: 10pt; }
QScrollArea#mainScroll { background-color: @bg@; border: none; }
QTabWidget#mainTabs::pane { border: none; background-color: @bg@; }
QTabWidget#mainTabs QTabBar::tab {
    color: @muted@; background-color: @surface_alt@; border: none;
    border-bottom: 2px solid transparent; padding: 11px 22px; font-weight: 700;
}
QTabWidget#mainTabs QTabBar::tab:selected {
    color: @primary_end@; background-color: @surface@;
    border-bottom: 2px solid @primary_end@;
}
QTabWidget#mainTabs QTabBar::tab:hover { color: @text@; background-color: @ghost_hover@; }
QFrame#sidePanel {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 @side_start@, stop:1 @side_end@); border: none;
}
QFrame#logoBadge {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 @step_active_start@, stop:1 @step_active_end@);
    border-radius: 12px;
}
QLabel#logoText { background-color: transparent; color: @side_text@; font-size: 12pt; font-weight: 800; }
QLabel#sideTitle { color: @side_text@; font-size: 12pt; font-weight: 750; }
QLabel#sideTag, QLabel#versionLabel { color: @side_muted@; font-size: 8.5pt; }
QLabel#workflowHeading { color: @side_muted@; font-size: 8pt; font-weight: 750; letter-spacing: 1px; padding-top: 6px; }
QFrame#stepRow { background-color: transparent; border: 1px solid transparent; border-radius: 11px; }
QFrame#stepRow[state="active"] { background-color: @side_card@; border-color: rgba(255, 255, 255, 0.13); }
QFrame#stepRow[state="error"] { background-color: rgba(239, 68, 68, 0.11); border-color: rgba(239, 68, 68, 0.33); }
QLabel#stepBadge {
    color: @step_pending_text@; background-color: @step_pending_bg@;
    border: 1px solid @step_pending_border@; border-radius: 15px; font-weight: 750;
}
QLabel#stepBadge[state="active"] {
    color: @step_active_text@; background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
    stop:0 @step_active_start@, stop:1 @step_active_end@); border: none;
}
QLabel#stepBadge[state="done"] { color: @step_done_text@; background-color: @step_done_bg@; border: none; }
QLabel#stepBadge[state="error"] { color: @step_error_text@; background-color: @step_error_bg@; border: none; }
QLabel#stepTitle { color: @step_pending_text@; font-size: 10pt; font-weight: 700; }
QLabel#stepTitle[state="active"], QLabel#stepTitle[state="done"], QLabel#stepTitle[state="error"] { color: @side_text@; }
QLabel#stepSubtitle { color: @side_muted@; font-size: 8.6pt; }
QFrame#privacyCard { background-color: @side_card@; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; }
QLabel#privacyTitle { color: @side_text@; font-weight: 700; }
QLabel#privacyText { color: @side_muted@; font-size: 8.5pt; }
QLabel#pageTitle { font-size: 20pt; font-weight: 780; color: @text@; }
QLabel#pageSubtitle, QLabel#cardCaption, QLabel#activityHint, QLabel#inlineHint, QLabel#footer { color: @muted@; }
QLabel#smallLabel, QLabel#fieldLabel { color: @muted@; font-size: 8.8pt; font-weight: 650; }
QLabel#cardTitle, QLabel#sectionTitle { color: @text@; font-size: 13pt; font-weight: 750; }
QFrame#clientCard, QFrame#formCard { background-color: @surface@; border: 1px solid @border@; border-radius: 18px; }
QFrame#emailPanel { background-color: @surface_alt@; border: 1px solid @border@; border-radius: 13px; }
QLabel#gmailStatus { color: @secondary_text@; font-size: 8.8pt; font-weight: 700; }
QFrame#progressCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
    stop:0 @side_start@, stop:1 @side_end@);
    border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 17px;
}
QLabel#stageCaption { color: @side_muted@; font-size: 8pt; font-weight: 750; letter-spacing: 1px; }
QLabel#statusLabel { color: @side_text@; font-size: 12pt; font-weight: 700; }
QLineEdit, QComboBox {
    color: @text@; background-color: @input_bg@; border: 1px solid @border@;
    border-radius: 10px; padding: 0 12px; selection-background-color: @primary_end@;
}
QLineEdit:focus, QComboBox:focus { border: 2px solid @primary_end@; }
QLineEdit:disabled, QComboBox:disabled { color: @muted@; background-color: @surface_alt@; }
QComboBox { padding-right: 34px; }
QComboBox::drop-down { width: 30px; border: none; }
QComboBox::down-arrow { image: url("@chevron@"); width: 12px; height: 8px; }
QComboBox QAbstractItemView {
    color: @text@; background-color: @surface@; border: 1px solid @border@;
    selection-color: @text@; selection-background-color: @secondary_bg@; outline: none;
}
QPushButton { border: none; border-radius: 10px; padding: 0 16px; font-weight: 700; }
QPushButton#primaryButton {
    color: #ffffff; background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop:0 @primary_start@, stop:1 @primary_end@); font-size: 11pt;
}
QPushButton#primaryButton:hover { background-color: @primary_hover@; }
QPushButton#secondaryButton { color: @secondary_text@; background-color: @secondary_bg@; }
QPushButton#secondaryButton:hover { background-color: @secondary_hover@; }
QPushButton#ghostButton { color: @ghost_text@; background-color: @ghost_bg@; border: 1px solid @border@; }
QPushButton#ghostButton:hover, QPushButton#ghostButton:checked { background-color: @ghost_hover@; }
QPushButton#dangerButton { color: #ffffff; background-color: @danger@; }
QPushButton#dangerButton:hover { background-color: @danger_hover@; }
QPushButton#dangerSoftButton { color: @danger@; background-color: @pill_failed_bg@; border: 1px solid @danger@; }
QPushButton#dangerSoftButton:hover { color: #ffffff; background-color: @danger@; }
QPushButton:disabled { color: @muted@; background-color: @surface_alt@; border: 1px solid @border@; }
QCheckBox { color: @text@; spacing: 8px; font-weight: 600; }
QCheckBox::indicator {
    width: 17px; height: 17px; border: 1px solid @border@;
    border-radius: 5px; background-color: @input_bg@;
}
QCheckBox::indicator:checked { background-color: @primary_end@; border-color: @primary_end@; }
QLabel#statusPill { border-radius: 15px; padding: 0 14px; font-size: 8pt; font-weight: 800; }
QLabel#statusPill[state="ready"] { color: @pill_ready_text@; background-color: @pill_ready_bg@; }
QLabel#statusPill[state="running"] { color: @pill_running_text@; background-color: @pill_running_bg@; }
QLabel#statusPill[state="action"] { color: @pill_action_text@; background-color: @pill_action_bg@; }
QLabel#statusPill[state="completed"] { color: @pill_completed_text@; background-color: @pill_completed_bg@; }
QLabel#statusPill[state="failed"] { color: @pill_failed_text@; background-color: @pill_failed_bg@; }
QLabel#statusPill[state="stopped"] { color: @pill_stopped_text@; background-color: @pill_stopped_bg@; }
QProgressBar {
    color: @progress_text@; background-color: @progress_bg@; border: none;
    border-radius: 9px; text-align: center; font-size: 8pt; font-weight: 700;
}
QProgressBar::chunk {
    border-radius: 9px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop:0 @primary_start@, stop:1 @primary_end@);
}
QTextEdit {
    color: @log_text@; background-color: @log_bg@; border: 1px solid @log_border@;
    border-radius: 14px; padding: 12px; font-family: "Cascadia Mono", "Consolas"; font-size: 9pt;
}
QTableWidget {
    color: @text@; background-color: @surface@; alternate-background-color: @surface_alt@;
    border: 1px solid @border@; border-radius: 10px; gridline-color: @border@;
    selection-color: @text@; selection-background-color: @secondary_bg@;
}
QHeaderView::section {
    color: @text@; background-color: @surface_alt@; border: none;
    border-bottom: 1px solid @border@; padding: 8px; font-weight: 700;
}
QScrollBar:vertical { background-color: @scroll_track@; width: 10px; margin: 2px; border-radius: 5px; }
QScrollBar::handle:vertical { background-color: @scroll_handle@; min-height: 32px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background-color: @scroll_hover@; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; border: none; }
QMessageBox { background-color: @surface@; }
QMessageBox QLabel { color: @text@; min-width: 320px; }
QMessageBox QPushButton {
    color: @secondary_text@; background-color: @secondary_bg@;
    min-width: 88px; min-height: 34px;
}
"""


def main():
    # High-DPI behavior is automatic in Qt 6.
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("AIS Automation")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

