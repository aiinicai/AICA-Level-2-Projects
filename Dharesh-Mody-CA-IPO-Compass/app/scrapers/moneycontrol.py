from .. import network as requests
from .base import parse_html_tables, rows_to_records

NAME = "Moneycontrol"
URL = "https://www.moneycontrol.com/ipo/"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
}


def fetch():
    resp = requests.get(URL, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"Moneycontrol returned HTTP {resp.status_code}.")
    tables = parse_html_tables(resp.text)
    records = []
    for t in tables:
        records.extend(rows_to_records(t))
    if not records:
        raise RuntimeError(
            "Moneycontrol's IPO page did not yield a parseable table (it may "
            "require JavaScript rendering now). Use 'Import saved page'."
        )
    return records, f"Parsed {len(records)} record(s) from {NAME}"
