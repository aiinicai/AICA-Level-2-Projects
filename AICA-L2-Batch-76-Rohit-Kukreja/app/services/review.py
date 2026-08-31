"""Review comments, status transitions and locking. Build Prompt v2 §10.

**Single-user build.** Role checks are gone — see `app.core.permissions` for
what that costs. The gates that do not depend on identity all remain: the
status sequence, zero blocking findings before manager review, zero open
comments before approval, one-way finalisation, and Create Revision as the
only route back.

Finalisation is one-way. A correction after it goes through Create Revision,
which supersedes the prior documents and leaves them byte-identical and
retrievable (§18.6, §18.7).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import LOCAL_ACTOR, require_transition
from app.models.engagement import Engagement
from app.models.enums import CommentStatus, DocumentStatus, EngagementStatus
from app.models.issuance import AuditLog, DocumentInstance, UdinRegister
from app.models.workflow import ReviewComment


class ReviewError(ValueError):
    """Message is safe to show a user."""


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# --------------------------------------------------------------------------
# Comments
# --------------------------------------------------------------------------


def raise_comment(
    session: Session,
    engagement_id: int,
    body: str,
    *,
    raised_by: str = LOCAL_ACTOR,
    field_key: str | None = None,
    document: str | None = None,
    parent_id: int | None = None,
) -> ReviewComment:
    if not body.strip():
        raise ReviewError("A comment cannot be empty")

    comment = ReviewComment(
        engagement_id=engagement_id,
        field_key=field_key,
        document=document,
        parent_id=parent_id,
        body=body.strip(),
        raised_by=raised_by,
        status=CommentStatus.OPEN,
    )
    session.add(comment)
    session.flush()
    session.add(
        AuditLog(
            entity="review_comment",
            entity_id=str(comment.comment_id),
            action="raise",
            field=field_key or "",
            actor=raised_by,
        )
    )
    session.flush()
    return comment


def respond_to_comment(
    session: Session, comment_id: int, body: str, *, responder: str = LOCAL_ACTOR
) -> ReviewComment:
    """A reply, which moves the thread to `responded` but never resolves it.

    Replying and resolving stay separate actions so the thread still records
    that a point was answered before it was closed. In a single-user build
    nothing stops the same person doing both — that separation was a role
    check, and the roles are gone.
    """
    parent = session.get(ReviewComment, comment_id)
    if parent is None:
        raise ReviewError("Comment not found")
    if parent.status is CommentStatus.RESOLVED:
        raise ReviewError("That comment is already resolved")

    reply = ReviewComment(
        engagement_id=parent.engagement_id,
        field_key=parent.field_key,
        document=parent.document,
        parent_id=parent.comment_id,
        body=body.strip(),
        raised_by=responder,
        status=CommentStatus.RESPONDED,
    )
    session.add(reply)
    parent.status = CommentStatus.RESPONDED
    session.flush()
    return reply


def resolve_comment(
    session: Session, comment_id: int, *, resolved_by: str = LOCAL_ACTOR
) -> ReviewComment:
    comment = session.get(ReviewComment, comment_id)
    if comment is None:
        raise ReviewError("Comment not found")
    comment.status = CommentStatus.RESOLVED
    comment.resolved_by = resolved_by
    comment.resolved_at = _now()
    session.add(
        AuditLog(
            entity="review_comment",
            entity_id=str(comment_id),
            action="resolve",
            actor=resolved_by,
        )
    )
    session.flush()
    return comment


def open_comments(session: Session, engagement_id: int) -> list[ReviewComment]:
    return list(
        session.scalars(
            select(ReviewComment)
            .where(
                ReviewComment.engagement_id == engagement_id,
                ReviewComment.status != CommentStatus.RESOLVED,
            )
            .order_by(ReviewComment.comment_id)
        ).all()
    )


def comment_thread(session: Session, engagement_id: int) -> list[ReviewComment]:
    return list(
        session.scalars(
            select(ReviewComment)
            .where(ReviewComment.engagement_id == engagement_id)
            .order_by(ReviewComment.comment_id)
        ).all()
    )


# --------------------------------------------------------------------------
# Status
# --------------------------------------------------------------------------


def advance(
    session: Session,
    engagement_id: int,
    target: EngagementStatus,
    *,
    actor: str = LOCAL_ACTOR,
    blocking_findings: int = 0,
) -> Engagement:
    engagement = session.get(Engagement, engagement_id)
    if engagement is None:
        raise ReviewError("Engagement not found")

    outstanding = session.scalar(
        select(func.count())
        .select_from(ReviewComment)
        .where(
            ReviewComment.engagement_id == engagement_id,
            ReviewComment.status != CommentStatus.RESOLVED,
        )
    )

    require_transition(
        engagement.status,
        target,
        blocking_findings=blocking_findings,
        open_comments=outstanding or 0,
    )

    before = engagement.status
    engagement.status = target
    session.add(
        AuditLog(
            entity="engagement",
            entity_id=str(engagement_id),
            action="status",
            before_json=json.dumps(before.value),
            after_json=json.dumps(target.value),
            actor=actor,
        )
    )
    session.flush()
    return engagement


def finalise(
    session: Session,
    engagement_id: int,
    *,
    actor: str = LOCAL_ACTOR,
    udin: str,
    partner_id: int | None = None,
    blocking_findings: int = 0,
) -> Engagement:
    """Lock the engagement and stamp every generated document `final` (§10)."""

    from app.core.validators import validate_udin

    engagement = session.get(Engagement, engagement_id)
    if engagement is None:
        raise ReviewError("Engagement not found")
    if engagement.is_locked:
        raise ReviewError(f"FY {engagement.fy_code} is already finalised")

    clean_udin = validate_udin(udin)

    advance(
        session,
        engagement_id,
        EngagementStatus.FINALISED,
        actor=actor,
        blocking_findings=blocking_findings,
    )

    engagement.locked_at = _now()
    engagement.locked_by = actor

    documents = session.scalars(
        select(DocumentInstance).where(
            DocumentInstance.engagement_id == engagement_id,
            DocumentInstance.status != DocumentStatus.SUPERSEDED,
        )
    ).all()
    for document in documents:
        document.status = DocumentStatus.FINAL
        document.udin = clean_udin

    if documents and partner_id is not None:
        session.add(
            UdinRegister(
                udin=clean_udin,
                doc_id=documents[0].doc_id,
                partner_id=partner_id,
                generated_on=_now().date(),
            )
        )

    session.add(
        AuditLog(
            entity="engagement",
            entity_id=str(engagement_id),
            action="finalise",
            after_json=json.dumps({"udin": clean_udin}),
            actor=actor,
        )
    )
    session.flush()
    return engagement


def create_revision(
    session: Session, engagement_id: int, reason: str, *, actor: str = LOCAL_ACTOR
) -> Engagement:
    """The only way to change a finalised engagement (§10, §18.7).

    Prior document instances become `superseded` — they are not deleted and
    not edited, so a reprint still reproduces what was signed.
    """
    if not reason.strip():
        raise ReviewError("A revision reason is required")

    engagement = session.get(Engagement, engagement_id)
    if engagement is None:
        raise ReviewError("Engagement not found")
    if not engagement.is_locked:
        raise ReviewError("Only a finalised engagement can be revised")

    superseded = session.scalars(
        select(DocumentInstance).where(
            DocumentInstance.engagement_id == engagement_id,
            DocumentInstance.status == DocumentStatus.FINAL,
        )
    ).all()
    for document in superseded:
        document.status = DocumentStatus.SUPERSEDED
        document.revision_reason = reason

    engagement.status = EngagementStatus.DATA_COLLECTION
    engagement.locked_at = None
    engagement.locked_by = ""

    session.add(
        AuditLog(
            entity="engagement",
            entity_id=str(engagement_id),
            action="create_revision",
            reason=reason,
            after_json=json.dumps({"superseded": len(superseded)}),
            actor=actor,
        )
    )
    session.flush()
    return engagement
