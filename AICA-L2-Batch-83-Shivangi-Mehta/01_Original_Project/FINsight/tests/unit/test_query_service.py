"""
Stage 13 — app/services/query_service.py: the Query & Working Papers
orchestration layer. Real (sandbox-shimmed) SQLite DB, a real Tax review
run (TAX-MSME-013) so the working paper under test is built from a
genuinely persisted ExceptionRecord/QueryRecord, exactly as
tests/unit/test_tax_review_service.py's own fixture does.

Uses only synthetic, fabricated data — never real client/financial
data, per the standing instruction.

Run with: pytest tests/unit/test_query_service.py -v
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

    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", future=True)
    Base.metadata.create_all(engine)
    extensions.engine = engine
    extensions.SessionLocal = scoped_session(sessionmaker(bind=engine, future=True, expire_on_commit=False))

    from app.models.rules import TaxRule
    from app.services import engagement_service, mapping_service, query_service, tax_review_service, upload_service

    engagement = engagement_service.create_engagement("Acme Manufacturing Ltd", "2025-26")

    buf = io.BytesIO()
    pd.DataFrame([
        {"Party Name": "Bright Traders", "Transaction Date": "01-06-2025", "Credit Amount": "50000", "Debit Amount": ""},
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

    review = tax_review_service.run_tax_review(engagement.engagement_id)
    assert review.persisted_exception_count == 1
    persisted = tax_review_service.get_last_review_results(engagement.engagement_id)[0]

    class _Env:
        svc = query_service
        tax_svc = tax_review_service
        engagement_id = engagement.engagement_id
        exception_id = persisted.exception.exception_id
        original_question_text = persisted.query.question_text
        original_description = persisted.exception.description

    yield _Env
    extensions.SessionLocal.remove()


# --- 1-3: Query Centre loads and links correctly -----------------------------

def test_query_centre_loads_existing_queries(env):
    items = env.svc.list_queries(env.engagement_id)
    assert len(items) == 1
    assert items[0].rule_id == "TAX-MSME-013"


def test_query_links_to_correct_finding(env):
    items = env.svc.list_queries(env.engagement_id)
    assert items[0].exception.exception_id == env.exception_id
    assert items[0].query.exception_id == env.exception_id


def test_tax_query_displayed_correctly(env):
    items = env.svc.list_queries(env.engagement_id)
    assert items[0].module == "TAX"
    assert items[0].exception.standard_reference == "Section 43B(h), Income-tax Act, 1961"


# --- 6-7: filters, search ------------------------------------------------------

def test_query_filters_work(env):
    assert len(env.svc.list_queries(env.engagement_id, module="TAX")) == 1
    assert len(env.svc.list_queries(env.engagement_id, module="ACCOUNTING")) == 0
    assert len(env.svc.list_queries(env.engagement_id, rule_id="TAX-MSME-013")) == 1
    assert len(env.svc.list_queries(env.engagement_id, rule_id="NOPE")) == 0
    assert len(env.svc.list_queries(env.engagement_id, status="OPEN")) == 1
    assert len(env.svc.list_queries(env.engagement_id, status="RESOLVED")) == 0


def test_query_search_works(env):
    assert len(env.svc.list_queries(env.engagement_id, search="TAX-MSME-013")) == 1
    assert len(env.svc.list_queries(env.engagement_id, search="MSME")) == 1
    assert len(env.svc.list_queries(env.engagement_id, search=str(env.exception_id))) == 1
    assert len(env.svc.list_queries(env.engagement_id, search="no-such-text")) == 0


# --- 8-13: Working Paper reviewer actions -------------------------------------

def test_reviewer_can_open_a_working_paper(env):
    wp = env.svc.get_working_paper(env.exception_id)
    assert wp is not None
    assert wp.exception.exception_id == env.exception_id
    assert wp.query is not None
    assert wp.finding is not None
    assert wp.finding.rule_id == "TAX-MSME-013"


def test_reviewer_can_add_notes(env):
    wp = env.svc.update_working_paper(env.exception_id, reviewer_notes="Following up with the client.")
    assert wp.exception.reviewer_notes == "Following up with the client."


def test_reviewer_can_record_response(env):
    wp = env.svc.update_working_paper(env.exception_id, management_response="Vendor confirmed not MSME-registered.")
    assert wp.response is not None
    assert wp.response.management_response == "Vendor confirmed not MSME-registered."


def test_reviewer_can_record_evidence_reference(env):
    wp = env.svc.update_working_paper(
        env.exception_id, evidence_description="Vendor declaration letter",
        evidence_reference="/local/evidence/vendor_decl.pdf",
    )
    assert wp.response.evidence_description == "Vendor declaration letter"
    assert wp.response.evidence_reference == "/local/evidence/vendor_decl.pdf"


def test_reviewer_can_record_conclusion_and_change_status(env):
    wp = env.svc.update_working_paper(env.exception_id, status="REVIEWED_NO_ISSUE", status_reason="Vendor is not MSME-registered.")
    assert wp.exception.status == "REVIEWED_NO_ISSUE"
    assert wp.exception.status_reason == "Vendor is not MSME-registered."
    assert env.svc.CONCLUSION_LABELS[wp.exception.status] == "Cleared"


def test_original_automated_finding_remains_unchanged(env):
    env.svc.update_working_paper(
        env.exception_id, reviewer_notes="x", reviewer_query_text="edited",
        management_response="y", status="UNDER_REVIEW",
    )
    wp = env.svc.get_working_paper(env.exception_id)
    assert wp.exception.description == env.original_description
    assert wp.exception.trigger_condition is not None


def test_reviewer_edited_query_is_preserved_separately_from_original(env):
    wp = env.svc.update_working_paper(env.exception_id, reviewer_query_text="Please also confirm the payment date.")
    assert wp.query.question_text == env.original_question_text  # untouched
    assert wp.query.reviewer_query_text == "Please also confirm the payment date."


# --- 7-8 (status_reason enforcement) ------------------------------------------

def test_reviewed_no_issue_cannot_be_saved_without_status_reason(env):
    with pytest.raises(env.svc.StatusReasonRequiredError):
        env.svc.update_working_paper(env.exception_id, status="REVIEWED_NO_ISSUE")
    # nothing was saved
    assert env.svc.get_working_paper(env.exception_id).exception.status == "OPEN"


def test_not_applicable_cannot_be_saved_without_status_reason(env):
    with pytest.raises(env.svc.StatusReasonRequiredError):
        env.svc.update_working_paper(env.exception_id, status="NOT_APPLICABLE")
    assert env.svc.get_working_paper(env.exception_id).exception.status == "OPEN"


def test_resolved_can_be_saved_without_special_handling(env):
    wp = env.svc.update_working_paper(env.exception_id, status="RESOLVED")
    assert wp.exception.status == "RESOLVED"
    assert wp.exception.resolved_at is not None


def test_invalid_status_value_is_rejected(env):
    with pytest.raises(env.svc.InvalidStatusError):
        env.svc.update_working_paper(env.exception_id, status="NOT_A_REAL_STATUS")


# --- 10: QueryRecord.status stays independent ---------------------------------

def test_query_record_status_remains_independent_of_exception_status(env):
    wp = env.svc.update_working_paper(env.exception_id, status="RESOLVED")
    assert wp.exception.status == "RESOLVED"
    assert wp.query.status == "OPEN"  # untouched, per your explicit instruction


# --- 11: AuditLog -------------------------------------------------------------

def test_audit_log_records_reviewer_changes(env):
    env.svc.update_working_paper(env.exception_id, reviewer_query_text="edited query")
    # First-ever response+evidence write in the same call -> both ADDED.
    env.svc.update_working_paper(env.exception_id, management_response="response text",
                                  evidence_description="desc", evidence_reference="ref.pdf")
    # A later, separate evidence edit on the same (now-existing) response -> UPDATED.
    env.svc.update_working_paper(env.exception_id, evidence_reference="ref-v2.pdf")
    env.svc.update_working_paper(env.exception_id, reviewer_notes="notes")
    env.svc.update_working_paper(env.exception_id, status="UNDER_REVIEW")

    trail = env.svc.get_audit_trail(env.exception_id)
    actions = [a.action for a in trail]
    assert "QUERY_TEXT_EDITED" in actions
    assert "RESPONSE_ADDED" in actions
    assert "EVIDENCE_ADDED" in actions
    assert "EVIDENCE_UPDATED" in actions
    assert "REVIEWER_NOTES_CHANGED" in actions
    assert "STATUS_CHANGED" in actions
    for entry in trail:
        assert entry.entity_affected == f"exceptions.{env.exception_id}"
        assert entry.engagement_id == env.engagement_id


def test_audit_log_does_not_record_a_no_op_save(env):
    env.svc.update_working_paper(env.exception_id, reviewer_notes="first note")
    before = len(env.svc.get_audit_trail(env.exception_id))
    # Same value submitted again -> no new audit entry.
    env.svc.update_working_paper(env.exception_id, reviewer_notes="first note")
    after = len(env.svc.get_audit_trail(env.exception_id))
    assert after == before


# --- 12: re-run preservation ---------------------------------------------------

def test_rerunning_review_does_not_erase_reviewer_work(env):
    env.svc.update_working_paper(
        env.exception_id, reviewer_query_text="edited", management_response="response",
        evidence_description="desc", evidence_reference="ref.pdf", reviewer_notes="notes",
        status="REVIEWED_NO_ISSUE", status_reason="Cleared after review.",
    )
    env.tax_svc.run_tax_review(env.engagement_id)  # re-run

    wp = env.svc.get_working_paper(env.exception_id)
    assert wp.exception.status == "REVIEWED_NO_ISSUE"
    assert wp.exception.status_reason == "Cleared after review."
    assert wp.exception.reviewer_notes == "notes"
    assert wp.query.reviewer_query_text == "edited"
    assert wp.query.question_text == env.original_question_text
    assert wp.response.management_response == "response"
    assert wp.response.evidence_description == "desc"
    assert wp.response.evidence_reference == "ref.pdf"


# --- 13: original finding still unchanged after everything --------------------

def test_original_finding_remains_unchanged_after_full_workflow(env):
    env.svc.update_working_paper(
        env.exception_id, reviewer_query_text="edited", management_response="response",
        status="RESOLVED",
    )
    wp = env.svc.get_working_paper(env.exception_id)
    assert wp.exception.description == env.original_description
    assert wp.query.question_text == env.original_question_text


# --- 16: no duplicate QueryRecord ----------------------------------------------

def test_no_duplicate_query_record_is_created_by_working_paper_edits(env):
    from sqlalchemy import select

    from app import extensions
    from app.models.queries import QueryRecord

    env.svc.update_working_paper(env.exception_id, reviewer_query_text="a")
    env.svc.update_working_paper(env.exception_id, management_response="b")
    env.svc.update_working_paper(env.exception_id, evidence_description="c")

    stmt = select(QueryRecord).where(QueryRecord.exception_id == env.exception_id)
    count = len(list(extensions.SessionLocal.scalars(stmt).all()))
    assert count == 1


def test_evidence_upsert_does_not_create_a_second_response_row(env):
    from sqlalchemy import select

    from app import extensions
    from app.models.queries import QueryResponse

    wp1 = env.svc.update_working_paper(env.exception_id, management_response="first")
    wp2 = env.svc.update_working_paper(env.exception_id, management_response="second", evidence_description="d")

    stmt = select(QueryResponse).where(QueryResponse.query_id == wp1.query.query_id)
    count = len(list(extensions.SessionLocal.scalars(stmt).all()))
    assert count == 1
    assert wp2.response.management_response == "second"


# --- misc ----------------------------------------------------------------------

def test_working_paper_not_found_returns_none(env):
    assert env.svc.get_working_paper(999999) is None


# --- Stage 13 migration backward-compatibility tests --------------------------

def test_existing_query_with_null_reviewer_query_text_continues_to_work(env):
    # This engagement's query was created by tax_review_service (Stage
    # 10 code, unaware reviewer_query_text even exists) — exactly the
    # "pre-migration row" shape. Nothing about reading or filtering it
    # should break.
    wp = env.svc.get_working_paper(env.exception_id)
    assert wp.query.reviewer_query_text is None
    assert wp.query.question_text is not None
    items = env.svc.list_queries(env.engagement_id)
    assert items[0].effective_query_text == wp.query.question_text  # falls back correctly


def test_existing_query_response_with_null_evidence_fields_continues_to_work(env):
    wp = env.svc.update_working_paper(env.exception_id, management_response="Confirmed.")
    assert wp.response.evidence_description is None
    assert wp.response.evidence_reference is None
    # Reading it back via get_working_paper must not raise or misbehave.
    wp2 = env.svc.get_working_paper(env.exception_id)
    assert wp2.response.management_response == "Confirmed."
    assert wp2.response.evidence_description is None


def test_query_summary_reflects_actual_data_not_hardcoded(env):
    summary = env.svc.query_summary(env.engagement_id)
    assert summary["total"] == 1
    assert summary["by_module"]["TAX"] == 1
    assert summary["by_status"]["OPEN"] == 1

    env.svc.update_working_paper(env.exception_id, status="RESOLVED")
    summary = env.svc.query_summary(env.engagement_id)
    assert summary["by_status"]["OPEN"] == 0
    assert summary["by_status"]["RESOLVED"] == 1
