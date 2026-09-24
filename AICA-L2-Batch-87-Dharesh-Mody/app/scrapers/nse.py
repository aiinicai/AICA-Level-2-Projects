"""
NSE publishes IPO data through a JSON API, but it only responds to requests
that carry cookies from a prior visit to nseindia.com plus browser-like
headers — hit it without that and you get HTTP 401/403. This does the same
two-step handshake a browser does: load the homepage to collect cookies,
then call the API with those cookies attached.

NSE tightens/loosens this periodically without notice, so treat failures as
routine and fall back to manual import — this is the flakiest source here.
"""
from .. import network as requests
from .base import number_text, price_text, normalize_status

NAME = "NSE India"
BASE = "https://www.nseindia.com"
API_URL = f"{BASE}/api/all-upcoming-issues?category=ipo"
CURRENT_URL = f"{BASE}/api/ipo-current-issue"
# Best-effort: the two endpoints above only ever carry an IPO while it is
# open or still upcoming — NSE has no documented bulk endpoint that keeps
# listing a company once bidding closes, so close_date/listing_date/final
# subscription for closed & listed IPOs previously never got an official
# refresh at all (they just froze at whatever the last "Open" snapshot
# happened to record). This candidate follows the same '/api/...-issues'
# naming pattern as the two confirmed endpoints above; it is unverified
# (no live network access when this was written), so it's tried the same
# tolerant way as CURRENT_URL/API_URL below — if it 404s or NSE renames it,
# that single attempt is logged as a partial failure and every other
# source keeps working exactly as before.
PAST_URL = f"{BASE}/api/public-past-issues"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{BASE}/market-data/all-upcoming-issues-ipo",
}


def _session():
    s = requests.Session()
    s.headers.update(HEADERS)
    s.get(BASE, timeout=15)  # picks up the nsit/nseappid cookies
    return s


def fetch():
    s = requests.Session()
    s.headers.update(HEADERS)
    try: s.get(BASE, timeout=12)
    except Exception: pass
    records, errors = [], []
    for url, kind in [(CURRENT_URL, 'Open'), (API_URL, 'Upcoming'), (PAST_URL, 'Closed')]:
        try:
            resp = s.get(url, timeout=15)
            if resp.status_code != 200: raise RuntimeError(f'HTTP {resp.status_code}')
            data = resp.json()
            rows = data if isinstance(data, list) else data.get('data', [])
            if not isinstance(rows, list): raise ValueError('Unexpected JSON schema')
            records.extend(map_rows(rows, kind))
        except Exception as e: errors.append(f'{kind}: {e}')
    if not records and errors: raise RuntimeError('; '.join(errors))
    return records, f'{len(records)} current/upcoming/past NSE rows' + ('; PARTIAL: '+'; '.join(errors) if errors else '')

def _val(row, *keys):
    """Try several candidate JSON keys — NSE's schema differs a little
    between its current/upcoming/past endpoints (and the past-issues one
    is unverified), so this avoids hard-coding a single key name."""
    for k in keys:
        v = row.get(k)
        if v not in (None, ''):
            return v
    return None

def map_rows(rows, kind):
    records = []
    for row in rows:
        name = _val(row, "companyName", "issuerName") or row.get("symbol")
        if not name:
            continue
        low, high = price_text(_val(row, 'issuePrice', 'finalIssuePrice', 'offerPrice'))
        records.append({
            "name": name,
            "symbol": row.get("symbol"),
            "exchange": "NSE",
            "board": "SME" if "sme" in str(row.get("series", "")).lower() else "Mainboard",
            "status": normalize_status(_val(row, "status", "issueStatus") or kind),
            "open_date": _val(row, "issueStartDate", "startDate"),
            "close_date": _val(row, "issueEndDate", "endDate"),
            # Never previously mapped by any scraper in this app — see the
            # comment on the "listing_date" alias in scrapers/base.py; this
            # is what lets a company move into the "Listed" status bucket
            # from an automatic refresh instead of staying stuck as
            # "Closed" forever once bidding ends.
            "listing_date": _val(row, "listingDate", "dateOfListing", "listing_date"),
            "price_low": number_text(row.get("issuePriceLower")) if row.get('issuePriceLower') is not None else low,
            "price_high": number_text(row.get("issuePriceUpper")) if row.get('issuePriceUpper') is not None else high,
            "sub_total": number_text(_val(row, 'noOfTime', 'overallSubscription', 'totalSubscription')),
        })
    return records
