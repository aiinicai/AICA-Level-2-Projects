"""Balance-sheet ratios at each month end plus integrity / risk flags (ported from analytics.ts balanceSheetAnalysis)."""
from __future__ import annotations

import dataclasses

from .context import Ctx, balances_at, movements, rupees
from .periods import DateRange, add_days, month_end, month_label, months_in
from .statements import balance_sheet
from .taxonomy import CLASS_BY_CODE


def balance_sheet_analysis(ctx: Ctx, r: DateRange, prev: DateRange | None) -> dict:
    trend = []
    for m in months_in(r):
        d = r[1] if month_end(m) > r[1] else month_end(m)
        t = balance_sheet(ctx, d)["totals"]
        ok = t["inventory"] is not None
        trend.append({
            "month": month_label(m),
            "currentRatio": t["currentAssets"] / t["currentLiabilities"] if ok and t["currentLiabilities"] > 0 else None,
            "quickRatio": t["quickAssets"] / t["currentLiabilities"] if t["quickAssets"] is not None and t["currentLiabilities"] > 0 else None,
            "debtToEquity": t["debt"] / t["equity"] if ok and t["equity"] > 0 else None,
            "workingCapital": rupees(t["currentAssets"] - t["currentLiabilities"]) if ok else None,
            "cash": rupees(t["cash"] + t["bank"]), "debt": rupees(t["debt"]),
            "equity": rupees(t["equity"]) if ok else None, "totalAssets": rupees(t["totalAssets"]) if ok else None})
    t = balance_sheet(ctx, r[1])["totals"]
    flags: list[dict] = []
    bal = balances_at(ctx, r[1])
    total_assets = max(1, t["totalAssets"])
    sus = sum(abs(bal.get(i, 0)) for i in ctx.chart.ledgers_of("suspense"))
    if sus > 0:
        flags.append({"code": "suspense", "title": "Balance in suspense / clearing accounts",
                      "severity": "high" if sus / total_assets > 0.01 else "medium", "amount": rupees(sus),
                      "rule": "Any non-zero suspense balance", "detail": "Suspense balances represent unidentified or unallocated entries.",
                      "action": "Identify and reclassify before period close."})
    for e in ctx.chart.entries.values():
        if not e.code:
            continue
        c = CLASS_BY_CODE[e.code]
        b = bal.get(e.ledger_id, 0)
        if c.statement != "BS" or abs(b) < 100000 or e.code in ("tax_balance", "trade_receivable", "trade_payable", "suspense", "branch_division", "pl_account"):
            continue
        if (c.normal == "debit" and b < 0) or (c.normal == "credit" and b > 0):
            side = "credit" if c.normal == "debit" else "debit"
            flags.append({"code": "abnormal_balance", "title": f"{e.name}: {side} balance in a {c.label.lower()} ledger",
                          "severity": "high" if e.code in ("cash", "bank", "fixed_asset") else "medium", "amount": rupees(b),
                          "rule": "Balance opposite to the class’s normal side",
                          "detail": "May indicate mis-posting, unreconciled bank entries or a classification issue.",
                          "action": "Review ledger and mapping.", "link": f"/ledgers/{e.ledger_id}"})
    for i in ctx.chart.ledgers_of("loans_advances_asset"):
        b = bal.get(i, 0)
        if b > total_assets * 0.05:
            flags.append({"code": "large_advance", "title": f"Large loan / advance: {ctx.chart.entries[i].name}", "severity": "medium",
                          "amount": rupees(b), "rule": "Loans & advances ledger > 5% of total assets",
                          "detail": "Large advances tie up funds and can conceal related-party transfers.",
                          "action": "Confirm terms, recoverability and approvals.", "link": f"/ledgers/{i}"})
    for e in [x for x in ctx.chart.entries.values() if x.attrs.get("relatedParty") and bal.get(x.ledger_id, 0) != 0]:
        flags.append({"code": "related_party", "title": f"Related-party balance: {e.name}", "severity": "low",
                      "amount": rupees(bal.get(e.ledger_id, 0)), "rule": "Ledger flagged (or detected by name) as related party",
                      "detail": "Related-party balances need disclosure and arm’s-length review.", "action": "Verify and document.",
                      "link": f"/ledgers/{e.ledger_id}"})
    if prev:
        cap_ids = ctx.chart.ledgers_of("equity_capital")
        mv = movements(dataclasses.replace(ctx, cost_centre_id=None), r)
        cap_move = sum(mv.get(i, 0) for i in cap_ids)
        if abs(cap_move) > total_assets * 0.02:
            flags.append({"code": "capital_movement", "title": "Material movement in capital accounts", "severity": "medium",
                          "amount": rupees(-cap_move), "rule": "Net capital movement > 2% of total assets in the period",
                          "detail": "Introductions or withdrawals of capital change the funding structure.",
                          "action": "Confirm board/partner approvals."})
    if t["unclassified"] != 0:
        flags.append({"code": "unclassified", "title": "Balances in unclassified ledgers", "severity": "high",
                      "amount": rupees(t["unclassified"]), "rule": "Ledgers without a mapping",
                      "detail": "These balances cannot be placed in the balance sheet structure.",
                      "action": "Map in Settings → Ledger mapping.", "link": "/settings/mapping"})
    if t["openingDifference"] != 0:
        flags.append({"code": "opening_diff", "title": "Difference in opening balances", "severity": "medium",
                      "amount": rupees(t["openingDifference"]), "rule": "Σ opening balances + opening stock ≠ 0",
                      "detail": "Opening balances entered in Tally do not tally.", "action": "Correct openings in Tally."})
    if abs(t["difference"]) > 100:
        flags.append({"code": "bs_difference", "title": "Assets ≠ liabilities + equity", "severity": "high",
                      "amount": rupees(t["difference"]), "rule": "Balance sheet check",
                      "detail": "Usually caused by unbalanced vouchers.", "action": "See Data quality.", "link": "/data-quality"})
    threshold = max(100000, total_assets * 0.005)
    pe = ctx.store.rows(
        "SELECT id, date, number, amt FROM (SELECT v.id AS id, v.date AS date, v.number AS number, "
        "SUM(CASE WHEN vl.amount_paise > 0 THEN vl.amount_paise ELSE 0 END) AS amt "
        "FROM vouchers v JOIN voucher_lines vl ON vl.voucher_id = v.id "
        "WHERE v.company_id = ? AND v.is_accounting = 1 AND v.base_type = 'Journal' AND v.date BETWEEN ? AND ? "
        "GROUP BY v.id, v.date, v.number) WHERE amt > ? ORDER BY amt DESC, id LIMIT 10",
        [ctx.cid, add_days(r[1], -2), r[1], threshold])
    if pe:
        flags.append({"code": "period_end_journals", "title": f"{len(pe)} material journal(s) in the last 3 days of the period",
                      "severity": "low", "amount": rupees(sum(x["amt"] for x in pe)),
                      "rule": "Journal vouchers in the final 3 days with debits > 0.5% of total assets",
                      "detail": "Period-end journals (provisions, depreciation, adjustments) are normal but should be reviewed.",
                      "action": "Review supporting documents.", "link": f"/vouchers/{pe[0]['id']}"})
    totals = {k: (rupees(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and not k.endswith("Pct") else v) for k, v in t.items()}
    return {"trend": trend, "flags": flags, "totals": totals}
