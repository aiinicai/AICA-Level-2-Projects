"""
Loads validated + user-confirmed data for rule engines to read (Stage 8
requirement: "The Accounting Engine should consume only: validated +
user-confirmed mapped data. It must not operate directly on unvalidated
uploads.").

Design decision (flagged, not a schema change): rather than persisting
mapped rows into `transactions`/`fixed_assets`/`gst_line_items`/
`tds_line_items` (all three approved since Stage 3 but never yet
populated by anything), this module keeps Stage 6/7's established
pattern — data is re-derived live from the immutable uploaded file
bytes plus the confirmed `DataMapping` rows, every time a rule engine
runs, rather than duplicated into a second, potentially-stale, on-disk
copy. Those three tables remain exactly as approved and available for
a later stage to populate if cross-rule reuse or performance ever
warrants it; nothing about them changes here.

Only files with `upload_status == "VALIDATED"` are read — a MAPPED-but-
not-yet-validated, or UPLOADED, file contributes nothing, per the
Stage 8 instruction.

Stage 19 addition — `attach_transaction_ids()`: the design decision
above (re-derive live, never persist a second copy) still holds for
every rule engine's own read of the data. What's new is narrower: when
a review is actually RUN (never on a read-only preview — see each
review service's own `preview_*_review()` docstring, which promises
"touches nothing"), this engagement's `transactions` table rows
(existing Stage 3 schema, unused until now) are refreshed from that
same live-derived data, and each freshly-created row's real database
`transaction_id` is written back onto the exact same `MappedRow`
object already in memory — a direct object reference, not a lookup by
file_id/row_index or by content, so two identical-looking rows (same
date, same account, same amount) can never be confused with each
other. This lets a rule module that flags one specific row record
*which* row via `ExceptionDraft.related_transaction_id`, which the
Query & Working Papers screen and its Excel export then read back to
show Account Name/Date next to a finding, instead of always blank.
Every prior transaction row for the engagement is deleted and
regenerated on each run (not incrementally updated), so this can never
drift out of sync with the source files the way a second, independently
-maintained copy could — it is a same-run materialization, not an
independent store. No schema change: `transactions` already existed
(Stage 3) with exactly the columns this needs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select

from app import extensions
from app.mapping.structure_detector import detect_structure, load_data_rows, split_source_column
from app.models.exceptions import ExceptionRecord
from app.models.transactions import Transaction
from app.services import mapping_service, upload_service
from app.utils.currency import CurrencyParseError, rupees_to_paise
from app.validation.data_quality import field_kind

# The dataset types that map onto the generic `transactions` table's
# columns (Transaction.dataset_type's own approved enum). FIXED_ASSETS/
# GST/TDS are deliberately excluded here — those have their own
# structured tables (fixed_assets / gst_line_items / tds_line_items,
# Stage 3 schema) with different, type-specific fields, and populating
# those is a larger, separate piece of work not needed for this fix
# (Account Name / Date on the Query & Working Papers screen only needs
# the generic ledger-style fields every other dataset type already
# shares). A finding raised against a FIXED_ASSETS/GST/TDS row still
# shows blank Account Name/Date, same as before — not silently changed.
TRANSACTION_DATASET_TYPES = {
    "TB", "GL", "JE", "SALES", "PURCHASE", "BANK", "AR", "AP", "PRIOR_YEAR", "OTHER",
}

# Target fields that map directly onto a Transaction column of the same
# name — every one of these already exists in column_mapper.py's
# CANONICAL_FIELDS for the dataset types above, so no new mapping
# vocabulary is introduced.
_TRANSACTION_COLUMNS = (
    "transaction_date", "account_name", "party_name", "description",
    "debit_amount", "credit_amount", "reference_number", "payment_mode", "is_manual_entry",
)


def _session():
    """See engagement_service._session()'s docstring — same reasoning."""
    return extensions.SessionLocal


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class MappedRow:
    file_id: int
    dataset_type: str  # the file's file_type, e.g. "TB", "FIXED_ASSETS"
    row_index: int
    values: dict[str, Any]  # target_field -> coerced value (paise int / ISO date str / float / str), or None
    # Populated only after attach_transaction_ids() runs (i.e. only
    # during a persisting run_*_review() call, never a preview) — the
    # real transactions.transaction_id row this MappedRow was written
    # as. None otherwise, including always for FIXED_ASSETS/GST/TDS
    # rows (see TRANSACTION_DATASET_TYPES above).
    transaction_id: int | None = field(default=None)


def _is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _coerce_value(target_field: str, raw) -> Any:
    """Best-effort coercion of one raw cell into the type its target
    field expects. Anything unparseable becomes None (the same value a
    genuinely blank cell produces) — Stage 7's Data Quality screen is
    where a professional finds out *why* a value was unusable; a rule
    reading it here only needs to know whether a usable value exists."""
    if _is_blank(raw):
        return None
    kind = field_kind(target_field)
    if kind == "amount":
        try:
            return rupees_to_paise(raw)
        except CurrencyParseError:
            return None
    if kind == "date":
        parsed = pd.to_datetime(raw, dayfirst=True, errors="coerce")
        return None if parsed is pd.NaT or pd.isna(parsed) else parsed.date().isoformat()
    if kind == "rate":
        try:
            return float(str(raw).strip().replace("%", ""))
        except ValueError:
            return None
    return str(raw).strip()


def load_mapped_rows(file_record) -> list[MappedRow]:
    """Only meaningful for a VALIDATED file — callers should already be
    filtering to that, but this does not itself re-check the status, to
    keep it a pure "given this file, load its confirmed data" function
    (the VALIDATED gate lives in load_engagement_dataset() below, the
    one place every rule engine actually enters through)."""
    mappings = mapping_service.get_confirmed_mappings(file_record.file_id)
    if not mappings:
        return []

    sheet_name, _first_column_key = split_source_column(mappings[0].source_column)
    file_bytes = Path(file_record.stored_path).read_bytes()
    extension = Path(file_record.stored_path).suffix.lower()

    structure = detect_structure(file_bytes, extension, sheet_name)
    column_key_to_position = {c.column_key: c.position for c in structure.columns}
    data = load_data_rows(file_bytes, extension, sheet_name, structure.header_row_index)

    resolved = []  # (target_field, position)
    for m in mappings:
        _sheet, column_key = split_source_column(m.source_column)
        position = column_key_to_position.get(column_key)
        if position is not None and position in data.columns:
            resolved.append((m.target_field, position))

    rows = []
    for row_index in range(len(data)):
        values = {
            target_field: _coerce_value(target_field, data.iloc[row_index, position])
            for target_field, position in resolved
        }
        rows.append(MappedRow(
            file_id=file_record.file_id, dataset_type=file_record.file_type,
            row_index=row_index, values=values,
        ))
    return rows


def load_engagement_dataset(engagement_id: int) -> dict[str, list[MappedRow]]:
    """dataset_type (file_type, e.g. "TB", "FIXED_ASSETS") -> every
    confirmed-mapped row from every VALIDATED file of that type for this
    engagement. A file that is UPLOADED, MAPPED, or ERROR contributes
    nothing — this is the single point that enforces "validated +
    user-confirmed mapped data only" for every rule engine."""
    by_type: dict[str, list[MappedRow]] = {}
    for upload in upload_service.list_uploads(engagement_id):
        if upload.upload_status != "VALIDATED":
            continue
        rows = load_mapped_rows(upload)
        by_type.setdefault(upload.file_type, []).extend(rows)
    return by_type


def _transaction_content_key(get) -> tuple:
    """`get` is either a Transaction row's own attribute getter
    (`lambda c: getattr(txn, c)`) or a MappedRow's values dict getter
    (`lambda c: row.values.get(c)`) — same key shape either way, so a
    freshly-derived row and a previously-persisted Transaction can be
    compared for "is this the same row" without any new column. Two
    genuinely identical rows (same date/account/amount/etc, e.g. two
    same-day ₹100 cash entries) simply become two entries under the
    same key — `attach_transaction_ids()` below pairs them up one to
    one rather than confusing them, since each is only ever reused
    once (see `used_ids`)."""
    return tuple(get(c) for c in _TRANSACTION_COLUMNS)


def attach_transaction_ids(engagement_id: int, dataset: dict[str, list[MappedRow]]) -> None:
    """Stage 19: refreshes this engagement's `transactions` table rows
    from `dataset` (already loaded by `load_engagement_dataset()`) and
    writes each row's real `transaction_id` back onto the exact same
    `MappedRow` object still referenced inside `dataset`.

    MUST be called only from a persisting run_*_review() — never from a
    preview_*_review(), whose docstring promises "touches the database
    at all" is false.

    NOT a blind delete-and-recreate (an earlier version of this
    function was, and broke the very first time a review was run
    twice): an `ExceptionRecord` can hold a `related_transaction_id`
    pointing at one of these rows — including one from a PREVIOUS run,
    still on file because a reviewer already started working on it
    (`_clear_stale_automated_exceptions()` in each review service
    preserves those) — so a transaction row a finding still points to
    can never be deleted; the database's own foreign key would refuse
    it anyway. Instead: a freshly-derived row is matched, by content
    (`_transaction_content_key()`), against this engagement's existing
    `transactions` rows — an unchanged row is reused as-is (same
    transaction_id a previous run may have already linked a finding
    to), a genuinely new row is inserted, and an existing row that no
    longer matches anything this run AND is not referenced by any
    current finding is removed as stale. No schema change: matching by
    content, not a new row-identity column.

    FIXED_ASSETS/GST/TDS rows are skipped (see TRANSACTION_DATASET_TYPES)
    — their MappedRow.transaction_id stays None, exactly as before this
    function existed."""
    session = _session()

    existing = list(session.scalars(
        select(Transaction).where(Transaction.engagement_id == engagement_id)
    ).all())
    existing_by_key: dict[tuple, list[Transaction]] = {}
    for txn in existing:
        key = _transaction_content_key(lambda c, txn=txn: getattr(txn, c))
        existing_by_key.setdefault(key, []).append(txn)

    # Never delete a transaction row a real finding still points to,
    # even one from a run before this function existed.
    referenced_ids = {
        exc.related_transaction_id
        for exc in session.scalars(
            select(ExceptionRecord).where(ExceptionRecord.engagement_id == engagement_id)
        ).all()
        if exc.related_transaction_id is not None
    }

    now = _now_iso()
    used_ids: set[int] = set()
    created: list[tuple[MappedRow, Transaction]] = []
    for dataset_type, rows in dataset.items():
        if dataset_type not in TRANSACTION_DATASET_TYPES:
            continue
        for row in rows:
            key = _transaction_content_key(lambda c: row.values.get(c))
            reusable = next(
                (t for t in existing_by_key.get(key, []) if t.transaction_id not in used_ids), None,
            )
            if reusable is not None:
                row.transaction_id = reusable.transaction_id
                used_ids.add(reusable.transaction_id)
                continue
            txn = Transaction(
                engagement_id=engagement_id,
                file_id=row.file_id,
                dataset_type=row.dataset_type,
                created_at=now,
                **{col: row.values.get(col) for col in _TRANSACTION_COLUMNS},
            )
            session.add(txn)
            created.append((row, txn))

    session.commit()  # assigns transaction_id to every newly-created row above
    for row, txn in created:
        row.transaction_id = txn.transaction_id
        used_ids.add(txn.transaction_id)

    for txn in existing:
        if txn.transaction_id in used_ids or txn.transaction_id in referenced_ids:
            continue  # still current this run, or still pointed to by a finding
        session.delete(txn)
    session.commit()
