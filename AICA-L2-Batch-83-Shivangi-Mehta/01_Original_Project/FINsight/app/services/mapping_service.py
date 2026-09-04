"""
DataMapping persistence (Stage 7). Same dynamic-session pattern as
`engagement_service.py`/`upload_service.py` — see either module's
`_session()` docstring.

Only confirmed mappings are ever written here. A suggestion generated
by `app/mapping/column_mapper.py` is computed live on every GET request
and is never persisted until the user explicitly submits the mapping
form — "Requiring user confirmation before mappings are used
downstream" (Stage 7 requirement #7) is enforced by this module simply
never writing an unconfirmed row in the first place, not by a separate
confirm step on top of an already-stored draft. No new tables/fields
are used — every field here already exists on the approved
`app/models/uploads.py::DataMapping`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app import extensions
from app.models.uploads import DataMapping, UploadedFile


def _session():
    return extensions.SessionLocal


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_confirmed_mappings(file_id: int) -> list[DataMapping]:
    stmt = select(DataMapping).where(
        DataMapping.file_id == file_id,
        DataMapping.is_user_confirmed == True,  # noqa: E712 — `.is_(True)` would be the SQLAlchemy style preference, but `==` is what the rest of this codebase already uses for boolean filters and compiles identically
    )
    return list(_session().scalars(stmt).all())


def confirm_mappings(file_id: int, confirmed: list[dict]) -> list[DataMapping]:
    """`confirmed` is a list of {"source_column": str, "target_field": str,
    "confidence_score": float | None} — exactly the columns the user
    chose to keep mapped in this submission. Any source_column NOT in
    this list that had a previously-confirmed mapping is removed (the
    user unmapped it this time round); everything in the list is
    upserted as confirmed. Keyed by (file_id, source_column) — the same
    pair the DB's own UNIQUE constraint is keyed on."""
    session = _session()

    existing_stmt = select(DataMapping).where(DataMapping.file_id == file_id)
    existing_by_column = {row.source_column: row for row in session.scalars(existing_stmt).all()}

    submitted_columns = {item["source_column"] for item in confirmed}
    now = _now_iso()

    for item in confirmed:
        row = existing_by_column.get(item["source_column"])
        if row is None:
            row = DataMapping(file_id=file_id, source_column=item["source_column"])
            session.add(row)
        row.target_field = item["target_field"]
        row.confidence_score = item.get("confidence_score")
        row.is_user_confirmed = True
        row.confirmed_at = now

    for source_column, row in existing_by_column.items():
        if source_column not in submitted_columns:
            session.delete(row)

    session.commit()
    return get_confirmed_mappings(file_id)


def mark_file_status(file_id: int, status: str) -> None:
    """Writes only the already-approved `uploaded_files.upload_status`
    enum (UPLOADED/MAPPED/VALIDATED/ERROR) — no new column."""
    session = _session()
    record = session.get(UploadedFile, file_id)
    if record is not None:
        record.upload_status = status
        session.commit()
