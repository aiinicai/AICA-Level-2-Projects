"""
Stage 9 — every audit rule module's evaluate() function, tested
directly against fabricated MappedRow/engagement objects (no DB, no
file upload pipeline — same style as tests/unit/test_accounting_rules.py).
Audit `evaluate()` is 2-arg (engagement, dataset) — NOT framework-aware,
per Stage 9's design (SA-based procedures apply regardless of AS/Ind
AS). The full real pipeline (upload -> map -> validate -> review) is
covered separately in tests/test_audit_http.py.

An autouse fixture forces `resolve_materiality_threshold_paise()` (used
by AUD-JE-001/003, AUD-CASH-010, AUD-WO-011) onto its disclosed FinSight
default (₹1,00,000 = 10,000,000 paise) by monkeypatching
`engagement_service.get_entity_profile` to return None — the same
approach test_shared_detectors.py uses, so no real DB/session is ever
touched by this file. Prior-/next-year comparison rules (AUD-MOV-005,
AUD-EST-009, AUD-SUB-007) monkeypatch their own module's
`find_prior_year_dataset`/`find_next_year_dataset` name directly,
mirroring test_accounting_rules.py's AS10-DEP-002/AS29-PROV-010 tests.

Uses only synthetic, fabricated data — never real client/financial
data, per the standing instruction.

Run with: pytest tests/unit/test_audit_rules.py -v
"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.rules import wording
from app.rules.accounting import shared_detectors
from app.rules.audit import (
    aud_acc_004, aud_cash_010, aud_cut_013, aud_est_009, aud_je_001,
    aud_je_002, aud_je_003, aud_lob_012, aud_mov_005, aud_rev_008,
    aud_rpt_006, aud_sub_007, aud_wo_011,
)
from app.services.dataset_service import MappedRow

DEFAULT_MATERIALITY_PAISE = shared_detectors.DEFAULT_MATERIALITY_FALLBACK_PAISE  # 10,000,000 = ₹1,00,000
ABOVE_THRESHOLD = DEFAULT_MATERIALITY_PAISE + 500_000
BELOW_THRESHOLD = DEFAULT_MATERIALITY_PAISE - 500_000


class _Engagement:
    def __init__(self, entity_name="Acme Manufacturing Ltd", financial_year="2025-26", engagement_id=1):
        self.entity_name = entity_name
        self.financial_year = financial_year
        self.engagement_id = engagement_id


def _row(dataset_type, values, file_id=1, row_index=0):
    return MappedRow(file_id=file_id, dataset_type=dataset_type, row_index=row_index, values=values)


ENGAGEMENT = _Engagement()
FY_END = date(2026, 3, 31)  # bounds of "2025-26"


@pytest.fixture(autouse=True)
def _no_entity_profile(monkeypatch):
    """Forces every resolve_materiality_threshold_paise() call in this
    file onto the disclosed FinSight default, without touching a real
    DB session."""
    monkeypatch.setattr(shared_detectors.engagement_service, "get_entity_profile", lambda engagement_id: None)


# --- AUD-JE-001: Manual Journal Entries Near Year-End -----------------------

def test_aud_je_001_no_je_data_is_insufficient_data():
    outcome = aud_je_001.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None
    assert outcome.exceptions == []
    assert outcome.rule_id == "AUD-JE-001"


def test_aud_je_001_unparseable_financial_year_is_insufficient_data():
    bad_engagement = _Engagement(financial_year="not-a-year")
    dataset = {"JE": [_row("JE", {"is_manual_entry": "Yes", "transaction_date": "2026-03-30", "debit_amount": ABOVE_THRESHOLD, "credit_amount": 0})]}
    outcome = aud_je_001.evaluate(bad_engagement, dataset)
    assert outcome.insufficient_data_reason is not None


def test_aud_je_001_manual_entry_near_year_end_above_threshold_flagged():
    dataset = {"JE": [_row("JE", {
        "is_manual_entry": "Yes", "transaction_date": "2026-03-30",
        "debit_amount": ABOVE_THRESHOLD, "credit_amount": 0,
    })]}
    outcome = aud_je_001.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.AUDIT_ATTENTION_REQUIRED
    assert exc.risk_level == "HIGH"
    assert exc.threshold_used["threshold_is_sa_requirement"] is False


def test_aud_je_001_manual_entry_outside_window_not_flagged():
    dataset = {"JE": [_row("JE", {
        "is_manual_entry": "Yes", "transaction_date": "2026-01-15",
        "debit_amount": ABOVE_THRESHOLD, "credit_amount": 0,
    })]}
    outcome = aud_je_001.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []
    assert outcome.evaluated_count == 1


def test_aud_je_001_non_manual_entry_not_flagged():
    dataset = {"JE": [_row("JE", {
        "is_manual_entry": "No", "transaction_date": "2026-03-30",
        "debit_amount": ABOVE_THRESHOLD, "credit_amount": 0,
    })]}
    outcome = aud_je_001.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []
    assert outcome.evaluated_count == 0


def test_aud_je_001_amount_below_threshold_not_flagged():
    dataset = {"JE": [_row("JE", {
        "is_manual_entry": "Yes", "transaction_date": "2026-03-30",
        "debit_amount": BELOW_THRESHOLD, "credit_amount": 0,
    })]}
    outcome = aud_je_001.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_aud_je_001_missing_transaction_date_is_partial_note():
    dataset = {"JE": [_row("JE", {"is_manual_entry": "Yes", "debit_amount": ABOVE_THRESHOLD, "credit_amount": 0})]}
    outcome = aud_je_001.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []
    assert len(outcome.partial_insufficient_data_notes) == 1


# --- AUD-JE-002: Manual Journal Entry Posted on a Non-Business Day ---------

def test_aud_je_002_no_je_data_is_insufficient_data():
    outcome = aud_je_002.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


def test_aud_je_002_weekend_manual_entry_flagged_low_review_required():
    # 2026-03-28 is a Saturday.
    dataset = {"JE": [_row("JE", {"is_manual_entry": "Yes", "transaction_date": "2026-03-28"})]}
    outcome = aud_je_002.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.REVIEW_REQUIRED
    assert exc.risk_level == "LOW"


def test_aud_je_002_weekday_manual_entry_not_flagged():
    # 2026-03-30 is a Monday.
    dataset = {"JE": [_row("JE", {"is_manual_entry": "Yes", "transaction_date": "2026-03-30"})]}
    outcome = aud_je_002.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_aud_je_002_non_manual_weekend_entry_not_flagged():
    dataset = {"JE": [_row("JE", {"is_manual_entry": "No", "transaction_date": "2026-03-28"})]}
    outcome = aud_je_002.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-JE-003: Round-Sum Manual Entry Above Threshold ---------------------

def test_aud_je_003_no_je_data_is_insufficient_data():
    outcome = aud_je_003.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


def test_aud_je_003_round_sum_above_threshold_flagged_medium():
    amount = DEFAULT_MATERIALITY_PAISE + 1_000_000  # a further exact multiple of 1,000,000
    dataset = {"JE": [_row("JE", {"is_manual_entry": "Yes", "debit_amount": amount, "credit_amount": 0})]}
    outcome = aud_je_003.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.POTENTIAL_AUDIT_RISK
    assert exc.risk_level == "MEDIUM"


def test_aud_je_003_non_round_amount_not_flagged():
    dataset = {"JE": [_row("JE", {"is_manual_entry": "Yes", "debit_amount": ABOVE_THRESHOLD + 1, "credit_amount": 0})]}
    outcome = aud_je_003.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_aud_je_003_round_amount_below_threshold_not_flagged():
    dataset = {"JE": [_row("JE", {"is_manual_entry": "Yes", "debit_amount": 1_000_000, "credit_amount": 0})]}
    outcome = aud_je_003.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-ACC-004: Rare Account Combination ----------------------------------

def _je_voucher(ref, accounts, file_id=1):
    return [_row("JE", {"reference_number": ref, "account_name": acc, "debit_amount": 100000, "credit_amount": 0}, file_id=file_id) for acc in accounts]


def test_aud_acc_004_no_je_data_is_insufficient_data():
    outcome = aud_acc_004.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


def test_aud_acc_004_no_reference_number_is_insufficient_data():
    dataset = {"JE": [_row("JE", {"account_name": "Cash"})]}
    outcome = aud_acc_004.evaluate(ENGAGEMENT, dataset)
    assert outcome.insufficient_data_reason is not None


def test_aud_acc_004_fewer_than_minimum_multiline_vouchers_is_insufficient_data():
    rows = []
    for i in range(2):
        rows += _je_voucher(f"V{i}", ["Cash", "Sales"])
    outcome = aud_acc_004.evaluate(ENGAGEMENT, {"JE": rows})
    assert outcome.insufficient_data_reason is not None


def test_aud_acc_004_rare_combination_flagged_medium():
    rows = []
    for i in range(5):
        rows += _je_voucher(f"COMMON{i}", ["Cash", "Sales"])
    rows += _je_voucher("RARE1", ["Repairs & Maintenance", "Bank"])
    outcome = aud_acc_004.evaluate(ENGAGEMENT, {"JE": rows})
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.POTENTIAL_AUDIT_RISK
    assert exc.risk_level == "MEDIUM"
    assert exc.threshold_used["occurrence_count"] == 1


# --- AUD-MOV-005: Significant Account Balance Movement vs Prior Year -------

def test_aud_mov_005_no_tb_data_is_insufficient_data():
    outcome = aud_mov_005.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


def test_aud_mov_005_no_prior_engagement_is_insufficient_data(monkeypatch):
    monkeypatch.setattr(aud_mov_005, "find_prior_year_dataset", lambda engagement: None)
    dataset = {"TB": [_row("TB", {"account_name": "Sales", "debit_amount": 0, "credit_amount": 1_000_000})]}
    outcome = aud_mov_005.evaluate(ENGAGEMENT, dataset)
    assert outcome.insufficient_data_reason is not None


def test_aud_mov_005_large_movement_flagged_medium(monkeypatch):
    prior = {"TB": [_row("TB", {"account_name": "Sales", "debit_amount": 0, "credit_amount": 1_000_000})]}
    monkeypatch.setattr(aud_mov_005, "find_prior_year_dataset", lambda engagement: prior)
    dataset = {"TB": [_row("TB", {"account_name": "Sales", "debit_amount": 0, "credit_amount": 1_400_000})]}  # +40%
    outcome = aud_mov_005.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.POTENTIAL_AUDIT_RISK
    assert exc.risk_level == "MEDIUM"  # Stage 9 correction: downgraded from High
    assert exc.threshold_used["movement_pct"] == 40.0


def test_aud_mov_005_small_movement_not_flagged(monkeypatch):
    prior = {"TB": [_row("TB", {"account_name": "Sales", "debit_amount": 0, "credit_amount": 1_000_000})]}
    monkeypatch.setattr(aud_mov_005, "find_prior_year_dataset", lambda engagement: prior)
    dataset = {"TB": [_row("TB", {"account_name": "Sales", "debit_amount": 0, "credit_amount": 1_050_000})]}  # +5%
    outcome = aud_mov_005.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-RPT-006: Related Party Transaction Candidates ----------------------

def test_aud_rpt_006_no_party_name_anywhere_is_insufficient_data():
    dataset = {"TB": [_row("TB", {"account_name": "Sales"})]}
    outcome = aud_rpt_006.evaluate(ENGAGEMENT, dataset)
    assert outcome.insufficient_data_reason is not None


def test_aud_rpt_006_candidate_flagged_high_audit_attention():
    dataset = {"SALES": [_row("SALES", {"party_name": "XYZ Director Enterprises", "debit_amount": 250000, "credit_amount": 0})]}
    outcome = aud_rpt_006.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.AUDIT_ATTENTION_REQUIRED
    assert exc.risk_level == "HIGH"
    assert "CANDIDATE only" in exc.explanation or "candidate" in exc.explanation.lower()


def test_aud_rpt_006_no_match_no_exceptions():
    dataset = {"SALES": [_row("SALES", {"party_name": "Independent Buyer Pvt Ltd", "debit_amount": 100000, "credit_amount": 0})]}
    outcome = aud_rpt_006.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-SUB-007: Pre-Year-End Entry Reversed Shortly After -----------------

def test_aud_sub_007_no_je_data_is_insufficient_data():
    outcome = aud_sub_007.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


def test_aud_sub_007_within_period_reversal_flagged_independent_of_next_engagement(monkeypatch):
    monkeypatch.setattr(aud_sub_007, "find_next_year_dataset", lambda engagement: None)
    dataset = {"JE": [
        _row("JE", {"transaction_date": "2026-03-25", "account_name": "Suspense", "debit_amount": 500000, "credit_amount": 0}, file_id=1),
        _row("JE", {"transaction_date": "2026-03-31", "account_name": "Suspense", "debit_amount": 0, "credit_amount": 500000}, file_id=2),
    ]}
    outcome = aud_sub_007.evaluate(ENGAGEMENT, dataset)
    # Within-period half must run regardless of the missing next engagement.
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.AUDIT_ATTENTION_REQUIRED
    assert exc.threshold_used["half"] == "within_period"
    # Only the subsequent-period half is reported as unavailable, via a
    # partial note — never outcome.insufficient_data_reason.
    assert outcome.insufficient_data_reason is None
    assert len(outcome.partial_insufficient_data_notes) == 1


def test_aud_sub_007_subsequent_period_reversal_flagged_when_next_engagement_exists(monkeypatch):
    next_dataset = {"JE": [
        _row("JE", {"transaction_date": "2026-04-05", "account_name": "Suspense", "debit_amount": 0, "credit_amount": 700000}, file_id=3),
    ]}
    monkeypatch.setattr(aud_sub_007, "find_next_year_dataset", lambda engagement: next_dataset)
    dataset = {"JE": [
        _row("JE", {"transaction_date": "2026-03-28", "account_name": "Suspense", "debit_amount": 700000, "credit_amount": 0}, file_id=1),
    ]}
    outcome = aud_sub_007.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].threshold_used["half"] == "subsequent_period"
    assert outcome.partial_insufficient_data_notes == []


def test_aud_sub_007_no_match_in_either_half_no_exceptions(monkeypatch):
    monkeypatch.setattr(aud_sub_007, "find_next_year_dataset", lambda engagement: None)
    dataset = {"JE": [
        _row("JE", {"transaction_date": "2026-03-25", "account_name": "Suspense", "debit_amount": 500000, "credit_amount": 0}),
    ]}
    outcome = aud_sub_007.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []
    assert len(outcome.partial_insufficient_data_notes) == 1


# --- AUD-CUT-013: Revenue Cut-off -------------------------------------------

def test_aud_cut_013_no_sales_data_is_insufficient_data():
    outcome = aud_cut_013.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


def test_aud_cut_013_transaction_near_year_end_flagged_high():
    dataset = {"SALES": [_row("SALES", {"transaction_date": "2026-03-29", "party_name": "Buyer Co", "debit_amount": 300000, "credit_amount": 0})]}
    outcome = aud_cut_013.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.AUDIT_ATTENTION_REQUIRED
    assert exc.risk_level == "HIGH"
    assert exc.threshold_used["side"] == "before"


def test_aud_cut_013_transaction_shortly_after_year_end_flagged_high():
    dataset = {"SALES": [_row("SALES", {"transaction_date": "2026-04-03", "party_name": "Buyer Co", "debit_amount": 300000, "credit_amount": 0})]}
    outcome = aud_cut_013.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].threshold_used["side"] == "after"


def test_aud_cut_013_transaction_mid_year_not_flagged():
    dataset = {"SALES": [_row("SALES", {"transaction_date": "2025-09-15", "party_name": "Buyer Co", "debit_amount": 300000, "credit_amount": 0})]}
    outcome = aud_cut_013.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-REV-008: Revenue Entry With No Matching Receivable ----------------

def test_aud_rev_008_no_sales_data_is_insufficient_data():
    outcome = aud_rev_008.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


def test_aud_rev_008_no_ar_data_is_insufficient_data():
    dataset = {"SALES": [_row("SALES", {"party_name": "Buyer Co", "debit_amount": 100000, "credit_amount": 0})]}
    outcome = aud_rev_008.evaluate(ENGAGEMENT, dataset)
    assert outcome.insufficient_data_reason is not None


def test_aud_rev_008_unmatched_sale_flagged_medium():
    dataset = {
        "SALES": [_row("SALES", {"party_name": "Buyer Co", "debit_amount": 100000, "credit_amount": 0})],
        "AR": [_row("AR", {"party_name": "A Totally Different Party", "debit_amount": 100000, "credit_amount": 0})],
    }
    outcome = aud_rev_008.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.POTENTIAL_AUDIT_RISK
    assert exc.risk_level == "MEDIUM"


def test_aud_rev_008_matched_sale_not_flagged():
    dataset = {
        "SALES": [_row("SALES", {"party_name": "Buyer Co", "debit_amount": 100000, "credit_amount": 0})],
        "AR": [_row("AR", {"party_name": "Buyer Co", "debit_amount": 100000, "credit_amount": 0})],
    }
    outcome = aud_rev_008.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-EST-009: Significant Estimate-Linked Account Movement -------------

def test_aud_est_009_no_matching_accounts_is_insufficient_data():
    outcome = aud_est_009.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


def test_aud_est_009_no_prior_engagement_is_insufficient_data(monkeypatch):
    monkeypatch.setattr(aud_est_009, "find_prior_year_dataset", lambda engagement: None)
    dataset = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 500000})]}
    outcome = aud_est_009.evaluate(ENGAGEMENT, dataset)
    assert outcome.insufficient_data_reason is not None


def test_aud_est_009_large_movement_either_direction_flagged_high(monkeypatch):
    prior = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 500000})]}
    monkeypatch.setattr(aud_est_009, "find_prior_year_dataset", lambda engagement: prior)
    # A 40% decrease.
    dataset = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 200000, "credit_amount": 0})]}
    outcome = aud_est_009.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.AUDIT_ATTENTION_REQUIRED
    assert exc.risk_level == "HIGH"
    assert exc.threshold_used["direction"] == "decreased"


def test_aud_est_009_large_increase_also_flagged(monkeypatch):
    prior = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 500000})]}
    monkeypatch.setattr(aud_est_009, "find_prior_year_dataset", lambda engagement: prior)
    dataset = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 800000})]}  # +60%
    outcome = aud_est_009.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].threshold_used["direction"] == "increased"


def test_aud_est_009_small_movement_not_flagged(monkeypatch):
    prior = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 500000})]}
    monkeypatch.setattr(aud_est_009, "find_prior_year_dataset", lambda engagement: prior)
    dataset = {"TB": [_row("TB", {"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 520000})]}  # +4%
    outcome = aud_est_009.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-CASH-010: Material Cash Transaction Review -------------------------

def test_aud_cash_010_no_bank_data_is_insufficient_data():
    outcome = aud_cash_010.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


def test_aud_cash_010_no_payment_mode_populated_is_insufficient_data():
    dataset = {"BANK": [_row("BANK", {"debit_amount": 100000, "credit_amount": 0})]}
    outcome = aud_cash_010.evaluate(ENGAGEMENT, dataset)
    assert outcome.insufficient_data_reason is not None


def test_aud_cash_010_material_cash_transaction_flagged_medium_neutral_wording():
    dataset = {"BANK": [_row("BANK", {"payment_mode": "Cash", "debit_amount": ABOVE_THRESHOLD, "credit_amount": 0})]}
    outcome = aud_cash_010.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.POTENTIAL_AUDIT_RISK
    assert exc.risk_level == "MEDIUM"
    assert "not imply" in exc.explanation or "inherently unusual" in exc.explanation


def test_aud_cash_010_non_cash_transaction_not_flagged():
    dataset = {"BANK": [_row("BANK", {"payment_mode": "Cheque", "debit_amount": ABOVE_THRESHOLD, "credit_amount": 0})]}
    outcome = aud_cash_010.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_aud_cash_010_cash_below_threshold_not_flagged():
    dataset = {"BANK": [_row("BANK", {"payment_mode": "Cash", "debit_amount": BELOW_THRESHOLD, "credit_amount": 0})]}
    outcome = aud_cash_010.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-WO-011: Large Write-offs -------------------------------------------

def test_aud_wo_011_no_ledger_data_is_insufficient_data():
    outcome = aud_wo_011.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


def test_aud_wo_011_write_off_above_threshold_flagged_high():
    dataset = {"JE": [_row("JE", {"account_name": "Bad Debts Written Off", "debit_amount": ABOVE_THRESHOLD, "credit_amount": 0})]}
    outcome = aud_wo_011.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.AUDIT_ATTENTION_REQUIRED
    assert exc.risk_level == "HIGH"


def test_aud_wo_011_no_keyword_match_not_flagged():
    dataset = {"JE": [_row("JE", {"account_name": "Sales Return", "debit_amount": ABOVE_THRESHOLD, "credit_amount": 0})]}
    outcome = aud_wo_011.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_aud_wo_011_write_off_below_threshold_not_flagged():
    dataset = {"JE": [_row("JE", {"account_name": "Bad Debts Written Off", "debit_amount": BELOW_THRESHOLD, "credit_amount": 0})]}
    outcome = aud_wo_011.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_aud_wo_011_matches_via_description_field_too():
    dataset = {"JE": [_row("JE", {"account_name": "Sundry Debtors", "description": "Balance waived off as uncollectible", "debit_amount": 0, "credit_amount": ABOVE_THRESHOLD})]}
    outcome = aud_wo_011.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1


# --- AUD-LOB-012: Long Outstanding Balances ---------------------------------

def test_aud_lob_012_no_ar_ap_data_is_insufficient_data():
    outcome = aud_lob_012.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


def test_aud_lob_012_unparseable_financial_year_is_insufficient_data():
    bad_engagement = _Engagement(financial_year="bad")
    dataset = {"AR": [_row("AR", {"party_name": "Old Debtor", "transaction_date": "2025-06-01", "debit_amount": 500000, "credit_amount": 0})]}
    outcome = aud_lob_012.evaluate(bad_engagement, dataset)
    assert outcome.insufficient_data_reason is not None


def test_aud_lob_012_long_outstanding_ar_balance_flagged_medium():
    # Last movement 2025-06-01, FY end 2026-03-31 -> 303 days, above 180-day threshold.
    dataset = {"AR": [_row("AR", {"party_name": "Old Debtor", "transaction_date": "2025-06-01", "debit_amount": 500000, "credit_amount": 0})]}
    outcome = aud_lob_012.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    assert exc.label == wording.POTENTIAL_AUDIT_RISK
    assert exc.risk_level == "MEDIUM"
    assert exc.threshold_used["ageing_is_approximated_not_per_invoice"] is True


def test_aud_lob_012_recent_ar_balance_not_flagged():
    dataset = {"AR": [_row("AR", {"party_name": "Recent Debtor", "transaction_date": "2026-03-01", "debit_amount": 500000, "credit_amount": 0})]}
    outcome = aud_lob_012.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_aud_lob_012_below_minimum_outstanding_not_flagged():
    dataset = {"AR": [_row("AR", {"party_name": "Tiny Balance", "transaction_date": "2025-01-01", "debit_amount": 50000, "credit_amount": 0})]}
    outcome = aud_lob_012.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_aud_lob_012_ap_polarity_is_credit_minus_debit():
    # Long-outstanding AP balance: credit-heavy, aged.
    dataset = {"AP": [_row("AP", {"party_name": "Old Vendor", "transaction_date": "2025-05-01", "debit_amount": 0, "credit_amount": 500000})]}
    outcome = aud_lob_012.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].threshold_used["polarity_source_dataset_type"] == "AP"


# --- Cross-cutting: every audit module's ExceptionDraft label is in AUDIT_LABELS ---

_ALL_MODULES = (
    aud_je_001, aud_je_002, aud_je_003, aud_acc_004, aud_mov_005, aud_rpt_006,
    aud_sub_007, aud_cut_013, aud_rev_008, aud_est_009, aud_cash_010, aud_wo_011, aud_lob_012,
)


def test_every_audit_module_declares_a_single_string_rule_id():
    seen_ids = set()
    for module in _ALL_MODULES:
        assert isinstance(module.RULE_ID, str)
        assert module.RULE_ID not in seen_ids, f"Duplicate RULE_ID {module.RULE_ID!r}"
        seen_ids.add(module.RULE_ID)
    assert len(seen_ids) == 13


def test_every_audit_module_assertions_are_valid_codes():
    valid_codes = {
        "EXISTENCE", "OCCURRENCE", "COMPLETENESS", "ACCURACY", "CUT_OFF",
        "CLASSIFICATION", "VALUATION", "RIGHTS_OBLIGATIONS", "PRESENTATION_DISCLOSURE",
    }
    for module in _ALL_MODULES:
        for code in module.ASSERTIONS:
            assert code in valid_codes, f"{module.RULE_ID} uses unknown assertion code {code!r}"
