"""
Uploaded file persistence + safe file handling (Stage 6).

Real SQLAlchemy 2.x ORM code, same pattern as
`app/services/engagement_service.py`: reads `app.extensions.SessionLocal`
dynamically on every call (never a stale name-import — see that
module's `_session()` docstring for why this matters across repeated
`create_app()` calls).

No new tables or fields are used here — every field this module reads
or writes already exists in the approved Stage 3 schema
(`app/models/uploads.py`).

Offline-first (Blueprint Section A.2 / this stage's own instruction):
row-counting uses pandas + openpyxl entirely locally against bytes
already in memory — no network call, no external/cloud service of any
kind touches the uploaded file at any point in this module.
"""
from __future__ import annotations

import hashlib
import io
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from werkzeug.utils import secure_filename

from app import extensions
from app.models.uploads import DataMapping, UploadedFile


def _session():
    """See engagement_service._session()'s docstring — same reasoning,
    same fix, applied here for the same class of bug."""
    return extensions.SessionLocal


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DuplicateUploadError(Exception):
    """Raised when this exact file (same engagement, same SHA-256
    checksum) has already been uploaded — mirrors the DB's own
    UNIQUE(engagement_id, checksum) constraint (Blueprint D.4), checked
    here first so the user gets a clear message instead of a raw
    IntegrityError."""

    def __init__(self, existing_file: UploadedFile):
        self.existing_file = existing_file
        super().__init__(
            f"This exact file was already uploaded as "
            f"“{existing_file.original_filename}” on {existing_file.uploaded_at}."
        )


class UnreadableFileError(Exception):
    """Raised when the file can't be parsed as CSV/Excel at all (e.g.
    corrupted, not actually the claimed format). Nothing is written to
    disk or the database when this is raised — see save_uploaded_file()."""


def compute_checksum(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def find_duplicate(engagement_id: int, checksum: str) -> UploadedFile | None:
    stmt = select(UploadedFile).where(
        UploadedFile.engagement_id == engagement_id,
        UploadedFile.checksum == checksum,
    )
    return _session().scalars(stmt).first()


def count_rows(file_bytes: bytes, extension: str) -> int:
    """Row count excludes the header row (pandas' default), matching
    "how many records does this file contain" rather than a raw line
    count. Raises UnreadableFileError on anything pandas/openpyxl can't
    parse — deliberately not persisted as an upload with an ERROR
    status: `upload_status=ERROR` (Blueprint D.4's enum) is reserved for
    Stage 7's validation engine finding problems in an already-parsed
    file, not for "this isn't a readable file at all," which Stage 6
    rejects outright instead."""
    try:
        if extension == ".csv":
            df = pd.read_csv(io.BytesIO(file_bytes))
        else:  # .xlsx — the only other extension validate_upload_form allows
            df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    except Exception as exc:
        kind = extension.lstrip(".").upper()
        raise UnreadableFileError(f"Could not read this file as {kind} — is it corrupted or the wrong format?") from exc
    return len(df)


def _build_stored_path(input_dir: Path, engagement_id: int, original_filename: str) -> Path:
    """Safe file handling / path-traversal guard (Blueprint Section 25):
    `secure_filename()` strips directory separators and unsafe
    characters, a timestamp+random suffix avoids collisions between two
    different uploads that happen to share a filename, and the final
    resolved path is confirmed to still sit inside this engagement's own
    subfolder of DATA_INPUT_DIR before anything is written."""
    safe_name = secure_filename(original_filename) or "upload"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    token = secrets.token_hex(4)

    engagement_dir = input_dir / str(engagement_id)
    engagement_dir.mkdir(parents=True, exist_ok=True)

    stored_path = engagement_dir / f"{stamp}_{token}_{safe_name}"

    resolved_engagement_dir = engagement_dir.resolve()
    resolved_stored_path = stored_path.resolve()
    if os.path.commonpath([resolved_engagement_dir, resolved_stored_path]) != str(resolved_engagement_dir):
        # Defense in depth — should be unreachable given secure_filename()
        # above, but a stored path escaping its engagement folder is
        # exactly the class of bug a path-traversal guard exists to catch.
        raise ValueError("Resolved upload path escaped the engagement's upload directory.")
    return stored_path


def save_uploaded_file(
    *,
    engagement_id: int,
    original_filename: str,
    file_type: str,
    file_bytes: bytes,
    input_dir: Path,
) -> UploadedFile:
    """Checksum -> duplicate check -> parse (row count) -> write to disk
    -> persist, in that order, so a rejected upload (duplicate or
    unreadable) never touches the filesystem at all."""
    checksum = compute_checksum(file_bytes)

    duplicate = find_duplicate(engagement_id, checksum)
    if duplicate is not None:
        raise DuplicateUploadError(duplicate)

    extension = Path(original_filename).suffix.lower()
    row_count = count_rows(file_bytes, extension)  # raises UnreadableFileError

    stored_path = _build_stored_path(input_dir, engagement_id, original_filename)
    stored_path.write_bytes(file_bytes)

    record = UploadedFile(
        engagement_id=engagement_id,
        file_type=file_type,
        original_filename=original_filename,
        stored_path=str(stored_path),
        row_count=row_count,
        upload_status="UPLOADED",
        uploaded_at=_now_iso(),
        checksum=checksum,
    )
    _session().add(record)
    _session().commit()
    return record


def get_upload(file_id: int) -> UploadedFile | None:
    """Added in Stage 7 for the Mapping/Data Quality screens, which need
    to look up one specific uploaded file by id — not a schema change,
    just a read helper alongside the existing `list_uploads()`."""
    return _session().get(UploadedFile, file_id)


def list_uploads(engagement_id: int) -> list[UploadedFile]:
    stmt = (
        select(UploadedFile)
        .where(UploadedFile.engagement_id == engagement_id)
        .order_by(UploadedFile.uploaded_at.desc())
    )
    return list(_session().scalars(stmt).all())


class CannotDeleteValidatedFileError(Exception):
    """Raised by `delete_upload()` when asked to remove a file whose
    `upload_status` is already VALIDATED. A VALIDATED file's data may
    already have contributed to a preview or a run of the review
    engines — silently allowing it to disappear would make "what data
    did this review actually see" unanswerable after the fact, which
    conflicts with FinSight's audit-trail principle. Only a file that
    never successfully finished data preparation (UPLOADED / MAPPED /
    ERROR) can be removed this way."""


def delete_upload(file_id: int) -> None:
    """Stage 18 Phase 3 addition: until now there was no way to remove
    an uploaded file at all, and no way to change a file's Data Type
    after upload (only at upload time). A file uploaded under the
    wrong Data Type — e.g. a period-summary GST file that will never
    satisfy the per-invoice "GST Data" essential fields no matter how
    its columns are mapped — had no path forward: it can't validate,
    and `unified_review_service.check_review_readiness()` requires
    every uploaded file to be VALIDATED before Run Review is allowed
    at all, so one such file permanently blocks the whole engagement's
    review with no way out through the UI. This lets a professional
    remove that one file (then, if they still need its data, re-upload
    it under a different, correct Data Type) rather than being stuck.

    Deliberately does NOT touch `check_review_readiness()`'s "every
    file must be VALIDATED" rule itself — that stays exactly the
    disclosed Stage 12 design it always was. This only makes that rule
    actually satisfiable again once a file can't be fixed in place.

    No schema change: this file's `DataMapping` rows are deleted
    explicitly (individually, via `session.delete()` — the same
    pattern `mapping_service.confirm_mappings()` already uses to drop
    an unmapped column, rather than relying solely on the model's own
    `cascade="all, delete-orphan"`, so this works the same way against
    any SQLAlchemy-compatible session) before the `UploadedFile` row
    itself is deleted, avoiding a foreign-key violation. No detailed
    validation-result rows exist to clean up separately — only the
    overall VALIDATED/ERROR outcome is ever persisted, onto
    `upload_status` itself, per the Stage 7 design. The database rows
    are removed first and committed; the file on disk is then
    unlinked on a best-effort basis — an unlink failure is swallowed
    rather than raised, so the database (the source of truth for
    what's "uploaded") and the UI can never disagree about whether the
    file still exists, even if a stray file is left on disk.
    A no-op (returns without error) if `file_id` doesn't exist at all.
    """
    session = _session()
    record = session.get(UploadedFile, file_id)
    if record is None:
        return
    if record.upload_status == "VALIDATED":
        raise CannotDeleteValidatedFileError(
            "This file is already Validated and may have been used in a review, "
            "so it can't be removed. If you need to replace it, upload the "
            "corrected file separately."
        )
    stored_path = Path(record.stored_path)

    mapping_stmt = select(DataMapping).where(DataMapping.file_id == file_id)
    for mapping_row in session.scalars(mapping_stmt).all():
        session.delete(mapping_row)

    session.delete(record)
    session.commit()
    try:
        stored_path.unlink(missing_ok=True)
    except OSError:
        pass  # best-effort disk cleanup only — the database rows are already gone
