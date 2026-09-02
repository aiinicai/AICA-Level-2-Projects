"""
Stage 10 — app/services/tax_review_service.py: the full preview/run/
persist/re-run-preservation cycle, against a real (sandbox-shimmed)
SQLite DB and a real uploaded+mapped+validated Accounts Payable file,
so `dataset_service.load_engagement_dataset()` is exercised for real
rather than mocked. Mirrors tests/unit/test_audit_review_service.py,
with the one deliberate Stage 10 difference from both Accounting and
Audit: the Act-transition precondition (Decision 1) —
`ActEraNotSupportedError` is raised for an engagement whose financial
year falls under the (unverified) Income-tax Act, 2025, BEFORE any tax
rule ever runs. `standard_reference` is populated from
`TaxRule.provision_reference` (the verified old-Act citation only,
never the New Act 2025 forward reference), module="TAX", no
assertions_snapshot (Tax exceptions never populate that field, per the
existing model comment).

Uses only synthetic, fabricated data — never real client/financial
data, per the standing instruction.

Run with: pytest tests/unit/test_tax_review_service.py -v
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

    from app.models.rules import TaxRule
    from app.services import engagement_service, mapping_service, tax_review_service, upload_service

    # Old-Act engagement (FY 2025-26 / AY 2026-27) — every currently
    # coded tax rule is verified and gated against this era only.
    engagement = engagement_service.create_engagement("Acme Manufacturing Ltd", "2025-26")

    # New-Act engagement (FY 2026-27) — used only by the
    # ActEraNotSupportedError test below; no data is uploaded for it,
    # since the precondition must fire before any rule (or even
    # dataset load) ever runs.
    new_act_engagement = engagement_service.create_engagement("Acme Manufacturing Ltd", "2026-27")

    # An AP payable to "Bright Traders" recorded at the very start of
    # the FY, with no further movement — well past TAX-MSME-013's
    # 45-day ageing window as of FY end (2026-03-31), and well above
    # its ₹1,000 noise floor.
    buf = io.BytesIO()
    pd.DataFrame([
        {"Party Name": "Bright Traders", "Transaction Date": "01-06-2025", "Credit Amount": "50000", "Debit Amount": ""},
        {"Party Name": "Quick Suppliers", "Transaction Date": "15-03-2026", "Credit Amount": "2000", "Debit Amount": ""},
    ]).to_csv(buf, index=False)
    uploaded_file = upload_service.save_uploaded_file(
        engagement_id=engagement.engagement_id, original_filename="ap.csv", file_type="AP",
        file_bytes=buf.getvalue(), input_dir=tmp_path / "data_input",
    )
    mapping_service.confirm_mappings(uploaded_file.file_id, [
        {"source_column": "Party Name", "target_field": "party_name", "confidence_score": 1.0},
        {"source_column": "Transaction Date", "target_field": "transaction_date", "confidence_score": 1.0},
        {"source_column": "Credit Amount", "target_field": "credit_amount", "confidence_score": 1.0},
        {"source_column": "Debit Amount", "target_field": "debit_amount", "confidence_score": 1.0},
    ])
    mapping_service.mark_file_status(uploaded_file.file_id, "VALIDATED")

    session = extensions.SessionLocal
    session.add(TaxRule(
        rule_id="TAX-MSME-013", topic="MSME Delayed-Payment Review Screen",
        is_active=True, verification_status="VERIFIED",
        legislative_act="IT_ACT_1961", provision_reference="Section 43B(h), Income-tax Act, 1961",
        suggested_action="Confirm MSME registration and agreed payment terms before concluding on disallowance.",
    ))
    session.commit()

    class _Env:
        svc = tax_review_service
        engagement_id = engagement.engagement_id
        new_act_engagement_id = new_act_engagement.engagement_id

    yield _Env
    extensions.SessionLocal.remove()


def test_preview_does_not_persist_anything(env):
    review = env.svc.preview_tax_review(env.engagement_id)
    assert len(review.rule_outcomes["TAX-MSME-013"].exceptions) == 1
    assert review.persisted_exception_count == 0
    assert env.svc.get_last_review_results(env.engagement_id) == []


def test_run_persists_exception_with_standard_reference_and_no_assertions(env):
    review = env.svc.run_tax_review(env.engagement_id)
    assert review.persisted_exception_count == 1
    assert review.preserved_exception_count == 0

    results = env.svc.get_last_review_results(env.engagement_id)
    assert len(results) == 1
    persisted = results[0]
    assert persisted.exception.rule_id == "TAX-MSME-013"
    assert persisted.exception.module == "TAX"
    assert persisted.exception.status == "OPEN"
    # standard_reference comes from TaxRule.provision_reference — the verified
    # old-Act citation only, never a New Act 2025 forward reference.
    assert persisted.exception.standard_reference == "Section 43B(h), Income-tax Act, 1961"
    assert persisted.query is not None
    assert persisted.query.category == "TAX"
    assert persisted.query.is_ai_drafted is False


def test_finding_uses_the_msme_payment_review_label_not_a_confirmed_disallowance(env):
    from app.rules import wording

    review = env.svc.preview_tax_review(env.engagement_id)
    exceptions = review.rule_outcomes["TAX-MSME-013"].exceptions
    assert exceptions[0].label == wording.POTENTIAL_MSME_PAYMENT_REVIEW


def test_engagement_not_found_raises(env):
    from app.services.tax_review_service import EngagementNotFoundError
    with pytest.raises(EngagementNotFoundError):
        env.svc.preview_tax_review(999999)


def test_new_act_financial_year_raises_act_era_not_supported(env):
    from app.services.tax_review_service import ActEraNotSupportedError
    with pytest.raises(ActEraNotSupportedError):
        env.svc.preview_tax_review(env.new_act_engagement_id)
    with pytest.raises(ActEraNotSupportedError):
        env.svc.run_tax_review(env.new_act_engagement_id)


def test_old_act_financial_year_does_not_raise_act_era_error(env):
    # The defining Stage 10 precondition check: FY 2025-26 is squarely
    # within the Income-tax Act, 1961's scope, so no ActEraNotSupportedError.
    review = env.svc.preview_tax_review(env.engagement_id)
    assert review.rule_outcomes  # ran without raising


def test_rerunning_with_unchanged_data_does_not_pile_up_duplicates(env):
    env.svc.run_tax_review(env.engagement_id)
    env.svc.run_tax_review(env.engagement_id)
    env.svc.run_tax_review(env.engagement_id)
    assert len(env.svc.get_last_review_results(env.engagement_id)) == 1


def test_reviewer_touched_exception_is_preserved_across_a_rerun(env):
    from sqlalchemy import select

    from app import extensions
    from app.models.exceptions import ExceptionRecord

    env.svc.run_tax_review(env.engagement_id)
    first = env.svc.get_last_review_results(env.engagement_id)[0]
    original_exception_id = first.exception.exception_id

    stmt = select(ExceptionRecord).where(ExceptionRecord.exception_id == original_exception_id)
    row = extensions.SessionLocal.scalars(stmt).first()
    row.status = "UNDER_REVIEW"
    extensions.SessionLocal.commit()

    review = env.svc.run_tax_review(env.engagement_id)
    assert review.preserved_exception_count == 1
    assert review.persisted_exception_count == 0

    results = env.svc.get_last_review_results(env.engagement_id)
    assert len(results) == 1
    assert results[0].exception.exception_id == original_exception_id
    assert results[0].exception.status == "UNDER_REVIEW"


def test_get_tax_rules_by_id_returns_every_seeded_row(env):
    rules_by_id = env.svc.get_tax_rules_by_id()
    assert "TAX-MSME-013" in rules_by_id
    assert rules_by_id["TAX-MSME-013"].suggested_action == (
        "Confirm MSME registration and agreed payment terms before concluding on disallowance."
    )
