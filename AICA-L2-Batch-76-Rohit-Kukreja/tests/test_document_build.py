"""Document assembly from real engagement answers (§16 Phase 3, rebased).

Phase 3 built these from a hard-coded fixture. Phase 6 deleted it — every
value now comes from `engagement_response` and the child tables, which is
what a user actually writes.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet
from app.models.engagement import Engagement
from app.models.masters import Client, ClientProfile
from app.render.html import render
from app.services.document import BuiltDocument, build_document
from app.services.engagement import answer_map, child_row_dicts, set_response
from app.services.render_context import render_context_for
from tests.conftest import FY_2022_23


@pytest.fixture
def engagement(db: Session, client_id: int) -> Engagement:
    found = db.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == "2025-26")
    )
    assert found is not None, "seed missing the open engagement"
    return found


def _build(
    db: Session,
    clause_set: ClauseSet,
    engagement: Engagement,
    document_id: str,
    fy_end: date | None = None,
    responses: dict[str, Any] | None = None,
) -> BuiltDocument:
    client = db.get(Client, engagement.client_id)
    profile = db.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None
    child_data = {
        clause.id: child_row_dicts(db, engagement.engagement_id, clause.repeating_block.entity)
        for clause in clause_set.for_document(document_id, fy_end or engagement.fy_end)
        if clause.repeating_block is not None
    }
    return build_document(
        clause_set,
        document_id,
        fy_end or engagement.fy_end,
        responses=(
            responses if responses is not None else answer_map(db, engagement.engagement_id)
        ),
        child_rows=child_data,
        context=render_context_for(engagement, client, profile),
    )


class TestAuditorsReport:
    def test_every_in_force_clause_renders(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        built = _build(db, clause_set, engagement, "auditors_report")
        rendered = {n.clause_id for n in built.document.nodes if getattr(n, "clause_id", "")}
        assert rendered == {"rule11.a", "rule11.e", "rule11.f", "rule11.g"}

    def test_nothing_blocks_export(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        built = _build(db, clause_set, engagement, "auditors_report")
        assert built.exportable, (
            f"unanswered={built.unanswered} narratives={built.missing_narratives} "
            f"rows={built.missing_rows} placeholders={built.placeholders}"
        )

    def test_no_unresolved_placeholder_survives(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        # §18.4 — the prototype shipped 63 of these.
        assert _build(db, clause_set, engagement, "auditors_report").placeholders == ()

    def test_litigation_table_comes_from_the_child_table(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        built = _build(db, clause_set, engagement, "auditors_report")
        tables = [n for n in built.document.nodes if type(n).__name__ == "Table"]
        assert len(tables) == 1
        assert len(tables[0].rows) == 2
        assert "Court / Forum" in tables[0].headers

    def test_rule11e_three_parts_render_as_three_paragraphs(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        built = _build(db, clause_set, engagement, "auditors_report")
        paras = [n for n in built.document.nodes if getattr(n, "clause_id", "") == "rule11.e"]
        assert len(paras) == 3
        assert paras[0].text.startswith("(i)")
        assert paras[2].text.startswith("(iii)")

    def test_only_the_first_paragraph_carries_the_clause_number(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        built = _build(db, clause_set, engagement, "auditors_report")
        paras = [n for n in built.document.nodes if getattr(n, "clause_id", "") == "rule11.e"]
        assert paras[0].number == "(e)"
        assert all(p.number == "" for p in paras[1:])

    def test_clause_number_is_separated_from_the_body(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        html = render(_build(db, clause_set, engagement, "auditors_report").document)
        assert '<span class="clause-no">(a)</span> The' in html

    def test_nil_dividend_still_renders(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        # §4.2 — nil reporting is mandatory.
        built = _build(db, clause_set, engagement, "auditors_report")
        paras = [n for n in built.document.nodes if getattr(n, "clause_id", "") == "rule11.f"]
        assert paras and paras[0].text.strip()

    def test_audit_trail_clause_absent_from_an_earlier_year(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        built = _build(db, clause_set, engagement, "auditors_report", fy_end=FY_2022_23)
        rendered = {n.clause_id for n in built.document.nodes if getattr(n, "clause_id", "")}
        assert "rule11.g" not in rendered

    def test_company_name_interpolates_from_the_pinned_profile(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        context = render_context_for(
            engagement,
            db.get(Client, engagement.client_id),
            db.get(ClientProfile, engagement.profile_id),
        )
        assert context["company_name"] == "ABC Private Limited"
        assert context["fy_end_long"] == "31st March, 2026"


class TestCaroAnnexure:
    def test_renders_with_the_disputed_dues_table(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        built = _build(db, clause_set, engagement, "caro_2020")
        tables = [n for n in built.document.nodes if type(n).__name__ == "Table"]
        assert len(tables) == 1
        assert "Forum where Dispute is Pending" in tables[0].headers

    def test_exception_is_recorded_but_does_not_block(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        built = _build(db, clause_set, engagement, "caro_2020")
        assert "caro.vii.b" in built.exceptions
        assert built.exportable


class TestBlockingFindings:
    def test_missing_answer_blocks(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        built = _build(db, clause_set, engagement, "auditors_report", responses={})
        assert not built.exportable
        assert set(built.unanswered) == {"rule11.a", "rule11.e", "rule11.f", "rule11.g"}

    def test_an_answer_needing_a_narrative_blocks_until_it_is_given(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        set_response(
            db, engagement.engagement_id, "rule11.f.status", "not_complied", updated_by="t"
        )
        built = _build(db, clause_set, engagement, "auditors_report")
        assert "rule11.f" in built.missing_narratives
        assert not built.exportable

        set_response(
            db,
            engagement.engagement_id,
            "rule11.f.narrative",
            "Interim dividend paid without adequate profits.",
            updated_by="t",
        )
        cleared = _build(db, clause_set, engagement, "auditors_report")
        assert "rule11.f" not in cleared.missing_narratives

    def test_the_narrative_is_actually_printed(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        """The narrative must reach the page, not merely unblock the export.

        It did not. `requires_narrative` collected the text, checked it was
        present, and never rendered it — so an exception clause printed its
        lead-in ("...as follows:") and stopped. Every modified opinion, fraud
        disclosure and going concern uncertainty across all six documents
        would have been signed with the matter itself missing.
        """
        matter = "Interim dividend paid without adequate profits."
        set_response(
            db, engagement.engagement_id, "rule11.f.status", "not_complied", updated_by="t"
        )
        set_response(db, engagement.engagement_id, "rule11.f.narrative", matter, updated_by="t")

        built = _build(db, clause_set, engagement, "auditors_report")
        assert built.exportable
        assert any(
            matter in text for text in built.document.text_nodes()
        ), "the narrative is missing from the rendered document"

    def test_no_narrative_is_printed_when_none_is_required(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        """A stale narrative from a previous answer must not leak into a
        clean clause when the answer is changed back."""
        set_response(
            db, engagement.engagement_id, "rule11.f.narrative", "Stale text.", updated_by="t"
        )
        set_response(db, engagement.engagement_id, "rule11.f.status", "none", updated_by="t")
        built = _build(db, clause_set, engagement, "auditors_report")
        assert not any("Stale text." in text for text in built.document.text_nodes())


class TestPreviewRoute:
    def test_renders_from_the_engagement(self, app_client, engagement: Engagement) -> None:
        from tests.test_client_routes import _sign_in

        _sign_in(app_client)
        response = app_client.get(f"/documents/{engagement.engagement_id}/auditors_report/preview")
        assert response.status_code == 200
        assert "document-surface" in response.text
        # Proof the page is built from this engagement's stored data rather
        # than from anything hard-coded: the litigation forum lives only in
        # the `litigation` child table.
        assert "Commissioner of Income Tax (Appeals), Mumbai" in response.text
        assert "Independent Auditor" in response.text

    def test_unknown_document_is_a_clean_404(self, app_client, engagement: Engagement) -> None:
        from tests.test_client_routes import _sign_in

        _sign_in(app_client)
        response = app_client.get(f"/documents/{engagement.engagement_id}/not_a_document/preview")
        assert response.status_code == 404
        assert "Traceback" not in response.text

    def test_stylesheet_is_served_locally(self, app_client) -> None:
        response = app_client.get("/static/app.css")
        assert response.status_code == 200
        assert "@media print" in response.text


class TestHtmlIsWellFormed:
    def test_tags_balance(self, db: Session, clause_set: ClauseSet, engagement: Engagement) -> None:
        html = render(_build(db, clause_set, engagement, "auditors_report").document)
        for tag in ("article", "table", "thead", "tbody", "p"):
            assert html.count(f"<{tag}") == html.count(f"</{tag}>"), tag


class TestChildTableFormatting:
    """§12 and §19 — the table a partner signs, not raw repr()."""

    def test_amounts_use_indian_grouping(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        built = _build(db, clause_set, engagement, "caro_2020")
        table = next(n for n in built.document.nodes if type(n).__name__ == "Table")
        amounts = [row[2] for row in table.rows]
        # Not "4260000.00", and not western grouping either.
        assert "42,60,000" in amounts
        assert not any(cell.endswith(".00") for cell in amounts)

    def test_an_empty_amount_is_blank_not_the_word_none(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        built = _build(db, clause_set, engagement, "caro_2020")
        table = next(n for n in built.document.nodes if type(n).__name__ == "Table")
        for row in table.rows:
            for cell in row:
                assert cell != "None"

    def test_the_second_row_has_no_amount_paid(
        self, db: Session, clause_set: ClauseSet, engagement: Engagement
    ) -> None:
        # The seeded service-tax row has no amount paid under protest, which
        # is what makes the previous test meaningful rather than vacuous.
        built = _build(db, clause_set, engagement, "caro_2020")
        table = next(n for n in built.document.nodes if type(n).__name__ == "Table")
        assert table.rows[1][-1] == ""
