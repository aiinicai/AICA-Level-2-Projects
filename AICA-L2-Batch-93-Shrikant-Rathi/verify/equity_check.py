"""
Adding listed companies to the security master: validation, pricing rule, statements optional, use, sector edit, removal.

Runs the real bridge in-process with everything it writes redirected to a temporary folder (as bridge_check.py).
Deterministic and offline: NSE's list comes from the cache; the prices and statements of the test symbols are
synthetic and are supplied in memory (sources.price_cache / company_cache / yahoo_prices / yahoo_company are patched),
so nothing is written to the real data/cache.

Usage:  python verify/equity_check.py
"""
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
from datetime import date, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="lt_equity_check_"))
os.environ["LOOKTHROUGH_USER_DIR"] = str(TMP / "user")
sys.path[:0] = [str(ROOT / "bridge"), str(ROOT / "verify")]
import build_dataset  # noqa: E402
import lookthrough_bridge as B  # noqa: E402
import sources as S  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   -> {detail}"))


DS0 = json.loads((ROOT / "data" / "live" / "dataset.json").read_text(encoding="utf-8"))
BY_SYM, _ = S.nse_equity_list()
have = {c["code"] for c in DS0["companies"]}
free = [s for s, v in sorted(BY_SYM.items()) if v["series"] == "EQ" and s not in have]
NOFIN, WITHFIN, TOONEW = free[0], free[1], free[2]  # three NSE equities not yet in the master
FUNDONLY = next(c["code"] for c in DS0["companies"] if c.get("origin") == "fund" and not c.get("price") and c["code"] in BY_SYM)


def synth_points(days):
    start = date(2026, 8, 31) - timedelta(days=days)
    return [[(start + timedelta(days=i)).isoformat(), round(500 * (1 + 0.0003 * i), 2)] for i in range(days + 1)]


SYNTH = {S.yahoo_ticker(NOFIN): synth_points(1200), S.yahoo_ticker(WITHFIN): synth_points(1200), S.yahoo_ticker(TOONEW): synth_points(140),
         S.yahoo_ticker(FUNDONLY): synth_points(1200)}
YEARS = [{"period_end": f"{y}-03-31", "fy": f"FY{y - 1}-{str(y)[2:]}", "revenue": 5e10 * (1 + 0.1 * k), "ebitda": 1e10, "depreciation": 2e9, "interest": 5e8,
          "pbt": 7.5e9, "tax": 1.9e9, "pat": 5.6e9, "total_assets": 6e10, "net_worth": 3e10, "total_debt": 5e9, "cash_eq": 4e9, "current_assets": 2e10,
          "current_liabilities": 1.2e10, "cfo": 7e9, "capex": -3e9, "shares": 1e8} for k, y in enumerate(range(2022, 2027))]
COS = {S.yahoo_ticker(NOFIN): {"info": {"industry": "Specialty Chemicals", "sector": "Basic Materials"}, "years": []},
       S.yahoo_ticker(WITHFIN): {"info": {"industry": "Auto Parts", "sector": "Consumer Cyclical", "sharesOutstanding": 1e8, "financialCurrency": "INR"}, "years": YEARS}}
_real_cache, _real_co_cache, _real_prices, _real_co = S.price_cache, S.company_cache, S.yahoo_prices, S.yahoo_company


FETCHED = set()  # synthetic tickers appear in the cache only once "downloaded", as with the real cache


def price_cache():
    c = dict(_real_cache())
    c.update({t: {"fetched": "2026-08-31T00:00:00", "points": p} for t, p in SYNTH.items() if t in FETCHED})
    return c


def yahoo_prices(tickers, start, end, refresh=False):
    if all(t in SYNTH for t in tickers):
        FETCHED.update(tickers)
        return {t: {"points": SYNTH[t]} for t in tickers}
    return _real_prices(tickers, start, end, refresh)


S.price_cache = price_cache
S.company_cache = lambda tk: COS.get(tk) or _real_co_cache(tk)
S.yahoo_prices = yahoo_prices
S.yahoo_company = lambda sym, refresh=False: COS.get(S.yahoo_ticker(sym)) or {"info": {}, "years": []}

(TMP / "live").mkdir()
shutil.copy(ROOT / "data" / "live" / "dataset.json", TMP / "live" / "dataset.json")
for mod in (build_dataset, B):
    mod.LIVE, mod.APP_OUT = TMP / "live", TMP / "app" / "LookThrough.html"
build_dataset.build(fetch=False)
httpd = ThreadingHTTPServer(("127.0.0.1", 0), B.Handler)
PORT = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()


class Client:
    def __init__(self):
        self.cookie = None

    def req(self, method, path, body=None):
        c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=180)
        h = {"Host": f"localhost:{PORT}"}
        if self.cookie:
            h["Cookie"] = self.cookie
        data = None
        if body is not None:
            data, h["Content-Type"] = json.dumps(body).encode(), "application/json"
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        out = r.read()
        sc = r.getheader("Set-Cookie")
        if sc:
            self.cookie = sc.split(";")[0]
        return r.status, (json.loads(out) if out else {})


def ds():
    return json.loads((TMP / "live" / "dataset.json").read_text(encoding="utf-8"))


def co(code):
    return next((c for c in ds()["companies"] if c["code"] == code), None)


admin, viewer = Client(), Client()
admin.req("POST", "/api/setup", {"user": "cio", "password": "Look2026"})
admin.req("POST", "/api/users", {"action": "create", "user": "view1", "password": "View2026", "role": "viewer"})
viewer.req("POST", "/api/login", {"user": "view1", "password": "View2026"})
_, j = admin.req("POST", "/api/entities", {"action": "add", "name": "Equity Test Client", "type": "Individual", "relationship": "Test"})
MID = j["record"]["member_id"]
cfg_before = {p.name: p.read_bytes() for p in (ROOT / "data" / "config").glob("*")}

# ------------------------------------------------------------------ validation
st, _ = viewer.req("POST", "/api/equities", {"action": "add", "symbol": NOFIN})
check("A viewer cannot add companies (analyst role)", st == 403, st)
st, j = admin.req("POST", "/api/equities", {"action": "add", "symbol": "ZZNOTLISTED"})
check("A symbol not on NSE's equity list is refused (BSE-only explained)", st == 400 and "not on NSE's equity list" in j["error"] and "BSE" in j["error"], (st, j))
st, j = admin.req("POST", "/api/equities", {"action": "add", "symbol": "HDFCBANK"})
check("A company already in the master is refused, saying it can be used directly", st == 400 and "already in the security master as HDFCBANK" in j["error"], (st, j))
st, j = admin.req("POST", "/api/equities", {"action": "add", "symbol": TOONEW})
check("A company with under 13 month-end prices is refused with the reason", st == 400 and "at least 13" in j["error"], (st, j))
st, j = admin.req("POST", "/api/equities", {"action": "add", "symbol": "bad sym!"})
check("A malformed symbol is refused", st == 400, (st, j))
st, j = admin.req("POST", "/api/equities", {"action": "add", "symbol": NOFIN, "sector": "Crypto"})
check("A sector outside the list is refused", st == 400 and "sector" in j["error"], (st, j))
check("Nothing was added by the refused attempts", not any(c.get("origin") == "user" for c in ds()["companies"]))

# ------------------------------------------------------------------ add
st, j = admin.req("POST", "/api/equities", {"action": "add", "symbol": NOFIN})
c1 = co(NOFIN)
check(f"{NOFIN} without statements is added: priced on the valuation date, not scored", st == 200 and c1 and c1["origin"] == "user" and c1["price"]
      and not c1["has_fin"] and any(p["code"] == NOFIN and p["date"] == ds()["meta"]["as_on"] for p in ds()["prices"]), (st, j, c1))
check("Its name and ISIN come from NSE's list; sector from Yahoo's classification", c1 and c1["isin"] == BY_SYM[NOFIN]["isin"] and c1["sector"] == "Metals & Mining", c1)
st, j = admin.req("POST", "/api/equities", {"action": "add", "symbol": WITHFIN, "sector": "Automobile"})
c2 = co(WITHFIN)
check(f"{WITHFIN} with statements is added with the chosen sector, ratios computed from 5 years", st == 200 and c2 and c2["has_fin"] and c2["sector"] == "Automobile"
      and sum(1 for f in ds()["financials"] if f["code"] == WITHFIN) == 5, (st, j, c2))
st, j = admin.req("POST", "/api/equities", {"action": "add", "symbol": NOFIN})
check("The same company cannot be added twice", st == 400 and "already in the security master" in j["error"], (st, j))

# ------------------------------------------------------------------ use, edit, remove
st, j = admin.req("POST", "/api/transactions", {"action": "add", "member_id": MID, "asset_type": "EQ", "instrument": NOFIN, "plan": "",
                                                  "txn_type": "Buy", "date": "2026-07-15", "units": 50, "price": 510})
check("A transaction can be recorded in the added company", st == 200, (st, j))
TXN = j.get("record", {}).get("txn_id")
st, j = admin.req("POST", "/api/equities", {"action": "delete", "symbol": NOFIN})
check("Removal is refused while a transaction uses the company", st == 400 and "delete them first" in j["error"], (st, j))
st, j = admin.req("POST", "/api/equities", {"action": "update", "symbol": NOFIN, "sector": "Chemicals"})
check("The sector of an added company can be corrected (it drives the sector limit)", st == 200 and co(NOFIN)["sector"] == "Chemicals", (st, j))
st, j = admin.req("POST", "/api/equities", {"action": "update", "symbol": "HDFCBANK", "sector": "Others"})
check("A research-universe company is read-only", st == 400 and "not a company you added" in j["error"], (st, j))
st, j = admin.req("POST", "/api/equities", {"action": "delete", "symbol": FUNDONLY})
check("A company held via funds (not added by a user) cannot be removed", st == 400 and "not a company you added" in j["error"], (st, j))
st, j = admin.req("POST", "/api/equities", {"action": "add", "symbol": FUNDONLY})
cf = co(FUNDONLY)
check(f"A fund holding known only by weight ({FUNDONLY}, unpriced) can be added: it is priced, kept once, and usable",
      st == 200 and cf and cf["price"] and sum(1 for c in ds()["companies"] if c["code"] == FUNDONLY) == 1, (st, j, cf))
st, j = admin.req("POST", "/api/transactions", {"action": "add", "member_id": MID, "asset_type": "EQ", "instrument": FUNDONLY, "plan": "",
                                                  "txn_type": "Buy", "date": "2026-07-15", "units": 10, "price": 500})
check(f"A transaction can be recorded in {FUNDONLY} once priced", st == 200, (st, j))
admin.req("POST", "/api/transactions", {"action": "delete", "txn_id": j.get("record", {}).get("txn_id")})
st, j = admin.req("POST", "/api/equities", {"action": "delete", "symbol": FUNDONLY})
check(f"Removing it returns {FUNDONLY} to a fund holding (kept for look-through; its fetched prices stay cached)",
      st == 200 and co(FUNDONLY) and co(FUNDONLY)["origin"] == "fund", (st, j, co(FUNDONLY)))
admin.req("POST", "/api/transactions", {"action": "delete", "txn_id": TXN})
st, j = admin.req("POST", "/api/equities", {"action": "delete", "symbol": NOFIN})
check("Once unused, the added company is removed and leaves the master", st == 200 and co(NOFIN) is None, (st, j))
audit_raw = (TMP / "user" / "audit.jsonl").read_text(encoding="utf-8")
check("Add, edit and removal are audited", all(a in audit_raw for a in ('"COMPANY_ADD"', '"COMPANY_EDIT"', '"COMPANY_DELETE"')))
check("Added companies are kept in data/user, not in the committed data/config",
      {p.name: p.read_bytes() for p in (ROOT / "data" / "config").glob("*")} == cfg_before and not (ROOT / "data" / "config" / "user_universe.json").exists())

httpd.shutdown()
S.price_cache, S.company_cache, S.yahoo_prices, S.yahoo_company = _real_cache, _real_co_cache, _real_prices, _real_co
shutil.rmtree(TMP, ignore_errors=True)
n = sum(results)
line = f"{n}/{len(results)} equity checks passed"
print("\n" + line)
(ROOT / "verify" / "equity_result.txt").write_text(line + "\n", encoding="utf-8")
sys.exit(0 if all(results) else 1)
