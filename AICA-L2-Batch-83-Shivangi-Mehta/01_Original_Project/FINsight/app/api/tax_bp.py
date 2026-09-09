"""
Tax Review blueprint — Review > Tax (Stage 10).

Real routes, per the approved Stage 10 catalogue + implementation plan.
Per the approved governance rule (Blueprint Section 1.2 / Section 5),
no tax rule may execute unless its verification_status is VERIFIED —
enforced in rule_runner_service/tax_review_service, never bypassed
here. Mirrors `audit_bp.py`'s structure, with one addition: this
blueprint catches `tax_review_service.ActEraNotSupportedError` (the
Decision 1 Act-transition precondition) the same way `accounting_bp.py`
catches `AccountingFrameworkNotSetError` — rendered as a clear banner,
never a crash, and never a silent zero-rule run.
"""
from __future__ import annotations

from flask import Blueprint, render_template, request, session

from app.services import engagement_service as engagement_svc
from app.services import rule_runner_service, tax_review_service

tax_bp = Blueprint("tax", __name__, url_prefix="/review/tax")


def _status_label(rule):
    """Catalogue-display-only classification — never used for
    execution. Mirrors audit_bp._status_label(), with one addition: a
    VERIFIED-but-inactive row (TAX-ACM-010 — legally verified, blocked
    only by a data-model gap per Decision 5) gets its own distinct
    label rather than being folded into the generic "Future / Not
    Currently Executable" bucket, so a reviewer can tell "law not yet
    verified" apart from "law is fine, data isn't there yet"."""
    if rule.verification_status != "VERIFIED":
        return "Source Verification Required — Not Executable", "fs-badge-high"
    if not rule.is_active:
        return "Verified — Not Executable (Data Requirement Unresolved)", "fs-badge-neutral"
    return "Active", "fs-badge-low"


def _catalogue():
    rules = rule_runner_service.list_all_tax_rules()
    entries = []
    for rule in rules:
        status_label, status_class = _status_label(rule)
        entries.append({
            "rule": rule,
            "status_label": status_label,
            "status_class": status_class,
        })
    return entries


@tax_bp.route("/", methods=["GET", "POST"])
def index():
    engagement = engagement_svc.get_current_engagement(session)
    catalogue = _catalogue()
    rules_by_id = tax_review_service.get_tax_rules_by_id()

    review = None
    persisted_exceptions = []
    ran = False
    error = None

    if engagement is not None:
        if request.method == "POST":
            try:
                review = tax_review_service.run_tax_review(engagement.engagement_id)
                ran = True
            except (tax_review_service.EngagementNotFoundError, tax_review_service.ActEraNotSupportedError) as exc:
                error = str(exc)

        if review is None and error is None:
            try:
                review = tax_review_service.preview_tax_review(engagement.engagement_id)
            except (tax_review_service.EngagementNotFoundError, tax_review_service.ActEraNotSupportedError) as exc:
                error = str(exc)

        persisted_exceptions = tax_review_service.get_last_review_results(engagement.engagement_id)

    return render_template(
        "tax/index.html",
        engagement=engagement,
        catalogue=catalogue,
        rules_by_id=rules_by_id,
        review=review,
        persisted_exceptions=persisted_exceptions,
        ran=ran,
        error=error,
    )
