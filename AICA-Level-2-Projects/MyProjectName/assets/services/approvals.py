"""
Maker-checker helper (blueprint §05, §06): "no single user can create and
approve a disposal." Every workflow that must post to the books routes
through create_request() / decide() so the same different-user rule is
enforced in exactly one place.
"""

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from assets.models import ApprovalRequest


def create_request(requested_by, obj, action, summary=""):
    return ApprovalRequest.objects.create(
        content_type=ContentType.objects.get_for_model(obj),
        object_id=obj.pk,
        action=action,
        requested_by=requested_by,
        payload_summary=summary,
    )


class DifferentUserRequiredError(Exception):
    pass


def decide(approval, decided_by, approve, comment=""):
    if approval.status != ApprovalRequest.Status.PENDING:
        raise ValueError("This request has already been decided.")
    if not approval.can_be_decided_by(decided_by):
        raise DifferentUserRequiredError(
            "The approver must be a different user from the person who made this request."
        )
    approval.status = ApprovalRequest.Status.APPROVED if approve else ApprovalRequest.Status.REJECTED
    approval.decided_by = decided_by
    approval.decided_at = timezone.now()
    approval.decision_comment = comment
    approval.save()
    return approval
