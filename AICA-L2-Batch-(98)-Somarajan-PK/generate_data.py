"""Generate SYNTHETIC bank statement + bank books (and a 2-bank Tally-style export) for 'ABC Traders Pvt Ltd' (Oct 2026).

All data is fictional. 19 issues are deliberately planted; answer_key.csv lists them
so the engine's detection accuracy can be measured.
Run:  python generate_data.py
"""
import csv, json, random
from datetime import date, timedelta
from pathlib import Path

random.seed(2026)
OUT = Path("sample_data")
OUT.mkdir(exist_ok=True)

BANK_OPEN, BOOKS_OPEN = 521500.0, 500000.0   # difference = B/F outstanding cheque 21,500
D = lambda d: date(2026, 10, d)
fmt = lambda d: d.strftime("%d-%m-%Y")

PLANTED_CHQ = {"000812", "000896", "000902", "000915", "000921", "000925", "000930",
               "000941", "000943", "000944"}
CUSTOMERS = ["Sharma Retail", "Mehta Distributors", "Iyer Traders", "Gupta Wholesale",
             "Nair Supplies", "Reddy Stores"]
SUPPLIERS = ["Bharat Paper Mills", "Hindustan Packaging", "Fortune Chemicals", "Royal Fasteners"]

books, bank = [], []   # (date, narration, ref, receipt, payment) / (date, narration, ref, withdrawal, deposit)
used_amounts = set()


def uniq_amount(lo, hi):
    while True:
        a = random.randrange(lo, hi) + random.choice([0.0, 0.25, 0.5, 0.75])
        a = float(int(a)) if random.random() < 0.6 else a
        if a % 10000 != 0 and a not in used_amounts:
            used_amounts.add(a)
            return a


def weekday(offset_from=1, last=26):
    while True:
        d = D(random.randint(offset_from, last))
        if d.weekday() < 5:
            return d


def next_weekday(d):
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return min(d, D(30))


# ---- Base (clean, matching) transactions -------------------------------------------
for i in range(12):                                   # receipts
    c, d, amt = random.choice(CUSTOMERS), weekday(), uniq_amount(8000, 90000)
    ref = "UTR" + str(random.randint(10**8, 10**9 - 1))
    inv = f"INV{random.randint(1000, 9999)}"
    blank_ref = i in (2, 6, 9)                         # 3 books entries missing reference -> near match
    books.append((d, f"Receipt from {c} - {inv}", "" if blank_ref else ref, amt, 0))
    bank.append((next_weekday(d + timedelta(days=random.randint(0, 2))), f"NEFT-{c.upper()}-{inv}", ref, 0, amt))

chq = 870
for i in range(14):                                   # cheque payments
    while f"{chq:06d}" in PLANTED_CHQ:
        chq += 1
    s, d, amt = random.choice(SUPPLIERS), weekday(), uniq_amount(3100, 22000)
    ref = f"CHQ{chq:06d}"
    chq += 1
    books.append((d, f"Payment to {s}", ref, 0, amt))
    bank.append((next_weekday(d + timedelta(days=random.randint(1, 4))), f"CHQ CLEARING-{ref}-{s.upper()}", ref, amt, 0))

key = []   # answer key


def issue(code, ref, desc):
    key.append((f"I{len(key) + 1:02d}", code, ref, desc))


# ---- Planted issues ----------------------------------------------------------------
# 1-3 Outstanding cheques (books only)
for d, party, ref, amt in [(D(27), "Zenith Packaging", "CHQ000941", 23450.0),
                           (D(29), "Sunrise Textiles", "CHQ000943", 18720.0),
                           (D(30), "Lakshmi Plastics", "CHQ000944", 31275.0)]:
    books.append((d, f"Payment to {party}", ref, 0, amt))
    issue("OUTSTANDING_CHEQUE", ref, "Cheque issued, not yet presented")

# 4-5 Deposits in transit (books only)
for d, party, ref, amt in [(D(29), "Sharma Retail", "DEP0007781", 38640.0),
                           (D(30), "Iyer Traders", "DEP0007790", 52115.0)]:
    books.append((d, f"Cheque deposit - {party}", ref, amt, 0))
    issue("DEPOSIT_IN_TRANSIT", ref, "Deposit recorded in books, not credited by bank")

# 6-8 Bank-only items
bank.append((D(30), "SMS ALERT CHARGES INCL GST", "BNKCHG01", 590.0, 0))
bank.append((D(27), "CHEQUE BOOK ISSUE CHARGES", "BNKCHG02", 354.0, 0))
bank.append((D(30), "INTEREST CREDITED SB A/C", "BNKINT01", 0, 1284.0))
issue("BANK_CHARGE", "BNKCHG01", "Bank charge not in books")
issue("BANK_CHARGE", "BNKCHG02", "Bank charge not in books")
issue("BANK_INTEREST", "BNKINT01", "Interest credit not in books")

# 9 Duplicate posting in books (same cheque posted twice)
for _ in range(2):
    books.append((D(8), "Payment to Kapoor Logistics", "CHQ000902", 0, 27360.0))
bank.append((D(12), "CHQ CLEARING-CHQ000902-KAPOOR LOGISTICS", "CHQ000902", 27360.0, 0))
issue("DUPLICATE_PAYMENT", "CHQ000902", "Same cheque posted twice in books")

# 10 Transposition error (4,590 in books vs 4,950 at bank)
books.append((D(14), "Payment to Metro Stationers", "CHQ000915", 0, 4590.0))
bank.append((D(16), "CHQ CLEARING-CHQ000915-METRO STATIONERS", "CHQ000915", 4950.0, 0))
issue("TRANSPOSITION", "CHQ000915", "4,590 booked vs 4,950 cleared")

# 11-12 Amounts just below Rs 50,000 approval limit
for d, bd, party, ref, amt in [(D(7), D(9), "Orbit Steel", "CHQ000896", 49500.0),
                               (D(21), D(23), "Delta Chemicals", "CHQ000925", 49800.0)]:
    books.append((d, f"Payment to {party}", ref, 0, amt))
    bank.append((bd, f"CHQ CLEARING-{ref}-{party.upper()}", ref, amt, 0))
    issue("NEAR_LIMIT", ref, "Payment just below Rs 50,000 approval limit")

# 13 Weekend posting (Sunday 18-Oct)
books.append((D(18), "Payment to Vertex Utilities", "CHQ000921", 0, 12830.0))
bank.append((D(19), "CHQ CLEARING-CHQ000921-VERTEX UTILITIES", "CHQ000921", 12830.0, 0))
issue("WEEKEND", "CHQ000921", "Books entry dated Sunday")

# 14 Many-to-one: three books receipts = one bank credit
for d, ref, amt in [(D(6), "REC0004", 51240.0), (D(8), "REC0005", 44860.0), (D(12), "REC0006", 29925.0)]:
    books.append((d, "Receipt from Patel Enterprises", ref, amt, 0))
bank.append((D(13), "NEFT-PATEL ENTERPRISES-CONSOLIDATED SETTLEMENT", "UTR998123400", 0, 126025.0))
issue("MANY_TO_ONE", "UTR998123400", "One bank credit = 3 book receipts")

# 15 Round-sum large payment
books.append((D(22), "Payment to Ganesh Steel Traders (advance)", "CHQ000930", 0, 200000.0))
bank.append((D(23), "CHQ CLEARING-CHQ000930-GANESH STEEL TRADERS", "CHQ000930", 200000.0, 0))
issue("ROUND_SUM", "CHQ000930", "Round-sum payment of Rs 2,00,000")

# 16 Stale cheque brought forward (opening_items.csv)
issue("STALE_CHEQUE", "CHQ000812", "Cheque issued 12-06-2026 still outstanding (>90 days)")

# 17-19 Books entries with missing reference -> must be found via near match (bank refs)
# identify the 3 receipts whose books ref was blanked
blank_books = [b for b in books if b[2] == "" and b[3] > 0]
for bk in blank_books:
    match = [x for x in bank if x[4] == bk[3]][0]
    issue("NEAR_MATCH", match[2], "Books entry has no reference; match via amount+date+narration")


# ---- Write files -------------------------------------------------------------------
def write(name, header, rows, opening, credit_idx, debit_idx):
    rows = sorted(rows, key=lambda r: r[0])
    bal = opening
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            bal += r[credit_idx] - r[debit_idx]
            w.writerow([fmt(r[0]), r[1], r[2],
                        f"{r[3]:.2f}" if r[3] else "", f"{r[4]:.2f}" if r[4] else "", f"{bal:.2f}"])
    return len(rows), bal


nb, bank_close = write("bank_statement.csv", ["Date", "Narration", "Ref_No", "Withdrawal", "Deposit", "Balance"],
                       bank, BANK_OPEN, 4, 3)
nk, books_close = write("bank_books.csv", ["Date", "Narration", "Voucher_Ref", "Receipt", "Payment", "Balance"],
                        books, BOOKS_OPEN, 3, 4)

with open(OUT / "opening_items.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Date", "Narration", "Ref", "Amount"])
    w.writerow(["12-06-2026", "Payment to Annapurna Foods (cheque issued, not presented)", "CHQ000812", "-21500.00"])

# ---- Tally-style multi-bank export (same shape tally_extract.py produces) -----------
import re
BANK_A = "Bank A - Current A/c"
BANK_B = "Bank B - Savings A/c"
safe = lambda n: re.sub(r"[^A-Za-z0-9]+", "_", n).strip("_").lower()


def book_rows(rows, opening):
    out, bal = [], opening
    for r in sorted(rows, key=lambda x: x[0]):
        bal += r[3] - r[4]
        out.append({"Date": fmt(r[0]), "Narration": r[1], "Voucher_Ref": r[2],
                    "Receipt": f"{r[3]:.2f}" if r[3] else "", "Payment": f"{r[4]:.2f}" if r[4] else "",
                    "Balance": f"{bal:.2f}"})
    return out, bal


# Bank B: small second account with 1 outstanding cheque, 1 deposit in transit, 1 bank charge
B_OPEN = 150000.0
b_books = [(D(3), "Receipt from Kumar Agencies", "UTR700100201", 42000.0, 0),
           (D(9), "Payment to Prime Logistics", "CHQ550101", 0, 16500.0),
           (D(15), "Receipt from Das Brothers", "UTR700100377", 28750.0, 0),
           (D(20), "Payment to Spark Electricals", "CHQ550102", 0, 9300.0),
           (D(28), "Payment to Lotus Packaging", "CHQ550103", 0, 12480.0),
           (D(30), "Cheque deposit - Kumar Agencies", "DEP0004410", 19900.0, 0)]
b_bank = [(D(3), "NEFT-KUMAR AGENCIES", "UTR700100201", 0, 42000.0),
          (D(12), "CHQ CLEARING-CHQ550101-PRIME LOGISTICS", "CHQ550101", 16500.0, 0),
          (D(15), "NEFT-DAS BROTHERS", "UTR700100377", 0, 28750.0),
          (D(22), "CHQ CLEARING-CHQ550102-SPARK ELECTRICALS", "CHQ550102", 9300.0, 0),
          (D(30), "SERVICE CHARGES INCL GST", "BNKCHG21", 177.0, 0)]

(OUT / "banks" / safe(BANK_A)).mkdir(parents=True, exist_ok=True)
(OUT / "banks" / safe(BANK_B)).mkdir(parents=True, exist_ok=True)
import shutil
shutil.copy(OUT / "bank_statement.csv", OUT / "banks" / safe(BANK_A) / "bank_statement.csv")
shutil.copy(OUT / "opening_items.csv", OUT / "banks" / safe(BANK_A) / "opening_items.csv")
_bal = B_OPEN
with open(OUT / "banks" / safe(BANK_B) / "bank_statement.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Date", "Narration", "Ref_No", "Withdrawal", "Deposit", "Balance"])
    for r in sorted(b_bank, key=lambda x: x[0]):
        _bal += r[4] - r[3]
        w.writerow([fmt(r[0]), r[1], r[2], f"{r[3]:.2f}" if r[3] else "", f"{r[4]:.2f}" if r[4] else "", f"{_bal:.2f}"])
with open(OUT / "banks" / safe(BANK_B) / "opening_items.csv", "w", newline="", encoding="utf-8") as f:
    csv.writer(f).writerow(["Date", "Narration", "Ref", "Amount"])

a_rows, a_close = book_rows(books, BOOKS_OPEN)
b_rows, b_close = book_rows(b_books, B_OPEN)
json.dump({"company": "ABC Traders Pvt Ltd (fictional)", "source": "SYNTHETIC sample in Tally-export shape",
           "group": "Bank Accounts", "period_from": "01-10-2026", "period_to": "31-10-2026",
           "banks": [{"name": BANK_A, "parent": "Bank Accounts", "opening_balance": BOOKS_OPEN,
                      "closing_balance": round(a_close, 2), "rows": a_rows},
                     {"name": BANK_B, "parent": "Bank Accounts", "opening_balance": B_OPEN,
                      "closing_balance": round(b_close, 2), "rows": b_rows}]},
          open(OUT / "tally_bank_books.json", "w", encoding="utf-8"), indent=1)

json.dump({"entity": "ABC Traders Pvt Ltd (fictional)", "period": "October 2026", "bank_opening": BANK_OPEN,
           "books_opening": BOOKS_OPEN, "period_end": "31-10-2026", "approval_limit": 50000,
           "stale_days": 90, "date_tolerance": 3, "answer_key_bank": BANK_A},
          open(OUT / "config.json", "w"), indent=2)

with open(OUT / "answer_key.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["issue_id", "code", "ref", "description"])
    w.writerows(key)

print(f"Bank rows: {nb}, closing {bank_close:,.2f} | Books rows: {nk}, closing {books_close:,.2f}")
print(f"Planted issues: {len(key)}")
