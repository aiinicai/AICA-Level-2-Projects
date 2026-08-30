import pytest
import os
import json
from pathlib import Path
from decimal import Decimal
from datetime import date
from app.services.export_service import ExportService

def test_get_masked_account(temp_config):
    svc = ExportService(temp_config)
    assert svc._get_masked_account("123") == "****"
    assert svc._get_masked_account("123456789") == "*****6789"
    assert svc._get_masked_account("") == ""

def test_machine_fallback_export(temp_config, tmp_path):
    job_id = "test_machine_export"
    job_dir = tmp_path / 'temp' / 'jobs' / job_id
    norm_dir = job_dir / 'normalization'
    norm_dir.mkdir(parents=True)
    val_dir = job_dir / 'validation'
    val_dir.mkdir(parents=True)
    
    # Write synthetic normalized data
    norm_data = {
        "job_id": job_id,
        "metadata": {"account_number": "9876543210"},
        "transactions": [
            {
                "transaction_date": "2023-01-01",
                "narration": "Test 1",
                "debit": "100.0",
                "credit": None,
                "balance": "900.0"
            }
        ]
    }
    with open(norm_dir / 'normalized_statement.json', 'w') as f:
        json.dump(norm_data, f)
        
    val_data = {
        "summary": {
            "validation_status": "VALID",
            "opening_balance": "1000.00",
            "total_debits": "100.00",
            "total_credits": "0.00",
            "expected_closing_balance": "900.00",
            "statement_closing_balance": "900.00",
            "difference": "0.00",
            "transaction_count": 1,
            "validated_transaction_count": 1,
            "balance_mismatch_count": 0,
            "transactions_not_verifiable": 0,
            "exception_count": 0
        },
        "transactions": [{"transaction_index": 0, "source_page": 1, "source_row": 1, "validation_status": "BALANCED"}],
        "exceptions": []
    }
    with open(val_dir / 'validation_result.json', 'w') as f:
        json.dump(val_data, f)
        
    temp_config.set('paths', 'temp', str(tmp_path / 'temp'))
    temp_config.set('paths', 'output', str(tmp_path / 'output'))
    
    from app.database.db import get_db_connection
    from app.database.migrations import init_db
    db_path = tmp_path / f'{job_id}.db'
    temp_config.set('paths', 'database', str(db_path))
    init_db(temp_config)
    with get_db_connection(temp_config) as conn:
        conn.execute("INSERT INTO processing_jobs (id, display_name, status, stage, sha256) VALUES (?, ?, ?, ?, ?)",
                    (job_id, 'test.pdf', 'validated', 'validation', 'hash123'))
        conn.commit()

    svc = ExportService(temp_config)
    payload = svc._get_export_payload(job_id)
    
    assert payload['summary']['export_source'] == 'Machine Normalized'
    assert payload['summary']['account_number'] == '******3210'
    assert len(payload['transactions']) == 1
    
    tx = payload['transactions'][0]
    assert tx['debit'] == Decimal("100.0")
    assert tx['credit'] is None
    assert tx['user_corrected'] is False
    assert tx['transaction_date'] == date(2023, 1, 1)

def test_safe_filename(temp_config, tmp_path):
    temp_config.set('paths', 'temp', str(tmp_path / 'temp'))
    temp_config.set('paths', 'output', str(tmp_path / 'output'))
    svc = ExportService(temp_config)
    
    path1 = svc._get_safe_filename("job1", "my report.pdf")
    assert path1.suffix == ".xlsx"
    assert "my_report" in path1.name
    
    # Touch path1 to force collision
    path1.parent.mkdir(parents=True, exist_ok=True)
    path1.touch()
    
    path2 = svc._get_safe_filename("job1", "my report.pdf")
    assert path2.name != path1.name
    assert "_1.xlsx" in path2.name
