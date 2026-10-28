"""Casting and tie-out checks. Pure arithmetic on the finished statements: no AI, fully reproducible.

Each Check says what was compared, the two figures, and the difference. Tolerance is zero for
statement arithmetic (whole rupees) and a few rupees where unrounded books are compared with
rounded statements.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..format import rs
from ..model import Model
from ..statements import line_totals

ROUNDING_TOLERANCE = 5   # rupees: sub-heads are rounded one by one, so books and statements can differ slightly


@dataclass
class Check:
    id: str
    area: str
    description: str
    expected: float | None
    actual: float | None
    status: str            # Pass | Fail
    severity: str = "High"

    @property
    def difference(self):
        if self.expected is None or self.actual is None:
            return None
        return self.actual - self.expected


def _chk(id, area, desc, expected, actual, tol=0):
    ok = abs(actual - expected) <= tol
    return Check(id, area, desc, expected, actual, "Pass" if ok else "Fail", "High")


def _bs_foots(m: Model) -> list[Check]:
    out, side, acc = [], None, {"cur": 0, "prev": 0}
    for r in m.bs:
        if r.kind == "head":
            side, acc = r.label, {"cur": 0, "prev": 0}
        elif r.kind in ("item", "subitem") and r.cur is not None:
            acc["cur"] += r.cur
            acc["prev"] += r.prev or 0
        elif r.kind == "total":
            out.append(_chk(f"BS-{len(out) + 1}", "Balance sheet", f"{r.label}: items add up (current year)", acc["cur"], r.cur))
            out.append(_chk(f"BS-{len(out) + 1}", "Balance sheet", f"{r.label}: items add up (previous year)", acc["prev"], r.prev))
    tot = {r.label: r for r in m.bs if r.kind == "total"}
    a, e = tot["TOTAL ASSETS"], tot["TOTAL EQUITY AND LIABILITIES"]
    out.append(_chk("BS-A", "Balance sheet", "Total assets = total equity and liabilities (current year)", e.cur, a.cur))
    out.append(_chk("BS-B", "Balance sheet", "Total assets = total equity and liabilities (previous year)", e.prev, a.prev))
    return out


def _pl_foots(m: Model) -> list[Check]:
    rows = {r.label: r for r in m.pl}
    exp_items = []
    inside = False
    for r in m.pl:
        if r.label.startswith("IV. Expenses"):
            inside = True
        elif r.label == "Total expenses":
            inside = False
        elif inside and r.kind == "item":
            exp_items.append(r.cur)
    inc = rows["I. Revenue from operations"].cur + rows["II. Other income"].cur
    tot_inc = rows["III. Total income (I + II)"].cur
    tot_exp = rows["Total expenses"].cur
    pbt = rows["V. Profit / (loss) before tax (III - IV)"].cur
    tax = rows["(1) Current tax"].cur + rows["(2) Deferred tax"].cur
    return [
        _chk("PL-1", "Profit and loss", "Total income = revenue + other income", inc, tot_inc),
        _chk("PL-2", "Profit and loss", "Total expenses = sum of expense lines", sum(exp_items), tot_exp),
        _chk("PL-3", "Profit and loss", "Profit before tax = total income - total expenses", tot_inc - tot_exp, pbt),
        _chk("PL-4", "Profit and loss", "Profit for the year = profit before tax - tax",
             pbt - tax, rows["VII. Profit / (loss) for the year (V - VI)"].cur),
    ]


def _notes(m: Model) -> list[Check]:
    out = []
    by_no = {n.no: n for n in m.notes}
    for n in m.notes:
        if n.kind == "text":          # the ratios note holds words, not amounts to add up
            continue
        rows = [r for r in n.rows if len(r) > 1 and r[1] is not None and not r[0].startswith(("Opening", "Add"))]
        for i, label in ((1, "current year"), (2, "previous year")):
            if len(n.total) > i:
                out.append(_chk(f"N{n.no}-{i}", "Notes", f"Note {n.no} ({n.title}): rows add up, {label}",
                                sum((r[i] or 0) for r in rows if len(r) > i), n.total[i]))
    for r in m.bs + m.pl:
        if r.note:
            n = by_no[r.note]
            out.append(_chk(f"F{r.note}", "Notes", f"Face of statement agrees to Note {n.no} ({n.title})", n.total[1], r.cur))
    return out


def _surplus_and_profit(m: Model) -> list[Check]:
    note = next((n for n in m.notes if n.title == "Reserves and surplus"), None)
    if note is None:
        return []
    get = lambda label: next(r for r in note.rows if r[0] == label)  # noqa: E731
    try:
        opening, add, closing = get("Opening balance")[1], get("Add: profit for the year")[1], get("Closing balance")[1]
    except StopIteration:
        return []
    return [
        _chk("PL-5", "Profit and loss", "Profit in the P&L = profit added to surplus in the reserves note", m.profit, add),
        _chk("PL-6", "Profit and loss", "Surplus rolls forward: opening + profit = closing", opening + add, closing),
    ]


def _cash_flow(m: Model) -> list[Check]:
    st = {"item": None}
    sums = {"ops_pre": 0, "wc": 0, "tax": 0, "B": 0, "C": 0}
    val = {}
    phase = "op_pre"
    for r in m.cashflow:
        L = r.label
        if r.kind == "total" and L.startswith("Operating profit before"):
            val["ops_pre"] = r.cur
            phase = "wc"
        elif r.kind == "total" and L.startswith("Cash generated"):
            val["cash_gen"] = r.cur
            phase = "tax"
        elif r.kind == "total" and L.startswith("Net cash from / (used in) operating"):
            val["A"] = r.cur
            phase = "B"
        elif r.kind == "total" and "investing activities (B)" in L:
            val["B"] = r.cur
            phase = "C"
        elif r.kind == "total" and "financing activities (C)" in L:
            val["C"] = r.cur
            phase = "D"
        elif r.kind == "total" and L.startswith("D. NET"):
            val["D"] = r.cur
        elif L.startswith("Cash and cash equivalents at the beginning"):
            val["open"] = r.cur
        elif L.startswith("Cash and cash equivalents at the end"):
            val["close"] = r.cur
        elif r.cur is not None and r.kind in ("item", "subitem"):
            key = {"op_pre": "ops_pre_items", "wc": "wc", "tax": "tax", "B": "B", "C": "C"}.get(phase)
            if key:
                sums[key] = sums.get(key, 0) + r.cur
    bs_cce_close = m.figures["cur"]["cce"]
    bs_cce_open = m.figures["prev"]["cce"]
    return [
        _chk("CF-1", "Cash flow", "Operating profit before working capital = profit before tax + adjustments",
             sums.get("ops_pre_items", 0), val["ops_pre"]),
        _chk("CF-2", "Cash flow", "Cash generated from operations = operating profit + working capital changes",
             val["ops_pre"] + sums["wc"], val["cash_gen"]),
        _chk("CF-3", "Cash flow", "Net cash from operating activities = cash generated - taxes paid",
             val["cash_gen"] + sums["tax"], val["A"]),
        _chk("CF-4", "Cash flow", "Investing activities add up", sums["B"], val["B"]),
        _chk("CF-5", "Cash flow", "Financing activities add up", sums["C"], val["C"]),
        _chk("CF-6", "Cash flow", "Net movement = A + B + C", val["A"] + val["B"] + val["C"], val["D"]),
        _chk("CF-7", "Cash flow", "Opening cash + net movement = closing cash", val["open"] + val["D"], val["close"]),
        _chk("CF-8", "Cash flow", "Closing cash agrees to cash and cash equivalents on the balance sheet", bs_cce_close, val["close"]),
        _chk("CF-9", "Cash flow", "Opening cash agrees to the previous year's balance sheet", bs_cce_open, val["open"]),
    ]


def _ppe(m: Model) -> list[Check]:
    note = next((n for n in m.notes if n.movement and n.kind != "text"), None)
    if note is None:
        return []
    mv = note.movement
    out = [_chk(f"PPE-{i + 1}", "Notes", f"PPE movement for {r[0]}: opening + additions + deductions = closing",
                r[1] + r[2] + r[3], r[4]) for i, r in enumerate(mv["rows"])]
    out.append(_chk("PPE-T", "Notes", "PPE movement closing agrees to the balance sheet", note.total[1], mv["total"][4]))
    return out


def _books(m: Model, mapped) -> list[Check]:
    """Statements against the unrounded Tally books."""
    out = []
    tol = ROUNDING_TOLERANCE * m.unit.step      # each sub-head is rounded to the presentation unit, so allow for that
    unmapped = mapped[mapped["line"] == "UNMAPPED"]
    amount = float(unmapped["closing"].abs().sum())
    out.append(Check("TB-1", "Trial balance", "Every ledger with a balance is mapped to a statement line "
                     f"({len(unmapped)} unmapped, {rs(amount)})", 0, amount, "Pass" if len(unmapped) == 0 else "Fail", "High"))
    t = line_totals(mapped)
    bs = t[t["statement"] == "BS"]
    side = {r.line: ("A" if r.line.startswith(("NCA", "CA.")) else "L") for r in bs.itertuples()}
    assets = float(sum(r.closing for r in bs.itertuples() if side[r.line] == "A"))
    assets_open = float(sum(r.opening for r in bs.itertuples() if side[r.line] == "A"))
    tot = {r.label: r for r in m.bs if r.kind == "total"}["TOTAL ASSETS"]
    out.append(_chk("TB-2", "Trial balance", "Total assets in the statements agree to the Tally books (within rounding)",
                    assets, tot.cur, tol))
    out.append(_chk("TB-3", "Trial balance", "Previous-year total assets agree to Tally's opening balances (within rounding)",
                    assets_open, tot.prev, tol))
    out.append(_chk("TB-4", "Trial balance", "Profit in the statements agrees to the profit in the Tally books (within rounding)",
                    float(t.attrs.get("profit", 0.0)), m.profit, tol))
    return out


def run_tieouts(m: Model, mapped) -> list[Check]:
    return (_bs_foots(m) + _pl_foots(m) + _surplus_and_profit(m) + _cash_flow(m) + _ppe(m) + _notes(m) + _books(m, mapped))
