"""
Form validation for Engagement creation and the Entity Profile form
(Stage 5). Pure functions — take a plain mapping (e.g. Flask's
`request.form`, or a plain dict in tests) and return
`(errors: dict[str, str], cleaned: dict)`. No Flask/SQLAlchemy
dependency, so these are directly unit-testable.

Enum whitelists here mirror the comments already on the approved
`app/models/engagement.py` fields exactly — nothing here invents a new
allowed value.
"""
from __future__ import annotations

import re

from app.utils.currency import CurrencyParseError, rupees_to_paise

ENTITY_TYPES = ("Company", "LLP", "Partnership", "Proprietorship", "Other")
ACCOUNTING_FRAMEWORKS = ("AS", "IND_AS")
TAX_AUDIT_STATUSES = ("APPLICABLE", "NOT_APPLICABLE", "REQUIRES_REVIEW")
APPLICABILITY_CONFIRM_STATUSES = ("APPLICABLE", "NOT_APPLICABLE", "REQUIRES_FURTHER_REVIEW")

_FINANCIAL_YEAR_HELP = 'e.g. "2025-26"'

# Stage 5 round-2 correction #3: simple format validation for the Indian
# financial-year convention (e.g. "2025-26"), deliberately kept as one
# regex + one arithmetic check — not a financial-year rules engine.
# Intentionally does NOT special-case a plausible calendar range (e.g.
# "reject before 2000" or "reject more than N years out") — that would
# be a policy/business-rule judgment call the standing "no silent
# architectural decisions" instruction says to flag, not assume; only
# the format itself (4-digit year, hyphen, the following 2-digit year)
# is validated here.
_FINANCIAL_YEAR_RE = re.compile(r"^(\d{4})-(\d{2})$")


def _is_valid_financial_year(value: str) -> bool:
    match = _FINANCIAL_YEAR_RE.match(value)
    if not match:
        return False
    start_year, end_suffix = match.group(1), match.group(2)
    expected_end_suffix = f"{(int(start_year) + 1) % 100:02d}"
    return end_suffix == expected_end_suffix


def validate_engagement_form(form: dict) -> dict[str, str]:
    """Validate the "new engagement" form. Returns an errors dict keyed
    by field name; empty dict means valid."""
    errors: dict[str, str] = {}

    entity_name = (form.get("entity_name") or "").strip()
    if not entity_name:
        errors["entity_name"] = "Entity name is required."
    elif len(entity_name) > 255:
        errors["entity_name"] = "Entity name must be 255 characters or fewer."

    financial_year = (form.get("financial_year") or "").strip()
    if not financial_year:
        errors["financial_year"] = f"Financial year is required ({_FINANCIAL_YEAR_HELP})."
    elif len(financial_year) > 20:
        errors["financial_year"] = "Financial year is too long."
    elif not _is_valid_financial_year(financial_year):
        errors["financial_year"] = f'Enter a valid Indian financial year, {_FINANCIAL_YEAR_HELP} (not "2026" or "2025-2026").'

    return errors


def _checkbox(form, name: str) -> bool:
    """HTML checkboxes only appear in form data when checked."""
    return form.get(name) is not None


def validate_entity_profile_form(form: dict) -> tuple[dict[str, str], dict]:
    """Validate + clean the Entity Profile form.

    Returns (errors, cleaned) — `cleaned` uses exactly the
    `EntityProfile` model's field names so callers can do
    `EntityProfile(engagement_id=..., **cleaned)` / bulk-setattr
    without any further translation. Money fields are converted from
    rupee input to integer paise here (the one approved place that
    conversion happens — see `app/utils/currency.py`).
    """
    errors: dict[str, str] = {}
    cleaned: dict = {}

    entity_type = (form.get("entity_type") or "").strip()
    if entity_type not in ENTITY_TYPES:
        errors["entity_type"] = f"Select a valid entity type ({', '.join(ENTITY_TYPES)})."
    cleaned["entity_type"] = entity_type or None

    industry = (form.get("industry") or "").strip()
    cleaned["industry"] = industry or None

    cleaned["is_listed"] = _checkbox(form, "is_listed")

    # Stage 18 (approved): auto-detect AS vs Ind AS from a plain Yes/No
    # answer ("Is this company required to follow Ind AS?"), while still
    # letting a professional set `accounting_framework` directly — that
    # explicit choice always wins over the auto-derived one. Any caller
    # that posts `accounting_framework` directly (every pre-Stage-18
    # form submission, including every existing test) is completely
    # unaffected by this block — it only fills the gap when
    # `accounting_framework` was left blank.
    ind_as_raw = (form.get("ind_as_mandated") or "").strip().lower()
    if ind_as_raw in ("yes", "true", "1"):
        ind_as_mandated = True
    elif ind_as_raw in ("no", "false", "0"):
        ind_as_mandated = False
    else:
        ind_as_mandated = None
    cleaned["ind_as_mandated"] = ind_as_mandated

    accounting_framework = (form.get("accounting_framework") or "").strip()
    if not accounting_framework and ind_as_mandated is not None:
        accounting_framework = "IND_AS" if ind_as_mandated else "AS"
    if accounting_framework not in ACCOUNTING_FRAMEWORKS:
        errors["accounting_framework"] = (
            "Answer \"Is this company required to follow Ind AS?\" (or set the accounting framework manually)."
        )
    cleaned["accounting_framework"] = accounting_framework or None

    cleaned["is_gst_registered"] = _checkbox(form, "is_gst_registered")
    cleaned["statutory_audit_applicable"] = _checkbox(form, "statutory_audit_applicable")

    tax_audit_status = (form.get("tax_audit_status") or "REQUIRES_REVIEW").strip()
    if tax_audit_status not in TAX_AUDIT_STATUSES:
        errors["tax_audit_status"] = "Select a valid tax audit status."
    cleaned["tax_audit_status"] = tax_audit_status if tax_audit_status in TAX_AUDIT_STATUSES else "REQUIRES_REVIEW"

    cleaned["consolidated_fs_applicable"] = _checkbox(form, "consolidated_fs_applicable")
    cleaned["prior_year_data_available"] = _checkbox(form, "prior_year_data_available")

    for money_field in ("turnover", "overall_materiality", "performance_materiality", "clearly_trivial_threshold"):
        raw = form.get(money_field)
        try:
            cleaned[money_field] = rupees_to_paise(raw)
        except CurrencyParseError:
            errors[money_field] = "Enter a valid, non-negative rupee amount (or leave blank)."
            cleaned[money_field] = None

    # entity_type/accounting_framework are the only fields a broken
    # applicability suggestion would silently degrade on if missing —
    # everything else is independently optional per Section 2.13.
    return errors, cleaned
