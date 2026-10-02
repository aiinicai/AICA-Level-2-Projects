"""
Holdings-lag check: early in a month, fund holdings are a month older than the prices.

AMCs publish a month's portfolio within about 10 days of month-end, so for the first days of every month the latest
disclosure is for the month before the valuation date. Look-through still uses it (it is the best available), but the
app and the MCP tools must SAY so. This check builds a lagged copy of the live dataset (latest month's holdings removed)
and proves:

  * every look-through screen (dashboard, look-through, overlap, concentration, stress, family report) shows the
    warning and names both dates; the dashboard alerts and the Data & controls check flag it;
  * portfolio_summary, look_through_exposure and policy_check return the holdings date and a caveat;
  * on the current dataset (holdings for the valuation month) none of the warnings appears (negative control),
    while the subtitles still name the holdings date.

Usage:  python verify/holdings_lag_check.py      (needs Chrome + verify/node_modules, like the other UI checks)
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bridge"))
LIVE = ROOT / "data" / "live" / "dataset.json"
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   -> {str(detail)[:400]}"))


def lagged(src, out):
    """The live dataset with the latest month's fund holdings removed: the state of the first days of a month."""
    d = json.loads(src.read_text(encoding="utf-8"))
    last = max(r["portfolio_date"] for r in d["scheme_portfolios"])
    d["scheme_portfolios"] = [r for r in d["scheme_portfolios"] if r["portfolio_date"] < last]
    prev = max(r["portfolio_date"] for r in d["scheme_portfolios"])
    for s in d["schemes"]:
        if s.get("portfolio_date") == last:
            s["portfolio_date"] = prev
    d["meta"]["portfolio_dates"] = sorted({r["portfolio_date"] for r in d["scheme_portfolios"]})
    out.mkdir(parents=True, exist_ok=True)
    (out / "dataset.json").write_text(json.dumps(d), encoding="utf-8")
    import build_dataset
    build_dataset.APP_OUT = out / "LookThrough.html"
    build_dataset.build_app(d)
    return d, prev


def ui(html):
    r = subprocess.run(["node", str(ROOT / "verify" / "holdings_lag_ui.js"), str(html)], cwd=ROOT / "verify", capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


MCP_PROBE = r"""
import json, sys
sys.path.insert(0, "mcp_server")
import lookthrough_mcp as T
out = {t: getattr(T, t)("ALL") for t in ("portfolio_summary", "look_through_exposure", "policy_check")}
print(json.dumps({t: {"basis": o["data"].get("holdings_basis"), "caveats": o["caveats"]} for t, o in out.items()}))
"""


def mcp(dataset):
    env = dict(os.environ, LOOKTHROUGH_DATASET=str(dataset))
    r = subprocess.run([sys.executable, "-c", MCP_PROBE], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def fmt(iso):
    y, m, d = iso.split("-")
    return f"{d} {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][int(m) - 1]} {y}"


tmp = Path(tempfile.mkdtemp(prefix="lt_lag_"))
d, prev = lagged(LIVE, tmp)
AS = d["meta"]["as_on"]
SCREENS = ("dashboard", "lookthrough", "overlap", "concentration", "stress", "report")

# ---------------------------------------------------------------- lagged: every surface says so
g = ui(tmp / "LookThrough.html")
check("Lagged: the app loads without script errors", not g["errors"], g["errors"])
miss = [v for v in SCREENS if not (fmt(prev) in g["screens"][v]["note"] and fmt(AS) in g["screens"][v]["note"])]
check(f"Lagged: all {len(SCREENS)} look-through screens warn, naming the holdings date ({fmt(prev)}) and the price date ({fmt(AS)})", not miss, miss)
check("Lagged: the family report header names the fund-holdings date", "Fund holdings " + fmt(prev) in g["report"], g["report"])
check("Lagged: a Data alert on the dashboard names both dates", any(fmt(prev) in a and fmt(AS) in a for a in g["alerts"]), g["alerts"])
check("Lagged: the Data & controls check 'Fund holdings are for the valuation month' is a warning",
      g["check"] and g["check"]["s"] == "warn" and fmt(prev) in g["check"]["d"], g["check"])
m = mcp(tmp / "dataset.json")
bad = [t for t, o in m.items() if not (o["basis"] and o["basis"]["fund_holdings_disclosed_on"] == prev and o["basis"]["prices_and_navs_at"] == AS
                                       and len(o["basis"]["funds_on_an_earlier_disclosure"]) > 0
                                       and any("older than the prices" in c and prev in c for c in o["caveats"]))]
check("Lagged: portfolio_summary, look_through_exposure and policy_check return the holdings date and a caveat", not bad, {t: m[t] for t in bad})

# ---------------------------------------------------------------- current: no false alarm, dates still named
c = ui(ROOT / "app" / "LookThrough.html")
cur = max(r["portfolio_date"] for r in json.loads(LIVE.read_text(encoding="utf-8"))["scheme_portfolios"])
if cur[:7] == c["asOn"][:7]:
    check("Current: no lag warning on any screen", not any(c["screens"][v]["note"] for v in SCREENS), {v: c["screens"][v]["note"][:80] for v in SCREENS})
    check("Current: no lag alert, and the valuation-month check passes", not any("prices from" in a for a in c["alerts"]) and c["check"] and c["check"]["s"] == "ok", (c["alerts"], c["check"]))
    check("Current: the dashboard and look-through subtitles name the fund-holdings date",
          all("fund holdings as disclosed on " + fmt(cur) in c["screens"][v]["head"] for v in ("dashboard", "lookthrough")), {v: c["screens"][v]["head"][-160:] for v in ("dashboard", "lookthrough")})
    m = mcp(LIVE)
    check("Current: the MCP tools return the holdings date and no lag caveat",
          all(o["basis"]["fund_holdings_disclosed_on"] == cur and not o["basis"]["funds_on_an_earlier_disclosure"] and not any("older than the prices" in x for x in o["caveats"]) for o in m.values()), m)
else:
    print(f"SKIP  current-data negative control: the live data itself is lagged ({cur} vs {c['asOn']})")

print(f"\n{sum(results)}/{len(results)} holdings-lag checks passed")
sys.exit(0 if all(results) else 1)
