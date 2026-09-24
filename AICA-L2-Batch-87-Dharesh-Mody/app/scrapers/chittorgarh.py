from .browser import fetch_rendered_html
from .base import parse_html_tables, rows_to_records

NAME = "Chittorgarh"
URL = "https://www.chittorgarh.com/report/ipo-gmp-grey-market-premium/93/"


def fetch():
    html = fetch_rendered_html(URL, wait_selector="table", wait_ms=5000)
    tables = parse_html_tables(html)
    records = []
    for t in tables:
        records.extend(rows_to_records(t))
    if not records:
        raise RuntimeError(
            "Page loaded but no recognisable GMP table was found — "
            "Chittorgarh likely changed its layout. Use 'Import saved page' "
            "as a fallback."
        )
    return records, f"Parsed {len(records)} record(s) from {NAME}"
