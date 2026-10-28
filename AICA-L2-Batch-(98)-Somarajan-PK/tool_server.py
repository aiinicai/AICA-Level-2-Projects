"""Local application server for the Bank Reconciliation tool (web app + Tally connector + engine).

Browsers cannot talk to Tally directly (no CORS), so this small Python server sits in between:
    browser (web app)  <->  tool_server.py (127.0.0.1 only)  <->  Tally Prime XML server (localhost:9000)

Run:   python tool_server.py          (opens http://127.0.0.1:8765)
Flow:  1) Pull bank books from Tally (choose bank)   2) Add bank statement   3) Reconcile
       4) Review results in the app   5) Approve   6) Export to Excel (only after approval)

Security: listens on 127.0.0.1 only; only localhost Tally hosts are allowed unless you start with --allow-host;
cross-site requests are rejected. Pulled data is saved under the --data folder on this computer.
"""
import argparse, json, re, subprocess, sys, threading, uuid, webbrowser
from collections import OrderedDict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd

import recon_engine as E
import tally_extract as T

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "webapp"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json",
         ".svg": "image/svg+xml", ".css": "text/css"}


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
RUNS = OrderedDict()                       # run_id -> engine run (kept in memory for review/export)
MAX_BODY = 25 * 1024 * 1024


def demo_payload():
    """Synthetic 2-bank sample (generated on first use) for trying the app without Tally."""
    d = ROOT / "sample_data"
    if not (d / "tally_bank_books.json").exists():
        subprocess.run([sys.executable, str(ROOT / "generate_data.py")], cwd=ROOT, check=True, capture_output=True)
    tally = json.loads((d / "tally_bank_books.json").read_text(encoding="utf-8"))
    out = dict(tally=tally, statements={}, opening={}, settings={k: v for k, v in json.loads((d / "config.json").read_text(encoding="utf-8")).items()
                                 if k in ("approval_limit", "stale_days", "date_tolerance")})
    for b in tally["banks"]:
        f = d / "banks" / T.safe_name(b["name"])
        out["statements"][b["name"]] = (f / "bank_statement.csv").read_text(encoding="utf-8")
        out["opening"][b["name"]] = (f / "opening_items.csv").read_text(encoding="utf-8")
    return out


def check_statement(text):
    bank = E.standardise(E.read_statement(text), E.BANK_COLS, "B")
    warn = []
    bad = int(bank.date.isna().sum())
    if bad:
        warn.append(f"{bad} row(s) have an unreadable date.")
    opening = None if pd.isna(bank.balance.iloc[0]) else float(bank.balance.iloc[0] - bank.amount.iloc[0])
    if opening is None:
        warn.append("No Balance column: opening balance cannot be derived; enter it in the settings.")
    closing = None if opening is None else opening + float(bank.amount.sum())
    return dict(rows=len(bank), date_from=E.fdate(bank.date.min()), date_to=E.fdate(bank.date.max()),
                opening=opening, closing=closing, credits=float(bank.amount[bank.amount > 0].sum()),
                debits=float(-bank.amount[bank.amount < 0].sum()), warnings=warn)


def do_reconcile(p):
    st = p.get("settings") or {}
    books = p.get("books") or {}
    if not p.get("statement_csv"):
        raise ValueError("Add the bank statement first.")
    if "rows" not in books or "opening_balance" not in books:
        raise ValueError("Pull the bank books from Tally first.")
    cfg = dict(entity=p.get("entity") or "", bank=p.get("bank") or "", period=f"{p['period_from']} to {p['period_to']}",
               period_end=p["period_to"], approval_limit=float(st.get("approval_limit") or 50000),
               stale_days=int(st.get("stale_days") or 90), date_tolerance=int(st.get("date_tolerance") or 3))
    bo = st.get("bank_opening")
    run = E.run_from_inputs(p["statement_csv"], books["rows"], books["opening_balance"], p.get("opening_csv") or "", cfg,
                            bank_opening=None if bo in (None, "") else float(bo))
    rid = uuid.uuid4().hex[:12]
    RUNS[rid] = run
    while len(RUNS) > 20:
        RUNS.popitem(last=False)
    return dict(run_id=rid, result=E.to_ui(run))


def do_export(p, export_dir):
    run = RUNS.get(p.get("run_id"))
    if run is None:
        raise LookupError("This reconciliation is no longer in memory (server restarted?). Please run it again.")
    ap = p.get("approval") or {}
    reviewer = str(ap.get("reviewer") or "").strip()
    decisions = list(ap.get("decisions") or [])
    remarks = str(ap.get("remarks") or "").strip()
    if not ap.get("approved"):
        raise ValueError("Export is only available after the reconciliation has been approved.")
    if not reviewer:
        raise ValueError("Reviewer name is required for approval.")
    if len(decisions) != len(run["entries"]) or any(d not in ("Approved", "Rejected") for d in decisions):
        raise ValueError("Approve or reject every proposed journal entry before exporting.")
    if abs(run["diff"]) >= 0.01 and not remarks:
        raise ValueError("The reconciliation has an unreconciled difference: reviewer remarks are required.")
    approval = dict(reviewer=reviewer, remarks=remarks, decisions=decisions, approved_at=datetime.now().strftime("%d-%m-%Y %H:%M"),
                    difference=run["diff"], n_approved=decisions.count("Approved"), n_rejected=decisions.count("Rejected"),
                    n_flags=len(run["flags"]), n_high=sum(f["risk"] == "High" for f in run["flags"]))
    Path(export_dir).mkdir(parents=True, exist_ok=True)
    cfg = run["cfg"]
    name = f"Reconciliation_{T.safe_name(cfg.get('bank') or 'bank')}_{T.safe_name(cfg['period_end'])}_APPROVED.xlsx"
    path = Path(export_dir) / name
    E.export_run(path, run, approval)
    return name, path


def make_handler(data_dir, allow_hosts, export_dir="exports"):
    class H(BaseHTTPRequestHandler):
        server_version = "BankReconTool"

        def log_message(self, fmt, *a):
            sys.stderr.write("[tool] " + fmt % a + "\n")

        # ---- helpers
        def send(self, code, obj, ctype="application/json", extra=None):
            body = obj if isinstance(obj, bytes) else json.dumps(obj, default=lambda o: o.item() if hasattr(o, "item") else str(o)).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def origin_ok(self):
            o = self.headers.get("Origin")
            if not o:
                return True
            port = self.server.server_address[1]
            return o in (f"http://127.0.0.1:{port}", f"http://localhost:{port}")

        def params(self):
            p = self.read_json()
            host = str(p.get("host") or "localhost").strip()
            if host not in LOCAL_HOSTS and host not in allow_hosts:
                raise ValueError(f"Host '{host}' is not allowed. Use localhost (or start the tool with --allow-host {host}).")
            port = int(p.get("port") or 9000)
            if not 1 <= port <= 65535:
                raise ValueError("Port must be 1-65535.")
            return p, host, port, (str(p.get("company") or "").strip() or None)

        def read_json(self):
            if "application/json" not in (self.headers.get("Content-Type") or ""):
                raise ValueError("Content-Type must be application/json")
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise ValueError("Request too large.")
            return json.loads(self.rfile.read(n) or b"{}")

        # ---- routes
        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/api/demo":
                try:
                    return self.send(200, demo_payload())
                except Exception as e:
                    return self.send(500, {"error": f"Could not prepare demo data: {e}"})
            if path == "/api/ping":
                return self.send(200, {"ok": True, "data_dir": str(data_dir)})
            rel = "index.html" if path in ("/", "") else path.lstrip("/")
            f = (WEB / rel).resolve()
            if WEB not in f.parents or not f.is_file():
                return self.send(404, {"error": "Not found"})
            self.send(200, f.read_bytes(), TYPES.get(f.suffix, "application/octet-stream"))

        def do_POST(self):
            if not self.origin_ok():
                return self.send(403, {"error": "Cross-site request blocked."})
            try:
                if self.path == "/api/tally/test":
                    _, host, port, company = self.params()
                    return self.send(200, T.check_connection(host, port, company))
                if self.path == "/api/tally/pull":
                    p, host, port, company = self.params()
                    d_from, d_to = T.dmy(str(p.get("from"))), T.dmy(str(p.get("to")))
                    if d_to < d_from:
                        raise ValueError("'To' date is before 'From' date.")
                    fy = T.dmy(p["fy_start"]) if p.get("fy_start") else None
                    data = T.pull(host, port, company, d_from, d_to, fy)
                    T.write_outputs(Path(data_dir), company, d_from, d_to, data["banks"])
                    return self.send(200, {"data": data, "saved_to": str(Path(data_dir).resolve())})
                if self.path == "/api/statement/check":
                    return self.send(200, check_statement(self.read_json().get("csv") or ""))
                if self.path == "/api/reconcile":
                    return self.send(200, do_reconcile(self.read_json()))
                if self.path == "/api/export":
                    name, path = do_export(self.read_json(), export_dir)
                    return self.send(200, path.read_bytes(), XLSX, {
                        "Content-Disposition": f'attachment; filename="{name}"',
                        "X-Saved-To": str(path.resolve()), "X-File-Name": name,
                        "Access-Control-Expose-Headers": "X-Saved-To, X-File-Name"})
                return self.send(404, {"error": "Unknown endpoint"})
            except LookupError as e:
                return self.send(410, {"error": str(e)})
            except T.TallyError as e:
                return self.send(502, {"error": str(e)})
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                return self.send(400, {"error": f"Invalid request: {e}"})
            except Exception as e:                       # keep the server alive; report it
                return self.send(500, {"error": f"Unexpected error: {e}"})
    return H


def serve(port=8765, data_dir="tally_export", allow_hosts=(), open_browser=True, export_dir="exports"):
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(data_dir, set(allow_hosts), export_dir))
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    print(f"Bank Reconciliation tool running at {url}  (Ctrl+C to stop)")
    print(f"Pulled Tally data is saved in: {Path(data_dir).resolve()}")
    print(f"Approved Excel exports are saved in: {Path(export_dir).resolve()}")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    return srv


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Local connector + web server for the Bank Reconciliation tool")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--data", default="tally_export", help="folder where pulled Tally data is saved")
    ap.add_argument("--export-dir", default="exports", help="folder for approved Excel exports")
    ap.add_argument("--allow-host", action="append", default=[], help="extra Tally host allowed (e.g. a LAN IP)")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    s = serve(a.port, a.data, a.allow_host, not a.no_browser, a.export_dir)
    try:
        s.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
