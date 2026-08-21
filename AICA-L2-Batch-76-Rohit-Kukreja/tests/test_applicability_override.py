"""Overrides on the applicability engine.

Demonstrated throughout on `kam`, a flag the engine still computes from company
class. The example has moved twice in a day: these first used `ifc`, then `csr`,
and both became DECLARED on 20 August 2026 — the auditor states them and the
engine infers nothing, so an "override" on either is the answer itself, carries
no computed reasoning beside it, and deliberately requires no reason.

Only a flag with a computed answer has anything worth overruling, and after that
change the ones left turn on company class rather than on any figure. Declared
behaviour is covered in tests/test_applicability.py::TestNoFlagReadsAFigure.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.engagement import Engagement
from app.models.issuance import AuditLog
from app.models.masters import ClientProfile
from app.services.applicability import (
    OverrideError,
    overridable,
    resolve,
    set_override,
    stored_overrides,
)
from tests.test_client_routes import _sign_in

# A real financial year end. `profile.valid_from` is 2010 and predates the
# IFC rule's commencement, which makes every basis read "not in force".
FY = date(2026, 3, 31)


@pytest.fixture
def profile(db: Session, client_id: int) -> ClientProfile:
    found = db.scalar(
        select(ClientProfile).where(
            ClientProfile.client_id == client_id, ClientProfile.is_current.is_(True)
        )
    )
    assert found is not None
    return found


@pytest.fixture
def engagement_id(db: Session, client_id: int) -> int:
    found = db.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == "2025-26")
    )
    assert found is not None
    return found.engagement_id


def _rules():
    return get_settings().content_path / "applicability_rules.yaml"


class TestKamOverride:
    """The flag the firm asked for a control on."""

    def test_ifc_is_overridable(self, profile: ClientProfile) -> None:
        assert "kam" in overridable(profile)

    def test_computed_kam_for_the_seeded_client(self, db: Session, profile: ClientProfile) -> None:
        effective, computed = resolve(profile, FY, _rules())
        # A small private company with no figures recorded: exempt.
        assert computed.kam.value is False
        assert effective.kam.value is False

    def test_forcing_kam_applicable(self, db: Session, profile: ClientProfile) -> None:
        set_override(db, profile, "kam", "applicable", reason="Reporting KAM voluntarily")
        effective, computed = resolve(profile, FY, _rules())
        assert effective.kam.value is True
        assert effective.kam.overridden is True
        # The engine's own answer is still there to be seen.
        assert computed.kam.value is False

    def test_the_computed_basis_survives_the_override(
        self, db: Session, profile: ClientProfile
    ) -> None:
        set_override(db, profile, "kam", "applicable", reason="Reporting KAM voluntarily")
        effective, _ = resolve(profile, FY, _rules())
        assert "computed: False" in effective.kam.basis
        assert "does not apply to pvt" in effective.kam.basis

    def test_reverting_to_computed(self, db: Session, profile: ClientProfile) -> None:
        set_override(db, profile, "kam", "applicable", reason="Reporting KAM voluntarily")
        set_override(db, profile, "kam", "computed", reason="")
        effective, _ = resolve(profile, FY, _rules())
        assert effective.ifc.overridden is False
        assert effective.kam.value is False

    def test_stored_overrides_only_lists_flags_that_carry_one(
        self, db: Session, profile: ClientProfile
    ) -> None:
        """The seeded profile already states all five declared flags.

        Declared flags are stored in the same columns an override uses -- the
        auditor's answer has to reach `compute` somehow -- so they appear here
        too, whether the answer was yes or no. What matters is that nothing
        else does.
        """
        stated = {
            "caro": True,
            "ifc": True,
            "csr": False,
            "internal_audit": False,
            "secretarial_audit": False,
        }
        assert stored_overrides(profile) == stated
        set_override(db, profile, "kam", "applicable", reason="Reporting KAM voluntarily")
        assert stored_overrides(profile) == {**stated, "kam": True}


class TestGuards:
    def test_a_reason_is_required_to_overrule(self, db: Session, profile: ClientProfile) -> None:
        with pytest.raises(OverrideError, match="reason is required"):
            set_override(db, profile, "kam", "not_applicable", reason="   ")

    def test_no_reason_needed_to_revert(self, db: Session, profile: ClientProfile) -> None:
        set_override(db, profile, "kam", "computed", reason="")

    def test_an_unknown_flag_is_refused(self, db: Session, profile: ClientProfile) -> None:
        with pytest.raises(OverrideError, match="cannot be overridden"):
            set_override(db, profile, "nonsense", "applicable", reason="x")

    def test_an_invalid_choice_is_refused(self, db: Session, profile: ClientProfile) -> None:
        with pytest.raises(OverrideError, match="not a valid choice"):
            set_override(db, profile, "kam", "maybe", reason="x")


class TestAuditLog:
    def test_an_override_is_recorded_with_its_reason(
        self, db: Session, profile: ClientProfile
    ) -> None:
        set_override(db, profile, "kam", "applicable", reason="Reporting KAM voluntarily")
        entry = db.scalar(
            select(AuditLog)
            .where(AuditLog.action == "applicability_override")
            .order_by(AuditLog.log_id.desc())
        )
        assert entry is not None
        assert entry.field == "kam"
        assert entry.reason == "Reporting KAM voluntarily"
        assert '"overridden": true' in entry.after_json


class TestOverHttp:
    def test_the_page_offers_a_control_for_kam(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        _sign_in(app_client)
        body = app_client.get(f"/engagements/{engagement_id}/applicability").text
        assert 'name="flag" value="kam"' in body
        assert "Use the computed answer" in body
        assert "Applicable — override" in body

    def test_setting_it_through_the_form_persists(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        csrf = _sign_in(app_client)
        response = app_client.post(
            f"/engagements/{engagement_id}/applicability",
            data={
                "csrf_token": csrf,
                "flag": "kam",
                "choice": "applicable",
                "reason": "Lender requires IFC reporting",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        body = app_client.get(f"/engagements/{engagement_id}/applicability").text
        assert "overridden" in body
        assert "Computed answer" in body

    def test_a_missing_reason_is_refused_with_a_message(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        csrf = _sign_in(app_client)
        response = app_client.post(
            f"/engagements/{engagement_id}/applicability",
            data={"csrf_token": csrf, "flag": "kam", "choice": "applicable", "reason": ""},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "reason is required" in response.text
        assert "Traceback" not in response.text

    def test_a_finalised_engagement_refuses(
        self, app_client: TestClient, db: Session, client_id: int
    ) -> None:
        locked = db.scalar(
            select(Engagement).where(
                Engagement.client_id == client_id, Engagement.fy_code == "2024-25"
            )
        )
        assert locked is not None
        csrf = _sign_in(app_client)
        response = app_client.post(
            f"/engagements/{locked.engagement_id}/applicability",
            data={"csrf_token": csrf, "flag": "kam", "choice": "applicable", "reason": "x"},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Create Revision" in response.text


class TestADerivedFlagCannotBeSetOnItsOwn:
    """`full_board_report` is the inverse of `abridged_board_report`.

    Offering a control for it would either write to a column that does not
    exist or, worse, succeed — leaving a company abridged by the engine and
    printing the full Rule 8 report. The supported path is to override the
    flag it derives from, which moves both together.
    """

    def test_it_is_not_offered_as_overridable(self, profile: ClientProfile) -> None:
        assert "full_board_report" not in overridable(profile)

    def test_setting_it_directly_is_refused(self, db: Session, profile: ClientProfile) -> None:
        with pytest.raises(OverrideError, match="derived"):
            set_override(db, profile, "full_board_report", "applicable", reason="x")

    def test_overriding_what_it_derives_from_moves_it(
        self, db: Session, profile: ClientProfile
    ) -> None:
        set_override(db, profile, "abridged_board_report", "applicable", reason="Treated as small")
        effective, _ = resolve(profile, FY, _rules())
        assert effective.abridged_board_report.value is True
        assert effective.full_board_report.value is False
