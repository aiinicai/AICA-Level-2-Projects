"""Profit and loss statement and balance sheet built from the AED trial balance.

Sign conventions in the outputs:
 * P&L rows show the effect on profit: income positive, expenses negative.
 * Balance sheet: assets as debit-positive; liabilities and equity as credit-positive.
No balancing figures are invented. The only derived item is the currency translation difference
(see fx.py), which is labelled as derived and requires user approval.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .fx import TranslationResult
from .mapping import fs_lines
from .models import ZERO_TOL


@dataclass
class StmtRow:
    label: str
    amount: Optional[float] = None
    kind: str = "line"            # header | line | subtotal | total | note
    line_key: str = ""
    accounts: list = field(default_factory=list)      # [(code, name, amount_aed)]
    note: str = ""


@dataclass
class Statements:
    pl_rows: list
    bs_rows: list
    revenue: float
    profit_before_tax: float
    tax_expense: float            # shown negative in the P&L (effect on profit)
    profit_for_year: float
    total_assets: float
    total_liabilities: float
    total_equity: float           # includes profit for the year and any derived translation difference
    bs_difference: float          # assets - (liabilities + equity); should be ~0
    unmapped_net: float
    unmapped_accounts: list
    flags: list = field(default_factory=list)
    line_totals: dict = field(default_factory=dict)   # line key -> amount in statement sign


def _collect(tr: TranslationResult):
    by_line = {}
    for a in tr.accounts:
        by_line.setdefault(a.line, []).append(a)
    return by_line


def build_statements(tr: TranslationResult) -> Statements:
    lines = fs_lines()
    by_line = _collect(tr)
    flags = []

    def pl_amt(key):
        return -sum(a.net_aed for a in by_line.get(key, []))

    def bs_debit(key):
        return sum(a.net_aed for a in by_line.get(key, []))

    def bs_credit(key):
        return -sum(a.net_aed for a in by_line.get(key, []))

    def accts(key, sign):
        return [(a.account.code, a.account.name, sign * a.net_aed) for a in by_line.get(key, [])]

    totals = {}
    # ---------------- P&L ----------------
    pl = []
    rev = pl_amt("P_REV")
    totals["P_REV"] = rev
    pl.append(StmtRow("Revenue", rev, "line", "P_REV", accts("P_REV", -1)))
    cos = pl_amt("P_COS")
    totals["P_COS"] = cos
    pl.append(StmtRow("Cost of sales", cos, "line", "P_COS", accts("P_COS", -1)))
    gross = rev + cos
    pl.append(StmtRow("Gross profit", gross, "subtotal"))

    def block(section, title):
        keys = sorted([k for k, l in lines.items() if l["section"] == section and l["statement"] == "PL"],
                      key=lambda k: lines[k]["order"])
        rows, tot = [], 0.0
        for k in keys:
            if k in by_line:
                amt = pl_amt(k)
                totals[k] = amt
                rows.append(StmtRow(lines[k]["label"], amt, "line", k, accts(k, -1)))
                tot += amt
        if rows:
            if len(rows) > 1 or section in ("OTHER_INCOME", "OPEX"):
                pl.append(StmtRow(title, None, "header"))
            pl.extend(rows)
        return tot

    other_income = block("OTHER_INCOME", "Other income")
    if other_income or any(k in by_line for k in ("P_DIV", "P_INT_INC", "P_GAIN_REAL", "P_FV", "P_OTHER_INC")):
        pl.append(StmtRow("Total other income", other_income, "subtotal"))
    opex = block("OPEX", "Operating expenses")
    if any(lines[k]["section"] == "OPEX" for k in by_line):
        pl.append(StmtRow("Total operating expenses", opex, "subtotal"))
    dep = block("DEPRECIATION", "Depreciation and amortisation")
    fin = block("FINANCE", "Finance costs")
    fxl = block("FX", "Foreign exchange")
    pbt = gross + other_income + opex + dep + fin + fxl
    pl.append(StmtRow("Profit/(loss) before tax", pbt, "total"))
    tax = block("TAX", "Corporate tax")
    pfy = pbt + tax
    pl.append(StmtRow("Profit/(loss) for the year", pfy, "total"))

    # ---------------- Balance sheet ----------------
    bs = []

    def bs_block(section, title, sign):
        keys = sorted([k for k, l in lines.items() if l["section"] == section and l["statement"] == "BS"],
                      key=lambda k: lines[k]["order"])
        rows, tot = [], 0.0
        for k in keys:
            if k in by_line:
                amt = bs_debit(k) if sign == 1 else bs_credit(k)
                totals[k] = amt
                rows.append(StmtRow(lines[k]["label"], amt, "line", k, accts(k, sign if sign == 1 else -1)))
                tot += amt
        return rows, tot

    arows, ta = bs_block("ASSETS", "Assets", 1)
    bs.append(StmtRow("ASSETS", None, "header"))
    bs.extend(arows)
    bs.append(StmtRow("Total assets", ta, "total"))
    lrows, tl = bs_block("LIABILITIES", "Liabilities", -1)
    bs.append(StmtRow("LIABILITIES", None, "header"))
    bs.extend(lrows)
    bs.append(StmtRow("Total liabilities", tl, "total"))
    erows, te = bs_block("EQUITY", "Equity", -1)
    bs.append(StmtRow("EQUITY", None, "header"))
    bs.extend(erows)
    bs.append(StmtRow("Profit/(loss) for the year (from the P&L)", pfy, "line", "PROFIT_YEAR"))
    te += pfy
    if tr.diff_applicable:
        bs.append(StmtRow("Currency translation difference (derived - requires approval)", -tr.translation_diff, "line",
                          "DERIVED_CTR", note="Not a TB figure: arises from translating P&L, balance sheet and equity at different rates."))
        te += -tr.translation_diff
    bs.append(StmtRow("Total equity", te, "total"))
    bs.append(StmtRow("Total liabilities and equity", tl + te, "total"))
    diff = ta - (tl + te)

    unm = by_line.get("UNMAPPED", [])
    unm_net = sum(a.net_aed for a in unm)
    if unm:
        bs.append(StmtRow("Unmapped accounts (excluded from totals - review)", unm_net, "note",
                          "UNMAPPED", [(a.account.code, a.account.name, a.net_aed) for a in unm]))
        flags.append(f"{len(unm)} unmapped account(s) are excluded from the statements.")
    if abs(diff) > 0.5:
        flags.append(f"The balance sheet does not balance: assets less liabilities and equity = AED {diff:,.2f}.")

    return Statements(pl, bs, rev, pbt, tax, pfy, ta, tl, te, diff, unm_net,
                      [(a.account.code, a.account.name, a.net_aed) for a in unm], flags, totals)
