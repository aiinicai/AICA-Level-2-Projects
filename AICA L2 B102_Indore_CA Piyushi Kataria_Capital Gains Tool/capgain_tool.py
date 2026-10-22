#!/usr/bin/env python3
"""
Offline Capital Gains Summariser (India) - Equity & Mutual Funds      [v2]
==========================================================================
Reads capital-gain reports of ANY Indian broker / RTA (CAMS, KFintech) and produces
one Excel workbook:  Summary  |  Workings  |  Exceptions  |  Reconciliation  |  Parse log

Nothing leaves your computer - no network calls anywhere in this file.

Run (GUI):  python capgain_tool.py
Run (UI): python capgain_tool.py   -> opens the tool in your browser (offline, 127.0.0.1)
Run (CLI):  python capgain_tool.py a.xlsx b.xls c.csv --out summary.xlsx [--eq-charges 1000] [--mf-charges 0]  (mf-charges = Non-Equity)

Needs:  pip install pandas openpyxl xlrd python-dateutil      (lxml only if a broker gives an HTML ".xls")

HOW IT STAYS FORMAT-PROOF
  * Headers are recognised by MEANING (words like buy/sell/purchase/redemption + date/value/price/FMV),
    not by column position, and are searched anywhere on the sheet - junk rows above are ignored.
  * Two-row headers, several tables on one sheet, section titles (Intraday / Short Term / Long Term ...),
    ".xls" files that are really text/HTML are all handled.
  * Two plain "Date" columns (CAMS / KFintech) are resolved from the data (earlier = purchase).
  * Per-unit prices x quantity are used when a report has no value column.
  * Every file is reconciled against the "Total / Sub total" rows and broker-reported gains printed in it.
  * Anything doubtful goes to the Exceptions sheet - nothing is silently dropped or guessed.

TAX RULES CODED (all in the CONFIG block - verify against the Act in force before filing)
  * Listed equity shares / equity-oriented MF units : held > 12 months => LTCG, else STCG
  * Grandfathering (acquired on/before 31-01-2018, LTCG):  Cost = max( actual cost , min( FMV 31-01-2018 , sale value ) )
  * Gains are split by sale date (before / on-after 23-07-2024) because the rates differ
  * STT is never deducted.  Intraday / speculative and F&O are business income and are listed separately.
  * Debt / non-equity MF, gold & silver ETFs etc. are flagged for manual review (term rules differ).
"""
import re, sys, os, io, csv, json, math, argparse, warnings, datetime as dt
from collections import defaultdict, OrderedDict

import pandas as pd
from dateutil.relativedelta import relativedelta

warnings.filterwarnings("ignore")

# =============================================================================== CONFIG
GF_DATE = pd.Timestamp("2018-01-31")           # FMV date for grandfathering
RATE_CHANGE = pd.Timestamp("2024-07-23")       # Finance (No.2) Act 2024 rate change
EQ_MONTHS = 12                                 # holding period for listed equity / equity MF
NONEQ_MF_MONTHS = 24                           # fallback for non-equity MF when broker gives no term
RATES_NOTE = ("Indicative rates (verify): sale before 23-Jul-2024 - STCG 111A 15%, LTCG 112A 10% above Rs 1,00,000; "
              "on/after 23-Jul-2024 - STCG 20%, LTCG 12.5% above Rs 1,25,000.")

# =============================================================================== LOW-LEVEL HELPERS
def clean(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, str):
        s = v.replace("\xa0", " ").strip()
        return s if s and s.lower() not in ("nan", "nat", "none") else None
    return v


def to_num(v):
    v = clean(v)
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, (pd.Timestamp, dt.datetime, dt.date)):
        return None
    s = str(v).strip()
    if s.lower() in ("na", "n/a", "-", "--", "nil", "null", "nan"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    s2 = re.sub(r"[₹,\s]|rs\.?|inr", "", s, flags=re.I).strip("()")
    if s2.endswith("-") and s2[:-1].replace(".", "").isdigit():
        s2, neg = s2[:-1], True
    try:
        x = float(s2)
    except ValueError:
        return None
    return -x if neg else x


_DATE_FORMATS = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d-%b-%Y", "%d-%B-%Y",
                 "%d %b %Y", "%d %B %Y", "%d/%b/%Y", "%d/%m/%y", "%d-%b-%y", "%d-%m-%y", "%b %d, %Y",
                 "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%d-%b-%Y %H:%M:%S", "%Y/%m/%d", "%d %b, %Y"]


def to_date(v):
    v = clean(v)
    if v is None:
        return None
    if isinstance(v, (pd.Timestamp, dt.datetime, dt.date)):
        try:
            t = pd.Timestamp(v).normalize()
            return t if 1990 <= t.year <= 2100 else None
        except Exception:
            return None
    if isinstance(v, (int, float)):
        if 25000 < v < 60000:
            return pd.Timestamp("1899-12-30") + pd.Timedelta(days=int(v))
        return None
    s = str(v).strip()
    if not re.search(r"\d", s) or len(s) > 30:
        return None
    for f in _DATE_FORMATS:
        try:
            t = pd.Timestamp(dt.datetime.strptime(s, f)).normalize()
            return t if 1990 <= t.year <= 2100 else None
        except ValueError:
            continue
    return None


def hnorm(s):
    s = str(s).lower().replace("\xa0", " ")
    s = re.sub(r"[\n\r_]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# =============================================================================== FILE READING
def sniff(path):
    with open(path, "rb") as f:
        head = f.read(4096)
    if head[:4] == b"PK\x03\x04":
        return "xlsx"
    if head[:8] == bytes.fromhex("D0CF11E0A1B11AE1"):
        return "xls"
    low = head.lower()
    if b"<table" in low or b"<html" in low:
        return "html"
    return "text"


def _decode(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", "ignore")


def load_sheets(path):
    """-> list of (sheet_name, rows) ; rows = list of lists of cleaned cells."""
    kind = sniff(path)
    out = []
    if kind in ("xlsx", "xls"):
        x = pd.read_excel(path, sheet_name=None, header=None, dtype=object,
                          engine="openpyxl" if kind == "xlsx" else "xlrd")
        for name, df in x.items():
            out.append((str(name), [[clean(c) for c in r] for r in df.itertuples(index=False)]))
    elif kind == "html":
        for k, df in enumerate(pd.read_html(io.StringIO(_decode(path)), header=None)):
            out.append((f"table{k+1}", [[clean(c) for c in r] for r in df.itertuples(index=False)]))
    else:
        lines = _decode(path).splitlines()
        sample = "\n".join(lines[:40])
        delim = max(["\t", ",", ";", "|"], key=lambda d: sample.count(d))
        rows = [[clean(c) for c in r] for r in csv.reader(lines, delimiter=delim)]
        out.append((os.path.splitext(os.path.basename(path))[0], rows))
    return out


# =============================================================================== HEADER RECOGNITION
BUY_W = re.compile(r"\b(buy|bought|purchas\w*|entry|acqui\w*|subscri\w*|inflow\w*)\b|unit cost|original (purchase )?cost", re.I)
SELL_W = re.compile(r"\b(sell|sold|sale|sales|exit|redeem\w*|redemp\w*|outflow\w*|proceeds|consideration|full value)\b", re.I)

_CUSTOM = []  # user-supplied extra header rules, loaded from capgain_custom_headers.json


def load_custom_rules():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capgain_custom_headers.json")
    if os.path.exists(p):
        try:
            for field, pats in json.load(open(p, encoding="utf-8")).items():
                for pat in pats:
                    _CUSTOM.append((re.compile(pat, re.I), field))
        except Exception as e:
            print("custom header file ignored:", e)


def classify(text):
    """Header text -> (field, priority) or None.  Lower priority number wins when two columns claim a field."""
    t = hnorm(text)
    if not t:
        return None
    for rx, field in _CUSTOM:
        if rx.search(t):
            return (field, 0)
    if "folio" in t:
        return ("folio", 3)
    if (re.search(r"\b(id|code|pan|guardian\w*|status|remarks?|address|expiry|strike|turnover|serial|sr\.? ?no\.?|s\.? ?no\.?|tax perc|tax deduct|surcharge|tds)\b", t)
            or re.match(r"^(desc|tax$)", t) or re.search(r"acquisition type|sell type|purchase type|indexed|trxn type", t)):
        return None
    # ---- 31-Jan-2018 FMV family (before value/price rules)
    if re.search(r"fmv|fair market|grandfather|31 ?(st)? ?[./-]? ?(01|jan)[a-z]*[ ./-]*(20)?18|as on 31", t):
        if re.search(r"(?<!per )\bunits? as on|grandfathered units", t):
            return None
        if "cost" in t:
            return ("gf_cost", 3)
        if re.search(r"\b(per unit|price|nav|rate)\b", t):
            return ("fmv_unit", 4 if "considering" in t else 1)
        if re.search(r"market value as on|grandfathered value|\btotal\b", t):
            return ("fmv_total", 2)
        return ("fmv_any", 3)
    if re.search(r"computation|price considered|applicable", t):
        return ("cost_broker", 9)
    if re.search(r"tax treatment|type of (gain|profit)|gain type|capital gain type|holding type|^term$", t):
        return ("term_label", 3)
    if re.search(r"period of holding|holding period|days held|no\.? of days", t):
        return ("hold_days", 3)
    # ---- dates
    if re.search(r"\bdate\b|\bdt\b|date of", t):
        if re.search(r"ex.?date|posting|expiry|record|dividend", t):
            return None
        b, s = BUY_W.search(t), SELL_W.search(t)
        if b and not s:
            return ("buy_date", 1)
        if s and not b:
            return ("sell_date", 1)
        return ("date_any", 5)
    # ---- quantity
    if re.search(r"\b(qty|quantity|units?)\b|redunits", t) and not re.search(r"per unit|unit cost|price|rate|\bcost\b|value|amount|\bnav\b", t):
        if re.search(r"as on|current|source|balance|opening|closing|purh|pending|holding", t):
            return None
        return ("qty", 1 if re.search(r"matched|closed|redunits|sold|sell|sale|redeem", t) else 3)
    # ---- broker gains
    if re.search(r"p ?[&/] ?l|\bpl\b|profit|gain|loss|income", t) or re.fullmatch(r"(short|long) term( with(out)? index)?|speculat\w*", t):
        if "index" in t and not re.search(r"without|w/o", t):
            return None
        if "buyback" in t:
            return ("gain_buyback", 8)
        if re.search(r"speculat|intraday", t):
            return ("gain_intra", 2)
        if re.search(r"short|<\s*1|\bst\b|stcg", t):
            return ("gain_st", 2)
        if re.search(r"long|>\s*1|\blt\b|ltcg", t):
            return ("gain_lt", 2)
        if "taxable" in t:
            return ("gain_taxable", 3)
        if re.search(r"\bnet\b", t):
            return ("gain_net", 6)
        if re.search(r"gross|excluding all charges", t):
            return ("gain_gross", 7)
        if re.search(r"\btotal\b", t):
            return ("gain_total", 5)
        return ("gain_any", 4)
    # ---- values
    if re.search(r"value|amount|amt|consideration|proceeds", t) and "turnover" not in t:
        b, s = BUY_W.search(t), SELL_W.search(t)
        if s and not b:
            return ("sell_value", 1)
        if b and not s:
            return ("buy_value", 1)
        return ("amount_any", 6)
    # ---- prices
    if re.search(r"total (buy|sell|sale|purchase)? ?cost|total cost", t):
        return None
    if re.search(r"\b(price|rate|nav|per unit)\b|unit cost|cost of acquisition|(original|purchase) (purchase )?cost", t):
        b, s = BUY_W.search(t), SELL_W.search(t)
        if s and not b:
            return ("sell_price", 1)
        if b and not s:
            return ("buy_price", 4 if "cost of acquisition" in t else 1)
        return ("price_any", 6)
    # ---- charges
    if re.search(r"\bstt\b|\bctt\b|securities transaction tax", t):
        return ("stt", 2)
    if re.search(r"\btotal\b", t) and re.search(r"charge|expense", t):
        return ("charges_total", 5)
    if re.search(r"b(ro|o)kerage|\b[cis]?gst\b|service tax|stamp|sebi|ipft|clearing|misc|expenses?|levies|levy|"
                 r"exchange transaction|transaction charges|other charges|charges|\bdp\b", t):
        return ("expense", 2)
    # ---- identity
    if re.search(r"\bisin\b", t):
        return ("isin", 1) if "name" not in t else None
    if re.search(r"(security|asset|instrument) (type|class)|sub asset|^category$|type of instrument|^segment$", t):
        return ("asset_type", 3)
    if "scheme name" in t:
        return ("name", 1)
    if re.search(r"\b(stock|scrip|script|security|symbol|instrument)( name)?\b", t):
        return ("name", 2)
    if t == "name":
        return ("name", 4)
    if t.endswith("fund name") or t == "fund":
        return ("name", 5)
    return None


def expense_label(t):
    t = hnorm(t)
    for rx, lab in [(r"b(ro|o)kerage", "Brokerage"), (r"levy", "Exchange / transaction charges"), (r"\b[cis]?gst\b|service tax", "GST / service tax"),
                    (r"exchange transaction|transaction charges", "Exchange / transaction charges"),
                    (r"sebi", "SEBI turnover fees"), (r"stamp", "Stamp duty"), (r"ipft", "IPFT"),
                    (r"clearing", "Clearing charges"), (r"misc|other", "Other / misc charges"),
                    (r"sale expenses", "Sale-side expenses"), (r"purchase expenses", "Purchase-side expenses"),
                    (r"levies|statutory", "Charges & statutory levies"), (r"\bdp\b", "DP charges")]:
        if re.search(rx, t):
            return lab
    return t.title()


class Header:
    """Resolved column map of one table."""
    def __init__(self, texts, consumed, rownum):
        self.consumed, self.rownum, self.texts = consumed, rownum, texts
        self.cand = defaultdict(list)          # field -> [(prio, col)]
        self.expense_cols, self.stt_cols = [], []
        for c, tx in texts.items():
            r = classify(tx)
            if r:
                f, p = r
                if f == "expense":
                    self.expense_cols.append((c, expense_label(tx)))
                elif f == "stt":
                    self.stt_cols.append(c)
                else:
                    self.cand[f].append((p, c))
        totals = [(c, l) for c, l in self.expense_cols
                  if re.fullmatch(r"(buy ?(&|and) ?sell )?(total )?(expenses?|charges)( \(.*\))?", hnorm(texts[c]))]
        if totals:
            self.expense_cols = totals[:1]
        self.col = {}
        self.embedded = bool(re.search(r"(considering|including|net of|after)\s+(all\s+|buy\s+side\s+|sell\s+side\s+)?(brokerage|charges)",
                                       " | ".join(hnorm(x) for x in texts.values())))

    def valid(self):
        nd = sum(len(self.cand[k]) for k in ("buy_date", "sell_date", "date_any"))
        nv = sum(len(self.cand[k]) for k in ("buy_value", "sell_value", "buy_price", "sell_price", "amount_any", "price_any"))
        return nd >= 2 and nv >= 1

    def resolve(self, sample):
        """sample = a few data rows; used to settle 'Date'/'Date' ambiguity and generic price/amount columns."""
        def best(f):
            return sorted(self.cand[f])[0][1] if self.cand.get(f) else None
        b, s = best("buy_date"), best("sell_date")
        anys = [c for _, c in sorted(self.cand.get("date_any", []), key=lambda x: x[1])]
        if (b is None or s is None) and anys:
            means = {}
            for c in anys:
                ds = [to_date(r[c]) for r in sample if c < len(r) and to_date(r[c]) is not None]
                means[c] = (sum(d.value for d in ds) / len(ds)) if ds else float("nan")
            cs = [c for c in anys if not math.isnan(means[c])] or anys
            cs = sorted(cs, key=lambda c: (means.get(c, 0), c))
            if b is None and s is None and len(cs) >= 2:
                b, s = cs[0], cs[-1]
            elif b is None and cs:
                b = cs[0]
            elif s is None and cs:
                s = cs[-1]
        col = {}
        qs = sorted(self.cand.get("qty", []))
        if len(qs) >= 2 and qs[0][1] != qs[1][1] and qs[0][0] < qs[1][0]:
            col["qty_total"] = qs[1][1]            # e.g. CAMS: 'Units' (whole redemption) next to 'RedUnits' (this lot)
        if b is not None: col["buy_date"] = b
        if s is not None: col["sell_date"] = s
        for f in ("name", "isin", "asset_type", "folio", "qty", "buy_value", "sell_value", "buy_price", "sell_price",
                  "fmv_unit", "fmv_total", "fmv_any", "gf_cost", "term_label", "hold_days",
                  "gain_st", "gain_lt", "gain_intra", "gain_taxable", "gain_any", "gain_net", "gain_total", "gain_gross", "charges_total"):
            c = best(f)
            if c is not None:
                col[f] = c
        # generic price / amount columns take the side of the nearest date column on their left (CAMS / KFin layout)
        dpos = {"buy": b, "sell": s}
        def side(c):
            left = [(dc, sd) for sd, dc in dpos.items() if dc is not None and dc < c]
            if left: return max(left)[1]
            right = [(dc, sd) for sd, dc in dpos.items() if dc is not None and dc > c]
            return min(right)[1] if right else None
        for gen, tail in (("price_any", "price"), ("amount_any", "value")):
            for _, c in sorted(self.cand.get(gen, []), key=lambda x: x[1]):
                sd = side(c)
                if sd and f"{sd}_{tail}" not in col:
                    col[f"{sd}_{tail}"] = c
        self.col = col
        self.fmv_any_is_total_by_header = "fmv_unit" in col
        return self


DERIV_HEADER = re.compile(r"strike|expiry|option type|\blot\b|contract name", re.I)
DERIV_NAME = re.compile(r"\b(\d{4,6}\s?(CE|PE)|FUT(IDX|STK)?|OPT(IDX|STK)|(CE|PE))\b\s*$|\d{2}[A-Z]{3}\d{0,2}\s?(FUT|CE|PE)", re.I)


def try_header(rows, i, ncols):
    row = rows[i]
    cells = [(j, c) for j, c in enumerate(row) if c is not None]
    if len(cells) < 4:
        return None
    nontext = sum(1 for _, c in cells if (not isinstance(c, str)) or to_date(c) is not None
                  or (to_num(c) is not None and not re.search(r"[A-Za-z]", str(c))))
    if nontext >= 2:
        return None
    texts = {j: str(c) for j, c in cells}
    consumed = 1
    if i + 1 < len(rows):                                  # optional second header row (Kotak style)
        c2 = [(j, c) for j, c in enumerate(rows[i + 1]) if c is not None]
        if len(c2) >= 2 and all(isinstance(c, str) and to_num(c) is None and to_date(c) is None for _, c in c2):
            if len([j for j, _ in c2 if j not in texts]) >= 1:
                sub, merged, last = dict(c2), {}, None
                for j in range(ncols):
                    m, s = texts.get(j), sub.get(j)
                    if m is not None: last = m
                    if s is not None:
                        merged[j] = ((m if m is not None else (last or "")) + " " + s).strip()
                    elif m is not None:
                        merged[j] = m
                texts, consumed = merged, 2
    h = Header(texts, consumed, i + 1)
    return h if h.valid() else None


# =============================================================================== SHEET PARSING
DERIV_SHEET = re.compile(r"deriv|f\s*&\s*o|\bfno\b|futur|option|commodit|currenc", re.I)
IGNORE_SHEET = re.compile(r"dividend|ledger|non.?trade|open position|other debit|investor|portfolio|interest", re.I)
DERIV_TITLE = re.compile(r"deriv|futures|options|\bf ?& ?o\b|commodit|currenc", re.I)
STOP_TITLE = re.compile(r"disclaimer|^note", re.I)
NOT_SALE_TITLE = re.compile(r"transfer transactions|open sell|open holdings|open position|qty breakup|unrealis", re.I)
TOTAL_ROW = re.compile(r"^\s*([a-z &/()-]{0,25}\s)?(sub[\s-]*total|grand[\s-]*total|total)\s*:?\s*$", re.I)
REPORT_LABEL = re.compile(r"p ?& ?l|profit|gain|loss|charges|expenses|\bstt\b|brokerage|turnover|taxable", re.I)
NONEQ_NAME = re.compile(r"gold|silver|liquid|gilt|debt|bond|sgb|g-?sec|treasury|money market|overnight|ncd|debenture|fixed", re.I)


def section_flags(sec):
    s = (sec or "").lower()
    return dict(intraday=bool(re.search(r"intraday|speculat", s)),
                st=bool(re.search(r"short ?term", s)), lt=bool(re.search(r"long ?term", s)),
                buyback="buyback" in s,
                noneq=bool(re.search(r"debt|non.?equity|other than equity", s)),
                nostt=bool(re.search(r"stt not paid|non.?stt|without stt", s)))


def parse_sheet(fname, sheet, rows, log):
    ncols = max((len(r) for r in rows), default=0)
    recs, excl, errs, checks, rlines = [], [], [], [], []
    deriv_rows = 0
    hdr, section, mode, block = None, "", "normal", 0
    acc_sub, acc_tot = [], []
    sheet_deriv = bool(DERIV_SHEET.search(sheet))
    if IGNORE_SHEET.search(sheet) and not re.search(r"capital|gain|p ?& ?l", sheet, re.I):
        log.append((fname, sheet, "-", "Skipped sheet (not a capital-gain table: dividends / ledger / holdings)"))
        return recs, excl, errs, checks, rlines
    if sheet_deriv:
        log.append((fname, sheet, "-", "Skipped sheet: derivatives / commodity / currency (business income, not capital gains)"))
        return recs, excl, errs, checks, rlines
    i = 0
    while i < len(rows):
        row = rows[i]
        ne = [(j, c) for j, c in enumerate(row) if c is not None]
        if not ne:
            i += 1
            continue
        h = try_header(rows, i, ncols)
        if h:
            nxt = i + h.consumed
            sample = [r for r in rows[nxt:nxt + 80] if sum(1 for c in r if c is not None) >= 3][:60]
            h.resolve(sample)
            if "buy_date" in h.col and "sell_date" in h.col and ("sell_value" in h.col or "sell_price" in h.col):
                if any(DERIV_HEADER.search(hnorm(x)) for x in h.texts.values()):
                    mode, hdr = "excluded", h
                    log.append((fname, sheet, h.rownum, "Derivatives table (strike / expiry columns) - ignored: business income, not capital gains"))
                    i = nxt
                    continue
                hdr, block = h, block + 1
                hdr.block = block
                acc_sub, acc_tot = [], []
                log.append((fname, sheet, h.rownum, "Header found. Mapped: " + ", ".join(
                    f"{k}=[{hnorm(h.texts[v])[:28]}]" for k, v in h.col.items()) +
                    (" | per-row charges: " + ", ".join(l for _, l in h.expense_cols) if h.expense_cols else "") +
                    (" | charges already inside buy/sell values" if h.embedded else "")))
                i = nxt
                continue
        # ---- title / section row
        if hdr is not None and not any(isinstance(c, str) for _, c in ne) and len(ne) >= 2 \
                and not any(to_date(c) is not None and not isinstance(c, (int, float)) for _, c in ne):
            rep_ = broker_gain(row, hdr)
            if rep_ is not None and acc_sub:
                checks.append((fname, sheet, i + 1, "unlabeled total", len(acc_sub), sum(x for x in acc_sub if x is not None), rep_))
            acc_sub, acc_tot = [], []
            i += 1
            continue
        if len(ne) <= 3 and all(isinstance(c, str) and to_num(c) is None and to_date(c) is None for _, c in ne) \
                and len(ne[0][1]) < 120 \
                and not TOTAL_ROW.match(ne[0][1]) and not re.match(r"^\s*(name|pan|client|account|folio|investor|period|for the period)\b[^a-z]*[:\-]", ne[0][1], re.I):
            title = ne[0][1].strip()
            if len(ne) > 1 and not re.search(r"short|long|intraday|speculat|equity|debt|buyback|delivery", title, re.I):
                i += 1
                continue
            if DERIV_TITLE.search(title):
                mode, hdr = "excluded", None
            elif NOT_SALE_TITLE.search(title):
                mode, hdr = "excluded", None          # off-market transfers, open positions, holdings: not sales
            elif STOP_TITLE.search(title):
                hdr = None
            else:
                mode = "normal"
            section = title
            i += 1
            continue
        # ---- total / sub-total rows -> reconciliation check
        if hdr is not None and any(isinstance(c, str) and TOTAL_ROW.match(c) for _, c in ne):
            label = next(c for _, c in ne if isinstance(c, str) and TOTAL_ROW.match(c)).lower()
            rep = broker_gain(row, hdr)
            acc = acc_sub if "sub" in label else (acc_tot + acc_sub if False else acc_tot)
            if rep is not None and (acc or "sub" not in label):
                mine = sum(x for x in acc if x is not None)
                checks.append((fname, sheet, i + 1, label.strip(), len(acc), mine, rep))
            if "sub" in label:
                acc_sub = []
            else:
                acc_sub, acc_tot = [], []
            i += 1
            continue
        # ---- data row
        if hdr is not None:
            if mode == "excluded":
                deriv_rows += 1
                i += 1
                continue
            r = build_record(row, hdr, fname, sheet, i + 1, section, block)
            if r == "skip":
                pass
            elif isinstance(r, dict) and r.get("_err"):
                errs.append(r)
            elif r:
                recs.append(r)
                acc_sub.append(r["broker_gain"])
                acc_tot.append(r["broker_gain"])
        else:
            for idx, (j, c) in enumerate(ne):                      # client name, for the 'mixed clients' warning
                if isinstance(c, str):
                    m = re.match(r"^\s*(client\s+name|investor\s+name|customer\s+name|account\s+holder|name)\s*:?\s*(.*)$", c, re.I)
                    if m:
                        val = m.group(2).strip() or (str(ne[idx + 1][1]).strip() if idx + 1 < len(ne) and isinstance(ne[idx + 1][1], str) else "")
                        if 3 < len(val) < 60 and to_num(val) is None and classify(val) is None and not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{10}", val):
                            rlines.append((fname, sheet, i + 1, "__client__", val))
            # summary area: capture "label  number" pairs for tie-out
            for j, c in ne:
                if isinstance(c, str) and REPORT_LABEL.search(c) and len(c) < 90:
                    for k in range(j + 1, min(j + 3, len(row))):
                        n = to_num(row[k])
                        if n is not None and row[k] is not None:
                            if len(rlines) < 60:
                                rlines.append((fname, sheet, i + 1, c.strip(), n))
                            break
        i += 1
    if deriv_rows:
        log.append((fname, sheet, "-", f"{deriv_rows} derivative / commodity rows in a 'Derivatives' section ignored (business income)"))
    return recs, excl, errs, checks, rlines


def broker_gain(row, h):
    g = lambda f: to_num(row[h.col[f]]) if f in h.col and h.col[f] < len(row) else None
    parts = [g("gain_st"), g("gain_lt"), g("gain_intra")]
    if any(p is not None for p in parts):
        return sum(p for p in parts if p is not None)
    for f in ("gain_taxable", "gain_any", "gain_total", "gain_net"):
        v = g(f)
        if v is not None:
            return v
    return None


def build_record(row, h, fname, sheet, rownum, section, block):
    gc = lambda f: row[h.col[f]] if f in h.col and h.col[f] < len(row) else None
    bd, sd = to_date(gc("buy_date")), to_date(gc("sell_date"))
    sv_raw, qty = to_num(gc("sell_value")), to_num(gc("qty"))
    if bd is None or sd is None:
        nums = sum(1 for c in row if to_num(c) is not None and not isinstance(c, str))
        if sv_raw is not None and nums >= 3:
            return {"_err": True, "file": fname, "sheet": sheet, "row": rownum,
                    "reason": "Row has amounts but buy/sell date is missing or unreadable - NOT included"}
        return "skip"
    nm_ = str(gc("name") or "")
    if DERIV_NAME.search(nm_.strip()) and not str(gc("isin") or "").strip():
        return "skip"
    bp, sp = to_num(gc("buy_price")), to_num(gc("sell_price"))
    bv, sv = to_num(gc("buy_value")), sv_raw
    flags, notes = [], []
    if bv is None and bp is not None and qty:
        bv = bp * qty
    derived = False
    if sv is None and sp is not None and qty:
        sv = sp * qty
        derived = True
    elif sv is not None and sp is not None and qty and abs(sv - sp * qty) > max(1.0, 0.0005 * abs(sv)):
        qt = to_num(gc("qty_total"))
        if qt and qt > qty * 1.0000001 and abs(sv - sp * qt) <= max(1.0, 0.03 * abs(sv)):
            sv = sv * qty / qt                           # CAMS: 'Amount' is the whole redemption, repeated on every lot row
            notes.append(f"sale value = report amount {sv_raw:,.2f} x lot units {qty:g} / redemption units {qt:g}")
        elif abs(sv - sp * qty) > max(1.0, 0.02 * abs(sv)):
            sv = sp * qty
            notes.append("sale value = units x price (report amount did not match this lot)")
        if sp * qty - sv > max(1.0, 0.003 * sp * qty):
            flags.append(f"Amount received is {sp * qty - sv:,.2f} less than units x NAV ({sp * qty:,.2f}): exit load / charges already netted off")
    if bv is not None and bp is not None and qty and abs(bv - bp * qty) > max(1.0, 0.5 * abs(bv)) and "buy_price" in h.col and "buy_value" not in h.col:
        bv = bp * qty
    exp_detail, exp = OrderedDict(), 0.0
    for c, lab in h.expense_cols:
        x = to_num(row[c]) if c < len(row) else None
        if x:
            exp_detail[lab] = exp_detail.get(lab, 0.0) + x
            exp += x
    if not h.expense_cols and "charges_total" in h.col:
        x = to_num(gc("charges_total"))
        stt_part = sum((to_num(row[c]) or 0) for c in h.stt_cols if c < len(row))
        if x:
            exp = max(x - stt_part, 0.0)
            exp_detail["Total charges (excl. STT)"] = exp
    stt = sum((to_num(row[c]) or 0) for c in h.stt_cols if c < len(row))
    gst, glt, gint = to_num(gc("gain_st")), to_num(gc("gain_lt")), to_num(gc("gain_intra"))
    bterm = ""
    if gint not in (None, 0):
        bterm = "Intraday"
    elif glt not in (None, 0):
        bterm = "LTCG"
    elif gst not in (None, 0):
        bterm = "STCG"
    else:
        tl = str(gc("term_label") or "").lower()
        if re.search(r"intraday|speculat", tl): bterm = "Intraday"
        elif re.search(r"long", tl): bterm = "LTCG"
        elif re.search(r"short", tl): bterm = "STCG"
    sf = section_flags(section)
    if not bterm:
        if sf["intraday"]: bterm = "Intraday"
        elif sf["lt"]: bterm = "LTCG"
        elif sf["st"]: bterm = "STCG"
    asset_val = str(gc("asset_type") or "")
    isin = str(gc("isin") or "").strip().upper()
    name = str(gc("name") or "").strip()
    return dict(file=fname, sheet=sheet, row=rownum, section=section, block=block, name=name, isin=isin, qty=qty,
                bd=bd, sd=sd, bv=bv, sv=sv, exp=exp, exp_detail=exp_detail, stt=stt, embedded=h.embedded,
                fmv_unit=to_num(gc("fmv_unit")), fmv_total=to_num(gc("fmv_total")), fmv_any=to_num(gc("fmv_any")),
                gf_cost=to_num(gc("gf_cost")), has_fmv_unit_col="fmv_unit" in h.col,
                broker_gain=broker_gain(row, h), bterm=bterm, asset_val=asset_val,
                is_mf_table=("folio" in h.col) or bool(re.search(r"mutual|\bmf\b|scheme|cams|kfin|karvy", sheet + " " + fname, re.I))
                            or bool(re.search(r"mutual|scheme", section, re.I))
                            or ("name" in h.col and bool(re.search(r"scheme|fund", hnorm(h.texts[h.col["name"]])))),
                sec=sf, flags=flags, notes=notes, derived=derived)


# =============================================================================== F&O / INTRADAY (business income) WORKINGS
GRP_FNO, GRP_CC, GRP_INTRA = "F&O (futures & options)", "Commodity & currency derivatives", "Intraday equity (speculative)"
BIZ_FILE_RX = re.compile(r"(^|[^a-z])(fno|f&o|fo)([^a-z]|$)|derivativ", re.I)
BIZ_TEXT_RX = re.compile(r"\bf\s*&\s*o\b|\bfno\b|derivatives?\b|futures\s*(and|&)\s*options", re.I)
BIZ_TITLE_RX = re.compile(r"deriv|futures|options|\bf ?& ?o\b|\bfno\b|commodit|currenc", re.I)
CC_RX = re.compile(r"commodit|currenc", re.I)
CHARGE_LBL = re.compile(r"delayed payment|investor protection|b(ro|o)kerage|\bstt\b|\bctt\b|securities transaction|transaction (charge|tax|fee)|exchange|sebi|ipft|stamp|gst|"
                        r"service tax|clearing|regulatory|other charges|levies|\bcess\b|\bdp charges?\b|turnover (fee|charge)", re.I)
PNL_WORDS = re.compile(r"p ?& ?l|profit|gain|loss|realis|realiz", re.I)
HEADS = ("Brokerage", "STT", "Exchange transaction charges", "Other trading charges")


def charge_head(label):
    t = hnorm(label)
    if re.search(r"b(ro|o)kerage", t): return HEADS[0]
    if re.search(r"\bstt\b|securities transaction|\bctt\b|commodity transaction", t): return HEADS[1]
    if re.search(r"turnover (tax|charges?)", t) and "sebi" not in t: return HEADS[2]            # Angel One: 'Turnover Tax' = exchange turnover/transaction charge
    if re.search(r"exchange transaction|exchange (txn|charges|turnover)|transaction charges|regulatory|exchange / transaction", t) and "sebi turnover" not in t:
        return HEADS[2]
    return HEADS[3]


def _bmap(texts):
    """Column map of a derivative table from header words."""
    hs = {c: hnorm(t) for c, t in texts.items()}
    def first(rxs, bad=None):
        for rx in rxs:
            for c in sorted(hs):
                if re.search(rx, hs[c]) and not (bad and re.search(bad, hs[c])):
                    return c
        return None
    m = {"name": first([r"^(scrip|script|symbol|contract|instrument|security|stock)\s*name", r"^symbol$", r"^(scrip|script) ?symbol$", r"^(scrip|script|name)$", r"^contract$"]),
         "qty": first([r"^(closed |net |total )?(qty|quantity)\b"], r"price|rate|value"),
         "buy": first([r"^(total )?buy ?(value|amt|amount)\b", r"^buy$", r"^buy price$"]),
         "sell": first([r"^(total )?sell ?(value|amt|amount)\b", r"^sell$", r"^sell price$"]),
         "pnl": first([r"realis(ed|ed)? ?(p ?& ?l|pnl|profit|gain)", r"^(total )?(pl|p ?& ?l|pnl)$", r"total pl", r"^profit( ?/ ?loss)?$", r"gross (gain|p ?& ?l|pnl|profit)", r"profit ?/ ?loss", r"p ?& ?l"],
                      r"taxable|net|short|long|specul|intra|txn|type"),
         "pnl2": first([r"taxable.*(p ?& ?l|profit|gain)", r"net (profit|p ?& ?l|gain)"]),
         "turn": first([r"turn ?over"], r"fee|charge"),
         "bdate": first([r"^(buy|entry|purchase) ?date$"]), "sdate": first([r"^(sell|exit|sale) ?date$"])}
    return m


def extract_biz(fname, sheet, rows):
    """Collect F&O / commodity / currency derivative entries and their charges from one sheet (never raises)."""
    try:
        return _extract_biz(fname, sheet, rows)
    except Exception as ex:                                                        # a bad sheet must not stop the run
        return dict(file=fname, sheet=sheet, named=False, rows=[], err=repr(ex), report_charges={}, rep_real=None, rep_turn=None)


def _extract_biz(fname, sheet, rows):
    base = os.path.basename(fname)
    top_text = " ".join(str(c) for r in rows[:30] for c in r if isinstance(c, str))
    named = bool(DERIV_SHEET.search(sheet) or BIZ_FILE_RX.search(clean_name(base)) or BIZ_TEXT_RX.search(top_text))
    if IGNORE_SHEET.search(sheet) and not named:
        return dict(file=fname, sheet=sheet, named=False, rows=[], report_charges={}, rep_real=None, rep_turn=None)
    ncols = max((len(r) for r in rows), default=0)
    out, title, cur, section = [], "", None, ""
    rep_ch, rep_real, rep_turn, sec_tot = OrderedDict(), [], [], {}
    rep_grp, sec_grp = {}, None
    seen_hdr = False
    for i, row in enumerate(rows):
        cells = [(j, c) for j, c in enumerate(row) if clean(c) is not None and str(clean(c)).strip() != ""]
        if not cells: continue
        txts = {j: str(c) for j, c in cells}
        first_txt = str(cells[0][1]).strip()
        # ---- table header?
        if len(cells) >= 4 and sum(1 for _, c in cells if isinstance(c, str) and to_num(c) is None) >= max(3, int(len(cells) * 0.7)):
            m = _bmap(txts)
            if m["name"] is not None and sum(1 for k in ("buy", "sell", "pnl", "pnl2", "turn") if m[k] is not None) >= 2:
                h = Header(txts, 1, i + 1)
                exp_cols = list(h.expense_cols)
                if not exp_cols and h.cand.get("charges_total"):
                    exp_cols = [(sorted(h.cand["charges_total"])[0][1], "Total charges")]
                have = {c for c, _ in exp_cols} | set(h.stt_cols)
                for c_, t_ in txts.items():
                    if c_ not in have and re.search(r"^(turnover tax|exchange (service )?tax|ipft charges?|sebi charges?|stamp duty|gst)$", hnorm(t_)):
                        exp_cols.append((c_, str(t_).strip()))
                tblock = f"{sheet} {title}"
                deriv_ctx = named or BIZ_TITLE_RX.search(title) or any(DERIV_HEADER.search(hnorm(t)) for t in txts.values())
                if not named and re.search(r"intraday|speculat|delivery|short ?term|long ?term|buyback", title, re.I) and not BIZ_TITLE_RX.search(title):
                    deriv_ctx = False
                cur = dict(m=m, exp=exp_cols, stt=list(h.stt_cols), title=title, ok=bool(deriv_ctx),
                           grp=GRP_CC if CC_RX.search(tblock) else GRP_FNO)
                seen_hdr = True
                continue
        if len(cells) == 1:                                                         # title / section line
            t = first_txt
            if re.search(r"disclaimer|^note|sebi registration|^cin\b", t, re.I): cur = None
            title = t
            section = hnorm(t)
            continue
        if cur is not None and cur["ok"]:
            m = cur["m"]
            nm = clean(row[m["name"]]) if m["name"] < len(row) else None
            if nm is not None and isinstance(nm, str) and re.search(r"[A-Za-z]", nm) and not TOTAL_ROW.match(nm.strip()) and not re.match(r"\s*total\b", nm, re.I):
                g = lambda k: (to_num(row[m[k]]) if m[k] is not None and m[k] < len(row) else None)
                buy, sell, expl = g("buy"), g("sell"), g("pnl")
                mtm = False
                if buy is not None and sell is not None:
                    pnl = sell - buy
                elif expl is not None:
                    pnl = expl
                elif g("pnl2") is not None:                  # open position marked to market at year end (Angel One style)
                    pnl, mtm = g("pnl2"), True
                else:
                    continue
                ch = OrderedDict()
                for c, lab in cur["exp"]:
                    x = to_num(row[c]) if c < len(row) else None
                    if x: ch[lab] = ch.get(lab, 0.0) + x
                for c in cur["stt"]:
                    x = to_num(row[c]) if c < len(row) else None
                    if x: ch["STT"] = ch.get("STT", 0.0) + x
                heads = {k: 0.0 for k in HEADS}
                for lab, x in ch.items(): heads[charge_head(lab)] += x
                nmu = nm.upper()
                instr = ("Futures" if re.search(r"\bFUT|FUTSTK|FUTIDX|FUTCOM|FUTCUR|~F\b", nmu) else
                         "Options" if re.search(r"(CE|PE)$|\d(CE|PE)\b|\b(CE|PE)\b|CALL|PUT|OPT|~O", nmu) else
                         ("Futures" if re.search(r"future", cur["title"], re.I) else "Options" if re.search(r"option", cur["title"], re.I) else "Derivative"))
                out.append(dict(file=fname, sheet=sheet, row=i + 1, group=cur["grp"], instr=instr, name=nm.strip(), qty=g("qty"),
                                buy=buy, sell=sell, pnl=pnl, explicit=expl, turn_col=g("turn"),
                                bdate=to_date(row[m["bdate"]]) if m["bdate"] is not None and m["bdate"] < len(row) else None,
                                sdate=to_date(row[m["sdate"]]) if m["sdate"] is not None and m["sdate"] < len(row) else None,
                                heads=heads, labels=ch, src="per-row" if ch else "", mtm=mtm))
                continue
        # ---- label / amount pairs (report-level summary) - only on sheets that are derivative reports.
        # Handles one pair per row (label, amount) and two pairs side by side (e.g. Tradesmart: profit block left, charges block right).
        if named and len(cells) in (2, 4) and isinstance(cells[0][1], str):
            if BIZ_TITLE_RX.search(title): sec_grp = GRP_CC if CC_RX.search(title) else GRP_FNO
            elif re.search(r"equity|mf|slbm", title, re.I): sec_grp = None
            pairs = [(cells[0][1], cells[1][1])] + ([(cells[2][1], cells[3][1])] if len(cells) == 4 and isinstance(cells[2][1], str) else [])
            for lab_raw, val_raw in pairs:
                if not isinstance(lab_raw, str): continue
                lab, v = hnorm(lab_raw), to_num(val_raw)
                if v is None:
                    if isinstance(val_raw, str): section = lab
                    continue
                if re.fullmatch(r"(grand )?total( charges.*)?", lab) or lab.startswith("total charges"):
                    sec_tot[section] = v; continue
                if CHARGE_LBL.search(lab) and not (PNL_WORDS.search(lab) and not re.search(r"charge|tax|fee", lab)):
                    if not re.search(r"credit|debit", lab):
                        rep_ch[lab_raw.strip()] = rep_ch.get(lab_raw.strip(), 0.0) + v
                        if sec_grp: rep_grp.setdefault(sec_grp, OrderedDict())[lab_raw.strip()] = v
                    continue
                if "turnover" in lab or "turnover" in section:
                    rep_turn.append((section, lab, v)); continue
                if re.search(r"realis|realiz|gross", lab) and not re.search(r"net|after|taxable|unrealis", lab):
                    rep_real.append((section, lab, v))
    # reported totals (memo)
    def tot(lst):
        if not lst: return None
        d = [v for (l, v) in dict.fromkeys((l, v) for s_, l, v in lst if not re.search(r"\btotal\b", l))]
        return sum(d) if d else None
    return dict(file=fname, sheet=sheet, named=named, rows=out, report_charges=rep_ch, report_charges_grp=rep_grp, rep_real=tot(rep_real), rep_turn=tot(rep_turn))


def choose_biz_sources(sheets):
    """Pick one source per (file, group) so the same trades are never counted twice (e.g. contract level vs trade level)."""
    keep = []
    byfile = defaultdict(list)
    for s in sheets:
        if s["rows"]: byfile[s["file"]].append(s)
    for f, ss in byfile.items():
        has_named = any(s["named"] for s in ss)
        cand = [s for s in ss if s["named"]] if has_named else ss
        bygrp = defaultdict(list)
        for s in cand:
            gc = Counter_(r["group"] for r in s["rows"]).most_common(1)[0][0]
            bygrp[gc].append(s)
        for g, lst in bygrp.items():
            lst = sorted(lst, key=lambda s: len(s["rows"]))
            chosen = []
            for s in lst:
                tot = sum(r["pnl"] for r in s["rows"])
                dup = next((c for c in chosen if abs(sum(r["pnl"] for r in c["rows"]) - tot) <= 1.0 and len(c["rows"]) > 0), None)
                if dup is None:
                    chosen.append(s)
                else:                                                                   # same total P/L => same trades at another level
                    rt = s.get("rep_turn") or dup.get("rep_turn")
                    a_s, a_d = sum(abs(r["pnl"]) for r in s["rows"]), sum(abs(r["pnl"]) for r in dup["rows"])
                    if rt and abs(a_s - rt) < abs(a_d - rt) - 0.5:
                        chosen[chosen.index(dup)] = s
            keep += chosen
    return keep


def Counter_(it):
    from collections import Counter
    return Counter(it)


def biz_dataframe(sheets, exc):
    """All F&O / derivative entries + intraday-equity entries -> DataFrame with charge heads; plus per-source meta."""
    recs, meta = [], []
    for s in choose_biz_sources(sheets):
        rowch = any(sum(r["heads"].values()) > 0 for r in s["rows"])
        grp_main = Counter_(r["group"] for r in s["rows"]).most_common(1)[0][0]
        rep = {k: 0.0 for k in HEADS}
        if not rowch:
            for lab, v in s["report_charges"].items(): rep[charge_head(lab)] += v
        else:
            for r in s["rows"]: r["src"] = "per-row"
        for r in s["rows"]:
            if not rowch: r["src"] = "report summary"
            recs.append(dict(r))
        rep_grp = {}
        if not rowch:
            for g_, dd in (s.get("report_charges_grp") or {}).items():
                rep_grp[g_] = {k: 0.0 for k in HEADS}
                for lab, v in dd.items(): rep_grp[g_][charge_head(lab)] += v
        meta.append(dict(file=s["file"], sheet=s["sheet"], group=grp_main, rep_grp=rep_grp, rows=len(s["rows"]), pnl=sum(r["pnl"] for r in s["rows"]),
                         absum=sum(abs(r["pnl"]) for r in s["rows"]), rep_real=s["rep_real"], rep_turn=s["rep_turn"],
                         charges_src=("per-row" if rowch else ("report summary" if sum(rep.values()) else "none found")), rep=rep,
                         rep_labels=dict(s["report_charges"]) if not rowch else {}))
    # intraday equity rows (taken from the capital-gain tables where they were excluded as business income)
    if exc is not None and len(exc):
        for _, x in exc.iterrows():
            why = str(x.get("reason", ""))
            if not (why.startswith("Intraday") or why.startswith("Same-day")): continue
            sv, bv = x.get("sale_value"), x.get("actual_cost")
            pnl = (sv - bv) if (pd.notna(sv) and pd.notna(bv)) else x.get("broker_gain")
            if pnl is None or (isinstance(pnl, float) and math.isnan(pnl)): continue
            heads = {k: 0.0 for k in HEADS}
            ed = x.get("exp_detail") if isinstance(x.get("exp_detail"), dict) else {}
            if not x.get("embedded"):
                for lab, v in ed.items(): heads[charge_head(lab)] += v
            if pd.notna(x.get("stt")) and x.get("stt"): heads["STT"] += float(x["stt"])
            recs.append(dict(file=x["file"], sheet=x["sheet"], row=x["row"], group=GRP_INTRA, instr="Equity intraday", name=x["name"], qty=x.get("qty"),
                             buy=bv, sell=sv, pnl=float(pnl), explicit=x.get("broker_gain"), turn_col=None, bdate=x.get("buy_date"), sdate=x.get("sale_date"),
                             heads=heads, labels=ed, src=("per-row" if sum(heads.values()) else "")))
    df = pd.DataFrame(recs)
    return df, meta


def biz_summary(df, meta, broker_of):
    """Rows per (broker, group) with turnover / favourable / unfavourable / gross / expense heads / net."""
    out = []
    if df is None or not len(df): return pd.DataFrame(out)
    df = df.copy()
    df["broker"] = df["file"].map(lambda f: broker_of.get(f, clean_name(f)))
    for (b, g), d in df.groupby(["broker", "group"], sort=False):
        files = set(d["file"])
        row = dict(broker=b, group=g, entries=len(d), turnover=float(d["pnl"].abs().sum()), fav=float(d.loc[d["pnl"] > 0, "pnl"].sum()),
                   unfav=float(d.loc[d["pnl"] < 0, "pnl"].sum()))
        row["gross"] = row["fav"] + row["unfav"]
        for k in HEADS:
            row[k] = float(sum(r["heads"][k] for r in d.to_dict("records")))
        for mt in meta:
            if mt["file"] in files and mt["charges_src"] == "report summary" and mt["sheet"] in set(d["sheet"]):
                if mt.get("rep_grp"):                                    # report gives charges per segment -> use them directly
                    for k in HEADS: row[k] += mt["rep_grp"].get(g, {}).get(k, 0.0)
                    continue
                src_rows = df[(df["file"] == mt["file"]) & (df["sheet"] == mt["sheet"]) & (df["group"] != GRP_INTRA)]
                tot_t = src_rows["pnl"].abs().sum()
                share = (src_rows[src_rows["group"] == g]["pnl"].abs().sum() / tot_t) if tot_t else (1.0 if mt["group"] == g else 0.0)
                for k in HEADS: row[k] += mt["rep"][k] * share
        row["exp"] = sum(row[k] for k in HEADS)
        row["net"] = row["gross"] - row["exp"]
        row["rep_real"] = sum(mt["rep_real"] for mt in meta if mt["file"] in files and mt["group"] == g and mt["rep_real"] is not None) or None
        row["rep_turn"] = sum(mt["rep_turn"] for mt in meta if mt["file"] in files and mt["group"] == g and mt["rep_turn"] is not None) or None
        row["chg_src"] = ", ".join(sorted({r["src"] for r in d.to_dict("records") if r["src"]} | {mt["charges_src"] for mt in meta if mt["file"] in files and mt["group"] == g and mt["charges_src"] == "report summary"})) or "none found"
        out.append(row)
    return pd.DataFrame(out)



# =============================================================================== COMPUTATION
ASSET_EQ, ASSET_NE = "Equity", "Non-Equity"
NONEQ_ASSET_VAL = re.compile(r"debt|gilt|liquid|money market|fixed income|hybrid|others?\b|non.?equity|commodity|gold|silver|bond|arbitrage|fund of fund|fof", re.I)
EQ_ASSET_VAL = re.compile(r"^\W*(equity|equities|shares?|stocks?|eq)\W*$|equity oriented|equity scheme|equity fund", re.I)
NONEQ_SEC_NAME = re.compile(r"\bgold|\bsilver|liquid|gilt|\bdebt|\bbond|\bsgb\b|g-?sec|treasury|money market|overnight|\bncd\b|debenture|fixed (income|maturity)|\bcpse?bees?\b.*bond|bharat ?bond|\bnetf?\b.*gsec|\bcash\b|\bltf\b|\bmmf\b", re.I)


def decide_asset(r):
    """Return (asset, kind, noneq). asset = 'Equity' | 'Non-Equity'.
    Priority: (1) the broker's own Equity / Non-Equity label (section, sheet, asset-class/category column),
    (2) fund / security name hints (gold, silver, liquid, gilt, debt, bond, SGB ...), (3) default Equity."""
    a = r["asset_val"].lower().strip()
    is_mf = bool(r["is_mf_table"])
    is_inf = r["isin"].startswith("INF")
    sec_ne = r["sec"]["noneq"]
    sec_eq = bool(re.match(r"\W*equity\b", (r["section"] or "").lower())) and not sec_ne
    ne, why = False, ""
    if sec_ne:
        ne, why = True, "broker section says non-equity/debt"
    elif a and NONEQ_ASSET_VAL.search(a) and not EQ_ASSET_VAL.search(a) and not re.search(r"(?<!non )(?<!non-)(?<!non)\bequity\b", a):
        ne, why = True, f"broker asset class '{r['asset_val']}'"
    elif a and EQ_ASSET_VAL.search(a):
        ne, why = False, "broker asset class equity"
    elif sec_eq:
        ne, why = False, "broker section says equity"
    elif (is_mf or is_inf or r["isin"].startswith("IN0") or r["isin"].startswith("IN00")) and NONEQ_SEC_NAME.search(r["name"] or ""):
        ne, why = True, "name suggests debt / gold / silver / bond"
    elif re.search(r"\bsgb\b|sovereign gold|\bgold ?bees|\bsilver ?bees|\bliquid ?bees|\bgsec|\bncd\b", r["name"] or "", re.I):
        ne, why = True, "name suggests debt / gold / silver / bond"
    n = r["name"] or ""
    if ne:
        if re.search(r"gold|silver", n, re.I): kind = "Gold/Silver ETF-Fund" if (is_inf or is_mf) else "Gold/Silver security"
        elif re.search(r"hybrid|balanced|arbitrage", a + " " + n, re.I): kind = "Hybrid / Arbitrage fund"
        elif is_mf or is_inf: kind = "Debt / other mutual fund or ETF"
        else: kind = "Bond / debenture / other"
    else:
        if is_mf and not (is_inf and not r["is_mf_table"]): kind = "Equity mutual fund"
        elif is_inf: kind = "Equity ETF"
        else: kind = "Listed shares"
    r["asset_why"] = why
    return (ASSET_NE if ne else ASSET_EQ), kind, ne


def resolve_fmv(recs):
    """Settle 'FMV' columns that do not say whether they are per-unit or total (decided per table from the numbers)."""
    by_block = defaultdict(list)
    for r in recs:
        by_block[(r["file"], r["sheet"], r["block"])].append(r)
    for _, rs in by_block.items():
        du = dt_ = 0.0
        n = 0
        for r in rs:
            fa, q, bv = r["fmv_any"], r["qty"], r["bv"]
            if fa and fa > 0 and q and bv and bv > 0:
                du += abs(math.log(max(fa * q, 1e-9) / bv)); dt_ += abs(math.log(max(fa, 1e-9) / bv)); n += 1
        per_unit = (n > 0 and du < dt_)
        for r in rs:
            fa = r["fmv_any"]
            if fa and fa > 0:
                r["fmv_any_total"] = fa if (r["has_fmv_unit_col"] or not per_unit) else (fa * r["qty"] if r["qty"] else None)
            else:
                r["fmv_any_total"] = None


def compute(recs, opts=None):
    opts = opts or {}
    resolve_fmv(recs)
    inc, exc = [], []
    for r in recs:
        flags = list(r["flags"])
        grp, kind, noneq = decide_asset(r)
        is_mf_like = r["is_mf_table"] or r["isin"].startswith("INF")
        days = (r["sd"] - r["bd"]).days
        base = dict(file=r["file"], sheet=r["sheet"], row=r["row"], section=r["section"], asset=grp, kind=kind, name=r["name"], derived=r["derived"], buyback=r["sec"]["buyback"], nostt=r["sec"]["nostt"],
                    isin=r["isin"], qty=r["qty"], buy_date=r["bd"], sale_date=r["sd"], days=days, sale_value=r["sv"],
                    actual_cost=r["bv"], broker_gain=r["broker_gain"], broker_term=r["bterm"], stt=r["stt"])
        # ---- exclusions: business income
        if r["bterm"] == "Intraday" or (days == 0 and not is_mf_like and not noneq and r["bterm"] == ""):
            why = "Intraday / speculative (business income)" if r["bterm"] == "Intraday" else \
                  "Same-day buy & sell treated as intraday (business income) - confirm"
            base.update(reason=why, exp_detail=r["exp_detail"], embedded=r["embedded"], buy_date=r["bd"], sale_date=r["sd"])
            exc.append(base)
            continue
        if r["bv"] is None or r["sv"] is None:
            base.update(reason="Purchase or sale value missing - NOT included")
            exc.append(base)
            continue
        if r["sec"]["buyback"]:
            flags.append("Buy-back section: tax treatment differs (deemed dividend for buy-backs on/after 01-10-2024) - verify")
        if r["sec"]["nostt"]:
            flags.append("STT not paid: Sec 111A/112A concessional rates may not apply")
        # ---- term
        months = EQ_MONTHS
        eq_oriented = not noneq
        if noneq:
            flags.append("Non-equity / debt / gold-silver fund or ETF: term, rate and Sec 50AA need manual review")
            months = NONEQ_MF_MONTHS if r["is_mf_table"] else EQ_MONTHS
        if kind in ("Equity mutual fund", "Equity ETF") and opts.get("mf_type") == "other":
            noneq, eq_oriented, months = True, False, NONEQ_MF_MONTHS
            grp, kind = ASSET_NE, "Debt / other mutual fund or ETF"
        comp_term = "LTCG" if r["sd"] > r["bd"] + relativedelta(months=months) else "STCG"
        term = comp_term
        if noneq and r["bterm"] in ("STCG", "LTCG"):
            term = r["bterm"]                              # trust broker where the rules are not simple
        elif r["bterm"] in ("STCG", "LTCG") and r["bterm"] != comp_term:
            flags.append(f"Broker says {r['bterm']} but dates give {comp_term} - computed value used")
        if kind == "Equity ETF":
            flags.append("ETF treated as equity-oriented (" + (r.get("asset_why") or "default") + ") - confirm >=65% domestic equity")
        if noneq and r.get("asset_why"):
            flags.append("Non-equity because: " + r["asset_why"])
        # ---- grandfathering
        cost, gf, work = r["bv"], "No", ""
        fmv = None
        for cand in (
            (r["fmv_unit"] * r["qty"]) if (r["fmv_unit"] and r["fmv_unit"] > 0 and r["qty"]) else None,
            r["fmv_total"] if (r["fmv_total"] and r["fmv_total"] > 0) else None,
            r.get("fmv_any_total"),
        ):
            if cand:
                fmv = cand
                break
        fmv_src = ""
        if fmv is None and r["gf_cost"] and r["gf_cost"] > 0:
            fmv, fmv_src = r["gf_cost"], " (broker's grandfathered cost value used as FMV)"
        if term == "LTCG" and r["bd"] <= GF_DATE and eq_oriented:
            if fmv is None:
                flags.append("Bought on/before 31-01-2018 but FMV missing - actual cost used; ADD FMV")
            else:
                cost = max(r["bv"], min(fmv, r["sv"]))
                gf = "Yes"
                work = f"GF cost = max(actual {r['bv']:,.2f}, min(FMV {fmv:,.2f}{fmv_src}, sale {r['sv']:,.2f})) = {cost:,.2f}"
        deduct = 0.0 if r["embedded"] else r["exp"]
        gain = r["sv"] - cost - deduct
        bits = [f"Gain = sale {r['sv']:,.2f} - cost {cost:,.2f}"]
        if deduct:
            bits.append(f"- expenses {deduct:,.2f}")
        if r["embedded"] and r["exp"]:
            bits.append(f"(charges {r['exp']:,.2f} already inside broker's buy/sell values - not deducted again)")
        working = (work + " ; " if work else "") + " ".join(bits) + f" = {gain:,.2f}"
        if r["notes"]:
            working += " | " + "; ".join(r["notes"])
        base.update(term=term, comp_term=comp_term, period=("Pre 23-Jul-2024" if r["sd"] < RATE_CHANGE else "On/After 23-Jul-2024"),
                    fmv=fmv, gf=gf, cost_used=cost, expenses=deduct, embedded_charges=(r["exp"] if r["embedded"] else 0.0),
                    exp_detail=r["exp_detail"] if not r["embedded"] else {}, gain=gain,
                    variance=(gain - r["broker_gain"]) if r["broker_gain"] is not None else None,
                    working=working, flags="; ".join(flags))
        inc.append(base)
    return pd.DataFrame(inc), pd.DataFrame(exc)


# =============================================================================== SUMMARY TABLES
def build_summary(res, charges):
    """charges = {'Equity': x, 'Non-Equity': y} extra manually entered charges, allocated by sale value within the asset."""
    res = res.copy()
    res["extra"] = 0.0
    for asset, ch in (charges or {}).items():
        m = res["asset"] == asset
        tot = res.loc[m, "sale_value"].sum()
        if ch and tot:
            res.loc[m, "extra"] = ch * res.loc[m, "sale_value"] / tot
    res["exp_total"] = res["expenses"] + res["extra"]
    res["net"] = res["gain"] - res["extra"]
    return res


def matrix(res):
    cols = [("Equity", "STCG"), ("Equity", "LTCG"), ("Non-Equity", "STCG"), ("Non-Equity", "LTCG")]
    out = OrderedDict()
    def s(df, col): return float(df[col].sum()) if len(df) else 0.0
    for key in ("sale", "cost", "gross", "exp", "net", "uplift", "stt", "embedded", "broker"):
        out[key] = []
    for a, t in cols:
        d = res[(res["asset"] == a) & (res["term"] == t)]
        sale, cost, exp = s(d, "sale_value"), s(d, "cost_used"), s(d, "exp_total")
        out["sale"].append(sale); out["cost"].append(cost); out["gross"].append(sale - cost)
        out["exp"].append(exp); out["net"].append(sale - cost - exp)
        out["uplift"].append(s(d, "cost_used") - s(d, "actual_cost"))
        out["stt"].append(s(d, "stt")); out["embedded"].append(s(d, "embedded_charges"))
        out["broker"].append(float(d["broker_gain"].sum()) if len(d) and d["broker_gain"].notna().any() else None)
    return cols, out


# =============================================================================== EXCEL OUTPUT
def write_excel(res, exc, errs, checks, rlines, log, charges, path, files):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter as L

    wb = Workbook()
    NUM = '#,##0.00;[Red](#,##0.00);-'
    HFILL = PatternFill("solid", fgColor="1F3864"); HFONT = Font(bold=True, color="FFFFFF")
    SUB = PatternFill("solid", fgColor="D9E2F3"); TOT = PatternFill("solid", fgColor="F2F2F2")
    thin = Side(style="thin", color="BFBFBF"); BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
    WARN = PatternFill("solid", fgColor="FFF2CC")

    def hdr_row(ws, r, vals, c0=1):
        for k, v in enumerate(vals):
            c = ws.cell(r, c0 + k, v); c.fill, c.font, c.border = HFILL, HFONT, BOX
            c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")

    # ------------------------------------------------------------------ Summary
    ws = wb.active; ws.title = "Summary"
    ws["A1"] = "Capital Gains Summary - Equity and Non-Equity (shares, mutual funds, ETFs)"; ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Source files: {', '.join(os.path.basename(f) for f in files)}"
    ws["A3"] = (f"Rows included: {len(res)}   |   excluded (intraday etc.): {len(exc)}   |   "
                f"rows needing attention: {int((res['flags'] != '').sum()) + len(errs)}")
    names = OrderedDict()
    for f_, sh_, rw_, lab_, val_ in rlines:
        if lab_ == "__client__":
            names.setdefault(re.sub(r"\s+", " ", str(val_).upper()), os.path.basename(f_))
    if names:
        ws["A4"] = "Client name(s) found in the reports: " + "; ".join(names)
        if len(names) > 1:
            ws["A4"] = "WARNING - more than one name found in these reports (" + "; ".join(names) + "). Are you mixing clients?"
            ws["A4"].fill = WARN; ws["A4"].font = Font(bold=True, color="C00000")
    cols, m = matrix(res)
    r0 = 5
    ws.cell(r0, 1, "A.  Capital gain summary  (all figures in Rs)").font = Font(bold=True, size=12)
    heads = ["Particulars", "Equity\nSTCG", "Equity\nLTCG", "Equity\nTOTAL", "Non-Equity\nSTCG", "Non-Equity\nLTCG",
             "Non-Equity\nTOTAL", "ALL\nSTCG", "ALL\nLTCG", "GRAND\nTOTAL"]
    hdr_row(ws, r0 + 1, heads)
    def line(label, key, bold=False, fill=None, note=None):
        vals = m[key]
        row = [label, vals[0], vals[1], vals[0] + vals[1], vals[2], vals[3], vals[2] + vals[3],
               vals[0] + vals[2], vals[1] + vals[3], sum(vals)]
        return row, bold, fill
    rowsA = [line("1. Total sale value (full value of consideration)", "sale"),
             line("2. Total purchase cost (after grandfathering where applicable)", "cost"),
             line("3. Gross profit / (loss)   [1 - 2]", "gross", True, SUB),
             line("4. Less: charges / expenses deducted", "exp"),
             line("5. NET PROFIT / (LOSS)   [3 - 4]", "net", True, SUB)]
    r = r0 + 2
    for row, bold, fill in rowsA:
        for k, v in enumerate(row):
            c = ws.cell(r, 1 + k, v); c.border = BOX
            if k: c.number_format = NUM
            if bold: c.font = Font(bold=True)
            if fill: c.fill = fill
        r += 1
    r += 1
    ws.cell(r, 1, "Memo items (not part of the totals above)").font = Font(bold=True, italic=True); r += 1
    memo = [("Cost uplift due to grandfathering (cost used - actual cost)", "uplift"),
            ("STT paid on these trades (NOT deductible)", "stt"),
            ("Charges already inside broker's buy/sell values (not deducted again)", "embedded"),
            ("Gain as reported by broker (for tie-out; differs by STT / charges / grandfathering)", "broker")]
    for label, key in memo:
        v = m[key]
        vv = [label] + [None if x is None else x for x in (v[0], v[1], (v[0] or 0) + (v[1] or 0), v[2], v[3], (v[2] or 0) + (v[3] or 0),
                                                           (v[0] or 0) + (v[2] or 0), (v[1] or 0) + (v[3] or 0), sum(x or 0 for x in v))]
        for k, x in enumerate(vv):
            c = ws.cell(r, 1 + k, x); c.border = BOX
            if k: c.number_format = NUM
            c.font = Font(italic=True, color="595959")
        r += 1
    manual = {k: v for k, v in (charges or {}).items() if v}
    if manual:
        ws.cell(r, 1, "Manual charges entered and included in row 4: " + ", ".join(f"{k} {v:,.2f}" for k, v in manual.items())).font = Font(italic=True)
        r += 1
    r += 1
    # ---- A2: split by kind of security
    ws.cell(r, 1, "A2.  Equity / Non-Equity split by type of security (how each row was classified is in Workings > Kind / Flags)").font = Font(bold=True, size=12); r += 1
    hdr_row(ws, r, ["Asset  |  Kind", "Rows", "Sale value", "Purchase cost", "Gross P/(L)", "Charges", "NET P/(L)", "of which STCG", "of which LTCG"]); r += 1
    for (a, kd), d in (res.groupby(["asset", "kind"], sort=True) if len(res) else []):
        sale, cost, ex_ = float(d["sale_value"].sum()), float(d["cost_used"].sum()), float(d["exp_total"].sum())
        vals = [f"{a}  |  {kd}", len(d), sale, cost, sale - cost, ex_, sale - cost - ex_,
                float(d[d["term"] == "STCG"]["net"].sum()), float(d[d["term"] == "LTCG"]["net"].sum())]
        for k, x in enumerate(vals):
            c = ws.cell(r, 1 + k, x); c.border = BOX
            if k > 1: c.number_format = NUM
        r += 1
    r += 1
    # ---- B: by sale period
    ws.cell(r, 1, "B.  Net profit / (loss) by date of sale (rates differ before / after 23-Jul-2024)").font = Font(bold=True, size=12); r += 1
    hdr_row(ws, r, ["Head", "Sale before\n23-Jul-2024", "Sale on/after\n23-Jul-2024", "Total"]); r += 1
    for a, t in cols:
        d = res[(res["asset"] == a) & (res["term"] == t)]
        p1 = float(d[d["period"].str.startswith("Pre")]["net"].sum()); p2 = float(d[~d["period"].str.startswith("Pre")]["net"].sum())
        for k, v in enumerate([f"{a} {t}", p1, p2, p1 + p2]):
            c = ws.cell(r, 1 + k, v); c.border = BOX
            if k: c.number_format = NUM
        r += 1
    ws.cell(r, 1, RATES_NOTE).font = Font(italic=True, size=9); r += 2
    # ---- C: charges detail
    ws.cell(r, 1, "C.  Charges / expenses deducted - detail").font = Font(bold=True, size=12); r += 1
    hdr_row(ws, r, ["Charge head", "Equity", "Non-Equity", "Total"]); r += 1
    comp = defaultdict(lambda: {"Equity": 0.0, "Non-Equity": 0.0})
    for _, x in res.iterrows():
        for lab, amt in (x["exp_detail"] or {}).items():
            comp[lab][x["asset"]] += amt
    for a, v in (charges or {}).items():
        if v: comp["Manual entry (allocated by sale value)"][a] += v
    tot_e = tot_m = 0.0
    for lab, v in comp.items():
        for k, x in enumerate([lab, v["Equity"], v["Non-Equity"], v["Equity"] + v["Non-Equity"]]):
            c = ws.cell(r, 1 + k, x); c.border = BOX
            if k: c.number_format = NUM
        tot_e += v["Equity"]; tot_m += v["Non-Equity"]; r += 1
    if not comp:
        ws.cell(r, 1, "No per-trade charges found in these reports (or they are already inside the buy/sell values)."); r += 1
    else:
        for k, x in enumerate(["Total deducted", tot_e, tot_m, tot_e + tot_m]):
            c = ws.cell(r, 1 + k, x); c.border = BOX; c.font = Font(bold=True); c.fill = TOT
            if k: c.number_format = NUM
        r += 1
    r += 1
    # ---- D: excluded
    ws.cell(r, 1, "D.  Not part of capital gains (shown for completeness)").font = Font(bold=True, size=12); r += 1
    hdr_row(ws, r, ["Item", "Rows", "Sale value", "Gain / (loss) as reported"]); r += 1
    if len(exc):
        for reason, d in exc.groupby("reason"):
            vals = [reason, len(d), float(d["sale_value"].fillna(0).sum()), float(d["broker_gain"].fillna(0).sum())]
            for k, x in enumerate(vals):
                c = ws.cell(r, 1 + k, x); c.border = BOX
                if k > 1: c.number_format = NUM
            r += 1
    skipped = [l for l in log if str(l[3]).startswith("Skipped sheet") or "ignored (business income)" in str(l[3])]
    for f, sh, rw, msg in skipped:
        ws.cell(r, 1, f"{os.path.basename(f)} | {sh}: {msg}").font = Font(italic=True, size=9); r += 1
    if len(errs):
        ws.cell(r, 1, f"{len(errs)} row(s) with amounts but unreadable dates were NOT included - see Exceptions.").fill = WARN; r += 1
    ws.column_dimensions["A"].width = 72
    for k in range(2, 12): ws.column_dimensions[L(k)].width = 17
    ws.row_dimensions[r0 + 1].height = 46
    ws.sheet_view.showGridLines = False

    # ------------------------------------------------------------------ Broker Summary (first sheet)
    ws.title = "Consolidated"
    bs = wb.create_sheet("Broker Summary", 0)
    GREEN = PatternFill("solid", fgColor="E2EFDA"); BLUE = PatternFill("solid", fgColor="DDEBF7"); ORNG = PatternFill("solid", fgColor="FCE4D6")
    bs["A1"] = "Capital Gains Summary - Broker-wise"; bs["A1"].font = Font(bold=True, size=15)
    bs["A2"] = "All amounts in Rs.  Loss shown in red brackets.  Equity = listed shares, equity-oriented MF/ETF.  Non-Equity = debt / gold-silver / hybrid / bonds etc.  STCG = short term, LTCG = long term."
    bs["A2"].font = Font(italic=True, size=9, color="595959")
    names_ = OrderedDict()
    for f_, sh_, rw_, lab_, val_ in rlines:
        if lab_ == "__client__":
            names_.setdefault(re.sub(r"\s+", " ", str(val_).upper()), 1)
    if names_:
        bs["A3"] = ("Client: " + "; ".join(names_)) if len(names_) == 1 else ("WARNING - more than one client name found: " + "; ".join(names_))
        bs["A3"].font = Font(bold=True, color=("000000" if len(names_) == 1 else "C00000"))
    brokers = list(OrderedDict.fromkeys(res["broker"])) if len(res) else []
    CL = ["Equity\nSTCG", "Equity\nLTCG", "Equity\nTOTAL", "Non-Equity\nSTCG", "Non-Equity\nLTCG", "Non-Equity\nTOTAL", "ALL\nSTCG", "ALL\nLTCG", "GRAND\nTOTAL"]
    def vals_for(d):
        out = {}
        for key, fn in (("sale", lambda x: x["sale_value"].sum()), ("cost", lambda x: x["cost_used"].sum()),
                        ("exp", lambda x: x["exp_total"].sum())):
            v = []
            for a in ("Equity", "Non-Equity"):
                p = [float(fn(d[(d["asset"] == a) & (d["term"] == t)])) for t in ("STCG", "LTCG")]
                v += [p[0], p[1], p[0] + p[1]]
            v += [v[0] + v[3], v[1] + v[4], v[2] + v[5]]
            out[key] = v
        out["gross"] = [a - b for a, b in zip(out["sale"], out["cost"])]
        out["net"] = [a - b for a, b in zip(out["gross"], out["exp"])]
        return out
    r = 5
    # --- 1. at a glance : NET profit by broker
    bs.cell(r, 1, "1.  AT A GLANCE - NET PROFIT / (LOSS) BY BROKER").font = Font(bold=True, size=12); r += 1
    hdr_row(bs, r, ["Broker"] + CL); hdr_r = r; r += 1
    first = r
    allv = {k: [0.0] * 9 for k in ("sale", "cost", "gross", "exp", "net")}
    per = OrderedDict()
    for b in brokers:
        per[b] = vals_for(res[res["broker"] == b])
        for k in allv: allv[k] = [x + y for x, y in zip(allv[k], per[b][k])]
        for k_, v in enumerate([b] + per[b]["net"]):
            c = bs.cell(r, 1 + k_, v); c.border = BOX
            if k_: c.number_format = NUM
            if k_ in (3, 6, 9): c.fill = GREEN if k_ != 9 else BLUE; c.font = Font(bold=True)
        r += 1
    last = r - 1
    bs.cell(r, 1, "TOTAL - ALL BROKERS")
    for k_ in range(2, 11):
        col = L(k_)
        bs.cell(r, k_, f"=SUM({col}{first}:{col}{last})" if brokers else 0)
    for k_ in range(1, 11):
        c = bs.cell(r, k_); c.border = BOX; c.font = Font(bold=True); c.fill = TOT
        if k_ > 1: c.number_format = NUM
    glance_total_row = r
    r += 2
    # --- 2. broker-wise details
    bs.cell(r, 1, "2.  BROKER-WISE DETAIL  (sale value, purchase cost, gross, charges, net)").font = Font(bold=True, size=12); r += 1
    LINES = [("Total sale value", "sale", None), ("Total purchase cost", "cost", None), ("Gross profit / (loss)", "gross", SUB),
             ("Less: charges / expenses", "exp", None), ("NET PROFIT / (LOSS)", "net", GREEN)]
    blocks = [(b, per[b]) for b in brokers] + [("TOTAL - ALL BROKERS", allv)]
    for b, v in blocks:
        is_tot = b.startswith("TOTAL")
        bfill = PatternFill("solid", fgColor="C00000" if is_tot else "1F3864")
        c = bs.cell(r, 1, b); c.font = Font(bold=True, size=11, color="FFFFFF"); c.fill = bfill
        if not is_tot:
            nrows = int((res["broker"] == b).sum())
            files_ = sorted({os.path.basename(x) for x in res.loc[res["broker"] == b, "file"]})
            c2 = bs.cell(r, 2, f"{nrows} trades | " + "; ".join(clean_name(x) for x in files_))
            c2.font = Font(italic=True, size=9, color="FFFFFF"); c2.fill = bfill
            for k_ in range(3, 11): bs.cell(r, k_).fill = bfill
        else:
            for k_ in range(2, 11): bs.cell(r, k_).fill = bfill
        r += 1
        hdr_row(bs, r, ["Particulars"] + CL); r += 1
        for lab, key, fill in LINES:
            bs.cell(r, 1, lab).border = BOX
            for k_, x in enumerate(v[key], start=2):
                c = bs.cell(r, k_, x); c.border = BOX; c.number_format = NUM
                if fill: c.fill = fill
                if key in ("gross", "net"): c.font = Font(bold=True)
            if fill: bs.cell(r, 1).fill = fill; bs.cell(r, 1).font = Font(bold=True)
            r += 1
        r += 1
    # --- 3. checks and notes
    bs.cell(r, 1, "3.  CHECKS").font = Font(bold=True, size=12); r += 1
    tot_net_rows = float(res["net"].sum()) if len(res) else 0.0
    chk = [("Net P/(L) of all trades read (Workings sheet)", tot_net_rows),
           ("Net P/(L) shown above (grand total)", f"=J{glance_total_row}"),
           ("Difference (must be nil)", f"=ROUND(B{r+1}-B{r},2)".replace(f"B{r+1}", f"B{r+1}").replace(f"B{r}", f"B{r}"))]
    chk[2] = ("Difference (must be nil)", f"=ROUND(B{r+1}-B{r},2)")
    for lab, v in chk:
        bs.cell(r, 1, lab).border = BOX
        c = bs.cell(r, 2, v); c.border = BOX; c.number_format = NUM
        r += 1
    r += 1
    bs.cell(r, 1, "4.  FILE-BY-FILE PARSE STATUS  (every uploaded file, with broker where it could be read)").font = Font(bold=True, size=12); r += 1
    hdr_row(bs, r, ["File", "Broker", "Status", "Trades", "Detail"]); r += 1
    for st_ in file_status(files, res, exc, errs, log):
        fill_ = {"ok": GREEN, "warn": WARN, "bad": PatternFill("solid", fgColor="F8CBAD")}[st_["level"]]
        for k_, v in enumerate([st_["file"], st_["broker"], st_["status"], st_["trades"] or None, st_["detail"]], start=1):
            c = bs.cell(r, k_, v); c.border = BOX
            if k_ == 3: c.fill = fill_; c.font = Font(bold=True, color=("C00000" if st_["level"] == "bad" else "000000"))
        r += 1
    r += 1
    bs.cell(r, 1, "Sheets: Consolidated = combined view and charge detail | Workings = every trade with working | Exceptions = rows to review | Reconciliation = tie-out to each broker report").font = Font(italic=True, size=9)
    bs.column_dimensions["A"].width = 34
    for k_ in range(2, 11): bs.column_dimensions[L(k_)].width = 16
    bs.row_dimensions[hdr_r].height = 34
    bs.sheet_view.showGridLines = False
    bs.freeze_panes = "B5"
    bs.page_setup.orientation = "landscape"; bs.page_setup.fitToWidth = 1; bs.page_setup.fitToHeight = 0
    bs.sheet_properties.pageSetUpPr = __import__("openpyxl").worksheet.properties.PageSetupProperties(fitToPage=True)

    # ------------------------------------------------------------------ F&O and Intraday (business income) sheets
    bsum, bdf, bmeta = LAST_BIZ.get("summary"), LAST_BIZ.get("df"), LAST_BIZ.get("meta", [])
    if bsum is not None and len(bsum):
        fx = wb.create_sheet("F&O and Intraday", 2)
        fx["A1"] = "F&O and Intraday - broker-wise working (business income, not capital gains)"; fx["A1"].font = Font(bold=True, size=15)
        fx["A2"] = ("Turnover = sum of absolute value of every profit and every loss entry.  Favourable = sum of all profit entries.  Unfavourable = sum of all loss entries (shown negative).  "
                    "Gross P/(L) = Favourable + Unfavourable.  Net P/(L) = Gross - total expenses.  STT is treated as an expense here (business income).")
        fx["A2"].font = Font(italic=True, size=9, color="595959"); fx["A2"].alignment = Alignment(wrap_text=True, vertical="top")
        fx.merge_cells("A2:L2"); fx.row_dimensions[2].height = 38
        cols = ["Broker", "Entries", "Turnover\n(sum of |P/L|)", "Favourable\n(profits)", "Unfavourable\n(losses)", "Gross\nprofit / (loss)",
                "Brokerage", "STT", "Exchange\ntransaction charges", "Other trading\ncharges", "TOTAL\nEXPENSES", "NET\nprofit / (loss)"]
        keys = ["entries", "turnover", "fav", "unfav", "gross"] + list(HEADS) + ["exp", "net"]
        def block(r, title, d, fill_title="1F3864"):
            c = fx.cell(r, 1, title); c.font = Font(bold=True, size=11, color="FFFFFF"); tf_ = PatternFill("solid", fgColor=fill_title)
            for k_ in range(1, 13): fx.cell(r, k_).fill = tf_
            r += 1
            hdr_row(fx, r, cols); fx.row_dimensions[r].height = 34; r += 1
            first = r
            for _, x in d.iterrows():
                fx.cell(r, 1, x["broker"]).border = BOX
                for k_, key in enumerate(keys, start=2):
                    c = fx.cell(r, k_, x[key]); c.border = BOX; c.number_format = NUM if key != "entries" else "0"
                    if key in ("gross", "net", "exp"): c.font = Font(bold=True)
                    if key == "net": c.fill = GREEN
                r += 1
            last = r - 1
            fx.cell(r, 1, "TOTAL")
            for k_, key in enumerate(keys, start=2):
                col = L(k_)
                fx.cell(r, k_, f"=SUM({col}{first}:{col}{last})")
            for k_ in range(1, 13):
                c = fx.cell(r, k_); c.border = BOX; c.font = Font(bold=True); c.fill = TOT
                if k_ > 1: c.number_format = NUM if k_ != 2 else "0"
            return r + 2
        r = 4
        fx.cell(r, 1, "1.  BROKER-WISE - ALL F&O, COMMODITY / CURRENCY DERIVATIVES AND INTRADAY COMBINED").font = Font(bold=True, size=12); r += 1
        allb = bsum.groupby("broker", sort=False)[["entries", "turnover", "fav", "unfav", "gross"] + list(HEADS) + ["exp", "net"]].sum().reset_index()
        r = block(r, "All segments", allb, "C00000")
        fx.cell(r, 1, "2.  SEGMENT-WISE DETAIL").font = Font(bold=True, size=12); r += 1
        for g in (GRP_FNO, GRP_CC, GRP_INTRA):
            d = bsum[bsum["group"] == g]
            if len(d): r = block(r, g, d)
        # --- C. charges as printed in the reports
        fx.cell(r, 1, "3.  EXPENSE HEADS - HOW EACH CHARGE WAS GROUPED").font = Font(bold=True, size=12); r += 1
        hdr_row(fx, r, ["Broker", "Source", "Charge as printed in report", "Grouped under", "Amount"]); r += 1
        shown = False
        for mt in bmeta:
            br = BROKER_OF.get(mt["file"], clean_name(mt["file"]))
            if mt["charges_src"] == "report summary":
                for lab, v in mt["rep_labels"].items():
                    for k_, vv in enumerate([br, f"{mt['sheet']} (report summary)", lab, charge_head(lab), v], start=1):
                        c = fx.cell(r, k_, vv); c.border = BOX
                        if k_ == 5: c.number_format = NUM
                    r += 1; shown = True
        if bdf is not None and len(bdf):
            lab_tot = defaultdict(float)
            for rec in bdf.to_dict("records"):
                if rec["src"] == "per-row":
                    br = BROKER_OF.get(rec["file"], clean_name(rec["file"]))
                    for lab, v in (rec.get("labels") or {}).items(): lab_tot[(br, f"per-trade columns ({rec['group'][:12]})", lab, charge_head(lab))] += v
            for (br, src_, lab, hd), v in lab_tot.items():
                for k_, vv in enumerate([br, src_, lab, hd, v], start=1):
                    c = fx.cell(r, k_, vv); c.border = BOX
                    if k_ == 5: c.number_format = NUM
                r += 1; shown = True
        if not shown: fx.cell(r, 1, "No charges were found in the F&O / intraday sections of these reports.").fill = WARN; r += 1
        r += 1
        # --- D. sources and tie-out
        fx.cell(r, 1, "4.  SOURCES USED AND TIE-OUT TO THE BROKER'S OWN FIGURES").font = Font(bold=True, size=12); r += 1
        hdr_row(fx, r, ["Broker", "File | sheet", "Segment", "Entries", "Sum of P/(L)", "Broker-reported\nrealised P&L", "Difference", "Turnover\n(sum of |P/L|)", "Broker-reported\nturnover", "Difference", "Charges taken from"])
        fx.row_dimensions[r].height = 34; r += 1
        for mt in bmeta:
            vals = [BROKER_OF.get(mt["file"], clean_name(mt["file"])), f"{clean_name(mt['file'])} | {mt['sheet']}", mt["group"], mt["rows"], mt["pnl"], mt["rep_real"],
                    (mt["pnl"] - mt["rep_real"]) if mt["rep_real"] is not None else None, mt["absum"], mt["rep_turn"],
                    (mt["absum"] - mt["rep_turn"]) if mt["rep_turn"] is not None else None, mt["charges_src"]]
            for k_, v in enumerate(vals, start=1):
                c = fx.cell(r, k_, v); c.border = BOX
                if k_ in (5, 6, 7, 8, 9, 10): c.number_format = NUM
                if k_ in (7, 10) and v is not None and abs(v) > 1: c.fill = WARN
            r += 1
        if bdf is not None and len(bdf):
            ig = bdf[bdf["group"] == GRP_INTRA]
            if len(ig):
                for (f_, sh_), d in ig.groupby(["file", "sheet"]):
                    vals = [BROKER_OF.get(f_, clean_name(f_)), f"{clean_name(f_)} | {sh_}", GRP_INTRA, len(d), float(d["pnl"].sum()), None, None, float(d["pnl"].abs().sum()), None, None,
                            "per-row" if any(rr["src"] for rr in d.to_dict("records")) else "none found"]
                    for k_, v in enumerate(vals, start=1):
                        c = fx.cell(r, k_, v); c.border = BOX
                        if k_ in (5, 6, 7, 8, 9, 10): c.number_format = NUM
                    r += 1
        r += 1
        notes_ = ["Highlighted differences: some brokers print P&L after charges, include open positions marked to market, or round - read the difference against the notes below.",
                  "Where one report shows the same trades at contract level AND trade level, only one level is used (the one matching the broker's turnover) so nothing is counted twice.",
                  "Open positions marked to market at year end (Angel One style) are included at the broker's taxable figure and marked 'MTM' in the working sheet.",
                  "Intraday equity is taken from the equity tables of each report (rows marked intraday / speculative, or same-day buy and sell). Charges are those printed per trade in that report.",
                  "Where a report gives charges only as a single combined figure (for example Angel One 'Total Charges and Statutory Levies' excluding STT) that figure is shown under Other trading charges.",
                  "Brokers that print no charges for F&O (for example Geojit) show nil expenses - add them manually if known."]
        for n_ in notes_:
            fx.cell(r, 1, "Note: " + n_).font = Font(italic=True, size=9, color="595959"); r += 1
        fx.column_dimensions["A"].width = 30
        for k_, w_ in zip(range(2, 13), (11, 17, 17, 17, 17, 14, 14, 18, 17, 17, 17)): fx.column_dimensions[L(k_)].width = w_
        fx.sheet_view.showGridLines = False; fx.freeze_panes = "B4"
        fx.page_setup.orientation = "landscape"; fx.page_setup.fitToWidth = 1; fx.page_setup.fitToHeight = 0
        fx.sheet_properties.pageSetUpPr = __import__("openpyxl").worksheet.properties.PageSetupProperties(fitToPage=True)
        # ---- workings sheet
        fw = wb.create_sheet("F&O-Intraday Workings", 3)
        wc = [("broker", "Broker"), ("file", "File"), ("sheet", "Sheet"), ("row", "Row"), ("group", "Segment"), ("instr", "Instrument"), ("name", "Contract / Scrip"),
              ("qty", "Qty"), ("bdate", "Buy date"), ("sdate", "Sell date"), ("buy", "Buy value"), ("sell", "Sell value"), ("pnl", "Profit / (loss)"),
              ("fav", "Favourable"), ("unfav", "Unfavourable"), ("turn", "Turnover |P/L|"), ("h0", "Brokerage"), ("h1", "STT"), ("h2", "Exchange txn charges"),
              ("h3", "Other trading charges"), ("src", "Charges source"), ("note", "Note")]
        hdr_row(fw, 1, [h for _, h in wc]); fw.row_dimensions[1].height = 32
        for ri, rec in enumerate(bdf.to_dict("records"), start=2):
            rec["broker"] = BROKER_OF.get(rec["file"], clean_name(rec["file"])); rec["file"] = clean_name(rec["file"])
            rec["fav"] = rec["pnl"] if rec["pnl"] > 0 else 0.0; rec["unfav"] = rec["pnl"] if rec["pnl"] < 0 else 0.0; rec["turn"] = abs(rec["pnl"])
            for k_, hk in enumerate(HEADS): rec[f"h{k_}"] = rec["heads"][hk] or None
            rec["note"] = "MTM (open position at year end)" if rec.get("mtm") else ""
            for ci, (k, _) in enumerate(wc, start=1):
                v = rec.get(k)
                if isinstance(v, pd.Timestamp): v = v.to_pydatetime().date()
                elif isinstance(v, float) and math.isnan(v): v = None
                c = fw.cell(ri, ci, v)
                if k in ("buy", "sell", "pnl", "fav", "unfav", "turn", "h0", "h1", "h2", "h3"): c.number_format = NUM
                elif k in ("bdate", "sdate"): c.number_format = "dd-mmm-yyyy"
        for ci, wd in enumerate([16, 26, 16, 6, 26, 12, 30, 9, 12, 12, 13, 13, 14, 13, 13, 14, 11, 11, 13, 13, 14, 28], start=1):
            fw.column_dimensions[L(ci)].width = wd
        fw.freeze_panes = "H2"; fw.auto_filter.ref = f"A1:{L(len(wc))}{max(len(bdf) + 1, 2)}"

    # ------------------------------------------------------------------ KDK notes (only when KDK output was requested)
    if LAST_KDK.get("notes") is not None:
        kn = wb.create_sheet("KDK Notes")
        hdr_row(kn, 1, ["Type", "Trade", "Note"])
        for ri, (a_, b_, c_) in enumerate(LAST_KDK["notes"], start=2):
            for ci, v in enumerate((a_, b_, c_), start=1): kn.cell(ri, ci, v)
        if not LAST_KDK["notes"]: kn.cell(2, 1, "No notes.")
        kn.cell(len(LAST_KDK["notes"]) + 4, 1, "Rows written - " + ", ".join(f"sheet {k}: {v}" for k, v in LAST_KDK.get("counts", {}).items()))
        for col_, w_ in zip("ABC", (16, 60, 110)): kn.column_dimensions[col_].width = w_

    # ------------------------------------------------------------------ Workings
    w = wb.create_sheet("Workings")
    wcols = [("file", "Source file"), ("sheet", "Sheet"), ("row", "Row"), ("section", "Section"), ("broker", "Broker"), ("asset", "Asset"), ("kind", "Kind"),
             ("name", "Scrip / Scheme"), ("isin", "ISIN"), ("qty", "Qty / Units"), ("buy_date", "Buy date"),
             ("sale_date", "Sale date"), ("days", "Holding days"), ("term", "Term (computed)"), ("broker_term", "Term (broker)"),
             ("period", "Sale period"), ("sale_value", "Sale value"), ("actual_cost", "Actual cost"),
             ("fmv", "FMV 31-01-2018"), ("gf", "Grandfathered?"), ("cost_used", "Cost used"), ("expenses", "Expenses deducted"),
             ("extra", "Manual charges"), ("stt", "STT (info)"), ("net", "Net gain / (loss)"), ("broker_gain", "Broker-reported gain"),
             ("variance", "Variance"), ("working", "Working"), ("flags", "Flags")]
    hdr_row(w, 1, [h for _, h in wcols])
    for ri, (_, x) in enumerate(res.iterrows(), start=2):
        for ci, (k, _) in enumerate(wcols, start=1):
            v = x.get(k)
            if isinstance(v, pd.Timestamp): v = v.to_pydatetime().date()
            elif isinstance(v, float) and math.isnan(v): v = None
            elif k == "file": v = os.path.basename(str(v))
            c = w.cell(ri, ci, v)
            if k in ("sale_value", "actual_cost", "fmv", "cost_used", "expenses", "extra", "stt", "net", "broker_gain", "variance"):
                c.number_format = NUM
            elif k in ("buy_date", "sale_date"):
                c.number_format = "dd-mmm-yyyy"
            if k == "flags" and v: c.fill = WARN
    for ci, wd in enumerate([22, 14, 16, 6, 18, 11, 22, 28, 14, 10, 12, 12, 9, 10, 10, 18, 14, 14, 14, 9, 14, 12, 10, 10, 14, 14, 11, 70, 60], start=1):
        w.column_dimensions[L(ci)].width = wd
    w.freeze_panes = "H2"; w.auto_filter.ref = f"A1:{L(len(wcols))}{max(len(res) + 1, 2)}"
    w.row_dimensions[1].height = 32

    # ------------------------------------------------------------------ Exceptions
    e = wb.create_sheet("Exceptions")
    hdr_row(e, 1, ["Source file", "Sheet", "Row", "Scrip / Scheme", "Sale date", "Sale value", "Issue"])
    er = 2
    for _, x in res[res["flags"] != ""].iterrows():
        vals = [os.path.basename(x["file"]), x["sheet"], x["row"], x["name"], x["sale_date"].date(), x["sale_value"], x["flags"]]
        for k, v in enumerate(vals, start=1): e.cell(er, k, v)
        e.cell(er, 5).number_format = "dd-mmm-yyyy"; e.cell(er, 6).number_format = NUM; er += 1
    for ex in errs:
        for k, v in enumerate([os.path.basename(ex["file"]), ex["sheet"], ex["row"], "", None, None, ex["reason"]], start=1):
            e.cell(er, k, v)
        er += 1
    if len(exc):
        for _, x in exc.iterrows():
            vals = [os.path.basename(x["file"]), x["sheet"], x["row"], x["name"], x["sale_date"].date(), x["sale_value"], "EXCLUDED: " + x["reason"]]
            for k, v in enumerate(vals, start=1): e.cell(er, k, v)
            e.cell(er, 5).number_format = "dd-mmm-yyyy"; e.cell(er, 6).number_format = NUM; er += 1
    for ci, wd in enumerate([30, 22, 7, 30, 13, 14, 110], start=1): e.column_dimensions[L(ci)].width = wd
    e.freeze_panes = "A2"

    # ------------------------------------------------------------------ Reconciliation
    q = wb.create_sheet("Reconciliation")
    q["A1"] = "1.  Per-file tie-out"; q["A1"].font = Font(bold=True, size=12)
    hdr_row(q, 2, ["Source file", "Sheet", "Rows included", "Sale value", "Net gain (this tool)", "Broker-reported gain (sum of rows)",
                   "Variance", "Likely reason for variance"])
    rr = 3
    for (f, sh), d in res.groupby(["file", "sheet"]):
        bg = float(d["broker_gain"].sum()) if d["broker_gain"].notna().any() else None
        mine = float(d["net"].sum()); var = None if bg is None else mine - bg
        why = ""
        if var is not None and abs(var) > 0.5:
            stt = float(d["stt"].sum()); cu = float((d["cost_used"] - d["actual_cost"]).sum())
            parts = []
            if abs(var + stt) < 1 or abs(var - stt) < 1: parts.append("STT (not deductible)")
            if abs(cu) > 0.5: parts.append(f"grandfathering uplift {cu:,.0f}")
            exp = float(d["expenses"].sum())
            if exp: parts.append(f"expenses deducted {exp:,.0f} (broker figure is gross of them)")
            if "derived" in d and d["derived"].any() and abs(var) <= 0.001 * max(float(d["sale_value"].sum()), 1):
                parts.append("rounding: report gives per-unit prices, sale value = units x price")
            if d["flags"].astype(str).str.contains("exit load").any():
                parts.append("exit load netted off the amount received (broker's own gain is on gross NAV; here it is allowed as a transfer expense)")
            why = "; ".join(parts) or "check Workings"
        for k, v in enumerate([os.path.basename(f), sh, len(d), float(d["sale_value"].sum()), mine, bg, var, why], start=1):
            c = q.cell(rr, k, v)
            if k in (4, 5, 6, 7): c.number_format = NUM
        rr += 1
    rr += 1
    q.cell(rr, 1, "2.  'Total / Sub total' rows printed in the reports vs. sum of the rows read").font = Font(bold=True, size=12); rr += 1
    hdr_row(q, rr, ["Source file", "Sheet", "Row of total", "Label", "Rows summed", "Sum of rows read", "Total printed in report", "Status"]); rr += 1
    for f, sh, rw, lab, n, mine, rep in checks:
        ok = abs(mine - rep) <= max(1.0, 0.0005 * abs(rep))
        for k, v in enumerate([os.path.basename(f), sh, rw, lab, n, mine, rep, "OK" if ok else "MISMATCH - rows may be missed"], start=1):
            c = q.cell(rr, k, v)
            if k in (6, 7): c.number_format = NUM
            if k == 8 and not ok: c.fill = WARN
        rr += 1
    if not checks:
        q.cell(rr, 1, "(no total rows found in these reports)"); rr += 1
    rr += 1
    q.cell(rr, 1, "3.  Summary figures printed in the reports (for your manual tie-out)").font = Font(bold=True, size=12); rr += 1
    hdr_row(q, rr, ["Source file", "Sheet", "Row", "Label in report", "Value"]); rr += 1
    for f, sh, rw, lab, n in rlines:
        if lab == "__client__":
            continue
        for k, v in enumerate([os.path.basename(f), sh, rw, lab, n], start=1):
            c = q.cell(rr, k, v)
            if k == 5: c.number_format = NUM
        rr += 1
    for ci, wd in enumerate([34, 26, 14, 52, 16, 22, 22, 50], start=1): q.column_dimensions[L(ci)].width = wd

    # ------------------------------------------------------------------ Parse log
    p = wb.create_sheet("Parse log")
    hdr_row(p, 1, ["Source file", "Sheet", "Header row", "What was recognised"])
    for ri, (f, sh, rw, msg) in enumerate(log, start=2):
        for k, v in enumerate([os.path.basename(f), sh, rw, msg], start=1): p.cell(ri, k, v)
    for ci, wd in enumerate([34, 28, 11, 200], start=1): p.column_dimensions[L(ci)].width = wd
    wb.save(path)


# =============================================================================== DRIVER
BROKER_PATTERNS = [(r"tradesmart", "Tradesmart Fintech"), (r"zerodha|kite|tax ?pnl", "Zerodha"), (r"angel|angle|total exchange service tax|total ipft charges|bsecm and nsecm", "Angel One"), (r"kotak", "Kotak Securities"), (r"groww|transfer expenses|taxable portfolio", "Groww"),
                   (r"icici ?direct|icicidirect|icici securities|\bicici\b", "ICICI Direct"), (r"hdfc", "HDFC Securities"), (r"geojit", "Geojit"),
                   (r"m[ _-]?stock|mirae", "mStock"), (r"5 ?paisa", "5paisa"), (r"upstox|rksv", "Upstox"), (r"fyers", "Fyers"),
                   (r"cams|computer age", "CAMS (RTA)"), (r"kfin|karvy", "KFintech (RTA)"), (r"sharekhan", "Sharekhan"), (r"motilal", "Motilal Oswal"),
                   (r"(?<![a-z])dhan(?![a-z])", "Dhan"), (r"paytm", "Paytm Money"), (r"iifl|india ?infoline", "IIFL"), (r"sbi ?sec|sbicap", "SBI Securities"),
                   (r"axis ?direct|axis securities", "Axis Direct"), (r"edelweiss|nuvama", "Edelweiss / Nuvama"), (r"anand ?rathi", "Anand Rathi")]
BROKER_OF = {}


def clean_name(path):
    """File name without the upload-time prefixes (e.g. 00- or 5251256f-)."""
    return re.sub(r"^(\d\d-)?([0-9a-f]{8}-)?", "", os.path.basename(path))


def detect_broker(path, sheets):
    base = clean_name(path)
    for pat, nm in BROKER_PATTERNS:
        if re.search(pat, base, re.I):
            return nm
    txt = " ".join(str(c) for _, rows in sheets[:3] for r in rows[:12] for c in r if c is not None)[:4000]
    for pat, nm in BROKER_PATTERNS:
        if re.search(pat, txt, re.I):
            return nm
    return "Not identified"


LAST_KDK = {}
LAST_BIZ = {}


def run(files, out, charges=None, mf_type="equity", kdk_template=None):
    load_custom_rules()
    recs, excl, errs, checks, rlines, log = [], [], [], [], [], []
    biz_sheets = []
    for f in files:
        try:
            sheets = load_sheets(f)
        except Exception as ex:
            log.append((f, "-", "-", f"COULD NOT READ FILE: {ex!r}"))
            continue
        found = False
        BROKER_OF[f] = detect_broker(f, sheets)
        for sheet, rows in sheets:
            a, b, c, d, e = parse_sheet(f, sheet, rows, log)
            recs += a; excl += b; errs += c; checks += d; rlines += e
            bz = extract_biz(f, sheet, rows)
            if bz["rows"]: biz_sheets.append(bz)
            found = found or bool(a)
        if not any(r["file"] == f for r in recs):
            had_hdr = any(l[0] == f and str(l[3]).startswith("Header found") for l in log)
            log.append((f, "-", "-", ("Capital-gain table(s) recognised but they contain NO transactions (nil report)." if had_hdr else
                        "No capital-gain table with buy date, sale date and values was recognised in this file "
                        "(if it is a derivatives-only report that is expected; otherwise send me the file so the matcher can learn it).")))
    res, exc = compute(recs, {"mf_type": mf_type})
    if not len(res):
        res = pd.DataFrame(columns=["asset", "term", "sale_value", "cost_used", "actual_cost", "expenses", "gain", "stt", "embedded_charges",
                                    "broker_gain", "period", "exp_detail", "flags", "file", "sheet", "sale_date"])
    res = build_summary(res, charges or {})
    res["broker"] = res["file"].map(lambda f: BROKER_OF.get(f, os.path.basename(str(f)))) if len(res) else []
    if len(exc):
        exc["broker"] = exc["file"].map(lambda f: BROKER_OF.get(f, os.path.basename(str(f))))
    if "reason" not in exc.columns:
        exc = pd.DataFrame(columns=["file", "sheet", "row", "name", "sale_date", "sale_value", "broker_gain", "reason"])
    LAST_BIZ.clear()
    bdf, bmeta = biz_dataframe(biz_sheets, exc)
    LAST_BIZ.update(df=bdf, meta=bmeta, summary=biz_summary(bdf, bmeta, BROKER_OF))
    LAST_KDK.clear()
    if kdk_template and len(res):
        kout = os.path.splitext(out)[0] + "_KDK.xlsx"
        try:
            counts, knotes = write_kdk(kdk_template, kout, res, exc)
            LAST_KDK.update(path=kout, counts=counts, notes=knotes)
        except Exception as ex:
            LAST_KDK.update(error=repr(ex))
    elif kdk_template:
        LAST_KDK.update(error="No capital-gain trades found, so the KDK template was not filled.")
    write_excel(res, exc, errs, checks, rlines, log, charges, out, files)
    return res, exc, errs, checks, rlines, log


def print_summary(res):
    cols, m = matrix(res)
    names = ["Sale value", "Purchase cost", "Gross P/(L)", "Expenses", "NET P/(L)"]
    print(f"{'':16}" + "".join(f"{a[:6]+' '+t:>16}" for a, t in cols) + f"{'TOTAL':>16}")
    for nm, k in zip(names, ("sale", "cost", "gross", "exp", "net")):
        print(f"{nm:16}" + "".join(f"{v:16,.2f}" for v in m[k]) + f"{sum(m[k]):16,.2f}")


# =============================================================================== GUI
# =============================================================================== FILE STATUS (what was / was not read)
def file_status(files, res, exc, errs, log):
    """One row per uploaded file: broker (if it can be read from file name / content), status and reason."""
    out = []
    for f in files:
        base = clean_name(f)
        broker = BROKER_OF.get(f) or detect_broker(f, [])
        n_in = int((res["file"] == f).sum()) if len(res) else 0
        n_ex = int((exc["file"] == f).sum()) if len(exc) else 0
        n_er = sum(1 for e in errs if e["file"] == f)
        msgs = [str(l[3]) for l in log if l[0] == f]
        net = float(res.loc[res["file"] == f, "net"].sum()) if n_in else 0.0
        _bd = LAST_BIZ.get("df")
        n_biz = int((_bd["file"] == f).sum()) if _bd is not None and len(_bd) else 0
        if any(m.startswith("COULD NOT READ FILE") for m in msgs):
            st, lvl = "NOT READ", "bad"
            det = next(m for m in msgs if m.startswith("COULD NOT READ FILE")) + " - file may be corrupt, password-protected or not an Excel/CSV report."
        elif n_in:
            st, lvl = "Parsed", "ok"
            det = f"{n_in} trades included, net P/(L) {net:,.2f}" + (f"; {n_ex} intraday/business rows excluded" if n_ex else "")
            if n_biz: det += f"; {n_biz} F&O/intraday entries captured (see F&O and Intraday sheet)"
            if n_er: st, lvl, det = "Parsed with warnings", "warn", det + f"; {n_er} row(s) with unreadable dates NOT included"
        elif n_biz:
            st, lvl, det = "Parsed - F&O / intraday", "ok", f"{n_biz} F&O / commodity / intraday entries captured as business income (see F&O and Intraday sheet); no capital-gain trades in this file"
        elif n_ex:
            st, lvl, det = "Parsed - no capital gains", "warn", f"{n_ex} rows read but all are intraday / business income (not capital gains)"
        elif any("NO transactions" in m for m in msgs):
            st, lvl, det = "Parsed - nil report", "warn", "Capital-gain tables found but they contain no transactions"
        elif any(m.startswith("Skipped sheet") or "ignored" in m and ("business income" in m or "Derivatives table" in m) for m in msgs):
            st, lvl, det = "Skipped - derivatives", "warn", "Derivatives / F&O / currency / commodity report (business income, not capital gains)"
        else:
            st, lvl = "NOT PARSED", "bad"
            det = ("No capital-gain table with buy date, sale date and values was recognised. If this is a derivatives-only report that is expected; "
                   "otherwise the format is new - send it to be added to the matcher.")
        out.append(dict(file=base, broker=broker, status=st, level=lvl, detail=det, trades=n_in, net=net))
    return out


def fno_rows():
    """Broker-wise F&O + intraday totals (all segments combined) for the web page."""
    s = LAST_BIZ.get("summary")
    if s is None or not len(s): return []
    cols = ["entries", "turnover", "fav", "unfav", "gross"] + list(HEADS) + ["exp", "net"]
    a = s.groupby("broker", sort=False)[cols].sum().reset_index()
    rows = [dict(r) for r in a.to_dict("records")]
    rows.append(dict(broker="TOTAL - ALL BROKERS", **{c: float(a[c].sum()) for c in cols}))
    return rows


def broker_metrics(res):
    """{broker: {metric: [9 values]}} + TOTAL, columns = Eq STCG/LTCG/Total, NonEq STCG/LTCG/Total, All STCG/LTCG/Total."""
    def vals(d):
        o = {}
        for key, col in (("sale", "sale_value"), ("cost", "cost_used"), ("exp", "exp_total")):
            v = []
            for a in ("Equity", "Non-Equity"):
                p = [float(d[(d["asset"] == a) & (d["term"] == t)][col].sum()) for t in ("STCG", "LTCG")]
                v += [p[0], p[1], p[0] + p[1]]
            o[key] = v + [v[0] + v[3], v[1] + v[4], v[2] + v[5]]
        o["gross"] = [a - b for a, b in zip(o["sale"], o["cost"])]
        o["net"] = [a - b for a, b in zip(o["gross"], o["exp"])]
        return o
    out = OrderedDict()
    if not len(res): return out
    for b in OrderedDict.fromkeys(res["broker"]):
        out[b] = vals(res[res["broker"] == b])
    out["TOTAL - ALL BROKERS"] = vals(res)
    return out

# =============================================================================== KDK TEMPLATE OUTPUT
_APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
KDK_DEFAULT_TEMPLATE = os.path.join(_APP_DIR, "kdk_template.xlsx")      # beside the .py / .exe


def _xl_serial(d):
    return (pd.Timestamp(d).to_pydatetime().date() - dt.date(1899, 12, 30)).days


DATE_COLS = {"1": "DE", "2": "CD", "3": "BC", "7": "CD", "9": "BCH"}


def write_kdk(template, out, res, exc=None):
    """Fill the KDK (ITR-utility style) template with the trades. The template file is edited at XML level so its
    drop-downs, hidden Master sheet, images and formatting stay exactly as they are. Returns (rows_per_sheet, notes)."""
    import zipfile, copy
    from lxml import etree
    NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    q = lambda t: "{%s}%s" % (NS, t)
    notes = []
    sheets = OrderedDict((k, []) for k in ("1", "2", "3", "7", "9"))
    cap = {"1": 499, "2": 575, "3": 496, "7": 499, "9": 530}

    def txt(v): return ("s", "" if v is None else str(v))
    def num(v): return ("n", 0.0 if v is None or (isinstance(v, float) and math.isnan(v)) else float(v))
    def dat(v): return ("n", float(_xl_serial(v)))

    for _, x in res.iterrows():
        where = f"{clean_name(x['file'])} | {x['sheet']} row {x['row']} | {x['name']}"
        qty = x["qty"] if x["qty"] else None
        price = (x["sale_value"] / qty) if qty else None
        tc = float(x.get("exp_total") or 0.0)
        if x.get("buyback"):
            sheets["7"].append({"A": txt("Listed"), "B": txt(x["name"]), "C": dat(x["sale_date"]), "D": dat(x["buy_date"]),
                                "E": num(x["sale_value"]), "F": num(x["actual_cost"]), "G": txt("No" if x.get("nostt") else "Yes")})
            notes.append(("Buy-back", where, "Placed in sheet 7 (Buyback Shares). Check treatment for buy-backs on/after 01-10-2024 (deemed dividend)."))
            continue
        fmv_unit = None
        if x["buy_date"] <= pd.Timestamp(GF_DATE) and x.get("fmv") and qty:
            fmv_unit = x["fmv"] / qty
        elif x["buy_date"] <= pd.Timestamp(GF_DATE):
            notes.append(("FMV missing", where, "Bought on/before 31-01-2018 but no FMV found - 0 written. Fill FMV as on 31/01/2018 in the template."))
        if x["asset"] == "Equity" and x["kind"] == "Listed shares":
            if not x["isin"]: notes.append(("ISIN missing", where, "ISIN is mandatory in the template - blank written."))
            sheets["1"].append({"A": txt("Listed"), "B": txt(x["isin"]), "C": txt(x["name"]), "D": dat(x["sale_date"]), "E": dat(x["buy_date"]),
                                "F": num(qty), "G": num(price), "H": num(x["sale_value"]), "I": txt("No" if x.get("nostt") else "Yes"),
                                "J": num(fmv_unit), "K": num(x["actual_cost"]), "L": num(tc)})
        elif x["asset"] == "Equity":
            if not x["isin"]: notes.append(("ISIN missing", where, "ISIN is mandatory in the template - blank written."))
            sheets["2"].append({"A": txt(x["isin"]), "B": txt(x["name"]), "C": dat(x["sale_date"]), "D": dat(x["buy_date"]), "E": num(qty),
                                "F": num(price), "G": num(x["sale_value"]), "H": num(fmv_unit), "I": num(x["actual_cost"]), "J": num(tc)})
            if x["kind"] == "Equity ETF":
                notes.append(("ETF", where, "Equity-oriented ETF placed in sheet 2 (Equity Linked Mutual Funds). Confirm it qualifies (>=65% domestic equity)."))
        elif x["kind"] == "Bond / debenture / other":
            sheets["3"].append({"A": txt("Listed"), "B": dat(x["buy_date"]), "C": dat(x["sale_date"]), "D": num(x["sale_value"]),
                                "E": num(x["actual_cost"]), "F": num(tc)})
            notes.append(("Non-equity", where, "Placed in sheet 3 (Bonds and Debentures) as Listed - change to Unlisted / another sheet if needed."))
        else:
            nature = "Debt Oriented Mutual Funds" if x["kind"] == "Debt / other mutual fund or ETF" else "Any Capital Asset"
            sheets["9"].append({"A": txt(nature), "B": dat(x["buy_date"]), "C": dat(x["sale_date"]), "D": num(x["sale_value"]),
                                "E": num(x["actual_cost"]), "F": num(tc), "G": num(0)})
            notes.append(("Non-equity", where, f"Placed in sheet 9 (Others) as '{nature}'. Check holding-period / Sec 50AA treatment."))
    for k, n in cap.items():
        if len(sheets[k]) > n:
            notes.append(("Capacity", f"Sheet {k}", f"{len(sheets[k])} rows but the template has room/validation for about {n}. Split into two files before uploading to the software."))

    zin = zipfile.ZipFile(template)
    wbx = etree.fromstring(zin.read("xl/workbook.xml"))
    rels = etree.fromstring(zin.read("xl/_rels/workbook.xml.rels"))
    rid2t = {r.get("Id"): r.get("Target") for r in rels}
    path_of = {}
    for sh in wbx.iter(q("sheet")):
        m = re.match(r"\s*(\d+)\.", sh.get("name"))
        if m:
            t = rid2t[sh.get("{%s}id" % RNS)]
            path_of[m.group(1)] = ("xl/" + t) if not t.startswith("/") else t[1:]
    colnum = lambda c: sum((ord(ch) - 64) * 26 ** i for i, ch in enumerate(reversed(c)))
    new_xml = {}
    for k, rows in sheets.items():
        if k not in path_of or not rows: continue
        root = etree.fromstring(zin.read(path_of[k]))
        sd = root.find(q("sheetData"))
        byrow = {int(r.get("r")): r for r in sd.findall(q("row"))}
        tmpl_cells = {}                                   # style per column taken from row 5
        if 5 in byrow:
            for c in byrow[5].findall(q("c")):
                tmpl_cells[re.match(r"[A-Z]+", c.get("r")).group(0)] = c.get("s")
        date_cols = DATE_COLS[k]
        date_style = next((tmpl_cells[c] for c in date_cols if tmpl_cells.get(c) and tmpl_cells[c] not in ("4", "6", "17", "32")), None)
        for i, rec in enumerate(rows):
            rn = 5 + i
            row = byrow.get(rn)
            if row is None:
                row = etree.SubElement(sd, q("row")); row.set("r", str(rn)); byrow[rn] = row
            if "spans" in row.attrib: del row.attrib["spans"]
            cells = {re.match(r"[A-Z]+", c.get("r")).group(0): c for c in row.findall(q("c"))}
            for col, (kind, val) in rec.items():
                c = cells.get(col)
                if c is None:
                    c = etree.SubElement(row, q("c")); c.set("r", f"{col}{rn}")
                    if tmpl_cells.get(col): c.set("s", tmpl_cells[col])
                    cells[col] = c
                for ch in list(c): c.remove(ch)
                if "t" in c.attrib: del c.attrib["t"]
                if col in date_cols and date_style: c.set("s", date_style)          # template leaves some date columns in a number style
                if kind == "s":
                    if val == "": continue
                    c.set("t", "inlineStr"); is_ = etree.SubElement(c, q("is")); t_ = etree.SubElement(is_, q("t")); t_.text = val
                    if val != val.strip(): t_.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                else:
                    v = etree.SubElement(c, q("v")); v.text = repr(round(val, 6)) if val != int(val) else str(int(val))
            for c in sorted(row.findall(q("c")), key=lambda e: colnum(re.match(r"[A-Z]+", e.get("r")).group(0))):
                row.remove(c); row.append(c)
        for r in sorted(sd.findall(q("row")), key=lambda e: int(e.get("r"))):
            sd.remove(r); sd.append(r)
        dim = root.find(q("dimension"))
        if dim is not None:
            m = re.match(r"([A-Z]+\d+):([A-Z]+)(\d+)", dim.get("ref") or "")
            if m: dim.set("ref", f"{m.group(1)}:{m.group(2)}{max(int(m.group(3)), 4 + len(rows))}")
        new_xml[path_of[k]] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            zout.writestr(it, new_xml.get(it.filename, zin.read(it.filename)))
    return {k: len(v) for k, v in sheets.items()}, notes



# =============================================================================== LOCAL WEB UI (offline - runs on 127.0.0.1 only)
UI_HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Capital Gains Summariser</title>
<style>
:root{--navy:#0F2747;--navy2:#1B3A63;--teal:#0E9F8E;--teal-d:#0B7F72;--bg:#F3F5F9;--card:#fff;--line:#DDE3EC;--text:#1D2939;--mute:#667085;
--ok:#1E8E5A;--okbg:#E6F5EC;--warn:#B7791F;--warnbg:#FFF4DB;--bad:#C0392B;--badbg:#FCE9E7;--gain:#1E8E5A;--loss:#C0392B}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 "Segoe UI",system-ui,-apple-system,Roboto,Arial,sans-serif}
header{background:linear-gradient(120deg,var(--navy),var(--navy2));color:#fff;padding:18px 32px;display:flex;align-items:center;gap:16px}
header .logo{width:40px;height:40px;border-radius:10px;background:var(--teal);display:grid;place-items:center;font-weight:700;font-size:20px}
header h1{margin:0;font-size:20px;font-weight:600}header p{margin:2px 0 0;font-size:12.5px;opacity:.78}
header .badge{margin-left:auto;font-size:12px;padding:5px 12px;border:1px solid rgba(255,255,255,.35);border-radius:20px}
main{max-width:1280px;margin:24px auto;padding:0 24px;display:grid;gap:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px 22px;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.card h2{margin:0 0 14px;font-size:15px;font-weight:600;color:var(--navy);display:flex;align-items:center;gap:10px}
.step{width:24px;height:24px;border-radius:50%;background:var(--navy);color:#fff;font-size:12px;display:grid;place-items:center}
.grid2{display:grid;grid-template-columns:1.6fr 1fr;gap:20px}@media(max-width:900px){.grid2{grid-template-columns:1fr}}
#drop{border:2px dashed #B8C4D6;border-radius:12px;padding:34px 20px;text-align:center;background:#F8FAFD;cursor:pointer;transition:.15s}
#drop.hov{border-color:var(--teal);background:#E8F7F5}#drop b{color:var(--navy);font-size:15px}#drop span{display:block;color:var(--mute);margin-top:4px;font-size:12.5px}
.fl{margin-top:12px;display:grid;gap:6px}.fi{display:flex;align-items:center;gap:10px;padding:8px 12px;border:1px solid var(--line);border-radius:8px;background:#fff;font-size:13px}
.fi .n{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.fi .s{color:var(--mute);font-size:12px}.fi button{border:0;background:none;color:var(--mute);cursor:pointer;font-size:16px}
label{display:block;font-size:12.5px;font-weight:600;color:var(--mute);margin:0 0 4px}
input[type=number],select{width:100%;padding:9px 11px;border:1px solid var(--line);border-radius:8px;font:inherit;background:#fff;color:var(--text)}
input:focus,select:focus{outline:2px solid var(--teal);outline-offset:-1px}.fld{margin-bottom:12px}.hint{font-size:11.5px;color:var(--mute);margin-top:3px}
.btn{border:0;border-radius:9px;padding:11px 20px;font:600 14px inherit;cursor:pointer;background:var(--teal);color:#fff;transition:.15s}
.btn:hover{background:var(--teal-d)}.btn:disabled{background:#A9B4C4;cursor:not-allowed}.btn.sec{background:#fff;color:var(--navy);border:1px solid var(--line)}.btn.sec:hover{background:#EEF2F8}
.btn.dl{background:var(--navy)}.btn.dl:hover{background:var(--navy2)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px}
.stat{border:1px solid var(--line);border-radius:10px;padding:14px 16px;background:#fff;border-top:3px solid var(--teal)}
.stat .k{font-size:11.5px;color:var(--mute);text-transform:uppercase;letter-spacing:.04em}.stat .v{font-size:20px;font-weight:700;margin-top:4px;font-variant-numeric:tabular-nums}
.stat.t{border-top-color:var(--navy)}.pos{color:var(--gain)}.neg{color:var(--loss)}
table{width:100%;border-collapse:collapse;font-size:13px}th{background:var(--navy);color:#fff;font-weight:600;text-align:right;padding:9px 10px;white-space:nowrap}
th:first-child,td:first-child{text-align:left}td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right;font-variant-numeric:tabular-nums}
tbody tr:hover{background:#F6F9FC}tr.tot td{background:#E7EDF6;font-weight:700;border-top:2px solid var(--navy)}
th.g1{background:var(--navy2)}th.g2{background:#245C6E}th.g3{background:var(--teal-d)}td.sub{font-weight:600;background:#F8FAFD}
.pill{display:inline-block;padding:2px 10px;border-radius:12px;font-size:11.5px;font-weight:600;white-space:nowrap}
.pill.ok{background:var(--okbg);color:var(--ok)}.pill.warn{background:var(--warnbg);color:var(--warn)}.pill.bad{background:var(--badbg);color:var(--bad)}
.tw{overflow-x:auto}td.l{text-align:left}.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.sp{flex:1}
.alert{padding:11px 14px;border-radius:9px;margin-bottom:12px;font-size:13px}.alert.bad{background:var(--badbg);color:var(--bad);border:1px solid #F3C4BE}.alert.warn{background:var(--warnbg);color:var(--warn);border:1px solid #F0DDA6}
.spin{display:inline-block;width:14px;height:14px;border:2px solid #fff;border-top-color:transparent;border-radius:50%;animation:r .7s linear infinite;vertical-align:-2px;margin-right:8px}@keyframes r{to{transform:rotate(360deg)}}
footer{max-width:1280px;margin:0 auto 30px;padding:0 24px;color:var(--mute);font-size:12px}.hide{display:none}
</style></head><body>
<header><div class="logo">&#8377;</div><div><h1>Capital Gains Summariser</h1><p>Indian broker &amp; RTA capital-gain reports &rarr; Equity / Non-Equity, STCG / LTCG, broker-wise</p></div><div class="badge">Offline &middot; data never leaves this computer</div><button class="btn sec" id="quit" style="padding:6px 14px;font-size:12px" title="Stop the tool">Quit</button></header>
<main>
<div class="grid2">
 <section class="card"><h2><span class="step">1</span>Upload broker / RTA reports</h2>
  <div id="drop"><b>Drop files here or click to browse</b><span>.xlsx .xls .csv .html &mdash; any number of brokers, any format</span></div>
  <input id="pick" type="file" multiple class="hide" accept=".xlsx,.xls,.csv,.txt,.html,.htm">
  <div class="fl" id="fl"></div></section>
 <section class="card"><h2><span class="step">2</span>Options</h2>
  <div class="fld"><label>Extra charges to deduct - Equity (Rs)</label><input id="eq" type="number" min="0" step="0.01" value="0"><div class="hint">Optional. Allocated across Equity trades by sale value.</div></div>
  <div class="fld"><label>Extra charges to deduct - Non-Equity (Rs)</label><input id="ne" type="number" min="0" step="0.01" value="0"></div>
  <div class="fld"><label>Treat equity mutual funds / ETFs as</label><select id="mf"><option value="equity">Equity-oriented (default)</option><option value="other">Non-equity (debt / other)</option></select></div>
  <div class="fld" style="padding:12px;border:1px solid var(--line);border-radius:9px;background:#F8FAFD"><label style="display:flex;gap:8px;align-items:center;margin:0;color:var(--navy);cursor:pointer"><input type="checkbox" id="kdk" style="width:16px;height:16px"> Also generate report in KDK template format</label>
   <div id="kdkbox" class="hide" style="margin-top:10px"><label>KDK template (.xlsx) <span id="tplstat" style="font-weight:400"></span></label><input type="file" id="tpl" accept=".xlsx" style="font-size:12px"><div class="hint">Optional once a template is saved - the last uploaded template is remembered on this computer.</div></div></div>
  <button class="btn" id="go" disabled style="width:100%">Generate summary</button></section>
</div>
<div id="res" class="hide">
 <section class="card"><h2><span class="step">3</span>File check <span class="sp"></span><span id="fsum" style="font-weight:400;color:var(--mute);font-size:12.5px"></span></h2><div id="alerts"></div><div class="tw"><table id="ft"></table></div></section>
 <section class="card"><h2><span class="step">4</span>Result</h2><div class="stats" id="stats"></div></section>
 <section class="card"><h2>Broker-wise summary <span class="sp"></span>
   <select id="metric" style="width:auto"><option value="net">Net profit / (loss)</option><option value="sale">Total sale value</option><option value="cost">Total purchase cost</option><option value="gross">Gross profit / (loss)</option><option value="exp">Charges / expenses</option></select></h2>
   <div class="tw"><table id="bt"></table></div>
   <div class="row" style="margin-top:16px"><span class="sp"></span><button class="btn dl" id="dl">Download Excel workbook (with workings)</button></div></section>
 <section class="card hide" id="fcard"><h2>F&amp;O and intraday &mdash; broker-wise (business income) <span class="sp"></span></h2><div class="tw"><table id="ft2"></table></div></section>
 <section class="card hide" id="kcard"><h2>KDK template output <span class="sp"></span><button class="btn dl" id="dlk">Download KDK template (filled)</button></h2><div id="kinfo"></div></section>
</div></main>
<footer>Figures are computed from the broker reports uploaded. Tax rates, grandfathering and term rules are in the CONFIG block of the tool - please verify before filing.</footer>
<script>
const $=s=>document.querySelector(s);let files=[],job=null,data=null;
const fmt=n=>{if(n==null)return'-';const a=Math.abs(n).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2});return n<0?'('+a+')':(Math.abs(n)<0.005?'-':a)};
const cls=n=>n<0?'neg':(n>0?'pos':'');const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function draw(){$('#fl').innerHTML=files.map((f,i)=>`<div class="fi"><span class="n">${esc(f.name)}</span><span class="s">${(f.size/1024).toFixed(0)} KB</span><button data-i="${i}" title="Remove">&times;</button></div>`).join('');
 $('#go').disabled=!files.length;$('#fl').querySelectorAll('button').forEach(b=>b.onclick=()=>{files.splice(+b.dataset.i,1);draw()})}
function add(l){for(const f of l)if(!files.some(x=>x.name===f.name&&x.size===f.size))files.push(f);draw()}
const d=$('#drop');d.onclick=()=>$('#pick').click();$('#pick').onchange=e=>{add(e.target.files);e.target.value=''};
['dragenter','dragover'].forEach(t=>d.addEventListener(t,e=>{e.preventDefault();d.classList.add('hov')}));
['dragleave','drop'].forEach(t=>d.addEventListener(t,e=>{e.preventDefault();d.classList.remove('hov')}));d.addEventListener('drop',e=>add(e.dataTransfer.files));
$('#go').onclick=async()=>{const b=$('#go');b.disabled=true;b.innerHTML='<span class="spin"></span>Reading reports...';
 const fd=new FormData();files.forEach(f=>fd.append('files',f,f.name));fd.append('eq',$('#eq').value||0);fd.append('ne',$('#ne').value||0);fd.append('mf',$('#mf').value);if($('#kdk').checked){fd.append('kdk','1');if($('#tpl').files[0])fd.append('kdk_template',$('#tpl').files[0],'kdk_template.xlsx')}
 try{const r=await fetch('/process',{method:'POST',body:fd});data=await r.json();if(data.error)throw new Error(data.error);job=data.job;render()}
 catch(e){alert('Could not process: '+e.message)}b.disabled=false;b.textContent='Generate summary'};
function render(){$('#res').classList.remove('hide');
 const bad=data.files.filter(f=>f.level==='bad'),warn=data.files.filter(f=>f.level==='warn');
 $('#fsum').textContent=`${data.files.length} file(s): ${data.files.filter(f=>f.level==='ok').length} parsed, ${warn.length} nothing to include, ${bad.length} not parsed`;
 let al='';if(bad.length)al+=`<div class="alert bad"><b>${bad.length} file(s) could NOT be parsed and are missing from the totals:</b><br>`+bad.map(f=>`&bull; ${esc(f.file)} &mdash; ${esc(f.broker)}`).join('<br>')+'</div>';
 if(data.mixed)al+=`<div class="alert warn"><b>More than one client name found:</b> ${esc(data.mixed)}. Are you mixing clients?</div>`;
 $('#alerts').innerHTML=al;
 $('#ft').innerHTML='<thead><tr><th>File</th><th style="text-align:left">Broker</th><th style="text-align:left">Status</th><th>Trades</th><th style="text-align:left">Detail</th></tr></thead><tbody>'+data.files.map(f=>`<tr><td class="l">${esc(f.file)}</td><td class="l">${esc(f.broker)}</td><td class="l"><span class="pill ${f.level}">${esc(f.status)}</span></td><td>${f.trades||'-'}</td><td class="l" style="white-space:normal;max-width:480px;color:var(--mute)">${esc(f.detail)}</td></tr>`).join('')+'</tbody>';
 const T=data.brokers['TOTAL - ALL BROKERS'];
 $('#stats').innerHTML=T?[['Net profit / (loss)',T.net[8],'t'],['Equity - net',T.net[2]],['Non-Equity - net',T.net[5]],['Short term (STCG)',T.net[6]],['Long term (LTCG)',T.net[7]],['Total sale value',T.sale[8],'t'],['Charges deducted',T.exp[8],'t']]
   .map(x=>`<div class="stat ${x[2]||''}"><div class="k">${x[0]}</div><div class="v ${x[0].includes('Charges')||x[0].includes('sale')?'':cls(x[1])}">${fmt(x[1])}</div></div>`).join(''):'<div class="alert warn">No capital-gain trades were found in the uploaded files.</div>';
 fnoRender();kdkRender();table();$('#res').scrollIntoView({behavior:'smooth'})}
function fnoRender(){const F=data.fno||[],c=$('#fcard');if(!F.length){c.classList.add('hide');return}c.classList.remove('hide');
 const cols=['Turnover','Favourable','Unfavourable','Gross','Brokerage','STT','Exch. txn','Other','Expenses','Net'],ks=['turnover','fav','unfav','gross','Brokerage','STT','Exchange transaction charges','Other trading charges','exp','net'];
 $('#ft2').innerHTML='<thead><tr><th>Broker</th><th>Entries</th>'+cols.map(x=>`<th>${x}</th>`).join('')+'</tr></thead><tbody>'+F.map(r=>`<tr class="${r.broker.startsWith('TOTAL')?'tot':''}"><td class="l">${esc(r.broker)}</td><td>${r.entries}</td>`+ks.map(k=>`<td class="${k==='net'||k==='gross'?cls(r[k]):''}">${fmt(r[k])}</td>`).join('')+'</tr>').join('')+'</tbody>'}
function kdkRender(){const k=data.kdk,c=$('#kcard');if(!k){c.classList.add('hide');return}c.classList.remove('hide');
 const nm={1:'1. Shares',2:'2. Equity Linked Mutual Funds',3:'3. Bonds and Debentures',7:'7. Buyback Shares',9:'9. Others'};
 $('#dlk').style.display=k.ready?'':'none';
 let h=k.error?`<div class="alert bad">${esc(k.error)}</div>`:'';
 if(k.ready){h+='<div class="tw"><table><thead><tr><th>Template sheet</th><th>Rows written</th></tr></thead><tbody>'+Object.entries(k.counts).map(([a,b])=>`<tr><td>${nm[a]}</td><td>${b}</td></tr>`).join('')+'</tbody></table></div>';
  if(k.nnotes)h+=`<div class="alert warn" style="margin-top:12px"><b>${k.nnotes} item(s) to check</b> (full list in the Excel workbook, sheet "KDK Notes"):<br>`+k.notes.slice(0,12).map(n=>`&bull; ${esc(n.type)}: ${esc(n.trade)} &mdash; ${esc(n.note)}`).join('<br>')+(k.notes.length>12?'<br>... and '+(k.notes.length-12)+' more groups':'')+'</div>'}
 $('#kinfo').innerHTML=h}
$('#dlk').onclick=()=>{location.href='/download/'+job+'k'};
function table(){const m=$('#metric').value,B=data.brokers;if(!Object.keys(B).length){$('#bt').innerHTML='';return}
 let h='<thead><tr><th rowspan="2">Broker</th><th colspan="3" class="g1" style="text-align:center">EQUITY</th><th colspan="3" class="g2" style="text-align:center">NON-EQUITY</th><th colspan="3" class="g3" style="text-align:center">ALL</th></tr><tr>'+['STCG','LTCG','Total','STCG','LTCG','Total','STCG','LTCG','Grand total'].map((x,i)=>`<th class="g${i<3?1:i<6?2:3}">${x}</th>`).join('')+'</tr></thead><tbody>';
 for(const[b,v]of Object.entries(B)){const t=b.startsWith('TOTAL');h+=`<tr class="${t?'tot':''}"><td>${esc(b)}</td>`+v[m].map((x,i)=>`<td class="${[2,5,8].includes(i)?'sub ':''}${m==='net'||m==='gross'?cls(x):''}">${fmt(x)}</td>`).join('')+'</tr>'}
 $('#bt').innerHTML=h+'</tbody>'}
setInterval(()=>fetch('/ping').catch(()=>{}),5000);fetch('/ping').catch(()=>{});
$('#quit').onclick=async()=>{try{await fetch('/quit')}catch(e){}document.body.innerHTML='<div style="padding:80px;text-align:center;font:16px Segoe UI,Arial;color:#0F2747"><b>Capital Gains Summariser has stopped.</b><br>You can close this tab.</div>'};
$('#kdk').onchange=()=>$('#kdkbox').classList.toggle('hide',!$('#kdk').checked);
$('#metric').onchange=table;$('#dl').onclick=()=>{location.href='/download/'+job};
</script></body></html>"""


def _group_notes(notes):
    g = OrderedDict()
    for a, b, c in notes:
        key = (a, b.split(" | ")[-1], c)
        g[key] = g.get(key, 0) + 1
    return [dict(type=a, trade=f"{t} ({n} row{'s' if n > 1 else ''})", note=c) for (a, t, c), n in g.items()][:300]


def web_ui(port=8765, open_browser=True):
    import http.server, socketserver, threading, tempfile, json, webbrowser, uuid, shutil
    from email.parser import BytesParser
    from email.policy import default as _pol
    import time
    if sys.stdout is None: sys.stdout = open(os.devnull, "w")      # pythonw.exe has no console
    if sys.stderr is None: sys.stderr = open(os.path.join(tempfile.gettempdir(), "capgain_error.log"), "a")
    jobs, work = {}, tempfile.mkdtemp(prefix="capgain_")
    state = {"last": time.time(), "seen": False, "start": time.time()}

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, code, body, ctype="application/json", extra=None):
            if isinstance(body, str): body = body.encode("utf-8")
            self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
            for k, v in (extra or {}).items(): self.send_header(k, v)
            self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            if self.path in ("/", "/index.html"):
                return self._send(200, UI_HTML, "text/html; charset=utf-8")
            if self.path == "/ping":
                state["last"] = time.time(); state["seen"] = True
                return self._send(200, "ok", "text/plain")
            if self.path == "/quit":
                self._send(200, "bye", "text/plain")
                threading.Thread(target=lambda: (time.sleep(0.3), srv.shutdown()), daemon=True).start()
                return
            if self.path.startswith("/download/"):
                key = self.path.split("/")[-1]
                p = jobs.get(key)
                if p and os.path.exists(p):
                    fn = "capital_gain_summary_KDK.xlsx" if key.endswith("k") else "capital_gain_summary.xlsx"
                    return self._send(200, open(p, "rb").read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                      {"Content-Disposition": f'attachment; filename="{fn}"'})
            self._send(404, "not found", "text/plain")
        def do_POST(self):
            if self.path != "/process": return self._send(404, "{}")
            try:
                n = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(n)
                msg = BytesParser(policy=_pol).parsebytes(b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + raw)
                job = uuid.uuid4().hex[:12]; d = os.path.join(work, job); os.makedirs(d)
                paths, form, tpl = [], {}, None
                for part in msg.iter_parts():
                    nm, fn = part.get_param("name", header="content-disposition"), part.get_filename()
                    data = part.get_payload(decode=True) or b""
                    if fn and nm == "kdk_template":
                        tpl = os.path.join(d, "kdk_template_upload.xlsx"); open(tpl, "wb").write(data)
                    elif fn:
                        p = os.path.join(d, f"{len(paths):02d}-" + re.sub(r"[^\w.\- ()]", "_", os.path.basename(fn))); open(p, "wb").write(data); paths.append(p)
                    else:
                        form[nm] = data.decode("utf-8", "ignore")
                out = os.path.join(d, "capital_gain_summary.xlsx")
                ch = {"Equity": float(form.get("eq") or 0), "Non-Equity": float(form.get("ne") or 0)}
                want_kdk = form.get("kdk") == "1"
                if want_kdk and tpl:
                    try: shutil.copyfile(tpl, KDK_DEFAULT_TEMPLATE)          # remember the uploaded template for next time
                    except Exception: pass
                use_tpl = (tpl or (KDK_DEFAULT_TEMPLATE if os.path.exists(KDK_DEFAULT_TEMPLATE) else None)) if want_kdk else None
                res, exc, errs, checks, rl, log = run(paths, out, ch, form.get("mf", "equity"), use_tpl)
                jobs[job] = out
                kd = None
                if want_kdk:
                    kd = dict(error=LAST_KDK.get("error") or ("" if LAST_KDK.get("path") else "No KDK template available - upload it in the options box."),
                              ready=bool(LAST_KDK.get("path")), counts=LAST_KDK.get("counts", {}),
                              notes=_group_notes(LAST_KDK.get("notes", [])), nnotes=len(LAST_KDK.get("notes", [])))
                    if LAST_KDK.get("path"): jobs[job + "k"] = LAST_KDK["path"]
                names = OrderedDict()
                for f_, sh_, rw_, lab_, val_ in rl:
                    if lab_ == "__client__": names.setdefault(re.sub(r"\s+", " ", str(val_).upper()), 1)
                fs = file_status(paths, res, exc, errs, log)
                self._send(200, json.dumps(dict(job=job, kdk=kd, files=fs, brokers=broker_metrics(res), fno=fno_rows(), mixed=("; ".join(names) if len(names) > 1 else "")), default=float))
            except Exception as ex:
                import traceback; traceback.print_exc()
                self._send(200, json.dumps(dict(error=repr(ex))))

    class S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True
    srv = None
    for p in range(port, port + 20):
        try: srv = S(("127.0.0.1", p), H); break
        except OSError: continue
    if srv is None:
        return
    def watchdog():                      # no console to close -> stop when the browser tab has been closed
        while True:
            time.sleep(10)
            idle = time.time() - state["last"]
            if (state["seen"] and idle > 600) or (not state["seen"] and time.time() - state["start"] > 900):
                srv.shutdown(); return
    threading.Thread(target=watchdog, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"Capital Gains Summariser running at {url}   (press Ctrl+C or close this window to stop)")
    if open_browser: threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try: srv.serve_forever()
    except KeyboardInterrupt: pass


def gui_tk():
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext
    root = tk.Tk(); root.title("Capital Gains Summariser - offline")
    files = []
    lb = tk.Listbox(root, width=95, height=8); lb.grid(row=0, column=0, columnspan=4, padx=8, pady=8)
    def add():
        for f in filedialog.askopenfilenames(filetypes=[("Reports", "*.xlsx *.xls *.csv *.txt *.html"), ("All", "*.*")]):
            files.append(f); lb.insert("end", f)
    def clear():
        files.clear(); lb.delete(0, "end")
    tk.Button(root, text="Add report files", command=add).grid(row=1, column=0, sticky="w", padx=8)
    tk.Button(root, text="Clear list", command=clear).grid(row=1, column=1, sticky="w")
    tk.Label(root, text="Extra equity charges to deduct (optional):").grid(row=2, column=0, sticky="e")
    e1 = tk.Entry(root); e1.insert(0, "0"); e1.grid(row=2, column=1, sticky="w")
    tk.Label(root, text="Extra mutual-fund charges (optional):").grid(row=3, column=0, sticky="e")
    e2 = tk.Entry(root); e2.insert(0, "0"); e2.grid(row=3, column=1, sticky="w")
    mv = tk.StringVar(value="equity")
    tk.Label(root, text="Mutual funds are:").grid(row=4, column=0, sticky="e")
    tk.OptionMenu(root, mv, "equity", "other").grid(row=4, column=1, sticky="w")
    box = scrolledtext.ScrolledText(root, width=110, height=12); box.grid(row=6, column=0, columnspan=4, padx=8, pady=8)
    def go():
        try:
            if not files:
                messagebox.showwarning("No files", "Add at least one report."); return
            out = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile="capital_gain_summary.xlsx")
            if not out: return
            res, exc, errs, checks, rl, log = run(files, out, {"Equity": float(e1.get() or 0), "Non-Equity": float(e2.get() or 0)}, mv.get())
            buf = io.StringIO(); sys_stdout, sys.stdout = sys.stdout, buf
            print_summary(res); sys.stdout = sys_stdout
            box.delete("1.0", "end"); box.insert("end", buf.getvalue() + f"\nSaved: {out}\nRows included {len(res)}, excluded {len(exc)}, errors {len(errs)}\n")
            try: os.startfile(out)
            except Exception: pass
        except Exception as ex:
            messagebox.showerror("Error", repr(ex))
    tk.Button(root, text="Generate Excel summary", command=go, bg="#1F3864", fg="white").grid(row=5, column=0, columnspan=4, pady=6)
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] in ("--ui", "--web", "--hidden-child", "--show-console"):
        # Windows: re-start with pythonw.exe so no black console window stays open.
        # If that hidden copy does not come up within ~10 s, fall back to running here (visible) so the tool still works.
        if os.name == "nt" and os.path.basename(sys.executable).lower() == "python.exe" and "--show-console" not in sys.argv:
            import subprocess, socket, time, tempfile
            pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            logp = os.path.join(tempfile.gettempdir(), "capgain_error.log")
            if os.path.exists(pyw):
                try: os.remove(logp)
                except Exception: pass
                subprocess.Popen([pyw, os.path.abspath(__file__), "--hidden-child"], creationflags=0x08000000, close_fds=True)
                up = False
                for _ in range(40):
                    time.sleep(0.25)
                    for p_ in range(8765, 8785):
                        try:
                            socket.create_connection(("127.0.0.1", p_), 0.15).close(); up = True; break
                        except OSError: pass
                    if up: break
                if up: sys.exit(0)
                print("The hidden start did not work. Reason (if any):")
                print(open(logp).read() if os.path.exists(logp) else "(no error log) - continuing in this window instead.")
        if "--hidden-child" in sys.argv: sys.argv.remove("--hidden-child")
        try:
            web_ui()
        except Exception:
            import traceback, tempfile
            with open(os.path.join(tempfile.gettempdir(), "capgain_error.log"), "a") as f_: f_.write(traceback.format_exc())
            raise
    elif sys.argv[1] == "--tk":
        gui_tk()
    else:
        ap = argparse.ArgumentParser(description="Offline capital gains summariser (India)")
        ap.add_argument("files", nargs="+")
        ap.add_argument("--out", default="capital_gain_summary.xlsx")
        ap.add_argument("--eq-charges", type=float, default=0.0)
        ap.add_argument("--mf-charges", type=float, default=0.0)
        ap.add_argument("--mf-type", default="equity", choices=["equity", "other"])
        ap.add_argument("--kdk", nargs="?", const=KDK_DEFAULT_TEMPLATE, default=None, help="also write the KDK template (optionally give the template path)")
        a = ap.parse_args()
        res, exc, errs, checks, rl, log = run(a.files, a.out, {"Equity": a.eq_charges, "Non-Equity": a.mf_charges}, a.mf_type, a.kdk)
        if LAST_KDK.get("path"): print("KDK template written:", LAST_KDK["path"], LAST_KDK["counts"])
        print_summary(res)
        print(f"\nRows included {len(res)} | excluded {len(exc)} | unreadable rows {len(errs)} | saved {a.out}")
