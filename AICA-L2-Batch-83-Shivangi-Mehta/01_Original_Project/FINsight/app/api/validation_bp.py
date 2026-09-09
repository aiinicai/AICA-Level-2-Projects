"""
Validation blueprint — Data > Data Quality (Blueprint Section E, #8;
Stage 7).

GET always computes a fresh, read-only Data Quality result (nothing is
written) — see `app/services/validation_service.py`. POST recomputes
and then persists only the overall VALIDATED/ERROR outcome onto the
already-approved `uploaded_files.upload_status` field.
"""
from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, request, session, url_for

from app.services import engagement_service as engagement_svc
from app.services import upload_service
from app.services import validation_service
from app.upload.validation import FILE_TYPE_LABELS

validation_bp = Blueprint("validation", __name__, url_prefix="/data/quality")


def _get_engagement_scoped_upload(file_id: int):
    engagement = engagement_svc.get_current_engagement(session)
    if engagement is None:
        return None, None
    upload = upload_service.get_upload(file_id)
    if upload is None or upload.engagement_id != engagement.engagement_id:
        abort(404)
    return engagement, upload


@validation_bp.route("/")
def index():
    engagement = engagement_svc.get_current_engagement(session)
    uploads = upload_service.list_uploads(engagement.engagement_id) if engagement else []
    return render_template(
        "validation/index.html",
        engagement=engagement,
        uploads=uploads,
        file_type_labels=FILE_TYPE_LABELS,
    )


@validation_bp.route("/<int:file_id>/", methods=["GET", "POST"])
def detail(file_id: int):
    engagement, upload = _get_engagement_scoped_upload(file_id)
    if engagement is None:
        return redirect(url_for("validation.index"))

    try:
        result = validation_service.evaluate_file(upload)
    except validation_service.NoConfirmedMappingsError as exc:
        return render_template(
            "validation/not_mapped.html", engagement=engagement, upload=upload, error=str(exc),
        )

    saved = False
    if request.method == "POST":
        validation_service.save_validation_result(upload, result)
        saved = True
        upload = upload_service.get_upload(file_id)  # refresh persisted upload_status

    return render_template(
        "validation/detail.html",
        engagement=engagement,
        upload=upload,
        result=result,
        saved=saved,
    )
