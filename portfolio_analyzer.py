#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PORTFOLIO ANALYZER  -  Indian listed equities            (version 2)
=====================================================================

What it does
------------
1. Reads your holdings file (Excel / CSV) from any broker or your own sheet,
   and finds Script Name / Symbol, ISIN, Quantity and Cost wherever they are.
2. Asks for the Name of the Entity and the Valuation Date.
3. Identifies every script (NSE main board, NSE SME, BSE, ETFs), fetches a
   missing ISIN, and - when a script is not found - searches by company
   name (renamed / T2T / SME / merged scripts) on NSE, BSE, Yahoo Finance
   and the web.
4. Prices as on the VALUATION DATE (not today): the closing price on or
   before that date, and the WEEKLY CLOSING PRICE of each of the 12 weeks
   before it. A script listed after the valuation date is shown as
   "Not listed as on valuation date".
5. Reads key data from Screener.in for each company and (with a Claude API
   key) researches it on the web - financials, promoter, legal / SEBI /
   case law, industry, news and social-media sentiment.
6. Portfolio Insights and a PDF named  "<Entity> - Portfolio as on <date>.pdf"
   plus an Excel copy of the numbers.

Errors never stop the run: a script that fails is listed in the report
with the reason, and everything else continues.

Run:  double-click RUN_WINDOWS.bat      (see HOW_TO_RUN.txt)
Check set-up:  double-click RUN_SELFTEST.bat
Disclaimer: For information only. Not investment advice.
"""

import configparser
import datetime as dt
import difflib
import getpass
import html as htmllib
import io
import json
import logging
import math
import os
import re
import sys
import time
import traceback
from pathlib import Path
from urllib.parse import quote

try:                                    # Windows console: never crash on symbols
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

# --------------------------------------------------------------------------
# 0. Package check - friendly message instead of a crash
# --------------------------------------------------------------------------
_MISSING = []
for _pkg, _imp in [("pandas", "pandas"), ("openpyxl", "openpyxl"),
                   ("requests", "requests"), ("matplotlib", "matplotlib"),
                   ("reportlab", "reportlab"), ("pillow", "PIL")]:
    try:
        __import__(_imp)
    except ImportError:
        _MISSING.append(_pkg)
if _MISSING:
    print("\nSome required packages are not installed: " + ", ".join(_MISSING))
    print("Please run this command once, then run the program again:\n")
    print("    python -m pip install -r requirements.txt\n")
    input("Press Enter to close...")
    sys.exit(1)

import pandas as pd
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

try:                                    # optional - used only as a backup source
    import yfinance as yf
    for _n in ("yfinance", "peewee", "urllib3"):
        logging.getLogger(_n).setLevel(logging.CRITICAL)
        logging.getLogger(_n).disabled = True
except Exception:
    yf = None

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"
ISIN_RE = re.compile(r"^IN[A-Z0-9]{10}$")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": UA, "Accept": "*/*",
                     "Accept-Language": "en-US,en;q=0.9"})
PREPARED_BY = "SV Arka Advisors"
NOTES = []          # processing notes (run log only)
EXCEPTIONS = []     # (script, problem) shown in the PDF
_LOGFILE = None


LOG_HOOK = None      # set by the app window to receive log lines
PROGRESS = {"stage": "", "done": 0, "total": 0}


def progress(stage, done=0, total=0):
    PROGRESS.update(stage=stage, done=done, total=total)


def log(msg=""):
    print(msg, flush=True)
    if LOG_HOOK:
        try:
            LOG_HOOK(str(msg))
        except Exception:
            pass
    if _LOGFILE:
        try:
            _LOGFILE.write(str(msg) + "\n")
            _LOGFILE.flush()
        except Exception:
            pass


def note(msg):
    NOTES.append(msg)
    log("   note: " + msg)


def exception(script, problem):
    EXCEPTIONS.append((script, problem))
    log(f"   ! {script}: {problem}")


# --------------------------------------------------------------------------
# 1. Settings
# --------------------------------------------------------------------------
def _yes(v):
    return str(v).strip().lower() in ("yes", "y", "true", "1")


def load_settings():
    cfg = configparser.ConfigParser()
    try:
        cfg.read(BASE_DIR / "config.ini", encoding="utf-8")
    except Exception as e:
        print("config.ini could not be read:", e)
    g = lambda k, d="": cfg.get("SETTINGS", k, fallback=d).strip()
    s = {
        "api_key": g("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", ""),
        "provider": (g("AI_PROVIDER") or "").lower(),
        "model": g("AI_MODEL") or g("CLAUDE_MODEL") or "",
        "input_file": g("PORTFOLIO_FILE", "portfolio.xlsx"),
        "ai_research": _yes(g("AI_RESEARCH", "yes")),
        "max_searches": int(g("MAX_WEB_SEARCHES_PER_STOCK", "6") or 6),
        "refresh": _yes(g("REFRESH_RESEARCH", "no")),
        "entity": g("ENTITY_NAME") or g("INVESTOR_NAME"),
        "benchmark": g("BENCHMARK_SYMBOL", "^NSEI") or "^NSEI",
        "benchmark_name": g("BENCHMARK_NAME", "NIFTY 50") or "NIFTY 50",
        "screener": _yes(g("SCREENER_DATA", "yes")),
        "detail_min_pct": to_number(g("DETAIL_MIN_PERCENT", "1")) if g("DETAIL_MIN_PERCENT", "1") else 1.0,
        "columns": {},
    }
    if s["provider"] not in PROVIDERS:
        s["provider"] = guess_provider(s["api_key"]) or "anthropic"
    s["model"] = s["model"] or DEFAULT_MODELS[s["provider"]]
    s["output_dir"] = g("OUTPUT_FOLDER")
    if cfg.has_section("COLUMNS"):          # optional manual column override
        for k in ("name", "symbol", "isin", "qty", "avg_cost", "total_cost"):
            v = cfg.get("COLUMNS", k, fallback="").strip()
            if v:
                s["columns"][k] = v
    return s


# --------------------------------------------------------------------------
# 2. Small helpers
# --------------------------------------------------------------------------
def norm(text):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%]+", " ", str(text).lower())).strip()


def to_number(v):
    """'1,23,456.50', 'Rs. 450', '(1,200)', '-' -> float or None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return None if (isinstance(v, float) and math.isnan(v)) else float(v)
    t = str(v).strip()
    if t in ("", "-", "--", "nan", "NaN", "None"):
        return None
    neg = t.startswith("(") and t.endswith(")")
    t = re.sub(r"[^0-9.\-]", "", t)
    if t in ("", "-", ".", "-."):
        return None
    try:
        x = float(t)
    except ValueError:
        return None
    return -x if neg else x


def inr(x, dec=0):
    """Indian digit grouping: 12,34,567.89"""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "-"
    neg = x < 0
    x = abs(x)
    s = f"{x:.{dec}f}"
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        whole = head + "," + tail
    out = whole + ("." + frac if frac else "")
    return ("-" if neg else "") + out


def pct(x, dec=1, sign=True):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "-"
    return f"{x * 100:+.{dec}f}%" if sign else f"{x * 100:.{dec}f}%"


def clean_company(name):
    n = norm(name)
    n = re.sub(r"\b(limited|ltd|the|india|ind|co|company|corp|corporation|"
               r"inc|plc|eq|equity|shares?|nse|bse|be|fv|rs|re|sm|st)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def strip_tags(h):
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", h or ""))).strip()


# --------------------------------------------------------------------------
# 3. Read the broker file - any layout
# --------------------------------------------------------------------------
ALIASES = {
    "isin": ["isin", "isin code", "isin no", "isin number", "isin no.", "isin_code"],
    "symbol": ["symbol", "trading symbol", "tradingsymbol", "nse symbol", "nse code",
               "ticker", "stock symbol", "scrip symbol", "nse scrip code", "scrip id",
               "security id", "bse code", "scrip code", "code"],
    "name": ["scrip name", "script name", "stock name", "company name", "company",
             "instrument", "instrument name", "security name", "security",
             "security description", "scrip", "script", "stock", "name",
             "share name", "particulars", "description", "scheme name",
             "isin name", "stock details", "company name and isin", "name of security",
             "name of the security", "name of company", "security name and isin"],
    "qty": ["quantity", "qty", "total quantity", "total qty", "net quantity",
            "net qty", "no of shares", "number of shares", "shares", "units",
            "holding qty", "holding quantity", "current qty", "free qty",
            "available qty", "quantity available", "balance", "current balance",
            "current bal", "curr bal", "closing balance", "closing bal", "total bal",
            "net balance", "holding balance", "demat balance", "total holding", "holding",
            "total balance", "free balance", "beneficiary balance", "holdings",
            "qty held", "quantity held", "position", "free bal", "no of units", "units held"],
    "avg_cost": ["avg cost", "average cost", "avg price", "average price",
                 "avg buy price", "average buy price", "buy avg", "buy average",
                 "avg rate", "average rate", "buy price", "purchase price",
                 "purchase rate", "cost price", "unit cost", "cost per share",
                 "avg cost price", "average cost price", "buy avg price", "rate",
                 "avg trading price", "wap", "avg acquisition price"],
    "total_cost": ["total cost", "buy value", "invested value", "investment value",
                   "invested amount", "invested", "cost value", "purchase value",
                   "amount invested", "investment", "total investment",
                   "buy amount", "acquisition cost", "holding cost",
                   "total buy value", "cost of acquisition", "total invested",
                   "investment amount", "purchase cost", "book value",
                   "total purchase value", "net investment"],
    "cost_ambiguous": ["cost", "cost rs", "cost inr", "cost amount"],
}
EXCLUDE_WORDS = ("ltp", "current", "market", "close", "closing", "previous", "prev",
                 "pnl", "p l", "gain", "loss", "change", "day", "unrealised",
                 "unrealized", "realised", "realized", "present", "today", "cmp",
                 "value at", "mkt", "pledge", "lien", "discrepant", "long term",
                 "short term", "blocked", "t1", "collateral")


def _match_columns(headers):
    """headers: list of raw header strings -> {field: column index}"""
    nh = [norm(h) for h in headers]
    found = {}
    used = set()
    # pass 1 exact alias match, in alias priority order
    for field, aliases in ALIASES.items():
        for a in aliases:
            na = norm(a)
            for i, h in enumerate(nh):
                if i not in used and h == na:
                    found[field] = i
                    used.add(i)
                    break
            if field in found:
                break
    # pass 2 'contains' matching for remaining fields (guarded)
    contains_rules = {
        "isin": ["isin"],
        "qty": ["qty", "quantity", "no of shares", "balance", " bal"],
        "avg_cost": ["avg", "average"],
        "total_cost": ["invest", "buy value", "total cost", "purchase value",
                       "acquisition"],
        "name": ["scrip name", "script name", "stock name", "company",
                 "instrument", "security name"],
        "symbol": ["symbol"],
    }
    for field, keys in contains_rules.items():
        if field in found:
            continue
        for i, h in enumerate(nh):
            if i in used or not h:
                continue
            if field != "isin" and any(w in h for w in EXCLUDE_WORDS):
                continue
            if field == "avg_cost" and not any(w in h for w in ("cost", "price", "rate", "buy")):
                continue
            if field == "name" and "isin" in h:
                continue
            if any(k in h for k in keys):
                found[field] = i
                used.add(i)
                break
    return found


def _score(found):
    s = 0
    if "name" in found or "symbol" in found:
        s += 3
    if "qty" in found:
        s += 3
    if "isin" in found:
        s += 2
    if any(k in found for k in ("avg_cost", "total_cost", "cost_ambiguous")):
        s += 2
    return s


def _read_csv_any(path):
    for enc in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            df = pd.read_csv(path, header=None, dtype=object, encoding=enc,
                             sep=None, engine="python", skip_blank_lines=True,
                             on_bad_lines="skip")
            if df.shape[1] > 1:
                return {"csv": df}
        except Exception:
            continue
    raise ValueError("Could not read the file as CSV.")


def _read_raw_sheets(path):
    """Reads by the file's real content, not its extension (brokers often
    save CSV or HTML tables with an .xls / .xlsx name)."""
    with open(path, "rb") as f:
        head = f.read(2048)
    errors = []
    if head.startswith(b"PK"):                               # real .xlsx
        try:
            return pd.read_excel(path, sheet_name=None, header=None, dtype=object,
                                 engine="openpyxl")
        except Exception as e:
            errors.append(f"xlsx: {e}")
    elif head.startswith(b"\xd0\xcf\x11\xe0"):             # real old .xls
        try:
            return pd.read_excel(path, sheet_name=None, header=None, dtype=object,
                                 engine="xlrd")
        except Exception as e:
            errors.append(f"xls: {e}")
    text_head = head.decode("latin-1", "ignore").lstrip().lower()
    if text_head.startswith("<"):                             # HTML table saved as .xls
        try:
            tables = pd.read_html(io.StringIO(Path(path).read_text(encoding="utf-8", errors="ignore")),
                                  header=None)
            out = {}
            for i, t in enumerate(tables):
                head_row = [" ".join(str(x) for x in c if not str(x).startswith("Unnamed")).strip()
                            if isinstance(c, tuple) else ("" if str(c).startswith("Unnamed") else str(c))
                            for c in t.columns]
                out[f"table{i + 1}"] = pd.DataFrame([head_row] + t.astype(object).values.tolist(),
                                                    dtype=object)
            return out
        except Exception as e:
            errors.append(f"html: {e}")
    try:
        sheets = _read_csv_any(path)
        if path.suffix.lower() not in (".csv", ".txt"):
            note(f"'{path.name}' is a CSV (text) file although named {path.suffix}; read as CSV.")
        return sheets
    except Exception as e:
        errors.append(f"csv: {e}")
    raise ValueError("Could not read the holdings file (" + "; ".join(errors)[:300] + ")")


def read_portfolio(path, manual_cols, sheets=None):
    log(f"\nReading holdings file: {path.name}")
    sheets = sheets if sheets is not None else _read_raw_sheets(path)
    best = None
    for sname, raw in sheets.items():
        raw = raw.dropna(how="all").dropna(axis=1, how="all")
        if raw.empty:
            continue
        for r in range(min(len(raw), 40)):
            headers = ["" if pd.isna(x) else str(x) for x in raw.iloc[r].tolist()]
            if manual_cols:
                nh = [norm(h) for h in headers]
                found = {k: nh.index(norm(v)) for k, v in manual_cols.items() if norm(v) in nh}
                if not found:
                    continue
                if "qty" in found:
                    for k, v in _match_columns(headers).items():
                        if k not in found and v not in found.values():
                            found[k] = v
            else:
                found = _match_columns(headers)
            sc = _score(found)
            if best is None or sc > best[0]:
                best = (sc, sname, r, headers, found, raw)
    excel_row = None
    if not best or best[0] < 6:
        raise ValueError(
            "Could not find the holdings table (need at least a stock name / "
            "symbol column and a quantity column). If your broker uses unusual "
            "headings, enter them in the [COLUMNS] section of config.ini.")
    _, sname, hrow, headers, found, raw = best
    excel_row = int(raw.index[hrow]) + 1
    data = raw.iloc[hrow + 1:].reset_index(drop=True)

    # Zerodha-style split quantity columns -> add them up
    nh = [norm(h) for h in headers]
    qty_parts = [i for i, h in enumerate(nh)
                 if h.startswith("quantity available") or h.startswith("quantity discrepant")
                 or h.startswith("quantity pledged")]
    if "qty" in found and nh[found["qty"]] != "quantity" and len(qty_parts) > 1:
        qty_cols = qty_parts
    else:
        qty_cols = [found["qty"]] if "qty" in found else []

    log(f"   sheet '{sname}', header row {excel_row}. Columns used:")
    for k in ("name", "symbol", "isin", "qty", "avg_cost", "total_cost", "cost_ambiguous"):
        if k in found:
            label = " + ".join(headers[i] for i in qty_cols) if k == "qty" else headers[found[k]]
            log(f"     {k:<14}: {label}")
    NOTES.append("Columns read from the holdings file: " + "; ".join(
        f"{k} = '{headers[v]}'" for k, v in found.items()))

    rows = []
    for _, r in data.iterrows():
        cell = lambda k: (None if k not in found or pd.isna(r.iloc[found[k]])
                          else str(r.iloc[found[k]]).strip())
        name = cell("name")
        sym = cell("symbol")
        isin = (cell("isin") or "").upper().replace(" ", "")
        if not name and not sym:
            continue
        label = norm(name or sym)
        if label.startswith(("total", "grand total", "sub total", "subtotal", "net total")):
            continue
        qty = sum(filter(None, [to_number(r.iloc[i]) for i in qty_cols])) if qty_cols else None
        if not qty or qty <= 0:
            continue
        rows.append({
            "name": name or sym,
            "symbol_in_file": sym or (name.strip().upper() if re.fullmatch(
                r"[A-Za-z0-9&][A-Za-z0-9&\-\.]{1,24}", (name or "").strip()) else None),
            "isin": isin if ISIN_RE.match(isin) else "",
            "qty": qty,
            "avg_cost": to_number(cell("avg_cost")),
            "total_cost": to_number(cell("total_cost")),
            "cost_ambiguous": to_number(cell("cost_ambiguous")),
        })
        rows[-1]["amb_lines"] = ([(qty, rows[-1]["cost_ambiguous"])]
                                 if rows[-1]["cost_ambiguous"] is not None else [])
    if not rows:
        raise ValueError("No holdings with a positive quantity were found in the file.")

    # Merge duplicate lines (same ISIN / same name) - e.g. several lots
    merged = {}
    for h in rows:
        key = h["isin"] or clean_company(h["name"])
        if key not in merged:
            merged[key] = dict(h)
            merged[key]["_tc"] = _line_cost(h)
        else:
            m = merged[key]
            m["qty"] += h["qty"]
            m["_tc"] = _add(m["_tc"], _line_cost(h))
            m["amb_lines"] = m["amb_lines"] + h["amb_lines"]
    out = []
    for m in merged.values():
        m["line_cost"] = m.pop("_tc")
        out.append(m)
    log(f"   {len(out)} holdings found.")
    return out


def _add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return a + b


def _line_cost(h):
    if h.get("total_cost") is not None:
        return h["total_cost"]
    if h.get("avg_cost") is not None:
        return h["avg_cost"] * h["qty"]
    return None


def resolve_costs(holdings):
    """When the only cost column is a plain 'Cost', decide whether it is the
    total cost or the per-share cost by comparing with the market price."""
    for h in holdings:
        if h["line_cost"] is not None:
            h["cost"] = h["line_cost"]
            h["cost_basis_note"] = ""
            continue
        lines = h.get("amb_lines") or []
        if not lines:
            h["cost"] = None
            h["cost_basis_note"] = "cost not available in file"
            continue
        if_unit = sum(q * c for q, c in lines)        # 'Cost' = per share
        if_total = sum(c for _, c in lines)           # 'Cost' = total
        cmp_ = h.get("cmp")
        if cmp_ and if_unit > 0 and if_total > 0 and (
                abs(math.log(if_unit / h["qty"] / cmp_)) <
                abs(math.log(if_total / h["qty"] / cmp_))):
            h["cost"] = if_unit
            h["cost_basis_note"] = "'Cost' read as per-share cost"
        else:
            h["cost"] = if_total
            h["cost_basis_note"] = "'Cost' read as total cost"
    notes = {h["cost_basis_note"] for h in holdings if h.get("cost_basis_note")}
    for n in notes:
        NOTES.append(f"Cost column: {n} (decided by comparing with market price).")




# --------------------------------------------------------------------------
# 4. Security masters: NSE (main board + SME + ETF) and BSE
# --------------------------------------------------------------------------
NSE_LISTS = [
    ("NSE", ["https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
             "https://archives.nseindia.com/content/equities/EQUITY_L.csv"]),
    ("NSE-SME", ["https://nsearchives.nseindia.com/emerge/corporates/content/SME_EQUITY_L.csv",
                 "https://archives.nseindia.com/emerge/corporates/content/SME_EQUITY_L.csv"]),
    ("NSE-ETF", ["https://nsearchives.nseindia.com/content/equities/eq_etfseclist.csv"]),
]
MASTER_COLS = ["EXCH", "SYMBOL", "NAME", "ISIN", "LISTED"]


def _pick(cols, *keys):
    for k in keys:
        for c in cols:
            if k in c:
                return c
    return None


def _download_nse_lists():
    frames = []
    for exch, urls in NSE_LISTS:
        for url in urls:
            try:
                r = HTTP.get(url, timeout=25)
                if not (r.ok and "ISIN" in r.text[:800].upper()):
                    continue
                df = pd.read_csv(io.StringIO(r.text), dtype=str)
                df.columns = [re.sub(r"[_\s]+", " ", c).strip().upper() for c in df.columns]
                sc = _pick(df.columns, "SYMBOL")
                nc = _pick(df.columns, "NAME OF COMPANY", "SECURITY NAME", "UNDERLYING", "NAME")
                ic = _pick(df.columns, "ISIN")
                lc = _pick(df.columns, "DATE OF LISTING", "LISTING")
                frames.append(pd.DataFrame({
                    "EXCH": exch, "SYMBOL": df[sc].str.strip(),
                    "NAME": df[nc].str.strip() if nc else df[sc].str.strip(),
                    "ISIN": df[ic].str.strip(),
                    "LISTED": df[lc].str.strip() if lc else ""}))
                break
            except Exception:
                continue
    return frames


def _download_bse_list():
    frames = []
    hdr = {"Referer": "https://www.bseindia.com/", "Origin": "https://www.bseindia.com"}
    for status in ("Active", "Suspended"):
        url = ("https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Scripcode="
               f"&industry=&segment=Equity&status={status}")
        try:
            r = HTTP.get(url, headers=hdr, timeout=30)
            data = r.json() if r.ok else []
            if isinstance(data, dict):
                data = data.get("Table") or data.get("Data") or []
            if not data:
                continue
            df = pd.DataFrame(data)
            cols = {c.upper(): c for c in df.columns}
            code = cols.get("SCRIP_CD") or cols.get("SCRIPCODE")
            name = cols.get("SCRIP_NAME") or cols.get("ISSUER_NAME")
            isin = cols.get("ISIN_NUMBER") or cols.get("ISIN")
            if not (code and isin):
                continue
            frames.append(pd.DataFrame({
                "EXCH": "BSE" if status == "Active" else "BSE-SUSPENDED",
                "SYMBOL": df[code].astype(str).str.strip(),
                "NAME": df[name].astype(str).str.strip() if name else "",
                "ISIN": df[isin].astype(str).str.strip(),
                "LISTED": ""}))
        except Exception:
            continue
    return frames


def load_master():
    """NSE + BSE security list, cached for 7 days."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache = CACHE_DIR / "security_master.csv"
    if cache.exists() and (time.time() - cache.stat().st_mtime) < 7 * 86400:
        try:
            return pd.read_csv(cache, dtype=str).fillna("")
        except Exception:
            pass
    frames = _download_nse_lists() + _download_bse_list()
    if frames:
        m = pd.concat(frames, ignore_index=True)[MASTER_COLS].fillna("")
        m = m[m["SYMBOL"] != ""]
        try:
            m.to_csv(cache, index=False)
        except Exception:
            pass
        got = sorted(set(m["EXCH"]))
        log(f"   Security lists loaded: {', '.join(got)} ({len(m):,} scripts)")
        return m
    if cache.exists():
        return pd.read_csv(cache, dtype=str).fillna("")
    note("NSE / BSE security lists could not be downloaded; Yahoo Finance and web "
         "search were used to identify scripts.")
    return pd.DataFrame(columns=MASTER_COLS)


def _listing_date(text):
    if not text:
        return None
    for f in ("%d-%b-%Y", "%d-%b-%y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d %b %Y", "%d-%m-%y"):
        try:
            return dt.datetime.strptime(str(text).strip(), f).date()
        except ValueError:
            continue
    return None


def master_rows(master, name=None, symbol=None, isin=None):
    """All master rows that match (ISIN first, then symbol, then name)."""
    if master is None or master.empty:
        return []
    out = []
    if isin:
        out += master[master["ISIN"] == isin].to_dict("records")
    for key in filter(None, symbol_bases(symbol)):
        out += master[master["SYMBOL"].str.upper() == key].to_dict("records")
    if name and not out:
        target = clean_company(name)
        if target:
            cleaned = master["NAME"].map(clean_company)
            hit = master[cleaned == target]
            if hit.empty:
                cands = difflib.get_close_matches(target, list(set(cleaned)), n=2, cutoff=0.86)
                if cands:
                    hit = master[cleaned.isin(cands)]
            out += hit.to_dict("records")
    seen, uniq = set(), []
    for r in out:
        k = (r["EXCH"], r["SYMBOL"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    return uniq


def symbol_bases(sym):
    """'REMUS-SM', 'REMUSSM', 'INFY EQ', 'NSE:INFY' -> ['REMUSSM', 'REMUS', ...]"""
    if not sym:
        return []
    s = str(sym).upper().strip()
    s = re.sub(r"^(NSE|BSE)\s*[:\-]\s*", "", s)
    s = re.sub(r"\.(NS|BO)$", "", s)
    out = []
    full = re.sub(r"[^A-Z0-9&\-]", "", s.replace(" ", ""))
    stripped = re.split(r"[\s\-]+(?:EQ|BE|BZ|SM|ST|BL|IL|E1|T|X|XT|Z)$", s)[0]
    stripped = re.sub(r"[^A-Z0-9&\-]", "", stripped.replace(" ", ""))
    for v in (stripped, full):
        if v and v not in out:
            out.append(v)
    m = re.match(r"^([A-Z0-9&]{3,})(SM|ST|BE|BZ|EQ)$", full)
    if m and m.group(1) not in out:
        out.append(m.group(1))
    return out


def yahoo_symbols_for(row):
    if row["EXCH"].startswith("BSE"):
        return [row["SYMBOL"] + ".BO"]
    return [row["SYMBOL"] + ".NS"]


def yahoo_search(query):
    """Yahoo Finance search -> list of (symbol, name) on NSE / BSE."""
    if not query:
        return []
    out = []
    for host in ("query2", "query1"):
        try:
            r = HTTP.get(f"https://{host}.finance.yahoo.com/v1/finance/search",
                         params={"q": query, "quotesCount": 10, "newsCount": 0,
                                 "listsCount": 0, "enableFuzzyQuery": "true"}, timeout=15)
            if r.ok:
                for q in r.json().get("quotes", []):
                    s = q.get("symbol", "")
                    if s.endswith((".NS", ".BO")):
                        out.append((s, q.get("longname") or q.get("shortname") or ""))
                break
        except Exception:
            continue
    if not out and yf is not None:
        try:
            for q in (yf.Search(query, max_results=10, news_count=0).quotes or []):
                s = q.get("symbol", "")
                if s.endswith((".NS", ".BO")):
                    out.append((s, q.get("longname") or q.get("shortname") or ""))
        except Exception:
            pass
    out.sort(key=lambda x: 0 if x[0].endswith(".NS") else 1)
    return out


# --------------------------------------------------------------------------
# 5. Prices as on the valuation date
# --------------------------------------------------------------------------
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def yahoo_chart(symbol, start, end):
    """Daily closes between two dates (inclusive) straight from Yahoo's chart
    service, using exact dates. Returns (Series or None, info dict)."""
    p1 = int(dt.datetime(start.year, start.month, start.day, tzinfo=IST).timestamp())
    p2 = int(dt.datetime(end.year, end.month, end.day, 23, 59, tzinfo=IST).timestamp())
    info = {"error": "no response"}
    for host in ("query1", "query2"):
        for attempt in range(3):
            try:
                r = HTTP.get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{quote(symbol)}",
                             params={"period1": p1, "period2": p2, "interval": "1d",
                                     "includePrePost": "false", "events": "div|split"},
                             timeout=20)
            except requests.RequestException as e:
                info = {"error": f"connection problem ({type(e).__name__})"}
                time.sleep(1)
                continue
            if r.status_code == 429:
                info = {"error": "Yahoo rate limit"}
                time.sleep(3 + 4 * attempt)
                continue
            try:
                j = r.json()
            except ValueError:
                info = {"error": f"HTTP {r.status_code}"}
                break
            ch = j.get("chart") or {}
            if ch.get("error"):
                return None, {"error": (ch["error"] or {}).get("description") or "not found"}
            res = (ch.get("result") or [None])[0]
            if not res:
                return None, {"error": "no data"}
            meta = res.get("meta") or {}
            info = {"meta": meta}
            ftd = meta.get("firstTradeDate")
            if ftd:
                try:
                    info["first_trade"] = dt.datetime.fromtimestamp(int(ftd), IST).date()
                except Exception:
                    pass
            ts = res.get("timestamp") or []
            quotes = ((res.get("indicators") or {}).get("quote") or [{}])[0]
            closes = quotes.get("close") or []
            if not ts or not closes:
                info["error"] = "no trades in the period"
                return None, info
            tzname = meta.get("exchangeTimezoneName") or "Asia/Kolkata"
            idx = (pd.to_datetime(pd.Series(ts), unit="s", utc=True)
                   .dt.tz_convert(tzname).dt.tz_localize(None).dt.normalize())
            s = pd.Series(pd.to_numeric(pd.Series(closes), errors="coerce").values,
                          index=pd.DatetimeIndex(idx)).dropna()
            s = s[~s.index.duplicated(keep="last")].sort_index()
            s = s[s.index <= pd.Timestamp(end)]
            if s.empty:
                info["error"] = "no trades up to the valuation date"
                return None, info
            info["source"] = "Yahoo Finance"
            return s, info
    return None, info


_NSE = {"session": None}


def _nse_session():
    if _NSE["session"] is None:
        s = requests.Session()
        s.headers.update({"User-Agent": UA, "Accept": "application/json, text/plain, */*",
                          "Accept-Language": "en-US,en;q=0.9",
                          "Referer": "https://www.nseindia.com/get-quotes/equity"})
        try:
            s.get("https://www.nseindia.com/", timeout=15)
        except Exception:
            pass
        _NSE["session"] = s
    return _NSE["session"]


def nse_history(symbol, start, end):
    """Backup source: NSE's own historical price service (all series:
    EQ / BE (T2T) / BZ / SM / ST)."""
    s = _nse_session()
    f, t = f"{start:%d-%m-%Y}", f"{end:%d-%m-%Y}"
    sym = quote(symbol)
    urls = [
        f"https://www.nseindia.com/api/historicalOR/generateSecurityWiseHistoricalData?from={f}&to={t}&symbol={sym}&type=priceVolumeDeliverable&series=ALL",
        f"https://www.nseindia.com/api/historical/securityArchives?from={f}&to={t}&symbol={sym}&dataType=priceVolumeDeliverable&series=ALL",
        f"https://www.nseindia.com/api/historical/cm/equity?symbol={sym}&series=[%22EQ%22,%22BE%22,%22BZ%22,%22SM%22,%22ST%22]&from={f}&to={t}",
    ]
    for u in urls:
        try:
            r = s.get(u, timeout=20)
            if not r.ok:
                continue
            data = r.json()
            rows = data.get("data") if isinstance(data, dict) else data
            if not rows:
                continue
            k = rows[0].keys()
            dk = next((x for x in k if "TIMESTAMP" in x.upper() or x.upper() in ("DATE", "CH_DATE")), None)
            ck = next((x for x in k if "CLOS" in x.upper() and "PREV" not in x.upper()), None)
            if not (dk and ck):
                continue
            def _d(v):
                d = parse_date(str(v)[:11])
                return pd.Timestamp(d) if d else pd.to_datetime(v, errors="coerce")
            ser = pd.Series({_d(r_[dk]): to_number(r_[ck]) for r_ in rows}).dropna()
            ser = ser[ser.index.notna()].sort_index()
            ser.index = pd.DatetimeIndex(ser.index).normalize()
            ser = ser[~ser.index.duplicated(keep="last")]
            ser = ser[ser.index <= pd.Timestamp(end)]
            if len(ser):
                return ser, {"source": "NSE"}
        except Exception:
            continue
    return None, {"error": "not found on NSE"}


def nse_industry(symbol):
    """NSE's own industry classification for a symbol ('' if unavailable)."""
    try:
        r = _nse_session().get("https://www.nseindia.com/api/quote-equity?symbol=" + quote(symbol),
                               timeout=15)
        if not r.ok:
            return ""
        j = r.json()
        ii = j.get("industryInfo") or {}
        val = ii.get("industry") or ii.get("sector") or (j.get("info") or {}).get("industry") or ""
        return str(val).strip()
    except Exception:
        return ""


def yf_history(symbol, start, end):
    """Second backup: the yfinance library, with explicit dates."""
    if yf is None:
        return None, {"error": "yfinance not installed"}
    try:
        df = yf.Ticker(symbol).history(start=f"{start:%Y-%m-%d}",
                                       end=f"{end + dt.timedelta(days=1):%Y-%m-%d}",
                                       interval="1d", auto_adjust=False, actions=False,
                                       raise_errors=False)
    except TypeError:
        try:
            df = yf.Ticker(symbol).history(start=f"{start:%Y-%m-%d}",
                                           end=f"{end + dt.timedelta(days=1):%Y-%m-%d}",
                                           interval="1d", auto_adjust=False, actions=False)
        except Exception as e:
            return None, {"error": str(e)[:80]}
    except Exception as e:
        return None, {"error": str(e)[:80]}
    if df is None or df.empty or "Close" not in df:
        return None, {"error": "no data"}
    s = df["Close"].dropna()
    try:
        s.index = s.index.tz_localize(None)
    except (TypeError, AttributeError):
        pass
    s.index = pd.DatetimeIndex(s.index).normalize()
    s = s[s.index <= pd.Timestamp(end)]
    return (s, {"source": "Yahoo (yfinance)"}) if len(s) else (None, {"error": "no data"})


def fetch_prices(symbol, start, end):
    """Try Yahoo chart -> NSE -> yfinance. Returns (series, info)."""
    s, info = yahoo_chart(symbol, start, end)
    if s is not None and len(s):
        return s, info
    first = info.get("first_trade")
    if symbol.endswith(".NS"):
        s2, i2 = nse_history(symbol[:-3], start, end)
        if s2 is not None:
            return s2, i2
    s3, i3 = yf_history(symbol, start, end)
    if s3 is not None:
        return s3, i3
    if first:
        info["first_trade"] = first
    return None, info


def weekly_closes(series, val_date, weeks=12):
    """Weekly closing price = last traded close of each week (Mon-Fri), up to
    the valuation date. Returns base week + 12 weeks (13 rows) or fewer when
    the script was listed later."""
    s = series[series.index <= pd.Timestamp(val_date)]
    if s.empty:
        return None
    per = s.index.to_period("W-FRI")
    g = s.groupby(per)
    out = pd.DataFrame({"date": g.apply(lambda x: x.index[-1]).values,
                        "close": g.last().values})
    return out.tail(weeks + 1).reset_index(drop=True)


def performance(series, val_date, weeks=12):
    wc = weekly_closes(series, val_date, weeks)
    if wc is None or wc.empty:
        return None
    s = series[series.index <= pd.Timestamp(val_date)]
    cmp_ = float(s.iloc[-1])
    base = float(wc["close"].iloc[0])
    window = s[s.index >= wc["date"].iloc[0]]
    daily = window.pct_change().dropna()
    wcl = wc["close"]
    return {
        "cmp": cmp_,
        "price_date": s.index[-1].date(),
        "weekly": wc,
        "ret_12w": (cmp_ / base - 1) if (base and len(wc) > 1) else None,
        "high_12w": float(window.max()) if len(window) else cmp_,
        "low_12w": float(window.min()) if len(window) else cmp_,
        "vol": float(daily.std() * math.sqrt(252)) if len(daily) > 5 else None,
        "max_dd": float((wcl / wcl.cummax() - 1).min()),
        "up_weeks": int((wcl.pct_change().dropna() > 0).sum()),
        "n_weeks": int(len(wcl) - 1),
        "first_date": s.index[0].date(),
    }


# --------------------------------------------------------------------------
# 6. Screener.in snapshot (read directly - no AI involved)
# --------------------------------------------------------------------------
def screener_snapshot(slugs):
    for slug in [x for x in slugs if x]:
        for suffix in ("consolidated/", ""):
            url = f"https://www.screener.in/company/{quote(slug)}/{suffix}"
            try:
                r = HTTP.get(url, timeout=20)
            except Exception:
                continue
            if not r.ok or 'id="top-ratios"' not in r.text:
                continue
            try:
                snap = parse_screener(r.text)
            except Exception:
                continue
            if snap.get("ratios"):
                snap["url"] = url
                return snap
            time.sleep(0.5)
    return None


def parse_screener(t):
    snap = {"ratios": {}, "pros": [], "cons": [], "about": "", "promoters": [],
            "growth": {}, "sector": ""}
    m = re.search(r'<ul id="top-ratios"[^>]*>(.*?)</ul>', t, re.S)
    if m:
        for li in re.findall(r"<li[^>]*>(.*?)</li>", m.group(1), re.S):
            nm = re.search(r'class="name"[^>]*>(.*?)</span>', li, re.S)
            if not nm:
                continue
            name = strip_tags(nm.group(1))
            val = strip_tags(li.replace(nm.group(0), "", 1))
            if name and val:
                snap["ratios"][name] = val.replace("₹", "Rs").strip()
    for key in ("pros", "cons"):
        m = re.search(rf'<div class="{key}"[^>]*>(.*?)</div>', t, re.S)
        if m:
            snap[key] = [strip_tags(x) for x in re.findall(r"<li[^>]*>(.*?)</li>", m.group(1), re.S)][:5]
    m = re.search(r'<div class="[^"]*\babout\b[^"]*"[^>]*>(.*?)</div>', t, re.S)
    if m:
        snap["about"] = strip_tags(m.group(1))[:600]
    sec = re.search(r'<section[^>]*id="shareholding"[^>]*>(.*?)</section>', t, re.S)
    if sec:
        tbl = re.search(r"<table[^>]*>(.*?)</table>", sec.group(1), re.S)
        if tbl:
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tbl.group(1), re.S)
            cells = [[strip_tags(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r_, re.S)]
                     for r_ in rows]
            head = next((c for c in cells if len(c) > 2 and not c[0]), cells[0] if cells else [])
            for c in cells:
                if c and c[0].lower().startswith("promoter"):
                    pairs = list(zip(head[1:], c[1:]))[-5:]
                    snap["promoters"] = [(a, b) for a, b in pairs if b]
                    break
    for tb in re.findall(r'<table class="ranges-table"[^>]*>(.*?)</table>', t, re.S):
        cells = [strip_tags(x) for x in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tb, re.S)]
        if cells:
            title = cells[0]
            pairs = [f"{cells[i].rstrip(':')} {cells[i + 1]}" for i in range(1, len(cells) - 1, 2)]
            snap["growth"][title] = ", ".join(pairs)
    for ttl in ("Broad Sector", "Sector", "Broad Industry", "Industry"):
        m = re.search(rf'title="{ttl}"[^>]*>(.*?)</a>', t, re.S)
        if m and strip_tags(m.group(1)):
            snap["sector"] = strip_tags(m.group(1))
            break
    return snap


def screener_text(snap):
    if not snap:
        return "Not available."
    parts = ["; ".join(f"{k}: {v}" for k, v in snap["ratios"].items())]
    if snap.get("growth"):
        parts.append(" | ".join(f"{k}: {v}" for k, v in snap["growth"].items()))
    if snap.get("promoters"):
        parts.append("Promoter holding: " + ", ".join(f"{a} {b}" for a, b in snap["promoters"]))
    if snap.get("pros"):
        parts.append("Screener pros: " + "; ".join(snap["pros"]))
    if snap.get("cons"):
        parts.append("Screener cons: " + "; ".join(snap["cons"]))
    if snap.get("about"):
        parts.append("About: " + snap["about"])
    return "\n".join(parts)


# --------------------------------------------------------------------------
# 7. Claude API - web research
# --------------------------------------------------------------------------
class ResearchError(Exception):
    pass


PROVIDERS = {"anthropic": "Claude (Anthropic)", "openai": "OpenAI (ChatGPT)",
             "gemini": "Google Gemini"}
PROVIDER_CONSOLE = {"anthropic": "console.anthropic.com", "openai": "platform.openai.com",
                    "gemini": "aistudio.google.com"}
DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-5.5", "gemini": "gemini-3.8-flash"}


def guess_provider(key):
    k = (key or "").strip()
    if k.startswith("sk-ant-"):
        return "anthropic"
    if k.startswith("AIza"):
        return "gemini"
    if k.startswith("sk-"):
        return "openai"
    return ""


class APIHTTPError(Exception):
    def __init__(self, status, message):
        super().__init__(f"HTTP {status}: {message}")
        self.status, self.message = status, f"HTTP {status}: {message}"


def _api_error_text(e, provider="anthropic"):
    """Turn an API exception into a plain-English reason."""
    pname = PROVIDERS.get(provider, provider).split(" (")[0]
    console = PROVIDER_CONSOLE.get(provider, "the provider's console")
    name = type(e).__name__
    msg = getattr(e, "message", None) or str(e)
    low = msg.lower()
    if ("authentication" in name.lower() or "invalid x-api-key" in low or "401" in low
            or "api key not valid" in low or "invalid api key" in low or "incorrect api key" in low
            or "api_key_invalid" in low):
        hint = guess_provider(getattr(e, "_key", ""))
        return (f"The API key was not accepted by {pname}. Check the key, and that the AI provider "
                f"selected matches the key (Claude keys start with sk-ant-, OpenAI keys with sk-, "
                f"Gemini keys with AIza).")
    if "credit balance" in low or "billing" in low or "insufficient_quota" in low or "quota" in low:
        return f"The {pname} account has no credit / quota left - please add credit at {console}."
    if ("web search" in low or "google_search" in low or "web_search" in low) and \
            ("not enabled" in low or "disabled" in low or "not supported" in low):
        return (f"Web search is not available for this {pname} key or model - choose another "
                f"model, or enable web search at {console}.")
    if "permission" in name.lower() or "403" in low:
        return f"This {pname} key does not have permission for the request: " + msg[:200]
    if "notfound" in name.lower() or ("model" in low and "not found" in low) or "404" in low:
        return f"The model is not available for this {pname} key: " + msg[:200]
    if "ratelimit" in name.lower() or "429" in low:
        return f"{pname} rate limit reached - please wait a minute and run again."
    if "connection" in name.lower() or "timeout" in name.lower():
        return f"Could not connect to the {pname} API (internet / firewall)."
    return f"{name}: {msg[:250]}"


class Researcher:
    """Claude (Anthropic). OpenAI and Gemini versions follow below."""
    provider = "anthropic"

    def __init__(self, api_key, model, max_searches):
        try:
            import anthropic
        except ImportError:
            raise ResearchError("The 'anthropic' package is not installed "
                                "(run: python -m pip install -r requirements.txt).")
        self.anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=5, timeout=600)
        self.model = model
        self.max_searches = max(1, max_searches)
        self.use_fetch = True

    # -- low level ------------------------------------------------------
    def _tools(self, searches, fetches):
        tools = []
        if searches:
            tools.append({"type": "web_search_20250305", "name": "web_search",
                          "max_uses": searches,
                          "user_location": {"type": "approximate", "country": "IN",
                                            "timezone": "Asia/Kolkata"}})
        if fetches and self.use_fetch:
            tools.append({"type": "web_fetch_20250910", "name": "web_fetch",
                          "max_uses": fetches, "max_content_tokens": 12000})
        return tools

    def _run(self, prompt, searches=0, fetches=0, max_tokens=6000):
        messages = [{"role": "user", "content": prompt}]
        texts, sources = [], []
        stats = {"searches": 0, "fetches": 0, "errors": []}
        for _ in range(6):                       # handles 'pause_turn'
            kwargs = dict(model=self.model, max_tokens=max_tokens, messages=messages)
            tools = self._tools(searches, fetches)
            if tools:
                kwargs["tools"] = tools
            try:
                resp = self.client.messages.create(**kwargs)
            except Exception as e:
                txt = str(getattr(e, "message", e)).lower()
                if self.use_fetch and fetches and "web_fetch" in txt:
                    self.use_fetch = False          # account without web fetch
                    continue
                raise ResearchError(_api_error_text(e, self.provider))
            for b in resp.content:
                t = getattr(b, "type", "")
                if t == "text":
                    texts.append(b.text)
                    for c in (getattr(b, "citations", None) or []):
                        u = getattr(c, "url", None)
                        if u:
                            sources.append((getattr(c, "title", "") or u, u, True))
                elif t == "server_tool_use":
                    if getattr(b, "name", "") == "web_search":
                        stats["searches"] += 1
                    elif getattr(b, "name", "") == "web_fetch":
                        stats["fetches"] += 1
                elif t == "web_search_tool_result":
                    content = getattr(b, "content", None)
                    if isinstance(content, list):
                        for r in content:
                            u = getattr(r, "url", None)
                            if u:
                                sources.append((getattr(r, "title", "") or u, u, False))
                    elif content is not None:
                        stats["errors"].append("search: " + str(getattr(content, "error_code", "error")))
                elif t == "web_fetch_tool_result":
                    content = getattr(b, "content", None)
                    u = getattr(content, "url", None)
                    if u:
                        sources.append((u, u, False))
                    elif content is not None and getattr(content, "error_code", None):
                        stats["errors"].append("fetch: " + str(content.error_code))
            if resp.stop_reason == "pause_turn":         # continue the same answer
                if messages[-1]["role"] == "assistant":
                    messages[-1]["content"] = list(messages[-1]["content"]) + list(resp.content)
                else:
                    messages.append({"role": "assistant", "content": list(resp.content)})
                continue
            break
        seen, ordered = set(), []
        for cited in (True, False):
            for title, url, c in sources:
                if c == cited and url not in seen:
                    seen.add(url)
                    ordered.append({"title": title, "url": url})
        return "".join(texts), ordered, stats

    def _json(self, text):
        m = re.findall(r"<json>(.*?)</json>", text, re.S)
        body = m[-1] if m else text[text.find("{"): text.rfind("}") + 1]
        body = re.sub(r"^```(?:json)?|```$", "", body.strip()).strip()
        try:
            return json.loads(body, strict=False)
        except Exception:
            body2 = re.sub(r",\s*([}\]])", r"\1", body)
            try:
                return json.loads(body2, strict=False)
            except Exception:
                pass
        # last resort - ask the model (no web) to re-format its own answer
        fix, _, _ = self._run("Convert the following notes into valid JSON with the same "
                              "keys. Reply with JSON only inside <json></json> tags.\n\n"
                              + text[-12000:], max_tokens=4000)
        m = re.findall(r"<json>(.*?)</json>", fix, re.S)
        body = m[-1] if m else fix[fix.find("{"): fix.rfind("}") + 1]
        return json.loads(body, strict=False)

    # -- checks ---------------------------------------------------------
    def preflight(self):
        """Confirms key, model and web search work. Returns a status line."""
        try:
            ids = self.list_models()
        except Exception as e:
            raise ResearchError(_api_error_text(e, self.provider))
        if ids and self.model not in ids:
            alias_ok = any(i.startswith(self.model) for i in ids)
            if not alias_ok:
                pick = pick_default_model(self.provider, ids)
                note(f"Model '{self.model}' is not available for this key; using '{pick}'.")
                self.model = pick
        text, src, st = self._run(
            "Use web search once: what was the latest closing value of the NIFTY 50 "
            "index? Answer in one short line.", searches=1, max_tokens=600)
        if st["errors"] and not src:
            raise ResearchError("Web search returned an error (" + ", ".join(st["errors"]) +
                                "). Check that web search is enabled at "
                                "console.anthropic.com > Settings > Capabilities.")
        if st["searches"] == 0:
            return (f"{PROVIDERS[self.provider]}: key OK, model {self.model} "
                    "(test question answered without searching)")
        return (f"{PROVIDERS[self.provider]}: key OK, model {self.model}, "
                f"web search OK ({len(src)} results)")

    def list_models(self):
        return [m.id for m in self.client.models.list(limit=100)]

    def read_statement(self, kind, data, mime, text, prompt):
        """kind: pdf / image / text. Returns the model's reply text."""
        import base64
        content = []
        if kind == "pdf":
            content.append({"type": "document", "source": {"type": "base64", "media_type": mime,
                            "data": base64.standard_b64encode(data).decode()}})
        elif kind == "image":
            content.append({"type": "image", "source": {"type": "base64", "media_type": mime,
                            "data": base64.standard_b64encode(data).decode()}})
        else:
            content.append({"type": "text", "text": "Holding statement content:\n\n" + text})
        content.append({"type": "text", "text": prompt})
        try:
            resp = self.client.messages.create(model=self.model, max_tokens=16000,
                                               messages=[{"role": "user", "content": content}])
        except Exception as e:
            raise ResearchError(_api_error_text(e, self.provider))
        return "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")

    # -- tasks ----------------------------------------------------------
    def lookup_listing(self, name, symbol, isin, val_date):
        prompt = (
            "Identify this Indian security and its listing status. It may have been "
            "renamed, moved to the trade-to-trade (T2T / BE) segment, listed on the "
            "NSE SME (Emerge) or BSE SME platform, migrated to the main board, "
            "merged / amalgamated, suspended or delisted.\n"
            f"Name as per holding statement: {name}\n"
            f"Symbol as per statement: {symbol or 'n/a'}\nISIN: {isin or 'n/a'}\n"
            f"Valuation date: {val_date:%d-%m-%Y}\n"
            "Reply only with <json>{\"company_name\": \"\", \"isin\": \"\", "
            "\"nse_symbol\": \"\", \"bse_code\": \"\", \"former_names_or_symbols\": [], "
            "\"listing_date\": \"YYYY-MM-DD\", \"status\": \"listed / renamed / merged / "
            "suspended / delisted / not listed / unlisted\", \"note\": \"one line\"}</json>. "
            "Use empty strings when you cannot confirm a value.")
        text, _, _ = self._run(prompt, searches=4, max_tokens=1500)
        return self._json(text)

    def research_stock(self, h, val_date, bench_name):
        perf = h["perf"]
        wk = perf["weekly"]
        wk_txt = ", ".join(f"{d:%d-%b}: {c:.2f}" for d, c in zip(wk["date"], wk["close"]))
        nse = h["symbol"][:-3] if h["symbol"].endswith(".NS") else ""
        urls = []
        if h.get("screener"):
            urls.append(h["screener"]["url"])
        elif nse:
            urls.append(f"https://www.screener.in/company/{nse}/consolidated/")
        urls.append("https://indiankanoon.org/search/?formInput=" + quote(f'"{h["name"]}"'))
        prompt = f"""You are assisting an Indian Chartered Accountant and lawyer in reviewing ONE
listed equity holding. Research THIS company on the web and write a short, factual,
balanced and company-specific note.

Company: {h['name']}
ISIN: {h.get('isin') or 'n/a'} | NSE symbol: {nse or 'n/a'} | Yahoo symbol: {h['symbol']}
Valuation date: {val_date:%d %B %Y}
Closing price on valuation date: Rs {perf['cmp']:.2f}
12-week change (weekly closes): {pct(perf['ret_12w'])}  | {bench_name}: {pct(h.get('bench_ret'))}
Weekly closing prices: {wk_txt}

Data read from Screener.in (current figures):
{screener_text(h.get('screener'))}

Useful pages to open: {' , '.join(urls)}

Steps - use web search for each of these about THIS company, with information up
to the valuation date:
 a) "<company> quarterly results" / annual report - sales, profit, margins, debt.
 b) "<company> promoter holding pledge" - promoter background and changes.
 c) "<company> SEBI order", "<company> NCLT", "<company> High Court / Supreme Court",
    tax or GST disputes - note case names / forums where found (Indian Kanoon link above).
 d) Industry / sector outlook and key regulations.
 e) Recent news, analyst views and social-media (X / Twitter) discussion.
 f) Likely reasons for the 12-week price movement.

Rules: Every statement must be specific to this company and dated where possible.
Do not repeat generic text. Write "Nothing material found" only after searching.
No buy / sell / hold advice and no price targets. Keep each field to 1-3 sentences;
lists up to 4 short items. Use "Rs" instead of the rupee symbol.

Finish with ONLY this JSON inside <json></json> tags:
<json>{{
 "sector": "",
 "industry": "industry as per NSE classification, e.g. Electrical Equipment",
 "business_snapshot": "",
 "financials": "",
 "recent_developments": [],
 "promoter_governance": "",
 "legal_regulatory": "",
 "industry_view": "",
 "market_sentiment": "",
 "price_move_reasons": "",
 "positives": [],
 "watch_points": [],
 "takeaway": "one or two neutral sentences summarising the stock today"
}}</json>"""
        text, sources, st = self._run(prompt, searches=self.max_searches, fetches=3,
                                      max_tokens=8000)
        data = self._json(text)
        data["sources"] = sources[:10]
        data["_searches"] = st["searches"]
        data["_fetches"] = st["fetches"]
        data["_errors"] = st["errors"]
        data["_model"] = self.model
        return data

    def portfolio_commentary(self, summary):
        prompt = ("Below is a summary of an Indian equity portfolio prepared for a "
                  "Chartered Accountant. Write 5 to 7 short, neutral, specific "
                  "observations on allocation, concentration, sector mix, performance "
                  "against the benchmark and points worth reviewing. No buy/sell advice. "
                  'Reply only with <json>{"observations": ["...", "..."]}</json>.\n\n'
                  + json.dumps(summary, indent=1, default=str))
        text, _, _ = self._run(prompt, max_tokens=2000)
        return self._json(text).get("observations", [])


def _version_key(model_id):
    """'gpt-5.5' -> (5, 5); 'gemini-3.8-flash' -> (3, 8); used to put newest first."""
    nums = re.findall(r"\d+(?:\.\d+)?", model_id)
    out = []
    for n in nums[:2]:
        out += [int(x) for x in n.split(".")]
    return tuple(out) or (0,)


def pick_default_model(provider, ids):
    if not ids:
        return DEFAULT_MODELS.get(provider, "")
    if DEFAULT_MODELS.get(provider) in ids:
        return DEFAULT_MODELS[provider]
    if provider == "anthropic":
        return next((i for i in ids if "sonnet" in i), ids[0])
    if provider == "openai":
        main = [i for i in ids if re.match(r"^gpt-\d", i) and not re.search(r"mini|nano|chat|audio", i)]
        return sorted(main or ids, key=_version_key, reverse=True)[0]
    if provider == "gemini":
        fl = [i for i in ids if "flash" in i and "lite" not in i and "preview" not in i] or \
             [i for i in ids if "pro" in i] or ids
        return sorted(fl, key=_version_key, reverse=True)[0]
    return ids[0]


def _http_json(method, url, headers, body=None, timeout=600):
    for attempt in range(4):
        try:
            r = HTTP.request(method, url, headers=headers, json=body, timeout=timeout)
        except requests.RequestException as e:
            if attempt == 3:
                raise
            time.sleep(3 + 3 * attempt)
            continue
        if r.status_code in (429, 500, 502, 503, 529) and attempt < 3:
            time.sleep(5 + 10 * attempt)
            continue
        if r.status_code >= 400:
            try:
                j = r.json()
                err = j.get("error") if isinstance(j, dict) else None
                msg = (err.get("message") if isinstance(err, dict) else str(err or j))
                code = (err.get("code") or err.get("status") or "") if isinstance(err, dict) else ""
                msg = f"{msg} {code}".strip()
            except Exception:
                msg = r.text[:300]
            raise APIHTTPError(r.status_code, msg)
        return r.json()
    raise APIHTTPError(0, "no response")


class OpenAIResearcher(Researcher):
    """OpenAI Responses API with the built-in web search tool."""
    provider = "openai"
    URL = "https://api.openai.com/v1"

    def __init__(self, api_key, model, max_searches):
        self.key, self.model = api_key, model
        self.max_searches = max(1, max_searches)
        self.use_fetch = False

    def _h(self):
        return {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}

    def list_models(self):
        j = _http_json("GET", self.URL + "/models", self._h(), timeout=30)
        ids = [m.get("id", "") for m in j.get("data", [])]
        skip = ("audio", "realtime", "image", "tts", "transcribe", "embedding", "dall", "whisper",
                "moderation", "babbage", "davinci", "search", "instruct", "codex", "sora")
        ids = [i for i in ids if (i.startswith("gpt-") or re.match(r"^o\d", i)) and not any(x in i for x in skip)]
        return sorted(ids, key=_version_key, reverse=True)

    def _call(self, content, searches=0, max_tokens=6000):
        body = {"model": self.model, "input": [{"role": "user", "content": content}],
                "max_output_tokens": max_tokens}
        if searches:
            body["tools"] = [{"type": "web_search",
                              "user_location": {"type": "approximate", "country": "IN",
                                                "timezone": "Asia/Kolkata"}}]
        try:
            j = _http_json("POST", self.URL + "/responses", self._h(), body)
        except APIHTTPError as e:
            if searches and "user_location" in e.message:
                body["tools"] = [{"type": "web_search"}]
                j = _http_json("POST", self.URL + "/responses", self._h(), body)
            else:
                raise
        texts, sources, stats = [], [], {"searches": 0, "fetches": 0, "errors": []}
        for item in j.get("output", []) or []:
            t = item.get("type")
            if t == "web_search_call":
                act = item.get("action") or {}
                if act.get("type") in (None, "search"):
                    stats["searches"] += 1
                else:
                    stats["fetches"] += 1
                if item.get("status") == "failed":
                    stats["errors"].append("search failed")
            elif t == "message":
                for c in item.get("content", []) or []:
                    if c.get("type") == "output_text":
                        texts.append(c.get("text", ""))
                        for a in c.get("annotations", []) or []:
                            if a.get("url"):
                                sources.append({"title": a.get("title") or a["url"], "url": a["url"]})
        seen, uniq = set(), []
        for s_ in sources:
            if s_["url"] not in seen:
                seen.add(s_["url"])
                uniq.append(s_)
        return "".join(texts), uniq, stats

    def _run(self, prompt, searches=0, fetches=0, max_tokens=6000):
        try:
            return self._call([{"type": "input_text", "text": prompt}], searches, max_tokens)
        except Exception as e:
            raise ResearchError(_api_error_text(e, self.provider))

    def read_statement(self, kind, data, mime, text, prompt):
        import base64
        b64 = base64.standard_b64encode(data).decode() if data else ""
        if kind == "pdf":
            part = {"type": "input_file", "filename": "statement.pdf",
                    "file_data": f"data:application/pdf;base64,{b64}"}
        elif kind == "image":
            part = {"type": "input_image", "image_url": f"data:{mime};base64,{b64}"}
        else:
            part = {"type": "input_text", "text": "Holding statement content:\n\n" + text}
        try:
            out, _, _ = self._call([part, {"type": "input_text", "text": prompt}], 0, 16000)
            return out
        except Exception as e:
            raise ResearchError(_api_error_text(e, self.provider))


class GeminiResearcher(Researcher):
    """Google Gemini with Google Search grounding (Interactions API, falling
    back to generateContent)."""
    provider = "gemini"
    URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key, model, max_searches):
        self.key, self.model = api_key, model.replace("models/", "")
        self.max_searches = max(1, max_searches)
        self.use_fetch = False
        self.use_interactions = True

    def _h(self):
        return {"x-goog-api-key": self.key, "Content-Type": "application/json"}

    def list_models(self):
        j = _http_json("GET", self.URL + "/models?pageSize=200", self._h(), timeout=30)
        ids = []
        for m in j.get("models", []):
            name = m.get("name", "").replace("models/", "")
            meth = m.get("supportedGenerationMethods") or []
            if "gemini" in name and (not meth or "generateContent" in meth) and not any(
                    x in name for x in ("embedding", "image", "tts", "live", "audio", "aqa", "vision")):
                ids.append(name)
        return sorted(ids, key=_version_key, reverse=True)

    # Interactions API ----------------------------------------------------
    def _interactions(self, parts, searches, max_tokens):
        body = {"model": self.model, "input": parts, "store": False,
                "generation_config": {"max_output_tokens": max_tokens}}
        if searches:
            body["tools"] = [{"type": "google_search"}]
        j = _http_json("POST", self.URL + "/interactions", self._h(), body)
        texts, sources, stats = [], [], {"searches": 0, "fetches": 0, "errors": []}
        for st in j.get("steps", []) or j.get("outputs", []) or []:
            t = st.get("type", "")
            if t == "google_search_call":
                q = (st.get("arguments") or {}).get("queries") or [1]
                stats["searches"] += len(q)
            elif t == "model_output" or t == "text":
                items = st.get("content") if t == "model_output" else [st]
                for c in items or []:
                    if c.get("type") == "text":
                        texts.append(c.get("text", ""))
                        for a in c.get("annotations", []) or []:
                            if a.get("url"):
                                sources.append({"title": a.get("title") or a["url"], "url": a["url"]})
        if not texts and j.get("output_text"):
            texts.append(j["output_text"])
        return "".join(texts), sources, stats

    # generateContent (older, widely available) -----------------------------
    def _generate(self, parts, searches, max_tokens):
        gparts = []
        for p in parts:
            if p["type"] == "text":
                gparts.append({"text": p["text"]})
            else:
                gparts.append({"inline_data": {"mime_type": p["mime_type"], "data": p["data"]}})
        body = {"contents": [{"role": "user", "parts": gparts}],
                "generationConfig": {"maxOutputTokens": max_tokens}}
        if searches:
            body["tools"] = [{"google_search": {}}]
        j = _http_json("POST", f"{self.URL}/models/{self.model}:generateContent", self._h(), body)
        cand = (j.get("candidates") or [{}])[0]
        texts = [p.get("text", "") for p in (cand.get("content") or {}).get("parts", []) if p.get("text")]
        gm = cand.get("groundingMetadata") or {}
        sources = [{"title": (c.get("web") or {}).get("title") or (c.get("web") or {}).get("uri"),
                    "url": (c.get("web") or {}).get("uri")}
                   for c in gm.get("groundingChunks", []) or [] if (c.get("web") or {}).get("uri")]
        stats = {"searches": len(gm.get("webSearchQueries") or []), "fetches": 0, "errors": []}
        return "".join(texts), sources, stats

    def _call(self, parts, searches=0, max_tokens=6000):
        if self.use_interactions:
            try:
                return self._interactions(parts, searches, max_tokens)
            except APIHTTPError as e:
                if e.status in (400, 404) and "key" not in e.message.lower():
                    self.use_interactions = False      # fall back to generateContent
                else:
                    raise
        return self._generate(parts, searches, max_tokens)

    def _run(self, prompt, searches=0, fetches=0, max_tokens=6000):
        try:
            return self._call([{"type": "text", "text": prompt}], searches, max_tokens)
        except Exception as e:
            raise ResearchError(_api_error_text(e, self.provider))

    def read_statement(self, kind, data, mime, text, prompt):
        import base64
        parts = []
        if kind in ("pdf", "image"):
            parts.append({"type": "document" if kind == "pdf" else "image",
                          "data": base64.standard_b64encode(data).decode(), "mime_type": mime})
        else:
            parts.append({"type": "text", "text": "Holding statement content:\n\n" + text})
        parts.append({"type": "text", "text": prompt})
        try:
            out, _, _ = self._call(parts, 0, 16000)
            return out
        except Exception as e:
            raise ResearchError(_api_error_text(e, self.provider))


def make_researcher(provider, api_key, model, max_searches=6):
    provider = provider or guess_provider(api_key) or "anthropic"
    cls = {"anthropic": Researcher, "openai": OpenAIResearcher, "gemini": GeminiResearcher}[provider]
    return cls(api_key, model or DEFAULT_MODELS[provider], max_searches)


def research_cache_load():
    p = CACHE_DIR / "research_cache.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def research_cache_save(cache):
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        (CACHE_DIR / "research_cache.json").write_text(
            json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


# --------------------------------------------------------------------------
# 8. Inputs: entity name and valuation date
# --------------------------------------------------------------------------
def ask_entity(default=""):
    try:
        raw = input("\nName of the ENTITY (person / company / trust) for this portfolio"
                    + (f" [{default}]" if default else "") + ": ").strip()
    except EOFError:
        raw = ""
    return raw or default


def parse_date(raw):
    fmts = ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y",
            "%d-%b-%y", "%d-%m-%y", "%d/%m/%y", "%d %B %Y", "%d-%B-%Y", "%d%m%Y")
    for f in fmts:
        try:
            return dt.datetime.strptime(raw.strip(), f).date()
        except ValueError:
            continue
    return None


def ask_valuation_date(cli_value=None):
    today = dt.date.today()
    while True:
        if cli_value is not None:
            raw, cli_value = cli_value, None
        else:
            try:
                raw = input(f"\nEnter VALUATION DATE (DD-MM-YYYY), or press Enter for "
                            f"today [{today:%d-%m-%Y}]: ").strip()
            except EOFError:
                raw = ""
        if not raw:
            return today
        d = parse_date(raw)
        if d is None:
            print("   Could not understand the date. Example: 30-09-2026")
        elif d > today:
            print("   The valuation date cannot be in the future. Please re-enter.")
        elif d < dt.date(2000, 1, 1):
            print("   Please enter a date after 2000.")
        else:
            if d.weekday() >= 5:
                print(f"   {d:%d-%m-%Y} is a {d:%A}; the last trading day's closing price "
                      "before it will be used.")
            return d


# --------------------------------------------------------------------------
# 9. Charts
# --------------------------------------------------------------------------
PALETTE = {"ink": "#1F2937", "muted": "#6B7280", "blue": "#1D4E89",
           "green": "#2E7D32", "red": "#C62828", "grid": "#E5E7EB",
           "bench": "#9CA3AF", "head_bg": "#DCE6F2", "head_tx": "#0B2545",
           "band": "#F5F7FA"}


def _style_axes(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color(PALETTE["grid"])
    ax.spines["bottom"].set_color(PALETTE["grid"])
    ax.tick_params(colors=PALETTE["muted"], labelsize=7)
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.6)
    ax.set_axisbelow(True)


def chart_weekly(h, bench_wc, path):
    wc = h["perf"]["weekly"]
    fig, ax = plt.subplots(figsize=(7.2, 2.3), dpi=200)
    base = wc["close"].iloc[0]
    ax.plot(wc["date"], wc["close"] / base * 100, marker="o", ms=3,
            color=PALETTE["blue"], lw=1.6, label=h["short"])
    if bench_wc is not None and len(bench_wc):
        b = bench_wc[bench_wc["date"] >= wc["date"].iloc[0] - pd.Timedelta(days=3)]
        if len(b):
            ax.plot(b["date"], b["close"] / b["close"].iloc[0] * 100, ls="--",
                    color=PALETTE["bench"], lw=1.2, label="Benchmark")
    ax.axhline(100, color=PALETTE["grid"], lw=0.8)
    ax.set_ylabel("Rebased to 100", fontsize=7, color=PALETTE["muted"])
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    _style_axes(ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_bars(labels, values, path, title, color_by_sign=False):
    n = len(labels)
    fig, ax = plt.subplots(figsize=(7.2, max(1.6, 0.24 * n + 0.7)), dpi=200)
    cols = [(PALETTE["green"] if v >= 0 else PALETTE["red"]) if color_by_sign
            else PALETTE["blue"] for v in values]
    y = list(range(n))[::-1]
    ax.barh(y, [v * 100 for v in values], color=cols, height=0.62)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7 if n < 30 else 5.5, color=PALETTE["ink"])
    for yi, v in zip(y, values):
        ax.text(v * 100, yi, f" {v * 100:+.1f}% " if color_by_sign else f" {v * 100:.1f}%",
                va="center", ha="left" if v >= 0 else "right", fontsize=6.3,
                color=PALETTE["ink"])
    ax.axvline(0, color=PALETTE["muted"], lw=0.6)
    ax.set_title(title, fontsize=8.5, color=PALETTE["ink"], loc="left")
    _style_axes(ax)
    ax.grid(axis="x", color=PALETTE["grid"], linewidth=0.6)
    ax.grid(axis="y", visible=False)
    lo, hi = min(0, min(values) * 100), max(0, max(values) * 100)
    pad = (hi - lo) * 0.2 or 1
    ax.set_xlim(lo - (pad if lo < 0 else 0), hi + pad)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# Pie colours validated for colour-blind separation (labels + legend added)
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]
OTHERS_GREY = "#9a9a96"
RETURN_BANDS = [("Loss above 10%", -9e9, -0.10, "#a3302d"),
                ("Loss up to 10%", -0.10, 0.0, "#e66767"),
                ("Gain up to 20%", 0.0, 0.20, "#6da7ec"),
                ("Gain above 20%", 0.20, 9e9, "#1c5cab")]


def _pie(labels, values, cols, path, title, legend_extra=None):
    fig = plt.figure(figsize=(3.6, 4.4), dpi=220)
    ax = fig.add_axes([0.12, 0.40, 0.76, 0.50])          # same donut size in every pie
    total = sum(values) or 1
    wedges, _ = ax.pie(values, colors=cols, startangle=90, counterclock=False,
                       wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 2})
    for w_, v in zip(wedges, values):
        share = v / total
        if share < 0.04:
            continue
        ang = math.radians((w_.theta1 + w_.theta2) / 2)
        r = 0.79
        ax.text(r * math.cos(ang), r * math.sin(ang), f"{share * 100:.0f}%",
                ha="center", va="center", fontsize=7, color="white", fontweight="bold")
    fig.text(0.04, 0.96, title, fontsize=8.5, color=PALETTE["ink"], va="top")
    leg = [f"{l}  {v / total * 100:.1f}%" + (f"  ({legend_extra[i]})" if legend_extra else "")
           for i, (l, v) in enumerate(zip(labels, values))]
    fig.legend(wedges, leg, loc="upper left", bbox_to_anchor=(0.08, 0.37), ncol=1,
               fontsize=6.3, frameon=False, handlelength=1, handleheight=1)
    ax.set_aspect("equal")
    fig.savefig(path)
    plt.close(fig)


def chart_pie_returns(holdings, path):
    labels, values, cols, counts = [], [], [], []
    for lab, lo, hi, col in RETURN_BANDS:
        grp = [h for h in holdings if h["ret"] is not None and lo <= h["ret"] < hi]
        if grp:
            labels.append(lab)
            values.append(sum(h["value"] for h in grp))
            cols.append(col)
            counts.append(f"{len(grp)} stock" + ("s" if len(grp) > 1 else ""))
    if not values:
        return False
    _pie(labels, values, cols, path, "Returns on cost - share of market value", counts)
    return True


def chart_pie_industry(industries, path):
    if not industries:
        return False
    top = industries[:7] if len(industries) <= 8 else industries[:7]
    rest = industries[len(top):]
    labels = [i[0][:30] for i in top]
    values = [i[1] for i in top]
    cols = CATEGORICAL[:len(top)]
    if rest:
        labels.append("Others")
        values.append(sum(i[1] for i in rest))
        cols.append(OTHERS_GREY)
    _pie(labels, values, cols, path, "Industry allocation - share of market value")
    return True


# --------------------------------------------------------------------------
# 10. PDF
# --------------------------------------------------------------------------
FONT, FONT_B = "Helvetica", "Helvetica-Bold"


def setup_fonts():
    """DejaVu Sans (ships with matplotlib) supports the rupee sign and Indian
    names; Helvetica is the fallback."""
    global FONT, FONT_B
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.fonts import addMapping
        fdir = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
        pdfmetrics.registerFont(TTFont("DejaVu", str(fdir / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(fdir / "DejaVuSans-Bold.ttf")))
        addMapping("DejaVu", 0, 0, "DejaVu")
        addMapping("DejaVu", 1, 0, "DejaVu-Bold")
        addMapping("DejaVu", 0, 1, "DejaVu")
        addMapping("DejaVu", 1, 1, "DejaVu-Bold")
        FONT, FONT_B = "DejaVu", "DejaVu-Bold"
    except Exception:
        FONT, FONT_B = "Helvetica", "Helvetica-Bold"


def esc(t):
    t = str(t if t is not None else "")
    if FONT == "Helvetica":
        t = t.replace("₹", "Rs ")
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _img_ratio(path):
    from PIL import Image as PImage
    with PImage.open(path) as im:
        return im.height / im.width


def build_pdf(holdings, unpriced, ins, val_date, settings, out_path, tmp, title):
    S = {
        "title": ParagraphStyle("t", fontName=FONT_B, fontSize=17, leading=21,
                                textColor=colors.HexColor(PALETTE["blue"]), spaceAfter=2),
        "sub": ParagraphStyle("s", fontName=FONT, fontSize=8.5, leading=11,
                              textColor=colors.HexColor(PALETTE["muted"])),
        "h1": ParagraphStyle("h1", fontName=FONT_B, fontSize=12.5, leading=16,
                             textColor=colors.HexColor(PALETTE["blue"]),
                             spaceBefore=4, spaceAfter=5),
        "h2": ParagraphStyle("h2", fontName=FONT_B, fontSize=10, leading=13,
                             textColor=colors.HexColor(PALETTE["ink"]),
                             spaceBefore=8, spaceAfter=3),
        "body": ParagraphStyle("b", fontName=FONT, fontSize=8.4, leading=11.5),
        "small": ParagraphStyle("sm", fontName=FONT, fontSize=7, leading=9.2,
                                textColor=colors.HexColor(PALETTE["muted"])),
        "cell": ParagraphStyle("c", fontName=FONT, fontSize=7, leading=8.8),
        "warn": ParagraphStyle("w", fontName=FONT, fontSize=7.6, leading=10,
                               textColor=colors.HexColor("#8A4B00"),
                               backColor=colors.HexColor("#FFF4E5"),
                               borderPadding=(4, 5, 4, 5)),
        "take": ParagraphStyle("tk", fontName=FONT, fontSize=8.8, leading=12.2,
                               backColor=colors.HexColor("#EEF3FA"),
                               borderPadding=(6, 7, 6, 7),
                               textColor=colors.HexColor(PALETTE["ink"])),
    }
    W = A4[0] - 30 * mm
    story = []
    grid = colors.HexColor("#D1D5DB")
    hbg = colors.HexColor(PALETTE["head_bg"])
    htx = colors.HexColor(PALETTE["head_tx"])

    def table(data, widths, num_cols=(), zebra=True, font=7, head_rows=(0,)):
        coloured = []
        data = [list(r) for r in data]
        for ri, row in enumerate(data):
            for ci, cell in enumerate(row):
                if isinstance(cell, tuple) and cell and cell[0] == "__C__":
                    row[ci] = cell[1]
                    coloured.append(("TEXTCOLOR", (ci, ri), (ci, ri), colors.HexColor(cell[2])))
        t = Table(data, colWidths=widths, repeatRows=1)
        st = [("FONT", (0, 0), (-1, -1), FONT, font),
              ("LINEBELOW", (0, 0), (-1, -1), 0.25, grid),
              ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
              ("TOPPADDING", (0, 0), (-1, -1), 2.4),
              ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4)]
        for r in head_rows:            # light header, dark text: always readable
            st += [("FONT", (0, r), (-1, r), FONT_B, font),
                   ("TEXTCOLOR", (0, r), (-1, r), htx),
                   ("BACKGROUND", (0, r), (-1, r), hbg),
                   ("LINEBELOW", (0, r), (-1, r), 0.8, htx)]
        for c in num_cols:
            st.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
        if zebra:
            for r in range(1, len(data)):
                if r % 2 == 0 and r not in head_rows:
                    st.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor(PALETTE["band"])))
        t.setStyle(TableStyle(st + coloured))
        return t

    def cpct(x):
        if x is None:
            return "-"
        return ("__C__", pct(x), PALETTE["green"] if x >= 0 else PALETTE["red"])

    max_h = A4[1] - 14 * mm - 16 * mm - 60          # frame height less a heading

    def img(path, limit=None):
        """Image scaled to the page width, never taller than the page."""
        lim = limit or max_h
        w, h = W, W * _img_ratio(path)
        if h > lim:
            w, h = w * lim / h, lim
        return Image(str(path), width=w, height=h)

    # ---------------- Page 1: Insights ----------------
    story.append(Paragraph(esc(title), S["title"]))
    story.append(Paragraph(
        f"Valuation date: <b>{val_date:%d %B %Y}</b> &nbsp;|&nbsp; Prepared by "
        f"<b>{PREPARED_BY}</b> on {dt.datetime.now():%d %B %Y} &nbsp;|&nbsp; Amounts in Rs.", S["sub"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Equity Portfolio Insights", S["h1"]))
    kpi = [
        ["Total cost", "Market value", "Unrealised gain / (loss)", "Return on cost"],
        [inr(ins["total_cost"]), inr(ins["total_value"]), inr(ins["pnl"]), pct(ins["ret"])],
        ["Holdings valued", "12-week return (portfolio)",
         f"12-week return ({settings['benchmark_name']})", "Top-3 concentration"],
        [f"{ins['n']} of {ins['n'] + len(unpriced)}", pct(ins["ret_12w"]),
         pct(ins["bench_12w"]), pct(ins["top3"], sign=False)],
    ]
    kt = Table(kpi, colWidths=[W / 4] * 4)
    kt.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), FONT, 7.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(PALETTE["muted"])),
        ("TEXTCOLOR", (0, 2), (-1, 2), colors.HexColor(PALETTE["muted"])),
        ("FONT", (0, 1), (-1, 1), FONT_B, 12), ("FONT", (0, 3), (-1, 3), FONT_B, 12),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F6FA")),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8), ("BOTTOMPADDING", (0, 3), (-1, 3), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4)]))
    story.append(kt)
    story.append(Spacer(1, 8))

    def nm(h, key=None):
        return esc(h["short"]) if h else "-"
    facts = [
        ("Highest allocation", f"{nm(ins['top_alloc'])} - {pct(ins['top_alloc']['weight'], sign=False)} of portfolio"),
        ("Highest return on cost", f"{nm(ins['best_cost'])} ({pct(ins['best_cost']['ret'])})" if ins["best_cost"] else "-"),
        ("Lowest return on cost", f"{nm(ins['worst_cost'])} ({pct(ins['worst_cost']['ret'])})" if ins["worst_cost"] else "-"),
        ("Best in last 12 weeks", f"{nm(ins['best_12w'])} ({pct(ins['best_12w']['perf']['ret_12w'])})" if ins["best_12w"] else "-"),
        ("Weakest in last 12 weeks", f"{nm(ins['worst_12w'])} ({pct(ins['worst_12w']['perf']['ret_12w'])})" if ins["worst_12w"] else "-"),
        ("Holdings in profit / loss", f"{ins['n_profit']} / {ins['n_loss']}"),
        ("Beat the benchmark (12 weeks)", f"{ins['n_beat']} of {ins['n']} holdings"),
    ]
    if ins.get("sectors"):
        s0 = ins["sectors"][0]
        facts.append(("Largest industry", f"{esc(s0[0])} ({pct(s0[1], sign=False)})"))
    if unpriced:
        facts.append(("Not valued", f"{len(unpriced)} script(s), cost {inr(ins['unpriced_cost'])} "
                                    "- see the holdings page"))
    ft = Table([[Paragraph(f"<b>{a}</b>", S["cell"]), Paragraph(b, S["cell"])] for a, b in facts],
               colWidths=[W * 0.32, W * 0.68])
    ft.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.25, grid),
                            ("TOPPADDING", (0, 0), (-1, -1), 3),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.append(ft)
    if ins.get("observations"):
        story.append(Paragraph("Observations", S["h2"]))
        for o in ins["observations"]:
            story.append(Paragraph("&bull; " + esc(o), S["body"]))
    pies = [tmp / n for n in ("pie_returns.png", "pie_industry.png") if (tmp / n).exists()]
    if pies:
        story.append(Spacer(1, 8))
        pw = W / 2 - 4
        cells = []
        for pth in pies:
            ph = pw * _img_ratio(pth)
            sc = min(1.0, (max_h * 0.55) / ph)
            cells.append(Image(str(pth), width=pw * sc, height=ph * sc))
        pt = Table([cells], colWidths=[W / 2] * len(cells))
        pt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(pt)
    story.append(PageBreak())
    story.append(Paragraph("Allocation and 12-week performance", S["h1"]))
    story.append(img(tmp / "alloc.png"))
    story.append(Spacer(1, 6))
    story.append(img(tmp / "ret12.png"))

    # ---------------- Holdings table ----------------
    story.append(PageBreak())
    story.append(Paragraph(f"Equity holdings as on {val_date:%d %B %Y}", S["h1"]))
    hdr = ["#", "Script", "Qty", "Avg cost", "Price", "Price date", "Cost", "Market value",
           "Gain/(loss)", "Return", "Weight", "12 wk"]
    rows = [hdr]
    for i, h in enumerate(holdings, 1):
        rows.append([str(i), Paragraph(esc(h["short"]), S["cell"]), inr(h["qty"], 0),
                     inr(h["avg"], 2) if h["avg"] else "-", inr(h["perf"]["cmp"], 2),
                     f"{h['perf']['price_date']:%d-%m-%y}",
                     inr(h["cost"]) if h["cost"] is not None else "-", inr(h["value"]),
                     inr(h["pnl"]) if h["pnl"] is not None else "-",
                     cpct(h["ret"]), pct(h["weight"], sign=False), cpct(h["perf"]["ret_12w"])])
    rows.append(["", Paragraph("<b>Total</b>", S["cell"]), "", "", "", "", inr(ins["total_cost"]),
                 inr(ins["total_value"]), inr(ins["pnl"]), cpct(ins["ret"]), "100.0%",
                 cpct(ins["ret_12w"])])
    w = [11, 86, 30, 40, 42, 40, 48, 54, 52, 46, 34, 42]
    w = [x * W / sum(w) for x in w]
    t = table(rows, w, num_cols=[2, 3, 4] + list(range(6, 12)), font=6.3)
    t.setStyle(TableStyle([("ALIGN", (5, 0), (5, -1), "CENTER")]))
    t.setStyle(TableStyle([("FONT", (0, -1), (-1, -1), FONT_B, 6.3),
                           ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor(PALETTE["ink"]))]))
    story.append(t)
    if unpriced:
        story.append(Paragraph("Scripts not valued", S["h2"]))
        ur = [["Script", "ISIN", "Qty", "Cost", "Status / reason"]]
        for u in unpriced:
            ur.append([Paragraph(esc(u["name"]), S["cell"]), u.get("isin") or "-",
                       inr(u["qty"]), inr(u.get("cost")) if u.get("cost") else "-",
                       Paragraph(esc(u.get("reason", "")), S["cell"])])
        story.append(table(ur, [W * .27, W * .15, W * .08, W * .11, W * .39], num_cols=(2, 3)))

    nd, nt, thr = settings.get("detail_note", (len(holdings), len(holdings), 0))
    if thr > 0 and nd < nt:
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f"Detailed analysis follows for the {nd} holdings whose invested value is at least "
            f"{thr * 100:g}% of the portfolio; the other {nt - nd} are included in the totals "
            "and charts above.", S["small"]))

    # ---------------- One section per stock ----------------
    for h in holdings:
        if not h.get("detail", True):
            continue
        i = h.get("row_no", 0)
        story.append(PageBreak())
        p = h["perf"]
        r = h.get("research") or {}
        snap = h.get("screener") or {}
        story.append(Paragraph(f"{i}. {esc(h['name'])}", S["h1"])
                     )
        sector = h.get("industry") or ""
        isin_tag = esc(h.get("isin") or "-") + (" (auto-fetched)" if h.get("isin_fetched") else "")
        story.append(Paragraph(
            f"ISIN: <b>{isin_tag}</b> &nbsp;|&nbsp; Symbol: <b>{esc(h['symbol'])}</b>"
            f" &nbsp;|&nbsp; Price source: {esc(h.get('price_source', ''))}"
            + (f" &nbsp;|&nbsp; Industry: {esc(sector)}" if sector else ""), S["sub"]))
        if h.get("match_note"):
            story.append(Paragraph(esc(h["match_note"]), S["warn"]))
        story.append(Spacer(1, 5))
        m = [["Quantity", "Avg cost", "Price", "Cost", "Market value", "Gain/(loss)",
              "Return", "Weight"],
             [inr(h["qty"]), inr(h["avg"], 2) if h["avg"] else "-", inr(p["cmp"], 2),
              inr(h["cost"]) if h["cost"] is not None else "-", inr(h["value"]),
              inr(h["pnl"]) if h["pnl"] is not None else "-", cpct(h["ret"]),
              pct(h["weight"], sign=False)],
             ["12-wk change", f"vs {settings['benchmark_name']}", "12-wk high", "12-wk low",
              "Max fall", "Up weeks", "Volatility", "Price date"],
             [cpct(p["ret_12w"]),
              pct(p["ret_12w"] - h["bench_ret"]) if (p["ret_12w"] is not None and h.get("bench_ret") is not None) else "-",
              inr(p["high_12w"], 2), inr(p["low_12w"], 2), pct(p["max_dd"]),
              f"{p['up_weeks']} of {p['n_weeks']}", pct(p["vol"], sign=False) if p["vol"] else "-",
              f"{p['price_date']:%d-%m-%Y}"]]
        story.append(table(m, [W / 8] * 8, num_cols=range(0, 8), zebra=False, head_rows=(0, 2)))

        wk = p["weekly"]
        recs = []
        for j in range(len(wk)):
            chg = (wk["close"].iloc[j] / wk["close"].iloc[j - 1] - 1) if j else None
            recs.append(["Base" if j == 0 else f"Wk {j}", f"{wk['date'].iloc[j]:%d-%m-%Y}",
                         inr(wk["close"].iloc[j], 2), cpct(chg) if chg is not None else "-"])
        half = math.ceil(len(recs) / 2)
        left, right = recs[:half], recs[half:]
        right += [["", "", "", ""]] * (half - len(right))
        wdata = [["Week", "Week ending", "Weekly close", "Chg", "", "Week", "Week ending",
                  "Weekly close", "Chg"]]
        for a, b in zip(left, right):
            wdata.append(a + [""] + b)
        cw = [W * x for x in (.08, .13, .13, .1, .02, .08, .13, .13, .1)]
        wt = table(wdata, cw, num_cols=(2, 3, 7, 8), zebra=False)
        wt.setStyle(TableStyle([("BACKGROUND", (4, 0), (4, -1), colors.white),
                                ("LINEBELOW", (4, 0), (4, -1), 0, colors.white)]))
        title_wk = "Weekly closing prices - last 12 weeks"
        if p["n_weeks"] < 12:
            title_wk += f" (only {p['n_weeks']} weeks traded - listed on or after {p['first_date']:%d-%m-%Y})"
        story.append(KeepTogether([Paragraph(title_wk, S["h2"]), wt]))
        story.append(Spacer(1, 4))
        story.append(img(h["chart"]))

        # Screener key data (fetched directly)
        if snap.get("ratios"):
            items = list(snap["ratios"].items())[:10]
            cells = [Paragraph(f"<b>{esc(k)}</b><br/>{esc(v)}", S["cell"]) for k, v in items]
            while len(cells) % 5:
                cells.append("")
            grid_rows = [cells[k:k + 5] for k in range(0, len(cells), 5)]
            gt = Table(grid_rows, colWidths=[W / 5] * 5)
            gt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F9FC")),
                                    ("BOX", (0, 0), (-1, -1), 0.3, grid),
                                    ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.white),
                                    ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            extra = []
            if snap.get("promoters"):
                extra.append("<b>Promoter holding:</b> " + esc(", ".join(f"{a}: {b}" for a, b in snap["promoters"])))
            if snap.get("growth"):
                extra.append(" &nbsp;|&nbsp; ".join(f"<b>{esc(k)}:</b> {esc(v)}" for k, v in list(snap["growth"].items())[:2]))
            blk = [Paragraph("Key data - Screener.in (current figures)", S["h2"]), gt]
            for e in extra:
                blk.append(Paragraph(e, S["cell"]))
            story.append(KeepTogether(blk))

        story.append(Paragraph("Highlights", S["h2"]))
        if not r:
            msg = h.get("research_msg") or "Web research was not run (no API key / switched off)."
            story.append(Paragraph(esc(msg), S["warn"]))
            if snap.get("pros") or snap.get("cons"):
                pc = [[Paragraph("<b>Screener - pros</b>", S["cell"]),
                       Paragraph("<br/>".join("&bull; " + esc(x) for x in snap.get("pros", [])) or "-", S["cell"])],
                      [Paragraph("<b>Screener - cons</b>", S["cell"]),
                       Paragraph("<br/>".join("&bull; " + esc(x) for x in snap.get("cons", [])) or "-", S["cell"])]]
                pt = Table(pc, colWidths=[W * .24, W * .76])
                pt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                        ("LINEBELOW", (0, 0), (-1, -1), 0.25, grid)]))
                story.append(Spacer(1, 4))
                story.append(pt)
            continue
        if r.get("_searches", 1) == 0:
            story.append(Paragraph("Caution: no web search was performed for this note "
                                   "- verify before relying on it.", S["warn"]))
            story.append(Spacer(1, 4))
        if r.get("takeaway"):
            story.append(Spacer(1, 5))
            story.append(Paragraph("<b>In brief:</b> " + esc(str(r["takeaway"])[:800]), S["take"]))
            story.append(Spacer(1, 6))
        sections = [("Business", "business_snapshot"), ("Financials", "financials"),
                    ("Promoter and governance", "promoter_governance"),
                    ("Legal, regulatory and case law", "legal_regulatory"),
                    ("Industry", "industry_view"),
                    ("Market sentiment (news / social media)", "market_sentiment"),
                    ("Why the price moved (12 weeks)", "price_move_reasons")]
        rows = []
        for lab, key in sections:
            if r.get(key):
                rows.append([Paragraph(f"<b>{lab}</b>", S["cell"]),
                             Paragraph(esc(str(r[key])[:1500]), S["cell"])])
        for lab, key in [("Recent developments", "recent_developments"),
                         ("Positives", "positives"), ("Points to watch", "watch_points")]:
            items = [x for x in (r.get(key) or []) if str(x).strip()]
            if items:
                rows.append([Paragraph(f"<b>{lab}</b>", S["cell"]),
                             Paragraph("<br/>".join("&bull; " + esc(str(x)[:400]) for x in items[:6]),
                                       S["cell"])])
        if rows:
            ht = Table(rows, colWidths=[W * .24, W * .76])
            ht.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                    ("LINEBELOW", (0, 0), (-1, -1), 0.25, grid),
                                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
            story.append(ht)
        story.append(Spacer(1, 4))
        basis = (f"Based on {r.get('_searches', '?')} web searches and "
                 f"{r.get('_fetches', 0)} pages read by {esc(r.get('_model', 'Claude'))}.")
        src = "; ".join(f'<link href="{esc(s["url"])}" color="#1D4E89">{esc(s["title"][:70])}</link>'
                        for s in (r.get("sources") or [])[:8])
        story.append(Paragraph(basis + (" <b>Sources:</b> " + src if src else ""), S["small"]))

    footer = f"{title}"

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor(PALETTE["grid"]))
        canvas.setLineWidth(0.5)
        canvas.line(15 * mm, 12.5 * mm, A4[0] - 15 * mm, 12.5 * mm)
        canvas.setFont(FONT, 7)
        canvas.setFillColor(colors.HexColor(PALETTE["muted"]))
        canvas.drawString(15 * mm, 8.5 * mm, footer[:95])
        canvas.setFont(FONT_B, 7)
        canvas.setFillColor(colors.HexColor(PALETTE["blue"]))
        canvas.drawRightString(A4[0] - 15 * mm, 8.5 * mm,
                               f"Prepared by {PREPARED_BY}   |   Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(out_path), pagesize=A4, leftMargin=15 * mm,
                            rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
                            title=title, author=PREPARED_BY)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


# --------------------------------------------------------------------------
# 11. Identify each script and price it as on the valuation date
# --------------------------------------------------------------------------
def short_name(name):
    n = re.sub(r"\b(limited|ltd\.?)\b", "", str(name), flags=re.I)
    n = re.sub(r"\s+", " ", n).strip(" .-")
    return n[:34]


def _similar(a, b):
    a, b = clean_company(a), clean_company(b)
    if not a or not b:
        return False
    if a.split()[0] == b.split()[0]:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.6


def _candidates_from_symbol(sym):
    out = []
    for b in symbol_bases(sym):
        if re.fullmatch(r"\d{6}", b):
            out.append(b + ".BO")
        else:
            out += [b + ".NS", b + ".BO"]
    return out


def locate_and_price(h, master, researcher, start, val_date):
    """Fills h['symbol'], h['perf'] ... or sets h['reason'] (not valued)."""
    tried = set()
    listing = None
    original = h.get("symbol_in_file") or h["name"]

    def attempt(cands, how=None):
        nonlocal listing
        for c in list(dict.fromkeys(cands)):
            if not c or c in tried:
                continue
            tried.add(c)
            s, info = fetch_prices(c, start, val_date)
            time.sleep(0.2)
            if s is not None and len(s):
                perf = performance(s, val_date)
                if perf:
                    h["symbol"], h["perf"] = c, perf
                    h["price_source"] = info.get("source", "")
                    if how:
                        h["match_note"] = how.format(sym=c)
                    return True
            ft = info.get("first_trade")
            if ft and ft > val_date:
                listing = ft if not listing else min(listing, ft)
        return False

    # Stage 1 - security lists + symbol in the file
    rows = master_rows(master, h["name"], h.get("symbol_in_file"), h["isin"])
    cands = []
    for r in rows:
        cands += yahoo_symbols_for(r)
        if not h["isin"] and ISIN_RE.match(r["ISIN"] or ""):
            h["isin"], h["isin_fetched"] = r["ISIN"], True
        ld = _listing_date(r.get("LISTED"))
        if ld:
            listing = ld if not listing else min(listing, ld)
        if r["EXCH"] == "BSE-SUSPENDED":
            h["status_hint"] = "Suspended on BSE"
    if rows and (len(h["name"]) <= 12 or h["name"].upper() == str(h.get("symbol_in_file") or "").upper()):
        h["name"] = rows[0]["NAME"] or h["name"]
        h["short"] = short_name(h["name"])
    cands += _candidates_from_symbol(h.get("symbol_in_file"))
    if not h.get("symbol_in_file") and not rows:
        cands += _candidates_from_symbol(re.sub(r"\s+", "", clean_company(h["name"]).upper())[:10])
    if listing and listing > val_date:
        h["reason"] = f"Not listed as on valuation date (listed on {listing:%d-%m-%Y})"
        return False
    if attempt(cands):
        return True

    # Stage 2 - search by ISIN and by company name (renamed / T2T / SME / migrated)
    found = []
    if h["isin"]:
        found += [(s, n, True) for s, n in yahoo_search(h["isin"])]
    for q in dict.fromkeys([h["name"], clean_company(h["name"])]):
        found += [(s, n, False) for s, n in yahoo_search(q)]
    ok = [s for s, n, by_isin in found if by_isin or _similar(n, h["name"])]
    if attempt(ok, how=f"Not found under '{original}'; matched by ISIN / company name to "
                     "{sym}. Please verify."):
        return True

    # Stage 3 - web search through Claude
    status_note = ""
    if researcher:
        try:
            info = researcher.lookup_listing(h["name"], h.get("symbol_in_file"), h["isin"], val_date)
            isin = (info.get("isin") or "").upper().strip()
            if not h["isin"] and ISIN_RE.match(isin):
                h["isin"], h["isin_fetched"] = isin, True
            st = (info.get("status") or "").strip()
            status_note = "; ".join(x for x in [st, info.get("note", "")] if x)
            ld = _listing_date(info.get("listing_date"))
            if ld and ld > val_date:
                h["reason"] = f"Not listed as on valuation date (listed on {ld:%d-%m-%Y})"
                return False
            c3 = []
            if info.get("nse_symbol"):
                c3 += _candidates_from_symbol(info["nse_symbol"])
            if info.get("bse_code"):
                c3 += _candidates_from_symbol(str(info["bse_code"]))
            for r in master_rows(master, isin=isin) if ISIN_RE.match(isin) else []:
                c3 += yahoo_symbols_for(r)
            for old in info.get("former_names_or_symbols") or []:
                c3 += [s for s, n in yahoo_search(old)][:2]
            if attempt(c3, how=f"Not found under '{original}'; identified through web search as "
                              "{sym}" + (f" ({status_note})" if status_note else "") +
                              ". Please verify."):
                return True
        except Exception as e:
            status_note = status_note or f"web lookup failed: {str(e)[:120]}"

    if listing and listing > val_date:
        h["reason"] = f"Not listed as on valuation date (listed on {listing:%d-%m-%Y})"
    else:
        bits = ["No price found on NSE / BSE / Yahoo Finance up to the valuation date"]
        if h.get("status_hint"):
            bits.append(h["status_hint"])
        if status_note:
            bits.append("Web: " + status_note)
        else:
            bits.append("possibly unlisted, suspended, delisted or not a listed equity")
        h["reason"] = ". ".join(bits)
    return False


# --------------------------------------------------------------------------
# 12. Self-test (RUN_SELFTEST.bat)
# --------------------------------------------------------------------------
def selftest(settings):
    log("=" * 64)
    log("  SELF-TEST - checks every data source from this computer")
    log("=" * 64)
    res = []

    def chk(label, fn):
        try:
            ok, msg = fn()
        except Exception as e:
            ok, msg = False, f"{type(e).__name__}: {str(e)[:150]}"
        res.append((label, ok, msg))
        log(f" [{'OK ' if ok else 'FAIL'}] {label}: {msg}")

    today = dt.date.today()
    past = today - dt.timedelta(days=45)

    def t_yahoo():
        s, info = yahoo_chart("RELIANCE.NS", today - dt.timedelta(days=12), today)
        if s is None:
            return False, info.get("error", "no data")
        return True, f"RELIANCE latest close {s.iloc[-1]:.2f} on {s.index[-1]:%d-%m-%Y}"

    def t_past():
        s, info = yahoo_chart("RELIANCE.NS", past - dt.timedelta(days=100), past)
        if s is None:
            return False, info.get("error", "no data")
        ok = s.index[-1].date() <= past
        return ok, (f"asked {past:%d-%m-%Y} -> got close {s.iloc[-1]:.2f} of {s.index[-1]:%d-%m-%Y}"
                    + ("" if ok else " (WRONG DATE)"))

    def t_master():
        m = load_master()
        if m.empty:
            return False, "could not download"
        return True, ", ".join(f"{k}: {v:,}" for k, v in m["EXCH"].value_counts().items())

    def t_nse():
        s, info = nse_history("RELIANCE", today - dt.timedelta(days=20), today)
        return (s is not None), (f"{len(s)} days" if s is not None else
                                 "not reachable (only a backup source - fine if Yahoo works)")

    def t_search():
        r = yahoo_search("Infosys")
        return bool(r), (", ".join(x[0] for x in r[:3]) or "no results")

    def t_screener():
        snap = screener_snapshot(["ITC"])
        if not snap:
            return False, "not reachable (report will rely on web research)"
        return True, f"{len(snap['ratios'])} ratios read, e.g. " + ", ".join(
            f"{k}={v}" for k, v in list(snap["ratios"].items())[:3])

    def t_api():
        key = settings["api_key"]
        if not key:
            return False, "no API key entered"
        r = make_researcher(settings.get("provider"), key, settings["model"], settings["max_searches"])
        return True, r.preflight()

    chk("Yahoo Finance prices", t_yahoo)
    chk("Price for a past valuation date", t_past)
    chk("Yahoo symbol search", t_search)
    chk("NSE / BSE security lists", t_master)
    chk("NSE price service (backup)", t_nse)
    chk("Screener.in", t_screener)
    chk("AI provider + web search", t_api)
    log("-" * 64)
    bad = [r for r in res if not r[1]]
    log("All checks passed." if not bad else f"{len(bad)} check(s) need attention (see above).")
    return 0


# --------------------------------------------------------------------------
# 12b. Text-mode front end and the report pipeline
# --------------------------------------------------------------------------
def choose_input(settings, args):
    if args:
        p = Path(args[0])
        return p if p.is_absolute() else (Path.cwd() / p if (Path.cwd() / p).exists() else BASE_DIR / p)
    p = BASE_DIR / settings["input_file"]
    if p.exists():
        return p
    files = sorted([f for f in BASE_DIR.iterdir()
                    if f.suffix.lower() in (".xlsx", ".xls", ".csv") and not f.name.startswith("~$")])
    if not files:
        return p
    log("\nHoldings files in this folder:")
    for i, f in enumerate(files, 1):
        log(f"   {i}. {f.name}")
    try:
        k = input("Type the number of the file to use: ").strip()
        return files[int(k) - 1]
    except Exception:
        return files[0]


def safe_filename(s):
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", s)
    return re.sub(r"\s+", " ", s).strip(" .")[:120] or "Portfolio"


def cli_main(settings):
    """Text-mode run (python portfolio_analyzer.py --cli <file>)."""
    log("=" * 64)
    log("  EQUITY PORTFOLIO ANALYZER  -  text mode")
    log("=" * 64)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    date_arg = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--date=")), None)
    ent_arg = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--entity=")), None)
    in_path = choose_input(settings, args)
    if not in_path.exists():
        log(f"\nHoldings file not found: {in_path}")
        return 1
    key = settings["api_key"]
    try:
        holdings, info = read_holdings(in_path, settings, api_key=key)
    except Exception as e:
        log(f"\nCould not read the holdings file: {e}")
        return 1
    entity = ent_arg if ent_arg is not None else ask_entity(settings["entity"])
    val_date = ask_valuation_date(date_arg)
    if settings["ai_research"] and not key:
        try:
            key = getpass.getpass("Paste your Claude API key (hidden) or press Enter to skip: ").strip()
        except Exception:
            key = ""
    pdf_path = run_pipeline(holdings, settings, entity, val_date, key)
    if not pdf_path:
        return 1
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(pdf_path))
        elif sys.platform == "darwin":
            os.system(f'open "{pdf_path}"')
    except Exception:
        pass
    return 0


def run_pipeline(holdings, settings, entity, val_date, api_key=""):
    """Prices, research, insights, charts, PDF and Excel. Returns the PDF path
    (or None when nothing could be valued)."""
    EXCEPTIONS.clear()
    settings = dict(settings)
    settings["entity"] = entity
    log(f"   Entity: {entity or '-'}   |   Valuation date: {val_date:%d-%m-%Y} ({val_date:%A})"
        f"   |   Holdings: {len(holdings)}")
    for h in holdings:                       # fresh state for each run
        for k in ("perf", "symbol", "reason", "research", "research_msg", "screener",
                  "match_note", "industry", "cost", "cmp"):
            h.pop(k, None)

    # ---- Claude API ----
    researcher, research_off_reason = None, ""
    progress("Checking Claude API")
    if settings["ai_research"]:
        key = api_key
        if key:
            log("\nChecking the Claude API and web search...")
            try:
                researcher = make_researcher(settings.get("provider"), key, settings["model"],
                                             settings["max_searches"])
                log("   " + researcher.preflight())
            except Exception as e:
                research_off_reason = str(e)
                researcher = None
                log("   Web research switched off for this run: " + research_off_reason)
                note("Web research not done: " + research_off_reason)
        else:
            research_off_reason = "No API key provided - web research skipped."
            note(research_off_reason)
    else:
        research_off_reason = "Web research was switched off for this run."

    # ---- Identify and price ----
    progress("Loading NSE / BSE security lists")
    log("\nLoading NSE / BSE security lists...")
    try:
        master = load_master()
    except Exception as e:
        master = pd.DataFrame(columns=MASTER_COLS)
        exception("Security lists", str(e)[:150])
    start = val_date - dt.timedelta(days=12 * 7 + 45)
    bench_series, _ = fetch_prices(settings["benchmark"], start, val_date)
    bench_wc = weekly_closes(bench_series, val_date) if bench_series is not None else None
    bench_ret = (float(bench_wc["close"].iloc[-1] / bench_wc["close"].iloc[0] - 1)
                 if bench_wc is not None and len(bench_wc) > 1 else None)
    if bench_ret is None:
        note(f"Benchmark {settings['benchmark_name']} prices could not be downloaded.")

    log(f"\nFetching prices as on {val_date:%d-%m-%Y} and 12 weekly closes...")
    priced, unpriced = [], []
    for i, h in enumerate(holdings, 1):
        progress("Fetching prices", i - 1, len(holdings))
        h["short"] = short_name(h["name"])
        h["isin_fetched"] = False
        try:
            ok = locate_and_price(h, master, researcher, start, val_date)
        except Exception as e:
            ok = False
            h["reason"] = f"Error while processing: {str(e)[:150]}"
        if ok:
            h["bench_ret"] = bench_ret
            h["cmp"] = h["perf"]["cmp"]
            pdt = h["perf"]["price_date"]
            if (val_date - pdt).days > 7:
                exception(h["short"], f"last traded on {pdt:%d-%m-%Y}, before the valuation date "
                                      "(suspended / illiquid?) - that price is used.")
            if h["perf"]["n_weeks"] < 12:
                h["match_note"] = ((h.get("match_note") or "") + f" Trading history starts "
                                   f"{h['perf']['first_date']:%d-%m-%Y}; 12-week figures cover "
                                   "the period since then.").strip()
            if h.get("match_note"):
                exception(h["short"], h["match_note"])
            priced.append(h)
            log(f"   [{i}/{len(holdings)}] {h['short']:<34} {h['symbol']:<15} "
                f"{inr(h['cmp'], 2):>11} on {pdt:%d-%m-%Y}   12-wk {pct(h['perf']['ret_12w'])}")
        else:
            unpriced.append(h)
            log(f"   [{i}/{len(holdings)}] {h['short']:<34} NOT VALUED - {h.get('reason', '')}")

    if not priced:
        log("\nNo prices could be fetched for any script. Please use 'Check connections' "
            "to test the internet / data sources.")
        progress("Stopped")
        return None

    # ---- Costs / values ----
    resolve_costs(priced)
    for u in unpriced:
        u["cost"] = u["line_cost"] if u.get("line_cost") is not None else (
            sum(c for _, c in u.get("amb_lines") or []) or None)
    total_value = sum(h["qty"] * h["cmp"] for h in priced)
    for h in priced:
        h["value"] = h["qty"] * h["cmp"]
        h["weight"] = h["value"] / total_value if total_value else 0
        h["avg"] = h["cost"] / h["qty"] if h.get("cost") else None
        h["pnl"] = h["value"] - h["cost"] if h.get("cost") is not None else None
        h["ret"] = h["pnl"] / h["cost"] if h.get("cost") else None
    priced.sort(key=lambda x: -x["value"])

    # ---- Which holdings get the detailed analysis ----
    thr = float(settings.get("detail_min_pct", 1.0) or 0) / 100.0
    cost_total = sum(h["cost"] for h in priced if h.get("cost"))
    for idx, h in enumerate(priced, 1):
        h["row_no"] = idx
        share = (h["cost"] / cost_total) if (h.get("cost") and cost_total) else h["weight"]
        h["invested_share"] = share
        h["detail"] = share >= thr - 1e-12
    detailed = [h for h in priced if h["detail"]]
    if thr > 0:
        log(f"\nDetailed analysis for {len(detailed)} of {len(priced)} holdings "
            f"(invested value at least {thr * 100:g}% of the portfolio); the others are included "
            "in the totals, charts and holdings table.")
    settings["detail_note"] = (len(detailed), len(priced), thr)

    # ---- Screener ----
    if settings["screener"]:
        log("\nReading key data from Screener.in...")
        fails = 0
        for si, h in enumerate(detailed):
            progress("Reading Screener.in", si, len(detailed))
            slugs = []
            if h["symbol"].endswith(".NS"):
                slugs.append(h["symbol"][:-3])
            elif re.fullmatch(r"\d{6}\.BO", h["symbol"]):
                slugs.append(h["symbol"][:-3])
            elif h["symbol"].endswith(".BO"):
                slugs.append(h["symbol"][:-3])
                for r in master_rows(master, isin=h.get("isin")):
                    if r["EXCH"].startswith("BSE"):
                        slugs.append(r["SYMBOL"])
            try:
                h["screener"] = screener_snapshot(slugs) if fails < 4 else None
            except Exception:
                h["screener"] = None
            if not h["screener"]:
                fails += 1
            else:
                fails = 0
            time.sleep(0.8)
        got = sum(1 for h in detailed if h.get("screener"))
        log(f"   Screener data read for {got} of {len(detailed)} scripts.")

    # ---- Web research ----
    if researcher:
        log("\nResearching each stock on the web (about 30-90 seconds per stock)...")
        cache = research_cache_load()
        for i, h in enumerate(detailed, 1):
            progress("Web research", i - 1, len(detailed))
            key = f"v2|{h.get('isin') or h['symbol']}|{val_date:%Y-%m-%d}"
            if key in cache and not settings["refresh"]:
                h["research"] = cache[key]
                log(f"   [{i}/{len(detailed)}] {h['short']} - saved research reused")
                continue
            if researcher is None:
                h["research_msg"] = research_off_reason
                continue
            log(f"   [{i}/{len(detailed)}] {h['short']} ...")
            try:
                r = researcher.research_stock(h, val_date, settings["benchmark_name"])
                h["research"] = r
                log(f"        done - {r.get('_searches', 0)} searches, {r.get('_fetches', 0)} pages read"
                    + (f", issues: {', '.join(r['_errors'])}" if r.get("_errors") else ""))
                if r.get("_searches", 0) > 0:
                    cache[key] = r
                    research_cache_save(cache)
            except Exception as e:
                msg = str(e)
                h["research"] = None
                h["research_msg"] = "Web research could not be completed: " + msg[:250]
                exception(h["short"], h["research_msg"])
                if any(k in msg for k in ("API key", "credit", "switched off", "permission")):
                    research_off_reason = "Web research stopped: " + msg
                    researcher = None
    for h in priced:
        if not h.get("research") and not h.get("research_msg"):
            h["research_msg"] = research_off_reason or "Web research was not run."

    # ---- Industry classification ----
    progress("Classifying industries")
    log("\nClassifying industries...")
    nse_tries, nse_ok = 0, 0
    for h in priced:
        ind = ""
        if h["symbol"].endswith(".NS") and (nse_ok or nse_tries < 3):   # stop if NSE unreachable
            nse_tries += 1
            ind = nse_industry(h["symbol"][:-3])
            nse_ok += bool(ind)
        r = h.get("research") or {}
        ind = ind or (h.get("screener") or {}).get("sector") or r.get("industry") or r.get("sector") or ""
        if ind.lower().startswith("industry as per"):
            ind = r.get("sector") or ""
        h["industry"] = ind.strip()[:40]
    log(f"   Industry found for {sum(1 for h in priced if h['industry'])} of {len(priced)} scripts.")

    # ---- Insights ----
    tc = [h for h in priced if h.get("cost") is not None]
    total_cost = sum(h["cost"] for h in tc)
    value_with_cost = sum(h["value"] for h in tc)
    val_12w_ago = sum(h["qty"] * h["perf"]["weekly"]["close"].iloc[0] for h in priced)
    with_ret = [h for h in priced if h["ret"] is not None]
    with_12 = [h for h in priced if h["perf"]["ret_12w"] is not None]
    secmap = {}
    for h in priced:
        sec = h.get("industry") or "Not classified"
        secmap[sec] = secmap.get(sec, 0) + h["weight"]
    sectors = sorted(secmap.items(), key=lambda x: -x[1])
    ins = {
        "n": len(priced), "total_cost": total_cost, "total_value": total_value,
        "pnl": value_with_cost - total_cost if tc else None,
        "ret": (value_with_cost / total_cost - 1) if total_cost else None,
        "ret_12w": total_value / val_12w_ago - 1 if val_12w_ago else None,
        "bench_12w": bench_ret,
        "top3": sum(h["weight"] for h in priced[:3]),
        "top_alloc": priced[0],
        "best_cost": max(with_ret, key=lambda x: x["ret"]) if with_ret else None,
        "worst_cost": min(with_ret, key=lambda x: x["ret"]) if with_ret else None,
        "best_12w": max(with_12, key=lambda x: x["perf"]["ret_12w"]) if with_12 else None,
        "worst_12w": min(with_12, key=lambda x: x["perf"]["ret_12w"]) if with_12 else None,
        "n_profit": sum(1 for h in with_ret if h["ret"] >= 0),
        "n_loss": sum(1 for h in with_ret if h["ret"] < 0),
        "n_beat": sum(1 for h in with_12 if bench_ret is not None and h["perf"]["ret_12w"] > bench_ret),
        "sectors": sectors,
        "unpriced_cost": sum(u.get("cost") or 0 for u in unpriced),
    }
    if len(tc) < len(priced):
        note(f"{len(priced) - len(tc)} holding(s) have no cost in the file; they are "
             "excluded from cost-based return figures.")
    if researcher:
        try:
            summary = {
                "entity": entity, "valuation_date": str(val_date),
                "holdings": [{"name": h["short"], "weight_pct": round(h["weight"] * 100, 1),
                              "return_on_cost_pct": round(h["ret"] * 100, 1) if h["ret"] is not None else None,
                              "ret_12w_pct": round(h["perf"]["ret_12w"] * 100, 1) if h["perf"]["ret_12w"] is not None else None,
                              "industry": h.get("industry")} for h in priced],
                "not_valued": [{"name": u["name"], "reason": u.get("reason")} for u in unpriced],
                "portfolio_return_on_cost_pct": round((ins["ret"] or 0) * 100, 1),
                "portfolio_12w_pct": round((ins["ret_12w"] or 0) * 100, 1),
                "benchmark_12w_pct": round((bench_ret or 0) * 100, 1),
                "top3_weight_pct": round(ins["top3"] * 100, 1)}
            ins["observations"] = researcher.portfolio_commentary(summary)
        except Exception as e:
            log(f"   portfolio commentary skipped: {e}")

    # ---- Charts and PDF ----
    progress("Preparing charts and PDF")
    log("\nPreparing charts and PDF...")
    tmp = CACHE_DIR / "charts"
    tmp.mkdir(parents=True, exist_ok=True)
    for f in tmp.glob("*.png"):
        try:
            f.unlink()
        except Exception:
            pass
    TOP = 25
    al_lab = [h["short"] for h in priced[:TOP]]
    al_val = [h["weight"] for h in priced[:TOP]]
    al_title = "Allocation by market value"
    if len(priced) > TOP:
        al_lab.append(f"Other {len(priced) - TOP} holdings")
        al_val.append(sum(h["weight"] for h in priced[TOP:]))
        al_title += f" - top {TOP} holdings (all {len(priced)} are in the holdings table)"
    chart_bars(al_lab, al_val, tmp / "alloc.png", al_title)
    by12 = sorted(with_12, key=lambda x: -x["perf"]["ret_12w"])
    if by12:
        r_title = "Price change over the last 12 weeks (weekly closes)"
        if len(by12) > 30:
            by12 = by12[:15] + by12[-15:]
            r_title += " - best 15 and weakest 15"
        chart_bars([h["short"] for h in by12], [h["perf"]["ret_12w"] for h in by12],
                   tmp / "ret12.png", r_title, color_by_sign=True)
    else:
        chart_bars(["-"], [0], tmp / "ret12.png", "Price change over the last 12 weeks")
    try:
        chart_pie_returns(priced, tmp / "pie_returns.png")
        chart_pie_industry(sectors, tmp / "pie_industry.png")
    except Exception as e:
        log(f"   pie charts skipped: {e}")
    for i, h in enumerate(detailed):
        h["chart"] = tmp / f"stock_{i}.png"
        try:
            chart_weekly(h, bench_wc, h["chart"])
        except Exception:
            chart_bars(["-"], [0], h["chart"], "Chart not available")

    setup_fonts()
    title = (f"{entity} - Equity Portfolio as on {val_date:%d %B %Y}" if entity
             else f"Equity Portfolio as on {val_date:%d %B %Y}")
    base = safe_filename(f"{entity} - Equity Portfolio as on {val_date:%d-%m-%Y}" if entity
                         else f"Equity Portfolio as on {val_date:%d-%m-%Y}")
    out_dir = Path(settings.get("output_dir") or OUTPUT_DIR).expanduser()
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log(f"   Could not use the folder {out_dir} ({e}); saving in {OUTPUT_DIR} instead.")
        out_dir = OUTPUT_DIR
    pdf_path = out_dir / f"{base}.pdf"
    try:
        build_pdf(priced, unpriced, ins, val_date, settings, pdf_path, tmp, title)
    except PermissionError:
        pdf_path = out_dir / f"{base} ({dt.datetime.now():%H%M%S}).pdf"
        build_pdf(priced, unpriced, ins, val_date, settings, pdf_path, tmp, title)

    xl_path = pdf_path.with_suffix(".xlsx")
    try:
        rows = []
        for h in priced:
            r = {"Script": h["name"], "ISIN": h.get("isin"), "Symbol": h["symbol"],
                 "Industry": h.get("industry"),
                 "Qty": h["qty"], "Avg cost": h["avg"], "Cost": h.get("cost"),
                 "Price": h["cmp"], "Price date": h["perf"]["price_date"],
                 "Market value": h["value"], "Gain/(loss)": h["pnl"],
                 "Return %": h["ret"] * 100 if h["ret"] is not None else None,
                 "Weight %": h["weight"] * 100,
                 "12-wk %": h["perf"]["ret_12w"] * 100 if h["perf"]["ret_12w"] is not None else None}
            for j, (d, c) in enumerate(zip(h["perf"]["weekly"]["date"], h["perf"]["weekly"]["close"])):
                r[f"Wk {j} ({d:%d-%m})"] = round(float(c), 2)
            rows.append(r)
        with pd.ExcelWriter(xl_path) as xw:
            pd.DataFrame(rows).to_excel(xw, sheet_name="Valued", index=False)
            if unpriced:
                pd.DataFrame([{"Script": u["name"], "ISIN": u.get("isin"), "Qty": u["qty"],
                               "Cost": u.get("cost"), "Status / reason": u.get("reason")}
                              for u in unpriced]).to_excel(xw, sheet_name="Not valued", index=False)
    except Exception as e:
        log(f"   Excel copy not saved: {e}")

    log("\n" + "=" * 64)
    log(f"  DONE.  {len(priced)} valued, {len(unpriced)} not valued.")
    log(f"  Report: {pdf_path}")
    log("=" * 64)
    progress("Done", 1, 1)
    return pdf_path




def main():
    global _LOGFILE
    OUTPUT_DIR.mkdir(exist_ok=True)
    CACHE_DIR.mkdir(exist_ok=True)
    try:
        _LOGFILE = open(OUTPUT_DIR / "run_log.txt", "w", encoding="utf-8")
    except Exception:
        _LOGFILE = None
    settings = load_settings()
    if "--selftest" in sys.argv:
        return selftest(settings)
    if "--cli" in sys.argv:
        return cli_main(settings)
    return run_app(settings)


# --------------------------------------------------------------------------
# 13. Reading any holding statement: Excel, CSV, PDF, Word, HTML, image
# --------------------------------------------------------------------------
class NeedPassword(Exception):
    pass


def detect_kind(path):
    """File type from its content (extensions are often wrong)."""
    path = Path(path)
    with open(path, "rb") as f:
        head = f.read(4096)
    ext = path.suffix.lower()
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"PK"):
        try:
            import zipfile
            names = zipfile.ZipFile(path).namelist()
        except Exception:
            names = []
        if any(n.startswith("word/") for n in names):
            return "docx"
        if any(n.startswith("xl/") for n in names):
            return "xlsx"
        return "unknown"
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        try:
            whole = path.read_bytes()
            if "EncryptedPackage".encode("utf-16-le") in whole:
                return "office_encrypted"
        except Exception:
            pass
        return "doc" if ext == ".doc" else "xls"
    if head[:8] == b"\x89PNG\r\n\x1a\n" or head[:3] == b"\xff\xd8\xff" \
            or head[:6] in (b"GIF87a", b"GIF89a") or (head[:4] == b"RIFF" and head[8:12] == b"WEBP"):
        return "image"
    t = head.decode("latin-1", "ignore").lstrip().lower()
    if t.startswith("{\\rtf"):
        return "rtf"
    if t.startswith("<"):
        return "html"
    return "text"


KIND_LABEL = {"office_encrypted": "Password-protected Excel / Word", "pdf": "PDF", "docx": "Word", "xlsx": "Excel", "xls": "Excel (old format)",
              "doc": "Word (old .doc)", "image": "Image / scan", "html": "Web page table",
              "text": "CSV / text", "rtf": "Rich text", "unknown": "Unknown"}


def _rows_to_sheets(groups, prefix):
    sheets = {}
    for n, rows in groups.items():
        if len(rows) >= 2:
            sheets[f"{prefix}_{n}cols"] = pd.DataFrame(rows, dtype=object).replace("", None)
    return sheets


def _pdf_tables(path, password=""):
    import pdfplumber
    groups, texts = {}, []
    try:
        pdf = pdfplumber.open(str(path), password=password or None)
    except Exception as e:
        encrypted = "password" in (type(e).__name__ + str(e)).lower() or "encrypt" in str(e).lower()
        try:
            from pypdf import PdfReader
            encrypted = encrypted or PdfReader(str(path)).is_encrypted
        except Exception:
            pass
        if encrypted:
            raise NeedPassword(("The PDF password is not correct. " if password else
                                "This PDF is password protected. ") +
                               "Please enter the PDF password (for CDSL / NSDL CAS statements "
                               "it is usually your PAN in capitals).")
        raise
    with pdf:
        for page in pdf.pages[:80]:
            try:
                tables = page.extract_tables() or []
                if not tables:
                    tables = page.extract_tables({"vertical_strategy": "text",
                                                  "horizontal_strategy": "text"}) or []
            except Exception:
                tables = []
            for t in tables:
                rows = [[(c or "").replace("\n", " ").strip() for c in r] for r in t
                        if r and any((c or "").strip() for c in r)]
                if not rows:
                    continue
                n = max(len(r) for r in rows)
                groups.setdefault(n, []).extend(r + [""] * (n - len(r)) for r in rows)
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                pass
    return _rows_to_sheets(groups, "pdf"), "\n".join(texts)


def _docx_tables(path):
    import docx
    d = docx.Document(str(path))
    groups = {}
    for t in d.tables:
        rows = [[c.text.replace("\n", " ").strip() for c in r.cells] for r in t.rows]
        rows = [r for r in rows if any(r)]
        if rows:
            n = max(len(r) for r in rows)
            groups.setdefault(n, []).extend(r + [""] * (n - len(r)) for r in rows)
    text = "\n".join(p.text for p in d.paragraphs)
    for t in d.tables:
        text += "\n" + "\n".join(" | ".join(c.text for c in r.cells) for r in t.rows)
    return _rows_to_sheets(groups, "word"), text


def _decrypt_office(path, password):
    """Opens a password-protected Excel / Word file; returns a decrypted copy."""
    if not password:
        raise NeedPassword("This file is password protected. Please enter the file password.")
    try:
        import msoffcrypto
    except ImportError:
        raise ValueError("The 'msoffcrypto-tool' package is missing - run: "
                         "python -m pip install -r requirements.txt")
    out = CACHE_DIR / ("decrypted_" + Path(path).stem + ".bin")
    CACHE_DIR.mkdir(exist_ok=True)
    try:
        with open(path, "rb") as f:
            of = msoffcrypto.OfficeFile(f)
            of.load_key(password=password)
            with open(out, "wb") as o:
                of.decrypt(o)
    except Exception as e:
        if "key" in type(e).__name__.lower() or "password" in str(e).lower() or "verif" in str(e).lower():
            raise NeedPassword("The file password is not correct. Please enter it again.")
        raise ValueError(f"The protected file could not be opened: {e}")
    return out


def _decrypted_pdf_bytes(path, password):
    data = Path(path).read_bytes()
    try:
        from pypdf import PdfReader, PdfWriter
        rd = PdfReader(io.BytesIO(data))
        if rd.is_encrypted:
            if not password or not rd.decrypt(password):
                raise NeedPassword("This PDF is password protected. Please enter the PDF password.")
            w = PdfWriter()
            for pg in rd.pages:
                w.add_page(pg)
            buf = io.BytesIO()
            w.write(buf)
            return buf.getvalue()
    except NeedPassword:
        raise
    except Exception:
        pass
    return data


AI_EXTRACT_PROMPT = """This is an Indian demat / broker holding statement. Extract every
EQUITY SHARE (and exchange traded fund) holding. Skip mutual fund units, bonds,
debentures, government securities, cash and totals.

For each holding give:
 name        - company / security name as shown
 symbol      - NSE symbol or BSE code if shown, else ""
 isin        - ISIN if shown (12 characters starting with IN), else ""
 qty         - total quantity held (free + pledged + locked-in balances), a number
 avg_cost    - average buy price per share if shown, else null
 total_cost  - total purchase cost / invested value if shown, else null
Never take market value or LTP as cost. Do not invent values.

Reply ONLY with <json>{"holdings": [{"name": "", "symbol": "", "isin": "", "qty": 0,
"avg_cost": null, "total_cost": null}], "statement_date": "", "notes": ""}</json>"""


def ai_extract_holdings(path, kind, api_key, settings, text="", password=""):
    """Reads a statement with the chosen AI (PDF / image / any text). Returns a
    raw sheet with standard headings, ready for the normal column detection."""
    data, mime, mode = b"", "", "text"
    if kind == "pdf":
        data = _decrypted_pdf_bytes(path, password)
        if len(data) > 30 * 1024 * 1024:
            raise ValueError("PDF is larger than 30 MB - please split it.")
        mime, mode = "application/pdf", "pdf"
    elif kind == "image":
        data = Path(path).read_bytes()
        mime = ("image/png" if data[:4] == b"\x89PNG" else "image/jpeg" if data[:3] == b"\xff\xd8\xff"
                else "image/gif" if data[:3] == b"GIF" else "image/webp")
        mode = "image"
    elif not text:
        raise ValueError("No readable text found in the file.")
    r = make_researcher(settings.get("provider"), api_key, settings.get("model"))
    try:
        out = r.read_statement(mode, data, mime, text[:180000], AI_EXTRACT_PROMPT)
    except ResearchError as e:
        raise ValueError("AI reading failed: " + str(e))
    m = re.findall(r"<json>(.*?)</json>", out, re.S)
    body = m[-1] if m else out[out.find("{"): out.rfind("}") + 1]
    try:
        data = json.loads(re.sub(r",\s*([}\]])", r"\1", body), strict=False)
    except Exception:
        raise ValueError("The AI reply could not be understood. Please try again or use another model.")
    items = data.get("holdings") or []
    if not items:
        raise ValueError("No equity holdings were found in the statement.")
    rows = [["Scrip Name", "Symbol", "ISIN", "Quantity", "Avg Cost", "Total Cost"]]
    for it in items:
        rows.append([it.get("name") or "", it.get("symbol") or "", it.get("isin") or "",
                     it.get("qty"), it.get("avg_cost"), it.get("total_cost")])
    if data.get("notes"):
        note("AI reading: " + str(data["notes"])[:300])
    return {"ai": pd.DataFrame(rows, dtype=object)}


def _sheets_as_text(sheets, limit=3000):
    parts = []
    for name, df in (sheets or {}).items():
        parts.append(f"--- {name} ---\n" + df.head(limit).fillna("").to_csv(index=False, header=False))
    return "\n".join(parts)


def read_holdings(path, settings, api_key="", password="", force_ai=False):
    """Reads holdings from any statement. Returns (holdings, info).
    Order: table detection on the file itself -> AI reading (needs API key)."""
    path = Path(path)
    kind = detect_kind(path)
    info = {"kind": kind, "kind_label": KIND_LABEL.get(kind, kind), "method": "", "columns": ""}
    log(f"\nReading holding statement: {path.name}  ({info['kind_label']})")
    sheets, text, err = None, "", ""
    cols = settings.get("columns") or {}
    if kind == "office_encrypted":
        path = _decrypt_office(path, password)
        kind = detect_kind(path)
        info.update(kind=kind, kind_label=KIND_LABEL.get(kind, kind) + " (password protected)")
    if kind == "doc":
        raise ValueError("Old Word (.doc) files cannot be read. Please open it in Word and "
                         "'Save As' .docx or PDF, then select that file.")
    try:
        if kind == "pdf":
            sheets, text = _pdf_tables(path, password)
        elif kind == "docx":
            sheets, text = _docx_tables(path)
        elif kind in ("xlsx", "xls", "html", "text"):
            sheets = _read_raw_sheets(path)
            if kind in ("html", "text"):
                text = path.read_text(encoding="utf-8", errors="ignore")
        elif kind == "rtf":
            text = path.read_text(encoding="latin-1", errors="ignore")
    except NeedPassword:
        raise
    except Exception as e:
        err = str(e)
    if sheets and not force_ai:
        n_before = len(NOTES)
        try:
            holdings = read_portfolio(path, cols, sheets=sheets)
            info["method"] = "Read directly from the file"
            raw = next((x.split(": ", 1)[1] for x in NOTES[n_before:]
                        if x.startswith("Columns read")), "")
            nice = {"name": "Script name", "symbol": "Symbol", "isin": "ISIN", "qty": "Quantity",
                    "avg_cost": "Avg cost", "total_cost": "Total cost", "cost_ambiguous": "Cost"}
            info["columns"] = ", ".join(f"{nice.get(k.strip(), k.strip())} from '{v.strip()}'"
                                        for k, v in re.findall(r"(\w+) = '([^']*)'", raw))
            return holdings, info
        except Exception as e:
            err = str(e)
    # ---- AI reading ----
    if not api_key:
        raise ValueError(((err + " ") if err else "") +
                         "The holdings could not be found automatically in this file. Enter your "
                         "Claude API key above and press 'Read file again' - the statement will "
                         "then be read with AI.")
    if not text and sheets:
        text = _sheets_as_text(sheets)
    log(f"   Reading the statement with AI ({PROVIDERS.get(settings.get('provider'), 'AI')})...")
    ai_sheets = ai_extract_holdings(path, kind, api_key, settings, text=text, password=password)
    holdings = read_portfolio(path, {}, sheets=ai_sheets)
    info["method"] = f"Read with AI ({PROVIDERS.get(settings.get('provider'), 'AI')}) - please check the rows"
    info["columns"] = "name, symbol, ISIN, quantity, average cost, total cost"
    return holdings, info


def holdings_to_rows(holdings):
    rows = []
    for h in holdings:
        amb = h.get("line_cost") is None and bool(h.get("amb_lines"))
        total = h.get("line_cost")
        if amb:
            total = sum(c for _, c in h["amb_lines"])
        avg = (h["line_cost"] / h["qty"]) if (h.get("line_cost") and h.get("qty")) else None
        rows.append({"name": h.get("name") or "", "symbol": h.get("symbol_in_file") or "",
                     "isin": h.get("isin") or "", "qty": h.get("qty"),
                     "avg_cost": round(avg, 4) if avg else None,
                     "total_cost": round(total, 2) if total is not None else None,
                     "amb": amb, "amb_lines": h.get("amb_lines") or []})
    return rows


def rows_to_holdings(rows):
    out = []
    for r in rows:
        name = str(r.get("name") or "").strip()
        sym = str(r.get("symbol") or "").strip().upper() or None
        qty = to_number(r.get("qty"))
        if not (name or sym) or not qty or qty <= 0:
            continue
        isin = str(r.get("isin") or "").strip().upper().replace(" ", "")
        total = to_number(r.get("total_cost"))
        avg = to_number(r.get("avg_cost"))
        h = {"name": name or sym, "symbol_in_file": sym,
             "isin": isin if ISIN_RE.match(isin) else "", "qty": qty,
             "avg_cost": avg, "total_cost": total, "cost_ambiguous": None, "amb_lines": []}
        if r.get("amb") and r.get("amb_lines"):
            h["amb_lines"] = [tuple(x) for x in r["amb_lines"]]
            h["cost_ambiguous"] = sum(c for _, c in h["amb_lines"])
            h["line_cost"] = None
        else:
            h["line_cost"] = total if total is not None else (avg * qty if avg is not None else None)
        out.append(h)
    return out



# --------------------------------------------------------------------------
# 14. The app window (opens in your web browser, runs only on this computer)
# --------------------------------------------------------------------------
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs as _pqs, urlparse as _urlparse, unquote as _unquote

USER_SETTINGS = BASE_DIR / "user_settings.json"
UPLOAD_DIR = BASE_DIR / "uploads"
BENCHMARKS = {"^NSEI": "NIFTY 50", "^BSESN": "SENSEX", "^CRSLDX": "NIFTY 500"}
APP = {"status": "idle", "lines": [], "result": None, "excel": None, "error": "",
       "file": None, "server": None, "busy_with": ""}


def _load_user_settings():
    try:
        return json.loads(USER_SETTINGS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_user_settings(d):
    try:
        USER_SETTINGS.write_text(json.dumps(d, indent=1), encoding="utf-8")
    except Exception:
        pass



def _default_output_dir(us, base):
    return us.get("output_dir") or base.get("output_dir") or str(OUTPUT_DIR)


def _quick_folders():
    out = []
    home = Path.home()
    for name in ("Desktop", "Documents", "Downloads"):
        for cand in (home / name, home / "OneDrive" / name):
            if cand.is_dir():
                out.append({"label": name, "path": str(cand)})
                break
    out.append({"label": "App output folder", "path": str(OUTPUT_DIR)})
    if sys.platform.startswith("win"):
        import string
        for d in string.ascii_uppercase:
            if os.path.exists(f"{d}:\\"):
                out.append({"label": f"Drive {d}:", "path": f"{d}:\\"})
    else:
        out.append({"label": "Home", "path": str(home)})
    return out


def _list_dirs(path):
    p = Path(path).expanduser() if path else OUTPUT_DIR
    if not p.exists():
        p = OUTPUT_DIR
    dirs = []
    try:
        for c in sorted(p.iterdir(), key=lambda x: x.name.lower()):
            try:
                if c.is_dir() and not c.name.startswith((".", "$")):
                    dirs.append(c.name)
            except Exception:
                continue
    except Exception as e:
        return {"path": str(p), "parent": str(p.parent), "dirs": [], "error": str(e)}
    return {"path": str(p), "parent": str(p.parent) if p.parent != p else "", "dirs": dirs[:500]}


def _check_folder(path):
    try:
        p = Path(path).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        t = p / ".write_test"
        t.write_text("x")
        t.unlink()
        return ""
    except Exception as e:
        return f"The report cannot be saved in '{path}': {e}"


def _app_log(line):
    APP["lines"].append(line)


def _settings_from_request(base, req):
    s = dict(base)
    prov = req.get("provider") or guess_provider(req.get("api_key", "")) or s.get("provider") or "anthropic"
    s["provider"] = prov if prov in PROVIDERS else "anthropic"
    s["model"] = req.get("model") or DEFAULT_MODELS[s["provider"]]
    s["output_dir"] = (req.get("output_dir") or "").strip() or s.get("output_dir") or str(OUTPUT_DIR)
    s["ai_research"] = bool(req.get("ai_research", True))
    s["screener"] = bool(req.get("screener", True))
    s["refresh"] = bool(req.get("refresh", False))
    try:
        s["detail_min_pct"] = max(0.0, min(100.0, float(req.get("detail_min_pct", s.get("detail_min_pct", 1)))))
    except Exception:
        pass
    try:
        s["max_searches"] = max(1, min(15, int(req.get("max_searches") or s["max_searches"])))
    except Exception:
        pass
    b = req.get("benchmark") or s["benchmark"]
    s["benchmark"], s["benchmark_name"] = b, BENCHMARKS.get(b, s.get("benchmark_name", b))
    return s


def _job(target, *args):
    def runner():
        try:
            APP["result"] = target(*args)
            APP["status"] = "done"
        except Exception as e:
            APP["error"] = str(e)
            APP["status"] = "error"
            log("\nSomething went wrong: " + str(e))
            log(traceback.format_exc())
        finally:
            APP["busy_with"] = ""
    threading.Thread(target=runner, daemon=True).start()


def _run_report(rows, settings, entity, val_date, api_key):
    holdings = rows_to_holdings(rows)
    if not holdings:
        raise ValueError("No holdings with a quantity to analyse.")
    pdf = run_pipeline(holdings, settings, entity, val_date, api_key)
    if not pdf:
        raise ValueError("No script could be priced - use 'Check connections'.")
    APP["excel"] = str(Path(pdf).with_suffix(".xlsx"))
    return str(pdf)


def _open_path(p):
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(p))
        elif sys.platform == "darwin":
            os.system(f'open "{p}"')
        else:
            os.system(f'xdg-open "{p}" >/dev/null 2>&1 &')
    except Exception:
        pass


class AppHandler(BaseHTTPRequestHandler):
    settings = None

    def log_message(self, *a):          # keep the console clean
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else (
            json.dumps(body, default=str) if ctype == "application/json" else body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if "text" in ctype or "json" in ctype else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}

    # ---------------- GET ----------------
    def do_GET(self):
        u = _urlparse(self.path)
        if u.path == "/":
            return self._send(200, APP_HTML, "text/html")
        if u.path == "/api/settings":
            us = _load_user_settings()
            s = self.settings
            keys = dict(us.get("keys") or {})
            if s.get("api_key") and s["provider"] not in keys:
                keys[s["provider"]] = s["api_key"]
            return self._send(200, {
                "provider": us.get("provider") or s["provider"], "providers": PROVIDERS,
                "keys": keys, "remember_key": bool(us.get("remember_key")),
                "entities": us.get("entities") or ([s["entity"]] if s.get("entity") else []),
                "model": us.get("model") or s["model"], "default_models": DEFAULT_MODELS,
                "output_dir": _default_output_dir(us, s), "quick": _quick_folders(),
                "ai_research": us.get("ai_research", s["ai_research"]),
                "screener": us.get("screener", s["screener"]),
                "refresh": us.get("refresh", s["refresh"]),
                "max_searches": us.get("max_searches", s["max_searches"]),
                "detail_min_pct": us.get("detail_min_pct", s.get("detail_min_pct", 1.0)),
                "benchmark": us.get("benchmark", s["benchmark"]), "benchmarks": BENCHMARKS,
                "today": dt.date.today().isoformat(),
                "preloaded": Path(APP["file"]).name if APP["file"] else ""})
        if u.path == "/api/status":
            since = int((_pqs(u.query).get("since") or ["0"])[0])
            return self._send(200, {"status": APP["status"], "busy_with": APP["busy_with"],
                                    "lines": APP["lines"][since:], "next": len(APP["lines"]),
                                    "progress": PROGRESS, "error": APP["error"],
                                    "result": Path(APP["result"]).name if APP["result"] else None})
        if u.path == "/api/dirs":
            return self._send(200, _list_dirs((_pqs(u.query).get("path") or [""])[0]))
        if u.path in ("/api/report", "/api/excel"):
            p = APP["result"] if u.path == "/api/report" else APP["excel"]
            if not p or not Path(p).exists():
                return self._send(404, {"error": "No report yet"})
            data = Path(p).read_bytes()
            ctype = ("application/pdf" if p.endswith(".pdf") else
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            disp = "inline" if p.endswith(".pdf") else "attachment"
            self.send_header("Content-Disposition", f'{disp}; filename="{quote(Path(p).name)}"')
            self.end_headers()
            self.wfile.write(data)
            return
        return self._send(404, {"error": "not found"})

    # ---------------- POST ----------------
    def do_POST(self):
        u = _urlparse(self.path)
        if u.path == "/api/upload":
            n = int(self.headers.get("Content-Length") or 0)
            name = _unquote(self.headers.get("X-Filename") or "statement")
            name = re.sub(r'[\\/:*?"<>|]+', "_", Path(name).name)[:120] or "statement"
            UPLOAD_DIR.mkdir(exist_ok=True)
            dest = UPLOAD_DIR / name
            dest.write_bytes(self.rfile.read(n))
            APP["file"] = str(dest)
            return self._send(200, {"ok": True, "name": name, "kind": KIND_LABEL.get(detect_kind(dest), "")})

        if u.path == "/api/models":
            req = self._json_body()
            prov = req.get("provider") or guess_provider(req.get("api_key", ""))
            if not req.get("api_key"):
                return self._send(200, {"error": "Enter the API key first."})
            try:
                r = make_researcher(prov, req["api_key"], DEFAULT_MODELS.get(prov, ""))
                ids = r.list_models()
                return self._send(200, {"models": ids, "default": pick_default_model(prov, ids),
                                        "provider": prov})
            except Exception as e:
                return self._send(200, {"error": _api_error_text(e, prov),
                                        "guess": guess_provider(req.get("api_key", ""))})

        if u.path == "/api/mkdir":
            req = self._json_body()
            name = re.sub(r'[\\/:*?"<>|]+', "", str(req.get("name") or "")).strip()
            if not name:
                return self._send(200, {"error": "Type a folder name."})
            try:
                (Path(req.get("path") or OUTPUT_DIR) / name).mkdir(parents=True, exist_ok=True)
                return self._send(200, _list_dirs(str(Path(req.get("path") or OUTPUT_DIR) / name)))
            except Exception as e:
                return self._send(200, {"error": f"Could not create the folder: {e}"})

        if u.path == "/api/read":
            req = self._json_body()
            if not APP["file"]:
                return self._send(200, {"error": "Select a holding statement first."})
            settings = _settings_from_request(self.settings, req)
            NOTES.clear()
            try:
                holdings, info = read_holdings(APP["file"], settings, api_key=req.get("api_key", ""),
                                               password=req.get("password", ""),
                                               force_ai=bool(req.get("force_ai")))
                notes = [n for n in NOTES if not n.startswith("Columns read")]
                return self._send(200, {"rows": holdings_to_rows(holdings), "info": info, "notes": notes})
            except NeedPassword as e:
                return self._send(200, {"need_password": True, "error": str(e)})
            except Exception as e:
                return self._send(200, {"error": str(e)})

        if u.path == "/api/run":
            if APP["busy_with"]:
                return self._send(200, {"error": "A task is already running."})
            req = self._json_body()
            vd = parse_date(str(req.get("date") or ""))
            if not vd:
                return self._send(200, {"error": "Enter a valid valuation date."})
            if vd > dt.date.today():
                return self._send(200, {"error": "The valuation date cannot be in the future."})
            entity = str(req.get("entity") or "").strip()
            if not entity:
                return self._send(200, {"error": "Enter the name of the entity."})
            settings = _settings_from_request(self.settings, req)
            bad = _check_folder(settings["output_dir"])
            if bad:
                return self._send(200, {"error": bad})
            us = _load_user_settings()
            ents = [entity] + [e for e in (us.get("entities") or []) if e != entity]
            keys = dict(us.get("keys") or {})
            if req.get("remember_key") and req.get("api_key"):
                keys[settings["provider"]] = req["api_key"]
            elif not req.get("remember_key"):
                keys = {}
            us.update({"entities": ents[:15], "model": settings["model"], "keys": keys,
                       "provider": settings["provider"], "output_dir": settings["output_dir"],
                       "ai_research": settings["ai_research"], "screener": settings["screener"],
                       "refresh": settings["refresh"], "max_searches": settings["max_searches"],
                       "detail_min_pct": settings["detail_min_pct"],
                       "benchmark": settings["benchmark"],
                       "remember_key": bool(req.get("remember_key"))})
            us.pop("api_key", None)
            _save_user_settings(us)
            APP.update(status="running", lines=[], result=None, excel=None, error="",
                       busy_with="report")
            progress("Starting")
            _job(_run_report, req.get("rows") or [], settings, entity, vd, req.get("api_key", ""))
            return self._send(200, {"ok": True})

        if u.path == "/api/selftest":
            if APP["busy_with"]:
                return self._send(200, {"error": "A task is already running."})
            req = self._json_body()
            settings = _settings_from_request(self.settings, req)
            settings["api_key"] = req.get("api_key", "")
            APP.update(status="running", lines=[], result=None, excel=None, error="",
                       busy_with="check")
            progress("Checking connections")
            _job(selftest, settings)
            return self._send(200, {"ok": True})

        if u.path == "/api/open":
            req = self._json_body()
            if req.get("what") == "folder":
                _open_path(OUTPUT_DIR)
            elif APP["result"]:
                _open_path(APP["result"])
            return self._send(200, {"ok": True})

        if u.path == "/api/quit":
            self._send(200, {"ok": True})
            threading.Thread(target=APP["server"].shutdown, daemon=True).start()
            return
        return self._send(404, {"error": "not found"})


def run_app(settings, open_browser=True, port=None):
    global LOG_HOOK
    LOG_HOOK = _app_log
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args and Path(args[0]).exists():                      # file dragged onto the .bat
        APP["file"] = str(Path(args[0]).resolve())
    AppHandler.settings = settings
    server = None
    for p in ([port] if port else range(8765, 8800)):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), AppHandler)
            break
        except OSError:
            continue
    if server is None:
        print("Could not start the app (no free port).")
        return 1
    APP["server"] = server
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print("=" * 64)
    print("  EQUITY PORTFOLIO ANALYZER is running.")
    print(f"  It has opened in your web browser:  {url}")
    print("  Keep this window open while you use the app.")
    print("  To finish, click 'Close app' in the browser or close this window.")
    print("=" * 64)
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


APP_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Equity Portfolio Report - SV Arka Advisors</title>
<style>
:root{
  --ink:#14213D; --blue:#1D4E89; --blue-2:#2B64A8; --paper:#F5F7FA; --white:#FFFFFF;
  --rule:#D8DFE9; --rule-2:#E9EDF3; --muted:#5B6678; --green:#2E7D32; --red:#B3261E;
  --amber-bg:#FFF4E5; --amber:#8A4B00; --focus:#F2B705;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--paper);color:var(--ink);
  font:15px/1.5 "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif}
button,input,select{font:inherit;color:inherit}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
header{background:var(--ink);color:#fff}
.bar{max-width:1320px;margin:0 auto;padding:14px 24px;display:flex;align-items:center;gap:16px}
.brand{display:flex;flex-direction:column;line-height:1.15}
.brand b{font-size:19px;font-weight:600;letter-spacing:.2px}
.brand span{font-size:13px;color:#B9C6DA}
.bar .spacer{flex:1}
.ghost{background:transparent;border:1px solid #4A5D82;color:#fff;border-radius:6px;padding:7px 14px;cursor:pointer}
.ghost:hover{background:#22325A}
main{max-width:1320px;margin:0 auto;padding:22px 24px 40px;display:grid;
  grid-template-columns:minmax(300px,380px) 1fr;gap:22px;align-items:start}
section{background:var(--white);border:1px solid var(--rule);border-radius:10px}
.step{display:flex;gap:12px;align-items:baseline;padding:16px 20px 4px}
.stepno{flex:none;width:26px;height:26px;border-radius:50%;background:var(--blue);color:#fff;
  display:grid;place-items:center;font-size:13px;font-weight:600;transform:translateY(-2px)}
h2{margin:0;font-size:17px;font-weight:600}
.hint{color:var(--muted);font-size:13px;margin:2px 0 0}
.body{padding:10px 20px 20px}
label{display:block;font-size:13.5px;font-weight:600;margin:14px 0 5px}
label small{font-weight:400;color:var(--muted)}
input[type=text],input[type=password],input[type=date],input[type=number],select{
  width:100%;padding:9px 11px;border:1px solid var(--rule);border-radius:6px;background:#fff}
input:hover,select:hover{border-color:#B8C3D3}
.row{display:flex;gap:8px;align-items:center}
.row input{flex:1}
.check{display:flex;gap:8px;align-items:center;font-weight:400;font-size:13.5px;margin:8px 0 0}
.check input{width:16px;height:16px}
details{margin-top:14px;border-top:1px solid var(--rule-2);padding-top:10px}
summary{cursor:pointer;font-weight:600;font-size:13.5px;color:var(--blue)}
.drop{margin-top:6px;border:1.5px dashed #9FB1CB;border-radius:8px;padding:18px 14px;text-align:center;
  background:#F9FBFD;cursor:pointer}
.drop.over{background:#EAF1FA;border-color:var(--blue)}
.drop strong{display:block;font-size:14.5px}
.drop span{font-size:12.5px;color:var(--muted)}
.btn{background:var(--blue);color:#fff;border:0;border-radius:6px;padding:10px 18px;font-weight:600;cursor:pointer}
.btn:hover{background:var(--blue-2)}
a.btn{text-decoration:none;display:inline-block}
.row .btn{white-space:nowrap;flex:none}
.btn[disabled]{background:#9AAAC2;cursor:not-allowed}
.btn.quiet{background:#fff;color:var(--blue);border:1px solid var(--rule)}
.btn.quiet:hover{background:#F1F5FB}
.msg{margin:10px 0 0;padding:9px 12px;border-radius:6px;font-size:13.5px}
.msg.err{background:#FDECEA;color:var(--red)}
.msg.warn{background:var(--amber-bg);color:var(--amber)}
.msg.ok{background:#EAF4EA;color:#1E5E22}
.right{display:flex;flex-direction:column;gap:22px;min-width:0}
.paper-head{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center;padding:6px 20px 0}
.chip{border:1px solid var(--rule);border-radius:999px;padding:3px 10px;font-size:12.5px;color:var(--muted);background:#fff}
.chip b{color:var(--ink);font-weight:600}
.tablewrap{overflow:auto;margin:12px 0 0;border-top:1px solid var(--rule);max-height:52vh}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:13.5px}
th{position:sticky;top:0;background:#EEF2F8;color:var(--ink);font-weight:600;text-align:left;
  padding:8px 8px;border-bottom:1px solid var(--rule);white-space:nowrap;z-index:1}
td{border-bottom:1px solid var(--rule-2);padding:0}
td.n{color:var(--muted);text-align:right;padding:0 8px;width:34px}
td input[type=text]{width:100%;border:0;background:transparent;padding:8px 8px;border-radius:0;min-width:70px}
td input[type=text]:hover{background:#F6F9FD}
td input[type=text]:focus{background:#FFFBEA;outline:2px solid var(--focus);outline-offset:-2px}
td.num input[type=text],th.num{text-align:right}
th.num:first-child{width:34px}
td.x{width:40px;text-align:center}
.x button{border:0;background:transparent;color:#8A94A6;cursor:pointer;font-size:18px;line-height:1;padding:6px}
.x button:hover{color:var(--red)}
tr.flag td{background:#FFF8EC}
tfoot td{background:#F7F9FC;font-weight:600;padding:9px 8px;border-top:1px solid var(--rule)}
tfoot td.num{text-align:right}
.empty{padding:34px 20px;text-align:center;color:var(--muted)}
.tools{display:flex;gap:10px;align-items:center;padding:12px 20px 18px;flex-wrap:wrap}
.tools .spacer{flex:1}
.run{padding:10px 20px 20px}
.stage{display:flex;justify-content:space-between;font-size:13.5px;margin:4px 0 6px;gap:10px}
.track{height:8px;background:#E6EBF2;border-radius:99px;overflow:hidden}
.fill{height:100%;width:0;background:var(--blue);transition:width .4s ease}
.log{margin-top:12px;background:#0F1A30;color:#D6E0F0;border-radius:8px;padding:12px 14px;height:240px;
  overflow:auto;font:12.5px/1.45 Consolas,"Cascadia Mono",monospace;white-space:pre-wrap}
.done{display:none;gap:10px;flex-wrap:wrap;margin-top:12px;align-items:center}
.done.show{display:flex}
.done .file{font-weight:600;margin-right:6px}
.spin{display:inline-block;width:14px;height:14px;border:2px solid #C9D4E5;border-top-color:var(--blue);
  border-radius:50%;animation:sp 0.8s linear infinite;vertical-align:-2px;margin-right:6px}
@keyframes sp{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){.spin{animation:none}.fill{transition:none}}
@media (max-width:900px){main{grid-template-columns:1fr;padding:16px}.bar{padding:12px 16px}}
.sr{position:absolute;left:-9999px}
dialog{border:1px solid var(--rule);border-radius:10px;padding:0;width:min(640px,94vw);color:var(--ink)}
dialog::backdrop{background:rgba(20,33,61,.45)}
.pk-head{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--rule)}
.x-close{border:0;background:transparent;font-size:22px;cursor:pointer;color:var(--muted)}
.pk-quick{display:flex;flex-wrap:wrap;gap:8px;padding:12px 18px 0}
.pk-quick button{border:1px solid var(--rule);background:#fff;border-radius:999px;padding:4px 12px;cursor:pointer;font-size:13px}
.pk-quick button:hover{background:#F1F5FB}
.pk-path{display:flex;gap:10px;align-items:center;padding:12px 18px;font-size:13.5px;word-break:break-all}
.pk-list{list-style:none;margin:0;padding:0 8px;max-height:44vh;overflow:auto;border-top:1px solid var(--rule-2);border-bottom:1px solid var(--rule-2)}
.pk-list button{width:100%;text-align:left;border:0;background:transparent;padding:8px 10px;cursor:pointer;border-radius:6px}
.pk-list button:hover{background:#F1F5FB}
.pk-list .none{padding:14px 10px;color:var(--muted)}
.pk-foot{display:flex;gap:8px;align-items:center;padding:12px 18px;flex-wrap:wrap}
.pk-foot input{width:auto;flex:1;min-width:150px}
.pk-foot .spacer{flex:1}
</style></head>
<body>
<header><div class="bar">
  <div class="brand"><b>Equity Portfolio Report</b><span>SV Arka Advisors</span></div>
  <div class="spacer"></div>
  <button class="ghost" id="btnCheck" type="button">Check connections</button>
  <button class="ghost" id="btnQuit" type="button">Close app</button>
</div></header>

<main>
  <div>
    <section aria-labelledby="h1">
      <div class="step"><span class="stepno">1</span><div><h2 id="h1">Report details</h2>
        <p class="hint">Who the report is for and the date to value it on.</p></div></div>
      <div class="body">
        <label for="entity">Name of the entity</label>
        <input type="text" id="entity" list="entities" placeholder="e.g. ABC Family Trust" autocomplete="off">
        <datalist id="entities"></datalist>

        <label for="vdate">Valuation date</label>
        <input type="date" id="vdate">

        <label for="provider">AI provider <small>(for web research and reading PDFs or scans)</small></label>
        <select id="provider"></select>

        <label for="key">API key</label>
        <div class="row"><input type="password" id="key" placeholder="Paste the API key" autocomplete="off">
          <button class="btn quiet" type="button" id="btnShow" aria-label="Show or hide the API key">Show</button></div>
        <p class="hint" id="keyHint"></p>
        <label class="check"><input type="checkbox" id="remember"> Remember the key on this computer</label>

        <label for="model">Model</label>
        <div class="row"><select id="model"></select>
          <button class="btn quiet" type="button" id="btnModels">Load models</button></div>
        <p class="hint" id="modelHint">Enter the key, then the models available to it are listed.</p>

        <details>
          <summary>Report options</summary>
          <label class="check"><input type="checkbox" id="optResearch" checked> Web research and highlights for each stock</label>
          <label class="check"><input type="checkbox" id="optScreener" checked> Key ratios from Screener.in</label>
          <label class="check"><input type="checkbox" id="optRefresh"> Research again even if saved research exists</label>
          <label for="minpct">Detailed analysis only for holdings with invested value of at least
            <small>(% of the portfolio; 0 = all holdings)</small></label>
          <input type="number" id="minpct" min="0" max="100" step="0.5" value="1">
          <label for="searches">Web searches per stock</label>
          <input type="number" id="searches" min="1" max="15" value="6">
          <label for="bench">Compare with</label>
          <select id="bench"></select>
        </details>
      </div>
    </section>

    <section aria-labelledby="h2" style="margin-top:22px">
      <div class="step"><span class="stepno">2</span><div><h2 id="h2">Holding statement</h2>
        <p class="hint">Excel, CSV, PDF, Word, web page or a photo / scan of the statement.</p></div></div>
      <div class="body">
        <div class="drop" id="drop" tabindex="0" role="button" aria-describedby="dropHint">
          <strong id="dropTitle">Select the holding statement</strong>
          <span id="dropHint">Click to browse, or drop the file here</span>
        </div>
        <input type="file" id="file" class="sr"
          accept=".xlsx,.xls,.xlsm,.csv,.txt,.pdf,.docx,.doc,.htm,.html,.rtf,.png,.jpg,.jpeg,.webp,.gif">
        <div id="pwBox">
          <label for="pw">File password, if the file is protected <small>(CAS statements: usually your PAN in capitals)</small></label>
          <input type="password" id="pw" autocomplete="off" placeholder="Leave blank if not protected">
        </div>
        <div id="readMsg"></div>
        <div class="row" style="margin-top:12px;gap:10px;flex-wrap:wrap">
          <button class="btn quiet" type="button" id="btnRead" disabled>Read file again</button>
          <button class="btn quiet" type="button" id="btnAI" disabled>Read with AI instead</button>
        </div>
      </div>
    </section>
  </div>

  <div class="right">
    <section aria-labelledby="h3">
      <div class="step"><span class="stepno">3</span><div><h2 id="h3">Check the holdings</h2>
        <p class="hint">This is what was read from the statement. Correct any cell, remove rows that are not equity shares, or add a missing one.</p></div></div>
      <div class="paper-head" id="paperHead"></div>
      <div class="tablewrap">
        <table aria-describedby="h3">
          <thead><tr><th class="num">#</th><th>Script name</th><th>Symbol</th><th>ISIN</th>
            <th class="num">Quantity</th><th class="num">Avg cost (Rs)</th><th class="num">Total cost (Rs)</th><th><span class="sr">Remove</span></th></tr></thead>
          <tbody id="tbody"><tr><td colspan="8" class="empty">Select a holding statement to see its holdings here.</td></tr></tbody>
          <tfoot id="tfoot"></tfoot>
        </table>
      </div>
      <div class="tools">
        <button class="btn quiet" type="button" id="btnAdd">Add a row</button>
        <span class="spacer"></span>
        <span class="hint" id="ambHint" style="display:none">Rows shaded amber have one "Cost" column; the report decides whether it is per share or total by comparing with the market price.</span>
      </div>
    </section>

    <section aria-labelledby="h4">
      <div class="step"><span class="stepno">4</span><div><h2 id="h4">Generate the report</h2>
        <p class="hint">Prices as on the valuation date, 12 weekly closes, research, insights and the PDF.</p></div></div>
      <div class="run">
        <label for="outdir" style="margin-top:4px">Save the report in</label>
        <div class="row" style="margin-bottom:14px"><input type="text" id="outdir" spellcheck="false">
          <button class="btn quiet" type="button" id="btnPick">Choose folder</button></div>
        <div class="row" style="gap:12px;flex-wrap:wrap">
          <button class="btn" type="button" id="btnGo">Generate report</button>
          <span id="goMsg" class="hint"></span>
        </div>
        <div id="runBox" style="display:none;margin-top:16px">
          <div class="stage"><span id="stage">Starting</span><span id="count"></span></div>
          <div class="track"><div class="fill" id="fill"></div></div>
          <div class="done" id="done">
            <span class="file" id="doneName"></span>
            <button class="btn" type="button" id="btnOpen">Open report</button>
            <a class="btn quiet" id="lnkPdf" href="/api/report" target="_blank" rel="noopener">View in browser</a>
            <a class="btn quiet" id="lnkXls" href="/api/excel">Download Excel</a>
            <button class="btn quiet" type="button" id="btnFolder">Open folder</button>
          </div>
          <div class="log" id="log" role="log" aria-live="polite"></div>
        </div>
      </div>
    </section>
  </div>
</main>

<dialog id="picker" aria-labelledby="pkTitle">
  <div class="pk-head"><h2 id="pkTitle">Choose the folder for the report</h2>
    <button class="x-close" type="button" id="pkClose" aria-label="Close">&times;</button></div>
  <div class="pk-quick" id="pkQuick"></div>
  <div class="pk-path"><button class="btn quiet" type="button" id="pkUp">Up one level</button><span id="pkPath"></span></div>
  <ul class="pk-list" id="pkList"></ul>
  <div class="pk-foot">
    <input type="text" id="pkNew" placeholder="New folder name">
    <button class="btn quiet" type="button" id="pkMk">Create folder</button>
    <span class="spacer"></span>
    <button class="btn" type="button" id="pkUse">Use this folder</button>
  </div>
</dialog>

<script>
const $ = id => document.getElementById(id);
let rows = [], fileName = "", polling = null, since = 0, benchName = {}, keys = {}, defaults = {}, quick = [];
const STAGES = ["Checking Claude API","Loading NSE / BSE security lists","Fetching prices",
  "Reading Screener.in","Web research","Classifying industries","Preparing charts and PDF","Done"];

function fmt(n, d){ if(n===null||n===undefined||n==="") return "";
  const x = Number(n); if(!isFinite(x)) return String(n);
  return x.toLocaleString("en-IN",{maximumFractionDigits:d,minimumFractionDigits:0}); }
function num(v){ if(v===null||v===undefined) return null; const t=String(v).replace(/[^0-9.\-]/g,"");
  if(t===""||t==="-"||t===".") return null; const x=Number(t); return isFinite(x)?x:null; }
function opts(){ return { api_key:$("key").value.trim(), model:$("model").value, provider:$("provider").value,
  output_dir:$("outdir").value.trim(),
  ai_research:$("optResearch").checked, screener:$("optScreener").checked, refresh:$("optRefresh").checked,
  max_searches:Number($("searches").value)||6, detail_min_pct:Number($("minpct").value), benchmark:$("bench").value, remember_key:$("remember").checked }; }
async function post(url, body){ const r = await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify(body||{})}); return r.json(); }
function msg(el, kind, text){ $(el).innerHTML = text ? `<div class="msg ${kind}"></div>` : "";
  if(text) $(el).firstChild.textContent = text; }

async function init(){
  const s = await (await fetch("/api/settings")).json();
  $("vdate").value = s.today; $("vdate").max = s.today;
  keys = s.keys || {}; defaults = s.default_models; quick = s.quick || [];
  $("provider").innerHTML = Object.entries(s.providers).map(([k,v])=>`<option value="${k}" ${k===s.provider?"selected":""}>${v}</option>`).join("");
  $("key").value = keys[s.provider] || ""; $("remember").checked = s.remember_key;
  $("outdir").value = s.output_dir || "";
  setModels([s.model], s.model);
  if($("key").value) loadModels(true);
  $("entities").innerHTML = (s.entities||[]).map(e=>`<option value="${e.replace(/"/g,"&quot;")}">`).join("");
  if((s.entities||[]).length) $("entity").value = s.entities[0];
  benchName = s.benchmarks;
  $("bench").innerHTML = Object.entries(s.benchmarks).map(([k,v])=>`<option value="${k}" ${k===s.benchmark?"selected":""}>${v}</option>`).join("");
  $("optResearch").checked = s.ai_research; $("optScreener").checked = s.screener; $("optRefresh").checked = s.refresh;
  $("searches").value = s.max_searches; $("minpct").value = (s.detail_min_pct ?? 1);
  if(s.preloaded){ fileName = s.preloaded; setFile(s.preloaded, ""); readFile(false); }
}

const KEY_PREFIX = {anthropic:"sk-ant-", openai:"sk-", gemini:"AIza"};
function guessProvider(k){ k=(k||"").trim(); if(k.startsWith("sk-ant-")) return "anthropic";
  if(k.startsWith("AIza")) return "gemini"; if(k.startsWith("sk-")) return "openai"; return ""; }
function setModels(list, pick){ $("model").innerHTML = list.filter(Boolean).map(m=>`<option ${m===pick?"selected":""}>${m}</option>`).join(""); }
async function loadModels(quiet){
  const key = $("key").value.trim(); const prov = $("provider").value;
  if(!key){ if(!quiet) $("modelHint").textContent = "Enter the API key first."; return; }
  $("modelHint").innerHTML = '<span class="spin"></span>Checking the key and loading models';
  const j = await post("/api/models",{api_key:key, provider:prov});
  if(j.error){ $("modelHint").textContent = j.error;
    const g = j.guess; if(g && g !== prov) $("keyHint").textContent = "This key looks like a " + $("provider").querySelector(`[value=${g}]`).textContent + " key - choose that provider.";
    setModels([defaults[prov]], defaults[prov]); return; }
  const cur = $("model").value;
  setModels(j.models, j.models.includes(cur) ? cur : j.default);
  $("modelHint").textContent = `Key accepted. ${j.models.length} models available.`;
  $("keyHint").textContent = "";
}
function keyChanged(){
  const g = guessProvider($("key").value);
  if(g && g !== $("provider").value){ $("provider").value = g; setModels([defaults[g]], defaults[g]);
    $("keyHint").textContent = "Provider set to " + $("provider").selectedOptions[0].textContent + " to match the key."; }
  loadModels(true);
}

// ---- folder picker ----
let pkPath = "";
async function pkLoad(path){
  const j = await (await fetch("/api/dirs?path=" + encodeURIComponent(path||""))).json();
  pkPath = j.path; $("pkPath").textContent = j.path; $("pkUp").disabled = !j.parent;
  $("pkUp").onclick = ()=>pkLoad(j.parent);
  const ul = $("pkList"); ul.innerHTML = "";
  if(j.error){ ul.innerHTML = '<li class="none"></li>'; ul.firstChild.textContent = j.error; return; }
  if(!j.dirs.length){ ul.innerHTML = '<li class="none">No sub-folders here. You can use this folder or create a new one.</li>'; }
  j.dirs.forEach(d=>{ const li=document.createElement("li"); const b=document.createElement("button");
    b.type="button"; b.textContent = "\u{1F4C1}  " + d; b.onclick = ()=>pkLoad(j.path.replace(/[\\/]$/,"") + (j.path.includes("\\")?"\\":"/") + d);
    li.appendChild(b); ul.appendChild(li); });
}
function pkOpen(){
  $("pkQuick").innerHTML = ""; quick.forEach(q=>{ const b=document.createElement("button"); b.type="button";
    b.textContent=q.label; b.onclick=()=>pkLoad(q.path); $("pkQuick").appendChild(b); });
  $("picker").showModal(); pkLoad($("outdir").value);
}
$("btnPick").onclick = pkOpen;
$("pkClose").onclick = ()=>$("picker").close();
$("pkUse").onclick = ()=>{ $("outdir").value = pkPath; $("picker").close(); };
$("pkMk").onclick = async ()=>{ const j = await post("/api/mkdir",{path:pkPath, name:$("pkNew").value});
  if(j.error){ alert(j.error); return; } $("pkNew").value=""; pkLoad(j.path); };

function setFile(name, kind){
  $("dropTitle").textContent = name; $("dropHint").textContent = (kind? kind + " file. ":"") + "Click to choose a different file";
  $("btnRead").disabled = false; $("btnAI").disabled = false;
}

async function upload(file){
  msg("readMsg","","");
  $("dropTitle").textContent = file.name; $("dropHint").innerHTML = '<span class="spin"></span>Uploading';
  const r = await fetch("/api/upload",{method:"POST",headers:{"X-Filename":encodeURIComponent(file.name)},body:file});
  const j = await r.json(); fileName = j.name; setFile(j.name, j.kind); readFile(false);
}

async function readFile(forceAI){
  if(forceAI && !$("key").value.trim()){ msg("readMsg","warn","Enter your API key in step 1 to read the file with AI."); return; }
  $("dropHint").innerHTML = '<span class="spin"></span>' + (forceAI? "Reading with AI - this can take a minute" : "Reading the statement");
  $("btnRead").disabled = $("btnAI").disabled = true;
  const j = await post("/api/read",{...opts(), password:$("pw").value, force_ai:!!forceAI});
  $("btnRead").disabled = $("btnAI").disabled = false;
  $("dropHint").textContent = "Click to choose a different file";
  if(j.need_password){ $("pw").focus(); msg("readMsg","warn",j.error + " Then press 'Read file again'."); return; }
  if(j.error){ msg("readMsg","err",j.error); return; }
  rows = j.rows; render();
  const info = j.info || {};
  $("paperHead").innerHTML = "";
  [["File", fileName],["Type", info.kind_label],["How", info.method],["Columns used", info.columns]]
    .filter(x=>x[1]).forEach(([k,v])=>{ const c=document.createElement("span"); c.className="chip";
      c.innerHTML = k + ": <b></b>"; c.querySelector("b").textContent = v; $("paperHead").appendChild(c); });
  const extra = (j.notes||[]).join(" ");
  msg("readMsg", info.method && info.method.includes("AI") ? "warn" : "ok",
      `${rows.length} holdings read. ` + (info.method && info.method.includes("AI") ? "Please check each row against the statement." : "") + (extra? " " + extra : ""));
}

function render(){
  const tb = $("tbody");
  if(!rows.length){ tb.innerHTML = '<tr><td colspan="8" class="empty">No holdings. Use "Add a row" or select another statement.</td></tr>'; $("tfoot").innerHTML=""; return; }
  tb.innerHTML = "";
  rows.forEach((r,i)=>{
    const tr = document.createElement("tr"); if(r.amb) tr.className = "flag";
    const cell = (key, cls, label) => { const td=document.createElement("td"); if(cls) td.className=cls;
      const inp=document.createElement("input"); inp.type="text";
      inp.value = (key==="qty"||key==="avg_cost"||key==="total_cost") ? fmt(r[key], key==="qty"?4:2) : (r[key]||"");
      inp.setAttribute("aria-label", label + " row " + (i+1));
      inp.addEventListener("change", ()=>{ let v = inp.value.trim();
        if(key==="qty"||key==="avg_cost"||key==="total_cost"){ v = num(v); }
        if(key==="symbol"||key==="isin") v = v.toUpperCase();
        r[key] = v;
        if(key==="avg_cost" && v!==null && num(r.qty)) { r.total_cost = Math.round(v*num(r.qty)*100)/100; r.amb=false; }
        if(key==="total_cost") { r.amb=false; if(v!==null && num(r.qty)) r.avg_cost = Math.round(v/num(r.qty)*10000)/10000; }
        if(key==="qty" && num(r.avg_cost)!==null && !r.amb) r.total_cost = Math.round(num(r.avg_cost)*v*100)/100;
        render(); });
      td.appendChild(inp); return td; };
    const n=document.createElement("td"); n.className="n"; n.textContent=i+1; tr.appendChild(n);
    tr.appendChild(cell("name","","Script name")); tr.appendChild(cell("symbol","","Symbol"));
    tr.appendChild(cell("isin","","ISIN")); tr.appendChild(cell("qty","num","Quantity"));
    tr.appendChild(cell("avg_cost","num","Average cost")); tr.appendChild(cell("total_cost","num","Total cost"));
    const x=document.createElement("td"); x.className="x"; const b=document.createElement("button");
    b.type="button"; b.textContent="×"; b.setAttribute("aria-label","Remove row "+(i+1)+" "+(r.name||""));
    b.onclick=()=>{ rows.splice(i,1); render(); }; x.appendChild(b); tr.appendChild(x);
    tb.appendChild(tr);
  });
  const tot = rows.reduce((a,r)=>a+(num(r.total_cost)||0),0);
  $("tfoot").innerHTML = `<tr><td></td><td colspan="3">${rows.length} holdings</td><td></td><td></td><td class="num">${fmt(tot,2)}</td><td></td></tr>`;
  $("ambHint").style.display = rows.some(r=>r.amb) ? "inline" : "none";
}

async function go(){
  $("goMsg").textContent = "";
  if(!$("entity").value.trim()){ $("goMsg").textContent = "Enter the name of the entity in step 1."; $("entity").focus(); return; }
  if(!$("vdate").value){ $("goMsg").textContent = "Enter the valuation date in step 1."; $("vdate").focus(); return; }
  const valid = rows.filter(r=>(r.name||r.symbol) && num(r.qty)>0);
  if(!valid.length){ $("goMsg").textContent = "Select a holding statement first (step 2)."; return; }
  if(!$("outdir").value.trim()){ $("goMsg").textContent = "Choose the folder to save the report in."; return; }
  if(!$("key").value.trim() && $("optResearch").checked)
    $("goMsg").textContent = "No API key: the report will be made without web research.";
  const j = await post("/api/run",{...opts(), rows:valid, entity:$("entity").value.trim(), date:$("vdate").value});
  if(j.error){ $("goMsg").textContent = j.error; return; }
  startPolling("report");
}

async function check(){
  const j = await post("/api/selftest", opts());
  if(j.error){ $("goMsg").textContent = j.error; return; }
  startPolling("check");
}

function startPolling(kind){
  $("runBox").style.display="block"; $("log").textContent=""; since=0; $("done").classList.remove("show");
  $("btnGo").disabled = true; $("btnCheck").disabled = true;
  $("runBox").scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto":"smooth", block:"start"});
  clearInterval(polling); polling = setInterval(()=>poll(kind), 900); poll(kind);
}

async function poll(kind){
  let j; try{ j = await (await fetch("/api/status?since="+since)).json(); }catch(e){ return; }
  if(j.lines.length){ const L=$("log"); L.textContent += j.lines.join("\n") + "\n"; L.scrollTop = L.scrollHeight; }
  since = j.next;
  const p = j.progress || {};
  $("stage").textContent = kind==="check" ? "Checking connections" : (p.stage || "Working");
  $("count").textContent = p.total ? `${Math.min(p.done+1,p.total)} of ${p.total}` : "";
  let pct;
  if(kind==="check"){ pct = j.status==="running" ? 50 : 100; }
  else { const si = Math.max(0, STAGES.indexOf(p.stage)); const part = p.total ? p.done/p.total : 0;
    pct = Math.round(((si + part) / (STAGES.length-1)) * 100); }
  $("fill").style.width = Math.min(100,pct) + "%";
  if(j.status !== "running"){
    clearInterval(polling); $("btnGo").disabled=false; $("btnCheck").disabled=false;
    if(j.status==="done" && kind==="report"){ $("stage").textContent="Report ready"; $("count").textContent="";
      $("doneName").textContent = j.result; $("done").classList.add("show"); $("fill").style.width="100%"; }
    else if(j.status==="done"){ $("stage").textContent="Check finished - see the results below"; $("fill").style.width="100%"; }
    else { $("stage").textContent = "Stopped: " + (j.error||"see the log below"); }
  }
}

$("drop").onclick = ()=>$("file").click();
$("drop").onkeydown = e=>{ if(e.key==="Enter"||e.key===" "){ e.preventDefault(); $("file").click(); } };
$("file").onchange = e=>{ if(e.target.files[0]) upload(e.target.files[0]); e.target.value=""; };
["dragenter","dragover"].forEach(ev=>$("drop").addEventListener(ev,e=>{e.preventDefault();$("drop").classList.add("over");}));
["dragleave","drop"].forEach(ev=>$("drop").addEventListener(ev,e=>{e.preventDefault();$("drop").classList.remove("over");}));
$("drop").addEventListener("drop",e=>{ const f=e.dataTransfer.files[0]; if(f) upload(f); });
$("btnRead").onclick = ()=>readFile(false);
$("btnAI").onclick = ()=>readFile(true);
$("btnAdd").onclick = ()=>{ rows.push({name:"",symbol:"",isin:"",qty:null,avg_cost:null,total_cost:null,amb:false,amb_lines:[]}); render();
  const ins=$("tbody").querySelectorAll("tr:last-child input"); if(ins[0]) ins[0].focus(); };
$("provider").onchange = ()=>{ const p=$("provider").value; $("key").value = keys[p] || "";
  $("keyHint").textContent=""; setModels([defaults[p]], defaults[p]); if($("key").value) loadModels(true);
  else $("modelHint").textContent = "Enter the key, then the models available to it are listed."; };
$("key").addEventListener("change", keyChanged);
$("btnModels").onclick = ()=>loadModels(false);
$("btnShow").onclick = ()=>{ const k=$("key"); const show = k.type==="password"; k.type = show?"text":"password"; $("btnShow").textContent = show?"Hide":"Show"; };
$("btnGo").onclick = go;
$("btnCheck").onclick = check;
$("btnOpen").onclick = ()=>post("/api/open",{what:"pdf"});
$("btnFolder").onclick = ()=>post("/api/open",{what:"folder"});
$("btnQuit").onclick = async ()=>{ await post("/api/quit"); document.body.innerHTML =
  '<div style="max-width:560px;margin:80px auto;font:16px Segoe UI,system-ui;color:#14213D"><h2>The app has been closed.</h2><p>You can close this browser tab. To start again, double-click RUN_WINDOWS.bat.</p></div>'; };
init();
</script>
</body></html>
"""


if __name__ == "__main__":
    try:
        code = main()
    except KeyboardInterrupt:
        code = 1
        print("\nStopped.")
    except Exception as e:
        code = 1
        log("\nSomething went wrong: " + str(e))
        log(traceback.format_exc())
        log("Please send the file output\\run_log.txt so the problem can be fixed.")
    if sys.stdin and sys.stdin.isatty() and "--no-pause" not in sys.argv:
        try:
            input("\nPress Enter to close...")
        except Exception:
            pass
    sys.exit(code)
