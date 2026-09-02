"""
Data Quality validation engine (Stage 7 requirements #9/#10): given a
file's *confirmed* column mappings, checks that dates parse, that
amounts parse (including Indian-formatted / text-stored numbers), and
that every essential field for the file's declared type has actually
been mapped — then produces one clear result.

Deliberately NOT an Accounting/Audit/Tax rule engine: nothing here
judges whether a debit/credit balances, whether a rate is correct, or
any other analytical/statutory question — Blueprint Section 9 divides
that into later, not-yet-approved stages. This module only asks "is the
data usable" (parses, present), never "is the data right."

Detailed per-column results are computed on demand from the confirmed
mappings + the original uploaded file every time this runs — they are
NOT persisted row-by-row (that would need a new table, which Stage 7's
own instruction says to stop and ask about before adding; re-deriving
them from the immutable uploaded file is free and avoids that
question entirely). Only the overall outcome is written back, and only
onto the already-approved `uploaded_files.upload_status` field — see
`app/services/validation_service.py`.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import pandas as pd

from app.utils.currency import CurrencyParseError, rupees_to_paise

_CURRENCY_CLEAN_RE = re.compile(r"[₹,\s]")

# target_field -> "date" | "amount" | "rate" | "text"
_DATE_FIELDS = {"transaction_date", "invoice_date", "date_put_to_use", "deposit_date"}
_AMOUNT_FIELDS = {
    "debit_amount", "credit_amount", "original_cost_paise", "opening_wdv_paise",
    "additions_paise", "deletions_paise", "book_depreciation_amount_paise",
    "closing_wdv_paise", "taxable_value_paise", "cgst_paise", "sgst_paise",
    "igst_paise", "amount_deducted_paise",
}
_RATE_FIELDS = {"book_depreciation_rate", "tax_depreciation_rate", "tax_rate", "rate_applied"}


def _field_kind(target_field: str) -> str:
    if target_field in _DATE_FIELDS:
        return "date"
    if target_field in _AMOUNT_FIELDS:
        return "amount"
    if target_field in _RATE_FIELDS:
        return "rate"
    return "text"


# Public alias — Stage 8's dataset_service.py needs the same
# field-kind classification (to know how to coerce a raw cell into a
# real Python value for rule evaluation) and reuses this rather than
# duplicating the date/amount/rate field lists a second time.
field_kind = _field_kind


# Fields that must be mapped for the file's data to be usable at all.
# A reasonable-effort default classification for Stage 7's own scope
# (structural completeness), not a statutory or accounting rule — the
# same kind of disclosed-but-not-gated judgment call as Stage 5's
# applicability wording. Flagged in the Stage 7 report.
ESSENTIAL_FIELDS: dict[str, list[str]] = {
    "TB": ["account_name"],
    "GL": ["transaction_date", "account_name"],
    "JE": ["transaction_date", "account_name"],
    "SALES": ["party_name"],
    "PURCHASE": ["party_name"],
    "BANK": ["transaction_date"],
    "AR": ["party_name"],
    "AP": ["party_name"],
    "FIXED_ASSETS": ["asset_description"],
    "GST": ["gstin", "invoice_number"],
    "TDS": ["deductee_pan", "section_code"],
    "PRIOR_YEAR": [],
    "OTHER": [],
}

# At least one field from each group must be mapped.
ESSENTIAL_ANY_OF: dict[str, list[list[str]]] = {
    "TB": [["debit_amount", "credit_amount"]],
    "GL": [["debit_amount", "credit_amount"]],
    "JE": [["debit_amount", "credit_amount"]],
    # A Sales/Purchase Register commonly dates each row by its invoice
    # date rather than a generic "transaction date" column — both mean
    # the same thing for this file type, so either satisfies the
    # essential "this row needs a date" requirement (Stage 18 fix, same
    # disclosed-judgment-call basis as the rest of this dict — see the
    # comment above ESSENTIAL_FIELDS).
    "SALES": [["debit_amount", "credit_amount", "taxable_value_paise"], ["transaction_date", "invoice_date"]],
    "PURCHASE": [["debit_amount", "credit_amount", "taxable_value_paise"], ["transaction_date", "invoice_date"]],
    "BANK": [["debit_amount", "credit_amount"]],
    "AR": [["debit_amount", "credit_amount"]],
    "AP": [["debit_amount", "credit_amount"]],
    "FIXED_ASSETS": [],
    "GST": [["taxable_value_paise"]],
    "TDS": [["amount_deducted_paise"]],
    "PRIOR_YEAR": [],
    "OTHER": [],
}


def _is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _evaluate_amount_cell(value) -> str:
    """One of "blank" / "valid_native" (already numeric) /
    "valid_text" (text that parses fine once cleaned — the "numeric
    values stored as text" case) / "invalid"."""
    if _is_blank(value):
        return "blank"
    if isinstance(value, (int, float)):
        return "valid_native"
    if isinstance(value, str):
        cleaned = _CURRENCY_CLEAN_RE.sub("", value.strip())
        try:
            rupees_to_paise(cleaned)
            return "valid_text"
        except CurrencyParseError:
            return "invalid"
    return "invalid"


def _evaluate_rate_cell(value) -> str:
    if _is_blank(value):
        return "blank"
    if isinstance(value, (int, float)):
        return "valid_native"
    if isinstance(value, str):
        cleaned = value.strip().replace("%", "")
        try:
            float(cleaned)
            return "valid_text"
        except ValueError:
            return "invalid"
    return "invalid"


def _evaluate_date_cell(value) -> str:
    if _is_blank(value):
        return "blank"
    parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
    if parsed is pd.NaT or pd.isna(parsed):
        return "invalid"
    return "valid_native" if not isinstance(value, str) else "valid_text"


@dataclass
class ColumnReport:
    source_column: str
    target_field: str
    target_label: str
    kind: str
    total: int
    is_required: bool = False
    blank_count: int = 0
    valid_count: int = 0
    stored_as_text_count: int = 0
    invalid_count: int = 0
    sample_invalid_values: list = field(default_factory=list)

    @property
    def penalized_blank_count(self) -> int:
        """Blanks that count against the quality score — only when this
        field is required. A blank in an optional field is informational
        only (Stage 7 correction #2)."""
        return self.blank_count if self.is_required else 0

    @property
    def informational_blank_count(self) -> int:
        return 0 if self.is_required else self.blank_count


@dataclass
class ValidationResult:
    status: str  # "VALIDATED" or "ERROR"
    file_type: str
    total_rows: int
    mapped_field_count: int
    missing_essential_fields: list[str]
    column_reports: list[ColumnReport]
    data_quality_score: float  # 0-100
    messages: list[str] = field(default_factory=list)


def _missing_essential_fields(file_type: str, mapped_fields: set[str]) -> list[str]:
    missing = [f for f in ESSENTIAL_FIELDS.get(file_type, []) if f not in mapped_fields]
    for group in ESSENTIAL_ANY_OF.get(file_type, []):
        if not any(f in mapped_fields for f in group):
            missing.append(" or ".join(group))
    return missing


def _field_is_required(file_type: str, target_field: str) -> bool:
    """Stage 7 correction #2: whether a *mapped* field counts as
    "required" for scoring purposes — i.e. whether a blank value in it
    should be graded (and so can lower the score) rather than treated as
    purely informational. A field is required if it's one of the file
    type's `ESSENTIAL_FIELDS`, or a member of one of its
    `ESSENTIAL_ANY_OF` groups (e.g. `debit_amount` is required for a TB
    once it's mapped, because it's one of the two fields satisfying
    "at least one of debit/credit must be mapped") — regardless of
    whether a sibling in that group is also mapped, since either one
    being blank is still a real gap in that row's data."""
    if target_field in ESSENTIAL_FIELDS.get(file_type, []):
        return True
    for group in ESSENTIAL_ANY_OF.get(file_type, []):
        if target_field in group:
            return True
    return False


def run_validation(
    file_type: str,
    data: pd.DataFrame,
    mappings: list,
    column_key_to_position: dict[str, int],
) -> ValidationResult:
    """`data` is a DataFrame of data rows only (see
    `structure_detector.load_data_rows`), columns keyed by 0-based
    position. `mappings` is a list of confirmed DataMapping rows for
    this file (already filtered to `is_user_confirmed=True` by the
    caller). `column_key_to_position` comes from re-running
    `structure_detector.detect_structure()` against this same file/sheet
    (see `app/services/validation_service.py`) — it is how a mapping's
    stored `source_column` (a text key) gets back to a physical column
    position, without persisting that position anywhere."""
    from app.mapping.column_mapper import CANONICAL_FIELDS
    from app.mapping.structure_detector import split_source_column

    total_rows = len(data)
    mapped_fields = {m.target_field for m in mappings}
    missing_essential = _missing_essential_fields(file_type, mapped_fields)

    column_reports: list[ColumnReport] = []
    for m in mappings:
        _sheet_name, column_key = split_source_column(m.source_column)
        position = column_key_to_position.get(column_key)
        if position is None or position not in data.columns:
            continue

        kind = _field_kind(m.target_field)
        series = data[position]
        blank = valid_native = valid_text = invalid = 0
        sample_invalid = []
        for value in series:
            if kind == "date":
                outcome = _evaluate_date_cell(value)
            elif kind == "amount":
                outcome = _evaluate_amount_cell(value)
            elif kind == "rate":
                outcome = _evaluate_rate_cell(value)
            else:
                outcome = "blank" if _is_blank(value) else "valid_native"

            if outcome == "blank":
                blank += 1
            elif outcome == "valid_native":
                valid_native += 1
            elif outcome == "valid_text":
                valid_text += 1
            else:
                invalid += 1
                if len(sample_invalid) < 5:
                    sample_invalid.append(value)

        column_reports.append(ColumnReport(
            source_column=m.source_column,
            target_field=m.target_field,
            target_label=CANONICAL_FIELDS.get(m.target_field, (m.target_field, []))[0],
            kind=kind,
            total=len(series),
            is_required=_field_is_required(file_type, m.target_field),
            blank_count=blank,
            valid_count=valid_native + valid_text,
            stored_as_text_count=valid_text,
            invalid_count=invalid,
            sample_invalid_values=sample_invalid,
        ))

    # Stage 7 correction #2: blanks are no longer lumped in as
    # "not invalid, so fine." A cell is graded (counted toward the
    # score) as either a pass (valid) or a fail (invalid, OR blank in a
    # *required* field); a blank in an *optional* field is excluded from
    # grading entirely — informational, never a penalty either way. If
    # nothing is gradable at all (e.g. every mapped field is optional
    # and entirely blank), the score is 100 — there is nothing to fail.
    total_invalid = sum(r.invalid_count for r in column_reports)
    total_blank_required = sum(r.penalized_blank_count for r in column_reports)
    total_blank_optional = sum(r.informational_blank_count for r in column_reports)
    total_valid = sum(r.valid_count for r in column_reports)

    graded_cells = total_valid + total_invalid + total_blank_required
    failed_cells = total_invalid + total_blank_required
    data_quality_score = 100.0 if graded_cells == 0 else round(100.0 * (1 - failed_cells / graded_cells), 1)

    messages = []
    if missing_essential:
        messages.append(
            "Missing essential column mapping(s) for a " + file_type + " file: "
            + ", ".join(missing_essential) + "."
        )
    if total_rows == 0:
        messages.append("This file has no data rows to validate.")
    if total_invalid:
        messages.append(f"{total_invalid} value(s) across mapped columns could not be parsed — see details below.")
    if total_blank_required:
        messages.append(
            f"{total_blank_required} blank value(s) in required field(s) reduced the quality score."
        )
    if total_blank_optional:
        messages.append(
            f"{total_blank_optional} blank value(s) in optional field(s) — informational only, not scored."
        )

    status = "ERROR" if (missing_essential or total_rows == 0) else "VALIDATED"

    return ValidationResult(
        status=status,
        file_type=file_type,
        total_rows=total_rows,
        mapped_field_count=len(mappings),
        missing_essential_fields=missing_essential,
        column_reports=column_reports,
        data_quality_score=data_quality_score,
        messages=messages,
    )
