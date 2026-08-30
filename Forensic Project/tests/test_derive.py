"""
Tests for Financial Statement Derivation and Indirect Cash Flow computation.
"""
import pytest
import pandas as pd
import numpy as np
from engine.parse_excel import parse_excel
from engine.normalise import normalise_ledgers
from engine.derive import derive_financial_statements

def test_derive_from_sample_data():
    raw_df = parse_excel("data/sample/sample_tb_FY22_FY24.xlsx")
    ledgers = normalise_ledgers(raw_df)
    derived = derive_financial_statements(ledgers)
    
    assert len(derived) == 3
    assert set(derived["fy"]) == {"FY22", "FY23", "FY24"}
    
    for idx, row in derived.iterrows():
        # Check Total Assets == Total Liabilities + Net Worth
        assets = row["total_assets"]
        liab_equity = row["total_liabilities"] + row["net_worth"]
        assert abs(assets - liab_equity) < 5000.0, f"Balance sheet mismatch in {row['fy']}: Assets={assets}, Liab+Equity={liab_equity}"
        
        # Check revenue and PAT are positive
        assert row["revenue"] > 0
        assert row["pat"] > 0
        
        # Check CFO indirect is present for sample data (which has opening balances)
        assert row["cfo_indirect"] is not None

def test_derive_null_safety_without_opening_balances():
    raw_df = parse_excel("data/sample/sample_tb_FY22_FY24.xlsx")
    ledgers = normalise_ledgers(raw_df)
    
    # Strip opening balances
    ledgers_no_opening = ledgers.copy()
    ledgers_no_opening["opening_dr"] = 0.0
    ledgers_no_opening["opening_cr"] = 0.0
    
    derived = derive_financial_statements(ledgers_no_opening)
    assert len(derived) == 3
    for _, row in derived.iterrows():
        assert row["cfo_indirect"] is None
        assert row["revenue"] > 0
        assert row["total_assets"] > 0

def test_cfo_indirect_reconciliation():
    # Hand-built 1-year test with known figures
    ledgers = pd.DataFrame([
        {"fy": "FY24", "ledger_name": "Sales", "group": "Revenue from Operations", "sub_group": None,
         "opening_dr": 0.0, "opening_cr": 0.0, "turnover_dr": 0.0, "turnover_cr": 1000000.0, "closing_dr": 0.0, "closing_cr": 1000000.0,
         "closing_net": -1000000.0, "opening_net": 0.0, "movement": -1000000.0, "turnover_total": 1000000.0},
        {"fy": "FY24", "ledger_name": "Purchases", "group": "Cost of Materials Consumed", "sub_group": None,
         "opening_dr": 0.0, "opening_cr": 0.0, "turnover_dr": 600000.0, "turnover_cr": 0.0, "closing_dr": 600000.0, "closing_cr": 0.0,
         "closing_net": 600000.0, "opening_net": 0.0, "movement": 600000.0, "turnover_total": 600000.0},
        {"fy": "FY24", "ledger_name": "Depreciation A/c", "group": "Depreciation and Amortisation Expense", "sub_group": None,
         "opening_dr": 0.0, "opening_cr": 0.0, "turnover_dr": 50000.0, "turnover_cr": 0.0, "closing_dr": 50000.0, "closing_cr": 0.0,
         "closing_net": 50000.0, "opening_net": 0.0, "movement": 50000.0, "turnover_total": 50000.0},
        {"fy": "FY24", "ledger_name": "Trade Debtors", "group": "Sundry Debtors", "sub_group": None,
         "opening_dr": 100000.0, "opening_cr": 0.0, "turnover_dr": 1000000.0, "turnover_cr": 900000.0, "closing_dr": 200000.0, "closing_cr": 0.0,
         "closing_net": 200000.0, "opening_net": 100000.0, "movement": 100000.0, "turnover_total": 1900000.0},
        {"fy": "FY24", "ledger_name": "Trade Creditors", "group": "Sundry Creditors", "sub_group": None,
         "opening_dr": 0.0, "opening_cr": 50000.0, "turnover_dr": 550000.0, "turnover_cr": 600000.0, "closing_dr": 0.0, "closing_cr": 100000.0,
         "closing_net": -100000.0, "opening_net": -50000.0, "movement": -50000.0, "turnover_total": 1150000.0},
    ])
    derived = derive_financial_statements(ledgers)
    # pat = 1000000 - 600000 - 50000 = 350000
    # delta_receivables = 200000 - 100000 = +100000
    # delta_payables = 100000 - 50000 = +50000
    # cfo = pat + dep (50000) - delta_rec (100000) + delta_pay (50000) = 350000 + 50000 - 100000 + 50000 = 350000
    assert derived.iloc[0]["pat"] == 350000.0
    assert derived.iloc[0]["cfo_indirect"] == 350000.0
