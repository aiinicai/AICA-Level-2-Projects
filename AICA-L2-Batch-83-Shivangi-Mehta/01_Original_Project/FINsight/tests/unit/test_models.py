"""
Stage 3 model tests — schema/model correctness only, no business logic
(nothing here exercises an accounting/audit/tax/SEBI rule, per condition
#5). Run with an in-memory SQLite DB created fresh per test via
Base.metadata.create_all().

NOTE ON THIS SANDBOX: these tests require SQLAlchemy, which could not be
installed here (see Stage 3 delivery notes — pip and apt were both
confirmed network-blocked, not merely assumed unavailable). They are
written to run normally with `pytest` once dependencies are installed
per requirements.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from sqlalchemy.exc import IntegrityError

from app.models import (
    Base,
    Engagement, EntityProfile, Applicability,
    UploadedFile, DataMapping,
    Standard, AccountingRule, AuditRule, TaxRule, SebiRule,
    AuditAssertion, AuditRuleAssertion,
    Transaction,
    FixedAsset, GstLineItem, TdsLineItem,
    ExceptionRecord,
    RiskScore,
    QueryRecord, QueryResponse,
    Document,
    AuditLog, ApplicationSetting, KnowledgeBaseVersion,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_conn, _):
        # SQLite does not enforce FKs unless explicitly told to — this
        # is enforcement of the schema already approved, not a new one.
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_all_24_tables_created(session):
    inspector_tables = set(Base.metadata.tables.keys())
    expected = {
        "engagements", "entity_profiles", "applicability",
        "uploaded_files", "data_mappings",
        "standards", "accounting_rules", "audit_rules", "tax_rules", "sebi_rules",
        "audit_assertions", "audit_rule_assertions",
        "transactions", "fixed_assets", "gst_line_items", "tds_line_items",
        "exceptions", "risk_scores",
        "queries", "query_responses",
        "documents",
        "audit_log", "application_settings", "knowledge_base_versions",
    }
    assert expected == inspector_tables
    assert len(expected) == 24


def test_engagement_entity_profile_round_trip(session):
    eng = Engagement(
        entity_name="Test Pvt Ltd", financial_year="2025-26", status="DRAFT",
        created_at="2026-08-21T00:00:00", updated_at="2026-08-21T00:00:00",
    )
    session.add(eng)
    session.flush()

    profile = EntityProfile(
        engagement_id=eng.engagement_id,
        entity_type="Company",
        is_listed=False,
        accounting_framework="IND_AS",
        turnover=1_50_00_000_00,  # paise: 1.5 crore
        overall_materiality=5_00_000_00,  # paise: 5 lakh
    )
    session.add(profile)
    session.commit()

    fetched = session.get(EntityProfile, profile.profile_id)
    assert fetched.accounting_framework == "IND_AS"
    assert isinstance(fetched.turnover, int)  # paise stored as INTEGER, not float
    assert fetched.turnover == 150000000


def test_applicability_system_vs_user_confirmation_split(session):
    eng = Engagement(
        entity_name="X", financial_year="2025-26", status="DRAFT",
        created_at="t", updated_at="t",
    )
    session.add(eng)
    session.flush()

    row = Applicability(
        engagement_id=eng.engagement_id,
        area="SEBI/LODR",
        system_suggested_status="REVIEW_REQUIRED",
        system_suggested_reason="Listed flag not yet set",
        user_confirmed_status=None,
    )
    session.add(row)
    session.commit()

    fetched = session.query(Applicability).filter_by(area="SEBI/LODR").one()
    assert fetched.system_suggested_status == "REVIEW_REQUIRED"
    assert fetched.user_confirmed_status is None  # system suggestion never auto-promoted


def test_accounting_rule_defaults_and_no_content_seeded(session):
    # Schema exists; zero rows — rule content is Stage 8, not Stage 3.
    assert session.query(AccountingRule).count() == 0
    assert session.query(AuditRule).count() == 0
    assert session.query(TaxRule).count() == 0
    assert session.query(SebiRule).count() == 0


def test_tax_and_sebi_rules_default_to_source_verification_required(session):
    rule = TaxRule(rule_id="TAX-CASH-001", topic="Cash Payments")
    session.add(rule)
    session.commit()
    fetched = session.get(TaxRule, "TAX-CASH-001")
    assert fetched.verification_status == "SOURCE_VERIFICATION_REQUIRED"

    sebi_rule = SebiRule(rule_id="SEBI-FR-001", topic="Financial Results Consistency")
    session.add(sebi_rule)
    session.commit()
    fetched_sebi = session.get(SebiRule, "SEBI-FR-001")
    assert fetched_sebi.verification_status == "SOURCE_VERIFICATION_REQUIRED"


def test_accounting_and_audit_rules_default_to_verified(session):
    rule = AccountingRule(rule_id="AS10-FA-001", framework="IND_AS", topic="Fixed Assets")
    session.add(rule)
    session.commit()
    assert session.get(AccountingRule, "AS10-FA-001").verification_status == "VERIFIED"

    audit_rule = AuditRule(rule_id="AUD-JE-001", topic="Journal Entry Testing")
    session.add(audit_rule)
    session.commit()
    assert session.get(AuditRule, "AUD-JE-001").verification_status == "VERIFIED"


def test_audit_rule_assertion_many_to_many(session):
    audit_rule = AuditRule(rule_id="AUD-WO-011", topic="Large Write-offs")
    session.add(audit_rule)

    valuation = AuditAssertion(code="VALUATION", label="Valuation")
    existence = AuditAssertion(code="EXISTENCE", label="Existence")
    session.add_all([valuation, existence])
    session.flush()

    session.add_all([
        AuditRuleAssertion(rule_id=audit_rule.rule_id, assertion_id=valuation.assertion_id),
        AuditRuleAssertion(rule_id=audit_rule.rule_id, assertion_id=existence.assertion_id),
    ])
    session.commit()

    links = session.query(AuditRuleAssertion).filter_by(rule_id="AUD-WO-011").all()
    codes = {link.assertion.code for link in links}
    assert codes == {"VALUATION", "EXISTENCE"}


def test_transaction_payment_mode_and_paise(session):
    eng = Engagement(entity_name="X", financial_year="2025-26", status="DRAFT", created_at="t", updated_at="t")
    session.add(eng)
    session.flush()

    txn = Transaction(
        engagement_id=eng.engagement_id,
        dataset_type="JE",
        debit_amount=45_00_000,  # paise: 45,000 rupees
        credit_amount=45_00_000,
        payment_mode="CASH",
        created_at="t",
    )
    session.add(txn)
    session.commit()

    fetched = session.get(Transaction, txn.transaction_id)
    assert fetched.payment_mode == "CASH"
    assert isinstance(fetched.debit_amount, int)


def test_exception_record_status_default_and_new_statuses_accepted(session):
    eng = Engagement(entity_name="X", financial_year="2025-26", status="DRAFT", created_at="t", updated_at="t")
    session.add(eng)
    session.flush()

    exc = ExceptionRecord(engagement_id=eng.engagement_id, module="AUDIT", created_at="t")
    session.add(exc)
    session.commit()
    assert session.get(ExceptionRecord, exc.exception_id).status == "OPEN"

    exc.status = "REVIEWED_NO_ISSUE"
    exc.status_reason = "Verified against supporting invoice; no exception."
    session.commit()
    fetched = session.get(ExceptionRecord, exc.exception_id)
    assert fetched.status == "REVIEWED_NO_ISSUE"
    assert fetched.status_reason is not None


def test_exception_record_class_does_not_shadow_builtin_exception():
    # Guards the Correction-flagged naming decision — this class must
    # never be importable as `Exception`.
    assert ExceptionRecord.__name__ != "Exception"
    assert issubclass(ExceptionRecord, Base)
    assert not issubclass(ExceptionRecord, BaseException)


def test_query_record_and_response_link(session):
    eng = Engagement(entity_name="X", financial_year="2025-26", status="DRAFT", created_at="t", updated_at="t")
    session.add(eng)
    session.flush()

    q = QueryRecord(engagement_id=eng.engagement_id, category="TAX", is_ai_drafted=False, created_at="t")
    session.add(q)
    session.flush()

    resp = QueryResponse(query_id=q.query_id, management_response="Confirmed cash payment split across two days.")
    session.add(resp)
    session.commit()

    assert session.get(QueryRecord, q.query_id).status == "OPEN"
    assert session.query(QueryResponse).filter_by(query_id=q.query_id).count() == 1


def test_fixed_asset_gst_tds_structured_tables_exist_and_link(session):
    eng = Engagement(entity_name="X", financial_year="2025-26", status="DRAFT", created_at="t", updated_at="t")
    session.add(eng)
    session.flush()

    fa = FixedAsset(engagement_id=eng.engagement_id, asset_class="CWIP", original_cost_paise=10_00_000_00)
    session.add(fa)

    txn = Transaction(engagement_id=eng.engagement_id, dataset_type="GST", created_at="t")
    session.add(txn)
    session.flush()

    gst = GstLineItem(
        transaction_id=txn.transaction_id, engagement_id=eng.engagement_id,
        invoice_number="INV-001", taxable_value_paise=1_00_000_00, source_dataset="SALES",
    )
    tds = TdsLineItem(
        transaction_id=txn.transaction_id, engagement_id=eng.engagement_id,
        section_code="194C", rate_applied=2.0, amount_deducted_paise=2_000_00,
    )
    session.add_all([gst, tds])
    session.commit()

    assert session.query(FixedAsset).filter_by(asset_class="CWIP").count() == 1
    assert session.query(GstLineItem).filter_by(invoice_number="INV-001").one().source_dataset == "SALES"
    assert session.query(TdsLineItem).filter_by(section_code="194C").one().rate_applied == 2.0


def test_application_settings_and_kb_version(session):
    session.add(ApplicationSetting(setting_key="ai_enabled", setting_value="false"))
    session.add(KnowledgeBaseVersion(version_label="0.2-schema-baseline", is_current=False))
    session.commit()

    assert session.get(ApplicationSetting, "ai_enabled").setting_value == "false"
    kb = session.query(KnowledgeBaseVersion).filter_by(version_label="0.2-schema-baseline").one()
    assert kb.is_current is False


def test_audit_log_records_independent_of_engagement(session):
    log = AuditLog(action="SCHEMA_CREATED", performed_by="stage3-init", timestamp="t")
    session.add(log)
    session.commit()
    assert session.get(AuditLog, log.log_id).engagement_id is None


# --- Stage 3 review round 2: new constraint tests -------------------------


def test_entity_profile_unique_per_engagement_enforced(session):
    eng = Engagement(entity_name="X", financial_year="2025-26", status="DRAFT", created_at="t", updated_at="t")
    session.add(eng)
    session.flush()

    session.add(EntityProfile(engagement_id=eng.engagement_id, entity_type="Company", accounting_framework="IND_AS"))
    session.commit()

    session.add(EntityProfile(engagement_id=eng.engagement_id, entity_type="Company", accounting_framework="AS"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_applicability_unique_per_engagement_and_area_enforced(session):
    eng = Engagement(entity_name="X", financial_year="2025-26", status="DRAFT", created_at="t", updated_at="t")
    session.add(eng)
    session.flush()

    session.add(Applicability(engagement_id=eng.engagement_id, area="SEBI/LODR", system_suggested_status="NO"))
    session.commit()

    session.add(Applicability(engagement_id=eng.engagement_id, area="SEBI/LODR", system_suggested_status="REVIEW_REQUIRED"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_uploaded_file_duplicate_checksum_within_engagement_rejected(session):
    eng = Engagement(entity_name="X", financial_year="2025-26", status="DRAFT", created_at="t", updated_at="t")
    session.add(eng)
    session.flush()

    session.add(UploadedFile(
        engagement_id=eng.engagement_id, file_type="GL", original_filename="gl.xlsx",
        stored_path="/data/input/1/gl.xlsx", uploaded_at="t", checksum="abc123",
    ))
    session.commit()

    session.add(UploadedFile(
        engagement_id=eng.engagement_id, file_type="GL", original_filename="gl_copy.xlsx",
        stored_path="/data/input/1/gl_copy.xlsx", uploaded_at="t", checksum="abc123",
    ))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_exceptions_no_longer_has_supporting_file_id():
    # Correction #3 — the circular FK was removed. Guard against it
    # silently reappearing.
    assert not hasattr(ExceptionRecord, "supporting_file_id")
    assert "supporting_file_id" not in ExceptionRecord.__table__.columns.keys()


def test_document_supports_many_documents_per_exception(session):
    eng = Engagement(entity_name="X", financial_year="2025-26", status="DRAFT", created_at="t", updated_at="t")
    session.add(eng)
    session.flush()

    exc = ExceptionRecord(engagement_id=eng.engagement_id, module="TAX", created_at="t")
    session.add(exc)
    session.flush()

    session.add_all([
        Document(engagement_id=eng.engagement_id, related_exception_id=exc.exception_id,
                  file_name="invoice_1.pdf", stored_path="/data/input/1/invoice_1.pdf", uploaded_at="t"),
        Document(engagement_id=eng.engagement_id, related_exception_id=exc.exception_id,
                  file_name="invoice_2.pdf", stored_path="/data/input/1/invoice_2.pdf", uploaded_at="t"),
        Document(engagement_id=eng.engagement_id, related_exception_id=exc.exception_id,
                  file_name="approval_email.pdf", stored_path="/data/input/1/approval_email.pdf", uploaded_at="t"),
    ])
    session.commit()

    docs = session.query(Document).filter_by(related_exception_id=exc.exception_id).all()
    assert len(docs) == 3  # one exception, many supporting documents — the intended workflow


def test_exception_rule_id_intentionally_nullable(session):
    # Flagged as an open decision in documentation/db_constraints.md,
    # not silently decided — this test documents the current (nullable)
    # behavior so a future change to NOT NULL is a visible, deliberate
    # test update, not a silent regression either way.
    eng = Engagement(entity_name="X", financial_year="2025-26", status="DRAFT", created_at="t", updated_at="t")
    session.add(eng)
    session.flush()

    exc = ExceptionRecord(engagement_id=eng.engagement_id, module="AUDIT", created_at="t", rule_id=None)
    session.add(exc)
    session.commit()
    assert session.get(ExceptionRecord, exc.exception_id).rule_id is None
