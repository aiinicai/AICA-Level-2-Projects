# -*- coding: utf-8 -*-
"""
make_sample_tally_company.py
Creates import files for a SAMPLE Tally Prime company (all names and amounts are invented).

Output (in the folder named below, default: Sample_Tally_Company):
    1_Masters.xml                 ledgers with opening balances at 1-Apr-2024
    2_Vouchers_FY2024-25.xml      vouchers for 1-Apr-2024 to 31-Mar-2025   (previous year)
    3_Vouchers_FY2025-26.xml      vouchers for 1-Apr-2025 to 31-Mar-2026   (current year)
    Expected_Trial_Balance.csv    what the Trial Balance should show after import, for both years
    HOW_TO_IMPORT.txt             step-by-step instructions

Run:  python make_sample_tally_company.py [output_folder]
"""
import csv
import os
import sys
from datetime import date
from xml.sax.saxutils import escape

COMPANY = "Sample Engineering Private Limited"
OPEN_RES_PY = 1850000.0          # reserves (Profit & Loss A/c, credit) at 1-Apr-2024
GROUPS = {"Capital Account", "Secured Loans", "Unsecured Loans", "Bank OD A/c", "Fixed Assets", "Sundry Creditors", "Duties & Taxes",
          "Provisions", "Current Liabilities", "Sundry Debtors", "Cash-in-Hand", "Deposits (Asset)", "Loans & Advances (Asset)",
          "Current Assets", "Sales Accounts", "Indirect Incomes", "Purchase Accounts", "Direct Expenses",
          "Indirect Expenses", "Bank Accounts"}
NOMINAL = {"Sales Accounts", "Indirect Incomes", "Purchase Accounts", "Direct Expenses", "Indirect Expenses"}
# ledger, Tally group, closing balance at 31-Mar-2026 (debit +, credit -), closing balance at 31-Mar-2025
LEDGERS = [
    ("Equity Share Capital", "Capital Account", -2500000, -2500000),
    ("Term Loan - Sample Bank", "Secured Loans", -3200000, -3900000),
    ("Loan from Director", "Unsecured Loans", -600000, -450000),
    ("Cash Credit - Sample Bank", "Bank OD A/c", -1450000, -1100000),
    ("Plant and Machinery", "Fixed Assets", 5625000, 5300000),
    ("Furniture and Fixtures", "Fixed Assets", 338000, 365000),
    ("Computers and Printers", "Fixed Assets", 215000, 148000),
    ("Vehicles", "Fixed Assets", 790000, 900000),
    ("Alpha Components Pvt Ltd", "Sundry Creditors", -1380000, -1190000),
    ("Beta Metals Traders", "Sundry Creditors", -920000, -760000),
    ("Gamma Logistics", "Sundry Creditors", -340000, -280000),
    ("GST Output Payable", "Duties & Taxes", -410000, -350000),
    ("TDS Payable", "Duties & Taxes", -86000, -71000),
    ("PF Payable", "Duties & Taxes", -54000, -47000),
    ("Provision for Gratuity", "Provisions", -180000, -140000),
    ("Audit Fee Payable", "Current Liabilities", -60000, -50000),
    ("Salary Payable", "Current Liabilities", -230000, -205000),
    ("Advance from Customers", "Current Liabilities", -275000, -120000),
    ("Delta Industries Ltd", "Sundry Debtors", 2150000, 1820000),
    ("Epsilon Engineering", "Sundry Debtors", 1640000, 1330000),
    ("Zeta Retail Co", "Sundry Debtors", 880000, 740000),
    ("Eta Customer (advance received)", "Sundry Debtors", -90000, 0),
    ("Cash in Hand", "Cash-in-Hand", 45000, 38000),
    ("Rent Deposit", "Deposits (Asset)", 300000, 300000),
    ("Advance to Suppliers", "Loans & Advances (Asset)", 260000, 190000),
    ("Staff Advances", "Loans & Advances (Asset)", 75000, 60000),
    ("GST Input Credit", "Current Assets", 390000, 310000),
    ("Prepaid Insurance", "Current Assets", 48000, 41000),
    ("Closing Stock", "Current Assets", 2250000, 1900000),
    ("Changes in Inventories", "Indirect Expenses", -350000, -400000),
    ("Sales - Products", "Sales Accounts", -17800000, -15200000),
    ("Sales - Services", "Sales Accounts", -2600000, -2100000),
    ("Interest Received", "Indirect Incomes", -64000, -52000),
    ("Discount Received", "Indirect Incomes", -22000, -18000),
    ("Purchase of Raw Materials", "Purchase Accounts", 9600000, 8300000),
    ("Freight Inward", "Direct Expenses", 420000, 370000),
    ("Salaries and Wages", "Indirect Expenses", 3250000, 2800000),
    ("PF Employer Contribution", "Indirect Expenses", 310000, 270000),
    ("Staff Welfare", "Indirect Expenses", 120000, 98000),
    ("Interest on Term Loan", "Indirect Expenses", 380000, 450000),
    ("Interest on Cash Credit", "Indirect Expenses", 165000, 130000),
    ("Bank Charges", "Indirect Expenses", 38000, 31000),
    ("Rent", "Indirect Expenses", 720000, 660000),
    ("Electricity", "Indirect Expenses", 410000, 370000),
    ("Repairs and Maintenance", "Indirect Expenses", 265000, 215000),
    ("Insurance", "Indirect Expenses", 96000, 88000),
    ("Professional Fees", "Indirect Expenses", 185000, 160000),
    ("Audit Fees", "Indirect Expenses", 60000, 50000),
    ("Telephone and Internet", "Indirect Expenses", 72000, 66000),
    ("Travelling Expenses", "Indirect Expenses", 238000, 196000),
    ("Office Expenses", "Indirect Expenses", 134000, 119000),
    ("Advertisement", "Indirect Expenses", 150000, 110000),
    ("Depreciation", "Indirect Expenses", 700000, 820000),
]
ADDITIONS = {"Plant and Machinery": [(700000, date(2025, 6, 15), "Purchase of CNC machine")],
             "Computers and Printers": [(120000, date(2025, 10, 1), "Purchase of laptops and printer")],
             "Vehicles": [(135000, date(2026, 1, 20), "Purchase of delivery van")]}
ACCRUE = {"Provision for Gratuity": "Salaries and Wages", "Salary Payable": "Salaries and Wages",
          "Audit Fee Payable": "Audit Fees", "PF Payable": "PF Employer Contribution"}
STOCK_OPEN = 1500000.0
DEP_PY = 820000.0
QEND = [(6, 30), (9, 30), (12, 31), (3, 31)]


def rnd(x):
    return round(float(x), 2)


def split4(x):
    """Split an amount into four whole-rupee parts that add back to the total."""
    q = int(round(x / 4.0))
    return [q, q, q, rnd(x - 3 * q)]


def build():
    names = [l[0] for l in LEDGERS]
    grp = {l[0]: l[1] for l in LEDGERS}
    C = {2025: {l[0]: float(l[3]) for l in LEDGERS}, 2026: {l[0]: float(l[2]) for l in LEDGERS}}
    # balancing bank ledger so the books agree
    bank = "Sample Bank Current Account"
    grp[bank] = "Bank Accounts"
    names.append(bank)
    open_res = {2025: OPEN_RES_PY}
    for y in (2025, 2026):
        nom = sum(v for n, v in C[y].items() if grp[n] in NOMINAL)
        if y == 2025:
            open_res[2026] = OPEN_RES_PY - nom           # reserves at 1-Apr-2025 = opening + profit of the previous year
        C[y][bank] = 0.0
        C[y][bank] = open_res[y] - sum(C[y].values())
    # opening balances at 1-Apr-2024
    fa = [n for n in names if grp[n] == "Fixed Assets"]
    tfa = sum(C[2025][n] for n in fa)
    dep_py = {n: rnd(DEP_PY * C[2025][n] / tfa) for n in fa}
    dep_py[fa[-1]] = rnd(DEP_PY - sum(dep_py[n] for n in fa[:-1]))
    O = {2025: {}, 2026: dict(C[2025])}
    for n in names:
        O[2025][n] = 0.0 if grp[n] in NOMINAL else C[2025][n]
    for n in fa:
        O[2025][n] = C[2025][n] + dep_py[n]
    O[2025]["Closing Stock"] = STOCK_OPEN
    O[2025][bank] = OPEN_RES_PY - sum(v for n, v in O[2025].items() if n != bank)
    # the previous year's profit lifts the bank balance; assume part of it repaid the term loan, so the opening bank balance is a sensible 6,00,000
    shortfall = 600000.0 - O[2025][bank]
    if shortfall > 0:
        O[2025]["Term Loan - Sample Bank"] -= shortfall
        O[2025][bank] += shortfall
    for y in (2026,):
        for n in names:
            if grp[n] in NOMINAL:
                O[y][n] = 0.0
    vouchers = {2025: [], 2026: []}
    cnt = {}

    def add(y, d, vtype, lines, narr, party=None):
        cnt[(y, vtype)] = cnt.get((y, vtype), 0) + 1
        vouchers[y].append({"date": d, "type": vtype, "no": cnt[(y, vtype)], "lines": lines, "narr": narr, "party": party})

    for y in (2025, 2026):
        yr = y - 1                      # calendar year in which the Tally year starts (2024 or 2025)
        qd = [date(yr, 6, 30), date(yr, 9, 30), date(yr, 12, 31), date(yr + 1, 3, 31)]
        m = {n: C[y][n] - O[y][n] for n in names}
        bankpart = {n: 0.0 for n in names if n != bank}
        done = set()
        # --- sales (customers) and purchases (suppliers)
        sales_led = [n for n in names if grp[n] == "Sales Accounts"]
        total_sales = -sum(C[y][n] for n in sales_led)
        deb = [n for n in names if grp[n] == "Sundry Debtors"]
        wd = {n: max(C[y][n], 0.0) for n in deb}
        sw = sum(wd.values())
        bill_d = {n: rnd(total_sales * wd[n] / sw) for n in deb}
        big = max(deb, key=lambda n: wd[n])
        bill_d[big] = rnd(bill_d[big] + total_sales - sum(bill_d.values()))
        sales_part = {n: C[y][n] for n in sales_led}
        for q in range(4):
            lines, tot = [], 0.0
            for n in deb:
                a = split4(bill_d[n])[q]
                if a:
                    lines.append((n, a))
                    tot += a
            if not lines:
                continue
            # split the credit between sales ledgers in the year's proportion
            cr = []
            rem = tot
            for k, s in enumerate(sales_led):
                share = rnd(tot * (-sales_part[s]) / total_sales) if k < len(sales_led) - 1 else rnd(rem)
                cr.append((s, -share))
                rem -= share
            for n, a in lines:
                add(y, qd[q], "Sales", [(n, a)] + [(s, v * a / tot) for s, v in cr], "Sales invoices - quarter %d" % (q + 1), party=n)
        for n in deb:
            bankpart[n] = m[n] - bill_d[n]
        pur = [n for n in names if grp[n] == "Purchase Accounts"][0]
        total_pur = C[y][pur]
        cre = [n for n in names if grp[n] == "Sundry Creditors"]
        wc = {n: -C[y][n] for n in cre}
        sc = sum(wc.values())
        bill_c = {n: rnd(total_pur * wc[n] / sc) for n in cre}
        bigc = max(cre, key=lambda n: wc[n])
        bill_c[bigc] = rnd(bill_c[bigc] + total_pur - sum(bill_c.values()))
        for q in range(4):
            for n in cre:
                a = split4(bill_c[n])[q]
                if a:
                    add(y, qd[q], "Purchase", [(pur, a), (n, -a)], "Purchase of raw materials - quarter %d" % (q + 1), party=n)
        for n in cre:
            bankpart[n] = m[n] + bill_c[n]
        done |= set(sales_led) | {pur}
        # --- stock
        d_stock = C[y]["Closing Stock"] - O[y]["Closing Stock"]
        add(y, qd[3], "Journal", [("Closing Stock", d_stock), ("Changes in Inventories", -d_stock)], "Closing stock as per physical verification and valuation")
        done |= {"Closing Stock", "Changes in Inventories"}
        # --- fixed assets: additions through bank, depreciation by journal
        dep_lines = []
        for n in fa:
            adds = ADDITIONS.get(n, []) if y == 2026 else []
            a_tot = sum(a for a, _, _ in adds)
            for a, d, t in adds:
                add(y, d, "Payment", [(n, a), (bank, -a)], t)
            dep_n = a_tot - m[n]
            dep_lines.append((n, dep_n))
        dep_tot = sum(v for _, v in dep_lines)
        assert abs(dep_tot - C[y]["Depreciation"]) < 1, ("depreciation mismatch", y, dep_tot, C[y]["Depreciation"])
        add(y, qd[3], "Journal", [("Depreciation", dep_tot)] + [(n, -v) for n, v in dep_lines], "Depreciation for the year")
        done |= set(fa) | {"Depreciation"}
        # --- accruals by journal
        acc_exp = {}
        for lia, exp in ACCRUE.items():
            amt = -m[lia]
            if amt > 0.5:
                add(y, qd[3], "Journal", [(exp, amt), (lia, -amt)], "Provision for the year - %s" % lia)
                acc_exp[exp] = acc_exp.get(exp, 0.0) + amt
                done.add(lia)
        # --- everything else through the bank, quarter by quarter
        for n in names:
            if n == bank or n in done:
                continue
            if n in bankpart and (n in deb or n in cre):
                continue
            bankpart[n] = (C[y][n] - acc_exp.get(n, 0.0)) if grp[n] in NOMINAL else m[n]
        for q in range(4):
            pay, rec = [], []
            for n, v in bankpart.items():
                if n in done and n not in deb and n not in cre:
                    continue
                part = split4(abs(v))[q] if abs(v) >= 0.5 else 0
                if not part:
                    continue
                (pay if v > 0 else rec).append((n, part))
            if pay:
                t = sum(a for _, a in pay)
                add(y, qd[q], "Payment", pay + [(bank, -t)], "Payments - quarter %d" % (q + 1))
            if rec:
                t = sum(a for _, a in rec)
                add(y, qd[q], "Receipt", [(bank, t)] + [(n, -a) for n, a in rec], "Receipts - quarter %d" % (q + 1))
    return names, grp, O, C, vouchers, open_res


def tdate(d):
    return d.strftime("%Y%m%d")


def amt_xml(name, v):
    """Debit amounts are negative in Tally XML, credit amounts positive."""
    dr = v > 0
    return ("<ALLLEDGERENTRIES.LIST><LEDGERNAME>%s</LEDGERNAME><ISDEEMEDPOSITIVE>%s</ISDEEMEDPOSITIVE><AMOUNT>%.2f</AMOUNT></ALLLEDGERENTRIES.LIST>"
            % (escape(name), "Yes" if dr else "No", -v))


def envelope(report, body):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA>'
            '<REQUESTDESC><REPORTNAME>%s</REPORTNAME><STATICVARIABLES><SVCURRENTCOMPANY>%s</SVCURRENTCOMPANY></STATICVARIABLES></REQUESTDESC>'
            '<REQUESTDATA>%s</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>' % (report, escape(COMPANY), body))


def masters_xml(names, grp, O):
    out = []
    for n in names:
        o = O[2025][n]
        ob = "" if abs(o) < 0.005 else "<OPENINGBALANCE>%.2f</OPENINGBALANCE>" % (-o)
        out.append('<TALLYMESSAGE xmlns:UDF="TallyUDF"><LEDGER NAME="%s" ACTION="Create"><NAME>%s</NAME><PARENT>%s</PARENT>%s</LEDGER></TALLYMESSAGE>'
                   % (escape(n, {'"': "&quot;"}), escape(n), escape(grp[n]), ob))
    out.append('<TALLYMESSAGE xmlns:UDF="TallyUDF"><LEDGER NAME="Profit &amp; Loss A/c" ACTION="Alter"><NAME>Profit &amp; Loss A/c</NAME>'
               '<OPENINGBALANCE>%.2f</OPENINGBALANCE></LEDGER></TALLYMESSAGE>' % OPEN_RES_PY)
    return envelope("All Masters", "".join(out))


def vouchers_xml(vs):
    out = []
    for v in sorted(vs, key=lambda x: (x["date"], x["type"], x["no"])):
        lines = "".join(amt_xml(n, a) for n, a in v["lines"])
        party = "<PARTYLEDGERNAME>%s</PARTYLEDGERNAME>" % escape(v["party"]) if v["party"] else ""
        out.append('<TALLYMESSAGE xmlns:UDF="TallyUDF"><VOUCHER VCHTYPE="%s" ACTION="Create" OBJVIEW="Accounting Voucher View">'
                   '<DATE>%s</DATE><VOUCHERTYPENAME>%s</VOUCHERTYPENAME><VOUCHERNUMBER>%d</VOUCHERNUMBER>%s<NARRATION>%s</NARRATION>'
                   '<PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>%s</VOUCHER></TALLYMESSAGE>'
                   % (v["type"], tdate(v["date"]), v["type"], v["no"], party, escape(v["narr"]), lines))
    return envelope("Vouchers", "".join(out))


HOW = """HOW TO LOAD THE SAMPLE COMPANY INTO TALLY PRIME
(All names and amounts are invented. Use a new, empty company only - never your client's company.)

A. Create the company
 1. In Tally Prime press Alt+K (Company) > Create, or from the Select Company screen choose Create Company.
 2. Name:                      Sample Engineering Private Limited   (type exactly this)
    Financial year begins:    01-04-2024
    Books beginning from:     01-04-2024
    Maintain:                 Accounts only   (this sample has no stock items)
 3. Accept the remaining defaults and save.

B. Import the files (do them in this order)
 1. Press Alt+O (Import) > Masters. File type: XML (Tally). Path: the full path of 1_Masters.xml. Press Enter.
 2. Alt+O > Transactions (Vouchers). Path: 2_Vouchers_FY2024-25.xml. Enter.
 3. Alt+O > Transactions (Vouchers). Path: 3_Vouchers_FY2025-26.xml. Enter.
    Tally shows a summary with the number of items created. 'Errors' or 'Ignored' should be 0.
 If Tally reports that 'Profit & Loss A/c' could not be altered: open Chart of Accounts > Ledgers > Alter > Profit & Loss A/c,
 enter Opening Balance 18,50,000.00 Cr, save, and import the two voucher files again.

C. Check the import before the demo
 1. Display More Reports > Trial Balance, period 01-04-2025 to 31-03-2026. Compare with Expected_Trial_Balance.csv (column 'FY2025-26').
 2. Change the period to 01-04-2024 to 31-03-2025. Compare with column 'FY2024-25'.
 3. Total of debit and credit columns must agree in both years.

D. Use it in the application
 1. Keep Tally Prime open with the sample company loaded, ODBC/HTTP server enabled on port 9000
    (F1 Help > Settings > Connectivity > Client/Server configuration: Tally acts as Server or Both, port 9000).
 2. In the application sidebar choose the sample company, the year ended 31-Mar-2026, and pull the trial balance.
 3. In the 'Previous year' tab pull the year ended 31-Mar-2025 from the same company. Both years load from the one Tally company.
 4. Closing stock is booked as a ledger ('Closing Stock' with an offsetting 'Changes in Inventories' entry), so no stock summary is needed.
 5. Depreciation tab: the additions to enter are  Plant and Machinery 7,00,000 (15-Jun-2025),  Computers and Printers 1,20,000 (01-Oct-2025),
    Vehicles 1,35,000 (20-Jan-2026). The opening cost and accumulated depreciation split is for you to enter (the sample uses opening cost = 1.30 x opening WDV).

Note: the vouchers are summary entries (one per quarter) written to give the right balances; GST is not posted separately.
"""


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "Sample_Tally_Company"
    os.makedirs(out, exist_ok=True)
    names, grp, O, C, vouchers, open_res = build()
    # prove the books balance
    for y in (2025, 2026):
        bal = dict(O[y])
        for v in vouchers[y]:
            assert abs(sum(a for _, a in v["lines"])) < 0.02, ("unbalanced voucher", v)
            for n, a in v["lines"]:
                bal[n] += a
        for n in names:
            assert abs(bal[n] - C[y][n]) < 0.02, ("balance mismatch", y, n, bal[n], C[y][n])
    with open(os.path.join(out, "1_Masters.xml"), "w", encoding="utf-8") as f:
        f.write(masters_xml(names, grp, O))
    for y, fn in ((2025, "2_Vouchers_FY2024-25.xml"), (2026, "3_Vouchers_FY2025-26.xml")):
        with open(os.path.join(out, fn), "w", encoding="utf-8") as f:
            f.write(vouchers_xml(vouchers[y]))
    fixv = {y: [v for v in vouchers[y] if v["narr"].startswith("Closing stock")] for y in (2025, 2026)}
    with open(os.path.join(out, "4_Closing_Stock_Journals_ONLY.xml"), "w", encoding="utf-8") as f:
        f.write(vouchers_xml(fixv[2025] + fixv[2026]))
    with open(os.path.join(out, "Expected_Trial_Balance.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Ledger", "Group", "FY2024-25 closing (Dr +, Cr -)", "FY2025-26 closing (Dr +, Cr -)"])
        for n in names:
            w.writerow([n, grp[n], "%.2f" % C[2025][n], "%.2f" % C[2026][n]])
        w.writerow(["Profit & Loss A/c", "Primary",
                    "%.2f" % -(open_res[2025] - sum(v for k, v in C[2025].items() if grp[k] in NOMINAL)),
                    "%.2f" % -(open_res[2026] - sum(v for k, v in C[2026].items() if grp[k] in NOMINAL))])
    with open(os.path.join(out, "HOW_TO_IMPORT.txt"), "w", encoding="utf-8") as f:
        f.write(HOW)
    print("Created in '%s': %d + %d vouchers; books balance in both years." % (out, len(vouchers[2025]), len(vouchers[2026])))
    print("Next: open HOW_TO_IMPORT.txt")


if __name__ == "__main__":
    main()
