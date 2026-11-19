from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template

register = template.Library()


def _group_indian(digits: str) -> str:
    """1234567 -> 12,34,567"""
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


@register.filter
def inr(value):
    try:
        d = Decimal(value if value not in (None, "") else 0).quantize(Decimal("0.01"), ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return value
    whole, frac = f"{abs(d):.2f}".split(".")
    return f"{'-' if d < 0 else ''}₹{_group_indian(whole)}.{frac}"


@register.filter
def hhmm(minutes):
    h, m = divmod(int(minutes or 0), 60)
    return f"{h}h {m:02d}m"


TONES = {
    "TODO": "bg-slate-100 text-slate-700",
    "IN_PROGRESS": "bg-blue-100 text-blue-700",
    "REVIEW": "bg-amber-100 text-amber-800",
    "COMPLETED": "bg-emerald-100 text-emerald-700",
    "PENDING": "bg-amber-100 text-amber-800",
    "PAID": "bg-emerald-100 text-emerald-700",
    "CANCELLED": "bg-slate-100 text-slate-500",
    "OVERDUE": "bg-red-100 text-red-700",
    "HIGH": "bg-red-100 text-red-700",
    "UPLOAD": "bg-blue-100 text-blue-700",
    "LINK": "bg-violet-100 text-violet-700",
    "PHYSICAL": "bg-amber-100 text-amber-800",
    "ADMIN": "bg-violet-100 text-violet-700",
    "TEAM_MEMBER": "bg-blue-100 text-blue-700",
    "CLIENT": "bg-amber-100 text-amber-800",
    "GOOD": "bg-emerald-100 text-emerald-700",
}


@register.filter
def tone(value):
    return "badge " + TONES.get(str(value), "bg-slate-100 text-slate-700")


@register.simple_tag(takes_context=True)
def nav_cls(context, prefix):
    path = context["request"].path
    return "bg-brand-50 text-brand-700" if path.startswith(prefix) else "text-slate-600 hover:bg-slate-100"


@register.filter
def initials(name):
    return "".join(w[0] for w in str(name).split()[:2]).upper()


@register.filter
def firstname(name):
    return str(name).split(" ")[0]
