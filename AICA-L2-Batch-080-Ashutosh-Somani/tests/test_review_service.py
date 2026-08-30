import pytest
import json
import uuid
import datetime
from pathlib import Path
from decimal import Decimal
from app.services.review_service import ReviewService
from app.services.audit_service import AuditService
from app.services.correction_service import CorrectionService
from app.models.review import CorrectionStatus, ReviewStatus

def setup_baseline(tmp_path, sample_job_id, baseline_data):
    job_dir = tmp_path / 'temp' / 'jobs' / sample_job_id
    norm_dir = job_dir / 'normalization'
    norm_dir.mkdir(parents=True)
    with open(norm_dir / 'normalized_statement.json', 'w') as f:
        json.dump(baseline_data, f)
    return norm_dir / 'normalized_statement.json'

def init_services(temp_config, tmp_path, sample_job_id):
    temp_config.set('paths', 'temp', str(tmp_path / 'temp'))
    from app.database.db import get_db_connection
    from app.database.migrations import init_db
    
    db_path = tmp_path / f'{sample_job_id}.db'
    temp_config.set('paths', 'database', str(db_path))
    init_db(temp_config)
    with get_db_connection(temp_config) as conn:
        conn.execute("INSERT INTO processing_jobs (id, display_name, status, stage) VALUES (?, ?, ?, ?)",
                    (sample_job_id, 'test.pdf', 'normalized', 'normalization'))
        conn.commit()

    rev_svc = ReviewService(temp_config)
    aud_svc = AuditService(temp_config)
    corr_svc = CorrectionService(rev_svc, aud_svc)
    return rev_svc, aud_svc, corr_svc

def test_review_lifecycle(temp_config, tmp_path):
    sample_job_id = "test_review_lifecycle"
    baseline_data = {
        "job_id": sample_job_id,
        "transactions": [
            {
                "transaction_date": "2023-01-01",
                "narration": "Test 1",
                "debit": "100.50",
                "credit": None,
                "balance": "900.50",
                "source_page": 1,
                "source_row": 0
            }
        ]
    }
    setup_baseline(tmp_path, sample_job_id, baseline_data)
    rev_svc, aud_svc, corr_svc = init_services(temp_config, tmp_path, sample_job_id)
    
    # 1. Initialize
    statement = rev_svc.initialize_review(sample_job_id)
    assert statement.review_revision == 1
    
    tx = statement.transactions[0]
    
    # 2. Edit
    statement = corr_svc.apply_edit(sample_job_id, 1, tx.transaction_id, {"debit": "100.55"})
    assert statement.transactions[0].debit == Decimal("100.55")
    
    # 4. Check optimistic concurrency
    with pytest.raises(ValueError, match="REVIEW_REVISION_CONFLICT"):
        corr_svc.apply_edit(sample_job_id, 1, tx.transaction_id, {"debit": "0"})
        
    # 5. Check Non-transaction
    statement = corr_svc.mark_non_transaction(sample_job_id, 2, tx.transaction_id)
    assert statement.transactions[0].review_status == CorrectionStatus.NON_TRANSACTION
    
    # 6. Check revert
    statement = corr_svc.revert_transaction(sample_job_id, 3, tx.transaction_id)
    assert statement.transactions[0].debit == Decimal("100.50")
    
def test_blank_vs_zero(temp_config, tmp_path):
    sample_job_id = "test_blank_zero"
    baseline_data = {
        "job_id": sample_job_id,
        "transactions": [{"transaction_date": "2023-01-01", "narration": "A", "debit": "10.0", "credit": None, "balance": "100.0"}]
    }
    setup_baseline(tmp_path, sample_job_id, baseline_data)
    rev_svc, aud_svc, corr_svc = init_services(temp_config, tmp_path, sample_job_id)
    
    statement = rev_svc.initialize_review(sample_job_id)
    tx_id = statement.transactions[0].transaction_id
    
    # Blank credit (None)
    assert statement.transactions[0].credit is None
    
    # Edit debit to zero explicitly
    statement = corr_svc.apply_edit(sample_job_id, 1, tx_id, {"debit": "0.00", "credit": ""})
    tx = statement.transactions[0]
    assert tx.debit == Decimal("0.00")
    assert tx.credit is None
    
    # Reload from disk to ensure persistence
    statement2 = rev_svc.load_reviewed_statement(sample_job_id)
    assert statement2.transactions[0].debit == Decimal("0.00")
    assert statement2.transactions[0].credit is None

def test_machine_baseline_immutability(temp_config, tmp_path):
    sample_job_id = "test_immutability"
    baseline_data = {
        "job_id": sample_job_id,
        "transactions": [{"transaction_date": "2023-01-01", "narration": "Baseline", "debit": "50.0", "credit": None, "balance": "100.0"}]
    }
    baseline_path = setup_baseline(tmp_path, sample_job_id, baseline_data)
    
    import hashlib
    with open(baseline_path, 'rb') as f:
        original_hash = hashlib.sha256(f.read()).hexdigest()
        
    rev_svc, aud_svc, corr_svc = init_services(temp_config, tmp_path, sample_job_id)
    statement = rev_svc.initialize_review(sample_job_id)
    tx_id = statement.transactions[0].transaction_id
    
    # Mutate heavily
    corr_svc.apply_edit(sample_job_id, 1, tx_id, {"debit": "100.0"})
    
    with open(baseline_path, 'rb') as f:
        new_hash = hashlib.sha256(f.read()).hexdigest()
        
    assert original_hash == new_hash

def test_merge_workflow_and_financial_safety(temp_config, tmp_path):
    sample_job_id = "test_merge"
    baseline_data = {
        "job_id": sample_job_id,
        "transactions": [
            {"transaction_date": "2023-01-01", "narration": "Row 1", "debit": "50.0", "credit": None, "balance": "100.0"},
            {"transaction_date": None, "narration": "Row 2", "debit": "20.0", "credit": None, "balance": "80.0"}
        ]
    }
    setup_baseline(tmp_path, sample_job_id, baseline_data)
    rev_svc, aud_svc, corr_svc = init_services(temp_config, tmp_path, sample_job_id)
    
    statement = rev_svc.initialize_review(sample_job_id)
    tx1 = statement.transactions[0].transaction_id
    tx2 = statement.transactions[1].transaction_id
    
    # Explicit user data for merge
    merged_data = {
        "transaction_date": "2023-01-01",
        "narration": "Row 1 Row 2",
        "debit": "70.00",
        "credit": "",
        "balance": "80.00"
    }
    
    statement = corr_svc.merge_rows(sample_job_id, 1, [tx1, tx2], merged_data)
    
    assert statement.review_revision == 2
    active = [t for t in statement.transactions if t.review_status != CorrectionStatus.SUPERSEDED]
    assert len(active) == 1
    assert active[0].debit == Decimal("70.00")
    assert tx1 in active[0].derived_from_transaction_ids
    assert tx2 in active[0].derived_from_transaction_ids

def test_split_workflow(temp_config, tmp_path):
    sample_job_id = "test_split"
    baseline_data = {
        "job_id": sample_job_id,
        "transactions": [
            {"transaction_date": "2023-01-01", "narration": "Combined", "debit": "100.0", "credit": None, "balance": "100.0"}
        ]
    }
    setup_baseline(tmp_path, sample_job_id, baseline_data)
    rev_svc, aud_svc, corr_svc = init_services(temp_config, tmp_path, sample_job_id)
    
    statement = rev_svc.initialize_review(sample_job_id)
    tx1 = statement.transactions[0].transaction_id
    
    child_list = [
        {"transaction_date": "2023-01-01", "narration": "Part 1", "debit": "60.00", "credit": "", "balance": "160.0"},
        {"transaction_date": "2023-01-01", "narration": "Part 2", "debit": "40.00", "credit": "", "balance": "100.0"}
    ]
    
    statement = corr_svc.split_row(sample_job_id, 1, tx1, child_list)
    assert statement.review_revision == 2
    active = [t for t in statement.transactions if t.review_status != CorrectionStatus.SUPERSEDED]
    assert len(active) == 2
    assert active[0].debit == Decimal("60.00")
    assert active[1].debit == Decimal("40.00")
    assert tx1 in active[0].derived_from_transaction_ids
    assert tx1 in active[1].derived_from_transaction_ids

def test_correction_creates_exception(temp_config, tmp_path):
    sample_job_id = "test_exception"
    baseline_data = {
        "job_id": sample_job_id,
        "transactions": [
            {"transaction_date": "2023-01-01", "narration": "Valid", "debit": "10.0", "credit": None, "balance": "90.0"}
        ]
    }
    setup_baseline(tmp_path, sample_job_id, baseline_data)
    rev_svc, aud_svc, corr_svc = init_services(temp_config, tmp_path, sample_job_id)
    
    # We mock validator to succeed initially, but fail if debit != 10
    class MockValidator:
        def _perform_validation(self, norm_dict):
            from app.models.validation import StatementValidationResult, TransactionValidationResult
            from decimal import Decimal
            import uuid
            txs = []
            excs = []
            for i, t in enumerate(norm_dict['transactions']):
                if t['debit'] == 10.01:
                    from app.models.exception import ExceptionRecord
                    excs.append(ExceptionRecord(
                        transaction_index=i,
                        exception_code="BALANCE_MISMATCH",
                        severity="ERROR",
                        message="Mismatch",
                        context={}
                    ))
                txs.append(TransactionValidationResult(transaction_index=i, source_page=1, source_row=1))
            val_summary = StatementValidationResult(
                validation_status="VALID" if not excs else "EXCEPTIONS_FOUND"
            )
            return val_summary, txs, excs
            
    rev_svc.validator = MockValidator()
    
    statement = rev_svc.initialize_review(sample_job_id)
    tx_id = statement.transactions[0].transaction_id
    
    statement = corr_svc.apply_edit(sample_job_id, 1, tx_id, {"debit": "10.01"})
    
    # The review status should be EXCEPTIONS_FOUND because our edit ruined it
    assert statement.review_status == ReviewStatus.REVIEWED_WITH_EXCEPTIONS

