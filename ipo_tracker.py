# -*- coding: utf-8 -*-
"""
IPO_Tracker  -  Indian IPO tracker (PyQt5)
==========================================
* Archive  : IPOs of the last 2 years, grouped month by month.
* Upcoming : IPOs from today onward in 4 buckets (this month, next month,
             within 6 months, within 1 year) with filters, financial
             highlights, broker / fund-house views and a final verdict.
* Every IPO is validated: the gap between opening and closing date must not
  exceed 12 days, otherwise the IPO is REJECTED.

Run:  open in IDLE and press F5   (needs:  pip install PyQt5 requests beautifulsoup4)

Data policy: live data is read from public websites (Chittorgarh, NSE, Yahoo
Finance).  If the internet or a website is unavailable the app falls back to
its last saved cache, and finally to clearly labelled DEMO data with fictional
companies.  Nothing here is investment advice.
"""

import sys
import os
import re
import csv
import json
import time
import random
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor

# ----------------------------------------------------------------------------
# Friendly start-up check (works even inside IDLE without a console)
# ----------------------------------------------------------------------------
try:
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRectF, QPointF, QTimer
    from PyQt5.QtGui import (QKeySequence, QColor, QFont, QPainter, QPen, QBrush,
                             QLinearGradient, QPainterPath)
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QTabWidget, QTreeWidget,
        QTreeWidgetItem, QLineEdit, QRadioButton, QButtonGroup, QComboBox,
        QFrame, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem,
        QHeaderView, QTextBrowser, QStackedWidget, QShortcut, QMessageBox, QFileDialog, QSizePolicy,
        QAbstractItemView)
except ImportError:
    msg = ("IPO_Tracker needs the PyQt5 library.\n\n"
           "Open Command Prompt and run:\n"
           "pip install PyQt5 requests beautifulsoup4")
    try:
        import tkinter
        from tkinter import messagebox
        _r = tkinter.Tk()
        _r.withdraw()
        messagebox.showerror("IPO_Tracker - missing library", msg)
    except Exception:
        print(msg)
    sys.exit(1)

try:
    import requests
except ImportError:          # the app still runs (demo / cache / CSV mode)
    requests = None
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# ----------------------------------------------------------------------------
# Settings you may change
# ----------------------------------------------------------------------------
APP_NAME = "IPO_Tracker"
APP_VERSION = "1.1"
MAX_WINDOW_DAYS = 12          # open -> close gap above this is REJECTED
ARCHIVE_MONTHS = 24           # archive = last 2 years
LARGE_CAP_MIN_CR = 100000     # approx. post-issue market cap (Rs crore)
MID_CAP_MIN_CR = 30000        # below this -> small cap (approximate AMFI bands)
CACHE_DIR = Path.home() / ".ipo_tracker"
CACHE_FILE = CACHE_DIR / "cache.json"
HTTP_TIMEOUT = 15
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Editable live endpoints (websites change them from time to time)
CHITTORGARH_JSON = [
    "https://webnodejs.chittorgarh.com/cloud/report/data-read/82/1/{m}/{y}/{fy}/0/all/0?search=&v=1",
]
CHITTORGARH_HTML = "https://www.chittorgarh.com/report/ipo-in-india-list-main-board-sme/82/?year={y}"
NSE_HOME = "https://www.nseindia.com"
NSE_APIS = [
    "https://www.nseindia.com/api/ipo-current-issues",
    "https://www.nseindia.com/api/all-upcoming-issues?category=ipo",
    "https://www.nseindia.com/api/all-upcoming-issues?category=sme",
]
YAHOO_SEARCH = "https://query2.finance.yahoo.com/v1/finance/search?q={q}&quotesCount=6&newsCount=0"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=1d&interval=1d"

# ----------------------------------------------------------------------------
# Text shown in the app and exported to the Word files
# ----------------------------------------------------------------------------
SOURCES = [
    ("Chittorgarh.com", "https://www.chittorgarh.com",
     "IPO lists (mainboard and SME), dates, price bands, issue size, financial tables and broker review tables on IPO pages."),
    ("NSE India", "https://www.nseindia.com",
     "Current and upcoming public issues (official exchange data)."),
    ("BSE India", "https://www.bseindia.com",
     "Public issues and listing information (official exchange data, reference source)."),
    ("Yahoo Finance", "https://finance.yahoo.com",
     "Current market price (CMP) of listed shares (NSE / BSE tickers)."),
    ("SEBI", "https://www.sebi.gov.in",
     "Regulatory reference for IPO rules and offer documents (RHP / DRHP)."),
]

BROKERS = [
    ("Angel One", "Broker"), ("Axis Securities", "Broker"),
    ("Anand Rathi", "Broker"), ("Arihant Capital", "Broker"),
    ("Bajaj Broking", "Broker"), ("Canara Bank Securities", "Broker"),
    ("Choice Broking", "Broker"), ("Geojit", "Broker"),
    ("HDFC Securities", "Broker"), ("ICICI Securities (ICICIdirect)", "Broker"),
    ("Kotak Securities", "Broker"), ("Motilal Oswal", "Broker"),
    ("Nirmal Bang", "Broker"), ("Prabhudas Lilladher", "Broker"),
    ("Religare Broking", "Broker"), ("Reliance Securities", "Broker"),
    ("SBI Securities", "Broker"), ("Sharekhan", "Broker"),
    ("SMC Global Securities", "Broker"), ("Ventura Securities", "Broker"),
    ("Hem Securities", "Broker (SME focus)"), ("StoxBox", "Broker / Research"),
    ("SBI Mutual Fund", "Fund house (anchor investor)"),
    ("HDFC Mutual Fund", "Fund house (anchor investor)"),
    ("ICICI Prudential Mutual Fund", "Fund house (anchor investor)"),
    ("Nippon India Mutual Fund", "Fund house (anchor investor)"),
    ("Kotak Mahindra Mutual Fund", "Fund house (anchor investor)"),
    ("Axis Mutual Fund", "Fund house (anchor investor)"),
    ("Aditya Birla Sun Life Mutual Fund", "Fund house (anchor investor)"),
    ("UTI Mutual Fund", "Fund house (anchor investor)"),
    ("Mirae Asset Mutual Fund", "Fund house (anchor investor)"),
    ("Motilal Oswal Mutual Fund", "Fund house (anchor investor)"),
    ("Life Insurance Corporation (LIC)", "Institutional investor"),
]

BROKER_NOTE = ("The app only displays opinions that the data source actually publishes for "
               "an IPO. Any broker or fund house not listed on the source for a particular "
               "issue is shown as 'not available' - the app never invents an opinion. "
               "Fund-house 'opinion' is normally visible only through anchor-investor "
               "participation, not as a written rating.")

DISCLAIMER = [
    "The verdict shown in IPO_Tracker (Good / Average / Not Recommended) is an automated "
    "OPINION generated from a simple, transparent scoring rule using publicly available "
    "information. It is NOT financial, investment, tax or legal advice and is NOT a "
    "recommendation to buy, sell, apply for or hold any security.",
    "Data is collected from third-party public websites and may be delayed, incomplete, "
    "wrongly parsed or out of date. Dates, price bands, market prices, financial figures and "
    "broker views must be verified against the official Red Herring Prospectus (RHP), the "
    "stock exchanges (NSE / BSE) and SEBI before any decision.",
    "Investments in securities, including IPOs, are subject to market risk. You may lose part "
    "or all of your capital. Past performance and listing gains do not guarantee future results.",
    "Broker and fund-house views quoted come from the cited sources; their inclusion does not "
    "mean that those firms endorse this application. Market-cap class and industry may be "
    "estimated when not published (marked 'est.').",
    "When the app runs in DEMO mode, every company, number and opinion shown is fictional "
    "sample data for demonstrating the screen layout only.",
    "Please do your own research and consult a SEBI-registered investment adviser before "
    "investing. The authors of this software accept no liability for any loss.",
]

INDUSTRIES = ["Banking & Finance", "Information Technology", "Pharma & Healthcare",
              "Energy & Power", "Infrastructure & Construction", "Real Estate",
              "Automobile & Components", "FMCG & Consumer", "Chemicals & Materials",
              "Textiles & Apparel", "Logistics & Transport", "Manufacturing & Engineering",
              "Retail & E-commerce", "Other"]

INDUSTRY_KEYWORDS = [
    ("Banking & Finance", ["bank", "finance", "finserv", "capital", "insur", "fund", "credit",
                           "housing fin", "microfin", "securities", "amc", "wealth"]),
    ("Information Technology", ["tech", "software", "digital", "systems", "data", "cyber",
                                "info", "cloud", "ai ", "semicon", "electronic"]),
    ("Pharma & Healthcare", ["pharma", "health", "hospital", "bio", "labs", "medic", "care",
                             "therap", "diagnos", "life science"]),
    ("Energy & Power", ["energy", "power", "solar", "oil", "gas", "renew", "hydro", "wind",
                        "battery", "petro"]),
    ("Infrastructure & Construction", ["infra", "construct", "highway", "engineer", "cement",
                                       "build", "rail", "metro"]),
    ("Real Estate", ["realty", "estate", "housing", "propert", "developer", "reit"]),
    ("Automobile & Components", ["auto", "motor", "vehicle", "tyre", "ev "]),
    ("FMCG & Consumer", ["food", "foods", "beverage", "agro", "dairy", "consumer", "fmcg",
                         "hotel", "restaurant", "spice", "bakery", "snack"]),
    ("Chemicals & Materials", ["chem", "steel", "metal", "alloy", "polymer", "plastic", "paper",
                               "packag", "mining", "mineral"]),
    ("Textiles & Apparel", ["textile", "tex", "apparel", "garment", "fashion", "spin", "loom"]),
    ("Logistics & Transport", ["logistic", "transport", "shipping", "cargo", "aviation",
                               "airline", "freight"]),
    ("Retail & E-commerce", ["retail", "mart", "commerce", "store", "market", "jewel"]),
]

# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
DATE_FORMATS = ["%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%d %b, %Y", "%b %d, %Y",
                "%d/%m/%Y", "%d-%m-%Y", "%d-%B-%Y", "%d %B %Y", "%d/%m/%y", "%Y-%m-%d"]


def parse_date(v) -> Optional[date]:
    """Convert many date styles into a date, or None."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = re.sub(r"<[^>]+>", "", str(v)).strip().replace("Sept", "Sep")
    if not s:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        s = s[:10]
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            continue
    return None


def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    last = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28,
            31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(d.day, last))


def numbers_in(s) -> List[float]:
    out = []
    for x in re.findall(r"\d[\d,]*\.?\d*", str(s)):
        try:
            out.append(float(x.replace(",", "")))
        except ValueError:
            pass
    return out


def signed_num(cell: str) -> Optional[float]:
    """Number from a table cell; '(10)' or '-10' are negative."""
    n = numbers_in(cell)
    if not n:
        return None
    neg = "(" in cell or cell.strip().startswith("-") or cell.strip().startswith("\u2212")
    return -n[0] if neg else n[0]


def strip_html(s) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(s))).strip()


def fmt_date(d: Optional[date]) -> str:
    return d.strftime("%d %b %Y") if d else "-"


def fmt_date_short(d: Optional[date]) -> str:
    return d.strftime("%d %b %y") if d else "-"


def fmt_money(v: Optional[float]) -> str:
    if v is None:
        return "-"
    if abs(v - round(v)) < 0.005:
        return "\u20b9{:,.0f}".format(v)
    return "\u20b9{:,.2f}".format(v)


def fmt_cr(v: Optional[float]) -> str:
    if v is None:
        return "-"
    return "\u20b9{:,.0f} Cr".format(v)


def norm_key(k) -> str:
    return re.sub(r"[^a-z0-9]", "", str(k).lower())


# ----------------------------------------------------------------------------
# Data model
# ----------------------------------------------------------------------------
class IPO:
    def __init__(self, name, open_date, close_date, price_low=None, price_high=None,
                 exchange="", is_sme=False, issue_size_cr=None, market_cap_cr=None,
                 industry="", symbol="", detail_url="", lead_manager="", cmp=None,
                 financials=None, opinions=None, source="", demo=False):
        self.name = name
        self.open_date = open_date
        self.close_date = close_date
        self.price_low = price_low
        self.price_high = price_high
        self.exchange = exchange
        self.is_sme = is_sme
        self.issue_size_cr = issue_size_cr
        self.market_cap_cr = market_cap_cr
        self.industry = industry
        self.symbol = symbol
        self.detail_url = detail_url
        self.lead_manager = lead_manager
        self.cmp = cmp
        self.financials = financials or []   # [{period, revenue, pat, net_worth}]
        self.opinions = opinions or []       # [{source, view, note}]
        self.source = source
        self.demo = demo
        self.enriched = False

    @property
    def key(self) -> str:
        return self.name.strip().lower() + "|" + str(self.open_date)

    @property
    def issue_price(self) -> Optional[float]:
        return self.price_high if self.price_high is not None else self.price_low

    @property
    def price_band_text(self) -> str:
        if self.price_low is None and self.price_high is None:
            return "To be announced"
        if self.price_low is None or self.price_low == self.price_high:
            return fmt_money(self.price_high)
        return "{} - {}".format(fmt_money(self.price_low), fmt_money(self.price_high))

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["open_date"] = self.open_date.isoformat() if self.open_date else None
        d["close_date"] = self.close_date.isoformat() if self.close_date else None
        return d

    @staticmethod
    def from_dict(d: dict) -> "IPO":
        o = IPO(d.get("name", ""), parse_date(d.get("open_date")), parse_date(d.get("close_date")))
        for k, v in d.items():
            if k not in ("open_date", "close_date"):
                setattr(o, k, v)
        return o


def validate_window(o: IPO) -> Tuple[bool, str]:
    """The 12-day rule.  Returns (is_valid, reason_if_rejected)."""
    if not o.open_date or not o.close_date:
        return False, "Opening or closing date missing"
    gap = (o.close_date - o.open_date).days
    if gap < 0:
        return False, "Closing date is before opening date"
    if gap > MAX_WINDOW_DAYS:
        return False, "Subscription window is {} days (maximum allowed {})".format(gap, MAX_WINDOW_DAYS)
    return True, ""


def cap_info(o: IPO) -> Tuple[str, bool]:
    """(class, estimated?) where class is Large Cap / Mid Cap / Small Cap / SME / Unclassified."""
    if o.is_sme:
        return "SME", False
    mc, est = o.market_cap_cr, False
    if mc is None and o.issue_size_cr:
        mc, est = o.issue_size_cr * 10.0, True      # rough proxy when not published
    if mc is None:
        return "Unclassified", False
    if mc >= LARGE_CAP_MIN_CR:
        return "Large Cap", est
    if mc >= MID_CAP_MIN_CR:
        return "Mid Cap", est
    return "Small Cap", est


def infer_industry(o: IPO) -> Tuple[str, bool]:
    if o.industry:
        return o.industry, False
    n = " " + o.name.lower() + " "
    for label, words in INDUSTRY_KEYWORDS:
        if any(w in n for w in words):
            return label, True
    return "Other", True


def bucket_for(o: IPO, today: date) -> Optional[str]:
    ref = max(o.open_date, today)          # an issue open today counts as "this month"
    diff = (ref.year - today.year) * 12 + ref.month - today.month
    if diff == 0:
        return "This Month"
    if diff == 1:
        return "Next Month"
    if ref <= add_months(today, 6):
        return "Within 6 Months"
    if ref <= add_months(today, 12):
        return "Within 1 Year"
    return None


BUCKETS = ["This Month", "Next Month", "Within 6 Months", "Within 1 Year"]


# ----------------------------------------------------------------------------
# Verdict engine (transparent rule-based opinion)
# ----------------------------------------------------------------------------
def classify_view(text: str) -> str:
    t = str(text).lower()
    if any(w in t for w in ("avoid", "not recommended", "sell", "reduce", "negative")):
        return "neg"
    if any(w in t for w in ("may apply", "neutral", "hold", "wait", "average", "cautious", "risky")):
        return "neu"
    if any(w in t for w in ("subscribe", "buy", "apply", "accumulate", "positive", "recommend")):
        return "pos"
    return "neu"


def compute_verdict(o: IPO) -> dict:
    score, reasons, evidence = 0.0, [], 0
    fin = [f for f in o.financials if f.get("revenue") is not None]
    if len(fin) >= 2:
        evidence += 1
        r0, r1 = fin[0]["revenue"], fin[-1]["revenue"]
        if r0 and r0 > 0 and r1 is not None:
            growth = (r1 / r0 - 1) * 100
            if growth >= 20:
                score += 1.5
                reasons.append("Revenue grew {:.0f}% over the period shown (+1.5)".format(growth))
            elif growth >= 5:
                score += 0.5
                reasons.append("Revenue grew moderately, {:.0f}% (+0.5)".format(growth))
            else:
                score -= 1
                reasons.append("Revenue growth is weak/negative, {:.0f}% (-1)".format(growth))
    pats = [f["pat"] for f in o.financials if f.get("pat") is not None]
    if pats:
        evidence += 1
        if pats[-1] < 0:
            score -= 2
            reasons.append("Latest Profit After Tax is negative (-2)")
        else:
            score += 1
            reasons.append("Latest Profit After Tax is positive (+1)")
            if len(pats) >= 2 and pats[0] > 0 and pats[-1] / pats[0] >= 1.2:
                score += 1
                reasons.append("Profit is growing strongly (+1)")
        rev = [f for f in o.financials if f.get("pat") is not None and f.get("revenue")]
        if rev and rev[-1]["revenue"] > 0 and pats[-1] > 0:
            margin = pats[-1] / rev[-1]["revenue"] * 100
            if margin >= 10:
                score += 0.5
                reasons.append("Healthy net margin, {:.1f}% (+0.5)".format(margin))
    views = [classify_view(x.get("view", "")) for x in o.opinions]
    if views:
        evidence += 1
        pos, neg = views.count("pos"), views.count("neg")
        share = pos / float(len(views))
        if share >= 0.6:
            score += 2
            reasons.append("{} of {} brokers/houses are positive (+2)".format(pos, len(views)))
        elif neg / float(len(views)) >= 0.4:
            score -= 2
            reasons.append("{} of {} brokers/houses say avoid (-2)".format(neg, len(views)))
        else:
            reasons.append("Broker views are mixed/neutral (0)")
    if evidence == 0:
        return {"label": "Average", "score": 0.0, "confidence": "Low",
                "reasons": ["Not enough published data yet - defaulting to Average with low confidence."]}
    label = "Good" if score >= 3 else ("Not Recommended" if score <= -1 else "Average")
    conf = "High" if evidence == 3 else ("Medium" if evidence == 2 else "Low")
    return {"label": label, "score": score, "confidence": conf, "reasons": reasons}


VERDICT_COLORS = {"Good": "#2EAD6B", "Average": "#E9A427", "Not Recommended": "#D9534F"}
VERDICT_BG = {"Good": "#D5F5E3", "Average": "#FFF0C9", "Not Recommended": "#FFD9D6"}
VIEW_BG = {"pos": "#D5F5E3", "neu": "#FFF0C9", "neg": "#FFD9D6"}
VIEW_TEXT = {"pos": "Positive", "neu": "Neutral", "neg": "Avoid"}


# ----------------------------------------------------------------------------
# Live data providers  (all wrapped: any failure just means "try the next one")
# ----------------------------------------------------------------------------
def _session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json, text/html, */*",
                      "Accept-Language": "en-US,en;q=0.9"})
    return s


def _pick(m: dict, needles, avoid=()) -> object:
    for k, v in m.items():
        nk = norm_key(k)
        if any(n in nk for n in needles) and not any(a in nk for a in avoid):
            return v
    return None


def record_to_ipo(m: dict, source: str) -> Optional[IPO]:
    """Turn one raw dictionary (any provider) into an IPO, tolerant to key names."""
    name_raw = _pick(m, ("companyname", "company", "issuer", "name"), avoid=("lead", "manager", "registrar"))
    if not name_raw:
        return None
    href = re.search(r'href="([^"]+)"', str(name_raw))
    name = strip_html(name_raw)
    name = re.sub(r"\s+IPO$", "", name, flags=re.I).strip()
    od = parse_date(_pick(m, ("opendate", "opening", "startdate", "issuestart")))
    cd = parse_date(_pick(m, ("closedate", "closing", "enddate", "issueend")))
    if not name or not od:
        return None
    band = _pick(m, ("priceband", "issueprice", "price"), avoid=("listing", "gain", "current"))
    ns = numbers_in(strip_html(band)) if band is not None else []
    lo = min(ns[:2]) if ns else None
    hi = max(ns[:2]) if ns else None
    listing_at = strip_html(_pick(m, ("listingat", "exchange", "series", "platform")) or "")
    is_sme = "sme" in listing_at.lower() or "sme" in (name.lower()) or "emerge" in listing_at.lower()
    size = _pick(m, ("issueamount", "issuesize", "totalissue", "size"))
    size_n = numbers_in(strip_html(size)) if size is not None else []
    url = ""
    if href:
        url = href.group(1)
        if url.startswith("/"):
            url = "https://www.chittorgarh.com" + url
    sym = strip_html(_pick(m, ("symbol",)) or "")
    lm = strip_html(_pick(m, ("leadmanager", "bookrunner")) or "")
    o = IPO(name, od, cd, lo, hi, listing_at or ("NSE" if source == "NSE" else ""), is_sme,
            (size_n[0] / 1e7 if size_n and size_n[0] > 1e6 else (size_n[0] if size_n else None)), None, "", sym, url, lm, None, source=source)
    return o


def rows_from_json(obj) -> List[dict]:
    """Find the list of row-dictionaries inside an unknown JSON layout."""
    if isinstance(obj, list):
        if obj and isinstance(obj[0], dict):
            return obj
        for x in obj:
            r = rows_from_json(x)
            if r:
                return r
    elif isinstance(obj, dict):
        for k in ("reportTableData", "data", "rows", "result", "records", "issues"):
            if k in obj:
                r = rows_from_json(obj[k])
                if r:
                    return r
        for v in obj.values():
            if isinstance(v, (list, dict)):
                r = rows_from_json(v)
                if r:
                    return r
    return []


def fetch_chittorgarh(sess, year: int) -> List[IPO]:
    out = []
    fy = "{}-{:02d}".format(year, (year + 1) % 100)
    for tpl in CHITTORGARH_JSON:
        for month in (12, 1):
            try:
                r = sess.get(tpl.format(m=month, y=year, fy=fy), timeout=HTTP_TIMEOUT)
                if r.status_code != 200:
                    continue
                for row in rows_from_json(r.json()):
                    o = record_to_ipo(row, "Chittorgarh")
                    if o:
                        out.append(o)
                if out:
                    return out
            except Exception:
                continue
    # HTML table fallback (works only if the page is server-rendered)
    if BeautifulSoup is not None:
        try:
            r = sess.get(CHITTORGARH_HTML.format(y=year), timeout=HTTP_TIMEOUT)
            soup = BeautifulSoup(r.text, "html.parser")
            for table in soup.find_all("table"):
                heads = [strip_html(th.get_text(" ")) for th in table.find_all("th")]
                if not any("clos" in h.lower() for h in heads):
                    continue
                for tr in table.find_all("tr"):
                    tds = tr.find_all("td")
                    if len(tds) != len(heads):
                        continue
                    row = {}
                    for h, td in zip(heads, tds):
                        a = td.find("a")
                        row[h] = ('<a href="{}">{}</a>'.format(a["href"], td.get_text(" "))
                                  if a is not None and a.get("href") else td.get_text(" "))
                    o = record_to_ipo(row, "Chittorgarh")
                    if o:
                        out.append(o)
        except Exception:
            pass
    return out


def fetch_nse(sess) -> List[IPO]:
    out = []
    try:
        sess.get(NSE_HOME, timeout=HTTP_TIMEOUT)         # cookies
    except Exception:
        return out
    for url in NSE_APIS:
        try:
            r = sess.get(url, timeout=HTTP_TIMEOUT, headers={"Referer": NSE_HOME + "/market-data/all-upcoming-issues-ipo"})
            if r.status_code != 200:
                continue
            for row in rows_from_json(r.json()):
                o = record_to_ipo(row, "NSE")
                if o:
                    if "sme" in url or "sme" in json.dumps(row).lower():
                        o.is_sme = True
                    out.append(o)
        except Exception:
            continue
    return out


def parse_detail_html(html: str) -> dict:
    """Best-effort extraction of financial highlights, broker views, market cap."""
    res = {"financials": [], "opinions": [], "market_cap_cr": None}
    if BeautifulSoup is None:
        return res
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [strip_html(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if len(rows) < 2:
            continue
        labels = [r[0].lower() for r in rows]
        flat = " ".join(" ".join(r) for r in rows[:2]).lower()
        # financial table
        if any("profit after tax" in l or l.strip() == "pat" for l in labels) and \
                any("revenue" in l or "total income" in l for l in labels):
            head = rows[0]
            periods = head[1:]
            def row_vals(*words):
                for r in rows[1:]:
                    if any(w in r[0].lower() for w in words):
                        return [signed_num(c) for c in r[1:]]
                return [None] * len(periods)
            rev, pat, nw = row_vals("revenue", "total income"), row_vals("profit after tax"), row_vals("net worth")
            fin = []
            for i, p in enumerate(periods):
                if i < len(rev):
                    fin.append({"period": p, "revenue": rev[i],
                                "pat": pat[i] if i < len(pat) else None,
                                "net_worth": nw[i] if i < len(nw) else None})
            def yr(x):
                m = re.search(r"(20\d\d)", x["period"])
                return int(m.group(1)) if m else 0
            fin.sort(key=yr)
            if fin:
                res["financials"] = fin
        # broker views table
        head = " ".join(rows[0]).lower()
        if ("recommend" in head or "review" in head or "brokerage" in head or "rating" in head) and len(rows[0]) >= 2:
            for r in rows[1:]:
                if len(r) >= 2 and r[0] and r[1]:
                    res["opinions"].append({"source": r[0], "view": r[1],
                                            "note": r[2] if len(r) > 2 else ""})
    text = soup.get_text(" ")
    m = re.search(r"Market\s*Cap[^0-9]{0,40}([\d,]+\.?\d*)\s*(Cr|Crore)", text, re.I)
    if m:
        try:
            res["market_cap_cr"] = float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return res


def fetch_detail(o: IPO) -> dict:
    sess = _session()
    r = sess.get(o.detail_url, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return parse_detail_html(r.text)


def lookup_price(sess, name: str, symbol: str, cache: dict) -> Tuple[str, Optional[float]]:
    """Find a ticker (NSE first) and its latest price using Yahoo Finance."""
    syms = cache.setdefault("symbols", {})
    sym = syms.get(name.lower()) or (symbol + ".NS" if symbol else "")
    if not sym:
        try:
            q = re.sub(r"\b(ltd|limited|pvt|private)\b\.?", "", name, flags=re.I).strip()
            r = sess.get(YAHOO_SEARCH.format(q=requests.utils.quote(q)), timeout=HTTP_TIMEOUT)
            for item in r.json().get("quotes", []):
                s = item.get("symbol", "")
                if s.endswith(".NS") or s.endswith(".BO"):
                    sym = s
                    break
        except Exception:
            return "", None
    if not sym:
        return "", None
    try:
        r = sess.get(YAHOO_CHART.format(s=sym), timeout=HTTP_TIMEOUT)
        price = r.json()["chart"]["result"][0]["meta"]["regularMarketPrice"]
        syms[name.lower()] = sym
        return sym, float(price)
    except Exception:
        return sym, None


def load_cache() -> dict:
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(data: dict):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


# ----------------------------------------------------------------------------
# Demo data  (FICTIONAL companies, generated relative to today)
# ----------------------------------------------------------------------------
_DEMO_NAMES = ["Nilgiri Meadow Foods", "Sunvale Solar Energy", "Orbitek Systems", "Meghdoot Pharma Labs",
               "Lotus Harbor Logistics", "Vantage Loom Textiles", "PrimeAxis Finserv", "Aurora Circuits",
               "Tarang Hydro Power", "Kesari Agro Chem", "Indus Quill Education", "BlueMango Retail",
               "Sahyadri Realty Works", "Deltabyte Software", "Himal Steelcraft", "Pragati Auto Components",
               "Ganga Bio Therapeutics", "Rudra Cement Mix", "Cobalt Lane Fintech", "Saffron Bay Hotels",
               "Vertex Wind Turbines", "Kaveri Dairy Products", "Zephyr Cloud Data", "Mandala Wellness Care",
               "Ashoka Rail Infra", "Neelam Jewels Retail", "Brahma Packaging", "Quanta Micro Devices",
               "Harappa Spice Foods", "Trident Ports Cargo", "Ekta Housing Finance", "Lumen Diagnostics",
               "Arka Solar Cells", "Pinnacle Tyre Works", "Sagar Aqua Foods", "Omkar Metro Builders",
               "Vidya Learning Tech", "Rasa Beverages", "Ivory Garments", "Falcon Airline Services",
               "Mithila Textile Spinners", "Cedar Semiconductor", "Gully Kitchen Restaurants",
               "Titan Peak Forgings", "Bhoomi Land Developers", "Kohinoor Battery Systems"]


def make_demo_data(today: date) -> List[IPO]:
    rnd = random.Random(2026)
    pre = ["Amber", "Zenith", "Coral", "Lakshya", "Nova", "Sarvam", "Jade", "Kirti", "Meru", "Aster",
           "Tulsi", "Onyx", "Vayu", "Prism", "Ravi", "Indigo", "Talwar", "Opal", "Suvarna", "Delta"]
    suf = ["Foods", "Pharma", "Power", "Infra", "Software", "Textiles", "Finance", "Motors",
           "Chemicals", "Logistics", "Realty", "Retail"]
    names = _DEMO_NAMES[:] + ["{} {}".format(a, b) for a in pre for b in suf]
    rnd.shuffle(names)
    out = []

    def mk(name, od, window, sme, mcap, size, quality, listed):
        cd = od + timedelta(days=window)
        hi = rnd.choice([58, 96, 118, 142, 186, 240, 310, 425, 560, 780, 1020, 1375])
        lo = hi - rnd.choice([3, 5, 8, 10, 12, 15]) if not sme else hi
        o = IPO(name + " (Demo)", od, cd, float(lo), float(hi), "NSE SME" if sme else "NSE, BSE",
                sme, size, mcap, "", "", "", "Demo Lead Manager", None, source="Demo", demo=True)
        if listed:
            o.cmp = round(hi * rnd.uniform(0.6, 1.9), 2)
        base = rnd.uniform(200, 3000) * (0.2 if sme else 1)
        g = {"good": rnd.uniform(1.25, 1.6), "mid": rnd.uniform(1.03, 1.15), "bad": rnd.uniform(0.7, 0.95)}[quality]
        revs = [base, base * g, base * g * g]
        pm = {"good": 0.13, "mid": 0.05, "bad": -0.03}[quality]
        for i, (p, r) in enumerate(zip(["FY 2023-24", "FY 2024-25", "FY 2025-26"], revs)):
            m = pm * (0.6 + 0.2 * i)
            o.financials.append({"period": p, "revenue": round(r, 1), "pat": round(r * m, 1),
                                 "net_worth": round(r * (0.5 + 0.1 * i), 1)})
        if not listed:
            pool = {"good": ["pos", "pos", "pos", "pos", "neu"], "mid": ["pos", "neu", "neu", "neu", "neg"],
                    "bad": ["neg", "neg", "neu", "neg", "pos"]}[quality]
            for i in range(rnd.randint(4, 6)):
                v = rnd.choice(pool)
                word = {"pos": "Subscribe", "neu": "Neutral", "neg": "Avoid"}[v]
                o.opinions.append({"source": "Demo Broker {}".format(chr(65 + i)), "view": word,
                                   "note": "Illustrative sample opinion"})
        o.enriched = True
        return o

    ni = 0
    for back in range(ARCHIVE_MONTHS + 1, 0, -1):
        base = add_months(today.replace(day=1), -back + 1)
        for _ in range(rnd.randint(1, 2)):
            if ni >= len(names):
                break
            od = base.replace(day=rnd.randint(2, 24))
            if od >= today - timedelta(days=8):
                continue
            window = rnd.choice([2, 3, 3, 4, 5])
            out.append(mk(names[ni], od, window, rnd.random() < 0.25, rnd.choice([900, 2500, 6000, 15000, 45000]),
                          rnd.choice([80, 240, 800, 2200]), "mid", True))
            ni += 1
    # deliberately invalid windows (to demonstrate the 12-day rule)
    out.append(mk("Invalid Window Co One", today - timedelta(days=60), 15, False, 5000, 500, "mid", True))
    out.append(mk("Invalid Window Co Two", today + timedelta(days=20), 14, False, 5000, 500, "mid", False))
    plan = [("This Month", 3), ("Next Month", 4), ("Within 6 Months", 5), ("Within 1 Year", 4)]
    quals = ["good", "mid", "bad", "good", "mid"]
    for label, cnt in plan:
        for i in range(cnt):
            if ni >= len(names):
                break
            if label == "This Month":
                od = today + timedelta(days=1 + i * 2)
            elif label == "Next Month":
                od = add_months(today.replace(day=1), 1) + timedelta(days=3 + i * 6)
            elif label == "Within 6 Months":
                od = add_months(today, 2) + timedelta(days=i * 25 + 4)
            else:
                od = add_months(today, 7) + timedelta(days=i * 40 + 3)
            sme = (ni % 5 == 0)
            out.append(mk(names[ni], od, rnd.choice([3, 4, 5]), sme,
                          rnd.choice([1200, 3500, 9000, 22000, 60000, 150000]), rnd.choice([120, 450, 1500, 5200]),
                          quals[(ni + i) % 5], False))
            ni += 1
    return out


# ----------------------------------------------------------------------------
# Background threads (the window never freezes)
# ----------------------------------------------------------------------------
class FetchThread(QThread):
    done = pyqtSignal(object)

    def __init__(self, force_demo=False):
        super().__init__()
        self.force_demo = force_demo

    def run(self):
        result = {"ipos": [], "mode": "DEMO", "note": "", "error": ""}
        today = date.today()
        try:
            if not self.force_demo and requests is not None:
                sess = _session()
                found = []
                for y in (today.year - 2, today.year - 1, today.year):
                    found += fetch_chittorgarh(sess, y)
                found += fetch_nse(sess)
                uniq = {}
                for o in found:
                    uniq.setdefault((o.name.lower(), o.open_date), o)
                if len(uniq) >= 5:
                    result["ipos"] = list(uniq.values())
                    result["mode"] = "LIVE"
                    result["note"] = "Live data loaded from public websites."
                    old = load_cache()
                    for o in result["ipos"]:                       # keep earlier prices
                        for d in old.get("ipos", []):
                            if d.get("name") == o.name and d.get("open_date") == str(o.open_date):
                                o.cmp = d.get("cmp")
                                o.symbol = o.symbol or d.get("symbol", "")
                    save_cache({"saved": str(today), "ipos": [o.to_dict() for o in result["ipos"]],
                                "symbols": old.get("symbols", {})})
                    self.done.emit(result)
                    return
                result["error"] = "Live websites returned no usable IPO table (they may have changed or blocked the request)."
            elif requests is None:
                result["error"] = "The 'requests' library is not installed."
        except Exception as e:                                       # network problems etc.
            result["error"] = "Could not reach the data websites ({}).".format(type(e).__name__)
        cache = load_cache()
        if cache.get("ipos") and not self.force_demo:
            try:
                result["ipos"] = [IPO.from_dict(d) for d in cache["ipos"]]
                result["mode"] = "CACHED"
                result["note"] = "Showing data saved on {}.".format(cache.get("saved", "an earlier run"))
                self.done.emit(result)
                return
            except Exception:
                pass
        result["ipos"] = make_demo_data(today)
        result["mode"] = "DEMO"
        result["note"] = "Showing fictional DEMO data. " + result["error"]
        self.done.emit(result)


class PriceThread(QThread):
    price = pyqtSignal(str, str, float)      # key, symbol, price
    finished_all = pyqtSignal()

    def __init__(self, items):
        super().__init__()
        self.items = items                   # [(key, name, symbol)]
        self.stop = False

    def run(self):
        if requests is None:
            return
        cache = load_cache()
        sess = _session()

        def work(it):
            if self.stop:
                return
            key, name, symbol = it
            sym, p = lookup_price(sess, name, symbol, cache)
            if p is not None and not self.stop:
                self.price.emit(key, sym, p)
        try:
            with ThreadPoolExecutor(max_workers=4) as ex:
                list(ex.map(work, self.items))
        except Exception:
            pass
        cache_now = load_cache()
        cache_now["symbols"] = cache.get("symbols", {})
        save_cache(cache_now)
        self.finished_all.emit()


class DetailThread(QThread):
    done = pyqtSignal(str, object, str)      # key, data, error

    def __init__(self, o: IPO):
        super().__init__()
        self.ipo = o

    def run(self):
        try:
            self.done.emit(self.ipo.key, fetch_detail(self.ipo), "")
        except Exception as e:
            self.done.emit(self.ipo.key, None, "{}".format(type(e).__name__))


# ----------------------------------------------------------------------------
# Custom-painted visual widgets
# ----------------------------------------------------------------------------
class BarChart(QWidget):
    """Grouped bars (e.g. Revenue vs Profit for each year)."""

    def __init__(self):
        super().__init__()
        self.periods, self.series = [], []
        self.setMinimumHeight(230)
        self.setMinimumWidth(200)

    def set_data(self, periods, series):
        self.periods, self.series = periods, series
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor("#FFFFFF"))
        vals = [v for _, vs, _ in self.series for v in vs if v is not None]
        if not vals or not self.periods:
            p.setPen(QColor("#8A94A6"))
            p.drawText(self.rect(), Qt.AlignCenter, "No chart data available")
            return
        left, right, top, bottom = 12, 12, 46, 30
        vmax, vmin = max(max(vals), 0), min(min(vals), 0)
        span = (vmax - vmin) or 1
        ch = h - top - bottom
        y0 = top + ch * (vmax / span)
        gw = (w - left - right) / float(len(self.periods))
        n = len(self.series)
        bw = min(38, gw * 0.7 / max(n, 1))
        p.setPen(QPen(QColor("#DDE3EE"), 1))
        p.drawLine(int(left), int(y0), int(w - right), int(y0))
        f = QFont(self.font())
        f.setPointSize(8)
        p.setFont(f)
        for i, per in enumerate(self.periods):
            gx = left + gw * i + gw / 2 - bw * n / 2
            for j, (label, vs, color) in enumerate(self.series):
                v = vs[i] if i < len(vs) else None
                if v is None:
                    continue
                bh = ch * abs(v) / span
                x = gx + j * bw
                rect = QRectF(x + 2, y0 - bh if v >= 0 else y0, bw - 4, max(bh, 1))
                g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
                c = QColor(color)
                g.setColorAt(0, c.lighter(125))
                g.setColorAt(1, c)
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(g))
                path = QPainterPath()
                path.addRoundedRect(rect, 4, 4)
                p.drawPath(path)
                p.setPen(QColor("#44506A"))
                ty = rect.top() - 14 if v >= 0 else rect.bottom() + 1
                p.drawText(QRectF(x - 8, ty, bw + 12, 13), Qt.AlignCenter, "{:,.0f}".format(v))
            p.setPen(QColor("#5B6780"))
            p.drawText(QRectF(left + gw * i, h - bottom + 6, gw, 16), Qt.AlignCenter, per)
        lx = left + 4
        for label, _, color in self.series:
            p.setBrush(QColor(color))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(lx, 10, 12, 12), 3, 3)
            p.setPen(QColor("#44506A"))
            p.drawText(QRectF(lx + 16, 7, 110, 18), Qt.AlignVCenter | Qt.AlignLeft, label)
            lx += 120


class VerdictGauge(QWidget):
    def __init__(self):
        super().__init__()
        self.score, self.label = 0.0, "Average"
        self.setMinimumSize(230, 150)

    def set_verdict(self, score, label):
        self.score, self.label = score, label
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = min(w / 2.0 - 16, h - 44)
        cx, cy = w / 2.0, h - 34
        rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)
        for start, color in ((120, "#F4A6A0"), (60, "#F8D57E"), (0, "#8EDDB2")):
            pen = QPen(QColor(color), 20)
            pen.setCapStyle(Qt.FlatCap)
            p.setPen(pen)
            p.drawArc(rect, start * 16, 60 * 16)
        frac = max(0.0, min(1.0, (self.score + 4.0) / 8.0))
        import math
        ang = math.radians(180 - frac * 180)
        nx, ny = cx + (r - 6) * math.cos(ang), cy - (r - 6) * math.sin(ang)
        p.setPen(QPen(QColor("#34405A"), 3, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx, cy), QPointF(nx, ny))
        p.setBrush(QColor("#34405A"))
        p.drawEllipse(QPointF(cx, cy), 7, 7)
        f = QFont(self.font())
        f.setPointSize(13)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(VERDICT_COLORS.get(self.label, "#34405A")))
        p.drawText(QRectF(0, cy + 8, w, 26), Qt.AlignCenter, self.label)


class ConsensusBar(QWidget):
    def __init__(self):
        super().__init__()
        self.counts = (0, 0, 0)
        self.setFixedHeight(30)

    def set_counts(self, pos, neu, neg):
        self.counts = (pos, neu, neg)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        tot = float(sum(self.counts))
        w, h = self.width(), self.height()
        if tot == 0:
            p.setPen(QColor("#8A94A6"))
            p.drawText(self.rect(), Qt.AlignLeft | Qt.AlignVCenter, "No broker views published yet")
            return
        x = 0.0
        for c, col, name in zip(self.counts, ("#5CCB8E", "#F2C14E", "#EF7D77"), ("Positive", "Neutral", "Avoid")):
            if not c:
                continue
            seg = w * c / tot
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(col))
            p.drawRoundedRect(QRectF(x, 2, seg - 2, h - 4), 6, 6)
            p.setPen(QColor("#FFFFFF"))
            p.drawText(QRectF(x, 2, seg - 2, h - 4), Qt.AlignCenter, "{} {}".format(name, c))
            x += seg


class WindowBar(QWidget):
    """Visual open -> close timeline with the 12-day limit shown."""

    def __init__(self):
        super().__init__()
        self.days = 0
        self.setFixedHeight(46)

    def set_days(self, d):
        self.days = d
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width() - 20
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#E6ECF8"))
        p.drawRoundedRect(QRectF(10, 16, w, 10), 5, 5)
        frac = min(self.days / float(MAX_WINDOW_DAYS), 1.0)
        g = QLinearGradient(10, 0, 10 + w, 0)
        g.setColorAt(0, QColor("#7BC6FF"))
        g.setColorAt(1, QColor("#B79CFF"))
        p.setBrush(QBrush(g))
        p.drawRoundedRect(QRectF(10, 16, max(w * frac, 10), 10), 5, 5)
        p.setPen(QColor("#5B6780"))
        f = QFont(self.font())
        f.setPointSize(8)
        p.setFont(f)
        p.drawText(QRectF(10, 28, w, 16), Qt.AlignLeft, "Open")
        p.drawText(QRectF(10, 28, w, 16), Qt.AlignRight, "Limit: {} days".format(MAX_WINDOW_DAYS))
        p.drawText(QRectF(10, 0, w, 15), Qt.AlignLeft, "Subscription window: {} day(s)".format(self.days))


# ----------------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------------
MONTH_COLORS = ["#FFE3EC", "#E1F0FF", "#E4F7E8", "#FFF3D1", "#EBE4FA", "#DDF6F6",
                "#FDE6F1", "#EDF7DA", "#FFE9D6", "#E3E8FB", "#DAF3EC", "#FBE4E0"]
BUCKET_COLORS = {"This Month": "#FFD9E4", "Next Month": "#DCEBFF", "Within 6 Months": "#DDF5E3",
                 "Within 1 Year": "#EADFFB"}

STYLE = """
QMainWindow, QWidget#root { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #F3F7FF, stop:0.5 #FBF6FF, stop:1 #F1FBF7); }
QWidget { font-family: 'Segoe UI', 'Helvetica Neue', Arial; font-size: 10pt; color: #2C3550; }
QFrame#header { border-radius: 14px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #7F8CFF, stop:0.45 #6EC6F5, stop:0.8 #74E0C3, stop:1 #FFC978); }
QLabel#title { color: white; font-size: 24pt; font-weight: 700; }
QLabel#subtitle { color: rgba(255,255,255,0.92); font-size: 10pt; }
QLabel#badge { background: rgba(255,255,255,0.9); border-radius: 10px; padding: 3px 12px; font-weight: 700; }
QPushButton { background: white; border: 1px solid #CBD6EE; border-radius: 9px; padding: 7px 14px; font-weight: 600; }
QPushButton:hover { background: #EEF3FF; border-color: #8FA6E8; }
QPushButton:disabled { color: #A6AEC2; }
QPushButton#accent { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #8C7BFF, stop:1 #54B6F0); color: white; border: none; }
QPushButton#accent:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7A68F5, stop:1 #43A5E2); }
QTabWidget::pane { border: 1px solid #DCE4F5; border-radius: 12px; background: rgba(255,255,255,0.75); top: -1px; }
QTabBar::tab { background: #E8EEFB; padding: 9px 22px; margin-right: 4px; border-top-left-radius: 10px;
        border-top-right-radius: 10px; font-weight: 600; color: #55627E; }
QTabBar::tab:selected { background: white; color: #4B5BD6; }
QTabBar::tab:hover { background: #F1F5FF; }
QTreeWidget, QTableWidget { background: white; border: 1px solid #E1E8F5; border-radius: 10px;
        alternate-background-color: #FAFBFF; gridline-color: #EEF2FA; }
QTreeWidget::item { padding: 5px 2px; }
QTreeWidget::item:selected { background: #DCE6FF; color: #2C3550; }
QHeaderView::section { background: #EEF2FF; border: none; padding: 7px; font-weight: 700; color: #4A5878; }
QLineEdit, QComboBox { background: white; border: 1px solid #CBD6EE; border-radius: 8px; padding: 6px 10px; }
QRadioButton { padding: 3px; spacing: 8px; }
QFrame#card { background: white; border: 1px solid #E3E9F6; border-radius: 12px; }
QLabel#cardTitle { font-size: 11.5pt; font-weight: 700; }
QLabel#h1 { font-size: 17pt; font-weight: 700; }
QLabel#muted { color: #7C879E; }
QStatusBar { background: #EEF2FF; color: #4A5878; }
QScrollArea { border: none; background: transparent; }
QGroupBox { font-weight: 700; }
QFrame#pane { background: rgba(255,255,255,0.78); border: 1px solid #DCE4F5; border-radius: 12px; }
QFrame#navbar { background: #F1F4FF; border: none; border-top-left-radius: 12px; border-top-right-radius: 12px;
        border-bottom: 1px solid #DCE4F5; }
QPushButton#back { background: #DDE7FF; border: 1px solid #A9BDF2; color: #33408F; }
QPushButton#back:hover { background: #C9D8FF; }
"""


def fit_table(tbl: QTableWidget):
    """Show every row without inner scroll bars."""
    tbl.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    tbl.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    tbl.horizontalHeader().setFixedHeight(34)
    for r in range(tbl.rowCount()):
        tbl.setRowHeight(r, 30)
    tbl.setFixedHeight(34 + 30 * tbl.rowCount() + 4)


def make_card(title: str, accent: str):
    card = QFrame()
    card.setObjectName("card")
    card.setStyleSheet("QFrame#card { border-left: 6px solid %s; }" % accent)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(16, 12, 16, 14)
    lay.setSpacing(8)
    if title:
        t = QLabel(title)
        t.setObjectName("cardTitle")
        lay.addWidget(t)
    return card, lay


def chip(text: str, bg: str, fg: str = "#2C3550") -> QLabel:
    l = QLabel(text)
    l.setStyleSheet("background:%s; color:%s; border-radius:9px; padding:3px 11px; font-weight:600;" % (bg, fg))
    l.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return l


def friendly_error(parent, title: str, text: str, detail: str = ""):
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Information)
    box.setWindowTitle(title)
    box.setText(text)
    if detail:
        box.setDetailedText(detail)
    box.exec_()


# ----------------------------------------------------------------------------
# Archive tab
# ----------------------------------------------------------------------------
class ArchiveTab(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        top = QHBoxLayout()
        title = QLabel("Archive - IPOs of the last 2 years")
        title.setObjectName("h1")
        top.addWidget(title)
        top.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search company name...")
        self.search.setFixedWidth(260)
        self.search.textChanged.connect(self.apply_search)
        top.addWidget(self.search)
        lay.addLayout(top)
        self.info = QLabel("")
        self.info.setObjectName("muted")
        lay.addWidget(self.info)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(["Opening Date", "Closing Date", "Company Name", "Issue Price", "Current Market Price"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setUniformRowHeights(True)
        hh = self.tree.header()
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        for c in (0, 1, 3, 4):
            hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        lay.addWidget(self.tree, 1)
        self.items: Dict[str, QTreeWidgetItem] = {}
        self.ipo_by_key: Dict[str, IPO] = {}

    def populate(self, ipos: List[IPO]):
        self.tree.clear()
        self.items, self.ipo_by_key = {}, {}
        groups: Dict[Tuple[int, int], List[IPO]] = {}
        for o in ipos:
            groups.setdefault((o.open_date.year, o.open_date.month), []).append(o)
        for idx, ym in enumerate(sorted(groups.keys(), reverse=True)):
            lst = sorted(groups[ym], key=lambda x: x.open_date)
            color = QColor(MONTH_COLORS[(ym[0] * 12 + ym[1]) % len(MONTH_COLORS)])
            g = QTreeWidgetItem(["{}   -   {} IPO{}".format(date(ym[0], ym[1], 1).strftime("%B %Y"),
                                                           len(lst), "" if len(lst) == 1 else "s")])
            g.setFirstColumnSpanned(True)
            f = g.font(0)
            f.setBold(True)
            f.setPointSize(11)
            g.setFont(0, f)
            for c in range(5):
                g.setBackground(c, color)
            self.tree.addTopLevelItem(g)
            for o in lst:
                it = QTreeWidgetItem([fmt_date(o.open_date), fmt_date(o.close_date), o.name,
                                      fmt_money(o.issue_price), "..." if o.cmp is None else fmt_money(o.cmp)])
                for c in (3, 4):
                    it.setTextAlignment(c, Qt.AlignRight | Qt.AlignVCenter)
                g.addChild(it)
                self.items[o.key] = it
                self.ipo_by_key[o.key] = o
                self.color_cmp(o, it)
            g.setExpanded(idx < 3)
        self.info.setText("{} IPOs shown, newest month first. Click a month to expand / collapse.".format(len(ipos)))

    def color_cmp(self, o: IPO, it: QTreeWidgetItem):
        if o.cmp is None or o.issue_price is None:
            return
        col = "#1F9D5B" if o.cmp >= o.issue_price else "#D24B45"
        it.setForeground(4, QBrush(QColor(col)))
        f = it.font(4)
        f.setBold(True)
        it.setFont(4, f)

    def set_price(self, key: str, price: float):
        o, it = self.ipo_by_key.get(key), self.items.get(key)
        if o is None or it is None:
            return
        o.cmp = price
        it.setText(4, fmt_money(price))
        self.color_cmp(o, it)

    def apply_search(self, text: str):
        t = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            g = self.tree.topLevelItem(i)
            vis = 0
            for j in range(g.childCount()):
                c = g.child(j)
                hide = bool(t) and t not in c.text(2).lower()
                c.setHidden(hide)
                vis += 0 if hide else 1
            g.setHidden(vis == 0)
            if t and vis:
                g.setExpanded(True)


# ----------------------------------------------------------------------------
# Upcoming tab (filters + list + rich detail panel)
# ----------------------------------------------------------------------------
class DetailView(QScrollArea):
    """Full-page details of one upcoming IPO."""
    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current: Optional[IPO] = None
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        hb = QHBoxLayout(outer)
        hb.setContentsMargins(10, 6, 10, 10)
        hb.addStretch(1)
        self.host = QWidget()
        self.host.setMaximumWidth(1000)
        self.host.setMinimumWidth(520)
        self.detail_lay = QVBoxLayout(self.host)
        self.detail_lay.setContentsMargins(0, 0, 0, 0)
        self.detail_lay.setSpacing(12)
        hb.addWidget(self.host, 10)
        hb.addStretch(1)
        self.setWidget(outer)

    def show_ipo(self, o: IPO):
        self.current = o
        self.render(o)
        self.verticalScrollBar().setValue(0)

    # ---- detail panel
    def clear_detail(self):
        while self.detail_lay.count():
            w = self.detail_lay.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def show_placeholder(self, text: str):
        self.clear_detail()
        card, lay = make_card("", "#B79CFF")
        l = QLabel(text)
        l.setWordWrap(True)
        l.setObjectName("muted")
        l.setAlignment(Qt.AlignCenter)
        l.setMinimumHeight(140)
        lay.addWidget(l)
        self.detail_lay.addWidget(card)
        self.detail_lay.addStretch()

    def render(self, o: IPO):
        self.clear_detail()
        cap, cap_est = cap_info(o)
        ind, ind_est = infer_industry(o)
        verdict = compute_verdict(o)

        # 1. header
        head = QFrame()
        head.setStyleSheet("QFrame { border-radius: 14px; background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                           "stop:0 #DCD6FF, stop:0.5 #CDE8FF, stop:1 #D3F7E8); }")
        hl = QVBoxLayout(head)
        hl.setContentsMargins(18, 14, 18, 14)
        nm = QLabel(o.name)
        nm.setStyleSheet("font-size:17pt; font-weight:700; background:transparent; color:#2A3358;")
        nm.setWordWrap(True)
        hl.addWidget(nm)
        chips = QHBoxLayout()
        chips.setSpacing(8)
        chips.addWidget(chip(cap + (" (est.)" if cap_est else ""), "#FFFFFF", "#5A48D0"))
        chips.addWidget(chip(ind + (" (est.)" if ind_est else ""), "#FFFFFF", "#1E86B5"))
        chips.addWidget(chip(o.exchange or "Exchange TBA", "#FFFFFF", "#1E9C6B"))
        if o.demo:
            chips.addWidget(chip("DEMO DATA", "#FFE0A8", "#8A5A00"))
        chips.addStretch()
        hl.addLayout(chips)
        self.detail_lay.addWidget(head)

        # 2. key facts
        card, lay = make_card("Issue details", "#5AB0F0")
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        facts = [("Opening date", fmt_date(o.open_date), "#E8F1FF"), ("Closing date", fmt_date(o.close_date), "#FFE9EF"),
                 ("Price band", o.price_band_text, "#E7F8EE"), ("Issue size", fmt_cr(o.issue_size_cr), "#FFF4D9")]
        for i, (k, v, bg) in enumerate(facts):
            box = QFrame()
            box.setStyleSheet("QFrame { background:%s; border-radius:10px; }" % bg)
            bv = QVBoxLayout(box)
            bv.setContentsMargins(12, 8, 12, 8)
            a = QLabel(k)
            a.setStyleSheet("color:#6B7690; font-size:8.5pt; background:transparent;")
            b = QLabel(v)
            b.setStyleSheet("font-weight:700; font-size:11pt; background:transparent;")
            b.setWordWrap(True)
            bv.addWidget(a)
            bv.addWidget(b)
            grid.addWidget(box, i // 2, i % 2)
        lay.addLayout(grid)
        wb = WindowBar()
        wb.set_days((o.close_date - o.open_date).days)
        lay.addWidget(wb)
        if o.lead_manager:
            lm = QLabel("Lead manager(s): " + o.lead_manager)
            lm.setObjectName("muted")
            lm.setWordWrap(True)
            lay.addWidget(lm)
        self.detail_lay.addWidget(card)

        # 3. financial highlights
        card, lay = make_card("Financial highlights", "#F29BC0")
        if o.financials:
            periods = [f["period"] for f in o.financials]
            chart = BarChart()
            chart.set_data(periods, [("Revenue", [f.get("revenue") for f in o.financials], "#6FA8FF"),
                                     ("Profit After Tax", [f.get("pat") for f in o.financials], "#5CCB9B")])
            lay.addWidget(chart)
            rows = [("Revenue", "revenue"), ("Profit After Tax", "pat"), ("Net worth", "net_worth")]
            tbl = QTableWidget(len(rows) + 2, len(periods) + 1)
            tbl.setHorizontalHeaderLabels([""] + periods)
            tbl.verticalHeader().setVisible(False)
            tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
            tbl.setSelectionMode(QAbstractItemView.NoSelection)
            tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            for r, (lab, k) in enumerate(rows):
                tbl.setItem(r, 0, QTableWidgetItem(lab))
                for c, f in enumerate(o.financials):
                    v = f.get(k)
                    it = QTableWidgetItem("-" if v is None else "{:,.1f}".format(v))
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if k == "pat" and v is not None:
                        it.setForeground(QBrush(QColor("#1F9D5B" if v >= 0 else "#D24B45")))
                    tbl.setItem(r, c + 1, it)
            tbl.setItem(3, 0, QTableWidgetItem("Net margin %"))
            tbl.setItem(4, 0, QTableWidgetItem("Revenue growth %"))
            for c, f in enumerate(o.financials):
                m = "-"
                if f.get("pat") is not None and f.get("revenue"):
                    m = "{:.1f}%".format(f["pat"] / f["revenue"] * 100)
                g = "-"
                if c > 0 and f.get("revenue") and o.financials[c - 1].get("revenue"):
                    g = "{:+.1f}%".format((f["revenue"] / o.financials[c - 1]["revenue"] - 1) * 100)
                for rr, txt in ((3, m), (4, g)):
                    it = QTableWidgetItem(txt)
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    tbl.setItem(rr, c + 1, it)
            fit_table(tbl)
            lay.addWidget(tbl)
            note = QLabel("Figures as published by the source (unit normally Rs crore or Rs million - check the prospectus).")
            note.setObjectName("muted")
            note.setWordWrap(True)
            lay.addWidget(note)
        else:
            msg = ("Loading financial data from the source..." if (o.detail_url and not o.enriched and not o.demo)
                   else "Financial data is not published on the source for this IPO yet (the prospectus may not be filed).")
            l = QLabel(msg)
            l.setObjectName("muted")
            l.setWordWrap(True)
            lay.addWidget(l)
        self.detail_lay.addWidget(card)

        # 4. broker opinions
        card, lay = make_card("Opinions - brokers and fund houses", "#F2C14E")
        views = [classify_view(x.get("view", "")) for x in o.opinions]
        cb = ConsensusBar()
        cb.set_counts(views.count("pos"), views.count("neu"), views.count("neg"))
        lay.addWidget(cb)
        if o.opinions:
            tbl = QTableWidget(len(o.opinions), 3)
            tbl.setHorizontalHeaderLabels(["Broker / fund house", "View", "Comment"])
            tbl.verticalHeader().setVisible(False)
            tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
            tbl.setSelectionMode(QAbstractItemView.NoSelection)
            tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            for r, x in enumerate(o.opinions):
                v = classify_view(x.get("view", ""))
                tbl.setItem(r, 0, QTableWidgetItem(x.get("source", "")))
                raw = str(x.get("view", ""))
                vi = QTableWidgetItem(raw if raw.lower() == VIEW_TEXT[v].lower() or raw.lower() in ("subscribe", "neutral", "avoid")
                                      else "{} ({})".format(raw, VIEW_TEXT[v]))
                vi.setBackground(QColor(VIEW_BG[v]))
                tbl.setItem(r, 1, vi)
                tbl.setItem(r, 2, QTableWidgetItem(x.get("note", "")))
            fit_table(tbl)
            lay.addWidget(tbl)
        else:
            msg = ("Loading broker views from the source..." if (o.detail_url and not o.enriched and not o.demo)
                   else "No broker or fund-house view is published for this IPO yet - shown as 'not available'.")
            l = QLabel(msg)
            l.setObjectName("muted")
            l.setWordWrap(True)
            lay.addWidget(l)
        self.detail_lay.addWidget(card)

        # 5. verdict
        card, lay = make_card("Final verdict (opinion only)", VERDICT_COLORS[verdict["label"]])
        row = QHBoxLayout()
        gauge = VerdictGauge()
        gauge.set_verdict(verdict["score"], verdict["label"])
        row.addWidget(gauge, 0)
        col = QVBoxLayout()
        big = QLabel(verdict["label"])
        big.setStyleSheet("font-size:20pt; font-weight:800; color:%s;" % VERDICT_COLORS[verdict["label"]])
        col.addWidget(big)
        col.addWidget(chip("Confidence: " + verdict["confidence"], VERDICT_BG[verdict["label"]]))
        for r in verdict["reasons"]:
            rl = QLabel("\u2022 " + r)
            rl.setWordWrap(True)
            col.addWidget(rl)
        col.addStretch()
        row.addLayout(col, 1)
        lay.addLayout(row)
        disc = QLabel("This verdict is an automated opinion, not financial advice. Do your own research "
                      "before investing (see the 'Sources & Disclaimer' tab).")
        disc.setWordWrap(True)
        disc.setStyleSheet("color:#8A5A00; background:#FFF6DE; border-radius:8px; padding:8px;")
        lay.addWidget(disc)
        self.detail_lay.addWidget(card)
        if o.detail_url:
            src = QLabel('Source page: <a href="{0}">{0}</a>'.format(o.detail_url))
            src.setOpenExternalLinks(True)
            src.setWordWrap(True)
            self.detail_lay.addWidget(src)
        bb = QPushButton("\u2190  Back to the list")
        bb.setObjectName("back")
        bb.setCursor(Qt.PointingHandCursor)
        bb.clicked.connect(self.back_clicked.emit)
        self.detail_lay.addWidget(bb, 0, Qt.AlignLeft)
        self.detail_lay.addStretch()




class UpcomingTab(QWidget):
    """List screen: bucketed IPO list with filters. Click a row to open its details page."""
    open_ipo = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.ipos: List[IPO] = []
        self._ready = False
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 14)
        title = QLabel("Upcoming IPOs - from today onward")
        title.setObjectName("h1")
        root.addWidget(title)

        bar, bl = make_card("", "#8C7BFF")
        row = QHBoxLayout()
        row.setSpacing(14)
        lab = QLabel("Market cap:")
        lab.setStyleSheet("font-weight:700;")
        row.addWidget(lab)
        self.cap_group = QButtonGroup(self)
        self.cap_radios = {}
        for txt in ("All", "Large Cap", "Mid Cap", "Small Cap", "SME"):
            rb = QRadioButton(txt)
            self.cap_group.addButton(rb)
            self.cap_radios[txt] = rb
            row.addWidget(rb)
            rb.toggled.connect(self.refilter)
        self.cap_radios["All"].setChecked(True)
        row.addSpacing(12)
        lab2 = QLabel("Industry:")
        lab2.setStyleSheet("font-weight:700;")
        row.addWidget(lab2)
        self.industry = QComboBox()
        self.industry.addItem("All industries")
        self.industry.addItems(INDUSTRIES)
        self.industry.setMinimumWidth(210)
        self.industry.currentIndexChanged.connect(self.refilter)
        row.addWidget(self.industry)
        row.addStretch()
        self.reset_btn = QPushButton("Show full unfiltered list")
        self.reset_btn.setObjectName("accent")
        self.reset_btn.clicked.connect(self.reset_filters)
        row.addWidget(self.reset_btn)
        bl.addLayout(row)
        root.addWidget(bar)

        self.count_lbl = QLabel("")
        self.count_lbl.setObjectName("muted")
        root.addWidget(self.count_lbl)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels(["Opens", "Closes", "Company", "Price Band", "Cap", "Verdict"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setCursor(Qt.PointingHandCursor)
        hh = self.tree.header()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        for c in (0, 1, 3, 4, 5):
            hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.tree.itemClicked.connect(self.on_click)
        root.addWidget(self.tree, 1)
        self._ready = True

    def selected_cap(self) -> str:
        for k, rb in self.cap_radios.items():
            if rb.isChecked():
                return k
        return "All"

    def reset_filters(self):
        self.cap_radios["All"].setChecked(True)
        self.industry.setCurrentIndex(0)

    def set_ipos(self, ipos: List[IPO]):
        self.ipos = ipos
        self.refilter()

    def style_verdict(self, it, v):
        it.setText(5, v)
        it.setBackground(5, QColor(VERDICT_BG[v]))
        it.setForeground(5, QBrush(QColor(VERDICT_COLORS[v])))
        ff = it.font(5)
        ff.setBold(True)
        it.setFont(5, ff)

    def refilter(self, *_):
        if not self._ready:
            return
        cap = self.selected_cap()
        ind = self.industry.currentText()
        today = date.today()
        self.tree.clear()
        shown = 0
        groups = {b: [] for b in BUCKETS}
        for o in self.ipos:
            if cap != "All" and cap_info(o)[0] != cap:
                continue
            if ind != "All industries" and infer_industry(o)[0] != ind:
                continue
            b = bucket_for(o, today)
            if b:
                groups[b].append(o)
        for b in BUCKETS:
            lst = sorted(groups[b], key=lambda x: x.open_date)
            g = QTreeWidgetItem(["{}   -   {} IPO{}".format(b, len(lst), "" if len(lst) == 1 else "s")])
            g.setFirstColumnSpanned(True)
            f = g.font(0)
            f.setBold(True)
            f.setPointSize(11)
            g.setFont(0, f)
            for c in range(6):
                g.setBackground(c, QColor(BUCKET_COLORS[b]))
            self.tree.addTopLevelItem(g)
            for o in lst:
                it = QTreeWidgetItem([fmt_date(o.open_date), fmt_date(o.close_date), o.name,
                                      o.price_band_text, cap_info(o)[0], ""])
                it.setData(0, Qt.UserRole, o.key)
                self.style_verdict(it, compute_verdict(o)["label"])
                g.addChild(it)
                shown += 1
            g.setExpanded(True)
        total = len([o for o in self.ipos if bucket_for(o, today)])
        self.count_lbl.setText("{} upcoming IPO{} match the current filters (of {} total).  "
                               "Click any IPO to open its full details page.".format(
                                   shown, "" if shown == 1 else "s", total))

    def on_click(self, item, col):
        key = item.data(0, Qt.UserRole)
        if not key:
            return
        for o in self.ipos:
            if o.key == key:
                self.open_ipo.emit(o)
                return

    def refresh_row(self, o: IPO):
        it = self.tree.findItems(o.name, Qt.MatchExactly | Qt.MatchRecursive, 2)
        for i in it:
            self.style_verdict(i, compute_verdict(o)["label"])


# ----------------------------------------------------------------------------
# Sources & disclaimer tab
# ----------------------------------------------------------------------------
class SourcesTab(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        tb = QTextBrowser()
        tb.setOpenExternalLinks(True)
        h = ["<h2 style='color:#4B5BD6'>Sources</h2><table cellpadding='6' width='100%'>"]
        for i, (n, u, use) in enumerate(SOURCES):
            bg = ["#EAF2FF", "#FFF0F5", "#EAF9EF", "#FFF6DD", "#F0EAFF"][i % 5]
            h.append("<tr style='background:%s'><td><b>%s</b><br><a href='%s'>%s</a></td><td>%s</td></tr>" % (bg, n, u, u, use))
        h.append("</table><h2 style='color:#1E9C6B'>Brokers, fund houses and institutions whose views may appear</h2><p>")
        h.append(" &nbsp;&#8226;&nbsp; ".join("<b>%s</b> <i>(%s)</i>" % (n, t) for n, t in BROKERS))
        h.append("</p><p><i>%s</i></p>" % BROKER_NOTE)
        h.append("<h2 style='color:#C0392B'>Disclaimer</h2>")
        h.append("<div style='background:#FFF3F1; padding:10px;'>")
        for i, d in enumerate(DISCLAIMER):
            h.append("<p><b>%d.</b> %s</p>" % (i + 1, d))
        h.append("</div><p><b>The verdict is opinion only, not financial advice. Please do your own research "
                 "before investing.</b></p>")
        tb.setHtml("".join(h))
        lay.addWidget(tb)


# ----------------------------------------------------------------------------
# Home page and main window
# ----------------------------------------------------------------------------
class HomePage(QWidget):
    go = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)
        h = QLabel("Welcome to IPO_Tracker")
        h.setObjectName("h1")
        lay.addWidget(h)
        d = QLabel("Choose a section to begin. Use the Back button (or Alt + Left arrow) at any time to return to the previous screen.")
        d.setObjectName("muted")
        d.setWordWrap(True)
        lay.addWidget(d)
        row = QHBoxLayout()
        row.setSpacing(18)
        specs = [("archive", "Archive", "Every IPO of the last two years, month by month, with issue price and current market price.",
                  "#FFD9E8", "#E9D5FF"),
                 ("upcoming", "Upcoming IPOs", "This month, next month, within 6 months and 1 year - with financials, broker views and a verdict.",
                  "#D3ECFF", "#C9F5E4"),
                 ("sources", "Sources & Disclaimer", "Websites and brokers cited, plus the important disclaimer.",
                  "#FFF0BF", "#FFD9C2")]
        for name, title, desc, c1, c2 in specs:
            b = QPushButton()
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(190)
            b.setStyleSheet("QPushButton { text-align:left; border:1px solid #DCE4F5; border-radius:18px; "
                            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 %s, stop:1 %s); }"
                            "QPushButton:hover { border:2px solid #7F8CFF; }" % (c1, c2))
            bl = QVBoxLayout(b)
            bl.setContentsMargins(22, 18, 22, 18)
            t = QLabel(title)
            t.setStyleSheet("font-size:17pt; font-weight:800; color:#2A3358; background:transparent;")
            t.setAttribute(Qt.WA_TransparentForMouseEvents)
            x = QLabel(desc)
            x.setWordWrap(True)
            x.setStyleSheet("font-size:10.5pt; color:#46526F; background:transparent; font-weight:400;")
            x.setAttribute(Qt.WA_TransparentForMouseEvents)
            go = QLabel("Open  \u2192")
            go.setStyleSheet("font-weight:700; color:#4B5BD6; background:transparent;")
            go.setAttribute(Qt.WA_TransparentForMouseEvents)
            bl.addWidget(t)
            bl.addWidget(x)
            bl.addStretch()
            bl.addWidget(go)
            b.clicked.connect(lambda _=False, n=name: self.go.emit(n))
            row.addWidget(b)
        lay.addLayout(row)
        self.stats = QLabel("")
        self.stats.setWordWrap(True)
        self.stats.setStyleSheet("background:#EEF2FF; border-radius:10px; padding:10px 14px; color:#3B4770;")
        lay.addWidget(self.stats)
        lay.addStretch()

    def set_stats(self, archive_n, upcoming_n, rejected_n, mode, note):
        self.stats.setText("<b>Data mode: {}</b> &nbsp;|&nbsp; {} archive IPOs &nbsp;|&nbsp; {} upcoming IPOs &nbsp;|&nbsp; "
                           "{} rejected by the {}-day rule<br><span style='color:#6B7690'>{}</span>".format(
                               mode, archive_n, upcoming_n, rejected_n, MAX_WINDOW_DAYS, note))


class MainWindow(QMainWindow):
    TITLES = {"home": "Home", "archive": "Archive", "upcoming": "Upcoming IPOs",
              "detail": "IPO details", "sources": "Sources & Disclaimer"}

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1400, 860)
        self.rejected: List[Tuple[IPO, str]] = []
        self.fetch_thread = None
        self.price_thread = None
        self.detail_threads = []
        self.mode = "..."
        self.history: List[str] = []
        self.current = "home"
        self.titles = dict(self.TITLES)
        self.screens: Dict[str, int] = {}
        self.back_btns: Dict[str, QPushButton] = {}
        self.crumbs: Dict[str, QLabel] = {}

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(16, 14, 16, 8)
        lay.setSpacing(12)

        header = QFrame()
        header.setObjectName("header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(22, 14, 22, 14)
        tcol = QVBoxLayout()
        t = QLabel(APP_NAME)
        t.setObjectName("title")
        st = QLabel("Track Indian IPOs - archive, upcoming issues, financials and opinions")
        st.setObjectName("subtitle")
        tcol.addWidget(t)
        tcol.addWidget(st)
        hl.addLayout(tcol)
        hl.addStretch()
        self.badge = QLabel("Loading...")
        self.badge.setObjectName("badge")
        hl.addWidget(self.badge)
        self.rej_btn = QPushButton("Rejected (0)")
        self.rej_btn.clicked.connect(self.show_rejected)
        hl.addWidget(self.rej_btn)
        self.csv_btn = QPushButton("Import CSV")
        self.csv_btn.clicked.connect(self.import_csv)
        hl.addWidget(self.csv_btn)
        self.refresh_btn = QPushButton("Refresh data")
        self.refresh_btn.setObjectName("accent")
        self.refresh_btn.clicked.connect(self.refresh)
        hl.addWidget(self.refresh_btn)
        lay.addWidget(header)

        self.stack = QStackedWidget()
        self.home = HomePage()
        self.home.go.connect(self.go)
        self.archive = ArchiveTab()
        self.upcoming = UpcomingTab()
        self.upcoming.open_ipo.connect(self.open_ipo)
        self.detail = DetailView()
        self.detail.back_clicked.connect(self.back)
        self.sources = SourcesTab()
        self.add_screen("home", self.home)
        self.add_screen("archive", self.archive)
        self.add_screen("upcoming", self.upcoming)
        self.add_screen("detail", self.detail)
        self.add_screen("sources", self.sources)
        lay.addWidget(self.stack, 1)

        foot = QLabel("Verdicts are opinion only - not financial advice. Always do your own research before investing.")
        foot.setAlignment(Qt.AlignCenter)
        foot.setObjectName("muted")
        lay.addWidget(foot)
        QShortcut(QKeySequence("Alt+Left"), self, activated=self.back)
        self.statusBar().showMessage("Starting...")
        self.go("home", record=False)
        QTimer.singleShot(250, self.refresh)

    # ---- navigation with a history so 'Back' returns to the previous screen
    def add_screen(self, name: str, widget: QWidget):
        pane = QFrame()
        pane.setObjectName("pane")
        v = QVBoxLayout(pane)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        if name != "home":
            bar = QFrame()
            bar.setObjectName("navbar")
            h = QHBoxLayout(bar)
            h.setContentsMargins(14, 8, 14, 8)
            back = QPushButton("\u2190  Back")
            back.setObjectName("back")
            back.setCursor(Qt.PointingHandCursor)
            back.clicked.connect(self.back)
            home = QPushButton("\u2302  Home")
            home.setCursor(Qt.PointingHandCursor)
            home.clicked.connect(lambda: self.go("home"))
            crumb = QLabel("")
            crumb.setObjectName("muted")
            h.addWidget(back)
            h.addWidget(home)
            h.addSpacing(10)
            h.addWidget(crumb, 1)
            v.addWidget(bar)
            self.back_btns[name] = back
            self.crumbs[name] = crumb
        v.addWidget(widget, 1)
        self.screens[name] = self.stack.addWidget(pane)

    def go(self, name: str, record: bool = True):
        if name == "home":
            self.history = []
        elif record and name != self.current:
            self.history.append(self.current)
            if len(self.history) > 30:
                self.history = self.history[-30:]
        self.current = name
        self.stack.setCurrentIndex(self.screens[name])
        if name in self.back_btns:
            prev = self.history[-1] if self.history else "home"
            self.back_btns[name].setText("\u2190  Back to " + self.titles.get(prev, "previous screen"))
            trail = self.history[-3:] + [name]
            self.crumbs[name].setText("  \u203a  ".join(self.titles.get(x, x) for x in trail))

    def back(self):
        if self.current == "home":
            return
        prev = self.history.pop() if self.history else "home"
        if prev == "detail" and self.detail.current is None:
            prev = "upcoming"
        self.go(prev, record=False)

    def open_ipo(self, o: IPO):
        self.titles["detail"] = o.name
        self.detail.show_ipo(o)
        self.go("detail")
        if o.detail_url and not o.enriched and not o.demo:
            t = DetailThread(o)
            t.done.connect(self.on_detail)
            self.detail_threads.append(t)
            t.start()

    def on_detail(self, key, data, error):
        for o in self.upcoming.ipos:
            if o.key != key:
                continue
            o.enriched = True
            if data:
                if data.get("financials"):
                    o.financials = data["financials"]
                if data.get("opinions"):
                    o.opinions = data["opinions"]
                if data.get("market_cap_cr"):
                    o.market_cap_cr = data["market_cap_cr"]
            self.upcoming.refresh_row(o)
            if self.detail.current is o and self.current == "detail":
                pos = self.detail.verticalScrollBar().value()
                self.detail.render(o)
                self.detail.verticalScrollBar().setValue(pos)
            break

    # ---- data flow
    def refresh(self, force_demo=False):
        if self.fetch_thread is not None and self.fetch_thread.isRunning():
            return
        self.refresh_btn.setEnabled(False)
        self.badge.setText("Loading...")
        self.statusBar().showMessage("Fetching IPO data - please wait...")
        self.fetch_thread = FetchThread(force_demo=force_demo is True)
        self.fetch_thread.done.connect(self.on_fetched)
        self.fetch_thread.start()

    def on_fetched(self, result):
        self.refresh_btn.setEnabled(True)
        try:
            self.apply_data(result["ipos"], result["mode"], result.get("note", ""))
        except Exception:
            friendly_error(self, "Something went wrong",
                           "The data was received but could not be displayed. Showing demo data instead.",
                           traceback.format_exc())
            self.apply_data(make_demo_data(date.today()), "DEMO", "Fallback after a display error.")

    def apply_data(self, ipos: List[IPO], mode: str, note: str):
        today = date.today()
        self.mode = mode
        valid, self.rejected = [], []
        for o in ipos:
            ok, why = validate_window(o)
            (valid.append(o) if ok else self.rejected.append((o, why)))
        start = add_months(today, -ARCHIVE_MONTHS)
        archive = [o for o in valid if o.close_date < today and o.open_date >= start]
        upcoming = [o for o in valid if o.close_date >= today]
        self.archive.populate(archive)
        self.upcoming.set_ipos(upcoming)
        if self.current == "detail":                       # the shown IPO object is now stale
            self.detail.current = None
            self.history = [h for h in self.history if h != "detail"]
            self.go("upcoming", record=False)
        colors = {"LIVE": "#1E9C6B", "CACHED": "#B7791F", "DEMO": "#C0392B", "IMPORTED": "#4B5BD6"}
        self.badge.setText("Data: " + mode)
        self.badge.setStyleSheet("color:%s;" % colors.get(mode, "#333"))
        self.rej_btn.setText("Rejected ({})".format(len(self.rejected)))
        self.home.set_stats(len(archive), len(upcoming), len(self.rejected), mode, note)
        self.statusBar().showMessage("{}  |  {} archive, {} upcoming, {} rejected by the {}-day rule.".format(
            note, len(archive), len(upcoming), len(self.rejected), MAX_WINDOW_DAYS))
        if mode == "DEMO":
            friendly_error(self, "Demo mode",
                           "Live IPO data could not be loaded, so the app is showing FICTIONAL demo data "
                           "to demonstrate the screens.\n\nCheck your internet connection and press "
                           "'Refresh data', or use 'Import CSV' to load your own list.",
                           note)
        if mode in ("LIVE", "CACHED", "IMPORTED") and requests is not None:
            todo = [(o.key, o.name, o.symbol) for o in archive if o.cmp is None]
            if todo:
                if self.price_thread is not None:
                    self.price_thread.stop = True
                self.price_thread = PriceThread(todo)
                self.price_thread.price.connect(self.on_price)
                self.price_thread.start()

    def on_price(self, key, symbol, price):
        self.archive.set_price(key, price)
        o = self.archive.ipo_by_key.get(key)
        if o is not None and symbol:
            o.symbol = symbol

    def show_rejected(self):
        if not self.rejected:
            friendly_error(self, "Rejected IPOs", "No IPO was rejected - every IPO passed the {}-day rule.".format(MAX_WINDOW_DAYS))
            return
        lines = ["{}  ({} to {}) - {}".format(o.name, fmt_date(o.open_date), fmt_date(o.close_date), why)
                 for o, why in self.rejected]
        friendly_error(self, "Rejected IPOs",
                       "{} IPO(s) were rejected because the opening-to-closing gap is not valid "
                       "(maximum {} days). Open 'Show Details' for the list.".format(len(self.rejected), MAX_WINDOW_DAYS),
                       "\n".join(lines))

    def import_csv(self):
        friendly_error(self, "Import CSV",
                       "Choose a CSV file with these column headings (only the first three are compulsory):\n\n"
                       "name, open_date, close_date, price_low, price_high, exchange, issue_size_cr, "
                       "market_cap_cr, industry, cmp, symbol\n\n"
                       "Dates like 25-Mar-2026 or 2026-03-25 are accepted. Write SME in 'exchange' for SME issues.")
        path, _ = QFileDialog.getOpenFileName(self, "Choose CSV file", "", "CSV files (*.csv)")
        if not path:
            return
        try:
            out = []
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    row = {norm_key(k): v for k, v in row.items() if k}
                    od, cd = parse_date(row.get("opendate")), parse_date(row.get("closedate"))
                    name = (row.get("name") or "").strip()
                    if not name or not od:
                        continue
                    def num(k):
                        n = numbers_in(row.get(k, ""))
                        return n[0] if n else None
                    ex = (row.get("exchange") or "").strip()
                    out.append(IPO(name, od, cd or od, num("pricelow"), num("pricehigh") or num("pricelow"), ex,
                                   "sme" in ex.lower(), num("issuesizecr"), num("marketcapcr"),
                                   (row.get("industry") or "").strip(), (row.get("symbol") or "").strip(),
                                   "", "", num("cmp"), source="CSV"))
            if not out:
                friendly_error(self, "Import CSV", "No usable rows were found. Please check the column headings.")
                return
            self.apply_data(out, "IMPORTED", "Imported {} rows from {}.".format(len(out), os.path.basename(path)))
        except Exception as e:
            friendly_error(self, "Import CSV", "The file could not be read. Please check that it is a valid CSV file.",
                           traceback.format_exc())

    def closeEvent(self, ev):
        try:
            if self.price_thread is not None:
                self.price_thread.stop = True
            for t in [self.fetch_thread, self.price_thread] + self.detail_threads:
                if t is not None and t.isRunning():
                    t.wait(1500)
        except Exception:
            pass
        ev.accept()


# ----------------------------------------------------------------------------
def main():
    def hook(etype, value, tb):
        detail = "".join(traceback.format_exception(etype, value, tb))
        try:
            friendly_error(None, "Oops - something unexpected happened",
                           "IPO_Tracker hit a problem but is still running. If it keeps happening, "
                           "press 'Refresh data' or restart the program.", detail)
        except Exception:
            print(detail)
    sys.excepthook = hook
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    except Exception:
        pass
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    win = MainWindow()
    win.show()
    app.exec_()


if __name__ == "__main__":
    main()
