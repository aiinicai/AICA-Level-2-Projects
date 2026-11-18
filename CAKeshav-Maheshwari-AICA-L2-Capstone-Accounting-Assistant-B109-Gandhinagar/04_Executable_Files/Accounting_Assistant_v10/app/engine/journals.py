"""Multi-ledger journals: clone a past voucher, run a rule template, learn templates from
history, or build a salary journal from a salary register (Excel/CSV)."""
from __future__ import annotations

import re
import statistics
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .history import vouchers as _hv
from ..db.models import JournalTemplate, VoucherHistory
from .voucher import VLine, Voucher

Q = Decimal("0.01")
_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_MONTH_FULL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]


# ------------------------------------------------------------------ narration roll-forward
def roll_narration(text: str, months: int = 1) -> str:
    """'Rent for Oct-26' -> 'Rent for Nov-26'; also 'October 2026', '10/2026', 'Oct 2026'."""
    def shift(m_idx: int, year: int) -> tuple[int, int]:
        t = m_idx + months
        return t % 12, year + t // 12

    def full(m):
        i, y = shift(_MONTH_FULL.index(m.group(1).capitalize()), int(m.group(2)))
        return f"{_MONTH_FULL[i]} {y}"

    def short(m):
        y_raw = m.group(3)
        year = int(y_raw) + (2000 if len(y_raw) == 2 else 0)
        i, y = shift(_MON.index(m.group(1).capitalize()), year)
        return f"{_MON[i]}{m.group(2)}{str(y)[-2:] if len(y_raw) == 2 else y}"

    def numeric(m):
        i, y = shift(int(m.group(1)) - 1, int(m.group(2)))
        return f"{i + 1:02d}/{y}"

    text = re.sub(r"\b(" + "|".join(_MONTH_FULL) + r")\s+(\d{4})\b", full, text, flags=re.I)
    text = re.sub(r"\b(" + "|".join(_MON) + r")([\s\-'’]*)(\d{4}|\d{2})\b", short, text, flags=re.I)
    text = re.sub(r"\b(0?[1-9]|1[0-2])/(\d{4})\b", numeric, text)
    return text


# ------------------------------------------------------------------ clone
def recurring_vouchers(session: Session, company_id: str, min_months: int = 2) -> list[dict]:
    """Ledger sets that recur across months, newest example first."""
    groups: dict[frozenset, list[VoucherHistory]] = defaultdict(list)
    for v in _hv(session, company_id):
        if not re.search(r"journal", v.voucher_type, re.I) or len(v.entries) < 2:
            continue
        groups[frozenset(e["ledger"] for e in v.entries)].append(v)
    out = []
    for key, vs in groups.items():
        months = {v.date[:6] for v in vs}
        if len(months) >= min_months:
            vs.sort(key=lambda v: v.date, reverse=True)
            out.append({"ledgers": sorted(key), "months": len(months), "latest": vs[0], "all": vs})
    return sorted(out, key=lambda g: (-g["months"], g["latest"].narration))


def clone(src: VoucherHistory, new_date: str, amounts: dict[int, Decimal] | None = None,
          vtype: str | None = None) -> Voucher:
    lines = [VLine(e["ledger"], Decimal(e["amount"]) if not amounts or i not in amounts else amounts[i], e["dr"],
                   "other", f"Cloned from {src.date[6:8]}-{src.date[4:6]}-{src.date[:4]}", "amber") for i, e in enumerate(src.entries)]
    months = (int(new_date[:4]) - int(src.date[:4])) * 12 + int(new_date[4:6]) - int(src.date[4:6])
    return Voucher(vtype=vtype or src.voucher_type, base_type="Journal", date=new_date, lines=lines,
                   narration=roll_narration(src.narration, months) if months else src.narration)


# ------------------------------------------------------------------ templates
@dataclass
class TLine:
    ledger: str
    side: str                       # Dr | Cr
    expr: dict                      # {"type":"input","key":..} | {"type":"pct","of":idx,"rate":..}
                                    # | {"type":"fixed","amount":..} | {"type":"balance"}


def evaluate(lines: list[dict], inputs: dict[str, Decimal]) -> list[VLine]:
    vals: dict[int, Decimal] = {}
    pending_balance = None
    for _ in range(3):                                 # resolve pct-of chains
        for i, l in enumerate(lines):
            e = l["expr"]
            if i in vals:
                continue
            t = e.get("type")
            if t == "input":
                vals[i] = Decimal(str(inputs.get(e["key"], 0)))
            elif t == "fixed":
                vals[i] = Decimal(str(e["amount"]))
            elif t == "pct" and e["of"] in vals:
                vals[i] = (vals[e["of"]] * Decimal(str(e["rate"])) / 100).quantize(Decimal("1") if e.get("round")
                                                                                   else Q)
            elif t == "balance":
                pending_balance = i
    dr = sum((v for i, v in vals.items() if lines[i]["side"] == "Dr"), Decimal(0))
    cr = sum((v for i, v in vals.items() if lines[i]["side"] == "Cr"), Decimal(0))
    if pending_balance is not None:
        side = lines[pending_balance]["side"]
        vals[pending_balance] = (dr - cr) if side == "Cr" else (cr - dr)
    return [VLine(l["ledger"], vals.get(i, Decimal(0)).quantize(Q), l["side"] == "Dr", "other",
                  _describe(l["expr"], lines), "amber") for i, l in enumerate(lines)]


def _describe(e: dict, lines: list[dict]) -> str:
    t = e.get("type")
    if t == "input":
        return f"Input: {e['key']}"
    if t == "pct":
        return f"{e['rate']}% of {lines[e['of']]['ledger']}"
    if t == "balance":
        return "Balancing figure"
    return "Fixed amount"


def template_inputs(lines: list[dict]) -> list[str]:
    return [l["expr"]["key"] for l in lines if l["expr"].get("type") == "input"]


def learn_templates(session: Session, company_id: str, min_months: int = 3) -> list[JournalTemplate]:
    """Turn recurring journals into draft templates. Lines whose ratio to the largest debit is stable
    (<1% spread) become pct-of; the largest credit becomes the balancing line; the rest are inputs."""
    made = []
    existing = {t.name for t in session.scalars(select(JournalTemplate).where(JournalTemplate.company_id == company_id))}
    for g in recurring_vouchers(session, company_id, min_months):
        latest = g["latest"]
        base_i = max((i for i, e in enumerate(latest.entries) if e["dr"]),
                     key=lambda i: Decimal(latest.entries[i]["amount"]), default=0)
        base_ledger = latest.entries[base_i]["ledger"]
        bal_i = max((i for i, e in enumerate(latest.entries) if not e["dr"]),
                    key=lambda i: Decimal(latest.entries[i]["amount"]), default=None)
        lines = []
        for i, e in enumerate(latest.entries):
            side = "Dr" if e["dr"] else "Cr"
            if i == base_i:
                expr = {"type": "input", "key": base_ledger}
            elif i == bal_i:
                expr = {"type": "balance"}
            else:
                ratios = []
                for v in g["all"]:
                    amt = {x["ledger"]: Decimal(x["amount"]) for x in v.entries}
                    if amt.get(base_ledger) and e["ledger"] in amt:
                        ratios.append(float(amt[e["ledger"]] / amt[base_ledger] * 100))
                if len(ratios) >= 2 and statistics.pstdev(ratios) < 1 and statistics.mean(ratios) > 0:
                    expr = {"type": "pct", "of": base_i, "rate": round(statistics.mean(ratios), 2)}
                else:
                    expr = {"type": "input", "key": e["ledger"]}
            lines.append({"ledger": e["ledger"], "side": side, "expr": expr})
        name = re.sub(r"\s+", " ", re.sub(r"\d{1,2}[-/]\d{2,4}|\b(" + "|".join(_MON) + r")\w*[\s\-']*\d{2,4}", "",
                                          latest.narration or "", flags=re.I)).strip()[:60] or \
            f"{base_ledger} journal"
        if name in existing:
            continue
        t = JournalTemplate(company_id=company_id, name=name, voucher_type=latest.voucher_type, lines=lines,
                            narration=latest.narration, origin="learned")
        session.add(t)
        made.append(t)
        existing.add(name)
    session.commit()
    return made


# ------------------------------------------------------------------ salary register
def read_register(path: Path) -> tuple[list[str], dict[str, Decimal], int]:
    """Column totals of a salary register. Header row = first row with 3+ text cells.
    Returns (headers, totals per numeric column, employee rows)."""
    rows: list[list] = []
    if path.suffix.lower() == ".csv":
        import csv
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = [r for r in csv.reader(f)]
    else:
        from openpyxl import load_workbook
        ws = load_workbook(path, data_only=True, read_only=True).worksheets[0]
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    hdr_i = next(i for i, r in enumerate(rows) if sum(1 for c in r if isinstance(c, str) and c.strip()) >= 3)
    headers = [str(c).strip() if c is not None else "" for c in rows[hdr_i]]
    totals: dict[str, Decimal] = defaultdict(Decimal)
    n = 0
    for r in rows[hdr_i + 1:]:
        first = next((str(c) for c in r if c not in (None, "")), "")
        if not first or re.match(r"(grand\s+)?total", first, re.I):
            continue
        has_num = False
        for h, c in zip(headers, r):
            if not h:
                continue
            try:
                val = Decimal(str(c).replace(",", "")) if c not in (None, "") else None
            except Exception:
                val = None
            if val is not None:
                totals[h] += val
                has_num = True
        n += has_num
    numeric = [h for h in headers if h in totals]
    return numeric, dict(totals), n


def salary_journal(totals: dict[str, Decimal], mapping: dict[str, tuple[str, str]], payable_ledger: str,
                   date_: str, narration: str, vtype: str = "Journal") -> Voucher:
    """mapping: register column -> (ledger, 'Dr'|'Cr'). Balance goes to payable_ledger (Cr)."""
    lines = []
    for col, (ledger, side) in mapping.items():
        amt = totals.get(col, Decimal(0)).quantize(Q)
        if ledger and amt:
            lines.append(VLine(ledger, amt, side == "Dr", "other", f"Register column '{col}'", "green"))
    dr = sum((l.amount for l in lines if l.dr), Decimal(0))
    cr = sum((l.amount for l in lines if not l.dr), Decimal(0))
    lines.append(VLine(payable_ledger, dr - cr, False, "other", "Net salary payable (balance)", "green"))
    return Voucher(vtype=vtype, base_type="Journal", date=date_, lines=lines, narration=narration)
