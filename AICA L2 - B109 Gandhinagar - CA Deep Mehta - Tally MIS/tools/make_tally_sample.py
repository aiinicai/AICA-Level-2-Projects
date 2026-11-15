"""Makes a small, fictional sample company that you can import into TallyPrime (and so test Tally MIS against real Tally).

  python tools/make_tally_sample.py            # writes sample_tally_data/

Design choices (so it imports cleanly, even in TallyPrime Educational mode):
* Every voucher is dated the 1st, 2nd or 31st of a month (Educational mode only accepts those dates).
* Accounts only: no stock items, no GST. Sales and purchases are bill-wise; receipts and payments settle those bills.
* The expected totals are worked out here, independently of Tally MIS, and written to EXPECTED_FIGURES.md so you can compare.
"""
from __future__ import annotations

import calendar
import os
import random
import sys
from datetime import date
from xml.sax.saxutils import escape

COMPANY = "Sample Trading Co"
FIRST_MONTH, LAST_MONTH = (2024, 4), (2025, 9)  # Apr 2024 .. Sep 2025 (18 months, two financial years)

DEBTORS = ["Aarav Enterprises", "Bhavna Traders", "Chauhan Stores", "Deshmukh & Sons", "Eastern Retail", "Fortune Distributors"]
CREDITORS = ["Apex Components", "Bharat Supplies", "Crown Packaging", "Delta Wholesale"]
EXPENSES = [  # name, group
    ("Salaries", "Indirect Expenses"), ("Office Rent", "Indirect Expenses"), ("Electricity Charges", "Indirect Expenses"),
    ("Telephone & Internet", "Indirect Expenses"), ("Advertisement", "Indirect Expenses"), ("Bank Charges", "Indirect Expenses"),
    ("Interest on Loan", "Indirect Expenses"), ("Depreciation", "Indirect Expenses"),
]
OPENING = {"HDFC Bank": -600000, "Furniture & Fixtures": -300000, "Owner's Capital": 700000, "Secured Loan - Bank": 200000}  # Tally sign: Dr negative


def amt(x: float) -> str:
    return f"{x:.2f}"


def months():
    y, m = FIRST_MONTH
    while (y, m) <= LAST_MONTH:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fy_label(d: date) -> str:
    s = d.year if d.month >= 4 else d.year - 1
    return f"{s % 100:02d}-{(s + 1) % 100:02d}"


# ------------------------------------------------------------------------------------------------ ledgers
def ledger_xml(name, parent, opening=None, billwise=False):
    extra = ""
    if opening is not None:
        extra += f"<OPENINGBALANCE>{amt(opening)}</OPENINGBALANCE>"
    if billwise:
        extra += "<ISBILLWISEON>Yes</ISBILLWISEON><BILLCREDITPERIOD>30 Days</BILLCREDITPERIOD>"
    n = escape(name)
    return f'<TALLYMESSAGE xmlns:UDF="TallyUDF"><LEDGER NAME="{n}" ACTION="Create"><NAME.LIST><NAME>{n}</NAME></NAME.LIST><PARENT>{escape(parent)}</PARENT>{extra}</LEDGER></TALLYMESSAGE>'


def masters_xml() -> str:
    rows = [
        ledger_xml("HDFC Bank", "Bank Accounts", OPENING["HDFC Bank"]),
        ledger_xml("Furniture & Fixtures", "Fixed Assets", OPENING["Furniture & Fixtures"]),
        ledger_xml("Owner's Capital", "Capital Account", OPENING["Owner's Capital"]),
        ledger_xml("Secured Loan - Bank", "Secured Loans", OPENING["Secured Loan - Bank"]),
        ledger_xml("Sales - Domestic", "Sales Accounts"),
        ledger_xml("Purchases", "Purchase Accounts"),
        ledger_xml("Freight Inward", "Direct Expenses"),
        ledger_xml("Interest Received", "Indirect Incomes"),
    ]
    rows += [ledger_xml(n, g) for n, g in EXPENSES]
    rows += [ledger_xml(n, "Sundry Debtors", 0, True) for n in DEBTORS]
    rows += [ledger_xml(n, "Sundry Creditors", 0, True) for n in CREDITORS]
    return wrap("All Masters", "\n".join(rows))


def wrap(report: str, body: str) -> str:
    # No SVCURRENTCOMPANY: the data goes into whichever company is open in Tally.
    return ('<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC>'
            f'<REPORTNAME>{report}</REPORTNAME></REQUESTDESC><REQUESTDATA>\n{body}\n</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>\n')


# ------------------------------------------------------------------------------------------------ vouchers
class Books:
    def __init__(self):
        self.vouchers: list[str] = []
        self.n = {"Sales": 0, "Purchase": 0, "Receipt": 0, "Payment": 0, "Journal": 0, "Contra": 0}
        self.bal = {k: 0 for k in [*OPENING, "Cash", "Sales - Domestic", "Purchases", "Freight Inward", "Interest Received",
                                    *[e for e, _ in EXPENSES], *DEBTORS, *CREDITORS]}   # Dr positive here
        for k, v in OPENING.items():
            self.bal[k] = -v
        self.open_sales: list[dict] = []      # unpaid invoices
        self.open_purch: list[dict] = []
        self.totals = {"sales": 0.0, "purchases": 0.0}
        self.min_bank = (1e18, None)
        self.by_fy: dict[str, dict] = {}

    def fy(self, d: date) -> dict:
        return self.by_fy.setdefault(fy_label(d), {"sales": 0.0, "purchases": 0.0, "freight": 0.0, "expenses": {}, "interest_received": 0.0})

    def add(self, vtype: str, d: date, party: str | None, entries: list[tuple], narration: str):
        """entries: (ledger, 'Dr'|'Cr', amount, bill_or_None) ; bill = (name, 'New Ref'|'Agst Ref')"""
        assert abs(sum(a if s == "Dr" else -a for _, s, a, _ in entries)) < 0.005, (vtype, d, entries)
        self.n[vtype] += 1
        parts = []
        for led, side, a, bill in entries:
            dr = side == "Dr"
            sign = -a if dr else a  # Tally XML: debit negative
            self.bal[led] += a if dr else -a
            if led == "HDFC Bank" and self.bal[led] < self.min_bank[0]:
                self.min_bank = (self.bal[led], d)
            b = ""
            if bill:
                b = (f"<BILLALLOCATIONS.LIST><NAME>{escape(bill[0])}</NAME><BILLTYPE>{bill[1]}</BILLTYPE>"
                     + ("<BILLCREDITPERIOD>30 Days</BILLCREDITPERIOD>" if bill[1] == "New Ref" else "")
                     + f"<AMOUNT>{amt(sign)}</AMOUNT></BILLALLOCATIONS.LIST>")
            is_party = "<ISPARTYLEDGER>Yes</ISPARTYLEDGER>" if led == party else ""
            parts.append(f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{escape(led)}</LEDGERNAME><ISDEEMEDPOSITIVE>{'Yes' if dr else 'No'}</ISDEEMEDPOSITIVE>"
                         f"{is_party}<AMOUNT>{amt(sign)}</AMOUNT>{b}</ALLLEDGERENTRIES.LIST>")
        pl = f"<PARTYLEDGERNAME>{escape(party)}</PARTYLEDGERNAME>" if party else ""
        self.vouchers.append(
            f'<TALLYMESSAGE xmlns:UDF="TallyUDF"><VOUCHER VCHTYPE="{vtype}" ACTION="Create" OBJVIEW="Accounting Voucher View">'
            f"<DATE>{d:%Y%m%d}</DATE><VOUCHERTYPENAME>{vtype}</VOUCHERTYPENAME><VOUCHERNUMBER>{self.n[vtype]}</VOUCHERNUMBER>{pl}"
            f"<NARRATION>{escape(narration)}</NARRATION><PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>{''.join(parts)}</VOUCHER></TALLYMESSAGE>")


def build() -> Books:
    rnd = random.Random(20251114)
    b = Books()
    for y, m in months():
        last = calendar.monthrange(y, m)[1]
        d1, d2 = date(y, m, 1), date(y, m, 2)
        d31 = date(y, m, 31) if last == 31 else None
        idx = (y - FIRST_MONTH[0]) * 12 + m - FIRST_MONTH[1]
        growth = 1 + 0.015 * idx

        def sale(d, cust):
            a = round(rnd.randrange(20000, 120000, 500) * growth, -1)
            inv = f"SI/{fy_label(d)}/{b.n['Sales'] + 1}"
            b.add("Sales", d, cust, [(cust, "Dr", a, (inv, "New Ref")), ("Sales - Domestic", "Cr", a, None)], f"Sale {inv}")
            b.open_sales.append({"name": inv, "party": cust, "amt": a, "date": d})
            b.fy(d)["sales"] += a
            b.totals["sales"] += a

        for _ in range(rnd.randint(3, 5)):
            sale(d1, rnd.choice(DEBTORS))
        if d31:
            for _ in range(2):
                sale(d31, rnd.choice(DEBTORS))
        for _ in range(2):
            sup = rnd.choice(CREDITORS)
            a = round(rnd.randrange(30000, 90000, 500) * growth, -1)
            bill = f"{sup.split()[0].upper()}/{y}/{b.n['Purchase'] + 1}"
            b.add("Purchase", d1, sup, [("Purchases", "Dr", a, None), (sup, "Cr", a, (bill, "New Ref"))], f"Purchase {bill}")
            b.open_purch.append({"name": bill, "party": sup, "amt": a, "date": d1})
            b.fy(d1)["purchases"] += a
            b.totals["purchases"] += a
        # a small cash sale and a cash deposit
        a = rnd.randrange(5000, 15000, 100)
        b.add("Sales", d2, "Cash", [("Cash", "Dr", a, None), ("Sales - Domestic", "Cr", a, None)], "Cash sale")
        b.fy(d2)["sales"] += a
        b.totals["sales"] += a
        b.add("Contra", d2, None, [("HDFC Bank", "Dr", a, None), ("Cash", "Cr", a, None)], "Cash deposited in bank")

        # receipts: most invoices that are at least a month old are paid
        old = [s for s in b.open_sales if (d2 - s["date"]).days >= 30]
        for s in old:
            if rnd.random() > 0.85:
                continue  # a few customers pay late, so there is something overdue to see
            b.add("Receipt", d2, s["party"], [("HDFC Bank", "Dr", s["amt"], None), (s["party"], "Cr", s["amt"], (s["name"], "Agst Ref"))], f"Receipt against {s['name']}")
            b.open_sales.remove(s)
        # payments to suppliers: bills at least a month old are paid
        oldp = [p for p in b.open_purch if (d2 - p["date"]).days >= 30]
        for p in oldp:
            b.add("Payment", d2, p["party"], [(p["party"], "Dr", p["amt"], (p["name"], "Agst Ref")), ("HDFC Bank", "Cr", p["amt"], None)], f"Payment against {p['name']}")
            b.open_purch.remove(p)
        # running costs, paid from the bank on the 2nd
        costs = [("Salaries", round(85000 * growth, -2)), ("Office Rent", 40000), ("Electricity Charges", rnd.randrange(8000, 12500, 50)),
                 ("Telephone & Internet", 3500), ("Bank Charges", rnd.randrange(400, 900, 10)), ("Interest on Loan", 1500)]
        if idx % 2 == 0:
            costs.append(("Advertisement", rnd.randrange(5000, 15000, 100)))
        if idx % 3 == 1:
            costs.append(("Freight Inward", rnd.randrange(2000, 6000, 100)))
        for name, a in costs:
            b.add("Payment", d2, None, [(name, "Dr", a, None), ("HDFC Bank", "Cr", a, None)], f"{name} for {d2:%b %Y}")
            f = b.fy(d2)
            if name == "Freight Inward":
                f["freight"] += a
            else:
                f["expenses"][name] = f["expenses"].get(name, 0) + a
        dep = 2500
        b.add("Journal", d2, None, [("Depreciation", "Dr", dep, None), ("Furniture & Fixtures", "Cr", dep, None)], "Monthly depreciation")
        b.fy(d2)["expenses"]["Depreciation"] = b.fy(d2)["expenses"].get("Depreciation", 0) + dep
    return b


def report(b: Books) -> str:
    inr = lambda x: f"₹{x:,.2f}"
    out = [f"# Expected figures for the sample company “{COMPANY}”",
           "",
           "These were worked out directly from the sample vouchers (not by Tally MIS and not by Tally), so you can use them to",
           "check both TallyPrime and Tally MIS. There is no stock and no GST, so purchases are fully expensed (closing stock is nil).",
           ""]
    for fy, f in sorted(b.by_fy.items()):
        exp = sum(f["expenses"].values())
        np_ = f["sales"] - f["purchases"] - f["freight"] - exp
        label = f"FY 20{fy[:2]}-{fy[3:]}" + (" (Apr–Sep 2025 only)" if fy == "25-26" else "")
        out += [f"## {label}", "", "| Figure | Amount |", "|---|---|",
                f"| Sales (revenue) | {inr(f['sales'])} |", f"| Purchases | {inr(f['purchases'])} |", f"| Freight inward (direct expense) | {inr(f['freight'])} |",
                f"| Gross profit | {inr(f['sales'] - f['purchases'] - f['freight'])} |", f"| Indirect expenses (salaries, rent, depreciation …) | {inr(exp)} |",
                f"| **Net profit** | **{inr(np_)}** |", ""]
    rec = sum(s["amt"] for s in b.open_sales)
    pay = sum(p["amt"] for p in b.open_purch)
    bank = b.bal["HDFC Bank"]
    cash = b.bal["Cash"]
    out += ["## Balances at 30-Sep-2025", "", "| Figure | Amount |", "|---|---|",
            f"| Bank (HDFC Bank) | {inr(bank)} |", f"| Cash | {inr(cash)} |", f"| Receivables (sundry debtors) | {inr(rec)} |",
            f"| Payables (sundry creditors) | {inr(pay)} |", f"| Furniture & Fixtures (after depreciation) | {inr(b.bal['Furniture & Fixtures'])} |", "",
            f"Vouchers: {sum(b.n.values())} in total — " + ", ".join(f"{k} {v}" for k, v in b.n.items()) + ".", "",
            "Open (unpaid) sales invoices at 30-Sep-2025 — receivables by customer:", "", "| Customer | Outstanding |", "|---|---|"]
    by: dict[str, float] = {}
    for s in b.open_sales:
        by[s["party"]] = by.get(s["party"], 0) + s["amt"]
    out += [f"| {k} | {inr(v)} |" for k, v in sorted(by.items(), key=lambda kv: -kv[1])]
    return "\n".join(out) + "\n"


def main() -> None:
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "sample_tally_data")
    os.makedirs(out_dir, exist_ok=True)
    b = build()
    # the trial balance must balance (Dr = Cr) before any file is written
    assert abs(sum(b.bal.values())) < 0.01, sum(b.bal.values())
    assert b.min_bank[0] > 0, f"bank would go overdrawn on {b.min_bank[1]}"
    open(os.path.join(out_dir, "1_Masters_Ledgers.xml"), "w", encoding="utf-8").write(masters_xml())
    open(os.path.join(out_dir, "2_Vouchers.xml"), "w", encoding="utf-8").write(wrap("Vouchers", "\n".join(b.vouchers)))
    open(os.path.join(out_dir, "EXPECTED_FIGURES.md"), "w", encoding="utf-8").write(report(b))
    print(f"Wrote {len(b.vouchers)} vouchers to {os.path.abspath(out_dir)}")


if __name__ == "__main__":
    main()
