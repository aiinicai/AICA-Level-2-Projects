"""Monthly series, revenue and cost analysis, ledger statement and voucher detail (ported from analytics.ts)."""
from __future__ import annotations

import math
from collections import OrderedDict

from .context import Ctx, balances_at, day_before, ints, memoize, movements, pct_change, rupees
from .inventory import item_analytics
from .periods import DateRange, add_days, month_end, month_label, months_in
from .statements import balance_sheet, profit_and_loss
from .taxonomy import CLASS_BY_CODE, OPEX_CLASSES


def monthly_series(ctx: Ctx, r: DateRange) -> list[dict]:
    def run():
        out = []
        for m in months_in(r):
            mr = DateRange(r[0] if m < r[0] else m, r[1] if month_end(m) > r[1] else month_end(m))
            f = profit_and_loss(ctx, mr).figures
            rev = f["revenue"].paise or 0
            bs = balance_sheet(ctx, mr[1])["totals"] if ctx.cost_centre_id is None else None
            gp, np_ = f["grossProfit"].paise, f["netProfit"].paise
            out.append({
                "month": m[:7], "label": month_label(m),
                "revenue": rupees(f["revenue"].paise), "cogs": rupees(f["cogs"].paise), "grossProfit": rupees(gp), "opex": rupees(f["opex"].paise),
                "ebitda": rupees(f["ebitda"].paise), "netProfit": rupees(np_), "otherIncome": rupees(f["otherIncome"].paise),
                "financeCost": rupees(f["financeCost"].paise), "expenses": rupees(rev - (np_ or 0)),
                "grossMarginPct": (gp / rev) * 100 if rev > 0 and gp is not None else None,
                "netMarginPct": (np_ / rev) * 100 if rev > 0 and np_ is not None else None,
                "status": f["cogs"].status,
                "cash": rupees(bs["cash"] + bs["bank"]) if bs else None,
                "workingCapital": rupees(bs["currentAssets"] - bs["currentLiabilities"]) if bs and bs["inventory"] is not None else None,
                "receivables": rupees(bs["tradeReceivables"]) if bs else None, "payables": rupees(bs["tradePayables"]) if bs else None,
                "inventory": rupees(bs["inventory"]) if bs else None,
            })
        return out
    return memoize(ctx.store, ctx.cid, f"series:{r[0]}:{r[1]}:{ctx.cost_centre_id}", run)


def _revenue_by_party(ctx: Ctx, r: DateRange) -> list[dict]:
    rev = ctx.chart.ledgers_of("revenue_operating", "revenue_contra")
    if not rev:
        return []
    return ctx.store.rows(
        "SELECT v.party_ledger_id AS pid, ANY_VALUE(v.party_name) AS party, SUM(-vl.amount_paise) AS amt, COUNT(DISTINCT v.id) AS n "
        "FROM voucher_lines vl JOIN vouchers v ON v.id = vl.voucher_id "
        f"WHERE v.company_id = ? AND v.is_accounting = 1 AND v.date BETWEEN ? AND ? AND vl.ledger_id IN ({ints(rev)}) "
        "GROUP BY v.party_ledger_id ORDER BY v.party_ledger_id NULLS FIRST", [ctx.cid, r[0], r[1]])


def concentration(values: list[float]) -> dict:
    srt = sorted([v for v in values if v > 0], reverse=True)
    total = sum(srt)
    share = lambda n: (sum(srt[:n]) / total) * 100 if total > 0 else None
    hhi = sum(((v / total) * 100) ** 2 for v in srt) if total > 0 else None
    return {"top5": share(5), "top10": share(10), "top20": share(20), "count": len(srt), "hhi": hhi}


def ledger_changes(ctx: Ctx, codes: list[str], r: DateRange, prev: DateRange | None, sign: int) -> list[dict]:
    cur = movements(ctx, r)
    prv = movements(ctx, prev) if prev else {}
    ids = ctx.chart.ledgers_of(*codes)
    total = sum(sign * cur.get(i, 0) for i in ids)
    out = []
    for i in ids:
        e = ctx.chart.entries[i]
        a, b = sign * cur.get(i, 0), sign * prv.get(i, 0)
        pc = pct_change(a, b)
        out.append({"ledgerId": i, "ledger": e.name, "group": e.group_name, "classCode": e.code,
                    "classLabel": CLASS_BY_CODE[e.code].label if e.code in CLASS_BY_CODE else "", "amount": rupees(a),
                    "previous": rupees(b) if prev else None, "change": rupees(a - b) if prev else None,
                    "changePct": pc["pct"] if prev else None, "sharePct": (a / total) * 100 if total else None,
                    "costBehavior": e.attrs.get("costBehavior"), "unverified": e.status != "verified"})
    out = [x for x in out if x["amount"] != 0 or (x["previous"] or 0) != 0]
    out.sort(key=lambda x: -x["amount"])
    return out


def revenue_analysis(ctx: Ctx, r: DateRange, prev: DateRange | None) -> dict:
    ledgers = ledger_changes(ctx, ["revenue_operating", "revenue_contra"], r, prev, -1)
    by_party = _revenue_by_party(ctx, r)
    prev_party = {p["pid"]: p["amt"] for p in _revenue_by_party(ctx, prev)} if prev else {}
    debtor_ids = set(ctx.chart.ledgers_of("trade_receivable"))
    cash_ids = set(ctx.chart.ledgers_of("cash", "bank"))
    total = sum(p["amt"] for p in by_party)
    customers = []
    for p in by_party:
        pid = p["pid"]
        customers.append({
            "ledgerId": pid, "customer": f"Cash sales ({p['party']})" if pid and pid in cash_ids else (p["party"] or "(no party on voucher)"),
            "isDebtor": pid in debtor_ids if pid else False, "amount": rupees(p["amt"]), "invoices": p["n"],
            "sharePct": (p["amt"] / total) * 100 if total else None,
            "previous": rupees(prev_party.get(pid, 0)) if prev else None,
            "changePct": pct_change(p["amt"], prev_party.get(pid, 0))["pct"] if prev else None})
    customers.sort(key=lambda c: -c["amount"])
    rev_ids = ctx.chart.ledgers_of("revenue_operating", "revenue_contra")
    cc = ctx.store.rows(
        "SELECT c.name, SUM(-ca.amount_paise) AS amt FROM cost_allocations ca JOIN cost_centres c ON c.id = ca.cost_centre_id "
        "JOIN vouchers v ON v.id = ca.voucher_id "
        f"WHERE v.company_id = ? AND v.is_accounting = 1 AND v.date BETWEEN ? AND ? AND ca.ledger_id IN ({ints(rev_ids) if rev_ids else '-1'}) "
        "GROUP BY c.name ORDER BY amt DESC, c.name", [ctx.cid, r[0], r[1]])
    items = [i for i in item_analytics(ctx, r) if i.net_sales != 0] if ctx.has_items else []
    groups: "OrderedDict[str, dict]" = OrderedDict()
    for i in items:
        key = i.group or "(no group)"
        g = groups.setdefault(key, {"group": key, "netSales": 0, "qtyItems": 0})
        g["netSales"] += i.net_sales
        g["qtyItems"] += 1
    pl = profit_and_loss(ctx, r).figures
    return {
        "totals": {"revenue": rupees(pl["revenue"].paise), "grossSales": rupees(pl["grossSales"].paise),
                   "salesReturns": rupees(pl["salesReturns"].paise), "otherIncome": rupees(pl["otherIncome"].paise)},
        "ledgers": ledgers[:20], "customers": customers[:50],
        "customerConcentration": concentration([p["amt"] for p in by_party if p["pid"] and p["pid"] not in cash_ids]),
        "productConcentration": concentration([i.net_sales for i in items]) if items else None,
        "byCostCentre": [{"costCentre": c["name"], "amount": rupees(c["amt"])} for c in cc],
        "byProductGroup": sorted([{**g, "netSales": rupees(g["netSales"])} for g in groups.values()], key=lambda g: -(g["netSales"] or 0)),
        "monthly": [{"month": m["label"], "revenue": m["revenue"]} for m in monthly_series(ctx, r)],
        "notes": ["Revenue by customer uses the party ledger on each voucher; journal-posted revenue without a party appears as \"(no party on voucher)\".",
                  *(["Product-level revenue needs inventory-linked sales vouchers; not available for this company."] if not ctx.has_items else [])],
    }


def expense_anomalies(ctx: Ctx, r: DateRange) -> list[dict]:
    ids = ctx.chart.ledgers_of(*OPEX_CLASSES, "cogs_direct", "finance_cost", "exceptional")
    if not ids:
        return []
    frm = add_days(r[0], -365)
    rows = ctx.store.rows(
        "SELECT vl.ledger_id, SUBSTR(v.date,1,7) AS ym, SUM(vl.amount_paise) AS amt FROM voucher_lines vl JOIN vouchers v ON v.id = vl.voucher_id "
        f"WHERE v.company_id = ? AND v.is_accounting = 1 AND v.date BETWEEN ? AND ? AND vl.ledger_id IN ({ints(ids)}) "
        "GROUP BY vl.ledger_id, SUBSTR(v.date,1,7) ORDER BY vl.ledger_id, ym", [ctx.cid, frm, r[1]])
    by: "OrderedDict[int, dict]" = OrderedDict()
    for x in rows:
        by.setdefault(x["ledger_id"], {})[x["ym"]] = int(x["amt"])
    out = []
    months = [m[:7] for m in months_in(DateRange(frm, r[1]))]
    for lid, m in by.items():
        for ym in [x for x in months if x >= r[0][:7]]:
            hist = [m.get(x, 0) for x in [x for x in months if x < ym][-12:]]
            if sum(1 for h in hist if h != 0) < 6:
                continue
            mean = sum(hist) / len(hist)
            sd = math.sqrt(sum((h - mean) ** 2 for h in hist) / len(hist))
            v = m.get(ym, 0)
            if sd > 0 and abs(v - mean) / sd > 3 and abs(v - mean) > 500000:
                out.append({"ledgerId": lid, "ledger": ctx.chart.entries[lid].name, "month": ym, "amount": rupees(v),
                            "mean": rupees(mean), "z": (v - mean) / sd})
    out.sort(key=lambda a: -abs(a["z"]))
    return out[:20]


def cost_analysis(ctx: Ctx, r: DateRange, prev: DateRange | None) -> dict:
    expense_codes = [*OPEX_CLASSES, "cogs_direct", "depreciation", "finance_cost", "exceptional"]
    ledgers = ledger_changes(ctx, expense_codes, r, prev, 1)
    pl = profit_and_loss(ctx, r)
    pp = profit_and_loss(ctx, prev) if prev else None
    classes = []
    for code in expense_codes:
        a = sum(l["amount"] for l in ledgers if l["classCode"] == code)
        b = sum((l["previous"] or 0) for l in ledgers if l["classCode"] == code)
        classes.append({"code": code, "label": CLASS_BY_CODE[code].label, "amount": a, "previous": b if prev else None,
                        "changePct": pct_change(a, b)["pct"] if prev else None})
    classes = [c for c in classes if c["amount"] or c["previous"]]
    fixed = sum(l["amount"] for l in ledgers if l["costBehavior"] == "fixed")
    variable = sum(l["amount"] for l in ledgers if l["costBehavior"] == "variable")
    unassigned = sum(l["amount"] for l in ledgers) - fixed - variable
    rev = rupees(pl.figures["revenue"].paise) or 0
    cogs = rupees(pl.figures["cogs"].paise)
    coverage = (fixed + variable) / (fixed + variable + unassigned) if fixed + variable > 0 else 0
    var_ratio = (variable + (cogs or 0)) / rev if rev > 0 else None
    break_even = fixed / (1 - var_ratio) if coverage >= 0.8 and var_ratio is not None and var_ratio < 1 else None
    f = pl.figures
    return {
        "totals": {"cogs": cogs, "opex": rupees(f["opex"].paise), "purchases": rupees(f["purchases"].paise), "revenue": rev,
                   "grossProfit": rupees(f["grossProfit"].paise), "prevOpex": rupees(pp.figures["opex"].paise) if pp else None,
                   "cogsStatus": f["cogs"].status, "cogsNotes": f["cogs"].notes},
        "ledgers": ledgers[:20], "allLedgers": len(ledgers), "classes": classes,
        "fixedVariable": {"fixed": fixed, "variable": variable, "unassigned": unassigned, "coveragePct": coverage * 100,
                          "breakEvenRevenue": break_even,
                          "note": "Break-even needs ≥ 80% of expenses tagged fixed or variable (Ledger mapping → cost behaviour)." if break_even is None
                          else "Break-even = fixed costs ÷ (1 − (variable costs + COGS) ÷ revenue)."},
        "anomalies": expense_anomalies(ctx, r),
        "monthly": [{"month": m["label"], "cogs": m["cogs"], "opex": m["opex"], "financeCost": m["financeCost"]} for m in monthly_series(ctx, r)],
    }


def ledger_statement(ctx: Ctx, ledger_id: int, r: DateRange, page: int = 1, page_size: int = 200) -> dict | None:
    e = ctx.chart.entries.get(ledger_id)
    if not e:
        return None
    opening = balances_at(ctx, day_before(r[0])).get(ledger_id, 0)
    base = "FROM voucher_lines vl JOIN vouchers v ON v.id = vl.voucher_id WHERE vl.company_id = ? AND vl.ledger_id = ? AND v.is_accounting = 1 AND v.date BETWEEN ? AND ?"
    args = [ctx.cid, ledger_id, r[0], r[1]]
    total = ctx.store.scalar(f"SELECT COUNT(*) {base}", args)
    before = (page - 1) * page_size
    order = "ORDER BY v.date, v.id, vl.line_no"
    run_start = opening if before == 0 else opening + (ctx.store.scalar(
        f"SELECT SUM(amt) FROM (SELECT vl.amount_paise AS amt {base} {order} LIMIT ?)", [*args, before]) or 0)
    rows = ctx.store.rows(
        "SELECT v.id AS voucher_id, v.date, v.voucher_type, v.number, v.party_name, v.narration, vl.amount_paise "
        f"{base} {order} LIMIT ? OFFSET ?", [*args, page_size, before])
    closing = balances_at(ctx, r[1]).get(ledger_id, 0)
    cls = CLASS_BY_CODE.get(e.code) if e.code else None
    monthly = ctx.store.rows(
        "SELECT SUBSTR(v.date,1,7) AS ym, SUM(CASE WHEN vl.amount_paise > 0 THEN vl.amount_paise ELSE 0 END) AS dr, "
        f"SUM(CASE WHEN vl.amount_paise < 0 THEN -vl.amount_paise ELSE 0 END) AS cr {base} GROUP BY SUBSTR(v.date,1,7) ORDER BY ym", args)
    run, out_rows = run_start, []
    for x in rows:
        run += x["amount_paise"]
        out_rows.append({"voucherId": x["voucher_id"], "date": x["date"], "type": x["voucher_type"], "number": x["number"], "party": x["party_name"],
                         "narration": x["narration"], "debit": rupees(x["amount_paise"]) if x["amount_paise"] > 0 else None,
                         "credit": rupees(-x["amount_paise"]) if x["amount_paise"] < 0 else None, "balance": rupees(run)})
    return {
        "ledger": {"id": e.ledger_id, "name": e.name, "group": e.group_name, "primaryGroup": e.primary_group, "classCode": e.code,
                   "classLabel": cls.label if cls else "Unclassified", "status": e.status, "confidence": e.confidence,
                   "rationale": e.rationale, "isBillwise": e.is_billwise, "creditDays": e.credit_days, "normal": cls.normal if cls else None},
        "opening": rupees(opening), "closing": rupees(closing), "total": total, "page": page, "pageSize": page_size, "rows": out_rows,
        "monthly": [{"month": m["ym"], "debit": rupees(m["dr"]), "credit": rupees(m["cr"])} for m in monthly],
    }


def voucher_detail(ctx: Ctx, voucher_id: int) -> dict | None:
    v = ctx.store.one("SELECT * FROM vouchers WHERE id = ? AND company_id = ?", [voucher_id, ctx.cid])
    if not v:
        return None
    lines = ctx.store.rows("SELECT vl.ledger_id, vl.amount_paise, l.name FROM voucher_lines vl JOIN ledgers l ON l.id = vl.ledger_id "
                           "WHERE vl.voucher_id = ? ORDER BY vl.line_no", [voucher_id])
    inv = ctx.store.rows("SELECT il.*, si.name AS item FROM inventory_lines il JOIN stock_items si ON si.id = il.stock_item_id "
                         "WHERE il.voucher_id = ? ORDER BY il.line_no", [voucher_id])
    bills = ctx.store.rows("SELECT ba.*, l.name AS ledger FROM bill_allocations ba JOIN ledgers l ON l.id = ba.ledger_id "
                           "WHERE ba.voucher_id = ? ORDER BY ba.id", [voucher_id])
    cc = ctx.store.rows("SELECT ca.amount_paise, c.name AS cost_centre, l.name AS ledger FROM cost_allocations ca "
                        "JOIN cost_centres c ON c.id = ca.cost_centre_id JOIN ledgers l ON l.id = ca.ledger_id "
                        "WHERE ca.voucher_id = ? ORDER BY ca.id", [voucher_id])
    return {
        "id": v["id"], "guid": v["guid"], "masterId": v["master_id"], "alterId": v["alter_id"], "date": v["date"], "type": v["voucher_type"],
        "baseType": v["base_type"], "number": v["number"], "reference": v["reference"], "party": v["party_name"], "narration": v["narration"],
        "isCancelled": bool(v["is_cancelled"]), "isOptional": bool(v["is_optional"]), "isAccounting": bool(v["is_accounting"]),
        "isInventory": bool(v["is_inventory"]), "unbalancedBy": rupees(v["line_total_paise"]),
        "lines": [{"ledgerId": l["ledger_id"], "ledger": l["name"],
                   "classCode": (ctx.chart.entries[l["ledger_id"]].code if l["ledger_id"] in ctx.chart.entries else None),
                   "debit": rupees(l["amount_paise"]) if l["amount_paise"] > 0 else None,
                   "credit": rupees(-l["amount_paise"]) if l["amount_paise"] < 0 else None} for l in lines],
        "inventory": [{"item": i["item"], "direction": i["direction"], "qty": i["qty_e4"] / 1e4, "unit": i["unit"], "value": rupees(i["value_paise"]),
                       "godown": i["godown"], "batch": i["batch"], "expiry": i["expiry_date"]} for i in inv],
        "bills": [{"ledger": b["ledger"], "bill": b["bill_name"], "type": b["bill_type"], "amount": rupees(b["amount_paise"]), "dueDate": b["due_date"]} for b in bills],
        "costCentres": [{"costCentre": c["cost_centre"], "ledger": c["ledger"], "amount": rupees(c["amount_paise"])} for c in cc],
    }


def product_analysis(ctx: Ctx, r: DateRange, prev: DateRange | None) -> dict:
    if not ctx.has_items:
        return {"available": False, "reason": "This company does not track stock items in Tally, so product-level analysis is unavailable."
                if ctx.inventory_mode == "none" else
                "Product analysis needs inventory-linked sales and purchase vouchers in Tally (stock items on invoices)."}
    cur = item_analytics(ctx, r)
    prv = {i.item_id: i for i in item_analytics(ctx, prev)} if prev else {}
    total_sales = sum(i.net_sales for i in cur)
    total_gp = sum(i.gross_profit for i in cur)
    rows = []
    for i in [x for x in cur if x.net_sales or x.purchase_value or x.sales_qty]:
        p = prv.get(i.item_id)
        pm = (p.gross_profit / p.net_sales) * 100 if p and p.net_sales > 0 else None
        flags = []
        if pm is not None and i.margin_pct is not None and pm - i.margin_pct >= 3:
            flags.append("declining_margin")
        if p and i.net_sales > p.net_sales and i.gross_profit < p.gross_profit:
            flags.append("sales_up_profit_down")
        if total_sales and i.net_sales / total_sales > 0.05 and (i.margin_pct if i.margin_pct is not None else 100) < 10:
            flags.append("strong_sales_weak_margin")
        if i.gross_profit < 0:
            flags.append("loss_making")
        rows.append({
            "itemId": i.item_id, "item": i.name, "group": i.group, "unit": i.unit, "units": i.units, "salesQty": i.sales_qty,
            "returnQty": i.return_qty, "netQty": i.net_qty, "netSales": rupees(i.net_sales), "salesReturns": rupees(i.return_value),
            "estCost": rupees(i.est_cost), "grossProfit": rupees(i.gross_profit), "marginPct": i.margin_pct,
            "avgSellingPrice": rupees(i.avg_selling_price), "avgCost": rupees(i.avg_cost), "purchaseQty": i.purchase_qty,
            "purchaseValue": rupees(i.purchase_value), "avgPurchaseRate": rupees(i.avg_purchase_rate),
            "salesSharePct": (i.net_sales / total_sales) * 100 if total_sales else None,
            "gpSharePct": (i.gross_profit / total_gp) * 100 if total_gp else None,
            "prevNetSales": rupees(p.net_sales) if p else None,
            "salesGrowthPct": pct_change(i.net_sales, p.net_sales)["pct"] if p else None, "prevMarginPct": pm, "flags": flags})
    units = list(dict.fromkeys(x["unit"] for x in rows if x["unit"]))
    return {"available": True, "rows": rows,
            "basis": "Item COGS is estimated: quantity sold × moving weighted-average cost from recorded inward values (purchases at invoice value; sales returns re-enter at average cost). Company-wide expenses are not allocated to products.",
            "units": units}
