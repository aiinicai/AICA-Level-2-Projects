"""
Stage 12 — app/services/unified_review_service.py: the Unified Review
Engine orchestrator. Exercises the real preview/run cycle against a real
(sandbox-shimmed) SQLite DB and real uploaded+mapped+validated files
across all three approved engines at once, so the orchestrator's "call
the existing engine unchanged" claim is actually verified rather than
mocked.

One engagement is seeded with enough synthetic data to trigger a finding
in each of the three modules simultaneously:
  - JE file #1 ("Prior period adjustment...") -> AS5-PPI-012 (Accounting)
  - JE file #2 (a manual entry dated a Saturday) -> AUD-JE-002 (Audit)
  - AP file (an old MSME-eligible payable) -> TAX-MSME-013 (Tax)
Multiple JE-type files are legitimate — dataset_service.load_engagement_
dataset() concatenates every VALIDATED file of the same file_type, the
same behavior every individual engine's own test suite already relies on.

Uses only synthetic, fabricated data — never real client/financial data,
per the standing instruction.

Run with: pytest tests/unit/test_unified_review_service.py -v
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

    from app.models.rules import AccountingRule, AuditAssertion, AuditRule, AuditRuleAssertion, Standard, TaxRule
    from app.services import (
        engagement_service, mapping_service, unified_review_service, upload_service,
    )

    engagement = engagement_service.create_engagement("Acme Manufacturing Ltd", "2025-26")
    engagement_service.save_entity_profile(engagement.engagement_id, {
        "entity_type": "Company", "industry": None, "is_listed": False,
        "accounting_framework": "AS", "is_gst_registered": False,
        "statutory_audit_applicable": False, "tax_audit_status": "REQUIRES_REVIEW",
        "consolidated_fs_applicable": False, "prior_year_data_available": False,
        "turnover": None, "overall_materiality": None, "performance_materiality": None,
        "clearly_trivial_threshold": None,
    })

    # New-Act engagement (FY 2026-27) — no Entity Profile, no data — used
    # only by the Tax-precondition / error-isolation tests below.
    new_act_engagement = engagement_service.create_engagement("Acme Manufacturing Ltd", "2026-27")

    def _upload_mapped_validated(file_type, filename, rows, mapping):
        buf = io.BytesIO()
        pd.DataFrame(rows).to_csv(buf, index=False)
        uploaded = upload_service.save_uploaded_file(
            engagement_id=engagement.engagement_id, original_filename=filename, file_type=file_type,
            file_bytes=buf.getvalue(), input_dir=tmp_path / "data_input",
        )
        mapping_service.confirm_mappings(uploaded.file_id, mapping)
        mapping_service.mark_file_status(uploaded.file_id, "VALIDATED")
        return uploaded

    # JE #1 -> triggers AS5-PPI-012 (Accounting)
    _upload_mapped_validated("JE", "je_ppi.csv", [
        {"Description": "Prior period adjustment for FY24-25 expense", "Debit": 30000, "Credit": 0},
        {"Description": "Routine sale of goods", "Debit": 0, "Credit": 50000},
    ], [
        {"source_column": "Description", "target_field": "description", "confidence_score": 1.0},
        {"source_column": "Debit", "target_field": "debit_amount", "confidence_score": 1.0},
        {"source_column": "Credit", "target_field": "credit_amount", "confidence_score": 1.0},
    ])

    # JE #2 -> triggers AUD-JE-002 (Audit)
    _upload_mapped_validated("JE", "je_weekend.csv", [
        {"Is Manual Entry": "Yes", "Transaction Date": "2026-03-28", "Description": "Adjustment entry"},
        {"Is Manual Entry": "No", "Transaction Date": "2026-03-30", "Description": "Routine entry"},
    ], [
        {"source_column": "Is Manual Entry", "target_field": "is_manual_entry", "confidence_score": 1.0},
        {"source_column": "Transaction Date", "target_field": "transaction_date", "confidence_score": 1.0},
        {"source_column": "Description", "target_field": "description", "confidence_score": 1.0},
    ])

    # AP -> triggers TAX-MSME-013 (Tax)
    _upload_mapped_validated("AP", "ap.csv", [
        {"Party Name": "Bright Traders", "Transaction Date": "01-06-2025", "Credit Amount": "50000", "Debit Amount": ""},
    ], [
        {"source_column": "Party Name", "target_field": "party_name", "confidence_score": 1.0},
        {"source_column": "Transaction Date", "target_field": "transaction_date", "confidence_score": 1.0},
        {"source_column": "Credit Amount", "target_field": "credit_amount", "confidence_score": 1.0},
        {"source_column": "Debit Amount", "target_field": "debit_amount", "confidence_score": 1.0},
    ])

    session = extensions.SessionLocal

    as_standard = Standard(framework="AS", code="AS 5", title="Net Profit or Loss for the Period, Prior Period Items and Changes in Accounting Policies")
    session.add(as_standard)
    session.commit()
    session.add(AccountingRule(
        rule_id="AS5-PPI-012", standard_id=as_standard.standard_id, framework="AS",
        topic="Prior Period Items / Errors — Narration Keyword Check", is_active=True, verification_status="VERIFIED",
        suggested_action="Confirm classification of this entry with the reviewer.",
    ))

    sa_standard = Standard(framework="SA", code="SA 240", title="The Auditor's Responsibilities Relating to Fraud")
    session.add(sa_standard)
    session.commit()
    session.add(AuditRule(
        rule_id="AUD-JE-002", standard_id=sa_standard.standard_id, topic="Manual Journal Entry Posted on a Non-Business Day",
        is_active=True, verification_status="VERIFIED", related_sa="SA 240", audit_area="Journal Entry Testing",
        suggested_audit_procedure="Consider whether a brief inquiry is warranted.",
        suggested_evidence="Journal voucher, explanation for the posting date.",
    ))
    occurrence = AuditAssertion(code="OCCURRENCE", label="Occurrence")
    session.add(occurrence)
    session.commit()
    session.add(AuditRuleAssertion(rule_id="AUD-JE-002", assertion_id=occurrence.assertion_id))

    session.add(TaxRule(
        rule_id="TAX-MSME-013", topic="MSME Delayed-Payment Review Screen",
        is_active=True, verification_status="VERIFIED",
        legislative_act="IT_ACT_1961", provision_reference="Section 43B(h), Income-tax Act, 1961",
        suggested_action="Confirm MSME registration and agreed payment terms before concluding on disallowance.",
    ))
    session.commit()

    class _Env:
        svc = unified_review_service
        engagement_id = engagement.engagement_id
        new_act_engagement_id = new_act_engagement.engagement_id

    yield _Env
    extensions.SessionLocal.remove()


# --- 1-4: per-module selection -----------------------------------------------

def test_accounting_only_review_runs_only_accounting(env):
    summary = env.svc.run_unified_review(env.engagement_id, ("ACCOUNTING",))
    assert summary.executed
    assert [o.module for o in summary.module_outcomes] == ["ACCOUNTING"]
    assert summary.module_outcomes[0].status == "COMPLETED"
    assert summary.total_persisted_exceptions == 1


def test_audit_only_review_runs_only_audit(env):
    summary = env.svc.run_unified_review(env.engagement_id, ("AUDIT",))
    assert [o.module for o in summary.module_outcomes] == ["AUDIT"]
    assert summary.module_outcomes[0].status == "COMPLETED"
    assert summary.total_persisted_exceptions == 1


def test_tax_only_review_runs_only_tax(env):
    summary = env.svc.run_unified_review(env.engagement_id, ("TAX",))
    assert [o.module for o in summary.module_outcomes] == ["TAX"]
    assert summary.module_outcomes[0].status == "COMPLETED"
    assert summary.total_persisted_exceptions == 1


def test_all_three_modules_run_together_and_all_default_selected(env):
    summary = env.svc.run_unified_review(env.engagement_id)  # modules=None -> all three, default behavior
    assert [o.module for o in summary.module_outcomes] == list(env.svc.MODULES)
    assert all(o.status == "COMPLETED" for o in summary.module_outcomes)
    assert summary.total_persisted_exceptions == 3
    assert summary.all_completed


# --- 5-6: readiness gate -----------------------------------------------------

def test_review_blocked_when_no_files_uploaded_at_all(env):
    from app.services import engagement_service
    bare_engagement = engagement_service.create_engagement("Bare Co", "2025-26")
    summary = env.svc.run_unified_review(bare_engagement.engagement_id)
    assert summary.executed is False
    assert summary.blocked_reason == env.svc.BLOCKED_MESSAGE
    assert summary.module_outcomes == []


def test_review_blocked_when_a_file_is_uploaded_but_not_yet_validated(env):
    from app.services import engagement_service, upload_service

    partial = engagement_service.create_engagement("Partial Co", "2025-26")
    buf = io.BytesIO()
    pd.DataFrame([{"Description": "x", "Debit": 1, "Credit": 0}]).to_csv(buf, index=False)
    upload_service.save_uploaded_file(
        engagement_id=partial.engagement_id, original_filename="je.csv", file_type="JE",
        file_bytes=buf.getvalue(), input_dir=Path("/tmp") / "unified_review_test_input",
    )
    # Deliberately not mapped or validated — upload_status stays UPLOADED.
    readiness = env.svc.check_review_readiness(partial.engagement_id)
    assert readiness.ready is False
    assert readiness.reason == env.svc.BLOCKED_MESSAGE

    summary = env.svc.run_unified_review(partial.engagement_id)
    assert summary.executed is False
    assert summary.blocked_reason == env.svc.BLOCKED_MESSAGE


def test_review_ready_once_every_uploaded_file_is_validated(env):
    readiness = env.svc.check_review_readiness(env.engagement_id)
    assert readiness.ready is True
    assert readiness.reason is None
    assert len(readiness.uploads) == 3


# --- 7-8: reused (not duplicated) applicability logic ------------------------

def test_accounting_framework_selection_is_reused_from_the_existing_engine(env):
    summary = env.svc.run_unified_review(env.engagement_id, ("ACCOUNTING",))
    outcome = summary.module_outcomes[0]
    assert outcome.result.framework == "AS"  # came straight from accounting_review_service, not recomputed here


def test_tax_act_era_precondition_is_reused_and_reported_as_blocked_not_failed(env):
    summary = env.svc.run_unified_review(env.new_act_engagement_id, ("ACCOUNTING", "AUDIT", "TAX"))
    # No uploads at all for the new-act engagement -> the readiness gate
    # fires first, before any per-module precondition is even reached.
    assert summary.executed is False
    assert summary.blocked_reason == env.svc.BLOCKED_MESSAGE


def test_tax_act_era_precondition_reported_per_module_when_data_is_ready(env, tmp_path):
    # Give the new-act engagement a trivially VALIDATED file so the
    # readiness gate passes and the per-module Act-era precondition
    # (raised deep inside tax_review_service, not reimplemented here) is
    # what actually gets exercised.
    from app.services import mapping_service, upload_service

    buf = io.BytesIO()
    pd.DataFrame([{"Description": "Routine entry", "Debit": 1, "Credit": 0}]).to_csv(buf, index=False)
    uploaded = upload_service.save_uploaded_file(
        engagement_id=env.new_act_engagement_id, original_filename="je.csv", file_type="JE",
        file_bytes=buf.getvalue(), input_dir=tmp_path / "data_input",
    )
    mapping_service.confirm_mappings(uploaded.file_id, [
        {"source_column": "Description", "target_field": "description", "confidence_score": 1.0},
    ])
    mapping_service.mark_file_status(uploaded.file_id, "VALIDATED")

    summary = env.svc.run_unified_review(env.new_act_engagement_id, ("TAX",))
    assert summary.executed is True
    assert summary.module_outcomes[0].module == "TAX"
    assert summary.module_outcomes[0].status == "BLOCKED"
    assert "Income-tax Act, 2025" in summary.module_outcomes[0].error_message


# --- 9-12: preview vs run, re-run preservation -------------------------------

def test_preview_does_not_persist_anything(env):
    summary = env.svc.preview_unified_review(env.engagement_id)
    assert summary.persisted is False
    assert all(o.result.persisted_exception_count == 0 for o in summary.module_outcomes)
    assert env.svc.get_unified_findings(env.engagement_id) == []


def test_run_persists_across_all_three_modules(env):
    summary = env.svc.run_unified_review(env.engagement_id)
    assert summary.persisted is True
    findings = env.svc.get_unified_findings(env.engagement_id)
    assert len(findings) == 3
    assert {f.module for f in findings} == {"ACCOUNTING", "AUDIT", "TAX"}


def test_rerunning_with_unchanged_data_does_not_pile_up_duplicates(env):
    env.svc.run_unified_review(env.engagement_id)
    env.svc.run_unified_review(env.engagement_id)
    env.svc.run_unified_review(env.engagement_id)
    assert len(env.svc.get_unified_findings(env.engagement_id)) == 3


def test_reviewer_touched_finding_is_preserved_across_a_unified_rerun(env):
    from sqlalchemy import select

    from app import extensions
    from app.models.exceptions import ExceptionRecord

    env.svc.run_unified_review(env.engagement_id)
    tax_finding = next(f for f in env.svc.get_unified_findings(env.engagement_id) if f.module == "TAX")

    stmt = select(ExceptionRecord).where(ExceptionRecord.exception_id == tax_finding.finding_id)
    row = extensions.SessionLocal.scalars(stmt).first()
    row.status = "UNDER_REVIEW"
    extensions.SessionLocal.commit()

    summary = env.svc.run_unified_review(env.engagement_id)
    tax_outcome = next(o for o in summary.module_outcomes if o.module == "TAX")
    assert tax_outcome.result.preserved_exception_count == 1
    assert tax_outcome.result.persisted_exception_count == 0

    findings = env.svc.get_unified_findings(env.engagement_id)
    tax_findings = [f for f in findings if f.module == "TAX"]
    assert len(tax_findings) == 1
    assert tax_findings[0].status == "UNDER_REVIEW"


# --- 13: error isolation -----------------------------------------------------

def test_one_module_failing_unexpectedly_does_not_prevent_the_others_from_running(env, monkeypatch):
    def _boom(_engagement_id):
        raise RuntimeError("simulated unexpected failure inside the audit engine")

    monkeypatch.setitem(env.svc._RUN_FN, "AUDIT", _boom)

    summary = env.svc.run_unified_review(env.engagement_id)
    by_module = {o.module: o for o in summary.module_outcomes}
    assert by_module["AUDIT"].status == "FAILED"
    assert "simulated unexpected failure" in by_module["AUDIT"].error_message
    assert by_module["ACCOUNTING"].status == "COMPLETED"
    assert by_module["TAX"].status == "COMPLETED"
    assert summary.any_failed is True
    assert summary.all_completed is False

    # Accounting and Tax findings were still saved despite Audit's failure.
    findings = env.svc.get_unified_findings(env.engagement_id)
    assert {f.module for f in findings} == {"ACCOUNTING", "TAX"}


# --- 14-15: normalization, module-specific fields ----------------------------

def test_unified_finding_displays_the_correct_module_and_title(env):
    env.svc.run_unified_review(env.engagement_id)
    findings = {f.module: f for f in env.svc.get_unified_findings(env.engagement_id)}
    assert findings["ACCOUNTING"].title == "Prior Period Items / Errors — Narration Keyword Check"
    assert findings["AUDIT"].title == "Manual Journal Entry Posted on a Non-Business Day"
    assert findings["TAX"].title == "MSME Delayed-Payment Review Screen"


def test_module_specific_fields_are_preserved_not_flattened_away(env):
    env.svc.run_unified_review(env.engagement_id)
    findings = {f.module: f for f in env.svc.get_unified_findings(env.engagement_id)}

    acc = findings["ACCOUNTING"]
    assert acc.module_fields["framework"] == "AS"
    assert acc.module_fields["standard_code"] == "AS 5"
    assert acc.suggested_evidence is None  # Accounting's catalogue has no such column — never invented

    audit = findings["AUDIT"]
    assert audit.module_fields["audit_area"] == "Journal Entry Testing"
    assert audit.module_fields["assertions"] == ["OCCURRENCE"]
    assert audit.suggested_evidence == "Journal voucher, explanation for the posting date."

    tax = findings["TAX"]
    assert tax.module_fields["legislative_act"] == "IT_ACT_1961"
    assert tax.reference == "Section 43B(h), Income-tax Act, 1961"


# --- 16: Insufficient Data stays distinct, never persisted -------------------

def test_insufficient_data_outcome_is_never_persisted_as_a_finding(env):
    # TAX-CASH-001 is not seeded in this fixture at all, so it never
    # contributes a rule_outcome either way; what this test actually
    # confirms is the structural guarantee every engine already provides
    # (Insufficient Data is a RuleOutcome-only concept) by checking that
    # every module ran and every persisted finding has a real ExceptionRecord
    # status - never something like "INSUFFICIENT_DATA" leaking into it.
    env.svc.run_unified_review(env.engagement_id)
    findings = env.svc.get_unified_findings(env.engagement_id)
    assert all(f.status in ("OPEN", "UNDER_REVIEW", "QUERY_RAISED", "RESPONSE_RECEIVED",
                             "RESOLVED", "REVIEWED_NO_ISSUE", "NOT_APPLICABLE", "CLOSED") for f in findings)


# --- 17: queries linked, never duplicated ------------------------------------

def test_queries_are_linked_once_per_finding_even_after_repeated_runs(env):
    from sqlalchemy import select

    from app import extensions
    from app.models.queries import QueryRecord

    env.svc.run_unified_review(env.engagement_id)
    env.svc.run_unified_review(env.engagement_id)

    findings = env.svc.get_unified_findings(env.engagement_id)
    for f in findings:
        assert f.suggested_query is not None
        q_count = len(list(extensions.SessionLocal.scalars(
            select(QueryRecord).where(QueryRecord.exception_id == f.finding_id)
        ).all()))
        assert q_count == 1


# --- 18: no SEBI, ever -------------------------------------------------------

def test_sebi_is_never_a_selectable_module(env):
    assert "SEBI" not in env.svc.MODULES
    assert env.svc.MODULES == ("ACCOUNTING", "AUDIT", "TAX")
    assert env.svc._normalize_modules(["SEBI", "TAX"]) == ("TAX",)
    assert env.svc._normalize_modules(["SEBI"]) == ()


def test_posting_only_sebi_runs_nothing_and_is_reported_as_no_modules_selected(env):
    summary = env.svc.run_unified_review(env.engagement_id, ("SEBI",))
    assert summary.executed is False
    assert summary.blocked_reason == "No review modules were selected."


# --- grouping / dashboard summary --------------------------------------------

def test_related_transaction_id_is_set_for_single_row_findings_only(env):
    """Stage 19: AS5-PPI-012 and AUD-JE-002 are both single-row findings
    (a specific JE row's narration / a specific JE row's weekend date)
    and now set `related_transaction_id` via `dataset_service.
    attach_transaction_ids()`. TAX-MSME-013 is an aggregate finding (a
    net AP balance across possibly many rows, aged off the party's last
    movement) and deliberately never sets it — see tax_msme_013.py's
    own classification. `group_findings_by_transaction()` still returns
    an empty grouping here since no two findings in this fixture share
    the same transaction_id, not because nothing is ever populated
    (that assumption is what this test replaces)."""
    env.svc.run_unified_review(env.engagement_id)
    findings = env.svc.get_unified_findings(env.engagement_id)
    by_rule = {f.rule_id: f for f in findings}

    assert by_rule["AS5-PPI-012"].related_transaction_id is not None
    assert by_rule["AUD-JE-002"].related_transaction_id is not None
    assert by_rule["TAX-MSME-013"].related_transaction_id is None

    # Each single-row finding's transaction really is the row it was
    # raised about, not an arbitrary/incorrect one.
    from app import extensions
    from app.models.transactions import Transaction
    session = extensions.SessionLocal
    ppi_txn = session.get(Transaction, by_rule["AS5-PPI-012"].related_transaction_id)
    assert "prior period" in (ppi_txn.description or "").lower()
    je2_txn = session.get(Transaction, by_rule["AUD-JE-002"].related_transaction_id)
    assert je2_txn.transaction_date == "2026-03-28"

    assert env.svc.group_findings_by_transaction(findings) == {}


def test_unified_dashboard_summary_counts_match_findings(env):
    env.svc.run_unified_review(env.engagement_id)
    summary = env.svc.unified_dashboard_summary(env.engagement_id)
    assert summary["total_findings"] == 3
    assert summary["per_module"] == {"ACCOUNTING": 1, "AUDIT": 1, "TAX": 1}


# --- finding lookup / detail --------------------------------------------------

def test_get_finding_returns_none_for_an_unknown_id(env):
    env.svc.run_unified_review(env.engagement_id)
    assert env.svc.get_finding(env.engagement_id, "TAX", 999999) is None


def test_get_finding_returns_the_matching_normalized_finding(env):
    env.svc.run_unified_review(env.engagement_id)
    tax_finding = next(f for f in env.svc.get_unified_findings(env.engagement_id) if f.module == "TAX")
    looked_up = env.svc.get_finding(env.engagement_id, "TAX", tax_finding.finding_id)
    assert looked_up is not None
    assert looked_up.rule_id == "TAX-MSME-013"


def test_engagement_not_found_raises(env):
    with pytest.raises(env.svc.EngagementNotFoundError):
        env.svc.run_unified_review(999999)
    with pytest.raises(env.svc.EngagementNotFoundError):
        env.svc.preview_unified_review(999999)
