import pytest
from decimal import Decimal
from app.services.validation_service import ValidationService

def test_statement_level_validation_pass(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {
            "opening_balance": "1000.00",
            "closing_balance": "1400.00"
        },
        "transactions": [
            {"debit": "100.00", "credit": "", "balance": "900.00", "transaction_date": "2026-01-01"},
            {"debit": "", "credit": "500.00", "balance": "1400.00", "transaction_date": "2026-01-02"}
        ]
    }
    
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    assert summary.total_debits == Decimal("100.00")
    assert summary.total_credits == Decimal("500.00")
    assert summary.expected_closing_balance == Decimal("1400.00")
    assert summary.difference == Decimal("0")
    assert summary.validation_status == "PASS"
    assert summary.exception_count == 0

def test_statement_level_validation_fail(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {
            "opening_balance": "1000.00",
            "closing_balance": "1300.00" # wrong closing
        },
        "transactions": [
            {"debit": "100.00", "credit": "", "balance": "900.00", "transaction_date": "2026-01-01"},
            {"debit": "", "credit": "500.00", "balance": "1400.00", "transaction_date": "2026-01-02"}
        ]
    }
    
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    assert summary.expected_closing_balance == Decimal("1400.00")
    assert summary.difference == Decimal("-100.00")
    assert summary.validation_status == "FAIL"
    assert any(e.exception_code == "STATEMENT_CLOSING_MISMATCH" for e in exceptions)

def test_statement_missing_balances(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {},
        "transactions": [
            {"debit": "100.00", "credit": "", "balance": "900.00", "transaction_date": "2026-01-01"}
        ]
    }
    
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    assert summary.validation_status == "NOT_VERIFIABLE"
    assert any(e.exception_code == "MISSING_OPENING_BALANCE" for e in exceptions)
    assert any(e.exception_code == "MISSING_CLOSING_BALANCE" for e in exceptions)
