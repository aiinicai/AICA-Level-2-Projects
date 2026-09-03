import pytest
import os
from app.services.pdf_intake_service import process_uploaded_pdf
from app.services.job_state_service import create_job
from app.services.extraction_service import run_extraction
from app.services.normalization_service import run_normalization
from app.services.pdf_intake_service import calculate_sha256

def test_original_file_integrity(app, fake_file_storage):
    with app.app_context():
        import hashlib
        
        def hash_file(path):
            h = hashlib.sha256()
            with open(path, 'rb') as f:
                h.update(f.read())
            return h.hexdigest()
            
        original_hash = hash_file(fake_file_storage.path)
        
        metadata = process_uploaded_pdf(fake_file_storage, app.config['APP_CONFIG'])
        job_id = metadata['job_id']
        create_job(app.config['APP_CONFIG'], metadata)
        
        run_extraction(job_id, app.config['APP_CONFIG'])
        run_normalization(job_id, app.config['APP_CONFIG'])
        
        post_processing_hash = hash_file(fake_file_storage.path)
        
        assert original_hash == post_processing_hash
