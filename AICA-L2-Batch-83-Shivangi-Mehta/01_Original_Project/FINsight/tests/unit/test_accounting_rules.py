"""
Stage 8 — every accounting rule module's evaluate() function, tested
directly against fabricated MappedRow/engagement objects (no DB, no
file upload pipeline — dataset_service.MappedRow is a plain dataclass,
so rule logic is unit-testable in isolation). The prior-year rules
(AS10-DEP-002, AS29-PROV-010) monkeypatch their own module's
`find_prior_year_dataset` name rather than touching the DB — the full
real pipeline (upload -> map -> validate -> two engagements -> review)
is covered separately in tests/test_accounting_http.py.

Stage 8 Round 2 rewrite. Every `evaluate()` call now takes a third
`framework` argument ("AS" or "IND_AS") per correction #1 — the module
itself is framework-agnostic in its analytical logic but must return
the correct `rule_id` (and, for AS5-PPI-012/INDAS8-PPE-012, the correct
framework-specific terminology) for whichever framework it's asked to
evaluate under. AS10-FA-001/AS26-INT-011 were redesigned (correction
#3/#4) to a method-agnostic roll-forward consistency check instead of a
straight-line variance estimate — their test fixtures now use
opening/closing WDV roll-forward fields instead of
date_put_to_use/original_cost_paise/book_depreciation_rate.
AS6-DEP-002 was replaced by AS10-DEP-002 (correction #2) — its module
is deleted; AS10-DEP-002 carries the same rate-consistency logic under
corrected rule_ids.

Uses only synthetic, fabricated data — never real client/financial
data, per the standing instruction.

Run with: pytest tests/unit/test_accounting_rules.py -v
"""
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.rules import wording
from app.rules.accounting import (
    as2_inv_003, as10_dep_002, as10_fa_001, as13_inv_005, as15_eb_008,
    as16_bc_006, as18_rpt_009, as26_int_011, as29_prov_010, gen_ppi_012,
)
from app.services.dataset_service import MappedRow


class _Engagement:
    def __init__(self, entity_name="Acme Manufacturing Ltd", financial_year="2025-26"):
        self.entity_name = entity_name
        self.financial_year = financial_year
        self.engagement_id = 1


def _row(dataset_type, values, file_id=1, row_index=0):
    return MappedRow(file_id=file_id, dataset_type=dataset_type, row_index=row_index, values=values)


ENGAGEMENT = _Engagement()

# Full, reconciling roll-forward fixture used as a base by several tests below.
_RECONCILING_FA = {
    "asset_description": "Plant", "opening_wdv_paise": 10_000_000, "additions_paise": 0,
    "deletions_paise": 0, "book_depreciation_amount_paise": 1_000_000, "closing_wdv_paise": 9_000_000,
}


# --- AS10-FA-001 / INDAS16-FA-001 -------------------------------------------

def test_as10_no_fixed_assets_is_insufficient_data():
    outcome = as10_fa_001.evaluate(ENGAGEMENT, {}, "AS")
    assert outcome.insufficient_data_reason is not None
    assert outcome.exceptions == []
    assert outcome.rule_id == "AS10-FA-001"


def test_as10_rule_id_is_framework_specific():
    outcome_as = as10_fa_001.evaluate(ENGAGEMENT, {}, "AS")
    outcome_ind_as = as10_fa_001.evaluate(ENGAGEMENT, {}, "IND_AS")
    assert outcome_as.rule_id == "AS10-FA-001"
    assert outcome_ind_as.rule_id == "INDAS16-FA-001"


def test_as10_reconciling_roll_forward_no_exception():
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", dict(_RECONCILING_FA))]}
    outcome = as10_fa_001.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.evaluated_count == 1
    assert outcome.exceptions == []


def test_as10_non_straight_line_wdv_style_figures_reconcile_without_exception():
    # A WDV-method entity's own figures — no assumption of straight-line is
    # made anywhere in this check; it only tests whether the entity's own
    # reported numbers arithmetically tie out.
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {
        "asset_description": "Plant (WDV method)", "opening_wdv_paise": 5_000_000, "additions_paise": 1_000_000,
        "deletions_paise": 0, "book_depreciation_amount_paise": 900_000, "closing_wdv_paise": 5_100_000,
    })]}
    outcome = as10_fa_001.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.evaluated_count == 1
    assert outcome.exceptions == []


def test_as10_non_reconciling_roll_forward_raises_review_required():
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {
        "asset_description": "Plant", "opening_wdv_paise": 10_000_000, "additions_paise": 0,
        "deletions_paise": 0, "book_depreciation_amount_paise": 1_000_000, "closing_wdv_paise": 8_500_000,
    })]}
    outcome = as10_fa_001.evaluate(ENGAGEMENT, dataset, "AS")
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.REVIEW_REQUIRED
    assert exc.threshold_used["difference_paise"] == 500_000


def test_as10_missing_roll_forward_field_is_insufficient_data_not_exception():
    # Correction #3: do not create an exception merely because a method
    # cannot be established — missing fields must produce a partial
    # insufficient-data note, never a fabricated exception.
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {
        "asset_description": "Plant", "opening_wdv_paise": 10_000_000, "additions_paise": None,
        "deletions_paise": 0, "book_depreciation_amount_paise": 1_000_000, "closing_wdv_paise": 9_000_000,
    })]}
    outcome = as10_fa_001.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.evaluated_count == 0
    assert outcome.exceptions == []
    assert len(outcome.partial_insufficient_data_notes) == 1


# --- AS26-INT-011 / INDAS38-INT-011 -----------------------------------------

def test_as26_no_intangible_rows_is_insufficient_data():
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {
        "asset_description": "Plant", "asset_class": "Tangible", **{
            k: v for k, v in _RECONCILING_FA.items() if k != "asset_description"
        },
    })]}
    outcome = as26_int_011.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.insufficient_data_reason is not None
    assert outcome.rule_id == "AS26-INT-011"


def test_as26_rule_id_is_framework_specific():
    assert as26_int_011.evaluate(ENGAGEMENT, {}, "AS").rule_id == "AS26-INT-011"
    assert as26_int_011.evaluate(ENGAGEMENT, {}, "IND_AS").rule_id == "INDAS38-INT-011"


def test_as26_intangible_non_reconciling_raises_review_required():
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {
        "asset_description": "Software License", "asset_class": "Intangible",
        "opening_wdv_paise": 2_000_000, "additions_paise": 0, "deletions_paise": 0,
        "book_depreciation_amount_paise": 500_000, "closing_wdv_paise": 1_600_000,
    })]}
    outcome = as26_int_011.evaluate(ENGAGEMENT, dataset, "AS")
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].label == wording.REVIEW_REQUIRED
    assert outcome.exceptions[0].risk_level == "LOW"


def test_as26_intangible_reconciling_no_exception():
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {
        "asset_description": "Software License", "asset_class": "intangible",
        "opening_wdv_paise": 2_000_000, "additions_paise": 0, "deletions_paise": 0,
        "book_depreciation_amount_paise": 500_000, "closing_wdv_paise": 1_500_000,
    })]}
    outcome = as26_int_011.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.evaluated_count == 1
    assert outcome.exceptions == []


# --- AS10-DEP-002 / INDAS16-DEP-002 (prior-year comparison, monkeypatched) --

def test_as10_dep_002_no_current_fixed_assets_is_insufficient_data():
    outcome = as10_dep_002.evaluate(ENGAGEMENT, {}, "AS")
    assert outcome.insufficient_data_reason is not None
    assert outcome.rule_id == "AS10-DEP-002"


def test_as10_dep_002_rule_id_is_framework_specific():
    assert as10_dep_002.evaluate(ENGAGEMENT, {}, "AS").rule_id == "AS10-DEP-002"
    assert as10_dep_002.evaluate(ENGAGEMENT, {}, "IND_AS").rule_id == "INDAS16-DEP-002"


def test_as10_dep_002_no_prior_engagement_is_insufficient_data(monkeypatch):
    monkeypatch.setattr(as10_dep_002, "find_prior_year_dataset", lambda engagement: None)
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {"asset_class": "Plant & Machinery", "book_depreciation_rate": 10.0})]}
    outcome = as10_dep_002.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.insufficient_data_reason is not None
    assert "prior-year engagement" in outcome.insufficient_data_reason


def test_as10_dep_002_prior_engagement_with_no_fixed_assets_is_insufficient_data(monkeypatch):
    monkeypatch.setattr(as10_dep_002, "find_prior_year_dataset", lambda engagement: {})
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {"asset_class": "Plant & Machinery", "book_depreciation_rate": 10.0})]}
    outcome = as10_dep_002.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.insufficient_data_reason is not None


def test_as10_dep_002_same_rate_no_exception(monkeypatch):
    prior = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {"asset_class": "Plant & Machinery", "book_depreciation_rate": 10.0})]}
    monkeypatch.setattr(as10_dep_002, "find_prior_year_dataset", lambda engagement: prior)
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {"asset_class": "Plant & Machinery", "book_depreciation_rate": 10.0})]}
    outcome = as10_dep_002.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.evaluated_count == 1
    assert outcome.exceptions == []


def test_as10_dep_002_changed_rate_raises_potential_inconsistency(monkeypatch):
    prior = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {"asset_class": "Plant & Machinery", "book_depreciation_rate": 10.0})]}
    monkeypatch.setattr(as10_dep_002, "find_prior_year_dataset", lambda engagement: prior)
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {"asset_class": "Plant & Machinery", "book_depreciation_rate": 15.0})]}
    outcome = as10_dep_002.evaluate(ENGAGEMENT, dataset, "AS")
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].label == wording.POTENTIAL_INCONSISTENCY


def test_as10_dep_002_asset_class_absent_in_prior_year_is_partial_insufficient_data(monkeypatch):
    prior = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {"asset_class": "Furniture", "book_depreciation_rate": 10.0})]}
    monkeypatch.setattr(as10_dep_002, "find_prior_year_dataset", lambda engagement: prior)
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {"asset_class": "Plant & Machinery", "book_depreciation_rate": 15.0})]}
    outcome = as10_dep_002.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.exceptions == []
    assert len(outcome.partial_insufficient_data_notes) == 1


def test_as6_dep_002_module_no_longer_exists():
    # Correction #2: AS6-DEP-002 must not remain an active, coded rule.
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("app.rules.accounting.as6_dep_002")


# --- AS29-PROV-010 / INDAS37-PROV-010 (prior-year comparison, monkeypatched) -

def test_as29_no_provision_accounts_is_insufficient_data():
    dataset = {"TB": [_row("TB", {"account_name": "Sales", "debit_amount": 0, "credit_amount": 100000})]}
    outcome = as29_prov_010.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.insufficient_data_reason is not None


def test_as29_rule_id_is_framework_specific():
    assert as29_prov_010.evaluate(ENGAGEMENT, {}, "AS").rule_id == "AS29-PROV-010"
    assert as29_prov_010.evaluate(ENGAGEMENT, {}, "IND_AS").rule_id == "INDAS37-PROV-010"


def test_as29_no_prior_engagement_is_insufficient_data(monkeypatch):
    monkeypatch.setattr(as29_prov_010, "find_prior_year_dataset", lambda engagement: None)
    dataset = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 500000})]}
    outcome = as29_prov_010.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.insufficient_data_reason is not None
    assert "prior-year engagement" in outcome.insufficient_data_reason


def test_as29_prior_engagement_with_no_provision_accounts_is_insufficient_data(monkeypatch):
    prior = {"TB": [_row("TB", {"account_name": "Sales", "debit_amount": 0, "credit_amount": 100000})]}
    monkeypatch.setattr(as29_prov_010, "find_prior_year_dataset", lambda engagement: prior)
    dataset = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 500000})]}
    outcome = as29_prov_010.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.insufficient_data_reason is not None


def test_as29_zero_prior_closing_balance_is_skipped_without_exception(monkeypatch):
    prior = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 500000, "credit_amount": 500000})]}
    monkeypatch.setattr(as29_prov_010, "find_prior_year_dataset", lambda engagement: prior)
    dataset = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 100000})]}
    outcome = as29_prov_010.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.exceptions == []


def test_as29_large_movement_raises_review_required_with_analytical_threshold_labeled(monkeypatch):
    # Prior closing balance: credit 500000, no debit -> net credit 500000
    prior = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 500000})]}
    monkeypatch.setattr(as29_prov_010, "find_prior_year_dataset", lambda engagement: prior)
    # Current period: a 400000 debit against the same account -> an 80% movement
    dataset = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 400000, "credit_amount": 0})]}
    outcome = as29_prov_010.evaluate(ENGAGEMENT, dataset, "AS")
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    # Correction #5: must be "Review Required," never framed as an accounting
    # exception/inconsistency, and the threshold must be labeled explicitly
    # as a configurable FinSight analytical threshold, not a standard rule.
    assert exc.label == wording.REVIEW_REQUIRED
    assert exc.threshold_used["movement_pct"] == 80.0
    assert exc.threshold_used["finsight_analytical_threshold_pct"] == 50.0
    assert exc.threshold_used["threshold_is_accounting_standard_requirement"] is False
    assert "accounting-standard requirement" in exc.explanation
    assert "not, on its own, described as inconsistent" in exc.explanation


def test_as29_small_movement_below_threshold_no_exception(monkeypatch):
    prior = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 500000})]}
    monkeypatch.setattr(as29_prov_010, "find_prior_year_dataset", lambda engagement: prior)
    dataset = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 50000, "credit_amount": 0})]}
    outcome = as29_prov_010.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.exceptions == []


def test_as29_account_missing_in_current_year_is_partial_insufficient_data(monkeypatch):
    prior = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 500000})]}
    monkeypatch.setattr(as29_prov_010, "find_prior_year_dataset", lambda engagement: prior)
    dataset = {"TB": [_row("TB", {"account_name": "Provision for Gratuity", "debit_amount": 0, "credit_amount": 100000})]}
    outcome = as29_prov_010.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.exceptions == []
    assert len(outcome.partial_insufficient_data_notes) == 1


# --- AS2-INV-003 / AS13-INV-005 (always insufficient data) ------------------

def test_as2_inv_003_always_insufficient_data():
    for framework in ("AS", "IND_AS"):
        for dataset in ({}, {"TB": [_row("TB", {"account_name": "Inventory", "debit_amount": 100000, "credit_amount": 0})]}):
            outcome = as2_inv_003.evaluate(ENGAGEMENT, dataset, framework)
            assert outcome.insufficient_data_reason is not None
            assert outcome.exceptions == []
    assert as2_inv_003.evaluate(ENGAGEMENT, {}, "AS").rule_id == "AS2-INV-003"
    assert as2_inv_003.evaluate(ENGAGEMENT, {}, "IND_AS").rule_id == "INDAS2-INV-003"


def test_as13_inv_005_always_insufficient_data():
    for framework in ("AS", "IND_AS"):
        for dataset in ({}, {"TB": [_row("TB", {"account_name": "Investments", "debit_amount": 100000, "credit_amount": 0})]}):
            outcome = as13_inv_005.evaluate(ENGAGEMENT, dataset, framework)
            assert outcome.insufficient_data_reason is not None
            assert outcome.exceptions == []
    assert as13_inv_005.evaluate(ENGAGEMENT, {}, "AS").rule_id == "AS13-INV-005"
    assert as13_inv_005.evaluate(ENGAGEMENT, {}, "IND_AS").rule_id == "INDAS109-INV-005"


# --- AS16-BC-006 / INDAS23-BC-006 -------------------------------------------

def test_as16_no_cwip_asset_is_insufficient_data():
    outcome = as16_bc_006.evaluate(ENGAGEMENT, {}, "AS")
    assert outcome.insufficient_data_reason is not None


def test_as16_rule_id_is_framework_specific():
    assert as16_bc_006.evaluate(ENGAGEMENT, {}, "AS").rule_id == "AS16-BC-006"
    assert as16_bc_006.evaluate(ENGAGEMENT, {}, "IND_AS").rule_id == "INDAS23-BC-006"


def test_as16_cwip_asset_with_no_loan_rows_is_partial_insufficient_data():
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {"asset_class": "CWIP", "asset_description": "Factory shed under construction", "original_cost_paise": 5_000_000})]}
    outcome = as16_bc_006.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.exceptions == []
    assert len(outcome.partial_insufficient_data_notes) == 1


def test_as16_cwip_and_loan_rows_raises_review_required_not_an_exception():
    dataset = {
        "FIXED_ASSETS": [_row("FIXED_ASSETS", {"asset_class": "CWIP", "asset_description": "Factory shed under construction", "original_cost_paise": 5_000_000})],
        "TB": [_row("TB", {"account_name": "Term Loan from Bank", "debit_amount": 0, "credit_amount": 3_000_000})],
    }
    outcome = as16_bc_006.evaluate(ENGAGEMENT, dataset, "AS")
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    # Correction #6: must be Review Required, never presented as an
    # accounting exception, and must state what cannot be established.
    assert exc.label == wording.REVIEW_REQUIRED
    assert exc.risk_level == "LOW"
    assert "qualifying asset" in exc.explanation
    assert "directly attributable" in exc.explanation
    assert "capitalization" in exc.explanation


# --- AS15-EB-008 / INDAS19-EB-008 -------------------------------------------

def test_as15_no_ledger_data_is_insufficient_data():
    outcome = as15_eb_008.evaluate(ENGAGEMENT, {}, "AS")
    assert outcome.insufficient_data_reason is not None


def test_as15_rule_id_is_framework_specific():
    assert as15_eb_008.evaluate(ENGAGEMENT, {}, "AS").rule_id == "AS15-EB-008"
    assert as15_eb_008.evaluate(ENGAGEMENT, {}, "IND_AS").rule_id == "INDAS19-EB-008"


def test_as15_no_matching_account_raises_review_required_advisory():
    dataset = {"TB": [_row("TB", {"account_name": "Sales", "debit_amount": 0, "credit_amount": 100000})]}
    outcome = as15_eb_008.evaluate(ENGAGEMENT, dataset, "AS")
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].label == wording.REVIEW_REQUIRED
    assert outcome.exceptions[0].risk_level == "LOW"


def test_as15_matching_account_present_no_exception():
    dataset = {"TB": [_row("TB", {"account_name": "Provision for Gratuity", "debit_amount": 0, "credit_amount": 200000})]}
    outcome = as15_eb_008.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.exceptions == []


# --- AS18-RPT-009 / INDAS24-RPT-009 -----------------------------------------

def test_as18_no_party_name_anywhere_is_insufficient_data():
    dataset = {"TB": [_row("TB", {"account_name": "Sales", "debit_amount": 0, "credit_amount": 100000})]}
    outcome = as18_rpt_009.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.insufficient_data_reason is not None


def test_as18_rule_id_is_framework_specific():
    assert as18_rpt_009.evaluate(ENGAGEMENT, {}, "AS").rule_id == "AS18-RPT-009"
    assert as18_rpt_009.evaluate(ENGAGEMENT, {}, "IND_AS").rule_id == "INDAS24-RPT-009"


def test_as18_no_related_party_match_no_exceptions():
    dataset = {"SALES": [_row("SALES", {"party_name": "Independent Buyer Pvt Ltd", "debit_amount": 100000, "credit_amount": 0})]}
    outcome = as18_rpt_009.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.exceptions == []


def test_as18_related_party_candidate_raises_potential_inconsistency():
    dataset = {"SALES": [_row("SALES", {"party_name": "XYZ Director Enterprises", "debit_amount": 250000, "credit_amount": 0})]}
    outcome = as18_rpt_009.evaluate(ENGAGEMENT, dataset, "AS")
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].label == wording.POTENTIAL_INCONSISTENCY
    assert outcome.exceptions[0].risk_level == "MEDIUM"


# --- AS5-PPI-012 / INDAS8-PPE-012 -------------------------------------------

def test_gen_ppi_012_no_description_data_is_insufficient_data():
    dataset = {"GL": [_row("GL", {"account_name": "Sales", "description": None})]}
    outcome = gen_ppi_012.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.insufficient_data_reason is not None


def test_gen_ppi_012_rule_id_is_framework_specific():
    assert gen_ppi_012.evaluate(ENGAGEMENT, {}, "AS").rule_id == "AS5-PPI-012"
    assert gen_ppi_012.evaluate(ENGAGEMENT, {}, "IND_AS").rule_id == "INDAS8-PPE-012"


def test_gen_ppi_012_no_keyword_match_no_exceptions():
    dataset = {"GL": [_row("GL", {"description": "Routine sale of goods", "debit_amount": 0, "credit_amount": 50000})]}
    outcome = gen_ppi_012.evaluate(ENGAGEMENT, dataset, "AS")
    assert outcome.evaluated_count == 1
    assert outcome.exceptions == []


def test_gen_ppi_012_as_framework_uses_prior_period_item_terminology():
    dataset = {"JE": [_row("JE", {"description": "Prior period adjustment for FY24-25 expense", "debit_amount": 30000, "credit_amount": 0})]}
    outcome = gen_ppi_012.evaluate(ENGAGEMENT, dataset, "AS")
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.POTENTIAL_INCONSISTENCY
    assert "prior period item" in exc.explanation.lower()
    assert "AS 5" in exc.explanation
    assert "prior period error" not in exc.explanation.lower()
    assert "Ind AS 8" not in exc.explanation


def test_gen_ppi_012_ind_as_framework_uses_prior_period_error_terminology():
    dataset = {"JE": [_row("JE", {"description": "Prior period adjustment for FY24-25 expense", "debit_amount": 30000, "credit_amount": 0})]}
    outcome = gen_ppi_012.evaluate(ENGAGEMENT, dataset, "IND_AS")
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.POTENTIAL_INCONSISTENCY
    assert "prior period error" in exc.explanation.lower()
    assert "Ind AS 8" in exc.explanation
    assert "prior period item" not in exc.explanation.lower()
    assert "AS 5" not in exc.explanation
