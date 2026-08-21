"""Items 5, 6 and 10 of the firm's team's fifth round. Decisions 74 and 75.

Item 5 was a genuine gap: directors and KMP were written once by the new-client
form and no route touched them again, so a resignation during the year could
not be recorded anywhere.

Items 6 and 10 were not. The applicability screen existed and was linked; the
statutory auditors' term field existed and rendered. Both were on a Board's
Report tab 21,283 pixels tall carrying 312 fields under 41 headings, with no
index. "I cannot find it" and "it is not there" are the same report from the
far side of a page nobody can traverse.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet
from app.models.enums import Designation, KmpRole
from app.models.masters import Client, Director, Kmp
from app.services.client import (
    ProfileError,
    add_director,
    add_kmp,
    directors_during_fy,
    directors_in_office,
    end_director,
    end_kmp,
)
from app.services.progress import page_index
from tests.test_client_routes import _sign_in


def _client(db: Session) -> Client:
    client = db.scalar(select(Client))
    assert client is not None
    return client


class TestTheRegisterCanBeMaintained:
    """Item 5."""

    def test_a_director_can_be_appointed_after_the_client_exists(self, db: Session) -> None:
        client = _client(db)
        director = add_director(
            db,
            client.client_id,
            name="Meera Iyer",
            din="09876543",
            designation=Designation.MANAGING,
            appointment_date=date(2025, 7, 15),
        )
        db.flush()
        assert director.is_active
        assert director in directors_in_office(db, client.client_id, date(2025, 8, 1))

    def test_a_resignation_can_be_recorded(self, db: Session) -> None:
        client = _client(db)
        director = add_director(
            db,
            client.client_id,
            name="Ravi Menon",
            din="09876544",
            designation=Designation.NON_EXECUTIVE,
            appointment_date=date(2025, 4, 1),
        )
        db.flush()
        end_director(db, client.client_id, director.director_id, cessation_date=date(2025, 11, 30))
        db.flush()

        assert director.cessation_date == date(2025, 11, 30)
        assert not director.is_active
        assert director not in directors_in_office(db, client.client_id, date(2026, 1, 1))

    def test_the_row_is_dated_and_never_deleted(self, db: Session) -> None:
        """Last year's signed report names the people who held office then, and
        has to go on naming them. A cessation dates the row; it does not remove
        it."""
        client = _client(db)
        director = add_director(
            db,
            client.client_id,
            name="Left Midyear",
            din="09876545",
            designation=Designation.EXECUTIVE,
            appointment_date=date(2025, 5, 1),
        )
        db.flush()
        end_director(db, client.client_id, director.director_id, cessation_date=date(2025, 9, 30))
        db.flush()

        assert db.get(Director, director.director_id) is not None
        during = directors_during_fy(db, client.client_id, date(2025, 4, 1), date(2026, 3, 31))
        assert director in during, "the disclosure would lose someone who served part of the year"

    def test_a_cessation_before_the_appointment_is_refused(self, db: Session) -> None:
        client = _client(db)
        director = add_director(
            db,
            client.client_id,
            name="Impossible",
            din="09876546",
            designation=Designation.EXECUTIVE,
            appointment_date=date(2025, 7, 15),
        )
        db.flush()
        with pytest.raises(ProfileError, match="before being appointed"):
            end_director(
                db, client.client_id, director.director_id, cessation_date=date(2024, 1, 1)
            )

    def test_leaving_twice_is_refused(self, db: Session) -> None:
        client = _client(db)
        director = add_director(
            db,
            client.client_id,
            name="Gone Already",
            din="09876547",
            designation=Designation.EXECUTIVE,
            appointment_date=date(2025, 4, 1),
        )
        db.flush()
        end_director(db, client.client_id, director.director_id, cessation_date=date(2025, 6, 1))
        db.flush()
        with pytest.raises(ProfileError, match="already left"):
            end_director(
                db, client.client_id, director.director_id, cessation_date=date(2025, 9, 1)
            )

    @pytest.mark.parametrize("din", ["1234567", "123456789", "abcdefgh", ""])
    def test_a_din_is_eight_digits(self, db: Session, din: str) -> None:
        with pytest.raises(ProfileError):
            add_director(
                db,
                _client(db).client_id,
                name="Bad DIN",
                din=din,
                designation=Designation.EXECUTIVE,
                appointment_date=date(2025, 4, 1),
            )

    def test_the_same_din_cannot_sit_twice(self, db: Session) -> None:
        """One person, one live row. Two would put the name in the Board's
        Report twice and in the changes table twice."""
        client = _client(db)
        add_director(
            db,
            client.client_id,
            name="Original",
            din="09876548",
            designation=Designation.EXECUTIVE,
            appointment_date=date(2025, 4, 1),
        )
        db.flush()
        with pytest.raises(ProfileError, match="already on the register"):
            add_director(
                db,
                client.client_id,
                name="Duplicate",
                din="09876548",
                designation=Designation.EXECUTIVE,
                appointment_date=date(2025, 6, 1),
            )

    def test_a_din_may_return_after_leaving(self, db: Session) -> None:
        """A director who resigns and is reappointed is two spells, both real."""
        client = _client(db)
        first = add_director(
            db,
            client.client_id,
            name="Back Again",
            din="09876549",
            designation=Designation.EXECUTIVE,
            appointment_date=date(2024, 4, 1),
        )
        db.flush()
        end_director(db, client.client_id, first.director_id, cessation_date=date(2024, 9, 30))
        db.flush()
        second = add_director(
            db,
            client.client_id,
            name="Back Again",
            din="09876549",
            designation=Designation.EXECUTIVE,
            appointment_date=date(2025, 4, 1),
        )
        db.flush()
        assert second.director_id != first.director_id

    def test_kmp_can_be_appointed_and_ended(self, db: Session) -> None:
        client = _client(db)
        kmp = add_kmp(
            db,
            client.client_id,
            name="S Rao",
            role=next(iter(KmpRole)),
            appointment_date=date(2025, 4, 1),
        )
        db.flush()
        end_kmp(db, client.client_id, kmp.kmp_id, cessation_date=date(2026, 1, 31))
        db.flush()
        assert db.get(Kmp, kmp.kmp_id) is not None
        assert kmp.cessation_date == date(2026, 1, 31)

    def test_another_clients_director_cannot_be_touched(self, db: Session) -> None:
        """The route takes a client id and a director id; they have to agree."""
        client = _client(db)
        director = add_director(
            db,
            client.client_id,
            name="Not Yours",
            din="09876550",
            designation=Designation.EXECUTIVE,
            appointment_date=date(2025, 4, 1),
        )
        db.flush()
        with pytest.raises(ProfileError, match="not on this client"):
            end_director(
                db, client.client_id + 999, director.director_id, cessation_date=date(2025, 9, 1)
            )


class TestTheRegisterIsReachableFromTheScreen:
    """Item 5, through the routes. The service could always have done this; the
    point of the observation was that nothing on any page called it."""

    def test_the_directors_tab_offers_an_appointment_form(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        client_id = 1
        body = app_client.get(f"/clients/{client_id}?tab=directors").text
        assert f'action="/clients/{client_id}/directors"' in body
        assert "Appoint a director" in body

    def test_appointing_through_the_route_works(self, app_client: TestClient) -> None:
        csrf = _sign_in(app_client)
        response = app_client.post(
            "/clients/1/directors",
            data={
                "csrf_token": csrf,
                "name": "Route Tested",
                "din": "09871234",
                "designation": Designation.EXECUTIVE.value,
                "appointment_date": "2025-07-15",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

    def test_a_bad_date_comes_back_as_a_message(self, app_client: TestClient) -> None:
        """Not a 422 blob, and not a 500 (§8.10)."""
        csrf = _sign_in(app_client)
        response = app_client.post(
            "/clients/1/directors",
            data={
                "csrf_token": csrf,
                "name": "No Date",
                "din": "09871235",
                "designation": Designation.EXECUTIVE.value,
                "appointment_date": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Appointment date is required" in response.text

    def test_every_csrf_field_on_the_client_screen_is_filled(self) -> None:
        """A hidden field bound to a variable the context does not carry renders
        empty, and the form 422s on submit with nothing on screen to explain it.

        Four such fields shipped in one change. This template's convention is
        the cookie expression; the workspace's is `csrf`, and copying markup
        between them is exactly how it happened.
        """
        import re
        from pathlib import Path

        page = (Path("app") / "templates" / "client_detail.html").read_text(encoding="utf-8")
        offenders = [
            match.group(0)[:80]
            for match in re.finditer(r'name="csrf_token"\s+value="\{\{([^}]+)\}\}"', page)
            if "request.cookies" not in match.group(1)
        ]
        assert offenders == [], f"csrf fields bound to something else: {offenders}"


class TestTheLongPageIsNavigable:
    """Items 6 and 10. Decision 75.

    `page_index` is a pure function of the states the page is rendering and the
    clause set, so it is tested as one. Driving it through the database instead
    would test the fixture's seeding: the fixture repository has ten fields and
    a Board's Report you can read in a single screen, which is exactly the
    condition under which this defect is invisible.
    """

    @staticmethod
    def _state(key: str, clause_id: str, *, mandatory: bool = True, value: object = None):
        from app.clauses.model import CarryForward
        from app.services.engagement import FieldState

        return FieldState(
            key=key,
            label=key,
            datatype="text",
            clause_id=clause_id,
            clause_ref="",
            options=(),
            mandatory=mandatory,
            carry_forward=CarryForward.NEVER,
            value=value,
            reviewed=True,
            source=None,
            wp_reference="",
        )

    def test_one_entry_per_clause_in_page_order(self, production_clause_set: ClauseSet) -> None:
        states = [
            self._state("a.one", "bdr.opening"),
            self._state("a.two", "bdr.opening"),
            self._state("b.one", "bdr.statutory.auditors"),
        ]
        index = page_index(states, production_clause_set)
        assert [e.clause_id for e in index] == ["bdr.opening", "bdr.statutory.auditors"]
        assert [e.anchor for e in index] == ["field-a.one", "field-b.one"]

    def test_the_title_comes_from_the_clause(self, production_clause_set: ClauseSet) -> None:
        """The field the team reported as absent. It was 2,357 pixels down."""
        index = page_index(
            [self._state("bdr.statutory.auditors", "bdr.statutory.auditors")],
            production_clause_set,
        )
        assert index[0].title == "Statutory Auditors"
        assert index[0].anchor == "field-bdr.statutory.auditors"

    def test_a_clause_is_marked_when_any_of_its_fields_is_unanswered(
        self, production_clause_set: ClauseSet
    ) -> None:
        """The mark is on the CLAUSE, so an unanswered second field still shows
        on an entry whose first field is filled in."""
        states = [
            self._state("a.one", "bdr.opening", value="answered"),
            self._state("a.two", "bdr.opening", value=None),
        ]
        assert page_index(states, production_clause_set)[0].outstanding

    def test_an_optional_blank_field_is_not_outstanding(
        self, production_clause_set: ClauseSet
    ) -> None:
        states = [self._state("a.one", "bdr.opening", mandatory=False, value=None)]
        assert not page_index(states, production_clause_set)[0].outstanding

    def test_an_unknown_clause_still_gets_a_line(self, production_clause_set: ClauseSet) -> None:
        """A missing title is not a reason to drop the entry: the field is on
        the page either way, and an index that silently omits things is the
        defect this fixes."""
        index = page_index([self._state("x.one", "no.such.clause")], production_clause_set)
        assert index[0].title == "no.such.clause"

    def test_the_statutory_auditors_field_is_on_the_boards_report(
        self, production_clause_set: ClauseSet
    ) -> None:
        """The claim underneath item 10: the field exists, and it is asked."""
        clause = production_clause_set.get("bdr.statutory.auditors")
        assert clause is not None
        assert clause.document == "directors_report"
        assert clause.input is not None and clause.input.mandatory

    def test_the_workspace_still_renders(self, app_client: TestClient) -> None:
        """The fixture repository is too short to show an index -- the block is
        suppressed under five sections -- but the page must still render."""
        _sign_in(app_client)
        assert app_client.get("/engagements/1?document=auditors_report").status_code == 200

    def test_the_template_and_the_dataclass_agree_on_names(self) -> None:
        """The index block reads `entry.title`, `entry.anchor` and
        `entry.outstanding`. Jinja resolves a name it does not have to the
        undefined value and renders nothing rather than failing, so a rename on
        the Python side would empty the index in silence.

        This is the same failure as the four CSRF fields bound to a variable
        the context did not carry: a template referring to something that is
        not there looks exactly like a template with nothing to show.
        """
        import re
        from dataclasses import fields
        from pathlib import Path

        from app.services.progress import IndexEntry

        page = (Path("app") / "templates" / "workspace.html").read_text(encoding="utf-8")
        block = re.search(r'<details class="page-index".*?</details>', page, re.S)
        assert block is not None, "the page index block is gone"

        declared = {f.name for f in fields(IndexEntry)}
        used = set(re.findall(r"entry\.(\w+)", block.group(0)))
        assert used, "the index block reads no attributes at all"
        assert (
            used <= declared
        ), f"the template reads {sorted(used - declared)}, which IndexEntry has not"


class TestTheUndeclaredFlagsAreNamed:
    """Item 6. CARO, IFC, CSR, internal audit and secretarial audit are
    DECLARED: the engine does not infer them, and until one is stated every
    clause hanging off it is silently absent from the document.

    The screen that answers them was linked, as "Applicability" -- which is not
    what someone hunting for "where do I say CSR applies?" is reading for.
    """

    def test_the_three_the_team_could_not_find_are_declared_flags(self) -> None:
        from app.core.applicability import DECLARED_FLAGS

        assert {"csr", "internal_audit", "ifc"} <= DECLARED_FLAGS

    def test_an_unanswered_declared_flag_reports_itself_as_awaiting(self, db: Session) -> None:
        from app.config import get_settings
        from app.models.engagement import Engagement
        from app.models.masters import ClientProfile
        from app.services.applicability import flag_views

        engagement = db.scalar(select(Engagement))
        assert engagement is not None
        profile = db.get(ClientProfile, engagement.profile_id)
        assert profile is not None

        # The fixture answers some of them, so clear the stored overrides
        # first: the claim under test is that an UNANSWERED declared flag
        # reports itself, not that this particular fixture leaves them unset.
        from app.services.applicability import OVERRIDE_COLUMNS

        for column in OVERRIDE_COLUMNS.values():
            if hasattr(profile, column):
                setattr(profile, column, False)
        db.flush()

        views = flag_views(
            profile,
            engagement.fy_end,
            get_settings().content_path / "applicability_rules.yaml",
        )
        awaiting = {v.name for v in views if v.is_declared and v.awaiting_answer}
        assert {"csr", "internal_audit", "ifc"} <= awaiting

        # And an answered one drops off, or the prompt would never go away.
        answered = {v.name for v in views if v.is_declared and not v.awaiting_answer}
        assert not (answered & awaiting)

    def test_the_workspace_offers_the_screen_that_answers_them(
        self, app_client: TestClient
    ) -> None:
        _sign_in(app_client)
        body = app_client.get("/engagements/1").text
        assert "/engagements/1/applicability" in body
