import pytest
from decimal import Decimal
from app.services.validation_service import ValidationService

def test_row_level_balance_pass(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {"opening_balance": "100.00"},
        "transactions": [
            {"debit": "10.00", "credit": "", "balance": "90.00", "transaction_date": "2026-01-01"}
        ]
    }
    
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    tx = tx_results[0]
    assert tx.validation_status == "BALANCED"
    assert tx.expected_balance == Decimal("90.00")
    assert tx.difference == Decimal("0")
    assert tx.review_score == 100

def test_row_level_balance_mismatch(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {"opening_balance": "100.00"},
        "transactions": [
            # 1 cent off
            {"debit": "10.00", "credit": "", "balance": "89.99", "transaction_date": "2026-01-01"}
        ]
    }
    
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    tx = tx_results[0]
    assert tx.validation_status == "BALANCE_MISMATCH"
    assert tx.expected_balance == Decimal("90.00")
    assert tx.difference == Decimal("-0.01")
    assert tx.review_score == 40
    
def test_row_level_missing_prior_balance(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {},
        "transactions": [
            {"debit": "10.00", "credit": "", "balance": "90.00", "transaction_date": "2026-01-01"}
        ]
    }
    
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    tx = tx_results[0]
    assert tx.validation_status == "NO_PRIOR_BALANCE"
    assert tx.review_score == 90 # Structurally valid, but no math check possible

def test_row_level_missing_current_balance(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {"opening_balance": "100.00"},
        "transactions": [
            {"debit": "10.00", "credit": "", "balance": "", "transaction_date": "2026-01-01"}
        ]
    }
    
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    tx = tx_results[0]
    assert tx.validation_status == "MISSING_BALANCE"
    assert "MISSING_TRANSACTION_BALANCE" in tx.exception_codes
    assert tx.review_score == 70 # Warning
    assert tx.expected_balance == Decimal("90.00") # Expectation carries forward
    
def test_row_level_structural_anomalies(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {},
        "transactions": [
            {"debit": "10.00", "credit": "10.00", "balance": "90.00", "transaction_date": "2026-01-01"},
            {"debit": "", "credit": "", "balance": "90.00", "transaction_date": "2026-01-01"},
            {"debit": "0.00", "credit": "0.00", "balance": "90.00", "transaction_date": "2026-01-01"}
        ]
    }
    
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    
    assert "BOTH_DEBIT_AND_CREDIT_NONZERO" in tx_results[0].exception_codes
    assert tx_results[0].review_score == 20
    
    assert "NO_DEBIT_OR_CREDIT" in tx_results[1].exception_codes
    assert tx_results[1].review_score == 20
    
    assert "ZERO_AMOUNT_TRANSACTION" in tx_results[2].exception_codes
    assert tx_results[2].review_score == 70 # Warning
