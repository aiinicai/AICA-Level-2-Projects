"""
Latest-prices check: value, gain and the concentration limits at the latest prices, recomputed independently.

The app shows two price bases. The month-end valuation date drives returns, risk and the reconciliation; with the Data
Bridge running, value, gain and the concentration limits are also shown at the latest prices (shares from Yahoo, NAVs
from AMFI). This check hands the offline app a fixed set of quotes, exactly as /api/quotes returns them, and proves:

  * family and entity value, and gain, at latest prices = units x latest price, recomputed here in pandas;
  * a holding without a quote stays at its valuation-date price and is counted (never silently "no change");
  * the four concentration limits at latest prices (largest stock, largest sector, top 10, HHI) agree with the
    reference engine's look-through run on the revalued holdings; HDFC Bank's jump changes the result;
  * the screens show them with the price and NAV dates; the valuation-date figures are unchanged;
  * with no quotes (offline file) none of it appears.

Usage:  python verify/latest_prices_check.py      (needs Chrome + verify/node_modules, like the other UI checks)
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "verify"))
import recompute as E  # noqa: E402  - the reference engine (pandas), independent of the app's JavaScript

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   -> {str(detail)[:500]}"))


def close(a, b, tol=0.5):
    return a is not None and b is not None and abs(a - b) <= tol


# ---------------------------------------------------------------- a fixed set of quotes
H = E.H.copy()
eq, mf = H[H.asset_type == "EQ"], H[H.asset_type == "MF"]
held_eq = sorted(set(eq.instrument))
NOQUOTE = held_eq[-1] if held_eq[-1] != "HDFCBANK" else held_eq[-2]  # one held share without a quote
px = {c: float((g.value / g.units).iloc[0]) for c, g in eq.groupby("instrument")}
nav = {f"{s}|{p}": float((g.value / g.units).iloc[0]) for (s, p), g in mf.groupby(["instrument", "plan"])}
factor = lambda c: 1.20 if c == "HDFCBANK" else 1.03 if sum(map(ord, c)) % 2 else 0.97  # noqa: E731 - HDFC Bank up 20%, others +-3%
quotes = {"as_of": "2026-09-28T12:00:00", "valuation_date": E.AS_ON,
          "equity": {c: {"price": round(px[c] * factor(c), 2), "date": "2026-09-26", "prev_close": None} for c in held_eq if c != NOQUOTE},
          "mf": {k: {"nav": round(v * 0.98, 4), "date": "2026-09-25"} for k, v in nav.items()}}
older = sorted(quotes["mf"])[0]
quotes["mf"][older]["date"] = "2026-09-24"  # one fund on an older NAV: the date range must show it


def latest_value(r):
    if r.asset_type == "EQ":
        q = quotes["equity"].get(r.instrument)
        return r.units * q["price"] if q else r.value
    return r.units * quotes["mf"][f"{r.instrument}|{r.plan}"]["nav"]


H2 = H.copy()
H2["value"] = [latest_value(r) for r in H.itertuples()]

# reference look-through on the revalued holdings (the same function the reconciliation trusts)
E.H = H2
lt, *_ = E.look_through(None)
c = E.conc(lt)
tot = float(lt.total.sum())
sec = {}
for code, v in lt.total.items():
    sec[E.co_field(code, "sector")] = sec.get(E.co_field(code, "sector"), 0.0) + v
top_sec = max(sec.items(), key=lambda kv: kv[1])
E.H = H
ref = {"stock": (lt.index[0], c["top_pct"]), "sector": (top_sec[0], top_sec[1] / tot * 100),
       "top10": ("", c["top10"]), "hhi": ("", c["hhi"])}

tmp = Path(tempfile.mkdtemp(prefix="lt_quotes_"))
(tmp / "quotes.json").write_text(json.dumps(quotes), encoding="utf-8")
r = subprocess.run(["node", str(ROOT / "verify" / "latest_prices_ui.js"), str(ROOT / "app" / "LookThrough.html"), str(tmp / "quotes.json")],
                   cwd=ROOT / "verify", capture_output=True, text=True, encoding="utf-8")
if r.returncode:
    raise SystemExit(r.stderr[-2000:])
g = json.loads(r.stdout.strip().splitlines()[-1])

check("The app runs without script errors with quotes and without", not g["errors"], g["errors"])
check("Family value at latest prices = units x latest price (pandas)", close(g["total"]["v"], float(H2.value.sum())), (g["total"]["v"], float(H2.value.sum())))
check("Gain at latest prices = latest value - cost", close(g["total"]["gain"], float(H2.value.sum() - H2.cost.sum())), g["total"]["gain"])
bad = {m: (v, float(H2[H2.member_id == m].value.sum())) for m, v in g["members"].items() if not close(v, float(H2[H2.member_id == m].value.sum()))}
check("Each entity's value at latest prices agrees", not bad, bad)
n_noq = int((H.instrument == NOQUOTE).sum())
check(f"A holding without a quote ({NOQUOTE}) stays at its valuation-date price and is counted ({n_noq})", g["total"]["missing"] == n_noq, g["total"])
check("Price and NAV dates are kept apart, and the older NAV shows as a range",
      g["total"]["eq"] == ["2026-09-26", "2026-09-26"] and g["total"]["nav"] == ["2026-09-24", "2026-09-25"]
      and "prices 26 Sep 2026" in g["total"]["dates"] and "NAVs 24 Sep 2026 to 25 Sep 2026" in g["total"]["dates"], g["total"])
T = {t["k"]: t for t in g["tests"]}
bad = {k: (T[k]["who"], T[k]["v"], ref[k]) for k in ref if not (abs(T[k]["v"] - ref[k][1]) < (1e-6 if k == "hhi" else 1e-4) and (not ref[k][0] or (T[k]["code"] if k == "stock" else T[k]["who"]) == ref[k][0]))}
check("Limits at latest prices (largest stock, sector, top 10, HHI) agree with the reference engine", not bad, bad)
check("HDFC Bank up 20% moves its share of equity above the valuation-date figure", T["stock"]["v"] > g["before"]["top"] + 1, (T["stock"]["v"], g["before"]["top"]))
check("The valuation-date figures are unchanged by the quotes", g["after"] == g["before"], (g["before"], g["after"]))
s = g["screens"]
check("Dashboard card shows the value at latest prices with both dates (short form)",
      g["fmt"]["total"] in s["dashboard"] and g["fmt"]["short"] == "prices 26 Sep · NAVs 24–25 Sep · 1 unquoted" and g["fmt"]["short"] in s["dashboard"], g["fmt"])
check("Concentration names the full dates", g["fmt"]["dates"] in s["concentration"], g["fmt"]["dates"])
check("Holdings shows 'At latest prices' and a 'Value at latest' column", "At latest prices" in s["holdings"] and "Value at latest" in s["holdings"])
check("Concentration shows 'Limits at latest prices' with the re-tested largest stock", "Limits at latest prices" in s["concentration"] and g["fmt"]["top"] in s["concentration"], g["fmt"]["top"])
check("Family report states the value and largest stock at latest prices", "At latest prices" in s["report"] and g["fmt"]["totalCr"] in s["report"] and g["fmt"]["top"] in s["report"])
check("Methodology explains the two price bases", "Two price bases" in s["method"])
o = g["off"]
check("Offline (no quotes): no latest-price figures on any screen",
      not any(x in o["dashboard"] + o["concentration"] + o["holdings"] for x in ("At latest prices", "Limits at latest prices", "Value at latest")))

print(f"\n{sum(results)}/{len(results)} latest-price checks passed")
sys.exit(0 if all(results) else 1)
