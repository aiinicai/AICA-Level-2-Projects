"""
demo_data.py  -  Realistic sample company data (with deliberate mistakes) so the app
can be demonstrated without Tally - useful for the capstone presentation/viva.
"""

import random
from datetime import date, timedelta

import pandas as pd

GROUPS = [
    ("Current Assets", "Primary"), ("Cash-in-Hand", "Current Assets"), ("Bank Accounts", "Current Assets"),
    ("Sundry Debtors", "Current Assets"), ("Loans & Advances (Asset)", "Current Assets"),
    ("Current Liabilities", "Primary"), ("Sundry Creditors", "Current Liabilities"),
    ("Duties & Taxes", "Current Liabilities"), ("Loans (Liability)", "Primary"),
    ("Unsecured Loans", "Loans (Liability)"), ("Indirect Expenses", "Primary"),
    ("Direct Expenses", "Primary"), ("Purchase Accounts", "Primary"), ("Sales Accounts", "Primary"),
    ("Capital Account", "Primary"), ("Suspense A/c", "Primary"),
]

LEDGERS = [
    ("Cash", "Cash-in-Hand", 25000), ("HDFC Bank", "Bank Accounts", 450000),
    ("Sharma Traders", "Sundry Debtors", 120000), ("Patil Enterprises", "Sundry Debtors", 80000),
    ("Mehta & Co", "Sundry Debtors", 0),
    ("Shree Suppliers", "Sundry Creditors", -90000), ("Gupta Transport", "Sundry Creditors", 0),
    ("Joshi & Associates", "Sundry Creditors", 0), ("Desai Properties", "Sundry Creditors", 0),
    ("Rao Contractors", "Sundry Creditors", 0),
    ("Purchase A/c", "Purchase Accounts", 0), ("Sales A/c", "Sales Accounts", 0),
    ("Freight & Transport Charges", "Direct Expenses", 0), ("Contract Labour Charges", "Direct Expenses", 0),
    ("Professional Fees", "Indirect Expenses", 0), ("Office Rent", "Indirect Expenses", 0),
    ("Staff Welfare", "Indirect Expenses", 0), ("Printing & Stationery", "Indirect Expenses", 0),
    ("Travelling Expenses", "Indirect Expenses", 0), ("Electricity Charges", "Indirect Expenses", 0),
    ("Penalty & Fines", "Indirect Expenses", 0), ("Donation", "Indirect Expenses", 0),
    ("Repairs & Maintenance", "Indirect Expenses", 0),
    ("TDS Payable", "Duties & Taxes", 0), ("Input CGST", "Duties & Taxes", 0), ("Input SGST", "Duties & Taxes", 0),
    ("Loan from Ramesh", "Unsecured Loans", -200000), ("Advance to Staff", "Loans & Advances (Asset)", 0),
    ("Capital - Rahul", "Capital Account", -500000), ("Suspense", "Suspense A/c", 0),
]


def make_demo(seed=7, start=date(2025, 4, 1), end=date(2026, 3, 31)):
    rnd = random.Random(seed)
    groups = pd.DataFrame(GROUPS, columns=["name", "parent"])
    ledgers = pd.DataFrame(LEDGERS, columns=["name", "parent", "opening_balance"])
    rows, n = [], [0]
    counters = {}

    def vch(d, vtype, lines, narr=None, no=None):
        n[0] += 1
        counters[vtype] = counters.get(vtype, 0) + 1
        vid = f"DEMO-{n[0]}"
        for led, amt, side in lines:
            rows.append({"voucher_id": vid, "date": d, "voucher_type": vtype,
                         "voucher_no": str(no or counters[vtype]),
                         "narration": narr if narr is not None else f"Being {vtype.lower()} as per bill",
                         "party": next((l for l, _, _ in lines if l in PARTIES), ""),
                         "ledger": led, "amount": round(amt, 2), "dr_cr": side})

    PARTIES = {"Sharma Traders", "Patil Enterprises", "Mehta & Co", "Shree Suppliers", "Gupta Transport",
               "Joshi & Associates", "Desai Properties", "Rao Contractors", "Loan from Ramesh"}
    days = (end - start).days
    small_exp = ["Staff Welfare", "Printing & Stationery", "Travelling Expenses", "Repairs & Maintenance"]

    for _ in range(900):
        d = start + timedelta(days=rnd.randint(0, days))
        if d.weekday() == 6:
            d -= timedelta(days=1)
        k = rnd.random()
        if k < 0.25:   # sales
            amt = rnd.randint(8000, 180000) + rnd.choice([0.5, 0.0, 0.25])
            p = rnd.choice(["Sharma Traders", "Patil Enterprises", "Mehta & Co"])
            vch(d, "Sales", [(p, amt, "Dr"), ("Sales A/c", amt, "Cr")])
        elif k < 0.45:  # purchase with GST
            base = rnd.randint(5000, 150000) + 0.4
            gst = round(base * 0.09, 2)
            vch(d, "Purchase", [("Purchase A/c", base, "Dr"), ("Input CGST", gst, "Dr"),
                                ("Input SGST", gst, "Dr"), ("Shree Suppliers", base + 2 * gst, "Cr")])
        elif k < 0.60:  # receipts in bank
            p = rnd.choice(["Sharma Traders", "Patil Enterprises", "Mehta & Co"])
            amt = rnd.randint(5000, 150000) + 0.3
            vch(d, "Receipt", [("HDFC Bank", amt, "Dr"), (p, amt, "Cr")])
        elif k < 0.72:  # payment to supplier by bank
            amt = rnd.randint(10000, 160000) + 0.7
            vch(d, "Payment", [("Shree Suppliers", amt, "Dr"), ("HDFC Bank", amt, "Cr")])
        elif k < 0.92:  # small cash expenses
            amt = rnd.randint(150, 6000) + 0.5
            vch(d, "Payment", [(rnd.choice(small_exp), amt, "Dr"), ("Cash", amt, "Cr")],
                narr=rnd.choice(["Tea & snacks for staff", "Courier charges", "Local conveyance", "", "Repairs"]))
        else:           # cash withdrawal
            amt = rnd.choice([20000, 25000, 30000])
            vch(d, "Contra", [("Cash", amt, "Dr"), ("HDFC Bank", amt, "Cr")], narr="Cash withdrawn for office use")

    # electricity monthly, rent monthly WITH TDS (correct), professional WITHOUT TDS (wrong)
    for m in range(12):
        d = date(2025 + (m + 3) // 12, (m + 3) % 12 + 1, 5)
        vch(d, "Payment", [("Electricity Charges", 4200 + 37 * m, "Dr"), ("HDFC Bank", 4200 + 37 * m, "Cr")],
            narr="MSEDCL bill paid")
        vch(d, "Journal", [("Office Rent", 60000, "Dr"), ("TDS Payable", 6000, "Cr"),
                           ("Desai Properties", 54000, "Cr")], narr="Rent for the month, TDS u/s 194I")
        if m % 3 == 0:
            vch(d, "Journal", [("Professional Fees", 35000, "Dr"), ("Joshi & Associates", 35000, "Cr")],
                narr="Quarterly consultancy fees")
    # freight - contractor aggregate > 1 lakh, no TDS
    for m in range(0, 12, 2):
        d = date(2025 + (m + 3) // 12, (m + 3) % 12 + 1, 18)
        vch(d, "Journal", [("Freight & Transport Charges", 24500, "Dr"), ("Gupta Transport", 24500, "Cr")],
            narr="Freight bills for the period")

    # ---------- deliberate audit issues ----------
    vch(date(2025, 6, 14), "Payment", [("Contract Labour Charges", 8000, "Dr"), ("Cash", 8000, "Cr")],
        narr="Labour payment part 1")
    vch(date(2025, 6, 14), "Payment", [("Contract Labour Charges", 7500, "Dr"), ("Cash", 7500, "Cr")],
        narr="Labour payment part 2")                          # 40A(3) split payment
    vch(date(2025, 8, 2), "Payment", [("Repairs & Maintenance", 18000, "Dr"), ("Cash", 18000, "Cr")],
        narr="AC repair")                                      # 40A(3)
    vch(date(2025, 9, 10), "Receipt", [("Cash", 250000, "Dr"), ("Mehta & Co", 250000, "Cr")],
        narr="Cash received against bill")                     # 269ST
    vch(date(2025, 7, 1), "Receipt", [("Cash", 50000, "Dr"), ("Loan from Ramesh", 50000, "Cr")],
        narr="Loan taken")                                     # 269SS
    vch(date(2025, 12, 20), "Payment", [("Loan from Ramesh", 30000, "Dr"), ("Cash", 30000, "Cr")],
        narr="Loan repaid")                                    # 269T
    vch(date(2025, 11, 9), "Payment", [("Staff Welfare", 3200, "Dr"), ("Cash", 3200, "Cr")],
        narr="Diwali sweets")                                  # Sunday
    vch(date(2025, 10, 3), "Payment", [("Penalty & Fines", 5000, "Dr"), ("HDFC Bank", 5000, "Cr")],
        narr="GST late fee and penalty")                       # disallowance
    vch(date(2025, 10, 15), "Payment", [("Donation", 51000, "Dr"), ("HDFC Bank", 51000, "Cr")],
        narr="Donation to temple trust")
    vch(date(2025, 11, 20), "Payment", [("Shree Suppliers", 87345.5, "Dr"), ("HDFC Bank", 87345.5, "Cr")], narr="Payment")
    vch(date(2025, 11, 22), "Payment", [("Shree Suppliers", 87345.5, "Dr"), ("HDFC Bank", 87345.5, "Cr")], narr="Payment")  # duplicate
    vch(date(2026, 1, 12), "Journal", [("Travelling Expenses", 12000, "Dr"), ("Cash", 12000, "Cr")],
        narr="Tour expenses")                                  # cash in journal + 40A(3)
    vch(date(2026, 2, 5), "Journal", [("Suspense", 75000, "Dr"), ("HDFC Bank", 75000, "Cr")],
        narr="Unidentified debit")                             # suspense
    vch(date(2026, 3, 30), "Payment", [("Printing & Stationery", 95000, "Dr"), ("HDFC Bank", 95000, "Cr")],
        narr="Stationery")                                     # outlier + round sum
    vch(date(2026, 3, 31), "Journal", [("Repairs & Maintenance", 700000, "Dr"), ("Rao Contractors", 700000, "Cr")],
        narr="Provision")                                      # material, round, TDS 194C
    vch(date(2025, 5, 3), "Payment", [("Advance to Staff", 25000, "Dr"), ("Cash", 25000, "Cr")],
        narr="Advance given")                                  # loan given in cash
    vch(date(2025, 4, 3), "Payment", [("Shree Suppliers", 300000, "Dr"), ("HDFC Bank", 300000, "Cr")],
        narr="Advance")                                        # creditor may go Dr

    entries = pd.DataFrame(rows)
    return groups, ledgers, entries
