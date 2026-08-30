import uuid
from pathlib import Path
import os
from werkzeug.utils import secure_filename
import pypdf
from app.utils.hash_utils import calculate_sha256
import logging
from flask import current_app

logger = logging.getLogger(__name__)

def process_uploaded_pdf(file_storage, config):
    """
    Handles safe storage, metadata extraction, and hashing for an uploaded PDF.
    """
    job_id = str(uuid.uuid4())
    
    # Use configured temp directory
    temp_dir = Path(config.get('paths', 'temp', fallback='temp'))
    project_root = Path(__file__).resolve().parent.parent.parent
    job_dir = project_root / temp_dir / 'jobs' / job_id
    
    # Ensure job directory exists
    job_dir.mkdir(parents=True, exist_ok=True)
    
    stored_filename = 'source.pdf'
    filepath = job_dir / stored_filename
    
    original_filename = secure_filename(file_storage.filename)
    if not original_filename:
        original_filename = "unnamed.pdf"
        
    # Save file safely
    file_storage.save(filepath)
    
    file_size = os.path.getsize(filepath)
    sha256_hash = calculate_sha256(filepath)
    
    metadata = {
        'job_id': job_id,
        'source_filename': original_filename,
        'stored_filename': stored_filename,
        'file_size': file_size,
        'sha256': sha256_hash,
        'page_count': 0,
        'encrypted': False,
        'pdf_type': 'Unknown',
        'status': 'uploaded',
        'stage': 'intake',
        'error_code': None
    }
    
    # Validate PDF structure with pypdf
    try:
        with open(filepath, 'rb') as f:
            reader = pypdf.PdfReader(f)
            metadata['encrypted'] = reader.is_encrypted
            
            if metadata['encrypted']:
                metadata['status'] = 'password_required'
            else:
                metadata['page_count'] = len(reader.pages)
                metadata['status'] = 'ready_for_preview'
                metadata['pdf_type'] = 'Digital/Text PDF' # Heuristic default for now
                
    except Exception as e:
        logger.warning(f"Invalid PDF uploaded (job {job_id}): {e}")
        metadata['status'] = 'invalid'
        metadata['error_code'] = 'INVALID_PDF'
        
    return metadata

def verify_pdf_password(job_id, password, config):
    """
    Verifies if the provided password decrypts the PDF.
    If valid, creates a temporary decrypted copy in the job directory.
    """
    temp_dir = Path(config.get('paths', 'temp', fallback='temp'))
    project_root = Path(__file__).resolve().parent.parent.parent
    job_dir = project_root / temp_dir / 'jobs' / job_id
    source_path = job_dir / 'source.pdf'
    
    if not source_path.exists():
        return False
        
    try:
        reader = pypdf.PdfReader(source_path)
        if not reader.is_encrypted:
            return True
            
        # Try decrypting
        result = reader.decrypt(password)
        if result == pypdf.PasswordType.NOT_DECRYPTED:
            return False
            
        # Write decrypted temp copy
        writer = pypdf.PdfWriter()
        writer.append_pages_from_reader(reader)
        
        decrypted_path = job_dir / 'source_decrypted.pdf'
        with open(decrypted_path, 'wb') as f:
            writer.write(f)
            
        return True
    except Exception as e:
        logger.error(f"Error verifying password for job {job_id}: {e}")
        return False

def get_job_pdf_path(job_id, config):
    """
    Returns the absolute path to the PDF to serve (decrypted if applicable, else source).
    Ensures safe path resolution.
    """
    temp_dir = Path(config.get('paths', 'temp', fallback='temp'))
    project_root = Path(__file__).resolve().parent.parent.parent
    job_dir = (project_root / temp_dir / 'jobs' / job_id).resolve()
    
    # Path traversal protection - verify it's under the intended directory
    temp_jobs_root = (project_root / temp_dir / 'jobs').resolve()
    if temp_jobs_root not in job_dir.parents:
        return None
        
    decrypted_path = job_dir / 'source_decrypted.pdf'
    if decrypted_path.exists():
        return decrypted_path
        
    source_path = job_dir / 'source.pdf'
    if source_path.exists():
        return source_path
        
    return None

def cleanup_job(job_id, config):
    """
    Safely deletes the local temporary job directory and files.
    """
    import shutil
    temp_dir = Path(config.get('paths', 'temp', fallback='temp'))
    project_root = Path(__file__).resolve().parent.parent.parent
    job_dir = (project_root / temp_dir / 'jobs' / job_id).resolve()
    
    temp_jobs_root = (project_root / temp_dir / 'jobs').resolve()
    if temp_jobs_root not in job_dir.parents:
        return False
        
    if job_dir.exists() and job_dir.is_dir():
        shutil.rmtree(job_dir)
        return True
        
    return False
