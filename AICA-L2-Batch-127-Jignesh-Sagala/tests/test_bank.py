"""Tests for the bank readers (app/bank.py), on made-up statements only.

Run:  python tests/test_bank.py
Every parsed figure must equal the planted one; the checks must PASS on a clean file and FAIL on each planted error.
"""
import copy
import json
import sys
import tempfile
from datetime import date
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tools"))
import bank                       # noqa: E402
import cdsl                       # noqa: E402
import make_dummy_bank as gen     # noqa: E402

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


def kotak_case(tag, name, t, pages):
    d = bank.kotak_parse(pages)
    rows_ok = len(d["rows"]) == len(t["rows"]) and all(
        r["serial"] == p["serial"] and r["date"].isoformat() == p["date"] and r["amount"] == D(p["amount"]) and r["balance"] == D(p["balance"]) and r["dir"] == p["dir"]
        for r, p in zip(d["rows"], t["rows"]))
    check(f"{tag} {name}: every row (number, date, amount, balance, direction) equals planted", rows_ok)
    check(f"{tag} {name}: account, opening and summary equal planted",
          d["account"] == t["account"] and d["opening"] == D(t["opening"]) and [(s["code"], s["open"], s["close"]) for s in d["summary"]] == [(s["code"], D(s["open"]), D(s["close"])) for s in t["summary"]])
    bad = [n for n, s, _ in bank.kotak_checks(d) if s == "FAIL"]
    check(f"{tag} {name}: all checks PASS on a clean file", not bad, str(bad))
    return d


def indus_case(tag, name, t, pages):
    d = bank.indus_parse(pages)
    ok = len(d["blocks"]) == len(t["accounts"])
    for b, a in zip(d["blocks"], t["accounts"]):
        sm, why = bank.summary_for(d, b)
        ok = ok and b["account"] == a["no"] and b["product"] == a["product"] and b["bf"] == D(a["bf"]) and b["cf"] == D(a["cf"]) and len(b["rows"]) == len(a["rows"])
        ok = ok and all(r["date"].isoformat() == p["date"] and r["amount"] == D(p["amount"]) and r["balance"] == D(p["balance"]) and r["dir"] == p["dir"] for r, p in zip(b["rows"], a["rows"]))
        ok = ok and sm is not None and sm["balance"] == D(a["cf"]) and sm["currency"] == a["cur"] and sm["type"].startswith(a["type"])
    check(f"{tag} {name}: every block, row and summary balance equals planted", bool(ok))
    fd_ok = len(d["fds"]) == len(t["fds"]) and all(
        f["account"] == p["no"] and f["start"].isoformat() == p["start"] and f["maturity"].isoformat() == p["maturity"] and f["value"] == D(p["value"]) and f["rate"] == D(p["rate"]) and f["currency"] == p["cur"]
        for f, p in zip(d["fds"], t["fds"]))
    check(f"{tag} {name}: every term deposit (dates, rate, currency, value) equals planted", fd_ok)
    bad = [n for n, s, _ in bank.indus_checks(d) if s == "FAIL"]
    check(f"{tag} {name}: all checks PASS on a clean file", not bad, str(bad))
    return d


def run(seed, force=None):
    tag = f"seed {seed} {force or 'auto'}"
    got = {}
    with tempfile.TemporaryDirectory() as tmp:
        gen.main(["x", tmp, str(seed)])
        truth = json.loads((Path(tmp) / "bank_truth.json").read_text())
        for name, t in truth.items():
            pages = cdsl.read_rows(Path(tmp) / name, gen.PASSWORD, force=force)
            got[name] = (kotak_case if t["kind"] == "kotak" else indus_case)(tag, name, t, pages)
            got[name + "_pages"] = pages
        try:
            cdsl.read_rows(Path(tmp) / "kotak_a.pdf", "wrong password")
            check(f"{tag}: wrong password refused", False)
        except cdsl.PasswordError:
            check(f"{tag}: wrong password refused", True)
    return got


def planted_kotak(pages, d):
    def with_pages(fn):
        p = copy.deepcopy(pages)
        fn(p)
        return bank.kotak_checks(bank.kotak_parse(p))

    def swap_amount(p):
        for pg in p:
            for i, ln in enumerate(pg):
                m = bank.K_ROW.match(ln)
                if m and m.group(1) == "3":
                    t = bank.MONEY_END2.match(m.group(3))
                    amt = t.group(2)
                    pg[i] = ln.replace(amt, _plus(amt, 1), 1)
                    return
    check("planted: amount in row 3 off by 1 -> running balance FAILS", st(with_pages(swap_amount), "Running balance") == "FAIL")

    def drop_row(p):
        for pg in p:
            for i, ln in enumerate(pg):
                m = bank.K_ROW.match(ln)
                if m and m.group(1) == "4":
                    del pg[i]
                    return
    r = with_pages(drop_row)
    check("planted: row 4 missing -> numbering gap FAILS", st(r, "Row numbers run") == "FAIL")
    check("planted: row 4 missing -> running balance FAILS", st(r, "Running balance") == "FAIL")

    def bad_summary(p):
        for pg in p:
            for i, ln in enumerate(pg):
                if ln.startswith("Savings Account (SA):"):
                    pg[i] = ln[:-4] + "9.99"
                    return
    check("planted: summary closing balance off -> last row vs summary FAILS", st(with_pages(bad_summary), "Last row balance") == "FAIL")

    def no_amount(p):
        for pg in p:
            for i, ln in enumerate(pg):
                m = bank.K_ROW.match(ln)
                if m and m.group(1) == "5":
                    pg[i] = " ".join(ln.split()[:-2])
                    return
    check("planted: row 5 loses amount and balance -> unread row FAILS", st(with_pages(no_amount), "Every dated row has") == "FAIL")


def _plus(s, n):
    v = D(s.replace(",", "")) + n
    neg = v < 0
    return ("-" if neg else "") + f"{abs(v):.2f}"


def planted_indus(pages):
    def with_pages(fn):
        p = copy.deepcopy(pages)
        fn(p)
        return bank.indus_checks(bank.indus_parse(p))

    def change_first_total(p):
        for pg in p:
            for i, ln in enumerate(pg):
                if ln.startswith("Total "):
                    pg[i] = "Total " + _plus(ln.split()[1], 1)
                    return
    check("planted: first Total line off by 1 -> summary total FAILS", st(with_pages(change_first_total), "Account summary: each Total") == "FAIL")

    def change_fd_total(p):
        seen = 0
        for pg in p:
            for i, ln in enumerate(pg):
                if ln.startswith("Total "):
                    seen += 1
                    if seen == 3:
                        pg[i] = "Total " + _plus(ln.split()[1], 5)
                        return
    check("planted: term deposit Total off by 5 -> FAILS", st(with_pages(change_fd_total), "Term deposits: each Total") == "FAIL")

    def change_row_balance(p):
        for pg in p:
            for i, ln in enumerate(pg):
                m = bank.I_TXN.match(ln)
                if m and bank.MONEY_END2.match(m.group(2)):
                    t = bank.MONEY_END2.match(m.group(2))
                    pg[i] = ln[:ln.rfind(t.group(3))] + _plus(t.group(3), 10)
                    return
    r = with_pages(change_row_balance)
    check("planted: one running balance off by 10 -> running balance FAILS", st(r, "Running balance") == "FAIL")

    def change_cf(p):
        for pg in p:
            for i, ln in enumerate(pg):
                if "Carried Forward" in ln:
                    pg[i] = ln[:ln.rfind(" ")] + " " + _plus(ln.split()[-1], 3)
                    return
    r = with_pages(change_cf)
    check("planted: Carried Forward off by 3 -> last row vs Carried Forward FAILS", st(r, "Last row balance") == "FAIL")
    check("planted: Carried Forward off by 3 -> summary vs Carried Forward FAILS", st(r, "Summary balance") == "FAIL")

    def drop_bf(p):
        for pg in p:
            for i, ln in enumerate(pg):
                if "Brought Forward" in ln:
                    del pg[i]
                    return
    check("planted: Brought Forward line missing -> FAILS", st(with_pages(drop_bf), "Brought Forward and a Carried") == "FAIL")

    def dateless(p):
        done = False
        for pg in p:
            for k, ln in enumerate(pg):
                m = bank.I_TXN.match(ln)
                if m and "Forward" not in ln and not done:
                    pg[k] = m.group(2)
                    done = True
    check("planted: a row loses its date -> stray amount line FAILS", st(with_pages(dateless), "No line ending in two amounts") == "FAIL")

    def drop_fd(p):
        for pg in p:
            for i, ln in enumerate(pg):
                if bank.I_FD_ROW.match(ln):
                    del pg[i]
                    return
    check("planted: one term deposit row missing -> total FAILS", st(with_pages(drop_fd), "Term deposits: each Total") == "FAIL")


def main():
    runs = [run(s) for s in (7, 19, 31)] + [run(7, "pypdf")]
    g = runs[0]
    planted_kotak(g["kotak_a.pdf_pages"], g["kotak_a.pdf"])
    planted_indus(g["indus_a.pdf_pages"])
    kb = runs[0]["kotak_b.pdf"]
    check("kotak_b: an overdrawn (negative) balance is read with its minus sign", any(r["balance"] < 0 for r in kb["rows"]))
    print()
    if FAILS:
        print(f"{len(FAILS)} FAILED")
        sys.exit(1)
    print("ALL PASSED")


if __name__ == "__main__":
    main()
