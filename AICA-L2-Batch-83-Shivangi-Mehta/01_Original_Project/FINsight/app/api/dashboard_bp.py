"""
Dashboard blueprint.

Serves the engagement command-center screen (Blueprint Section E, #5).
Note: this blueprint file was not explicitly named in the original
Blueprint Section C file list, which enumerated API blueprints starting
from engagement_bp. It is added here because the approved nav (Section 8)
has "Dashboard" as the first top-level item and something must serve it.
This is a small additive gap-fill, not a change to any approved module
boundary, schema, or workflow — flagged rather than added silently.

Stage 4 ("Basic UI") built the real Dashboard screen and its chart
components with a genuine zero state, since engagement creation
(Stage 5) didn't exist yet. Stage 5 wired the screen to the real
current engagement + Applicability data.

Stage 11 scope change (does not touch Accounting/Audit/Tax): FinSight V1
does not implement SEBI/Listed-Entity review at all — see
documentation/finsight_v1_scope.md. The dashboard's module list is
always exactly Accounting/Audit/Tax.

Stage 14 (Final UX & Application Polish) — this is the change flagged
explicitly in the Stage 14 UX audit before implementation: every
figure below WAS a hard-coded 0 (there was no rule/exception/query
module yet when Stage 4 shipped this screen). Stage 12's Unified
Review Engine and Stage 13's Query & Working Papers Centre now exist
and already expose read-only, already-tested summary functions
(`unified_review_service.unified_dashboard_summary()`,
`unified_review_service.check_review_readiness()`,
`query_service.query_summary()`). This module now calls those directly
— no new service-layer logic, no schema change, nothing that redefines
what a "finding" or a "query status" is. It is UI-layer wiring only.

One number is deliberately NOT shown: a numeric 0-100 "Overall Risk
Score". No weighted risk-scoring algorithm has ever been built anywhere
in FinSight (the `RiskScore` model exists but is unpopulated scaffold —
see app/models/risk.py) — showing a gauge that can only ever read 0
would be exactly the kind of fabricated/hard-coded figure Stage 14
explicitly prohibits. It is replaced below with a genuine, already-
computed Data Readiness indicator instead. This is a disclosed
limitation, not a silent omission — see documentation/
stage14_final_ux_polish.md.
"""
from flask import Blueprint, render_template, session

from app.services import engagement_service as svc
from app.services import query_service
from app.services import unified_review_service

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/")

# Mirrors query_service's own terminal-status grouping (RESOLVED /
# REVIEWED_NO_ISSUE / NOT_APPLICABLE / CLOSED) for the Dashboard's
# "Resolved" vs. "Open" split. Defined locally rather than importing
# query_service's private `_TERMINAL_STATUSES` — this is display-only
# grouping over the public `STATUS_VALUES` vocabulary, not a new status
# value, so it does not touch query_service.py at all.
_RESOLVED_QUERY_STATUSES = ("RESOLVED", "REVIEWED_NO_ISSUE", "NOT_APPLICABLE", "CLOSED")


def _core_module_rows(counts: dict) -> list[dict]:
    """Accounting/Audit/Tax are always-on per the approved nav (Section
    8) — never conditionally hidden."""
    return [
        {"label": "Accounting", "module_key": "ACCOUNTING", "value": counts.get("ACCOUNTING", 0)},
        {"label": "Audit", "module_key": "AUDIT", "value": counts.get("AUDIT", 0)},
        {"label": "Tax", "module_key": "TAX", "value": counts.get("TAX", 0)},
    ]


def _dashboard_data() -> dict:
    """Real engagement identity + real Stage 12/13 figures. See the
    module docstring for exactly which functions this calls and why the
    numeric risk-score gauge was removed rather than wired to a fake 0.

    Every branch below still degrades to an honest zero/empty state when
    there is no current engagement — nothing is fabricated in that case
    either.
    """
    engagement = svc.get_current_engagement(session)

    if engagement is None:
        return {
            "engagement": None,
            "readiness": None,
            "review_summary": {"total_findings": 0, "per_module": {}, "per_risk_level": {}},
            "exceptions_by_module": _core_module_rows({}),
            "risk_distribution": [],
            "query_summary": {"total": 0, "by_status": {}, "by_module": {}},
            "query_status_bars": [],
            "open_queries": 0,
            "resolved_queries": 0,
            "high_risk_items": 0,
        }

    review_summary = unified_review_service.unified_dashboard_summary(engagement.engagement_id)
    readiness = unified_review_service.check_review_readiness(engagement.engagement_id)
    q_summary = query_service.query_summary(engagement.engagement_id)

    risk_distribution = [
        {"label": level.title(), "level": level.lower(), "value": count}
        for level, count in sorted(review_summary["per_risk_level"].items())
    ]
    high_risk_items = review_summary["per_risk_level"].get("HIGH", 0) + review_summary["per_risk_level"].get("CRITICAL", 0)

    query_status_bars = [
        {"label": query_service.CONCLUSION_LABELS.get(status, status), "value": count}
        for status, count in q_summary["by_status"].items()
        if count
    ]
    resolved_queries = sum(q_summary["by_status"].get(s, 0) for s in _RESOLVED_QUERY_STATUSES)
    open_queries = q_summary["total"] - resolved_queries

    return {
        "engagement": {
            "entity_name": engagement.entity_name,
            "financial_year": engagement.financial_year,
            "status": engagement.status,
        },
        "readiness": {"ready": readiness.ready, "reason": readiness.reason, "upload_count": len(readiness.uploads)},
        "review_summary": review_summary,
        "exceptions_by_module": _core_module_rows(review_summary["per_module"]),
        "risk_distribution": risk_distribution,
        "query_summary": q_summary,
        "query_status_bars": query_status_bars,
        "open_queries": open_queries,
        "resolved_queries": resolved_queries,
        "high_risk_items": high_risk_items,
    }


@dashboard_bp.route("/")
def index():
    return render_template("dashboard/index.html", dashboard=_dashboard_data())
