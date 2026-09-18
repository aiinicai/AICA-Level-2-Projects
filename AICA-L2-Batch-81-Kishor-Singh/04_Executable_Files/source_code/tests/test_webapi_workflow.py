"""Tests for webapi.workflow: the maker-checker state machine, in isolation from the DB/API."""
from __future__ import annotations

import pytest

from webapi.models import DocumentStatus, UserRole
from webapi.workflow import WorkflowError, apply_transition, content_change_resets_to_draft, find_transition


def test_maker_can_submit_draft_for_review():
    result = apply_transition(DocumentStatus.DRAFT, "submit_for_review", UserRole.MAKER, "user-1", None)
    assert result == DocumentStatus.PREPARED


def test_checker_can_approve_document_prepared_by_someone_else():
    result = apply_transition(DocumentStatus.IN_REVIEW, "approve", UserRole.CHECKER, "checker-1", "maker-1")
    assert result == DocumentStatus.APPROVED


def test_maker_cannot_approve_own_document_self_approval_blocked():
    with pytest.raises(WorkflowError, match="Separation of duties"):
        apply_transition(DocumentStatus.IN_REVIEW, "approve", UserRole.CHECKER, "same-user", "same-user")


def test_maker_cannot_perform_checker_only_action():
    with pytest.raises(WorkflowError, match="Allowed roles"):
        apply_transition(DocumentStatus.IN_REVIEW, "approve", UserRole.MAKER, "user-1", "user-2")


def test_admin_can_approve_even_if_admin_was_the_preparer():
    # Admins are the one role deliberately exempt from block_same_actor in
    # practice? -- no: block_same_actor still applies to Admin identity match.
    # This test documents that an Admin acting as both maker and approver
    # under the SAME identity is still blocked -- only a *different* admin
    # or a checker/approver identity can approve.
    with pytest.raises(WorkflowError):
        apply_transition(DocumentStatus.IN_REVIEW, "approve", UserRole.ADMIN, "admin-1", "admin-1")


def test_different_admin_can_approve():
    result = apply_transition(DocumentStatus.IN_REVIEW, "approve", UserRole.ADMIN, "admin-2", "admin-1")
    assert result == DocumentStatus.APPROVED


def test_invalid_action_from_status_raises():
    with pytest.raises(WorkflowError, match="not a valid action"):
        apply_transition(DocumentStatus.DRAFT, "approve", UserRole.CHECKER, "user-1", None)


def test_changes_requested_returns_to_prepared_via_resubmit():
    result = apply_transition(DocumentStatus.CHANGES_REQUESTED, "resubmit", UserRole.MAKER, "maker-1", None)
    assert result == DocumentStatus.PREPARED


def test_full_happy_path_to_archived():
    status = DocumentStatus.DRAFT
    status = apply_transition(status, "submit_for_review", UserRole.MAKER, "maker", None)
    status = apply_transition(status, "send_to_checker", UserRole.MAKER, "maker", None)
    status = apply_transition(status, "approve", UserRole.CHECKER, "checker", "maker")
    assert status == DocumentStatus.APPROVED
    status = apply_transition(status, "start_signing", UserRole.SIGNATORY, "signer", None)
    status = apply_transition(status, "confirm_signed", UserRole.SIGNATORY, "signer", None)
    status = apply_transition(status, "verify", UserRole.AUDITOR, "auditor", None)
    status = apply_transition(status, "release", UserRole.APPROVER, "approver", None)
    status = apply_transition(status, "archive", UserRole.ADMIN, "admin", None)
    assert status == DocumentStatus.ARCHIVED


def test_cancel_allowed_from_non_terminal_state_admin_only():
    result = apply_transition(DocumentStatus.IN_REVIEW, "cancel", UserRole.ADMIN, "admin", None)
    assert result == DocumentStatus.CANCELLED


def test_cancel_denied_for_non_admin():
    with pytest.raises(WorkflowError):
        apply_transition(DocumentStatus.IN_REVIEW, "cancel", UserRole.MAKER, "maker", None)


def test_cancel_not_allowed_from_terminal_state():
    with pytest.raises(WorkflowError):
        apply_transition(DocumentStatus.ARCHIVED, "cancel", UserRole.ADMIN, "admin", None)


def test_reject_and_request_changes_also_blocked_for_same_actor():
    with pytest.raises(WorkflowError, match="Separation of duties"):
        apply_transition(DocumentStatus.IN_REVIEW, "reject", UserRole.APPROVER, "x", "x")
    with pytest.raises(WorkflowError, match="Separation of duties"):
        apply_transition(DocumentStatus.IN_REVIEW, "request_changes", UserRole.APPROVER, "x", "x")


def test_find_transition_returns_metadata():
    t = find_transition(DocumentStatus.DRAFT, "submit_for_review")
    assert t.to_status == DocumentStatus.PREPARED
    assert UserRole.MAKER in t.allowed_roles


def test_content_change_resets_to_draft_rules():
    assert not content_change_resets_to_draft(DocumentStatus.DRAFT)
    for status in (
        DocumentStatus.PREPARED, DocumentStatus.IN_REVIEW, DocumentStatus.APPROVED,
        DocumentStatus.SIGNED, DocumentStatus.RELEASED,
    ):
        assert content_change_resets_to_draft(status)
