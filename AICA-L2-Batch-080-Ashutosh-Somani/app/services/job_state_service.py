import configparser
import logging
from app.database.db import get_db_connection

logger = logging.getLogger(__name__)

def get_recent_jobs(config: configparser.ConfigParser, limit=5):
    """
    Retrieve recent jobs for the dashboard shell.
    """
    jobs = []
    try:
        with get_db_connection(config) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, created_at, display_name, status, stage 
                FROM processing_jobs 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            for row in rows:
                jobs.append(dict(row))
    except Exception as e:
        logger.error(f"Failed to retrieve jobs: {e}")
    
    return jobs

def create_job(config, metadata):
    try:
        with get_db_connection(config) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO processing_jobs 
                (id, display_name, status, stage, source_filename, stored_filename, file_size, sha256, page_count, pdf_type, encrypted, error_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metadata['job_id'],
                metadata['source_filename'],
                metadata['status'],
                metadata['stage'],
                metadata['source_filename'],
                metadata['stored_filename'],
                metadata['file_size'],
                metadata['sha256'],
                metadata['page_count'],
                metadata['pdf_type'],
                metadata['encrypted'],
                metadata['error_code']
            ))
    except Exception as e:
        logger.error(f"Failed to create job {metadata['job_id']}: {e}")
        
def get_job(config, job_id):
    try:
        with get_db_connection(config) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM processing_jobs WHERE id = ?', (job_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
    return None

def update_job_status(config, job_id, status, error_code=None, page_count=None):
    try:
        with get_db_connection(config) as conn:
            cursor = conn.cursor()
            
            if page_count is not None:
                cursor.execute('UPDATE processing_jobs SET status = ?, error_code = ?, page_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                               (status, error_code, page_count, job_id))
            else:
                cursor.execute('UPDATE processing_jobs SET status = ?, error_code = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                               (status, error_code, job_id))
    except Exception as e:
        logger.error(f"Failed to update job {job_id}: {e}")

def delete_job(config, job_id):
    try:
        with get_db_connection(config) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM processing_jobs WHERE id = ?', (job_id,))
    except Exception as e:
        logger.error(f"Failed to delete job {job_id}: {e}")
