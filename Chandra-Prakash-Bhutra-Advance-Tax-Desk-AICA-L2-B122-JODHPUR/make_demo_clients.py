"""Create the demo_clients/ folder: six invented clients, each with its own test files, and the blank templates.

Run:  python make_demo_clients.py

Every name, PAN, TAN, mobile number and figure here is made up. The mobile numbers start with 0 so they
cannot belong to anyone. `python seed_demo.py` (or the Load demo clients button in the app) reads this
folder and loads the clients.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font

OUT = Path(__file__).resolve().parent / "demo_clients"

# (ledger, group, debit, credit) - a trading concern, books up to 31 Oct 2026
LEDGERS = [
    ("Proprietor Capital", "Capital Account", 0, 1800000),
    ("Drawings", "Capital Account", 280000, 0),
    ("HDFC Bank CC", "Bank OD A/c", 0, 950000),
    ("Sundry Creditors", "Sundry Creditors", 0, 1120000),
    ("GST Payable", "Duties & Taxes", 0, 64000),
    ("Furniture", "Fixed Assets", 210000, 0),
    ("Delivery Van", "Fixed Assets", 540000, 0),
    ("Sundry Debtors", "Sundry Debtors", 2356000, 0),
    ("Cash", "Cash-in-Hand", 46000, 0),
    ("State Bank Current A/c", "Bank Accounts", 818000, 0),
    ("Opening Stock", "Stock-in-Hand", 1450000, 0),
    ("Sales - Hardware", "Sales Accounts", 0, 9840000),
    ("Sales - Paints", "Sales Accounts", 0, 2260000),
    ("Purchases - Hardware", "Purchase Accounts", 7610000, 0),
    ("Purchases - Paints", "Purchase Accounts", 1720000, 0),
    ("Freight Inward", "Direct Expenses", 148000, 0),
    ("Salaries", "Indirect Expenses", 462000, 0),
    ("Shop Rent", "Indirect Expenses", 245000, 0),
    ("Electricity Charges", "Indirect Expenses", 58000, 0),
    ("Bank Interest and Charges", "Indirect Expenses", 71000, 0),
    ("Vehicle Running Expenses", "Indirect Expenses", 96000, 0),
    ("Office and General Expenses", "Indirect Expenses", 83000, 0),
    ("Discount Received", "Indirect Incomes", 0, 39000),
    ("Insurance Claim Received", "Indirect Incomes", 0, 120000),
]
assert sum(l[2] for l in LEDGERS) == sum(l[3] for l in LEDGERS)


def scaled(factor: float, capital_name: str) -> list:
    """The same set of books at another size, for a second and third client."""
    rows = [(capital_name if l[0] == "Proprietor Capital" else l[0], l[1], int(l[2] * factor), int(l[3] * factor))
            for l in LEDGERS]
    assert sum(r[2] for r in rows) == sum(r[3] for r in rows)
    return rows


# ------------------------------------------------------------ trial balances
def tb_tally(path: Path, rows: list, title: str) -> None:
    """Title rows on top, Particulars / Debit / Credit, no group column."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Trial Balance"
    ws.append([title])
    ws.append(["Trial Balance"])
    ws.append(["1-Apr-26 to 31-Oct-26"])
    ws.append([])
    ws.append(["Particulars", "Closing Balance", None])
    ws.append([None, "Debit", "Credit"])
    for r in rows:
        ws.append([r[0], r[2] or None, r[3] or None])
    ws.append(["Grand Total", sum(r[2] for r in rows), sum(r[3] for r in rows)])
    wb.save(path)


def tb_busy(path: Path, rows: list) -> None:
    """CSV with a single balance column and a Dr/Cr column."""
    pd.DataFrame([{"Account Name": r[0], "Group": r[1], "Closing Balance": r[2] or r[3],
                   "Dr/Cr": "Dr" if r[2] else "Cr"} for r in rows]).to_csv(path, index=False)


def tb_zoho(path: Path, rows: list) -> None:
    """Balance with Dr/Cr suffix inside the cell and an account type column."""
    kind = {"Sales Accounts": "Income", "Indirect Incomes": "Other Income", "Purchase Accounts": "Cost of Goods Sold",
            "Direct Expenses": "Cost of Goods Sold", "Indirect Expenses": "Expense", "Stock-in-Hand": "Stock",
            "Fixed Assets": "Fixed Asset", "Capital Account": "Equity", "Sundry Debtors": "Accounts Receivable",
            "Sundry Creditors": "Accounts Payable", "Duties & Taxes": "Other Current Liability",
            "Bank Accounts": "Bank", "Bank OD A/c": "Other Current Liability", "Cash-in-Hand": "Cash"}
    pd.DataFrame([{"Account": r[0], "Account Type": kind[r[1]],
                   "Balance": f"{(r[2] or r[3]):,.2f} {'Dr' if r[2] else 'Cr'}"} for r in rows]).to_excel(path, index=False)


# ------------------------------------------------------------- capital gains
def cg_broker(path: Path) -> None:
    """In the style of a stock broker's tax P&L export: title rows, then one row per sale."""
    rows = [
        ("ALPHA INDUSTRIES", "INE000A01001", "EQ", "10-04-2025", "15-06-2026", 200, 100000, 160000, 60000),
        ("BETA FINANCE", "INE000B01002", "EQ", "01-05-2026", "20-08-2026", 500, 200000, 170000, -30000),
        ("GAMMA FLEXI CAP FUND - DIRECT", "INF000G01003", "Equity MF", "05-01-2026", "10-09-2026", 1250.5, 50000, 62000, 12000),
        ("DELTA LIQUID FUND - DIRECT", "INF000D01004", "Debt MF", "01-01-2022", "01-06-2026", 95.2, 300000, 345000, 45000),
        ("EPSILON GOLD ETF UNITS", "INF000E01005", "Gold", "12-02-2023", "18-07-2026", 400, 220000, 310000, 90000),
        ("NIFTY OCT FUT", "", "F&O", "01-10-2026", "03-10-2026", 50, 0, 0, 5000),
    ]
    wb = Workbook()
    ws = wb.active
    ws.title = "Tax P&L"
    ws.append(["Demo Broking Limited"])
    ws.append(["Tax P&L statement from 01-04-2026 to 31-10-2026"])
    ws.append(["Client ID: DEMO02"])
    ws.append([])
    ws.append(["Symbol", "ISIN", "Segment", "Entry Date", "Exit Date", "Quantity", "Buy Value", "Sell Value", "Realized P&L"])
    for cell in ws[5]:
        cell.font = Font(bold=True)
    for r in rows:
        ws.append(list(r))
    ws.append(["Total", "", "", "", "", "", sum(r[6] for r in rows), sum(r[7] for r in rows), sum(r[8] for r in rows)])
    wb.save(path)


def cg_fund_app(path: Path) -> None:
    """In the style of a mutual fund app: no buy date, but a short / long term column."""
    pd.DataFrame([
        {"Scheme Name": "Demo Bluechip Fund - Growth", "Category": "Equity", "Gain Type": "Long Term",
         "Redemption Date": "12-05-2026", "Purchase Amount": 420000, "Redemption Amount": 600000, "Capital Gain": 180000},
        {"Scheme Name": "Demo Midcap Fund - Growth", "Category": "Equity", "Gain Type": "Short Term",
         "Redemption Date": "20-07-2026", "Purchase Amount": 150000, "Redemption Amount": 175000, "Capital Gain": 25000},
        {"Scheme Name": "Demo Corporate Bond Fund", "Category": "Debt", "Gain Type": "Short Term",
         "Redemption Date": "03-08-2026", "Purchase Amount": 200000, "Redemption Amount": 215000, "Capital Gain": 15000},
        {"Scheme Name": "Demo Smallcap Fund - Growth", "Category": "Equity", "Gain Type": "Long Term",
         "Redemption Date": "15-09-2026", "Purchase Amount": 120000, "Redemption Amount": 100000, "Capital Gain": -20000},
    ]).to_csv(path, index=False)


CG_COLUMNS = ["Asset / scrip", "Asset type", "Buy date", "Sell date", "Quantity", "Buy value", "Sell value",
              "Expenses on transfer", "Gain / loss (optional)"]


def cg_sheet(path: Path, rows: list, example_only: bool = False) -> None:
    """The app's own capital gains sheet: blank template, or filled in for a client."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Capital gains"
    ws.append(CG_COLUMNS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for r in rows:
        ws.append(list(r))
    for col, width in zip("ABCDEFGHI", (34, 16, 12, 12, 10, 14, 14, 20, 22)):
        ws.column_dimensions[col].width = width
    if example_only:
        how = wb.create_sheet("How to fill")
        for line in [
            "One row per sale. Dates as DD-MM-YYYY. Delete the example row.",
            "Asset type: Equity, Equity MF, Debt MF, Property, Gold, Unlisted shares, Bonds. Intraday and F&O rows are left out.",
            "Give either the gain / loss, or the buy value and sell value (expenses are deducted).",
            "Listed shares and equity funds are long-term when held for more than 12 months; other assets, more than 24 months.",
            "Debt funds are always treated as short-term and taxed at slab rates.",
        ]:
            how.append([line])
        how.column_dimensions["A"].width = 120
    wb.save(path)


def tb_template(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Trial Balance"
    ws.append(["Ledger", "Group", "Debit", "Credit"])
    for c in ws[1]:
        c.font = Font(bold=True)
    for r in LEDGERS[10:16]:
        ws.append([r[0], r[1], r[2] or None, r[3] or None])
    for col, w in zip("ABCD", (34, 24, 14, 14)):
        ws.column_dimensions[col].width = w
    note = wb.create_sheet("How to fill")
    for line in ["Replace the example rows. One row per ledger. Balance sheet ledgers may be left in; they are ignored.",
                 "Give the closing balance in Debit or Credit (not both).",
                 "Group is optional but improves automatic classification.",
                 "Any software: export the trial balance to Excel and paste the columns here,",
                 "or upload the export directly and match the columns in the app."]:
        note.append([line])
    wb.save(path)


# ------------------------------------------------------------------ Form 26AS
def form_26as(path: Path, pan: str, name: str, tds: list, tcs: list = ()) -> None:
    """A text file laid out like the TRACES text download. Rows: (name, TAN, section, amount, tax)."""
    lines = [f"File Creation Date^27-11-2026^Permanent Account Number (PAN)^{pan}^Current Status of PAN^Active^"
             "Financial Year^2026-27^Assessment Year^2027-28",
             f"Name of Assessee^{name}", "DEMO FILE - INVENTED DATA, NOT FROM TRACES", ""]

    def part(title: str, who: str, word: str, rows: list) -> None:
        lines.append(title)
        lines.append(f"Sr. No.^Name of {who}^TAN of {who}^^^^^Total Amount Paid / Credited^Total Tax {word}^Total {word[:1]}{'DS' if word == 'Deducted' else 'CS'} Deposited")
        for n, (party, tan, section, amount, tax) in enumerate(rows, 1):
            lines.append(f"{n}^{party}^{tan}^^^^^{amount:.2f}^{tax:.2f}^{tax:.2f}")
            lines.append("^Sr. No.^Section^Transaction Date^Status of Booking^Date of Booking^Remarks^Amount^Tax^Deposited")
            lines.append(f"^1^{section}^30-Sep-2026^F^15-Oct-2026^-^{amount:.2f}^{tax:.2f}^{tax:.2f}")
        lines.append("")

    if tds:
        part("PART-I - Details of Tax Deducted at Source", "Deductor", "Deducted", list(tds))
    if tcs:
        part("PART-VI - Details of Tax Collected at Source", "Collector", "Collected", list(tcs))
    path.write_text("\n".join(lines), encoding="utf-8")


# -------------------------------------------------------------------- clients
def client(folder: str, profile: dict) -> Path:
    d = OUT / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / "client.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return d


def main() -> None:
    OUT.mkdir(exist_ok=True)
    t = OUT / "templates"
    t.mkdir(exist_ok=True)
    tb_template(t / "trial_balance_template.xlsx")
    cg_sheet(t / "capital_gains_template.xlsx",
             [("Example Ltd (delete this row)", "Equity", "10-04-2025", "15-06-2026", 100, 100000, 160000, 250, "")], True)

    d = client("D01 Marudhar Hardware Stores", {
        "name": "D01 Marudhar Hardware Stores (Prop. R. Sharma) - Demo", "constitution": "Individual",
        "age_band": "below60", "resident": True, "regime": "auto", "mobile": "0000000001", "pan": "AAAPS0001A",
        "business": {"mode": "trial_balance", "file": "trial_balance_tally.xlsx", "books_date": "2026-10-31",
                     "closing_stock": 1620000, "add_backs": 45000, "less_deductions": 30000},
        "other_interest": 42000, "form_26as_file": "26AS.txt",
        "payments": [{"date": "2026-06-12", "amount": 60000}, {"date": "2026-09-14", "amount": 120000}],
        "what_to_test": "Tally trial balance without group names (some ledgers are flagged for checking), projection, 26AS reading."})
    tb_tally(d / "trial_balance_tally.xlsx", LEDGERS, "Marudhar Hardware Stores (Demo)")
    form_26as(d / "26AS.txt", "AAAPS0001A", "R SHARMA (DEMO)",
              [("DEMO BANK LIMITED", "JDHD00001A", "194A", 42000, 4200), ("DEMO BUILDERS PRIVATE LIMITED", "JDHD00002B", "194C", 300000, 3000)])

    d = client("D02 Dr A Mehta", {
        "name": "D02 Dr. A. Mehta (Presumptive Profession) - Demo", "constitution": "Individual",
        "age_band": "below60", "resident": True, "regime": "auto", "mobile": "0000000002", "pan": "AAAPM0002B",
        "business": {"mode": "presumptive", "books_date": "2026-10-31", "turnover": 2140000, "rate": 50},
        "other_dividend": 65000, "capital_gains_file": "capital_gains_broker_tax_pnl.xlsx", "form_26as_file": "26AS.txt",
        "payments": [], "what_to_test": "Presumptive income (single instalment by 15 March), broker tax P&L import with a loss, a debt fund and an F&O row."})
    cg_broker(d / "capital_gains_broker_tax_pnl.xlsx")
    form_26as(d / "26AS.txt", "AAAPM0002B", "A MEHTA (DEMO)",
              [("DEMO CITY HOSPITAL LIMITED", "JPRD00003C", "194J", 1200000, 120000), ("DEMO DIAGNOSTICS LLP", "JPRD00004D", "194J", 600000, 60000)])

    d = client("D03 Mrs K Iyer", {
        "name": "D03 Mrs. K. Iyer (Salaried) - Demo", "constitution": "Individual",
        "age_band": "below60", "resident": True, "regime": "auto", "mobile": "0000000003", "pan": "AAAPI0003C",
        "business": {"mode": "none"}, "salary": 1800000, "hp_self_occupied_interest": 200000, "deductions_old": 450000,
        "other_interest": 60000, "capital_gains_file": "capital_gains_fund_app.csv", "form_26as_file": "26AS.txt",
        "payments": [], "what_to_test": "Old versus new regime, mutual fund app statement with a short / long column and no buy dates, salary TDS from 26AS."})
    cg_fund_app(d / "capital_gains_fund_app.csv")
    form_26as(d / "26AS.txt", "AAAPI0003C", "K IYER (DEMO)", [("DEMO SOFTWARE SERVICES LIMITED", "BLRD00005E", "192", 1800000, 210000)])

    d = client("D04 S Verma HUF", {
        "name": "D04 S. Verma HUF - Demo", "constitution": "HUF", "resident": True, "regime": "auto",
        "mobile": "0000000004", "pan": "AAAHV0004D",
        "business": {"mode": "trial_balance", "file": "trial_balance_busy.csv", "books_date": "2026-10-31", "closing_stock": 810000},
        "hp_let_out_rent": 360000, "hp_municipal_tax": 12000, "form_26as_file": "26AS.txt",
        "payments": [{"date": "2026-06-15", "amount": 25000}],
        "what_to_test": "Busy CSV with one balance column and Dr/Cr, HUF, let-out property, a short first instalment."})
    tb_busy(d / "trial_balance_busy.csv", scaled(0.5, "Karta Capital"))
    form_26as(d / "26AS.txt", "AAAHV0004D", "S VERMA HUF (DEMO)", [("DEMO RETAIL LIMITED", "JDHD00006F", "194I", 360000, 36000)])

    d = client("D05 Demo Traders Firm", {
        "name": "D05 Demo Traders (Partnership Firm) - Demo", "constitution": "Firm", "mobile": "0000000005", "pan": "AAAFD0005E",
        "business": {"mode": "trial_balance", "file": "trial_balance_zoho.xlsx", "books_date": "2026-10-31",
                     "closing_stock": 3240000, "less_deductions": 600000},
        "form_26as_file": "26AS.txt",
        "payments": [{"date": "2026-06-15", "amount": 150000}, {"date": "2026-09-15", "amount": 300000}],
        "what_to_test": "Zoho export with Dr/Cr inside the amount, firm rate, partner remuneration as a further deduction, TDS and TCS in 26AS."})
    tb_zoho(d / "trial_balance_zoho.xlsx", scaled(2, "Partners Capital"))
    form_26as(d / "26AS.txt", "AAAFD0005E", "DEMO TRADERS (DEMO)", [("DEMO STEEL LIMITED", "MUMD00007G", "194Q", 6000000, 6000)],
              [("DEMO MOTORS LIMITED", "DELD00008H", "206C", 1500000, 15000)])

    d = client("D06 Demo Textiles LLP", {
        "name": "D06 Demo Textiles LLP - Demo", "constitution": "LLP", "mobile": "0000000006", "pan": "AAAFT0006F",
        "business": {"mode": "direct", "amount": 4250000}, "other_interest": 110000,
        "capital_gains_file": "capital_gains_sheet.xlsx",
        "payments": [{"date": "2026-06-15", "amount": 200000}],
        "what_to_test": "Full-year figure typed directly, the app's own capital gains sheet with a property sale and a short-term loss set off against it."})
    cg_sheet(d / "capital_gains_sheet.xlsx", [
        ("Factory plot at Pali", "Property", "15-06-2019", "10-08-2026", 1, 2500000, 4100000, 100000, ""),
        ("Unlisted shares of Demo Private Limited", "Unlisted shares", "01-12-2025", "01-09-2026", 2000, 700000, 500000, 0, ""),
    ])
    print("Demo clients written to", OUT)


if __name__ == "__main__":
    main()
