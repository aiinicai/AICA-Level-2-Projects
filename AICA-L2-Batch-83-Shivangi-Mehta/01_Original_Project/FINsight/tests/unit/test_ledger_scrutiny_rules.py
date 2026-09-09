"""
Ledger Scrutiny pack — every rule module's evaluate() function, tested
directly against fabricated MappedRow/engagement objects (no DB, no
file upload pipeline — same style as tests/unit/test_audit_rules.py).
Added per the user's explicit further approval on top of the Stage 9
13-rule cap (see app/rules/audit/ledger_scrutiny_shared.py's module
docstring for the full disclosure of what was adapted from the
user-provided prototype and what was excluded as a duplicate).

Stage 21 revision (explicitly approved): AUD-LS-008 (Month-End
Transaction) is retired — its module and tests are gone; see
app/rules/audit/__init__.py's docstring for the rationale. 12 rule
modules remain (AUD-LS-001 through AUD-LS-007, AUD-LS-009 through
AUD-LS-013). AUD-LS-012 (Unusual Ledger Activity) is extended to also
detect unusually LOW months, not just unusually high ones — see that
module's own docstring for why the "too low" side needs 3+ other
months of history.

AUD-LS-007 (Possible Split Transactions) uses
resolve_materiality_threshold_paise(), so it shares this file's
autouse fixture forcing that onto its disclosed FinSight default —
same approach as test_audit_rules.py.

Uses only synthetic, fabricated data — never real client/financial
data, per the standing instruction.

Run with: pytest tests/unit/test_ledger_scrutiny_rules.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.rules import wording
from app.rules.accounting import shared_detectors
from app.rules.audit import (
    aud_ls_001, aud_ls_002, aud_ls_003, aud_ls_004, aud_ls_005, aud_ls_006,
    aud_ls_007, aud_ls_009, aud_ls_010, aud_ls_011, aud_ls_012,
    aud_ls_013,
)
from app.services.dataset_service import MappedRow

DEFAULT_MATERIALITY_PAISE = shared_detectors.DEFAULT_MATERIALITY_FALLBACK_PAISE  # 10,000,000 = ₹1,00,000


class _Engagement:
    def __init__(self, entity_name="Acme Manufacturing Ltd", financial_year="2025-26", engagement_id=1):
        self.entity_name = entity_name
        self.financial_year = financial_year
        self.engagement_id = engagement_id


def _row(dataset_type, values, file_id=1, row_index=0, transaction_id=None):
    return MappedRow(file_id=file_id, dataset_type=dataset_type, row_index=row_index, values=values,
                      transaction_id=transaction_id)


ENGAGEMENT = _Engagement()


@pytest.fixture(autouse=True)
def _no_entity_profile(monkeypatch):
    monkeypatch.setattr(shared_detectors.engagement_service, "get_entity_profile", lambda engagement_id: None)


def _assert_valid_exception(exc, rule_id):
    assert exc.label in wording.AUDIT_LABELS
    for field in (exc.trigger_condition, exc.explanation):
        wording.assert_non_definitive(field)


# --- AUD-LS-001: Missing Narration -------------------------------------------

def test_aud_ls_001_no_ledger_data_is_insufficient_data():
    outcome = aud_ls_001.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None
    assert outcome.exceptions == []
    assert outcome.rule_id == "AUD-LS-001"


def test_aud_ls_001_blank_description_flagged():
    dataset = {"GL": [_row("GL", {
        "transaction_date": "2025-06-10", "account_name": "Rent", "debit_amount": 500000, "credit_amount": 0,
        "description": "",
    }, transaction_id=101)]}
    outcome = aud_ls_001.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    _assert_valid_exception(exc, "AUD-LS-001")
    assert exc.related_transaction_id == 101


def test_aud_ls_001_populated_description_not_flagged():
    dataset = {"GL": [_row("GL", {
        "transaction_date": "2025-06-10", "account_name": "Rent", "debit_amount": 500000, "credit_amount": 0,
        "description": "June office rent per lease agreement",
    })]}
    outcome = aud_ls_001.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-LS-002: Generic Narration -------------------------------------------

def test_aud_ls_002_generic_term_flagged():
    dataset = {"GL": [_row("GL", {
        "transaction_date": "2025-06-10", "account_name": "Rent", "debit_amount": 500000, "credit_amount": 0,
        "description": "payment",
    }, transaction_id=102)]}
    outcome = aud_ls_002.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    _assert_valid_exception(outcome.exceptions[0], "AUD-LS-002")
    assert outcome.exceptions[0].related_transaction_id == 102


def test_aud_ls_002_blank_description_not_flagged_here():
    """AUD-LS-001's territory, not AUD-LS-002's."""
    dataset = {"GL": [_row("GL", {
        "transaction_date": "2025-06-10", "account_name": "Rent", "debit_amount": 500000, "credit_amount": 0,
        "description": "",
    })]}
    outcome = aud_ls_002.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_aud_ls_002_descriptive_narration_not_flagged():
    dataset = {"GL": [_row("GL", {
        "transaction_date": "2025-06-10", "account_name": "Rent", "debit_amount": 500000, "credit_amount": 0,
        "description": "June office rent per lease agreement dated 1 April 2025",
    })]}
    outcome = aud_ls_002.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-LS-003: Potential Duplicate Transactions ----------------------------

def test_aud_ls_003_matching_pair_flagged():
    dataset = {"GL": [
        _row("GL", {"transaction_date": "2025-07-01", "account_name": "Office Exp", "debit_amount": 200000,
                     "credit_amount": 0, "description": "stationery purchase"}, transaction_id=103),
        _row("GL", {"transaction_date": "2025-07-01", "account_name": "Office Exp", "debit_amount": 200000,
                     "credit_amount": 0, "description": "stationery purchase"}, transaction_id=104, row_index=1),
    ]}
    outcome = aud_ls_003.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 2
    for exc in outcome.exceptions:
        _assert_valid_exception(exc, "AUD-LS-003")
    assert {e.related_transaction_id for e in outcome.exceptions} == {103, 104}


def test_aud_ls_003_no_match_not_flagged():
    dataset = {"GL": [
        _row("GL", {"transaction_date": "2025-07-01", "account_name": "Office Exp", "debit_amount": 200000,
                     "credit_amount": 0, "description": "stationery purchase"}),
        _row("GL", {"transaction_date": "2025-07-02", "account_name": "Office Exp", "debit_amount": 300000,
                     "credit_amount": 0, "description": "printer cartridges"}, row_index=1),
    ]}
    outcome = aud_ls_003.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-LS-004: Zero, Negative, or Dual-Sided Amount ------------------------

@pytest.mark.parametrize("debit,credit", [(0, 0), (-10000, 0), (10000, 5000)])
def test_aud_ls_004_structural_issues_flagged(debit, credit):
    dataset = {"GL": [_row("GL", {
        "transaction_date": "2025-07-05", "account_name": "Misc", "debit_amount": debit, "credit_amount": credit,
        "description": "test entry",
    }, transaction_id=105)]}
    outcome = aud_ls_004.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    _assert_valid_exception(outcome.exceptions[0], "AUD-LS-004")
    assert outcome.exceptions[0].related_transaction_id == 105


def test_aud_ls_004_normal_single_sided_amount_not_flagged():
    dataset = {"GL": [_row("GL", {
        "transaction_date": "2025-07-05", "account_name": "Misc", "debit_amount": 10000, "credit_amount": 0,
        "description": "test entry",
    })]}
    outcome = aud_ls_004.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-LS-005: Round-Number Transaction ------------------------------------

def test_aud_ls_005_exact_multiple_flagged():
    dataset = {"GL": [_row("GL", {
        "transaction_date": "2025-07-10", "account_name": "Conveyance", "debit_amount": 500000, "credit_amount": 0,
        "description": "cab fare reimbursement",
    }, transaction_id=106)]}
    outcome = aud_ls_005.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    _assert_valid_exception(outcome.exceptions[0], "AUD-LS-005")
    assert outcome.exceptions[0].related_transaction_id == 106


def test_aud_ls_005_non_round_amount_not_flagged():
    dataset = {"GL": [_row("GL", {
        "transaction_date": "2025-07-10", "account_name": "Conveyance", "debit_amount": 437650, "credit_amount": 0,
        "description": "cab fare reimbursement",
    })]}
    outcome = aud_ls_005.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-LS-006: Unusual Amount vs Ledger Pattern ----------------------------

def test_aud_ls_006_outlier_amount_flagged():
    dataset = {"GL": [
        _row("GL", {"transaction_date": d, "account_name": "Electricity", "debit_amount": amt, "credit_amount": 0,
                     "description": "electricity bill"}, row_index=i, transaction_id=200 + i)
        for i, (d, amt) in enumerate([
            ("2025-04-05", 15000), ("2025-05-05", 15200), ("2025-06-05", 15400),
            ("2025-07-05", 15600), ("2025-08-05", 15800), ("2025-09-05", 16000),
            ("2025-10-05", 500000),
        ])
    ]}
    outcome = aud_ls_006.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    _assert_valid_exception(exc, "AUD-LS-006")
    assert exc.related_transaction_id == 206


def test_aud_ls_006_below_min_rows_is_insufficient_data():
    dataset = {"GL": [
        _row("GL", {"transaction_date": "2025-04-05", "account_name": "Electricity", "debit_amount": 15000,
                     "credit_amount": 0, "description": "electricity bill"}),
        _row("GL", {"transaction_date": "2025-05-05", "account_name": "Electricity", "debit_amount": 15200,
                     "credit_amount": 0, "description": "electricity bill"}, row_index=1),
    ]}
    outcome = aud_ls_006.evaluate(ENGAGEMENT, dataset)
    assert outcome.insufficient_data_reason is not None
    assert outcome.exceptions == []


# --- AUD-LS-007: Possible Split Transactions ---------------------------------

def test_aud_ls_007_same_day_split_below_threshold_flagged():
    half = (DEFAULT_MATERIALITY_PAISE // 2) + 100000
    dataset = {"GL": [
        _row("GL", {"transaction_date": "2025-08-01", "party_name": "Buyer Y", "debit_amount": half,
                     "credit_amount": 0, "description": "bulk order part 1"}, transaction_id=301),
        _row("GL", {"transaction_date": "2025-08-01", "party_name": "Buyer Y", "debit_amount": half,
                     "credit_amount": 0, "description": "bulk order part 2"}, transaction_id=302, row_index=1),
    ]}
    outcome = aud_ls_007.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 2
    for exc in outcome.exceptions:
        _assert_valid_exception(exc, "AUD-LS-007")
    assert {e.related_transaction_id for e in outcome.exceptions} == {301, 302}


def test_aud_ls_007_single_leg_already_above_threshold_not_flagged():
    dataset = {"GL": [
        _row("GL", {"transaction_date": "2025-08-01", "party_name": "Buyer Y",
                     "debit_amount": DEFAULT_MATERIALITY_PAISE + 500000, "credit_amount": 0,
                     "description": "large single order"}),
        _row("GL", {"transaction_date": "2025-08-01", "party_name": "Buyer Y", "debit_amount": 50000,
                     "credit_amount": 0, "description": "small unrelated add-on"}, row_index=1),
    ]}
    outcome = aud_ls_007.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-LS-009: Year-End Transaction ----------------------------------------

def test_aud_ls_009_last_three_days_of_fy_flagged():
    dataset = {"GL": [_row("GL", {
        "transaction_date": "2026-03-30", "account_name": "Provision", "debit_amount": 500000, "credit_amount": 0,
        "description": "year end provision entry",
    }, transaction_id=108)]}
    outcome = aud_ls_009.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    _assert_valid_exception(outcome.exceptions[0], "AUD-LS-009")
    assert outcome.exceptions[0].related_transaction_id == 108


def test_aud_ls_009_mid_year_not_flagged():
    dataset = {"GL": [_row("GL", {
        "transaction_date": "2025-09-15", "account_name": "Provision", "debit_amount": 500000, "credit_amount": 0,
        "description": "provision entry",
    })]}
    outcome = aud_ls_009.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_aud_ls_009_unparseable_financial_year_is_insufficient_data():
    bad_engagement = _Engagement(financial_year="not-a-year")
    dataset = {"GL": [_row("GL", {"transaction_date": "2026-03-30", "account_name": "Provision",
                                   "debit_amount": 500000, "credit_amount": 0, "description": "entry"})]}
    outcome = aud_ls_009.evaluate(bad_engagement, dataset)
    assert outcome.insufficient_data_reason is not None


# --- AUD-LS-010: Risk Indicator Keywords -------------------------------------

def test_aud_ls_010_keyword_match_flagged():
    dataset = {"GL": [_row("GL", {
        "transaction_date": "2025-09-15", "account_name": "Donation Exp", "debit_amount": 250000, "credit_amount": 0,
        "description": "donation to trust fund",
    }, transaction_id=109)]}
    outcome = aud_ls_010.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    _assert_valid_exception(outcome.exceptions[0], "AUD-LS-010")
    assert outcome.exceptions[0].related_transaction_id == 109


def test_aud_ls_010_no_keyword_not_flagged():
    dataset = {"GL": [_row("GL", {
        "transaction_date": "2025-09-15", "account_name": "Office Supplies", "debit_amount": 250000,
        "credit_amount": 0, "description": "stationery and printing",
    })]}
    outcome = aud_ls_010.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-LS-011: Repeated Party Transactions ---------------------------------

def test_aud_ls_011_more_than_threshold_in_month_flagged():
    dataset = {"GL": [
        _row("GL", {"transaction_date": d, "party_name": "Vendor Z", "debit_amount": 100000, "credit_amount": 0,
                     "description": "material purchase"}, row_index=i, transaction_id=400 + i)
        for i, d in enumerate(["2025-11-02", "2025-11-10", "2025-11-20"])
    ]}
    outcome = aud_ls_011.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 3
    for exc in outcome.exceptions:
        _assert_valid_exception(exc, "AUD-LS-011")


def test_aud_ls_011_at_or_below_threshold_not_flagged():
    dataset = {"GL": [
        _row("GL", {"transaction_date": d, "party_name": "Vendor Z", "debit_amount": 100000, "credit_amount": 0,
                     "description": "material purchase"}, row_index=i)
        for i, d in enumerate(["2025-11-02", "2025-11-10"])
    ]}
    outcome = aud_ls_011.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-LS-012: Unusual Ledger Activity -------------------------------------

def test_aud_ls_012_monthly_spike_flagged():
    dataset = {"GL": [
        _row("GL", {"transaction_date": d, "account_name": "Repairs", "debit_amount": amt, "credit_amount": 0,
                     "description": "repair work"}, row_index=i, transaction_id=500 + i)
        for i, (d, amt) in enumerate([
            ("2025-04-15", 500000), ("2025-05-15", 600000), ("2025-06-15", 50000000),
        ])
    ]}
    outcome = aud_ls_012.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    _assert_valid_exception(exc, "AUD-LS-012")
    assert exc.related_transaction_id == 502


def test_aud_ls_012_below_min_months_is_insufficient_data():
    dataset = {"GL": [_row("GL", {
        "transaction_date": "2025-04-15", "account_name": "Repairs", "debit_amount": 500000, "credit_amount": 0,
        "description": "repair work",
    })]}
    outcome = aud_ls_012.evaluate(ENGAGEMENT, dataset)
    assert outcome.insufficient_data_reason is not None
    assert outcome.exceptions == []


def test_aud_ls_012_monthly_dip_flagged():
    # 4 months of otherwise-steady activity, one month far below the rest.
    dataset = {"GL": [
        _row("GL", {"transaction_date": d, "account_name": "Office Rent", "debit_amount": amt, "credit_amount": 0,
                     "description": "monthly rent"}, row_index=i, transaction_id=700 + i)
        for i, (d, amt) in enumerate([
            ("2025-04-05", 1000000), ("2025-05-05", 1100000), ("2025-06-05", 1050000), ("2025-07-05", 100000),
        ])
    ]}
    outcome = aud_ls_012.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    _assert_valid_exception(exc, "AUD-LS-012")
    assert exc.related_transaction_id == 703
    assert exc.threshold_used["direction"] == "low"


def test_aud_ls_012_dip_not_flagged_with_fewer_than_three_other_months():
    # Only 2 "other" months of history — the dip side is deliberately
    # NOT evaluated here (see the module's own docstring for why: a
    # single large month would otherwise drag the average down onto
    # every other month as a false "too low" flag).
    dataset = {"GL": [
        _row("GL", {"transaction_date": d, "account_name": "Office Rent", "debit_amount": amt, "credit_amount": 0,
                     "description": "monthly rent"}, row_index=i)
        for i, (d, amt) in enumerate([
            ("2025-04-05", 1000000), ("2025-05-05", 1100000), ("2025-06-05", 100000),
        ])
    ]}
    outcome = aud_ls_012.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- AUD-LS-013: Unusual Ledger Usage ----------------------------------------

def test_aud_ls_013_one_off_ledger_use_flagged():
    rows = [
        _row("GL", {"transaction_date": d, "party_name": "Vendor W", "account_name": "Freight Exp",
                     "debit_amount": 200000, "credit_amount": 0, "description": "freight charge"}, row_index=i)
        for i, d in enumerate(["2025-05-01", "2025-05-08", "2025-05-15", "2025-05-22"])
    ]
    rows.append(_row("GL", {
        "transaction_date": "2025-06-01", "party_name": "Vendor W", "account_name": "Handling Exp",
        "debit_amount": 50000, "credit_amount": 0, "description": "handling charge one time",
    }, row_index=4, transaction_id=600))
    dataset = {"GL": rows}
    outcome = aud_ls_013.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    exc = outcome.exceptions[0]
    _assert_valid_exception(exc, "AUD-LS-013")
    assert exc.related_transaction_id == 600


def test_aud_ls_013_below_min_party_txns_is_insufficient_data():
    dataset = {"GL": [
        _row("GL", {"transaction_date": "2025-05-01", "party_name": "Vendor W", "account_name": "Freight Exp",
                     "debit_amount": 200000, "credit_amount": 0, "description": "freight charge"}),
    ]}
    outcome = aud_ls_013.evaluate(ENGAGEMENT, dataset)
    assert outcome.insufficient_data_reason is not None
    assert outcome.exceptions == []


# --- Cross-cutting: every AUD-LS module's ExceptionDraft label/assertions are valid --

_ALL_LS_MODULES = (
    aud_ls_001, aud_ls_002, aud_ls_003, aud_ls_004, aud_ls_005, aud_ls_006,
    aud_ls_007, aud_ls_009, aud_ls_010, aud_ls_011, aud_ls_012,
    aud_ls_013,
)


def test_every_ls_module_declares_a_single_string_rule_id():
    seen_ids = set()
    for module in _ALL_LS_MODULES:
        assert isinstance(module.RULE_ID, str)
        assert module.RULE_ID not in seen_ids, f"Duplicate RULE_ID {module.RULE_ID!r}"
        seen_ids.add(module.RULE_ID)
    assert len(seen_ids) == 12


def test_every_ls_module_assertions_are_valid_codes():
    valid_codes = {
        "EXISTENCE", "OCCURRENCE", "COMPLETENESS", "ACCURACY", "CUT_OFF",
        "CLASSIFICATION", "VALUATION", "RIGHTS_OBLIGATIONS", "PRESENTATION_DISCLOSURE",
    }
    for module in _ALL_LS_MODULES:
        for code in module.ASSERTIONS:
            assert code in valid_codes, f"{module.RULE_ID} uses unknown assertion code {code!r}"
