"""
GST portal worker (runs in its own thread, owns the Playwright browser).

How it works - all of this was verified on the live portal:
  * Login: you type the captcha (and OTP if asked). The app never solves it.
  * After login the app moves between portal pages from INSIDE the page
    (like clicking a link). Typing URLs directly gives "Access Denied".
  * Data is read from the same JSON services the portal's own screens use,
    then saved as Excel (pandas) + raw JSON. PDFs (REG-06, optional GSTR-3B)
    are saved as files.
"""
from __future__ import annotations

import base64
import io
import json
import os
import queue
import re
import threading
import time
import traceback
import zipfile
from datetime import date, datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

import compliance as comp
import reports as rp
from portal_config import (API, ERR_IN_PROGRESS, ERR_NO_RECORD, GSTR2B, LOGIN, MONTHS, PAGES, RETURNS,
                           RETURNS_DASH, SERVICES, prd_code, prd_label, quarter_label)

FETCH_JS = """
async ({url, method, body, binary}) => {
  try {
    const opt = {method: method || 'GET', credentials: 'include', headers: {}};
    if (body) { opt.headers['Content-Type'] = 'application/json;charset=UTF-8'; opt.body = JSON.stringify(body); }
    const r = await fetch(url, opt);
    const ct = r.headers.get('content-type') || '';
    const cd = r.headers.get('content-disposition') || '';
    if (binary && !ct.includes('json') && !ct.includes('html')) {
      const b = new Uint8Array(await r.arrayBuffer());
      let s = ''; for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
      return {status: r.status, ct, cd, b64: btoa(s), url: r.url};
    }
    return {status: r.status, ct, cd, text: await r.text(), url: r.url};
  } catch (e) { return {error: String(e)}; }
}
"""

FORM_OF_JS = """
([form, label]) => {
  const formOf = b => { let p = b; for (let i = 0; i < 8 && p; i++) { p = p.parentElement;
      const m = p && p.innerText.replace(/[\\s-]/g, '').toUpperCase().match(/GSTR(1A|2A|2B|3B|9C|9A|9|1|4|7|8)/g);
      if (m) return [...new Set(m)].join('/'); } return null; };
  const b = [...document.querySelectorAll('button')].find(b => b.offsetParent && b.innerText.trim() === label && formOf(b) === form);
  if (!b) return false;
  setTimeout(() => b.click(), 30);
  return true;
}
"""


class SessionError(Exception):
    pass


class StopRequested(Exception):
    pass


class PortalWorker(threading.Thread):
    def __init__(self, to_gui: queue.Queue):
        super().__init__(daemon=True)
        self.cmds: queue.Queue = queue.Queue()
        self.to_gui = to_gui
        self.stop_flag = False
        self.ctx = None
        self.page = None
        self.gstin = ""
        self.out_dir = Path.home() / "Documents" / "GST_Downloads"

    # ------------------------------------------------------------------ plumbing
    def send(self, kind, **kw):
        self.to_gui.put((kind, kw))

    def log(self, msg):
        self.send("log", msg=msg)

    def submit(self, *cmd):
        self.cmds.put(cmd)

    def run(self):
        try:
            with sync_playwright() as p:
                browser = None
                for ch in ("chrome", "msedge", None):
                    try:
                        browser = p.chromium.launch(headless=False, channel=ch) if ch else p.chromium.launch(headless=False)
                        self.log(f"Browser started ({ch or 'Playwright Chromium'}).")
                        break
                    except Exception:
                        continue
                if browser is None:
                    self.send("fatal", msg="Could not start Chrome/Edge/Chromium. Run setup.bat first.")
                    return
                self.ctx = browser.new_context(accept_downloads=True, viewport={"width": 1280, "height": 820})
                self.page = self.ctx.new_page()
                self.page.set_default_timeout(30000)
                while True:
                    try:
                        cmd = self.cmds.get(timeout=0.3)
                    except queue.Empty:
                        try:
                            self.page.wait_for_timeout(100)
                        except Exception:
                            time.sleep(0.1)
                        continue
                    if cmd[0] == "quit":
                        break
                    try:
                        getattr(self, "cmd_" + cmd[0])(*cmd[1:])
                    except StopRequested:
                        self.log("Stopped.")
                        self.send("jobs_done", results=[], status=None)
                    except SessionError as e:
                        self.log(f"SESSION: {e}")
                        self.send("session_lost", msg=str(e))
                    except Exception as e:
                        self.log(f"Error: {e}")
                        self.log(traceback.format_exc(limit=3))
                        self.send("error", msg=str(e))
                try:
                    browser.close()
                except Exception:
                    pass
        except Exception as e:
            self.send("fatal", msg=f"Browser engine error: {e}\nRun setup.bat to install Playwright.")

    def _pg(self):
        pages = [p for p in self.ctx.pages if not p.is_closed()]
        if pages and (self.page is None or self.page.is_closed()):
            self.page = pages[-1]
        return self.page

    def _check_stop(self):
        if self.stop_flag:
            raise StopRequested()

    # ------------------------------------------------------------------ navigation + API
    def nav(self, url: str):
        """Open a portal page the way a link click does (keeps the Referer)."""
        pg = self._pg()
        if not pg.url.startswith("https://"):
            pg.goto(url, wait_until="domcontentloaded")
        else:
            try:
                with pg.expect_navigation(wait_until="domcontentloaded", timeout=45000):
                    pg.evaluate("u => setTimeout(() => { window.location.href = u; }, 30)", url)
            except PWTimeout:
                raise RuntimeError(f"Page did not open: {url}")
        pg.wait_for_timeout(1500)
        if "accessdenied" in pg.url or "/error/" in pg.url or pg.url.rstrip("/").endswith("/services/login"):
            raise SessionError(f"Portal refused {url} (now at {pg.url}). Session may have expired - log in again.")

    def ensure_origin(self, origin: str):
        pg = self._pg()
        if pg.url.startswith(origin):
            return
        if origin == SERVICES:
            self.nav(PAGES["services_dashboard"])
        elif origin == RETURNS:
            self.nav(PAGES["returns_dashboard"])
        else:
            raise RuntimeError("GSTR-2B site must be opened through the Returns Dashboard tile")

    def api(self, path: str, method="GET", body=None, binary=False):
        pg = self._pg()
        res = pg.evaluate(FETCH_JS, {"url": path, "method": method, "body": body, "binary": binary})
        if res.get("error"):
            raise RuntimeError(f"Network error on {path}: {res['error']}")
        if binary and "b64" in res:
            return res
        txt = res.get("text", "")
        if txt.lstrip().startswith("<"):
            raise SessionError(f"Portal returned a web page instead of data for {path} - session expired?")
        try:
            return json.loads(txt) if txt else {}
        except json.JSONDecodeError:
            raise RuntimeError(f"Unexpected reply from {path}: {txt[:150]}")

    # ------------------------------------------------------------------ LOGIN
    def _send_captcha(self, error=""):
        pg = self._pg()
        try:
            img = pg.locator(LOGIN["captcha_img"])
            img.wait_for(state="visible", timeout=15000)
            pg.wait_for_function("() => { const i = document.querySelector('#imgCaptcha'); "
                                 "return i && i.complete && i.naturalWidth > 0; }", timeout=10000)
            png = img.screenshot()
            self.send("captcha", png=base64.b64encode(png).decode(), error=error)
        except Exception as e:
            self.send("captcha", png=None, error=(error + " " if error else "") +
                      f"Captcha not visible yet ({type(e).__name__}). Click 'New captcha' or type it in the browser.")

    def cmd_open_login(self, username):
        pg = self._pg()
        self.log("Opening GST login page...")
        pg.goto(PAGES["login"], wait_until="domcontentloaded")
        u = pg.locator(LOGIN["username"])
        u.wait_for(state="visible")
        u.click()
        u.fill("")
        u.press_sequentially(username, delay=40)   # real key presses - portal shows captcha after this
        u.press("Tab")
        pg.wait_for_timeout(800)
        self._send_captcha()

    def cmd_refresh_captcha(self):
        pg = self._pg()
        try:
            pg.locator(LOGIN["captcha_refresh"]).first.click(timeout=4000)
        except Exception:
            pass
        pg.wait_for_timeout(1200)
        self._send_captcha()

    def cmd_login(self, password, captcha):
        pg = self._pg()
        pw = pg.locator(LOGIN["password"])
        pw.fill("")
        pw.press_sequentially(password, delay=20)
        if captcha:
            c = pg.locator(LOGIN["captcha_input"])
            c.fill("")
            c.press_sequentially(captcha, delay=40)    # box blocks paste and allows digits only
        # clear any old error text so a stale message is not mistaken for a new one
        pg.evaluate("() => document.querySelectorAll('.err, .alert-danger').forEach(e => { e.textContent = ''; })")
        pg.locator(LOGIN["login_btn"]).first.click()
        self.log("Login submitted...")
        end = time.time() + 45
        while time.time() < end:
            pg = self._pg()
            url = pg.url
            if "/services/auth/" in url:
                return self._after_login()
            # the page may be navigating (post-login); DOM reads can throw "context destroyed"
            try:
                otp = pg.get_by_text("One-Time Password", exact=False)
                if "otpforauth" in url or (otp.count() and otp.first.is_visible()):
                    self.send("otp", msg="The portal sent an OTP to the registered mobile/email. Enter it in the "
                                         "browser window, submit, then click 'I have logged in (continue)'.")
                    return
                errs = [t.strip() for t in pg.locator(LOGIN["error"]).all_inner_texts() if t.strip()]
            except Exception:
                pg.wait_for_timeout(500)             # mid-navigation - re-check next loop
                continue
            if errs:
                msg = " | ".join(dict.fromkeys(errs))[:200]
                self.log(f"Portal: {msg}")
                pg.wait_for_timeout(1200)            # portal refreshes the captcha itself
                return self._send_captcha(error=msg)
            pg.wait_for_timeout(500)
        self.send("captcha", png=None, error="No response from portal yet. If something is shown in the browser, "
                                             "finish it there and click 'I have logged in (continue)'.")

    def cmd_confirm_logged_in(self):
        self._after_login()

    def _after_login(self):
        pg = self._pg()
        pg.wait_for_timeout(1500)
        try:
            u = self.api(API["ustatus"])
            self.gstin = u.get("gstin") or ""
            if u.get("role") != "login" and not self.gstin:
                raise SessionError("Not logged in yet.")
        except SessionError:
            raise
        except Exception:
            m = re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b", pg.inner_text("body"))
            self.gstin = m.group(0) if m else ""
        if not self.gstin:
            self.send("captcha", png=None, error="Login not detected yet. Finish login in the browser, then click continue.")
            return
        self.log(f"Logged in. GSTIN {self.gstin}")
        self.send("logged_in", gstin=self.gstin)

    # ------------------------------------------------------------------ E-WAY BILL PORTAL
    def _ewb_dest(self, out_dir):
        dest = Path(out_dir) / (self.gstin or "EWB") / "ewb"
        dest.mkdir(parents=True, exist_ok=True)
        return dest

    def _save_unique(self, d, dest: Path):
        """Save a Playwright download under a non-colliding name, keep the portal's extension."""
        raw = d.suggested_filename or "ewb_report.xls"
        raw = re.sub(r'[<>:"/\\|?*]', "_", raw)
        target = dest / raw
        if target.exists():
            stem, ext = os.path.splitext(raw)
            target = dest / f"{stem}_{int(time.time())}{ext}"
        d.save_as(str(target))
        return target

    def cmd_open_ewb(self, out_dir):
        """Open the e-way bill portal in a new tab and keep it. The user logs in there
        (captcha / OTP by hand). Any report the user downloads by hand is also saved into
        <GSTIN>/ewb/. After login the app can pull the COMPLETE records itself."""
        from portal_config import EWB_LOGIN
        dest = self._ewb_dest(out_dir)
        self._ewb_out_dir = out_dir

        def on_dl(d):
            try:
                target = self._save_unique(d, self._ewb_dest(self._ewb_out_dir))
                self.send("ewb_downloaded", path=str(target))
                self.log(f"   e-way bill report saved: {target.name}")
            except Exception as e:
                self.log(f"   EWB download: {e}")

        self._ewb_on_dl = on_dl
        try:
            pg = self.ctx.new_page()
            pg.on("download", on_dl)
            self.ewb_page = pg
            pg.goto(EWB_LOGIN["page"], wait_until="domcontentloaded")
            self.send("ewb_opened", folder=str(dest))
            self.log("E-way bill portal opened. Log in there (type the captcha / OTP). "
                     "Then set the From/To dates in this app and click "
                     "'Download complete EWB records' - the app pulls every record itself.")
        except Exception as e:
            self.send("error", msg=f"Could not open e-way bill portal: {e}")

    def _ewb_page(self):
        pg = getattr(self, "ewb_page", None)
        if pg is None or pg.is_closed():
            raise RuntimeError("The e-way bill portal is not open. Click 'Open e-way bill portal' and log in first.")
        return pg

    def _ewb_open_report(self, pg, url):
        """Reach an EWB report page the way a menu click does (direct URLs bounce to the
        main menu because of the referer rule)."""
        from portal_config import EWB_LOGIN
        pg.goto(EWB_LOGIN["mainmenu"], wait_until="domcontentloaded")
        pg.wait_for_timeout(600)
        if "login.aspx" in pg.url.lower():
            raise SessionError("Not logged in to the e-way bill portal yet. Log in in the browser, then try again.")
        try:
            with pg.expect_navigation(wait_until="domcontentloaded", timeout=45000):
                pg.evaluate("u => { window.location.href = u; }", url)
        except PWTimeout:
            raise RuntimeError(f"E-way bill report did not open: {url}")
        pg.wait_for_timeout(1200)
        if "commomreport" not in pg.url.lower():
            raise RuntimeError(f"E-way bill report redirected to {pg.url} - session may have expired.")

    def _ewb_window_download(self, pg, cfg, d_from, d_to, dest, tag):
        """Set a <=5-day window + ALL subuser, submit, and Export-To-Excel. Returns the
        saved path, or None when the window has no records."""
        f = lambda sel: sel[1:] if sel.startswith("#") else sel  # id without '#'
        js_set = """
            (a) => {
              const g = id => document.getElementById(id);
              const d0 = g(a.f0), d1 = g(a.f1), su = g(a.su);
              if (d0) d0.value = a.v0;
              if (d1) d1.value = a.v1;
              if (su) su.value = a.suv;
              return !!(d0 && d1);
            }"""
        ok = pg.evaluate(js_set, {"f0": f(cfg["date_from"]), "f1": f(cfg["date_to"]),
                                  "su": f(cfg["subuser"]), "v0": d_from, "v1": d_to,
                                  "suv": cfg["subuser_all"]})
        if not ok:
            raise RuntimeError("E-way bill report date fields not found (portal layout changed?).")
        # Go -> full postback
        try:
            with pg.expect_navigation(wait_until="domcontentloaded", timeout=60000):
                pg.evaluate("id => document.getElementById(id).click()", f(cfg["go_btn"]))
        except PWTimeout:
            raise RuntimeError("E-way bill report did not respond to 'Go'.")
        pg.wait_for_timeout(1200)
        # how many rows came back?
        rows = pg.evaluate("""
            id => { const t = document.getElementById(id);
                    return t ? t.querySelectorAll('tbody tr').length : 0; }""", "ListgenMetable")
        has_export = pg.evaluate("id => !!document.getElementById(id)", f(cfg["export_excel"]))
        if not rows or not has_export:
            return None
        with pg.expect_download(timeout=90000) as dl:
            pg.evaluate("id => document.getElementById(id).click()", f(cfg["export_excel"]))
        target = self._save_unique(dl.value, dest)
        # stamp the window into the name so chunks never collide
        stamped = dest / f"{self.gstin or 'EWB'}_EWB_{tag}_{d_from.replace('/','-')}_{d_to.replace('/','-')}{target.suffix}"
        try:
            if stamped != target:
                target.replace(stamped)
                target = stamped
        except Exception:
            pass
        return target

    def cmd_download_ewb_range(self, out_dir, from_date, to_date, include_inward=False):
        """Pull the COMPLETE 'EWB generated by me' records across the whole period by
        looping the portal's 5-day windows and Export-To-Excel on each. The chunks are
        combined (deduped on EWB No) by ewaybill.load_export at analysis time.

        from_date / to_date are dd/mm/yyyy strings."""
        from portal_config import EWB_REPORT as cfg
        import datetime as _dt

        def parse(s):
            return _dt.datetime.strptime(s.strip(), "%d/%m/%Y").date()

        try:
            start, end = parse(from_date), parse(to_date)
        except Exception:
            self.send("error", msg="Dates must be dd/mm/yyyy, e.g. 01/04/2025.")
            return
        if start > end:
            start, end = end, start
        today = _dt.date.today()
        if end > today:
            end = today

        # if the e-way bill tab isn't open yet, open it and ask the user to log in there first
        pg = getattr(self, "ewb_page", None)
        if pg is None or pg.is_closed():
            self.cmd_open_ewb(out_dir)
            self.send("ewb_range_done", folder=str(self._ewb_dest(out_dir)), files=[], empty=0)
            self.send("error", msg="The e-way bill portal is a SEPARATE login from the GST portal. I've "
                      "opened it for you - log in there (username, password, captcha/OTP), then click "
                      "'Download complete EWB records' again.")
            return
        self._ewb_out_dir = out_dir
        dest = self._ewb_dest(out_dir)
        # don't let the generic handler double-save the export downloads
        try:
            pg.remove_listener("download", self._ewb_on_dl)
        except Exception:
            pass

        step = _dt.timedelta(days=cfg["max_days"] - 1)  # inclusive 5-day windows
        one = _dt.timedelta(days=1)
        reports = [("outward", cfg["outward"], "outward")]
        if include_inward:
            reports.append(("inward", cfg["inward"], "inward"))

        saved, empty, total_windows = [], 0, 0
        try:
            for label, url, tag in reports:
                self.log(f"E-way bills - {label}: pulling {start:%d/%m/%Y} to {end:%d/%m/%Y} in 5-day windows...")
                self._ewb_open_report(pg, url)
                cur = start
                while cur <= end:
                    self._check_stop()
                    w_end = min(cur + step, end)
                    total_windows += 1
                    d_from, d_to = cur.strftime("%d/%m/%Y"), w_end.strftime("%d/%m/%Y")
                    try:
                        path = self._ewb_window_download(pg, cfg, d_from, d_to, dest, tag)
                    except SessionError:
                        raise
                    except Exception as e:
                        self.log(f"   {d_from}-{d_to}: {e}")
                        path = None
                    if path:
                        saved.append(str(path))
                        self.send("ewb_downloaded", path=str(path))
                        self.log(f"   {d_from} - {d_to}: saved {path.name}")
                    else:
                        empty += 1
                    self.send("ewb_progress", done=total_windows, saved=len(saved))
                    cur = w_end + one
        except StopRequested:
            self.log("E-way bill download stopped.")
        except SessionError as e:
            self.send("session_lost", msg=str(e))
        finally:
            try:
                pg.on("download", self._ewb_on_dl)  # restore manual auto-save
            except Exception:
                pass

        self.log(f"E-way bill download done: {len(saved)} file(s) into {dest} "
                 f"({empty} empty window(s) skipped).")
        self.send("ewb_range_done", folder=str(dest), files=saved, empty=empty)

    # ------------------------------------------------------------------ RETURNS DASHBOARD (UI)
    def _select_label(self, css, text):
        pg = self._pg()
        sel = pg.locator(css)
        sel.wait_for(state="visible")
        for _ in range(20):
            opts = [o.strip() for o in sel.locator("option").all_inner_texts()]
            match = next((o for o in opts if text.lower() in o.lower()), None)
            if match:
                sel.select_option(label=match)
                pg.wait_for_timeout(600)
                return
            pg.wait_for_timeout(300)
        raise RuntimeError(f"'{text}' not available in {css}")

    def _dash_period(self, fy, month):
        self.nav(PAGES["returns_dashboard"])
        pg = self._pg()
        self._select_label(RETURNS_DASH["fy"], fy)
        self._select_label(RETURNS_DASH["quarter"], quarter_label(month))
        self._select_label(RETURNS_DASH["month"], month)
        pg.get_by_role("button", name=re.compile(r"^\s*search\s*$", re.I)).first.click()
        pg.wait_for_function("() => [...document.querySelectorAll('button')].some(b => b.offsetParent && "
                             "/^(DOWNLOAD|VIEW)/.test(b.innerText.trim()))", timeout=25000)
        pg.wait_for_timeout(800)

    def _open_2b_site(self, fy, month):
        self._dash_period(fy, month)
        pg = self._pg()
        host = re.escape(GSTR2B.split("//", 1)[1])
        with pg.expect_navigation(url=re.compile(host), timeout=45000):
            if not pg.evaluate(FORM_OF_JS, ["GSTR2B", "DOWNLOAD"]):
                raise RuntimeError("GSTR-2B tile not shown for this month")
        pg.wait_for_timeout(2500)

    def _portal_3b_pdf(self, fy, month, folder: Path, prd: str):
        self._dash_period(fy, month)
        pg = self._pg()
        with pg.expect_download(timeout=90000) as dl:
            if not pg.evaluate(FORM_OF_JS, ["GSTR3B", "DOWNLOAD"]):
                raise RuntimeError("GSTR-3B DOWNLOAD button not shown")
        target = folder / f"{self.gstin}_GSTR3B_{prd_label(prd)}_portal.pdf"
        dl.value.save_as(str(target))
        return target

    # ------------------------------------------------------------------ binary downloads
    def _download_file(self, path: str):
        """Returns (bytes, filename). Tries in-page fetch, then the browser's request context."""
        res = self._pg().evaluate(FETCH_JS, {"url": path, "method": "GET", "body": None, "binary": True})
        if res.get("b64"):
            return base64.b64decode(res["b64"]), self._fname(res.get("cd"))
        link = None
        txt = res.get("text") or ""
        if txt.lstrip().startswith("<"):
            raise SessionError(f"Portal returned a web page instead of the file for {path}")
        if txt:
            m = re.findall(r"https?://[^\"'\s]+", txt)
            link = m[0] if m else None
            if not link:
                try:
                    j = json.loads(txt)
                    if j.get("status") == 0:
                        raise RuntimeError((j.get("error") or {}).get("message", "file not available"))
                except json.JSONDecodeError:
                    pass
        base = SERVICES if path.startswith("/document") or path.startswith("/services") else RETURNS
        url = link or (base + path if path.startswith("/") else path)
        r = self.ctx.request.get(url, headers={"Referer": self._pg().url}, timeout=120000)
        if not r.ok:
            raise RuntimeError(f"Download failed (HTTP {r.status})")
        return r.body(), self._fname(r.headers.get("content-disposition"))

    @staticmethod
    def _fname(cd):
        m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', cd or "")
        return m.group(1) if m else None

    def _offline(self, typ, prd, folder: Path):
        """GSTR-1 full JSON / GSTR-2A: request now, collect when ready."""
        js = self.api(API["offline_generate"].format(flag=0, prd=prd, typ=typ))
        if js.get("status") == 1:
            d = js.get("data") or {}
            if d.get("status") == 1:
                return "requested - portal prepares it in ~20 min, run again later", None
            rc = int(d.get("rc") or 0)
            saved = []
            for n in range(1, rc + 1):
                variants = [API["offline_file"].format(prd=prd, typ=typ, n=n)]
                if typ == "GSTR2A":
                    variants.append(variants[0] + "&file_type=EX")
                for v in variants:
                    try:
                        data, name = self._download_file(v)
                    except Exception as e:
                        self.log(f"   file {n}: {e}")
                        continue
                    ext = Path(name).suffix if name else (".zip" if data[:2] == b"PK" else ".bin")
                    tag = "excel" if "file_type=EX" in v else "json"
                    target = folder / f"{self.gstin}_{typ}_{prd_label(prd)}_{tag}_file{n}{ext}"
                    target.write_bytes(data)
                    saved.append(target)
                    if data[:2] == b"PK":
                        try:
                            with zipfile.ZipFile(io.BytesIO(data)) as z:
                                z.extractall(folder / f"{typ}_{prd_label(prd)}_extracted")
                        except zipfile.BadZipFile:
                            pass
            return (f"downloaded {len(saved)} file(s)" if saved else "ready on portal but download failed"), \
                (saved[0] if saved else None)
        err = js.get("error") or {}
        if err.get("errorCode") in ERR_IN_PROGRESS:
            return "portal still preparing the file - run again later", None
        return f"portal: {err.get('message', 'no data')}", None

    # ------------------------------------------------------------------ MAIN JOB (multi-year)
    def cmd_run_jobs(self, job: dict):
        self.stop_flag = False
        if not self.gstin:
            self.ensure_origin(SERVICES)
            self.gstin = (self.api(API["ustatus"]) or {}).get("gstin") or ""
            if not self.gstin:
                raise SessionError("Not logged in - please log in first.")
        fys = job.get("fys") or [job.get("fy")]
        fys = [f for f in fys if f]
        results = []

        # copy any user-provided e-way-bill export files into <GSTIN>/ewb/
        ewb_files = job.get("ewb_files") or []
        if ewb_files:
            import shutil
            dest = Path(job["out_dir"]) / self.gstin / "ewb"
            dest.mkdir(parents=True, exist_ok=True)
            n = 0
            for f in ewb_files:
                try:
                    shutil.copy2(f, dest / Path(f).name)
                    n += 1
                except Exception as e:
                    self.log(f"   EWB file {f}: {e}")
            if n:
                results.append({"item": "E-way bill export", "period": "loaded", "status": f"{n} file(s) added",
                                "file": str(dest)})
                self.send("result", **results[-1])

        # notices & orders are not FY-scoped - fetch once per GSTIN
        if "notices" in set(job["items"]):
            self._fetch_notices(job, results)

        last_status = None
        for fy in fys:
            if self.stop_flag:
                break
            try:
                last_status = self._run_one_fy(job, fy, results)
            except SessionError:
                raise
            except Exception as e:
                self.log(f"[FY {fy}] failed: {e}")
                results.append({"item": "FY run", "period": fy, "status": f"error: {e}", "file": ""})
                self.send("result", **results[-1])

        # consolidated e-way bill register (all chunks / all years) -> one workbook
        import dashboard as dash
        gstin_root = Path(job["out_dir"]) / self.gstin
        try:
            import ewaybill as ew
            alldf = ew.load_folder_all(gstin_root / "ewb")
            if alldf is not None and not alldf.empty:
                sheets = ew.consolidated_sheets(alldf)
                cout = rp.write_excel(gstin_root / f"{self.gstin}_EWB_Consolidated.xlsx", sheets,
                                      f"{self.gstin} - all e-way bills (consolidated)")
                results.append({"item": "E-way bills consolidated", "period": f"{len(alldf)} bills",
                                "status": "saved", "file": str(cout)})
                self.send("result", **results[-1])
        except Exception as e:
            self.log(f"   consolidated EWB not built: {e}")

        try:
            self.send("progress", text="Building multi-year overview...")
            overview = dash.generate_overview(gstin_root)
            if overview:
                results.append({"item": "Overview dashboard", "period": f"{len(fys)} year(s)",
                                "status": "saved", "file": str(overview)})
                self.send("result", **results[-1])
                self.send("dashboard_ready", path=str(overview))
        except Exception as e:
            self.log(f"   overview not built: {e}")

        # firm-wide portfolio across every GSTIN downloaded under this folder
        try:
            self.send("progress", text="Building firm portfolio...")
            portfolio = dash.generate_portfolio(Path(job["out_dir"]))
            if portfolio:
                results.append({"item": "Firm portfolio", "period": "all clients",
                                "status": "saved", "file": str(portfolio)})
                self.send("result", **results[-1])
                self.send("portfolio_ready", path=str(portfolio))
        except Exception as e:
            self.log(f"   portfolio not built: {e}")

        self._write_run_log(job, fys, results)
        self.send("jobs_done", results=results, status=last_status)

    def _write_run_log(self, job: dict, fys: list, results: list):
        """Append an audit line so the firm has a record of every run."""
        try:
            log = Path(job["out_dir"]) / "run_history.log"
            ok = sum(1 for r in results if r["status"].startswith(("saved", "downloaded")) or "found" in r["status"])
            line = (f"{datetime.now():%Y-%m-%d %H:%M:%S}\tGSTIN {self.gstin}\tFY {','.join(fys)}\t"
                    f"items={'+'.join(job['items'])}\t{ok} ok / {len(results)} steps\n")
            with open(log, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            self.log(f"   run log: {e}")

    def _fetch_notices(self, job: dict, results: list):
        self.send("progress", text="Reading notices and orders...")
        self.log("Reading notices and orders...")
        gstin_root = Path(job["out_dir"]) / self.gstin
        notices, cases = [], []
        try:
            self.ensure_origin(SERVICES)
            n = self.api(API["notices"], method="POST", body={"onLoad": True})
            notices = n if isinstance(n, list) else []
        except SessionError:
            raise
        except Exception as e:
            self.log(f"   notices: {e}")
        try:
            c = self.api(API["notices_cases"], method="POST", body={"gstIn": self.gstin})
            cases = c if isinstance(c, list) else []
        except Exception as e:
            self.log(f"   cases: {e}")
        (gstin_root / "json").mkdir(parents=True, exist_ok=True)
        rp.save_json(gstin_root / "json" / "notices.json", {"notices": notices, "cases": cases})
        df, summ = rp.notices_frame(notices, cases)
        if not df.empty:
            rp.write_excel(gstin_root / f"{self.gstin}_Notices.xlsx", {"Notices & orders": df},
                           f"{self.gstin} Notices & Orders")
        results.append({"item": "Notices & orders", "period": "all years",
                        "status": f"{summ['total']} found, {summ['pending']} pending", "file": ""})
        self.send("result", **results[-1])

        # download each notice / order as a PDF (best-effort, listed either way)
        if notices:
            self._download_notice_pdfs(notices, gstin_root, results)
        self.send("notices_data", gstin=self.gstin, df=df, summary=summ)

    def _notice_pdf_url(self, n: dict):
        """Return a direct-download PDF URL for a notice/order, or None.
        Only documents with a docId download cleanly (/document/{docId}).
        System-generated u/s 46 notices (GSTR-3A, appDefId only) are view-on-portal,
        so they are listed but not saved as a file."""
        if n.get("docId"):
            return API["notice_doc"].format(docid=n["docId"])
        return None

    def _download_notice_pdfs(self, notices: list, gstin_root: Path, results: list):
        folder = gstin_root / "Notices"
        folder.mkdir(parents=True, exist_ok=True)
        saved = failed = on_portal = 0
        for n in notices:
            self._check_stop()
            url = self._notice_pdf_url(n)
            ref = (n.get("noticeOrderId") or "notice").replace("/", "_")
            if not url:
                on_portal += 1            # system u/s 46 notice - viewable only on the portal
                continue
            try:
                self.send("progress", text=f"Notice PDF {ref}")
                data, name = self._download_file(url)
                if not data or (data[:4] != b"%PDF" and b"<html" in data[:400].lower()):
                    failed += 1
                    continue
                safe = re.sub(r"[<>:\"/\\|?*]", "_", name or f"{ref}.pdf")
                target = folder / f"{self.gstin}_{n.get('type', 'Notice')}_{ref}_{safe}"
                if not target.suffix:
                    target = target.with_suffix(".pdf")
                target.write_bytes(data)
                saved += 1
            except SessionError:
                raise
            except Exception as e:
                self.log(f"   notice PDF {ref}: {e}")
                failed += 1
        bits = [f"{saved} PDF(s) saved"]
        if on_portal:
            bits.append(f"{on_portal} viewable on portal only")
        if failed:
            bits.append(f"{failed} could not be fetched")
        results.append({"item": "Notice PDFs", "period": "all years", "status": ", ".join(bits),
                        "file": str(folder) if saved else ""})
        self.send("result", **results[-1])

    def _run_one_fy(self, job: dict, fy: str, results: list):
        items = set(job["items"])
        months = [m for m in MONTHS if m in job["months"]]
        base = Path(job["out_dir"]) / self.gstin / fy
        raw = base / "json"
        base.mkdir(parents=True, exist_ok=True)
        today = date.today()

        def res(item, period, status, file=None):
            results.append({"item": item, "period": period, "status": status, "file": str(file or "")})
            self.send("result", **results[-1])

        def step(text):
            self._check_stop()
            self.send("progress", text=f"[FY {fy}] {text}")
            self.log(f"[FY {fy}] {text}")

        # ---------------- services.gst.gov.in : turnover + certificate
        aato = None
        step("Reading aggregate turnover and certificates...")
        self.ensure_origin(SERVICES)
        try:
            a = self.api(API["aato"].format(fy=fy))
            lst = a.get("aggTurnoverInfoList") or []
            if lst:
                aato = float(lst[0].get("panFinalTo") or lst[0].get("gstinFinalTo") or 0) or None
        except SessionError:
            raise
        except Exception as e:
            self.log(f"   turnover not available: {e}")
        if "cert" in items:
            try:
                certs = self.api(API["certs"])
                got = False
                for c in certs if isinstance(certs, list) else []:
                    if c.get("docid") and c.get("applnId"):
                        data, name = self._download_file(API["cert_pdf"].format(docid=c["docid"], applnId=c["applnId"]))
                        folder = Path(job["out_dir"]) / self.gstin / "Registration"
                        folder.mkdir(parents=True, exist_ok=True)
                        t = folder / f"{self.gstin}_{c.get('frmno', 'CERT').replace(' ', '')}_{name or 'certificate.pdf'}"
                        t.write_bytes(data)
                        res(c.get("frmdc") or c.get("frmno"), c.get("isdt", ""), "downloaded", t)
                        got = True
                if not got:
                    res("Registration Certificate", "", "no certificate listed on portal")
            except SessionError:
                raise
            except Exception as e:
                res("Registration Certificate", "", f"error: {e}")

        # ---------------- return.gst.gov.in
        step("Opening Returns Dashboard...")
        self.ensure_origin(RETURNS)
        try:
            dd = self.api(API["dropdown"])
            avail = {m["value"] for y in (dd.get("data") or {}).get("Years", []) if y.get("year") == fy
                     for m in y.get("months", [])}
        except SessionError:
            raise
        except Exception:
            avail = set()
        prds = [prd_code(fy, m) for m in months]
        if avail:
            prds = [p for p in prds if p in avail] or prds
        month_of = {prd_code(fy, m): m for m in months}

        rolestatus, efiled, g3b, g1, g2b = {}, [], {}, {}, {}
        if "status" in items:
            for p in prds:
                step(f"Filing status {prd_label(p)}")
                try:
                    rolestatus[p] = self.api(API["rolestatus"].format(prd=p))
                except SessionError:
                    raise
                except Exception as e:
                    self.log(f"   {e}")
            for rtn, rfps in (("GSTR1", ("Monthly", "Quarterly")), ("GSTR3B", ("Monthly", "Quarterly")),
                              ("GSTR9", ("Annual",)), ("GSTR9C", ("Annual",))):
                for rfp in rfps:
                    try:
                        r = self.api(API["efiled"], method="POST",
                                     body={"fy": fy, "rfp": rfp, "qtr": None, "mth": None, "rtntp": rtn})
                        if isinstance(r, list):
                            efiled.extend(r)
                    except SessionError:
                        raise
                    except Exception as e:
                        self.log(f"   e-filed {rtn}/{rfp}: {e}")
            rp.save_json(raw / "rolestatus.json", rolestatus)
            rp.save_json(raw / "efiled.json", efiled)
            res("Filing status", fy, f"{len(efiled)} filed return(s) found")

        if "gstr3b" in items:
            for p in prds:
                step(f"GSTR-3B data {prd_label(p)}")
                try:
                    j = self.api(API["gstr3b"].format(prd=p))
                    if j.get("status") == 1 and j.get("data"):
                        g3b[p] = j
                        rp.save_json(raw / f"GSTR3B_{prd_label(p)}.json", j)
                    else:
                        res("GSTR-3B", prd_label(p), f"not available: {(j.get('error') or {}).get('message', 'not filed')}")
                except SessionError:
                    raise
                except Exception as e:
                    res("GSTR-3B", prd_label(p), f"error: {e}")

        if "gstr1" in items:
            for p in prds:
                step(f"GSTR-1 summary {prd_label(p)}")
                try:
                    j = self.api(API["gstr1_summary"].format(prd=p))
                    if j.get("status") == 1 and j.get("data"):
                        g1[p] = j
                        rp.save_json(raw / f"GSTR1_summary_{prd_label(p)}.json", j)
                    else:
                        res("GSTR-1", prd_label(p), f"not available: {(j.get('error') or {}).get('message', '')}")
                except SessionError:
                    raise
                except Exception as e:
                    res("GSTR-1", prd_label(p), f"error: {e}")

        if "gstr9" in items:
            step("GSTR-9 data")
            try:
                fp = "03" + str(int(fy[:4]) + 1)
                j = self.api(API["gstr9"].format(fp=fp))
                if j.get("status") == 1 and j.get("data"):
                    rp.save_json(raw / f"GSTR9_{fy}.json", j)
                    out = rp.write_excel(base / f"{self.gstin}_GSTR9_{fy}.xlsx", {"GSTR-9": rp.gstr9_frame(j)},
                                         f"{self.gstin} GSTR-9 FY {fy}")
                    res("GSTR-9", fy, "saved", out)
                else:
                    res("GSTR-9", fy, f"not available: {(j.get('error') or {}).get('message', '')}")
            except SessionError:
                raise
            except Exception as e:
                res("GSTR-9", fy, f"error: {e}")

        for key, typ, label in (("gstr1json", "GSTR1", "GSTR-1 full JSON"), ("gstr2a", "GSTR2A", "GSTR-2A")):
            if key in items:
                folder = base / typ
                folder.mkdir(exist_ok=True)
                for p in prds:
                    step(f"{label} {prd_label(p)}")
                    try:
                        st, f = self._offline(typ, p, folder)
                        res(label, prd_label(p), st, f)
                    except SessionError:
                        raise
                    except Exception as e:
                        res(label, prd_label(p), f"error: {e}")

        if "pdf3b" in items:
            folder = base / "PDF"
            folder.mkdir(exist_ok=True)
            for p in prds:
                step(f"GSTR-3B portal PDF {prd_label(p)}")
                try:
                    t = self._portal_3b_pdf(fy, month_of[p], folder, p)
                    res("GSTR-3B PDF", prd_label(p), "downloaded", t)
                except SessionError:
                    raise
                except Exception as e:
                    res("GSTR-3B PDF", prd_label(p), f"not saved: {e}")

        # ---------------- gstr2b.gst.gov.in (opened via dashboard tile)
        if "gstr2b" in items and prds:
            opened = False
            for p in reversed(prds):
                try:
                    step(f"Opening GSTR-2B site via {prd_label(p)} tile...")
                    self._open_2b_site(fy, month_of[p])
                    opened = True
                    break
                except SessionError:
                    raise
                except Exception as e:
                    self.log(f"   {e}")
            if not opened:
                res("GSTR-2B", fy, "could not open GSTR-2B page")
            else:
                for p in prds:
                    step(f"GSTR-2B data {prd_label(p)}")
                    try:
                        j = self.api(API["gstr2b"].format(prd=p))
                        d = j.get("data") if isinstance(j, dict) else None
                        if d and (d.get("docdata") is not None or d.get("itcsumm") is not None):
                            g2b[p] = j
                            rp.save_json(raw / f"GSTR2B_{prd_label(p)}.json", j)
                        else:
                            res("GSTR-2B", prd_label(p), f"not available: {(j.get('error') or {}).get('message', '')[:120]}")
                    except SessionError:
                        raise
                    except Exception as e:
                        res("GSTR-2B", prd_label(p), f"error: {e}")
            try:
                self.nav(PAGES["returns_dashboard"])
            except Exception:
                pass

        # ---------------- build Excel workbooks (pandas)
        step("Building Excel workbooks...")
        g3_detail = g3_sum = g1_tot = g2_tot = None
        nil_flags = {}
        if g3b:
            g3_detail, g3_sum = rp.gstr3b_frames(g3b)
            out = rp.write_excel(base / f"{self.gstin}_GSTR3B_{fy}.xlsx",
                                 {"Monthly summary": g3_sum, "Table-wise detail": g3_detail}, f"{self.gstin} GSTR-3B FY {fy}")
            res("GSTR-3B", f"{len(g3b)} month(s)", "saved", out)
            nil_flags.update({("GSTR-3B", r["Period"]): r["Nil return"] == "Yes" for _, r in g3_sum.iterrows()})
        if g1:
            g1_long, g1_piv, g1_tot = rp.gstr1_frames(g1)
            g1_sheets = {"Monthly totals": g1_tot, "Section x month": g1_piv, "All sections": g1_long}
            # party-wise (recipient-GSTIN) B2B, when the GSTR-1 full JSON has been collected
            try:
                g1_b2b = rp.load_gstr1_b2b(base)
                if g1_b2b is not None and not g1_b2b.empty:
                    g1_sheets["B2B party-wise"] = g1_b2b
            except Exception as e:
                self.log(f"   GSTR-1 B2B party-wise not added: {e}")
            out = rp.write_excel(base / f"{self.gstin}_GSTR1_{fy}.xlsx", g1_sheets, f"{self.gstin} GSTR-1 FY {fy}")
            note = " + B2B party-wise" if "B2B party-wise" in g1_sheets else ""
            res("GSTR-1", f"{len(g1)} month(s){note}", "saved", out)
            nil_flags.update({("GSTR-1", prd_label(p)): str((j.get("data") or {}).get("isnil", "")).upper() == "Y"
                              for p, j in g1.items()})
        if g2b:
            sheets, g2_tot = rp.gstr2b_frames(g2b)
            if g2_tot is not None and not g2_tot.empty:
                sheets = {"ITC by month": g2_tot, **sheets}
            out = rp.write_excel(base / f"{self.gstin}_GSTR2B_{fy}.xlsx", sheets, f"{self.gstin} GSTR-2B FY {fy}")
            res("GSTR-2B", f"{len(g2b)} month(s)", "saved", out)

        status_df = None
        if "status" in items:
            status_df = comp.build_status(fy, rolestatus, efiled, self.gstin, aato, nil_flags, today)
            recon = rp.reconciliation(g1_tot, g3_sum, g2_tot)
            summ = comp.summary(status_df)
            summ_df = rp.pd.DataFrame([{"GSTIN": self.gstin, "FY": fy, "Aggregate turnover": aato,
                                        "Returns due": summ["due"], "Filed on time": summ["on_time"],
                                        "Filed late": summ["late"], "Overdue": summ["pending"],
                                        "Compliance score %": summ["score"], "Est. late fee": summ["late_fee"],
                                        "Generated on": today.strftime("%d-%m-%Y")}])
            out = rp.write_excel(base / f"{self.gstin}_Compliance_{fy}.xlsx",
                                 {"Summary": summ_df, "Return status": status_df, "Month grid": comp.month_grid(status_df),
                                  "Reconciliation": recon}, f"{self.gstin} Compliance FY {fy}")
            res("Compliance dashboard", fy, "saved", out)
            self.send("status_data", fy=fy, gstin=self.gstin, status=status_df, recon=recon, aato=aato,
                      path=str(out) if out else "")

            # ---- pre-filing issues & risk analysis (Excel)
            try:
                import issues as iss
                import ewaybill as ew
                ewb_month = None
                ewb_folder = base.parent / "ewb"
                ewb_frames = []
                if ewb_folder.exists():
                    for ext in ("*.xlsx", "*.xls", "*.csv"):
                        for f in ewb_folder.glob(ext):
                            try:
                                ewb_frames.append(ew.load_export(f))
                            except Exception:
                                pass
                ewb_all = rp.pd.concat(ewb_frames, ignore_index=True).drop_duplicates(subset=["EWB no"]) \
                    if ewb_frames else None
                if ewb_all is not None and not ewb_all.empty:
                    y0 = int(fy[:4])
                    fyset = {f"{(y0 if m >= 4 else y0 + 1)}-{m:02d}" for m in list(range(4, 13)) + list(range(1, 4))}
                    ewb_fy = ewb_all[ewb_all["Period"].isin(fyset)].reset_index(drop=True)
                    if not ewb_fy.empty:
                        ewb_month = ew.monthwise_outward(ewb_fy)
                        an, _ = ew.analyse_ewb(ewb_fy)
                        # party-wise (recipient-GSTIN) EWB vs GSTR-1 B2B
                        g1_b2b = rp.load_gstr1_b2b(base)
                        ewb_party = ew.partywise_outward(ewb_fy)
                        party_recon = ew.reconcile_partywise_gstr1(ewb_party, g1_b2b)
                        sheets = {"EWB vs GSTR-1 (month)": ew.reconcile_with_gstr1(ewb_month, g1_tot),
                                  "EWB vs GSTR-1 (party)": party_recon,
                                  "Line level": ewb_fy, **{k[:31]: v for k, v in an.items()}}
                        eout = rp.write_excel(base / f"{self.gstin}_EWB_{fy}.xlsx", sheets, f"{self.gstin} E-way bills FY {fy}")
                        pr = ew.partywise_summary(party_recon)
                        note = "" if (g1_b2b is not None and not g1_b2b.empty) else \
                            " (party-wise needs GSTR-1 full JSON - tick it and collect after ~20 min)"
                        res("E-way bill analysis", fy,
                            f"saved; party-wise: {pr['mismatch']} mismatch, {pr['ewb_only']} EWB-only{note}", eout)
                g9j = None
                for gf in raw.glob(f"GSTR9_{fy}.json"):
                    g9j = rp.json.loads(gf.read_text(encoding="utf-8"))
                issues_df, isumm = iss.analyse_filing(fy, status_df, g3_sum, g1_tot, g2_tot, recon, g9j, aato, ewb_month, today)
                iout = rp.write_excel(base / f"{self.gstin}_Issues_{fy}.xlsx", {"Issues & risk": issues_df},
                                      f"{self.gstin} Pre-filing issues FY {fy}")
                res("Pre-filing issues", fy, f"{isumm['high']} high, {isumm['medium']} medium", iout)
            except Exception as e:
                self.log(f"   issues/EWB not built: {e}")

        # ---- build the shareable HTML dashboard from everything just saved
        try:
            step("Building HTML dashboard...")
            import dashboard as dash
            html_out = dash.generate(base)
            res("HTML dashboard", fy, "saved", html_out)
            self.send("dashboard_ready", path=str(html_out))
        except Exception as e:
            self.log(f"   dashboard not built: {e}")

        return status_df
