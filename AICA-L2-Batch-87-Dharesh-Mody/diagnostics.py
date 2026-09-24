import sys
import platform
import sqlite3
from pathlib import Path

print('CA IPO Compass - setup diagnostic')
print('Python:',sys.version)
print('Windows / OS:',platform.platform())
print('Architecture:',platform.machine())
print('SQLite:',sqlite3.sqlite_version)
print('Project files:', all((Path(__file__).parent/p).exists() for p in ('main.py','app/db.py','app/webapp.py','app/ui/web/index.html','app/ui/web/app.js','app/ui/web/style.css')))
try:
    sys.path.insert(0,str(Path(__file__).parent/'vendor'))
    import pypdf
    import socket
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.close()
    print('Local dashboard connection: OK')
    print('Bundled PDF reader:',pypdf.__version__)
except Exception as e:
    print('Diagnostic failed:',type(e).__name__,str(e))
    print('Extract the entire ZIP to a writable folder and retry.')

# GMP and live-subscription figures come from JavaScript-rendered pages
# (Chittorgarh, IPOJI, InvestorGain), which need Playwright's headless
# Chromium to read. Without it, those sources fall back to "Research
# needed" instead of live numbers — which is the single most common
# reason someone sees GMP or subscription data that never updates.
try:
    import playwright  # noqa: F401
    print('Playwright package: installed')
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        print('Playwright Chromium browser: OK — live GMP/subscription rendering is available')
    except Exception as e:
        print('Playwright Chromium browser: NOT usable —', type(e).__name__, str(e))
        print('  Fix: run  python -m playwright install chromium')
except ImportError:
    print('Playwright package: not installed (optional)')
    print('  This is the default build; GMP/subscription will show "Research needed" until you')
    print('  run:  pip install playwright && python -m playwright install chromium')
print('No websites were contacted by this diagnostic.')
