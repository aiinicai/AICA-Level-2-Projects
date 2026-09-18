"""Tests for database layer and CRUD operations (§13)."""
import os
import pytest
from src.database.repository import Repository
from src.core.calculator import SingleRatioResult
from src.core.integrity import IntegrityCheckResult
from src.core.audit import AuditLogger


def test_client_crud_and_backup(temp_db_repo, tmp_path):
    repo = temp_db_repo
    
    # Empty at start
    clients = repo.list_clients()
    assert len(clients) == 0
    
    # Create client
    cid = repo.create_client("Alpha Industries")
    assert cid > 0
    
    # Get client
    c = repo.get_client(cid)
    assert c["name"] == "Alpha Industries"
    
    # Case insensitive duplicate check
    c_dup = repo.get_client_by_name("alpha industries")
    assert c_dup is not None
    
    # Rename
    repo.update_client_name(cid, "Alpha Global Industries")
    c_renamed = repo.get_client(cid)
    assert c_renamed["name"] == "Alpha Global Industries"
    
    # Duplicate
    dup_id = repo.duplicate_client(cid, "Alpha Global Industries (Copy)")
    assert dup_id > cid
    assert len(repo.list_clients()) == 2
    
    # Save Analysis
    r = SingleRatioResult(
        id=1, key="current_ratio", name="Current Ratio", clause="", unit="x",
        is_percentage=False, numerator_desc="", denominator_desc="",
        numerator_cy=100.0, denominator_cy=50.0, value_cy=2.0, value_cy_formatted="2.00",
        numerator_py=90.0, denominator_py=45.0, value_py=2.0, value_py_formatted="2.00",
        variance_pct=0.0, variance_pct_formatted="0.00%", is_flagged=False, status="OK"
    )
    ic = IntegrityCheckResult(
        check_id="IC-1", name="Balance Sheet", description="", status="Pass",
        expected="0", actual="0", difference=0.0, comment="Passed"
    )
    logger = AuditLogger()
    logger.log("TEST", "Sample audit event")
    
    analysis_id = repo.save_analysis(cid, "FY 2026", 25.0, [r], [ic], logger)
    assert analysis_id > 0
    
    # Backup & Restore
    backup_file = str(tmp_path / "backup_test.db")
    repo.backup_to_file(backup_file)
    assert os.path.exists(backup_file)
    
    # Delete client
    repo.delete_client(cid)
    assert len(repo.list_clients()) == 1
    
    # Restore
    repo.restore_from_file(backup_file)
    assert len(repo.list_clients()) == 2
