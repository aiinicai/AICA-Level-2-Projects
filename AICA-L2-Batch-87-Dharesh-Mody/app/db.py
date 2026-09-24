"""
SQLite persistence layer for CA IPO Compass.
No server required — everything lives in one .db file next to the app.
"""
import sqlite3
import json
import os
import re
import threading
import copy
import uuid
from datetime import datetime, timezone, date, time as dtime, timedelta

from . import names as _names

# India Standard Time is a fixed UTC+5:30 offset with no daylight-saving
# changes, so this is exactly equivalent to zoneinfo's 'Asia/Kolkata' — but
# zoneinfo requires an IANA tzdata database that Windows does not ship with
# by default (only Linux/Mac normally have it pre-installed), which crashed
# the app on startup with ZoneInfoNotFoundError. A fixed offset needs no
# external tzdata package at all.
IST = timezone(timedelta(hours=5, minutes=30))

APP_DIR = os.environ.get('IPO_COMPASS_DATA_DIR') or os.path.join(os.path.expanduser("~"), "CA_IPO_Compass")
os.makedirs(APP_DIR, exist_ok=True)
DB_PATH = os.path.join(APP_DIR, "ipo_compass.db")
# Optional user-maintained equivalences for company names the automatic
# matcher cannot resolve, e.g. {"Some Company Limited": ["SCL", "Some Co"]}.
_names.ALIAS_FILE = os.path.join(APP_DIR, "name_aliases.json")

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS ipos (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    symbol TEXT, exchange TEXT, board TEXT, status TEXT,
    sector TEXT, location TEXT,
    open_date TEXT, close_date TEXT, listing_date TEXT,
    price_low REAL, price_high REAL, lot INTEGER, sme_lots INTEGER,
    issue_size REAL, fresh REAL, ofs REAL, market_cap REAL,
    years TEXT, revenue TEXT, ebitda TEXT, pat TEXT, cfo TEXT, fcf TEXT,
    de REAL, post_de REAL, roe REAL, roce REAL, pe REAL, peer_pe REAL,
    inv_days REAL, deb_days REAL, cred_days REAL,
    top_cust REAL, top_supp REAL, business_score REAL,
    anchor REAL, liquidity REAL,
    sub_total REAL, sub_qib REAL, sub_nii REAL, sub_shni REAL, sub_bhni REAL,
    sub_retail REAL, sub_retail_apps REAL, sub_shni_apps REAL, sub_bhni_apps REAL,
    sub_qib_anchor REAL, cutoff_price REAL, net_worth REAL, net_worth_previous REAL, borrowings REAL,
    promoter_pledge REAL, ipo_debt_repayment REAL, post_issue_eps REAL, post_issue_shares REAL,
    wc_days_change REAL, key_risks TEXT, business_description TEXT, sub_at TEXT,
    gmp_amount REAL, gmp_pct REAL, gmp_trend TEXT, gmp_at TEXT,
    override_verdict TEXT, override_reason TEXT, notes TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS gmp_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ipo_id TEXT NOT NULL,
    source TEXT, amount REAL, pct REAL, at TEXT,
    FOREIGN KEY(ipo_id) REFERENCES ipos(id)
);
CREATE TABLE IF NOT EXISTS sources_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ipo_id TEXT NOT NULL,
    name TEXT, url TEXT, fields TEXT, at TEXT,
    FOREIGN KEY(ipo_id) REFERENCES ipos(id)
);
CREATE TABLE IF NOT EXISTS refresh_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT, source TEXT, ok INTEGER, message TEXT, records INTEGER
);
CREATE TABLE IF NOT EXISTS gmp_quotes (
    ipo_id TEXT NOT NULL,
    source_key TEXT NOT NULL,
    source_name TEXT, source_url TEXT,
    gmp_amount REAL, gmp_pct REAL,
    fetch_status TEXT, note TEXT, source_time TEXT, at TEXT,
    PRIMARY KEY (ipo_id, source_key),
    FOREIGN KEY(ipo_id) REFERENCES ipos(id)
);
"""

BLANK = {
    "id": "", "name": "Unnamed IPO", "symbol": "", "exchange": "", "board": "Mainboard",
    "status": "Upcoming", "sector": "", "location": "",
    "open_date": "", "close_date": "", "listing_date": "",
    "price_low": None, "price_high": None, "lot": None, "sme_lots": None,
    "issue_size": None, "fresh": None, "ofs": None, "market_cap": None,
    "years": ["FY-2", "FY-1", "Latest"], "revenue": [None, None, None],
    "ebitda": [None, None, None], "pat": [None, None, None],
    "cfo": [None, None, None], "fcf": [None, None, None],
    "de": None, "post_de": None, "roe": None, "roce": None, "pe": None, "peer_pe": None,
    "inv_days": None, "deb_days": None, "cred_days": None,
    "top_cust": None, "top_supp": None, "business_score": None,
    "anchor": None, "liquidity": None,
    "sub_total": None, "sub_qib": None, "sub_nii": None, "sub_shni": None,
    "sub_bhni": None, "sub_retail": None, "sub_retail_apps": None,
    "sub_shni_apps": None, "sub_bhni_apps": None,
    "sub_qib_anchor": None, "cutoff_price": None, "net_worth": None, "net_worth_previous": None, "borrowings": None,
    "promoter_pledge": None, "ipo_debt_repayment": None, "post_issue_eps": None, "post_issue_shares": None,
    "wc_days_change": None, "key_risks": "", "business_description": "", "sub_at": "",
    "gmp_amount": None, "gmp_pct": None, "gmp_trend": "Unknown", "gmp_at": "",
    "override_verdict": "", "override_reason": "", "notes": "",
    "research": {}, "field_sources": {},
}

_JSON_FIELDS = {"years", "revenue", "ebitda", "pat", "cfo", "fcf", "research", "field_sources"}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def slugify(name):
    import re
    s = (name or "").lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\b(limited|ltd)\b", " ", s)
    s = re.sub(r'\s+ipo\s*$', '', s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "ipo"


def names_match(a, b, allow_typos=False):
    """
    True if two company names almost certainly refer to the same company.

    Delegates to app/names.py, which ignores the differences that different
    IPO websites introduce around the same company: legal suffixes (Limited,
    Ltd, Pvt, Private), "IPO"/"GMP"/"SME"/"NSE SME" tags, the word "India",
    "&" vs "and", abbreviations (Engg/Engineering, Corp/Corporation,
    Tech/Technologies, Shri/Shree/Sri), "(formerly ...)" notes, and
    initialisms (NSE = National Stock Exchange of India Limited, NSDL, L&T).
    Unrelated companies that merely share a generic first word ("Om Galaxy"
    vs "Om Industries") are still kept apart.
    """
    return _names.names_match(a, b, allow_typos)


def match_score(a, b, allow_typos=False):
    return _names.match_score(a, b, allow_typos)


def ranked_matches(name, records, allow_typos=True):
    """Records whose name matches `name`, most confident match first."""
    return _names.rank_matches(name, records, lambda r: r['name'], allow_typos)


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, connect() as conn:
        old_columns = {r[1] for r in conn.execute('PRAGMA table_info(ipos)')}
        if old_columns and 'research' not in old_columns:
            backup=DB_PATH+'.before-compat-'+datetime.now().strftime('%Y%m%d%H%M%S')+'.bak'
            with sqlite3.connect(backup) as destination: conn.backup(destination)
        conn.executescript(SCHEMA)
        columns = {r[1] for r in conn.execute('PRAGMA table_info(ipos)')}
        column_types = {
            'research': 'TEXT', 'field_sources': 'TEXT', 'sub_at': 'TEXT',
            'key_risks': 'TEXT', 'business_description': 'TEXT',
            'sub_qib_anchor': 'REAL', 'cutoff_price': 'REAL', 'net_worth': 'REAL',
            'net_worth_previous': 'REAL', 'borrowings': 'REAL', 'promoter_pledge': 'REAL',
            'ipo_debt_repayment': 'REAL', 'post_issue_eps': 'REAL', 'post_issue_shares': 'REAL',
            'wc_days_change': 'REAL',
        }
        for name, sql_type in column_types.items():
            if name not in columns: conn.execute(f'ALTER TABLE ipos ADD COLUMN {name} {sql_type}')
        conn.commit()
    consolidate_duplicates()


def _row_to_record(row):
    r = dict(row)
    for f in _JSON_FIELDS:
        try:
            r[f] = json.loads(r[f]) if r.get(f) else copy.deepcopy(BLANK[f])
        except Exception:
            r[f] = copy.deepcopy(BLANK[f])
    return r


def ensure_record(partial):
    """Fill missing keys with sane defaults, like the JS `ensure()` did."""
    r = copy.deepcopy(BLANK)
    r.update({k: v for k, v in partial.items() if v is not None})
    if not r.get("id"):
        r["id"] = slugify(r["name"])[:60] + "-" + uuid.uuid4().hex[:12]
    return r


def upsert_ipo(record):
    r = ensure_record(record)
    cols = [c for c in BLANK.keys()]
    values = []
    for c in cols:
        v = r.get(c)
        if c in _JSON_FIELDS:
            v = json.dumps(v)
        values.append(v)
    placeholders = ",".join("?" for _ in cols)
    updates = ",".join(f"{c}=excluded.{c}" for c in cols if c != "id")
    sql = (f"INSERT INTO ipos ({','.join(cols)}, updated_at) VALUES ({placeholders}, ?) "
           f"ON CONFLICT(id) DO UPDATE SET {updates}, updated_at=excluded.updated_at")
    with _lock, connect() as conn:
        conn.execute(sql, values + [now_iso()])
        conn.commit()
    return r["id"]


def find_by_name(name):
    with _lock, connect() as conn:
        rows = conn.execute("SELECT * FROM ipos").fetchall()
    best = _names.rank_matches(name, rows, lambda row: row["name"], allow_typos=True)
    return _row_to_record(best[0]) if best else None


def get(ipo_id):
    with _lock, connect() as conn:
        row = conn.execute("SELECT * FROM ipos WHERE id=?", (ipo_id,)).fetchone()
    return _row_to_record(row) if row else None


def all_ipos():
    with _lock, connect() as conn:
        rows = conn.execute("SELECT * FROM ipos ORDER BY updated_at DESC").fetchall()
    return [_row_to_record(r) for r in rows]


def _closed_by_cutoff(closing, today, now):
    """An IPO whose close_date is today isn't actually closed to new bids
    until bidding ends — by market convention, 5:00 PM IST. Before that time,
    still treat it as Open; after it, treat it as Closed even though the
    date-only comparison (closing < today) hasn't flipped yet."""
    if closing is None or closing != today:
        return closing is not None and closing < today
    return now.astimezone(IST).time() >= dtime(17, 0)


def is_active(record, today=None, now=None):
    """True only for an open or genuinely upcoming IPO (used to decide
    whether a *source row with no dates* is even worth keeping — see
    run_refresh's skip-brand-new-dateless-rows logic)."""
    today = today or date.today()
    now = now or datetime.now(timezone.utc)
    def parsed(key):
        try: return date.fromisoformat(str(record.get(key) or ''))
        except ValueError: return None
    opening, closing, listing = parsed('open_date'), parsed('close_date'), parsed('listing_date')
    if listing and listing <= today: return False
    if closing and _closed_by_cutoff(closing, today, now): return False
    status = str(record.get('status') or '').strip().lower()
    if status in ('closed', 'listed'): return False
    if closing: return not _closed_by_cutoff(closing, today, now)
    if opening:
        if opening >= today: return True
        return status in ('open', 'live', 'active')
    return status in ('open', 'live', 'active', 'upcoming', 'forthcoming')


def in_refresh_scope(record, today=None, now=None, closed_days=5, listed_days=5, dateless_open_days=15):
    """Which IPOs stay in scope for automatic refresh/research AND for
    display in the app at all — used both by run_refresh() and by the
    /api/state endpoint. The dashboard is meant to stay focused on
    currently-relevant IPOs, not grow into an ever-larger historical
    archive: a closed IPO stays in scope for `closed_days` after closing
    (subscription/listing-gain data keeps settling), a listed IPO for
    `listed_days` after listing, and if close_date is missing entirely, an
    open_date more than `dateless_open_days` old is treated as stale and
    dropped rather than kept forever."""
    today = today or date.today()
    now = now or datetime.now(timezone.utc)
    if is_active(record, today, now):
        return True
    def parsed(key):
        try: return date.fromisoformat(str(record.get(key) or ''))
        except ValueError: return None
    opening, closing, listing = parsed('open_date'), parsed('close_date'), parsed('listing_date')
    if listing is not None:
        return (today - listing).days <= listed_days
    if closing is not None:
        return (today - closing).days <= closed_days
    if opening is not None:
        return (today - opening).days <= dateless_open_days
    return True


def display_status(record, today=None, now=None, listed_display_days=5):
    """Derive status from dates so vague source labels such as Check are not shown.

    'Listed' is a short spotlight window (day-of-listing gain, still-settling
    figures), not a permanent bucket — used to show "Listed more than five
    days" for every past IPO forever. Once a listing is more than
    `listed_display_days` old it displays as 'Closed' instead (the deal is
    fully done; there's no further open/upcoming/listed state to be in).
    """
    today = today or date.today()
    now = now or datetime.now(timezone.utc)
    def parsed(key):
        try: return date.fromisoformat(str(record.get(key) or ''))
        except ValueError: return None
    opening, closing, listing = parsed('open_date'), parsed('close_date'), parsed('listing_date')
    if listing and listing <= today:
        return 'Listed' if (today - listing).days <= listed_display_days else 'Closed'
    if closing and _closed_by_cutoff(closing, today, now): return 'Closed'
    if opening and opening > today: return 'Upcoming'
    if (opening is None or opening <= today) and (closing is None or not _closed_by_cutoff(closing, today, now)):
        if opening or closing: return 'Open'
    status = str(record.get('status') or '').strip().title()
    if opening is None and closing is None and listing is None and status == 'Upcoming':
        return 'Verification required'
    return status if status in ('Open','Upcoming','Closed','Listed') else 'Verification required'


def consolidate_duplicates():
    """Merge duplicate copies of one IPO (e.g. BSE/NSE copies, or the same
    company recorded under a shortened name by one source and the full
    legal name by another) and preserve their linked audit rows."""
    records = all_ipos()
    clusters = []
    for record in records:
        cluster = next(
            (c for c in clusters if slugify(c[0]['name'])==slugify(record['name'])
             or names_match(c[0]['name'], record['name'])),
            None,
        )
        if cluster is None:
            clusters.append([record])
        else:
            cluster.append(record)
    remapped = {}
    for group in clusters:
        if len(group) < 2: continue
        def richness(r):
            important=('notes','research','revenue','pat','cfo','price_high','open_date','close_date')
            return sum(bool(r.get(k)) and not (isinstance(r.get(k),list) and all(v is None for v in r[k])) for k in important)
        survivor=max(group,key=richness)
        origins=survivor.get('field_sources') or {}
        exchanges=set(re.findall(r'BSE|NSE',str(survivor.get('exchange') or ''),re.I))
        for duplicate in group:
            if duplicate['id']==survivor['id']: continue
            exchanges.update(re.findall(r'BSE|NSE',str(duplicate.get('exchange') or ''),re.I))
            for key,value in duplicate.items():
                blank=survivor.get(key) in (None,'') or (isinstance(survivor.get(key),list) and all(v is None for v in survivor[key]))
                if key not in ('id','updated_at','exchange','field_sources') and blank and value not in (None,''):
                    survivor[key]=value
            origins={**(duplicate.get('field_sources') or {}),**origins}
            remapped[duplicate['id']]=survivor['id']
        if exchanges: survivor['exchange']=' / '.join(x for x in ('BSE','NSE') if x in {v.upper() for v in exchanges})
        survivor['field_sources']=origins
        upsert_ipo(survivor)
        with _lock,connect() as conn:
            for old_id,new_id in remapped.items():
                if new_id != survivor['id']: continue
                conn.execute('UPDATE gmp_history SET ipo_id=? WHERE ipo_id=?',(new_id,old_id))
                conn.execute('UPDATE sources_log SET ipo_id=? WHERE ipo_id=?',(new_id,old_id))
                conn.execute('DELETE FROM ipos WHERE id=?',(old_id,))
            conn.commit()
    return remapped


def delete_ipo(ipo_id):
    with _lock, connect() as conn:
        conn.execute("DELETE FROM ipos WHERE id=?", (ipo_id,))
        conn.execute("DELETE FROM gmp_history WHERE ipo_id=?", (ipo_id,))
        conn.execute("DELETE FROM sources_log WHERE ipo_id=?", (ipo_id,))
        conn.commit()


MALFORMED_NAME_PATTERN = re.compile(
    r"GMP\s*[:\-]|[₹$]\s*-?\d|\(\s*-?\d+(?:\.\d+)?\s*%\s*\)\s*[OC]?$"
    # Raw markup leaking into the name field — e.g. a manually imported
    # JSON record that kept a table cell's outerHTML instead of its text
    # ('<a href="/subscription/…" …>Raksan Transformers</a> <span
    # class="badge …">BSE SME</span> …'). A genuine company name never
    # contains an HTML tag, an href/class attribute, or an entity.
    r"|<\s*/?\s*[a-zA-Z][a-zA-Z0-9]*[\s>]|\b(?:href|class|target)\s*=\s*['\"]|&[a-zA-Z]+;",
    re.I,
)

def purge_malformed_records(records=None):
    """Removes records whose stored name matches the concatenated-cell or
    raw-markup garbage patterns a since-fixed parsing bug, or an unsanitised
    manual JSON import, could create (e.g. a badge column mistaken for the
    name column, producing names like 'Sonaselection IndiaIPOGMP:₹2
    (2.02%)O', or an imported record whose name is really a table cell's
    outerHTML). Safe to call every refresh — a genuine company name never
    matches this pattern. Returns how many were removed."""
    records = records if records is not None else all_ipos()
    removed = 0
    for r in records:
        if MALFORMED_NAME_PATTERN.search(r.get('name') or ''):
            delete_ipo(r['id'])
            removed += 1
    return removed


def add_gmp_history(ipo_id, source, amount, pct):
    with _lock, connect() as conn:
        conn.execute(
            "INSERT INTO gmp_history (ipo_id, source, amount, pct, at) VALUES (?,?,?,?,?)",
            (ipo_id, source, amount, pct, now_iso()),
        )
        conn.commit()


def gmp_history(ipo_id, limit=60):
    with _lock, connect() as conn:
        rows = conn.execute(
            "SELECT * FROM gmp_history WHERE ipo_id=? ORDER BY at DESC LIMIT ?",
            (ipo_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def derive_gmp_trend(ipo_id, min_gap_hours=12):
    """
    Auto-derive a GMP trend label (Rising/Stable/Falling/Sharp Fall) purely
    from this IPO's own gmp_history, instead of relying on a source
    explicitly reporting a trend column — many sources omit that column
    entirely, especially for SME issues, which is why "GMP trend" so often
    sits at "Pending" even when GMP itself is known.

    Compares the latest %-premium reading against the oldest reading that
    is at least `min_gap_hours` old (falling back to the very first
    recorded reading if history doesn't span that long yet), so a single
    intraday wobble between two GMP-table refreshes doesn't flip the label.
    Returns None (leave it at "Unknown"/Pending) when there's only one
    distinct reading so far — a trend genuinely can't be read from one point.
    """
    readings = [h for h in gmp_history(ipo_id, limit=200) if h.get('pct') is not None]
    if len(readings) < 2:
        return None
    readings.sort(key=lambda h: h['at'])  # oldest -> newest
    latest = readings[-1]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=min_gap_hours)
    baseline = next(
        (h for h in readings[:-1] if datetime.fromisoformat(h['at']) <= cutoff),
        readings[0],
    )
    if baseline is latest:
        return None
    delta = latest['pct'] - baseline['pct']
    if delta >= 5: return 'Rising'
    if delta <= -8: return 'Sharp Fall'
    if delta <= -3: return 'Falling'
    return 'Stable'


def record_gmp_quote(ipo_id, source_key, source_name, source_url, fetch_status,
                      gmp_amount=None, gmp_pct=None, source_time=None, note=None):
    """
    Store the latest raw GMP reading — or, just as importantly, the latest
    fetch *outcome* — for one (ipo, source) pair. This is independent of
    the single merged `gmp_amount` column on the ipos row: it powers the
    per-IPO "GMP" tab's source-by-source table, where every checked source
    keeps its own separate quote, its own reported timestamp (when
    available) and an honest status. A source that has nothing to say
    about this company ('no_quote_published') is never confused with a
    zero GMP, and a source that's down/blocked ('blocked'/'unavailable')
    is shown as exactly that rather than silently vanishing.
    """
    with _lock, connect() as conn:
        conn.execute(
            "INSERT INTO gmp_quotes (ipo_id, source_key, source_name, source_url, "
            "gmp_amount, gmp_pct, fetch_status, note, source_time, at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(ipo_id, source_key) DO UPDATE SET "
            "source_name=excluded.source_name, source_url=excluded.source_url, "
            "gmp_amount=excluded.gmp_amount, gmp_pct=excluded.gmp_pct, "
            "fetch_status=excluded.fetch_status, note=excluded.note, "
            "source_time=excluded.source_time, at=excluded.at",
            (ipo_id, source_key, source_name, source_url, gmp_amount, gmp_pct,
             fetch_status, note, source_time, now_iso()),
        )
        conn.commit()


def gmp_quotes_for(ipo_id, order=None):
    with _lock, connect() as conn:
        rows = conn.execute("SELECT * FROM gmp_quotes WHERE ipo_id=?", (ipo_id,)).fetchall()
    quotes = [dict(r) for r in rows]
    if order:
        rank = {key: i for i, key in enumerate(order)}
        quotes.sort(key=lambda q: rank.get(q['source_key'], len(order)))
    return quotes


def sync_gmp_quotes(source_key, source_name, source_url, records, redirect_note=None):
    """
    Called once per GMP-diagnostic source after a *successful* fetch this
    refresh. `records` is that source's full parsed table. For every IPO
    already tracked in the database, this records whether the source
    quoted it this time (and what) or explicitly logs "no_quote_published"
    when the source's table simply doesn't mention that company — a
    missing row is meaningfully different from a zero GMP or a failed
    fetch, and the diagnostics table needs to show that difference.

    `redirect_note`, when set (Chittorgarh today — see GMP_REDIRECTS in
    scrapers/__init__.py), skips using this source's own numbers for the
    diagnostics table entirely and marks every row 'directory_redirect'
    with that note instead, so a source that's really just mirroring
    another publisher isn't counted as independent corroboration.
    """
    for ipo in all_ipos():
        if redirect_note:
            record_gmp_quote(ipo['id'], source_key, source_name, source_url,
                              'directory_redirect', note=redirect_note)
            continue
        match = _best_source_row(ipo['name'], records)
        if match and match.get('gmp_amount') is not None:
            # When the source spells the company differently (extra words such
            # as "India"/"Limited"/"IPO", an abbreviation like NSE, ...) say so
            # in the GMP tab, so a looser match is never invisible.
            listed_as = re.sub(r'\s+', ' ', str(match.get('name') or '')).strip()
            note = (f'Listed by the source as \u201c{listed_as}\u201d'
                    if listed_as and listed_as.lower() != str(ipo['name']).strip().lower() else None)
            record_gmp_quote(ipo['id'], source_key, source_name, source_url, 'available',
                              gmp_amount=match.get('gmp_amount'), gmp_pct=match.get('gmp_pct'),
                              source_time=match.get('gmp_source_time'), note=note)
        else:
            record_gmp_quote(ipo['id'], source_key, source_name, source_url, 'no_quote_published')


def _best_source_row(ipo_name, records):
    """
    The row of a source's table that is this IPO, tolerant of the naming
    differences between websites (see app/names.py). Of all rows that match,
    a row that actually carries a GMP wins over one that doesn't (some sites
    list a company in more than one table), then the more confident name match.
    """
    best, best_key = None, None
    for rec in records:
        score = _names.match_score(ipo_name, rec.get('name', ''), allow_typos=True)
        if not score:
            continue
        key = (score >= 70, rec.get('gmp_amount') is not None, score)
        if best_key is None or key > best_key:
            best, best_key = rec, key
    return best


def sync_gmp_quotes_failed(source_key, source_name, source_url, message):
    """
    Called when a GMP-diagnostic source's fetch() raised this refresh —
    marks every tracked IPO's row for that source with the exact failure
    (rather than leaving a stale prior quote silently in place, which
    would misrepresent a source that's actually down as still agreeing
    with whatever it last said).
    """
    status = 'blocked' if re.search(r'403|forbidden|blocked', message, re.I) else 'unavailable'
    for ipo in all_ipos():
        record_gmp_quote(ipo['id'], source_key, source_name, source_url, status, note=str(message)[:600])


def add_source(ipo_id, name, url, fields):
    with _lock, connect() as conn:
        conn.execute(
            "INSERT INTO sources_log (ipo_id, name, url, fields, at) VALUES (?,?,?,?,?)",
            (ipo_id, name, url, fields, now_iso()),
        )
        conn.commit()


def sources_for(ipo_id, limit=25):
    with _lock, connect() as conn:
        rows = conn.execute(
            "SELECT * FROM sources_log WHERE ipo_id=? ORDER BY at DESC LIMIT ?",
            (ipo_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def log_refresh(source, ok, message, records=0):
    with _lock, connect() as conn:
        conn.execute(
            "INSERT INTO refresh_log (at, source, ok, message, records) VALUES (?,?,?,?,?)",
            (now_iso(), source, 1 if ok else 0, message, records),
        )
        conn.commit()


def recent_refresh_log(limit=100):
    with _lock, connect() as conn:
        rows = conn.execute(
            "SELECT * FROM refresh_log ORDER BY at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def last_refresh_at():
    """UTC ISO timestamp of the most recent refresh attempt across every
    source, or None if a refresh has never run. Used on startup to decide
    whether the data is fresh enough to skip an automatic refresh."""
    with _lock, connect() as conn:
        row = conn.execute("SELECT MAX(at) AS at FROM refresh_log").fetchone()
    return row["at"] if row and row["at"] else None


def refresh_is_stale(max_age_seconds=900):
    """True if there's no recorded refresh yet, or the most recent one
    finished at least `max_age_seconds` ago (default 15 minutes). Both the
    web dashboard and the classic desktop window use this to skip a
    needless refresh every time the app is opened."""
    at = last_refresh_at()
    if not at: return True
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(at)).total_seconds() >= max_age_seconds
    except ValueError:
        return True


def source_ok_recently(source_name):
    """
    Did the most recent refresh attempt for this source (by display name,
    e.g. 'Chittorgarh') succeed? Used to decide whether a secondary GMP
    source (IPOJI, then InvestorGain) is allowed to fill in/override GMP —
    i.e. only when the primary source could not be fetched this run.
    Returns True when there's no recorded attempt at all, so a brand-new
    install (or a partial refresh that skipped the primary source) doesn't
    accidentally block the fallback sources from ever populating GMP.
    """
    with _lock, connect() as conn:
        row = conn.execute(
            "SELECT ok FROM refresh_log WHERE source=? ORDER BY at DESC LIMIT 1",
            (source_name,),
        ).fetchone()
    return True if row is None else bool(row[0])


def merge_incoming(incoming, source_key, source_name, source_url, fields, official=False):
    """
    Mirrors the JS `merge()` logic: find-or-create by fuzzy name match,
    prefer official (NSE/BSE) values, fill blanks otherwise, and log GMP history.
    """
    incoming = validate_incoming(incoming)
    all_records = all_ipos()
    candidates=ranked_matches(incoming['name'],all_records)
    if len(candidates)>1:
        consolidate_duplicates()
        all_records = all_ipos()
        candidates=ranked_matches(incoming['name'],all_records)
    existing=candidates[0] if candidates else None
    r = existing if existing else ensure_record({"name": incoming.get("name", "")})
    origins = r.get('field_sources') or {}
    def blank(value):
        return value is None or value == '' or (isinstance(value, list) and all(x is None for x in value))
    incoming_exchange=incoming.get('exchange')
    SUBSCRIPTION_FIELDS = ("sub_total","sub_qib","sub_nii","sub_shni","sub_bhni",
        "sub_retail","sub_retail_apps","sub_shni_apps","sub_bhni_apps")
    for k, v in incoming.items():
        if k in ("id", "name", "exchange", "gmp_amount", "gmp_pct", "gmp_trend", "field_sources") or k in SUBSCRIPTION_FIELDS:
            continue
        if v is None or v == "":
            continue
        prior = origins.get(k, {})
        if official or blank(r.get(k)) or (not prior and r.get(k)==BLANK.get(k)) or prior.get('source') == source_key or (source_key == 'manual' and not prior.get('official')):
            r[k] = v
            origins[k] = {'source':source_key,'url':source_url,'official':bool(official),'at':now_iso()}
    if incoming_exchange:
        exchanges={x.upper() for x in re.findall(r'BSE|NSE',str(r.get('exchange') or '')+' '+str(incoming_exchange),re.I)}
        r['exchange']=' / '.join(x for x in ('BSE','NSE') if x in exchanges) if exchanges else str(incoming_exchange)
        origins['exchange']={'source':source_key,'url':source_url,'official':bool(official),'at':now_iso()}
    incoming_pct = incoming.get('gmp_pct')
    if incoming.get('gmp_amount') is not None and incoming_pct is None and r.get('price_high'):
        incoming_pct=incoming['gmp_amount']/r['price_high']*100
    primary_fresh=False
    prior_gmp=origins.get('gmp_amount',{})
    if prior_gmp.get('source')=='chittorgarh':
        try:primary_fresh=(datetime.now(timezone.utc)-datetime.fromisoformat(prior_gmp['at'])).total_seconds()<86400
        except (ValueError,KeyError):pass
        # Chittorgarh is the primary GMP source, but if its most recent
        # refresh attempt this session failed (site down/blocked/layout
        # change), don't let a merely-recent-timestamp value block the
        # fallback sources (IPOJI, then InvestorGain) from stepping in.
        if primary_fresh and not source_ok_recently('Chittorgarh'):
            primary_fresh=False
    if incoming.get("gmp_amount") is not None and (source_key in ('chittorgarh','manual') or not primary_fresh):
        r["gmp_amount"] = incoming["gmp_amount"]
        r['gmp_pct']=incoming_pct
        r["gmp_trend"] = incoming.get("gmp_trend") or r.get("gmp_trend") or "Unknown"
        r["gmp_at"] = now_iso()
        origins['gmp_amount']={'source':source_key,'url':source_url,'at':r['gmp_at'],'official':False}
    for k in SUBSCRIPTION_FIELDS:
        v = incoming.get(k)
        if v is None or v == "":
            continue
        r[k] = v
        origins[k] = {'source':source_key,'url':source_url,'official':bool(official),'at':now_iso()}
        r['sub_at'] = now_iso()
    r['field_sources'] = origins
    ipo_id = upsert_ipo(r)
    if incoming.get("gmp_amount") is not None:
        add_gmp_history(ipo_id, source_name, incoming.get("gmp_amount"), incoming_pct)
        # Prefer a trend calculated from this IPO's own GMP history (once
        # there are at least two readings spanning min_gap_hours) over
        # whatever a source's own "trend" column said, since most sources
        # leave that column blank/inconsistent — see derive_gmp_trend().
        derived_trend = derive_gmp_trend(ipo_id)
        if derived_trend and derived_trend != r.get('gmp_trend'):
            with _lock, connect() as conn:
                conn.execute("UPDATE ipos SET gmp_trend=? WHERE id=?", (derived_trend, ipo_id))
                conn.commit()
    add_source(ipo_id, source_name, source_url, fields)
    return ipo_id

def validate_incoming(record):
    import math
    from .scrapers.base import normalize_status, number_text
    if not isinstance(record, dict) or not isinstance(record.get('name'), str) or not record['name'].strip():
        raise ValueError('A company name is required')
    out = {k:v for k,v in record.items() if k in BLANK}
    if 'name' in out:
        # Defence in depth against the raw-markup garbage purge_malformed_records()
        # cleans up after the fact: a hand-edited/imported JSON record can carry a
        # table cell's outerHTML instead of its text (tags, href/class attributes,
        # HTML entities). Strip any '<...>' tag and collapse whitespace so a fresh
        # import can't recreate what the purge just removed.
        stripped = re.sub(r"<[^<>]*>", " ", out['name'])
        stripped = re.sub(r"\s+", " ", stripped).strip()
        if not stripped:
            raise ValueError('A company name is required')
        out['name'] = stripped
    numeric = {k for k,v in BLANK.items() if v is None}
    for key in numeric & out.keys():
        value = out[key]
        if value in (None, ''): out[key] = None; continue
        if isinstance(value, (dict,list,bool)): raise ValueError(f'{key} must be numeric')
        try: value = float(value)
        except (TypeError,ValueError): raise ValueError(f'{key} must be a number, not {value!r}')
        if not math.isfinite(value): raise ValueError(f'{key} must be finite')
        out[key] = value
    for key in ('revenue','ebitda','pat','cfo','fcf'):
        if key not in out: continue
        if not isinstance(out[key], list) or len(out[key]) != 3: raise ValueError(f'{key} requires three annual values, oldest first; use null for missing')
        out[key] = [None if v in (None,'') else float(v) for v in out[key]]
        if any(v is not None and not math.isfinite(v) for v in out[key]): raise ValueError(f'{key}: non-finite value')
    if 'years' in out and (not isinstance(out['years'],list) or len(out['years'])!=3): raise ValueError('years requires three annual labels')
    if 'years' in out:
        matches=[re.fullmatch(r'(?:FY)?(20\d{2}|\d{2})',str(y).strip(),re.I) for y in out['years']]
        if all(matches):
            years=[int(m[1])+(2000 if len(m[1])==2 else 0) for m in matches]
            if years[1]!=years[0]+1 or years[2]!=years[1]+1: raise ValueError('Financial years must be three consecutive years, oldest first')
    for key in ('research','field_sources'):
        if key in out and not isinstance(out[key],dict):raise ValueError(f'{key} must be a JSON object')
    if 'status' in out: out['status'] = normalize_status(out['status'])
    for key in ('open_date','close_date','listing_date'):
        if out.get(key):
            for fmt in ('%Y-%m-%d','%d-%m-%Y','%d/%m/%Y','%d-%b-%Y','%d %b %Y','%d %B %Y'):
                try: out[key]=datetime.strptime(out[key],fmt).date().isoformat(); break
                except ValueError: pass
    return out
