"""Schedule III (Division I - companies following Accounting Standards): Balance Sheet and Statement of Profit
and Loss with notes, from Tally's live ledger balances. Each ledger is mapped once per company to a line item;
the app suggests the line item from the Tally group and the ledger name, the user can change it, and the mapping
is remembered."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

ZERO = Decimal(0)

# code -> (statement, section, line item). Order = presentation order.
LINES: list[tuple[str, str, str, str]] = [
    # ---- Balance Sheet: Equity and Liabilities
    ("SH_CAP", "BS", "Shareholders' funds", "Share capital"),
    ("SH_RES", "BS", "Shareholders' funds", "Reserves and surplus"),
    ("SH_WAR", "BS", "Shareholders' funds", "Money received against share warrants"),
    ("SH_APP", "BS", "Share application money pending allotment", "Share application money pending allotment"),
    ("NCL_BOR", "BS", "Non-current liabilities", "Long-term borrowings"),
    ("NCL_DTL", "BS", "Non-current liabilities", "Deferred tax liabilities (net)"),
    ("NCL_OTH", "BS", "Non-current liabilities", "Other long-term liabilities"),
    ("NCL_PRO", "BS", "Non-current liabilities", "Long-term provisions"),
    ("CL_BOR", "BS", "Current liabilities", "Short-term borrowings"),
    ("CL_TP_MSME", "BS", "Current liabilities", "Trade payables - micro and small enterprises"),
    ("CL_TP", "BS", "Current liabilities", "Trade payables - others"),
    ("CL_OTH", "BS", "Current liabilities", "Other current liabilities"),
    ("CL_PRO", "BS", "Current liabilities", "Short-term provisions"),
    # ---- Balance Sheet: Assets
    ("NCA_PPE", "BS", "Non-current assets", "Property, Plant and Equipment"),
    ("NCA_INT", "BS", "Non-current assets", "Intangible assets"),
    ("NCA_CWIP", "BS", "Non-current assets", "Capital work-in-progress"),
    ("NCA_IAUD", "BS", "Non-current assets", "Intangible assets under development"),
    ("NCA_INV", "BS", "Non-current assets", "Non-current investments"),
    ("NCA_DTA", "BS", "Non-current assets", "Deferred tax assets (net)"),
    ("NCA_LLA", "BS", "Non-current assets", "Long-term loans and advances"),
    ("NCA_OTH", "BS", "Non-current assets", "Other non-current assets"),
    ("CA_INV", "BS", "Current assets", "Current investments"),
    ("CA_STK", "BS", "Current assets", "Inventories"),
    ("CA_TR", "BS", "Current assets", "Trade receivables"),
    ("CA_CASH", "BS", "Current assets", "Cash and cash equivalents"),
    ("CA_SLA", "BS", "Current assets", "Short-term loans and advances"),
    ("CA_OTH", "BS", "Current assets", "Other current assets"),
    # ---- Statement of Profit and Loss
    ("PL_REV", "PL", "Income", "Revenue from operations"),
    ("PL_OI", "PL", "Income", "Other income"),
    ("PL_MAT", "PL", "Expenses", "Cost of materials consumed"),
    ("PL_PUR", "PL", "Expenses", "Purchases of Stock-in-Trade"),
    ("PL_CHG", "PL", "Expenses", "Changes in inventories of finished goods, work-in-progress and Stock-in-Trade"),
    ("PL_EMP", "PL", "Expenses", "Employee benefits expense"),
    ("PL_FIN", "PL", "Expenses", "Finance costs"),
    ("PL_DEP", "PL", "Expenses", "Depreciation and amortization expense"),
    ("PL_OTH", "PL", "Expenses", "Other expenses"),
    ("PL_EXC", "PL", "Exceptional and extraordinary items", "Exceptional items"),
    ("PL_TAX_CUR", "PL", "Tax expense", "Current tax"),
    ("PL_TAX_DEF", "PL", "Tax expense", "Deferred tax"),
    ("IGNORE", "", "", "Not shown (e.g. suspense / control ledger)"),
]
LINE = {c: (st, sec, name) for c, st, sec, name in LINES}
LIABILITY_SIDE = {c for c, st, sec, _ in LINES if st == "BS" and (sec.startswith("Shareholders") or "liabilities"
                                                                   in sec.lower() or sec.startswith("Share app"))}
INCOME = {"PL_REV", "PL_OI"}

# Tally primary group -> default line item
_BY_GROUP = {
    "Capital Account": "SH_CAP", "Reserves & Surplus": "SH_RES", "Secured Loans": "NCL_BOR",
    "Unsecured Loans": "NCL_BOR", "Loans (Liability)": "NCL_BOR", "Bank OD A/c": "CL_BOR",
    "Sundry Creditors": "CL_TP", "Duties & Taxes": "CL_OTH", "Provisions": "CL_PRO",
    "Current Liabilities": "CL_OTH", "Suspense A/c": "CL_OTH",   # shown, never dropped (the BS would not balance); flagged in notes "Branch / Divisions": "CL_OTH",
    "Fixed Assets": "NCA_PPE", "Investments": "NCA_INV", "Stock-in-Hand": "CA_STK", "Sundry Debtors": "CA_TR",
    "Cash-in-Hand": "CA_CASH", "Bank Accounts": "CA_CASH", "Deposits (Asset)": "NCA_LLA",
    "Loans & Advances (Asset)": "CA_SLA", "Current Assets": "CA_OTH", "Misc. Expenses (ASSET)": "NCA_OTH",
    "Sales Accounts": "PL_REV", "Direct Incomes": "PL_REV", "Indirect Incomes": "PL_OI",
    "Purchase Accounts": "PL_PUR", "Direct Expenses": "PL_OTH", "Indirect Expenses": "PL_OTH",
}
# name keywords that override the group default (first match wins), limited to a statement
_BY_NAME = [
    (r"\bshare\s*capital|equity\s*share|preference\s*share", "SH_CAP"),
    (r"share\s*application", "SH_APP"),
    (r"general\s*reserve|securities\s*premium|capital\s*reserve|surplus|profit\s*&?\s*loss", "SH_RES"),
    (r"deferred\s*tax\s*liab", "NCL_DTL"), (r"deferred\s*tax\s*asset", "NCA_DTA"),
    (r"\b(cc|od|cash\s*credit|overdraft|working\s*capital|packing\s*credit)\b", "CL_BOR"),
    (r"current\s*maturit", "CL_BOR"),
    (r"\bmsme|micro|small\s*enterprise", "CL_TP_MSME"),
    (r"provision\s*for\s*(income\s*)?tax|income\s*tax\s*provision", "CL_PRO"),
    (r"gratuity|leave\s*encash", "NCL_PRO"),
    (r"software|goodwill|trademark|patent|copyright|licen[cs]e", "NCA_INT"),
    (r"capital\s*work|\bcwip\b", "NCA_CWIP"),
    (r"fixed\s*deposit|\bfd\b|term\s*deposit", "CA_CASH"),
    (r"security\s*deposit|rent\s*deposit|electricity\s*deposit", "NCA_LLA"),
    (r"prepaid|advance\s*tax|tds\s*receivable|tcs\s*receivable|gst\s*input|input\s*(c|s|i)gst|itc|"
     r"electronic\s*(cash|credit)", "CA_OTH"),
    (r"salar|wages|bonus|\bpf\b|provident|\besi|gratuity|staff\s*welfare|leave\s*encash|director.?s?\s*remun",
     "PL_EMP"),
    (r"\binterest\b(?!.*(received|income))|loan\s*processing|finance\s*charge", "PL_FIN"),
    (r"depreciat|amorti", "PL_DEP"),
    (r"current\s*tax|income\s*tax(?!\s*refund)", "PL_TAX_CUR"),
    (r"deferred\s*tax", "PL_TAX_DEF"),
    (r"raw\s*material|consumption|material\s*consumed", "PL_MAT"),
    (r"interest\s*(received|income)|dividend|rent\s*received|profit\s*on\s*sale|discount\s*received", "PL_OI"),
]


def suggest(ledger: str, primary_group: str, group: str = "", closing: Decimal = ZERO) -> str:
    """Line item code for a ledger, from its Tally primary group and name."""
    base = _BY_GROUP.get(primary_group, "")
    stmt = LINE[base][0] if base else ""
    text = f"{ledger} {group}".lower()
    for pat, code in _BY_NAME:
        if re.search(pat, text) and (not stmt or LINE[code][0] == stmt):
            return code
    if base:
        # a debtor with a credit balance is an advance from customer, a creditor with a debit balance an advance
        if base == "CA_TR" and closing > 0:
            return "CL_OTH"
        if base == "CL_TP" and closing < 0:
            return "CA_SLA"
        if base in ("CL_OTH", "CL_PRO") and closing < 0:       # duties / liabilities with a debit balance
            return "CA_OTH"
        return base
    return "IGNORE" if "profit & loss" in ledger.lower() else ("CL_OTH" if closing > 0 else "CA_OTH")


def is_pl_account(name: str, parent: str, groups: dict) -> bool:
    """Tally's built-in 'Profit & Loss A/c' ledger (sits at Primary)."""
    p = (parent or "").strip()
    return "profit" in name.lower() and "loss" in name.lower() and (p.lower() == "primary" or not p or p not in groups)


@dataclass
class Item:
    code: str
    name: str
    note: int = 0
    current: Decimal = ZERO          # presentation sign: positive = normal balance for the side
    previous: Decimal = ZERO
    ledgers: list = field(default_factory=list)    # [(ledger, current, previous)]


@dataclass
class Statements:
    bs: list            # [(section, [Item])] equity & liabilities first, then assets
    pl: list            # [(section, [Item])]
    totals: dict        # current/previous totals and profit
    unmapped: list      # ledgers that used a suggestion (not confirmed by the user)
    notes: list = field(default_factory=list)


def _present(code: str, tally_amt: Decimal) -> Decimal:
    """Tally sign (negative = Dr) -> presentation sign for the line item's side."""
    if code in LIABILITY_SIDE or code in INCOME:
        return tally_amt
    return -tally_amt


def build(ledgers: dict[str, dict], cur_bs: dict[str, Decimal], prev_bs: dict[str, Decimal],
          cur_pl: dict[str, Decimal], prev_pl: dict[str, Decimal], mapping: dict[str, str],
          stock: dict | None = None, profit_before: tuple = (ZERO, ZERO)) -> Statements:
    """ledgers: name -> {_primary, _group}; *_bs: closing balances (Tally sign) at the two balance-sheet dates;
    *_pl: period movements for revenue ledgers (Tally sign); stock: {"cur_open","cur_close","prev_open","prev_close"}.
    mapping: confirmed line items {ledger: code}. profit_before: profit of the same FY before the period starts
    (period not starting on 1 April) - it also sits in Reserves and surplus at the balance-sheet date."""
    stock = stock or {}
    items: dict[str, Item] = {c: Item(c, LINE[c][2]) for c, *_ in LINES if c != "IGNORE"}
    unmapped = []
    names = set(cur_bs) | set(prev_bs) | set(cur_pl) | set(prev_pl)
    for n in sorted(names):
        d = ledgers.get(n, {})
        if d.get("_group") == "Profit & Loss A/c":
            mapping = {**mapping, n: "SH_RES"}          # always Surplus (brought forward)
        is_pl = n in cur_pl or n in prev_pl
        c_amt = cur_pl.get(n, ZERO) if is_pl else cur_bs.get(n, ZERO)
        p_amt = prev_pl.get(n, ZERO) if is_pl else prev_bs.get(n, ZERO)
        if not c_amt and not p_amt:
            continue
        code = mapping.get(n)
        if code not in LINE:
            code = suggest(n, d.get("_primary", ""), d.get("_group", ""), c_amt)
            unmapped.append((n, code))
        if code == "IGNORE":
            continue
        it = items[code]
        cp, pp = _present(code, c_amt), _present(code, p_amt)
        it.current += cp
        it.previous += pp
        it.ledgers.append((n, cp, pp))
    # inventories and their change
    items["CA_STK"].current += stock.get("cur_close", ZERO)
    items["CA_STK"].previous += stock.get("prev_close", ZERO)
    if stock.get("cur_close") or stock.get("prev_close"):
        items["CA_STK"].ledgers.append(("Closing stock (as valued in Tally)", stock.get("cur_close", ZERO),
                                        stock.get("prev_close", ZERO)))
    chg_c = stock.get("cur_open", ZERO) - stock.get("cur_close", ZERO)
    chg_p = stock.get("prev_open", ZERO) - stock.get("prev_close", ZERO)
    if chg_c or chg_p:
        items["PL_CHG"].current += chg_c
        items["PL_CHG"].previous += chg_p
        items["PL_CHG"].ledgers += [("Opening stock", stock.get("cur_open", ZERO), stock.get("prev_open", ZERO)),
                                    ("Less: closing stock", -stock.get("cur_close", ZERO),
                                     -stock.get("prev_close", ZERO))]

    # profit for the period
    def sums(codes, attr):
        return sum((getattr(items[c], attr) for c in codes), ZERO)
    exp_codes = ["PL_MAT", "PL_PUR", "PL_CHG", "PL_EMP", "PL_FIN", "PL_DEP", "PL_OTH"]
    rev_c, rev_p = sums(INCOME, "current"), sums(INCOME, "previous")
    exp_c, exp_p = sums(exp_codes, "current"), sums(exp_codes, "previous")
    pbt_c = rev_c - exp_c - items["PL_EXC"].current
    pbt_p = rev_p - exp_p - items["PL_EXC"].previous
    tax_c = items["PL_TAX_CUR"].current + items["PL_TAX_DEF"].current
    tax_p = items["PL_TAX_CUR"].previous + items["PL_TAX_DEF"].previous
    pat_c, pat_p = pbt_c - tax_c, pbt_p - tax_p
    # this year's profit sits in Reserves and surplus (surplus in the Statement of P&L)
    res = items["SH_RES"]
    res.current += pat_c
    res.previous += pat_p
    res.ledgers.append(("Add: Profit / (loss) for the period", pat_c, pat_p))
    if profit_before[0] or profit_before[1]:
        res.current += profit_before[0]
        res.previous += profit_before[1]
        res.ledgers.append(("Add: Profit / (loss) of the year before this period", profit_before[0],
                            profit_before[1]))

    # notes numbered in order of appearance (only items with a value)
    note = 1
    bs_sections, pl_sections = [], []
    for stmt, target in (("BS", bs_sections), ("PL", pl_sections)):
        cur_sec, bucket = None, []
        for c, st, sec, _ in LINES:
            if st != stmt or c == "IGNORE":
                continue
            it = items[c]
            if not it.current and not it.previous:
                continue
            if c != "PL_CHG" or it.ledgers:
                it.note = note
                note += 1
            if sec != cur_sec:
                if bucket:
                    target.append((cur_sec, bucket))
                cur_sec, bucket = sec, []
            bucket.append(it)
        if bucket:
            target.append((cur_sec, bucket))
    eq_c = sum((it.current for sec, its in bs_sections for it in its if it.code in LIABILITY_SIDE), ZERO)
    eq_p = sum((it.previous for sec, its in bs_sections for it in its if it.code in LIABILITY_SIDE), ZERO)
    as_c = sum((it.current for sec, its in bs_sections for it in its if it.code not in LIABILITY_SIDE), ZERO)
    as_p = sum((it.previous for sec, its in bs_sections for it in its if it.code not in LIABILITY_SIDE), ZERO)
    notes = []
    if abs(eq_c - as_c) >= Decimal("0.01"):
        notes.append(f"Balance Sheet differs by {abs(eq_c - as_c):,.2f} (current year) - usually opening balance "
                     f"difference in Tally or stock valuation")
    susp = [(n, c) for n, c in cur_bs.items() if ledgers.get(n, {}).get("_primary") == "Suspense A/c" and c]
    if susp:
        notes.append(f"Suspense balances of {abs(sum((c for _n, c in susp), ZERO)):,.2f} net are shown under other "
                     f"current assets / liabilities ({', '.join(n for n, _c in susp)}) - clear them before finalising")
    if unmapped:
        notes.append(f"{len(unmapped)} ledger(s) use a suggested line item - confirm them on the Mapping tab")
    return Statements(bs_sections, pl_sections,
                      {"eq_c": eq_c, "eq_p": eq_p, "as_c": as_c, "as_p": as_p, "rev_c": rev_c, "rev_p": rev_p,
                       "exp_c": exp_c, "exp_p": exp_p, "pbt_c": pbt_c, "pbt_p": pbt_p, "tax_c": tax_c,
                       "tax_p": tax_p, "pat_c": pat_c, "pat_p": pat_p}, unmapped, notes)


# ------------------------------------------------------------------ live from Tally
def fetch(client, company: str, frm: str, to: str, masters_ledgers: dict, mapping: dict, progress=lambda m: None):
    """Current period + the same period a year earlier, all figures from Tally."""
    from .periods import fy_start
    from .reports import day_before, nature

    def ymd(s):
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))

    def back(s):
        d = ymd(s)
        try:
            return d.replace(year=d.year - 1).strftime("%Y%m%d")
        except ValueError:                       # 29-Feb
            return d.replace(year=d.year - 1, day=28).strftime("%Y%m%d")
    progress("Reading groups")
    groups = client.groups(company)

    def period(f, t):
        fys = fy_start(ymd(f)).strftime("%Y%m%d")
        cl = client.ledger_closings(company, fys, t)
        before = client.ledger_closings(company, fys, day_before(f)) if f > fys else {}
        try:
            so, sc = client.stock_values(company, f, t)
        except Exception:
            so = sc = ZERO
        stock_gain = ZERO
        fy_open = so
        if before:
            try:
                fy_open, close_before = client.stock_values(company, fys, day_before(f))
                stock_gain = abs(close_before) - abs(fy_open)
            except Exception:
                pass
        try:
            tb, _raw = client.trial_balance_report(company, f, t)
        except Exception:
            tb = []
        return cl, before, so, sc, stock_gain, abs(sc) - abs(fy_open), tb
    progress("Reading this period")
    cl, before, so, sc, gain, cum_stock, tb = period(frm, to)
    progress("Reading the previous year")
    pf, pt = back(frm), back(to)
    try:
        pcl, pbefore, pso, psc, pgain, pcum_stock, ptb = period(pf, pt)
    except Exception:
        pcl, pbefore, pso, psc, pgain, pcum_stock, ptb = {}, {}, ZERO, ZERO, ZERO, ZERO, []
    from .reports import _top
    ledgers = dict(masters_ledgers)

    def split(closings, bef, cum_stock=ZERO, tally_tb=()):
        bs, pl = {}, {}
        fy_profit = cum_stock + sum((d["closing"] for d in closings.values()
                                     if nature(groups, _top(groups, d["parent"].strip()) or d["parent"])
                                     in ("DI", "DE", "II", "IE")), ZERO)
        for n, d in closings.items():
            if is_pl_account(n, d["parent"], groups):
                # Tally's closing for P&L A/c already includes this FY's profit; keep only the brought-forward part
                ledgers[n] = {"_primary": "Reserves & Surplus", "_group": "Profit & Loss A/c"}
                bs[n] = d["closing"] - fy_profit
                continue
            top = _top(groups, d["parent"].strip()) or d["parent"]
            nat = nature(groups, top)
            ledgers.setdefault(n, {"_primary": top, "_group": d["parent"]})
            if nat in ("DI", "DE", "II", "IE"):
                pl[n] = d["closing"] - (bef.get(n, {}).get("closing", ZERO) if bef else ZERO)
            else:
                bs[n] = d["closing"]
        for name, dr, cr in tally_tb:                 # lines Tally computes itself (forex revaluation)
            if (name or "").strip().lower() == "unadjusted forex gain/loss" and (dr or cr):
                ledgers[name.strip()] = {"_primary": "Unadjusted Forex", "_group": ""}
                bs[name.strip()] = cr - dr
        return bs, pl
    cbs, cpl = split(cl, before, cum_stock, tb)
    pbs, ppl = split(pcl, pbefore, pcum_stock, ptb)

    def earlier_profit(bef):                 # P&L ledgers before the period (Tally sign: Cr = profit)
        return sum((d["closing"] for n, d in bef.items()
                    if nature(groups, _top(groups, d["parent"].strip()) or d["parent"]) in ("DI", "DE", "II", "IE")),
                   ZERO)
    st = build(ledgers, cbs, pbs, cpl, ppl, mapping,
               {"cur_open": abs(so), "cur_close": abs(sc), "prev_open": abs(pso), "prev_close": abs(psc)},
               (earlier_profit(before) + gain if before else ZERO, earlier_profit(pbefore) + pgain if pbefore
                else ZERO))
    st.period = (frm, to, pf, pt)
    st.ledgers = ledgers
    st.balances = {**{n: v for n, v in cbs.items()}, **cpl}
    return st


# ------------------------------------------------------------------ Excel
def to_excel(st: Statements, path, company: str, period_text: str, prev_text: str) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side
    wb = Workbook()
    bold, money = Font(bold=True), '#,##,##0.00;(#,##,##0.00);"-"'
    thin = Border(top=Side(style="thin"), bottom=Side(style="double"))

    def head(ws, title):
        ws.append([company])
        ws.append([title])
        ws.append(["Particulars", "Note No.", period_text, prev_text])
        for c in ws[1] + ws[3]:
            c.font = bold
        ws.column_dimensions["A"].width = 64
        ws.column_dimensions["B"].width = 10
        ws.column_dimensions["C"].width = 20
        ws.column_dimensions["D"].width = 20

    def row(ws, label, note="", cur=None, prev=None, b=False, indent=0):
        ws.append([("   " * indent) + label, note or None, float(cur) if cur is not None else None,
                   float(prev) if prev is not None else None])
        r = ws.max_row
        for col in (3, 4):
            ws.cell(r, col).number_format = money
        if b:
            for col in range(1, 5):
                ws.cell(r, col).font = bold
        ws.cell(r, 2).alignment = Alignment(horizontal="center")
        return r

    ws = wb.active
    ws.title = "Balance Sheet"
    head(ws, f"Balance Sheet as at {period_text}")
    t = st.totals
    row(ws, "I. EQUITY AND LIABILITIES", b=True)
    done_eq = False
    for sec, its in st.bs:
        is_liab = its[0].code in LIABILITY_SIDE
        if not is_liab and not done_eq:
            r = row(ws, "TOTAL", cur=t["eq_c"], prev=t["eq_p"], b=True)
            for col in (3, 4):
                ws.cell(r, col).border = thin
            row(ws, "")
            row(ws, "II. ASSETS", b=True)
            done_eq = True
        row(ws, sec, b=True, indent=1)
        for it in its:
            row(ws, it.name, it.note, it.current, it.previous, indent=2)
    if not done_eq:
        row(ws, "TOTAL", cur=t["eq_c"], prev=t["eq_p"], b=True)
    r = row(ws, "TOTAL", cur=t["as_c"], prev=t["as_p"], b=True)
    for col in (3, 4):
        ws.cell(r, col).border = thin

    ws = wb.create_sheet("Profit and Loss")
    head(ws, f"Statement of Profit and Loss for the period {period_text}")
    items = {it.code: it for _s, its in st.pl for it in its}

    def g(code, attr):
        return getattr(items[code], attr) if code in items else ZERO
    for label, code in (("I. Revenue from operations", "PL_REV"), ("II. Other income", "PL_OI")):
        row(ws, label, items[code].note if code in items else "", g(code, "current"), g(code, "previous"))
    row(ws, "III. Total Income (I + II)", "", t["rev_c"], t["rev_p"], b=True)
    row(ws, "IV. Expenses:", b=True)
    for code in ("PL_MAT", "PL_PUR", "PL_CHG", "PL_EMP", "PL_FIN", "PL_DEP", "PL_OTH"):
        if code in items:
            row(ws, items[code].name, items[code].note, g(code, "current"), g(code, "previous"), indent=1)
    row(ws, "Total expenses", "", t["exp_c"], t["exp_p"], b=True)
    row(ws, "V. Profit before exceptional and extraordinary items and tax (III - IV)", "",
        t["rev_c"] - t["exp_c"], t["rev_p"] - t["exp_p"])
    row(ws, "VI. Exceptional items", items["PL_EXC"].note if "PL_EXC" in items else "", g("PL_EXC", "current"),
        g("PL_EXC", "previous"))
    row(ws, "VII. Profit before tax", "", t["pbt_c"], t["pbt_p"], b=True)
    row(ws, "VIII. Tax expense:", b=True)
    row(ws, "(1) Current tax", items["PL_TAX_CUR"].note if "PL_TAX_CUR" in items else "", g("PL_TAX_CUR", "current"),
        g("PL_TAX_CUR", "previous"), indent=1)
    row(ws, "(2) Deferred tax", items["PL_TAX_DEF"].note if "PL_TAX_DEF" in items else "",
        g("PL_TAX_DEF", "current"), g("PL_TAX_DEF", "previous"), indent=1)
    r = row(ws, "IX. Profit / (Loss) for the period", "", t["pat_c"], t["pat_p"], b=True)
    for col in (3, 4):
        ws.cell(r, col).border = thin

    ws = wb.create_sheet("Notes")
    head(ws, "Notes to accounts")
    for sec_list in (st.bs, st.pl):
        for _sec, its in sec_list:
            for it in its:
                if not it.note:
                    continue
                row(ws, f"Note {it.note}: {it.name}", b=True)
                for n, c, p in it.ledgers:
                    row(ws, n, "", c, p, indent=1)
                row(ws, "Total", "", it.current, it.previous, b=True)
                row(ws, "")
    if st.notes:
        ws = wb.create_sheet("Checks")
        for n in st.notes:
            ws.append([n])
    wb.save(path)
