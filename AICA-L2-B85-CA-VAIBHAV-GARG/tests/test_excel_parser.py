"""Tests for Excel workbook parser."""
import pytest
from src.core.excel_parser import (
    parse_workbook, strip_leading_enumerators, normalize_whitespace,
    parse_numeric_cell_value, extract_year_from_header_text, ExcelParsingError
)


def test_enumerator_stripping():
    assert strip_leading_enumerators("(a) Share Capital") == "Share Capital"
    assert strip_leading_enumerators("(b) Reserves and Surplus") == "Reserves and Surplus"
    assert strip_leading_enumerators("(ii) Intangible Assets") == "Intangible Assets"
    assert strip_leading_enumerators("I. Revenue from Operations (Gross)") == "Revenue from Operations (Gross)"
    assert strip_leading_enumerators("IV Expenses:") == "Expenses:"
    assert strip_leading_enumerators("VII. Profit/(Loss) for the Year") == "Profit/(Loss) for the Year"
    assert strip_leading_enumerators("A. Cash flows from Operating Activities") == "Cash flows from Operating Activities"
    assert strip_leading_enumerators("Tax Adjustment Earlier Years") == "Tax Adjustment Earlier Years"
    assert strip_leading_enumerators("Cash in hand") == "Cash in hand"
    assert strip_leading_enumerators("Cash and Cash Equivalents") == "Cash and Cash Equivalents"
    assert strip_leading_enumerators("Misc expenses w/off") == "Misc expenses w/off"


def test_numeric_cell_parsing():
    assert parse_numeric_cell_value(1234.56) == 1234.56
    assert parse_numeric_cell_value("1,234.56") == 1234.56
    assert parse_numeric_cell_value("(1,234.56)") == -1234.56
    assert parse_numeric_cell_value("-1234.56") == -1234.56
    assert parse_numeric_cell_value("-") == 0.0
    assert parse_numeric_cell_value("—") == 0.0
    assert parse_numeric_cell_value("Nil") == 0.0
    assert parse_numeric_cell_value(None) is None


def test_year_extraction_from_headers():
    assert extract_year_from_header_text("As at March 31 2026")[0] == 2026
    assert extract_year_from_header_text("For the year ended  31.03.2026")[0] == 2026
    assert extract_year_from_header_text("For the year ended 31 March 2025")[0] == 2025
    assert extract_year_from_header_text("FY 2024-25")[0] == 2025


def test_sample_files_parsing(sample_cy_path, sample_py_path):
    if not sample_cy_path or not sample_py_path:
        pytest.skip("Sample files not present")
        
    cy_res = parse_workbook(sample_cy_path)
    assert cy_res.reporting_year == 2026
    assert cy_res.comparative_year == 2025
    assert cy_res.sheet_metadata["BS"].header_row == 6
    assert cy_res.sheet_metadata["PL"].header_row == 6
    assert cy_res.sheet_metadata["CF"].header_row == 4
    assert cy_res.sheet_metadata["CF"].reporting_year_col == 5
    assert cy_res.sheet_metadata["CF"].comparative_year_col == 7
    
    py_res = parse_workbook(sample_py_path)
    assert py_res.reporting_year == 2025
    assert py_res.comparative_year == 2024
    assert py_res.sheet_metadata["BS"].header_row == 6
    assert py_res.sheet_metadata["PL"].header_row == 5
    assert py_res.sheet_metadata["CF"].header_row == 4
