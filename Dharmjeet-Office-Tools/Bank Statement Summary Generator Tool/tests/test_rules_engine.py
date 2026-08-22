"""Unit tests for transaction classification and audit trail."""

import pytest
import pandas as pd
from datetime import date
from classification.rules_engine import classify_transactions

def test_classification_salary():
    df = pd.DataFrame([{
        "transaction_date": date(2024, 4, 30),
        "description": "ACH CR - INFOSYS LTD - SALARY FOR APRIL 2024",
        "credit_amount": 125000.0,
        "debit_amount": 0.0,
        "mode": "ACH",
        "counterparty_name": "Infosys Ltd"
    }])
    df_c = classify_transactions(df)
    assert df_c.iloc[0]["nature"] == "Salary"
    assert "Salary" in df_c.iloc[0]["audit_trail"]

def test_classification_interest():
    df = pd.DataFrame([{
        "transaction_date": date(2024, 6, 30),
        "description": "SB INT.PD 01-04-2024 TO 30-06-2024",
        "credit_amount": 4500.0,
        "debit_amount": 0.0,
        "mode": "INT",
        "counterparty_name": "Bank Interest Credit"
    }])
    df_c = classify_transactions(df)
    assert df_c.iloc[0]["nature"] == "Interest Income"

def test_classification_advance_tax():
    df = pd.DataFrame([{
        "transaction_date": date(2024, 9, 15),
        "description": "OLTAS ADVANCE TAX PMT CHALLAN 280",
        "credit_amount": 0.0,
        "debit_amount": 50000.0,
        "mode": "NETBANKING",
        "counterparty_name": "Income Tax Department"
    }])
    df_c = classify_transactions(df)
    assert df_c.iloc[0]["nature"] == "Tax Payment (Advance Tax/Self-Assessment/TDS/GST)"

def test_classification_bank_charges():
    df = pd.DataFrame([{
        "transaction_date": date(2024, 7, 1),
        "description": "CONSOLIDATED CHG + GST @ 18%",
        "credit_amount": 0.0,
        "debit_amount": 590.0,
        "mode": "BANK_CHG",
        "counterparty_name": "Bank Charges"
    }])
    df_c = classify_transactions(df)
    assert df_c.iloc[0]["nature"] == "Bank Charges"
