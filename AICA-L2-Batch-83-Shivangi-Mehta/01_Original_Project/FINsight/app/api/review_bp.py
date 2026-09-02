"""
Unified Review Engine blueprint (Stage 12) — Review > Run Review /
Findings Centre.

A thin HTTP layer over `app/services/unified_review_service.py`, the same
"blueprint only orchestrates request/response, the service module owns
all the logic" split every other review blueprint in this codebase
already follows. This blueprint never calls any rule module, any
`rule_runner_service.run_*` function, or any `ExceptionRecord`/
`QueryRecord` constructor directly — everything goes through
`unified_review_service`, which itself only calls the three existing
engines' own `preview_*_review()` / `run_*_review()` functions.

Three routes:
  - `/review/` (GET/POST) — Review Configuration (module checkboxes,
    all selected by default) + live preview on GET + Run Review on POST
    + the post-run Result Summary, all on one screen, mirroring the
    existing accounting/audit/tax blueprints' own GET-preview/POST-run
    shape (Stage 12 section 2: one screen, not three separate visits).
  - `/review/findings` (GET) — the Unified Findings Centre: every
    persisted Accounting+Audit+Tax finding for the current engagement,
    filterable by module/status/risk/rule_id.
  - `/review/findings/<module>/<finding_id>` (GET) — the Finding Detail
    Page for one finding.

No route here ever accepts or executes a "SEBI" module value (Stage 12
section 3) — `unified_review_service.MODULES` is the only source of
truth for what's selectable, and it has exactly three members.

Stage 18 addition (explicitly approved before implementation): a second,
additive POST shape on `/review/` — a bare `run_source=upload_quick_action`
field with no `modules` list at all, posted by the new one-click "Run
Review" button on the Upload screen (the standalone "Run Review" sidebar
tab/nav entry was removed per the Stage 18 redesign; the Upload screen's
button is now the entry point). This path does NOT read a `modules`
checkbox list at all — it runs whichever modules
`engagement_service.get_enabled_review_modules()` (driven by the
Applicability Matrix's Yes/No answers) says to, and redirects straight to
the Findings Centre on a successful run, rather than re-rendering this
page's Result Summary. The ORIGINAL checkbox-based POST shape (`modules`
posted, as every pre-Stage-18 caller and test already does) is left
COMPLETELY UNCHANGED below — same module-selection logic, same inline
Result Summary render, no redirect — this is a dual-path design (see
app/api/upload_bp.py's own docstring for the same pattern, used there for
the exact same reason: add new behavior without touching a single
existing, already-tested code path).
"""
from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, request, session, url_for

from app.services import engagement_service as engagement_svc
from app.services import unified_review_service as unified_svc

review_bp = Blueprint("review", __name__, url_prefix="/review")


@review_bp.route("/", methods=["GET", "POST"])
def index():
    engagement = engagement_svc.get_current_engagement(session)

    readiness = None
    summary = None
    selected_modules = unified_svc.MODULES  # all selected by default (Stage 12 section 3)
    ran = False
    error = None

    if engagement is not None:
        readiness = unified_svc.check_review_readiness(engagement.engagement_id)

        if request.method == "POST" and request.form.get("run_source") == "upload_quick_action":
            # --- Stage 18: one-click "Run Review" from the Upload screen. ---
            selected_modules = engagement_svc.get_enabled_review_modules(engagement.engagement_id)
            try:
                summary = unified_svc.run_unified_review(engagement.engagement_id, selected_modules)
                ran = summary.executed
                if summary.executed:
                    return redirect(url_for("review.findings"))
            except unified_svc.EngagementNotFoundError as exc:
                error = str(exc)
        elif request.method == "POST":
            # --- Original Stage 12 path, unchanged. ---
            posted = request.form.getlist("modules")
            selected_modules = tuple(m for m in unified_svc.MODULES if m in posted) or unified_svc.MODULES
            try:
                summary = unified_svc.run_unified_review(engagement.engagement_id, selected_modules)
                ran = True
            except unified_svc.EngagementNotFoundError as exc:
                error = str(exc)
        else:
            try:
                summary = unified_svc.preview_unified_review(engagement.engagement_id, selected_modules)
            except unified_svc.EngagementNotFoundError as exc:
                error = str(exc)

    return render_template(
        "review/configure.html",
        engagement=engagement,
        modules=unified_svc.MODULES,
        selected_modules=selected_modules,
        readiness=readiness,
        summary=summary,
        ran=ran,
        error=error,
    )


@review_bp.route("/findings")
def findings():
    engagement = engagement_svc.get_current_engagement(session)

    module_filter = request.args.get("module") or None
    status_filter = request.args.get("status") or None
    risk_filter = request.args.get("risk_level") or None
    rule_filter = request.args.get("rule_id") or None

    items = []
    grouped = {}
    dashboard_summary = None
    if engagement is not None:
        dashboard_summary = unified_svc.unified_dashboard_summary(engagement.engagement_id)
        items = unified_svc.get_unified_findings(
            engagement.engagement_id,
            modules=(module_filter,) if module_filter else None,
            status=status_filter,
            risk_level=risk_filter,
            rule_id=rule_filter,
        )
        grouped = unified_svc.group_findings_by_transaction(items)

    # Distinct filter option lists come from the engagement's own findings
    # (never a hardcoded/invented enum) — an engagement with no CRITICAL
    # findings simply never offers a CRITICAL filter option.
    all_items_for_filters = (
        unified_svc.get_unified_findings(engagement.engagement_id) if engagement is not None else []
    )
    statuses = sorted({f.status for f in all_items_for_filters})
    risk_levels = sorted({f.risk_level for f in all_items_for_filters if f.risk_level})
    rule_ids = sorted({f.rule_id for f in all_items_for_filters if f.rule_id})

    return render_template(
        "review/findings.html",
        engagement=engagement,
        modules=unified_svc.MODULES,
        dashboard_summary=dashboard_summary,
        findings=items,
        grouped_by_transaction=grouped,
        statuses=statuses,
        risk_levels=risk_levels,
        rule_ids=rule_ids,
        selected_module=module_filter,
        selected_status=status_filter,
        selected_risk_level=risk_filter,
        selected_rule_id=rule_filter,
    )


@review_bp.route("/findings/<module>/<int:finding_id>")
def finding_detail(module: str, finding_id: int):
    engagement = engagement_svc.get_current_engagement(session)
    if engagement is None:
        abort(404)

    module = module.upper()
    if module not in unified_svc.MODULES:
        abort(404)

    finding = unified_svc.get_finding(engagement.engagement_id, module, finding_id)
    if finding is None:
        abort(404)

    return render_template("review/finding_detail.html", engagement=engagement, finding=finding)
