import pytest
import os
from app.services.extraction_service import run_extraction, get_extraction_result
from app.services.pdf_intake_service import process_uploaded_pdf

def test_extraction_service_success(app, fake_file_storage):
    with app.app_context():
        # Intake a file
        metadata = process_uploaded_pdf(fake_file_storage, app.config['APP_CONFIG'])
        job_id = metadata['job_id']
        
        # We need the job in DB for extraction service to succeed
        from app.services.job_state_service import create_job
        create_job(app.config['APP_CONFIG'], metadata)
        
        success, error = run_extraction(job_id, app.config['APP_CONFIG'])
        assert success is True
        assert error is None
        
        result = get_extraction_result(job_id, app.config['APP_CONFIG'])
        assert result is not None
        assert result['job_id'] == job_id
        assert result['status'] == 'success'
        assert result['text_layer_status'] == 'none' # Since sample is blank

def test_extraction_service_missing_job(app):
    with app.app_context():
        success, error = run_extraction("fake_id", app.config['APP_CONFIG'])
        assert success is False
        assert "Job not found" in error

def test_extraction_service_missing_pdf(app):
    with app.app_context():
        # Create a DB entry but no file
        metadata = {
            'job_id': 'missing_pdf_id',
            'source_filename': 'fake.pdf',
            'stored_filename': 'source.pdf',
            'file_size': 0,
            'sha256': 'fake',
            'page_count': 0,
            'encrypted': False,
            'pdf_type': 'Unknown',
            'status': 'uploaded',
            'stage': 'intake',
            'error_code': None
        }
        from app.services.job_state_service import create_job
        create_job(app.config['APP_CONFIG'], metadata)
        
        success, error = run_extraction("missing_pdf_id", app.config['APP_CONFIG'])
        assert success is False
        assert "Source PDF not available" in error
