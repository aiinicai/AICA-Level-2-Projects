"""
Mapping blueprint — Data > Mapping (Blueprint Section E, #7; Stage 7).

Structure detection (headers, sheets, duplicate/blank columns) +
mapping suggestions are computed live on every GET — nothing is
persisted until the user explicitly confirms (POST), per Stage 7
requirement #7. See `app/mapping/structure_detector.py` and
`app/mapping/column_mapper.py` for the actual logic; this module is
just the HTTP/form layer, mirroring `upload_bp.py`'s shape.
"""
from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, redirect, render_template, request, session, url_for

from app.mapping.column_mapper import (
    CANONICAL_FIELDS,
    FILE_TYPE_FIELD_SETS,
    detect_file_type_mismatch,
    field_score,
    find_duplicate_target_assignments,
    suggest_mappings,
)
from app.mapping.structure_detector import (
    StructureDetectionError,
    detect_structure,
    make_source_column,
)
from app.services import engagement_service as engagement_svc
from app.services import mapping_service
from app.services import upload_service
from app.upload.validation import FILE_TYPE_LABELS

mapping_bp = Blueprint("mapping", __name__, url_prefix="/data/mapping")


def _get_engagement_scoped_upload(file_id: int):
    engagement = engagement_svc.get_current_engagement(session)
    if engagement is None:
        return None, None
    upload = upload_service.get_upload(file_id)
    if upload is None or upload.engagement_id != engagement.engagement_id:
        abort(404)
    return engagement, upload


@mapping_bp.route("/")
def index():
    engagement = engagement_svc.get_current_engagement(session)
    uploads = upload_service.list_uploads(engagement.engagement_id) if engagement else []
    return render_template(
        "mapping/index.html",
        engagement=engagement,
        uploads=uploads,
        file_type_labels=FILE_TYPE_LABELS,
    )


@mapping_bp.route("/<int:file_id>/", methods=["GET", "POST"])
def detail(file_id: int):
    engagement, upload = _get_engagement_scoped_upload(file_id)
    if engagement is None:
        return redirect(url_for("mapping.index"))

    file_bytes = Path(upload.stored_path).read_bytes()
    extension = Path(upload.stored_path).suffix.lower()

    try:
        from app.mapping.structure_detector import list_sheets
        available_sheets = list_sheets(file_bytes, extension)
    except StructureDetectionError as exc:
        return render_template("mapping/error.html", engagement=engagement, upload=upload, error=str(exc))

    sheet_name = request.args.get("sheet") or request.form.get("sheet") or None
    if available_sheets is not None and sheet_name is None:
        if len(available_sheets) == 1:
            sheet_name = available_sheets[0]
        else:
            return render_template(
                "mapping/sheet_picker.html", engagement=engagement, upload=upload,
                available_sheets=available_sheets,
            )

    try:
        structure = detect_structure(file_bytes, extension, sheet_name)
    except StructureDetectionError as exc:
        return render_template("mapping/error.html", engagement=engagement, upload=upload, error=str(exc))

    mappable_columns = [c for c in structure.columns if not c.is_blank]
    column_labels = [c.column_key for c in mappable_columns]
    suggestions = {s.column_key: s for s in suggest_mappings(column_labels, upload.file_type)}
    mismatch_warning = detect_file_type_mismatch(column_labels, upload.file_type)
    candidate_fields = FILE_TYPE_FIELD_SETS.get(upload.file_type, [])

    errors: dict = {}
    submitted_selection: dict[int, str] | None = None  # column.position -> chosen target_field, POST only

    if request.method == "POST":
        submitted_selection = {
            column.position: request.form.get(f"target_field__{column.position}", "").strip()
            for column in mappable_columns
        }

        # Stage 7 correction #1: enforced server-side, unconditionally —
        # never relying on the form's own client-side prevention of
        # picking the same target field twice. Checked by column_key
        # (not position) since that's what a person reads on screen.
        selection_by_key = {
            column.column_key: submitted_selection[column.position]
            for column in mappable_columns
        }
        duplicates = find_duplicate_target_assignments(selection_by_key)
        if duplicates:
            parts = []
            for target_field, column_keys in duplicates.items():
                label = CANONICAL_FIELDS.get(target_field, (target_field, []))[0]
                parts.append(f'"{label}" was selected for multiple columns: {", ".join(column_keys)}')
            errors["_duplicate_target"] = (
                "Each target field can only be mapped to one source column. " + "; ".join(parts) + "."
            )

        needs_ack = mismatch_warning is not None
        if needs_ack and request.form.get("file_type_reviewed") != "on":
            errors["_file_type"] = (
                "Please review the file type warning above and confirm before saving these mappings."
            )

        if not errors:
            confirmed = []
            for column in mappable_columns:
                chosen = submitted_selection[column.position]
                if not chosen:
                    continue
                confirmed.append({
                    "source_column": make_source_column(sheet_name, column.column_key),
                    "target_field": chosen,
                    "confidence_score": field_score(column.column_key, chosen) if chosen in CANONICAL_FIELDS else None,
                })
            if not confirmed:
                errors["_mappings"] = "Map at least one column before confirming."
            else:
                mapping_service.confirm_mappings(upload.file_id, confirmed)
                mapping_service.mark_file_status(upload.file_id, "MAPPED")
                # Stage 18 fix: redirect to the Upload screen (the real
                # hub now, not this list) rather than mapping.index — a
                # professional who maps one file by hand lands straight
                # back where the next step (Data Quality, then Run
                # Review) is one click away, instead of having to notice
                # and click a separate "Back to Upload" button.
                return redirect(url_for("upload.index"))

    already_confirmed = {m.source_column: m for m in mapping_service.get_confirmed_mappings(upload.file_id)}

    rows = []
    for column in mappable_columns:
        source_column = make_source_column(sheet_name, column.column_key)
        existing = already_confirmed.get(source_column)
        suggestion = suggestions.get(column.column_key)
        if submitted_selection is not None:
            # Re-rendering after a rejected POST — show what the user
            # actually submitted, not the original suggestion/prior
            # confirmation, so they can see and fix the problem in place.
            selected_field = submitted_selection[column.position] or None
        else:
            selected_field = existing.target_field if existing else (suggestion.target_field if suggestion else None)
        rows.append({
            "column": column,
            "suggestion": suggestion,
            "selected_field": selected_field,
            "is_confirmed": existing is not None,
        })

    return render_template(
        "mapping/detail.html",
        engagement=engagement,
        upload=upload,
        file_type_label=FILE_TYPE_LABELS.get(upload.file_type, upload.file_type),
        structure=structure,
        sheet_name=sheet_name,
        rows=rows,
        candidate_fields=candidate_fields,
        canonical_fields=CANONICAL_FIELDS,
        mismatch_warning=mismatch_warning,
        errors=errors,
    )
