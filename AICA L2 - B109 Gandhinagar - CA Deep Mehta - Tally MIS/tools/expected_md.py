"""Turns sample_tally_data_full/expected_figures.json into the readable EXPECTED_FIGURES.md.

  python tools/expected_md.py sample_tally_data_full
"""
import json
import os
import sys

d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "sample_tally_data_full")
E = json.load(open(os.path.join(d, "expected_figures.json"), encoding="utf-8"))


def inr(paise: float) -> str:
    x = paise / 100
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
    return f"{'-' if neg else ''}₹{tail}"


def lakh(paise: float) -> str:
    return f"₹{paise / 1e7:,.2f} L"


Y = E["years"]
names = {k: (f"FY {k} (Apr–Sep 2025 only)" if k == "2025-26" else f"FY {k}") for k in Y}
rows = [
    ("Sales (gross)", "sales", True), ("Sales returns (credit notes)", "returns", True), ("Net revenue", "netRevenue", True),
    ("Purchases (net of returns)", "purchases", True), ("Direct expenses (freight inward etc.)", "directExpenses", True),
    ("Opening stock", "openingStock", False), ("Closing stock", "closingStock", False), ("Cost of goods sold", "cogs", False),
    ("**Gross profit**", "grossProfit", False), ("Indirect expenses — all", "indirectExpenses", True),
    ("   of which depreciation", "depreciation", True), ("   of which interest + bank charges (finance cost)", None, True),
    ("   of which income tax provision", "incomeTax", True), ("Other income (discount received, FD interest)", "otherIncome", True),
    ("**Net profit**", "netProfit", False),
]
out = [f"# Expected figures for “{E['company']}” ({E['from']} to {E['to']})", "",
       "Worked out directly from the books in these files — not by Tally, and not by Tally MIS — so you can check both.", "",
       "* Figures marked **exact** must match to the rupee in Tally and in Tally MIS.",
       "* Figures marked **≈** depend on stock valuation. Tally values stock with its own costing method (average cost), which can differ by a few "
       "thousand rupees from this sheet (about 0.01% of stock). Treat a small difference there as normal.", ""]
for k, e in Y.items():
    out += [f"## {names[k]}", "", "| Figure | Amount | |", "|---|---|---|"]
    for label, key, exact in rows:
        v = e["interest"] + e["bankCharges"] if key is None else e[key]
        out.append(f"| {label} | {inr(v)} | {'exact' if exact else '≈'} |")
    out.append(f"| Gross margin | {100 * e['grossProfit'] / e['netRevenue']:.1f}% | ≈ |")
    out.append(f"| Net margin | {100 * e['netProfit'] / e['netRevenue']:.1f}% | ≈ |")
    out.append("")
b = E["balances"]
out += ["## Balances at 30-Sep-2025", "", "| Figure | Amount | |", "|---|---|---|",
        f"| Bank (HDFC Bank Current A/c) | {inr(b['bank'])} | exact |", f"| Cash | {inr(b['cash'])} | exact |",
        f"| Sundry debtors (receivables) | {inr(b['receivables'])} | exact |", f"| Sundry creditors (payables) | {inr(b['payables'])} | exact |",
        f"| Fixed assets (after depreciation) | {inr(b['fixedAssets'])} | exact |", f"| Cash credit (SBI) — short-term borrowing | {inr(b['cashCredit'])} | exact |",
        f"| Term loan outstanding | {inr(b['termLoan'])} (fully repaid) | exact |", f"| Closing stock | {inr(b['stock'])} | ≈ |", ""]
v = E["vouchers"]
out += ["## What is in the data", "", f"* **{v['total']:,} vouchers**: " + ", ".join(f"{t} {n:,}" for t, n in sorted(v["byType"].items(), key=lambda x: -x[1])) + ".",
        "* **30 stock items** in 6 groups (Lighting, Fans, Wires & Cables, Switchgear, Accessories, Power Backup) with opening stock, purchases, sales,",
        "  sales returns (credit notes) and purchase returns (debit notes), in two godowns (Main Location, Warehouse 2).",
        "* **25 customers and 12 suppliers**, bill-wise: credit periods of 30–60 days, some customers who pay late, one very slow payer, part payments,",
        "  an advance and an on-account receipt, supplier discounts, opening bills.",
        "* **GST** (CGST, SGST, IGST) on sales and purchases, with a monthly set-off and payment.",
        "* **Two cost centres** (Mumbai Branch, Pune Branch) on sales, rent and commission.",
        "* **Loans:** SBI term loan (repaid in full during the period), SBI cash credit that is drawn and repaid, interest on both.",
        "* **Fixed assets** (machinery, furniture, computers) with depreciation on written-down value; new computers (Apr 2023) and a new machine (Apr 2024).",
        "* **Income-tax provision** every March, paid the next year; an audit-fee provision; fixed-deposit interest; an item parked in suspense.",
        "* Only the **1st, 2nd and 31st** of a month are used as voucher dates, so it imports in TallyPrime Educational mode too.", ""]
open(os.path.join(d, "EXPECTED_FIGURES.md"), "w", encoding="utf-8").write("\n".join(out))
print("wrote EXPECTED_FIGURES.md")
