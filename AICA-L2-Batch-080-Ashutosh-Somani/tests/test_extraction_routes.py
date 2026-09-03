import pytest
from app.services.pdf_intake_service import process_uploaded_pdf
from app.services.job_state_service import create_job
from app.services.extraction_service import run_extraction

@pytest.fixture
def extracted_job(app, fake_file_storage):
    with app.app_context():
        metadata = process_uploaded_pdf(fake_file_storage, app.config['APP_CONFIG'])
        job_id = metadata['job_id']
        create_job(app.config['APP_CONFIG'], metadata)
        run_extraction(job_id, app.config['APP_CONFIG'])
        return job_id

def test_trigger_extraction_invalid_job(client):
    response = client.post('/jobs/invalid/extract')
    assert response.status_code == 404

def test_diagnostics_invalid_job(client):
    response = client.get('/jobs/invalid/diagnostics')
    assert response.status_code == 404

def test_trigger_extraction_success(client, app, fake_file_storage):
    with app.app_context():
        metadata = process_uploaded_pdf(fake_file_storage, app.config['APP_CONFIG'])
        job_id = metadata['job_id']
        create_job(app.config['APP_CONFIG'], metadata)
        
    response = client.post(f'/jobs/{job_id}/extract', follow_redirects=True)
    assert response.status_code == 200
    assert b"Digital extraction complete" in response.data

def test_diagnostics_views(client, extracted_job):
    # Summary
    response = client.get(f'/jobs/{extracted_job}/diagnostics')
    assert response.status_code == 200
    assert b"Digital Extraction Diagnostics" in response.data
    
    # Raw text
    response = client.get(f'/jobs/{extracted_job}/diagnostics/raw_text')
    assert response.status_code == 200
    assert b"Diagnostic: Raw Text" in response.data
    
    # Geometry
    response = client.get(f'/jobs/{extracted_job}/diagnostics/geometry')
    assert response.status_code == 200
    assert b"Diagnostic: Word Geometry" in response.data
    
    # Tables
    response = client.get(f'/jobs/{extracted_job}/diagnostics/tables')
    assert response.status_code == 200
    assert b"Diagnostic: Table Candidates" in response.data
