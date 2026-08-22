"""Unit tests for red flag anomaly detection."""

import pytest
import pandas as pd
from datetime import date
from analysis.red_flags import detect_red_flags

def test_high_cash_deposit_flag():
    df = pd.DataFrame([{
        "transaction_date": date(2024, 5, 10),
        "description": "BY CASH DEPOSIT - SELF",
        "credit_amount": 75000.0,
        "debit_amount": 0.0,
        "mode": "CASH",
        "nature": "Cash Deposit",
        "counterparty_name": "Self",
        "account_number": "XXXX1234",
        "fy": "FY 2024-25"
    }])
    df_f, summary = detect_red_flags(df)
    assert df_f.iloc[0]["is_flagged"] == True
    assert any("High Cash Deposit" in r for r in df_f.iloc[0]["flag_reasons"])

def test_sec_269ss_cash_loan():
    df = pd.DataFrame([{
        "transaction_date": date(2024, 6, 12),
        "description": "CASH LOAN RECEIVED FROM MR SHARMA",
        "credit_amount": 25000.0,
        "debit_amount": 0.0,
        "mode": "CASH",
        "nature": "Loan Received",
        "counterparty_name": "Mr Sharma",
        "account_number": "XXXX1234",
        "fy": "FY 2024-25"
    }])
    df_f, summary = detect_red_flags(df)
    assert df_f.iloc[0]["is_flagged"] == True
    assert any("269SS" in r for r in df_f.iloc[0]["flag_reasons"])

def test_accommodation_reversal_pattern():
    df = pd.DataFrame([
        {
            "transaction_date": date(2024, 7, 1),
            "description": "RTGS CR - ABC TRADERS",
            "credit_amount": 500000.0,
            "debit_amount": 0.0,
            "mode": "RTGS",
            "nature": "Business Receipts/Sales",
            "counterparty_name": "ABC Traders",
            "account_number": "XXXX1234",
            "fy": "FY 2024-25"
        },
        {
            "transaction_date": date(2024, 7, 2),
            "description": "RTGS DR - XYZ ENTERPRISES",
            "credit_amount": 0.0,
            "debit_amount": 500000.0,
            "mode": "RTGS",
            "nature": "Purchases",
            "counterparty_name": "XYZ Enterprises",
            "account_number": "XXXX1234",
            "fy": "FY 2024-25"
        }
    ])
    df_f, summary = detect_red_flags(df)
    assert df_f.iloc[0]["is_flagged"] == True
    assert df_f.iloc[1]["is_flagged"] == True
    assert any("Accommodation" in r for r in df_f.iloc[0]["flag_reasons"])
