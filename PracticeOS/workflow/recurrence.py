"""Recurring-deadline engine: turns RecurringRule rows into real Task rows.

Safe to run repeatedly (cron daily, or the "Generate now" button): the unique constraint on
(recurring_rule, due_date) plus get_or_create means an occurrence is never created twice.
"""
import calendar
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from core.utils import fy_label

MONTHS_PER = {"MONTHLY": 1, "QUARTERLY": 3, "HALF_YEARLY": 6, "ANNUAL": 12}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _clamped(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def add_period(d: date, frequency: str, day_of_month: int) -> date:
    """Next occurrence after d, keeping the day-of-month (clamped for short months)."""
    total = (d.month - 1) + MONTHS_PER[frequency]
    return _clamped(d.year + total // 12, total % 12 + 1, day_of_month)


def first_due_date(frequency: str, day_of_month: int, month: int | None = None, today: date | None = None) -> date:
    """First due date on/after today. `month` anchors quarterly/half-yearly/annual rules."""
    today = today or timezone.localdate()
    m = today.month if frequency == "MONTHLY" or not month else month
    candidate = _clamped(today.year, m, day_of_month)
    while candidate < today:
        candidate = add_period(candidate, frequency, day_of_month)
    return candidate


def period_label(frequency: str, due: date) -> str:
    """Label for the period a task relates to. A heuristic for staff, not a legal determination:
    monthly -> month before the due date (GSTR-3B due 20 Nov is for Oct); annual -> the financial
    year before the due date (ITR due 31 Jul 2027 is for FY 2026-27); others -> the due month,
    because quarterly items differ (advance tax is for the current FY, a TDS return for the
    quarter just ended)."""
    if frequency == "MONTHLY":
        y, m = (due.year, due.month - 1) if due.month > 1 else (due.year - 1, 12)
        return f"{MON[m - 1]} {y}"
    if frequency == "ANNUAL":
        return f"FY {fy_label(date(due.year - 1, due.month, min(due.day, 28)))}"
    return f"Due {MON[due.month - 1]} {due.year}"


def generate_due_tasks(firm=None) -> dict:
    """Create tasks for every active rule whose lead window has opened. Pass `firm` to limit to one
    tenant (the button); omit it for the scheduled run across all tenants."""
    from accounts.models import User
    from .models import RecurringRule, Task

    today = timezone.localdate()
    rules = RecurringRule.objects.filter(is_active=True).select_related("firm")
    if firm:
        rules = rules.filter(firm=firm)

    created = 0
    for rule in rules:
        creator = User.objects.filter(firm=rule.firm, role=User.Role.ADMIN, is_active=True).order_by("id").first()
        nxt = rule.next_due_date
        for _ in range(24):  # never loop more than 24 periods in one run
            if nxt - timedelta(days=rule.lead_days) > today:
                break
            with transaction.atomic():
                _, was_created = Task.objects.get_or_create(
                    recurring_rule=rule,
                    due_date=nxt,
                    defaults={
                        "firm": rule.firm, "client": rule.client, "title": rule.title, "description": rule.description,
                        "priority": rule.priority, "assignee": rule.assignee, "created_by": creator,
                        "period_label": period_label(rule.frequency, nxt),
                    },
                )
            created += was_created
            nxt = add_period(nxt, rule.frequency, rule.day_of_month)
        if nxt != rule.next_due_date:
            rule.next_due_date = nxt
            rule.last_generated = timezone.now()
            rule.save(update_fields=["next_due_date", "last_generated"])
    return {"rules_checked": rules.count(), "tasks_created": created}


# Editable starting points, NOT a live feed: due dates change by notification/extension, so firms
# should verify them against current CBDT / CBIC notices.
PRESETS = [
    {"key": "gstr1", "title": "GSTR-1 filing", "frequency": "MONTHLY", "day_of_month": 11, "priority": "HIGH"},
    {"key": "gstr3b", "title": "GSTR-3B filing", "frequency": "MONTHLY", "day_of_month": 20, "priority": "HIGH"},
    {"key": "tds-pay", "title": "TDS/TCS deposit", "frequency": "MONTHLY", "day_of_month": 7, "priority": "HIGH"},
    {"key": "pf-esi", "title": "PF / ESI payment & return", "frequency": "MONTHLY", "day_of_month": 15, "priority": "MEDIUM"},
    {"key": "advance-tax", "title": "Advance tax instalment", "frequency": "QUARTERLY", "day_of_month": 15, "month": 6, "priority": "HIGH"},
    {"key": "tds-return", "title": "TDS quarterly return", "frequency": "QUARTERLY", "day_of_month": 31, "month": 7, "priority": "MEDIUM"},
    {"key": "itr-nonaudit", "title": "ITR filing (non-audit)", "frequency": "ANNUAL", "day_of_month": 31, "month": 7, "priority": "HIGH"},
    {"key": "tax-audit", "title": "Tax audit report (3CD)", "frequency": "ANNUAL", "day_of_month": 30, "month": 9, "priority": "HIGH"},
    {"key": "itr-audit", "title": "ITR filing (audit cases)", "frequency": "ANNUAL", "day_of_month": 31, "month": 10, "priority": "HIGH"},
    {"key": "gstr9", "title": "GSTR-9 annual return", "frequency": "ANNUAL", "day_of_month": 31, "month": 12, "priority": "MEDIUM"},
]
