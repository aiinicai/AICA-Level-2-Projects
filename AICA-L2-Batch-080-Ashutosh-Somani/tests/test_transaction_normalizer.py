import pytest
from decimal import Decimal
import datetime
from app.services.transaction_normalizer import TransactionNormalizer

@pytest.fixture
def normalizer():
    return TransactionNormalizer()

def test_normalize_debit_credit_table(normalizer):
    raw_tables = [
        {
            "cells": [
                ["Date", "Narration", "Ref", "Debit", "Credit", "Balance"],
                ["01/01/2026", "Test TXN", "123", "100.00", "", "900.00"],
                ["02/01/2026", "Deposit", "456", "", "500.00", "1400.00"]
            ]
        }
    ]
    
    txns, warnings = normalizer.normalize(raw_tables)
    assert len(warnings) == 0
    assert len(txns) == 2
    
    assert txns[0].transaction_date == datetime.date(2026, 1, 1)
    assert txns[0].narration == "Test TXN"
    assert txns[0].reference_number == "123"
    assert txns[0].debit == Decimal("100.00")
    assert txns[0].credit is None
    assert txns[0].balance == Decimal("900.00")
    
    assert txns[1].debit is None
    assert txns[1].credit == Decimal("500.00")

def test_normalize_withdrawal_deposit_table(normalizer):
    raw_tables = [
        {
            "cells": [
                ["Txn Date", "Particulars", "Withdrawal Amount", "Deposit Amount", "Closing Balance"],
                ["01-Jan-2026", "Test TXN", "1,234.56", "", "900.00"]
            ]
        }
    ]
    
    txns, warnings = normalizer.normalize(raw_tables)
    assert len(txns) == 1
    assert txns[0].debit == Decimal("1234.56")
    assert txns[0].credit is None

def test_normalize_amount_crdrt_table(normalizer):
    raw_tables = [
        {
            "cells": [
                ["Date", "Description", "Amount", "CR/DR", "Balance"],
                ["01/01/2026", "Test TXN", "100.00", "DR", "900.00 DR"],
                ["02/01/2026", "Deposit", "500.00", "CR", "400.00 DR"]
            ]
        }
    ]
    
    txns, warnings = normalizer.normalize(raw_tables)
    assert len(txns) == 2
    
    assert txns[0].debit == Decimal("100.00")
    assert txns[0].credit is None
    assert txns[0].balance == Decimal("-900.00")
    
    assert txns[1].debit is None
    assert txns[1].credit == Decimal("500.00")
    assert txns[1].balance == Decimal("-400.00")

def test_normalize_repeated_header(normalizer):
    raw_tables = [
        {
            "cells": [
                ["Date", "Narration", "Debit", "Credit", "Balance"],
                ["01/01/2026", "Test 1", "100", "", "900"],
                ["Date", "Narration", "Debit", "Credit", "Balance"], # repeated header
                ["02/01/2026", "Test 2", "", "50", "950"]
            ]
        }
    ]
    txns, warnings = normalizer.normalize(raw_tables)
    assert len(txns) == 2

def test_normalize_footer_filter(normalizer):
    raw_tables = [
        {
            "cells": [
                ["Date", "Narration", "Debit", "Credit", "Balance"],
                ["01/01/2026", "Test 1", "100", "", "900"],
                ["Page 1 of 5", ""] # footer
            ]
        }
    ]
    txns, warnings = normalizer.normalize(raw_tables)
    assert len(txns) == 1
    
def test_normalize_missing_table(normalizer):
    raw_tables = [
        {
            "cells": [
                ["Random", "Data", "Not", "Transactions"],
                ["A", "B", "C", "D"]
            ]
        }
    ]
    txns, warnings = normalizer.normalize(raw_tables)
    assert len(txns) == 0
    assert "no_transaction_table" in warnings
    
def test_normalize_malformed_amounts(normalizer):
    raw_tables = [
        {
            "cells": [
                ["Date", "Narration", "Debit", "Credit", "Balance"],
                ["01/01/2026", "Test 1", "abc", "", "900"],
            ]
        }
    ]
    txns, warnings = normalizer.normalize(raw_tables)
    assert len(txns) == 1
    assert txns[0].debit is None
    assert "malformed_amount" in txns[0].normalization_warnings
