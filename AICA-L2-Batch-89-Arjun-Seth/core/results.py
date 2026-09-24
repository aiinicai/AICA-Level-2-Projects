# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Turning calculation results into database rows, and stored rows into display tables.

Pure Python + pandas: no UI framework, no database session. ``core/workflow.py`` does the
saving; keeping the row-building logic here makes it testable without a database.
"""
import json
from datetime import date

import pandas as pd

from core.formatting import format_money
from core.journal_entries import is_balanced

FRAMEWORKS = ("IND_AS_116", "ASC_842")
FRAMEWORK_LABELS = {"IND_AS_116": "Ind AS 116", "ASC_842": "ASC 842"}

# finance-schedule column -> AmortizationSchedule column
_FINANCE_COLUMNS = {
    "Escalated Contractual Rent": "escalated_contractual_rent",
    "Net Cash Payment": "net_cash_payment",
    "Opening Liability": "opening_liability",
    "Interest Expense": "interest_expense",
    "Principal Repayment": "principal_repayment",
    "Closing Liability": "closing_liability",
    "ROU Gross Cost (constant)": "rou_gross_cost",
    "Accum. Amortization Opening": "accum_amortization_opening",
    "Amortization Expense": "amortization_expense",
    "Accum. Amortization Closing": "accum_amortization_closing",
    "ROU Net Carrying Value": "rou_net_carrying_value",
    "Security Deposit Opening (PV)": "security_deposit_opening",
    "Security Deposit Closing": "security_deposit_closing",
}


# --------------------------------------------------------------------------- #
# Building rows to save
# --------------------------------------------------------------------------- #
def calculation_row(result: dict, inputs: dict, engine_version: str) -> dict:
    """Columns of one CalculationResult row (without case_id)."""
    initial, summary = result["initial"], result["operating_summary"]
    finance = result["finance_schedule"]
    inputs_json = json.dumps({k: (v.isoformat() if isinstance(v, date) else v) for k, v in inputs.items()})
    return {
        "inputs_json": inputs_json,
        "monthly_rate": float(initial["monthly_rate"]),
        "lease_liability_initial": float(initial["lease_liability_initial"]),
        "security_deposit_pv": float(initial["security_deposit_pv"]),
        "security_deposit_discount": float(initial["security_deposit_discount"]),
        "rou_asset_gross": float(initial["rou_asset_gross"]),
        "total_contractual_rent": float(summary["total_contractual_rent"]),
        "other_rou_components": float(summary["other_rou_components"]),
        "total_straight_line_base": float(summary["total_straight_line_base"]),
        "single_lease_cost_per_month": float(summary["single_lease_cost_per_month"]),
        "total_interest_expense": float(result["totals"]["IND_AS_116"]["total_interest"]),
        "total_undiscounted_payments": float(finance["Net Cash Payment"].sum()),
        "engine_version": engine_version,
    }


def classification_row(result: dict) -> dict:
    """Columns of one ClassificationResult row (without case_id)."""
    classification = result["classification"]
    return {
        "asc842_classification": classification["asc842_classification"],
        "asc842_test_results_json": json.dumps(classification["asc842_test_results"]),
        "ind_as116_exemption": classification["ind_as116_exemption"],
        "ind_as116_rationale": classification["ind_as116_rationale"],
        "rou_method": result["rou_method"]["ASC_842"],
        "is_override": bool(classification.get("is_override", False)),
    }


def schedule_rows(result: dict) -> list:
    """AmortizationSchedule rows (without case_id) for BOTH frameworks.

    Ind AS 116 always uses the finance schedule (gross_accum). ASC 842 uses the finance
    schedule for a FINANCE LEASE, otherwise the operating schedule (net_direct). The
    operating rows borrow the rent / cash / deposit columns from the finance schedule
    (same rent stream) so every row is complete.
    """
    finance = result["finance_schedule"]
    operating = result["operating_schedule"]

    def finance_row(framework: str, index: int) -> dict:
        source = finance.iloc[index]
        row = {"framework": framework, "rou_method": "gross_accum", "period": int(source["Period"]), "period_date": source["Date"]}
        for column, field in _FINANCE_COLUMNS.items():
            row[field] = float(source[column])
        row["single_lease_cost"] = None
        row["rou_reduction_plug"] = None
        return row

    def operating_row(index: int) -> dict:
        op, fin = operating.iloc[index], finance.iloc[index]
        return {
            "framework": "ASC_842",
            "rou_method": "net_direct",
            "period": int(op["Period"]),
            "period_date": op["Date"],
            "escalated_contractual_rent": float(fin["Escalated Contractual Rent"]),
            "net_cash_payment": float(fin["Net Cash Payment"]),
            "opening_liability": float(op["Opening Liability"]),
            "interest_expense": float(op["Interest"]),
            "principal_repayment": float(fin["Principal Repayment"]),
            "closing_liability": float(op["Closing Liability"]),
            "rou_gross_cost": None,
            "accum_amortization_opening": None,
            "amortization_expense": None,
            "accum_amortization_closing": None,
            "single_lease_cost": float(op["Lease Cost"]),
            "rou_reduction_plug": float(op["ROU Reduction (plug)"]),
            "rou_net_carrying_value": float(op["ROU Net Carrying Value"]),
            "security_deposit_opening": float(fin["Security Deposit Opening (PV)"]),
            "security_deposit_closing": float(fin["Security Deposit Closing"]),
        }

    count = len(finance)
    rows = [finance_row("IND_AS_116", i) for i in range(count)]
    if result["rou_method"]["ASC_842"] == "gross_accum":
        rows += [finance_row("ASC_842", i) for i in range(count)]
    else:
        rows += [operating_row(i) for i in range(count)]
    return rows


def journal_rows(result: dict, day1_date: date) -> list:
    """JournalEntry rows (without case_id): Day-1 legs A/B/C, then every periodic entry, both frameworks."""
    rows = []
    for letter, key in (("A", "leg_a"), ("B", "leg_b"), ("C", "leg_c")):
        leg = result["day1_entries"][key]
        for number, entry in enumerate(leg["entries"], start=1):
            rows.append(
                {
                    "entry_type": "DAY1",
                    "leg": letter,
                    "framework": None,
                    "period_number": None,
                    "entry_date": day1_date,
                    "line_no": number,
                    "account": entry["account"],
                    "debit": float(entry["debit"]),
                    "credit": float(entry["credit"]),
                    "narration": entry["narration"],
                    "is_balanced": bool(leg["is_balanced"]),
                }
            )
    for framework in FRAMEWORKS:
        for item in result["periodic_entries"][framework]:
            balanced = is_balanced(item["entries"])
            for number, entry in enumerate(item["entries"], start=1):
                rows.append(
                    {
                        "entry_type": "PERIODIC",
                        "leg": None,
                        "framework": framework,
                        "period_number": int(item["period"]),
                        "entry_date": item["date"],
                        "line_no": number,
                        "account": entry["account"],
                        "debit": float(entry["debit"]),
                        "credit": float(entry["credit"]),
                        "narration": entry["narration"],
                        "is_balanced": bool(balanced),
                    }
                )
    return rows


def group_journal(rows: list) -> dict:
    """Stored journal rows (dicts) -> {"day1": {"A": [lines], ...}, "periodic": {framework: {period: [lines]}}}."""
    grouped = {"day1": {"A": [], "B": [], "C": []}, "periodic": {fw: {} for fw in FRAMEWORKS}}
    for row in sorted(rows, key=lambda r: (r["line_no"],)):
        line = {k: row[k] for k in ("account", "debit", "credit", "narration")}
        if row["entry_type"] == "DAY1":
            grouped["day1"][row["leg"]].append(line)
        else:
            grouped["periodic"][row["framework"]].setdefault(row["period_number"], []).append(line)
    return grouped


# --------------------------------------------------------------------------- #
# Formatting for display
# --------------------------------------------------------------------------- #
def format_inr(value, symbol: str = "\u20b9") -> str:
    """Indian grouping in rupees: 5079693.73 -> '\u20b9 50,79,693.73' (kept for older callers;
    new code uses ``core.formatting.format_money`` with the lease's currency and the user's format)."""
    return format_money(value, "INR", "indian")


def format_tests(tests: list) -> list:
    """The five ASC 842 tests as display rows: Test / Computed / Threshold / Met (ratios as %)."""
    rows = []
    for test in tests:
        computed, threshold = test["computed_value"], test["threshold"]
        if isinstance(threshold, float):  # ratio tests
            computed_text, threshold_text = "{:.1f}%".format(computed * 100), "{:.0f}%".format(threshold * 100)
        else:
            computed_text, threshold_text = str(computed), str(threshold)
        rows.append(
            {
                "Test": test["test"],
                "Computed": computed_text,
                "Threshold": threshold_text,
                "Met": "Yes" if test["met"] == "Y" else "No",
            }
        )
    return rows


_DISPLAY = {
    "gross_accum": [
        ("period", "Period"),
        ("period_date", "Date"),
        ("escalated_contractual_rent", "Contract rent"),
        ("net_cash_payment", "Cash payment"),
        ("opening_liability", "Opening liability"),
        ("interest_expense", "Interest"),
        ("principal_repayment", "Principal"),
        ("closing_liability", "Closing liability"),
        ("amortization_expense", "Amortization"),
        ("accum_amortization_closing", "Accum. amortization"),
        ("rou_net_carrying_value", "ROU net value"),
        ("security_deposit_closing", "Deposit"),
    ],
    "net_direct": [
        ("period", "Period"),
        ("period_date", "Date"),
        ("net_cash_payment", "Cash payment"),
        ("opening_liability", "Opening liability"),
        ("interest_expense", "Interest"),
        ("single_lease_cost", "Lease cost"),
        ("rou_reduction_plug", "ROU reduction"),
        ("closing_liability", "Closing liability"),
        ("rou_net_carrying_value", "ROU net value"),
        ("security_deposit_closing", "Deposit"),
    ],
}


def schedule_frame(rows: list, rou_method: str) -> pd.DataFrame:
    """Stored schedule rows -> a tidy table (2 decimals, dates as text) for the screen."""
    columns = _DISPLAY[rou_method]
    frame = pd.DataFrame([{label: row[field] for field, label in columns} for row in rows], columns=[l for _, l in columns])
    if "Date" in frame:
        frame["Date"] = frame["Date"].astype(str)
    numeric = [label for _, label in columns if label not in ("Period", "Date")]
    frame[numeric] = frame[numeric].astype(float).round(2)
    return frame


def journal_frame(lines: list) -> pd.DataFrame:
    """Journal lines -> a table with Account / Debit / Credit / Narration."""
    frame = pd.DataFrame(lines, columns=["account", "debit", "credit", "narration"])
    frame = frame.rename(columns={"account": "Account", "debit": "Debit", "credit": "Credit", "narration": "Narration"})
    frame[["Debit", "Credit"]] = frame[["Debit", "Credit"]].astype(float).round(2)
    return frame
