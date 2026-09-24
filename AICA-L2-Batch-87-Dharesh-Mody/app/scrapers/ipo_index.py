"""
"IPO Index" GMP scraper — one of the secondary sources listed in the per-IPO
GMP diagnostics table (see the module docstring in scrapers/ipowatch.py for
how these secondary sources are used; the same applies here).

IMPORTANT — unverified URL: unlike ipowatch.py/ipoji.py/chittorgarh.py/
investorgain.py, this project's build environment had no live network
access to confirm "IPO Index"'s actual domain and table layout. The URL
below is a best-effort placeholder. That is fine by design: if it 404s or
the layout doesn't match, fetch() raises, refresh.py catches it and calls
db.sync_gmp_quotes_failed(), and the GMP tab honestly shows this source as
"Unavailable" for every IPO rather than crashing the refresh or silently
fabricating data. Update URL below once the correct address is confirmed.
"""
from .. import network
from .browser import fetch_rendered_html
from .base import parse_html_tables, rows_to_records

NAME = "IPO Index"
URL = "https://ipoindex.in/ipo-gmp"  # TODO: confirm actual URL


def fetch():
    records = []
    try:
        response = network.get(URL, timeout=15)
        if response.status_code == 200:
            for t in parse_html_tables(response.text):
                records.extend(rows_to_records(t))
    except Exception:
        records = []
    if not records:
        html = fetch_rendered_html(URL, wait_selector="table", wait_ms=5000)
        for t in parse_html_tables(html):
            records.extend(rows_to_records(t))
    if not records:
        raise RuntimeError(
            "Page loaded but no recognisable GMP table was found — confirm "
            "IPO Index's current URL and table layout, or use 'Import saved "
            "page' as a fallback."
        )
    return records, f"Parsed {len(records)} record(s) from {NAME}"
