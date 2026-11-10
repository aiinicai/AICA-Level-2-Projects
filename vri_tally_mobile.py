# -*- coding: utf-8 -*-
"""
VRI Tally Mobile  -  TallyPrime on your phone, on the go
=========================================================
VRI Group  |  Finance. Wealth. Technology. One Trusted Relationship.

HOW TO USE (on the PC where TallyPrime runs)
  1. Open TallyPrime and load your company/companies.
  2. In TallyPrime: F1 (Help) > Settings > Connectivity >
     "TallyPrime acts as" = Both (or Server), Port = 9000.  (One-time setting.)
  3. Open this file in IDLE and press F5.  First run installs the required
     libraries automatically (internet needed once).
  4. The desktop window opens. Go to "Mobile Access":
       - Same Wi-Fi: scan the QR code with your phone and enter the PIN.
       - On the go: switch on "Internet access" to get a secure https link.
  5. On the phone, use the browser menu "Add to Home screen" to get an app icon.

If an automatic install fails, run this once in Command Prompt:
  pip install PyQt5 reportlab qrcode pillow pycloudflared
"""

# =============================================================================
# 0. AUTO-INSTALL REQUIRED LIBRARIES (runs before any third-party import)
# =============================================================================
import sys
import os
import subprocess
import importlib
import importlib.util
import site

REQUIRED_LIBS = [("PyQt5", "PyQt5"), ("reportlab", "reportlab"),
                 ("qrcode", "qrcode"), ("PIL", "pillow")]
OPTIONAL_LIBS = [("pycloudflared", "pycloudflared")]   # only for internet access
PIP_LINE = "pip install PyQt5 reportlab qrcode pillow pycloudflared"


def _python_exe():
    exe = sys.executable or "python"
    # IDLE on Windows may run under pythonw.exe; pip is happier with python.exe
    if exe.lower().endswith("pythonw.exe"):
        cand = exe[:-len("pythonw.exe")] + "python.exe"
        if os.path.exists(cand):
            return cand
    return exe


def _run_quiet(cmd):
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, **kw)


def _pip_install(package):
    base = [_python_exe(), "-m", "pip", "install", "--disable-pip-version-check"]
    last = ""
    for extra in ([], ["--user"]):
        try:
            r = _run_quiet(base + extra + [package])
            if r.returncode == 0:
                return True, ""
            last = (r.stdout or "")[-600:]
        except Exception as exc:  # noqa
            last = str(exc)
    return False, last


def ensure_libraries():
    wanted = REQUIRED_LIBS + OPTIONAL_LIBS
    missing = [(m, p) for m, p in wanted if importlib.util.find_spec(m) is None]
    if not missing:
        return
    print("VRI Tally Mobile: installing libraries for first run, please wait...")
    if importlib.util.find_spec("pip") is None:
        try:
            _run_quiet([_python_exe(), "-m", "ensurepip", "--upgrade"])
        except Exception:
            pass
    for module, package in missing:
        print("  installing " + package + " ...")
        ok, log = _pip_install(package)
        print("    " + ("done" if ok else "could not install automatically"))
        if not ok and log:
            print("    " + log.strip().replace("\n", "\n    "))
    importlib.invalidate_caches()
    try:
        user_site = site.getusersitepackages()
        if user_site and user_site not in sys.path and os.path.isdir(user_site):
            sys.path.append(user_site)
    except Exception:
        pass
    still = [p for m, p in REQUIRED_LIBS if importlib.util.find_spec(m) is None]
    if still:
        print("\nThese libraries are still missing: " + ", ".join(still))
        print("Open Command Prompt and run:\n  " + PIP_LINE + "\nThen run this file again.")
        raise SystemExit(1)
    print("All libraries ready.\n")


ensure_libraries()

# =============================================================================
# 1. IMPORTS
# =============================================================================
import io
import re
import json
import hmac
import time
import socket
import secrets
import threading
import webbrowser
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as _xesc
from datetime import date, datetime, timedelta
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

APP_NAME = "VRI Tally Mobile"
APP_VERSION = "1.0"
APP_DIR = os.path.join(os.path.expanduser("~"), "Documents", "VRI_Tally_Mobile")
CACHE_DIR = os.path.join(APP_DIR, "cache")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
for _d in (APP_DIR, CACHE_DIR):
    os.makedirs(_d, exist_ok=True)


# =============================================================================
# 2. SMALL HELPERS
# =============================================================================
def xesc(s):
    return _xesc(str(s or ""), {'"': "&quot;", "'": "&apos;"})


def inr(v, sym=True):
    v = float(v or 0)
    neg = v < 0
    s = "%.2f" % abs(round(v, 2))
    whole, frac = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts) + "," + tail
    return ("-" if neg else "") + ("\u20b9" if sym else "") + whole + "." + frac


def drcr(v, sym=True):
    v = float(v or 0)
    if abs(v) < 0.005:
        return inr(0, sym)
    return inr(abs(v), sym) + (" Dr" if v > 0 else " Cr")


_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
         "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
         "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two(n):
    if n < 20:
        return _ONES[n]
    return _TENS[n // 10] + ((" " + _ONES[n % 10]) if n % 10 else "")


def _three(n):
    h, r = divmod(n, 100)
    s = (_ONES[h] + " Hundred") if h else ""
    if r:
        s += (" " if s else "") + _two(r)
    return s


def int_words(n):
    if n == 0:
        return "Zero"
    parts = []
    for div, name in ((10 ** 7, "Crore"), (10 ** 5, "Lakh"), (1000, "Thousand")):
        if n >= div:
            parts.append(int_words(n // div) + " " + name)
            n %= div
    if n:
        parts.append(_three(n))
    return " ".join(parts)


def words_inr(amount):
    amount = round(abs(float(amount or 0)), 2)
    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))
    s = "Rupees " + int_words(rupees)
    if paise:
        s += " and " + _two(paise) + " Paise"
    return s + " Only"


def ymd(d):
    return d.strftime("%Y%m%d")


def fy_start(d=None):
    d = d or date.today()
    return date(d.year if d.month >= 4 else d.year - 1, 4, 1)


def nice_date(s):
    try:
        return datetime.strptime(s, "%Y%m%d").strftime("%d-%b-%Y")
    except Exception:
        return s or ""


def parse_tally_date(s):
    s = (s or "").strip()
    for fmt in ("%Y%m%d", "%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y%m%d")
        except ValueError:
            pass
    return ""


_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def num(s):
    if s is None:
        return 0.0
    s = str(s)
    if "=" in s:                      # foreign currency: "-$10 @ 83 = -830.00"
        s = s.split("=")[-1]
    s = s.replace(" ", "").replace("\u20b9", "")
    m = _NUM.search(s)
    if not m:
        return 0.0
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return 0.0


def qty_unit(s):
    s = (s or "").strip().replace(",", "")
    m = _NUM.search(s)
    if not m:
        return 0.0, ""
    return float(m.group(0)), s[m.end():].strip()


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s or "").strip("_")[:60] or "company"


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))       # no packet is sent; just picks the LAN interface
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# =============================================================================
# 3. CONFIG
# =============================================================================
class Config:
    DEFAULTS = {"tally_host": "localhost", "tally_port": 9000, "web_port": 8765,
                "pin": "", "out_dir": os.path.join(APP_DIR, "PDFs"), "company": ""}

    def __init__(self):
        self.data = dict(self.DEFAULTS)
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.data.update(json.load(f))
        except Exception:
            pass
        if not re.fullmatch(r"\d{6}", str(self.data.get("pin", ""))):
            self.data["pin"] = "%06d" % secrets.randbelow(10 ** 6)
        os.makedirs(self.data["out_dir"], exist_ok=True)
        self.save()

    def __getitem__(self, k):
        return self.data.get(k, self.DEFAULTS.get(k))

    def __setitem__(self, k, v):
        self.data[k] = v
        self.save()

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass

    @property
    def tally_url(self):
        return "http://%s:%s" % (self["tally_host"], self["tally_port"])


# =============================================================================
# 4. TALLYPRIME XML CLIENT
# =============================================================================
class TallyError(Exception):
    pass


_CTRL_REF = re.compile(r"&#(x[0-9A-Fa-f]+|\d+);")
_CTRL_RAW = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _clean_xml(text):
    def rep(m):
        v = m.group(1)
        try:
            code = int(v[1:], 16) if v[0] in "xX" else int(v)
        except ValueError:
            return ""
        return m.group(0) if code in (9, 10, 13) or code >= 32 else ""
    text = _CTRL_REF.sub(rep, text)
    text = _CTRL_RAW.sub("", text)
    return re.sub(r"^\s*<\?xml[^>]*\?>", "", text.lstrip("\ufeff"))


def _decode(raw):
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    if len(raw) > 1 and raw[1:2] == b"\x00":
        return raw.decode("utf-16-le", errors="replace")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def _t(el, tag):
    c = el.find(tag)
    return (c.text or "").strip() if c is not None and c.text else ""


def _name(el):
    return (el.get("NAME") or _t(el, "NAME") or "").strip()


BASE_VTYPES = {"Sales", "Purchase", "Receipt", "Payment", "Contra", "Journal",
               "Credit Note", "Debit Note", "Sales Order", "Purchase Order",
               "Delivery Note", "Receipt Note", "Memorandum", "Stock Journal",
               "Physical Stock", "Rejections In", "Rejections Out", "Reversing Journal",
               "Attendance", "Payroll", "Job Work In Order", "Job Work Out Order",
               "Material In", "Material Out"}
ENTRY_TYPES = ["Sales", "Purchase", "Receipt", "Payment", "Contra", "Journal",
               "Credit Note", "Debit Note"]


class TallyClient:
    def __init__(self, url):
        self.url = url

    def post(self, xml, timeout=90):
        req = urllib.request.Request(self.url, data=xml.encode("utf-8"), method="POST",
                                     headers={"Content-Type": "text/xml; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
        except urllib.error.URLError as e:
            raise TallyError("Cannot reach TallyPrime at %s. Open TallyPrime, load the company "
                             "and enable Connectivity on port %s (F1 > Settings > Connectivity)."
                             % (self.url, self.url.rsplit(":", 1)[-1]))
        except (socket.timeout, TimeoutError):
            raise TallyError("TallyPrime took too long to answer. Try a shorter period.")
        text = _clean_xml(_decode(raw))
        self.last_raw = text
        try:
            return ET.fromstring(text)
        except ET.ParseError as e:
            raise TallyError("TallyPrime sent a response that could not be read (%s)." % e)

    def ping(self):
        try:
            with urllib.request.urlopen(self.url, timeout=4) as r:
                return b"Running" in r.read() or True
        except Exception:
            return False

    @staticmethod
    def _env(collection_tdl, company=None, frm=None, to=None, coll="VRICOLL"):
        sv = "<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
        if company:
            sv += "<SVCURRENTCOMPANY>%s</SVCURRENTCOMPANY>" % xesc(company)
        if frm:
            sv += '<SVFROMDATE TYPE="Date">%s</SVFROMDATE>' % frm
        if to:
            sv += '<SVTODATE TYPE="Date">%s</SVTODATE>' % to
        return ("<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST>"
                "<TYPE>Collection</TYPE><ID>%s</ID></HEADER><BODY><DESC><STATICVARIABLES>%s"
                "</STATICVARIABLES><TDL><TDLMESSAGE>%s</TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>"
                % (coll, sv, collection_tdl))

    def collection(self, typ, fetch, company=None, frm=None, to=None, filters=None):
        filt, system = "", ""
        if filters:
            names = []
            for i, formula in enumerate(filters):
                n = "VRIF%d" % i
                names.append(n)
                system += '<SYSTEM TYPE="Formulae" NAME="%s">%s</SYSTEM>' % (n, xesc(formula))
            filt = "<FILTERS>%s</FILTERS>" % ",".join(names)
        tdl = ('<COLLECTION NAME="VRICOLL" ISMODIFY="No"><TYPE>%s</TYPE><FETCH>%s</FETCH>%s'
               '</COLLECTION>%s' % (typ, fetch, filt, system))
        root = self.post(self._env(tdl, company, frm, to))
        coll = root.find(".//COLLECTION")
        if coll is None:
            err = " ".join((e.text or "").strip() for e in root.iter("LINEERROR"))
            if not err and root.tag == "RESPONSE":
                err = (root.text or "").strip()
            if err:
                if company and "company" in err.lower():
                    raise TallyError("Company '%s' is not open in TallyPrime. Load it and retry."
                                     % company)
                raise TallyError("TallyPrime: " + err)
            return []
        tag = typ.upper()
        return [c for c in coll if c.tag == tag]

    def _collection_fallback(self, typ, fetches, **kw):
        last = None
        for f in fetches:
            try:
                return self.collection(typ, f, **kw)
            except TallyError as e:
                if "Cannot reach" in str(e) or "not open" in str(e):
                    raise
                last = e
        raise last

    # ---------- masters ----------
    def companies(self):
        rows = self._collection_fallback(
            "Company", ["Name,StartingFrom,Address,StateName,Pincode,Email,PhoneNumber", "Name"])
        out = []
        for c in rows:
            nm = _name(c)
            if not nm:
                continue
            addr = [(a.text or "").strip() for a in c.iter("ADDRESS") if (a.text or "").strip()]
            out.append({"name": nm, "address": addr, "state": _t(c, "STATENAME"),
                        "pincode": _t(c, "PINCODE"), "email": _t(c, "EMAIL"),
                        "phone": _t(c, "PHONENUMBER"),
                        "start": parse_tally_date(_t(c, "STARTINGFROM"))})
        return out

    def groups(self, company):
        return {_name(g): _t(g, "PARENT") for g in self.collection("Group", "Name,Parent",
                                                                       company=company)}

    def vtypes(self, company):
        return {_name(v): _t(v, "PARENT") for v in self.collection("VoucherType", "Name,Parent",
                                                                       company=company)}

    def ledgers(self, company, frm, to):
        rows = self._collection_fallback(
            "Ledger", ["Name,Parent,OpeningBalance,ClosingBalance,LedgerMobile,Email,PartyGSTIN",
                       "Name,Parent,OpeningBalance,ClosingBalance"],
            company=company, frm=frm, to=to)
        out = []
        for l in rows:
            out.append({"name": _name(l), "parent": _t(l, "PARENT"),
                        "opening": -num(_t(l, "OPENINGBALANCE")),     # + = Dr
                        "closing": -num(_t(l, "CLOSINGBALANCE")),
                        "mobile": _t(l, "LEDGERMOBILE"), "email": _t(l, "EMAIL"),
                        "gstin": _t(l, "PARTYGSTIN")})
        return out

    # Vouchers are read in up to three ways, because TallyPrime releases differ.
    # The first one that returns vouchers wins.
    VCH_FETCH = ["Date,VoucherTypeName,VoucherNumber,PartyLedgerName,Narration,Reference,GUID,"
                 "MasterID,IsCancelled,IsOptional,AllLedgerEntries,LedgerEntries,"
                 "AllInventoryEntries,InventoryEntries",
                 "Date,VoucherTypeName,VoucherNumber,PartyLedgerName,Narration,GUID,MasterID,"
                 "AllLedgerEntries,AllInventoryEntries"]

    def daybook_xml(self, company, frm, to):
        return ("<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY>"
                "<EXPORTDATA><REQUESTDESC><REPORTNAME>Day Book</REPORTNAME><STATICVARIABLES>"
                "<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
                "<SVCURRENTCOMPANY>%s</SVCURRENTCOMPANY>"
                "<SVFROMDATE>%s</SVFROMDATE><SVTODATE>%s</SVTODATE>"
                "<EXPLODEFLAG>Yes</EXPLODEFLAG></STATICVARIABLES></REQUESTDESC></EXPORTDATA>"
                "</BODY></ENVELOPE>" % (xesc(company), frm, to))

    def _vch_daybook(self, company, frm, to):
        root = self.post(self.daybook_xml(company, frm, to), timeout=300)
        err = " ".join((e.text or "").strip() for e in root.iter("LINEERROR") if e.text)
        els = list(root.iter("VOUCHER"))
        if not els and err:
            raise TallyError("TallyPrime: " + err)
        return els

    def _vch_collection(self, company, frm, to):
        return self._collection_fallback(
            "Voucher", self.VCH_FETCH, company=company, frm=frm, to=to,
            filters=["$Date >= ##SVFromDate AND $Date <= ##SVToDate"])

    def _vch_collection_all(self, company, frm, to):
        # no date filter inside Tally; dates are filtered here instead
        return self._collection_fallback("Voucher", self.VCH_FETCH, company=company,
                                         frm=frm, to=to)

    def vouchers(self, company, frm, to, report=None):
        last_err = None
        for method in (self._vch_daybook, self._vch_collection, self._vch_collection_all):
            try:
                rows = method(company, frm, to)
            except TallyError as e:
                if "Cannot reach" in str(e) or "not open" in str(e):
                    raise
                last_err = e
                if report is not None:
                    report.append((method.__name__, "error: %s" % e, 0))
                continue
            out = self._parse_vouchers(rows, frm, to)
            if report is not None:
                report.append((method.__name__, "%d raw" % len(rows), len(out)))
            if out:
                return out
        return []

    def _parse_vouchers(self, rows, frm, to):
        out, seen = [], set()
        for i, v in enumerate(rows):
            d = parse_tally_date(_t(v, "DATE"))
            if not d or d < frm or d > to:
                continue
            if _t(v, "ISCANCELLED") == "Yes" or _t(v, "ISOPTIONAL") == "Yes" or \
                    _t(v, "ISDELETED") == "Yes":
                continue
            key = _t(v, "MASTERID") or _t(v, "GUID")
            if key and key in seen:
                continue
            seen.add(key)

            def entries(tag):
                res = []
                for le in v.findall(tag):
                    led = _t(le, "LEDGERNAME")
                    if led:
                        res.append({"ledger": led, "amount": round(-num(_t(le, "AMOUNT")), 2)})
                return res
            ents = entries("ALLLEDGERENTRIES.LIST") or entries("LEDGERENTRIES.LIST")
            items = []
            inv = v.findall("ALLINVENTORYENTRIES.LIST") or v.findall("INVENTORYENTRIES.LIST")
            for ie in inv:
                item = _t(ie, "STOCKITEMNAME")
                if not item:
                    continue
                q, unit = qty_unit(_t(ie, "BILLEDQTY") or _t(ie, "ACTUALQTY"))
                items.append({"item": item, "qty": q, "unit": unit,
                              "rate": num(_t(ie, "RATE")), "amount": abs(num(_t(ie, "AMOUNT")))})
                # invoice-mode sales/purchase ledgers sit inside the item lines
                for ac in ie.findall("ACCOUNTINGALLOCATIONS.LIST"):
                    led = _t(ac, "LEDGERNAME")
                    if led and not any(e["ledger"] == led for e in ents):
                        ents.append({"ledger": led, "amount": round(-num(_t(ac, "AMOUNT")), 2)})
            total = round(sum(e["amount"] for e in ents if e["amount"] > 0), 2)
            if not total and items:
                total = round(sum(x["amount"] for x in items), 2)
            vid = _t(v, "MASTERID") or _t(v, "GUID") or ("%s-%d" % (d, i))
            out.append({"id": vid, "date": d, "type": _t(v, "VOUCHERTYPENAME") or v.get("VCHTYPE", ""),
                        "no": _t(v, "VOUCHERNUMBER"), "party": _t(v, "PARTYLEDGERNAME"),
                        "narration": _t(v, "NARRATION"), "ref": _t(v, "REFERENCE"),
                        "entries": ents, "items": items, "total": total})
        out.sort(key=lambda x: (x["date"], x["id"]))
        return out

    def bills(self, company, to):
        try:
            rows = self.collection("Bill", "Name,Parent,ClosingBalance,BillDate,BillCreditPeriod",
                                   company=company, to=to)
        except TallyError as e:
            if "Cannot reach" in str(e):
                raise
            return []
        out = []
        for b in rows:
            amt = -num(_t(b, "CLOSINGBALANCE"))
            if abs(amt) < 0.005:
                continue
            out.append({"name": _name(b), "party": _t(b, "PARENT"), "amount": round(amt, 2),
                        "date": parse_tally_date(_t(b, "BILLDATE")),
                        "credit": _t(b, "BILLCREDITPERIOD")})
        return out

    # ---------- posting ----------
    def post_voucher(self, company, vtype, vdate, lines, party, narration="", ref="",
                     remote_id=""):
        ents = ""
        for led, amt in lines:
            ents += ("<ALLLEDGERENTRIES.LIST><LEDGERNAME>%s</LEDGERNAME>"
                     "<ISDEEMEDPOSITIVE>%s</ISDEEMEDPOSITIVE><ISPARTYLEDGER>%s</ISPARTYLEDGER>"
                     "<AMOUNT>%.2f</AMOUNT></ALLLEDGERENTRIES.LIST>"
                     % (xesc(led), "Yes" if amt > 0 else "No",
                        "Yes" if party and led == party else "No", -amt))
        rid = ' REMOTEID="%s"' % xesc(remote_id) if remote_id else ""
        xml = ("<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY>"
               "<IMPORTDATA><REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME><STATICVARIABLES>"
               "<SVCURRENTCOMPANY>%s</SVCURRENTCOMPANY></STATICVARIABLES></REQUESTDESC>"
               "<REQUESTDATA><TALLYMESSAGE xmlns:UDF=\"TallyUDF\">"
               "<VOUCHER%s VCHTYPE=\"%s\" ACTION=\"Create\" OBJVIEW=\"Accounting Voucher View\">"
               "<DATE>%s</DATE><VOUCHERTYPENAME>%s</VOUCHERTYPENAME>"
               "<PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>%s%s"
               "<NARRATION>%s</NARRATION>%s</VOUCHER></TALLYMESSAGE></REQUESTDATA>"
               "</IMPORTDATA></BODY></ENVELOPE>"
               % (xesc(company), rid, xesc(vtype), vdate, xesc(vtype),
                  ("<PARTYLEDGERNAME>%s</PARTYLEDGERNAME>" % xesc(party)) if party else "",
                  ("<REFERENCE>%s</REFERENCE>" % xesc(ref)) if ref else "",
                  xesc(narration), ents))
        root = self.post(xml)

        def first(tag):
            e = next(root.iter(tag), None)
            return (e.text or "").strip() if e is not None and e.text else ""
        created = int(num(first("CREATED")))
        errors = " ".join((e.text or "").strip() for e in root.iter("LINEERROR") if e.text)
        if created >= 1:
            return {"ok": True, "id": first("LASTVCHID")}
        raise TallyError(errors or "TallyPrime did not create the voucher. Check that the ledgers "
                                   "exist and the date is inside the financial year.")


# =============================================================================
# 5. DATA SERVICE  (fetch, cache, reports)
# =============================================================================
def _ancestry(parent, groups):
    out, cur, seen = [], parent, set()
    while cur and cur not in seen and cur != "Primary" and len(out) < 30:
        out.append(cur)
        seen.add(cur)
        cur = groups.get(cur, "")
    return out


def _kind(anc):
    s = set(anc)
    if "Sundry Debtors" in s:
        return "debtor"
    if "Sundry Creditors" in s:
        return "creditor"
    if "Cash-in-Hand" in s:
        return "cash"
    if s & {"Bank Accounts", "Bank OD A/c", "Bank OCC A/c"}:
        return "bank"
    if "Sales Accounts" in s:
        return "sales"
    if "Purchase Accounts" in s:
        return "purchase"
    if "Duties & Taxes" in s:
        return "tax"
    if s & {"Direct Expenses", "Indirect Expenses"}:
        return "expense"
    if s & {"Direct Incomes", "Indirect Incomes"}:
        return "income"
    return "other"


def _base_type(name, vtypes):
    cur = name
    for _ in range(20):
        if cur in BASE_VTYPES:
            return cur
        p = vtypes.get(cur, "")
        if not p or p == cur or p == "Primary":
            return cur
        cur = p
    return cur


class DataService:
    TTL = 120

    def __init__(self, cfg):
        self.cfg = cfg
        self.client = TallyClient(cfg.tally_url)
        self.lock = threading.RLock()
        self._bundles = {}
        self._companies = (0, None)

    def reconnect(self):
        self.client = TallyClient(self.cfg.tally_url)
        self._bundles.clear()
        self._companies = (0, None)

    def _cache_path(self, company, frm, to):
        return os.path.join(CACHE_DIR, "%s_%s_%s.json" % (slug(company), frm, to))

    def companies(self, force=False):
        with self.lock:
            ts, data = self._companies
            if data is not None and not force and time.time() - ts < 60:
                return data
            path = os.path.join(CACHE_DIR, "companies.json")
            try:
                data = self.client.companies()
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f)
            except TallyError:
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    raise
            self._companies = (time.time(), data)
            return data

    def default_period(self):
        return ymd(fy_start()), ymd(date.today())

    def bundle(self, company, frm=None, to=None, force=False):
        if not company:
            raise TallyError("Choose a company first.")
        d_frm, d_to = self.default_period()
        frm, to = frm or d_frm, to or d_to
        key = (company, frm, to)
        with self.lock:
            hit = self._bundles.get(key)
            if hit and not force and time.time() - hit["_ts"] < self.TTL:
                return hit
            try:
                b = self._fetch(company, frm, to)
                try:
                    with open(self._cache_path(company, frm, to), "w", encoding="utf-8") as f:
                        json.dump({k: v for k, v in b.items() if k != "_ts"}, f)
                except Exception:
                    pass
            except TallyError as e:
                try:
                    with open(self._cache_path(company, frm, to), encoding="utf-8") as f:
                        b = json.load(f)
                    b["offline"] = str(e)
                except Exception:
                    raise e
            b["_ts"] = time.time()
            self._bundles[key] = b
            return b

    def invalidate(self, company=None):
        with self.lock:
            for k in list(self._bundles):
                if company is None or k[0] == company:
                    del self._bundles[k]

    def _fetch(self, company, frm, to):
        c = self.client
        info = {}
        try:
            for co in self.companies():
                if co["name"] == company:
                    info = co
        except TallyError:
            pass
        groups = c.groups(company)
        vtypes = c.vtypes(company)
        ledgers = c.ledgers(company, frm, to)
        for l in ledgers:
            l["anc"] = _ancestry(l["parent"], groups)
            l["kind"] = _kind(l["anc"])
        vouchers = c.vouchers(company, frm, to)
        for v in vouchers:
            v["base"] = _base_type(v["type"], vtypes)
        bills = c.bills(company, to)
        return {"company": company, "info": info, "from": frm, "to": to,
                "fetched": datetime.now().strftime("%d-%b-%Y %I:%M %p"),
                "vtypes": {k: _base_type(k, vtypes) for k in vtypes},
                "ledgers": ledgers, "vouchers": vouchers, "bills": bills}

    def diagnose(self, company, frm=None, to=None):
        d_frm, d_to = self.default_period()
        frm, to = frm or d_frm, to or d_to
        lines = ["Company: %s" % company, "Period: %s to %s" % (nice_date(frm), nice_date(to)),
                 "TallyPrime: %s" % self.cfg.tally_url, ""]
        with self.lock:
            try:
                lines.append("Ledgers found: %d" % len(self.client.ledgers(company, frm, to)))
            except TallyError as e:
                lines.append("Ledgers: " + str(e))
            report = []
            try:
                self.client.vouchers(company, frm, to, report=report)
            except TallyError as e:
                lines.append("Vouchers: " + str(e))
            names = {"_vch_daybook": "Day Book export", "_vch_collection": "Voucher list (dated)",
                     "_vch_collection_all": "Voucher list (all)"}
            for m, info, n in report:
                lines.append("%s: %s, %d in period" % (names.get(m, m), info, n))
            raw_path = os.path.join(APP_DIR, "diagnostic_daybook.xml")
            try:
                self.client.post(self.client.daybook_xml(company, frm, to), timeout=300)
                with open(raw_path, "w", encoding="utf-8") as f:
                    f.write(self.client.last_raw[:300000])
                lines += ["", "Tally's Day Book reply saved to:", raw_path]
            except Exception as e:  # noqa
                lines.append("Could not save Tally's reply: %s" % e)
        self.invalidate(company)
        return "\n".join(lines)

    # ---------- posting ----------
    def post_entry(self, company, form):
        b = self.bundle(company)
        lines, party, base = build_lines(form, b)
        vdate = re.sub(r"\D", "", form.get("date") or "") or ymd(date.today())
        res = self.client.post_voucher(company, form.get("vtype") or base, vdate, lines, party,
                                       form.get("narration", ""), form.get("ref", ""),
                                       "VRI-" + secrets.token_hex(8))
        self.invalidate(company)
        return res


# ---------------- report builders (pure functions on a bundle) ----------------
def ledger_map(b):
    return {l["name"]: l for l in b["ledgers"]}


def dashboard(b):
    by = {}
    for v in b["vouchers"]:
        by.setdefault(v["base"], [0.0, 0])
        by[v["base"]][0] += v["total"]
        by[v["base"]][1] += 1
    led = b["ledgers"]
    s = lambda k: round(sum(l["closing"] for l in led if l["kind"] == k), 2)
    months = {}
    for v in b["vouchers"]:
        m = v["date"][:6]
        months.setdefault(m, [0.0, 0.0])
        if v["base"] == "Sales":
            months[m][0] += v["total"]
        elif v["base"] == "Purchase":
            months[m][1] += v["total"]
    monthly = [{"label": datetime.strptime(m, "%Y%m").strftime("%b %y"),
                "sales": round(x[0], 2), "purchase": round(x[1], 2)}
               for m, x in sorted(months.items())][-12:]
    debtors = sorted([l for l in led if l["kind"] == "debtor" and l["closing"] > 0.5],
                     key=lambda l: -l["closing"])[:6]
    recent = sorted(b["vouchers"], key=lambda v: (v["date"], v["id"]), reverse=True)[:8]
    tot = lambda k: round(by.get(k, [0, 0])[0], 2)
    return {"sales": tot("Sales"), "purchase": tot("Purchase"), "receipt": tot("Receipt"),
            "payment": tot("Payment"), "receivable": s("debtor"), "payable": -s("creditor"),
            "cash": s("cash"), "bank": s("bank"),
            "counts": {k: v[1] for k, v in by.items()}, "monthly": monthly,
            "top_debtors": [{"name": l["name"], "balance": l["closing"], "mobile": l["mobile"]}
                            for l in debtors],
            "recent": [vsummary(v) for v in recent]}


def vsummary(v):
    return {"id": v["id"], "date": v["date"], "type": v["type"], "base": v["base"],
            "no": v["no"], "party": v["party"] or (v["entries"][0]["ledger"] if v["entries"] else ""),
            "total": v["total"]}


def ledger_list(b):
    return [{"name": l["name"], "group": l["parent"], "balance": l["closing"], "kind": l["kind"],
             "mobile": l["mobile"], "email": l["email"]}
            for l in sorted(b["ledgers"], key=lambda x: x["name"].lower())]


def statement(b, name):
    l = ledger_map(b).get(name)
    if not l:
        raise TallyError("Ledger '%s' not found." % name)
    rows, net = [], 0.0
    for v in b["vouchers"]:
        amt = round(sum(e["amount"] for e in v["entries"] if e["ledger"] == name), 2)
        if abs(amt) < 0.005:
            continue
        others = [e for e in v["entries"] if e["ledger"] != name and (e["amount"] > 0) != (amt > 0)]
        if v["party"] and v["party"] != name:
            part = v["party"]
        elif others:
            part = max(others, key=lambda e: abs(e["amount"]))["ledger"]
        else:
            part = v["type"]
        rows.append({"vid": v["id"], "date": v["date"], "type": v["type"], "no": v["no"],
                     "particulars": part, "dr": amt if amt > 0 else 0.0,
                     "cr": -amt if amt < 0 else 0.0, "narration": v["narration"]})
        net += amt
    opening = round(l["closing"] - net, 2)
    bal = opening
    for r in rows:
        bal = round(bal + r["dr"] - r["cr"], 2)
        r["balance"] = bal
    return {"ledger": name, "group": l["parent"], "kind": l["kind"], "mobile": l["mobile"],
            "email": l["email"], "gstin": l["gstin"], "opening": opening, "closing": l["closing"],
            "total_dr": round(sum(r["dr"] for r in rows), 2),
            "total_cr": round(sum(r["cr"] for r in rows), 2), "rows": rows,
            "from": b["from"], "to": b["to"]}


def outstanding(b, kind="debtor"):
    sign = 1 if kind == "debtor" else -1
    to = datetime.strptime(b["to"], "%Y%m%d").date()
    bills_by = {}
    for bl in b.get("bills", []):
        bills_by.setdefault(bl["party"], []).append(bl)
    parties, buckets = [], {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    for l in b["ledgers"]:
        if l["kind"] != kind:
            continue
        bal = l["closing"] * sign
        if abs(bal) < 0.5:
            continue
        bl = []
        for x in bills_by.get(l["name"], []):
            age = (to - datetime.strptime(x["date"], "%Y%m%d").date()).days if x["date"] else 0
            amt = round(x["amount"] * sign, 2)
            bl.append({"name": x["name"], "date": x["date"], "amount": amt, "age": age})
            if amt > 0:
                k = "0-30" if age <= 30 else "31-60" if age <= 60 else "61-90" if age <= 90 else "90+"
                buckets[k] += amt
        bl.sort(key=lambda x: x["date"])
        parties.append({"name": l["name"], "balance": round(bal, 2), "mobile": l["mobile"],
                        "email": l["email"], "bills": bl})
    parties.sort(key=lambda p: -p["balance"])
    return {"kind": kind, "parties": parties,
            "total": round(sum(p["balance"] for p in parties), 2),
            "buckets": {k: round(v, 2) for k, v in buckets.items()},
            "billwise": bool(b.get("bills"))}


def find_voucher(b, vid):
    for v in b["vouchers"]:
        if v["id"] == vid:
            out = dict(v)
            p = ledger_map(b).get(v["party"]) if v["party"] else None
            out["party_info"] = {"mobile": p["mobile"], "email": p["email"],
                                 "gstin": p["gstin"]} if p else {}
            return out
    raise TallyError("Voucher not found. Refresh and try again.")


def entry_meta(b):
    led = sorted(b["ledgers"], key=lambda l: l["name"].lower())
    taxes = [l["name"] for l in led if l["kind"] == "tax"]
    pick = lambda key: next((t for t in taxes if key in t.upper()), "")
    return {"types": [{"name": n, "base": base} for n, base in sorted(b["vtypes"].items())
                      if base in ENTRY_TYPES],
            "ledgers": [{"name": l["name"], "kind": l["kind"]} for l in led],
            "tax": {"cgst": pick("CGST"), "sgst": pick("SGST") or pick("UTGST"),
                    "igst": pick("IGST"), "all": taxes}}


ENTRY_LABELS = {
    "Sales": ("Party (customer)", "Sales ledger"),
    "Purchase": ("Party (supplier)", "Purchase ledger"),
    "Receipt": ("Received from", "Received into (Cash / Bank)"),
    "Payment": ("Paid to", "Paid from (Cash / Bank)"),
    "Contra": ("Transfer to (Cash / Bank)", "Transfer from (Cash / Bank)"),
    "Journal": ("Debit ledger", "Credit ledger"),
    "Credit Note": ("Party (customer)", "Sales ledger"),
    "Debit Note": ("Party (supplier)", "Purchase ledger"),
}


def build_lines(form, b=None):
    """Turn a simple entry form into balanced ledger lines (+ = Debit)."""
    vtype = (form.get("vtype") or "").strip()
    base = (b or {}).get("vtypes", {}).get(vtype) if b else None
    base = base or form.get("base") or vtype
    if base not in ENTRY_TYPES:
        raise TallyError("Choose a voucher type.")
    a = (form.get("party") or "").strip()
    acc = (form.get("account") or "").strip()
    try:
        amt = round(float(str(form.get("amount") or "0").replace(",", "")), 2)
    except ValueError:
        raise TallyError("Enter the amount as a number.")
    if not a or not acc:
        raise TallyError("Fill in both ledgers.")
    if a == acc:
        raise TallyError("The two ledgers must be different.")
    if amt <= 0:
        raise TallyError("Amount must be more than zero.")
    if b:
        names = {l["name"] for l in b["ledgers"]}
        for n in (a, acc):
            if n not in names:
                raise TallyError("Ledger '%s' does not exist in Tally. Pick one from the list." % n)
    rate = float(form.get("gst_rate") or 0)
    taxes = []
    if base in ("Sales", "Purchase", "Credit Note", "Debit Note") and rate > 0:
        if form.get("gst_mode") == "inter":
            led = (form.get("igst") or "").strip()
            if not led:
                raise TallyError("Choose the IGST ledger.")
            taxes = [(led, round(amt * rate / 100, 2))]
        else:
            c, s = (form.get("cgst") or "").strip(), (form.get("sgst") or "").strip()
            if not c or not s:
                raise TallyError("Choose the CGST and SGST ledgers.")
            half = round(amt * rate / 200, 2)
            taxes = [(c, half), (s, half)]
    total = round(amt + sum(t[1] for t in taxes), 2)
    if base == "Sales":
        lines = [(a, total), (acc, -amt)] + [(t, -x) for t, x in taxes]
    elif base == "Debit Note":
        lines = [(a, total), (acc, -amt)] + [(t, -x) for t, x in taxes]
    elif base in ("Purchase", "Credit Note"):
        lines = [(acc, amt)] + [(t, x) for t, x in taxes] + [(a, -total)]
    elif base == "Receipt":
        lines = [(acc, amt), (a, -amt)]
    else:  # Payment, Contra, Journal: first ledger Dr, second Cr
        lines = [(a, amt), (acc, -amt)]
    if abs(sum(x for _, x in lines)) > 0.009:
        raise TallyError("Entry does not balance.")
    party = a if base not in ("Journal", "Contra") else ""
    return lines, party, base


# =============================================================================
# 6. PDF  (vouchers and ledger statements)
# =============================================================================
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_PDF = {"font": "Helvetica", "bold": "Helvetica-Bold", "rs": "Rs. "}


def _setup_pdf_fonts():
    windir = os.environ.get("WINDIR", r"C:\Windows")
    for reg, bold in (("arial.ttf", "arialbd.ttf"), ("Nirmala.ttf", "NirmalaB.ttf"),
                      ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")):
        cands = [os.path.join(windir, "Fonts", reg),
                 "/usr/share/fonts/truetype/dejavu/" + reg]
        bcands = [os.path.join(windir, "Fonts", bold),
                  "/usr/share/fonts/truetype/dejavu/" + bold]
        rp = next((p for p in cands if os.path.exists(p)), None)
        bp = next((p for p in bcands if os.path.exists(p)), None)
        if not rp or not bp:
            continue
        try:
            f = TTFont("VRIReg", rp)
            pdfmetrics.registerFont(f)
            pdfmetrics.registerFont(TTFont("VRIBold", bp))
            _PDF["font"], _PDF["bold"] = "VRIReg", "VRIBold"
            if 0x20B9 in getattr(f.face, "charToGlyph", {}):
                _PDF["rs"] = "\u20b9"
            return
        except Exception:
            continue


_setup_pdf_fonts()
PDF_INK = colors.HexColor("#1c1640")
PDF_ACC = colors.HexColor("#4b2bd6")
PDF_SOFT = colors.HexColor("#efeafe")


def _money(v):
    return _PDF["rs"] + inr(v, sym=False)


def _styles():
    f, fb = _PDF["font"], _PDF["bold"]
    return {
        "co": ParagraphStyle("co", fontName=fb, fontSize=16, leading=19, textColor=PDF_INK),
        "small": ParagraphStyle("s", fontName=f, fontSize=8.5, leading=11,
                                textColor=colors.HexColor("#555070")),
        "title": ParagraphStyle("t", fontName=fb, fontSize=14, leading=17, textColor=PDF_ACC),
        "body": ParagraphStyle("b", fontName=f, fontSize=9.5, leading=12.5, textColor=PDF_INK),
        "bold": ParagraphStyle("bb", fontName=fb, fontSize=9.5, leading=12.5, textColor=PDF_INK),
        "foot": ParagraphStyle("f", fontName=f, fontSize=7.5, leading=9,
                               textColor=colors.HexColor("#8a86a6")),
    }


def _company_block(b, st):
    info = b.get("info") or {}
    lines = [Paragraph(xesc(b["company"]), st["co"])]
    addr = ", ".join(info.get("address") or [])
    extra = " | ".join(x for x in [
        ", ".join(x for x in [addr, info.get("state", ""), info.get("pincode", "")] if x),
        ("Ph: " + info["phone"]) if info.get("phone") else "",
        info.get("email", "")] if x)
    if extra:
        lines.append(Paragraph(xesc(extra), st["small"]))
    return lines


def _table(data, widths, head=True, align_right=(), bold_last=False):
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    style = [("FONTNAME", (0, 0), (-1, -1), _PDF["font"]), ("FONTSIZE", (0, 0), (-1, -1), 8.8),
             ("TEXTCOLOR", (0, 0), (-1, -1), PDF_INK), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#ddd8f5")),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if head:
        style += [("BACKGROUND", (0, 0), (-1, 0), PDF_ACC), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), _PDF["bold"])]
    for c in align_right:
        style.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    if bold_last:
        style += [("FONTNAME", (0, -1), (-1, -1), _PDF["bold"]),
                  ("BACKGROUND", (0, -1), (-1, -1), PDF_SOFT)]
    t.setStyle(TableStyle(style))
    return t


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(_PDF["font"], 7.5)
    canvas.setFillColor(colors.HexColor("#8a86a6"))
    canvas.drawString(15 * mm, 9 * mm, "Generated from TallyPrime via %s on %s"
                      % (APP_NAME, datetime.now().strftime("%d-%b-%Y %I:%M %p")))
    canvas.drawRightString(195 * mm, 9 * mm, "Page %d" % doc.page)
    canvas.setFillColor(PDF_ACC)
    canvas.rect(0, A4[1] - 6 * mm, A4[0], 6 * mm, stroke=0, fill=1)
    canvas.restoreState()


def voucher_pdf(b, v):
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=14 * mm, bottomMargin=16 * mm,
                            title="%s %s" % (v["type"], v["no"]), author=b["company"])
    el = _company_block(b, st) + [Spacer(1, 5 * mm)]
    head = Table([[Paragraph(xesc(v["type"]).upper(), st["title"]),
                   Paragraph("<b>No.</b> %s<br/><b>Date</b> %s" % (xesc(v["no"] or "-"),
                                                                   nice_date(v["date"])), st["body"])]],
                 colWidths=[110 * mm, 70 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("BACKGROUND", (0, 0), (-1, -1), PDF_SOFT),
                              ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                              ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    el += [head, Spacer(1, 4 * mm)]
    if v.get("party"):
        pi = v.get("party_info") or {}
        extra = " &nbsp; ".join(x for x in [("GSTIN: " + xesc(pi["gstin"])) if pi.get("gstin") else "",
                                            ("Mobile: " + xesc(pi["mobile"])) if pi.get("mobile") else ""] if x)
        el.append(Paragraph("<b>Party:</b> %s%s" % (xesc(v["party"]), ("<br/>" + extra) if extra else ""),
                            st["body"]))
        el.append(Spacer(1, 4 * mm))
    if v.get("items"):
        data = [["#", "Item", "Qty", "Rate", "Amount"]]
        for i, it in enumerate(v["items"], 1):
            data.append([str(i), Paragraph(xesc(it["item"]), st["body"]),
                         ("%g %s" % (it["qty"], it["unit"])).strip(), inr(it["rate"], False),
                         inr(it["amount"], False)])
        data.append(["", "Items total", "", "", inr(sum(x["amount"] for x in v["items"]), False)])
        el += [_table(data, [10 * mm, 88 * mm, 26 * mm, 26 * mm, 30 * mm], align_right=(2, 3, 4),
                      bold_last=True), Spacer(1, 4 * mm)]
    data = [["Particulars", "Debit", "Credit"]]
    for e in v["entries"]:
        data.append([Paragraph(xesc(e["ledger"]), st["body"]),
                     inr(e["amount"], False) if e["amount"] > 0 else "",
                     inr(-e["amount"], False) if e["amount"] < 0 else ""])
    data.append(["Total", inr(v["total"], False), inr(v["total"], False)])
    el.append(_table(data, [120 * mm, 30 * mm, 30 * mm], align_right=(1, 2), bold_last=True))
    el += [Spacer(1, 3 * mm), Paragraph("<b>Amount:</b> %s &nbsp; (%s)" % (_money(v["total"]),
                                                                          words_inr(v["total"])), st["body"])]
    if v.get("narration"):
        el += [Spacer(1, 3 * mm), Paragraph("<b>Narration:</b> " + xesc(v["narration"]), st["body"])]
    el += [Spacer(1, 16 * mm),
           Table([["", Paragraph("For <b>%s</b><br/><br/><br/>Authorised Signatory" % xesc(b["company"]),
                                 st["body"])]], colWidths=[100 * mm, 80 * mm])]
    doc.build(el, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def statement_pdf(b, s):
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=14 * mm, bottomMargin=16 * mm,
                            title="Ledger - %s" % s["ledger"], author=b["company"])
    el = _company_block(b, st) + [Spacer(1, 5 * mm)]
    el.append(Paragraph("LEDGER STATEMENT", st["title"]))
    el.append(Paragraph("<b>%s</b> (%s) &nbsp; | &nbsp; %s to %s"
                        % (xesc(s["ledger"]), xesc(s["group"]), nice_date(s["from"]),
                           nice_date(s["to"])), st["body"]))
    el.append(Spacer(1, 4 * mm))
    data = [["Date", "Particulars", "Type", "No.", "Debit", "Credit", "Balance"],
            [nice_date(s["from"]), "Opening Balance", "", "", "", "", drcr(s["opening"], False)]]
    for r in s["rows"]:
        data.append([nice_date(r["date"]), Paragraph(xesc(r["particulars"]), st["body"]),
                     Paragraph(xesc(r["type"]), st["small"]), r["no"],
                     inr(r["dr"], False) if r["dr"] else "", inr(r["cr"], False) if r["cr"] else "",
                     drcr(r["balance"], False)])
    data.append(["", "Closing Balance", "", "", inr(s["total_dr"], False), inr(s["total_cr"], False),
                 drcr(s["closing"], False)])
    el.append(_table(data, [21 * mm, 56 * mm, 22 * mm, 15 * mm, 24 * mm, 24 * mm, 24 * mm],
                     align_right=(4, 5, 6), bold_last=True))
    doc.build(el, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def share_text_voucher(b, v):
    return ("Dear %s,\nPlease find attached %s No. %s dated %s for %s.\nRegards,\n%s"
            % (v["party"] or "Sir/Madam", v["type"], v["no"] or "-", nice_date(v["date"]),
               inr(v["total"]), b["company"]))


def share_text_ledger(b, s):
    return ("Dear %s,\nPlease find attached your ledger statement with %s for %s to %s.\n"
            "Closing balance: %s.\nRegards,\n%s"
            % (s["ledger"], b["company"], nice_date(s["from"]), nice_date(s["to"]),
               drcr(s["closing"]), b["company"]))


def wa_link(phone, text):
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        digits = "91" + digits
    return "https://wa.me/%s?text=%s" % (digits, urllib.parse.quote(text))


# =============================================================================
# 7. MOBILE WEB SERVER (PIN protected)
# =============================================================================
class MobileServer:
    def __init__(self, svc, cfg):
        self.svc, self.cfg = svc, cfg
        self.httpd = None
        self.sessions = {}
        self.fails = []
        self.slock = threading.Lock()
        self.error = ""
        self.tunnel_url = ""

    @property
    def port(self):
        return int(self.cfg["web_port"])

    def start(self):
        if self.httpd:
            return True
        svc_ref = self

        class H(Handler):
            server_ref = svc_ref
        try:
            self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), H)
        except OSError as e:
            self.error = "Port %s is busy (%s). Change it in Settings." % (self.port, e)
            self.httpd = None
            return False
        self.httpd.daemon_threads = True
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.error = ""
        return True

    def stop(self):
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
            self.httpd = None

    def lan_url(self):
        return "http://%s:%s" % (lan_ip(), self.port)

    # ---- auth ----
    def login(self, pin, ip):
        now = time.time()
        with self.slock:
            self.fails = [f for f in self.fails if now - f[0] < 900]
            ip_fails = [f for f in self.fails if f[1] == ip and now - f[0] < 300]
            if len(ip_fails) >= 5 or len(self.fails) >= 20:
                return None, "Too many wrong PINs. Wait 15 minutes and try again."
            if hmac.compare_digest(str(pin or ""), str(self.cfg["pin"])):
                tok = secrets.token_urlsafe(32)
                self.sessions[tok] = now + 12 * 3600
                return tok, ""
            self.fails.append((now, ip))
            return None, "Wrong PIN."

    def valid(self, tok):
        with self.slock:
            exp = self.sessions.get(tok or "")
            if exp and exp > time.time():
                return True
            self.sessions.pop(tok or "", None)
            return False

    def logout_all(self):
        with self.slock:
            self.sessions.clear()

    # ---- internet tunnel (optional) ----
    def start_tunnel(self):
        try:
            from pycloudflared import try_cloudflare
        except Exception:
            raise TallyError("Internet access needs the 'pycloudflared' library. Run:  "
                             "pip install pycloudflared")
        urls = try_cloudflare(port=self.port, verbose=False)
        self.tunnel_url = urls.tunnel
        return self.tunnel_url

    def stop_tunnel(self):
        if not self.tunnel_url:
            return
        try:
            from pycloudflared import try_cloudflare
            try_cloudflare.terminate(self.port)
        except Exception:
            pass
        self.tunnel_url = ""


class Handler(BaseHTTPRequestHandler):
    server_ref = None
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _ip(self):
        return self.headers.get("CF-Connecting-IP") or self.client_address[0]

    def _authed(self):
        auth = self.headers.get("Authorization", "")
        return auth.startswith("Bearer ") and self.server_ref.valid(auth[7:].strip())

    def do_GET(self):
        try:
            self._route("GET")
        except TallyError as e:
            self._send(400, {"error": str(e)})
        except Exception as e:  # noqa
            self._send(500, {"error": "Something went wrong: %s" % e})

    def do_POST(self):
        try:
            self._route("POST")
        except TallyError as e:
            self._send(400, {"error": str(e)})
        except Exception as e:  # noqa
            self._send(500, {"error": "Something went wrong: %s" % e})

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 200000:
            raise TallyError("Request too large.")
        return json.loads(self.rfile.read(n).decode("utf-8") or "{}") if n else {}

    def _route(self, method):
        u = urllib.parse.urlparse(self.path)
        path = u.path
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        srv, svc = self.server_ref, self.server_ref.svc
        if method == "GET" and path in ("/", "/index.html"):
            return self._send(200, MOBILE_HTML, "text/html; charset=utf-8")
        if method == "GET" and path == "/manifest.json":
            return self._send(200, MANIFEST, "application/manifest+json")
        if method == "GET" and path == "/icon.svg":
            return self._send(200, ICON_SVG, "image/svg+xml")
        if method == "POST" and path == "/api/login":
            tok, err = srv.login(self._body().get("pin"), self._ip())
            return self._send(200 if tok else 403, {"token": tok} if tok else {"error": err})
        if not path.startswith("/api/"):
            return self._send(404, {"error": "Not found"})
        if not self._authed():
            return self._send(401, {"error": "Please log in."})

        if path == "/api/companies":
            return self._send(200, {"companies": [c["name"] for c in svc.companies(q.get("force") == "1")],
                                    "default": srv.cfg["company"]})
        if method == "POST" and path == "/api/entry":
            body = self._body()
            res = svc.post_entry(body.get("c", ""), body)
            return self._send(200, res)

        b = svc.bundle(q.get("c", ""), q.get("from"), q.get("to"), q.get("force") == "1")
        meta = {"company": b["company"], "from": b["from"], "to": b["to"], "fetched": b["fetched"],
                "offline": b.get("offline", "")}
        if path == "/api/dashboard":
            return self._send(200, dict(meta, **dashboard(b)))
        if path == "/api/ledgers":
            return self._send(200, dict(meta, ledgers=ledger_list(b)))
        if path == "/api/ledger":
            s = statement(b, q.get("name", ""))
            s["share"] = share_text_ledger(b, s)
            return self._send(200, dict(meta, **s))
        if path == "/api/outstanding":
            return self._send(200, dict(meta, **outstanding(b, q.get("kind", "debtor"))))
        if path == "/api/vouchers":
            vs = b["vouchers"]
            if q.get("base"):
                vs = [v for v in vs if v["base"] == q["base"]]
            if q.get("q"):
                s = q["q"].lower()
                vs = [v for v in vs if s in (v["party"] + " " + v["no"] + " " + v["type"] + " "
                                             + v["narration"]).lower()]
            vs = sorted(vs, key=lambda v: (v["date"], v["id"]), reverse=True)[:400]
            return self._send(200, dict(meta, vouchers=[vsummary(v) for v in vs],
                                        total=round(sum(v["total"] for v in vs), 2)))
        if path == "/api/voucher":
            v = find_voucher(b, q.get("id", ""))
            v["share"] = share_text_voucher(b, v)
            return self._send(200, dict(meta, **v))
        if path == "/api/voucher.pdf":
            v = find_voucher(b, q.get("id", ""))
            name = "%s_%s.pdf" % (slug(v["type"]), slug(v["no"] or v["date"]))
            return self._send(200, voucher_pdf(b, v), "application/pdf",
                              {"Content-Disposition": 'inline; filename="%s"' % name})
        if path == "/api/ledger.pdf":
            s = statement(b, q.get("name", ""))
            return self._send(200, statement_pdf(b, s), "application/pdf",
                              {"Content-Disposition": 'inline; filename="Ledger_%s.pdf"' % slug(s["ledger"])})
        if path == "/api/entrymeta":
            return self._send(200, dict(meta, **entry_meta(b), labels=ENTRY_LABELS))
        return self._send(404, {"error": "Not found"})


MANIFEST = json.dumps({"name": APP_NAME, "short_name": "VRI Tally", "start_url": "/",
                       "display": "standalone", "background_color": "#f4f2ff",
                       "theme_color": "#4b2bd6",
                       "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"}]})
ICON_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96"><defs><linearGradient id="g" '
            'x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4b2bd6"/><stop offset=".6" '
            'stop-color="#a020c8"/><stop offset="1" stop-color="#ff5a5f"/></linearGradient></defs>'
            '<rect width="96" height="96" rx="22" fill="url(#g)"/><text x="48" y="60" font-size="34" '
            'font-family="Arial" font-weight="700" text-anchor="middle" fill="#fff">VRI</text></svg>')

# ------------------------------- mobile web app -------------------------------
MOBILE_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#4b2bd6"><link rel="manifest" href="/manifest.json">
<link rel="icon" href="/icon.svg"><link rel="apple-touch-icon" href="/icon.svg">
<title>VRI Tally Mobile</title>
<style>
:root{--ink:#1c1640;--muted:#6b6790;--bg:#f3f1ff;--card:#fff;--line:#e6e1fb;
--indigo:#4b2bd6;--violet:#a020c8;--coral:#ff5a5f;--teal:#00b3a4;--sun:#ffad1f;--green:#14a35a;--sky:#1e90ff}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--ink);
font-size:15px;padding-bottom:calc(84px + env(safe-area-inset-bottom))}
button,input,select,textarea{font:inherit;color:inherit}
header{position:sticky;top:0;z-index:20;color:#fff;padding:calc(12px + env(safe-area-inset-top)) 16px 14px;
background:linear-gradient(115deg,var(--indigo),var(--violet) 62%,var(--coral))}
.hrow{display:flex;align-items:center;gap:10px}
.logo{width:38px;height:38px;border-radius:11px;background:rgba(255,255,255,.18);display:grid;place-items:center;
font-weight:800;font-size:13px;letter-spacing:.5px}
.co{flex:1;min-width:0}.co b{display:block;font-size:16px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.co small{opacity:.85;font-size:12px}
.hbtn{background:rgba(255,255,255,.2);border:0;color:#fff;border-radius:12px;padding:8px 11px;font-weight:600}
main{padding:14px 16px;max-width:760px;margin:0 auto}
.banner{background:#fff4e0;color:#8a5200;border:1px solid #ffd79a;border-radius:12px;padding:10px 12px;margin-bottom:12px;font-size:13px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.stat{border-radius:18px;padding:13px 14px;color:#fff;min-height:88px;display:flex;flex-direction:column;justify-content:space-between}
.stat small{opacity:.9;font-size:12px;font-weight:600;letter-spacing:.3px;text-transform:uppercase}
.stat b{font-size:19px;font-variant-numeric:tabular-nums}
.g1{background:linear-gradient(135deg,#4b2bd6,#7b5cff)}.g2{background:linear-gradient(135deg,#ff5a5f,#ff9a3c)}
.g3{background:linear-gradient(135deg,#00b3a4,#2ad38b)}.g4{background:linear-gradient(135deg,#1e90ff,#00c6ff)}
.g5{background:linear-gradient(135deg,#a020c8,#e54fa0)}.g6{background:linear-gradient(135deg,#ff8a00,#ffc93c)}
.g7{background:linear-gradient(135deg,#14a35a,#7bd94b)}.g8{background:linear-gradient(135deg,#3d3a7a,#6f6ab8)}
.card{background:var(--card);border-radius:18px;padding:14px;margin-top:14px;box-shadow:0 2px 10px rgba(60,40,160,.06)}
h3{margin:0 0 10px;font-size:15px;display:flex;justify-content:space-between;align-items:center}
h3 a{font-size:13px;color:var(--indigo);text-decoration:none;font-weight:600}
.bars{display:flex;align-items:flex-end;gap:6px;height:130px;padding-top:6px}
.bar{flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;min-width:0}
.bar i{display:block;width:100%;border-radius:7px 7px 3px 3px;background:linear-gradient(180deg,var(--coral),var(--violet))}
.bar span{font-size:10px;color:var(--muted);white-space:nowrap}
.list{display:flex;flex-direction:column}
.row{display:flex;align-items:center;gap:10px;padding:11px 2px;border-bottom:1px solid var(--line);cursor:pointer}
.row:last-child{border-bottom:0}
.av{width:36px;height:36px;border-radius:12px;display:grid;place-items:center;color:#fff;font-weight:700;font-size:13px;flex:none}
.rt{flex:1;min-width:0}.rt b{display:block;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rt small{color:var(--muted);font-size:12px}
.amt{text-align:right;font-variant-numeric:tabular-nums;font-weight:700;white-space:nowrap}
.amt small{display:block;font-weight:500;color:var(--muted);font-size:11px}
.dr{color:var(--green)}.cr{color:var(--coral)}
.search{width:100%;border:1px solid var(--line);background:#fff;border-radius:14px;padding:12px 14px;outline:none}
.search:focus,.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--indigo);box-shadow:0 0 0 3px rgba(75,43,214,.15)}
.chips{display:flex;gap:8px;overflow-x:auto;padding:10px 0 2px;scrollbar-width:none}
.chip{flex:none;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 13px;font-size:13px;font-weight:600;cursor:pointer}
.chip.on{background:var(--indigo);border-color:var(--indigo);color:#fff}
.btns{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.btn{border:0;border-radius:14px;padding:11px 14px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:6px;text-decoration:none}
.btn.p{background:var(--indigo);color:#fff}.btn.wa{background:#25d366;color:#fff}.btn.em{background:#ffe9e9;color:#c0272d}
.btn.gh{background:#eeeafe;color:var(--indigo)}.btn.full{width:100%;justify-content:center;padding:14px}
.kv{display:grid;grid-template-columns:auto 1fr;gap:6px 14px;font-size:14px}.kv span{color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:var(--muted);font-weight:600;font-size:12px;padding:6px 4px;border-bottom:1px solid var(--line)}
td{padding:8px 4px;border-bottom:1px solid var(--line);vertical-align:top}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tw{overflow-x:auto}
.field{display:flex;flex-direction:column;gap:5px;margin-bottom:12px}
.field label{font-size:12px;font-weight:700;color:var(--muted);letter-spacing:.3px;text-transform:uppercase}
.field input,.field select,.field textarea{border:1px solid var(--line);border-radius:12px;padding:11px 12px;background:#fff;outline:none;width:100%}
.two{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.preview{background:#f7f5ff;border-radius:12px;padding:10px 12px;font-size:13px}
.empty{text-align:center;color:var(--muted);padding:26px 10px}
.spin{width:28px;height:28px;border:3px solid #ddd6ff;border-top-color:var(--indigo);border-radius:50%;animation:s 1s linear infinite;margin:30px auto}
@keyframes s{to{transform:rotate(360deg)}}
nav{position:fixed;left:0;right:0;bottom:0;z-index:30;background:#fff;border-top:1px solid var(--line);
display:flex;justify-content:space-around;align-items:center;padding:6px 6px calc(8px + env(safe-area-inset-bottom))}
nav button{background:none;border:0;display:flex;flex-direction:column;align-items:center;gap:2px;font-size:11px;font-weight:600;color:var(--muted);padding:4px 8px;cursor:pointer}
nav button.on{color:var(--indigo)}
nav svg{width:22px;height:22px}
nav .fab{width:54px;height:54px;border-radius:18px;margin-top:-22px;color:#fff;background:linear-gradient(135deg,var(--coral),var(--violet));box-shadow:0 6px 16px rgba(160,32,200,.35);justify-content:center}
nav .fab svg{width:26px;height:26px}
.sheet{position:fixed;inset:0;z-index:50;background:rgba(20,10,60,.45);display:flex;align-items:flex-end}
.sheet .in{background:#fff;width:100%;border-radius:22px 22px 0 0;padding:18px 16px calc(18px + env(safe-area-inset-bottom));max-height:88vh;overflow:auto}
#toast{position:fixed;left:50%;transform:translateX(-50%);bottom:calc(96px + env(safe-area-inset-bottom));z-index:60;background:#1c1640;color:#fff;border-radius:12px;padding:11px 15px;font-size:14px;max-width:90vw}
.login{min-height:100vh;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:24px;
background:linear-gradient(150deg,var(--indigo),var(--violet) 55%,var(--coral));color:#fff;text-align:center}
.login .box{background:rgba(255,255,255,.14);border-radius:24px;padding:24px 20px;width:100%;max-width:340px}
.login input{width:100%;text-align:center;font-size:28px;letter-spacing:10px;border:0;border-radius:14px;padding:12px;margin:14px 0;color:var(--ink)}
.login .btn{background:#fff;color:var(--indigo)}
.err{color:#ffe1e1;min-height:20px;font-size:14px}
:focus-visible{outline:3px solid var(--sun);outline-offset:2px}
@media (prefers-reduced-motion:reduce){.spin{animation:none}}
</style></head><body>
<div id="app"></div><div id="toast" hidden></div>
<script>
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function store(k,v){try{if(v===undefined)return localStorage.getItem(k)||'';localStorage.setItem(k,v)}catch(e){return ''}}
const S={token:store('vri_t'),company:store('vri_c'),from:store('vri_f'),to:store('vri_to'),view:'home',stack:[]};
function inr(v){v=Number(v||0);const n=v<0;v=Math.abs(v);let [w,f]=v.toFixed(2).split('.');
 if(w.length>3){let h=w.slice(0,-3),t=w.slice(-3),p=[];while(h.length>2){p.unshift(h.slice(-2));h=h.slice(0,-2)}if(h)p.unshift(h);w=p.join(',')+','+t}
 return (n?'-':'')+'\u20b9'+w+'.'+f}
function drcr(v){v=Number(v||0);if(Math.abs(v)<.005)return inr(0);return inr(Math.abs(v))+(v>0?' Dr':' Cr')}
function d8(s){if(!s||s.length<8)return s||'';const m=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];return s.slice(6,8)+' '+m[+s.slice(4,6)-1]+' '+s.slice(2,4)}
function iso(s){return s?s.slice(0,4)+'-'+s.slice(4,6)+'-'+s.slice(6,8):''}
function toast(m){const t=$('#toast');t.textContent=m;t.hidden=false;clearTimeout(t._h);t._h=setTimeout(()=>t.hidden=true,3600)}
const COLORS=['#4b2bd6','#ff5a5f','#00b3a4','#1e90ff','#a020c8','#ff8a00','#14a35a','#e54fa0'];
function av(name){let h=0;for(const c of name||'')h=(h*31+c.charCodeAt(0))>>>0;const ini=(name||'?').replace(/[^A-Za-z0-9 ]/g,'').split(' ').filter(Boolean).slice(0,2).map(w=>w[0]).join('').toUpperCase()||'?';
 return `<div class="av" style="background:${COLORS[h%COLORS.length]}">${esc(ini)}</div>`}
function qs(extra){const p=new URLSearchParams({c:S.company});if(S.from)p.set('from',S.from);if(S.to)p.set('to',S.to);for(const k in extra||{})if(extra[k]!=null&&extra[k]!=='')p.set(k,extra[k]);return p.toString()}
async function api(path,opt={}){
 const h={'Authorization':'Bearer '+S.token};if(opt.body)h['Content-Type']='application/json';
 const r=await fetch(path,{method:opt.body?'POST':'GET',headers:h,body:opt.body?JSON.stringify(opt.body):undefined});
 if(r.status===401){S.token='';store('vri_t','');renderLogin();throw new Error('Please log in again.')}
 if(opt.raw){if(!r.ok){let e='Could not create the file.';try{e=(await r.json()).error||e}catch(x){}throw new Error(e)}return r}
 let j={};try{j=await r.json()}catch(e){} if(!r.ok)throw new Error(j.error||'Request failed');return j}
const IC={home:'<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
book:'<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/>',
plus:'<path d="M12 5v14M5 12h14"/>',
doc:'<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>',
due:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'};
const svg=n=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${IC[n]}</svg>`;

function renderLogin(msg){
 document.body.style.paddingBottom='0';
 $('#app').innerHTML=`<div class="login"><div class="box"><div class="logo" style="margin:0 auto 10px;width:56px;height:56px;font-size:17px">VRI</div>
 <h2 style="margin:4px 0">VRI Tally Mobile</h2><div style="opacity:.85;font-size:14px">Enter the 6-digit PIN shown in the desktop app</div>
 <form id="lf"><input id="pin" inputmode="numeric" autocomplete="one-time-code" maxlength="6" pattern="[0-9]*" aria-label="PIN">
 <div class="err" id="lerr">${esc(msg||'')}</div><button class="btn full" type="submit">Unlock</button></form></div>
 <p style="opacity:.75;font-size:12px;margin-top:18px">VRI Group &middot; Finance. Wealth. Technology.</p></div>`;
 $('#pin').focus();
 $('#lf').onsubmit=async e=>{e.preventDefault();$('#lerr').textContent='';
  try{const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin:$('#pin').value})});
   const j=await r.json();if(!r.ok)throw new Error(j.error||'Wrong PIN');S.token=j.token;store('vri_t',j.token);boot()}
  catch(x){$('#lerr').textContent=x.message}}}

function shell(){
 document.body.style.paddingBottom='';
 $('#app').innerHTML=`<header><div class="hrow"><div class="logo">VRI</div><div class="co"><b id="coName">${esc(S.company||'Choose company')}</b><small id="per"></small></div>
 <button class="hbtn" id="refresh" aria-label="Refresh from Tally">&#8635;</button><button class="hbtn" id="opts">Change</button></div></header>
 <main id="main"></main>
 <nav>${[['home','Home','home'],['ledgers','Ledgers','book'],['entry','','plus'],['vouchers','Vouchers','doc'],['dues','Dues','due']]
 .map(([v,l,i])=>`<button data-v="${v}" class="${v==='entry'?'fab':''}" aria-label="${l||'New voucher'}">${svg(i)}${l?`<span>${l}</span>`:''}</button>`).join('')}</nav>`;
 document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>go(b.dataset.v));
 $('#opts').onclick=openOptions;$('#refresh').onclick=()=>{S.force=true;go(S.view,S.arg,true);toast('Refreshing from Tally...')};
}
function setPer(j){if(!j)return;$('#per').textContent=d8(j.from)+' to '+d8(j.to)+' \u00b7 synced '+String(j.fetched||'').slice(-8)}
function loading(){$('#main').innerHTML='<div class="spin" role="status" aria-label="Loading"></div>'}
function off(j){return j&&j.offline?`<div class="banner">Tally is not reachable right now. Showing data saved on ${esc(j.fetched)}.<br><small>${esc(j.offline)}</small></div>`:''}
function fail(e){$('#main').innerHTML=`<div class="card empty"><b>Could not load</b><p>${esc(e.message)}</p><button class="btn p" onclick="go(S.view,S.arg,true)">Try again</button></div>`}
async function go(view,arg,keep){
 S.view=view;S.arg=arg;document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('on',b.dataset.v===view));
 if(!S.company){openOptions();return}
 loading();window.scrollTo(0,0);const f=S.force?{force:'1'}:{};S.force=false;
 try{await VIEWS[view](arg,f)}catch(e){if(e.message!=='Please log in again.')fail(e)}}

const VIEWS={
async home(a,f){const j=await api('/api/dashboard?'+qs(f));setPer(j);
 const cards=[['Sales','sales','g1'],['Purchases','purchase','g2'],['Receipts','receipt','g3'],['Payments','payment','g4'],
 ['Receivable','receivable','g5'],['Payable','payable','g6'],['Cash','cash','g7'],['Bank','bank','g8']];
 const mx=Math.max(1,...j.monthly.map(m=>m.sales));
 $('#main').innerHTML=off(j)+`<div class="grid">${cards.map(([l,k,g])=>`<div class="stat ${g}"><small>${l}</small><b>${inr(j[k])}</b></div>`).join('')}</div>
 <div class="card"><h3>Sales by month</h3>${j.monthly.length?`<div class="bars">${j.monthly.map(m=>`<div class="bar" title="${esc(m.label)}: ${inr(m.sales)}"><i style="height:${Math.max(3,m.sales/mx*100)}px"></i><span>${esc(m.label)}</span></div>`).join('')}</div>`:'<div class="empty">No sales in this period</div>'}</div>
 <div class="card"><h3>Top receivables <a href="#" onclick="go('dues');return false">All dues</a></h3><div class="list">${j.top_debtors.map(p=>`<div class="row" data-l="${esc(p.name)}">${av(p.name)}<div class="rt"><b>${esc(p.name)}</b><small>${esc(p.mobile||'')}</small></div><div class="amt dr">${inr(p.balance)}</div></div>`).join('')||'<div class="empty">No dues</div>'}</div></div>
 <div class="card"><h3>Recent vouchers <a href="#" onclick="go('vouchers');return false">View all</a></h3><div class="list">${vrows(j.recent)}</div></div>`;
 bindRows()},
async ledgers(a,f){const j=await api('/api/ledgers?'+qs(f));setPer(j);S.led=j.ledgers;
 const kinds=[['','All'],['debtor','Debtors'],['creditor','Creditors'],['cash','Cash'],['bank','Bank'],['sales','Sales'],['purchase','Purchase'],['expense','Expenses'],['income','Income'],['tax','Taxes']];
 S.lk=S.lk||'';$('#main').innerHTML=off(j)+`<input class="search" id="ls" placeholder="Search ledgers" aria-label="Search ledgers" value="${esc(S.ls||'')}">
 <div class="chips">${kinds.map(([k,l])=>`<button class="chip ${S.lk===k?'on':''}" data-k="${k}">${l}</button>`).join('')}</div><div class="card"><div class="list" id="ll"></div></div>`;
 const draw=()=>{const s=($('#ls').value||'').toLowerCase();S.ls=$('#ls').value;
  const rows=S.led.filter(l=>(!S.lk||l.kind===S.lk)&&(!s||l.name.toLowerCase().includes(s))).slice(0,300);
  $('#ll').innerHTML=rows.map(l=>`<div class="row" data-l="${esc(l.name)}">${av(l.name)}<div class="rt"><b>${esc(l.name)}</b><small>${esc(l.group)}</small></div><div class="amt ${l.balance>=0?'dr':'cr'}">${drcr(l.balance)}</div></div>`).join('')||'<div class="empty">No ledgers match</div>';bindRows()};
 $('#ls').oninput=draw;document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{S.lk=c.dataset.k;document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('on',x===c));draw()});draw()},
async ledger(name,f){const j=await api('/api/ledger?'+qs(Object.assign({name},f)));setPer(j);
 $('#main').innerHTML=off(j)+`<button class="btn gh" onclick="go('ledgers')">&larr; Ledgers</button>
 <div class="card"><h3>${esc(j.ledger)}</h3><div class="kv"><span>Group</span><b>${esc(j.group)}</b><span>Opening</span><b>${drcr(j.opening)}</b>
 <span>Debits</span><b>${inr(j.total_dr)}</b><span>Credits</span><b>${inr(j.total_cr)}</b><span>Closing</span><b class="${j.closing>=0?'dr':'cr'}">${drcr(j.closing)}</b>
 ${j.mobile?`<span>Mobile</span><b>${esc(j.mobile)}</b>`:''}${j.email?`<span>Email</span><b>${esc(j.email)}</b>`:''}${j.gstin?`<span>GSTIN</span><b>${esc(j.gstin)}</b>`:''}</div>
 ${shareBtns('/api/ledger.pdf?'+qs({name}),'Ledger_'+j.ledger+'.pdf',j.mobile,j.email,j.share,'Ledger statement - '+j.ledger)}</div>
 <div class="card"><h3>Transactions <small style="color:var(--muted);font-weight:500">${j.rows.length}</small></h3><div class="tw"><table><thead><tr><th>Date</th><th>Particulars</th><th class="n">Debit</th><th class="n">Credit</th><th class="n">Balance</th></tr></thead><tbody>
 ${j.rows.slice().reverse().map(r=>`<tr data-v="${esc(r.vid)}" style="cursor:pointer"><td>${d8(r.date)}</td><td>${esc(r.particulars)}<br><small style="color:var(--muted)">${esc(r.type)} ${esc(r.no)}</small></td><td class="n">${r.dr?inr(r.dr):''}</td><td class="n">${r.cr?inr(r.cr):''}</td><td class="n">${drcr(r.balance)}</td></tr>`).join('')||'<tr><td colspan="5" class="empty">No transactions in this period</td></tr>'}</tbody></table></div></div>`;
 bindShare();document.querySelectorAll('tr[data-v]').forEach(t=>t.onclick=()=>go('voucher',t.dataset.v))},
async vouchers(a,f){S.vb=S.vb||'';const j=await api('/api/vouchers?'+qs(Object.assign({base:S.vb,q:S.vq||''},f)));setPer(j);
 const t=['','Sales','Purchase','Receipt','Payment','Journal','Contra','Credit Note','Debit Note'];
 $('#main').innerHTML=off(j)+`<form id="vf"><input class="search" id="vq" placeholder="Search party, number, narration" aria-label="Search vouchers" value="${esc(S.vq||'')}"></form>
 <div class="chips">${t.map(k=>`<button class="chip ${S.vb===k?'on':''}" data-k="${k}">${k||'All'}</button>`).join('')}</div>
 <div class="card"><h3>${j.vouchers.length} vouchers <span style="font-variant-numeric:tabular-nums">${inr(j.total)}</span></h3><div class="list">${vrows(j.vouchers)}</div></div>`;
 $('#vf').onsubmit=e=>{e.preventDefault();S.vq=$('#vq').value;go('vouchers')};
 document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{S.vb=c.dataset.k;go('vouchers')});bindRows()},
async voucher(id,f){const j=await api('/api/voucher?'+qs(Object.assign({id},f)));setPer(j);const pi=j.party_info||{};
 $('#main').innerHTML=off(j)+`<button class="btn gh" onclick="history.length&&S.stack.length?go(...S.stack.pop()):go('vouchers')">&larr; Back</button>
 <div class="card"><h3>${esc(j.type)} <span>${inr(j.total)}</span></h3><div class="kv"><span>No.</span><b>${esc(j.no||'-')}</b><span>Date</span><b>${d8(j.date)}</b>
 ${j.party?`<span>Party</span><b>${esc(j.party)}</b>`:''}${pi.gstin?`<span>GSTIN</span><b>${esc(pi.gstin)}</b>`:''}${j.ref?`<span>Ref</span><b>${esc(j.ref)}</b>`:''}</div>
 ${shareBtns('/api/voucher.pdf?'+qs({id}),(j.type+'_'+(j.no||j.date)).replace(/[^A-Za-z0-9]+/g,'_')+'.pdf',pi.mobile,pi.email,j.share,j.type+' '+(j.no||''))}</div>
 ${j.items.length?`<div class="card"><h3>Items</h3><div class="tw"><table><thead><tr><th>Item</th><th class="n">Qty</th><th class="n">Rate</th><th class="n">Amount</th></tr></thead><tbody>${j.items.map(i=>`<tr><td>${esc(i.item)}</td><td class="n">${i.qty} ${esc(i.unit)}</td><td class="n">${inr(i.rate)}</td><td class="n">${inr(i.amount)}</td></tr>`).join('')}</tbody></table></div></div>`:''}
 <div class="card"><h3>Accounts</h3><div class="tw"><table><thead><tr><th>Ledger</th><th class="n">Debit</th><th class="n">Credit</th></tr></thead><tbody>${j.entries.map(e=>`<tr><td>${esc(e.ledger)}</td><td class="n">${e.amount>0?inr(e.amount):''}</td><td class="n">${e.amount<0?inr(-e.amount):''}</td></tr>`).join('')}</tbody></table></div>
 ${j.narration?`<p style="color:var(--muted);font-size:13px;margin:10px 0 0">${esc(j.narration)}</p>`:''}</div>`;bindShare()},
async dues(a,f){S.dk=S.dk||'debtor';const j=await api('/api/outstanding?'+qs(Object.assign({kind:S.dk},f)));setPer(j);
 $('#main').innerHTML=off(j)+`<div class="chips"><button class="chip ${S.dk==='debtor'?'on':''}" data-k="debtor">Receivables</button><button class="chip ${S.dk==='creditor'?'on':''}" data-k="creditor">Payables</button></div>
 <div class="stat ${S.dk==='debtor'?'g5':'g6'}" style="margin-top:10px"><small>Total ${S.dk==='debtor'?'receivable':'payable'}</small><b>${inr(j.total)}</b></div>
 ${j.billwise?`<div class="grid" style="grid-template-columns:repeat(4,1fr);margin-top:10px">${Object.entries(j.buckets).map(([k,v])=>`<div class="card" style="margin:0;padding:10px"><small style="color:var(--muted)">${k} days</small><br><b style="font-size:13px">${inr(v)}</b></div>`).join('')}</div>`:''}
 <div class="card"><div class="list">${j.parties.map(p=>`<div class="row" data-l="${esc(p.name)}">${av(p.name)}<div class="rt"><b>${esc(p.name)}</b><small>${p.bills.length?p.bills.length+' bills \u00b7 oldest '+p.bills[0].age+' days':esc(p.mobile||'')}</small></div><div class="amt ${p.balance>=0?'dr':'cr'}">${inr(p.balance)}</div></div>`).join('')||'<div class="empty">Nothing outstanding</div>'}</div></div>`;
 document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{S.dk=c.dataset.k;go('dues')});bindRows()},
async entry(a,f){const j=await api('/api/entrymeta?'+qs(f));setPer(j);S.meta=j;
 const today=new Date();const td=today.getFullYear()+'-'+String(today.getMonth()+1).padStart(2,'0')+'-'+String(today.getDate()).padStart(2,'0');
 $('#main').innerHTML=off(j)+`<div class="card"><h3>New voucher</h3><form id="ef">
 <div class="two"><div class="field"><label for="et">Voucher type</label><select id="et">${j.types.map(t=>`<option value="${esc(t.name)}" data-b="${esc(t.base)}">${esc(t.name)}</option>`).join('')}</select></div>
 <div class="field"><label for="ed">Date</label><input type="date" id="ed" value="${td}"></div></div>
 <div class="field"><label for="ea" id="la">Party</label><input id="ea" list="dl_a" autocomplete="off"></div>
 <div class="field"><label for="eb" id="lb">Account</label><input id="eb" list="dl_b" autocomplete="off"></div>
 <div class="two"><div class="field"><label for="eamt" id="lamt">Amount</label><input id="eamt" inputmode="decimal" placeholder="0.00"></div>
 <div class="field"><label for="eref">Ref / bill no.</label><input id="eref"></div></div>
 <div id="gst"><div class="two"><div class="field"><label for="er">GST rate</label><select id="er">${[0,5,12,18,28].map(r=>`<option value="${r}">${r}%</option>`).join('')}</select></div>
 <div class="field"><label for="em">Supply</label><select id="em"><option value="intra">Within state (CGST+SGST)</option><option value="inter">Other state (IGST)</option></select></div></div>
 <div id="gl" class="two"></div></div>
 <div class="field"><label for="en">Narration</label><textarea id="en" rows="2"></textarea></div>
 <div class="preview" id="pv"></div><button class="btn p full" style="margin-top:12px" id="epost" type="submit">Post to Tally</button></form></div>
 <datalist id="dl_a"></datalist><datalist id="dl_b"></datalist><datalist id="dl_t">${j.tax.all.map(t=>`<option value="${esc(t)}">`).join('')}</datalist>`;
 const L=j.ledgers,byK=k=>L.filter(l=>k.includes(l.kind)),opts=a=>a.map(l=>`<option value="${esc(l.name)}">`).join('');
 const sync=()=>{const base=$('#et').selectedOptions[0]?.dataset.b||'';const lab=j.labels[base]||['Ledger','Ledger'];
  $('#la').textContent=lab[0];$('#lb').textContent=lab[1];$('#gst').hidden=!['Sales','Purchase','Credit Note','Debit Note'].includes(base);
  const A={Sales:['debtor'],'Credit Note':['debtor'],Purchase:['creditor'],'Debit Note':['creditor'],Receipt:['debtor','creditor','income','other'],Payment:['creditor','expense','debtor','other'],Contra:['cash','bank'],Journal:null}[base];
  const B={Sales:['sales'],'Credit Note':['sales'],Purchase:['purchase','expense'],'Debit Note':['purchase'],Receipt:['cash','bank'],Payment:['cash','bank'],Contra:['cash','bank'],Journal:null}[base];
  $('#dl_a').innerHTML=opts(A?byK(A):L);$('#dl_b').innerHTML=opts(B?byK(B):L);
  $('#lamt').textContent=$('#gst').hidden?'Amount':'Taxable value';
  const inter=$('#em').value==='inter';$('#gl').innerHTML=inter?`<div class="field"><label for="eig">IGST ledger</label><input id="eig" list="dl_t" value="${esc(j.tax.igst)}"></div>`
   :`<div class="field"><label for="ecg">CGST ledger</label><input id="ecg" list="dl_t" value="${esc(j.tax.cgst)}"></div><div class="field"><label for="esg">SGST ledger</label><input id="esg" list="dl_t" value="${esc(j.tax.sgst)}"></div>`;
  $('#gl').hidden=$('#er').value==='0';pv()};
 const pv=()=>{const base=$('#et').selectedOptions[0]?.dataset.b||'';const amt=parseFloat(($('#eamt').value||'').replace(/,/g,''))||0;
  const g=$('#gst').hidden?0:(+$('#er').value||0);const tax=Math.round(amt*g)/100;
  $('#pv').innerHTML=amt?`<b>${esc(base)}</b> &middot; ${g?`Taxable ${inr(amt)} + GST ${inr(tax)} = `:''}<b>${inr(amt+tax)}</b>`:'Enter an amount to see the total.'};
 $('#et').onchange=sync;$('#em').onchange=sync;$('#er').onchange=()=>{$('#gl').hidden=$('#er').value==='0';pv()};$('#eamt').oninput=pv;sync();
 $('#ef').onsubmit=async e=>{e.preventDefault();const btn=$('#epost');if(btn.disabled)return;
  const body={c:S.company,vtype:$('#et').value,date:$('#ed').value,party:$('#ea').value,account:$('#eb').value,amount:$('#eamt').value,ref:$('#eref').value,narration:$('#en').value,
   gst_rate:$('#gst').hidden?0:$('#er').value,gst_mode:$('#em').value,cgst:$('#ecg')?.value||'',sgst:$('#esg')?.value||'',igst:$('#eig')?.value||''};
  btn.disabled=true;btn.textContent='Posting...';
  try{await api('/api/entry',{body});toast('Posted to Tally.');S.force=true;go('vouchers')}
  catch(x){toast(x.message);btn.disabled=false;btn.textContent='Post to Tally'}}},
};
function vrows(list){return (list||[]).map(v=>`<div class="row" data-v="${esc(v.id)}">${av(v.base||v.type)}<div class="rt"><b>${esc(v.party||v.type)}</b><small>${esc(v.type)} ${esc(v.no||'')} &middot; ${d8(v.date)}</small></div><div class="amt">${inr(v.total)}</div></div>`).join('')||'<div class="empty">No vouchers</div>'}
function bindRows(){document.querySelectorAll('.row[data-v]').forEach(r=>r.onclick=()=>{S.stack.push([S.view,S.arg]);go('voucher',r.dataset.v)});
 document.querySelectorAll('.row[data-l]').forEach(r=>r.onclick=()=>go('ledger',r.dataset.l))}
function shareBtns(url,fname,mobile,email,text,subject){S.share={url,fname,mobile,email,text,subject};
 const d=(mobile||'').replace(/\D/g,'');const wa='https://wa.me/'+(d.length===10?'91'+d:d)+'?text='+encodeURIComponent(text||'');
 const ml='mailto:'+encodeURIComponent(email||'')+'?subject='+encodeURIComponent(subject||'')+'&body='+encodeURIComponent(text||'');
 return `<div class="btns"><button class="btn p" id="sPdf">Share PDF</button><a class="btn wa" href="${wa}" target="_blank" rel="noopener">WhatsApp</a><a class="btn em" href="${ml}">Email</a>${d?`<a class="btn gh" href="tel:${esc(d)}">Call</a>`:''}</div>
 <p style="font-size:12px;color:var(--muted);margin:8px 0 0">Share PDF opens your phone's share sheet (WhatsApp, Gmail...). If it can't, the PDF downloads; attach it in the chat or email.</p>`}
function bindShare(){const b=$('#sPdf');if(!b)return;b.onclick=async()=>{const s=S.share;b.disabled=true;b.textContent='Preparing...';
 try{const r=await api(s.url,{raw:true});const blob=await r.blob();const file=new File([blob],s.fname,{type:'application/pdf'});
  if(navigator.canShare&&navigator.canShare({files:[file]})){try{await navigator.share({files:[file],title:s.subject,text:s.text})}catch(e){if(e.name!=='AbortError')throw e}}
  else{const u=URL.createObjectURL(blob);const a=document.createElement('a');a.href=u;a.download=s.fname;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),60000);
   toast('PDF downloaded. Attach it in WhatsApp or email.')}}
 catch(e){toast(e.message)}finally{b.disabled=false;b.textContent='Share PDF'}}}
async function openOptions(){
 const sh=document.createElement('div');sh.className='sheet';sh.innerHTML=`<div class="in"><h3>Company &amp; period</h3><div class="spin"></div></div>`;document.body.appendChild(sh);
 sh.onclick=e=>{if(e.target===sh&&S.company)sh.remove()};
 try{const j=await api('/api/companies');if(!S.company&&j.default)S.company=j.default;
  const f=S.from||'',t=S.to||'';
  sh.querySelector('.in').innerHTML=`<h3>Company &amp; period</h3><form id="of"><div class="field"><label for="oc">Company (open in TallyPrime)</label><select id="oc">${j.companies.map(c=>`<option ${c===S.company?'selected':''}>${esc(c)}</option>`).join('')}</select></div>
  <div class="two"><div class="field"><label for="of1">From</label><input type="date" id="of1" value="${iso(f)}"></div><div class="field"><label for="ot">To</label><input type="date" id="ot" value="${iso(t)}"></div></div>
  <p style="font-size:12px;color:var(--muted);margin-top:-4px">Leave dates empty for this financial year to date.</p>
  <button class="btn p full" type="submit">Apply</button><div class="btns"><button class="btn gh" type="button" id="olo">Log out</button>${S.company?'<button class="btn gh" type="button" id="ocl">Close</button>':''}</div></form>`;
  if(!j.companies.length)sh.querySelector('.in').insertAdjacentHTML('afterbegin','<div class="banner">No company is open in TallyPrime. Load a company on the PC and try again.</div>');
  $('#of').onsubmit=e=>{e.preventDefault();S.company=$('#oc').value;S.from=($('#of1').value||'').replace(/-/g,'');S.to=($('#ot').value||'').replace(/-/g,'');
   store('vri_c',S.company);store('vri_f',S.from);store('vri_to',S.to);$('#coName').textContent=S.company;sh.remove();go(S.view==='voucher'||S.view==='ledger'?'home':S.view)};
  $('#olo').onclick=()=>{S.token='';store('vri_t','');sh.remove();renderLogin()};if($('#ocl'))$('#ocl').onclick=()=>sh.remove()}
 catch(e){sh.querySelector('.in').innerHTML=`<h3>Company &amp; period</h3><div class="banner">${esc(e.message)}</div><button class="btn p full" onclick="this.closest('.sheet').remove();openOptions()">Try again</button>`}}
function boot(){if(!S.token){renderLogin();return}shell();if(!S.company){openOptions();return}go('home')}
boot();
</script></body></html>'''


# =============================================================================
# 8. DESKTOP APP (PyQt5)
# =============================================================================
from PyQt5.QtCore import (Qt, QObject, QRunnable, QThreadPool, pyqtSignal, QDate, QUrl, QTimer)
from PyQt5.QtGui import QPixmap, QColor, QDesktopServices, QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QStackedWidget, QComboBox, QDateEdit, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSplitter, QFormLayout, QDoubleSpinBox, QTextEdit, QMessageBox,
    QSpinBox, QCompleter, QSizePolicy, QFileDialog, QButtonGroup, QScrollArea)

QSS = """
* { font-family: 'Segoe UI', Arial; font-size: 10pt; color: #1c1640; }
QMainWindow, #Body { background: #f3f1ff; }
#PageBody, #PageScroll { background: transparent; border: none; }
#Side { background: qlineargradient(x1:0, y1:0, x2:0.3, y2:1, stop:0 #3a1fb8, stop:0.55 #8e1fc4, stop:1 #ff5a5f); }
#Side QLabel { color: white; }
#Brand { font-size: 17pt; font-weight: 800; color: white; }
#BrandSub { color: rgba(255,255,255,0.82); font-size: 8.5pt; }
#Side QPushButton { background: transparent; color: white; border: none; text-align: left;
    padding: 11px 16px; border-radius: 12px; font-size: 10.5pt; font-weight: 600; }
#Side QPushButton:hover { background: rgba(255,255,255,0.14); }
#Side QPushButton:checked { background: white; color: #4b2bd6; }
#Top { background: white; border-radius: 16px; }
#PageTitle { font-size: 16pt; font-weight: 800; color: #1c1640; }
#Muted { color: #6b6790; }
#Card { background: white; border-radius: 16px; }
#CardTitle { font-size: 11pt; font-weight: 700; }
QPushButton { background: #4b2bd6; color: white; border: none; border-radius: 10px; padding: 8px 15px; font-weight: 700; }
QPushButton:hover { background: #5d3ff0; }
QPushButton:disabled { background: #c9c2f2; color: white; }
QPushButton#Ghost { background: #eeeafe; color: #4b2bd6; }
QPushButton#Ghost:hover { background: #e2dcff; }
QPushButton#Wa { background: #1fb954; } QPushButton#Wa:hover { background: #25d366; }
QPushButton#Em { background: #ff5a5f; } QPushButton#Em:hover { background: #ff7175; }
QPushButton#Warm { background: #ff8a00; } QPushButton#Warm:hover { background: #ffa12e; }
QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox, QTextEdit {
    background: white; border: 1px solid #ddd6fb; border-radius: 9px; padding: 6px 9px; }
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus, QTextEdit:focus { border: 2px solid #4b2bd6; }
QComboBox::drop-down, QDateEdit::drop-down { border: none; width: 22px; }
QTableWidget { background: white; border: none; border-radius: 12px; gridline-color: #f0edfd;
    alternate-background-color: #faf9ff; selection-background-color: #e4ddff; selection-color: #1c1640; }
QHeaderView::section { background: #4b2bd6; color: white; padding: 7px; border: none; font-weight: 700; }
QTableCornerButton::section { background: #4b2bd6; border: none; }
QScrollBar:vertical { background: transparent; width: 10px; } QScrollBar::handle:vertical { background: #cfc6fb; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
#Pill { border-radius: 10px; padding: 4px 10px; font-weight: 700; font-size: 9pt; }
"""

CARD_GRADS = [("#4b2bd6", "#7b5cff"), ("#ff5a5f", "#ff9a3c"), ("#00b3a4", "#2ad38b"),
              ("#1e90ff", "#00c6ff"), ("#a020c8", "#e54fa0"), ("#ff8a00", "#ffc93c"),
              ("#14a35a", "#7bd94b"), ("#3d3a7a", "#6f6ab8")]


class _Sig(QObject):
    done = pyqtSignal(object)
    fail = pyqtSignal(str)


class Job(QRunnable):
    def __init__(self, fn, *a, **k):
        super().__init__()
        self.fn, self.a, self.k = fn, a, k
        self.sig = _Sig()

    def run(self):
        try:
            res = self.fn(*self.a, **self.k)
        except Exception as e:  # noqa
            self.sig.fail.emit(str(e))
            return
        self.sig.done.emit(res)


def card(parent=None):
    f = QFrame(parent)
    f.setObjectName("Card")
    return f


def btn(text, kind="", tip=""):
    b = QPushButton(text)
    if kind:
        b.setObjectName(kind)
    if tip:
        b.setToolTip(tip)
    b.setCursor(Qt.PointingHandCursor)
    return b


def make_table(headers, numeric=()):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    t.setShowGrid(False)
    h = t.horizontalHeader()
    h.setSectionResizeMode(QHeaderView.Interactive)
    h.setStretchLastSection(False)
    t._numeric = set(numeric)
    t.setMinimumHeight(170)
    return t


def fill_table(t, rows, keys=None, stretch=1, colors_fn=None):
    t.setSortingEnabled(False)
    t.setRowCount(len(rows))
    for r, row in enumerate(rows):
        vals = row["cells"] if isinstance(row, dict) else row
        for c, val in enumerate(vals):
            it = QTableWidgetItem(str(val))
            if c in t._numeric:
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if colors_fn:
                col = colors_fn(r, c)
                if col:
                    it.setForeground(QColor(col))
            if isinstance(row, dict) and c == 0:
                it.setData(Qt.UserRole, row.get("key"))
            t.setItem(r, c, it)
    t.resizeColumnsToContents()
    t.horizontalHeader().setSectionResizeMode(stretch, QHeaderView.Stretch)


def selected_key(t):
    r = t.currentRow()
    if r < 0:
        return None
    it = t.item(r, 0)
    return it.data(Qt.UserRole) if it else None


def qr_pixmap(text, size=200):
    import qrcode
    img = qrcode.make(text, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    pm = QPixmap()
    pm.loadFromData(buf.getvalue(), "PNG")
    return pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class StatCard(QFrame):
    def __init__(self, title, grad):
        super().__init__()
        self.setStyleSheet("QFrame{border-radius:16px;background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                           "stop:0 %s, stop:1 %s);} QLabel{color:white;background:transparent;}" % grad)
        self.setMinimumHeight(92)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        t = QLabel(title.upper())
        t.setStyleSheet("font-size:8.5pt;font-weight:700;letter-spacing:1px;color:rgba(255,255,255,0.88);")
        self.val = QLabel("-")
        self.val.setStyleSheet("font-size:16pt;font-weight:800;")
        self.sub = QLabel("")
        self.sub.setStyleSheet("font-size:8.5pt;color:rgba(255,255,255,0.85);")
        lay.addWidget(t)
        lay.addWidget(self.val)
        lay.addWidget(self.sub)

    def set(self, value, sub=""):
        self.val.setText(value)
        self.sub.setText(sub)


class BarChart(QWidget):
    def __init__(self):
        super().__init__()
        self.data = []
        self.setMinimumHeight(170)

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, e):
        from PyQt5.QtGui import QPainter, QLinearGradient, QBrush
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if not self.data:
            p.setPen(QColor("#6b6790"))
            p.drawText(self.rect(), Qt.AlignCenter, "No sales or purchases in this period")
            return
        mx = max([1] + [max(d["sales"], d["purchase"]) for d in self.data])
        n = len(self.data)
        slot = (w - 20) / n
        bw = max(4, min(18, slot / 3))
        base = h - 24
        for i, d in enumerate(self.data):
            x = 10 + i * slot + slot / 2
            for j, (key, c1, c2) in enumerate((("sales", "#ff5a5f", "#a020c8"),
                                               ("purchase", "#00c6ff", "#1e90ff"))):
                bh = (base - 10) * d[key] / mx
                gx = x - bw - 1 + j * (bw + 2)
                g = QLinearGradient(0, base - bh, 0, base)
                g.setColorAt(0, QColor(c1))
                g.setColorAt(1, QColor(c2))
                p.setBrush(QBrush(g))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(int(gx), int(base - bh), int(bw), int(max(2, bh)), 4, 4)
            p.setPen(QColor("#6b6790"))
            p.drawText(int(x - slot / 2), base + 4, int(slot), 18, Qt.AlignCenter, d["label"])


class MainWindow(QMainWindow):
    def __init__(self, cfg, svc, server):
        super().__init__()
        self.cfg, self.svc, self.server = cfg, svc, server
        self.pool = QThreadPool.globalInstance()
        self.jobs = set()
        self.bundle = None
        self.setWindowTitle("%s  |  VRI Group" % APP_NAME)
        self.setMinimumSize(760, 480)
        scr = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1280, int(scr.width() * 0.95)), min(800, int(scr.height() * 0.92)))

        root = QWidget()
        root.setObjectName("Body")
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        # ---- sidebar ----
        side = QFrame()
        side.setObjectName("Side")
        side.setFixedWidth(190)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(14, 22, 14, 18)
        sv.setSpacing(4)
        brand = QLabel("VRI Tally")
        brand.setObjectName("Brand")
        sub = QLabel("Mobile  \u2022  VRI Group")
        sub.setObjectName("BrandSub")
        sv.addWidget(brand)
        sv.addWidget(sub)
        sv.addSpacing(18)
        self.nav = QButtonGroup(self)
        self.stack = QStackedWidget()
        pages = [("Dashboard", self.page_dashboard), ("Ledgers", self.page_ledgers),
                 ("Vouchers", self.page_vouchers), ("Outstanding", self.page_outstanding),
                 ("New Voucher", self.page_entry), ("Mobile Access", self.page_mobile),
                 ("Settings", self.page_settings)]
        for i, (name, builder) in enumerate(pages):
            b = QPushButton("   " + name)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            self.nav.addButton(b, i)
            sv.addWidget(b)
            self.stack.addWidget(self._scroll(builder()))
        self.nav.button(0).setChecked(True)
        self.nav.buttonClicked[int].connect(self.stack.setCurrentIndex)
        sv.addStretch(1)
        tag = QLabel("Finance. Wealth. Technology.\nOne Trusted Relationship.")
        tag.setObjectName("BrandSub")
        tag.setWordWrap(True)
        sv.addWidget(tag)
        h.addWidget(side)

        # ---- main column ----
        body = QVBoxLayout()
        body.setContentsMargins(18, 16, 18, 16)
        body.setSpacing(12)
        top = QFrame()
        top.setObjectName("Top")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(14, 10, 14, 10)
        tl.addWidget(QLabel("Company"))
        self.co = QComboBox()
        self.co.setMinimumWidth(150)
        self.co.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        tl.addWidget(self.co, 1)
        tl.addSpacing(10)
        tl.addWidget(QLabel("From"))
        fs, td = fy_start(), date.today()
        self.dfrom = QDateEdit(QDate(fs.year, fs.month, fs.day))
        self.dto = QDateEdit(QDate(td.year, td.month, td.day))
        for d in (self.dfrom, self.dto):
            d.setCalendarPopup(True)
            d.setDisplayFormat("dd-MMM-yyyy")
        tl.addWidget(self.dfrom)
        tl.addWidget(QLabel("To"))
        tl.addWidget(self.dto)
        self.btn_load = btn("Load from Tally")
        self.btn_load.clicked.connect(lambda: self.load(force=True))
        self.btn_load.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        tl.addWidget(self.btn_load)
        self.pill = QLabel("Not connected")
        self.pill.setObjectName("Pill")
        tl.addWidget(self.pill)
        body.addWidget(top)
        body.addWidget(self.stack, 1)
        h.addLayout(body, 1)

        self.co.currentTextChanged.connect(self._company_changed)
        self.set_pill("Checking Tally...", "#fff4e0", "#8a5200")
        self.load_companies()
        self.refresh_mobile()

    # ---------------- infrastructure ----------------
    @staticmethod
    def _scroll(w):
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        sa.setObjectName("PageScroll")
        sa.viewport().setAutoFillBackground(False)
        w.setObjectName(w.objectName() or "PageBody")
        sa.setWidget(w)
        return sa

    def run(self, fn, ok, fail=None, *a):
        job = Job(fn, *a)
        self.jobs.add(job)

        def _ok(r):
            self.jobs.discard(job)
            ok(r)

        def _fail(m):
            self.jobs.discard(job)
            (fail or self.error)(m)
        job.sig.done.connect(_ok)
        job.sig.fail.connect(_fail)
        self.pool.start(job)

    def error(self, msg):
        self.set_pill("Tally offline", "#ffe3e3", "#b3261e")
        QMessageBox.warning(self, APP_NAME, msg)

    def set_pill(self, text, bg, fg):
        self.pill.setText(text)
        self.pill.setStyleSheet("background:%s;color:%s;" % (bg, fg))

    def period(self):
        return self.dfrom.date().toString("yyyyMMdd"), self.dto.date().toString("yyyyMMdd")

    def page(self, title, subtitle=""):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(12)
        t = QLabel(title)
        t.setObjectName("PageTitle")
        v.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("Muted")
            s.setWordWrap(True)
            v.addWidget(s)
        return w, v

    # ---------------- loading ----------------
    def load_companies(self):
        def ok(cos):
            self.co.blockSignals(True)
            self.co.clear()
            names = [c["name"] for c in cos]
            self.co.addItems(names)
            want = self.cfg["company"]
            if want in names:
                self.co.setCurrentText(want)
            self.co.blockSignals(False)
            if names:
                self.set_pill("Tally connected", "#e2f8ec", "#0f7a43")
                self.load()
            else:
                self.set_pill("No company open", "#fff4e0", "#8a5200")
        self.run(self.svc.companies, ok, None, True)

    def _company_changed(self, name):
        if name:
            self.cfg["company"] = name
            self.load()

    def load(self, force=False):
        c = self.co.currentText()
        if not c:
            self.load_companies()
            return
        f, t = self.period()
        self.btn_load.setEnabled(False)
        self.btn_load.setText("Loading...")

        def ok(b):
            self.btn_load.setEnabled(True)
            self.btn_load.setText("Load from Tally")
            self.bundle = b
            if b.get("offline"):
                self.set_pill("Offline copy " + b["fetched"], "#fff4e0", "#8a5200")
            else:
                self.set_pill("Synced " + b["fetched"][-8:], "#e2f8ec", "#0f7a43")
            self.refresh_all()

        def bad(m):
            self.btn_load.setEnabled(True)
            self.btn_load.setText("Load from Tally")
            self.error(m)
        self.run(self.svc.bundle, ok, bad, c, f, t, force)

    def refresh_all(self):
        b = self.bundle
        if not b:
            return
        self.fill_dashboard(b)
        self.fill_ledgers(b)
        self.fill_vouchers(b)
        self.fill_outstanding(b)
        self.fill_entry_meta(b)

    # ---------------- Dashboard ----------------
    def page_dashboard(self):
        w, v = self.page("Dashboard", "Your Tally books at a glance for the selected period.")
        grid = QGridLayout()
        grid.setSpacing(12)
        self.cards = {}
        names = [("sales", "Sales"), ("purchase", "Purchases"), ("receipt", "Receipts"),
                 ("payment", "Payments"), ("receivable", "Receivable"), ("payable", "Payable"),
                 ("cash", "Cash in hand"), ("bank", "Bank")]
        for i, (k, label) in enumerate(names):
            c = StatCard(label, CARD_GRADS[i])
            self.cards[k] = c
            grid.addWidget(c, i // 4, i % 4)
        v.addLayout(grid)
        row = QHBoxLayout()
        row.setSpacing(12)
        c1 = card()
        l1 = QVBoxLayout(c1)
        t = QLabel("Sales (pink) vs Purchases (blue) by month")
        t.setObjectName("CardTitle")
        l1.addWidget(t)
        self.chart = BarChart()
        l1.addWidget(self.chart)
        c2 = card()
        l2 = QVBoxLayout(c2)
        t2 = QLabel("Top receivables")
        t2.setObjectName("CardTitle")
        l2.addWidget(t2)
        self.t_top = make_table(["Party", "Balance", "Mobile"], numeric=(1,))
        l2.addWidget(self.t_top)
        row.addWidget(c1, 3)
        row.addWidget(c2, 2)
        v.addLayout(row, 1)
        c3 = card()
        l3 = QVBoxLayout(c3)
        t3 = QLabel("Recent vouchers")
        t3.setObjectName("CardTitle")
        l3.addWidget(t3)
        self.t_recent = make_table(["Date", "Type", "No.", "Party", "Amount"], numeric=(4,))
        l3.addWidget(self.t_recent)
        v.addWidget(c3, 1)
        return w

    def fill_dashboard(self, b):
        d = dashboard(b)
        cnt = d["counts"]
        n = lambda k, one, many: "%d %s" % (cnt.get(k, 0), one if cnt.get(k, 0) == 1 else many)
        self.cards["sales"].set(inr(d["sales"]), n("Sales", "invoice", "invoices"))
        self.cards["purchase"].set(inr(d["purchase"]), n("Purchase", "bill", "bills"))
        self.cards["receipt"].set(inr(d["receipt"]), n("Receipt", "receipt", "receipts"))
        self.cards["payment"].set(inr(d["payment"]), n("Payment", "payment", "payments"))
        self.cards["receivable"].set(inr(d["receivable"]), "Sundry Debtors")
        self.cards["payable"].set(inr(d["payable"]), "Sundry Creditors")
        self.cards["cash"].set(inr(d["cash"]), "Closing balance")
        self.cards["bank"].set(inr(d["bank"]), "Closing balance")
        self.chart.set_data(d["monthly"])
        fill_table(self.t_top, [[p["name"], inr(p["balance"]), p["mobile"]] for p in d["top_debtors"]], stretch=0)
        fill_table(self.t_recent, [{"key": r["id"], "cells": [nice_date(r["date"]), r["type"], r["no"],
                                                              r["party"], inr(r["total"])]}
                                   for r in d["recent"]], stretch=3)

    # ---------------- Ledgers ----------------
    def page_ledgers(self):
        w, v = self.page("Ledgers", "Pick a ledger to see its statement. Share it as PDF on WhatsApp or email.")
        sp = QSplitter(Qt.Horizontal)
        left = card()
        ll = QVBoxLayout(left)
        self.l_search = QLineEdit()
        self.l_search.setPlaceholderText("Search ledgers...")
        self.l_kind = QComboBox()
        self.l_kind.addItems(["All", "Debtors", "Creditors", "Cash", "Bank", "Sales", "Purchase",
                              "Expenses", "Income", "Taxes", "Other"])
        r = QHBoxLayout()
        r.addWidget(self.l_search, 1)
        r.addWidget(self.l_kind)
        ll.addLayout(r)
        self.t_led = make_table(["Ledger", "Group", "Closing"], numeric=(2,))
        ll.addWidget(self.t_led)
        right = card()
        rl = QVBoxLayout(right)
        self.l_head = QLabel("Select a ledger")
        self.l_head.setObjectName("CardTitle")
        self.l_info = QLabel("")
        self.l_info.setObjectName("Muted")
        self.l_info.setWordWrap(True)
        rl.addWidget(self.l_head)
        rl.addWidget(self.l_info)
        br = QHBoxLayout()
        self.b_lpdf = btn("Save PDF", "Ghost")
        self.b_lwa = btn("WhatsApp", "Wa")
        self.b_lem = btn("Email", "Em")
        for x in (self.b_lpdf, self.b_lwa, self.b_lem):
            x.setEnabled(False)
            br.addWidget(x)
        br.addStretch(1)
        rl.addLayout(br)
        self.t_stmt = make_table(["Date", "Particulars", "Type", "No.", "Debit", "Credit", "Balance"],
                                 numeric=(4, 5, 6))
        rl.addWidget(self.t_stmt)
        sp.addWidget(left)
        sp.addWidget(right)
        sp.setSizes([380, 700])
        v.addWidget(sp, 1)
        self.l_search.textChanged.connect(lambda: self.fill_ledgers(self.bundle))
        self.l_kind.currentIndexChanged.connect(lambda: self.fill_ledgers(self.bundle))
        self.t_led.itemSelectionChanged.connect(self.show_statement)
        self.b_lpdf.clicked.connect(lambda: self.share_ledger("pdf"))
        self.b_lwa.clicked.connect(lambda: self.share_ledger("wa"))
        self.b_lem.clicked.connect(lambda: self.share_ledger("em"))
        return w

    def fill_ledgers(self, b):
        if not b:
            return
        kmap = {"Debtors": "debtor", "Creditors": "creditor", "Cash": "cash", "Bank": "bank",
                "Sales": "sales", "Purchase": "purchase", "Expenses": "expense", "Income": "income",
                "Taxes": "tax", "Other": "other"}
        k = kmap.get(self.l_kind.currentText())
        s = self.l_search.text().lower().strip()
        rows = [l for l in ledger_list(b) if (not k or l["kind"] == k) and (not s or s in l["name"].lower())]
        fill_table(self.t_led, [{"key": l["name"], "cells": [l["name"], l["group"], drcr(l["balance"])]}
                                for l in rows], stretch=0,
                   colors_fn=lambda r, c: ("#14a35a" if rows[r]["balance"] >= 0 else "#e0383e") if c == 2 else None)

    def show_statement(self):
        name = selected_key(self.t_led)
        if not name or not self.bundle:
            return
        s = statement(self.bundle, name)
        self.cur_stmt = s
        self.l_head.setText(s["ledger"])
        self.l_info.setText("%s  |  Opening %s  |  Closing %s%s%s" % (
            s["group"], drcr(s["opening"]), drcr(s["closing"]),
            ("  |  Mobile " + s["mobile"]) if s["mobile"] else "",
            ("  |  " + s["email"]) if s["email"] else ""))
        for x in (self.b_lpdf, self.b_lwa, self.b_lem):
            x.setEnabled(True)
        rows = [[nice_date(s["from"]), "Opening Balance", "", "", "", "", drcr(s["opening"])]]
        rows += [[nice_date(r["date"]), r["particulars"], r["type"], r["no"],
                  inr(r["dr"]) if r["dr"] else "", inr(r["cr"]) if r["cr"] else "", drcr(r["balance"])]
                 for r in s["rows"]]
        fill_table(self.t_stmt, rows, stretch=1)

    def _save_pdf(self, data, filename):
        folder = self.cfg["out_dir"]
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, filename)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def _reveal(self, path):
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
        except Exception:
            pass

    def _share(self, how, pdf_bytes, filename, mobile, email, text, subject):
        path = self._save_pdf(pdf_bytes, filename)
        if how == "pdf":
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            return
        self._reveal(path)
        if how == "wa":
            QDesktopServices.openUrl(QUrl(wa_link(mobile, text)))
        else:
            QDesktopServices.openUrl(QUrl("mailto:%s?subject=%s&body=%s" % (
                urllib.parse.quote(email or ""), urllib.parse.quote(subject), urllib.parse.quote(text))))
        QMessageBox.information(self, APP_NAME, "PDF saved here:\n%s\n\nThe folder is open. Drag the PDF "
                                "into the WhatsApp chat or email that just opened." % path)

    def share_ledger(self, how):
        s = getattr(self, "cur_stmt", None)
        if not s:
            return
        try:
            data = statement_pdf(self.bundle, s)
        except Exception as e:
            return self.error("Could not create the PDF: %s" % e)
        self._share(how, data, "Ledger_%s_%s.pdf" % (slug(s["ledger"]), s["to"]), s["mobile"], s["email"],
                    share_text_ledger(self.bundle, s), "Ledger statement - " + s["ledger"])

    # ---------------- Vouchers ----------------
    def page_vouchers(self):
        w, v = self.page("Vouchers", "Day book for the period. Select a voucher to share it as a PDF.")
        c = card()
        cl = QVBoxLayout(c)
        r = QHBoxLayout()
        self.v_type = QComboBox()
        self.v_type.addItems(["All", "Sales", "Purchase", "Receipt", "Payment", "Journal", "Contra",
                              "Credit Note", "Debit Note"])
        self.v_search = QLineEdit()
        self.v_search.setPlaceholderText("Search party, voucher number or narration...")
        r.addWidget(self.v_type)
        r.addWidget(self.v_search, 1)
        self.b_vpdf = btn("Save PDF", "Ghost")
        self.b_vwa = btn("WhatsApp", "Wa")
        self.b_vem = btn("Email", "Em")
        for x in (self.b_vpdf, self.b_vwa, self.b_vem):
            r.addWidget(x)
        cl.addLayout(r)
        self.v_total = QLabel("")
        self.v_total.setObjectName("Muted")
        cl.addWidget(self.v_total)
        self.t_v = make_table(["Date", "Type", "No.", "Party / Ledger", "Amount", "Narration"], numeric=(4,))
        cl.addWidget(self.t_v)
        v.addWidget(c, 1)
        self.v_type.currentIndexChanged.connect(lambda: self.fill_vouchers(self.bundle))
        self.v_search.textChanged.connect(lambda: self.fill_vouchers(self.bundle))
        self.b_vpdf.clicked.connect(lambda: self.share_voucher("pdf"))
        self.b_vwa.clicked.connect(lambda: self.share_voucher("wa"))
        self.b_vem.clicked.connect(lambda: self.share_voucher("em"))
        self.t_v.doubleClicked.connect(lambda: self.share_voucher("pdf"))
        return w

    def fill_vouchers(self, b):
        if not b:
            return
        t = self.v_type.currentText()
        s = self.v_search.text().lower().strip()
        vs = [x for x in b["vouchers"] if (t == "All" or x["base"] == t) and
              (not s or s in (x["party"] + " " + x["no"] + " " + x["type"] + " " + x["narration"]).lower())]
        vs = sorted(vs, key=lambda x: (x["date"], x["id"]), reverse=True)
        self.v_total.setText("%d vouchers  |  Total %s" % (len(vs), inr(sum(x["total"] for x in vs))))
        fill_table(self.t_v, [{"key": x["id"], "cells": [nice_date(x["date"]), x["type"], x["no"],
                                                         vsummary(x)["party"], inr(x["total"]),
                                                         x["narration"][:80]]} for x in vs[:2000]], stretch=5)

    def share_voucher(self, how):
        vid = selected_key(self.t_v)
        if not vid or not self.bundle:
            QMessageBox.information(self, APP_NAME, "Select a voucher first.")
            return
        v = find_voucher(self.bundle, vid)
        try:
            data = voucher_pdf(self.bundle, v)
        except Exception as e:
            return self.error("Could not create the PDF: %s" % e)
        pi = v.get("party_info") or {}
        self._share(how, data, "%s_%s.pdf" % (slug(v["type"]), slug(v["no"] or v["date"])),
                    pi.get("mobile", ""), pi.get("email", ""), share_text_voucher(self.bundle, v),
                    "%s %s - %s" % (v["type"], v["no"], self.bundle["company"]))

    # ---------------- Outstanding ----------------
    def page_outstanding(self):
        w, v = self.page("Outstanding", "Who owes you and whom you owe, with bill-wise ageing where Tally keeps bills.")
        r = QHBoxLayout()
        self.o_kind = QComboBox()
        self.o_kind.addItems(["Receivables (Sundry Debtors)", "Payables (Sundry Creditors)"])
        r.addWidget(self.o_kind)
        r.addStretch(1)
        v.addLayout(r)
        grid = QHBoxLayout()
        self.o_cards = []
        for i, lab in enumerate(["Total", "0-30 days", "31-60 days", "61-90 days", "90+ days"]):
            c = StatCard(lab, CARD_GRADS[[4, 2, 3, 5, 1][i]])
            self.o_cards.append(c)
            grid.addWidget(c)
        v.addLayout(grid)
        sp = QSplitter(Qt.Horizontal)
        c1 = card()
        l1 = QVBoxLayout(c1)
        self.t_o = make_table(["Party", "Balance", "Mobile", "Email"], numeric=(1,))
        l1.addWidget(self.t_o)
        c2 = card()
        l2 = QVBoxLayout(c2)
        self.o_head = QLabel("Bills")
        self.o_head.setObjectName("CardTitle")
        l2.addWidget(self.o_head)
        self.t_ob = make_table(["Bill", "Date", "Days", "Pending"], numeric=(2, 3))
        l2.addWidget(self.t_ob)
        rr = QHBoxLayout()
        self.b_owa = btn("Send reminder on WhatsApp", "Wa")
        self.b_ost = btn("Open ledger", "Ghost")
        rr.addWidget(self.b_owa)
        rr.addWidget(self.b_ost)
        rr.addStretch(1)
        l2.addLayout(rr)
        sp.addWidget(c1)
        sp.addWidget(c2)
        sp.setSizes([600, 450])
        v.addWidget(sp, 1)
        self.o_kind.currentIndexChanged.connect(lambda: self.fill_outstanding(self.bundle))
        self.t_o.itemSelectionChanged.connect(self.show_bills)
        self.b_owa.clicked.connect(self.remind)
        self.b_ost.clicked.connect(self.open_party_ledger)
        return w

    def fill_outstanding(self, b):
        if not b:
            return
        o = outstanding(b, "debtor" if self.o_kind.currentIndex() == 0 else "creditor")
        self.cur_out = o
        self.o_cards[0].set(inr(o["total"]), "%d parties" % len(o["parties"]))
        for i, k in enumerate(["0-30", "31-60", "61-90", "90+"]):
            self.o_cards[i + 1].set(inr(o["buckets"][k]) if o["billwise"] else "-",
                                    "" if o["billwise"] else "Bill-wise not maintained")
        fill_table(self.t_o, [{"key": p["name"], "cells": [p["name"], inr(p["balance"]), p["mobile"], p["email"]]}
                              for p in o["parties"]], stretch=0)
        self.t_ob.setRowCount(0)

    def _sel_party(self):
        name = selected_key(self.t_o)
        o = getattr(self, "cur_out", None)
        if not name or not o:
            return None
        return next((p for p in o["parties"] if p["name"] == name), None)

    def show_bills(self):
        p = self._sel_party()
        if not p:
            return
        self.o_head.setText("Bills - " + p["name"])
        fill_table(self.t_ob, [[x["name"], nice_date(x["date"]), x["age"], inr(x["amount"])] for x in p["bills"]],
                   stretch=0)

    def remind(self):
        p = self._sel_party()
        if not p:
            QMessageBox.information(self, APP_NAME, "Select a party first.")
            return
        text = ("Dear %s,\nThis is a gentle reminder that %s is outstanding as per our books (%s).\n"
                "Kindly arrange the payment at the earliest.\nRegards,\n%s"
                % (p["name"], inr(p["balance"]), self.bundle["company"], self.bundle["company"]))
        QDesktopServices.openUrl(QUrl(wa_link(p["mobile"], text)))

    def open_party_ledger(self):
        p = self._sel_party()
        if not p:
            return
        self.nav.button(1).click()
        self.l_search.setText(p["name"])
        for r in range(self.t_led.rowCount()):
            if self.t_led.item(r, 0).text() == p["name"]:
                self.t_led.selectRow(r)
                break

    # ---------------- New voucher ----------------
    def page_entry(self):
        w, v = self.page("New Voucher", "Creates the voucher directly in TallyPrime (accounting mode).")
        c = card()
        cl = QHBoxLayout(c)
        cl.setContentsMargins(18, 16, 18, 16)
        form = QFormLayout()
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)
        self.e_type = QComboBox()
        td = date.today()
        self.e_date = QDateEdit(QDate(td.year, td.month, td.day))
        self.e_date.setCalendarPopup(True)
        self.e_date.setDisplayFormat("dd-MMM-yyyy")
        self.e_a = QComboBox()
        self.e_b = QComboBox()
        for cb in (self.e_a, self.e_b):
            cb.setEditable(True)
            cb.setInsertPolicy(QComboBox.NoInsert)
            cb.completer().setFilterMode(Qt.MatchContains)
            cb.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.e_amt = QDoubleSpinBox()
        self.e_amt.setMaximum(1e12)
        self.e_amt.setDecimals(2)
        self.e_amt.setGroupSeparatorShown(True)
        self.e_amt.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.e_rate = QComboBox()
        self.e_rate.addItems(["0", "5", "12", "18", "28"])
        self.e_mode = QComboBox()
        self.e_mode.addItems(["Within state (CGST + SGST)", "Other state (IGST)"])
        self.e_cg, self.e_sg, self.e_ig = QComboBox(), QComboBox(), QComboBox()
        for cb in (self.e_cg, self.e_sg, self.e_ig):
            cb.setEditable(True)
        self.e_ref = QLineEdit()
        self.e_nar = QTextEdit()
        self.e_nar.setFixedHeight(60)
        self.lab_a, self.lab_b = QLabel("Party"), QLabel("Account")
        form.addRow("Voucher type", self.e_type)
        form.addRow("Date", self.e_date)
        form.addRow(self.lab_a, self.e_a)
        form.addRow(self.lab_b, self.e_b)
        self.lab_amt = QLabel("Amount")
        form.addRow(self.lab_amt, self.e_amt)
        self.gst_rows = [QLabel("GST rate %"), QLabel("Supply"), QLabel("CGST ledger"), QLabel("SGST ledger"),
                         QLabel("IGST ledger")]
        form.addRow(self.gst_rows[0], self.e_rate)
        form.addRow(self.gst_rows[1], self.e_mode)
        form.addRow(self.gst_rows[2], self.e_cg)
        form.addRow(self.gst_rows[3], self.e_sg)
        form.addRow(self.gst_rows[4], self.e_ig)
        form.addRow("Ref / bill no.", self.e_ref)
        form.addRow("Narration", self.e_nar)
        lw = QWidget()
        lw.setLayout(form)
        cl.addWidget(lw, 3)
        right = QVBoxLayout()
        right.setSpacing(10)
        self.b_post = btn("Post to Tally   (Ctrl+S)", "Warm")
        self.b_post.setMinimumHeight(44)
        right.addWidget(self.b_post)
        self.e_msg = QLabel("Fill in the form to see the entry.")
        self.e_msg.setWordWrap(True)
        right.addWidget(self.e_msg)
        t = QLabel("Preview")
        t.setObjectName("CardTitle")
        right.addWidget(t)
        self.t_prev = make_table(["Ledger", "Debit", "Credit"], numeric=(1, 2))
        self.t_prev.setMinimumHeight(140)
        self.t_prev.setMaximumHeight(240)
        right.addWidget(self.t_prev)
        right.addStretch(1)
        cl.addLayout(right, 2)
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        QShortcut(QKeySequence("Ctrl+S"), w, activated=lambda: self.b_post.isEnabled() and self.post_entry())
        v.addWidget(c, 1)
        for sig in (self.e_type.currentIndexChanged, self.e_mode.currentIndexChanged, self.e_rate.currentIndexChanged):
            sig.connect(self.entry_changed)
        for sig in (self.e_a.currentTextChanged, self.e_b.currentTextChanged, self.e_cg.currentTextChanged,
                    self.e_sg.currentTextChanged, self.e_ig.currentTextChanged):
            sig.connect(self.preview_entry)
        self.e_amt.valueChanged.connect(self.preview_entry)
        self.b_post.clicked.connect(self.post_entry)
        return w

    def fill_entry_meta(self, b):
        m = entry_meta(b)
        self.meta = m
        cur = self.e_type.currentText()
        self.e_type.blockSignals(True)
        self.e_type.clear()
        for t in m["types"]:
            self.e_type.addItem(t["name"], t["base"])
        if cur:
            self.e_type.setCurrentText(cur)
        self.e_type.blockSignals(False)
        for cb, key in ((self.e_cg, "cgst"), (self.e_sg, "sgst"), (self.e_ig, "igst")):
            cb.clear()
            cb.addItems([""] + m["tax"]["all"])
            cb.setCurrentText(m["tax"][key])
        self.entry_changed()

    def form_data(self):
        return {"vtype": self.e_type.currentText(), "date": self.e_date.date().toString("yyyyMMdd"),
                "party": self.e_a.currentText(), "account": self.e_b.currentText(),
                "amount": self.e_amt.value(), "gst_rate": self.e_rate.currentText() if self.gst_on() else 0,
                "gst_mode": "inter" if self.e_mode.currentIndex() == 1 else "intra",
                "cgst": self.e_cg.currentText(), "sgst": self.e_sg.currentText(),
                "igst": self.e_ig.currentText(), "ref": self.e_ref.text(),
                "narration": self.e_nar.toPlainText()}

    def gst_on(self):
        return self.e_type.currentData() in ("Sales", "Purchase", "Credit Note", "Debit Note")

    def entry_changed(self):
        if not getattr(self, "meta", None):
            return
        base = self.e_type.currentData() or ""
        la, lb = ENTRY_LABELS.get(base, ("Ledger", "Ledger"))
        self.lab_a.setText(la)
        self.lab_b.setText(lb)
        A = {"Sales": ["debtor"], "Credit Note": ["debtor"], "Purchase": ["creditor"], "Debit Note": ["creditor"],
             "Contra": ["cash", "bank"]}.get(base)
        B = {"Sales": ["sales"], "Credit Note": ["sales"], "Purchase": ["purchase", "expense"],
             "Debit Note": ["purchase"], "Receipt": ["cash", "bank"], "Payment": ["cash", "bank"],
             "Contra": ["cash", "bank"]}.get(base)
        L = self.meta["ledgers"]
        for cb, kinds in ((self.e_a, A), (self.e_b, B)):
            cur = cb.currentText()
            names = [l["name"] for l in L if (not kinds or l["kind"] in kinds)]
            others = [l["name"] for l in L if kinds and l["kind"] not in kinds]
            cb.blockSignals(True)
            cb.clear()
            cb.addItems([""] + names + others)
            cb.setCurrentText(cur)
            cb.blockSignals(False)
        on = self.gst_on()
        inter = self.e_mode.currentIndex() == 1
        rate_on = on and self.e_rate.currentText() != "0"
        self.lab_amt.setText("Taxable value" if on else "Amount")
        vis = [on, on, rate_on and not inter, rate_on and not inter, rate_on and inter]
        widgets = [self.e_rate, self.e_mode, self.e_cg, self.e_sg, self.e_ig]
        for lab, wdg, show in zip(self.gst_rows, widgets, vis):
            lab.setVisible(show)
            wdg.setVisible(show)
        self.preview_entry()

    def preview_entry(self):
        try:
            lines, _, _ = build_lines(self.form_data(), self.bundle)
            fill_table(self.t_prev, [[l, inr(a) if a > 0 else "", inr(-a) if a < 0 else ""] for l, a in lines],
                       stretch=0)
            self.t_prev.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.e_msg.setStyleSheet("color:#0f7a43;font-weight:600;")
            self.e_msg.setText("Balanced. Total %s" % inr(sum(a for _, a in lines if a > 0)))
            self.b_post.setEnabled(True)
        except TallyError as e:
            self.t_prev.setRowCount(0)
            self.e_msg.setStyleSheet("color:#b3261e;")
            self.e_msg.setText(str(e))
            self.b_post.setEnabled(False)

    def post_entry(self):
        if not self.bundle:
            return
        data = self.form_data()
        try:
            lines, _, _ = build_lines(data, self.bundle)
        except TallyError as e:
            return self.error(str(e))
        total = sum(a for _, a in lines if a > 0)
        if QMessageBox.question(self, APP_NAME, "Post this %s for %s into '%s'?" % (
                data["vtype"], inr(total), self.bundle["company"])) != QMessageBox.Yes:
            return
        self.b_post.setEnabled(False)
        self.b_post.setText("Posting...")

        def ok(res):
            self.b_post.setText("Post to Tally   (Ctrl+S)")
            self.e_amt.setValue(0)
            self.e_ref.clear()
            self.e_nar.clear()
            QMessageBox.information(self, APP_NAME, "Voucher created in TallyPrime.")
            self.load(force=True)

        def bad(m):
            self.b_post.setText("Post to Tally   (Ctrl+S)")
            self.b_post.setEnabled(True)
            QMessageBox.warning(self, APP_NAME, "Tally did not accept the voucher:\n\n" + m)
        self.run(self.svc.post_entry, ok, bad, self.bundle["company"], data)

    # ---------------- Mobile access ----------------
    def page_mobile(self):
        w, v = self.page("Mobile Access", "Open Tally on your phone. Keep this app and TallyPrime running on this PC.")
        row = QHBoxLayout()
        row.setSpacing(12)
        c1 = card()
        l1 = QVBoxLayout(c1)
        l1.setContentsMargins(18, 16, 18, 16)
        t = QLabel("Same Wi-Fi (office / home)")
        t.setObjectName("CardTitle")
        l1.addWidget(t)
        self.m_lan = QLabel("")
        self.m_lan.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.m_lan.setStyleSheet("font-size:12pt;font-weight:700;color:#4b2bd6;")
        l1.addWidget(self.m_lan)
        self.m_qr = QLabel()
        self.m_qr.setAlignment(Qt.AlignCenter)
        l1.addWidget(self.m_qr)
        hint = QLabel("Scan with the phone camera, then enter the PIN. If Windows asks, allow Python "
                      "through the firewall on private networks.")
        hint.setWordWrap(True)
        hint.setObjectName("Muted")
        l1.addWidget(hint)
        l1.addStretch(1)
        c2 = card()
        l2 = QVBoxLayout(c2)
        l2.setContentsMargins(18, 16, 18, 16)
        t2 = QLabel("On the go (internet)")
        t2.setObjectName("CardTitle")
        l2.addWidget(t2)
        self.m_net = QLabel("Off. Switch on to get a private https link that works on mobile data.")
        self.m_net.setWordWrap(True)
        self.m_net.setTextInteractionFlags(Qt.TextSelectableByMouse)
        l2.addWidget(self.m_net)
        self.m_qr2 = QLabel()
        self.m_qr2.setAlignment(Qt.AlignCenter)
        l2.addWidget(self.m_qr2)
        self.b_net = btn("Switch on internet access", "Warm")
        self.b_net.clicked.connect(self.toggle_tunnel)
        l2.addWidget(self.b_net)
        warn = QLabel("Uses a free Cloudflare quick tunnel. The link changes each time you switch it on, "
                      "and only people with the link and the PIN can open your books. Switch it off when "
                      "not needed.")
        warn.setWordWrap(True)
        warn.setObjectName("Muted")
        l2.addWidget(warn)
        l2.addStretch(1)
        c3 = card()
        l3 = QVBoxLayout(c3)
        l3.setContentsMargins(18, 16, 18, 16)
        t3 = QLabel("PIN")
        t3.setObjectName("CardTitle")
        l3.addWidget(t3)
        self.m_pin = QLabel(self.cfg["pin"])
        self.m_pin.setStyleSheet("font-size:28pt;font-weight:800;letter-spacing:6px;color:#ff5a5f;")
        self.m_pin.setTextInteractionFlags(Qt.TextSelectableByMouse)
        l3.addWidget(self.m_pin)
        b1 = btn("New random PIN", "Ghost")
        b1.clicked.connect(self.new_pin)
        l3.addWidget(b1)
        b2 = btn("Sign out all phones", "Ghost")
        b2.clicked.connect(lambda: (self.server.logout_all(),
                                    QMessageBox.information(self, APP_NAME, "All phones are signed out.")))
        l3.addWidget(b2)
        self.m_status = QLabel("")
        self.m_status.setWordWrap(True)
        l3.addWidget(self.m_status)
        l3.addStretch(1)
        row.addWidget(c1, 3)
        row.addWidget(c2, 3)
        row.addWidget(c3, 2)
        v.addLayout(row, 1)
        tip = QLabel("Tip: on the phone, use the browser menu > \"Add to Home screen\" to get a VRI Tally app icon.")
        tip.setObjectName("Muted")
        v.addWidget(tip)
        return w

    def refresh_mobile(self):
        if self.server.httpd:
            url = self.server.lan_url()
            self.m_lan.setText(url)
            self.m_qr.setPixmap(qr_pixmap(url, 210))
            self.m_status.setText("Mobile server is running on port %s." % self.server.port)
            self.m_status.setStyleSheet("color:#0f7a43;font-weight:600;")
        else:
            self.m_lan.setText("Not running")
            self.m_status.setText(self.server.error or "Mobile server is stopped.")
            self.m_status.setStyleSheet("color:#b3261e;")

    def new_pin(self):
        self.cfg["pin"] = "%06d" % secrets.randbelow(10 ** 6)
        self.m_pin.setText(self.cfg["pin"])
        self.server.logout_all()

    def toggle_tunnel(self):
        if self.server.tunnel_url:
            self.server.stop_tunnel()
            self.m_qr2.clear()
            self.m_net.setText("Off. Switch on to get a private https link that works on mobile data.")
            self.b_net.setText("Switch on internet access")
            return
        if not self.server.httpd:
            return self.error("Start the mobile server first (check the port in Settings).")
        self.b_net.setEnabled(False)
        self.b_net.setText("Connecting (first time downloads a small helper)...")

        def ok(url):
            self.b_net.setEnabled(True)
            self.b_net.setText("Switch off internet access")
            self.m_net.setText(url)
            self.m_net.setStyleSheet("font-size:11pt;font-weight:700;color:#ff5a5f;")
            self.m_qr2.setPixmap(qr_pixmap(url, 210))

        def bad(m):
            self.b_net.setEnabled(True)
            self.b_net.setText("Switch on internet access")
            self.error("Could not start internet access: " + m)
        self.run(self.server.start_tunnel, ok, bad)

    # ---------------- Settings ----------------
    def page_settings(self):
        w, v = self.page("Settings")
        c = card()
        f = QFormLayout(c)
        f.setContentsMargins(18, 16, 18, 16)
        f.setVerticalSpacing(12)
        self.s_host = QLineEdit(str(self.cfg["tally_host"]))
        self.s_port = QSpinBox()
        self.s_port.setRange(1, 65535)
        self.s_port.setValue(int(self.cfg["tally_port"]))
        self.s_web = QSpinBox()
        self.s_web.setRange(1024, 65535)
        self.s_web.setValue(int(self.cfg["web_port"]))
        self.s_out = QLineEdit(self.cfg["out_dir"])
        pick = btn("Browse", "Ghost")
        pick.clicked.connect(lambda: self.s_out.setText(
            QFileDialog.getExistingDirectory(self, "PDF folder", self.s_out.text()) or self.s_out.text()))
        orow = QHBoxLayout()
        orow.addWidget(self.s_out, 1)
        orow.addWidget(pick)
        f.addRow("TallyPrime computer", self.s_host)
        f.addRow("TallyPrime port", self.s_port)
        f.addRow("Mobile app port", self.s_web)
        f.addRow("Save PDFs in", orow)
        brow = QHBoxLayout()
        save = btn("Save and reconnect")
        save.clicked.connect(self.save_settings)
        test = btn("Test Tally connection", "Ghost")
        test.clicked.connect(self.test_tally)
        diag = btn("Check voucher download", "Ghost")
        diag.clicked.connect(self.check_vouchers)
        brow.addWidget(save)
        brow.addWidget(test)
        brow.addWidget(diag)
        brow.addStretch(1)
        f.addRow("", brow)
        v.addWidget(c)
        help_c = card()
        hl = QVBoxLayout(help_c)
        hl.setContentsMargins(18, 16, 18, 16)
        ht = QLabel("Connect TallyPrime (one time)")
        ht.setObjectName("CardTitle")
        hl.addWidget(ht)
        txt = QLabel("1. In TallyPrime press F1 (Help) > Settings > Connectivity.\n"
                     "2. Set 'TallyPrime acts as' to Both (or Server) and Port to 9000. Save.\n"
                     "3. Load the company you want to use, then press 'Load from Tally' above.\n\n"
                     "Data saved for offline viewing: %s\n"
                     "Libraries (if ever needed):  %s" % (CACHE_DIR, PIP_LINE))
        txt.setTextInteractionFlags(Qt.TextSelectableByMouse)
        txt.setWordWrap(True)
        hl.addWidget(txt)
        v.addWidget(help_c)
        v.addStretch(1)
        return w

    def save_settings(self):
        self.cfg.data.update({"tally_host": self.s_host.text().strip() or "localhost",
                              "tally_port": self.s_port.value(), "out_dir": self.s_out.text().strip()
                              or self.cfg["out_dir"]})
        web_changed = self.s_web.value() != int(self.cfg["web_port"])
        self.cfg["web_port"] = self.s_web.value()
        self.svc.reconnect()
        if web_changed:
            self.server.stop_tunnel()
            self.server.stop()
            self.server.start()
            self.refresh_mobile()
        self.load_companies()
        QMessageBox.information(self, APP_NAME, "Settings saved.")

    def check_vouchers(self):
        c = self.co.currentText()
        if not c:
            return self.error("Choose a company first.")
        f, t = self.period()

        def ok(text):
            QMessageBox.information(self, APP_NAME, text)
            self.load(force=True)
        self.run(self.svc.diagnose, ok, None, c, f, t)

    def test_tally(self):
        url = "http://%s:%s" % (self.s_host.text().strip() or "localhost", self.s_port.value())
        ok = TallyClient(url).ping()
        if ok:
            QMessageBox.information(self, APP_NAME, "TallyPrime is answering at %s." % url)
        else:
            QMessageBox.warning(self, APP_NAME, "No answer from %s.\nCheck that TallyPrime is open and "
                                "Connectivity is enabled on that port." % url)

    def closeEvent(self, e):
        try:
            self.server.stop_tunnel()
        except Exception:
            pass
        e.accept()


# =============================================================================
# 9. MAIN
# =============================================================================
def main():
    cfg = Config()
    svc = DataService(cfg)
    server = MobileServer(svc, cfg)
    server.start()
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(QApplication, "setHighDpiScaleFactorRoundingPolicy"):
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except Exception:
        pass
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    win = MainWindow(cfg, svc, server)
    win.showMaximized()
    print("%s is running. Phone (same Wi-Fi): %s   PIN: %s" % (APP_NAME, server.lan_url(), cfg["pin"]))
    app.exec_()
    server.stop_tunnel()
    server.stop()


if __name__ == "__main__":
    main()
