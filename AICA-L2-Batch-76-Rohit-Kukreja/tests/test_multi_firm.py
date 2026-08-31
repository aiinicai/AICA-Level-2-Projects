"""Several CA firms in one installation. Decision 20, 17 August 2026.

The partner chose this knowing what it means with no login: **anyone who opens
the application can see every firm's clients.** The active firm is a working
filter, not access control, and these tests assert that distinction rather than
pretending otherwise — see `test_switching_is_not_access_control`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.masters import Client, Firm
from app.services.client import (
    ACTIVE_FIRM_COOKIE,
    ProfileError,
    active_firm,
    all_firms,
    create_client,
    create_firm,
)
from app.services.register import dashboard_tiles, search_clients
from tests.test_client_routes import _csrf


@pytest.fixture
def second_firm(db: Session) -> Firm:
    firm = create_firm(db, firm_name="Second & Co", frn="123456W", address="Delhi")
    create_client(
        db,
        firm_id=firm.firm_id,
        client_code="SEC001",
        cin="U55555DL2018PTC012345",
        profile={"company_name": "Second Firm Client Private Limited"},
    )
    db.flush()
    return firm


class TestCreateFirm:
    def test_a_firm_is_added(self, db: Session) -> None:
        before = len(all_firms(db))
        create_firm(db, firm_name="New & Co", frn="654321N")
        assert len(all_firms(db)) == before + 1

    def test_a_duplicate_frn_is_refused(self, db: Session) -> None:
        existing = db.scalar(select(Firm))
        assert existing is not None
        with pytest.raises(ProfileError, match="already recorded"):
            create_firm(db, firm_name="Impostor", frn=existing.frn)

    def test_an_invalid_frn_is_refused(self, db: Session) -> None:
        from app.core.validators import ValidationError

        with pytest.raises(ValidationError):
            create_firm(db, firm_name="Bad FRN & Co", frn="nonsense")

    def test_a_firm_needs_a_name(self, db: Session) -> None:
        with pytest.raises(ProfileError, match="name is required"):
            create_firm(db, firm_name="  ", frn="999999N")


class TestScoping:
    def test_the_client_register_shows_only_the_active_firm(
        self, db: Session, second_firm: Firm
    ) -> None:
        first = db.scalar(select(Firm).order_by(Firm.firm_id))
        assert first is not None

        everything = search_clients(db).total
        assert search_clients(db, firm_id=first.firm_id).total < everything
        assert search_clients(db, firm_id=second_firm.firm_id).total == 1

    def test_the_dashboard_counts_only_the_active_firm(
        self, db: Session, second_firm: Firm
    ) -> None:
        assert dashboard_tiles(db, firm_id=second_firm.firm_id).total_clients == 1
        assert dashboard_tiles(db).total_clients > 1

    def test_an_unknown_firm_id_falls_back_rather_than_emptying_every_screen(
        self, db: Session
    ) -> None:
        """A stale cookie pointing at a firm that no longer exists must not
        leave the user staring at an empty register with no explanation."""
        assert active_firm(db, "99999") is not None
        assert active_firm(db, "not-a-number") is not None
        assert active_firm(db, None) is not None


class TestOverHttp:
    def test_the_picker_appears_once_there_is_more_than_one_firm(
        self, app_client: TestClient, db: Session, second_firm: Firm
    ) -> None:
        db.commit()
        body = app_client.get("/clients").text
        assert 'action="/admin/firms/switch"' in body
        assert "Second &amp; Co" in body or "Second & Co" in body

    def test_switching_changes_what_the_register_lists(
        self, app_client: TestClient, db: Session, second_firm: Firm
    ) -> None:
        db.commit()
        response = app_client.post(
            "/admin/firms/switch",
            data={"csrf_token": _csrf(app_client), "firm_id": str(second_firm.firm_id)},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.cookies.get(ACTIVE_FIRM_COOKIE) == str(second_firm.firm_id)

        listed = app_client.get("/clients").text
        assert "Second Firm Client Private Limited" in listed
        assert "ABC Private Limited" not in listed

    def test_switching_is_not_access_control(
        self, app_client: TestClient, db: Session, second_firm: Firm
    ) -> None:
        """Recorded deliberately. There is no login, so a client belonging to
        another firm is still reachable by its own URL. If this ever needs to
        be false, the single-user decision has to be revisited first."""
        db.commit()
        other = db.scalar(select(Client).where(Client.client_code == "SEC001"))
        assert other is not None

        app_client.post(
            "/admin/firms/switch",
            data={"csrf_token": _csrf(app_client), "firm_id": "1"},
            follow_redirects=False,
        )
        assert app_client.get(f"/clients/{other.client_id}").status_code == 200

    def test_the_firm_page_offers_a_way_to_add_one(self, app_client: TestClient) -> None:
        body = app_client.get("/admin/firm").text
        assert 'action="/admin/firms"' in body
        assert "no login" in body, "the confidentiality consequence must be on the page"
