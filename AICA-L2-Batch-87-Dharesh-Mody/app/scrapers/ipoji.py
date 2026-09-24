"""
IPOJI.com GMP (grey market premium) scraper.

Used as the designated *fallback* GMP source: `merge_incoming()` in app/db.py
only lets this source's gmp_amount/gmp_pct overwrite a record when the most
recent Chittorgarh refresh attempt did not succeed (see `source_ok_recently`
in app/db.py) - so on a normal day Chittorgarh stays authoritative for GMP,
and IPOJI only steps in when Chittorgarh is down, blocked, or changed layout.
It also feeds its own row in each IPO's "GMP" tab.

The page https://www.ipoji.com/ipo-gmp lists every tracked IPO in a table:

    IPO | Type | Price Band (Rs) | GMP (Rs) | GMP % | Indicative Listing (Rs) |
    Open - Close | Status | Last Updated

and links each company as  /ipo/<slug>  and each quote as  /ipo-gmp/<slug>.

Three strategies are tried in turn, and whichever fails is reported by name
(with the HTTP status, size and number of tables/links actually received) so a
failure is never just "Unavailable":

  1. plain HTTP request with browser-like headers -> parse the <table>;
  2. same HTML -> layout-independent parse of the /ipo-gmp/<slug> links, which
     keeps working if the site changes its table markup;
  3. headless browser render (only when Playwright is installed) -> both
     parsers again, for the case the plain page arrives without any data.
"""
import re
from html import unescape

from .. import network
from .base import parse_html_tables, rows_to_records, number_text, describe_page
from . import browser

NAME = "IPOJI"
URL = "https://www.ipoji.com/ipo-gmp"


def _text(fragment):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", fragment or ""))).strip()


def parse_links(html_text):
    """
    Layout-independent parse. Every quote on the page is an <a> to
    /ipo-gmp/<slug> whose text is like "+Rs135 (+32%)", and every company is an
    <a> to /ipo/<slug>. Joining the two on <slug> does not depend on whether
    the page uses a <table>, <div> rows, or a mobile card layout.
    """
    names, quotes = {}, {}
    for m in re.finditer(r'<a\b[^>]*?href=["\'][^"\']*?/ipo/([a-z0-9][a-z0-9\-]*)["\'][^>]*>(.*?)</a>',
                         html_text or "", re.I | re.S):
        names.setdefault(m.group(1).lower(), _text(m.group(2)))
    for m in re.finditer(r'<a\b[^>]*?href=["\'][^"\']*?/ipo-gmp/([a-z0-9][a-z0-9\-]*)["\'][^>]*>(.*?)</a>',
                         html_text or "", re.I | re.S):
        quotes.setdefault(m.group(1).lower(), _text(m.group(2)))
    records = []
    for slug, text in quotes.items():
        amount = number_text(text)
        if amount is None:
            continue
        pct = re.search(r"\(\s*([+\-\u2212\u2013]?\s*\d+(?:\.\d+)?)\s*%\s*\)", text)
        name = names.get(slug) or re.sub(r"-ipo$", "", slug).replace("-", " ").title()
        rec = {"name": name, "gmp_amount": amount}
        if pct:
            rec["gmp_pct"] = number_text(pct.group(1))
        records.append(rec)
    return records


def parse_page(html_text):
    """Records from IPOJI page HTML: the table when it holds GMP figures, else the quote links."""
    records = [r for t in parse_html_tables(html_text) for r in rows_to_records(t)]
    if any(r.get("gmp_amount") is not None for r in records):
        return records
    linked = parse_links(html_text)
    # A table with no GMP figure in it is not the GMP table (or the quotes are
    # rendered outside it): recover them from the links and keep any table rows.
    return _merge_link_quotes(records, linked) if linked else records


def _merge_link_quotes(records, linked):
    """Add the link-parsed quotes to table rows (matching on company name)."""
    from .. import names
    out = list(records)
    for quote in linked:
        row = next((r for r in out if names.names_match(r["name"], quote["name"])), None)
        if row is None:
            out.append(quote)
        elif row.get("gmp_amount") is None:
            row.update({k: v for k, v in quote.items() if k != "name"})
    return out


def fetch():
    plain = "plain request not attempted"
    try:
        response = network.get_page(URL, timeout=20)
        plain = describe_page(response.status_code, response.text)
        plain += f", {len(parse_links(response.text))} GMP link(s)"
        if response.status_code == 200:
            records = parse_page(response.text)
            if records:
                return records, f"Parsed {len(records)} record(s) from {NAME}"
    except Exception as e:  # network error, timeout, TLS error, size limit...
        plain = f"plain request failed: {type(e).__name__}: {e}"
    reason = browser.browser_unavailable_reason()
    if reason:
        raise RuntimeError(
            f"{NAME} page could not be read. Plain request: {plain}. "
            f"Browser rendering: not used because {reason}. {browser.INSTALL_HINT}")
    try:
        records = parse_page(browser.render_page(URL, wait_selector="table", wait_ms=5000))
    except Exception as e:
        raise RuntimeError(f"{NAME} page could not be read. Plain request: {plain}. "
                           f"Browser rendering failed: {e}") from e
    if not records:
        raise RuntimeError(f"{NAME} page loaded in the browser but no GMP table or quote links were "
                           f"found - the site layout has probably changed. Plain request: {plain}.")
    return records, f"Parsed {len(records)} record(s) from {NAME} (browser-rendered)"
