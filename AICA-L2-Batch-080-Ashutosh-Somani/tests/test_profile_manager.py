import pytest
import os
import json
import uuid
from app.models.profile import BankProfile
from app.services.profile_manager import ProfileManager
from app.database.migrations import init_db

def test_profile_creation(temp_config):
    init_db(temp_config)
    manager = ProfileManager(temp_config)
    
    prof = manager.create_profile("HDFC Current v1", "HDFC Bank")
    assert prof.profile_name == "HDFC Current v1"
    assert prof.bank_name == "HDFC Bank"
    assert prof.revision_number == 1
    
    # Verify save
    path = manager._get_path(prof.profile_id)
    assert path.exists()
    
    with open(path, 'r') as f:
        data = json.load(f)
        assert data['profile_name'] == "HDFC Current v1"

def test_profile_revision_and_backup(temp_config):
    init_db(temp_config)
    manager = ProfileManager(temp_config)
    prof = manager.create_profile("ICICI v1", "ICICI Bank")
    
    # Update profile
    prof.notes = "Updated notes"
    manager.save_profile(prof)
    
    assert prof.revision_number == 2
    
    # Check backups directory
    backups = list(manager.backups_dir.glob(f"{prof.profile_id}_*.json"))
    assert len(backups) == 1
    
def test_import_profile(temp_config):
    init_db(temp_config)
    manager = ProfileManager(temp_config)
    
    unique_id = str(uuid.uuid4())
    data = {
        "profile_id": unique_id,
        "profile_name": "Axis v1",
        "bank_name": "Axis Bank",
        "layout_version": "1.0",
        "notes": "Imported"
    }
    
    success, result_id = manager.import_profile(data)
    assert success
    
    prof = manager.get_profile(result_id)
    assert prof is not None
    assert prof.profile_name == "Axis v1"
    
def test_import_duplicate_clone(temp_config):
    init_db(temp_config)
    manager = ProfileManager(temp_config)
    prof = manager.create_profile("Test Bank", "Test")
    
    data = prof.to_dict()
    
    success, result_id = manager.import_profile(data, handle_duplicate="clone")
    assert success
    assert result_id != prof.profile_id
    
    cloned = manager.get_profile(result_id)
    assert "(Imported Clone)" in cloned.profile_name
