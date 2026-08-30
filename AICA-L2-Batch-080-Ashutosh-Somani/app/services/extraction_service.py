import json
import logging
from pathlib import Path
from flask import current_app
from app.extractors.pdfplumber_extractor import PdfPlumberExtractor
from app.services.pdf_intake_service import get_job_pdf_path
from app.services.job_state_service import update_job_status, get_job
from app.database.db import get_db_connection

logger = logging.getLogger(__name__)

def run_extraction(job_id, config):
    """
    Orchestrates the extraction process.
    """
    job = get_job(config, job_id)
    if not job:
        return False, "Job not found"
        
    pdf_path = get_job_pdf_path(job_id, config)
    if not pdf_path or not pdf_path.exists():
        return False, "Source PDF not available. It might have been cleaned up or password is missing."

    update_job_status(config, job_id, 'extracting')
    
    # 1. Select Extractor (Only pdfplumber in Stage 3)
    extractor = PdfPlumberExtractor()
    
    # 2. Extract
    try:
        result = extractor.extract(job_id, str(pdf_path), config)
        
        # 3. Store raw artifact JSON
        temp_dir = Path(config.get('paths', 'temp', fallback='temp'))
        project_root = Path(__file__).resolve().parent.parent.parent
        job_dir = project_root / temp_dir / 'jobs' / job_id
        
        extraction_dir = job_dir / 'extraction'
        extraction_dir.mkdir(exist_ok=True)
        
        artifact_path = extraction_dir / 'raw_extraction.json'
        with open(artifact_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False)
            
        # 4. Update Database Metadata
        with get_db_connection(config) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE processing_jobs 
                SET extractor_used = ?,
                    extraction_status = ?,
                    pages_processed = ?,
                    total_words = ?,
                    total_characters = ?,
                    table_candidate_count = ?,
                    status = 'ready_for_review',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                result.extractor_used,
                result.text_layer_status,
                result.pages_processed,
                result.total_words,
                result.total_characters,
                result.table_candidate_count,
                job_id
            ))
            
        return True, None
        
    except Exception as e:
        logger.error(f"Extraction failed for job {job_id}: {e}", exc_info=True)
        update_job_status(config, job_id, 'extraction_failed', error_code='EXTRACTION_ERROR')
        return False, str(e)

def get_extraction_result(job_id, config):
    """
    Loads the effective extraction artifact (if OCR ran) or the raw extraction JSON from disk.
    """
    if hasattr(config, 'get') and hasattr(config, 'read'):
        temp_dir_str = config.get('paths', 'temp', fallback='temp')
    elif hasattr(config, 'get') and 'APP_CONFIG' in config:
        temp_dir_str = config['APP_CONFIG'].get('paths', 'temp', fallback='temp')
    else:
        temp_dir_str = 'temp'
    temp_dir = Path(temp_dir_str)
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Check for OCR effective extraction first
    effective_path = project_root / temp_dir / 'jobs' / job_id / 'ocr' / 'effective_extraction.json'
    if effective_path.exists():
        try:
            with open(effective_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read effective extraction result for {job_id}: {e}")
            
    # Fallback to raw extraction
    artifact_path = project_root / temp_dir / 'jobs' / job_id / 'extraction' / 'raw_extraction.json'
    
    if artifact_path.exists():
        try:
            with open(artifact_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read raw extraction result for {job_id}: {e}")
    return None
