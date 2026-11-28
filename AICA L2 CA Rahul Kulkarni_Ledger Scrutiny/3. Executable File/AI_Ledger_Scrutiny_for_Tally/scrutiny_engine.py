"""
scrutiny_engine.py  -  Audit rules + AI checks on Tally ledger entries.

Input  : groups, ledgers, entries DataFrames (see tally_connector.py)
Output : exceptions DataFrame (one row per flagged item), summary DataFrame,
         and extra analyses (Benford, daily cash balance, AI anomaly scores).

Each rule is a small function -> easy to add / remove rules.
"""

from datetime import date

import numpy as np
import pandas as pd

from config import GROUPS

SEVERITY_ORDER = {"High": 0, "Medium": 1, "Low": 2, "Info": 3}
EXC_COLS = ["rule_id", "rule", "section", "severity", "date", "voucher_type",
            "voucher_no", "ledger", "party", "amount", "remark"]


# ======================================================= classification
def _ancestors(groups: pd.DataFrame) -> dict:
    parent = dict(zip(groups["name"], groups["parent"])) if not groups.empty else {}
    chains = {}
    for g in parent:
        chain, cur, guard = [g], parent.get(g), 0
        while cur and cur not in ("Primary", "&#4; Primary") and guard < 25:
            chain.append(cur)
            cur, guard = parent.get(cur), guard + 1
        chains[g] = chain
    return chains


def classify_ledgers(groups: pd.DataFrame, ledgers: pd.DataFrame) -> pd.DataFrame:
    """Add 'chain' (group path) and 'cls' (cash/bank/debtor/...) to every ledger."""
    chains = _ancestors(groups)
    out = []
    for _, l in ledgers.iterrows():
        parent = l.get("parent", "") or ""
        chain = chains.get(parent, [parent] if parent else [])
        cls = "other"
        for key in ["cash", "bank", "debtor", "creditor", "loan_liability", "loan_asset",
                    "duties", "expense", "income", "capital", "fixed_asset"]:
            if any(g in chain for g in GROUPS[key]):
                cls = key
                break
        out.append({**l.to_dict(), "chain": " > ".join(chain), "cls": cls})
    return pd.DataFrame(out, columns=list(ledgers.columns) + ["chain", "cls"])


def _guess_cls(name: str) -> str:
    """Fallback when masters are not available (e.g. only Day Book XML uploaded)."""
    n = name.lower()
    if n == "cash" or "cash" in n and "bank" not in n:
        return "cash"
    if "bank" in n or "a/c no" in n:
        return "bank"
    if "tds" in n or "gst" in n or "tcs" in n:
        return "duties"
    if "loan" in n:
        return "loan_liability"
    if any(k in n for k in ["exp", "charges", "salary", "wages", "rent", "fee", "purchase"]):
        return "expense"
    if "sales" in n or "income" in n:
        return "income"
    return "other"


def prepare(groups, ledgers, entries) -> pd.DataFrame:
    e = entries.copy()
    e["date"] = pd.to_datetime(e["date"]).dt.date
    e["amount"] = pd.to_numeric(e["amount"], errors="coerce").fillna(0.0)
    e["narration"] = e["narration"].fillna("").astype(str)
    e["party"] = e["party"].fillna("").astype(str)
    if ledgers is not None and not ledgers.empty:
        cl = classify_ledgers(groups if groups is not None else pd.DataFrame(columns=["name", "parent"]),
                              ledgers)
        cls_map = dict(zip(cl["name"], cl["cls"]))
    else:
        cls_map = {}
    e["cls"] = e["ledger"].map(lambda x: cls_map.get(x) or _guess_cls(x))
    e["is_cashbank"] = e["cls"].isin(["cash", "bank"])
    return e


# ======================================================= helpers
def _row(rule_id, rule, section, severity, r, remark, amount=None, ledger=None, party=None):
    return {"rule_id": rule_id, "rule": rule, "section": section, "severity": severity,
            "date": r.get("date"), "voucher_type": r.get("voucher_type", ""),
            "voucher_no": r.get("voucher_no", ""),
            "ledger": ledger if ledger is not None else r.get("ledger", ""),
            "party": party if party is not None else r.get("party", ""),
            "amount": round(float(amount if amount is not None else r.get("amount", 0)), 2),
            "remark": remark}


def _vouchers_with(e, cls):
    return set(e.loc[e["cls"] == cls, "voucher_id"])


def _inr(x):
    """Indian number format: 12,34,567"""
    neg, n = x < 0, f"{abs(x):.0f}"
    if len(n) > 3:
        head, tail = n[:-3], n[-3:]
        head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
        n = f"{head},{tail}"
    return f"{'-' if neg else ''}₹{n}"


# ======================================================= RULES
def r_cash_payment_40A3(e, cfg):
    lim = cfg["cash_payment_limit_40A3"]
    cash_cr = set(e.loc[(e["cls"] == "cash") & (e["dr_cr"] == "Cr"), "voucher_id"])
    lines = e[e["voucher_id"].isin(cash_cr) & (e["dr_cr"] == "Dr") &
              ~e["cls"].isin(["cash", "bank", "loan_liability", "loan_asset", "capital"])]
    rows = []
    for (d, led), g in lines.groupby(["date", "ledger"]):
        tot = g["amount"].sum()
        if tot > lim:
            r = g.iloc[0].to_dict()
            split = f" (split in {len(g)} entries)" if len(g) > 1 else ""
            rows.append(_row("R01", "Cash payment above limit", "Sec 40A(3)", "High", r,
                             f"Cash paid {_inr(tot)} to/for '{led}' on one day{split}; "
                             f"limit {_inr(lim)}. Check Rule 6DD exceptions.", tot))
    return rows


def r_cash_receipt_269ST(e, cfg):
    lim = cfg["cash_receipt_limit_269ST"]
    cash_dr = set(e.loc[(e["cls"] == "cash") & (e["dr_cr"] == "Dr"), "voucher_id"])
    lines = e[e["voucher_id"].isin(cash_dr) & (e["dr_cr"] == "Cr") & ~e["is_cashbank"]]
    rows = []
    for (d, led), g in lines.groupby(["date", "ledger"]):
        tot = g["amount"].sum()
        if tot >= lim:
            rows.append(_row("R02", "Cash receipt ≥ ₹2 lakh", "Sec 269ST", "High", g.iloc[0].to_dict(),
                             f"Cash received {_inr(tot)} from '{led}' in a day; penalty u/s 271DA.", tot))
    return rows


def r_cash_loans_269SS_T(e, cfg):
    lim = cfg["cash_loan_limit_269SS_T"]
    cash_v = _vouchers_with(e, "cash")
    rows = []
    lines = e[e["voucher_id"].isin(cash_v) & e["cls"].isin(["loan_liability", "loan_asset"]) &
              (e["amount"] >= lim)]
    for _, r in lines.iterrows():
        r = r.to_dict()
        if r["cls"] == "loan_liability":
            sec = "Sec 269SS" if r["dr_cr"] == "Cr" else "Sec 269T"
            what = "accepted" if r["dr_cr"] == "Cr" else "repaid"
            rows.append(_row("R03", "Loan/deposit in cash", sec, "High", r,
                             f"Loan/deposit {what} in cash {_inr(r['amount'])}; limit {_inr(lim)}."))
        else:
            rows.append(_row("R03", "Loan/advance given in cash", "Sec 269SS/269T (review)", "Medium", r,
                             f"Loan/advance in cash {_inr(r['amount'])} - verify nature & party."))
    return rows


def daily_cash_balance(e, ledgers):
    cash = e[e["cls"] == "cash"].copy()
    if cash.empty:
        return pd.DataFrame(columns=["ledger", "date", "closing"])
    cash["signed"] = np.where(cash["dr_cr"] == "Dr", cash["amount"], -cash["amount"])
    ob = dict(zip(ledgers["name"], ledgers["opening_balance"])) if ledgers is not None and not ledgers.empty else {}
    out = []
    for led, g in cash.groupby("ledger"):
        daily = g.groupby("date")["signed"].sum().sort_index().cumsum() + ob.get(led, 0.0)
        out.append(pd.DataFrame({"ledger": led, "date": daily.index, "closing": daily.values}))
    return pd.concat(out, ignore_index=True)


def r_negative_cash(e, cfg, ledgers):
    bal = daily_cash_balance(e, ledgers)
    rows = []
    for _, b in bal[bal["closing"] < 0].iterrows():
        rows.append(_row("R04", "Negative cash balance", "Audit - SA 500 / CARO", "High",
                         {"date": b["date"], "ledger": b["ledger"]},
                         f"Cash book closing balance is negative ({_inr(b['closing'])}). "
                         "Indicates unrecorded receipts or wrong dating.", b["closing"]))
    return rows


def r_holiday_entries(e, cfg):
    hol = {pd.to_datetime(h).date() for h in cfg.get("holidays", [])}
    v = e.drop_duplicates("voucher_id")
    rows = []
    for _, r in v.iterrows():
        d = r["date"]
        if d and (d.weekday() == 6 or d in hol):
            tot = e.loc[(e["voucher_id"] == r["voucher_id"]) & (e["dr_cr"] == "Dr"), "amount"].sum()
            rows.append(_row("R05", "Entry on Sunday/holiday", "Audit - unusual timing", "Low",
                             r.to_dict(), f"Voucher dated {d:%a %d-%b-%Y}.", tot))
    return rows


def r_round_sum(e, cfg):
    m, mn = cfg["round_sum_multiple"], cfg["round_sum_min"]
    lines = e[(e["dr_cr"] == "Dr") & ~e["is_cashbank"] & (e["cls"] != "duties") &
              (e["amount"] >= mn) & ((e["amount"] % m) == 0)]
    return [_row("R06", "Round-sum entry", "Audit - estimate/provision?", "Low", r.to_dict(),
                 f"Exact round figure {_inr(r['amount'])} - check supporting bill.")
            for _, r in lines.iterrows()]


def r_duplicates(e, cfg):
    win = cfg["duplicate_window_days"]
    rows = []
    lines = e[e["cls"].isin(["debtor", "creditor", "expense", "other", "fixed_asset"])]
    for (led, amt, side), g in lines.groupby(["ledger", "amount", "dr_cr"]):
        if len(g) < 2 or amt <= 0:
            continue
        g = g.sort_values("date")
        prev = None
        for _, r in g.iterrows():
            if prev is not None and r["voucher_id"] != prev["voucher_id"] and \
                    (pd.Timestamp(r["date"]) - pd.Timestamp(prev["date"])).days <= win:
                rows.append(_row("R07", "Possible duplicate entry", "Audit - completeness/occurrence",
                                 "Medium", r.to_dict(),
                                 f"Same ledger, same amount {_inr(amt)} ({side}) as voucher "
                                 f"{prev['voucher_type']} #{prev['voucher_no']} dated {prev['date']}."))
            prev = r
    # duplicate voucher numbers
    v = e.drop_duplicates("voucher_id")
    v = v[v["voucher_no"].astype(str).str.strip() != ""]
    for (vt, no), g in v.groupby(["voucher_type", "voucher_no"]):
        if len(g) > 1:
            rows.append(_row("R07", "Duplicate voucher number", "Audit - internal control", "Medium",
                             g.iloc[0].to_dict(), f"{vt} #{no} used {len(g)} times.", 0))
    return rows


def r_narration(e, cfg):
    v = e.drop_duplicates("voucher_id")
    v = v[v["narration"].str.strip().str.len() < cfg["min_narration_length"]]
    rows = []
    for _, r in v.iterrows():
        tot = e.loc[(e["voucher_id"] == r["voucher_id"]) & (e["dr_cr"] == "Dr"), "amount"].sum()
        rows.append(_row("R08", "Missing / weak narration", "Audit - documentation (SA 230)", "Low",
                         r.to_dict(), "Narration blank or too short - purpose not explained.", tot))
    return rows


def _voucher_payee(e):
    """Best guess of the payee for each voucher: party field, else creditor/other Cr line."""
    payee = {}
    for vid, g in e.groupby("voucher_id"):
        p = g["party"].iloc[0]
        if not p or p in set(g.loc[g["is_cashbank"], "ledger"]):
            cr = g[(g["dr_cr"] == "Cr") & g["cls"].isin(["creditor", "other", "loan_liability"])]
            p = cr["ledger"].iloc[0] if not cr.empty else "(payee not identified - cash/bank)"
        payee[vid] = p
    return payee


def r_tds(e, cfg):
    tds_v = set(e.loc[e["ledger"].str.lower().str.contains("tds"), "voucher_id"])
    payee = _voucher_payee(e)
    exp = e[(e["dr_cr"] == "Dr") & (e["cls"].isin(["expense", "other"]))].copy()
    rows = []
    for sec, rule in cfg["tds_rules"].items():
        hit = exp[exp["ledger"].str.lower().apply(lambda n: any(k in n for k in rule["keywords"]))].copy()
        if hit.empty:
            continue
        hit["payee"] = hit["voucher_id"].map(payee)
        for p, g in hit.groupby("payee"):
            agg, mx = g["amount"].sum(), g["amount"].max()
            unknown = p.startswith("(payee not identified")
            if unknown:                       # cannot aggregate - test single bills only
                g = g[g["amount"] > rule["single"]]
                agg = g["amount"].sum()
            if not g.empty and (mx > rule["single"] or (not unknown and agg > rule["aggregate"])):
                no_tds = g[~g["voucher_id"].isin(tds_v)]
                if no_tds.empty:
                    continue
                r = no_tds.iloc[0].to_dict()
                rows.append(_row("R09", f"TDS not deducted - {rule['label']}", f"Sec {sec} / 40(a)(ia)",
                                 "High", r,
                                 f"Payee '{p}': total {_inr(agg)} in period (single max {_inr(mx)}); "
                                 f"{len(no_tds)} entr(ies) without TDS ledger. "
                                 f"Limits: single {_inr(rule['single'])}, aggregate {_inr(rule['aggregate'])}. "
                                 "30% disallowance risk.", no_tds["amount"].sum(), party=p))
    return rows


def r_disallowance(e, cfg):
    kws = cfg["disallowance_keywords"]
    rows = []
    for _, r in e[e["dr_cr"] == "Dr"].iterrows():
        text = f"{r['ledger']} {r['narration']}".lower()
        found = [k for k in kws if k in text]
        if found:
            rows.append(_row("R10", "Possible disallowable expense", "Sec 37(1) / 40(a)(ii) / 43B",
                             "Medium", r.to_dict(), f"Keyword(s): {', '.join(found)}."))
    return rows


def r_journal_cash(e, cfg):
    jv = set(e.loc[e["voucher_type"].str.lower().str.contains("journal"), "voucher_id"])
    lines = e[e["voucher_id"].isin(jv) & e["is_cashbank"]]
    return [_row("R11", "Cash/Bank in Journal voucher", "Audit - internal control", "Medium",
                 r.to_dict(), "Cash/Bank should move through Payment/Receipt/Contra, not Journal.")
            for _, r in lines.iterrows()]


def r_material(e, cfg):
    lim = cfg["materiality_amount"]
    lines = e[(e["dr_cr"] == "Dr") & (e["amount"] >= lim) & ~(e["is_cashbank"] &
              e["voucher_type"].str.lower().str.contains("contra"))]
    return [_row("R12", "Material entry - vouch 100%", "SA 320 materiality", "Info", r.to_dict(),
                 f"Amount ≥ {_inr(lim)}.") for _, r in lines.iterrows()]


def r_period(e, cfg, p_from, p_to):
    v = e.drop_duplicates("voucher_id")
    rows = []
    today = date.today()
    for _, r in v.iterrows():
        d = r["date"]
        if d is None:
            rows.append(_row("R13", "Voucher without date", "Audit - cut-off", "High", r.to_dict(), "No date."))
        elif (p_from and d < p_from) or (p_to and d > p_to):
            rows.append(_row("R13", "Entry outside audit period", "Audit - cut-off", "Medium", r.to_dict(),
                             f"Date {d} outside {p_from} to {p_to}."))
        elif d > today:
            rows.append(_row("R13", "Future-dated entry", "Audit - cut-off", "High", r.to_dict(),
                             f"Date {d} is after today."))
    return rows


def r_suspense(e, cfg):
    lines = e[e["ledger"].str.lower().str.contains("suspense")]
    return [_row("R14", "Entry in Suspense account", "Audit - unexplained items", "High", r.to_dict(),
                 "Suspense balances must be cleared before finalisation.") for _, r in lines.iterrows()]


def r_party_balance(e, cfg, ledgers):
    ob = dict(zip(ledgers["name"], ledgers["opening_balance"])) if ledgers is not None and not ledgers.empty else {}
    rows = []
    p = e[e["cls"].isin(["debtor", "creditor"])].copy()
    p["signed"] = np.where(p["dr_cr"] == "Dr", p["amount"], -p["amount"])
    for (led, cls), g in p.groupby(["ledger", "cls"]):
        close = ob.get(led, 0.0) + g["signed"].sum()
        if cls == "debtor" and close < -1:
            rows.append(_row("R15", "Debtor with credit balance", "Audit - classification (Sch III)", "Low",
                             {"date": g["date"].max(), "ledger": led},
                             f"Closing {_inr(-close)} Cr - advance from customer? reclassify.", -close))
        if cls == "creditor" and close > 1:
            rows.append(_row("R15", "Creditor with debit balance", "Audit - classification (Sch III)", "Low",
                             {"date": g["date"].max(), "ledger": led},
                             f"Closing {_inr(close)} Dr - advance/excess payment? reclassify.", close))
    return rows


def r_outliers(e, cfg):
    z = cfg["outlier_zscore"]
    rows = []
    lines = e[(e["dr_cr"] == "Dr") & ~e["is_cashbank"]]
    for led, g in lines.groupby("ledger"):
        if len(g) < 8:
            continue
        mu, sd = g["amount"].mean(), g["amount"].std()
        if sd == 0 or np.isnan(sd):
            continue
        for _, r in g[g["amount"] > mu + z * sd].iterrows():
            rows.append(_row("R16", "Unusual amount for this ledger", "Analytical review (SA 520)", "Medium",
                             r.to_dict(), f"{_inr(r['amount'])} vs usual avg {_inr(mu)} "
                             f"({(r['amount'] - mu) / sd:.1f} SD above)."))
    return rows


# ======================================================= Analytics / AI
def benford(e):
    amt = e.loc[(e["dr_cr"] == "Dr") & (e["amount"] >= 10), "amount"]
    first = amt.astype(int).astype(str).str[0].astype(int)
    digits = range(1, 10)
    actual = first.value_counts(normalize=True).reindex(digits, fill_value=0)
    expected = pd.Series([np.log10(1 + 1 / d) for d in digits], index=digits)
    mad = float((actual - expected).abs().mean()) if len(amt) else 0.0
    if mad < 0.006:
        verdict = "Close conformity"
    elif mad < 0.012:
        verdict = "Acceptable conformity"
    elif mad < 0.015:
        verdict = "Marginal conformity"
    else:
        verdict = "Non-conformity - investigate"
    df = pd.DataFrame({"digit": list(digits), "actual_%": (actual * 100).round(2).values,
                       "expected_%": (expected * 100).round(2).values})
    return df, mad, verdict, len(amt)


def ai_anomalies(e, cfg):
    """Unsupervised ML (Isolation Forest) - learns 'normal' entries & scores unusual ones."""
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        return pd.DataFrame(), "scikit-learn not installed - AI check skipped."
    d = e[(e["dr_cr"] == "Dr") & ~e["is_cashbank"]].copy()
    if len(d) < 30:
        return pd.DataFrame(), "Too few entries for AI model (need 30+)."
    dt = pd.to_datetime(d["date"])
    led_cnt = d["ledger"].map(d["ledger"].value_counts())
    grp = d.groupby("ledger")["amount"]
    z = ((d["amount"] - grp.transform("mean")) / grp.transform("std").replace(0, np.nan)).fillna(0)
    X = pd.DataFrame({
        "log_amount": np.log1p(d["amount"]),
        "weekday": dt.dt.weekday,
        "day": dt.dt.day,
        "ledger_rarity": -np.log(led_cnt / len(d)),
        "amount_z_in_ledger": z,
        "round": ((d["amount"] % 1000) == 0).astype(int),
        "narration_len": d["narration"].str.len().clip(upper=100),
        "vch_type": d["voucher_type"].astype("category").cat.codes,
    })
    model = IsolationForest(n_estimators=200, contamination=cfg["ai_contamination"], random_state=42)
    model.fit(X)
    d["ai_score"] = -model.score_samples(X)          # higher = more unusual
    d["ai_flag"] = model.predict(X) == -1

    def reason(i):
        x, why = X.loc[i], []
        if x["amount_z_in_ledger"] > 2: why.append("amount much higher than usual for ledger")
        if x["ledger_rarity"] > np.log(len(d) / 3): why.append("rarely used ledger")
        if x["weekday"] == 6: why.append("Sunday entry")
        if x["round"] == 1 and d.loc[i, "amount"] >= 10000: why.append("round figure")
        if x["narration_len"] < 5: why.append("no narration")
        if x["log_amount"] > X["log_amount"].quantile(0.98): why.append("among largest amounts")
        return "; ".join(why) or "unusual combination of features"
    flagged = d[d["ai_flag"]].sort_values("ai_score", ascending=False).copy()
    flagged["ai_reason"] = [reason(i) for i in flagged.index]
    return flagged, f"Isolation Forest trained on {len(d)} entries; {len(flagged)} flagged."


# ======================================================= RUN ALL
def run_all(groups, ledgers, entries, cfg, period_from=None, period_to=None):
    e = prepare(groups, ledgers, entries)
    rows = []
    rows += r_cash_payment_40A3(e, cfg)
    rows += r_cash_receipt_269ST(e, cfg)
    rows += r_cash_loans_269SS_T(e, cfg)
    rows += r_negative_cash(e, cfg, ledgers)
    rows += r_holiday_entries(e, cfg)
    rows += r_round_sum(e, cfg)
    rows += r_duplicates(e, cfg)
    rows += r_narration(e, cfg)
    rows += r_tds(e, cfg)
    rows += r_disallowance(e, cfg)
    rows += r_journal_cash(e, cfg)
    rows += r_material(e, cfg)
    rows += r_period(e, cfg, period_from, period_to)
    rows += r_suspense(e, cfg)
    rows += r_party_balance(e, cfg, ledgers)
    rows += r_outliers(e, cfg)

    ai_df, ai_msg = ai_anomalies(e, cfg)
    for _, r in ai_df.iterrows():
        rows.append(_row("R17", "AI-detected anomaly", "AI - Isolation Forest", "Medium", r.to_dict(),
                         f"Anomaly score {r['ai_score']:.3f}: {r['ai_reason']}."))

    exc = pd.DataFrame(rows, columns=EXC_COLS)
    if not exc.empty:
        exc["_s"] = exc["severity"].map(SEVERITY_ORDER)
        exc = exc.sort_values(["_s", "rule_id", "date"]).drop(columns="_s").reset_index(drop=True)
    summary = (exc.groupby(["rule_id", "rule", "section", "severity"], as_index=False)
               .agg(count=("amount", "size"), amount=("amount", "sum"))
               if not exc.empty else pd.DataFrame(columns=["rule_id", "rule", "section", "severity", "count", "amount"]))
    if not summary.empty:
        summary["_s"] = summary["severity"].map(SEVERITY_ORDER)
        summary = summary.sort_values(["_s", "rule_id"]).drop(columns="_s").reset_index(drop=True)

    bf, mad, verdict, n = benford(e)
    extras = {
        "entries": e,
        "benford": bf, "benford_mad": mad, "benford_verdict": verdict, "benford_n": n,
        "cash_balance": daily_cash_balance(e, ledgers),
        "ai_message": ai_msg,
        "stats": {"vouchers": e["voucher_id"].nunique(), "lines": len(e),
                  "ledgers": e["ledger"].nunique(),
                  "total_dr": float(e.loc[e["dr_cr"] == "Dr", "amount"].sum()),
                  "total_cr": float(e.loc[e["dr_cr"] == "Cr", "amount"].sum())},
    }
    return exc, summary, extras
