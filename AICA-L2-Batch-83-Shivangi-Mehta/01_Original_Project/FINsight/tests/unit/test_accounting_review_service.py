"""
Stage 8 — app/services/accounting_review_service.py: the full
preview/run/persist/re-run-preservation cycle, against a real (sandbox-
shimmed) SQLite DB and a real uploaded+mapped+validated file, so
`dataset_service.load_engagement_dataset()` is exercised for real
rather than mocked.

Stage 8 Round 2 (correction #1): the review is now framework-aware —
`_compute_outcomes()` requires the engagement to have an Entity Profile
with `accounting_framework` set, and raises `AccountingFrameworkNotSetError`
otherwise. Every fixture below now saves an Entity Profile before
exercising preview/run, and the seeded rule uses the framework-specific
rule_id (AS5-PPI-012 for an AS-framework engagement) rather than the old
framework-agnostic GEN-PPI-012.

Uses only synthetic, fabricated data — never real client/financial
data, per the standing instruction.

Run with: pytest tests/unit/test_accounting_review_service.py -v
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import pytest


def _save_entity_profile(engagement_service, engagement_id, accounting_framework="AS"):
    engagement_service.save_entity_profile(engagement_id, {
        "entity_type": "Company",
        "industry": None,
        "is_listed": False,
        "accounting_framework": accounting_framework,
        "is_gst_registered": False,
        "statutory_audit_applicable": False,
        "tax_audit_status": "REQUIRES_REVIEW",
        "consolidated_fs_applicable": False,
        "prior_year_data_available": False,
        "turnover": None,
        "overall_materiality": None,
        "performance_materiality": None,
        "clearly_trivial_threshold": None,
    })


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

    from app.models.rules import AccountingRule, Standard
    from app.services import accounting_review_service, engagement_service, mapping_service, upload_service

    engagement = engagement_service.create_engagement("Acme Manufacturing Ltd", "2025-26")
    _save_entity_profile(engagement_service, engagement.engagement_id, "AS")

    buf = io.BytesIO()
    pd.DataFrame([
        {"Description": "Prior period adjustment for FY24-25 expense", "Debit": 30000, "Credit": 0},
        {"Description": "Routine sale of goods", "Debit": 0, "Credit": 50000},
    ]).to_csv(buf, index=False)
    uploaded_file = upload_service.save_uploaded_file(
        engagement_id=engagement.engagement_id, original_filename="je.csv", file_type="JE",
        file_bytes=buf.getvalue(), input_dir=tmp_path / "data_input",
    )
    mapping_service.confirm_mappings(uploaded_file.file_id, [
        {"source_column": "Description", "target_field": "description", "confidence_score": 1.0},
        {"source_column": "Debit", "target_field": "debit_amount", "confidence_score": 1.0},
        {"source_column": "Credit", "target_field": "credit_amount", "confidence_score": 1.0},
    ])
    mapping_service.mark_file_status(uploaded_file.file_id, "VALIDATED")

    session = extensions.SessionLocal
    standard = Standard(framework="AS", code="AS 5", title="Net Profit or Loss for the Period, Prior Period Items and Changes in Accounting Policies")
    session.add(standard)
    session.commit()
    session.add(AccountingRule(
        rule_id="AS5-PPI-012", standard_id=standard.standard_id, framework="AS",
        topic="Prior Period Items / Errors — Narration Keyword Check", is_active=True, verification_status="VERIFIED",
    ))
    session.commit()

    class _Env:
        svc = accounting_review_service
        engagement_id = engagement.engagement_id

    yield _Env
    extensions.SessionLocal.remove()


def test_preview_does_not_persist_anything(env):
    review = env.svc.preview_accounting_review(env.engagement_id)
    assert review.framework == "AS"
    assert len(review.rule_outcomes["AS5-PPI-012"].exceptions) == 1
    assert review.persisted_exception_count == 0
    assert env.svc.get_last_review_results(env.engagement_id) == []


def test_run_persists_exception_and_linked_query(env):
    review = env.svc.run_accounting_review(env.engagement_id)
    assert review.framework == "AS"
    assert review.persisted_exception_count == 1
    assert review.preserved_exception_count == 0

    results = env.svc.get_last_review_results(env.engagement_id)
    assert len(results) == 1
    persisted = results[0]
    assert persisted.exception.rule_id == "AS5-PPI-012"
    assert persisted.exception.module == "ACCOUNTING"
    assert persisted.exception.status == "OPEN"
    assert "prior period" in persisted.exception.trigger_condition.lower()
    assert persisted.query is not None
    assert persisted.query.is_ai_drafted is False
    assert persisted.query.category == "ACCOUNTING"
    assert persisted.query.question_text  # the Suggested Query text
    assert "AS 5" in persisted.query.question_text
    assert "Ind AS 8" not in persisted.query.question_text


def test_engagement_not_found_raises(env):
    from app.services.accounting_review_service import EngagementNotFoundError
    with pytest.raises(EngagementNotFoundError):
        env.svc.preview_accounting_review(999999)


def test_no_entity_profile_raises_framework_not_set_error(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker

    from app import extensions
    from app.models import Base

    db_path = tmp_path / "test2.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    extensions.engine = engine
    extensions.SessionLocal = scoped_session(sessionmaker(bind=engine, future=True, expire_on_commit=False))

    from app.services import accounting_review_service, engagement_service
    from app.services.accounting_review_service import AccountingFrameworkNotSetError

    engagement = engagement_service.create_engagement("No Profile Ltd", "2025-26")
    with pytest.raises(AccountingFrameworkNotSetError):
        accounting_review_service.preview_accounting_review(engagement.engagement_id)

    extensions.SessionLocal.remove()


def test_rerunning_with_unchanged_data_does_not_pile_up_duplicates(env):
    env.svc.run_accounting_review(env.engagement_id)
    env.svc.run_accounting_review(env.engagement_id)
    env.svc.run_accounting_review(env.engagement_id)
    assert len(env.svc.get_last_review_results(env.engagement_id)) == 1


def test_reviewer_touched_exception_is_preserved_across_a_rerun(env):
    from sqlalchemy import select

    from app import extensions
    from app.models.exceptions import ExceptionRecord

    env.svc.run_accounting_review(env.engagement_id)
    first = env.svc.get_last_review_results(env.engagement_id)[0]
    original_exception_id = first.exception.exception_id

    # Simulate a reviewer starting work on it.
    stmt = select(ExceptionRecord).where(ExceptionRecord.exception_id == original_exception_id)
    row = extensions.SessionLocal.scalars(stmt).first()
    row.status = "UNDER_REVIEW"
    extensions.SessionLocal.commit()

    review = env.svc.run_accounting_review(env.engagement_id)
    assert review.preserved_exception_count == 1
    assert review.persisted_exception_count == 0  # same finding — not duplicated

    results = env.svc.get_last_review_results(env.engagement_id)
    assert len(results) == 1
    assert results[0].exception.exception_id == original_exception_id
    assert results[0].exception.status == "UNDER_REVIEW"
