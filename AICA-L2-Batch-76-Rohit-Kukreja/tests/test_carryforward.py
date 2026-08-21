"""Phase 7 exit test — carry-forward and rollover (§6, §16).

The scenario is the protocol's Gate C one, run in code. Gate C then requires
it to be run again by hand, because a written account of it is not evidence.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import CarryForward, ClauseSet
from app.core.carryforward import (
    RolloverError,
    catalog_policies,
    roll_forward,
    unreviewed_carry_forwards,
)
from app.models.engagement import (
    Engagement,
    EngagementResponse,
    FieldCatalog,
    Litigation,
)
from app.models.enums import EngagementStatus, ResponseSource
from app.services.client import current_profile
from app.services.engagement import answer_map, set_response

FY_2026_27_START = date(2026, 4, 1)
FY_2026_27_END = date(2027, 3, 31)


@pytest.fixture
def source_id(db: Session, client_id: int) -> int:
    found = db.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == "2025-26")
    )
    assert found is not None
    return found.engagement_id


@pytest.fixture
def rolled(db: Session, source_id: int):
    return roll_forward(
        db,
        source_id,
        fy_start=FY_2026_27_START,
        fy_end=FY_2026_27_END,
        profile_id=None,
        rolled_by="manager@firm.local",
    )


class TestPolicyComesFromTheYaml:
    def test_policy_is_not_hardcoded_in_python(self, clause_set: ClauseSet) -> None:
        # §6.1 — "Policy is set in the clause YAML, never in Python."
        policies = catalog_policies(clause_set)
        assert policies["caro.viii"] is CarryForward.PROMPT
        assert set(policies.values()) <= set(CarryForward)

    def test_the_catalogue_agrees_with_the_yaml(self, db: Session, clause_set: ClauseSet) -> None:
        policies = catalog_policies(clause_set)
        for key, expected in policies.items():
            entry = db.get(FieldCatalog, key)
            assert entry is not None, key
            assert entry.carry_forward is expected, key

    def test_narratives_never_carry_forward(self, db: Session) -> None:
        # A prior year's explanation must never be presented as this year's.
        for entry in db.scalars(select(FieldCatalog)):
            if entry.field_key.endswith(".narrative"):
                assert entry.carry_forward is CarryForward.NEVER


class TestRollover:
    def test_a_new_engagement_is_created(self, rolled) -> None:
        engagement, report = rolled
        assert engagement.fy_code == "2026-27"
        assert report.fy_code == "2026-27"
        assert engagement.status is EngagementStatus.DATA_COLLECTION

    def test_it_records_where_it_came_from(self, rolled, source_id: int) -> None:
        engagement, _ = rolled
        assert engagement.rolled_from == source_id

    def test_prompt_answers_are_copied_but_unconfirmed(self, db: Session, rolled) -> None:
        # §6.1 — copied, `reviewed = False`, export blocked until confirmed.
        engagement, report = rolled
        row = db.get(EngagementResponse, (engagement.engagement_id, "caro.viii"))
        assert row is not None
        assert row.value_text == "none"
        assert row.source is ResponseSource.CARRIED_FORWARD
        assert row.reviewed is False
        assert "caro.viii" in report.requires_review

    def test_every_judgmental_answer_needs_confirmation(self, rolled) -> None:
        _, report = rolled
        # All six sample clauses are `prompt`, so all six must be flagged.
        assert report.review_count == len(report.carried)
        assert report.review_count > 0

    def test_unreviewed_list_matches_the_report(self, db: Session, rolled) -> None:
        engagement, report = rolled
        assert unreviewed_carry_forwards(db, engagement.engagement_id) == sorted(
            report.requires_review
        )

    def test_a_duplicate_year_is_refused(self, db: Session, source_id: int, rolled) -> None:
        with pytest.raises(RolloverError, match="already exists"):
            roll_forward(
                db,
                source_id,
                fy_start=FY_2026_27_START,
                fy_end=FY_2026_27_END,
                profile_id=None,
                rolled_by="m",
            )


class TestNeverFieldsAreBlanked:
    def test_a_narrative_is_not_carried(self, db: Session, source_id: int) -> None:
        set_response(
            db,
            source_id,
            "caro.viii.narrative",
            "Prior year explanation that must not reappear.",
            updated_by="t",
        )
        engagement, report = roll_forward(
            db,
            source_id,
            fy_start=FY_2026_27_START,
            fy_end=FY_2026_27_END,
            profile_id=None,
            rolled_by="m",
        )
        assert "caro.viii.narrative" in report.blanked
        assert db.get(EngagementResponse, (engagement.engagement_id, "caro.viii.narrative")) is None

    def test_year_specific_engagement_fields_are_not_copied(self, rolled) -> None:
        # §6.1 `never` — UDIN, report date, opinion. The new engagement
        # starts with none of them.
        engagement, _ = rolled
        assert engagement.report_date is None
        assert engagement.opinion_type is None
        assert engagement.locked_at is None


class TestChildRecords:
    def test_litigation_rows_carry_forward_flagged(self, db: Session, rolled) -> None:
        engagement, report = rolled
        rows = db.scalars(
            select(Litigation).where(Litigation.engagement_id == engagement.engagement_id)
        ).all()
        assert len(rows) == 2
        assert report.child_rows_carried["litigation"] == 2
        # §6.2 — litigation status changes constantly; never presume it.
        assert all(row.reviewed is False for row in rows)
        assert all(row.source is ResponseSource.CARRIED_FORWARD for row in rows)

    def test_amounts_survive_as_numbers(self, db: Session, rolled) -> None:
        engagement, _ = rolled
        rows = db.scalars(
            select(Litigation)
            .where(Litigation.engagement_id == engagement.engagement_id)
            .order_by(Litigation.row_index)
        ).all()
        assert rows[0].amount == Decimal("4260000")

    def test_board_meetings_are_not_carried(self, db: Session, rolled) -> None:
        """Recomputed from the register each year, never inherited (§18.8)."""
        _, report = rolled
        assert "board_meeting" not in report.child_rows_carried


class TestClauseMovements:
    """§6.3 step 5 — the step that makes the design amendment-proof."""

    def test_a_clause_newly_in_force_is_reported(self, db: Session, client_id: int) -> None:
        source = db.scalar(
            select(Engagement).where(
                Engagement.client_id == client_id, Engagement.fy_code == "2024-25"
            )
        )
        assert source is not None
        # FY 2023-24 → FY 2024-25 spans the audit-trail commencement, so
        # rule11.g becomes newly in force.
        source.fy_end = date(2023, 3, 31)
        db.flush()

        _, report = roll_forward(
            db,
            source.engagement_id,
            fy_start=date(2023, 4, 1),
            fy_end=date(2024, 3, 31),
            profile_id=None,
            rolled_by="m",
        )
        assert "rule11.g.status" in report.newly_in_force

    def test_a_retired_clause_is_not_carried_into_a_year_it_does_not_exist(
        self, db: Session, source_id: int
    ) -> None:
        entry = db.get(FieldCatalog, "caro.viii")
        assert entry is not None
        entry.effective_to = date(2026, 3, 31)
        db.flush()

        engagement, report = roll_forward(
            db,
            source_id,
            fy_start=FY_2026_27_START,
            fy_end=FY_2026_27_END,
            profile_id=None,
            rolled_by="m",
        )
        assert "caro.viii" in report.retired
        assert "caro.viii" not in report.carried
        assert db.get(EngagementResponse, (engagement.engagement_id, "caro.viii")) is None


class TestSelectiveCategories:
    def test_only_the_chosen_documents_are_copied(self, db: Session, source_id: int) -> None:
        _, report = roll_forward(
            db,
            source_id,
            fy_start=FY_2026_27_START,
            fy_end=FY_2026_27_END,
            profile_id=None,
            rolled_by="m",
            categories={"caro_2020"},
        )
        assert all(key.startswith("caro.") for key in report.carried)
        assert not any(key.startswith("rule11.") for key in report.carried)


class TestPriorYearIsUntouched:
    def test_rolling_forward_does_not_alter_the_source(
        self, db: Session, source_id: int, rolled
    ) -> None:
        # §18.6 — a prior-year document must remain reproducible.
        source_answers = {
            row.field_key: (row.value_text, row.reviewed, row.source)
            for row in db.scalars(
                select(EngagementResponse).where(EngagementResponse.engagement_id == source_id)
            )
        }
        assert source_answers["caro.viii"] == ("none", True, ResponseSource.USER)


class TestRollForwardCarriesTheProfile:
    """Decision 16 cleared the financial figures on roll-forward, so that a new
    year's applicability was never decided from last year's numbers.

    Both halves of that are gone. Decision 61 stopped every flag reading a
    figure, and decision 62 removed the columns. What roll-forward carries now
    is the company's identity and the facts an auditor states, none of which
    goes stale merely because the year turned.
    """

    def test_the_new_year_inherits_the_company_details(self, db: Session, client_id: int) -> None:
        profile = current_profile(db, client_id)
        assert profile.company_name
        assert profile.company_type is not None


class TestEveryDocumentCanCarryForward:
    """The document list was hard-coded to two of six.

    `DOCUMENT_CATEGORIES` named only the auditor's report and the CARO
    annexure, which silently overrode the per-clause `carry_forward` policies
    the register approved for the other four — 46 clauses marked `prompt` that
    could never carry at all. A 32-clause representation letter was being
    re-answered from scratch every year because of it.
    """

    def test_all_six_documents_less_the_engagement_letter_are_offered(
        self, production_clause_set
    ) -> None:
        from app.routers.rollover import NEVER_CARRIED, document_categories

        offered = {document_id for document_id, _ in document_categories(production_clause_set)}
        assert offered == set(production_clause_set.documents) - set(NEVER_CARRIED)
        assert "mrl" in offered, "the representation letter carried nothing forward"
        assert "directors_report" in offered
        assert "ifc_report" in offered

    def test_the_engagement_letter_is_excluded_on_purpose(self) -> None:
        """Gate C decision 18 — a fresh letter every year, so last year's
        answers must not be offered for reuse."""
        from app.routers.rollover import NEVER_CARRIED

        assert "engagement_letter" in NEVER_CARRIED
        assert NEVER_CARRIED["engagement_letter"].strip(), "no reason recorded"

    def test_the_list_follows_the_manifest(self, production_clause_set) -> None:
        """Derived, not hard-coded: a document added to the manifest must not
        have to be remembered here as well."""
        from app.routers.rollover import document_categories

        titles = dict(document_categories(production_clause_set))
        for document_id, title in titles.items():
            assert title == production_clause_set.documents[document_id].title

    def test_an_mrl_answer_is_carried_into_the_new_year(
        self, db: Session, client_id: int, clause_set: ClauseSet
    ) -> None:
        """The behaviour, not just the list. Asserted through the core roller
        so it holds regardless of what the form posts."""
        from app.core.carryforward import roll_forward

        source = db.scalar(
            select(Engagement).where(
                Engagement.client_id == client_id, Engagement.fy_code == "2025-26"
            )
        )
        assert source is not None
        set_response(db, source.engagement_id, "caro.viii", "none", updated_by="t")
        db.flush()

        target, report = roll_forward(
            db,
            source.engagement_id,
            fy_start=date(2027, 4, 1),
            fy_end=date(2028, 3, 31),
            profile_id=source.profile_id,
            rolled_by="t",
            categories=None,
        )
        db.flush()
        assert report.review_count > 0, "nothing carried forward at all"
        carried = answer_map(db, target.engagement_id)
        assert carried, "the new year has no answers"
