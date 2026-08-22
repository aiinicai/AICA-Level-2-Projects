"""
tax_engine.py
Core computation logic for the Salary TDS Calculator & Advisor.

Section references used throughout (Income Tax Act, 2025 — effective 1 Apr 2026,
applicable from Tax Year 2026-27 onwards):

    Provision                              1961 Act        2025 Act
    ------------------------------------------------------------------
    TDS on salary                          Sec 192         Sec 392
    Standard deduction                     Sec 16(ia)      Sec 19
    HRA exemption                          Sec 10(13A)     Sec 11 r/w Sec 19 & Sch. II
    Home loan interest (self-occupied)     Sec 24(b)       Sec 22(2)
    80C investments (PPF/ELSS/LIC/etc.)    Sec 80C         Sec 123 r/w Schedule XV
    NPS additional deduction               Sec 80CCD(1B)   Sec 124
    Health insurance premium               Sec 80D         Sec 126
    Default new regime                     Sec 115BAC      Sec 202
    Rebate (nil tax up to certain income)  Sec 87A         Sec 156

NOTE FOR THE CA REVIEWING THIS CODE:
Slabs, caps and thresholds below are as commonly reported for Tax Year 2026-27.
Please cross-check against the Gazette text / CBDT notifications before relying
on this for actual client advice — this app is built for an AICA Level 2
capstone demo, not as a certified compliance tool.
"""

from dataclasses import dataclass, field


CESS_RATE = 0.04  # Health & education cess, both regimes

METRO_CITIES = {
    "Delhi", "Mumbai", "Chennai", "Kolkata",
    "Bengaluru", "Hyderabad", "Pune", "Ahmedabad",
}


@dataclass
class SalaryInput:
    name: str
    age_band: str  # "Below 60" | "60-80" | "Above 80"
    basic_salary: float
    hra_received: float
    special_allowance: float
    bonus: float
    other_income: float
    rent_paid: float
    city: str
    invest_123: float       # Sec 123 (old Sec 80C) - cap 150000
    nps_124: float           # Sec 124 (old Sec 80CCD(1B)) - cap 50000
    health_126: float        # Sec 126 (old Sec 80D)
    home_loan_interest_22: float  # Sec 22(2) (old Sec 24b) - cap 200000, old regime only


@dataclass
class RegimeResult:
    regime: str
    gross_salary: float
    exemptions: float
    standard_deduction: float
    chapter_via_deductions: float
    taxable_income: float
    tax_before_cess: float
    rebate: float
    tax_after_rebate: float
    cess: float
    total_tax: float
    monthly_tds: float
    breakup: dict = field(default_factory=dict)


def compute_hra_exemption(basic_salary, hra_received, rent_paid, city):
    """Sec 11 r/w Sec 19 & Schedule II (old Sec 10(13A)). Old regime only."""
    if hra_received <= 0 or rent_paid <= 0:
        return 0.0
    pct = 0.50 if city in METRO_CITIES else 0.40
    least_of = [
        hra_received,
        max(0.0, rent_paid - 0.10 * basic_salary),
        pct * basic_salary,
    ]
    return max(0.0, min(least_of))


def _slab_tax_new_regime(taxable_income: float) -> float:
    """Sec 202 (old Sec 115BAC) slabs, Tax Year 2026-27."""
    slabs = [
        (400000, 0.00),
        (400000, 0.05),
        (400000, 0.10),
        (400000, 0.15),
        (400000, 0.20),
        (400000, 0.25),
        (float("inf"), 0.30),
    ]
    remaining = taxable_income
    tax = 0.0
    for width, rate in slabs:
        if remaining <= 0:
            break
        chunk = min(width, remaining)
        tax += chunk * rate
        remaining -= chunk
    return tax


def _slab_tax_old_regime(taxable_income: float, age_band: str) -> float:
    """Old regime slabs, varying basic exemption by age."""
    if age_band == "Above 80":
        exempt = 500000
    elif age_band == "60-80":
        exempt = 300000
    else:
        exempt = 250000

    if taxable_income <= exempt:
        return 0.0

    slabs = [
        (exempt, 0.00),
        (max(0, 500000 - exempt), 0.05),
        (500000, 0.20),
        (float("inf"), 0.30),
    ]
    remaining = taxable_income
    tax = 0.0
    for width, rate in slabs:
        if remaining <= 0:
            break
        chunk = min(width, remaining)
        tax += chunk * rate
        remaining -= chunk
    return tax


def compute_new_regime(inp: SalaryInput) -> RegimeResult:
    gross_salary = inp.basic_salary + inp.hra_received + inp.special_allowance + inp.bonus
    std_deduction = 75000.0
    taxable_income = max(0.0, gross_salary + inp.other_income - std_deduction)

    tax_before_cess = _slab_tax_new_regime(taxable_income)

    # Sec 156 rebate: nil tax if taxable income <= 12,00,000, with marginal relief just above.
    # Marginal relief: tax payable is capped at (taxable_income - 12,00,000) if that is
    # lower than the slab tax, so a rupee of extra income never costs more than a rupee of tax.
    rebate = 0.0
    if taxable_income <= 1200000:
        rebate = tax_before_cess
    else:
        excess_income = taxable_income - 1200000
        if excess_income < tax_before_cess:
            rebate = tax_before_cess - excess_income

    tax_after_rebate = max(0.0, tax_before_cess - rebate)
    cess = tax_after_rebate * CESS_RATE
    total_tax = tax_after_rebate + cess

    return RegimeResult(
        regime="New Regime (Sec 202)",
        gross_salary=gross_salary,
        exemptions=0.0,
        standard_deduction=std_deduction,
        chapter_via_deductions=0.0,
        taxable_income=taxable_income,
        tax_before_cess=tax_before_cess,
        rebate=rebate,
        tax_after_rebate=tax_after_rebate,
        cess=cess,
        total_tax=total_tax,
        monthly_tds=total_tax / 12,
        breakup={
            "Basic": inp.basic_salary,
            "HRA": inp.hra_received,
            "Special Allowance": inp.special_allowance,
            "Bonus": inp.bonus,
        },
    )


def compute_old_regime(inp: SalaryInput) -> RegimeResult:
    gross_salary = inp.basic_salary + inp.hra_received + inp.special_allowance + inp.bonus
    hra_exempt = compute_hra_exemption(inp.basic_salary, inp.hra_received, inp.rent_paid, inp.city)
    std_deduction = 50000.0

    ch_via_123 = min(inp.invest_123, 150000.0)
    ch_via_124 = min(inp.nps_124, 50000.0)
    ch_via_126 = inp.health_126
    home_loan_22 = min(inp.home_loan_interest_22, 200000.0)
    chapter_via_total = ch_via_123 + ch_via_124 + ch_via_126

    taxable_income = max(
        0.0,
        gross_salary + inp.other_income - hra_exempt - std_deduction
        - chapter_via_total - home_loan_22,
    )

    tax_before_cess = _slab_tax_old_regime(taxable_income, inp.age_band)

    # Sec 156 rebate (old regime): nil tax if taxable income <= 5,00,000, cap 12,500
    rebate = 0.0
    if taxable_income <= 500000:
        rebate = min(tax_before_cess, 12500.0)

    tax_after_rebate = max(0.0, tax_before_cess - rebate)
    cess = tax_after_rebate * CESS_RATE
    total_tax = tax_after_rebate + cess

    return RegimeResult(
        regime="Old Regime",
        gross_salary=gross_salary,
        exemptions=hra_exempt,
        standard_deduction=std_deduction,
        chapter_via_deductions=chapter_via_total + home_loan_22,
        taxable_income=taxable_income,
        tax_before_cess=tax_before_cess,
        rebate=rebate,
        tax_after_rebate=tax_after_rebate,
        cess=cess,
        total_tax=total_tax,
        monthly_tds=total_tax / 12,
        breakup={
            "Basic": inp.basic_salary,
            "HRA": inp.hra_received,
            "Special Allowance": inp.special_allowance,
            "Bonus": inp.bonus,
        },
    )
