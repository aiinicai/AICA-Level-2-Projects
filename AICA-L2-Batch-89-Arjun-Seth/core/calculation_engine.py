# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Lease calculation engine.

Pure, deterministic functions that replicate the Excel workbook
``LeaseIQ_Pro_POC_corrected.xlsx``:

* ``compute_initial_measurement`` -> "Initial Measurement Summary" block
  (sheet ``Initial Measurement``, B9:B19)
* ``build_finance_schedule``      -> sheet ``IndAS116 & ASC842-Fin`` (rows 11+)
* ``compute_operating_summary`` / ``build_operating_schedule``
                                  -> sheet ``ASC842-Operating Schedule``
* ``run_full_calculation``        -> orchestrates everything (Section 9.6), incl. the
                                  Classification sheet's "Downstream Method Flag" block

RULE: pure Python only - no UI-framework imports. No AI is
involved in any calculation.

Conventions
-----------------------------------
* monthly_rate = ibr / 12 (nominal, NOT the effective-annual conversion).
* Payments are end-of-month; the security deposit is discounted at the same
  monthly rate over ``lease_term_months``.
* Rent escalates at each 12-month anniversary:
  base_rent * (1 + escalation) ** ((period - 1) // 12).
* Prepaid rent covers the FIRST ``prepaid_rent_months`` months: the net cash
  payment is 0 there and the liability still accretes at the monthly rate.
"""
import calendar
from datetime import date, datetime

import pandas as pd

# Column headers exactly as on the Excel "IndAS116 & ASC842-Fin" sheet (row 10).
FINANCE_SCHEDULE_COLUMNS = [
    "Period",
    "Date",
    "Escalated Contractual Rent",
    "Net Cash Payment",
    "Opening Liability",
    "Interest Expense",
    "Principal Repayment",
    "Closing Liability",
    "ROU Gross Cost (constant)",
    "Accum. Amortization Opening",
    "Amortization Expense",
    "Accum. Amortization Closing",
    "ROU Net Carrying Value",
    "Security Deposit Opening (PV)",
    "Security Deposit Closing",
]

# Column headers exactly as on the Excel "ASC842-Operating Schedule" sheet (row 10).
# Deliberately NO gross-cost / accumulated-amortization columns: ASC 842 operating
# leases reduce the ROU asset directly through one net carrying value.
OPERATING_SCHEDULE_COLUMNS = [
    "Period",
    "Date",
    "Lease Cost",
    "Interest",
    "ROU Reduction (plug)",
    "Opening Liability",
    "Closing Liability",
    "ROU Net Carrying Value",
]

_CALC_KEYS = (
    "lease_term_months",
    "base_rent",
    "escalation",
    "prepaid_rent",
    "prepaid_rent_months",
    "idc",
    "incentives",
    "restoration_cost",
    "deposit",
    "ibr",
)
_INITIAL_KEYS = (
    "monthly_rate",
    "lease_liability_initial",
    "security_deposit_pv",
    "rou_asset_gross",
)


# --------------------------------------------------------------------------- #
# Input validation helpers (stricter than Excel: bad data raises ValueError)
# --------------------------------------------------------------------------- #
def _float(source: dict, key: str) -> float:
    value = source[key]
    if isinstance(value, bool):
        raise ValueError("'{}' must be a number, got {!r}".format(key, value))
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("'{}' must be a number, got {!r}".format(key, value)) from None
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError("'{}' must be a finite number, got {!r}".format(key, value))
    return number


def _non_negative(source: dict, key: str) -> float:
    number = _float(source, key)
    if number < 0:
        raise ValueError("'{}' must not be negative, got {!r}".format(key, source[key]))
    return number


def _whole_number(source: dict, key: str) -> int:
    number = _float(source, key)
    if not number.is_integer():
        raise ValueError("'{}' must be a whole number, got {!r}".format(key, source[key]))
    return int(number)


def _validate_inputs(inputs: dict) -> dict:
    """Return a cleaned copy of the calculation inputs (never mutates ``inputs``)."""
    missing = [key for key in _CALC_KEYS if key not in inputs]
    if missing:
        raise ValueError("Missing required input(s): {}".format(", ".join(missing)))

    term = _whole_number(inputs, "lease_term_months")
    if term < 1:
        raise ValueError("'lease_term_months' must be at least 1, got {!r}".format(term))
    prepaid_months = _whole_number(inputs, "prepaid_rent_months")
    if not 0 <= prepaid_months <= term:
        raise ValueError(
            "'prepaid_rent_months' must be between 0 and the lease term ({}), got {!r}".format(
                term, prepaid_months
            )
        )
    escalation = _float(inputs, "escalation")
    if escalation <= -1:
        raise ValueError("'escalation' must be greater than -1 (e.g. 0.05 for 5%), got {!r}".format(escalation))

    return {
        "term": term,
        "prepaid_months": prepaid_months,
        "escalation": escalation,
        "base_rent": _non_negative(inputs, "base_rent"),
        "prepaid_rent": _non_negative(inputs, "prepaid_rent"),
        "idc": _non_negative(inputs, "idc"),
        "incentives": _non_negative(inputs, "incentives"),
        "restoration_cost": _non_negative(inputs, "restoration_cost"),
        "deposit": _non_negative(inputs, "deposit"),
        "ibr": _non_negative(inputs, "ibr"),
    }


def _to_date(value) -> date:
    if isinstance(value, datetime):  # also covers pandas.Timestamp
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            pass
    raise ValueError("'commencement_date' must be a date or 'YYYY-MM-DD' text, got {!r}".format(value))


def _add_months(start: date, months: int) -> date:
    """Excel EDATE: same day-of-month, clamped to the end of shorter months."""
    index = start.year * 12 + (start.month - 1) + months
    year, month0 = divmod(index, 12)
    month = month0 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _payment_streams(p: dict):
    """Per-period escalated contractual rent and net cash payment (periods 1..term)."""
    rents = [p["base_rent"] * (1 + p["escalation"]) ** ((n - 1) // 12) for n in range(1, p["term"] + 1)]
    net_cash = [0.0 if n <= p["prepaid_months"] else rents[n - 1] for n in range(1, p["term"] + 1)]
    return rents, net_cash


# --------------------------------------------------------------------------- #
# Initial measurement (Section 9.2)
# --------------------------------------------------------------------------- #
def compute_initial_measurement(inputs: dict) -> dict:
    """Initial measurement, replicating the Excel "Initial Measurement Summary".

    Required ``inputs`` keys: lease_term_months, base_rent, escalation,
    prepaid_rent, prepaid_rent_months, idc, incentives, restoration_cost,
    deposit, ibr.

    Returns:
        monthly_rate               ibr / 12
        lease_liability_initial    PV of net cash payments (end-of-month, at monthly_rate)
        security_deposit_pv        deposit / (1 + monthly_rate) ** term_months
        security_deposit_discount  deposit - security_deposit_pv
        rou_asset_gross            liability + prepaid + IDC + restoration - incentives
                                   + security_deposit_discount
    Amounts are unrounded floats.
    """
    p = _validate_inputs(inputs)
    monthly_rate = p["ibr"] / 12
    _, net_cash = _payment_streams(p)

    lease_liability_initial = sum(cash / (1 + monthly_rate) ** n for n, cash in enumerate(net_cash, start=1))
    security_deposit_pv = p["deposit"] / (1 + monthly_rate) ** p["term"]
    security_deposit_discount = p["deposit"] - security_deposit_pv
    rou_asset_gross = (
        lease_liability_initial
        + p["prepaid_rent"]
        + p["idc"]
        - p["incentives"]
        + p["restoration_cost"]
        + security_deposit_discount
    )
    return {
        "monthly_rate": monthly_rate,
        "lease_liability_initial": lease_liability_initial,
        "security_deposit_pv": security_deposit_pv,
        "security_deposit_discount": security_deposit_discount,
        "rou_asset_gross": rou_asset_gross,
    }


# --------------------------------------------------------------------------- #
# Ind AS 116 / ASC 842 finance schedule (Sections 9.4-9.5)
# --------------------------------------------------------------------------- #
def build_finance_schedule(inputs: dict, initial: dict) -> pd.DataFrame:
    """Monthly gross-cost / accumulated-amortization schedule (one row per period).

    Used for Ind AS 116 always, and for ASC 842 when the lease is a FINANCE LEASE.
    ``inputs`` needs the keys of ``compute_initial_measurement`` plus
    ``commencement_date``; ``initial`` is that function's output.
    Columns are ``FINANCE_SCHEDULE_COLUMNS`` (the Excel headers). Unlike the Excel
    (fixed 240 rows) only periods 1..lease_term_months are produced.
    """
    p = _validate_inputs(inputs)
    if "commencement_date" not in inputs:
        raise ValueError("Missing required input(s): commencement_date")
    commencement = _to_date(inputs["commencement_date"])
    missing = [key for key in _INITIAL_KEYS if key not in initial]
    if missing:
        raise ValueError("'initial' is missing: {}".format(", ".join(missing)))

    monthly_rate = _float(initial, "monthly_rate")
    rou_gross = _float(initial, "rou_asset_gross")
    term = p["term"]
    rents, net_cash = _payment_streams(p)
    amortization = rou_gross / term  # straight-line, identical every month

    liability = _float(initial, "lease_liability_initial")
    accumulated = 0.0
    deposit = _float(initial, "security_deposit_pv")

    rows = []
    for n in range(1, term + 1):
        cash = net_cash[n - 1]
        interest = liability * monthly_rate
        principal = cash - interest  # negative while prepaid rent covers the month
        closing_liability = liability - principal
        closing_accumulated = accumulated + amortization
        closing_deposit = deposit * (1 + monthly_rate)
        rows.append(
            [
                n,
                _add_months(commencement, n - 1),
                rents[n - 1],
                cash,
                liability,
                interest,
                principal,
                closing_liability,
                rou_gross,
                accumulated,
                amortization,
                closing_accumulated,
                rou_gross - closing_accumulated,
                deposit,
                closing_deposit,
            ]
        )
        liability, accumulated, deposit = closing_liability, closing_accumulated, closing_deposit

    return pd.DataFrame(rows, columns=FINANCE_SCHEDULE_COLUMNS)


# --------------------------------------------------------------------------- #
# ASC 842 operating lease schedule (Section 9.3)
# --------------------------------------------------------------------------- #
_FINANCE_SCHEDULE_NEEDED = (
    "Period",
    "Date",
    "Escalated Contractual Rent",
    "Opening Liability",
    "Interest Expense",
    "Closing Liability",
)


def _check_finance_schedule(finance_schedule: pd.DataFrame, term: int) -> None:
    missing = [c for c in _FINANCE_SCHEDULE_NEEDED if c not in finance_schedule.columns]
    if missing:
        raise ValueError("'finance_schedule' is missing column(s): {}".format(", ".join(missing)))
    if finance_schedule["Period"].tolist() != list(range(1, term + 1)):
        raise ValueError(
            "'finance_schedule' must have exactly one row per period 1..{} (lease_term_months)".format(term)
        )


def compute_operating_summary(inputs: dict, initial: dict, finance_schedule: pd.DataFrame) -> dict:
    """The straight-line cost figures at the top of the Excel operating sheet (B6:B9).

    Returns:
        total_contractual_rent       sum of the finance schedule's "Escalated Contractual
                                     Rent" (same rent stream; includes prepaid-covered months)
        other_rou_components         idc + restoration_cost - incentives + security_deposit_discount
        total_straight_line_base     total_contractual_rent + other_rou_components
        single_lease_cost_per_month  total_straight_line_base / lease_term_months
                                     (IDENTICAL every month: a single straight-line cost)
    """
    p = _validate_inputs(inputs)
    _check_finance_schedule(finance_schedule, p["term"])
    if "security_deposit_discount" not in initial:
        raise ValueError("'initial' is missing: security_deposit_discount")

    total_contractual_rent = float(finance_schedule["Escalated Contractual Rent"].sum())
    other_rou_components = (
        p["idc"] + p["restoration_cost"] - p["incentives"] + _float(initial, "security_deposit_discount")
    )
    total_straight_line_base = total_contractual_rent + other_rou_components
    return {
        "total_contractual_rent": total_contractual_rent,
        "other_rou_components": other_rou_components,
        "total_straight_line_base": total_straight_line_base,
        "single_lease_cost_per_month": total_straight_line_base / p["term"],
    }


def build_operating_schedule(inputs: dict, initial: dict, finance_schedule: pd.DataFrame) -> pd.DataFrame:
    """ASC 842 OPERATING lease schedule (one row per period).

    A different mechanism from ``build_finance_schedule``: one constant
    straight-line ``Lease Cost`` each month, and the ROU asset is reduced directly by
    the balancing plug ``Lease Cost - Interest``. The liability accretes exactly as in
    the finance schedule, so Interest and both liability columns are taken from it.

    Columns are ``OPERATING_SCHEDULE_COLUMNS``. There is intentionally NO gross-cost or
    accumulated-amortization column - only ``ROU Net Carrying Value``.

    Note: ROU Net Carrying Value ends at ~0 only when ``prepaid_rent`` equals the
    escalated rent of the prepaid-covered months (the workbook's own tie-out check);
    otherwise the difference remains as a visible residual.
    """
    p = _validate_inputs(inputs)
    summary = compute_operating_summary(inputs, initial, finance_schedule)
    if "rou_asset_gross" not in initial:
        raise ValueError("'initial' is missing: rou_asset_gross")

    lease_cost = summary["single_lease_cost_per_month"]
    rou_net = _float(initial, "rou_asset_gross")

    periods = finance_schedule["Period"].tolist()
    dates = finance_schedule["Date"].tolist()
    interest = finance_schedule["Interest Expense"].astype(float).tolist()
    opening = finance_schedule["Opening Liability"].astype(float).tolist()
    closing = finance_schedule["Closing Liability"].astype(float).tolist()

    rows = []
    for n in range(p["term"]):
        plug = lease_cost - interest[n]
        rou_net = rou_net - plug
        rows.append([periods[n], dates[n], lease_cost, interest[n], plug, opening[n], closing[n], rou_net])

    return pd.DataFrame(rows, columns=OPERATING_SCHEDULE_COLUMNS)


# --------------------------------------------------------------------------- #
# Orchestration: classification-driven switching (Section 9.6)
# --------------------------------------------------------------------------- #
_CLASSIFICATION_KEYS = (
    "asset_economic_life_months",
    "asset_fair_value",
    "ownership_transfers",
    "bargain_purchase_option",
    "specialized_asset",
    "low_value_election",
)
_FULL_CALC_KEYS = _CALC_KEYS + ("commencement_date",) + _CLASSIFICATION_KEYS


def run_full_calculation(inputs: dict, asc842_override: str = None) -> dict:
    """Run the whole lease calculation and return one result dict.

    Pipeline: initial measurement -> classification -> finance schedule -> operating
    schedule (BOTH schedules are always built: Ind AS 116 always needs the finance-style
    schedule whatever ASC 842 says) -> Day-1 entries -> periodic entries for every
    period under both frameworks.

    (The initial measurement runs first because the ASC 842 "90% of fair value" test
    needs the lease liability, exactly as on the Excel Classification sheet.)

    ``inputs`` needs every key of ``compute_initial_measurement`` plus commencement_date,
    asset_economic_life_months, asset_fair_value, ownership_transfers,
    bargain_purchase_option, specialized_asset and low_value_election.
    ``lease_liability_initial`` is always COMPUTED here; any value supplied is ignored.

    Returns a dict with:
        initial             compute_initial_measurement() output
        classification      classify_lease() output
        rou_method          {"IND_AS_116": "gross_accum",
                             "ASC_842": "gross_accum" if FINANCE LEASE else "net_direct"}
                            (the Excel "Downstream Method Flag"); downstream UI/reporting
                            MUST branch on this
        finance_schedule    Ind AS 116 / ASC 842 Finance schedule (gross + accumulated amortization)
        operating_schedule  ASC 842 Operating schedule (single lease cost, net ROU only)
        operating_summary   straight-line cost figures
        schedules           {"IND_AS_116": finance_schedule,
                             "ASC_842": finance_schedule if gross_accum else operating_schedule}
        day1_entries        generate_day1_entries() output (three legs + cross-checks)
        periodic_entries    {"IND_AS_116": [...], "ASC_842": [...]}; each item is
                            {"period", "date", "entries"}. Ind AS 116 always uses the
                            finance template; ASC 842 follows the classification.
        totals              per framework: rou_method, total_interest, total_rou_reduction,
                            total_expense

    ``asc842_override`` ("FINANCE LEASE" or "OPERATING LEASE") replaces the ASC 842 result of
    the five tests; everything downstream (method flag, schedules, journal templates) then
    follows it. When it differs from what the tests gave, ``classification`` gains
    ``is_override=True`` and ``asc842_computed`` (the tests' own answer). Ind AS 116 is unaffected.

    Note: an Ind AS 116 recognition EXEMPTION (short-term / low-value) is reported in
    ``classification`` but the on-balance-sheet figures are still computed; the caller
    decides whether to recognise them.
    """
    # Imported here (not at module top) because journal_entries itself imports this module.
    from core.classification import classify_lease
    from core.journal_entries import (
        generate_day1_entries,
        generate_periodic_entry,
        period_row_from_schedules,
    )

    if asc842_override is not None and asc842_override not in ("FINANCE LEASE", "OPERATING LEASE"):
        raise ValueError(
            "asc842_override must be 'FINANCE LEASE' or 'OPERATING LEASE', got {!r}".format(asc842_override)
        )
    missing = [key for key in _FULL_CALC_KEYS if key not in inputs]
    if missing:
        raise ValueError("Missing required input(s): {}".format(", ".join(missing)))

    initial = compute_initial_measurement(inputs)
    classification = classify_lease({**inputs, "lease_liability_initial": initial["lease_liability_initial"]})
    if asc842_override is not None and asc842_override != classification["asc842_classification"]:
        classification = {
            **classification,
            "asc842_computed": classification["asc842_classification"],
            "asc842_classification": asc842_override,
            "is_override": True,
        }
    finance_schedule = build_finance_schedule(inputs, initial)
    operating_summary = compute_operating_summary(inputs, initial, finance_schedule)
    operating_schedule = build_operating_schedule(inputs, initial, finance_schedule)
    day1_entries = generate_day1_entries(inputs, initial)

    asc842_classification = classification["asc842_classification"]
    asc842_is_finance = asc842_classification == "FINANCE LEASE"
    rou_method = {
        "IND_AS_116": "gross_accum",  # Ind AS 116 always uses gross cost / accumulated amortization
        "ASC_842": "gross_accum" if asc842_is_finance else "net_direct",
    }
    asc842_schedule = finance_schedule if asc842_is_finance else operating_schedule

    periodic_entries = {"IND_AS_116": [], "ASC_842": []}
    for period in finance_schedule["Period"].tolist():
        row = period_row_from_schedules(period, finance_schedule, operating_schedule)
        for framework, label in (("IND_AS_116", "IND AS 116"), ("ASC_842", asc842_classification)):
            periodic_entries[framework].append(
                {"period": row["period"], "date": row["date"], "entries": generate_periodic_entry(row, label)}
            )

    finance_totals = {
        "total_interest": float(finance_schedule["Interest Expense"].sum()),
        "total_rou_reduction": float(finance_schedule["Amortization Expense"].sum()),
    }
    finance_totals["total_expense"] = finance_totals["total_interest"] + finance_totals["total_rou_reduction"]
    if asc842_is_finance:
        asc842_totals = dict(finance_totals)
    else:
        asc842_totals = {
            "total_interest": float(operating_schedule["Interest"].sum()),
            "total_rou_reduction": float(operating_schedule["ROU Reduction (plug)"].sum()),
            "total_expense": float(operating_schedule["Lease Cost"].sum()),
        }

    return {
        "initial": initial,
        "classification": classification,
        "rou_method": rou_method,
        "finance_schedule": finance_schedule,
        "operating_schedule": operating_schedule,
        "operating_summary": operating_summary,
        "schedules": {"IND_AS_116": finance_schedule, "ASC_842": asc842_schedule},
        "day1_entries": day1_entries,
        "periodic_entries": periodic_entries,
        "totals": {
            "IND_AS_116": {"rou_method": rou_method["IND_AS_116"], **finance_totals},
            "ASC_842": {"rou_method": rou_method["ASC_842"], **asc842_totals},
        },
    }
