"""
Import a GMP web page that the user saved from their own browser.

This is the fallback that works whatever the reason a live fetch fails
(site blocks scripted requests, table filled by JavaScript, headless browser
not installed, layout changed): the user opens the site normally, saves the
page ("Webpage, Complete" keeps the rendered table), and imports the file. The
site is recognised from the page itself, its rows go through exactly the same
name matching, merge and per-source GMP diagnostics as a live refresh.
"""
import re
from urllib.parse import urlsplit

from . import db
from .scrapers import REGISTRY, SOURCE_URLS, GMP_DIAGNOSTIC_SOURCES, GMP_REDIRECTS
from .scrapers.base import parse_html_tables, rows_to_records


def _domain(url):
    return urlsplit(url).netloc.lower().removeprefix('www.')


def detect_source(filename, text):
    """Which GMP website a saved page came from (registry key), or None."""
    head = ((filename or '') + ' ' + (text or '')[:300000]).lower()
    best, best_score = None, 0
    for key in GMP_DIAGNOSTIC_SOURCES:
        domain = _domain(SOURCE_URLS[key])
        score = head.count(domain)
        # The page's own address (canonical / og:url / saved-from comment) is the strongest evidence.
        if re.search(r'(?:canonical|og:url|saved from url)[^>]{0,200}' + re.escape(domain), head):
            score += 1000
        if score > best_score:
            best, best_score = key, score
    return best


def records_from_html(key, text):
    module = REGISTRY[key][0]
    if hasattr(module, 'parse_page'):
        return module.parse_page(text)
    return [r for t in parse_html_tables(text) for r in rows_to_records(t)]


def import_saved_page(filename, text):
    """Import one saved GMP page. Returns a human-readable summary; raises ValueError with the reason otherwise."""
    key = detect_source(filename, text)
    if key is None:
        raise ValueError('Could not tell which GMP website this page came from. Save the page from '
                         'IPOWatch, IPOJI, InvestorGain, IPO Index, IPO Markets, IPO Premium or Chittorgarh '
                         'using "Webpage, Complete" and try again.')
    _, name, official, _ = REGISTRY[key]
    records = records_from_html(key, text)
    if not records:
        raise ValueError(f'Recognised the page as {name}, but found no GMP table or quotes in it. '
                         'Save the page while the table is visible, using "Webpage, Complete".')
    saved = 0
    for rec in records:
        try:
            # Same rule as a live refresh: never create a brand-new IPO from a row with no dates.
            if not db.find_by_name(rec.get('name', '')) and not rec.get('open_date') and not rec.get('close_date'):
                continue
            db.merge_incoming(rec, key, name, SOURCE_URLS[key], 'Saved page import', official)
            saved += 1
        except Exception:
            continue
    db.sync_gmp_quotes(key, name, SOURCE_URLS[key], records, redirect_note=GMP_REDIRECTS.get(key))
    db.log_refresh(name, True, f'Saved page imported: {len(records)} row(s) read', saved)
    tracked = db.all_ipos()
    matched = sum(1 for ipo in tracked for q in db.gmp_quotes_for(ipo['id'])
                  if q['source_key'] == key and q['fetch_status'] == 'available')
    if key in GMP_REDIRECTS:
        return f'{name}: read {len(records)} row(s). This site is shown as a directory redirect, not counted as a separate quote.'
    return f'{name}: read {len(records)} row(s); a GMP quote was matched to {matched} of your {len(tracked)} tracked IPO(s).'
