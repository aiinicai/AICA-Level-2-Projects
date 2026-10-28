"""Numbers behind the financial statements dashboard. Plain functions on the model and the review, so they can be tested
without a browser; the charts are drawn in ui/charts.py. Every amount is converted to the presentation unit."""
from __future__ import annotations

import pandas as pd

from .model import Model


def _days(num: float, den: float):
    return None if not den else round(num / den * 365)


def fs_dashboard(m: Model, review=None) -> dict:
    u = m.unit
    f, pl = m.figures["cur"], m.figures["pl"]
    prev = m.figures["prev"]
    v = u.value
    revenue, other = pl["revenue"], pl["other_income"]

    kpis = {
        "revenue": revenue, "profit": m.profit, "margin": (m.profit / revenue) if revenue else None,
        "total_assets": next(r.cur for r in m.bs if r.label == "TOTAL ASSETS"), "equity": f["equity"],
        "cash": f["cce"], "cfo": pl["cfo"],
        "current_ratio": (f["ca"] / f["cl"]) if f["cl"] else None,
        "debt_equity": ((f["ltb"] + f["stb"]) / f["equity"]) if f["equity"] else None,
        "receivable_days": _days(f["tr"], revenue), "payable_days": _days(f["tp"], pl["purchases"]),
        "inventory_days": _days(f["inv"], pl["cogs"]),
    }

    # profit and loss: where the money came from and where it went
    pl_rows = [("Revenue from operations", revenue, "Income"), ("Other income", other, "Income"),
               ("Cost of materials", pl["cogs"], "Cost"), ("Employee benefits", pl["employee"], "Cost"),
               ("Finance costs", pl["fin"], "Cost"), ("Depreciation", pl["dep"], "Cost"),
               ("Other expenses", pl["other_exp"], "Cost"), ("Tax", pl["tax"], "Cost"), ("Profit for the year", m.profit, "Profit")]
    pl_bridge = pd.DataFrame([(n, v(a), k) for n, a, k in pl_rows if a], columns=["item", "amount", "kind"])

    split_at = next(i for i, x in enumerate(m.bs) if x.label == "ASSETS")
    assets = pd.DataFrame([(r.label.split(") ", 1)[-1], v(r.cur)) for r in m.bs[split_at:] if r.kind in ("item", "subitem") and r.cur],
                          columns=["item", "amount"])
    funding = pd.DataFrame([(r.label.split(") ", 1)[-1].split("  [")[0], v(r.cur)) for r in m.bs[:split_at]
                            if r.kind in ("item", "subitem") and r.cur], columns=["item", "amount"])

    # cash flow bridge
    opening, closing = m.cf["open"], m.cf["close"]
    cash_bridge = pd.DataFrame([
        ("Opening cash", v(opening), "Balance"),
        ("Operating activities", v(m.cf["cfo"]), "Flow"), ("Investing activities", v(m.cf["cfi"]), "Flow"),
        ("Financing activities", v(m.cf["cff"]), "Flow"), ("Closing cash", v(closing), "Balance")],
        columns=["step", "amount", "kind"])

    # the largest expense heads, from the notes
    heads = []
    for n in m.notes:
        if n.kind == "amounts" and any(k in n.title.lower() for k in ("other expenses", "employee benefit", "finance cost")):
            heads += [(r[0], v(r[1])) for r in n.rows if len(r) > 1 and isinstance(r[1], (int, float)) and r[1] > 0
                      and not r[0].startswith("Opening less")]
    top_expenses = pd.DataFrame(heads, columns=["item", "amount"]).sort_values("amount", ascending=False).head(10)

    working_capital = pd.DataFrame([(n, d) for n, d in (("Receivables", kpis["receivable_days"]), ("Payables", kpis["payable_days"]),
                                                       ("Inventory", kpis["inventory_days"])) if d is not None],
                                   columns=["measure", "days"])

    health = None
    if review is not None:
        s = review.summary
        health = {"passed": s["passed"], "failed": s["failed"], "checklist": dict(s["checklist"]),
                  "ratios_flagged": s["ratios_flagged"], "ratios_unmeasured": s["ratios_unmeasured"]}
    return {"unit": u, "kpis": kpis, "pl_bridge": pl_bridge, "assets": assets, "funding": funding, "cash_bridge": cash_bridge,
            "top_expenses": top_expenses, "working_capital": working_capital, "health": health,
            "balance_sheet_change": pd.DataFrame(
                [("Total assets", v(kpis["total_assets"]), "Current year"),
                 ("Total assets", v(next(r.prev for r in m.bs if r.label == "TOTAL ASSETS")), "Previous year"),
                 ("Equity", v(f["equity"]), "Current year"), ("Equity", v(prev["equity"]), "Previous year"),
                 ("Borrowings", v(f["ltb"] + f["stb"]), "Current year"), ("Borrowings", v(prev["ltb"] + prev["stb"]), "Previous year"),
                 ("Receivables", v(f["tr"]), "Current year"), ("Receivables", v(prev["tr"]), "Previous year"),
                 ("Payables", v(f["tp"]), "Current year"), ("Payables", v(prev["tp"]), "Previous year")],
                columns=["item", "amount", "year"])}
