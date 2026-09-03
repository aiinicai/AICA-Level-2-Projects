import pytest
import json
from app.services.profile_manager import ProfileManager
from app.models.profile import BankProfile, ColumnDefinition
from app.services.pdf_intake_service import process_uploaded_pdf
from app.services.job_state_service import create_job
from app.services.extraction_service import run_extraction
from app.services.normalization_service import get_normalization_result

@pytest.fixture
def test_job(app, fake_file_storage):
    with app.app_context():
        config = app.config['APP_CONFIG']
        metadata = process_uploaded_pdf(fake_file_storage, config)
        job_id = metadata['job_id']
        create_job(config, metadata)
        run_extraction(job_id, config)
        return job_id

def test_json_safe_helper():
    from app.models.profile import BankProfile
    from pathlib import Path
    
    def assert_json_safe(value):
        try:
            json.dumps(value)
        except TypeError as e:
            raise AssertionError(f"Not JSON safe: {e}")
            
    assert_json_safe({"safe": "string"})
    
    with pytest.raises(AssertionError):
        assert_json_safe({"prof": BankProfile("p1", "Profile 1", "Bank 1")})
        
    with pytest.raises(AssertionError):
        assert_json_safe({"path": Path("/tmp")})

def test_auto_match_serialization_and_flask_route(client, app, test_job, monkeypatch):
    # Setup strong matching profile
    with app.app_context():
        pm = ProfileManager(app.config['APP_CONFIG'])
        prof = pm.create_profile("Auto Match Profile", "Bank of Baroda")
        prof.page_width = 72.0
        prof.page_height = 72.0
        pm.save_profile(prof)
        
    def mock_calc(*args, **kwargs):
        return 100, {"bank_match": True, "dimension_match": True}
    monkeypatch.setattr('app.services.profile_matcher.ProfileMatcher._calculate_score', mock_calc)
        
    # Test POST route
    response = client.post(f'/jobs/{test_job}/normalize', follow_redirects=True)
    assert response.status_code == 200
    
    # Ensure JSON artifact is safe
    with app.app_context():
        result = get_normalization_result(test_job, app.config['APP_CONFIG'])
        assert result['profile_application']['status'] == 'AUTO_APPLIED'
        
def test_restart_auto_match_route(client, app, test_job, monkeypatch):
    with app.app_context():
        pm = ProfileManager(app.config['APP_CONFIG'])
        prof = pm.create_profile("Restart Profile", "Bank of Baroda")
        prof.page_width = 72.0
        prof.page_height = 72.0
        pm.save_profile(prof)
        
    def mock_calc(*args, **kwargs):
        return 100, {"bank_match": True, "dimension_match": True}
    monkeypatch.setattr('app.services.profile_matcher.ProfileMatcher._calculate_score', mock_calc)
        
    # POST to normalize
    response = client.post(f'/jobs/{test_job}/normalize', follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        result = get_normalization_result(test_job, app.config['APP_CONFIG'])
        assert result['profile_application']['status'] == 'AUTO_APPLIED'
    
def test_profile_suggestion_route(client, app, test_job, monkeypatch):
    with app.app_context():
        pm = ProfileManager(app.config['APP_CONFIG'])
        p1 = pm.create_profile("Ambig 1", "Bank of Baroda")
        p1.page_width = 72.0
        p1.page_height = 72.0
        pm.save_profile(p1)
        
        p2 = pm.create_profile("Ambig 2", "Bank of Baroda")
        p2.page_width = 72.0
        p2.page_height = 72.0
        pm.save_profile(p2)
        
    def mock_calc(*args, **kwargs):
        return 85, {"bank_match": True, "dimension_match": True}
    monkeypatch.setattr('app.services.profile_matcher.ProfileMatcher._calculate_score', mock_calc)
        
    response = client.post(f'/jobs/{test_job}/normalize', follow_redirects=True)
    assert response.status_code == 200
    assert b"Existing Bank Profiles" in response.data
    assert b"Ambig 1" in response.data
    with app.app_context():
        result = get_normalization_result(test_job, app.config['APP_CONFIG'])
        assert result['profile_application']['status'] == 'SELECTION_REQUIRED'
    
def test_no_match_route(client, app, test_job):
    # No profiles at all
    response = client.post(f'/jobs/{test_job}/normalize', follow_redirects=True)
    assert response.status_code == 200
    assert b"Create Profile From Statement" in response.data
    with app.app_context():
        result = get_normalization_result(test_job, app.config['APP_CONFIG'])
        assert result['profile_application']['status'] == 'NO_PROFILES_AVAILABLE'

def test_manual_fallback_application(client, app, test_job, monkeypatch):
    with app.app_context():
        pm = ProfileManager(app.config['APP_CONFIG'])
        p1 = pm.create_profile("Low Score Profile", "Bank of Baroda")
        p1.page_width = 72.0
        p1.page_height = 72.0
        pm.save_profile(p1)
        
    def mock_calc(*args, **kwargs):
        return 20, {"bank_match": False, "dimension_match": False}
    monkeypatch.setattr('app.services.profile_matcher.ProfileMatcher._calculate_score', mock_calc)
        
    response = client.post(f'/jobs/{test_job}/normalize', follow_redirects=True)
    assert response.status_code == 200
    assert b"Existing Bank Profiles" in response.data
    assert b"Low Score Profile" in response.data
    
    # Click "Use This Profile"
    response = client.post(f'/profiles/apply/{test_job}/{p1.profile_id}', follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        result = get_normalization_result(test_job, app.config['APP_CONFIG'])
        assert result['profile_application']['status'] == 'MANUAL'
