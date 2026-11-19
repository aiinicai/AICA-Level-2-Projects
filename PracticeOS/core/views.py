from decimal import Decimal

from datetime import timedelta

from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from billing.models import Invoice, Payment, TimeEntry
from core.decorators import any_role_required, staff_required
from crm.models import Client
from documents.models import Document
from workflow.models import Task


@any_role_required
def home(request):
    return redirect("portal" if request.user.is_client else "dashboard")


@staff_required
def dashboard(request):
    firm, today = request.firm, timezone.localdate()
    open_tasks = Task.objects.filter(firm=firm).exclude(status=Task.Status.COMPLETED)
    by_status = {row["status"]: row["n"] for row in Task.objects.filter(firm=firm).values("status").annotate(n=Count("id"))}

    pending = list(Invoice.objects.filter(firm=firm, status=Invoice.Status.PENDING).prefetch_related("payments"))
    stats = {
        "clients": Client.objects.filter(firm=firm, is_active=True).count(),
        "overdue": open_tasks.filter(due_date__lt=today).count(),
        "due_week": open_tasks.filter(due_date__gte=today, due_date__lte=today + timedelta(days=7)).count(),
        "mine": open_tasks.filter(assignee=request.user).count(),
        "unbilled_hours": round((TimeEntry.objects.filter(firm=firm, billable=True, invoice__isnull=True).aggregate(m=Sum("minutes"))["m"] or 0) / 60, 2),
        "outstanding": sum((i.balance for i in pending), Decimal("0")),
        "overdue_amount": sum((i.balance for i in pending if i.is_overdue), Decimal("0")),
        "received_month": Payment.objects.filter(firm=firm, paid_on__gte=today.replace(day=1)).aggregate(s=Sum("amount"))["s"] or Decimal("0"),
        "pipeline": [(label, by_status.get(value, 0)) for value, label in Task.Status.choices],
    }
    upcoming = open_tasks.filter(due_date__isnull=False).select_related("client", "assignee").order_by("due_date")[:8]
    return render(request, "core/dashboard.html", {"s": stats, "upcoming": upcoming})


@any_role_required
def portal(request):
    """Read-only area for CLIENT logins: their own invoices and documents the firm chose to share."""
    if not request.user.is_client:
        return redirect("dashboard")
    cid = request.user.client_id
    invoices = Invoice.objects.filter(firm=request.firm, client_id=cid).exclude(status=Invoice.Status.CANCELLED).prefetch_related("payments")
    docs = Document.objects.filter(firm=request.firm, client_id=cid, shared_with_client=True).exclude(type=Document.Type.PHYSICAL)
    return render(request, "portal/home.html", {"invoices": invoices, "docs": docs})
