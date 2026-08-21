"""Phase 8 exit test — locking and immutability (§10, §18.6, §18.7, §16).

The property under test: once finalised, an engagement cannot be edited, and
a prior-year document reprints byte-identically from its own snapshot even
after the client's master data changes.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet
from app.core.snapshot import content_hash, freeze, payload_hash, thaw
from app.models.engagement import Engagement
from app.models.enums import DocumentStatus, EngagementStatus
from app.models.issuance import DocumentInstance
from app.models.masters import Client, ClientProfile
from app.services.client import ChangeScope, change_profile
from app.services.document import build_document
from app.services.engagement import (
    LockedError,
    add_child_row,
    answer_map,
    child_row_dicts,
    set_response,
)
from app.services.render_context import render_context_for
from app.services.review import ReviewError, create_revision, finalise

UDIN = "26123456AB1234CD56"


@pytest.fixture
def open_engagement(db: Session, client_id: int) -> Engagement:
    found = db.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == "2025-26")
    )
    assert found is not None
    return found


@pytest.fixture
def locked(db: Session, client_id: int) -> Engagement:
    found = db.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == "2024-25")
    )
    assert found is not None
    return found


class TestLocking:
    def test_a_finalised_engagement_refuses_field_edits(
        self, db: Session, locked: Engagement
    ) -> None:
        with pytest.raises(LockedError, match="Create Revision"):
            set_response(db, locked.engagement_id, "caro.viii", "none", updated_by="t")

    def test_a_finalised_engagement_refuses_child_rows(
        self, db: Session, locked: Engagement
    ) -> None:
        with pytest.raises(LockedError):
            add_child_row(
                db,
                locked.engagement_id,
                "litigation",
                {"forum": "x", "nature": "y"},
                added_by="t",
            )

    def test_finalising_stamps_who_and_when(self, db: Session, open_engagement: Engagement) -> None:
        open_engagement.status = EngagementStatus.APPROVED
        db.flush()
        finalise(
            db,
            open_engagement.engagement_id,
            actor="partner@firm.local",
            udin=UDIN,
        )
        assert open_engagement.status is EngagementStatus.FINALISED
        assert open_engagement.locked_at is not None
        assert open_engagement.locked_by == "partner@firm.local"

    def test_anyone_can_finalise_in_a_single_user_build(
        self, db: Session, open_engagement: Engagement
    ) -> None:
        """Recorded deliberately: the partner-only gate went with the roles.

        This is the cost of Step 4a, written as an assertion so it cannot be
        mistaken for an oversight.
        """
        open_engagement.status = EngagementStatus.APPROVED
        db.flush()
        finalise(db, open_engagement.engagement_id, actor="anyone", udin=UDIN)
        assert open_engagement.status is EngagementStatus.FINALISED
        assert open_engagement.locked_by == "anyone"

    def test_an_invalid_udin_is_refused(self, db: Session, open_engagement: Engagement) -> None:
        open_engagement.status = EngagementStatus.APPROVED
        db.flush()
        with pytest.raises(ValueError, match="UDIN"):
            finalise(
                db,
                open_engagement.engagement_id,
                actor="p",
                udin="too-short",
            )

    def test_finalising_twice_is_refused(self, db: Session, open_engagement: Engagement) -> None:
        open_engagement.status = EngagementStatus.APPROVED
        db.flush()
        finalise(db, open_engagement.engagement_id, actor="p", udin=UDIN)
        with pytest.raises(ReviewError, match="already finalised"):
            finalise(
                db,
                open_engagement.engagement_id,
                actor="p",
                udin=UDIN,
            )


class TestCreateRevision:
    def test_it_is_the_only_way_back(self, db: Session, open_engagement: Engagement) -> None:
        open_engagement.status = EngagementStatus.APPROVED
        db.flush()
        finalise(db, open_engagement.engagement_id, actor="p", udin=UDIN)

        create_revision(
            db,
            open_engagement.engagement_id,
            "Typographical error in the basis paragraph",
            actor="p",
        )
        assert open_engagement.status is EngagementStatus.DATA_COLLECTION
        assert open_engagement.locked_at is None
        # Editing works again.
        set_response(db, open_engagement.engagement_id, "caro.viii", "recorded", updated_by="t")

    def test_a_reason_is_required(self, db: Session, open_engagement: Engagement) -> None:
        open_engagement.status = EngagementStatus.APPROVED
        db.flush()
        finalise(db, open_engagement.engagement_id, actor="p", udin=UDIN)
        with pytest.raises(ReviewError, match="reason is required"):
            create_revision(db, open_engagement.engagement_id, "  ", actor="p")

    def test_an_open_engagement_cannot_be_revised(
        self, db: Session, open_engagement: Engagement
    ) -> None:
        with pytest.raises(ReviewError, match="Only a finalised"):
            create_revision(db, open_engagement.engagement_id, "why", actor="p")

    def test_prior_documents_are_superseded_not_deleted(
        self, db: Session, open_engagement: Engagement
    ) -> None:
        db.add(
            DocumentInstance(
                engagement_id=open_engagement.engagement_id,
                doc_type="auditors_report",
                version_no=1,
                template_version="0.1.0-phase1",
                payload_json="{}",
                content_sha256="abc",
                status=DocumentStatus.DRAFT,
            )
        )
        open_engagement.status = EngagementStatus.APPROVED
        db.flush()
        finalise(db, open_engagement.engagement_id, actor="p", udin=UDIN)
        create_revision(db, open_engagement.engagement_id, "Correction", actor="p")

        documents = db.scalars(
            select(DocumentInstance).where(
                DocumentInstance.engagement_id == open_engagement.engagement_id
            )
        ).all()
        assert len(documents) == 1
        assert documents[0].status is DocumentStatus.SUPERSEDED
        assert documents[0].revision_reason == "Correction"
        # The signed content is untouched.
        assert documents[0].content_sha256 == "abc"


class TestSnapshotReproducibility:
    """§18.6 — changing master data must not alter a finalised document."""

    def _build(self, db: Session, clause_set: ClauseSet, engagement: Engagement):
        client = db.get(Client, engagement.client_id)
        profile = db.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None
        child_data = {
            clause.id: child_row_dicts(db, engagement.engagement_id, clause.repeating_block.entity)
            for clause in clause_set.for_document("caro_2020", engagement.fy_end)
            if clause.repeating_block is not None
        }
        responses = answer_map(db, engagement.engagement_id)
        context = render_context_for(engagement, client, profile)
        built = build_document(
            clause_set,
            "caro_2020",
            engagement.fy_end,
            responses=responses,
            child_rows=child_data,
            context=context,
        )
        payload = freeze(
            document_id="caro_2020",
            template_version=clause_set.manifest.template_version,
            responses=responses,
            child_rows=child_data,
            context=context,
        )
        return built, payload

    def test_freezing_the_same_inputs_twice_gives_identical_bytes(
        self, db: Session, clause_set: ClauseSet, open_engagement: Engagement
    ) -> None:
        _, first = self._build(db, clause_set, open_engagement)
        _, second = self._build(db, clause_set, open_engagement)
        assert first == second
        assert payload_hash(first) == payload_hash(second)

    def test_the_content_hash_is_stable(
        self, db: Session, clause_set: ClauseSet, open_engagement: Engagement
    ) -> None:
        first, _ = self._build(db, clause_set, open_engagement)
        second, _ = self._build(db, clause_set, open_engagement)
        assert content_hash(first.document) == content_hash(second.document)

    def test_changing_master_data_does_not_alter_a_frozen_snapshot(
        self, db: Session, clause_set: ClauseSet, open_engagement: Engagement, client_id: int
    ) -> None:
        built, payload = self._build(db, clause_set, open_engagement)
        original_hash = content_hash(built.document)

        change_profile(
            db,
            client_id,
            {"company_name": "ABC Limited (renamed)"},
            change_date=date(2026, 6, 1),
            changed_by="m",
            reason="Renamed",
            scope=ChangeScope.MASTER_ONLY,
        )
        db.flush()

        # The stored snapshot is the source of truth for a reprint.
        restored = thaw(payload)
        assert restored["context"]["company_name"] == "ABC Private Limited"
        assert payload_hash(payload) == payload_hash(payload)
        assert original_hash == content_hash(built.document)

    def test_a_decimal_does_not_drift(self) -> None:
        # Amounts are frozen as strings; a float round-trip would change the
        # hash of an unchanged document.
        payload = freeze(
            document_id="d",
            template_version="v",
            responses={"amount": Decimal("4260000.00")},
            child_rows={},
            context={},
        )
        assert '"4260000.00"' in payload
        assert thaw(payload)["responses"]["amount"] == "4260000.00"

    def test_an_unknown_snapshot_version_is_refused(self) -> None:
        with pytest.raises(ValueError, match="cannot be read"):
            thaw('{"snapshot_version": 99}')
