"""Tests for the CDSL reader, on made-up statements only.

Run:  python tests/test_cdsl.py
Checks that every parsed figure equals the figure the generator planted,
that the self-checks PASS on a clean file, and that planted errors make them FAIL.
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
import cdsl                      # noqa: E402
import make_dummy_cdsl as gen    # noqa: E402

FAILS = []


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(label)


def status(d, name_part):
    for n, s, _ in cdsl.run_checks(d):
        if name_part in n:
            return s
    return "MISSING"


def one_seed(seed, force=None):
    with tempfile.TemporaryDirectory() as tmp:
        gen.main(["x", tmp, str(seed)])
        truth = json.loads((Path(tmp) / "cdsl_truth.json").read_text())
        pages = cdsl.read_rows(Path(tmp) / "cdsl_made_up.pdf", gen.PASSWORD, force=force)
        try:
            cdsl.read_rows(Path(tmp) / "cdsl_made_up.pdf", "wrong password")
            check(f"seed {seed} {force or 'auto'}: wrong password refused", False)
        except cdsl.PasswordError:
            check(f"seed {seed} {force or 'auto'}: wrong password refused", True)
    d = cdsl.parse(pages)

    check(f"seed {seed} {force or 'auto'}: period read", d["period"] == tuple(truth["period"]), str(d["period"]))
    check(f"seed {seed} {force or 'auto'}: 12 months, values equal", [(m["month"], str(m["value"])) for m in d["months"]] == [tuple(x) for x in truth["months"]])

    # MF holdings: compare by (isin, folio)
    got = {(x["isin"], x["folio"]): x for x in d["mf_holdings"]}
    ok = len(got) == len(truth["mf_holdings"])
    bad = []
    for t in truth["mf_holdings"]:
        g = got.get((t["isin"], t["folio"]))
        if not g or any(str(g[k]) != t[k] and D(str(g[k])) != D(t[k]) for k in ("units", "nav", "cost", "value", "gain", "gain_pct")):
            bad.append(t["isin"])
    check(f"seed {seed} {force or 'auto'}: MF holdings: every folio, units, NAV, cost, value, gain, gain% equal the planted figure", ok and not bad, str(bad[:3]))
    check(f"seed {seed} {force or 'auto'}: both MF Grand Totals", [(str(g["cost"]), str(g["value"])) for g in d["mf_totals"]] == [(g["cost"], g["value"]) for g in truth["mf_totals"]])

    # MF transactions
    bad = []
    for isin, t in truth["mf_txn"].items():
        g = d["mf_txn"].get(isin)
        if not g or str(g["opening"]) != t["opening"] or str(g["closing"]) != t["closing"] or [str(x["units"]) for x in g["txns"]] != t["units"]:
            bad.append(isin)
    check(f"seed {seed} {force or 'auto'}: MF transactions: opening, closing and every transaction's units equal", not bad and len(d["mf_txn"]) == len(truth["mf_txn"]),
          f"{bad[:3]} found {len(d['mf_txn'])} expected {len(truth['mf_txn'])}")

    # demat
    got = {x["isin"]: x for x in d["demat"]}
    bad = [t["isin"] for t in truth["demat"]
           if t["isin"] not in got or D(str(got[t["isin"]]["qty"])) != D(t["qty"]) or D(str(got[t["isin"]]["price"])) != D(t["price"])
           or D(str(got[t["isin"]]["value"])) != D(t["value"])]
    check(f"seed {seed} {force or 'auto'}: demat: every ISIN, quantity, price, value equal", not bad and len(d["demat"]) == len(truth["demat"]), str(bad[:3]))
    check(f"seed {seed} {force or 'auto'}: demat Portfolio Value", d["demat_total"] and str(d["demat_total"]["value"]) == truth["demat_total"])

    fails = [n for n, s, _ in cdsl.run_checks(d) if s == "FAIL"]
    check(f"seed {seed} {force or 'auto'}: all self-checks PASS on a clean file", not fails, str(fails))
    return d


def planted(d):
    """Plant one error at a time; the self-checks must catch each."""
    t1 = copy.deepcopy(d)
    t1["mf_holdings"][3]["value"] += D("500")
    check("planted: a folio value off by 500 -> total check FAILS", status(t1, "Grand Total") == "FAIL")

    t2 = copy.deepcopy(d)
    first = next(b for b in t2["mf_txn"].values() if b["txns"])
    first["txns"][0]["units"] += D("1.000")
    check("planted: a transaction off by 1 unit -> opening+txn=closing FAILS", status(t2, "opening units") == "FAIL")

    t3 = copy.deepcopy(d)
    counts = {}
    for x in t3["mf_holdings"]:
        counts[x["isin"]] = counts.get(x["isin"], 0) + 1
    isin = next(i for i, b in t3["mf_txn"].items() if b["closing"] is not None and "#" not in i and counts.get(i) == 1)
    t3["mf_txn"][isin]["closing"] += D("2")
    check("planted: closing units differ from holdings -> FAILS", status(t3, "Closing units in transactions") == "FAIL")

    t4 = copy.deepcopy(d)
    t4["demat"][2]["value"] += D("100")
    check("planted: a demat value off by 100 -> demat total FAILS", status(t4, "Sum of demat rows") == "FAIL")

    t5 = copy.deepcopy(d)
    t5["mf_holdings"][0]["isin"] = None
    check("planted: folio without ISIN -> FAILS", status(t5, "Folio rows with ISIN") == "FAIL")

    t6 = copy.deepcopy(d)
    t6["months"] = t6["months"][:11]
    check("planted: a month missing -> FAILS", status(t6, "Month table") == "FAIL")


def main():
    ds = [one_seed(s) for s in (7, 21, 99)] + [one_seed(s, 'pypdf') for s in (7, 21)]
    planted(ds[0])
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED")
        sys.exit(1)
    print("ALL PASSED")


if __name__ == "__main__":
    main()
