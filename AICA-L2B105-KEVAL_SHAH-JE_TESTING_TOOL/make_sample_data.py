"""
============================================================================
 DEVELOPER SCRIPT - builds the demo data shipped with JE Testing
 (not part of the product and not included in the .exe)
----------------------------------------------------------------------------
 Fictitious company: Sunrise Engineering Pvt Ltd, FY 2025-26, company code 1000

 sample_data/
   INPUT_1_CLEAN DATA/                     clean GL + TB (all checks pass)
   INPUT_2_FLAWED DATA/                    GL + TB that run but show many
                                           data-quality errors and red flags
   INPUT_3_WRONG FILES (tool rejects)/     files that stop with an error message

 Every file is written as Excel (.xlsx) and as CSV (.csv) where it makes sense.
 Run:  python make_sample_data.py
============================================================================
"""

import random
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "sample_data"
CLEAN = OUT / "INPUT_1_CLEAN DATA"
FLAWED = OUT / "INPUT_2_FLAWED DATA"
REJECT = OUT / "INPUT_3_WRONG FILES (tool rejects)"
COMPANY = "Sunrise Engineering Pvt Ltd"

ACCOUNTS = {  # G/L account: (name, opening balance; debit +, credit -)
    "11010000": ("Bank - HDFC Current Account", 45_000_000.0),
    "11020000": ("Cash in Hand", 200_000.0),
    "12010000": ("Trade Receivables", 38_000_000.0),
    "12500000": ("Input GST Receivable", 2_500_000.0),
    "13010000": ("Suspense Account", 0.0),
    "14010000": ("Raw Material Inventory", 22_000_000.0),
    "15010000": ("Plant and Machinery", 120_000_000.0),
    "15090000": ("Accumulated Depreciation - Plant", -30_000_000.0),
    "21010000": ("Trade Payables", -26_000_000.0),
    "21500000": ("Output GST Payable", -3_200_000.0),
    "21600000": ("TDS Payable", -800_000.0),
    "23010000": ("Provision for Expenses", -1_700_000.0),
    "31010000": ("Equity Share Capital", -100_000_000.0),
    "32010000": ("Retained Earnings", -66_000_000.0),
    "40010000": ("Revenue from Sale of Products", 0.0),
    "40020000": ("Other Income", 0.0),
    "50010000": ("Raw Material Consumed", 0.0),
    "60010000": ("Salaries and Wages", 0.0),
    "61010000": ("Power and Fuel", 0.0),
    "62010000": ("Repairs and Maintenance", 0.0),
    "63010000": ("Depreciation Expense", 0.0),
}
HOLIDAYS = {datetime(2025, m, d) for m, d in [(4, 14), (5, 1), (8, 15), (8, 27), (10, 2),
                                              (10, 21), (10, 22), (11, 5), (12, 25)]} | \
           {datetime(2026, m, d) for m, d in [(1, 1), (1, 26), (3, 4)]}
GL_COLUMNS = ["Company Code", "G/L Account", "G/L Account Name",
              "Offsetting Account", "Offsetting Account Name", "Document Number",
              "Document Type", "Posting Date", "Document Date", "Entry Date",
              "Fiscal Year/Period", "Amount in Local Currency", "Local Currency",
              "User Name", "Text"]


def acct_name(acc):
    return ACCOUNTS[acc][0] if acc in ACCOUNTS else ("Unmapped Clearing Account" if acc else "")


class Ledger:
    def __init__(self, seed=2025):
        self.rnd = random.Random(seed)   # nosec B311 - demo data only
        self.rows = []
        self.docno = 1900000000

    def post(self, day, dtype, user, lines, text, entry=None):
        """lines: [(account, amount)], debit +, credit -.  Must balance."""
        if abs(sum(a for _, a in lines)) >= 0.01:
            raise ValueError(f"Demo journal does not balance: {text} {lines}")
        self.docno += 1
        entry = entry or day
        fy_period = f"{day.year if day.month >= 4 else day.year - 1}/" \
                    f"{(day.month - 4) % 12 + 1:03d}"
        for acc, amt in lines:
            # SAP 'offsetting account' (GKONT): the main line on the opposite side
            opposite = [(a, x) for a, x in lines if (x > 0) != (amt > 0)]
            off = max(opposite, key=lambda t: abs(t[1]))[0] if opposite else ""
            self.rows.append({
                "Company Code": "1000", "G/L Account": acc,
                "G/L Account Name": acct_name(acc),
                "Offsetting Account": off, "Offsetting Account Name": acct_name(off),
                "Document Number": str(self.docno), "Document Type": dtype,
                "Posting Date": day, "Document Date": day, "Entry Date": entry,
                "Fiscal Year/Period": fy_period, "Amount in Local Currency": round(amt, 2),
                "Local Currency": "INR", "User Name": user, "Text": text})
        return str(self.docno)

    def workday(self, lo=1, hi=26):
        while True:
            day = datetime(2025, 4, 1) + timedelta(days=self.rnd.randint(0, 364))
            if day.weekday() != 6 and day not in HOLIDAYS and lo <= day.day <= hi:
                return day

    def amt(self, lo, hi):
        a = round(self.rnd.uniform(lo, hi), 2)
        return a + 0.37 if a % 100000 == 0 else a      # never an accidental round sum


def months():
    for i in range(12):
        yield datetime(2025 + (i + 3) // 12, (i + 3) % 12 + 1, 1)


def build_clean():
    L = Ledger()
    r = L.rnd
    # ---------- monthly routine ----------
    prev_tds = 0.0
    for m in months():
        pay = m.replace(day=7)
        while pay.weekday() == 6 or pay in HOLIDAYS:
            pay -= timedelta(days=1)
        gross = L.amt(4_100_000, 4_400_000); tds = round(gross * 0.10, 2)
        L.post(pay, "PR", "30000006", [("60010000", gross), ("11010000", -(gross - tds)),
               ("21600000", -tds)], f"Salary for {m:%b-%Y}")
        if prev_tds:
            d = m.replace(day=10) if m.replace(day=10).weekday() != 6 else m.replace(day=11)
            L.post(d, "KZ", "30000005", [("21600000", prev_tds), ("11010000", -prev_tds)],
                   f"TDS deposit challan {m:%b-%Y}")
        prev_tds = tds
        d = m.replace(day=12) if m.replace(day=12).weekday() != 6 else m.replace(day=13)
        p = L.amt(900_000, 1_300_000)
        L.post(d, "KR", "30000004", [("61010000", p), ("12500000", round(p * .18, 2)),
               ("21010000", -round(p + round(p * .18, 2), 2))], f"MSEDCL power bill {m:%b-%Y}")
        dep = 1_000_000.0 + r.randint(1, 99) * 13.0
        last = (m + pd.offsets.MonthEnd(0)).to_pydatetime()
        L.post(last, "AA", "30000007", [("63010000", dep), ("15090000", -dep)],
               f"Depreciation run {m:%b-%Y}")
    # ---------- day-to-day business ----------
    for _ in range(190):
        kind = r.choice(["sale", "sale", "receipt", "purchase", "purchase",
                         "payment", "consume", "repair"])
        d = L.workday()
        if kind == "sale":
            n = L.amt(300_000, 2_800_000)
            L.post(d, "DR", r.choice(["30000001", "30000002"]),
                   [("12010000", round(n + round(n * .18, 2), 2)), ("40010000", -n),
                    ("21500000", -round(n * .18, 2))], f"Sales invoice SI/{r.randint(1000, 9999)}")
        elif kind == "receipt":
            n = L.amt(400_000, 3_000_000)
            L.post(d, "DZ", "30000002", [("11010000", n), ("12010000", -n)],
                   f"Customer receipt UTR {r.randint(100000, 999999)}")
        elif kind == "purchase":
            n = L.amt(200_000, 2_200_000)
            L.post(d, "KR", r.choice(["30000003", "30000004"]),
                   [("14010000", n), ("12500000", round(n * .18, 2)),
                    ("21010000", -round(n + round(n * .18, 2), 2))], f"Vendor invoice INV-{r.randint(1000, 9999)}")
        elif kind == "payment":
            n = L.amt(300_000, 2_500_000)
            L.post(d, "KZ", "30000005", [("21010000", n), ("11010000", -n)],
                   f"Vendor payment NEFT {r.randint(100000, 999999)}")
        elif kind == "consume":
            n = L.amt(300_000, 1_800_000)
            L.post(d, "WA", "30000007", [("50010000", n), ("14010000", -n)],
                   "Raw material issued to production")
        else:
            n = L.amt(30_000, 250_000)
            L.post(d, "KR", "30000004", [("62010000", n), ("12500000", round(n * .18, 2)),
                   ("21010000", -round(n + round(n * .18, 2), 2))], f"Repair work order WO-{r.randint(100, 999)}")
    L.post(datetime(2026, 3, 30), "SA", "30000005", [("62010000", 345_600.0),
           ("23010000", -345_600.0)], "Provision for audit fees and expenses FY 2025-26")
    L.post(datetime(2026, 3, 20), "SA", "30000005", [("21500000", 2_150_000.0 + 431.0),
           ("12500000", -(2_150_000.0 + 431.0))], "GST set-off for FY 2025-26 (GSTR-3B)")

    # ---------- planted red flags ----------
    L.post(datetime(2026, 3, 31), "SA", "CFO01", [("12010000", 11_800_000.0),
           ("40010000", -10_000_000.0), ("21500000", -1_800_000.0)],
           "Year end topside adjustment as instructed", entry=datetime(2026, 4, 10))
    L.post(datetime(2025, 7, 6), "SA", "ADMIN01", [("13010000", 2_500_000.0),
           ("11010000", -2_500_000.0)], "adjustment")
    L.post(datetime(2025, 8, 15), "SA", "30000002", [("62010000", 750_000.0),
           ("11010000", -750_000.0)], "")
    L.post(datetime(2025, 11, 12), "SA", "30000003", [("61010000", 48_500.0),
           ("23010000", -48_500.0)], "balancing figure plug")
    L.post(datetime(2025, 9, 30), "KR", "30000004", [("15010000", 25_750_000.0),
           ("21010000", -25_750_000.0)], "Capital goods invoice INV-8812 - CNC machine")
    L.post(datetime(2025, 12, 5), "KR", "30000003", [("14010000", 310_000.0 + 0.5),
           ("21010000", -(310_000.0 + 0.5))], "Vendor invoice INV-9901",
           entry=datetime(2026, 1, 20))
    L.post(datetime(2026, 3, 28), "SA", "CFO01", [("23010000", 2_000_000.0),
           ("40020000", -2_000_000.0)], "Provision written back as discussed")
    L.post(datetime(2025, 11, 2), "SA", "30000003", [("13010000", 100_000.0),
           ("11020000", -100_000.0)], "jv")
    gl = pd.DataFrame(L.rows, columns=GL_COLUMNS)
    gl = gl.sort_values(["Posting Date", "Document Number"], kind="stable").reset_index(drop=True)
    return gl, L


def build_tb(gl, missing_from_tb=()):
    mv = gl.groupby("G/L Account")["Amount in Local Currency"].sum()
    rows = []
    for acc, (name, opening) in ACCOUNTS.items():
        rows.append({"G/L Account": acc, "G/L Account Name": name,
                     "Opening Balance": round(opening, 2),
                     "Closing Balance": round(opening + float(mv.get(acc, 0.0)), 2)})
    return pd.DataFrame(rows)


def build_flawed(clean_gl, L):
    """Start from the clean GL and break it in ways an auditor meets in practice."""
    gl = clean_gl.copy().astype({"Amount in Local Currency": object, "Posting Date": object})
    docs = list(dict.fromkeys(gl["Document Number"]))
    by_type = lambda t: [d for d in docs if (gl.loc[gl["Document Number"] == d, "Document Type"] == t).all()]
    sales, purch, pays, rec = by_type("DR"), by_type("KR"), by_type("KZ"), by_type("DZ")
    idx = lambda d: gl.index[gl["Document Number"] == d]

    # E1 amounts typed as text
    gl.at[idx(sales[3])[1], "Amount in Local Currency"] = "1,2O,500"      # letter O
    gl.at[idx(sales[8])[1], "Amount in Local Currency"] = "abc"
    # E2 unbalanced journal (debit line changed by 5,000)
    i = idx(purch[5])[0]; gl.at[i, "Amount in Local Currency"] = float(gl.at[i, "Amount in Local Currency"]) + 5000
    # E3 blank user
    gl.loc[idx(pays[4]), "User Name"] = ""
    # E4 blank posting date
    gl.loc[idx(rec[6]), "Posting Date"] = None
    # E5 impossible date
    gl.loc[idx(rec[9]), "Posting Date"] = "31-02-2026"
    # E6 dates outside FY 2025-26
    gl.loc[idx(pays[7]), "Posting Date"] = datetime(2024, 12, 15)
    gl.loc[idx(sales[12]), "Posting Date"] = datetime(2026, 5, 10)
    # E7 blank G/L account on one line
    gl.at[idx(purch[9])[2], "G/L Account"] = ""
    # E8 exact duplicate lines (a journal exported twice)
    gl = pd.concat([gl, gl.loc[idx(sales[15])]], ignore_index=True)

    # E9 posting to an account that is not in the TB + extra fraud red flags
    F = Ledger(seed=99); F.docno = 1900009000
    F.post(datetime(2025, 10, 31), "SA", "30000005", [("99999999", 640_000.0),
           ("11010000", -640_000.0)], "Transfer to clearing")
    flags = [
        (datetime(2025, 6, 30), "SA", "CFO01", "40010000", "12010000", 5_000_000.0,
         "Revenue reversal - management override"),
        (datetime(2025, 9, 30), "SA", "CFO01", "12010000", "40010000", 7_500_000.0,
         "Quarter end sales booking as instructed"),
        (datetime(2025, 12, 31), "SA", "CFO01", "23010000", "40020000", 3_000_000.0,
         "Provision reversal - do not record in MIS"),
        (datetime(2025, 10, 2), "SA", "ADMIN01", "13010000", "11010000", 1_200_000.0,
         ""),                                                      # Gandhi Jayanti
        (datetime(2026, 1, 25), "SA", "ADMIN01", "62010000", "11020000", 150_000.0,
         "personal use reimbursement"),                            # Sunday
        (datetime(2025, 12, 25), "SA", "30000003", "13010000", "21010000", 900_000.0,
         "misc"),                                                  # Christmas
        (datetime(2026, 3, 29), "SA", "30000005", "62010000", "11010000", 400_000.0,
         "correction"),                                            # Sunday
        (datetime(2026, 2, 27), "SA", "CFO01", "61010000", "23010000", 20_000_000.0,
         "Year end cost accrual override"),
    ]
    for day, dt, user, dr, cr, amt, text in flags:
        F.post(day, dt, user, [(dr, amt), (cr, -amt)], text,
               entry=day + timedelta(days=12) if user == "CFO01" else None)
    gl = pd.concat([gl, pd.DataFrame(F.rows, columns=GL_COLUMNS)], ignore_index=True)
    return gl


def flawed_tb(clean_tb):
    tb = clean_tb.copy()
    # T1 TB does not balance: one closing balance mistyped
    i = tb.index[tb["G/L Account"] == "62010000"][0]
    tb.at[i, "Closing Balance"] = round(tb.at[i, "Closing Balance"] + 25_000, 2)
    # T2 opening balances do not total zero
    j = tb.index[tb["G/L Account"] == "32010000"][0]
    tb.at[j, "Opening Balance"] = tb.at[j, "Opening Balance"] + 100_000
    # T3 account repeated in the TB
    dup = tb.loc[tb["G/L Account"] == "11020000"].copy()
    dup["Opening Balance"] = 0.0; dup["Closing Balance"] = 50_000.0
    return pd.concat([tb, dup], ignore_index=True)


def write(df, folder, stem, csv=True):
    folder.mkdir(parents=True, exist_ok=True)
    x = df.copy()
    for c in ("Posting Date", "Document Date", "Entry Date"):
        if c in x:
            x[c] = x[c].map(lambda v: v.date() if isinstance(v, datetime) else v)
    with pd.ExcelWriter(folder / f"{stem}.xlsx", engine="openpyxl") as w:
        x.to_excel(w, index=False, sheet_name=stem[:31])
        ws = w.book[stem[:31]]
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = min(
                max(len(str(c.value or "")) for c in col[:200]) + 2, 50)
            for c in col[1:]:
                if hasattr(c.value, "year"):
                    c.number_format = "DD-MM-YYYY"
                elif isinstance(c.value, float):
                    c.number_format = "#,##0.00"
        ws.freeze_panes = "A2"
    if csv:
        y = df.copy()
        for c in ("Posting Date", "Document Date", "Entry Date"):
            if c in y:
                y[c] = y[c].map(lambda v: f"{v:%d-%m-%Y}" if isinstance(v, datetime)
                                else ("" if v is None else v))
        y.to_csv(folder / f"{stem}.csv", index=False)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    gl, L = build_clean()
    tb = build_tb(gl)
    write(gl, CLEAN, "Sunrise_GL_FY2025-26")
    write(tb, CLEAN, "Sunrise_TB_FY2025-26")

    write(build_flawed(gl, L), FLAWED, "Sunrise_GL_with_errors")
    write(flawed_tb(tb), FLAWED, "Sunrise_TB_with_errors")

    REJECT.mkdir(parents=True, exist_ok=True)
    write(gl.drop(columns=["Amount in Local Currency"]), REJECT, "GL - Amount column missing")
    write(tb.drop(columns=["Closing Balance"]), REJECT, "TB - Closing Balance column missing")
    write(tb, REJECT, "Wrong file - TB selected as the GL", csv=False)
    (REJECT / "Empty file.csv").write_bytes(b"")
    (REJECT / "Not a spreadsheet.txt").write_text("Journal entry listing - plain text, not Excel.\n")
    (REJECT / "Damaged Excel file.xlsx").write_bytes(b"PK\x03\x04 this is not really a workbook")
    for p in sorted(OUT.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(OUT)}   ({p.stat().st_size / 1024:,.1f} KB)")


if __name__ == "__main__":
    main()
