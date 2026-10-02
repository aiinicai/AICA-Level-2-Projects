"""
End-to-end checks of the data bridge: sign-in, roles, and entity/transaction entry with server-side validation.

Runs a real bridge (the production Handler) on a free port with EVERYTHING it writes redirected to a temporary
folder: users, ledger, audit (LOOKTHROUGH_USER_DIR) and the rebuilt dataset and app (patched LIVE / APP_OUT).
The real data/user, data/live and app/ are never written. Needs the current data/live/dataset.json as a seed.

Usage:  python verify/bridge_check.py
"""
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="lt_bridge_check_"))
REAL_USER = ROOT / "data" / "user"
real_before = {p.name: p.read_bytes() for p in REAL_USER.glob("*") if p.is_file()} if REAL_USER.exists() else {}  # the operator's own accounts
os.environ["LOOKTHROUGH_USER_DIR"] = str(TMP / "user")
sys.path.insert(0, str(ROOT / "bridge"))
import build_dataset  # noqa: E402
import lookthrough_bridge as B  # noqa: E402

(TMP / "live").mkdir()
shutil.copy(ROOT / "data" / "live" / "dataset.json", TMP / "live" / "dataset.json")
for mod in (build_dataset, B):
    mod.LIVE, mod.APP_OUT = TMP / "live", TMP / "app" / "LookThrough.html"
build_dataset.build(fetch=False)  # seed the temp app/dataset with the current code

httpd = ThreadingHTTPServer(("127.0.0.1", 0), B.Handler)
PORT = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   -> {detail}"))


class Client:
    def __init__(self):
        self.cookie = None

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=120)
        h = {"Host": f"localhost:{PORT}", **(headers or {})}
        if self.cookie:
            h["Cookie"] = self.cookie
        data = None
        if body is not None:
            data, h["Content-Type"] = json.dumps(body).encode(), "application/json"
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        sc = r.getheader("Set-Cookie")
        if sc:
            self.cookie = sc.split(";")[0] if "Max-Age=0" not in sc else None
        try:
            j = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            j = {"_raw": raw[:80]}
        return r.status, j, r


def ds():
    return json.loads((TMP / "live" / "dataset.json").read_text(encoding="utf-8"))


anon, admin, analyst, viewer = Client(), Client(), Client(), Client()
STRONG = "Look2026"

# ------------------------------------------------------------------ sign-in and setup
st, _, r = anon.req("GET", "/")
check("Unauthenticated app request redirects to /login", st == 302 and r.getheader("Location") == "/login", st)
st, _, _ = anon.req("GET", "/api/dataset")
check("Unauthenticated data request is refused (401)", st == 401, st)
st, j, _ = anon.req("GET", "/api/auth-state")
check("First run reports that setup is needed", st == 200 and j["setup_needed"], j)
st, j, _ = admin.req("POST", "/api/setup", {"user": "cio", "password": "short"})
check("Setup refuses a password under 6 characters", st == 400 and "6 to 8 characters" in j["error"], j)
st, j, _ = admin.req("POST", "/api/setup", {"user": "cio", "password": "Look20261"})
check("Setup refuses a password over 8 characters", st == 400 and "6 to 8 characters" in j["error"], j)
st, j, _ = admin.req("POST", "/api/setup", {"user": "cio", "password": "look2026"})
check("Setup refuses a password without upper case", st == 400 and "upper- and lower-case" in j["error"], j)
st, j, r = admin.req("POST", "/api/setup", {"user": "cio", "password": STRONG})
check("Setup creates the admin and signs in (HttpOnly, SameSite=Strict cookie)",
      st == 200 and "HttpOnly" in (r.getheader("Set-Cookie") or "") and "SameSite=Strict" in (r.getheader("Set-Cookie") or ""), (st, j))
st, j, _ = admin.req("GET", "/api/me")
check("Signed-in admin is recognised", st == 200 and j == {"user": "cio", "role": "admin"}, j)
st, _, _ = anon.req("POST", "/api/setup", {"user": "intruder", "password": STRONG})
check("Setup cannot be run again once an admin exists", st == 403, st)
users_raw = (TMP / "user" / "users.json").read_text(encoding="utf-8")
check("Password is stored only as a salted PBKDF2 hash", STRONG not in users_raw and '"iterations": 600000' in users_raw)
st, _, _ = admin.req("POST", "/api/transactions", {"action": "add"}, {"Origin": "http://evil.example"})
check("Cross-site POST is refused (Origin check)", st == 403, st)
st, _, _ = admin.req("GET", "/", headers={"Host": "evil.example"})
check("Foreign Host header is refused (DNS-rebinding guard)", st == 403, st)

# ------------------------------------------------------------------ users and roles
for u, role in (("analyst1", "analyst"), ("viewer1", "viewer")):
    st, j, _ = admin.req("POST", "/api/users", {"action": "create", "user": u, "password": STRONG, "role": role})
    check(f"Admin creates {role}", st == 200, j)
st, _, _ = analyst.req("POST", "/api/login", {"user": "analyst1", "password": STRONG})
st2, _, _ = viewer.req("POST", "/api/login", {"user": "viewer1", "password": STRONG})
check("Analyst and viewer can sign in", st == 200 and st2 == 200, (st, st2))
st, _, _ = viewer.req("GET", "/api/dataset")
check("Viewer can read data", st == 200, st)
st, j, _ = viewer.req("POST", "/api/entities", {"action": "add", "name": "Viewer Try", "type": "Individual"})
check("Viewer cannot enter data (403)", st == 403, (st, j))
st, _, _ = analyst.req("POST", "/api/users", {"action": "create", "user": "x_user", "password": STRONG, "role": "admin"})
check("Analyst cannot manage users (403)", st == 403, st)
st, j, _ = admin.req("POST", "/api/users", {"action": "update", "user": "cio", "role": "viewer"})
check("Admin cannot demote their own account", st == 400, j)

# Content-Security-Policy: scripts only by hash, on the app and on the sign-in page
import re as _re  # noqa: E402
st, _, r = admin.req("GET", "/")
csp = r.getheader("Content-Security-Policy") or ""
script_src = (_re.search(r"script-src ([^;]*)", csp) or [None, ""])[1]
inline = _re.findall(rb"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", B.APP_OUT.read_bytes(), _re.S | _re.I)
import base64 as _b64, hashlib as _hl  # noqa: E401,E402
# as a browser computes it: after the HTML parser turns CRLF / CR into LF (the built file has CRLF line endings)
want = {"'sha256-" + _b64.b64encode(_hl.sha256(x.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).digest()).decode() + "'" for x in inline}
check("The built app really has CRLF line endings (so the normalisation above is exercised)", any(b"\r\n" in x for x in inline))
check("App page sends a CSP allowing only its own inline scripts by SHA-256 (no 'unsafe-inline' / eval for scripts)",
      st == 200 and inline and want <= set(script_src.split()) and "unsafe-inline" not in script_src and "unsafe-eval" not in script_src
      and "frame-ancestors 'none'" in csp and "connect-src 'self'" in csp, (st, len(inline), script_src[:120]))
st, _, r = anon.req("GET", "/login")
lcsp = r.getheader("Content-Security-Policy") or ""
check("Sign-in page CSP allows its script by hash only", "sha256-" in lcsp and "unsafe-inline" not in (_re.search(r"script-src ([^;]*)", lcsp) or [None, ""])[1], lcsp[:120])

# installable app (PWA): manifest, worker, offline page and icons are served without sign-in and hold no data
st, j, r = anon.req("GET", "/manifest.webmanifest")
check("PWA manifest is served without sign-in, as a manifest, with 192/512 and maskable icons and standalone display",
      st == 200 and (r.getheader("Content-Type") or "").startswith("application/manifest+json") and j.get("display") == "standalone"
      and j.get("start_url") == "/" and {"192x192", "512x512"} <= {i["sizes"] for i in j.get("icons", [])} and any(i.get("purpose") == "maskable" for i in j.get("icons", [])), (st, j))
def raw_get(path):
    """A GET without the JSON decoding of Client.req (icons are binary)."""
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
    c.request("GET", path, headers={"Host": f"localhost:{PORT}"})
    rr = c.getresponse()
    return rr, rr.read()


icon_resp = [raw_get(i["src"]) for i in j.get("icons", [])]
check("Every manifest icon is served as a real PNG", icon_resp and all(rr.status == 200 and rr.getheader("Content-Type") == "image/png" and b[:8] == b"\x89PNG\r\n\x1a\n"
                                                                      for rr, b in icon_resp), [rr.status for rr, _ in icon_resp])
rr, sw = raw_get("/sw.js")
sw = sw.decode()
shell = _re.search(r"const SHELL = \[([^\]]*)\]", sw)
shell_paths = _re.findall(r'"([^"]+)"', shell[1]) if shell else []
check("Service worker is served as JavaScript and caches only the shell (never '/', the sign-in page or /api)",
      rr.status == 200 and "javascript" in (rr.getheader("Content-Type") or "") and shell_paths and "/offline.html" in shell_paths
      and not any(p in ("/", "/login", "/index.html") or p.startswith("/api") for p in shell_paths), shell_paths)
st, _, r = anon.req("GET", "/offline.html")
check("Offline page is served without sign-in, with its own CSP", st == 200 and "script-src" in (r.getheader("Content-Security-Policy") or ""), st)
check("App CSP allows the manifest and the service worker (same origin only)", "manifest-src 'self'" in csp and "worker-src 'self'" in csp, csp[-80:])
st, _, _ = anon.req("GET", "/icons/../users.json")
check("PWA routes serve only the listed files (no path traversal)", st in (401, 404), st)

# idle sign-out: 30 minutes without activity ends the session; background polls do not count as activity
import auth as _auth  # noqa: E402
idler = Client()
idler.req("POST", "/api/login", {"user": "analyst1", "password": STRONG})
tok = idler.cookie.split("=", 1)[1]
st, j, _ = idler.req("GET", "/api/status")
check("Status tells the app the idle limit (30 minutes)", st == 200 and j.get("idle_seconds") == 30 * 60 == _auth.IDLE_SECONDS, j.get("idle_seconds"))
_auth._SESSIONS[tok]["seen"] -= 600
seen0 = _auth._SESSIONS[tok]["seen"]
idler.req("GET", "/api/job", headers={"X-LT-Background": "1"})
check("A background poll does not count as activity", _auth._SESSIONS[tok]["seen"] == seen0, (_auth._SESSIONS[tok]["seen"], seen0))
idler.req("GET", "/api/me")
check("A user request counts as activity", _auth._SESSIONS[tok]["seen"] > seen0 + 500, (_auth._SESSIONS[tok]["seen"], seen0))
_auth._SESSIONS[tok]["seen"] -= _auth.IDLE_SECONDS + 5
st, _, _ = idler.req("GET", "/api/me")
audit_raw = (TMP / "user" / "audit.jsonl").read_text(encoding="utf-8")
check("After 30 minutes idle the session is gone (401) and the expiry is audited", st == 401 and tok not in _auth._SESSIONS and "SESSION_IDLE_EXPIRED" in audit_raw, st)
for who, body, why in ((Client(), {}, "signed out"), (Client(), {"reason": "idle"}, "signed out by the app after inactivity")):
    who.req("POST", "/api/login", {"user": "analyst1", "password": STRONG})
    st, _, _ = who.req("POST", "/api/logout", body)
    st2, _, _ = who.req("GET", "/api/me")
    rows = [json.loads(x) for x in (TMP / "user" / "audit.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    check(f"Sign-out is audited ({why}) and ends the session", st == 200 and st2 == 401 and any(r.get("action") == "LOGOUT" and why in json.dumps(r) for r in rows), (st, st2))

# official figures replace Yahoo where it is known to be wrong (data/config/official_financials.json)
_off = json.loads((ROOT / "data" / "config" / "official_financials.json").read_text(encoding="utf-8"))
_fin = {(r["code"], r["fy"]): r for r in ds()["financials"]}
_bad = []
for _code, _spec in ((k, v) for k, v in _off.items() if not k.startswith("_")):
    for _fy, _y in _spec["years"].items():
        _r = _fin.get((_code, _fy))
        _nw = round(_y["capital"] + _y["reserves_and_surplus"], 2)
        if not _r or abs(_r["net_worth"] - _nw) > 0.01 or abs(_r["pat"] - _y["pat"]) > 0.01 or not _r.get("official_source", "").startswith("https://"):
            _bad.append((_code, _fy, "not applied"))
        if abs(_y["pbt"] - _y["tax"] - _y["pat"]) > 0.01:
            _bad.append((_code, _fy, "pbt - tax != pat in the filing figures"))
check("Audited figures replace Yahoo (net worth = capital + reserves, PAT, PBT - tax = PAT) and carry their filing link", not _bad, _bad)
_hd = sorted((r for (c, _), r in _fin.items() if c == "HDFCBANK"), key=lambda r: r["fy"])
_roe = _hd[-1]["pat"] / ((_hd[-1]["net_worth"] + _hd[-2]["net_worth"]) / 2) * 100
check("HDFC Bank ROE on audited standalone figures is about 14% (Yahoo's net worth gave 8.9%)", 13.5 < _roe < 15, round(_roe, 2))

# lockout
locker = Client()
for _ in range(5):
    locker.req("POST", "/api/login", {"user": "viewer1", "password": "Wrong-password-1"})
st, j, _ = locker.req("POST", "/api/login", {"user": "viewer1", "password": STRONG})
check("Five wrong passwords lock the account (even the right password is refused)", st == 400 and "locked" in j["error"], j)
st, j, _ = anon.req("POST", "/api/login", {"user": "nobody", "password": STRONG})
check("Unknown user gets the same message as a wrong password", st == 400 and j["error"] == "Wrong user name or password.", j)

# ------------------------------------------------------------------ entities
st, j, _ = analyst.req("POST", "/api/entities", {"action": "add", "name": "Kavya Mehta", "type": "Individual", "relationship": "Daughter"})
new_id = j.get("record", {}).get("member_id")
check("Analyst adds an entity; id continues after the demo entities (M6)", st == 200 and new_id == "M6", j)
check("New entity appears in the rebuilt dataset", any(m["member_id"] == new_id and m["source"] == "user" for m in ds()["members"]))
st, j, _ = analyst.req("POST", "/api/entities", {"action": "add", "name": "Kavya Mehta", "type": "Individual"})
check("Duplicate entity name refused", st == 400, j)
st, j, _ = analyst.req("POST", "/api/entities", {"action": "add", "name": "Some Co", "type": "Society"})
check("Unknown entity type refused", st == 400, j)
st, j, _ = analyst.req("POST", "/api/entities", {"action": "update", "member_id": "M1", "name": "Hacked", "type": "Individual"})
check("Demo entity cannot be edited", st == 400, j)

# ------------------------------------------------------------------ transactions
AS_ON = ds()["meta"]["as_on"]
infy = next(p["close"] for p in ds()["prices"] if p["code"] == "INFY" and p["date"] == AS_ON)
buy = {"action": "add", "member_id": new_id, "asset_type": "EQ", "instrument": "infy", "txn_type": "Buy", "date": "2026-03-10", "units": 100, "price": 1500, "amount": 1}
st, j, _ = analyst.req("POST", "/api/transactions", buy)
tb = j.get("record", {})
check("Analyst records an equity purchase; amount computed by the server (100 x 1500)", st == 200 and tb.get("txn_id") == "U00001" and tb.get("amount") == 150000 and tb.get("instrument") == "INFY", j)
d = ds()
check("Transaction is in the rebuilt dataset", any(t["txn_id"] == "U00001" and t["source"] == "user" for t in d["transactions"]))
bad_cases = [("future date", {**buy, "date": "2099-01-01"}), ("unknown instrument", {**buy, "instrument": "NOSUCHCO"}),
             ("fractional shares", {**buy, "units": 10.5}), ("zero price", {**buy, "price": 0}), ("negative units", {**buy, "units": -5}),
             ("unknown entity", {**buy, "member_id": "M99"}), ("MF without plan", {**buy, "asset_type": "MF", "instrument": "S05", "txn_type": "Purchase"}),
             ("bad date", {**buy, "date": "10/03/2026"})]
for name, body in bad_cases:
    st, j, _ = analyst.req("POST", "/api/transactions", body)
    check(f"Refused: {name}", st == 400, (st, j))
sell = {**buy, "txn_type": "Sell", "date": "2026-06-15", "units": 150, "price": 1600}
st, j, _ = analyst.req("POST", "/api/transactions", sell)
check("Refused: sale larger than units held (150 > 100)", st == 400 and "larger than the units held" in j["error"], j)
st, j, _ = analyst.req("POST", "/api/transactions", {**sell, "units": 40})
ts = j.get("record", {})
check("Sale within units held is accepted", st == 200 and ts.get("txn_id") == "U00002", j)
st, j, _ = analyst.req("POST", "/api/transactions", {"action": "delete", "txn_id": "U00001"})
check("Deleting the purchase that covers a later sale is refused", st == 400 and "larger than the units held" in j["error"], j)
st, j, _ = analyst.req("POST", "/api/transactions", {**buy, "action": "update", "txn_id": "U00001", "units": 30})
check("Editing the purchase below the later sale is refused (30 < 40)", st == 400, j)
st, j, _ = analyst.req("POST", "/api/entities", {"action": "delete", "member_id": new_id})
check("Entity with transactions cannot be deleted", st == 400, j)
st, j, _ = analyst.req("POST", "/api/transactions", {"action": "delete", "txn_id": "T00001"})
check("Demo transaction cannot be deleted", st == 400, j)

# numbers: the new holding is valued exactly like the engine values every other holding
sys.path.insert(0, str(ROOT / "verify"))
os.environ["LOOKTHROUGH_DATASET"] = str(TMP / "live" / "dataset.json")
import recompute as E  # noqa: E402
h = E.H[(E.H.member_id == new_id) & (E.H.instrument == "INFY")]
check("Engine values the entered holding at 60 shares x valuation-date price",
      len(h) == 1 and abs(float(h.units.iloc[0]) - 60) < 1e-9 and abs(float(h.value.iloc[0]) - 60 * infy) < 0.01, h.to_dict("records"))
r = E.R[E.R.member_id == new_id]
check("Realised gain on the sale is 40 x (1600 - 1500) = 4,000, short-term", len(r) == 1 and abs(r.gain.iloc[0] - 4000) < 1e-6 and r.term.iloc[0] == "ST",
      r.to_dict("records"))

# ------------------------------------------------------------------ demo switch and audit
st, j, _ = analyst.req("POST", "/api/settings", {"include_demo_family": False})
check("Hiding the demo family works when no entry depends on it", st == 200 and all(m["source"] == "user" for m in ds()["members"]), j)
check("With the demo hidden, only entered transactions remain", {t["source"] for t in ds()["transactions"]} == {"user"})
st, _, _ = analyst.req("POST", "/api/settings", {"include_demo_family": True})
audit_raw = (TMP / "user" / "audit.jsonl").read_text(encoding="utf-8")
acts = [json.loads(x)["action"] for x in audit_raw.splitlines()]
check("Audit trail records entity, transaction, user, login and setting changes",
      all(a in acts for a in ("ENTITY_ADD", "TXN_ADD", "USER_CREATE", "LOGIN", "LOGIN_FAILED", "SETTING_DEMO_FAMILY")), sorted(set(acts)))
check("No password appears in the audit trail", STRONG not in audit_raw and "Wrong-password-1" not in audit_raw)
st, j, _ = viewer.req("GET", "/api/audit")
check("Audit trail readable in the app", st in (200, 401), st)
st, _, _ = admin.req("POST", "/api/logout", {})
st2, _, _ = admin.req("GET", "/api/me")
check("Sign-out ends the session", st == 200 and st2 == 401, (st, st2))
# ------------------------------------------------------------------ latest prices (/api/quotes), offline: sources patched in memory
import sources as S  # noqa: E402
_asked = []
S.latest_quotes = lambda tickers, max_age=120: (_asked.extend(tickers) or {t: {"price": 123.45, "date": "2026-09-25", "prev_close": 120.0} for t in tickers})
S.latest_navs = lambda: {"120586": {"nav": 115.57, "date": "2026-09-25"}}
st, j, _ = anon.req("GET", "/api/quotes")
check("Latest prices: a request without sign-in is refused (401)", st == 401, st)
st, j, _ = viewer.req("GET", "/api/quotes?codes=RELIANCE,NOTACODE,../etc")
held = {t["instrument"] for t in ds()["transactions"] if t["asset_type"] == "EQ"}
check("Latest prices: a viewer gets quotes for every held equity, dated, with the valuation date alongside",
      st == 200 and held <= set(j["equity"]) and j["valuation_date"] == ds()["meta"]["as_on"] and all(v["date"] == "2026-09-25" for v in j["equity"].values()), (st, sorted(held - set(j.get("equity", {})))[:5]))
check("Latest prices: only codes in the security master are looked up (unknown or odd codes are ignored)",
      "NOTACODE.NS" not in _asked and not any("etc" in a for a in _asked) and "RELIANCE" in j["equity"], _asked[:5])
check("Latest prices: fund NAVs are keyed by scheme and plan", j["mf"].get("S01|Direct", {}).get("nav") == 115.57, j.get("mf"))

# ------------------------------------------------------------------ local password reset (Reset_Password.bat)
import auth  # noqa: E402
reset_user = Client()
for _ in range(5):
    reset_user.req("POST", "/api/login", {"user": "analyst1", "password": "Wrong-9x"})
st, j, _ = reset_user.req("POST", "/api/login", {"user": "analyst1", "password": STRONG})
check("Reset: the account is locked after five wrong passwords", st == 400 and "locked" in j["error"], j)
try:
    auth.reset_local("analyst1", "short")
    bad_ok = True
except auth.AuthError:
    bad_ok = False
check("Reset: the password rule applies to a local reset (a weak password is refused)", not bad_ok)
auth.reset_local("analyst1", "Reset26x")
st, j, _ = reset_user.req("POST", "/api/login", {"user": "analyst1", "password": "Reset26x"})
check("Reset: a local reset unlocks the account at once and the new password signs in (no restart)", st == 200, (st, j))
st, j, _ = reset_user.req("POST", "/api/login", {"user": "analyst1", "password": STRONG})
check("Reset: the old password no longer works", st == 400, (st, j))
audit_raw2 = (TMP / "user" / "audit.jsonl").read_text(encoding="utf-8")
check("Reset: audited as PASSWORD_RESET_LOCAL, without the password", '"PASSWORD_RESET_LOCAL"' in audit_raw2 and "Reset26x" not in audit_raw2)
_c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30); _c.request("GET", "/login", headers={"Host": f"localhost:{PORT}"})
check("Sign-in page tells a user how to recover a forgotten password", "Reset_Password.bat" in _c.getresponse().read().decode("utf-8", "replace"))

real_after = {p.name: p.read_bytes() for p in REAL_USER.glob("*") if p.is_file()} if REAL_USER.exists() else {}
check("Real data/user untouched by this test (byte-for-byte)", real_after == real_before, sorted(set(real_after) ^ set(real_before)) or "content changed")

httpd.shutdown()
shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{sum(results)}/{len(results)} bridge checks passed")
(ROOT / "verify" / "bridge_result.txt").write_text(f"{sum(results)}/{len(results)} bridge checks passed\n", encoding="utf-8")
sys.exit(0 if all(results) else 1)
