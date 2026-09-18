import decimal
from django import template
from django.utils.safestring import mark_safe
from tracker.services.permissions import get_user_role_for_engagement

register = template.Library()

@register.filter
def inr(value):
    """Formats amount in Indian Rupees system: ₹ 1,23,45,678.00"""
    if value is None or value == '':
        return "―"
    try:
        val = decimal.Decimal(str(value))
    except Exception:
        return value

    is_negative = val < 0
    val = abs(val)
    
    parts = f"{val:.2f}".split('.')
    integer_part = parts[0]
    decimal_part = parts[1]

    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        last3 = integer_part[-3:]
        remaining = integer_part[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted = ",".join(groups) + "," + last3

    prefix = "-₹ " if is_negative else "₹ "
    return f"{prefix}{formatted}.{decimal_part}"


@register.filter
def user_role_on_engagement(user, engagement):
    return get_user_role_for_engagement(user, engagement) or "No Assigned Role"


@register.filter
def status_badge(status):
    badge_map = {
        'Draft': 'secondary',
        'Pending Internal Review': 'warning text-dark',
        'Issued': 'primary',
        'Pending Client Review': 'info text-dark',
        'Responded': 'info text-dark',
        'Info Awaited': 'warning text-dark',
        'Closed': 'success',
        'Closed - Exception Approved': 'success',
        'Withdrawn': 'dark',
        'Planned': 'secondary',
        'In Progress': 'primary',
        'Queries Closed': 'info text-dark',
        'Memo Issued': 'success',
        'Archived': 'dark',
        'Pending': 'warning text-dark',
        'Approved': 'success',
        'Rejected': 'danger',
    }
    css_class = badge_map.get(status, 'secondary')
    return mark_safe(f'<span class="badge bg-{css_class}">{status}</span>')


@register.filter
def priority_badge(priority):
    badge_map = {
        'High': 'danger',
        'Medium': 'warning text-dark',
        'Low': 'info text-dark',
    }
    css_class = badge_map.get(priority, 'secondary')
    return mark_safe(f'<span class="badge bg-{css_class}">{priority}</span>')


@register.filter
def risk_badge(risk):
    badge_map = {
        'Critical': 'danger',
        'High': 'danger',
        'Medium': 'warning text-dark',
        'Low': 'success',
    }
    css_class = badge_map.get(risk, 'secondary')
    return mark_safe(f'<span class="badge bg-{css_class}">{risk}</span>')


@register.filter
def ageing_badge(query):
    bucket = query.ageing_bucket
    if query.is_terminal:
        return mark_safe(f'<span class="badge bg-light text-muted border">{query.days_open} days</span>')
    
    if bucket == '0-7 days':
        css = 'success'
    elif bucket == '8-15 days':
        css = 'info text-dark'
    elif bucket == '16-30 days':
        css = 'warning text-dark'
    else:
        css = 'danger'
    return mark_safe(f'<span class="badge bg-{css}">{bucket} ({query.days_open}d)</span>')
