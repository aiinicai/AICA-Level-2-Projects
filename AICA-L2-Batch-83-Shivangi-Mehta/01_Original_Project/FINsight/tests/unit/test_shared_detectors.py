"""
Stage 8 — app/rules/accounting/shared_detectors.py's pure-function
pieces (reconcile_asset_roll_forward, roll_forward_fields_present,
detect_related_party_candidates). find_prior_year_dataset() needs a
real engagement/upload pipeline and is covered instead in
tests/unit/test_accounting_rules.py's prior-year rule tests
(AS10-DEP-002 / AS29-PROV-010), via monkeypatching, and in
tests/test_accounting_http.py's full round trip.

Stage 8 Round 2 (correction #3/#4): `expected_depreciation_paise()` was
removed — it assumed straight-line depreciation, which is no longer
acceptable (see AS10-FA-001/AS26-INT-011's redesign). It is replaced by
`reconcile_asset_roll_forward()`, a method-agnostic arithmetic identity
check, tested below.

Stage 9 additions: `find_next_year_dataset`, `net_balance_by_account`,
`reversal_movement_amount_and_pct`, `is_flag_true`,
`is_cash_payment_mode`, `resolve_materiality_threshold_paise` — all
added for Audit rule reuse (AUD-EST-009, AUD-MOV-005, AUD-SUB-007,
and the JE-testing/cash rules), tested below the same way:
`find_next_year_dataset`/`resolve_materiality_threshold_paise` via
monkeypatching (a real engagement/upload pipeline isn't needed for a
unit test of the function's own branching), the rest as pure functions.

Run with: pytest tests/unit/test_shared_detectors.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.rules.accounting import shared_detectors
from app.rules.accounting.shared_detectors import (
    DEFAULT_MATERIALITY_FALLBACK_PAISE,
    ROLL_FORWARD_TOLERANCE_PAISE,
    detect_related_party_candidates,
    is_cash_payment_mode,
    is_flag_true,
    net_balance_by_account,
    reconcile_asset_roll_forward,
    resolve_materiality_threshold_paise,
    reversal_movement_amount_and_pct,
    roll_forward_fields_present,
)
from app.services.dataset_service import MappedRow


class _Engagement:
    def __init__(self, entity_name="Acme Manufacturing Ltd", financial_year="2025-26", engagement_id=1):
        self.entity_name = entity_name
        self.financial_year = financial_year
        self.engagement_id = engagement_id


class _EntityProfile:
    def __init__(self, overall_materiality):
        self.overall_materiality = overall_materiality


def _row(values, file_id=1, dataset_type="GL", row_index=0):
    return MappedRow(file_id=file_id, dataset_type=dataset_type, row_index=row_index, values=values)


# --- reconcile_asset_roll_forward -------------------------------------------

def test_reconcile_asset_roll_forward_exact_match_returns_zero():
    # opening 10,00,000 + additions 2,00,000 - deletions 0 - depreciation 1,00,000 = closing 11,00,000
    diff = reconcile_asset_roll_forward(1_000_000, 200_000, 0, 100_000, 1_100_000)
    assert diff == 0


def test_reconcile_asset_roll_forward_nonzero_difference():
    # implied closing = 1,000,000 + 0 - 0 - 100,000 = 900,000; reported closing 850,000 -> diff 50,000
    diff = reconcile_asset_roll_forward(1_000_000, 0, 0, 100_000, 850_000)
    assert diff == 50_000


def test_reconcile_asset_roll_forward_negative_difference():
    # implied closing = 900,000; reported closing 950,000 -> diff -50,000
    diff = reconcile_asset_roll_forward(1_000_000, 0, 0, 100_000, 950_000)
    assert diff == -50_000


def test_reconcile_asset_roll_forward_is_method_agnostic():
    # Two entities using entirely different depreciation methods (WDV vs SLM)
    # both reconcile cleanly as long as their OWN reported figures tie out —
    # the function never assumes or checks which method was used.
    wdv_diff = reconcile_asset_roll_forward(2_000_000, 0, 0, 300_000, 1_700_000)  # WDV-style
    slm_diff = reconcile_asset_roll_forward(2_000_000, 0, 0, 200_000, 1_800_000)  # SLM-style
    assert wdv_diff == 0
    assert slm_diff == 0


def test_reconcile_asset_roll_forward_within_tolerance_is_effectively_zero():
    diff = reconcile_asset_roll_forward(1_000_000, 0, 0, 100_000, 900_050)  # off by 50 paise
    assert abs(diff) <= ROLL_FORWARD_TOLERANCE_PAISE


# --- roll_forward_fields_present ---------------------------------------------

def test_roll_forward_fields_present_all_present():
    values = {
        "opening_wdv_paise": 1_000_000, "additions_paise": 0, "deletions_paise": 0,
        "book_depreciation_amount_paise": 100_000, "closing_wdv_paise": 900_000,
    }
    assert roll_forward_fields_present(values) is True


def test_roll_forward_fields_present_missing_one_field():
    values = {
        "opening_wdv_paise": 1_000_000, "additions_paise": 0, "deletions_paise": None,
        "book_depreciation_amount_paise": 100_000, "closing_wdv_paise": 900_000,
    }
    assert roll_forward_fields_present(values) is False


def test_roll_forward_fields_present_all_missing():
    assert roll_forward_fields_present({}) is False


def test_roll_forward_fields_present_zero_values_still_count_as_present():
    # 0 is a valid, meaningful value (e.g. no additions this year) — must not
    # be mistaken for "missing" the way None is.
    values = {
        "opening_wdv_paise": 0, "additions_paise": 0, "deletions_paise": 0,
        "book_depreciation_amount_paise": 0, "closing_wdv_paise": 0,
    }
    assert roll_forward_fields_present(values) is True


# --- detect_related_party_candidates ---------------------------------------

def test_detect_related_party_candidates_keyword_match():
    dataset = {"SALES": [_row({"party_name": "ABC Director Services"}, dataset_type="SALES")]}
    candidates = detect_related_party_candidates(dataset, "Acme Manufacturing Ltd")
    assert len(candidates) == 1
    assert "director" in candidates[0]._related_party_reason


def test_detect_related_party_candidates_name_similarity_match():
    dataset = {"SALES": [_row({"party_name": "Acme Manufacturing Limited"}, dataset_type="SALES")]}
    candidates = detect_related_party_candidates(dataset, "Acme Manufacturing Ltd")
    assert len(candidates) == 1
    assert "resembles" in candidates[0]._related_party_reason


def test_detect_related_party_candidates_no_match():
    dataset = {"SALES": [_row({"party_name": "Unrelated Traders Pvt Ltd"}, dataset_type="SALES")]}
    candidates = detect_related_party_candidates(dataset, "Acme Manufacturing Ltd")
    assert candidates == []


def test_detect_related_party_candidates_ignores_rows_without_party_name():
    dataset = {"SALES": [_row({"account_name": "Sales"}, dataset_type="SALES")]}
    candidates = detect_related_party_candidates(dataset, "Acme Manufacturing Ltd")
    assert candidates == []


def test_detect_related_party_candidates_scans_every_dataset_type():
    dataset = {
        "SALES": [_row({"party_name": "Normal Customer"}, dataset_type="SALES")],
        "PURCHASE": [_row({"party_name": "Promoter Holdings Pvt Ltd"}, dataset_type="PURCHASE")],
    }
    candidates = detect_related_party_candidates(dataset, "Acme Manufacturing Ltd")
    assert len(candidates) == 1
    assert candidates[0].dataset_type == "PURCHASE"


# --- net_balance_by_account (Stage 9, generalized from AS29-PROV-010) -------

def test_net_balance_by_account_matches_keyword_and_sums_credit_minus_debit():
    dataset = {"TB": [
        _row({"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 500000}, dataset_type="TB"),
        _row({"account_name": "Provision for Warranty", "debit_amount": 100000, "credit_amount": 0}, dataset_type="TB"),
        _row({"account_name": "Sales", "debit_amount": 0, "credit_amount": 200000}, dataset_type="TB"),
    ]}
    totals = net_balance_by_account(dataset, ("provision",))
    assert totals == {"Provision for Warranty": 400000}


def test_net_balance_by_account_respects_dataset_types_filter():
    dataset = {
        "TB": [_row({"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 500000}, dataset_type="TB")],
        "SALES": [_row({"account_name": "Provision for Warranty", "debit_amount": 0, "credit_amount": 999999}, dataset_type="SALES")],
    }
    totals = net_balance_by_account(dataset, ("provision",), dataset_types=("TB",))
    assert totals == {"Provision for Warranty": 500000}


def test_net_balance_by_account_no_match_returns_empty_dict():
    dataset = {"TB": [_row({"account_name": "Sales", "debit_amount": 0, "credit_amount": 200000}, dataset_type="TB")]}
    assert net_balance_by_account(dataset, ("provision",)) == {}


# --- reversal_movement_amount_and_pct ---------------------------------------

def test_reversal_movement_amount_and_pct_reduction():
    amount, pct = reversal_movement_amount_and_pct(prior_closing_paise=500000, current_net_movement_paise=-400000)
    assert amount == 400000
    assert pct == 80.0


def test_reversal_movement_amount_and_pct_increase_is_zero_amount():
    amount, pct = reversal_movement_amount_and_pct(prior_closing_paise=500000, current_net_movement_paise=100000)
    assert amount == 0
    assert pct == 0.0


def test_reversal_movement_amount_and_pct_zero_prior_closing_is_zero_pct():
    amount, pct = reversal_movement_amount_and_pct(prior_closing_paise=0, current_net_movement_paise=-100000)
    assert amount == 100000
    assert pct == 0.0


# --- is_flag_true / is_cash_payment_mode ------------------------------------

def test_is_flag_true_recognizes_common_truthy_strings():
    for value in ("Yes", "y", "TRUE", "1", "Manual", "manual entry", "Manually Posted"):
        assert is_flag_true(value) is True


def test_is_flag_true_rejects_falsy_or_blank_strings():
    for value in ("No", "n", "False", "0", "", None, "System"):
        assert is_flag_true(value) is False


def test_is_cash_payment_mode_matches_substring_case_insensitive():
    for value in ("Cash", "CASH", "Cash Payment", "petty cash"):
        assert is_cash_payment_mode(value) is True


def test_is_cash_payment_mode_rejects_non_cash_or_blank():
    for value in ("Cheque", "NEFT", "", None):
        assert is_cash_payment_mode(value) is False


# --- resolve_materiality_threshold_paise ------------------------------------

def test_resolve_materiality_threshold_prefers_entity_profile(monkeypatch):
    engagement = _Engagement()
    monkeypatch.setattr(
        shared_detectors.engagement_service, "get_entity_profile",
        lambda engagement_id: _EntityProfile(overall_materiality=2_000_000),
    )
    threshold, source = resolve_materiality_threshold_paise(engagement)
    assert threshold == 2_000_000
    assert "Overall Materiality" in source


def test_resolve_materiality_threshold_falls_back_when_no_profile(monkeypatch):
    engagement = _Engagement()
    monkeypatch.setattr(shared_detectors.engagement_service, "get_entity_profile", lambda engagement_id: None)
    threshold, source = resolve_materiality_threshold_paise(engagement)
    assert threshold == DEFAULT_MATERIALITY_FALLBACK_PAISE
    assert "FinSight default" in source


def test_resolve_materiality_threshold_falls_back_when_profile_has_no_materiality_set(monkeypatch):
    engagement = _Engagement()
    monkeypatch.setattr(
        shared_detectors.engagement_service, "get_entity_profile",
        lambda engagement_id: _EntityProfile(overall_materiality=None),
    )
    threshold, source = resolve_materiality_threshold_paise(engagement)
    assert threshold == DEFAULT_MATERIALITY_FALLBACK_PAISE


# --- find_next_year_dataset (Stage 9, mirror of find_prior_year_dataset) ----

def test_find_next_year_dataset_no_next_engagement_returns_none(monkeypatch):
    engagement = _Engagement(financial_year="2025-26")
    monkeypatch.setattr(shared_detectors.engagement_service, "find_engagement_by_entity_and_year", lambda entity, fy: None)
    assert shared_detectors.find_next_year_dataset(engagement) is None


def test_find_next_year_dataset_loads_dataset_for_next_engagement(monkeypatch):
    engagement = _Engagement(financial_year="2025-26")

    class _NextEngagement:
        engagement_id = 99

    monkeypatch.setattr(
        shared_detectors.engagement_service, "find_engagement_by_entity_and_year",
        lambda entity, fy: _NextEngagement() if fy == "2026-27" else None,
    )
    monkeypatch.setattr(shared_detectors.dataset_service, "load_engagement_dataset", lambda eid: {"JE": ["fake"]} if eid == 99 else {})
    result = shared_detectors.find_next_year_dataset(engagement)
    assert result == {"JE": ["fake"]}
