"""
probe_list.py — find the right selectors for the CHAT LIST sidebar.
Read-only. Clicks nothing except the filter buttons.

    python probe_list.py
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
PROFILE_DIR = HERE / "wa-profile"

CANDIDATES = [
    '#pane-side [role="listitem"]',
    '#pane-side div[role="row"]',
    '#pane-side [role="gridcell"]',
    '#pane-side [data-testid="cell-frame-container"]',
    '#pane-side span[title]',
    '#pane-side [role="listitem"] span[title]',
    '[aria-label="Chat list"] [role="listitem"]',
    '[data-testid="chat-list"] [role="listitem"]',
    '#pane-side div[data-id]',
]

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        channel="msedge",
        headless=False,
        viewport={"width": 1350, "height": 880},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

    print("waiting for chat list...")
    for _ in range(90):
        if page.locator("#pane-side").count() > 0:
            break
        time.sleep(2)
    time.sleep(4)
    print("loaded.\n")

    print("--- #pane-side exists:", page.locator("#pane-side").count(), "\n")

    print("--- candidate selectors ---")
    for sel in CANDIDATES:
        try:
            n = page.locator(sel).count()
        except Exception as e:
            n = f"err {e}"
        print(f"  {str(n):>6}   {sel}")

    print("\n--- first 15 titles via #pane-side span[title] ---")
    for s in page.locator("#pane-side span[title]").all()[:15]:
        try:
            print("   -", s.get_attribute("title"))
        except Exception:
            pass

    print("\n--- buttons in the header area above the list ---")
    for b in page.locator("header button, #side button, [role='tablist'] button").all()[:25]:
        try:
            lbl = b.get_attribute("aria-label") or b.inner_text()
            lbl = (lbl or "").strip().replace("\n", " ")
            if lbl:
                print(f"   - {lbl[:45]}")
        except Exception:
            pass

    print("\n--- elements whose text is exactly 'Groups' ---")
    g = page.get_by_text("Groups", exact=True)
    print("   count:", g.count())
    for i in range(min(g.count(), 5)):
        try:
            el = g.nth(i)
            print(f"   [{i}] role={el.get_attribute('role')} "
                  f"aria-label={el.get_attribute('aria-label')} "
                  f"testid={el.get_attribute('data-testid')}")
        except Exception:
            pass

    print("\nWindow stays open 60s.")
    time.sleep(60)
    ctx.close()
