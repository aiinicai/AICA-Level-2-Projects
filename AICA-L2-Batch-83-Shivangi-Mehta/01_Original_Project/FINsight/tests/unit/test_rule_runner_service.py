"""
Stage 8 — app/services/rule_runner_service.py: the verification/active
gate (Blueprint Section 1.2) that decides whether a coded rule module
actually runs. Real SQLAlchemy 2.x ORM code against the sandbox shim +
real SQLite, same pattern as tests/unit/test_mapping_service.py.

Stage 8 Round 2 (correction #1): the gate is now also framework-aware.
`get_runnable_accounting_rules()` takes a `framework` argument and
`run_accounting_rule()`/`run_all_accounting_rules()` take one too; every
test below exercises that a rule seeded under one framework never
appears/executes for the other, alongside the pre-existing
active/verified/coded gating.

Run with: pytest tests/unit/test_rule_runner_service.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest


@pytest.fixture()
def svc(tmp_path):
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
    from app.services import rule_runner_service

    session = extensions.SessionLocal
    as_standard = Standard(framework="AS", code="AS 2", title="Valuation of Inventories", source_reference="test")
    ind_as_standard = Standard(framework="IND_AS", code="Ind AS 2", title="Inventories", source_reference="test")
    session.add(as_standard)
    session.add(ind_as_standard)
    session.commit()

    # A genuinely runnable AS rule (coded + active + verified + framework=AS).
    session.add(AccountingRule(
        rule_id="AS2-INV-003", standard_id=as_standard.standard_id, framework="AS",
        topic="Inventory Valuation Method", is_active=True, verification_status="VERIFIED",
    ))
    # The SAME coded module's Ind AS counterpart — a genuinely runnable IND_AS rule.
    session.add(AccountingRule(
        rule_id="INDAS2-INV-003", standard_id=ind_as_standard.standard_id, framework="IND_AS",
        topic="Inventory Valuation Method", is_active=True, verification_status="VERIFIED",
    ))
    # Coded, but not yet active (AS framework).
    session.add(AccountingRule(
        rule_id="AS13-INV-005", standard_id=as_standard.standard_id, framework="AS",
        topic="Investment Valuation", is_active=False, verification_status="VERIFIED",
    ))
    # Coded, active, but still awaiting source verification (AS framework).
    session.add(AccountingRule(
        rule_id="AS10-FA-001", standard_id=as_standard.standard_id, framework="AS",
        topic="Fixed Assets — Roll-Forward Consistency Review", is_active=True,
        verification_status="SOURCE_VERIFICATION_REQUIRED",
    ))
    # Active + verified in the DB, but no matching coded module exists.
    session.add(AccountingRule(
        rule_id="FAKE-999", standard_id=as_standard.standard_id, framework="AS",
        topic="Not A Real Rule", is_active=True, verification_status="VERIFIED",
    ))
    # Withdrawn marker row (correction #2) — AS-only, inactive, no coded module.
    session.add(AccountingRule(
        rule_id="AS6-DEP-002", standard_id=as_standard.standard_id, framework="AS",
        topic="Depreciation Accounting (Withdrawn)", is_active=False, verification_status="VERIFIED",
        description="WITHDRAWN. Superseded by AS 10 (Revised).",
    ))

    # --- Stage 9: AuditRule fixture rows (no framework dimension) ---
    from app.models.rules import AuditRule

    sa_standard = Standard(framework="SA", code="SA 240", title="The Auditor's Responsibilities Relating to Fraud", source_reference="test")
    session.add(sa_standard)
    session.commit()

    # A genuinely runnable audit rule (coded + active + verified). AUD-JE-002
    # has no materiality/prior-year dependency, so it runs cleanly with {}.
    session.add(AuditRule(
        rule_id="AUD-JE-002", standard_id=sa_standard.standard_id, topic="Manual Journal Entry Posted on a Non-Business Day",
        is_active=True, verification_status="VERIFIED", related_sa="SA 240", audit_area="Journal Entry Testing",
    ))
    # Coded, but not yet active.
    session.add(AuditRule(
        rule_id="AUD-JE-003", standard_id=sa_standard.standard_id, topic="Round-Sum Manual Entry Above Threshold",
        is_active=False, verification_status="VERIFIED", related_sa="SA 240, SA 500", audit_area="Journal Entry Testing",
    ))
    # Coded, active, but still awaiting source verification.
    session.add(AuditRule(
        rule_id="AUD-ACC-004", standard_id=sa_standard.standard_id, topic="Rare Account Combination",
        is_active=True, verification_status="SOURCE_VERIFICATION_REQUIRED", related_sa="SA 315, SA 330", audit_area="Unusual Account Combinations",
    ))
    # Active + verified in the DB, but no matching coded module exists.
    session.add(AuditRule(
        rule_id="AUD-FAKE-999", standard_id=sa_standard.standard_id, topic="Not A Real Audit Rule",
        is_active=True, verification_status="VERIFIED", related_sa="SA 240", audit_area="Not Real",
    ))
    session.commit()

    # --- Stage 10: TaxRule fixture rows (no framework dimension, same
    # gating shape as Audit, plus the Stage 10 wording-label check) ---
    from app.models.rules import TaxRule

    # A genuinely runnable tax rule (coded + active + verified). TAX-MSME-013
    # returns cleanly from an empty AP dataset (insufficient_data path), so
    # it runs cleanly with {}, same reasoning as AUD-JE-002 above.
    session.add(TaxRule(
        rule_id="TAX-MSME-013", topic="MSME Delayed-Payment Review Screen",
        is_active=True, verification_status="VERIFIED",
        legislative_act="IT_ACT_1961", provision_reference="Section 43B(h)",
    ))
    # Coded, but not yet active.
    session.add(TaxRule(
        rule_id="TAX-FAKE-INACTIVE-001", topic="Not A Real Tax Rule (Inactive)",
        is_active=False, verification_status="VERIFIED", legislative_act="IT_ACT_1961",
    ))
    # Coded, active, but still awaiting source verification.
    session.add(TaxRule(
        rule_id="TAX-FAKE-UNVERIFIED-001", topic="Not A Real Tax Rule (Unverified)",
        is_active=True, verification_status="SOURCE_VERIFICATION_REQUIRED", legislative_act="IT_ACT_1961",
    ))
    # Active + verified in the DB, but no matching coded module exists —
    # mirrors TAX-ACM-010's "law fine, not yet executable" shape.
    session.add(TaxRule(
        rule_id="TAX-FAKE-999", topic="Not A Real Tax Rule",
        is_active=True, verification_status="VERIFIED", legislative_act="IT_ACT_1961",
    ))
    session.commit()

    yield rule_runner_service
    extensions.SessionLocal.remove()


class _Engagement:
    entity_name = "Acme Manufacturing Ltd"
    financial_year = "2025-26"


# --- basic active/verified/coded gating (framework held constant) -----------

def test_get_runnable_accounting_rules_only_returns_active_verified_and_coded(svc):
    runnable = svc.get_runnable_accounting_rules("AS")
    assert [r.rule_id for r in runnable] == ["AS2-INV-003"]


def test_list_all_accounting_rules_returns_every_seeded_row(svc):
    all_rules = svc.list_all_accounting_rules()
    assert {r.rule_id for r in all_rules} == {
        "AS2-INV-003", "INDAS2-INV-003", "AS13-INV-005", "AS10-FA-001", "FAKE-999", "AS6-DEP-002",
    }


def test_get_standards_by_id(svc):
    standards = svc.get_standards_by_id()
    # 3 rows: AS 2 / Ind AS 2 (accounting fixture) + SA 240 (Stage 9 audit fixture).
    assert len(standards) == 3
    assert {s.code for s in standards.values()} == {"AS 2", "Ind AS 2", "SA 240"}


# --- framework-aware gating (correction #1) ----------------------------------

def test_as_framework_never_returns_ind_as_rules(svc):
    runnable = svc.get_runnable_accounting_rules("AS")
    assert "INDAS2-INV-003" not in [r.rule_id for r in runnable]


def test_ind_as_framework_never_returns_as_rules(svc):
    runnable = svc.get_runnable_accounting_rules("IND_AS")
    assert [r.rule_id for r in runnable] == ["INDAS2-INV-003"]
    assert "AS2-INV-003" not in [r.rule_id for r in runnable]


def test_run_accounting_rule_refuses_framework_mismatch(svc):
    as_rule = [r for r in svc.list_all_accounting_rules() if r.rule_id == "AS2-INV-003"][0]
    with pytest.raises(ValueError, match="framework"):
        svc.run_accounting_rule(as_rule, _Engagement(), {}, "IND_AS")


def test_run_all_accounting_rules_only_runs_the_requested_frameworks_rules(svc):
    as_outcomes = svc.run_all_accounting_rules(_Engagement(), {}, "AS")
    assert list(as_outcomes.keys()) == ["AS2-INV-003"]

    ind_as_outcomes = svc.run_all_accounting_rules(_Engagement(), {}, "IND_AS")
    assert list(ind_as_outcomes.keys()) == ["INDAS2-INV-003"]


def test_findings_display_the_correct_framework_reference(svc):
    as_outcome = svc.run_accounting_rule(
        [r for r in svc.list_all_accounting_rules() if r.rule_id == "AS2-INV-003"][0],
        _Engagement(), {}, "AS",
    )
    ind_as_outcome = svc.run_accounting_rule(
        [r for r in svc.list_all_accounting_rules() if r.rule_id == "INDAS2-INV-003"][0],
        _Engagement(), {}, "IND_AS",
    )
    assert as_outcome.rule_id == "AS2-INV-003"
    assert ind_as_outcome.rule_id == "INDAS2-INV-003"


def test_outcome_rule_id_is_always_forced_to_the_db_rows_rule_id(svc, monkeypatch):
    from app.rules.accounting import as2_inv_003
    from app.rules.base_rule import RuleOutcome

    # Simulate a hypothetical bug in the module returning the wrong id —
    # the runner must overwrite it with the DB row's own rule_id regardless.
    monkeypatch.setattr(as2_inv_003, "evaluate", lambda engagement, dataset, framework: RuleOutcome(rule_id="WRONG-ID"))

    as_rule = [r for r in svc.list_all_accounting_rules() if r.rule_id == "AS2-INV-003"][0]
    outcome = svc.run_accounting_rule(as_rule, _Engagement(), {}, "AS")
    assert outcome.rule_id == "AS2-INV-003"


# --- verification / active gating (unchanged from Round 1, re-verified) -----

def test_run_accounting_rule_refuses_unverified_rule(svc):
    unverified = [r for r in svc.list_all_accounting_rules() if r.rule_id == "AS10-FA-001"][0]
    with pytest.raises(ValueError, match="not VERIFIED"):
        svc.run_accounting_rule(unverified, _Engagement(), {}, "AS")


def test_unverified_rule_is_excluded_from_runnable_rules(svc):
    runnable_ids = [r.rule_id for r in svc.get_runnable_accounting_rules("AS")]
    assert "AS10-FA-001" not in runnable_ids


def test_run_accounting_rule_refuses_inactive_rule(svc):
    inactive = [r for r in svc.list_all_accounting_rules() if r.rule_id == "AS13-INV-005"][0]
    with pytest.raises(ValueError, match="is_active"):
        svc.run_accounting_rule(inactive, _Engagement(), {}, "AS")


def test_uncoded_rule_is_excluded_from_runnable_rules(svc):
    runnable_ids = [r.rule_id for r in svc.get_runnable_accounting_rules("AS")]
    assert "FAKE-999" not in runnable_ids


# --- AS6-DEP-002 withdrawn marker (correction #2) ----------------------------

def test_as6_dep_002_never_appears_in_runnable_rules(svc):
    runnable_ids = [r.rule_id for r in svc.get_runnable_accounting_rules("AS")]
    assert "AS6-DEP-002" not in runnable_ids


def test_as6_dep_002_cannot_be_run_directly(svc):
    withdrawn = [r for r in svc.list_all_accounting_rules() if r.rule_id == "AS6-DEP-002"][0]
    with pytest.raises(ValueError, match="is_active"):
        svc.run_accounting_rule(withdrawn, _Engagement(), {}, "AS")


# --- Stage 9: Audit rule gating (no framework dimension) --------------------

def test_get_runnable_audit_rules_only_returns_active_verified_and_coded(svc):
    runnable = svc.get_runnable_audit_rules()
    assert [r.rule_id for r in runnable] == ["AUD-JE-002"]


def test_list_all_audit_rules_returns_every_seeded_row(svc):
    all_rules = svc.list_all_audit_rules()
    assert {r.rule_id for r in all_rules} == {"AUD-JE-002", "AUD-JE-003", "AUD-ACC-004", "AUD-FAKE-999"}


def test_run_audit_rule_refuses_unverified_rule(svc):
    unverified = [r for r in svc.list_all_audit_rules() if r.rule_id == "AUD-ACC-004"][0]
    with pytest.raises(ValueError, match="not VERIFIED"):
        svc.run_audit_rule(unverified, _Engagement(), {})


def test_audit_unverified_rule_is_excluded_from_runnable_rules(svc):
    runnable_ids = [r.rule_id for r in svc.get_runnable_audit_rules()]
    assert "AUD-ACC-004" not in runnable_ids


def test_run_audit_rule_refuses_inactive_rule(svc):
    inactive = [r for r in svc.list_all_audit_rules() if r.rule_id == "AUD-JE-003"][0]
    with pytest.raises(ValueError, match="is_active"):
        svc.run_audit_rule(inactive, _Engagement(), {})


def test_audit_uncoded_rule_is_excluded_from_runnable_rules(svc):
    runnable_ids = [r.rule_id for r in svc.get_runnable_audit_rules()]
    assert "AUD-FAKE-999" not in runnable_ids


def test_run_all_audit_rules_only_runs_runnable_rules(svc):
    outcomes = svc.run_all_audit_rules(_Engagement(), {})
    assert list(outcomes.keys()) == ["AUD-JE-002"]


def test_audit_outcome_rule_id_is_always_forced_to_the_db_rows_rule_id(svc, monkeypatch):
    from app.rules.audit import aud_je_002
    from app.rules.base_rule import RuleOutcome

    monkeypatch.setattr(aud_je_002, "evaluate", lambda engagement, dataset: RuleOutcome(rule_id="WRONG-ID"))

    rule = [r for r in svc.list_all_audit_rules() if r.rule_id == "AUD-JE-002"][0]
    outcome = svc.run_audit_rule(rule, _Engagement(), {})
    assert outcome.rule_id == "AUD-JE-002"


def test_run_audit_rule_enforces_audit_labels(svc, monkeypatch):
    from app.rules import wording
    from app.rules.audit import aud_je_002
    from app.rules.base_rule import ExceptionDraft, RuleOutcome

    def _bad_evaluate(engagement, dataset):
        outcome = RuleOutcome(rule_id="AUD-JE-002")
        outcome.exceptions.append(ExceptionDraft(
            label=wording.POTENTIAL_EXCEPTION,  # an Accounting-only label — must never leak into Audit
            area="Journal Entry Testing", trigger_condition="test trigger", explanation="test explanation",
            suggested_query="test query", risk_level="LOW",
        ))
        return outcome

    monkeypatch.setattr(aud_je_002, "evaluate", _bad_evaluate)
    rule = [r for r in svc.list_all_audit_rules() if r.rule_id == "AUD-JE-002"][0]
    with pytest.raises(ValueError, match="permitted audit labels"):
        svc.run_audit_rule(rule, _Engagement(), {})


def test_run_audit_rule_allows_review_required_and_insufficient_data_labels(svc, monkeypatch):
    from app.rules import wording
    from app.rules.audit import aud_je_002
    from app.rules.base_rule import ExceptionDraft, RuleOutcome

    def _ok_evaluate(engagement, dataset):
        outcome = RuleOutcome(rule_id="AUD-JE-002")
        outcome.exceptions.append(ExceptionDraft(
            label=wording.REVIEW_REQUIRED,
            area="Journal Entry Testing", trigger_condition="test trigger", explanation="test explanation",
            suggested_query="test query", risk_level="LOW",
        ))
        return outcome

    monkeypatch.setattr(aud_je_002, "evaluate", _ok_evaluate)
    rule = [r for r in svc.list_all_audit_rules() if r.rule_id == "AUD-JE-002"][0]
    outcome = svc.run_audit_rule(rule, _Engagement(), {})
    assert outcome.exceptions[0].label == wording.REVIEW_REQUIRED


# --- Stage 10: Tax rule gating (no framework dimension, same shape as Audit,
# plus the wording.TAX_LABELS enforcement Stage 10 added) ------------------

def test_get_runnable_tax_rules_only_returns_active_verified_and_coded(svc):
    runnable = svc.get_runnable_tax_rules()
    assert [r.rule_id for r in runnable] == ["TAX-MSME-013"]


def test_list_all_tax_rules_returns_every_seeded_row(svc):
    all_rules = svc.list_all_tax_rules()
    assert {r.rule_id for r in all_rules} == {
        "TAX-MSME-013", "TAX-FAKE-INACTIVE-001", "TAX-FAKE-UNVERIFIED-001", "TAX-FAKE-999",
    }


def test_run_tax_rule_refuses_unverified_rule(svc):
    unverified = [r for r in svc.list_all_tax_rules() if r.rule_id == "TAX-FAKE-UNVERIFIED-001"][0]
    with pytest.raises(ValueError, match="not VERIFIED"):
        svc.run_tax_rule(unverified, _Engagement(), {})


def test_tax_unverified_rule_is_excluded_from_runnable_rules(svc):
    runnable_ids = [r.rule_id for r in svc.get_runnable_tax_rules()]
    assert "TAX-FAKE-UNVERIFIED-001" not in runnable_ids


def test_run_tax_rule_refuses_inactive_rule(svc):
    inactive = [r for r in svc.list_all_tax_rules() if r.rule_id == "TAX-FAKE-INACTIVE-001"][0]
    with pytest.raises(ValueError, match="is_active"):
        svc.run_tax_rule(inactive, _Engagement(), {})


def test_tax_uncoded_rule_is_excluded_from_runnable_rules(svc):
    runnable_ids = [r.rule_id for r in svc.get_runnable_tax_rules()]
    assert "TAX-FAKE-999" not in runnable_ids


def test_run_all_tax_rules_only_runs_runnable_rules(svc):
    outcomes = svc.run_all_tax_rules(_Engagement(), {})
    assert list(outcomes.keys()) == ["TAX-MSME-013"]


def test_tax_outcome_rule_id_is_always_forced_to_the_db_rows_rule_id(svc, monkeypatch):
    from app.rules.base_rule import RuleOutcome
    from app.rules.tax import tax_msme_013

    monkeypatch.setattr(tax_msme_013, "evaluate", lambda engagement, dataset: RuleOutcome(rule_id="WRONG-ID"))

    rule = [r for r in svc.list_all_tax_rules() if r.rule_id == "TAX-MSME-013"][0]
    outcome = svc.run_tax_rule(rule, _Engagement(), {})
    assert outcome.rule_id == "TAX-MSME-013"


def test_run_tax_rule_enforces_tax_labels(svc, monkeypatch):
    from app.rules import wording
    from app.rules.base_rule import ExceptionDraft, RuleOutcome
    from app.rules.tax import tax_msme_013

    def _bad_evaluate(engagement, dataset):
        outcome = RuleOutcome(rule_id="TAX-MSME-013")
        outcome.exceptions.append(ExceptionDraft(
            label=wording.AUDIT_ATTENTION_REQUIRED,  # an Audit-only label — must never leak into Tax
            area="MSME Delayed-Payment Review Screen", trigger_condition="test trigger",
            explanation="test explanation", suggested_query="test query", risk_level="LOW",
        ))
        return outcome

    monkeypatch.setattr(tax_msme_013, "evaluate", _bad_evaluate)
    rule = [r for r in svc.list_all_tax_rules() if r.rule_id == "TAX-MSME-013"][0]
    with pytest.raises(ValueError, match="permitted tax labels"):
        svc.run_tax_rule(rule, _Engagement(), {})


def test_run_tax_rule_allows_every_tax_label(svc, monkeypatch):
    from app.rules import wording
    from app.rules.base_rule import ExceptionDraft, RuleOutcome
    from app.rules.tax import tax_msme_013

    def _ok_evaluate(engagement, dataset):
        outcome = RuleOutcome(rule_id="TAX-MSME-013")
        for label in wording.TAX_LABELS:
            outcome.exceptions.append(ExceptionDraft(
                label=label, area="MSME Delayed-Payment Review Screen", trigger_condition="test trigger",
                explanation="test explanation", suggested_query="test query", risk_level="LOW",
            ))
        return outcome

    monkeypatch.setattr(tax_msme_013, "evaluate", _ok_evaluate)
    rule = [r for r in svc.list_all_tax_rules() if r.rule_id == "TAX-MSME-013"][0]
    outcome = svc.run_tax_rule(rule, _Engagement(), {})
    assert [e.label for e in outcome.exceptions] == list(wording.TAX_LABELS)
    assert wording.POTENTIAL_MSME_PAYMENT_REVIEW in [e.label for e in outcome.exceptions]
