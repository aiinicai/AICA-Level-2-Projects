"""
Working Paper blueprint (Blueprint Section E, #14) — Stage 13.

`exceptions_bp.py`'s own docstring already said "Real routes implemented
in Stage 13. Status transitions must honor the approved 8-value status
enum, including the mandatory status_reason..." — this is exactly that.

`/exceptions/` stays a thin index: rather than duplicating Stage 12's
Unified Findings Centre (`/review/findings`) as a second "list of
findings" screen, it redirects there — the Findings Centre already IS
the entry point for finding-by-finding navigation; this blueprint's own
job is the per-finding Working Paper detail/edit screen at
`/exceptions/<exception_id>/`.

All actual reviewer-editing logic lives in
`app/services/query_service.py` — this blueprint only translates
form data in and a WorkingPaper out.
"""
from __future__ import annotations

from flask import Blueprint, abort, render_template, request, session

from app.services import engagement_service as engagement_svc
from app.services import query_service

exceptions_bp = Blueprint("exceptions", __name__, url_prefix="/exceptions")


@exceptions_bp.route("/")
def index():
    # Rather than a second "list of findings/queries" screen — which
    # would duplicate the Query Centre this blueprint's own working
    # papers link into — this delegates straight to queries.index()'s
    # real view function and renders the same Query Centre content at
    # this URL too (a plain HTTP redirect here would have made this
    # route return a 302, breaking the pre-existing Stage 2
    # `test_all_nav_pages_load` smoke test, which asserts every nav
    # path returns 200 directly).
    from app.api.queries_bp import index as queries_index
    return queries_index()


@exceptions_bp.route("/<int:exception_id>/", methods=["GET", "POST"])
def working_paper(exception_id: int):
    engagement = engagement_svc.get_current_engagement(session)

    wp = query_service.get_working_paper(exception_id)
    if wp is None:
        abort(404)
    if engagement is None or wp.exception.engagement_id != engagement.engagement_id:
        # A working paper only ever belongs to one engagement — viewing
        # it while a different engagement (or none) is selected would
        # show data inconsistent with the rest of the screen's context.
        abort(404)

    error = None
    saved = False

    if request.method == "POST":
        form = request.form
        try:
            wp = query_service.update_working_paper(
                exception_id,
                assigned_to=form.get("assigned_to"),
                reviewer_query_text=form.get("reviewer_query_text"),
                management_response=form.get("management_response"),
                evidence_description=form.get("evidence_description"),
                evidence_reference=form.get("evidence_reference"),
                reviewer_comments=form.get("reviewer_comments"),
                resolution=form.get("resolution"),
                reviewer_notes=form.get("reviewer_notes"),
                status=form.get("status") or None,
                status_reason=form.get("status_reason"),
            )
            saved = True
        except query_service.StatusReasonRequiredError as exc:
            error = str(exc)
        except query_service.InvalidStatusError as exc:
            error = str(exc)

    return render_template(
        "exceptions/working_paper.html",
        engagement=engagement,
        wp=wp,
        status_values=query_service.STATUS_VALUES,
        conclusion_labels=query_service.CONCLUSION_LABELS,
        statuses_requiring_reason=query_service.STATUS_REQUIRES_REASON,
        saved=saved,
        error=error,
    )
