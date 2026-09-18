"""Tests for default assumptions and principal repayment 3-step waterfall (§8)."""
import pytest
from src.core.excel_parser import parse_workbook
from src.core.components import map_workbook_components
from src.core.derivations import extract_period_financials
from src.core.assumptions import resolve_principal_repayment, build_assumptions_registry


def test_principal_repayment_waterfall(sample_cy_path, sample_py_path):
    if not sample_cy_path or not sample_py_path:
        pytest.skip("Sample files not present")
        
    cy_res = parse_workbook(sample_cy_path)
    py_res = parse_workbook(sample_py_path)
    
    cy_map, _ = map_workbook_components(cy_res, "CY")
    py_map, _ = map_workbook_components(py_res, "PY")
    
    cy_closing = extract_period_financials(cy_map, "reporting")
    cy_opening = extract_period_financials(cy_map, "comparative")
    py_closing = extract_period_financials(py_map, "reporting")
    py_opening = extract_period_financials(py_map, "comparative")
    
    pr_result = resolve_principal_repayment(cy_closing, cy_opening, py_closing, py_opening)
    
    # CY derived and reconciles
    assert pr_result.principal_repayment_cy == 0.0
    assert pr_result.basis_cy == "derived"
    assert not pr_result.ic7_failed_cy
    
    # PY fails validation and falls to step 3 with IC-7 raised
    assert pr_result.principal_repayment_py == 0.0
    assert pr_result.basis_py == "failed"
    assert pr_result.ic7_failed_py
