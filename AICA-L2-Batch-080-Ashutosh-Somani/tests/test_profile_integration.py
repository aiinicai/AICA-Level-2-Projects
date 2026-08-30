import pytest
import os
import json
from decimal import Decimal
from app.services.normalization_service import run_normalization, get_normalization_result
from app.services.profile_manager import ProfileManager
from app.models.profile import BankProfile, ColumnDefinition
from app.database.migrations import init_db

def test_profile_integration(app, temp_config):
    # 1. Setup DB and Profile
    init_db(temp_config)
    manager = ProfileManager(temp_config)
    prof = manager.create_profile("Mock Bank Profile", "MOCK_BANK")
    prof.page_width = 595.0
    prof.page_height = 842.0
    prof.expected_header_signatures = ["MOCK_BANK", "STATEMENT"]
    prof.column_definitions = [
        ColumnDefinition(canonical_name="transaction_date", x0=0, x1=50),
        ColumnDefinition(canonical_name="narration", x0=50, x1=200),
        ColumnDefinition(canonical_name="amount", x0=200, x1=300),
        ColumnDefinition(canonical_name="dr_cr", x0=300, x1=400),
        ColumnDefinition(canonical_name="balance", x0=400, x1=500)
    ]
    manager.save_profile(prof)
    
    # 2. Setup mock extraction artifact
    job_id = "test_profile_job"
    from pathlib import Path
    temp_dir = Path(temp_config.get('paths', 'temp'))
    job_dir = temp_dir / 'jobs' / job_id / 'extraction'
    job_dir.mkdir(parents=True, exist_ok=True)
    
    extraction_data = {
        "job_id": job_id,
        "extractor_used": "pdfplumber",
        "extractor_version": "0.1",
        "status": "success",
        "page_count": 1,
        "pages_processed": 1,
        "total_words": 15,
        "total_characters": 100,
        "text_layer_status": "found",
        "table_candidate_count": 0,
        "pages": [
            {
                "page_number": 1,
                "width": 595.0,
                "height": 842.0,
                "raw_text": "MOCK_BANK STATEMENT OF ACCOUNT",
                "word_count": 15,
                "character_count": 100,
                "words": [
                    {"text": "01/01/2026", "x0": 10, "x1": 45, "top": 100, "bottom": 110, "page_number": 1},
                    {"text": "DEPOSIT", "x0": 60, "x1": 150, "top": 100, "bottom": 110, "page_number": 1},
                    {"text": "5000.00", "x0": 210, "x1": 250, "top": 100, "bottom": 110, "page_number": 1},
                    {"text": "CR", "x0": 310, "x1": 330, "top": 100, "bottom": 110, "page_number": 1},
                    {"text": "10000.00", "x0": 410, "x1": 460, "top": 100, "bottom": 110, "page_number": 1},
                ],
                "table_candidates": []
            }
        ]
    }
    
    with open(job_dir / 'raw_extraction.json', 'w') as f:
        json.dump(extraction_data, f)
        
    # Setup job in DB
    from app.database.db import get_db_connection
    with get_db_connection(temp_config) as conn:
        conn.execute("INSERT INTO processing_jobs (id, display_name, status, stage) VALUES (?, ?, ?, ?)",
                     (job_id, "test.pdf", "extracted", "extraction"))
        conn.commit()
        
    # 3. Run Normalization (which should trigger Matcher & CoordinateExtractor)
    with app.app_context():
        success, err = run_normalization(job_id, temp_config)
        assert success, err
        
        # 4. Verify output
        norm_result = get_normalization_result(job_id, temp_config)
        assert norm_result is not None
        
        assert norm_result['profile_application']['status'] == "AUTO_APPLIED"
        assert norm_result['profile_application']['profile_id'] == prof.profile_id
        
        txns = norm_result['transactions']
        assert len(txns) == 1
        assert txns[0]['transaction_date'] == "2026-01-01"
        assert txns[0]['narration'] == "DEPOSIT"
        assert txns[0]['credit'] == "5000.00"
        assert txns[0]['balance'] == "10000.00"
    
