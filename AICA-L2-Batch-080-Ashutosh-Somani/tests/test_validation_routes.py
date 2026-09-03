import pytest
from app.services.pdf_intake_service import process_uploaded_pdf
from app.services.job_state_service import create_job
from app.services.extraction_service import run_extraction
from app.services.normalization_service import run_normalization
from app.services.validation_service import ValidationService

def test_trigger_validation_invalid_job(client):
    response = client.post('/jobs/invalid/validate')
    assert response.status_code == 404

def test_validation_summary_invalid_job(client):
    response = client.get('/jobs/invalid/validation')
    assert response.status_code == 404

def test_exceptions_invalid_job(client):
    response = client.get('/jobs/invalid/exceptions')
    assert response.status_code == 404

def test_trigger_validation_success(client, app, fake_file_storage):
    with app.app_context():
        metadata = process_uploaded_pdf(fake_file_storage, app.config['APP_CONFIG'])
        job_id = metadata['job_id']
        create_job(app.config['APP_CONFIG'], metadata)
        run_extraction(job_id, app.config['APP_CONFIG'])
        run_normalization(job_id, app.config['APP_CONFIG'])
        
    response = client.post(f'/jobs/{job_id}/validate', follow_redirects=True)
    assert response.status_code == 200
    assert b"Statement validation complete" in response.data
    assert b"Validation Summary" in response.data

def test_exceptions_view(client, app, fake_file_storage):
    with app.app_context():
        metadata = process_uploaded_pdf(fake_file_storage, app.config['APP_CONFIG'])
        job_id = metadata['job_id']
        create_job(app.config['APP_CONFIG'], metadata)
        run_extraction(job_id, app.config['APP_CONFIG'])
        run_normalization(job_id, app.config['APP_CONFIG'])
        
        # Manually run validation
        from app.services.validation_service import ValidationService
        ValidationService(app.config['APP_CONFIG']).validate_job(job_id)
        
    response = client.get(f'/jobs/{job_id}/exceptions')
    assert response.status_code == 200
    assert b"Exceptions for Review" in response.data
