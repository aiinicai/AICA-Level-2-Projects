"""
Upload blueprint — Data > Upload (Blueprint Section E, #6).

Stage 6 ("Excel/CSV upload") scope: accept a .csv/.xlsx file for the
current engagement, validate it, store it safely on local disk under
DATA_INPUT_DIR, and record it in `uploaded_files`. No column-mapping
UI (Stage 7's `app/api/mapping_bp.py`) and no
Accounting/Audit/Tax/SEBI rule logic here — this stage only gets a file
safely onto disk and into the database.

Multi-file upload convenience (post-Stage-17 fix): the form's file
picker can now select several files in one action; each selected file
still carries its own Data Type, chosen per-file on the page via
`frontend/static/js/upload.js`, and posted as `file_type__<index>`
fields alongside the (now `multiple`) `file` field. This is a pure UI/
HTTP-layer convenience — every file is still validated and saved one at
a time through the exact same `validate_upload_form()` /
`upload_service.save_uploaded_file()` calls Stage 6 always used; no
rollback ever happens across files (a failure on one file never touches
another file already saved this same request), and nothing here reaches
into mapping, validation, or the review engines.

Two code paths, deliberately kept separate rather than unified into one
generic loop:
  - The ORIGINAL single-file path below is left byte-for-byte as Stage 6
    built it, and only runs for a classic single-file submission (no
    `file_type__<n>` fields present at all) — the exact shape every
    existing caller/test already posts. This guarantees the pre-existing
    upload behavior (redirect-on-success, inline field errors on
    failure, exact error message text) is untouched.
  - The NEW multi-file path below only runs when the submission actually
    looks like a multi-file one (more than one file, or any
    `file_type__<n>` field present — i.e., the new picker was used).
    A single file selected through the new picker still redirects on a
    clean success, exactly like the legacy path, so the only visible
    difference for a one-file upload is which UI produced the request.

Stage 18 addition (explicitly approved before implementation): a THIRD,
additive POST shape on this same `/data/upload/` route — a bare
`action=confirm_auto` field, posted by the new "Looks Good — Confirm &
Continue" button (see `app/services/auto_pipeline_service.py`). This
path is checked first and, when present, never falls through to either
file-upload branch above — both of those are left completely
untouched. On every GET (and on the other two POST shapes, after they
finish handling the upload), this module also now computes a live,
non-persisted preview of what Mapping+Data Quality would auto-detect
for any file still sitting at `upload_status == "UPLOADED"`, exactly
like the (still fully functional) manual Mapping/Data Quality screens'
own GETs already do — nothing from that preview is written to the
database until `action=confirm_auto` is actually submitted.

Stage 18 Phase 3 addition: a FOURTH additive POST shape, `action=
delete_file` (plus a `file_id` field), posted by the new "Remove"
link next to a file that isn't VALIDATED yet. See
`upload_service.delete_upload()`'s docstring for why this exists —
in short, there was previously no way to fix a file uploaded under
the wrong Data Type, which could permanently block Run Review with no
path forward. Never removes a VALIDATED file.
"""
from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

from app.services import auto_pipeline_service
from app.services import engagement_service as engagement_svc
from app.services import unified_review_service
from app.services import upload_service as svc
from app.upload.validation import (
    ALLOWED_EXTENSIONS,
    FILE_TYPE_LABELS,
    FILE_TYPES,
    validate_upload_form,
)

upload_bp = Blueprint("upload", __name__, url_prefix="/data/upload")


def _save_one_file(engagement_id: int, filename: str, file_type: str, file_bytes: bytes):
    """Shared by both paths below: validate one file's form data, then
    save it via the existing, unmodified upload_service — the same two
    calls Stage 6 always made, just factored out so the new multi-file
    loop doesn't duplicate them. Returns (errors_dict, saved_record).
    `errors_dict` is empty and `saved_record` is set on success;
    otherwise `saved_record` is None."""
    errors = validate_upload_form(filename, file_type, len(file_bytes))
    if errors:
        return errors, None
    try:
        record = svc.save_uploaded_file(
            engagement_id=engagement_id,
            original_filename=filename,
            file_type=file_type,
            file_bytes=file_bytes,
            input_dir=Path(current_app.config["DATA_INPUT_DIR"]),
        )
        return {}, record
    except svc.DuplicateUploadError as exc:
        return {"file": str(exc)}, None
    except svc.UnreadableFileError as exc:
        return {"file": str(exc)}, None


@upload_bp.route("/", methods=["GET", "POST"])
def index():
    engagement = engagement_svc.get_current_engagement(session)
    errors: dict = {}
    batch_results: list[dict] = []  # NEW: one entry per file, multi-file path only
    auto_confirm_results: list[dict] | None = None  # NEW (Stage 18): set only after action=confirm_auto
    delete_error: str | None = None  # NEW (Stage 18 Phase 3): set only if action=delete_file fails

    if request.method == "POST" and request.form.get("action") == "confirm_auto":
        # --- Stage 18: one-click "Looks Good — Confirm & Continue". ---
        if engagement is not None:
            auto_confirm_results = auto_pipeline_service.confirm_all(engagement.engagement_id)
    elif request.method == "POST" and request.form.get("action") == "delete_file":
        # --- Stage 18 Phase 3: "Remove" a file that can't validate and
        # is blocking Run Review (see upload_service.delete_upload()'s
        # docstring for why this was added). Never removes a VALIDATED
        # file — see CannotDeleteValidatedFileError. ---
        if engagement is not None:
            try:
                target_id = int(request.form.get("file_id", ""))
            except (TypeError, ValueError):
                target_id = None
            target = svc.get_upload(target_id) if target_id is not None else None
            if target is None or target.engagement_id != engagement.engagement_id:
                delete_error = "That file could not be found — it may have already been removed."
            else:
                try:
                    svc.delete_upload(target_id)
                    return redirect(url_for("upload.index"))
                except svc.CannotDeleteValidatedFileError as exc:
                    delete_error = str(exc)
    elif request.method == "POST":
        if engagement is None:
            # No form is even shown without a current engagement (see the
            # template's empty-state banner) — this only fires if a POST
            # is sent anyway, e.g. a stale tab.
            errors["_engagement"] = "Select or create an engagement before uploading a file."
        else:
            file_storages = request.files.getlist("file")
            is_multi_file_submission = len(file_storages) > 1 or any(
                key.startswith("file_type__") for key in request.form.keys()
            )

            if not is_multi_file_submission:
                # --- Original Stage 6 single-file path, unchanged. ---
                file_storage = file_storages[0] if file_storages else None
                filename = file_storage.filename if file_storage else ""
                file_type = (request.form.get("file_type") or "").strip()
                file_bytes = file_storage.read() if file_storage and filename else b""

                errors, record = _save_one_file(engagement.engagement_id, filename, file_type, file_bytes)
                if record is not None:
                    return redirect(url_for("upload.index"))
            else:
                # --- New: multiple files, each with its own Data Type,
                # in one submission. Every file is processed
                # independently — one file's failure (validation error,
                # duplicate, unreadable) never prevents or undoes any
                # other file in the same batch from being saved. ---
                for index, file_storage in enumerate(file_storages):
                    filename = file_storage.filename if file_storage else ""
                    file_type = (request.form.get(f"file_type__{index}") or "").strip()
                    file_bytes = file_storage.read() if file_storage and filename else b""

                    file_errors, record = _save_one_file(engagement.engagement_id, filename, file_type, file_bytes)
                    if record is not None:
                        batch_results.append({
                            "filename": filename,
                            "status": "success",
                            "message": "Uploaded successfully.",
                        })
                    else:
                        batch_results.append({
                            "filename": filename or f"File {index + 1}",
                            "status": "error",
                            "message": " ".join(file_errors.values()),
                        })

                if batch_results and all(r["status"] == "success" for r in batch_results) and len(batch_results) == 1:
                    # A single file selected through the new picker with
                    # a clean result behaves exactly like the legacy
                    # path — redirect, no results table needed.
                    return redirect(url_for("upload.index"))

    uploads = svc.list_uploads(engagement.engagement_id) if engagement is not None else []
    previews = auto_pipeline_service.build_previews(engagement.engagement_id) if engagement is not None else []
    readiness = unified_review_service.check_review_readiness(engagement.engagement_id) if engagement is not None else None
    return render_template(
        "upload/index.html",
        engagement=engagement,
        uploads=uploads,
        errors=errors,
        batch_results=batch_results,
        previews=previews,
        auto_confirm_results=auto_confirm_results,
        delete_error=delete_error,
        readiness=readiness,
        file_types=FILE_TYPES,
        file_type_labels=FILE_TYPE_LABELS,
        allowed_extensions=ALLOWED_EXTENSIONS,
    )
