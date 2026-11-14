# -*- coding: utf-8 -*-
"""
GSTwithNihal Redaction Tool
===========================
Permanently redacts personal information from PDF files (true redaction: the
underlying text / image pixels are removed, not just covered by a black box).

How to run
    * IDLE  : open this file and press F5 (Run Module).
    * CMD   : python gstwithnihal_redaction_tool.py
    * CLI   : python gstwithnihal_redaction_tool.py a.pdf b.pdf -o out [--ocr] [--names names.txt]

On the first run the script installs the Python libraries it needs
(pymupdf, PyQt6, pytesseract, pillow) automatically - this can take a few
minutes and needs an internet connection. Manual fallback, if ever needed:
    python -m pip install pymupdf PyQt6 pytesseract pillow

OCR of scanned / image-only PDFs additionally needs the free Tesseract OCR
program (Windows: UB-Mannheim build). Everything else works without it.

Detection = three layers
    1. Pattern rules   : PAN, GSTIN, Aadhaar/VID, phone, e-mail, UPI, card, IP ...
    2. Label / layout  : "Name:", "Address:", "Legal Name", "Trade Name", "To," /
                         "Bill To" / "Ship To" / "Consignee" blocks, "M/s." lines ...
    3. Your own list   : names typed in the window (matched anywhere, also across
                         a line break)
Everything found in layers 1-3 is then searched again on every page of the same
document, so a name or address redacted once is redacted everywhere.

NEVER redacted (protected, always wins over the rules above):
    * case-law party names and citations   (X Vs. Y, (2019) 13 SCC 225, AIR ..., GSTL ...)
    * bare statutory provisions, section / rule / notification references, Act names
    * officer names, designations and jurisdiction (Superintendent, Range, Division, Commissionerate,
      digital-signature blocks) - the officer's name is also kept everywhere else in the document
    * long quoted passages (judgment / statute extracts)

No software can promise 100 % on free text. Always read the summary and spot-check
the output PDF before sharing it.
"""
from __future__ import annotations

import csv
import importlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import warnings
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

warnings.filterwarnings("ignore", message=".*fitz.*", category=FutureWarning)

APP_NAME = "GSTwithNihal Redaction Tool"

# --------------------------------------------------------------------------- #
# Automatic installation of the required libraries
# --------------------------------------------------------------------------- #
#   (import name, pip package name, required?)
REQUIRED_PACKAGES = [
    ("pymupdf", "pymupdf", True),        # PDF reading / true redaction
    ("PyQt6", "PyQt6", True),            # window interface
    ("pytesseract", "pytesseract", False),  # OCR bridge (optional)
    ("PIL", "pillow", False),            # images for OCR (optional)
]
PIP_LINE = "python -m pip install pymupdf PyQt6 pytesseract pillow"


def _python_for_pip() -> str:
    """IDLE on Windows may run under pythonw.exe; use python.exe next to it for pip."""
    exe = sys.executable or "python"
    if os.path.basename(exe).lower() == "pythonw.exe":
        cand = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.isfile(cand):
            return cand
    return exe


def _module_present(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _run_quiet(cmd: List[str]) -> subprocess.CompletedProcess:
    kw = {"capture_output": True, "text": True}
    if os.name == "nt":
        kw["creationflags"] = 0x08000000          # CREATE_NO_WINDOW: no black console flashes
    return subprocess.run(cmd, **kw)


def ensure_packages() -> bool:
    """Install any missing library with pip. Returns False only if a REQUIRED one is still missing."""
    missing = [(mod, pkg, req) for mod, pkg, req in REQUIRED_PACKAGES if not _module_present(mod)]
    if not missing:
        return True
    names = [pkg for _, pkg, _ in missing]
    py = _python_for_pip()
    print(f"{APP_NAME}: installing missing libraries: {', '.join(names)}")
    print("First run only - this can take a few minutes, please wait ...")
    if _run_quiet([py, "-m", "pip", "--version"]).returncode != 0:
        _run_quiet([py, "-m", "ensurepip", "--upgrade"])
    base = [py, "-m", "pip", "install", "--disable-pip-version-check", "--no-input"]
    attempts = [[], ["--user"]]
    if os.name != "nt":
        attempts.append(["--user", "--break-system-packages"])
    last = None
    for extra in attempts:
        last = _run_quiet(base + extra + names)
        if last.returncode == 0:
            break
    importlib.invalidate_caches()
    try:                                           # make a freshly created user site visible
        import site
        usp = site.getusersitepackages()
        if os.path.isdir(usp) and usp not in sys.path:
            site.addsitedir(usp)
    except Exception:
        pass
    still = [(mod, pkg, req) for mod, pkg, req in REQUIRED_PACKAGES if not _module_present(mod)]
    if not still:
        print("All libraries installed.\n")
        return True
    if last is not None and last.returncode != 0:
        tail = (last.stderr or last.stdout or "").strip().splitlines()[-6:]
        print("pip reported:\n   " + "\n   ".join(tail))
    hard = [pkg for _, pkg, req in still if req]
    soft = [pkg for _, pkg, req in still if not req]
    if soft:
        print("Optional OCR libraries not installed (" + ", ".join(soft) + ") - OCR will be unavailable.")
    if hard:
        print("\nCould not install: " + ", ".join(hard))
        print("Open Command Prompt and run:\n   " + PIP_LINE)
        return False
    return True


def _import_fitz():
    try:
        import pymupdf as fitz            # PyMuPDF >= 1.24
    except ImportError:
        import fitz                       # older PyMuPDF
    return fitz


# --------------------------------------------------------------------------- #
# Categories (shown as check-boxes in the window)
# --------------------------------------------------------------------------- #
CATEGORIES = [
    ("names", "Names of individuals",
     "Name, Proprietor, Partner, Director, Signatory, Legal/Authorised Representative, "
     "Mr/Mrs/Shri/Smt/Dr titles, S/o D/o W/o"),
    ("business", "Business names (Trade / Legal names)",
     "Trade Name, Legal Name, 'M/s.' lines, names ending Pvt Ltd / LLP / Enterprises / Traders ..."),
    ("blocks", "To / Bill To / Ship To / Consignee blocks",
     "The whole party block (name + address lines) under such a heading"),
    ("address", "Addresses (incl. PIN code)",
     "Address labels, registered / principal place of business, any line with a PIN code"),
    ("pan", "PAN", "Pattern + 'PAN:' label"),
    ("gstin", "GSTIN / UIN", "Pattern + 'GSTIN:' label (also removes the PAN hidden inside)"),
    ("aadhaar", "Aadhaar / VID / Enrolment ID", "Pattern (checksum) + label"),
    ("govt_ids", "Other IDs",
     "Passport, Driving Licence, Voter ID, Ration Card, UAN, PF/ESIC, ABHA, DIN, TAN, Udyam, "
     "IEC, vehicle no., employee / roll / customer ID"),
    ("phone", "Phone / mobile / fax numbers", "Indian mobile and landline formats + labels"),
    ("email", "E-mail addresses", "Pattern + 'Email:' label"),
    ("financial", "Bank account, UPI, card, loan / policy no., salary",
     "Labelled account numbers, UPI IDs, card numbers (Luhn check), salary / income labels"),
    ("demographic", "DOB, age, gender, religion, caste, marital status ...",
     "Labelled fields only"),
    ("digital", "IP address, IMEI, device ID, GPS, usernames", ""),
    ("manual", "My own list of names", "Names typed in the box in the window"),
]
CAT_LABEL = {k: v for k, v, _ in CATEGORIES}


@dataclass
class Config:
    cats: Dict[str, bool] = field(default_factory=lambda: {k: True for k, _, _ in CATEGORIES})
    company_suffix: bool = True        # redact "<Words> Pvt Ltd / LLP / Enterprises ..." anywhere
    manual_names: List[str] = field(default_factory=list)
    protect_citations: bool = True     # case-law names + citations are NEVER redacted
    protect_statutes: bool = True      # bare provisions / section references are NEVER redacted
    protect_officers: bool = True      # officer names, designations and jurisdiction are NEVER redacted
    protect_quotes: bool = True        # long quoted passages (judgments / statute extracts)
    flatten_forms: bool = True         # flatten form fields / comments so they can be redacted
    strip_metadata: bool = True
    ocr: bool = True                   # automatic: scanned pages + pictures are read when OCR is available
    ocr_all_image_pages: bool = False  # False = only pages with (almost) no text layer
    ocr_lang: str = "eng"
    ocr_dpi: int = 300
    ocr_psm: int = 3
    tesseract_cmd: str = ""

    def enabled(self, cat: str) -> bool:
        return self.cats.get(cat, True)


# --------------------------------------------------------------------------- #
# Small helpers: checksums
# --------------------------------------------------------------------------- #
_VD = [[0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],
       [3,4,0,1,2,8,9,5,6,7],[4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],
       [6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],[8,7,6,5,9,3,2,1,0,4],
       [9,8,7,6,5,4,3,2,1,0]]
_VP = [[0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],
       [8,9,1,6,0,4,3,5,2,7],[9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],
       [2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]]


def verhoeff_ok(num: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(num)):
        c = _VD[c][_VP[i % 8][int(ch)]]
    return c == 0


def luhn_ok(num: str) -> bool:
    s, alt = 0, False
    for ch in reversed(num):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        s += d
        alt = not alt
    return s % 10 == 0


# --------------------------------------------------------------------------- #
# Pattern rules  (category, regex, validator)
# --------------------------------------------------------------------------- #
I = re.IGNORECASE
_AADHAAR_CTX = re.compile(r"aadh?a+r|uidai|\buid\b|enrol", I)
_VID_CTX = re.compile(r"\bvid\b|virtual\s+id", I)


def _v_aadhaar(m, t):
    d = re.sub(r"\D", "", m.group(0))
    return len(d) == 12 and (verhoeff_ok(d) or bool(_AADHAAR_CTX.search(t)))


def _v_vid(m, t):
    return bool(_VID_CTX.search(t)) or bool(_AADHAAR_CTX.search(t))


def _v_card(m, t):
    d = re.sub(r"\D", "", m.group(0))
    if _VID_CTX.search(t) or not (13 <= len(d) <= 19):
        return False
    return luhn_ok(d)


_IP_CTX = re.compile(r"\bip\b|i\.p\.|internet\s+protocol|server|log-?in|logged|device|host", I)


def _v_ip(m, t):
    return all(int(x) <= 255 for x in m.group(0).split(".")) and bool(_IP_CTX.search(t))


REGEX_RULES = [
    ("gstin", re.compile(r"(?<![A-Za-z0-9])\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z](?![A-Za-z0-9])", I), None),
    ("pan", re.compile(r"(?<![A-Za-z0-9])[A-Z]{5}\d{4}[A-Z](?![A-Za-z0-9])", I), None),
    # GSTIN read by OCR with 0/O, 1/I/l mixed up in the number part
    ("gstin", re.compile(r"(?<![A-Za-z0-9])[0-9OIlJSBGQD]{2}[A-Z]{5}[0-9OIlJSBGQD]{4}[A-Z][0-9A-Z][Z2][0-9A-Z]"
                         r"(?![A-Za-z0-9])"), None),
    ("aadhaar", re.compile(r"(?<![\d-])[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?![\d-])"), _v_aadhaar),
    ("aadhaar", re.compile(r"(?<![\d-])\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}(?![\d-])"), _v_vid),
    ("aadhaar", re.compile(r"(?<!\d)\d{4}/\d{5}/\d{5}(?!\d)"), None),
    ("phone", re.compile(r"(?<![\w/-])(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"), None),
    ("phone", re.compile(r"(?<![\w/-])\(?0\d{2,4}\)?[\s-]\d{6,8}(?!\d)"), None),
    ("phone", re.compile(r"(?<![\w/])\+91[\s-]?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{4}(?!\d)"), None),
    ("email", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+"), None),
    ("financial", re.compile(r"(?<![\w.%+-])[A-Za-z0-9._-]{2,}@[A-Za-z]{2,}\b(?!\.[A-Za-z])"), None),   # UPI
    ("financial", re.compile(r"(?<![\d-])(?:\d[ -]?){12,18}\d(?![\d-])"), _v_card),
    ("digital", re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"), _v_ip),
    ("digital", re.compile(r"[-+]?\d{1,2}\.\d{4,}\s*[,;]\s*[-+]?\d{1,3}\.\d{4,}"), None),
    ("govt_ids", re.compile(r"(?<![A-Z0-9])[A-Z]{2}[ -]?\d{2}[ -]?(?:19|20)\d{2}\d{7}(?!\d)"), None),   # DL
    ("govt_ids", re.compile(r"(?<![A-Z0-9])[A-Z]{2}[ -]?\d{2}[ -]?[A-Z]{1,3}[ -]?\d{4}(?![A-Z0-9])"), None),  # vehicle
    ("govt_ids", re.compile(r"(?<![A-Z0-9])[A-Z]{4}\d{5}[A-Z](?![A-Z0-9])"), None),                     # TAN
    ("govt_ids", re.compile(r"UDYAM-[A-Z]{2}-\d{2}-\d{7}", I), None),
]

# --------------------------------------------------------------------------- #
# Label rules ("Name:", "Address:", ...)
# --------------------------------------------------------------------------- #
class LabelSpec:
    __slots__ = ("cat", "kind", "sig", "rx")

    def __init__(self, cat, pattern, anchored=False, kind="value", sig=False):
        self.cat, self.kind, self.sig = cat, kind, sig
        pre = (r"^\s*(?:\(?\w{1,2}[.)]\s*|\d{1,2}\s+|[\u2022*\-]\s*)?" if anchored
               else r"(?<![A-Za-z0-9/])")
        self.rx = re.compile(pre + "(?:" + pattern + ")", I)


_ROLES = (r"(?:proprietor|owner|partner|director|applicant|appellant|noticee|taxpayer|registered\s+person|customer|buyer|consignee|"
          r"employee|account\s*holder|beneficiary|recipient|authori[sz]ed\s+(?:signatory|representative|person)|"
          r"signatory|contact\s+person|assessee|payee|patient|student|candidate|member|holder|nominee|"
          r"guardian|father|mother|spouse|person)")
_ROLES2 = (r"(?:customer|buyer|consignee|employee|applicant|appellant|noticee|taxpayer|beneficiary|recipient|account\s*holder|"
           r"patient|student|candidate|member|nominee|payee|assessee|contact\s+person|proprietor|owner|"
           r"partner|director|signatory|authori[sz]ed\s+signatory|guardian|holder)")

LABEL_SPECS: List[LabelSpec] = [
    # --- individuals -------------------------------------------------------
    LabelSpec("names", r"(?:full\s+)?name", anchored=True),
    LabelSpec("names", r"name\s+of\s+(?:the\s+)?" + _ROLES),
    LabelSpec("names", _ROLES2 + r"(?:['\u2019]s)?\s+name"),
    LabelSpec("names", r"(?:father|mother|spouse|husband|wife|guardian)(?:['\u2019]?s)?\s*(?:/\s*(?:husband|wife|spouse))?\s*name"),
    LabelSpec("names", r"proprietor|owner|partners?|directors?|legal\s+representative|"
                       r"authori[sz]ed\s+(?:representative|signatory|person)|signatory|contact\s+person", sig=True),
    LabelSpec("names", r"issued\s+to|attn\.?|attention|kind\s+attention|kind\s+attn\.?"),
    # --- businesses --------------------------------------------------------
    LabelSpec("business", r"(?:trade|legal)\s*/\s*(?:trade|legal)\s*name"),
    LabelSpec("business", r"legal\s+name(?:\s+of\s+(?:the\s+)?(?:business|appellant|applicant|taxpayer|noticee|"
                          r"assessee|registered\s+person|person|supplier|recipient|dealer))?"),
    LabelSpec("business", r"trade\s+name(?:\s*,?\s*\(?\s*if\s+any\s*\)?)?"),
    LabelSpec("business", r"name\s+of\s+(?:the\s+)?(?:business|firm|company|organi[sz]ation|entity|party|supplier|vendor|institution)"),
    LabelSpec("business", r"(?:business|firm|company|organi[sz]ation|entity|party|supplier|vendor|registered|institution)\s+name"),
    # --- addresses ---------------------------------------------------------
    LabelSpec("address", r"address(?:\s*(?:line\s*)?\d)?", anchored=True, kind="address"),
    LabelSpec("address", r"(?:registered|residential|billing|shipping|delivery|permanent|correspondence|communication|"
                         r"office|business|present|current|mailing|site|bill\s*to|ship\s*to|supplier|buyer|customer|consignee)\s+address",
              kind="address"),
    LabelSpec("address", r"address\s+of\s+(?:the\s+)?(?:principal\s+place\s+of\s+business|supplier|recipient|customer|buyer|"
                         r"consignee|registered\s+office|business|firm|company|taxpayer|proprietor|premises|delivery|"
                         r"appellant|applicant|noticee|assessee|dealer|registered\s+person|party)",
              kind="address"),
    LabelSpec("address", r"address\s+for\s+(?:service|correspondence)|(?:principal\s+)?place\s+of\s+business|"
                         r"registered\s+office|regd\.?\s+office", kind="address"),
    # --- contact -----------------------------------------------------------
    LabelSpec("phone", r"(?:mobile|mob|phone|ph|tel|telephone|contact|cell|whatsapp|fax)(?:\s*(?:no|number|num|nos)\.?|\s*#)?\.?"),
    LabelSpec("email", r"e-?mail(?:\s*(?:id|address|ids))?"),
    # --- identifiers -------------------------------------------------------
    LabelSpec("pan", r"pan(?:\s*(?:no|number|card|#))?\.?"),
    LabelSpec("gstin", r"gstin(?:\s*/\s*(?:uin|id))?(?:\s*(?:no|number))?\.?(?:\s+of\s+(?:the\s+)?(?:taxpayer|appellant|"
                       r"applicant|noticee|assessee|dealer|supplier|recipient|registered\s+person|firm|company|party|"
                       r"client|buyer|seller))?|gstn\s*(?:no|number)?\.?|gst\s*(?:no|number|reg(?:istration)?\s*(?:no|number))\.?|uin"),
    LabelSpec("aadhaar", r"(?:aadhaar|aadhar|uidai)(?:\s*(?:no|number|card|id))?\.?|vid|enrol+ment\s*(?:id|no|number)"),
    LabelSpec("govt_ids",
              r"passport(?:\s*(?:no|number))?\.?|driving\s+licen[cs]e(?:\s*(?:no|number))?\.?|d\.?l\.?\s*(?:no|number)\.?|"
              r"voter\s*(?:id|card)(?:\s*(?:no|number))?\.?|epic(?:\s*(?:no|number))?\.?|"
              r"ration\s+card(?:\s*(?:no|number))?\.?|uan|(?:pf|epf|esi|esic)\s*(?:a/c\s*)?(?:no|number)\.?|"
              r"abha(?:\s*(?:no|number|id|address))?|din|iec|import\s+export\s+code|"
              r"udyam(?:\s+registration)?(?:\s*(?:no|number))?\.?|tan|"
              r"vehicle\s*(?:reg(?:istration)?\.?\s*)?(?:no|number)\.?|rc\s*(?:no|number)\.?|"
              r"employee\s*(?:id|code|no)\.?|emp\.?\s*(?:id|code|no)\.?|roll\s*(?:no|number)\.?|"
              r"student\s*id|customer\s*id|member\s*(?:id|no)\.?"),
    LabelSpec("financial",
              r"(?:bank\s+)?(?:a/c|acct?|account)\.?\s*(?:no|number|num|#)\.?|"
              r"beneficiary\s*(?:a/c|account)\s*(?:no|number)?\.?|card\s*(?:no|number)\.?|credit\s*card|debit\s*card|cvv|"
              r"policy\s*(?:no|number)\.?|loan\s*(?:a/c\s*)?(?:no|number)\.?|salary|gross\s*(?:salary|pay)|"
              r"net\s*(?:salary|pay)|take\s*home|ctc|annual\s*income|income|upi(?:\s*(?:id|address))?|vpa"),
    LabelSpec("demographic",
              r"date\s+of\s+birth|dob|d\.o\.b\.?|birth\s*date|marital\s+status|religion|nationality|blood\s+group"),
    LabelSpec("demographic", r"age|gender|sex|caste", anchored=True),
    LabelSpec("digital",
              r"ip\s*address|mac\s*address|device\s*id|imei(?:\s*(?:no|number))?\.?|user\s*(?:id|name)|username|login\s*id"),
]

_SEP_RE = re.compile(r"\s*(?:\([^)]{0,40}\)\s*)?(?::|\uFF1A|[-\u2013\u2014]+(?=\s)|\|)\s*")
_LABELISH_RE = re.compile(r"^\s*(?:\(?\w{1,2}[.)]\s*|\d{1,2}\s+)?[A-Za-z][A-Za-z0-9 .&/()'\u2019-]{1,34}?\s*[:\uFF1A]")

# "To," / "Bill To" / "Ship To" / "Consignee" ... block headers
_HEAD_RE = re.compile(
    r"^\s*(?:\(?\d{1,2}[.)]\s*)?"
    r"(?P<h>(?:details\s+of\s+)?(?:bill(?:ed)?\s*to|ship(?:ped)?\s*to|sold\s*to|deliver(?:ed)?\s*to|invoice\s*to|"
    r"consignee|buyer|receiver|recipient|customer|party|to)"
    r"(?:\s*\([^)]{0,30}\))?(?:\s*(?:party|details|name\s*(?:&|and)\s*address|address))?)"
    r"\s*(?P<sep>[:,\-\u2013\u2014.]?)\s*(?P<rest>.*)$", I)

_MS_RE = re.compile(r"(?<![A-Za-z])M\s*/\s*[sS]\b\.?")
_PIN_RE = re.compile(r"(?<![\d,.-])[1-9]\d{2}\s?\d{3}(?!\d)(?![,.]\d)")
_STATES = ("andhra pradesh|arunachal|assam|bihar|chhattisgarh|goa|gujarat|haryana|himachal|jharkhand|karnataka|"
           "kerala|madhya pradesh|maharashtra|manipur|meghalaya|mizoram|nagaland|odisha|orissa|punjab|rajasthan|"
           "sikkim|tamil nadu|telangana|tripura|uttar pradesh|uttarakhand|west bengal|delhi|chandigarh|puducherry|"
           "jammu|kashmir|ladakh|daman|diu|dadra|lakshadweep|andaman|india")
_STATE_RE = re.compile(r"\b(?:" + _STATES + r")\b", I)

_STOP_RE = re.compile(
    r"^\s*(?:tax\s+invoice|invoice|date|dated|place\s+of\s+supply|s\.?\s*no|sr\.?\s*no|sl\.?\s*no|description|"
    r"particulars|hsn|qty|quantity|rate|amount|total|sub\s*total|terms|declaration|bank\s+details|e-?way|irn|ack|"
    r"original|duplicate|triplicate|for\s|note|remarks|sub|subject|ref|reference|dear|sir|madam|copy\s+to|encl)\b", I)
_LOWER_START = re.compile(r"^\s*(?:of|the|and|or|for|in|on|to|if|a|an)\b")

_BAD_NAME_WORD = (r"invoice|gstin|pan|date|dated|address|phone|mobile|email|no|name|ph|tel|bill|ship|to|and|"
                  r"state|code|place|supply|total|amount|mob|contact|gst|uin")
_NAME_WORD = r"(?!(?i:" + _BAD_NAME_WORD + r")(?![A-Za-z]))[A-Z][A-Za-z.'\u2019-]*"
_TITLE_RE = re.compile(
    r"(?<![A-Za-z])(?:(?:Mr|MR|Mrs|MRS|Ms|Miss|MISS|Shri|SHRI|Shree|SHREE|Smt|SMT|Sri|SRI|Dr|DR|Prof|Kumari|KUMARI)(?![A-Za-z])\.?\s*|"
    r"(?i:[sdwch]/o|care\s+of)\.?\s+)" + _NAME_WORD + r"(?:\s+" + _NAME_WORD + r"){0,2}")

_CO_SUFFIX = (r"pvt\.?\s*ltd\.?|private\s+limited|public\s+limited|ltd\.?|limited|llp|l\.l\.p\.?|enterprises?|"
              r"traders?|industries|associates|corporation|corp\.?|&\s*co\.?|and\s+co\.?|&\s*sons|and\s+sons|stores|"
              r"agency|agencies|brothers|bros\.?|textiles|exports?|logistics|developers|builders|technologies|solutions")
_CO_RE = re.compile(r"(?<![A-Za-z0-9])(?:[A-Z][A-Za-z0-9&.'()-]*\s+){1,6}(?i:" + _CO_SUFFIX + r")(?![A-Za-z])")

_SIG_BAD = re.compile(r"\b(?:for|ltd|limited|pvt|private|authori[sz]ed|signatory|seal|stamp|sign|signed|digitally|"
                      r"proprietor|partner|director|manager|invoice|total|amount|thank|regards|yours|faithfully|"
                      r"sincerely|e&oe|computer|generated|page|original|duplicate)\b", I)
_NA_VALUES = {"n/a", "na", "nil", "none", "not applicable", "applicable", "same", "as above", "yes", "no",
              "male", "female", "-", "--"}


# --------------------------------------------------------------------------- #
# Page model
# --------------------------------------------------------------------------- #
@dataclass
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    ocr: bool = False          # read from a picture by OCR


class Seg:
    """A run of words on one visual row without a large horizontal gap (a 'cell')."""

    def __init__(self, widx: List[int], words: List[Word], rid: int):
        ws = [words[i] for i in widx]
        self.wi = widx
        self.rid = rid
        self.spans = []
        parts, pos = [], 0
        for w in ws:
            if parts:
                pos += 1
            self.spans.append((pos, pos + len(w.text)))
            parts.append(w.text)
            pos += len(w.text)
        self.text = " ".join(parts)
        self.x0 = min(w.x0 for w in ws)
        self.x1 = max(w.x1 for w in ws)
        self.y0 = min(w.y0 for w in ws)
        self.y1 = max(w.y1 for w in ws)
        self.h = max(1.0, max(w.y1 - w.y0 for w in ws))
        self.yc = sum((w.y0 + w.y1) / 2 for w in ws) / len(ws)
        self.xc = (self.x0 + self.x1) / 2
        self._cands = None


def build_segments(words: List[Word]) -> List[Seg]:
    order = sorted(range(len(words)), key=lambda i: (words[i].y0 + words[i].y1) / 2)
    rows: List[dict] = []
    for i in order:
        w = words[i]
        yc, h = (w.y0 + w.y1) / 2, max(1.0, w.y1 - w.y0)
        if rows and abs(yc - rows[-1]["yc"]) <= 0.45 * max(h, rows[-1]["h"]):
            r = rows[-1]
            r["idx"].append(i)
            n = len(r["idx"])
            r["yc"] = (r["yc"] * (n - 1) + yc) / n
            r["h"] = max(r["h"], h)
        else:
            rows.append({"idx": [i], "yc": yc, "h": h})
    segs: List[Seg] = []
    for rid, r in enumerate(rows):
        idx = sorted(r["idx"], key=lambda i: words[i].x0)
        cur = [idx[0]]
        for a, b in zip(idx, idx[1:]):
            wa, wb = words[a], words[b]
            thr = max(14.0, 1.3 * max(wa.y1 - wa.y0, wb.y1 - wb.y0))
            if wb.x0 - wa.x1 > thr:
                segs.append(Seg(cur, words, rid))
                cur = [b]
            else:
                cur.append(b)
        segs.append(Seg(cur, words, rid))
    return segs


def _aligned(s: Seg, r: Seg) -> bool:
    return abs(s.x0 - r.x0) <= 30 or abs(s.xc - r.xc) <= 30


class _XRef:
    """Alignment reference at the x-position where a value starts (e.g. after 'Address :')."""
    __slots__ = ("x0", "xc")

    def __init__(self, x0: float):
        self.x0, self.xc = x0, -1e9


_ADDR_WORD = re.compile(
    r"\d|,|\b(?:road|rd|nagar|marg|lane|street|st|near|opp|opposite|behind|building|bldg|chs|society|soc|"
    r"floor|flr|flat|shop|plot|sector|tower|complex|apartment|apt|wing|room|house|gali|chowk|bazar|bazaar|"
    r"market|colony|park|east|west|north|south|dist|district|taluka|tal|village|vill|post|po|pin|pincode|"
    r"station|highway|estate|industrial|midc|gala|unit|premises|mumbai|thane|pune|delhi)\b|\([ewns]\)", I)
_ADDR_GENERIC = set("""
no flat shop plot room floor ground first second third fourth building bldg road rd street st lane marg near opp
opposite behind east west north south e w n s dist district taluka tal city state india pin pincode code the of and
at post po village sector wing unit gala station highway house a b c d
""".split()) | {w for w in _STATES.replace(" ", "|").split("|")}


def _ntok(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", t.lower())


def _norm_key(t: str) -> str:
    return " ".join(t.split()).lower()


class Hit:
    __slots__ = ("cat", "chunks", "rects")

    def __init__(self, cat, chunks, rects):
        self.cat, self.chunks, self.rects = cat, chunks, rects


class _Cand:
    __slots__ = ("ls", "le", "vs", "ve", "spec", "has_sep")


# --------------------------------------------------------------------------- #
# "NEVER redact" rules: case law, statute, officers, jurisdiction
# --------------------------------------------------------------------------- #
NAMEY = {"names", "business", "blocks", "address", "manual"}      # categories that protection can veto
CONN = {"of", "and", "&", "the", "for", "ors.", "anr."}

_CITE_TAIL = r"(?:\s*\(\s*[A-Za-z][A-Za-z. ]{0,14}\))?"
CITE_RXS = [
    re.compile(r"\(\s*(?:19|20)\d\d\s*\)\s*\d{1,3}\s*[A-Z][A-Za-z.]{1,12}(?:\s+[A-Z][A-Za-z.]{1,10})?\s*\d{1,5}" + _CITE_TAIL),
    re.compile(r"\bAIR\s*(?:19|20)\d\d\s*[A-Za-z.()]{1,14}\s*\d{1,5}"),
    re.compile(r"(?<![\d(])(?:19|20)\d\d\s*[-\u2013]?\s*\(\s*\d{1,4}\s*\)\s*[-\u2013]?\s*[A-Z][A-Za-z.]{1,12}"
               r"(?:\s+[A-Z][A-Za-z.]{1,10})?\s*[-\u2013]?\s*\d{1,5}" + _CITE_TAIL),
    re.compile(r"\[\s*(?:19|20)\d\d\s*\]\s*\d{1,4}\s*[A-Za-z.]+(?:\.com)?\s*\d{1,5}" + _CITE_TAIL),
    re.compile(r"(?<![\d(])(?:19|20)\d\d\s*(?:SCC\s*OnLine\s*[A-Za-z]+|TIOL[-\w]*|taxmann\.com)\s*\d{1,6}", re.I),
    re.compile(r"\b(?:Civil\s+Appeal|Criminal\s+Appeal|Writ\s+Petition|W\.P\.|SLP|Special\s+Leave\s+Petition|Tax\s+Appeal|"
               r"Revision\s+Application|Misc\.?\s+Application|Appeal|Petition)(?:\s*\(\s*[A-Za-z.]{1,6}\s*\))?\s*"
               r"(?:No\.?|Nos\.?)\s*[\w./-]+(?:\s*(?:of|/)\s*(?:19|20)\d\d)?", re.I),
]
_ACT = (r"(?i:(?:the\s+)?(?:(?:Central|State|Integrated|Union\s+Territory|Maharashtra|[A-Z]{1,4})[\s/-]+)?"
        r"(?:Goods\s+and\s+Services\s+Tax|CGST|SGST|IGST|UTGST|MGST|GST|Customs|Income[- ]tax|Finance|Sales\s+Tax|VAT)"
        r"(?:\s*/\s*(?:CGST|SGST|IGST|UTGST|MGST))*\s+(?:Act|Rules?)\b(?:\s*,?\s*(?:19|20)\d\d)?)")
STAT_RXS = [
    re.compile(r"(?i:(?:sub-?\s?section|sub-?\s?rule|sections?|sec\.|u/s|u/r|rules?|regulations?|articles?|clauses?)"
               r"\s*\.?\s*\d+[A-Za-z]{0,2}(?:\s*\(\s*\w{1,4}\s*\))*)"),
    re.compile(_ACT),
    re.compile(r"(?i:\b(?:Notification|Circular|Instruction|Trade\s+Notice|Press\s+Release)\s*(?:No\.?|Nos\.?)\s*"
               r"[\w./()-]+(?:\s*[-\u2013]\s*[A-Za-z()]+)?(?:\s*dated\s*[\d./-]+)?)"),
]
_PROV_START = r"(?:Where|Every|Subject\s+to|Notwithstanding|Provided|Whoever|Any\s+person|No\s+person)\b"
ACT_THEN_PROVISION = re.compile(_ACT + r"\s*,?\s*(?P<body>" + _PROV_START + r".{0,900}?(?:\.(?=\s+[A-Z])|$))", re.S)
STAT_BLOCK_START = re.compile(
    r"^\s*(?:(?i:section)\s+)?\d{1,3}[A-Z]{0,2}\s*(?:\(\s*\w{1,3}\s*\)\s*){1,3}[.:\u2013-]?\s*" + _PROV_START + r"|"
    r"^\s*\(\s*\w{1,3}\s*\)\s+" + _PROV_START)
STAT_INTRO_END = re.compile(r"(?i:(?:as\s+under|as\s+follows|reads|provides|states|stipulates?|stipulated|provided)\s*[:\u2013-]\s*$)")

_PFX = r"(?:principal|pr\.?|additional|addl\.?|joint|jt\.?|deputy|dy\.?|assistant|asst\.?|senior|sr\.?|chief|special)"
DESIG_RX = re.compile(
    r"(?<![A-Za-z])(?:proper\s+officer|superintendent|inspector|appraiser|"
    r"(?:" + _PFX + r"\s+)*commissioner(?:\s*\(\s*appeals?\s*\))?|"
    r"(?:" + _PFX + r"\s+)+director(?:\s+general)?|director\s+general|adjudicating\s+authority|appellate\s+authority|"
    r"(?:state\s+|sales\s+|commercial\s+|central\s+|gst\s+|tax\s+|range\s+)+officer|tax\s+assistant|"
    r"(?:judicial|technical)\s+member|registrar|designated\s+authority)(?![A-Za-z])", I)
JUSTICE_RX = re.compile(r"(?:Hon['\u2019]?ble\s+)?(?:Mr\.?\s+|Ms\.?\s+|Mrs\.?\s+)?Justice(?=\s+[A-Z])")
JURIS_RXS = [
    re.compile(r"(?:[A-Z][\w-]*,?\s+){0,3}(?:Range|Division|Commissionerate|Jurisdictional|Jurisdiction)"
               r"(?:[\s,-]+(?:No\.?\s*)?[A-Z0-9][\w-]*){0,3}"),
    re.compile(r"(?i:jurisdiction(?:al)?)\s+(?:of\s+)?(?:the\s+)?(?:[A-Z][\w-]*,?\s*){1,4}"),
]
SIGNED_RX = re.compile(r"digitally\s+signed\s+by", I)

_GSTIN_FULL = re.compile(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", I)
_PAN_FULL = re.compile(r"[A-Z]{5}\d{4}[A-Z]", I)
_SKIPBACK = {"-", "\u2013", "\u2014", ":", "(", "[", "gstin", "gstin:", "gstin/id", "gstin/uin", "gstn", "gstn:", "gst", "no", "no.",
             "no:", "number", "pan", "pan:", "uin", "uin:", "having", "bearing", "with", "holding", "registered",
             "under", "is", "id", "id:", "vide", "(gstin", "(gstin:", "(pan", "(pan:", "gstin-", "bearing", "/"}
_STOPCAP = {"temporary", "provisional", "registration", "the", "supplier", "suppliers", "taxpayer", "dealer", "firm", "party", "buyer", "seller", "vendor",
            "recipient", "consignee", "assessee", "hence", "also", "as", "it", "this", "that", "from", "by", "to",
            "name", "trade", "legal", "sub", "ref", "its", "his", "her", "their", "our", "your", "said", "viz",
            "viz.", "i.e.", "e.g.", "gstin", "gstn", "pan", "of", "and", "in", "on", "with", "for", "against"}
_CUES = {"supplier", "suppliers", "taxpayer", "dealer", "firm", "vendor", "buyer", "seller", "recipient",
         "consignee", "assessee", "party"}
_ACR = {"CGST", "SGST", "IGST", "UTGST", "GST", "GSTR", "GSTR-1", "GSTR-3B", "GSTR-2A", "GSTR-2B", "GSTR-9", "ITC",
        "NGTP", "NGPT", "ACT", "PAN", "GSTIN", "GSTN", "HSN", "IT", "TDS", "TCS", "IRN", "RCM", "FIR", "DGGI",
        "SCN", "MGST", "INR", "RS", "NIL", "NA", "N/A", "I.E.", "I.E", "E.G.", "UIN", "ID", "AND", "OR", "NO"}
_FUNC = {"the", "is", "are", "was", "were", "has", "have", "had", "that", "which", "who", "by", "as", "with",
         "under", "for", "been", "be", "not", "it", "this", "these", "those", "from", "any", "shall", "may",
         "also", "hence", "such", "than", "would", "will", "can", "should", "his", "their", "its"}

_HDR_PARTY = (r"(?:supplier|recipient|taxpayer|buyer|dealer|customer|vendor|party|seller|consignee|assessee|firm)")
_HDR_BIZ = re.compile(
    r"(?:(?:trade|legal)\s*/\s*(?:trade|legal)\s*name|(?:trade|legal)\s+name|"
    r"name\s+of\s+(?:the\s+)?(?:" + _HDR_PARTY[3:-1] + r"|business)|(?:" + _HDR_PARTY[3:-1] + r")(?:['\u2019]s)?\s+name)"
    r"(?:\s+of\s+(?:the\s+)?" + _HDR_PARTY + r")?\s*(?:\(\s*if\s+any\s*\))?", I)
_HDR_ADDR = re.compile(r"address(?:\s+of\s+(?:the\s+)?(?:" + _HDR_PARTY[3:-1] + r"|business))?", I)


def iscap(t: str) -> bool:
    for ch in t:
        if ch.isalpha():
            return ch.isupper()
        if ch.isdigit():
            return False
    return False


def _clean_key(t: str) -> str:
    t = re.sub(r"[(),;:]", " ", t)
    t = _PREFIX_STRIP_KEY.sub("", " ".join(t.split())).strip(" .-")
    return t.lower()


_PREFIX_STRIP_KEY = re.compile(r"^(?:(?i:mrs|mr|ms|miss|shri|shree|smt|sri|dr|prof)\b\.?\s*)+")


# words that only ever appear in column headers / form labels: such a cell is never redacted
_HEADER_VOCAB = set("""
gstin gstn uin gstin/uin gstin/id pan supplier suppliers supplier's name names trade legal invoice invoices inv inv. bill
no no. nos nos. number date dated rs rs. gross net taxable value amount tax igst cgst sgst utgst cess itc total period
return hsn sac rate qty quantity particulars description sr sr. sl sl. s. s.no s.no. sr.no. of the recipient address
place state code type month year difference as per gstr gstr-1 gstr-3b gstr-2a gstr-2b gstr-9 gstr-9c 1 2a 2b 3b
books claimed available excess short remarks status arn irn e-way eway ack mobile email e-mail phone contact details
party vendor customer buyer seller id ref reference filing filed financial f.y. fy & and / - ( ) in (rs) (rs.) (in
rs.) to from on or wise taxpayer taxpayer's applicable
""".split())
# generic words: "Deemed Export", "Associated Enterprises", "Pure Agency" are legal terms, not businesses
_CO_GENERIC = set("""
the a an said such any all other this that these those his her their its our your deemed associated pure merchant
physical special economic related distinct registered foreign indian central state public private small micro medium
export import exports imports promotion capital goods scheme service services zero rated input output tax government
local authority holding subsidiary group parent joint venture major minor
""".split())
# signals that a paragraph is about THIS case (so it is not a pure statute extract)
_CASE_SPECIFIC = re.compile(r"\bm\s*/\s*s\b|\bnoticee\b|\bappellant\b|\btaxpayer\b|\byou\b|\byour\b|"
                            r"\bthe\s+said\b|\bdated\b|\brs\.?\s*\d|\u20b9|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", I)
_PROV_WORDS = re.compile(r"\bshall\b|\bprovided\s+that\b|\bnotwithstanding\b|\bregistered\s+person\b|"
                         r"\bproper\s+officer\b|\bprescribed\b|\bthereof\b|\btherein\b|\bhereinafter\b|"
                         r"\bunder\s+this\s+act\b|\bsub-?\s?section\b|\bentitled\b|\bliable\b|\bsubject\s+to\b|"
                         r"\bexplanation\b|\bwhere\s+it\s+appears\b|\bin\s+respect\s+of\b|\bsuch\s+person\b|"
                         r"\bcondition|\binput\s+tax\s+credit\b|\bitc\b|\bsection\b|\brule\b|\bact\b", I)
_PROV_LINE_START = re.compile(
    r"^\s*(?:[\u201c\u2018\"']|\(\s*(?:\d{1,3}[A-Z]{0,2}|[a-z]{1,4}|[ivx]{1,6})\s*\)|\d{1,3}[A-Z]{0,2}\s*[.(]|"
    r"(?i:section|rule|explanation|provided|proviso)\b|" + _PROV_START + r")")


# "2016 (44)" / "2015 (37)": year + volume of a law report - enough to recognise a citation in OCR text
_CITE_ANCHOR = re.compile(r"(?<![\d(/.-])(?:19|20)\d\d\s*[-\u2013]?\s*\(\s*\d{1,4}\s*\)(?!\s*\(?\s*[a-z]\b)")
_CBIC_DIN = re.compile(r"(?:CBIC-DIN-)?20\d{6}[A-Z0-9]{10,14}", I)
_LABEL_WORDS = {"gstin", "gstn", "gstin/uin", "gstin/id", "pan", "uin", "address", "name", "mobile", "email", "e-mail",
                "phone", "tel", "fax", "date", "dated", "din", "arn", "ref", "reference", "sub", "subject"}


def _is_header_seg(seg) -> bool:
    toks = [t.lower().strip(",:;.") or t for t in seg.text.split()]
    return bool(toks) and all(t in _HEADER_VOCAB or t.rstrip(".") in _HEADER_VOCAB for t in toks)


# --------------------------------------------------------------------------- #
# Detector (one page)
# --------------------------------------------------------------------------- #
class Detector:
    def __init__(self, words: List[Word], cfg: Config):
        self.words = words
        self.cfg = cfg
        self.segs = build_segments(words)
        self.hits: List[Hit] = []
        self._marked: set = set()
        self.prot_all: set = set()
        self.prot_name: set = set()
        self.prot_off: set = set()
        self.officer_keys: set = set()
        self.addr_keys: list = []
        # reading-order token flow (for text that wraps over lines)
        self.flow = []
        for seg in sorted(self.segs, key=lambda s: (s.rid, s.x0)):
            for k in range(len(seg.wi)):
                self.flow.append((seg, k))
        self.ft = [self.words[seg.wi[k]].text for seg, k in self.flow]
        self.fidx = [seg.wi[k] for seg, k in self.flow]
        self.fpos, pos = [], 0
        for t in self.ft:
            self.fpos.append(pos)
            pos += len(t) + 1
        self.fstr = " ".join(self.ft)

    # ---- geometry helpers -------------------------------------------------
    def right_of(self, seg: Seg) -> Optional[Seg]:
        best = None
        for s in self.segs:
            if s.rid == seg.rid and s.x0 > seg.x0 + 1 and s.x0 >= seg.x1 - 1:
                if best is None or s.x0 < best.x0:
                    best = s
        if best is not None and best.x0 - seg.x1 <= 250:
            return best
        return None

    def below(self, prev: Seg, refs: List[Seg], maxp: float = 2.2) -> Optional[Seg]:
        best = None
        for s in self.segs:
            if s is prev:
                continue
            dy = s.yc - prev.yc
            if dy < 0.6 * min(prev.h, s.h) or dy > maxp * max(prev.h, s.h):
                continue
            if not any(_aligned(s, r) for r in refs):
                continue
            key = (s.yc, abs(s.x0 - prev.x0))
            if best is None or key < best[0]:
                best = (key, s)
        return best[1] if best else None

    def above(self, nxt: Seg, maxp: float = 2.4) -> Optional[Seg]:
        best = None
        for s in self.segs:
            dy = nxt.yc - s.yc
            if dy < 0.6 * min(nxt.h, s.h) or dy > maxp * max(nxt.h, s.h):
                continue
            if not (_aligned(s, nxt) or (min(s.x1, nxt.x1) - max(s.x0, nxt.x0)) > 0):
                continue
            if best is None or s.yc > best.yc:
                best = s
        return best

    # ---- flow helpers -------------------------------------------------------
    def _tok_range(self, s: int, e: int) -> range:
        a = bisect_right(self.fpos, s) - 1
        a = max(a, 0)
        if self.fpos[a] + len(self.ft[a]) <= s:
            a += 1
        b = bisect_left(self.fpos, e)
        return range(a, max(a, b))

    def _protect(self, toks, level: str = "name"):
        for i in toks:
            w = self.fidx[i]
            if level == "off":           # weak: only stops person / business-name rules, never addresses
                self.prot_off.add(w)
                continue
            self.prot_name.add(w)
            if level == "all":
                self.prot_all.add(w)

    def _protect_seg(self, seg: Seg, level: str = "name"):
        for w in seg.wi:
            self.prot_name.add(w)
            if level == "all":
                self.prot_all.add(w)

    def _prosey(self, seg: Seg) -> bool:
        low = set(re.findall(r"\b[a-z']+\b", seg.text))
        return len(low & _FUNC) >= 2

    def _namelike_text(self, text: str) -> bool:
        t = re.sub(r"^\s*(?:name\s*[:\-]?|sd\s*/?\s*-?|\(sd\)\s*|-)\s*", "", text.strip(), flags=I)
        toks = t.split()
        if not (1 <= len(toks) <= 6):
            return False
        for tk in toks:
            if not re.fullmatch(r"\(?[A-Za-z][A-Za-z.'\u2019-]*\)?,?", tk):
                return False
            if not (iscap(tk) or tk.lower() in CONN):
                return False
        if re.search(r"\b(?:date|place|yours|thanks|regards|seal|signature|signed|digitally|page)\b", t, I):
            return False
        return not DESIG_RX.search(t)

    def _add_officer_key(self, text: str):
        k = _clean_key(text)
        words = [w for w in re.findall(r"[a-z][a-z.'-]*", k) if len(w.strip(".")) >= 2]
        # a person's name: 2-5 words, no digits, no place / state names, no designation words
        if (2 <= len(words) <= 5 and not re.search(r"\d", k) and not _STATE_RE.search(k)
                and not DESIG_RX.search(k) and not re.search(r"\b(?:range|division|ward|circle|office|"
                                                              r"commissionerate|jurisdiction|designation|name)\b", k)):
            self.officer_keys.add(k)

    # ---- protection --------------------------------------------------------------
    def _compute_protection(self, extra_keys=()):
        cfg = self.cfg
        if cfg.protect_citations:
            self._p_caselaw()
        if cfg.protect_statutes:
            self._p_statutes()
        if cfg.protect_quotes:
            self._p_quotes()
        if cfg.protect_officers:
            self._p_officers()
        if cfg.protect_officers:
            for k in extra_keys:
                rx = self._rx_for(k)
                if rx is None:
                    continue
                for m in rx.finditer(self.fstr):
                    self._protect(self._tok_range(m.start(), m.end()), "off")

    def _p_caselaw(self):
        ft0 = self.ft
        for rx in CITE_RXS + [_CITE_ANCHOR]:
            for m in rx.finditer(self.fstr):
                toks = list(self._tok_range(m.start(), m.end()))
                self._protect(toks, "all")
                # the party name written just before a citation, even without "v." / "Vs."
                # ("ii) Indeos Abs Ltd. 2010 (254) ELT 0628 (HC)")
                if toks:
                    j, back = toks[0] - 1, []
                    while j >= 0 and len(back) < 12:
                        tk = ft0[j]
                        core = tk.strip("(),;:\u201c\u201d\"'-\u2013")
                        if not core or re.fullmatch(r"\(?[ivxlc]{1,5}[.)]|\(?\d{1,3}[.)]|\(?[a-z][.)]", tk):
                            break
                        if tk.endswith(":") or (back and tk.endswith(".") and len(core) > 4
                                                 and core.lower() not in ("ltd", "pvt", "corpn", "bros", "co")):
                            break
                        if not (iscap(core) or core.lower() in CONN or core in ("&", "v", "vs", "v.", "vs.")
                                or core.lower() in ("ltd", "pvt", "ltd.", "pvt.", "(p)", "limited", "private")
                                or re.fullmatch(r"(?i:" + _CO_SUFFIX + r")", core)):
                            break
                        back.append(j)
                        j -= 1
                    if back:
                        self._protect(back, "all")
        ft, n = self.ft, len(self.ft)
        for i, t in enumerate(ft):
            tl = t.lower().rstrip(",;")
            if tl in ("vs", "vs.", "versus", "v/s", "v/s.") or (
                    tl in ("v", "v.") and 0 < i < n - 1 and iscap(ft[i - 1]) and iscap(ft[i + 1])):
                toks = [i]
                j, cnt = i - 1, 0
                left = []
                while j >= 0 and cnt < 12:
                    tk = ft[j]
                    if j < i - 1 and tk[-1] in ",;:":
                        break
                    if not (iscap(tk) or tk.lower() in CONN or tk[0] in "(&\u201c\"'"):
                        break
                    left.append(j)
                    j -= 1
                    cnt += 1
                while left and ft[left[-1]].lower() in CONN:
                    left.pop()
                toks += left
                j, cnt = i + 1, 0
                while j < n and cnt < 14:
                    tk = ft[j]
                    if (tk[0] in "([" or tk[0].isdigit()) and not re.fullmatch(r"\([A-Z]{1,3}\)[,;]?", tk):
                        break
                    if not (iscap(tk) or tk.lower() in CONN or tk[0] in "&\u201c\"'"):
                        break
                    toks.append(j)
                    cnt += 1
                    if tk[-1] in ",;":
                        break
                    j += 1
                self._protect(toks, "all")

    def _not_case_data(self, s: Seg) -> bool:
        """A line that can belong to a statute extract: no label, no GSTIN / PAN / M/s., not a table cell."""
        t = s.text
        if self.label_like(s) or _MS_RE.search(t) or _GSTIN_FULL.search(t) or _PAN_FULL.search(t):
            return False
        if _HEAD_RE.match(t) and _HEAD_RE.match(t).group("sep"):
            return False
        return len(t.split()) >= 5 or bool(_PROV_LINE_START.match(t))

    def _stat_extend(self, seg: Seg, include_first: bool = True, max_lines: int = 14):
        def terminal(s: Seg) -> bool:
            return s.text.rstrip().rstrip("\u201d\"'\u2019)").endswith(".")
        cur = seg
        if include_first:
            self._protect_seg(seg, "all")
            if terminal(seg):
                return
        for _ in range(max_lines):
            nx = self.below(cur, [seg, cur], 2.3)
            if nx is None or not self._not_case_data(nx):
                break
            self._protect_seg(nx, "all")
            cur = nx
            if terminal(nx):
                break

    def _p_statutes(self):
        for rx in STAT_RXS:
            for m in rx.finditer(self.fstr):
                self._protect(self._tok_range(m.start(), m.end()), "all")
        for m in ACT_THEN_PROVISION.finditer(self.fstr):
            self._protect(self._tok_range(m.start("body"), m.end("body")), "all")
        for seg in self.segs:
            if STAT_BLOCK_START.match(seg.text):
                self._stat_extend(seg, True)
            elif STAT_INTRO_END.search(seg.text):
                # "... reads as under:" protects what follows ONLY if it looks like a provision
                # ("The details are as follows-" followed by a table of party details must not be protected)
                nx = self.below(seg, [seg], 2.6)
                if nx is not None and _PROV_LINE_START.match(nx.text) and self._not_case_data(nx):
                    self._stat_extend(seg, False)
        self._p_provision_paras()

    def _p_provision_paras(self):
        """Statute text written as an ordinary paragraph (no quote marks, no 'reads as under').
        Protected from name / business / address rules only (IDs are still redacted) and only when the
        paragraph carries no case-specific detail (M/s., GSTIN, taxpayer, you, dates, Rs. amounts)."""
        used = set()
        for seg in sorted(self.segs, key=lambda s: (s.y0, s.x0)):
            if id(seg) in used or not self._prosey(seg):
                continue
            para, cur = [seg], seg
            while len(para) < 40:
                nx = self.below(cur, [seg, cur], 2.2)
                if nx is None or id(nx) in used or self.label_like(nx) or not (self._prosey(nx) or len(nx.text.split()) >= 4):
                    break
                para.append(nx)
                cur = nx
            for s_ in para:
                used.add(id(s_))
            text = " ".join(s_.text for s_ in para)
            if len(text.split()) < 12 or _CASE_SPECIFIC.search(text):
                continue
            if _GSTIN_FULL.search(text) or _PAN_FULL.search(text):
                continue
            if _TITLE_RE.search(text) or _CO_RE.search(text):          # Shri X / ABC Traders -> case narrative
                continue
            caps = re.findall(r"\b[A-Z][A-Z.&'-]{2,}\b", text)
            if sum(1 for c in caps if c.strip(".") not in _ACR) >= 2:      # RAMESH KUMAR style names
                continue
            kinds = {m.group(0).lower().split()[0] for m in _PROV_WORDS.finditer(text)}
            strong = kinds & {"shall", "provided", "notwithstanding", "thereof", "therein", "hereinafter",
                              "prescribed", "explanation", "entitled", "liable", "subject", "condition"}
            if len(kinds) >= 3 and strong:
                for s_ in para:
                    self._protect_seg(s_, "name")

    def _p_quotes(self):
        ft, n = self.ft, len(self.ft)
        i = 0
        while i < n:
            t = ft[i]
            straight = t.startswith('"') and len(t) > 1
            if t.startswith("\u201c") or t.startswith("\u2018\u2018") or straight:
                close = '"' if straight else "\u201d"
                for j in range(i, min(n, i + 600)):
                    if j == i and straight and not (len(t) > 2 and t.rstrip(".,;)").endswith('"')):
                        continue
                    if ft[j].rstrip(".,;)").endswith(close) or ft[j].endswith(close):
                        if 12 <= (j - i + 1):
                            self._protect(range(i, j + 1), "name")
                        i = j
                        break
            i += 1

    def _blockstop(self, s: Seg) -> bool:
        t = s.text.strip()
        if not re.search(r"[A-Za-z]{2}", t):
            return True
        m = _HEAD_RE.match(t)
        if m and m.group("sep"):
            return True
        if _MS_RE.search(t) or _STOP_RE.match(t) or self._prosey(s):
            return True
        if any(r.search(t) for _, r, _ in REGEX_RULES[:2]):
            return True
        return False

    def _sig_region(self, A: Seg):
        h = A.h
        cur_bottom = A.y1
        rows = [s for s in self.segs
                if s.yc >= A.y0 - 0.5 * h and s.x1 >= A.x0 - 260 and s.x0 <= A.x1 + 150 and s.x1 <= A.x1 + 220
                and not self._prosey(s)]
        rows.sort(key=lambda s: s.y0)
        n = 0
        for s in rows:
            if s.y0 - cur_bottom > 3.0 * max(h, s.h):
                break
            self._protect_seg(s, "name")
            cur_bottom = max(cur_bottom, s.y1)
            n += 1
            if n > 14:
                break

    def _p_officers(self):
        ft, n = self.ft, len(self.ft)
        # (a) designation phrases in running text: name before, jurisdiction after
        for m in list(DESIG_RX.finditer(self.fstr)) + list(JUSTICE_RX.finditer(self.fstr)):
            toks = list(self._tok_range(m.start(), m.end()))
            if not toks:
                continue
            self._protect(toks, "name")
            is_j = m.group(0).lower().find("justice") >= 0
            # name before
            if not is_j:
                names, j = [], toks[0] - 1
                row0 = self.flow[toks[0]][0].rid
                while j >= 0 and len(names) < 6:
                    if self.flow[j][0].rid != row0:     # stay on the designation's own line
                        break
                    tk = ft[j]
                    if len(names) > 0 and tk[-1] in ",;:":
                        break
                    core = tk.strip("(),;:")
                    if core.lower() in _STOPCAP or not (iscap(core) or core.lower() in ("&",)) or core[:1].isdigit():
                        break
                    names.append(j)
                    j -= 1
                    if tk[-1] == ")" and tk[0] == "(":
                        break
                if names:
                    names.reverse()
                    self._protect(names, "name")
                    self._add_officer_key(" ".join(ft[i] for i in names))
            # jurisdiction / name after
            j, cnt = toks[-1] + 1, 0
            if ft[toks[-1]].endswith(".") and len(ft[toks[-1]]) > 4:
                j = n
            names_after = []
            row1 = self.flow[toks[-1]][0].rid
            while j < n and cnt < 8:
                if self.flow[j][0].rid != row1:         # stay on the designation's own line
                    break
                tk = ft[j]
                if re.fullmatch(r"M\s*/\s*[sS]\.?", tk):
                    break
                core = tk.strip(",;:()")
                if not (iscap(core) or core.lower() in CONN or core in ("-", "\u2013") or core[:1].isdigit()):
                    break
                self._protect([j], "name")
                names_after.append(j)
                cnt += 1
                if ft[j].endswith(".") and len(ft[j]) > 4:      # sentence ends here
                    break
                j += 1
            if is_j and names_after:
                self._add_officer_key(" ".join(ft[i] for i in names_after[:4]))
        # (b) jurisdiction phrases
        for rx in JURIS_RXS:
            for m in rx.finditer(self.fstr):
                self._protect(self._tok_range(m.start(), m.end()), "name")
        # (c) stand-alone signature / designation blocks
        for seg in self.segs:
            t = seg.text
            if SIGNED_RX.search(t):
                self._sig_region(seg)
                mm = SIGNED_RX.search(t)
                key = t[mm.end():]
                key = re.split(r"\bDate\b|\bReason\b|\bLocation\b", key, flags=I)[0].strip()
                nx = self.below(seg, [seg], 1.9)
                if nx is not None and not re.match(r"\s*(?:date|reason|location)", nx.text, I) \
                        and self._namelike_text(nx.text):
                    key += " " + nx.text
                self._add_officer_key(key)
                continue
            if len(t.split()) > 10 or self._prosey(seg) or not DESIG_RX.search(t):
                continue
            self._protect_seg(seg, "name")
            ab = self.above(seg, 2.4)
            if ab is not None and self._namelike_text(ab.text):
                self._protect_seg(ab, "name")
                self._add_officer_key(re.sub(r"^\s*name\s*[:\-]?\s*", "", ab.text, flags=I))
            cur = seg
            for _ in range(3):
                nx = self.below(cur, [seg, cur], 2.4)
                if nx is None or self._blockstop(nx):
                    break
                self._protect_seg(nx, "name")
                cur = nx

    # ---- marking ----------------------------------------------------------
    def mark_parts(self, cat: str, parts) -> bool:
        if not self.cfg.enabled(cat):
            return False
        namey = cat in NAMEY
        rects, chunks, widx = [], [], set()
        for seg, s, e in parts:
            t = seg.text
            while s < e and t[s].isspace():
                s += 1
            while e > s and t[e - 1].isspace():
                e -= 1
            if s >= e:
                continue
            covk = [k for k, (ws, we) in enumerate(seg.spans) if ws < e and we > s]
            if not covk:
                continue
            if _is_header_seg(seg):
                continue
            weak = cat in ("names", "business", "manual")
            keep = [k for k in covk
                    if seg.wi[k] not in self.prot_all and not (namey and seg.wi[k] in self.prot_name)
                    and not (weak and seg.wi[k] in self.prot_off)]
            if not keep:
                continue
            runs: List[List[int]] = []
            for k in keep:
                if runs and k == runs[-1][-1] + 1:
                    runs[-1].append(k)
                else:
                    runs.append([k])
            for run in runs:
                ws_ = [self.words[seg.wi[k]] for k in run]
                x0, x1 = min(w.x0 for w in ws_), max(w.x1 for w in ws_)
                y0, y1 = min(w.y0 for w in ws_), max(w.y1 for w in ws_)
                if any(w.ocr for w in ws_):         # picture text: cover the whole glyphs generously
                    pad = 0.18 * (y1 - y0)
                    rects.append((x0 - pad, y0 - pad, x1 + pad, y1 + pad))
                else:
                    dy = 0.08 * (y1 - y0)
                    rects.append((x0 - 0.3, y0 + dy, x1 + 0.3, y1 - dy))
                if len(keep) == len(covk):
                    chunks.append(t[s:e])
                else:
                    chunks.append(" ".join(w.text for w in ws_))
                widx.update(seg.wi[k] for k in run)
        if not widx or widx <= self._marked:
            return False
        self._marked |= widx
        self.hits.append(Hit(cat, chunks, rects))
        return True

    def mark(self, cat, seg, s, e) -> bool:
        return self.mark_parts(cat, [(seg, s, e)])

    def mark_tokens(self, cat: str, toks) -> bool:
        parts: List[list] = []
        for i in toks:
            seg, k = self.flow[i]
            s, e = seg.spans[k]
            if parts and parts[-1][0] is seg and s >= parts[-1][2]:
                parts[-1][2] = e
            else:
                parts.append([seg, s, e])
        return self.mark_parts(cat, [tuple(p) for p in parts]) if parts else False

    # ---- label candidates -------------------------------------------------
    def _cands(self, seg: Seg) -> List[_Cand]:
        if seg._cands is not None:
            return seg._cands
        t = seg.text
        raw = []
        for spec in LABEL_SPECS:
            for m in spec.rx.finditer(t):
                le = m.end()
                sm = _SEP_RE.match(t, le)
                c = _Cand()
                c.ls, c.le, c.spec = m.start(), le, spec
                if sm:
                    sep = t[le:sm.end()]
                    if ":" not in sep and "\uFF1A" not in sep and c.ls > 6:
                        continue                      # a dash in running text is not a label
                    c.has_sep, c.vs = True, sm.end()
                elif not t[le:].strip():
                    if len(t[:c.ls].strip()) > 4:     # label must be the whole cell, not the end of a sentence
                        continue
                    c.has_sep, c.vs = False, len(t)
                else:
                    continue
                raw.append(c)
        raw.sort(key=lambda c: (c.ls, -(c.le - c.ls)))
        chosen, last = [], -1
        for c in raw:
            if c.ls >= last:
                chosen.append(c)
                last = c.le
        for i, c in enumerate(chosen):
            c.ve = chosen[i + 1].ls if i + 1 < len(chosen) else len(t)
        seg._cands = chosen
        return chosen

    def label_like(self, seg: Seg) -> bool:
        if _LABELISH_RE.match(seg.text):
            return True
        return any(c.ls <= 6 for c in self._cands(seg))

    def is_stop(self, seg: Seg) -> bool:
        t = seg.text.strip()
        if not t or not re.sub(r"\W", "", t):
            return True
        m = _HEAD_RE.match(t)
        if m and not m.group("rest").strip():
            return True
        if _STOP_RE.match(t) or _LOWER_START.match(t) or self.label_like(seg):
            return True
        return self._prosey(seg)

    # ---- multi-line continuation -------------------------------------------
    def _addr_line(self, s: Seg) -> bool:
        """A line that can continue an address: address-like, not a label, not a sentence."""
        t = s.text.strip()
        if not t or self.label_like(s) or self._prosey(s) or _STOP_RE.match(t):
            return False
        m = _HEAD_RE.match(t)
        if m and m.group("sep"):
            return False
        if _GSTIN_FULL.search(t) or _PAN_FULL.search(t) or _MS_RE.search(t):
            return False
        return bool(_ADDR_WORD.search(t)) or not _LOWER_START.match(t)

    def _continue(self, last: Seg, refs: list, cat: str, max_lines: int = 5, first_maxp: float = 2.8):
        """Mark the following lines of a multi-line value. Returns the texts marked."""
        done = []
        if _PIN_RE.search(last.text):
            return done
        addr = cat in ("address", "blocks")
        maxp = first_maxp
        for _ in range(max_lines):
            nxt = self.below(last, refs, maxp)
            if nxt is None:
                break
            if self.is_stop(nxt) and not (addr and self._addr_line(nxt)):
                break
            self.mark(cat, nxt, 0, len(nxt.text))
            done.append(nxt.text)
            refs = refs + [nxt]
            last = nxt
            maxp = 2.2
            if _PIN_RE.search(nxt.text):
                break
        return done

    def _whole_address(self, cat: str, first_text: str, more: list, before: list = ()):
        """Remember the full multi-line address as one item, so it is found again in other layouts."""
        full = " ".join([b.strip() for b in before] + [first_text.strip()] + [m.strip() for m in more])
        if cat == "address" and len(full) >= 10:
            self.addr_keys.append(_norm_key(full))
        if more or before:
            self.hits.append(Hit(cat, [full], []))

    def _has_left_cell(self, s: Seg, label: Seg) -> bool:
        """True when the line s has some other text to its left on the same row (= another table row)."""
        return any(o is not s and o.rid == s.rid and o.x1 <= s.x0 + 1 and o.x1 >= label.x0 - 5 for o in self.segs)

    def _addr_above(self, val: Seg, label: Seg) -> list:
        """Table cells are often centred: the first address line(s) sit ABOVE the label's row."""
        out, cur = [], val
        for _ in range(3):
            a = self.above(cur, 1.9)
            if (a is None or abs(a.x0 - val.x0) > 12 or a.wi[0] in self._marked or self._has_left_cell(a, label)
                    or not self._addr_line(a) or _PIN_RE.search(a.text)):
                break
            self.mark("address", a, 0, len(a.text))
            out.insert(0, a.text)
            cur = a
        return out

    def _addr_below(self, val: Seg, label: Seg, max_lines: int = 6) -> list:
        """Lines under the value, stopping at the next form / table row."""
        out, cur = [], val
        if _PIN_RE.search(val.text):
            return out
        for _ in range(max_lines):
            nx = self.below(cur, [val, cur], 2.2)
            if nx is None or abs(nx.x0 - val.x0) > 30 or self._has_left_cell(nx, label) or not self._addr_line(nx):
                break
            self.mark("address", nx, 0, len(nx.text))
            out.append(nx.text)
            cur = nx
            if _PIN_RE.search(nx.text):
                break
        return out

    def _value_ref(self, seg: Seg, pos: int):
        for k, (ws, we) in enumerate(seg.spans):
            if we > pos:
                return _XRef(self.words[seg.wi[k]].x0)
        return _XRef(seg.x0)

    def _near_marked_addr(self, seg: Seg) -> bool:
        """The line directly above or below is already redacted as an address (a wrapped address)."""
        for nb in (self.above(seg, 1.9), self.below(seg, [seg], 1.9)):
            if nb is not None and any(w in self._marked for w in nb.wi):
                return True
        return False

    def _addr_fuzzy(self, addr_keys):
        """Find a known address again even when it is wrapped differently, split over lines or table cells."""
        if not self.cfg.enabled("address") or not addr_keys:
            return
        norm = [_ntok(t) for t in self.ft]
        n = len(norm)
        for key in addr_keys:
            seq = [x for x in (_ntok(t) for t in key.split()) if x]
            aset = set(seq)
            dist = {x for x in aset if x not in _ADDR_GENERIC and (len(x) >= 3 or any(c.isdigit() for c in x))}
            # house-level words: flat / building / street (first half of the address), never town, state or PIN
            tail = set(seq[len(seq) // 2:])
            house = {x for x in seq[:max(1, len(seq) // 2)] if x in dist and x not in tail
                     and not re.fullmatch(r"\d{6}", x) and not _STATE_RE.fullmatch(x)}
            if len(dist) < 2 or not house:
                continue
            i = 0
            while i < n:                                   # runs in reading order (wraps across lines)
                if norm[i] and norm[i] in aset:
                    j = i
                    while j < n and (norm[j] in aset or not norm[j]):
                        j += 1
                    run = [k for k in range(i, j) if norm[k]]
                    got = {norm[k] for k in run}
                    if len(run) >= 3 and len(got & dist) >= 2 and got & house:
                        self.mark_tokens("address", list(range(i, j)))
                    i = j
                else:
                    i += 1
            for seg in self.segs:                          # single lines / table cells holding address pieces
                if len(seg.wi) < 2 or self._prosey(seg):
                    continue
                nt = [_ntok(self.words[w].text) for w in seg.wi]
                real = [k for k, x in enumerate(nt) if x]
                best, run = [], []                         # longest continuous stretch of address words
                for k in real + [None]:
                    if k is not None and nt[k] in aset:
                        run.append(k)
                    else:
                        if len(run) > len(best):
                            best = run
                        run = []
                got = {nt[k] for k in best}
                nd = len(got & dist)
                near = any(self.words[w].x0 >= 0 for w in seg.wi) and self._near_marked_addr(seg)
                if (len(best) >= 2 and len(best) >= 0.6 * len(real)
                        and ((nd >= 2 and got & house) or (nd >= 2 and near))):
                    self.mark("address", seg, seg.spans[best[0]][0], seg.spans[best[-1]][1])

    # ---- layer 1: patterns ---------------------------------------------------
    def _patterns(self, seg: Seg):
        t = seg.text
        for cat, rx, val in REGEX_RULES:
            if not self.cfg.enabled(cat):
                continue
            for m in rx.finditer(t):
                if val and not val(m, t):
                    continue
                self.mark(cat, seg, m.start(), m.end())
        if self.cfg.enabled("names"):
            for m in _TITLE_RE.finditer(t):
                self.mark("names", seg, m.start(), m.end())
        if self.cfg.company_suffix and self.cfg.enabled("business"):
            for m in _CO_RE.finditer(t):
                words = re.findall(r"[A-Za-z]+", m.group(0))[:-1]
                if words and all(w.lower() in _CO_GENERIC or w.lower() in CONN for w in words):
                    continue
                self.mark("business", seg, m.start(), m.end())

    # ---- layer 2: labels & layout -----------------------------------------------
    def _labels(self, seg: Seg):
        t = seg.text
        for c in self._cands(seg):
            spec = c.spec
            val = t[c.vs:c.ve]
            if val.strip():
                if val.strip().lower() in _NA_VALUES:
                    continue
                if spec.cat == "govt_ids" and _CBIC_DIN.match(re.sub(r"\s+", "", val.strip())[:26]):
                    continue                       # CBIC document number (DIN) - not personal data
                self.mark(spec.cat, seg, c.vs, c.ve)
                if spec.kind == "address":
                    more = self._continue(seg, [seg, self._value_ref(seg, c.vs)], spec.cat, max_lines=6)
                    self._whole_address(spec.cat, val, more)
                    if not more:
                        self.addr_keys.append(_norm_key(val))
                continue
            if spec.sig and not c.has_sep:
                self._sig_above(seg)
                continue
            nxt = self.right_of(seg)
            if nxt is not None and not self.label_like(nxt) and not self.is_stop(nxt):
                self.mark(spec.cat, nxt, 0, len(nxt.text))
                if spec.kind == "address":                 # label | value laid out as a form / table row
                    before = self._addr_above(nxt, seg)
                    more = self._addr_below(nxt, seg)
                    self._whole_address(spec.cat, nxt.text, more, before)
                continue
            nxt = self.below(seg, [seg], 3.4)
            if nxt is not None and (not self.is_stop(nxt) or (spec.kind == "address" and self._addr_line(nxt))):
                self.mark(spec.cat, nxt, 0, len(nxt.text))
                if spec.kind == "address":
                    more = self._continue(nxt, [seg, nxt], spec.cat, max_lines=6)
                    self._whole_address(spec.cat, nxt.text, more)
                    if not more:
                        self.addr_keys.append(_norm_key(nxt.text))
            elif spec.sig:
                self._sig_above(seg)

    def _sig_above(self, seg: Seg):
        a = self.above(seg)
        if a is None:
            return
        t = a.text.strip()
        words = t.split()
        if (1 <= len(words) <= 4 and re.fullmatch(r"[A-Za-z][A-Za-z.' \u2019-]{2,40}", t)
                and not _SIG_BAD.search(t) and not self.label_like(a)):
            self.mark("names", a, 0, len(a.text))

    def _columns(self, seg: Seg):
        """Table / form column headers such as 'Trade/Legal name of the Supplier': redact the cells below."""
        txt = seg.text.strip(" :.-\u2013")
        if len(txt.split()) > 8 or not txt:
            return
        r = self.right_of(seg)
        if r is not None and not _is_header_seg(r) and not self.label_like(r) and r.x0 - seg.x1 < 200:
            return                       # 'Legal Name | NARENDRA ...' is a form row, not a table column
        for rx, cat in ((_HDR_BIZ, "business"), (_HDR_ADDR, "address")):
            last = None
            nxt = self.below(seg, [seg], 1.7)
            if nxt is not None and len(nxt.text.split()) <= 6:
                comb = txt + " " + nxt.text.strip(" :.-\u2013")
                if rx.fullmatch(comb) and _LOWER_START.match(nxt.text):
                    last = nxt
            if last is None and rx.fullmatch(txt):
                last = seg
            if last is None:
                continue
            cur, refs = last, [seg, last]
            cell, start = [], len(self.hits)
            for n in range(5):
                d = self.below(cur, refs, 2.7 if n == 0 else 2.2)
                if d is None or self.is_stop(d) or not re.search(r"[A-Za-z]{2}", d.text):
                    break
                self.mark(cat, d, 0, len(d.text))
                cell.append(d.text)
                cur = d
            if len(cell) > 1:
                self.hits.append(Hit(cat, [" ".join(cell)], []))   # key only (no box): whole name elsewhere
            if cat == "address" and cell:
                self.addr_keys.append(_norm_key(" ".join(cell)))
            break

    def _headers(self, seg: Seg):
        m = _HEAD_RE.match(seg.text)
        if not m:
            return
        h, sep, rest = m.group("h").lower(), m.group("sep"), m.group("rest")
        if not sep and rest.strip():
            return
        strong = re.match(r"(?:details\s+of\s+)?(?:bill|ship|sold|deliver|invoice|consignee)", h)
        if not strong and sep != ":" and not (h == "to" and sep == ","):
            return
        if rest.strip():
            if self._prosey(seg):
                return
            self.mark("blocks", seg, m.start("rest"), len(seg.text))
        self._continue(seg, [seg], "blocks", max_lines=6)

    def _ms_all(self):
        ft, n = self.ft, len(self.ft)
        for i, tk in enumerate(ft):
            if not re.fullmatch(r"M\s*/\s*[sS]\.?", tk):
                continue
            seg, k = self.flow[i]
            rest = seg.text[seg.spans[k][1]:].split()
            lower = [w for w in rest if w[:1].islower() and w.lower() not in CONN]
            block = (k == 0 and len(rest) <= 8 and not lower and not self._prosey(seg))
            if block:
                self.mark("business", seg, 0, len(seg.text))
                self._continue(seg, [seg], "business", max_lines=4)
                continue
            toks, j = [i], i + 1
            while j < n and len(toks) < 9:
                t2 = ft[j]
                core = t2.strip(",;:")
                if not (iscap(core) or core.lower() in CONN or core == "&"):
                    break
                if t2.endswith(":") or (core.lower().strip("()-") in _LABEL_WORDS
                                        and self.flow[j][0].rid != self.flow[j - 1][0].rid):
                    break                                # the next field's label, e.g. "GSTIN of the Taxpayer:"
                toks.append(j)
                if t2[-1] in ",;:":
                    break
                j += 1
            if len(toks) > 1:
                self.mark_tokens("business", toks)

    def _pin_lines(self, seg: Seg):
        if not self.cfg.enabled("address"):
            return
        t = seg.text
        if not _PIN_RE.search(t) or self.label_like(seg) or self._prosey(seg) or len(t.split()) > 16:
            return
        if re.search(r"\brs\.?\s*\d|\u20b9|/-|\b(?:tax|interest|penalty|fine|fee|demand|amount|total|dated|"
                     r"refund|turnover|itc|igst|cgst|sgst)\b", t, I):
            return
        if not ("," in t or _STATE_RE.search(t) or re.search(r"\bpin(?:code)?\b", t, I)):
            return
        if len(re.findall(r"[A-Za-z]{2,}", t)) < 2:
            return
        self.mark("address", seg, 0, len(t))
        cur = seg
        for _ in range(3):
            p = self.above(cur, 2.2)
            if p is None or not p.text.rstrip().endswith(",") or not _aligned(p, cur) or self.is_stop(p):
                break
            self.mark("address", p, 0, len(p.text))
            cur = p

    def _name_before_ids(self):
        """'... supplier J.Y.P SCRAP & METALS - 27AAAAA0000A1Z5' -> the name in front of a GSTIN / PAN."""
        if not (self.cfg.enabled("business") or self.cfg.enabled("names")):
            return
        ft = self.ft
        for i, t in enumerate(ft):
            core = t.strip("()[],.;:")
            if not (_GSTIN_FULL.fullmatch(core) or _PAN_FULL.fullmatch(core)):
                continue
            j = i - 1
            while j >= 0 and ft[j].lower().strip().rstrip(":") in _SKIPBACK:
                j -= 1
            names = []
            while j >= 0 and len(names) < 9:
                tk = ft[j]
                c2 = tk.strip("()[],;:")
                low = c2.lower()
                if (names and tk[-1] in ",;:") or ":" in tk:
                    break
                if low in _STOPCAP and low not in ("and", "of"):
                    break
                if not (iscap(c2) or low in ("&", "and", "of") or c2 == "&"):
                    break
                if c2[:1].isdigit():
                    break
                names.append(j)
                j -= 1
            while names and ft[names[-1]].lower() in ("and", "of", "&"):
                names.pop()
            if names:
                names.reverse()
                self.mark_tokens("business", names)

    def _cue_names(self):
        """'the supplier J.Y.P SCRAP & METALS has ...' -> an upper-case run right after supplier/taxpayer/dealer."""
        if not self.cfg.enabled("business"):
            return
        ft, n = self.ft, len(self.ft)
        for i, t in enumerate(ft):
            if t.lower().strip(",.:;") not in _CUES:
                continue
            j, run = i + 1, []
            while j < n and len(run) < 8:
                tk = ft[j]
                core = tk.strip(",;:()")
                if core == "&" or core.upper() == "AND":
                    run.append(j)
                elif core.upper() == core and re.search(r"[A-Z]", core) and core.upper() not in _ACR:
                    run.append(j)
                else:
                    break
                if tk[-1] in ",;:" or tk.startswith("("):
                    break
                j += 1
            while run and ft[run[-1]].strip(",;:").upper() in ("&", "AND"):
                run.pop()
            if len(run) >= 2:
                self.mark_tokens("business", run)

    def _split_ids(self):
        """GSTIN / PAN printed in two pieces: '27AYYPP0719' + 'R1ZA' (wrapped table cell or line break)."""
        tests = [(c, rx) for c, rx in (("gstin", _GSTIN_FULL), ("pan", _PAN_FULL)) if self.cfg.enabled(c)]
        if not tests:
            return

        def try_join(a_seg, a_k, b_seg, b_k):
            a = a_seg.text[a_seg.spans[a_k][0]:a_seg.spans[a_k][1]]
            b = b_seg.text[b_seg.spans[b_k][0]:b_seg.spans[b_k][1]]
            ca, cb = a.strip("(),;:.[]").rstrip("-"), b.strip("(),;:.[]")
            if not (ca and cb) or not re.fullmatch(r"[0-9A-Za-z]+", ca + cb):
                return
            joined = (ca + cb).upper()
            for cat, rx in tests:
                if rx.fullmatch(joined) and not rx.fullmatch(ca.upper()):
                    parts = [(a_seg, a_seg.spans[a_k][0], a_seg.spans[a_k][1]),
                             (b_seg, b_seg.spans[b_k][0], b_seg.spans[b_k][1])]
                    if self.mark_parts(cat, parts):
                        self.hits[-1].chunks = [joined]
                    else:
                        self.hits.append(Hit(cat, [joined], []))
                    return
        for seg in self.segs:                                 # wrapped table cell (piece below)
            for k, wi in enumerate(seg.wi):
                w = self.words[wi]
                core = w.text.strip("(),;:.[]-")
                if not (7 <= len(core) <= 14 and core[:2].isdigit()):
                    continue
                for nb in self._next_row_segs(seg):           # the word directly under this one
                    for k2, wi2 in enumerate(nb.wi):
                        u = self.words[wi2]
                        if min(w.x1, u.x1) - max(w.x0, u.x0) > 0 or abs(u.x0 - w.x0) < 4:
                            try_join(seg, k, nb, k2)
                            break
        for i in range(len(self.flow) - 1):                   # running text / space inside the number
            (sa, ka), (sb, kb) = self.flow[i], self.flow[i + 1]
            try_join(sa, ka, sb, kb)

    # ---- layer 3: manual list + propagation -----------------------------------------
    @staticmethod
    def _rx_for(text: str):
        toks = text.split()
        if not toks:
            return None
        body = r"\s+".join(re.escape(x) for x in toks)
        return re.compile(r"(?<![A-Za-z0-9])" + body + r"(?![A-Za-z0-9])", I)

    def _next_row_segs(self, seg: Seg) -> list:
        """Segments on the next line that overlap this segment horizontally (cells of a wrapped table row)."""
        out = []
        for s in self.segs:
            dy = s.yc - seg.yc
            if 0.6 * min(seg.h, s.h) <= dy <= 1.9 * max(seg.h, s.h) and min(s.x1, seg.x1) - max(s.x0, seg.x0) > 0:
                out.append(s)
        if out:
            top = min(s.yc for s in out)
            out = [s for s in out if s.yc - top < 0.5 * seg.h]
        return sorted(out, key=lambda s: s.x0)

    def _search_list(self, items):
        for rx, cat, multi in items:                       # across line breaks, in reading order
            for m in rx.finditer(self.fstr):
                self.mark_tokens(cat, self._tok_range(m.start(), m.end()))
        for seg in self.segs:                              # table cells that wrap
            t = seg.text
            nxt, nxt_loaded = None, False
            for rx, cat, multi in items:
                if not multi:
                    continue
                if not nxt_loaded:
                    nxt = self._next_row_segs(seg)
                    nxt_loaded = True
                for nb in nxt:
                    j = t + " " + nb.text
                    for m in rx.finditer(j):
                        if m.start() < len(t) and m.end() > len(t) + 1:
                            self.mark_parts(cat, [(seg, m.start(), len(t)), (nb, 0, m.end() - len(t) - 1)])

    # ---- driver ------------------------------------------------------------------
    def run(self, entities: Optional[Dict[str, str]] = None, contextual: bool = True,
            officer_keys=(), addr_keys=()) -> List[Hit]:
        self.hits, self._marked = [], set()
        self.prot_all, self.prot_name, self.prot_off, self.officer_keys = set(), set(), set(), set()
        self.addr_keys = []
        self._compute_protection(officer_keys)
        for seg in self.segs:
            self._patterns(seg)
        self._split_ids()
        if contextual:
            self._name_before_ids()
            self._cue_names()
            for seg in self.segs:
                self._labels(seg)
                self._headers(seg)
                self._columns(seg)
                self._pin_lines(seg)
            self._ms_all()
        items = []
        if self.cfg.enabled("manual"):
            for nm in self.cfg.manual_names:
                rx = self._rx_for(nm)
                if rx is not None and len(nm.strip()) >= 2:
                    items.append((rx, "manual", len(nm.split()) > 1))
        if entities:
            for key, cat in sorted(entities.items(), key=lambda kv: -len(kv[0])):
                rx = self._rx_for(key)
                if rx is not None:
                    items.append((rx, cat, len(key.split()) > 1))
        if items:
            self._search_list(items)
        if contextual and addr_keys:
            self._addr_fuzzy(list(addr_keys))
        return self.hits

    def rects(self):
        return [r for h in self.hits for r in h.rects]

    def counts(self) -> Counter:
        return Counter(h.cat for h in self.hits if h.rects)


# --------------------------------------------------------------------------- #
# Entity propagation across the whole document
# --------------------------------------------------------------------------- #
_PROPAGATE = {"names", "business", "blocks", "address", "pan", "gstin", "aadhaar", "govt_ids",
              "phone", "email", "financial", "digital"}
_PREFIX_STRIP = re.compile(r"^(?:m\s*/\s*s\b\.?|(?i:mrs|mr|ms|miss|shri|shree|smt|sri|dr|prof)\b\.?|"
                           r"(?i:[sdwch]/o|care\s+of)\.?)\s*")
_GENERIC = {"the", "of", "and", "supplier", "suppliers", "taxpayer", "recipient", "buyer", "dealer", "customer",
            "vendor", "party", "seller", "consignee", "name", "trade", "legal", "address", "gstin", "pan", "no",
            "m/s", "ms", "firm", "business", "limited", "ltd", "pvt", "private", "co", "company", "if", "any",
            "&", "invoice", "date", "state", "india", "act", "tax", "goods", "services"}


def entity_keys(chunk: str, cat: str, cfg: Config) -> List[str]:
    t = chunk.strip().strip(",;:.|-\u2013\u2014 ")
    variants = {t}
    t2 = _PREFIX_STRIP.sub("", t).strip(",;:.|- ")
    if t2:
        variants.add(t2)
    out = []
    for v in variants:
        k = _norm_key(v)
        if len(k) < 4 or k in _NA_VALUES:
            continue
        letters = sum(c.isalpha() for c in k)
        digits = sum(c.isdigit() for c in k)
        if letters == 0 and digits < 6:
            continue
        if cat in ("names", "business", "blocks"):
            toks = re.findall(r"[a-z0-9&/]+", k)
            if all(x in _GENERIC for x in toks) or _LOWER_START.match(v):
                continue
            if cat != "blocks" and len(toks) > 8:
                continue
            if len([x for x in toks if x not in ("&", "/")]) < 2:
                continue
        if cat in ("address", "blocks") and not (len(k) >= 10 and (" " in k or digits)):
            continue
        out.append(k)
    return out


def collect_entities(all_hits: List[Hit], cfg: Config, skip=()) -> Dict[str, str]:
    skipl = list(skip)
    ents: Dict[str, str] = {}

    def skipped(k: str) -> bool:
        return any(k == sk or re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", sk) for sk in skipl)

    for h in all_hits:
        if h.cat not in _PROPAGATE:
            continue
        for ch in h.chunks:
            for k in entity_keys(ch, h.cat, cfg):
                if skipl and h.cat in ("names", "business", "manual") and skipped(k):
                    continue
                ents.setdefault(k, h.cat)
            if h.cat == "gstin" and cfg.enabled("pan"):
                d = re.sub(r"\s", "", ch)
                if len(d) == 15:
                    ents.setdefault(d[2:12].lower(), "pan")
    return ents


# --------------------------------------------------------------------------- #
# OCR engine (Tesseract): located automatically, installed automatically on first opening
# --------------------------------------------------------------------------- #
OCR_LANGS = ("eng", "hin", "mar")                     # English, Hindi, Marathi language files
TESSDATA_URL = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/{}.traineddata"
TESS_RELEASE_API = "https://api.github.com/repos/tesseract-ocr/tesseract/releases/latest"
TESS_FALLBACK_URLS = [
    "https://github.com/tesseract-ocr/tesseract/releases/download/5.5.3/tesseract-ocr-w64-setup-5.5.3.20260724.exe",
    "https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe",
]
WINGET_IDS = ("tesseract-ocr.tesseract", "UB-Mannheim.TesseractOCR")


def app_data_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    d = os.path.join(base, "GSTwithNihal")
    os.makedirs(d, exist_ok=True)
    return d


def user_tessdata() -> str:
    d = os.path.join(app_data_dir(), "tessdata")
    os.makedirs(d, exist_ok=True)
    return d


def _state_path() -> str:
    return os.path.join(app_data_dir(), "setup.json")


def _load_state() -> dict:
    import json
    try:
        with open(_state_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save_state(st: dict):
    import json
    try:
        with open(_state_path(), "w", encoding="utf-8") as fh:
            json.dump(st, fh, indent=1)
    except Exception:
        pass


def _registry_tesseract() -> List[str]:
    out = []
    if os.name != "nt":
        return out
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for key in (r"SOFTWARE\Tesseract-OCR", r"SOFTWARE\WOW6432Node\Tesseract-OCR"):
                try:
                    with winreg.OpenKey(hive, key) as k:
                        p = winreg.QueryValueEx(k, "InstallDir")[0]
                        out.append(os.path.join(p, "tesseract.exe"))
                except OSError:
                    pass
    except Exception:
        pass
    return out


def find_tesseract(custom: str = "") -> Optional[str]:
    cands = []
    if custom:
        cands.append(custom)
    saved = _load_state().get("tesseract")
    if saved:
        cands.append(saved)
    w = shutil.which("tesseract")
    if w:
        cands.append(w)
    cands += _registry_tesseract()
    for env in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(env)
        if base:
            cands.append(os.path.join(base, "Tesseract-OCR", "tesseract.exe"))
            cands.append(os.path.join(base, "Programs", "Tesseract-OCR", "tesseract.exe"))
    cands += [r"C:\Program Files\Tesseract-OCR\tesseract.exe",
              r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
              "/usr/bin/tesseract", "/usr/local/bin/tesseract", "/opt/homebrew/bin/tesseract"]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def _download(url: str, dest: str, log: Callable[[str], None], timeout: int = 120) -> bool:
    import urllib.request
    tmp = dest + ".part"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GSTwithNihal-Redaction-Tool"})
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as fh:
            total = int(resp.headers.get("Content-Length") or 0)
            got, last = 0, -1
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                fh.write(chunk)
                got += len(chunk)
                if total:
                    pct = int(got * 100 / total)
                    if pct // 25 != last:
                        last = pct // 25
                        log(f"   downloading {os.path.basename(dest)} ... {pct}%")
        if os.path.getsize(tmp) < 1000:
            raise IOError("download too small")
        os.replace(tmp, dest)
        return True
    except Exception as exc:
        log(f"   download failed ({type(exc).__name__}: {exc})")
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def _installer_url(log) -> List[str]:
    import json
    import urllib.request
    urls = []
    try:
        req = urllib.request.Request(TESS_RELEASE_API, headers={"User-Agent": "GSTwithNihal-Redaction-Tool",
                                                                "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        for a in data.get("assets", []):
            if re.search(r"w64-setup.*\.exe$", a.get("name", ""), I):
                urls.append(a["browser_download_url"])
    except Exception as exc:
        log(f"   could not read the latest release list ({type(exc).__name__}); using a known version")
    return urls + [u for u in TESS_FALLBACK_URLS if u not in urls]


def install_tesseract(log: Callable[[str], None] = print) -> Optional[str]:
    """Install the Tesseract OCR program (Windows). Windows will ask once for permission (UAC)."""
    if os.name != "nt":
        log("Automatic installation is only available on Windows. Install Tesseract with your package "
            "manager (e.g. 'sudo apt install tesseract-ocr' or 'brew install tesseract').")
        return find_tesseract()
    flags = 0x08000000                                     # no console window
    winget = shutil.which("winget")
    if winget:
        for wid in WINGET_IDS:
            log(f"Installing Tesseract OCR with winget ({wid}) - please click 'Yes' if Windows asks ...")
            try:
                subprocess.run([winget, "install", "-e", "--id", wid, "--silent", "--accept-package-agreements",
                                "--accept-source-agreements", "--disable-interactivity"],
                               capture_output=True, text=True, timeout=900, creationflags=flags)
            except Exception as exc:
                log(f"   winget did not finish ({type(exc).__name__})")
            exe = find_tesseract()
            if exe:
                return exe
    folder = tempfile.mkdtemp(prefix="gwn_tess_")
    try:
        for url in _installer_url(log):
            dest = os.path.join(folder, os.path.basename(url))
            log(f"Downloading the Tesseract installer: {os.path.basename(url)}")
            if not _download(url, dest, log, timeout=300):
                continue
            log("Running the installer - please click 'Yes' when Windows asks for permission ...")
            ps = ("Start-Process -FilePath '{}' -ArgumentList '/S' -Verb RunAs -Wait"
                  .format(dest.replace("'", "''")))
            try:
                subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                               capture_output=True, text=True, timeout=900, creationflags=flags)
            except Exception as exc:
                log(f"   installer did not finish ({type(exc).__name__})")
            exe = find_tesseract()
            if exe:
                return exe
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return None


def ensure_languages(log: Callable[[str], None] = print, langs=OCR_LANGS) -> bool:
    """English / Hindi / Marathi language files, kept in the user's own folder (no admin rights needed)."""
    td = user_tessdata()
    ok = True
    for lg in langs:
        dest = os.path.join(td, lg + ".traineddata")
        if os.path.isfile(dest) and os.path.getsize(dest) > 1000:
            continue
        log(f"Downloading OCR language file: {lg}")
        ok = _download(TESSDATA_URL.format(lg), dest, log) and ok
    return ok


def ensure_ocr_engine(log: Callable[[str], None] = print, force: bool = False) -> Optional[str]:
    """First opening: find (or install) Tesseract and its language files. Later openings: only a quick check.
    force=True is used by the 'Install / repair OCR' button."""
    st = _load_state()
    exe = find_tesseract()
    if not exe and (force or not st.get("tesseract_attempted")):
        log("\nOCR engine (Tesseract) not found - setting it up (first opening only).")
        st["tesseract_attempted"] = True
        _save_state(st)
        exe = install_tesseract(log)
        log("OCR engine installed: " + exe if exe else
            "OCR engine could not be installed automatically. The tool works normally for text PDFs; "
            "use 'Install / repair OCR' in the window to try again.")
    if exe:
        st["tesseract"] = exe
        missing = [lg for lg in OCR_LANGS
                   if not os.path.isfile(os.path.join(user_tessdata(), lg + ".traineddata"))]
        if missing and (force or not st.get("langs_attempted")):
            st["langs_attempted"] = True
            _save_state(st)
            ensure_languages(log, missing)
    _save_state(st)
    return exe


def _available_langs(exe: str) -> Dict[str, str]:
    """language code -> tessdata folder that holds it (user folder preferred)."""
    out: Dict[str, str] = {}
    folders = [user_tessdata()]
    if exe:
        folders.append(os.path.join(os.path.dirname(exe), "tessdata"))
    for env in ("TESSDATA_PREFIX",):
        if os.environ.get(env):
            folders.append(os.environ[env])
    folders += ["/usr/share/tesseract-ocr/5/tessdata", "/usr/share/tesseract-ocr/4.00/tessdata",
                "/usr/local/share/tessdata", "/opt/homebrew/share/tessdata"]
    for f in folders:
        try:
            for name in os.listdir(f):
                if name.endswith(".traineddata"):
                    out.setdefault(name[:-12], f)
        except OSError:
            pass
    return out


def _ocr_lang_setup(cfg: Config, exe: str) -> str:
    """Pick the language string and point Tesseract at a folder that contains all of it."""
    avail = _available_langs(exe)
    want = [x for x in re.split(r"[+,\s]+", cfg.ocr_lang or "eng") if x] or ["eng"]
    use = [x for x in want if x in avail] or (["eng"] if "eng" in avail else [])
    if not use:
        return cfg.ocr_lang or "eng"
    folders = {avail[x] for x in use}
    if len(folders) == 1:
        os.environ["TESSDATA_PREFIX"] = folders.pop()
    else:                                   # mixed folders: use the user folder copy of everything
        td = user_tessdata()
        for x in use:
            src = os.path.join(avail[x], x + ".traineddata")
            dst = os.path.join(td, x + ".traineddata")
            if not os.path.isfile(dst):
                try:
                    shutil.copyfile(src, dst)
                except OSError:
                    pass
        os.environ["TESSDATA_PREFIX"] = td
    return "+".join(use)


def ocr_status(cfg: Config) -> str:
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except Exception:
        return "OCR not available: run  pip install pytesseract pillow"
    exe = find_tesseract(cfg.tesseract_cmd)
    if not exe:
        return "OCR not available: Tesseract program not found - click 'Install / repair OCR'"
    langs = "+".join(sorted(k for k in _available_langs(exe) if k in OCR_LANGS)) or "none"
    return f"OCR ready: {exe}   (languages: {langs})"


def _ocr_words(page, cfg: Config, fitz, rotation: int, clip=None) -> List[Word]:
    """OCR the page (or only the 'clip' rectangle, unrotated pages only). Returns words in rotation-0 points."""
    import pytesseract
    from PIL import Image
    exe = find_tesseract(cfg.tesseract_cmd)
    pytesseract.pytesseract.tesseract_cmd = exe
    lang = _ocr_lang_setup(cfg, exe)
    if clip is not None:
        pix = page.get_pixmap(dpi=cfg.ocr_dpi, alpha=False, clip=clip)
        dm, ox, oy = None, clip.x0, clip.y0
    else:
        if rotation:
            page.set_rotation(rotation)          # render the page the way it is displayed
        dm = fitz.Matrix(page.derotation_matrix)
        pix = page.get_pixmap(dpi=cfg.ocr_dpi, alpha=False)
        if rotation:
            page.set_rotation(0)
        ox = oy = 0.0
    if pix.width < 20 or pix.height < 20:
        return []
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    data = pytesseract.image_to_data(img, lang=lang, config=f"--psm {cfg.ocr_psm}",
                                     output_type=pytesseract.Output.DICT)
    sc = 72.0 / cfg.ocr_dpi
    out = []
    for i, txt in enumerate(data["text"]):
        if not txt or not txt.strip() or not re.search(r"[A-Za-z0-9\u0900-\u097F]", txt):
            continue
        try:   # unsure words are dropped as noise - except number-like words (GSTIN, PAN, phone ...)
            if float(data["conf"][i]) < 20 and not re.search(r"\d", txt):
                continue
        except (TypeError, ValueError):
            pass
        l, t, w, h = (data[k][i] for k in ("left", "top", "width", "height"))
        r = fitz.Rect(ox + l * sc, oy + t * sc, ox + (l + w) * sc, oy + (t + h) * sc)
        if dm is not None:
            r = r * dm
        r.normalize()
        out.append(Word(r.x0, r.y0, r.x1, r.y1, txt.strip(), True))
    return out


def _picture_boxes(page, fitz, small: bool) -> list:
    """Pictures on the page that can hold readable text (scans, screenshots, stamps)."""
    pa = abs(page.rect) or 1.0
    min_share = 0.005 if small else 0.03
    boxes = []
    try:
        infos = page.get_image_info()
    except Exception:
        infos = []
    for inf in infos:
        r = fitz.Rect(inf["bbox"]) & page.rect
        if r.is_empty or r.width < 20 or r.height < 8:
            continue
        if abs(r) / pa >= min_share:
            boxes.append(r)
    return boxes


def _page_words(page, cfg: Config, fitz, tess_ok: bool):
    """Return (words in rotation-0 coordinates, ocr_used). Leaves page rotation unchanged.
    With OCR available, scanned pages AND pictures inside normal pages are read automatically."""
    rot = page.rotation
    if rot:
        page.set_rotation(0)
    try:
        words = [Word(w[0], w[1], w[2], w[3], w[4]) for w in page.get_text("words") if w[4].strip()]
        ocr_used = False
        if cfg.ocr and tess_ok:
            pics = _picture_boxes(page, fitz, cfg.ocr_all_image_pages)
            ow: List[Word] = []
            if len(words) < 10:                                   # scanned page: read all of it
                ow = _ocr_words(page, cfg, fitz, rot)
            elif pics:                                            # text page with pictures: read the pictures
                if rot:
                    full = _ocr_words(page, cfg, fitz, rot)
                    ow = [o for o in full if any(p.contains(fitz.Point((o.x0 + o.x1) / 2, (o.y0 + o.y1) / 2))
                                                 for p in pics)]
                else:
                    for p in pics[:15]:
                        ow += _ocr_words(page, cfg, fitz, 0, clip=p)
            if ow:
                if words:   # merge: keep OCR words that do not overlap real text
                    keep = []
                    for o in ow:
                        cx, cy = (o.x0 + o.x1) / 2, (o.y0 + o.y1) / 2
                        if not any(w.x0 <= cx <= w.x1 and w.y0 <= cy <= w.y1 for w in words):
                            keep.append(o)
                    ow = keep
                words += ow
                ocr_used = True
            elif len(words) < 10 or pics:
                ocr_used = True                                   # OCR ran (nothing readable found)
        return words, ocr_used
    finally:
        if rot:
            page.set_rotation(rot)


# --------------------------------------------------------------------------- #
# PDF processing
# --------------------------------------------------------------------------- #
ProgressCB = Callable[[float, str], None]


def _apply(page, fitz, rects) -> int:
    """Add redaction annotations and apply them. Returns number of rects."""
    for r in rects:
        rr = fitz.Rect(*r)
        if rr.is_empty or rr.is_infinite:
            continue
        page.add_redact_annot(rr, fill=(0, 0, 0))
    kw = {"images": fitz.PDF_REDACT_IMAGE_PIXELS}
    if hasattr(fitz, "PDF_REDACT_LINE_ART_NONE"):
        kw["graphics"] = fitz.PDF_REDACT_LINE_ART_NONE      # keep table borders / lines
    try:
        page.apply_redactions(**kw)
    except TypeError:
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
    return len(rects)


def _leftover_in_rects(page, rects) -> int:
    n = 0
    for w in page.get_text("words"):
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        if any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in rects):
            n += 1
    return n


def process_pdf(src: str, dst: str, cfg: Config, cb: Optional[ProgressCB] = None,
                should_cancel: Callable[[], bool] = lambda: False) -> dict:
    fitz = _import_fitz()
    cb = cb or (lambda f, m: None)
    res = {"file": src, "output": dst, "pages": 0, "ocr_pages": 0, "counts": Counter(),
           "per_page": [], "leftover": Counter(), "leftover_items": [], "warnings": [], "error": ""}
    doc = fitz.open(src)
    try:
        if doc.needs_pass:
            res["error"] = "Password-protected PDF - remove the password first."
            return res
        res["pages"] = len(doc)
        tess_ok = cfg.ocr and ocr_status(cfg).startswith("OCR ready")
        if cfg.ocr and not tess_ok:
            res["warnings"].append(ocr_status(cfg))
        if cfg.flatten_forms:
            try:
                doc.bake(annots=True, widgets=True)
            except Exception:
                pass

        n = len(doc)
        # ---- pass 1: read every page and detect --------------------------------------
        dets: List[Detector] = []
        ocr_pages = set()
        all_hits: List[Hit] = []
        officer_keys: set = set()
        addr_keys: set = set()
        for i in range(n):
            if should_cancel():
                res["error"] = "Cancelled"
                return res
            cb(0.45 * i / n, f"Reading page {i + 1}/{n}")
            words, used = _page_words(doc[i], cfg, fitz, tess_ok)
            if used:
                ocr_pages.add(i)
            elif not tess_ok and (len(words) < 10 or _picture_boxes(doc[i], fitz, False)) and doc[i].get_images():
                res["warnings"].append(f"Page {i + 1} contains a scan / picture that was NOT read "
                                       "(OCR engine missing or OCR switched off) - check it in the review window.")
            det = Detector(words, cfg)
            all_hits += det.run(None)
            officer_keys |= det.officer_keys
            addr_keys |= set(det.addr_keys)
            dets.append(det)
        entities = collect_entities(all_hits, cfg, officer_keys)
        for k in addr_keys:                       # the full addresses are searched as they are, too
            entities.setdefault(k, "address")

        # ---- pass 2: detect again with document-wide entities, redact ----------------
        for i in range(n):
            if should_cancel():
                res["error"] = "Cancelled"
                return res
            cb(0.45 + 0.45 * i / n, f"Redacting page {i + 1}/{n}")
            det = dets[i]
            det.run(entities, officer_keys=officer_keys, addr_keys=addr_keys)
            rects = det.rects()
            cnt = det.counts()
            res["counts"].update(cnt)
            res["per_page"].append((i + 1, dict(cnt)))
            if not rects:
                continue
            page = doc[i]
            rot = page.rotation
            if rot:
                page.set_rotation(0)
            _apply(page, fitz, rects)
            left = _leftover_in_rects(page, rects)
            if left:                                   # second attempt
                _apply(page, fitz, rects)
                left = _leftover_in_rects(page, rects)
                if left:
                    res["warnings"].append(f"Page {i + 1}: {left} word(s) could not be removed from the text layer.")
            if rot:
                page.set_rotation(rot)
        res["ocr_pages"] = len(ocr_pages)

        # ---- clean-up ---------------------------------------------------------------
        cb(0.92, "Cleaning metadata and saving")
        if cfg.strip_metadata:
            try:
                doc.set_metadata({})
            except Exception:
                pass
            try:
                doc.del_xml_metadata()
            except Exception:
                pass
            try:
                doc.set_toc([])
            except Exception:
                pass
            try:
                doc.scrub(hidden_text=False)
            except Exception:
                pass
        os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
        doc.save(dst, garbage=4, deflate=True, clean=True)
    except Exception as exc:  # noqa
        res["error"] = f"{type(exc).__name__}: {exc}"
        res["warnings"].append(traceback.format_exc(limit=3))
        return res
    finally:
        doc.close()

    # ---- leftover check on the saved file (patterns only; never uses labels) ---------
    try:
        cb(0.95, "Checking the redacted file")
        res["leftover"], res["leftover_items"] = leftover_scan(dst, cfg, ocr_pages if tess_ok else set())
    except Exception as exc:  # noqa
        res["warnings"].append(f"Leftover check failed: {exc}")
    cb(1.0, "Done")
    return res


def leftover_scan(path: str, cfg: Config, ocr_pages=frozenset()):
    """Pattern-only re-check of a redacted file.
    Returns (Counter of categories, [(page_no, category, text, [rects in unrotated page points]), ...])."""
    fitz = _import_fitz()
    cnt, items = Counter(), []
    tess_ok = bool(ocr_pages) and cfg.ocr and ocr_status(cfg).startswith("OCR ready")
    chk = fitz.open(path)
    try:
        for i in range(len(chk)):
            words, _ = _page_words(chk[i], cfg, fitz, tess_ok and i in ocr_pages)
            d = Detector(words, cfg)
            d.run(None, contextual=False)
            for h in d.hits:
                if h.rects:
                    cnt[h.cat] += 1
                    items.append((i + 1, h.cat, " ".join(h.chunks), [tuple(r) for r in h.rects]))
    finally:
        chk.close()
    return cnt, items


def out_path_for(src: str, out_dir: str = "") -> str:
    stem = os.path.splitext(os.path.basename(src))[0]
    folder = out_dir or os.path.dirname(os.path.abspath(src))
    p = os.path.join(folder, f"{stem}_redacted.pdf")
    if os.path.abspath(p) == os.path.abspath(src):
        p = os.path.join(folder, f"{stem}_redacted_1.pdf")
    return p


def write_report(results: List[dict], folder: str) -> str:
    """CSV with counts only - it never contains the redacted text itself."""
    path = os.path.join(folder, "redaction_report.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["file", "page", "category", "items redacted"])
        for r in results:
            for page, cnt in r.get("per_page", []):
                for cat, n in cnt.items():
                    w.writerow([os.path.basename(r["file"]), page, CAT_LABEL.get(cat, cat), n])
            for cat, n in r.get("leftover", {}).items():
                w.writerow([os.path.basename(r["file"]), "leftover-check", CAT_LABEL.get(cat, cat), n])
    return path


def summarize(r: dict) -> str:
    if r["error"]:
        return f"{os.path.basename(r['file'])}: FAILED - {r['error']}"
    total = sum(r["counts"].values())
    left = sum(r["leftover"].values())
    s = f"{os.path.basename(r['file'])}: {total} items redacted on {r['pages']} page(s)"
    if r["ocr_pages"]:
        s += f", OCR used on {r['ocr_pages']} page(s)"
    s += f". Leftover check: {'clean' if not left else str(left) + ' possible leftover(s) - review!'}"
    return s


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #
def run_cli(argv: List[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=APP_NAME)
    ap.add_argument("files", nargs="+")
    ap.add_argument("-o", "--out", default="", help="output folder (default: next to each file)")
    ap.add_argument("--ocr", action="store_true", help="(default) read scanned pages and pictures")
    ap.add_argument("--no-ocr", action="store_true", help="do not use OCR")
    ap.add_argument("--names", default="", help="text file with one name per line")
    a = ap.parse_args(argv)
    cfg = Config()
    cfg.ocr = not a.no_ocr
    if a.names:
        with open(a.names, encoding="utf-8") as f:
            cfg.manual_names = [x.strip() for x in f if x.strip()]
    results = []
    for f in a.files:
        r = process_pdf(f, out_path_for(f, a.out), cfg, lambda p, m: None)
        print(summarize(r))
        for w in r["warnings"]:
            print("   !", w)
        results.append(r)
    if results:
        print("Report:", write_report(results, a.out or os.path.dirname(os.path.abspath(a.files[0]))))
    return 0


# --------------------------------------------------------------------------- #
# Window (PyQt6)
# --------------------------------------------------------------------------- #
ACCENT = {
    "files": "#2563EB",     # blue
    "what": "#EA580C",      # orange
    "protect": "#059669",   # green
    "names": "#DB2777",     # pink
    "options": "#7C3AED",   # violet
    "results": "#0891B2",   # cyan
}

STYLE = """
QWidget { font-family: "Segoe UI", "Helvetica Neue", Arial; font-size: 10pt; color: #0F172A; }
QMainWindow { background: #EEF2FF; }
QWidget#page { background: #EEF2FF; }
QScrollArea#scroll { background: #EEF2FF; border: 0; }
QLabel { background: transparent; }
QLabel#hint { color: #475569; }
QLabel#count { color: #2563EB; font-weight: 600; }
QPushButton { background: #FFFFFF; color: #1E293B; border: 1px solid #CBD5E1; border-radius: 8px;
              padding: 7px 14px; font-weight: 600; }
QPushButton:hover { background: #EEF2FF; border-color: #6366F1; color: #3730A3; }
QPushButton:pressed { background: #E0E7FF; }
QPushButton:disabled { background: #F1F5F9; color: #94A3B8; border-color: #E2E8F0; }
QPushButton#start { color: #FFFFFF; border: 0; padding: 10px 30px; font-size: 11pt; font-weight: 700;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F97316, stop:1 #DB2777); }
QPushButton#start:hover { color: #FFFFFF;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EA580C, stop:1 #BE185D); }
QPushButton#start:disabled { color: #FFFFFF; background: #F4B6A2; }
QPushButton#cancel:enabled { color: #B91C1C; border-color: #FCA5A5; }
QPushButton#cancel:enabled:hover { background: #FEF2F2; }
QLineEdit, QPlainTextEdit, QListWidget, QTableWidget, QSpinBox, QComboBox {
    background: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 8px; padding: 5px;
    selection-background-color: #6366F1; selection-color: #FFFFFF; }
QLineEdit:focus, QPlainTextEdit:focus, QListWidget:focus, QSpinBox:focus, QComboBox:focus {
    border: 2px solid #6366F1; }
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled { background: #F1F5F9; color: #94A3B8; }
QCheckBox { spacing: 9px; background: transparent; padding: 3px 0; }
QCheckBox:disabled { color: #94A3B8; }
QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #94A3B8; border-radius: 5px; background: #FFFFFF; }
QCheckBox::indicator:hover { border-color: #6366F1; }
QCheckBox::indicator:disabled { background: #F1F5F9; border-color: #CBD5E1; }
QHeaderView::section { background: #E0E7FF; color: #1E1B4B; padding: 6px; border: 0;
                       border-right: 1px solid #C7D2FE; font-weight: 700; }
QTableWidget { gridline-color: #E2E8F0; }
QProgressBar { border: 1px solid #CBD5E1; border-radius: 10px; background: #FFFFFF; text-align: center;
               color: #0F172A; min-height: 22px; font-weight: 700; }
QProgressBar::chunk { border-radius: 9px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22C55E, stop:0.5 #06B6D4, stop:1 #6366F1); }
QTabWidget::pane { border: 1px solid #E2E8F0; background: #FFFFFF; border-radius: 8px; top: -1px; }
QTabBar::tab { background: #E0E7FF; color: #3730A3; padding: 8px 18px; margin-right: 3px;
               border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: 600; }
QTabBar::tab:selected { background: #FFFFFF; color: #0891B2; }
QScrollBar:vertical { background: transparent; width: 12px; margin: 2px; }
QScrollBar::handle:vertical { background: #C7D2FE; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #818CF8; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 2px; }
QScrollBar::handle:horizontal { background: #C7D2FE; border-radius: 4px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: #818CF8; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QToolTip { background: #1E293B; color: #F8FAFC; border: 0; padding: 6px; }
QFrame#bottombar { background: #FFFFFF; border-top: 1px solid #DDE3F0; }
QMessageBox QLabel { color: #0F172A; }
"""

TICK_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 18 18">'
            '<path d="M3.5 9.5l3.6 3.6L14.5 5.5" fill="none" stroke="#FFFFFF" stroke-width="2.6" '
            'stroke-linecap="round" stroke-linejoin="round"/></svg>')


LOGO_PNG_B64 = (
    "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"
)


def _in_idle() -> bool:
    return "idlelib" in sys.modules


def run_gui() -> int:
    try:
        from PyQt6 import QtCore, QtGui, QtWidgets
    except ImportError as exc:
        print(f"PyQt6 could not be loaded ({exc}).\nRun:  {PIP_LINE}")
        return 1
    Signal = QtCore.pyqtSignal
    Qt = QtCore.Qt
    W = QtWidgets

    def col(h):
        return QtGui.QColor(h)

    # ---------------- helpers that need a running QApplication ----------------
    def make_tick() -> str:
        """White tick image for the coloured check-boxes (SVG if supported, else PNG)."""
        folder = tempfile.gettempdir()
        fmts = {bytes(f).decode(errors="ignore").lower() for f in QtGui.QImageReader.supportedImageFormats()}
        try:
            if "svg" in fmts:
                p = os.path.join(folder, "gstwithnihal_tick.svg")
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(TICK_SVG)
            else:
                p = os.path.join(folder, "gstwithnihal_tick.png")
                pm = QtGui.QPixmap(14, 14)
                pm.fill(Qt.GlobalColor.transparent)
                pa = QtGui.QPainter(pm)
                pa.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
                pen = QtGui.QPen(col("#FFFFFF"), 2.0)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                pa.setPen(pen)
                pa.drawPolyline(QtGui.QPolygonF([QtCore.QPointF(2.7, 7.4), QtCore.QPointF(5.5, 10.2),
                                                 QtCore.QPointF(11.3, 4.3)]))
                pa.end()
                pm.save(p, "PNG")
            return p.replace("\\", "/")
        except Exception:
            return ""

    def make_icon() -> QtGui.QIcon:
        pm = QtGui.QPixmap(64, 64)
        pm.fill(Qt.GlobalColor.transparent)
        pa = QtGui.QPainter(pm)
        pa.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        g = QtGui.QLinearGradient(0, 0, 64, 64)
        g.setColorAt(0, col("#7C3AED"))
        g.setColorAt(0.5, col("#2563EB"))
        g.setColorAt(1, col("#06B6D4"))
        pa.setBrush(QtGui.QBrush(g))
        pa.setPen(Qt.PenStyle.NoPen)
        pa.drawRoundedRect(2, 2, 60, 60, 14, 14)
        pa.setBrush(col("#0F172A"))
        pa.drawRoundedRect(14, 24, 36, 9, 3, 3)
        pa.drawRoundedRect(14, 38, 24, 9, 3, 3)
        pa.end()
        return QtGui.QIcon(pm)

    class OcrSetup(QtCore.QThread):
        line = Signal(str)
        done = Signal(object)

        def run(self):
            try:
                exe = ensure_ocr_engine(lambda t: self.line.emit(t), force=True)
            except Exception as exc:  # noqa
                self.line.emit(f"OCR set-up failed: {exc}")
                exe = None
            self.done.emit(exe)

    # ---------------- background worker ----------------
    class Worker(QtCore.QThread):
        progress = Signal(float, str)
        file_done = Signal(object)
        all_done = Signal(object, str)

        def __init__(self, files, out_dir, cfg, write_csv, review=False, tmpdir=""):
            super().__init__()
            self.files, self.out_dir, self.cfg, self.write_csv = files, out_dir, cfg, write_csv
            self.review, self.tmpdir = review, tmpdir
            self._cancel = False

        def cancel(self):
            self._cancel = True

        def run(self):
            results, csv_path = [], ""
            n = len(self.files)
            for k, f in enumerate(self.files):
                if self._cancel:
                    break
                name = os.path.basename(f)
                final = out_path_for(f, self.out_dir)
                work = final
                if self.review:                     # write to a private temp copy first
                    work = os.path.join(self.tmpdir, f"{k:03d}_{os.path.basename(final)}")
                try:
                    r = process_pdf(f, work, self.cfg,
                                    lambda fr, m, k=k, name=name: self.progress.emit((k + fr) / n, f"{name}: {m}"),
                                    lambda: self._cancel)
                    r["final"], r["cfg"], r["pending"] = final, self.cfg, False
                    if self.review and not r["error"]:
                        if sum(r["leftover"].values()):
                            r["pending"] = True     # held back: saved only from the review window
                        else:
                            os.makedirs(os.path.dirname(os.path.abspath(final)), exist_ok=True)
                            if os.path.exists(final):
                                os.remove(final)
                            shutil.move(work, final)
                            r["output"] = final
                except Exception as exc:  # noqa
                    r = {"file": f, "output": "", "pages": 0, "ocr_pages": 0, "counts": Counter(),
                         "per_page": [], "leftover": Counter(), "leftover_items": [],
                         "warnings": [traceback.format_exc()], "final": final, "pending": False,
                         "error": f"{type(exc).__name__}: {exc}"}
                results.append(r)
                self.file_done.emit(r)
            if self.write_csv and results:
                try:
                    folder = self.out_dir or os.path.dirname(os.path.abspath(self.files[0]))
                    csv_path = write_report(results, folder)
                except Exception:
                    csv_path = ""
            self.all_done.emit(results, csv_path)

    # ---------------- review window: see flagged items page by page, redact, then save ----------------
    class PageView(W.QGraphicsView):
        boxDrawn = Signal(object)            # QRectF in page (display) points
        zoomRequest = Signal(float)
        clicked = Signal(object, bool)       # point in page (display) points, Ctrl held
        lineClicked = Signal(object)         # double-click: the whole line

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setScene(W.QGraphicsScene(self))
            self.setRenderHints(QtGui.QPainter.RenderHint.Antialiasing |
                                QtGui.QPainter.RenderHint.SmoothPixmapTransform)
            self.setBackgroundBrush(col("#CBD5E1"))
            self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            self.setCursor(Qt.CursorShape.CrossCursor)
            self._origin = None
            self._band = None

        def mousePressEvent(self, e):
            if e.button() == Qt.MouseButton.LeftButton:
                self._origin = self.mapToScene(e.position().toPoint())
                self._band = self.scene().addRect(QtCore.QRectF(self._origin, self._origin),
                                                  QtGui.QPen(col("#DC2626"), 0),
                                                  QtGui.QBrush(QtGui.QColor(0, 0, 0, 110)))
                self._band.setZValue(50)
                return
            super().mousePressEvent(e)

        def mouseMoveEvent(self, e):
            if self._band is not None:
                p = self.mapToScene(e.position().toPoint())
                self._band.setRect(QtCore.QRectF(self._origin, p).normalized())
                return
            super().mouseMoveEvent(e)

        def mouseReleaseEvent(self, e):
            if self._band is not None:
                r = self._band.rect()
                self.scene().removeItem(self._band)
                self._band = None
                if r.width() >= 3 and r.height() >= 3:
                    self.boxDrawn.emit(r)
                else:                                   # a plain click: select the word under the mouse
                    self.clicked.emit(self._origin, bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier))
                return
            super().mouseReleaseEvent(e)

        def mouseDoubleClickEvent(self, e):
            if e.button() == Qt.MouseButton.LeftButton:
                self.lineClicked.emit(self.mapToScene(e.position().toPoint()))
                return
            super().mouseDoubleClickEvent(e)

        def wheelEvent(self, e):
            if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.zoomRequest.emit(1.15 if e.angleDelta().y() > 0 else 1 / 1.15)
                return
            super().wheelEvent(e)

    class ReviewDialog(W.QDialog):
        """Shows the redacted file. Flagged leftovers are listed with their page number; clicking one jumps
        to that page and highlights it. The person can redact flagged items or draw extra boxes, and the
        file is written to its destination only when 'Save redacted file' is pressed."""
        saved = Signal(object)

        RENDER = 2.0                        # render scale (pixels per point) for a crisp page

        def __init__(self, parent, r: dict, tick: str):
            super().__init__(parent)
            self.r = r
            self.fitz = _import_fitz()
            self.src = r["output"]
            self.doc = self.fitz.open(self.src)
            self.npages = len(self.doc)
            self.cur = 0
            self.zoom = 1.0
            self.fit = True
            self.items = [{"page": p, "cat": c, "text": t, "rects": rs, "state": "open"}
                          for p, c, t, rs in r.get("leftover_items", [])]
            self.boxes: List[tuple] = []     # (page_no 1-based, rect in unrotated points)
            self.box_groups: List[int] = []  # how many boxes each action added (for Undo)
            self.sel: List[tuple] = []       # selected words: (page_no, rect, text, block, line, word_no)
            self._words: Dict[int, list] = {}
            self.setWindowTitle(f"Review - {os.path.basename(r['file'])}")
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
            scr = QtGui.QGuiApplication.primaryScreen()
            if scr is not None:
                av = scr.availableGeometry()
                self.resize(int(av.width() * 0.9), int(av.height() * 0.9))
            self._build(tick)
            self._fill_list()
            first = self.items[0]["page"] - 1 if self.items else 0
            self.go(first)
            if self.items:
                self.list.setCurrentRow(0)

        # ---------- layout ----------
        def _build(self, tick):
            self.setStyleSheet(
                "QDialog { background: #EEF2FF; }"
                "QListWidget::item { padding: 7px 6px; border-bottom: 1px solid #EEF2FF; }"
                "QListWidget::item:selected { background: #FDE68A; color: #0F172A; }"
                f"QCheckBox::indicator:checked {{ background: #DB2777; border-color: #DB2777;"
                + (f" image: url({tick});" if tick else "") + " }")
            root = W.QVBoxLayout(self)
            root.setContentsMargins(14, 12, 14, 12)
            root.setSpacing(10)

            head = W.QFrame()
            head.setStyleSheet("QFrame { border-radius: 12px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
                               " stop:0 #F97316, stop:1 #DB2777); } QLabel { color: white; background: transparent; }")
            hl = W.QHBoxLayout(head)
            hl.setContentsMargins(18, 10, 18, 10)
            t = W.QLabel(f"Review before saving  •  {os.path.basename(self.r['file'])}")
            t.setStyleSheet("font-size: 13pt; font-weight: 800;")
            hl.addWidget(t, 1)
            self.head_info = W.QLabel("")
            self.head_info.setStyleSheet("font-weight: 600;")
            hl.addWidget(self.head_info)
            root.addWidget(head)

            split = W.QSplitter(Qt.Orientation.Horizontal)
            root.addWidget(split, 1)

            # left: flagged items + my boxes
            left = W.QFrame()
            left.setStyleSheet("QFrame#side { background: #FFFFFF; border: 1px solid #DDE3F0; border-radius: 12px; }")
            left.setObjectName("side")
            lv = W.QVBoxLayout(left)
            lv.setContentsMargins(12, 12, 12, 12)
            lv.setSpacing(8)
            lab = W.QLabel("Flagged items")
            lab.setStyleSheet("color: #DB2777; font-size: 12pt; font-weight: 700;")
            lv.addWidget(lab)
            hint = W.QLabel("Click an item to jump to its page. It is outlined in red on the page.")
            hint.setObjectName("hint")
            hint.setWordWrap(True)
            lv.addWidget(hint)
            self.list = W.QListWidget()
            self.list.currentRowChanged.connect(self._pick)
            lv.addWidget(self.list, 1)
            g = W.QGridLayout()
            g.setSpacing(6)
            self.b_red = W.QPushButton("Redact selected")
            self.b_red.clicked.connect(self._redact_selected)
            self.b_keep = W.QPushButton("Keep as is")
            self.b_keep.setToolTip("Not personal data - leave it visible")
            self.b_keep.clicked.connect(lambda: self._set_state("keep"))
            self.b_all = W.QPushButton("Redact all flagged")
            self.b_all.clicked.connect(self._redact_all)
            g.addWidget(self.b_red, 0, 0)
            g.addWidget(self.b_keep, 0, 1)
            g.addWidget(self.b_all, 1, 0, 1, 2)
            lv.addLayout(g)
            sep = W.QLabel("My own boxes")
            sep.setStyleSheet("color: #7C3AED; font-size: 11pt; font-weight: 700; margin-top: 6px;")
            lv.addWidget(sep)
            h2 = W.QLabel("Anything else to hide?  Click words on the page to select them (double-click selects the "
                          "whole line), then press 'Redact selected'.  Or drag a box over any area.")
            h2.setObjectName("hint")
            h2.setWordWrap(True)
            lv.addWidget(h2)
            self.cb_everywhere = W.QCheckBox("Same text everywhere in the file")
            self.cb_everywhere.setToolTip("Also hides every other place where exactly the same words appear")
            lv.addWidget(self.cb_everywhere)
            self.box_lbl = W.QLabel("No boxes drawn")
            self.box_lbl.setObjectName("count")
            lv.addWidget(self.box_lbl)
            hb = W.QHBoxLayout()
            self.b_undo = W.QPushButton("Undo last box")
            self.b_undo.clicked.connect(self._undo)
            self.b_clear = W.QPushButton("Clear boxes on page")
            self.b_clear.clicked.connect(self._clear_page_boxes)
            hb.addWidget(self.b_undo)
            hb.addWidget(self.b_clear)
            lv.addLayout(hb)
            left.setMinimumWidth(300)
            split.addWidget(left)

            # right: page viewer
            right = W.QWidget()
            rv = W.QVBoxLayout(right)
            rv.setContentsMargins(0, 0, 0, 0)
            rv.setSpacing(6)
            nav = W.QHBoxLayout()
            self.b_prev = W.QPushButton("◀  Previous")
            self.b_prev.clicked.connect(lambda: self.go(self.cur - 1))
            self.b_next = W.QPushButton("Next  ▶")
            self.b_next.clicked.connect(lambda: self.go(self.cur + 1))
            self.spin = W.QSpinBox()
            self.spin.setRange(1, max(1, self.npages))
            self.spin.setButtonSymbols(W.QAbstractSpinBox.ButtonSymbols.NoButtons)
            self.spin.setMinimumWidth(60)
            self.spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.spin.setKeyboardTracking(False)
            self.spin.valueChanged.connect(lambda v: self.go(v - 1))
            nav.addWidget(self.b_prev)
            nav.addWidget(W.QLabel("Page"))
            nav.addWidget(self.spin)
            nav.addWidget(W.QLabel(f"of {self.npages}"))
            nav.addWidget(self.b_next)
            nav.addStretch(1)
            for txt, fn in (("−", lambda: self._zoom_by(1 / 1.2)), ("+", lambda: self._zoom_by(1.2)),
                            ("Fit width", self._fit_width)):
                b = W.QPushButton(txt)
                b.clicked.connect(fn)
                nav.addWidget(b)
            rv.addLayout(nav)
            self.view = PageView()
            self.view.boxDrawn.connect(self._box_drawn)
            self.view.zoomRequest.connect(self._zoom_by)
            self.view.clicked.connect(self._word_clicked)
            self.view.lineClicked.connect(self._line_clicked)
            rv.addWidget(self.view, 1)
            split.addWidget(right)
            split.setStretchFactor(0, 0)
            split.setStretchFactor(1, 1)
            split.setSizes([340, 1000])

            # bottom: destination + save
            bot = W.QFrame()
            bot.setStyleSheet("QFrame#bot { background: #FFFFFF; border: 1px solid #DDE3F0; border-radius: 12px; }")
            bot.setObjectName("bot")
            bl = W.QHBoxLayout(bot)
            bl.setContentsMargins(14, 10, 14, 10)
            bl.addWidget(W.QLabel("Save to:"))
            self.dest = W.QLineEdit(self.r.get("final") or self.r["output"])
            bl.addWidget(self.dest, 1)
            b = W.QPushButton("Browse...")
            b.clicked.connect(self._browse)
            bl.addWidget(b)
            b = W.QPushButton("Open in PDF viewer")
            b.setToolTip("Opens the current redacted copy in your normal PDF program")
            b.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self.src)))
            bl.addWidget(b)
            b = W.QPushButton("Close")
            b.clicked.connect(self.reject)
            bl.addWidget(b)
            self.b_save = W.QPushButton("Save redacted file")
            self.b_save.setObjectName("start")
            self.b_save.clicked.connect(self._save)
            bl.addWidget(self.b_save)
            root.addWidget(bot)

            for key, fn in (("PgDown", lambda: self.go(self.cur + 1)), ("PgUp", lambda: self.go(self.cur - 1)),
                            ("Ctrl+Z", self._undo), ("Esc", self._clear_selection), ("Delete", self._redact_selected)):
                QtGui.QShortcut(QtGui.QKeySequence(key), self, activated=fn)

        # ---------- list ----------
        def _item_label(self, it):
            mark = {"open": "⚠", "redact": "■", "keep": "✓"}[it["state"]]
            what = {"open": "not redacted yet", "redact": "will be redacted", "keep": "kept as is"}[it["state"]]
            txt = it["text"] if len(it["text"]) <= 40 else it["text"][:37] + "..."
            return f"{mark}  Page {it['page']}  •  {CAT_LABEL.get(it['cat'], it['cat'])}\n      {txt}   ({what})"

        def _fill_list(self):
            row = self.list.currentRow()
            self.list.blockSignals(True)
            self.list.clear()
            for it in self.items:
                li = W.QListWidgetItem(self._item_label(it))
                li.setForeground(col({"open": "#B91C1C", "redact": "#0F172A", "keep": "#047857"}[it["state"]]))
                self.list.addItem(li)
            if not self.items:
                li = W.QListWidgetItem("No flagged items in this file.\nYou can still draw boxes on any page.")
                li.setFlags(Qt.ItemFlag.NoItemFlags)
                self.list.addItem(li)
            if 0 <= row < len(self.items):
                self.list.setCurrentRow(row)
            self.list.blockSignals(False)
            for b in (self.b_keep, self.b_all):
                b.setEnabled(bool(self.items))
            self.b_red.setEnabled(bool(self.items) or bool(self.sel))
            self.b_red.setText(f"Redact selected ({len(self.sel)} word(s))" if self.sel else "Redact selected")
            n_open = sum(1 for it in self.items if it["state"] == "open")
            self.head_info.setText(f"{len(self.items)} flagged  •  {n_open} still open  •  "
                                   f"{len(self.boxes)} box(es) drawn")
            self.box_lbl.setText(("No boxes drawn" if not self.boxes else f"{len(self.boxes)} box(es) drawn")
                                 + (f"   \u2022   {len(self.sel)} word(s) selected" if self.sel else ""))

        def _pick(self, row):
            if 0 <= row < len(self.items):
                it = self.items[row]
                self.go(it["page"] - 1, focus=it)

        def _set_state(self, state):
            row = self.list.currentRow()
            if 0 <= row < len(self.items):
                self.items[row]["state"] = state
                self._fill_list()
                nxt = next((i for i, it in enumerate(self.items) if it["state"] == "open"), None)
                if nxt is not None:
                    self.list.setCurrentRow(nxt)
                else:
                    self._draw()

        def _redact_all(self):
            for it in self.items:
                if it["state"] == "open":
                    it["state"] = "redact"
            self._fill_list()
            self._draw()

        # ---------- word selection ----------
        def _page_words(self, pno: int) -> list:
            """Words of a page (1-based) in unrotated points: (rect, text, block, line, word_no)."""
            if pno not in self._words:
                page = self.doc[pno - 1]
                rot = page.rotation
                if rot:
                    page.set_rotation(0)
                try:
                    self._words[pno] = [((w[0], w[1], w[2], w[3]), w[4], w[5], w[6], w[7])
                                        for w in page.get_text("words") if w[4].strip()]
                finally:
                    if rot:
                        page.set_rotation(rot)
            return self._words[pno]

        def _word_at(self, pt):
            page = self.doc[self.cur]
            q = self.fitz.Point(pt.x(), pt.y()) * page.derotation_matrix
            best = None
            for w in self._page_words(self.cur + 1):
                r = self.fitz.Rect(*w[0])
                if r.contains(q):
                    return w
                d = abs(q.y - (r.y0 + r.y1) / 2) + max(0.0, r.x0 - q.x, q.x - r.x1)
                if d < 3 and (best is None or d < best[0]):
                    best = (d, w)
            return best[1] if best else None

        def _word_clicked(self, pt, _ctrl):
            w = self._word_at(pt)
            if w is None:
                if not self._page_words(self.cur + 1):
                    self.head_info.setText("This page has no text layer (scan) - drag a box over the text instead.")
                return
            key = (self.cur + 1, w[0])
            if any((s_[0], s_[1]) == key for s_ in self.sel):        # second click: unselect
                self.sel = [s_ for s_ in self.sel if (s_[0], s_[1]) != key]
            else:
                self.sel.append((self.cur + 1, w[0], w[1], w[2], w[3], w[4]))
            self._fill_list()
            self._draw(keep=True)

        def _line_clicked(self, pt):
            w = self._word_at(pt)
            if w is None:
                return
            for x in self._page_words(self.cur + 1):
                if x[2] == w[2] and x[3] == w[3]:
                    key = (self.cur + 1, x[0])
                    if not any((s_[0], s_[1]) == key for s_ in self.sel):
                        self.sel.append((self.cur + 1, x[0], x[1], x[2], x[3], x[4]))
            self._fill_list()
            self._draw(keep=True)

        def _clear_selection(self):
            if self.sel:
                self.sel = []
                self._fill_list()
                self._draw(keep=True)

        def _phrases(self):
            """Selected words joined into phrases (consecutive words on the same line)."""
            out, cur, last = [], [], None
            for pg, _r, t, b, ln, wn in sorted(self.sel, key=lambda x: (x[0], x[3], x[4], x[5])):
                if cur and last == (pg, b, ln, wn - 1):
                    cur.append(t)
                else:
                    if cur:
                        out.append(cur)
                    cur = [t]
                last = (pg, b, ln, wn)
            if cur:
                out.append(cur)
            return out

        def _redact_selected(self):
            if not self.sel:                     # nothing picked on the page: act on the flagged item
                self._set_state("redact")
                return
            def pad(r):
                h = (r[3] - r[1]) * 0.05
                return (r[0] - 0.4, r[1] - h, r[2] + 0.4, r[3] + h)
            new = {(pg, r) for pg, r, *_ in self.sel}
            if self.cb_everywhere.isChecked():
                for words in self._phrases():
                    want = [_ntok(x) for x in words]
                    if not "".join(want):
                        continue
                    for pno in range(1, self.npages + 1):
                        pw = self._page_words(pno)
                        norm = [_ntok(x[1]) for x in pw]
                        for i in range(len(pw) - len(want) + 1):
                            if norm[i:i + len(want)] == want:
                                for k in range(i, i + len(want)):
                                    new.add((pno, pw[k][0]))
            added = 0
            for pg, r in sorted(new):
                box = (pg, pad(r))
                if box not in self.boxes:
                    self.boxes.append(box)
                    added += 1
            if added:
                self.box_groups.append(added)
            self.sel = []
            self._fill_list()
            self._draw(keep=True)

        # ---------- boxes ----------
        def _box_drawn(self, qr):
            page = self.doc[self.cur]
            r = self.fitz.Rect(qr.left(), qr.top(), qr.right(), qr.bottom()) * page.derotation_matrix
            r.normalize()
            self.boxes.append((self.cur + 1, (r.x0, r.y0, r.x1, r.y1)))
            self.box_groups.append(1)
            self._fill_list()
            self._draw(keep=True)

        def _undo(self):
            if self.boxes:
                n = self.box_groups.pop() if self.box_groups else 1
                pg = self.boxes[-1][0]
                del self.boxes[-n:]
                self._fill_list()
                if pg - 1 == self.cur:
                    self._draw(keep=True)
                else:
                    self.go(pg - 1)

        def _clear_page_boxes(self):
            self.boxes = [b for b in self.boxes if b[0] != self.cur + 1]
            self.box_groups = [1] * len(self.boxes)
            self._fill_list()
            self._draw(keep=True)

        # ---------- page display ----------
        def go(self, idx, focus=None):
            if self.npages == 0:
                return
            idx = max(0, min(self.npages - 1, idx))
            self.cur = idx
            self.spin.blockSignals(True)
            self.spin.setValue(idx + 1)
            self.spin.blockSignals(False)
            self.b_prev.setEnabled(idx > 0)
            self.b_next.setEnabled(idx < self.npages - 1)
            self._draw(focus)

        def _disp(self, page, rect):
            r = self.fitz.Rect(*rect) * page.rotation_matrix
            r.normalize()
            return QtCore.QRectF(r.x0, r.y0, r.width, r.height)

        def _draw(self, focus=None, keep=False):
            hs, vs = self.view.horizontalScrollBar().value(), self.view.verticalScrollBar().value()
            sc = self.view.scene()
            sc.clear()
            page = self.doc[self.cur]
            pix = page.get_pixmap(matrix=self.fitz.Matrix(self.RENDER, self.RENDER), alpha=False)
            img = QtGui.QImage(pix.samples, pix.width, pix.height, pix.stride,
                               QtGui.QImage.Format.Format_RGB888).copy()
            pm_item = sc.addPixmap(QtGui.QPixmap.fromImage(img))
            pm_item.setScale(1 / self.RENDER)
            pm_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            sc.setSceneRect(QtCore.QRectF(0, 0, pix.width / self.RENDER, pix.height / self.RENDER))
            focus_rect = None
            for it in self.items:
                if it["page"] != self.cur + 1:
                    continue
                for rr in it["rects"]:
                    q = self._disp(page, rr).adjusted(-1.5, -1.5, 1.5, 1.5)
                    if it["state"] == "redact":
                        pen, brush = QtGui.QPen(col("#000000"), 0), QtGui.QBrush(QtGui.QColor(0, 0, 0, 200))
                    elif it["state"] == "keep":
                        pen, brush = QtGui.QPen(col("#059669"), 1.2, Qt.PenStyle.DashLine), QtGui.QBrush(Qt.BrushStyle.NoBrush)
                    else:
                        pen, brush = QtGui.QPen(col("#DC2626"), 1.6), QtGui.QBrush(QtGui.QColor(220, 38, 38, 45))
                    if it is focus:
                        pen = QtGui.QPen(col("#F59E0B"), 2.4)
                        focus_rect = q
                    sc.addRect(q, pen, brush).setZValue(20)
            for pg, rr in self.boxes:
                if pg == self.cur + 1:
                    sc.addRect(self._disp(page, rr), QtGui.QPen(col("#7C3AED"), 0),
                               QtGui.QBrush(QtGui.QColor(0, 0, 0, 200))).setZValue(30)
            for pg, rr, *_ in self.sel:
                if pg == self.cur + 1:
                    sc.addRect(self._disp(page, rr).adjusted(-0.8, -0.8, 0.8, 0.8), QtGui.QPen(col("#D97706"), 1.2),
                               QtGui.QBrush(QtGui.QColor(251, 191, 36, 110))).setZValue(40)
            self._apply_zoom()
            if keep:
                self.view.horizontalScrollBar().setValue(hs)
                self.view.verticalScrollBar().setValue(vs)
            elif focus_rect is not None:
                self.view.centerOn(focus_rect.center())
            else:
                self.view.verticalScrollBar().setValue(0)

        def _apply_zoom(self):
            if self.fit:
                w = self.view.sceneRect().width() or 1
                self.zoom = max(0.2, (self.view.viewport().width() - 24) / w)
            self.view.resetTransform()
            self.view.scale(self.zoom, self.zoom)

        def _zoom_by(self, f):
            self.fit = False
            self.zoom = max(0.2, min(8.0, self.zoom * f))
            self._apply_zoom()

        def _fit_width(self):
            self.fit = True
            self._apply_zoom()

        def resizeEvent(self, e):
            super().resizeEvent(e)
            if self.fit and hasattr(self, "view"):
                self._apply_zoom()

        def showEvent(self, e):
            super().showEvent(e)
            QtCore.QTimer.singleShot(0, lambda: self._draw(self._focus_item()))

        def _focus_item(self):
            row = self.list.currentRow()
            return self.items[row] if 0 <= row < len(self.items) else None

        # ---------- save ----------
        def _browse(self):
            p, _ = W.QFileDialog.getSaveFileName(self, "Save redacted PDF as", self.dest.text(), "PDF files (*.pdf)")
            if p:
                if not p.lower().endswith(".pdf"):
                    p += ".pdf"
                self.dest.setText(p)

        def _save(self):
            dest = self.dest.text().strip()
            if not dest:
                W.QMessageBox.warning(self, "No destination", "Choose where the redacted file should be saved.")
                return
            if not dest.lower().endswith(".pdf"):
                dest += ".pdf"
            if os.path.abspath(dest) == os.path.abspath(self.r["file"]):
                W.QMessageBox.warning(self, "Original file", "Please choose a different name - the original "
                                      "file is never overwritten.")
                return
            n_open = sum(1 for it in self.items if it["state"] == "open")
            if n_open:
                a = W.QMessageBox.question(
                    self, "Items still open",
                    f"{n_open} flagged item(s) are neither redacted nor marked 'Keep as is'.\n\n"
                    "They will stay visible in the saved file. Save anyway?")
                if a != W.QMessageBox.StandardButton.Yes:
                    return
            rects: Dict[int, list] = {}
            for it in self.items:
                if it["state"] == "redact":
                    rects.setdefault(it["page"], []).extend(it["rects"])
            for pg, rr in self.boxes:
                rects.setdefault(pg, []).append(rr)
            fitz = self.fitz
            tmpdir = tempfile.mkdtemp(prefix="gwn_save_")
            tmp = os.path.join(tmpdir, "out.pdf")
            try:
                self.doc.close()
                d = fitz.open(self.src)
                for pg, rs in rects.items():
                    page = d[pg - 1]
                    rot = page.rotation
                    if rot:
                        page.set_rotation(0)
                    _apply(page, fitz, rs)
                    if rot:
                        page.set_rotation(rot)
                d.save(tmp, garbage=4, deflate=True, clean=True)
                d.close()
                os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
                if os.path.exists(dest):
                    os.remove(dest)
                shutil.move(tmp, dest)
            except PermissionError:
                self.doc = fitz.open(self.src)
                W.QMessageBox.critical(self, "Could not save",
                                       f"{dest}\n\nis open in another program (for example a PDF viewer). "
                                       "Close it there and press Save again.")
                return
            except Exception as exc:  # noqa
                self.doc = fitz.open(self.src)
                W.QMessageBox.critical(self, "Could not save", f"{type(exc).__name__}: {exc}")
                return
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
            cfg = self.r.get("cfg") or Config()
            left, items = leftover_scan(dest, cfg)
            kept = {(it["page"], it["text"]) for it in self.items if it["state"] == "keep"}
            items = [x for x in items if (x[0], x[2]) not in kept]
            self.r["leftover"] = Counter(c for _, c, _, _ in items)
            self.r["leftover_items"] = items
            self.r["output"] = dest
            self.r["final"] = dest
            self.r["pending"] = False
            self.r["manual_boxes"] = self.r.get("manual_boxes", 0) + len(self.boxes)
            self.r["kept"] = len(kept)
            self.saved.emit(self.r)
            msg = f"Saved:\n{dest}"
            if items:
                msg += f"\n\n{len(items)} flagged item(s) are still visible in the saved file."
            W.QMessageBox.information(self, "Saved", msg)
            self.accept()

        def closeEvent(self, e):
            try:
                self.doc.close()
            except Exception:
                pass
            super().closeEvent(e)

        def done(self, code):
            try:
                self.doc.close()
            except Exception:
                pass
            super().done(code)

    # ---------------- main window ----------------
    class Main(W.QMainWindow):
        def __init__(self, tick: str):
            super().__init__()
            self.tick = tick
            self.setWindowTitle(APP_NAME)
            self.setAcceptDrops(True)
            self.setMinimumSize(820, 560)
            self.worker = None
            self.last_folder = ""
            self.results: List[dict] = []
            self.tmpdir = ""
            self._build()
            self._initial_geometry()

        # ---------- building blocks ----------
        def card(self, number: str, title: str, accent: str):
            f = W.QFrame()
            f.setObjectName("card")
            ind = (f"QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent};"
                   + (f" image: url({self.tick});" if self.tick else "") + " }"
                   f"QCheckBox::indicator:checked:disabled {{ background: #CBD5E1; border-color: #CBD5E1; }}")
            f.setStyleSheet(
                f"QFrame#card {{ background: #FFFFFF; border: 1px solid #DDE3F0; "
                f"border-top: 5px solid {accent}; border-radius: 12px; }}" + ind)
            sh = W.QGraphicsDropShadowEffect(f)
            sh.setBlurRadius(18)
            sh.setOffset(0, 3)
            sh.setColor(QtGui.QColor(30, 41, 89, 28))
            f.setGraphicsEffect(sh)
            v = W.QVBoxLayout(f)
            v.setContentsMargins(16, 12, 16, 14)
            v.setSpacing(8)
            head = W.QHBoxLayout()
            head.setSpacing(10)
            if number:
                b = W.QLabel(number)
                b.setFixedSize(28, 28)
                b.setAlignment(Qt.AlignmentFlag.AlignCenter)
                b.setStyleSheet(f"background: {accent}; color: #FFFFFF; border-radius: 14px; "
                                f"font-weight: 700; font-size: 10.5pt;")
                head.addWidget(b)
            lab = W.QLabel(title)
            lab.setStyleSheet(f"color: {accent}; font-size: 12pt; font-weight: 700;")
            head.addWidget(lab)
            head.addStretch(1)
            v.addLayout(head)
            return f, v

        def logo_widget(self):
            """GSTwithNihal logo on a white card in the top-right corner of the banner."""
            try:
                import base64
                pm = QtGui.QPixmap()
                pm.loadFromData(base64.b64decode(LOGO_PNG_B64), "PNG")
                if pm.isNull():
                    return None
                dpr = self.devicePixelRatioF() or 1.0
                h = 78
                pm = pm.scaledToHeight(int(h * dpr), Qt.TransformationMode.SmoothTransformation)
                pm.setDevicePixelRatio(dpr)
                card = W.QFrame()
                card.setObjectName("logocard")
                card.setStyleSheet("QFrame#logocard { background: #FFFFFF; border-radius: 12px; }")
                lay = W.QHBoxLayout(card)
                lay.setContentsMargins(10, 6, 10, 6)
                lab = W.QLabel()
                lab.setPixmap(pm)
                lab.setStyleSheet("background: transparent;")
                lay.addWidget(lab)
                return card
            except Exception:
                return None

        @staticmethod
        def hint(text: str) -> QtWidgets.QLabel:
            h = W.QLabel(text)
            h.setObjectName("hint")
            h.setWordWrap(True)
            return h

        # ---------- UI construction ----------
        def _build(self):
            central = W.QWidget()
            self.setCentralWidget(central)
            outer = W.QVBoxLayout(central)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)

            # Everything except the run bar lives in a scroll area, so no section is ever squeezed:
            # if the window is shorter than the content, a scroll bar appears instead.
            self.scroll = W.QScrollArea()
            self.scroll.setObjectName("scroll")
            self.scroll.setWidgetResizable(True)
            self.scroll.setFrameShape(W.QFrame.Shape.NoFrame)
            page = W.QWidget()
            page.setObjectName("page")
            self.scroll.setWidget(page)
            outer.addWidget(self.scroll, 1)

            pv = W.QVBoxLayout(page)
            pv.setContentsMargins(20, 18, 20, 18)
            pv.setSpacing(16)

            # --- banner
            banner = W.QFrame()
            banner.setObjectName("banner")
            banner.setStyleSheet(
                "QFrame#banner { border-radius: 16px; background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                "stop:0 #7C3AED, stop:0.55 #2563EB, stop:1 #06B6D4); }"
                "QLabel { color: #FFFFFF; background: transparent; }")
            bl = W.QHBoxLayout(banner)
            bl.setContentsMargins(24, 16, 24, 16)
            tv = W.QVBoxLayout()
            tv.setSpacing(2)
            t = W.QLabel(APP_NAME)
            t.setStyleSheet("font-size: 21pt; font-weight: 800;")
            s = W.QLabel("Permanently removes personal information (text and image pixels) from PDF files. "
                         "The original files are never changed.")
            s.setWordWrap(True)
            s.setStyleSheet("font-size: 10.5pt; color: #E0F2FE;")
            tv.addWidget(t)
            tv.addWidget(s)
            bl.addLayout(tv, 1)
            chips = W.QVBoxLayout()
            chips.setSpacing(6)
            for txt in ("DPDP-ready", "Works offline", "True redaction"):
                c = W.QLabel(txt)
                c.setAlignment(Qt.AlignmentFlag.AlignCenter)
                c.setStyleSheet("background: rgba(255,255,255,0.20); border: 1px solid rgba(255,255,255,0.55); "
                                "border-radius: 11px; padding: 3px 12px; font-weight: 600; font-size: 9pt;")
                chips.addWidget(c)
            bl.addLayout(chips)
            logo = self.logo_widget()
            if logo is not None:
                bl.addSpacing(14)
                bl.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)
            pv.addWidget(banner)

            # --- two columns
            cols = W.QBoxLayout(W.QBoxLayout.Direction.LeftToRight)
            self.cols = cols
            cols.setSpacing(16)
            left, right = W.QVBoxLayout(), W.QVBoxLayout()
            left.setSpacing(16)
            right.setSpacing(16)
            cols.addLayout(left, 5)
            cols.addLayout(right, 6)
            pv.addLayout(cols)

            # 1. files
            g, v = self.card("1", "PDF files", ACCENT["files"])
            self.files = W.QListWidget()
            self.files.setSelectionMode(W.QAbstractItemView.SelectionMode.ExtendedSelection)
            self.files.setMinimumHeight(140)
            self.files.model().rowsInserted.connect(self._count_files)
            self.files.model().rowsRemoved.connect(self._count_files)
            v.addWidget(self.files)
            hb = W.QHBoxLayout()
            hb.setSpacing(8)
            for text, fn in (("Add PDFs...", self.add_files), ("Add folder...", self.add_folder),
                             ("Remove selected", self.remove_selected), ("Clear", self.files.clear)):
                b = W.QPushButton(text)
                b.clicked.connect(fn)
                hb.addWidget(b)
            v.addLayout(hb)
            row = W.QHBoxLayout()
            self.count_lbl = W.QLabel("No files added yet")
            self.count_lbl.setObjectName("count")
            row.addWidget(self.count_lbl)
            row.addStretch(1)
            tip = self.hint("Tip: drag & drop PDFs onto this window")
            tip.setWordWrap(False)
            row.addWidget(tip)
            v.addLayout(row)
            ob = W.QHBoxLayout()
            ob.addWidget(W.QLabel("Save to:"))
            self.out_dir = W.QLineEdit()
            self.out_dir.setPlaceholderText("Empty = same folder as each original (file name + _redacted.pdf)")
            ob.addWidget(self.out_dir, 1)
            b = W.QPushButton("Browse...")
            b.clicked.connect(self.pick_out)
            ob.addWidget(b)
            v.addLayout(ob)
            left.addWidget(g)

            # 3. manual names
            g, v = self.card("3", "Names to always redact (optional)", ACCENT["names"])
            self.names = W.QPlainTextEdit()
            self.names.setPlaceholderText("One name per line, for example:\nABC Private Limited\n"
                                          "Mr Rahul Sharma\nXYZ Traders")
            self.names.setMinimumHeight(130)
            v.addWidget(self.names, 1)
            v.addWidget(self.hint("Matched anywhere in the document, any capitalisation, also when the name "
                                  "is split over two lines."))
            left.addWidget(g, 1)

            # 2. categories (two columns so the list never runs off the screen)
            g, v = self.card("2", "What to redact", ACCENT["what"])
            grid = W.QGridLayout()
            grid.setHorizontalSpacing(18)
            grid.setVerticalSpacing(2)
            self.cat_boxes = {}
            half = (len(CATEGORIES) + 1) // 2
            for i, (key, label, tip) in enumerate(CATEGORIES):
                cb = W.QCheckBox(label)
                cb.setChecked(True)
                if tip:
                    cb.setToolTip(tip)
                self.cat_boxes[key] = cb
                grid.addWidget(cb, i % half, i // half)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 1)
            v.addLayout(grid)
            self.cb_company = W.QCheckBox("Also redact any phrase ending in Pvt Ltd / LLP / Enterprises / Traders ...")
            self.cb_company.setChecked(True)
            self.cb_company.setToolTip("Catches business names that are not next to a label. Untick if it hides "
                                       "your own letter-head.")
            v.addWidget(self.cb_company)
            hb = W.QHBoxLayout()
            b1, b2 = W.QPushButton("Select all"), W.QPushButton("Select none")
            b1.clicked.connect(lambda: [c.setChecked(True) for c in self.cat_boxes.values()])
            b2.clicked.connect(lambda: [c.setChecked(False) for c in self.cat_boxes.values()])
            hb.addWidget(b1)
            hb.addWidget(b2)
            hb.addStretch(1)
            v.addLayout(hb)
            right.addWidget(g)

            # protected content
            g, v = self.card("✓", "Never redact (protected content)", ACCENT["protect"])
            self.cb_p_case = W.QCheckBox("Case laws: party names and citations (e.g. X Vs. Y, (2019) 13 SCC 225)")
            self.cb_p_stat = W.QCheckBox("Statute: bare provisions, section / rule / notification references, Act names")
            self.cb_p_off = W.QCheckBox("Officers: names, designations and jurisdiction (Range / Division / Commissionerate)")
            self.cb_p_quote = W.QCheckBox("Long quoted passages (12+ words inside quotation marks)")
            for c in (self.cb_p_case, self.cb_p_stat, self.cb_p_off, self.cb_p_quote):
                c.setChecked(True)
                v.addWidget(c)
            v.addWidget(self.hint("Protected text always wins: it is never redacted, even if it is in your own "
                                  "name list."))
            right.addWidget(g)

            # 4. options / OCR
            g, v = self.card("4", "Options", ACCENT["options"])
            self.cb_meta = W.QCheckBox("Remove document properties / metadata, bookmarks and attachments")
            self.cb_meta.setChecked(True)
            self.cb_flat = W.QCheckBox("Flatten form fields and comments first (so their text can be redacted)")
            self.cb_flat.setChecked(True)
            self.cb_csv = W.QCheckBox("Save redaction_report.csv (counts only, never the redacted text)")
            self.cb_csv.setChecked(True)
            self.cb_review = W.QCheckBox("Hold files with flagged items for my review - save them only after "
                                         "I click Save")
            self.cb_review.setChecked(True)
            self.cb_review.setToolTip("Files whose leftover check finds something are kept aside. Double-click "
                                      "them in Results to see each flagged item on its page, redact it, and save.")
            for c in (self.cb_meta, self.cb_flat, self.cb_csv, self.cb_review):
                v.addWidget(c)
            self.cb_ocr = W.QCheckBox("Automatically read scanned pages and pictures inside the PDF (OCR)")
            self.cb_ocr.setChecked(True)
            self.cb_ocr.setToolTip("Scanned pages and pictures (screenshots, pasted tables, stamps) are detected "
                                   "on their own, read with OCR and redacted like normal text.")
            self.cb_ocr.toggled.connect(self._ocr_toggled)
            v.addWidget(self.cb_ocr)
            self.ocr_box = W.QWidget()
            og = W.QGridLayout(self.ocr_box)
            og.setContentsMargins(26, 0, 0, 0)
            og.setVerticalSpacing(6)
            self.cb_ocr_all = W.QCheckBox("Also read very small pictures such as stamps and signatures (slower)")
            og.addWidget(self.cb_ocr_all, 0, 0, 1, 3)
            og.addWidget(W.QLabel("Tesseract:"), 1, 0)
            self.tess = W.QLineEdit()
            self.tess.setPlaceholderText("Auto-detect (or browse to tesseract.exe)")
            self.tess.editingFinished.connect(self._ocr_refresh)
            og.addWidget(self.tess, 1, 1)
            b = W.QPushButton("Browse...")
            b.clicked.connect(self.pick_tess)
            og.addWidget(b, 1, 2)
            og.addWidget(W.QLabel("Language:"), 2, 0)
            row = W.QHBoxLayout()
            self.lang = W.QLineEdit("eng")
            self.lang.setMaximumWidth(110)
            self.lang.setToolTip("Tesseract language codes, e.g. eng, hin, eng+hin")
            row.addWidget(self.lang)
            row.addWidget(W.QLabel("  DPI:"))
            self.dpi = W.QSpinBox()
            self.dpi.setRange(150, 600)
            self.dpi.setSingleStep(50)
            self.dpi.setValue(300)
            row.addWidget(self.dpi)
            row.addWidget(W.QLabel("  Layout:"))
            self.psm = W.QComboBox()
            self.psm.addItem("Automatic", 3)
            self.psm.addItem("Single block", 6)
            self.psm.addItem("Sparse text (forms)", 11)
            row.addWidget(self.psm)
            row.addStretch(1)
            og.addLayout(row, 2, 1, 1, 2)
            self.ocr_status = self.hint("")
            og.addWidget(self.ocr_status, 3, 0, 1, 2)
            self.btn_ocr_install = W.QPushButton("Install / repair OCR")
            self.btn_ocr_install.setToolTip("Downloads and installs the free Tesseract OCR program and the English, "
                                            "Hindi and Marathi language files. Windows asks once for permission.")
            self.btn_ocr_install.clicked.connect(lambda: self.install_ocr())
            og.addWidget(self.btn_ocr_install, 3, 2)
            v.addWidget(self.ocr_box)
            right.addWidget(g)
            right.addStretch(1)
            self._ocr_toggled(True)

            # 5. results (full width)
            self.results_card, v = self.card("5", "Results", ACCENT["results"])
            tabs = W.QTabWidget()
            self.table = W.QTableWidget(0, 6)
            self.table.setHorizontalHeaderLabels(["File", "Pages", "Items redacted", "OCR pages",
                                                  "Leftover check", "Output"])
            self.table.horizontalHeader().setStretchLastSection(True)
            self.table.horizontalHeader().setSectionResizeMode(0, W.QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(0, 260)
            self.table.setEditTriggers(W.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.table.setSelectionBehavior(W.QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.verticalHeader().setVisible(False)
            self.table.setAlternatingRowColors(True)
            self.table.setSelectionMode(W.QAbstractItemView.SelectionMode.SingleSelection)
            self.table.cellDoubleClicked.connect(lambda row, _c: self.review(row))
            self.table.setStyleSheet("QTableWidget::item:selected { background: #6366F1; color: #FFFFFF; }")
            tabs.addTab(self.table, "Summary")
            self.log = W.QPlainTextEdit()
            self.log.setReadOnly(True)
            tabs.addTab(self.log, "Details / warnings")
            tabs.setMinimumHeight(220)
            v.addWidget(tabs, 1)
            rr = W.QHBoxLayout()
            rr.addWidget(self.hint("Double-click a file to review it page by page: flagged items are listed with "
                                   "their page number, and you can redact them or draw your own boxes before saving."))
            self.btn_review = W.QPushButton("Review selected file")
            self.btn_review.setEnabled(False)
            self.btn_review.clicked.connect(lambda: self.review(self.table.currentRow()))
            rr.addWidget(self.btn_review)
            v.addLayout(rr)
            pv.addWidget(self.results_card, 1)

            # --- run bar: fixed at the bottom, always visible
            bar = W.QFrame()
            bar.setObjectName("bottombar")
            bv = W.QVBoxLayout(bar)
            bv.setContentsMargins(20, 10, 20, 12)
            bv.setSpacing(6)
            self.status = W.QLabel("Add one or more PDF files, then press Start redaction.")
            self.status.setObjectName("hint")
            bv.addWidget(self.status)
            rb = W.QHBoxLayout()
            rb.setSpacing(10)
            self.bar = W.QProgressBar()
            self.bar.setRange(0, 1000)
            self.bar.setValue(0)
            self.bar.setFormat("%p%")
            rb.addWidget(self.bar, 1)
            self.btn_open = W.QPushButton("Open output folder")
            self.btn_open.setEnabled(False)
            self.btn_open.clicked.connect(self.open_out)
            rb.addWidget(self.btn_open)
            self.btn_cancel = W.QPushButton("Cancel")
            self.btn_cancel.setObjectName("cancel")
            self.btn_cancel.setEnabled(False)
            self.btn_cancel.clicked.connect(self.cancel)
            rb.addWidget(self.btn_cancel)
            self.btn_start = W.QPushButton("Start redaction")
            self.btn_start.setObjectName("start")
            self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_start.clicked.connect(self.start)
            rb.addWidget(self.btn_start)
            bv.addLayout(rb)
            outer.addWidget(bar)

        def _initial_geometry(self):
            scr = QtGui.QGuiApplication.primaryScreen()
            if scr is None:
                self.resize(1280, 860)
                return
            av = scr.availableGeometry()
            w = min(1320, int(av.width() * 0.92))
            h = min(920, int(av.height() * 0.90))
            self.resize(w, h)
            self.move(av.x() + (av.width() - w) // 2, av.y() + (av.height() - h) // 2)

        def resizeEvent(self, e):
            super().resizeEvent(e)
            # wide window: two columns side by side; narrow window: one column (no sideways scrolling)
            want = (W.QBoxLayout.Direction.LeftToRight if self.width() >= 1200
                    else W.QBoxLayout.Direction.TopToBottom)
            if self.cols.direction() != want:
                self.cols.setDirection(want)

        def _count_files(self, *args):
            n = self.files.count()
            self.count_lbl.setText("No files added yet" if n == 0 else f"{n} PDF file(s) ready")

        # ---------------- file handling ----------------
        def _add(self, paths):
            have = {self.files.item(i).text() for i in range(self.files.count())}
            for p in paths:
                if p.lower().endswith(".pdf") and p not in have:
                    self.files.addItem(p)
                    self.files.item(self.files.count() - 1).setToolTip(p)
                    have.add(p)

        def add_files(self):
            ps, _ = W.QFileDialog.getOpenFileNames(self, "Select PDF files", "", "PDF files (*.pdf)")
            self._add(ps)

        def add_folder(self):
            d = W.QFileDialog.getExistingDirectory(self, "Select a folder with PDF files")
            if d:
                self._add(sorted(os.path.join(d, f) for f in os.listdir(d)))

        def remove_selected(self):
            for it in self.files.selectedItems():
                self.files.takeItem(self.files.row(it))

        def pick_out(self):
            d = W.QFileDialog.getExistingDirectory(self, "Select output folder")
            if d:
                self.out_dir.setText(d)

        def pick_tess(self):
            p, _ = W.QFileDialog.getOpenFileName(self, "Locate tesseract.exe", "", "Programs (*)")
            if p:
                self.tess.setText(p)
                self._ocr_refresh()

        def dragEnterEvent(self, e):
            if e.mimeData().hasUrls():
                e.acceptProposedAction()

        def dropEvent(self, e):
            paths = []
            for u in e.mimeData().urls():
                p = u.toLocalFile()
                if os.path.isdir(p):
                    paths += [os.path.join(p, f) for f in sorted(os.listdir(p))]
                else:
                    paths.append(p)
            self._add(paths)

        # ---------------- OCR ----------------
        def _ocr_toggled(self, on):
            self.ocr_box.setEnabled(on)
            if on:
                self._ocr_refresh()
            else:
                self.ocr_status.setText("")

        def _ocr_refresh(self):
            c = Config()
            c.tesseract_cmd = self.tess.text().strip()
            st = ocr_status(c)
            self.ocr_status.setText(st)
            self.ocr_status.setStyleSheet("color: #047857; font-weight: 600;" if st.startswith("OCR ready")
                                          else "color: #B45309; font-weight: 600;")
            self.btn_ocr_install.setText("Repair OCR" if st.startswith("OCR ready") else "Install OCR")

        def install_ocr(self, then=None):
            self.btn_ocr_install.setEnabled(False)
            self.btn_start.setEnabled(False)
            self.status.setText("Setting up OCR ... Windows may ask for permission - please click 'Yes'.")
            self.ocr_worker = OcrSetup()
            self.ocr_worker.line.connect(lambda t: self.status.setText(t.strip()))

            def finished(exe):
                self.btn_ocr_install.setEnabled(True)
                self.btn_start.setEnabled(True)
                self._ocr_refresh()
                if exe:
                    self.status.setText("OCR is ready.")
                    if then:
                        then()
                else:
                    self.status.setText("OCR could not be installed.")
                    W.QMessageBox.warning(
                        self, "OCR not installed",
                        "The OCR program could not be installed automatically (no internet, or Windows "
                        "permission was not given).\n\nText PDFs are redacted normally. For scanned pages, "
                        "try 'Install OCR' again, or install Tesseract from\n"
                        "https://github.com/tesseract-ocr/tesseract/releases\nand restart the tool.")
            self.ocr_worker.done.connect(finished)
            self.ocr_worker.start()

        # ---------------- run ----------------
        def config(self) -> Config:
            c = Config()
            c.cats = {k: b.isChecked() for k, b in self.cat_boxes.items()}
            c.company_suffix = self.cb_company.isChecked()
            c.manual_names = [x.strip() for x in self.names.toPlainText().splitlines() if x.strip()]
            c.protect_citations = self.cb_p_case.isChecked()
            c.protect_statutes = self.cb_p_stat.isChecked()
            c.protect_officers = self.cb_p_off.isChecked()
            c.protect_quotes = self.cb_p_quote.isChecked()
            c.strip_metadata = self.cb_meta.isChecked()
            c.flatten_forms = self.cb_flat.isChecked()
            c.ocr = self.cb_ocr.isChecked()
            c.ocr_all_image_pages = self.cb_ocr_all.isChecked()
            c.ocr_lang = self.lang.text().strip() or "eng"
            c.ocr_dpi = self.dpi.value()
            c.ocr_psm = int(self.psm.currentData())
            c.tesseract_cmd = self.tess.text().strip()
            return c

        def _set_busy(self, busy):
            for w in (self.btn_start, self.files, self.out_dir, self.names):
                w.setEnabled(not busy)
            self.btn_cancel.setEnabled(busy)

        def start(self):
            try:
                _import_fitz()
            except ImportError:
                W.QMessageBox.critical(self, "PyMuPDF missing", "Please install PyMuPDF first:\n\n    " + PIP_LINE)
                return
            files = [self.files.item(i).text() for i in range(self.files.count())]
            if not files:
                W.QMessageBox.warning(self, "No files", "Please add at least one PDF file.")
                return
            cfg = self.config()
            if not any(cfg.cats.values()):
                W.QMessageBox.warning(self, "Nothing selected", "Tick at least one category to redact.")
                return
            if cfg.ocr and not ocr_status(cfg).startswith("OCR ready"):
                box = W.QMessageBox(self)
                box.setWindowTitle("OCR not installed yet")
                box.setIcon(W.QMessageBox.Icon.Question)
                box.setText("The OCR program (needed to read scanned pages and pictures) is not installed.\n\n"
                            "Install it now? It is free; Windows will ask once for permission.")
                b_inst = box.addButton("Install OCR now", W.QMessageBox.ButtonRole.AcceptRole)
                b_skip = box.addButton("Continue without OCR", W.QMessageBox.ButtonRole.DestructiveRole)
                box.addButton("Cancel", W.QMessageBox.ButtonRole.RejectRole)
                box.exec()
                if box.clickedButton() is b_inst:
                    self.install_ocr(then=self.start)
                    return
                if box.clickedButton() is not b_skip:
                    return
                cfg.ocr = False
            self.table.setRowCount(0)
            self.log.clear()
            self.bar.setValue(0)
            self.btn_open.setEnabled(False)
            self.last_folder = self.out_dir.text().strip()
            self._set_busy(True)
            self.results = []
            self._cleanup_tmp()
            review = self.cb_review.isChecked()
            if review:
                self.tmpdir = tempfile.mkdtemp(prefix="gstwithnihal_review_")
            self.btn_review.setEnabled(False)
            self.worker = Worker(files, self.out_dir.text().strip(), cfg, self.cb_csv.isChecked(),
                                 review, self.tmpdir)
            self.worker.progress.connect(self._progress)
            self.worker.file_done.connect(self._file_done)
            self.worker.all_done.connect(self._all_done)
            self.worker.start()

        def cancel(self):
            if self.worker:
                self.worker.cancel()
                self.status.setText("Cancelling...")

        def _progress(self, frac, msg):
            self.bar.setValue(int(frac * 1000))
            self.status.setText(msg)

        def _paint_row(self, row, r):
            total = sum(r["counts"].values()) + r.get("manual_boxes", 0)
            left = sum(r["leftover"].values())
            pages = sorted({it[0] for it in r.get("leftover_items", [])})
            pg_txt = (" on page " + ", ".join(str(p) for p in pages[:6]) + (" ..." if len(pages) > 6 else "")) if pages else ""
            if r["error"]:
                leftover, out, tone = "FAILED: " + r["error"], "", "bad"
            elif r.get("pending"):
                leftover = f"{left} flagged{pg_txt} - double-click to review"
                out, tone = "Not saved yet - waiting for your review  →  " + r.get("final", ""), "wait"
            elif left:
                leftover = f"{left} flagged{pg_txt} - double-click to review"
                out, tone = r["output"], "bad"
            else:
                leftover, out, tone = ("Clean" + (" (items kept by you)" if r.get("kept") else "")), r["output"], "ok"
            vals = [os.path.basename(r["file"]), str(r["pages"]), str(total), str(r["ocr_pages"]), leftover, out]
            fg = {"bad": "#991B1B", "wait": "#92400E", "ok": "#0F172A"}[tone]
            bg = {"bad": "#FEE2E2", "wait": "#FEF3C7", "ok": None}[tone]
            for c, val in enumerate(vals):
                it = W.QTableWidgetItem(val)
                it.setForeground(col("#047857" if (tone == "ok" and c == 4) else fg))
                if bg:
                    it.setBackground(col(bg))
                it.setToolTip("Double-click to review this file page by page")
                self.table.setItem(row, c, it)

        def _file_done(self, r):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.results.append(r)
            self._paint_row(row, r)
            self.btn_review.setEnabled(True)
            left = sum(r["leftover"].values())
            if not self.last_folder and r["output"] and not r.get("pending"):
                self.last_folder = os.path.dirname(r["output"])
            self.log.appendPlainText(summarize(r))
            for cat, n in sorted(r["counts"].items(), key=lambda kv: -kv[1]):
                self.log.appendPlainText(f"     {CAT_LABEL.get(cat, cat)}: {n}")
            for pg, cat, _t, _r in r.get("leftover_items", []):
                self.log.appendPlainText(f"     FLAGGED  page {pg}: {CAT_LABEL.get(cat, cat)}")
            if r.get("pending"):
                self.log.appendPlainText("     Not saved yet - double-click the file in Summary to review and save.")
            for w in r["warnings"]:
                self.log.appendPlainText("     ! " + w)
            self.log.appendPlainText("")

        def _all_done(self, results, csv_path):
            self._set_busy(False)
            self.bar.setValue(1000)
            self.btn_open.setEnabled(bool(self.last_folder))
            self.scroll.ensureWidgetVisible(self.results_card, 0, 0)
            ok = [r for r in results if not r["error"]]
            bad = [r for r in results if r["error"]]
            risky = [r for r in ok if sum(r["leftover"].values())]
            pending = [r for r in ok if r.get("pending")]
            msg = f"{len(ok)} of {len(results)} file(s) redacted."
            if bad:
                msg += f"\n{len(bad)} file(s) failed - see the Results section."
            if pending:
                msg += (f"\n\n{len(pending)} file(s) have flagged items and are NOT saved yet. Review them, redact "
                        "what is needed, and press Save in the review window.")
            elif risky:
                msg += f"\n{len(risky)} file(s) have possible leftovers - double-click them in Results to review."
            if csv_path:
                msg += "\n\nReport saved: " + csv_path
            msg += ("\n\nAlways open the redacted PDF and check it before sharing. Automatic detection "
                    "of free-text names can never be guaranteed 100 %.")
            self.status.setText("Finished.")
            box = W.QMessageBox(self)
            box.setWindowTitle("Redaction completed")
            box.setIcon(W.QMessageBox.Icon.Warning if (bad or risky) else W.QMessageBox.Icon.Information)
            box.setText(msg)
            b_now = None
            if risky:
                b_now = box.addButton("Review now", W.QMessageBox.ButtonRole.AcceptRole)
                box.addButton("Later", W.QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if b_now is not None and box.clickedButton() is b_now:
                first = next(i for i, r in enumerate(self.results) if r in risky)
                self.table.selectRow(first)
                self.review(first)

        def review(self, row):
            if not (0 <= row < len(self.results)):
                return
            r = self.results[row]
            if r["error"] or not r.get("output") or not os.path.isfile(r["output"]):
                W.QMessageBox.warning(self, "Nothing to review", "This file was not produced - see Details / warnings.")
                return
            dlg = ReviewDialog(self, r, self.tick)
            dlg.saved.connect(lambda rr, row=row: self._after_save(row, rr))
            dlg.exec()

        def _after_save(self, row, r):
            self._paint_row(row, r)
            if not self.last_folder:
                self.last_folder = os.path.dirname(r["output"])
            self.btn_open.setEnabled(True)
            left = sum(r["leftover"].values())
            self.log.appendPlainText(f"{os.path.basename(r['file'])}: reviewed and saved to {r['output']}"
                                     + (f" ({left} flagged item(s) left visible)" if left else ""))
            self.status.setText(f"Saved {os.path.basename(r['output'])}")

        def _cleanup_tmp(self):
            if self.tmpdir:
                shutil.rmtree(self.tmpdir, ignore_errors=True)
                self.tmpdir = ""

        def open_out(self):
            if self.last_folder and os.path.isdir(self.last_folder):
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self.last_folder))

        def closeEvent(self, e):
            pend = [r for r in self.results if r.get("pending")]
            if pend:
                a = W.QMessageBox.question(
                    self, "Files not saved",
                    f"{len(pend)} file(s) are waiting for your review and have NOT been saved.\n\n"
                    "Close anyway and discard them?")
                if a != W.QMessageBox.StandardButton.Yes:
                    e.ignore()
                    return
            if self.worker is not None and self.worker.isRunning():
                self.worker.cancel()
                self.worker.wait(15000)
            self._cleanup_tmp()
            super().closeEvent(e)

    # ---------------- application ----------------
    try:   # crisp text on 125 % / 150 % Windows scaling
        QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except Exception:
        pass
    app = W.QApplication.instance() or W.QApplication(sys.argv or [APP_NAME])
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    try:   # Qt 6.8+: ignore the Windows dark mode so text is always dark on light
        app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    except Exception:
        pass
    R, G = QtGui.QPalette.ColorRole, QtGui.QPalette.ColorGroup
    pal = QtGui.QPalette()
    for role, hexv in ((R.Window, "#EEF2FF"), (R.WindowText, "#0F172A"), (R.Base, "#FFFFFF"),
                       (R.AlternateBase, "#F5F7FF"), (R.Text, "#0F172A"), (R.Button, "#FFFFFF"),
                       (R.ButtonText, "#0F172A"), (R.Highlight, "#6366F1"), (R.HighlightedText, "#FFFFFF"),
                       (R.ToolTipBase, "#1E293B"), (R.ToolTipText, "#F8FAFC"), (R.PlaceholderText, "#64748B")):
        pal.setColor(role, col(hexv))
    for role in (R.WindowText, R.Text, R.ButtonText):
        pal.setColor(G.Disabled, role, col("#94A3B8"))
    app.setPalette(pal)
    app.setStyleSheet(STYLE)
    app.setWindowIcon(make_icon())
    win = Main(make_tick())
    win.show()
    return app.exec()


def main() -> int:
    if not ensure_packages():
        return 1
    if _module_present("pytesseract") and _module_present("PIL"):
        try:
            ensure_ocr_engine(print)
        except Exception as exc:  # noqa - never block the app because of OCR set-up
            print(f"OCR set-up skipped: {exc}")
    if len(sys.argv) > 1 and not _in_idle():
        return run_cli(sys.argv[1:])
    return run_gui()


if __name__ == "__main__":
    _code = main()
    if not _in_idle():          # in IDLE, sys.exit would print a SystemExit traceback
        sys.exit(_code)
