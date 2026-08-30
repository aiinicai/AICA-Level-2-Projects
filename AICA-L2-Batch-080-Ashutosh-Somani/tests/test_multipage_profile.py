import pytest
import copy
from unittest.mock import patch, MagicMock
from app.models.extraction_result import ExtractionResult, RawPage, RawWord, RawTableCandidate
from app.models.profile import BankProfile, TableRegion, ColumnDefinition
from app.extractors.coordinate_extractor import CoordinateExtractor
from app.services.transaction_normalizer import TransactionNormalizer

def test_multipage_coordinate_extractor_and_normalizer():
    # 1. Create Profile
    profile = BankProfile(profile_id="test_multi", profile_name="MultiPage Profile", bank_name="Test Bank")
    profile.table_bbox = TableRegion(x0=50, top=300, x1=500, bottom=700) # Page 1 region (header takes up 300px)
    
    # We leave continuation_table_bbox None to test the fallback logic
    
    profile.column_definitions = [
        ColumnDefinition("transaction_date", 50, 100, required=True),
        ColumnDefinition("narration", 100, 300, required=False),
        ColumnDefinition("debit", 300, 350, required=False),
        ColumnDefinition("credit", 350, 400, required=False),
        ColumnDefinition("balance", 400, 500, required=False)
    ]
    
    # 2. Synthetic ExtractionResult
    # Page 1: 5 txns
    # Page 2: 6 txns
    # Page 3: 7 txns
    
    def create_page(page_num, start_y, txn_count, start_id=1):
        words = []
        y = start_y
        for i in range(txn_count):
            # date
            words.append(RawWord(f"01/01/2026", 55, 95, y, y+10, page_num))
            # narration
            words.append(RawWord(f"Txn {start_id + i}", 105, 195, y, y+10, page_num))
            # debit
            words.append(RawWord(f"100.00", 305, 345, y, y+10, page_num))
            # credit
            words.append(RawWord(f"", 355, 395, y, y+10, page_num))
            # balance
            words.append(RawWord(f"1000.00", 405, 495, y, y+10, page_num))
            y += 20
        return RawPage(
            page_number=page_num,
            width=600,
            height=800,
            raw_text="...",
            word_count=len(words),
            character_count=100,
            words=words
        )
        
    p1 = create_page(1, 350, 5, 1) # Starts at 350 (inside 300-700)
    p2 = create_page(2, 100, 6, 6) # Starts at 100 (outside page 1 region, should be caught by continuation)
    p3 = create_page(3, 100, 7, 12)
    
    # Test boundary narration merge
    # We will add an extra row at the start of Page 2 with NO date, NO amount, just narration
    # This should merge into the LAST txn of Page 1 (Txn 5)
    p2.words.insert(0, RawWord("Continued Narration", 105, 195, 80, 90, 2))
    p2.word_count += 1
    
    ext_result = ExtractionResult(
        job_id="test",
        extractor_used="x",
        extractor_version="1",
        status="success",
        page_count=3,
        pages_processed=3,
        total_words=100,
        total_characters=500,
        text_layer_status="present",
        table_candidate_count=0
    )
    ext_result.pages = [p1, p2, p3]
    
    # 3. Extract Coordinates
    extractor = CoordinateExtractor(profile)
    ext_result = extractor.extract(ext_result)
    
    assert len(ext_result.pages) == 3
    assert len(ext_result.pages[0].table_candidates) == 1
    assert len(ext_result.pages[1].table_candidates) == 1
    assert len(ext_result.pages[2].table_candidates) == 1
    
    # Extract raw tables
    raw_tables = []
    for p in ext_result.pages:
        for tc in p.table_candidates:
            # Need to provide dict for normalizer
            raw_tables.append(tc if isinstance(tc, dict) else tc.__dict__)
            
    # 4. Normalize
    normalizer = TransactionNormalizer()
    transactions, warnings = normalizer.normalize(raw_tables)
    
    # Assert
    assert len(transactions) == 18, f"Expected 18 transactions, got {len(transactions)}"
    
    # Verify continuation merge
    txn5 = transactions[4]
    assert "Txn 5" in txn5.narration
    
    # Check source pages
    pages_found = [t.source_page for t in transactions]
    assert pages_found.count(1) == 5
    assert pages_found.count(2) == 6
    assert pages_found.count(3) == 7
