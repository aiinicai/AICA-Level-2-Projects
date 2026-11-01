#!/usr/bin/env python3
"""UAE Corporate Tax workpaper (CLI). Same logic as app/core.js.

Usage:
    python ct_workpaper.py ../data/sample_trial_balance.csv [--loss-bf 0] [--sbr] [-o workpaper.csv]

Standard library only. Educational: verify rules against current FTA guidance.
"""
import argparse
import csv
import re

RATE, ZERO_BAND, ENT_DEDUCTIBLE, LOSS_CAP = 0.09, 375000, 0.5, 0.75
INT_SAFE, INT_PCT, SBR_CAP = 12_000_000, 0.30, 3_000_000

SIGN = {"revenue": 1, "other_income": 1, "dividend_income": 1, "interest_income": 1,
        "cogs": -1, "opex": -1, "depreciation": -1, "interest_expense": -1,
        "entertainment_client": -1, "fines": -1, "donations": -1, "donations_approved": -1,
        "personal": -1, "mixed": -1, "bs": 0}

KEYWORDS = [
    (r"dividend", "dividend_income"), (r"interest\s*(income|received)", "interest_income"),
    (r"interest|finance (cost|charge)|bank charge", "interest_expense"),
    (r"depreciation|amorti[sz]ation", "depreciation"), (r"fine|penalt", "fines"),
    (r"donation|charity", "donations"), (r"entertain|hospitality", "entertainment_client"),
    (r"owner|personal|drawings", "personal"), (r"vehicle|car |motor|internet|mobile|telephone", "mixed"),
    (r"cost of (goods|sales)|cogs|purchases", "cogs"), (r"revenue|sales|service income|fee income", "revenue"),
]


def num(x):
    try:
        return float(str(x or "0").replace(",", ""))
    except ValueError:
        return 0.0


def load_tb(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
            cat, auto = r.get("category", "").lower(), False
            if cat not in SIGN:
                auto, cat = True, ""
                code, name = r.get("account_code", ""), r.get("account_name", "")
                if code[:1] in "123" and code:
                    cat = "bs"
                if not cat:
                    cat = next((c for p, c in KEYWORDS if re.search(p, name, re.I)), "")
                if not cat:
                    cat = "other_income" if code[:1] == "4" else "opex"
            use = r.get("business_use_pct", "")
            rows.append(dict(name=r.get("account_name", ""), debit=num(r.get("debit")), credit=num(r.get("credit")),
                             cat=cat, auto=auto, use=100.0 if use == "" else num(use)))
    return rows


def amt(r):
    s = SIGN[r["cat"]]
    return r["credit"] - r["debit"] if s == 1 else r["debit"] - r["credit"] if s == -1 else 0.0


def compute(rows, loss_bf=0.0, sbr=False):
    S = lambda c: sum(amt(r) for r in rows if r["cat"] == c)
    rev, oth, div, ii = S("revenue"), S("other_income"), S("dividend_income"), S("interest_income")
    cogs, opex, dep, ie = S("cogs"), S("opex"), S("depreciation"), S("interest_expense")
    ent, fines, don, don_ok, pers, mixed = (S("entertainment_client"), S("fines"), S("donations"),
                                            S("donations_approved"), S("personal"), S("mixed"))
    private = sum(amt(r) * (1 - r["use"] / 100) for r in rows if r["cat"] == "mixed")
    profit = rev + oth + div + ii - cogs - opex - dep - ie - ent - fines - don - don_ok - pers - mixed

    adj = []
    for label, v in [("Client entertainment: non-deductible 50%", ent * (1 - ENT_DEDUCTIBLE)),
                     ("Fines and penalties", fines), ("Donations to non-approved entities", don),
                     ("Personal / owner expenses", pers), ("Mixed-use expenses: private share", private),
                     ("Dividend income (exempt)", -div)]:
        v = round(v, 2)
        if abs(v) > 0.004:
            adj.append((label, v))
    net_int = ie - ii
    ebitda = profit + net_int + dep
    excess = max(0.0, net_int - max(INT_SAFE, INT_PCT * max(ebitda, 0)))
    if excess > 0.004:
        adj.append(("Net interest above limit", round(excess, 2)))

    before = profit + sum(v for _, v in adj)
    used = min(max(loss_bf, 0), LOSS_CAP * max(before, 0))
    ti = before - used
    sbr_applied = sbr and rev <= SBR_CAP
    tax = 0.0 if sbr_applied else max(0.0, ti - ZERO_BAND) * RATE
    return dict(profit=profit, adj=adj, before=before, used=used, ti=ti, tax=tax,
                loss_cf=max(loss_bf - used, 0) + max(-before, 0), revenue=rev, sbr_applied=sbr_applied,
                review=sum(1 for r in rows if r["auto"] and r["cat"] != "bs"),
                tb_diff=sum(r["debit"] - r["credit"] for r in rows))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tb")
    ap.add_argument("--loss-bf", type=float, default=0.0)
    ap.add_argument("--sbr", action="store_true", help="Small Business Relief elected")
    ap.add_argument("-o", "--out", default="ct_workpaper.csv")
    a = ap.parse_args()
    r = compute(load_tb(a.tb), a.loss_bf, a.sbr)

    lines = [("Accounting profit", r["profit"]), *r["adj"], ("Taxable income before losses", r["before"]),
             ("Losses utilised", -r["used"]), ("Taxable income", r["ti"]),
             ("Corporate tax payable", r["tax"]), ("Losses carried forward", r["loss_cf"])]
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Item", "AED"])
        w.writerows([(k, round(v, 2)) for k, v in lines])
    for k, v in lines:
        print(f"{k:55s}{v:>16,.2f}")
    if abs(r["tb_diff"]) > 1:
        print(f"WARNING: trial balance out of balance by {r['tb_diff']:,.2f}")
    if r["review"]:
        print(f"NOTE: {r['review']} account(s) auto-classified. Review the mapping.")
    if a.sbr and not r["sbr_applied"]:
        print("NOTE: Small Business Relief not applied (revenue above AED 3m).")
    print(f"Saved: {a.out}")


if __name__ == "__main__":
    main()
