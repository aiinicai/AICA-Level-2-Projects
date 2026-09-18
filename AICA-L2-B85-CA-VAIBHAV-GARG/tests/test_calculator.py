"""Tests for calculation engine and pure ratio functions (§6, §14)."""
import pytest
from src.core.calculator import safe_divide, compute_ratios
from src.core.derivations import PeriodFinancials
from src.core.assumptions import build_assumptions_registry


def test_safe_divide():
    # Division by zero
    val, fmt, fn = safe_divide(100.0, 0.0)
    assert val is None
    assert fmt == "NA"
    assert "zero" in fn
    
    # Negative denominator
    val, fmt, fn = safe_divide(100.0, -50.0)
    assert val is None
    assert fmt == "NA"
    assert "negative" in fn
    
    # Nil on both
    val, fmt, fn = safe_divide(0.0, 0.0)
    assert val is None
    assert fmt == "NA"
    
    # Normal positive division
    val, fmt, fn = safe_divide(100.0, 50.0, is_percentage=False)
    assert val == 2.0
    assert fmt == "2.00"
    
    # Percentage format
    val, fmt, fn = safe_divide(10.0, 100.0, is_percentage=True)
    assert val == 10.0
    assert fmt == "10.00%"


def test_synthetic_calculation():
    # Construct clean synthetic dataset
    cy_close = PeriodFinancials(
        current_assets=1000.0, current_liabilities=500.0,
        total_debt=200.0, shareholders_equity=800.0,
        eads=150.0, cf_interest_paid=-50.0,
        pat=100.0, inventories=300.0, cogs=600.0,
        revenue_net=2000.0, trade_receivables=400.0,
        cost_of_materials=500.0, trade_payables_total=250.0,
        working_capital=500.0, ebit=180.0, capital_employed=1000.0
    )
    cy_open = PeriodFinancials(
        shareholders_equity=700.0, inventories=300.0,
        trade_receivables=400.0, trade_payables_total=250.0,
        working_capital=400.0
    )
    
    py_close = PeriodFinancials(
        current_assets=800.0, current_liabilities=400.0,
        total_debt=200.0, shareholders_equity=700.0,
        eads=120.0, cf_interest_paid=-40.0,
        pat=80.0, inventories=250.0, cogs=500.0,
        revenue_net=1600.0, trade_receivables=350.0,
        cost_of_materials=400.0, trade_payables_total=200.0,
        working_capital=400.0, ebit=140.0, capital_employed=900.0
    )
    py_open = PeriodFinancials(
        shareholders_equity=600.0, inventories=250.0,
        trade_receivables=350.0, trade_payables_total=200.0,
        working_capital=300.0
    )
    
    assumptions = build_assumptions_registry(closing_cy=cy_close, closing_py=py_close)
    res = compute_ratios(cy_close, cy_open, py_close, py_open, assumptions, threshold_pct=25.0)
    
    r_map = {r.key: r for r in res.schedule_iii_ratios}
    
    assert r_map["current_ratio"].value_cy == 2.0
    assert r_map["debt_equity_ratio"].value_cy == 0.25
    assert r_map["dscr"].value_cy == 3.0
    assert r_map["inventory_turnover"].value_cy == 2.0
    assert r_map["trade_receivables_turnover"].value_cy == 5.0
    assert r_map["net_profit_ratio"].value_cy == 5.0
