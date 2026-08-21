"""Workflow transitions. Build Prompt v2 §10.

**Single-user build.** The firm asked for a local application anyone can open
with no login and no accounts, so the four-role model in §10 has been removed
— Decision 9 of the Review and Sign-Off Protocol expressly allows that.

What went with it, stated plainly because it matters:

  · Nothing stops the person who prepared a file from approving and
    finalising it. The preparer/manager/partner separation is gone.
  · UDIN entry is no longer reserved to a partner.
  · The audit log records *what* changed and *when*, but not *who*. It is a
    change history, not evidence of review.

What survives, because none of it depends on identity:

  · the status sequence itself, and the fact that finalisation is one-way;
  · the gate requiring zero blocking findings before manager review;
  · the gate requiring zero open comments before approval;
  · locking, and Create Revision as the only route back.

If the firm later wants attribution without passwords, the cheapest change is
a "who are you?" selector feeding `actor` — the workflow gates below would
not need to move.
"""

from __future__ import annotations

from app.models.enums import EngagementStatus

# The actor recorded against every change. A single-user build has no way to
# tell one person from another, and inventing a name would be worse than
# admitting that.
LOCAL_ACTOR = "local user"


class TransitionError(ValueError):
    """An illegal workflow move. Message is safe to show a user."""


_TRANSITIONS: dict[EngagementStatus, tuple[EngagementStatus, ...]] = {
    EngagementStatus.NOT_STARTED: (EngagementStatus.DATA_COLLECTION,),
    EngagementStatus.DATA_COLLECTION: (EngagementStatus.PREPARED,),
    EngagementStatus.PREPARED: (
        EngagementStatus.APPROVED,
        EngagementStatus.DATA_COLLECTION,
    ),
    EngagementStatus.APPROVED: (EngagementStatus.FINALISED,),
    # Finalised is terminal but for archiving. Corrections go through
    # Create Revision, never through a status change (§10, §18.7).
    EngagementStatus.FINALISED: (EngagementStatus.ARCHIVED,),
    EngagementStatus.ARCHIVED: (),
}


def allowed_transitions(status: EngagementStatus) -> tuple[EngagementStatus, ...]:
    return _TRANSITIONS[status]


def require_transition(
    current: EngagementStatus,
    target: EngagementStatus,
    *,
    blocking_findings: int = 0,
    open_comments: int = 0,
) -> None:
    """Check the move is legal and the gates are clear.

    §10: advancing to Manager Review requires zero blocking findings;
    advancing to Approved requires zero open review comments. Both gates are
    about the state of the file, not about who is holding it, so both survive
    the removal of roles.
    """
    if target not in _TRANSITIONS[current]:
        raise TransitionError(f"Cannot move from {current.value} to {target.value}")

    # Both gates now sit on the single move to Approved. The reviewer STATES
    # were removed (decision 29); the checks they carried were not, because
    # they are about the state of the file rather than who is holding it, and
    # dropping them with the states would have been the real loss.
    if target is EngagementStatus.APPROVED and blocking_findings:
        raise TransitionError(
            f"{blocking_findings} blocking finding(s) must be resolved before approval"
        )
    if target is EngagementStatus.APPROVED and open_comments:
        raise TransitionError(
            f"{open_comments} open review comment(s) must be resolved before approval"
        )
