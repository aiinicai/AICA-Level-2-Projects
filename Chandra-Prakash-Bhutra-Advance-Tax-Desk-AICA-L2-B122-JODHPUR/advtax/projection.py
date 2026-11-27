"""Project year-to-date business profit to a full-year taxable figure."""
from __future__ import annotations

from datetime import date


def project_business(
    recurring_income: float,
    recurring_expense: float,
    one_off_income: float = 0.0,
    one_off_expense: float = 0.0,
    opening_stock: float = 0.0,
    closing_stock: float = 0.0,
    period_start: date = date(2026, 4, 1),
    as_on: date = date(2026, 11, 30),
    period_end: date = date(2027, 3, 31),
    add_backs: float = 0.0,
    less_deductions: float = 0.0,
    growth_pct: float = 0.0,
) -> dict:
    """Straight-line projection.

    Recurring profit to date is scaled to the full year (with an optional
    growth/seasonality percentage for the remaining months). One-off items are
    taken once. add_backs and less_deductions are full-year amounts
    (disallowances, tax depreciation difference, partner remuneration, etc.).
    """
    days_done = max(1, (as_on - period_start).days + 1)
    days_total = (period_end - period_start).days + 1
    days_done = min(days_done, days_total)
    ytd_recurring = recurring_income - recurring_expense - opening_stock + closing_stock
    daily = ytd_recurring / days_done
    remaining = daily * (days_total - days_done) * (1 + growth_pct / 100.0)
    one_off = one_off_income - one_off_expense
    book_profit = ytd_recurring + remaining + one_off
    taxable = book_profit + add_backs - less_deductions
    return {
        "days_done": days_done,
        "days_total": days_total,
        "ytd_recurring_profit": round(ytd_recurring),
        "ytd_profit": round(ytd_recurring + one_off),
        "projected_remaining_profit": round(remaining),
        "one_off_net": round(one_off),
        "projected_book_profit": round(book_profit),
        "add_backs": round(add_backs),
        "less_deductions": round(less_deductions),
        "projected_business_income": round(taxable),
    }


def project_presumptive(turnover_to_date: float, rate_pct: float, period_start: date, as_on: date,
                        period_end: date, growth_pct: float = 0.0) -> dict:
    days_done = max(1, (as_on - period_start).days + 1)
    days_total = (period_end - period_start).days + 1
    days_done = min(days_done, days_total)
    remaining = turnover_to_date / days_done * (days_total - days_done) * (1 + growth_pct / 100.0)
    turnover = turnover_to_date + remaining
    return {"projected_turnover": round(turnover), "rate_pct": rate_pct,
            "projected_business_income": round(turnover * rate_pct / 100.0)}
