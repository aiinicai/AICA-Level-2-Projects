"""
Stage 5 — app/engagement/validation.py (form validation for Engagement
creation and the Entity Profile form).

Stage 5 round-2 correction #3 added here: Financial Year format
validation (Indian convention, e.g. "2025-26") — see
test_engagement_form_rejects_invalid_financial_year_formats below.

Ran for real under `pytest` in the delivery sandbox — see the Stage 5
delivery notes for the sandbox's real-Flask + shimmed-SQLAlchemy setup
(this file's own logic needs neither, but importing `app.*` runs
`app/__init__.py` first). Also runs unmodified once real dependencies
are installed per requirements.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.engagement.validation import validate_engagement_form, validate_entity_profile_form


def test_engagement_form_requires_both_fields():
    errors = validate_engagement_form({"entity_name": "", "financial_year": ""})
    assert set(errors) == {"entity_name", "financial_year"}


def test_engagement_form_valid():
    errors = validate_engagement_form({"entity_name": "Acme Ltd", "financial_year": "2025-26"})
    assert errors == {}


def test_engagement_form_accepts_a_century_rollover_financial_year():
    # FY 2099-2100 correctly abbreviates to "2099-00" under the Indian
    # convention — must not be rejected as if "00" were a typo for "99".
    errors = validate_engagement_form({"entity_name": "Acme Ltd", "financial_year": "2099-00"})
    assert errors == {}


def test_engagement_form_rejects_invalid_financial_year_formats():
    """Round-2 correction #3: simple format validation, not a
    financial-year rules engine — just the Indian "YYYY-YY" convention
    with the second year actually following the first."""
    invalid_formats = [
        "2026",           # single year, not a range
        "2025-2026",      # 4-digit second year, not 2-digit
        "25-26",          # 2-digit first year
        "2025/26",        # wrong separator
        "2025-27",        # second year doesn't follow the first
        "2025-25",        # second year doesn't follow the first
        "2026-2027",
        "not a year",
    ]
    for financial_year in invalid_formats:
        errors = validate_engagement_form({"entity_name": "Acme Ltd", "financial_year": financial_year})
        assert "financial_year" in errors, f"expected {financial_year!r} to be rejected"


VALID_PROFILE_FORM = {
    "entity_type": "Company",
    "industry": "Manufacturing",
    "is_listed": "on",
    "accounting_framework": "IND_AS",
    "is_gst_registered": "on",
    "statutory_audit_applicable": "on",
    "tax_audit_status": "APPLICABLE",
    "consolidated_fs_applicable": "on",
    "prior_year_data_available": "on",
    "turnover": "12,34,56,789",
    "overall_materiality": "500000",
    "performance_materiality": "375000",
    "clearly_trivial_threshold": "",
}


def test_entity_profile_form_valid():
    errors, cleaned = validate_entity_profile_form(VALID_PROFILE_FORM)
    assert errors == {}
    assert cleaned["is_listed"] is True
    assert cleaned["turnover"] == 12345678900
    assert cleaned["clearly_trivial_threshold"] is None
    assert cleaned["accounting_framework"] == "IND_AS"


def test_unchecked_checkboxes_become_false_not_missing():
    """HTML omits unchecked checkboxes from form data entirely — the
    form dict simulates that by the key being absent, not `""`."""
    form = {k: v for k, v in VALID_PROFILE_FORM.items() if k not in ("is_listed", "is_gst_registered")}
    errors, cleaned = validate_entity_profile_form(form)
    assert errors == {}
    assert cleaned["is_listed"] is False
    assert cleaned["is_gst_registered"] is False


def test_invalid_entity_type_and_framework_rejected():
    form = {**VALID_PROFILE_FORM, "entity_type": "Sole Trader", "accounting_framework": "GAAP"}
    errors, _ = validate_entity_profile_form(form)
    assert "entity_type" in errors
    assert "accounting_framework" in errors


def test_negative_money_field_rejected():
    form = {**VALID_PROFILE_FORM, "turnover": "-500"}
    errors, cleaned = validate_entity_profile_form(form)
    assert "turnover" in errors
    assert cleaned["turnover"] is None


def test_invalid_tax_audit_status_falls_back_to_requires_review():
    form = {**VALID_PROFILE_FORM, "tax_audit_status": "MAYBE"}
    errors, cleaned = validate_entity_profile_form(form)
    assert "tax_audit_status" in errors
    assert cleaned["tax_audit_status"] == "REQUIRES_REVIEW"
