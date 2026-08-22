import csv
import json
import logging
import os
import re
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
DEFAULT_URL = "https://servicesepc.org/home/listVendors?sector_id=8&term=A"
DEFAULT_DELAY = 1.2
DEFAULT_RETRIES = 3
DEFAULT_TIMEOUT = 30000

COLUMNS = [
    "Company/Organization Name",
    "City",
    "State",
    "Senior Officer",
    "Mobile Number",
    "Email ID",
    "Source URL",
    "Industry/Sector",
    "Alphabet",
]


def clean(value):
    if value is None:
        return ""
    value = re.sub(r"\s+", " ", str(value)).strip()
    return value


def normalize_label(value):
    value = clean(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def canonical_url(url):
    try:
        p = urlparse(url)
        return urlunparse((p.scheme, p.netloc, p.path, "", p.query, ""))
    except Exception:
        return url


def build_listing_url(base_url, sector_id, letter):
    p = urlparse(base_url)
    q = parse_qs(p.query)
    if sector_id:
        q["sector_id"] = [str(sector_id)]
    q["term"] = [letter]
    return urlunparse((p.scheme, p.netloc, p.path or "/home/listVendors", "", urlencode(q, doseq=True), ""))


class Store:
    """SQLite checkpoint store. It makes the scraper resumable."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.db_path = self.folder / "sepc_progress.sqlite3"
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._create()

    def _create(self):
        with self.lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    key TEXT PRIMARY KEY,
                    company TEXT,
                    city TEXT,
                    state TEXT,
                    senior_officer TEXT,
                    mobile TEXT,
                    email TEXT,
                    source_url TEXT,
                    sector TEXT,
                    alphabet TEXT,
                    status TEXT,
                    error TEXT,
                    scraped_at TEXT
                )
            """)
            self.conn.commit()

    def key_for(self, url, company, letter):
        return canonical_url(url) if url else f"{letter}|{normalize_label(company)}"

    def get_status(self, key):
        with self.lock:
            row = self.conn.execute("SELECT status FROM records WHERE key=?", (key,)).fetchone()
            return row[0] if row else None

    def save(self, data, status="success", error=""):
        key = self.key_for(data.get("source_url", ""), data.get("company", ""), data.get("alphabet", ""))
        with self.lock:
            self.conn.execute("""
                INSERT INTO records
                (key, company, city, state, senior_officer, mobile, email,
                 source_url, sector, alphabet, status, error, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    company=excluded.company,
                    city=excluded.city,
                    state=excluded.state,
                    senior_officer=excluded.senior_officer,
                    mobile=excluded.mobile,
                    email=excluded.email,
                    source_url=excluded.source_url,
                    sector=excluded.sector,
                    alphabet=excluded.alphabet,
                    status=excluded.status,
                    error=excluded.error,
                    scraped_at=excluded.scraped_at
            """, (
                key, data.get("company", ""), data.get("city", ""),
                data.get("state", ""), data.get("senior_officer", ""),
                data.get("mobile", ""), data.get("email", ""),
                data.get("source_url", ""), data.get("sector", ""),
                data.get("alphabet", ""), status, error, now_iso()
            ))
            self.conn.commit()

    def all_rows(self):
        with self.lock:
            rows = self.conn.execute("""
                SELECT company, city, state, senior_officer, mobile, email,
                       source_url, sector, alphabet
                FROM records
                WHERE status='success'
                ORDER BY rowid
            """).fetchall()
        return rows

    def errors(self):
        with self.lock:
            return self.conn.execute("""
                SELECT company, source_url, sector, alphabet, error, scraped_at
                FROM records
                WHERE status='error'
                ORDER BY rowid
            """).fetchall()

    def close(self):
        with self.lock:
            self.conn.close()


class SEPCScraper:
    def __init__(self, config, log_callback, progress_callback, stop_event):
        self.cfg = config
        self.log = log_callback
        self.progress = progress_callback
        self.stop_event = stop_event
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.store = Store(config["output_folder"])

    def logmsg(self, msg):
        self.log(msg)

    def setup(self):
        self.pw = sync_playwright().start()
        browser_name = self.cfg.get("browser", "chromium")
        launcher = getattr(self.pw, browser_name)
        self.browser = launcher.launch(
            headless=self.cfg.get("headless", False),
            args=["--disable-blink-features=AutomationControlled"],
        )
        self.context = self.browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=False,
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.cfg.get("timeout", DEFAULT_TIMEOUT))

    def close(self):
        try:
            if self.context:
                self.context.close()
        finally:
            if self.browser:
                self.browser.close()
            if self.pw:
                self.pw.stop()
            self.store.close()

    def initial_page(self):
        self.page.goto(self.cfg["url"], wait_until="domcontentloaded")
        self.page.wait_for_load_state("networkidle", timeout=15000)
        self.page.wait_for_timeout(700)

    def discover_sector_options(self):
        """Read the real <select> options. No sector IDs are hard-coded."""
        options = self.page.locator("select option").evaluate_all(
            """els => els.map(o => ({text:(o.textContent||'').trim(), value:o.value}))"""
        )
        return [x for x in options if clean(x["text"]) and clean(x["value"])]

    def sector_id_from_current_url(self):
        q = parse_qs(urlparse(self.cfg["url"]).query)
        return (q.get("sector_id") or [""])[0]

    def select_sector(self, sector_text):
        selects = self.page.locator("select")
        count = selects.count()
        if count == 0:
            self.logmsg("No HTML <select> found; using sector_id from the URL.")
            return self.sector_id_from_current_url()

        # Prefer the select containing the sector option text.
        for i in range(count):
            sel = selects.nth(i)
            opts = sel.locator("option").all_text_contents()
            joined = " | ".join(opts).lower()
            if "accounting" in joined or "services" in joined or sector_text.lower() in joined:
                for j in range(sel.locator("option").count()):
                    opt = sel.locator("option").nth(j)
                    text = clean(opt.text_content())
                    if text.lower() == sector_text.lower():
                        value = opt.get_attribute("value") or ""
                        sel.select_option(value=value)
                        self.page.wait_for_timeout(1000)
                        return value
        return self.sector_id_from_current_url()

    def discover_sector_options_from_url(self):
        try:
            self.initial_page()
            return self.discover_sector_options()
        except Exception:
            return []

    def listing_url(self, sector_id, letter):
        return build_listing_url(self.cfg["url"], sector_id, letter)

    def wait_listing(self, letter):
        # Wait for heading and the member area to exist.
        self.page.wait_for_load_state("domcontentloaded")
        try:
            self.page.get_by_text("Members are listed/sorted from A to Z", exact=False).first.wait_for(
                state="visible", timeout=self.cfg.get("timeout", DEFAULT_TIMEOUT)
            )
        except Exception:
            pass
        self.page.wait_for_timeout(600)

    def discover_entities(self, letter):
        """
        Discover actual anchors/buttons from the member area. The DOM order is
        retained, which normally corresponds to left-to-right row order in a
        CSS grid. Alphabet navigation and site chrome are excluded.
        """
        candidates = self.page.locator(
            "main a, main button, #content a, #content button, "
            ".container a, .container button"
        )
        n = candidates.count()
        found = []
        seen = set()

        # First pass: clickable anchors/buttons with meaningful text.
        for i in range(n):
            el = candidates.nth(i)
            try:
                text = clean(el.inner_text(timeout=1500))
                if not text or len(text) > 180:
                    continue
                href = el.get_attribute("href") or ""
                onclick = el.get_attribute("onclick") or ""
                cls = (el.get_attribute("class") or "").lower()
                ident = (el.get_attribute("id") or "").lower()

                # Exclude alphabet controls, navigation, footer, social links.
                if text.upper() in set(LETTERS + ["#"]):
                    continue
                if any(x in (cls + " " + ident + " " + onclick).lower()
                       for x in ["navbar", "menu", "footer", "social", "alphabet"]):
                    continue

                # Entity candidates are most reliably identified by links that
                # either have an href to another SEPC page or invoke a profile.
                same_host = False
                abs_url = ""
                if href and not href.startswith(("javascript:", "#", "mailto:", "tel:")):
                    abs_url = urljoin(self.page.url, href)
                    same_host = urlparse(abs_url).netloc == urlparse(self.page.url).netloc

                profileish = any(word in (cls + " " + ident + " " + onclick).lower()
                                 for word in ["vendor", "member", "company", "profile", "view"])
                if same_host or profileish or "company" in text.lower():
                    key = canonical_url(abs_url) if abs_url else f"{letter}|{normalize_label(text)}"
                    if key not in seen:
                        seen.add(key)
                        found.append({"name": text, "url": abs_url, "key": key})
            except Exception:
                continue

        # If broad selectors missed the member cards, inspect links globally
        # but only in the region following the "Following are the members..." text.
        if len(found) == 0:
            all_links = self.page.locator("a")
            for i in range(all_links.count()):
                el = all_links.nth(i)
                try:
                    text = clean(el.inner_text(timeout=1000))
                    href = el.get_attribute("href") or ""
                    if not text or text.upper() in set(LETTERS + ["#"]):
                        continue
                    if href and "listVendors" not in href and urlparse(urljoin(self.page.url, href)).netloc == urlparse(self.page.url).netloc:
                        key = canonical_url(urljoin(self.page.url, href))
                        if key not in seen:
                            seen.add(key)
                            found.append({"name": text, "url": urljoin(self.page.url, href), "key": key})
                except Exception:
                    pass

        return found

    def open_entity(self, entity):
        """
        Prefer a real href. If the site uses a JS modal/AJAX profile instead,
        click the element matching the discovered text and inspect the visible
        COMPANY PROFILE/modal content.
        """
        if entity["url"]:
            self.page.goto(entity["url"], wait_until="domcontentloaded")
            try:
                self.page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            self.page.wait_for_timeout(500)
            return self.page.url

        # Modal fallback: find exact text and click.
        loc = self.page.get_by_text(entity["name"], exact=True).first
        loc.scroll_into_view_if_needed()
        loc.click(timeout=self.cfg.get("timeout", DEFAULT_TIMEOUT))
        self.page.wait_for_timeout(800)
        return self.page.url

    def visible_text(self):
        try:
            return clean(self.page.locator("body").inner_text(timeout=5000))
        except Exception:
            return ""

    def _dom_label_value(self, aliases):
        """Extract a value from the smallest DOM element that contains
        `Label: Value`. This is important on SEPC because the detail page
        displays each field as its own bullet/list item. Looking at a large
        parent/container can accidentally return the entire company profile.
        """
        aliases = [normalize_label(a) for a in aliases]
        # Find the smallest visible element whose complete text starts with
        # one of the requested labels. The size limit prevents selecting a
        # whole card/container containing every company field.
        script = r"""
        (aliases) => {
          const norm = s => (s || '').replace(/\s+/g, ' ').trim()
            .toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
          const nodes = Array.from(document.querySelectorAll(
            'li, p, dt, dd, td, th, label, div, span, strong, b, a'
          ));
          const candidates = [];
          for (const el of nodes) {
            if (!el || !el.offsetParent) continue;
            const raw = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
            if (!raw || raw.length > 500) continue;
            const n = norm(raw);
            for (const alias of aliases) {
              const a = norm(alias);
              // Match Label: value or Label - value.
              const re = new RegExp('^' + a + '\\s*[:\\-]\\s*(.+)$', 'i');
              const m = raw.match(re);
              if (m && m[1] && m[1].trim()) {
                candidates.push({len: raw.length, value: m[1].trim()});
                break;
              }
              // Some pages render the label and value as separate children.
              if (n === a && el.nextElementSibling) {
                const v = (el.nextElementSibling.innerText || '').replace(/\s+/g, ' ').trim();
                if (v) candidates.push({len: raw.length + v.length, value: v});
              }
            }
          }
          candidates.sort((x,y) => x.len-y.len);
          return candidates.length ? candidates[0].value : '';
        }
        """
        try:
            return clean(self.page.evaluate(script, aliases))
        except Exception:
            return ""

    def _label_from_list_items(self, aliases):
        """Second targeted strategy: inspect individual list/paragraph items,
        never the whole profile container."""
        aliases = [normalize_label(a) for a in aliases]
        try:
            nodes = self.page.locator('li, p, dt, dd, tr, label')
            for i in range(nodes.count()):
                raw = clean(nodes.nth(i).inner_text())
                if not raw or len(raw) > 500:
                    continue
                n = normalize_label(raw)
                for alias in aliases:
                    # exact beginning of the field label
                    if re.match(r'^' + re.escape(alias) + r'\s*[:\-]\s*', n, re.I):
                        m = re.match(r'^\s*' + re.escape(alias) + r'\s*[:\-]\s*(.+?)\s*$', raw, re.I)
                        if m:
                            return clean(m.group(1))
                # Table row: Label | Value
                cells = nodes.nth(i).locator('th,td')
                if cells.count() >= 2:
                    label = normalize_label(cells.nth(0).inner_text())
                    if any(label == a or label.startswith(a + ' ') for a in aliases):
                        return clean(cells.nth(1).inner_text())
        except Exception:
            pass
        return ""

    def _email_from_dom(self):
        try:
            links = self.page.locator('a[href^="mailto:"]')
            for i in range(links.count()):
                href = links.nth(i).get_attribute('href') or ''
                m = re.search(r'mailto:([^?]+)', href, re.I)
                if m and m.group(1).strip():
                    return clean(m.group(1))
        except Exception:
            pass
        return ""

    def _fallback_line_field(self, text, aliases, next_labels):
        """Line-based fallback, but only when a label and its value are in the
        same line. It deliberately does NOT return the next arbitrary line,
        which was the cause of the old scraper capturing the whole profile."""
        aliases_re = '|'.join(re.escape(a) for a in aliases)
        next_re = '|'.join(re.escape(a) for a in next_labels)
        # First try line-by-line so unrelated profile text cannot bleed in.
        for line in text.splitlines():
            line = clean(line)
            if not line:
                continue
            m = re.match(r'^\s*(?:' + aliases_re + r')\s*[:\-]\s*(.*?)\s*$', line, re.I)
            if m and clean(m.group(1)):
                return clean(m.group(1))
        # If the browser collapsed the list into one line, stop at the next
        # known field label.
        m = re.search(
            r'(?:^|\s)(?:' + aliases_re + r')\s*[:\-]\s*(.*?)\s+(?=(?:' + next_re + r')\s*[:\-])',
            text, re.I
        )
        return clean(m.group(1)) if m and clean(m.group(1)) else ""

    def extract_fields(self, fallback_company):
        """Extract only the six requested fields from the SEPC detail page.

        The SEPC page shown by the user renders fields as individual bullet
        items, e.g. `City: Kolkata`, `State: West Bengal`, `Name of Senior
        Officer: Atanu Sengupta`, `Mobile number: +91 ...`, and `Email id: ...`.
        We therefore target the individual DOM item first and use a tightly
        bounded regex fallback. We never use the whole profile container as a
        field value.
        """
        text = self.visible_text()

        def get(aliases):
            return (
                self._dom_label_value(aliases)
                or self._label_from_list_items(aliases)
            )

        company = get([
            'company/organization name', 'company / organization name',
            'company name', 'organization name', 'company', 'organization'
        ]) or fallback_company

        city = get(['city', 'town']) or self._fallback_line_field(
            text, ['city', 'town'],
            ['state', 'pincode', 'pin code', 'company telephone number',
             'telephone', 'mobile number', 'mobile', 'email id', 'email']
        )

        state = get(['state', 'state name', 'province']) or self._fallback_line_field(
            text, ['state', 'state name', 'province'],
            ['pincode', 'pin code', 'company telephone number', 'telephone',
             'brochure', 'name of senior officer', 'senior officer',
             'designation', 'mobile number', 'mobile', 'email id', 'email']
        )

        senior = get([
            'name of senior officer', 'senior officer name', 'senior officer',
            'contact person', 'key person'
        ]) or self._fallback_line_field(
            text, ['name of senior officer', 'senior officer'],
            ['designation', 'mobile number', 'mobile', 'email id', 'email']
        )

        mobile = get([
            'mobile number', 'mobile no.', 'mobile no', 'mobile',
            'contact number', 'telephone number', 'telephone', 'phone number', 'phone'
        ]) or self._fallback_line_field(
            text, ['mobile number', 'mobile no.', 'mobile no', 'mobile',
                   'contact number', 'telephone number', 'telephone', 'phone number', 'phone'],
            ['email id', 'email', 'company profile', 'quick links', 'about us']
        )

        email = get(['email id', 'email address', 'email', 'e mail id', 'e mail'])
        if not email:
            email = self._email_from_dom()
        if not email:
            # Email regex is safe because it only matches an email address,
            # unlike the previous broad body-text fallback.
            m = re.search(r'\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b', text, re.I)
            email = clean(m.group(0)) if m else ''

        return {
            'company': clean(company),
            'city': clean(city),
            'state': clean(state),
            'senior_officer': clean(senior),
            'mobile': clean(mobile),
            'email': clean(email),
        }

    def scrape_entity(self, entity, sector, letter):
        last_error = ""
        for attempt in range(1, self.cfg.get("retries", DEFAULT_RETRIES) + 1):
            if self.stop_event.is_set():
                raise InterruptedError
            try:
                source = self.open_entity(entity)
                data = self.extract_fields(entity["name"])
                data.update({
                    "source_url": source if source else entity["url"],
                    "sector": sector,
                    "alphabet": letter,
                })
                # A blank field is valid; the record is still successful.
                return data, ""
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                self.logmsg(f"  Attempt {attempt}/{self.cfg.get('retries', DEFAULT_RETRIES)} failed: {last_error}")
                if attempt < self.cfg.get("retries", DEFAULT_RETRIES):
                    time.sleep(1.5 * attempt)
        return None, last_error

    def export(self):
        rows = self.store.all_rows()
        data = pd.DataFrame(rows, columns=COLUMNS)
        xlsx = Path(self.cfg["output_folder"]) / "sepc_members.xlsx"
        csv_path = Path(self.cfg["output_folder"]) / "sepc_members.csv"
        errors_path = Path(self.cfg["output_folder"]) / "scraping_errors.csv"
        data.to_excel(xlsx, index=False)
        data.to_csv(csv_path, index=False, encoding="utf-8-sig")

        errors = self.store.errors()
        pd.DataFrame(
            errors,
            columns=["Company/Organization Name", "Source URL", "Industry/Sector",
                     "Alphabet", "Error", "Date/Time"]
        ).to_csv(errors_path, index=False, encoding="utf-8-sig")
        return xlsx, csv_path, errors_path, len(rows), len(errors)

    def run(self):
        try:
            self.setup()
            self.logmsg("Opening SEPC member directory...")
            self.initial_page()

            sector_options = self.discover_sector_options()
            self.logmsg(f"Discovered {len(sector_options)} sector options from the page.")
            sector = self.cfg["sector"]
            sector_id = self.cfg.get("sector_id") or self.sector_id_from_current_url()

            if sector and sector_options:
                matches = [o for o in sector_options if clean(o["text"]).lower() == sector.lower()]
                if matches:
                    sector_id = matches[0]["value"]

            if not sector_id:
                raise RuntimeError(
                    "Could not determine sector_id. Please open the directory URL containing sector_id or select a sector from the UI."
                )

            letters = self.cfg["letters"]
            processed = success = failed = skipped = 0

            for letter in letters:
                if self.stop_event.is_set():
                    break

                url = self.listing_url(sector_id, letter)
                self.logmsg(f"\nProcessing letter: {letter}")
                self.page.goto(url, wait_until="domcontentloaded")
                try:
                    self.page.wait_for_load_state("networkidle", timeout=12000)
                except Exception:
                    pass
                self.wait_listing(letter)

                entities = self.discover_entities(letter)
                self.logmsg(f"Found {len(entities)} entities")

                if self.cfg.get("test_mode"):
                    entities = entities[:self.cfg.get("test_count", 3)]
                    self.logmsg(f"TEST MODE: limiting this letter to first {len(entities)} entities.")

                for idx, entity in enumerate(entities, 1):
                    if self.stop_event.is_set():
                        break

                    processed += 1
                    existing = self.store.get_status(entity["key"])
                    if existing == "success" and self.cfg.get("resume", True):
                        skipped += 1
                        self.logmsg(f"[{idx}/{len(entities)}] Skipping completed: {entity['name']}")
                        continue

                    self.logmsg(f"[{idx}/{len(entities)}] Scraping: {entity['name']}")
                    data, error = self.scrape_entity(entity, sector, letter)

                    if data:
                        self.store.save(data, "success", "")
                        success += 1
                        self.logmsg("    ✓ saved")
                    else:
                        fail_data = {
                            "company": entity["name"],
                            "source_url": entity["url"],
                            "sector": sector,
                            "alphabet": letter,
                        }
                        self.store.save(fail_data, "error", error)
                        failed += 1
                        self.logmsg(f"    ✗ failed: {error}")

                    # Always return to the exact listing URL. This is more robust
                    # than relying on browser history after JS/AJAX navigation.
                    try:
                        self.page.goto(url, wait_until="domcontentloaded")
                        self.page.wait_for_timeout(500)
                    except Exception:
                        pass

                    self.progress(processed, success, failed, skipped)
                    time.sleep(float(self.cfg.get("delay", DEFAULT_DELAY)))

                self.logmsg(f"Letter {letter} completed.")

                if self.cfg.get("test_mode"):
                    break

            xlsx, csv_path, errors_path, total, err_count = self.export()
            self.progress(processed, success, failed, skipped)
            self.logmsg("\nFinished.")
            self.logmsg(f"Successful records: {total}")
            self.logmsg(f"Errors: {err_count}")
            self.logmsg(f"Excel: {xlsx}")
            self.logmsg(f"CSV:   {csv_path}")
            self.logmsg(f"Errors:{errors_path}")
        except InterruptedError:
            self.logmsg("\nStop requested. Progress has been checkpointed.")
            self.export()
        except Exception as exc:
            self.logmsg(f"\nFATAL ERROR: {type(exc).__name__}: {exc}")
            try:
                self.export()
            except Exception:
                pass
        finally:
            self.close()


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("SEPC Member Directory Scraper")
        self.root.geometry("980x720")
        self.root.minsize(900, 650)

        self.thread = None
        self.stop_event = threading.Event()
        self.sector_options = []

        self.url_var = tk.StringVar(value=DEFAULT_URL)
        self.sector_var = tk.StringVar()
        self.letter_mode = tk.StringVar(value="A-Z")
        self.single_letter = tk.StringVar(value="A")
        self.output_var = tk.StringVar(value=str(Path.cwd() / "sepc_output"))
        self.headless_var = tk.BooleanVar(value=False)
        self.resume_var = tk.BooleanVar(value=True)
        self.test_var = tk.BooleanVar(value=False)
        self.delay_var = tk.DoubleVar(value=DEFAULT_DELAY)
        self.retry_var = tk.IntVar(value=DEFAULT_RETRIES)

        self.build_ui()

    def build_ui(self):
        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="SEPC Member Directory Scraper", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(frm, text="Playwright-based • resumable • Excel/CSV export").pack(anchor="w", pady=(0, 12))

        grid = ttk.Frame(frm)
        grid.pack(fill="x")

        ttk.Label(grid, text="Website URL:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(grid, textvariable=self.url_var, width=90).grid(row=0, column=1, columnspan=3, sticky="ew", padx=8)

        ttk.Label(grid, text="Industry/Sector:").grid(row=1, column=0, sticky="w", pady=5)
        self.sector_combo = ttk.Combobox(grid, textvariable=self.sector_var, width=55, state="readonly")
        self.sector_combo.grid(row=1, column=1, sticky="w", padx=8)
        ttk.Button(grid, text="Load sectors", command=self.load_sectors).grid(row=1, column=2, padx=5)

        ttk.Label(grid, text="Letters:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Radiobutton(grid, text="A–Z", variable=self.letter_mode, value="A-Z").grid(row=2, column=1, sticky="w", padx=8)
        ttk.Radiobutton(grid, text="Specific letter", variable=self.letter_mode, value="ONE").grid(row=2, column=2, sticky="w")
        ttk.Combobox(grid, textvariable=self.single_letter, values=LETTERS, width=5, state="readonly").grid(row=2, column=3, sticky="w")

        ttk.Label(grid, text="Output folder:").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Entry(grid, textvariable=self.output_var, width=70).grid(row=3, column=1, columnspan=2, sticky="ew", padx=8)
        ttk.Button(grid, text="Browse", command=self.choose_folder).grid(row=3, column=3, sticky="w")

        ttk.Label(grid, text="Delay (seconds):").grid(row=4, column=0, sticky="w", pady=5)
        ttk.Spinbox(grid, from_=0.2, to=10, increment=0.2, textvariable=self.delay_var, width=8).grid(row=4, column=1, sticky="w", padx=8)

        ttk.Label(grid, text="Retries:").grid(row=4, column=2, sticky="e")
        ttk.Spinbox(grid, from_=1, to=8, textvariable=self.retry_var, width=8).grid(row=4, column=3, sticky="w", padx=8)

        ttk.Checkbutton(grid, text="Resume completed records", variable=self.resume_var).grid(row=5, column=1, sticky="w", padx=8)
        ttk.Checkbutton(grid, text="Headless browser", variable=self.headless_var).grid(row=5, column=2, sticky="w")
        ttk.Checkbutton(grid, text="Test mode (first 3 entities)", variable=self.test_var).grid(row=5, column=3, sticky="w")

        for c in range(4):
            grid.columnconfigure(c, weight=1)

        buttons = ttk.Frame(frm)
        buttons.pack(fill="x", pady=12)
        self.start_btn = ttk.Button(buttons, text="▶ Start Scraping", command=self.start)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = ttk.Button(buttons, text="■ Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left")

        stats = ttk.Frame(frm)
        stats.pack(fill="x", pady=(0, 8))
        self.stats_var = tk.StringVar(value="Processed: 0 | Success: 0 | Failed: 0 | Skipped: 0")
        ttk.Label(stats, textvariable=self.stats_var, font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.log_text = tk.Text(frm, wrap="word", height=28, font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)
        scroll = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_var.set(folder)

    def log(self, text):
        self.root.after(0, self._append_log, text)

    def _append_log(self, text):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def progress(self, processed, success, failed, skipped):
        self.root.after(
            0, lambda: self.stats_var.set(
                f"Processed: {processed} | Success: {success} | Failed: {failed} | Skipped: {skipped}"
            )
        )

    def load_sectors(self):
        # A short browser session reads the site's actual <select> options.
        def worker():
            cfg = {
                "url": self.url_var.get().strip(),
                "sector": "",
                "sector_id": "",
                "letters": ["A"],
                "output_folder": self.output_var.get(),
                "headless": True,
                "retries": 1,
                "timeout": DEFAULT_TIMEOUT,
                "delay": 0.5,
                "resume": True,
            }
            stop = threading.Event()
            scraper = None
            try:
                scraper = SEPCScraper(cfg, self.log, self.progress, stop)
                scraper.setup()
                scraper.initial_page()
                opts = scraper.discover_sector_options()
                self.sector_options = opts
                values = [o["text"] for o in opts]
                self.root.after(0, lambda: self.sector_combo.configure(values=values))
                if values:
                    self.root.after(0, lambda: self.sector_var.set(values[0]))
                self.log(f"Loaded {len(values)} sector options.")
            except Exception as exc:
                self.log(f"Could not load sectors: {exc}")
                self.log("You can still use the sector_id already present in the URL.")
            finally:
                if scraper:
                    scraper.close()
        threading.Thread(target=worker, daemon=True).start()

    def start(self):
        if self.thread and self.thread.is_alive():
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Missing URL", "Please enter the SEPC directory URL.")
            return

        sector = self.sector_var.get().strip()
        if not sector and self.sector_options:
            sector = self.sector_options[0]["text"]

        sector_id = ""
        for o in self.sector_options:
            if o["text"] == sector:
                sector_id = o["value"]
                break

        if not sector_id:
            q = parse_qs(urlparse(url).query)
            sector_id = (q.get("sector_id") or [""])[0]

        letters = LETTERS if self.letter_mode.get() == "A-Z" else [self.single_letter.get().upper()]
        if not letters or letters[0] not in LETTERS:
            messagebox.showerror("Invalid letter", "Select a letter from A to Z.")
            return

        os.makedirs(self.output_var.get(), exist_ok=True)
        self.stop_event.clear()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        cfg = {
            "url": url,
            "sector": sector,
            "sector_id": sector_id,
            "letters": letters,
            "output_folder": self.output_var.get(),
            "headless": self.headless_var.get(),
            "resume": self.resume_var.get(),
            "test_mode": self.test_var.get(),
            "test_count": 3,
            "delay": max(0.2, float(self.delay_var.get())),
            "retries": max(1, int(self.retry_var.get())),
            "timeout": DEFAULT_TIMEOUT,
        }

        def run():
            scraper = SEPCScraper(cfg, self.log, self.progress, self.stop_event)
            scraper.run()
            self.root.after(0, lambda: self.start_btn.configure(state="normal"))
            self.root.after(0, lambda: self.stop_btn.configure(state="disabled"))

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.log("Stop requested. The current entity will finish/retry, then the scraper will stop and export checkpointed data.")
        self.stop_btn.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except Exception:
        pass
    App(root)
    root.mainloop()
