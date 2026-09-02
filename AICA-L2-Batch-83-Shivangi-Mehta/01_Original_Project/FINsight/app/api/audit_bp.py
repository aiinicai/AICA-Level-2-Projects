"""
Audit Review blueprint — Review > Audit (Stage 9).

Strictly limited to audit risk indicators/assertions/procedures per the
approved module boundary (Blueprint Section 1.1) — no framework-
treatment conclusion belongs here, and no Tax/SEBI rule is implemented
in this stage. GET always shows a fresh, read-only preview (nothing is
written) alongside whatever is currently persisted from a past run;
POST is the explicit "commit this run's exceptions to the Exception/
Query records" action — see `app/services/audit_review_service.py` for
the full read-vs-write split and the re-run preservation behavior.

Unlike `accounting_bp.py`, there is no framework precondition here —
Audit rules are not framework-gated (Stage 9 design), so this blueprint
never checks or displays an Entity Profile / accounting_framework
state.
"""
from __future__ import annotations

from flask import Blueprint, render_template, request, session

from app.services import audit_review_service
from app.services import engagement_service as engagement_svc
from app.services import rule_runner_service

audit_bp = Blueprint("audit", __name__, url_prefix="/review/audit")


def _status_label(rule):
    """Catalogue-display-only classification — never used for
    execution. Mirrors accounting_bp._status_label(); Audit has no
    withdrawn/superseded marker rows in Stage 9, so that branch is
    omitted."""
    if rule.verification_status != "VERIFIED":
        return "Source Verification Required — Not Executable", "fs-badge-high"
    if not rule.is_active:
        return "Future / Not Currently Executable", "fs-badge-neutral"
    return "Active", "fs-badge-low"


def _catalogue():
    rules = rule_runner_service.list_all_audit_rules()
    entries = []
    for rule in rules:
        status_label, status_class = _status_label(rule)
        entries.append({
            "rule": rule,
            "status_label": status_label,
            "status_class": status_class,
        })
    return entries


@audit_bp.route("/", methods=["GET", "POST"])
def index():
    engagement = engagement_svc.get_current_engagement(session)
    catalogue = _catalogue()
    rules_by_id = audit_review_service.get_audit_rules_by_id()
    assertion_codes_by_rule_id = audit_review_service.get_assertion_codes_by_rule_id()

    review = None
    persisted_exceptions = []
    ran = False
    error = None

    if engagement is not None:
        if request.method == "POST":
            try:
                review = audit_review_service.run_audit_review(engagement.engagement_id)
                ran = True
            except audit_review_service.EngagementNotFoundError as exc:
                error = str(exc)

        if review is None and error is None:
            try:
                review = audit_review_service.preview_audit_review(engagement.engagement_id)
            except audit_review_service.EngagementNotFoundError as exc:
                error = str(exc)

        persisted_exceptions = audit_review_service.get_last_review_results(engagement.engagement_id)

    return render_template(
        "audit/index.html",
        engagement=engagement,
        catalogue=catalogue,
        rules_by_id=rules_by_id,
        assertion_codes_by_rule_id=assertion_codes_by_rule_id,
        review=review,
        persisted_exceptions=persisted_exceptions,
        ran=ran,
        error=error,
    )
