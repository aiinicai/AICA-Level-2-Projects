"""Kenyan statutory payroll engine: gross-to-net, net-to-gross.

Order of computation (KRA practice after the Tax Laws (Amendment) Act 2024):
  1. Gross cash pay = basic + allowances + overtime + bonus + arrears ... - absence
  2. Taxable non-cash benefits (exempt if total <= threshold), car, housing
  3. NSSF (Tier I / Tier II), SHIF 2.75% (min 300), AHL 1.5% on gross cash pay
  4. Taxable pay = gross + benefits - pension (capped) - SHIF - AHL
                   - mortgage interest (capped) - PRMF (capped) - disability exemption
  5. PAYE = tax on bands - personal relief - insurance relief (not below zero)
  6. Net pay = gross cash - NSSF - SHIF - AHL - PAYE - pension - other deductions
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP


def r2(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@dataclass
class PayInput:
    period: str = ""                       # YYYY-MM
    basic: float = 0.0
    allowances: dict = field(default_factory=dict)   # name -> amount (cash, taxable)
    non_cash_benefits: float = 0.0
    car_benefit: float = 0.0
    housing_benefit: float = 0.0
    ot_normal_hours: float = 0.0
    ot_holiday_hours: float = 0.0
    bonus: float = 0.0
    arrears: float = 0.0
    leave_pay: float = 0.0
    other_earnings: float = 0.0
    absent_days: float = 0.0
    proration: float = 1.0                 # fraction of month worked (joiners/leavers)
    voluntary_pension: float = 0.0         # employee contribution deducted via payroll
    insurance_premium: float = 0.0         # for insurance relief only
    mortgage_interest: float = 0.0         # for allowable deduction only
    prmf: float = 0.0                      # post-retirement medical fund contribution
    disabled: bool = False
    employment_type: str = "Primary"
    nssf_contracted_out: bool = False
    deductions: dict = field(default_factory=dict)   # post-tax deductions name -> amount


def nssf_limits(rates: dict, period: str) -> tuple[float, float]:
    """Return (LEL, UEL) applicable to a YYYY-MM period."""
    start = f"{period}-01" if period else "9999-12-31"
    schedule = sorted(rates["nssf_schedule"], key=lambda s: s["effective"])
    chosen = schedule[0]
    for entry in schedule:
        if entry["effective"] <= start:
            chosen = entry
    return float(chosen["lel"]), float(chosen["uel"])


def tax_on_bands(taxable: float, bands: list) -> float:
    tax, lower = 0.0, 0.0
    for upper, rate in bands:
        top = taxable if upper is None else min(taxable, float(upper))
        if top > lower:
            tax += (top - lower) * float(rate)
        if upper is None or taxable <= float(upper):
            break
        lower = float(upper)
    return tax


def calculate(inp: PayInput, rates: dict) -> dict:
    res: dict = {"warnings": []}
    p = inp.proration

    basic = r2(inp.basic * p)
    allowances = {k: r2(v * p) for k, v in inp.allowances.items() if v}
    hourly = inp.basic / rates["standard_monthly_hours"] if rates["standard_monthly_hours"] else 0
    overtime = r2(hourly * (inp.ot_normal_hours * rates["overtime_normal_multiplier"]
                            + inp.ot_holiday_hours * rates["overtime_holiday_multiplier"]))
    absence = r2(inp.basic / rates["days_per_month_for_absence"] * inp.absent_days)

    gross = r2(basic + sum(allowances.values()) + overtime + inp.bonus + inp.arrears
               + inp.leave_pay + inp.other_earnings - absence)
    gross = max(gross, 0.0)

    res.update(basic=basic, allowances=allowances, overtime=overtime, absence=absence,
               bonus=r2(inp.bonus), arrears=r2(inp.arrears), leave_pay=r2(inp.leave_pay),
               other_earnings=r2(inp.other_earnings), gross_pay=gross)

    other_deds = {k: r2(v) for k, v in inp.deductions.items() if v}
    res["other_deductions"] = other_deds
    total_other = r2(sum(other_deds.values()))

    zero_keys = ("nssf_tier1", "nssf_tier2", "nssf_employee", "nssf_employer_tier1",
                 "nssf_employer_tier2", "nssf_employer", "shif", "ahl_employee",
                 "ahl_employer", "nita", "pension_allowed", "mortgage_allowed",
                 "prmf_allowed", "disability_exempt", "tax_charged", "personal_relief",
                 "insurance_relief", "paye", "wht", "taxable_benefits", "taxable_pay",
                 "voluntary_pension")
    res.update({k: 0.0 for k in zero_keys})

    if inp.employment_type == "Consultant (WHT)":
        wht = r2(gross * rates["consultant_wht_rate"])
        total_ded = r2(wht + total_other)
        res.update(wht=wht, total_deductions=total_ded, net_pay=r2(gross - total_ded),
                   employer_cost=gross)
        _checks(res, inp, rates)
        return res

    # --- Taxable benefits -------------------------------------------------
    non_cash = inp.non_cash_benefits if inp.non_cash_benefits > rates["non_cash_benefit_threshold"] else 0.0
    taxable_benefits = r2(non_cash + inp.car_benefit + inp.housing_benefit)

    # --- NSSF -------------------------------------------------------------
    lel, uel = nssf_limits(rates, inp.period)
    rate = rates["nssf_rate"]
    tier1 = r2(rate * min(gross, lel))
    tier2 = 0.0 if inp.nssf_contracted_out else r2(rate * max(0.0, min(gross, uel) - lel))
    nssf_ee = r2(tier1 + tier2)

    # --- SHIF & Housing Levy ---------------------------------------------
    shif = r2(max(rates["shif_minimum"], gross * rates["shif_rate"])) if gross > 0 else 0.0
    ahl = r2(gross * rates["ahl_rate"])

    # --- Allowable deductions --------------------------------------------
    vol_pension = r2(inp.voluntary_pension)
    pension_allowed = r2(min(nssf_ee + vol_pension, rates["pension_deduction_cap"]))
    mortgage_allowed = r2(min(inp.mortgage_interest, rates["mortgage_interest_cap"]))
    prmf_allowed = r2(min(inp.prmf, rates["prmf_cap"]))

    taxable = gross + taxable_benefits - pension_allowed - shif - ahl - mortgage_allowed - prmf_allowed
    taxable = max(0.0, taxable)
    disability_exempt = 0.0
    if inp.disabled:
        disability_exempt = min(taxable, rates["disability_exemption"])
        taxable -= disability_exempt
    taxable = r2(taxable)

    # --- PAYE -------------------------------------------------------------
    if inp.employment_type == "Secondary":
        tax_charged = r2(taxable * rates["secondary_employment_rate"])
        personal_relief = 0.0
    else:
        tax_charged = r2(tax_on_bands(taxable, rates["paye_bands"]))
        personal_relief = float(rates["personal_relief"])
    insurance_relief = r2(min(inp.insurance_premium * rates["insurance_relief_rate"],
                              rates["insurance_relief_cap"]))
    personal_relief = min(personal_relief, tax_charged)
    insurance_relief = min(insurance_relief, tax_charged - personal_relief)
    paye = r2(max(0.0, tax_charged - personal_relief - insurance_relief))

    statutory = r2(nssf_ee + shif + ahl + paye)
    total_ded = r2(statutory + vol_pension + total_other)
    nita = float(rates["nita_levy"])

    res.update(
        taxable_benefits=taxable_benefits,
        nssf_lel=lel, nssf_uel=uel,
        nssf_tier1=tier1, nssf_tier2=tier2, nssf_employee=nssf_ee,
        nssf_employer_tier1=tier1, nssf_employer_tier2=tier2, nssf_employer=nssf_ee,
        shif=shif, ahl_employee=ahl, ahl_employer=ahl, nita=nita,
        voluntary_pension=vol_pension, pension_allowed=pension_allowed,
        mortgage_allowed=mortgage_allowed, prmf_allowed=prmf_allowed,
        disability_exempt=r2(disability_exempt), taxable_pay=taxable,
        tax_charged=tax_charged, personal_relief=r2(personal_relief),
        insurance_relief=r2(insurance_relief), paye=paye,
        statutory_deductions=statutory, total_deductions=total_ded,
        net_pay=r2(gross - total_ded),
        employer_cost=r2(gross + nssf_ee + ahl + nita),
    )
    _checks(res, inp, rates)
    return res


def _checks(res: dict, inp: PayInput, rates: dict) -> None:
    w = res["warnings"]
    gross = res["gross_pay"]
    if res["net_pay"] < 0:
        w.append("Net pay is negative - reduce deductions.")
    elif gross and res["total_deductions"] > gross * rates["max_deductions_fraction"]:
        w.append("Deductions exceed two-thirds of wages (Employment Act s.19(3)).")
    if (inp.employment_type != "Consultant (WHT)" and inp.proration >= 1
            and 0 < inp.basic < rates["minimum_wage"]):
        w.append(f"Basic pay below configured minimum wage (KES {rates['minimum_wage']:,.2f}).")


def net_to_gross(target_net: float, template: PayInput, rates: dict) -> tuple[float, dict]:
    """Find the basic salary that yields target_net, keeping other inputs fixed."""
    lo, hi = 0.0, max(target_net * 3, 50000.0)
    best = None
    for _ in range(80):
        mid = (lo + hi) / 2
        template.basic = mid
        res = calculate(template, rates)
        best = (mid, res)
        if abs(res["net_pay"] - target_net) < 0.005:
            break
        if res["net_pay"] < target_net:
            lo = mid
        else:
            hi = mid
    template.basic = r2(best[0])
    return template.basic, calculate(template, rates)
