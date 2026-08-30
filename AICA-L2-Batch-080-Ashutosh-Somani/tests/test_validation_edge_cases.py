import pytest
from decimal import Decimal
from app.services.validation_service import ValidationService

def test_page_transition_mismatch(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {"opening_balance": "100.00"},
        "transactions": [
            {"debit": "10.00", "credit": "", "balance": "90.00", "transaction_date": "2026-01-01", "source_page": 1},
            {"debit": "10.00", "credit": "", "balance": "70.00", "transaction_date": "2026-01-01", "source_page": 2} # Should be 80
        ]
    }
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    assert any(e.exception_code == "PAGE_TRANSITION_BALANCE_MISMATCH" for e in exceptions)

def test_duplicate_candidate(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {"opening_balance": "100.00"},
        "transactions": [
            {"debit": "10.00", "credit": "", "balance": "90.00", "transaction_date": "2026-01-01", "narration": "FEE"},
            {"debit": "10.00", "credit": "", "balance": "90.00", "transaction_date": "2026-01-01", "narration": "FEE"}
        ]
    }
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    assert any(e.exception_code == "POSSIBLE_DUPLICATE" for e in exceptions)
    assert len(tx_results) == 2 # Did not delete!

def test_date_sequence_mixed(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {},
        "transactions": [
            {"debit": "10.00", "credit": "", "balance": "90.00", "transaction_date": "2026-01-01"},
            {"debit": "10.00", "credit": "", "balance": "80.00", "transaction_date": "2026-01-03"},
            {"debit": "10.00", "credit": "", "balance": "70.00", "transaction_date": "2026-01-02"},
            {"debit": "10.00", "credit": "", "balance": "60.00", "transaction_date": "2026-01-05"}
        ]
    }
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    assert any(e.exception_code == "MIXED_DATE_SEQUENCE" for e in exceptions)
    
def test_zero_blank_semantics(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {"opening_balance": "100.00"},
        "transactions": [
            # valid ones
            {"debit": "0.00", "credit": "500.00", "balance": "600.00", "transaction_date": "2026-01-01"},
            {"debit": "500.00", "credit": "0.00", "balance": "100.00", "transaction_date": "2026-01-01"},
            # zeroes
            {"debit": "0.00", "credit": "0.00", "balance": "100.00", "transaction_date": "2026-01-01"},
            # blanks
            {"debit": "", "credit": "", "balance": "100.00", "transaction_date": "2026-01-01"}
        ]
    }
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    
    assert tx_results[0].validation_status == "BALANCED"
    assert tx_results[1].validation_status == "BALANCED"
    
    assert any(e.exception_code == "ZERO_AMOUNT_TRANSACTION" for e in exceptions)
    assert any(e.exception_code == "NO_DEBIT_OR_CREDIT" for e in exceptions)

def test_first_row_zero_balance(temp_config):
    service = ValidationService(temp_config)
    norm_data = {
        "metadata": {"opening_balance": "0.00"},
        "transactions": [
            {"debit": "10.00", "credit": "", "balance": "-10.00", "transaction_date": "2026-01-01"}
        ]
    }
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    assert tx_results[0].validation_status == "BALANCED"
    assert tx_results[0].expected_balance == Decimal("-10.00")
