"""
Self-test for app.py using the dummy files in ../sample_data.
Run from the project folder:   python tests/self_test.py
"""

import os
import sys

import pandas as pd

try:  # Windows consoles default to cp1252, which cannot print the rupee sign
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "sample_data"))

import app  # noqa: E402
import make_samples  # noqa: E402

PASS, FAIL = [], []


def check(label, cond):
    (PASS if cond else FAIL).append(label)
    print(("PASS  " if cond else "FAIL  ") + label)


# ---------------------------------------------------------------- ledger mapping
expect = {
    "taxable": ["Purchase IGST 18%", "Purchases IGST", "IGST Purchases", "IGST puurchases",
                "Purchase - Interstate (IGST)", "Labour Charges IGST", "Job Work IGST 18%",
                "Pur IGST 28%", "Purchase 18%", "Purchase Local CGST SGST"],
    "igst": ["Input IGST", "IGST Input", "Input IGST 18%", "IGST @18%", "IGST",
             "Input IGST on Purchases", "IGST RCM Payable"],
    "cgst": ["Input CGST 9% Local", "CGST Input 2.5%"],
    "sgst": ["Input SGST"],
    "tds": ["TDS on Labour Charges 194C"],
    "other": ["Round Off"],
}
for bucket, names in expect.items():
    for n in names:
        got = app.classify_ledger(n)
        check(f"ledger '{n}' -> {bucket} (got {got})", got == bucket)

# ---------------------------------------------------------------- helpers
check("to_number('100.00 Cr') = -100", app.to_number("100.00 Cr") == -100)
check("to_number('1,000 Dr') = 1000", app.to_number("1,000 Dr") == 1000)
check("to_number('(1,000)') = -1000", app.to_number("(1,000)") == -1000)
check("to_number('₹ 2,500.50') = 2500.5", app.to_number("₹ 2,500.50") == 2500.5)
check("to_number('Steel rods') is NaN", pd.isna(app.to_number("Steel rods")))
check("parse_date('2026-10-03') = 3-Oct-2026",
      app.parse_date("2026-10-03") == pd.Timestamp(2026, 10, 3))
check("parse_date('03-10-2026') = 3-Oct-2026",
      app.parse_date("03-10-2026") == pd.Timestamp(2026, 10, 3))
check("parse_date(46298) Excel serial = 3-Oct-2026",
      app.parse_date(46298) == pd.Timestamp(2026, 10, 3))
check("to_str(123.0) = '123'", app.to_str(123.0) == "123")
check("normalise 'inv-0005' == 'INV/5'",
      app.clean_invoice_number("inv-0005") == app.clean_invoice_number("INV/5"))
check("normalise 'INV/001' == 'INV/1'",
      app.clean_invoice_number("INV/001") == app.clean_invoice_number("INV/1"))

# ---------------------------------------------------------------- full pipeline
sd = os.path.join(ROOT, "sample_data")
make_samples.make_tally(os.path.join(sd, "Sample_Tally_Purchase_Register.xlsx"))
make_samples.make_2b(os.path.join(sd, "Sample_GSTR2B.xlsx"))
t_bytes = open(os.path.join(sd, "Sample_Tally_Purchase_Register.xlsx"), "rb").read()
g_bytes = open(os.path.join(sd, "Sample_GSTR2B.xlsx"), "rb").read()

tol = 1.0
clean, info = app.standardize_tally(app.read_sheet(t_bytes, 0), tol)
cols = list(clean.columns)
check(f"header row found on row 5 (got {info['header_row']})", info["header_row"] == 5)
check("10 vouchers kept, title + Grand Total removed",
      len(clean) == 10 and not clean["Particulars"].str.contains("Total").any())
check("Supplier Invoice No. right after Voucher No.",
      cols.index("Supplier Invoice No.") == cols.index("Voucher No.") + 1)
check("Narration kept as text column", "Narration" in cols)

a1 = clean[clean["Supplier Invoice No."] == "INV/001"].iloc[0]
check("Alpha: Taxable 16800, IGST 3024, Diff 0, OK - 18%",
      a1["Taxable"] == 16800 and a1["IGST"] == 3024 and a1["Diff"] == 0
      and a1["GST Rate Check"] == "OK - 18%")
b = clean[clean["Supplier Invoice No."] == "B-77"].iloc[0]
check("Beta: Labour Charges IGST -> Taxable 10000, IGST 1800",
      b["Taxable"] == 10000 and b["IGST"] == 1800)
check("Beta: TDS -100, Books Invoice Value 11800, Diff 0",
      b["TDS"] == -100 and b["Books Invoice Value"] == 11800 and b["Diff"] == 0)
check("Beta: ISO date read as 03-10-2026", b["Date"] == pd.Timestamp(2026, 10, 3))
gm = clean[clean["Supplier Invoice No."] == "inv-0005"].iloc[0]
check(f"Gamma: 16% flagged CHECK ({gm['GST Rate Check']})",
      gm["GST Rate %"] == 16 and gm["GST Rate Check"].startswith("CHECK"))
check("TDS column has no -0.0", not any(str(v) == "-0.0" for v in clean["TDS"]))

valid = clean["GSTIN/UIN"].map(app.is_valid_gstin)
unreg, registered = clean[~valid], clean[valid].reset_index(drop=True)
check("blank + invalid GSTIN -> Unregistered (2 rows)",
      sorted(unreg["Supplier Invoice No."]) == ["C-1", "T-1"])

sheets, idx = app.detect_2b_sheet(g_bytes)
check("B2B sheet auto-selected", sheets[idx] == "B2B")
twob = app.parse_gstr2b(app.read_sheet(g_bytes, sheets[idx]))
check(f"2B: 8 invoices after consolidation (got {len(twob)})", len(twob) == 8)
a2 = twob[twob["2B Invoice No."] == "INV/002"].iloc[0]
check("2B INV/002 split rows consolidated: value 2300, taxable 2000, IGST 300",
      a2["2B Invoice Value"] == 2300 and a2["2B Taxable"] == 2000 and a2["2B IGST"] == 300)
check("2B columns prefixed '2B '", all(c.startswith("2B ") for c in twob.columns))

rec = app.reconcile(registered, twob, tol)
t1, t2, t3, um = rec["t1"], rec["t2"], rec["t3"], rec["unmatched"]
check(f"Tier 1: INV/001, INV/002, B-77 (got {sorted(t1['Supplier Invoice No.'])})",
      sorted(t1["Supplier Invoice No."]) == ["B-77", "INV/001", "INV/002"])
check(f"Tier 2: inv-0005 = INV/5 and one E-10 = E10 (got {sorted(t2['Supplier Invoice No.'])})",
      sorted(t2["Supplier Invoice No."]) == ["E-10", "inv-0005"])
check("Tier 2: all 'Matched' within tolerance", (t2["Value Status"] == "Matched").all())
check("Tier 3: Delta 2 books + 2 2B rows, diff -0.50",
      len(t3) == 4 and set(t3["GSTIN"]) == {make_samples.DELTA}
      and (t3["GSTIN Diff"] == -0.5).all())
ub = um[um["Source"] == "Books"]
ug = um[um["Source"] == "GSTR-2B"]
check("Unmatched books: duplicate E-10 flagged",
      len(ub) == 1 and "Possible duplicate booking" in ub.iloc[0]["Remarks"])
check("Unmatched 2B: Zeta Z-99 'Not booked in Tally'",
      len(ug) == 1 and ug.iloc[0]["Invoice No."] == "Z-99"
      and ug.iloc[0]["Remarks"].startswith("Not booked in Tally"))

summary = app.build_summary(clean, unreg, twob, rec, tol)
wb_bytes = app.build_workbook({
    app.SHEET_SUMMARY: summary, app.SHEET_CLEAN: clean, app.SHEET_T1: t1, app.SHEET_T2: t2,
    app.SHEET_T3: t3, app.SHEET_UNREG: unreg, app.SHEET_UNMATCHED: um, app.SHEET_2B: twob,
})
xl = pd.ExcelFile(pd.io.common.BytesIO(wb_bytes))
check("Excel sheet order correct", xl.sheet_names == [
    "0_Summary", "Cleaned_Purchase_Register", "1_Exact_Matched", "2_Normalized_Exact_Matched",
    "3_GSTIN_Total_Matched", "5_Unregistered_Non_2B", "6_Unmatched_Books_vs_2B",
    "GSTR2B_Cleaned"])
no_helper = all(not str(c).startswith("_")
                for s in xl.sheet_names for c in pd.read_excel(xl, s).columns)
check("No internal '_' columns in Excel", no_helper)
out = os.path.join(ROOT, "sample_data", "Sample_Output_GSTR2B_Reconciliation.xlsx")
with open(out, "wb") as f:
    f.write(wb_bytes)

print(f"\n{len(PASS)} passed, {len(FAIL)} failed  (pandas {pd.__version__})")
sys.exit(1 if FAIL else 0)
