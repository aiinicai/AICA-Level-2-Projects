from app.services.pdf_intake_service import process_uploaded_pdf, verify_pdf_password, cleanup_job, get_job_pdf_path
from app.utils.hash_utils import calculate_sha256
from flask import Flask
from app import create_app
import os

def test_calculate_sha256(sample_pdf):
    # Deterministic SHA-256 for a known file isn't strict, but we can verify it returns a 64-char string
    h = calculate_sha256(sample_pdf)
    assert len(h) == 64
    assert isinstance(h, str)

def test_process_uploaded_pdf_valid(app, fake_file_storage):
    with app.app_context():
        metadata = process_uploaded_pdf(fake_file_storage, app.config['APP_CONFIG'])
        
        assert metadata['job_id'] is not None
        assert metadata['status'] == 'ready_for_preview'
        assert metadata['page_count'] == 1
        assert metadata['encrypted'] is False
        assert metadata['sha256'] is not None

def test_process_uploaded_pdf_encrypted(app, fake_encrypted_storage):
    with app.app_context():
        metadata = process_uploaded_pdf(fake_encrypted_storage, app.config['APP_CONFIG'])
        
        assert metadata['job_id'] is not None
        assert metadata['status'] == 'password_required'
        assert metadata['encrypted'] is True

def test_process_uploaded_pdf_invalid(app, fake_invalid_storage):
    with app.app_context():
        metadata = process_uploaded_pdf(fake_invalid_storage, app.config['APP_CONFIG'])
        
        assert metadata['job_id'] is not None
        assert metadata['status'] == 'invalid'
        assert metadata['error_code'] == 'INVALID_PDF'

def test_verify_password_correct(app, fake_encrypted_storage):
    with app.app_context():
        metadata = process_uploaded_pdf(fake_encrypted_storage, app.config['APP_CONFIG'])
        
        # Check incorrect password
        assert verify_pdf_password(metadata['job_id'], "wrong", app.config['APP_CONFIG']) is False
        
        # Check correct password
        assert verify_pdf_password(metadata['job_id'], "secret", app.config['APP_CONFIG']) is True
        
        # Ensure temporary decrypted file exists
        decrypted_path = get_job_pdf_path(metadata['job_id'], app.config['APP_CONFIG'])
        assert "source_decrypted.pdf" in str(decrypted_path)
        assert os.path.exists(decrypted_path)

def test_cleanup_job(app, fake_file_storage):
    with app.app_context():
        metadata = process_uploaded_pdf(fake_file_storage, app.config['APP_CONFIG'])
        job_id = metadata['job_id']
        
        pdf_path = get_job_pdf_path(job_id, app.config['APP_CONFIG'])
        assert os.path.exists(pdf_path)
        
        assert cleanup_job(job_id, app.config['APP_CONFIG']) is True
        assert not os.path.exists(pdf_path)
