"""Tests for automated integrity checks IC-1 to IC-10 (§11)."""
import pytest
from src.core.excel_parser import parse_workbook
from src.core.components import map_workbook_components
from src.core.derivations import extract_period_financials
from src.core.integrity import run_integrity_checks


def test_integrity_checks_expected_results(sample_cy_path, sample_py_path):
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
    
    ic_results = run_integrity_checks(
        cy_res, py_res, cy_map, py_map,
        cy_closing, cy_opening, py_closing, py_opening
    )
    
    ic_dict = {ic.check_id: ic for ic in ic_results}
    
    # IC-1, IC-2, IC-3, IC-4, IC-5, IC-6, IC-8 pass
    assert any(ic.check_id == "IC-1" and ic.status == "Pass" for ic in ic_results)
    assert ic_dict["IC-4"].status == "Pass"
    assert ic_dict["IC-5"].status == "Pass"
    assert ic_dict["IC-6"].status == "Pass"
    assert ic_dict["IC-8"].status == "Pass"
    
    # IC-7 fails on PY
    assert any(ic.check_id == "IC-7" and ic.status == "Fail" for ic in ic_results)
    
    # IC-9 dynamic check result
    assert "IC-9" in ic_dict
