# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""The dashboard as a REPORT: every figure the Excel and PDF exports contain, in one structure.

Pure Python + pandas. It is built from the very same functions the dashboard screen uses
(``core.dashboard``), so an exported file can never disagree with what the user sees. Everything is for ONE
currency: amounts are never added across currencies. Recent Leases is deliberately not part of it.
"""
from datetime import date, datetime

from core import dashboard as dash
from core.formatting import CURRENCIES, NUMBER_FORMATS, currency_decimals, currency_label, format_number, parse_currency

REPORT_TITLE = "LeaseIQ Pro - Portfolio Dashboard Report"
# Colours used in the exported charts (hex without '#'). They mirror the dashboard's light palette.
COLORS = {
    "navy": "0F1B3D",
    "blue": "2F80ED",
    "green": "27AE60",
    "purple": "8B5CF6",
    "orange": "F2994A",
    "interest": "D9770E",
    "principal": "2F80ED",
    "muted": "5B6577",
    "line": "D0D7E2",
    "zebra": "F5F7FA",
    "band": "E6EBF5",
}
STATUS_HEX = {
    "Draft": "9AA5B1", "Rejected": "D9480F", "Pending Review": "F2B233", "Approved": "27AE60",
    "Active": "2F80ED", "Expired": "B0B7C3", "Terminated": "E5534B",
}
CLASSIFICATION_HEX = {"Operating lease": "2F80ED", "Finance lease": "8B5CF6"}


def _shares(pairs: list) -> tuple:
    total = sum(count for _, count in pairs)
    return [
        {"label": label, "count": count, "percent": (count / total * 100.0) if total else 0.0} for label, count in pairs
    ], total


def build_report(
    leases: list,
    schedule,
    currency: str,
    statuses,
    include_label: str,
    framework_label: str,
    number_style: str,
    today: date,
    prepared_by: str = "",
    generated_at: datetime = None,
) -> dict:
    """Assemble the report for ONE currency.

    ``leases``: the dashboard's lease list (``core.workflow.get_dashboard_leases``); ``schedule``: the prepared
    schedule for the chosen reporting view (``core.dashboard.prepare_schedule``); ``statuses``: which lease statuses
    add up (``INCLUDE_VALIDATED`` or ``INCLUDE_APPROVED``); ``include_label`` / ``framework_label``: the wording the
    user sees for those two choices.
    """
    code = parse_currency(currency) or str(currency).strip().upper()
    generated_at = generated_at or datetime.now()
    in_currency = dash.leases_in_currency(leases, code)
    scope = dash.money_scope(leases, code, statuses)
    case_ids = [lease["case_id"] for lease in scope]
    metrics = dash.kpis(leases, code, statuses, schedule, today)
    monthly = dash.monthly_portfolio(schedule, case_ids, today, 60)
    crossover = dash.crossover_summary(monthly)

    kpis = [
        {
            "key": "total_leases", "label": "Total Leases", "kind": "count", "value": metrics["total_leases"],
            "previous": None, "change_percent": None,
            "note": "{} new this month".format(metrics["new_this_month"]) if metrics["new_this_month"] else "",
        }
    ]
    for key, label in (("liability", "Total Lease Liability"), ("rou_net", "ROU Asset (Net)"), ("expense", "Monthly Lease Expense")):
        item = metrics[key]
        kpis.append(
            {
                "key": key, "label": label, "kind": "money", "value": item["value"], "previous": item["previous"],
                "change_percent": item["change_percent"], "note": item["trend"]["text"],
            }
        )

    status, status_total = _shares(dash.status_counts(in_currency))
    classification, classification_total = _shares(dash.classification_counts(in_currency))
    maturity = dash.maturity_by_year(schedule, case_ids, today)
    payments = []
    for months in dash.PAYMENT_WINDOWS:
        window = dash.future_payments(monthly, months)
        split = window["interest"] + window["principal"]
        payments.append(
            {
                "months": months,
                "label": "Next {} months".format(months),
                "total": window["total"],
                "interest": window["interest"],
                "principal": window["principal"],
                "interest_share": window["interest"] / split if split else 0.0,
                "principal_share": window["principal"] / split if split else 0.0,
            }
        )

    month_label = metrics["month"].strftime("%B %Y")
    other = metrics["leases_in_other_currencies"]
    currency_name = "{} - {}".format(code, CURRENCIES[code][0]) if code in CURRENCIES else code
    notes = [
        "All amounts are in {}. Amounts in other currencies are never added to these figures{}.".format(
            currency_name, " ({} lease{} in other currencies are not included)".format(other, "" if other == 1 else "s") if other else ""
        ),
        "Balances (liability, net ROU asset) and the monthly expense are month-end figures for {}. A lease that has not started, "
        "or has ended, contributes 0.".format(month_label),
        "Leases included in the amounts: {}. Reporting view: {}. {} lease{} counted.".format(
            include_label, framework_label, len(scope), "" if len(scope) == 1 else "s"
        ),
        "Change is measured against the previous month; 'No earlier month to compare' means the previous month was zero.",
        "Lease liability maturity shows undiscounted payments due in each 12-month window, starting with the month after {}.".format(month_label),
        "Interest, principal repayment and payments are portfolio totals for the 60 months after {}. In every month the total "
        "payment equals interest plus principal repayment. A negative principal repayment means interest accrued in a month "
        "with no payment (for example while rent is prepaid).".format(month_label),
        "Number format: {}. Figures are values exported from LeaseIQ Pro at the time of generation; they do not recalculate.".format(
            NUMBER_FORMATS.get(number_style, number_style)
        ),
    ]
    return {
        "title": REPORT_TITLE,
        "generated_at": generated_at,
        "prepared_by": prepared_by,
        "currency": code,
        "currency_label": currency_label(code),
        "currency_name": currency_name,  # no symbol: safe in any PDF font
        "symbol": CURRENCIES[code][1] if code in CURRENCIES else code,
        "decimals": currency_decimals(code),
        "number_style": number_style,
        "number_format_label": NUMBER_FORMATS.get(number_style, number_style),
        "include_label": include_label,
        "framework_label": framework_label,
        "month": metrics["month"],
        "month_label": month_label,
        "leases_counted": len(scope),
        "total_leases": metrics["total_leases"],
        "leases_in_other_currencies": other,
        "kpis": kpis,
        "status": status,
        "status_total": status_total,
        "classification": classification,
        "classification_total": classification_total,
        "maturity": maturity,
        "maturity_total": sum(bucket["value"] for bucket in maturity),
        "monthly": monthly,
        "monthly_totals": {
            "interest": float(monthly["interest"].sum()),
            "principal": float(monthly["principal"].sum()),
            "cash": float(monthly["cash"].sum()),
        },
        "crossover": crossover,
        "crossover_text": dash.crossover_text(crossover),
        "payments": payments,
        "notes": notes,
    }


def money_text(value, report: dict) -> str:
    """'INR 50,79,693.73': the currency CODE and the amount in the user's number format (works in any font)."""
    return "{} {}".format(report["currency"], format_number(value, report["number_style"], report["decimals"]))


def number_text(value, report: dict) -> str:
    """The amount alone, in the user's number format and the currency's decimals."""
    return format_number(value, report["number_style"], report["decimals"])


def file_stem(report: dict) -> str:
    """'LeaseIQ_Dashboard_INR_2026-09' - the name (without extension) both exports are saved under."""
    return "LeaseIQ_Dashboard_{}_{}".format(report["currency"], report["month"].strftime("%Y-%m"))
