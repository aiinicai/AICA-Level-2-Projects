"""Tests for component mapping and deterministic ambiguity resolution rules (§5, §7)."""
import pytest
from src.core.excel_parser import parse_workbook
from src.core.components import map_workbook_components, clean_label_for_matching


def test_clean_label_for_matching():
    assert clean_label_for_matching("(a) Share Capital") == "share capital"
    assert clean_label_for_matching("Total Revenue (I + II)") == "total revenue (i + ii)"
    assert clean_label_for_matching("Reserves & Surplus") == "reserves and surplus"


def test_rule_1_duplicate_resolution(sample_cy_path):
    if not sample_cy_path:
        pytest.skip("Sample CY file not present")
        
    cy_res = parse_workbook(sample_cy_path)
    cy_map, _ = map_workbook_components(cy_res, "CY")
    
    # Acceptance Test 9: other_lt_liabilities resolves to 188.00 (non-zero chosen over nil)
    other_lt = cy_map["other_lt_liabilities"]
    assert other_lt.amount_reporting == pytest.approx(188.0, 0.01)
    assert "Rule 1" in other_lt.resolution_rule


def test_synonym_absorption(sample_cy_path, sample_py_path):
    if not sample_cy_path or not sample_py_path:
        pytest.skip("Sample files not present")
        
    cy_res = parse_workbook(sample_cy_path)
    cy_map, _ = map_workbook_components(cy_res, "CY")
    
    py_res = parse_workbook(sample_py_path)
    py_map, _ = map_workbook_components(py_res, "PY")
    
    # Tangible assets and Fixed Assets map to ppe
    assert cy_map["ppe"].amount_reporting > 0
    assert py_map["ppe"].amount_reporting > 0
    
    # Total Revenue and Total Income map to total_income
    assert cy_map["total_income"].amount_reporting > 0
    assert py_map["total_income"].amount_reporting > 0
