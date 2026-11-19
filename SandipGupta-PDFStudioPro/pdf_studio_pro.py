#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Studio Pro 1.2.0  -  one-file offline PDF toolkit for Windows offices
=========================================================================
Python 3.9+  |  PyQt5  |  PyMuPDF  |  every tool saves NEW files, originals are never changed.

WHAT IS INSIDE (all nine phases of the build prompt, in this one file)
  1  Merge, Split, Extract pages, Page numbering, Rearrange, PDF <-> Image, Password (open / owner / remove)
  2  Reader, Page Organiser (thumbnails), Compress, Page Tools (rotate/delete/crop/blank/resize/...), Watermark & Stamps,
     Header/Footer, Annotations & Forms, Metadata, Bookmarks, Strip (metadata/hidden data), PDF/A (best effort),
     Repair, Compare
  3  PDF -> Word / Excel / PowerPoint / Text / Markdown / HTML, Extract text-images-tables-links, Bundle Builder
  4  Redaction (draw boxes, auto-detect PAN / Aadhaar / GSTIN / IFSC / phone / e-mail ..., review table, true removal)
  5  OCR (searchable PDF), Image OCR, Scan Clean-up, Indian-languages check, Batch / Hot folder / Pipelines
  6  Image tools: resize/crop/convert, compress to KB, EXIF/GPS strip, blur/mask, watermark, passport photo,
     QR & barcode, collage, bulk rename
  7  Office AI Gateway (stdlib server, queue, per-user keys) + AI client + AI tools (Prime users only)
  8  Settings, administrator override file, update check, Inno Setup / build-script generator, About, shortcuts
  9  Digital Signature (DSC): USB token (PKCS#11) or .pfx, diagnostics, visible box, verify (pyHanko)
  10 Edit PDF (new in 1.1): click-to-edit text, add text / pictures / shapes / links, move & resize pictures, white-out,
     find & replace, undo / redo (Edit > Edit PDF).  Works on a copy; saves a NEW file.
  11 New in 1.2: quality-first Compress (per-picture decisions, lossless line-art, "fit under N MB", before/after quality check),
     PDF -> PowerPoint with real editable text boxes, ready-made AI set-ups in Settings (this PC / office gateway / internet
     service), DSC through the Windows certificate store, automatic choice of the signing certificate, several files per run.
     NOT testable by the author: the Windows-store signing calls (win_store_sign) - they need Windows and a real token.

HOW TO RUN  (normal staff PC)
  * Install Python 3.9 or newer from python.org (tick "Add python.exe to PATH").
  * Open this file in IDLE and press F5   -   or double-click it   -   or:  python pdf_studio_pro.py
  * First run only: missing libraries are installed automatically (internet needed once; a small progress window shows).
    Optional libraries that fail to install only switch off the feature that needs them.
  * A PDF can be passed as the only argument (or "Open with") and opens in the Reader.
  * OCR needs the free Tesseract program (UB-Mannheim Windows installer) with the language packs you need
    (eng, hin, mar, guj, ben, tam, tel, kan, mal, pan, ori, urd ...).  Settings > Tesseract path if not found automatically.
  * Indian-script text drawn BY the program (watermark, header/footer, stamps, bundle labels, Indic OCR text) needs a font file:
    put Noto Sans <Script>-Regular.ttf (SIL OFL licence) in a "fonts" folder next to this file.  Windows' own Nirmala UI is
    used when present.  A single .py file cannot carry the fonts itself.  "Indian Languages Check" shows what is found.

BUILD A DOUBLE-CLICK .EXE (PyInstaller; the first-run installer is skipped in a frozen build)
  python -m pip install pyinstaller
  python -m PyInstaller --noconfirm --windowed --name PDFStudioPro ^
      --collect-all pymupdf --collect-all pyhanko --collect-all pyhanko_certvalidator --collect-all pkcs11 ^
      --collect-all pdf2docx --collect-all docx --collect-all pptx --collect-all openpyxl --collect-all cv2 ^
      --hidden-import PIL --hidden-import pytesseract --hidden-import qrcode --hidden-import barcode ^
      pdf_studio_pro.py
  (Optional) add  --add-data "fonts;fonts"  to ship Indic fonts.   Output: dist\\PDFStudioPro\\PDFStudioPro.exe
  The "Office Deployment Kit" page writes build_windows.bat, an Inno Setup script (with "Open with PDF Studio Pro" for .pdf)
  and an admin_settings.json for you.

OFFICE AI GATEWAY  (one PC runs LM Studio + this gateway; staff PCs only talk to the gateway)
  1. On the server PC: install LM Studio, load a model, start its local server (default http://127.0.0.1:1234/v1).
  2. python pdf_studio_pro.py --gateway-admin     -> menu: create users (Prime / General), limits, reset keys, usage.
     Each key is shown ONCE; only a keyed hash is kept.   (Same functions are in the app: System > AI Gateway.)
  3. python pdf_studio_pro.py --gateway           -> listens on 0.0.0.0:8800 (change in gateway_config.json or the admin page).
     Optional:  --dir D:\\gateway-data   (data folder).   Open the port in Windows Firewall for the office LAN only.
     The gateway needs only the Python standard library (no PyQt5/PyMuPDF), so it also runs on a bare server.
  4. Run it as a Windows service, e.g. with NSSM:   nssm install PDFStudioGateway "C:\\Python\\python.exe" "C:\\psp\\pdf_studio_pro.py --gateway"
  5. Staff PCs: Settings > AI server address  http://<server-ip>:8800/v1 , paste the personal access key, "Test connection".
     Key owners are General (no AI) or Prime (AI pages).  Jobs are queued; one running job per user; limits per day / month.
  6. HTTPS: put a certificate/key (.pem) in the gateway config (tls_cert / tls_key); staff PCs then set "Certificate file".
  Sizing for about 50 users (guidance, not measured by the author): LM Studio handles ONE generation at a time per model, so jobs
  queue. A 7-9B model on a 16-24 GB GPU gives roughly 20-50 tokens/s; a 3-page summary is ~30-90 s; 50 staff using it in the same
  hour is normally fine, 50 pressing the button at the same minute means waiting.  Keep "Jobs at once" at 1 unless the server
  has memory for parallel slots.  Document text goes ONLY to the gateway and LM Studio; the gateway logs numbers (who, when,
  feature, seconds, size) and never document text.

PRIVACY AND SAFETY RULES BUILT IN
  * Strict Offline Mode (default ON): any network connection or DNS look-up to a host that is not the AI server or on the
    allow-list is blocked inside the program.  Switch off only in Settings (or lock it with admin_settings.json).
  * No document contents in logs (%APPDATA%\\PDFStudioPro\\logs).  Private temporary folder per run, removed on exit.
  * Passwords, token PINs and signing passwords are never stored. The AI access key is stored only if "Remember" is ticked.
  * Input files are never modified; outputs get unique names (name_1.pdf ...).
  * Administrator settings:  admin_settings.json in %ProgramData%\\PDFStudioPro\\  (or next to the program, or path in the
    PDFSTUDIO_ADMIN environment variable) overrides and LOCKS the same keys in Settings, and "disabled_tools" hides tools.

LIBRARY VERSIONS  (installed as ranges; the combination below is what the author tested, on Linux / Python 3.13)
  PyQt5 5.15.11 | PyMuPDF 2.1 | Pillow 12.3 | numpy 2.5 | opencv-python-headless 5.0 | pytesseract 0.3.13 | openpyxl 3.1.5
  python-docx 1.2.0 | python-pptx 1.0.2 | pdf2docx 0.5.13 | qrcode 8.2 | python-barcode 0.16.1 | pyHanko 0.38.1 | python-pkcs11 0.10.1
  For a frozen office build, freeze these exact versions:  pip install PyQt5==5.15.11 PyMuPDF==2.1 ...   and keep the build folder.

HONEST STATUS - PLEASE READ
  TESTED by the author (headless, Qt "offscreen", synthetic PDFs/images, Linux): every tool's core function, rotated pages,
  redaction removal, OCR incl. Hindi, bundle builder, batch pipelines, the gateway (queue / limits / cancel / roles) against a FAKE
  OpenAI-style server, the AI client and AI tools against that fake server, PFX signing + verification + tamper detection, window
  construction of all 56 pages.
  NOT TESTED:  (a) on Windows or on a real screen - look and feel, DPI, file dialogs, IDLE F5 behaviour;  (b) USB-token signing
  (PKCS#11) - needs the real token and its vendor driver;  (c) the AI with a real LM Studio model - answer QUALITY is unknown and
  models can misread numbers;  (d) Word/Excel files opened in Microsoft Office (written with python-docx / openpyxl);  (e) very large
  files (hundreds of MB), scanned files in other Indian languages beyond a few test pages;  (f) PDF/A output against veraPDF.
  Do a pilot with copies of real documents before relying on it.

MANUAL TEST CHECKLIST  (about 45 minutes, on a Windows PC, with COPIES of real files)
  General   [ ] starts by F5 in IDLE and by double-click   [ ] resize to 940x640: nothing cut off   [ ] light/dark switch
            [ ] every page shows title, red line, subtitle, "Save output to"; Run without a folder gives a friendly message
            [ ] drag-and-drop a PDF on the window opens the Reader   [ ] Esc / Cancel stops a long job and keeps the originals
  Phase 1   [ ] merge 3 files   [ ] split by range / every N / size   [ ] extract "1-3, 7"   [ ] page numbers (roman, "Page x of y")
            [ ] rearrange   [ ] PDF->JPG/PNG and back   [ ] password add / remove / wrong password message
  Phase 2   [ ] reader zoom, search, contents   [ ] organiser drag & delete   [ ] compress a scan (check size and legibility)
            [ ] rotate a page, then watermark and header/footer on a ROTATED page (must read upright)   [ ] highlight / note / text box
            [ ] fill a form   [ ] metadata, bookmarks   [ ] strip metadata   [ ] repair a damaged copy   [ ] compare two versions
  Phase 3   [ ] PDF->Word (check tables)   [ ] ->Excel   [ ] ->PowerPoint   [ ] ->Markdown/HTML   [ ] extract images/links
            [ ] Bundle: 5 documents, index, per-document numbering, Bates, Roman front matter; open result in Adobe Reader
  Phase 4   [ ] redact a name by drawing, by auto-detect (PAN, Aadhaar, phone, e-mail); then COPY ALL TEXT in the output and
              search for the redacted words - they must be gone.  Also test a scanned page and a rotated page.
  Phase 5   [ ] OCR an English scan and a Hindi/Marathi scan (language packs installed)   [ ] clean-up of a skewed scan
            [ ] batch of 10 files with a 3-step pipeline   [ ] hot folder picks up a dropped file
  Phase 6   [ ] image resize/convert/compress to 200 KB   [ ] EXIF strip (check GPS gone)   [ ] mask area   [ ] passport sheet
            [ ] QR create and read   [ ] collage   [ ] bulk rename (originals untouched)
  Phase 7   [ ] Settings > Test connection (General and Prime keys)   [ ] summarise / key terms / ask / clauses / classify /
              translate / extract on a text PDF - compare each answer with the document   [ ] cancel a queued job
            [ ] two users at once see the queue message   [ ] AI pages say "Prime" for a General key
  Phase 8   [ ] admin_settings.json locks a setting   [ ] update folder with version.json   [ ] deployment kit builds and installs
  Phase 10  [ ] Edit PDF: change a line, a paragraph, a word (find & replace), move text, add text incl. Hindi and the rupee sign,
              add / move / resize / delete a picture, white-out a name (copy text afterwards: it must be gone), draw shapes, add a link,
              undo / redo 5 steps, rotated page, a coloured-background cell, save and open the result in Adobe Reader
  Phase 9   [ ] Token diagnostics shows the token and certificate   [ ] sign with visible box   [ ] verify in Adobe Reader
            [ ] open the signed file here: "Verify Signatures" reports intact   [ ] a wrong PIN stops after one try with a warning

KNOWN LIMITATIONS
  * Scanned pages need OCR before AI, text extraction or auto-redaction can read them.  OCR accuracy depends on scan quality.
  * PDF -> Word is layout-approximate (pdf2docx); PDF -> PowerPoint puts each page in as a picture.  Translation keeps text only.
  * PDF/A is "best effort"; digital-signature "trusted" status needs the issuing authority's root certificate (Adobe does this better).
  * Visible signature boxes on rotated pages are placed by preset or by drawing; check them.  Signing an encrypted PDF is refused
    (remove protection first).  A signed file must not be edited afterwards.
  * Redaction removes text, images under the box and vector graphics inside the box, but cannot know about information that is
    ALSO elsewhere (metadata, bookmarks, a second copy of the same words).  Use "Strip" and always re-open and search the result.
  * AI output can be wrong or incomplete; every AI result carries a notice and is not legal advice.
  * PyMuPDF is AGPL / commercial licensed and PyQt5 is GPL / commercial licensed.  Internal office use is the intended case; get legal
    advice before distributing the program outside your organisation.
"""
# ============================================================================
#  SECTION 0 - standard-library imports and global constants
# ============================================================================
import sys, os, re, io, json, time, math, shutil, atexit, base64, hashlib, hmac
import secrets, socket, ssl, threading, queue, subprocess, tempfile, traceback
import datetime as dt
import importlib.util, logging, ipaddress, itertools, textwrap, difflib, csv
import zipfile, urllib.request, urllib.parse, urllib.error, http.client
import http.server, socketserver, collections, glob, fnmatch, uuid, platform
import multiprocessing, struct
from logging.handlers import RotatingFileHandler

APP_NAME = "PDF Studio Pro"
APP_VERSION = "1.2.0"
IS_FROZEN = bool(getattr(sys, "frozen", False))
IS_WIN = os.name == "nt"


def _config_dir():
    """Per-user folder for settings, logs and gateway data (never document data)."""
    if IS_WIN:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "PDFStudioPro")
    return os.path.join(os.path.expanduser("~"), ".pdfstudiopro")


CONFIG_DIR = _config_dir()
try:
    os.makedirs(CONFIG_DIR, exist_ok=True)
except OSError:
    CONFIG_DIR = tempfile.gettempdir()


def app_dir():
    """Folder that holds this program (script folder or the frozen exe folder)."""
    if IS_FROZEN:
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))
# ============================================================================
#  SECTION A - AI GATEWAY (standard library only; runs without PyQt5)
#  Sits between the desktop apps and LM Studio. Only the gateway talks to
#  LM Studio. Enforcement of roles, limits and queueing happens HERE.
#  Run:   python pdf_studio_pro.py --gateway          (serve)
#         python pdf_studio_pro.py --gateway-admin    (user admin menu)
#  Both accept   --dir <folder>   (default: <config>/gateway)
# ============================================================================
GW_DEFAULT_PORT = 8800
GW_FEATURES = ["summarise", "key_terms", "ask", "flag_clauses", "classify",
               "translate", "extract_data", "title", "redact_suggest",
               "rename", "ocr_fix", "test", "api"]

GW_DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": GW_DEFAULT_PORT,
    "lm_base_url": "http://127.0.0.1:1234/v1",   # LM Studio local server
    "default_model": "",                          # empty = whatever LM Studio has loaded
    "max_concurrent": 1,                          # simultaneous LM jobs
    "queue_timeout": 900,                         # seconds a job may wait in the queue
    "run_timeout": 600,                           # seconds LM Studio may take per job
    "max_chars_default": 400000,                  # max characters of document text per job
    "default_daily_limit": 100,
    "default_monthly_limit": 2000,
    "ip_allow_list": [],                          # e.g. ["192.168.1.0/24"]; empty = all
    "tls_cert": "", "tls_key": "",                # set both to enable HTTPS
    "secret": "",                                 # generated automatically
}


class GwError(Exception):
    def __init__(self, code, msg):
        Exception.__init__(self, msg)
        self.code, self.msg = code, msg


def _now():
    return time.time()


class GatewayStore:
    """Users, config and a metadata-only usage log (JSON files in one folder)."""

    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)
        self.lock = threading.RLock()
        self.cfg_path = os.path.join(folder, "gateway_config.json")
        self.users_path = os.path.join(folder, "gateway_users.json")
        self.usage_path = os.path.join(folder, "gateway_usage.jsonl")
        self.cfg = dict(GW_DEFAULT_CONFIG)
        self.cfg.update(self._load(self.cfg_path, {}))
        if not self.cfg.get("secret"):
            self.cfg["secret"] = secrets.token_hex(32)
        self.save_cfg()
        self.users = self._load(self.users_path, {"users": {}})
        self.users.setdefault("users", {})
        self.counts = collections.Counter()
        self._rebuild_counts()

    # -- files
    @staticmethod
    def _load(path, default):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    @staticmethod
    def _atomic_write(path, data):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)

    def save_cfg(self):
        with self.lock:
            self._atomic_write(self.cfg_path, self.cfg)

    def save_users(self):
        with self.lock:
            self._atomic_write(self.users_path, self.users)

    # -- keys
    def _hash(self, key):
        return hmac.new(self.cfg["secret"].encode(), key.encode("utf-8"),
                        hashlib.sha256).hexdigest()

    def add_user(self, name, role="prime", **kw):
        with self.lock:
            base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "user"
            uid, i = base, 1
            while uid in self.users["users"]:
                i += 1
                uid = "%s-%d" % (base, i)
            key = "psp_" + secrets.token_urlsafe(24)
            u = {"id": uid, "name": name, "key_hash": self._hash(key), "role": role,
                 "enabled": True, "expires": "",
                 "daily_limit": self.cfg["default_daily_limit"],
                 "monthly_limit": self.cfg["default_monthly_limit"],
                 "max_chars": 0, "features": ["*"], "models": ["*"], "priority": 5,
                 "created": dt.date.today().isoformat()}
            u.update(kw)
            self.users["users"][uid] = u
            self.save_users()
            return u, key

    def reset_key(self, uid):
        with self.lock:
            key = "psp_" + secrets.token_urlsafe(24)
            self.users["users"][uid]["key_hash"] = self._hash(key)
            self.save_users()
            return key

    def update_user(self, uid, **kw):
        with self.lock:
            self.users["users"][uid].update(kw)
            self.save_users()

    def remove_user(self, uid):
        with self.lock:
            self.users["users"].pop(uid, None)
            self.save_users()

    def find_by_key(self, key):
        if not key:
            return None
        h = self._hash(key)
        with self.lock:
            for u in self.users["users"].values():
                if hmac.compare_digest(u.get("key_hash", ""), h):
                    return u
        return None

    def check_user(self, u):
        """Raise GwError if the user may not use the service right now."""
        if not u.get("enabled", True):
            raise GwError(403, "This access key is disabled. Contact the administrator.")
        exp = u.get("expires") or ""
        if exp:
            try:
                if dt.date.today() > dt.date.fromisoformat(exp):
                    raise GwError(403, "This access key has expired (%s)." % exp)
            except ValueError:
                pass

    # -- usage (metadata only: user, time, feature, duration, size - never contents)
    def _rebuild_counts(self):
        self.counts.clear()
        try:
            with open(self.usage_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    d = r.get("day", "")
                    self.counts[(r.get("user"), "D" + d)] += 1
                    self.counts[(r.get("user"), "M" + d[:7])] += 1
        except OSError:
            pass

    def log_usage(self, uid, feature, seconds, chars, status):
        day = dt.date.today().isoformat()
        rec = {"ts": int(_now()), "day": day, "user": uid, "feature": feature,
               "seconds": round(seconds, 2), "chars": chars, "status": status}
        with self.lock:
            with open(self.usage_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            self.counts[(uid, "D" + day)] += 1
            self.counts[(uid, "M" + day[:7])] += 1

    def usage_today(self, uid):
        return self.counts[(uid, "D" + dt.date.today().isoformat())]

    def usage_month(self, uid):
        return self.counts[(uid, "M" + dt.date.today().isoformat()[:7])]

    def usage_rows(self, limit=500):
        rows = []
        try:
            with open(self.usage_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
        except OSError:
            pass
        return rows[-limit:]


class GwJob:
    _seq = itertools.count(1)

    def __init__(self, user, feature, request):
        self.id = uuid.uuid4().hex[:16]
        self.user, self.feature, self.request = user, feature, request
        self.priority = int(user.get("priority", 5))
        self.seq = next(GwJob._seq)
        self.created = _now()
        self.started = 0.0
        self.status = "queued"      # queued | running | done | error | cancelled
        self.result = None
        self.error = ""
        self.error_code = 500
        self.conn = None
        self.chars = 0
        self.finished = 0.0


class GatewayEngine:
    """Priority queue + worker threads that forward jobs to LM Studio."""

    def __init__(self, store):
        self.store = store
        self.cv = threading.Condition()
        self.jobs = {}
        self.stop_flag = False
        self.threads = []
        n = max(1, int(store.cfg.get("max_concurrent", 1)))
        for i in range(n):
            t = threading.Thread(target=self._worker, daemon=True, name="gw-worker-%d" % i)
            t.start()
            self.threads.append(t)

    def shutdown(self):
        with self.cv:
            self.stop_flag = True
            self.cv.notify_all()

    # -- submission
    def submit(self, user, feature, request):
        st = self.store
        st.check_user(user)
        feats = user.get("features") or ["*"]
        if "*" not in feats and feature not in feats:
            raise GwError(403, "Your account is not allowed to use '%s'." % feature)
        if not isinstance(request, dict) or "messages" not in request:
            raise GwError(400, "Bad request: 'messages' missing.")
        chars = 0
        for m in request.get("messages", []):
            c = m.get("content", "")
            chars += len(c) if isinstance(c, str) else len(json.dumps(c))
        maxc = int(user.get("max_chars") or st.cfg["max_chars_default"])
        if chars > maxc:
            raise GwError(413, "Document too large for your account (%d > %d characters)." % (chars, maxc))
        dl, ml = int(user.get("daily_limit") or 0), int(user.get("monthly_limit") or 0)
        if dl and st.usage_today(user["id"]) >= dl:
            raise GwError(429, "Daily limit of %d AI jobs reached." % dl)
        if ml and st.usage_month(user["id"]) >= ml:
            raise GwError(429, "Monthly limit of %d AI jobs reached." % ml)
        models = user.get("models") or ["*"]
        req = dict(request)
        req["stream"] = False
        mdl = req.get("model") or st.cfg.get("default_model") or ""
        if "*" not in models and mdl not in models:
            mdl = models[0]
        if mdl:
            req["model"] = mdl
        else:
            req.pop("model", None)
        with self.cv:
            for j in self.jobs.values():
                if j.user["id"] == user["id"] and j.status in ("queued", "running"):
                    raise GwError(429, "You already have an AI job in progress. Wait for it to finish or cancel it.")
            job = GwJob(user, feature, req)
            job.chars = chars
            self.jobs[job.id] = job
            self.cv.notify_all()
        return job

    def position(self, job):
        with self.cv:
            waiting = sorted([j for j in self.jobs.values() if j.status == "queued"],
                             key=lambda j: (-j.priority, j.seq))
            return waiting.index(job) + 1 if job in waiting else 0

    def queued_count(self):
        with self.cv:
            return len([j for j in self.jobs.values() if j.status == "queued"])

    def cancel(self, job):
        with self.cv:
            if job.status in ("queued", "running"):
                job.status = "cancelled"
                job.finished = _now()
                c = job.conn
                self.cv.notify_all()
            else:
                c = None
        if c is not None:
            try:
                c.close()          # closing the socket makes LM Studio stop generating
            except Exception:
                pass

    # -- worker
    def _worker(self):
        while True:
            job = None
            with self.cv:
                while not self.stop_flag:
                    now = _now()
                    qt = float(self.store.cfg.get("queue_timeout", 900))
                    for j in list(self.jobs.values()):
                        if j.status == "queued" and now - j.created > qt:
                            j.status, j.error, j.error_code = "error", "Timed out while waiting in the queue.", 504
                            j.finished = now
                        if j.status in ("done", "error", "cancelled") and j.finished and now - j.finished > 600:
                            self.jobs.pop(j.id, None)
                    waiting = sorted([j for j in self.jobs.values() if j.status == "queued"],
                                     key=lambda j: (-j.priority, j.seq))
                    if waiting:
                        job = waiting[0]
                        job.status, job.started = "running", now
                        break
                    self.cv.wait(1.0)
                if self.stop_flag:
                    return
            self._run(job)

    def _run(self, job):
        cfg = self.store.cfg
        status = "ok"
        try:
            u = urllib.parse.urlparse(cfg["lm_base_url"])
            host, port = u.hostname, u.port or (443 if u.scheme == "https" else 80)
            cls = http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection
            conn = cls(host, port, timeout=float(cfg.get("run_timeout", 600)))
            job.conn = conn
            body = json.dumps(job.request).encode("utf-8")
            path = u.path.rstrip("/") + "/chat/completions"
            conn.request("POST", path, body=body, headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            data = resp.read()
            if job.status == "cancelled":
                return
            if resp.status >= 400:
                raise GwError(502, "The AI engine returned an error (HTTP %d)." % resp.status)
            job.result = json.loads(data.decode("utf-8", "replace"))
            with self.cv:
                job.status = "done"
        except GwError as e:
            status = "error"
            with self.cv:
                if job.status != "cancelled":
                    job.status, job.error, job.error_code = "error", e.msg, e.code
        except Exception as e:
            status = "error"
            with self.cv:
                if job.status != "cancelled":
                    msg = "The AI engine (LM Studio) is not reachable or is busy. Try again later."
                    job.status, job.error, job.error_code = "error", msg, 503
        finally:
            job.finished = _now()
            if job.status == "cancelled":
                status = "cancelled"
            try:
                job.conn.close()
            except Exception:
                pass
            self.store.log_usage(job.user["id"], job.feature, job.finished - job.started,
                                 job.chars, status)


class _GwHandler(http.server.BaseHTTPRequestHandler):
    server_version = "PDFStudioGateway/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):      # silence default console logging (no contents anyway)
        pass

    # helpers
    def _send(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _ip_ok(self):
        allow = self.server.store.cfg.get("ip_allow_list") or []
        if not allow:
            return True
        try:
            ip = ipaddress.ip_address(self.client_address[0])
            for net in allow:
                if ip in ipaddress.ip_network(net, strict=False):
                    return True
        except ValueError:
            return False
        return False

    def _auth(self):
        h = self.headers.get("Authorization", "")
        key = h[7:].strip() if h.lower().startswith("bearer ") else self.headers.get("X-Access-Key", "")
        u = self.server.store.find_by_key(key)
        if not u:
            raise GwError(401, "Invalid or missing access key.")
        self.server.store.check_user(u)
        return u

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 40 * 1024 * 1024:
            raise GwError(413, "Request too large.")
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            raise GwError(400, "Body is not valid JSON.")

    def _guard(self, fn):
        try:
            if not self._ip_ok():
                raise GwError(403, "Your IP address is not allowed.")
            fn()
        except GwError as e:
            self._send(e.code, {"error": {"message": e.msg}})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self._send(500, {"error": {"message": "Gateway internal error."}})

    # routes
    def do_GET(self):
        self._guard(self._get)

    def do_POST(self):
        self._guard(self._post)

    def do_DELETE(self):
        self._guard(self._delete)

    def _get(self):
        eng, st = self.server.engine, self.server.store
        p = self.path.split("?")[0]
        if p == "/health":
            return self._send(200, {"ok": True, "app": "pdfstudio-gateway", "queue": eng.queued_count()})
        u = self._auth()
        if p == "/pdfstudio/whoami":
            return self._send(200, {"user": u["name"], "id": u["id"], "role": u["role"],
                                    "features": u.get("features", ["*"]),
                                    "daily_left": max(0, int(u.get("daily_limit") or 0) - st.usage_today(u["id"])) if u.get("daily_limit") else None,
                                    "max_chars": int(u.get("max_chars") or st.cfg["max_chars_default"])})
        if u["role"] != "prime":
            raise GwError(403, "AI features are available to Prime users only.")
        if p.startswith("/pdfstudio/jobs/"):
            job = eng.jobs.get(p.rsplit("/", 1)[1])
            if not job or job.user["id"] != u["id"]:
                raise GwError(404, "Unknown job.")
            out = {"status": job.status, "position": eng.position(job)}
            if job.status == "done":
                out["result"] = job.result
            if job.status == "error":
                out["error"] = job.error
                out["code"] = job.error_code
            return self._send(200, out)
        if p in ("/v1/models", "/models"):
            lm = urllib.parse.urlparse(st.cfg["lm_base_url"])
            try:
                cls = http.client.HTTPSConnection if lm.scheme == "https" else http.client.HTTPConnection
                c = cls(lm.hostname, lm.port or (443 if lm.scheme == "https" else 80), timeout=10)
                c.request("GET", lm.path.rstrip("/") + "/models")
                r = c.getresponse()
                data = json.loads(r.read().decode("utf-8", "replace"))
                c.close()
                return self._send(200, data)
            except Exception:
                raise GwError(503, "The AI engine (LM Studio) is not reachable.")
        raise GwError(404, "Not found.")

    def _post(self):
        eng = self.server.engine
        p = self.path.split("?")[0]
        u = self._auth()
        if u["role"] != "prime":
            raise GwError(403, "AI features are available to Prime users only.")
        body = self._body()
        if p == "/pdfstudio/jobs":
            job = eng.submit(u, str(body.get("feature", "api")), body.get("request"))
            return self._send(202, {"job_id": job.id, "position": eng.position(job)})
        if p in ("/v1/chat/completions", "/chat/completions"):
            job = eng.submit(u, "api", body)
            while job.status in ("queued", "running"):
                time.sleep(0.3)
            if job.status == "done":
                return self._send(200, job.result)
            raise GwError(job.error_code if job.status == "error" else 499, job.error or "Cancelled.")
        raise GwError(404, "Not found.")

    def _delete(self):
        eng = self.server.engine
        u = self._auth()
        p = self.path.split("?")[0]
        if p.startswith("/pdfstudio/jobs/"):
            job = eng.jobs.get(p.rsplit("/", 1)[1])
            if job and job.user["id"] == u["id"]:
                eng.cancel(job)
            return self._send(200, {"ok": True})
        raise GwError(404, "Not found.")


class _GwHTTPServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class GatewayServer:
    """Start/stop wrapper used by the CLI and by the in-app admin page."""

    def __init__(self, folder):
        self.store = GatewayStore(folder)
        self.engine = None
        self.httpd = None
        self.thread = None

    @property
    def running(self):
        return self.httpd is not None

    def start(self):
        cfg = self.store.cfg
        self.engine = GatewayEngine(self.store)
        self.httpd = _GwHTTPServer((cfg["host"], int(cfg["port"])), _GwHandler)
        self.httpd.store, self.httpd.engine = self.store, self.engine
        if cfg.get("tls_cert") and cfg.get("tls_key"):
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(cfg["tls_cert"], cfg["tls_key"])
            self.httpd.socket = ctx.wrap_socket(self.httpd.socket, server_side=True)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
        if self.engine:
            self.engine.shutdown()


def gateway_admin_menu(store):
    """Plain-text admin menu (CLI)."""
    def show():
        print("\n%-16s %-18s %-7s %-8s %-10s %s" % ("ID", "Name", "Role", "Enabled", "Expires", "Today/Month"))
        for u in store.users["users"].values():
            print("%-16s %-18s %-7s %-8s %-10s %d/%d" % (u["id"], u["name"], u["role"], u["enabled"],
                  u.get("expires") or "-", store.usage_today(u["id"]), store.usage_month(u["id"])))
    while True:
        print("\n=== PDF Studio Pro gateway admin ===")
        print("1 List users   2 Add user   3 Reset key   4 Remove user   5 Promote/Demote")
        print("6 Enable/Disable   7 Set limits/expiry   8 Usage (last 30)   9 Show config   0 Quit")
        c = input("> ").strip()
        try:
            if c == "1":
                show()
            elif c == "2":
                name = input("Name: ").strip()
                role = input("Role [prime/general] (prime): ").strip() or "prime"
                u, key = store.add_user(name, role)
                print("Created '%s'. ACCESS KEY (shown once, give to the user): %s" % (u["id"], key))
            elif c == "3":
                show(); uid = input("User id: ").strip()
                print("New ACCESS KEY (shown once):", store.reset_key(uid))
            elif c == "4":
                show(); store.remove_user(input("User id: ").strip()); print("Removed.")
            elif c == "5":
                show(); uid = input("User id: ").strip()
                cur = store.users["users"][uid]["role"]
                store.update_user(uid, role="general" if cur == "prime" else "prime")
                print("Role is now", store.users["users"][uid]["role"])
            elif c == "6":
                show(); uid = input("User id: ").strip()
                store.update_user(uid, enabled=not store.users["users"][uid]["enabled"])
                print("Enabled =", store.users["users"][uid]["enabled"])
            elif c == "7":
                show(); uid = input("User id: ").strip()
                kw = {}
                for k, lab in (("daily_limit", "Daily limit (0=none)"), ("monthly_limit", "Monthly limit (0=none)"),
                               ("max_chars", "Max characters per job (0=default)"), ("priority", "Priority 0-9"),
                               ("expires", "Expiry date YYYY-MM-DD (blank=never)")):
                    v = input(lab + " [keep]: ").strip()
                    if v != "":
                        kw[k] = v if k == "expires" else int(v)
                if kw:
                    store.update_user(uid, **kw)
            elif c == "8":
                for r in store.usage_rows(30):
                    print(time.strftime("%Y-%m-%d %H:%M", time.localtime(r["ts"])), r["user"], r["feature"],
                          "%.1fs" % r["seconds"], r["chars"], r["status"])
            elif c == "9":
                print(json.dumps({k: v for k, v in store.cfg.items() if k != "secret"}, indent=2))
                print("Edit", store.cfg_path, "to change settings, then restart the gateway.")
            elif c == "0":
                return
        except Exception as e:
            print("Error:", e)


def gateway_cli(argv):
    folder = os.environ.get("PDFSTUDIO_GATEWAY_DIR") or os.path.join(CONFIG_DIR, "gateway")
    if "--dir" in argv:
        folder = argv[argv.index("--dir") + 1]
    if "--gateway-admin" in argv:
        gateway_admin_menu(GatewayStore(folder))
        return
    srv = GatewayServer(folder)
    srv.start()
    cfg = srv.store.cfg
    print("PDF Studio Pro gateway listening on %s://%s:%s  (data folder: %s)" % (
        "https" if cfg.get("tls_cert") else "http", cfg["host"], cfg["port"], folder))
    print("LM Studio target:", cfg["lm_base_url"], " - press Ctrl+C to stop.")
    if not srv.store.users["users"]:
        print("No users yet. Run with --gateway-admin to create the first access key.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        srv.stop()


if __name__ == "__main__" and ("--gateway" in sys.argv or "--gateway-admin" in sys.argv):
    gateway_cli(sys.argv)
    sys.exit(0)
# ============================================================================
#  SECTION B - FIRST-RUN DEPENDENCY INSTALLER (skipped in a frozen build)
#  Runs BEFORE any PyQt5 / PyMuPDF import. Second and later runs install nothing.
# ============================================================================
# (import name, pip name, required?, what it is used for)
DEPENDENCIES = [
    ("PyQt5", "PyQt5>=5.15,<5.16", True, "user interface"),
    ("pymupdf", "PyMuPDF>=1.25,<3", True, "PDF engine"),
    ("PIL", "Pillow>=10,<13", False, "image tools"),
    ("numpy", "numpy>=1.24,<3", False, "image processing"),
    ("cv2", "opencv-python-headless>=4.8,<6", False, "scan clean-up, QR reading"),
    ("pytesseract", "pytesseract>=0.3.10,<0.4", False, "OCR (also needs Tesseract program)"),
    ("openpyxl", "openpyxl>=3.1,<4", False, "Excel export"),
    ("docx", "python-docx>=1.1,<2", False, "Word export"),
    ("pptx", "python-pptx>=1.0,<2", False, "PowerPoint export"),
    ("pdf2docx", "pdf2docx>=0.5.8,<0.6", False, "PDF to Word"),
    ("qrcode", "qrcode>=7.4,<9", False, "QR generation"),
    ("barcode", "python-barcode>=0.15,<0.17", False, "barcode generation"),
    ("pyhanko", "pyhanko>=0.25,<1", False, "digital signatures"),
    ("pkcs11", "python-pkcs11>=0.7,<1", False, "USB token (DSC) support"),
]
_STATE_FILE = os.path.join(CONFIG_DIR, "install_state.json")


def _have(modname):
    try:
        if modname == "pymupdf":
            return bool(importlib.util.find_spec("pymupdf") or importlib.util.find_spec("fitz"))
        return importlib.util.find_spec(modname) is not None
    except (ImportError, ValueError):
        return False


def _pip_install(pkg):
    """Install one package. Returns (ok, output). Hides the console window on Windows."""
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", pkg]
    kw = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "text": True}
    if IS_WIN:
        kw["creationflags"] = 0x08000000        # CREATE_NO_WINDOW
    out = ""
    for extra in ([], ["--user"]):
        try:
            p = subprocess.run(cmd[:5] + extra + cmd[5:], **kw)
            out += p.stdout or ""
            if p.returncode == 0:
                return True, out
        except Exception as e:                  # pip missing, no permission, ...
            out += "\n%s" % e
    return False, out


def ensure_dependencies():
    if IS_FROZEN:
        return                                   # PyInstaller build: everything is bundled
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        state = {}
    tried = set(state.get("tried", []))
    todo = [d for d in DEPENDENCIES if not _have(d[0]) and (d[2] or d[1] not in tried)]
    if not todo:
        return
    win = None
    try:
        import tkinter as tk
        win = tk.Tk()
        win.title(APP_NAME + " - first-time setup")
        win.geometry("520x120")
        lab = tk.Label(win, text="Installing components...", font=("Segoe UI", 11), justify="left")
        lab.pack(padx=14, pady=24, anchor="w")
        win.update()
    except Exception:
        win = None
    failed = []
    for i, (mod, pkg, req, why) in enumerate(todo):
        msg = "Installing %s (%s)  [%d/%d]\nOnly needed once. Please wait..." % (pkg, why, i + 1, len(todo))
        print(msg.replace("\n", " "))
        if win:
            lab.config(text=msg)
            win.update()
        ok, out = _pip_install(pkg)
        tried.add(pkg)
        if not ok:
            failed.append((pkg, req))
            print("FAILED:", pkg, "\n", out[-1500:])
    if win:
        win.destroy()
    try:
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"tried": sorted(tried)}, f)
    except OSError:
        pass
    if failed:
        text = ("Some components could not be installed automatically.\n\n"
                + "\n".join("  pip install \"%s\"%s" % (p, "   (REQUIRED)" if r else "   (optional feature)") for p, r in failed)
                + "\n\nOpen a Command Prompt and run the command(s) above, then start the program again.\n"
                  "Optional components only disable the feature that needs them.")
        print(text)
        try:
            import tkinter as tk
            from tkinter import messagebox
            r = tk.Tk(); r.withdraw()
            messagebox.showwarning(APP_NAME, text)
            r.destroy()
        except Exception:
            pass
        if any(rq for _, rq in failed):
            sys.exit(1)


ensure_dependencies()
# ============================================================================
#  SECTION C - CORE: imports, settings, logging, offline guard, utils, worker
# ============================================================================
try:
    import pymupdf as fitz
except ImportError:                       # very old PyMuPDF
    import fitz

from PyQt5.QtCore import (QT_VERSION_STR, Qt, QThread, pyqtSignal, QTimer, QSize, QRect, QRectF, QPoint, QPointF,
                          QUrl, QMimeData, QEvent, QSettings, QByteArray, QBuffer, QIODevice)
from PyQt5.QtGui import (QPixmap, QImage, QPainter, QColor, QPen, QBrush, QFont, QIcon, QDesktopServices,
                         QPalette, QLinearGradient, QFontDatabase, QFontMetrics, QTransform, QKeySequence,
                         QPolygonF, QPainterPath)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QPushButton, QLineEdit, QFileDialog, QMessageBox, QProgressBar,
                             QTextEdit, QPlainTextEdit, QListWidget, QListWidgetItem, QStackedWidget,
                             QFrame, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QRadioButton,
                             QButtonGroup, QGroupBox, QScrollArea, QSizePolicy, QAbstractItemView,
                             QTableWidget, QTableWidgetItem, QHeaderView, QTreeWidget, QTreeWidgetItem,
                             QTabWidget, QSplitter, QDialog, QDialogButtonBox, QToolButton, QStyleFactory,
                             QSlider, QInputDialog, QShortcut, QMenu, QAction, QProgressDialog,
                             QFormLayout, QColorDialog, QListView, QStatusBar, QTextBrowser)

try:
    from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageFont, ImageEnhance
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False
try:
    import numpy as np
    HAVE_NP = True
except Exception:
    HAVE_NP = False
try:
    import cv2
    HAVE_CV2 = True
except Exception:
    HAVE_CV2 = False
try:
    import pytesseract
    HAVE_PYTESS = True
except Exception:
    HAVE_PYTESS = False
try:
    import openpyxl
    HAVE_XLSX = True
except Exception:
    HAVE_XLSX = False
try:
    import docx as pydocx
    HAVE_DOCX = True
except Exception:
    HAVE_DOCX = False
try:
    import pptx as pypptx
    HAVE_PPTX = True
except Exception:
    HAVE_PPTX = False
try:
    import qrcode as pyqrcode
    HAVE_QR = True
except Exception:
    HAVE_QR = False
try:
    import barcode as pybarcode
    HAVE_BARCODE = True
except Exception:
    HAVE_BARCODE = False

BLUE, BLUE2, DARKBLUE, RED, REDH = "#1F4FBF", "#2D6CDF", "#0F2F73", "#D62839", "#B91C2C"
PDF_EXT = (".pdf",)
IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp")


# ---------------------------------------------------------------- errors / logging
class UserError(Exception):
    """A problem the user can fix; its message is shown in a friendly dialog."""


class Cancelled(Exception):
    pass


class OfflineBlocked(OSError):
    pass


def setup_logging():
    d = os.path.join(CONFIG_DIR, "logs")
    try:
        os.makedirs(d, exist_ok=True)
        h = RotatingFileHandler(os.path.join(d, "pdfstudio.log"), maxBytes=1000000, backupCount=3,
                                encoding="utf-8")
    except OSError:
        h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    lg = logging.getLogger("psp")
    lg.setLevel(logging.INFO)
    if not lg.handlers:
        lg.addHandler(h)
    return lg


LOG = setup_logging()
LOG_DIR = os.path.join(CONFIG_DIR, "logs")


def log_exc(where):
    """Log an exception WITHOUT any document contents (only type, message, stack)."""
    LOG.error("%s\n%s", where, traceback.format_exc())


# ---------------------------------------------------------------- settings
DEFAULT_SETTINGS = {
    "offline_mode": True,            # Strict Offline Mode
    "allowed_hosts": [],             # extra allow-listed LAN hosts (e.g. time server)
    "ai_base_url": "http://localhost:1234/v1",   # LM Studio default; or the gateway URL
    "ai_model": "", "ai_timeout": 300, "ai_max_context": 8192,
    "direct_mode": False, "ai_ca_file": "", "cloud_ai_ok": "",   # talk to a plain OpenAI-compatible server (no gateway)
    "remember_key": False, "access_key": "",
    "theme": "light", "recent_enabled": True, "recent": [], "last_dirs": {},
    "tesseract_path": "", "update_path": "", "disabled_tools": [],
    "pkcs11_path": "", "gateway_dir": "",
}


def _admin_settings_paths():
    p = [os.environ.get("PDFSTUDIO_ADMIN", "")]
    if IS_WIN:
        p.append(os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "PDFStudioPro", "admin_settings.json"))
    p.append(os.path.join(app_dir(), "admin_settings.json"))
    return [x for x in p if x]


class Settings:
    def __init__(self):
        self.path = os.path.join(CONFIG_DIR, "settings.json")
        self.user = dict(DEFAULT_SETTINGS)
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.user.update(json.load(f))
        except Exception:
            pass
        self.admin, self.admin_path = {}, ""
        for p in _admin_settings_paths():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    self.admin = json.load(f)
                self.admin_path = p
                break
            except Exception:
                continue

    def get(self, key, default=None):
        if key in self.admin:
            return self.admin[key]
        return self.user.get(key, DEFAULT_SETTINGS.get(key, default))

    def locked(self, key):
        return key in self.admin

    def set(self, key, value, save=True):
        if key in self.admin:
            return
        self.user[key] = value
        if save:
            self.save()

    def save(self):
        d = dict(self.user)
        if not d.get("remember_key"):
            d["access_key"] = ""         # passwords / PINs / keys are never stored unless asked
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            log_exc("settings save")

    # last-used folders per dialog context
    def last_dir(self, ctx):
        d = self.get("last_dirs", {}).get(ctx) or self.get("last_dirs", {}).get("_any") or ""
        return d if d and os.path.isdir(d) else os.path.expanduser("~")

    def remember_dir(self, ctx, path):
        d = path if os.path.isdir(path) else os.path.dirname(path)
        if d and os.path.isdir(d):
            ld = dict(self.user.get("last_dirs", {}))
            ld[ctx] = d
            ld["_any"] = d
            self.set("last_dirs", ld)

    def add_recent(self, path):
        if not self.get("recent_enabled"):
            return
        r = [p for p in self.user.get("recent", []) if p != path][:14]
        self.set("recent", [path] + r)


SET = Settings()


# ---------------------------------------------------------------- Strict Offline Mode
_ORIG_CONNECT = socket.socket.connect
_ORIG_CONNECT_EX = socket.socket.connect_ex
_ALLOW_EXTRA = set()                      # hosts added at run time (e.g. gateway's LM Studio)
_RESOLVED = {}


def _host_of(url):
    try:
        return urllib.parse.urlparse(url if "//" in url else "//" + url).hostname or ""
    except ValueError:
        return ""


def is_local_host(host):
    """True for this PC, a private (office LAN) address or a plain machine name - i.e. NOT an internet service."""
    h = (host or "").strip().lower()
    if not h or h == "localhost" or "." not in h or h.endswith((".local", ".lan", ".internal")):
        return True
    try:
        ip = ipaddress.ip_address(h)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


AI_SETUPS = [
    ("Choose a ready-made AI set-up ...", None, None, ""),
    ("AI on THIS computer with LM Studio  (free, private, no key)", "http://localhost:1234/v1", True,
     "1. Install the free LM Studio program on this PC and download a model in it.\n"
     "2. In LM Studio open 'Developer' / 'Local Server' and press Start.\n"
     "3. Here: leave the access key empty, press 'Test connection', then 'Save settings'.\n"
     "You are now a PRIME user on this PC - the AI tools in the left list are no longer dimmed. Nothing leaves this computer."),
    ("AI on THIS computer with Ollama  (free, private, no key)", "http://localhost:11434/v1", True,
     "1. Install the free Ollama program on this PC and pull a model (for example: ollama pull llama3.1).\n"
     "2. Type that model name in the 'Model' box below.\n"
     "3. Leave the access key empty, press 'Test connection', then 'Save settings'. Nothing leaves this computer."),
    ("Office AI server (gateway) - I have a personal access key", "", False,
     "1. Ask your administrator for the server address and YOUR access key.\n"
     "   (Administrator: on the server PC open 'AI Gateway (Administrator)' in this program, press 'Start gateway',\n"
     "    then 'Add user' with role Prime. The key is shown once.)\n"
     "2. Type the address below, for example  http://192.168.1.10:8800/v1\n"
     "3. Paste the key in 'Access key', press 'Test connection' - it must say role: PRIME - then 'Save settings'."),
    ("Internet AI service - OpenAI  (needs your own API key; text leaves the office)", "https://api.openai.com/v1", True,
     "1. Create an API key in your OpenAI account and paste it in 'Access key'.\n"
     "2. Type a model name in the 'Model' box (the name exactly as your provider lists it).\n"
     "3. Press 'Test connection', then 'Save settings'.\n"
     "WARNING: the text of the pages you select is sent over the internet to that company. Use it only if your firm's "
     "confidentiality rules and your client engagement terms allow it."),
    ("Internet AI service - Google Gemini  (needs your own API key; text leaves the office)", "https://generativelanguage.googleapis.com/v1beta/openai", True,
     "1. Create an API key in Google AI Studio and paste it in 'Access key'.\n"
     "2. Type a model name in the 'Model' box (the name exactly as Google lists it).\n"
     "3. Press 'Test connection', then 'Save settings'.\n"
     "WARNING: the text of the pages you select is sent over the internet to that company. Use it only if your firm's "
     "confidentiality rules and your client engagement terms allow it."),
    ("Internet AI service - other OpenAI-compatible provider", "https://", True,
     "1. Type the provider's OpenAI-compatible address below (it normally ends in /v1).\n"
     "2. Paste your API key in 'Access key' and type the model name in the 'Model' box.\n"
     "3. Press 'Test connection', then 'Save settings'.\n"
     "WARNING: the text of the pages you select is sent over the internet to that company."),
]


def allowed_hosts():
    hosts = set(h.strip().lower() for h in (SET.get("allowed_hosts") or []) if h.strip())
    for k in ("ai_base_url",):
        h = _host_of(SET.get(k) or "")
        if h:
            hosts.add(h.lower())
    return hosts | _ALLOW_EXTRA


def host_allowed(host):
    host = (host or "").lower()
    if not SET.get("offline_mode"):
        return True
    allowed = allowed_hosts()
    if host in allowed:
        return True
    for a in allowed:
        if a not in _RESOLVED:
            try:
                _RESOLVED[a] = {x[4][0] for x in _ORIG_GAI(a, None)}
            except OSError:
                _RESOLVED[a] = set()
        if host in _RESOLVED[a]:
            return True
    return False


def _guard(sock, addr):
    if SET.get("offline_mode") and sock.family in (socket.AF_INET, socket.AF_INET6):
        host = addr[0] if isinstance(addr, tuple) else str(addr)
        if not host_allowed(host):
            raise OfflineBlocked("Strict Offline Mode blocked a connection to %s. Only the allow-listed "
                                 "server(s) may be contacted." % host)


def _g_connect(self, addr):
    _guard(self, addr)
    return _ORIG_CONNECT(self, addr)


def _g_connect_ex(self, addr):
    _guard(self, addr)
    return _ORIG_CONNECT_EX(self, addr)


_ORIG_GAI = socket.getaddrinfo


def _g_getaddrinfo(host, *a, **k):
    """Block even the DNS look-up of names that are not allow-listed (no name leaks out)."""
    if SET.get("offline_mode") and isinstance(host, str) and host and host.lower() not in ("localhost",):
        try:
            socket.inet_pton(socket.AF_INET, host)
            lit = True
        except (OSError, ValueError):
            try:
                socket.inet_pton(socket.AF_INET6, host)
                lit = True
            except (OSError, ValueError):
                lit = False
        if not lit and host.lower() not in allowed_hosts():
            raise OfflineBlocked("Strict Offline Mode blocked a look-up of %s." % host)
    return _ORIG_GAI(host, *a, **k)


def install_offline_guard():
    socket.socket.connect = _g_connect
    socket.socket.connect_ex = _g_connect_ex
    socket.getaddrinfo = _g_getaddrinfo


# ---------------------------------------------------------------- utils
def human_size(n):
    n = float(n)
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return ("%d %s" % (n, u)) if u == "B" else ("%.1f %s" % (n, u))
        n /= 1024.0


def safe_name(s, default="file"):
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", str(s)).strip(" ._")
    return s[:120] or default


def unique_path(folder, base, ext):
    """Return folder/base+ext, or base_1+ext, base_2+ext ... never an existing path."""
    base = safe_name(base)
    p = os.path.join(folder, base + ext)
    i = 1
    while os.path.exists(p):
        p = os.path.join(folder, "%s_%d%s" % (base, i, ext))
        i += 1
    return p


def unique_dir(folder, base):
    base = safe_name(base)
    p = os.path.join(folder, base)
    i = 1
    while os.path.exists(p):
        p = os.path.join(folder, "%s_%d" % (base, i))
        i += 1
    os.makedirs(p)
    return p


def ensure_out_dir(out_dir):
    if not out_dir:
        raise UserError("Please choose the 'Save output to' folder first.")
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError:
        raise UserError("The output folder cannot be created:\n%s" % out_dir)
    if not os.access(out_dir, os.W_OK):
        raise UserError("You do not have permission to write to:\n%s" % out_dir)
    return out_dir


def _norm_ranges(text):
    t = re.sub(r"[\u2012\u2013\u2014\u2212]", "-", text or "")
    t = re.sub(r"\s*-\s*", "-", t)
    return [x for x in re.split(r"[,;\s]+", t.strip()) if x]


def parse_page_spec(text, n, allow_reverse=False):
    """'1, 3-5, 8-10' -> list of (a, b) 1-based tokens, validated against page count n."""
    toks = _norm_ranges(text)
    if not toks:
        raise UserError("Please enter the pages, for example:  1, 3-5, 8-10")
    out = []
    for t in toks:
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", t)
        if not m:
            raise UserError("'%s' is not a valid page number or range. Use numbers like 3 or 3-5." % t)
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        for v in (a, b):
            if v < 1 or v > n:
                raise UserError("Page %d is outside the document (it has %d page%s)." % (v, n, "" if n == 1 else "s"))
        if b < a and not allow_reverse:
            raise UserError("Range '%d-%d' goes backwards. Write it as %d-%d." % (a, b, b, a))
        out.append((a, b))
    return out


def expand_pages(spec_tokens):
    """[(a,b),...] -> flat 0-based page list in entered order (reverse ranges allowed)."""
    pages = []
    for a, b in spec_tokens:
        step = 1 if b >= a else -1
        pages.extend(range(a - 1, b - 1 + step, step))
    return pages


def pages_from_text(text, n, allow_reverse=False, blank_means_all=True):
    if blank_means_all and not (text or "").strip():
        return list(range(n))
    return expand_pages(parse_page_spec(text, n, allow_reverse))


def to_roman(n):
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"),
            (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


class TempDir:
    _all = []

    def __enter__(self):
        self.path = tempfile.mkdtemp(prefix="psp_")
        TempDir._all.append(self.path)
        return self.path

    def __exit__(self, *a):
        shutil.rmtree(self.path, ignore_errors=True)

    @staticmethod
    def cleanup_all():
        for p in TempDir._all:
            shutil.rmtree(p, ignore_errors=True)


atexit.register(TempDir.cleanup_all)


# ---------------------------------------------------------------- PDF helpers
def open_pdf(path, password=None, allow_empty=False):
    """Open a PDF safely. Never modifies the file. Raises UserError with friendly text."""
    name = os.path.basename(path)
    if not path or not os.path.isfile(path):
        raise UserError("File not found:\n%s" % path)
    try:
        doc = fitz.open(path)
    except Exception:
        raise UserError("'%s' could not be opened. It may be damaged or is not a real PDF.\n"
                        "Try the Repair PDF tool first." % name)
    if doc.needs_pass:
        if password:
            if not doc.authenticate(password):
                doc.close()
                raise UserError("The password for '%s' is wrong." % name)
        else:
            doc.close()
            raise UserError("'%s' is password-protected.\nRemove the password first "
                            "(Security > Password protect / remove)." % name)
    if doc.page_count == 0 and not allow_empty:
        doc.close()
        raise UserError("'%s' has no pages." % name)
    return doc


def save_pdf(doc, path, **kw):
    opts = {"garbage": 3, "deflate": True}
    opts.update(kw)
    doc.save(path, **opts)
    return path


def build_from_pages(src, pages, report=None, lo=0, hi=100):
    """New PDF made of src pages in the given order (duplicates become independent copies)."""
    new = fitz.open()
    runs, cur = [], None
    for p in pages:                       # group ascending consecutive runs for speed
        if cur and p == cur[1] + 1:
            cur[1] = p
        else:
            cur = [p, p]
            runs.append(cur)
    for i, (a, b) in enumerate(runs):
        new.insert_pdf(src, from_page=a, to_page=b)
        if report and (i % 10 == 0):
            report(lo + (hi - lo) * i / max(1, len(runs)), "Building pages...")
    return new


def page_has_text(page):
    return bool(page.get_text("text").strip())


COLORS = {"Blue": (0.12, 0.31, 0.75), "Red": (0.84, 0.16, 0.22), "Black": (0, 0, 0),
          "Gray": (0.4, 0.4, 0.4), "White": (1, 1, 1), "Green": (0.1, 0.5, 0.2),
          "Yellow": (1, 0.9, 0.2), "Orange": (1, 0.55, 0.1)}


def qcolor(rgb):
    return QColor(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))


# ---------------------------------------------------------------- Indian-language fonts
INDIC_BLOCKS = [("devanagari", 0x0900, 0x097F), ("bengali", 0x0980, 0x09FF), ("gurmukhi", 0x0A00, 0x0A7F),
                ("gujarati", 0x0A80, 0x0AFF), ("oriya", 0x0B00, 0x0B7F), ("tamil", 0x0B80, 0x0BFF),
                ("telugu", 0x0C00, 0x0C7F), ("kannada", 0x0C80, 0x0CFF), ("malayalam", 0x0D00, 0x0D7F),
                ("arabic", 0x0600, 0x06FF)]


def script_of(text):
    for ch in text:
        o = ord(ch)
        for name, a, b in INDIC_BLOCKS:
            if a <= o <= b:
                return name
    return None


def _font_dirs():
    ds = [os.path.join(app_dir(), "fonts"), os.path.join(CONFIG_DIR, "fonts")]
    if IS_WIN:
        ds.append(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
    else:
        ds += ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
               "/Library/Fonts", "/System/Library/Fonts"]
    return ds


_FONT_CACHE = {}


def find_font(script=None):
    """Find a TTF/OTF that can draw the given script (None = any Unicode text like the rupee sign)."""
    key = script or "_unicode"
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    names = []
    if script:
        cap = script.capitalize()
        names += ["NotoSans%s-Regular.ttf" % cap, "NotoSans%s-Regular.otf" % cap, "NotoSans%s[wdth,wght].ttf" % cap,
                  "NotoSerif%s-Regular.ttf" % cap]
        if script == "arabic":
            names += ["NotoNaskhArabic-Regular.ttf", "arial.ttf"]
        else:
            names += ["Nirmala.ttf", "NirmalaUI.ttf", "mangal.ttf", "FreeSerif.ttf", "Lohit-%s.ttf" % cap]
    else:
        names += ["NotoSans-Regular.ttf", "arial.ttf", "Nirmala.ttf", "DejaVuSans.ttf", "FreeSans.ttf"]
    found = None
    for d in _font_dirs():
        if not os.path.isdir(d):
            continue
        for want in names:
            for root, _dirs, files in os.walk(d):
                for f in files:
                    if f.lower() == want.lower():
                        found = os.path.join(root, f)
                        break
                if found:
                    break
            if found:
                break
        if found:
            break
    _FONT_CACHE[key] = found
    return found


def is_latin1(text):
    return all(ord(c) < 256 for c in text)


def _vis_to_page(page, pt):
    return fitz.Point(pt) * page.derotation_matrix


def draw_label(page, text, where, fontsize=10, margin=24, color=(0, 0, 0), bold=False):
    """Draw a one-line label at a named visible position (works on rotated pages and Indian scripts).
    where: 'top-left'|'top-center'|'top-right'|'bottom-left'|'bottom-center'|'bottom-right'."""
    vr = page.rect                                      # visible (rotated) rectangle
    vert, horiz = where.split("-")
    script = script_of(text)
    if is_latin1(text) and not script:
        fname = "hebo" if bold else "helv"
        w = fitz.get_text_length(text, fname, fontsize)
        x = {"left": margin, "center": (vr.width - w) / 2, "right": vr.width - margin - w}[horiz]
        y = margin + fontsize * 0.8 if vert == "top" else vr.height - margin
        page.insert_text(_vis_to_page(page, (x, y)), text, fontsize=fontsize, fontname=fname,
                         color=color, rotate=page.rotation)
        return
    font = find_font(script)
    if script:                                          # shaped text through the HTML engine
        h = fontsize * 2.0
        y0 = margin if vert == "top" else vr.height - margin - h + fontsize * 0.3
        rect = fitz.Rect(margin, y0, vr.width - margin, y0 + h)
        r2 = rect * page.derotation_matrix
        r2.normalize()
        fam = "indic"
        css = "body{font-family:%s;font-size:%spt;color:rgb(%d,%d,%d);text-align:%s;margin:0;}" % (
            fam, fontsize, color[0] * 255, color[1] * 255, color[2] * 255, horiz)
        if font:
            css = "@font-face{font-family:indic;src:url(%s);}" % os.path.basename(font) + css
            arch = fitz.Archive(os.path.dirname(font))
        else:
            arch = None
            css = css.replace("font-family:indic;", "")
        html = "<body>%s</body>" % (text.replace("&", "&amp;").replace("<", "&lt;"))
        page.insert_htmlbox(r2, html, css=css, archive=arch, rotate=(page.rotation) % 360)
        return
    # non-Latin-1 symbols such as the rupee sign: use a real Unicode font file
    if font:
        fo = fitz.Font(fontfile=font)
        w = fo.text_length(text, fontsize)
        x = {"left": margin, "center": (vr.width - w) / 2, "right": vr.width - margin - w}[horiz]
        y = margin + fontsize * 0.8 if vert == "top" else vr.height - margin
        page.insert_text(_vis_to_page(page, (x, y)), text, fontsize=fontsize, fontfile=font,
                         fontname="uni_" + str(abs(hash(font)) % 9999), color=color, rotate=page.rotation)
    else:
        draw_label(page, text.encode("latin-1", "replace").decode("latin-1"), where, fontsize, margin, color, bold)


# ---------------------------------------------------------------- Qt-rendered text (watermarks etc.)
_QT_LOCK = threading.RLock()
_REGISTERED_FONTS = {}


def qt_font_family(script=None):
    f = find_font(script)
    if not f:
        return "Arial"
    with _QT_LOCK:
        if f not in _REGISTERED_FONTS:
            fid = QFontDatabase.addApplicationFont(f)
            fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
            _REGISTERED_FONTS[f] = fams[0] if fams else "Arial"
        return _REGISTERED_FONTS[f]


def render_text_image(text, px, rgb=(0, 0, 0), opacity=1.0, angle=0.0, box=False, bold=True, pad=None):
    """Render text (any script, correctly shaped by Qt) to a transparent QImage."""
    with _QT_LOCK:
        script = script_of(text)
        font = QFont(qt_font_family(script) if (script or not is_latin1(text)) else "Arial")
        font.setPixelSize(max(8, int(px)))
        font.setBold(bold)
        fm = QFontMetrics(font)
        lines = text.split("\n")
        tw = max(fm.horizontalAdvance(l) for l in lines)
        th = fm.height() * len(lines)
        pad = int(px * 0.35) if pad is None else pad
        w, h = tw + pad * 2, th + pad * 2
        img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        col = qcolor(rgb)
        col.setAlphaF(opacity)
        p.setPen(QPen(col, max(2, px / 12.0)))
        if box:
            p.drawRoundedRect(QRectF(px / 24.0, px / 24.0, w - px / 12.0, h - px / 12.0), px / 6.0, px / 6.0)
        p.setFont(font)
        p.drawText(QRect(0, 0, w, h), Qt.AlignCenter, text)
        p.end()
        if angle:
            tr = QTransform().rotate(-angle)
            img = img.transformed(tr, Qt.SmoothTransformation)
        return img


def qimage_to_png(img):
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(ba)


# ---------------------------------------------------------------- Worker thread
class Worker(QThread):
    progress = pyqtSignal(int, str)
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str, bool)
    cancelled = pyqtSignal()

    def __init__(self, task, parent=None):
        QThread.__init__(self, parent)
        self.task = task
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def run(self):
        def report(pct, msg=""):
            if self._cancel.is_set():
                raise Cancelled()
            self.progress.emit(max(0, min(100, int(pct))), msg)

        try:
            res = self.task(report, self._cancel.is_set)
        except Cancelled:
            self.cancelled.emit()
        except UserError as e:
            self.failed.emit(str(e), True)
        except MemoryError:
            log_exc("worker")
            self.failed.emit("Not enough memory for this job. Try a lower DPI or fewer pages at a time.", False)
        except PermissionError:
            log_exc("worker")
            self.failed.emit("Windows refused access to a file or folder. Close the file in other programs "
                             "or choose another output folder.", False)
        except OfflineBlocked as e:
            self.failed.emit(str(e), True)
        except Exception as e:
            log_exc("worker")
            self.failed.emit("Something unexpected went wrong: %s: %s\n\nThe details were saved to the log "
                             "file (Help > Open log folder)." % (type(e).__name__, str(e)[:300]), False)
        else:
            self.succeeded.emit(res)


def open_folder(path):
    if os.path.isfile(path):
        path = os.path.dirname(path)
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))


DISCLAIMER = "AI-generated, may contain errors, not legal advice - verify against the source."
# ============================================================================
#  SECTION D - SHARED WIDGETS: pickers, file list, output picker, viewer, organiser, ToolPage
# ============================================================================
def hint_label(text):
    l = QLabel(text)
    l.setObjectName("hint")
    l.setWordWrap(True)
    return l


def hbox(*widgets, stretch_last=False, spacing=8):
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(spacing)
    for x in widgets:
        if isinstance(x, int):
            h.addSpacing(x)
        elif x is None:
            h.addStretch(1)
        else:
            h.addWidget(x)
    return w


class DropLineEdit(QLineEdit):
    filesDropped = pyqtSignal(list)

    def __init__(self, *a):
        QLineEdit.__init__(self, *a)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            QLineEdit.dragEnterEvent(self, e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            self.filesDropped.emit([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])
            e.acceptProposedAction()
        else:
            QLineEdit.dropEvent(self, e)


class PasswordField(QWidget):
    """Password entry with a 'Show' toggle. Never stored anywhere."""

    def __init__(self, placeholder=""):
        QWidget.__init__(self)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.Password)
        self.edit.setPlaceholderText(placeholder)
        self.btn = QToolButton()
        self.btn.setText("Show")
        self.btn.setCheckable(True)
        self.btn.toggled.connect(lambda on: self.edit.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
        h.addWidget(self.edit, 1)
        h.addWidget(self.btn)

    def text(self):
        return self.edit.text()

    def setText(self, t):
        self.edit.setText(t)

    def set_visible_text(self, on):
        self.btn.setChecked(on)


class FilePicker(QWidget):
    changed = pyqtSignal(str)

    def __init__(self, ctx_key, exts=PDF_EXT, title="Select file", filt="PDF files (*.pdf)", placeholder=None):
        QWidget.__init__(self)
        self.ctx_key, self.exts, self.title_, self.filt = ctx_key, tuple(exts), title, filt
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.edit = DropLineEdit()
        self.edit.setPlaceholderText(placeholder or "Choose a file or drag it here...")
        self.edit.filesDropped.connect(self._dropped)
        self.edit.editingFinished.connect(lambda: self.changed.emit(self.edit.text().strip()))
        self.btn = QPushButton("Browse...")
        self.btn.clicked.connect(self.browse)
        h.addWidget(self.edit, 1)
        h.addWidget(self.btn)

    def path(self):
        return self.edit.text().strip().strip('"')

    def set_path(self, p):
        self.edit.setText(p)
        self.changed.emit(p)

    def _dropped(self, files):
        files = [f for f in files if f.lower().endswith(self.exts)]
        if files:
            self.set_path(files[0])

    def browse(self):
        p, _ = QFileDialog.getOpenFileName(self, self.title_, SET.last_dir(self.ctx_key), self.filt)
        if p:
            SET.remember_dir(self.ctx_key, p)
            self.set_path(p)


class PdfPicker(FilePicker):
    """PDF chooser that shows page count / protection status."""

    def __init__(self, ctx_key, allow_password=False):
        FilePicker.__init__(self, ctx_key, PDF_EXT, "Select a PDF", "PDF files (*.pdf)")
        lay = QVBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        self.info = QLabel("")
        self.info.setObjectName("hint")
        self.page_count = 0
        self.encrypted = False
        self.allow_password = allow_password
        self.changed.connect(self.refresh_info)

    def refresh_info(self, p=None):
        p = self.path()
        self.page_count, self.encrypted = 0, False
        if not p:
            self.info.setText("")
            return
        if not os.path.isfile(p):
            self.info.setText("File not found.")
            return
        try:
            d = fitz.open(p)
            if d.needs_pass:
                self.encrypted = True
                self.info.setText("Password-protected PDF (%s)" % human_size(os.path.getsize(p)))
            else:
                self.page_count = d.page_count
                self.info.setText("%d page%s  |  %s%s" % (d.page_count, "" if d.page_count == 1 else "s",
                                  human_size(os.path.getsize(p)), "  |  restricted/encrypted" if d.is_encrypted else ""))
            d.close()
        except Exception:
            self.info.setText("This file cannot be read as a PDF (damaged?).")

    def open(self, password=None):
        return open_pdf(self.path(), password)

    def require(self):
        if not self.path():
            raise UserError("Please choose a PDF file first.")
        if not os.path.isfile(self.path()):
            raise UserError("The file was not found:\n%s" % self.path())
        return self.path()


class _DropList(QListWidget):
    filesDropped = pyqtSignal(list)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            QListWidget.dragEnterEvent(self, e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            QListWidget.dragMoveEvent(self, e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            self.filesDropped.emit([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])
            e.acceptProposedAction()
        else:
            QListWidget.dropEvent(self, e)


class FileListWidget(QWidget):
    """Ordered multi-file list: add, drag-reorder, move up/down, remove, clear, drop from desktop."""
    changed = pyqtSignal()

    def __init__(self, ctx_key, exts=PDF_EXT, filt="PDF files (*.pdf)", title="Select files"):
        QWidget.__init__(self)
        self.ctx_key, self.exts, self.filt, self.title_ = ctx_key, tuple(exts), filt, title
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.list = _DropList()
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.setAcceptDrops(True)
        self.list.setMinimumHeight(150)
        self.list.filesDropped.connect(self.add_paths)
        self.list.model().rowsMoved.connect(lambda *a: self.changed.emit())
        v.addWidget(self.list)
        row = QHBoxLayout()
        for text, fn in (("Add files...", self.browse), ("Move up", lambda: self.move(-1)),
                         ("Move down", lambda: self.move(1)), ("Remove", self.remove), ("Clear", self.clear)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        self.count_label = QLabel("")
        self.count_label.setObjectName("hint")
        row.addWidget(self.count_label)
        v.addLayout(row)

    def browse(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.title_, SET.last_dir(self.ctx_key), self.filt)
        if files:
            SET.remember_dir(self.ctx_key, files[0])
            self.add_paths(files)

    def add_paths(self, files):
        have = set(self.paths())
        skipped = 0
        for f in files:
            if f.lower().endswith(self.exts) and os.path.isfile(f):
                if f not in have:
                    it = QListWidgetItem(os.path.basename(f))
                    it.setData(Qt.UserRole, f)
                    it.setToolTip(f)
                    self.list.addItem(it)
            else:
                skipped += 1
        if skipped:
            QMessageBox.information(self, APP_NAME, "%d item(s) were skipped (not a supported file type)." % skipped)
        self._upd()

    def paths(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]

    def move(self, d):
        rows = sorted([self.list.row(i) for i in self.list.selectedItems()], reverse=(d > 0))
        for r in rows:
            nr = r + d
            if 0 <= nr < self.list.count():
                it = self.list.takeItem(r)
                self.list.insertItem(nr, it)
                it.setSelected(True)
        self._upd()

    def remove(self):
        for it in self.list.selectedItems():
            self.list.takeItem(self.list.row(it))
        self._upd()

    def clear(self):
        self.list.clear()
        self._upd()

    def _upd(self):
        self.count_label.setText("%d file(s)" % self.list.count())
        self.changed.emit()


class OutputPicker(QWidget):
    def __init__(self, ctx_key="output"):
        QWidget.__init__(self)
        self.ctx_key = ctx_key
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.edit = DropLineEdit()
        self.edit.setPlaceholderText("Choose the folder where results will be saved (required)")
        self.edit.filesDropped.connect(lambda f: self.edit.setText(f[0] if os.path.isdir(f[0]) else os.path.dirname(f[0])))
        self.edit.setText(SET.get("last_dirs", {}).get("_out", ""))
        b = QPushButton("Browse...")
        b.clicked.connect(self.browse)
        o = QPushButton("Open")
        o.setObjectName("flat")
        o.clicked.connect(lambda: self.path() and os.path.isdir(self.path()) and open_folder(self.path()))
        h.addWidget(self.edit, 1)
        h.addWidget(b)
        h.addWidget(o)

    def path(self):
        return self.edit.text().strip().strip('"')

    def browse(self):
        d = QFileDialog.getExistingDirectory(self, "Save output to", self.path() or SET.last_dir("_out"))
        if d:
            self.edit.setText(d)
            ld = dict(SET.get("last_dirs", {}))
            ld["_out"] = d
            SET.set("last_dirs", ld)


# ---------------------------------------------------------------- PDF viewer
class ViewCanvas(QWidget):
    def __init__(self, viewer):
        QWidget.__init__(self)
        self.v = viewer
        self.setMouseTracking(True)
        self.drag_start = None
        self.drag_now = None
        self.drag_page = -1

    def paintEvent(self, ev):
        v = self.v
        p = QPainter(self)
        p.fillRect(ev.rect(), QColor("#8C98AD"))
        if not v.doc:
            p.setPen(QColor("white"))
            p.drawText(self.rect(), Qt.AlignCenter, "No PDF open")
            return
        top, bot = ev.rect().top(), ev.rect().bottom()
        first = v.page_at(top)
        for i in range(first, v.doc.page_count):
            y = v.offsets[i]
            if y > bot:
                break
            pm = v.get_pixmap(i)
            x = v.page_x(i)
            p.fillRect(QRect(x, y, pm.width(), pm.height()), Qt.white)
            p.drawPixmap(x, y, pm)
            page = v.doc[i]
            z = v.zoom
            # search highlights
            for rr, cur in v.highlights.get(i, []):
                vr = fitz.Rect(rr) * page.rotation_matrix
                col = QColor(255, 140, 0, 120) if cur else QColor(255, 235, 0, 110)
                p.fillRect(QRectF(x + vr.x0 * z, y + vr.y0 * z, vr.width * z, vr.height * z), col)
            if v.extra_rot == 0:
                for rr, style in v.overlays.get(i, []):
                    vr = fitz.Rect(rr) * page.rotation_matrix
                    qr = QRectF(x + vr.x0 * z, y + vr.y0 * z, vr.width * z, vr.height * z)
                    col = QColor(style) if style else QColor(0, 0, 0)
                    fill = QColor(col)
                    fill.setAlpha(110)
                    p.fillRect(qr, fill)
                    p.setPen(QPen(col, 1.5))
                    p.drawRect(qr)
        if self.drag_start and self.drag_now:
            p.setPen(QPen(QColor(RED), 1.6, Qt.DashLine))
            p.setBrush(QColor(214, 40, 57, 40))
            p.drawRect(QRect(self.drag_start, self.drag_now).normalized())

    def mousePressEvent(self, e):
        v = self.v
        if v.select_mode and v.doc and e.button() == Qt.LeftButton:
            self.drag_start = self.drag_now = e.pos()
            self.drag_page = v.page_at(e.pos().y())

    def mouseMoveEvent(self, e):
        if self.drag_start:
            self.drag_now = e.pos()
            self.update()

    def mouseReleaseEvent(self, e):
        v = self.v
        if self.drag_start and v.doc:
            a, b = self.drag_start, e.pos()
            self.drag_start = self.drag_now = None
            self.update()
            if abs(a.x() - b.x()) < 4 or abs(a.y() - b.y()) < 4:
                return
            i = self.drag_page
            page = v.doc[i]
            x0, y0 = v.page_x(i), v.offsets[i]
            z = v.zoom
            vis = fitz.Rect((min(a.x(), b.x()) - x0) / z, (min(a.y(), b.y()) - y0) / z,
                            (max(a.x(), b.x()) - x0) / z, (max(a.y(), b.y()) - y0) / z)
            vis = vis & page.rect                        # clip to the visible page
            if vis.is_empty:
                return
            r = vis * page.derotation_matrix             # back to unrotated page coordinates
            r.normalize()
            v.rectSelected.emit(i, r)


class PdfViewer(QWidget):
    """Continuous-scroll PDF viewer with thumbnails, outline, search, zoom, rotate and
    rubber-band selection (emits rectSelected(page_index, Rect) in UNROTATED page coordinates)."""
    rectSelected = pyqtSignal(int, object)
    pageChanged = pyqtSignal(int)

    def __init__(self, select_mode=False, compact=False):
        QWidget.__init__(self)
        self.doc = None
        self.path = ""
        self.zoom = 1.0
        self.fit_mode = "width"
        self.extra_rot = 0
        self.select_mode = select_mode
        self.offsets, self.sizes = [], []
        self.cache = collections.OrderedDict()
        self.highlights = {}
        self.overlays = {}
        self.hits = []
        self.hit_idx = -1
        self._thumb_gen = 0
        self._busy_scroll = False
        self.gap, self.margin = 12, 12

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.btn_prev = QToolButton(); self.btn_prev.setText("<"); self.btn_prev.setToolTip("Previous page")
        self.btn_next = QToolButton(); self.btn_next.setText(">"); self.btn_next.setToolTip("Next page")
        self.spin = QSpinBox(); self.spin.setMinimum(1); self.spin.setMaximum(1); self.spin.setKeyboardTracking(False)
        self.lbl_total = QLabel("/ 0")
        self.btn_zout = QToolButton(); self.btn_zout.setText("-"); self.btn_zout.setToolTip("Zoom out")
        self.btn_zin = QToolButton(); self.btn_zin.setText("+"); self.btn_zin.setToolTip("Zoom in")
        self.btn_fitw = QToolButton(); self.btn_fitw.setText("Fit width")
        self.btn_fitp = QToolButton(); self.btn_fitp.setText("Fit page")
        self.btn_rot = QToolButton(); self.btn_rot.setText("Rotate view"); self.btn_rot.setToolTip("Rotates only what you see, not the file")
        self.lbl_zoom = QLabel("100%")
        self.search = QLineEdit(); self.search.setPlaceholderText("Search text...")
        self.search.setMaximumWidth(180)
        self.btn_sp = QToolButton(); self.btn_sp.setText("^"); self.btn_sp.setToolTip("Previous match")
        self.btn_sn = QToolButton(); self.btn_sn.setText("v"); self.btn_sn.setToolTip("Next match")
        self.lbl_hits = QLabel("")
        for w in (self.btn_prev, self.spin, self.lbl_total, self.btn_next, self.btn_zout, self.lbl_zoom, self.btn_zin,
                  self.btn_fitw, self.btn_fitp):
            bar.addWidget(w)
        if not select_mode:
            bar.addWidget(self.btn_rot)
        bar.addStretch(1)
        for w in (self.search, self.btn_sp, self.btn_sn, self.lbl_hits):
            bar.addWidget(w)
        root.addLayout(bar)

        self.split = QSplitter(Qt.Horizontal)
        self.tabs = QTabWidget()
        self.thumbs = QListWidget()
        self.thumbs.setViewMode(QListView.IconMode)
        self.thumbs.setIconSize(QSize(96, 128))
        self.thumbs.setGridSize(QSize(112, 150))
        self.thumbs.setMovement(QListView.Static)
        self.thumbs.setResizeMode(QListView.Adjust)
        self.thumbs.itemClicked.connect(lambda it: self.go_to(it.data(Qt.UserRole)))
        self.toc = QTreeWidget()
        self.toc.setHeaderHidden(True)
        self.toc.itemClicked.connect(self._toc_click)
        self.tabs.addTab(self.thumbs, "Pages")
        self.tabs.addTab(self.toc, "Contents")
        self.canvas = ViewCanvas(self)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.canvas)
        self.scroll.setWidgetResizable(False)
        self.scroll.setStyleSheet("QScrollArea{border:1px solid #AFC3E6;}")
        self.split.addWidget(self.tabs)
        self.split.addWidget(self.scroll)
        self.split.setStretchFactor(1, 1)
        self.split.setSizes([150, 700])
        if compact:
            self.tabs.hide()
        root.addWidget(self.split, 1)
        if select_mode:
            self.canvas.setCursor(Qt.CrossCursor)

        self.btn_prev.clicked.connect(lambda: self.go_to(self.current_page() - 1))
        self.btn_next.clicked.connect(lambda: self.go_to(self.current_page() + 1))
        self.spin.valueChanged.connect(lambda n: self.go_to(n - 1, from_spin=True))
        self.btn_zin.clicked.connect(lambda: self.set_zoom(self.zoom * 1.2))
        self.btn_zout.clicked.connect(lambda: self.set_zoom(self.zoom / 1.2))
        self.btn_fitw.clicked.connect(lambda: self.fit("width"))
        self.btn_fitp.clicked.connect(lambda: self.fit("page"))
        self.btn_rot.clicked.connect(self.rotate_view)
        self.search.returnPressed.connect(self.do_search)
        self.btn_sn.clicked.connect(lambda: self.step_hit(1))
        self.btn_sp.clicked.connect(lambda: self.step_hit(-1))
        self.scroll.verticalScrollBar().valueChanged.connect(self._scrolled)

    # ---- document
    def load(self, path, password=None):
        doc = open_pdf(path, password)
        self.load_doc(doc, path)

    def load_doc(self, doc, path=""):
        self.close_doc()
        self.doc, self.path = doc, path
        self.extra_rot = 0
        self.highlights, self.overlays, self.hits, self.hit_idx = {}, {}, [], -1
        self.lbl_hits.setText("")
        self.spin.blockSignals(True)
        self.spin.setMaximum(max(1, doc.page_count))
        self.spin.setValue(1)
        self.spin.blockSignals(False)
        self.lbl_total.setText("/ %d" % doc.page_count)
        self.fit("width", relayout=False)
        self._relayout()
        self._fill_toc()
        self._start_thumbs()

    def close_doc(self):
        self._thumb_gen += 1
        if self.doc:
            try:
                self.doc.close()
            except Exception:
                pass
        self.doc = None
        self.cache.clear()
        self.thumbs.clear()
        self.toc.clear()
        self.offsets, self.sizes = [], []
        self.canvas.resize(10, 10)
        self.canvas.update()

    # ---- geometry
    def _page_size(self, i):
        r = self.doc[i].rect
        if self.extra_rot in (90, 270):
            return r.height, r.width
        return r.width, r.height

    def _relayout(self):
        if not self.doc:
            return
        self.sizes = [self._page_size(i) for i in range(self.doc.page_count)]
        self.offsets, y = [], self.margin
        for w, h in self.sizes:
            self.offsets.append(y)
            y += int(h * self.zoom) + self.gap
        maxw = int(max(w for w, h in self.sizes) * self.zoom) + 2 * self.margin
        self.canvas.resize(max(maxw, self.scroll.viewport().width()), y + self.margin)
        self.lbl_zoom.setText("%d%%" % int(self.zoom * 100))
        self.canvas.update()

    def page_x(self, i):
        w = int(self.sizes[i][0] * self.zoom)
        return max(self.margin, (self.canvas.width() - w) // 2)

    def page_at(self, y):
        lo, hi = 0, len(self.offsets) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.offsets[mid] <= y:
                lo = mid
            else:
                hi = mid - 1
        return max(0, lo)

    def get_pixmap(self, i):
        key = (i, round(self.zoom, 3), self.extra_rot)
        pm = self.cache.get(key)
        if pm is not None:
            self.cache.move_to_end(key)
            return pm
        mat = fitz.Matrix(self.zoom, self.zoom)
        if self.extra_rot:
            mat = mat.prerotate(self.extra_rot)
        pix = self.doc[i].get_pixmap(matrix=mat, alpha=False)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
        pm = QPixmap.fromImage(img)
        self.cache[key] = pm
        while len(self.cache) > 24:
            self.cache.popitem(last=False)
        return pm

    # ---- navigation / zoom
    def current_page(self):
        if not self.doc:
            return 0
        return self.page_at(self.scroll.verticalScrollBar().value() + self.scroll.viewport().height() // 3)

    def go_to(self, i, from_spin=False):
        if not self.doc:
            return
        i = max(0, min(self.doc.page_count - 1, i))
        self._busy_scroll = True
        self.scroll.verticalScrollBar().setValue(max(0, self.offsets[i] - self.margin))
        self._busy_scroll = False
        if not from_spin:
            self.spin.blockSignals(True)
            self.spin.setValue(i + 1)
            self.spin.blockSignals(False)
        self.pageChanged.emit(i)

    def _scrolled(self, _v):
        if self.doc and not self._busy_scroll:
            i = self.current_page()
            self.spin.blockSignals(True)
            self.spin.setValue(i + 1)
            self.spin.blockSignals(False)
            self.pageChanged.emit(i)

    def set_zoom(self, z):
        if not self.doc:
            return
        cur = self.current_page()
        self.zoom = max(0.1, min(6.0, z))
        self.fit_mode = ""
        self._relayout()
        self.go_to(cur)

    def fit(self, mode, relayout=True):
        if not self.doc:
            return
        self.fit_mode = mode
        vw = self.scroll.viewport().width() - 2 * self.margin - 4
        vh = self.scroll.viewport().height() - 2 * self.margin
        w, h = self._page_size(self.current_page() if self.offsets else 0)
        if vw < 50:
            vw = 600
        if vh < 50:
            vh = 700
        self.zoom = max(0.1, min(6.0, vw / w if mode == "width" else min(vw / w, vh / h)))
        if relayout:
            cur = self.current_page()
            self._relayout()
            self.go_to(cur)

    def rotate_view(self):
        if not self.doc:
            return
        cur = self.current_page()
        self.extra_rot = (self.extra_rot + 90) % 360
        self.cache.clear()
        self._relayout()
        self.go_to(cur)

    def resizeEvent(self, e):
        QWidget.resizeEvent(self, e)
        if self.doc and self.fit_mode:
            self.fit(self.fit_mode)

    # ---- outline / thumbnails
    def _fill_toc(self):
        self.toc.clear()
        try:
            entries = self.doc.get_toc()
        except Exception:
            entries = []
        stack = []
        for lvl, title, pg in entries:
            it = QTreeWidgetItem([title])
            it.setData(0, Qt.UserRole, max(0, pg - 1))
            while stack and stack[-1][0] >= lvl:
                stack.pop()
            if stack:
                stack[-1][1].addChild(it)
            else:
                self.toc.addTopLevelItem(it)
            stack.append((lvl, it))
        self.toc.expandToDepth(0)

    def _toc_click(self, it, _c):
        self.go_to(it.data(0, Qt.UserRole))

    def _start_thumbs(self):
        self._thumb_gen += 1
        gen = self._thumb_gen
        n = self.doc.page_count
        for i in range(n):
            it = QListWidgetItem("%d" % (i + 1))
            it.setData(Qt.UserRole, i)
            it.setTextAlignment(Qt.AlignHCenter)
            self.thumbs.addItem(it)
        self._thumb_next = 0

        def step():
            if gen != self._thumb_gen or not self.doc:
                return
            for _ in range(4):
                i = self._thumb_next
                if i >= n:
                    return
                self._thumb_next += 1
                try:
                    pg = self.doc[i]
                    z = 110.0 / max(pg.rect.width, pg.rect.height)
                    pix = pg.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
                    img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
                    self.thumbs.item(i).setIcon(QIcon(QPixmap.fromImage(img)))
                except Exception:
                    pass
            QTimer.singleShot(5, step)
        QTimer.singleShot(30, step)

    # ---- search
    def do_search(self):
        if not self.doc:
            return
        term = self.search.text().strip()
        self.highlights, self.hits, self.hit_idx = {}, [], -1
        if not term:
            self.lbl_hits.setText("")
            self.canvas.update()
            return
        dlg = QProgressDialog("Searching...", "Cancel", 0, self.doc.page_count, self)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setMinimumDuration(400)
        for i in range(self.doc.page_count):
            dlg.setValue(i)
            if dlg.wasCanceled():
                break
            for r in self.doc[i].search_for(term):
                self.hits.append((i, r))
        dlg.setValue(self.doc.page_count)
        self.lbl_hits.setText("%d match%s" % (len(self.hits), "" if len(self.hits) == 1 else "es"))
        if self.hits:
            self.step_hit(1)
        else:
            self.canvas.update()

    def step_hit(self, d):
        if not self.hits:
            return
        self.hit_idx = (self.hit_idx + d) % len(self.hits)
        self.highlights = {}
        for k, (i, r) in enumerate(self.hits):
            self.highlights.setdefault(i, []).append((r, k == self.hit_idx))
        i, r = self.hits[self.hit_idx]
        vr = fitz.Rect(r) * self.doc[i].rotation_matrix
        self._busy_scroll = True
        self.scroll.verticalScrollBar().setValue(max(0, int(self.offsets[i] + vr.y0 * self.zoom - 80)))
        self._busy_scroll = False
        self.lbl_hits.setText("%d / %d" % (self.hit_idx + 1, len(self.hits)))
        self.canvas.update()

    # ---- overlays for tools (redaction boxes etc.)
    def set_overlays(self, mapping):
        """mapping: page_index -> list of (fitz.Rect in unrotated page coords, '#rrggbb' colour)."""
        self.overlays = mapping
        self.canvas.update()


# ---------------------------------------------------------------- page organiser widget
class PageOrganiser(QWidget):
    """Thumbnail grid: drag to reorder, multi-select, rotate, delete, duplicate."""

    def __init__(self):
        QWidget.__init__(self)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        for text, fn in (("Rotate left", lambda: self.rotate(-90)), ("Rotate right", lambda: self.rotate(90)),
                         ("Delete", self.delete_sel), ("Duplicate", self.duplicate_sel),
                         ("Move left", lambda: self.shift(-1)), ("Move right", lambda: self.shift(1)),
                         ("Select all", lambda: self.list.selectAll()), ("Reset", self.reset)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.list = QListWidget()
        self.list.setViewMode(QListView.IconMode)
        self.list.setIconSize(QSize(120, 160))
        self.list.setGridSize(QSize(140, 196))
        self.list.setMovement(QListView.Static)
        self.list.setResizeMode(QListView.Adjust)
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.setMinimumHeight(300)
        v.addWidget(self.list, 1)
        self.src_path, self._gen = "", 0
        self.lbl = QLabel("")
        self.lbl.setObjectName("hint")
        v.addWidget(self.lbl)

    def load(self, path, password=None):
        doc = open_pdf(path, password)
        self.src_path = path
        self._gen += 1
        gen = self._gen
        self.list.clear()
        n = doc.page_count
        self._pending = list(range(n))

        def step():
            if gen != self._gen:
                doc.close()
                return
            for _ in range(5):
                if not self._pending:
                    doc.close()
                    self._count()
                    return
                i = self._pending.pop(0)
                pg = doc[i]
                z = 150.0 / max(pg.rect.width, pg.rect.height)
                pix = pg.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
                self._add_item(i, 0, QPixmap.fromImage(img))
            QTimer.singleShot(5, step)
        # items are added progressively so the window stays responsive
        QTimer.singleShot(10, step)

    def _add_item(self, src, rot, base_pm, label=None):
        it = QListWidgetItem(QIcon(base_pm), label or "Page %d" % (src + 1))
        it.setData(Qt.UserRole, (src, rot))
        it.setData(Qt.UserRole + 1, base_pm)
        it.setTextAlignment(Qt.AlignHCenter)
        self.list.addItem(it)
        self._count()

    def _apply_rot(self, it):
        src, rot = it.data(Qt.UserRole)
        base = it.data(Qt.UserRole + 1)
        pm = base.transformed(QTransform().rotate(rot), Qt.SmoothTransformation) if rot else base
        it.setIcon(QIcon(pm))

    def rotate(self, deg):
        for it in self.list.selectedItems():
            src, rot = it.data(Qt.UserRole)
            it.setData(Qt.UserRole, (src, (rot + deg) % 360))
            self._apply_rot(it)

    def delete_sel(self):
        for it in self.list.selectedItems():
            self.list.takeItem(self.list.row(it))
        self._count()

    def duplicate_sel(self):
        rows = sorted(self.list.row(i) for i in self.list.selectedItems())
        for off, r in enumerate(rows):
            it = self.list.item(r + off)
            src, rot = it.data(Qt.UserRole)
            new = QListWidgetItem(it.icon(), it.text() + " (copy)")
            new.setData(Qt.UserRole, (src, rot))
            new.setData(Qt.UserRole + 1, it.data(Qt.UserRole + 1))
            new.setTextAlignment(Qt.AlignHCenter)
            self.list.insertItem(r + off + 1, new)
        self._count()

    def shift(self, d):
        rows = sorted([self.list.row(i) for i in self.list.selectedItems()], reverse=(d > 0))
        for r in rows:
            nr = r + d
            if 0 <= nr < self.list.count():
                it = self.list.takeItem(r)
                self.list.insertItem(nr, it)
                it.setSelected(True)

    def reset(self):
        if self.src_path:
            try:
                self.load(self.src_path)
            except UserError as e:
                QMessageBox.warning(self, APP_NAME, str(e))

    def order(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]

    def _count(self):
        self.lbl.setText("%d page(s) in the new document. Drag thumbnails to reorder." % self.list.count())


# ---------------------------------------------------------------- base class for every tool
class ToolPage(QWidget):
    key, title, subtitle, group = "tool", "Tool", "", "Organize"
    needs_output = True
    no_action = False            # True = viewer-style page without Run button / log
    prime_only = False
    action_text = "Run"

    def __init__(self, ctx):
        QWidget.__init__(self)
        self.ctx = ctx
        self.worker = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.NoFrame)
        outer.addWidget(sc)
        body = QWidget()
        body.setObjectName("content")
        sc.setWidget(body)
        self.page_layout = QVBoxLayout(body)
        self.page_layout.setContentsMargins(28, 20, 28, 16)
        self.page_layout.setSpacing(10)
        t = QLabel(self.title)
        t.setObjectName("pageTitle")
        self.page_layout.addWidget(t)
        acc = QFrame()
        acc.setObjectName("accent")
        acc.setFixedSize(90, 4)
        self.page_layout.addWidget(acc)
        st = QLabel(self.subtitle)
        st.setObjectName("subtitle")
        st.setWordWrap(True)
        self.page_layout.addWidget(st)
        self.card = QFrame()
        self.card.setObjectName("card")
        self.form = QVBoxLayout(self.card)
        self.form.setContentsMargins(16, 14, 16, 14)
        self.form.setSpacing(8)
        self.page_layout.addWidget(self.card)
        self.build(self.form)
        self.out_picker = None
        if self.needs_output:
            oc = QFrame()
            oc.setObjectName("card")
            ol = QVBoxLayout(oc)
            ol.setContentsMargins(16, 12, 16, 12)
            lab = QLabel("Save output to")
            lab.setObjectName("fieldLabel")
            self.out_picker = OutputPicker(self.key)
            ol.addWidget(lab)
            ol.addWidget(self.out_picker)
            ol.addWidget(hint_label("Results are always saved as NEW files here. Your original files are never changed."))
            self.page_layout.addWidget(oc)
        if self.no_action:
            self.page_layout.addStretch(0)
            self.after_build()
            return
        row = QHBoxLayout()
        self.run_btn = QPushButton(self.action_text)
        self.run_btn.setObjectName("primary")
        self.run_btn.setMinimumHeight(44)
        self.run_btn.clicked.connect(self.on_run)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumHeight(44)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.on_cancel)
        row.addWidget(self.run_btn, 3)
        row.addWidget(self.cancel_btn, 1)
        self.page_layout.addLayout(row)
        self.status = QLabel("Ready.")
        self.status.setObjectName("status")
        self.page_layout.addWidget(self.status)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(True)
        self.page_layout.addWidget(self.bar)
        self.logbox = QTextEdit()
        self.logbox.setObjectName("log")
        self.logbox.setReadOnly(True)
        self.logbox.setMaximumHeight(120)
        self.page_layout.addWidget(self.logbox)
        self.page_layout.addStretch(1)
        self.after_build()

    # -- to override
    def build(self, layout):
        pass

    def after_build(self):
        pass

    def make_task(self, out_dir):
        raise NotImplementedError

    def on_show(self):
        pass

    # -- form helpers
    def add_row(self, label, widget, hint=None, layout=None):
        lay = layout or self.form
        if label:
            l = QLabel(label)
            l.setObjectName("fieldLabel")
            lay.addWidget(l)
        lay.addWidget(widget)
        if hint:
            lay.addWidget(hint_label(hint))
        return widget

    def add_hint(self, text, layout=None):
        (layout or self.form).addWidget(hint_label(text))

    def combo(self, items, current=None):
        c = QComboBox()
        for it in items:
            if isinstance(it, tuple):
                c.addItem(it[0], it[1])
            else:
                c.addItem(it)
        if current is not None:
            i = c.findText(str(current))
            if i >= 0:
                c.setCurrentIndex(i)
        return c

    def spin(self, lo, hi, val, suffix="", step=1):
        s = QSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        s.setSingleStep(step)
        if suffix:
            s.setSuffix(suffix)
        return s

    def dspin(self, lo, hi, val, suffix="", step=0.5, dec=1):
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        s.setSingleStep(step)
        s.setDecimals(dec)
        if suffix:
            s.setSuffix(suffix)
        return s

    # -- running
    def log(self, text):
        self.logbox.append(text)

    def set_busy(self, busy):
        self.run_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.card.setEnabled(not busy)
        if hasattr(self.ctx, "set_busy"):
            self.ctx.set_busy(self, busy)

    def warn(self, msg):
        QMessageBox.warning(self, APP_NAME, msg)

    def on_run(self):
        if self.worker and self.worker.isRunning():
            return
        try:
            out = ""
            if self.needs_output:
                out = ensure_out_dir(self.out_picker.path())
            task = self.make_task(out)
        except UserError as e:
            self.warn(str(e))
            return
        if task is None:
            return
        self.out_dir_last = out
        self.run_task(task, self.on_success)

    def run_task(self, task, on_success=None, on_fail=None):
        self.logbox.clear()
        self.bar.setValue(0)
        self.status.setText("Working...")
        self.set_busy(True)
        w = Worker(task, self)
        w.progress.connect(lambda p, m: (self.bar.setValue(p), m and self.status.setText(m)))
        w.succeeded.connect(lambda r: self._done_ok(r, on_success))
        w.failed.connect(lambda m, u: self._done_fail(m, u, on_fail))
        w.cancelled.connect(self._done_cancel)
        self.worker = w
        w.start()

    def on_cancel(self):
        if self.worker:
            self.worker.cancel()
            self.status.setText("Cancelling...")
            self.cancel_btn.setEnabled(False)

    def _done_ok(self, res, cb):
        self.set_busy(False)
        self.bar.setValue(100)
        self.status.setText("Done.")
        if cb:
            cb(res)

    def _done_fail(self, msg, is_user, cb):
        self.set_busy(False)
        self.status.setText("Stopped - see the message.")
        self.log(msg)
        if cb:
            cb(msg)
        (self.warn if is_user else lambda m: QMessageBox.critical(self, APP_NAME, m))(msg)

    def _done_cancel(self):
        self.set_busy(False)
        self.bar.setValue(0)
        self.status.setText("Cancelled. Nothing was saved from the unfinished job.")
        self.log("Cancelled by user.")

    def on_success(self, res):
        if isinstance(res, str):
            res = {"message": res}
        res = res or {}
        msg = res.get("message", "Finished.")
        files = res.get("files", [])
        for f in files:
            self.log("Saved: %s" % f)
        self.status.setText(msg.split("\n")[0])
        folder = res.get("folder") or getattr(self, "out_dir_last", "")
        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setIcon(QMessageBox.Information)
        box.setText(msg)
        openb = None
        if folder and os.path.isdir(folder):
            openb = box.addButton("Open folder", QMessageBox.AcceptRole)
        box.addButton("Close", QMessageBox.RejectRole)
        box.exec_()
        if openb is not None and box.clickedButton() is openb:
            open_folder(files[0] if files else folder)

    def shutdown(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(3000)
# ============================================================================
#  SECTION E - PHASE 1 TOOLS: merge, split, extract, number, rearrange,
#              PDF<->image, password
# ============================================================================
def pdf_page_count(path):
    d = open_pdf(path)
    n = d.page_count
    d.close()
    return n


def strip_pdf_ext(name):
    name = name.strip()
    return name[:-4] if name.lower().endswith(".pdf") else name


NUMBER_FORMATS = ["1", "Page 1", "Page 1 of N", "1 of N", "- 1 -"]
POSITIONS = [("Bottom center", "bottom-center"), ("Bottom right", "bottom-right"), ("Bottom left", "bottom-left"),
             ("Top center", "top-center"), ("Top right", "top-right"), ("Top left", "top-left")]


def format_number_label(fmt, num, last):
    return {"1": "%d", "Page 1": "Page %d", "Page 1 of N": "Page %d of " + str(last),
            "1 of N": "%d of " + str(last), "- 1 -": "- %d -"}.get(fmt, "%d") % num


def core_number_pages(src, dst, start, fmt, pos, fontsize, margin, color, report=None):
    doc = open_pdf(src)
    n = doc.page_count
    last = start + n - 1
    for i in range(n):
        draw_label(doc[i], format_number_label(fmt, start + i, last), pos, fontsize, margin, color)
        if report and i % 5 == 0:
            report(5 + 85 * i / n, "Numbering page %d of %d" % (i + 1, n))
    save_pdf(doc, dst)
    doc.close()


class MergeTool(ToolPage):
    key, title, group = "merge", "Merge PDFs", "Organize"
    subtitle = "Combine several PDFs into one file, in the order shown in the list."

    def build(self, L):
        self.files = FileListWidget("merge")
        self.add_row("PDF files (drag to reorder, or drop files from the desktop)", self.files)
        self.name = QLineEdit("merged")
        self.add_row("Output file name", self.name, "Without .pdf. If the name exists, _1, _2... is added automatically.")

    def make_task(self, out):
        files = self.files.paths()
        if len(files) < 2:
            raise UserError("Add at least two PDF files to merge.")
        name = safe_name(strip_pdf_ext(self.name.text()) or "merged")

        def task(report, cancelled):
            new = fitz.open()
            for i, f in enumerate(files):
                report(3 + 87 * i / len(files), "Adding %s" % os.path.basename(f))
                src = open_pdf(f)
                new.insert_pdf(src)
                src.close()
            report(93, "Saving...")
            path = save_pdf(new, unique_path(out, name, ".pdf"))
            return {"message": "Merged %d files into one PDF with %d pages:\n%s" % (len(files), new.page_count, path),
                    "files": [path]}
        return task


class SplitTool(ToolPage):
    key, title, group = "split", "Split PDF", "Organize"
    subtitle = "Cut one PDF into several. Each page or range you enter becomes its own file."

    def build(self, L):
        self.pdf = PdfPicker("split")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("1, 3-5, 8-10")
        self.add_row("Pages / ranges", self.pages,
                     "Example: 1, 3-5, 8-10 makes 3 PDFs (page 1; pages 3-5; pages 8-10). Separate with commas.")

    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        toks = parse_page_spec(self.pages.text(), n)
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            src = open_pdf(path)
            files = []
            for k, (a, b) in enumerate(toks, 1):
                report(5 + 90 * (k - 1) / len(toks), "Creating part %d of %d" % (k, len(toks)))
                new = fitz.open()
                new.insert_pdf(src, from_page=a - 1, to_page=b - 1)
                label = ("%d" % a) if a == b else ("%d-%d" % (a, b))
                files.append(save_pdf(new, unique_path(out, "%s_part%d_pages_%s" % (stem, k, label), ".pdf")))
                new.close()
            src.close()
            return {"message": "Created %d PDF file(s)." % len(files), "files": files}
        return task


class ExtractTool(ToolPage):
    key, title, group = "extract", "Extract Pages", "Organize"
    subtitle = "Pick pages from a PDF and save them together as one new PDF, in the order you type."

    def build(self, L):
        self.pdf = PdfPicker("extract")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("1, 3-5, 8-10")
        self.add_row("Pages / ranges", self.pages, "1, 3-5, 8-10 gives one PDF with pages 1,3,4,5,8,9,10.")

    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        pages = expand_pages(parse_page_spec(self.pages.text(), n))
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            src = open_pdf(path)
            new = build_from_pages(src, pages, report, 5, 85)
            p = save_pdf(new, unique_path(out, stem + "_extracted", ".pdf"))
            return {"message": "Extracted %d page(s) into:\n%s" % (len(pages), p), "files": [p]}
        return task


class NumberTool(ToolPage):
    key, title, group = "number", "Page Numbering", "Organize"
    subtitle = "Stamp page numbers on every page. Works on rotated pages too."

    def build(self, L):
        self.pdf = PdfPicker("number")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        g = QGridLayout()
        self.pos = self.combo([p[0] for p in POSITIONS])
        self.start = self.spin(1, 999999, 1)
        self.fmt = self.combo(NUMBER_FORMATS, "Page 1 of N")
        self.size = self.spin(6, 48, 10, " pt")
        self.margin = self.spin(5, 200, 24, " pt")
        self.color = self.combo(["Blue", "Red", "Black", "Gray"], "Black")
        for r, (lab, w) in enumerate((("Position", self.pos), ("Starting number", self.start), ("Format", self.fmt),
                                      ("Font size", self.size), ("Distance from edge", self.margin), ("Colour", self.color))):
            g.addWidget(QLabel(lab), r // 2, (r % 2) * 2)
            g.addWidget(w, r // 2, (r % 2) * 2 + 1)
        L.addLayout(g)
        self.preview = QLabel("")
        self.preview.setObjectName("preview")
        self.add_row("Preview of the first label", self.preview,
                     "In 'of N' formats, N is the last number used (start + pages - 1).")
        for w in (self.start, self.fmt):
            (w.valueChanged if isinstance(w, QSpinBox) else w.currentIndexChanged).connect(self._prev)
        self.pdf.changed.connect(self._prev)
        self._prev()

    def _prev(self, *a):
        n = self.pdf.page_count or 0
        last = self.start.value() + max(n, 1) - 1
        self.preview.setText(format_number_label(self.fmt.currentText(), self.start.value(), last if n else "N"))

    def make_task(self, out):
        path = self.pdf.require()
        pdf_page_count(path)
        pos = POSITIONS[self.pos.currentIndex()][1]
        args = (self.start.value(), self.fmt.currentText(), pos, self.size.value(), self.margin.value(),
                COLORS[self.color.currentText()])
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            dst = unique_path(out, stem + "_numbered", ".pdf")
            core_number_pages(path, dst, *args, report=report)
            return {"message": "Page numbers added:\n%s" % dst, "files": [dst]}
        return task


class RearrangeTool(ToolPage):
    key, title, group = "rearrange", "Rearrange Pages", "Organize"
    subtitle = "Type the new page order. Reverse ranges (10-4) and repeated pages are allowed."

    def build(self, L):
        self.pdf = PdfPicker("rearrange")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.order = QLineEdit()
        self.order.setPlaceholderText("3, 1, 2, 4-10")
        self.add_row("New page order", self.order, "Example: 3, 1, 2, 4-10  or  10-4 to reverse part of the file.")
        self.rest = QCheckBox("Add pages I did not list to the end")
        self.rest.setChecked(True)
        L.addWidget(self.rest)

    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        pages = expand_pages(parse_page_spec(self.order.text(), n, allow_reverse=True))
        if self.rest.isChecked():
            used = set(pages)
            pages += [p for p in range(n) if p not in used]
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            src = open_pdf(path)
            new = build_from_pages(src, pages, report, 5, 85)
            p = save_pdf(new, unique_path(out, stem + "_rearranged", ".pdf"))
            return {"message": "New order saved (%d pages):\n%s" % (len(pages), p), "files": [p]}
        return task


class PdfToImageTool(ToolPage):
    key, title, group = "pdf2img", "PDF to Image", "Convert"
    subtitle = "Save PDF pages as PNG or JPG pictures in a new folder."

    def build(self, L):
        self.pdf = PdfPicker("pdf2img")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.all_r = QRadioButton("All pages")
        self.sel_r = QRadioButton("Selected pages:")
        self.all_r.setChecked(True)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("1, 3-5, 8-10")
        L.addWidget(hbox(self.all_r, self.sel_r, self.pages))
        self.fmt = self.combo(["PNG", "JPG"])
        self.dpi = self.combo(["72", "100", "150", "200", "300"], "150")
        L.addWidget(hbox(QLabel("Format"), self.fmt, QLabel("Resolution (DPI)"), self.dpi, None))
        self.add_hint("Higher DPI = sharper but bigger files and more memory. Pictures go into a new sub-folder.")

    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        pages = list(range(n)) if self.all_r.isChecked() else expand_pages(parse_page_spec(self.pages.text(), n))
        fmt, dpi = self.fmt.currentText().lower(), int(self.dpi.currentText())
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            src = open_pdf(path)
            folder = unique_dir(out, stem + "_images")
            width = len(str(n))
            files = []
            for k, p in enumerate(pages):
                report(3 + 94 * k / len(pages), "Rendering page %d" % (p + 1))
                pix = src[p].get_pixmap(dpi=dpi, alpha=False)
                f = os.path.join(folder, "%s_page_%s.%s" % (stem, str(p + 1).zfill(width), "jpg" if fmt == "jpg" else "png"))
                if fmt == "jpg":
                    pix.save(f, jpg_quality=90)
                else:
                    pix.save(f)
                files.append(f)
                pix = None
            return {"message": "Saved %d image(s) in:\n%s" % (len(files), folder), "files": files[:1], "folder": folder}
        return task


def _prepare_image_for_pdf(path):
    """Return (bytes, width_px, height_px, dpi) ready for PyMuPDF insert_image."""
    if not HAVE_PIL:
        raise UserError("The Pillow library is missing. Run:  pip install Pillow")
    try:
        im = Image.open(path)
        im.seek(0)
    except Exception:
        raise UserError("The image '%s' could not be read." % os.path.basename(path))
    raw_jpeg = (im.format == "JPEG")
    try:
        fixed = ImageOps.exif_transpose(im)
        changed = fixed is not im and fixed.size != im.size or (fixed is not im and getattr(im, "getexif", None) and im.getexif().get(0x0112, 1) != 1)
        im2 = fixed
    except Exception:
        im2, changed = im, False
    dpi = 0
    try:
        d = im.info.get("dpi")
        dpi = float(d[0]) if d else 0
    except Exception:
        dpi = 0
    if dpi < 36 or dpi > 1200:
        dpi = 150
    if im2.mode in ("RGBA", "LA", "P"):
        im2 = im2.convert("RGBA")
        bg = Image.new("RGB", im2.size, (255, 255, 255))
        bg.paste(im2, mask=im2.split()[-1])
        im2, raw_jpeg = bg, False
    elif im2.mode not in ("RGB", "L"):
        im2, raw_jpeg = im2.convert("RGB"), False
    if raw_jpeg and not changed:
        with open(path, "rb") as f:
            data = f.read()
    else:
        buf = io.BytesIO()
        if im.format == "JPEG":
            im2.save(buf, "JPEG", quality=92)
        else:
            im2.save(buf, "PNG")
        data = buf.getvalue()
    return data, im2.size[0], im2.size[1], dpi


def core_images_to_pdf(files, dst, size_mode, report=None):
    doc = fitz.open()
    for i, f in enumerate(files):
        if report:
            report(3 + 90 * i / len(files), "Adding %s" % os.path.basename(f))
        data, w, h, dpi = _prepare_image_for_pdf(f)
        if size_mode == "image":
            pw, ph = min(14400, w * 72.0 / dpi), min(14400, h * 72.0 / dpi)
            page = doc.new_page(width=pw, height=ph)
            rect = fitz.Rect(0, 0, pw, ph)
        else:
            a, b = (595.28, 841.89) if size_mode == "A4" else (612.0, 792.0)
            pw, ph = (b, a) if w > h else (a, b)
            page = doc.new_page(width=pw, height=ph)
            m = 10.0
            s = min((pw - 2 * m) / w, (ph - 2 * m) / h)
            rw, rh = w * s, h * s
            rect = fitz.Rect((pw - rw) / 2, (ph - rh) / 2, (pw + rw) / 2, (ph + rh) / 2)
        page.insert_image(rect, stream=data)
    save_pdf(doc, dst)
    doc.close()


class ImageToPdfTool(ToolPage):
    key, title, group = "img2pdf", "Image to PDF", "Convert"
    subtitle = "Turn pictures (JPG, PNG, BMP, GIF, TIFF) into one PDF, one picture per page."

    def build(self, L):
        self.files = FileListWidget("img2pdf", IMG_EXT, "Images (*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff)", "Select images")
        self.add_row("Images (drag to reorder)", self.files)
        self.size = self.combo([("Same as image", "image"), ("A4 fitted", "A4"), ("Letter fitted", "Letter")])
        self.name = QLineEdit("images")
        L.addWidget(hbox(QLabel("Page size"), self.size, QLabel("Output file name"), self.name))
        self.add_hint("'Fitted' sizes keep the picture's shape and switch to landscape automatically when the picture is wide. "
                      "For multi-frame GIF/TIFF only the first frame is used.")

    def make_task(self, out):
        files = self.files.paths()
        if not files:
            raise UserError("Add at least one image.")
        mode = self.size.currentData()
        name = safe_name(strip_pdf_ext(self.name.text()) or "images")

        def task(report, cancelled):
            dst = unique_path(out, name, ".pdf")
            core_images_to_pdf(files, dst, mode, report)
            return {"message": "Created a PDF with %d page(s):\n%s" % (len(files), dst), "files": [dst]}
        return task


class PasswordTool(ToolPage):
    key, title, group = "password", "Password protect / remove", "Security"
    subtitle = "Add AES-256 protection with optional print/copy/edit limits, or remove a password you know."

    def build(self, L):
        self.pdf = PdfPicker("password")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.r_add, self.r_rem = QRadioButton("Add password / restrictions"), QRadioButton("Remove password")
        self.r_add.setChecked(True)
        L.addWidget(hbox(self.r_add, self.r_rem, None))
        self.cur = PasswordField("Current password (only if the file is already protected)")
        self.add_row("Current password", self.cur, "Needed to remove protection, or to add protection to an already protected file.")
        self.add_box = QWidget()
        a = QVBoxLayout(self.add_box)
        a.setContentsMargins(0, 0, 0, 0)
        self.p1, self.p2, self.owner = PasswordField("Password to open the file"), PasswordField("Repeat password"), PasswordField("Separate permissions (owner) password")
        self.add_row("Open password (leave empty to only restrict)", self.p1, layout=a)
        self.add_row("Repeat open password", self.p2, layout=a)
        self.add_row("Permissions password", self.owner, "Required if you forbid anything below. It lets you lift the limits later.", layout=a)
        self.no_print, self.no_copy, self.no_edit = QCheckBox("Forbid printing"), QCheckBox("Forbid copying text/images"), QCheckBox("Forbid editing, annotating and assembling")
        for c in (self.no_print, self.no_copy, self.no_edit):
            a.addWidget(c)
        self.show = QCheckBox("Show passwords while typing")
        self.show.toggled.connect(lambda on: [f.set_visible_text(on) for f in (self.cur, self.p1, self.p2, self.owner)])
        a.addWidget(self.show)
        a.addWidget(hint_label("Encryption: AES-256. Passwords are never stored by this program. There is NO way to recover a forgotten password."))
        L.addWidget(self.add_box)
        self.r_add.toggled.connect(lambda on: self.add_box.setVisible(on))

    def make_task(self, out):
        path = self.pdf.require()
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])
        cur = self.cur.text()
        if self.r_rem.isChecked():
            def task(report, cancelled):
                d = fitz.open(path) if os.path.isfile(path) else None
                if not d.is_encrypted:
                    d.close()
                    raise UserError("This PDF is not password-protected, so there is nothing to remove.")
                if not cur:
                    d.close()
                    raise UserError("Enter the current password to remove the protection.")
                rc = d.authenticate(cur)
                if not rc:
                    d.close()
                    raise UserError("The password is wrong. (Passwords cannot be recovered or cracked by this program.)")
                report(50, "Saving unprotected copy...")
                dst = unique_path(out, stem + "_unprotected", ".pdf")
                save_pdf(d, dst, encryption=fitz.PDF_ENCRYPT_NONE)
                return {"message": "Password removed. New file:\n%s" % dst, "files": [dst]}
            return task
        up, up2, ow = self.p1.text(), self.p2.text(), self.owner.text()
        if up != up2:
            raise UserError("The two open passwords are different.")
        restrict = self.no_print.isChecked() or self.no_copy.isChecked() or self.no_edit.isChecked()
        if not up and not restrict:
            raise UserError("Enter an open password, or tick at least one restriction.")
        if restrict and not ow:
            raise UserError("Any restriction needs a permissions (owner) password. Please enter one.")
        perm = int(fitz.PDF_PERM_ACCESSIBILITY | fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY | fitz.PDF_PERM_ANNOTATE |
                   fitz.PDF_PERM_FORM | fitz.PDF_PERM_MODIFY | fitz.PDF_PERM_ASSEMBLE | fitz.PDF_PERM_PRINT_HQ)
        if self.no_print.isChecked():
            perm &= ~(int(fitz.PDF_PERM_PRINT) | int(fitz.PDF_PERM_PRINT_HQ))
        if self.no_copy.isChecked():
            perm &= ~int(fitz.PDF_PERM_COPY)
        if self.no_edit.isChecked():
            perm &= ~(int(fitz.PDF_PERM_MODIFY) | int(fitz.PDF_PERM_ANNOTATE) | int(fitz.PDF_PERM_ASSEMBLE))
        owner_pw = ow or up

        def task(report, cancelled):
            d = fitz.open(path)
            if d.needs_pass and not d.authenticate(cur):
                d.close()
                raise UserError("This file is already protected. Enter its current password to add new protection.")
            report(50, "Encrypting...")
            dst = unique_path(out, stem + "_protected", ".pdf")
            save_pdf(d, dst, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=up, owner_pw=owner_pw, permissions=perm)
            return {"message": "Protected copy saved:\n%s\n\nKeep your passwords safe - they cannot be recovered." % dst,
                    "files": [dst]}
        return task
# ============================================================================
#  SECTION F - PHASE 2 TOOLS (part 1): compress, page tools, organiser,
#              watermark / stamps, header / footer
# ============================================================================
# preset -> (only images above this dpi are resized, resized to this dpi, JPEG quality)
COMPRESS_PRESETS = collections.OrderedDict([
    ("Lossless", (0, 0, 0)),
    ("Best quality", (330, 300, 92)),
    ("High quality", (240, 200, 86)),
    ("Balanced", (180, 150, 76)),
    ("Smallest file", (130, 110, 60)),
])
COMPRESS_LABELS = collections.OrderedDict([
    ("Lossless", "Lossless - pictures are not changed at all"),
    ("Best quality", "Best quality - looks the same even when zoomed in"),
    ("High quality", "High quality (recommended) - sharp on screen and in print"),
    ("Balanced", "Balanced - good for e-mail"),
    ("Smallest file", "Smallest file - for strict upload limits"),
    ("Custom", "Custom - choose DPI and JPEG quality yourself"),
])
COMPRESS_LEVELS = {"Low": "Lossless", "Medium": "High quality", "High": "Balanced"}      # names used by older saved batch pipelines
# quality ladder used by "fit under a size": best first
COMPRESS_LADDER = [(0, 0, 0), (330, 300, 92), (280, 240, 89), (240, 200, 86), (210, 175, 81), (180, 150, 76), (160, 130, 70),
                   (145, 120, 64), (130, 110, 58), (115, 96, 50), (100, 84, 42), (90, 72, 35)]


def _img_is_graphic(im):
    """True for logos / screenshots / charts (few flat colours): JPEG would smear them, so they stay lossless."""
    t = im.resize((min(im.width, 160), min(im.height, 160)), Image.NEAREST)
    cols = t.convert("RGB").getcolors(maxcolors=96)
    return cols is not None


def _img_is_gray(im):
    """True when a colour picture holds no colour at all (a black-and-white page scanned in colour mode)."""
    if im.mode != "RGB":
        return False
    t = im.resize((min(im.width, 420), min(im.height, 420)), Image.NEAREST)
    r, g, b = t.split()
    from PIL import ImageChops
    for x, y in ((r, g), (g, b), (r, b)):
        if ImageChops.difference(x, y).getextrema()[1] > 10:
            return False
    return True


def _image_dpi_map(doc, cancelled=None):
    """{xref: highest DPI at which the image is shown anywhere in the file}.  Images never shown are left out."""
    res = {}
    for page in doc:
        if cancelled and cancelled():
            raise Cancelled()
        try:
            infos = page.get_image_info(xrefs=True)
        except Exception:
            continue
        for it in infos:
            x = it.get("xref") or 0
            r = fitz.Rect(it["bbox"])
            if x <= 0 or r.width < 1 or r.height < 1:
                continue
            tr = it.get("transform")
            wpt, hpt = r.width, r.height
            if tr:                                        # true drawn size, also right for rotated placements
                wpt = math.hypot(tr[0], tr[1]) or wpt
                hpt = math.hypot(tr[2], tr[3]) or hpt
            dpi = max(it["width"] / (wpt / 72.0), it["height"] / (hpt / 72.0))
            res[x] = max(res.get(x, 0), dpi)
    return res


def _recompress_images(doc, thr, tgt, q, gray=False, report=None, cancelled=None, stats=None):
    """Resize / re-encode the pictures of an open PDF with Pillow.  Every picture is replaced only if the new
    version is clearly smaller; line-art, logos, masks and black-and-white fax pictures are never made lossy."""
    stats = stats if stats is not None else {}
    dpis = _image_dpi_map(doc, cancelled)
    todo = sorted(dpis)
    stats["seen"] = len(todo)
    page0 = doc[0]
    for n, xref in enumerate(todo):
        if cancelled and cancelled():
            raise Cancelled()
        if report and n % 3 == 0:
            report(12 + 55.0 * n / max(1, len(todo)), "Optimising picture %d of %d..." % (n + 1, len(todo)))
        try:
            if doc.xref_get_key(xref, "ImageMask")[1] == "true" or doc.xref_get_key(xref, "Mask")[0] != "null":
                stats["kept"] = stats.get("kept", 0) + 1
                continue
            bpc = doc.xref_get_key(xref, "BitsPerComponent")[1]
            if bpc == "1":
                stats["bw"] = stats.get("bw", 0) + 1
                continue
            sm = doc.xref_get_key(xref, "SMask")
            old_len = len(doc.xref_stream_raw(xref) or b"")
            if old_len < 6000:
                continue
            filt = doc.xref_get_key(xref, "Filter")[1]
            was_lossy = "DCT" in filt or "JPX" in filt
            pix = fitz.Pixmap(doc, xref)
            if pix.colorspace is None or pix.width < 48 or pix.height < 48:
                continue
            if pix.alpha:
                pix = fitz.Pixmap(pix, 0)
            if pix.colorspace.n not in (1, 3):
                pix = fitz.Pixmap(fitz.csRGB, pix)
            im = Image.frombytes("L" if pix.n == 1 else "RGB", (pix.width, pix.height), pix.samples)
            pix = None
            dpi = dpis[xref]
            scale = 1.0
            if thr and tgt and dpi > thr:
                scale = float(tgt) / dpi
            graphic = (not was_lossy) and _img_is_graphic(im)
            if scale < 1.0:
                im = im.resize((max(8, int(round(im.width * scale))), max(8, int(round(im.height * scale)))), Image.LANCZOS)
            if gray and im.mode != "L":
                im = im.convert("L")
            elif _img_is_gray(im):
                im = im.convert("L")
            buf = io.BytesIO()
            if graphic:
                if scale >= 1.0 and not gray:
                    stats["kept"] = stats.get("kept", 0) + 1
                    continue
                im.save(buf, "PNG", optimize=True)
            else:
                kw = dict(quality=int(q), optimize=True)
                if im.mode == "RGB":
                    kw["subsampling"] = 0 if q >= 80 else (1 if q >= 65 else 2)
                im.save(buf, "JPEG", **kw)
            data = buf.getvalue()
            need = 0.97 if scale < 1.0 or not was_lossy else 0.85     # re-encoding a JPEG must pay off clearly, or it is left alone
            if len(data) >= old_len * need:
                stats["kept"] = stats.get("kept", 0) + 1
                continue
            page0.replace_image(xref, stream=data)
            if sm[0] == "xref":
                doc.xref_set_key(xref, "SMask", sm[1])
            stats["done"] = stats.get("done", 0) + 1
            if scale < 1.0:
                stats["resized"] = stats.get("resized", 0) + 1
        except Cancelled:
            raise
        except Exception as e:
            LOG.warning("image %s not recompressed: %s", xref, type(e).__name__)
            stats["failed"] = stats.get("failed", 0) + 1
    return stats


def _visual_match(src, dst, max_pages=4):
    """Compare how pages LOOK before and after (rendered at 100 dpi).  Returns the lowest PSNR in dB, or None."""
    if not HAVE_NP:
        return None
    try:
        a, b = fitz.open(src), fitz.open(dst)
        try:
            n = min(a.page_count, b.page_count)
            if n < 1 or a.needs_pass or b.needs_pass:
                return None
            idx = sorted(set([0, n // 3, (2 * n) // 3, n - 1]))[:max_pages]
            worst = None
            for i in idx:
                pa = a[i].get_pixmap(dpi=100, colorspace=fitz.csGRAY, alpha=False)
                pb = b[i].get_pixmap(dpi=100, colorspace=fitz.csGRAY, alpha=False)
                if (pa.width, pa.height) != (pb.width, pb.height):
                    return None
                x = np.frombuffer(pa.samples, dtype=np.uint8).astype(np.float32)
                y = np.frombuffer(pb.samples, dtype=np.uint8).astype(np.float32)
                mse = float(((x - y) ** 2).mean())
                ps = 99.0 if mse < 1e-6 else 10.0 * math.log10(255.0 * 255.0 / mse)
                worst = ps if worst is None else min(worst, ps)
            return worst
        finally:
            a.close()
            b.close()
    except Exception:
        return None


def quality_words(psnr):
    if psnr is None:
        return ""
    if psnr >= 60:
        return "identical"
    if psnr >= 40:
        return "excellent - no visible difference"
    if psnr >= 33:
        return "very good"
    if psnr >= 29.5:
        return "good"
    return "reduced - check small print before sending"


def _compress_once(src, tmp, thr, tgt, q, gray, fonts, report, cancelled):
    doc = open_pdf(src)
    note, stats = "", {}
    try:
        if hasattr(doc, "rewrite_images"):                      # lossless: re-pack black-and-white fax pictures only
            try:
                doc.rewrite_images(lossy=False, lossless=False, bitonal=True, color=False, gray=False)
            except Exception as e:
                LOG.warning("bitonal repack skipped: %s", type(e).__name__)
        if q or gray:
            if HAVE_PIL:
                _recompress_images(doc, thr, tgt, q or 90, gray, report, cancelled, stats)
            elif hasattr(doc, "rewrite_images"):
                try:
                    doc.rewrite_images(dpi_threshold=thr or None, dpi_target=tgt, quality=q or 90, bitonal=False, set_to_gray=bool(gray))
                except Exception as e:
                    LOG.warning("rewrite_images failed: %s", e)
                    note = " (picture recompression was not possible for this file)"
            else:
                note = " (Pillow is missing - only lossless optimisation was done)"
        if fonts:
            try:
                doc.subset_fonts()
            except Exception:
                pass
        if report:
            report(72, "Saving...")
        try:
            doc.save(tmp, garbage=4, deflate=True, deflate_images=True, deflate_fonts=True, use_objstms=1)
        except Exception:
            doc.save(tmp, garbage=3, deflate=True)
    finally:
        doc.close()
    return os.path.getsize(tmp), note, stats


def core_compress(src, dst, level="High quality", dpi=None, quality=None, gray=False, report=None, target_bytes=None,
                  cancelled=None, fonts=None, info=None):
    """Returns (original_size, new_size, note).  Writes dst only if the result is smaller.
    target_bytes: try the quality ladder from best to worst and keep the FIRST (= best looking) result that fits."""
    level = COMPRESS_LEVELS.get(level, level)
    orig = os.path.getsize(src)
    info = info if info is not None else {}
    with TempDir() as td:
        tmp = os.path.join(td, "c.pdf")
        if target_bytes:
            best, steps = None, COMPRESS_LADDER
            for k, (thr, tgt, q) in enumerate(steps):
                if cancelled and cancelled():
                    raise Cancelled()
                sub = (lambda p, m, k=k: report(100.0 * k / len(steps) + p / len(steps), "Try %d of %d: %s" % (k + 1, len(steps), m))) if report else None
                t2 = os.path.join(td, "t%d.pdf" % k)
                new, note, stats = _compress_once(src, t2, thr, tgt, q, gray, q and q < 80, sub, cancelled)
                if best is None or new < best[0]:
                    if best:
                        try:
                            os.remove(best[4])
                        except OSError:
                            pass
                    best = (new, note, stats, (thr, tgt, q), t2)
                else:
                    os.remove(t2)
                if new <= target_bytes:
                    break
                if k and not stats.get("seen"):
                    break                                           # no pictures to shrink: lower quality cannot help
            new, note, stats, used, tmp = best
            info["fit"] = new <= target_bytes
            info["used"] = used
        else:
            if level == "Custom" or level not in COMPRESS_PRESETS:
                thr, tgt, q = int((dpi or 150) * 1.2), int(dpi or 150), int(quality or 80)
            else:
                thr, tgt, q = COMPRESS_PRESETS[level]
                if dpi:
                    thr, tgt = int(dpi * 1.2), int(dpi)
                if quality:
                    q = int(quality)
            if fonts is None:
                fonts = level in ("Balanced", "Smallest file")
            new, note, stats = _compress_once(src, tmp, thr, tgt, q, gray, fonts, report, cancelled)
            info["used"] = (thr, tgt, q)
        info["stats"] = stats
        if new < orig:
            if report:
                report(92, "Checking the quality...")
            info["psnr"] = _visual_match(src, tmp) if not gray else None
            shutil.copyfile(tmp, dst)
        return orig, new, note


class CompressTool(ToolPage):
    key, title, group = "compress", "Compress PDF", "Organize"
    subtitle = "Make a PDF smaller while keeping it sharp."

    def build(self, L):
        self.pdf = PdfPicker("compress")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.level = self.combo([(v, k) for k, v in COMPRESS_LABELS.items()])
        self.level.setCurrentIndex(list(COMPRESS_LABELS).index("High quality"))
        self.level.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.level.setMinimumContentsLength(30)
        self.add_row("Quality", self.level)
        self.dpi = self.spin(50, 600, 200, " dpi")
        self.q = self.spin(20, 98, 86, " %")
        L.addWidget(hbox(QLabel("Picture resolution"), self.dpi, QLabel("JPEG quality"), self.q, None))
        self.fit = QCheckBox("Fit under")
        self.mb = QDoubleSpinBox()
        self.mb.setRange(0.05, 2000.0)
        self.mb.setDecimals(2)
        self.mb.setValue(5.0)
        self.mb.setSuffix(" MB")
        self.mb.setEnabled(False)
        self.fit.toggled.connect(self._fit)
        L.addWidget(hbox(self.fit, self.mb, QLabel("(for upload limits)"), None))
        self.add_hint("'Fit under' tries the quality levels from best to smallest and keeps the BEST one that fits the size you type.")
        self.gray = QCheckBox("Convert pictures to grayscale (smaller, loses colour)")
        L.addWidget(self.gray)
        self.add_hint("Text, tables and drawings stay exactly as they are. Logos, charts and black-and-white scans are kept lossless. "
                      "Photos and colour scans are resized only when they hold more detail than the chosen resolution. "
                      "After saving, the program compares the pages before and after and tells you how close they look. "
                      "If the result is not smaller, nothing is saved.")
        self.level.currentIndexChanged.connect(self._lv)
        self._lv()

    def _fit(self, on):
        self.mb.setEnabled(on)
        self.level.setEnabled(not on)
        self._lv()

    def _lv(self, *a):
        lv = self.level.currentData()
        custom = lv == "Custom" and not self.fit.isChecked()
        self.dpi.setEnabled(custom)
        self.q.setEnabled(custom)
        if lv in COMPRESS_PRESETS and lv != "Lossless":
            self.dpi.setValue(COMPRESS_PRESETS[lv][1])
            self.q.setValue(COMPRESS_PRESETS[lv][2])

    def make_task(self, out):
        path = self.pdf.require()
        pdf_page_count(path)
        lv, dpi, q, gray = self.level.currentData(), self.dpi.value(), self.q.value(), self.gray.isChecked()
        target = int(self.mb.value() * 1024 * 1024) if self.fit.isChecked() else None
        if target and os.path.getsize(path) <= target:
            raise UserError("This file is already under %.2f MB (%s)." % (self.mb.value(), human_size(os.path.getsize(path))))
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            dst = unique_path(out, stem + "_compressed", ".pdf")
            info = {}
            if lv == "Custom":
                orig, new, note = core_compress(path, dst, "Custom", dpi, q, gray, report, target, cancelled, info=info)
            else:
                orig, new, note = core_compress(path, dst, lv, None, None, gray, report, target, cancelled, info=info)
            if new >= orig:
                return {"message": "The compressed version (%s) is not smaller than the original (%s), so nothing was saved. "
                                   "Your original file is already well optimised.%s" % (human_size(new), human_size(orig), note),
                        "files": []}
            st = info.get("stats") or {}
            lines = ["Before: %s" % human_size(orig), "After:  %s" % human_size(new), "Saved:  %.1f%%%s" % (100.0 * (orig - new) / orig, note)]
            thr, tgt, qq = info.get("used") or (0, 0, 0)
            if qq:
                rs = ("%d resized to %d dpi, " % (st["resized"], tgt)) if st.get("resized") else ""
                lines.append("Pictures: %d optimised (%sJPEG quality %d), %d left untouched." % (
                    st.get("done", 0), rs, qq, st.get("kept", 0) + st.get("bw", 0)))
            else:
                lines.append("Pictures were not changed (lossless).")
            if info.get("psnr") is not None:
                lines.append("Quality check (pages before / after): %s  [%.1f dB]" % (quality_words(info["psnr"]), info["psnr"]))
            if target:
                lines.append("Fits under %.2f MB: %s" % (target / 1048576.0, "YES" if info.get("fit") else
                             "NO - this is the smallest the file can be made. Try grayscale, or split the file."))
            lines += ["", dst]
            return {"message": "\n".join(lines), "files": [dst]}
        return task


# ---------------------------------------------------------------- page tools
def is_blank_page(page, sens):
    if page_has_text(page):
        return False
    pix = page.get_pixmap(dpi=40, colorspace=fitz.csGRAY, alpha=False)
    s = pix.samples
    dark = len(s.translate(None, bytes(range(200, 256))))
    frac = dark / float(max(1, len(s)))
    return frac <= {1: 0.0005, 2: 0.002, 3: 0.005, 4: 0.01, 5: 0.02}[sens]


def content_rect(page):
    """Bounding box (unrotated page coordinates) of text, images and drawings, or None."""
    rects = []
    for b in page.get_text("blocks"):
        if b[4].strip():
            rects.append(fitz.Rect(b[:4]))
    for im in page.get_image_info():
        rects.append(fitz.Rect(im["bbox"]))
    for d in page.get_drawings():
        r = fitz.Rect(d["rect"])
        if r.width > 0.5 or r.height > 0.5:
            rects.append(r)
    if not rects:
        return None
    u = fitz.Rect(rects[0])
    for r in rects[1:]:
        u |= r
    return u


PAPER = {"A3": (841.89, 1190.55), "A4": (595.28, 841.89), "A5": (419.53, 595.28), "Letter": (612, 792), "Legal": (612, 1008)}
MM = 72 / 25.4


def op_rotate(doc, pages, deg):
    for p in pages:
        doc[p].set_rotation((doc[p].rotation + deg) % 360)
    return doc


def op_nup(src, per, border, report):
    cols, rows = {2: (2, 1), 4: (2, 2), 6: (3, 2), 9: (3, 3)}[per]
    W, H = (841.89, 595.28) if cols > rows else (595.28, 841.89)
    m, gap = 18.0, 8.0
    cw, ch = (W - 2 * m - (cols - 1) * gap) / cols, (H - 2 * m - (rows - 1) * gap) / rows
    new = fitz.open()
    n = src.page_count
    for s in range(0, n, per):
        pg = new.new_page(width=W, height=H)
        for k in range(per):
            i = s + k
            if i >= n:
                break
            r, c = divmod(k, cols)
            rect = fitz.Rect(m + c * (cw + gap), m + r * (ch + gap), m + c * (cw + gap) + cw, m + r * (ch + gap) + ch)
            pg.show_pdf_page(rect, src, i)
            if border:
                pg.draw_rect(rect, color=(0.5, 0.5, 0.5), width=0.5)
        report(5 + 85 * s / n, "Laying out sheet %d" % (s // per + 1))
    return new


def op_booklet(src, report):
    n = src.page_count
    total = ((n + 3) // 4) * 4
    w, h = src[0].rect.width, src[0].rect.height
    new = fitz.open()
    order = []
    for s in range(total // 4):
        order.append((total - 1 - 2 * s, 2 * s))
        order.append((2 * s + 1, total - 2 - 2 * s))
    for k, (l, r) in enumerate(order):
        pg = new.new_page(width=2 * w, height=h)
        for idx, rect in ((l, fitz.Rect(0, 0, w, h)), (r, fitz.Rect(w, 0, 2 * w, h))):
            if idx < n:
                pg.show_pdf_page(rect, src, idx)
        report(5 + 85 * k / len(order), "Sheet side %d of %d" % (k + 1, len(order)))
    return new


def op_page_size(src, target, report):
    tw, th = PAPER[target]
    new = fitz.open()
    n = src.page_count
    for i in range(n):
        r = src[i].rect
        W, H = (th, tw) if r.width > r.height else (tw, th)
        pg = new.new_page(width=W, height=H)
        pg.show_pdf_page(pg.rect, src, i)
        report(5 + 85 * i / n, "Resizing page %d" % (i + 1))
    return new


PAGE_OPS = ["Rotate pages", "Delete pages", "Duplicate pages", "Insert blank pages", "Crop pages",
            "Change page size", "Remove blank pages", "N-up (several pages per sheet)", "Booklet layout"]


class PageToolsTool(ToolPage):
    key, title, group = "pagetools", "Page Tools", "Organize"
    subtitle = "Rotate, delete, duplicate, insert blanks, crop, resize, remove blank pages, N-up and booklet."

    def build(self, L):
        self.pdf = PdfPicker("pagetools")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.op = self.combo(PAGE_OPS)
        self.add_row("What do you want to do?", self.op)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("blank = all pages  |  e.g. 1, 3-5, 8-10")
        self.pages_row = self.add_row("Pages", self.pages)
        self.stack = QStackedWidget()
        L.addWidget(self.stack)
        # 0 rotate
        w = QWidget(); l = QHBoxLayout(w)
        self.rot = self.combo([("90 degrees clockwise", 90), ("180 degrees", 180), ("90 degrees anticlockwise", 270)])
        l.addWidget(QLabel("Rotate by")); l.addWidget(self.rot); l.addStretch(1)
        self.stack.addWidget(w)
        # 1 delete
        w = QWidget(); l = QVBoxLayout(w); l.addWidget(hint_label("The pages you list above will be removed (you must list at least one).")); self.stack.addWidget(w)
        # 2 duplicate
        w = QWidget(); l = QHBoxLayout(w)
        self.copies = self.spin(1, 20, 1)
        l.addWidget(QLabel("Extra copies of each page")); l.addWidget(self.copies); l.addStretch(1); self.stack.addWidget(w)
        # 3 blank
        w = QWidget(); l = QHBoxLayout(w)
        self.after = self.spin(0, 99999, 0)
        self.nblank = self.spin(1, 100, 1)
        self.bsize = self.combo([("Same as neighbouring page", "same"), ("A4", "A4"), ("Letter", "Letter")])
        for x in (QLabel("Insert after page (0 = at start)"), self.after, QLabel("How many"), self.nblank, self.bsize):
            l.addWidget(x)
        l.addStretch(1); self.stack.addWidget(w)
        # 4 crop
        w = QWidget(); g = QGridLayout(w)
        self.cm = [self.dspin(0, 500, 0, " mm", 1) for _ in range(4)]
        for k, lab in enumerate(("Top", "Bottom", "Left", "Right")):
            g.addWidget(QLabel(lab), 0, k * 2); g.addWidget(self.cm[k], 0, k * 2 + 1)
        self.autocrop = QCheckBox("Auto-crop to content, keeping this margin:")
        self.automm = self.dspin(0, 100, 5, " mm", 1)
        g.addWidget(self.autocrop, 1, 0, 1, 3); g.addWidget(self.automm, 1, 3)
        g.addWidget(hint_label("Cropping hides the outside area (the content is not deleted from the file)."), 2, 0, 1, 8)
        self.stack.addWidget(w)
        # 5 page size
        w = QWidget(); l = QHBoxLayout(w)
        self.psize = self.combo(list(PAPER.keys()), "A4")
        l.addWidget(QLabel("Scale every page to")); l.addWidget(self.psize)
        l.addWidget(hint_label("Content is scaled to fit and centred; landscape pages stay landscape. Links and form fields on resized pages are not kept."))
        self.stack.addWidget(w)
        # 6 blank removal
        w = QWidget(); l = QHBoxLayout(w)
        self.sens = self.spin(1, 5, 3)
        l.addWidget(QLabel("Sensitivity (1 = only perfectly white, 5 = also near-empty/noisy scans)")); l.addWidget(self.sens); l.addStretch(1)
        self.stack.addWidget(w)
        # 7 nup
        w = QWidget(); l = QHBoxLayout(w)
        self.nup = self.combo([("2 per sheet", 2), ("4 per sheet", 4), ("6 per sheet", 6), ("9 per sheet", 9)], "4 per sheet")
        self.nborder = QCheckBox("Draw thin border")
        l.addWidget(self.nup); l.addWidget(self.nborder); l.addStretch(1); self.stack.addWidget(w)
        # 8 booklet
        w = QWidget(); l = QVBoxLayout(w)
        l.addWidget(hint_label("Creates landscape sheets so that, printed double-sided (flip on short edge) and folded, "
                               "the pages read in order. Page count is padded to a multiple of 4 with blanks."))
        self.stack.addWidget(w)
        self.op.currentIndexChanged.connect(self._opch)
        self._opch(0)

    def _opch(self, i):
        self.stack.setCurrentIndex(i)
        uses = i in (0, 1, 2, 4, 5 - 5 + 4)  # rotate, delete, duplicate, crop
        self.pages.setEnabled(i in (0, 1, 2, 4))

    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        k = self.op.currentIndex()
        pages = []
        if k in (0, 1, 2, 4):
            pages = pages_from_text(self.pages.text(), n, blank_means_all=(k != 1))
            pages = sorted(set(pages))
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])
        deg, copies = self.rot.currentData(), self.copies.value()
        after, nblank, bsize = self.after.value(), self.nblank.value(), self.bsize.currentData()
        margins = [c.value() * MM for c in self.cm]
        auto, automm = self.autocrop.isChecked(), self.automm.value() * MM
        psize, sens, nup, nborder = self.psize.currentText(), self.sens.value(), self.nup.currentData(), self.nborder.isChecked()
        if k == 3 and after > n:
            raise UserError("'Insert after page' cannot be more than %d." % n)
        tag = ["rotated", "pages_deleted", "duplicated", "with_blanks", "cropped", "resized", "no_blanks", "nup", "booklet"][k]

        def task(report, cancelled):
            src = open_pdf(path)
            msg = ""
            if k == 0:
                doc = op_rotate(src, pages, deg)
            elif k == 1:
                if len(pages) >= src.page_count:
                    raise UserError("You cannot delete every page of the document.")
                src.delete_pages(pages)
                doc = src
            elif k == 2:
                order = []
                for i in range(n):
                    order += [i] * (1 + (copies if i in pages else 0))
                doc = build_from_pages(src, order, report, 5, 85)
            elif k == 3:
                doc = src
                for _ in range(nblank):
                    ref = doc[after - 1] if after > 0 else doc[0]
                    w, h = (ref.rect.width, ref.rect.height) if bsize == "same" else PAPER[bsize]
                    doc.new_page(pno=after, width=w, height=h)
            elif k == 4:
                doc = src
                for j, p in enumerate(pages):
                    pg = doc[p]
                    if auto:
                        cr = content_rect(pg)
                        if cr is None:
                            continue
                        nr = fitz.Rect(cr.x0 - automm, cr.y0 - automm, cr.x1 + automm, cr.y1 + automm) & pg.mediabox
                        nr = fitz.Rect(nr)
                    else:
                        vr = pg.rect
                        t, b, l_, r_ = margins
                        vis = fitz.Rect(vr.x0 + l_, vr.y0 + t, vr.x1 - r_, vr.y1 - b)
                        if vis.is_empty or vis.width < 20 or vis.height < 20:
                            raise UserError("The crop margins are larger than the page.")
                        nr = vis * pg.derotation_matrix
                        nr.normalize()
                    pg.set_cropbox(nr)
                    if j % 10 == 0:
                        report(5 + 85 * j / len(pages), "Cropping page %d" % (p + 1))
            elif k == 5:
                doc = op_page_size(src, psize, report)
            elif k == 6:
                blanks = []
                for i in range(n):
                    if is_blank_page(src[i], sens):
                        blanks.append(i)
                    if i % 10 == 0:
                        report(5 + 80 * i / n, "Checking page %d of %d" % (i + 1, n))
                if not blanks:
                    return {"message": "No blank pages were found at this sensitivity. Nothing was saved.", "files": []}
                if len(blanks) == n:
                    raise UserError("Every page looks blank at this sensitivity. Lower it (e.g. to 1 or 2).")
                msg = "\nRemoved blank pages: %s" % ", ".join(str(b + 1) for b in blanks)
                src.delete_pages(blanks)
                doc = src
            elif k == 7:
                doc = op_nup(src, nup, nborder, report)
            else:
                doc = op_booklet(src, report)
            dst = save_pdf(doc, unique_path(out, "%s_%s" % (stem, tag), ".pdf"))
            return {"message": "Done (%d page(s) in the result).%s\n%s" % (doc.page_count, msg, dst), "files": [dst]}
        return task


class OrganiserTool(ToolPage):
    key, title, group = "organiser", "Page Organiser", "Organize"
    subtitle = "See all pages as thumbnails: drag to reorder, select several, rotate, delete or duplicate, then save."
    action_text = "Save organised PDF"

    def build(self, L):
        self.pdf = PdfPicker("organiser")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        b = QPushButton("Load pages")
        b.clicked.connect(self.load)
        L.addWidget(b)
        self.org = PageOrganiser()
        L.addWidget(self.org)

    def load(self):
        try:
            self.org.load(self.pdf.require())
        except UserError as e:
            self.warn(str(e))

    def make_task(self, out):
        path = self.pdf.require()
        if self.org.src_path != path:
            raise UserError("Click 'Load pages' first (the thumbnails belong to a different file).")
        order = self.org.order()
        if not order:
            raise UserError("The page list is empty - at least one page is needed.")
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            src = open_pdf(path)
            new = build_from_pages(src, [o[0] for o in order], report, 5, 80)
            for i, (_, rot) in enumerate(order):
                if rot:
                    new[i].set_rotation((new[i].rotation + rot) % 360)
            dst = save_pdf(new, unique_path(out, stem + "_organised", ".pdf"))
            return {"message": "Saved %d page(s):\n%s" % (len(order), dst), "files": [dst]}
        return task


# ---------------------------------------------------------------- watermark / stamps
STAMPS = {"APPROVED": "Green", "REJECTED": "Red", "DRAFT": "Blue", "CONFIDENTIAL": "Red", "FOR REVIEW": "Orange",
          "PAID": "Green", "RECEIVED": "Blue", "ORIGINAL": "Black", "COPY": "Gray"}
WM_POS = [("Center", "center"), ("Top left", "tl"), ("Top center", "tc"), ("Top right", "tr"),
          ("Bottom left", "bl"), ("Bottom center", "bc"), ("Bottom right", "br"), ("Tiled across page", "tile")]


def place_overlay(doc, page, png, ow, oh, pos, front, cache):
    """Insert a transparent PNG at a visible position on a page (handles rotated pages)."""
    vr = page.rect
    m = 24
    if pos == "tile":
        cs = []
        sx, sy = ow * 1.5, oh * 2.2
        y = sy / 2
        row = 0
        while y < vr.height + sy:
            x = sx / 2 + (sx / 2 if row % 2 else 0) - sx
            while x < vr.width + sx:
                cs.append((x, y))
                x += sx
            y += sy
            row += 1
    else:
        cx = {"l": m + ow / 2, "c": vr.width / 2, "r": vr.width - m - ow / 2}
        cy = {"t": m + oh / 2, "c": vr.height / 2, "b": vr.height - m - oh / 2}
        if pos == "center":
            cs = [(cx["c"], cy["c"])]
        else:
            cs = [(cx[{"l": "l", "c": "c", "r": "r"}[pos[1]]], cy[{"t": "t", "b": "b"}[pos[0]]])]
    for (x, y) in cs:
        rect = fitz.Rect(x - ow / 2, y - oh / 2, x + ow / 2, y + oh / 2)
        if not rect.intersects(vr):
            continue
        r = rect * page.derotation_matrix
        r.normalize()
        key = (id(doc), ow, oh)
        if key in cache:
            page.insert_image(r, xref=cache[key], rotate=page.rotation, keep_proportion=False, overlay=front)
        else:
            cache[key] = page.insert_image(r, stream=png, rotate=page.rotation, keep_proportion=False, overlay=front)


def image_overlay_png(path, opacity, angle):
    if not HAVE_PIL:
        raise UserError("The Pillow library is missing. Run:  pip install Pillow")
    try:
        im = Image.open(path).convert("RGBA")
    except Exception:
        raise UserError("The watermark image could not be read.")
    if opacity < 1:
        a = im.split()[3].point(lambda v: int(v * opacity))
        im.putalpha(a)
    if angle:
        im = im.rotate(angle, expand=True, resample=Image.BICUBIC)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue(), im.size


class WatermarkTool(ToolPage):
    key, title, group = "watermark", "Watermark & Stamps", "Edit"
    subtitle = "Add a text or image watermark, or a ready-made stamp (APPROVED, DRAFT, CONFIDENTIAL...). Indian scripts supported."

    def build(self, L):
        self.pdf = PdfPicker("watermark")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.kind = self.combo(["Text watermark", "Image watermark", "Stamp"])
        self.add_row("Type", self.kind)
        self.stamp = self.combo(list(STAMPS.keys()) + ["Custom text"])
        self.text = QLineEdit("CONFIDENTIAL")
        self.text_row = hbox(QLabel("Stamp"), self.stamp, QLabel("Text"), self.text)
        L.addWidget(self.text_row)
        self.img = FilePicker("wm_img", IMG_EXT, "Select image", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff)")
        self.img_row = QWidget(); il = QVBoxLayout(self.img_row); il.setContentsMargins(0, 0, 0, 0)
        self.add_row("Watermark image (PNG with transparency works best)", self.img, layout=il)
        L.addWidget(self.img_row)
        self.size = self.spin(8, 400, 60, " pt")
        self.imgscale = self.spin(5, 100, 40, " % of page width")
        self.color = self.combo(list(COLORS.keys()), "Gray")
        self.opacity = self.spin(5, 100, 30, " %")
        self.angle = self.spin(-180, 180, 45, " deg")
        self.pos = self.combo([p[0] for p in WM_POS])
        g = QGridLayout()
        for r, (lab, w) in enumerate((("Font size", self.size), ("Image size", self.imgscale), ("Colour", self.color),
                                      ("Opacity", self.opacity), ("Angle", self.angle), ("Position", self.pos))):
            g.addWidget(QLabel(lab), r // 3, (r % 3) * 2)
            g.addWidget(w, r // 3, (r % 3) * 2 + 1)
        L.addLayout(g)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("blank = all pages")
        self.add_row("Pages", self.pages)
        self.behind = QCheckBox("Place behind the page content (may be hidden by scanned/filled pages)")
        L.addWidget(self.behind)
        self.kind.currentIndexChanged.connect(self._kind)
        self.stamp.currentTextChanged.connect(self._stamp)
        self._kind(0)

    def _kind(self, i):
        self.text_row.setVisible(i in (0, 2))
        self.stamp.setVisible(i == 2)
        self.img_row.setVisible(i == 1)
        self.size.setEnabled(i != 1)
        self.imgscale.setEnabled(i == 1)
        if i == 2:
            self._stamp(self.stamp.currentText())
            self.angle.setValue(20)
            self.opacity.setValue(70)
            self.pos.setCurrentIndex(0)
        elif i == 0:
            self.angle.setValue(45)

    def _stamp(self, s):
        if s in STAMPS:
            self.text.setText(s)
            self.color.setCurrentText(STAMPS[s])
            self.text.setEnabled(False)
        else:
            self.text.setEnabled(True)

    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        pages = pages_from_text(self.pages.text(), n)
        k, pos = self.kind.currentIndex(), WM_POS[self.pos.currentIndex()][1]
        op, ang, front = self.opacity.value() / 100.0, float(self.angle.value()), not self.behind.isChecked()
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])
        if k == 1:
            ip = self.img.path()
            if not ip or not os.path.isfile(ip):
                raise UserError("Choose the watermark image first.")
            png, (iw, ih) = image_overlay_png(ip, op, ang)
            scale = self.imgscale.value() / 100.0
            png_size = None
        else:
            txt = self.text.text().strip()
            if not txt:
                raise UserError("Enter the watermark text.")
            img = render_text_image(txt, self.size.value() * 3, COLORS[self.color.currentText()], op, ang, box=(k == 2))
            png, ow_fixed, oh_fixed = qimage_to_png(img), img.width() / 3.0, img.height() / 3.0

        def task(report, cancelled):
            doc = open_pdf(path)
            cache = {}
            for j, p in enumerate(pages):
                pg = doc[p]
                if k == 1:
                    ow = pg.rect.width * scale
                    oh = ow * ih / float(iw)
                else:
                    ow, oh = ow_fixed, oh_fixed
                place_overlay(doc, pg, png, ow, oh, pos, front, cache)
                if j % 5 == 0:
                    report(5 + 85 * j / len(pages), "Page %d" % (p + 1))
            dst = save_pdf(doc, unique_path(out, stem + "_marked", ".pdf"))
            return {"message": "Watermark/stamp added to %d page(s):\n%s" % (len(pages), dst), "files": [dst]}
        return task


# ---------------------------------------------------------------- header / footer
def expand_tokens(text, page_no, total, docname):
    return (text.replace("{page}", str(page_no)).replace("{total}", str(total))
            .replace("{date}", dt.date.today().strftime("%d-%b-%Y")).replace("{docname}", docname))


def core_header_footer(src, dst, texts, fontsize, margin, color, pages, skip_first, report=None):
    doc = open_pdf(src)
    n = doc.page_count
    name = os.path.splitext(os.path.basename(src))[0]
    for j, p in enumerate(pages):
        if skip_first and p == 0:
            continue
        for where, t in texts.items():
            if t.strip():
                draw_label(doc[p], expand_tokens(t, p + 1, n, name), where, fontsize, margin, color)
        if report and j % 5 == 0:
            report(5 + 85 * j / len(pages), "Page %d" % (p + 1))
    save_pdf(doc, dst)
    doc.close()


class HeaderFooterTool(ToolPage):
    key, title, group = "headerfooter", "Header & Footer", "Edit"
    subtitle = "Put text at the top and bottom of pages. Tokens: {page} {total} {date} {docname}."

    def build(self, L):
        self.pdf = PdfPicker("headerfooter")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        g = QGridLayout()
        self.fields = {}
        for r, (rowname, vert) in enumerate((("Header", "top"), ("Footer", "bottom"))):
            g.addWidget(QLabel(rowname), r + 1, 0)
            for c, h in enumerate(("left", "center", "right")):
                e = QLineEdit()
                e.setPlaceholderText(h)
                self.fields["%s-%s" % (vert, h)] = e
                g.addWidget(e, r + 1, c + 1)
        for c, h in enumerate(("Left", "Center", "Right")):
            g.addWidget(QLabel(h), 0, c + 1)
        self.fields["bottom-center"].setText("Page {page} of {total}")
        self.fields["top-left"].setText("{docname}")
        self.fields["top-right"].setText("{date}")
        L.addLayout(g)
        self.size = self.spin(5, 36, 9, " pt")
        self.margin = self.spin(5, 150, 24, " pt")
        self.color = self.combo(["Black", "Gray", "Blue", "Red"], "Gray")
        self.skip1 = QCheckBox("Skip the first page")
        L.addWidget(hbox(QLabel("Font size"), self.size, QLabel("Distance from edge"), self.margin, QLabel("Colour"), self.color, self.skip1, None))
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("blank = all pages")
        self.add_row("Pages", self.pages)

    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        pages = pages_from_text(self.pages.text(), n)
        texts = {k: e.text() for k, e in self.fields.items()}
        if not any(t.strip() for t in texts.values()):
            raise UserError("Type some header or footer text first.")
        args = (texts, self.size.value(), self.margin.value(), COLORS[self.color.currentText()], pages, self.skip1.isChecked())
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            dst = unique_path(out, stem + "_hf", ".pdf")
            core_header_footer(path, dst, *args, report=report)
            return {"message": "Header/footer added:\n%s" % dst, "files": [dst]}
        return task
# ============================================================================
#  SECTION G - PHASE 2 TOOLS (part 2): viewer, annotations & forms, properties,
#              bookmarks, strip, PDF/A, repair, compare
# ============================================================================
class ViewerTool(ToolPage):
    key, title, group = "viewer", "PDF Reader", "Organize"
    subtitle = "Read PDFs: thumbnails, contents, search, zoom and rotate view."
    needs_output = False
    no_action = True

    def build(self, L):
        self.pdf = PdfPicker("viewer")
        self.add_row("Open a PDF", self.pdf)
        L.addWidget(self.pdf.info)
        self.pdf.changed.connect(self.open_current)
        self.viewer = PdfViewer()
        self.viewer.setMinimumHeight(560)
        L.addWidget(self.viewer)
        self.pw = None

    def open_current(self, *a):
        p = self.pdf.path()
        if not p:
            return
        try:
            self.viewer.load(p)
            SET.add_recent(p)
        except UserError as e:
            self.viewer.close_doc()
            self.warn(str(e))

    def open_file(self, p):
        self.pdf.set_path(p)


# ---------------------------------------------------------------- annotations & forms
ANNOT_KINDS = ["Highlight text in area", "Underline text in area", "Strike-through text in area",
               "Sticky note", "Text box", "Rectangle", "Oval", "Line", "Signature / image"]


class AnnotateTool(ToolPage):
    key, title, group = "annotate", "Annotations & Forms", "Edit"
    subtitle = "Draw an area on the page, then add a highlight, note, text box, shape or signature image. Fill and flatten forms."
    action_text = "Save annotated PDF"

    def build(self, L):
        self.pdf = PdfPicker("annotate")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        b = QPushButton("Open in editor below")
        b.clicked.connect(self.load)
        L.addWidget(b)
        self.tabs = QTabWidget()
        L.addWidget(self.tabs)
        # tab 1: mark up
        t1 = QWidget(); v = QVBoxLayout(t1)
        self.viewer = PdfViewer(select_mode=True, compact=True)
        self.viewer.setMinimumHeight(430)
        self.viewer.rectSelected.connect(self.on_rect)
        v.addWidget(self.viewer)
        self.kind = self.combo(ANNOT_KINDS)
        self.color = self.combo(["Yellow", "Red", "Blue", "Green", "Black", "Orange"])
        self.text = QLineEdit()
        self.text.setPlaceholderText("Text for the note / text box")
        self.sig = FilePicker("sig_img", IMG_EXT, "Select signature image", "Images (*.png *.jpg *.jpeg *.bmp)", "Signature / image file")
        v.addWidget(hbox(QLabel("Tool"), self.kind, QLabel("Colour"), self.color))
        v.addWidget(self.text)
        v.addWidget(self.sig)
        v.addWidget(hint_label("1) choose a tool  2) drag a rectangle on the page  3) repeat  4) Save. "
                               "Items are listed below and can be removed before saving."))
        self.pending = QListWidget()
        self.pending.setMaximumHeight(110)
        rm = QPushButton("Remove selected item")
        rm.clicked.connect(self.remove_item)
        v.addWidget(self.pending)
        v.addWidget(rm)
        self.terms = QPlainTextEdit()
        self.terms.setPlaceholderText("Optional: words/phrases to highlight everywhere (one per line)")
        self.terms.setMaximumHeight(70)
        self.term_kind = self.combo(["Highlight", "Underline", "Strike-through", "Squiggly"])
        v.addWidget(self.terms)
        v.addWidget(hbox(QLabel("Mark the words above with"), self.term_kind, None))
        self.tabs.addTab(t1, "Mark up")
        # tab 2: forms
        t2 = QWidget(); v2 = QVBoxLayout(t2)
        lb = QPushButton("Load form fields")
        lb.clicked.connect(self.load_fields)
        v2.addWidget(lb)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Page", "Field", "Type", "Value (edit)"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(200)
        v2.addWidget(self.table)
        self.flat_f = QCheckBox("Flatten form fields (make the filled values permanent and non-editable)")
        self.flat_a = QCheckBox("Also flatten annotations (comments, highlights)")
        v2.addWidget(self.flat_f)
        v2.addWidget(self.flat_a)
        self.tabs.addTab(t2, "Fill & flatten forms")
        self.items = []          # (page, rect, kind, text, color_name, sig_path)

    # --- UI actions
    def load(self):
        try:
            p = self.pdf.require()
            self.viewer.load(p)
            self.items = []
            self.pending.clear()
        except UserError as e:
            self.warn(str(e))

    def on_rect(self, pg, rect):
        k = self.kind.currentIndex()
        txt = self.text.text().strip()
        if k in (3, 4) and not txt:
            self.warn("Type the note / text first, then draw the area.")
            return
        sig = self.sig.path()
        if k == 8 and (not sig or not os.path.isfile(sig)):
            self.warn("Choose the signature / image file first.")
            return
        item = (pg, fitz.Rect(rect), k, txt, self.color.currentText(), sig)
        self.items.append(item)
        self.pending.addItem("Page %d - %s %s" % (pg + 1, ANNOT_KINDS[k], txt[:30]))
        self._ov()

    def remove_item(self):
        r = self.pending.currentRow()
        if r >= 0:
            self.pending.takeItem(r)
            self.items.pop(r)
            self._ov()

    def _ov(self):
        m = {}
        for pg, r, k, t, c, s in self.items:
            m.setdefault(pg, []).append((r, {"Yellow": "#e0b800", "Red": "#d62839", "Blue": "#1f4fbf", "Green": "#1a8a3a",
                                             "Black": "#000000", "Orange": "#e07000"}[c]))
        self.viewer.set_overlays(m)

    def load_fields(self):
        try:
            doc = open_pdf(self.pdf.require())
        except UserError as e:
            self.warn(str(e))
            return
        self.table.setRowCount(0)
        for pg in doc:
            for w in (pg.widgets() or []):
                r = self.table.rowCount()
                self.table.insertRow(r)
                for c, v in enumerate((str(pg.number + 1), w.field_name, w.field_type_string, str(w.field_value if w.field_value is not None else ""))):
                    it = QTableWidgetItem(v)
                    if c < 3:
                        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                    self.table.setItem(r, c, it)
        doc.close()
        if self.table.rowCount() == 0:
            QMessageBox.information(self, APP_NAME, "This PDF has no fillable form fields.")

    def make_task(self, out):
        path = self.pdf.require()
        pdf_page_count(path)
        items = list(self.items)
        terms = [t.strip() for t in self.terms.toPlainText().splitlines() if t.strip()]
        tkind = self.term_kind.currentIndex()
        fields = {}
        for r in range(self.table.rowCount()):
            fields[(int(self.table.item(r, 0).text()) - 1, self.table.item(r, 1).text())] = (self.table.item(r, 2).text(), self.table.item(r, 3).text())
        flat_f, flat_a = self.flat_f.isChecked(), self.flat_a.isChecked()
        if not (items or terms or fields or flat_a or flat_f):
            raise UserError("Nothing to do: add an annotation, words to mark, form values or choose flattening.")
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])
        # text-box images for non-Latin text are rendered here (GUI thread)
        imgs = {}
        for idx, (pg, r, k, t, c, s) in enumerate(items):
            if k == 4 and (script_of(t) or not is_latin1(t)):
                im = render_text_image(t, 40, COLORS[c], 1.0, 0, bold=False)
                imgs[idx] = qimage_to_png(im)
        cols = {"Yellow": (1, 0.9, 0), "Red": (0.85, 0.1, 0.15), "Blue": (0.1, 0.3, 0.8), "Green": (0.1, 0.6, 0.2),
                "Black": (0, 0, 0), "Orange": (1, 0.55, 0)}

        def task(report, cancelled):
            doc = open_pdf(path)
            nA = 0
            for idx, (pg, r, k, t, c, s) in enumerate(items):
                page = doc[pg]
                col = cols[c]
                if k in (0, 1, 2):
                    fn = (page.add_highlight_annot, page.add_underline_annot, page.add_strikeout_annot)[k]
                    try:
                        a = fn(clip=r)
                    except Exception:
                        a = None
                    if a is None:
                        a = fn(quads=[r.quad] if hasattr(r, "quad") else r)
                    a.set_colors(stroke=col)
                    a.update()
                elif k == 3:
                    a = page.add_text_annot(r.tl, t)
                    a.set_colors(stroke=col)
                    a.update()
                elif k == 4:
                    if idx in imgs:
                        page.insert_image(r, stream=imgs[idx], rotate=page.rotation, keep_proportion=True)
                    else:
                        a = page.add_freetext_annot(r, t, fontsize=11, text_color=col, fill_color=(1, 1, 0.85), border_color=col)
                        a.update()
                elif k == 5:
                    a = page.add_rect_annot(r); a.set_colors(stroke=col); a.set_border(width=1.5); a.update()
                elif k == 6:
                    a = page.add_circle_annot(r); a.set_colors(stroke=col); a.set_border(width=1.5); a.update()
                elif k == 7:
                    a = page.add_line_annot(r.tl, r.br); a.set_colors(stroke=col); a.set_border(width=1.5); a.update()
                elif k == 8:
                    page.insert_image(r, filename=s, rotate=page.rotation, keep_proportion=True)
                nA += 1
            report(30, "Marking words...")
            fn_name = ("add_highlight_annot", "add_underline_annot", "add_strikeout_annot", "add_squiggly_annot")[tkind]
            nT = 0
            for t in terms:
                for page in doc:
                    for q in page.search_for(t, quads=True):
                        a = getattr(page, fn_name)(q)
                        a.update()
                        nT += 1
            report(55, "Filling forms...")
            nF = 0
            if fields:
                for page in doc:
                    for w in (page.widgets() or []):
                        key = (page.number, w.field_name)
                        if key in fields:
                            ftype, val = fields[key]
                            old = str(w.field_value if w.field_value is not None else "")
                            if val == old:
                                continue
                            if ftype in ("CheckBox",):
                                w.field_value = val.strip().lower() in ("true", "yes", "on", "1", "x")
                            else:
                                w.field_value = val
                            w.update()
                            nF += 1
            if flat_f or flat_a:
                report(80, "Flattening...")
                doc.bake(annots=bool(flat_a), widgets=bool(flat_f))
            dst = save_pdf(doc, unique_path(out, stem + "_annotated", ".pdf"))
            return {"message": "Saved. Annotations: %d, marked words: %d, form values changed: %d.\n%s" % (nA, nT, nF, dst), "files": [dst]}
        return task


# ============================================================================
#  EDIT PDF - ENGINE (no GUI code: every function takes a PyMuPDF document)
#  All coordinates are in UNROTATED page space unless a name starts with "v" (visible / as seen on screen).
# ============================================================================
_SUBSET_RE = re.compile(r"^[A-Z]{6}\+")
_ED_TXT_FLAGS = fitz.TEXTFLAGS_TEXT & ~fitz.TEXT_PRESERVE_LIGATURES
_BASE14 = {("sans", 0, 0): "helv", ("sans", 1, 0): "hebo", ("sans", 0, 1): "heit", ("sans", 1, 1): "hebi",
           ("serif", 0, 0): "tiro", ("serif", 1, 0): "tibo", ("serif", 0, 1): "tiit", ("serif", 1, 1): "tibi",
           ("mono", 0, 0): "cour", ("mono", 1, 0): "cobo", ("mono", 0, 1): "coit", ("mono", 1, 1): "cobi"}
_CSS_FAMILY = {"sans": "sans-serif", "serif": "serif", "mono": "monospace"}
_FAMILY_LABEL = {"sans": "Helvetica", "serif": "Times", "mono": "Courier"}


def _rgb_from_int(c):
    c = int(c)
    return (((c >> 16) & 255) / 255.0, ((c >> 8) & 255) / 255.0, (c & 255) / 255.0)


def style_from_span(span):
    """Text style detected from a PyMuPDF span dict."""
    name = span.get("font", "") or ""
    low = name.lower()
    flags = int(span.get("flags", 0))
    bold = bool(flags & 16) or any(k in low for k in ("bold", "black", "heavy", "demi"))
    italic = bool(flags & 2) or any(k in low for k in ("italic", "oblique"))
    if flags & 8 or any(k in low for k in ("courier", "mono", "consol", "typewriter")):
        fam = "mono"
    elif any(k in low for k in ("sans", "arial", "helvet", "calibri", "verdana", "tahoma", "segoe", "roboto", "gothic", "nirmala")):
        fam = "sans"
    elif flags & 4 or any(k in low for k in ("times", "serif", "georgia", "garamond", "cambria", "minion", "palatino", "roman")):
        fam = "serif"
    else:
        fam = "sans"
    return {"font": "auto", "fontfile": "", "family": fam, "bold": bold, "italic": italic, "orig_bold": bold,
            "orig_italic": italic, "font_name": name, "size": round(float(span.get("size", 11.0)), 1),
            "color": _rgb_from_int(span.get("color", 0)), "align": 0, "fit": True}


def default_style():
    return {"font": "auto", "fontfile": "", "family": "sans", "bold": False, "italic": False, "orig_bold": False,
            "orig_italic": False, "font_name": "", "size": 12.0, "color": (0, 0, 0), "align": 0, "fit": True}


def _dir_to_rot(d):
    dx, dy = d
    if abs(dx) >= abs(dy):
        return 0 if dx > 0 else 180
    return 90 if dy < 0 else 270


def _mk_text_item(bbox, text, spans, direction, pitch, unit):
    main = max(spans, key=lambda s: len(s.get("text", "")))
    first = spans[0]
    return {"kind": "text", "rect": fitz.Rect(bbox), "text": text, "style": style_from_span(main),
            "origin": fitz.Point(first.get("origin", (bbox[0], bbox[3]))), "rot": _dir_to_rot(direction),
            "pitch": pitch, "unit": unit}


def page_text_items(page, unit="line"):
    """Editable text units of a page: 'line' = one visual line, 'para' = one text block (paragraph)."""
    d = page.get_text("dict", flags=_ED_TXT_FLAGS)
    out = []
    for b in d.get("blocks", []):
        if b.get("type", 0) != 0:
            continue
        lines = []
        for ln in b.get("lines", []):
            spans = [s for s in ln.get("spans", []) if s.get("text", "") != ""]
            txt = "".join(s["text"] for s in spans)
            if txt.strip():
                lines.append((ln, spans, txt.rstrip()))
        if not lines:
            continue
        if unit == "line":
            for ln, spans, txt in lines:
                out.append(_mk_text_item(ln["bbox"], txt, spans, ln.get("dir", (1, 0)), None, "line"))
        else:
            allspans = [s for _l, sp, _t in lines for s in sp]
            pitch = None
            if len(lines) > 1:
                a, c = lines[0][1][0].get("origin"), lines[1][1][0].get("origin")
                if a and c:
                    pitch = math.hypot(c[0] - a[0], c[1] - a[1]) or None
            msize = float(max(allspans, key=lambda s: len(s.get("text", ""))).get("size", 11))
            if pitch and not (msize * 0.8 <= pitch <= msize * 2.6):     # fragmented lines (Indic scripts) give nonsense pitches
                pitch = None
            out.append(_mk_text_item(b["bbox"], "\n".join(t for _l, _s, t in lines), allspans,
                                     lines[0][0].get("dir", (1, 0)), pitch, "para"))
    return out


def page_edit_items(page, unit="line"):
    """Everything on a page that can be selected: text, images, annotations, links."""
    items = page_text_items(page, unit)
    try:
        for im in page.get_image_info(xrefs=True):
            r = fitz.Rect(im["bbox"])
            if r.width > 1 and r.height > 1:
                items.append({"kind": "image", "rect": r, "xref": int(im.get("xref", 0) or 0)})
    except Exception:
        pass
    try:
        for a in (page.annots() or []):
            if a.type[0] == fitz.PDF_ANNOT_LINK:
                continue
            items.append({"kind": "annot", "rect": fitz.Rect(a.rect), "xref": a.xref, "type": a.type[1]})
    except Exception:
        pass
    try:
        for lk in page.get_links():
            items.append({"kind": "link", "rect": fitz.Rect(lk["from"]), "link": lk})
    except Exception:
        pass
    return items


def pick_item(items, pt):
    """Item under the point: text first, then annotation, image, link (smallest area wins inside a class)."""
    order = {"text": 0, "annot": 1, "image": 2, "link": 3}
    best = None
    for it in items:
        if it["rect"].contains(pt):
            key = (order[it["kind"]], it["rect"].width * it["rect"].height)
            if best is None or key < best[0]:
                best = (key, it)
    return best[1] if best else None


# ---------------------------------------------------------------- fonts
def _cp1252_ok(text):
    try:
        text.encode("cp1252")
        return True
    except UnicodeEncodeError:
        return False


def _norm_font(n):
    return re.sub(r"[^a-z0-9]", "", _SUBSET_RE.sub("", n or "").lower())


def _embedded_font(doc, page, fontname):
    """Font program of the original text (bytes) or None (base-14 fonts and Type3 have none)."""
    want = _norm_font(fontname)
    if not want:
        return None
    best = None
    try:
        for f in page.get_fonts(full=True):
            cand = _norm_font(f[3])
            if cand == want:
                score = 0
            elif want in cand and len(cand) - len(want) <= 10:
                score = len(cand) - len(want)
            else:
                continue
            if best is None or score < best[0]:
                best = (score, f)
        if best and best[1][1] in ("ttf", "otf", "cff", "ttc"):
            res = doc.extract_font(best[1][0])
            if res and res[3]:
                return res[3]
    except Exception:
        pass
    return None


_FONT_INDEX = {}
_UNI_FILES = {
    "sans": [["arial.ttf", "LiberationSans-Regular.ttf", "DejaVuSans.ttf", "NotoSans-Regular.ttf"],
             ["arialbd.ttf", "LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf", "NotoSans-Bold.ttf"],
             ["ariali.ttf", "LiberationSans-Italic.ttf", "DejaVuSans-Oblique.ttf", "NotoSans-Italic.ttf"],
             ["arialbi.ttf", "LiberationSans-BoldItalic.ttf", "DejaVuSans-BoldOblique.ttf", "NotoSans-BoldItalic.ttf"]],
    "serif": [["times.ttf", "LiberationSerif-Regular.ttf", "DejaVuSerif.ttf", "NotoSerif-Regular.ttf"],
              ["timesbd.ttf", "LiberationSerif-Bold.ttf", "DejaVuSerif-Bold.ttf", "NotoSerif-Bold.ttf"],
              ["timesi.ttf", "LiberationSerif-Italic.ttf", "DejaVuSerif-Italic.ttf", "NotoSerif-Italic.ttf"],
              ["timesbi.ttf", "LiberationSerif-BoldItalic.ttf", "DejaVuSerif-BoldItalic.ttf", "NotoSerif-BoldItalic.ttf"]],
    "mono": [["cour.ttf", "LiberationMono-Regular.ttf", "DejaVuSansMono.ttf"],
             ["courbd.ttf", "LiberationMono-Bold.ttf", "DejaVuSansMono-Bold.ttf"],
             ["couri.ttf", "LiberationMono-Italic.ttf", "DejaVuSansMono-Oblique.ttf"],
             ["courbi.ttf", "LiberationMono-BoldItalic.ttf", "DejaVuSansMono-BoldOblique.ttf"]]}


def _font_index():
    """lower-case file name -> path over the program's fonts folder, the config fonts folder and the system fonts."""
    if not _FONT_INDEX:
        for d in _font_dirs():
            if os.path.isdir(d):
                for root, _dirs, files in os.walk(d):
                    for f in files:
                        if f.lower().endswith((".ttf", ".otf")):
                            _FONT_INDEX.setdefault(f.lower(), os.path.join(root, f))
        _FONT_INDEX["_done"] = ""
    return _FONT_INDEX


def _unicode_font(fam, bold, italic, text):
    """A real font file that can draw `text` (curly quotes, euro, rupee ...) in the wanted style, or None."""
    idx = _font_index()
    for name in _UNI_FILES[fam][int(bold) + 2 * int(italic)]:
        p = idx.get(name.lower())
        if p:
            try:
                if _covers(fitz.Font(fontfile=p), text):
                    return p
            except Exception:
                pass
    return find_font(None)


def _covers(fobj, text):
    try:
        return all(c.isspace() or fobj.has_glyph(ord(c)) for c in text)
    except Exception:
        return False


def _pick_font(doc, page, st, text):
    """Decide how to draw `text`. Returns dict(kind=base14|buf|file|generic, ...,  label)."""
    choice = st.get("font", "auto")
    bold, italic = bool(st.get("bold")), bool(st.get("italic"))
    fam = st.get("family", "sans")
    script = script_of(text)
    wide = bool(script) or not is_latin1(text)
    if choice == "file" and st.get("fontfile") and os.path.isfile(st["fontfile"]):
        return {"kind": "file", "file": st["fontfile"], "label": os.path.basename(st["fontfile"]), "family": fam}
    if choice in ("sans", "serif", "mono"):
        fam = choice
    if choice == "auto" and bold == st.get("orig_bold", bold) and italic == st.get("orig_italic", italic):
        buf = _embedded_font(doc, page, st.get("font_name", ""))
        if buf:
            try:
                fo = fitz.Font(fontbuffer=buf)
                if _covers(fo, text):
                    return {"kind": "buf", "buf": buf, "font": fo, "label": _SUBSET_RE.sub("", st.get("font_name", "")),
                            "family": fam}
            except Exception:
                pass
    if wide or choice == "unicode":
        ff = find_font(script) if script else _unicode_font(fam, bold, italic, text)
        if ff:
            return {"kind": "file", "file": ff, "label": os.path.basename(ff), "family": fam}
        return {"kind": "generic", "label": "built-in fallback font", "family": fam,
                "missing": script or "non-Latin"}
    return {"kind": "base14", "name": _BASE14[(fam, int(bold), int(italic))], "label": _FAMILY_LABEL[fam], "family": fam}


def _html_escape(s):
    import html as _h
    return _h.escape(s, quote=False)


def _to_html(text):
    out = []
    for ln in text.split("\n"):
        e = _html_escape(ln).replace("  ", " &nbsp;").replace("\t", " &nbsp;&nbsp;&nbsp;")
        if e.startswith(" "):
            e = "&nbsp;" + e[1:]
        out.append('<p style="margin:0;padding:0">%s</p>' % (e or "&nbsp;"))
    return "".join(out)


def _write_html(page, rect, text, st, fp, rot, pitch, grow=True):
    """Draw (possibly multi-line, shaped) text in `rect` with the HTML engine. Returns list of notes."""
    notes = []
    size = float(st["size"])
    col = st["color"]
    align = ("left", "center", "right", "justify")[int(st.get("align", 0)) % 4]
    css = "body{margin:0;padding:0;font-size:%.2fpt;color:rgb(%d,%d,%d);text-align:%s;line-height:%s;" % (
        size, round(col[0] * 255), round(col[1] * 255), round(col[2] * 255), align,
        ("%.2fpt" % pitch) if pitch else "1.2")
    arch = None
    if fp["kind"] in ("buf", "file"):
        data = fp["buf"] if fp["kind"] == "buf" else open(fp["file"], "rb").read()
        arch = fitz.Archive()
        arch.add(data, "edfont.ttf")
        css = "@font-face{font-family:edf;src:url(edfont.ttf);}" + css + "font-family:edf;}"
    else:
        css += "font-family:%s;" % _CSS_FAMILY.get(fp.get("family", "sans"), "sans-serif")
        if st.get("bold"):
            css += "font-weight:bold;"
        if st.get("italic"):
            css += "font-style:italic;"
        css += "}"
    html = _to_html(text)
    low = 0.6 if st.get("fit", True) else 1.0
    spare, scale = page.insert_htmlbox(rect, html, css=css, archive=arch, rotate=rot, scale_low=low)
    if spare < 0 and grow and rot == 0 and page.rotation == 0:
        r2 = fitz.Rect(rect.x0, rect.y0, rect.x1, max(rect.y1, page.rect.y1 - 18))
        spare, scale = page.insert_htmlbox(r2, html, css=css, archive=arch, rotate=rot, scale_low=1.0)
        if spare >= 0:
            notes.append("The new text is longer than the old space, so it extends further down the page.")
    if spare < 0:
        raise UserError("The new text does not fit in the box. Make the box bigger (Paragraph unit) or use less text.")
    if scale < 0.98:
        notes.append("Text was reduced to %d%% to fit." % round(scale * 100))
    return notes


def _write_text(doc, page, rect, text, st, origin, rot, pitch, force_html, fp=None):
    """Write text at `origin` (single line, exact baseline) or reflowed inside `rect`. Returns notes.
    `fp` = font choice made BEFORE the old text was removed (removing it can drop the font from the page)."""
    fp = fp or _pick_font(doc, page, st, text)
    notes = ["Font used: %s" % fp["label"]]
    if fp.get("missing"):
        notes.append("No font file for %s text was found - put a Noto font in the 'fonts' folder next to the program." % fp["missing"])
    size = float(st["size"])
    multi = ("\n" in text.strip("\n")) or force_html
    direct = (not multi and origin is not None and fp["kind"] in ("base14", "buf", "file")
              and not script_of(text) and int(st.get("align", 0)) == 0)
    if not direct:
        return notes + _write_html(page, rect, text, st, fp, rot, pitch)
    if fp["kind"] == "base14":
        name = fp["name"]
        width = fitz.get_text_length(text, name, size)
    else:
        fo = fp.get("font") or fitz.Font(fontfile=fp["file"])
        name = "ed%x" % (abs(hash(fp["label"])) % 0xFFFFFF)
        if fp["kind"] == "buf":
            page.insert_font(fontname=name, fontbuffer=fp["buf"])
        else:
            page.insert_font(fontname=name, fontfile=fp["file"])
        width = fo.text_length(text, size)
    if st.get("fit", True) and rect.width > 4:
        avail = rect.width if rot in (0, 180) else rect.height
        if width > avail * 1.005:
            new = max(size * 0.6, size * avail / width)
            notes.append("Text was reduced to %d%% to keep the original width." % round(100 * new / size))
            size = new
    page.insert_text(fitz.Point(origin), text, fontsize=size, fontname=name, color=tuple(st["color"]), rotate=rot)
    return notes


_LINK_KEYS = ("kind", "from", "uri", "page", "to", "zoom", "file", "name")


def _links_snapshot(page):
    try:
        return [dict(l) for l in page.get_links()]
    except Exception:
        return []


def _links_restore(page, saved):
    """Redaction deletes links that touch the redacted area; put back the ones that vanished."""
    try:
        now = set((fitz.Rect(l["from"]).irect, l.get("uri"), l.get("page")) for l in page.get_links())
        for l in saved:
            if (fitz.Rect(l["from"]).irect, l.get("uri"), l.get("page")) not in now:
                page.insert_link({k: l[k] for k in _LINK_KEYS if k in l})
    except Exception:
        pass


def _remove_text(page, rect, size, rot=0):
    """True removal of the text characters inside rect (images and graphics are left alone)."""
    r = fitz.Rect(rect)
    pad = max(0.5, min(size * 0.28, (r.height if rot in (0, 180) else r.width) * 0.3))
    if rot in (0, 180):
        r = fitz.Rect(r.x0 - 0.5, r.y0 + pad, r.x1 + 0.5, r.y1 - pad)
    else:
        r = fitz.Rect(r.x0 + pad, r.y0 - 0.5, r.x1 - pad, r.y1 + 0.5)
    if r.is_empty:
        r = fitz.Rect(rect)
    saved = _links_snapshot(page)
    page.add_redact_annot(r, fill=False)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                          text=fitz.PDF_REDACT_TEXT_REMOVE)
    _links_restore(page, saved)


def ed_replace_text(doc, pno, rect, text, st, dest=None, origin=None, rot=0, pitch=None, para=False, remove=True):
    """Replace (or, with empty text, delete / move) the text in `rect`. Returns notes."""
    page = doc[pno]
    rect = fitz.Rect(rect)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    fp = _pick_font(doc, page, st, text) if text.strip() else None
    if remove:
        _remove_text(page, rect, float(st["size"]), rot)
    notes = []
    if text.strip():
        notes = _write_text(doc, page, fitz.Rect(dest or rect), text, st, origin, rot, pitch, para, fp)
    return notes


def ed_add_text(doc, pno, vrect, text, st, fill=None):
    """New text box. vrect is the box AS SEEN on screen; the text always reads upright."""
    page = doc[pno]
    rect = fitz.Rect(fitz.Rect(vrect) * page.derotation_matrix).normalize()
    if fill:
        page.draw_rect(rect, color=None, fill=fill, overlay=True)
    return _write_text(doc, page, rect, text.replace("\r\n", "\n"), st, None, page.rotation % 360, None, True)


# ---------------------------------------------------------------- images
def ed_add_image(doc, pno, vrect, path):
    page = doc[pno]
    rect = fitz.Rect(fitz.Rect(vrect) * page.derotation_matrix).normalize()
    page.insert_image(rect, filename=path, keep_proportion=True, rotate=page.rotation, overlay=True)


def _image_pixmap(doc, xref):
    pix = fitz.Pixmap(doc, xref)
    if pix.colorspace is not None and pix.colorspace.n >= 4:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    info = doc.extract_image(xref) or {}
    sm = int(info.get("smask", 0) or 0)
    if sm:
        try:
            pix = fitz.Pixmap(pix, fitz.Pixmap(doc, sm))
        except Exception:
            pass
    return pix, info


def _remove_image(doc, page, bbox, xref):
    """Take one image off THIS page. Uses a page-local method when no other image overlaps it."""
    bbox = fitz.Rect(bbox)
    others = 0
    try:
        for im in page.get_image_info(xrefs=True):
            r = fitz.Rect(im["bbox"])
            if r.intersects(bbox) and not (int(im.get("xref", 0) or 0) == xref and abs(r.x0 - bbox.x0) < 0.5
                                           and abs(r.y0 - bbox.y0) < 0.5):
                others += 1
    except Exception:
        pass
    if not others or not xref:
        r = fitz.Rect(bbox.x0 + 0.5, bbox.y0 + 0.5, bbox.x1 - 0.5, bbox.y1 - 0.5)
        saved = _links_snapshot(page)
        page.add_redact_annot(r, fill=False)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE, graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                              text=fitz.PDF_REDACT_TEXT_NONE)
        _links_restore(page, saved)
        return ""
    page.delete_image(xref)
    return "This picture overlapped others, so it was removed everywhere it is used in the file."


def ed_delete_image(doc, pno, bbox, xref):
    return _remove_image(doc, doc[pno], bbox, xref)


def ed_move_image(doc, pno, bbox, xref, new_rect):
    """Move / resize a picture: remember it, take it off the page, draw it again at new_rect."""
    page = doc[pno]
    if not xref:
        raise UserError("This picture is stored inline in the page and cannot be moved. You can delete it and add it again.")
    pix, info = _image_pixmap(doc, xref)
    data = info.get("image") if (info and not info.get("smask") and info.get("ext") in ("jpeg", "jpg", "png")) else None
    note = _remove_image(doc, page, bbox, xref)
    kw = dict(keep_proportion=False, rotate=page.rotation, overlay=True)
    if data:
        page.insert_image(fitz.Rect(new_rect), stream=data, **kw)
    else:
        page.insert_image(fitz.Rect(new_rect), pixmap=pix, **kw)
    return note


def ed_replace_image(doc, pno, bbox, xref, path):
    page = doc[pno]
    note = _remove_image(doc, page, bbox, xref)
    page.insert_image(fitz.Rect(bbox), filename=path, keep_proportion=True, rotate=page.rotation, overlay=True)
    return note


# ---------------------------------------------------------------- shapes, cover, links, annotations
def ed_shape(doc, pno, kind, vp0, vp1, color, fill, width):
    """Rectangle / oval / line / arrow drawn between two points AS SEEN on screen."""
    page = doc[pno]
    inv = page.derotation_matrix
    p0, p1 = fitz.Point(vp0), fitz.Point(vp1)
    sh = page.new_shape()
    if kind in ("rect", "oval"):
        r = fitz.Rect(fitz.Rect(p0, p1) * inv).normalize()
        (sh.draw_rect if kind == "rect" else sh.draw_oval)(r)
    else:
        sh.draw_line(p0 * inv, p1 * inv)
        if kind == "arrow":
            vx, vy = p1.x - p0.x, p1.y - p0.y
            ln = math.hypot(vx, vy) or 1.0
            ux, uy = vx / ln, vy / ln
            head = min(max(8.0, width * 4.5), ln * 0.45)
            for ang in (math.radians(25), -math.radians(25)):
                c, s = math.cos(ang), math.sin(ang)
                hx, hy = ux * c - uy * s, ux * s + uy * c
                sh.draw_line(p1 * inv, fitz.Point(p1.x - hx * head, p1.y - hy * head) * inv)
    sh.finish(color=color, fill=fill if kind in ("rect", "oval") else None, width=width, closePath=False,
              lineCap=1, lineJoin=1)
    sh.commit(overlay=True)


def _sample_bg(page, rect):
    """Most common colour just outside rect (so a white-out blends with a coloured background)."""
    vr = fitz.Rect(rect) * page.rotation_matrix
    pix = page.get_pixmap(dpi=72, alpha=False)
    if pix.n < 3:
        return (1, 1, 1)
    votes = {}
    pts = []
    for k in range(0, 40):
        t = k / 39.0
        for (x, y) in ((vr.x0 + t * vr.width, vr.y0 - 2), (vr.x0 + t * vr.width, vr.y1 + 2),
                       (vr.x0 - 2, vr.y0 + t * vr.height), (vr.x1 + 2, vr.y0 + t * vr.height)):
            pts.append((int(x), int(y)))
    for x, y in pts:
        if 0 <= x < pix.width and 0 <= y < pix.height:
            px = pix.pixel(x, y)[:3]
            key = tuple(v // 8 * 8 for v in px)
            votes[key] = votes.get(key, 0) + 1
    if not votes:
        return (1, 1, 1)
    best = max(votes, key=votes.get)
    return tuple(min(255, v + 4) / 255.0 for v in best)


def ed_cover(doc, pno, vrect, color=None, remove_under=True):
    """White-out. With remove_under the text/picture pixels below are really deleted, not just hidden."""
    page = doc[pno]
    rect = fitz.Rect(fitz.Rect(vrect) * page.derotation_matrix).normalize()
    col = tuple(color) if color else _sample_bg(page, rect)
    if remove_under:
        page.add_redact_annot(rect, fill=col)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS, graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                              text=fitz.PDF_REDACT_TEXT_REMOVE)
    else:
        page.draw_rect(rect, color=None, fill=col, overlay=True)
    return col


def ed_add_link(doc, pno, vrect, kind, target):
    page = doc[pno]
    rect = fitz.Rect(fitz.Rect(vrect) * page.derotation_matrix).normalize()
    if kind == "uri":
        page.insert_link({"kind": fitz.LINK_URI, "from": rect, "uri": target})
    else:
        n = int(target)
        if n < 1 or n > doc.page_count:
            raise UserError("There is no page %d in this PDF." % n)
        page.insert_link({"kind": fitz.LINK_GOTO, "from": rect, "page": n - 1, "to": fitz.Point(36, 36), "zoom": 0})


def _find_link(page, rect):
    for lk in page.get_links():
        if fitz.Rect(lk["from"]).irect == fitz.Rect(rect).irect:
            return lk
    raise UserError("That link was not found any more.")


def ed_delete_link(doc, pno, rect):
    page = doc[pno]
    page.delete_link(_find_link(page, rect))


def ed_update_link(doc, pno, rect, kind, target):
    page = doc[pno]
    lk = _find_link(page, rect)
    page.delete_link(lk)
    ed_add_link(doc, pno, fitz.Rect(rect) * page.rotation_matrix, kind, target)


def ed_delete_annot(doc, pno, xref):
    page = doc[pno]
    for a in (page.annots() or []):
        if a.xref == xref:
            page.delete_annot(a)
            return
    raise UserError("That annotation was not found any more.")


# ---------------------------------------------------------------- find / replace
def _scan_lines(page, find, case, whole):
    """Lines that contain the search text: dict(txt, chars, matches=[(a, b)], rect, origin, rot, style, uniform)."""
    flags = 0 if case else re.I
    pat = re.escape(find)
    if whole:
        pat = r"(?<!\w)" + pat + r"(?!\w)"
    rx = re.compile(pat, flags)
    d = page.get_text("rawdict", flags=_ED_TXT_FLAGS)
    out = []
    for b in d.get("blocks", []):
        if b.get("type", 0) != 0:
            continue
        for ln in b.get("lines", []):
            chars = []
            for s in ln.get("spans", []):
                for ch in s.get("chars", []):
                    for _k in range(max(1, len(ch["c"]))):
                        chars.append((ch["c"][:1] if ch["c"] else " ", ch["bbox"], ch["origin"], s))
            txt = "".join(c[0] for c in chars)
            ms = [(m.start(), m.end()) for m in rx.finditer(txt)]
            if not ms or not chars:
                continue
            rect = fitz.Rect(chars[0][1])
            for c in chars[1:]:
                rect |= fitz.Rect(c[1])
            rot = _dir_to_rot(ln.get("dir", (1, 0)))
            keys = set((c[3].get("font"), round(c[3].get("size", 0), 1), c[3].get("color")) for c in chars if c[0] != " ")
            size = float(chars[0][3].get("size", 11))
            gap = False
            for a, c in zip(chars, chars[1:]):                       # a wide empty gap = table columns: do not re-flow the line
                if a[0] != " " and c[0] != " ":
                    g = (c[1][0] - a[1][2]) if rot == 0 else 0
                    if g > size * 1.2:
                        gap = True
                        break
            out.append({"txt": txt, "chars": chars, "matches": ms, "rect": rect, "origin": fitz.Point(chars[0][2]), "rot": rot,
                        "style": style_from_span(chars[0][3]), "uniform": len(keys) <= 1 and not gap and rot == 0})
    return out


def _matches_on_page(page, find, case, whole):
    """Every match as dict(rect, origin, rot, style, text), unrotated coordinates."""
    out = []
    for ln in _scan_lines(page, find, case, whole):
        for a, b in ln["matches"]:
            cs = ln["chars"][a:b]
            r = fitz.Rect(cs[0][1])
            for c in cs[1:]:
                r |= fitz.Rect(c[1])
            out.append({"rect": r, "origin": fitz.Point(cs[0][2]), "rot": ln["rot"], "style": style_from_span(cs[0][3]),
                        "text": ln["txt"][a:b]})
    return out


def ed_find(doc, find, case=False, whole=False, pages=None, progress=None):
    """List of (page_index, Rect) for the highlight display."""
    hits = []
    rng = list(pages) if pages is not None else list(range(doc.page_count))
    for n, pno in enumerate(rng):
        if progress and progress(n, len(rng)):
            break
        for m in _matches_on_page(doc[pno], find, case, whole):
            hits.append((pno, m["rect"]))
    return hits


def _units_for_page(page, find, repl, case, whole, only, pno):
    """Work list for one page. A uniformly styled line is re-written as a whole (natural spacing);
    other lines are replaced word by word."""
    units = []
    for ln in _scan_lines(page, find, case, whole):
        sel = []
        for a, b in ln["matches"]:
            cs = ln["chars"][a:b]
            r = fitz.Rect(cs[0][1])
            for c in cs[1:]:
                r |= fitz.Rect(c[1])
            if only is None or (only[0] == pno and fitz.Rect(r).irect == fitz.Rect(only[1]).irect):
                sel.append((a, b, r, fitz.Point(cs[0][2]), style_from_span(cs[0][3])))
        if not sel:
            continue
        if ln["uniform"]:
            txt, pos, new = ln["txt"], 0, []
            for a, b, _r, _o, _s in sel:
                new.append(txt[pos:a])
                new.append(repl)
                pos = b
            new.append(txt[pos:])
            units.append({"rect": ln["rect"], "origin": ln["origin"], "rot": ln["rot"], "style": ln["style"],
                          "text": "".join(new).rstrip(), "count": len(sel)})
        else:
            for a, b, r, o, st in sel:
                units.append({"rect": r, "origin": o, "rot": ln["rot"], "style": st, "text": repl, "count": 1})
    return units


def ed_find_replace(doc, find, repl, case=False, whole=False, pages=None, fit=False, only=None, progress=None):
    """Replace matches, keeping font, size and colour. Returns the number of matches replaced."""
    if not find:
        raise UserError("Type the text to find first.")
    rng = list(pages) if pages is not None else list(range(doc.page_count))
    total = 0
    for n, pno in enumerate(rng):
        if progress and progress(n, len(rng)):
            raise Cancelled()
        page = doc[pno]
        units = _units_for_page(page, find, repl, case, whole, only, pno)
        if not units:
            continue
        for u in units:                                # choose fonts first: redaction may drop them from the page
            u["style"] = dict(u["style"], fit=bool(fit))
            u["fp"] = _pick_font(doc, page, u["style"], u["text"]) if u["text"].strip() else None
        saved_links = _links_snapshot(page)
        for u in units:
            r = u["rect"]
            pad = max(0.5, float(u["style"]["size"]) * 0.28)
            rr = (fitz.Rect(r.x0 - 0.3, r.y0 + pad, r.x1 + 0.3, r.y1 - pad) if u["rot"] in (0, 180)
                  else fitz.Rect(r.x0 + pad, r.y0 - 0.3, r.x1 - pad, r.y1 + 0.3))
            page.add_redact_annot(rr if not rr.is_empty else r, fill=False)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                              text=fitz.PDF_REDACT_TEXT_REMOVE)
        _links_restore(page, saved_links)
        for u in units:
            if u["text"].strip():
                _write_text(doc, page, u["rect"], u["text"], u["style"], u["origin"], u["rot"], None, False, u["fp"])
            total += u["count"]
    return total


# ============================================================================
#  EDIT PDF - session (undo/redo), canvas, dialogs and the tool page
# ============================================================================
class EditSession:
    """One PDF open for editing. Works on an in-memory copy; every successful change is an undo step."""

    def __init__(self, path):
        self.path = path
        self.doc = open_pdf(path)
        self.undo, self.redo = [], []
        self.changes = 0
        self.saved_mark = 0
        self.max_bytes = 350 * 1024 * 1024

    @property
    def dirty(self):
        return self.changes != self.saved_mark

    def _snapshot(self):
        return self.doc.tobytes(garbage=0, deflate=True)

    def run(self, fn, *args, **kw):
        """Run fn(doc, ...). On any error the document is restored from the snapshot (self.doc is then a NEW object)."""
        snap = self._snapshot()
        try:
            res = fn(self.doc, *args, **kw)
        except BaseException:
            self.doc = fitz.open("pdf", snap)
            raise
        self.undo.append(snap)
        self.redo = []
        self.changes += 1
        while len(self.undo) > 1 and sum(len(x) for x in self.undo) > self.max_bytes:
            self.undo.pop(0)
        return res

    def step_undo(self):
        if not self.undo:
            return False
        self.redo.append(self._snapshot())
        self.doc = fitz.open("pdf", self.undo.pop())
        self.changes -= 1
        return True

    def step_redo(self):
        if not self.redo:
            return False
        self.undo.append(self._snapshot())
        self.doc = fitz.open("pdf", self.redo.pop())
        self.changes += 1
        return True

    def has_signature(self):
        try:
            if not self.doc.is_form_pdf:
                return False
            for i in range(min(self.doc.page_count, 200)):
                for w in (self.doc[i].widgets() or []):
                    if w.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                        return True
        except Exception:
            pass
        return False


def _pick_color(parent, rgb):
    c = QColorDialog.getColor(qcolor(rgb), parent, "Choose a colour")
    if not c.isValid():
        return None
    return (c.red() / 255.0, c.green() / 255.0, c.blue() / 255.0)


def _paint_swatch(btn, rgb):
    btn.setStyleSheet("QPushButton{background:rgb(%d,%d,%d);border:1px solid #7A8AA8;border-radius:4px;min-width:30px;max-width:30px;}"
                      % tuple(int(round(v * 255)) for v in rgb))


class StyleBar(QWidget):
    """Font, size, colour, bold / italic, alignment: used for new text and inside the edit-text window."""
    FONTS = [("Auto (as original)", "auto"), ("Sans-serif", "sans"), ("Serif", "serif"), ("Monospace", "mono"),
             ("Unicode / Indic", "unicode"), ("Font file...", "file")]

    def __init__(self):
        QWidget.__init__(self)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        self.font = QComboBox()
        for lab, key in self.FONTS:
            self.font.addItem(lab, key)
        self.size = QDoubleSpinBox()
        self.size.setRange(3, 300)
        self.size.setDecimals(1)
        self.size.setSingleStep(0.5)
        self.size.setValue(12)
        self.size.setSuffix(" pt")
        self.btn = QPushButton("")
        self.btn.setToolTip("Text colour")
        self.color = (0.0, 0.0, 0.0)
        _paint_swatch(self.btn, self.color)
        self.bold = QToolButton(); self.bold.setText("B"); self.bold.setCheckable(True); self.bold.setToolTip("Bold")
        f = self.bold.font(); f.setBold(True); self.bold.setFont(f)
        self.italic = QToolButton(); self.italic.setText("I"); self.italic.setCheckable(True); self.italic.setToolTip("Italic")
        f = self.italic.font(); f.setItalic(True); self.italic.setFont(f)
        self.align = QComboBox()
        for a in ("Left", "Centre", "Right", "Justify"):
            self.align.addItem(a)
        self.fit = QCheckBox("Keep width")
        self.font.setMinimumWidth(130)
        self.fit.setChecked(True)
        self.fit.setToolTip("If the new text is longer than the old, shrink it (down to 60%) instead of letting it run on.")
        self.fontfile = ""
        self.base = default_style()
        for w in (self.font, self.size, self.btn, self.bold, self.italic, self.align, self.fit):
            h.addWidget(w)
        h.addStretch(1)
        self.btn.clicked.connect(self._pick)
        self.font.activated.connect(self._font_changed)

    def _pick(self):
        c = _pick_color(self, self.color)
        if c:
            self.color = c
            _paint_swatch(self.btn, c)

    def _font_changed(self, _i):
        if self.font.currentData() == "file":
            p, _ = QFileDialog.getOpenFileName(self, "Choose a font file", SET.last_dir("fontfile"), "Fonts (*.ttf *.otf)")
            if p:
                SET.remember_dir("fontfile", p)
                self.fontfile = p
                self.font.setItemText(self.font.currentIndex(), "Font file: " + os.path.basename(p))
            else:
                self.font.setCurrentIndex(0)

    def set(self, st):
        self.base = dict(st)
        self.font.setCurrentIndex(0)
        self.size.setValue(float(st.get("size", 12)))
        self.color = tuple(st.get("color", (0, 0, 0)))
        _paint_swatch(self.btn, self.color)
        self.bold.setChecked(bool(st.get("bold")))
        self.italic.setChecked(bool(st.get("italic")))
        self.align.setCurrentIndex(int(st.get("align", 0)))
        self.fit.setChecked(bool(st.get("fit", True)))

    def get(self):
        st = dict(self.base)
        st.update({"font": self.font.currentData(), "fontfile": self.fontfile, "size": float(self.size.value()),
                   "color": tuple(self.color), "bold": self.bold.isChecked(), "italic": self.italic.isChecked(),
                   "align": self.align.currentIndex(), "fit": self.fit.isChecked()})
        return st


class TextEditDialog(QDialog):
    """Edit the wording and style of one piece of text (or write a new one)."""

    def __init__(self, parent, title, text, style, allow_delete=False, hint=""):
        QDialog.__init__(self, parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(640)
        v = QVBoxLayout(self)
        if hint:
            v.addWidget(hint_label(hint))
        self.edit = QPlainTextEdit()
        self.edit.setPlainText(text)
        self.edit.setMinimumHeight(130)
        f = self.edit.font(); f.setPointSize(11); self.edit.setFont(f)
        v.addWidget(self.edit)
        self.bar = StyleBar()
        self.bar.set(style)
        v.addWidget(self.bar)
        row = QHBoxLayout()
        ok = QPushButton("Apply"); ok.setObjectName("primary"); ok.setDefault(True)
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        row.addStretch(1)
        if allow_delete:
            dele = QPushButton("Delete this text")
            dele.clicked.connect(lambda: self.done(2))
            row.addWidget(dele)
        row.addWidget(cancel)
        row.addWidget(ok)
        v.addLayout(row)

    def values(self):
        return self.edit.toPlainText(), self.bar.get()


class LinkDialog(QDialog):
    def __init__(self, parent, kind="uri", target="", pages=1):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Link")
        v = QVBoxLayout(self)
        self.r_uri = QRadioButton("Open a web address / e-mail")
        self.r_page = QRadioButton("Jump to a page in this PDF")
        self.uri = QLineEdit(target if kind == "uri" else "https://")
        self.page = QSpinBox(); self.page.setRange(1, max(1, pages))
        if kind == "page":
            try:
                self.page.setValue(int(target))
            except Exception:
                pass
        (self.r_page if kind == "page" else self.r_uri).setChecked(True)
        for w in (self.r_uri, self.uri, self.r_page, self.page):
            v.addWidget(w)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def values(self):
        if self.r_page.isChecked():
            return "page", self.page.value()
        u = self.uri.text().strip()
        if u and "://" not in u and not u.lower().startswith("mailto:"):
            u = ("mailto:" + u) if "@" in u else ("https://" + u)
        return "uri", u


class EditCanvas(ViewCanvas):
    """Page canvas with selection, hover, drag-to-move, resize handles and rubber-band drawing."""

    def __init__(self, viewer, tool):
        ViewCanvas.__init__(self, viewer)
        self.tool = tool
        self.state = None
        self.hover = None
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

    # ---- geometry
    def crect(self, pno, rect):
        v = self.v
        vr = fitz.Rect(rect) * v.doc[pno].rotation_matrix
        vr.normalize()
        z = v.zoom
        return QRectF(v.page_x(pno) + vr.x0 * z, v.offsets[pno] + vr.y0 * z, vr.width * z, vr.height * z)

    def vpt(self, pno, pos, clamp=True):
        v = self.v
        z = v.zoom
        x, y = (pos.x() - v.page_x(pno)) / z, (pos.y() - v.offsets[pno]) / z
        if clamp:
            pr = v.doc[pno].rect
            x, y = min(max(x, 0), pr.width), min(max(y, 0), pr.height)
        return fitz.Point(x, y)

    def _unrot_rect(self, pno, qr):
        v = self.v
        z = v.zoom
        x0, y0 = v.page_x(pno), v.offsets[pno]
        vr = fitz.Rect((qr.left() - x0) / z, (qr.top() - y0) / z, (qr.right() - x0) / z, (qr.bottom() - y0) / z)
        return fitz.Rect(vr * v.doc[pno].derotation_matrix).normalize()

    def _handles(self, qr):
        return {"tl": qr.topLeft(), "tr": qr.topRight(), "bl": qr.bottomLeft(), "br": qr.bottomRight()}

    def _handle_at(self, sel, pos):
        qr = self.crect(sel["pno"], sel["rect"])
        for k, p in self._handles(qr).items():
            if abs(p.x() - pos.x()) <= 6 and abs(p.y() - pos.y()) <= 6:
                return k
        return None

    # ---- painting
    def paintEvent(self, ev):
        ViewCanvas.paintEvent(self, ev)
        v, t = self.v, self.tool
        if not v.doc:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.hover and self.hover is not t.selected and t.mode == "select":
            r = self.crect(self.hover["pno"], self.hover["rect"])
            p.fillRect(r, QColor(255, 170, 0, 55))
            p.setPen(QPen(QColor(255, 140, 0), 1))
            p.drawRect(r)
        sel, st = t.selected, self.state
        if sel and t.mode == "select":
            r = self.crect(sel["pno"], sel["rect"])
            if st and st["kind"] in ("move", "resize") and st.get("moved"):
                p.setPen(QPen(QColor(BLUE2), 1, Qt.DashLine))
                p.setBrush(Qt.NoBrush)
                p.drawRect(st["preview"])
            p.setPen(QPen(QColor(BLUE2), 2))
            p.setBrush(QColor(45, 108, 223, 30))
            p.drawRect(r)
            if sel["kind"] == "image":
                p.setBrush(QColor("white"))
                for pt in self._handles(r).values():
                    p.drawRect(QRectF(pt.x() - 4, pt.y() - 4, 8, 8))
        if st and st["kind"] == "draw":
            a, b = st["start"], st["now"]
            p.setPen(QPen(QColor(RED), 1.6, Qt.DashLine))
            p.setBrush(QColor(214, 40, 57, 30))
            if t.mode in ("line", "arrow"):
                p.drawLine(a, b)
            else:
                rr = QRect(a, b).normalized()
                (p.drawEllipse if t.mode == "oval" else p.drawRect)(rr)
        p.end()

    # ---- mouse
    def mousePressEvent(self, e):
        v, t = self.v, self.tool
        if not v.doc or e.button() != Qt.LeftButton:
            return
        self.setFocus()
        pno = v.page_at(e.pos().y())
        page = v.doc[pno]
        if t.mode == "select":
            sel = t.selected
            if sel and sel["pno"] == pno:
                if sel["kind"] == "image":
                    h = self._handle_at(sel, e.pos())
                    if h:
                        orig = self.crect(pno, sel["rect"])
                        self.state = {"kind": "resize", "h": h, "pno": pno, "start": e.pos(), "moved": False,
                                      "orig": orig, "preview": orig}
                        return
                if sel["kind"] in ("text", "image") and self.crect(pno, sel["rect"]).contains(e.pos()):
                    orig = self.crect(pno, sel["rect"])
                    self.state = {"kind": "move", "pno": pno, "start": e.pos(), "moved": False, "orig": orig, "preview": orig}
                    return
            item = t.pick(pno, fitz.Point(self.vpt(pno, e.pos(), False)) * page.derotation_matrix)
            t.select(item)
            if item and item["kind"] in ("text", "image"):
                orig = self.crect(pno, item["rect"])
                self.state = {"kind": "move", "pno": pno, "start": e.pos(), "moved": False, "orig": orig, "preview": orig}
            self.update()
        else:
            self.state = {"kind": "draw", "pno": pno, "start": e.pos(), "now": e.pos()}

    def mouseMoveEvent(self, e):
        v, t = self.v, self.tool
        st = self.state
        if st:
            if st["kind"] == "draw":
                st["now"] = e.pos()
            else:
                d = e.pos() - st["start"]
                if abs(d.x()) + abs(d.y()) > 4:
                    st["moved"] = True
                if st["moved"]:
                    if st["kind"] == "move":
                        st["preview"] = st["orig"].translated(d.x(), d.y())
                    else:
                        st["preview"] = self._resize_rect(st["orig"], st["h"], e.pos())
            self.update()
            return
        if v.doc and t.mode == "select":
            pno = v.page_at(e.pos().y())
            page = v.doc[pno]
            it = t.pick(pno, fitz.Point(self.vpt(pno, e.pos(), False)) * page.derotation_matrix, quiet=True)
            if it is not self.hover:
                self.hover = it
                self.setCursor(Qt.PointingHandCursor if it else Qt.ArrowCursor)
                self.setToolTip(t.describe(it) if it else "")
                self.update()

    @staticmethod
    def _resize_rect(orig, h, pos):
        ax = orig.right() if "l" in h else orig.left()
        ay = orig.bottom() if "t" in h else orig.top()
        w = max(10.0, abs(pos.x() - ax))
        hh = w / max(0.01, orig.width() / max(1.0, orig.height()))
        x = ax - w if "l" in h else ax
        y = ay - hh if "t" in h else ay
        return QRectF(x, y, w, hh)

    def mouseReleaseEvent(self, e):
        v, t = self.v, self.tool
        st, self.state = self.state, None
        self.update()
        if not st or not v.doc:
            return
        pno = st["pno"]
        if st["kind"] == "draw":
            a, b = self.vpt(pno, st["start"]), self.vpt(pno, e.pos())
            t.drawn(t.mode, pno, a, b)
        elif st.get("moved") and t.selected:
            item = t.selected
            if st["kind"] == "move":
                d = e.pos() - st["start"]
                z = v.zoom
                inv = v.doc[pno].derotation_matrix
                delta = fitz.Point(d.x() / z, d.y() / z) * inv - fitz.Point(0, 0) * inv
                t.move_item(item, delta)
            else:
                t.resize_item(item, self._unrot_rect(pno, st["preview"]))

    def mouseDoubleClickEvent(self, e):
        if self.tool.mode == "select" and self.tool.selected:
            self.tool.edit_selected()

    def leaveEvent(self, e):
        if self.hover:
            self.hover = None
            self.update()

    def keyPressEvent(self, e):
        t = self.tool
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            t.delete_selected()
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter):
            t.edit_selected()
        elif e.key() == Qt.Key_Escape:
            self.state = None
            t.select(None)
        else:
            ViewCanvas.keyPressEvent(self, e)


class EditViewer(PdfViewer):
    """PdfViewer whose canvas is the editing canvas; can swap the document (undo / redo) keeping zoom and scroll."""

    def __init__(self, tool):
        PdfViewer.__init__(self, select_mode=False, compact=True)
        self.btn_rot.hide()
        old = self.scroll.takeWidget()
        self.canvas = EditCanvas(self, tool)
        self.scroll.setWidget(self.canvas)
        if old is not None:
            old.deleteLater()

    def _start_thumbs(self):
        pass

    def swap_doc(self, doc):
        old, keep = self.doc, self.scroll.verticalScrollBar().value()
        self.doc = doc
        self.cache.clear()
        self.spin.blockSignals(True)
        self.spin.setMaximum(max(1, doc.page_count))
        self.spin.blockSignals(False)
        self.lbl_total.setText("/ %d" % doc.page_count)
        self._relayout()
        self.scroll.verticalScrollBar().setValue(keep)
        if old is not None and old is not doc:
            try:
                old.close()
            except Exception:
                pass

    def invalidate(self, pno=None):
        if pno is None:
            self.cache.clear()
        else:
            for k in [k for k in self.cache if k[0] == pno]:
                del self.cache[k]
        self.canvas.update()


EDIT_MODES = [("select", "Select"), ("text", "Text"), ("image", "Image"), ("rect", "Rect"),
              ("oval", "Oval"), ("line", "Line"), ("arrow", "Arrow"), ("cover", "White-out"), ("link", "Link")]
EDIT_MODE_TIPS = {"select": "Select / edit existing text, pictures and links", "text": "Add new text", "image": "Add a picture",
                  "rect": "Draw a rectangle", "oval": "Draw an oval", "line": "Draw a line", "arrow": "Draw an arrow",
                  "cover": "White-out: hide (and really delete) an area", "link": "Add a link to an area"}
EDIT_MODE_HELP = {
    "select": "Click text, a picture, a note or a link to select it. Double-click text to change it. Drag to move. "
              "Pictures have corner handles. Delete key removes the selected item.",
    "text": "Drag a box where the new text should go (or just click), then type it.",
    "image": "Drag a box where the picture should go, then choose the picture file.",
    "rect": "Drag to draw a rectangle.", "oval": "Drag to draw an oval.", "line": "Drag to draw a line.",
    "arrow": "Drag from the tail to the point of the arrow.",
    "cover": "Drag over what you want to hide. With the tick below it is really deleted, not just covered.",
    "link": "Drag over the area that should become a link."}


class EditPdfTool(ToolPage):
    key, title, group = "pdfedit", "Edit PDF", "Edit"
    subtitle = ("Change the wording of existing text, add text, pictures, shapes and links, find & replace, white-out, "
                "move or delete things - then undo anything. Saves a NEW file; the original is never changed.")
    action_text = "Save edited PDF"

    def build(self, L):
        self.sess = None
        self.selected = None
        self.mode = "select"
        self._items = {}
        self.find_hits, self.find_idx, self._hits_key = [], -1, None
        self.pdf = PdfPicker("pdfedit")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        top = QHBoxLayout()
        ob = QPushButton("Reload file")
        ob.setToolTip("Open the chosen PDF again (discards unsaved changes after asking)")
        ob.clicked.connect(self.open_doc)
        top.addWidget(ob)
        self.btn_undo = QPushButton("Undo"); self.btn_redo = QPushButton("Redo")
        self.btn_edit = QPushButton("Edit"); self.btn_del = QPushButton("Delete")
        self.btn_rep = QPushButton("Replace picture")
        self.btn_edit.setToolTip("Edit the selected text or link (or double-click it)")
        self.btn_del.setToolTip("Delete the selected item (Delete key)")
        self.btn_rep.setToolTip("Replace the selected picture with another file")
        self.btn_undo.clicked.connect(self.do_undo)
        self.btn_redo.clicked.connect(self.do_redo)
        self.btn_edit.clicked.connect(self.edit_selected)
        self.btn_del.clicked.connect(self.delete_selected)
        self.btn_rep.clicked.connect(self.replace_selected_image)
        for b in (self.btn_undo, self.btn_redo, self.btn_edit, self.btn_del, self.btn_rep):
            top.addWidget(b)
        top.addStretch(1)
        L.addLayout(top)
        bar = QWidget()
        bar.setStyleSheet("QToolButton{border:1px solid #AFC3E6;border-radius:6px;padding:4px 7px;background:transparent;}"
                          "QToolButton:hover{border-color:#2D6CDF;}"
                          "QToolButton:checked{background:#2D6CDF;color:white;border:1px solid #2D6CDF;}")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(4)
        self.mode_buttons = {}
        grp = QButtonGroup(self)
        grp.setExclusive(True)
        for key, label in EDIT_MODES:
            b = QToolButton()
            b.setText(label)
            b.setToolTip(EDIT_MODE_TIPS[key])
            b.setCheckable(True)
            b.clicked.connect(lambda _c, k=key: self.set_mode(k))
            grp.addButton(b)
            bl.addWidget(b)
            self.mode_buttons[key] = b
        bl.addStretch(1)
        self.mode_buttons["select"].setChecked(True)
        L.addWidget(bar)
        # options: only the group that belongs to the chosen tool is shown
        self.style = StyleBar()
        self.w_text = QWidget()
        tl = QVBoxLayout(self.w_text)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.addWidget(QLabel("Style for NEW text (existing text opens its own style box when you edit it):"))
        tl.addWidget(self.style)
        self.unit = self.combo([("Text: by line", "line"), ("Text: by paragraph", "para")])
        self.unit.setToolTip("Line: change one line exactly where it is. Paragraph: change a whole block; the words re-wrap inside the same box.")
        self.unit.currentIndexChanged.connect(lambda _i: (self._items.clear(), self.select(None)))
        self.w_select = QWidget()
        sl = QHBoxLayout(self.w_select)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.addWidget(QLabel("What a click selects:"))
        sl.addWidget(self.unit)
        sl.addStretch(1)
        self.stroke = (0.84, 0.16, 0.22)
        self.btn_stroke = QPushButton("")
        self.btn_stroke.setToolTip("Outline / line colour")
        _paint_swatch(self.btn_stroke, self.stroke)
        self.btn_stroke.clicked.connect(self._pick_stroke)
        self.width = self.dspin(0.5, 20, 2.0, " pt", 0.5, 1)
        self.fill = self.combo([("No fill", None), ("Fill white", (1, 1, 1)), ("Fill = outline", "same"),
                                ("Fill yellow", (1, 1, 0.7)), ("Fill blue", (0.8, 0.9, 1))])
        self.w_shape = QWidget()
        hl = QHBoxLayout(self.w_shape)
        hl.setContentsMargins(0, 0, 0, 0)
        for w in (QLabel("Outline:"), self.btn_stroke, self.width, self.fill):
            hl.addWidget(w)
        hl.addStretch(1)
        self.remove_under = QCheckBox("White-out really deletes what is underneath (not just hides it)")
        self.remove_under.setChecked(True)
        self.w_cover = self.remove_under
        self.opt_panels = {"select": self.w_select, "text": self.w_text, "rect": self.w_shape, "oval": self.w_shape,
                           "line": self.w_shape, "arrow": self.w_shape, "cover": self.w_cover}
        for w in (self.w_select, self.w_text, self.w_shape, self.w_cover):
            L.addWidget(w)
        self.hint = hint_label(EDIT_MODE_HELP["select"])
        L.addWidget(self.hint)
        self.hint.setMinimumWidth(10)
        self.note = QLabel("Choose a PDF above - it opens here for editing.")
        self.note.setObjectName("status")
        self.note.setWordWrap(True)
        L.addWidget(self.note)
        self.viewer = EditViewer(self)
        self.viewer.setMinimumHeight(520)
        L.addWidget(self.viewer)
        # find & replace
        gb = QGroupBox("Find and replace")
        gv = QVBoxLayout(gb)
        gl, gl2, gl3 = QHBoxLayout(), QHBoxLayout(), QHBoxLayout()
        gv.addLayout(gl)
        gv.addLayout(gl2)
        gv.addLayout(gl3)
        self.f_find, self.f_repl = QLineEdit(), QLineEdit()
        self.f_find.setPlaceholderText("Find...")
        self.f_repl.setPlaceholderText("Replace with...")
        self.f_case = QCheckBox("Match case")
        self.f_whole = QCheckBox("Whole word")
        self.f_fit = QCheckBox("Keep line width")
        self.f_fit.setChecked(True)
        self.f_fit.setToolTip("If the new text makes the line longer, shrink it (down to 60%) instead of letting it run on.")
        self.f_scope = self.combo(["All pages", "This page only"])
        b1, b2, b3 = QPushButton("Find next"), QPushButton("Replace this"), QPushButton("Replace all")
        self.f_count = QLabel("")
        b1.clicked.connect(self.find_next)
        b2.clicked.connect(self.replace_this)
        b3.clicked.connect(self.replace_all)
        self.f_find.returnPressed.connect(self.find_next)
        for w in (self.f_find, self.f_repl):
            gl.addWidget(w)
        for w in (self.f_case, self.f_whole, self.f_fit, self.f_scope):
            gl2.addWidget(w)
        gl2.addStretch(1)
        for w in (b1, b2, b3, self.f_count):
            gl3.addWidget(w)
        gl3.addStretch(1)
        L.addWidget(gb)
        L.addWidget(hint_label("Edited text keeps the font, size and colour of the original where the file allows it; otherwise the closest "
                               "standard font is used and the status line above tells you. Scanned pages have no real text - run OCR first, "
                               "or use White-out + Add text. Editing a digitally signed PDF removes the signature's validity."))
        self.set_mode("select")
        self._buttons_update()
        self.pdf.changed.connect(self._picked)

    def _picked(self, *a):
        p = self.pdf.path()
        if p and os.path.isfile(p) and p.lower().endswith(".pdf") and not (self.sess and os.path.abspath(self.sess.path) == os.path.abspath(p)):
            self.open_doc()

    def after_build(self):
        for seq, fn in (("Ctrl+Z", self.do_undo), ("Ctrl+Y", self.do_redo), ("Ctrl+Shift+Z", self.do_redo),
                        ("Delete", self._key_delete)):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.WidgetWithChildrenShortcut)
            sc.activated.connect(fn)

    # ---------------------------------------------------------------- small helpers
    def _key_delete(self):
        fw = QApplication.focusWidget()
        if isinstance(fw, (QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox)):
            return
        self.delete_selected()

    def _pick_stroke(self):
        c = _pick_color(self, self.stroke)
        if c:
            self.stroke = c
            _paint_swatch(self.btn_stroke, c)

    def set_mode(self, key):
        self.mode = key
        self.mode_buttons[key].setChecked(True)
        self.hint.setText(EDIT_MODE_HELP[key])
        for w in (self.w_select, self.w_text, self.w_shape, self.w_cover):
            w.setVisible(w is self.opt_panels.get(key))
        self.viewer.canvas.setCursor(Qt.ArrowCursor if key == "select" else Qt.CrossCursor)
        if key != "select":
            self.select(None)

    def _buttons_update(self):
        s = self.sess
        self.btn_undo.setEnabled(bool(s and s.undo))
        self.btn_redo.setEnabled(bool(s and s.redo))
        sel = self.selected
        self.btn_edit.setEnabled(bool(sel and sel["kind"] in ("text", "link")))
        self.btn_del.setEnabled(bool(sel))
        self.btn_rep.setEnabled(bool(sel and sel["kind"] == "image"))

    def describe(self, it):
        k = it["kind"]
        if k == "text":
            t = it["text"].replace("\n", " ")
            return "Text: %s%s  (%s, %s pt)" % (t[:40], "..." if len(t) > 40 else "", _SUBSET_RE.sub("", it["style"]["font_name"]), it["style"]["size"])
        if k == "image":
            return "Picture"
        if k == "annot":
            return "Annotation: %s" % it.get("type", "")
        lk = it["link"]
        return "Link: %s" % (lk.get("uri") or ("page %s" % (int(lk.get("page", 0)) + 1)))

    def items_for(self, pno):
        if pno not in self._items:
            its = page_edit_items(self.sess.doc[pno], self.unit.currentData())
            for it in its:
                it["pno"] = pno
            self._items[pno] = its
        return self._items[pno]

    def pick(self, pno, upt, quiet=False):
        if not self.sess:
            return None
        its = self.items_for(pno)
        it = pick_item(its, upt)
        if it is None and not quiet and not any(i["kind"] == "text" for i in its) and self.mode == "select":
            self.note.setText("This page has no real text (it may be a scanned picture). Use OCR first, or White-out + Add text.")
        return it

    def select(self, item):
        self.selected = item
        if item:
            tip = {"text": "Double-click or press Enter to change the text; drag to move; Delete removes it.",
                   "image": "Drag to move, drag a corner to resize, Delete removes it, or use 'Replace picture...'.",
                   "annot": "Delete removes this annotation.", "link": "Enter edits the link; Delete removes it."}[item["kind"]]
            self.note.setText("%s.  %s" % (self.describe(item), tip))
        self._buttons_update()
        self.viewer.canvas.update()

    # ---------------------------------------------------------------- open / undo
    def open_doc(self):
        try:
            path = self.pdf.require()
            if self.sess and self.sess.dirty:
                r = QMessageBox.question(self, APP_NAME, "You have unsaved changes in the PDF that is open. Discard them and open this file?")
                if r != QMessageBox.Yes:
                    return
            sess = EditSession(path)
        except UserError as e:
            self.warn(str(e))
            return
        self.sess = sess
        self._items.clear()
        self.selected = None
        self.find_hits, self.find_idx = [], -1
        self.viewer.load_doc(sess.doc, path)
        SET.add_recent(path)
        msg = "Opened %d page(s)." % sess.doc.page_count
        if sess.has_signature():
            msg = "WARNING: this PDF has a digital signature. Any edit makes the signature invalid.  " + msg
        self.note.setText(msg)
        self._buttons_update()

    def open_file(self, p):
        self.pdf.set_path(p)
        self.open_doc()

    def _swapped(self, text):
        self.viewer.swap_doc(self.sess.doc)
        self._items.clear()
        self.find_hits, self.find_idx = [], -1
        self.viewer.highlights = {}
        self.viewer.canvas.hover = None
        self.select(None)
        self.note.setText(text)
        self._buttons_update()

    def do_undo(self):
        if self.sess and self.sess.step_undo():
            self._swapped("Undone.")

    def do_redo(self):
        if self.sess and self.sess.step_redo():
            self._swapped("Redone.")

    # ---------------------------------------------------------------- applying changes
    def _need_doc(self):
        if not self.sess:
            self.warn("Choose a PDF file above first.")
            return False
        return True

    def apply(self, label, inval, fn, *args, **kw):
        """Run an engine function as ONE undo step. Returns True on success."""
        if not self._need_doc():
            return False
        try:
            res = self.sess.run(fn, *args, **kw)
        except Cancelled:
            self._swapped("Cancelled - nothing was changed.")
            return False
        except UserError as e:
            self._swapped("Not changed.")
            self.warn(str(e))
            return False
        except Exception as e:
            log_exc("pdfedit")
            self._swapped("Not changed.")
            QMessageBox.critical(self, APP_NAME, "This change could not be made: %s: %s\n\nNothing was changed. Details are in the log file."
                                 % (type(e).__name__, str(e)[:250]))
            return False
        self._items.clear()
        self.find_hits, self.find_idx = [], -1
        self.viewer.highlights = {}
        self.viewer.canvas.hover = None
        self.viewer.invalidate(inval)
        self.selected = None
        notes = []
        if isinstance(res, list):
            notes = [n for n in res if n]
        elif isinstance(res, str) and res:
            notes = [res]
        self.note.setText("%s.%s" % (label, ("  " + "  ".join(notes)) if notes else ""))
        self._buttons_update()
        return True

    # ---------------------------------------------------------------- selected item actions
    def edit_selected(self):
        s = self.selected
        if not s or not self._need_doc():
            return
        if s["kind"] == "text":
            hint = ("Paragraph: lines are re-wrapped inside the same box." if s["unit"] == "para" else
                    "One line. To write several lines, switch to 'Edit by paragraph' (box under the toolbar).")
            dlg = TextEditDialog(self, "Edit text", s["text"], s["style"], allow_delete=True, hint=hint)
            r = dlg.exec_()
            if r == QDialog.Accepted:
                text, st = dlg.values()
                self.apply("Text changed", s["pno"], ed_replace_text, s["pno"], s["rect"], text, st, dest=s["rect"],
                           origin=s["origin"], rot=s["rot"], pitch=s["pitch"], para=(s["unit"] == "para"))
            elif r == 2:
                self.delete_selected()
        elif s["kind"] == "link":
            lk = s["link"]
            kind, target = ("page", int(lk.get("page", 0)) + 1) if lk.get("kind") == fitz.LINK_GOTO else ("uri", lk.get("uri", ""))
            dlg = LinkDialog(self, kind, str(target), self.sess.doc.page_count)
            if dlg.exec_() == QDialog.Accepted:
                k, t = dlg.values()
                self.apply("Link changed", s["pno"], ed_update_link, s["pno"], s["rect"], k, t)

    def delete_selected(self):
        s = self.selected
        if not s or not self._need_doc():
            return
        p = s["pno"]
        if s["kind"] == "text":
            self.apply("Text deleted", p, ed_replace_text, p, s["rect"], "", s["style"], rot=s["rot"])
        elif s["kind"] == "image":
            self.apply("Picture deleted", p, ed_delete_image, p, s["rect"], s["xref"])
        elif s["kind"] == "annot":
            self.apply("Annotation deleted", p, ed_delete_annot, p, s["xref"])
        elif s["kind"] == "link":
            self.apply("Link deleted", p, ed_delete_link, p, s["rect"])

    def replace_selected_image(self):
        s = self.selected
        if not s or s["kind"] != "image":
            return
        path, _ = QFileDialog.getOpenFileName(self, "Choose the new picture", SET.last_dir("pdfedit_img"),
                                              "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)")
        if path:
            SET.remember_dir("pdfedit_img", path)
            self.apply("Picture replaced", s["pno"], ed_replace_image, s["pno"], s["rect"], s["xref"], path)

    def move_item(self, item, delta):
        p, r = item["pno"], fitz.Rect(item["rect"])
        dest = fitz.Rect(r.x0 + delta.x, r.y0 + delta.y, r.x1 + delta.x, r.y1 + delta.y)
        if item["kind"] == "text":
            origin = fitz.Point(item["origin"].x + delta.x, item["origin"].y + delta.y)
            self.apply("Text moved", p, ed_replace_text, p, r, item["text"], item["style"], dest=dest, origin=origin,
                       rot=item["rot"], pitch=item["pitch"], para=(item["unit"] == "para"))
        elif item["kind"] == "image":
            self.apply("Picture moved", p, ed_move_image, p, r, item["xref"], dest)

    def resize_item(self, item, new_rect):
        if item["kind"] == "image":
            self.apply("Picture resized", item["pno"], ed_move_image, item["pno"], item["rect"], item["xref"], new_rect)

    # ---------------------------------------------------------------- drawing on the page
    def drawn(self, mode, pno, p0, p1):
        if not self._need_doc():
            return
        vr = fitz.Rect(p0, p1).normalize()
        small = vr.width < 6 or vr.height < 6
        if mode == "text":
            st = self.style.get()
            if small:
                vr = fitz.Rect(p0.x, p0.y, min(p0.x + 220, self.sess.doc[pno].rect.x1), p0.y + max(24, st["size"] * 2.2))
            dlg = TextEditDialog(self, "Add text", "", st, hint="Type the text. It is placed in the box you drew.")
            if dlg.exec_() == QDialog.Accepted:
                text, st2 = dlg.values()
                if text.strip():
                    self.apply("Text added", pno, ed_add_text, pno, vr, text, st2)
        elif small:
            return
        elif mode == "image":
            path, _ = QFileDialog.getOpenFileName(self, "Choose the picture", SET.last_dir("pdfedit_img"),
                                                  "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)")
            if path:
                SET.remember_dir("pdfedit_img", path)
                self.apply("Picture added", pno, ed_add_image, pno, vr, path)
        elif mode in ("rect", "oval", "line", "arrow"):
            fill = self.fill.currentData()
            if fill == "same":
                fill = self.stroke
            self.apply("%s added" % dict(EDIT_MODES)[mode], pno, ed_shape, pno, mode, p0, p1, self.stroke, fill, float(self.width.value()))
        elif mode == "cover":
            self.apply("Area covered", pno, ed_cover, pno, vr, None, self.remove_under.isChecked())
        elif mode == "link":
            dlg = LinkDialog(self, "uri", "", self.sess.doc.page_count)
            if dlg.exec_() == QDialog.Accepted:
                k, t = dlg.values()
                if k == "uri" and not t.replace("https://", ""):
                    return
                self.apply("Link added", pno, ed_add_link, pno, vr, k, t)

    # ---------------------------------------------------------------- find and replace
    def _pages(self):
        return [self.viewer.current_page()] if self.f_scope.currentIndex() == 1 else None

    def _progress(self, title):
        dlg = QProgressDialog(title, "Cancel", 0, 100, self)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setMinimumDuration(500)

        def cb(i, n):
            dlg.setValue(int(100 * i / max(1, n)))
            QApplication.processEvents()
            return dlg.wasCanceled()
        return dlg, cb

    def find_next(self):
        if not self._need_doc():
            return
        text = self.f_find.text()
        if not text:
            return
        key = (text, self.f_case.isChecked(), self.f_whole.isChecked(), self.f_scope.currentIndex(),
               self.viewer.current_page() if self.f_scope.currentIndex() == 1 else -1, self.sess.changes, len(self.sess.undo))
        if key != self._hits_key:
            dlg, cb = self._progress("Searching...")
            try:
                self.find_hits = ed_find(self.sess.doc, text, key[1], key[2], self._pages(), cb)
            finally:
                dlg.close()
            self._hits_key, self.find_idx = key, -1
        if not self.find_hits:
            self.f_count.setText("No match")
            self.viewer.highlights = {}
            self.viewer.canvas.update()
            return
        self.find_idx = (self.find_idx + 1) % len(self.find_hits)
        self._show_hit()

    def _show_hit(self):
        hl = {}
        for k, (pno, r) in enumerate(self.find_hits):
            hl.setdefault(pno, []).append((r, k == self.find_idx))
        self.viewer.highlights = hl
        pno, r = self.find_hits[self.find_idx]
        vr = fitz.Rect(r) * self.sess.doc[pno].rotation_matrix
        self.viewer.scroll.verticalScrollBar().setValue(max(0, int(self.viewer.offsets[pno] + vr.y0 * self.viewer.zoom - 90)))
        self.f_count.setText("%d / %d" % (self.find_idx + 1, len(self.find_hits)))
        self.viewer.canvas.update()

    def replace_this(self):
        if not self._need_doc():
            return
        if not self.find_hits or self.find_idx < 0:
            self.find_next()
            return
        pno, r = self.find_hits[self.find_idx]
        if self.apply("Replaced 1 match", pno, ed_find_replace, self.f_find.text(), self.f_repl.text(), self.f_case.isChecked(),
                      self.f_whole.isChecked(), [pno], self.f_fit.isChecked(), (pno, r)):
            self._hits_key = None
            self.find_next()

    def replace_all(self):
        if not self._need_doc():
            return
        text = self.f_find.text()
        if not text:
            self.warn("Type the text to find first.")
            return
        dlg, cb = self._progress("Replacing...")
        n = [0]

        def run(doc, *a, **k):
            n[0] = ed_find_replace(doc, *a, **k)
            return ["%d replaced." % n[0]]
        try:
            ok = self.apply("Replace all", None, run, text, self.f_repl.text(), self.f_case.isChecked(), self.f_whole.isChecked(),
                            self._pages(), self.f_fit.isChecked(), None, cb)
        finally:
            dlg.close()
        if ok:
            self.f_count.setText("%d replaced" % n[0])
            if n[0] == 0:
                self.note.setText("Nothing found to replace.")

    # ---------------------------------------------------------------- saving
    def on_success(self, res):
        if self.sess is not None:
            self.sess.saved_mark = getattr(self, "_saving_n", self.sess.changes)
        ToolPage.on_success(self, res)

    def make_task(self, out):
        if not self.sess:
            raise UserError("Choose a PDF file above first.")
        if self.sess.changes <= 0:
            raise UserError("Nothing has been changed yet, so there is nothing to save.")
        data = self.sess.doc.tobytes(garbage=3, deflate=True)       # taken here (GUI thread); the worker only writes bytes
        stem = safe_name(os.path.splitext(os.path.basename(self.sess.path))[0])
        n = self.sess.changes
        self._saving_n = n

        def task(report, cancelled):
            report(30, "Writing the file...")
            dst = unique_path(out, stem + "_edited", ".pdf")
            with open(dst, "wb") as f:
                f.write(data)
            return {"message": "Saved the edited PDF (%d change%s). You can keep editing and save again.\n%s" % (n, "" if n == 1 else "s", dst),
                    "files": [dst]}
        return task



# ---------------------------------------------------------------- properties
class PropertiesTool(ToolPage):
    key, title, group = "properties", "Document Properties", "Edit"
    subtitle = "Edit title, author, subject, keywords and other document information."
    action_text = "Save with new properties"

    KEYS = [("title", "Title"), ("author", "Author"), ("subject", "Subject"), ("keywords", "Keywords"),
            ("creator", "Creator"), ("producer", "Producer")]

    def build(self, L):
        self.pdf = PdfPicker("properties")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.ed = {}
        for k, lab in self.KEYS:
            self.ed[k] = QLineEdit()
            self.add_row(lab, self.ed[k])
        self.pdf.changed.connect(self.fill)

    def fill(self, *a):
        try:
            d = open_pdf(self.pdf.path())
        except UserError:
            return
        md = d.metadata or {}
        for k, _ in self.KEYS:
            self.ed[k].setText(md.get(k) or "")
        d.close()

    def make_task(self, out):
        path = self.pdf.require()
        vals = {k: e.text() for k, e in self.ed.items()}
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            d = open_pdf(path)
            md = dict(d.metadata or {})
            md.update(vals)
            d.set_metadata(md)
            dst = save_pdf(d, unique_path(out, stem + "_props", ".pdf"))
            return {"message": "Properties saved:\n%s" % dst, "files": [dst]}
        return task


# ---------------------------------------------------------------- bookmarks
class BookmarksTool(ToolPage):
    key, title, group = "bookmarks", "Bookmarks Editor", "Edit"
    subtitle = "View, add, rename, re-order and nest bookmarks (the outline in the Contents panel)."
    action_text = "Save with new bookmarks"

    def build(self, L):
        self.pdf = PdfPicker("bookmarks")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Level (1 = top)", "Title", "Page"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(260)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        L.addWidget(self.table)
        row = QHBoxLayout()
        for text, fn in (("Add", self.add), ("Remove", self.rem), ("Up", lambda: self.mv(-1)), ("Down", lambda: self.mv(1)),
                         ("Indent >", lambda: self.lvl(1)), ("< Outdent", lambda: self.lvl(-1)), ("Clear all", lambda: self.table.setRowCount(0))):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        L.addLayout(row)
        self.pdf.changed.connect(self.load)

    def load(self, *a):
        try:
            d = open_pdf(self.pdf.path())
        except UserError:
            return
        self.table.setRowCount(0)
        for lvl, title, pg in d.get_toc():
            self._add(lvl, title, pg)
        d.close()

    def _add(self, lvl, title, pg):
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c, v in enumerate((str(lvl), title, str(pg))):
            self.table.setItem(r, c, QTableWidgetItem(v))

    def add(self):
        r = self.table.currentRow()
        lvl = int(self.table.item(r, 0).text()) if r >= 0 and self.table.item(r, 0) else 1
        self._add(lvl, "New bookmark", 1)

    def rem(self):
        for r in sorted({i.row() for i in self.table.selectedItems()}, reverse=True):
            self.table.removeRow(r)

    def _rowvals(self, r):
        return [self.table.item(r, c).text() if self.table.item(r, c) else "" for c in range(3)]

    def mv(self, d):
        r = self.table.currentRow()
        nr = r + d
        if r < 0 or not (0 <= nr < self.table.rowCount()):
            return
        a, b = self._rowvals(r), self._rowvals(nr)
        for c in range(3):
            self.table.item(r, c).setText(b[c])
            self.table.item(nr, c).setText(a[c])
        self.table.selectRow(nr)

    def lvl(self, d):
        for r in {i.row() for i in self.table.selectedItems()}:
            v = max(1, int(self._rowvals(r)[0] or 1) + d)
            self.table.item(r, 0).setText(str(v))

    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        toc = []
        for r in range(self.table.rowCount()):
            l, t, p = self._rowvals(r)
            try:
                l, p = int(l), int(p)
            except ValueError:
                raise UserError("Row %d: level and page must be numbers." % (r + 1))
            if not (1 <= p <= n):
                raise UserError("Row %d: page %d is outside the document (1-%d)." % (r + 1, p, n))
            if not t.strip():
                raise UserError("Row %d has no title." % (r + 1))
            toc.append([l, t.strip(), p])
        prev = 0
        for e in toc:                              # outline levels may only go one step deeper at a time
            e[0] = max(1, min(e[0], prev + 1))
            prev = e[0]
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            d = open_pdf(path)
            d.set_toc(toc)
            dst = save_pdf(d, unique_path(out, stem + "_bookmarks", ".pdf"))
            return {"message": "%d bookmark(s) saved:\n%s" % (len(toc), dst), "files": [dst]}
        return task


# ---------------------------------------------------------------- strip metadata / attachments
def core_strip(src, dst, opts, report=None):
    doc = open_pdf(src)
    kw = dict(metadata=opts.get("meta", True), xml_metadata=opts.get("meta", True),
              attached_files=opts.get("attach", True), embedded_files=opts.get("attach", True),
              javascript=opts.get("js", True), thumbnails=opts.get("thumbs", True),
              hidden_text=opts.get("hidden", False), clean_pages=True, remove_links=opts.get("links", False),
              reset_fields=False, reset_responses=opts.get("annots", False), redactions=False, redact_images=0)
    try:
        doc.scrub(**kw)
    except TypeError:
        doc.scrub()
    if opts.get("annots"):
        for pg in doc:
            for a in list(pg.annots() or []):
                pg.delete_annot(a)
    if opts.get("bookmarks"):
        doc.set_toc([])
    if opts.get("meta"):
        doc.set_metadata({})
    save_pdf(doc, dst, garbage=4, clean=True)
    doc.close()


class StripTool(ToolPage):
    key, title, group = "strip", "Strip Metadata & Attachments", "Security"
    subtitle = "Remove hidden information before sharing a file."

    def build(self, L):
        self.pdf = PdfPicker("strip")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.cb = {}
        for k, lab, on in (("meta", "Document properties and XMP metadata (author, software, dates)", True),
                           ("attach", "Embedded files and file attachments", True),
                           ("js", "JavaScript", True), ("thumbs", "Embedded thumbnails", True),
                           ("hidden", "Hidden text", False), ("annots", "Annotations / comments", False),
                           ("bookmarks", "Bookmarks", False), ("links", "Links", False)):
            c = QCheckBox(lab)
            c.setChecked(on)
            self.cb[k] = c
            L.addWidget(c)
        self.add_hint("The file is rewritten completely so old removed data does not stay inside. "
                      "For redaction of visible content use the Redaction tool instead.")

    def make_task(self, out):
        path = self.pdf.require()
        pdf_page_count(path)
        opts = {k: c.isChecked() for k, c in self.cb.items()}
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            dst = unique_path(out, stem + "_clean", ".pdf")
            report(30, "Cleaning...")
            core_strip(path, dst, opts)
            return {"message": "Clean copy saved:\n%s" % dst, "files": [dst]}
        return task


# ---------------------------------------------------------------- PDF/A (best effort)
def core_pdfa(src, dst, report=None):
    """Best-effort PDF/A-2b preparation. NOT a validated conversion."""
    doc = open_pdf(src)
    issues = []
    unemb = 0
    for pg in doc:
        for f in pg.get_fonts(full=False):
            if f[1] in ("n/a", ""):
                unemb += 1
    if unemb:
        issues.append("%d font reference(s) are not embedded (PDF/A requires embedded fonts)." % unemb)
    if doc.is_encrypted:
        issues.append("Encrypted files cannot be PDF/A (encryption removed in the copy).")
    try:
        doc.scrub(javascript=True, embedded_files=True, attached_files=True, metadata=False, xml_metadata=False,
                  hidden_text=False, thumbnails=True, remove_links=False, reset_fields=False, reset_responses=False,
                  redactions=False, redact_images=0, clean_pages=True)
    except Exception:
        pass
    md = doc.metadata or {}
    title = (md.get("title") or "").replace("&", "&amp;").replace("<", "&lt;")
    now = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    xmp = ('<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
           '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
           '<rdf:Description rdf:about="" xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/" '
           'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:xmp="http://ns.adobe.com/xap/1.0/">'
           '<pdfaid:part>2</pdfaid:part><pdfaid:conformance>B</pdfaid:conformance>'
           '<dc:title><rdf:Alt><rdf:li xml:lang="x-default">%s</rdf:li></rdf:Alt></dc:title>'
           '<xmp:CreateDate>%s</xmp:CreateDate><xmp:ModifyDate>%s</xmp:ModifyDate>'
           '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>') % (title, now, now)
    doc.set_xml_metadata(xmp)
    if HAVE_PIL:
        try:
            from PIL import ImageCms
            icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
            px = doc.get_new_xref()
            doc.update_object(px, "<< /N 3 /Alternate /DeviceRGB >>")
            doc.update_stream(px, icc, new=True)
            ox = doc.get_new_xref()
            doc.update_object(ox, "<< /Type /OutputIntent /S /GTS_PDFA1 /OutputConditionIdentifier (sRGB) "
                                  "/Info (sRGB IEC61966-2.1) /DestOutputProfile %d 0 R >>" % px)
            doc.xref_set_key(doc.pdf_catalog(), "OutputIntents", "[%d 0 R]" % ox)
        except Exception as e:
            LOG.warning("PDF/A output intent failed: %s", e)
            issues.append("Could not add the colour profile (output intent).")
    else:
        issues.append("Pillow is missing, so no colour profile was added.")
    try:
        doc.subset_fonts()
    except Exception:
        pass
    doc.save(dst, garbage=4, deflate=True, encryption=fitz.PDF_ENCRYPT_NONE)
    doc.close()
    return issues


class PdfaTool(ToolPage):
    key, title, group = "pdfa", "PDF/A (best effort)", "Security"
    subtitle = "Prepare an archive-style PDF/A-2b copy. EXPERIMENTAL - not guaranteed to pass validation."

    def build(self, L):
        self.pdf = PdfPicker("pdfa")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.add_hint("What it does: adds PDF/A identification, an sRGB colour profile, removes JavaScript/attachments and "
                      "embeds nothing new. What it cannot do: embed missing fonts or fix every rule. "
                      "Always check the result with a validator such as veraPDF before relying on it.")

    def make_task(self, out):
        path = self.pdf.require()
        pdf_page_count(path)
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            dst = unique_path(out, stem + "_pdfa", ".pdf")
            report(20, "Preparing...")
            issues = core_pdfa(path, dst)
            msg = "PDF/A-2b preparation done (unvalidated):\n%s" % dst
            if issues:
                msg += "\n\nPossible problems:\n- " + "\n- ".join(issues)
            return {"message": msg, "files": [dst]}
        return task


# ---------------------------------------------------------------- repair
def core_repair(src, dst, report=None):
    if not os.path.isfile(src):
        raise UserError("File not found:\n%s" % src)
    doc = None
    try:
        doc = fitz.open(src)
    except Exception:
        try:
            with open(src, "rb") as f:
                data = f.read()
            i = data.find(b"%PDF")
            if i < 0:
                raise ValueError
            doc = fitz.open(stream=data[i:], filetype="pdf")
        except Exception:
            raise UserError("This file is too badly damaged to read (no PDF structure found).")
    if doc.needs_pass:
        doc.close()
        raise UserError("This PDF is password-protected. Remove the password first.")
    new = fitz.open()
    bad = []
    n = doc.page_count
    for i in range(n):
        try:
            new.insert_pdf(doc, from_page=i, to_page=i)
        except Exception:
            bad.append(i + 1)
        if report and i % 10 == 0:
            report(5 + 85 * i / max(1, n), "Rebuilding page %d of %d" % (i + 1, n))
    if new.page_count == 0:
        raise UserError("No readable pages could be recovered.")
    try:
        new.set_toc(doc.get_toc())
    except Exception:
        pass
    new.save(dst, garbage=4, clean=True, deflate=True)
    return n, new.page_count, bad


class RepairTool(ToolPage):
    key, title, group = "repair", "Repair PDF", "Security"
    subtitle = "Try to rebuild a damaged PDF into a clean new file."

    def build(self, L):
        self.file = FilePicker("repair")
        self.add_row("PDF file", self.file)
        self.add_hint("The damaged original is never changed. Pages that cannot be read are skipped and listed.")

    def make_task(self, out):
        p = self.file.path()
        if not p:
            raise UserError("Please choose a PDF file first.")
        stem = safe_name(os.path.splitext(os.path.basename(p))[0])

        def task(report, cancelled):
            dst = unique_path(out, stem + "_repaired", ".pdf")
            n, ok, bad = core_repair(p, dst, report)
            msg = "Recovered %d of %d pages:\n%s" % (ok, n, dst)
            if bad:
                msg += "\n\nUnreadable pages that were skipped: " + ", ".join(map(str, bad))
            return {"message": msg, "files": [dst]}
        return task


# ---------------------------------------------------------------- compare
class CompareTool(ToolPage):
    key, title, group = "compare", "Compare Two PDFs", "Edit"
    subtitle = "Find differences: an HTML text comparison plus a visual overlay PDF (red = only in A, blue = only in B)."

    def build(self, L):
        self.a = PdfPicker("compareA")
        self.b = PdfPicker("compareB")
        self.add_row("Original PDF (A)", self.a)
        L.addWidget(self.a.info)
        self.add_row("Changed PDF (B)", self.b)
        L.addWidget(self.b.info)
        self.dpi = self.combo(["72", "100", "150"], "100")
        L.addWidget(hbox(QLabel("Overlay resolution (DPI)"), self.dpi, None))

    def make_task(self, out):
        pa, pb = self.a.require(), self.b.require()
        if not (HAVE_PIL and HAVE_NP):
            raise UserError("Comparison needs Pillow and numpy. Run:  pip install Pillow numpy")
        dpi = int(self.dpi.currentText())

        def task(report, cancelled):
            A, B = open_pdf(pa), open_pdf(pb)
            na, nb = A.page_count, B.page_count
            m = min(na, nb)
            hd = difflib.HtmlDiff(wrapcolumn=80)
            body, changed_pages = [], []
            rep = fitz.open()
            for i in range(m):
                report(5 + 85 * i / m, "Comparing page %d of %d" % (i + 1, m))
                ta = A[i].get_text("text").splitlines()
                tb = B[i].get_text("text").splitlines()
                if ta != tb:
                    body.append("<h3>Page %d</h3>" % (i + 1) + hd.make_table(ta, tb, "A", "B", context=True, numlines=2))
                pa_ = A[i].get_pixmap(dpi=dpi, colorspace=fitz.csGRAY, alpha=False)
                pb_ = B[i].get_pixmap(dpi=dpi, colorspace=fitz.csGRAY, alpha=False)
                ia = np.frombuffer(pa_.samples, np.uint8).reshape(pa_.h, pa_.w)
                ib = Image.fromarray(np.frombuffer(pb_.samples, np.uint8).reshape(pb_.h, pb_.w))
                if ib.size != (pa_.w, pa_.h):
                    ib = ib.resize((pa_.w, pa_.h))
                ib = np.asarray(ib)
                da, db = ia < 140, ib < 140
                only_a, only_b, both = da & ~db, db & ~da, da & db
                rgb = np.full((pa_.h, pa_.w, 3), 255, np.uint8)
                rgb[both] = (110, 110, 110)
                rgb[only_a] = (214, 40, 57)
                rgb[only_b] = (31, 79, 191)
                frac = (only_a.sum() + only_b.sum()) / float(max(1, (da | db).sum()))
                if frac > 0.002:
                    changed_pages.append(i + 1)
                buf = io.BytesIO()
                Image.fromarray(rgb).save(buf, "PNG")
                pg = rep.new_page(width=pa_.w * 72.0 / dpi, height=pa_.h * 72.0 / dpi)
                pg.insert_image(pg.rect, stream=buf.getvalue())
                pg.insert_text((10, 14), "Page %d  (red = only in A, blue = only in B, grey = same)" % (i + 1), fontsize=8, color=(0, 0, 0))
            summary = "Pages: A=%d, B=%d.\nPages with visible differences: %s" % (
                na, nb, ", ".join(map(str, changed_pages)) or "none")
            if na != nb:
                summary += "\nThe documents have a different number of pages; only the first %d were compared." % m
            files = []
            if rep.page_count:
                files.append(save_pdf(rep, unique_path(out, "compare_overlay", ".pdf")))
            html = unique_path(out, "compare_text", ".html")
            with open(html, "w", encoding="utf-8") as f:
                f.write("<html><meta charset='utf-8'><body><h2>Text comparison</h2><pre>%s</pre>%s</body></html>" % (
                    summary, "".join(body) or "<p>No text differences found.</p>"))
            files.append(html)
            return {"message": summary + "\n\nReports saved in the output folder.", "files": files}
        return task
# ============================================================================
#  SECTION H - PHASE 3 TOOLS (part 1): conversions and content extraction
# ============================================================================
SCANNED_WARNING = ("Note: pages that are pictures (scans) contain no real text. Run OCR first "
                   "(Convert > OCR) if the result comes out empty.")


def pdf_text_sample(path, pages=3):
    d = open_pdf(path)
    t = "".join(d[i].get_text("text") for i in range(min(pages, d.page_count)))
    d.close()
    return t.strip()


def need_lib(flag, pipname, what):
    if not flag:
        raise UserError("%s needs an extra library that is not installed.\nOpen a Command Prompt and run:\n  pip install %s" % (what, pipname))


class PdfToWordTool(ToolPage):
    key, title, group = "pdf2word", "PDF to Word", "Convert"
    subtitle = "Convert a PDF to an editable Word (.docx) document."

    def build(self, L):
        self.pdf = PdfPicker("pdf2word")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("blank = all pages  |  e.g. 1-5")
        self.add_row("Pages", self.pages)
        self.add_hint(SCANNED_WARNING + " Complex layouts may need manual tidy-up in Word. Cancel takes effect after the conversion step.")

    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        pages = pages_from_text(self.pages.text(), n)
        a, b = min(pages), max(pages)
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])
        if not pdf_text_sample(path):
            r = QMessageBox.question(self, APP_NAME, "The first pages contain no selectable text - this looks like a scanned PDF.\n"
                                     "The Word file will probably be empty. Continue anyway?")
            if r != QMessageBox.Yes:
                return None

        def task(report, cancelled):
            try:
                from pdf2docx import Converter
            except ImportError:
                raise UserError("PDF to Word needs the pdf2docx library.\nRun:  pip install pdf2docx")
            dst = unique_path(out, stem, ".docx")
            report(10, "Converting (this can take a while for big files)...")
            cv = Converter(path)
            try:
                cv.convert(dst, start=a, end=b + 1)
            finally:
                cv.close()
            return {"message": "Word document saved:\n%s" % dst, "files": [dst]}
        return task


def _cell_value(s, convert):
    if s is None:
        return ""
    s = str(s).replace("\n", " ").strip()
    if convert:
        t = s.replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
        if re.fullmatch(r"-?\d+(\.\d+)?", t) and not (len(t.lstrip("-")) > 1 and t.lstrip("-").startswith("0") and "." not in t):
            try:
                return float(t) if "." in t else int(t)
            except ValueError:
                return s
    return s


def table_rows(page, t):
    """Cell texts read straight from each cell rectangle (more reliable than Table.extract for punctuation)."""
    try:
        rows = []
        for row in t.rows:
            rows.append([(" ".join(page.get_textbox(fitz.Rect(c)).split()) if c else "") for c in row.cells])
        return rows
    except Exception:
        return t.extract()


def collect_tables(doc, pages, report=None):
    res = []
    for k, p in enumerate(pages):
        try:
            tabs = doc[p].find_tables()
            for ti, t in enumerate(tabs.tables):
                rows = table_rows(doc[p], t)
                if rows:
                    res.append((p, ti, rows))
        except Exception as e:
            LOG.warning("find_tables page %d: %s", p + 1, e)
        if report and k % 3 == 0:
            report(5 + 60 * k / len(pages), "Looking for tables on page %d" % (p + 1))
    return res


class PdfToExcelTool(ToolPage):
    key, title, group = "pdf2excel", "PDF to Excel", "Convert"
    subtitle = "Find tables in a PDF and save them to Excel (.xlsx)."

    def build(self, L):
        self.pdf = PdfPicker("pdf2excel")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("blank = all pages")
        self.add_row("Pages", self.pages)
        self.mode = self.combo([("One sheet per table", "table"), ("One sheet per page", "page"), ("All tables on one sheet", "all")])
        self.add_row("Layout", self.mode)
        self.num = QCheckBox("Turn numbers like 1,23,456.00 or Rs. 500 into real numbers")
        self.num.setChecked(True)
        L.addWidget(self.num)
        self.add_hint(SCANNED_WARNING + " Only tables with a clear grid or aligned text are detected.")

    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        pages = pages_from_text(self.pages.text(), n)
        need_lib(HAVE_XLSX, "openpyxl", "PDF to Excel")
        mode, conv = self.mode.currentData(), self.num.isChecked()
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            doc = open_pdf(path)
            tabs = collect_tables(doc, pages, report)
            if not tabs:
                return {"message": "No tables were found in the selected pages.\n" + SCANNED_WARNING, "files": []}
            wb = openpyxl.Workbook()
            wb.remove(wb.active)
            ws = None
            lastpage = None
            for (p, ti, rows) in tabs:
                if mode == "table":
                    ws = wb.create_sheet("p%d_t%d" % (p + 1, ti + 1))
                    r0 = 1
                elif mode == "page":
                    if p != lastpage:
                        ws = wb.create_sheet("Page %d" % (p + 1))
                    r0 = ws.max_row + (2 if ws.max_row > 1 else 0)
                else:
                    if ws is None:
                        ws = wb.create_sheet("Tables")
                    r0 = ws.max_row + (2 if ws.max_row > 1 else 0)
                lastpage = p
                for ri, row in enumerate(rows):
                    for ci, v in enumerate(row):
                        ws.cell(row=r0 + ri, column=ci + 1, value=_cell_value(v, conv))
            dst = unique_path(out, stem, ".xlsx")
            wb.save(dst)
            return {"message": "Saved %d table(s) to Excel:\n%s" % (len(tabs), dst), "files": [dst]}
        return task


# ---------------------------------------------------------------- PDF -> editable PowerPoint
_PPT_FONT_MAP = [("arial", "Arial"), ("helvetica", "Arial"), ("helv", "Arial"), ("timesnewroman", "Times New Roman"), ("times", "Times New Roman"),
                 ("tiro", "Times New Roman"), ("couriernew", "Courier New"), ("courier", "Courier New"), ("cour", "Courier New"),
                 ("calibri", "Calibri"), ("cambria", "Cambria"), ("verdana", "Verdana"), ("tahoma", "Tahoma"), ("georgia", "Georgia"),
                 ("segoeui", "Segoe UI"), ("garamond", "Garamond"), ("bookantiqua", "Book Antiqua"), ("centurygothic", "Century Gothic"),
                 ("trebuchet", "Trebuchet MS"), ("bookmanoldstyle", "Bookman Old Style"), ("palatino", "Palatino Linotype"),
                 ("consolas", "Consolas"), ("candara", "Candara"), ("corbel", "Corbel"), ("constantia", "Constantia"), ("symbol", "Symbol"),
                 ("nirmala", "Nirmala UI"), ("mangal", "Mangal"), ("notosansdevanagari", "Nirmala UI"), ("notosans", "Noto Sans"),
                 ("dejavusans", "DejaVu Sans"), ("liberationsans", "Arial"), ("liberationserif", "Times New Roman"), ("freeserif", "Times New Roman")]
_INDIC_RE = re.compile(u"[ऀ-෿]")
_XML_BAD_RE = re.compile(u"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


def ppt_font_name(pdf_font):
    n = (pdf_font or "").split("+")[-1]
    key = re.sub(r"[^a-z]", "", n.lower())
    for k, v in _PPT_FONT_MAP:
        if key.startswith(k):
            return v
    n = re.split(r"[-,]", n)[0]
    n = re.sub(r"(PS)?MT$|PS$", "", n)
    n = re.sub(r"(Bold|Italic|Oblique|Regular|Medium|Light|Semibold|SemiBold|Roman|Book)+$", "", n)
    n = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", n).strip()
    return n or "Arial"


def _ppt_lines(page, mat):
    """Text lines of a page in DISPLAYED coordinates: dicts with rect, angle, size, spans [(text, font, size, bold, italic, rgb)]."""
    out = []
    try:
        d = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    except Exception:
        return out
    for bi, b in enumerate(d.get("blocks", [])):
        if b.get("type") != 0:
            continue
        for ln in b.get("lines", []):
            spans = []
            for sp in ln.get("spans", []):
                t = _XML_BAD_RE.sub("", sp.get("text", ""))
                if not t:
                    continue
                fl = sp.get("flags", 0)
                fname = sp.get("font", "")
                low = fname.lower()
                spans.append((t, ppt_font_name(fname), float(sp.get("size", 10)), bool(fl & 16) or "bold" in low or "black" in low,
                              bool(fl & 2) or "italic" in low or "oblique" in low, int(sp.get("color", 0)) & 0xFFFFFF))
            if not spans or not "".join(s[0] for s in spans).strip():
                continue
            while spans and not spans[-1][0].strip():
                spans.pop()
            dx, dy = ln.get("dir", (1.0, 0.0))
            v = fitz.Point(dx, dy) * fitz.Matrix(mat.a, mat.b, mat.c, mat.d, 0, 0)
            ang = math.degrees(math.atan2(v.y, v.x))
            r = fitz.Rect(ln["bbox"]) * mat
            r.normalize()
            if r.width < 0.5 or r.height < 0.5:
                continue
            size = max(s[2] for s in spans)
            out.append({"rect": r, "angle": ang, "size": size, "spans": spans, "block": bi})
    return out


def _ppt_groups(lines):
    """Join the lines of one paragraph / cell into a group so that it becomes ONE editable text box."""
    groups, cur = [], None
    for ln in lines:
        if abs(ln["angle"]) > 2.0:
            groups.append({"lines": [ln], "rot": True})
            cur = None
            continue
        ok = False
        if cur is not None and cur["block"] == ln["block"]:
            prev, gr = cur["lines"][-1], cur["rect"]
            step = ln["rect"].y0 - prev["rect"].y0
            ov = min(gr.x1, ln["rect"].x1) - max(gr.x0, ln["rect"].x0)
            ok = (0.55 * prev["size"] <= step <= 2.3 * prev["size"] and ov > 0.3 * min(gr.width, ln["rect"].width)
                  and abs(ln["size"] - prev["size"]) <= 0.2 * prev["size"])
        if ok:
            cur["lines"].append(ln)
            cur["rect"] |= ln["rect"]
        else:
            cur = {"lines": [ln], "rect": fitz.Rect(ln["rect"]), "block": ln["block"], "rot": False}
            groups.append(cur)
    return groups


_BULLET_RE = re.compile(u"^\\s*([\u00b7\u2022\u25cf\u25aa\u25e6\u2023\u2043\\-\u2013\\*]|\\(?[0-9a-zA-Z]{1,3}[.)])\\s+")


def _ppt_paragraphs(g):
    """[(lines, align)] - wrapped lines are merged so the text re-flows when it is edited in PowerPoint."""
    ls, r = g["lines"], g["rect"]
    if len(ls) == 1:
        return [[ls[0]]], "l"
    lefts = [abs(l["rect"].x0 - r.x0) for l in ls]
    rights = [abs(r.x1 - l["rect"].x1) for l in ls]
    mids = [abs((l["rect"].x0 + l["rect"].x1) / 2 - (r.x0 + r.x1) / 2) for l in ls]
    tol = max(1.5, 0.25 * ls[0]["size"])
    align = "l"
    if max(lefts) > tol * 2:
        if max(mids) <= tol * 1.5:
            align = "c"
        elif max(rights) <= tol:
            align = "r"
    paras, cur = [], [ls[0]]
    for prev, ln in zip(ls, ls[1:]):
        full = (r.x1 - prev["rect"].x1) <= max(2.5 * prev["size"], 0.12 * r.width)
        txt = "".join(s[0] for s in ln["spans"])
        indent = align == "l" and (ln["rect"].x0 - prev["rect"].x0) > 0.9 * ln["size"]
        if align == "l" and full and not _BULLET_RE.match(txt) and not indent:
            cur.append(ln)
        else:
            paras.append(cur)
            cur = [ln]
    paras.append(cur)
    return paras, align


def _ppt_add_runs(par, lines, k):
    from pptx.util import Pt
    from pptx.dml.color import RGBColor
    from pptx.oxml.ns import qn
    for i, ln in enumerate(lines):
        spans = list(ln["spans"])
        if i < len(lines) - 1:
            last = spans[-1][0]
            if not last.endswith((" ", "-", u"­")):
                spans[-1] = (last + " ",) + tuple(spans[-1][1:])
        for t, fnt, size, bold, ital, rgb in spans:
            run = par.add_run()
            run.text = t
            f = run.font
            f.size = Pt(max(1.0, round(size * k * 2) / 2.0))
            f.bold, f.italic = bool(bold), bool(ital)
            f.color.rgb = RGBColor((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255)
            if _INDIC_RE.search(t):
                rPr = run._r.get_or_add_rPr()
                for tag in ("a:latin", "a:cs"):
                    el = rPr.makeelement(qn(tag), {"typeface": "Nirmala UI"})
                    rPr.append(el)
            else:
                f.name = fnt


def _ppt_picture_bytes(doc, xref):
    """(bytes) of an embedded picture in a form PowerPoint accepts, or None."""
    try:
        info = doc.extract_image(xref)
        if not info or not info.get("image"):
            return None
        sm = info.get("smask") or 0
        if not sm and info.get("ext") in ("png", "jpeg") and info.get("colorspace") in (1, 3):
            return info["image"]
        pix = fitz.Pixmap(doc, xref)
        if pix.colorspace is None:
            return None
        if pix.alpha:
            pix = fitz.Pixmap(pix, 0)
        if pix.colorspace.n not in (1, 3):
            pix = fitz.Pixmap(fitz.csRGB, pix)
        if sm:
            try:
                mask = fitz.Pixmap(doc, sm)
                if (mask.width, mask.height) == (pix.width, pix.height) and mask.n == 1:
                    pix = fitz.Pixmap(pix, mask)
            except Exception:
                pass
        return pix.tobytes("png")
    except Exception:
        return None


def _ppt_is_scan(page, lines):
    """A page that is one big picture (a scan, with or without a hidden OCR text layer)."""
    try:
        area = abs(page.rect)
        big = 0.0
        for it in page.get_image_info():
            big = max(big, abs(fitz.Rect(it["bbox"])))
        return area > 0 and min(big, area) / area >= 0.80
    except Exception:
        return False


def pdf_page_to_slide(doc, pno, prs, slide, dpi=150, ocr_lang=None, stats=None):
    """Fill one slide with EDITABLE content of one PDF page: background drawing (lines, tables, shapes) as a picture at the
    back, each embedded picture as its own picture, each paragraph as a real text box."""
    from pptx.util import Emu, Pt
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
    stats = stats if stats is not None else {}
    E = 12700.0
    page = doc[pno]
    pr = fitz.Rect(page.rect)
    SW, SH = prs.slide_width / E, prs.slide_height / E
    k = min(SW / pr.width, SH / pr.height)
    ox, oy = (SW - pr.width * k) / 2.0, (SH - pr.height * k) / 2.0
    mat = fitz.Matrix(page.rotation_matrix) if page.rotation else fitz.Matrix(1, 0, 0, 1, 0, 0)

    def emu(v):
        return Emu(int(round(v * E)))

    def place(r):
        return emu(ox + r.x0 * k), emu(oy + r.y0 * k), emu(max(1.0, r.width * k)), emu(max(1.0, r.height * k))
    lines = _ppt_lines(page, mat)
    if _ppt_is_scan(page, lines):
        pix = page.get_pixmap(dpi=max(dpi, 150), alpha=False)
        slide.shapes.add_picture(io.BytesIO(pix.tobytes("jpeg", jpg_quality=90) if pix.width * pix.height > 3000000 else pix.tobytes("png")),
                                 emu(ox), emu(oy), emu(pr.width * k), emu(pr.height * k))
        text = "\n".join("".join(s[0] for s in l["spans"]) for l in lines).strip()
        if not text and ocr_lang:
            try:
                text = ocr_page_text(page, ocr_lang, 250).strip()
                stats["ocr"] = stats.get("ocr", 0) + 1
            except Exception as e:
                LOG.warning("ppt ocr failed: %s", type(e).__name__)
        if text:
            slide.notes_slide.notes_text_frame.text = _XML_BAD_RE.sub("", text)
        stats["scan"] = stats.get("scan", 0) + 1
        return
    # ---- background: the page without its text and without the pictures that become separate objects
    pics = []
    tmp = fitz.open()
    try:
        tmp.insert_pdf(doc, from_page=pno, to_page=pno)
        tp = tmp[0]
        if not page.rotation:
            seen = set()
            for it in page.get_image_info(xrefs=True):
                x, tr = it.get("xref") or 0, it.get("transform") or (1, 0, 0, 1, 0, 0)
                r = fitz.Rect(it["bbox"])
                if x <= 0 or x in seen or r.width < 2 or r.height < 2 or abs(tr[1]) > 0.01 * abs(tr[0]) or abs(tr[2]) > 0.01 * abs(tr[3]) or tr[0] <= 0 or tr[3] <= 0:
                    continue
                if not pr.contains(r + (-2, -2, 2, 2)) and abs(r & pr) < 0.9 * abs(r):
                    continue                                      # cropped by the page edge - keep it in the background
                seen.add(x)
                data = _ppt_picture_bytes(doc, x)
                if data:
                    pics.append((r, data, x))
            names = {}
            for im in tp.get_images(full=True):
                names[im[7]] = im[0]
            src_names = {im[0]: im[7] for im in page.get_images(full=True)}
            for r, data, x in pics:
                tx = names.get(src_names.get(x))
                if tx:
                    try:
                        tp.delete_image(tx)
                    except Exception:
                        pass
        if lines:
            try:
                tp.add_redact_annot(fitz.Rect(tp.rect) * tp.derotation_matrix if tp.rotation else tp.rect, fill=False)
                tp.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=getattr(fitz, "PDF_REDACT_LINE_ART_NONE", 0),
                                    text=getattr(fitz, "PDF_REDACT_TEXT_REMOVE", 0))
            except TypeError:
                tp.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
        bg = tp.get_pixmap(dpi=dpi, alpha=False)
        blank = False
        try:
            blank = bg.is_unicolor and tuple(bg.pixel(0, 0))[:3] == (255, 255, 255)
        except Exception:
            pass
        if not blank:
            slide.shapes.add_picture(io.BytesIO(bg.tobytes("png")), emu(ox), emu(oy), emu(pr.width * k), emu(pr.height * k))
            stats["bg"] = stats.get("bg", 0) + 1
    finally:
        tmp.close()
    for r, data, x in pics:
        try:
            slide.shapes.add_picture(io.BytesIO(data), *place(r))
            stats["pics"] = stats.get("pics", 0) + 1
        except Exception as e:
            LOG.warning("ppt picture skipped: %s", type(e).__name__)
    # ---- text boxes
    for g in _ppt_groups(lines):
        if g["rot"]:
            ln = g["lines"][0]
            r, ang = ln["rect"], ln["angle"]
            length = max(r.width, r.height) if abs(abs(ang) - 90) < 45 else math.hypot(r.width, r.height) if abs(ang) % 90 > 5 else r.width
            hgt = ln["size"] * 1.25
            cx, cy = (r.x0 + r.x1) / 2.0, (r.y0 + r.y1) / 2.0
            box = slide.shapes.add_textbox(emu(ox + (cx - length / 2.0) * k), emu(oy + (cy - hgt / 2.0) * k), emu(length * k * 1.03), emu(hgt * k))
            box.rotation = ang % 360
            paras, align, wrap = [[ln]], "l", False
        else:
            paras, align = _ppt_paragraphs(g)
            r = g["rect"]
            wrap = any(len(p) > 1 for p in paras)
            pad = 0.02 * r.width + 1.0
            x0 = r.x0 - (pad if align == "r" else pad / 2.0 if align == "c" else 0)
            box = slide.shapes.add_textbox(emu(ox + x0 * k), emu(oy + r.y0 * k), emu((r.width + pad + (0 if wrap else 0.04 * r.width + 2)) * k),
                                           emu(max(r.height, g["lines"][0]["size"] * 1.2) * k))
        tf = box.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.word_wrap = bool(wrap)
        tf.auto_size = MSO_AUTO_SIZE.NONE
        tf.vertical_anchor = MSO_ANCHOR.TOP
        ls = g["lines"]
        pitch = None
        if len(ls) > 1:
            steps = [b["rect"].y0 - a["rect"].y0 for a, b in zip(ls, ls[1:])]
            pitch = sorted(steps)[len(steps) // 2]
        for i, pl in enumerate(paras):
            par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            par.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
            if pitch and pitch > 0:
                par.line_spacing = Pt(max(1.0, round(pitch * k * 4) / 4.0))
            _ppt_add_runs(par, pl, k)
        stats["boxes"] = stats.get("boxes", 0) + 1


def core_pdf_to_pptx(path, dst, pages, mode="edit", dpi=150, ocr_lang=None, report=None, cancelled=None):
    from pptx.util import Emu
    doc = open_pdf(path)
    stats = {}
    try:
        prs = pypptx.Presentation()
        r = doc[pages[0]].rect
        sc = min(1.0, 4000.0 / max(r.width, r.height))                 # PowerPoint allows slides up to 56 inches
        prs.slide_width, prs.slide_height = Emu(int(max(72, r.width * sc) * 12700)), Emu(int(max(72, r.height * sc) * 12700))
        blank = prs.slide_layouts[6]
        for n, p in enumerate(pages):
            if cancelled and cancelled():
                raise Cancelled()
            if report:
                report(5 + 88.0 * n / len(pages), "Slide %d of %d" % (n + 1, len(pages)))
            s = prs.slides.add_slide(blank)
            done = False
            if mode == "edit":
                try:
                    pdf_page_to_slide(doc, p, prs, s, dpi, ocr_lang, stats)
                    done = True
                except Cancelled:
                    raise
                except Exception as e:
                    LOG.warning("editable slide failed on page %d: %s", p + 1, type(e).__name__)
                    stats["fallback"] = stats.get("fallback", 0) + 1
                    for sh in list(s.shapes):
                        sh._element.getparent().remove(sh._element)
            if not done:
                pg = doc[p]
                pix = pg.get_pixmap(dpi=dpi, alpha=False)
                E = 12700.0
                kk = min(prs.slide_width / E / pg.rect.width, prs.slide_height / E / pg.rect.height)
                w, h = pg.rect.width * kk, pg.rect.height * kk
                s.shapes.add_picture(io.BytesIO(pix.tobytes("png")), Emu(int((prs.slide_width / E - w) / 2 * E)),
                                     Emu(int((prs.slide_height / E - h) / 2 * E)), Emu(int(w * E)), Emu(int(h * E)))
        prs.save(dst)
    finally:
        doc.close()
    return stats


class PdfToPptTool(ToolPage):
    key, title, group = "pdf2ppt", "PDF to PowerPoint", "Convert"
    subtitle = "One slide per page with real, editable text boxes and separate pictures - or an exact picture of each page."

    def build(self, L):
        self.pdf = PdfPicker("pdf2ppt")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.mode = self.combo([("Editable slides - text you can change, pictures you can move (recommended)", "edit"),
                                ("Exact picture of each page (not editable)", "pic")])
        self.mode.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.mode.setMinimumContentsLength(30)
        self.add_row("Result", self.mode)
        self.dpi = self.combo(["100", "150", "200", "300"], "150")
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("blank = all pages")
        L.addWidget(hbox(QLabel("Picture quality (DPI)"), self.dpi, QLabel("Pages"), self.pages))
        self.ocr = QCheckBox("Scanned pages: read the text with OCR and put it in the slide notes")
        self.ocr.setChecked(True)
        self.lang = self.combo(tess_langs() or ["eng"], "eng")
        L.addWidget(hbox(self.ocr, QLabel("Language"), self.lang, None))
        self.add_hint("Editable slides: every paragraph becomes a text box with its font, size, colour, bold and italic. Lines, tables and "
                      "shapes stay as a background picture so the layout looks the same. Scanned pages have no real text, so they stay a "
                      "picture (their text goes to the notes). Fonts not installed on your PC are replaced by PowerPoint, which can "
                      "move text slightly.")

    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        pages = pages_from_text(self.pages.text(), n)
        need_lib(HAVE_PPTX, "python-pptx", "PDF to PowerPoint")
        dpi, mode = int(self.dpi.currentText()), self.mode.currentData()
        lang = self.lang.currentText() if (self.ocr.isChecked() and HAVE_PYTESS and HAVE_PIL and tess_ready()) else None
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            dst = unique_path(out, stem, ".pptx")
            st = core_pdf_to_pptx(path, dst, pages, mode, dpi, lang, report, cancelled)
            msg = "PowerPoint saved (%d slides):\n%s" % (len(pages), dst)
            if mode == "edit":
                msg += "\n\nEditable text boxes: %d     Separate pictures: %d" % (st.get("boxes", 0), st.get("pics", 0))
                if st.get("scan"):
                    msg += "\nScanned pages kept as pictures: %d%s" % (st["scan"], " (text is in the slide notes)" if (lang or st.get("ocr")) else
                                                                      " - install Tesseract OCR to get their text in the notes")
                if st.get("fallback"):
                    msg += "\nPages that could only be placed as a picture: %d" % st["fallback"]
            return {"message": msg, "files": [dst]}
        return task


def page_to_markdown(page, body):
    d = page.get_text("dict")
    out = []
    for b in d.get("blocks", []):
        if b.get("type") != 0:
            continue
        lines = []
        head = 0
        for ln in b["lines"]:
            parts = []
            for sp in ln["spans"]:
                t = sp["text"]
                if not t.strip():
                    parts.append(t)
                    continue
                bold = bool(sp["flags"] & 16) or "bold" in sp["font"].lower()
                parts.append("**%s**" % t.strip() if bold and len(ln["spans"]) > 1 else t)
                if sp["size"] >= body * 1.6:
                    head = max(head, 1)
                elif sp["size"] >= body * 1.3:
                    head = max(head, 2)
                elif sp["size"] >= body * 1.12:
                    head = max(head, 3)
            lines.append("".join(parts).strip())
        text = " ".join(l for l in lines if l)
        if not text:
            continue
        if head and len(text) < 140:
            out.append("#" * head + " " + text.replace("**", ""))
        elif re.match(r"^[•●▪\-–*]\s+", text):
            out.append("- " + re.sub(r"^[•●▪\-–*]\s+", "", text))
        else:
            out.append(text)
    return "\n\n".join(out)


def doc_body_size(doc):
    cnt = collections.Counter()
    for i in range(min(doc.page_count, 15)):
        for b in doc[i].get_text("dict").get("blocks", []):
            if b.get("type") == 0:
                for ln in b["lines"]:
                    for sp in ln["spans"]:
                        cnt[round(sp["size"])] += len(sp["text"])
    return float(cnt.most_common(1)[0][0]) if cnt else 11.0


class PdfToTextTool(ToolPage):
    key, title, group = "pdf2text", "PDF to Text / Markdown / HTML", "Convert"
    subtitle = "Pull the text out of a PDF as plain text, Markdown or HTML."

    def build(self, L):
        self.pdf = PdfPicker("pdf2text")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.fmt = self.combo([("Plain text (.txt)", "txt"), ("Markdown (.md)", "md"), ("HTML (.html)", "html")])
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("blank = all pages")
        L.addWidget(hbox(QLabel("Format"), self.fmt, QLabel("Pages"), self.pages))
        self.add_hint(SCANNED_WARNING + " Markdown headings are guessed from font sizes, so check the result.")

    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        pages = pages_from_text(self.pages.text(), n)
        fmt = self.fmt.currentData()
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            doc = open_pdf(path)
            parts = []
            body = doc_body_size(doc) if fmt == "md" else 11
            for k, p in enumerate(pages):
                report(5 + 85 * k / len(pages), "Page %d" % (p + 1))
                pg = doc[p]
                if fmt == "txt":
                    parts.append("----- Page %d -----\n%s" % (p + 1, pg.get_text("text")))
                elif fmt == "md":
                    parts.append("<!-- Page %d -->\n\n%s" % (p + 1, page_to_markdown(pg, body)))
                else:
                    parts.append("<div class='page'><h4>Page %d</h4>%s</div>" % (p + 1, pg.get_text("xhtml")))
            data = "\n\n".join(parts)
            if fmt == "html":
                data = "<!DOCTYPE html><html><head><meta charset='utf-8'><title>%s</title></head><body>%s</body></html>" % (stem, data)
            if not re.sub(r"[-\s<>!\w]*Page \d+[-\s>]*", "", data).strip():
                return {"message": "No text found - this PDF seems to be scanned. Use OCR first.", "files": []}
            dst = unique_path(out, stem, "." + fmt)
            with open(dst, "w", encoding="utf-8") as f:
                f.write(data)
            return {"message": "Saved:\n%s" % dst, "files": [dst]}
        return task


class ExtractContentTool(ToolPage):
    key, title, group = "extractc", "Extract Text, Images, Tables, Links", "Convert"
    subtitle = "Save the pieces inside a PDF: text per page, embedded pictures, tables (CSV) and links (CSV)."

    def build(self, L):
        self.pdf = PdfPicker("extractc")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        self.cb = {}
        for k, lab in (("text", "Text (one .txt file per page)"), ("images", "Embedded images"), ("tables", "Tables (one CSV per table)"),
                       ("links", "Links (CSV list)")):
            c = QCheckBox(lab)
            c.setChecked(k in ("text", "images"))
            self.cb[k] = c
            L.addWidget(c)
        self.minpx = self.spin(1, 2000, 50, " px")
        L.addWidget(hbox(QLabel("Ignore images smaller than"), self.minpx, None))
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("blank = all pages")
        self.add_row("Pages", self.pages)

    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        pages = pages_from_text(self.pages.text(), n)
        want = {k: c.isChecked() for k, c in self.cb.items()}
        if not any(want.values()):
            raise UserError("Tick at least one thing to extract.")
        minpx = self.minpx.value()
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            doc = open_pdf(path)
            folder = unique_dir(out, stem + "_extracted")
            counts = collections.Counter()
            seen = set()
            links = []
            for k, p in enumerate(pages):
                report(3 + 92 * k / len(pages), "Page %d" % (p + 1))
                pg = doc[p]
                if want["text"]:
                    with open(os.path.join(folder, "page_%03d.txt" % (p + 1)), "w", encoding="utf-8") as f:
                        f.write(pg.get_text("text"))
                    counts["text"] += 1
                if want["images"]:
                    for im in pg.get_images(full=True):
                        xref, smask = im[0], im[1]
                        if xref in seen or im[2] < minpx or im[3] < minpx:
                            continue
                        seen.add(xref)
                        try:
                            if smask:
                                pix = fitz.Pixmap(doc, xref)
                                if pix.n - pix.alpha > 3:
                                    pix = fitz.Pixmap(fitz.csRGB, pix)
                                pix = fitz.Pixmap(pix, fitz.Pixmap(doc, smask))
                                pix.save(os.path.join(folder, "p%03d_img%d.png" % (p + 1, xref)))
                            else:
                                d = doc.extract_image(xref)
                                with open(os.path.join(folder, "p%03d_img%d.%s" % (p + 1, xref, d["ext"])), "wb") as f:
                                    f.write(d["image"])
                            counts["images"] += 1
                        except Exception as e:
                            LOG.warning("image extract failed: %s", e)
                if want["tables"]:
                    try:
                        for ti, t in enumerate(pg.find_tables().tables):
                            with open(os.path.join(folder, "p%03d_table%d.csv" % (p + 1, ti + 1)), "w", encoding="utf-8-sig", newline="") as f:
                                csv.writer(f).writerows(table_rows(pg, t))
                            counts["tables"] += 1
                    except Exception as e:
                        LOG.warning("tables failed: %s", e)
                if want["links"]:
                    for l in pg.get_links():
                        txt = pg.get_textbox(fitz.Rect(l["from"])).strip().replace("\n", " ") if l.get("from") else ""
                        target = l.get("uri") or ("page %d" % (l["page"] + 1) if l.get("page", -1) >= 0 else l.get("file", ""))
                        links.append([p + 1, txt, target])
            if want["links"]:
                with open(os.path.join(folder, "links.csv"), "w", encoding="utf-8-sig", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["Page", "Link text", "Target"])
                    w.writerows(links)
                counts["links"] = len(links)
            msg = "Saved in:\n%s\n\n" % folder + "\n".join("%s: %d" % kv for kv in counts.items())
            return {"message": msg, "files": [], "folder": folder}
        return task
# ============================================================================
#  SECTION I - PHASE 3 TOOLS (part 2): BUNDLE BUILDER
# ============================================================================
INDEX_ROWS = 32


def fix_toc(toc):
    prev = 0
    for e in toc:
        e[0] = max(1, min(e[0], prev + 1))
        prev = e[0]
    return toc


def _font_css(text, size_pt, rgb=(0, 0, 0), align="left", bold=False):
    font = None
    script = script_of(text)
    if script:
        font = find_font(script)
    elif not is_latin1(text):
        font = find_font(None)
    css = "body{font-size:%spt;color:rgb(%d,%d,%d);text-align:%s;margin:0;%s}" % (
        size_pt, rgb[0] * 255, rgb[1] * 255, rgb[2] * 255, align, "font-weight:bold;" if bold else "")
    arch = None
    if font:
        css = "@font-face{font-family:uni;src:url(%s);}body{font-family:uni;}" % os.path.basename(font) + css
        arch = fitz.Archive(os.path.dirname(font))
    return css, arch


def put_box(page, rect, text, size, rgb=(0, 0, 0), align="left", bold=False, min_scale=0.4):
    """Text in a box (wrapped, auto-shrunk) on an UNROTATED page; handles Indian scripts and symbols."""
    css, arch = _font_css(text, size, rgb, align, bold)
    html = "<body>%s</body>" % text.replace("&", "&amp;").replace("<", "&lt;")
    page.insert_htmlbox(rect, html, css=css, archive=arch, scale_low=min_scale)


def put_line(page, x, y_base, max_w, text, size, rgb=(0, 0, 0), bold=False, align="left"):
    """One line, truncated with '...' if too wide. Latin/symbols via insert_text, Indian scripts via HTML box."""
    if script_of(text):
        r = fitz.Rect(x, y_base - size * 1.05, x + max_w, y_base + size * 0.6)
        put_box(page, r, text, size, rgb, align, bold, min_scale=0.5)
        return
    if is_latin1(text):
        fname, font = ("hebo" if bold else "helv"), None
        tl = lambda s: fitz.get_text_length(s, fname, size)
    else:
        ff = find_font(None)
        font = fitz.Font(fontfile=ff) if ff else None
        fname = "uni_" + str(abs(hash(ff)) % 9999) if ff else "helv"
        if font is None:
            text = text.encode("latin-1", "replace").decode("latin-1")
            tl = lambda s: fitz.get_text_length(s, "helv", size)
            fname = "helv"
        else:
            tl = lambda s: font.text_length(s, size)
    t = text
    while tl(t) > max_w and len(t) > 1:
        t = t[:-2] + "…" if len(t) > 2 else t[:-1]
        if tl(t) <= max_w:
            break
    if font is None and not is_latin1(t):
        t = t.replace("…", "...")
    w = tl(t)
    xx = x if align == "left" else (x + max_w - w if align == "right" else x + (max_w - w) / 2)
    kw = {"fontfile": find_font(None)} if (font is not None) else {}
    page.insert_text((xx, y_base), t, fontsize=size, fontname=fname, color=rgb, **kw)


BUNDLE_NUMBER_MODES = [("No page numbers", "none"), ("Continuous across the whole bundle", "cont"),
                       ("Restart for each document", "restart"), ("Combined: Page 15 of 120 | Doc 2: 3 of 10", "combined"),
                       ("Bates (prefix + fixed digits)", "bates")]


def build_bundle(cfg, report, cancelled=lambda: False):
    """Build the bundle PDF in memory. Returns (doc, info)."""
    docs = cfg["docs"]
    if len(docs) < 1:
        raise UserError("Add at least one document to the bundle.")
    srcs = []
    for i, d in enumerate(docs):
        report(2 + 8 * i / len(docs), "Opening %s" % os.path.basename(d["path"]))
        srcs.append(open_pdf(d["path"]))
    nd = len(docs)
    use_index = cfg["index"]
    idx_pages = (nd + INDEX_ROWS - 1) // INDEX_ROWS if use_index else 0
    sep = cfg["sep"]
    pm = []                                          # page map (one dict per output page)
    for i in range(idx_pages):
        pm.append({"kind": "index", "doc": -1, "local": i})
    starts = []
    for k, s in enumerate(srcs):
        starts.append(len(pm))
        if sep:
            pm.append({"kind": "sep", "doc": k, "local": -1})
        for j in range(s.page_count):
            pm.append({"kind": "doc", "doc": k, "local": j})
    total = len(pm)
    roman = cfg["roman_front"] and idx_pages > 0
    front = idx_pages if roman else 0
    mode = cfg["num_mode"]
    skip_sep = cfg["skip_sep"]
    N = total - front
    bates_ctr = {}
    counter = cfg["bates_start"]
    for ph in range(total):                          # pre-compute Bates numbers in physical order
        m = pm[ph]
        if mode == "bates" and not (m["kind"] == "sep" and skip_sep):
            bates_ctr[ph] = "%s%s" % (cfg["bates_prefix"], str(counter).zfill(cfg["bates_digits"]))
            counter += 1

    def label_of(ph):
        m = pm[ph]
        if mode == "none":
            return None
        if m["kind"] == "sep" and skip_sep:
            return None
        if m["kind"] == "index" and roman:
            return to_roman(ph + 1)
        if mode == "bates":
            return bates_ctr.get(ph)
        g = ph - front + 1
        if mode == "cont":
            return format_number_label(cfg["num_fmt"], g, N)
        if m["kind"] == "sep":
            return None
        if mode == "restart":
            return format_number_label(cfg["num_fmt"], m["local"] + 1, srcs[m["doc"]].page_count)
        if mode == "combined":
            if m["kind"] == "index":
                return "Page %d of %d" % (g, N)
            return "Page %d of %d | Doc %d: %d of %d" % (g, N, m["doc"] + 1, m["local"] + 1, srcs[m["doc"]].page_count)
        return None

    def index_no(ph):
        return bates_ctr.get(ph) if mode == "bates" and ph in bates_ctr else str(ph + 1 - front)

    new = fitz.open()
    for i in range(idx_pages):
        new.new_page(width=595.28, height=841.89)
    toc = []
    if use_index:
        toc.append([1, cfg["index_title"], 1])
    for k, s in enumerate(srcs):
        report(12 + 38 * k / nd, "Adding %s" % docs[k]["title"])
        title = docs[k]["title"]
        if sep:
            pg = new.new_page(width=595.28, height=841.89)
            txt = expand_sep(cfg["sep_text"], k + 1, title, s.page_count)
            put_box(pg, fitz.Rect(60, 300, 535, 540), txt, 30, (0.06, 0.18, 0.45), "center", True, 0.3)
            pg.draw_line((200, 290), (395, 290), color=(0.84, 0.16, 0.22), width=3)
        new.insert_pdf(s)
        if cfg["bookmarks"]:
            toc.append([1, "%d. %s" % (k + 1, title), starts[k] + 1])
            if cfg["subbookmarks"]:
                off = starts[k] + (1 if sep else 0)
                for lvl, t, p in s.get_toc():
                    if p >= 1:
                        toc.append([lvl + 1, t, p + off])
    # ---- index pages
    if use_index:
        report(55, "Drawing index...")
        rows = []
        for k in range(nd):
            rows.append((k + 1, docs[k]["title"], index_no(starts[k]), srcs[k].page_count))
        for ip in range(idx_pages):
            pg = new[ip]
            if ip == 0:
                put_line(pg, 50, 70, 495, cfg["index_title"], 24, (0.06, 0.18, 0.45), True)
                pg.draw_line((50, 80), (545, 80), color=(0.84, 0.16, 0.22), width=2.5)
            y = 118
            pg.draw_rect(fitz.Rect(46, y - 15, 549, y + 5), color=None, fill=(0.88, 0.93, 1))
            for x, wd, h, al in ((52, 30, "No.", "left"), (86, 330, "Document", "left"), (420, 70, "Start page", "right"), (495, 50, "Pages", "right")):
                put_line(pg, x, y, wd, h, 10, (0.06, 0.18, 0.45), True, al)
            y += 24
            for r in rows[ip * INDEX_ROWS:(ip + 1) * INDEX_ROWS]:
                put_line(pg, 52, y, 30, str(r[0]), 10)
                put_line(pg, 86, y, 330, r[1], 10)
                put_line(pg, 420, y, 70, str(r[2]), 10, align="right")
                put_line(pg, 495, y, 50, str(r[3]), 10, align="right")
                pg.draw_line((46, y + 5), (549, y + 5), color=(0.85, 0.88, 0.94), width=0.4)
                pg.insert_link({"kind": fitz.LINK_GOTO, "from": fitz.Rect(46, y - 11, 549, y + 5),
                                "page": starts[r[0] - 1], "to": fitz.Point(0, 36)})
                y += 21
    # ---- bookmarks
    if toc:
        new.set_toc(fix_toc(toc))
    # ---- headers / footers (document name) and numbering
    for ph in range(total):
        if cancelled():
            raise Cancelled()
        m = pm[ph]
        pg = new[ph]
        if cfg["hf"] and m["kind"] == "doc":
            draw_label(pg, expand_tokens(cfg["hf_text"], m["local"] + 1, srcs[m["doc"]].page_count, docs[m["doc"]]["title"]).replace("{title}", docs[m["doc"]]["title"]),
                       cfg["hf_pos"], cfg["hf_size"], cfg["hf_margin"], COLORS[cfg["hf_color"]])
        lab = label_of(ph)
        if lab:
            pos = cfg["num_pos"]
            if cfg["mirror"] and not pos.endswith("center"):
                side = "right" if (ph + 1) % 2 == 1 else "left"
                pos = pos.split("-")[0] + "-" + side
            draw_label(pg, lab, pos, cfg["num_size"], cfg["num_margin"], COLORS[cfg["num_color"]])
        if ph % 20 == 0:
            report(60 + 32 * ph / total, "Numbering page %d of %d" % (ph + 1, total))
    md = new.metadata or {}
    md.update({"title": cfg["meta_title"], "author": cfg["meta_author"], "subject": cfg["meta_subject"], "producer": APP_NAME})
    new.set_metadata(md)
    info = {"rows": [(k + 1, docs[k]["title"], index_no(starts[k]), srcs[k].page_count) for k in range(nd)], "total": total}
    for s in srcs:
        s.close()
    return new, info


def expand_sep(tpl, n, title, pages):
    return tpl.replace("{n}", str(n)).replace("{title}", title).replace("{pages}", str(pages))


BUNDLE_DEFAULTS = {"bookmarks": True, "subbookmarks": False, "index": True, "index_title": "Index", "sep": False,
                   "sep_text": "Tab {n} – {title}", "roman_front": False, "skip_sep": True, "mirror": False,
                   "num_mode": "cont", "num_fmt": "Page 1 of N", "bates_prefix": "DOC-", "bates_digits": 6, "bates_start": 1,
                   "num_pos": "bottom-center", "num_size": 10, "num_margin": 24, "num_color": "Black",
                   "hf": True, "hf_text": "{title}", "hf_pos": "top-center", "hf_size": 9, "hf_margin": 22, "hf_color": "Gray",
                   "meta_title": "", "meta_author": "", "meta_subject": ""}


class BundleTool(ToolPage):
    key, title, group = "bundle", "Bundle Builder", "Bundle"
    subtitle = "Combine many documents into one organised bundle: index page, bookmarks, tabs, headers and page numbering."
    action_text = "Build bundle"

    def build(self, L):
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["#", "Title (double-click to edit)", "File", "Pages / status"])
        self.tree.setRootIsDecorated(False)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setAcceptDrops(True)
        self.tree.setMinimumHeight(190)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree.itemDoubleClicked.connect(lambda it, col: self.tree.editItem(it, 1) if col == 1 else None)
        self.tree.model().rowsMoved.connect(self.renumber)
        self.tree.dragEnterEvent = self._tree_drag
        self.tree.dragMoveEvent = self._tree_drag
        self._orig_drop = self.tree.dropEvent
        self.tree.dropEvent = self._tree_drop
        L.addWidget(self.tree)
        row = QHBoxLayout()
        for text, fn in (("Add PDFs...", self.add_files), ("Move up", lambda: self.mv(-1)), ("Move down", lambda: self.mv(1)),
                         ("Remove", self.rem), ("Clear", lambda: (self.tree.clear())), ("Pre-merge check", self.check),
                         ("Preview", self.preview), ("Save recipe", self.save_recipe), ("Load recipe", self.load_recipe)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        self.ai_btn = QPushButton("AI: suggest titles (Prime)")
        self.ai_btn.clicked.connect(self.ai_titles)
        row.addWidget(self.ai_btn)
        row.addStretch(1)
        L.addLayout(row)
        self.tabs = QTabWidget()
        L.addWidget(self.tabs)
        self.w = {}

        def reg(name, widget):
            self.w[name] = widget
            return widget

        # --- structure
        t = QWidget(); g = QVBoxLayout(t)
        g.addWidget(reg("bookmarks", QCheckBox("Add a bookmark for each document")))
        g.addWidget(reg("subbookmarks", QCheckBox("Keep each document's own bookmarks as sub-bookmarks")))
        g.addWidget(reg("index", QCheckBox("Create a clickable index page at the front")))
        g.addWidget(hbox(QLabel("Index title"), reg("index_title", QLineEdit())))
        g.addWidget(reg("sep", QCheckBox("Insert a separator ('tab') page before each document")))
        g.addWidget(hbox(QLabel("Separator wording  ({n} {title} {pages})"), reg("sep_text", QLineEdit())))
        self.xl = QCheckBox("Also export the index to Excel")
        self.dc = QCheckBox("Also export the index to Word")
        g.addWidget(hbox(self.xl, self.dc, None))
        self.tabs.addTab(t, "Structure")
        # --- numbering
        t = QWidget(); g = QVBoxLayout(t)
        cm = reg("num_mode", QComboBox())
        for lab, val in BUNDLE_NUMBER_MODES:
            cm.addItem(lab, val)
        g.addWidget(hbox(QLabel("Numbering"), cm))
        g.addWidget(hbox(QLabel("Format (continuous / restart)"), reg("num_fmt", self.combo(NUMBER_FORMATS, "Page 1 of N"))))
        g.addWidget(hbox(QLabel("Bates prefix"), reg("bates_prefix", QLineEdit()), QLabel("Digits"), reg("bates_digits", self.spin(1, 12, 6)),
                         QLabel("Start at"), reg("bates_start", self.spin(1, 99999999, 1))))
        g.addWidget(reg("roman_front", QCheckBox("Use Roman numerals (i, ii, iii) for the index / front matter")))
        g.addWidget(reg("skip_sep", QCheckBox("Do not number separator pages")))
        g.addWidget(reg("mirror", QCheckBox("Odd / even placement (odd pages right, even pages left)")))
        g.addWidget(hbox(QLabel("Position"), reg("num_pos", self.combo([(p[0], p[1]) for p in POSITIONS])),
                         QLabel("Font size"), reg("num_size", self.spin(6, 36, 10)), QLabel("Margin"), reg("num_margin", self.spin(5, 150, 24)),
                         QLabel("Colour"), reg("num_color", self.combo(["Black", "Blue", "Red", "Gray"]))))
        self.tabs.addTab(t, "Numbering")
        # --- header
        t = QWidget(); g = QVBoxLayout(t)
        g.addWidget(reg("hf", QCheckBox("Print the document name on every page of each document")))
        g.addWidget(hbox(QLabel("Text ({title} {page} {total} {date})"), reg("hf_text", QLineEdit())))
        g.addWidget(hbox(QLabel("Position"), reg("hf_pos", self.combo([(p[0], p[1]) for p in POSITIONS])), QLabel("Font size"),
                         reg("hf_size", self.spin(6, 36, 9)), QLabel("Margin"), reg("hf_margin", self.spin(5, 150, 22)),
                         QLabel("Colour"), reg("hf_color", self.combo(["Gray", "Black", "Blue", "Red"]))))
        self.tabs.addTab(t, "Document-name header")
        # --- output
        t = QWidget(); g = QVBoxLayout(t)
        self.outname = QLineEdit("bundle")
        g.addWidget(hbox(QLabel("Output file name"), self.outname))
        g.addWidget(hbox(QLabel("Title"), reg("meta_title", QLineEdit()), QLabel("Author"), reg("meta_author", QLineEdit()),
                         QLabel("Subject"), reg("meta_subject", QLineEdit())))
        self.tabs.addTab(t, "Output")
        self.apply_options(BUNDLE_DEFAULTS)
        self.add_hint("Index 'Start page' = the page where each tab begins. With Roman numerals ticked, the index pages are i, ii... and "
                      "the first document page is 1. In Bates mode the index shows Bates numbers.")

    # --- drag from desktop
    def _tree_drag(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            QTreeWidget.dragMoveEvent(self.tree, e)

    def _tree_drop(self, e):
        if e.mimeData().hasUrls():
            self.add_paths([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])
            e.acceptProposedAction()
        else:
            self._orig_drop(e)
            self.renumber()

    # --- list management
    def add_files(self):
        fs, _ = QFileDialog.getOpenFileNames(self, "Add PDFs", SET.last_dir("bundle"), "PDF files (*.pdf)")
        if fs:
            SET.remember_dir("bundle", fs[0])
            self.add_paths(fs)

    def add_paths(self, paths, titles=None):
        for i, p in enumerate(paths):
            if not p.lower().endswith(".pdf") or not os.path.isfile(p):
                continue
            title = (titles[i] if titles else os.path.splitext(os.path.basename(p))[0])
            pages = "?"
            try:
                d = fitz.open(p)
                pages = "password-protected" if d.needs_pass else str(d.page_count)
                d.close()
            except Exception:
                pages = "damaged"
            it = QTreeWidgetItem(["", title, os.path.basename(p), pages])
            it.setData(0, Qt.UserRole, p)
            it.setToolTip(2, p)
            it.setFlags(it.flags() | Qt.ItemIsEditable)
            self.tree.addTopLevelItem(it)
        self.renumber()

    def renumber(self, *a):
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setText(0, str(i + 1))

    def mv(self, d):
        its = self.tree.selectedItems()
        rows = sorted([self.tree.indexOfTopLevelItem(i) for i in its], reverse=(d > 0))
        for r in rows:
            nr = r + d
            if 0 <= nr < self.tree.topLevelItemCount():
                it = self.tree.takeTopLevelItem(r)
                self.tree.insertTopLevelItem(nr, it)
                it.setSelected(True)
        self.renumber()

    def rem(self):
        for it in self.tree.selectedItems():
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(it))
        self.renumber()

    def docs(self):
        return [{"path": self.tree.topLevelItem(i).data(0, Qt.UserRole),
                 "title": self.tree.topLevelItem(i).text(1).strip() or "Document %d" % (i + 1)}
                for i in range(self.tree.topLevelItemCount())]

    # --- options <-> widgets
    def options(self):
        o = {}
        for k, w in self.w.items():
            if isinstance(w, QCheckBox):
                o[k] = w.isChecked()
            elif isinstance(w, QLineEdit):
                o[k] = w.text()
            elif isinstance(w, QComboBox):
                o[k] = w.currentData() if w.currentData() is not None and k in ("num_mode", "num_pos", "hf_pos") else w.currentText()
            elif isinstance(w, QSpinBox):
                o[k] = w.value()
        return o

    def apply_options(self, o):
        for k, w in self.w.items():
            if k not in o:
                continue
            v = o[k]
            if isinstance(w, QCheckBox):
                w.setChecked(bool(v))
            elif isinstance(w, QLineEdit):
                w.setText(str(v))
            elif isinstance(w, QComboBox):
                i = w.findData(v)
                if i < 0:
                    i = w.findText(str(v))
                if i >= 0:
                    w.setCurrentIndex(i)
            elif isinstance(w, QSpinBox):
                w.setValue(int(v))

    def cfg(self):
        c = dict(self.options())
        c["docs"] = self.docs()
        return c

    # --- recipes
    def save_recipe(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save bundle recipe", SET.last_dir("recipe"), "Bundle recipe (*.json)")
        if p:
            SET.remember_dir("recipe", p)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "docs": self.docs(), "options": self.options(), "outname": self.outname.text()}, f, indent=2)

    def load_recipe(self):
        p, _ = QFileDialog.getOpenFileName(self, "Load bundle recipe", SET.last_dir("recipe"), "Bundle recipe (*.json)")
        if not p:
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                r = json.load(f)
            self.tree.clear()
            miss = [d["path"] for d in r["docs"] if not os.path.isfile(d["path"])]
            ok = [d for d in r["docs"] if os.path.isfile(d["path"])]
            self.add_paths([d["path"] for d in ok], [d["title"] for d in ok])
            self.apply_options(r.get("options", {}))
            self.outname.setText(r.get("outname", "bundle"))
            if miss:
                QMessageBox.warning(self, APP_NAME, "These files from the recipe were not found and were skipped:\n" + "\n".join(miss))
        except Exception:
            self.warn("That recipe file could not be read.")

    # --- checks / preview / AI
    def check(self):
        docs = self.docs()
        if not docs:
            self.warn("Add documents first.")
            return

        def task(report, cancelled):
            lines, bad = [], 0
            for i, d in enumerate(docs):
                report(100 * i / len(docs), os.path.basename(d["path"]))
                try:
                    doc = open_pdf(d["path"])
                    blanks = [p + 1 for p in range(doc.page_count) if is_blank_page(doc[p], 3)]
                    lines.append("OK  %s - %d pages%s" % (os.path.basename(d["path"]), doc.page_count,
                                 (", blank pages: " + ", ".join(map(str, blanks[:15]))) if blanks else ""))
                    doc.close()
                except UserError as e:
                    bad += 1
                    lines.append("PROBLEM  %s - %s" % (os.path.basename(d["path"]), str(e).splitlines()[0]))
            return {"message": ("%d problem(s) found.\n\n" % bad if bad else "All documents can be merged.\n\n") + "\n".join(lines), "files": []}
        self.run_task(task, self.on_success)

    def preview(self):
        try:
            cfg = self.cfg()
            if not cfg["docs"]:
                raise UserError("Add documents first.")
        except UserError as e:
            self.warn(str(e))
            return
        td = TempDir()
        tmp = td.__enter__()

        def task(report, cancelled):
            doc, info = build_bundle(cfg, report, cancelled)
            p = os.path.join(tmp, "preview.pdf")
            doc.save(p, garbage=1, deflate=True)
            return {"path": p}

        def done(res):
            dlg = QDialog(self)
            dlg.setWindowTitle("Bundle preview (a real build; nothing is saved)")
            dlg.resize(900, 700)
            v = QVBoxLayout(dlg)
            pv = PdfViewer()
            v.addWidget(pv)
            pv.load(res["path"])
            dlg.exec_()
            pv.close_doc()
        self.run_task(task, done)

    def ai_titles(self):
        if not getattr(self.ctx, "is_prime", False):
            self.warn(AI_HOWTO)
            return
        docs = self.docs()
        if not docs:
            self.warn("Add documents first.")
            return
        ai = self.ctx.ai

        def task(report, cancelled):
            res = []
            for i, d in enumerate(docs):
                report(100 * i / len(docs), "Reading %s" % os.path.basename(d["path"]))
                doc = open_pdf(d["path"])
                txt = "".join(doc[p].get_text("text") for p in range(min(2, doc.page_count)))[:3500]
                doc.close()
                res.append(ai_suggest_title(ai, txt, cancelled) if txt.strip() else "")
            return {"titles": res}

        def done(res):
            dlg = QDialog(self)
            dlg.setWindowTitle("Suggested titles - tick the ones to apply")
            dlg.resize(640, 420)
            v = QVBoxLayout(dlg)
            lst = QListWidget()
            for i, t in enumerate(res["titles"]):
                it = QListWidgetItem("%s  ->  %s" % (docs[i]["title"], t or "(no suggestion)"))
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Unchecked)
                lst.addItem(it)
            v.addWidget(QLabel(DISCLAIMER))
            v.addWidget(lst)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            bb.accepted.connect(dlg.accept)
            bb.rejected.connect(dlg.reject)
            v.addWidget(bb)
            if dlg.exec_() == QDialog.Accepted:
                for i in range(lst.count()):
                    if lst.item(i).checkState() == Qt.Checked and res["titles"][i]:
                        self.tree.topLevelItem(i).setText(1, res["titles"][i])
        self.run_task(task, done)

    def make_task(self, out):
        cfg = self.cfg()
        if not cfg["docs"]:
            raise UserError("Add at least one document to the bundle.")
        if cfg["num_mode"] == "bates" and not cfg["bates_prefix"].strip():
            raise UserError("Enter a Bates prefix (for example CASE1-).")
        name = safe_name(strip_pdf_ext(self.outname.text()) or "bundle")
        want_x, want_d = self.xl.isChecked(), self.dc.isChecked()
        if want_x:
            need_lib(HAVE_XLSX, "openpyxl", "Excel export of the index")
        if want_d:
            need_lib(HAVE_DOCX, "python-docx", "Word export of the index")

        def task(report, cancelled):
            doc, info = build_bundle(cfg, report, cancelled)
            report(94, "Saving...")
            dst = save_pdf(doc, unique_path(out, name, ".pdf"))
            files = [dst]
            if want_x:
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Index"
                ws.append(["No.", "Document", "Start page", "Pages"])
                for r in info["rows"]:
                    ws.append(list(r))
                p = unique_path(out, name + "_index", ".xlsx")
                wb.save(p)
                files.append(p)
            if want_d:
                d = pydocx.Document()
                d.add_heading(cfg["index_title"], 1)
                t = d.add_table(rows=1, cols=4)
                t.style = "Table Grid"
                for i, h in enumerate(("No.", "Document", "Start page", "Pages")):
                    t.rows[0].cells[i].text = h
                for r in info["rows"]:
                    cells = t.add_row().cells
                    for i, v in enumerate(r):
                        cells[i].text = str(v)
                p = unique_path(out, name + "_index", ".docx")
                d.save(p)
                files.append(p)
            return {"message": "Bundle built: %d documents, %d pages.\n%s" % (len(cfg["docs"]), info["total"], dst), "files": files}
        return task
# ============================================================================
#  SECTION J - PHASE 4: REDACTION  (+ shared Tesseract helpers)
# ============================================================================
TESS_HELP = ("Tesseract OCR is not installed or was not found.\n\n"
             "1) Download the Windows installer (UB Mannheim build) from  https://github.com/UB-Mannheim/tesseract/wiki\n"
             "2) During setup tick the extra languages you need (Hindi, Gujarati, Tamil, Bengali...).\n"
             "3) Restart PDF Studio Pro - it looks in the standard folders automatically. "
             "If you installed elsewhere, set the path in Settings.")


def find_tesseract():
    cands = [SET.get("tesseract_path"), os.path.join(app_dir(), "tesseract", "tesseract.exe"), shutil.which("tesseract")]
    if IS_WIN:
        cands += [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                  os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe")]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def tess_ready():
    if not HAVE_PYTESS or not HAVE_PIL:
        return False
    p = find_tesseract()
    if not p:
        return False
    pytesseract.pytesseract.tesseract_cmd = p
    return True


def require_tess():
    if not HAVE_PYTESS or not HAVE_PIL:
        raise UserError("OCR needs the pytesseract and Pillow libraries.\nRun:  pip install pytesseract Pillow")
    if not tess_ready():
        raise UserError(TESS_HELP)


def tess_langs():
    if not tess_ready():
        return []
    try:
        return sorted(l for l in pytesseract.get_languages(config="") if l != "osd")
    except Exception:
        return ["eng"]


def pix_to_pil(pix):
    mode = "L" if pix.n == 1 else "RGB"
    return Image.frombytes(mode, (pix.width, pix.height), pix.samples)


def ocr_words(page, dpi=200, lang="eng"):
    """OCR one page; returns [(Rect in UNROTATED page coords, text, block, line)]."""
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    img = pix_to_pil(pix)
    d = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    k = 72.0 / dpi
    res = []
    for i, t in enumerate(d["text"]):
        if not t or not t.strip():
            continue
        try:
            if float(d["conf"][i]) < 0:
                continue
        except ValueError:
            pass
        r = fitz.Rect(d["left"][i] * k, d["top"][i] * k, (d["left"][i] + d["width"][i]) * k, (d["top"][i] + d["height"][i]) * k)
        r = r * page.derotation_matrix
        r.normalize()
        res.append((r, t.strip(), d["block_num"][i], d["line_num"][i] + 1000 * d["par_num"][i]))
    return res


def _luhn(num):
    ds = [int(c) for c in re.sub(r"\D", "", num)]
    if not 13 <= len(ds) <= 19:
        return False
    s = 0
    for i, d in enumerate(reversed(ds)):
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        s += d
    return s % 10 == 0


DETECTORS = collections.OrderedDict([
    ("pan", ("PAN", r"(?<![A-Za-z0-9])[A-Z]{5}[0-9]{4}[A-Z](?![A-Za-z0-9])", 0, None)),
    ("aadhaar", ("Aadhaar (12 digits)", r"(?<!\d)(?<!\d )(?<!\d-)[2-9]\d{3}\s?\d{4}\s?\d{4}(?!\d)(?! \d)(?!-\d)", 0, None)),
    ("gstin", ("GSTIN", r"(?<![A-Za-z0-9])[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z][Zz][0-9A-Z](?![A-Za-z0-9])", 0, None)),
    ("ifsc", ("IFSC", r"(?<![A-Za-z0-9])[A-Z]{4}0[A-Z0-9]{6}(?![A-Za-z0-9])", 0, None)),
    ("bank", ("Bank account no. (9-18 digits)", r"(?<![\d.,])\d{9,18}(?![\d.,])", 0, None)),
    ("mobile", ("Mobile number", r"(?<!\d)(?<!\d )(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)(?! \d)", 0, None)),
    ("email", ("Email address", r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+", 0, None)),
    ("amount", ("Amounts (\u20b9 / Rs / INR)", r"(?:\u20b9|Rs\.?|INR)\s?\d[\d,]*(?:\.\d+)?", re.I, None)),
    ("date", ("Dates", r"(?<!\d)\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}(?!\d)|(?<!\d)\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?,?\s\d{2,4}", re.I, None)),
    ("card", ("Card number (Luhn checked)", r"(?<!\d)(?:\d[ \-]?){13,19}(?!\d)", 0, _luhn)),
    ("passport", ("Passport number", r"(?<![A-Za-z0-9])[A-PR-WY][1-9]\d\s?\d{4}[1-9](?![A-Za-z0-9])", 0, None)),
])
DEFAULT_ON = ("pan", "aadhaar", "gstin", "ifsc", "mobile", "email", "card", "passport")


def page_word_list(page, ocr, ocr_lang, ocr_dpi=200):
    """-> (words[(rect,text,blockline_key)], is_ocr)"""
    words = [(fitz.Rect(w[:4]), w[4], (w[5], w[6])) for w in page.get_text("words")]
    if words or not ocr:
        return words, False
    return [(r, t, (b, l)) for r, t, b, l in ocr_words(page, ocr_dpi, ocr_lang)], True


def find_matches(page, words, regexes, is_ocr):
    """regexes: [(kind, compiled, validator)] -> list of dicts(kind,text,ctx,rects)."""
    if not words:
        return []
    parts, spans, pos = [], [], 0
    for r, t, k in words:
        spans.append((pos, pos + len(t)))
        parts.append(t)
        pos += len(t) + 1
    text = " ".join(parts)
    out = []
    for kind, rx, validator in regexes:
        for m in rx.finditer(text):
            s, e = m.span()
            mt = m.group(0)
            if not mt.strip() or (validator and not validator(mt)):
                continue
            idx = [i for i, (a, b) in enumerate(spans) if a < e and b > s]
            if not idx:
                continue
            wrects = [words[i][0] for i in idx]
            rects = []
            if not is_ocr:
                try:
                    precise = [r for r in page.search_for(mt.strip()) if any(r.intersects(w) for w in wrects)]
                except Exception:
                    precise = []
                rects = precise
            if not rects:                          # merge words per line
                byline = collections.OrderedDict()
                for i in idx:
                    byline.setdefault(words[i][2], fitz.Rect(words[i][0]))
                    byline[words[i][2]] |= words[i][0]
                rects = list(byline.values())
            ctx = (text[max(0, s - 28):s] + "\u00ab" + mt + "\u00bb" + text[e:e + 28]).replace("\n", " ")
            out.append({"kind": kind, "text": mt.strip(), "ctx": ctx, "rects": rects, "page": page.number})
    return out


def compile_patterns(detectors, keywords, whole_word, custom):
    rx = []
    for k in detectors:
        label, pat, fl, val = DETECTORS[k]
        rx.append((label, re.compile(pat, fl), val))
    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        body = r"\s+".join(re.escape(x) for x in kw.split())
        if whole_word:
            body = r"(?<!\w)" + body + r"(?!\w)"
        rx.append(("Keyword", re.compile(body, re.I), None))
    for c in custom:
        c = c.strip()
        if not c:
            continue
        try:
            rx.append(("Custom regex", re.compile(c), None))
        except re.error as e:
            raise UserError("The custom pattern  %s  is not a valid regular expression:\n%s" % (c, e))
    return rx


def scan_matches(path, regexes, ocr, lang, report, cancelled):
    doc = open_pdf(path)
    out, n = [], doc.page_count
    for i in range(n):
        report(3 + 94 * i / n, "Scanning page %d of %d" % (i + 1, n))
        pg = doc[i]
        words, is_ocr = page_word_list(pg, ocr, lang)
        for m in find_matches(pg, words, regexes, is_ocr):
            m["ocr"] = is_ocr
            out.append(m)
    doc.close()
    return out


def core_redact(src, dst, rect_map, fill, label, raster, dpi, strip, ocr_layer, ocr_lang, terms, verify, report):
    doc = open_pdf(src)
    n_rects = 0
    txt_col = (1, 1, 1) if sum(fill) < 1.5 else (0, 0, 0)
    for pno, rects in rect_map.items():
        pg = doc[pno]
        for r in rects:
            rr = fitz.Rect(r) + (-1, -1, 1, 1)
            rr = rr & pg.mediabox if False else rr
            if label:
                pg.add_redact_annot(rr, text=label, fontname="helv", fontsize=8, fill=fill, text_color=txt_col,
                                    align=fitz.TEXT_ALIGN_CENTER, cross_out=False)
            else:
                pg.add_redact_annot(rr, fill=fill)
            n_rects += 1
        report(5 + 35 * pno / max(1, doc.page_count), "Applying redaction on page %d" % (pno + 1))
        try:
            pg.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS, graphics=1, text=fitz.PDF_REDACT_TEXT_REMOVE)
        except TypeError:
            pg.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
    if strip:
        report(42, "Removing metadata, bookmarks, annotations, attachments, forms...")
        for pg in doc:
            for w in list(pg.widgets() or []):
                try:
                    pg.delete_widget(w)
                except Exception:
                    pass
            for a in list(pg.annots() or []):
                try:
                    pg.delete_annot(a)
                except Exception:
                    pass
        doc.set_toc([])
        doc.set_metadata({})
        try:
            doc.scrub(attached_files=True, embedded_files=True, hidden_text=True, javascript=True, metadata=True,
                      xml_metadata=True, thumbnails=True, remove_links=True, reset_fields=True, reset_responses=True,
                      clean_pages=True, redactions=False, redact_images=0)
        except Exception:
            pass
    if raster:
        out = fitz.open()
        use_ocr = ocr_layer and tess_ready()
        n = doc.page_count
        for i in range(n):
            report(45 + 45 * i / n, "Rasterizing page %d of %d" % (i + 1, n))
            pg = doc[i]
            pix = pg.get_pixmap(dpi=dpi, alpha=False)
            np_ = out.new_page(width=pg.rect.width, height=pg.rect.height)
            if use_ocr:
                try:
                    pdfb = pytesseract.image_to_pdf_or_hocr(pix_to_pil(pix), lang=ocr_lang, extension="pdf")
                    tmp = fitz.open("pdf", pdfb)
                    np_.show_pdf_page(np_.rect, tmp, 0)
                    tmp.close()
                    continue
                except Exception as e:
                    LOG.warning("ocr layer failed: %s", e)
            np_.insert_image(np_.rect, stream=pix.tobytes("jpg", jpg_quality=88) if dpi >= 150 else pix.tobytes("png"))
        doc.close()
        doc = out
    report(92, "Saving...")
    save_pdf(doc, dst, garbage=4)
    pages = doc.page_count
    doc.close()
    left = []
    if verify and terms:
        report(95, "Verifying...")
        chk = open_pdf(dst)
        has_text = any(page_has_text(chk[i]) for i in range(chk.page_count))
        if has_text:
            for i in range(chk.page_count):
                t = " ".join(chk[i].get_text("text").split())
                for term in terms:
                    if re.sub(r"\s+", " ", term).lower() in t.lower():
                        left.append((i + 1, term))
            status = "text"
        elif tess_ready():
            status = "ocr"
            for i in range(chk.page_count):
                t = " ".join(pytesseract.image_to_string(pix_to_pil(chk[i].get_pixmap(dpi=200, alpha=False)), lang=ocr_lang).split())
                for term in terms:
                    if re.sub(r"\s+", " ", term).lower() in t.lower():
                        left.append((i + 1, term))
        else:
            status = "none"
        chk.close()
        return n_rects, pages, left, status
    return n_rects, pages, left, "skipped"


class RedactTool(ToolPage):
    key, title, group = "redact", "Redaction", "Security"
    subtitle = "Permanently remove sensitive text, images and graphics. Draw boxes by hand and/or auto-detect PAN, Aadhaar, GSTIN and more."
    action_text = "Apply redaction & save"

    def build(self, L):
        self.pdf = PdfPicker("redact")
        self.add_row("PDF file", self.pdf)
        L.addWidget(self.pdf.info)
        b = QPushButton("Open in redaction editor")
        b.clicked.connect(self.load)
        L.addWidget(b)
        self.man, self.redo_stack, self.matches = [], [], []
        self.tabs = QTabWidget()
        L.addWidget(self.tabs)
        # --- manual
        t = QWidget(); v = QVBoxLayout(t)
        self.viewer = PdfViewer(select_mode=True, compact=True)
        self.viewer.setMinimumHeight(440)
        self.viewer.rectSelected.connect(self.on_rect)
        v.addWidget(self.viewer)
        row = QHBoxLayout()
        for text, fn in (("Undo", self.undo), ("Redo", self.redo), ("Clear manual boxes", self.clear_boxes)):
            bb = QPushButton(text); bb.clicked.connect(fn); row.addWidget(bb)
        self.lbl_boxes = QLabel("0 manual boxes")
        row.addWidget(self.lbl_boxes)
        row.addStretch(1)
        v.addLayout(row)
        v.addWidget(hint_label("Drag a rectangle over anything to remove. Boxes are shown in black; nothing is changed until you press the big red button."))
        self.tabs.addTab(t, "1. Draw boxes")
        # --- auto
        t = QWidget(); v = QVBoxLayout(t)
        g = QGridLayout()
        self.det = {}
        for i, (k, (lab, *_)) in enumerate(DETECTORS.items()):
            c = QCheckBox(lab)
            c.setChecked(k in DEFAULT_ON)
            self.det[k] = c
            g.addWidget(c, i // 3, i % 3)
        v.addLayout(g)
        self.kw = QPlainTextEdit()
        self.kw.setPlaceholderText("Keywords / names / company names - one per line (case-insensitive)")
        self.kw.setMaximumHeight(80)
        self.whole = QCheckBox("Whole words only")
        self.custom = QPlainTextEdit()
        self.custom.setPlaceholderText("Custom regular expressions - one per line (advanced)")
        self.custom.setMaximumHeight(60)
        self.ocr_scan = QCheckBox("Scanned pages: use OCR to find the text (needs Tesseract)")
        self.lang = QLineEdit("eng")
        self.lang.setMaximumWidth(120)
        self.lang.setToolTip("Tesseract language code(s), e.g. eng or eng+hin")
        for w in (self.kw, self.whole, self.custom):
            v.addWidget(w)
        v.addWidget(hbox(self.ocr_scan, QLabel("OCR language"), self.lang, None))
        row = QHBoxLayout()
        fb = QPushButton("Find matches")
        fb.setObjectName("primary")
        fb.clicked.connect(self.find)
        row.addWidget(fb)
        self.ai_btn = QPushButton("AI: suggest names to redact (Prime)")
        self.ai_btn.clicked.connect(self.ai_suggest)
        row.addWidget(self.ai_btn)
        row.addStretch(1)
        v.addLayout(row)
        self.tabs.addTab(t, "2. Auto-detect")
        # --- review
        t = QWidget(); v = QVBoxLayout(t)
        v.addWidget(hint_label("REVIEW every match. Only ticked rows are redacted. Click a row to see it on the page. AI suggestions start unticked."))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Redact", "Page", "Type", "Text", "Context"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setMinimumHeight(260)
        self.table.cellClicked.connect(self.row_clicked)
        self.table.itemChanged.connect(lambda *a: self.refresh_overlay())
        v.addWidget(self.table)
        row = QHBoxLayout()
        for text, fn in (("Tick all", lambda: self.tick(True)), ("Untick all", lambda: self.tick(False)),
                         ("Untick selected", self.untick_sel)):
            bb = QPushButton(text); bb.clicked.connect(fn); row.addWidget(bb)
        self.lbl_match = QLabel("")
        row.addWidget(self.lbl_match)
        row.addStretch(1)
        v.addLayout(row)
        self.tabs.addTab(t, "3. Review matches")
        # --- options
        t = QWidget(); v = QVBoxLayout(t)
        self.fill = self.combo(["Black", "White", "Red"])
        self.label = QLineEdit()
        self.label.setPlaceholderText("optional label, e.g. REDACTED")
        v.addWidget(hbox(QLabel("Fill colour"), self.fill, QLabel("Label"), self.label))
        self.raster = QCheckBox("Rasterize: turn every page into a picture afterwards (safest - removes hidden text, layers, everything)")
        self.raster.setChecked(True)
        self.dpi = self.combo(["150", "200", "300"], "200")
        self.ocr_layer = QCheckBox("Add a fresh searchable text layer from the redacted pictures (needs Tesseract)")
        self.strip = QCheckBox("Strip metadata, bookmarks, annotations, attachments and form fields")
        self.strip.setChecked(True)
        self.verify = QCheckBox("Verify: search the result for the redacted text afterwards")
        self.verify.setChecked(True)
        for w in (self.raster, hbox(QLabel("Picture DPI"), self.dpi, None), self.ocr_layer, self.strip, self.verify):
            v.addWidget(w)
        warn = QLabel("ALWAYS open the result and check it visually before sharing. Automatic detection can miss text "
                      "(odd spacing, images of text, handwriting).")
        warn.setStyleSheet("color:#B91C2C;font-weight:bold;")
        warn.setWordWrap(True)
        v.addWidget(warn)
        self.tabs.addTab(t, "4. Options")

    # ---- manual boxes
    def load(self):
        try:
            self.viewer.load(self.pdf.require())
            self.man, self.redo_stack, self.matches = [], [], []
            self.table.setRowCount(0)
            self.refresh_overlay()
        except UserError as e:
            self.warn(str(e))

    def on_rect(self, pg, r):
        self.man.append((pg, fitz.Rect(r)))
        self.redo_stack = []
        self.refresh_overlay()

    def undo(self):
        if self.man:
            self.redo_stack.append(self.man.pop())
            self.refresh_overlay()

    def redo(self):
        if self.redo_stack:
            self.man.append(self.redo_stack.pop())
            self.refresh_overlay()

    def clear_boxes(self):
        self.man, self.redo_stack = [], []
        self.refresh_overlay()

    def refresh_overlay(self):
        m = {}
        for pg, r in self.man:
            m.setdefault(pg, []).append((r, "#000000"))
        for row, mt in enumerate(self.matches):
            it = self.table.item(row, 0)
            if it is not None and it.checkState() == Qt.Checked:
                for r in mt["rects"]:
                    m.setdefault(mt["page"], []).append((r, "#d62839"))
        self.viewer.set_overlays(m)
        self.lbl_boxes.setText("%d manual box(es)" % len(self.man))
        n = sum(1 for r in range(self.table.rowCount()) if self.table.item(r, 0) and self.table.item(r, 0).checkState() == Qt.Checked)
        self.lbl_match.setText("%d of %d ticked" % (n, len(self.matches)))

    # ---- auto detect
    def find(self):
        try:
            path = self.pdf.require()
            pdf_page_count(path)
            kws = [x for x in self.kw.toPlainText().splitlines() if x.strip()]
            cus = [x for x in self.custom.toPlainText().splitlines() if x.strip()]
            dets = [k for k, c in self.det.items() if c.isChecked()]
            if not (dets or kws or cus):
                raise UserError("Tick at least one detector or type a keyword.")
            rx = compile_patterns(dets, kws, self.whole.isChecked(), cus)
            ocr = self.ocr_scan.isChecked()
            if ocr:
                require_tess()
            lang = self.lang.text().strip() or "eng"
        except UserError as e:
            self.warn(str(e))
            return
        self.load_viewer_if_needed(path)

        def task(report, cancelled):
            return {"matches": scan_matches(path, rx, ocr, lang, report, cancelled)}

        def done(res):
            self.matches = res["matches"]
            self.fill_table()
            self.tabs.setCurrentIndex(2)
            QMessageBox.information(self, APP_NAME, "%d possible match(es) found.\nPlease review the list in step 3 before saving." % len(self.matches)
                                    if self.matches else "No matches found.")
        self.run_task(task, done)

    def load_viewer_if_needed(self, path):
        if self.viewer.path != path:
            try:
                self.viewer.load(path)
            except UserError:
                pass

    def fill_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for mt in self.matches:
            r = self.table.rowCount()
            self.table.insertRow(r)
            c = QTableWidgetItem()
            c.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            c.setCheckState(Qt.Unchecked if mt.get("ai") else Qt.Checked)
            self.table.setItem(r, 0, c)
            for i, v in enumerate((str(mt["page"] + 1), ("AI: " if mt.get("ai") else "") + mt["kind"] + (" (OCR)" if mt.get("ocr") else ""), mt["text"], mt["ctx"])):
                it = QTableWidgetItem(v)
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(r, i + 1, it)
        self.table.resizeColumnsToContents()
        self.table.blockSignals(False)
        self.refresh_overlay()

    def row_clicked(self, r, c):
        if 0 <= r < len(self.matches):
            self.viewer.go_to(self.matches[r]["page"])

    def tick(self, on):
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            self.table.item(r, 0).setCheckState(Qt.Checked if on else Qt.Unchecked)
        self.table.blockSignals(False)
        self.refresh_overlay()

    def untick_sel(self):
        self.table.blockSignals(True)
        for r in {i.row() for i in self.table.selectedItems()}:
            self.table.item(r, 0).setCheckState(Qt.Unchecked)
        self.table.blockSignals(False)
        self.refresh_overlay()

    def ai_suggest(self):
        if not getattr(self.ctx, "is_prime", False):
            self.warn(AI_HOWTO)
            return
        try:
            path = self.pdf.require()
            pdf_page_count(path)
        except UserError as e:
            self.warn(str(e))
            return
        ai = self.ctx.ai
        self.load_viewer_if_needed(path)

        def task(report, cancelled):
            doc = open_pdf(path)
            pages = [(i + 1, doc[i].get_text("text")) for i in range(doc.page_count)]
            names = ai_suggest_redactions(ai, pages, report, cancelled)
            found = []
            for nm in names:
                for i in range(doc.page_count):
                    for r in doc[i].search_for(nm):
                        found.append({"kind": "Name/company/address", "text": nm, "ctx": "(suggested by AI - verify)", "rects": [r], "page": i, "ai": True})
            return {"found": found, "n": len(names)}

        def done(res):
            self.matches += res["found"]
            self.fill_table()
            self.tabs.setCurrentIndex(2)
            QMessageBox.information(self, APP_NAME, "%s\n\nThe AI proposed %d term(s); %d place(s) were located. They are UNTICKED - tick only what is correct." % (DISCLAIMER, res["n"], len(res["found"])))
        self.run_task(task, done)

    # ---- apply
    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        rect_map, terms = {}, []
        for pg, r in self.man:
            rect_map.setdefault(pg, []).append(r)
        for row, mt in enumerate(self.matches):
            it = self.table.item(row, 0)
            if it is not None and it.checkState() == Qt.Checked:
                rect_map.setdefault(mt["page"], []).extend(mt["rects"])
                terms.append(mt["text"])
        if not rect_map:
            raise UserError("Nothing to redact yet. Draw boxes (step 1) or find and tick matches (steps 2-3).")
        label = self.label.text().strip()
        if label and not is_latin1(label):
            raise UserError("The label can use English letters only.")
        fill = COLORS[self.fill.currentText()]
        raster, dpi, strip = self.raster.isChecked(), int(self.dpi.currentText()), self.strip.isChecked()
        ocr_layer, verify = self.ocr_layer.isChecked(), self.verify.isChecked()
        if ocr_layer:
            require_tess()
        lang = self.lang.text().strip() or "eng"
        total = sum(len(v) for v in rect_map.values())
        r = QMessageBox.question(self, "Confirm redaction", "%d area(s) on %d page(s) will be permanently removed from a NEW copy of the file.\n"
                                 "Your original is not changed.\n\nContinue?" % (total, len(rect_map)))
        if r != QMessageBox.Yes:
            return None
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            dst = unique_path(out, stem + "_redacted", ".pdf")
            nr, pages, left, status = core_redact(path, dst, rect_map, fill, label, raster, dpi, strip, ocr_layer, lang, terms, verify, report)
            msg = "Redacted %d area(s). Saved:\n%s\n\n" % (nr, dst)
            if status == "text":
                msg += ("VERIFICATION FOUND LEFTOVERS - these strings still appear in the file:\n" + "\n".join("  page %d: %s" % x for x in left[:20])
                        if left else "Verification: none of the redacted text was found in the output.")
            elif status == "ocr":
                msg += ("OCR VERIFICATION FOUND LEFTOVERS:\n" + "\n".join("  page %d: %s" % x for x in left[:20])
                        if left else "OCR verification: none of the redacted text was recognised in the output.")
            elif status == "none":
                msg += "Verification by text search is not possible on an image-only result (install Tesseract to verify with OCR)."
            msg += "\n\nIMPORTANT: open the result and check it visually before sharing."
            return {"message": msg, "files": [dst]}
        return task
# ============================================================================
#  SECTION K - PHASE 5: OCR, scan clean-up, Indian languages, batch & hot folder
# ============================================================================
LANG_NAMES = {"eng": "English", "hin": "Hindi", "guj": "Gujarati", "tam": "Tamil", "ben": "Bengali", "mar": "Marathi",
              "tel": "Telugu", "kan": "Kannada", "mal": "Malayalam", "pan": "Punjabi", "ori": "Odia", "asm": "Assamese",
              "urd": "Urdu", "san": "Sanskrit", "nep": "Nepali", "script/Devanagari": "Devanagari script"}
INDIAN_LANGS = ("hin", "guj", "tam", "ben", "mar", "tel", "kan", "mal", "pan", "ori", "asm", "urd", "san", "nep")


class LangPicker(QWidget):
    """Check-list of installed Tesseract languages (English pre-ticked)."""

    def __init__(self):
        QWidget.__init__(self)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.setMaximumHeight(110)
        self.list.setFlow(QListView.LeftToRight)
        self.list.setWrapping(True)
        self.list.setResizeMode(QListView.Adjust)
        v.addWidget(self.list)
        row = QHBoxLayout()
        b = QPushButton("Refresh languages")
        b.clicked.connect(self.refresh)
        row.addWidget(b)
        self.lbl = QLabel("")
        self.lbl.setObjectName("hint")
        row.addWidget(self.lbl, 1)
        v.addLayout(row)
        self.refresh()

    def refresh(self):
        keep = set(self.codes())
        self.list.clear()
        if not tess_ready():
            self.lbl.setText("Tesseract not found - see Settings / help text.")
            return
        langs = tess_langs()
        for l in langs:
            it = QListWidgetItem("%s (%s)" % (LANG_NAMES.get(l, l), l))
            it.setData(Qt.UserRole, l)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if (l in keep or (not keep and l == "eng")) else Qt.Unchecked)
            self.list.addItem(it)
        missing = [l for l in ("hin", "guj", "tam", "ben") if l not in langs]
        self.lbl.setText("%d language(s) installed.%s" % (len(langs), ("  Not installed: " + ", ".join(missing)) if missing else ""))

    def codes(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count()) if self.list.item(i).checkState() == Qt.Checked]

    def lang(self):
        c = self.codes()
        if not c:
            raise UserError("Tick at least one OCR language (for English plus Hindi tick both).")
        return "+".join(c)


# ---------------------------------------------------------------- scan clean-up (OpenCV, no AI)
def require_cv():
    if not (HAVE_CV2 and HAVE_NP):
        raise UserError("Scan clean-up needs OpenCV and numpy.\nRun:  pip install opencv-python-headless numpy")


def pix_to_np(pix):
    a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        a = a[:, :, :3]
    return a.copy()


def _estimate_skew(gray):
    h, w = gray.shape
    s = 700.0 / max(h, w)
    small = cv2.resize(gray, (int(w * s), int(h * s))) if s < 1 else gray
    bw = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    hh, ww = bw.shape
    best, bestv = 0.0, -1
    for ang in np.arange(-6, 6.01, 0.25):
        M = cv2.getRotationMatrix2D((ww / 2, hh / 2), ang, 1.0)
        r = cv2.warpAffine(bw, M, (ww, hh), flags=cv2.INTER_NEAREST)
        v = float(np.var(r.sum(axis=1)))
        if v > bestv:
            best, bestv = float(ang), v
    return best


def cleanup_array(img, o):
    """img: RGB or gray uint8. o: dict of booleans (shadow, denoise, deskew, crop, contrast, bw)."""
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    if o.get("shadow"):
        ch = cv2.split(img)
        res = []
        for c_ in ch:
            bg = cv2.medianBlur(cv2.dilate(c_, np.ones((7, 7), np.uint8)), 21)
            diff = 255 - cv2.absdiff(c_, bg)
            res.append(cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX))
        img = cv2.merge(res)
    if o.get("denoise"):
        img = cv2.fastNlMeansDenoisingColored(img, None, 6, 6, 7, 21)
    if o.get("deskew"):
        g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        ang = _estimate_skew(g)
        if abs(ang) >= 0.2:
            h, w = g.shape
            M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
            img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    if o.get("crop"):
        g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        mask = (g < 200).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        ys, xs = np.where(mask > 0)
        if len(xs) > 50:
            pad = 20
            y0, y1, x0, x1 = max(0, ys.min() - pad), min(img.shape[0], ys.max() + pad), max(0, xs.min() - pad), min(img.shape[1], xs.max() + pad)
            if (y1 - y0) * (x1 - x0) > 0.2 * img.shape[0] * img.shape[1]:
                img = img[y0:y1, x0:x1]
    if o.get("contrast"):
        lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        l = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(l)
        img = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)
    if o.get("bw"):
        g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        g = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
        img = cv2.cvtColor(g, cv2.COLOR_GRAY2RGB)
    return img


def array_to_page(doc, arr, dpi, as_png):
    ok, buf = cv2.imencode(".png" if as_png else ".jpg", cv2.cvtColor(arr, cv2.COLOR_RGB2BGR),
                           [] if as_png else [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    h, w = arr.shape[:2]
    pg = doc.new_page(width=w * 72.0 / dpi, height=h * 72.0 / dpi)
    pg.insert_image(pg.rect, stream=buf.tobytes())


def core_cleanup_pdf(src, dst, opts, dpi=200, report=None, cancelled=lambda: False):
    require_cv()
    doc = open_pdf(src)
    out = fitz.open()
    n = doc.page_count
    for i in range(n):
        if cancelled():
            raise Cancelled()
        if report:
            report(5 + 85 * i / n, "Cleaning page %d of %d" % (i + 1, n))
        arr = pix_to_np(doc[i].get_pixmap(dpi=dpi, alpha=False, colorspace=fitz.csRGB))
        array_to_page(out, cleanup_array(arr, opts), dpi, bool(opts.get("bw")))
    save_pdf(out, dst)


def core_cleanup_image(path, out_doc, opts, dpi=200):
    require_cv()
    data = np.fromfile(path, np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise UserError("The image '%s' could not be read." % os.path.basename(path))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    array_to_page(out_doc, cleanup_array(img, opts), dpi, bool(opts.get("bw")))


class CleanupTool(ToolPage):
    key, title, group = "cleanup", "Scan Clean-up", "Images"
    subtitle = "Straighten, crop, de-shadow, denoise and sharpen scanned pages (no AI). Optionally OCR afterwards."

    def build(self, L):
        self.files = FileListWidget("cleanup", PDF_EXT + IMG_EXT, "PDF or images (*.pdf *.jpg *.jpeg *.png *.bmp *.tif *.tiff)", "Select scans")
        self.add_row("Scanned PDFs or images (each becomes its own cleaned PDF)", self.files)
        self.cb = {}
        for k, lab, on in (("deskew", "Straighten (deskew)", True), ("crop", "Crop empty borders", True), ("shadow", "Remove shadows / uneven lighting", False),
                           ("denoise", "Remove noise (slower)", False), ("contrast", "Improve contrast", True), ("bw", "Adaptive black-and-white (small files, best for text)", False)):
            c = QCheckBox(lab)
            c.setChecked(on)
            self.cb[k] = c
        g = QGridLayout()
        for i, c in enumerate(self.cb.values()):
            g.addWidget(c, i // 2, i % 2)
        self.form.addLayout(g)
        self.dpi = self.combo(["150", "200", "300"], "200")
        self.ocr_after = QCheckBox("Run OCR afterwards (make searchable)")
        self.lang = LangPicker()
        self.form.addWidget(hbox(QLabel("Working resolution (DPI)"), self.dpi, self.ocr_after, None))
        self.form.addWidget(self.lang)
        pb = QPushButton("Preview first file: before / after")
        pb.clicked.connect(self.preview)
        self.form.addWidget(pb)

    def _opts(self):
        return {k: c.isChecked() for k, c in self.cb.items()}

    def preview(self):
        ps = self.files.paths()
        if not ps:
            self.warn("Add a file first.")
            return
        try:
            require_cv()
            if ps[0].lower().endswith(".pdf"):
                d = open_pdf(ps[0])
                arr = pix_to_np(d[0].get_pixmap(dpi=100, alpha=False, colorspace=fitz.csRGB))
                d.close()
            else:
                arr = cv2.cvtColor(cv2.imdecode(np.fromfile(ps[0], np.uint8), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
                s = 1000.0 / max(arr.shape[:2])
                if s < 1:
                    arr = cv2.resize(arr, None, fx=s, fy=s)
            after = cleanup_array(arr, self._opts())
        except UserError as e:
            self.warn(str(e))
            return

        def qpm(a):
            a = np.ascontiguousarray(a)
            return QPixmap.fromImage(QImage(a.data, a.shape[1], a.shape[0], a.shape[1] * 3, QImage.Format_RGB888).copy()).scaledToHeight(560, Qt.SmoothTransformation)
        dlg = QDialog(self)
        dlg.setWindowTitle("Before (left)  |  After (right)")
        h = QHBoxLayout(dlg)
        for a in (arr, after):
            l = QLabel()
            l.setPixmap(qpm(a))
            h.addWidget(l)
        dlg.exec_()

    def make_task(self, out):
        files = self.files.paths()
        if not files:
            raise UserError("Add at least one PDF or image.")
        require_cv()
        opts, dpi = self._opts(), int(self.dpi.currentText())
        if not any(opts.values()):
            raise UserError("Tick at least one clean-up step.")
        ocr, lang = self.ocr_after.isChecked(), None
        if ocr:
            require_tess()
            lang = self.lang.lang()

        def task(report, cancelled):
            res = []
            for k, f in enumerate(files):
                base = 100.0 * k / len(files)
                sub = lambda p, m="": report(base + p / len(files), m)
                stem = safe_name(os.path.splitext(os.path.basename(f))[0])
                dst = unique_path(out, stem + "_cleaned", ".pdf")
                if f.lower().endswith(".pdf"):
                    core_cleanup_pdf(f, dst, opts, dpi, sub, cancelled)
                else:
                    d = fitz.open()
                    core_cleanup_image(f, d, opts, dpi)
                    save_pdf(d, dst)
                if ocr:
                    tmp = dst + ".tmp.pdf"
                    os.replace(dst, tmp)
                    core_ocr_pdf(tmp, dst, lang, dpi, None, False, None, sub, cancelled)
                    os.remove(tmp)
                res.append(dst)
            return {"message": "Cleaned %d file(s)." % len(res), "files": res}
        return task


# ---------------------------------------------------------------- OCR
def _jpeg_tmp(pil, td, name):
    p = os.path.join(td, name)
    pil.convert("RGB").save(p, "JPEG", quality=85)
    return p


def core_ocr_pdf(src, dst, lang, dpi, pages, skip_text, cleanup_opts, report, cancelled):
    require_tess()
    doc = open_pdf(src)
    n = doc.page_count
    pages = set(range(n)) if pages is None else set(pages)
    out = fitz.open()
    done = 0
    with TempDir() as td:
        for i in range(n):
            if cancelled():
                raise Cancelled()
            if report:
                report(3 + 92 * i / n, "OCR page %d of %d" % (i + 1, n))
            pg = doc[i]
            if i not in pages or (skip_text and page_has_text(pg)):
                out.insert_pdf(doc, from_page=i, to_page=i)
                continue
            pix = pg.get_pixmap(dpi=dpi, alpha=False)
            pil = pix_to_pil(pix)
            if cleanup_opts and HAVE_CV2:
                pil = Image.fromarray(cleanup_array(np.asarray(pil.convert("RGB")), cleanup_opts))
            path = _jpeg_tmp(pil, td, "p%d.jpg" % i)
            pdfb = pytesseract.image_to_pdf_or_hocr(path, lang=lang, extension="pdf")
            tmp = fitz.open("pdf", pdfb)
            np_ = out.new_page(width=pg.rect.width, height=pg.rect.height)
            np_.show_pdf_page(np_.rect, tmp, 0)
            tmp.close()
            done += 1
    save_pdf(out, dst)
    return done


def ocr_page_text(page, lang, dpi):
    return pytesseract.image_to_string(pix_to_pil(page.get_pixmap(dpi=dpi, alpha=False)), lang=lang)


def ocr_page_rows(page, lang, dpi):
    """Rows of cells guessed from word gaps (for statements/tables)."""
    d = pytesseract.image_to_data(pix_to_pil(page.get_pixmap(dpi=dpi, alpha=False)), lang=lang, output_type=pytesseract.Output.DICT)
    lines = collections.OrderedDict()
    for i, t in enumerate(d["text"]):
        if t.strip():
            lines.setdefault((d["block_num"][i], d["par_num"][i], d["line_num"][i]), []).append((d["left"][i], d["width"][i], d["height"][i], t))
    rows = []
    for ws in lines.values():
        ws.sort()
        cells, cur, lastx = [], [], None
        for (x, w, h, t) in ws:
            if lastx is not None and x - lastx > h * 1.6:
                cells.append(" ".join(cur))
                cur = []
            cur.append(t)
            lastx = x + w
        cells.append(" ".join(cur))
        rows.append(cells)
    return rows


class OcrTool(ToolPage):
    key, title, group = "ocr", "OCR (Scanned PDF)", "Convert"
    subtitle = "Make scanned PDFs searchable, or turn them into Word / Excel. Indian languages supported."

    def build(self, L):
        self.pdf = PdfPicker("ocr")
        self.add_row("Scanned PDF", self.pdf)
        L.addWidget(self.pdf.info)
        self.mode = self.combo([("Make searchable PDF (invisible text layer)", "pdf"), ("Scanned PDF to Word (.docx)", "docx"),
                                ("Scanned PDF to Excel (.xlsx) - tables/statements", "xlsx"), ("Plain text (.txt)", "txt")])
        self.add_row("Result", self.mode)
        self.lang = LangPicker()
        self.add_row("Languages", self.lang)
        self.dpi = self.combo(["200", "300", "400"], "300")
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("blank = all pages")
        self.skip = QCheckBox("Skip pages that already have real text")
        self.skip.setChecked(True)
        self.clean = QCheckBox("Clean up the scan first (straighten + contrast)")
        L.addWidget(hbox(QLabel("OCR resolution (DPI)"), self.dpi, QLabel("Pages"), self.pages))
        L.addWidget(hbox(self.skip, self.clean, None))
        self.add_hint("Searchable PDF: processed pages are rebuilt from pictures at the chosen DPI (a little larger/smaller than the original). "
                      "For best results on Indian languages install the matching Tesseract language data.")

    def make_task(self, out):
        path = self.pdf.require()
        n = pdf_page_count(path)
        require_tess()
        lang = self.lang.lang()
        pages = pages_from_text(self.pages.text(), n)
        dpi, mode = int(self.dpi.currentText()), self.mode.currentData()
        skip, clean = self.skip.isChecked(), ({"deskew": True, "contrast": True} if self.clean.isChecked() else None)
        if clean:
            require_cv()
        if mode == "docx":
            need_lib(HAVE_DOCX, "python-docx", "Word output")
        if mode == "xlsx":
            need_lib(HAVE_XLSX, "openpyxl", "Excel output")
        stem = safe_name(os.path.splitext(os.path.basename(path))[0])

        def task(report, cancelled):
            if mode == "pdf":
                dst = unique_path(out, stem + "_ocr", ".pdf")
                k = core_ocr_pdf(path, dst, lang, dpi, pages, skip, clean, report, cancelled)
                return {"message": "OCR finished for %d page(s):\n%s" % (k, dst), "files": [dst]}
            doc = open_pdf(path)
            texts = []
            for j, p in enumerate(pages):
                if cancelled():
                    raise Cancelled()
                report(3 + 90 * j / len(pages), "OCR page %d" % (p + 1))
                if mode == "xlsx":
                    texts.append((p, ocr_page_rows(doc[p], lang, dpi)))
                else:
                    texts.append((p, ocr_page_text(doc[p], lang, dpi)))
            if mode == "txt":
                dst = unique_path(out, stem + "_ocr", ".txt")
                with open(dst, "w", encoding="utf-8") as f:
                    f.write("\n\n".join("----- Page %d -----\n%s" % (p + 1, t) for p, t in texts))
            elif mode == "docx":
                dst = unique_path(out, stem + "_ocr", ".docx")
                d = pydocx.Document()
                for p, t in texts:
                    d.add_heading("Page %d" % (p + 1), 3)
                    for para in re.split(r"\n\s*\n", t):
                        if para.strip():
                            d.add_paragraph(" ".join(para.split()))
                d.save(dst)
            else:
                dst = unique_path(out, stem + "_ocr", ".xlsx")
                wb = openpyxl.Workbook()
                wb.remove(wb.active)
                for p, rows in texts:
                    ws = wb.create_sheet("Page %d" % (p + 1))
                    for r in rows:
                        ws.append([_cell_value(c, True) for c in r])
                wb.save(dst)
            return {"message": "Saved:\n%s\n\nPlease proof-read OCR output - it can contain mistakes." % dst, "files": [dst]}
        return task


class ImageOcrTool(ToolPage):
    key, title, group = "imgocr", "Image to Text (OCR)", "Images"
    subtitle = "Read the text from pictures (photos of documents, screenshots)."

    def build(self, L):
        self.files = FileListWidget("imgocr", IMG_EXT, "Images (*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp)", "Select images")
        self.add_row("Images", self.files)
        self.lang = LangPicker()
        self.add_row("Languages", self.lang)
        self.merge = QCheckBox("Put all results in one text file")
        self.merge.setChecked(True)
        L.addWidget(self.merge)

    def make_task(self, out):
        files = self.files.paths()
        if not files:
            raise UserError("Add at least one image.")
        require_tess()
        lang, merge = self.lang.lang(), self.merge.isChecked()

        def task(report, cancelled):
            res, parts = [], []
            for k, f in enumerate(files):
                report(3 + 90 * k / len(files), "Reading %s" % os.path.basename(f))
                try:
                    txt = pytesseract.image_to_string(Image.open(f), lang=lang)
                except Exception as e:
                    raise UserError("Could not read '%s': %s" % (os.path.basename(f), e))
                if merge:
                    parts.append("----- %s -----\n%s" % (os.path.basename(f), txt))
                else:
                    p = unique_path(out, os.path.splitext(os.path.basename(f))[0], ".txt")
                    with open(p, "w", encoding="utf-8") as fh:
                        fh.write(txt)
                    res.append(p)
            if merge:
                p = unique_path(out, "ocr_text", ".txt")
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write("\n\n".join(parts))
                res = [p]
            return {"message": "Text saved (%d file(s)). Please proof-read it." % len(res), "files": res}
        return task


# ---------------------------------------------------------------- Indian-language check page
INDIC_SAMPLES = [("devanagari", "Hindi", "क्षत्रिय  ज्ञान  श्रीमान्  संयुक्त  ₹ 1,00,000"),
                 ("gujarati", "Gujarati", "ગુજરાતી  ક્ષત્રિય  શ્રી"),
                 ("tamil", "Tamil", "தமிழ்  ஸ்ரீ  க்ஷ"),
                 ("bengali", "Bengali", "বাংলা  ক্ষত্রিয়  শ্রী"),
                 ("telugu", "Telugu", "తెలుగు  క్ష  శ్రీ"),
                 ("kannada", "Kannada", "ಕನ್ನಡ  ಕ್ಷ  ಶ್ರೀ"),
                 ("malayalam", "Malayalam", "മലയാളം  ക്ഷ  ശ്രീ"),
                 ("gurmukhi", "Punjabi", "ਪੰਜਾਬੀ  ਸ਼੍ਰੀ"),
                 ("oriya", "Odia", "ଓଡ଼ିଆ  ଶ୍ରୀ")]


class IndicCheckTool(ToolPage):
    key, title, group = "indic", "Indian Languages Check", "Edit"
    subtitle = "Find fonts and OCR language packs on this PC and create a test PDF to see how each script is drawn."

    def build(self, L):
        self.info = QTextEdit()
        self.info.setReadOnly(True)
        self.info.setMinimumHeight(230)
        L.addWidget(self.info)
        b = QPushButton("Re-scan this PC")
        b.clicked.connect(self.scan)
        L.addWidget(b)
        self.add_hint("Fonts are searched in the 'fonts' folder next to this program (put OFL-licensed Noto Sans .ttf files there, e.g. "
                      "NotoSansDevanagari-Regular.ttf) and in the Windows Fonts folder (Nirmala UI covers most Indian scripts). "
                      "Press the red button to create 'indic_test.pdf' and check conjuncts such as क्ष and श्र by eye.")
        self.scan()

    def scan(self):
        _FONT_CACHE.clear()
        lines = ["Fonts found per script:"]
        for sc, name, _ in INDIC_SAMPLES:
            f = find_font(sc)
            lines.append("  %-10s %s" % (name, f or "NOT FOUND (text in this script cannot be drawn)"))
        lines.append("")
        lines.append("Fonts for rupee sign and symbols: %s" % (find_font(None) or "none found"))
        lines.append("")
        langs = tess_langs()
        lines.append("Tesseract: %s" % (find_tesseract() or "not found"))
        lines.append("OCR languages installed: %s" % (", ".join(langs) or "-"))
        miss = [l for l in INDIAN_LANGS[:6] if l not in langs]
        if langs and miss:
            lines.append("Indian packs not installed: %s  (re-run the Tesseract installer and tick them)" % ", ".join(miss))
        self.info.setPlainText("\n".join(lines))

    def make_task(self, out):
        def task(report, cancelled):
            doc = fitz.open()
            pg = doc.new_page()
            put_box(pg, fitz.Rect(40, 30, 555, 70), "Indian-language test page", 20, (0.06, 0.18, 0.45), "left", True)
            y = 90
            for sc, name, txt in INDIC_SAMPLES:
                put_line(pg, 40, y, 90, name + ":", 11, (0.3, 0.3, 0.3))
                if find_font(sc):
                    put_box(pg, fitz.Rect(130, y - 16, 555, y + 14), txt, 16)
                else:
                    put_line(pg, 130, y, 420, "(no font found for this script)", 11, (0.84, 0.16, 0.22))
                y += 44
            put_line(pg, 40, y + 20, 500, "Check by eye: conjuncts (e.g. the first Hindi word) must be joined, not split into separate letters.", 9, (0.3, 0.3, 0.3))
            dst = save_pdf(doc, unique_path(out, "indic_test", ".pdf"))
            return {"message": "Test PDF created:\n%s\n\nOpen it and check each script." % dst, "files": [dst]}
        return task


# ---------------------------------------------------------------- batch & automation
class BatchOp:
    def __init__(self, key, label, params, fn, terminal=False, ext=".pdf", prime=False):
        self.key, self.label, self.params, self.fn, self.terminal, self.ext, self.prime = key, label, params, fn, terminal, ext, prime


def _bo_compress(src, dst, p, ctx):
    o, n, _ = core_compress(src, dst, p.get("level", "High quality"), cancelled=ctx.get("cancelled"))
    if not os.path.exists(dst):
        shutil.copyfile(src, dst)


def _bo_ocr(src, dst, p, ctx):
    require_tess()
    core_ocr_pdf(src, dst, p.get("lang", "eng"), int(p.get("dpi", 300)), None, True, None, None, ctx["cancelled"])


def _bo_cleanup(src, dst, p, ctx):
    core_cleanup_pdf(src, dst, {k: bool(p.get(k)) for k in ("deskew", "crop", "shadow", "denoise", "contrast", "bw")}, int(p.get("dpi", 200)), None, ctx["cancelled"])


def _bo_number(src, dst, p, ctx):
    core_number_pages(src, dst, int(p.get("start", 1)), p.get("fmt", "Page 1 of N"), p.get("pos", "bottom-center"),
                      int(p.get("size", 10)), int(p.get("margin", 24)), COLORS[p.get("color", "Black")])


def _bo_hf(src, dst, p, ctx):
    d = open_pdf(src)
    n = d.page_count
    d.close()
    texts = {"top-left": p.get("top_left", ""), "top-center": p.get("top_center", ""), "top-right": p.get("top_right", ""),
             "bottom-left": p.get("bottom_left", ""), "bottom-center": p.get("bottom_center", ""), "bottom-right": p.get("bottom_right", "")}
    core_header_footer(src, dst, texts, int(p.get("size", 9)), 24, COLORS[p.get("color", "Gray")], list(range(n)), False)


def _bo_strip(src, dst, p, ctx):
    core_strip(src, dst, {"meta": True, "attach": True, "js": True, "thumbs": True, "annots": bool(p.get("annots")), "bookmarks": bool(p.get("bookmarks"))})


def _bo_repair(src, dst, p, ctx):
    core_repair(src, dst)


def _bo_rotate(src, dst, p, ctx):
    d = open_pdf(src)
    op_rotate(d, list(range(d.page_count)), int(p.get("angle", 90)))
    save_pdf(d, dst)


def _bo_pdfa(src, dst, p, ctx):
    core_pdfa(src, dst)


def _bo_text(src, dst, p, ctx):
    d = open_pdf(src)
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n\n".join("----- Page %d -----\n%s" % (i + 1, d[i].get_text("text")) for i in range(d.page_count)))


def _bo_ai_rename(src, dst, p, ctx):
    shutil.copyfile(src, dst)
    ai = ctx.get("ai")
    if not ai:
        raise UserError("AI smart renaming needs a Prime login.")
    d = open_pdf(src)
    txt = "".join(d[i].get_text("text") for i in range(min(2, d.page_count)))[:3500]
    d.close()
    if txt.strip():
        nm = ai_suggest_name(ai, txt, ctx["cancelled"])
        if nm:
            ctx["name_override"] = safe_name(nm)


_PC = ["Black", "Gray", "Blue", "Red"]
BATCH_OPS = collections.OrderedDict((o.key, o) for o in [
    BatchOp("compress", "Compress", [("level", "Quality", "choice", "High quality", list(COMPRESS_PRESETS))], _bo_compress),
    BatchOp("cleanup", "Scan clean-up", [("deskew", "Straighten", "bool", True, None), ("crop", "Crop borders", "bool", True, None),
            ("shadow", "Remove shadows", "bool", False, None), ("denoise", "Denoise", "bool", False, None),
            ("contrast", "Contrast", "bool", True, None), ("bw", "Black & white", "bool", False, None),
            ("dpi", "DPI", "choice", "200", ["150", "200", "300"])], _bo_cleanup),
    BatchOp("ocr", "OCR (searchable)", [("lang", "Language code(s)", "text", "eng", None), ("dpi", "DPI", "choice", "300", ["200", "300", "400"])], _bo_ocr),
    BatchOp("number", "Page numbers", [("start", "Start at", "int", 1, None), ("fmt", "Format", "choice", "Page 1 of N", NUMBER_FORMATS),
            ("pos", "Position", "choice", "bottom-center", [p[1] for p in POSITIONS]), ("size", "Font size", "int", 10, None),
            ("margin", "Margin", "int", 24, None), ("color", "Colour", "choice", "Black", _PC)], _bo_number),
    BatchOp("headerfooter", "Header / footer", [("top_left", "Top left", "text", "{docname}", None), ("top_center", "Top center", "text", "", None),
            ("top_right", "Top right", "text", "{date}", None), ("bottom_left", "Bottom left", "text", "", None),
            ("bottom_center", "Bottom center", "text", "Page {page} of {total}", None), ("bottom_right", "Bottom right", "text", "", None),
            ("size", "Font size", "int", 9, None), ("color", "Colour", "choice", "Gray", _PC)], _bo_hf),
    BatchOp("rotate", "Rotate all pages", [("angle", "Degrees clockwise", "choice", "90", ["90", "180", "270"])], _bo_rotate),
    BatchOp("strip", "Strip metadata/attachments", [("annots", "Remove annotations", "bool", False, None), ("bookmarks", "Remove bookmarks", "bool", False, None)], _bo_strip),
    BatchOp("repair", "Repair", [], _bo_repair),
    BatchOp("pdfa", "PDF/A (best effort)", [], _bo_pdfa),
    BatchOp("ai_rename", "AI smart rename by document type (Prime)", [], _bo_ai_rename, prime=True),
    BatchOp("to_text", "Extract text to .txt (final step)", [], _bo_text, terminal=True, ext=".txt"),
])


class ParamDialog(QDialog):
    def __init__(self, parent, op, values=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle(op.label)
        self.op, self.w = op, {}
        v = QFormLayout(self)
        for key, label, typ, default, choices in op.params:
            cur = (values or {}).get(key, default)
            if typ == "choice":
                w = QComboBox()
                w.addItems([str(c) for c in choices])
                w.setCurrentText(str(cur))
            elif typ == "bool":
                w = QCheckBox()
                w.setChecked(bool(cur))
            elif typ == "int":
                w = QSpinBox()
                w.setRange(0, 99999999)
                w.setValue(int(cur))
            else:
                w = QLineEdit(str(cur))
            self.w[key] = (w, typ)
            v.addRow(label, w)
        if not op.params:
            v.addRow(QLabel("This step has no options."))
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addRow(bb)

    def values(self):
        o = {}
        for k, (w, typ) in self.w.items():
            o[k] = w.currentText() if typ == "choice" else w.isChecked() if typ == "bool" else w.value() if typ == "int" else w.text()
        return o


def collect_files(folder, include, exclude, recursive):
    inc = [x.strip() for x in re.split(r"[;,]", include or "*.pdf") if x.strip()] or ["*.pdf"]
    exc = [x.strip() for x in re.split(r"[;,]", exclude or "") if x.strip()]
    res = []
    for root, dirs, files in os.walk(folder):
        if not recursive:
            dirs[:] = []
        for f in sorted(files):
            if not f.lower().endswith(".pdf"):
                continue
            if any(fnmatch.fnmatch(f.lower(), p.lower()) for p in inc) and not any(fnmatch.fnmatch(f.lower(), p.lower()) for p in exc):
                res.append(os.path.join(root, f))
    return res


def run_pipeline(src, steps, out_dir, pattern, n, ctxd):
    """Run the steps on one file. Returns the final output path. The source file is never modified."""
    stem = os.path.splitext(os.path.basename(src))[0]
    with TempDir() as td:
        cur, ext = src, ".pdf"
        ctxd = dict(ctxd)
        ctxd.pop("name_override", None)
        for i, st in enumerate(steps):
            op = BATCH_OPS[st["op"]]
            if ctxd["cancelled"]():
                raise Cancelled()
            nxt = os.path.join(td, "s%d%s" % (i, op.ext))
            op.fn(cur, nxt, st.get("params", {}), ctxd)
            if not os.path.exists(nxt):
                shutil.copyfile(cur, nxt)
            cur, ext = nxt, op.ext
        name = ctxd.get("name_override") or stem
        base = pattern.replace("{name}", name).replace("{date}", dt.date.today().isoformat()).replace("{n}", "%03d" % n)
        dst = unique_path(out_dir, safe_name(base), ext)
        shutil.copyfile(cur, dst)
        return dst


class BatchTool(ToolPage):
    key, title, group = "batch", "Batch & Hot Folder", "Automation"
    subtitle = "Run a chain of steps over a whole folder, or watch a folder and process new PDFs automatically."
    action_text = "Run batch now"

    def build(self, L):
        self.folder = QLineEdit()
        self.folder.setPlaceholderText("Folder containing the PDFs")
        fb = QPushButton("Browse...")
        fb.clicked.connect(lambda: self._pick(self.folder))
        self.add_row("Input folder", hbox(self.folder, fb))
        self.inc = QLineEdit("*.pdf")
        self.exc = QLineEdit()
        self.exc.setPlaceholderText("e.g. *_old*;*draft*")
        self.rec = QCheckBox("Include sub-folders")
        L.addWidget(hbox(QLabel("Include"), self.inc, QLabel("Exclude"), self.exc, self.rec))
        self.pattern = QLineEdit("{name}_processed")
        self.add_row("Output file name pattern", self.pattern, "Tokens: {name} (original name), {date}, {n} (counter). Existing names get _1, _2...")
        self.steps = []
        self.steplist = QListWidget()
        self.steplist.setMaximumHeight(130)
        self.add_row("Steps (run in this order)", self.steplist)
        self.opbox = self.combo([(o.label, k) for k, o in BATCH_OPS.items()])
        row = QHBoxLayout()
        row.addWidget(self.opbox, 1)
        for text, fn in (("Add step", self.add_step), ("Edit options", self.edit_step), ("Remove", self.rem_step), ("Up", lambda: self.mv(-1)),
                         ("Down", lambda: self.mv(1)), ("Save pipeline", self.save_pipe), ("Load pipeline", self.load_pipe)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        L.addLayout(row)
        self.cont = QCheckBox("Continue with the next file if one fails")
        self.cont.setChecked(True)
        L.addWidget(self.cont)
        # hot folder
        L.addWidget(hint_label("Hot folder: new PDFs appearing in the watched folder are processed with the steps above and saved to the output folder. "
                               "Originals stay where they are."))
        self.watch = QLineEdit()
        wb = QPushButton("Browse...")
        wb.clicked.connect(lambda: self._pick(self.watch))
        self.interval = self.spin(3, 3600, 10, " s")
        self.btn_watch = QPushButton("Start watching")
        self.btn_watch.setCheckable(True)
        self.btn_watch.toggled.connect(self.toggle_watch)
        L.addWidget(hbox(QLabel("Watch folder"), self.watch, wb, QLabel("Check every"), self.interval, self.btn_watch))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.seen, self.sizes, self.queue, self.hot_counter = set(), {}, [], 0
        self.busy_hot = False

    def after_build(self):
        self.steps = [{"op": "compress", "params": {"level": "High quality"}}]
        self.refresh_steps()

    def _pick(self, edit):
        d = QFileDialog.getExistingDirectory(self, "Select folder", edit.text() or SET.last_dir("batch"))
        if d:
            edit.setText(d)
            SET.remember_dir("batch", d)

    def refresh_steps(self):
        self.steplist.clear()
        for i, s in enumerate(self.steps):
            op = BATCH_OPS[s["op"]]
            desc = ", ".join("%s=%s" % (k, v) for k, v in list(s["params"].items())[:4])
            self.steplist.addItem("%d. %s   %s" % (i + 1, op.label, ("(" + desc + ")") if desc else ""))

    def add_step(self):
        k = self.opbox.currentData()
        op = BATCH_OPS[k]
        if op.prime and not getattr(self.ctx, "is_prime", False):
            self.warn("This step is available to Prime users.")
            return
        if self.steps and BATCH_OPS[self.steps[-1]["op"]].terminal:
            self.warn("The last step already produces a final file; no step can follow it.")
            return
        d = ParamDialog(self, op)
        if op.params and d.exec_() != QDialog.Accepted:
            return
        self.steps.append({"op": k, "params": d.values() if op.params else {}})
        self.refresh_steps()

    def edit_step(self):
        r = self.steplist.currentRow()
        if r < 0:
            return
        op = BATCH_OPS[self.steps[r]["op"]]
        d = ParamDialog(self, op, self.steps[r]["params"])
        if op.params and d.exec_() == QDialog.Accepted:
            self.steps[r]["params"] = d.values()
            self.refresh_steps()

    def rem_step(self):
        r = self.steplist.currentRow()
        if r >= 0:
            self.steps.pop(r)
            self.refresh_steps()

    def mv(self, d):
        r = self.steplist.currentRow()
        if 0 <= r + d < len(self.steps):
            self.steps[r], self.steps[r + d] = self.steps[r + d], self.steps[r]
            self.refresh_steps()
            self.steplist.setCurrentRow(r + d)

    def save_pipe(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save pipeline", SET.last_dir("pipeline"), "Pipeline (*.json)")
        if p:
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"steps": self.steps, "pattern": self.pattern.text(), "include": self.inc.text(), "exclude": self.exc.text()}, f, indent=2)

    def load_pipe(self):
        p, _ = QFileDialog.getOpenFileName(self, "Load pipeline", SET.last_dir("pipeline"), "Pipeline (*.json)")
        if p:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                steps = [s for s in d["steps"] if s.get("op") in BATCH_OPS]
                self.steps = steps
                self.pattern.setText(d.get("pattern", "{name}_processed"))
                self.inc.setText(d.get("include", "*.pdf"))
                self.exc.setText(d.get("exclude", ""))
                self.refresh_steps()
            except Exception:
                self.warn("That pipeline file could not be read.")

    def _ctxd(self, cancelled):
        d = {"cancelled": cancelled}
        if getattr(self.ctx, "is_prime", False):
            d["ai"] = self.ctx.ai
        return d

    def _check_steps(self):
        if not self.steps:
            raise UserError("Add at least one step.")
        for s in self.steps:
            if BATCH_OPS[s["op"]].prime and not getattr(self.ctx, "is_prime", False):
                raise UserError("The step '%s' is available to Prime users only." % BATCH_OPS[s["op"]].label)

    def make_task(self, out):
        folder = self.folder.text().strip()
        if not folder or not os.path.isdir(folder):
            raise UserError("Choose the input folder.")
        self._check_steps()
        files = collect_files(folder, self.inc.text(), self.exc.text(), self.rec.isChecked())
        if not files:
            raise UserError("No PDF files match in that folder.")
        steps, pattern, cont = list(self.steps), self.pattern.text().strip() or "{name}", self.cont.isChecked()
        ctxd_f = self._ctxd

        def task(report, cancelled):
            rows, ok, bad = [], 0, 0
            ctxd = ctxd_f(cancelled)
            for i, f in enumerate(files):
                report(100.0 * i / len(files), "%d/%d  %s" % (i + 1, len(files), os.path.basename(f)))
                try:
                    dst = run_pipeline(f, steps, out, pattern, i + 1, ctxd)
                    rows.append((f, "OK", dst))
                    ok += 1
                except Cancelled:
                    raise
                except Exception as e:
                    bad += 1
                    if not isinstance(e, UserError):
                        log_exc("batch file")
                    rows.append((f, "FAILED", str(e).splitlines()[0] if str(e) else type(e).__name__))
                    if not cont:
                        break
            rep = unique_path(out, "batch_report", ".csv")
            with open(rep, "w", encoding="utf-8-sig", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["Input file", "Result", "Output / error"])
                w.writerows(rows)
            return {"message": "Batch finished: %d succeeded, %d failed.\nReport: %s" % (ok, bad, rep), "files": [rep]}
        return task

    # ---- hot folder
    def toggle_watch(self, on):
        if on:
            try:
                wf = self.watch.text().strip()
                if not wf or not os.path.isdir(wf):
                    raise UserError("Choose the folder to watch.")
                out = ensure_out_dir(self.out_picker.path())
                self._check_steps()
                if os.path.abspath(wf) == os.path.abspath(out):
                    raise UserError("The output folder must be different from the watched folder.")
            except UserError as e:
                self.btn_watch.blockSignals(True)
                self.btn_watch.setChecked(False)
                self.btn_watch.blockSignals(False)
                self.warn(str(e))
                return
            self.seen = set(os.path.join(wf, f) for f in os.listdir(wf) if f.lower().endswith(".pdf")) if self._skip_existing() else set()
            self.sizes, self.queue = {}, []
            self.timer.start(self.interval.value() * 1000)
            self.btn_watch.setText("Stop watching")
            self.status.setText("Watching %s ..." % wf)
            self.log("Watching started. Existing files are %s." % ("ignored" if self.seen else "processed"))
        else:
            self.timer.stop()
            self.btn_watch.setText("Start watching")
            self.status.setText("Watching stopped.")

    def _skip_existing(self):
        return QMessageBox.question(self, APP_NAME, "Ignore the PDFs that are already in the watched folder?\n(Yes = only new files; No = process existing files too)") == QMessageBox.Yes

    def poll(self):
        wf = self.watch.text().strip()
        if not os.path.isdir(wf):
            return
        for f in os.listdir(wf):
            p = os.path.join(wf, f)
            if f.lower().endswith(".pdf") and p not in self.seen:
                try:
                    sz = os.path.getsize(p)
                except OSError:
                    continue
                if self.sizes.get(p) == sz and sz > 0:          # unchanged since last poll = fully copied
                    self.seen.add(p)
                    self.queue.append(p)
                else:
                    self.sizes[p] = sz
        if self.queue and not self.busy_hot and not (self.worker and self.worker.isRunning()):
            self._run_hot(self.queue.pop(0))

    def _run_hot(self, f):
        out = self.out_picker.path()
        steps, pattern = list(self.steps), self.pattern.text().strip() or "{name}"
        self.hot_counter += 1
        n = self.hot_counter
        ctxd_f = self._ctxd
        self.busy_hot = True

        def task(report, cancelled):
            return {"file": f, "dst": run_pipeline(f, steps, out, pattern, n, ctxd_f(cancelled))}

        def ok(res):
            self.busy_hot = False
            self.log("OK: %s -> %s" % (os.path.basename(res["file"]), res["dst"]))
            self.status.setText("Watching... last: %s" % os.path.basename(res["dst"]))

        def fail(msg):
            self.busy_hot = False
            self.log("FAILED: %s - %s" % (os.path.basename(f), str(msg).splitlines()[0] if msg else ""))
        w = Worker(task, self)
        w.succeeded.connect(ok)
        w.failed.connect(lambda m, u: fail(m))
        w.cancelled.connect(lambda: fail("cancelled"))
        self.worker = w
        w.start()

    def shutdown(self):
        self.timer.stop()
        ToolPage.shutdown(self)
# ============================================================================
#  SECTION L - PHASE 6: IMAGE TOOLS
# ============================================================================
def need_pil():
    if not HAVE_PIL:
        raise UserError("The image tools need the Pillow library.\nRun:  pip install Pillow")


def load_image(path):
    need_pil()
    try:
        im = Image.open(path)
        im.load()
    except Exception:
        raise UserError("The image '%s' could not be read." % os.path.basename(path))
    try:
        im = ImageOps.exif_transpose(im)
    except Exception:
        pass
    return im


FORMATS = {"JPG": (".jpg", "JPEG"), "PNG": (".png", "PNG"), "WebP": (".webp", "WEBP"), "TIFF": (".tif", "TIFF"), "BMP": (".bmp", "BMP")}


def save_image(im, path, fmt_key, quality=90):
    ext, pf = FORMATS[fmt_key]
    kw = {}
    if pf in ("JPEG", "WEBP"):
        kw["quality"] = int(quality)
        if pf == "JPEG":
            kw["optimize"] = True
        if im.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            rgba = im.convert("RGBA")
            bg.paste(rgba, mask=rgba.split()[-1])
            im = bg
        elif im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
    elif pf == "PNG":
        kw["optimize"] = True
    elif pf == "TIFF":
        kw["compression"] = "tiff_lzw"
        if im.mode == "P":
            im = im.convert("RGB")
    elif pf == "BMP" and im.mode not in ("RGB", "L", "P", "1"):
        im = im.convert("RGB")
    im.save(path, pf, **kw)
    return path


def fmt_key_of(path):
    e = os.path.splitext(path)[1].lower()
    return {".jpg": "JPG", ".jpeg": "JPG", ".png": "PNG", ".webp": "WebP", ".tif": "TIFF", ".tiff": "TIFF", ".bmp": "BMP"}.get(e, "PNG")


class ImageEditTool(ToolPage):
    key, title, group = "imgedit", "Resize, Crop, Rotate, Convert", "Images"
    subtitle = "Edit many pictures at once: resize, crop to a shape, rotate, flip and change the file type."

    def build(self, L):
        self.files = FileListWidget("imgedit", IMG_EXT, "Images (*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp)", "Select images")
        self.add_row("Images", self.files)
        self.c_resize = QCheckBox("Resize")
        self.rmode = self.combo([("Percent of original", "pct"), ("Width (keep shape)", "w"), ("Height (keep shape)", "h"), ("Fit inside width x height", "fit"), ("Exact width x height", "exact")])
        self.rw, self.rh = self.spin(1, 20000, 50), self.spin(1, 20000, 1000)
        L.addWidget(hbox(self.c_resize, self.rmode, QLabel("Value / width"), self.rw, QLabel("Height"), self.rh, None))
        self.c_crop = QCheckBox("Crop to shape (centered)")
        self.ratio = self.combo(["1:1", "4:5", "3:4", "4:3", "16:9", "9:16", "35:45", "3:2"])
        self.margin_pct = self.spin(0, 45, 0, " % off each side")
        L.addWidget(hbox(self.c_crop, self.ratio, QLabel("then trim"), self.margin_pct, None))
        self.c_rot = QCheckBox("Rotate")
        self.rot = self.combo([("90 degrees clockwise", 270), ("180 degrees", 180), ("90 degrees anticlockwise", 90), ("Custom angle", 0)])
        self.angle = self.spin(-180, 180, 0, " deg")
        self.flip_h, self.flip_v = QCheckBox("Flip left-right"), QCheckBox("Flip top-bottom")
        L.addWidget(hbox(self.c_rot, self.rot, self.angle, self.flip_h, self.flip_v, None))
        self.fmt = self.combo(["Keep original type"] + list(FORMATS.keys()))
        self.q = self.spin(10, 100, 90, " %")
        self.suffix = QLineEdit("_edited")
        L.addWidget(hbox(QLabel("Save as"), self.fmt, QLabel("Quality (JPG/WebP)"), self.q, QLabel("Name ending"), self.suffix, None))

    def make_task(self, out):
        files = self.files.paths()
        if not files:
            raise UserError("Add at least one image.")
        need_pil()
        o = dict(resize=self.c_resize.isChecked(), rmode=self.rmode.currentData(), rw=self.rw.value(), rh=self.rh.value(),
                 crop=self.c_crop.isChecked(), ratio=self.ratio.currentText(), trim=self.margin_pct.value(),
                 rot=self.c_rot.isChecked(), rdeg=self.rot.currentData() or self.angle.value(), fh=self.flip_h.isChecked(), fv=self.flip_v.isChecked(),
                 fmt=self.fmt.currentText(), q=self.q.value(), suffix=self.suffix.text())
        if not (o["resize"] or o["crop"] or o["rot"] or o["fh"] or o["fv"] or o["fmt"] != "Keep original type"):
            raise UserError("Choose at least one change (resize, crop, rotate, flip or a new file type).")

        def task(report, cancelled):
            res = []
            for k, f in enumerate(files):
                report(3 + 92 * k / len(files), os.path.basename(f))
                im = load_image(f)
                if o["crop"]:
                    a, b = [float(x) for x in o["ratio"].split(":")]
                    w, h = im.size
                    tw = min(w, h * a / b)
                    th = tw * b / a
                    l, t = (w - tw) / 2, (h - th) / 2
                    im = im.crop((int(l), int(t), int(l + tw), int(t + th)))
                    if o["trim"]:
                        w, h = im.size
                        mx, my = int(w * o["trim"] / 100), int(h * o["trim"] / 100)
                        im = im.crop((mx, my, w - mx, h - my))
                if o["resize"]:
                    w, h = im.size
                    m = o["rmode"]
                    if m == "pct":
                        nw, nh = int(w * o["rw"] / 100), int(h * o["rw"] / 100)
                    elif m == "w":
                        nw, nh = o["rw"], int(h * o["rw"] / w)
                    elif m == "h":
                        nw, nh = int(w * o["rh"] / h), o["rh"]
                    elif m == "fit":
                        s = min(o["rw"] / w, o["rh"] / h)
                        nw, nh = int(w * s), int(h * s)
                    else:
                        nw, nh = o["rw"], o["rh"]
                    im = im.resize((max(1, nw), max(1, nh)), Image.LANCZOS)
                if o["rot"]:
                    im = im.rotate(o["rdeg"], expand=True, resample=Image.BICUBIC, fillcolor=(255, 255, 255) if im.mode == "RGB" else None)
                if o["fh"]:
                    im = ImageOps.mirror(im)
                if o["fv"]:
                    im = ImageOps.flip(im)
                fk = fmt_key_of(f) if o["fmt"] == "Keep original type" else o["fmt"]
                p = unique_path(out, os.path.splitext(os.path.basename(f))[0] + o["suffix"], FORMATS[fk][0])
                res.append(save_image(im, p, fk, o["q"]))
            return {"message": "Saved %d image(s)." % len(res), "files": res}
        return task


class ImageCompressTool(ToolPage):
    key, title, group = "imgcompress", "Compress Image to Target Size", "Images"
    subtitle = "Make pictures fit a size limit (for example 'under 200 KB' for a portal upload)."

    def build(self, L):
        self.files = FileListWidget("imgcompress", IMG_EXT, "Images (*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp)", "Select images")
        self.add_row("Images", self.files)
        self.kb = self.spin(5, 50000, 200, " KB")
        self.fmt = self.combo(["JPG", "WebP"])
        self.minside = self.spin(100, 20000, 600, " px")
        L.addWidget(hbox(QLabel("Largest allowed size"), self.kb, QLabel("Save as"), self.fmt, QLabel("Never go smaller than (long side)"), self.minside, None))
        self.add_hint("Quality is reduced first; if that is not enough the picture is made slightly smaller until the limit is met.")

    def make_task(self, out):
        files = self.files.paths()
        if not files:
            raise UserError("Add at least one image.")
        need_pil()
        target, fk, minside = self.kb.value() * 1024, self.fmt.currentText(), self.minside.value()

        def task(report, cancelled):
            res, notes = [], []
            for k, f in enumerate(files):
                report(3 + 92 * k / len(files), os.path.basename(f))
                im = load_image(f)
                if im.mode not in ("RGB", "L"):
                    bg = Image.new("RGB", im.size, (255, 255, 255))
                    rgba = im.convert("RGBA")
                    bg.paste(rgba, mask=rgba.split()[-1])
                    im = bg
                best = None
                cur = im
                while True:
                    lo, hi, found = 10, 95, None
                    while lo <= hi:
                        mid = (lo + hi) // 2
                        buf = io.BytesIO()
                        cur.save(buf, FORMATS[fk][1], quality=mid, optimize=(fk == "JPG"))
                        if buf.tell() <= target:
                            found, lo = (mid, buf.getvalue()), mid + 1
                        else:
                            hi = mid - 1
                    if found:
                        best = found[1]
                        break
                    w, h = cur.size
                    if max(w, h) * 0.88 < minside:
                        buf = io.BytesIO()
                        cur.save(buf, FORMATS[fk][1], quality=10)
                        best = buf.getvalue()
                        notes.append("%s could not reach the limit (smallest possible: %s)" % (os.path.basename(f), human_size(len(best))))
                        break
                    cur = cur.resize((int(w * 0.88), int(h * 0.88)), Image.LANCZOS)
                p = unique_path(out, os.path.splitext(os.path.basename(f))[0] + "_small", FORMATS[fk][0])
                with open(p, "wb") as fh:
                    fh.write(best)
                res.append(p)
            return {"message": "Saved %d image(s).%s" % (len(res), ("\n\n" + "\n".join(notes)) if notes else ""), "files": res}
        return task


class ExifStripTool(ToolPage):
    key, title, group = "exif", "Remove EXIF & Location", "Images"
    subtitle = "Strip camera details, dates and GPS location from photos before sharing."

    def build(self, L):
        self.files = FileListWidget("exif", IMG_EXT, "Images (*.jpg *.jpeg *.png *.tif *.tiff *.webp)", "Select photos")
        self.add_row("Photos", self.files)
        self.add_hint("Cleaned copies are saved (JPEG at quality 95). The picture is first rotated upright, then all metadata is dropped.")

    def make_task(self, out):
        files = self.files.paths()
        if not files:
            raise UserError("Add at least one photo.")
        need_pil()

        def task(report, cancelled):
            res, gps = [], 0
            for k, f in enumerate(files):
                report(3 + 92 * k / len(files), os.path.basename(f))
                raw = Image.open(f)
                try:
                    ex = raw.getexif()
                    if ex and 0x8825 in ex:
                        gps += 1
                except Exception:
                    pass
                im = load_image(f)
                clean = Image.new(im.mode, im.size)
                clean.paste(im)
                fk = fmt_key_of(f)
                p = unique_path(out, os.path.splitext(os.path.basename(f))[0] + "_clean", FORMATS[fk][0])
                res.append(save_image(clean, p, fk, 95))
            return {"message": "Cleaned %d photo(s). GPS location was found and removed in %d of them." % (len(res), gps), "files": res}
        return task


# ---------------------------------------------------------------- blur / mask
class RegionPicker(QWidget):
    """Shows an image; drag to mark rectangles (stored as fractions of the image size)."""

    def __init__(self, maxw=720, maxh=420):
        QWidget.__init__(self)
        self.pm, self.rects, self.maxw, self.maxh = None, [], maxw, maxh
        self.start = self.now = None
        self.setMinimumHeight(200)
        self.setCursor(Qt.CrossCursor)

    def set_image(self, path):
        im = QImage(path)
        if im.isNull():
            self.pm = None
        else:
            self.pm = QPixmap.fromImage(im).scaled(self.maxw, self.maxh, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setFixedSize(self.pm.size())
        self.rects = []
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        if not self.pm:
            p.drawText(self.rect(), Qt.AlignCenter, "Choose an image to mark areas")
            return
        p.drawPixmap(0, 0, self.pm)
        p.setPen(QPen(QColor(RED), 2))
        p.setBrush(QColor(214, 40, 57, 60))
        W, H = self.pm.width(), self.pm.height()
        for x0, y0, x1, y1 in self.rects:
            p.drawRect(QRectF(x0 * W, y0 * H, (x1 - x0) * W, (y1 - y0) * H))
        if self.start and self.now:
            p.drawRect(QRect(self.start, self.now).normalized())

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton and self.rects:
            self.rects.pop()
            self.update()
        elif self.pm:
            self.start = self.now = e.pos()

    def mouseMoveEvent(self, e):
        if self.start:
            self.now = e.pos()
            self.update()

    def mouseReleaseEvent(self, e):
        if self.start and self.pm:
            r = QRect(self.start, e.pos()).normalized() & self.rect()
            self.start = self.now = None
            if r.width() > 4 and r.height() > 4:
                W, H = self.pm.width(), self.pm.height()
                self.rects.append((r.left() / W, r.top() / H, r.right() / W, r.bottom() / H))
            self.update()


class BlurMaskTool(ToolPage):
    key, title, group = "imgmask", "Blur / Mask Areas", "Images"
    subtitle = "Hide faces, numbers or addresses in a picture: draw rectangles, then blur, pixelate or black them out."

    def build(self, L):
        self.img = FilePicker("imgmask", IMG_EXT, "Select image", "Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp)")
        self.add_row("Image", self.img)
        self.img.changed.connect(lambda p: self.picker.set_image(p) if os.path.isfile(p) else None)
        self.picker = RegionPicker()
        L.addWidget(self.picker)
        self.add_hint("Drag to mark an area. Right-click removes the last one.")
        self.mode = self.combo([("Pixelate (hard to undo)", "pix"), ("Solid black box (safest)", "black"), ("Blur", "blur")])
        self.strength = self.spin(4, 80, 20)
        L.addWidget(hbox(QLabel("Style"), self.mode, QLabel("Strength"), self.strength, None))
        self.add_hint("For anything confidential choose the solid black box - blur and pixelation can sometimes be reversed.")

    def make_task(self, out):
        p = self.img.path()
        if not p or not os.path.isfile(p):
            raise UserError("Choose an image first.")
        if not self.picker.rects:
            raise UserError("Draw at least one area on the picture.")
        need_pil()
        rects, mode, st = list(self.picker.rects), self.mode.currentData(), self.strength.value()

        def task(report, cancelled):
            im = load_image(p).convert("RGB")
            W, H = im.size
            for x0, y0, x1, y1 in rects:
                box = (int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))
                reg = im.crop(box)
                if mode == "black":
                    reg = Image.new("RGB", reg.size, (0, 0, 0))
                elif mode == "blur":
                    reg = reg.filter(ImageFilter.GaussianBlur(st))
                else:
                    sw, sh = max(1, reg.width // st), max(1, reg.height // st)
                    reg = reg.resize((sw, sh), Image.BILINEAR).resize(reg.size, Image.NEAREST)
                im.paste(reg, box)
            fk = fmt_key_of(p)
            dst = save_image(im, unique_path(out, os.path.splitext(os.path.basename(p))[0] + "_masked", FORMATS[fk][0]), fk, 95)
            return {"message": "Saved:\n%s" % dst, "files": [dst]}
        return task


# ---------------------------------------------------------------- image watermark
class ImageWatermarkTool(ToolPage):
    key, title, group = "imgwm", "Watermark Images", "Images"
    subtitle = "Add a text or logo watermark to many pictures."

    def build(self, L):
        self.files = FileListWidget("imgwm", IMG_EXT, "Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp)", "Select images")
        self.add_row("Images", self.files)
        self.kind = self.combo(["Text", "Logo image"])
        self.text = QLineEdit("CONFIDENTIAL")
        self.logo = FilePicker("imgwm_logo", IMG_EXT, "Select logo", "Images (*.png *.jpg *.jpeg *.bmp)", "Logo file")
        L.addWidget(hbox(QLabel("Watermark"), self.kind, self.text))
        L.addWidget(self.logo)
        self.pos = self.combo([p[0] for p in WM_POS])
        self.size = self.spin(5, 100, 35, " % of width")
        self.opacity = self.spin(5, 100, 40, " %")
        self.angle = self.spin(-90, 90, 0, " deg")
        self.color = self.combo(list(COLORS.keys()), "White")
        L.addWidget(hbox(QLabel("Position"), self.pos, QLabel("Size"), self.size, QLabel("Opacity"), self.opacity, QLabel("Angle"), self.angle, QLabel("Colour"), self.color))
        self.fmt = self.combo(["Keep original type"] + list(FORMATS.keys()))
        self.add_row("Save as", self.fmt)

    def make_task(self, out):
        files = self.files.paths()
        if not files:
            raise UserError("Add at least one image.")
        need_pil()
        op, ang, pos = self.opacity.value() / 100.0, self.angle.value(), WM_POS[self.pos.currentIndex()][1]
        scale = self.size.value() / 100.0
        if self.kind.currentIndex() == 0:
            t = self.text.text().strip()
            if not t:
                raise UserError("Type the watermark text.")
            qi = render_text_image(t, 160, COLORS[self.color.currentText()], 1.0, 0)
            wm = Image.open(io.BytesIO(qimage_to_png(qi))).convert("RGBA")
        else:
            lp = self.logo.path()
            if not lp or not os.path.isfile(lp):
                raise UserError("Choose the logo file.")
            wm = Image.open(lp).convert("RGBA")
        a = wm.split()[3].point(lambda v: int(v * op))
        wm.putalpha(a)
        if ang:
            wm = wm.rotate(ang, expand=True, resample=Image.BICUBIC)
        fmt = self.fmt.currentText()

        def task(report, cancelled):
            res = []
            for k, f in enumerate(files):
                report(3 + 92 * k / len(files), os.path.basename(f))
                im = load_image(f).convert("RGBA")
                W, H = im.size
                w = max(8, int(W * scale))
                h = max(8, int(w * wm.height / wm.width))
                m = wm.resize((w, h), Image.LANCZOS)
                if pos == "tile":
                    for y in range(0, H, int(h * 2.2)):
                        for x in range(-(w if (y // int(h * 2.2)) % 2 else 0), W, int(w * 1.6)):
                            im.alpha_composite(m, (max(0, x), y)) if x >= 0 and x + w <= W and y + h <= H else None
                else:
                    mg = int(W * 0.03)
                    xs = {"l": mg, "c": (W - w) // 2, "r": W - w - mg}
                    ys = {"t": mg, "c": (H - h) // 2, "b": H - h - mg}
                    x, y = (xs["c"], ys["c"]) if pos == "center" else (xs[pos[1]], ys[pos[0]])
                    im.alpha_composite(m, (max(0, x), max(0, y)))
                fk = fmt_key_of(f) if fmt == "Keep original type" else fmt
                p = unique_path(out, os.path.splitext(os.path.basename(f))[0] + "_wm", FORMATS[fk][0])
                res.append(save_image(im, p, fk, 92))
            return {"message": "Saved %d image(s)." % len(res), "files": res}
        return task


# ---------------------------------------------------------------- passport photo
PASSPORT_SIZES = [("35 x 45 mm  (India passport/visa, UK, Schengen)", 35, 45), ("25 x 35 mm  (PAN card)", 25, 35),
                  ("2 x 2 inch  (USA)", 50.8, 50.8), ("Custom", 0, 0)]


def detect_face(arr_gray):
    if not HAVE_CV2:
        return None
    try:
        xml = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        if not os.path.isfile(xml):
            return None
        casc = cv2.CascadeClassifier(xml)
        fs = casc.detectMultiScale(arr_gray, 1.1, 5, minSize=(60, 60))
        if len(fs):
            return max(fs, key=lambda r: r[2] * r[3])
    except Exception:
        pass
    return None


class PassportTool(ToolPage):
    key, title, group = "passport", "Passport Photo Maker", "Images"
    subtitle = "Crop a portrait to a standard photo size on a white background and make a print sheet."

    def build(self, L):
        self.img = FilePicker("passport", IMG_EXT, "Select portrait photo", "Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp)")
        self.add_row("Portrait photo", self.img)
        self.size = self.combo([s[0] for s in PASSPORT_SIZES])
        self.cw, self.ch = self.dspin(10, 200, 35, " mm", 1, 1), self.dspin(10, 200, 45, " mm", 1, 1)
        L.addWidget(hbox(QLabel("Photo size"), self.size, QLabel("Custom W"), self.cw, QLabel("H"), self.ch, None))
        self.sheet = self.combo([("4 x 6 inch (102 x 152 mm)", (101.6, 152.4)), ("A4", (210, 297)), ("5 x 7 inch", (127, 177.8))])
        self.copies = self.spin(1, 60, 8)
        self.dpi = self.combo(["300", "600"], "300")
        L.addWidget(hbox(QLabel("Print sheet"), self.sheet, QLabel("Copies"), self.copies, QLabel("DPI"), self.dpi, None))
        self.auto = QCheckBox("Find the face and centre the head automatically")
        self.auto.setChecked(True)
        self.rembg = QCheckBox("Replace background with white (needs the optional 'rembg' package + a one-time model download)")
        L.addWidget(self.auto)
        L.addWidget(self.rembg)
        self.add_hint("Without background removal, use a photo taken against a plain light wall. Check the official size/head-position rules of the "
                      "office that will receive the photo - rules differ.")

    def make_task(self, out):
        p = self.img.path()
        if not p or not os.path.isfile(p):
            raise UserError("Choose a photo first.")
        need_pil()
        pre = PASSPORT_SIZES[self.size.currentIndex()]
        wmm, hmm = (self.cw.value(), self.ch.value()) if pre[1] == 0 else (pre[1], pre[2])
        sw, sh = self.sheet.currentData()
        dpi, copies, auto, rb = int(self.dpi.currentText()), self.copies.value(), self.auto.isChecked(), self.rembg.isChecked()
        if rb:
            try:
                import rembg  # noqa
            except ImportError:
                raise UserError("Background removal needs the optional package 'rembg'.\nRun:  pip install rembg\n"
                                "(It downloads a ~170 MB model the first time and needs internet; turn Strict Offline Mode off for that.)")

        def task(report, cancelled):
            im = load_image(p).convert("RGB")
            if rb:
                import rembg
                cut = rembg.remove(im.convert("RGBA"))
                bg = Image.new("RGB", cut.size, (255, 255, 255))
                bg.paste(cut, mask=cut.split()[-1])
                im = bg
            W, H = im.size
            aspect = wmm / hmm
            face = detect_face(np.asarray(im.convert("L"))) if (auto and HAVE_NP) else None
            if face is not None:
                fx, fy, fw, fh = [int(v) for v in face]
                ch_ = fh * 1.95
                cw_ = ch_ * aspect
                cx, cy = fx + fw / 2, fy + fh * 0.42
                box = (cx - cw_ / 2, cy - ch_ * 0.46, cx + cw_ / 2, cy + ch_ * 0.54)
                note = "Face found and centred."
            else:
                ch_ = min(H, W / aspect)
                cw_ = ch_ * aspect
                box = ((W - cw_) / 2, (H - ch_) / 2, (W + cw_) / 2, (H + ch_) / 2)
                note = "No face detected - centre crop used. Check the result."
            canvas = Image.new("RGB", (int(box[2] - box[0]), int(box[3] - box[1])), (255, 255, 255))
            canvas.paste(im, (-int(box[0]), -int(box[1])))
            pw, ph = int(wmm / 25.4 * dpi), int(hmm / 25.4 * dpi)
            photo = canvas.resize((pw, ph), Image.LANCZOS)
            single = save_image(photo, unique_path(out, "passport_photo", ".jpg"), "JPG", 95)
            SW, SH = int(sw / 25.4 * dpi), int(sh / 25.4 * dpi)
            if SW < SH and pw > ph and False:
                pass
            gap = int(2 / 25.4 * dpi)
            cols = max(1, (SW + gap) // (pw + gap))
            rows = max(1, (SH + gap) // (ph + gap))
            if cols * rows < copies and (SH + gap) // (pw + gap) * ((SW + gap) // (ph + gap)) > cols * rows:
                photo = photo.rotate(90, expand=True)
                pw, ph = ph, pw
                cols, rows = max(1, (SW + gap) // (pw + gap)), max(1, (SH + gap) // (ph + gap))
            n = min(copies, cols * rows)
            sheet = Image.new("RGB", (SW, SH), (255, 255, 255))
            x0 = (SW - (cols * pw + (cols - 1) * gap)) // 2
            y0 = gap * 2
            d = ImageDraw.Draw(sheet)
            for i in range(n):
                r, c_ = divmod(i, cols)
                x, y = x0 + c_ * (pw + gap), y0 + r * (ph + gap)
                sheet.paste(photo, (x, y))
                d.rectangle([x, y, x + pw - 1, y + ph - 1], outline=(190, 190, 190))
            sp = save_image(sheet, unique_path(out, "passport_sheet", ".jpg"), "JPG", 95)
            pdf = fitz.open()
            pg = pdf.new_page(width=sw / 25.4 * 72, height=sh / 25.4 * 72)
            pg.insert_image(pg.rect, filename=sp)
            pp = save_pdf(pdf, unique_path(out, "passport_sheet", ".pdf"))
            return {"message": "%s\nSingle photo, print sheet (%d copies) and a printable PDF were saved.\nPrint at 100%% size (no 'fit to page')." % (note, n), "files": [single, sp, pp]}
        return task


# ---------------------------------------------------------------- QR / barcode
class QrBarcodeTool(ToolPage):
    key, title, group = "qr", "QR & Barcode", "Images"
    subtitle = "Create QR codes and barcodes, or read them from pictures."

    def build(self, L):
        self.mode = self.combo(["Create", "Read from images"])
        self.add_row("What do you want to do?", self.mode)
        self.gen = QWidget(); g = QVBoxLayout(self.gen); g.setContentsMargins(0, 0, 0, 0)
        self.text = QLineEdit()
        self.text.setPlaceholderText("Text or web address (for barcodes: letters/digits)")
        self.kind = self.combo(["QR code", "Code 128 barcode", "EAN-13 barcode (12 digits)"])
        self.px = self.spin(100, 3000, 600, " px")
        g.addWidget(self.text)
        g.addWidget(hbox(QLabel("Type"), self.kind, QLabel("Size"), self.px, None))
        L.addWidget(self.gen)
        self.rd = QWidget(); r = QVBoxLayout(self.rd); r.setContentsMargins(0, 0, 0, 0)
        self.files = FileListWidget("qr", IMG_EXT, "Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp)", "Select images")
        r.addWidget(self.files)
        L.addWidget(self.rd)
        self.result = QTextEdit()
        self.result.setReadOnly(True)
        self.result.setMaximumHeight(100)
        L.addWidget(self.result)
        self.mode.currentIndexChanged.connect(self._m)
        self._m(0)

    def _m(self, i):
        self.gen.setVisible(i == 0)
        self.rd.setVisible(i == 1)

    def make_task(self, out):
        if self.mode.currentIndex() == 0:
            t = self.text.text().strip()
            if not t:
                raise UserError("Type the text for the code.")
            k, px = self.kind.currentIndex(), self.px.value()
            if k == 0:
                need_lib(HAVE_QR, "qrcode", "QR codes")
            else:
                need_lib(HAVE_BARCODE, "python-barcode", "Barcodes")
            if k == 2 and not re.fullmatch(r"\d{12}", t):
                raise UserError("EAN-13 needs exactly 12 digits (the 13th check digit is added automatically).")

            def task(report, cancelled):
                need_pil()
                if k == 0:
                    qr = pyqrcode.QRCode(error_correction=pyqrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
                    qr.add_data(t)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
                    img = img.resize((px, px), Image.NEAREST)
                    dst = unique_path(out, "qr_code", ".png")
                    img.save(dst)
                else:
                    from barcode.writer import ImageWriter
                    code = pybarcode.get("code128" if k == 1 else "ean13", t, writer=ImageWriter())
                    base = unique_path(out, "barcode", "")
                    dst = code.save(base, {"module_height": 15.0, "quiet_zone": 6.5, "write_text": True, "dpi": 300})
                return {"message": "Saved:\n%s" % dst, "files": [dst]}
            return task
        files = self.files.paths()
        if not files:
            raise UserError("Add at least one image to read.")
        require_cv()
        box = self.result

        def task(report, cancelled):
            lines = []
            for k_, f in enumerate(files):
                report(5 + 90 * k_ / len(files), os.path.basename(f))
                img = cv2.imdecode(np.fromfile(f, np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    lines.append("%s: cannot read the picture" % os.path.basename(f))
                    continue
                found = []
                try:
                    ok, infos, pts, _ = cv2.QRCodeDetector().detectAndDecodeMulti(img)
                    if ok:
                        found += [("QR", s) for s in infos if s]
                except Exception:
                    pass
                if hasattr(cv2, "barcode"):                  # OpenCV reads EAN-13/EAN-8/UPC only (not Code 128)
                    for sc in (1, 0.6, 0.4, 2):              # the detector is sensitive to picture size - try several
                        try:
                            im2 = img if sc == 1 else cv2.resize(img, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_CUBIC)
                            im2 = cv2.copyMakeBorder(im2, 40, 40, 80, 80, cv2.BORDER_CONSTANT, value=(255, 255, 255))
                            det = cv2.barcode.BarcodeDetector()
                            res = det.detectAndDecodeWithType(im2) if hasattr(det, "detectAndDecodeWithType") else det.detectAndDecode(im2)
                            infos, types = (res[1], res[2]) if len(res) >= 3 and isinstance(res[1], (list, tuple)) else ((res[0],), ("",))
                            got = [(str(t) or "barcode", s_) for t, s_ in zip(types, infos) if s_]
                            if got:
                                found += got
                                break
                        except Exception:
                            continue
                if found:
                    lines += ["%s: [%s] %s" % (os.path.basename(f), t, s) for t, s in found]
                else:
                    lines.append("%s: nothing readable found" % os.path.basename(f))
            dst = unique_path(out, "codes_read", ".txt")
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
            return {"message": "\n".join(lines[:12]) + "\n\nSaved: " + dst, "files": [dst]}
        return task


# ---------------------------------------------------------------- collage / contact sheet
class CollageTool(ToolPage):
    key, title, group = "collage", "Collage & Contact Sheet", "Images"
    subtitle = "Place many pictures on one sheet, in a grid, optionally with file names."

    def build(self, L):
        self.files = FileListWidget("collage", IMG_EXT, "Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp)", "Select images")
        self.add_row("Images (in order)", self.files)
        self.cols = self.spin(1, 12, 3)
        self.cell = self.spin(100, 1500, 500, " px")
        self.gap = self.spin(0, 100, 12, " px")
        self.bg = self.combo(["White", "Black", "Gray"])
        self.names = QCheckBox("Show file names under each picture (contact sheet)")
        L.addWidget(hbox(QLabel("Columns"), self.cols, QLabel("Picture size"), self.cell, QLabel("Spacing"), self.gap, QLabel("Background"), self.bg))
        L.addWidget(self.names)

    def make_task(self, out):
        files = self.files.paths()
        if not files:
            raise UserError("Add at least one image.")
        need_pil()
        cols, cell, gap, names = self.cols.value(), self.cell.value(), self.gap.value(), self.names.isChecked()
        bgc = {"White": (255, 255, 255), "Black": (0, 0, 0), "Gray": (128, 128, 128)}[self.bg.currentText()]
        fg = (0, 0, 0) if sum(bgc) > 380 else (255, 255, 255)

        def task(report, cancelled):
            rows = (len(files) + cols - 1) // cols
            lab_h = 28 if names else 0
            W, H = gap + cols * (cell + gap), gap + rows * (cell + lab_h + gap)
            sheet = Image.new("RGB", (W, H), bgc)
            d = ImageDraw.Draw(sheet)
            for i, f in enumerate(files):
                report(3 + 90 * i / len(files), os.path.basename(f))
                im = load_image(f).convert("RGB")
                im.thumbnail((cell, cell), Image.LANCZOS)
                r, c_ = divmod(i, cols)
                x, y = gap + c_ * (cell + gap), gap + r * (cell + lab_h + gap)
                sheet.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2))
                if names:
                    d.text((x, y + cell + 6), os.path.basename(f)[:40], fill=fg)
            p = save_image(sheet, unique_path(out, "collage", ".jpg"), "JPG", 92)
            return {"message": "Collage saved (%d pictures):\n%s" % (len(files), p), "files": [p]}
        return task


# ---------------------------------------------------------------- bulk rename
class BulkRenameTool(ToolPage):
    key, title, group = "rename", "Bulk Rename (copies)", "Images"
    subtitle = "Give many files tidy new names. Copies are made in the output folder - the originals are not touched."

    def build(self, L):
        self.files = FileListWidget("rename", ("",), "All files (*.*)", "Select files")
        self.files.exts = ("",)           # accept any file
        self.add_row("Files (in order)", self.files)
        self.pattern = QLineEdit("Document_{n}")
        self.start = self.spin(0, 999999, 1)
        self.digits = self.spin(1, 8, 3)
        self.case = self.combo(["Keep as typed", "lower case", "UPPER CASE"])
        L.addWidget(hbox(QLabel("New name"), self.pattern, QLabel("Start at"), self.start, QLabel("Digits"), self.digits, self.case))
        self.add_hint("Tokens: {n} counter, {name} old name, {date} today. The file type (.pdf, .jpg ...) is kept.")
        b = QPushButton("Preview names")
        b.clicked.connect(self.preview)
        L.addWidget(b)
        self.prev = QPlainTextEdit()
        self.prev.setReadOnly(True)
        self.prev.setMaximumHeight(110)
        L.addWidget(self.prev)

    def names(self):
        res, used = [], set()
        for i, f in enumerate(self.files.paths()):
            nm, ext = os.path.splitext(os.path.basename(f))
            new = (self.pattern.text().replace("{n}", str(self.start.value() + i).zfill(self.digits.value()))
                   .replace("{name}", nm).replace("{date}", dt.date.today().isoformat()))
            new = safe_name(new, "file")
            c = self.case.currentIndex()
            new = new.lower() if c == 1 else new.upper() if c == 2 else new
            full = new + ext
            k = 1
            while full.lower() in used:
                k += 1
                full = "%s_%d%s" % (new, k, ext)
            used.add(full.lower())
            res.append((f, full))
        return res

    def preview(self):
        self.prev.setPlainText("\n".join("%s  ->  %s" % (os.path.basename(a), b) for a, b in self.names()))

    def make_task(self, out):
        pairs = self.names()
        if not pairs:
            raise UserError("Add some files first.")

        def task(report, cancelled):
            res = []
            for i, (src, nm) in enumerate(pairs):
                report(5 + 90 * i / len(pairs), nm)
                dst = unique_path(out, os.path.splitext(nm)[0], os.path.splitext(nm)[1])
                shutil.copyfile(src, dst)
                res.append(dst)
            return {"message": "%d renamed copies saved." % len(res), "files": res}
        return task
# ============================================================================
#  SECTION M - PHASE 7: AI CLIENT AND AI FEATURES
#  Text of the pages you choose is sent ONLY to the AI server named in Settings
#  (your office gateway or LM Studio).  Nothing is stored by this program.
# ============================================================================
class AIError(UserError):
    pass


# ---------------------------------------------------------------------------
# >>>>>>>>>>>>>>>>>>>>>>>>>  PROMPTS - EDIT HERE  <<<<<<<<<<<<<<<<<<<<<<<<<<<<
# Plain English instructions given to the AI model.  Change wording freely;
# keep the {placeholders}.  Prompts that ask for JSON must keep saying so.
# ---------------------------------------------------------------------------
PROMPTS = {
    "system": (
        "You are a careful assistant for professionals who work with documents (lawyers, accountants, auditors). "
        "Use ONLY the document text supplied. If something is not in the text, say it is not stated - never guess or invent "
        "names, numbers, dates or clauses. Keep the document's language unless asked to translate. The text may contain OCR "
        "mistakes. Page markers look like [Page 7]."),
    "sum_short": "Summarise the document text below in at most 6 short bullet points (under 120 words in total). Mention page numbers like (p. 3) where useful.\n\n{text}",
    "sum_standard": ("Write a clear summary of the document text below in about 250-350 words. Start with one sentence saying what kind of document "
                     "it is. Then give the key points as short paragraphs or bullets. Mention page numbers like (p. 3).\n\n{text}"),
    "sum_detailed": ("Write a detailed, well-organised summary of the document text below, with a heading for each major part, covering all "
                     "important facts, figures, dates, parties and obligations. Mention page numbers like (p. 3).\n\n{text}"),
    "sum_map": ("Below is ONE PART of a longer document. Write detailed notes on this part only (facts, figures, dates, parties, obligations), "
                "keeping page numbers like (p. 3). Do not conclude about the whole document.\n\n{text}"),
    "sum_reduce": ("Below are notes made from consecutive parts of one document. Combine them into the final {style} summary of the whole "
                   "document. Remove repetition, keep page numbers.\n\nStyle: {style_desc}\n\n{text}"),
    "terms": ("Extract the key terms from the document text below. Reply with ONLY a JSON array. Each item: "
              "{{\"term\": short label such as Parties, Effective date, End date, Contract value, Payment terms, Renewal, Termination notice, "
              "Governing law, Penalty, Interest, Deadline, Obligation, Warranty, Liability cap; \"value\": the exact value in plain words; "
              "\"page\": page number as integer; \"note\": optional short remark}}. Only include terms really present. If none, reply [].\n\n{text}"),
    "ask": ("Answer the question using ONLY the document text below. Be concise and precise. After each fact, cite the page like (p. 4). "
            "If the answer is not in the text, say: \"The supplied pages do not state this.\"\n\nQuestion: {question}\n\n{text}"),
    "clauses": ("Review the contract text below for clauses that are unusual, one-sided or risky for the party who did not draft it: "
                "auto-renewal, unlimited liability, heavy penalties or interest, unilateral termination or change, broad indemnity, "
                "non-compete, exclusivity, far-away jurisdiction, hidden fees, vague payment terms, missing standard protections. "
                "Reply with ONLY a JSON array. Each item: {{\"page\": integer, \"excerpt\": exact short quote (max 200 characters), "
                "\"concern\": why it may be a problem, in one or two sentences, \"severity\": \"High\" or \"Medium\" or \"Low\"}}. "
                "If nothing stands out, reply [].\n\n{text}"),
    "classify": ("Classify the document from its first pages into exactly ONE of these categories:\n{cats}\n\n"
                 "Reply with ONLY JSON: {{\"category\": one of the categories exactly as written, \"confidence\": number 0-100, "
                 "\"reason\": one short sentence}}.\n\n{text}"),
    "translate": ("Translate the text below into {lang}. Keep numbers, names, dates and legal terms accurate. Keep paragraph breaks. "
                  "Output only the translation, nothing else. Keep [Page n] markers unchanged on their own lines.\n\n{text}"),
    "invoice": ("Extract the invoice data from the text below. Reply with ONLY JSON: {{\"vendor\": , \"vendor_gstin\": , \"buyer\": , "
                "\"buyer_gstin\": , \"invoice_no\": , \"invoice_date\": \"DD-MM-YYYY\", \"taxable_value\": number, \"cgst\": number, "
                "\"sgst\": number, \"igst\": number, \"total\": number, \"currency\": , \"items\": [{{\"description\": , \"hsn\": , "
                "\"qty\": number, \"rate\": number, \"amount\": number}}]}}. Use null for anything not present. Numbers without commas.\n\n{text}"),
    "bank": ("Extract the transactions from this bank statement text. Reply with ONLY a JSON array. Each item: "
             "{{\"date\": \"DD-MM-YYYY\", \"description\": , \"ref\": , \"debit\": number or null, \"credit\": number or null, "
             "\"balance\": number or null}}. Keep the original order. Numbers without commas. Skip headers, totals and opening lines.\n\n{text}"),
    "title": ("Give a short title (maximum 8 words, no quotes, no full stop) for this document, such as 'Sale Deed - Plot 14, Pune' or "
              "'Invoice 2231 - ABC Traders'. Output only the title.\n\n{text}"),
    "name": ("Suggest a file name (maximum 60 characters, no extension, no slashes) for this document in the form "
             "'Type - Party - Date', for example 'Invoice - ABC Traders - 2024-03-15'. Leave out parts that are not clear. "
             "Output only the name.\n\n{text}"),
    "redact": ("List the personal or confidential items in the text below that should be considered for redaction: person names, company "
               "names, street addresses, and any other identifying words. Reply with ONLY a JSON array of the exact strings as they appear "
               "in the text (no duplicates).\n\n{text}"),
}
# ----------------------------------------------------------------- end PROMPTS

SUMMARY_STYLES = {"short": ("sum_short", "a very short bullet summary"), "standard": ("sum_standard", "a standard summary of 250-350 words"),
                  "detailed": ("sum_detailed", "a detailed section-by-section summary")}
LANGS = ["English", "Hindi", "Marathi", "Gujarati", "Bengali", "Tamil", "Telugu", "Kannada", "Malayalam", "Punjabi", "Odia", "Urdu"]
CLASS_DEFAULT = ["Invoice", "Contract / Agreement", "Bank statement", "Letter / Notice", "Court order / Legal pleading",
                 "ID / KYC document", "Tax return / GST / Income-tax", "Financial statements / Audit report", "Other"]


def strip_think(s):
    s = re.sub(r"<think>.*?</think>", "", s or "", flags=re.S)
    return re.sub(r"^.*?</think>", "", s, flags=re.S).strip()


def parse_json(txt, want=None):
    txt = strip_think(txt)
    txt = re.sub(r"```(?:json)?", "", txt).strip()
    cands = [txt]
    for a, b in (("[", "]"), ("{", "}")):
        i, j = txt.find(a), txt.rfind(b)
        if 0 <= i < j:
            cands.append(txt[i:j + 1])
    for c in cands:
        try:
            v = json.loads(c)
        except Exception:
            continue
        if want is list and isinstance(v, dict):
            for x in v.values():
                if isinstance(x, list):
                    return x
            return [v]
        if want is dict and isinstance(v, list) and v and isinstance(v[0], dict):
            return v[0]
        if want is None or isinstance(v, want):
            return v
    return None


class AIClient:
    """OpenAI-compatible client.  Gateway mode: job queue with polling.  Direct mode: plain chat/completions."""

    def __init__(self):
        self.key = SET.get("access_key") or ""
        self.role, self.user, self.max_chars, self.daily_left = "general", "", 0, None

    # --- configuration
    @property
    def direct(self):
        return bool(SET.get("direct_mode"))

    def base(self):
        return (SET.get("ai_base_url") or "").strip().rstrip("/")

    def root(self):
        b = self.base()
        return b[:-3] if b.endswith("/v1") else b

    def host_label(self):
        return _host_of(self.base()) or "(not set)"

    def set_key(self, key):
        self.key = (key or "").strip()
        SET.set("access_key", self.key if SET.get("remember_key") else "", save=False)

    def is_prime(self):
        return self.direct or self.role == "prime"

    # --- low level
    def _ctx(self):
        if not self.base().lower().startswith("https"):
            return None
        try:
            return ssl.create_default_context(cafile=(SET.get("ai_ca_file") or None))
        except Exception:
            return ssl.create_default_context()

    def _req(self, method, url, body=None, timeout=30):
        import urllib.request
        import urllib.error
        hdr = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.key:
            hdr["Authorization"] = "Bearer " + self.key
        data = json.dumps(body).encode("utf-8") if body is not None else None
        rq = urllib.request.Request(url, data=data, headers=hdr, method=method)
        try:
            with urllib.request.urlopen(rq, timeout=timeout, context=self._ctx()) as r:
                raw = r.read().decode("utf-8", "replace")
                return r.status, (json.loads(raw) if raw.strip() else {})
        except urllib.error.HTTPError as e:
            try:
                d = json.loads(e.read().decode("utf-8", "replace"))
            except Exception:
                d = {}
            msg = (d.get("error") or {}).get("message") if isinstance(d.get("error"), dict) else d.get("error")
            raise AIError(self._http_msg(e.code, msg))
        except OfflineBlocked:
            raise
        except (urllib.error.URLError, OSError) as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, OfflineBlocked):
                raise reason
            if isinstance(reason, socket.timeout) or isinstance(e, socket.timeout):
                raise AIError("The AI server did not answer in time. It may be busy - try again in a minute.")
            if isinstance(reason, ssl.SSLError):
                raise AIError("A secure connection to the AI server could not be made (certificate problem).\n"
                              "Ask your administrator for the certificate file and set it in Settings > AI > Certificate file.")
            raise AIError("The AI server at %s could not be reached.\nCheck that it is switched on (LM Studio / gateway) and that the "
                          "address in Settings is right." % self.host_label())
        except ValueError:
            raise AIError("The AI server sent an answer this program could not understand.")

    @staticmethod
    def _http_msg(code, msg):
        m = {401: "Your access key / API key was not accepted. Check it in Settings.",
             403: "Your account is not allowed to use this AI feature.",
             413: "This document is too large for your account. Select fewer pages.",
             429: "Your AI usage limit has been reached. Try again later or ask your administrator.",
             503: "The AI engine is not available right now. Ask your administrator to start LM Studio.",
             504: "The request waited too long in the AI queue. Try again."}.get(code)
        return (m + ("\n(%s)" % msg if msg and code not in (401,) else "")) if m else "The AI server returned error %s. %s" % (code, msg or "")

    # --- public
    def refresh_role(self):
        """Ask the gateway who we are.  Returns 'prime' or 'general'."""
        self.role, self.user = "general", ""
        if self.direct:
            self.role = "prime"
            return self.role
        if not self.key:
            return self.role
        st, d = self._req("GET", self.root() + "/pdfstudio/whoami", timeout=10)
        self.role, self.user = d.get("role", "general"), d.get("user", "")
        self.max_chars, self.daily_left = int(d.get("max_chars") or 0), d.get("daily_left")
        return self.role

    def test(self):
        lines = []
        if self.direct:
            st, d = self._req("GET", self.base() + "/models", timeout=10)
            names = [m.get("id", "?") for m in d.get("data", [])][:6]
            lines.append("Connected to the AI server %s - you are a PRIME user (AI tools switched on)." % self.host_label())
            lines.append("Models available: " + (", ".join(names) if names else "none loaded - load one in LM Studio"))
        else:
            st, d = self._req("GET", self.root() + "/health", timeout=10)
            lines.append("Gateway reached (jobs waiting: %s)." % d.get("queue", "?"))
            if self.key:
                role = self.refresh_role()
                lines.append("Signed in as %s - role: %s." % (self.user or "?", role.upper()))
                if self.daily_left is not None:
                    lines.append("AI jobs left today: %s" % self.daily_left)
                if role == "prime":
                    try:
                        st, d = self._req("GET", self.base() + "/models", timeout=10)
                        names = [m.get("id", "?") for m in d.get("data", [])][:5]
                        lines.append("Models: " + (", ".join(names) if names else "none loaded"))
                    except AIError as e:
                        lines.append("AI engine problem: " + str(e).split("\n")[0])
            else:
                lines.append("No access key entered - you are a General user (AI features off).\n"
                             "Paste the key your administrator gave you, or pick 'AI on THIS computer' under AI set-up.")
        return "\n".join(lines)

    def chat(self, messages, cancelled=None, note=None, max_tokens=1500, temperature=0.2, feature="api"):
        if not self.is_prime():
            raise AIError(AI_HOWTO)
        cancelled = cancelled or (lambda: False)
        req = {"messages": messages, "temperature": temperature, "max_tokens": int(max_tokens)}
        if SET.get("ai_model"):
            req["model"] = SET.get("ai_model")
        timeout = max(30, int(SET.get("ai_timeout") or 300))
        t0 = time.time()
        LOG.info("AI call: feature=%s chars=%d", feature, sum(len(m.get("content", "")) for m in messages))
        if self.direct:
            res = self._direct_call(req, timeout, cancelled)
        else:
            st, d = self._req("POST", self.root() + "/pdfstudio/jobs", {"feature": feature, "request": req}, timeout=30)
            jid = d.get("job_id")
            if not jid:
                raise AIError("The gateway did not accept the job.")
            res, last = None, None
            while True:
                if cancelled():
                    try:
                        self._req("DELETE", self.root() + "/pdfstudio/jobs/" + jid, timeout=10)
                    except Exception:
                        pass
                    raise Cancelled()
                if time.time() - t0 > timeout:
                    try:
                        self._req("DELETE", self.root() + "/pdfstudio/jobs/" + jid, timeout=10)
                    except Exception:
                        pass
                    raise AIError("The AI took longer than %d seconds. Try fewer pages, or raise the time limit in Settings." % timeout)
                st, d = self._req("GET", self.root() + "/pdfstudio/jobs/" + jid, timeout=15)
                s = d.get("status")
                if s == "done":
                    res = d.get("result")
                    break
                if s == "error":
                    raise AIError(self._http_msg(int(d.get("code") or 500), d.get("error")))
                if s == "cancelled":
                    raise Cancelled()
                msg = ("Waiting in the AI queue - %d ahead of you..." % d.get("position", 0)) if s == "queued" and d.get("position", 0) else "The AI is working..."
                if note and msg != last:
                    note(msg)
                    last = msg
                time.sleep(1.0)
        try:
            out = strip_think(res["choices"][0]["message"]["content"])
        except Exception:
            raise AIError("The AI returned an empty or unexpected answer.")
        LOG.info("AI done in %.1fs, %d chars", time.time() - t0, len(out))
        return out

    def _direct_call(self, req, timeout, cancelled):
        """Plain OpenAI-compatible call.  Some providers / newer models refuse 'max_tokens' or a custom 'temperature':
        the request is adapted and tried again instead of failing."""
        req = dict(req)
        if not req.get("model") and not is_local_host(_host_of(self.base())):
            raise AIError("Type the model name in Settings > Model (internet AI services need it).")
        for _ in range(3):
            try:
                return self._blocking(self.base() + "/chat/completions", req, timeout, cancelled)
            except AIError as e:
                m = str(e).lower()
                if "max_completion_tokens" in m and "max_tokens" in req:
                    req["max_completion_tokens"] = req.pop("max_tokens")
                    continue
                if "temperature" in m and "temperature" in req:
                    req.pop("temperature")
                    continue
                raise
        raise AIError("The AI service did not accept the request.")

    def _blocking(self, url, req, timeout, cancelled):
        box = {}

        def run():
            try:
                box["r"] = self._req("POST", url, req, timeout=timeout)[1]
            except BaseException as e:
                box["e"] = e
        th = threading.Thread(target=run, daemon=True)
        th.start()
        while th.is_alive():
            th.join(0.3)
            if cancelled():
                raise Cancelled()
        if "e" in box:
            raise box["e"]
        return box["r"]


AI_HOWTO = ("AI is not switched on for you yet (you are a General user).\n\n"
            "Open  Settings  and pick a line under 'AI set-up':\n"
            "  - AI on THIS computer (LM Studio / Ollama): free and private, no key - you become a Prime user at once.\n"
            "  - Office AI server: type the address, paste the access key from your administrator, press 'Test connection'.\n"
            "  - Internet AI service: paste your own API key and model name.\n"
            "Then press 'Save settings'. The AI tools in the left list stop being dimmed.")


def ai_gate(ctx):
    ai = getattr(ctx, "ai", None)
    if not ai or not getattr(ctx, "is_prime", False):
        raise UserError(AI_HOWTO)
    return ai


# --------------------------------------------------------------- text plumbing
def doc_pages_text(path, spec=None, password=None):
    """[(page_number, text)] for chosen pages; refuses scans without a text layer."""
    doc = open_pdf(path, password) if password else open_pdf(path)
    try:
        idx = expand_pages(parse_page_spec(spec, doc.page_count), doc.page_count) if spec else list(range(doc.page_count))
        res = [(i + 1, doc[i].get_text("text")) for i in idx]
    finally:
        doc.close()
    if sum(len(t.strip()) for _, t in res) < 40:
        raise UserError("This document has almost no readable text (it looks like a scan).\nRun 'OCR (Searchable PDF)' first, then try again.")
    return res


def chunk_limit(ai, max_tokens, extra=1200):
    ctx_tokens = int(SET.get("ai_max_context") or 8192)
    chars = int((ctx_tokens - max_tokens - 600) * 3.0) - extra
    chars = max(2500, chars)
    if ai and ai.max_chars and not ai.direct:
        chars = min(chars, max(2500, ai.max_chars - extra - 500))
    return chars


def chunk_pages(pages, limit):
    """Split [(n, text)] into [(text, [page numbers])], each at most `limit` characters."""
    chunks, cur, cur_p, size = [], [], [], 0

    def flush():
        nonlocal cur, cur_p, size
        if cur:
            chunks.append(("\n\n".join(cur), cur_p))
        cur, cur_p, size = [], [], 0
    for n, t in pages:
        t = t.strip()
        if not t:
            continue
        pieces = [t]
        if len(t) + 12 > limit:
            pieces, buf = [], ""
            for para in re.split(r"\n\s*\n|(?<=[.!?।])\s+", t):
                if len(buf) + len(para) + 1 > limit - 20 and buf:
                    pieces.append(buf)
                    buf = ""
                buf += (" " if buf else "") + para[:limit - 20]
            if buf:
                pieces.append(buf)
        for piece in pieces:
            blk = "[Page %d]\n%s" % (n, piece)
            if size + len(blk) > limit:
                flush()
            cur.append(blk)
            if n not in cur_p:
                cur_p.append(n)
            size += len(blk) + 2
    flush()
    return chunks


def msgs(user_prompt):
    return [{"role": "system", "content": PROMPTS["system"]}, {"role": "user", "content": user_prompt}]


def ai_for_chunks(ai, pages, prompt_key, report, cancelled, max_tokens=1500, as_json=False, feature="api", **fmt):
    """Run one prompt over each chunk.  Returns list of (pages, answer-or-parsed)."""
    chunks = chunk_pages(pages, chunk_limit(ai, max_tokens, 1500))
    if not chunks:
        raise UserError("No text found in the selected pages.")
    res = []
    for k, (txt, pp) in enumerate(chunks):
        pct = 5 + 85 * k / len(chunks)
        label = "Part %d of %d (pages %s-%s)" % (k + 1, len(chunks), pp[0], pp[-1]) if len(chunks) > 1 else "Reading the document"
        report(pct, label)
        prompt = PROMPTS[prompt_key].format(text=txt, **fmt)
        ans = ai.chat(msgs(prompt), cancelled, lambda m, p=pct: report(p, m), max_tokens, feature=feature)
        if as_json:
            v = parse_json(ans, list if prompt_key in ("terms", "clauses", "bank", "redact") else dict)
            if v is None:
                ans = ai.chat(msgs(prompt) + [{"role": "assistant", "content": ans[:600]},
                              {"role": "user", "content": "That was not valid JSON. Reply again with ONLY the JSON."}],
                              cancelled, None, max_tokens, feature=feature)
                v = parse_json(ans, list if prompt_key in ("terms", "clauses", "bank", "redact") else dict)
            res.append((pp, v))
        else:
            res.append((pp, ans))
    return res


def ai_summarise(ai, pages, style, report, cancelled):
    key, desc = SUMMARY_STYLES[style]
    mt = {"short": 400, "standard": 900, "detailed": 2200}[style]
    chunks = chunk_pages(pages, chunk_limit(ai, mt, 1500))
    if len(chunks) <= 1:
        return ai_for_chunks(ai, pages, key, report, cancelled, mt, feature="summary")[0][1]
    notes = ai_for_chunks(ai, pages, "sum_map", report, cancelled, 1200, feature="summary")
    joined = "\n\n".join("--- Part %d ---\n%s" % (i + 1, a) for i, (_, a) in enumerate(notes))
    lim = chunk_limit(ai, mt, 1500)
    while len(joined) > lim:           # notes themselves too long: condense in groups
        report(92, "Condensing notes...")
        grp = chunk_pages([(i + 1, a) for i, (_, a) in enumerate(notes)], lim)
        notes = [(p, ai.chat(msgs(PROMPTS["sum_map"].format(text=t)), cancelled, None, 1200, feature="summary")) for t, p in grp]
        joined = "\n\n".join("--- Part %d ---\n%s" % (i + 1, a) for i, (_, a) in enumerate(notes))
    report(95, "Writing the final summary...")
    return ai.chat(msgs(PROMPTS["sum_reduce"].format(text=joined, style=style, style_desc=desc)), cancelled, None, mt, feature="summary")


# --------- helpers used by other tools (title / file name / redaction ideas)
def ai_suggest_title(ai, text, cancelled=None):
    t = ai.chat(msgs(PROMPTS["title"].format(text=text[:3500])), cancelled, None, 40, feature="title")
    return t.strip().strip("\"'").splitlines()[0][:80] if t.strip() else ""


def ai_suggest_name(ai, text, cancelled=None):
    t = ai.chat(msgs(PROMPTS["name"].format(text=text[:3500])), cancelled, None, 60, feature="rename")
    return re.sub(r"[\\/:*?\"<>|]", "-", t.strip().splitlines()[0])[:60] if t.strip() else ""


def ai_suggest_redactions(ai, pages, report, cancelled):
    out, seen = [], set()
    for pp, v in ai_for_chunks(ai, pages, "redact", report, cancelled, 700, True, "redaction"):
        for s in (v or []):
            if isinstance(s, str):
                s = s.strip()
                if 3 <= len(s) <= 80 and s.lower() not in seen:
                    seen.add(s.lower())
                    out.append(s)
    return out


# --------------------------------------------------------------- output helpers
def write_text_report(out, base, title, body, fmt="docx"):
    """Save an AI answer.  Always carries the disclaimer."""
    if fmt == "docx" and HAVE_DOCX:
        d = pydocx.Document()
        d.add_heading(title, 1)
        p = d.add_paragraph()
        r = p.add_run(DISCLAIMER)
        r.italic = True
        for para in body.split("\n"):
            if para.startswith("### "):
                d.add_heading(para[4:], 3)
            elif para.startswith("## "):
                d.add_heading(para[3:], 2)
            elif para.startswith("# "):
                d.add_heading(para[2:], 2)
            elif re.match(r"^\s*[-*•]\s+", para):
                d.add_paragraph(re.sub(r"^\s*[-*•]\s+", "", para).replace("**", ""), style="List Bullet")
            elif para.strip():
                d.add_paragraph(para.replace("**", ""))
        d.add_paragraph().add_run(DISCLAIMER).italic = True
        path = unique_path(out, base, ".docx")
        d.save(path)
        return path
    path = unique_path(out, base, ".txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("%s\n%s\n\n[%s]\n\n%s\n\n[%s]\n" % (title, "=" * len(title), DISCLAIMER, body, DISCLAIMER))
    return path


def write_table_files(out, base, title, headers, rows, want_x=True, want_d=True, widths=None):
    files = []
    if want_x:
        need_lib(HAVE_XLSX, "openpyxl", "Excel export")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Result"[:31]
        ws.append(headers)
        for c in ws[1]:
            c.font = openpyxl.styles.Font(bold=True)
        for r in rows:
            ws.append(list(r))
        for i, h in enumerate(headers):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i + 1)].width = (widths[i] if widths else 22)
        ws.freeze_panes = "A2"
        rd = wb.create_sheet("Read me")
        rd.append([title])
        rd.append([DISCLAIMER])
        rd.column_dimensions["A"].width = 90
        p = unique_path(out, base, ".xlsx")
        wb.save(p)
        files.append(p)
    if want_d:
        need_lib(HAVE_DOCX, "python-docx", "Word export")
        d = pydocx.Document()
        d.add_heading(title, 1)
        d.add_paragraph().add_run(DISCLAIMER).italic = True
        t = d.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        for i, h in enumerate(headers):
            t.rows[0].cells[i].text = h
        for r in rows:
            cells = t.add_row().cells
            for i, v in enumerate(r):
                cells[i].text = "" if v is None else str(v)
        p = unique_path(out, base, ".docx")
        d.save(p)
        files.append(p)
    return files


def to_num(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return v
    s = re.sub(r"[^\d.\-]", "", str(v).replace(",", ""))
    try:
        return float(s) if s not in ("", "-", ".") else None
    except ValueError:
        return None


# --------------------------------------------------------------- AI tool pages
class AiTool(ToolPage):
    group = "AI"
    prime_only = True
    privacy = True

    def build(self, L):
        self.pdf = PdfPicker(self.key, allow_password=True)
        self.add_row("PDF document", self.pdf)
        self.pw = PasswordField("Password (only if the file is protected)")
        self.add_row("", self.pw)
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("All pages  (or e.g. 1-10, 15)")
        self.add_row("Pages to use", self.pages)
        self.build_options(L)
        ai = getattr(self.ctx, "ai", None)
        host = ai.host_label() if ai else "-"
        if ai and not is_local_host(_host_of(ai.base())):
            self.add_hint("PRIVACY WARNING: the text of the selected pages is sent over the INTERNET to %s. Do not use it for confidential "
                          "client papers unless your firm allows it. %s" % (host, DISCLAIMER))
        else:
            self.add_hint("Privacy: the text of the selected pages is sent only to your own AI server (%s). Nothing goes to the internet. %s"
                          % (host, DISCLAIMER))

    def build_options(self, L):
        pass

    def on_show(self):
        if not getattr(self.ctx, "is_prime", False):
            self.status.setText("AI is not switched on yet - open Settings and choose an 'AI set-up' (it takes two minutes).")

    def source(self):
        ai = ai_gate(self.ctx)
        p = self.pdf.require()
        return ai, p, (self.pages.text().strip() or None), (self.pw.text() or None)

    def out_fmt(self):
        return "docx" if HAVE_DOCX else "txt"


class AiSummaryTool(AiTool):
    key, title = "ai_summary", "Summarise Document"
    subtitle = "A short, standard or detailed summary of a long PDF, with page references."

    def build_options(self, L):
        self.style = self.combo([("Short (6 bullets)", "short"), ("Standard (about 300 words)", "standard"), ("Detailed (section by section)", "detailed")], "Standard (about 300 words)")
        self.add_row("Length", self.style)

    def make_task(self, out):
        ai, p, spec, pw = self.source()
        style = self.style.currentData()
        fmt = self.out_fmt()

        def task(report, cancelled):
            pages = doc_pages_text(p, spec, pw)
            ans = ai_summarise(ai, pages, style, report, cancelled)
            path = write_text_report(out, safe_name(os.path.splitext(os.path.basename(p))[0]) + "_summary", "Summary - " + os.path.basename(p), ans, fmt)
            return {"message": "Summary saved:\n%s\n\n%s\n\n%s" % (path, ans[:700] + ("..." if len(ans) > 700 else ""), DISCLAIMER), "files": [path]}
        return task


class AiTermsTool(AiTool):
    key, title = "ai_terms", "Key Terms Table"
    subtitle = "Pull parties, dates, amounts, payment terms and deadlines out of a contract into a table."

    def build_options(self, L):
        self.fx = QCheckBox("Excel"); self.fx.setChecked(True)
        self.fd = QCheckBox("Word"); self.fd.setChecked(True)
        L.addWidget(hbox(QLabel("Save as"), self.fx, self.fd, None))

    def make_task(self, out):
        ai, p, spec, pw = self.source()
        wx, wd = self.fx.isChecked(), self.fd.isChecked()
        if not (wx or wd):
            raise UserError("Tick Excel and/or Word.")

        def task(report, cancelled):
            pages = doc_pages_text(p, spec, pw)
            res = ai_for_chunks(ai, pages, "terms", report, cancelled, 1500, True, "terms")
            rows, seen, bad = [], set(), 0
            for pp, v in res:
                if v is None:
                    bad += 1
                    continue
                for it in v:
                    if not isinstance(it, dict):
                        continue
                    k = (str(it.get("term", "")).lower(), str(it.get("value", "")).lower())
                    if k in seen or not k[1]:
                        continue
                    seen.add(k)
                    rows.append([it.get("term", ""), it.get("value", ""), it.get("page", ""), it.get("note", "") or ""])
            if not rows:
                raise UserError("The AI found no key terms%s." % (" (some parts of the answer could not be read)" if bad else ""))
            files = write_table_files(out, safe_name(os.path.splitext(os.path.basename(p))[0]) + "_key_terms", "Key terms - " + os.path.basename(p),
                                      ["Term", "Value", "Page", "Note"], rows, wx, wd, [26, 60, 8, 40])
            return {"message": "%d terms found.%s\n\n%s" % (len(rows), ("\n%d part(s) could not be read." % bad) if bad else "", DISCLAIMER), "files": files}
        return task


class AiAskTool(AiTool):
    key, title = "ai_ask", "Ask Questions About a Document"
    subtitle = "Type a question; the answer comes with the page numbers it was found on."

    def build_options(self, L):
        self.q = QLineEdit()
        self.q.setPlaceholderText("e.g. What is the notice period for termination?")
        self.add_row("Your question", self.q)
        self.answer = QTextEdit()
        self.answer.setReadOnly(True)
        self.answer.setMinimumHeight(160)
        self.add_row("Answer", self.answer)

    @staticmethod
    def pick_pages(pages, question, limit):
        stop = set("the a an of to and or in on for is are was were be by with what which who whom when where why how does do did this that it as at from about under any".split())
        words = [w for w in re.findall(r"\w{3,}", question.lower()) if w not in stop]
        scored = []
        for n, t in pages:
            low = t.lower()
            sc = sum(min(low.count(w), 5) * (1 + len(w) / 10.0) for w in words)
            scored.append((sc, n, t))
        if not any(s[0] for s in scored):
            return sorted(pages)[:max(1, limit // 2500)], False
        chosen, size = [], 0
        for sc, n, t in sorted(scored, key=lambda x: -x[0]):
            if sc <= 0:
                break
            if size + len(t) > limit and chosen:
                continue
            chosen.append((n, t[:limit]))
            size += len(t)
        return sorted(chosen), True

    def make_task(self, out):
        ai, p, spec, pw = self.source()
        q = self.q.text().strip()
        if not q:
            raise UserError("Type your question first.")

        def task(report, cancelled):
            pages = doc_pages_text(p, spec, pw)
            lim = chunk_limit(ai, 900, 1200)
            sel, matched = self.pick_pages(pages, q, lim)
            txt = "\n\n".join("[Page %d]\n%s" % (n, t.strip()) for n, t in sel)[:lim]
            report(20, "Asking...")
            ans = ai.chat(msgs(PROMPTS["ask"].format(question=q, text=txt)), cancelled, lambda m: report(30, m), 900, feature="ask")
            used = ", ".join(str(n) for n, _ in sel)
            note = "Pages searched: %s%s" % (used, "" if matched else "  (no page matched your words; the first pages were used)")
            full = "Question: %s\n\n%s\n\n%s\n%s" % (q, ans, note, DISCLAIMER)
            path = write_text_report(out, safe_name(os.path.splitext(os.path.basename(p))[0]) + "_answer", "Answer - " + os.path.basename(p), "Question: %s\n\n%s\n\n%s" % (q, ans, note), "txt")
            return {"message": "Answer saved:\n%s" % path, "files": [path], "answer": full, "silent": True}
        return task

    def on_success(self, res):
        self.answer.setPlainText(res.get("answer", ""))
        self.status.setText("Answer ready (also saved in the output folder).")


class AiClausesTool(AiTool):
    key, title = "ai_clauses", "Flag Unusual Clauses"
    subtitle = "Highlights clauses that may be one-sided or risky. A first screen - not legal advice."

    def build_options(self, L):
        self.fx = QCheckBox("Excel"); self.fx.setChecked(True)
        self.fd = QCheckBox("Word"); self.fd.setChecked(True)
        L.addWidget(hbox(QLabel("Save as"), self.fx, self.fd, None))

    def make_task(self, out):
        ai, p, spec, pw = self.source()
        wx, wd = self.fx.isChecked(), self.fd.isChecked()
        if not (wx or wd):
            raise UserError("Tick Excel and/or Word.")

        def task(report, cancelled):
            pages = doc_pages_text(p, spec, pw)
            res = ai_for_chunks(ai, pages, "clauses", report, cancelled, 1800, True, "clauses")
            rank = {"high": 0, "medium": 1, "low": 2}
            rows, bad = [], 0
            for pp, v in res:
                if v is None:
                    bad += 1
                    continue
                for it in v:
                    if isinstance(it, dict) and it.get("concern"):
                        rows.append([str(it.get("severity", "Medium")).title(), it.get("page", ""), str(it.get("excerpt", ""))[:300], it.get("concern", "")])
            rows.sort(key=lambda r: (rank.get(r[0].lower(), 1), str(r[1])))
            if not rows:
                return {"message": "The AI did not flag anything.%s\nThis does not mean the document is safe - read it yourself.\n\n%s" % (("\n%d part(s) could not be read." % bad) if bad else "", DISCLAIMER), "files": []}
            files = write_table_files(out, safe_name(os.path.splitext(os.path.basename(p))[0]) + "_flagged_clauses", "Flagged clauses - " + os.path.basename(p),
                                      ["Severity", "Page", "Excerpt", "Why it may matter"], rows, wx, wd, [10, 8, 60, 70])
            return {"message": "%d clause(s) flagged.\nPlease read each one in the original - the AI can be wrong.\n\n%s" % (len(rows), DISCLAIMER), "files": files}
        return task


class AiClassifyTool(ToolPage):
    key, title, group = "ai_classify", "Classify Documents", "AI"
    subtitle = "Sort many PDFs into types (invoice, contract, bank statement ...) and get an Excel list."
    prime_only = True

    def build(self, L):
        self.files = FileListWidget("ai_classify")
        self.add_row("PDF files", self.files)
        self.cats = QPlainTextEdit("\n".join(CLASS_DEFAULT))
        self.cats.setMaximumHeight(120)
        self.add_row("Categories (one per line)", self.cats)
        self.copy = QCheckBox("Also copy each file into a sub-folder named after its category")
        L.addWidget(self.copy)
        self.add_hint("Only the first 2 pages of each file are read. Scanned files without text are marked 'No text - run OCR'. " + DISCLAIMER)

    def make_task(self, out):
        ai = ai_gate(self.ctx)
        files = self.files.paths()
        cats = [c.strip() for c in self.cats.toPlainText().splitlines() if c.strip()]
        if not files:
            raise UserError("Add some PDF files.")
        if len(cats) < 2:
            raise UserError("Give at least two categories.")
        copy = self.copy.isChecked()

        def task(report, cancelled):
            rows = []
            for k, f in enumerate(files):
                report(3 + 92 * k / len(files), os.path.basename(f))
                try:
                    d = open_pdf(f)
                    txt = "".join(d[i].get_text("text") for i in range(min(2, d.page_count)))[:3500]
                    d.close()
                except UserError as e:
                    rows.append([os.path.basename(f), "Unreadable", "", str(e).split("\n")[0]])
                    continue
                if len(txt.strip()) < 30:
                    rows.append([os.path.basename(f), "No text - run OCR", "", ""])
                    continue
                ans = ai.chat(msgs(PROMPTS["classify"].format(cats="\n".join("- " + c for c in cats), text=txt)), cancelled, None, 200, feature="classify")
                v = parse_json(ans, dict) or {}
                cat = str(v.get("category", "")).strip()
                match = next((c for c in cats if c.lower() == cat.lower()), None)
                rows.append([os.path.basename(f), match or "Unclear", v.get("confidence", ""), v.get("reason", "")])
                if copy and match:
                    sub = ensure_out_dir(os.path.join(out, safe_name(match)))
                    shutil.copyfile(f, unique_path(sub, os.path.splitext(os.path.basename(f))[0], os.path.splitext(f)[1]))
            xs = write_table_files(out, "classification", "Document classification", ["File", "Category", "Confidence %", "Reason"], rows, True, False, [40, 30, 12, 70])
            return {"message": "%d file(s) classified.\n\n%s" % (len(rows), DISCLAIMER), "files": xs}
        return task


class AiTranslateTool(AiTool):
    key, title = "ai_translate", "Translate Document Text"
    subtitle = "Translate the text of a PDF into another language (text only - the page layout is not kept)."

    def build_options(self, L):
        self.lang = self.combo(LANGS, "Hindi")
        self.add_row("Translate into", self.lang)
        self.add_hint("Always have important translations checked by a qualified translator.")

    def make_task(self, out):
        ai, p, spec, pw = self.source()
        lang, fmt = self.lang.currentText(), self.out_fmt()

        def task(report, cancelled):
            pages = doc_pages_text(p, spec, pw)
            res = ai_for_chunks(ai, pages, "translate", report, cancelled, int(max(800, chunk_limit(ai, 1500, 1500) / 2.2)), False, "translate", lang=lang)
            body = "\n\n".join(a for _, a in res)
            path = write_text_report(out, safe_name(os.path.splitext(os.path.basename(p))[0]) + "_" + lang, "Translation (%s) - %s" % (lang, os.path.basename(p)), body, fmt)
            return {"message": "Translation saved:\n%s\n\n%s" % (path, DISCLAIMER), "files": [path]}
        return task


class AiExtractTool(AiTool):
    key, title = "ai_extract", "Invoices & Bank Statements to Excel"
    subtitle = "Read invoices or a bank statement and put the figures into an Excel sheet, with arithmetic checks."

    def build_options(self, L):
        self.kind = self.combo([("Bank statement (transactions)", "bank"), ("Invoice(s) - one PDF per invoice", "invoice")])
        self.add_row("Document type", self.kind)
        self.more = FileListWidget("ai_extract_more")
        self.add_row("More invoice PDFs (optional, for invoices)", self.more)
        self.add_hint("Every extracted figure must be checked against the original. Rows that fail an arithmetic check are marked in the 'Check' column.")

    def make_task(self, out):
        ai, p, spec, pw = self.source()
        kind = self.kind.currentData()
        extra = self.more.paths()

        def task(report, cancelled):
            if kind == "bank":
                pages = doc_pages_text(p, spec, pw)
                res = ai_for_chunks(ai, pages, "bank", report, cancelled, 3000, True, "extract")
                rows, bad, prev = [], 0, None
                for pp, v in res:
                    if v is None:
                        bad += 1
                        continue
                    for it in v:
                        if not isinstance(it, dict):
                            continue
                        dr, cr, bal = to_num(it.get("debit")), to_num(it.get("credit")), to_num(it.get("balance"))
                        chk = ""
                        if prev is not None and bal is not None and (dr or cr):
                            exp = round(prev - (dr or 0) + (cr or 0), 2)
                            if abs(exp - bal) > 0.02:
                                chk = "Balance mismatch (expected %.2f)" % exp
                        if bal is not None:
                            prev = bal
                        rows.append([it.get("date", ""), it.get("description", ""), it.get("ref", ""), dr, cr, bal, "p.%s" % pp[0], chk])
                if not rows:
                    raise UserError("No transactions were found.%s" % (" Some AI answers could not be read." if bad else ""))
                fl = write_table_files(out, safe_name(os.path.splitext(os.path.basename(p))[0]) + "_transactions", "Bank statement extract - " + os.path.basename(p),
                                       ["Date", "Description", "Reference", "Debit", "Credit", "Balance", "Page", "Check"], rows, True, False, [12, 50, 18, 14, 14, 14, 8, 34])
                nb = sum(1 for r in rows if r[7])
                return {"message": "%d transactions extracted. %d row(s) fail the running-balance check%s.\n\n%s" % (len(rows), nb, " (some parts unreadable: %d)" % bad if bad else "", DISCLAIMER), "files": fl}
            files = [p] + [f for f in extra if f != p]
            rows = []
            for k, f in enumerate(files):
                report(5 + 85 * k / len(files), os.path.basename(f))
                pages = doc_pages_text(f, spec if f == p else None, pw if f == p else None)
                txt = "\n\n".join("[Page %d]\n%s" % (n, t) for n, t in pages)[:chunk_limit(ai, 1500, 1200)]
                ans = ai.chat(msgs(PROMPTS["invoice"].format(text=txt)), cancelled, None, 1500, feature="extract")
                v = parse_json(ans, dict)
                if not v:
                    rows.append([os.path.basename(f)] + [""] * 11 + ["AI answer unreadable"])
                    continue
                tx, cg, sg, ig, tot = (to_num(v.get(x)) for x in ("taxable_value", "cgst", "sgst", "igst", "total"))
                chk = ""
                if None not in (tx, tot):
                    exp = round(tx + (cg or 0) + (sg or 0) + (ig or 0), 2)
                    if abs(exp - tot) > 1.0:
                        chk = "Total mismatch (taxable+tax = %.2f)" % exp
                items = v.get("items") or []
                if items and tx is not None:
                    s = sum(to_num(i.get("amount")) or 0 for i in items if isinstance(i, dict))
                    if s and abs(s - tx) > 1.0:
                        chk = (chk + "; " if chk else "") + "Items sum %.2f differs from taxable value" % s
                rows.append([os.path.basename(f), v.get("vendor"), v.get("vendor_gstin"), v.get("buyer"), v.get("buyer_gstin"), v.get("invoice_no"),
                             v.get("invoice_date"), tx, cg, sg, ig, tot, chk])
            fl = write_table_files(out, "invoices_extract", "Invoice extract", ["File", "Vendor", "Vendor GSTIN", "Buyer", "Buyer GSTIN", "Invoice no.", "Date", "Taxable value",
                                   "CGST", "SGST", "IGST", "Total", "Check"], rows, True, False, [26, 28, 18, 28, 18, 16, 12, 14, 12, 12, 12, 14, 40])
            return {"message": "%d invoice(s) extracted.\nCheck every figure against the original.\n\n%s" % (len(rows), DISCLAIMER), "files": fl}
        return task
# ============================================================================
#  SECTION N - PHASE 8: SETTINGS, GATEWAY ADMIN, DEPLOYMENT, UPDATES, ABOUT
# ============================================================================
def ver_tuple(v):
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", str(v)))


def check_update(folder=None):
    """Look for version.json in the shared update folder.  Returns (state, info) - state: none/new/current/error."""
    folder = folder or SET.get("update_path")
    if not folder:
        return "none", "No update folder is set (Settings > Updates)."
    f = os.path.join(folder, "version.json")
    try:
        with open(f, "r", encoding="utf-8") as fh:
            d = json.load(fh)
    except OSError:
        return "error", "The update folder could not be reached:\n%s" % folder
    except ValueError:
        return "error", "version.json in the update folder is not valid."
    nv = str(d.get("version", "0"))
    if ver_tuple(nv) > ver_tuple(APP_VERSION):
        return "new", "Version %s is available (you have %s).\n%s\n\nFile: %s" % (nv, APP_VERSION, d.get("notes", ""), os.path.join(folder, d.get("file", "")))
    return "current", "You have the newest version (%s)." % APP_VERSION


class SettingsTool(ToolPage):
    key, title, group = "settings", "Settings", "System"
    subtitle = "Offline mode, AI connection, access key, appearance and updates."
    needs_output = False
    no_action = True

    def build(self, L):
        def lock(w, key):
            if SET.locked(key):
                w.setEnabled(False)
                w.setToolTip("Set by your administrator.")
            return w
        self.offline = lock(QCheckBox("Strict Offline Mode  (recommended - only the servers below can be contacted)"), "offline_mode")
        self.offline.setChecked(bool(SET.get("offline_mode")))
        L.addWidget(self.offline)
        self.hosts = lock(QPlainTextEdit("\n".join(SET.get("allowed_hosts") or [])), "allowed_hosts")
        self.hosts.setMaximumHeight(70)
        self.add_row("Other allowed servers", self.hosts, "One per line, e.g. a time-stamp server. The AI server is allowed automatically.")
        L.addWidget(self._hr())
        self.setup = self.combo([(a[0], i) for i, a in enumerate(AI_SETUPS)])
        self.setup.setEnabled(not (SET.locked("ai_base_url") or SET.locked("direct_mode")))
        self.setup.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.setup.setMinimumContentsLength(30)
        self.add_row("AI set-up", self.setup, "Pick how you want to use the AI tools. General user = AI off. Prime user = AI switched on.")
        self.setup.activated.connect(self.pick_setup)
        self.url = lock(QLineEdit(SET.get("ai_base_url")), "ai_base_url")
        self.add_row("AI server address", self.url, "Your office gateway, e.g. http://192.168.1.10:8800/v1  - or LM Studio, e.g. http://localhost:1234/v1")
        self.direct = lock(QCheckBox("Direct mode: talk to the AI server without an office gateway"), "direct_mode")
        self.direct.setChecked(bool(SET.get("direct_mode")))
        L.addWidget(self.direct)
        self.model = lock(QLineEdit(SET.get("ai_model")), "ai_model")
        self.model.setPlaceholderText("(leave empty to use whatever model the server has loaded)")
        self.timeout = lock(self.spin(30, 3600, int(SET.get("ai_timeout")), " s"), "ai_timeout")
        self.maxctx = lock(self.spin(1024, 262144, int(SET.get("ai_max_context")), " tokens", 1024), "ai_max_context")
        self.ca = lock(QLineEdit(SET.get("ai_ca_file")), "ai_ca_file")
        self.ca.setPlaceholderText("Certificate file (.pem) - only for an HTTPS gateway with its own certificate")
        L.addWidget(hbox(QLabel("Model"), self.model, QLabel("Time limit"), self.timeout, QLabel("Model context size"), self.maxctx))
        L.addWidget(self.ca)
        self.key = PasswordField("Access key from your administrator, or your own API key")
        self.key.setText(self.ctx.ai.key if getattr(self.ctx, "ai", None) else "")
        self.add_row("Access key / API key  (not needed for AI on this computer)", self.key)
        self.remember = lock(QCheckBox("Remember the key on this computer (tick only on your own PC)"), "remember_key")
        self.remember.setChecked(bool(SET.get("remember_key")))
        L.addWidget(self.remember)
        self.role_lbl = QLabel("")
        self.role_lbl.setObjectName("status")
        tb = QPushButton("Test connection")
        tb.clicked.connect(self.test_conn)
        L.addWidget(hbox(tb, self.role_lbl, None))
        L.addWidget(self._hr())
        self.tess = lock(FilePicker("tess", (".exe", ""), "Select tesseract.exe", "Programs (*.exe);;All files (*.*)"), "tesseract_path")
        self.tess.set_path(SET.get("tesseract_path"))
        self.add_row("Tesseract OCR program (leave empty to find it automatically)", self.tess)
        self.theme = lock(self.combo([("Light", "light"), ("Dark", "dark")], "Dark" if SET.get("theme") == "dark" else "Light"), "theme")
        self.recent = lock(QCheckBox("Remember recently opened files"), "recent_enabled")
        self.recent.setChecked(bool(SET.get("recent_enabled")))
        L.addWidget(hbox(QLabel("Appearance"), self.theme, self.recent, None))
        self.upd = lock(QLineEdit(SET.get("update_path")), "update_path")
        self.upd.setPlaceholderText(r"Shared update folder, e.g. \\server\software\PDFStudioPro")
        self.add_row("Update folder (the office puts version.json and the new installer here)", self.upd)
        ub = QPushButton("Check for updates now")
        ub.clicked.connect(lambda: self.ctx.check_updates(True))
        sb = QPushButton("Save settings")
        sb.setObjectName("primary")
        sb.setMinimumHeight(40)
        sb.clicked.connect(self.save)
        L.addWidget(hbox(sb, ub, None))
        if SET.admin_path:
            self.add_hint("Some settings are fixed by your administrator (%s)." % SET.admin_path)
        self.out = QTextEdit()
        self.out.setReadOnly(True)
        self.out.setMaximumHeight(110)
        L.addWidget(self.out)

    @staticmethod
    def _hr():
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setFrameShadow(QFrame.Sunken)
        return f

    def pick_setup(self, i):
        name, url, direct, steps = AI_SETUPS[self.setup.itemData(i) or 0]
        if url is None:
            return
        if url:
            self.url.setText(url)
        self.direct.setChecked(bool(direct))
        self.out.setPlainText(name + "\n\n" + steps)

    def cloud_ok(self):
        """Ask once before text may be sent to an internet AI service."""
        host = _host_of(self.url.text().strip())
        if is_local_host(host) or SET.get("cloud_ai_ok") == host:
            return True
        a = QMessageBox.question(self, "Internet AI service",
                                 "The AI server '%s' is on the INTERNET.\n\nWhen you use an AI tool, the text of the pages you select "
                                 "will be sent to that company. Client documents may be confidential.\n\nUse this server?" % host,
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if a != QMessageBox.Yes:
            return False
        SET.set("cloud_ai_ok", host, save=False)
        return True

    def apply_to_settings(self):
        pairs = [("offline_mode", self.offline.isChecked()), ("allowed_hosts", [h.strip() for h in self.hosts.toPlainText().splitlines() if h.strip()]),
                 ("ai_base_url", self.url.text().strip()), ("direct_mode", self.direct.isChecked()), ("ai_model", self.model.text().strip()),
                 ("ai_timeout", self.timeout.value()), ("ai_max_context", self.maxctx.value()), ("ai_ca_file", self.ca.text().strip()),
                 ("remember_key", self.remember.isChecked()), ("tesseract_path", self.tess.path()), ("theme", self.theme.currentData()),
                 ("recent_enabled", self.recent.isChecked()), ("update_path", self.upd.text().strip())]
        for k, v in pairs:
            SET.set(k, v, save=False)
        if not SET.get("recent_enabled"):
            SET.set("recent", [], save=False)
        self.ctx.ai.set_key(self.key.text())
        if SET.get("remember_key"):
            SET.user["access_key"] = self.ctx.ai.key
        SET.save()
        _ALLOW_EXTRA.clear()
        _RESOLVED.clear()

    def save(self):
        if not self.cloud_ok():
            return
        self.apply_to_settings()
        self.ctx.settings_changed()
        self.out.setPlainText("Saved.")

    def test_conn(self):
        if not self.cloud_ok():
            return
        self.apply_to_settings()
        ai = self.ctx.ai

        def task(report, cancelled):
            report(30, "Contacting the AI server...")
            msg = ai.test()
            return {"msg": msg, "role": ai.role if not ai.direct else "prime"}

        def done(res):
            self.out.setPlainText(res["msg"])
            self.ctx.settings_changed()

        def fail(msg):
            self.out.setPlainText(msg)
        w = Worker(task, self)
        w.succeeded.connect(done)
        w.failed.connect(lambda m, u: fail(m))
        self._w = w
        w.start()
        self.out.setPlainText("Testing...")


# ---------------------------------------------------------------- in-app gateway administration
class UserDialog(QDialog):
    def __init__(self, parent, store, user=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle("Edit user" if user else "Add user")
        f = QFormLayout(self)
        u = user or {}
        self.name = QLineEdit(u.get("name", ""))
        self.role = QComboBox()
        self.role.addItems(["prime", "general"])
        self.role.setCurrentText(u.get("role", "prime"))
        self.daily = QSpinBox(); self.daily.setRange(0, 100000); self.daily.setValue(int(u.get("daily_limit", store.cfg["default_daily_limit"])))
        self.monthly = QSpinBox(); self.monthly.setRange(0, 1000000); self.monthly.setValue(int(u.get("monthly_limit", store.cfg["default_monthly_limit"])))
        self.maxc = QSpinBox(); self.maxc.setRange(0, 5000000); self.maxc.setValue(int(u.get("max_chars", 0)))
        self.prio = QSpinBox(); self.prio.setRange(1, 9); self.prio.setValue(int(u.get("priority", 5)))
        self.exp = QLineEdit(u.get("expires", ""))
        self.exp.setPlaceholderText("YYYY-MM-DD or empty")
        self.enabled = QCheckBox("Account enabled")
        self.enabled.setChecked(u.get("enabled", True))
        f.addRow("Name", self.name)
        f.addRow("Role", self.role)
        f.addRow("AI jobs per day (0 = no limit)", self.daily)
        f.addRow("AI jobs per month (0 = no limit)", self.monthly)
        f.addRow("Max characters per job (0 = default)", self.maxc)
        f.addRow("Queue priority (1 = first, 9 = last)", self.prio)
        f.addRow("Expires on", self.exp)
        f.addRow("", self.enabled)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def values(self):
        return dict(name=self.name.text().strip(), role=self.role.currentText(), daily_limit=self.daily.value(), monthly_limit=self.monthly.value(),
                    max_chars=self.maxc.value(), priority=self.prio.value(), expires=self.exp.text().strip(), enabled=self.enabled.isChecked())


class GatewayAdminTool(ToolPage):
    key, title, group = "gwadmin", "AI Gateway (Administrator)", "System"
    subtitle = "Run the office AI gateway on this PC, manage users and see usage. Needs the folder to be on the server PC."
    needs_output = False
    no_action = True

    def build(self, L):
        self.srv = None
        self.folder = QLineEdit(SET.get("gateway_dir") or os.path.join(CONFIG_DIR, "gateway"))
        bb = QPushButton("Browse...")
        bb.clicked.connect(self.pick)
        L.addWidget(hbox(QLabel("Data folder"), self.folder, bb))
        self.lm = QLineEdit()
        self.port = self.spin(1024, 65535, GW_DEFAULT_PORT)
        self.conc = self.spin(1, 8, 1)
        self.maxc = self.spin(10000, 5000000, 400000, " chars", 10000)
        L.addWidget(hbox(QLabel("LM Studio address"), self.lm, QLabel("Port"), self.port, QLabel("Jobs at once"), self.conc, QLabel("Max text per job"), self.maxc))
        self.ipl = QLineEdit()
        self.ipl.setPlaceholderText("Allowed IP ranges, comma separated, e.g. 192.168.1.0/24  (empty = whole network)")
        L.addWidget(self.ipl)
        self.tls_c, self.tls_k = QLineEdit(), QLineEdit()
        self.tls_c.setPlaceholderText("TLS certificate file (.pem) - optional")
        self.tls_k.setPlaceholderText("TLS key file (.pem) - optional")
        L.addWidget(hbox(self.tls_c, self.tls_k))
        self.btn = QPushButton("Start gateway")
        self.btn.setObjectName("primary")
        self.btn.clicked.connect(self.toggle)
        self.state = QLabel("Stopped.")
        self.state.setObjectName("status")
        ld = QPushButton("Load folder")
        ld.clicked.connect(self.load)
        L.addWidget(hbox(ld, self.btn, self.state, None))
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Name", "ID", "Role", "Enabled", "Expires", "Today", "Month", "Limit/day"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(190)
        L.addWidget(self.table)
        row = QHBoxLayout()
        for txt, fn in (("Add user", self.add), ("Edit", self.edit), ("New key", self.newkey), ("Remove", self.remove), ("Usage report (Excel)", self.usage)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        L.addLayout(row)
        self.add_hint("Keys are shown once, when created. Only a hash is stored - a lost key cannot be recovered, only replaced. "
                      "Usage is logged as numbers only (who, when, which feature, seconds, size) - never document text. "
                      "Windows Firewall must allow the port. For use as a Windows service see the notes at the top of this file.")
        self.store = None
        self.load()

    def pick(self):
        d = QFileDialog.getExistingDirectory(self, "Gateway data folder", self.folder.text())
        if d:
            self.folder.setText(d)
            self.load()

    def load(self):
        try:
            self.store = GatewayStore(self.folder.text().strip())
        except OSError as e:
            self.warn("That folder cannot be used: %s" % e)
            return
        c = self.store.cfg
        self.lm.setText(c["lm_base_url"]); self.port.setValue(int(c["port"])); self.conc.setValue(int(c["max_concurrent"]))
        self.maxc.setValue(int(c["max_chars_default"])); self.ipl.setText(", ".join(c.get("ip_allow_list", [])))
        self.tls_c.setText(c.get("tls_cert", "")); self.tls_k.setText(c.get("tls_key", ""))
        SET.set("gateway_dir", self.folder.text().strip())
        self.refresh()

    def refresh(self):
        if not self.store:
            return
        us = list(self.store.users["users"].values())
        self.table.setRowCount(len(us))
        for r, u in enumerate(us):
            vals = [u["name"], u["id"], u["role"], "yes" if u.get("enabled") else "NO", u.get("expires") or "-",
                    self.store.usage_today(u["id"]), self.store.usage_month(u["id"]), u.get("daily_limit") or "no limit"]
            for c_, v in enumerate(vals):
                self.table.setItem(r, c_, QTableWidgetItem(str(v)))

    def sel_id(self):
        r = self.table.currentRow()
        if r < 0:
            self.warn("Select a user in the list first.")
            return None
        return self.table.item(r, 1).text()

    def show_key(self, name, key):
        box = QMessageBox(self)
        box.setWindowTitle("Access key for " + name)
        box.setText("Give this key to %s now.\nIt will not be shown again:\n\n%s" % (name, key))
        cp = box.addButton("Copy to clipboard", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Ok)
        box.exec_()
        if box.clickedButton() == cp:
            QApplication.clipboard().setText(key)

    def add(self):
        if not self.store:
            return
        d = UserDialog(self, self.store)
        if d.exec_() == QDialog.Accepted:
            v = d.values()
            if not v["name"]:
                self.warn("Enter a name.")
                return
            name = v.pop("name")
            u, key = self.store.add_user(name, v.pop("role"), **v)
            self.refresh()
            self.show_key(name, key)

    def edit(self):
        uid = self.sel_id()
        if not uid:
            return
        d = UserDialog(self, self.store, self.store.users["users"][uid])
        if d.exec_() == QDialog.Accepted:
            self.store.update_user(uid, **d.values())
            self.refresh()

    def newkey(self):
        uid = self.sel_id()
        if uid and QMessageBox.question(self, APP_NAME, "Create a new key? The old key stops working immediately.") == QMessageBox.Yes:
            self.show_key(self.store.users["users"][uid]["name"], self.store.reset_key(uid))

    def remove(self):
        uid = self.sel_id()
        if uid and QMessageBox.question(self, APP_NAME, "Remove this user?") == QMessageBox.Yes:
            self.store.remove_user(uid)
            self.refresh()

    def usage(self):
        if not self.store:
            return
        need_lib(HAVE_XLSX, "openpyxl", "Excel export")
        dst, _ = QFileDialog.getSaveFileName(self, "Save usage report", os.path.join(os.path.expanduser("~"), "gateway_usage.xlsx"), "Excel (*.xlsx)")
        if not dst:
            return
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Date/time", "User", "Feature", "Seconds", "Characters", "Status"])
        for r in self.store.usage_rows(100000):
            ws.append([dt.datetime.fromtimestamp(r.get("ts", 0)).strftime("%Y-%m-%d %H:%M:%S"), r.get("user"), r.get("feature"), r.get("seconds"), r.get("chars"), r.get("status")])
        wb.save(dst)
        QMessageBox.information(self, APP_NAME, "Saved:\n" + dst)

    def toggle(self):
        if self.srv and self.srv.running:
            self.srv.stop()
            self.srv = None
            self.btn.setText("Start gateway")
            self.state.setText("Stopped.")
            return
        if not self.store:
            return
        c = self.store.cfg
        c.update({"lm_base_url": self.lm.text().strip(), "port": self.port.value(), "max_concurrent": self.conc.value(), "max_chars_default": self.maxc.value(),
                  "ip_allow_list": [x.strip() for x in self.ipl.text().split(",") if x.strip()], "tls_cert": self.tls_c.text().strip(), "tls_key": self.tls_k.text().strip()})
        self.store.save_cfg()
        h = _host_of(c["lm_base_url"])
        if h:
            _ALLOW_EXTRA.add(h.lower())                # the gateway must be able to reach LM Studio even in Strict Offline Mode
        try:
            self.srv = GatewayServer(self.folder.text().strip())
            self.srv.start()
        except Exception as e:
            self.srv = None
            self.warn("The gateway could not start: %s\n\nIs the port already in use?" % e)
            return
        self.btn.setText("Stop gateway")
        self.state.setText("Running on port %s (%s)" % (c["port"], "https" if c.get("tls_cert") else "http"))

    def on_show(self):
        self.refresh()


# ---------------------------------------------------------------- office deployment
class DeployTool(ToolPage):
    key, title, group = "deploy", "Office Deployment Kit", "System"
    subtitle = "Create the files you need to roll the program out to every PC: installer script, administrator settings and build commands."
    action_text = "Create deployment files"

    def build(self, L):
        self.url = QLineEdit(SET.get("ai_base_url") or "")
        self.add_row("AI gateway address to preset", self.url)
        self.upd = QLineEdit(SET.get("update_path") or "")
        self.add_row("Shared update folder to preset", self.upd)
        self.hosts = QLineEdit()
        self.hosts.setPlaceholderText("Other allowed servers, comma separated (e.g. a time-stamp server)")
        self.add_row("", self.hosts)
        self.offline = QCheckBox("Lock Strict Offline Mode ON for everyone")
        self.offline.setChecked(True)
        self.lock_ai = QCheckBox("Lock the AI address (users cannot change it)")
        self.lock_ai.setChecked(True)
        self.assoc = QCheckBox("Add 'Open with PDF Studio Pro' for .pdf files")
        self.assoc.setChecked(True)
        self.all_users = QCheckBox("Install for all users (needs administrator rights)")
        self.all_users.setChecked(True)
        for w in (self.offline, self.lock_ai, self.assoc, self.all_users):
            L.addWidget(w)
        self.hide = QLineEdit()
        self.hide.setPlaceholderText("Tools to hide from staff, comma separated keys (e.g. redact,deploy,gwadmin)")
        self.add_row("", self.hide)
        self.add_hint("Tool keys: " + ", ".join(sorted(t.key for t in ALL_TOOLS)))

    def make_task(self, out):
        cfg = {}
        if self.url.text().strip():
            cfg["ai_base_url"] = self.url.text().strip()
        if self.upd.text().strip():
            cfg["update_path"] = self.upd.text().strip()
        hosts = [h.strip() for h in self.hosts.text().split(",") if h.strip()]
        if hosts:
            cfg["allowed_hosts"] = hosts
        if self.offline.isChecked():
            cfg["offline_mode"] = True
        if not self.lock_ai.isChecked():
            cfg.pop("ai_base_url", None)
            if self.url.text().strip():
                cfg["_note"] = "ai_base_url omitted because the lock option was off"
        dis = [x.strip() for x in self.hide.text().split(",") if x.strip()]
        if dis:
            cfg["disabled_tools"] = dis
        assoc, allu = self.assoc.isChecked(), self.all_users.isChecked()

        def task(report, cancelled):
            files = []
            p = unique_path(out, "admin_settings", ".json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            files.append(p)
            iss = INNO_TEMPLATE.replace("@@VERSION@@", APP_VERSION).replace("@@PRIV@@", "admin" if allu else "lowest") \
                .replace("@@DIR@@", "{autopf}" if allu else "{localappdata}")
            if assoc:
                iss += INNO_ASSOC
            p = unique_path(out, "PDFStudioPro", ".iss")
            with open(p, "w", encoding="utf-8") as f:
                f.write(iss)
            files.append(p)
            p = unique_path(out, "build_windows", ".bat")
            with open(p, "w", encoding="utf-8", newline="\r\n") as f:
                f.write(BUILD_BAT)
            files.append(p)
            return {"message": "Deployment files created.\n\n1) Put pdf_studio_pro.py, build_windows.bat and PDFStudioPro.iss in one folder.\n"
                    "2) Run build_windows.bat (needs Python + PyInstaller).\n3) Compile PDFStudioPro.iss with Inno Setup.\n"
                    "4) Place admin_settings.json next to the installed program (the installer copies it to %ProgramData%\\PDFStudioPro).", "files": files}
        return task


INNO_TEMPLATE = r"""; PDF Studio Pro - Inno Setup script (generated)
[Setup]
AppName=PDF Studio Pro
AppVersion=@@VERSION@@
DefaultDirName={@@DIR@@}\PDFStudioPro
DefaultGroupName=PDF Studio Pro
PrivilegesRequired=@@PRIV@@
OutputBaseFilename=PDFStudioPro_Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\PDFStudioPro.exe

[Files]
Source: "dist\PDFStudioPro\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "admin_settings.json"; DestDir: "{commonappdata}\PDFStudioPro"; Flags: ignoreversion onlyifdoesntexist skipifsourcedoesntexist
Source: "fonts\*"; DestDir: "{app}\fonts"; Flags: recursesubdirs skipifsourcedoesntexist ignoreversion

[Icons]
Name: "{group}\PDF Studio Pro"; Filename: "{app}\PDFStudioPro.exe"
Name: "{autodesktop}\PDF Studio Pro"; Filename: "{app}\PDFStudioPro.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Run]
Filename: "{app}\PDFStudioPro.exe"; Description: "Start PDF Studio Pro"; Flags: nowait postinstall skipifsilent
"""
_INNO_CMD = '"""{app}\\PDFStudioPro.exe"" ""%1"""'          # Inno Setup quoting: "" = one literal quote
INNO_ASSOC = (
    "\n[Registry]\n"
    'Root: HKA; Subkey: "Software\\Classes\\Applications\\PDFStudioPro.exe\\shell\\open\\command"; ValueType: string; ValueData: ' + _INNO_CMD + '; Flags: uninsdeletekey\n'
    'Root: HKA; Subkey: "Software\\Classes\\SystemFileAssociations\\.pdf\\shell\\PDFStudioPro"; ValueType: string; ValueData: "Open with PDF Studio Pro"; Flags: uninsdeletekey\n'
    'Root: HKA; Subkey: "Software\\Classes\\SystemFileAssociations\\.pdf\\shell\\PDFStudioPro\\command"; ValueType: string; ValueData: ' + _INNO_CMD + '\n')
BUILD_BAT = r"""@echo off
rem PDF Studio Pro - build the Windows program (run once per release)
python -m pip install --upgrade pyinstaller PyQt5 PyMuPDF Pillow numpy opencv-python-headless pytesseract openpyxl python-docx python-pptx pdf2docx qrcode python-barcode pyhanko python-pkcs11
python -m PyInstaller --noconfirm --windowed --name PDFStudioPro --collect-all pymupdf --collect-all pyhanko --collect-all pyhanko_certvalidator --collect-all pkcs11 --collect-all pdf2docx --collect-all docx --collect-all pptx --collect-all openpyxl --collect-all cv2 --hidden-import PIL --hidden-import pytesseract --hidden-import qrcode --hidden-import barcode pdf_studio_pro.py
echo.
echo Done. The program is in dist\PDFStudioPro  - now compile PDFStudioPro.iss with Inno Setup.
pause
"""


# ---------------------------------------------------------------- About / help
SHORTCUTS = [("Ctrl+O", "Open a PDF in the reader"), ("Ctrl+K", "Jump to the tool search box"), ("Ctrl+,", "Settings"),
             ("F1", "This list"), ("Ctrl+Q", "Exit"), ("Esc", "Cancel the running job (when a page is busy)")]


def show_about(parent):
    ok = lambda f: "yes" if f else "no"
    pv = getattr(fitz, "__doc__", "") or ""
    txt = ("<h2>%s %s</h2><p>Offline PDF toolkit for professional offices.</p>"
           "<p><b>Engine:</b> PyMuPDF %s<br><b>Qt:</b> %s<br><b>Python:</b> %s</p>"
           "<p><b>Optional parts available:</b><br>OCR (pytesseract): %s - Tesseract program: %s<br>Images (Pillow): %s - Clean-up (OpenCV): %s<br>Excel: %s - Word: %s - PowerPoint: %s<br>"
           "QR: %s - Barcode: %s - Digital signatures (pyHanko): %s</p>"
           "<p><b>Strict Offline Mode:</b> %s<br><b>Logs:</b> %s</p>"
           "<p style='color:#666'>Your documents never leave this computer, except text you send to the AI server you configured. "
           "No passwords or PINs are stored. Licence notes: PyMuPDF is AGPL/commercial, PyQt5 is GPL/commercial - check before distributing outside your office.</p>") % (
        APP_NAME, APP_VERSION, getattr(fitz, "VersionBind", "?"), QT_VERSION_STR, sys.version.split()[0], ok(HAVE_PYTESS), ok(tess_ready() if "tess_ready" in globals() else False),
        ok(HAVE_PIL), ok(HAVE_CV2), ok(HAVE_XLSX), ok(HAVE_DOCX), ok(HAVE_PPTX), ok(HAVE_QR), ok(HAVE_BARCODE), ok(importlib.util.find_spec("pyhanko")),
        "ON" if SET.get("offline_mode") else "off", LOG_DIR)
    QMessageBox.about(parent, "About " + APP_NAME, txt)


def show_shortcuts(parent):
    QMessageBox.information(parent, "Keyboard shortcuts", "\n".join("%-8s  %s" % s for s in SHORTCUTS))


# ============================================================================
#  SECTION O - PHASE 9: DIGITAL SIGNATURES (DSC / USB TOKEN) - pyHanko
#  !! Cannot be fully tested without the real USB token. Use "Token diagnostics" first. !!
# ============================================================================
P11_CANDIDATES = [
    ("eMudhra / ePass2003 (Feitian)", ["eps2003csp11v2.dll", "eps2003csp11.dll", "ShuttleCsp11_3003.dll", "ep2003csp11.dll"]),
    ("WatchData (ProxKey / TimeStamp)", ["SignatureP11.dll", "wdpkcs.dll", "WDPKCS.dll", "Watchdata\\PROXKey CSP India V3.0\\wdpkcs.dll"]),
    ("SafeNet (Sify / Capricorn / Gemalto)", ["eTPKCS11.dll", "eToken.dll", "IDPrimePKCS1164.dll", "IDPrimePKCS11.dll"]),
    ("HYP2003 (Hypersecu)", ["eps2003csp11.dll", "HID_PKCS11.dll", "hyp2003p11.dll", "HYP2003csp11.dll"]),
    ("mToken (Longmai)", ["CryptoIDA_pkcs11.dll", "mToken_pkcs11.dll", "mtoken.dll", "CryptoIDA_pkcs11v2.dll"]),
    ("TrustKey / Moserbaer", ["TRUSTKEYP11_ND_v34.dll", "TrustKeyP11.dll", "aetpkss1.dll"]),
    ("StarSign / Aladdin / other", ["aetpkss1.dll", "cmP1164.dll", "cmP11.dll", "bit4xpki.dll", "acospkcs11.dll"]),
    ("OpenSC (generic)", ["opensc-pkcs11.dll", "opensc-pkcs11.so"]),
    ("SoftHSM (test token)", ["libsofthsm2.so", "softhsm2-x64.dll", "softhsm2.dll"]),
]


def find_pkcs11():
    dirs = []
    if IS_WIN:
        for e in ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)"):
            b = os.environ.get(e)
            if b:
                dirs += [os.path.join(b, "System32"), os.path.join(b, "SysWOW64"), b]
        for e in ("ProgramFiles", "ProgramFiles(x86)"):
            b = os.environ.get(e)
            if b and os.path.isdir(b):
                dirs.append(os.path.join(b, "OpenSC Project", "OpenSC", "pkcs11"))
                try:                                            # vendor folders such as "C:\Program Files\Feitian\ePass2003"
                    for v in os.listdir(b):
                        if re.search(r"feitian|epass|watchdata|proxkey|safenet|hyp|longmai|mtoken|trustkey|emudhra|softhsm|token|gemalto|bit4id", v, re.I):
                            vp = os.path.join(b, v)
                            dirs.append(vp)
                            for root, ds, _fs in os.walk(vp):
                                if root.count(os.sep) - vp.count(os.sep) < 3:
                                    dirs += [os.path.join(root, d) for d in ds]
                except OSError:
                    pass
    else:
        dirs = ["/usr/lib", "/usr/lib/x86_64-linux-gnu", "/usr/lib/opensc-pkcs11", "/usr/lib/x86_64-linux-gnu/opensc-pkcs11", "/usr/local/lib", "/usr/lib/softhsm",
                "/usr/lib/x86_64-linux-gnu/softhsm"]
    found = []
    want64 = struct.calcsize("P") * 8 == 64
    for name, libs in P11_CANDIDATES:
        for d in dirs:
            if IS_WIN and want64 and d.lower().endswith("syswow64"):
                continue                                         # 32-bit drivers cannot be loaded by this 64-bit program
            for l in libs:
                p = os.path.join(d, l)
                if os.path.isfile(p) and os.path.normcase(p) not in [os.path.normcase(x[1]) for x in found]:
                    found.append((name, p))
    return found


def need_hanko():
    if not importlib.util.find_spec("pyhanko"):
        raise UserError("Digital signatures need the 'pyhanko' package.\nRun:  pip install pyhanko python-pkcs11")


def cert_summary(cert):
    """Facts about an asn1crypto certificate that matter when choosing a signing certificate."""
    d = {"cn": "", "issuer": "", "not_after": None, "expired": False, "sign_ok": True, "ca": False, "subject": ""}
    try:
        d["subject"] = cert.subject.human_friendly
        d["cn"] = cert.subject.native.get("common_name") or d["subject"]
        if isinstance(d["cn"], (list, tuple)):
            d["cn"] = ", ".join(str(x) for x in d["cn"])
        iss = cert.issuer.native.get("common_name") or cert.issuer.native.get("organization_name") or ""
        d["issuer"] = ", ".join(iss) if isinstance(iss, (list, tuple)) else str(iss)
        na = cert["tbs_certificate"]["validity"]["not_after"].native
        d["not_after"] = na
        d["expired"] = na < dt.datetime.now(na.tzinfo)
        d["ca"] = bool(cert.ca)
        ku = cert.key_usage_value
        if ku is not None:
            ku = ku.native
            d["sign_ok"] = ("digital_signature" in ku) or ("non_repudiation" in ku)
        if d["ca"]:
            d["sign_ok"] = False
    except Exception:
        pass
    return d


def cert_line(s):
    return "%s  -  issued by %s  -  valid to %s%s%s" % (s["cn"] or "?", s["issuer"] or "?", s["not_after"].date() if s["not_after"] else "?",
                                                         "  (EXPIRED)" if s["expired"] else "", "" if s["sign_ok"] else "  (not a signing certificate)")


def pick_signing_cert(entries):
    """entries: [(summary, anything)].  Best first: valid signing certificate, latest expiry."""
    good = [e for e in entries if e[0]["sign_ok"] and not e[0]["expired"]]
    pool = good or [e for e in entries if e[0]["sign_ok"]] or [e for e in entries if not e[0]["ca"]] or list(entries)
    if not pool:
        return None
    return sorted(pool, key=lambda e: (e[0]["not_after"].timestamp() if e[0]["not_after"] else 0), reverse=True)[0]


def build_cert_chain(cert, pool):
    """Issuer certificates of 'cert' found in 'pool' (leaf not included), nearest first."""
    chain, cur = [], cert
    for _ in range(8):
        if cur.self_signed in ("yes", "maybe") and cur.issuer == cur.subject:
            break
        nxt = None
        for c in pool:
            if c.subject == cur.issuer and c.dump() != cur.dump():
                aki, ski = cur.authority_key_identifier, c.key_identifier
                if aki and ski and aki != ski:
                    continue
                nxt = c
                break
        if nxt is None:
            break
        chain.append(nxt)
        cur = nxt
    return chain


def p11_list_certs(session):
    """[(summary, cert_id bytes, label, asn1 cert)] for every certificate on an open token session."""
    import pkcs11
    from asn1crypto import x509 as ax
    out = []
    for o in session.get_objects({pkcs11.Attribute.CLASS: pkcs11.ObjectClass.CERTIFICATE}):
        try:
            c = ax.Certificate.load(o[pkcs11.Attribute.VALUE])
            try:
                cid = bytes(o[pkcs11.Attribute.ID])
            except Exception:
                cid = b""
            try:
                lbl = o[pkcs11.Attribute.LABEL]
            except Exception:
                lbl = ""
            out.append((cert_summary(c), cid, lbl, c))
        except Exception:
            continue
    return out


def p11_open(libpath, pin):
    """Log in to THE token of a driver library.  Many drivers show several slots (empty readers, virtual slots): the PIN is
    sent to one token only, never tried on several, so that a mistake cannot use up PIN attempts on the wrong device."""
    import pkcs11
    try:
        lib = pkcs11.lib(libpath)
    except Exception as e:
        raise UserError("The token library could not be loaded: %s\n\nCommon causes: wrong (32/64-bit) driver, driver not installed, or another "
                        "token library was already used in this session (close and restart the program to switch)." % (str(e) or type(e).__name__)[:200])
    toks = []
    for sl in lib.get_slots(token_present=True):
        try:
            tok = sl.get_token()
            if tok.flags & pkcs11.TokenFlag.TOKEN_INITIALIZED:
                toks.append(tok)
        except Exception:
            continue
    if not toks:
        raise UserError("No USB token was found. Plug it in, wait for its light, and try again.")
    ready = [t for t in toks if t.flags & pkcs11.TokenFlag.USER_PIN_INITIALIZED] or toks
    tok = ready[0]
    try:
        return tok.open(user_pin=pin)
    except Exception as e:
        n = type(e).__name__
        if "PinIncorrect" in n or "PinInvalid" in n or "PinLenRange" in n:
            raise UserError("The PIN was NOT accepted by the token '%s'.\nCareful: repeated wrong PINs LOCK the token. After 2 failures stop and "
                            "check with your certificate provider." % (tok.label or "").strip())
        if "PinLocked" in n:
            raise UserError("The token is LOCKED (too many wrong PINs). Contact your certificate provider to unblock it.")
        raise UserError("The token could not be opened: %s\nCheck that it is plugged in and run 'Token diagnostics'." % ((str(e) or n)[:200]))


def p11_diagnose(libpath, pin=None, report=None):
    """Return (plain-text report, [(text, cert_id hex, label)]).  Never prints the PIN."""
    lines = []
    if not libpath or not os.path.isfile(libpath):
        raise UserError("Choose the token's PKCS#11 library file (a .dll) first - use 'Find automatically' or the file from the token's driver folder.")
    try:
        import pkcs11
    except ImportError:
        raise UserError("USB token support needs the 'python-pkcs11' package.\nRun:  pip install python-pkcs11")
    if IS_WIN and struct.calcsize("P") * 8 == 64:
        lines.append("This program is 64-bit - the token library must also be 64-bit.")
    try:
        lib = pkcs11.lib(libpath)
    except Exception as e:
        raise UserError("The token library could not be loaded: %s\n\nCommon causes: wrong (32/64-bit) driver, driver not installed, "
                        "or another library was already loaded in this session (close and restart the program to switch libraries).\n"
                        "Tip: 'Windows certificate store' in the 'Signing with' list needs no library file at all." % str(e)[:200])
    lines.append("Library loaded: %s" % os.path.basename(libpath))
    try:
        lines.append("Library: %s %s" % (lib.manufacturer_id, ".".join(str(x) for x in lib.library_version)))
    except Exception:
        pass
    slots = lib.get_slots(token_present=True)
    if not slots:
        lines.append("NO TOKEN FOUND. Plug in the USB token, wait for its light, and try again.")
        return "\n".join(lines), []
    certs_out = []
    for sl in slots:
        try:
            tok = sl.get_token()
            if not (tok.flags & pkcs11.TokenFlag.TOKEN_INITIALIZED):
                continue
        except Exception:
            continue
        lines.append("Slot %s: token '%s'" % (sl.slot_id, (tok.label or "").strip()))
        if pin:
            try:
                with tok.open(user_pin=pin) as sess:
                    found = p11_list_certs(sess)
                    for sm, cid, lbl, c in found:
                        lines.append("   " + cert_line(sm))
                        certs_out.append((cert_line(sm), cid.hex(), lbl))
                    if not found:
                        lines.append("   No certificate is stored on this token.")
                    best = pick_signing_cert([(f[0], f) for f in found])
                    if best:
                        lines.append("   -> will sign with: %s" % best[0]["cn"])
                        certs_out.sort(key=lambda t: 0 if t[1] == best[1][1].hex() and t[2] == best[1][2] else 1)
            except Exception as e:
                m = str(e) or type(e).__name__
                if "PIN" in (m + type(e).__name__).upper():
                    lines.append("   The PIN was not accepted (%s). Careful: repeated wrong PINs LOCK the token." % type(e).__name__)
                else:
                    lines.append("   Could not read certificates: %s" % m[:160])
        else:
            lines.append("   (Enter the PIN to list the certificates on the token.)")
    return "\n".join(lines), certs_out


# ------------------------------------------------- Windows certificate store (CryptoAPI / CNG) - no PKCS#11 file needed
_WIN_ERR = {0x8010006E: "You cancelled the PIN window.", 0x8010006B: "The PIN is wrong. Careful: repeated wrong PINs LOCK the token.",
            0x8010006C: "The token is LOCKED (too many wrong PINs). Contact your certificate provider.",
            0x8010000C: "The USB token is not plugged in.", 0x80100069: "The USB token was removed.", 0x8010002E: "No smart-card reader / token was found.",
            0x80090016: "The private key for this certificate was not found - plug in the token that holds it.",
            0x8009000D: "The private key for this certificate was not found - plug in the token that holds it.",
            0x80090008: "The token driver does not support SHA-256 through Windows. Use 'USB token (PKCS#11)' instead.",
            0x80090029: "The token driver does not support this operation through Windows. Use 'USB token (PKCS#11)' instead.",
            0x000004C7: "You cancelled the PIN window.", 0x8010001D: "The Windows 'Smart Card' service is not running."}


def _win_err(code, what):
    code &= 0xFFFFFFFF
    return UserError("%s\n%s (Windows code 0x%08X)" % (what, _WIN_ERR.get(code, "Windows could not use the certificate's private key."), code))


def _win_crypt32():
    if not IS_WIN:
        raise UserError("The Windows certificate store is available on Windows only.")
    import ctypes
    from ctypes import wintypes

    class CERT_CONTEXT(ctypes.Structure):
        _fields_ = [("dwCertEncodingType", wintypes.DWORD), ("pbCertEncoded", ctypes.POINTER(ctypes.c_ubyte)),
                    ("cbCertEncoded", wintypes.DWORD), ("pCertInfo", ctypes.c_void_p), ("hCertStore", ctypes.c_void_p)]
    PCC = ctypes.POINTER(CERT_CONTEXT)
    c32 = ctypes.WinDLL("crypt32", use_last_error=True)
    c32.CertOpenSystemStoreW.restype = ctypes.c_void_p
    c32.CertOpenSystemStoreW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    c32.CertEnumCertificatesInStore.restype = PCC
    c32.CertEnumCertificatesInStore.argtypes = [ctypes.c_void_p, PCC]
    c32.CertCloseStore.restype = wintypes.BOOL
    c32.CertCloseStore.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    c32.CertFreeCertificateContext.restype = wintypes.BOOL
    c32.CertFreeCertificateContext.argtypes = [PCC]
    c32.CertGetCertificateContextProperty.restype = wintypes.BOOL
    c32.CertGetCertificateContextProperty.argtypes = [PCC, wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]
    c32.CryptAcquireCertificatePrivateKey.restype = wintypes.BOOL
    c32.CryptAcquireCertificatePrivateKey.argtypes = [PCC, wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
                                                      ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.BOOL)]
    return ctypes, wintypes, c32, PCC


def win_store_ders(store="MY", need_key=False):
    """DER bytes of the certificates in a Windows store of the current user."""
    ctypes, wintypes, c32, PCC = _win_crypt32()
    h = c32.CertOpenSystemStoreW(None, store)
    if not h:
        return []
    out = []
    try:
        ctx = c32.CertEnumCertificatesInStore(h, None)
        while ctx:
            der = ctypes.string_at(ctx.contents.pbCertEncoded, ctx.contents.cbCertEncoded)
            ok = True
            if need_key:
                n = wintypes.DWORD(0)
                ok = bool(c32.CertGetCertificateContextProperty(ctx, 2, None, ctypes.byref(n)))        # CERT_KEY_PROV_INFO_PROP_ID
            if ok:
                out.append(der)
            ctx = c32.CertEnumCertificatesInStore(h, ctx)                                               # frees the previous context
    finally:
        c32.CertCloseStore(h, 0)
    return out


def win_store_certs():
    """[(summary, der)] - personal certificates that have a private key (tokens register theirs here when plugged in)."""
    from asn1crypto import x509 as ax
    res = []
    for der in win_store_ders("MY", need_key=True):
        try:
            res.append((cert_summary(ax.Certificate.load(der)), der))
        except Exception:
            continue
    return res


def win_store_sign(der, digest, hash_name, pin=None, hwnd=0):
    """Sign a ready-made hash with the private key that belongs to certificate 'der' (RSA, PKCS#1 v1.5).
    The token's own driver shows its PIN window.  !! Written for Windows CNG / CryptoAPI - not testable without Windows + token. !!"""
    ctypes, wintypes, c32, PCC = _win_crypt32()
    alg = {"sha1": ("SHA1", 0x8004), "sha256": ("SHA256", 0x800C), "sha384": ("SHA384", 0x800D), "sha512": ("SHA512", 0x800E)}.get(hash_name.lower())
    if not alg:
        raise UserError("Hash '%s' is not supported for the Windows certificate store." % hash_name)
    h = c32.CertOpenSystemStoreW(None, "MY")
    if not h:
        raise UserError("The Windows certificate store could not be opened.")
    ctx = None
    try:
        cur = c32.CertEnumCertificatesInStore(h, None)
        while cur:
            if ctypes.string_at(cur.contents.pbCertEncoded, cur.contents.cbCertEncoded) == der:
                ctx = cur
                break
            cur = c32.CertEnumCertificatesInStore(h, cur)
        if not ctx:
            raise UserError("The chosen certificate is no longer in the Windows store. Plug the token in and press 'Refresh list'.")
        hkey, spec, must_free = ctypes.c_void_p(), wintypes.DWORD(0), wintypes.BOOL(False)
        if not c32.CryptAcquireCertificatePrivateKey(ctx, 0x00020000, None, ctypes.byref(hkey), ctypes.byref(spec), ctypes.byref(must_free)):
            raise _win_err(ctypes.get_last_error(), "The private key of this certificate could not be opened.")
        buf = ctypes.create_string_buffer(2048)
        if spec.value == 0xFFFFFFFF:                                           # CNG key (most current token drivers)
            nc = ctypes.WinDLL("ncrypt")

            class PAD(ctypes.Structure):
                _fields_ = [("pszAlgId", ctypes.c_wchar_p)]
            nc.NCryptSignHash.restype = ctypes.c_long
            nc.NCryptSignHash.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                          ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
            nc.NCryptSetProperty.restype = ctypes.c_long
            nc.NCryptSetProperty.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD]
            nc.NCryptFreeObject.restype = ctypes.c_long
            nc.NCryptFreeObject.argtypes = [ctypes.c_void_p]
            try:
                if hwnd:
                    hw = ctypes.c_void_p(int(hwnd))
                    nc.NCryptSetProperty(hkey, "HWND Handle", ctypes.byref(hw), ctypes.sizeof(hw), 0)
                if pin:
                    pw = ctypes.create_unicode_buffer(pin)
                    nc.NCryptSetProperty(hkey, "SmartCardPin", pw, ctypes.sizeof(pw), 0)
                pad, n = PAD(alg[0]), wintypes.DWORD(0)
                st = nc.NCryptSignHash(hkey, ctypes.byref(pad), digest, len(digest), buf, len(buf), ctypes.byref(n), 0x2)   # BCRYPT_PAD_PKCS1
                if st != 0:
                    raise _win_err(st, "Signing with the token failed.")
                return buf.raw[:n.value]
            finally:
                if must_free.value:
                    nc.NCryptFreeObject(hkey)
        adv = ctypes.WinDLL("advapi32", use_last_error=True)                   # older CSP key
        adv.CryptCreateHash.restype = wintypes.BOOL
        adv.CryptCreateHash.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)]
        adv.CryptSetHashParam.restype = wintypes.BOOL
        adv.CryptSetHashParam.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_char_p, wintypes.DWORD]
        adv.CryptSignHashW.restype = wintypes.BOOL
        adv.CryptSignHashW.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_wchar_p, wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]
        adv.CryptDestroyHash.argtypes = [ctypes.c_void_p]
        adv.CryptReleaseContext.argtypes = [ctypes.c_void_p, wintypes.DWORD]
        adv.CryptSetProvParam.restype = wintypes.BOOL
        adv.CryptSetProvParam.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        hh = ctypes.c_void_p()
        try:
            if hwnd:
                hw = ctypes.c_void_p(int(hwnd))
                adv.CryptSetProvParam(hkey, 1, ctypes.byref(hw), 0)                                     # PP_CLIENT_HWND
            if pin:
                try:
                    pb = ctypes.create_string_buffer(pin.encode("ascii"))
                    adv.CryptSetProvParam(hkey, 33 if spec.value == 2 else 32, pb, 0)                   # PP_SIGNATURE_PIN / PP_KEYEXCHANGE_PIN
                except UnicodeEncodeError:
                    pass
            if not adv.CryptCreateHash(hkey, alg[1], None, 0, ctypes.byref(hh)):
                raise _win_err(ctypes.get_last_error(), "The token driver refused to start a %s signature." % alg[0])
            if not adv.CryptSetHashParam(hh, 2, digest, 0):                                             # HP_HASHVAL
                raise _win_err(ctypes.get_last_error(), "The token driver refused the document hash.")
            n = wintypes.DWORD(len(buf))
            if not adv.CryptSignHashW(hh, spec.value, None, 0, buf, ctypes.byref(n)):
                raise _win_err(ctypes.get_last_error(), "Signing with the token failed.")
            return buf.raw[:n.value][::-1]                                                              # CryptoAPI gives little-endian
        finally:
            if hh:
                adv.CryptDestroyHash(hh)
            if must_free.value:
                adv.CryptReleaseContext(hkey, 0)
    finally:
        if ctx:
            c32.CertFreeCertificateContext(ctx)
        c32.CertCloseStore(h, 0)


def make_hash_signer(der, chain_ders, raw_sign):
    """A pyHanko signer whose private-key operation is done elsewhere: raw_sign(digest_bytes, hash_name) -> signature bytes."""
    from pyhanko.sign import signers
    from pyhanko_certvalidator.registry import SimpleCertificateStore
    from asn1crypto import x509 as ax
    cert = ax.Certificate.load(der)
    if cert.public_key.algorithm != "rsa":
        raise UserError("This certificate does not use an RSA key. Use 'USB token (PKCS#11)' for it.")
    reg = SimpleCertificateStore()
    reg.register_multiple([ax.Certificate.load(c) for c in chain_ders])
    klen = (cert.public_key.bit_size + 7) // 8

    class HashSigner(signers.Signer):
        async def async_sign_raw(self, data, digest_algorithm, dry_run=False):
            if dry_run:
                return bytes(klen)
            sig = raw_sign(hashlib.new(digest_algorithm, data).digest(), digest_algorithm)
            if len(sig) != klen:
                raise UserError("The token returned a signature of an unexpected size (%d bytes)." % len(sig))
            return sig
    return HashSigner(signing_cert=cert, cert_registry=reg)


def win_store_signer(der, pin=None, hwnd=0):
    from asn1crypto import x509 as ax
    leaf = ax.Certificate.load(der)
    pool = []
    for st in ("CA", "ROOT", "MY"):
        try:
            for d in win_store_ders(st):
                try:
                    pool.append(ax.Certificate.load(d))
                except Exception:
                    pass
        except UserError:
            raise
        except Exception:
            pass
    chain = [c.dump() for c in build_cert_chain(leaf, pool)]
    return make_hash_signer(der, chain, lambda digest, name: win_store_sign(der, digest, name, pin, hwnd))


def sign_box_for(page_rect, mediabox, rot, derot, k, picked=None):
    """pyHanko box (PDF user space, y up) for preset position k or a picked rectangle (unrotated page space)."""
    H = mediabox.height
    bw, bh = 210, 64
    if picked is not None:
        r = fitz.Rect(picked)
    else:
        m, Wd, Hd = 36, page_rect.width, page_rect.height        # presets are defined on the page as it is DISPLAYED
        if rot in (90, 270):
            bw, bh = bh, bw
        x0 = {0: Wd - bw - m, 1: m, 2: (Wd - bw) / 2, 3: Wd - bw - m, 4: m}.get(k, m)
        y0 = {0: Hd - bh - m, 1: Hd - bh - m, 2: Hd - bh - m, 3: m, 4: m}.get(k, m)
        r = fitz.Rect(x0, y0, x0 + bw, y0 + bh) * derot
        r.normalize()
    return (int(mediabox.x0 + r.x0), int(mediabox.y0 + H - r.y1), int(mediabox.x0 + r.x1), int(mediabox.y0 + H - r.y0))


def core_sign_pdf(src, dst, signer, page_index=0, box=None, meta=None, ts_url=None, who=""):
    """Add ONE signature (incremental save - earlier signatures stay valid)."""
    from pyhanko.sign import signers, fields, timestamps
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.stamp import TextStampStyle
    meta = meta or {}
    tzv = os.environ.get("TZ")
    if tzv:                                         # an unusual TZ variable would make pyHanko's time zone look-up fail
        try:
            import zoneinfo
            zoneinfo.ZoneInfo(tzv)
            import tzlocal
            tzlocal.get_localzone()
        except Exception:
            os.environ.pop("TZ", None)
    fname = "Signature_%s_%s" % (dt.datetime.now().strftime("%H%M%S"), secrets.token_hex(2))
    smeta = signers.PdfSignatureMetadata(field_name=fname, md_algorithm="sha256", **meta)
    tstamper = timestamps.HTTPTimeStamper(ts_url) if ts_url else None
    txt = "Digitally signed by\n%(cn)s\nDate: %(ts)s"
    if meta.get("reason"):
        txt += "\nReason: %(reason)s"
    if meta.get("location"):
        txt += "\nPlace: %(place)s"
    style = TextStampStyle(stamp_text=txt, border_width=1) if box else None
    spec = fields.SigFieldSpec(fname, on_page=page_index, box=box) if box else fields.SigFieldSpec(fname)
    with open(src, "rb") as inf:
        w = IncrementalPdfFileWriter(inf, strict=False)
        ps = signers.PdfSigner(smeta, signer=signer, timestamper=tstamper, stamp_style=style, new_field_spec=spec)
        with open(dst, "wb") as outf:
            ps.sign_pdf(w, output=outf, appearance_text_params={"cn": who or "certificate holder", "reason": meta.get("reason") or "",
                                                                "place": meta.get("location") or ""})


class DscSignTool(ToolPage):
    key, title, group = "dsc", "Digital Signature (DSC)", "Security"
    subtitle = "Sign PDFs with your Digital Signature Certificate (USB token or .pfx file)."
    action_text = "Sign the PDF"

    def build(self, L):
        self.pdf = PdfPicker("dsc")
        self.add_row("PDF to sign", self.pdf)
        self.more = FileListWidget("dsc_more")
        self.more.setMaximumHeight(110)
        self.add_row("More PDFs to sign in the same run (optional)", self.more)
        modes = [("USB token / smart card - PKCS#11 driver file", "p11"), ("Certificate file (.pfx / .p12)", "pfx")]
        if IS_WIN:
            modes.insert(0, ("USB token through Windows (easiest - the token's own PIN window opens)", "win"))
        self.mode = self.combo(modes)
        self.add_row("Signing with", self.mode)
        for cb in (self.mode,):
            cb.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            cb.setMinimumContentsLength(30)
        # --- Windows store
        self.winw = QWidget(); wl = QVBoxLayout(self.winw); wl.setContentsMargins(0, 0, 0, 0)
        self.wcert = self.combo(["(press 'Refresh list' after plugging in the token)"])
        self.wcert.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.wcert.setMinimumContentsLength(30)
        rb = QPushButton("Refresh list")
        rb.clicked.connect(lambda: self.refresh_win(False))
        wl.addWidget(hbox(QLabel("Certificate"), self.wcert, rb, None))
        L.addWidget(self.winw)
        # --- PKCS#11
        self.p11 = QWidget(); pl = QVBoxLayout(self.p11); pl.setContentsMargins(0, 0, 0, 0)
        self.lib = FilePicker("p11lib", (".dll", ".so", ".dylib"), "Select the token's PKCS#11 library", "Libraries (*.dll *.so *.dylib);;All files (*.*)")
        self.lib.set_path(SET.get("pkcs11_path"))
        pl.addWidget(self.lib)
        self.libs = self.combo(["(automatic search found nothing yet)"])
        self.libs.activated.connect(lambda i: self.lib.set_path(self.libs.itemData(i)) if self.libs.itemData(i) else None)
        self.libs.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.libs.setMinimumContentsLength(30)
        fb = QPushButton("Find automatically")
        fb.clicked.connect(self.find_lib)
        pl.addWidget(hbox(fb, self.libs, None))
        self.pcert = self.combo([("Automatic - the valid signing certificate on the token", "")])
        self.pcert.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.pcert.setMinimumContentsLength(30)
        pl.addWidget(hbox(QLabel("Certificate"), self.pcert, None))
        L.addWidget(self.p11)
        # --- PFX
        self.pfxw = QWidget(); fl = QVBoxLayout(self.pfxw); fl.setContentsMargins(0, 0, 0, 0)
        self.pfx = FilePicker("pfx", (".pfx", ".p12"), "Select certificate file", "Certificate (*.pfx *.p12)")
        fl.addWidget(self.pfx)
        L.addWidget(self.pfxw)
        self.pin = PasswordField("Token PIN / certificate password (never stored)")
        self.pin_hint = QLabel("")
        self.pin_hint.setObjectName("hint")
        self.pin_hint.setWordWrap(True)
        self.add_row("PIN / password", self.pin)
        L.addWidget(self.pin_hint)
        self.diagb = QPushButton("Token diagnostics (test the token without signing)")
        self.diagb.clicked.connect(self.diagnose)
        L.addWidget(hbox(self.diagb, None))
        self.diag = QTextEdit()
        self.diag.setReadOnly(True)
        self.diag.setMaximumHeight(110)
        self.diag.setLineWrapMode(QTextEdit.WidgetWidth)
        L.addWidget(self.diag)
        self.reason = QLineEdit("I approve this document")
        self.loc = QLineEdit()
        self.contact = QLineEdit()
        L.addWidget(hbox(QLabel("Reason"), self.reason, QLabel("Place"), self.loc, QLabel("Contact"), self.contact))
        self.visible = QCheckBox("Show a visible signature box")
        self.visible.setChecked(True)
        self.where = self.combo([("on the first page", "first"), ("on the last page", "last"), ("on page number", "num")], "on the last page")
        self.page = self.spin(1, 99999, 1)
        self.pos = self.combo(["Bottom right", "Bottom left", "Bottom centre", "Top right", "Top left", "Chosen on the page"])
        pb = QPushButton("Pick on the page...")
        pb.clicked.connect(self.pick_box)
        L.addWidget(hbox(self.visible, self.where, self.page, None))
        L.addWidget(hbox(QLabel("Position of the box"), self.pos, pb, None))
        self.where.currentIndexChanged.connect(lambda i: self.page.setEnabled(self.where.currentData() == "num"))
        self.page.setEnabled(False)
        self.picked = None
        self.ts = QLineEdit()
        self.ts.setPlaceholderText("Time-stamp server address (optional; the server must be in the allowed list in Settings)")
        self.add_row("RFC 3161 time-stamp (optional)", self.ts)
        self.add_hint("The signed copy is saved as a NEW file (name_signed.pdf) and is checked straight after signing. Do not edit or re-save a "
                      "signed file in any program - that breaks the signature. A wrong PIN twice can LOCK a token: stop and call your provider. "
                      "First time with a new token: run 'Token diagnostics', then sign a test page and open it in Adobe Reader.")
        self.mode.currentIndexChanged.connect(self._m)
        self._m(0)
        self.find_lib(quiet=True)
        if IS_WIN:
            self.refresh_win(True)

    def _m(self, i=0):
        m = self.mode.currentData()
        self.winw.setVisible(m == "win")
        self.p11.setVisible(m == "p11")
        self.pfxw.setVisible(m == "pfx")
        self.diagb.setVisible(m != "pfx")
        self.pin_hint.setText({"win": "Leave the PIN empty: the token's own PIN window opens when you sign. (You may also type it here.)",
                               "p11": "Type the token PIN. Wrong PINs can lock a token - after 2 failures stop and check with your certificate provider.",
                               "pfx": "Type the password of the .pfx / .p12 file."}.get(m, ""))

    def refresh_win(self, quiet=False):
        self.wcert.clear()
        try:
            certs = win_store_certs()
        except Exception as e:
            self.wcert.addItem("(Windows certificate store not available)")
            if not quiet:
                self.warn(str(e))
            return
        if not certs:
            self.wcert.addItem("(no certificate found - plug in the token, wait 10 seconds, press 'Refresh list')")
            if not quiet:
                self.warn("No certificate with a private key was found in Windows.\n\nPlug in the USB token and make sure its driver "
                          "(from your certificate provider) is installed. If it still does not appear, use 'USB token / smart card - PKCS#11 driver file'.")
            return
        best = pick_signing_cert(certs)
        certs.sort(key=lambda e: 0 if best and e[1] == best[1] else 1)
        for sm, der in certs:
            self.wcert.addItem(cert_line(sm), der)

    def find_lib(self, quiet=False):
        found = find_pkcs11()
        self.libs.clear()
        if not found:
            self.libs.addItem("(nothing found - choose the file above)")
            if not quiet:
                self.warn("No token driver was found automatically.\nInstall your token's driver (from your certificate provider) and look for a file such as "
                          "eps2003csp11.dll / SignatureP11.dll / eTPKCS11.dll in C:\\Windows\\System32, then choose it above.")
            return
        for n, p in found:
            self.libs.addItem("%s  -  %s" % (n, p), p)
        if not self.lib.path():
            self.lib.set_path(found[0][1])

    def diagnose(self):
        if self.mode.currentData() == "win":
            self.refresh_win(False)
            n = sum(1 for i in range(self.wcert.count()) if self.wcert.itemData(i))
            self.diag.setPlainText("Certificates with a private key known to Windows: %d\n%s\n\nThe PIN is checked only when you sign."
                                   % (n, "\n".join("  " + self.wcert.itemText(i) for i in range(self.wcert.count()) if self.wcert.itemData(i))))
            return
        lp, pin = self.lib.path(), self.pin.text() or None
        SET.set("pkcs11_path", lp)

        def task(report, cancelled):
            report(30, "Talking to the token...")
            txt, certs = p11_diagnose(lp, pin)
            return {"txt": txt, "certs": certs}

        def done(r):
            self.diag.setPlainText(r["txt"])
            if r["certs"]:
                self.pcert.clear()
                self.pcert.addItem("Automatic - the valid signing certificate on the token", "")
                for text, cid, lbl in r["certs"]:
                    self.pcert.addItem(text, json.dumps([cid, lbl]))
        self.run_task(task, done)

    def pick_box(self):
        try:
            p = self.pdf.require()
        except UserError as e:
            self.warn(str(e))
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Drag a rectangle where the signature should appear")
        dlg.resize(760, 720)
        lay = QVBoxLayout(dlg)
        v = PdfViewer(select_mode=True)
        lay.addWidget(v)
        v.load(p)
        want = {"first": 0, "last": v.doc.page_count - 1}.get(self.where.currentData(), self.page.value() - 1)
        if 0 <= want < v.doc.page_count:
            v.go_to(want)

        def got(pg, rect):
            self.picked = (pg, fitz.Rect(rect))
            self.where.setCurrentIndex(2)
            self.page.setValue(pg + 1)
            self.pos.setCurrentIndex(5)
            dlg.accept()
        v.rectSelected.connect(got)
        dlg.exec_()
        v.close_doc()

    def _plan(self, src, where, pgno, vis, k):
        """(page index, box or None, rotated?) for one file; raises UserError for unusable files."""
        d = open_pdf(src)
        try:
            if d.is_encrypted:
                raise UserError("'%s' is password-protected. Remove the protection first (Password tool), sign, then protect again if needed." % os.path.basename(src))
            n = d.page_count
            idx = {"first": 0, "last": n - 1}.get(where, pgno - 1)
            if idx >= n:
                raise UserError("'%s' has only %d pages." % (os.path.basename(src), n))
            if not vis:
                return idx, None, False
            pg = d[idx]
            picked = None
            if k == 5:
                if not self.picked or self.picked[0] != idx:
                    raise UserError("Use 'Pick on the page...' to draw the box, or choose a preset position.")
                picked = self.picked[1]
            return idx, sign_box_for(fitz.Rect(pg.rect), pg.mediabox, pg.rotation, fitz.Matrix(pg.derotation_matrix), k, picked), bool(pg.rotation)
        finally:
            d.close()

    def make_task(self, out):
        need_hanko()
        files = [self.pdf.require()]
        for f in self.more.paths():
            if f.lower().endswith(".pdf") and f not in files:
                files.append(f)
        mode = self.mode.currentData()
        pin = self.pin.text()
        libp = pfxp = wder = None
        psel = None
        if mode == "p11":
            libp = self.lib.path()
            if not libp or not os.path.isfile(libp):
                raise UserError("Choose the token's PKCS#11 library first (see 'Find automatically').")
            if not pin:
                raise UserError("Enter the token PIN.")
            try:
                import pkcs11  # noqa
            except ImportError:
                raise UserError("USB token support needs the 'python-pkcs11' package.\nRun:  pip install python-pkcs11")
            SET.set("pkcs11_path", libp)
            if self.pcert.currentData():
                psel = json.loads(self.pcert.currentData())
        elif mode == "win":
            wder = self.wcert.currentData()
            if not wder:
                raise UserError("Choose your certificate in the list. Plug in the token and press 'Refresh list' if the list is empty.")
            wder = bytes(wder)
        else:
            pfxp = self.pfx.path()
            if not pfxp or not os.path.isfile(pfxp):
                raise UserError("Choose the .pfx / .p12 certificate file.")
        vis, k = self.visible.isChecked(), self.pos.currentIndex()
        if vis and k == 5 and len(files) > 1:
            raise UserError("A box picked on the page works for one file. For several files choose a preset position (e.g. Bottom right).")
        where, pgno = self.where.currentData(), self.page.value()
        plans = [(f,) + self._plan(f, where, pgno, vis, k) for f in files]
        ts = self.ts.text().strip()
        if ts and not host_allowed(_host_of(ts)):
            raise UserError("The time-stamp server '%s' is not in the allowed list.\nAdd it in Settings > Other allowed servers, or leave the time-stamp empty." % _host_of(ts))
        meta = dict(reason=self.reason.text().strip() or None, location=self.loc.text().strip() or None, contact_info=self.contact.text().strip() or None)
        try:
            hwnd = int(self.window().winId())
        except Exception:
            hwnd = 0

        def task(report, cancelled):
            tzv = os.environ.get("TZ")
            if tzv:                                     # an unusual TZ variable would make pyHanko's time zone look-up fail
                try:
                    import zoneinfo
                    zoneinfo.ZoneInfo(tzv)
                except Exception:
                    os.environ.pop("TZ", None)
            from pyhanko.sign import signers
            report(8, "Opening the certificate...")
            session = None
            raw_fallback = None
            try:
                if mode == "p11":
                    from pyhanko.sign.pkcs11 import PKCS11Signer
                    session = p11_open(libp, pin)
                    found = p11_list_certs(session)
                    if not found:
                        raise UserError("No certificate is stored on this token.")
                    chosen = None
                    if psel:
                        for f in found:
                            if f[1].hex() == psel[0] and f[2] == psel[1]:
                                chosen = f
                    if chosen is None:
                        b = pick_signing_cert([(f[0], f) for f in found])
                        chosen = b[1] if b else found[0]
                    others = [f[3] for f in found if f[3].dump() != chosen[3].dump()]
                    chain = build_cert_chain(chosen[3], others)

                    def mk(raw):
                        kw = dict(signing_cert=chosen[3], ca_chain=chain, use_raw_mechanism=raw)
                        if chosen[1]:
                            kw["key_id"] = chosen[1]
                        else:
                            kw["key_label"] = chosen[2]
                        return PKCS11Signer(session, **kw)
                    signer = mk(False)
                    raw_fallback = lambda: mk(True)                                           # noqa: E731
                elif mode == "win":
                    signer = win_store_signer(wder, pin or None, hwnd)
                else:
                    try:
                        signer = signers.SimpleSigner.load_pkcs12(pfx_file=pfxp, passphrase=(pin.encode("utf-8") if pin else None))
                    except Exception as e:
                        raise UserError("The certificate file could not be opened - wrong password or damaged file. (%s)" % type(e).__name__)
                    if signer is None:
                        raise UserError("The certificate file could not be opened - the password is wrong or the file is damaged.")
                sm = cert_summary(signer.signing_cert) if signer.signing_cert is not None else {"cn": "", "expired": False, "not_after": None}
                if sm["expired"]:
                    raise UserError("This certificate EXPIRED on %s. A signature made with it would not be valid." % sm["not_after"].date())
                who = sm["cn"] or "(certificate)"
                done, lines, rotated = [], [], False
                for n, (src, idx, box, rot) in enumerate(plans):
                    if cancelled():
                        raise Cancelled()
                    report(15 + 75.0 * n / len(plans), "Signing %d of %d..." % (n + 1, len(plans)))
                    dst = unique_path(out, os.path.splitext(os.path.basename(src))[0] + "_signed", ".pdf")
                    try:
                        core_sign_pdf(src, dst, signer, idx, box, meta, ts or None, who)
                    except UserError:
                        raise
                    except Exception as e:
                        if raw_fallback is not None and n == 0:                               # token without a combined hash+sign mechanism
                            LOG.info("token sign failed (%s) - retrying with the raw mechanism", type(e).__name__)
                            signer = raw_fallback()
                            raw_fallback = None
                            try:
                                if os.path.exists(dst):
                                    os.remove(dst)
                            except OSError:
                                pass
                            core_sign_pdf(src, dst, signer, idx, box, meta, ts or None, who)
                        else:
                            raise UserError("Signing '%s' failed: %s" % (os.path.basename(src), (str(e) or type(e).__name__)[:300]))
                    chk = verify_pdf_signatures(dst)
                    done.append(dst)
                    rotated = rotated or rot
                    lines.append("%s\n   check: %s" % (dst, chk[-1] if chk else "NO SIGNATURE FOUND"))
                return {"message": "Signed by: %s\nFiles signed: %d\n\n%s%s" % (who, len(done), "\n".join(lines),
                        "\n\nRotated page: if the box looks misplaced, choose another preset position or 'Pick on the page'." if rotated else ""), "files": done}
            finally:
                try:
                    if session is not None:
                        session.close()
                except Exception:
                    pass
        return task

    def on_success(self, res):
        self.pin.setText("")
        ToolPage.on_success(self, res)

    def _done_fail(self, msg, is_user, cb):
        self.pin.setText("")
        ToolPage._done_fail(self, msg, is_user, cb)


def verify_pdf_signatures(path):
    """List of one-line results, one per signature.  Integrity is checked; trust needs the chain, which is reported separately."""
    need_hanko()
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    for n in ("pyhanko", "pyhanko_certvalidator"):
        logging.getLogger(n).setLevel(logging.CRITICAL)      # keep library chatter out of the console
    res = []
    with open(path, "rb") as f:
        r = PdfFileReader(f, strict=False)
        for sig in r.embedded_signatures:
            try:
                st = validate_pdf_signature(sig)
                who = ""
                try:
                    who = sig.signer_cert.subject.human_friendly
                except Exception:
                    pass
                if st.coverage.name == "ENTIRE_FILE":
                    cov = "covers the whole file"
                elif getattr(getattr(st, "modification_level", None), "name", "") in ("NONE", "LTA_UPDATES", "FORM_FILLING"):
                    cov = "signed part unchanged (only a later signature / form entry was added after it)"
                else:
                    cov = "document was changed after signing"
                res.append("'%s' by %s: %s; %s; certificate trusted by this PC: %s" % (
                    sig.field_name, who or "?", "content intact" if (st.intact and st.valid) else "CONTENT CHANGED OR BROKEN", cov, "yes" if st.trusted else "not verified"))
            except Exception as e:
                res.append("'%s': could not be checked (%s)" % (getattr(sig, "field_name", "?"), str(e)[:100]))
    return res


class DscVerifyTool(ToolPage):
    key, title, group = "dscverify", "Verify Signatures", "Security"
    subtitle = "Check whether a signed PDF was changed after signing and who signed it."
    needs_output = False
    action_text = "Check signatures"

    def build(self, L):
        self.pdf = PdfPicker("dscverify")
        self.add_row("Signed PDF", self.pdf)
        self.res = QTextEdit()
        self.res.setReadOnly(True)
        self.res.setMinimumHeight(140)
        L.addWidget(self.res)
        self.add_hint("'Trusted by this PC' needs the issuing authority's root certificate to be known here; for Indian DSCs it is normally 'not verified' "
                      "in this program even when the signature is perfectly intact. Use Adobe Reader for the full trust check if required.")

    def make_task(self, out):
        p = self.pdf.require()
        need_hanko()

        def task(report, cancelled):
            report(30, "Checking...")
            return {"lines": verify_pdf_signatures(p)}
        return task

    def on_success(self, res):
        self.res.setPlainText("\n\n".join(res["lines"]) if res["lines"] else "This PDF contains no digital signature.")
        self.status.setText("Checked %d signature(s)." % len(res["lines"]))
# ============================================================================
#  SECTION P0 - HOME SCREEN AND BUILT-IN OFFICE SETUP GUIDE
# ============================================================================
TILES = [
    ("merge", "Merge PDFs", "Join many files into one", "#1F4FBF", "M"),
    ("split", "Split PDF", "Cut a file into parts", "#2D6CDF", "S"),
    ("pdfedit", "Edit PDF", "Change text, add images", "#E11D48", "E"),
    ("compress", "Make PDF Smaller", "Shrink for e-mail or portals", "#0E9F6E", "C"),
    ("pdf2word", "PDF to Word", "Get an editable document", "#2B6CB0", "W"),
    ("ocr", "Scanned PDF to Text", "Make scans searchable (OCR)", "#7C3AED", "O"),
    ("redact", "Redact (Hide Data)", "Remove PAN, Aadhaar, names", "#D62839", "R"),
    ("annotate", "Annotate & Forms", "Highlight, notes, fields", "#CA8A04", "N"),
    ("watermark", "Watermark & Stamps", "CONFIDENTIAL, DRAFT, logo", "#D97706", "T"),
    ("bundle", "Bundle Builder", "Index, page numbers, Bates", "#0F2F73", "B"),
    ("dsc", "Sign with DSC", "USB token or .pfx signature", "#B91C2C", "D"),
    ("passport", "Passport Photo", "Photo sheet ready to print", "#0891B2", "P"),
    ("imgcompress", "Image to 200 KB", "Fit portal size limits", "#059669", "K"),
    ("ai_summary", "Summarise (AI)", "Short summary with pages", "#9333EA", "A"),
    ("viewer", "PDF Reader", "Read, search, zoom", "#475569", "V"),
]


def tile_icon(color, letter, size=46):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor(color).lighter(125))
    g.setColorAt(1, QColor(color))
    p.setBrush(QBrush(g))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), 12, 12)
    p.setPen(QColor("white"))
    f = QFont()
    f.setBold(True)
    f.setPixelSize(int(size * 0.5))
    p.setFont(f)
    p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, letter)
    p.end()
    return pm


class Tile(QPushButton):
    def __init__(self, title, desc, color, letter, parent=None):
        QPushButton.__init__(self, parent)
        self.setObjectName("tile")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(84)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 10, 12, 10)
        ic = QLabel()
        ic.setPixmap(tile_icon(color, letter))
        ic.setFixedSize(46, 46)
        v = QVBoxLayout()
        v.setSpacing(1)
        t = QLabel(title)
        t.setObjectName("tileTitle")
        d = QLabel(desc)
        d.setObjectName("hint")
        d.setWordWrap(True)
        v.addStretch(1); v.addWidget(t); v.addWidget(d); v.addStretch(1)
        h.addWidget(ic); h.addLayout(v, 1)
        for w in (ic, t, d):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)


class HomePage(QWidget):
    key, title, group, subtitle, prime_only = "home", "Home", "Home", "Start here", False

    def __init__(self, ctx):
        QWidget.__init__(self)
        self.ctx = ctx
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.NoFrame)
        outer.addWidget(sc)
        body = QWidget()
        body.setObjectName("content")
        sc.setWidget(body)
        L = QVBoxLayout(body)
        L.setContentsMargins(28, 22, 28, 18)
        L.setSpacing(14)
        hero = QFrame()
        hero.setObjectName("hero")
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(26, 22, 26, 22)
        h1 = QLabel("What would you like to do today?")
        h1.setObjectName("heroTitle")
        h2 = QLabel("Type what you need - for example  merge, word, scan, sign, photo - and press Enter. Or pick a tile below.")
        h2.setObjectName("heroSub")
        h2.setWordWrap(True)
        self.search = QLineEdit()
        self.search.setObjectName("heroSearch")
        self.search.setPlaceholderText("Search all tools...")
        self.search.returnPressed.connect(self.go_search)
        hl.addWidget(h1); hl.addWidget(h2); hl.addSpacing(6); hl.addWidget(self.search)
        L.addWidget(hero)
        lab = QLabel("Popular tasks")
        lab.setObjectName("sectionTitle")
        L.addWidget(lab)
        grid = QGridLayout()
        grid.setSpacing(12)
        i = 0
        for key, title, desc, color, letter in TILES:
            if key not in ctx.by_key:
                continue
            t = Tile(title, desc, color, letter)
            t.clicked.connect(lambda _c=False, k=key: ctx.goto(k))
            grid.addWidget(t, i // 3, i % 3)
            i += 1
        for c_ in range(3):
            grid.setColumnStretch(c_, 1)
        L.addLayout(grid)
        rl = QLabel("Recent files")
        rl.setObjectName("sectionTitle")
        L.addWidget(rl)
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 10)
        self.recent = QListWidget()
        self.recent.setMaximumHeight(150)
        self.recent.setFrameShape(QFrame.NoFrame)
        self.recent.itemDoubleClicked.connect(lambda it: ctx.open_in_viewer(it.data(Qt.UserRole)))
        cl.addWidget(self.recent)
        cl.addWidget(hint_label("Double-click to read a file. Tip: you can also drag any PDF onto this window."))
        L.addWidget(card)
        self.safe = QLabel("")
        self.safe.setObjectName("hint")
        self.safe.setWordWrap(True)
        L.addWidget(self.safe)
        L.addStretch(1)

    def go_search(self):
        q = self.search.text().strip().lower()
        if not q:
            return
        words = q.split()
        for t in self.ctx.tools:
            if t.key == "home":
                continue
            hay = (t.title + " " + t.group + " " + t.subtitle).lower()
            if all(w in hay for w in words):
                self.ctx.goto(t.key)
                return
        self.ctx.filter.setText(q)
        self.ctx.statusBar().showMessage("No exact match - the list on the left shows similar tools.", 6000)

    def on_show(self):
        self.recent.clear()
        rec = [p for p in (SET.get("recent") or []) if os.path.isfile(p)][:6]
        if not rec:
            it = QListWidgetItem("(nothing yet - files you open in the reader appear here)")
            it.setFlags(Qt.NoItemFlags)
            self.recent.addItem(it)
        for p in rec:
            it = QListWidgetItem("%s     %s" % (os.path.basename(p), os.path.dirname(p)))
            it.setData(Qt.UserRole, p)
            self.recent.addItem(it)
        self.safe.setText("Your files stay on this computer. Strict Offline Mode is %s. Results are always saved as new files - originals are never changed."
                          % ("ON" if SET.get("offline_mode") else "OFF"))


GUIDE_HTML = """
<h2>Office set-up guide (plain language)</h2>
<p>There are <b>three jobs</b>. Job 1 is done once by the person who looks after computers. Job 2 is done on every staff PC (5 minutes).
Job 3 is only needed if you want the AI features.</p>

<h3>Job 1 - Prepare the program once (IT person, about 30 minutes)</h3>
<ol>
<li>On any one Windows PC, install <b>Python</b> from python.org. Tick <i>"Add python.exe to PATH"</i>.</li>
<li>Create a folder <code>C:\\psp</code>. Put <code>pdf_studio_pro.py</code> in it. Double-click the file once. It installs what it needs (internet needed this one time) and the program opens. Close it.</li>
<li>Open the program, go to <b>Office Deployment Kit</b> (left list, System). Type the AI server address (if you will use AI), tick the options, choose a folder, press <b>Create deployment files</b>.</li>
<li>Double-click <code>build_windows.bat</code>. After a few minutes you get a folder <code>dist\\PDFStudioPro</code> - that is the finished program, no Python needed on staff PCs.</li>
<li>Install the free <b>Inno Setup</b>, open <code>PDFStudioPro.iss</code>, press Compile. You get <code>PDFStudioPro_Setup.exe</code> - the installer for staff.</li>
<li>Put the installer and <code>admin_settings.json</code> in a shared folder, e.g. <code>\\\\server\\software\\PDFStudioPro</code>. Everybody in the office must be able to open that folder.</li>
</ol>

<h3>Job 2 - Give it to staff (each PC, 5 minutes)</h3>
<ol>
<li>Open the shared folder and double-click <code>PDFStudioPro_Setup.exe</code>. Click Next, Next, Finish. A shortcut appears on the desktop.</li>
<li>Right-click any PDF - <b>Open with PDF Studio Pro</b> - it opens in the reader.</li>
<li>For scanned papers (OCR): install the free <b>Tesseract</b> program once (the UB-Mannheim Windows installer) and tick the languages you need (English, Hindi, Marathi, Gujarati ...).</li>
<li>Nothing else to set up. Offline protection is already ON and locked by the settings file, so no file leaves the PC.</li>
</ol>
<p><b>Updates:</b> put the new installer in the shared folder together with a small file <code>version.json</code> like
<code>{"version": "1.1.0", "file": "PDFStudioPro_Setup.exe", "notes": "What is new"}</code>. Staff PCs notice it by themselves and offer to open the folder.</p>

<h3>Job 3 - Switch on AI for chosen staff (optional)</h3>
<ol>
<li><b>Quickest way, one PC:</b> install the free <b>LM Studio</b> on that PC, load a model, start its Local Server. In this program open <b>Settings</b> - <b>AI set-up</b> - <i>AI on THIS computer with LM Studio</i> - <b>Test connection</b> - <b>Save settings</b>. That user is now a Prime user; no key is needed. The steps below are for sharing one AI server with the whole office.</li>
<li>Pick <b>one strong PC</b> to be the AI server (a good graphics card helps). Install <b>LM Studio</b>, download a model, and start its <i>Local Server</i>.</li>
<li>On that same PC open this program, go to <b>AI Gateway (Administrator)</b>. Press <b>Start gateway</b>. Windows may ask about the firewall - allow it for the <b>private network only</b>.</li>
<li>Press <b>Add user</b> for each staff member. Role <b>Prime</b> = can use AI. Role <b>General</b> = no AI. A secret <b>access key</b> appears <b>once</b> - give it to that person privately (WhatsApp/paper). If lost, press <b>New key</b>.</li>
<li>On the staff PC: <b>Settings</b> - AI server address <code>http://SERVER-PC-IP:8800/v1</code> - paste the key - <b>Test connection</b> - <b>Save</b>. The AI tools in the left list stop being dimmed.</li>
<li>To keep the gateway running all the time, leave that PC on, or ask IT to run it as a Windows service (see the top of the program file).</li>
</ol>
<p>People wait in a queue when many press AI at the same time - this is normal. AI answers can be wrong: always check them against the document.</p>

<h3>Digital signature (DSC) on the USB token</h3>
<ol>
<li>Install the token's own driver (from your certificate provider) first. Plug the token in.</li>
<li><b>Digital Signature (DSC)</b> - 'Signing with': choose <b>USB token through Windows</b> and pick your name in the Certificate list (press <b>Refresh list</b> if it is empty). The token's own PIN window opens when you sign.</li>
<li>If your name does not appear there, choose <b>USB token / smart card - PKCS#11 driver file</b> - <b>Find automatically</b> - enter the PIN - <b>Token diagnostics</b>. If your certificate name appears, it is working.</li>
<li>Choose the PDF, choose where the box should appear, press <b>Sign the PDF</b>. A wrong PIN twice can <b>lock the token</b> - stop and call your provider.</li>
</ol>

<h3>If something goes wrong</h3>
<ul>
<li><b>Program will not open:</b> Help - Open log folder - send the newest log file to IT. Logs never contain document text.</li>
<li><b>"Blocked by Strict Offline Mode":</b> the program tried to reach a server that is not allowed. Ask IT to add it in Settings.</li>
<li><b>AI says the server cannot be reached:</b> is the server PC on, LM Studio running, gateway started, firewall open?</li>
<li><b>Hindi/Marathi text looks like boxes in a watermark:</b> put Noto Sans Devanagari font files into the <code>fonts</code> folder next to the program.</li>
<li>Always test on <b>copies</b> of real files first. The program never changes your original, but test once anyway.</li>
</ul>
"""


class GuideTool(ToolPage):
    key, title, group = "guide", "Office Setup Guide", "System"
    subtitle = "Step-by-step instructions to roll this out in your office, in plain language."
    needs_output = False
    no_action = True

    def build(self, L):
        tb = QTextBrowser()
        tb.setOpenExternalLinks(True)
        tb.setHtml(GUIDE_HTML)
        tb.setMinimumHeight(560)
        L.addWidget(tb)
# ============================================================================
#  SECTION P - THEME, ICON, SIDEBAR, MAIN WINDOW, main()
# ============================================================================
GROUPS = ["Home", "Organize", "Convert", "Edit", "Security", "Bundle", "Images", "Automation", "AI", "System"]

ALL_TOOLS = [
    HomePage, ViewerTool, MergeTool, SplitTool, ExtractTool, RearrangeTool, OrganiserTool, PageToolsTool, NumberTool, CompressTool,
    PdfToImageTool, ImageToPdfTool, PdfToWordTool, PdfToExcelTool, PdfToPptTool, PdfToTextTool, ExtractContentTool,
    WatermarkTool, HeaderFooterTool, EditPdfTool, AnnotateTool, PropertiesTool, BookmarksTool, StripTool, PdfaTool, RepairTool, CompareTool,
    OcrTool, ImageOcrTool, CleanupTool, IndicCheckTool,
    PasswordTool, RedactTool, DscSignTool, DscVerifyTool,
    BundleTool,
    ImageEditTool, ImageCompressTool, ExifStripTool, BlurMaskTool, ImageWatermarkTool, PassportTool, QrBarcodeTool, CollageTool, BulkRenameTool,
    BatchTool,
    AiSummaryTool, AiTermsTool, AiAskTool, AiClausesTool, AiClassifyTool, AiTranslateTool, AiExtractTool,
    GuideTool, SettingsTool, DeployTool, GatewayAdminTool,
]


def make_icon():
    ic = QIcon()
    for sz in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(sz, sz)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, sz, sz)
        g.setColorAt(0, QColor(BLUE2))
        g.setColorAt(1, QColor(DARKBLUE))
        p.setBrush(QBrush(g))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(sz * .04, sz * .04, sz * .92, sz * .92), sz * .2, sz * .2)
        pw, ph = sz * .46, sz * .62
        x0, y0 = (sz - pw) / 2, sz * .16
        path = QPainterPath()
        fold = pw * .32
        path.moveTo(x0, y0); path.lineTo(x0 + pw - fold, y0); path.lineTo(x0 + pw, y0 + fold)
        path.lineTo(x0 + pw, y0 + ph); path.lineTo(x0, y0 + ph); path.closeSubpath()
        p.setBrush(QColor("white"))
        p.drawPath(path)
        p.setBrush(QColor(RED))
        tri = QPolygonF([QPointF(x0 + pw - fold, y0), QPointF(x0 + pw, y0 + fold), QPointF(x0 + pw - fold, y0 + fold)])
        p.drawPolygon(tri)
        p.drawRect(QRectF(x0 + pw * .14, y0 + ph * .62, pw * .72, ph * .16))
        p.setBrush(QColor(BLUE))
        for i in range(2):
            p.drawRect(QRectF(x0 + pw * .14, y0 + ph * (.30 + i * .13), pw * (.5 if i else .6), ph * .06))
        p.end()
        ic.addPixmap(pm)
    return ic


def stylesheet(dark=False):
    c = dict(bg="#121A2B", card="#1B2540", text="#E6ECF7", sub="#9FB0CF", border="#2E3B5C", field="#101829", hint="#8FA2C6", sel="#2D6CDF") if dark else \
        dict(bg="#F3F6FC", card="#FFFFFF", text="#1B2430", sub="#5A6B85", border="#D3DDEE", field="#FFFFFF", hint="#6B7B96", sel="#2D6CDF")
    return """
QWidget { font-family: "Segoe UI", "Noto Sans", Arial; font-size: 10pt; color: %(text)s; }
QMainWindow, QWidget#content, QScrollArea { background: %(bg)s; }
QDialog, QMessageBox { background: %(bg)s; }
QLabel#pageTitle { font-size: 21pt; font-weight: 700; color: %(text)s; }
QFrame#accent { background: %(red)s; border-radius: 2px; }
QLabel#subtitle { color: %(sub)s; font-size: 10.5pt; padding-bottom: 4px; }
QFrame#card { background: %(card)s; border: 1px solid %(border)s; border-radius: 10px; }
QLabel#fieldLabel { font-weight: 600; background: transparent; }
QLabel#hint { color: %(hint)s; font-size: 9pt; background: transparent; }
QLabel#status { color: %(blue)s; font-weight: 600; background: transparent; }
QLabel { background: transparent; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit, QTableWidget, QListWidget, QTreeWidget {
    background: %(field)s; border: 1px solid %(border)s; border-radius: 6px; padding: 4px 6px; selection-background-color: %(sel)s; selection-color: white; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus { border: 1px solid %(blue)s; }
QTextEdit#log { font-family: Consolas, "DejaVu Sans Mono", monospace; font-size: 9pt; }
QPushButton { background: %(card)s; border: 1px solid %(border)s; border-radius: 6px; padding: 6px 14px; }
QPushButton:hover { border-color: %(blue)s; }
QPushButton:disabled { color: %(hint)s; }
QPushButton#primary { background: %(red)s; color: white; border: none; font-weight: 700; font-size: 11pt; border-radius: 8px; }
QPushButton#primary:hover { background: %(redh)s; }
QPushButton#primary:disabled { background: #B8BFCC; color: #F0F0F0; }
QPushButton#flat { border: none; background: transparent; color: %(blue)s; }
QProgressBar { border: 1px solid %(border)s; border-radius: 7px; background: %(field)s; text-align: center; height: 16px; }
QProgressBar::chunk { border-radius: 6px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 %(dblue)s, stop:1 %(blue2)s); }
QHeaderView::section { background: %(card)s; border: none; border-bottom: 1px solid %(border)s; padding: 4px; font-weight: 600; }
QTabWidget::pane { border: 1px solid %(border)s; border-radius: 6px; }
QTabBar::tab { padding: 6px 14px; border: 1px solid %(border)s; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; background: %(bg)s; }
QTabBar::tab:selected { background: %(card)s; border-top: 3px solid %(red)s; }
QMenuBar { background: %(card)s; } QMenu { background: %(card)s; border: 1px solid %(border)s; } QMenu::item:selected { background: %(sel)s; color: white; }
QToolTip { background: %(card)s; color: %(text)s; border: 1px solid %(border)s; }
QScrollBar:vertical { width: 12px; background: transparent; } QScrollBar::handle:vertical { background: %(border)s; border-radius: 5px; min-height: 30px; }
QScrollBar:horizontal { height: 12px; background: transparent; } QScrollBar::handle:horizontal { background: %(border)s; border-radius: 5px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QPushButton#tile { background: %(card)s; border: 1px solid %(border)s; border-radius: 12px; text-align: left; padding: 0; }
QPushButton#tile:hover { border: 1px solid %(blue)s; background: %(bg)s; }
QLabel#tileTitle { font-size: 11pt; font-weight: 700; background: transparent; }
QLabel#sectionTitle { font-size: 13pt; font-weight: 700; padding-top: 4px; }
QFrame#hero { border-radius: 16px; background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 %(dblue)s, stop:1 %(blue2)s); }
QLabel#heroTitle { color: white; font-size: 22pt; font-weight: 800; background: transparent; }
QLabel#heroSub { color: #DCE6FF; font-size: 10.5pt; background: transparent; }
QLineEdit#heroSearch { background: white; color: #1B2430; border: none; border-radius: 10px; padding: 10px 14px; font-size: 12pt; }
QFrame#sidebar { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 %(dblue)s, stop:1 %(blue)s); }
QFrame#sidebar QLabel { color: white; }
QLabel#brand { font-size: 15pt; font-weight: 800; color: white; }
QLabel#role { color: #DCE6FF; font-size: 9pt; }
QFrame#stripe { background: %(red)s; }
QLineEdit#filter { background: rgba(255,255,255,0.14); color: white; border: 1px solid rgba(255,255,255,0.25); }
QListWidget#nav { background: transparent; border: none; outline: 0; color: white; }
QListWidget#nav::item { padding: 6px 10px 6px 16px; border-left: 4px solid transparent; color: #E6EEFF; }
QListWidget#nav::item:hover { background: rgba(255,255,255,0.10); }
QListWidget#nav::item:selected { background: rgba(255,255,255,0.20); border-left: 4px solid %(red)s; color: white; font-weight: 600; }
""" % dict(c, red=RED, redh=REDH, blue=BLUE, blue2=BLUE2, dblue=DARKBLUE)


def apply_theme(app, dark):
    app.setStyle("Fusion")
    pal = QPalette()
    if dark:
        pal.setColor(QPalette.Window, QColor("#121A2B")); pal.setColor(QPalette.WindowText, QColor("#E6ECF7"))
        pal.setColor(QPalette.Base, QColor("#101829")); pal.setColor(QPalette.Text, QColor("#E6ECF7"))
        pal.setColor(QPalette.Button, QColor("#1B2540")); pal.setColor(QPalette.ButtonText, QColor("#E6ECF7"))
    else:
        pal.setColor(QPalette.Window, QColor("#F3F6FC")); pal.setColor(QPalette.WindowText, QColor("#1B2430"))
        pal.setColor(QPalette.Base, QColor("#FFFFFF")); pal.setColor(QPalette.Text, QColor("#1B2430"))
        pal.setColor(QPalette.Button, QColor("#FFFFFF")); pal.setColor(QPalette.ButtonText, QColor("#1B2430"))
    pal.setColor(QPalette.Highlight, QColor(BLUE2)); pal.setColor(QPalette.HighlightedText, QColor("white"))
    app.setPalette(pal)
    app.setStyleSheet(stylesheet(dark))


class MainWindow(QMainWindow):
    def __init__(self, start_file=None):
        QMainWindow.__init__(self)
        self.setWindowTitle("%s %s" % (APP_NAME, APP_VERSION))
        self.setWindowIcon(make_icon())
        self.setMinimumSize(940, 640)
        self.resize(1200, 780)
        self.setAcceptDrops(True)
        self.ai = AIClient()
        self.pages, self.busy = {}, set()
        hidden = set(SET.get("disabled_tools") or [])
        self.tools = [t for t in ALL_TOOLS if t.key not in hidden]
        self.by_key = {t.key: t for t in self.tools}
        # ----- sidebar
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(262)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 14, 0, 0)
        sl.setSpacing(6)
        brand = QLabel("  PDF Studio Pro")
        brand.setObjectName("brand")
        sl.addWidget(brand)
        self.filter = QLineEdit()
        self.filter.setObjectName("filter")
        self.filter.setPlaceholderText("Search tools...  (Ctrl+K)")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self.apply_filter)
        fw = QHBoxLayout(); fw.setContentsMargins(10, 0, 10, 0); fw.addWidget(self.filter)
        sl.addLayout(fw)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setTextElideMode(Qt.ElideRight)
        self.nav.currentItemChanged.connect(self.on_nav)
        sl.addWidget(self.nav, 1)
        self.role_lbl = QLabel("")
        self.role_lbl.setObjectName("role")
        self.role_lbl.setWordWrap(True)
        self.role_lbl.setContentsMargins(14, 4, 10, 8)
        sl.addWidget(self.role_lbl)
        stripe = QFrame()
        stripe.setObjectName("stripe")
        stripe.setFixedHeight(6)
        sl.addWidget(stripe)
        self.stack = QStackedWidget()
        central = QWidget()
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(side)
        h.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.build_nav()
        self.build_menu()
        for seq, fn in (("Ctrl+K", lambda: (self.filter.setFocus(), self.filter.selectAll())), ("Esc", self.cancel_current)):
            QShortcut(QKeySequence(seq), self, activated=fn)
        self.settings_changed(first=True)
        self.goto("home")
        if start_file:
            QTimer.singleShot(200, lambda: self.open_in_viewer(start_file))
        if SET.get("update_path"):
            QTimer.singleShot(2500, lambda: self.check_updates(False))

    # ---- context API used by pages
    @property
    def is_prime(self):
        return self.ai.is_prime()

    def set_busy(self, page, busy):
        (self.busy.add if busy else self.busy.discard)(page)
        self.statusBar().showMessage("Working...  (press Esc to cancel)" if self.busy else "Ready.")

    def goto(self, key):
        for i in range(self.nav.count()):
            it = self.nav.item(i)
            if it.data(Qt.UserRole) == key:
                self.nav.setCurrentItem(it)
                return

    def open_in_viewer(self, path):
        if "viewer" not in self.by_key:
            return
        self.goto("viewer")
        pg = self.page_for("viewer")
        if hasattr(pg, "open_file") and os.path.isfile(path):
            pg.open_file(path)

    def check_updates(self, manual=False):
        st, info = check_update()
        if st == "new":
            if QMessageBox.question(self, APP_NAME, info + "\n\nOpen the update folder now?") == QMessageBox.Yes:
                open_folder(SET.get("update_path"))
        elif manual:
            QMessageBox.information(self, APP_NAME, info)

    def settings_changed(self, first=False):
        app = QApplication.instance()
        apply_theme(app, SET.get("theme") == "dark")
        self.refresh_role_label()
        self.build_nav(keep=True)
        if not first and not self.ai.direct and self.ai.key:
            w = Worker(lambda rep, can: self.ai.refresh_role(), self)
            w.succeeded.connect(lambda r: (self.refresh_role_label(), self.build_nav(keep=True)))
            w.failed.connect(lambda m, u: self.statusBar().showMessage("AI server: " + m.split("\n")[0], 8000))
            self._rw = w
            w.start()
        elif first and self.ai.key and not self.ai.direct:
            w = Worker(lambda rep, can: self.ai.refresh_role(), self)
            w.succeeded.connect(lambda r: (self.refresh_role_label(), self.build_nav(keep=True)))
            w.failed.connect(lambda m, u: None)
            self._rw = w
            w.start()

    def refresh_role_label(self):
        if self.ai.direct:
            t = "PRIME user - AI: %s" % self.ai.host_label()
        elif self.ai.role == "prime":
            t = "PRIME user: %s" % (self.ai.user or "")
        elif self.ai.key:
            t = "General user (key not verified)"
        else:
            t = "General user"
        self.role_lbl.setText(t + ("\nOffline mode ON" if SET.get("offline_mode") else "\nOffline mode OFF"))

    # ---- navigation
    def build_nav(self, keep=False):
        cur = None
        if keep and self.nav.currentItem():
            cur = self.nav.currentItem().data(Qt.UserRole)
        self.nav.blockSignals(True)
        self.nav.clear()
        for g in GROUPS + sorted({t.group for t in self.tools} - set(GROUPS)):
            ts = [t for t in self.tools if t.group == g]
            if not ts:
                continue
            hd = QListWidgetItem(g.upper())
            hd.setFlags(Qt.NoItemFlags)
            f = hd.font(); f.setBold(True); f.setPointSize(8)
            hd.setFont(f)
            hd.setForeground(QColor("#9FB8F0"))
            hd.setData(Qt.UserRole + 1, "group")
            self.nav.addItem(hd)
            for t in ts:
                locked = t.prime_only and not self.is_prime
                it = QListWidgetItem(t.title)
                if locked:                                   # dimmed = needs a Prime key
                    it.setForeground(QColor("#8FA6D6"))
                    it.setToolTip("AI tool - not switched on yet. Open Settings and choose an 'AI set-up'.")
                it.setData(Qt.UserRole, t.key)
                it.setData(Qt.UserRole + 2, (t.title + " " + t.group + " " + t.subtitle).lower())
                self.nav.addItem(it)
        self.nav.blockSignals(False)
        self.apply_filter(self.filter.text())
        if cur:
            self.goto(cur)

    def apply_filter(self, text):
        q = text.strip().lower()
        group_item, any_vis = None, False
        for i in range(self.nav.count()):
            it = self.nav.item(i)
            if it.data(Qt.UserRole + 1) == "group":
                if group_item is not None:
                    group_item.setHidden(not any_vis)
                group_item, any_vis = it, False
            else:
                vis = (not q) or all(w in it.data(Qt.UserRole + 2) for w in q.split())
                it.setHidden(not vis)
                any_vis = any_vis or vis
        if group_item is not None:
            group_item.setHidden(not any_vis)

    def page_for(self, key):
        if key in self.pages:
            return self.pages[key]
        cls = self.by_key[key]
        try:
            pg = cls(self)
        except Exception as e:
            log_exc("create page %s" % key)
            pg = QLabel("This tool could not be opened:\n%s: %s\n\n(Details are in the log file: Help > Open log folder.)" % (type(e).__name__, e))
            pg.setAlignment(Qt.AlignCenter)
            pg.setWordWrap(True)
        self.pages[key] = pg
        self.stack.addWidget(pg)
        return pg

    def on_nav(self, cur, prev):
        if cur is None:
            return
        key = cur.data(Qt.UserRole)
        if not key:
            return
        pg = self.page_for(key)
        self.stack.setCurrentWidget(pg)
        if hasattr(pg, "on_show"):
            try:
                pg.on_show()
            except Exception:
                log_exc("on_show %s" % key)

    def cancel_current(self):
        pg = self.stack.currentWidget()
        if pg in self.busy and hasattr(pg, "on_cancel"):
            pg.on_cancel()

    # ---- menus
    def build_menu(self):
        mb = self.menuBar()
        fm = mb.addMenu("&File")
        a = fm.addAction("Open PDF in reader...")
        a.setShortcut("Ctrl+O")
        a.triggered.connect(self.open_dialog)
        self.recent_menu = fm.addMenu("Recent files")
        self.recent_menu.aboutToShow.connect(self.fill_recent)
        fm.addSeparator()
        q = fm.addAction("Exit")
        q.setShortcut("Ctrl+Q")
        q.triggered.connect(self.close)
        tm = mb.addMenu("&Settings")
        s = tm.addAction("Settings...")
        s.setShortcut("Ctrl+,")
        s.triggered.connect(lambda: self.goto("settings"))
        tm.addAction("Light / dark appearance").triggered.connect(self.toggle_theme)
        hm = mb.addMenu("&Help")
        hm.addAction("Keyboard shortcuts").triggered.connect(lambda: show_shortcuts(self))
        hm.addAction("Open log folder").triggered.connect(lambda: (os.makedirs(LOG_DIR, exist_ok=True), open_folder(LOG_DIR)))
        hm.addAction("Check for updates").triggered.connect(lambda: self.check_updates(True))
        hm.addSeparator()
        hm.addAction("About").triggered.connect(lambda: show_about(self))
        QShortcut(QKeySequence("F1"), self, activated=lambda: show_shortcuts(self))

    def toggle_theme(self):
        SET.set("theme", "light" if SET.get("theme") == "dark" else "dark")
        apply_theme(QApplication.instance(), SET.get("theme") == "dark")

    def open_dialog(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open PDF", SET.last_dir("open_main"), "PDF files (*.pdf)")
        if p:
            self.open_in_viewer(p)

    def fill_recent(self):
        self.recent_menu.clear()
        rec = [p for p in SET.get("recent") or [] if os.path.isfile(p)]
        if not rec:
            self.recent_menu.addAction("(none)").setEnabled(False)
        for p in rec:
            self.recent_menu.addAction(os.path.basename(p)).triggered.connect(lambda _c=False, p=p: self.open_in_viewer(p))

    # ---- drag & drop a PDF anywhere to read it
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            if u.isLocalFile() and u.toLocalFile().lower().endswith(".pdf"):
                self.open_in_viewer(u.toLocalFile())
                break

    def closeEvent(self, e):
        for _pg in self.pages.values():
            _s = getattr(_pg, "sess", None)
            if getattr(_pg, "key", "") == "pdfedit" and _s is not None and _s.dirty:
                if QMessageBox.question(self, APP_NAME, "Edit PDF has changes that are not saved yet.\nClose without saving?") != QMessageBox.Yes:
                    e.ignore()
                    return
                break
        if self.busy and QMessageBox.question(self, APP_NAME, "A job is still running. Stop it and exit?") != QMessageBox.Yes:
            e.ignore()
            return
        for pg in list(self.busy):
            try:
                pg.worker.cancel()
                pg.worker.wait(3000)
            except Exception:
                pass
        for pg in self.pages.values():
            srv = getattr(pg, "srv", None)
            if srv:
                try:
                    srv.stop()
                except Exception:
                    pass
        SET.save()
        e.accept()


_WINDOW = None


def _excepthook(tp, val, tb):
    LOG.error("UNCAUGHT\n%s", "".join(traceback.format_exception(tp, val, tb)))
    try:
        QMessageBox.critical(None, APP_NAME, "Something unexpected went wrong: %s: %s\n\nDetails were saved in the log file (Help > Open log folder). "
                             "Your original files were not changed." % (tp.__name__, str(val)[:300]))
    except Exception:
        pass


def main():
    global _WINDOW
    multiprocessing.freeze_support()
    for _n in ("stdout", "stderr"):          # windowed exe has no console: give print() somewhere harmless to go
        if getattr(sys, _n) is None:
            setattr(sys, _n, open(os.devnull, "w"))
    files = [a for a in sys.argv[1:] if not a.startswith("-") and os.path.isfile(a) and a.lower().endswith(".pdf")]
    if QApplication.instance() is None:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    install_offline_guard()
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(make_icon())
    sys.excepthook = _excepthook
    _WINDOW = MainWindow(files[0] if files else None)
    _WINDOW.show()
    _WINDOW.raise_()
    app.exec_()                      # no sys.exit() - so it also runs from IDLE (F5)


if __name__ == "__main__":
    main()
