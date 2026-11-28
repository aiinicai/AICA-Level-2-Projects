"""Functions the UI (JavaScript) calls through pywebview.

Every public method returns plain JSON-able data: {"ok": True, ...} or
{"ok": False, "error": "..."}. Attributes starting with "_" are hidden from JS.
"""
import os
import subprocess
import sys
import threading
import traceback
from datetime import date, datetime

import blocked
import clients as cl
import emailer
import settings
from jobs import JobRunner
from naming import FORM_LABELS, fy_start, is_period_available


def _err(e) -> dict:
    return {"ok": False, "error": str(e) or e.__class__.__name__}


class Api:
    def __init__(self):
        self._window = None
        self._cfg = settings.load()
        self._clients = []
        self._load_error = ""
        self._job = None
        self._last_forms = None
        self._email_state = {}       # gstin -> "sent" | "skipped"
        self._done_rows = {}         # gstin -> {row_key: row}
        self._lock = threading.Lock()
        self._log_path = os.path.join(settings.app_dir(), "app.log")
        self._reload()

    # ------------------------------------------------------------ helpers
    def _log(self, msg):
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now():%d-%b-%Y %H:%M:%S}] {msg}\n")
        except OSError:
            pass

    def _excel_path(self):
        return settings.resolve(self._cfg.get("clients_excel", "clients.xlsx"))

    def _reload(self):
        path = self._excel_path()
        if not os.path.exists(path) and os.path.basename(path) == "clients.xlsx":
            cl.create_template(path)
        try:
            self._clients = cl.load_clients(path)
            self._load_error = ""
        except Exception as e:
            self._clients = []
            self._load_error = str(e)

    def _client(self, gstin):
        return next((c for c in self._clients if c.gstin == gstin), None)

    def _client_view(self, c):
        d = c.public()
        b = blocked.check(c)
        d["blocked"] = bool(b)
        d["blocked_reason"] = b.get("reason") if b else ""
        warn = int(self._cfg.get("password_age_warn_days", 60))
        d["pwd_old"] = d["pwd_age_days"] is not None and d["pwd_age_days"] > warn
        d["errors"] = [m for lvl, m in c.issues if lvl == "error"]
        d["warnings"] = [m for lvl, m in c.issues if lvl == "warn"]
        return d

    def _open_dialog(self, kind, **kw):
        import webview
        fd = getattr(webview, "FileDialog", None)
        if fd is not None:
            k = {"folder": fd.FOLDER, "open": fd.OPEN}[kind]
        else:
            k = {"folder": webview.FOLDER_DIALOG, "open": webview.OPEN_DIALOG}[kind]
        res = self._window.create_file_dialog(k, **kw)
        if not res:
            return None
        return res[0] if isinstance(res, (list, tuple)) else res

    # ------------------------------------------------------------ init / clients
    def get_init(self):
        cfg = self._cfg
        today = date.today()
        return {
            "ok": True,
            "excel_path": self._excel_path(),
            "download_folder": settings.resolve(cfg.get("download_folder")),
            "firm_name": cfg.get("firm_name", ""),
            "today": [today.year, today.month, today.day],
            "current_fy": fy_start(today.year, today.month),
            "pwd_warn_days": cfg.get("password_age_warn_days", 60),
            "load_error": self._load_error,
            "clients": [self._client_view(c) for c in self._clients],
            "loaded_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        }

    def reload_clients(self):
        self._reload()
        return self.get_init()

    def choose_excel(self):
        try:
            path = self._open_dialog("open", file_types=("Excel files (*.xlsx)", "All files (*.*)"))
            if not path:
                return {"ok": False, "cancelled": True}
            self._cfg["clients_excel"] = path
            settings.save(self._cfg)
            return self.reload_clients()
        except Exception as e:
            return _err(e)

    def choose_folder(self):
        try:
            path = self._open_dialog("folder")
            if not path:
                return {"ok": False, "cancelled": True}
            self._cfg["download_folder"] = path
            settings.save(self._cfg)
            return {"ok": True, "path": path}
        except Exception as e:
            return _err(e)

    def set_download_folder(self, path):
        path = (path or "").strip()
        if not path:
            return _err("Folder path is empty")
        self._cfg["download_folder"] = path
        settings.save(self._cfg)
        return {"ok": True, "path": settings.resolve(path)}

    def open_excel(self):
        return self.open_path(self._excel_path())

    def save_client(self, original_gstin, data):
        """original_gstin empty = add a new client."""
        try:
            data = dict(data or {})
            gstin = (data.get("gstin") or "").upper().strip()
            if not gstin:
                return _err("GSTIN is required")
            if not original_gstin and not data.get("password"):
                return _err("Password is required for a new client")
            if not (data.get("login_id") or "").strip():
                return _err("Login ID is required")
            pwd = data.get("password")
            if pwd and pwd != pwd.strip():
                return _err("Password starts or ends with a space. Remove the space and save again.")
            if self._job and not self._job.finished:
                return _err("A download is running. Save after it finishes.")
            cl.save_client(self._excel_path(), original_gstin or None, data)
            if data.get("unblock"):
                blocked.unblock(original_gstin or gstin)
            self._reload()
            return dict(self.get_init(), saved=gstin)
        except Exception as e:
            self._log(traceback.format_exc())
            return _err(e)

    def unblock(self, gstin):
        blocked.unblock(gstin)
        return self.get_init()

    # ------------------------------------------------------------ jobs
    def start_job(self, params):
        try:
            if self._job and not self._job.finished:
                return _err("A download is already running")
            gstins = params.get("gstins") or []
            periods = [tuple(p) for p in params.get("periods") or []]
            forms = params.get("forms") or {}
            if not gstins:
                return _err("Select at least one client")
            if not periods:
                return _err("Select at least one month")
            periods = [p for p in periods if is_period_available(*p)]
            if not periods:
                return _err("Selected month(s) are not over yet")
            if not any(forms.get(k) for k in ("GSTR1", "GSTR3B")) and not (
                    forms.get("GSTR2B") and (forms["GSTR2B"].get("excel") or forms["GSTR2B"].get("json"))):
                return _err("Select at least one form")
            if forms.get("GSTR2B") and not (forms["GSTR2B"].get("excel") or forms["GSTR2B"].get("json")):
                forms["GSTR2B"] = False
            folder = params.get("folder") or self._cfg.get("download_folder")
            if folder:
                self._cfg["download_folder"] = folder
                settings.save(self._cfg)
            save_root = settings.resolve(self._cfg.get("download_folder"))
            os.makedirs(save_root, exist_ok=True)
            self._reload()
            chosen = [self._client(g) for g in gstins if self._client(g)]
            if not chosen:
                return _err("Selected clients not found. Reload the client list.")
            self._last_forms = forms
            self._job = JobRunner(self._cfg, chosen, sorted(set(periods)), forms, save_root, log=self._log)
            self._job.start()
            return {"ok": True}
        except Exception as e:
            self._log(traceback.format_exc())
            return _err(e)

    def retry_failed(self):
        if not self._job or not self._job.finished:
            return _err("Wait for the current run to finish")
        st = self._job.state()
        tasks = [(r["gstin"], r["form"], r["year"], r["month"], r["period"])
                 for r in st["rows"] if r["status"] in ("failed", "manual")
                 or (r["status"] == "skipped" and "user" in r["note"].lower())]
        if not tasks:
            return _err("Nothing to retry")
        self._reload()
        gst = {t[0] for t in tasks}
        chosen = [c for c in self._clients if c.gstin in gst]
        save_root = settings.resolve(self._cfg.get("download_folder"))
        self._job = JobRunner(self._cfg, chosen, [], self._last_forms or {}, save_root,
                              log=self._log, tasks=[t for t in tasks if self._client(t[0])])
        self._job.start()
        return {"ok": True}

    def get_status(self):
        if not self._job:
            return {"ok": True, "job": None}
        st = self._job.state()
        # remember finished rows for the Email tab
        with self._lock:
            for r in st["rows"]:
                if r["status"] == "done" and r["files"]:
                    key = (r["form"], r["year"], r["month"])
                    self._done_rows.setdefault(r["gstin"], {})[key] = r
        return {"ok": True, "job": st}

    def respond_prompt(self, prompt_id, answer):
        if not self._job:
            return {"ok": False}
        return {"ok": self._job.respond(prompt_id, answer or {})}

    def pause(self, value):
        if self._job:
            self._job.pause_flag = bool(value)
        return {"ok": True}

    def stop_job(self):
        if self._job:
            self._job.stop_flag = True
            self._job.pause_flag = False
        return {"ok": True}

    def export_report(self):
        try:
            if not self._job:
                return _err("No download run yet")
            import openpyxl
            from openpyxl.styles import Font, PatternFill
            st = self._job.state()
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Download report"
            ws.append(["Client", "GSTIN", "Form", "Period", "Status", "File / reason"])
            for c in ws[1]:
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = PatternFill("solid", fgColor="0F766E")
            labels = {"done": "Downloaded", "failed": "Failed", "blocked": "Blocked", "notavail": "Not available",
                      "skipped": "Skipped", "manual": "Needs attention", "pending": "Pending",
                      "running": "Running", "waiting": "Waiting"}
            for r in st["rows"]:
                ws.append([r["client"], r["gstin"], r["form_label"], r["period"],
                           labels.get(r["status"], r["status"]), r["note"]])
            for col, w in zip("ABCDEF", (32, 18, 10, 18, 16, 70)):
                ws.column_dimensions[col].width = w
            root = settings.resolve(self._cfg.get("download_folder"))
            os.makedirs(root, exist_ok=True)
            path = os.path.join(root, f"Download Report {datetime.now():%d-%b-%Y %H%M}.xlsx")
            wb.save(path)
            self.open_path(path)
            return {"ok": True, "path": path}
        except Exception as e:
            return _err(e)

    # ------------------------------------------------------------ email
    def _email_rows(self, gstin):
        return sorted(self._done_rows.get(gstin, {}).values(),
                      key=lambda r: (r["year"], r["month"], r["form"]))

    def email_list(self):
        self.get_status()
        out = []
        for gstin in self._done_rows:
            c = self._client(gstin)
            if not c:
                continue
            rows = self._email_rows(gstin)
            files = [f for r in rows for f in r["files"]]
            st = self._email_state.get(gstin)
            if not st:
                st = "ready" if c.emails() else "noemail"
            forms = []
            for r in rows:
                if r["form_label"] not in forms:
                    forms.append(r["form_label"])
            out.append({"gstin": gstin, "name": c.display_name, "status": st,
                        "summary": f"{len(files)} file(s) · {', '.join(forms)}"})
        return {"ok": True, "items": out,
                "sender": self._cfg["email"].get("sender_email") or "(not set up)"}

    def email_preview(self, gstin):
        c = self._client(gstin)
        if not c:
            return _err("Client not found")
        try:
            p = emailer.build(self._cfg, c, self._email_rows(gstin))
            p.pop("attachments")
            return dict(p, ok=True, status=self._email_state.get(gstin, "ready" if c.emails() else "noemail"))
        except Exception as e:
            return _err(e)

    def send_email(self, gstin, to, cc, subject, body):
        c = self._client(gstin)
        if not c:
            return _err("Client not found")
        try:
            p = emailer.build(self._cfg, c, self._email_rows(gstin))
            if p["too_big"]:
                return _err(f"Attachments are {p['size_mb']} MB. Gmail allows about 25 MB.")
            port = emailer.send(self._cfg, to, cc, subject, body, p["attachments"])
            if port and port != int(self._cfg["email"].get("smtp_port") or 587):
                self._cfg["email"]["smtp_port"] = port
                settings.save(self._cfg)
            self._email_state[gstin] = "sent"
            self._log(f"Email sent to {to} for {gstin}")
            return {"ok": True}
        except Exception as e:
            self._log(f"Email failed for {gstin}: {e}")
            return _err(e)

    def skip_email(self, gstin):
        self._email_state[gstin] = "skipped"
        return {"ok": True}

    # ------------------------------------------------------------ settings
    def get_settings(self):
        cfg = self._cfg
        e = cfg["email"]
        return {"ok": True, "firm_name": cfg.get("firm_name", ""), "firm_phone": cfg.get("firm_phone", ""),
                "send_by_day": cfg.get("send_by_day", 18),
                "pwd_warn_days": cfg.get("password_age_warn_days", 60),
                "smtp_server": e.get("smtp_server", ""), "smtp_port": e.get("smtp_port", 587),
                "sender_email": e.get("sender_email", ""), "sender_name": e.get("sender_name", ""),
                "cc": e.get("cc", ""), "has_password": bool(e.get("app_password")),
                "templates": cfg["templates"]}

    def save_settings(self, data):
        try:
            cfg = self._cfg
            cfg["firm_name"] = data.get("firm_name", cfg.get("firm_name", ""))
            cfg["firm_phone"] = data.get("firm_phone", cfg.get("firm_phone", ""))
            cfg["send_by_day"] = max(1, min(28, int(data.get("send_by_day") or 18)))
            cfg["password_age_warn_days"] = max(1, int(data.get("pwd_warn_days") or 60))
            e = cfg["email"]
            for k in ("smtp_server", "sender_email", "sender_name", "cc"):
                if k in data:
                    e[k] = (data.get(k) or "").strip()
            e["smtp_port"] = int(data.get("smtp_port") or 587)
            if data.get("app_password"):
                e["app_password"] = data["app_password"].strip()
            if isinstance(data.get("templates"), dict):
                for k in ("returns", "gstr2b"):
                    t = data["templates"].get(k)
                    if t:
                        cfg["templates"][k] = {"subject": t.get("subject", ""), "body": t.get("body", "")}
            settings.save(cfg)
            return {"ok": True}
        except Exception as e:
            return _err(e)

    def test_email(self):
        try:
            me = self._cfg["email"].get("sender_email")
            if not me:
                return _err("Enter the Gmail address and App Password, click Save settings, then test.")
            port = emailer.send(self._cfg, me, "", "GST Downloader - test email",
                                "This is a test email from GST Downloader. Email is set up correctly.", [])
            if port and port != int(self._cfg["email"].get("smtp_port") or 587):
                self._cfg["email"]["smtp_port"] = port
                settings.save(self._cfg)
            return {"ok": True, "to": me, "port": port}
        except Exception as e:
            self._log("Test email failed:\n" + traceback.format_exc())
            return _err(e)

    # ------------------------------------------------------------ misc
    def open_path(self, path):
        try:
            if not path or not os.path.exists(path):
                return _err("Not found")
            if sys.platform.startswith("win"):
                os.startfile(path)  # noqa
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
            return {"ok": True}
        except Exception as e:
            return _err(e)

    def open_download_folder(self):
        root = settings.resolve(self._cfg.get("download_folder"))
        os.makedirs(root, exist_ok=True)
        return self.open_path(root)

    def form_labels(self):
        return FORM_LABELS
