from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from billing.models import Invoice
from core.decorators import staff_required
from core.utils import firm_object_or_404
from documents.models import Document
from workflow.models import Task

from .forms import ClientForm, ServiceForm
from .models import Client, ClientService

SERVICE_SUGGESTIONS = [
    "GST Returns", "Income Tax Return", "Statutory Audit", "Tax Audit", "TDS Compliance", "Bookkeeping",
    "ROC Compliance", "Payroll", "IBC / Insolvency Advisory", "Social Audit",
]


@staff_required
def client_list(request):
    q = request.GET.get("q", "").strip()
    archived = request.GET.get("archived") == "1"
    clients = Client.objects.filter(firm=request.firm, is_active=not archived).annotate(
        open_tasks=Count("tasks", filter=~Q(tasks__status=Task.Status.COMPLETED), distinct=True)
    ).prefetch_related("services")
    if q:
        clients = clients.filter(Q(name__icontains=q) | Q(pan__icontains=q) | Q(gstin__icontains=q) | Q(email__icontains=q))
    return render(request, "crm/client_list.html", {"clients": clients, "q": q, "archived": archived})


@staff_required
def client_create(request):
    form = ClientForm(request.POST or None, firm=request.firm)
    if request.method == "POST" and form.is_valid():
        client = form.save()
        messages.success(request, f"{client.name} added.")
        return redirect("client_detail", pk=client.pk)
    return render(request, "form.html", {"form": form, "title": "Add client", "cancel_url": "client_list", "wide": True})


@staff_required
def client_detail(request, pk):
    client = firm_object_or_404(Client, request, pk=pk)
    invoices = list(Invoice.objects.filter(firm=request.firm, client=client).prefetch_related("payments").order_by("-issue_date")[:10])
    pending = Invoice.objects.filter(firm=request.firm, client=client, status=Invoice.Status.PENDING).prefetch_related("payments")
    outstanding = sum((i.balance for i in pending), Decimal("0"))
    return render(
        request,
        "crm/client_detail.html",
        {
            "client": client,
            "profile": [("PAN", client.pan), ("GSTIN", client.gstin), ("Email", client.email), ("Phone", client.phone),
                        ("Contact person", client.contact_person), ("Address", client.address)],
            "services": client.services.all(),
            "tasks": Task.objects.filter(firm=request.firm, client=client).select_related("assignee").order_by("due_date")[:10],
            "documents": Document.objects.filter(firm=request.firm, client=client)[:10],
            "invoices": invoices,
            "outstanding": outstanding,
        },
    )


@staff_required
def client_edit(request, pk):
    client = firm_object_or_404(Client, request, pk=pk)
    form = ClientForm(request.POST or None, instance=client, firm=request.firm)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Client updated.")
        return redirect("client_detail", pk=client.pk)
    return render(request, "form.html", {"form": form, "title": f"Edit {client.name}", "cancel_url": "client_list", "wide": True})


@staff_required
@require_POST
def client_set_active(request, pk, active):
    client = firm_object_or_404(Client, request, pk=pk)
    client.is_active = active
    client.save(update_fields=["is_active", "updated_at"])
    messages.success(request, f"{client.name} {'restored' if active else 'archived'}.")
    return redirect("client_detail" if active else "client_list", **({"pk": pk} if active else {}))


@staff_required
def service_form(request, pk, service_pk=None):
    client = firm_object_or_404(Client, request, pk=pk)
    service = firm_object_or_404(ClientService, request, pk=service_pk, client=client) if service_pk else None
    form = ServiceForm(request.POST or None, instance=service, firm=request.firm)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.client = client
        obj.save()
        messages.success(request, "Service saved.")
        return redirect("client_detail", pk=client.pk)
    return render(
        request, "form.html",
        {"form": form, "title": f"{'Edit' if service else 'Add'} service – {client.name}", "back_pk": client.pk,
         "cancel_url": "client_detail", "suggestions": SERVICE_SUGGESTIONS},
    )


@staff_required
@require_POST
def service_delete(request, pk, service_pk):
    service = firm_object_or_404(ClientService, request, pk=service_pk, client_id=pk)
    service.delete()
    messages.success(request, "Service removed.")
    return redirect("client_detail", pk=pk)
