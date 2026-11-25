"""Module 8b — illustrative tax-impact simulator.

Principles (Project QC rules 1, 2, 3, 6, 8):
* Output always states AY, assessee category, governing Act, provision, rate,
  surcharge, cess, assumptions, exclusions and full workings.
* Computes INCREMENTAL tax attributable to a proposed addition, separately from
  the tax on returned income — never presented as total liability or demand.
* Each addition is a *proposed* amount; scenarios show normal rate vs s.115BBE
  vs "explanation accepted" (nil). No scenario is labelled an upper bound.
* Marginal relief, interest (ss.234A-C), rebate interaction with special-rate
  income and set-off of losses are NOT computed and are listed as exclusions.
"""
from __future__ import annotations

import json

from ..core import audit
from ..core.config import STATIC_DATA_DIR
from ..core.db import dumps, ro, row_to_dict, tx, utcnow
from ..core.errors import ValidationError
from . import cases


def load_rates(ay: str) -> dict:
    data = json.loads((STATIC_DATA_DIR / "tax_rates.json").read_text(encoding="utf-8"))
    if ay not in data:
        raise ValidationError(f"No rate table configured for AY {ay}. Add it to data/tax_rates.json after verification.",
                              details={"available": [k for k in data if not k.startswith("_")]})
    return data[ay]


def _table(rates: dict, category: str) -> dict:
    t = rates.get(category)
    if isinstance(t, str):
        t = rates.get(t)
    if not t:
        raise ValidationError(f"No rate table for assessee category {category}.")
    return t


def _r(x: float) -> float:
    return round(x + 1e-9, 0)


def _normal_tax(income: float, table: dict, cess: float, steps: list[str], label: str) -> dict:
    income = max(0.0, income)
    if "slabs" in table:
        tax, lower = 0.0, 0.0
        for upper, rate in table["slabs"]:
            top = income if upper is None else min(income, upper)
            if top > lower:
                part = (top - lower) * rate
                if part:
                    steps.append(f"{label}: ₹{lower:,.0f}–₹{top:,.0f} @ {rate:.0%} = ₹{part:,.0f}")
                tax += part
            if upper is None or income <= upper:
                break
            lower = upper
        reb = table.get("rebate_87a")
        rebate = 0.0
        if reb and income <= reb["income_upto"]:
            rebate = min(tax, reb["max_rebate"])
            steps.append(f"{label}: rebate u/s 87A (income ≤ ₹{reb['income_upto']:,.0f}) = −₹{rebate:,.0f}")
        tax -= rebate
    else:
        tax = income * table["rate"]
        steps.append(f"{label}: ₹{income:,.0f} @ {table['rate']:.0%} = ₹{tax:,.0f}")
    sc_rate = 0.0
    for band in table.get("surcharge", []):
        if income > band["above"]:
            sc_rate = band["rate"]
    sc = tax * sc_rate
    if sc:
        steps.append(f"{label}: surcharge @ {sc_rate:.0%} = ₹{sc:,.0f} (marginal relief NOT computed)")
    c = (tax + sc) * cess
    steps.append(f"{label}: Health & Education cess @ {cess:.0%} = ₹{c:,.0f}")
    return {"income": income, "tax": _r(tax), "surcharge_rate": sc_rate, "surcharge": _r(sc), "cess": _r(c), "total": _r(tax + sc + c)}


def simulate(user: dict, case_id: int, *, assessment_year: str, assessee_category: str, returned_income: float | None,
             additions: list[dict], save: bool = True) -> dict:
    """additions: [{"label": str, "amount": float, "issue_id": int|None, "possible_provision": str|None}]"""
    cases.check_access(user, case_id)
    if returned_income is not None and returned_income < 0:
        raise ValidationError("Returned income cannot be negative in this simulator (loss cases need CA computation).")
    if not additions:
        raise ValidationError("At least one proposed addition is required.")
    seen = set()
    for a in additions:
        if not a.get("label") or float(a.get("amount", 0)) <= 0:
            raise ValidationError("Each addition needs a label and a positive amount.")
        key = (a.get("issue_id"), float(a["amount"]))
        if a.get("issue_id") and key in seen:
            raise ValidationError("Same issue and amount entered twice — avoid double counting the same receipt.")
        seen.add(key)

    rates = load_rates(assessment_year)
    table = _table(rates, assessee_category)
    cess = rates["cess_rate"]
    total_add = sum(float(a["amount"]) for a in additions)
    assumptions = [
        f"Assessment Year {assessment_year}; governing law: {rates['governing_act']}.",
        f"Assessee category: {assessee_category} — {table['basis']}.",
        "Each addition is a PROPOSED amount under examination; it is not established as taxable income.",
        "Amounts are taken as entered by the user; they have not been independently verified.",
    ]
    exclusions = ["Interest u/s 234A/234B/234C", "Marginal relief on surcharge", "Set-off of losses / unabsorbed depreciation",
                  "Advance tax, TDS and self-assessment tax credits", "Penalty levy (shown only as indicative exposure)",
                  "Interaction of rebate u/s 87A with special-rate income"]
    if not rates.get("verified"):
        assumptions.append("RATE TABLE NOT YET VERIFIED BY CA — results are provisional.")
    if returned_income is None:
        assumptions.append("Returned income NOT PROVIDED — treated as ₹0 for the incremental computation; surcharge thresholds may therefore be understated.")
    base_inc = float(returned_income or 0)

    scenarios = []
    # Scenario A — explanation accepted
    scenarios.append({"key": "A", "title": "Explanation accepted — no addition", "incremental_tax": 0.0,
                      "workings": ["No addition made; incremental tax nil."], "provision": "—"})

    # Scenario B — addition taxed at normal rates
    steps_b: list[str] = []
    base = _normal_tax(base_inc, table, cess, steps_b, "Returned income")
    with_add = _normal_tax(base_inc + total_add, table, cess, steps_b, "Returned + additions")
    inc_b = with_add["total"] - base["total"]
    steps_b.append(f"Incremental tax = ₹{with_add['total']:,.0f} − ₹{base['total']:,.0f} = ₹{inc_b:,.0f}")
    scenarios.append({"key": "B", "title": "Addition taxed as business/other income at normal rates",
                      "provision": "Normal rates (e.g., if treated as unrecorded business receipts) — legal basis REQUIRES CA VERIFICATION",
                      "incremental_tax": inc_b, "workings": steps_b, "base": base, "with_additions": with_add})

    # Scenario C — s.115BBE on additions (if characterised under ss.68–69D)
    bbe = rates["S115BBE"]
    steps_c: list[str] = []
    base_c = _normal_tax(base_inc, table, cess, steps_c, "Returned income (normal rates)")
    t = total_add * bbe["rate"]
    sc = t * bbe["surcharge_flat"]
    c = (t + sc) * cess
    steps_c += [f"Additions ₹{total_add:,.0f} @ {bbe['rate']:.0%} u/s 115BBE = ₹{t:,.0f}",
                f"Surcharge @ {bbe['surcharge_flat']:.0%} = ₹{sc:,.0f}", f"Cess @ {cess:.0%} = ₹{c:,.0f}",
                "No deduction of expenditure/allowance or set-off of loss against this income (s.115BBE(2))."]
    if table.get("surcharge"):
        steps_c.append("Surcharge on returned-income tax may change because total income rises — re-check thresholds (not recomputed).")
    inc_c = _r(t + sc + c)
    scenarios.append({"key": "C", "title": "Addition characterised u/s 68/69/69A/69B/69C/69D and taxed u/s 115BBE",
                      "provision": "s.115BBE read with the relevant section among 68–69D — applicability REQUIRES CA VERIFICATION",
                      "incremental_tax": inc_c, "workings": steps_c, "base": base_c})

    pen = rates["PENALTY"]
    penalty = {
        "note": "Indicative only. Penalty is a separate proceeding; levy depends on facts, immunity options and CA assessment.",
        "s270A_under_reporting_on_B": _r(inc_b * pen["s270A_under_reporting"]),
        "s270A_misreporting_on_B": _r(inc_b * pen["s270A_misreporting"]),
        "s271AAC_on_C": _r(t * pen["s271AAC"]),
        "s271AAC_basis": "10% of tax computed u/s 115BBE(1)(i) (before surcharge & cess) — verify base",
    }
    result = {
        "label": "ILLUSTRATIVE ESTIMATE — NOT A TAX DEMAND OR FINAL LIABILITY — REQUIRES CA VERIFICATION",
        "assessment_year": assessment_year, "assessee_category": assessee_category,
        "governing_act": rates["governing_act"], "rates_verified": bool(rates.get("verified")),
        "returned_income": returned_income, "additions": additions, "total_proposed_additions": total_add,
        "scenarios": scenarios, "penalty_exposure_indicative": penalty,
        "assumptions": assumptions, "exclusions": exclusions,
        "methodology": "Incremental tax = tax on (returned income + proposed additions) − tax on returned income, per scenario.",
    }
    if save:
        with tx() as conn:
            cur = conn.execute("INSERT INTO tax_computations(case_id,inputs_json,result_json,created_by,created_at) VALUES (?,?,?,?,?)",
                               (case_id, dumps({"ay": assessment_year, "cat": assessee_category, "returned": returned_income,
                                                "additions": additions}), dumps(result), user["id"], utcnow()))
            result["id"] = cur.lastrowid
            audit.log_event(conn, "TAX_SIMULATION", user_id=user["id"], case_id=case_id,
                            meta={"computation_id": cur.lastrowid, "n_additions": len(additions)})
    return result


def list_computations(user: dict, case_id: int) -> list[dict]:
    cases.check_access(user, case_id)
    with ro() as conn:
        rows = conn.execute("SELECT * FROM tax_computations WHERE case_id=? ORDER BY id DESC", (case_id,)).fetchall()
    return [row_to_dict(r, ("inputs_json", "result_json")) for r in rows]
