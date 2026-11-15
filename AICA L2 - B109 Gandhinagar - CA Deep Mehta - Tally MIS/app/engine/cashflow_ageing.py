"""Cash flow (direct method) and bill-wise ageing (ported from cashflow.ts and ageing.ts)."""
from __future__ import annotations

from .context import Ctx, balances_at, day_before, ints, memoize, sum_of
from .periods import DateRange, days_between, js_to_fixed
from .taxonomy import CLASS_BY_CODE

# ------------------------------------------------------------------------------------------------ cash flow
_CATEGORY = {
    "fixed_asset": "investing", "investment": "investing", "other_noncurrent_asset": "investing", "misc_expense_asset": "investing",
    "equity_capital": "financing", "equity_reserves": "financing", "pl_account": "financing", "borrowing_long": "financing",
    "borrowing_short": "financing", "finance_cost": "financing", "other_noncurrent_liability": "financing",
    "suspense": "unclassified", "branch_division": "unclassified",
}


def category_of(code: str | None) -> str:
    return "unclassified" if not code else _CATEGORY.get(code, "operating")


def cash_flow(ctx: Ctx, r: DateRange) -> dict:
    return memoize(ctx.store, ctx.cid, f"cf:{r[0]}:{r[1]}", lambda: _cash_flow(ctx, r))


def _cash_flow(ctx: Ctx, r: DateRange) -> dict:
    cash_ids = list(dict.fromkeys(ctx.chart.ledgers_of("cash", "bank")))
    cash_set = set(cash_ids)
    notes: list[str] = []
    by_cat = {"operating": 0, "investing": 0, "financing": 0, "unclassified": 0}
    cls: dict[str, dict] = {}
    monthly: dict[str, dict] = {}
    opening = sum_of(balances_at(ctx, day_before(r[0])), cash_ids)
    closing = sum_of(balances_at(ctx, r[1]), cash_ids)
    if not cash_set:
        notes.append("No cash or bank ledgers are classified; cash flow unavailable.")
    else:
        rows = ctx.store.rows(
            "SELECT vl.voucher_id, v.date, vl.ledger_id, vl.amount_paise FROM voucher_lines vl JOIN vouchers v ON v.id = vl.voucher_id "
            "WHERE v.company_id = ? AND v.is_accounting = 1 AND v.date BETWEEN ? AND ? "
            f"AND vl.voucher_id IN (SELECT vl2.voucher_id FROM voucher_lines vl2 WHERE vl2.company_id = ? AND vl2.ledger_id IN ({ints(cash_ids)})) "
            "ORDER BY vl.voucher_id, vl.line_no", [ctx.cid, r[0], r[1], ctx.cid])
        i = 0
        while i < len(rows):
            vid = rows[i]["voucher_id"]
            lines = []
            while i < len(rows) and rows[i]["voucher_id"] == vid:
                lines.append(rows[i])
                i += 1
            cash_delta = sum(l["amount_paise"] for l in lines if l["ledger_id"] in cash_set)
            if cash_delta == 0:
                continue  # contra between cash and bank
            month = lines[0]["date"][:7]
            m = monthly.setdefault(month, {"operating": 0, "investing": 0, "financing": 0, "unclassified": 0})
            for l in lines:
                if l["ledger_id"] in cash_set:
                    continue
                e = ctx.chart.entries.get(l["ledger_id"])
                code = e.code if e else None
                flow = -l["amount_paise"]
                cat = category_of(code)
                by_cat[cat] += flow
                m[cat] += flow
                c = cls.setdefault(code or "unclassified", {"inflow": 0, "outflow": 0})
                if flow >= 0:
                    c["inflow"] += flow
                else:
                    c["outflow"] += -flow
    net = by_cat["operating"] + by_cat["investing"] + by_cat["financing"] + by_cat["unclassified"]
    check = opening + net - closing
    if abs(check) > 100:
        notes.append("Cash flow does not reconcile to the change in cash balances — usually caused by unbalanced vouchers.")
    notes.append("Interest and dividends received are shown in operating activities; interest paid in financing.")
    by_class = [{"code": code, "label": CLASS_BY_CODE[code].label if code in CLASS_BY_CODE else "Unclassified ledgers",
                 "category": category_of(None if code == "unclassified" else code), **v} for code, v in cls.items()]
    by_class.sort(key=lambda x: -(x["inflow"] + x["outflow"]))
    return {"range": r, "opening": opening, "closing": closing, "net": net, "byCategory": by_cat, "check": check, "notes": notes,
            "byClass": by_class, "monthly": [{"month": k, **v} for k, v in sorted(monthly.items())]}


# ------------------------------------------------------------------------------------------------ ageing
def bucket_labels(bounds: list[int]) -> list[str]:
    labels, lo = ["Not due"], 1
    for b in bounds:
        labels.append(f"{lo}–{b} days")
        lo = b + 1
    labels.append(f"> {bounds[-1]} days")
    return labels


def _bucket_for(days, bounds, labels) -> str:
    if days is None:
        return "Undated"
    if days <= 0:
        return labels[0]
    for i, b in enumerate(bounds):
        if days <= b:
            return labels[i + 1]
    return labels[-1]


def ageing(ctx: Ctx, kind: str, as_of: str, bounds: list[int] | None = None) -> dict:
    bnds = bounds or ctx.settings.get("ageingBuckets") or [30, 60, 90, 180]
    return memoize(ctx.store, ctx.cid, f"age:{kind}:{as_of}:{','.join(map(str, bnds))}", lambda: _ageing(ctx, kind, as_of, bnds))


def _ageing(ctx: Ctx, kind: str, as_of: str, bnds: list[int]) -> dict:
    code = "trade_receivable" if kind == "receivable" else "trade_payable"
    sign = 1 if kind == "receivable" else -1
    labels = bucket_labels(bnds)
    ledgers = ctx.chart.by_code.get(code, [])
    ids = [l.ledger_id for l in ledgers]
    bal = balances_at(ctx, as_of)
    notes: list[str] = []
    empty_totals = {"ledgerBalance": 0, "billTotal": 0, "onAccount": 0, "unreconciled": 0, "overdue": 0, "notDue": 0, "advances": 0,
                    "buckets": {}, "billwiseCoveragePct": None, "parties": 0}
    if not ids:
        return {"kind": kind, "asOf": as_of, "bucketLabels": labels, "parties": [], "bills": [], "totals": empty_totals,
                "notes": [f"No {'debtor' if kind == 'receivable' else 'creditor'} ledgers are classified."]}
    allocs = ctx.store.rows(
        "SELECT ba.ledger_id, ba.bill_name, ba.bill_type, ba.amount_paise, ba.date, ba.due_date, ba.is_opening "
        "FROM bill_allocations ba LEFT JOIN vouchers v ON v.id = ba.voucher_id "
        f"WHERE ba.company_id = ? AND ba.ledger_id IN ({ints(ids)}) AND (ba.is_opening = 1 OR (v.is_accounting = 1 AND v.date <= ?)) "
        "ORDER BY ba.ledger_id, ba.bill_name, ba.id", [ctx.cid, as_of])
    bill_map: dict[tuple, dict] = {}
    on_account: dict[int, int] = {}
    has_allocs: set[int] = set()
    for a in allocs:
        has_allocs.add(a["ledger_id"])
        if a["bill_type"] == "On Account":
            on_account[a["ledger_id"]] = on_account.get(a["ledger_id"], 0) + a["amount_paise"]
            continue
        k = (a["ledger_id"], a["bill_name"])
        b = bill_map.get(k)
        if b is None:
            b = bill_map[k] = {"ledgerId": a["ledger_id"], "name": a["bill_name"], "total": 0, "original": 0, "date": None,
                               "due": None, "advance": False, "refs": 0}
        b["total"] += a["amount_paise"]
        b["refs"] += 1
        if a["bill_type"] in ("New Ref", "Advance") or a["is_opening"] == 1:
            b["original"] += a["amount_paise"]
            d = None if a["date"] == "1900-01-01" else a["date"]
            if d and (not b["date"] or d < b["date"]):
                b["date"] = d
            if a["due_date"] and (not b["due"] or a["due_date"] < b["due"]):
                b["due"] = a["due_date"]
            if a["bill_type"] == "Advance":
                b["advance"] = True

    bills: list[dict] = []
    parties: dict[int, dict] = {}
    for l in ledgers:
        lb = bal.get(l.ledger_id, 0)
        parties[l.ledger_id] = {"ledgerId": l.ledger_id, "party": l.name, "ledgerBalance": sign * lb, "billTotal": 0,
                                "onAccount": sign * on_account.get(l.ledger_id, 0), "unreconciled": 0,
                                "billwise": l.ledger_id in has_allocs or l.is_billwise, "overdue": 0, "notDue": 0,
                                "creditLimit": l.credit_limit_paise, "creditDays": l.credit_days, "buckets": {}, "bills": 0,
                                "oldestDays": None, "abnormalSign": sign * lb < 0}
    for b in bill_map.values():
        if b["total"] == 0:
            continue
        p = parties[b["ledgerId"]]
        amount = sign * b["total"]
        due = b["due"]
        basis = "due_date" if due else "bill_date" if b["date"] else "unknown"
        age_days = days_between(b["date"], as_of) if b["date"] else None
        days_overdue = days_between(due, as_of) if due else None
        bucket_days = days_overdue if basis == "due_date" else age_days
        bucket = "Advances / credits" if amount < 0 else _bucket_for(bucket_days, bnds, labels)
        bnotes = []
        if basis == "bill_date":
            bnotes.append("No due date recorded; aged from bill date")
        if basis == "unknown":
            bnotes.append("No bill date (opening bill without date)")
        if b["refs"] > 1 and abs(b["total"]) < abs(b["original"]):
            bnotes.append("Partly settled")
        if b["original"] == 0:
            bnotes.append("Settlement reference with no originating bill in imported data")
        bills.append({"ledgerId": b["ledgerId"], "party": p["party"], "billName": b["name"], "billDate": b["date"], "dueDate": due,
                      "amount": amount, "original": sign * b["original"], "settled": sign * (b["original"] - b["total"]),
                      "isAdvance": b["advance"] or amount < 0, "daysOverdue": days_overdue, "ageDays": age_days, "basis": basis,
                      "bucket": bucket, "notes": bnotes})
        p["billTotal"] += amount
        p["bills"] += 1
        p["buckets"][bucket] = p["buckets"].get(bucket, 0) + amount
        if amount > 0:
            od = (days_overdue or 0) > 0 if basis == "due_date" else False
            if od:
                p["overdue"] += amount
            else:
                p["notDue"] += amount if basis == "due_date" else 0
            if age_days is not None and (p["oldestDays"] is None or age_days > p["oldestDays"]):
                p["oldestDays"] = age_days

    totals = {"ledgerBalance": 0, "billTotal": 0, "onAccount": 0, "unreconciled": 0, "overdue": 0, "notDue": 0, "advances": 0,
              "buckets": {}, "billwiseCoveragePct": None, "parties": 0}
    billwise_bal = abs_bal = 0
    for p in parties.values():
        p["unreconciled"] = p["ledgerBalance"] - p["billTotal"] - p["onAccount"]
        if not p["billwise"]:
            p["unreconciled"] = 0
        for k in ("ledgerBalance", "billTotal", "onAccount", "unreconciled", "overdue", "notDue"):
            totals[k] += p[k]
        for k, v in p["buckets"].items():
            totals["buckets"][k] = totals["buckets"].get(k, 0) + v
        abs_bal += abs(p["ledgerBalance"])
        if p["billwise"]:
            billwise_bal += abs(p["ledgerBalance"])
        if p["ledgerBalance"] != 0 or p["bills"]:
            totals["parties"] += 1
    totals["advances"] = sum(b["amount"] for b in bills if b["amount"] < 0)
    totals["billwiseCoveragePct"] = (billwise_bal / abs_bal) * 100 if abs_bal else None
    if totals["billwiseCoveragePct"] is not None and totals["billwiseCoveragePct"] < 100:
        notes.append(f"{js_to_fixed(100 - totals['billwiseCoveragePct'], 0)}% of {kind} balances are on ledgers without bill-wise details: shown as ledger-level exposure and not aged.")
    if any(b["basis"] == "bill_date" for b in bills):
        notes.append("Some bills have no due date (no credit period); those are aged from the bill date.")
    if abs(totals["unreconciled"]) > 100:
        notes.append("Bill-wise outstanding does not fully reconcile to ledger balances; see the reconciliation table.")
    plist = [p for p in parties.values() if p["ledgerBalance"] != 0 or p["bills"]]
    plist.sort(key=lambda p: -p["ledgerBalance"])
    bills.sort(key=lambda b: -((b["daysOverdue"] if b["daysOverdue"] is not None else b["ageDays"]) or 0))
    return {"kind": kind, "asOf": as_of, "bucketLabels": [*labels, "Advances / credits", "Undated"], "notes": notes,
            "parties": plist, "bills": bills, "totals": totals}
