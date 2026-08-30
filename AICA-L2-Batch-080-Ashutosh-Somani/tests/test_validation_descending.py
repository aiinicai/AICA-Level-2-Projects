import pytest
from decimal import Decimal
import datetime
from app.services.validation_service import ValidationService

def test_descending_credit_reconciliation(temp_config):
    service = ValidationService(temp_config)
    
    # older balance = Decimal("369.79")
    # newer credit = Decimal("1000.00")
    # newer balance = Decimal("1369.79")
    norm_data = {
        "metadata": {
            # opening_balance is None, so statement validation is NOT_VERIFIABLE, 
            # but row-level adjacent validation should still work.
        },
        "transactions": [
            # Row 1 (Newer transaction): Credit 1000.00, Balance 1369.79
            {"debit": "", "credit": "1000.00", "balance": "1369.79", "transaction_date": "2026-01-02", "narration": "Newer credit"},
            # Row 2 (Older transaction): Balance 369.79
            {"debit": "", "credit": "", "balance": "369.79", "transaction_date": "2026-01-01", "narration": "Older base"}
        ]
    }
    
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    
    # 0 BALANCE_MISMATCH exceptions
    balance_mismatches = [e for e in exceptions if e.exception_code in ["BALANCE_MISMATCH", "PAGE_TRANSITION_BALANCE_MISMATCH"]]
    assert len(balance_mismatches) == 0
    assert tx_results[0].validation_status == "BALANCED"
    assert tx_results[1].validation_status == "NO_PRIOR_BALANCE"
    assert summary.validation_status == "NOT_VERIFIABLE"

def test_descending_debit_reconciliation(temp_config):
    service = ValidationService(temp_config)
    
    # older balance = Decimal("647.97")
    # newer debit = Decimal("50.00")
    # newer balance = Decimal("597.97")
    norm_data = {
        "metadata": {},
        "transactions": [
            # Row 1 (Newer): Debit 50.00, Balance 597.97
            {"debit": "50.00", "credit": "", "balance": "597.97", "transaction_date": "2026-01-02", "narration": "Newer debit"},
            # Row 2 (Older): Balance 647.97
            {"debit": "", "credit": "", "balance": "647.97", "transaction_date": "2026-01-01", "narration": "Older base"}
        ]
    }
    
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    
    balance_mismatches = [e for e in exceptions if e.exception_code in ["BALANCE_MISMATCH", "PAGE_TRANSITION_BALANCE_MISMATCH"]]
    assert len(balance_mismatches) == 0
    assert tx_results[0].validation_status == "BALANCED"
    assert tx_results[1].validation_status == "NO_PRIOR_BALANCE"

def test_synthetic_descending_statement_three_rows(temp_config):
    service = ValidationService(temp_config)
    
    # Row 1 newer: Debit = Decimal("50.00"), Balance = Decimal("597.97")
    # Row 2 older: Debit = Decimal("706.82"), Balance = Decimal("647.97")
    # Row 3 older: Debit = Decimal("15.00"), Balance = Decimal("1354.79")
    # Designing the complete synthetic sequence so balances reconcile exactly:
    # Row 3 older: Debit = 15.00, Balance = 1354.79. (Older balance = 1369.79)
    # Row 2 older: Debit = 706.82, Balance = 647.97. (Older balance = 1354.79. Matches!)
    # Row 1 newer: Debit = 50.00, Balance = 597.97. (Older balance = 647.97. Matches!)
    norm_data = {
        "metadata": {},
        "transactions": [
            {"debit": "50.00", "credit": "", "balance": "597.97", "transaction_date": "2026-01-03", "narration": "Tx 1"},
            {"debit": "706.82", "credit": "", "balance": "647.97", "transaction_date": "2026-01-02", "narration": "Tx 2"},
            {"debit": "15.00", "credit": "", "balance": "1354.79", "transaction_date": "2026-01-01", "narration": "Tx 3"}
        ]
    }
    
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    
    balance_mismatches = [e for e in exceptions if e.exception_code in ["BALANCE_MISMATCH", "PAGE_TRANSITION_BALANCE_MISMATCH"]]
    assert len(balance_mismatches) == 0
    assert tx_results[0].validation_status == "BALANCED"
    assert tx_results[1].validation_status == "BALANCED"
    assert tx_results[2].validation_status == "NO_PRIOR_BALANCE"

def test_synthetic_ascending_regression(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {},
        "transactions": [
            {"debit": "15.00", "credit": "", "balance": "1354.79", "transaction_date": "2026-01-01", "narration": "Tx 1"},
            {"debit": "706.82", "credit": "", "balance": "647.97", "transaction_date": "2026-01-02", "narration": "Tx 2"},
            {"debit": "50.00", "credit": "", "balance": "597.97", "transaction_date": "2026-01-03", "narration": "Tx 3"}
        ]
    }
    
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    
    balance_mismatches = [e for e in exceptions if e.exception_code in ["BALANCE_MISMATCH", "PAGE_TRANSITION_BALANCE_MISMATCH"]]
    assert len(balance_mismatches) == 0
    assert tx_results[0].validation_status == "NO_PRIOR_BALANCE"
    assert tx_results[1].validation_status == "BALANCED"
    assert tx_results[2].validation_status == "BALANCED"

def test_multiple_same_date_descending(temp_config):
    service = ValidationService(temp_config)
    
    # 4 transactions on the same date followed by a different older date
    # Chronological older balance: 1000.00
    # Tx 5 (older date): Debit 100.00, Balance 900.00 (Date: 2026-01-01)
    # Tx 4 (same date): Credit 200.00, Balance 1100.00 (Date: 2026-01-02)
    # Tx 3 (same date): Debit 50.00, Balance 1050.00 (Date: 2026-01-02)
    # Tx 2 (same date): Credit 300.00, Balance 1350.00 (Date: 2026-01-02)
    # Tx 1 (same date): Debit 150.00, Balance 1200.00 (Date: 2026-01-02)
    
    norm_data = {
        "metadata": {},
        "transactions": [
            {"debit": "150.00", "credit": "", "balance": "1200.00", "transaction_date": "2026-01-02", "narration": "Tx 1"},
            {"debit": "", "credit": "300.00", "balance": "1350.00", "transaction_date": "2026-01-02", "narration": "Tx 2"},
            {"debit": "50.00", "credit": "", "balance": "1050.00", "transaction_date": "2026-01-02", "narration": "Tx 3"},
            {"debit": "", "credit": "200.00", "balance": "1100.00", "transaction_date": "2026-01-02", "narration": "Tx 4"},
            {"debit": "100.00", "credit": "", "balance": "900.00", "transaction_date": "2026-01-01", "narration": "Tx 5"}
        ]
    }
    
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    
    balance_mismatches = [e for e in exceptions if e.exception_code in ["BALANCE_MISMATCH", "PAGE_TRANSITION_BALANCE_MISMATCH"]]
    assert len(balance_mismatches) == 0
    assert tx_results[4].validation_status == "NO_PRIOR_BALANCE" # Tx 5 (oldest)
    assert tx_results[3].validation_status == "BALANCED" # Tx 4: 900.00 + 200.00 = 1100.00
    assert tx_results[2].validation_status == "BALANCED" # Tx 3: 1100.00 - 50.00 = 1050.00
    assert tx_results[1].validation_status == "BALANCED" # Tx 2: 1050.00 + 300.00 = 1350.00
    assert tx_results[0].validation_status == "BALANCED" # Tx 1: 1350.00 - 150.00 = 1200.00

def test_mixed_order_validation_not_verifiable(temp_config):
    service = ValidationService(temp_config)
    
    norm_data = {
        "metadata": {
            "opening_balance": "1000.00",
            "closing_balance": "1200.00"
        },
        "transactions": [
            # Ascending, then descending, then ascending
            {"debit": "", "credit": "100.00", "balance": "1100.00", "transaction_date": "2026-01-01"},
            {"debit": "", "credit": "100.00", "balance": "1200.00", "transaction_date": "2026-01-03"},
            {"debit": "50.00", "credit": "", "balance": "1150.00", "transaction_date": "2026-01-02"}
        ]
    }
    
    summary, tx_results, exceptions = service._perform_validation(norm_data)
    assert summary.validation_status == "NOT_VERIFIABLE"
    assert any(e.exception_code == "MIXED_DATE_SEQUENCE" for e in exceptions)
