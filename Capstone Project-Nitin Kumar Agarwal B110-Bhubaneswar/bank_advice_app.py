#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BANK ADVICE -> SAP UPLOADER   (window / GUI version)
====================================================
Double-click  Run_Bank_Advice.bat   (or run:  python bank_advice_app.py)

A page opens in your browser (it runs only on your own computer, nothing is sent anywhere):
    1. drop / choose the Bank Advice file(s)   (.html / .pdf)
    2. drop / choose the Bank Statement        (.xlsx / .csv)
    3. press  "Preview"  (changes nothing)  or  "Process & Update Excel"
    4. download the Excel uploader for SAP

All rules (amount check, duplicate check, Posted / Not Posted folders) live in
bank_advice_processor.py - keep both files in the same folder.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import traceback
import webbrowser
import datetime as dt
from email.parser import BytesParser
from email.policy import HTTP
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))
import bank_advice_processor as eng          # noqa: E402  (the engine)
import openpyxl                              # noqa: E402

APP_VERSION = "v3 - 26 Nov 2026 (Statements folder + Uploader-Posted fix)"
SETTINGS_FILE = APP_DIR / "bank_advice_app_settings.json"
MAX_UPLOAD = 200 * 1024 * 1024
LOCK = threading.Lock()                      # one run at a time
RUNS = {}                                    # run_id -> (filename, bytes)
STATE = {"work_dir": eng.DEFAULT_INPUT, "out_dir": eng.DEFAULT_OUTPUT,
         "out_path": None, "posted_path": None}


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def load_settings(args):
    cfg = {}
    try:
        cfg = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    STATE["work_dir"] = args.work_dir or cfg.get("work_dir") or eng.DEFAULT_INPUT
    STATE["out_dir"] = args.out_dir or cfg.get("out_dir") or eng.DEFAULT_OUTPUT


def save_settings():
    try:
        SETTINGS_FILE.write_text(json.dumps({"work_dir": STATE["work_dir"], "out_dir": STATE["out_dir"]},
                                            indent=2), encoding="utf-8")
    except Exception:
        pass


def safe_name(name):
    name = Path(str(name).replace("\\", "/")).name.strip()
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name)
    return name or "upload"


def unique_path(folder, name):
    dest = folder / name
    if dest.exists():
        p = Path(name)
        dest = folder / f"{p.stem}_{dt.datetime.now():%Y%m%d_%H%M%S}{p.suffix}"
    return dest


def parse_multipart(content_type, body):
    """-> (fields{name:str}, files[(field, filename, bytes)])   (stdlib only, no cgi)"""
    raw = b"Content-Type: " + content_type.encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    msg = BytesParser(policy=HTTP).parsebytes(raw)
    fields, files = {}, []
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        fname = part.get_filename()
        data = part.get_payload(decode=True) or b""
        if fname is not None:
            if fname:
                files.append((name, fname, data))
        else:
            fields[name] = data.decode("utf-8", "replace")
    return fields, files


def open_in_os(path):
    path = str(path)
    if sys.platform.startswith("win"):
        os.startfile(path)                                   # noqa: S606 (local, user-initiated)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def run_rows_workbook(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bank Uploader"
    ws.append(eng.HEADERS)
    for r in rows:
        ws.append(r)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# --------------------------------------------------------------------------------------
# the actual work
# --------------------------------------------------------------------------------------
def originals_index(work_dir):
    """sha1 -> path of advice files already waiting in <work>\\Statements or <work> root."""
    idx = {}
    for d in (Path(work_dir) / eng.INBOX_FOLDER, Path(work_dir)):
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if f.is_file() and f.suffix.lower() in eng.ADVICE_EXT and not f.name.startswith("~$"):
                    try:
                        idx.setdefault(hashlib.sha1(f.read_bytes()).hexdigest(), f)
                    except OSError:
                        pass
    return idx


def finish(out, dry, work_dir, out_dir, log):
    run_id = None
    if not dry:
        STATE.update(work_dir=str(work_dir), out_dir=str(out_dir),
                     out_path=str(out["out_path"]), posted_path=str(out["posted_uploader_path"]))
        save_settings()
        if out["posted_rows"]:
            run_id = dt.datetime.now().strftime("%Y%m%d%H%M%S")
            RUNS[run_id] = (f"Bank Uploader - new rows {dt.datetime.now():%Y-%m-%d %H%M}.xlsx",
                            run_rows_workbook(out["posted_rows"]))
            for k in list(RUNS)[:-10]:
                RUNS.pop(k, None)
    return 200, {
        "ok": True, "dry_run": dry, "results": out["results"], "counts": out["counts"],
        "warnings": out["warnings"], "log": log, "run_id": run_id,
        "rows_added": 0 if dry else len(out["posted_rows"]),
        "bills_posted": out["counts"].get("POSTED", 0),
        "would_add": len(out["posted_rows"]) if dry else None,
        "uploader_file": Path(out["out_path"]).name,
        "downloads": {
            "uploader": (not dry) and Path(out["out_path"]).exists(),
            "posted": (not dry) and Path(out["posted_uploader_path"]).exists(),
            "run_rows": run_id,
        },
    }


def process_folder(work_dir, out_dir, uploaded_statements, dry):
    """Process every advice waiting in <work>\\Statements (and <work> root) IN PLACE:
    the original files are moved to Posted / Not Posted."""
    advices, statements = eng.collect_folder_files(work_dir)
    tmp = None
    log = []
    try:
        if uploaded_statements:                       # a statement chosen on the page wins
            tmp = Path(tempfile.mkdtemp(prefix="bankadvice_"))
            statements = []
            for name, data in uploaded_statements:
                q = tmp / safe_name(name)
                q.write_bytes(data)
                statements.append(q)
        if not advices:
            return 400, {"error": f"No bank advice files found in '{Path(work_dir) / eng.INBOX_FOLDER}'."}
        if not statements:
            return 400, {"error": "No bank statement found in the Bank advice folder - add it on the page "
                                  "(box 2) or save it in that folder."}
        out = eng.run_pipeline(advices, statements, work_dir, out_dir, dry_run=dry, say=log.append)
    except eng.ProcessingError as e:
        return 400, {"error": str(e), "log": log}
    except PermissionError as e:
        locked = Path(getattr(e, "filename", "") or "").name or "a file"
        return 400, {"error": f"'{locked}' is open in Excel (or locked by OneDrive sync). "
                              f"Please close it and press the button again. Nothing was changed.", "log": log}
    except Exception as e:
        traceback.print_exc()
        return 500, {"error": f"Unexpected error: {e}", "log": log}
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return finish(out, dry, work_dir, out_dir, log)


def process(fields, files, dry):
    work_dir = Path((fields.get("work_dir") or STATE["work_dir"]).strip()).expanduser()
    out_dir = Path((fields.get("out_dir") or STATE["out_dir"]).strip()).expanduser()
    folder_mode = fields.get("mode") == "folder"
    advices = [(n, d) for f, n, d in files if f == "advices"]
    statements = [(n, d) for f, n, d in files if f == "statements"]
    if folder_mode:
        return process_folder(work_dir, out_dir, statements, dry)
    if not advices:
        return 400, {"error": "Please upload at least one bank advice file."}
    if not statements:
        return 400, {"error": "Please upload the bank statement."}

    tmp = Path(tempfile.mkdtemp(prefix="bankadvice_")) if dry else None
    adv_dir = (tmp / "advices") if dry else work_dir
    stm_dir = (tmp / "statements") if dry else (work_dir / eng.STATEMENT_ARCHIVE_FOLDER)
    saved_adv, saved_new_stm, adv_paths, stm_paths = {}, [], [], []
    log = []
    try:
        for d in (adv_dir, stm_dir):
            d.mkdir(parents=True, exist_ok=True)
        originals = originals_index(work_dir)
        for name, data in advices:
            orig = originals.get(hashlib.sha1(data).hexdigest())
            if orig is not None and orig not in adv_paths:
                adv_paths.append(orig)           # same file already in Statements / Bank advice -> move the ORIGINAL
                continue
            p = unique_path(adv_dir, safe_name(name))
            p.write_bytes(data)
            saved_adv[p.name] = p
            adv_paths.append(p)
        for name, data in statements:
            digest = hashlib.sha1(data).hexdigest()
            same = next((q for q in stm_dir.glob("*") if q.is_file() and q.stat().st_size == len(data)
                         and hashlib.sha1(q.read_bytes()).hexdigest() == digest), None)
            if same is None:
                same = unique_path(stm_dir, safe_name(name))
                same.write_bytes(data)
                saved_new_stm.append(same)
            stm_paths.append(same)

        out = eng.run_pipeline(adv_paths, stm_paths, work_dir, out_dir, dry_run=dry, say=log.append)
    except eng.ProcessingError as e:
        if not dry:                                   # leave folders exactly as they were
            for p in list(saved_adv.values()) + saved_new_stm:
                p.unlink(missing_ok=True)
        return 400, {"error": str(e), "log": log}
    except PermissionError as e:                      # a file is open in Excel / locked by OneDrive
        if not dry:
            for p in list(saved_adv.values()) + saved_new_stm:
                p.unlink(missing_ok=True)
        locked = Path(getattr(e, "filename", "") or "").name or "a file"
        return 400, {"error": f"'{locked}' is open in Excel (or locked by OneDrive sync). "
                              f"Please close it and press the button again. Nothing was changed.", "log": log}
    except Exception as e:                            # unexpected
        if not dry:
            for p in list(saved_adv.values()) + saved_new_stm:
                p.unlink(missing_ok=True)
        traceback.print_exc()
        return 500, {"error": f"Unexpected error: {e}", "log": log}
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    if not dry:
        for r in out["results"]:                      # unrecognised uploads are not kept
            if r["status"] == "SKIPPED" and r["advice"] in saved_adv:
                saved_adv[r["advice"]].unlink(missing_ok=True)
    return finish(out, dry, work_dir, out_dir, log)


# --------------------------------------------------------------------------------------
# web server
# --------------------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "BankAdviceApp/1.0"

    def log_message(self, fmt, *args):      # keep the console quiet
        pass

    # ---- plumbing
    def _local_only(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        origin = self.headers.get("Origin")
        ok = host in ("127.0.0.1", "localhost")
        if origin:
            ok = ok and urlparse(origin).hostname in ("127.0.0.1", "localhost")
        if not ok:
            self._send(403, b"Forbidden", "text/plain")
        return ok

    def _send(self, code, body, ctype, extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj), "application/json; charset=utf-8")

    def _file(self, name, data):
        self._send(200, data,
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                   {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"})

    # ---- routes
    def do_GET(self):
        if not self._local_only():
            return
        u = urlparse(self.path)
        if u.path == "/":
            return self._send(200, PAGE.replace("__VER__", APP_VERSION), "text/html; charset=utf-8")
        if u.path == "/api/config":
            adv, stm = eng.collect_folder_files(STATE["work_dir"])
            return self._json(200, {"work_dir": STATE["work_dir"], "out_dir": STATE["out_dir"],
                                    "inbox": str(Path(STATE["work_dir"]) / eng.INBOX_FOLDER),
                                    "inbox_advices": [a.name for a in adv],
                                    "inbox_statements": [x.name for x in stm]})
        if u.path == "/download/uploader":
            p = Path(STATE["out_path"] or "")
            if p.is_file():
                return self._file(p.name, p.read_bytes())
            return self._send(404, b"No uploader yet - process something first.", "text/plain")
        if u.path == "/download/posted":
            p = Path(STATE["posted_path"] or "")
            if p.is_file():
                return self._file(p.name, p.read_bytes())
            return self._send(404, b"No Uploader-Posted file yet.", "text/plain")
        if u.path == "/download/run":
            rid = (parse_qs(u.query).get("id") or [""])[0]
            if rid in RUNS:
                return self._file(*RUNS[rid])
            return self._send(404, b"Run not found.", "text/plain")
        self._send(404, b"Not found", "text/plain")

    def do_POST(self):
        if not self._local_only():
            return
        u = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_UPLOAD:
            return self._json(413, {"error": "Upload too large."})
        body = self.rfile.read(length)
        if u.path == "/api/process":
            dry = (parse_qs(u.query).get("dry") or ["0"])[0] == "1"
            try:
                fields, files = parse_multipart(self.headers.get("Content-Type", ""), body)
            except Exception as e:
                return self._json(400, {"error": f"Could not read the upload: {e}"})
            if not LOCK.acquire(blocking=False):
                return self._json(409, {"error": "Another run is in progress - please wait."})
            try:
                code, payload = process(fields, files, dry)
            finally:
                LOCK.release()
            return self._json(code, payload)
        if u.path == "/api/open":
            try:
                what = json.loads(body or b"{}").get("what")
                work, out = Path(STATE["work_dir"]), Path(STATE["out_dir"])
                target = {"output": out, "work": work, "posted": work / eng.POSTED_FOLDER,
                          "notposted": work / eng.NOT_POSTED_FOLDER}[what]
                target.mkdir(parents=True, exist_ok=True)
                open_in_os(target)
                return self._json(200, {"ok": True})
            except Exception as e:
                return self._json(400, {"error": str(e)})
        if u.path == "/api/quit":
            self._json(200, {"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        self._send(404, b"Not found", "text/plain")


def find_port(start):
    for port in range(start, start + 30):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit("No free port found.")


def main():
    ap = argparse.ArgumentParser(description="Bank advice -> SAP uploader (browser window)")
    ap.add_argument("--work-dir", help="working folder (Posted / Not Posted folders are created here)")
    ap.add_argument("--out-dir", help="folder holding Bank Uploader.xlsx, register and log")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    load_settings(args)
    port = find_port(args.port)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print("=" * 66)
    print("  Bank Advice -> SAP Uploader is running   (" + APP_VERSION + ")")
    print(f"  Open:  {url}")
    print("  Keep this window open while you work. Close it (or press Ctrl+C) to stop.")
    print("=" * 66)
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    print("Stopped.")


# --------------------------------------------------------------------------------------
# the page
# --------------------------------------------------------------------------------------
PAGE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bank Advice to SAP Uploader</title>
<style>
:root{--bg:#f5f6f8;--card:#fff;--ink:#1c2530;--mute:#5d6b7a;--line:#dde2e8;--acc:#1a5fb4;--acc2:#154a8c;
--ok:#1b7a3d;--okbg:#e6f4ea;--warn:#8a5a00;--warnbg:#fff4d6;--bad:#b3261e;--badbg:#fdeceb}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 "Segoe UI",system-ui,Arial,sans-serif}
header{background:#14263d;color:#fff;padding:18px 28px}header h1{margin:0;font-size:20px;font-weight:600}
header p{margin:4px 0 0;color:#b9c7d8;font-size:13px}
main{max-width:1040px;margin:22px auto;padding:0 18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin-bottom:16px}
.card h2{margin:0 0 4px;font-size:16px}.hint{color:var(--mute);font-size:13px;margin:0 0 12px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:820px){.grid{grid-template-columns:1fr}}
.drop{border:2px dashed #b7c2cf;border-radius:10px;padding:22px 12px;text-align:center;cursor:pointer;background:#fafbfc;transition:.15s}
.drop:hover,.drop.over{border-color:var(--acc);background:#eef4fc}
.drop b{display:block;font-size:15px}.drop span{color:var(--mute);font-size:13px}
.files{list-style:none;margin:10px 0 0;padding:0;font-size:13.5px}
.files li{display:flex;justify-content:space-between;align-items:center;padding:5px 8px;border:1px solid var(--line);border-radius:6px;margin-top:6px;background:#fff}
.files li button{border:0;background:none;color:var(--bad);cursor:pointer;font-size:16px;line-height:1}
.files .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:88%}
details summary{cursor:pointer;color:var(--acc);font-size:13.5px}
label{display:block;font-size:13px;color:var(--mute);margin:10px 0 3px}
input[type=text]{width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:6px;font:inherit}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
button.btn{padding:10px 18px;border-radius:8px;border:1px solid var(--acc);background:#fff;color:var(--acc);font:inherit;font-weight:600;cursor:pointer}
button.btn:hover{background:#eef4fc}button.btn.primary{background:var(--acc);color:#fff}button.btn.primary:hover{background:var(--acc2)}
button.btn:disabled{opacity:.5;cursor:not-allowed}
.chips{display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 14px}
.chip{padding:8px 14px;border-radius:8px;font-weight:600;font-size:14px}
.c-ok{background:var(--okbg);color:var(--ok)}.c-warn{background:var(--warnbg);color:var(--warn)}.c-bad{background:var(--badbg);color:var(--bad)}
table{width:100%;border-collapse:collapse;font-size:13.5px}th{text-align:left;background:#f0f3f6;padding:8px 10px;border-bottom:1px solid var(--line)}
td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}td.num{text-align:right;white-space:nowrap}
.badge{display:inline-block;padding:2px 9px;border-radius:12px;font-weight:600;font-size:12px;white-space:nowrap}
.b-POSTED{background:var(--okbg);color:var(--ok)}.b-ALREADY{background:var(--warnbg);color:var(--warn)}
.b-NOT{background:var(--badbg);color:var(--bad)}.b-SKIPPED{background:#eceff3;color:var(--mute)}
.note{color:var(--mute);font-size:12.5px;max-width:420px}
.msg{padding:10px 14px;border-radius:8px;margin-bottom:12px;font-size:14px}.msg.err{background:var(--badbg);color:var(--bad)}.msg.warn{background:var(--warnbg);color:var(--warn)}.msg.info{background:#e8f0fb;color:var(--acc2)}
pre{background:#101820;color:#d6e2ee;padding:12px;border-radius:8px;overflow:auto;font-size:12px;max-height:240px}
.spin{display:none;width:18px;height:18px;border:3px solid #cfd8e3;border-top-color:var(--acc);border-radius:50%;animation:s 0.8s linear infinite}
@keyframes s{to{transform:rotate(360deg)}}.hide{display:none}
footer{text-align:center;color:var(--mute);font-size:12px;margin:22px 0}
</style></head><body>
<header><h1>Bank Advice &rarr; SAP Uploader</h1>
<p>Upload the bank advice(s) and the bank statement &middot; amounts are verified &middot; duplicates are blocked &middot; get the Excel for SAP</p></header>
<main>
<div class="card" id="inboxCard"><h2>Option A &mdash; process the files waiting in the Statements folder</h2>
 <p class="hint" id="inboxPath">Save new bank advices in the Statements folder. They are processed in place and MOVED to Posted / Not Posted.</p>
 <ul class="files" id="inboxList"></ul>
 <div class="row" style="margin-top:12px">
  <button class="btn" id="fPrev">Preview folder</button>
  <button class="btn primary" id="fGo">Process Statements folder</button>
  <button class="btn" id="fRef">Refresh list</button></div></div>
<p class="hint" style="margin:4px 4px 10px">Option B &mdash; or choose / drop files below. If a chosen advice is also in the Statements folder, that original is moved too.</p>
<div class="grid">
 <div class="card"><h2>1. Bank advice(s)</h2><p class="hint">&ldquo;Foreign Export Bill Transaction Tax Invoice&rdquo; &mdash; .html or .pdf (you can add many)</p>
  <div class="drop" id="dz1"><b>Drop advice files here</b><span>or click to choose</span></div>
  <input type="file" id="in1" multiple accept=".html,.htm,.pdf" class="hide"><ul class="files" id="l1"></ul></div>
 <div class="card"><h2>2. Bank statement</h2><p class="hint">ICICI statement &mdash; .xlsx / .csv with Description and Withdrawal columns</p>
  <div class="drop" id="dz2"><b>Drop bank statement here</b><span>or click to choose</span></div>
  <input type="file" id="in2" multiple accept=".xlsx,.xlsm,.csv" class="hide"><ul class="files" id="l2"></ul></div>
</div>
<div class="card"><details><summary>Folders (already set &mdash; change only if needed)</summary>
 <label for="work">Working folder &mdash; &ldquo;Posted&rdquo; and &ldquo;Not Posted&rdquo; sub-folders are kept here</label><input type="text" id="work">
 <label for="out">Output folder &mdash; Bank Uploader.xlsx, Processed_Register.csv and Processing_Log.csv are kept here</label><input type="text" id="out"></details></div>
<div class="card"><div class="row">
 <button class="btn" id="bPrev">Preview (changes nothing)</button>
 <button class="btn primary" id="bGo">Process &amp; Update Excel</button><div class="spin" id="spin"></div>
 <span class="hint" style="margin:0" id="status"></span></div></div>
<div id="out-area" class="hide">
 <div id="msgs"></div>
 <div class="card"><h2 id="resTitle">Result</h2><div class="chips" id="chips"></div>
  <table><thead><tr><th>Bill No.</th><th>Status</th><th style="text-align:right">Amount (INR)</th><th>Advice file</th><th>Details</th></tr></thead><tbody id="rows"></tbody></table></div>
 <div class="card" id="dlCard"><h2>Excel files</h2><p class="hint">The uploader accumulates every posted bill. &ldquo;New rows&rdquo; has only what this run added.</p>
  <div class="row" id="dl"></div></div>
 <div class="card"><details><summary>Run log</summary><pre id="log"></pre></details></div>
</div>
</main>
<footer>Version: __VER__ &middot; Runs only on this computer &middot; <a href="#" id="quit">Quit the app</a></footer>
<script>
const S={a:[],s:[]};const $=id=>document.getElementById(id);
function zone(dz,inp,list,key){
 const el=$(dz),fi=$(inp);
 el.onclick=()=>fi.click();
 fi.onchange=()=>{add(key,fi.files);fi.value=""};
 ["dragenter","dragover"].forEach(e=>el.addEventListener(e,ev=>{ev.preventDefault();el.classList.add("over")}));
 ["dragleave","drop"].forEach(e=>el.addEventListener(e,ev=>{ev.preventDefault();el.classList.remove("over")}));
 el.addEventListener("drop",ev=>add(key,ev.dataTransfer.files));
}
function add(key,files){for(const f of files){if(!S[key].some(x=>x.name===f.name&&x.size===f.size))S[key].push(f)}render()}
function render(){for(const [k,l] of [["a","l1"],["s","l2"]]){const ul=$(l);ul.innerHTML="";
 S[k].forEach((f,i)=>{const li=document.createElement("li");const n=document.createElement("span");n.className="nm";n.textContent=f.name;
  const b=document.createElement("button");b.textContent="×";b.title="Remove";b.onclick=()=>{S[k].splice(i,1);render()};li.append(n,b);ul.append(li)})}}
zone("dz1","in1","l1","a");zone("dz2","in2","l2","s");
function loadCfg(){fetch("/api/config").then(r=>r.json()).then(c=>{if(!$("work").value)$("work").value=c.work_dir;if(!$("out").value)$("out").value=c.out_dir;
 $("inboxPath").textContent="Folder: "+c.inbox+"  \u2013  advices here are processed in place and MOVED to Posted / Not Posted.";
 const ul=$("inboxList");ul.innerHTML="";
 if(!c.inbox_advices.length)ul.append(el("li","","No bank advice waiting."));
 c.inbox_advices.forEach(n=>ul.append(el("li","","\ud83d\udcc4 "+n)));
 (c.inbox_statements||[]).forEach(n=>ul.append(el("li","","\ud83d\udcca Bank statement: "+n)));
 $("fGo").disabled=$("fPrev").disabled=!c.inbox_advices.length;})}
loadCfg();
function el(t,c,x){const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e}
function busy(on,txt){$("bPrev").disabled=$("bGo").disabled=$("fRef").disabled=on;if(on)$("fGo").disabled=$("fPrev").disabled=true;$("spin").style.display=on?"block":"none";$("status").textContent=txt||""}
async function run(dry,folder){
 if(!folder&&(!S.a.length||!S.s.length)){show({error:"Please add at least one bank advice AND the bank statement first."});return}
 const fd=new FormData();if(!folder)S.a.forEach(f=>fd.append("advices",f,f.name));S.s.forEach(f=>fd.append("statements",f,f.name));
 fd.append("work_dir",$("work").value);fd.append("out_dir",$("out").value);if(folder)fd.append("mode","folder");
 busy(true,dry?"Checking...":"Processing...");
 try{const r=await fetch("/api/process?dry="+(dry?1:0),{method:"POST",body:fd});const j=await r.json();show(j);
  if(j.ok&&!dry){S.a=[];render()}}
 catch(e){show({error:"Could not reach the app: "+e})}
 busy(false,"");loadCfg()}
function badge(s){const c=s==="POSTED"?"POSTED":s==="ALREADY POSTED"?"ALREADY":s==="NOT POSTED"?"NOT":"SKIPPED";return el("span","badge b-"+c,s)}
function show(j){
 $("out-area").classList.remove("hide");const m=$("msgs");m.innerHTML="";
 if(j.error){m.append(el("div","msg err",j.error));$("rows").innerHTML="";$("chips").innerHTML="";$("dlCard").classList.add("hide");
  $("resTitle").textContent="Not processed";$("log").textContent=(j.log||[]).join("\n");return}
 (j.warnings||[]).forEach(w=>m.append(el("div","msg warn",w)));
 if(j.dry_run)m.append(el("div","msg info","PREVIEW ONLY – nothing was written or moved. "+j.would_add+" row(s) would be added to the uploader."));
 else m.append(el("div","msg info",j.rows_added+" row(s) added to "+j.uploader_file+". Advice files were MOVED into the Posted / Not Posted folders."));
 $("resTitle").textContent=j.dry_run?"Preview":"Result";
 const ch=$("chips");ch.innerHTML="";
 const c=j.counts||{};
 [["POSTED","c-ok","Posted"],["ALREADY POSTED","c-warn","Already posted"],["NOT POSTED","c-bad","Not posted"],["SKIPPED","c-warn","Ignored files"]]
  .forEach(([k,cl,lab])=>{if(c[k])ch.append(el("div","chip "+cl,c[k]+" "+lab))});
 const tb=$("rows");tb.innerHTML="";
 (j.results||[]).forEach(r=>{const tr=el("tr");tr.append(el("td","",r.bill||"–"));const td=el("td");td.append(badge(r.status));tr.append(td);
  tr.append(el("td","num",r.amount||""),el("td","",r.advice),el("td","note",r.note));tb.append(tr)});
 $("log").textContent=(j.log||[]).join("\n");
 const dl=$("dl");dl.innerHTML="";$("dlCard").classList.toggle("hide",!!j.dry_run);
 if(!j.dry_run){
  const d=j.downloads||{};
  const mk=(txt,href,pri)=>{const a=el("a");a.href=href;const b=el("button","btn"+(pri?" primary":""),txt);a.append(b);dl.append(a)};
  if(d.uploader)mk("⬇ Download Bank Uploader (Excel)","/download/uploader",true);
  if(d.run_rows)mk("⬇ Download new rows of this run","/download/run?id="+d.run_rows);
  if(d.posted)mk("⬇ Download Uploader-Posted","/download/posted");
  [["output","Open output folder"],["posted","Open Posted folder"],["notposted","Open Not Posted folder"]].forEach(([w,t])=>{
   const b=el("button","btn",t);b.onclick=()=>fetch("/api/open",{method:"POST",body:JSON.stringify({what:w})});dl.append(b)})}
 $("out-area").scrollIntoView({behavior:"smooth"})}
$("bPrev").onclick=()=>run(true,false);$("bGo").onclick=()=>run(false,false);
$("fPrev").onclick=()=>run(true,true);$("fGo").onclick=()=>run(false,true);$("fRef").onclick=loadCfg;
$("quit").onclick=async e=>{e.preventDefault();if(confirm("Stop the app?")){await fetch("/api/quit",{method:"POST"});document.body.innerHTML="<p style='padding:40px'>The app has stopped. You can close this tab.</p>"}};
</script></body></html>
"""

if __name__ == "__main__":
    main()
