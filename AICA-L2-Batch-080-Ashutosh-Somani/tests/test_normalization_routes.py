import pytest
from app.services.pdf_intake_service import process_uploaded_pdf
from app.services.job_state_service import create_job
from app.services.extraction_service import run_extraction
from app.services.normalization_service import run_normalization

@pytest.fixture
def normalized_job(app, fake_file_storage):
    with app.app_context():
        metadata = process_uploaded_pdf(fake_file_storage, app.config['APP_CONFIG'])
        job_id = metadata['job_id']
        create_job(app.config['APP_CONFIG'], metadata)
        run_extraction(job_id, app.config['APP_CONFIG'])
        run_normalization(job_id, app.config['APP_CONFIG'])
        return job_id

def test_trigger_normalization_invalid_job(client):
    response = client.post('/jobs/invalid/normalize')
    assert response.status_code == 404

def test_normalization_summary_invalid_job(client):
    response = client.get('/jobs/invalid/normalization')
    assert response.status_code == 404

def test_trigger_normalization_success(client, app, fake_file_storage):
    with app.app_context():
        metadata = process_uploaded_pdf(fake_file_storage, app.config['APP_CONFIG'])
        job_id = metadata['job_id']
        create_job(app.config['APP_CONFIG'], metadata)
        run_extraction(job_id, app.config['APP_CONFIG'])
        
    response = client.post(f'/jobs/{job_id}/normalize', follow_redirects=True)
    assert response.status_code == 200
    assert b"Statement normalization complete" in response.data
    assert b"Normalization Summary" in response.data

def test_normalization_summary_view(client, normalized_job):
    response = client.get(f'/jobs/{normalized_job}/normalization')
    assert response.status_code == 200
    assert b"Normalization Summary" in response.data
    assert b"Bank Detection" in response.data
    assert b"Statement Metadata" in response.data

def test_normalized_transactions_view(client, normalized_job):
    response = client.get(f'/jobs/{normalized_job}/transactions')
    assert response.status_code == 200
    assert b"Normalized Transactions" in response.data
    assert b"Txn Date" in response.data
