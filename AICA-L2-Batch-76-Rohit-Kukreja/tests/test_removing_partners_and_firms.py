"""Deleting a partner or a firm. Partner's request, 20 August 2026.

Decision 63. The rule under every test here: a record may be removed only when
nothing ISSUED points at it. What the guards protect is not the row — it is the
ability to answer, years later, who signed a report and under which UDIN.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engagement import Engagement
from app.models.enums import EngagementStatus
from app.models.issuance import AuditLog, DocumentInstance, UdinRegister
from app.models.masters import Client, FieldDefault, Firm, Partner
from app.services.client import (
    ProfileError,
    add_partner,
    create_firm,
    delete_firm,
    delete_partner,
    firm_blockers,
    partner_blockers,
)
from tests.test_client_routes import _sign_in


def _spare_partner(db: Session, firm_id: int, name: str = "New Joiner") -> Partner:
    """A partner who has signed nothing."""
    partner = add_partner(
        db, firm_id=firm_id, partner_name=name, membership_no="123456", is_signing=False
    )
    db.flush()
    return partner


def _a_document(db: Session) -> int:
    """Any issued document, so a UDIN has something to point at."""
    existing = db.scalar(select(DocumentInstance))
    if existing is not None:
        return existing.doc_id
    engagement = db.scalar(select(Engagement))
    assert engagement is not None
    doc = DocumentInstance(
        engagement_id=engagement.engagement_id,
        doc_type="auditors_report",
        version_no=99,
        template_version="test",
        payload_json="{}",
        content_sha256="0" * 64,
    )
    db.add(doc)
    db.flush()
    return doc.doc_id


class TestRemovingAPartner:
    def test_one_who_signed_nothing_goes(self, db: Session) -> None:
        firm = db.scalar(select(Firm))
        assert firm is not None
        partner = _spare_partner(db, firm.firm_id)
        partner_id = partner.partner_id

        assert partner_blockers(db, partner_id) == {}
        assert delete_partner(db, partner_id) == "New Joiner"
        assert db.get(Partner, partner_id) is None

    def test_the_removal_is_recorded(self, db: Session) -> None:
        """The row goes; the fact that it went does not.

        `audit_log` has no delete path anywhere in the application, so this
        entry is what answers "there used to be a partner here" later.
        """
        firm = db.scalar(select(Firm))
        assert firm is not None
        partner = _spare_partner(db, firm.firm_id, "Recorded Exit")
        delete_partner(db, partner.partner_id, deleted_by="tester")
        db.flush()

        entry = db.scalar(
            select(AuditLog)
            .where(AuditLog.entity == "partner", AuditLog.action == "delete")
            .order_by(AuditLog.log_id.desc())
        )
        assert entry is not None
        assert "Recorded Exit" in entry.before_json
        assert entry.actor == "tester"

    def test_one_named_on_a_finalised_year_is_refused(self, db: Session) -> None:
        firm = db.scalar(select(Firm))
        assert firm is not None
        partner = _spare_partner(db, firm.firm_id, "Signed Something")
        engagement = db.scalar(select(Engagement))
        assert engagement is not None
        engagement.partner_id = partner.partner_id
        engagement.status = EngagementStatus.FINALISED
        db.flush()

        assert "finalised financial years they signed" in partner_blockers(db, partner.partner_id)
        with pytest.raises(ProfileError, match="cannot be deleted"):
            delete_partner(db, partner.partner_id)
        assert db.get(Partner, partner.partner_id) is not None

    def test_one_holding_a_udin_is_refused(self, db: Session) -> None:
        """A UDIN is a public record against that member's own number."""
        firm = db.scalar(select(Firm))
        assert firm is not None
        partner = _spare_partner(db, firm.firm_id, "Udin Holder")
        db.add(
            UdinRegister(
                udin="26123456ABCDEF1234",
                doc_id=_a_document(db),
                partner_id=partner.partner_id,
                generated_on=date(2026, 8, 1),
            )
        )
        db.flush()

        assert "UDINs generated in their name" in partner_blockers(db, partner.partner_id)
        with pytest.raises(ProfileError, match="cannot be deleted"):
            delete_partner(db, partner.partner_id)

    def test_an_open_year_blocks_too_rather_than_being_cleared(self, db: Session) -> None:
        """`Engagement.partner_id` is nullable, so this COULD be silently
        cleared. It must not be: clearing it changes who an unissued report
        goes out under, and nothing on screen would say so.
        """
        firm = db.scalar(select(Firm))
        assert firm is not None
        partner = _spare_partner(db, firm.firm_id, "Assigned Open")
        engagement = db.scalar(
            select(Engagement).where(
                Engagement.status.notin_((EngagementStatus.FINALISED, EngagementStatus.ARCHIVED))
            )
        )
        assert engagement is not None
        engagement.partner_id = partner.partner_id
        db.flush()

        assert "open financial years assigned to them" in partner_blockers(db, partner.partner_id)
        with pytest.raises(ProfileError, match="cannot be deleted"):
            delete_partner(db, partner.partner_id)

    def test_the_refusal_names_what_is_holding_them(self, db: Session) -> None:
        """ "Cannot be deleted" with no reason is a dead end, not an answer."""
        firm = db.scalar(select(Firm))
        assert firm is not None
        partner = _spare_partner(db, firm.firm_id, "Blocked Person")
        engagement = db.scalar(select(Engagement))
        assert engagement is not None
        engagement.partner_id = partner.partner_id
        engagement.status = EngagementStatus.FINALISED
        db.flush()

        with pytest.raises(ProfileError) as caught:
            delete_partner(db, partner.partner_id)
        message = str(caught.value)
        assert "finalised" in message
        assert "retire" in message.lower()


class TestRemovingAFirm:
    def test_a_firm_with_clients_is_refused(self, db: Session) -> None:
        client = db.scalar(select(Client))
        assert client is not None
        blockers = firm_blockers(db, client.firm_id)
        assert "clients on its register" in blockers
        with pytest.raises(ProfileError, match="cannot be deleted"):
            delete_firm(db, client.firm_id)

    def test_the_last_firm_stays(self, db: Session) -> None:
        """An installation with no firm renders no letterhead and no signature.

        `bootstrap.first_run` creates one for exactly that reason, so allowing
        the final one to be removed would mean a screen that empties itself and
        a placeholder that reappears on the next start.
        """
        for firm in db.scalars(select(Firm)).all()[1:]:
            db.delete(firm)
        db.flush()
        remaining = db.scalar(select(Firm))
        assert remaining is not None
        assert any("only firm" in key for key in firm_blockers(db, remaining.firm_id))

    def test_an_empty_firm_goes_with_its_partners_and_defaults(self, db: Session) -> None:
        """Both are the firm's own configuration and mean nothing without it."""
        firm = create_firm(db, firm_name="Spare & Co", frn="099099W")
        db.flush()
        _spare_partner(db, firm.firm_id, "Spare Partner")
        db.add(FieldDefault(firm_id=firm.firm_id, field_key="bdr.dividend", value="none"))
        db.flush()
        firm_id = firm.firm_id

        assert firm_blockers(db, firm_id) == {}
        assert delete_firm(db, firm_id) == "Spare & Co"
        db.flush()

        assert db.get(Firm, firm_id) is None
        assert db.scalars(select(Partner).where(Partner.firm_id == firm_id)).all() == []
        assert db.scalars(select(FieldDefault).where(FieldDefault.firm_id == firm_id)).all() == []

    def test_a_firm_whose_partner_signed_is_refused(self, db: Session) -> None:
        """The partner guard is not bypassable by deleting the firm instead."""
        firm = create_firm(db, firm_name="Held & Co", frn="098098W")
        db.flush()
        partner = _spare_partner(db, firm.firm_id, "Held Partner")
        db.add(
            UdinRegister(
                udin="26999999ZZZZZZ9999",
                doc_id=_a_document(db),
                partner_id=partner.partner_id,
                generated_on=date(2026, 8, 1),
            )
        )
        db.flush()

        assert "partners named on issued documents" in firm_blockers(db, firm.firm_id)
        with pytest.raises(ProfileError, match="cannot be deleted"):
            delete_firm(db, firm.firm_id)


class TestOverHttp:
    def test_the_name_must_be_typed_to_confirm(self, app_client: TestClient, db: Session) -> None:
        """A wrong row confirmed is the failure mode a dialog does not prevent."""
        firm = db.scalar(select(Firm))
        assert firm is not None
        partner = _spare_partner(db, firm.firm_id, "Typed Confirm")
        db.commit()

        csrf = _sign_in(app_client)
        response = app_client.post(
            f"/admin/partners/{partner.partner_id}/delete",
            data={"csrf_token": csrf, "confirm_name": "wrong name"},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "name exactly" in response.text
        assert db.get(Partner, partner.partner_id) is not None

    def test_the_right_name_removes_them(self, app_client: TestClient, db: Session) -> None:
        firm = db.scalar(select(Firm))
        assert firm is not None
        partner = _spare_partner(db, firm.firm_id, "Goes Away")
        partner_id = partner.partner_id
        db.commit()

        csrf = _sign_in(app_client)
        response = app_client.post(
            f"/admin/partners/{partner_id}/delete",
            data={"csrf_token": csrf, "confirm_name": "Goes Away"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        db.expire_all()
        assert db.get(Partner, partner_id) is None

    def test_a_held_partner_offers_no_control(self, app_client: TestClient, db: Session) -> None:
        """The page says what holds them instead of showing a button that refuses."""
        engagement = db.scalar(select(Engagement))
        assert engagement is not None
        firm = db.scalar(select(Firm))
        assert firm is not None
        partner = _spare_partner(db, firm.firm_id, "Cannot Go")
        engagement.partner_id = partner.partner_id
        engagement.status = EngagementStatus.FINALISED
        db.commit()

        _sign_in(app_client)
        body = app_client.get("/admin/firm").text
        assert "Held by" in body
