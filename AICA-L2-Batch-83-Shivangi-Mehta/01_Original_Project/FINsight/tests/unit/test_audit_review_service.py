"""
Stage 9 — app/services/audit_review_service.py: the full preview/run/
persist/re-run-preservation cycle, against a real (sandbox-shimmed)
SQLite DB and a real uploaded+mapped+validated file, so
`dataset_service.load_engagement_dataset()` is exercised for real
rather than mocked. Mirrors tests/unit/test_accounting_review_service.py,
with the deliberate Stage 9 differences: no Entity Profile / framework
precondition, `standard_reference` populated from `AuditRule.related_sa`
free text, `assertions_snapshot` populated via the AuditRuleAssertion
junction, module="AUDIT".

Uses only synthetic, fabricated data — never real client/financial
data, per the standing instruction.

Run with: pytest tests/unit/test_audit_review_service.py -v
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import pytest


@pytest.fixture()
def env(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker

    from app import extensions
    from app.models import Base

    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    extensions.engine = engine
    extensions.SessionLocal = scoped_session(sessionmaker(bind=engine, future=True, expire_on_commit=False))

    from app.models.rules import AuditAssertion, AuditRule, AuditRuleAssertion, Standard
    from app.services import audit_review_service, engagement_service, mapping_service, upload_service

    # Deliberately NO Entity Profile save — Audit has no framework precondition.
    engagement = engagement_service.create_engagement("Acme Manufacturing Ltd", "2025-26")

    # A manual JE dated on a Saturday (2026-03-28) — matches AUD-JE-002's
    # weekend heuristic, the only audit rule seeded in this fixture.
    buf = io.BytesIO()
    pd.DataFrame([
        {"Is Manual Entry": "Yes", "Transaction Date": "2026-03-28", "Description": "Adjustment entry"},
        {"Is Manual Entry": "No", "Transaction Date": "2026-03-30", "Description": "Routine entry"},
    ]).to_csv(buf, index=False)
    uploaded_file = upload_service.save_uploaded_file(
        engagement_id=engagement.engagement_id, original_filename="je.csv", file_type="JE",
        file_bytes=buf.getvalue(), input_dir=tmp_path / "data_input",
    )
    mapping_service.confirm_mappings(uploaded_file.file_id, [
        {"source_column": "Is Manual Entry", "target_field": "is_manual_entry", "confidence_score": 1.0},
        {"source_column": "Transaction Date", "target_field": "transaction_date", "confidence_score": 1.0},
        {"source_column": "Description", "target_field": "description", "confidence_score": 1.0},
    ])
    mapping_service.mark_file_status(uploaded_file.file_id, "VALIDATED")

    session = extensions.SessionLocal
    standard = Standard(framework="SA", code="SA 240", title="The Auditor's Responsibilities Relating to Fraud")
    session.add(standard)
    session.commit()
    session.add(AuditRule(
        rule_id="AUD-JE-002", standard_id=standard.standard_id, topic="Manual Journal Entry Posted on a Non-Business Day",
        is_active=True, verification_status="VERIFIED", related_sa="SA 240", audit_area="Journal Entry Testing",
        suggested_audit_procedure="Consider whether a brief inquiry is warranted.",
        suggested_evidence="Journal voucher, explanation for the posting date.",
    ))
    occurrence = AuditAssertion(code="OCCURRENCE", label="Occurrence")
    existence = AuditAssertion(code="EXISTENCE", label="Existence")
    session.add(occurrence)
    session.add(existence)
    session.commit()
    session.add(AuditRuleAssertion(rule_id="AUD-JE-002", assertion_id=occurrence.assertion_id))
    session.add(AuditRuleAssertion(rule_id="AUD-JE-002", assertion_id=existence.assertion_id))
    session.commit()

    class _Env:
        svc = audit_review_service
        engagement_id = engagement.engagement_id

    yield _Env
    extensions.SessionLocal.remove()


def test_preview_does_not_persist_anything(env):
    review = env.svc.preview_audit_review(env.engagement_id)
    assert len(review.rule_outcomes["AUD-JE-002"].exceptions) == 1
    assert review.persisted_exception_count == 0
    assert env.svc.get_last_review_results(env.engagement_id) == []


def test_run_persists_exception_with_standard_reference_and_assertions_snapshot(env):
    review = env.svc.run_audit_review(env.engagement_id)
    assert review.persisted_exception_count == 1
    assert review.preserved_exception_count == 0

    results = env.svc.get_last_review_results(env.engagement_id)
    assert len(results) == 1
    persisted = results[0]
    assert persisted.exception.rule_id == "AUD-JE-002"
    assert persisted.exception.module == "AUDIT"
    assert persisted.exception.status == "OPEN"
    # standard_reference comes from AuditRule.related_sa free text, not a single Standard row.
    assert persisted.exception.standard_reference == "SA 240"
    # assertions_snapshot populated via the AuditRuleAssertion junction.
    assert set(persisted.assertions) == {"OCCURRENCE", "EXISTENCE"}
    assert persisted.query is not None
    assert persisted.query.category == "AUDIT"
    assert persisted.query.is_ai_drafted is False


def test_engagement_not_found_raises(env):
    from app.services.audit_review_service import EngagementNotFoundError
    with pytest.raises(EngagementNotFoundError):
        env.svc.preview_audit_review(999999)


def test_no_entity_profile_needed_review_still_runs(env):
    # The defining Stage 9 difference from Accounting: no framework
    # precondition, so a review runs fine with no Entity Profile at all
    # (the fixture above never saves one).
    review = env.svc.preview_audit_review(env.engagement_id)
    assert review.rule_outcomes  # ran without raising


def test_rerunning_with_unchanged_data_does_not_pile_up_duplicates(env):
    env.svc.run_audit_review(env.engagement_id)
    env.svc.run_audit_review(env.engagement_id)
    env.svc.run_audit_review(env.engagement_id)
    assert len(env.svc.get_last_review_results(env.engagement_id)) == 1


def test_reviewer_touched_exception_is_preserved_across_a_rerun(env):
    from sqlalchemy import select

    from app import extensions
    from app.models.exceptions import ExceptionRecord

    env.svc.run_audit_review(env.engagement_id)
    first = env.svc.get_last_review_results(env.engagement_id)[0]
    original_exception_id = first.exception.exception_id

    stmt = select(ExceptionRecord).where(ExceptionRecord.exception_id == original_exception_id)
    row = extensions.SessionLocal.scalars(stmt).first()
    row.status = "UNDER_REVIEW"
    extensions.SessionLocal.commit()

    review = env.svc.run_audit_review(env.engagement_id)
    assert review.preserved_exception_count == 1
    assert review.persisted_exception_count == 0

    results = env.svc.get_last_review_results(env.engagement_id)
    assert len(results) == 1
    assert results[0].exception.exception_id == original_exception_id
    assert results[0].exception.status == "UNDER_REVIEW"


def test_get_audit_rules_by_id_and_assertion_codes_by_rule_id(env):
    rules_by_id = env.svc.get_audit_rules_by_id()
    assert "AUD-JE-002" in rules_by_id
    assert rules_by_id["AUD-JE-002"].suggested_evidence == "Journal voucher, explanation for the posting date."

    assertion_codes = env.svc.get_assertion_codes_by_rule_id()
    assert set(assertion_codes["AUD-JE-002"]) == {"OCCURRENCE", "EXISTENCE"}
