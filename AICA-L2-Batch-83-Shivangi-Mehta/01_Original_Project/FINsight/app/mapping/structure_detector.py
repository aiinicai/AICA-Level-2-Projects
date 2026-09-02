"""
File structure detection (Stage 7, requirement #1/#2/#3/#4 of the Stage
7 instruction): given raw uploaded bytes, work out what is actually in
the file — which sheets exist, which row is really the header, what the
columns are, and which of those columns are duplicates or blank —
*before* anything is suggested or mapped.

Pure, stateless functions: everything here takes file bytes (already
read into memory by the caller, exactly like `upload_service.py`
already does for row-counting) and returns plain data. Nothing is
persisted from this module — see `app/services/mapping_service.py` for
the one place structure/mapping results get written to the database,
and only once a user explicitly confirms them.

Multi-sheet design note (flagged in the Stage 7 report, not gated as a
schema change): a selected sheet is never stored as a new column
anywhere. Instead, once a sheet is chosen for mapping, every confirmed
`DataMapping.source_column` for that file is written as
"{sheet_name}::{column_key}" instead of a bare column name (see
`make_source_column`/`split_source_column` below) — a values-only
convention inside the *existing* TEXT column, not a schema change. The
sheet a file's data should be read from downstream is recovered by
re-parsing any one of its confirmed mappings, which is possible because
this module is a pure function of the immutable, already-stored file
bytes — nothing here needs to remember "which sheet was picked" between
requests.

Offline-first: everything below is local pandas/openpyxl parsing of
bytes already in memory — no network call, no external/cloud service.
"""
from __future__ import annotations

import io
import math
import re
from dataclasses import dataclass, field

import pandas as pd

SHEET_DELIM = "::"

_HEADER_SCAN_ROWS = 5
_NUMERIC_CLEAN_RE = re.compile(r"[₹,\s]")


class StructureDetectionError(Exception):
    """Raised when the file can't be parsed as CSV/Excel at all — same
    class of failure `upload_service.UnreadableFileError` guards
    against, kept as a separate exception here since this module has no
    dependency on `upload_service` (and shouldn't need one just to
    report "this isn't readable")."""


@dataclass
class ColumnInfo:
    position: int          # 0-based physical column position in the sheet
    raw_name: str          # exactly what's in the header cell (possibly "")
    column_key: str        # disambiguated, always-unique label — see _build_columns()
    is_blank: bool
    is_duplicate: bool


@dataclass
class StructureResult:
    sheet_name: str | None          # None for CSV / a single-sheet file
    available_sheets: list[str] | None   # None for CSV; list of names for .xlsx
    header_row_index: int
    header_detection_warning: str | None
    columns: list[ColumnInfo]
    duplicate_column_names: list[str]
    blank_column_count: int
    data_row_count: int
    warnings: list[str] = field(default_factory=list)


def list_sheets(file_bytes: bytes, extension: str) -> list[str] | None:
    """None for CSV (no sheet concept). A list of sheet names for
    .xlsx — always at least one entry."""
    if extension != ".xlsx":
        return None
    try:
        workbook = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
        return list(workbook.sheet_names)
    except Exception as exc:
        raise StructureDetectionError(
            "Could not read this workbook's sheets — is it corrupted or the wrong format?"
        ) from exc


def _read_raw(file_bytes: bytes, extension: str, sheet_name: str | None) -> pd.DataFrame:
    """Every cell as pandas naturally infers it (numbers stay numeric,
    text stays text) — deliberately NOT forced to dtype=str, so that
    validate_dataset() downstream can tell "this cell is genuinely a
    number" from "this cell is text that merely looks numeric" (Stage 7
    requirement: detecting numeric values stored as text). `header=None`
    so the header row itself is read as ordinary row 0 — this module
    decides which row is the header, not pandas."""
    try:
        buf = io.BytesIO(file_bytes)
        if extension == ".csv":
            return pd.read_csv(buf, header=None, dtype=object)
        return pd.read_excel(buf, sheet_name=sheet_name, header=None, dtype=object, engine="openpyxl")
    except Exception as exc:
        kind = extension.lstrip(".").upper()
        raise StructureDetectionError(
            f"Could not read this file as {kind} — is it corrupted or the wrong format?"
        ) from exc


def _is_blank_cell(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _looks_numeric(value) -> bool:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return not (isinstance(value, float) and math.isnan(value))
    if isinstance(value, str):
        cleaned = _NUMERIC_CLEAN_RE.sub("", value.strip())
        if cleaned in ("", "-", "."):
            return False
        try:
            float(cleaned)
            return True
        except ValueError:
            return False
    return False


def _header_likeness_score(row_values: list) -> float:
    """Higher = more plausibly a header row. Blends three signals: how
    much of the row is non-blank (a title row usually has one cell and
    is otherwise empty), how much of the non-blank content is text
    rather than numbers (headers are names, data is usually numbers for
    a financial file), and how unique the non-blank cells are (repeated
    values in a row is more typical of data than of column names)."""
    total = len(row_values)
    if total == 0:
        return 0.0
    non_blank = [v for v in row_values if not _is_blank_cell(v)]
    if not non_blank:
        return 0.0

    coverage_ratio = len(non_blank) / total
    numeric_count = sum(1 for v in non_blank if _looks_numeric(v))
    string_ratio = 1 - (numeric_count / len(non_blank))
    normalized = [str(v).strip().lower() for v in non_blank]
    unique_ratio = len(set(normalized)) / len(non_blank)

    score = 0.35 * string_ratio + 0.15 * unique_ratio + 0.50 * coverage_ratio
    if len(non_blank) <= 1 and total > 1:
        # A single populated cell spanning an otherwise-empty row is
        # characteristic of a report title, not a header — uniqueness
        # is trivially 1.0 for a lone value, which would otherwise
        # score this deceptively high.
        score *= 0.3
    return round(score, 3)


def _detect_header_row(raw_df: pd.DataFrame) -> tuple[int, str | None]:
    """Returns (header_row_index, warning_or_None). Defaults to row 0
    (the overwhelmingly common case) unless a later row in the first
    few rows scores clearly better AND row 0 itself scores poorly —
    e.g. a report title occupying only the first cell of row 0, with
    the real column headers one row down."""
    scan_limit = min(_HEADER_SCAN_ROWS, len(raw_df))
    if scan_limit == 0:
        return 0, "This sheet appears to be empty."

    scores = [_header_likeness_score(list(raw_df.iloc[i])) for i in range(scan_limit)]
    row0_score = scores[0]

    best_index = 0
    best_score = row0_score
    for i in range(1, scan_limit):
        if scores[i] > best_score:
            best_index, best_score = i, scores[i]

    if best_index != 0 and row0_score < 0.5 and (best_score - row0_score) >= 0.2:
        return best_index, (
            f"Row 1 didn't look like a header row (it may be a title or blank row) — "
            f"row {best_index + 1} was used as the header instead. Please check this is correct."
        )

    if row0_score < 0.5:
        return 0, (
            "The header row could not be detected with confidence. Row 1 was used as the "
            "header — please review the columns below carefully before mapping."
        )

    return 0, None


def _build_columns(header_row: list) -> tuple[list[ColumnInfo], list[str]]:
    """Assigns every physical column a unique `column_key`: the raw
    header text if it's neither blank nor duplicated, otherwise a
    disambiguated label carrying its position — so every column,
    including a blank or repeated one, can still be individually
    selected and mapped without colliding with another column under
    `data_mappings`' UNIQUE(file_id, source_column) constraint."""
    raw_names = ["" if _is_blank_cell(v) else str(v).strip() for v in header_row]

    seen_counts: dict[str, int] = {}
    for name in raw_names:
        if name:
            seen_counts[name] = seen_counts.get(name, 0) + 1
    duplicate_names = sorted(name for name, count in seen_counts.items() if count > 1)

    columns: list[ColumnInfo] = []
    for position, name in enumerate(raw_names):
        is_blank = name == ""
        is_duplicate = (not is_blank) and seen_counts.get(name, 0) > 1
        if is_blank:
            column_key = f"(blank column {position + 1})"
        elif is_duplicate:
            column_key = f"{name} (col {position + 1})"
        else:
            column_key = name
        columns.append(ColumnInfo(
            position=position, raw_name=name, column_key=column_key,
            is_blank=is_blank, is_duplicate=is_duplicate,
        ))
    return columns, duplicate_names


def detect_structure(file_bytes: bytes, extension: str, sheet_name: str | None = None) -> StructureResult:
    """The single entry point for Stage 7 requirements #1, #3 and #4.
    For a multi-sheet .xlsx, `sheet_name` must be supplied by the
    caller (the Mapping screen asks the user to pick one first — see
    `app/api/mapping_bp.py`) — this function does not guess a default
    sheet."""
    available_sheets = list_sheets(file_bytes, extension)
    raw_df = _read_raw(file_bytes, extension, sheet_name)

    header_row_index, header_warning = _detect_header_row(raw_df)
    header_row = list(raw_df.iloc[header_row_index]) if len(raw_df) > header_row_index else []
    columns, duplicate_names = _build_columns(header_row)

    data_row_count = max(len(raw_df) - (header_row_index + 1), 0)
    blank_column_count = sum(1 for c in columns if c.is_blank)

    warnings: list[str] = []
    if header_warning:
        warnings.append(header_warning)
    if duplicate_names:
        warnings.append(
            f"Duplicate column headers found: {', '.join(duplicate_names)}. "
            f"Each occurrence is listed separately below so it can be mapped individually."
        )
    if blank_column_count:
        warnings.append(
            f"{blank_column_count} column(s) have a blank header and will need to be reviewed manually."
        )
    if data_row_count == 0:
        warnings.append("No data rows were found below the header row.")

    return StructureResult(
        sheet_name=sheet_name,
        available_sheets=available_sheets,
        header_row_index=header_row_index,
        header_detection_warning=header_warning,
        columns=columns,
        duplicate_column_names=duplicate_names,
        blank_column_count=blank_column_count,
        data_row_count=data_row_count,
        warnings=warnings,
    )


def load_data_rows(file_bytes: bytes, extension: str, sheet_name: str | None, header_row_index: int) -> pd.DataFrame:
    """The data rows only (header and anything above it excluded),
    columns kept as plain 0-based positions (`df[0]`, `df[1]`, ...) —
    matching `ColumnInfo.position` above — deliberately not pandas
    column *names*, so lookups never depend on pandas' own
    auto-renaming of blank/duplicate headers. Used by
    `app/validation/data_quality.py` once mappings are confirmed."""
    raw_df = _read_raw(file_bytes, extension, sheet_name)
    data = raw_df.iloc[header_row_index + 1:].reset_index(drop=True)
    data.columns = range(data.shape[1])
    return data


def make_source_column(sheet_name: str | None, column_key: str) -> str:
    if sheet_name is None:
        return column_key
    return f"{sheet_name}{SHEET_DELIM}{column_key}"


def split_source_column(source_column: str) -> tuple[str | None, str]:
    if SHEET_DELIM in source_column:
        sheet_name, column_key = source_column.split(SHEET_DELIM, 1)
        return sheet_name, column_key
    return None, source_column
