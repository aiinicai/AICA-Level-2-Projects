"""
Shared non-definitive wording layer (Blueprint Section 12's "shared
string-template wording layer" — referenced since v0.1 but not built
until now, since Stage 8 is the first stage that actually generates
rule-driven exception text).

Every rule-generated finding, across every module (Accounting now,
Audit/Tax/SEBI later), must be built through one of the labels below —
never a free-text "non-compliant"/"violation confirmed"/"breach"
string. This is the one place that vocabulary is defined, so it can't
drift module-to-module.
"""
from __future__ import annotations

# The only four outcome labels an ACCOUNTING rule-generated finding may use.
POTENTIAL_EXCEPTION = "Potential Accounting Exception"
REVIEW_REQUIRED = "Review Required"
POTENTIAL_INCONSISTENCY = "Potential Inconsistency"
INSUFFICIENT_DATA = "Insufficient Data"

# Stage 9, Decision B (approved): the only two labels AN AUDIT rule may
# additionally use, alongside REVIEW_REQUIRED and INSUFFICIENT_DATA
# above (both shared across modules). An audit finding must NEVER use
# POTENTIAL_EXCEPTION or POTENTIAL_INCONSISTENCY — those are Accounting-
# only labels asserting a framework-treatment question, not a risk
# indicator. `app/services/rule_runner_service.py::run_audit_rule()`
# enforces this at the same structural layer that forces a finding's
# rule_id to match its DB row — every ExceptionDraft an audit module
# returns is checked against AUDIT_LABELS below and rejected (raises)
# if it isn't one of them, the same "structural control, not a
# convention" approach Section 1.2 already uses for verification gating.
AUDIT_ATTENTION_REQUIRED = "Audit Attention Required"
POTENTIAL_AUDIT_RISK = "Potential Audit Risk"

# Stage 10, wording requirement (approved): the only three labels A TAX
# rule may additionally use, alongside INSUFFICIENT_DATA (shared across
# every module). A Tax finding must NEVER use POTENTIAL_EXCEPTION,
# POTENTIAL_INCONSISTENCY, AUDIT_ATTENTION_REQUIRED, or
# POTENTIAL_AUDIT_RISK — those belong to Accounting/Audit's own
# vocabulary. Critically, NONE of these three labels — nor any Tax
# finding's explanation text — may state that a tax disallowance or
# violation is confirmed; every one is a "review required" framing.
# `POTENTIAL_DISALLOWANCE_REVIEW_REQUIRED` in particular names the
# *possibility* the reviewer needs to assess, not a computed conclusion.
POTENTIAL_TAX_ISSUE = "Potential Tax Issue"
TAX_REVIEW_REQUIRED = "Tax Review Required"
POTENTIAL_DISALLOWANCE_REVIEW_REQUIRED = "Potential Disallowance — Review Required"

# Stage 10, Decision 4 (approved): TAX-MSME-013's finding must use this
# exact, rule-specific label — never implying a disallowance exists
# merely because a payment exceeded the 45-day MSME window. Kept as its
# own constant (not reused elsewhere) because Decision 4 specifically
# named this wording for MSME findings, distinct from the general Tax
# vocabulary above; treated as an approved fifth member of TAX_LABELS,
# not a replacement for it, since Decision 4 named this rule's finding
# text specifically rather than revising the general Tax label list.
POTENTIAL_MSME_PAYMENT_REVIEW = "Potential MSME Payment Review"

# Stage 10 Round 3 (approved, explicit correction #2): TAX-AUD-014's
# professional (Section 44AB(b)) finding must use this exact,
# rule-specific label rather than the general TAX_REVIEW_REQUIRED —
# FinSight cannot conclusively determine Section 44ADA-related
# applicability (specified-profession status, presumptive-scheme
# election, opt-out, or the ₹50L/₹75L condition) from current data, so
# the label itself must say "Review Required" for audit APPLICABILITY,
# never imply turnover alone settles the question. Same "approved
# additional member of TAX_LABELS, not a replacement" treatment as
# POTENTIAL_MSME_PAYMENT_REVIEW above.
TAX_AUDIT_APPLICABILITY_REVIEW_REQUIRED = "Tax Audit Applicability — Review Required"

# Every label a module may legitimately construct an ExceptionDraft
# with, grouped by module — used by rule_runner_service.py to assert no
# audit/tax rule module accidentally uses another module's label.
ACCOUNTING_LABELS = (POTENTIAL_EXCEPTION, REVIEW_REQUIRED, POTENTIAL_INCONSISTENCY, INSUFFICIENT_DATA)
AUDIT_LABELS = (AUDIT_ATTENTION_REQUIRED, POTENTIAL_AUDIT_RISK, REVIEW_REQUIRED, INSUFFICIENT_DATA)
TAX_LABELS = (
    POTENTIAL_TAX_ISSUE, TAX_REVIEW_REQUIRED, POTENTIAL_DISALLOWANCE_REVIEW_REQUIRED,
    POTENTIAL_MSME_PAYMENT_REVIEW, TAX_AUDIT_APPLICABILITY_REVIEW_REQUIRED, INSUFFICIENT_DATA,
)

# Never allowed in generated text — a cheap guard, not a substitute for
# careful drafting, but catches an accidental slip back into definitive
# language during a future edit.
FORBIDDEN_TERMS = (
    "non-compliant", "noncompliant", "non compliant",
    "violation confirmed", "confirmed violation",
    "is in breach", "breach of", "definitively", "conclusively",
    "guilty", "fraudulent",
)


class DefinitiveLanguageError(ValueError):
    """Raised by assert_non_definitive() when generated text uses
    forbidden definitive/compliance-conclusion language."""


def assert_non_definitive(text: str) -> None:
    lowered = (text or "").lower()
    for term in FORBIDDEN_TERMS:
        if term in lowered:
            raise DefinitiveLanguageError(
                f"Rule-generated text used forbidden definitive language ({term!r}): {text!r}"
            )


def label_line(label: str, detail: str) -> str:
    """`"{label}: {detail}"` — the one place this formatting happens,
    so every rule's exception/insufficient-data text looks the same."""
    assert_non_definitive(detail)
    return f"{label}: {detail}"
