"""
Generates the synthetic client used to build and demonstrate AuditLens.

Bharat Precision Components Private Limited is fictitious.  No client
data of any kind is used anywhere in this project.

Defects are deliberately seeded so that every analytical routine has
something to find, and so that the tests have known expected results:

  * a ledger outside the firm's numbering convention, to exercise the
    keyword fallback and the unmapped queue
  * a sharp movement in three ratios, to trigger the Schedule III
    25 per cent explanation requirement
  * round-sum, weekend, back-dated, period-end and rare-combination
    journal entries, to exercise the SA 240 routines
  * an infrequent posting user
"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
SEED = 20250401
rng = random.Random(SEED)

COMPANY = "Bharat Precision Components Private Limited"
CIN = "U29253MH2011PTC000000"   # fictitious


# --------------------------------------------------------------------------
# Trial balance
# --------------------------------------------------------------------------
# (code, name, FY 2024-25 net, FY 2023-24 net) - debit positive, in rupees.

LEDGERS: list[tuple[str, str, float, float]] = [
    # Equity and liabilities (credit balances carry a negative net)
    ("1001", "Equity share capital", -2_50_00_000, -2_50_00_000),
    ("1101", "Securities premium", -1_20_00_000, -1_20_00_000),
    ("1102", "Surplus in Statement of Profit and Loss", -4_86_42_500, -3_94_10_000),
    ("1201", "Term loan from State Bank of India", -3_10_00_000, -3_85_00_000),
    ("1251", "Deferred tax liabilities (net)", -28_40_000, -25_10_000),
    ("1291", "Provision for gratuity (long-term)", -34_20_000, -30_80_000),
    ("1301", "Cash credit facility from HDFC Bank", -1_92_00_000, -1_18_00_000),
    ("1331", "Trade payables - micro and small enterprises", -68_40_000, -52_30_000),
    ("1332", "Trade payables - other than micro and small", -3_46_20_000, -2_71_50_000),
    ("1361", "Statutory dues payable", -41_80_000, -33_60_000),
    ("1362", "Employee benefits payable", -29_50_000, -26_40_000),
    ("1391", "Provision for taxation", -52_00_000, -61_00_000),
    # Assets
    ("2001", "Freehold land", 1_45_00_000, 1_45_00_000),
    ("2002", "Factory building", 2_86_00_000, 2_86_00_000),
    ("2003", "Plant and machinery", 6_74_00_000, 5_92_00_000),
    ("2004", "Furniture and fixtures", 38_00_000, 34_00_000),
    ("2005", "Computers and peripherals", 46_00_000, 39_00_000),
    ("2010", "Accumulated depreciation", -4_18_60_000, -3_47_20_000),
    ("2051", "Capital work-in-progress", 62_00_000, 18_00_000),
    ("2061", "Computer software", 24_00_000, 24_00_000),
    ("2091", "Investment in equity of associate", 85_00_000, 85_00_000),
    ("2121", "Security deposits with utilities", 32_40_000, 30_10_000),
    ("2221", "Raw materials", 1_84_60_000, 1_46_20_000),
    ("2222", "Work-in-progress", 62_30_000, 54_80_000),
    ("2223", "Finished goods", 1_38_90_000, 1_02_40_000),
    ("2224", "Stores and spares", 28_70_000, 26_10_000),
    ("2251", "Trade receivables - considered good", 4_92_80_000, 3_18_40_000),
    ("2252", "Provision for doubtful debts", -24_60_000, -14_20_000),
    ("2281", "Cash in hand", 2_40_000, 3_10_000),
    ("2282", "Balances with banks in current accounts", 68_20_000, 1_24_60_000),
    ("2301", "Advances to suppliers", 47_30_000, 38_90_000),
    ("2331", "Prepaid expenses", 18_40_000, 16_20_000),
    ("2332", "GST input tax credit receivable", 74_60_000, 58_30_000),
    # Income
    ("3001", "Sale of manufactured goods", -21_46_00_000, -17_28_00_000),
    ("3002", "Sale of scrap", -38_40_000, -31_20_000),
    ("3101", "Interest income on deposits", -6_80_000, -9_40_000),
    ("3102", "Dividend from associate", -8_50_000, -6_20_000),
    # Expenses
    ("4001", "Cost of materials consumed", 12_84_60_000, 10_36_40_000),
    ("4151", "Changes in inventories of finished goods and WIP", -44_00_000, -18_60_000),
    ("4201", "Salaries and wages", 2_18_40_000, 1_92_60_000),
    ("4202", "Contribution to provident and other funds", 24_60_000, 21_80_000),
    ("4203", "Staff welfare expenses", 14_20_000, 12_40_000),
    ("4301", "Interest on term loan", 34_80_000, 41_20_000),
    ("4302", "Interest on working capital facilities", 21_60_000, 13_40_000),
    ("4303", "Bank charges", 4_20_000, 3_60_000),
    ("4351", "Depreciation on tangible assets", 71_40_000, 64_80_000),
    ("4352", "Amortisation of intangible assets", 4_80_000, 4_80_000),
    ("4401", "Power and fuel", 96_40_000, 82_30_000),
    ("4402", "Repairs to machinery", 38_20_000, 33_60_000),
    ("4403", "Rent", 24_00_000, 24_00_000),
    ("4404", "Legal and professional charges", 28_60_000, 19_40_000),
    ("4405", "Payment to auditors", 6_50_000, 5_50_000),
    ("4406", "Travelling and conveyance", 21_30_000, 18_70_000),
    ("4407", "Insurance", 12_40_000, 11_20_000),
    ("4408", "CSR expenditure", 14_60_000, 12_80_000),
    ("4409", "Freight outward", 46_80_000, 38_20_000),
    ("4410", "Miscellaneous expenses", 18_90_000, 16_40_000),
    ("4901", "Current tax", 62_00_000, 71_00_000),
    ("4951", "Deferred tax", 3_30_000, 2_80_000),
    # Seeded defect: outside the firm's code convention, so the keyword
    # fallback has to catch it.
    ("9911", "Capital advance for machinery under installation", 26_00_000, 0),
    # Seeded defect: unmappable by code or keyword - goes to the review queue.
    ("9999", "Suspense account - to be cleared", 4_20_000, 0),
]


def _balance(rows: list[tuple[str, str, float, float]], column: int) -> list[tuple[str, str, float, float]]:
    """Force the trial balance to tie by taking the difference to reserves."""
    total = sum(r[column] for r in rows)
    adjusted = []
    for r in rows:
        if r[0] == "1102":
            new = list(r)
            new[column] = r[column] - total
            adjusted.append(tuple(new))
        else:
            adjusted.append(r)
    return adjusted


def write_trial_balances() -> None:
    rows = _balance(_balance(LEDGERS, 2), 3)

    for fy, column in (("2024-25", 2), ("2023-24", 3)):
        records = []
        for code, name, cur, pri in rows:
            net = cur if column == 2 else pri
            records.append(
                {
                    "Account Code": code,
                    "Ledger Name": name,
                    "Debit": round(net, 2) if net > 0 else 0.0,
                    "Credit": round(-net, 2) if net < 0 else 0.0,
                }
            )
        df = pd.DataFrame(records)
        path = HERE / f"trial_balance_FY{fy}.csv"
        df.to_csv(path, index=False)
        total_dr, total_cr = df["Debit"].sum(), df["Credit"].sum()
        print(f"  {path.name}: {len(df)} ledgers, Dr {total_dr:,.2f} / Cr {total_cr:,.2f}, "
              f"difference {total_dr - total_cr:,.2f}")


# --------------------------------------------------------------------------
# General ledger
# --------------------------------------------------------------------------

ROUTINE_PATTERNS: list[tuple[str, str, str, str, tuple[int, int]]] = [
    ("4001", "Cost of materials consumed", "1332", "Trade payables - other than micro and small",
     "Purchase of raw material", (24_000, 2_400_000)),
    ("2251", "Trade receivables - considered good", "3001", "Sale of manufactured goods",
     "Sale invoice raised", (32_000, 3_200_000)),
    ("2282", "Balances with banks in current accounts", "2251", "Trade receivables - considered good",
     "Collection from customer", (28_000, 2_800_000)),
    ("1332", "Trade payables - other than micro and small", "2282", "Balances with banks in current accounts",
     "Payment to supplier", (22_000, 2_200_000)),
    ("4201", "Salaries and wages", "1362", "Employee benefits payable",
     "Payroll for the month", (19_500, 1_950_000)),
    ("4401", "Power and fuel", "1332", "Trade payables - other than micro and small",
     "Electricity charges", (9_200, 920_000)),
    ("4409", "Freight outward", "1332", "Trade payables - other than micro and small",
     "Outward freight", (3_400, 340_000)),
    ("4402", "Repairs to machinery", "1332", "Trade payables - other than micro and small",
     "Machinery repairs", (2_800, 280_000)),
]

USERS = ["priya.sharma", "amit.deshpande", "ravi.krishnan", "nisha.patel"]

FY_START = date(2024, 4, 1)
FY_END = date(2025, 3, 31)

HOLIDAYS = {
    date(2024, 8, 15), date(2024, 10, 2), date(2024, 10, 31),
    date(2024, 11, 1), date(2025, 1, 26), date(2025, 3, 14),
}


def _random_working_day() -> date:
    while True:
        d = FY_START + timedelta(days=rng.randint(0, (FY_END - FY_START).days))
        if d.weekday() < 5 and d not in HOLIDAYS:
            return d


def write_general_ledger() -> None:
    lines: list[dict] = []
    counter = 1

    def add_entry(
        dr_code: str, dr_name: str, cr_code: str, cr_name: str,
        amount: float, narration: str, posting: date,
        user: str, entry_dt: date | None = None,
    ) -> None:
        nonlocal counter
        entry_id = f"JV{counter:05d}"
        counter += 1
        entry_dt = entry_dt or posting
        for code, name, dr, cr in (
            (dr_code, dr_name, amount, 0.0),
            (cr_code, cr_name, 0.0, amount),
        ):
            lines.append({
                "entry_id": entry_id,
                "posting_date": posting.strftime("%d-%m-%Y"),
                "entry_date": entry_dt.strftime("%d-%m-%Y"),
                "account_code": code,
                "account_name": name,
                "debit": round(dr, 2),
                "credit": round(cr, 2),
                "narration": narration,
                "posted_by": user,
            })

    # ---- routine population ------------------------------------------
    # Amounts are drawn log-uniformly.  Genuine transaction populations are
    # scale-invariant and therefore conform to Benford's law; drawing from a
    # uniform range would not, and the Benford routine would report a false
    # departure on a clean population.
    for _ in range(900):
        dr_code, dr_name, cr_code, cr_name, narration, (lo, hi) = rng.choice(ROUTINE_PATTERNS)
        amount = int(math.exp(rng.uniform(math.log(lo), math.log(hi))))
        amount += rng.randint(1, 99) * 7          # avoids accidental round sums
        add_entry(dr_code, dr_name, cr_code, cr_name, float(amount), narration,
                  _random_working_day(), rng.choice(USERS[:3]))

    # ---- seeded: round-sum entries -----------------------------------
    for amount in (25_00_000, 10_00_000, 50_00_000, 15_00_000):
        add_entry("4404", "Legal and professional charges",
                  "1332", "Trade payables - other than micro and small",
                  float(amount), "Consultancy retainer", _random_working_day(),
                  rng.choice(USERS[:3]))

    # ---- seeded: weekend and holiday postings ------------------------
    for d in (date(2024, 6, 15), date(2024, 9, 21), date(2025, 2, 8), date(2024, 10, 2)):
        add_entry("4410", "Miscellaneous expenses",
                  "2282", "Balances with banks in current accounts",
                  float(rng.randint(120000, 480000)), "Sundry settlement", d,
                  rng.choice(USERS[:3]))

    # ---- seeded: material entries in the final week ------------------
    for offset, amount in ((2, 1_84_00_000), (4, 96_00_000), (1, 1_42_00_000)):
        add_entry("2251", "Trade receivables - considered good",
                  "3001", "Sale of manufactured goods",
                  float(amount), "Year-end despatch",
                  FY_END - timedelta(days=offset), rng.choice(USERS[:3]))

    # ---- seeded: back-dated entries ----------------------------------
    for posting, lag in ((date(2024, 12, 20), 74), (date(2025, 1, 9), 61)):
        add_entry("4410", "Miscellaneous expenses",
                  "1361", "Statutory dues payable",
                  float(rng.randint(300000, 900000)), "Prior period adjustment",
                  posting, "amit.deshpande", posting + timedelta(days=lag))

    # ---- seeded: rare account combinations ---------------------------
    add_entry("1102", "Surplus in Statement of Profit and Loss",
              "2252", "Provision for doubtful debts",
              38_00_000.0, "Write-off approved by the board",
              date(2025, 3, 29), "nisha.patel")
    add_entry("2091", "Investment in equity of associate",
              "1102", "Surplus in Statement of Profit and Loss",
              12_00_000.0, "Revaluation of associate holding",
              date(2025, 3, 30), "nisha.patel")

    # ---- seeded: infrequent posting user -----------------------------
    for _ in range(3):
        add_entry("4410", "Miscellaneous expenses",
                  "2282", "Balances with banks in current accounts",
                  float(rng.randint(400000, 1200000)), "Reimbursement",
                  _random_working_day(), "s.venkatesh")

    df = pd.DataFrame(lines)
    path = HERE / "general_ledger_FY2024-25.csv"
    df.to_csv(path, index=False)
    print(f"  {path.name}: {df['entry_id'].nunique()} entries, {len(df)} lines")


def main() -> None:
    print(f"Generating synthetic data for {COMPANY} (fictitious, CIN {CIN})")
    write_trial_balances()
    write_general_ledger()
    print("Done. These files contain no real client information.")


if __name__ == "__main__":
    main()
