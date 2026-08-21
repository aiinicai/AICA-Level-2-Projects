"""Five changes asked for by the signing partner on 17 August 2026.

Decisions 29 to 33 in `docs/GATE_A_DECISIONS.md`. Each test names the property
that has to survive the change, not the control that implements it.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet
from app.models.engagement import Engagement, EngagementResponse
from app.models.enums import EngagementStatus
from app.models.issuance import AuditLog, DocumentInstance
from app.models.masters import Client, ClientProfile, Firm
from app.services.client import profile_versions
from app.services.engagement import (
    EngagementError,
    LockedError,
    delete_engagement,
    field_states,
)
from tests.test_client_routes import _sign_in


def _governed_document(clause_set: ClauseSet) -> tuple[str, str]:
    """A document every one of whose clauses requires the same single flag."""
    from app.services.applicability import governing_flag

    for document_id in clause_set.documents:
        flag = governing_flag(clause_set, document_id)
        if flag is not None:
            return document_id, flag
    raise AssertionError("no wholly gated document in this repository")


@pytest.fixture
def engagement(db: Session, client_id: int) -> Engagement:
    found = db.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == "2025-26")
    )
    assert found is not None
    return found


class TestDeletingAFinancialYear:
    """Decision 31 - remove a client's data for one year."""

    def test_it_removes_the_year_and_everything_recorded_against_it(
        self, db: Session, engagement: Engagement
    ) -> None:
        engagement_id = engagement.engagement_id
        assert db.scalars(
            select(EngagementResponse).where(EngagementResponse.engagement_id == engagement_id)
        ).all(), "the fixture has no answers, so this would assert nothing"

        delete_engagement(db, engagement_id, deleted_by="t")
        db.flush()

        assert db.get(Engagement, engagement_id) is None
        assert (
            db.scalars(
                select(EngagementResponse).where(EngagementResponse.engagement_id == engagement_id)
            ).all()
            == []
        )

    def test_the_client_survives(self, db: Session, engagement: Engagement, client_id: int) -> None:
        """Deleting a year is not deleting a client: its other years, profile
        versions and director register all stay."""
        before = len(profile_versions(db, client_id))
        delete_engagement(db, engagement.engagement_id, deleted_by="t")
        db.flush()

        assert db.get(Client, client_id) is not None
        assert len(profile_versions(db, client_id)) == before

    def test_a_finalised_year_cannot_be_deleted(self, db: Session, engagement: Engagement) -> None:
        """Documents have been issued from it, and its snapshots are what make a
        reprint byte-identical. This is the guard that must never be relaxed."""
        engagement.status = EngagementStatus.FINALISED
        db.flush()
        with pytest.raises(LockedError, match="Create Revision"):
            delete_engagement(db, engagement.engagement_id, deleted_by="t")

    def test_the_route_requires_the_fy_code_to_be_typed(
        self, db: Session, app_client: TestClient, engagement: Engagement, client_id: int
    ) -> None:
        """A bare button beside a list of years is one misclick from a year's
        work, and this cannot be undone."""
        _sign_in(app_client)
        csrf = app_client.cookies.get("auditcraft_csrf")
        engagement_id = engagement.engagement_id
        fy_code = engagement.fy_code

        refused = app_client.post(
            f"/clients/{client_id}/engagements/{engagement_id}/delete",
            data={"csrf_token": csrf, "confirm_fy": ""},
            follow_redirects=False,
        )
        assert refused.status_code == 400
        assert db.get(Engagement, engagement_id) is not None, "deleted without confirmation"

        accepted = app_client.post(
            f"/clients/{client_id}/engagements/{engagement_id}/delete",
            data={"csrf_token": csrf, "confirm_fy": fy_code},
            follow_redirects=False,
        )
        assert accepted.status_code == 303
        db.expire_all()
        assert db.get(Engagement, engagement_id) is None


class TestTheOneQuestionThatDecidesADocument:
    """Decisions 30 and 34 - one question decides whether a whole document is
    prepared, for CARO and for Annexure B.

    Written against whatever document the repository under test gates entirely
    behind one flag, rather than naming `ifc_report`: the control is derived
    from the clause set, and the fixture repository has CARO but no Annexure B.
    """

    def test_answering_yes_sets_the_flag_rather_than_an_answer_row(
        self, db: Session, app_client: TestClient, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        """It must write the applicability OVERRIDE, not a response row.

        The annexure, the paragraph in the auditor's report that refers to it and
        the engagement letter's scope all read one flag. A separate answer row
        would let them disagree, which is the failure the applicability engine
        exists to prevent - and the state the partner actually found, with the
        report saying IFC applied and Annexure B empty.
        """
        document, flag = _governed_document(clause_set)
        _sign_in(app_client)
        response = app_client.post(
            f"/engagements/{engagement.engagement_id}/document-applicable",
            data={
                "csrf_token": app_client.cookies.get("auditcraft_csrf"),
                "document": document,
                "choice": "not_applicable",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        db.expire_all()

        profile = db.get(ClientProfile, engagement.profile_id)
        assert profile is not None
        assert getattr(profile, f"{flag}_override") is True
        assert getattr(profile, flag) is False

    def test_answering_no_hides_every_question_in_that_section(
        self, app_client: TestClient, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        """ "Where CARO is not applicable, the related inputs should be hidden to
        avoid unnecessary data entry."

        The first attempt hid only 49 of 96 CARO fields: a narrative is
        catalogued as `<clause id>.narrative`, not under the clause's input key,
        so filtering on input keys alone left every explanation box on screen.
        """
        document, _flag = _governed_document(clause_set)
        _sign_in(app_client)
        csrf = app_client.cookies.get("auditcraft_csrf")

        before = app_client.get(f"/engagements/{engagement.engagement_id}?document={document}").text
        assert re.findall(r'id="input-', before), "no fields to hide"

        app_client.post(
            f"/engagements/{engagement.engagement_id}/document-applicable",
            data={"csrf_token": csrf, "document": document, "choice": "not_applicable"},
            follow_redirects=False,
        )
        after = app_client.get(f"/engagements/{engagement.engagement_id}?document={document}").text
        assert re.findall(r'id="input-', after) == [], "questions remain for a document ruled out"

    def test_overruling_the_figures_is_logged(
        self, db: Session, app_client: TestClient, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        """A reviewer needs to see that someone decided, not that a threshold
        was crossed."""
        document, flag = _governed_document(clause_set)
        _sign_in(app_client)
        app_client.post(
            f"/engagements/{engagement.engagement_id}/document-applicable",
            data={
                "csrf_token": app_client.cookies.get("auditcraft_csrf"),
                "document": document,
                "choice": "not_applicable",
            },
            follow_redirects=False,
        )
        db.expire_all()
        assert db.scalars(
            select(AuditLog).where(AuditLog.field == flag)
        ).all(), "an override reached the profile without being logged"

    def test_only_wholly_gated_documents_are_asked_about(self, clause_set: ClauseSet) -> None:
        """The auditor's report has one gated clause out of 34, so it is not
        decided by a flag and must not offer the question. Derived, so a
        document that stops being wholly gated stops being asked about."""
        from app.services.applicability import governing_flag

        assert governing_flag(clause_set, "auditors_report") is None


class TestTheReviewStatesAreGone:
    """Decision 29 - the preparer finalises, so the reviewer states described a
    handover that does not happen in this firm."""

    def test_neither_state_exists(self) -> None:
        assert not hasattr(EngagementStatus, "MANAGER_REVIEW")
        assert not hasattr(EngagementStatus, "PARTNER_REVIEW")

    def test_the_gates_they_carried_did_not_go_with_them(self) -> None:
        """Removing a reviewer is a decision about who works on the file. It is
        not a decision to let an incomplete file through, and the easy mistake
        would have been to delete both checks along with the states."""
        from app.core.permissions import TransitionError, require_transition

        with pytest.raises(TransitionError, match="blocking finding"):
            require_transition(
                EngagementStatus.PREPARED, EngagementStatus.APPROVED, blocking_findings=1
            )
        with pytest.raises(TransitionError, match="open review comment"):
            require_transition(
                EngagementStatus.PREPARED, EngagementStatus.APPROVED, open_comments=1
            )


class TestDraftOnLetterhead:
    """Decision 32 - read the document on firm paper during data collection."""

    def test_it_exports_while_the_file_still_has_findings(
        self, app_client: TestClient, engagement: Engagement
    ) -> None:
        """The whole request: see it before every finding is cleared."""
        _sign_in(app_client)
        response = app_client.get(f"/documents/{engagement.engagement_id}/auditors_report/draft")
        assert response.status_code == 200
        assert response.content[:2] == b"PK", "not a .docx"
        assert "DRAFT" in response.headers["content-disposition"]

    def test_it_is_not_recorded_as_an_issued_document(
        self, db: Session, app_client: TestClient, engagement: Engagement
    ) -> None:
        """A draft must never appear in the document register or the audit pack,
        and must not consume a version number."""
        before = len(
            db.scalars(
                select(DocumentInstance).where(
                    DocumentInstance.engagement_id == engagement.engagement_id
                )
            ).all()
        )
        _sign_in(app_client)
        app_client.get(f"/documents/{engagement.engagement_id}/auditors_report/draft")
        db.expire_all()
        after = len(
            db.scalars(
                select(DocumentInstance).where(
                    DocumentInstance.engagement_id == engagement.engagement_id
                )
            ).all()
        )
        assert after == before

    def test_the_draft_says_it_is_a_draft(
        self, app_client: TestClient, engagement: Engagement
    ) -> None:
        """A draft on the firm's letterhead is indistinguishable from a signed
        report once it is on a desk. The stamp is the only thing preventing that,
        so it lives in the body rather than as a watermark a copy-paste drops.
        """
        from io import BytesIO

        from docx import Document as DocxDocument

        _sign_in(app_client)
        response = app_client.get(f"/documents/{engagement.engagement_id}/auditors_report/draft")
        rendered = DocxDocument(BytesIO(response.content))
        assert any("NOT AN ISSUED DOCUMENT" in p.text for p in rendered.paragraphs)


class TestBranding:
    """Decision 33 - AuditCraft and the firm, on the first page."""

    def test_the_dashboard_shows_the_product_mark(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        page = app_client.get("/").text
        assert "masthead" in page
        assert "AuditCraft" in page

    def test_the_firm_is_read_from_its_record_never_hard_coded(
        self, db: Session, app_client: TestClient
    ) -> None:
        """Any CA firm can use this tool (decision 20), so the masthead has to
        read the firm record rather than name a firm in the template."""
        firm = db.scalar(select(Firm))
        assert firm is not None
        firm.firm_name = "Renamed & Co"
        db.flush()

        _sign_in(app_client)
        assert "Renamed &amp; Co" in app_client.get("/").text


class TestTheClientProfileAsksOnlyWhatIsUsed:
    """Decision 35 - remove inputs nothing consumes, add the ones the engine
    was reading and nobody could set."""

    def test_no_question_survives_that_nothing_reads(self) -> None:
        """Six were asked on the new-client form and used nowhere: no clause
        interpolated them, the engine did not read them, no document printed
        them. Asserted as a sweep of the form against the whole application, so
        a field that stops being used fails here rather than lingering."""
        from pathlib import Path

        from app.routers.clients import NEW_CLIENT_TEXT

        consumers = ""
        for folder, pattern in ((Path("content"), "*.yaml"), (Path("app"), "*.py")):
            for path in folder.rglob(pattern):
                if "routers/clients.py" in path.as_posix() or "models/masters" in path.as_posix():
                    continue
                consumers += path.read_text(encoding="utf-8", errors="replace")

        unused = [name for name, _label in NEW_CLIENT_TEXT if name not in consumers]
        assert unused == [], f"asked on the form and read by nothing: {unused}"

    def test_the_master_data_editor_asks_only_what_is_read(self) -> None:
        """Widened on 20 August 2026 to cover the whole profile form.

        Decision 62 swept fifteen more columns that nothing read. The sweep now
        runs over every field the master-data editor offers, not just the free
        text on the new-client form, because that is where the next unread
        field would appear.
        """
        from pathlib import Path

        from app.routers.clients import EDITABLE_FIELDS

        consumers = ""
        for folder, pattern in ((Path("content"), "*.yaml"), (Path("app"), "*.py")):
            for path in folder.rglob(pattern):
                if "routers/clients.py" in path.as_posix() or "models/masters" in path.as_posix():
                    continue
                consumers += path.read_text(encoding="utf-8", errors="replace")

        unused = [name for name in EDITABLE_FIELDS if name not in consumers]
        assert unused == [], f"editable and read by nothing: {unused}"

    def test_every_fact_captured_at_onboarding_can_be_corrected(self) -> None:
        """The gap decision 62 closed.

        Decision 35 put the engine's facts on the new-client form. It did not
        put them on the master-data editor, so a box mis-ticked at onboarding
        was permanent: the only way to change one was to create the client
        again. Anything askable at the start must be correctable later.
        """
        from app.routers.clients import EDITABLE_FIELDS, NEW_CLIENT_FACTS

        stranded = [name for name, _l, _h in NEW_CLIENT_FACTS if name not in EDITABLE_FIELDS]
        assert stranded == [], f"captured once and never correctable: {stranded}"

    def test_every_fact_the_engine_reads_can_be_set(self) -> None:
        """The mirror of the same defect. CFS, cost records, s.197 and
        secretarial audit were all decided partly from booleans that defaulted
        silently to False because no screen could set them."""
        import inspect

        from app.core.applicability import facts_from_profile
        from app.routers.clients import EDITABLE_FIELDS, NEW_CLIENT_FACTS, NEW_CLIENT_TEXT

        source = inspect.getsource(facts_from_profile)
        # `profile.company_type.value` names the column `company_type`; the
        # attribute after it is the enum's, not another column.
        read = {
            line.split("profile.")[1].split(",")[0].split(")")[0].strip().split(".")[0]
            for line in source.splitlines()
            if "profile." in line
        }
        settable = (
            {name for name, _l, _h in NEW_CLIENT_FACTS}
            | set(EDITABLE_FIELDS)
            | {name for name, _l in NEW_CLIENT_TEXT}
            | {"company_type", "framework"}
        )
        missing = sorted(name for name in read if name and name not in settable)
        assert missing == [], f"the engine reads these and nothing can set them: {missing}"


class TestProgress:
    """Decisions 36 and 37 - the workflow bar and per-section completion."""

    def test_the_stage_bar_has_exactly_one_current_step(
        self, db: Session, engagement: Engagement
    ) -> None:
        from app.services.progress import stages

        bar = stages(engagement)
        assert sum(1 for stage in bar if stage.current) == 1
        assert [stage.label for stage in bar] == [
            "Client profile",
            "Data collection",
            "Review",
            "Reports",
            "Finalisation",
        ]

    def test_a_finalised_engagement_shows_every_earlier_step_done(
        self, db: Session, engagement: Engagement
    ) -> None:
        from app.services.progress import stages

        engagement.status = EngagementStatus.FINALISED
        db.flush()
        bar = stages(engagement)
        assert all(stage.done for stage in bar if not stage.current)
        assert bar[-1].current

    def test_section_state_is_derived_not_stored(
        self, db: Session, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        """Answering a field must move its section without anything being
        written to say so - a stored 'done' flag drifts the moment an answer
        changes, and what it would drift about is whether a document can be
        signed."""
        from app.services.engagement import set_response
        from app.services.progress import SectionState, sections

        def caro() -> object:
            found = [
                s for s in sections(db, engagement, clause_set, None, set()) if s.id == "caro_2020"
            ]
            assert found, "the fixture has no CARO section"
            return found[0]

        for state in field_states(db, engagement, clause_set, "caro_2020"):
            row = db.get(EngagementResponse, (engagement.engagement_id, state.key))
            if row is not None:
                db.delete(row)
        db.flush()
        assert caro().state is SectionState.NOT_STARTED

        set_response(db, engagement.engagement_id, "caro.viii", "none", updated_by="t")
        db.flush()
        assert caro().state is not SectionState.NOT_STARTED


class TestDashboardShortcuts:
    """Decision 38 - the common actions, one click from the first screen."""

    def test_every_quick_action_points_somewhere_real(self, app_client: TestClient) -> None:
        """A shortcut to a 404 is worse than no shortcut. This codebase has
        already shipped one dead link and one page reachable only by typing."""
        _sign_in(app_client)
        page = app_client.get("/").text
        targets = re.findall(r'<a class="qa[^"]*" href="([^"]+)"', page)
        assert targets, "no quick actions rendered"
        for href in targets:
            response = app_client.get(href, follow_redirects=True)
            assert response.status_code == 200, f"{href} -> {response.status_code}"


class TestPreviewLooksLikeTheDocument:
    """Decision 39 - see the letterhead before finalising."""

    def test_both_previews_carry_the_firms_letterhead(
        self, db: Session, app_client: TestClient, engagement: Engagement
    ) -> None:
        """Two templates render a preview. Fixing one and not the other is
        exactly how this class of defect survives here."""
        firm = db.scalar(select(Firm))
        assert firm is not None
        _sign_in(app_client)
        for url in (
            f"/documents/{engagement.engagement_id}/auditors_report/preview",
            f"/engagements/{engagement.engagement_id}?document=auditors_report",
        ):
            page = app_client.get(url).text
            assert 'class="letterhead"' in page, url
            assert firm.firm_name in page, url

    def test_it_does_not_invent_a_page_count(
        self, app_client: TestClient, engagement: Engagement
    ) -> None:
        """A browser cannot know where the .docx page breaks fall, so a
        simulated "Page 1 of 4" would be a preview lying about the one thing it
        exists to show."""
        _sign_in(app_client)
        page = app_client.get(f"/documents/{engagement.engagement_id}/auditors_report/preview").text
        assert "applied by Word on export" in page
        assert not re.search(r"Page \d+ of \d+", page)


class TestStylesheetCannotGoStale:
    """A cached stylesheet made a working build look broken.

    `app.css` is served under a fixed name, so a browser holding a page open
    across a change kept its old copy: new markup, months-old rules. The result
    was an 800-pixel logo and the quick actions as a run of underlined links —
    indistinguishable from a broken deploy, and it survived a normal reload.
    """

    def test_the_stylesheet_is_fingerprinted(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        page = app_client.get("/").text
        href = re.search(r'<link rel="stylesheet" href="([^"]+)"', page)
        assert href, "no stylesheet link"
        assert re.fullmatch(r"/static/app\.css\?v=[0-9a-f]{8}", href.group(1)), href.group(1)

    def test_the_fingerprint_follows_the_content(self) -> None:
        """Content, not modification time: a file restored from a backup keeps
        its identity, and two machines serving the same bytes agree."""
        from app.templating import STATIC_DIR, _fingerprint, asset_url

        before = asset_url("app.css")
        original = (STATIC_DIR / "app.css").read_bytes()
        try:
            (STATIC_DIR / "app.css").write_bytes(original + b"\n/* touched */\n")
            _fingerprint.cache_clear()
            assert asset_url("app.css") != before, "the URL did not change with the content"
        finally:
            (STATIC_DIR / "app.css").write_bytes(original)
            _fingerprint.cache_clear()
        assert asset_url("app.css") == before

    def test_a_missing_asset_does_not_break_the_page(self) -> None:
        """A missing file is the template's problem to show, not a reason to
        fail every render in the application."""
        from app.templating import asset_url

        assert asset_url("does-not-exist.css") == "/static/does-not-exist.css?v=0"


class TestAnExemptCompanyCanBeFinalised:
    """A consistency rule tested for an option value the clause never offered.

    `iar.143.3.i` offers exempt / unmodified / modified. The rule accepted only
    a blank or the literal "exempt private company", so **the one correct answer
    for an IFC-exempt company still raised a blocking finding** — and a blocking
    finding stops approval, which stops finalisation. The commonest client in
    this practice, a small private company, could never have a report issued.

    Found by walking the finalisation sequence rather than by reading the rule:
    it looks right until you check it against the option set.
    """

    def test_the_rule_accepts_the_option_the_clause_offers(
        self, production_clause_set: ClauseSet
    ) -> None:
        """Asserted against the clause itself, so the two cannot drift again."""
        from app.core.applicability import Applicability, Flag
        from app.core.consistency import _applicability_rules

        clause = production_clause_set.get("iar.143.3.i")
        assert clause.input is not None
        exempt_option = clause.input.options[0].value

        applicability = Applicability(
            **{
                name: Flag(value=(name != "ifc"), basis="test")
                for name in Applicability.__dataclass_fields__
            }
        )
        engagement = Engagement(client_id=1, fy_code="2025-26")

        clean = _applicability_rules(engagement, {"iar.143.3.i": exempt_option}, applicability)
        assert [
            f.rule for f in clean
        ] == [], f"answering {exempt_option!r} on an IFC-exempt company still raises a finding"

        # The rule must still catch the case it exists for.
        wrong = _applicability_rules(engagement, {"iar.143.3.i": "unmodified"}, applicability)
        assert any(f.rule == "ifc_cross_reference" for f in wrong)


class TestEveryEngagementScreenIsReachableFromTheWorkspace:
    """ "I am not able to trace the Finalise audit option" — 19 August 2026.

    Readiness read 100% and there was nothing on the page to press. Finalise
    lives on the Review screen, and the only link to it anywhere was the
    dashboard's quick action, which points at whichever engagement was touched
    last rather than the one being worked on. From inside a file, its own
    Applicability, What Changed, roll forward and Review screens were reachable
    only by typing the address.

    **This had already happened once, to the workspace itself.** The sweep
    written then — `TestNothingIsReachableOnlyByTyping` — asserted that the
    workspace was linked, which is a fact about the last bug rather than a
    property. Written as a property here: the routes are discovered from the
    application, so a screen added later cannot be orphaned quietly.
    """

    def _engagement_screens(self) -> list[str]:
        """Every GET screen belonging to one engagement, from the application.

        Read off the OpenAPI schema rather than walked out of `app.routes`:
        FastAPI nests included routers behind `_IncludedRouter` objects whose
        inner paths are missing the router prefix, and a sweep that quietly
        resolves to nothing passes for ever. The schema carries full paths.
        """
        from app.main import app as application

        screens: list[str] = []
        for path, operations in application.openapi()["paths"].items():
            if "get" not in operations or "{engagement_id}" not in path:
                continue
            tail = path.split("{engagement_id}", 1)[1]
            # One fixed segment: a screen for the engagement as a whole. Routes
            # with a further parameter (a document, a generated file) are
            # reached from the thing they belong to, not from a nav bar.
            if tail.startswith("/") and "{" not in tail and tail.count("/") == 1:
                screens.append(tail)
        return sorted(set(screens))

    def test_the_routes_under_test_are_the_ones_that_matter(self) -> None:
        """A sweep that silently found nothing would pass for ever."""
        found = self._engagement_screens()
        assert "/validation" in found, found
        assert len(found) >= 3, found

    def test_each_one_that_works_is_linked_from_the_workspace(
        self, app_client: TestClient, engagement: Engagement
    ) -> None:
        """The property, stated so it has no hole: **a screen that answers must
        be reachable by clicking.**

        Not "every screen is linked" — What Changed correctly 404s on a first
        year, where there is no prior year to compare against, and linking it
        would just move the fault to the dead-link sweep. Asking the application
        which screens work for THIS engagement keeps both halves honest without
        a list to maintain.
        """
        _sign_in(app_client)
        base = f"/engagements/{engagement.engagement_id}"
        page = app_client.get(base).text

        missing = []
        for tail in self._engagement_screens():
            if app_client.get(base + tail).status_code != 200:
                continue  # not a screen for this engagement at all
            if f'href="{base}{tail}"' not in page:
                missing.append(tail)
        assert missing == [], f"reachable only by typing the address: {missing}"

    def test_finalise_is_on_the_screen_those_links_reach(
        self, app_client: TestClient, engagement: Engagement
    ) -> None:
        """What the partner was actually looking for, on the page the link now
        opens — not merely a link that resolves."""
        _sign_in(app_client)
        page = app_client.get(f"/engagements/{engagement.engagement_id}/validation").text
        assert f'action="/engagements/{engagement.engagement_id}/finalise"' in page
        assert 'name="udin"' in page, "no UDIN field to finalise with"


class TestEachDocumentGoesOutOnTheRightLetterhead:
    """ "The MRL should be on the company's letterhead" — 19 August 2026.

    Not a formatting preference. A Management Representation Letter is written
    BY the company TO the auditor; the audit firm's letterhead on it makes the
    auditor appear to have written the client's own representations. The Board's
    Report was wrong the same way — it is issued by the directors under s.134 and
    the auditor is not a party to it.

    The issuer is declared per document in the manifest, so a document added
    later has to state whose paper it is instead of inheriting the firm's.
    """

    def test_the_manifest_decides_it_not_the_document_id(
        self, production_clause_set: ClauseSet
    ) -> None:
        from app.clauses.model import IssuedBy

        by_issuer = {
            document_id: template.issued_by
            for document_id, template in production_clause_set.documents.items()
        }
        assert by_issuer["mrl"] is IssuedBy.COMPANY
        assert by_issuer["directors_report"] is IssuedBy.COMPANY
        assert by_issuer["auditors_report"] is IssuedBy.FIRM
        assert by_issuer["caro_2020"] is IssuedBy.FIRM
        assert by_issuer["ifc_report"] is IssuedBy.FIRM
        assert by_issuer["engagement_letter"] is IssuedBy.FIRM

    def test_a_company_letterhead_never_says_chartered_accountants(
        self, db: Session, production_clause_set: ClauseSet
    ) -> None:
        """The detail that would survive review because nobody reads a
        letterhead twice: the subtitle, and CIN rather than FRN."""
        from app.models.masters import Client as ClientModel
        from app.services.export import letterhead_for

        firm = db.scalar(select(Firm))
        client = db.scalar(select(ClientModel))
        profile = db.scalar(select(ClientProfile).where(ClientProfile.is_current.is_(True)))
        assert firm and client and profile

        company = letterhead_for(production_clause_set.documents["mrl"], firm, client, profile)
        assert company.name == profile.company_name
        assert company.subtitle == "", "the client is not a firm of chartered accountants"
        assert not company.logo_path and not company.logo_url, "the tool holds no client artwork"
        assert not any("FRN" in line for line in company.lines), "a company has a CIN, not an FRN"

        auditor = letterhead_for(
            production_clause_set.documents["auditors_report"], firm, client, profile
        )
        assert auditor.name == firm.firm_name
        assert auditor.subtitle == "Chartered Accountants"

    def test_an_unknown_issuer_is_refused_at_load(self, tmp_path) -> None:
        """Defaulting a typo to the firm would put the auditor's letterhead on
        the client's representation letter — silently, which is the whole
        failure this field exists to prevent."""
        import shutil

        from app.clauses.loader import ClauseValidationError, load_clause_set
        from app.config import PROJECT_ROOT

        content = tmp_path / "content"
        shutil.copytree(PROJECT_ROOT / "tests" / "fixtures" / "content", content)
        manifest = content / "manifest.yaml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(
                "  caro_2020:", "  caro_2020:\n    issued_by: the_bank", 1
            ),
            encoding="utf-8",
        )
        with pytest.raises(ClauseValidationError, match="issued_by"):
            load_clause_set(content)

    def test_the_preview_and_the_export_use_one_implementation(self) -> None:
        """A preview showing one party's letterhead while the export carries
        another would defeat the purpose of previewing at all."""
        import inspect

        from app.routers import documents as documents_router
        from app.routers import engagements as engagements_router
        from app.services import export

        for module in (documents_router, engagements_router):
            assert "letterhead_for" in inspect.getsource(module), module.__name__
        assert "letterhead_for" in inspect.getsource(export.draft_document)


class TestTheFirmActuallyReachesTheDocument:
    """Found when the firm's letterhead came off the MRL and there was nothing
    underneath it.

    `render_context_for` took `firm` and `partner` as optional arguments, and
    **not one of its four call sites passed either**. So `firm_name`,
    `firm_frn`, `firm_address`, `partner_name` and `partner_mno` were empty
    strings in every document the tool has ever produced — the auditor's report
    signed by nobody, and the representation letter addressed to a blank line
    above "Chartered Accountants".

    It was invisible because the clause bodies carry the *labels*: a signature
    block reading "Membership No:" with nothing after it looks like a template
    waiting to be filled rather than a bug.
    """

    def test_no_caller_builds_a_context_without_the_firm(self) -> None:
        """A sweep, not a list: the next caller must not be able to omit it
        either, which is exactly how this survived four call sites."""

        from app.config import PROJECT_ROOT

        offenders = []
        for path in (PROJECT_ROOT / "app").rglob("*.py"):
            if path.name == "render_context.py":
                continue  # where the function is defined
            text = path.read_text(encoding="utf-8")
            if "render_context_for(" in text:
                offenders.append(str(path.relative_to(PROJECT_ROOT)))
        assert offenders == [], (
            f"these build a render context directly, so the firm and partner "
            f"will be blank: {offenders}. Use `signing_context`."
        )

    def test_the_firm_and_partner_reach_a_rendered_document(
        self, db: Session, app_client: TestClient, engagement: Engagement
    ) -> None:
        from app.models.masters import Client as ClientModel

        client = db.get(ClientModel, engagement.client_id)
        assert client is not None
        firm = db.get(Firm, client.firm_id)
        assert firm is not None and firm.firm_name

        _sign_in(app_client)
        page = app_client.get(f"/documents/{engagement.engagement_id}/auditors_report/preview").text
        assert firm.firm_name in page, "the firm's name never reached the document"

    def test_the_letterhead_and_the_signature_name_the_same_firm(
        self, db: Session, engagement: Engagement, production_clause_set: ClauseSet
    ) -> None:
        """They disagreed for one turn — the letterhead read from the active-firm
        cookie while the signature block read from the client. A cookie chooses
        what someone is looking at; it does not decide whose name goes on a
        report."""
        from app.models.masters import Client as ClientModel
        from app.services.export import letterhead_for
        from app.services.render_context import firm_for_client, signing_context

        client = db.get(ClientModel, engagement.client_id)
        profile = db.get(ClientProfile, engagement.profile_id)

        head = letterhead_for(
            production_clause_set.documents["auditors_report"],
            firm_for_client(db, client),
            client,
            profile,
        )
        context = signing_context(db, engagement, client, profile)
        assert head.name == context["firm_name"] != ""


class TestNilAnswersDoNotDemandATable:
    """Reported by the firm's team, 19 August 2026, in three of five points.

    Every repeating block carried `min_rows: 1` with no condition, so answering
    "None" printed the correct nil paragraph AND still blocked export with "the
    table needs at least one row". Twelve of fourteen blocks were unguarded — a
    clean audit could not export without inventing Key Audit Matters, IFC
    deficiencies and uncorrected misstatements that did not exist.

    A colleague worked around it by typing the nil sentence into the **Name of
    the party** column, producing a document that said the right thing in the
    wrong place with a stray 0 beside it.
    """

    def test_a_nil_answer_never_leaves_a_table_outstanding(
        self, production_clause_set: ClauseSet
    ) -> None:
        """The property, over every clause that has both a question and a table:
        an answer that prints no table must not require rows.

        Swept rather than listed, because the bug was that a rule everyone knew
        had been applied to two clauses out of fourteen.
        """
        from datetime import date as _date

        from app.clauses.model import CONTEXT_VARIABLES
        from app.services.document import build_document

        offenders = []
        for clause in production_clause_set.clauses:
            if clause.repeating_block is None or clause.input is None:
                continue
            for option in clause.input.options:
                built = build_document(
                    production_clause_set,
                    clause.document,
                    _date(2026, 3, 31),
                    responses={clause.input.key: option.value},
                    child_rows={},
                    context=dict.fromkeys(CONTEXT_VARIABLES, ""),
                )
                if clause.id not in built.missing_rows:
                    continue
                # Demanding rows is only legitimate where the answer actually
                # prints a table for them to appear in.
                resolved = [
                    v
                    for v in clause.variants
                    if v.render_block is not None and v.when and option.value in v.when
                ]
                if not resolved:
                    offenders.append(f"{clause.id}={option.value}")
        assert offenders == [], f"these answers demand rows they cannot print: {offenders}"

    def test_the_guard_and_the_variant_cannot_contradict_each_other(self, tmp_path) -> None:
        """Two mechanisms answer one question: `repeating_block.when` decides
        whether the workspace OFFERS the table, `variant.render_block` whether
        the document PRINTS one, and `min_rows` is enforced from the second.

        When they disagreed the table was hidden on screen and demanded on
        export, leaving no control anywhere to satisfy it. The loader now
        refuses the combination — it caught a real one the moment it was added,
        on the arm's-length limb of Form AOC-2.
        """
        import shutil

        from app.clauses.loader import ClauseValidationError, load_clause_set
        from app.config import PROJECT_ROOT

        content = tmp_path / "content"
        shutil.copytree(PROJECT_ROOT / "content", content)
        target = content / "directors_report" / "bdr_subsidiaries.yaml"
        text = target.read_text(encoding="utf-8")
        # The table is printed by 'changes'; hide it for that very answer.
        target.write_text(
            text.replace("when: \"value == 'changes'\"", "when: \"value == 'none'\"", 1),
            encoding="utf-8",
        )
        with pytest.raises(ClauseValidationError, match="never offered on the workspace"):
            load_clause_set(content)


class TestTheCatalogueIsSyncedByStartup:
    """ "These points are not available to fill details" — the firm's team, with
    31 findings blocking export on the Board's Report and no field on the page.

    `field_catalog` turns a clause into a question, and it was built only by
    `scripts/seed.py` — a script nobody runs on a copy of the application. Their
    catalogue predated the Board's Report clauses, so the document knew every
    clause was unanswered and nothing rendered a control. Reproduced exactly by
    emptying the catalogue for one document: 0 fields, 32 findings.
    """

    def test_startup_owns_it_not_a_script(self) -> None:
        """However the application starts — `run.py`, the packaged .exe, or a
        test client — the catalogue must be brought in line with the repository.
        Wiring it into one entry point is what left the other two broken."""
        import inspect

        from app import main

        assert "_sync_catalogue" in inspect.getsource(main.lifespan)

    def test_it_fills_an_empty_catalogue(self, db: Session, clause_set: ClauseSet) -> None:
        from app.models.engagement import FieldCatalog
        from app.services.catalog import sync_field_catalog

        # The responses go first: a foreign key protects an answered field, which
        # is the same guard that stops `prune_orphans` deleting one.
        for answer in list(db.scalars(select(EngagementResponse))):
            db.delete(answer)
        db.flush()
        for row in list(db.scalars(select(FieldCatalog))):
            db.delete(row)
        db.flush()
        assert db.scalars(select(FieldCatalog)).all() == []

        count = sync_field_catalog(db, clause_set, prune=False)
        db.flush()
        assert count > 0
        assert len(db.scalars(select(FieldCatalog)).all()) == count

    def test_an_answered_field_is_never_pruned(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        """A foreign key protects it, so deleting one would stop the application
        opening at all — and an answer on a live engagement is evidence, not
        litter."""
        from app.models.engagement import FieldCatalog
        from app.services.catalog import prune_orphans
        from app.services.engagement import set_response

        set_response(db, engagement.engagement_id, "caro.viii", "none", updated_by="t")
        db.flush()

        entry = db.get(FieldCatalog, "caro.viii")
        assert entry is not None
        entry.clause_id = "gone.from.the.repository"
        db.flush()

        kept = prune_orphans(db, clause_set)
        db.flush()
        assert db.get(FieldCatalog, "caro.viii") is not None, "an answered field was deleted"
        assert kept == [] or "caro.viii" not in kept  # still live under its own key


class TestSmallCompanyHasNoCashFlowStatement:
    """Reported by the firm's team, 20 August 2026, on two documents.

    Section 2(40) first proviso: a One Person Company, a small company, a
    dormant company and a start-up private company need not include a cash flow
    statement in their financial statements. The partner confirmed the tool is
    used for **small companies and OPCs**, and that the exemption applies to
    those classes only.

    The failure this guards against is the wrong generalisation, not the
    omission: the query arrived worded as "not applicable in private limited
    company", and dropping the statement for every private company would put a
    false description of the financial statements into a signed report.
    """

    def test_only_the_exempt_classes_lose_it(self) -> None:
        from app.models.enums import CompanyType
        from app.services.render_context import CASH_FLOW_EXEMPT

        assert {CompanyType.SMALL, CompanyType.OPC} == CASH_FLOW_EXEMPT
        assert (
            CompanyType.PVT not in CASH_FLOW_EXEMPT
        ), "a private company is not exempt merely for being private"

    def test_an_unknown_company_type_keeps_the_fuller_wording(self) -> None:
        """A document must not quietly lose a statement because nobody set the
        company type. Absence of information is not evidence of exemption."""
        from datetime import date as _date

        from app.models.enums import GoingConcern
        from app.services.render_context import render_context_for

        engagement = Engagement(
            client_id=1,
            fy_code="2025-26",
            fy_start=_date(2025, 4, 1),
            fy_end=_date(2026, 3, 31),
            # Set explicitly: a column default is applied by the database on
            # insert, and this object never reaches it.
            going_concern=GoingConcern.NONE,
        )
        context = render_context_for(engagement, None, None)
        assert context["cash_flow_required"] is True

    def test_the_opinion_does_not_name_cash_flows_for_a_small_company(
        self, production_clause_set: ClauseSet
    ) -> None:
        """The operative sentence of the report. Swept over every opinion type,
        because the qualified and adverse opinions are separate variants and it
        would be easy to fix one and leave the others saying the accounts show a
        true and fair view of cash flows that were never prepared.
        """
        from datetime import date as _date

        from app.clauses.model import CONTEXT_VARIABLES
        from app.services.document import build_document

        for opinion in ("clean", "qualified", "adverse"):
            for required, expected in ((True, True), (False, False)):
                context = dict.fromkeys(CONTEXT_VARIABLES, "")
                context.update(
                    {
                        "framework": "igaap",
                        "cash_flow_required": required,
                        "opinion_type": opinion,
                        "going_concern": "none",
                        "company_name": "Test",
                    }
                )
                built = build_document(
                    production_clause_set,
                    "auditors_report",
                    _date(2026, 3, 31),
                    responses={},
                    context=context,
                    applicable=frozenset({"caro"}),
                )
                opinion_text = " ".join(
                    node.text
                    for node in built.document.nodes
                    if getattr(node, "text", "").startswith("In our opinion and to the best")
                )
                assert opinion_text, f"no opinion paragraph for {opinion}"
                assert (
                    "cash flows" in opinion_text.lower()
                ) is expected, f"{opinion} opinion, cash_flow_required={required}"

    def test_the_statements_audited_match_across_the_three_documents(
        self, production_clause_set: ClauseSet
    ) -> None:
        """The report, the representation letter and the engagement letter each
        list what was audited. They must agree — a letter naming a cash flow
        statement the report does not is exactly the contradiction this tool
        exists to prevent."""
        from datetime import date as _date

        from app.clauses.model import CONTEXT_VARIABLES
        from app.services.document import build_document

        for required in (True, False):
            context = dict.fromkeys(CONTEXT_VARIABLES, "")
            context.update(
                {
                    "framework": "igaap",
                    "cash_flow_required": required,
                    "opinion_type": "clean",
                    "going_concern": "none",
                    "company_name": "Test",
                }
            )
            for document_id, clause_id in (
                ("auditors_report", "iar.opinion.scope"),
                ("mrl", "mrl.header"),
                ("engagement_letter", "eng.framework"),
            ):
                built = build_document(
                    production_clause_set,
                    document_id,
                    _date(2026, 3, 31),
                    responses={},
                    context=context,
                    applicable=frozenset({"caro"}),
                )
                text = " ".join(
                    node.text for node in built.document.nodes if getattr(node, "text", "")
                )
                named = "Statement of Cash Flows" in text or "Cash Flow Statement" in text
                assert named is required, f"{clause_id}: cash_flow_required={required}"


class TestTypedControlsAndSigningPartner:
    """Five observations from the firm's team, 20 August 2026 (decision 50)."""

    def test_no_enum_is_edited_as_free_text(self, app_client: TestClient, client_id: int) -> None:
        """A single free-text box served every field on the master-data editor,
        so changing the framework or the company class meant typing an enum
        token exactly — "igaap", "small" — with a refusal on a near miss.

        Swept over the editable fields rather than checking the two that were
        reported, so a third enum added later cannot arrive as a text box.
        """
        from app.models.masters import ClientProfile as Profile
        from app.routers.clients import EDITABLE_FIELDS

        enum_fields = [
            name for name in EDITABLE_FIELDS if hasattr(getattr(Profile, name).type, "enums")
        ]
        assert enum_fields, "no enum-backed profile fields found; the sweep would assert nothing"

        _sign_in(app_client)
        page = app_client.get(f"/clients/{client_id}?tab=master-data").text
        for name in enum_fields:
            block = re.search(rf'<label for="f-{re.escape(name)}".*?</div>', page, re.S)
            assert block, f"{name} has no value control"
            assert "<select" in block.group(0), f"{name} is still edited as free text"

    def test_the_company_classes_are_named_not_tokenised(self, app_client: TestClient) -> None:
        """ "Classify the company as a Small Company, OPC, or Private Limited
        other than a Small Company." The form offered `pvt`, `opc`, `small`."""
        from app.routers.clients import COMPANY_TYPE_LABELS

        _sign_in(app_client)
        page = app_client.get("/clients/new").text
        assert COMPANY_TYPE_LABELS["small"] in page
        assert COMPANY_TYPE_LABELS["opc"] in page
        assert COMPANY_TYPE_LABELS["pvt"] in page
        assert "Small Company" in COMPANY_TYPE_LABELS["small"]
        # The distinction the team asked for: a private company that is NOT a
        # small company has to be separately nameable, or the classification
        # cannot express the cash-flow exemption of decision 49.
        assert "other than" in COMPANY_TYPE_LABELS["pvt"]

    def test_the_document_font_is_chosen_from_a_list(self, app_client: TestClient) -> None:
        """A misspelled face is substituted silently by Word, and the page
        breaks of a signed report move with it."""
        from app.routers.clients import DOCUMENT_FONTS

        _sign_in(app_client)
        page = app_client.get("/admin/firm").text
        block = re.search(r'id="f-doc_font"(.*?)</select>', page, re.S)
        assert block, "the document font is not a dropdown"
        for face in DOCUMENT_FONTS:
            assert f'value="{face}"' in block.group(1)

    def test_the_logo_is_offered_rather_than_fixed(self, app_client: TestClient) -> None:
        """The ICAI mark is the default and ships with the application, but a
        firm can choose its own or none: the mark is ICAI's, its use is governed
        by ICAI's guidelines for members, and decision 20 makes this
        installation usable by any practice."""
        from app.config import PROJECT_ROOT
        from app.routers.clients import ICAI_CA_LOGO

        assert (PROJECT_ROOT / "app" / "static" / "Firm_logo.png").is_file()

        _sign_in(app_client)
        block = re.search(
            r'id="f-logo_path"(.*?)</select>', app_client.get("/admin/firm").text, re.S
        )
        assert block, "the logo is not a dropdown"
        assert ICAI_CA_LOGO in block.group(1)
        assert 'value=""' in block.group(1), "a firm cannot choose to have no logo"

    def test_the_engagements_own_partner_signs_it(
        self, db: Session, app_client: TestClient, engagement: Engagement
    ) -> None:
        """Partner A signs client Y and partner B signs client Z under the same
        firm. `Engagement.partner_id` existed from the start and nothing read or
        set it, so every report in a firm with two signatories named whichever
        partner sorted first.
        """
        from app.models.masters import Client as ClientModel
        from app.models.masters import Partner
        from app.services.render_context import signing_context

        client = db.get(ClientModel, engagement.client_id)
        assert client is not None
        second = Partner(
            firm_id=client.firm_id,
            partner_name="Second Signatory",
            membership_no="999999",
            is_signing=True,
            active=True,
        )
        db.add(second)
        db.flush()

        engagement.partner_id = second.partner_id
        db.flush()
        assert signing_context(db, engagement, client, None)["partner_name"] == "Second Signatory"

        # Cleared: back to the firm's first active signatory, never to nobody.
        engagement.partner_id = None
        db.flush()
        assert signing_context(db, engagement, client, None)["partner_name"]

    def test_a_partner_of_another_firm_is_refused(
        self, db: Session, engagement: Engagement
    ) -> None:
        """An engagement naming one firm's member over another firm's
        letterhead is the sort of thing noticed only after a report goes out."""
        from app.models.masters import Firm as FirmModel
        from app.models.masters import Partner
        from app.services.engagement import set_engagement_field

        other_firm = FirmModel(firm_name="Unrelated & Co", frn="888888W")
        db.add(other_firm)
        db.flush()
        outsider = Partner(
            firm_id=other_firm.firm_id,
            partner_name="Outsider",
            membership_no="111111",
            is_signing=True,
            active=True,
        )
        db.add(outsider)
        db.flush()

        with pytest.raises(EngagementError, match="different firm"):
            set_engagement_field(
                db,
                engagement.engagement_id,
                "partner_id",
                str(outsider.partner_id),
                updated_by="t",
            )


class TestTheAccountingStandardsCitation:
    """Corrected on the partner's instruction, 20 August 2026 (decision 51).

    The clauses cited "Rule 7 of the Companies (Accounts) Rules, 2014" — the
    **transitional** provision, which deemed the standards notified under the
    Companies Act, 1956 to be the accounting standards until new ones were
    prescribed. The Accounting Standards are now prescribed by the Companies
    (Accounting Standards) Rules, 2021.

    Raised twice before it was acted on, and left unchanged until the partner
    said so: correcting a statutory citation in a signed report is the firm's
    call, not the tool's.
    """

    def test_no_clause_still_cites_the_transitional_rule(
        self, production_clause_set: ClauseSet
    ) -> None:
        """A sweep of every clause body, because the same phrase appeared in
        four variants across three documents and fixing the one that was
        reported would have left the report and the letter disagreeing."""
        offenders = [
            f"{clause.id}[{index}]"
            for clause in production_clause_set.clauses
            for index, variant in enumerate(clause.variants)
            if "Rule 7 of the Companies (Accounts) Rules" in " ".join(variant.body.split())
        ]
        assert offenders == [], f"still citing the transitional rule: {offenders}"

    def test_the_unrelated_rule_7_is_untouched(self, production_clause_set: ClauseSet) -> None:
        """`bdr.vigil.mechanism` cites Rule 7 of the Companies (Meetings of
        Board and its Powers) Rules, 2014 — a different Rule 7, correctly. A
        search-and-replace on "Rule 7" would have broken it."""
        clause = production_clause_set.get("bdr.vigil.mechanism")
        assert "Meetings of Board" in clause.clause_ref

    def test_the_three_documents_cite_the_same_rules(
        self, production_clause_set: ClauseSet
    ) -> None:
        """The report, the engagement letter and the representation letter each
        name the rules the accounts are prepared under. They must agree."""
        from datetime import date as _date

        from app.clauses.model import CONTEXT_VARIABLES
        from app.services.document import build_document

        expected = "Companies (Accounting Standards) Rules, 2021, as amended"
        for required in (True, False):
            context = dict.fromkeys(CONTEXT_VARIABLES, "")
            context.update(
                {
                    "framework": "igaap",
                    "cash_flow_required": required,
                    "opinion_type": "clean",
                    "going_concern": "none",
                    "company_name": "Test",
                }
            )
            for document_id in ("auditors_report", "engagement_letter", "mrl"):
                built = build_document(
                    production_clause_set,
                    document_id,
                    _date(2026, 3, 31),
                    responses={},
                    context=context,
                    applicable=frozenset({"caro"}),
                )
                text = " ".join(
                    node.text for node in built.document.nodes if getattr(node, "text", "")
                )
                assert expected in text, f"{document_id}, cash_flow_required={required}"

    def test_ind_as_still_cites_its_own_rules(self, production_clause_set: ClauseSet) -> None:
        """Ind AS is section 133 read with the Companies (Indian Accounting
        Standards) Rules, 2015, and was already correct. The correction must not
        have reached it."""
        clause = production_clause_set.get("iar.143.3.e")
        indas = [v for v in clause.variants if v.when and "indas" in v.when]
        assert indas, "no Ind AS variant to check"
        assert "Indian Accounting Standards) Rules, 2015" in " ".join(indas[0].body.split())
