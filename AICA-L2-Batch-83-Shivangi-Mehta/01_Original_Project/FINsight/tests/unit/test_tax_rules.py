"""
Stage 10 — every executable tax rule module's evaluate() function,
tested directly against fabricated MappedRow/engagement objects (no DB,
no file upload pipeline — same style as tests/unit/test_audit_rules.py
and tests/unit/test_accounting_rules.py). Tax `evaluate()` is 2-arg
(engagement, dataset) — NOT framework-aware, same reasoning as Audit.
The full real pipeline (upload -> map -> validate -> review, plus the
Act-transition precondition) is covered separately in
tests/test_tax_http.py.

Uses only synthetic, fabricated data — never real client/financial
data, per the standing instruction.

Run with: pytest tests/unit/test_tax_rules.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.rules import wording
from app.rules.tax import (
    act_transition, tax_aud_014, tax_cash_001, tax_cash_002, tax_dep_005,
    tax_dis_006, tax_gst_009, tax_loan_003, tax_msme_013, tax_rpt_004,
)
from app.services.dataset_service import MappedRow


class _Engagement:
    def __init__(self, entity_name="Acme Manufacturing Ltd", financial_year="2025-26", engagement_id=1):
        self.entity_name = entity_name
        self.financial_year = financial_year
        self.engagement_id = engagement_id


def _row(dataset_type, values, file_id=1, row_index=0):
    return MappedRow(file_id=file_id, dataset_type=dataset_type, row_index=row_index, values=values)


ENGAGEMENT = _Engagement()


@pytest.fixture(autouse=True)
def _no_entity_profile(monkeypatch):
    """TAX-AUD-014 reads EntityProfile.turnover as a fallback — force it
    to None so tests never touch a real DB session, mirroring
    test_audit_rules.py's own autouse fixture for the same reason."""
    monkeypatch.setattr(tax_aud_014.engagement_service, "get_entity_profile", lambda engagement_id: None)


# --- act_transition.py -------------------------------------------------------

def test_is_old_act_fy_true_for_fy_2025_26():
    assert act_transition.is_old_act_fy("2025-26") is True


def test_is_old_act_fy_false_for_fy_2026_27():
    assert act_transition.is_old_act_fy("2026-27") is False


def test_is_old_act_fy_false_for_unparseable():
    assert act_transition.is_old_act_fy("not-a-year") is False


def test_describe_act_era_includes_ay_and_act():
    text = act_transition.describe_act_era("2025-26")
    assert "2025-26" in text
    assert "2026-27" in text  # the derived Assessment Year
    assert "Income-tax Act, 1961" in text


# --- TAX-CASH-001: Cash Expenditure Disallowance Screen ----------------------

def test_tax_cash_001_no_data_is_insufficient_data():
    outcome = tax_cash_001.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None
    assert outcome.rule_id == "TAX-CASH-001"


def test_tax_cash_001_flags_cash_payment_above_threshold():
    dataset = {"GL": [_row("GL", {
        "payment_mode": "Cash", "party_name": "Vendor A", "transaction_date": "2025-06-10",
        "debit_amount": 1_200_000, "credit_amount": 0,  # ₹12,000 > ₹10,000 threshold
    })]}
    outcome = tax_cash_001.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    finding = outcome.exceptions[0]
    assert finding.label == wording.POTENTIAL_TAX_ISSUE
    assert finding.threshold_used["threshold_is_statutory"] is True


def test_tax_cash_001_below_threshold_not_flagged():
    dataset = {"GL": [_row("GL", {
        "payment_mode": "Cash", "party_name": "Vendor A", "transaction_date": "2025-06-10",
        "debit_amount": 500_000, "credit_amount": 0,  # ₹5,000 < ₹10,000
    })]}
    outcome = tax_cash_001.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- Round 2 regression: TAX-CASH-001/002 direction (polarity) correction ---
# TAX-CASH-001 is an EXPENDITURE screen — it must read debit_amount only.
# TAX-CASH-002 is a RECEIPT screen — it must read credit_amount only.
# Previously both used max(debit_amount, credit_amount), which could count
# a receipt as an expenditure (or vice versa). These four tests prove the fix.

def test_tax_cash_001_detects_cash_expenditure():
    dataset = {"GL": [_row("GL", {
        "payment_mode": "Cash", "party_name": "Vendor A", "transaction_date": "2025-06-10",
        "debit_amount": 1_200_000, "credit_amount": 0,  # a genuine ₹12,000 cash PAYMENT
    })]}
    outcome = tax_cash_001.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].threshold_used["polarity"] == "debit_amount only (payment/outflow side)"


def test_tax_cash_001_does_not_flag_a_cash_receipt():
    # A RECEIPT (credit_amount only, debit_amount=0) must never be picked up by
    # the expenditure screen, even though it is well above the ₹10,000 threshold.
    dataset = {"GL": [_row("GL", {
        "payment_mode": "Cash", "party_name": "Client X", "transaction_date": "2025-06-10",
        "debit_amount": 0, "credit_amount": 1_200_000,  # a ₹12,000 cash RECEIPT, not a payment
    })]}
    outcome = tax_cash_001.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_tax_cash_002_detects_cash_receipt():
    dataset = {"GL": [_row("GL", {
        "payment_mode": "Cash", "party_name": "Client X", "transaction_date": "2025-07-01",
        "debit_amount": 0, "credit_amount": 25_000_000,  # a genuine ₹2,50,000 cash RECEIPT
    })]}
    outcome = tax_cash_002.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].threshold_used["polarity"] == "credit_amount only (receipt/inflow side)"


def test_tax_cash_002_does_not_flag_a_cash_payment():
    # A PAYMENT (debit_amount only, credit_amount=0) must never be picked up by
    # the receipt screen, even though it is well above the ₹2,00,000 threshold.
    dataset = {"GL": [_row("GL", {
        "payment_mode": "Cash", "party_name": "Vendor A", "transaction_date": "2025-07-01",
        "debit_amount": 25_000_000, "credit_amount": 0,  # a ₹2,50,000 cash PAYMENT, not a receipt
    })]}
    outcome = tax_cash_002.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_tax_cash_001_discloses_gl_and_bank_double_counting():
    # Same counterparty/day, one row from GL and one from BANK — FinSight cannot
    # tell whether these are the same underlying payment recorded twice, so the
    # finding must disclose that rather than silently aggregating as independent.
    dataset = {
        "GL": [_row("GL", {
            "payment_mode": "Cash", "party_name": "Vendor A", "transaction_date": "2025-06-10",
            "debit_amount": 700_000, "credit_amount": 0,
        }, file_id=1)],
        "BANK": [_row("BANK", {
            "payment_mode": "Cash", "description": "Vendor A", "transaction_date": "2025-06-10",
            "debit_amount": 700_000, "credit_amount": 0,
        }, file_id=2)],
    }
    outcome = tax_cash_001.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    finding = outcome.exceptions[0]
    assert finding.threshold_used["cross_source_deduplicated"] is False
    assert set(finding.threshold_used["sources_contributing"]) == {"GL", "BANK"}
    assert "recorded twice" in finding.explanation


def test_tax_cash_001_single_source_does_not_show_dedup_warning():
    dataset = {"GL": [_row("GL", {
        "payment_mode": "Cash", "party_name": "Vendor A", "transaction_date": "2025-06-10",
        "debit_amount": 1_200_000, "credit_amount": 0,
    })]}
    outcome = tax_cash_001.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert "recorded twice" not in outcome.exceptions[0].explanation


# --- Round 3 explicit boundary tests: TAX-CASH-001 ---------------------------
# Section 40A(3) is triggered only where the aggregate EXCEEDS ₹10,000 — an
# aggregate of exactly ₹10,000 must NOT be flagged; ₹10,000.01 or higher must.

def test_tax_cash_001_boundary_1_paisa_under_10000_not_flagged():
    dataset = {"GL": [_row("GL", {
        "payment_mode": "Cash", "party_name": "Vendor A", "transaction_date": "2025-06-10",
        "debit_amount": 999_999, "credit_amount": 0,  # ₹9,999.99
    })]}
    outcome = tax_cash_001.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_tax_cash_001_boundary_exactly_10000_not_flagged():
    dataset = {"GL": [_row("GL", {
        "payment_mode": "Cash", "party_name": "Vendor A", "transaction_date": "2025-06-10",
        "debit_amount": 1_000_000, "credit_amount": 0,  # exactly ₹10,000
    })]}
    outcome = tax_cash_001.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_tax_cash_001_boundary_1_paisa_over_10000_is_flagged():
    dataset = {"GL": [_row("GL", {
        "payment_mode": "Cash", "party_name": "Vendor A", "transaction_date": "2025-06-10",
        "debit_amount": 1_000_001, "credit_amount": 0,  # ₹10,000.01
    })]}
    outcome = tax_cash_001.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].threshold_used["threshold_comparison_operator"] == "strictly greater than (exceeds)"


# --- TAX-CASH-002: Large Cash Receipt Restriction Screen ---------------------

def test_tax_cash_002_flags_single_transaction_above_threshold():
    dataset = {"GL": [_row("GL", {
        "payment_mode": "Cash", "party_name": "Client X", "transaction_date": "2025-07-01",
        "debit_amount": 0, "credit_amount": 25_000_000,  # ₹2,50,000 > ₹2,00,000
    })]}
    outcome = tax_cash_002.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].threshold_used["limb_b_single_transaction"] is True


def test_tax_cash_002_no_data_is_insufficient_data():
    outcome = tax_cash_002.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


def test_tax_cash_002_discloses_multi_source_double_counting():
    dataset = {
        "GL": [_row("GL", {
            "payment_mode": "Cash", "party_name": "Client X", "transaction_date": "2025-07-01",
            "debit_amount": 0, "credit_amount": 15_000_000,
        }, file_id=1)],
        "SALES": [_row("SALES", {
            "payment_mode": "Cash", "party_name": "Client X", "transaction_date": "2025-07-01",
            "debit_amount": 0, "credit_amount": 15_000_000,
        }, file_id=2)],
    }
    outcome = tax_cash_002.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    finding = outcome.exceptions[0]
    assert finding.threshold_used["cross_source_deduplicated"] is False
    assert set(finding.threshold_used["sources_contributing"]) == {"GL", "SALES"}
    assert "recorded twice" in finding.explanation


# --- TAX-LOAN-003: Cash Loan/Deposit Acceptance & Repayment Restriction ------

def test_tax_loan_003_flags_loan_keyword_above_threshold():
    dataset = {"GL": [_row("GL", {
        "account_name": "Unsecured Loan from Director", "description": "",
        "debit_amount": 0, "credit_amount": 3_000_000,  # ₹30,000 > ₹20,000
    })]}
    outcome = tax_loan_003.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert "acceptance" in outcome.exceptions[0].trigger_condition.lower()


def test_tax_loan_003_non_loan_account_not_flagged():
    dataset = {"GL": [_row("GL", {
        "account_name": "Office Rent", "description": "",
        "debit_amount": 3_000_000, "credit_amount": 0,
    })]}
    outcome = tax_loan_003.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- Round 2 regression: TAX-LOAN-003 Payment Mode now decides whether to
# flag at all, not just annotate the finding. ---------------------------------

def test_tax_loan_003_cash_mode_is_flagged_as_potential_tax_issue():
    dataset = {"GL": [_row("GL", {
        "account_name": "Unsecured Loan from Director", "description": "", "payment_mode": "Cash",
        "debit_amount": 0, "credit_amount": 3_000_000,
    })]}
    outcome = tax_loan_003.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    finding = outcome.exceptions[0]
    assert finding.label == wording.POTENTIAL_TAX_ISSUE
    assert finding.threshold_used["payment_mode_classification"] == "cash"


def test_tax_loan_003_clearly_permitted_electronic_mode_is_not_flagged():
    dataset = {"GL": [_row("GL", {
        "account_name": "Unsecured Loan from Director", "description": "", "payment_mode": "NEFT",
        "debit_amount": 0, "credit_amount": 3_000_000,
    })]}
    outcome = tax_loan_003.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_tax_loan_003_account_payee_cheque_is_not_flagged():
    dataset = {"GL": [_row("GL", {
        "account_name": "Unsecured Loan from Director", "description": "", "payment_mode": "Account Payee Cheque",
        "debit_amount": 0, "credit_amount": 3_000_000,
    })]}
    outcome = tax_loan_003.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_tax_loan_003_unavailable_mode_is_review_required():
    # No payment_mode key at all — GL carries it, but it's simply not populated here.
    dataset = {"GL": [_row("GL", {
        "account_name": "Unsecured Loan from Director", "description": "",
        "debit_amount": 0, "credit_amount": 3_000_000,
    })]}
    outcome = tax_loan_003.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    finding = outcome.exceptions[0]
    assert finding.label == wording.TAX_REVIEW_REQUIRED
    assert finding.threshold_used["payment_mode_classification"] == "unknown"


def test_tax_loan_003_ambiguous_mode_is_review_required():
    # A bare "Cheque" — could be bearer (not exempt) or account-payee (exempt);
    # FinSight cannot tell, so it must ask rather than assume either way.
    dataset = {"GL": [_row("GL", {
        "account_name": "Unsecured Loan from Director", "description": "", "payment_mode": "Cheque",
        "debit_amount": 0, "credit_amount": 3_000_000,
    })]}
    outcome = tax_loan_003.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    finding = outcome.exceptions[0]
    assert finding.label == wording.TAX_REVIEW_REQUIRED
    assert finding.threshold_used["payment_mode_classification"] == "ambiguous"


def test_tax_loan_003_jead_ap_ar_have_no_payment_mode_field_and_are_review_required():
    # JE/AP/AR carry no Payment Mode field at all (FILE_TYPE_FIELD_SETS) — every
    # match from these sources should land in the "unknown" bucket, same as GL
    # rows where the field simply wasn't populated.
    dataset = {"AP": [_row("AP", {
        "account_name": "Unsecured Loan from Director", "description": "",
        "debit_amount": 0, "credit_amount": 3_000_000,
    })]}
    outcome = tax_loan_003.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].label == wording.TAX_REVIEW_REQUIRED


# --- TAX-DIS-006: Statutory Dues Payment-Basis Timing Test -------------------

def test_tax_dis_006_flags_unpaid_statutory_due():
    dataset = {"GL": [_row("GL", {
        "account_name": "Provident Fund Payable", "description": "",
        "debit_amount": 0, "credit_amount": 500_000,  # ₹5,000 net credit, unpaid
    })]}
    outcome = tax_dis_006.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].label == wording.TAX_REVIEW_REQUIRED


def test_tax_dis_006_fully_paid_not_flagged():
    dataset = {"GL": [
        _row("GL", {"account_name": "Provident Fund Payable", "description": "", "debit_amount": 0, "credit_amount": 500_000}, row_index=0),
        _row("GL", {"account_name": "Provident Fund Payable", "description": "", "debit_amount": 500_000, "credit_amount": 0}, row_index=1),
    ]}
    outcome = tax_dis_006.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


# --- TAX-AUD-014: Tax Audit Applicability / Turnover-Threshold Test ----------

def test_tax_aud_014_flags_turnover_crossing_threshold():
    # Round 3: crossing BOTH the business and professional thresholds now
    # produces two INDEPENDENT findings (see the split-finding design below),
    # not one combined finding.
    dataset = {"SALES": [_row("SALES", {
        "credit_amount": 12_000_000_000, "debit_amount": 0,  # ₹12 crore — crosses both base and professional
    })]}
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 2
    business = next(f for f in outcome.exceptions if f.label == wording.TAX_REVIEW_REQUIRED)
    professional = next(f for f in outcome.exceptions if f.label == wording.TAX_AUDIT_APPLICABILITY_REVIEW_REQUIRED)
    assert business.threshold_used["crosses_business_threshold"] is True
    assert "computed from the validated Sales Register" in business.explanation
    assert professional.threshold_used["crosses_professional_threshold"] is True
    assert "computed from the validated Sales Register" in professional.explanation


def test_tax_aud_014_below_threshold_not_flagged():
    dataset = {"SALES": [_row("SALES", {"credit_amount": 10_000_000, "debit_amount": 0})]}  # ₹1 lakh
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_tax_aud_014_no_data_is_insufficient_data():
    outcome = tax_aud_014.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


# --- Round 2 regression: TAX-AUD-014 cash-receipt/cash-payment percentages
# must be computed SEPARATELY, never as one blended figure. Turnover in most
# scenarios below is set to ₹1,00,00,001 (the base ₹1cr threshold plus ₹1) so
# that it STRICTLY EXCEEDS the base threshold under the Round 3 ">" operator
# (a turnover of exactly ₹1cr no longer crosses under the corrected "exceeds"
# semantics — see the boundary tests further below). Because this turnover
# also always exceeds the ₹50 lakh professional threshold, the professional
# finding (wording.TAX_AUDIT_APPLICABILITY_REVIEW_REQUIRED) is ALWAYS present
# too, independent of the business one (Round 3's split-finding design) — the
# tests below look up findings BY LABEL rather than by list position, and a
# scenario where the enhanced ₹10cr threshold applies (so the base threshold
# is never crossed) correctly produces NO business finding at all, only the
# professional one.

def _aud014_dataset(receipt_cash_paise, receipt_electronic_paise, payment_cash_paise, payment_electronic_paise):
    rows = {"SALES": [], "GL": []}
    if receipt_cash_paise:
        rows["SALES"].append(_row("SALES", {"credit_amount": receipt_cash_paise, "debit_amount": 0, "payment_mode": "Cash"}, row_index=0))
    if receipt_electronic_paise:
        rows["SALES"].append(_row("SALES", {"credit_amount": receipt_electronic_paise, "debit_amount": 0, "payment_mode": "NEFT"}, row_index=1))
    if payment_cash_paise:
        rows["GL"].append(_row("GL", {"debit_amount": payment_cash_paise, "credit_amount": 0, "payment_mode": "Cash"}, row_index=0))
    if payment_electronic_paise:
        rows["GL"].append(_row("GL", {"debit_amount": payment_electronic_paise, "credit_amount": 0, "payment_mode": "NEFT"}, row_index=1))
    return rows


def test_tax_aud_014_both_receipts_and_payments_at_or_under_5_percent_applies_enhanced_threshold():
    # Receipts: 0% cash. Payments: 0% cash. Both conditions satisfied -> enhanced
    # ₹10cr threshold applies -> turnover of exactly ₹1cr does NOT cross it, so NO
    # business finding is raised at all (Round 3 split-finding design). The
    # professional finding is still raised (₹1cr turnover > ₹50L professional
    # threshold), and carries the shared receipt/payment-condition fields.
    dataset = _aud014_dataset(
        receipt_cash_paise=0, receipt_electronic_paise=1_000_000_000,
        payment_cash_paise=0, payment_electronic_paise=100_000_000,
    )
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    finding = outcome.exceptions[0]
    assert finding.label == wording.TAX_AUDIT_APPLICABILITY_REVIEW_REQUIRED
    tu = finding.threshold_used
    assert tu["receipt_condition_satisfied"] is True
    assert tu["payment_condition_satisfied"] is True
    assert tu["enhanced_threshold_applied"] is True
    assert "crosses_business_threshold" not in tu  # no business finding was raised at all


def test_tax_aud_014_receipts_ok_but_payments_over_5_percent_uses_base_threshold():
    # Receipts: 0% cash (satisfied). Payments: 10% cash (NOT satisfied).
    # Enhanced threshold must NOT apply -> base ₹1cr threshold -> turnover of
    # ₹1,00,00,001 (₹1cr + ₹1) strictly exceeds it.
    dataset = _aud014_dataset(
        receipt_cash_paise=0, receipt_electronic_paise=1_000_000_100,
        payment_cash_paise=10_000_000, payment_electronic_paise=90_000_000,
    )
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    business = next(f for f in outcome.exceptions if f.label == wording.TAX_REVIEW_REQUIRED)
    tu = business.threshold_used
    assert tu["receipt_condition_satisfied"] is True
    assert tu["payment_condition_satisfied"] is False
    assert tu["enhanced_threshold_applied"] is False
    assert tu["crosses_business_threshold"] is True  # base ₹1cr threshold used, turnover exceeds it
    assert tu["cash_payment_percentage"] == 10.0


def test_tax_aud_014_payments_ok_but_receipts_over_5_percent_uses_base_threshold():
    # Receipts: ~10% cash (NOT satisfied). Payments: 0% cash (satisfied).
    # A single blended percentage would have averaged this away — it must not.
    # Electronic receipts bumped by ₹1 so turnover (₹1,00,00,001) strictly
    # exceeds the ₹1cr base threshold under the Round 3 ">" operator.
    dataset = _aud014_dataset(
        receipt_cash_paise=100_000_000, receipt_electronic_paise=900_000_100,
        payment_cash_paise=0, payment_electronic_paise=100_000_000,
    )
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    business = next(f for f in outcome.exceptions if f.label == wording.TAX_REVIEW_REQUIRED)
    tu = business.threshold_used
    assert tu["receipt_condition_satisfied"] is False
    assert tu["payment_condition_satisfied"] is True
    assert tu["enhanced_threshold_applied"] is False
    assert tu["crosses_business_threshold"] is True
    assert tu["cash_receipt_percentage"] == 10.0


def test_tax_aud_014_both_receipts_and_payments_over_5_percent_uses_base_threshold():
    # Electronic receipts bumped by ₹1 so turnover strictly exceeds ₹1cr.
    dataset = _aud014_dataset(
        receipt_cash_paise=100_000_000, receipt_electronic_paise=900_000_100,
        payment_cash_paise=10_000_000, payment_electronic_paise=90_000_000,
    )
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    business = next(f for f in outcome.exceptions if f.label == wording.TAX_REVIEW_REQUIRED)
    tu = business.threshold_used
    assert tu["receipt_condition_satisfied"] is False
    assert tu["payment_condition_satisfied"] is False
    assert tu["enhanced_threshold_applied"] is False
    assert tu["crosses_business_threshold"] is True


def test_tax_aud_014_no_payment_side_data_does_not_assume_enhanced_threshold():
    # Receipts data exists (0% cash, would satisfy the condition on its own),
    # but there is NO payment-side data at all — FinSight must not assume the
    # payment condition is satisfied just because it can't be measured.
    # Electronic receipts bumped by ₹1 so turnover strictly exceeds ₹1cr.
    dataset = _aud014_dataset(
        receipt_cash_paise=0, receipt_electronic_paise=1_000_000_100,
        payment_cash_paise=0, payment_electronic_paise=0,
    )
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    business = next(f for f in outcome.exceptions if f.label == wording.TAX_REVIEW_REQUIRED)
    tu = business.threshold_used
    assert tu["cash_payment_percentage"] is None
    assert tu["payment_condition_satisfied"] is False
    assert tu["enhanced_threshold_applied"] is False
    assert tu["crosses_business_threshold"] is True
    assert "insufficient data" in business.explanation.lower()


def test_tax_aud_014_professional_75l_figure_is_informational_only():
    # A ₹75 lakh figure should never change the ₹50 lakh professional comparison
    # this rule actually makes — it's Section 44ADA's own ceiling, not 44AB(b)'s.
    # Turnover here is exactly ₹1cr (enhanced threshold applies, so no business
    # finding is raised) — the sole finding is the professional one, labeled
    # wording.TAX_AUDIT_APPLICABILITY_REVIEW_REQUIRED (Round 3).
    dataset = _aud014_dataset(
        receipt_cash_paise=0, receipt_electronic_paise=1_000_000_000,
        payment_cash_paise=0, payment_electronic_paise=100_000_000,
    )
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    finding = outcome.exceptions[0]
    assert finding.label == wording.TAX_AUDIT_APPLICABILITY_REVIEW_REQUIRED
    tu = finding.threshold_used
    assert tu["professional_threshold_paise"] == 500_000_000  # ₹50 lakh, unchanged
    assert tu["professional_44ada_presumptive_enhanced_threshold_paise"] == 750_000_000  # ₹75 lakh, disclosed
    assert tu["professional_44ada_applied_to_crosses_professional"] is False
    assert tu["crosses_professional_threshold"] is True  # turnover ₹1cr > ₹50L regardless of the ₹75L figure


# --- Round 3 explicit boundary tests: TAX-AUD-014 ----------------------------
# "Exceeds" is strict (">"): a figure exactly equal to a threshold must NOT
# cross it; a figure ₹1 above it must. Business-threshold boundaries use a
# plain SALES-only dataset (no GL/payment-mode data at all, so payments are
# not determinable, the enhanced threshold never applies, and the base ₹1cr
# threshold governs) except the ₹10cr set, which needs the enhanced threshold
# actually applied to be a meaningful test of ITS OWN boundary, so it reuses
# _aud014_dataset() with both cash percentages at 0%. Findings are looked up
# by label since the professional finding is independent and may or may not
# also be present depending on whether turnover also exceeds ₹50 lakh.

def _business_finding(outcome):
    return next((f for f in outcome.exceptions if f.label == wording.TAX_REVIEW_REQUIRED), None)


def _professional_finding(outcome):
    return next((f for f in outcome.exceptions if f.label == wording.TAX_AUDIT_APPLICABILITY_REVIEW_REQUIRED), None)


def test_tax_aud_014_business_base_threshold_exactly_1cr_does_not_cross():
    dataset = {"SALES": [_row("SALES", {"credit_amount": 1_000_000_000, "debit_amount": 0})]}  # exactly ₹1cr
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    assert _business_finding(outcome) is None  # exactly at the threshold must NOT cross it
    assert _professional_finding(outcome) is not None  # ₹1cr still exceeds the ₹50L professional threshold


def test_tax_aud_014_business_base_threshold_1_rupee_under_does_not_cross():
    dataset = {"SALES": [_row("SALES", {"credit_amount": 999_999_900, "debit_amount": 0})]}  # ₹1cr - ₹1
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    assert _business_finding(outcome) is None
    assert _professional_finding(outcome) is not None


def test_tax_aud_014_business_base_threshold_1_rupee_over_crosses():
    dataset = {"SALES": [_row("SALES", {"credit_amount": 1_000_000_100, "debit_amount": 0})]}  # ₹1cr + ₹1
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    business = _business_finding(outcome)
    assert business is not None
    assert business.threshold_used["crosses_business_threshold"] is True


def test_tax_aud_014_business_enhanced_threshold_exactly_10cr_does_not_cross():
    dataset = _aud014_dataset(
        receipt_cash_paise=0, receipt_electronic_paise=10_000_000_000,  # exactly ₹10cr, 0% cash both sides
        payment_cash_paise=0, payment_electronic_paise=100_000_000,
    )
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    assert _business_finding(outcome) is None  # enhanced threshold applies; exactly ₹10cr must NOT cross it
    assert _professional_finding(outcome) is not None


def test_tax_aud_014_business_enhanced_threshold_1_rupee_under_does_not_cross():
    dataset = _aud014_dataset(
        receipt_cash_paise=0, receipt_electronic_paise=9_999_999_900,  # ₹10cr - ₹1
        payment_cash_paise=0, payment_electronic_paise=100_000_000,
    )
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    assert _business_finding(outcome) is None
    assert _professional_finding(outcome) is not None


def test_tax_aud_014_business_enhanced_threshold_1_rupee_over_crosses():
    dataset = _aud014_dataset(
        receipt_cash_paise=0, receipt_electronic_paise=10_000_000_100,  # ₹10cr + ₹1
        payment_cash_paise=0, payment_electronic_paise=100_000_000,
    )
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    business = _business_finding(outcome)
    assert business is not None
    assert business.threshold_used["enhanced_threshold_applied"] is True
    assert business.threshold_used["crosses_business_threshold"] is True


def test_tax_aud_014_professional_threshold_exactly_50l_does_not_cross():
    dataset = {"SALES": [_row("SALES", {"credit_amount": 500_000_000, "debit_amount": 0})]}  # exactly ₹50L
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []  # below business base threshold and exactly at professional threshold


def test_tax_aud_014_professional_threshold_1_rupee_under_does_not_cross():
    dataset = {"SALES": [_row("SALES", {"credit_amount": 499_999_900, "debit_amount": 0})]}  # ₹50L - ₹1
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_tax_aud_014_professional_threshold_1_rupee_over_crosses():
    dataset = {"SALES": [_row("SALES", {"credit_amount": 500_000_100, "debit_amount": 0})]}  # ₹50L + ₹1
    outcome = tax_aud_014.evaluate(ENGAGEMENT, dataset)
    assert _business_finding(outcome) is None  # still well under the ₹1cr base threshold
    professional = _professional_finding(outcome)
    assert professional is not None
    assert professional.threshold_used["crosses_professional_threshold"] is True


# --- TAX-DEP-005: Tax Depreciation Consistency Review ------------------------

def test_tax_dep_005_flags_variance():
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {
        "asset_description": "Factory Machine", "tax_block_of_asset": "Plant & Machinery",
        "tax_depreciation_rate": 15.0, "opening_wdv_paise": 10_000_000, "additions_paise": 0,
        "deletions_paise": 0, "closing_wdv_paise": 10_000_000,  # no depreciation applied — a variance
        "date_put_to_use": None,
    })]}
    outcome = tax_dep_005.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].threshold_used["recorded_rate_independently_verified"] is False


def test_tax_dep_005_no_variance_not_flagged():
    # opening 10,000,000 @ 15% -> expected dep 1,500,000 -> expected closing 8,500,000
    dataset = {"FIXED_ASSETS": [_row("FIXED_ASSETS", {
        "asset_description": "Factory Machine", "tax_block_of_asset": "Plant & Machinery",
        "tax_depreciation_rate": 15.0, "opening_wdv_paise": 10_000_000, "additions_paise": 0,
        "deletions_paise": 0, "closing_wdv_paise": 8_500_000, "date_put_to_use": None,
    })]}
    outcome = tax_dep_005.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_tax_dep_005_no_data_is_insufficient_data():
    outcome = tax_dep_005.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


# --- TAX-RPT-004: Related-Party Payment Reasonableness Screen ----------------

def test_tax_rpt_004_flags_expense_side_related_party():
    dataset = {"GL": [_row("GL", {
        "party_name": "Director Holdings Pvt Ltd", "debit_amount": 200_000, "credit_amount": 0,
    })]}
    outcome = tax_rpt_004.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].threshold_used["candidate_only_not_confirmed"] is True


def test_tax_rpt_004_receipt_side_not_flagged():
    dataset = {"GL": [_row("GL", {
        "party_name": "Director Holdings Pvt Ltd", "debit_amount": 0, "credit_amount": 200_000,
    })]}
    outcome = tax_rpt_004.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_tax_rpt_004_no_party_name_is_insufficient_data():
    outcome = tax_rpt_004.evaluate(ENGAGEMENT, {"GL": [_row("GL", {"debit_amount": 100})]})
    assert outcome.insufficient_data_reason is not None


# --- TAX-GST-009: GST Invoice Reconciliation ---------------------------------

def test_tax_gst_009_flags_mismatched_invoice():
    dataset = {
        "SALES": [_row("SALES", {"invoice_number": "INV001", "taxable_value_paise": 10_000_000, "cgst_paise": 900_000, "sgst_paise": 900_000, "igst_paise": 0}, file_id=1)],
        "GST": [_row("GST", {"invoice_number": "INV001", "taxable_value_paise": 9_000_000, "cgst_paise": 810_000, "sgst_paise": 810_000, "igst_paise": 0}, file_id=2)],
    }
    outcome = tax_gst_009.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    assert outcome.exceptions[0].threshold_used["taxable_value_mismatch"] is True


def test_tax_gst_009_matching_invoice_not_flagged():
    dataset = {
        "SALES": [_row("SALES", {"invoice_number": "INV001", "taxable_value_paise": 10_000_000, "cgst_paise": 900_000, "sgst_paise": 900_000, "igst_paise": 0}, file_id=1)],
        "GST": [_row("GST", {"invoice_number": "INV001", "taxable_value_paise": 10_000_000, "cgst_paise": 900_000, "sgst_paise": 900_000, "igst_paise": 0}, file_id=2)],
    }
    outcome = tax_gst_009.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_tax_gst_009_single_source_invoice_is_insufficient_data():
    dataset = {"SALES": [_row("SALES", {"invoice_number": "INV001", "taxable_value_paise": 10_000_000})]}
    outcome = tax_gst_009.evaluate(ENGAGEMENT, dataset)
    assert outcome.insufficient_data_reason is not None


# --- TAX-MSME-013: MSME Delayed-Payment Review Screen ------------------------

def test_tax_msme_013_flags_aged_payable_with_msme_label():
    dataset = {"AP": [_row("AP", {
        "party_name": "Small Supplier Co", "transaction_date": "2025-04-01",
        "debit_amount": 0, "credit_amount": 200_000,  # ₹2,000, aged ~365 days by FY end
    })]}
    outcome = tax_msme_013.evaluate(ENGAGEMENT, dataset)
    assert len(outcome.exceptions) == 1
    finding = outcome.exceptions[0]
    assert finding.label == wording.POTENTIAL_MSME_PAYMENT_REVIEW
    assert finding.threshold_used["msme_registration_status_known"] is False
    assert finding.threshold_used["candidate_only_not_a_disallowance"] is True
    assert "does NOT state that a Section 43B(h) disallowance exists" in finding.explanation


def test_tax_msme_013_recently_paid_not_flagged():
    dataset = {"AP": [_row("AP", {
        "party_name": "Small Supplier Co", "transaction_date": "2026-03-25",  # 6 days before FY end
        "debit_amount": 0, "credit_amount": 200_000,
    })]}
    outcome = tax_msme_013.evaluate(ENGAGEMENT, dataset)
    assert outcome.exceptions == []


def test_tax_msme_013_no_data_is_insufficient_data():
    outcome = tax_msme_013.evaluate(ENGAGEMENT, {})
    assert outcome.insufficient_data_reason is not None


# --- Structural: every executable rule's every ExceptionDraft label is TAX ---

@pytest.mark.parametrize("module,dataset", [
    (tax_cash_001, {"GL": [_row("GL", {"payment_mode": "Cash", "party_name": "V", "transaction_date": "2025-06-10", "debit_amount": 1_200_000, "credit_amount": 0})]}),
    (tax_cash_002, {"GL": [_row("GL", {"payment_mode": "Cash", "party_name": "C", "transaction_date": "2025-07-01", "debit_amount": 0, "credit_amount": 25_000_000})]}),
    (tax_loan_003, {"GL": [_row("GL", {"account_name": "Unsecured Loan from Director", "description": "", "debit_amount": 0, "credit_amount": 3_000_000})]}),
    (tax_dis_006, {"GL": [_row("GL", {"account_name": "Provident Fund Payable", "description": "", "debit_amount": 0, "credit_amount": 500_000})]}),
    (tax_rpt_004, {"GL": [_row("GL", {"party_name": "Director Holdings Pvt Ltd", "debit_amount": 200_000, "credit_amount": 0})]}),
])
def test_every_finding_uses_a_tax_label(module, dataset):
    outcome = module.evaluate(ENGAGEMENT, dataset)
    for finding in outcome.exceptions:
        assert finding.label in wording.TAX_LABELS
