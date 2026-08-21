"""Workflow transitions in the single-user build. §10, §16.

The four-role model is gone at the firm's instruction (Step 4a). What these
tests now protect is the half that never depended on identity — the status
sequence, the two gates, and the one-way nature of finalisation.

The half that *did* depend on identity is gone, and the first test class
below records that plainly rather than leaving it to be discovered.
"""

from __future__ import annotations

import pytest

from app.core.permissions import (
    LOCAL_ACTOR,
    TransitionError,
    allowed_transitions,
    require_transition,
)
from app.models.enums import EngagementStatus
from app.services.auth import CsrfError, check_csrf

S = EngagementStatus


class TestWhatWasGivenUp:
    """Explicit record of the trade, so nobody has to infer it from absence."""

    def test_there_is_no_role_check_left_to_import(self) -> None:
        import app.core.permissions as permissions

        for gone in ("Role", "Action", "require", "PermissionDeniedError", "PERMISSIONS"):
            assert not hasattr(
                permissions, gone
            ), f"{gone} still exists — the single-user build should not have it"

    def test_every_action_is_attributed_to_the_same_actor(self) -> None:
        # Nothing distinguishes one person from another, so the change log
        # records what changed and when, not who. Inventing a name would be
        # worse than admitting that.
        assert LOCAL_ACTOR == "local user"

    def test_nothing_prevents_a_preparer_finalising_their_own_file(self) -> None:
        """The separation of duties in §10 rested entirely on roles.

        This passes deliberately. If the firm later wants attribution, the
        gates below do not need to move — only an actor selector is missing.
        """
        require_transition(S.PREPARED, S.APPROVED)
        require_transition(S.APPROVED, S.FINALISED)


class TestWorkflowSurvives:
    def test_the_happy_path(self) -> None:
        assert allowed_transitions(S.NOT_STARTED) == (S.DATA_COLLECTION,)
        # Decision 29 removed manager review and partner review: the person
        # who prepares the file finalises it, so those two described a handover
        # that does not happen in this firm.
        require_transition(S.DATA_COLLECTION, S.PREPARED)
        require_transition(S.PREPARED, S.APPROVED)
        require_transition(S.APPROVED, S.FINALISED)

    def test_finalised_is_terminal_but_for_archiving(self) -> None:
        # §18.7 — corrections go through Create Revision, never a status move.
        assert allowed_transitions(S.FINALISED) == (S.ARCHIVED,)
        assert allowed_transitions(S.ARCHIVED) == ()

    def test_cannot_skip_review(self) -> None:
        with pytest.raises(TransitionError, match="Cannot move"):
            require_transition(S.DATA_COLLECTION, S.APPROVED)

    def test_cannot_reopen_a_finalised_engagement(self) -> None:
        with pytest.raises(TransitionError):
            require_transition(S.FINALISED, S.DATA_COLLECTION)

    def test_a_file_may_be_returned_for_correction(self) -> None:
        """Still possible with the reviewer states gone — from Prepared, which
        is now the only place a file sits before approval."""
        require_transition(S.PREPARED, S.DATA_COLLECTION)


class TestGatesSurvive:
    """Both gates are about the state of the file, not about who holds it."""

    def test_blocking_findings_stop_approval(self) -> None:
        """The findings gate used to sit on the move into manager review.

        That state is gone (decision 29), so the gate MOVED to approval rather
        than going with it. Losing it would have been the real damage: removing
        a reviewer is a decision about who works on the file, not a decision to
        let an incomplete one through.
        """
        with pytest.raises(TransitionError, match="3 blocking finding"):
            require_transition(S.PREPARED, S.APPROVED, blocking_findings=3)

    def test_a_clean_file_advances(self) -> None:
        require_transition(S.PREPARED, S.APPROVED, blocking_findings=0)

    def test_open_comments_stop_approval(self) -> None:
        with pytest.raises(TransitionError, match="2 open review comment"):
            require_transition(S.PREPARED, S.APPROVED, open_comments=2)

    def test_both_gates_now_sit_on_the_same_move(self) -> None:
        """This test previously asserted the OPPOSITE — that findings did not
        block approval, because they were caught one step earlier. With that
        step gone, a file with findings must not reach Approved."""
        with pytest.raises(TransitionError, match="blocking finding"):
            require_transition(S.PREPARED, S.APPROVED, blocking_findings=5, open_comments=0)
        require_transition(S.PREPARED, S.APPROVED, blocking_findings=0, open_comments=0)


class TestCsrf:
    """Kept even without a session: it still stops another page POSTing here."""

    def test_matching_tokens_pass(self) -> None:
        check_csrf("abc123", "abc123")

    @pytest.mark.parametrize(
        ("cookie", "form"), [("abc", "def"), (None, "abc"), ("abc", None), (None, None)]
    )
    def test_mismatch_or_absence_fails(self, cookie: str | None, form: str | None) -> None:
        with pytest.raises(CsrfError):
            check_csrf(cookie, form)


class TestNoPasswordMachineryRemains:
    def test_hashing_and_sessions_are_gone(self) -> None:
        import app.services.auth as auth

        for gone in (
            "hash_password",
            "verify_password",
            "authenticate",
            "issue_session",
            "read_session",
            "Principal",
            "SESSION_COOKIE",
        ):
            assert not hasattr(auth, gone), f"{gone} survived the auth removal"
