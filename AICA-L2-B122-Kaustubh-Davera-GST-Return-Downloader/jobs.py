"""Download job: runs in a background thread, talks to the UI through
`state()` (polled) and `respond()` (captcha / manual-step answers)."""
import itertools
import os
import shutil
import threading
import time
import traceback
from datetime import datetime

import blocked
from naming import (FORM_LABELS, build_filename, clean_name, fy_label, period_label,
                    quarter_end_month, quarter_label)
from settings import app_dir

_ids = itertools.count(1)


class SkipClient(Exception):
    pass


class LoginStop(Exception):
    def __init__(self, msg, block=False):
        super().__init__(msg)
        self.block = block


class JobRunner(threading.Thread):
    def __init__(self, cfg, clients, periods, forms, save_root, log=print, tasks=None):
        """periods: [(year, month)], forms: {"GSTR2B": {"excel":bool,"json":bool}, "GSTR1":True, "GSTR3B":True}
        tasks: optional exact list of (gstin, form, year, month, label) - used by "Retry failed"."""
        super().__init__(daemon=True)
        self.cfg = cfg
        self.clients = clients
        self.forms = forms
        self.save_root = save_root
        self.log = log
        self.lock = threading.Lock()
        self.rows = []
        self.prompt = None
        self._answer = None
        self._event = threading.Event()
        self.stop_flag = False
        self.pause_flag = False
        self.finished = False
        self.started_at = datetime.now()
        self.title = ""
        self.tmp_dir = os.path.join(app_dir(), "_downloads_tmp")
        self.portal = None
        if tasks:
            by_gstin = {c.gstin: c for c in clients}
            for g, form, y, m, label in tasks:
                self._add_row(by_gstin[g], form, y, m, label)
            self.title = f"Retry · {len(tasks)} item(s)"
        else:
            self._plan(periods)

    # ------------------------------------------------------------ planning
    def _plan(self, periods):
        for c in self.clients:
            seen = set()
            for (y, m) in periods:
                for form in ("GSTR2B", "GSTR1", "GSTR3B"):
                    if not self.forms.get(form):
                        continue
                    if form in ("GSTR1", "GSTR3B") and c.quarterly:
                        qm = quarter_end_month(m)
                        key = (form, y, qm)
                        if key in seen:
                            continue
                        seen.add(key)
                        self._add_row(c, form, y, qm, quarter_label(y, m))
                    else:
                        self._add_row(c, form, y, m, period_label(y, m))
        forms = [FORM_LABELS[f] for f in ("GSTR2B", "GSTR1", "GSTR3B") if self.forms.get(f)]
        months = sorted(set(periods))
        per = period_label(*months[0]) if len(months) == 1 else \
            f"{period_label(*months[0])} to {period_label(*months[-1])}"
        who = self.clients[0].display_name if len(self.clients) == 1 else f"{len(self.clients)} clients"
        self.title = f"{', '.join(forms)} · {per} · {who}"

    def _add_row(self, c, form, y, m, label):
        self.rows.append({
            "id": next(_ids), "gstin": c.gstin, "client": c.display_name, "form": form,
            "form_label": FORM_LABELS[form], "year": y, "month": m, "period": label,
            "status": "pending", "note": "In queue", "files": [],
        })

    # ------------------------------------------------------------ UI bridge
    def state(self) -> dict:
        with self.lock:
            counts = {}
            for r in self.rows:
                counts[r["status"]] = counts.get(r["status"], 0) + 1
            return {
                "title": self.title,
                "rows": [dict(r) for r in self.rows],
                "counts": counts,
                "prompt": dict(self.prompt) if self.prompt else None,
                "running": not self.finished,
                "paused": self.pause_flag,
                "stopping": self.stop_flag and not self.finished,
            }

    def respond(self, prompt_id, answer: dict) -> bool:
        with self.lock:
            if not self.prompt or self.prompt.get("id") != prompt_id:
                return False
            self._answer = answer
            self.prompt = None
        self._event.set()
        return True

    def _ask(self, prompt: dict, watch=None) -> dict:
        """Show a prompt and wait. `watch()` may return an answer by itself
        (used to auto-finish a manual step when the file shows up)."""
        prompt = dict(prompt, id=next(_ids))
        with self.lock:
            self._answer = None
            self._event.clear()
            self.prompt = prompt
        while True:
            if self._event.wait(0.8):
                return self._answer or {"action": "skip"}
            if self.stop_flag:
                with self.lock:
                    self.prompt = None
                return {"action": "stop"}
            if watch:
                auto = watch()
                if auto:
                    with self.lock:
                        self.prompt = None
                    return auto

    def _set(self, row, status, note=None, files=None):
        with self.lock:
            row["status"] = status
            if note is not None:
                row["note"] = note
            if files is not None:
                row["files"] = files

    def _client_rows(self, c):
        return [r for r in self.rows if r["gstin"] == c.gstin]

    def _mark_all(self, c, status, note, only_pending=True):
        for r in self._client_rows(c):
            if not only_pending or r["status"] in ("pending", "running", "waiting"):
                self._set(r, status, note)

    def _wait_if_paused(self):
        while self.pause_flag and not self.stop_flag:
            time.sleep(0.5)

    # ------------------------------------------------------------ main loop
    def run(self):
        try:
            self._run()
        except Exception as e:
            self.log("Job crashed:\n" + traceback.format_exc())
            for r in self.rows:
                if r["status"] in ("pending", "running", "waiting"):
                    self._set(r, "failed", f"Stopped: {e}")
        finally:
            if self.portal:
                self.portal.quit()
            with self.lock:
                self.prompt = None
            self.finished = True

    def _run(self):
        from portal import GSTPortal   # selenium import only when a job starts
        if os.path.isdir(self.tmp_dir):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
        os.makedirs(self.tmp_dir, exist_ok=True)
        total = len(self.clients)
        delay = float(self.cfg["browser"].get("delay_between_clients", 3))

        for idx, c in enumerate(self.clients):
            if self.stop_flag:
                self._mark_all(c, "skipped", "Stopped by user")
                continue
            self._wait_if_paused()
            pending = [r for r in self._client_rows(c) if r["status"] == "pending"]
            if not pending:
                continue
            errors = [m for lvl, m in c.issues if lvl == "error"]
            if errors:
                self._mark_all(c, "skipped", f"Skipped: {errors[0]}")
                continue
            entry = blocked.check(c)
            if entry:
                self._mark_all(c, "blocked", f"Blocked ({entry.get('time')}): {entry.get('reason')}")
                continue

            if self.portal is None or not self.portal.alive():
                try:
                    self.portal = GSTPortal(self.cfg, self.tmp_dir, self.log)
                    self.portal.start()
                except Exception as e:
                    self.log(traceback.format_exc())
                    for r in self.rows:
                        if r["status"] == "pending":
                            self._set(r, "failed", f"Chrome could not start: {str(e).splitlines()[0][:150]}")
                    return

            nxt = next((x.display_name for x in self.clients[idx + 1:]), "")
            try:
                for r in pending:
                    self._set(r, "waiting", "Logging in")
                self._login(c, idx, total, nxt)
            except LoginStop as e:
                if e.block:
                    blocked.block(c, str(e))
                    self._mark_all(c, "blocked", str(e))
                else:
                    self._mark_all(c, "failed", str(e))
                continue
            except SkipClient:
                self._mark_all(c, "skipped", "Stopped by user" if self.stop_flag else "Skipped by user")
                continue
            except Exception as e:
                self.log(traceback.format_exc())
                self._mark_all(c, "failed", f"Login page problem: {str(e).splitlines()[0][:150]}")
                continue

            for r in pending:
                self._set(r, "pending", "In queue")
            for r in pending:
                if self.stop_flag:
                    self._set(r, "skipped", "Stopped by user")
                    continue
                self._wait_if_paused()
                self._process(c, r)
            self.portal.logout()
            if idx < total - 1 and not self.stop_flag:
                time.sleep(delay)

    # ------------------------------------------------------------ login
    def _login(self, c, idx, total, nxt):
        """At most one password check per client. Wrong captcha = retry with a
        fresh login page; anything else that is not success = stop."""
        p = self.portal
        max_tries = int(self.cfg["browser"].get("max_captcha_tries", 3))
        tries = 0
        error = ""
        p.open_login(c)
        while True:
            if self.stop_flag:
                raise SkipClient()
            try:
                img = p.captcha_image_b64()
            except Exception:
                img = ""
            ans = self._ask({
                "type": "captcha", "client": c.display_name, "gstin": c.gstin,
                "image": f"data:image/png;base64,{img}" if img else "",
                "attempt": tries + 1, "max": max_tries, "index": idx + 1, "total": total,
                "next": nxt, "error": error,
            })
            act = ans.get("action")
            if act == "stop":
                self.stop_flag = True
                raise SkipClient()
            if act == "skip":
                raise SkipClient()
            if act == "refresh":
                try:
                    p.refresh_captcha()
                except Exception:
                    p.open_login(c)
                error = ""
                continue
            text = (ans.get("text") or "").strip()
            if not text:
                error = "Type the captcha first"
                continue

            tries += 1
            result = p.submit_login(text)
            self.log(f"{c.gstin}: login result = {result}")
            if result == "success":
                p.dismiss_popups()
                return
            if result == "captcha":
                if tries >= max_tries:
                    raise LoginStop(f"Wrong captcha {tries} times. Skipped (password not rejected).")
                error = "Wrong captcha. Please type the new one."
                p.open_login(c)          # fresh page, no stale messages
                continue
            if result == "bad_credentials":
                raise LoginStop("Wrong user ID or password. Stopped after 1 attempt. Update the password to unblock.", block=True)
            if result == "locked":
                raise LoginStop("Account locked on the portal. Reset it with the client's OTP.", block=True)
            if result == "expired":
                raise LoginStop("Password expired on the portal. Change it, then update it here.", block=True)
            raise LoginStop("Login result unclear. Check the portal by hand before trying again.", block=True)

    # ------------------------------------------------------------ one form
    def _expected(self, row) -> int:
        if row["form"] == "GSTR2B":
            o = self.forms["GSTR2B"]
            return int(bool(o.get("excel"))) + int(bool(o.get("json")))
        return 1

    def _process(self, c, row, allow_retry=True):
        from portal import NotAvailable
        p = self.portal
        self._set(row, "running", "Downloading")
        y, m, form = row["year"], row["month"], row["form"]
        before = p.snapshot()
        try:
            if form == "GSTR2B":
                o = self.forms["GSTR2B"]
                files = p.download_gstr2b(y, m, bool(o.get("excel")), bool(o.get("json")))
            elif form == "GSTR1":
                files = p.download_gstr1(y, m)
            else:
                files = p.download_gstr3b(y, m)
            self._store(c, row, files)
            return
        except NotAvailable as e:
            self._set(row, "notavail", str(e))
            return
        except Exception as e:
            reason = str(e).splitlines()[0][:160] if str(e) else e.__class__.__name__
            self.log(f"{c.gstin} {form} {row['period']}: {traceback.format_exc()}")

        # ---- manual fallback: user clicks in Chrome, app catches the file
        need = self._expected(row)
        self._set(row, "manual", f"{reason}. Click it in Chrome")

        def watch():
            files = p.new_files(before)
            return {"action": "done", "auto": True} if len(files) >= need else None

        ans = self._ask({
            "type": "manual", "client": c.display_name, "gstin": c.gstin,
            "form": row["form_label"], "period": row["period"], "reason": reason, "need": need,
        }, watch=watch)
        act = ans.get("action")
        if act == "retry" and allow_retry:
            return self._process(c, row, allow_retry=False)
        if act == "done":
            time.sleep(1)
            files = p.new_files(before)
            if files:
                self._store(c, row, files)
            else:
                self._set(row, "failed", "No downloaded file found")
            return
        if act == "stop":
            self._set(row, "skipped", "Stopped by user")
            return
        self._set(row, "failed", f"Skipped: {reason}")

    def _store(self, c, row, files):
        folder = os.path.join(self.save_root, clean_name(c.display_name), fy_label(row["year"], row["month"]))
        os.makedirs(folder, exist_ok=True)
        out = []
        used = set()
        for f in files:
            ext = os.path.splitext(f)[1].lstrip(".").lower() or "dat"
            name = build_filename(c.display_name, row["form"], row["period"], ext)
            if name in used:   # two files with the same extension
                base, e = os.path.splitext(name)
                name = f"{base} ({len(used) + 1}){e}"
            used.add(name)
            dest = os.path.join(folder, name)
            if os.path.exists(dest):
                os.remove(dest)       # newer download replaces the old one
            shutil.move(f, dest)
            out.append(dest)
        self._set(row, "done", " + ".join(os.path.basename(x) for x in out), files=out)
