"""
IPOWatch.in GMP (grey market premium) scraper.

This is one of several non-primary GMP sources checked purely for the
per-IPO "GMP" tab's source-by-source diagnostics table (see
db.sync_gmp_quotes() and REGISTRY/GMP_DIAGNOSTIC_SOURCES in
scrapers/__init__.py). It never feeds the single merged gmp_amount used
elsewhere in the app (Chittorgarh remains primary for that, with IPOJI then
InvestorGain as fallbacks) — it only records its own reading against each
IPO so the diagnostics tab can show where sources agree or disagree, and
show "No quote published" rather than silence when this source simply
doesn't mention a given company.
"""
from .browser import fetch_rendered_html
from .base import parse_html_tables, rows_to_records

NAME = "IPOWatch"
URL = "https://ipowatch.in/ipo-grey-market-premium/"


def fetch():
    html = fetch_rendered_html(URL, wait_selector="table", wait_ms=5000)
    records = []
    for t in parse_html_tables(html):
        records.extend(rows_to_records(t))
    if not records:
        raise RuntimeError(
            "Page loaded but no recognisable GMP table was found — "
            "IPOWatch likely changed its layout. Use 'Import saved page' "
            "as a fallback (save the page as HTML and import it)."
        )
    return records, f"Parsed {len(records)} record(s) from {NAME}"
