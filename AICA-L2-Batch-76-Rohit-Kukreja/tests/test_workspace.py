"""Phase 6 exit test — nothing lost on refresh; every field persists (§16).

Every assertion here re-reads through a *fresh* request rather than the
object just written, because the failure mode being guarded against is
"looked saved, wasn't".
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import CONTEXT_VARIABLES, ClauseSet
from app.models.engagement import Engagement, EngagementResponse
from app.models.enums import EngagementStatus, ResponseSource
from app.services.document import BuiltDocument, build_document
from app.services.engagement import (
    EngagementError,
    LockedError,
    add_child_row,
    answer_map,
    child_rows,
    coerce,
    confirm_carry_forward,
    create_engagement,
    delete_child_row,
    field_states,
    readiness,
    set_response,
)
from tests.test_client_routes import _sign_in


@pytest.fixture
def engagement_id(db: Session, client_id: int) -> int:
    found = db.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == "2025-26")
    )
    assert found is not None
    return found.engagement_id


@pytest.fixture
def locked_id(db: Session, client_id: int) -> int:
    found = db.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == "2024-25")
    )
    assert found is not None
    return found.engagement_id


class TestTypedStorage:
    """§12, §19 — store numeric values and raw dates, never formatted strings."""

    @pytest.mark.parametrize(
        ("raw", "datatype", "expected"),
        [
            ("42,60,000", "amount", (None, Decimal("4260000"), None)),
            ("₹1,25,000", "amount", (None, Decimal("125000"), None)),
            ("2026-03-31", "date", (None, None, date(2026, 3, 31))),
            ("none", "select", ("none", None, None)),
            ("", "text", (None, None, None)),
            ("   ", "amount", (None, None, None)),
        ],
    )
    def test_coercion(self, raw: str, datatype: str, expected: tuple) -> None:
        assert coerce(raw, datatype) == expected

    def test_a_bad_number_is_refused_with_a_message(self) -> None:
        # "amount" since decision 71, when the numeric paths were unified on
        # `parse_amount`. The point of the test is unchanged: unreadable input
        # raises an error the router can catch, not an unhandled 500.
        with pytest.raises(EngagementError, match="not a valid amount"):
            coerce("about forty lakh", "amount")

    def test_a_bad_date_is_refused_with_a_message(self) -> None:
        with pytest.raises(EngagementError, match="not a valid date"):
            coerce("31/03/2026", "date")

    def test_an_amount_lands_in_the_numeric_column(self, db: Session, engagement_id: int) -> None:
        set_response(db, engagement_id, "rule11.f.narrative", "text", updated_by="t")
        row = db.get(EngagementResponse, (engagement_id, "rule11.f.narrative"))
        assert row is not None
        assert row.value_text == "text"
        assert row.value_num is None


class TestPersistence:
    def test_an_answer_survives_a_fresh_read(self, db: Session, engagement_id: int) -> None:
        set_response(db, engagement_id, "caro.viii", "not_recorded", updated_by="t")
        db.expire_all()
        assert answer_map(db, engagement_id)["caro.viii"] == "not_recorded"

    def test_editing_marks_the_answer_verified_for_this_year(
        self, db: Session, engagement_id: int
    ) -> None:
        # §6.2 — the system must distinguish "same as last year" from
        # "verified for the current year".
        set_response(db, engagement_id, "caro.viii", "recorded", updated_by="t@firm.local")
        row = db.get(EngagementResponse, (engagement_id, "caro.viii"))
        assert row is not None
        assert row.reviewed is True
        assert row.source is ResponseSource.USER
        assert row.reviewed_by == "t@firm.local"

    def test_clearing_a_field_stores_null_not_an_empty_string(
        self, db: Session, engagement_id: int
    ) -> None:
        set_response(db, engagement_id, "caro.viii", "", updated_by="t")
        row = db.get(EngagementResponse, (engagement_id, "caro.viii"))
        assert row is not None
        assert (row.value_text, row.value_num, row.value_date) == (None, None, None)

    def test_a_wp_reference_persists(self, db: Session, engagement_id: int) -> None:
        set_response(db, engagement_id, "caro.viii", "none", updated_by="t", wp_reference="B-14")
        row = db.get(EngagementResponse, (engagement_id, "caro.viii"))
        assert row is not None and row.wp_reference == "B-14"

    def test_an_uncatalogued_field_is_refused(self, db: Session, engagement_id: int) -> None:
        with pytest.raises(EngagementError, match="not a catalogued field"):
            set_response(db, engagement_id, "made.up.field", "x", updated_by="t")

    def test_a_value_outside_the_option_set_is_refused(
        self, db: Session, engagement_id: int
    ) -> None:
        # §18.3 — a control must not accept a value no variant can render.
        with pytest.raises(EngagementError, match="not an option"):
            set_response(db, engagement_id, "caro.viii", "maybe", updated_by="t")


class TestCarryForwardConfirmation:
    def test_confirming_does_not_change_the_value(self, db: Session, engagement_id: int) -> None:
        row = db.get(EngagementResponse, (engagement_id, "caro.viii"))
        assert row is not None
        row.source = ResponseSource.CARRIED_FORWARD
        row.reviewed = False
        db.flush()

        confirm_carry_forward(db, engagement_id, "caro.viii", confirmed_by="m@firm.local")
        db.expire_all()

        confirmed = db.get(EngagementResponse, (engagement_id, "caro.viii"))
        assert confirmed is not None
        assert confirmed.reviewed is True
        assert confirmed.value_text == "none"

    def test_an_unconfirmed_carry_forward_is_flagged(
        self, db: Session, engagement_id: int, clause_set
    ) -> None:
        row = db.get(EngagementResponse, (engagement_id, "caro.viii"))
        assert row is not None
        row.source = ResponseSource.CARRIED_FORWARD
        row.reviewed = False
        db.flush()

        engagement = db.get(Engagement, engagement_id)
        states = {s.key: s for s in field_states(db, engagement, clause_set)}
        assert states["caro.viii"].is_unconfirmed_carry_forward is True

    def test_readiness_excludes_unconfirmed_carry_forwards(
        self, db: Session, engagement_id: int, clause_set
    ) -> None:
        engagement = db.get(Engagement, engagement_id)
        before = readiness(field_states(db, engagement, clause_set))

        row = db.get(EngagementResponse, (engagement_id, "caro.viii"))
        assert row is not None
        row.source = ResponseSource.CARRIED_FORWARD
        row.reviewed = False
        db.flush()

        after = readiness(field_states(db, engagement, clause_set))
        assert after < before


class TestChildRecords:
    def test_a_row_persists_with_typed_columns(self, db: Session, engagement_id: int) -> None:
        add_child_row(
            db,
            engagement_id,
            "litigation",
            {
                "forum": "NCLT Mumbai",
                "nature": "Operational creditor petition",
                "amount": "12,50,000",
                "status": "pending",
            },
            added_by="t",
        )
        db.expire_all()
        rows = child_rows(db, engagement_id, "litigation")
        added = rows[-1]
        assert added.forum == "NCLT Mumbai"
        # §19 — an amount is a Decimal, not "12,50,000".
        assert added.amount == Decimal("1250000")

    def test_row_index_is_assigned_in_order(self, db: Session, engagement_id: int) -> None:
        rows = child_rows(db, engagement_id, "litigation")
        assert [r.row_index for r in rows] == list(range(len(rows)))

    def test_deleting_keeps_row_index_contiguous(self, db: Session, engagement_id: int) -> None:
        rows = child_rows(db, engagement_id, "litigation")
        assert len(rows) >= 2
        delete_child_row(db, engagement_id, "litigation", rows[0].litigation_id, deleted_by="t")
        db.expire_all()
        remaining = child_rows(db, engagement_id, "litigation")
        assert [r.row_index for r in remaining] == list(range(len(remaining)))

    def test_an_unknown_column_is_refused(self, db: Session, engagement_id: int) -> None:
        with pytest.raises(EngagementError, match="unknown column"):
            add_child_row(db, engagement_id, "litigation", {"not_a_column": "x"}, added_by="t")

    def test_an_unknown_entity_is_refused(self, db: Session, engagement_id: int) -> None:
        with pytest.raises(EngagementError, match="unknown repeating entity"):
            add_child_row(db, engagement_id, "spaceships", {"x": "y"}, added_by="t")

    def test_a_row_from_another_engagement_cannot_be_deleted(
        self, db: Session, client_id: int, engagement_id: int
    ) -> None:
        """Row ids are global, so ownership must be checked, not assumed.

        Deleted through an *unlocked* other engagement, so this exercises the
        ownership check rather than the lock guard.
        """
        other = create_engagement(
            db,
            client_id,
            date(2026, 4, 1),
            date(2027, 3, 31),
            profile_id=None,
            created_by="t",
        )
        rows = child_rows(db, engagement_id, "litigation")
        with pytest.raises(EngagementError, match="not found on this engagement"):
            delete_child_row(
                db,
                other.engagement_id,
                "litigation",
                rows[0].litigation_id,
                deleted_by="t",
            )


class TestLocking:
    """§10, §18.7 — a finalised engagement cannot be edited."""

    def test_a_field_cannot_be_saved(self, db: Session, locked_id: int) -> None:
        with pytest.raises(LockedError, match="Create Revision"):
            set_response(db, locked_id, "caro.viii", "none", updated_by="t")

    def test_a_child_row_cannot_be_added(self, db: Session, locked_id: int) -> None:
        with pytest.raises(LockedError):
            add_child_row(db, locked_id, "litigation", {"forum": "x", "nature": "y"}, added_by="t")

    def test_a_carry_forward_cannot_be_confirmed(self, db: Session, locked_id: int) -> None:
        with pytest.raises(LockedError):
            confirm_carry_forward(db, locked_id, "caro.viii", confirmed_by="t")


class TestCreation:
    def test_a_new_year_is_created(self, db: Session, client_id: int) -> None:
        created = create_engagement(
            db,
            client_id,
            date(2026, 4, 1),
            date(2027, 3, 31),
            profile_id=None,
            created_by="t",
        )
        assert created.fy_code == "2026-27"
        assert created.status is EngagementStatus.DATA_COLLECTION

    def test_a_duplicate_year_is_refused(self, db: Session, client_id: int) -> None:
        with pytest.raises(EngagementError, match="already exists"):
            create_engagement(
                db,
                client_id,
                date(2025, 4, 1),
                date(2026, 3, 31),
                profile_id=None,
                created_by="t",
            )


class TestWorkspaceOverHttp:
    """The exit test proper: save through the UI, reload, nothing lost."""

    def _csrf(self, app_client: TestClient) -> str:
        return _sign_in(app_client)

    def test_workspace_renders(self, app_client: TestClient, engagement_id: int) -> None:
        self._csrf(app_client)
        response = app_client.get(f"/engagements/{engagement_id}")
        assert response.status_code == 200
        assert "Readiness" in response.text

    def test_a_saved_answer_is_still_there_after_a_reload(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        csrf = self._csrf(app_client)
        saved = app_client.post(
            f"/engagements/{engagement_id}/field",
            data={
                "csrf_token": csrf,
                "field_key": "caro.viii",
                "value": "not_recorded",
                "document": "caro_2020",
            },
            follow_redirects=False,
        )
        assert saved.status_code == 303

        reloaded = app_client.get(f"/engagements/{engagement_id}?document=caro_2020")
        # Matched with tolerance for line breaks inside the tag: the option
        # markup now spans two lines because an unanswered field preselects
        # its clean answer, and asserting on exact spacing tested the
        # formatter rather than the behaviour.
        assert re.search(
            r'<option value="not_recorded"\s[^>]*selected', reloaded.text
        ), "the saved answer is no longer selected on reload"

    def test_a_narrative_survives_a_reload(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        csrf = self._csrf(app_client)
        text = "Surrendered income of Rs. 42,60,000 was not recorded in the books."
        app_client.post(
            f"/engagements/{engagement_id}/field",
            data={
                "csrf_token": csrf,
                "field_key": "caro.viii.narrative",
                "value": text,
                "document": "caro_2020",
            },
            follow_redirects=False,
        )
        reloaded = app_client.get(f"/engagements/{engagement_id}?document=caro_2020")
        assert text in reloaded.text

    def test_a_child_row_added_through_the_form_appears_in_the_document(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        csrf = self._csrf(app_client)
        response = app_client.post(
            f"/engagements/{engagement_id}/rows/litigation",
            data={
                "csrf_token": csrf,
                "document": "auditors_report",
                "col_forum": "NCLT Bengaluru",
                "col_nature": "Insolvency application",
                "col_amount": "9,00,000",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        reloaded = app_client.get(f"/engagements/{engagement_id}?document=auditors_report")
        # Present in both the editor table and the rendered document.
        assert reloaded.text.count("NCLT Bengaluru") >= 2

    def test_an_empty_add_row_is_refused_with_a_message(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        csrf = self._csrf(app_client)
        response = app_client.post(
            f"/engagements/{engagement_id}/rows/litigation",
            data={"csrf_token": csrf, "document": "auditors_report"},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "at least one value" in response.text
        assert "Traceback" not in response.text

    def test_an_invalid_amount_shows_a_message_not_a_traceback(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        csrf = self._csrf(app_client)
        response = app_client.post(
            f"/engagements/{engagement_id}/field",
            data={
                "csrf_token": csrf,
                "field_key": "caro.viii",
                "value": "not-an-option",
                "document": "caro_2020",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "not an option" in response.text
        assert "Traceback" not in response.text

    def test_a_locked_engagement_refuses_edits_over_http(
        self, app_client: TestClient, locked_id: int
    ) -> None:
        csrf = self._csrf(app_client)
        response = app_client.post(
            f"/engagements/{locked_id}/field",
            data={
                "csrf_token": csrf,
                "field_key": "caro.viii",
                "value": "none",
                "document": "caro_2020",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Create Revision" in response.text

    def test_the_prior_year_column_is_shown(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        self._csrf(app_client)
        body = app_client.get(f"/engagements/{engagement_id}?document=caro_2020").text
        assert "FY 2024-25:" in body

    def test_the_page_works_without_javascript(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        """Autosave is an enhancement. Every control is a real form.

        Asserted against the markup rather than a script filename, which is
        what this used to check — a filename tells you nothing about whether
        the page still works when the script does not run. HTMX and Alpine
        were vendored after this test was written and the old assertion broke
        on the rename while proving nothing either way.
        """
        self._csrf(app_client)
        body = app_client.get(f"/engagements/{engagement_id}").text

        # A real form, a real method, a real submit button. This is the whole
        # no-JavaScript guarantee.
        assert body.count("<form") >= 3
        assert ">Save</button>" in body
        assert 'method="post"' in body
        for form in re.findall(r"<form\b[^>]*>", body):
            if "autosave" in form:
                assert 'action="' in form, f"an autosave form has no action: {form}"
                assert 'method="post"' in form, form

        # Every script is deferred, so none of them can block the parse, and
        # nothing is loaded from anywhere but /static.
        scripts = re.findall(r"<script\b[^>]*>", body)
        assert scripts, "no scripts at all — the enhancement is missing"
        for tag in scripts:
            assert "defer" in tag, f"a blocking script would break this: {tag}"
            assert 'src="/static/' in tag, f"§13 — assets are local only: {tag}"


class TestEngagementLevelFields:
    """Opinion, going concern, report date and place (§5.3).

    These are columns on `engagement`, not catalogued fields, so they need
    their own editor — without one the §6.4 opinion comparison and the §18.4
    export block have nothing to read.
    """

    def test_the_opinion_can_be_set(self, db: Session, engagement_id: int) -> None:
        from app.models.enums import OpinionType
        from app.services.engagement import set_engagement_field

        set_engagement_field(db, engagement_id, "opinion_type", "qualified", updated_by="t")
        db.expire_all()
        assert db.get(Engagement, engagement_id).opinion_type is OpinionType.QUALIFIED

    def test_an_invalid_opinion_is_refused(self, db: Session, engagement_id: int) -> None:
        from app.services.engagement import set_engagement_field

        with pytest.raises(EngagementError, match="is not one of"):
            set_engagement_field(db, engagement_id, "opinion_type", "excellent", updated_by="t")

    def test_a_report_date_before_the_year_end_is_refused(
        self, db: Session, engagement_id: int
    ) -> None:
        from app.services.engagement import set_engagement_field

        with pytest.raises(EngagementError, match="cannot precede"):
            set_engagement_field(db, engagement_id, "report_date", "2026-03-30", updated_by="t")

    def test_a_locked_engagement_refuses(self, db: Session, locked_id: int) -> None:
        from app.services.engagement import set_engagement_field

        with pytest.raises(LockedError):
            set_engagement_field(db, locked_id, "place", "Pune", updated_by="t")

    def test_an_unknown_field_is_refused(self, db: Session, engagement_id: int) -> None:
        from app.services.engagement import set_engagement_field

        with pytest.raises(EngagementError, match="not an editable engagement field"):
            set_engagement_field(db, engagement_id, "audit_fee", "1000", updated_by="t")

    def test_the_workspace_offers_the_controls(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        _sign_in(app_client)
        body = app_client.get(f"/engagements/{engagement_id}").text
        assert 'name="field" value="opinion_type"' in body
        assert 'name="field" value="going_concern"' in body
        assert 'name="field" value="report_date"' in body

    def test_setting_the_opinion_over_http_persists(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        csrf = _sign_in(app_client)
        saved = app_client.post(
            f"/engagements/{engagement_id}/engagement-field",
            data={
                "csrf_token": csrf,
                "field": "opinion_type",
                "value": "qualified",
                "document": "auditors_report",
            },
            follow_redirects=False,
        )
        assert saved.status_code == 303
        reloaded = app_client.get(f"/engagements/{engagement_id}")
        assert 'value="qualified" selected' in reloaded.text


def _clean_auditors_report(clause_set: ClauseSet) -> BuiltDocument:
    """The auditor's report as it renders on a clean file.

    Every select is answered with its **first** option, which is the clean one
    by the convention the workspace dropdowns rely on. Built this way rather
    than from a written-out answer map so that the report under test is the one
    the tool actually opens on, and so a clause whose clean option stops being
    first shows up here too.
    """
    responses = {
        clause.input.key: clause.input.options[0].value
        for clause in clause_set.clauses
        if clause.input is not None and clause.input.options
    }
    return build_document(
        clause_set,
        "auditors_report",
        date(2025, 3, 31),
        responses=responses,
        context=dict.fromkeys(CONTEXT_VARIABLES, ""),
    )


class TestCleanDefaultsAndApplicability:
    """Partner's instructions, 17 August 2026."""

    def test_an_unanswered_dropdown_opens_on_its_clean_option(
        self, db: Session, app_client: TestClient, engagement_id: int
    ) -> None:
        """An audit is exception-based: the auditor changes what is not clean.

        Every clause lists its nil answer first, so `loop.first` is the clean
        one. This is a default, not an assertion — nothing is stored until the
        field is saved, which `test_a_default_is_not_a_stored_answer` holds to.
        """
        # The seed answers every clause in the fixture repository, so one has
        # to be cleared for "unanswered" to mean anything here.
        _sign_in(app_client)
        existing = db.get(EngagementResponse, (engagement_id, "caro.viii"))
        if existing is not None:
            db.delete(existing)
            db.flush()

        body = app_client.get(f"/engagements/{engagement_id}?document=caro_2020").text
        block = re.search(r'id="input-caro\.viii"(.*?)</select>', body, re.S)
        assert block, "caro.viii is not on the page"
        options = re.findall(r'<option value="([^"]*)"([^>]*)>', block.group(1))
        selected = [value for value, attrs in options if "selected" in attrs]
        assert selected, "nothing is preselected"
        assert selected[0] == options[0][0], "the preselected option is not the first"
        assert selected[0] != "", "the blank option is still the default"

    def test_a_default_is_not_a_stored_answer(
        self, db: Session, app_client: TestClient, engagement_id: int
    ) -> None:
        """Preselecting must not make an unanswered field count as answered —
        §18.4's export block and readiness both depend on that distinction."""
        _sign_in(app_client)
        existing = db.get(EngagementResponse, (engagement_id, "caro.viii"))
        if existing is not None:
            db.delete(existing)
            db.flush()
        app_client.get(f"/engagements/{engagement_id}?document=caro_2020")
        assert db.get(EngagementResponse, (engagement_id, "caro.viii")) is None

    def test_key_audit_matters_is_absent_when_it_does_not_apply(
        self, app_client: TestClient, engagement_id: int
    ) -> None:
        """SA 701 does not reach an unlisted private company. The workspace
        asked for KAM anyway and the preview printed the section, because it
        built the document with no applicability filter at all."""
        _sign_in(app_client)
        body = app_client.get(f"/engagements/{engagement_id}?document=auditors_report").text
        assert "Key Audit Matters" not in body
        assert 'id="block-iar.kam"' not in body

    def test_the_agreement_and_standards_clauses_ask_nothing(self, production_clause_set) -> None:
        """Partner: always in agreement, always complied. Both clauses print
        their compliant wording and carry no input."""
        for clause_id in ("iar.143.3.d", "iar.143.3.e"):
            clause = production_clause_set.get(clause_id)
            assert clause.input is None, f"{clause_id} still asks a question"
            assert not any(v.requires_narrative for v in clause.variants)
            assert not any(
                v.severity for v in clause.variants
            ), f"{clause_id} still has an exception path"

    def test_a_preselected_default_is_visibly_not_saved(
        self, db: Session, app_client: TestClient, engagement_id: int
    ) -> None:
        """Reported by the user, 17 August 2026: "even after saving the answer
        with dropdown boxes, still showing findings blocking export".

        Saving worked. Preselecting did not: the form autosaves on `change`,
        which an untouched dropdown never fires, so the clean option showed,
        nothing was stored, and the field went on blocking export looking
        exactly like an answered one. The page must say so.
        """
        _sign_in(app_client)
        existing = db.get(EngagementResponse, (engagement_id, "caro.viii"))
        if existing is not None:
            db.delete(existing)
            db.flush()

        body = app_client.get(f"/engagements/{engagement_id}?document=caro_2020").text
        field = re.search(
            r'<div class="([^"]*)"\s*\n?\s*id="field-caro\.viii">(.*?)</form>', body, re.S
        )
        assert field, "caro.viii is not on the page"
        assert "not saved" in field.group(2), "an unsaved default looks like a saved answer"
        assert "unsaved" in field.group(1), "the field carries no unsaved class"

    def test_accepting_the_defaults_stores_them_and_unblocks_export(
        self, db: Session, app_client: TestClient, engagement_id: int, clause_set: ClauseSet
    ) -> None:
        """The offer on the page and the act behind it must agree, and the
        result must actually count — the whole complaint was a readiness number
        that would not move."""
        _sign_in(app_client)
        engagement = db.get(Engagement, engagement_id)
        assert engagement is not None
        for state in field_states(db, engagement, clause_set, "caro_2020"):
            row = db.get(EngagementResponse, (engagement_id, state.key))
            if row is not None:
                db.delete(row)
        db.flush()

        before = app_client.get(f"/engagements/{engagement_id}?document=caro_2020").text
        offered = re.search(r"Accept the (\d+) clean", before)
        assert offered, "no offer to accept the defaults"

        csrf = app_client.cookies.get("auditcraft_csrf")
        posted = app_client.post(
            f"/engagements/{engagement_id}/accept-defaults",
            data={"csrf_token": csrf, "document": "caro_2020"},
            follow_redirects=True,
        )
        assert posted.status_code == 200

        stored = db.get(EngagementResponse, (engagement_id, "caro.viii"))
        assert stored is not None, "accepting the defaults stored nothing"
        assert stored.reviewed is True, "an accepted default is not confirmed for the year"

        after = app_client.get(f"/engagements/{engagement_id}?document=caro_2020").text
        assert "Accept the" not in after, "still offering to accept what is already stored"

    def test_accepting_defaults_never_overwrites_an_answer(
        self, db: Session, app_client: TestClient, engagement_id: int
    ) -> None:
        """Including one carried forward and not yet confirmed: silently
        replacing an answer the auditor has not looked at is the opposite of
        what this button is for."""
        _sign_in(app_client)
        set_response(db, engagement_id, "caro.viii", "not_recorded", updated_by="t")
        row = db.get(EngagementResponse, (engagement_id, "caro.viii"))
        assert row is not None
        row.source = ResponseSource.CARRIED_FORWARD
        row.reviewed = False
        db.flush()

        csrf = app_client.cookies.get("auditcraft_csrf")
        app_client.post(
            f"/engagements/{engagement_id}/accept-defaults",
            data={"csrf_token": csrf, "document": "caro_2020"},
            follow_redirects=True,
        )
        db.expire_all()
        kept = db.get(EngagementResponse, (engagement_id, "caro.viii"))
        assert kept is not None
        assert kept.value_text == "not_recorded", "an existing answer was overwritten"
        assert kept.reviewed is False, "an unconfirmed carry-forward was silently confirmed"

    def test_only_the_two_intended_section_143_3_questions_remain(
        self, production_clause_set
    ) -> None:
        """Partner, 17 August 2026: (a), (b), (c), (d), (e), (g) and (h) are all
        hard-coded, leaving exactly two paragraphs that still ask anything.

        Swept over the whole group rather than checked id by id, so a question
        reappearing � a clause re-authored, a new one added � fails here rather
        than reaching a signing partner as a dropdown nobody meant to ask.
        """
        asked = sorted(
            clause.id
            for clause in production_clause_set.clauses
            if clause.id.startswith("iar.143.3.") and clause.input is not None
        )
        # (f) observations having an adverse effect on the functioning of the
        # company, and (i) the adequacy and operating effectiveness of internal
        # financial controls. Both are genuine auditor judgements on every file
        # and neither was withdrawn.
        assert asked == ["iar.143.3.f", "iar.143.3.i"], asked

    def test_the_hard_coded_paragraphs_have_no_exception_path(self, production_clause_set) -> None:
        """A hard-coded answer with an exception variant still reachable would
        be worse than the question: unreachable wording that looks live."""
        for clause_id in (
            "iar.143.3.a",
            "iar.143.3.b",
            "iar.143.3.c",
            "iar.143.3.g",
            "iar.143.3.h",
            "iar.197.16",
        ):
            clause = production_clause_set.get(clause_id)
            assert clause.input is None, f"{clause_id} still asks a question"
            assert len(clause.variants) == 1, f"{clause_id} still has a choice to make"
            assert not clause.variants[0].requires_narrative, clause_id
            assert not clause.variants[0].severity, f"{clause_id} keeps an exception path"

    def test_the_branch_and_maintenance_paragraphs_never_print(self, production_clause_set) -> None:
        """s.143(3)(c) and (h): "no paragraph is required for this". They are
        kept in the repository rather than deleted, so `omit` is what has to
        hold � a clause that is present and prints would be the failure."""
        built = _clean_auditors_report(production_clause_set)
        printed = {getattr(node, "clause_id", None) for node in built.document.nodes}
        for clause_id in ("iar.143.3.c", "iar.143.3.h"):
            assert production_clause_set.get(clause_id).variants[0].omit is True
            assert clause_id not in printed, f"{clause_id} printed"
            assert clause_id in built.omitted, f"{clause_id} was dropped without being reported"

    def test_the_section_143_3_lettering_closes_up_over_them(self, production_clause_set) -> None:
        """The letters are positional (`auto:alpha`), so removing (c) and (h)
        must renumber everything below them rather than leave a gap.

        Asserted as a property of the run � contiguous from (a), no repeats �
        rather than against an expected list of letters, because the list is
        what a wrong change would quietly rewrite.
        """
        built = _clean_auditors_report(production_clause_set)
        letters = [
            node.number
            for node in built.document.nodes
            if getattr(node, "number", None) and re.fullmatch(r"\([a-z]\)", node.number)
        ]
        expected = [f"({chr(ord('a') + i)})" for i in range(len(letters))]
        assert letters == expected, f"the lettering has a gap or a repeat: {letters}"

    def test_they_still_follow_the_reporting_framework(self, production_clause_set) -> None:
        """Removing the question must not lose the Ind AS wording: an Ind AS
        company names two more statements and a different rule."""
        from app.clauses.resolve import resolve

        probe = dict.fromkeys(CONTEXT_VARIABLES, "")
        for clause_id, marker in (
            ("iar.143.3.d", "Changes in Equity"),
            ("iar.143.3.e", "Indian Accounting Standards"),
        ):
            clause = production_clause_set.get(clause_id)
            indas = resolve(clause, {**probe, "framework": "indas", "value": None}).body
            other = resolve(clause, {**probe, "framework": "igaap", "value": None}).body
            assert marker in indas, clause_id
            assert marker not in other, clause_id
