"""The six improvements approved on 21 August 2026. Decision 67.

Item 04 — help inside the tool — was deferred until the kit is final and is not
covered here.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet
from app.models.engagement import Engagement, Mgt9Shareholding
from app.models.masters import Client
from app.services.client import add_partner
from app.services.engagement import create_engagement
from tests.test_client_routes import _sign_in


class TestTheSigningPartnerFollowsTheClient:
    """Item 01. Forty clients meant making the same choice forty times a year."""

    def test_a_new_year_inherits_the_clients_partner(self, db: Session) -> None:
        client = db.scalar(select(Client))
        assert client is not None
        partner = add_partner(
            db,
            firm_id=client.firm_id,
            partner_name="Usual Signatory",
            membership_no="654321",
            is_signing=True,
        )
        db.flush()
        client.default_partner_id = partner.partner_id
        db.flush()

        engagement = create_engagement(
            db,
            client.client_id,
            date(2027, 4, 1),
            date(2028, 3, 31),
            profile_id=None,
            created_by="tester",
        )
        assert engagement.partner_id == partner.partner_id

    def test_it_is_copied_not_looked_up(self, db: Session) -> None:
        """The engagement's own partner is what a signed report names.

        Reassigning the client next year must not move the name on a report
        already issued, so the value is copied at the moment the year opens
        rather than read through to the client whenever a document renders.
        """
        client = db.scalar(select(Client))
        assert client is not None
        first = add_partner(
            db,
            firm_id=client.firm_id,
            partner_name="Signed It",
            membership_no="111222",
            is_signing=True,
        )
        db.flush()
        client.default_partner_id = first.partner_id
        db.flush()
        engagement = create_engagement(
            db,
            client.client_id,
            date(2029, 4, 1),
            date(2030, 3, 31),
            profile_id=None,
            created_by="tester",
        )

        second = add_partner(
            db,
            firm_id=client.firm_id,
            partner_name="Took Over",
            membership_no="333444",
            is_signing=True,
        )
        db.flush()
        client.default_partner_id = second.partner_id
        db.flush()

        assert engagement.partner_id == first.partner_id, "the old year followed the client"

    def test_no_default_leaves_the_year_to_choose(self, db: Session) -> None:
        client = db.scalar(select(Client))
        assert client is not None
        client.default_partner_id = None
        db.flush()
        engagement = create_engagement(
            db,
            client.client_id,
            date(2031, 4, 1),
            date(2032, 3, 31),
            profile_id=None,
            created_by="tester",
        )
        assert engagement.partner_id is None

    def test_a_partner_from_another_firm_is_refused(
        self, app_client: TestClient, db: Session
    ) -> None:
        """The control lists this firm's signatories; the route checks anyway."""
        from app.services.client import create_firm

        client = db.scalar(select(Client))
        assert client is not None
        other = create_firm(db, firm_name="Unrelated & Co", frn="097097W")
        db.flush()
        assert other.firm_id != client.firm_id

        stranger = add_partner(
            db,
            firm_id=other.firm_id,
            partner_name="Other Firm",
            membership_no="999888",
            is_signing=True,
        )
        db.commit()

        csrf = _sign_in(app_client)
        response = app_client.post(
            f"/clients/{client.client_id}/signing-partner",
            data={"csrf_token": csrf, "partner_id": str(stranger.partner_id)},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "not an active signatory" in response.text


class TestTheAnnexuresSayWhichReportTheyBelongTo:
    """Item 02. Two documents were both labelled "Annexure A"."""

    def test_no_two_documents_share_a_sidebar_label(self, production_clause_set: ClauseSet) -> None:
        titles = [d.short_title for d in production_clause_set.documents.values()]
        assert len(titles) == len(set(titles)), f"duplicate sidebar labels: {titles}"

    def test_each_annexure_names_its_parent_report(self, production_clause_set: ClauseSet) -> None:
        docs = production_clause_set.documents
        for doc_id, parent in (
            ("caro_2020", "Auditor's Report"),
            ("ifc_report", "Auditor's Report"),
            ("mgt9", "Board's Report"),
        ):
            label = docs[doc_id].short_title
            assert parent in label, f"{doc_id} does not say what it annexes: {label!r}"

    def test_the_printed_titles_are_untouched(self, production_clause_set: ClauseSet) -> None:
        """Only the sidebar changed. The `title` goes on a signed document."""
        docs = production_clause_set.documents
        assert docs["caro_2020"].title.startswith("Annexure A")
        assert docs["ifc_report"].title.startswith("Annexure B")


class TestNothingCountsTheDocuments:
    """Item 07. It produces seven, and the number moves with the client."""

    def test_no_source_file_says_six_documents(self) -> None:
        offenders = []
        for folder in (Path("app"), Path("content")):
            for path in folder.rglob("*"):
                if path.suffix not in {".py", ".html", ".yaml", ".css"}:
                    continue
                if "__pycache__" in path.as_posix():
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                if re.search(r"\b(all six|six document|six-document)\b", text, re.I):
                    offenders.append(path.as_posix())
        assert offenders == [], f"still counting documents: {offenders}"


class TestThePartnerRowsAreValidMarkup:
    """Item 06. A <tr> may hold only <td> and <th>."""

    def test_no_form_sits_inside_a_table_row(self) -> None:
        """A <tr> may contain only <td> and <th>.

        Written with index arithmetic rather than a regex. The first attempt
        used nested patterns, passed while an invalid row was deliberately
        planted in the template, and took four rounds to disbelieve -- a guard
        you cannot read is a guard you cannot trust.
        """
        template = Path(__file__).resolve().parent.parent / "app" / "templates" / "firm.html"
        page = template.read_text(encoding="utf-8")
        assert "partner-list" in page, "read the wrong file"

        # The template explains this very rule in a comment, and that prose
        # contains the literal text "<tr>". Strip comments before scanning.
        page = re.sub(r"\{#.*?#\}", "", page, flags=re.S)

        offenders = []
        for match in re.finditer(r"<tr\b[^>]*>", page):
            after = page[match.end() :]
            cell = after.find("<td")
            form = after.find("<form")
            close = after.find("</tr>")
            if form == -1 or (close != -1 and form > close):
                continue  # no form before this row closes
            if cell != -1 and cell < form:
                continue  # the form is inside a cell: legal
            offenders.append(page[match.start() : match.start() + 70])

        assert offenders == [], f"a form is a direct child of <tr>: {offenders}"

    def test_the_page_still_offers_both_controls(self, app_client: TestClient) -> None:
        _sign_in(app_client)
        body = app_client.get("/admin/firm").text
        assert "Still with the firm" in body
        assert 'action="/admin/partners' in body


class TestTheMgt9TablesRollForward:
    """Item 05. Six tables, retyped every year, in a company whose
    shareholding rarely moves."""

    def test_they_are_registered_to_roll(self) -> None:
        from app.core.carryforward import ROLLED_CHILD_MODELS

        for entity in (
            "mgt9_business_activity",
            "mgt9_shareholding",
            "mgt9_promoter_holding",
            "mgt9_director_holding",
            "mgt9_indebtedness",
        ):
            assert entity in ROLLED_CHILD_MODELS, f"{entity} does not roll forward"

    def test_a_carried_row_is_not_a_confirmed_one(self, db: Session) -> None:
        """Carrying is not confirming. Every carried row arrives for review,
        and the export gate holds until someone looks at it — the same rule
        litigation has followed since §6.2.
        """
        from app.core.carryforward import _roll_child_rows

        engagements = db.scalars(select(Engagement)).all()
        assert len(engagements) >= 2, "need two years to roll between"
        source, target = engagements[0], engagements[1]

        db.add(
            Mgt9Shareholding(
                engagement_id=source.engagement_id,
                category="Promoters",
                shares_begin="10000 / 100%",
                shares_end="10000 / 100%",
                reviewed=True,
            )
        )
        db.flush()

        _roll_child_rows(db, source.engagement_id, target.engagement_id, "tester")
        db.flush()

        carried = db.scalars(
            select(Mgt9Shareholding).where(Mgt9Shareholding.engagement_id == target.engagement_id)
        ).all()
        assert carried, "nothing was carried"
        assert all(not row.reviewed for row in carried), "a carried row arrived pre-confirmed"


class TestTheEngagementDetailsAreFoundable:
    """Item 03. The section existed and was collapsed; a new user never saw it."""

    def test_it_opens_while_something_required_is_unset(
        self, app_client: TestClient, db: Session
    ) -> None:
        engagement = db.scalar(select(Engagement))
        assert engagement is not None
        engagement.opinion_type = None
        db.commit()

        _sign_in(app_client)
        body = app_client.get(f"/engagements/{engagement.engagement_id}").text
        block = re.search(r"<details[^>]*engagement-level[^>]*>", body)
        assert block, "the engagement details section is gone"
        assert "open" in block.group(0), "it stayed collapsed with the opinion unset"

    def test_it_collapses_once_complete(self, app_client: TestClient, db: Session) -> None:
        """Collapsed is right once decided — decision 48 measured 567px of
        controls between the auditor and the first question."""
        from app.models.enums import OpinionType

        engagement = db.scalar(select(Engagement))
        assert engagement is not None
        engagement.opinion_type = OpinionType.CLEAN
        engagement.report_date = date(2026, 8, 1)
        db.commit()

        _sign_in(app_client)
        body = app_client.get(f"/engagements/{engagement.engagement_id}").text
        block = re.search(r"<details[^>]*engagement-level[^>]*>", body)
        assert block
        assert "open" not in block.group(0), "it stayed open after being completed"
