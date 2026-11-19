from datetime import date

from django.shortcuts import get_object_or_404


def fy_label(d: date) -> str:
    """Indian financial year (Apr-Mar) for a date, e.g. 2026-11-02 -> '2026-27'."""
    start = d.year if d.month >= 4 else d.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def firm_object_or_404(model, request, **kwargs):
    """The one way views fetch a record by id: always scoped to the caller's firm, so another
    tenant's id yields 404 instead of data."""
    return get_object_or_404(model, firm=request.firm, **kwargs)
