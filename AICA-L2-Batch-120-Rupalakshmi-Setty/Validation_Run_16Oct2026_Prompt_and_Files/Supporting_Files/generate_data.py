"""
Ledger Sentinel - Synthetic Data Generator
Generates a fictional Tally Prime Day Book export with planted fraud scenarios,
plus a separate hidden answer key for scoring the fraud detection rules engine.

Output: tally_daybook_export.xlsx, fraud_answer_key.xlsx
"""

import random
import pandas as pd
from datetime import datetime, timedelta
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

random.seed(42)

company_name = "Ad Hoc Company Limited"

users = [
    {"user_id": "U001", "name": "Ahmed Al Mansoori", "role": "Accountant"},
    {"user_id": "U002", "name": "Fatima Al Hashimi", "role": "Senior Accountant"},
    {"user_id": "U003", "name": "Rajesh Kumar", "role": "Finance Manager"},
    {"user_id": "U004", "name": "Sara Abdullah", "role": "Owner/Director"},
    {"user_id": "U005", "name": "Michael D'Souza", "role": "Accounts Clerk"},
    {"user_id": "U006", "name": "Priya Nair", "role": "Accounts Clerk"},
    {"user_id": "U007", "name": "Khalid Al Suwaidi", "role": "Controller"},
    {"user_id": "U008", "name": "Lisa Fernandes", "role": "Auditor Liaison"},
]

# Real TallyPrime books give every vendor its OWN ledger under the "Sundry
# Creditors" (Accounts Payable) group, rather than one shared generic
# account - that per-vendor granularity is what makes vendor-level analytics
# (like Rule 11's structured-disbursement check, see ledger_sentinel_rules.py)
# possible at all. This generator models that properly: "Accounts Payable"
# is a GROUP of 15 named vendor ledgers, not a single flat account.
VENDOR_NAMES = [
    "Al Noor Trading Services LLC", "Gulf Supplies & Co", "Zenith Logistics FZE",
    "Emirates Office Solutions",
    "Horizon Marketing Consultants", "Desert Rose Freight Services",
    "Al Maha Equipment Rental", "Continental Import Export LLC",
    "Silverline Facilities Management", "Prime Vendor Services FZE",
    "Al Ain Building Materials Trading", "Falcon IT Solutions FZE",
    "Noor Al Sabah Consultancy", "Union Office Supplies Trading",
    "Gulf Emirates Equipment Co",
]
vendor_accounts = [f"Accounts Payable - {v}" for v in VENDOR_NAMES]

# A SEPARATE, 16th vendor ledger - a quiet, rarely-used one, deliberately
# NOT part of the genuine-business pool above. This is the more realistic
# insider-fraud pattern discussed on the call: a seasoned insider siphoning
# funds is more likely to set up or exploit a quiet/low-activity vendor
# than to inflate a vendor real colleagues deal with every month (who would
# notice their own invoices looking wrong). It gets ZERO normal business -
# see the "Normal vendor transactions" block below, which only draws from
# VENDOR_NAMES, never this one.
SHELL_VENDOR_NAME = "Al Falah General Trading LLC"
shell_vendor_account = f"Accounts Payable - {SHELL_VENDOR_NAME}"

accounts = [
    "Sales - Domestic", "Sales - Export", "Purchase - Domestic", "Purchase - Import",
    "Inventory", "Accounts Receivable", "Bank - ADCB Current",
    "Bank - ENBD Current", "Cash in Hand", "VAT Output", "VAT Input",
    "Salaries Expense", "Rent Expense", "Utilities Expense", "Freight & Logistics",
    "Marketing Expense", "Office Supplies", "Suspense Account", "Miscellaneous Expense",
    "Commission Expense", "Bad Debts", "Depreciation", "Interest Expense",
    "Director's Loan", "Retained Earnings", "Capital Account"
] + vendor_accounts + [shell_vendor_account]
normal_accounts = [a for a in accounts if a not in ["Suspense Account", "Miscellaneous Expense"]]
# Real vendor ledgers are only ever touched by genuine purchase/payment
# transactions - never by an arbitrary unrelated pairing (a vendor ledger
# would never be credited by, say, a Salaries Expense posting). So the
# fully-random generic baseline below draws ONLY from the non-vendor pool;
# vendor ledgers get their own realistic "Normal vendor transactions" block
# further down instead. Without this separation, each vendor ledger picks
# up ~400 random unrelated touches/year purely from being 1-of-41 in a
# random pool, drowning any real vendor-level analytics (like Rule 11) in
# noise that could never occur in a real set of books.
non_vendor_normal_accounts = [a for a in normal_accounts if a not in vendor_accounts and a != shell_vendor_account]
purchase_side_accounts = ["Purchase - Domestic", "Purchase - Import", "Freight & Logistics",
                           "Office Supplies", "Marketing Expense", "Commission Expense"]
payment_side_accounts = ["Bank - ADCB Current", "Bank - ENBD Current", "Cash in Hand"]

start_date = datetime(2025, 1, 1)
end_date = datetime(2025, 12, 31)
total_days = (end_date - start_date).days

vouchers = []
voucher_counter = 1


def random_date_in_year(exclude_weekend=False, after_hours=False):
    day_offset = random.randint(0, total_days)
    dt = start_date + timedelta(days=day_offset)
    if exclude_weekend:
        while dt.weekday() in [4, 5]:  # Fri/Sat weekend in UAE
            day_offset = random.randint(0, total_days)
            dt = start_date + timedelta(days=day_offset)
    hour = random.choice([23, 0, 1, 2, 3]) if after_hours else random.randint(9, 18)
    return dt.replace(hour=hour, minute=random.randint(0, 59))


def random_amount(low=500, high=50000, round_amt=False):
    if round_amt:
        return random.choice([1000, 5000, 10000, 15000, 20000, 25000, 50000, 100000])
    return round(random.uniform(low, high), 2)


narrations_good = [
    "Payment received from customer as per invoice", "Purchase of goods from supplier as per PO",
    "Monthly salary disbursement", "Rent payment for warehouse facility",
    "Utility bill payment for office premises", "Freight charges for import shipment",
    "VAT payment to FTA", "Office supplies purchased", "Customer refund processed",
    "Bank charges debited", "Inventory adjustment post stock count", "Commission paid to sales agent",
]
narrations_vague = ["Misc entry", "Adjustment", "As discussed", "Entry", "N/A", ""]

# ---- Normal vouchers (generic baseline, 6,957) ----
for i in range(6957):
    user = random.choice(users)
    dt = random_date_in_year(exclude_weekend=True)
    debit_acc = random.choice(non_vendor_normal_accounts)
    credit_acc = random.choice([a for a in non_vendor_normal_accounts if a != debit_acc])
    vouchers.append({
        "voucher_id": f"V{voucher_counter:06d}", "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M"), "day_of_week": dt.strftime("%A"),
        "created_by": user["user_id"], "created_by_name": user["name"],
        "altered_by": "", "altered_date": "",
        "debit_account": debit_acc, "credit_account": credit_acc, "amount": random_amount(),
        "narration": random.choice(narrations_good), "is_fraud": 0, "fraud_type": ""
    })
    voucher_counter += 1

# ---- Normal vendor transactions (genuine purchase/payment activity, 540) ----
# A real recurring vendor relationship has a fairly STEADY monthly spend
# (a retainer, a standing supply contract) - not wildly random month to
# month. So each vendor is given its own typical monthly spend anchor, and
# 3 transactions/month drawn tightly around that anchor (+/-20% noise).
# This is what makes a rolling-window anomaly check (Rule 11) meaningful:
# without a believable "normal" to compare against, no anomaly test -
# ours or a real auditor's - can tell a genuine spike from ordinary noise.
for vendor in vendor_accounts:
    typical_monthly_total = random.uniform(40000, 90000)
    for month in range(1, 13):
        per_tx = typical_monthly_total / 3
        for _ in range(3):
            user = random.choice(users)
            day = random.randint(1, 28)
            dt = datetime(2025, month, day)
            while dt.weekday() in [4, 5]:
                day = random.randint(1, 28)
                dt = datetime(2025, month, day)
            dt = dt.replace(hour=random.randint(9, 18), minute=random.randint(0, 59))
            amt = round(per_tx * random.uniform(0.8, 1.2), 2)
            if random.random() < 0.5:
                debit_acc, credit_acc = random.choice(purchase_side_accounts), vendor
                narration = "Purchase of goods from supplier as per PO"
            else:
                debit_acc, credit_acc = vendor, random.choice(payment_side_accounts)
                narration = random.choice(narrations_good)
            vouchers.append({
                "voucher_id": f"V{voucher_counter:06d}", "date": dt.strftime("%Y-%m-%d"),
                "time": dt.strftime("%H:%M"), "day_of_week": dt.strftime("%A"),
                "created_by": user["user_id"], "created_by_name": user["name"],
                "altered_by": "", "altered_date": "",
                "debit_account": debit_acc, "credit_account": credit_acc, "amount": amt,
                "narration": narration, "is_fraud": 0, "fraud_type": ""
            })
            voucher_counter += 1

# ---- Fraud 1: Weekend / after-hours postings (60) ----
for i in range(60):
    user = random.choice(users)
    dt = random_date_in_year(after_hours=True)
    if random.random() < 0.5:
        while dt.weekday() not in [4, 5]:
            dt = random_date_in_year(after_hours=True)
    debit_acc = random.choice(non_vendor_normal_accounts)
    credit_acc = random.choice([a for a in non_vendor_normal_accounts if a != debit_acc])
    vouchers.append({
        "voucher_id": f"V{voucher_counter:06d}", "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M"), "day_of_week": dt.strftime("%A"),
        "created_by": user["user_id"], "created_by_name": user["name"],
        "altered_by": "", "altered_date": "",
        "debit_account": debit_acc, "credit_account": credit_acc, "amount": random_amount(),
        "narration": random.choice(narrations_good), "is_fraud": 1,
        "fraud_type": "Weekend/After-hours posting"
    })
    voucher_counter += 1

# ---- Fraud 2: Backdated entries after year-end close (25) ----
for i in range(25):
    user = random.choice(users)
    fake_date = datetime(2025, 12, random.randint(20, 31))
    vouchers.append({
        "voucher_id": f"V{voucher_counter:06d}", "date": fake_date.strftime("%Y-%m-%d"),
        "time": "22:15", "day_of_week": fake_date.strftime("%A"),
        "created_by": user["user_id"], "created_by_name": user["name"],
        "altered_by": user["user_id"], "altered_date": "2026-01-15",
        "debit_account": "Suspense Account", "credit_account": random.choice(non_vendor_normal_accounts),
        "amount": random_amount(), "narration": random.choice(narrations_vague),
        "is_fraud": 1, "fraud_type": "Backdated post year-end close"
    })
    voucher_counter += 1

# ---- Fraud 3: Amounts just under approval limit of 25,000 (40) ----
for i in range(40):
    user = random.choice(users)
    dt = random_date_in_year(exclude_weekend=True)
    amt = round(random.uniform(24000, 24999), 2)
    vouchers.append({
        "voucher_id": f"V{voucher_counter:06d}", "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M"), "day_of_week": dt.strftime("%A"),
        "created_by": user["user_id"], "created_by_name": user["name"],
        "altered_by": "", "altered_date": "",
        "debit_account": random.choice(non_vendor_normal_accounts), "credit_account": random.choice(vendor_accounts),
        "amount": amt, "narration": random.choice(narrations_good),
        "is_fraud": 1, "fraud_type": "Amount just under approval limit"
    })
    voucher_counter += 1

# ---- Fraud 4: Round amounts to suspense/misc accounts (35) ----
for i in range(35):
    user = random.choice(users)
    dt = random_date_in_year(exclude_weekend=True)
    vouchers.append({
        "voucher_id": f"V{voucher_counter:06d}", "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M"), "day_of_week": dt.strftime("%A"),
        "created_by": user["user_id"], "created_by_name": user["name"],
        "altered_by": "", "altered_date": "",
        "debit_account": random.choice(["Suspense Account", "Miscellaneous Expense"]),
        "credit_account": "Bank - ADCB Current", "amount": random_amount(round_amt=True),
        "narration": random.choice(narrations_vague), "is_fraud": 1,
        "fraud_type": "Round amount to suspense/misc account"
    })
    voucher_counter += 1

# ---- Fraud 5: Same user creates AND alters their own entry (30) ----
for i in range(30):
    user = random.choice(users)
    dt = random_date_in_year(exclude_weekend=True)
    vouchers.append({
        "voucher_id": f"V{voucher_counter:06d}", "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M"), "day_of_week": dt.strftime("%A"),
        "created_by": user["user_id"], "created_by_name": user["name"],
        "altered_by": user["user_id"], "altered_date": dt.strftime("%Y-%m-%d"),
        "debit_account": random.choice(non_vendor_normal_accounts), "credit_account": random.choice(non_vendor_normal_accounts),
        "amount": random_amount(5000, 40000), "narration": random.choice(narrations_good),
        "is_fraud": 1, "fraud_type": "Same user created and altered entry"
    })
    voucher_counter += 1

# ---- Fraud 6: Duplicate invoices with slightly changed amounts (20 pairs = 40) ----
for i in range(20):
    user = random.choice(users)
    dt = random_date_in_year(exclude_weekend=True)
    base_amt = random_amount(5000, 30000)
    dup_vendor = random.choice(vendor_accounts)
    for dup in range(2):
        dt2 = dt + timedelta(days=random.randint(0, 3))
        vouchers.append({
            "voucher_id": f"V{voucher_counter:06d}", "date": dt2.strftime("%Y-%m-%d"),
            "time": dt2.strftime("%H:%M"), "day_of_week": dt2.strftime("%A"),
            "created_by": user["user_id"], "created_by_name": user["name"],
            "altered_by": "", "altered_date": "",
            "debit_account": "Purchase - Import", "credit_account": dup_vendor,
            "amount": round(base_amt + random.uniform(-5, 5), 2),
            "narration": "Purchase of goods from supplier as per PO",
            "is_fraud": 1, "fraud_type": "Duplicate invoice, slightly changed amount"
        })
        voucher_counter += 1

# ---- Fraud 7: Vendor bank-detail change before large payment (15) ----
for i in range(15):
    user = random.choice(users)
    dt = random_date_in_year(exclude_weekend=True)
    vouchers.append({
        "voucher_id": f"V{voucher_counter:06d}", "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M"), "day_of_week": dt.strftime("%A"),
        "created_by": user["user_id"], "created_by_name": user["name"],
        "altered_by": "", "altered_date": "",
        "debit_account": random.choice(vendor_accounts), "credit_account": "Bank - ENBD Current",
        "amount": random_amount(40000, 50000), "narration": "Vendor bank details updated - urgent payment",
        "is_fraud": 1, "fraud_type": "Vendor bank-detail change before large payment"
    })
    voucher_counter += 1

# ---- Fraud 8: Old vouchers edited long after the review period (20) ----
for i in range(20):
    user = random.choice(users)
    dt = random_date_in_year(exclude_weekend=True)
    alter_dt = dt + timedelta(days=random.randint(60, 150))
    vouchers.append({
        "voucher_id": f"V{voucher_counter:06d}", "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M"), "day_of_week": dt.strftime("%A"),
        "created_by": user["user_id"], "created_by_name": user["name"],
        "altered_by": random.choice(users)["user_id"], "altered_date": alter_dt.strftime("%Y-%m-%d"),
        "debit_account": random.choice(non_vendor_normal_accounts), "credit_account": random.choice(non_vendor_normal_accounts),
        "amount": random_amount(), "narration": random.choice(narrations_good),
        "is_fraud": 1, "fraud_type": "Old voucher edited after review period"
    })
    voucher_counter += 1

# ---- Normal seed activity on the shell vendor (3) ----
# A few genuinely innocuous, SMALL, early-year payments - just enough that
# the ledger isn't a brand-new, never-used account (which the existing
# "rare account pair" rule would flag on sight, for the trivial reason
# that it's barely used at all, rather than for detecting the structuring
# pattern itself) - but deliberately modest in size, so the vendor's early
# baseline rate genuinely reflects "a small, quiet vendor" rather than
# something already close to the later structuring volume.
for i in range(3):
    user = random.choice(users)
    dt = random_date_in_year(exclude_weekend=True)
    dt = datetime(2025, random.randint(1, 2), dt.day) if dt.day <= 28 else datetime(2025, random.randint(1, 2), 28)
    while dt.weekday() in [4, 5]:
        dt = dt + timedelta(days=1)
    dt = dt.replace(hour=random.randint(9, 18), minute=random.randint(0, 59))
    vouchers.append({
        "voucher_id": f"V{voucher_counter:06d}", "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M"), "day_of_week": dt.strftime("%A"),
        "created_by": user["user_id"], "created_by_name": user["name"],
        "altered_by": "", "altered_date": "",
        "debit_account": shell_vendor_account, "credit_account": "Bank - ADCB Current",
        "amount": round(random.uniform(1500, 3000), 2), "narration": random.choice(narrations_good),
        "is_fraud": 0, "fraud_type": ""
    })
    voucher_counter += 1

# ---- Fraud 9: Structured disbursement to a single vendor (13) ----
# A seasoned insider siphons funds to ONE vendor via many small, individually
# unremarkable payments spread across the year - no single entry is round,
# near the approval limit, after-hours, weekend, or altered; different users
# create different entries so it never looks like one person's pattern. Only
# the AGGREGATE - the cumulative total paid to this one vendor - reveals it.
# This is exactly the scenario proven (and proven undetectable by rules 1-10)
# in the Rule11_Structuring_Prototype test, now built into the official
# dataset with a real vendor ledger instead of a fake name guessed from text.
structuring_vendor = shell_vendor_account  # the quiet, 16th shell vendor - no other activity touches it
# Starts in May - safely AFTER the quiet Jan/Feb seed period (and after
# Rule 11's 60-day early-baseline window, which only sees the seeds) - so
# there is a genuine, uncontaminated "before" baseline to detect a
# ramp-up against. Irregular spacing, stays well clear of year-end.
structuring_months = [5, 5, 6, 6, 7, 8, 8, 9, 10, 10, 11, 11, 11]
structuring_users_pool = [u for u in users if u["user_id"] != "U004"]  # rotate everyone except the Owner/Director
for i in range(13):
    user = structuring_users_pool[i % len(structuring_users_pool)]
    month = structuring_months[i]
    day = random.randint(1, 26)
    dt = datetime(2025, month, day)
    while dt.weekday() in [4, 5]:
        day = random.randint(1, 26)
        dt = datetime(2025, month, day)
    dt = dt.replace(hour=random.randint(9, 17), minute=random.randint(0, 59))
    amt = round(random.uniform(9000, 19500), 2)
    vouchers.append({
        "voucher_id": f"V{voucher_counter:06d}", "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M"), "day_of_week": dt.strftime("%A"),
        "created_by": user["user_id"], "created_by_name": user["name"],
        "altered_by": "", "altered_date": "",
        "debit_account": structuring_vendor, "credit_account": "Bank - ADCB Current",
        "amount": amt, "narration": random.choice(narrations_good),
        "is_fraud": 1, "fraud_type": "Structured disbursement to a single vendor"
    })
    voucher_counter += 1

df = pd.DataFrame(vouchers)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # shuffle so fraud isn't clustered

# File 1: the clean Day Book export (NO fraud labels - this is the "input" data)
daybook_export = df[[
    "voucher_id", "date", "time", "day_of_week", "created_by", "created_by_name",
    "altered_by", "altered_date", "debit_account", "credit_account", "amount", "narration"
]].copy()

# File 2: the hidden answer key (use ONLY to score the detector afterward)
answer_key = df[["voucher_id", "is_fraud", "fraud_type"]].copy()


def write_formatted_xlsx(dataframe, path, sheet_name, header_fill_hex):
    dataframe.to_excel(path, index=False, sheet_name=sheet_name, engine="openpyxl")
    wb = load_workbook(path)
    ws = wb[sheet_name]

    header_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    body_font = Font(name="Arial", size=10)
    header_fill = PatternFill(start_color=header_fill_hex, end_color=header_fill_hex, fill_type="solid")

    for col_idx, col_name in enumerate(dataframe.columns, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ws.max_column):
        for cell in row:
            cell.font = body_font

    # Auto-fit column widths (approximate)
    for col_idx, col_name in enumerate(dataframe.columns, start=1):
        max_len = max(
            [len(str(col_name))] + [len(str(v)) for v in dataframe[col_name].astype(str).values[:2000]]
        )
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 3, 40)

    ws.freeze_panes = "A2"
    wb.save(path)


write_formatted_xlsx(daybook_export, "tally_daybook_export.xlsx", "Day Book", "1F4E78")
write_formatted_xlsx(answer_key, "fraud_answer_key.xlsx", "Answer Key", "C00000")

print(f"Total vouchers: {len(df)}")
print(f"Fraud planted: {df['is_fraud'].sum()}")
print(f"Normal vouchers: {(df['is_fraud']==0).sum()}")
print("\nFiles saved: tally_daybook_export.xlsx, fraud_answer_key.xlsx")
print("\nFraud type breakdown:")
print(df[df['is_fraud'] == 1]['fraud_type'].value_counts().to_string())
