import pytest
import os
import json
from decimal import Decimal
from app.services.normalization_service import run_normalization, get_normalization_result
from app.services.profile_manager import ProfileManager
from app.models.profile import BankProfile, ColumnDefinition, TableRegion
from app.database.migrations import init_db
from flask import current_app

def test_api_preview_extraction(app, client, temp_config):
    init_db(temp_config)
    
    # 2. Setup mock extraction artifact
    job_id = "test_profile_preview"
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
                    # inside bbox
                    {"text": "01/01/2026", "x0": 10, "x1": 45, "top": 100, "bottom": 110, "page_number": 1},
                    {"text": "DEPOSIT", "x0": 60, "x1": 150, "top": 100, "bottom": 110, "page_number": 1},
                    {"text": "5000.00", "x0": 210, "x1": 250, "top": 100, "bottom": 110, "page_number": 1},
                    {"text": "CR", "x0": 310, "x1": 330, "top": 100, "bottom": 110, "page_number": 1},
                    {"text": "10000.00", "x0": 410, "x1": 460, "top": 100, "bottom": 110, "page_number": 1},
                    # outside bbox (should be excluded)
                    {"text": "PAGE", "x0": 500, "x1": 520, "top": 10, "bottom": 20, "page_number": 1},
                ],
                "table_candidates": []
            }
        ]
    }
    
    with open(job_dir / 'raw_extraction.json', 'w') as f:
        json.dump(extraction_data, f)
        
    from app.database.db import get_db_connection
    with get_db_connection(temp_config) as conn:
        conn.execute("INSERT INTO processing_jobs (id, display_name, status, stage) VALUES (?, ?, ?, ?)",
                     (job_id, "test.pdf", "extracted", "extraction"))
        conn.commit()
        
    payload = {
        "job_id": job_id,
        "profile_data": {
            "profile_name": "Test",
            "bank_name": "Test Bank",
            "table_bbox": {"x0": 0, "top": 50, "x1": 500, "bottom": 800},
            "column_definitions": [
                {"canonical_name": "transaction_date", "x0": 0, "x1": 50},
                {"canonical_name": "narration", "x0": 50, "x1": 200},
                {"canonical_name": "amount", "x0": 200, "x1": 300},
                {"canonical_name": "dr_cr", "x0": 300, "x1": 400},
                {"canonical_name": "balance", "x0": 400, "x1": 500}
            ]
        }
    }
    
    response = client.post('/profiles/api/preview', json=payload)
    assert response.status_code == 200
    data = response.json
    assert data['status'] == 'success'
    
    # Verify raw rows include header and 1 row
    assert len(data['raw_rows']) > 0
    # Verify transaction parsed correctly
    txns = data['transactions']
    assert len(txns) == 1
    assert txns[0]['transaction_date'] == "2026-01-01"
    
    # Confirm it did NOT save anything to profiles/ directory
    manager = ProfileManager(temp_config)
    assert len(manager.list_profiles()) == 0
