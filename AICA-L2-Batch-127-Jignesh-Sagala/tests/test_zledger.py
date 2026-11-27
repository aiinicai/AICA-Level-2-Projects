"""Tests for the Zerodha funds ledger reader (app/zledger.py), made-up ledgers only.
Run: python tests/test_zledger.py
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
import cdsl                         # noqa: E402
import zledger                      # noqa: E402
import make_dummy_zledger as gen    # noqa: E402

FAILS = []


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(label)


def st(res, part):
    for n, s, _ in res:
        if part in n:
            return s
    return "MISSING"


def run(seed, conv, force=None):
    tag = f"seed {seed} {conv} {force or 'auto'}"
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        gen.build(out, seed, conv)
        t = json.loads((out / "ledger_truth.json").read_text())
        pages = cdsl.read_rows(out / "ledger.pdf", gen.PASSWORD, force=force)
    d = zledger.parse(pages)
    ok = len(d["rows"]) == t["n"] and all(r["date"].isoformat() == p["date"] and r["debit"] == D(p["debit"]) and r["credit"] == D(p["credit"]) and r["balance"] == D(p["balance"])
                                           for r, p in zip(d["rows"], t["rows"]))
    check(f"{tag}: every row (date, debit, credit, balance) equals planted", ok)
    check(f"{tag}: sign convention found = planted", d["convention"] == conv)
    c = zledger.closing(d)
    check(f"{tag}: closing balance equals planted", c is not None and c["balance"] == D(t["closing"]))
    bad = [n for n, s, _ in zledger.checks(d) if s == "FAIL"]
    check(f"{tag}: all checks PASS on a clean ledger", not bad, str(bad))
    return pages


def planted(pages):
    def with_pages(fn):
        p = copy.deepcopy(pages)
        fn(p)
        return zledger.checks(zledger.parse(p))

    def change_balance(p):
        n = 0
        for pg in p:
            for i, ln in enumerate(pg):
                if zledger.ROW.match(ln):
                    n += 1
                    if n == 4:
                        m = zledger.ROW.match(ln)
                        pg[i] = ln[:ln.rfind(m.group(6))] + f"{D(m.group(6).replace(',', '')) + 7:.2f}"
                        return
    r = with_pages(change_balance)
    check("planted: one balance off by 7 -> chain FAILS", st(r, "every row except the first") == "FAIL")

    def drop_row(p):
        n = 0
        for pg in p:
            for i, ln in enumerate(pg):
                if zledger.ROW.match(ln):
                    n += 1
                    if n == 5:
                        del pg[i]
                        return
    check("planted: a row missing -> chain FAILS", st(with_pages(drop_row), "every row except the first") == "FAIL")

    def lose_amounts(p):
        for pg in p:
            for i, ln in enumerate(pg):
                if zledger.ROW.match(ln):
                    pg[i] = ln.rsplit(" ", 2)[0]
                    return
    check("planted: a row loses two amounts -> unread row FAILS", st(with_pages(lose_amounts), "Every dated row") == "FAIL")

    def move_date(p):
        for pg in p:
            for i, ln in enumerate(pg):
                if zledger.ROW.match(ln):
                    pg[i] = "2025-01-01" + ln[10:]
                    return
    check("planted: a date outside the period -> FAILS", st(with_pages(move_date), "inside the statement period") == "FAIL")


def main():
    pages = run(5, "credit")
    run(11, "credit")
    run(23, "debit")
    run(5, "credit", "pypdf")
    planted(pages)
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED")
        sys.exit(1)
    print("ALL PASSED")


if __name__ == "__main__":
    main()
