from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render

from assets.models import Asset, ApprovalRequest, CWIP, RevaluationRecord
from disposal.models import DisposalRequest
from transfers.models import TransferRequest
from verification.models import ScanEvent, VerificationCycle


@login_required
def dashboard(request):
    assets = Asset.objects.all()
    total_assets = assets.count()
    gross_block = sum((a.gross_block() for a in assets), start=0) if total_assets else 0
    net_block = sum((a.net_book_value() for a in assets), start=0) if total_assets else 0

    by_status = assets.values("life_status").annotate(n=Count("id")).order_by()
    untagged = assets.filter(tag_status=Asset.TagStatus.UNTAGGED).count()

    due_for_verification = [a for a in assets.filter(life_status=Asset.LifeStatus.IN_USE) if a.verification_due()]

    pending_approvals = ApprovalRequest.objects.filter(status=ApprovalRequest.Status.PENDING)
    pending_cwip = CWIP.objects.filter(status__in=[CWIP.Status.OPEN, CWIP.Status.READY])
    pending_disposals = DisposalRequest.objects.filter(
        status__in=[DisposalRequest.Status.DRAFT, DisposalRequest.Status.PENDING_APPROVAL]
    )
    pending_transfers = TransferRequest.objects.filter(status=TransferRequest.Status.PENDING)
    open_mismatches = ScanEvent.objects.filter(location_mismatch=True, mismatch_resolved=False)
    active_cycles = VerificationCycle.objects.filter(status=VerificationCycle.Status.IN_PROGRESS)
    upcoming_revaluations_flag = RevaluationRecord.objects.filter(exceeds_10pct_threshold=True).count()

    insurance_expiring = assets.filter(
        insurance_renewal_date__isnull=False, insurance_renewal_date__gte=date.today()
    ).order_by("insurance_renewal_date")[:5]

    context = {
        "total_assets": total_assets,
        "gross_block": gross_block,
        "net_block": net_block,
        "by_status": by_status,
        "untagged": untagged,
        "due_for_verification_count": len(due_for_verification),
        "pending_approvals": pending_approvals[:8],
        "pending_approvals_count": pending_approvals.count(),
        "pending_cwip_count": pending_cwip.count(),
        "pending_disposals_count": pending_disposals.count(),
        "pending_transfers_count": pending_transfers.count(),
        "open_mismatches_count": open_mismatches.count(),
        "active_cycles": active_cycles,
        "revaluation_threshold_flags": upcoming_revaluations_flag,
        "insurance_expiring": insurance_expiring,
        "recent_assets": assets.order_by("-created_at")[:6],
    }
    return render(request, "dashboard.html", context)
