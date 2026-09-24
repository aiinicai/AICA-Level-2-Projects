"""
InvestorGain's live subscription report — https://www.investorgain.com/report/ipo-subscription-live/333/all/

Verified live: this table is JavaScript-rendered (the raw HTML ships with
"0 records" / "No data available" until client-side JS fills it in), the
same pattern already confirmed for Chittorgarh's and InvestorGain's own GMP
tables — so this uses the headless-browser fetch, not a plain HTTP request.

This source is intentionally marked official=False. Unlike GMP (which has a
single designated primary source), subscription figures use a *freshness*
rule in db.merge_incoming(): whichever source's number arrived most recently
wins, regardless of official/unofficial status. That's deliberate — NSE/BSE
publish the authoritative figure but may lag between refreshes, while this
report updates roughly every few minutes during bidding hours, so it can
legitimately be more current than a stale official number. A subsequent
refresh that successfully re-fetches NSE/BSE will simply overwrite it again.
"""
from .browser import fetch_rendered_html
from .base import parse_html_tables, rows_to_records

NAME = "InvestorGain Subscription"
URL = "https://www.investorgain.com/report/ipo-subscription-live/333/all/"
# The "-live" report is, by design, for IPOs currently accepting bids — once
# an issue closes it drops off this table entirely, so it can only ever
# supply a *final* subscription snapshot for the last refresh made while the
# issue was still open, never anything closer to the actual close. This
# status-filtered variant of the same report (InvestorGain's report pages
# take a status segment in the URL, as already used for the GMP report
# elsewhere) is a best-effort attempt to also capture already-closed issues'
# final subscription figures in the same refresh; if the segment name below
# doesn't match InvestorGain's actual URL scheme it simply 404s and is
# skipped, same as any other source hiccup.
CLOSED_URL = "https://www.investorgain.com/report/ipo-subscription-live/333/closed/"


def fetch():
    records = []
    html = fetch_rendered_html(URL, wait_selector="table", wait_ms=6000)
    for t in parse_html_tables(html):
        records.extend(rows_to_records(t))
    try:
        closed_html = fetch_rendered_html(CLOSED_URL, wait_selector="table", wait_ms=6000)
        closed_records = []
        for t in parse_html_tables(closed_html):
            closed_records.extend(rows_to_records(t))
        records.extend(closed_records)
    except Exception:
        pass  # best-effort only — the live/"all" report above is the primary source
    if not records:
        raise RuntimeError(
            "Page loaded but no recognisable subscription table was found — "
            "InvestorGain likely changed its layout. Use 'Import saved page' "
            "as a fallback (save the page as HTML and import it)."
        )
    return records, f"Parsed {len(records)} record(s) from {NAME}"
