"""
Data Quality orchestration (Stage 7): ties a file's confirmed mappings
back to its stored bytes, re-derives which sheet/header row they came
from, runs `app/validation/data_quality.py`, and persists only the
overall outcome onto the existing `uploaded_files.upload_status`
column.

Same dynamic-session pattern as the other services in this package —
see `upload_service._session()`'s docstring.
"""
from __future__ import annotations

from pathlib import Path

from app.mapping.structure_detector import detect_structure, load_data_rows, split_source_column
from app.services import mapping_service
from app.validation.data_quality import ValidationResult, run_validation


class NoConfirmedMappingsError(Exception):
    """Raised when Data Quality is requested for a file with no
    confirmed mappings yet — validating against nothing would produce a
    meaningless result, so this is surfaced as a clear "map this file
    first" state instead of a misleading pass/fail."""


def evaluate_file(file_record) -> ValidationResult:
    """Read-only: computes a fresh ValidationResult every call. Does
    NOT write to the database — see `save_validation_result()` for the
    explicit, separate persistence step."""
    mappings = mapping_service.get_confirmed_mappings(file_record.file_id)
    if not mappings:
        raise NoConfirmedMappingsError(
            "This file has no confirmed column mappings yet — confirm mappings before running a Data Quality check."
        )

    # Every confirmed mapping for one file was written from the same
    # mapping session, so they all share one sheet (see
    # structure_detector.py's multi-sheet design note) — recovering it
    # from the first mapping is enough.
    sheet_name, _column_key = split_source_column(mappings[0].source_column)

    file_bytes = Path(file_record.stored_path).read_bytes()
    extension = Path(file_record.stored_path).suffix.lower()

    structure = detect_structure(file_bytes, extension, sheet_name)
    column_key_to_position = {c.column_key: c.position for c in structure.columns}

    data = load_data_rows(file_bytes, extension, sheet_name, structure.header_row_index)

    return run_validation(file_record.file_type, data, mappings, column_key_to_position)


def save_validation_result(file_record, result: ValidationResult) -> None:
    mapping_service.mark_file_status(file_record.file_id, result.status)
