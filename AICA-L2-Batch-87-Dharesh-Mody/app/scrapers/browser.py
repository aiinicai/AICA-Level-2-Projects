"""
Headless-browser fetch for sites that render their IPO/GMP tables with
JavaScript after the page loads (confirmed for InvestorGain; Chittorgarh's
and IPOJI's React-based report pages behave the same way). Plain `requests`
only ever sees the pre-render skeleton ("Loading…", "0 records"), so this
uses Playwright's bundled Chromium instead.

Needs a one-time `python -m playwright install chromium` after pip install
(see README) — the browser binary is what lets this work with no server.

PERFORMANCE NOTE: launching a fresh Chromium process is the slowest part of
a refresh (each cold start can take several seconds). A full refresh calls
this function up to three times in a row (Chittorgarh, IPOJI, InvestorGain),
so instead of "launch -> use -> close" every single call, one Chromium
process is started lazily on first use and kept alive (just opening/closing
a cheap browser *tab* per call) for the lifetime of the app process. It's
closed automatically on exit via `atexit`. If the shared browser ever
crashes or disconnects, the next call transparently relaunches it once.
"""
import atexit
import threading

_lock = threading.Lock()
_playwright = None
_browser = None


def _launch():
    from playwright.sync_api import sync_playwright
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    return playwright, browser


def _get_browser():
    global _playwright, _browser
    with _lock:
        if _browser is None or not _browser.is_connected():
            _close_browser()  # clean up any half-dead handle first
            _playwright, _browser = _launch()
            atexit.register(_close_browser)
        return _browser


def _close_browser():
    global _playwright, _browser
    try:
        if _browser: _browser.close()
    except Exception: pass
    try:
        if _playwright: _playwright.stop()
    except Exception: pass
    _playwright, _browser = None, None


def browser_unavailable_reason():
    """None when headless-browser rendering can be used, else a plain-English reason."""
    import os
    if os.environ.get('IPO_COMPASS_BROWSER') != '1':
        return ('browser rendering is not enabled on this PC (Playwright is not installed, '
                'or the app was started without it)')
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401 - import check only
    except ImportError:
        return 'the Playwright package is not installed'
    return None


INSTALL_HINT = ('To enable it: pip install playwright, then python -m playwright install chromium, '
                'then close and restart START_IPO_COMPASS.cmd. Alternatively open the site in your '
                'browser, save the page (Ctrl+S, "Webpage, Complete") and use Data & sources > '
                'Import saved GMP page.')


def fetch_rendered_html(url, wait_selector=None, wait_ms=4000, timeout_ms=25000):
    """
    Returns the page HTML: from a plain HTTP request when that already carries
    real data, otherwise from the headless browser. Raises RuntimeError whose
    message states exactly what came back, so the GMP tab / Data & sources page
    can show the true reason instead of a bare "Unavailable".
    """
    from ..network import get_page
    from .base import parse_html_tables, rows_to_records, describe_page
    response = get_page(url, timeout=15)
    records = []
    if response.status_code == 200:
        records = [r for t in parse_html_tables(response.text) for r in rows_to_records(t)]
        # Any of the several distinct fields these pages carry counts as
        # evidence the page wasn't just the pre-render skeleton.
        signal_fields = ('gmp_amount', 'gmp_pct', 'sub_total', 'sub_qib',
                          'sub_nii', 'sub_retail', 'price_low', 'price_high')
        if any(r.get(f) is not None for r in records for f in signal_fields):
            return response.text
    seen = f'The plain page request returned {describe_page(response.status_code, response.text)}'
    if records:
        seen += ' but none of them held GMP/price/subscription figures'
    reason = browser_unavailable_reason()
    if reason:
        raise RuntimeError(f'{seen}. That means the site either fills its table with JavaScript or '
                           f'refused the request, and {reason}. {INSTALL_HINT}')
    return render_page(url, wait_selector, wait_ms, timeout_ms)


def render_page(url, wait_selector=None, wait_ms=4000, timeout_ms=25000):
    """Load `url` in the shared headless Chromium and return the rendered HTML."""
    for attempt in (1, 2):  # one retry in case the shared browser had just crashed
        try:
            browser = _get_browser()
            context = browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0 Safari/537.36")
            )
            try:
                page = context.new_page()
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=timeout_ms)
                    except Exception:
                        pass  # fall through and grab whatever rendered
                page.wait_for_timeout(wait_ms)
                return page.content()
            finally:
                context.close()  # closes the tab; the shared browser process stays up
        except RuntimeError:
            raise
        except Exception as e:
            if attempt == 2:
                if 'executable doesn' in str(e).lower() or 'browsertype.launch' in str(e).lower():
                    raise RuntimeError(
                        f"Headless browser fetch failed for {url}: Playwright's Chromium "
                        "browser binary isn't downloaded yet (the pip package alone isn't "
                        "enough). Run: python -m playwright install chromium"
                    ) from e
                raise RuntimeError(f"Headless browser fetch failed for {url}: {e}") from e
            _close_browser()  # force a clean relaunch and try once more
