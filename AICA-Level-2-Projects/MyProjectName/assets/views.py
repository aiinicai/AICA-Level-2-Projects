import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.roles import ADMIN_CFO, APPROVER, AUDITOR_READONLY, DATA_ENTRY, VERIFIER, user_has_role
from locations.models import Entity, Location

from .forms import (
    AssetEditForm,
    BulkImportForm,
    CapexRequisitionForm,
    CapitaliseForm,
    CWIPForm,
    DocumentUploadForm,
    RevaluationForm,
)
from .models import (
    ApprovalRequest,
    Asset,
    AssetClass,
    CapexRequisition,
    CWIP,
    Document,
    ImpairmentCheck,
    RevaluationRecord,
    Vendor,
)
from .services import approvals as approval_service
from .services import qr as qr_service
from .services import depreciation as depreciation_service

User = get_user_model()


def require_role(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if not user_has_role(request.user, *roles):
                return HttpResponseForbidden(
                    f"Your account does not have any of the required roles: {', '.join(roles)}."
                )
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


# ==========================================================================
# Asset master
# ==========================================================================

@login_required
def asset_list(request):
    qs = Asset.objects.select_related("asset_class", "location", "custodian", "entity").order_by("-created_at")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if q:
        qs = qs.filter(description__icontains=q) | qs.filter(asset_id__icontains=q)
    if status:
        qs = qs.filter(life_status=status)
    return render(request, "assets/list.html", {
        "assets": qs[:300], "q": q, "status": status, "status_choices": Asset.LifeStatus.choices,
    })


@login_required
def asset_detail(request, asset_id):
    asset = get_object_or_404(Asset.objects.select_related("asset_class", "location", "custodian", "vendor"), asset_id=asset_id)
    pending_approval = asset.approval_requests.filter(status=ApprovalRequest.Status.PENDING).first()
    book_entries = asset.book_depreciation_entries.select_related("run").order_by("-run__period_end")[:12]
    tax_entries = asset.tax_depreciation_entries.select_related("run").order_by("-run__period_end")[:12]
    scans = asset.scan_events.select_related("scanned_by", "confirmed_location").order_by("-scanned_at")[:15]
    transfers = asset.transfers.select_related("from_location", "to_location").order_by("-requested_at")[:10]
    verifications = asset.verification_records.select_related("verified_by").order_by("-verified_date")[:10]
    revaluations = asset.revaluations.order_by("-valuation_date")
    disposals = asset.disposal_requests.order_by("-requested_at")
    components = asset.components.select_related("asset_class")
    documents = asset.documents.select_related("uploaded_by")
    return render(request, "assets/detail.html", {
        "asset": asset, "pending_approval": pending_approval, "book_entries": book_entries,
        "tax_entries": tax_entries, "scans": scans, "transfers": transfers, "verifications": verifications,
        "revaluations": revaluations, "disposals": disposals, "components": components, "documents": documents,
        "doc_form": DocumentUploadForm(),
    })


@require_role(DATA_ENTRY, ADMIN_CFO)
def asset_edit(request, asset_id):
    asset = get_object_or_404(Asset, asset_id=asset_id)
    if request.method == "POST":
        form = AssetEditForm(request.POST, instance=asset)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.save()
            approval_service.create_request(
                request.user, obj, ApprovalRequest.Action.ASSET_EDIT,
                summary=f"Edited asset {obj.asset_id}: {obj.description}",
            )
            messages.success(request, "Change saved and routed for approval.")
            return redirect(obj.get_absolute_url())
    else:
        form = AssetEditForm(instance=asset)
    return render(request, "assets/edit.html", {"asset": asset, "form": form})


@require_role(DATA_ENTRY, ADMIN_CFO)
def asset_create(request):
    """
    Direct asset creation — for assets not routed through a CWIP (e.g.
    migrated legacy assets outside the bulk-import path). Capitalisation
    from CWIP (cwip_capitalise below) is the preferred entry point.
    """
    if request.method == "POST":
        form = CapitaliseForm(request.POST)
        entity_id = request.POST.get("entity")
        vendor_id = request.POST.get("vendor")
        cost = request.POST.get("capitalised_cost")
        if form.is_valid() and entity_id and vendor_id and cost:
            asset_class = form.cleaned_data["asset_class"]
            asset = Asset.objects.create(
                entity_id=entity_id,
                description=form.cleaned_data["description"],
                make_model=form.cleaned_data["make_model"],
                asset_class=asset_class,
                serial_number=form.cleaned_data["serial_number"],
                acquisition_date=form.cleaned_data["acquisition_date"],
                put_to_use_date=form.cleaned_data["put_to_use_date"],
                vendor_id=vendor_id,
                capitalised_cost=Decimal(cost),
                depreciation_method=form.cleaned_data["depreciation_method"],
                useful_life_years=form.cleaned_data["useful_life_years"],
                residual_value_pct=form.cleaned_data["residual_value_pct"],
                tax_block_code=form.cleaned_data["tax_block_code"],
                tax_wdv_rate_pct=form.cleaned_data["tax_wdv_rate_pct"],
                location=form.cleaned_data["location"],
                department=form.cleaned_data["department"],
                custodian=form.cleaned_data["custodian"],
                ownership_status=form.cleaned_data["ownership_status"],
                is_immovable_property=form.cleaned_data["is_immovable_property"],
                title_deed_in_company_name=form.cleaned_data["title_deed_in_company_name"],
                title_deed_reference=form.cleaned_data["title_deed_reference"],
                created_by=request.user,
            )
            approval_service.create_request(
                request.user, asset, ApprovalRequest.Action.ASSET_CREATE,
                summary=f"New asset {asset.asset_id}: {asset.description} (₹{asset.capitalised_cost:,.0f})",
            )
            messages.success(request, f"Asset {asset.asset_id} created and routed for approval.")
            return redirect(asset.get_absolute_url())
    else:
        form = CapitaliseForm()
    return render(request, "assets/create.html", {
        "form": form, "entities": Entity.objects.all(), "vendors": Vendor.objects.all(),
    })


@require_role(DATA_ENTRY, VERIFIER, ADMIN_CFO)
def document_upload(request, asset_id):
    asset = get_object_or_404(Asset, asset_id=asset_id)
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.content_type = ContentType.objects.get_for_model(Asset)
            doc.object_id = asset.pk
            doc.uploaded_by = request.user
            doc.save()
            messages.success(request, "Document attached.")
    return redirect(asset.get_absolute_url())


@login_required
def asset_qr_png(request, asset_id):
    asset = get_object_or_404(Asset, asset_id=asset_id)
    png = qr_service.generate_qr_png_bytes(asset)
    return HttpResponse(png, content_type="image/png")


# ==========================================================================
# Capex requisition (Sec. 179)
# ==========================================================================

@require_role(DATA_ENTRY, ADMIN_CFO)
def capex_list(request):
    items = CapexRequisition.objects.select_related("entity", "requested_by").order_by("-created_at")
    return render(request, "assets/capex_list.html", {"items": items})


@require_role(DATA_ENTRY, ADMIN_CFO)
def capex_create(request):
    if request.method == "POST":
        form = CapexRequisitionForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.requested_by = request.user
            obj.status = CapexRequisition.Status.PENDING_APPROVAL
            obj.save()
            messages.success(request, "Capex requisition submitted for approval.")
            return redirect("assets:capex_list")
    else:
        form = CapexRequisitionForm()
    return render(request, "assets/capex_form.html", {"form": form})


@require_role(APPROVER, ADMIN_CFO)
def capex_decide(request, pk):
    from django.utils import timezone
    req = get_object_or_404(CapexRequisition, pk=pk)
    if request.method == "POST":
        if req.requested_by_id == request.user.id:
            messages.error(request, "Maker-checker: you cannot approve your own requisition.")
        else:
            decision = request.POST.get("decision")
            req.status = CapexRequisition.Status.APPROVED if decision == "approve" else CapexRequisition.Status.REJECTED
            req.approved_by = request.user
            req.decided_at = timezone.now()
            req.board_resolution_reference = request.POST.get("board_resolution_reference", req.board_resolution_reference)
            req.save()
            messages.success(request, f"Requisition {req.get_status_display().lower()}.")
    return redirect("assets:capex_list")


# ==========================================================================
# CWIP -> capitalisation
# ==========================================================================

@require_role(DATA_ENTRY, ADMIN_CFO, AUDITOR_READONLY)
def cwip_list(request):
    items = CWIP.objects.select_related("entity", "vendor").order_by("-created_at")
    return render(request, "assets/cwip_list.html", {"items": items})


@require_role(DATA_ENTRY, ADMIN_CFO)
def cwip_create(request):
    if request.method == "POST":
        form = CWIPForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            messages.success(request, f"CWIP item {obj.reference} created.")
            return redirect("assets:cwip_detail", pk=obj.pk)
    else:
        form = CWIPForm()
    return render(request, "assets/cwip_form.html", {"form": form})


@require_role(DATA_ENTRY, ADMIN_CFO, AUDITOR_READONLY)
def cwip_detail(request, pk):
    cwip = get_object_or_404(CWIP, pk=pk)
    return render(request, "assets/cwip_detail.html", {
        "cwip": cwip, "doc_form": DocumentUploadForm(), "can_capitalise": cwip.status != CWIP.Status.CAPITALISED,
    })


@require_role(DATA_ENTRY, ADMIN_CFO)
def cwip_capitalise(request, pk):
    cwip = get_object_or_404(CWIP, pk=pk)
    if cwip.status == CWIP.Status.CAPITALISED:
        messages.error(request, "This CWIP item is already capitalised.")
        return redirect("assets:cwip_detail", pk=pk)

    default_class = None
    if request.method == "POST":
        form = CapitaliseForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                asset_class = form.cleaned_data["asset_class"]
                asset = Asset.objects.create(
                    entity=cwip.entity,
                    cwip_source=cwip,
                    description=form.cleaned_data["description"],
                    make_model=form.cleaned_data["make_model"],
                    asset_class=asset_class,
                    serial_number=form.cleaned_data["serial_number"],
                    acquisition_date=form.cleaned_data["acquisition_date"],
                    put_to_use_date=form.cleaned_data["put_to_use_date"],
                    vendor=cwip.vendor,
                    po_reference=cwip.po_number,
                    grn_reference=cwip.grn_number,
                    invoice_reference=cwip.invoice_number,
                    capitalised_cost=cwip.total_cost(),
                    depreciation_method=form.cleaned_data["depreciation_method"],
                    useful_life_years=form.cleaned_data["useful_life_years"],
                    residual_value_pct=form.cleaned_data["residual_value_pct"],
                    tax_block_code=form.cleaned_data["tax_block_code"],
                    tax_wdv_rate_pct=form.cleaned_data["tax_wdv_rate_pct"],
                    location=form.cleaned_data["location"],
                    department=form.cleaned_data["department"],
                    custodian=form.cleaned_data["custodian"],
                    ownership_status=form.cleaned_data["ownership_status"],
                    is_immovable_property=form.cleaned_data["is_immovable_property"],
                    title_deed_in_company_name=form.cleaned_data["title_deed_in_company_name"],
                    title_deed_reference=form.cleaned_data["title_deed_reference"],
                    created_by=request.user,
                )
                cwip.status = CWIP.Status.CAPITALISED
                cwip.save()
                approval_service.create_request(
                    request.user, asset, ApprovalRequest.Action.CAPITALISATION,
                    summary=f"Capitalised CWIP {cwip.reference} → {asset.asset_id} (₹{asset.capitalised_cost:,.0f})",
                )
            messages.success(request, f"Capitalised as {asset.asset_id}. QR tag generated — print the label to affix it.")
            return redirect(asset.get_absolute_url())
    else:
        form = CapitaliseForm(initial={
            "description": cwip.description,
            "asset_class": default_class,
            "acquisition_date": cwip.invoice_date or date.today(),
            "put_to_use_date": date.today(),
        })
    return render(request, "assets/cwip_capitalise.html", {"cwip": cwip, "form": form})


# ==========================================================================
# QR label printing
# ==========================================================================

@login_required
def label_print(request):
    ids = request.GET.getlist("asset")
    if not ids:
        messages.info(request, "Select at least one asset to print labels for.")
        return redirect("assets:list")
    assets = Asset.objects.filter(asset_id__in=ids)
    pdf = qr_service.generate_batch_label_pdf(assets)
    now = date.today()
    for asset in assets:
        if asset.tag_status == Asset.TagStatus.UNTAGGED:
            asset.tag_status = Asset.TagStatus.TAGGED
            asset.tagged_at = now
            asset.tagged_by = request.user
            asset.save(update_fields=["tag_status", "tagged_at", "tagged_by"])
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="asset_labels.pdf"'
    return response


# ==========================================================================
# Revaluation & impairment
# ==========================================================================

@require_role(DATA_ENTRY, ADMIN_CFO, AUDITOR_READONLY)
def revaluation_list(request):
    items = RevaluationRecord.objects.select_related("asset").order_by("-valuation_date")
    return render(request, "assets/revaluation_list.html", {"items": items})


@require_role(DATA_ENTRY, ADMIN_CFO)
def revaluation_create(request):
    if request.method == "POST":
        form = RevaluationForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.surplus_or_deficit = form.cleaned_data.get("surplus_or_deficit", Decimal("0"))
            obj.movement_pct = form.cleaned_data.get("movement_pct", Decimal("0"))
            obj.requested_by = request.user
            obj.save()
            approval_service.create_request(
                request.user, obj, ApprovalRequest.Action.REVALUATION,
                summary=(
                    f"Revaluation of {obj.asset.asset_id} by {obj.valuer_name} — "
                    f"surplus/deficit ₹{obj.surplus_or_deficit:,.0f} ({obj.movement_pct:.1f}%)"
                ),
            )
            messages.success(request, "Revaluation recorded and routed for approval.")
            return redirect("assets:revaluation_list")
    else:
        form = RevaluationForm()
    return render(request, "assets/revaluation_form.html", {"form": form})


@require_role(APPROVER, ADMIN_CFO)
def revaluation_decide(request, pk):
    obj = get_object_or_404(RevaluationRecord, pk=pk)
    approval = obj.approval_requests.filter(status=ApprovalRequest.Status.PENDING).first()
    if request.method == "POST" and approval:
        approve = request.POST.get("decision") == "approve"
        try:
            approval_service.decide(approval, request.user, approve, request.POST.get("comment", ""))
        except approval_service.DifferentUserRequiredError as exc:
            messages.error(request, str(exc))
            return redirect("assets:revaluation_list")
        if approve:
            obj.approved_by = request.user
            obj.save()
            asset = obj.asset
            asset.is_revalued = True
            asset.last_revaluation_date = obj.valuation_date
            asset.accumulated_revaluation_surplus += obj.surplus_or_deficit
            asset.save()
            messages.success(request, "Revaluation approved and posted to the asset's gross block.")
        else:
            messages.info(request, "Revaluation rejected.")
    return redirect("assets:revaluation_list")


@require_role(APPROVER, ADMIN_CFO)
def impairment_create(request, asset_id):
    asset = get_object_or_404(Asset, asset_id=asset_id)
    if request.method == "POST":
        carrying = asset.net_book_value()
        recoverable = request.POST.get("recoverable_amount")
        indicators = request.POST.get("indicators_present") == "on"
        loss = Decimal("0")
        recoverable_dec = None
        if recoverable:
            try:
                recoverable_dec = Decimal(recoverable)
                if recoverable_dec < carrying:
                    loss = carrying - recoverable_dec
            except InvalidOperation:
                pass
        check = ImpairmentCheck.objects.create(
            asset=asset, check_date=date.today(), indicators_present=indicators,
            indicator_notes=request.POST.get("indicator_notes", ""),
            recoverable_amount=recoverable_dec, carrying_amount=carrying,
            impairment_loss=loss, checked_by=request.user,
        )
        if loss > 0:
            asset.impairment_loss_to_date += loss
            asset.save()
        messages.success(request, f"Impairment check recorded (loss ₹{loss:,.0f}).")
    return redirect(asset.get_absolute_url())


# ==========================================================================
# Approvals inbox (generic maker-checker)
# ==========================================================================

@require_role(APPROVER, ADMIN_CFO)
def approval_inbox(request):
    items = ApprovalRequest.objects.filter(status=ApprovalRequest.Status.PENDING).select_related(
        "requested_by", "content_type"
    ).order_by("requested_at")
    return render(request, "assets/approval_inbox.html", {"items": items})


@require_role(APPROVER, ADMIN_CFO)
def approval_decide(request, pk):
    approval = get_object_or_404(ApprovalRequest, pk=pk)
    if request.method == "POST":
        approve = request.POST.get("decision") == "approve"
        comment = request.POST.get("comment", "")
        try:
            approval_service.decide(approval, request.user, approve, comment)
        except (approval_service.DifferentUserRequiredError, ValueError) as exc:
            messages.error(request, str(exc))
            return redirect("assets:approval_inbox")

        obj = approval.content_object
        if approve and isinstance(obj, Asset):
            obj.approved_by = request.user
            obj.save(update_fields=["approved_by"])
        messages.success(request, f"Request {approval.get_status_display().lower()}.")
    return redirect("assets:approval_inbox")


# ==========================================================================
# Depreciation run
# ==========================================================================

@require_role(ADMIN_CFO)
def depreciation_run(request):
    entities = Entity.objects.all()
    if request.method == "POST":
        entity = get_object_or_404(Entity, pk=request.POST.get("entity"))
        period_start = request.POST.get("period_start")
        period_end = request.POST.get("period_end")
        book = request.POST.get("book")
        try:
            if book == "SCHEDULE_II":
                run = depreciation_service.run_schedule_ii(entity, date.fromisoformat(period_start), date.fromisoformat(period_end), request.user)
            else:
                run = depreciation_service.run_income_tax(entity, date.fromisoformat(period_start), date.fromisoformat(period_end), request.user)
            messages.success(request, f"Depreciation run posted: {run}.")
        except Exception as exc:  # surfaced to the CFO/admin running it
            messages.error(request, f"Run failed: {exc}")
        return redirect("assets:depreciation_run")

    from .models import DepreciationRun
    recent_runs = DepreciationRun.objects.select_related("entity", "run_by").order_by("-run_at")[:20]
    return render(request, "assets/depreciation_run.html", {"entities": entities, "recent_runs": recent_runs})


# ==========================================================================
# Bulk import / export
# ==========================================================================

BULK_FIELDS = [
    "entity_name", "description", "make_model", "asset_class", "serial_number",
    "acquisition_date", "put_to_use_date", "vendor_name", "capitalised_cost",
    "depreciation_method", "useful_life_years", "residual_value_pct",
    "tax_block_code", "tax_wdv_rate_pct", "location_code", "department",
    "ownership_status",
]


@require_role(DATA_ENTRY, ADMIN_CFO)
def bulk_template(request):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(BULK_FIELDS)
    writer.writerow([
        "Demo Listed Company Ltd.", "Dell Latitude laptop", "Latitude 5440", "IT-LAP-001",
        "2026-04-01", "2026-04-05", "Dell India", "85000", "SLM", "3", "5",
        "", "", "HO-B1-F2-R01", "IT", "OWNED",
    ])
    response = HttpResponse(buf.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="far_bulk_import_template.csv"'
    return response


@require_role(DATA_ENTRY, ADMIN_CFO)
def bulk_export(request):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "asset_id", "description", "asset_class", "location", "capitalised_cost",
        "net_book_value", "life_status", "tag_status", "custodian",
    ])
    for a in Asset.objects.select_related("asset_class", "location", "custodian"):
        writer.writerow([
            a.asset_id, a.description, a.asset_class.name, a.location.breadcrumb(),
            a.capitalised_cost, a.net_book_value(), a.life_status, a.tag_status,
            str(a.custodian) if a.custodian else "",
        ])
    response = HttpResponse(buf.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="far_asset_export.csv"'
    return response


@require_role(DATA_ENTRY, ADMIN_CFO)
def bulk_import(request):
    result = None
    if request.method == "POST":
        form = BulkImportForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES["file"]
            text = f.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            created, errors = 0, []
            for i, row in enumerate(reader, start=2):
                try:
                    with transaction.atomic():
                        entity, _ = Entity.objects.get_or_create(name=row["entity_name"].strip())
                        asset_class, _ = AssetClass.objects.get_or_create(
                            name=row["asset_class"].strip(),
                            defaults={"useful_life_years": row.get("useful_life_years") or None},
                        )
                        vendor, _ = Vendor.objects.get_or_create(name=row["vendor_name"].strip())
                        location = Location.objects.filter(code=row["location_code"].strip()).first()
                        if not location:
                            raise ValueError(f"location_code '{row['location_code']}' not found")
                        Asset.objects.create(
                            entity=entity,
                            description=row["description"],
                            make_model=row.get("make_model", ""),
                            asset_class=asset_class,
                            serial_number=row.get("serial_number", ""),
                            acquisition_date=row["acquisition_date"],
                            put_to_use_date=row["put_to_use_date"],
                            vendor=vendor,
                            capitalised_cost=Decimal(row["capitalised_cost"]),
                            depreciation_method=row["depreciation_method"],
                            useful_life_years=Decimal(row["useful_life_years"]),
                            residual_value_pct=Decimal(row.get("residual_value_pct") or 5),
                            tax_block_code=row.get("tax_block_code", ""),
                            tax_wdv_rate_pct=Decimal(row["tax_wdv_rate_pct"]) if row.get("tax_wdv_rate_pct") else None,
                            location=location,
                            department=row.get("department", ""),
                            ownership_status=row.get("ownership_status") or Asset.OwnershipStatus.OWNED,
                            created_by=request.user,
                        )
                        created += 1
                except Exception as exc:
                    errors.append(f"Row {i}: {exc}")
            result = {"created": created, "errors": errors}
    else:
        form = BulkImportForm()
    return render(request, "assets/bulk_import.html", {"form": form, "result": result})
