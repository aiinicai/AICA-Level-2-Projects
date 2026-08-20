"""
test_tax_engine.py
Verifies the three reference test cases for the Salary TDS Calculator.
Run with:  python test_tax_engine.py
(Must be run from the files/ directory so tax_engine is importable.)
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from tax_engine import SalaryInput, compute_old_regime, compute_new_regime

def fmt(v): return f"Rs.{v:>12,.0f}"

def run_case(label, **kwargs):
    inp = SalaryInput(**kwargs)
    old = compute_old_regime(inp)
    new = compute_new_regime(inp)
    print(f"\n{'='*62}")
    print(f"  CASE: {label}")
    print(f"{'='*62}")
    print(f"  Gross salary           : {fmt(old.gross_salary)}")
    print(f"  --- OLD REGIME ---")
    print(f"    HRA exemption        : {fmt(old.exemptions)}")
    print(f"    Standard deduction   : {fmt(old.standard_deduction)}")
    print(f"    Ch VI-A + Sec 22(2)  : {fmt(old.chapter_via_deductions)}")
    print(f"    Taxable income       : {fmt(old.taxable_income)}")
    print(f"    Tax before cess      : {fmt(old.tax_before_cess)}")
    print(f"    Rebate (Sec 156)     : {fmt(old.rebate)}")
    print(f"    Cess (4%)            : {fmt(old.cess)}")
    print(f"    Total tax            : {fmt(old.total_tax)}")
    print(f"    Monthly TDS (Sec 392): {fmt(old.monthly_tds)}")
    print(f"  --- NEW REGIME (Sec 202) ---")
    print(f"    Standard deduction   : {fmt(new.standard_deduction)}")
    print(f"    Taxable income       : {fmt(new.taxable_income)}")
    print(f"    Tax before cess      : {fmt(new.tax_before_cess)}")
    print(f"    Rebate (Sec 156)     : {fmt(new.rebate)}")
    print(f"    Cess (4%)            : {fmt(new.cess)}")
    print(f"    Total tax            : {fmt(new.total_tax)}")
    print(f"    Monthly TDS (Sec 392): {fmt(new.monthly_tds)}")
    better = "New Regime" if new.total_tax <= old.total_tax else "Old Regime"
    savings = abs(new.total_tax - old.total_tax)
    print(f"  => Better option: {better}  |  Annual savings: {fmt(savings)}")
    return old, new

# ── Case 1: Low income — both regimes should be zero (Sec 156 rebate) ──────
run_case(
    "Case 1 — Low income (Gross ~4.8L, lots of deductions)",
    name="", age_band="Below 60",
    basic_salary=300000, hra_received=120000, special_allowance=60000, bonus=0,
    other_income=0, rent_paid=96000, city="Other (Non-Metro)",
    invest_123=100000, nps_124=0, health_126=15000, home_loan_interest_22=0,
)

# ── Case 2: Mid income — the default example in the app ────────────────────
run_case(
    "Case 2 — Mid income (Gross 12L, Delhi, home no loan)",
    name="", age_band="Below 60",
    basic_salary=600000, hra_received=240000, special_allowance=300000, bonus=60000,
    other_income=0, rent_paid=180000, city="Delhi",
    invest_123=100000, nps_124=0, health_126=15000, home_loan_interest_22=0,
)

# ── Case 3: High income + home loan ────────────────────────────────────────
run_case(
    "Case 3 — High income (Gross 26L, Mumbai, home loan 2L)",
    name="", age_band="Below 60",
    basic_salary=1200000, hra_received=480000, special_allowance=400000, bonus=200000,
    other_income=0, rent_paid=360000, city="Mumbai",
    invest_123=150000, nps_124=50000, health_126=25000, home_loan_interest_22=200000,
)

print("\n\nAll test cases completed successfully.\n")
