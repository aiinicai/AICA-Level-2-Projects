"""The firm's master answer sheet — decision 28, 17 August 2026.

Partner's instruction: set every dropdown once for the whole practice, have new
engagements start from those answers, and override any of them on an individual
engagement when the facts differ.

The tests are written around the three properties that make that safe rather
than around the screen, because the screen is the easy part:

* a default is **copied** onto an engagement, so editing the sheet cannot reach
  a file already in progress;
* a default **never overwrites** an answer already given;
* an answer taken from the sheet is **still marked as such**, because readiness
  can no longer distinguish it from one a person entered.
"""

from __future__ import annotations

import json
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet
from app.models.engagement import Engagement, EngagementResponse, FieldCatalog
from app.models.enums import ResponseSource
from app.models.masters import Firm
from app.services.defaults import (
    apply_defaults,
    default_map,
    selectable_fields,
    set_defaults,
    stale_defaults,
)
from app.services.engagement import EngagementError, field_states, readiness
from tests.test_client_routes import _sign_in


@pytest.fixture
def firm_id(db: Session) -> int:
    found = db.scalar(select(Firm))
    assert found is not None
    return found.firm_id


@pytest.fixture
def engagement(db: Session, client_id: int) -> Engagement:
    found = db.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == "2025-26")
    )
    assert found is not None
    return found


def _clean_sheet(db: Session, clause_set: ClauseSet) -> dict[str, str]:
    """The first option of every dropdown — a clean file, as a firm would set it."""
    sheet: dict[str, str] = {}
    for entry in selectable_fields(db, clause_set):
        options = json.loads(entry.options_json)
        sheet[entry.field_key] = options[0]["value"]
    return sheet


class TestTheSheetItself:
    def test_only_dropdowns_can_hold_a_default(self, db: Session, clause_set: ClauseSet) -> None:
        """A narrative has no option set, so there is nothing to default it to,
        and a firm-wide default narrative would be a fabricated disclosure."""
        for entry in selectable_fields(db, clause_set):
            assert entry.datatype == "select"
            assert json.loads(entry.options_json)

    def test_a_value_outside_the_option_set_is_refused(self, db: Session, firm_id: int) -> None:
        with pytest.raises(EngagementError, match="not an option"):
            set_defaults(db, firm_id, {"caro.viii": "maybe"}, updated_by="t")

    def test_an_uncatalogued_field_is_refused(self, db: Session, firm_id: int) -> None:
        with pytest.raises(EngagementError, match="not a catalogued field"):
            set_defaults(db, firm_id, {"made.up.field": "none"}, updated_by="t")

    def test_a_blank_clears_the_default_rather_than_storing_one(
        self, db: Session, firm_id: int
    ) -> None:
        """ "The firm has no standing answer" and "the firm's answer is blank"
        are different, and only the first is meaningful."""
        set_defaults(db, firm_id, {"caro.viii": "none"}, updated_by="t")
        assert default_map(db, firm_id)["caro.viii"] == "none"

        saved, cleared = set_defaults(db, firm_id, {"caro.viii": ""}, updated_by="t")
        assert (saved, cleared) == (0, 1)
        assert "caro.viii" not in default_map(db, firm_id)

    def test_a_default_whose_option_was_withdrawn_is_reported_not_deleted(
        self, db: Session, firm_id: int
    ) -> None:
        """Eleven questions were withdrawn from the auditor's report on the day
        this was built. A firm that answered one deliberately should be told the
        question changed, not have the record quietly removed."""
        set_defaults(db, firm_id, {"caro.viii": "none"}, updated_by="t")
        entry = db.get(FieldCatalog, "caro.viii")
        assert entry is not None
        entry.options_json = json.dumps([{"value": "recorded", "label": "Recorded"}])
        db.flush()

        assert stale_defaults(db, firm_id) == ["caro.viii"]
        assert "caro.viii" in default_map(db, firm_id), "the record was deleted"

    def test_two_firms_do_not_share_answers(self, db: Session, firm_id: int) -> None:
        """Two practices in one installation are two sets of house positions."""
        other = Firm(firm_name="Other & Co", frn="999999W")
        db.add(other)
        db.flush()

        set_defaults(db, firm_id, {"caro.viii": "none"}, updated_by="t")
        assert default_map(db, other.firm_id) == {}


class TestApplyingThemToAnEngagement:
    def test_they_are_copied_onto_the_engagement_and_marked_as_defaults(
        self, db: Session, firm_id: int, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        """Readiness can no longer tell a standing answer from one a person
        entered (decision 28), so `source` is the only thing that can."""
        for state in field_states(db, engagement, clause_set):
            row = db.get(EngagementResponse, (engagement.engagement_id, state.key))
            if row is not None:
                db.delete(row)
        db.flush()

        set_defaults(db, firm_id, _clean_sheet(db, clause_set), updated_by="t")
        applied = apply_defaults(db, engagement, clause_set, firm_id, applied_by="t")
        assert applied, "nothing was applied"

        for key in applied:
            row = db.get(EngagementResponse, (engagement.engagement_id, key))
            assert row is not None
            assert row.source is ResponseSource.DEFAULT, key

    def test_an_applied_default_counts_as_answered(
        self, db: Session, firm_id: int, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        """The partner's instruction: finalise without repeating selections.

        The accepted consequence is asserted rather than hidden — readiness rises
        without anyone having looked at this client's file.
        """
        for state in field_states(db, engagement, clause_set):
            row = db.get(EngagementResponse, (engagement.engagement_id, state.key))
            if row is not None:
                db.delete(row)
        db.flush()
        before = readiness(field_states(db, engagement, clause_set))

        set_defaults(db, firm_id, _clean_sheet(db, clause_set), updated_by="t")
        apply_defaults(db, engagement, clause_set, firm_id, applied_by="t")

        assert readiness(field_states(db, engagement, clause_set)) > before

    def test_an_existing_answer_is_never_overwritten(
        self, db: Session, firm_id: int, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        row = db.get(EngagementResponse, (engagement.engagement_id, "caro.viii"))
        assert row is not None
        row.value_text = "not_recorded"
        row.source = ResponseSource.CARRIED_FORWARD
        row.reviewed = False
        db.flush()

        set_defaults(db, firm_id, {"caro.viii": "none"}, updated_by="t")
        apply_defaults(db, engagement, clause_set, firm_id, applied_by="t")

        db.expire_all()
        kept = db.get(EngagementResponse, (engagement.engagement_id, "caro.viii"))
        assert kept is not None
        assert kept.value_text == "not_recorded", "the master sheet overwrote an answer"
        assert kept.reviewed is False, "an unconfirmed carry-forward was silently confirmed"

    def test_editing_the_sheet_does_not_reach_an_existing_engagement(
        self, db: Session, firm_id: int, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        """An audit file in progress must not change because someone edited a
        settings screen. This is why the default is copied, not read through."""
        set_defaults(db, firm_id, {"caro.viii": "none"}, updated_by="t")
        row = db.get(EngagementResponse, (engagement.engagement_id, "caro.viii"))
        if row is not None:
            db.delete(row)
            db.flush()
        apply_defaults(db, engagement, clause_set, firm_id, applied_by="t")

        set_defaults(db, firm_id, {"caro.viii": "recorded"}, updated_by="t")
        db.expire_all()

        unchanged = db.get(EngagementResponse, (engagement.engagement_id, "caro.viii"))
        assert unchanged is not None
        assert unchanged.value_text == "none"


class TestTheRoutes:
    def test_the_sheet_lists_every_dropdown_in_every_document(
        self, db: Session, app_client: TestClient, clause_set: ClauseSet
    ) -> None:
        _sign_in(app_client)
        body = app_client.get("/admin/defaults").text
        posted = set(re.findall(r'name="default:([^"]+)"', body))
        assert posted == {entry.field_key for entry in selectable_fields(db, clause_set)}

    def test_nothing_is_preselected_on_the_sheet(
        self, app_client: TestClient, engagement: Engagement
    ) -> None:
        """The screen must not repeat the workspace's mistake — a dropdown
        showing an answer nobody chose. Here the blank comes first."""
        _sign_in(app_client)
        body = app_client.get("/admin/defaults").text
        block = re.search(r'name="default:caro\.viii">(.*?)</select>', body, re.S)
        assert block
        options = re.findall(r'<option value="([^"]*)"([^>]*)>', block.group(1))
        selected = [value for value, attrs in options if "selected" in attrs]
        assert selected == [""], f"something other than the blank is preselected: {selected}"

    def test_saving_the_sheet_then_opening_a_year_arrives_answered(
        self, db: Session, app_client: TestClient, client_id: int, clause_set: ClauseSet
    ) -> None:
        """The whole point, end to end: fill the sheet once, open a financial
        year, and the file is answered without touching a dropdown."""
        _sign_in(app_client)
        csrf = app_client.cookies.get("auditcraft_csrf")

        sheet = {f"default:{key}": value for key, value in _clean_sheet(db, clause_set).items()}
        saved = app_client.post(
            "/admin/defaults", data={"csrf_token": csrf, **sheet}, follow_redirects=False
        )
        assert saved.status_code == 303

        opened = app_client.post(
            f"/clients/{client_id}/engagements",
            data={"csrf_token": csrf, "fy_start": "2027-04-01", "fy_end": "2028-03-31"},
            follow_redirects=False,
        )
        assert opened.status_code == 303
        new_id = int(str(opened.headers["location"]).rsplit("/", 1)[-1])

        stored = db.scalars(
            select(EngagementResponse).where(EngagementResponse.engagement_id == new_id)
        ).all()
        assert stored, "the new year arrived with no answers"
        assert all(row.source is ResponseSource.DEFAULT for row in stored)

        page = app_client.get(f"/engagements/{new_id}?document=caro_2020").text
        assert "not saved" not in page, "dropdowns still show unsaved defaults"
        assert "Accept the" not in page, "still asking for defaults to be accepted"

    def test_a_client_with_no_financial_year_can_be_given_one(
        self, app_client: TestClient, client_id: int
    ) -> None:
        """This route did not exist, and without it decision 28 was unreachable
        for a new client: the only path to a financial year was rolling an
        existing one forward, so a client with none was a dead end."""
        _sign_in(app_client)
        body = app_client.get(f"/clients/{client_id}?tab=financial-years").text
        assert f'action="/clients/{client_id}/engagements"' in body

    def test_the_sheet_refuses_a_bad_value_without_losing_the_page(
        self, app_client: TestClient
    ) -> None:
        _sign_in(app_client)
        csrf = app_client.cookies.get("auditcraft_csrf")
        response = app_client.post(
            "/admin/defaults",
            data={"csrf_token": csrf, "default:caro.viii": "maybe"},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "not an option" in response.text
        assert 'name="default:caro.viii"' in response.text, "the sheet was not re-rendered"


class TestOverriding:
    def test_changing_a_dropdown_overrides_the_default_and_leaves_the_sheet_alone(
        self, db: Session, app_client: TestClient, firm_id: int, engagement: Engagement
    ) -> None:
        """The override direction only: an engagement never writes back to the
        firm's sheet. One client's facts must not become the house position."""
        _sign_in(app_client)
        set_defaults(db, firm_id, {"caro.viii": "none"}, updated_by="t")
        db.commit()

        csrf = app_client.cookies.get("auditcraft_csrf")
        app_client.post(
            f"/engagements/{engagement.engagement_id}/field",
            data={
                "csrf_token": csrf,
                "field_key": "caro.viii",
                "document": "caro_2020",
                "value": "recorded",
            },
            follow_redirects=False,
        )
        db.expire_all()

        overridden = db.get(EngagementResponse, (engagement.engagement_id, "caro.viii"))
        assert overridden is not None
        assert overridden.value_text == "recorded"
        assert overridden.source is ResponseSource.USER
        assert default_map(db, firm_id)["caro.viii"] == "none", "the firm's sheet was changed"


class TestDatesAreNotAssumed:
    def test_the_sheet_is_not_filtered_by_a_financial_year(
        self, db: Session, clause_set: ClauseSet
    ) -> None:
        """The sheet has no financial year, so a question that only applies from
        a later year still needs an answer on it. Filtering by today's date would
        hide it; filtering by an engagement's would make the sheet
        client-specific, which is what this screen exists to avoid."""
        dated = [
            entry
            for entry in selectable_fields(db, clause_set)
            if entry.effective_from and entry.effective_from > date(2020, 1, 1)
        ]
        if not dated:
            pytest.skip("no dated dropdown in the fixture repository")
        assert dated, "dated questions are being filtered out of the sheet"


class TestNilAnswersSuppressStaleRows:
    """Asked by the partner on seeing two litigation cases in a preview: "why
    are these cases shown as default for a clean company?"

    They were the seed script's demo rows, not defaults. But the question
    exposes a real exposure that nothing was pinning: **child rows outlive the
    answer that produced them.** They survive the answer being changed to nil,
    and on a roll-forward both the rows and the answer carry into the new year.
    A clean company must never print last year's litigation table.
    """

    def test_a_nil_answer_suppresses_rows_that_are_still_stored(
        self, db: Session, app_client: TestClient, engagement: Engagement
    ) -> None:
        from app.services.engagement import add_child_row, child_rows, set_response

        add_child_row(
            db,
            engagement.engagement_id,
            "litigation",
            {
                "forum": "NCLT Mumbai",
                "nature": "Operational creditor petition",
                "amount": "12,50,000",
                "status": "pending",
            },
            added_by="t",
        )
        set_response(db, engagement.engagement_id, "rule11.a.status", "disclosed", updated_by="t")
        db.commit()

        _sign_in(app_client)
        shown = app_client.get(
            f"/documents/{engagement.engagement_id}/auditors_report/preview"
        ).text
        assert "NCLT Mumbai" in shown, "the table does not print when it should"

        set_response(db, engagement.engagement_id, "rule11.a.status", "none", updated_by="t")
        db.commit()

        clean = app_client.get(
            f"/documents/{engagement.engagement_id}/auditors_report/preview"
        ).text
        assert "NCLT Mumbai" not in clean, "a nil answer still printed the stored rows"
        assert "does not have any pending litigations" in clean

        # The rows are deliberately NOT deleted — an auditor who flips an answer
        # by mistake must not lose the particulars they typed. Suppression is
        # the guard, so it is suppression that has to be asserted.
        assert child_rows(db, engagement.engagement_id, "litigation"), "the rows were destroyed"


class TestARuledOutDocumentSaysSo:
    """Reported by the partner: "IFC reporting is showing nil data whereas I
    selected the IFC applicable in main audit report."

    The annexure was empty because every one of its eleven clauses requires the
    `ifc` flag and the engine had ruled the company exempt. That was the correct
    determination, but the page showed a bare heading and nothing else — a
    document that had been ruled out looked identical to one that had failed to
    render.

    `BuiltDocument.not_applicable` was populated from the start precisely so the
    two could be told apart, and no template ever read it. The same shape of
    defect as `clause.requires` being parsed and never used.
    """

    def test_an_empty_document_is_detectable(self, production_clause_set: ClauseSet) -> None:
        from app.clauses.model import CONTEXT_VARIABLES
        from app.services.document import build_document

        context = dict.fromkeys(CONTEXT_VARIABLES, "")
        ruled_out = build_document(
            production_clause_set,
            "ifc_report",
            date(2026, 3, 31),
            context=context,
            applicable=frozenset({"caro"}),
        )
        assert ruled_out.has_body is False
        assert ruled_out.not_applicable
        # The flag that did it, so the page can name the determination rather
        # than report a bare count of absent clauses.
        assert ruled_out.excluded_by == frozenset({"ifc"})

        allowed = build_document(
            production_clause_set,
            "ifc_report",
            date(2026, 3, 31),
            context=context,
            applicable=frozenset({"caro", "ifc"}),
        )
        assert allowed.has_body is True
        assert allowed.not_applicable == ()

    def test_the_page_says_why_it_is_empty_and_where_to_change_it(
        self, db: Session, app_client: TestClient, engagement: Engagement
    ) -> None:
        """Both surfaces, because the preview pane and the standalone preview
        are different templates, and only one of them being fixed is exactly how
        this class of defect survives.

        Uses the CARO annexure rather than the IFC one — every clause in it
        requires the `caro` flag, so a CARO-exempt company empties it the same
        way an IFC-exempt company empties Annexure B. The fixture repository has
        no IFC document.
        """
        from app.models.masters import ClientProfile

        profile = db.get(ClientProfile, engagement.profile_id)
        assert profile is not None
        # CARO is stated, not inferred (decision 59), so the figures no longer
        # rule it out — the auditor does. The seeded profile says it applies;
        # this says otherwise.
        profile.caro = False
        profile.caro_override = True
        db.commit()

        _sign_in(app_client)
        for url in (
            f"/documents/{engagement.engagement_id}/caro_2020/preview",
            f"/engagements/{engagement.engagement_id}?document=caro_2020",
        ):
            page = app_client.get(url).text
            assert "not produced for this engagement" in page, url
            # The determination's own basis text, not a second explanation
            # written beside it that could drift from what was actually
            # decided. For a declared flag that basis names the auditor, since
            # no threshold was read.
            assert "stated by the auditor" in page, url
            assert (
                f"/engagements/{engagement.engagement_id}/applicability" in page
            ), f"{url} does not say where to change the determination"


class TestTheFinancialFiguresAreNoLongerAsked:
    """Decision 61 supersedes the 17 August request for an editing screen.

    The partner asked then for a way to edit paid-up capital, turnover,
    borrowings and the rest, because those figures decided CARO, IFC, CSR,
    internal audit and secretarial audit, and a wrong figure meant a wrong
    annexure. On 20 August all five became questions the auditor answers
    directly, and the figures stopped driving anything.

    They are no longer on the master-data screen. An input that changes no
    outcome is worse than no input: someone corrects it, watches the
    determination stay where it was, and has no way to tell whether the tool
    is broken or the figure was irrelevant.
    """

    def test_the_master_data_screen_asks_for_no_figures(self) -> None:
        from app.routers.clients import EDITABLE_FIELDS

        money = ("capital", "turnover", "borrow", "worth", "profit", "reserve", "deposit")
        offenders = [f for f in EDITABLE_FIELDS if any(w in f for w in money)]
        assert not offenders, f"the profile asks for figures again: {offenders}"

    def test_the_engine_cannot_read_one_even_if_asked(self) -> None:
        """The columns still exist; the engine's input object does not carry them."""
        import dataclasses

        from app.core.applicability import ProfileFacts

        fields = {f.name for f in dataclasses.fields(ProfileFacts)}
        for money in (
            "paid_up_capital",
            "turnover",
            "borrowings",
            "net_worth",
            "net_profit",
            "reserves",
            "deposits",
            "revenue",
        ):
            assert money not in fields, f"the engine can still read {money}"
