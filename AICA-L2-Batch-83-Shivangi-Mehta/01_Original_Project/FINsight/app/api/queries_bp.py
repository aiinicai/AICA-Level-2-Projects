"""
Query Centre blueprint (Blueprint Section E, #15) — Stage 13.

Real routes, at last (the placeholder's own docstring said "Stage 14,"
a leftover from the original blueprint's stage numbering — the current,
governing instruction is Stage 13, and this is it).

Lists every `QueryRecord` for the current engagement, joined with its
`ExceptionRecord` (module/rule/risk/status) and latest `QueryResponse`
— all read through `app/services/query_service.py`, nothing queried
directly here.

Stage 18 additions (explicitly approved before implementation):
  - The on-screen table now shows Sr No / Account Name / Date / Amount /
    Observation / Additional Note / Client Remark, with Additional Note
    and Client Remark editable directly in the row (a small per-row
    form posting to `update_remarks()` below) rather than requiring a
    visit to the full Working Paper screen for that quick edit. The
    full Working Paper screen (`exceptions.working_paper`) is untouched
    and still the place for status changes, evidence, and assignment.
  - `/queries/export.xlsx` — a one-click Excel download of the same
    table, built by `query_service.export_working_papers_workbook()`.

Stage 20 addition (explicitly approved before implementation): the
Status column, previously a read-only badge here (a professional had
to open the full Working Paper page just to move a finding off its
default "Open" status — a discoverability gap, not a missing feature;
`exceptions_bp.py`'s `working_paper()` route already had full status
editing), now also has an inline `<select>` in `update_remarks()`'s
same per-row form. Only the statuses that don't require a
`status_reason` (STATUS_REQUIRES_REASON: REVIEWED_NO_ISSUE / NOT_
APPLICABLE) are offered inline — there's no room for the mandatory
reason textarea in a table row, so those two conclusions still route
the reviewer to "Full Working Paper", exactly as before. The field is
named `finding_status` (not `status`) specifically to avoid colliding
with this same form's pre-existing hidden `status` input, which echoes
back the page's *status filter* selection for the post-save redirect —
two unrelated meanings that happened to want the same name.
"""
from __future__ import annotations

import io

from flask import Blueprint, abort, redirect, render_template, request, send_file, session, url_for

from app.services import engagement_service as engagement_svc
from app.services import query_service
from app.services import unified_review_service as unified_svc

queries_bp = Blueprint("queries", __name__, url_prefix="/queries")

# Offered in the inline Status <select> — every STATUS_VALUES entry
# except the two that require a status_reason (no room for that
# textarea in a table row; those two stay Full-Working-Paper-only).
INLINE_STATUS_VALUES = tuple(
    s for s in query_service.STATUS_VALUES if s not in query_service.STATUS_REQUIRES_REASON
)


@queries_bp.route("/")
def index():
    engagement = engagement_svc.get_current_engagement(session)

    module_filter = request.args.get("module") or None
    status_filter = request.args.get("status") or None
    risk_filter = request.args.get("risk_level") or None
    rule_filter = request.args.get("rule_id") or None
    search = request.args.get("search") or None
    status_error = request.args.get("status_error") or None

    items = []
    summary = None
    rule_ids = []
    risk_levels = []
    if engagement is not None:
        summary = query_service.query_summary(engagement.engagement_id)
        items = query_service.list_queries(
            engagement.engagement_id, module=module_filter, status=status_filter,
            risk_level=risk_filter, rule_id=rule_filter, search=search,
        )
        all_items = query_service.list_queries(engagement.engagement_id)
        rule_ids = sorted({i.rule_id for i in all_items if i.rule_id})
        risk_levels = sorted({i.exception.risk_level for i in all_items if i.exception.risk_level})

    return render_template(
        "queries/index.html",
        engagement=engagement,
        modules=unified_svc.MODULES,
        status_values=query_service.STATUS_VALUES,
        inline_status_values=INLINE_STATUS_VALUES,
        conclusion_labels=query_service.CONCLUSION_LABELS,
        summary=summary,
        items=items,
        rule_ids=rule_ids,
        risk_levels=risk_levels,
        selected_module=module_filter,
        selected_status=status_filter,
        selected_risk_level=risk_filter,
        selected_rule_id=rule_filter,
        search=search or "",
        status_error=status_error,
    )


@queries_bp.route("/<int:exception_id>/update-remarks", methods=["POST"])
def update_remarks(exception_id):
    """The Stage 18 tabular table's inline "Additional Note"/"Client
    Remark" edit — a quick save for just these two fields, without
    leaving the table. Writes through the exact same
    `query_service.update_working_paper()` function (and therefore the
    exact same audit-log entries) the full Working Paper screen's own
    POST handler already uses — see `app/api/exceptions_bp.py`.

    Stage 20 addition: also accepts `finding_status` — the same inline
    form's new Status <select> (see this module's own docstring for why
    it isn't named `status`). Only INLINE_STATUS_VALUES are ever offered
    in that dropdown, but this route re-validates server-side anyway
    (never trust the client) by simply passing whatever arrived straight
    through to `update_working_paper()`'s own existing validation —
    `InvalidStatusError`/`StatusReasonRequiredError` are caught the same
    way `exceptions_bp.working_paper()` already catches them, the
    difference being this route has no page of its own to re-render
    with an inline `error`, so it redirects back with a short
    `status_error` message in the query string instead, shown as a
    page-level banner (see queries/index.html)."""
    engagement = engagement_svc.get_current_engagement(session)
    if engagement is None:
        abort(404)

    redirect_args = {
        key: request.form.get(key)
        for key in ("module", "status", "risk_level", "rule_id", "search")
        if request.form.get(key)
    }

    try:
        query_service.update_working_paper(
            exception_id,
            reviewer_comments=request.form.get("additional_note", ""),
            management_response=request.form.get("client_remark", ""),
            status=request.form.get("finding_status") or None,
        )
    except query_service.WorkingPaperNotFoundError:
        abort(404)
    except query_service.StatusReasonRequiredError:
        redirect_args["status_error"] = (
            "That status needs a reason — open Full Working Paper to record it."
        )
    except query_service.InvalidStatusError:
        redirect_args["status_error"] = "That status value wasn't recognized."

    return redirect(url_for("queries.index", **redirect_args))


@queries_bp.route("/export.xlsx")
def export_xlsx():
    """One-click Excel download of the Query & Working Papers table
    (Stage 18, approved) — see
    `query_service.export_working_papers_workbook()` for the exact
    column shape and the disclosed reason Account Name/Date are blank."""
    engagement = engagement_svc.get_current_engagement(session)
    if engagement is None:
        abort(404)

    workbook = query_service.export_working_papers_workbook(engagement.engagement_id)
    buf = io.BytesIO()
    workbook.save(buf)
    buf.seek(0)

    safe_entity = "".join(c if c.isalnum() else "_" for c in engagement.entity_name)
    safe_year = "".join(c if c.isalnum() else "_" for c in engagement.financial_year)
    filename = f"working_papers_{safe_entity}_{safe_year}.xlsx"

    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
