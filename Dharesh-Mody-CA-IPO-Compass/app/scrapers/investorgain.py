from .browser import fetch_rendered_html
from .base import parse_html_tables, rows_to_records

NAME = "InvestorGain"
URL = "https://www.investorgain.com/report/live-ipo-gmp/331/"


def fetch():
    """
    Returns (records, message). Records are normalised IPO dicts with
    gmp_amount / gmp_pct populated where available.
    """
    html = fetch_rendered_html(URL, wait_selector="table", wait_ms=5000)
    tables = parse_html_tables(html)
    records = []
    for t in tables:
        records.extend(rows_to_records(t))
    if not records:
        raise RuntimeError(
            "Page loaded but no recognisable GMP table was found — "
            "InvestorGain likely changed its layout. Use 'Import saved page' "
            "as a fallback (save the page as HTML and import it)."
        )
    return records, f"Parsed {len(records)} record(s) from {NAME}"
