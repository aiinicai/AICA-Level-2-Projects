"""
Applicability suggestion engine (Stage 5).

Deliberately NOT placed under `app/rules/` — that package is reserved
for the four approved rule packs (accounting/audit/tax/sebi) that
produce exceptions against uploaded transaction data (Stages 8-11).
This module does something narrower and earlier in the workflow: it
turns Entity Profile facts the user has already entered into a
*system-suggested* value for the `applicability` table (Blueprint
Section 2.11), which the user then confirms or overrides on the
Applicability Matrix screen.

Design decision (flagged in the Stage 5 scope note, not a schema/
architecture change): every suggestion here is a MECHANICAL ECHO of an
already-entered Entity Profile field — never a computed statutory
threshold (turnover limits, net-worth limits, etc.). Tax/SEBI numeric
thresholds have not been through the Section 5/6 verification register,
so this module must not encode any of its own. This mirrors the
original spec's own example Applicability Matrix, whose "Reason" column
says "Entity profile" for nearly every row.

Pure functions only — no SQLAlchemy, no Flask — so this is directly
unit-testable without any of the sandbox's dependency constraints.

Stage 5 round-2 corrections (post-approval review):
1. Audit Review's suggestion no longer mirrors `statutory_audit_
   applicable` — Statutory Audit Applicability (an entity fact) and
   Audit Review (FinSight's own analytical capability) are different
   concepts; see `_suggest_audit_review`.
2. Every suggestion now has a matching `entity_profile_input()` label
   and a `suggestion_display()` wording, so the UI can show Entity
   Profile Input / System Suggestion / Professional Confirmation as
   three clearly distinct lines instead of one sentence that could be
   mistaken for a conclusion.
"""
from __future__ import annotations

# The six areas from the original spec's example Applicability Matrix
# (Section 6). Order matters only for consistent display; do not
# reorder without checking templates that iterate this list.
AREAS: tuple[str, ...] = (
    "Accounting Standards",
    "Ind AS",
    "Audit Review",
    "Income Tax Review",
    "Tax Audit Review",
    "SEBI/LODR",
)

# system_suggested_status values (Blueprint Section 2.11's own enum).
YES = "YES"
NO = "NO"
REVIEW_REQUIRED = "REVIEW_REQUIRED"


def _to_bool_or_none(value):
    """Normalize a boolean-ish Entity Profile field before comparing it.

    Every boolean check in this module compares against `True`/`False`
    by IDENTITY further down (`is True`/`is False`), deliberately, so
    that "genuinely unknown" (`None` — profile not yet saved) reads as
    a third state rather than silently defaulting to falsy. That only
    stays correct if the value is actually a Python `bool` by the time
    it gets there. `is_listed`/`statutory_audit_applicable` normally
    arrive as real `bool` (real SQLAlchemy's `Boolean` type coerces
    SQLite's stored 0/1 back to `False`/`True` on read) — but nothing
    stops a raw integer 0/1 from reaching this module some other way
    (a lower-level query, a differently-sourced dict), and `1 is True`
    is `False` in Python, which would silently misclassify a listed
    entity as unlisted. Normalizing here once, rather than trusting
    every call site to pass a real bool, is the defensive fix.
    """
    return None if value is None else bool(value)


def _display_bool(value: bool | None) -> str:
    value = _to_bool_or_none(value)
    if value is None:
        return "Not yet recorded"
    return "Yes" if value else "No"


def _suggest_accounting_standards(_facts: dict) -> tuple[str, str]:
    return YES, "Every engagement requires an accounting standards review."


def _suggest_ind_as(facts: dict) -> tuple[str, str]:
    framework = facts.get("accounting_framework")
    if framework == "IND_AS":
        return YES, "Entity profile: accounting framework recorded as Ind AS."
    if framework == "AS":
        return NO, "Entity profile: accounting framework recorded as AS (not Ind AS)."
    return REVIEW_REQUIRED, "Entity profile: accounting framework not yet recorded."


def _suggest_audit_review(facts: dict) -> tuple[str, str]:
    """Stage 5 round-2 correction #1: Audit Review (FinSight's own
    analytical/audit-risk review capability) is NOT the same concept as
    Statutory Audit Applicability (an entity/engagement fact recorded on
    the Entity Profile as `statutory_audit_applicable`). The first
    delivery of this function suggested Audit Review = NO whenever
    statutory audit was marked not applicable, which conflated the two —
    Audit Review can still be useful even when a statutory audit is not
    legally required. Audit Review is therefore always-on, like
    Accounting Standards and Income Tax Review, and is never
    automatically disabled by the statutory-audit fact. This is a
    conceptual separation only — it does not introduce any new
    statutory/legal applicability rule or threshold.

    The statutory-audit fact is still surfaced in the reason text below,
    for context, but it does not drive this suggestion."""
    statutory_audit = _to_bool_or_none(facts.get("statutory_audit_applicable"))
    return (
        YES,
        "FinSight's Audit Review is offered to every engagement, independently of "
        "statutory audit applicability. Entity profile: Statutory Audit Applicable = "
        f"{_display_bool(statutory_audit)} (shown for context only — it does not "
        "determine this suggestion)."
    )


def _suggest_income_tax_review(_facts: dict) -> tuple[str, str]:
    return YES, "Every engagement requires an income tax review."


_TAX_AUDIT_STATUS_MAP = {
    "APPLICABLE": (YES, "Entity profile: tax audit status recorded as Applicable."),
    "NOT_APPLICABLE": (NO, "Entity profile: tax audit status recorded as Not Applicable."),
    "REQUIRES_REVIEW": (REVIEW_REQUIRED, "Entity profile: tax audit status recorded as Requires Review."),
}


def _suggest_tax_audit_review(facts: dict) -> tuple[str, str]:
    status = facts.get("tax_audit_status")
    return _TAX_AUDIT_STATUS_MAP.get(
        status,
        (REVIEW_REQUIRED, "Entity profile: tax audit status not yet recorded."),
    )


def _suggest_sebi_lodr(facts: dict) -> tuple[str, str]:
    is_listed = _to_bool_or_none(facts.get("is_listed"))
    if is_listed is True:
        return YES, "Entity profile: entity recorded as listed."
    if is_listed is False:
        return NO, "Entity profile: entity recorded as unlisted."
    return REVIEW_REQUIRED, "Entity profile: listed status not yet recorded."


_SUGGESTERS = {
    "Accounting Standards": _suggest_accounting_standards,
    "Ind AS": _suggest_ind_as,
    "Audit Review": _suggest_audit_review,
    "Income Tax Review": _suggest_income_tax_review,
    "Tax Audit Review": _suggest_tax_audit_review,
    "SEBI/LODR": _suggest_sebi_lodr,
}


def suggest_applicability(facts: dict) -> dict[str, tuple[str, str]]:
    """Given a dict of Entity Profile facts (accounting_framework,
    statutory_audit_applicable, tax_audit_status, is_listed), return
    {area: (system_suggested_status, system_suggested_reason)} for
    every area in AREAS.

    `facts` intentionally takes a plain dict, not an ORM instance, so
    this stays testable without SQLAlchemy and reusable anywhere a
    profile's facts are available (e.g. a future bulk-import path).
    """
    return {area: _SUGGESTERS[area](facts) for area in AREAS}


# --- Display wording (Stage 5 round-2 correction #2) ------------------
#
# `system_suggested_status` itself stays exactly YES / NO / REVIEW_REQUIRED
# in the database (Blueprint Section 2.11's approved enum — unchanged),
# so this is presentation only. The wording below exists to make sure a
# system suggestion is never mistaken for a professional's conclusion:
# the UI shows it as one of three explicitly-labeled, separate lines —
# Entity Profile Input, System Suggestion, Professional Confirmation —
# never merged into one sentence that could read as a finding.

_SUGGESTION_DISPLAY = {
    YES: "Suggested based on current profile",
    NO: "Not Suggested based on current profile",
    REVIEW_REQUIRED: "Review Required — profile information incomplete",
}


def suggestion_display(area: str, status: str) -> str:
    """e.g. "SEBI/LODR — Not Suggested based on current profile" — the
    exact "System Suggestion" line wording from the round-2 correction's
    own example. Never renders the bare enum value (YES/NO) on its own."""
    return f"{area} — {_SUGGESTION_DISPLAY.get(status, status)}"


_FRAMEWORK_DISPLAY = {"IND_AS": "Ind AS", "AS": "AS"}
_TAX_AUDIT_STATUS_DISPLAY = {
    "APPLICABLE": "Applicable",
    "NOT_APPLICABLE": "Not Applicable",
    "REQUIRES_REVIEW": "Requires Review",
}


def entity_profile_input(area: str, facts: dict) -> str | None:
    """The single already-entered Entity Profile fact this area's system
    suggestion mechanically echoes — rendered ABOVE the System Suggestion
    line so the two can never be visually conflated (round-2 correction
    #2's own example: "Listed Entity: No" shown above "System Suggestion:
    SEBI/LODR — Not Suggested based on current profile").

    Returns None for the three areas with no single driving fact:
    Accounting Standards and Income Tax Review are always-on (every
    engagement needs them, regardless of profile), and Audit Review was
    deliberately decoupled from any single Entity Profile fact by
    round-2 correction #1 — see `_suggest_audit_review`, whose reason
    text carries the Statutory Audit Applicable fact instead, clearly
    marked as context rather than as this area's driving input.
    """
    if area == "Ind AS":
        framework = _FRAMEWORK_DISPLAY.get(facts.get("accounting_framework"), "Not yet recorded")
        return f"Accounting Framework: {framework}"
    if area == "Tax Audit Review":
        status = _TAX_AUDIT_STATUS_DISPLAY.get(facts.get("tax_audit_status"), "Not yet recorded")
        return f"Tax Audit Status: {status}"
    if area == "SEBI/LODR":
        return f"Listed Entity: {_display_bool(facts.get('is_listed'))}"
    return None


# Nav display states for the SEBI nav item (base.html) — matches the
# 3-state spec written into that template's comment since Stage 2/3.
NAV_SHOW = "SHOW"
NAV_HIDE = "HIDE"
NAV_REVIEW_REQUIRED = "REVIEW_REQUIRED"


def compute_sebi_nav_state(is_listed: bool | None, user_confirmed_status: str | None) -> str:
    """Resolve the SEBI nav item's display state per the base.html spec:

    1. Listed AND confirmed applicable -> SHOW.
    2. Unlisted, OR explicitly confirmed not applicable -> HIDE.
    3. Everything else (not yet confirmed at all, or explicitly marked
       "requires further review") -> REVIEW_REQUIRED. This is the safe
       default for "we don't yet have a professional's confirmation" —
       a listed entity whose SEBI applicability nobody has confirmed
       yet must never silently render as a normal, settled module.

    Only `is_listed` and `user_confirmed_status` are needed:
    `system_suggested_status` for the SEBI/LODR area is itself always a
    direct mirror of `is_listed` (see `_suggest_sebi_lodr` above), so it
    carries no information `is_listed` doesn't already give this
    function directly — deliberately not threading it through here just
    to leave it unused.

    Pure function: takes plain values, not ORM/session objects, so the
    exact precedence rules are unit-testable without a database.
    """
    is_listed = _to_bool_or_none(is_listed)
    if user_confirmed_status == "NOT_APPLICABLE" or is_listed is False:
        return NAV_HIDE
    if is_listed is True and user_confirmed_status == "APPLICABLE":
        return NAV_SHOW
    return NAV_REVIEW_REQUIRED
