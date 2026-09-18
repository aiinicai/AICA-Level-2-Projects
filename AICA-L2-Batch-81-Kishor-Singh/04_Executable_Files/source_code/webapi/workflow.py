"""Maker-checker document workflow state machine.

This is the actual enforcement point for separation of duties: a
transition function decides, given the acting user's role and identity,
whether a requested status change is allowed -- server-side, on every
request, regardless of what a client claims. There is no client-trusted
"I am an approver" flag anywhere in this module.

State machine (per the project's design brief):

    Draft -> Prepared -> In Review -> {Changes Requested, Rejected, Approved}
    Approved -> Signing -> Signed -> Verified -> Released -> Archived
    (Any state) -> Cancelled  [Admin only]

Uploading a new document version while status is anything past DRAFT resets
it to DRAFT -- an approval is tied to a specific reviewed version, so a
content change must invalidate it rather than silently carrying forward.
"""
from __future__ import annotations

from dataclasses import dataclass

from webapi.models import DocumentStatus, UserRole


class WorkflowError(Exception):
    """Raised for any disallowed transition -- always safe to show to the caller."""


@dataclass(frozen=True)
class Transition:
    from_status: DocumentStatus
    to_status: DocumentStatus
    action: str
    allowed_roles: frozenset[UserRole]
    #: If True, the acting user must NOT be the same person who most
    #: recently moved the document into `from_status` (self-approval block).
    block_same_actor: bool = False


_TRANSITIONS: list[Transition] = [
    Transition(DocumentStatus.DRAFT, DocumentStatus.PREPARED, "submit_for_review", frozenset({UserRole.MAKER, UserRole.ADMIN})),
    Transition(DocumentStatus.PREPARED, DocumentStatus.IN_REVIEW, "send_to_checker", frozenset({UserRole.MAKER, UserRole.ADMIN})),
    Transition(
        DocumentStatus.IN_REVIEW, DocumentStatus.APPROVED, "approve",
        frozenset({UserRole.CHECKER, UserRole.APPROVER, UserRole.ADMIN}), block_same_actor=True,
    ),
    Transition(
        DocumentStatus.IN_REVIEW, DocumentStatus.CHANGES_REQUESTED, "request_changes",
        frozenset({UserRole.CHECKER, UserRole.APPROVER, UserRole.ADMIN}), block_same_actor=True,
    ),
    Transition(
        DocumentStatus.IN_REVIEW, DocumentStatus.REJECTED, "reject",
        frozenset({UserRole.CHECKER, UserRole.APPROVER, UserRole.ADMIN}), block_same_actor=True,
    ),
    Transition(DocumentStatus.CHANGES_REQUESTED, DocumentStatus.PREPARED, "resubmit", frozenset({UserRole.MAKER, UserRole.ADMIN})),
    Transition(DocumentStatus.APPROVED, DocumentStatus.SIGNING, "start_signing", frozenset({UserRole.SIGNATORY, UserRole.ADMIN})),
    Transition(DocumentStatus.SIGNING, DocumentStatus.SIGNED, "confirm_signed", frozenset({UserRole.SIGNATORY, UserRole.ADMIN})),
    Transition(DocumentStatus.SIGNED, DocumentStatus.VERIFIED, "verify", frozenset({UserRole.AUDITOR, UserRole.ADMIN})),
    Transition(DocumentStatus.VERIFIED, DocumentStatus.RELEASED, "release", frozenset({UserRole.APPROVER, UserRole.ADMIN})),
    Transition(DocumentStatus.RELEASED, DocumentStatus.ARCHIVED, "archive", frozenset({UserRole.ADMIN})),
]

# Cancellation is allowed from any non-terminal state, admin only.
_TERMINAL_STATES = {DocumentStatus.ARCHIVED, DocumentStatus.CANCELLED}


def find_transition(from_status: DocumentStatus, action: str) -> Transition:
    for t in _TRANSITIONS:
        if t.from_status == from_status and t.action == action:
            return t
    if action == "cancel" and from_status not in _TERMINAL_STATES:
        return Transition(from_status, DocumentStatus.CANCELLED, "cancel", frozenset({UserRole.ADMIN}))
    raise WorkflowError(f"'{action}' is not a valid action from status '{from_status.value}'.")


def apply_transition(
    from_status: DocumentStatus, action: str, actor_role: UserRole, actor_id: str, last_actor_id: str | None
) -> DocumentStatus:
    """Validate and return the resulting status, or raise WorkflowError.

    ``last_actor_id`` is whoever performed the transition that put the
    document into ``from_status`` -- used to enforce that the same person
    cannot both prepare and approve/reject/request-changes on a document.
    """
    transition = find_transition(from_status, action)
    if actor_role not in transition.allowed_roles:
        allowed = ", ".join(r.value for r in transition.allowed_roles)
        raise WorkflowError(f"Role '{actor_role.value}' cannot perform '{action}'. Allowed roles: {allowed}.")
    if transition.block_same_actor and last_actor_id is not None and actor_id == last_actor_id:
        raise WorkflowError(
            "Separation of duties: you cannot review/approve a document you yourself prepared or submitted."
        )
    return transition.to_status


def content_change_resets_to_draft(current_status: DocumentStatus) -> bool:
    """Whether uploading a new version while in this status must reset the
    document to DRAFT (an approval is tied to a specific version)."""
    return current_status not in (DocumentStatus.DRAFT,)
