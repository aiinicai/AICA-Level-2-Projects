"""Disclosure engine (Ind AS 116.47–60, Ind AS 7.44A–44E, Schedule III).

Aggregates calculated lease results for a reporting period into the tables normally
presented in the lease note of Indian financial statements. Narrative items that need
entity input (para 59 qualitative disclosures) are returned as prompts, never invented.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from .decimal_utils import D, ZERO, q
from .models import Framework, LesseeResult, PaymentCategory
from .references import ref


@dataclass
class LeaseForDisclosure:
    lease_id: str
    entity: str
    asset_class: str
    result: Optional[LesseeResult] = None          # capitalised lessee lease
    exempt_type: Optional[str] = None              # SHORT_TERM | LOW_VALUE
    exempt_rows: list = field(default_factory=list)
    sublease_income_rows: list = field(default_factory=list)
    slb_gain: Decimal = ZERO
    slb_date: Optional[date] = None
    currency: str = "INR"
    option_exposure: Decimal = ZERO                # undiscounted payments in optional periods not included
    commencement: Optional[date] = None


def _rows_in(result: LesseeResult, start: date, end: date):
    return [r for r in result.periods if start <= r.period_end <= end]


def _row_at_or_before(result: LesseeResult, d: date):
    cand = [r for r in result.periods if r.period_end <= d]
    return cand[-1] if cand else None


def build_disclosures(items: list[LeaseForDisclosure], start: date, end: date,
                      framework: Framework = Framework.IND_AS_116, decimals: int = 2,
                      buckets: tuple = (1, 2, 3, 4, 5)) -> dict:
    classes = sorted({i.asset_class for i in items if i.result is not None})
    rou_mv = {c: defaultdict(lambda: ZERO) for c in classes}
    liab_mv = defaultdict(lambda: ZERO)
    p53 = defaultdict(lambda: ZERO)
    dep_by_class = defaultdict(lambda: ZERO)
    maturity = defaultdict(lambda: ZERO)
    not_commenced = []
    weighted_rate_num = ZERO
    weighted_rate_den = ZERO
    current = ZERO
    noncurrent = ZERO
    for it in items:
        if it.result is not None:
            res = it.result
            rows = _rows_in(res, start, end)
            before = _row_at_or_before(res, date.fromordinal(start.toordinal() - 1))
            last = _row_at_or_before(res, end)
            if res.periods and res.periods[0].period_start > end:
                not_commenced.append({"lease_id": it.lease_id, "commencement": res.periods[0].period_start,
                                      "initial_liability": res.initial.liability})
                continue
            c = it.asset_class
            m = rou_mv[c]
            open_rou = before.rou_close if before else ZERO
            open_cost = before.rou_cost_close if before else ZERO
            open_accdep = (before.rou_accdep_close + before.rou_accimp_close) if before else ZERO
            m["opening_nbv"] += open_rou
            m["opening_gross"] += open_cost
            m["opening_acc_dep_imp"] += open_accdep
            for r in rows:
                m["additions"] += r.rou_additions
                m["remeasurement_modification"] += r.rou_remeasurement + r.rou_modification
                m["derecognition"] += r.rou_derecognised
                m["depreciation"] += r.depreciation
                m["impairment"] += r.impairment
                liab_mv["additions"] += r.liab_additions
                liab_mv["interest"] += r.interest
                liab_mv["payments"] += r.payments
                liab_mv["remeasurement_modification"] += r.liab_remeasurement + r.liab_modification
                liab_mv["derecognition"] += r.liab_derecognised
                liab_mv["fx"] += getattr(r, "liab_fx", ZERO)
                p53["interest"] += r.interest
                p53["variable"] += r.variable_expense
                p53["cash_outflow"] += r.cash_outflow
                p53["additions"] += r.rou_additions
                p53["gain_loss_events"] += r.gain_loss + r.remeasurement_pl
                dep_by_class[c] += r.depreciation
                if r.rou_additions and r.liab_additions:
                    weighted_rate_num += r.liab_additions * r.rate_pct
                    weighted_rate_den += r.liab_additions
            # pre-commencement cash within the period
            for ln in res.payments:
                if ln.included and ln.date < res.initial.measurement_date and start <= ln.date <= end:
                    p53["cash_outflow"] += D(ln.lease_amount)
            m["closing_nbv"] += last.rou_close if last else ZERO
            m["closing_gross"] += last.rou_cost_close if last else ZERO
            m["closing_acc_dep_imp"] += (last.rou_accdep_close + last.rou_accimp_close) if last else ZERO
            liab_mv["opening"] += before.liab_close if before else ZERO
            liab_mv["closing"] += last.liab_close if last else ZERO
            if last and last.period_end == end:
                current += last.liab_current
                noncurrent += last.liab_noncurrent
                for k, v in last.maturity.items():
                    maturity[k] += v
            if it.option_exposure:
                p53["option_exposure"] += it.option_exposure
        if it.exempt_type:
            for r in it.exempt_rows:
                if start <= r["period_end"] <= end:
                    key = "short_term" if it.exempt_type == "SHORT_TERM" else "low_value"
                    p53[key] += r["expense"]
                    p53["variable"] += r.get("variable_expense", ZERO)
                    p53["cash_outflow"] += r.get("cash_paid", ZERO)
        for r in it.sublease_income_rows:
            if start <= r["period_end"] <= end:
                p53["sublease_income"] += r.get("lease_income", ZERO) + r.get("finance_income", ZERO)
        if it.slb_gain and it.slb_date and start <= it.slb_date <= end:
            p53["slb_gain"] += it.slb_gain

    rou_table = []
    for c in classes:
        m = rou_mv[c]
        calc_close = (m["opening_nbv"] + m["additions"] + m["remeasurement_modification"] - m["derecognition"]
                      - m["depreciation"] - m["impairment"])
        rou_table.append({"asset_class": c, **{k: q(v, decimals) for k, v in m.items()},
                          "reconciliation_difference": q(calc_close - m["closing_nbv"], decimals)})
    total_row = {"asset_class": "Total"}
    for k in ("opening_gross", "opening_acc_dep_imp", "opening_nbv", "additions", "remeasurement_modification", "derecognition",
              "depreciation", "impairment", "closing_gross", "closing_acc_dep_imp", "closing_nbv", "reconciliation_difference"):
        total_row[k] = q(sum((D(r.get(k, 0)) for r in rou_table), ZERO), decimals)
    rou_table.append(total_row)

    lm = {k: q(v, decimals) for k, v in liab_mv.items()}
    calc_close = (liab_mv["opening"] + liab_mv["additions"] + liab_mv["interest"] - liab_mv["payments"]
                  + liab_mv["remeasurement_modification"] - liab_mv["derecognition"] + liab_mv["fx"])
    lm["reconciliation_difference"] = q(calc_close - liab_mv["closing"], decimals)

    total_undiscounted = sum(maturity.values(), ZERO)
    mat_rows = [{"bucket": _bucket_label(k), "undiscounted": q(v, decimals)} for k, v in maturity.items()]
    closing_liab = liab_mv["closing"]
    cash_label = ("Principal and interest portions in financing activities; short-term, low-value and variable payments in "
                  "operating activities (Ind AS 116.50; Ind AS 7)" if framework == Framework.IND_AS_116 else
                  "Principal in financing activities; interest per entity's IAS 7 policy (IFRS 16.50) — check IFRS 18 from 2027")
    para53 = [
        {"item": "Depreciation charge for right-of-use assets — by class", "ref": "53(a)",
         "amount": q(sum(dep_by_class.values(), ZERO), decimals),
         "by_class": {k: q(v, decimals) for k, v in dep_by_class.items()}},
        {"item": "Interest expense on lease liabilities", "ref": "53(b)", "amount": q(p53["interest"], decimals)},
        {"item": "Expense relating to short-term leases (excluding leases ≤ 1 month)", "ref": "53(c)", "amount": q(p53["short_term"], decimals)},
        {"item": "Expense relating to leases of low-value assets (excluding short-term)", "ref": "53(d)", "amount": q(p53["low_value"], decimals)},
        {"item": "Expense relating to variable lease payments not included in lease liabilities", "ref": "53(e)", "amount": q(p53["variable"], decimals)},
        {"item": "Income from subleasing right-of-use assets", "ref": "53(f)", "amount": q(p53["sublease_income"], decimals)},
        {"item": "Total cash outflow for leases", "ref": "53(g)", "amount": q(p53["cash_outflow"], decimals)},
        {"item": "Additions to right-of-use assets", "ref": "53(h)", "amount": q(p53["additions"], decimals)},
        {"item": "Gains or losses arising from sale and leaseback transactions", "ref": "53(i)", "amount": q(p53["slb_gain"], decimals)},
        {"item": "Carrying amount of right-of-use assets at the end of the period — by class", "ref": "53(j)",
         "amount": q(sum((D(r["closing_nbv"]) for r in rou_table if r["asset_class"] != "Total"), ZERO), decimals),
         "by_class": {r["asset_class"]: r["closing_nbv"] for r in rou_table if r["asset_class"] != "Total"}},
    ]
    ind_as7 = {
        "opening": lm.get("opening", ZERO),
        "cash_flows_financing": -q(liab_mv["payments"], decimals),
        "non_cash_new_leases": lm.get("additions", ZERO),
        "non_cash_interest_accrued": lm.get("interest", ZERO),
        "non_cash_remeasurement_modification": lm.get("remeasurement_modification", ZERO),
        "non_cash_derecognition": -lm.get("derecognition", ZERO),
        "non_cash_exchange_differences": lm.get("fx", ZERO),
        "closing": lm.get("closing", ZERO),
        "reference": "Ind AS 7.44A–44E",
    }
    return {
        "period": {"start": start, "end": end, "framework": framework.value},
        "para53": para53,
        "rou_movement": rou_table,
        "liability_movement": lm,
        "presentation": {"current": q(current, decimals), "non_current": q(noncurrent, decimals),
                         "total": q(current + noncurrent, decimals), "reference": "Ind AS 116.47; " + ref("SCHEDULE_III")},
        "maturity": {"rows": mat_rows, "total_undiscounted": q(total_undiscounted, decimals),
                     "future_finance_charges": q(total_undiscounted - closing_liab, decimals),
                     "carrying_amount": q(closing_liab, decimals), "reference": ref("MATURITY")},
        "ind_as_7": ind_as7,
        "cash_flow_classification": cash_label,
        "weighted_average_rate_new_leases": (q(weighted_rate_num / weighted_rate_den, 4) if weighted_rate_den else None),
        "leases_not_yet_commenced": not_commenced,
        "qualitative_prompts": [
            {"ref": "59(a)", "prompt": "Nature of leasing activities (asset types, typical terms, locations)."},
            {"ref": "59(b)(i)", "prompt": "Variable lease payments — nature and future cash outflow exposure."},
            {"ref": "59(b)(ii)", "prompt": "Extension and termination options not reflected in lease liabilities.",
             "amount_undiscounted": q(p53["option_exposure"], decimals)},
            {"ref": "59(b)(iii)", "prompt": "Residual value guarantees."},
            {"ref": "59(b)(iv)", "prompt": "Leases not yet commenced to which the lessee is committed.", "count": len(not_commenced)},
            {"ref": "59(c)", "prompt": "Restrictions or covenants imposed by leases."},
            {"ref": "59(d)", "prompt": "Sale and leaseback transactions."},
            {"ref": "60", "prompt": "State that the short-term and/or low-value exemptions are applied, if so."},
        ],
    }


def _bucket_label(k: str) -> str:
    if k.startswith(">"):
        return f"More than {k[1:]} years"
    a, b = k.split("-")
    if a == "0":
        return "Not later than 1 year" if b == "1" else f"Up to {b} years"
    return f"Later than {a} year{'s' if a != '1' else ''} and not later than {b} years"
