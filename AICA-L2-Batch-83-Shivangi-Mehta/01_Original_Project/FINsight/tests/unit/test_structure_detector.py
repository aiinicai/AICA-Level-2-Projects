"""
Stage 7 — app/mapping/structure_detector.py. Pure pandas/openpyxl logic,
no Flask/SQLAlchemy dependency — runs directly under real pytest +
real pandas/openpyxl in this sandbox (see Stage 5/6 delivery notes for
why those two are genuinely installed here).

Uses only synthetic, fabricated data — never real client/financial
data, per the standing instruction.
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import openpyxl
import pandas as pd
import pytest

from app.mapping.structure_detector import (
    StructureDetectionError,
    detect_structure,
    list_sheets,
    load_data_rows,
    make_source_column,
    split_source_column,
)

SYNTHETIC_TB_ROWS = [
    {"Account": "Cash", "Debit": 100000, "Credit": 0},
    {"Account": "Sales", "Debit": 0, "Credit": 100000},
    {"Account": "Purchases", "Debit": 50000, "Credit": 0},
]


def _csv_bytes(rows=SYNTHETIC_TB_ROWS) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue()


def _xlsx_bytes(rows=SYNTHETIC_TB_ROWS, sheet_name="Sheet1") -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False, engine="openpyxl", sheet_name=sheet_name)
    return buf.getvalue()


def _multi_sheet_xlsx_bytes() -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(SYNTHETIC_TB_ROWS).to_excel(writer, index=False, sheet_name="TB Jan")
        pd.DataFrame(SYNTHETIC_TB_ROWS[:2]).to_excel(writer, index=False, sheet_name="TB Feb")
    return buf.getvalue()


def _title_row_xlsx_bytes() -> bytes:
    """A synthetic file with a one-cell report title on row 1, real
    headers on row 2 — the "header row uncertain / title row" case."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Acme Manufacturing Ltd - Trial Balance (Synthetic)"])
    ws.append(["Account", "Debit", "Credit"])
    ws.append(["Cash", 100000, 0])
    ws.append(["Sales", 0, 100000])
    ws.append(["Purchases", 50000, 0])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _duplicate_and_blank_header_csv_bytes() -> bytes:
    return (
        b"Account,Amount,Amount,\n"
        b"Cash,100000,0,extra1\n"
        b"Sales,0,100000,extra2\n"
    )


# --- list_sheets ------------------------------------------------------

def test_csv_has_no_sheet_concept():
    assert list_sheets(_csv_bytes(), ".csv") is None


def test_xlsx_single_sheet_lists_one_sheet():
    sheets = list_sheets(_xlsx_bytes(sheet_name="Trial Balance"), ".xlsx")
    assert sheets == ["Trial Balance"]


def test_xlsx_multiple_sheets_all_listed():
    sheets = list_sheets(_multi_sheet_xlsx_bytes(), ".xlsx")
    assert sheets == ["TB Jan", "TB Feb"]


# --- header + column detection -----------------------------------------

def test_normal_csv_header_detected_at_row_zero():
    result = detect_structure(_csv_bytes(), ".csv", sheet_name=None)
    assert result.header_row_index == 0
    assert result.header_detection_warning is None
    assert [c.raw_name for c in result.columns] == ["Account", "Debit", "Credit"]
    assert result.data_row_count == 3


def test_title_row_pushes_header_detection_to_row_two():
    result = detect_structure(_title_row_xlsx_bytes(), ".xlsx", sheet_name="Sheet")
    assert result.header_row_index == 1
    assert result.header_detection_warning is not None
    assert [c.raw_name for c in result.columns] == ["Account", "Debit", "Credit"]
    assert result.data_row_count == 3


def test_multi_sheet_file_requires_a_sheet_name_to_detect_structure():
    file_bytes = _multi_sheet_xlsx_bytes()
    result = detect_structure(file_bytes, ".xlsx", sheet_name="TB Feb")
    assert result.sheet_name == "TB Feb"
    assert result.data_row_count == 2  # SYNTHETIC_TB_ROWS[:2]
    assert result.available_sheets == ["TB Jan", "TB Feb"]


def test_duplicate_column_names_detected_and_disambiguated():
    result = detect_structure(_duplicate_and_blank_header_csv_bytes(), ".csv", sheet_name=None)
    assert "Amount" in result.duplicate_column_names
    keys = [c.column_key for c in result.columns]
    assert "Amount (col 2)" in keys
    assert "Amount (col 3)" in keys
    assert any(w.startswith("Duplicate column headers") for w in result.warnings)


def test_blank_header_column_detected():
    result = detect_structure(_duplicate_and_blank_header_csv_bytes(), ".csv", sheet_name=None)
    assert result.blank_column_count == 1
    blank_columns = [c for c in result.columns if c.is_blank]
    assert len(blank_columns) == 1
    assert blank_columns[0].column_key.startswith("(blank column")


def test_unreadable_file_raises_structure_detection_error():
    garbage = b"this is not a valid csv or xlsx file \x00\x01\x02" * 20
    with pytest.raises(StructureDetectionError):
        detect_structure(garbage, ".xlsx", sheet_name=None)


# --- load_data_rows -----------------------------------------------------

def test_load_data_rows_excludes_header_and_any_rows_above_it():
    file_bytes = _title_row_xlsx_bytes()
    structure = detect_structure(file_bytes, ".xlsx", sheet_name="Sheet")
    data = load_data_rows(file_bytes, ".xlsx", "Sheet", structure.header_row_index)
    assert len(data) == 3
    assert list(data[0]) == ["Cash", "Sales", "Purchases"]


def test_load_data_rows_columns_are_positional_not_pandas_names():
    file_bytes = _csv_bytes()
    structure = detect_structure(file_bytes, ".csv", sheet_name=None)
    data = load_data_rows(file_bytes, ".csv", None, structure.header_row_index)
    assert list(data.columns) == [0, 1, 2]


# --- sheet-aware source_column encoding ---------------------------------

def test_source_column_roundtrip_single_sheet():
    encoded = make_source_column(None, "Account")
    assert encoded == "Account"
    assert split_source_column(encoded) == (None, "Account")


def test_source_column_roundtrip_multi_sheet():
    encoded = make_source_column("TB Feb", "Account")
    assert encoded == "TB Feb::Account"
    assert split_source_column(encoded) == ("TB Feb", "Account")
