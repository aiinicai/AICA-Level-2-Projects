import pytest
from app.services.statement_metadata_service import StatementMetadataService

def test_metadata_extraction_account_number():
    service = StatementMetadataService()
    
    text1 = "A/C NO: 1234567890"
    meta = service.extract_metadata(text1)
    assert meta.account_number == "1234567890"
    
    text2 = "Account Number 0987654321"
    meta = service.extract_metadata(text2)
    assert meta.account_number == "0987654321"
    
def test_metadata_extraction_ifsc():
    service = StatementMetadataService()
    text = "IFSC Code: HDFC0001234"
    meta = service.extract_metadata(text)
    assert meta.ifsc == "HDFC0001234"

def test_metadata_extraction_period():
    service = StatementMetadataService()
    text = "Statement Period: 01-Jan-2026 to 31-Jan-2026"
    meta = service.extract_metadata(text)
    assert meta.statement_start_date == "2026-01-01"
    assert meta.statement_end_date == "2026-01-31"
