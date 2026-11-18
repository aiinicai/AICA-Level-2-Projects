"""Trial Balance, Balance Sheet and Profit & Loss built from Tally's own live figures: every ledger's closing
balance comes from TallyPrime for the chosen period; this module only arranges them by Tally's group tree.
Sign convention follows Tally: negative = Dr, positive = Cr."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

ZERO = Decimal(0)

# Fallback classification when Tally doesn't return group flags (reserved primary groups)
_NATURE = {
    "Capital Account": "L", "Loans (Liability)": "L", "Current Liabilities": "L", "Suspense A/c": "L",
    "Branch / Divisions": "L", "Reserves & Surplus": "L", "Duties & Taxes": "L", "Provisions": "L",
    "Sundry Creditors": "L", "Bank OD A/c": "L", "Secured Loans": "L", "Unsecured Loans": "L",
    "Fixed Assets": "A", "Investments": "A", "Current Assets": "A", "Misc. Expenses (ASSET)": "A",
    "Bank Accounts": "A", "Cash-in-Hand": "A", "Deposits (Asset)": "A", "Loans & Advances (Asset)": "A",
    "Stock-in-Hand": "A", "Sundry Debtors": "A",
    "Sales Accounts": "DI", "Direct Incomes": "DI", "Purchase Accounts": "DE", "Direct Expenses": "DE",
    "Indirect Incomes": "II", "Indirect Expenses": "IE",
}


@dataclass
class Node:
    name: str
    kind: str = "group"                 # group | ledger | stock | profit | diff
    amount: Decimal = ZERO              # Tally sign
    children: list = field(default_factory=list)

    @property
    def dr(self) -> Decimal:
        return -self.amount if self.amount < 0 else ZERO

    @property
    def cr(self) -> Decimal:
        return self.amount if self.amount > 0 else ZERO

    def total(self) -> Decimal:
        if self.kind == "group":
            self.amount = sum((c.total() for c in self.children), ZERO)
        return self.amount

    def prune(self) -> "Node":
        self.children = [c.prune() for c in self.children if c.kind != "group" or c.has_value()]
        self.children = [c for c in self.children if c.kind != "ledger" or c.amount]
        return self

    def has_value(self) -> bool:
        return bool(self.amount) or any(c.has_value() for c in self.children)


def _is_primary(parent: str) -> bool:
    p = (parent or "").replace("\x04", "").strip().lower()
    return p in ("", "primary", "&#4; primary")


def _top(groups: dict[str, dict], g: str) -> str:
    seen = set()
    while g in groups and not _is_primary(groups[g].get("PARENT", "")) and g not in seen:
        seen.add(g)
        g = groups[g].get("PARENT", "").strip()
    return g


def nature(groups: dict[str, dict], top: str) -> str:
    """A asset, L liability, DI direct income, DE direct expense, II indirect income, IE indirect expense."""
    if top in _NATURE:
        return _NATURE[top]
    d = groups.get(top, {})
    yes = lambda k: str(d.get(k, "")).lower() == "yes"
    if yes("ISREVENUE"):
        if yes("AFFECTSGROSSPROFIT"):
            return "DE" if yes("ISDEEMEDPOSITIVE") else "DI"
        return "IE" if yes("ISDEEMEDPOSITIVE") else "II"
    return "A" if yes("ISDEEMEDPOSITIVE") else "L"


def tree(groups: dict[str, dict], amounts: dict[str, Decimal], ledger_parent: dict[str, str]) -> dict[str, Node]:
    """Top-level group name -> Node tree with sub-groups and ledgers."""
    nodes = {g: Node(g) for g in groups}
    tops: dict[str, Node] = {}
    for g, d in groups.items():
        p = d.get("PARENT", "").strip()
        if _is_primary(p) or p not in nodes:
            tops[g] = nodes[g]
        else:
            nodes[p].children.append(nodes[g])
    for led, amt in amounts.items():
        p = ledger_parent.get(led, "")
        node = Node(led, "ledger", amt)
        if p in nodes:
            nodes[p].children.append(node)
        else:                                    # e.g. Profit & Loss A/c sits at Primary
            tops.setdefault(led, Node(led, "ledger", amt))
    for n in tops.values():
        n.total()
        _sort(n)
    return tops


def _sort(n: Node):
    n.children.sort(key=lambda c: (c.kind != "group", c.name.lower()))
    for c in n.children:
        _sort(c)


@dataclass
class Reports:
    trial_balance: list[Node]
    pl_left: list[Node]          # expenses side
    pl_right: list[Node]         # income side
    gross_profit: Decimal
    net_profit: Decimal
    bs_liabilities: list[Node]
    bs_assets: list[Node]
    tb_dr: Decimal
    tb_cr: Decimal
    notes: list[str] = field(default_factory=list)
    # Tally layout: Trading Account, then Profit & Loss Account (each two-sided, with totals)
    trading_left: list = field(default_factory=list)
    trading_right: list = field(default_factory=list)
    trading_total: Decimal = ZERO
    plac_left: list = field(default_factory=list)
    plac_right: list = field(default_factory=list)
    plac_total: Decimal = ZERO
    stock_source: str = ""
    tally_tb: list = field(default_factory=list)          # Tally's own TB report: [(group, dr, cr)]
    tb_mismatch: list = field(default_factory=list)       # [(group, app dr, app cr, tally dr, tally cr)]


def build(groups: dict[str, dict], closings: dict[str, dict], before: dict[str, dict] | None,
          stock_period: tuple = (ZERO, ZERO), stock_cum: tuple = (ZERO, ZERO)) -> Reports:
    """closings: ledger closing balances at the period end (cumulative from FY start).
    before: closings on the day before the period starts (same FY) - subtracted for P&L items so the P&L shows
    the chosen period only. None when the period starts on the FY start."""
    parent = {n: d["parent"].strip() for n, d in closings.items()}
    cum = {n: d["closing"] for n, d in closings.items()}
    top_of = {n: _top(groups, parent.get(n, "")) or n for n in closings}
    nat = {n: nature(groups, top_of[n]) for n in closings}

    # Profit for the FY up to the period end (incl. stock movement) - Tally adds this to the P&L A/c ledger's
    # closing balance, but its Trial Balance shows only the brought-forward part (revenue ledgers carry the rest)
    cum_profit = sum((cum[n] for n in closings if nat[n] in ("DI", "DE", "II", "IE")), ZERO)
    open_stock_ledgers = [n for n in closings if top_of[n] == "Stock-in-Hand"]
    if stock_cum[0] or stock_cum[1]:
        cum_profit += stock_cum[1] - stock_cum[0]
    elif open_stock_ledgers:
        cum_profit += -sum((cum[n] for n in open_stock_ledgers), ZERO) + \
            sum((closings[n].get("opening", ZERO) or ZERO for n in open_stock_ledgers), ZERO)
    pl_name = next((n for n in closings if nat[n] in ("A", "L") and "profit" in n.lower()
                    and (_is_primary(parent.get(n, "")) or parent.get(n, "") not in groups)), None)
    cum_tb = dict(cum)
    if pl_name:
        cum_tb[pl_name] = cum[pl_name] - cum_profit          # brought forward from earlier years only

    # Trial balance: closing balances as at the period end
    tb = list(tree(groups, cum_tb, parent).values())
    for n in tb:
        n.prune()
    tb = [n for n in tb if n.has_value()]
    tb_dr = sum((n.dr for n in tb), ZERO)
    tb_cr = sum((n.cr for n in tb), ZERO)

    # P&L for the period
    def pl_amount(n):
        a = cum[n]
        if before is not None and n in before:
            a -= before[n]["closing"]
        return a
    pl_amts = {n: pl_amount(n) for n in closings if nat[n] in ("DI", "DE", "II", "IE")}
    pl_tops = tree(groups, pl_amts, parent)
    for n in pl_tops.values():
        n.prune()

    def side(kinds):
        return [n for g, n in sorted(pl_tops.items()) if nature(groups, g) in kinds and n.has_value()]
    open_stock, close_stock = stock_period
    stock_source = "stock items (as valued in Tally)" if (open_stock or close_stock) else ""
    if not open_stock and not close_stock:
        # accounting-only company: closing stock is kept in a ledger under Stock-in-Hand
        stock_leds = [n for n in closings if top_of[n] == "Stock-in-Hand"]
        if stock_leds:
            close_stock = -sum((cum[n] for n in stock_leds), ZERO)
            if before is not None:
                open_stock = -sum((before.get(n, {}).get("closing", ZERO) for n in stock_leds), ZERO)
            else:
                open_stock = -sum((closings[n].get("opening", ZERO) or ZERO for n in stock_leds), ZERO)
            stock_source = "Stock-in-Hand ledger(s)"
    dexp = side(("DE",))
    dinc = side(("DI",))
    gp = sum((n.amount for n in dinc + dexp), ZERO) + close_stock - open_stock   # Cr positive = profit
    iexp = side(("IE",))
    iinc = side(("II",))
    np_ = gp + sum((n.amount for n in iinc + iexp), ZERO)
    # Trading Account
    t_left = ([Node("Opening Stock", "stock", -open_stock)] if open_stock else []) + dexp
    t_right = dinc + ([Node("Closing Stock", "stock", close_stock)] if close_stock else [])
    if gp >= 0:
        t_left.append(Node("Gross Profit c/o", "profit", -gp))
    else:
        t_right.append(Node("Gross Loss c/o", "profit", -gp))
    t_total = sum((abs(n.amount) for n in t_left), ZERO)
    # Profit & Loss Account
    p_left = ([Node("Gross Loss b/f", "carry", gp)] if gp < 0 else []) + iexp
    p_right = ([Node("Gross Profit b/f", "carry", gp)] if gp >= 0 else []) + iinc
    if np_ >= 0:
        p_left.append(Node("Nett Profit", "profit", -np_))
    else:
        p_right.append(Node("Nett Loss", "profit", -np_))
    p_total = sum((abs(n.amount) for n in p_left), ZERO)
    left = t_left + p_left
    right = t_right + p_right

    # Balance sheet: cumulative position at the period end
    bs_amts = {n: cum_tb[n] for n in closings if nat[n] in ("A", "L")}
    bs_tops = tree(groups, bs_amts, parent)
    for n in bs_tops.values():
        n.prune()
    liab = [n for g, n in sorted(bs_tops.items()) if nature(groups, g) == "L" and n.has_value()]
    assets = [n for g, n in sorted(bs_tops.items()) if nature(groups, g) == "A" and n.has_value()]
    pl_ledger = next((n for n in bs_tops.values() if n.kind == "ledger" and "profit" in n.name.lower()), None)
    pl_node = Node("Profit & Loss A/c", "group",
                   children=([Node("Opening balance", "ledger", pl_ledger.amount)] if pl_ledger else []) +
                   [Node("Current period", "profit", cum_profit)])
    pl_node.total()
    liab = [n for n in liab if n is not pl_ledger] + [pl_node]
    assets = [n for n in assets if n is not pl_ledger]
    if stock_cum[1] and stock_source.startswith("stock items"):
        stock_node = Node("Closing Stock", "stock", -stock_cum[1])
        assets.append(stock_node)
    notes = []
    diff = sum((n.amount for n in liab + assets), ZERO)
    if abs(diff) >= Decimal("0.01"):
        notes.append(f"Difference of {abs(diff):,.2f} (usually opening balances or stock valuation) - "
                     f"compare with Tally's own Balance Sheet")
    return Reports(tb, left, right, gp, np_, liab, assets, tb_dr, tb_cr, notes, t_left, t_right, t_total,
                   p_left, p_right, p_total, stock_source)


def day_before(yyyymmdd: str) -> str:
    d = date(int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:8])) - timedelta(days=1)
    return d.strftime("%Y%m%d")


def fetch(client, company: str, frm: str, to: str, progress=lambda m: None) -> Reports:
    """Live from Tally: groups, ledger closings at period end (and the day before for P&L), stock values."""
    from .periods import fy_start
    progress("Reading groups")
    groups = client.groups(company)
    progress("Reading ledger balances")
    fys = fy_start(date(int(frm[:4]), int(frm[4:6]), int(frm[6:8]))).strftime("%Y%m%d")
    closings = client.ledger_closings(company, fys, to)
    before = None
    if frm > fys:
        progress("Reading balances before the period")
        before = client.ledger_closings(company, fys, day_before(frm))
    progress("Reading stock values")
    try:
        sp = client.stock_values(company, frm, to)
        sc = client.stock_values(company, fys, to)
    except Exception:
        sp = sc = (ZERO, ZERO)
    rep = build(groups, closings, before, sp, sc)
    progress("Cross-checking with Tally's own Trial Balance")
    try:
        tb, raw = client.trial_balance_report(company, frm, to)
        rep.tally_tb = tb
        add_tally_only_lines(rep, tb)
        rep.tb_mismatch = compare_tb(rep, tb)
        if rep.tb_mismatch:
            _save_diag(company, raw, closings, groups)
    except Exception as e:
        rep.notes.append(f"Tally's Trial Balance report could not be read for the cross-check ({str(e)[:80]})")
    return rep


# Lines Tally computes itself (no ledger behind them). "Unadjusted Forex Gain/Loss" is the revaluation gap on
# foreign-currency balances (seen in real company data); without it the TB and Balance Sheet don't tally.
TALLY_ONLY_LINES = ("unadjusted forex gain/loss",)


def add_tally_only_lines(rep: "Reports", tally_tb: list) -> None:
    have = {n.name.strip().lower() for n in rep.trial_balance}
    for name, dr, cr in tally_tb:
        key = (name or "").strip().lower()
        if key in TALLY_ONLY_LINES and key not in have and (dr or cr):
            amt = cr - dr                                  # Tally sign: negative = Dr
            node = Node(name.strip(), "ledger", amt)
            rep.trial_balance.append(node)
            rep.tb_dr += dr
            rep.tb_cr += cr
            (rep.bs_assets if amt < 0 else rep.bs_liabilities).append(Node(name.strip(), "ledger", amt))
            diff = sum((n.amount for n in rep.bs_liabilities + rep.bs_assets), ZERO)
            rep.notes = [x for x in rep.notes if not x.startswith("Difference of ")]
            if abs(diff) >= Decimal("0.01"):
                rep.notes.append(f"Difference of {abs(diff):,.2f} (usually opening balances or stock valuation) - "
                                 f"compare with Tally's own Balance Sheet")


def compare_tb(rep: "Reports", tally_tb: list) -> list:
    app = {n.name.strip().lower(): (n.dr, n.cr) for n in rep.trial_balance}
    out = []
    for name, dr, cr in tally_tb:
        if not name or name.lower().startswith(("grand total", "difference in opening")):
            continue
        a = app.get(name.strip().lower(), (ZERO, ZERO))
        if abs((a[0] - a[1]) - (dr - cr)) >= Decimal("1"):
            out.append((name, a[0], a[1], dr, cr))
    tally_names = {n.strip().lower() for n, _d, _c in tally_tb}
    for n in rep.trial_balance:
        if n.name.strip().lower() not in tally_names and (n.dr or n.cr) and tally_tb:
            out.append((n.name, n.dr, n.cr, ZERO, ZERO))
    return out


def _save_diag(company: str, raw: bytes, closings: dict, groups: dict) -> None:
    """Keep both sides on this PC so a mismatch can be investigated (Settings -> diagnostics folder)."""
    try:
        import json
        from ..config import app_dir
        d = app_dir() / "diagnostics"
        d.mkdir(exist_ok=True)
        safe = "".join(ch for ch in company if ch.isalnum())[:30]
        (d / f"tb_tally_{safe}.xml").write_bytes(raw)
        (d / f"tb_app_{safe}.json").write_text(json.dumps(
            {"closings": {k: {**v, "opening": str(v.get("opening")), "closing": str(v.get("closing"))}
                          for k, v in closings.items()},
             "groups": {k: {kk: str(vv) for kk, vv in g.items() if isinstance(vv, str)} for k, g in groups.items()}},
            indent=1))
    except Exception:
        pass


# ------------------------------------------------------------------ Excel
def to_excel(rep: Reports, path, company: str, period_text: str) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    wb = Workbook()
    bold = Font(bold=True)
    money = '#,##,##0.00'

    def put_tree(ws, nodes, row, depth=0, two_col=True):
        for n in nodes:
            ws.cell(row, 1, ("    " * depth) + n.name).font = Font(bold=n.kind == "group" and depth == 0)
            if two_col:
                if n.dr:
                    ws.cell(row, 2, float(n.dr)).number_format = money
                if n.cr:
                    ws.cell(row, 3, float(n.cr)).number_format = money
            else:
                ws.cell(row, 2, float(abs(n.amount))).number_format = money
            row += 1
            if n.kind == "group":
                row = put_tree(ws, n.children, row, depth + 1, two_col)
        return row

    ws = wb.active
    ws.title = "Trial Balance"
    ws.append([company])
    ws.append([f"Trial Balance · {period_text}"])
    ws.append(["Particulars", "Debit", "Credit"])
    for c in ws[3]:
        c.font = bold
    r = put_tree(ws, rep.trial_balance, 4)
    ws.cell(r, 1, "Grand Total").font = bold
    ws.cell(r, 2, float(rep.tb_dr)).number_format = money
    ws.cell(r, 3, float(rep.tb_cr)).number_format = money

    pl_a = [Node("TRADING ACCOUNT", "header")] + rep.trading_left + [Node("Total", "total", rep.trading_total),
                                                                       Node("PROFIT & LOSS ACCOUNT", "header")] + \
        rep.plac_left + [Node("Total", "total", rep.plac_total)]
    pl_b = [Node("TRADING ACCOUNT", "header")] + rep.trading_right + [Node("Total", "total", rep.trading_total),
                                                                        Node("PROFIT & LOSS ACCOUNT", "header")] + \
        rep.plac_right + [Node("Total", "total", rep.plac_total)]
    for title, a, b, la, lb in (("Profit & Loss", pl_a, pl_b, "Dr (expenses)", "Cr (income)"),
                                ("Balance Sheet", rep.bs_liabilities, rep.bs_assets, "Liabilities", "Assets")):
        ws = wb.create_sheet(title)
        ws.append([company])
        ws.append([f"{title} · {period_text}"])
        ws.append([la, "Amount"])
        ws.cell(3, 1).font = ws.cell(3, 2).font = bold
        r = put_tree(ws, a, 4, two_col=False)
        if title == "Balance Sheet":
            ws.cell(r, 1, "Total").font = bold
            ws.cell(r, 2, float(sum((abs(n.amount) for n in a), ZERO))).number_format = money
        r += 2
        ws.cell(r, 1, lb).font = bold
        ws.cell(r, 2, "Amount").font = bold
        r = put_tree(ws, b, r + 1, two_col=False)
        if title == "Balance Sheet":
            ws.cell(r, 1, "Total").font = bold
            ws.cell(r, 2, float(sum((abs(n.amount) for n in b), ZERO))).number_format = money
    for ws in wb.worksheets:
        ws.column_dimensions["A"].width = 48
        for col in "BC":
            ws.column_dimensions[col].width = 18
        ws.cell(1, 1).font = Font(bold=True, size=13)
        ws.cell(2, 1).alignment = Alignment(horizontal="left")
    wb.save(path)
