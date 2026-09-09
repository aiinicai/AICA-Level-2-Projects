"""
Upload auto-pipeline (Stage 18, approved).

The user's Stage 18 redesign request: Detect Structure / Map Columns /
Validate should be automatic, ending in one clickable "Looks Good —
Confirm & Continue" action rather than three separate screen visits.
The user's own later, revised answer (simple-language clarifying round)
was "add one quick 'Looks good?' click" — i.e. NOT the earlier "fully
automatic, zero human step" answer — so this module computes everything
live and shows it, but writes nothing to the database until that one
click is submitted. This preserves, unchanged, the pre-existing
Blueprint Section 8 safeguard that a mapping is never used downstream
until a human has confirmed it — enforced the same way it always was:
`mapping_service.confirm_mappings()` is the only function that ever
writes an `is_user_confirmed=True` row, and this module calls it no
earlier than the manual Mapping screen's own POST handler does.

Deliberately a thin orchestration layer over the exact same building
blocks the (still fully functional, NOT removed) Mapping and Data
Quality blueprints already use — `structure_detector`, `column_mapper`,
`mapping_service`, `data_quality.run_validation`, `validation_service`
— so this can never disagree with what a professional would see if they
opened those screens directly, and a file this module can't confidently
handle is simply left for the manual screens rather than guessed at.

Multi-sheet auto-pick (the one new judgement call this module makes
that the manual screens don't): the existing Mapping screen stops and
asks a human to pick a sheet whenever an .xlsx file has more than one.
An automatic pipeline can't stop and ask, so this module always picks
`available_sheets[0]` (the first/leftmost sheet in the workbook) for a
multi-sheet file, and says so in the preview (`auto_picked_sheet`) so
nothing is silently decided without being visible on screen.

Zero-suggestion fallback: if not one single column scores at or above
`column_mapper.SUGGESTION_THRESHOLD`, the file is reported as
"couldn't auto-map any columns" and excluded from the "Confirm &
Continue" action — `mapping_service.confirm_mappings()` would reject an
empty confirm anyway (mirrors `mapping_bp.py`'s own `_mappings` error),
and nothing is ever force-mapped. The file stays exactly where it is
(`upload_status == "UPLOADED"`) and the existing manual Mapping screen
remains available as a fallback for it.

Bug fix (caught after Phase 2 shipped, before the .exe was built): a
file that had already been mapped through the still-reachable manual
Mapping screen (`upload_status == "MAPPED"`, not "UPLOADED") used to
fall through every screen entirely — this module only looked at
"UPLOADED" files, the Upload screen's "Run Review" button only appears
once every file is "VALIDATED", and the old Mapping/Data Quality
sidebar links (the only other way to reach the Data Quality screen)
were removed in this same stage. A professional who mapped a file
manually had no visible next step. This module now also picks up
"MAPPED" files: since a human already confirmed that mapping (via the
manual screen's own POST, same Blueprint Section 8 safeguard), nothing
further needs confirming — only Data Quality needs to run — so these
files are shown in the same "Ready to Confirm" panel (labeled "Already
mapped") and the same "Looks Good — Confirm & Continue" click runs and
saves Data Quality for them via the exact same `validation_service`
functions the manual Data Quality screen's own POST already uses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.mapping.column_mapper import detect_file_type_mismatch, suggest_mappings
from app.mapping.structure_detector import (
    StructureDetectionError,
    detect_structure,
    list_sheets,
    load_data_rows,
    make_source_column,
)
from app.services import mapping_service
from app.services import upload_service
from app.services import validation_service
from app.validation.data_quality import run_validation

# Stage 18 fix: column_mapper.suggest_mappings() itself only requires a
# match to score at or above SUGGESTION_THRESHOLD (0.35) to be offered
# as a suggestion — reasonable when a human reviews every suggestion
# before confirming, exactly what the manual Mapping screen has always
# done. This automatic pipeline confirms mappings with no per-column
# human review at all, so it holds itself to a stricter bar: only a
# match scored 1.0 (exact, after normalization) or 0.75 (one label
# contains the other) is auto-confirmed. Anything below that is a pure
# difflib fuzzy guess (see column_mapper.field_score()'s docstring —
# fuzzy-only matches are mathematically capped below 0.7) and is left
# unmapped here rather than silently confirmed on a coin-flip-quality
# guess; real data surfaced this (e.g. a "GST (INR)" amount column
# fuzzy-matching "GSTIN" at 0.583) — the file simply shows fewer
# auto-matched columns and the human is pointed at "Review manually"
# instead of getting a wrong mapping nobody checked.
AUTO_ACCEPT_THRESHOLD = 0.75


@dataclass
class _PreviewMapping:
    """Stand-in for a confirmed DataMapping row, used only to preview a
    Data Quality result before anything is actually confirmed.
    `run_validation()` (app/validation/data_quality.py) only ever reads
    `.source_column`/`.target_field` off whatever list it's given — a
    real, persisted DataMapping row is not required."""
    source_column: str
    target_field: str


@dataclass
class FilePreview:
    upload: object
    error: str | None = None                    # unreadable file / structure detection failure
    sheet_name: str | None = None
    auto_picked_sheet: bool = False              # True only when a MULTI-sheet workbook's first sheet was auto-chosen
    already_mapped: bool = False                 # True for a file mapped via the manual Mapping screen already
    mapped_count: int = 0
    unmapped_columns: list = field(default_factory=list)
    mismatch_warning: str | None = None
    validation_status: str | None = None         # "VALIDATED" or "ERROR" preview, None if can_auto_confirm is False
    validation_messages: list = field(default_factory=list)
    can_auto_confirm: bool = False
    confirmed_payload: list = field(default_factory=list)  # exact list mapping_service.confirm_mappings() expects


def build_previews(engagement_id: int) -> list[FilePreview]:
    """Read-only — like the Mapping/Data Quality screens' own GETs,
    nothing here is written to the database. Files sitting at
    upload_status == 'UPLOADED' get the full detect+suggest+preview
    treatment; files already 'MAPPED' (e.g. via the manual Mapping
    screen) only need a Data Quality preview — see
    `_build_one_preview_for_mapped_file()`. A file already
    VALIDATED/ERROR was already fully handled and is left alone."""
    previews = []
    for upload in upload_service.list_uploads(engagement_id):
        if upload.upload_status == "UPLOADED":
            previews.append(_build_one_preview(upload))
        elif upload.upload_status == "MAPPED":
            previews.append(_build_one_preview_for_mapped_file(upload))
    return previews


def _build_one_preview_for_mapped_file(upload) -> FilePreview:
    """A file already mapped (mapping already confirmed by a human, via
    the manual Mapping screen — same Blueprint Section 8 safeguard).
    Nothing further needs confirming, so this only computes a Data
    Quality preview from the mapping already on file, via the exact
    same `validation_service.evaluate_file()` the manual Data Quality
    screen's own GET already uses."""
    preview = FilePreview(upload=upload, already_mapped=True)
    confirmed = mapping_service.get_confirmed_mappings(upload.file_id)
    preview.mapped_count = len(confirmed)
    preview.can_auto_confirm = len(confirmed) > 0
    if preview.can_auto_confirm:
        try:
            result = validation_service.evaluate_file(upload)
            preview.validation_status = result.status
            preview.validation_messages = result.messages
        except validation_service.NoConfirmedMappingsError:
            # Unreachable given the len(confirmed) > 0 check above —
            # guarded so a future change here can't silently 500.
            preview.can_auto_confirm = False
    return preview


def _build_one_preview(upload) -> FilePreview:
    preview = FilePreview(upload=upload)
    file_bytes = Path(upload.stored_path).read_bytes()
    extension = Path(upload.stored_path).suffix.lower()

    try:
        available_sheets = list_sheets(file_bytes, extension)
        sheet_name = None
        if available_sheets is not None:
            sheet_name = available_sheets[0]
            preview.auto_picked_sheet = len(available_sheets) > 1
        preview.sheet_name = sheet_name

        structure = detect_structure(file_bytes, extension, sheet_name)
    except StructureDetectionError as exc:
        preview.error = str(exc)
        return preview

    mappable_columns = [c for c in structure.columns if not c.is_blank]
    column_labels = [c.column_key for c in mappable_columns]
    suggestions = {s.column_key: s for s in suggest_mappings(column_labels, upload.file_type)}
    preview.mismatch_warning = detect_file_type_mismatch(column_labels, upload.file_type)

    confirmed_payload = []
    preview_mappings = []
    for column in mappable_columns:
        suggestion = suggestions.get(column.column_key)
        if (
            suggestion is None
            or suggestion.target_field is None
            or (suggestion.confidence or 0.0) < AUTO_ACCEPT_THRESHOLD
        ):
            preview.unmapped_columns.append(column.column_key)
            continue
        source_column = make_source_column(sheet_name, column.column_key)
        confirmed_payload.append({
            "source_column": source_column,
            "target_field": suggestion.target_field,
            "confidence_score": suggestion.confidence,
        })
        preview_mappings.append(
            _PreviewMapping(source_column=source_column, target_field=suggestion.target_field)
        )

    preview.mapped_count = len(confirmed_payload)
    preview.confirmed_payload = confirmed_payload
    preview.can_auto_confirm = len(confirmed_payload) > 0

    if preview.can_auto_confirm:
        column_key_to_position = {c.column_key: c.position for c in structure.columns}
        data = load_data_rows(file_bytes, extension, sheet_name, structure.header_row_index)
        result = run_validation(upload.file_type, data, preview_mappings, column_key_to_position)
        preview.validation_status = result.status
        preview.validation_messages = result.messages

    return preview


def confirm_all(engagement_id: int) -> list[dict]:
    """The 'Looks Good — Confirm & Continue' action. For every file
    `build_previews()` reports as `can_auto_confirm`, actually persists
    its suggested mappings via `mapping_service.confirm_mappings()` —
    the exact same function, with the exact same "never write an
    unconfirmed row" guarantee, the manual Mapping screen's own POST
    handler already calls — then runs and saves Data Quality via
    `validation_service`, again the same functions the manual Data
    Quality screen's own POST handler already calls. Returns one
    summary dict per file actually processed, for the confirmation
    screen to display. A file with zero auto-mapped columns is skipped
    here exactly as it is excluded from `can_auto_confirm` above —
    nothing is ever force-mapped or force-validated with an empty
    mapping set."""
    results = []
    for preview in build_previews(engagement_id):
        if not preview.can_auto_confirm:
            continue

        if not preview.already_mapped:
            mapping_service.confirm_mappings(preview.upload.file_id, preview.confirmed_payload)
            mapping_service.mark_file_status(preview.upload.file_id, "MAPPED")

        refreshed = upload_service.get_upload(preview.upload.file_id)
        try:
            result = validation_service.evaluate_file(refreshed)
            validation_service.save_validation_result(refreshed, result)
            status = result.status
        except validation_service.NoConfirmedMappingsError:
            # Unreachable in practice — we just confirmed >=1 mapping
            # above — kept only so a future change to this file can't
            # silently turn into an unhandled 500 here.
            status = "ERROR"

        results.append({
            "filename": preview.upload.original_filename,
            "mapped_count": preview.mapped_count,
            "status": status,
        })
    return results
