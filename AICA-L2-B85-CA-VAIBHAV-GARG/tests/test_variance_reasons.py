"""Tests for variance computation and driver decomposition reasons (§9)."""
import pytest
from src.core.excel_parser import parse_workbook
from src.core.components import map_workbook_components
from src.core.derivations import extract_period_financials
from src.core.assumptions import resolve_principal_repayment, build_assumptions_registry
from src.core.calculator import compute_ratios
from src.core.variance_engine import populate_reasons_for_results


def test_driver_reasons_quality(sample_cy_path, sample_py_path):
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
    assumptions = build_assumptions_registry(pr_result=pr_result, closing_cy=cy_closing, closing_py=py_closing)
    
    res = compute_ratios(cy_closing, cy_opening, py_closing, py_opening, assumptions, 25.0)
    populate_reasons_for_results(res.schedule_iii_ratios, cy_closing, cy_opening, py_closing, py_opening, units=cy_res.units)
    
    flagged = [r for r in res.schedule_iii_ratios if r.is_flagged]
    assert len(flagged) == 4
    
    # Assert reasons name actual numbers / percentages
    for r in flagged:
        assert len(r.reason_final) > 40
        assert "%" in r.reason_final
