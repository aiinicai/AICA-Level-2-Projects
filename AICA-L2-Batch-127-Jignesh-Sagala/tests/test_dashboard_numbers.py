"""Numbers test. The dashboard engine (JavaScript, engine.js) and the Python engine (portfolio.py) are two
separate implementations of the same rules. This test makes the JavaScript engine compute a long list of
questions (every month end and the latest date, 9 slicer combinations) and compares each answer with Python.
It also checks small cases that can be done by hand.
Needs Node.js (any version from 14).
"""
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import build_dashboard, portfolio as P  # noqa: E402

DB = ROOT / "db_dummy"
JS = r"""
const Engine = require(process.argv[2]);
const data = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8'));
const E = new Engine(data);
const scen = JSON.parse(require('fs').readFileSync(process.argv[4], 'utf8'));
const out = scen.map(s => {
  const ls = E.filtered(s.on, s.F), t = E.sum(ls), bc = E.byClass(ls);
  return { on: s.on, F: s.F, n: ls.length, value: t.value, cost: t.cost, byClass: bc,
    lines: ls.map(x => [x.cls, x.account, x.key, x.value, x.cost, x.qty == null ? null : x.qty]),
    xirr: E.xirrFor(s.on, s.F), sip: E.sipMonth(s.on, s.F), buysS: E.buysByMonth(s.on, s.F, 'SHARE'),
    series: E.timeSeries(s.on, s.F).map(p => [p.date, p.value, p.cost]) };
});
console.log(JSON.stringify(out));
"""

FILTERS = [{}, {"account": "Demat ZD1234"}, {"fh": "HDFC Mutual Fund"}, {"sector": "Banking"}, {"category": "Flexi Cap"},
           {"ccy": "USD"}, {"cls": "Equity shares"}, {"key": "INFY"}, {"account": "Demat ZD5678", "sector": "IT"}]


def run_node(data, scen):
    d = Path(tempfile.mkdtemp())
    (d / "data.json").write_text(json.dumps(data))
    (d / "scen.json").write_text(json.dumps(scen))
    (d / "run.js").write_text(JS)
    r = subprocess.run(["node", str(d / "run.js"), str(ROOT / "app/web/engine.js"), str(d / "data.json"), str(d / "scen.json")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def attrs(db, x):
    """Attributes the slicers look at, taken from the Python line."""
    ins = db["instruments"].get(x["key"])
    a = dict(account=x["account"], key=x["key"], ccy=x["ccy"], cls=x["cls"], fh=None, sector=None, category=None)
    if ins and ins["kind"] == "MF":
        a["fh"], a["category"] = ins["house"], ins["group"]
    elif ins:
        a["sector"] = ins["group"]
    return a


def ok(a, F):
    return all(a.get(k) == v for k, v in F.items())


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def test_against_python():
    data = build_dashboard.data_for(DB)
    db = P.load(DB)
    ons = sorted({r["date"] for r in data["prices"]})
    scen = [dict(on=o, F=F) for o in ons for F in FILTERS]
    res = run_node(data, scen)
    assert len(res) == len(scen)
    nlines = 0
    for s, r in zip(scen, res):
        on, F = date.fromisoformat(s["on"]), s["F"]
        py = [x for x in P.lines(db, on) if ok(attrs(db, x), F)]
        assert r["n"] == len(py), (s, r["n"], len(py))
        jl = {(l[1], l[2]): l for l in r["lines"]}
        for x in py:
            j = jl[(x["account"], x["key"])]
            assert close(j[3], x["value"]) and close(j[4], x["cost"]), (s, x["account"], x["key"], j, x["value"], x["cost"])
            if x["qty"] is not None:
                assert close(j[5], x["qty"]), (s, x["key"])
            nlines += 1
        assert close(r["value"], sum(x["value"] for x in py)) and close(r["cost"], sum(x["cost"] for x in py)), s
        for c in P.CLASSES:
            assert close(r["byClass"][c]["value"], sum(x["value"] for x in py if x["cls"] == c)), (s, c)
        # funds money-weighted return
        open_ = min(t["date"] for t in db["tx"] if t["action"] == "OPENING")
        sel_acc = {t["account"] for t in db["tx"]}
        keys = {t["key"] for t in db["tx"] if db["instruments"][t["key"]]["kind"] == "MF"}
        pairs = [(t["account"], t["key"]) for t in db["tx"] if t["key"] in keys]
        good = {(a, k) for a, k in pairs if ok(dict(account=a, key=k, ccy="INR", cls="Mutual funds", fh=db["instruments"][k]["house"],
                                                     sector=None, category=db["instruments"][k]["group"]), F)}
        if (on - open_).days < 180 or not good:
            assert r["xirr"] is None, (s, r["xirr"])
        else:
            fl = P.xirr_flows(db, on, "MF", accounts={a for a, _ in good}, keys={k for _, k in good})
            # xirr_flows filters on account and key sets separately; restrict to exact pairs
            fl = []
            for a, k in sorted(good):
                for t in db["tx"]:
                    if t["account"] == a and t["key"] == k and t["date"] <= on:
                        if t["action"] == "OPENING":
                            fl.append((t["date"], -t["qty"] * P.price_on(db, k, t["date"])[0]))
                        elif t["action"] == "SELL":
                            fl.append((t["date"], t["qty"] * t["price"]))
                        else:
                            fl.append((t["date"], -t["qty"] * t["price"]))
                ev = P.position_series(db, a, k, on)
                if ev and ev[-1]["units"] > 1e-9:
                    fl.append((on, ev[-1]["units"] * P.price_on(db, k, on)[0]))
            want = P.xirr(fl)
            if want is None:
                assert r["xirr"] is None, s
            else:
                assert r["xirr"] is not None and abs(r["xirr"] - want) < 1e-9, (s, r["xirr"], want)
        # SIP total in the month of `on`
        sip = 0.0
        for t in db["tx"]:
            if t["action"] == "SIP" and (t["date"].year, t["date"].month) == (on.year, on.month) and t["date"] <= on:
                ins = db["instruments"][t["key"]]
                if ok(dict(account=t["account"], key=t["key"], ccy="INR", cls="Mutual funds", fh=ins["house"], sector=None,
                           category=ins["group"]), F):
                    sip += t["qty"] * t["price"]
        assert close(r["sip"], sip), (s, r["sip"], sip)
        # buys of shares by month
        want = {}
        for t in db["tx"]:
            ins = db["instruments"][t["key"]]
            if t["action"] in ("BUY", "SIP") and ins["kind"] == "SHARE" and t["date"] <= on and ok(
                    dict(account=t["account"], key=t["key"], ccy="INR", cls="Equity shares", fh=None, sector=ins["group"], category=None), F):
                m = t["date"].isoformat()[:7]
                want[m] = want.get(m, 0.0) + t["qty"] * t["price"]
        assert set(want) == set(r["buysS"]) and all(close(want[m], r["buysS"][m]) for m in want), s
        # month-end series
        for d_, v, c in r["series"]:
            pyl = [x for x in P.lines(db, date.fromisoformat(d_)) if ok(attrs(db, x), F)]
            assert close(v, sum(x["value"] for x in pyl)) and close(c, sum(x["cost"] for x in pyl)), (s, d_)
    print(f"  JavaScript engine = Python engine on {len(scen)} questions, {nlines} holding lines")


def write_db(folder, tx, prices, inst):
    folder.mkdir(parents=True, exist_ok=True)

    def w(name, header, rows):
        (folder / name).write_text("\n".join([",".join(header)] + [",".join(map(str, r)) for r in rows]) + "\n")
    w("instruments.csv", ["key", "name", "kind", "group", "house", "currency"], inst)
    w("transactions.csv", ["date", "account", "key", "action", "qty", "price"], tx)
    w("prices.csv", ["date", "key", "price"], prices)
    w("bank_balances.csv", ["bank", "account_last4", "kind", "currency", "as_of", "balance"], [])
    w("fixed_deposits.csv", ["bank", "account_last4", "kind", "start", "maturity", "currency", "rate_pct", "principal", "current_value"], [])
    w("broker_cash.csv", ["broker", "account", "as_of", "cash"], [])


def test_by_hand():
    """Opening 100 units at 10; SIP 50 units at 12; sell 30; price 14 on the last date."""
    d = Path(tempfile.mkdtemp())
    tx = [("2025-12-31", "F1", "X", "OPENING", 100, 10), ("2026-01-05", "F1", "X", "SIP", 50, 12), ("2026-02-10", "F1", "X", "SELL", 30, 13)]
    prices = [("2025-12-31", "X", 10), ("2026-01-31", "X", 12.5), ("2026-02-28", "X", 14)]
    write_db(d, tx, prices, [("X", "Test Fund", "MF", "Large Cap", "Test AMC", "INR")])
    data = build_dashboard.data_for(d)
    res = run_node(data, [dict(on="2026-02-28", F={}), dict(on="2026-01-31", F={})])
    a, b = res
    # Jan: 150 units, cost 1000 + 600 = 1600, value 150 x 12.5 = 1875
    assert abs(b["value"] - 1875) < 1e-9 and abs(b["cost"] - 1600) < 1e-9, b
    # Feb: average cost 1600/150 = 10.6667; sell 30 removes 320; units 120, cost 1280, value 120 x 14 = 1680
    assert abs(a["value"] - 1680) < 1e-9 and abs(a["cost"] - 1280) < 1e-9, a
    assert abs(a["lines"][0][5] - 120) < 1e-9
    print("  hand case: units 150 / cost 1600 in Jan; units 120 / cost 1280 / value 1680 in Feb")


def test_xirr_known():
    """-1000 now and +1100 after 365 days is exactly 10% a year."""
    d = Path(tempfile.mkdtemp())
    js = r"""const E=require(process.argv[2]);const e=new E({instruments:[],tx:[],prices:[],bank:[],cash:[],fd:[]});
    const a=e.xirr([[0,-1000],[365,1100]]);const b=e.xirr([[0,-1000],[730,1210]]);console.log(JSON.stringify([a,b]));"""
    (d / "x.js").write_text(js)
    r = subprocess.run(["node", str(d / "x.js"), str(ROOT / "app/web/engine.js")], capture_output=True, text=True)
    a, b = json.loads(r.stdout)
    assert abs(a - 0.10) < 1e-9 and abs(b - 0.10) < 1e-9, (a, b)
    print("  XIRR: 1000 to 1100 in 365 days = 10.0000%; 1000 to 1210 in 730 days = 10.0000%")


if __name__ == "__main__":
    for f in (test_by_hand, test_xirr_known, test_against_python):
        print(f.__name__)
        f()
    print("ALL PASS")
