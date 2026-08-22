"""Unit tests for balance reconciliation check."""

import pytest
import pandas as pd
from datetime import date
from analysis.reconciliation import validate_running_balances

def test_reconciliation_success():
    df = pd.DataFrame([
        {"transaction_date": date(2024, 4, 1), "source_file": "stmt.pdf", "account_number": "1234", "credit_amount": 10000.0, "debit_amount": 0.0, "balance": 10000.0},
        {"transaction_date": date(2024, 4, 5), "source_file": "stmt.pdf", "account_number": "1234", "credit_amount": 5000.0, "debit_amount": 0.0, "balance": 15000.0},
        {"transaction_date": date(2024, 4, 10), "source_file": "stmt.pdf", "account_number": "1234", "credit_amount": 0.0, "debit_amount": 3000.0, "balance": 12000.0},
    ])
    df_recon, summary = validate_running_balances(df)
    assert summary["status"] == "RECONCILED"
    assert summary["discrepancies_found"] == 0

def test_reconciliation_discrepancy():
    df = pd.DataFrame([
        {"transaction_date": date(2024, 4, 1), "source_file": "stmt.pdf", "account_number": "1234", "credit_amount": 10000.0, "debit_amount": 0.0, "balance": 10000.0},
        {"transaction_date": date(2024, 4, 5), "source_file": "stmt.pdf", "account_number": "1234", "credit_amount": 5000.0, "debit_amount": 0.0, "balance": 18000.0}, # Error: should be 15000
    ])
    df_recon, summary = validate_running_balances(df)
    assert summary["status"] == "DISCREPANCIES_FOUND"
    assert summary["discrepancies_found"] == 1
