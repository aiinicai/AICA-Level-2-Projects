"""
Accounting Review blueprint — Review > Accounting (Blueprint Section E, #9).

Strictly limited to framework-treatment checks per the approved module
boundary (Blueprint Section 1.1) — no audit-style risk-indicator logic
belongs here. GET always shows a fresh, read-only preview (nothing is
written) alongside whatever is currently persisted from a past run;
POST is the explicit "commit this run's exceptions to the Exception/
Query records" action — see `app/services/accounting_review_service.py`
for the full read-vs-write split and the re-run preservation behavior.

Stage 8 Round 2 (correction #1): the review is now framework-aware —
`accounting_review_service` selects rules against the engagement's own
`accounting_framework` (AS or IND_AS), and raises
`AccountingFrameworkNotSetError` if that isn't known yet (no Entity
Profile saved) — shown here as a clear "complete the Entity Profile
first" banner rather than silently running nothing.
"""
from __future__ import annotations

from flask import Blueprint, render_template, request, session

from app.services import accounting_review_service
from app.services import engagement_service as engagement_svc
from app.services import rule_runner_service

accounting_bp = Blueprint("accounting", __name__, url_prefix="/review/accounting")


def _status_label(rule):
    """Catalogue-display-only classification — never used for
    execution (that's rule_runner_service's job). Distinguishes a
    withdrawn/superseded marker row, an unverified row, a coded-but-
    deliberately-inactive "Future" row, and a genuinely active row, per
    Stage 8 Round 2 correction #9's "clearly show Future / Insufficient
    Data / Not currently executable" instruction."""
    if (rule.description or "").startswith("WITHDRAWN"):
        return "Withdrawn — Superseded", "fs-badge-neutral"
    if rule.verification_status != "VERIFIED":
        return "Source Verification Required — Not Executable", "fs-badge-high"
    if not rule.is_active:
        return "Future / Not Currently Executable", "fs-badge-neutral"
    return "Active", "fs-badge-low"


def _catalogue():
    rules = rule_runner_service.list_all_accounting_rules()
    standards_by_id = rule_runner_service.get_standards_by_id()
    entries = []
    for rule in rules:
        status_label, status_class = _status_label(rule)
        entries.append({
            "rule": rule,
            "standard": standards_by_id.get(rule.standard_id),
            "status_label": status_label,
            "status_class": status_class,
        })
    return entries


@accounting_bp.route("/", methods=["GET", "POST"])
def index():
    engagement = engagement_svc.get_current_engagement(session)
    catalogue = _catalogue()

    review = None
    persisted_exceptions = []
    ran = False
    error = None

    if engagement is not None:
        if request.method == "POST":
            try:
                review = accounting_review_service.run_accounting_review(engagement.engagement_id)
                ran = True
            except (accounting_review_service.EngagementNotFoundError,
                     accounting_review_service.AccountingFrameworkNotSetError) as exc:
                error = str(exc)

        if review is None and error is None:
            try:
                review = accounting_review_service.preview_accounting_review(engagement.engagement_id)
            except (accounting_review_service.EngagementNotFoundError,
                     accounting_review_service.AccountingFrameworkNotSetError) as exc:
                error = str(exc)

        persisted_exceptions = accounting_review_service.get_last_review_results(engagement.engagement_id)

    return render_template(
        "accounting/index.html",
        engagement=engagement,
        catalogue=catalogue,
        review=review,
        persisted_exceptions=persisted_exceptions,
        ran=ran,
        error=error,
    )
