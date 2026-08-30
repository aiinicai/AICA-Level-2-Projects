"""
Tests for the 4 Forensic Models (Beneish M-Score, Altman Z"-Score, Sloan Accrual, Piotroski F-Score).
"""
import pytest
import pandas as pd
from engine.models import (
    compute_beneish_m_score,
    compute_altman_z_score,
    compute_sloan_accrual,
    compute_piotroski_f_score
)

def test_beneish_worked_example():
    # Worked example baseline
    prev = pd.Series({
        "fy": "FY23", "revenue": 1000000.0, "receivables": 100000.0, "total_assets": 2000000.0,
        "cogs": 600000.0, "current_assets": 800000.0, "net_block": 1000000.0, "investments": 100000.0,
        "depreciation": 50000.0, "sga": 100000.0, "current_liabilities": 400000.0, "lt_borrowings": 300000.0,
        "pbt": 150000.0, "pat": 110000.0, "cfo_indirect": 120000.0
    })
    curr = pd.Series({
        "fy": "FY24", "revenue": 1100000.0, "receivables": 200000.0, "total_assets": 2300000.0,
        "cogs": 660000.0, "current_assets": 1100000.0, "net_block": 1000000.0, "investments": 100000.0,
        "depreciation": 50000.0, "sga": 110000.0, "current_liabilities": 450000.0, "lt_borrowings": 300000.0,
        "pbt": 180000.0, "pat": 130000.0, "cfo_indirect": -50000.0
    })
    res = compute_beneish_m_score(prev, curr)
    assert "m_score" in res
    assert "components" in res
    assert res["components"]["DSRI"] > 1.5
    assert res["m_score"] > -1.78
    assert res["is_flagged"] is True

def test_altman_z_score_zones():
    # Safe zone entity
    safe_row = pd.Series({
        "fy": "FY24", "working_capital": 500000.0, "total_assets": 1000000.0,
        "retained_earnings": 400000.0, "ebit": 250000.0, "net_worth": 700000.0, "total_liabilities": 300000.0
    })
    res_safe = compute_altman_z_score(safe_row)
    assert res_safe["zone"] == "Safe"
    assert res_safe["z_score"] > 2.60
    assert res_safe["is_distress"] is False

    # Distress zone entity
    distress_row = pd.Series({
        "fy": "FY24", "working_capital": -200000.0, "total_assets": 1000000.0,
        "retained_earnings": -100000.0, "ebit": -50000.0, "net_worth": 100000.0, "total_liabilities": 900000.0
    })
    res_distress = compute_altman_z_score(distress_row)
    assert res_distress["zone"] == "Distress"
    assert res_distress["z_score"] < 1.10
    assert res_distress["is_distress"] is True

def test_sloan_accrual():
    prev = pd.Series({"fy": "FY23", "total_assets": 1000000.0})
    curr = pd.Series({"fy": "FY24", "total_assets": 1200000.0, "pat": 200000.0, "cfo_indirect": 50000.0})
    res = compute_sloan_accrual(prev, curr)
    assert res["is_flagged"] is True
    assert res["accrual_ratio"] > 0.10

def test_piotroski_f_score_range():
    prev = pd.Series({
        "fy": "FY23", "revenue": 1000000.0, "total_assets": 1000000.0, "pat": 100000.0,
        "cfo_indirect": 120000.0, "lt_borrowings": 200000.0, "current_assets": 400000.0,
        "current_liabilities": 200000.0, "share_capital": 300000.0, "cogs": 500000.0
    })
    curr = pd.Series({
        "fy": "FY24", "revenue": 1200000.0, "total_assets": 1100000.0, "pat": 130000.0,
        "cfo_indirect": 150000.0, "lt_borrowings": 150000.0, "current_assets": 500000.0,
        "current_liabilities": 200000.0, "share_capital": 300000.0, "cogs": 550000.0
    })
    res = compute_piotroski_f_score(prev, curr)
    assert 0 <= res["f_score"] <= 9
