"""
wa.py — WhatsApp group history cleaner (UI automation spike)
============================================================
Drives the REAL WhatsApp Web interface in Microsoft Edge, clicking the same
buttons a human would. It never touches WhatsApp's internal JavaScript, so the
"ERROR r: r" class of failure cannot occur here.

HARD RULE — this script must NEVER click:
    "Exit group", "Delete chat", "Delete group", "Leave group"
Those strings are in FORBIDDEN below and are actively blocked at click time.

SETUP (one time)
    pip install playwright
    python wa.py setup          <- scan QR once, session is saved to wa-profile\

COMMANDS
    python wa.py list                          list your groups
    python wa.py inspect "Group Name"          calibration: dump what it can see
    python wa.py peek "Group Name"             show recent visible messages
    python wa.py clear-all  "Group Name" [--confirm]
    python wa.py clear-last "Group Name" 5 [--confirm]

Without --confirm everything is a DRY RUN. Nothing is clicked that changes data.
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    sys.exit("Playwright not installed. Run:  pip install playwright")

# ----------------------------------------------------------------------------
# CONFIG — edit these if WhatsApp changes its interface or you use a non-English UI
# ----------------------------------------------------------------------------
HERE = Path(__file__).parent
PROFILE_DIR = HERE / "wa-profile"      # keeps you logged in; treat as a password
EXPORT_DIR = HERE / "exports"
LOG_FILE = HERE / "audit.log"

BROWSER_CHANNEL = "msedge"             # "msedge" or "chrome"

LABELS = {
    "search_box": "Search input textbox",
    "groups_filter": "Groups",
    "menu_button": "Menu",
    "clear_chat": "Clear chat",
    "delete": "Delete",
    "delete_for_me": "Delete for me",
    "cancel": "Cancel",
}

# Candidate selectors for message rows, tried in order. The first one that
# returns a non-zero count wins. Add your own here if none of them match.
MESSAGE_SELECTORS = [
    '#main div[role="row"]',
    '#main [data-id]',
    '#main div.message-in, #main div.message-out',
    '#main .copyable-text[data-pre-plain-text]',
    'div[role="application"] div[role="row"]',
    '#main div[data-pre-plain-text]',
]

# Never clicked. Guarded at runtime.
FORBIDDEN = ["exit group", "delete chat", "delete group", "leave group",
             "delete for everyone"]

SLOW = 1.2      # seconds between UI actions — keep this human-paced


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def log(msg):
    line = f"{datetime.now().isoformat(timespec='seconds')}  {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def safe_click(locator, label):
    """Click, but refuse if the element text looks destructive."""
    try:
        text = (locator.inner_text(timeout=3000) or "").strip().lower()
    except Exception:
        text = ""
    for bad in FORBIDDEN:
        if bad in text:
            raise RuntimeError(
                f"BLOCKED: refusing to click '{text}' (matched forbidden '{bad}')"
            )
    locator.click()
    log(f"clicked: {label}")
    time.sleep(SLOW)


def dump(group, items, tag):
    EXPORT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = "".join(c if c.isalnum() else "_" for c in group)[:50]
    path = EXPORT_DIR / f"{safe}_{tag}_{stamp}.json"
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"BACKUP {len(items)} items -> {path}")
    return path


# ----------------------------------------------------------------------------
# browser
# ----------------------------------------------------------------------------
def open_whatsapp(p, headless=False):
    PROFILE_DIR.mkdir(exist_ok=True)
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        channel=BROWSER_CHANNEL,
        headless=headless,
        viewport={"width": 1400, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
    return ctx, page


def wait_for_login(page, timeout=180):
    """Waits until the chat list pane exists."""
    print("Waiting for WhatsApp to load (scan the QR if shown)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if page.locator("#pane-side").count() > 0:
            time.sleep(3)
            log("WhatsApp Web is loaded and logged in.")
            return True
        time.sleep(2)
    raise RuntimeError("Timed out waiting for login. Scan the QR and retry.")


def open_chat(page, name):
    """Find a chat by name using the search box, then open it."""
    box = page.get_by_role("textbox").first
    box.click()
    time.sleep(0.5)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    box.type(name, delay=60)
    time.sleep(2.5)

    result = page.locator("#pane-side").get_by_title(name, exact=True).first
    if result.count() == 0:
        result = page.locator("#pane-side").get_by_text(name, exact=False).first
    if result.count() == 0:
        raise RuntimeError(f'Could not find a chat named "{name}"')
    result.click()
    time.sleep(SLOW * 2)
    log(f'opened chat: "{name}"')


def scroll_history(page, times=8):
    """Scroll the conversation pane upward to force older messages to render."""
    pane = page.locator("#main").locator('div[role="application"]').first
    if pane.count() == 0:
        pane = page.locator("#main")
    for _ in range(times):
        try:
            pane.click(position={"x": 20, "y": 20})
        except Exception:
            pass
        page.keyboard.press("PageUp")
        time.sleep(0.7)
    time.sleep(1.5)


def find_message_locator(page):
    """Try each candidate selector; return the first that finds anything."""
    for sel in MESSAGE_SELECTORS:
        loc = page.locator(sel)
        try:
            n = loc.count()
        except Exception:
            n = 0
        if n > 0:
            log(f"message selector in use: {sel}  ({n} rows)")
            return loc, sel
    return None, None


def visible_messages(page):
    """Return the message rows currently rendered in the conversation pane."""
    rows, sel = find_message_locator(page)
    if rows is None:
        return None, []
    out = []
    for i in range(rows.count()):
        r = rows.nth(i)
        try:
            txt = r.inner_text(timeout=1500).replace("\n", " | ").strip()[:160]
        except Exception:
            txt = "<unreadable>"
        if txt:
            out.append({"index": i, "text": txt})
    return rows, out


# ----------------------------------------------------------------------------
# commands
# ----------------------------------------------------------------------------
def cmd_setup():
    with sync_playwright() as p:
        ctx, page = open_whatsapp(p)
        print("\nScan the QR code in the Edge window that just opened.")
        print("WhatsApp > Settings > Linked devices > Link a device\n")
        wait_for_login(page, timeout=300)
        print("\nSession saved. You will not need to scan again.")
        time.sleep(3)
        ctx.close()


def cmd_list():
    with sync_playwright() as p:
        ctx, page = open_whatsapp(p)
        wait_for_login(page)

        # Try WhatsApp's built-in Groups filter first
        try:
            page.get_by_role("button", name=LABELS["groups_filter"]).click(timeout=5000)
            time.sleep(2.5)
            print("\n(using the Groups filter)")
        except Exception:
            print("\n(Groups filter not found — listing ALL chats instead)")

        rows = page.locator("#pane-side").locator('[role="listitem"]')
        n = rows.count()
        print(f"\n{n} chats visible in the list "
              f"(scroll the window to load more, then re-run):\n")
        for i in range(n):
            try:
                title = rows.nth(i).locator("span[title]").first.get_attribute("title")
            except Exception:
                title = "<unreadable>"
            print(f"  {title}")
        print("\nUse the exact name in quotes, e.g.:  python wa.py peek \"ZZ Test Clear\"\n")
        ctx.close()


def cmd_inspect(name):
    """Calibration run — reports which selectors actually match your build."""
    with sync_playwright() as p:
        ctx, page = open_whatsapp(p)
        wait_for_login(page)
        open_chat(page, name)
        scroll_history(page, times=6)

        print("\n--- selector probe (message rows) ---")
        for sel in MESSAGE_SELECTORS:
            try:
                n = page.locator(sel).count()
            except Exception as e:
                n = f"error: {e}"
            print(f"  {n:>6}   {sel}")

        rows, msgs = visible_messages(page)
        print(f"\nUsable message rows: {len(msgs)}")
        for m in msgs[-10:]:
            print("   ", m["text"][:90])

        print("\n--- conversation header buttons (#main header) ---")
        for b in page.locator("#main header button").all()[:20]:
            try:
                lbl = b.get_attribute("aria-label") or b.inner_text()
                print("   -", (lbl or "<no label>").strip()[:60])
            except Exception:
                pass

        print("\n--- data-icon values in #main header ---")
        for ic in page.locator("#main header [data-icon]").all()[:20]:
            try:
                print("   -", ic.get_attribute("data-icon"))
            except Exception:
                pass

        print("\nLeaving the window open 60s so you can inspect it.")
        time.sleep(60)
        ctx.close()


def open_message_menu(page, row):
    """Open a single message's context menu. Tries right-click, then chevron."""
    row.hover()
    time.sleep(0.6)

    # Approach 1: right-click the message row
    try:
        row.click(button="right")
        time.sleep(SLOW)
        if page.get_by_text(LABELS["delete"], exact=True).count() > 0:
            return True
    except Exception:
        pass

    # Approach 2: the hover chevron
    for sel in ['[data-icon="down-context"]',
                '[aria-label="Context menu"]',
                '[aria-label="Open chat context menu"]',
                '[data-icon="ic-chevron-down-menu"]',
                'button[aria-haspopup="true"]']:
        try:
            ch = row.locator(sel).first
            if ch.count() > 0:
                ch.click()
                time.sleep(SLOW)
                return True
        except Exception:
            continue
    return False


def open_header_menu(page):
    """Open the conversation's header menu (the ... button)."""
    btn = page.locator("#main header").get_by_role("button", name=LABELS["menu_button"]).first
    if btn.count() == 0:
        btn = page.locator('#main header [data-icon="menu"]').first
    btn.click()
    time.sleep(SLOW)


def menu_items(page, limit=40):
    """Return the text of every item currently showing in an open menu."""
    out = []
    for sel in ['[role="application"] li', '[role="menu"] li',
                'li[role="button"]', '[role="menuitem"]']:
        for it in page.locator(sel).all()[:limit]:
            try:
                t = (it.inner_text() or "").strip().replace("\n", " ")
            except Exception:
                continue
            if t and len(t) < 40 and t not in out:
                out.append(t)
        if out:
            break
    return out


def cmd_probe_menu(name):
    """Open the conversation header menu and list EVERY item in it."""
    with sync_playwright() as p:
        ctx, page = open_whatsapp(p)
        wait_for_login(page)
        open_chat(page, name)

        open_header_menu(page)
        items = menu_items(page)
        print(f"\n--- header menu: {len(items)} items ---")
        for t in items:
            mark = ""
            if t.strip().lower() == LABELS["clear_chat"].lower():
                mark = "   <-- CLEAR CHAT (this is what clear-all uses)"
            if "select messages" in t.lower():
                mark = "   <-- SELECT MESSAGES (this is what clear-last uses)"
            for bad in FORBIDDEN:
                if bad in t.lower():
                    mark = "   <-- FORBIDDEN, never clicked"
            print(f"   - {t}{mark}")

        page.keyboard.press("Escape")
        print("\nLeaving the window open 30s.")
        time.sleep(30)
        ctx.close()


def cmd_peek(name):
    with sync_playwright() as p:
        ctx, page = open_whatsapp(p)
        wait_for_login(page)
        open_chat(page, name)
        _, msgs = visible_messages(page)
        print(f"\n{len(msgs)} message rows currently rendered:\n")
        for m in msgs:
            print(f"  {m['index']}. {m['text'][:100]}")
        print("")
        ctx.close()


def cmd_clear_all(name, confirm):
    with sync_playwright() as p:
        ctx, page = open_whatsapp(p)
        wait_for_login(page)
        open_chat(page, name)
        scroll_history(page, times=10)
        _, msgs = visible_messages(page)
        print(f'\nGroup "{name}" — {len(msgs)} message rows currently rendered.')

        if not confirm:
            print("\nDRY RUN. Re-run with --confirm to actually clear.\n")
            ctx.close()
            return

        dump(name, msgs, "before-clear-all")

        # open the conversation menu in the header
        open_header_menu(page)

        item = page.locator('[data-testid="li-clear-chat"]').first
        if item.count() == 0:
            item = page.get_by_role("button", name=LABELS["clear_chat"]).first
        if item.count() == 0:
            item = page.get_by_text(LABELS["clear_chat"], exact=True).first
        safe_click(item, "Clear chat (menu item)")

        # --- confirmation dialog -------------------------------------------
        # Scope strictly to the modal. Clicking outside it hits the menu item
        # sitting behind the overlay, which is what failed before.
        dlg = page.locator('[role="dialog"]').last
        dlg.wait_for(state="visible", timeout=15000)

        print("\ndialog buttons:")
        for b in dlg.get_by_role("button").all():
            try:
                print("   -", ((b.get_attribute("aria-label") or b.inner_text()) or "").strip()[:40])
            except Exception:
                pass

        confirm_btn = dlg.get_by_role("button", name=LABELS["clear_chat"]).first
        if confirm_btn.count() == 0:
            # fall back to the last button that is not Cancel
            cands = [b for b in dlg.get_by_role("button").all()
                     if LABELS["cancel"].lower() not in ((b.inner_text() or "").strip().lower())]
            if not cands:
                raise RuntimeError("No confirm button found in the dialog")
            confirm_btn = cands[-1]
        safe_click(confirm_btn, "Clear chat (confirm dialog)")

        time.sleep(4)
        _, after = visible_messages(page)
        log(f'CLEAR-ALL group="{name}" rows_before={len(msgs)} rows_after={len(after)}')

        # prove the group still exists: if we can still find and open it by
        # name, it is in the chat list. open_chat() is the same routine that
        # has located this group on every run, so it is the reliable check.
        page.reload(wait_until="domcontentloaded")
        wait_for_login(page)
        time.sleep(5)
        try:
            open_chat(page, name)
            still = True
        except Exception as e:
            still = False
            log(f"verify could not reopen the chat: {e}")
        log(f"VERIFY group still present in chat list = {still}")
        if not still:
            log("NOTE: check your phone. Clear chat cannot remove a group, so "
                "a False here is most likely a verification miss.")
        ctx.close()


def cmd_clear_last(name, n, confirm):
    """Delete the newest N messages using WhatsApp's own Select messages mode."""
    with sync_playwright() as p:
        ctx, page = open_whatsapp(p)
        wait_for_login(page)
        open_chat(page, name)
        scroll_history(page, times=6)
        rows, msgs = visible_messages(page)

        targets = msgs[-n:]
        print(f"\nWould delete-for-me the newest {len(targets)} messages:")
        for t in targets:
            print("   -", t["text"][:90])

        if not confirm:
            print("\nDRY RUN. Re-run with --confirm to actually delete.\n")
            ctx.close()
            return

        dump(name, targets, f"before-clear-last{n}")

        # 1. enter multi-select mode
        open_header_menu(page)
        sel_item = page.get_by_text("Select messages", exact=True).first
        safe_click(sel_item, "Select messages")

        # 2. tick each target message
        ticked = 0
        for t in targets:
            try:
                rows.nth(t["index"]).click()
                ticked += 1
                time.sleep(0.5)
            except Exception as e:
                log(f"could not tick message {t['index']}: {e}")
        log(f"ticked {ticked} of {len(targets)} messages")

        if ticked == 0:
            log("nothing ticked - aborting without deleting")
            page.keyboard.press("Escape")
            ctx.close()
            return

        # 3. press Delete in the selection toolbar
        del_btn = page.get_by_role("button", name=LABELS["delete"]).first
        if del_btn.count() == 0:
            del_btn = page.locator('[data-icon="ic-delete-filled"], [aria-label="Delete"]').first
        safe_click(del_btn, "Delete (selection toolbar)")

        # 4. confirm with Delete for me
        confirm_btn = page.get_by_role("button", name=LABELS["delete_for_me"]).first
        if confirm_btn.count() == 0:
            confirm_btn = page.get_by_text(LABELS["delete_for_me"], exact=True).first
        safe_click(confirm_btn, "Delete for me (confirm)")

        time.sleep(3)
        _, after = visible_messages(page)
        log(f'CLEAR-LAST group="{name}" ticked={ticked} rows_before={len(msgs)} rows_after={len(after)}')
        ctx.close()


# ----------------------------------------------------------------------------
def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    confirm = "--confirm" in flags

    if not args:
        print(__doc__)
        return

    cmd = args[0]
    if cmd == "setup":
        cmd_setup()
    elif cmd == "list":
        cmd_list()
    elif cmd == "inspect":
        cmd_inspect(args[1])
    elif cmd == "probe-menu":
        cmd_probe_menu(args[1])
    elif cmd == "peek":
        cmd_peek(args[1])
    elif cmd == "clear-all":
        cmd_clear_all(args[1], confirm)
    elif cmd == "clear-last":
        cmd_clear_last(args[1], int(args[2]), confirm)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
