"""
Stage 7 — app/validation/data_quality.py. Pure pandas + the existing,
already-approved currency parser (app/utils/currency.py) — no Flask/
SQLAlchemy dependency, so `mappings` are plain fake objects here rather
than real DataMapping rows (this module only ever reads
`.source_column`/`.target_field` off them).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import pytest

from app.validation.data_quality import run_validation


class FakeMapping:
    def __init__(self, source_column, target_field):
        self.source_column = source_column
        self.target_field = target_field


def _data(rows: list[list]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df.columns = range(df.shape[1])
    return df


# --- date parsing (Indian day-first formats) -----------------------------

def test_valid_dates_in_multiple_common_formats_all_parse():
    data = _data([
        ["12-01-2026"],   # DD-MM-YYYY
        ["01/12/2026"],   # DD/MM/YYYY
        [pd.Timestamp("2026-03-05")],  # native datetime (already parsed by pandas on read)
    ])
    mappings = [FakeMapping("Date", "transaction_date")]
    result = run_validation("GL", data, mappings, {"Date": 0})
    report = result.column_reports[0]
    assert report.invalid_count == 0
    assert report.blank_count == 0
    assert report.valid_count == 3


def test_unparseable_date_flagged_invalid():
    data = _data([["12-01-2026"], ["not a date at all"], [""]])
    mappings = [FakeMapping("Date", "transaction_date")]
    result = run_validation("GL", data, mappings, {"Date": 0})
    report = result.column_reports[0]
    assert report.invalid_count == 1
    assert report.blank_count == 1
    assert "not a date at all" in report.sample_invalid_values


# --- amounts: Indian currency formats + numeric-as-text -----------------

def test_indian_grouped_currency_text_parses_as_valid_stored_as_text():
    data = _data([["1,00,000.50"], ["₹ 50,000"], [" 2,500 "]])
    mappings = [FakeMapping("Amount", "debit_amount")]
    result = run_validation("TB", data, mappings, {"Amount": 0})
    report = result.column_reports[0]
    assert report.invalid_count == 0
    assert report.stored_as_text_count == 3  # all three came in as text


def test_native_numeric_cell_not_counted_as_stored_as_text():
    data = _data([[100000], [50000.75]])
    mappings = [FakeMapping("Amount", "debit_amount")]
    result = run_validation("TB", data, mappings, {"Amount": 0})
    report = result.column_reports[0]
    assert report.stored_as_text_count == 0
    assert report.valid_count == 2


def test_unparseable_amount_text_flagged_invalid():
    data = _data([["not a number"], ["100000"]])
    mappings = [FakeMapping("Amount", "debit_amount")]
    result = run_validation("TB", data, mappings, {"Amount": 0})
    report = result.column_reports[0]
    assert report.invalid_count == 1
    assert "not a number" in report.sample_invalid_values


# --- essential fields --------------------------------------------------

def test_missing_essential_field_produces_error_status():
    data = _data([["Some Ref"]])
    mappings = [FakeMapping("Ref", "reference_number")]  # account_name never mapped
    result = run_validation("TB", data, mappings, {"Ref": 0})
    assert result.status == "ERROR"
    assert any("account_name" in m for m in result.missing_essential_fields)


def test_missing_amount_any_of_group_produces_error_status():
    # account_name mapped, but neither debit_amount nor credit_amount is.
    data = _data([["Cash"]])
    mappings = [FakeMapping("Account", "account_name")]
    result = run_validation("TB", data, mappings, {"Account": 0})
    assert result.status == "ERROR"
    assert any("debit_amount" in m for m in result.missing_essential_fields)


def test_all_essential_fields_present_and_clean_data_is_validated():
    data = _data([["Cash", 100000, 0], ["Sales", 0, 100000]])
    mappings = [
        FakeMapping("Account", "account_name"),
        FakeMapping("Debit", "debit_amount"),
        FakeMapping("Credit", "credit_amount"),
    ]
    result = run_validation("TB", data, mappings, {"Account": 0, "Debit": 1, "Credit": 2})
    assert result.status == "VALIDATED"
    assert result.data_quality_score == 100.0
    assert result.missing_essential_fields == []


def test_no_data_rows_is_an_error():
    data = _data([])
    mappings = [
        FakeMapping("Account", "account_name"),
        FakeMapping("Debit", "debit_amount"),
    ]
    result = run_validation("TB", data, mappings, {"Account": 0, "Debit": 1})
    assert result.status == "ERROR"
    assert result.total_rows == 0


def test_quality_score_reflects_partial_invalid_data_but_stays_validated_when_essentials_present():
    data = _data([["Cash", 100000], ["Sales", "not a number"]])
    mappings = [FakeMapping("Account", "account_name"), FakeMapping("Debit", "debit_amount")]
    result = run_validation("TB", data, mappings, {"Account": 0, "Debit": 1})
    assert result.status == "VALIDATED"  # essentials mapped — bad data noted, not blocked
    assert result.data_quality_score < 100.0


# --- Stage 7 correction #2: blank vs invalid scoring --------------------

def test_100_percent_when_every_mapped_value_required_and_optional_is_valid():
    data = _data([["Cash", 100000, "REF-1"], ["Sales", 50000, "REF-2"]])
    mappings = [
        FakeMapping("Account", "account_name"),   # required
        FakeMapping("Debit", "debit_amount"),      # required (any-of group)
        FakeMapping("Ref", "reference_number"),    # optional
    ]
    result = run_validation("TB", data, mappings, {"Account": 0, "Debit": 1, "Ref": 2})
    assert result.data_quality_score == 100.0
    assert result.status == "VALIDATED"


def test_invalid_values_reduce_the_score():
    data = _data([["Cash", 100000], ["Sales", "not a number"]])
    mappings = [FakeMapping("Account", "account_name"), FakeMapping("Debit", "debit_amount")]
    result = run_validation("TB", data, mappings, {"Account": 0, "Debit": 1})
    # 3 valid + 1 invalid graded cells -> 75.0
    assert result.data_quality_score == 75.0


def test_blank_required_field_reduces_the_score():
    data = _data([["Cash", 100000], ["Sales", ""]])
    mappings = [FakeMapping("Account", "account_name"), FakeMapping("Debit", "debit_amount")]
    result = run_validation("TB", data, mappings, {"Account": 0, "Debit": 1})
    debit_report = next(r for r in result.column_reports if r.target_field == "debit_amount")
    assert debit_report.is_required is True
    assert debit_report.blank_count == 1
    # 3 valid + 1 required-blank graded as a failure -> 75.0, NOT 100.
    assert result.data_quality_score == 75.0
    assert result.data_quality_score != 100.0


def test_blank_optional_field_does_not_reduce_the_score():
    data = _data([["Cash", 100000, ""], ["Sales", 50000, ""]])
    mappings = [
        FakeMapping("Account", "account_name"),
        FakeMapping("Debit", "debit_amount"),
        FakeMapping("Ref", "reference_number"),  # optional for TB, entirely blank
    ]
    result = run_validation("TB", data, mappings, {"Account": 0, "Debit": 1, "Ref": 2})
    ref_report = next(r for r in result.column_reports if r.target_field == "reference_number")
    assert ref_report.is_required is False
    assert ref_report.blank_count == 2
    assert result.data_quality_score == 100.0  # optional blanks are informational only


def test_invalid_value_in_an_optional_field_still_penalizes_the_score():
    # cgst_paise is an optional amount field for GST (only taxable_value_paise
    # is required) — invalid values must still count against the score
    # regardless of whether the field itself is required.
    data = _data([["27ABCDE1234F1Z5", "INV-1", 100000, "garbage"]])
    mappings = [
        FakeMapping("GSTIN", "gstin"),
        FakeMapping("Invoice", "invoice_number"),
        FakeMapping("Taxable", "taxable_value_paise"),
        FakeMapping("CGST", "cgst_paise"),
    ]
    result = run_validation(
        "GST", data, mappings, {"GSTIN": 0, "Invoice": 1, "Taxable": 2, "CGST": 3},
    )
    cgst_report = next(r for r in result.column_reports if r.target_field == "cgst_paise")
    assert cgst_report.is_required is False
    assert cgst_report.invalid_count == 1
    assert result.data_quality_score < 100.0


def test_mixed_valid_blank_and_invalid_produces_the_expected_score():
    # account_name: 3 valid (required). debit_amount: 1 valid, 1 blank
    # (required -> penalized), 1 invalid (required file type-agnostic
    # penalty). Graded = 3 + 1 + 1 + 1 = 6, failed = 1 (blank) + 1 (invalid) = 2.
    data = _data([
        ["Cash", 100000],
        ["Sales", ""],
        ["Purchases", "not a number"],
    ])
    mappings = [FakeMapping("Account", "account_name"), FakeMapping("Debit", "debit_amount")]
    result = run_validation("TB", data, mappings, {"Account": 0, "Debit": 1})
    assert result.data_quality_score == round(100.0 * (1 - 2 / 6), 1)
    assert any("blank value" in m and "required" in m for m in result.messages)


def test_messages_distinguish_required_and_optional_blank_counts():
    data = _data([["Cash", 100000, ""]])
    mappings = [
        FakeMapping("Account", "account_name"),
        FakeMapping("Debit", "debit_amount"),
        FakeMapping("Ref", "reference_number"),
    ]
    result = run_validation("TB", data, mappings, {"Account": 0, "Debit": 1, "Ref": 2})
    assert not any("required field" in m for m in result.messages)  # nothing required is blank here
    assert any("optional field" in m for m in result.messages)


# --- multi-sheet source_column encoding is handled transparently --------

def test_sheet_prefixed_source_column_still_resolves_via_column_key():
    data = _data([["Cash", 100000]])
    mappings = [
        FakeMapping("TB Jan::Account", "account_name"),
        FakeMapping("TB Jan::Debit", "debit_amount"),
    ]
    result = run_validation("TB", data, mappings, {"Account": 0, "Debit": 1})
    assert result.status == "VALIDATED"
    assert len(result.column_reports) == 2
