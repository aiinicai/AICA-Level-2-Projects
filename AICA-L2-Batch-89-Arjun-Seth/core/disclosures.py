# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Disclosure notes: maturity analysis, weighted averages, ROU roll-forwards.

Replicates the Excel workbook's ``Disclosures`` sheet. Pure Python + pandas: no UI framework,
no database, no AI. Every figure is derived from the schedules the calculation engine
already produced, so the disclosures can never disagree with the schedules.

Two ROU roll-forward formats exist and are NEVER mixed:
* ``gross_accum`` (Ind AS 116, and ASC 842 finance leases): gross / accumulated amortization / net
* ``net_direct``  (ASC 842 operating leases): net carrying value only

Year tables cover lease years 1..ceil(term / 12) (the Excel pads to 20 years with zeros).
"""
import math

import pandas as pd

from core.formatting import DEFAULT_CURRENCY, DEFAULT_NUMBER_FORMAT, format_money

FINANCE_ROLLFORWARD_COLUMNS = [
    "Lease Year",
    "Gross Opening",
    "Additions",
    "Gross Closing",
    "Accum. Amort. Opening",
    "Amortization Charge",
    "Accum. Amort. Closing",
    "Net Carrying Value",
]
OPERATING_ROLLFORWARD_COLUMNS = [
    "Lease Year",
    "Net Opening",
    "Additions",
    "ROU Reduction (lease cost \u2212 interest)",
    "Net Closing",
]
ROLLFORWARD_METHODS = ("gross_accum", "net_direct")

# stored AmortizationSchedule column -> engine schedule column (see core/results.py)
_FINANCE_FROM_ROWS = {
    "period": "Period",
    "escalated_contractual_rent": "Escalated Contractual Rent",
    "net_cash_payment": "Net Cash Payment",
    "interest_expense": "Interest Expense",
    "amortization_expense": "Amortization Expense",
    "rou_net_carrying_value": "ROU Net Carrying Value",
}
_OPERATING_FROM_ROWS = {
    "period": "Period",
    "rou_reduction_plug": "ROU Reduction (plug)",
    "rou_net_carrying_value": "ROU Net Carrying Value",
}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _years(term_months: int) -> int:
    if isinstance(term_months, bool) or not isinstance(term_months, int) or term_months < 1:
        raise ValueError("term_months must be a whole number of at least 1, got {!r}".format(term_months))
    return math.ceil(term_months / 12)


def _yearly_sums(schedule: pd.DataFrame, column: str, term_months: int) -> list:
    """Sum ``column`` per lease year (periods 1-12 = year 1, ...). One value per year, zeros included."""
    for needed in ("Period", column):
        if needed not in schedule.columns:
            raise ValueError("The schedule is missing the '{}' column".format(needed))
    years = _years(term_months)
    if len(schedule) != term_months:
        raise ValueError(
            "The schedule has {} periods but the lease term is {} months".format(len(schedule), term_months)
        )
    sums = [0.0] * years
    for period, value in zip(schedule["Period"], schedule[column]):
        sums[(int(period) - 1) // 12] += float(value)
    return sums


def _label(year: int) -> str:
    return "Year {}".format(year)


# --------------------------------------------------------------------------- #
# maturity analysis
# --------------------------------------------------------------------------- #
def generate_maturity_analysis(schedule: pd.DataFrame, term_months: int) -> pd.DataFrame:
    """Undiscounted lease payments by lease year (columns: Year, Payments, Cumulative).

    Uses the 'Net Cash Payment' column: future payments only, so months already covered by
    prepaid rent (cash = 0) contribute nothing. The Payments column sums to the total
    undiscounted lease payments.
    """
    payments = _yearly_sums(schedule, "Net Cash Payment", term_months)
    cumulative, running = [], 0.0
    for amount in payments:
        running += amount
        cumulative.append(running)
    return pd.DataFrame(
        {
            "Year": [_label(year) for year in range(1, len(payments) + 1)],
            "Payments": payments,
            "Cumulative": cumulative,
        }
    )


# --------------------------------------------------------------------------- #
# ROU roll-forwards (two formats, never mixed)
# --------------------------------------------------------------------------- #
def generate_finance_rou_rollforward(schedule: pd.DataFrame, initial: dict, term_months: int) -> dict:
    """Gross / accumulated amortization / net roll-forward (Ind AS 116 and ASC 842 finance leases)."""
    charges = _yearly_sums(schedule, "Amortization Expense", term_months)
    gross = float(initial["rou_asset_gross"])
    rows, gross_opening, accumulated_opening = [], 0.0, 0.0
    for year, charge in enumerate(charges, start=1):
        additions = gross if year == 1 else 0.0
        gross_closing = gross_opening + additions
        accumulated_closing = accumulated_opening + charge
        rows.append(
            [
                _label(year),
                gross_opening,
                additions,
                gross_closing,
                accumulated_opening,
                charge,
                accumulated_closing,
                gross_closing - accumulated_closing,
            ]
        )
        gross_opening, accumulated_opening = gross_closing, accumulated_closing
    return {
        "rou_method": "gross_accum",
        "title": "ROU asset roll-forward - gross cost, accumulated amortization and net carrying value",
        "table": pd.DataFrame(rows, columns=FINANCE_ROLLFORWARD_COLUMNS),
        "closing_gross": gross_opening,
        "closing_accumulated": accumulated_opening,
        "closing_net": gross_opening - accumulated_opening,
    }


def generate_operating_rou_rollforward(schedule: pd.DataFrame, initial: dict, term_months: int) -> dict:
    """Net-only roll-forward (ASC 842 operating leases): no gross cost, no accumulated amortization."""
    reductions = _yearly_sums(schedule, "ROU Reduction (plug)", term_months)
    opening = 0.0
    rows = []
    for year, reduction in enumerate(reductions, start=1):
        additions = float(initial["rou_asset_gross"]) if year == 1 else 0.0
        closing = opening + additions - reduction
        rows.append([_label(year), opening, additions, reduction, closing])
        opening = closing
    return {
        "rou_method": "net_direct",
        "title": "ROU asset roll-forward - net carrying value only (operating lease)",
        "table": pd.DataFrame(rows, columns=OPERATING_ROLLFORWARD_COLUMNS),
        "closing_net": opening,
    }


def generate_rou_rollforward(rou_method: str, schedule: pd.DataFrame, initial: dict, term_months: int) -> dict:
    """The roll-forward for ``rou_method``: gross_accum -> finance format, net_direct -> operating format."""
    if rou_method == "gross_accum":
        return generate_finance_rou_rollforward(schedule, initial, term_months)
    if rou_method == "net_direct":
        return generate_operating_rou_rollforward(schedule, initial, term_months)
    raise ValueError("rou_method must be 'gross_accum' or 'net_direct', got {!r}".format(rou_method))


# --------------------------------------------------------------------------- #
# weighted averages
# --------------------------------------------------------------------------- #
def weighted_averages(leases: list) -> dict:
    """Portfolio weighted-average discount rate and remaining term, weighted by lease liability.

    ``leases``: list of {"liability", "annual_rate" (fraction), "remaining_months"}. For one lease the
    result is simply that lease's own rate and term. If the total liability is 0, leases are weighted equally.
    """
    if not leases:
        return {"weighted_average_discount_rate": 0.0, "weighted_average_remaining_months": 0.0,
                "weighted_average_remaining_years": 0.0, "lease_count": 0}
    weights = [float(lease["liability"]) for lease in leases]
    if sum(weights) <= 0:
        weights = [1.0] * len(leases)
    total = sum(weights)
    rate = sum(w * float(lease["annual_rate"]) for w, lease in zip(weights, leases)) / total
    months = sum(w * float(lease["remaining_months"]) for w, lease in zip(weights, leases)) / total
    return {
        "weighted_average_discount_rate": rate,
        "weighted_average_remaining_months": months,
        "weighted_average_remaining_years": months / 12,
        "lease_count": len(leases),
    }


# --------------------------------------------------------------------------- #
# the whole disclosure pack
# --------------------------------------------------------------------------- #
def draft_narrative(
    lease_ref, metrics: dict, currency: str = DEFAULT_CURRENCY, number_format: str = DEFAULT_NUMBER_FORMAT
) -> str:
    """A first-draft disclosure paragraph filled with this lease's figures (for professional review)."""
    def money(value):
        return format_money(value, currency, number_format)

    return (
        "Illustrative draft disclosure: The entity has recognised a right-of-use asset and a lease liability in "
        "respect of lease {ref}. The initial lease liability of {liability} is measured at the present value of net "
        "contractual lease payments (after payments covered by prepaid rent) using the specified discount rate of "
        "{rate:.2%} per year applied monthly (rate / 12). The right-of-use asset of {rou} includes the lease liability "
        "plus prepaid rent, initial direct costs and restoration amounts, less incentives, together with the "
        "security-deposit financing component. The maturity analysis presents undiscounted future lease payments of "
        "{undiscounted}. The weighted average remaining lease term is {months:.0f} months ({years:.1f} years). This "
        "text is a first draft for professional review and should be reconciled to the applicable reporting "
        "framework and the final validated lease data before external reporting."
    ).format(
        ref=lease_ref or "(unreferenced)",
        liability=money(metrics["initial_lease_liability"]),
        rate=metrics["weighted_average_discount_rate"],
        rou=money(metrics["initial_rou_asset"]),
        undiscounted=money(metrics["undiscounted_future_payments"]),
        months=metrics["weighted_average_remaining_months"],
        years=metrics["weighted_average_remaining_years"],
    )


def generate_disclosures(
    finance_schedule: pd.DataFrame,
    operating_schedule,
    initial: dict,
    annual_rate: float,
    term_months: int,
    asc842_rou_method: str,
    lease_ref=None,
    currency: str = DEFAULT_CURRENCY,
    number_format: str = DEFAULT_NUMBER_FORMAT,
) -> dict:
    """All disclosures for ONE lease.

    ``finance_schedule`` (engine columns) is always required: Ind AS 116 always uses it. The
    ``operating_schedule`` is only needed when ``asc842_rou_method`` is 'net_direct'.

    Returns {"maturity", "maturity_total", "key_metrics", "reconciliation", "rollforward",
    "rou_method", "narrative"} where ``rollforward`` holds one roll-forward per framework
    ("IND_AS_116" always gross_accum; "ASC_842" follows ``asc842_rou_method``).
    """
    if asc842_rou_method not in ROLLFORWARD_METHODS:
        raise ValueError("asc842_rou_method must be 'gross_accum' or 'net_direct', got {!r}".format(asc842_rou_method))
    if asc842_rou_method == "net_direct" and operating_schedule is None:
        raise ValueError("An operating schedule is required when the ASC 842 method is 'net_direct'")

    maturity = generate_maturity_analysis(finance_schedule, term_months)
    maturity_total = float(maturity["Payments"].sum())

    contractual = float(finance_schedule["Escalated Contractual Rent"].sum())
    undiscounted = float(finance_schedule["Net Cash Payment"].sum())
    imputed_interest = float(finance_schedule["Interest Expense"].sum())
    liability = float(initial["lease_liability_initial"])
    averages = weighted_averages([{"liability": liability, "annual_rate": annual_rate, "remaining_months": term_months}])

    rollforward = {
        "IND_AS_116": generate_finance_rou_rollforward(finance_schedule, initial, term_months),
        "ASC_842": generate_rou_rollforward(
            asc842_rou_method,
            finance_schedule if asc842_rou_method == "gross_accum" else operating_schedule,
            initial,
            term_months,
        ),
    }
    metrics = {
        "initial_lease_liability": liability,
        "initial_rou_asset": float(initial["rou_asset_gross"]),
        **averages,
        "total_contractual_rent": contractual,
        "prepaid_rent_already_paid": contractual - undiscounted,
        "undiscounted_future_payments": undiscounted,
        "imputed_interest": imputed_interest,
        "present_value_of_payments": undiscounted - imputed_interest,
        "maturity_ties_to_payments": abs(maturity_total - undiscounted) < 0.01,
        "liability_reconciles": abs((undiscounted - imputed_interest) - liability) < 0.01,
        "finance_rou_closing": float(finance_schedule["ROU Net Carrying Value"].iloc[-1]),
        # only meaningful (and only saved) when the ASC 842 view actually uses the operating method
        "operating_rou_closing": (
            float(operating_schedule["ROU Net Carrying Value"].iloc[-1])
            if operating_schedule is not None and asc842_rou_method == "net_direct"
            else None
        ),
        "asc842_rou_format": asc842_rou_method,
    }
    reconciliation = [
        {"Item": "Total contractual rent (undiscounted, all periods)", "Amount": contractual},
        {"Item": "Less: contractual rent for months covered by prepaid rent", "Amount": -(contractual - undiscounted)},
        {"Item": "Undiscounted future lease payments", "Amount": undiscounted},
        {"Item": "Less: imputed interest", "Amount": -imputed_interest},
        {"Item": "Present value of lease payments (= lease liability)", "Amount": undiscounted - imputed_interest},
    ]
    return {
        "maturity": maturity,
        "maturity_total": maturity_total,
        "key_metrics": metrics,
        "reconciliation": reconciliation,
        "rollforward": rollforward,
        "rou_method": {"IND_AS_116": "gross_accum", "ASC_842": asc842_rou_method},
        "narrative": draft_narrative(lease_ref, metrics, currency, number_format),
    }


def generate_disclosures_from_run(
    result: dict, lease_ref=None, currency: str = DEFAULT_CURRENCY, number_format: str = DEFAULT_NUMBER_FORMAT
) -> dict:
    """Disclosures straight from a ``run_full_calculation`` result."""
    finance = result["finance_schedule"]
    return generate_disclosures(
        finance,
        result["operating_schedule"],
        result["initial"],
        annual_rate=result["initial"]["monthly_rate"] * 12,
        term_months=len(finance),
        asc842_rou_method=result["rou_method"]["ASC_842"],
        lease_ref=lease_ref,
        currency=currency,
        number_format=number_format,
    )


def _frame(rows: list, mapping: dict) -> pd.DataFrame:
    return pd.DataFrame([{engine: row[stored] for stored, engine in mapping.items()} for row in rows])


def generate_disclosures_from_stored(stored: dict, number_format: str = DEFAULT_NUMBER_FORMAT) -> dict:
    """Disclosures from a lease's SAVED results (``core.workflow.get_stored_results``).

    Ind AS 116 rows are always the gross/accumulated schedule; the ASC 842 rows are only used
    (as the operating schedule) when the ASC 842 method is 'net_direct'.
    """
    calculation = stored["calculation"]
    ind_as_rows = stored["schedules"]["IND_AS_116"]["rows"]
    asc842 = stored["schedules"]["ASC_842"]
    method = asc842["rou_method"]
    operating = _frame(asc842["rows"], _OPERATING_FROM_ROWS) if method == "net_direct" else None
    return generate_disclosures(
        _frame(ind_as_rows, _FINANCE_FROM_ROWS),
        operating,
        {
            "lease_liability_initial": calculation["lease_liability_initial"],
            "rou_asset_gross": calculation["rou_asset_gross"],
        },
        annual_rate=calculation["monthly_rate"] * 12,
        term_months=len(ind_as_rows),
        asc842_rou_method=method,
        lease_ref=stored["case"]["lease_ref"],
        currency=stored["case"].get("currency") or DEFAULT_CURRENCY,
        number_format=number_format,
    )
