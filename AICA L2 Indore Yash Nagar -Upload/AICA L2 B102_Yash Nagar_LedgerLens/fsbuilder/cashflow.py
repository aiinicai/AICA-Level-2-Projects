"""AS 3 cash flow statement, indirect method, from rounded balance sheet and P&L figures.

Every balance sheet movement is classified once (operating, investing, financing, or cash itself), so
the statement ties by construction: opening cash + net movement must equal closing cash, and the
caller is told if it does not.

Cash and cash equivalents = cash on hand + balances in current accounts. Bank deposits are shown in
investing activities until their maturity is confirmed (they are not necessarily cash equivalents).
"""
from __future__ import annotations

import re

NOTES = [
    "Cash and cash equivalents are cash on hand and balances with banks in current accounts. Bank deposits "
    "are shown under investing activities until their maturity is confirmed.",
    "Interest paid and received are taken as equal to the amounts in the statement of profit and loss, because "
    "Tally holds no accrued-interest ledgers.",
    "Purchase of property, plant and equipment is derived from the change in net book value plus depreciation, "
    "because gross block is not available in Tally.",
    "Previous-year cash flows need the balance sheet at the start of the previous year and its statement of "
    "profit and loss; only the current year was loaded.",
]


def _cls(line: str, sub: str) -> str:
    """Bucket for the cash effect of a balance sheet movement."""
    s = sub.lower()
    if line == "CA.CBB":
        return "deposits" if s.startswith("other bank balances") else "cash"
    if line in ("NCA.PPE", "NCA.INTG", "NCA.CWIP"):
        return "ppe"
    if line in ("NCA.NCI", "CA.CI"):
        return "invest"
    if line in ("NCA.DTA", "NCL.DTL") or (line == "CL.STP" and "provision for tax" in s):
        return "tax"
    if line in ("NCA.LTLA", "NCA.ONCA", "CA.STLA", "CA.OCA"):
        return "loans_rel" if re.search(r"related part|employee", s) else "oth_assets"
    if line == "CA.INV":
        return "inv"
    if line == "CA.TR":
        return "tr"
    if line == "CL.TP":
        return "tp"
    if line in ("CL.OCL", "CL.STP", "NCL.LTP", "NCL.OLL"):
        return "lt_debt" if "current maturities" in s else "oth_liab"
    if line == "EQ.SC":
        return "share"
    if line == "EQ.RS":
        return "reserves"
    if line == "NCL.LTB":
        return "lt_debt"
    if line == "CL.STB":
        return "st_debt"
    raise ValueError(f"No cash flow treatment for line {line}")


def build_cash_flow(subs: dict, lines: dict, pl: dict, deposit_flags=()) -> dict:
    """subs: {line: [[sub, cur, prev], ...]} (rounded; presentation sign: assets Dr+, liabilities Cr+).
    pl: pbt, profit, tax_expense, dep, fin, interest, dividend, gain (all current-year, whole rupees).
    Returns rows as (label, cur, kind, flags), plus cash figures and the proof difference."""
    b = {k: 0 for k in ("inv", "tr", "oth_assets", "tp", "oth_liab", "ppe", "invest", "deposits", "loans_rel",
                        "share", "lt_debt", "st_debt", "reserves", "tax")}
    cce_cur = cce_prev = 0
    for line, items in subs.items():
        if lines[line]["statement"] != "BS":
            continue
        for sub, cur, prev in items:
            bucket = _cls(line, sub)
            if bucket == "cash":
                cce_cur += cur
                cce_prev += prev
                continue
            d = cur - prev
            b[bucket] += -d if lines[line]["side"] == "A" else d

    dep, fin, intr, div, gain = pl["dep"], pl["fin"], pl["interest"], pl["dividend"], pl["gain"]
    equity_other = b["reserves"] - pl["profit"]          # reserve movement other than the year's profit
    tax_paid = -pl["tax_expense"] + b["tax"]
    ppe_inv = b["ppe"] - dep + gain                      # additions net of disposals, incl. sale proceeds

    rows: list[tuple] = []

    def add(label, val, kind="item", flags=(), always=False):
        if val or always:
            rows.append((label, val, kind, list(flags)))

    op_before_wc = pl["pbt"] + dep + fin - intr - div - gain
    wc = b["inv"] + b["tr"] + b["oth_assets"] + b["tp"] + b["oth_liab"]
    cash_ops = op_before_wc + wc
    net_a = cash_ops + tax_paid
    net_b = ppe_inv + b["invest"] + b["deposits"] + b["loans_rel"] + intr + div
    net_c = b["share"] + b["lt_debt"] + b["st_debt"] - fin + equity_other
    net = net_a + net_b + net_c

    rows.append(("A. CASH FLOW FROM OPERATING ACTIVITIES", None, "head", []))
    add("Net profit / (loss) before tax", pl["pbt"], always=True)
    rows.append(("Adjustments for:", None, "sub", []))
    add("Depreciation and amortisation expense", dep, "subitem")
    add("Finance costs", fin, "subitem")
    add("Interest income", -intr, "subitem")
    add("Dividend income", -div, "subitem")
    add("Net (gain) / loss on sale of assets", -gain, "subitem")
    add("Operating profit before working capital changes", op_before_wc, "total", always=True)
    rows.append(("Adjustments for changes in working capital:", None, "sub", []))
    add("(Increase) / decrease in inventories", b["inv"], "subitem")
    add("(Increase) / decrease in trade receivables", b["tr"], "subitem")
    add("(Increase) / decrease in loans, advances and other assets", b["oth_assets"], "subitem")
    add("Increase / (decrease) in trade payables", b["tp"], "subitem")
    add("Increase / (decrease) in other liabilities and provisions", b["oth_liab"], "subitem")
    add("Cash generated from operations", cash_ops, "total", always=True)
    add("Direct taxes paid (net of refunds)", tax_paid, "subitem", always=True)
    add("Net cash from / (used in) operating activities (A)", net_a, "total", always=True)

    rows.append(("B. CASH FLOW FROM INVESTING ACTIVITIES", None, "head", []))
    add("Purchase of property, plant and equipment (net of sales)", ppe_inv, "subitem")
    add("Purchase of investments (net of sales)", b["invest"], "subitem")
    add("Bank deposits placed (net of maturities)", b["deposits"], "subitem", deposit_flags)
    add("Loans and advances to related parties / employees (net)", b["loans_rel"], "subitem")
    add("Interest received", intr, "subitem")
    add("Dividend received", div, "subitem")
    add("Net cash from / (used in) investing activities (B)", net_b, "total", always=True)

    rows.append(("C. CASH FLOW FROM FINANCING ACTIVITIES", None, "head", []))
    add("Proceeds from issue of share capital", b["share"], "subitem")
    add("Proceeds from / (repayment of) long-term borrowings", b["lt_debt"], "subitem")
    add("Proceeds from / (repayment of) short-term borrowings", b["st_debt"], "subitem")
    add("Finance costs paid", -fin, "subitem")
    add("Dividends and other movement in reserves", equity_other, "subitem")
    add("Net cash from / (used in) financing activities (C)", net_c, "total", always=True)

    add("D. NET INCREASE / (DECREASE) IN CASH AND CASH EQUIVALENTS (A + B + C)", net, "total", always=True)
    add("Cash and cash equivalents at the beginning of the year", cce_prev, "item", always=True)
    add("Cash and cash equivalents at the end of the year", cce_prev + net, "total", always=True)
    return {"rows": rows, "net": net, "open": cce_prev, "close": cce_cur, "diff": cce_prev + net - cce_cur,
            "notes": list(NOTES), "buckets": dict(b), "cfo": net_a, "cfi": net_b, "cff": net_c}
