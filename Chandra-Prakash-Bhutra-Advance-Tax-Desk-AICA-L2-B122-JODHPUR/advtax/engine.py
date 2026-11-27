"""Rule-based tax and advance tax computation.

All rates, limits and dates come from the JSON rules file in /config, so the
figures can be checked and updated without touching this code.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent.parent / "config" / "tax_rules_ty2026_27.json"

CONSTITUTIONS = ["Individual", "HUF", "Firm", "LLP"]
AGE_BANDS = {"below60": "Below 60", "senior": "60 to 79", "super_senior": "80 and above"}


def load_rules(path: str | Path = RULES_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@dataclass
class ClientInputs:
    name: str = ""
    constitution: str = "Individual"
    age_band: str = "below60"
    resident: bool = True
    regime: str = "auto"  # auto / new / old (individuals and HUFs only)
    presumptive: bool = False
    # Business or profession (projected full-year taxable figure)
    business_income: float = 0.0
    # Salary
    salary_gross: float = 0.0
    # House property
    hp_let_out_rent: float = 0.0
    hp_municipal_tax: float = 0.0
    hp_let_out_interest: float = 0.0
    hp_self_occupied_interest: float = 0.0
    # Capital gains
    stcg_equity: float = 0.0
    ltcg_equity: float = 0.0
    ltcg_other: float = 0.0
    stcg_other: float = 0.0
    # Other sources
    other_interest: float = 0.0
    other_dividend: float = 0.0
    other_misc: float = 0.0
    # Deductions (old regime only)
    deductions_old: float = 0.0
    # Taxes already paid
    tds_tcs: float = 0.0
    payments: list = field(default_factory=list)  # [{"date": "2026-06-10", "amount": 10000}]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ClientInputs":
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    @property
    def is_firm(self) -> bool:
        return self.constitution in ("Firm", "LLP")


def slab_tax(income: float, slabs: list) -> float:
    tax, lower = 0.0, 0.0
    for upper, rate in slabs:
        if upper is None or income <= upper:
            tax += max(0.0, income - lower) * rate
            break
        tax += (upper - lower) * rate
        lower = upper
    return tax


def _surcharge_rate(income: float, table: list, cap: float) -> float:
    rate = 0.0
    for threshold, r in table:
        if income > threshold:
            rate = r
    return min(rate, cap)


def _house_property(inp: ClientInputs, regime: str, rules: dict) -> tuple[float, list]:
    hp, flags = rules["house_property"], []
    nav = max(0.0, inp.hp_let_out_rent - inp.hp_municipal_tax)
    let_out = nav - nav * hp["standard_deduction_rate"] - inp.hp_let_out_interest
    if regime == "old":
        total = let_out - min(inp.hp_self_occupied_interest, hp["self_occupied_interest_cap"])
        if total < -hp["loss_setoff_cap"]:
            flags.append("House property loss above Rs 2,00,000 is not set off this year (carried forward).")
            total = -hp["loss_setoff_cap"]
        return total, flags
    if inp.hp_self_occupied_interest > 0 and not inp.is_firm:
        flags.append("Interest on self-occupied house is not allowed under the new regime.")
    if let_out < 0:
        flags.append("House property loss is not set off against other heads under the new regime.")
    return max(0.0, let_out), flags


def compute_tax(inp: ClientInputs, regime: str, rules: dict) -> dict:
    """Tax for the full year under one regime. For firms/LLPs regime is ignored."""
    flags: list[str] = []
    cg = rules["capital_gains"]
    firm = inp.is_firm
    reg_key = "old" if (regime == "old" and not firm) else "new"
    reg = rules["old_regime"] if reg_key == "old" else rules["new_regime"]

    # ---- heads of income -------------------------------------------------
    salary = 0.0
    if not firm and inp.salary_gross > 0:
        salary = max(0.0, inp.salary_gross - reg["standard_deduction"])
    hp_income, hp_flags = _house_property(inp, "old" if (firm or reg_key == "old") else "new", rules)
    flags += hp_flags
    other = inp.other_interest + inp.other_dividend + inp.other_misc
    pool = inp.business_income + other + inp.stcg_other
    if pool < 0:
        flags.append("Business loss exceeds other non-salary income; the balance is carried forward, not set off here.")
        pool = 0.0
    gross_normal = max(0.0, salary + pool + hp_income)
    deductions = 0.0
    if reg_key == "old" and not firm:
        deductions = min(max(0.0, inp.deductions_old), gross_normal)
    normal = gross_normal - deductions

    stcg_eq = max(0.0, inp.stcg_equity)
    ltcg_eq = max(0.0, inp.ltcg_equity)
    ltcg_ot = max(0.0, inp.ltcg_other)
    total_income = normal + stcg_eq + ltcg_eq + ltcg_ot

    # ---- tax before surcharge -------------------------------------------
    if firm:
        normal_tax = normal * rules["firm"]["rate"]
        t_stcg, t_ltcg_eq, t_ltcg_ot = stcg_eq, ltcg_eq, ltcg_ot
    else:
        # Higher exemption for age applies only to resident individuals
        age = inp.age_band if (inp.constitution == "Individual" and inp.resident) else "below60"
        slabs = reg["slabs"] if reg_key == "new" else reg["slabs_by_age"][age]
        normal_tax = slab_tax(normal, slabs)
        t_stcg, t_ltcg_eq, t_ltcg_ot = stcg_eq, ltcg_eq, ltcg_ot
        # Unused basic exemption is adjusted against special-rate gains (residents only)
        if inp.resident:
            gap = max(0.0, slabs[0][0] - normal)
            used = min(gap, t_stcg); t_stcg -= used; gap -= used
            used = min(gap, t_ltcg_ot); t_ltcg_ot -= used; gap -= used
            used = min(gap, t_ltcg_eq); t_ltcg_eq -= used; gap -= used

    stcg_tax = t_stcg * cg["stcg_equity_rate"]
    ltcg_eq_tax = max(0.0, t_ltcg_eq - cg["ltcg_equity_exemption"]) * cg["ltcg_equity_rate"]
    ltcg_ot_tax = t_ltcg_ot * cg["ltcg_other_rate"]
    special_tax = stcg_tax + ltcg_eq_tax + ltcg_ot_tax
    has_special = (stcg_eq + ltcg_eq + ltcg_ot) > 0

    # ---- rebate (resident individuals only) ------------------------------
    rebate = 0.0
    if inp.constitution == "Individual" and inp.resident:
        limit = reg["rebate_income_limit"]
        if reg_key == "new":
            if total_income <= limit:
                rebate = min(normal_tax, reg["rebate_max"])
            elif not has_special:
                relief = normal_tax - (total_income - limit)
                if relief > 0:
                    rebate = relief  # marginal relief just above the rebate limit
        elif total_income <= limit:
            rebate = min(normal_tax + stcg_tax + ltcg_ot_tax, reg["rebate_max"])
    tax_after_rebate = normal_tax + special_tax - rebate

    # ---- surcharge -------------------------------------------------------
    surcharge = 0.0
    if firm:
        f = rules["firm"]
        if total_income > f["surcharge_threshold"]:
            surcharge = tax_after_rebate * f["surcharge"]
            if not has_special:
                cap = f["surcharge_threshold"] * f["rate"] + (total_income - f["surcharge_threshold"])
                surcharge = max(0.0, min(tax_after_rebate + surcharge, cap) - tax_after_rebate)
    else:
        table, max_sc = rules["surcharge_individual"], reg["max_surcharge"]
        rate_total = _surcharge_rate(total_income, table, max_sc)
        if rate_total > 0:
            cap15 = rules["capital_gains_surcharge_cap"]
            income_ex_cg = total_income - (stcg_eq + ltcg_eq + ltcg_ot)
            rate_normal = _surcharge_rate(income_ex_cg, table, max_sc)
            if rate_normal <= cap15:
                rate_normal = min(rate_total, cap15)
            normal_part = max(0.0, normal_tax - rebate)
            surcharge = normal_part * rate_normal + special_tax * min(rate_total, cap15)
            if rate_normal > cap15 and inp.other_dividend > 0:
                flags.append("Surcharge above 15% applies and there is dividend income: the surcharge on tax on "
                             "dividend is limited to 15%, which is not worked out here. Check manually.")
            if not has_special:
                threshold = max(t for t, _ in table if total_income > t)
                base = slab_tax(threshold, slabs)
                base *= 1 + _surcharge_rate(threshold, table, max_sc)
                cap = base + (total_income - threshold)
                surcharge = max(0.0, min(tax_after_rebate + surcharge, cap) - tax_after_rebate)
            else:
                flags.append("Surcharge applies with capital gains: marginal relief is not computed, check manually.")

    cess = (tax_after_rebate + surcharge) * rules["cess"]
    total_tax = round(tax_after_rebate + surcharge + cess)

    return {
        "regime": "Firm rate" if firm else ("Old regime" if reg_key == "old" else "New regime"),
        "regime_key": "firm" if firm else reg_key,
        "salary_income": round(salary),
        "house_property_income": round(hp_income),
        "business_income": round(inp.business_income),
        "other_sources_income": round(other),
        "stcg_other": round(inp.stcg_other),
        "deductions": round(deductions),
        "normal_income": round(normal),
        "stcg_equity": round(stcg_eq),
        "ltcg_equity": round(ltcg_eq),
        "ltcg_other": round(ltcg_ot),
        "total_income": round(total_income),
        "tax_on_normal_income": round(normal_tax),
        "tax_on_capital_gains": round(special_tax),
        "rebate": round(rebate),
        "surcharge": round(surcharge),
        "cess": round(cess),
        "total_tax": total_tax,
        "flags": flags,
    }


def _d(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def _floor100(x: float) -> float:
    return math.floor(max(0.0, x) / 100.0) * 100.0


def instalment_schedule(net_liability: float, payments: list, as_on: date, presumptive: bool, rules: dict) -> dict:
    """Instalment-wise position and deferment interest (Section 425)."""
    at = rules["advance_tax"]
    plan = at["presumptive_instalments"] if presumptive else at["instalments"]
    months = [1] if presumptive else at["deferment_months"]
    pays = sorted(((_d(p["date"]), float(p["amount"])) for p in payments if float(p.get("amount", 0) or 0) > 0))
    paid_to_date = sum(a for d, a in pays if d <= as_on)
    rows, incurred, projected = [], 0.0, 0.0
    next_due = None
    for (due_s, pct), m in zip(plan, months):
        due = _d(due_s)
        required = net_liability * pct
        paid_by_due = sum(a for d, a in pays if d <= due)
        shortfall = max(0.0, required - paid_by_due)
        safe = at["safe_harbour"].get(due_s)
        if safe is not None and paid_by_due >= net_liability * safe:
            shortfall_for_interest = 0.0
        else:
            shortfall_for_interest = _floor100(shortfall)
        interest = round(shortfall_for_interest * at["deferment_rate_per_month"] * m)
        passed = as_on > due
        if passed:
            incurred += interest
            status = "Paid in full" if shortfall <= 0 else "Missed / short"
        else:
            status = "Covered" if shortfall <= 0 else "Due"
            if next_due is None:
                next_due = {"date": due, "cumulative_pct": pct, "required_cumulative": round(required),
                            "pay_now": round(max(0.0, required - paid_to_date)),
                            "days_left": (due - as_on).days}
        projected += interest
        rows.append({"due_date": due, "cumulative_pct": pct, "required_cumulative": round(required),
                     "paid_by_due_date": round(paid_by_due), "shortfall": round(shortfall),
                     "interest": interest, "status": status, "passed": passed})
    return {"rows": rows, "paid_to_date": round(paid_to_date), "interest_incurred": round(incurred),
            "interest_if_nothing_more_paid": round(projected), "next_due": next_due}


def compute(inp: ClientInputs, rules: dict, as_on: date | None = None) -> dict:
    """Full result: regime comparison, advance tax liability and instalment position."""
    as_on = as_on or date.today()
    start, end = _d(rules["start"]), _d(rules["end"])
    as_on = min(max(as_on, start), end)

    if inp.is_firm:
        options = {"firm": compute_tax(inp, "new", rules)}
        chosen_key = "firm"
    else:
        options = {"new": compute_tax(inp, "new", rules), "old": compute_tax(inp, "old", rules)}
        if inp.regime in ("new", "old"):
            chosen_key = inp.regime
        else:
            chosen_key = "new" if options["new"]["total_tax"] <= options["old"]["total_tax"] else "old"
    chosen = options[chosen_key]

    at = rules["advance_tax"]
    net = max(0.0, chosen["total_tax"] - max(0.0, inp.tds_tcs))
    liable, reason = True, ""
    if net < at["threshold"]:
        liable, reason = False, "Tax payable after TDS/TCS is below Rs 10,000."
    elif (inp.constitution == "Individual" and inp.resident and inp.age_band != "below60"
          and inp.business_income == 0 and not inp.presumptive):
        liable, reason = False, "Resident senior citizen without business or professional income."

    schedule = instalment_schedule(net if liable else 0.0, inp.payments, as_on, inp.presumptive, rules)
    total_paid_all = sum(float(p.get("amount", 0) or 0) for p in inp.payments)
    monthly_default_interest = 0
    if liable and total_paid_all < at["default_min_ratio"] * net:
        monthly_default_interest = round(_floor100(net - total_paid_all) * at["default_rate_per_month"])

    saving = None
    if not inp.is_firm:
        other_key = "old" if chosen_key == "new" else "new"
        saving = options[other_key]["total_tax"] - chosen["total_tax"]

    return {
        "tax_year": rules["tax_year"], "as_on": as_on, "options": options, "chosen_key": chosen_key,
        "chosen": chosen, "regime_saving": saving, "tds_tcs": round(max(0.0, inp.tds_tcs)),
        "net_liability": round(net), "liable": liable, "not_liable_reason": reason,
        "schedule": schedule, "monthly_default_interest": monthly_default_interest,
        "flags": chosen["flags"],
    }


def fmt_inr(amount: float) -> str:
    """Indian digit grouping, e.g. 1234567 -> 12,34,567."""
    n = int(round(amount))
    sign, s = ("-" if n < 0 else ""), str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return f"{sign}{s}"
