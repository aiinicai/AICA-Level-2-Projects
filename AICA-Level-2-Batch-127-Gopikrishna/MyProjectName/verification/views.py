from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.roles import ADMIN_CFO, VERIFIER, user_has_role
from assets.models import Asset
from disposal.models import DisposalRequest
from locations.models import Location

from .models import MaintenanceLog, PhysicalVerificationRecord, ScanEvent, VerificationCycle


@login_required
def scan_home(request):
    locations = Location.objects.filter(is_active=True).order_by("entity", "node_type", "name")
    return render(request, "verification/scan_home.html", {
        "purposes": ScanEvent.Purpose.choices, "locations": locations,
    })


@login_required
def scan_lookup(request, asset_id):
    """AJAX lookup used by the scan page right after the camera decodes a QR payload."""
    try:
        asset = Asset.objects.select_related("location", "asset_class").get(asset_id=asset_id)
    except Asset.DoesNotExist:
        return JsonResponse({"found": False})
    is_disposed = asset.life_status == Asset.LifeStatus.DISPOSED
    return JsonResponse({
        "found": True,
        "asset_id": asset.asset_id,
        "description": asset.description,
        "asset_class": asset.asset_class.name,
        "current_location": asset.location.breadcrumb(),
        "current_location_id": asset.location_id,
        "is_disposed": is_disposed,
        "life_status": asset.get_life_status_display(),
    })


@login_required
def scan_submit(request):
    if request.method != "POST":
        return redirect("verification:scan_home")

    asset = get_object_or_404(Asset, asset_id=request.POST.get("asset_id"))
    purpose = request.POST.get("purpose")
    confirmed_location_id = request.POST.get("confirmed_location")
    lat = request.POST.get("latitude") or None
    lng = request.POST.get("longitude") or None
    condition_notes = request.POST.get("condition_notes", "")

    tag_was_disposed = asset.life_status == Asset.LifeStatus.DISPOSED
    if tag_was_disposed:
        ScanEvent.objects.create(
            asset=asset, purpose=purpose, scanned_by=request.user,
            device_latitude=lat, device_longitude=lng, tag_was_disposed=True,
            condition_notes="EXCEPTION: scan of a disposed asset's tag.",
        )
        messages.error(request, f"{asset.asset_id} is DISPOSED. This tag should have been deactivated — exception logged.")
        return redirect("verification:scan_home")

    confirmed_location = Location.objects.filter(pk=confirmed_location_id).first() if confirmed_location_id else None
    mismatch = bool(confirmed_location) and confirmed_location_id != str(asset.location_id)

    scan = ScanEvent.objects.create(
        asset=asset, purpose=purpose, scanned_by=request.user,
        device_latitude=lat, device_longitude=lng,
        confirmed_location=confirmed_location, location_mismatch=mismatch,
        condition_notes=condition_notes,
    )

    asset.last_scan_latitude = lat
    asset.last_scan_longitude = lng
    asset.last_scan_at = timezone.now()
    update_fields = ["last_scan_latitude", "last_scan_longitude", "last_scan_at"]

    if purpose == ScanEvent.Purpose.TAG_CONFIRM and asset.tag_status == Asset.TagStatus.UNTAGGED:
        asset.tag_status = Asset.TagStatus.TAGGED
        asset.tagged_at = timezone.now()
        asset.tagged_by = request.user
        update_fields += ["tag_status", "tagged_at", "tagged_by"]
        messages.success(request, f"{asset.asset_id} tag confirmed — status set to Tagged.")

    if purpose == ScanEvent.Purpose.VERIFICATION:
        asset.last_verified_date = date.today()
        asset.last_verified_by = request.user
        asset.last_verification_condition = request.POST.get("condition", "")
        update_fields += ["last_verified_date", "last_verified_by", "last_verification_condition"]
        cycle = VerificationCycle.objects.filter(
            entity=asset.entity, status=VerificationCycle.Status.IN_PROGRESS
        ).first()
        if cycle:
            PhysicalVerificationRecord.objects.update_or_create(
                cycle=cycle, asset=asset,
                defaults={
                    "scan_event": scan, "verified_by": request.user, "verified_date": date.today(),
                    "condition": request.POST.get("condition", PhysicalVerificationRecord.Condition.GOOD),
                    "discrepancy_notes": "Location mismatch on scan." if mismatch else "",
                },
            )
        messages.success(request, f"Physical verification logged for {asset.asset_id}.")

    if purpose == ScanEvent.Purpose.MAINTENANCE:
        MaintenanceLog.objects.create(
            asset=asset, scan_event=scan, logged_by=request.user,
            description=condition_notes or "Maintenance logged via QR scan.",
        )
        messages.success(request, f"Maintenance entry logged for {asset.asset_id}.")

    if purpose == ScanEvent.Purpose.DISPOSAL_CHECK:
        messages.info(request, f"Disposal check scan recorded for {asset.asset_id}.")

    asset.save(update_fields=update_fields)

    if mismatch:
        messages.warning(
            request,
            f"Location mismatch: scan confirmed {confirmed_location.breadcrumb()} but the register shows "
            f"{asset.location.breadcrumb()}. Exception logged — resolve it or raise a transfer.",
        )

    return redirect("verification:scan_home")


@login_required
def mismatch_queue(request):
    items = ScanEvent.objects.filter(location_mismatch=True, mismatch_resolved=False).select_related(
        "asset", "confirmed_location", "scanned_by"
    ).order_by("-scanned_at")
    return render(request, "verification/mismatch_queue.html", {"items": items})


@login_required
def mismatch_resolve(request, pk):
    scan = get_object_or_404(ScanEvent, pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        scan.mismatch_resolution_notes = request.POST.get("notes", "")
        scan.mismatch_resolved = True
        scan.save()
        if action == "accept_transfer" and scan.confirmed_location:
            from transfers.models import TransferRequest
            TransferRequest.objects.create(
                asset=scan.asset, from_location=scan.asset.location, to_location=scan.confirmed_location,
                reason="Formalising location mismatch found during scan.",
                requested_by=request.user, scan_event=scan, triggered_by_mismatch=True,
            )
            messages.success(request, "Transfer request raised to formalise the new location.")
        else:
            messages.info(request, "Mismatch dismissed as a data-entry correction; register location unchanged.")
    return redirect("verification:mismatch_queue")


# ==========================================================================
# Verification cycles (CARO 3(i)(b) rotational programme)
# ==========================================================================

@login_required
def cycle_list(request):
    cycles = VerificationCycle.objects.select_related("entity", "scope_location").order_by("-start_date")
    return render(request, "verification/cycle_list.html", {"cycles": cycles})


@login_required
def cycle_create(request):
    if not user_has_role(request.user, VERIFIER, ADMIN_CFO):
        messages.error(request, "You need the Verifier or Admin/CFO role to plan a cycle.")
        return redirect("verification:cycle_list")
    if request.method == "POST":
        from locations.models import Entity
        cycle = VerificationCycle.objects.create(
            entity=Entity.objects.get(pk=request.POST["entity"]),
            name=request.POST["name"],
            scope_location_id=request.POST.get("scope_location") or None,
            start_date=request.POST["start_date"],
            target_end_date=request.POST["target_end_date"],
            status=VerificationCycle.Status.IN_PROGRESS,
            created_by=request.user,
        )
        messages.success(request, f"Verification cycle '{cycle.name}' created.")
        return redirect("verification:cycle_detail", pk=cycle.pk)
    from locations.models import Entity
    return render(request, "verification/cycle_form.html", {
        "entities": Entity.objects.all(), "locations": Location.objects.filter(is_active=True),
    })


@login_required
def cycle_detail(request, pk):
    cycle = get_object_or_404(VerificationCycle, pk=pk)
    in_scope = cycle.in_scope_assets().select_related("location", "asset_class")
    verified_ids = set(cycle.records.values_list("asset_id", flat=True))
    pending = [a for a in in_scope if a.id not in verified_ids]
    records = cycle.records.select_related("asset", "verified_by").order_by("-verified_date")
    return render(request, "verification/cycle_detail.html", {
        "cycle": cycle, "pending": pending, "records": records, "coverage_pct": cycle.coverage_pct(),
    })


@login_required
def cycle_verify_asset(request, pk, asset_id):
    cycle = get_object_or_404(VerificationCycle, pk=pk)
    asset = get_object_or_404(Asset, asset_id=asset_id)
    if request.method == "POST":
        PhysicalVerificationRecord.objects.update_or_create(
            cycle=cycle, asset=asset,
            defaults={
                "verified_by": request.user, "verified_date": date.today(),
                "condition": request.POST.get("condition"),
                "discrepancy_notes": request.POST.get("discrepancy_notes", ""),
            },
        )
        asset.last_verified_date = date.today()
        asset.last_verified_by = request.user
        asset.last_verification_condition = request.POST.get("condition", "")
        asset.save(update_fields=["last_verified_date", "last_verified_by", "last_verification_condition"])
        messages.success(request, f"{asset.asset_id} marked verified.")
    return redirect("verification:cycle_detail", pk=pk)
