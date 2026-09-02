from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from assets.models import Asset
from locations.models import Location

from .models import TransferRequest


@login_required
def transfer_list(request):
    items = TransferRequest.objects.select_related("asset", "from_location", "to_location").order_by("-requested_at")
    return render(request, "transfers/list.html", {"items": items})


@login_required
def transfer_create(request):
    if request.method == "POST":
        asset = get_object_or_404(Asset, asset_id=request.POST["asset_id"])
        to_location = get_object_or_404(Location, pk=request.POST["to_location"])
        TransferRequest.objects.create(
            asset=asset, from_location=asset.location, to_location=to_location,
            from_custodian=asset.custodian, to_custodian_id=request.POST.get("to_custodian") or None,
            from_department=asset.department, to_department=request.POST.get("to_department", ""),
            reason=request.POST.get("reason", ""), requested_by=request.user,
        )
        messages.success(request, "Transfer requested — awaiting custodian sign-off.")
        return redirect("transfers:list")
    from django.contrib.auth import get_user_model
    return render(request, "transfers/form.html", {
        "assets": Asset.objects.exclude(life_status=Asset.LifeStatus.DISPOSED),
        "locations": Location.objects.filter(is_active=True),
        "users": get_user_model().objects.filter(is_active=True),
    })


@login_required
def transfer_sign_off(request, pk):
    transfer = get_object_or_404(TransferRequest, pk=pk)
    if request.method == "POST" and transfer.status == TransferRequest.Status.PENDING:
        transfer.status = TransferRequest.Status.COMPLETED
        transfer.signed_off_by = request.user
        transfer.signed_off_at = timezone.now()
        transfer.save()

        asset = transfer.asset
        asset.location = transfer.to_location
        if transfer.to_custodian_id:
            asset.custodian = transfer.to_custodian
        if transfer.to_department:
            asset.department = transfer.to_department
        asset.save(update_fields=["location", "custodian", "department"])
        messages.success(request, f"Transfer completed — {asset.asset_id} now shows at {transfer.to_location.breadcrumb()}.")
    return redirect("transfers:list")
