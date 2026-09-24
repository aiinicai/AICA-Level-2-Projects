"""
"IPO Markets" GMP scraper — secondary GMP source for the diagnostics table.
See the module docstring in scrapers/ipo_index.py: this project's build
environment had no live network access to confirm this source's actual
domain, so the URL below is a best-effort placeholder that degrades to an
honest "Unavailable" status in the GMP tab rather than failing the refresh.
Update URL below once the correct address is confirmed.
"""
from .. import network
from .browser import fetch_rendered_html
from .base import parse_html_tables, rows_to_records

NAME = "IPO Markets"
URL = "https://ipomarkets.in/ipo-gmp"  # TODO: confirm actual URL


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
            "IPO Markets's current URL and table layout, or use 'Import "
            "saved page' as a fallback."
        )
    return records, f"Parsed {len(records)} record(s) from {NAME}"
