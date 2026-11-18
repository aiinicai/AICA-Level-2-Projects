"""Builds the FACTS the assistant may quote, and checks its answer against them.

The Python engine does all the calculating. The model only receives finished figures and puts them into words, and every
number in its reply is then checked against those figures.
"""
from __future__ import annotations

import re

from ..engine import reports as R
from ..engine.analytics import cost_analysis, revenue_analysis
from ..engine.cashflow_ageing import ageing
from ..engine.kpi import DASHBOARD_DEFAULT, evaluate_kpis

STATUS_WORD = {"actual": "actual", "calculated": "calculated", "estimated": "ESTIMATED", "unavailable": "not available"}


def inr(x: float | None) -> str:
    """Indian digit grouping: 1,81,27,955.66"""
    if x is None:
        return "n/a"
    neg, x = x < 0, abs(x)
    whole, frac = f"{x:.2f}".split(".")
    head, tail = whole[:-3], whole[-3:]
    if head:
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        tail = ",".join(parts) + "," + tail
    return f"{'-' if neg else ''}₹{tail}.{frac}"


def fmt_value(v, unit: str) -> str:
    if v is None:
        return "not available"
    if unit == "currency":
        return inr(v)
    if unit == "percent":
        return f"{v:.2f}%"
    if unit == "days":
        return f"{v:.1f} days"
    if unit == "months":
        return f"{v:.1f} months"
    return f"{v:.2f}"


def build_facts(f: R.Filters, question: str = "") -> list[str]:
    ctx = f.ctx
    out: list[str] = [
        f"Company: {ctx.company['name']}",
        f"Period: {f.range[0]} to {f.range[1]}",
        f"Compared with: {f.prev[0]} to {f.prev[1]}" if f.prev else "Compared with: nothing (no comparison selected)",
        "Amounts are in Indian rupees (₹).",
    ]
    for k in evaluate_kpis(ctx, f.range, f.prev, codes=list(dict.fromkeys(list(DASHBOARD_DEFAULT) + ["revenue_growth_pct", "ebitda_margin_pct", "interest_coverage", "quick_ratio",
                                                                                                         "inventory_days", "payable_days", "overdue_receivables_pct"]))):
        cur = k["current"]
        line = f"{k['name']}: {fmt_value(cur['value'], k['unit'])} ({STATUS_WORD[cur['status']]})"
        c = k["comparison"]
        if c and c["previous"] is not None:
            line += f"; previous period {fmt_value(c['previous'], k['unit'])}"
            if c["pctChange"] is not None:
                line += f"; change {c['pctChange']:.2f}%"
        out.append(line)
    try:
        prod = R.pnl_products(f)
        rows = sorted(prod.get("rows") or [], key=lambda r: -(r.get("netSales") or 0))[:5] if prod.get("available") else []
    except Exception:
        rows = []
    for r in rows:
        mp = r.get("marginPct")
        out.append(f"Product sales — {r['item']}: {inr(r['netSales'])}" + (f"; gross margin {mp:.1f}%" if mp is not None else ""))
    rev = revenue_analysis(ctx, f.range, f.prev)
    for c in rev["customers"][:5]:
        out.append(f"Sales made to customer (revenue, not money owed) — {c['customer']}: {inr(c['amount'])}" + (f" ({c['sharePct']:.1f}% of sales)" if c["sharePct"] is not None else ""))
    for l in rev["ledgers"][:4]:
        out.append(f"Revenue ledger — {l['ledger']}: {inr(l['amount'])}")
    cost = cost_analysis(ctx, f.range, f.prev)
    for l in cost["ledgers"][:8]:
        line = f"Expense — {l['ledger']}: {inr(l['amount'])}"
        if l["previous"] is not None:
            line += f"; previous period {inr(l['previous'])}"
        out.append(line)
    if ctx.cost_centre_id is None:
        for kind, label, plural in (("receivable", "Customer owes us", "Total receivables (money customers owe us)"),
                                    ("payable", "We owe supplier", "Total payables (money we owe suppliers)")):
            a = ageing(ctx, kind, f.range[1])
            t = a["totals"]
            out.append(f"{plural}: {inr(R.r2(t['ledgerBalance']))}; overdue {inr(R.r2(t['overdue']))}")
            for p in a["parties"][:5]:
                out.append(f"{label} — {p['party']}: {inr(R.r2(p['ledgerBalance']))}; overdue {inr(R.r2(p['overdue']))}")
    # any ledger the question names
    q = question.lower()
    seen = 0
    for e in ctx.chart.entries.values():
        if len(e.name) >= 4 and e.name.lower() in q and seen < 5:
            s = R.ledger_statement(ctx, e.ledger_id, f.range, 1, 1)
            if s:
                out.append(f"Ledger {e.name}: opening {inr(s['opening'])}, closing {inr(s['closing'])} (under {e.group_name or 'no group'})")
                seen += 1
    return out


# ------------------------------------------------------------------------------------------------ checking the reply
_NUM = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")


def numbers_in(text: str) -> list[str]:
    out = []
    for m in _NUM.finditer(text):
        t = m.group(0).replace(",", "").lstrip("-")
        out.append(t)
    return out


def _value(t: str) -> float:
    return float(t)


def unmatched_numbers(answer: str, facts: list[str], question: str) -> list[str]:
    """Numbers in the reply that are not in the facts (or the question). List markers like '1.' are ignored."""
    allowed_text = "\n".join(facts) + "\n" + question
    allowed = {_value(t) for t in numbers_in(allowed_text)}
    bad: list[str] = []
    for line in answer.splitlines():
        line = re.sub(r"^\s*(\d{1,2})[.)]\s+", "", line)  # numbered list markers
        for t in numbers_in(line):
            v = _value(t)
            if any(abs(v - a) <= 0.0051 for a in allowed):
                continue
            if t not in bad:
                bad.append(t)
    return bad
