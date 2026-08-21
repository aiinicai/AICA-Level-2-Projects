"""
WhatsApp Group History Cleaner
==============================
Desktop tool that clears message history from WhatsApp groups in bulk,
exports chat history (with or without media), and never deletes a group
or a chat.

    pip install playwright
    python wa_cleaner.py
"""

import json
import os
import queue
import re
import sys
import threading
import time
from datetime import date as _date, datetime
from pathlib import Path

try:
    import webview
except ImportError:
    raise SystemExit("pywebview not installed.  Run:  pip install pywebview")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    raise SystemExit("Playwright not installed.  Run:  pip install playwright")

# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------
# When frozen by PyInstaller, __file__ points inside the temp extraction
# folder; user data (session, backups, log, presets) must live next to the
# EXE so it survives across launches.
if getattr(sys, "frozen", False):
    HERE = Path(sys.executable).parent
else:
    HERE = Path(__file__).parent

PROFILE_DIR = HERE / "wa-profile"
EXPORT_DIR = HERE / "exports"
LOG_FILE = HERE / "audit.log"
PRESETS_FILE = HERE / "presets.json"

BROWSER_CHANNEL = "msedge"

MESSAGE_SELECTORS = [
    '#main div[role="row"]',
    '#main [data-id]',
    '#main .copyable-text[data-pre-plain-text]',
    '#main div.message-in, #main div.message-out',
]

LABELS = {
    "menu_button": "Menu",
    "clear_chat": "Clear chat",
    "select_messages": "Select messages",
    "delete": "Delete",
    "delete_for_me": "Delete for me",
    "cancel": "Cancel",
    "more": "More",
    "export_chat": "Export chat",
}

FORBIDDEN = ["exit group", "delete chat", "delete group", "leave group",
             "delete for everyone"]

SLOW = 1.2
GROUP_GAP = 4.0
BACKUP_CAP = 300
DEFAULT_MAX_GROUPS = 50

# For older-than-date: WhatsApp puts a "[HH:MM(:SS) am/pm, DD/MM/YYYY]"
# prefix on message-carrying elements via data-pre-plain-text.
DATE_RE = re.compile(
    r'(\d{1,2}):(\d{2})(?::\d{2})?\s*(?:am|pm|AM|PM)?[,\s]+'
    r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})'
)

# --------------------------------------------------------------------------
# palette
# --------------------------------------------------------------------------
C_BG        = "#f1f5f9"
C_CARD      = "#ffffff"
C_BORDER    = "#e2e8f0"
C_PRIMARY   = "#16a34a"
C_PRIMARY_D = "#15803d"
C_ACCENT    = "#2563eb"
C_SUCCESS   = "#16a34a"
C_WARN      = "#ea580c"
C_DANGER    = "#dc2626"
C_TEXT      = "#0f172a"
C_MUTE      = "#64748b"
C_INPUT     = "#f1f5f9"
C_LOG_BG    = "#0b1220"
C_LOG_FG    = "#cbd5e1"

FONT_HEAD  = ("Segoe UI Semibold", 18)
FONT_SUB   = ("Segoe UI", 10)
FONT_CARD  = ("Segoe UI Semibold", 11)
FONT_BODY  = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_BTN   = ("Segoe UI Semibold", 10)
FONT_LOG   = ("Consolas", 9)


# --------------------------------------------------------------------------
# preset storage
# --------------------------------------------------------------------------
def load_presets():
    if not PRESETS_FILE.exists():
        return {}
    try:
        data = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_presets(data):
    PRESETS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                            encoding="utf-8")


def _looks_like_name(t):
    """True iff t plausibly is a chat title (not a URL, not a message,
    not a preview snippet). WhatsApp puts hover titles on many kinds of
    row content; this filter keeps only real-looking chat names."""
    if not t:
        return False
    t = t.strip()
    if not t or "\n" in t or "\t" in t:
        return False
    if len(t) > 50:
        return False
    lt = t.lower()
    if "://" in lt:
        return False
    if lt.startswith(("http", "www.", "wa.me/", "chat.whatsapp.com")):
        return False
    if t.startswith("[") and t.endswith("]"):
        return False   # [Photo], [Video], [Sticker], etc.
    if t.startswith("~"):
        return False   # WA "~Name" preview marker
    if ": " in t and any(m in lt for m in
                        ("you: ", "photo", "video", "audio",
                         "sticker", "document", "gif", "voice")):
        return False   # "You: photo", "Rahul: video", etc.
    return True


def extract_message_date(text):
    """Return a date parsed from the WhatsApp timestamp prefix in the given
    raw text (typically data-pre-plain-text), or None. Tries DD/MM/YYYY
    first, then MM/DD/YYYY."""
    if not text:
        return None
    m = DATE_RE.search(text)
    if not m:
        return None
    _, _, a, b, y = m.groups()
    a, b, y = int(a), int(b), int(y)
    if y < 100:
        y += 2000
    for day, month in ((a, b), (b, a)):
        try:
            return _date(y, month, day)
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------
# worker  (all Playwright work happens on this thread, never the GUI thread)
# --------------------------------------------------------------------------
class Worker(threading.Thread):
    def __init__(self, jobs, out):
        super().__init__(daemon=True)
        self.jobs = jobs
        self.out = out
        self.cancel = threading.Event()
        self.page = None
        self.ctx = None
        self.groups_only = True
        self.want_backup = True
        self.max_groups = DEFAULT_MAX_GROUPS

    def say(self, msg, kind="info"):
        self.out.put(("log", msg, kind))
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')}  {msg}\n")

    def send(self, tag, payload=None):
        self.out.put((tag, payload, "info"))

    # ---- safety ----
    def safe_click(self, locator, label):
        try:
            text = (locator.inner_text(timeout=3000) or "").strip().lower()
        except Exception:
            text = ""
        for bad in FORBIDDEN:
            if bad in text:
                raise RuntimeError(f"BLOCKED: refused to click '{text}'")
        locator.click(timeout=12000)
        self.say(f"   · {label}")
        time.sleep(SLOW)

    # ---- browser ----
    def run(self):
        try:
            with sync_playwright() as p:
                PROFILE_DIR.mkdir(exist_ok=True)
                self.ctx = p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR),
                    channel=BROWSER_CHANNEL,
                    headless=False,
                    viewport={"width": 1350, "height": 880},
                    args=["--disable-blink-features=AutomationControlled"],
                    accept_downloads=True,
                )
                self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
                self.page.goto("https://web.whatsapp.com",
                               wait_until="domcontentloaded")

                self.say("Waiting for WhatsApp to load — scan the QR if shown.")
                deadline = time.time() + 300
                while time.time() < deadline:
                    if self.page.locator("#pane-side").count() > 0:
                        break
                    time.sleep(2)
                else:
                    self.say("Timed out waiting for login.", "err")
                    self.send("dead")
                    return

                time.sleep(3)
                self.say("Connected to WhatsApp Web.", "ok")
                self.send("ready")
                self.loop()
        except Exception as e:
            self.say(f"Worker crashed: {e}", "err")
            self.send("dead")

    def loop(self):
        while True:
            job = self.jobs.get()
            kind = job.get("type")
            try:
                if kind == "quit":
                    break
                elif kind == "groups":
                    self.max_groups = job.get("limit", DEFAULT_MAX_GROUPS)
                    self.job_groups()
                elif kind == "clear":
                    self.job_clear(job)
                elif kind == "export":
                    self.job_export(job)
                elif kind == "verify":
                    self.job_verify(job)
                elif kind == "delete_threads":
                    self.job_delete_threads(job)
            except Exception as e:
                self.say(f"Error: {e}", "err")
                self.send("done")
        try:
            self.ctx.close()
        except Exception:
            pass

    # ---- helpers ----
    def rows(self):
        for sel in MESSAGE_SELECTORS:
            loc = self.page.locator(sel)
            try:
                n = loc.count()
            except Exception:
                continue
            if n > 0:
                return loc, n
        return None, 0

    def read_rows(self, loc, indices, cap=BACKUP_CAP):
        out = []
        for i in list(indices)[-cap:]:
            try:
                t = loc.nth(i).inner_text(timeout=900).replace("\n", " | ").strip()[:160]
            except Exception:
                t = "<unreadable>"
            out.append({"index": i, "text": t})
        return out

    def scroll_history(self, times=10):
        pane = self.page.locator("#main")
        for _ in range(times):
            try:
                pane.click(position={"x": 20, "y": 20})
            except Exception:
                pass
            self.page.keyboard.press("PageUp")
            time.sleep(0.6)
        time.sleep(1.2)

    def scroll_to_top(self, max_pages=500, max_seconds=300):
        """PageUp until the top is reached — five consecutive scrolls with
        no new rows loading — or safety caps hit. Cancellable."""
        pane = self.page.locator("#main")
        try:
            pane.click(position={"x": 20, "y": 20})
        except Exception:
            pass
        _, last = self.rows()
        self.say(f"   · scrolling to top of history (starts at {last} rows)")
        stall, t0 = 0, time.time()
        for i in range(max_pages):
            if self.cancel.is_set():
                self.say("   · scroll cancelled", "warn")
                return
            if time.time() - t0 > max_seconds:
                self.say(f"   · scroll timed out at {i} pages", "warn")
                return
            self.page.keyboard.press("PageUp")
            time.sleep(0.55)
            _, now = self.rows()
            if now == last:
                stall += 1
                if stall >= 5:
                    self.say(f"   · reached top after {i + 1} pages "
                             f"({now} rows loaded)", "ok")
                    return
            else:
                stall = 0
                last = now
            if (i + 1) % 20 == 0:
                self.say(f"   · scrolled {i + 1} pages — {now} rows loaded")
        self.say(f"   · scroll hit the {max_pages}-page cap "
                 f"({last} rows loaded)", "warn")

    def open_chat(self, name):
        box = self.page.get_by_role("textbox").first
        box.click()
        time.sleep(0.4)
        self.page.keyboard.press("Control+A")
        self.page.keyboard.press("Backspace")
        box.type(name, delay=50)
        time.sleep(2.2)
        res = self.page.locator("#pane-side").get_by_title(name, exact=True).first
        if res.count() == 0:
            raise RuntimeError(f'chat "{name}" not found')
        res.click()
        self.page.wait_for_selector("#main header", timeout=20000)
        time.sleep(SLOW)

    def open_header_menu(self):
        hdr = self.page.locator("#main header")
        hdr.first.wait_for(state="visible", timeout=20000)
        btn = hdr.get_by_role("button", name=LABELS["menu_button"]).first
        if btn.count() == 0:
            btn = self.page.locator('#main header [data-icon="menu"]').first
        if btn.count() == 0:
            btn = hdr.locator("button").last
        btn.wait_for(state="visible", timeout=10000)
        btn.click(timeout=10000)
        time.sleep(SLOW)

    def backup(self, group, items, tag):
        if not self.want_backup:
            self.say("   · backup skipped (disabled)")
            return
        EXPORT_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe = "".join(c if c.isalnum() else "_" for c in group)[:50]
        path = EXPORT_DIR / f"{safe}_{tag}_{stamp}.json"
        path.write_text(json.dumps(items, indent=2, ensure_ascii=False),
                        encoding="utf-8")
        self.say(f"   · backup: {path.name}")

    def menu_texts(self, limit=40):
        out = []
        for sel in ['[role="application"] li', '[role="menu"] li',
                    'li[role="button"]', '[role="menuitem"]']:
            for it in self.page.locator(sel).all()[:limit]:
                try:
                    t = (it.inner_text() or "").strip().replace("\n", " ")
                except Exception:
                    continue
                if t and len(t) < 40 and t not in out:
                    out.append(t)
            if out:
                break
        return out

    def click_menu_containing(self, keyword, label, avoid=None):
        """Find the first currently-visible menu item whose text contains
        keyword (case-insensitive substring) and click it. FORBIDDEN
        strings are always avoided. Returns True on success."""
        kw = keyword.lower()
        avoid_low = [a.lower() for a in (avoid or [])]
        for sel in ['[role="application"] li', '[role="menu"] li',
                    'li[role="button"]', '[role="menuitem"]']:
            for it in self.page.locator(sel).all()[:40]:
                try:
                    t = (it.inner_text() or "").strip()
                except Exception:
                    continue
                lt = t.lower()
                if not lt or len(lt) > 40:
                    continue
                if kw not in lt:
                    continue
                if any(bad in lt for bad in FORBIDDEN):
                    continue
                if any(a in lt for a in avoid_low):
                    continue
                try:
                    it.click(timeout=8000)
                    self.say(f"   · {label}")
                    time.sleep(SLOW)
                    return True
                except Exception:
                    continue
        return False

    def job_groups(self):
        self.say("Reading chat list…")
        pane = self.page.locator("#pane-side")
        chain = ['#pane-side [role="listitem"] span[title]',
                 '#pane-side div[role="row"] span[title]',
                 '#pane-side span[title]']
        sel = None
        for c in chain:
            try:
                if self.page.locator(c).count() > 0:
                    sel = c
                    break
            except Exception:
                continue
        if not sel:
            self.say("Could not find any chat rows.", "err")
            self.send("groups", [])
            return
        self.say(f"   · using {sel}")

        box = pane.bounding_box()
        cx = (box["x"] + box["width"] / 2) if box else 200
        cy = (box["y"] + box["height"] / 2) if box else 400

        limit = self.max_groups
        seen, seen_set, stale, passes = [], set(), 0, 0
        preview_map = {}
        kind_map = {}
        t0 = time.time()
        MAX_PASSES, MAX_SECONDS = 120, 150

        while (len(seen) < limit and stale < 4 and passes < MAX_PASSES
               and time.time() - t0 < MAX_SECONDS
               and not self.cancel.is_set()):
            before = len(seen)

            # PRIMARY: iterate at LISTITEM level and pick exactly ONE
            # valid title per row. Iterating span[title] directly (the
            # old approach) counted each row's message-preview span as a
            # second entry, doubling the list (150 → 75 real + 75 previews).
            row_titles = []
            try:
                row_titles = self.page.locator(
                    '#pane-side [role="listitem"]'
                ).evaluate_all(
                    "els => els.map(el => {"
                    " const spans = [...el.querySelectorAll('span[title]')];"
                    " const bad = t => !t || t.length > 50 || /:\\/\\//.test(t)"
                    "   || /^(https?|www\\.|wa\\.me\\/)/i.test(t)"
                    "   || /[\\n\\t]/.test(t)"
                    "   || (t.startsWith('[') && t.endsWith(']'))"
                    "   || t.startsWith('~');"
                    " for (const sp of spans) {"
                    "   const t = (sp.getAttribute('title')||'').trim();"
                    "   if (t && !bad(t)) return t;"
                    " }"
                    " return '';"
                    "})"
                )
            except Exception:
                row_titles = []

            if row_titles:
                for t in row_titles:
                    if not t or not _looks_like_name(t):
                        continue
                    if t not in seen_set:
                        seen.append(t); seen_set.add(t)
                    if len(seen) >= limit:
                        break
            else:
                # fallback for builds where [role="listitem"] returns 0
                for el in self.page.locator(sel).all():
                    try:
                        t = el.get_attribute("title")
                    except Exception:
                        t = None
                    if not t or not _looks_like_name(t.strip()):
                        continue
                    t = t.strip()
                    if t not in seen_set:
                        seen.append(t); seen_set.add(t)
                    if len(seen) >= limit:
                        break

            # SECONDARY: pick the CHAT NAME (not a message preview) and
            # classify group vs individual. WhatsApp puts hover-title
            # attributes on both the chat name AND on message previews
            # (URLs, forwarded text, etc.), so we filter out anything
            # that looks like a message before accepting a title as a name.
            try:
                rows_meta = self.page.locator(
                    '#pane-side [role="listitem"]'
                ).evaluate_all(
                    "els => els.map(el => {"
                    " const spans = [...el.querySelectorAll('span[title]')];"
                    " const isMsg = t => !t || t.length > 55 ||"
                    "   /^(https?:\\/\\/|www\\.)/i.test(t) ||"
                    "   /\\n/.test(t) || /^\\[/.test(t);"
                    " let name = '', preview = '';"
                    " for (const sp of spans) {"
                    "   const t = (sp.getAttribute('title')||'').trim();"
                    "   if (!t) continue;"
                    "   if (!name && !isMsg(t)) name = t;"
                    "   else if (!preview && t !== name) preview = t;"
                    " }"
                    " let kind = 'unknown';"
                    " const icons = [...el.querySelectorAll('[data-icon]')]"
                    "   .map(x => (x.getAttribute('data-icon')||'').toLowerCase());"
                    " for (const ic of icons) {"
                    "   if (ic.includes('group') || ic.includes('community')) { kind='group'; break; }"
                    "   if (ic.includes('default-user') || ic === 'user') { kind='individual'; break; }"
                    " }"
                    " if (kind === 'unknown') {"
                    "   const labs = [...el.querySelectorAll('[aria-label]')]"
                    "     .map(x => (x.getAttribute('aria-label')||'').toLowerCase());"
                    "   if (labs.some(l => l.includes('group'))) kind='group';"
                    " }"
                    " return [name, preview, kind];"
                    "})"
                )
                for meta in rows_meta:
                    if not meta or len(meta) < 3 or not meta[0]:
                        continue
                    nm = meta[0].strip()
                    pv = (meta[1] or "").strip()
                    kn = meta[2] or "unknown"
                    if nm and pv and pv != nm and nm not in preview_map:
                        preview_map[nm] = pv[:100]
                    if nm and kn != "unknown" and nm not in kind_map:
                        kind_map[nm] = kn
            except Exception:
                pass

            stale = stale + 1 if len(seen) == before else 0
            passes += 1
            if passes % 5 == 0:
                self.say(f"   · scrolling… {len(seen)} chats so far")
            try:
                self.page.mouse.move(cx, cy)
                self.page.mouse.wheel(0, 900)
            except Exception:
                pass
            time.sleep(0.6)

        if self.cancel.is_set():
            self.say("   · listing cancelled", "warn")
        elif len(seen) >= limit:
            self.say(f"   · reached the {limit}-chat limit", "warn")
        elif passes >= MAX_PASSES or time.time() - t0 >= MAX_SECONDS:
            self.say("   · stopped at the scroll limit — increase Load max "
                     "and reload if a chat is missing", "warn")

        self.say("   · returning to the top of the list")
        for _ in range(25):
            try:
                self.page.mouse.move(cx, cy)
                self.page.mouse.wheel(0, -2000)
            except Exception:
                break
            time.sleep(0.05)

        self.say(f"Found {len(seen)} chats (limit {limit}); "
                 f"classified {len(kind_map)} via WA icons.", "ok")
        items = [{"name": n,
                  "preview": preview_map.get(n, ""),
                  "kind": kind_map.get(n, "unknown")}
                 for n in seen]
        self.send("groups", items)

    def overlay_open(self):
        try:
            if self.page.locator('[role="dialog"]').count() > 0:
                return True
            if self.page.locator('[data-testid="li-clear-chat"]').count() > 0:
                return True
            if self.page.get_by_text(LABELS["select_messages"], exact=True).count() > 0:
                return True
        except Exception:
            pass
        return False

    def reset_ui(self):
        for _ in range(3):
            if not self.overlay_open():
                return
            try:
                self.page.keyboard.press("Escape")
            except Exception:
                return
            time.sleep(0.4)

    def open_menu_verified(self):
        for attempt in range(1, 4):
            self.reset_ui()
            try:
                self.open_header_menu()
            except Exception as e:
                self.say(f"   · menu click failed ({attempt}/3): {e}", "warn")
                continue
            items = self.menu_texts()
            if not items:
                self.say(f"   · menu looked empty ({attempt}/3)", "warn")
                time.sleep(1.0)
                continue
            low = [t.lower() for t in items]
            if self.groups_only and not any(
                    "exit group" in t or "group info" in t or "add member" in t
                    for t in low):
                self.reset_ui()
                raise RuntimeError("not a group — skipped")
            return items
        raise RuntimeError("could not open the chat menu after 3 tries")

    def clear_all_history(self, name):
        loc, n = self.rows()
        self.say(f"   · {n} message rows rendered")
        if loc is not None and n:
            self.backup(name, self.read_rows(loc, range(n)), "before-clear-all")
        self.open_menu_verified()
        item = self.page.locator('[data-testid="li-clear-chat"]').first
        if item.count() == 0:
            item = self.page.get_by_text(LABELS["clear_chat"], exact=True).first
        if item.count() == 0:
            self.reset_ui()
            raise RuntimeError("'Clear chat' not present in this chat's menu")
        self.safe_click(item, "Clear chat")
        dlg = self.page.locator('[role="dialog"]').last
        dlg.wait_for(state="visible", timeout=20000)
        btn = dlg.get_by_role("button", name=LABELS["clear_chat"]).first
        if btn.count() == 0:
            cands = [b for b in dlg.get_by_role("button").all()
                     if LABELS["cancel"].lower() not in (b.inner_text() or "").lower()]
            btn = cands[-1]
        self.safe_click(btn, "confirm")
        time.sleep(3)
        _, after = self.rows()
        self.say(f"   · rows {n} → {after}", "ok")

    def clear_n(self, name, n, newest=True, scroll_all=False):
        if scroll_all:
            self.scroll_to_top()
        elif not newest:
            self.scroll_history(10)
        loc, total = self.rows()
        if not total:
            self.say("   · no messages found", "warn")
            return
        idx = list(range(total))[-n:] if newest else list(range(total))[:n]
        which = ("newest" if newest else
                 ("oldest (from top)" if scroll_all else "oldest (rendered)"))
        self.say(f"   · targeting {len(idx)} of {total} rendered ({which})")
        self.backup(name, self.read_rows(loc, idx),
                    f"before-clear-{'last' if newest else 'first'}{n}")
        self._select_and_delete(loc, idx)

    def clear_older_than(self, name, cutoff):
        self.scroll_to_top()
        loc, total = self.rows()
        if not total:
            self.say("   · no messages loaded", "warn")
            return
        idx, dated = [], 0
        for i in range(total):
            if self.cancel.is_set():
                self.say("   · scan cancelled", "warn")
                return
            try:
                attr = loc.nth(i).evaluate(
                    "el => (el.querySelector('[data-pre-plain-text]')"
                    "||el).getAttribute?.('data-pre-plain-text') || ''"
                )
            except Exception:
                attr = ""
            d = extract_message_date(attr)
            if d is None:
                continue
            dated += 1
            if d < cutoff:
                idx.append(i)
        self.say(f"   · {dated} of {total} rows had a parseable date; "
                 f"{len(idx)} are older than {cutoff.isoformat()}")
        if not idx:
            return
        self.backup(name, self.read_rows(loc, idx),
                    f"before-clear-before-{cutoff.isoformat()}")
        self._select_and_delete(loc, idx)

    def _select_and_delete(self, loc, idx):
        self.open_menu_verified()
        sm = self.page.get_by_text(LABELS["select_messages"], exact=True).first
        if sm.count() == 0:
            self.reset_ui()
            raise RuntimeError("'Select messages' not present in this chat's menu")
        self.safe_click(sm, "Select messages")
        ticked = 0
        for i in idx:
            try:
                row = loc.nth(i)
                row.scroll_into_view_if_needed(timeout=3000)
                row.click(timeout=4000)
                ticked += 1
                time.sleep(0.35)
            except Exception:
                pass
        self.say(f"   · ticked {ticked}")
        if ticked == 0:
            self.page.keyboard.press("Escape")
            return
        db = self.page.get_by_role("button", name=LABELS["delete"]).first
        if db.count() == 0:
            db = self.page.locator('[aria-label="Delete"]').first
        self.safe_click(db, "Delete")
        dlg = self.page.locator('[role="dialog"]').last
        dlg.wait_for(state="visible", timeout=20000)
        cb = dlg.get_by_role("button", name=LABELS["delete_for_me"]).first
        if cb.count() == 0:
            cb = dlg.get_by_text(LABELS["delete_for_me"], exact=True).first
        self.safe_click(cb, "Delete for me")
        time.sleep(2)

    def job_clear(self, job):
        groups = job["groups"]
        mode = job["mode"]
        n = job["n"]
        dry = job["dry"]
        self.groups_only = job.get("groups_only", True)
        self.want_backup = job.get("backup", True)
        cutoff = job.get("cutoff")  # date object for "Older than"

        self.cancel.clear()
        self.say("")
        head = f"{'DRY RUN — ' if dry else ''}{mode}"
        if mode == "Older than" and cutoff:
            head += f" ({cutoff.isoformat()})"
        elif mode in ("Last N", "First N", "First N true"):
            head += f" ({n})"
        head += f" across {len(groups)} chat(s)"
        self.say(head)
        self.say("─" * 60)

        for idx, g in enumerate(groups, 1):
            if self.cancel.is_set():
                self.say("Cancelled by user.", "warn")
                break
            self.send("progress", (idx, len(groups)))
            self.say(f"[{idx}/{len(groups)}] {g}")
            try:
                self.reset_ui()
                self.open_chat(g)
                if dry:
                    try:
                        self.open_menu_verified()
                    except RuntimeError as e:
                        self.say(f"   · {e}", "warn")
                        self.reset_ui()
                        continue
                    self.reset_ui()
                    _, cnt = self.rows()
                    if mode == "All history":
                        detail = "all"
                    elif mode == "Older than" and cutoff:
                        detail = f"older than {cutoff.isoformat()} (of loaded)"
                    else:
                        detail = str(min(n, cnt))
                    self.say(f"   · group ok — would affect {detail} of "
                             f"{cnt} rendered messages")
                elif mode == "All history":
                    self.clear_all_history(g)
                elif mode == "Last N":
                    self.clear_n(g, n, newest=True)
                elif mode == "First N":
                    self.clear_n(g, n, newest=False, scroll_all=False)
                elif mode == "First N true":
                    self.clear_n(g, n, newest=False, scroll_all=True)
                elif mode == "Older than" and cutoff:
                    self.clear_older_than(g, cutoff)
                else:
                    self.say(f"   · unknown mode {mode}", "err")
            except Exception as e:
                msg = str(e).split("Call log:")[0].strip()[:180]
                self.say(f"   · skipped: {msg}", "err")
                try:
                    self.reset_ui()
                except Exception:
                    pass
            time.sleep(GROUP_GAP)

        self.say("─" * 60)
        self.say("Finished." if not dry
                 else "Dry run finished — nothing was changed.", "ok")
        self.send("done")

    # ---- verify (open each chat's menu and classify group vs individual) ----
    def job_verify(self, job):
        names = job.get("groups", [])
        self.cancel.clear()
        self.say(f"Verifying {len(names)} chat(s) via menu check…")
        self.say("─" * 60)
        for idx, g in enumerate(names, 1):
            if self.cancel.is_set():
                self.say("Verification cancelled.", "warn"); break
            self.send("progress", (idx, len(names)))
            try:
                self.reset_ui()
                self.open_chat(g)
                self.groups_only = False   # scan without raising
                self.reset_ui()
                self.open_header_menu()
                items = [t.lower() for t in self.menu_texts()]
                kind = "group" if any(
                    "exit group" in t or "group info" in t or "add member" in t
                    for t in items
                ) else "individual"
                self.reset_ui()
                self.say(f"   [{idx}/{len(names)}] {g} → {kind}")
                self.out.put(("kind", (g, kind), "info"))
            except Exception as e:
                self.say(f"   · could not classify {g}: {e}", "warn")
                self.reset_ui()
            time.sleep(0.6)
        self.say("─" * 60)
        self.say("Verification complete.", "ok")
        self.send("done")

    # ---- delete individual chat threads (clear + delete chat) ----
    def job_delete_threads(self, job):
        names = job.get("groups", [])
        self.want_backup = bool(job.get("backup", True))
        self.cancel.clear()
        self.say(f"Delete-thread run across {len(names)} individual chat(s)")
        self.say("─" * 60)
        for idx, g in enumerate(names, 1):
            if self.cancel.is_set():
                self.say("Cancelled by user.", "warn"); break
            self.send("progress", (idx, len(names)))
            self.say(f"[{idx}/{len(names)}] {g}")
            try:
                self.reset_ui()
                self.open_chat(g)
                # verify it is an individual (menu MUST NOT have group markers)
                self.reset_ui()
                self.open_header_menu()
                items = [t.lower() for t in self.menu_texts()]
                if any("exit group" in t or "group info" in t
                       or "add member" in t for t in items):
                    self.reset_ui()
                    self.say("   · SKIPPED: this is a group, not an "
                            "individual chat", "warn")
                    continue
                self.reset_ui()
                # clear history first
                self.groups_only = False
                self.clear_all_history(g)
                # then delete the chat thread (individual only!)
                self.reset_ui()
                self.open_header_menu()
                items_now = self.menu_texts()
                target = None
                for t in items_now:
                    lt = t.lower()
                    if "delete chat" in lt and "group" not in lt:
                        target = t
                        break
                if not target:
                    self.say("   · 'Delete chat' not present — thread not "
                            "removed", "warn")
                    self.reset_ui()
                    continue
                # find and click by text (bypass safe_click FORBIDDEN)
                clicked = False
                for sel_it in ['[role="application"] li', '[role="menu"] li',
                               'li[role="button"]', '[role="menuitem"]']:
                    if clicked: break
                    for it in self.page.locator(sel_it).all()[:40]:
                        try:
                            t = (it.inner_text() or "").strip()
                        except Exception:
                            continue
                        if t == target:
                            try:
                                it.click(timeout=8000)
                                self.say(f"   · Delete chat "
                                         f"(individual only)", "warn")
                                time.sleep(SLOW)
                                clicked = True
                                break
                            except Exception:
                                continue
                if not clicked:
                    self.say("   · could not click Delete chat", "err")
                    self.reset_ui()
                    continue
                # confirm dialog
                dlg = self.page.locator('[role="dialog"]').last
                dlg.wait_for(state="visible", timeout=15000)
                confirm_btn = dlg.get_by_role(
                    "button", name="Delete chat").first
                if confirm_btn.count() == 0:
                    cands = [b for b in dlg.get_by_role("button").all()
                             if (b.inner_text() or "").strip().lower()
                             != "cancel"]
                    confirm_btn = cands[-1] if cands else None
                if confirm_btn:
                    confirm_btn.click(timeout=10000)
                    self.say("   · confirmed — thread deleted", "ok")
                    time.sleep(2)
                else:
                    self.say("   · confirmation button not found", "err")
                    self.reset_ui()
            except Exception as e:
                msg = str(e).split("Call log:")[0].strip()[:180]
                self.say(f"   · skipped: {msg}", "err")
                try: self.reset_ui()
                except Exception: pass
            time.sleep(GROUP_GAP)
        self.say("─" * 60)
        self.say("Delete-thread run finished.", "ok")
        self.send("done")

    # ---- export ----
    def job_export(self, job):
        groups = job["groups"]
        dest = Path(job["dest"])
        with_media = bool(job.get("with_media", False))
        self.groups_only = job.get("groups_only", True)
        self.cancel.clear()
        self.say("")
        self.say(f"Export {'WITH' if with_media else 'WITHOUT'} media — "
                 f"{len(groups)} chat(s) → {dest}")
        self.say("─" * 60)
        dest.mkdir(parents=True, exist_ok=True)
        ok, fail = 0, 0
        for idx, g in enumerate(groups, 1):
            if self.cancel.is_set():
                self.say("Cancelled by user.", "warn")
                break
            self.send("progress", (idx, len(groups)))
            self.say(f"[{idx}/{len(groups)}] {g}")
            try:
                self.reset_ui()
                self.open_chat(g)
                self.open_menu_verified()

                # Export chat may be a direct menu item, or nested one level
                # deeper under "More". Try direct first, then walk into More.
                self.say(f"   · menu items: {self.menu_texts()}")
                clicked = self.click_menu_containing("export", "Export chat")
                if not clicked:
                    if self.click_menu_containing("more", "More",
                                                  avoid=["delete", "leave",
                                                         "exit"]):
                        time.sleep(SLOW)
                        clicked = self.click_menu_containing(
                            "export", "Export chat")
                if not clicked:
                    self.reset_ui()
                    raise RuntimeError("'Export chat' not present in this "
                                       "chat's menu (see menu items above)")

                dlg = self.page.locator('[role="dialog"]').last
                dlg.wait_for(state="visible", timeout=20000)

                # Media choice: WhatsApp uses "Include Media" / "Without Media"
                # on most builds. Match by substring for resilience.
                wanted = "include" if with_media else "without"
                choice = None
                choice_label = None
                for b in dlg.get_by_role("button").all():
                    try:
                        t = (b.inner_text() or "").strip()
                    except Exception:
                        continue
                    lt = t.lower()
                    if wanted in lt and "media" in lt:
                        choice, choice_label = b, t; break
                if choice is None:
                    # some builds render as clickable divs, not buttons
                    for b in dlg.locator("div[role='button'], span").all():
                        try:
                            t = (b.inner_text() or "").strip()
                        except Exception:
                            continue
                        lt = t.lower()
                        if wanted in lt and "media" in lt:
                            choice, choice_label = b, t; break
                if choice is None:
                    self.reset_ui()
                    raise RuntimeError(f"could not find '{wanted} media' "
                                       f"button in the export dialog")

                with self.page.expect_download(timeout=180000) as di:
                    self.safe_click(choice, choice_label)
                dl = di.value
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                safe = "".join(c if c.isalnum() else "_" for c in g)[:50]
                suffix = Path(dl.suggested_filename).suffix or ".zip"
                out_path = dest / f"{safe}_{stamp}{suffix}"
                dl.save_as(str(out_path))
                self.say(f"   · saved: {out_path.name}", "ok")
                ok += 1
            except Exception as e:
                msg = str(e).split("Call log:")[0].strip()[:180]
                self.say(f"   · skipped: {msg}", "err")
                fail += 1
                try:
                    self.reset_ui()
                except Exception:
                    pass
            time.sleep(GROUP_GAP)
        self.say("─" * 60)
        self.say(f"Export finished — {ok} ok, {fail} failed.",
                 "ok" if fail == 0 else "warn")
        self.send("done")

# --------------------------------------------------------------------------
# UI  (pywebview + inline HTML/CSS/JS — real modern dashboard)
# --------------------------------------------------------------------------

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>WhatsApp Cleaner</title>
<style>
*,*::before,*::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg-1: #05070f;
  --bg-2: #0a0f1e;
  --bg-3: #0f172e;
  --card-bg: rgba(20, 27, 51, 0.72);
  --card-border: rgba(148, 163, 184, 0.12);
  --card-hi: rgba(255, 255, 255, 0.04);
  --text: #f1f5f9;
  --text-2: #cbd5e1;
  --muted: #7c88a3;
  --accent: #22c55e;
  --accent-d: #16a34a;
  --info: #3b82f6;
  --info-d: #2563eb;
  --purple: #a855f7;
  --purple-d: #7c3aed;
  --cyan: #06b6d4;
  --cyan-d: #0891b2;
  --orange: #f97316;
  --orange-d: #ea580c;
  --pink: #ec4899;
  --danger: #ef4444;
  --danger-d: #dc2626;
}
html, body { height: 100vh; width: 100vw; overflow: hidden; }
body {
  font-family: Calibri, "Segoe UI", "Inter", system-ui, sans-serif;
  font-size: 15px; color: var(--text);
  background:
    radial-gradient(1200px 800px at 15% -10%, rgba(34,197,94,0.18), transparent 60%),
    radial-gradient(1000px 700px at 100% 100%, rgba(59,130,246,0.20), transparent 55%),
    radial-gradient(900px 600px at 100% 0%, rgba(168,85,247,0.13), transparent 60%),
    linear-gradient(180deg, #05070f 0%, #0a0f1e 100%);
  background-attachment: fixed;
}
button, input, select { font-family: inherit; font-size: inherit; color: inherit; }
button { cursor: pointer; border: 0; background: transparent; }
input, select { outline: none; }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2a3454; border-radius: 5px; }
::-webkit-scrollbar-thumb:hover { background: #3a4970; }

/* ---------- shell ---------- */
.shell {
  display: grid;
  grid-template-columns: 78px 1fr;
  height: 100vh;
}
.side {
  display: flex; flex-direction: column; align-items: center;
  gap: 8px; padding: 18px 0;
  background: rgba(6, 10, 22, 0.7);
  border-right: 1px solid var(--card-border);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
.side .logo {
  width: 46px; height: 46px; border-radius: 14px;
  background: linear-gradient(135deg, #22c55e 0%, #06b6d4 100%);
  display: grid; place-items: center;
  font-size: 22px; margin-bottom: 12px;
  box-shadow: 0 10px 24px rgba(34,197,94,0.35);
}
.side .nav {
  width: 46px; height: 46px; border-radius: 14px;
  display: grid; place-items: center;
  font-size: 20px; color: var(--muted);
  transition: background 0.15s, color 0.15s, transform 0.05s;
  cursor: pointer;
}
.side .nav:hover { background: rgba(255,255,255,0.06); color: var(--text); }
.side .nav.active {
  color: var(--accent);
  background: rgba(34,197,94,0.14);
  box-shadow: inset 0 0 0 1px rgba(34,197,94,0.25);
}
.side .spacer { flex: 1; }

/* ---------- main ---------- */
main {
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  gap: 18px;
  padding: 22px 26px 20px;
  min-width: 0; min-height: 0;
  overflow: hidden;
}

/* ---------- top ---------- */
.top {
  display: flex; align-items: center; justify-content: space-between;
  gap: 20px;
}
.top .title { font-size: 26px; font-weight: 700; letter-spacing: -0.4px; }
.top .subtitle { font-size: 13px; color: var(--muted); margin-top: 3px; }
.pill {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 10px 18px; border-radius: 999px;
  background: rgba(148,163,184,0.14); color: var(--muted);
  font-weight: 600; font-size: 13px;
  border: 1px solid var(--card-border);
}
.pill.connected { background: rgba(34,197,94,0.16); color: var(--accent); border-color: rgba(34,197,94,0.3); }
.pill.busy { background: rgba(249,115,22,0.16); color: var(--orange); border-color: rgba(249,115,22,0.3); }
.pill.dead { background: rgba(239,68,68,0.16); color: var(--danger); border-color: rgba(239,68,68,0.3); }
.pill .dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor;
  box-shadow: 0 0 10px currentColor; }

/* ---------- metric tiles ---------- */
.metrics {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px;
}
.tile {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 18px;
  padding: 14px 18px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  display: flex; align-items: center; gap: 14px;
  position: relative; overflow: hidden;
}
.tile .icon {
  width: 44px; height: 44px; border-radius: 12px;
  display: grid; place-items: center; font-size: 20px; flex-shrink: 0;
}
.tile.a .icon { background: linear-gradient(135deg, #22c55e, #16a34a); }
.tile.b .icon { background: linear-gradient(135deg, #a855f7, #7c3aed); }
.tile.c .icon { background: linear-gradient(135deg, #06b6d4, #0891b2); }
.tile.d .icon { background: linear-gradient(135deg, #f97316, #ea580c); }
.tile .k { font-size: 12px; color: var(--muted); text-transform: uppercase;
  letter-spacing: 0.6px; font-weight: 600; }
.tile .v { font-size: 26px; font-weight: 800; line-height: 1.1; margin-top: 2px; }

/* ---------- body ---------- */
.body {
  display: grid; grid-template-columns: minmax(0,1fr) 480px; gap: 18px;
  min-height: 0; min-width: 0;
}
.card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 22px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  display: flex; flex-direction: column; overflow: hidden;
  min-height: 0; min-width: 0;
}
.card-head {
  padding: 16px 22px 10px;
  font-weight: 700; font-size: 16px;
  display: flex; align-items: center; gap: 10px;
}
.card-body { padding: 6px 22px 18px; }

/* ---------- buttons ---------- */
.btn {
  padding: 11px 18px; border-radius: 12px;
  font-weight: 700; font-size: 13.5px;
  display: inline-flex; align-items: center; gap: 8px;
  transition: filter 0.15s, transform 0.05s, box-shadow 0.15s;
  color: white; white-space: nowrap;
}
.btn:hover { filter: brightness(1.14); }
.btn:active { transform: translateY(1px); }
.btn:disabled { opacity: 0.45; cursor: not-allowed; filter: grayscale(20%); }
.btn-green   { background: linear-gradient(140deg, #22c55e, #16a34a);
  box-shadow: 0 8px 24px rgba(34,197,94,0.28); }
.btn-purple  { background: linear-gradient(140deg, #a855f7, #7c3aed);
  box-shadow: 0 8px 24px rgba(168,85,247,0.28); }
.btn-cyan    { background: linear-gradient(140deg, #06b6d4, #0891b2);
  box-shadow: 0 8px 24px rgba(6,182,212,0.28); }
.btn-orange  { background: linear-gradient(140deg, #f97316, #ea580c);
  box-shadow: 0 8px 24px rgba(249,115,22,0.28); }
.btn-blue    { background: linear-gradient(140deg, #3b82f6, #2563eb);
  box-shadow: 0 8px 24px rgba(59,130,246,0.28); }
.btn-red     { background: linear-gradient(140deg, #ef4444, #dc2626);
  box-shadow: 0 8px 24px rgba(239,68,68,0.24); }
.btn-ghost   { background: rgba(255,255,255,0.06); color: var(--text-2);
  border: 1px solid var(--card-border); }
.btn-ghost:hover { background: rgba(255,255,255,0.10); color: var(--text); }
.btn-lg { padding: 14px 20px; font-size: 14.5px; border-radius: 14px; }
.btn-xl { padding: 16px; font-size: 15px; border-radius: 14px; width: 100%;
  justify-content: center; }

.row-flex { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }

/* ---------- inputs ---------- */
.input, .select {
  padding: 11px 14px; border-radius: 12px;
  background: rgba(10, 15, 30, 0.6);
  color: var(--text);
  border: 1px solid var(--card-border);
  font-size: 14px;
  transition: border 0.15s, box-shadow 0.15s;
}
.input:focus, .select:focus {
  border-color: rgba(34,197,94,0.6);
  box-shadow: 0 0 0 3px rgba(34,197,94,0.15);
}
.input.compact { padding: 9px 12px; font-size: 13px; }
.input-narrow { width: 74px; text-align: center; }
.tag-lbl { color: var(--muted); font-size: 12.5px; padding: 0 4px;
  font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }

/* ---------- chat list ---------- */
.chat-scroll { flex: 1; overflow-y: auto; padding: 6px 14px 10px; min-height: 0; }
.chat-row {
  display: flex; align-items: center; gap: 14px;
  padding: 12px 16px; border-radius: 14px;
  margin-bottom: 6px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid transparent;
  cursor: pointer; user-select: none;
  transition: background 0.15s, border 0.15s, transform 0.05s;
}
.chat-row:hover { background: rgba(255,255,255,0.07); border-color: var(--card-border); }
.chat-row.selected {
  background: rgba(34,197,94,0.13);
  border-color: rgba(34,197,94,0.45);
  box-shadow: inset 0 0 0 1px rgba(34,197,94,0.2);
}
.chat-row .cbx {
  width: 22px; height: 22px; border-radius: 7px;
  border: 2px solid #4a5878; flex-shrink: 0;
  display: grid; place-items: center;
  transition: background 0.15s, border-color 0.15s;
}
.chat-row.selected .cbx {
  background: var(--accent); border-color: var(--accent);
}
.chat-row.selected .cbx::after { content: '✓'; color: white; font-weight: 900; font-size: 14px; }
.avatar {
  width: 42px; height: 42px; border-radius: 50%;
  display: grid; place-items: center; color: white;
  font-weight: 800; font-size: 14px; flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  letter-spacing: 0.5px;
}
.chat-name { flex: 1; font-weight: 700; font-size: 14.5px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chat-tag {
  font-size: 10.5px; padding: 3px 9px; border-radius: 6px;
  background: rgba(148,163,184,0.15); color: var(--muted);
  font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
}
.chat-tag.group { background: rgba(168,85,247,0.16); color: #c084fc; }
.chat-tag.individual { background: rgba(6,182,212,0.16); color: #22d3ee; }
.chat-count { padding: 10px 22px 16px; color: var(--muted); font-size: 12.5px;
  border-top: 1px solid var(--card-border); }
.empty-state { padding: 70px 20px; text-align: center; color: var(--muted); font-size: 14px; }
.empty-state b { color: var(--text-2); }

/* ---------- tabs ---------- */
.tabs { display: flex; padding: 0 22px; border-bottom: 1px solid var(--card-border); }
.tab {
  padding: 14px 22px; cursor: pointer; color: var(--muted);
  font-weight: 700; font-size: 14px;
  border-bottom: 3px solid transparent;
  transition: color 0.15s, border-color 0.15s;
  display: flex; align-items: center; gap: 8px;
}
.tab:hover { color: var(--text-2); }
.tab.active { color: var(--accent); border-color: var(--accent); }
.right-panel { overflow-y: auto; padding: 16px 22px; min-height: 0; }
.right-panel h4 { padding: 4px 0; font-size: 14.5px; font-weight: 700;
  display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }

/* ---------- mode cards ---------- */
.mode-block { display: flex; flex-direction: column; gap: 8px; margin-bottom: 6px; }
.mode-item {
  display: flex; gap: 14px; align-items: flex-start;
  padding: 14px 16px; border-radius: 14px;
  background: rgba(255,255,255,0.03);
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.15s, border 0.15s;
}
.mode-item:hover { background: rgba(255,255,255,0.07); }
.mode-item.active {
  background: rgba(34,197,94,0.10);
  border-color: rgba(34,197,94,0.35);
  box-shadow: inset 0 0 0 1px rgba(34,197,94,0.15);
}
.mode-radio { width: 20px; height: 20px; border-radius: 50%;
  border: 2px solid #4a5878; flex-shrink: 0; margin-top: 2px;
  display: grid; place-items: center; }
.mode-item.active .mode-radio { border-color: var(--accent); }
.mode-item.active .mode-radio::after { content: '';
  width: 10px; height: 10px; border-radius: 50%; background: var(--accent); }
.mode-name { font-weight: 700; font-size: 14px; }
.mode-hint { color: var(--muted); font-size: 12.5px; margin-top: 4px; line-height: 1.4; }

/* ---------- toggles ---------- */
.toggle-row {
  display: flex; gap: 14px; align-items: flex-start;
  padding: 14px 16px; border-radius: 14px;
  background: rgba(255,255,255,0.03);
  cursor: pointer; margin-bottom: 8px;
  transition: background 0.15s;
}
.toggle-row:hover { background: rgba(255,255,255,0.07); }
.toggle-box { width: 22px; height: 22px; border-radius: 7px;
  border: 2px solid #4a5878; flex-shrink: 0; margin-top: 1px;
  display: grid; place-items: center; transition: background 0.15s, border-color 0.15s; }
.toggle-row.on .toggle-box { background: var(--accent); border-color: var(--accent); }
.toggle-row.on .toggle-box::after { content: '✓'; color: white; font-weight: 900; font-size: 14px; }
.toggle-name { font-weight: 700; font-size: 14px; }
.toggle-hint { color: var(--muted); font-size: 12.5px; margin-top: 4px; line-height: 1.4; }

/* ---------- progress ---------- */
.prog-outer { height: 8px; background: rgba(255,255,255,0.06);
  border-radius: 5px; overflow: hidden; margin-top: 14px;
  border: 1px solid var(--card-border); }
.prog-inner { height: 100%; width: 0%;
  background: linear-gradient(90deg, #16a34a, #22c55e, #06b6d4);
  transition: width 0.25s;
  box-shadow: 0 0 12px rgba(34,197,94,0.55); }

/* ---------- log ---------- */
.log-card {
  background: rgba(3, 6, 15, 0.85);
  max-height: 200px;
}
.log-body { flex: 1; overflow-y: auto; padding: 12px 22px;
  font-family: "Cascadia Mono", Consolas, monospace;
  font-size: 12.5px; line-height: 1.55; }
.log-line { padding: 2px 0; white-space: pre-wrap; word-break: break-word; }
.log-info { color: #cbd5e1; }
.log-ok   { color: #4ade80; }
.log-err  { color: #f87171; }
.log-warn { color: #fbbf24; }
</style>
</head>
<body>
<div class="shell">

  <!-- ============== sidebar ============== -->
  <aside class="side">
    <div class="logo">💬</div>
    <div class="nav active" title="Chats">🧹</div>
    <div class="nav" title="Backups" onclick="api('open_backups')">📁</div>
    <div class="spacer"></div>
    <div class="nav" title="About">ℹ️</div>
  </aside>

  <!-- ============== main ============== -->
  <main>

    <!-- top -->
    <header class="top">
      <div>
        <div class="title">H.D.Nakarani &amp; Associates</div>
        <div class="subtitle">WhatsApp Cleaner — clears message history; individual chat threads can be removed on request.</div>
      </div>
      <div id="status" class="pill">
        <span class="dot"></span>
        <span id="statusText">Not connected</span>
      </div>
    </header>

    <!-- metric tiles -->
    <section class="metrics">
      <div class="tile a">
        <div class="icon">💬</div>
        <div><div class="k">Chats loaded</div><div class="v" id="mTotal">0</div></div>
      </div>
      <div class="tile b">
        <div class="icon">👥</div>
        <div><div class="k">Groups</div><div class="v" id="mGroups">0</div></div>
      </div>
      <div class="tile c">
        <div class="icon">👤</div>
        <div><div class="k">Individuals</div><div class="v" id="mIndiv">0</div></div>
      </div>
      <div class="tile d">
        <div class="icon">✓</div>
        <div><div class="k">Selected</div><div class="v" id="mSel">0</div></div>
      </div>
    </section>

    <!-- body -->
    <section class="body">

      <!-- chats card -->
      <div class="card">
        <div class="card-head">💬 &nbsp;Chats</div>
        <div class="card-body row-flex">
          <button class="btn btn-green btn-lg" onclick="reload('All chats')">🔗 Reload All</button>
          <button class="btn btn-purple btn-lg" onclick="reload('Groups only')">👥 Groups</button>
          <button class="btn btn-cyan btn-lg" onclick="reload('Individuals only')">👤 Individuals</button>
        </div>
        <div class="card-body row-flex" style="padding-top:0;">
          <button class="btn btn-blue" onclick="toggleAll(true)">Select all</button>
          <button class="btn btn-ghost" onclick="toggleAll(false)">None</button>
          <button class="btn btn-ghost" onclick="verifyTypes()" title="Open each chat's menu to accurately classify group vs individual (slow, but 100% correct)">🔍 Verify types</button>
          <span class="tag-lbl">Sort</span>
          <select class="select input compact" id="sort" onchange="renderChats()">
            <option>Order loaded</option>
            <option>Name (A→Z)</option>
            <option>Name (Z→A)</option>
          </select>
          <span class="tag-lbl">Max</span>
          <input class="input input-narrow compact" id="maxLoad" type="number" value="50" min="5" max="9999">
          <button class="btn btn-orange" onclick="loadAll()">Load ALL</button>
        </div>
        <div class="card-body" style="padding-top:0;">
          <input class="input" id="search" placeholder="🔎  Search chats…" style="width:100%;">
        </div>
        <div class="chat-scroll" id="chatList">
          <div class="empty-state">Click <b>Reload All</b> to fetch your WhatsApp chats.</div>
        </div>
        <div class="chat-count" id="chatCount">Not connected</div>
      </div>

      <!-- action card -->
      <div class="card">
        <div class="tabs">
          <div class="tab active" id="tabClean" onclick="showTab('clean')">🧹 Clean</div>
          <div class="tab" id="tabExport" onclick="showTab('export')">📤 Export</div>
        </div>

        <!-- clean panel -->
        <div class="right-panel" id="panelClean">
          <h4>🎯 What to clear</h4>
          <div class="mode-block" id="modes"></div>
          <div id="modeCtrls" style="margin-top:12px;"></div>

          <h4 style="margin-top:20px;">🛡️ Safety</h4>
          <div class="toggle-row on" id="tg-groupsOnly" data-key="groupsOnly">
            <div class="toggle-box"></div>
            <div>
              <div class="toggle-name">Groups only</div>
              <div class="toggle-hint">Skips personal chats — verified via the chat's own menu before clearing.</div>
            </div>
          </div>
          <div class="toggle-row on" id="tg-backup" data-key="backup">
            <div class="toggle-box"></div>
            <div>
              <div class="toggle-name">Backup to JSON before clearing</div>
              <div class="toggle-hint">Snapshot of affected messages saved to exports\\ before any deletion.</div>
            </div>
          </div>

          <h4 style="margin-top:20px;">⚡ Run</h4>
          <button class="btn btn-green btn-xl" id="btnRun" onclick="startClean()" disabled>▶ Run cleanup</button>
          <button class="btn btn-red btn-xl" id="btnStop" onclick="api('stop')" disabled style="margin-top:10px;">■ Cancel</button>
          <div class="prog-outer"><div class="prog-inner" id="prog"></div></div>
        </div>

        <!-- export panel -->
        <div class="right-panel" id="panelExport" style="display:none;">
          <h4>ℹ️ About export</h4>
          <div style="color:var(--muted); font-size:13px; line-height:1.55; margin-bottom:18px;">
            Uses WhatsApp's own <b>Export chat</b> action. Text-only is fast; media downloads a .zip with attachments.<br><br>
            You'll be asked where to save.
          </div>

          <h4>🎞️ Media</h4>
          <div class="toggle-row" id="tg-withMedia" data-key="withMedia">
            <div class="toggle-box"></div>
            <div>
              <div class="toggle-name">Include media</div>
              <div class="toggle-hint">Unchecked = text-only export (fast, small).</div>
            </div>
          </div>

          <h4 style="margin-top:20px;">⚡ Run</h4>
          <button class="btn btn-blue btn-xl" id="btnExport" onclick="startExport()" disabled>📤 Choose folder & export…</button>
          <button class="btn btn-red btn-xl" id="btnStopExport" onclick="api('stop')" disabled style="margin-top:10px;">■ Cancel</button>
        </div>
      </div>

    </section>

    <!-- log -->
    <div class="card log-card">
      <div class="card-head">📜 &nbsp;Activity</div>
      <div class="log-body" id="log">
        <div class="log-line log-info">Ready. Click Reload All to open WhatsApp Web.</div>
      </div>
    </div>

  </main>
</div>

<script>
// ---------------- state ----------------
const modes = [
  ["All history",         "All history",  "Everything in the chat."],
  ["Newest N messages",   "Last N",       "Delete the N most recent messages."],
  ["Oldest N (of loaded)","First N",      "Fast — deletes the oldest N of what is currently visible."],
  ["Oldest N (from top)", "First N true", "Slower — scrolls to the actual top first, then deletes the true oldest N."],
  ["Older than a date",   "Older than",   "Deletes messages older than the cutoff. Loads history first — can take a while on large groups."],
  ["Clear + delete thread (individuals only)", "Delete thread",
   "Clears all history AND removes the chat thread from your sidebar. Only runs on individual chats — groups are skipped for safety. Requires a Verify pass first if types are unknown."],
];
let selectedMode = 0;
let chats = [];              // [{name, kind}]
let selected = new Set();
let kindFilter = "All chats";
let toggles = { groupsOnly: true, backup: true, withMedia: false };

// ---------------- helpers ----------------
const $ = id => document.getElementById(id);
const AVATAR = ["#0891b2","#059669","#7c3aed","#db2777","#ea580c","#ca8a04",
                "#dc2626","#4f46e5","#0284c7","#16a34a","#c026d3","#f97316",
                "#0d9488","#a21caf","#65a30d","#e11d48"];
function avatarColor(n){let h=0;for(const c of n)h+=c.charCodeAt(0);return AVATAR[h%AVATAR.length];}
function avatarInit(n){const p=n.trim().split(/\s+/).filter(Boolean);
  if(!p.length)return "?"; if(p.length===1)return p[0].slice(0,2).toUpperCase();
  return (p[0][0]+p[p.length-1][0]).toUpperCase();}
function esc(s){return String(s).replace(/[&<>"']/g,
  c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function escAttr(s){return esc(s);}

// ---------------- API bridge ----------------
function api(method, ...args){
  if(!window.pywebview || !window.pywebview.api){
    console.error("pywebview API not ready"); return;
  }
  const fn = window.pywebview.api[method];
  if(!fn){ console.error("no api method", method); return; }
  return fn.apply(null, args);
}
function reload(kind){
  kindFilter = kind;
  api("reload", parseInt($("maxLoad").value)||50);
}
function loadAll(){ $("maxLoad").value = 5000; reload(kindFilter); }
function verifyTypes(){
  if(!chats.length){ alert("Load chats first."); return; }
  const names = chats.map(c => c.name);
  if(!confirm("Open each of "+names.length+" chat(s) to accurately classify group vs individual?\n\nThis is slow (a few seconds per chat) but gives correct results.")) return;
  api("verify", names);
}
function toggleAll(state){
  for(const c of getFiltered()){ if(state) selected.add(c.name); else selected.delete(c.name); }
  renderChats();
}
function toggleChat(name){
  if(selected.has(name)) selected.delete(name); else selected.add(name);
  renderChats();
}

// toggle-row (safety checkboxes) — event delegation
document.addEventListener("click", function(e){
  const tg = e.target.closest(".toggle-row");
  if(!tg) return;
  const key = tg.dataset.key; if(!key) return;
  toggles[key] = !toggles[key];
  tg.classList.toggle("on", toggles[key]);
});

// ---------------- chat list ----------------
function effectiveKind(c){
  if(c.kind && c.kind !== "unknown") return c.kind;
  // heuristic: phone-number-shaped names classify as individual
  if(/^[\+\d\s\-\(\)]{6,}$/.test((c.name||"").trim())) return "individual";
  return "unknown";
}
function getFiltered(){
  const q = ($("search").value||"").toLowerCase().trim();
  let list = chats.filter(c => {
    if(q && !c.name.toLowerCase().includes(q)) return false;
    const k = effectiveKind(c);
    if(kindFilter === "Groups only" && k === "individual") return false;
    if(kindFilter === "Individuals only" && k !== "individual") return false;
    return true;
  });
  const sort = $("sort").value;
  if(sort === "Name (A→Z)") list = list.slice().sort((a,b)=>a.name.localeCompare(b.name));
  else if(sort === "Name (Z→A)") list = list.slice().sort((a,b)=>b.name.localeCompare(a.name));
  return list;
}
function renderChats(){
  const list = getFiltered();
  const el = $("chatList");
  if(!chats.length){
    el.innerHTML = '<div class="empty-state">Click <b>Reload All</b> to fetch your WhatsApp chats.</div>';
  } else if(!list.length){
    el.innerHTML = '<div class="empty-state">No chats match this filter / search.</div>';
  } else {
    el.innerHTML = list.map(c => {
      const kind = c.kind || "unknown";
      const kindLabel = kind === "group" ? "group" : kind === "individual" ? "individual" : "";
      const tag = kindLabel ? `<span class="chat-tag ${kind}">${kindLabel}</span>` : "";
      const sel = selected.has(c.name) ? "selected" : "";
      return `<div class="chat-row ${sel}" data-name="${escAttr(c.name)}">
        <div class="cbx"></div>
        <div class="avatar" style="background:${avatarColor(c.name)}">${esc(avatarInit(c.name))}</div>
        <div class="chat-name">${esc(c.name)}</div>
        ${tag}
      </div>`;
    }).join("");
  }
  updateCounts();
}
function updateCounts(){
  const list = getFiltered();
  const total = chats.length;
  const groups = chats.filter(c => effectiveKind(c) === "group").length;
  const indiv = chats.filter(c => effectiveKind(c) === "individual").length;
  $("mTotal").textContent  = total;
  $("mGroups").textContent = groups;
  $("mIndiv").textContent  = indiv;
  $("mSel").textContent    = selected.size;
  $("chatCount").textContent = total
    ? `${list.length} shown · ${selected.size} selected · ${total} total`
    : "Not connected";
}
// event delegation for row clicks — reliable regardless of chat name content
$("chatList").addEventListener("click", function(e){
  const row = e.target.closest(".chat-row");
  if(!row) return;
  const name = row.dataset.name;
  if(name) toggleChat(name);
});
$("search").addEventListener("input", renderChats);

// ---------------- modes ----------------
function renderModes(){
  $("modes").innerHTML = modes.map((m,i) => `
    <div class="mode-item ${i===selectedMode?'active':''}" onclick="setMode(${i})">
      <div class="mode-radio"></div>
      <div>
        <div class="mode-name">${m[0]}</div>
        <div class="mode-hint">${m[2]}</div>
      </div>
    </div>`).join("");
  renderModeCtrls();
}
function setMode(i){ selectedMode = i; renderModes(); }
function renderModeCtrls(){
  const v = modes[selectedMode][1];
  const el = $("modeCtrls");
  if(["Last N","First N","First N true"].includes(v)){
    el.innerHTML = `<label class="row-flex"><span class="tag-lbl">N =</span>
      <input class="input compact" id="nVal" type="number" value="5" min="1" max="9999" style="width:100px;"></label>`;
  } else if(v === "Older than"){
    const d = new Date(); d.setDate(1);
    const s = d.toISOString().slice(0,10);
    el.innerHTML = `<label class="row-flex"><span class="tag-lbl">Cutoff:</span>
      <input class="input compact" id="dateVal" type="date" value="${s}" style="width:180px;"></label>`;
  } else {
    el.innerHTML = "";
  }
}

// ---------------- tabs ----------------
function showTab(t){
  $("tabClean").classList.toggle("active", t==="clean");
  $("tabExport").classList.toggle("active", t==="export");
  $("panelClean").style.display  = t==="clean" ? "block" : "none";
  $("panelExport").style.display = t==="export"? "block" : "none";
}

// ---------------- run/export ----------------
function startClean(){
  const picked = Array.from(selected);
  if(!picked.length){ alert("Tick at least one chat."); return; }
  const mode = modes[selectedMode][1];
  if(mode === "Delete thread"){
    // extra confirmation because this actually removes chat threads
    const msg2 = "You are about to CLEAR HISTORY and then DELETE THE CHAT "+
                 "THREAD for "+picked.length+" chat(s).\n\n"+
                 "This ONLY runs on individual chats — group chats are "+
                 "automatically skipped.\n\n"+
                 "The deleted threads are removed from your sidebar. "+
                 "Contacts are NOT blocked or deleted. Other party still "+
                 "keeps their copy.\n\nProceed?";
    if(!confirm(msg2)) return;
    $("btnRun").disabled = true;
    $("btnStop").disabled = false;
    $("prog").style.width = "0%";
    api("delete_threads", {groups: picked, backup: toggles.backup});
    return;
  }
  let n = 5, cutoff = null;
  const nEl = $("nVal");   if(nEl) n = parseInt(nEl.value)||5;
  const dEl = $("dateVal");if(dEl) cutoff = dEl.value;
  const msg = "This will permanently clear message history in "+picked.length+
              " chat(s).\n\nMode: "+mode+"\nGroups NOT deleted. Others keep their copies.\n\nProceed?";
  if(!confirm(msg)) return;
  $("btnRun").disabled = true;
  $("btnStop").disabled = false;
  $("prog").style.width = "0%";
  api("clean", {groups: picked, mode: mode, n: n, cutoff: cutoff,
    backup: toggles.backup, groups_only: toggles.groupsOnly});
}
function startExport(){
  const picked = Array.from(selected);
  if(!picked.length){ alert("Tick at least one chat."); return; }
  $("btnExport").disabled = true;
  $("btnStopExport").disabled = false;
  $("prog").style.width = "0%";
  api("export_chats", {groups: picked, with_media: toggles.withMedia});
}

// ---------------- events from Python ----------------
window.onEvent = function(evt){
  if(evt.type === "log"){
    const line = document.createElement("div");
    line.className = "log-line log-"+(evt.kind||"info");
    line.textContent = evt.msg;
    $("log").appendChild(line);
    $("log").scrollTop = $("log").scrollHeight;
  } else if(evt.type === "status"){
    const p = $("status");
    p.className = "pill "+(evt.cls||"");
    $("statusText").textContent = evt.text;
  } else if(evt.type === "groups"){
    chats = evt.items || [];
    selected = new Set();
    renderChats();
    $("btnRun").disabled = false;
    $("btnExport").disabled = false;
    $("btnStop").disabled = true;
    $("btnStopExport").disabled = true;
    try { window.focus(); } catch(_){}
  } else if(evt.type === "kind"){
    // per-chat classification update from Verify pass
    for(const c of chats){
      if(c.name === evt.name){ c.kind = evt.kind; break; }
    }
    renderChats();
  } else if(evt.type === "progress"){
    const pct = evt.total ? (100*evt.i/evt.total) : 0;
    $("prog").style.width = pct+"%";
  } else if(evt.type === "done"){
    $("btnRun").disabled = false;
    $("btnExport").disabled = false;
    $("btnStop").disabled = true;
    $("btnStopExport").disabled = true;
    setTimeout(()=>{$("prog").style.width = "0%";}, 900);
  }
};

renderModes();
renderChats();
</script>
</body>
</html>"""


class Api:
    """JS-visible surface. All methods run on pywebview's worker thread —
    they must push work to the Playwright worker via the jobs queue, not
    block on it."""

    def __init__(self):
        self.jobs = queue.Queue()
        self.out = queue.Queue()
        self.worker = None
        self.window = None
        self._started = False

    def _start_worker_if_needed(self):
        if self.worker is not None:
            return
        self.worker = Worker(self.jobs, self.out)
        self.worker.start()
        self._push("status", cls="busy", text="Connecting…")

    def reload(self, limit):
        try:
            limit = int(limit)
        except Exception:
            limit = DEFAULT_MAX_GROUPS
        self._start_worker_if_needed()
        self.jobs.put({"type": "groups", "limit": limit})

    def clean(self, params):
        cutoff = None
        if params.get("cutoff"):
            try:
                cutoff = datetime.strptime(
                    params["cutoff"], "%Y-%m-%d").date()
            except Exception:
                cutoff = None
        self._start_worker_if_needed()
        self.jobs.put({
            "type": "clear",
            "groups": params.get("groups", []),
            "mode":   params.get("mode", "All history"),
            "n":      int(params.get("n", 5) or 5),
            "dry":    False,
            "backup": bool(params.get("backup", True)),
            "groups_only": bool(params.get("groups_only", True)),
            "cutoff": cutoff,
        })

    def export_chats(self, params):
        # native folder picker
        dest = None
        try:
            r = self.window.create_file_dialog(webview.FOLDER_DIALOG)
            if r:
                dest = r[0] if isinstance(r, (list, tuple)) else r
        except Exception as e:
            self._push("log", msg=f"folder picker failed: {e}", kind="err")
            self._push("done")
            return
        if not dest:
            self._push("log", msg="export cancelled — no folder chosen",
                       kind="warn")
            self._push("done")
            return
        self._start_worker_if_needed()
        self.jobs.put({
            "type": "export",
            "groups": params.get("groups", []),
            "dest":   dest,
            "with_media": bool(params.get("with_media", False)),
            "groups_only": True,
        })

    def verify(self, names):
        if not names: return
        self._start_worker_if_needed()
        self.jobs.put({"type": "verify", "groups": list(names)})

    def delete_threads(self, params):
        self._start_worker_if_needed()
        self.jobs.put({
            "type": "delete_threads",
            "groups": params.get("groups", []),
            "backup": bool(params.get("backup", True)),
        })

    def stop(self):
        if self.worker:
            self.worker.cancel.set()
            self._push("log", msg="Cancelling after the current chat…",
                       kind="warn")

    def open_backups(self):
        try:
            EXPORT_DIR.mkdir(exist_ok=True)
            os.startfile(str(EXPORT_DIR))
        except Exception as e:
            self._push("log", msg=f"could not open backups: {e}", kind="err")

    def _push(self, kind, **fields):
        """Called on any thread — schedule a JS event."""
        payload = dict(fields)
        payload["type"] = kind
        if self.window is None:
            return
        try:
            self.window.evaluate_js(
                f"window.onEvent && window.onEvent({json.dumps(payload)});"
            )
        except Exception:
            pass


def _pump_thread(api):
    """Drain worker output queue and push each event to JS."""
    while True:
        try:
            tag, payload, kind = api.out.get()
        except Exception:
            time.sleep(0.1); continue
        try:
            if tag == "log":
                api._push("log", msg=str(payload), kind=kind)
            elif tag == "ready":
                api._push("status", cls="connected", text="Connected")
            elif tag == "groups":
                items = []
                for it in (payload or []):
                    if isinstance(it, str):
                        items.append({"name": it, "kind": "unknown"})
                    else:
                        items.append({
                            "name": it.get("name", ""),
                            "kind": it.get("kind", "unknown"),
                        })
                api._push("groups", items=items)
                # Bring the tool window to the front so activity is visible
                # (Edge/WhatsApp Web often sits on top after login).
                try:
                    if api.window is not None:
                        api.window.on_top = True
                        threading.Timer(
                            0.6,
                            lambda: setattr(api.window, "on_top", False)
                        ).start()
                except Exception:
                    pass
            elif tag == "kind":
                name, k = payload
                api._push("kind", name=name, kind=k)
            elif tag == "progress":
                i, total = payload
                api._push("progress", i=int(i), total=int(total))
            elif tag == "done":
                api._push("done")
            elif tag == "dead":
                api._push("status", cls="dead", text="Disconnected")
        except Exception:
            pass


def start_app():
    api = Api()
    window = webview.create_window(
        title="H.D.Nakarani & Associates — WhatsApp Cleaner",
        html=HTML,
        js_api=api,
        width=1320, height=920,
        min_size=(1120, 780),
        background_color="#0b1220",
    )
    api.window = window
    threading.Thread(target=_pump_thread, args=(api,), daemon=True).start()
    webview.start(debug=False)


if __name__ == "__main__":
    start_app()
