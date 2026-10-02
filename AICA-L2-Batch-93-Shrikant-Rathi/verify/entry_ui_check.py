"""
Browser test of sign-in and data entry through the real UI, against a bridge whose writes all go to a temp folder.

Starts the production bridge Handler on a free port (users, ledger, audit, dataset and app redirected to a temp
directory; the real data/ and app/ are not written), then runs verify/entry_ui.js in Chrome via Playwright.
Usage:  python verify/entry_ui_check.py [--shots DIR]
"""
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="lt_entry_ui_"))
os.environ["LOOKTHROUGH_USER_DIR"] = str(TMP / "user")
sys.path.insert(0, str(ROOT / "bridge"))
import build_dataset  # noqa: E402
import lookthrough_bridge as B  # noqa: E402

(TMP / "live").mkdir()
shutil.copy(ROOT / "data" / "live" / "dataset.json", TMP / "live" / "dataset.json")
for mod in (build_dataset, B):
    mod.LIVE, mod.APP_OUT = TMP / "live", TMP / "app" / "LookThrough.html"
build_dataset.build(fetch=False)
sys.path.insert(0, str(ROOT / "verify"))
import contract_note_fixtures as FX  # noqa: E402
(TMP / "note_a.pdf").write_bytes(FX.encrypted(FX.layout_a()[0]))  # fictitious note, password FX.PASSWORD
os.environ["CN_PDF"], os.environ["CN_PW"] = str(TMP / "note_a.pdf"), FX.PASSWORD
import cas_fixtures as CF  # noqa: E402
(TMP / "cas.pdf").write_bytes(CF.encrypted(CF.build()[0], CF.PASSWORD))  # fictitious CAS
os.environ["CAS_PDF"], os.environ["CAS_PW"] = str(TMP / "cas.pdf"), CF.PASSWORD
# offline and deterministic: synthetic NAV history for the scheme the UI test adds (Quant Small Cap, Direct/Regular)
import sources as S  # noqa: E402
from datetime import date, timedelta  # noqa: E402
_real_hist = S.mf_nav_history


def _fake_hist(code, refresh=False):
    if code not in ("120828", "100177"):
        return _real_hist(code, refresh)
    start = date(2026, 8, 31) - timedelta(days=1200)
    rows = [{"date": (start + timedelta(days=i)).strftime("%d-%m-%Y"), "nav": f"{250 * (1 + 0.0004 * i):.4f}"} for i in range(1201)]
    return {"meta": {"scheme_name": code}, "data": rows[::-1]}


S.mf_nav_history = _fake_hist

# a listed company not yet in the master, with synthetic prices supplied in memory once "downloaded" (nothing cached)
import json as _json  # noqa: E402
_have = {c["code"] for c in _json.loads((ROOT / "data" / "live" / "dataset.json").read_text(encoding="utf-8"))["companies"]}
_by, _ = S.nse_equity_list()
EQ_SYM = next(s for s, v in sorted(_by.items()) if v["series"] == "EQ" and s not in _have)
_tk, _fetched = S.yahoo_ticker(EQ_SYM), set()
_pts = [[(date(2026, 8, 31) - timedelta(days=1200 - i)).isoformat(), round(400 * (1 + 0.0003 * i), 2)] for i in range(1201)]
_real_pc, _real_yp, _real_yc = S.price_cache, S.yahoo_prices, S.yahoo_company
S.price_cache = lambda: {**_real_pc(), **({_tk: {"fetched": "2026-08-31", "points": _pts}} if _tk in _fetched else {})}
S.yahoo_prices = lambda t, start, end, refresh=False: (_fetched.update(t) or {_tk: {"points": _pts}}) if t == [_tk] else _real_yp(t, start, end, refresh)
S.yahoo_company = lambda sym, refresh=False: {"info": {"sector": "Industrials", "industry": "Engineering"}, "years": []} if sym == EQ_SYM else _real_yc(sym, refresh)
os.environ["EQ_SYM"] = EQ_SYM

# latest prices, offline and deterministic: every quote is 5% above its valuation-date price, dated 25-Sep-2026
_ds0 = _json.loads((ROOT / "data" / "live" / "dataset.json").read_text(encoding="utf-8"))
_px = {S.yahoo_ticker(c["code"]): c["price"] for c in _ds0["companies"] if c.get("price")}
_nv = {}
for _s in _ds0["schemes"]:
    for _plan, _code in (("Direct", _s.get("amfi_code")), ("Regular", _s.get("amfi_code_regular"))):
        _last = [n["nav"] for n in _ds0["nav_history"] if n["scheme_id"] == _s["scheme_id"] and n["plan"] == _plan and n["date"] == _ds0["meta"]["as_on"]]
        if _code and _last:
            _nv[_code] = {"nav": round(_last[0] * 1.05, 4), "date": "2026-09-25"}
S.latest_quotes = lambda tickers, max_age=120: {t: {"price": round(_px[t] * 1.05, 2), "date": "2026-09-25", "prev_close": _px[t]} for t in tickers if t in _px}
S.latest_navs = lambda: _nv
httpd = ThreadingHTTPServer(("127.0.0.1", 0), B.Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
args = ["node", str(ROOT / "verify" / "entry_ui.js"), str(httpd.server_address[1])] + sys.argv[1:]
code = subprocess.run(args, cwd=ROOT / "verify").returncode
httpd.shutdown()
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(code)
