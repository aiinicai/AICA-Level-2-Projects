import pytest
from app.services.validation_service import ValidationService

def test_date_outside_statement_period(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {
            "statement_start_date": "2026-01-01",
            "statement_end_date": "2026-01-31"
        },
        "transactions": [
            {"debit": "10.00", "credit": "", "balance": "90.00", "transaction_date": "2025-12-31"}, # Before
            {"debit": "10.00", "credit": "", "balance": "80.00", "transaction_date": "2026-01-15"}, # Inside
            {"debit": "10.00", "credit": "", "balance": "70.00", "transaction_date": "2026-02-01"}  # After
        ]
    }
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    
    assert "DATE_OUTSIDE_STATEMENT_PERIOD" in tx_results[0].exception_codes
    assert "DATE_OUTSIDE_STATEMENT_PERIOD" not in tx_results[1].exception_codes
    assert "DATE_OUTSIDE_STATEMENT_PERIOD" in tx_results[2].exception_codes
