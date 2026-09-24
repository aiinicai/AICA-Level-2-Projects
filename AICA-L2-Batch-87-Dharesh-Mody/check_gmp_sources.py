"""
Live check of the IPOJI GMP page, run from THIS PC (double-click CHECK_GMP_SOURCES.cmd).

Answers "why does IPOJI show Unavailable?" with facts instead of guesses:
what the site actually returned to this app, whether the table/quotes were in
it, what the app's parser made of it, and whether the company you name below
would be matched to one of your tracked IPOs.

Usage:  python check_gmp_sources.py ["SS Retail"]
"""
import os
import re
import sys
import platform
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'vendor'))
company = sys.argv[1] if len(sys.argv) > 1 else 'SS Retail'

print('CA IPO Compass - IPOJI GMP check')
print('Python:', sys.version.split()[0], '|', platform.platform())

from app import network, names
from app.scrapers import ipoji, browser
from app.scrapers.base import parse_html_tables

reason = browser.browser_unavailable_reason()
print('\n[1] Headless browser (needed only if the plain page has no data):')
print('    ', 'AVAILABLE' if reason is None else 'NOT AVAILABLE - ' + reason)

print('\n[2] Plain request to', ipoji.URL)
verdict = None
text = ''
try:
    response = network.get_page(ipoji.URL, timeout=25)
    text = response.text
    print('     HTTP status   :', response.status_code)
    print('     Content-Type  :', response.headers.get('Content-Type'))
    print('     Size          :', f'{len(response.content) / 1024:.0f} KB')
    tables = parse_html_tables(text)
    links = ipoji.parse_links(text)
    print('     Tables w/ data:', len(tables))
    if tables:
        print('     Table header  :', tables[0][0])
    print('     GMP links     :', len(links))
    low = text.lower()
    if response.status_code in (401, 403, 429) or any(k in low for k in ('just a moment', 'cf-chl', 'captcha', 'access denied')):
        verdict = ('The site REFUSED / CHALLENGED this app\'s request (bot protection). '
                   'Use "Import saved GMP page" on the Data & sources page, or enable the headless browser.')
    elif response.status_code != 200:
        verdict = f'The site answered HTTP {response.status_code}, not the page.'
except Exception as e:
    print('     REQUEST FAILED:', type(e).__name__, e)
    verdict = ('The request never completed (no internet, DNS, firewall/antivirus, proxy or TLS problem on this PC). '
               'Check that the site opens in your browser and that Python is allowed through your firewall.')

records = []
if text and verdict is None:
    records = ipoji.parse_page(text)
    with_gmp = [r for r in records if r.get('gmp_amount') is not None]
    print('\n[3] What the app\'s parser read')
    print('     Rows read     :', len(records), '| rows with a GMP:', len(with_gmp))
    for r in with_gmp[:4]:
        print('       ', r.get('name'), '->', r.get('gmp_amount'), f"({r.get('gmp_pct')}%)")
    if not records:
        verdict = ('The plain page carries NO table and NO GMP links: IPOJI fills the table with JavaScript. '
                   'Enable the headless browser (see below) or use "Import saved GMP page".')
        snippet = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text))[:300]
        print('     Page text starts:', snippet)

if records:
    print('\n[4] Would "' + company + '" be found?')
    hits = [r for r in records if company.lower() in str(r.get('name', '')).lower()]
    for r in hits:
        print('     IPOJI row  :', repr(r.get('name')), '| GMP', r.get('gmp_amount'))
    if not hits:
        print('     No IPOJI row contains that text.')
    try:
        from app import db
        tracked = db.all_ipos()
        print('     Tracked IPOs in your database:', len(tracked))
        for r in hits:
            m = [(names.match_score(t['name'], r['name'], True), t['name']) for t in tracked]
            m = [x for x in m if x[0]]
            print('     Matches tracked IPO:', sorted(m, reverse=True)[:2] or 'NONE (name not recognised as any tracked IPO)')
    except Exception as e:
        print('     (Could not read your IPO database:', e, ')')
    verdict = verdict or 'IPOJI is readable from this PC. If the app still shows Unavailable, run "Refresh & analyse all" and check Data & sources > Recent source responses.'

print('\nRESULT:', verdict or 'No conclusion - send this whole output.')
print('\nTo enable the headless browser: pip install playwright  then  python -m playwright install chromium  then restart the app.')
