# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Journal entry generation.

Replicates the Excel sheet ``Journal Entries`` of ``LeaseIQ_Pro_POC_corrected.xlsx``:

* ``generate_day1_entries``   -> the THREE separately balanced Day-1 legs (rows 4-29)
* ``generate_periodic_entry`` -> the classification-driven monthly entry (rows 42-61)
* ``period_row_from_schedules`` -> builds the "period_row" (Excel rows 32-40) from the
  finance / operating schedules

This part of the Excel was corrected twice after real balancing errors, so the legs
and templates below follow it line for line: do not "simplify" them.

RULE: pure Python only, no UI-framework imports. Amounts are unrounded floats (as in
Excel); round at export.
"""
import pandas as pd

from core.calculation_engine import _float, _non_negative  # shared input validators

# Stricter than the spec's 1-rupee tolerance: every entry is derived analytically and
# balances to floating-point precision, so a paisa-level gap would signal a real bug.
BALANCE_TOLERANCE = 0.01

_FINANCE_CLASSIFICATIONS = ("FINANCE LEASE", "IND AS 116", "IND_AS_116")
_OPERATING_CLASSIFICATIONS = ("OPERATING LEASE",)


def _line(account: str, debit: float = 0.0, credit: float = 0.0, narration: str = "") -> dict:
    return {"account": account, "debit": float(debit), "credit": float(credit), "narration": narration}


def _split(amount: float):
    """Signed amount -> (debit, credit): positive is a debit, negative a credit."""
    return (amount, 0.0) if amount >= 0 else (0.0, -amount)


def entry_totals(entries: list) -> tuple:
    """Return (total_debit, total_credit) of a list of journal lines."""
    return sum(e["debit"] for e in entries), sum(e["credit"] for e in entries)


def is_balanced(entries: list, tolerance: float = BALANCE_TOLERANCE) -> bool:
    """True if total debits equal total credits within ``tolerance``."""
    debit, credit = entry_totals(entries)
    return abs(debit - credit) <= tolerance


def _leg(title: str, entries: list) -> dict:
    debit, credit = entry_totals(entries)
    return {
        "title": title,
        "entries": entries,
        "total_debit": debit,
        "total_credit": credit,
        "is_balanced": abs(debit - credit) <= BALANCE_TOLERANCE,
    }


# --------------------------------------------------------------------------- #
# Day-1 entries: three separately balanced legs
# --------------------------------------------------------------------------- #
def generate_day1_entries(inputs: dict, initial: dict) -> dict:
    """The three Day-1 legs plus the two Excel cross-checks.

    ``inputs`` needs: prepaid_rent, idc, incentives, restoration_cost, deposit.
    ``initial`` (from ``compute_initial_measurement``) needs: lease_liability_initial,
    security_deposit_pv, security_deposit_discount, rou_asset_gross.

    Returns ``{"leg_a": leg, "leg_b": leg, "leg_c": leg, "cross_checks": [...]}`` where
    each leg is ``{title, entries, total_debit, total_credit, is_balanced}`` and each
    entry is ``{account, debit, credit, narration}``.

    Leg A  recognise liability and ROU asset (EXCLUDES the deposit)
    Leg B  pay the security deposit at full nominal value
    Leg C  same-day remeasurement of the deposit to present value
    """
    missing = [k for k in ("prepaid_rent", "idc", "incentives", "restoration_cost", "deposit") if k not in inputs]
    missing += [
        k
        for k in ("lease_liability_initial", "security_deposit_pv", "security_deposit_discount", "rou_asset_gross")
        if k not in initial
    ]
    if missing:
        raise ValueError("Missing required input(s): {}".format(", ".join(missing)))

    prepaid = _non_negative(inputs, "prepaid_rent")
    idc = _non_negative(inputs, "idc")
    incentives = _non_negative(inputs, "incentives")
    restoration = _non_negative(inputs, "restoration_cost")
    deposit = _non_negative(inputs, "deposit")
    liability = _non_negative(initial, "lease_liability_initial")
    deposit_discount = _non_negative(initial, "security_deposit_discount")

    rou_leg_a = liability + prepaid + idc + restoration - incentives
    leg_a = _leg(
        "Day 1 - Leg A: Recognize Lease Liability and ROU Asset (excludes deposit)",
        [
            _line(
                "Right-of-Use Asset",
                debit=rou_leg_a,
                narration="Liability + prepaid rent + IDC + restoration \u2212 incentives (excludes deposit discount)",
            ),
            _line("Lease Liability", credit=liability, narration="PV of net cash payments"),
            _line("Cash / Bank \u2013 Prepaid Rent", credit=prepaid, narration="Advance rent"),
            _line("Cash / Bank \u2013 Initial Direct Costs", credit=idc, narration="Initial direct costs"),
            _line("Asset Retirement / Restoration Obligation", credit=restoration, narration="Restoration obligation"),
            _line(
                "Cash / Bank \u2013 Lease Incentive Received",
                debit=incentives,
                narration=(
                    "Incentive received from lessor (nil in the illustrative lease); "
                    "keeps Leg A balanced when incentives > 0"
                ),
            ),
        ],
    )
    leg_b = _leg(
        "Day 1 - Leg B: Pay Security Deposit at full nominal value",
        [
            _line("Security Deposit Receivable", debit=deposit, narration="Deposit paid, recorded at nominal"),
            _line("Cash / Bank \u2013 Security Deposit", credit=deposit, narration="Cash payment of deposit"),
        ],
    )
    leg_c = _leg(
        "Day 1 - Leg C: Same-day remeasurement of deposit to present value",
        [
            _line(
                "Right-of-Use Asset (financing component)",
                debit=deposit_discount,
                narration="Deposit discount capitalised into ROU",
            ),
            _line(
                "Security Deposit Receivable",
                credit=deposit_discount,
                narration="Deposit remeasured from nominal to PV",
            ),
        ],
    )

    rou_computed = leg_a["entries"][0]["debit"] + leg_c["entries"][0]["debit"]
    deposit_computed = leg_b["entries"][0]["debit"] - leg_c["entries"][1]["credit"]
    cross_checks = [
        {
            "check": "Leg A ROU debit + Leg C ROU debit = rou_asset_gross",
            "computed": rou_computed,
            "expected": _float(initial, "rou_asset_gross"),
        },
        {
            "check": "Leg B deposit debit \u2212 Leg C deposit credit = security_deposit_pv",
            "computed": deposit_computed,
            "expected": _float(initial, "security_deposit_pv"),
        },
    ]
    for check in cross_checks:
        check["passed"] = abs(check["computed"] - check["expected"]) < BALANCE_TOLERANCE

    return {"leg_a": leg_a, "leg_b": leg_b, "leg_c": leg_c, "cross_checks": cross_checks}


# --------------------------------------------------------------------------- #
# Periodic entries: branch on classification
# --------------------------------------------------------------------------- #
def period_row_from_schedules(
    period: int, finance_schedule: pd.DataFrame, operating_schedule: pd.DataFrame = None
) -> dict:
    """Build the ``period_row`` dict (the Excel's INDEX/MATCH block, rows 34-40).

    Keys: period, date, net_cash_payment, interest_expense, rou_amortization,
    deposit_accretion (= deposit closing - opening) and, when ``operating_schedule`` is
    given, single_lease_cost and rou_reduction_plug.
    """
    matches = finance_schedule[finance_schedule["Period"] == period]
    if matches.empty:
        raise ValueError("Period {!r} not found in the finance schedule".format(period))
    fin = matches.iloc[0]
    row = {
        "period": int(period),
        "date": fin["Date"],
        "net_cash_payment": float(fin["Net Cash Payment"]),
        "interest_expense": float(fin["Interest Expense"]),
        "rou_amortization": float(fin["Amortization Expense"]),
        "deposit_accretion": float(fin["Security Deposit Closing"]) - float(fin["Security Deposit Opening (PV)"]),
    }
    if operating_schedule is not None:
        op_matches = operating_schedule[operating_schedule["Period"] == period]
        if op_matches.empty:
            raise ValueError("Period {!r} not found in the operating schedule".format(period))
        op = op_matches.iloc[0]
        row["single_lease_cost"] = float(op["Lease Cost"])
        row["rou_reduction_plug"] = float(op["ROU Reduction (plug)"])
    return row


def generate_periodic_entry(period_row: dict, classification: str) -> list:
    """The monthly journal entry for one period, as a list of {account, debit, credit, narration}.

    ``classification``: "FINANCE LEASE" (or "IND AS 116") uses the gross / accumulated
    amortization template; "OPERATING LEASE" uses the single-cost, direct-ROU-reduction
    template. Anything else raises ValueError.

    ``period_row`` keys - both templates: net_cash_payment, interest_expense,
    deposit_accretion; finance also rou_amortization; operating also single_lease_cost and
    rou_reduction_plug. Principal = cash - interest; when negative (prepaid months, cash = 0)
    it is posted as a CREDIT to Lease Liability (accretion) in both templates.
    """
    label = classification.strip().upper() if isinstance(classification, str) else None
    if label in _FINANCE_CLASSIFICATIONS:
        finance = True
    elif label in _OPERATING_CLASSIFICATIONS:
        finance = False
    else:
        raise ValueError(
            "classification must be 'FINANCE LEASE', 'IND AS 116' or 'OPERATING LEASE', got {!r}".format(classification)
        )

    needed = ["net_cash_payment", "interest_expense", "deposit_accretion"]
    needed += ["rou_amortization"] if finance else ["single_lease_cost", "rou_reduction_plug"]
    missing = [k for k in needed if k not in period_row]
    if missing:
        raise ValueError("period_row is missing: {}".format(", ".join(missing)))

    cash = _non_negative(period_row, "net_cash_payment")
    interest = _non_negative(period_row, "interest_expense")
    accretion = _non_negative(period_row, "deposit_accretion")
    principal = cash - interest  # negative in prepaid months
    liability_debit, liability_credit = _split(principal)

    liability_line = _line(
        "Lease Liability",
        debit=liability_debit,
        credit=liability_credit,
        narration=(
            "Principal reduction (Dr) / accretion in prepaid months (Cr)"
            if finance
            else "Principal reduction (Dr) / accretion in prepaid months (Cr) \u2013 same liability mechanics as finance path"
        ),
    )
    deposit_lines = [
        _line("Security Deposit Receivable", debit=accretion, narration="Accretion of deposit discount"),
        _line("Interest Income \u2013 Security Deposit", credit=accretion, narration="Financing income on deposit"),
    ]

    if finance:
        amortization = _non_negative(period_row, "rou_amortization")
        return [
            _line("Interest Expense", debit=interest, narration="Interest on lease liability"),
            liability_line,
            _line("Cash / Bank", credit=cash, narration="Monthly lease payment (net of prepaid months)"),
            _line("Amortization Expense \u2013 ROU Asset", debit=amortization, narration="Straight-line ROU amortization"),
            _line(
                "Accumulated Amortization \u2013 ROU Asset",
                credit=amortization,
                narration="Contra-asset credit (never credit the ROU asset directly here)",
            ),
            *deposit_lines,
        ]

    lease_cost = _non_negative(period_row, "single_lease_cost")
    plug = _float(period_row, "rou_reduction_plug")
    rou_debit, rou_credit = _split(-plug)  # normally a credit; a negative plug is posted as a debit
    return [
        _line("Lease Expense", debit=lease_cost, narration="Single straight-line lease cost"),
        liability_line,
        _line("Cash / Bank", credit=cash, narration="Cash paid in the period"),
        _line(
            "Right-of-Use Asset (direct reduction)",
            debit=rou_debit,
            credit=rou_credit,
            narration="Direct ROU reduction = lease cost \u2212 interest; NO accumulated amortization account",
        ),
        *deposit_lines,
    ]
