import os

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from core.decorators import any_role_required, staff_required
from core.utils import firm_object_or_404
from crm.models import Client

from .forms import DocumentForm
from .models import Document

CATEGORIES = ["ITR", "GST", "TDS", "Audit", "Bank statements", "Accounts", "ROC", "Notices", "KYC"]


@staff_required
def document_list(request):
    docs = Document.objects.filter(firm=request.firm).select_related("client", "uploaded_by")
    client_id, kind, q = request.GET.get("client", ""), request.GET.get("type", ""), request.GET.get("q", "").strip()
    if client_id.isdigit():
        docs = docs.filter(client_id=client_id)
    if kind in Document.Type.values:
        docs = docs.filter(type=kind)
    if q:
        docs = docs.filter(Q(name__icontains=q) | Q(category__icontains=q))
    return render(request, "documents/list.html", {
        "docs": docs, "clients": Client.objects.filter(firm=request.firm), "types": Document.Type.choices,
        "f": {"client": client_id, "type": kind, "q": q},
    })


@staff_required
def document_create(request):
    initial = {"type": Document.Type.UPLOAD, "client": request.GET.get("client")}
    form = DocumentForm(request.POST or None, request.FILES or None, firm=request.firm, initial=initial)
    if request.method == "POST" and form.is_valid():
        doc = form.save(commit=False)
        doc.uploaded_by = request.user
        doc.save()
        messages.success(request, f"“{doc.name}” saved.")
        return redirect("document_list")
    return render(request, "documents/form.html", {"form": form, "categories": CATEGORIES})


@any_role_required
@require_GET
def download(request, pk):
    """Authenticated, tenant-checked streaming. Staff: any document in their firm. Client logins:
    only documents of their own client record that the firm has marked as shared."""
    doc = firm_object_or_404(Document, request, pk=pk, type=Document.Type.UPLOAD)
    if request.user.is_client and not (doc.shared_with_client and doc.client_id == request.user.client_id):
        raise Http404
    if not doc.file:
        raise Http404
    filename = doc.name if os.path.splitext(doc.name)[1] else doc.name + os.path.splitext(doc.file.name)[1]
    return FileResponse(doc.file.open("rb"), as_attachment=True, filename=filename)


@staff_required
@require_POST
def toggle_share(request, pk):
    doc = firm_object_or_404(Document, request, pk=pk)
    doc.shared_with_client = not doc.shared_with_client
    doc.save(update_fields=["shared_with_client"])
    return redirect(request.POST.get("next") or "document_list")


@staff_required
@require_POST
def document_delete(request, pk):
    doc = firm_object_or_404(Document, request, pk=pk)
    if doc.file:
        doc.file.delete(save=False)  # remove the stored file too
    doc.delete()
    messages.success(request, "Document deleted.")
    return redirect("document_list")
