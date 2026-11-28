"""GST portal automation with Selenium (Chrome).

Safety rule: a login is submitted only after the user typed a captcha, and the
app NEVER submits a second login for a client after the portal says the user
ID / password is wrong (or the result is unclear). See JobRunner._login.
"""
import os
import re
import time

from selenium import webdriver
from selenium.common.exceptions import (NoSuchElementException, TimeoutException,
                                        WebDriverException)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from naming import MONTH_ABBR, MONTH_FULL, fy_label, quarter_no
from settings import app_dir


class PortalError(Exception):
    """A step could not be done automatically (user can do it by hand)."""


class NotAvailable(Exception):
    """Return / statement not available for this period (not filed, not generated)."""


FORM_PATTERNS = {
    "GSTR1": r"GSTR\s*-?\s*1(?![0-9A-Z])",
    "GSTR2B": r"GSTR\s*-?\s*2B",
    "GSTR3B": r"GSTR\s*-?\s*3B",
}

PARTIAL_EXT = (".crdownload", ".tmp", ".part", ".download")

# A "tile" = the smallest box around a button that mentions the form and holds
# only a few buttons (a row of several tiles holds many). Works even when the
# tile's description mentions other forms.
JS_TILE_HELPERS = r"""
const re = new RegExp(arguments[0], 'i');
const vis = (e) => !!(e.offsetParent || e.getClientRects().length);
const btnCount = (el) => Array.from(el.querySelectorAll('button')).filter(vis).length;
// [tile, depth, score]; score 0 = the form is the first form named in the tile (its title)
function tileOf(b) {
  let el = b.parentElement, d = 0;
  while (el && d < 12) {
    const txt = el.innerText || '';
    if (re.test(txt)) {
      if (btnCount(el) > 4) return null;
      const first = (txt.match(/GSTR\s*-?\s*\d+[A-Z]*/i) || [''])[0];
      return [el, d, re.test(first) ? 0 : 1];
    }
    el = el.parentElement; d++;
  }
  return null;
}
const better = (r, best) => !best || r[2] < best[2] || (r[2] === best[2] && r[1] < best[1]);
"""

JS_TILE_BUTTON = JS_TILE_HELPERS + r"""
const want = arguments[1];
let best = null, bestR = null;
for (const b of document.querySelectorAll('button, a, input[type=button]')) {
  const t = (b.innerText || b.value || '').replace(/\s+/g, ' ').trim().toUpperCase();
  if (t !== want || !vis(b)) continue;
  const r = tileOf(b);
  if (r && better(r, bestR)) { best = b; bestR = r; }
}
return best;
"""

JS_TILE_TEXT = JS_TILE_HELPERS + r"""
let bestR = null;
for (const b of document.querySelectorAll('button')) {
  if (!vis(b)) continue;
  const r = tileOf(b);
  if (r && better(r, bestR)) bestR = r;
}
return bestR ? bestR[0].innerText : null;
"""

# Visible button / link whose text contains one of the given texts.
JS_BUTTON_CONTAINS = r"""
const wants = arguments[0];
const els = Array.from(document.querySelectorAll('button, a, input[type=button], input[type=submit]'));
for (const w of wants) {
  for (const b of els) {
    const t = (b.innerText || b.value || '').replace(/\s+/g, ' ').trim().toUpperCase();
    if (t && t.includes(w) && b.offsetParent && !b.disabled) return b;
  }
}
return null;
"""


# Visible <button> (or input button) whose whole text equals one of the texts.
# Menu links like "Search Taxpayer" can never match "SEARCH".
JS_BUTTON_EXACT = r"""
const wants = arguments[0];
const vis = (e) => !!(e.offsetParent || e.getClientRects().length);
const els = Array.from(document.querySelectorAll('button, input[type=button], input[type=submit], a.btn'));
for (const w of wants) {
  for (const b of els) {
    const t = (b.innerText || b.value || '').replace(/\s+/g, ' ').trim().toUpperCase();
    if (t === w && vis(b) && !b.disabled && !b.closest('nav, header, .navbar, .menu')) return b;
  }
}
return null;
"""


class GSTPortal:
    def __init__(self, cfg: dict, download_dir: str, log=print):
        self.cfg = cfg
        self.sel = cfg["portal"]
        self.timeout = int(cfg["browser"]["page_timeout"])
        self.dl_timeout = int(cfg["browser"]["download_timeout"])
        self.download_dir = download_dir
        self.log = log
        self.driver = None
        self.main_handle = None

    # ------------------------------------------------------------ browser
    def start(self):
        os.makedirs(self.download_dir, exist_ok=True)
        opts = webdriver.ChromeOptions()
        profile = os.path.join(app_dir(), "chrome_profile")
        opts.add_argument(f"--user-data-dir={profile}")
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_experimental_option("prefs", {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True,
            "profile.default_content_setting_values.automatic_downloads": 1,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        })
        self.driver = webdriver.Chrome(options=opts)
        self.driver.set_page_load_timeout(90)
        for cmd in ("Browser.setDownloadBehavior", "Page.setDownloadBehavior"):
            try:
                self.driver.execute_cdp_cmd(cmd, {"behavior": "allow", "downloadPath": self.download_dir})
                break
            except Exception:
                pass
        self.main_handle = self.driver.current_window_handle

    def alive(self) -> bool:
        try:
            _ = self.driver.current_url
            return True
        except Exception:
            return False

    def quit(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        self.driver = None

    # ------------------------------------------------------------ helpers
    def _wait(self, timeout=None):
        return WebDriverWait(self.driver, timeout or self.timeout)

    def _body_text(self) -> str:
        try:
            return (self.driver.execute_script("return document.body ? document.body.innerText : ''") or "").lower()
        except WebDriverException:
            return ""

    def _js_click(self, el):
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", el)

    def _click_contains(self, texts, timeout=None) -> bool:
        end = time.time() + (timeout if timeout is not None else self.timeout)
        wants = [t.upper() for t in texts]
        while time.time() < end:
            try:
                el = self.driver.execute_script(JS_BUTTON_CONTAINS, wants)
                if el:
                    self._js_click(el)
                    return True
            except WebDriverException:
                pass
            time.sleep(0.5)
        return False

    def _click_exact(self, texts, timeout=None) -> bool:
        end = time.time() + (timeout if timeout is not None else self.timeout)
        wants = [t.upper() for t in texts]
        while time.time() < end:
            try:
                el = self.driver.execute_script(JS_BUTTON_EXACT, wants)
                if el:
                    self._js_click(el)
                    return True
            except WebDriverException:
                pass
            time.sleep(0.5)
        return False

    def _tile_text(self, form: str, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            try:
                t = self.driver.execute_script(JS_TILE_TEXT, FORM_PATTERNS[form])
                if t:
                    return t
            except WebDriverException:
                pass
            time.sleep(0.5)
        return None

    def _click_tile(self, form: str, button: str, timeout=6) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            try:
                el = self.driver.execute_script(JS_TILE_BUTTON, FORM_PATTERNS[form], button.upper())
                if el:
                    self._js_click(el)
                    return True
            except WebDriverException:
                pass
            time.sleep(0.5)
        return False

    def close_extra_windows(self):
        try:
            for h in list(self.driver.window_handles):
                if h != self.main_handle:
                    self.driver.switch_to.window(h)
                    self.driver.close()
            self.driver.switch_to.window(self.main_handle)
        except WebDriverException:
            pass

    # ------------------------------------------------------------ downloads
    def snapshot(self) -> set:
        return set(os.listdir(self.download_dir))

    def new_files(self, before: set) -> list[str]:
        """Completed files that appeared since `before` (none while one is partial)."""
        names = set(os.listdir(self.download_dir))
        if any(n.lower().endswith(PARTIAL_EXT) for n in names - before):
            return []
        out = []
        for n in sorted(names - before):
            p = os.path.join(self.download_dir, n)
            if os.path.isfile(p) and os.path.getsize(p) > 0:
                out.append(p)
        return out

    def wait_files(self, before: set, count=1, timeout=None) -> list[str]:
        end = time.time() + (timeout or self.dl_timeout)
        while time.time() < end:
            files = self.new_files(before)
            if len(files) >= count:
                time.sleep(0.8)            # let the file settle
                return self.new_files(before)
            time.sleep(0.7)
        raise TimeoutException("Download did not finish in time")

    # ------------------------------------------------------------ login
    def open_login(self, client):
        d = self.driver
        self.close_extra_windows()
        d.get(self.sel["login_url"])
        user = self._wait().until(EC.visibility_of_element_located((By.ID, self.sel["username_id"])))
        user.clear()
        user.send_keys(client.login_id)
        pw = d.find_element(By.ID, self.sel["password_id"])
        pw.clear()
        pw.send_keys(client.password)    # typed exactly, symbols included

    def captcha_image_b64(self) -> str:
        el = self._wait().until(EC.visibility_of_element_located((By.ID, self.sel["captcha_image_id"])))
        end = time.time() + 10
        while time.time() < end:
            ok = self.driver.execute_script(
                "const i=arguments[0]; return i.complete && (i.naturalWidth||i.width) > 0;", el)
            if ok:
                break
            time.sleep(0.3)
        time.sleep(0.3)
        return el.screenshot_as_base64

    def refresh_captcha(self):
        d = self.driver
        img = d.find_element(By.ID, self.sel["captcha_image_id"])
        old = img.get_attribute("src")
        clicked = False
        for xp in ("//*[contains(@class,'refresh')]", "//*[contains(@ng-click,'refresh') or contains(@ng-click,'Captcha')]",
                   "//*[@title='Refresh' or @aria-label='Refresh']"):
            try:
                for el in d.find_elements(By.XPATH, xp):
                    if el.is_displayed():
                        self._js_click(el)
                        clicked = True
                        break
            except WebDriverException:
                pass
            if clicked:
                break
        if not clicked:
            self._js_click(img)
        end = time.time() + 5
        while time.time() < end:
            try:
                if d.find_element(By.ID, self.sel["captcha_image_id"]).get_attribute("src") != old:
                    break
            except WebDriverException:
                pass
            time.sleep(0.3)
        time.sleep(0.5)

    def submit_login(self, captcha: str) -> str:
        """Submit ONE login. Returns success|captcha|bad_credentials|locked|expired|unknown."""
        d = self.driver
        cap = d.find_element(By.ID, self.sel["captcha_input_id"])
        cap.clear()
        cap.send_keys(captcha)
        btn = None
        for xp in ("//button[@type='submit']", "//button[contains(translate(normalize-space(.),'login','LOGIN'),'LOGIN')]"):
            found = [b for b in d.find_elements(By.XPATH, xp) if b.is_displayed()]
            if found:
                btn = found[0]
                break
        if btn is None:
            raise PortalError("Login button not found")
        # Phrases already on the page before we click are ignored, so a static
        # label can never be mistaken for a "wrong captcha" reply.
        before = self._body_text()
        pre = {t for group in ("captcha_error_texts", "bad_credential_texts", "locked_texts",
                               "password_expired_texts") for t in self.sel[group] if t in before}
        self._js_click(btn)
        time.sleep(1.5)
        return self._login_result(pre)

    def _login_result(self, pre: set) -> str:
        s = self.sel

        def has(group, text):
            return any(t in text and t not in pre for t in s[group])

        end = time.time() + max(self.timeout, 30)
        while time.time() < end:
            try:
                url = self.driver.current_url.lower()
            except WebDriverException:
                url = ""
            text = self._body_text()
            if has("bad_credential_texts", text):
                return "bad_credentials"
            if has("locked_texts", text):
                return "locked"
            if has("password_expired_texts", text):
                return "expired"
            if any(p in url for p in s["login_success_url_parts"]):
                return "success"
            if has("captcha_error_texts", text):
                return "captcha"
            time.sleep(0.5)
        return "unknown"

    def dismiss_popups(self):
        for _ in range(3):
            time.sleep(1.2)
            if not self._click_exact(self.sel["popup_dismiss_texts"], timeout=1):
                break

    def logout(self):
        try:
            self.close_extra_windows()
            self.driver.get(self.sel["logout_url"])
            time.sleep(2)
            self.driver.delete_all_cookies()
        except WebDriverException:
            pass

    # ------------------------------------------------------------ dashboard
    # Lists every <select> on the page with its options (textContent works even
    # when the portal hides the real dropdown behind a styled one).
    JS_SELECTS = r"""
    return Array.from(document.querySelectorAll('select')).map((s, i) => {
      let label = '';
      if (s.id) { const l = document.querySelector('label[for="' + s.id + '"]'); if (l) label = l.textContent; }
      if (!label) { let p = s.parentElement; for (let k = 0; k < 3 && p && !label; k++, p = p.parentElement) {
        const l = p.querySelector('label'); if (l) label = l.textContent; } }
      const r = s.getBoundingClientRect();
      return { i, id: s.id || '', name: s.name || '', label: (label || '').replace(/\s+/g, ' ').trim(),
               shown: !!(r.width || r.height), disabled: s.disabled,
               options: Array.from(s.options).map(o => (o.textContent || '').replace(/\s+/g, ' ').trim()) };
    });
    """
    # Select an option the way the page does it, so Angular/React notice the change.
    JS_PICK = r"""
    const s = document.querySelectorAll('select')[arguments[0]];
    s.selectedIndex = arguments[1];
    s.dispatchEvent(new Event('input', { bubbles: true }));
    s.dispatchEvent(new Event('change', { bubbles: true }));
    return s.options[s.selectedIndex] ? s.options[s.selectedIndex].textContent.trim() : '';
    """

    def _select_option(self, css: str, index: int, match, words=()) -> None:
        end = time.time() + self.timeout
        info = []
        want_name = re.search(r"name=['\"]?([\w-]+)", css or "")
        want_name = want_name.group(1) if want_name else ""
        while time.time() < end:
            try:
                info = self.driver.execute_script(self.JS_SELECTS) or []
            except WebDriverException:
                info = []
            usable = [s for s in info if not s["disabled"] and len([o for o in s["options"] if o]) > 0]

            def pick_order():
                by_name = [s for s in usable if want_name and (s["name"] == want_name or s["id"] == want_name)]
                by_label = [s for s in usable if any(w in s["label"].lower() for w in words)]
                by_opts = [s for s in usable if any(match(o) for o in s["options"])]
                shown = [s for s in usable if s["shown"]]
                by_index = [shown[index]] if len(shown) > index else []
                seen, out = set(), []
                for s in by_name + by_label + by_index + by_opts:
                    if s["i"] not in seen:
                        seen.add(s["i"])
                        out.append(s)
                return out

            for s in pick_order():
                for k, t in enumerate(s["options"]):
                    if t and match(t):
                        try:
                            self.driver.execute_script(self.JS_PICK, s["i"], k)
                        except WebDriverException:
                            break
                        time.sleep(1.0)
                        return
            time.sleep(0.7)
        dump = self.save_debug("dashboard", info)
        summary = "; ".join(f"{s['label'] or s['name'] or s['id'] or 'select'}: {', '.join(s['options'][:6])}"
                            for s in info)[:200] or "no dropdowns found on the page"
        raise PortalError(f"Could not select the period on the returns dashboard ({summary}). Debug saved: {dump}")

    def save_debug(self, tag: str, extra=None) -> str:
        """Screenshot + page details for troubleshooting. Returns the folder."""
        import json
        from datetime import datetime
        folder = os.path.join(app_dir(), "debug")
        os.makedirs(folder, exist_ok=True)
        base = os.path.join(folder, f"{datetime.now():%Y%m%d_%H%M%S}_{tag}")
        try:
            self.driver.save_screenshot(base + ".png")
        except Exception:
            pass
        try:
            with open(base + ".txt", "w", encoding="utf-8") as f:
                f.write(f"URL: {self.driver.current_url}\nTITLE: {self.driver.title}\n\n")
                f.write("DROPDOWNS:\n" + json.dumps(extra, indent=2, ensure_ascii=False) + "\n\n")
                f.write("VISIBLE TEXT:\n" + (self.driver.execute_script("return document.body.innerText") or "")[:20000])
        except Exception:
            pass
        return folder

    # Visible-or-hidden link/button whose text matches exactly (menu items are hidden
    # until hovered, so offsetParent is not required here).
    JS_FIND_LINK = r"""
    const wants = arguments[0];
    const els = Array.from(document.querySelectorAll('a, button'));
    for (const w of wants) for (const e of els) {
      const t = (e.innerText || e.textContent || '').replace(/\s+/g, ' ').trim().toUpperCase();
      if (t === w) return e;
    }
    return null;
    """

    def _on_dashboard(self) -> bool:
        try:
            url = self.driver.current_url.lower()
        except WebDriverException:
            return False
        return "returns/auth/dashboard" in url

    def _denied(self) -> bool:
        try:
            url = self.driver.current_url.lower()
        except WebDriverException:
            return False
        return "accessdenied" in url or "access denied" in self._body_text()[:3000]

    def _wait_dashboard(self, timeout=25) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            if self._denied():
                return False
            if self._on_dashboard():
                try:
                    n = self.driver.execute_script("return document.querySelectorAll('select').length")
                except WebDriverException:
                    n = 0
                if n:
                    return True
            time.sleep(0.6)
        return self._on_dashboard()

    def open_dashboard(self):
        """Reach the Returns Dashboard the way a person does (the portal refuses
        a direct jump to its address with 'Access Denied')."""
        d = self.driver
        s = self.sel
        if self._on_dashboard() and not self._denied():
            d.refresh()
            if self._wait_dashboard():
                return
        # 1) welcome page -> RETURN DASHBOARD button
        d.get(s["welcome_url"])
        time.sleep(1.5)
        if "login" in d.current_url.lower():
            raise PortalError("Portal session expired (sent back to the login page)")
        self.dismiss_popups()
        if self._click_contains(s["dashboard_button_texts"], timeout=10) and self._wait_dashboard():
            return
        # 2) menu: Services > Returns > Returns Dashboard
        d.get(s["welcome_url"])
        time.sleep(1.5)
        try:
            link = d.execute_script(self.JS_FIND_LINK, [t.upper() for t in s["dashboard_menu_texts"]])
            if link:
                self._js_click(link)
                if self._wait_dashboard():
                    return
        except WebDriverException:
            pass
        dump = self.save_debug("open_dashboard")
        if self._denied():
            raise PortalError(f"Portal said 'Access Denied' when opening the Returns Dashboard. Debug saved: {dump}")
        raise PortalError(f"Could not open the Returns Dashboard. Debug saved: {dump}")

    def open_period(self, year: int, month: int):
        d = self.driver
        s = self.sel
        self.close_extra_windows()
        self.open_dashboard()
        fy = fy_label(year, month)
        q = quarter_no(month)
        full, abbr = MONTH_FULL[month - 1].lower(), MONTH_ABBR[month - 1].lower()
        try:
            self._wait().until(lambda drv: drv.execute_script("return document.readyState") == "complete")
        except TimeoutException:
            pass
        fy_short = f"{fy[:4]}-20{fy[5:]}"          # portal may show 2026-2027
        self._select_option(s["fy_select_css"], 0,
                            lambda t: fy in t.replace(" ", "") or fy_short in t.replace(" ", ""),
                            words=("financial year", "year"))
        self._select_option(s["quarter_select_css"], 1,
                            lambda t: re.search(rf"quarter\s*{q}\b", t, re.I) is not None or t.strip() == f"Q{q}",
                            words=("quarter",))
        self._select_option(s["month_select_css"], 2,
                            lambda t: t.lower().startswith(full) or t.lower().startswith(abbr + " ")
                            or t.lower() == abbr,
                            words=("period", "month"))
        if not self._click_exact(s["search_button_texts"], timeout=10):
            dump = self.save_debug("search_button")
            raise PortalError(f"SEARCH button not found on the returns dashboard. Debug saved: {dump}")
        # wait for tiles to appear
        end = time.time() + self.timeout
        while time.time() < end:
            try:
                ready = self.driver.execute_script(
                    "return Array.from(document.querySelectorAll('button')).some(b => "
                    "(b.offsetParent || b.getClientRects().length) && /^(VIEW|DOWNLOAD|PREPARE ONLINE)$/i"
                    ".test((b.innerText||'').trim()))")
            except WebDriverException:
                ready = False
            if ready:
                time.sleep(1.5)
                return
            time.sleep(0.5)
        dump = self.save_debug("tiles")
        raise PortalError(f"Return tiles did not load after SEARCH. Debug saved: {dump}")

    def _check_tile(self, form: str, need_filed: bool):
        text = self._tile_text(form)
        if text is None:
            dump = self.save_debug(f"tile_{form}")
            if form == "GSTR1":
                raise NotAvailable(f"GSTR-1 tile not shown (quarterly filer, or not applicable). Debug: {dump}")
            raise NotAvailable(f"{form} tile not found on the dashboard. Debug: {dump}")
        if need_filed and re.search(self.sel["not_filed_regex"], text, re.I):
            raise NotAvailable(f"{form} not filed yet")

    # ------------------------------------------------------------ forms
    def download_gstr2b(self, year, month, excel=True, json=True) -> list[str]:
        self.open_period(year, month)
        self._check_tile("GSTR2B", need_filed=False)
        if not self._click_tile("GSTR2B", "DOWNLOAD"):
            raise NotAvailable("GSTR-2B not generated yet for this period")
        files = []
        if excel:
            before = self.snapshot()
            if not self._click_contains(self.sel["gstr2b_excel_button_texts"]):
                raise PortalError("GSTR-2B 'Generate Excel' button not found")
            files += self.wait_files(before)
        if json:
            before = self.snapshot()
            if not self._click_contains(self.sel["gstr2b_json_button_texts"]):
                raise PortalError("GSTR-2B 'Generate JSON' button not found")
            files += self.wait_files(before)
        return files

    def download_gstr1(self, year, month) -> list[str]:
        self.open_period(year, month)
        self._check_tile("GSTR1", need_filed=True)
        if not self._click_tile("GSTR1", "VIEW"):
            raise PortalError("GSTR-1 VIEW button not found")
        time.sleep(2)
        before = self.snapshot()
        if not self._click_contains(self.sel["gstr1_pdf_button_texts"], timeout=10):
            if not self._click_contains(self.sel["gstr1_summary_button_texts"], timeout=10):
                raise PortalError("GSTR-1 'View Summary' button not found")
            time.sleep(2)
            if not self._click_contains(self.sel["gstr1_pdf_button_texts"]):
                raise PortalError("GSTR-1 'Download (PDF)' button not found")
        files = self.wait_files(before)
        self.close_extra_windows()
        return files

    def download_gstr3b(self, year, month) -> list[str]:
        self.open_period(year, month)
        self._check_tile("GSTR3B", need_filed=True)
        before = self.snapshot()
        if self._click_tile("GSTR3B", "DOWNLOAD"):
            try:
                files = self.wait_files(before, timeout=25)
                self.close_extra_windows()
                return files
            except TimeoutException:
                self.close_extra_windows()
        # second route: open the return and use its download button
        self.open_period(year, month)
        if not self._click_tile("GSTR3B", "VIEW"):
            raise PortalError("GSTR-3B DOWNLOAD / VIEW button not found")
        time.sleep(2)
        before = self.snapshot()
        if not self._click_contains(self.sel["gstr3b_pdf_button_texts"]):
            raise PortalError("GSTR-3B 'Download filed return' button not found")
        files = self.wait_files(before)
        self.close_extra_windows()
        return files
