from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.roles import ADMIN_CFO, APPROVER
from assets.models import ApprovalRequest, Asset
from assets.services import approvals as approval_service

from .models import DisposalRequest

# Simplification, flagged in the UI: Section 180 doesn't set a numeric bright
# line for "substantial part of an undertaking" — companies typically set
# their own threshold in the delegation-of-authority policy. 10% of total
# net PP&E is used here as a conservative default trigger for the board-
# approval flag; confirm the company's own policy figure with the CS/legal team.
SECTION_180_DEFAULT_THRESHOLD_PCT = Decimal("10.00")


@login_required
def disposal_list(request):
    items = DisposalRequest.objects.select_related("asset").order_by("-requested_at")
    return render(request, "disposal/list.html", {"items": items})


@login_required
def disposal_create(request):
    if request.method == "POST":
        asset = get_object_or_404(Asset, asset_id=request.POST["asset_id"])
        nbv = asset.net_book_value()
        sale_value = Decimal(request.POST.get("sale_or_scrap_value") or "0")
        costs = Decimal(request.POST.get("disposal_costs") or "0")

        total_net_ppe = Asset.objects.exclude(life_status=Asset.LifeStatus.DISPOSED).aggregate(
            total=Sum("capitalised_cost")
        )["total"] or Decimal("1")
        pct = (sale_value / total_net_ppe) * 100 if total_net_ppe else Decimal("0")

        disposal = DisposalRequest.objects.create(
            asset=asset, mode=request.POST["mode"], reason=request.POST.get("reason", ""),
            requested_disposal_date=request.POST["requested_disposal_date"],
            net_book_value_at_request=nbv, sale_or_scrap_value=sale_value, disposal_costs=costs,
            section_180_threshold_pct=pct, is_material_section_180=pct >= SECTION_180_DEFAULT_THRESHOLD_PCT,
            buyer_or_scrap_vendor=request.POST.get("buyer_or_scrap_vendor", ""),
            is_related_party=request.POST.get("is_related_party") == "on",
            requested_by=request.user, status=DisposalRequest.Status.PENDING_APPROVAL,
        )
        disposal.compute_profit_loss()
        disposal.save()
        approval_service.create_request(
            request.user, disposal, ApprovalRequest.Action.DISPOSAL,
            summary=(
                f"{disposal.get_mode_display()} of {asset.asset_id} — NBV ₹{nbv:,.0f}, "
                f"proceeds ₹{sale_value:,.0f}, P&L ₹{disposal.profit_or_loss:,.0f}"
                + (" — SECTION 180: may need shareholder approval" if disposal.is_material_section_180 else "")
            ),
        )
        asset.life_status = Asset.LifeStatus.HELD_FOR_DISPOSAL
        asset.save(update_fields=["life_status"])
        messages.success(request, "Disposal request submitted for approval.")
        return redirect("disposal:list")
    return render(request, "disposal/form.html", {
        "assets": Asset.objects.exclude(life_status=Asset.LifeStatus.DISPOSED),
        "modes": DisposalRequest.Mode.choices,
    })


@login_required
def disposal_decide(request, pk):
    disposal = get_object_or_404(DisposalRequest, pk=pk)
    approval = disposal.approval_requests.filter(status=ApprovalRequest.Status.PENDING).first()
    if request.method == "POST" and approval:
        approve = request.POST.get("decision") == "approve"
        board_ref = request.POST.get("board_resolution_reference", "")
        try:
            approval_service.decide(approval, request.user, approve, request.POST.get("comment", ""))
        except approval_service.DifferentUserRequiredError as exc:
            messages.error(request, str(exc))
            return redirect("disposal:list")

        if approve:
            disposal.status = DisposalRequest.Status.APPROVED
            disposal.approved_by = request.user
            disposal.approved_at = timezone.now()
            if board_ref:
                disposal.board_resolution_reference = board_ref
            disposal.save()

            asset = disposal.asset
            asset.life_status = Asset.LifeStatus.DISPOSED
            asset.tag_status = Asset.TagStatus.DEACTIVATED
            asset.save(update_fields=["life_status", "tag_status"])
            messages.success(request, f"Disposal approved. {asset.asset_id} archived (record retained, never deleted) and QR tag deactivated.")
        else:
            disposal.status = DisposalRequest.Status.REJECTED
            disposal.save()
            asset = disposal.asset
            asset.life_status = Asset.LifeStatus.IN_USE
            asset.save(update_fields=["life_status"])
            messages.info(request, "Disposal rejected; asset restored to in-use.")
    return redirect("disposal:list")
