"""Partner management. Added 17 August 2026.

The firm screen listed partners read-only, so a firm could not record its own
partners — even though the signing partner's name and membership number appear
on every document the tool issues. Reported by the partner after trying to use
it.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.masters import Partner
from app.services.client import ProfileError, add_partner, signing_partners, update_partner
from tests.test_client_routes import _csrf


class TestAddPartner:
    def test_the_firm_page_offers_a_form(self, app_client: TestClient) -> None:
        body = app_client.get("/admin/firm").text
        assert 'action="/admin/partners"' in body, "no way to add a partner"
        assert 'name="membership_no"' in body

    def test_a_partner_is_added(self, app_client: TestClient, db: Session) -> None:
        response = app_client.post(
            "/admin/partners",
            data={
                "csrf_token": _csrf(app_client),
                "partner_name": "S. Iyer",
                "membership_no": "123456",
                "is_signing": "on",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303, response.text[:300]
        added = db.scalar(select(Partner).where(Partner.membership_no == "123456"))
        assert added is not None
        assert added.partner_name == "S. Iyer"
        assert added.is_signing is True
        assert added.active is True

    def test_a_bad_membership_number_is_refused_with_a_sentence(self, db: Session) -> None:
        from app.core.validators import ValidationError

        with pytest.raises(ValidationError, match=r"[Mm]embership"):
            add_partner(db, firm_id=1, partner_name="X", membership_no="12")

    def test_a_duplicate_membership_number_is_refused(self, db: Session) -> None:
        existing = db.scalar(select(Partner))
        assert existing is not None
        with pytest.raises(ProfileError, match="already recorded"):
            add_partner(
                db, firm_id=1, partner_name="Someone Else", membership_no=existing.membership_no
            )

    def test_a_partner_needs_a_name(self, db: Session) -> None:
        with pytest.raises(ProfileError, match="name is required"):
            add_partner(db, firm_id=1, partner_name="   ", membership_no="654321")


class TestUpdatePartner:
    def test_a_partner_can_be_renamed(self, app_client: TestClient, db: Session) -> None:
        existing = db.scalar(select(Partner))
        assert existing is not None
        response = app_client.post(
            f"/admin/partners/{existing.partner_id}",
            data={
                "csrf_token": _csrf(app_client),
                "partner_name": "Renamed Partner",
                "membership_no": existing.membership_no,
                "is_signing": "on",
                "active": "on",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303, response.text[:300]
        db.expire_all()
        assert db.get(Partner, existing.partner_id).partner_name == "Renamed Partner"

    def test_retiring_a_partner_keeps_the_row(self, db: Session) -> None:
        """§18.6 — a report already signed must still name a findable partner,
        so leaving the firm is a flag, never a delete."""
        existing = db.scalar(select(Partner))
        assert existing is not None
        update_partner(db, existing.partner_id, {"active": False})
        db.expire_all()
        still_there = db.get(Partner, existing.partner_id)
        assert still_there is not None
        assert still_there.active is False

    def test_a_retired_partner_cannot_be_chosen_to_sign(self, db: Session) -> None:
        existing = db.scalar(select(Partner))
        assert existing is not None
        assert existing in signing_partners(db, existing.firm_id)
        update_partner(db, existing.partner_id, {"active": False})
        assert existing not in signing_partners(db, existing.firm_id)

    def test_a_membership_number_cannot_be_moved_to_another_partner(self, db: Session) -> None:
        first = db.scalar(select(Partner))
        assert first is not None
        second = add_partner(
            db, firm_id=first.firm_id, partner_name="Second", membership_no="999888"
        )
        with pytest.raises(ProfileError, match="belongs to another"):
            update_partner(db, second.partner_id, {"membership_no": first.membership_no})

    def test_an_unknown_field_is_refused(self, db: Session) -> None:
        existing = db.scalar(select(Partner))
        assert existing is not None
        with pytest.raises(ProfileError, match="Not editable"):
            update_partner(db, existing.partner_id, {"firm_id": 99})

    def test_the_change_is_logged(self, db: Session) -> None:
        from app.models.issuance import AuditLog

        existing = db.scalar(select(Partner))
        assert existing is not None
        before = len(db.scalars(select(AuditLog)).all())
        update_partner(db, existing.partner_id, {"partner_name": "Logged Change"})
        assert len(db.scalars(select(AuditLog)).all()) > before
