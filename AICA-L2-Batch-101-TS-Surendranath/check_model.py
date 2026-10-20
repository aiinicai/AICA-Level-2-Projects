"""
Independent reconciliation check for YearEnd_Tax_Recompute_Model.xlsx
AICA Level 2 Capstone - CA T S Surendranath (Batch AICA-L2B101, Chennai)

What it does:
  1. Reads the trial balance and the adjustment register from the Excel file.
  2. Recomputes profit before tax, total income, current tax and deferred tax
     in Python, completely independently of the Excel formulas.
  3. Compares Python's answers with the Excel answers and prints MATCH / MISMATCH.
  4. Prints the 10 reconciliation checks from the Checks sheet.

How to run (Windows):
  Easiest: keep this file in the same folder as the Excel model and DOUBLE-CLICK it.
  Or in Command Prompt, in that folder:
      pip install openpyxl
      python check_model.py

Note: open the workbook in Excel and SAVE it once after any change, so the
latest calculated values are stored in the file for Python to read.
"""
import sys
import os
import glob

print("Starting the check... please wait.")


def pause_and_exit(code=0):
    # Keeps the window open when the script is started by double-clicking.
    try:
        input("\nPress Enter to close this window...")
    except EOFError:
        pass
    sys.exit(code)


try:
    from openpyxl import load_workbook
except ImportError:
    print("\nThe 'openpyxl' package is not installed.")
    print("Open Command Prompt and type:   pip install openpyxl")
    print("Then run this script again.")
    pause_and_exit(1)

# Look for the Excel file in the same folder as this script.
HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    FILE = sys.argv[1]
else:
    preferred = os.path.join(HERE, "YearEnd_Tax_Recompute_Model.xlsx")
    candidates = [preferred] if os.path.exists(preferred) else sorted(
        f for f in glob.glob(os.path.join(HERE, "YearEnd*.xlsx")) if not os.path.basename(f).startswith("~$"))
    if not candidates:
        print("\nNo Excel file starting with 'YearEnd' was found in this folder:")
        print("   " + HERE)
        print("Put check_model.py in the SAME folder as the Excel model and run it again.")
        pause_and_exit(1)
    FILE = candidates[0]

print("Reading: " + os.path.basename(FILE))
try:
    wb = load_workbook(FILE, data_only=True)
except PermissionError:
    print("\nThe Excel file could not be opened. Please close it in Excel and run again.")
    pause_and_exit(1)


def rows(ws, first_row, last_col):
    for r in ws.iter_rows(min_row=first_row, max_col=last_col, values_only=True):
        if r[0] in (None, ""):
            continue
        yield r


# ---- Settings ----
st = wb["Settings"]
base, surcharge, cess = st["B7"].value, st["B8"].value, st["B9"].value
rate = base * (1 + surcharge) * (1 + cess)
nature = {}
for r in st.iter_rows(min_row=15, max_row=20, max_col=3, values_only=True):
    nature[r[0]] = {"pct": r[1], "type": r[2]}

# ---- Trial balance ----
tb = {}
for code, name, typ, line, amt, *_ in rows(wb["Trial_Balance"], 5, 8):
    if str(code).startswith("L"):
        tb[code] = {"type": typ, "line": line, "amt": amt or 0}

# ---- Adjustments: apply entries and work out the tax effect ----
adjusted = {c: v["amt"] for c, v in tb.items()}
pbt_change = 0
addback = {}
timing_addback = 0
for row in rows(wb["Adjustments"], 5, 11):
    no, ver, dt, desc, dr, _, cr, _, amount, include, tax_nature = row[:11]
    if include != "Y" or not str(no).startswith("A"):
        continue
    adjusted[dr] += amount
    adjusted[cr] -= amount
    impact = amount * ((tb[cr]["type"].startswith("PL")) - (tb[dr]["type"].startswith("PL")))
    pbt_change += impact
    if impact < 0:
        add = -impact * nature[tax_nature]["pct"]
        if tax_nature != "Book Depreciation":
            addback[tax_nature] = addback.get(tax_nature, 0) + add
        if nature[tax_nature]["type"] == "Timing":
            timing_addback += add


def line_total(name, bal):
    return sum(bal[c] for c, v in tb.items() if v["line"] == name)


pl_net = sum(adjusted[c] for c, v in tb.items() if v["type"].startswith("PL"))
pbt = -pl_net
book_dep = line_total("Depreciation", adjusted)
csr = line_total("CSR expenditure", adjusted)
tax_dep = wb["Tax_Computation"]["C5"].value
total_income = pbt + book_dep + csr + sum(addback.values()) - tax_dep
total_income_r = round(total_income / 10) * 10
current_tax = round(total_income_r * rate / 10) * 10
deferred = round(((tax_dep - book_dep) - timing_addback) * rate)

# ---- Compare with Excel ----
tc = wb["Tax_Computation"]
excel = {
    "Profit before tax": wb["Financial_Statements"]["C17"].value,
    "Total income": tc["C21"].value,
    "Current tax": tc["C30"].value,
    "Deferred tax": tc["C40"].value,
}
python = {"Profit before tax": pbt, "Total income": total_income_r,
          "Current tax": current_tax, "Deferred tax": deferred}

print("=" * 72)
print(" INDEPENDENT PYTHON RECOMPUTATION vs EXCEL MODEL")
print("=" * 72)
print(f"{'Item':<22}{'Python (Rs.)':>16}{'Excel (Rs.)':>16}   Result")
all_ok = True
for k in python:
    e = excel[k]
    ok = e is not None and abs(python[k] - e) < 1
    all_ok &= ok
    e_txt = f"{e:,.0f}" if e is not None else "not saved"
    print(f"{k:<22}{python[k]:>16,.0f}{e_txt:>16}   {'MATCH' if ok else 'MISMATCH'}")

print("\nDisallowances found in the adjustment register:")
for k, v in addback.items():
    print(f"   {k:<36}{v:>14,.0f}")

print("\n" + "=" * 72)
print(" RECONCILIATION CHECKS (from the Checks sheet)")
print("=" * 72)
ck = wb["Checks"]
for r in range(5, 15):
    print(f"{ck.cell(r, 1).value:>3}. {ck.cell(r, 2).value:<62} {ck.cell(r, 4).value}")
print(f"\nOVERALL EXCEL STATUS : {ck['D15'].value}")
print(f"PYTHON CROSS-CHECK   : {'ALL MATCH' if all_ok else 'REVIEW - values differ (save the file in Excel and rerun)'}")
if excel["Profit before tax"] is None:
    print("\nTip: open the Excel file, press Ctrl+S to save it once, close it, and run this again.")
pause_and_exit(0)
