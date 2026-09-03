import pytest
from app.models.profile import BankProfile, TableRegion, ColumnDefinition
from app.extractors.coordinate_extractor import CoordinateExtractor
from app.models.extraction_result import ExtractionResult, RawPage, RawWord

def test_coordinate_extractor():
    prof = BankProfile(
        profile_id="p1", profile_name="Test", bank_name="Test",
        table_bbox=TableRegion(x0=0, top=10, x1=500, bottom=100),
        column_definitions=[
            ColumnDefinition(canonical_name="transaction_date", x0=0, x1=50),
            ColumnDefinition(canonical_name="narration", x0=50, x1=200),
            ColumnDefinition(canonical_name="amount", x0=200, x1=300)
        ],
        row_y_tolerance=5.0
    )
    
    extractor = CoordinateExtractor(prof)
    
    page = RawPage(
        page_number=1, width=500, height=800, raw_text="", word_count=5, character_count=20,
        words=[
            # Row 1
            RawWord(text="01/01/26", x0=10, x1=40, top=20, bottom=30, page_number=1),
            RawWord(text="DEPOSIT", x0=60, x1=120, top=21, bottom=31, page_number=1),
            RawWord(text="100.00", x0=210, x1=250, top=20, bottom=30, page_number=1),
            
            # Row 2 (Out of bounds Y)
            RawWord(text="IGNORE", x0=10, x1=40, top=150, bottom=160, page_number=1)
        ]
    )
    
    er = ExtractionResult(
        job_id="test", extractor_used="pdfplumber", extractor_version="1",
        status="success", page_count=1, pages_processed=1,
        total_words=4, total_characters=20, text_layer_status="found",
        table_candidate_count=0, pages=[page]
    )
    
    res = extractor.extract(er)
    
    assert res.table_candidate_count == 1
    tc = res.pages[0].table_candidates[0]
    
    assert tc.row_count == 2 # header + 1 data row
    assert tc.column_count == 3
    
    assert tc.cells[0] == ["transaction_date", "narration", "amount"]
    assert tc.cells[1][0] == "01/01/26"
    assert tc.cells[1][1] == "DEPOSIT"
    assert tc.cells[1][2] == "100.00"
