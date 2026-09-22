# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Dashboard numbers: KPI cards, donut counts, liability maturity.

Pure Python + pandas: no UI framework, no database. The rule that governs everything here:
**amounts are never added across currencies.** Every money figure is computed for ONE currency
(the caller selects it first); counts of leases (by status / classification) are just counts.

Month-end convention: a lease's schedule has one row per month; the balance "in September" is
the closing balance of the period that starts in September. A lease that has not started yet, or
has already ended, has no row for that month and contributes 0.
"""
from datetime import date

import pandas as pd

STATUS_ORDER = ("Draft", "Rejected", "Pending Review", "Approved", "Active", "Expired", "Terminated")
INCLUDE_VALIDATED = ("Pending Review", "Approved", "Active")  # leases whose numbers have been calculated
INCLUDE_APPROVED = ("Approved", "Active")
CLASSIFICATION_LABELS = {"OPERATING LEASE": "Operating lease", "FINANCE LEASE": "Finance lease"}
SCHEDULE_COLUMNS = ["case_id", "period_date", "month_index", "interest", "principal", "closing_liability", "rou_net", "cash", "expense"]


# --------------------------------------------------------------------------- #
# months
# --------------------------------------------------------------------------- #
def month_index(day: date) -> int:
    """Months since year 0: lets us compare and step through calendar months with plain integers."""
    return day.year * 12 + day.month - 1


def month_start(day: date) -> date:
    return date(day.year, day.month, 1)


def shift_month(day: date, months: int) -> date:
    """The first day of the month ``months`` after (or before, if negative) the month of ``day``."""
    index = month_index(day) + months
    return date(index // 12, index % 12 + 1, 1)


# --------------------------------------------------------------------------- #
# schedule data
# --------------------------------------------------------------------------- #
def prepare_schedule(rows: list) -> pd.DataFrame:
    """Stored AmortizationSchedule rows (dicts) -> a tidy table with the columns in SCHEDULE_COLUMNS.

    ``expense`` is the lease's cost for the month: the single straight-line cost for an operating
    (net_direct) row, otherwise interest + amortization.
    """
    records = []
    for row in rows:
        single = row.get("single_lease_cost")
        interest = float(row.get("interest_expense") or 0.0)
        expense = float(single) if single is not None else interest + float(row.get("amortization_expense") or 0.0)
        period_date = row["period_date"]
        records.append(
            {
                "case_id": row["case_id"],
                "period_date": period_date,
                "month_index": month_index(period_date),
                "interest": interest,
                "principal": float(row.get("principal_repayment") or 0.0),
                "closing_liability": float(row.get("closing_liability") or 0.0),
                "rou_net": float(row.get("rou_net_carrying_value") or 0.0),
                "cash": float(row.get("net_cash_payment") or 0.0),
                "expense": expense,
            }
        )
    return pd.DataFrame(records, columns=SCHEDULE_COLUMNS)


# --------------------------------------------------------------------------- #
# which leases
# --------------------------------------------------------------------------- #
def currency_options(leases: list) -> list:
    """[(currency, number of leases)], most leases first (ties: alphabetical). The dashboard's currency choices."""
    counts = {}
    for lease in leases:
        code = lease.get("currency") or "INR"
        counts[code] = counts.get(code, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def default_currency(options: list, preferred: str = "INR") -> str:
    """The user's preferred currency if they have leases in it, else the currency with the most leases."""
    codes = [code for code, _ in options]
    if preferred in codes:
        return preferred
    return codes[0] if codes else preferred


def leases_in_currency(leases: list, currency: str) -> list:
    return [lease for lease in leases if (lease.get("currency") or "INR") == currency]


def money_scope(leases: list, currency: str, statuses=INCLUDE_VALIDATED) -> list:
    """The leases that may contribute MONEY to the dashboard: this currency, calculated, in an included status."""
    return [
        lease
        for lease in leases_in_currency(leases, currency)
        if lease.get("has_results") and lease.get("status") in statuses
    ]


# --------------------------------------------------------------------------- #
# donut counts
# --------------------------------------------------------------------------- #
def status_counts(leases: list) -> list:
    """[(status, count)] for the statuses that occur, in lifecycle order."""
    counts = {}
    for lease in leases:
        counts[lease.get("status")] = counts.get(lease.get("status"), 0) + 1
    ordered = [(status, counts[status]) for status in STATUS_ORDER if status in counts]
    ordered += [(status, count) for status, count in counts.items() if status not in STATUS_ORDER]
    return ordered


def classification_counts(leases: list) -> list:
    """[('Operating lease', n), ('Finance lease', m)] for leases that have been classified (calculated)."""
    counts = {label: 0 for label in CLASSIFICATION_LABELS.values()}
    for lease in leases:
        label = CLASSIFICATION_LABELS.get(lease.get("classification"))
        if label:
            counts[label] += 1
    return [(label, count) for label, count in counts.items() if count]


# --------------------------------------------------------------------------- #
# KPI cards
# --------------------------------------------------------------------------- #
def month_snapshot(schedule: pd.DataFrame, case_ids, month: date) -> dict:
    """Sum of the month's figures over the given leases: {"liability", "rou_net", "expense"}."""
    rows = schedule[(schedule["month_index"] == month_index(month)) & (schedule["case_id"].isin(list(case_ids)))]
    return {
        "liability": float(rows["closing_liability"].sum()),
        "rou_net": float(rows["rou_net"].sum()),
        "expense": float(rows["expense"].sum()),
    }


def change_percent(current: float, previous: float):
    """Percentage change vs the previous month, or None when there is nothing to compare with."""
    if previous is None or abs(previous) < 1e-9:
        return None
    return (current - previous) / abs(previous) * 100.0


def trend(change) -> dict:
    """How to say a change: {"direction": up|down|flat|none, "arrow", "text"}."""
    if change is None:
        return {"direction": "none", "arrow": "", "text": "No earlier month to compare"}
    if abs(change) < 0.05:
        return {"direction": "flat", "arrow": "\u25ac", "text": "No change vs last month"}
    arrow, direction = ("\u25b2", "up") if change > 0 else ("\u25bc", "down")
    return {"direction": direction, "arrow": arrow, "text": "{:+.1f}% vs last month".format(change)}


def kpis(all_leases: list, currency: str, statuses, schedule: pd.DataFrame, today: date) -> dict:
    """The four KPI cards for ONE currency.

    ``schedule`` must contain only leases of that currency's money scope (see ``money_scope``). Returns
    counts for Total Leases (all statuses) and current / previous-month figures with % change for the
    liability, the net ROU asset and the monthly lease expense.
    """
    in_currency = leases_in_currency(all_leases, currency)
    scope = money_scope(all_leases, currency, statuses)
    case_ids = [lease["case_id"] for lease in scope]
    this_month, last_month = month_start(today), shift_month(today, -1)
    now, before = month_snapshot(schedule, case_ids, this_month), month_snapshot(schedule, case_ids, last_month)

    new_this_month = sum(
        1 for lease in in_currency if lease.get("created_at") and month_index(lease["created_at"].date()) == month_index(today)
    )
    result = {
        "currency": currency,
        "total_leases": len(in_currency),
        "new_this_month": new_this_month,
        "leases_in_other_currencies": len(all_leases) - len(in_currency),
        "leases_counted": len(scope),
        "month": this_month,
    }
    for key in ("liability", "rou_net", "expense"):
        change = change_percent(now[key], before[key])
        result[key] = {"value": now[key], "previous": before[key], "change_percent": change, "trend": trend(change)}
    return result


# --------------------------------------------------------------------------- #
# liability maturity
# --------------------------------------------------------------------------- #
def maturity_by_year(schedule: pd.DataFrame, case_ids, today: date, years: int = 5) -> list:
    """Undiscounted payments due in each of the next ``years`` 12-month windows (starting NEXT month).

    Returns [{"label": "Year 1", "range": "Oct 2026 - Sep 2027", "value": total}, ...] - zeros included.
    """
    first = month_index(shift_month(today, 1))
    rows = schedule[schedule["case_id"].isin(list(case_ids))]
    buckets = []
    for year in range(years):
        low, high = first + 12 * year, first + 12 * year + 11
        start, end = shift_month(today, 1 + 12 * year), shift_month(today, 12 + 12 * year)
        in_window = rows[(rows["month_index"] >= low) & (rows["month_index"] <= high)]
        buckets.append(
            {
                "label": "Year {}".format(year + 1),
                "range": "{} - {}".format(start.strftime("%b %Y"), end.strftime("%b %Y")),
                "value": float(in_window["cash"].sum()),
            }
        )
    return buckets


# --------------------------------------------------------------------------- #
# search box
# --------------------------------------------------------------------------- #
def search_leases(leases: list, text: str, limit: int = 6) -> list:
    """Leases whose ID, lessor or lessee contains ``text`` (ignoring case and extra spaces); newest first as given."""
    needle = " ".join(str(text or "").split()).casefold()
    if not needle:
        return []
    matches = [
        lease
        for lease in leases
        if any(needle in " ".join(str(lease.get(field) or "").split()).casefold() for field in ("lease_ref", "lessor", "lessee"))
    ]
    return matches[:limit]


# --------------------------------------------------------------------------- #
# Interest vs principal and future payments
# --------------------------------------------------------------------------- #
MONTHLY_COLUMNS = ["month", "interest", "principal", "cash"]
PAYMENT_WINDOWS = (12, 24, 60)  # the months choices of the Future Payments Overview


def monthly_portfolio(schedule: pd.DataFrame, case_ids, today: date, months: int = 60) -> pd.DataFrame:
    """Interest, principal repayment and cash payment summed by calendar month over the given leases, for the
    ``months`` months AFTER the current month (months with nothing due are kept as zeros).

    Columns: month (first day of the month), interest, principal, cash. Add only leases of ONE currency.
    """
    rows = schedule[schedule["case_id"].isin(list(case_ids))]
    totals = rows.groupby("month_index")[["interest", "principal", "cash"]].sum()
    records = []
    for step in range(1, months + 1):
        month = shift_month(today, step)
        index = month_index(month)
        if index in totals.index:
            line = totals.loc[index]
            records.append((month, float(line["interest"]), float(line["principal"]), float(line["cash"])))
        else:
            records.append((month, 0.0, 0.0, 0.0))
    return pd.DataFrame(records, columns=MONTHLY_COLUMNS)


def crossover_summary(monthly: pd.DataFrame) -> dict:
    """Where principal repayment overtakes interest. Read from the data, never forced.

    {"kind": "crosses", "month": date}  - principal was below interest and rises to (or above) it in ``month``
    {"kind": "principal_higher"}        - principal is already above interest from the start
    {"kind": "interest_higher"}         - interest stays above principal for the whole window
    {"kind": "none"}                    - no payments in the window
    """
    if monthly.empty or float(monthly["interest"].abs().sum() + monthly["principal"].abs().sum()) < 1e-9:
        return {"kind": "none"}
    gap = (monthly["principal"] - monthly["interest"]).tolist()
    if gap[0] >= 0:
        return {"kind": "principal_higher"}
    for position in range(1, len(gap)):
        if gap[position] >= 0:
            return {"kind": "crosses", "month": monthly["month"].iloc[position]}
    return {"kind": "interest_higher"}


def crossover_text(summary: dict) -> str:
    """The sentence that describes ``crossover_summary`` (used on the dashboard and in the exports)."""
    kind = summary["kind"]
    if kind == "crosses":
        return "Principal repayment overtakes interest in {}.".format(summary["month"].strftime("%B %Y"))
    if kind == "principal_higher":
        return "Principal repayment is above interest throughout this period, so the lines do not cross."
    if kind == "interest_higher":
        return "Interest stays above principal repayment for the whole period, so the lines do not cross yet."
    return "No payments fall in the next 60 months for the selected leases."


def future_payments(monthly: pd.DataFrame, months: int) -> dict:
    """The Future Payments Overview for the next ``months`` months (12, 24 or 60):
    {"total", "interest", "principal", "table"} where table has columns month, total, interest, principal."""
    window = monthly.head(months)
    table = pd.DataFrame(
        {
            "month": window["month"],
            "total": window["cash"],
            "interest": window["interest"],
            "principal": window["principal"],
        }
    ).reset_index(drop=True)
    return {
        "total": float(window["cash"].sum()),
        "interest": float(window["interest"].sum()),
        "principal": float(window["principal"].sum()),
        "table": table,
        "months": len(window),
    }


def recent_leases(leases: list, limit: int = 8) -> list:
    """The most recently created leases, newest first (the list is already newest first; ties broken by ID)."""
    ordered = sorted(leases, key=lambda lease: (lease.get("created_at") is not None, lease.get("created_at"), lease.get("case_id", 0)), reverse=True)
    return ordered[:limit]


def latest_calculated_lease(leases: list):
    """The newest lease that has calculation results (what 'Generate Disclosure Notes' / 'Memo' open), or None."""
    calculated = [lease for lease in recent_leases(leases, limit=len(leases)) if lease.get("has_results")]
    return calculated[0] if calculated else None
