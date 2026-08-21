"""Creating a client. Added 17 August 2026.

There was no way to do this: no `create_client` service and no route, so the
application could only work with whatever `scripts/seed.py` had inserted. The
partner reported it after trying to use the tool.

One long form, on the partner's instruction, which makes returning the user's
entries on a validation failure part of the feature rather than a nicety.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.masters import Client, ClientProfile, Director, Kmp
from tests.test_client_routes import _csrf


def _payload(csrf: str, **overrides: str) -> dict[str, object]:
    """The form body, as a dict whose repeated fields hold lists.

    NOT a list of 2-tuples. httpx does not form-encode a list passed as
    `data=`, so the body arrived empty, `request.form()` saw nothing, and the
    route reported "Missing CSRF token" — which read like a CSRF fault in the
    application and was entirely a fault in this test. Repeated field names go
    in as `{"director_name": [...]}`.
    """
    body: dict[str, object] = {
        "csrf_token": csrf,
        "firm_id": "1",
        "client_code": "XYZ001",
        "cin": "U12345MH2015PTC099999",
        "pan": "AAACX1234X",
        "date_of_incorp": "2015-06-01",
        "company_type": "pvt",
        "framework": "igaap",
        "company_name": "XYZ Manufacturing Private Limited",
        "registered_addr": "9 Industrial Estate, Pune 411001",
        # Two real directors and two blank spares, exactly as the form renders
        # them — the spares must not become records.
        "director_name": ["A. Sharma", "B. Rao", "", ""],
        "director_din": ["01234567", "07654321", "", ""],
        "director_designation": ["managing", "independent", "managing", "managing"],
        "director_appointment_date": ["2015-06-01", "2020-04-01", "", ""],
        "director_cessation_date": ["", "", "", ""],
        "kmp_name": ["C. Patel", "", ""],
        "kmp_role": ["cfo", "cfo", "cfo"],
        "kmp_appointment_date": ["2019-07-01", "", ""],
    }
    body.update(overrides)
    return body


def _post(app_client: TestClient, **overrides: str):
    """Post the form with a token read immediately beforehand.

    The CSRF cookie is reissued on every response, so a token captured once
    and reused across requests is already stale by the time it is submitted.
    """
    token = _csrf(app_client)
    return app_client.post(
        "/clients/new", data=_payload(token, **overrides), follow_redirects=False
    )


class TestCreateClient:
    def test_the_form_opens(self, app_client: TestClient) -> None:
        """`/clients/new` must be declared before `/clients/{client_id}`.

        FastAPI matches in declaration order, so the literal was swallowed by
        the parameterised route and returned 422 trying to read "new" as an id.
        """
        assert app_client.get("/clients/new").status_code == 200

    def test_it_creates_the_client_profile_and_officers(
        self, app_client: TestClient, db: Session
    ) -> None:
        response = _post(app_client)
        assert response.status_code == 303, response.text[:500]

        client = db.scalar(select(Client).where(Client.client_code == "XYZ001"))
        assert client is not None
        assert client.cin == "U12345MH2015PTC099999"

        profile = db.scalar(
            select(ClientProfile).where(ClientProfile.client_id == client.client_id)
        )
        assert profile is not None
        assert profile.is_current is True
        assert profile.company_name == "XYZ Manufacturing Private Limited"
        # §12 — "42,60,00,000" is stored as a number, never as the typed string.

        directors = db.scalars(select(Director).where(Director.client_id == client.client_id)).all()
        assert len(directors) == 2, "blank spare rows became records"
        kmps = db.scalars(select(Kmp).where(Kmp.client_id == client.client_id)).all()
        assert len(kmps) == 1

    def test_a_duplicate_client_code_is_refused_with_a_sentence(self, db: Session) -> None:
        """§8.10 — a message, not an IntegrityError.

        Asserted against the service rather than the route: both keys are
        unique in the schema, and the point is that the user is told which one
        collided instead of seeing a database error.
        """
        from app.services.client import ProfileError, create_client

        with pytest.raises(ProfileError, match="already in use"):
            create_client(
                db,
                firm_id=1,
                client_code="ABC001",
                cin="U99999MH2020PTC000001",
                profile={"company_name": "Duplicate Code Ltd"},
            )

    def test_a_duplicate_cin_is_refused_too(self, db: Session) -> None:
        from app.services.client import ProfileError, create_client

        existing = db.scalar(select(Client).where(Client.client_code == "ABC001"))
        assert existing is not None
        with pytest.raises(ProfileError, match="already belongs"):
            create_client(
                db,
                firm_id=1,
                client_code="NEW001",
                cin=existing.cin,
                profile={"company_name": "Duplicate CIN Ltd"},
            )

    def test_a_refused_form_returns_what_was_typed(self, app_client: TestClient) -> None:
        """A rejected form must not make the user retype everything.

        The case that used to prove this was an unparseable amount. There are
        no amounts on the form since decision 62, so a missing company name
        stands in — the property is the same one: the response carries back
        what was entered.
        """
        response = _post(app_client, company_name="")
        assert response.status_code == 400
        # What was typed comes back, so nothing has to be entered twice.
        assert "XYZ001" in response.text

    def test_nothing_is_left_behind_when_it_fails(
        self, app_client: TestClient, db: Session
    ) -> None:
        """A client with no profile is unusable, so the whole thing rolls back."""
        before = len(db.scalars(select(Client)).all())
        _post(app_client, company_name="")
        db.expire_all()
        assert len(db.scalars(select(Client)).all()) == before

    def test_the_register_links_to_the_form(self, app_client: TestClient) -> None:
        assert "/clients/new" in app_client.get("/clients").text


class TestTheFormAsksForNothingThatDoesNotExist:
    """A leftover input is invisible to every other test.

    GSTIN survived decision 62 as a label and a text box on this form after the
    column was dropped: nothing read it, nothing saved it, and 786 tests passed
    while it sat there asking staff for a number the tool would discard. It was
    found by reading the page out of the packaged build, which is the one place
    a form field cannot hide.
    """

    def test_every_input_maps_to_something_real(self) -> None:
        import re
        from pathlib import Path

        import sqlalchemy as sa

        from app.models.masters import Client, ClientProfile, Director, Kmp

        columns = set()
        for model in (Client, ClientProfile, Director, Kmp):
            columns |= {c.name for c in sa.inspect(model).columns}

        # Controls that belong to the form itself rather than to a column.
        machinery = {"csrf_token", "auditcraft_csrf", "firm_id", "company_type", "framework"}
        # The repeating officer rows are posted with a prefix.
        prefixes = ("director_", "kmp_")

        page = Path("app/templates/client_new.html").read_text(encoding="utf-8")
        names = set(re.findall(r'name="([a-z_]+)"', page))
        names |= set(re.findall(r"\('([a-z_]+)',", page))

        unknown = sorted(
            name
            for name in names
            if name not in columns and name not in machinery and not name.startswith(prefixes)
        )
        assert unknown == [], f"the form asks for fields that do not exist: {unknown}"
