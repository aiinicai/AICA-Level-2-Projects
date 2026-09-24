"""
Shared parsing helpers used by every scraper/importer, plus the manual
CSV / JSON / pasted-HTML importer (the reliable fallback whenever a
source website changes its layout or blocks automated access).
"""
import re
import json
import io
import csv as csvmod


def number_text(x):
    if x is None:
        return None
    s = str(x).replace(",", "")
    s = s.replace('\u2212', '-').replace('\u2013', '-')
    # Drop the rupee sign without leaving a gap, so "-\u20b95 (-5%)" keeps its
    # minus sign (it used to become "- 5" and read as a positive 5).
    s = re.sub(r"\s*\u20b9\s*", "", s)
    s = re.sub(r"[%xX]", " ", s)
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m: return None
    value = float(m.group(0))
    # Accounting negative: the *whole* cell is one parenthesised number, e.g.
    # "(1,234.5)". A figure that merely has a bracketed percentage after it,
    # such as "\u20b925 (27%)", is not negative.
    if re.fullmatch(r"\(\s*\d+(?:\.\d+)?\s*\)", s.strip()):
        return -abs(value)
    return 0.0 if value == 0 else value


def price_text(x):
    s = str(x or "").replace(",", "")
    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", s)]
    if len(nums) > 1:
        return nums[0], nums[1]
    if nums:
        return nums[0], nums[0]
    return None, None


def normalize_status(s):
    s = (s or "").strip()
    return {'live':'Open','active':'Open','open':'Open','forthcoming':'Upcoming','upcoming':'Upcoming','closed':'Closed','listed':'Listed'}.get(s.lower(), s)


def normalize_board(s):
    return "SME" if re.search(r"sme", str(s or ""), re.I) else "Mainboard"


HEADER_ALIASES = {
    "name": ["name", "company", "security name", "issuer", "issue name", "ipo name", "ipo"],
    "symbol": ["symbol"],
    "board": ["platform", "board"],
    "status": ["status"],
    "open_date": ["start date", "open date", "opening date"],
    "close_date": ["end date", "close date", "closing date"],
    "listing_date": ["listing date", "date of listing", "listed on"],
    "gmp_source_time": ["updated", "last updated", "as of", "time", "date & time"],
    "price": ["price range", "offer price", "price band", "ipo price"],
    "lot": ["lot size", "market lot"],
    "issue": ["issue size"],
    "total": ["total subscription", "total"],
    "qib": ["qib"],
    "nii": ["nii", "hni"],
    "shni": ["shni", "s-hni", "s hni", "hni (>10l)", "hni (>₹10l)"],
    "bhni": ["bhni", "b-hni", "b hni", "hni (>1cr)", "hni (>₹1cr)"],
    "retail": ["retail", "rii"],
    "retail_apps": ["retail applications", "retail applicants", "no. of applications - retail"],
    "shni_apps": ["shni applications", "s-hni applications", "no. of applications - shni"],
    "bhni_apps": ["bhni applications", "b-hni applications", "no. of applications - bhni"],
    "gmp": ["gmp", "grey market"],
    "gmp_pct": ["gmp %", "gain %", "premium %"],
    "mcap": ["mcap", "market cap", "market capitalisation", "market capitalization", "m cap"],
}


def _find_col(headers, keys):
    for k in keys:
        if k in headers: return headers.index(k)
    for i, h in enumerate(headers):
        for k in keys:
            if k in h:
                return i
    return -1


def rows_to_records(rows):
    """Turn a generic table (list of row-lists, header first) into IPO dict records."""
    if len(rows) < 2:
        return []
    headers = [str(x).strip().lower() for x in rows[0]]
    ix = {key: _find_col(headers, aliases) for key, aliases in HEADER_ALIASES.items()}
    if ix['name'] < 0: return []
    # A genuine IPO table has at least a couple of other recognisable
    # columns alongside the name (price/GMP/status/dates/subscription).
    # A table with only the name column matched is more likely an unrelated
    # compact widget on the page (e.g. a mobile summary strip) whose single
    # remaining cell crams multiple fields together — reject it outright
    # rather than risk extracting a garbled "name".
    other_matches = sum(1 for k, i in ix.items() if k != 'name' and i >= 0)
    if other_matches < 2: return []
    # GMP % is not a rupee GMP observation, and total issue size is not demand.
    if ix['gmp'] >= 0 and '%' in headers[ix['gmp']]: ix['gmp'] = -1
    if ix['total'] >= 0 and 'size' in headers[ix['total']]: ix['total'] = -1
    # "hni" is a substring of "shni"/"bhni", so on a table that splits HNI
    # into sHNI/bHNI columns (no separate combined-HNI column), the generic
    # substring pass can mistake one of those for "nii" and double-count it.
    # Only trust that match when it didn't land on a column already claimed
    # by the more specific sHNI/bHNI aliases.
    if ix['nii'] >= 0 and ix['nii'] in (ix['shni'], ix['bhni']): ix['nii'] = -1
    name_i = ix["name"] if ix["name"] >= 0 else 0
    out = []
    for row in rows[1:]:
        if name_i >= len(row):
            continue
        name = re.sub(r"\s+", " ", str(row[name_i] or "")).strip()
        if len(name) < 3 or not re.search(r"[a-zA-Z]", name):
            continue
        if re.fullmatch(r"company|security name|total|no records? found|loading[.…]*", name, re.I):
            continue
        # A real company name never contains a GMP figure, a currency symbol,
        # or a lone open/closed status letter glued straight onto it — those
        # are signs multiple cells got concatenated (a mis-detected column,
        # or a compact widget cramming several fields into one cell).
        if re.search(r"GMP\s*[:\-]|[₹$]\s*-?\d|\(\s*-?\d+(?:\.\d+)?\s*%\s*\)\s*[OC]?$", name, re.I):
            continue

        def col(key):
            i = ix[key]
            return row[i] if 0 <= i < len(row) else None

        low, high = price_text(col("price")) if ix["price"] >= 0 else (None, None)
        rec = {
            "name": name,
            "symbol": (col("symbol") or "").strip() if ix["symbol"] >= 0 else None,
            "board": normalize_board(col("board")) if ix["board"] >= 0 else None,
            "status": normalize_status(col("status")) if ix["status"] >= 0 else None,
            "open_date": (col("open_date") or "").strip() if ix["open_date"] >= 0 else None,
            "close_date": (col("close_date") or "").strip() if ix["close_date"] >= 0 else None,
            # Previously never extracted anywhere in the codebase — every
            # status/date calculation downstream (db.is_active(),
            # db.display_status(), the web UI's statusOf()) reads
            # listing_date to decide whether an IPO should show as
            # "Listed" rather than "Closed", so without this an IPO could
            # never move into the Listed bucket from an automatic refresh.
            "listing_date": (col("listing_date") or "").strip() if ix["listing_date"] >= 0 else None,
            # Best-effort per-row "as of" timestamp some GMP tables publish
            # alongside their figure; purely informational for the GMP
            # source-diagnostics table (falls back to "Timestamp
            # unavailable" in the UI when a source's table doesn't have it).
            "gmp_source_time": (col("gmp_source_time") or "").strip() if ix["gmp_source_time"] >= 0 else None,
            "price_low": low, "price_high": high,
            "lot": number_text(col("lot")) if ix["lot"] >= 0 else None,
            "issue_size": number_text(col("issue")) if ix["issue"] >= 0 and re.search(r'cr|crore', headers[ix['issue']]) else None,
            "sub_total": number_text(col("total")) if ix["total"] >= 0 else None,
            "sub_qib": number_text(col("qib")) if ix["qib"] >= 0 else None,
            "sub_nii": number_text(col("nii")) if ix["nii"] >= 0 else None,
            "sub_shni": number_text(col("shni")) if ix["shni"] >= 0 else None,
            "sub_bhni": number_text(col("bhni")) if ix["bhni"] >= 0 else None,
            "sub_retail": number_text(col("retail")) if ix["retail"] >= 0 else None,
            "sub_retail_apps": number_text(col("retail_apps")) if ix["retail_apps"] >= 0 else None,
            "sub_shni_apps": number_text(col("shni_apps")) if ix["shni_apps"] >= 0 else None,
            "sub_bhni_apps": number_text(col("bhni_apps")) if ix["bhni_apps"] >= 0 else None,
            "gmp_amount": number_text(col("gmp")) if ix["gmp"] >= 0 else None,
            "gmp_pct": number_text(col("gmp_pct")) if ix["gmp_pct"] >= 0 else None,
            "market_cap": number_text(col("mcap")) if ix["mcap"] >= 0 else None,
        }
        out.append({k: v for k, v in rec.items() if v not in (None, "")})
    return out


def parse_csv_text(text):
    return list(csvmod.reader(io.StringIO(text)))


def parse_html_tables(html_text):
    """Extract every <table> as rows-of-cells using a lightweight parser (no lxml dep)."""
    from html.parser import HTMLParser

    class TableExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tables = []
            self._in_table = self._in_row = self._in_cell = False
            self._cell_text = ""

        def handle_starttag(self, tag, attrs):
            if tag == "table":
                self._in_table = True
                self.tables.append([])
            elif tag == "tr" and self._in_table:
                self._in_row = True
                self.tables[-1].append([])
            elif tag in ("td", "th") and self._in_row:
                self._in_cell = True
                self._cell_text = ""

        def handle_endtag(self, tag):
            if tag == "table":
                self._in_table = False
            elif tag == "tr":
                self._in_row = False
            elif tag in ("td", "th") and self._in_cell:
                self._in_cell = False
                self.tables[-1][-1].append(self._cell_text.strip())

        def handle_data(self, data):
            if self._in_cell:
                self._cell_text += data

    p = TableExtractor()
    p.feed(html_text)
    return [t for t in p.tables if len(t) > 1]


def describe_page(status, text):
    """Short factual description of a fetched page, used in failure messages."""
    tables = len(parse_html_tables(text)) if text else 0
    size = len((text or '').encode('utf-8', 'ignore')) / 1024
    return f"HTTP {status}, {size:.0f} KB, {tables} table(s) with data"


def infer_source(filename, text):
    s = (filename + " " + text[:3000]).lower()
    for key in ("investorgain", "moneycontrol", "nse", "bse", "chittorgarh", "ipoji"):
        if key in s:
            return key
    return "manual"


def import_text(text, source_key="manual"):
    """
    Returns a list of normalised IPO dict records extracted from pasted/uploaded
    JSON, HTML (with one or more <table>s), or CSV text — mirrors the original
    tool's importText() so saved webpages / exported reports remain a reliable
    fallback whenever a live scrape is blocked or a site layout changes.
    """
    text = (text or "").strip()
    if not text:
        return []
    if text[0] in "{[":
        obj = json.loads(text)
        arr = obj if isinstance(obj, list) else obj.get("data", [obj])
        if not isinstance(arr, list): raise ValueError('JSON must contain a list of IPO records')
        return [r for r in arr if isinstance(r, dict) and isinstance(r.get("name"), str) and r['name'].strip()]
    if re.search(r"<table|<!doctype|<html", text, re.I):
        records = []
        for table in parse_html_tables(text):
            records.extend(rows_to_records(table))
        return records
    return rows_to_records(parse_csv_text(text))
