"""
LookThrough Data Bridge — runs on your PC, fetches real market data and serves the app.

    python lookthrough_bridge.py            start the bridge and open the app (default)
    python lookthrough_bridge.py refresh    fetch everything and rebuild the offline app, then exit
    python lookthrough_bridge.py build      rebuild from cached data only (no internet)
    python lookthrough_bridge.py scan       list what the portfolio parser finds in data/amc_portfolios

The server listens on 127.0.0.1 only; nothing is exposed to the network.
"""
import json
import re
import sys
import threading
import traceback
import webbrowser
from contextlib import contextmanager
from datetime import date
from http.cookies import SimpleCookie
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import amc_parser  # noqa: E402
import auth  # noqa: E402
import build_dataset  # noqa: E402
import cas_statement  # noqa: E402
import contract_note  # noqa: E402
import ledger  # noqa: E402
import sources as S  # noqa: E402
from common import APP_OUT, CACHE, CONFIG, LIVE, PORTFOLIO_DIR, VERSION, config, load_json, log, now_iso, save_json  # noqa: E402

JOB = {"running": False, "lines": [], "error": None, "started": None, "finished": None, "kind": None}
LOCK = threading.Lock()


def run_job(kind, fn):
    with LOCK:
        if JOB["running"]:
            return False
        JOB.update(running=True, lines=[], error=None, started=now_iso(), finished=None, kind=kind)

    def progress(msg):
        JOB["lines"].append(f"{now_iso()[11:]}  {msg}")
        JOB["lines"] = JOB["lines"][-200:]
        log.info(msg)

    def target():
        try:
            fn(progress)
            progress("Finished.")
        except Exception as e:  # noqa: BLE001
            JOB["error"] = str(e)
            progress(f"Failed: {e}")
            log.error(traceback.format_exc())
        finally:
            JOB["running"] = False
            JOB["finished"] = now_iso()

    threading.Thread(target=target, daemon=True).start()
    return True


def scan(progress=lambda m: None):
    schemes = config("schemes")
    res = amc_parser.scan_folder(PORTFOLIO_DIR, schemes)
    save_json(CACHE / "portfolios_scanned.json", res)
    progress(f"Scanned {len({r['file'] for r in res})} files, {len([r for r in res if r.get('holdings')])} portfolio sheets")
    return res


def scan_summary(res):
    names = {s["scheme_id"]: s["name"] for s in config("schemes")}
    out = []
    for i, r in enumerate(res):
        top = sorted(r.get("holdings") or [], key=lambda h: -h["weight"])[:5]
        out.append({"id": i, "file": r["file"], "sheet": r.get("sheet"), "scheme_id": r.get("scheme_id"), "scheme_name": names.get(r.get("scheme_id")),
                    "portfolio_date": r.get("portfolio_date"), "n": r.get("n", 0), "equity_pct": r.get("equity_pct"), "debt_other_pct": r.get("debt_other_pct"),
                    "listed_total_pct": r.get("listed_total_pct"), "title": r.get("title"), "warnings": r.get("warnings", []),
                    "top": [{"name": h["name"], "isin": h["isin"], "weight": round(h["weight"], 2)} for h in top], "error": r.get("error")})
    return out


def apply_portfolios(assign):
    scanned = load_json(CACHE / "portfolios_scanned.json", []) or []
    applied = {(p["scheme_id"], p["portfolio_date"]): p for p in (load_json(CACHE / "portfolios_applied.json", []) or [])}
    n = 0
    for a in assign:
        i = int(a["id"])
        if i >= len(scanned) or not scanned[i].get("holdings"):
            continue
        r = dict(scanned[i])
        r["scheme_id"] = a.get("scheme_id") or r.get("scheme_id")
        r["portfolio_date"] = a.get("portfolio_date") or r.get("portfolio_date")
        if not r["scheme_id"] or not r["portfolio_date"]:
            continue
        r["applied_at"] = now_iso()
        applied[(r["scheme_id"], r["portfolio_date"])] = r
        n += 1
    save_json(CACHE / "portfolios_applied.json", list(applied.values()))
    return n


def search(q):
    q = q.strip()
    if len(q) < 2:
        return []
    by_sym, _ = S.nse_equity_list()
    ql = q.lower()
    hits = []
    for sym, v in by_sym.items():
        if v.get("series") not in ("EQ", "BE", "BZ", ""):
            continue
        score = 3 if sym.lower() == ql else 2 if sym.lower().startswith(ql) else 1 if ql in v["name"].lower() else 0
        if score:
            hits.append((score, {"symbol": sym, "name": v["name"], "isin": v["isin"], "exchange": "NSE", "source": "NSE list"}))
    hits.sort(key=lambda x: (-x[0], x[1]["symbol"]))
    out = [h for _, h in hits[:12]]
    if len(out) < 5:
        seen = {h["symbol"] for h in out}
        out += [h for h in S.yahoo_search(q) if h["symbol"] not in seen][:8]
    return out


def price_months(symbol):
    """Month-end closes available for an NSE symbol in the app's 37-month window (fetches that one ticker)."""
    from common import month_ends, valuation_date
    dates = month_ends(valuation_date(), 37)
    tk = S.yahoo_ticker(symbol)
    cache = S.yahoo_prices([tk], start=date(dates[0].year, dates[0].month, 1), end=date.today())
    pts = (cache or {}).get(tk, {}).get("points") or []
    return sum(v is not None for v in S.monthly_from_daily([(date.fromisoformat(d), v) for d, v in pts], dates))


def equity_candidate(symbol, sector, ds):
    """Check a listed company before it is added: on NSE's equity list, not already in the security master, and with
    enough price history to be valued. Financial statements are fetched but optional (priced, not scored, without)."""
    sym = str(symbol or "").upper().strip()
    if not re.fullmatch(r"[A-Z0-9&\-]{1,20}", sym):
        raise ledger.LedgerError("Enter the NSE symbol (letters, digits, & or -).")
    by_sym, _ = S.nse_equity_list()
    v = by_sym.get(sym)
    if not v:
        raise ledger.LedgerError(f"{sym} is not on NSE's equity list. Only NSE-listed shares can be priced by the app; "
                                 "a BSE-only company cannot be added yet.")
    if v.get("series") not in ("EQ", "BE", "BZ", ""):
        raise ledger.LedgerError(f"{sym} trades in series {v.get('series')}, not as an equity share.")
    hit = next((c for c in ds["companies"] if c["code"] == sym or (v.get("isin") and c.get("isin") == v["isin"])), None)
    if hit and hit.get("price"):
        raise ledger.LedgerError(f"{hit['name']} is already in the security master as {hit['code']}, priced. You can record transactions for it directly.")
    if hit and hit["code"] != sym:
        raise ledger.LedgerError(f"{hit['name']} is in the master under {hit['code']} (same ISIN {v.get('isin')}); it cannot be added again under {sym}.")
    # a company held only inside funds is in the master for look-through but was never priced: adding it fetches its price
    n = price_months(sym)
    if n < ledger.MIN_PRICE_MONTHS:
        raise ledger.LedgerError(f"{sym} has {n} month-end prices in the app's 3-year window; at least {ledger.MIN_PRICE_MONTHS} are needed "
                                 "to value it and measure returns (recently listed, or Yahoo has no data for it).")
    info, has_fin = {}, False
    try:
        co = S.yahoo_company(sym, refresh=True)
        info, has_fin = co.get("info") or {}, bool(co.get("years"))
    except Exception as e:  # noqa: BLE001 - statements are optional
        log.warning("%s statements: %s", sym, e)
    auto = build_dataset.YAHOO_SECTOR.get(info.get("sector") or "") or build_dataset.sector_from_text(info.get("industry"))
    return {"symbol": sym, "name": v.get("name") or info.get("longName") or sym, "isin": v.get("isin") or "",
            "sector": sector or auto or "Others", "industry": info.get("industry") or "", "has_fin": has_fin}


class JobBusy(Exception):
    pass


@contextmanager
def job_slot(kind):
    """Hold the single data-update slot for a synchronous change (entry + rebuild); refuse if a refresh is running."""
    with LOCK:
        if JOB["running"]:
            raise JobBusy("A data update is running. Try again when it finishes.")
        JOB.update(running=True, lines=[], error=None, started=now_iso(), finished=None, kind=kind)
    try:
        yield
    finally:
        JOB["running"] = False
        JOB["finished"] = now_iso()


def current_dataset():
    ds = load_json(LIVE / "dataset.json")
    if not ds:
        raise ledger.LedgerError("No dataset yet. Run a refresh first.")
    ds.setdefault("members_demo", config("family")["members"])
    return ds


def latest_prices(extra_codes=()):
    """Latest prices beside the valuation-date figures: every equity the family holds (plus any company asked for) from
    Yahoo, and every tracked scheme's latest NAV from AMFI. The analytics stay at the valuation date."""
    ds = current_dataset()
    known = {c["code"] for c in ds["companies"] if c.get("price")}
    codes = sorted({t["instrument"] for t in ds["transactions"] if t["asset_type"] == "EQ"} | {c for c in extra_codes if c in known})[:400]
    tk = {c: S.yahoo_ticker(c) for c in codes}
    q = S.latest_quotes(list(tk.values()))
    navs = S.latest_navs()
    mf = {}
    for sc in ds["schemes"]:
        for plan, code in (("Direct", sc.get("amfi_code")), ("Regular", sc.get("amfi_code_regular"))):
            if code and code in navs:
                mf[f"{sc['scheme_id']}|{plan}"] = navs[code]
    return {"as_of": now_iso(), "valuation_date": ds["meta"]["as_on"], "equity": {c: q[t] for c, t in tk.items() if t in q}, "mf": mf,
            "sources": {"equity": "Yahoo Finance, NSE (delayed about 15 minutes in market hours; last close otherwise)",
                        "mf": "AMFI NAVAll.txt (latest published NAV)"}}


def nav_months(code):
    """Month-end NAVs available for an AMFI code in the app's 37-month window (fetches the history if not cached)."""
    from common import month_ends, valuation_date
    return sum(v is not None for v in S.nav_monthly(S.mf_nav_history(code), month_ends(valuation_date(), 37)))


def scheme_search(q):
    navall = S.amfi_navall()
    tracked = {}
    for x in config("schemes") + ledger.load()["schemes"]:
        for c in (x.get("amfi_code_direct"), x.get("amfi_code_regular")):
            if c:
                tracked[str(c)] = x["scheme_id"]
    res = S.amfi_search(q, navall)
    for g in res:
        g["tracked_as"] = tracked.get(g["direct"]["code"]) or (tracked.get(g["regular"]["code"]) if g["regular"] else None)
        g["not_equity"] = bool(ledger.NOT_EQUITY.search(g["direct"]["name"]))
    return {"results": res, "amfi_rows": len(navall), "categories": ledger.SCHEME_CATEGORIES, "benchmarks": ledger.BENCHMARKS}


def month_end_navs(ds, sid, plan, iso_date):
    """Month-end NAVs either side of a date for one scheme and plan, for the CAS NAV check."""
    nv = sorted((n["date"], n["nav"]) for n in ds["nav_history"] if n["scheme_id"] == sid and n["plan"] == plan and n.get("nav"))
    return [c for d, c in nv if d <= iso_date][-1:] + [c for d, c in nv if d >= iso_date][:1]


def read_upload(handler):
    """(file bytes or None, file name, form fields) from a multipart upload."""
    raw = handler._json_body()
    msg = BytesParser(policy=policy.default).parsebytes(b"Content-Type: " + (handler.headers.get("Content-Type") or "").encode() + b"\r\n\r\n" + raw)
    data, fname, fields = None, "", {}
    for part in msg.iter_parts() if msg.is_multipart() else []:
        if part.get_filename():
            data, fname = part.get_payload(decode=True) or b"", Path(part.get_filename()).name
        else:
            fields[part.get_param("name", header="content-disposition")] = (part.get_content() or "").strip()
    return data, fname, fields


def month_end_closes(ds, code, iso_date):
    """Month-end closes either side of a trade date (the one before and the one after), for the rate check."""
    px = sorted((p["date"], p["close"]) for p in ds["prices"] if p["code"] == code and p.get("close"))
    before = [c for d, c in px if d <= iso_date][-1:]
    after = [c for d, c in px if d >= iso_date][:1]
    return before + after

COOKIE = "lt_session"
PUBLIC_GET = {"/login", "/api/auth-state"}
# Installable-app (PWA) files: public, because the browser fetches the manifest without the sign-in cookie; none holds data.
# The service worker caches only these (never the app page or /api), so no portfolio data is stored in the browser.
PWA_FILES = {"/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"), "/sw.js": ("sw.js", "text/javascript; charset=utf-8"),
             "/offline.html": ("offline.html", "text/html; charset=utf-8"), "/icons/icon-192.png": ("icons/icon-192.png", "image/png"),
             "/icons/icon-512.png": ("icons/icon-512.png", "image/png"), "/icons/icon-maskable-512.png": ("icons/icon-maskable-512.png", "image/png"),
             "/icons/apple-touch-icon.png": ("icons/apple-touch-icon.png", "image/png")}


def _script_hashes(html):
    """CSP source list allowing exactly the page's own inline scripts (by SHA-256), and nothing else."""
    import base64
    import hashlib
    import re
    html = html.encode() if isinstance(html, str) else html
    found = re.findall(rb"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S | re.I)
    # browsers hash the script AFTER the HTML parser normalises line endings (CRLF and lone CR become LF); the built file has CRLF
    found = [b.replace(b"\r\n", b"\n").replace(b"\r", b"\n") for b in found]
    return " ".join(dict.fromkeys("'sha256-" + base64.b64encode(hashlib.sha256(b).digest()).decode() + "'" for b in found))


def page_csp(html):
    """Content-Security-Policy for a page served by the bridge: scripts only by hash (no eval, no injected script), data only
    from this bridge, fonts from Google Fonts, no framing, no plugins, no form posts elsewhere."""
    return ("default-src 'none'; script-src 'self' " + _script_hashes(html) + "; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; base-uri 'none'; form-action 'self'; "
            "frame-ancestors 'none'; object-src 'none'; manifest-src 'self'; worker-src 'self'")


_APP_CSP = {}


def app_csp(body, stamp):
    """page_csp for the built app, cached per build (hashing 2 MB on every page load is wasted work)."""
    if _APP_CSP.get("stamp") != stamp:
        _APP_CSP.update(stamp=stamp, csp=page_csp(body))
    return _APP_CSP["csp"]


def _code_id():
    """Fingerprint of the bridge code this process runs. A second launch compares it with the running bridge's, so an
    earlier build still running is recognised (the app page is read from disk, the API is whatever was loaded)."""
    import hashlib
    h = hashlib.sha256()
    for f in sorted(Path(__file__).resolve().parent.glob("*.py")):
        h.update(f.name.encode() + f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


CODE_ID = _code_id()
PUBLIC_POST = {"/api/login", "/api/setup"}
POST_ROLE = {"/api/logout": "viewer", "/api/refresh": "analyst", "/api/equities": "analyst", "/api/portfolios/upload": "analyst", "/api/contract-note": "analyst", "/api/cas": "analyst", "/api/schemes": "analyst",
             "/api/portfolios/apply": "analyst", "/api/entities": "analyst", "/api/transactions": "analyst",
             "/api/settings": "analyst", "/api/users": "admin"}
GET_ROLE = {"/api/users": "admin", "/api/amfi-search": "analyst"}


class Handler(BaseHTTPRequestHandler):
    server_version = f"LookThroughBridge/{VERSION}"

    def log_message(self, fmt, *args):  # quieter console
        pass

    def _send(self, code, body, ctype="application/json", headers=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, default=str).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def _origin_ok(self):
        """Browsers send Origin on cross-site POSTs; accept only our own page (or no Origin, e.g. scripts)."""
        origin = self.headers.get("Origin")
        if not origin:
            return True
        o = urlparse(origin)
        return o.hostname in ("127.0.0.1", "localhost") and o.port == self.server.server_address[1]

    MAX_BODY = 60 * 1024 * 1024

    def _json_body(self):
        """The request body, read once (do_POST reads it before any check, see there)."""
        if getattr(self, "_raw", None) is None:
            n = int(self.headers.get("Content-Length") or 0)
            if n > self.MAX_BODY:
                raise ValueError("Request too large")
            self._raw = self.rfile.read(n) if n else b""
        return self._raw

    def _body(self):
        return json.loads(self._json_body() or b"{}")

    def _token(self):
        c = SimpleCookie(self.headers.get("Cookie") or "")
        return c[COOKIE].value if COOKIE in c else None

    def _session(self):
        # an automatic background poll (refresh progress) checks the session without counting as user activity
        return auth.get_session(self._token(), touch=not self.headers.get("X-LT-Background"))

    def _cookie(self, token, max_age):
        return {"Set-Cookie": f"{COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={max_age}"}

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "forbidden"})
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in PWA_FILES:
                name, ctype = PWA_FILES[u.path]
                f = APP_OUT.parent / "pwa" / name
                if not f.exists():
                    return self._send(404, {"error": "not found"})
                body = f.read_bytes()
                return self._send(200, body, ctype, {"Content-Security-Policy": page_csp(body)} if name.endswith(".html") else None)
            if u.path == "/login":
                return self._send(200, LOGIN_PAGE, "text/html; charset=utf-8", {"Content-Security-Policy": LOGIN_CSP})
            if u.path == "/api/auth-state":
                s = self._session()
                return self._send(200, {"setup_needed": not auth.has_users(), "signed_in": bool(s), "user": s and s["user"], "role": s and s["role"],
                                        "code": CODE_ID})
            s = self._session()
            if not s:
                if u.path in ("/", "/index.html"):
                    return self._send(302, b"", "text/plain", {"Location": "/login"})
                return self._send(401, {"error": "Sign in required."})
            need = GET_ROLE.get(u.path, "viewer")
            if not auth.allowed(s["role"], need):
                return self._send(403, {"error": f"Your role ({s['role']}) cannot do this."})
            if u.path in ("/", "/index.html"):
                if not APP_OUT.exists():
                    return self._send(503, "App not built yet. Run a refresh.", "text/plain")
                body, st = APP_OUT.read_bytes(), APP_OUT.stat()
                return self._send(200, body, "text/html; charset=utf-8", {"Content-Security-Policy": app_csp(body, (st.st_mtime_ns, st.st_size))})
            if u.path == "/api/me":
                return self._send(200, {"user": s["user"], "role": s["role"]})
            if u.path == "/api/status":
                ds = load_json(LIVE / "dataset.json")
                meta = (ds or {}).get("meta", {})
                return self._send(200, {"ok": True, "version": VERSION, "as_on": meta.get("as_on"), "built_at": meta.get("built_at"),
                                        "warnings": meta.get("warnings", []), "job": {k: JOB[k] for k in ("running", "kind", "error", "started", "finished")},
                                        "counts": {k: len(ds[k]) for k in ("companies", "schemes", "scheme_portfolios", "transactions")} if ds else None,
                                        "user": s["user"], "role": s["role"], "idle_seconds": auth.IDLE_SECONDS})
            if u.path == "/api/dataset":
                p = LIVE / "dataset.json"
                return self._send(200, p.read_bytes()) if p.exists() else self._send(404, {"error": "No dataset yet. Run a refresh."})
            if u.path == "/api/job":
                return self._send(200, JOB)
            if u.path == "/api/ledger":
                led = ledger.load()
                return self._send(200, {"members": led["members"], "transactions": led["transactions"], "settings": led["settings"],
                                        "entity_types": ledger.ENTITY_TYPES, "txn_types": ledger.TXN_TYPES, "plans": ledger.PLANS,
                                        "schemes": led["schemes"], "scheme_categories": ledger.SCHEME_CATEGORIES, "benchmarks": ledger.BENCHMARKS,
                                        "companies": led["companies"], "sectors": ledger.SECTORS})
            if u.path == "/api/audit":
                return self._send(200, ledger.read_audit(int(q.get("limit", 300))))
            if u.path == "/api/users":
                return self._send(200, auth.list_users())
            if u.path == "/api/search":
                return self._send(200, search(q.get("q", "")))
            if u.path == "/api/portfolios/scan":
                return self._send(200, scan_summary(scan()))
            if u.path == "/api/schemes":
                return self._send(200, config("schemes") + ledger.load()["schemes"])
            if u.path == "/api/quotes":
                extra = [c.strip().upper() for c in (q.get("codes") or "").split(",") if c.strip()][:20]
                return self._send(200, latest_prices(extra))
            if u.path == "/api/amfi-search":
                q = (q.get("q") or [""])[0] if isinstance(q.get("q"), list) else q.get("q", "")
                if len(q.strip()) < 3:
                    return self._send(400, {"error": "Type at least 3 characters of the scheme name, its AMFI code or its ISIN."})
                return self._send(200, scheme_search(q))
            return self._send(404, {"error": "not found"})
        except Exception as e:  # noqa: BLE001
            log.error(traceback.format_exc())
            return self._send(500, {"error": str(e)})

    def do_POST(self):
        # Read the body BEFORE any refusal: answering while the client is still sending leaves unread bytes, and Windows
        # then resets the connection, so the client sees a network error instead of the 403.
        self._raw = None
        try:
            self._json_body()
        except ValueError:
            self.close_connection = True
            return self._send(413, {"error": "The upload is larger than 60 MB."})
        if not self._host_ok() or not self._origin_ok():
            return self._send(403, {"error": "forbidden"})
        u = urlparse(self.path)
        try:
            if u.path == "/api/setup":
                if auth.has_users():
                    return self._send(403, {"error": "Setup is already complete. Ask an admin to create your account."})
                b = self._body()
                auth.create_user(b.get("user"), b.get("password"), "admin", "setup")
                token = auth.new_session(b["user"].strip().lower(), "admin")
                return self._send(200, {"ok": True}, headers=self._cookie(token, auth.SESSION_SECONDS))
            if u.path == "/api/login":
                b = self._body()
                role = auth.verify(b.get("user"), b.get("password"))
                token = auth.new_session(b["user"].strip().lower(), role)
                return self._send(200, {"ok": True, "role": role}, headers=self._cookie(token, auth.SESSION_SECONDS))
            s = self._session()
            if not s:
                return self._send(401, {"error": "Sign in required."})
            need = POST_ROLE.get(u.path)
            if need is None:
                return self._send(404, {"error": "not found"})
            if not auth.allowed(s["role"], need):
                return self._send(403, {"error": f"Your role ({s['role']}) cannot do this."})
            user = s["user"]
            if u.path == "/api/logout":
                idle = (self._body() or {}).get("reason") == "idle"
                auth.end_session(self._token())
                ledger.audit(s["user"], "LOGOUT", None, None, "signed out by the app after inactivity" if idle else "signed out")
                return self._send(200, {"ok": True}, headers=self._cookie("", 0))
            if u.path == "/api/refresh":
                ok = run_job("refresh", lambda p: build_dataset.build(fetch=True, progress=p))
                ledger.audit(user, "REFRESH", None, None, "started" if ok else "already running")
                return self._send(202 if ok else 409, {"started": ok})
            if u.path == "/api/equities":
                b = self._body()
                act = b.get("action")
                with job_slot("entry"):
                    if act == "add":
                        ds0 = current_dataset()
                        rec = ledger.add_company(equity_candidate(b.get("symbol"), b.get("sector") or None, ds0), user)
                        build_dataset.build(fetch=False)
                        after = current_dataset()
                        if not any(c["code"] == rec["symbol"] and c.get("price") for c in after["companies"]):
                            ledger.delete_company(rec["symbol"], user)  # the build could not price it: undo rather than keep a phantom
                            build_dataset.build(fetch=False)
                            return self._send(400, {"error": f"{rec['symbol']} was added but could not be priced on the valuation date, so it was removed again."})
                        result = next(c for c in after["companies"] if c["code"] == rec["symbol"])
                    elif act == "update":
                        result = ledger.update_company(b.get("symbol"), b, user)
                        build_dataset.build(fetch=False)
                    elif act == "delete":
                        result = ledger.delete_company(b.get("symbol"), user)
                        build_dataset.build(fetch=False)
                    else:
                        return self._send(400, {"error": "Unknown action."})
                return self._send(200, {"ok": True, "record": result})
            if u.path == "/api/contract-note":
                raw = self._json_body()
                msg = BytesParser(policy=policy.default).parsebytes(b"Content-Type: " + (self.headers.get("Content-Type") or "").encode() + b"\r\n\r\n" + raw)
                pdf, fname, password = None, "", ""
                for part in msg.iter_parts() if msg.is_multipart() else []:
                    if part.get_filename():
                        pdf, fname = part.get_payload(decode=True) or b"", Path(part.get_filename()).name
                    elif part.get_param("name", header="content-disposition") == "password":
                        password = (part.get_content() or "").strip()
                if pdf is None:
                    return self._send(400, {"error": "Choose the contract note PDF."})
                ds = current_dataset()
                try:
                    preview = contract_note.parse(pdf, password, ds["companies"], ds["meta"]["as_on"],
                                                  priced=lambda code: ledger._priced(ds, "EQ", code, "")[0], ref_prices=lambda code, d: month_end_closes(ds, code, d))
                except contract_note.ContractNoteError as e:
                    ledger.audit(user, "CONTRACT_NOTE_READ", None, None, f"{fname}: refused - {e}")
                    return self._send(400, {"error": str(e)})
                preview["file"] = fname
                ledger.audit(user, "CONTRACT_NOTE_READ", None, None,
                             f"{fname} (sha256 {preview['sha256'][:16]}): {len(preview['trades'])} trades, {preview['reconciliation']['status']}")
                return self._send(200, preview)
            if u.path == "/api/cas":
                pdf, fname, fields = read_upload(self)
                if pdf is None:
                    return self._send(400, {"error": "Choose the CAS statement PDF."})
                ds = current_dataset()
                try:
                    preview = cas_statement.parse(pdf, fields.get("password", ""), ds["schemes"], ds["meta"]["as_on"],
                                                  ref_navs=lambda sid, plan, d: month_end_navs(ds, sid, plan, d))
                except cas_statement.CasError as e:
                    ledger.audit(user, "CAS_READ", None, None, f"{fname}: refused - {e}")
                    return self._send(400, {"error": str(e)})
                member = fields.get("member_id") or ""
                seen = {ledger.txn_key(t): t["txn_id"] for t in ds["transactions"] if t["member_id"] == member}
                for f in preview["folios"]:
                    for t in f["txns"]:
                        k = (member, f["scheme_id"], f["plan"] or "", t["date"], t["txn_type"] == "Sell", round(t["units"], 3))
                        t["duplicate_of"] = seen.get(k) if f["scheme_id"] else None
                preview["file"], preview["member_id"] = fname, member
                sm = preview["summary"]
                ledger.audit(user, "CAS_READ", None, None, f"{fname} (sha256 {preview['sha256'][:16]}): {sm['folios']} folios, "
                             f"{sm['transactions']} transactions, {sm['reconciled']} folios reconciled")
                return self._send(200, preview)
            if u.path == "/api/portfolios/upload":
                raw = self._json_body()
                msg = BytesParser(policy=policy.default).parsebytes(b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\n\r\n" + raw)
                saved = []
                for part in msg.iter_parts():
                    fn = part.get_filename()
                    if not fn:
                        continue
                    fn = Path(fn).name
                    if Path(fn).suffix.lower() not in (".xlsx", ".xls", ".xlsm", ".csv"):
                        continue
                    (PORTFOLIO_DIR / fn).write_bytes(part.get_payload(decode=True))
                    saved.append(fn)
                log.info("Portfolio files uploaded: %s", saved)
                ledger.audit(user, "PORTFOLIO_UPLOAD", None, saved)
                return self._send(200, {"saved": saved, "scan": scan_summary(scan())})
            if u.path == "/api/portfolios/apply":
                n = apply_portfolios(self._body().get("assign", []))
                ok = run_job("portfolios", lambda p: build_dataset.build(fetch=True, progress=p)) if n else False
                ledger.audit(user, "PORTFOLIO_APPLY", None, {"applied": n})
                return self._send(202 if ok else 200, {"applied": n, "started": ok})
            if u.path == "/api/users":
                b = self._body()
                if b.get("action") == "create":
                    auth.create_user(b.get("user"), b.get("password"), b.get("role"), user)
                elif b.get("action") == "update":
                    if b.get("user") == user and (b.get("active") is False or (b.get("role") and b.get("role") != "admin")):
                        return self._send(400, {"error": "You cannot disable or demote your own account."})
                    auth.update_user(b.get("user"), user, role=b.get("role"), active=b.get("active"), password=b.get("password"))
                else:
                    return self._send(400, {"error": "Unknown action."})
                return self._send(200, {"ok": True, "users": auth.list_users()})
            if u.path == "/api/schemes":
                b = self._body()
                act = b.get("action")
                with job_slot("entry"):
                    if act == "add":
                        result = ledger.add_scheme(b, user, config("schemes"), S.amfi_navall(), nav_months)
                    elif act == "update":
                        result = ledger.update_scheme(b.get("scheme_id"), b, user)
                    elif act == "delete":
                        result = ledger.delete_scheme(b.get("scheme_id"), user)
                    else:
                        return self._send(400, {"error": "Unknown action."})
                    build_dataset.build(fetch=False)
                    if act == "add" and not any(x["scheme_id"] == result["scheme_id"] for x in current_dataset()["schemes"]):
                        ledger.delete_scheme(result["scheme_id"], user)  # the build could not price it: undo rather than keep a phantom
                        build_dataset.build(fetch=False)
                        return self._send(400, {"error": "The scheme was added but its NAV history could not be built, so it was removed again. Try again later."})
                return self._send(200, {"ok": True, "record": result})
            if u.path in ("/api/entities", "/api/transactions", "/api/settings"):
                b = self._body()
                with job_slot("entry"):
                    ds = current_dataset()
                    act = b.get("action")
                    if u.path == "/api/entities":
                        rec = {"add": lambda: ledger.add_member(b, user, ds["members_demo"]),
                               "update": lambda: ledger.update_member(b.get("member_id"), b, user),
                               "delete": lambda: ledger.delete_member(b.get("member_id"), user)}.get(act)
                    elif u.path == "/api/transactions":
                        rec = {"add": lambda: ledger.add_txn(b, user, ds), "update": lambda: ledger.update_txn(b.get("txn_id"), b, user, ds),
                               "delete": lambda: ledger.delete_txn(b.get("txn_id"), user, ds),
                               "import": lambda: ledger.add_txns(b.get("trades"), user, ds, b.get("ref"), b.get("kind") or "contract_note")}.get(act)
                    else:
                        rec = lambda: ledger.set_demo(b.get("include_demo_family"), user, ds)  # noqa: E731
                    if rec is None:
                        return self._send(400, {"error": "Unknown action."})
                    result = rec()
                    build_dataset.build(fetch=False)
                return self._send(200, {"ok": True, "record": result})
            return self._send(404, {"error": "not found"})
        except (ledger.LedgerError, auth.AuthError) as e:
            return self._send(400, {"error": str(e)})
        except JobBusy as e:
            return self._send(409, {"error": str(e)})
        except json.JSONDecodeError:
            return self._send(400, {"error": "Request body is not valid JSON."})
        except Exception as e:  # noqa: BLE001
            log.error(traceback.format_exc())
            return self._send(500, {"error": str(e)})


LOGIN_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>LookThrough - sign in</title>
<link rel="manifest" href="/manifest.webmanifest"><link rel="icon" href="/icons/icon-192.png"><link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">
<meta name="theme-color" content="#F4F5F7" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#0B0F16" media="(prefers-color-scheme: dark)">
<style>
:root{color-scheme:light dark;--bg:#f4f5f7;--card:#fff;--ink:#1d2939;--muted:#667085;--line:#d0d5dd;--edge:#858FA0;--acc:#0e7c86;--acc-ink:#fff;--bad:#b42318}
@media (prefers-color-scheme:dark){:root{--bg:#0f1720;--card:#16202b;--ink:#e6e9ee;--muted:#98a2b3;--line:#2b3a4a;--edge:#5E6E89;--acc:#35b3bd;--acc-ink:#04181b;--bad:#f97066}}
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--ink);font:15px/1.5 "Segoe UI",system-ui,Arial,sans-serif}
.card{width:min(380px,calc(100vw - 32px));background:var(--card);border:1px solid var(--line);border-radius:12px;padding:28px}
.mk{display:inline-grid;place-items:center;width:36px;height:36px;border-radius:9px;background:linear-gradient(135deg,#0e7c86,#35b3bd);color:#fff;font-weight:700;margin-bottom:10px}
h1{font-size:19px;margin:0 0 4px}p{margin:0 0 18px;color:var(--muted);font-size:13.5px}
label{display:block;font-size:13px;margin:12px 0 4px}input{width:100%;padding:10px 12px;border:1px solid var(--edge);border-radius:8px;background:transparent;color:var(--ink);font:inherit;font-size:16px}
input:focus{outline:2px solid var(--acc);outline-offset:1px}button{margin-top:18px;width:100%;padding:11px;border:0;border-radius:8px;background:var(--acc);color:var(--acc-ink);font:inherit;font-weight:600;font-size:15px;cursor:pointer}
button:disabled{opacity:.6;cursor:wait}.err{color:var(--bad);font-size:13.5px;min-height:20px;margin-top:12px}.foot{margin-top:18px;font-size:12px;color:var(--muted)}
</style></head><body><main class="card"><div class="mk" aria-hidden="true">LT</div><h1 id="t">Sign in to LookThrough</h1><p id="s">Family office portfolio intelligence</p>
<form id="f" novalidate><label for="u">User name</label><input id="u" autocomplete="username" required>
<label for="p">Password</label><input id="p" type="password" autocomplete="current-password" required>
<div id="c2" hidden><label for="p2">Confirm password</label><input id="p2" type="password" autocomplete="new-password" maxlength="8"></div>
<button id="b" type="submit">Sign in</button><div class="err" id="e" role="alert"></div></form>
<div class="foot">Forgot the password, or account locked? On this PC, double-click <b>Reset_Password.bat</b> in the LookThrough folder.<br>Runs on this PC only (127.0.0.1). Decision support, not investment advice.</div></main>
<script>
var setup=false;
if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js').catch(function(){})}
var q=new URLSearchParams(location.search);if(q.get('idle')){var e0=document.getElementById('e');e0.style.color='var(--muted)';e0.textContent='Signed out after about '+(parseInt(q.get('idle'),10)||30)+' minutes without activity. Sign in again.'}
fetch('/api/auth-state').then(function(r){return r.json()}).then(function(s){
  if(s.signed_in){location.href='/';return}
  if(s.setup_needed){setup=true;document.getElementById('t').textContent='Create the admin account';
    document.getElementById('s').textContent='First run: this account can add users, entities and transactions. Password: 6 to 8 characters, upper and lower case, and a digit.';
    document.getElementById('c2').hidden=false;document.getElementById('p').autocomplete='new-password';document.getElementById('b').textContent='Create account and sign in'}
});
document.getElementById('f').addEventListener('submit',function(ev){ev.preventDefault();
  var u=document.getElementById('u').value.trim(),p=document.getElementById('p').value,e=document.getElementById('e'),b=document.getElementById('b');
  e.textContent='';if(!u||!p){e.textContent='Enter your user name and password.';return}
  if(setup&&p!==document.getElementById('p2').value){e.textContent='The passwords do not match.';return}
  b.disabled=true;fetch(setup?'/api/setup':'/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:u,password:p})})
  .then(function(r){return r.json().then(function(j){return {ok:r.ok,j:j}})}).then(function(x){if(x.ok){location.href='/'}else{e.textContent=x.j.error||'Sign-in failed.';b.disabled=false}})
  .catch(function(){e.textContent='The data bridge is not responding.';b.disabled=false});
});
</script></body></html>"""
LOGIN_CSP = page_csp(LOGIN_PAGE)  # the sign-in page's own inline script, by hash


def browser_command(url):
    """Command that opens url in Chrome, else Edge, else None (use the system default).

    The system default is not trusted on corporate PCs: Edge can be forced into Internet Explorer
    mode for localhost, where the app cannot run. Chrome is preferred; Edge is the fallback (the app
    shows an explanatory notice if IE mode still applies)."""
    import os
    import shutil
    pf, pf86, local = os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", ""), os.environ.get("LOCALAPPDATA", "")
    candidates = [
        Path(pf) / "Google/Chrome/Application/chrome.exe", Path(pf86) / "Google/Chrome/Application/chrome.exe",
        Path(local) / "Google/Chrome/Application/chrome.exe",
        Path(pf86) / "Microsoft/Edge/Application/msedge.exe", Path(pf) / "Microsoft/Edge/Application/msedge.exe",
    ]
    for exe in candidates:
        if str(exe) not in (".", "") and exe.is_file():
            return [str(exe), url]
    for name in ("google-chrome", "chromium", "chrome", "msedge"):  # non-Windows or unusual installs
        found = shutil.which(name)
        if found:
            return [found, url]
    return None


def open_in_browser(url):
    import subprocess
    cmd = browser_command(url)
    try:
        if cmd:
            subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log.info("Opened %s in %s", url, Path(cmd[0]).stem)
            return
    except OSError as e:
        log.warning("Could not start %s (%s); using the default browser", cmd[0], e)
    webbrowser.open(url)


class ExclusiveServer(ThreadingHTTPServer):
    """Owns its port outright. The stock server sets SO_REUSEADDR, which on Windows lets a SECOND bridge bind the
    same port silently; requests then reach whichever process Windows picks, e.g. an old bridge without sign-in."""
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        import socket
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def probe_port(p):
    """What is already listening on port p: 'current' (this same bridge code, running), 'stale' (a LookThrough bridge
    with sign-in but an earlier build of the code), 'old' (an earlier bridge without sign-in) or 'other'."""
    import urllib.error
    import urllib.request

    def get(path):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{p}{path}", timeout=2) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, None
        except Exception:  # noqa: BLE001 - anything unreadable is simply not a bridge
            return None, None

    code, body = get("/api/auth-state")
    if code == 200 and isinstance(body, dict) and "setup_needed" in body:
        return "current" if body.get("code") == CODE_ID else "stale"
    code, body = get("/api/status")
    if code == 200 and isinstance(body, dict) and "version" in body:
        return "old"
    return "other"


def serve(port=8765, open_browser=True):
    httpd = None
    for p in range(port, port + 10):
        try:
            httpd = ExclusiveServer(("127.0.0.1", p), Handler)
            break
        except OSError:
            kind = probe_port(p)
            if kind == "current":
                url = f"http://localhost:{p}/"
                log.info("LookThrough is already running at %s; opening it. This window can be closed.", url)
                if open_browser:
                    open_in_browser(url)
                return
            if kind == "stale":
                raise SystemExit(
                    f"\n  An EARLIER BUILD of the LookThrough Data Bridge is still running on port {p}, so recent changes\n"
                    "  would not take effect. Close every 'LookThrough Data Bridge' window (or end python.exe in Task\n"
                    "  Manager), then run Start_LookThrough.bat again.\n")
            if kind == "old":
                raise SystemExit(
                    f"\n  An OLDER LookThrough Data Bridge (without sign-in and data entry) is still running on port {p}.\n"
                    "  Close every 'LookThrough Data Bridge' window (or end python.exe in Task Manager), then run\n"
                    "  Start_LookThrough.bat again.\n")
            continue
    if httpd is None:
        raise SystemExit("No free port between 8765 and 8774")
    if not APP_OUT.exists():
        build_dataset.build_empty()
    url = f"http://localhost:{httpd.server_port}/"
    log.info("LookThrough Data Bridge %s running at %s  (close this window to stop)", VERSION, url)
    if not (LIVE / "dataset.json").exists():
        log.info("No live dataset yet: starting the first refresh in the background.")
        run_job("refresh", lambda pr: build_dataset.build(fetch=True, progress=pr))
    if open_browser:
        threading.Timer(1.0, lambda: open_in_browser(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "serve"
    if cmd == "serve":
        serve(open_browser="--no-browser" not in argv)
    elif cmd == "refresh":
        build_dataset.build(fetch=True, progress=log.info)
    elif cmd == "build":
        build_dataset.build(fetch=False, progress=log.info)
    elif cmd == "empty":
        build_dataset.build_empty()
    elif cmd == "scan":
        for r in scan_summary(scan()):
            print(f"{r['file']} [{r['sheet']}] -> {r['scheme_id']} {r['portfolio_date']} n={r['n']} eq={r['equity_pct']} warn={r['warnings']}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
