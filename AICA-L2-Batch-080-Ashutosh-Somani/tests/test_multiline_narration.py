import pytest
from decimal import Decimal
from app.services.transaction_normalizer import TransactionNormalizer

def test_multiline_narration():
    normalizer = TransactionNormalizer()
    
    raw_tables = [
        {
            "cells": [
                ["Date", "Narration", "Debit", "Credit", "Balance"],
                ["01/01/2026", "UPI/ASHUTOSH/", "100.00", "", "900.00"],
                ["", "SOMANI/12345", "", "", ""],
                ["02/01/2026", "Next TXN", "50.00", "", "850.00"]
            ]
        }
    ]
    
    txns, warnings = normalizer.normalize(raw_tables)
    
    assert len(txns) == 2
    assert txns[0].narration == "UPI/ASHUTOSH/ SOMANI/12345"
    assert txns[0].debit == Decimal("100.00")
    
    assert txns[1].narration == "Next TXN"
    
def test_multiline_narration_ambiguous():
    normalizer = TransactionNormalizer()
    
    raw_tables = [
        {
            "cells": [
                ["Date", "Narration", "Debit", "Credit", "Balance"],
                ["01/01/2026", "UPI/ASHUTOSH/", "100.00", "", "900.00"],
                ["", "Wait what is this", "50.00", "", ""], # Has amount but no date, ambiguous
                ["02/01/2026", "Next TXN", "50.00", "", "850.00"]
            ]
        }
    ]
    
    txns, warnings = normalizer.normalize(raw_tables)
    # The second row is ambiguous and not merged, and currently skipped because of date failure 
    # but not appended to narration because of amount presence.
    # The length should be 2.
    assert len(txns) == 2
    assert txns[0].narration == "UPI/ASHUTOSH/"
