"""Phase 8 exit test — the consistency and completeness gate (§9, §16)."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet
from app.core.consistency import Severity, blocking, check, summarise, udin_finding
from app.models.engagement import Engagement, EngagementResponse
from app.models.enums import GoingConcern, OpinionType, ResponseSource
from app.services.engagement import set_response


@pytest.fixture
def engagement(db: Session, client_id: int) -> Engagement:
    found = db.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == "2025-26")
    )
    assert found is not None
    return found


def _rules(findings, rule: str):
    return [f for f in findings if f.rule == rule]


class TestCleanFile:
    def test_a_complete_engagement_has_no_blocking_findings(
        self, db: Session, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        findings = check(db, engagement, clause_set)
        assert not blocking(findings), [f.message for f in blocking(findings)]


class TestCrossDocumentContradictions:
    """Each document is individually plausible; the set contradicts itself."""

    def test_fraud_in_caro_but_not_in_the_mrl_blocks(self, engagement: Engagement) -> None:
        # CARO (xi) and the MRL fraud representation are not in the sample
        # repository yet, so the rule is exercised against its inputs
        # directly. Phase 2 will supply the clauses that feed it.
        from app.core.consistency import _cross_document_rules

        found = _cross_document_rules(
            engagement, {"caro.xi.a": "noticed", "mrl.fraud.disclosure": "none"}
        )
        assert _rules(found, "fraud_contradiction")
        assert _rules(found, "fraud_contradiction")[0].blocks

    def test_fraud_reported_in_both_is_clean(self, engagement: Engagement) -> None:
        from app.core.consistency import _cross_document_rules

        found = _cross_document_rules(
            engagement, {"caro.xi.a": "noticed", "mrl.fraud.disclosure": "disclosed"}
        )
        assert not _rules(found, "fraud_contradiction")

    def test_going_concern_uncertainty_but_caro_xix_says_none(
        self, db: Session, engagement: Engagement
    ) -> None:
        from app.core.consistency import _cross_document_rules

        engagement.going_concern = GoingConcern.MATERIAL_UNCERTAINTY
        found = _cross_document_rules(engagement, {"caro.xix": "none"})
        assert _rules(found, "going_concern_contradiction")

    def test_going_concern_uncertainty_with_caro_xix_agreeing_is_clean(
        self, engagement: Engagement
    ) -> None:
        from app.core.consistency import _cross_document_rules

        engagement.going_concern = GoingConcern.MATERIAL_UNCERTAINTY
        found = _cross_document_rules(engagement, {"caro.xix": "exists"})
        assert not _rules(found, "going_concern_contradiction")

    def test_a_modified_opinion_needs_a_basis_narrative(self, engagement: Engagement) -> None:
        from app.core.consistency import _cross_document_rules

        engagement.opinion_type = OpinionType.QUALIFIED
        found = _cross_document_rules(engagement, {})
        assert _rules(found, "missing_basis_narrative")

    def test_a_modified_opinion_needs_a_board_report_explanation(
        self, engagement: Engagement
    ) -> None:
        from app.core.consistency import _cross_document_rules

        engagement.opinion_type = OpinionType.ADVERSE
        found = _cross_document_rules(engagement, {})
        assert _rules(found, "board_report_contradiction")

    def test_a_clean_opinion_demands_neither(self, engagement: Engagement) -> None:
        from app.core.consistency import _cross_document_rules

        engagement.opinion_type = OpinionType.CLEAN
        found = _cross_document_rules(engagement, {})
        assert not found


class TestCompleteness:
    def test_an_empty_mandatory_field_blocks(
        self, db: Session, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        set_response(db, engagement.engagement_id, "caro.viii", "", updated_by="t")
        findings = check(db, engagement, clause_set)
        assert any(
            f.rule == "mandatory_empty" and f.field_key == "caro.viii" for f in blocking(findings)
        )

    def test_an_unconfirmed_carry_forward_blocks(
        self, db: Session, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        # §6.1 — export blocked until confirmed.
        row = db.get(EngagementResponse, (engagement.engagement_id, "caro.viii"))
        assert row is not None
        row.source = ResponseSource.CARRIED_FORWARD
        row.reviewed = False
        db.flush()

        findings = check(db, engagement, clause_set)
        assert any(f.rule == "unconfirmed_carry_forward" for f in blocking(findings))

    def test_confirming_clears_it(
        self, db: Session, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        row = db.get(EngagementResponse, (engagement.engagement_id, "caro.viii"))
        assert row is not None
        row.source = ResponseSource.CARRIED_FORWARD
        row.reviewed = True
        db.flush()
        findings = check(db, engagement, clause_set)
        assert not any(f.rule == "unconfirmed_carry_forward" for f in findings)


class TestPlaceholders:
    def test_an_unresolved_placeholder_blocks(
        self, db: Session, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        findings = check(
            db,
            engagement,
            clause_set,
            rendered_placeholders={"auditors_report": ("[State the opinion]",)},
        )
        assert any(f.rule == "unresolved_placeholder" for f in blocking(findings))


class TestIdentity:
    def test_a_missing_pinned_profile_blocks(
        self, db: Session, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        engagement.profile_id = None
        db.flush()
        findings = check(db, engagement, clause_set)
        assert any(f.rule == "no_pinned_profile" for f in blocking(findings))


class TestDates:
    def test_a_late_report_date_warns_but_does_not_block(
        self, db: Session, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        engagement.report_date = date(2027, 6, 1)
        db.flush()
        findings = check(db, engagement, clause_set)
        late = _rules(findings, "report_date_late")
        assert late and late[0].severity is Severity.WARN
        assert not late[0].blocks

    def test_a_normal_report_date_is_silent(
        self, db: Session, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        engagement.report_date = date(2026, 8, 12)
        db.flush()
        findings = check(db, engagement, clause_set)
        assert not _rules(findings, "report_date_late")


class TestUdin:
    def test_missing_udin_blocks_finalisation(self, engagement: Engagement) -> None:
        finding = udin_finding(engagement, None)
        assert finding is not None and finding.blocks

    def test_a_udin_clears_it(self, engagement: Engagement) -> None:
        assert udin_finding(engagement, "26123456AB1234CD56") is None


class TestOrdering:
    def test_blocks_come_before_warnings(
        self, db: Session, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        engagement.report_date = date(2027, 6, 1)
        set_response(db, engagement.engagement_id, "caro.viii", "", updated_by="t")
        findings = check(db, engagement, clause_set)
        severities = [f.severity for f in findings]
        assert severities == sorted(severities, key=lambda s: s is not Severity.BLOCK)

    def test_summary_counts(
        self, db: Session, engagement: Engagement, clause_set: ClauseSet
    ) -> None:
        counts = summarise(check(db, engagement, clause_set))
        assert set(counts) == {"block", "warn"}
