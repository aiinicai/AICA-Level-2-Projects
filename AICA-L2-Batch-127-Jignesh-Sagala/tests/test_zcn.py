"""Tests for the contract-note reader (app/zcn.py), on made-up notes only.

Run:  python tests/test_zcn.py
Every parsed figure must equal the planted one; the checks must PASS on a clean note and FAIL on each planted error.
"""
import copy
import json
import sys
import tempfile
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tools"))
import cdsl                       # noqa: E402
import zcn                        # noqa: E402
import make_dummy_zcn as gen      # noqa: E402

FAILS = []


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(label)


def status(d, part):
    for n, s, _ in zcn.run_checks(d):
        if part in n:
            return s
    return "MISSING"


def one_seed(seed, force=None):
    tag = f"seed {seed} {force or 'auto'}"
    first = None
    with tempfile.TemporaryDirectory() as tmp:
        gen.main(["x", tmp, str(seed), "3"])
        truth = json.loads((Path(tmp) / "zcn_truth.json").read_text())
        for name, t in truth.items():
            d = zcn.parse(cdsl.read_rows(Path(tmp) / name, gen.PASSWORD, force=force))
            first = first or d
            ok = (d["trade_date"].isoformat() == t["trade_date"] and d["settle_date"].isoformat() == t["settle_date"]
                  and d["settle_no"] == t["settle_no"] and d["contract_no"] == t["contract_no"])
            check(f"{tag} {name[:10]}: header equals planted", ok)
            got = {s["isin"]: s for s in d["summary"]}
            bad = []
            for s in t["summary"]:
                g = got.get(s["isin"])
                if not g or g["name"] != s["name"] or any(D(str(g[k])) != D(str(s[k])) for k in s if k not in ("isin", "name")):
                    bad.append(s["isin"])
            check(f"{tag} {name[:10]}: every summary row, all 12 numbers equal", not bad and len(got) == len(t["summary"]), str(bad[:3]))
            gt = sorted((x["trade_no"], x["isin"], x["side"], x["qty"], str(x["p1"]), str(x["total"])) for x in d["trades"])
            tt = sorted((x["trade_no"], x["isin"], x["side"], x["qty"], str(D(x["p1"])), str(D(x["total"]))) for x in t["trades"])
            # trade totals in the PDF carry the sign (buys negative); the planted total is the absolute value
            gt = [(a, b, c, e, f, str(abs(D(g)))) for a, b, c, e, f, g in gt]
            check(f"{tag} {name[:10]}: every trade (number, ISIN, side, quantity, rate, total) equal", gt == tt)
            sl = {r["isin"]: r for r in zcn.sells(d)}
            sells_truth = [s for s in t["summary"] if int(s["sell_qty"]) > 0]
            gross_s = {}
            for x in t["trades"]:
                if x["side"] == "S":
                    gross_s[x["isin"]] = gross_s.get(x["isin"], D(0)) + abs(D(str(x["total"])))
            bad_s = [s["isin"] for s in sells_truth
                     if s["isin"] not in sl
                     or sl[s["isin"]]["sell_qty"] != int(s["sell_qty"])
                     or sl[s["isin"]]["value_after_brokerage"] != D(str(s["sell_value"]))
                     or sl[s["isin"]]["gross_value"] != gross_s.get(s["isin"], D(0))
                     or sl[s["isin"]]["gross_value"] - sl[s["isin"]]["brokerage"] != D(str(s["sell_value"]))]
            check(f"{tag} {name[:10]}: sells() equals planted sell rows (quantity, gross, brokerage, value)",
                  not bad_s and len(sl) == len(sells_truth), str(bad_s[:3]))
            ob = [c for c in d["charges"] if "pay in" in c["label"].lower()]
            nt = [c for c in d["charges"] if "net amount" in c["label"].lower()]
            check(f"{tag} {name[:10]}: obligation and net amount equal", len(ob) == 1 and len(nt) == 1 and ob[0]["value"] == D(t["obligation"]) and nt[0]["value"] == D(t["net"]))
            fails = [n for n, s, _ in zcn.run_checks(d) if s == "FAIL"]
            check(f"{tag} {name[:10]}: all checks PASS on a clean note", not fails, str(fails))
        try:
            cdsl.read_rows(Path(tmp) / name, "wrong password")
            check(f"{tag}: wrong password refused", False)
        except cdsl.PasswordError:
            check(f"{tag}: wrong password refused", True)
    return first


def planted(d):
    t = copy.deepcopy(d)
    t["summary"][0]["net_qty"] += 1
    check("planted: net quantity off by 1 -> FAILS", status(t, "Net quantity") == "FAIL")
    t = copy.deepcopy(d)
    t["summary"][0]["buy_value"] *= D("1.05")
    check("planted: buy value 5% too high -> value = quantity x price after brokerage FAILS", status(t, "Summary value = quantity") == "FAIL")
    t = copy.deepcopy(d)
    t["trades"][0]["qty"] += 1
    check("planted: a trade quantity off by 1 -> trades vs summary FAILS", status(t, "Trades: quantity per ISIN") == "FAIL")
    t = copy.deepcopy(d)
    t["charges"][1]["value"] += D("25")
    check("planted: a charge off by 25 -> obligation + charges = net FAILS", status(t, "obligation + every charge") == "FAIL")
    t = copy.deepcopy(d)
    t["summary"][0]["buy_value"] -= D("500")
    check("planted: summary value 500 below the trades (negative brokerage) -> FAILS", status(t, "never negative") == "FAIL")
    t = copy.deepcopy(d)
    br = [c for c in t["charges"] if "brokerage" in c["label"].lower()][0]
    br["value"] -= D("30")
    check("planted: brokerage row 30 off -> brokerage row check FAILS", status(t, "Brokerage row in charges") == "FAIL")
    t = copy.deepcopy(d)
    t["settle_date"] = None
    check("planted: settlement date missing -> header FAILS", status(t, "Header") == "FAIL")
    t = copy.deepcopy(d)
    t["summary_unread"] = ["x"]
    check("planted: an unread summary row -> FAILS", status(t, "Summary rows read") == "FAIL")


def main():
    ds = [one_seed(s) for s in (5, 11, 23)] + [one_seed(5, "pypdf")]
    planted(ds[0])
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED")
        sys.exit(1)
    print("ALL PASSED")


if __name__ == "__main__":
    main()
