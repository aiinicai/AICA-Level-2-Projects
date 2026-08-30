import logging
import threading
import json
from flask import Blueprint, jsonify, current_app
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from app.services.progress_service import init_progress, update_progress, complete_progress, error_progress

from app.services.ocr_service import OcrService
from app.models.extraction_result import ExtractionResult, RawPage, RawWord
from app.database.db import get_db_connection

logger = logging.getLogger(__name__)
ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')

# Simple thread pool
ocr_executor = ThreadPoolExecutor(max_workers=1)
ocr_jobs = {}
ocr_cancel_events = {}
ocr_job_locks = defaultdict(threading.Lock)


def _get_job_lock(job_id):
    """Return the per-job lock (creates one if absent)."""
    return ocr_job_locks[job_id]


def _reconstruct_extraction(raw_extraction_dict):
    """Rebuild ExtractionResult from a serialized dict."""
    pages = []
    for p in raw_extraction_dict.get('pages', []):
        words = [RawWord(**w) for w in p.get('words', [])]
        p_copy = p.copy()
        if 'words' in p_copy: del p_copy['words']
        if 'table_candidates' in p_copy: del p_copy['table_candidates']
        pages.append(RawPage(words=words, **p_copy))

    ext_copy = raw_extraction_dict.copy()
    if 'pages' in ext_copy: del ext_copy['pages']
    return ExtractionResult(pages=pages, **ext_copy)


def _run_ocr_background(config, job_id, raw_extraction_dict, force_pages=None):
    lock = _get_job_lock(job_id)
    try:
        with lock:
            ocr_jobs[job_id] = "OCR_RUNNING"
            cancel_event = threading.Event()
            ocr_cancel_events[job_id] = cancel_event

        # update db
        with get_db_connection(config) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE processing_jobs SET ocr_status = 'OCR_RUNNING' WHERE id = ?", (job_id,))
            conn.commit()

        extraction = _reconstruct_extraction(raw_extraction_dict)
        update_progress(job_id, config, percent=10, message="Preparing OCR...")

        svc = OcrService(config)
        status = svc.run_ocr(job_id, extraction, force_pages=force_pages, cancel_event=cancel_event)
        complete_progress(job_id, config, "Local OCR completed.")

        with lock:
            ocr_jobs[job_id] = status

        with get_db_connection(config) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE processing_jobs SET ocr_status = ? WHERE id = ?", (status, job_id))
            conn.commit()

    except Exception as e:
        logger.error(f"OCR background task failed for {job_id}: {e}")
        error_progress(job_id, config, f"OCR failed: {e}")
        with lock:
            ocr_jobs[job_id] = "OCR_FAILED"
        with get_db_connection(config) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE processing_jobs SET ocr_status = 'OCR_FAILED' WHERE id = ?", (job_id,))
            conn.commit()
    finally:
        with lock:
            ocr_cancel_events.pop(job_id, None)


@ocr_bp.route('/<job_id>/trigger', methods=['POST'])
def trigger_ocr(job_id):
    config = current_app.config['APP_CONFIG']

    lock = _get_job_lock(job_id)
    with lock:
        # Check if already running
        if ocr_jobs.get(job_id) == "OCR_RUNNING":
            return jsonify({"status": "error", "message": "OCR_ALREADY_RUNNING"}), 400

    temp_dir = Path(config.get('paths', 'temp', fallback='temp'))
    project_root = Path(current_app.root_path).parent
    raw_ext_path = project_root / temp_dir / 'jobs' / job_id / 'extraction' / 'raw_extraction.json'

    if not raw_ext_path.exists():
        return jsonify({"status": "error", "message": "Job not found or digital extraction missing"}), 404

    with open(raw_ext_path, 'r', encoding='utf-8') as f:
        raw_extraction_dict = json.load(f)

    init_progress(job_id, config, stage="OCR", message="Queuing local OCR...")
    ocr_executor.submit(_run_ocr_background, config, job_id, raw_extraction_dict)

    return jsonify({"status": "success", "message": "OCR started", "job_id": job_id})


@ocr_bp.route('/<job_id>/status', methods=['GET'])
def ocr_status(job_id):
    lock = _get_job_lock(job_id)
    with lock:
        status = ocr_jobs.get(job_id, "OCR_PENDING")

    # Check DB if not in memory (server restart)
    if status == "OCR_PENDING":
        config = current_app.config['APP_CONFIG']
        with get_db_connection(config) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ocr_status FROM processing_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if row and row[0]:
                status = row[0]
                if status == "OCR_RUNNING":
                    # Stale from crash
                    status = "OCR_INTERRUPTED"
                    cursor.execute("UPDATE processing_jobs SET ocr_status = 'OCR_INTERRUPTED' WHERE id = ?", (job_id,))
                    conn.commit()

    return jsonify({"job_id": job_id, "ocr_status": status})


@ocr_bp.route('/<job_id>/cancel', methods=['POST'])
def cancel_ocr(job_id):
    """Cooperatively cancel a running OCR job."""
    lock = _get_job_lock(job_id)
    with lock:
        cancel_event = ocr_cancel_events.get(job_id)
        current_status = ocr_jobs.get(job_id)

    if current_status != "OCR_RUNNING":
        return jsonify({"job_id": job_id, "status": "error", "message": "OCR not currently running"}), 400

    if cancel_event:
        cancel_event.set()
        return jsonify({"job_id": job_id, "status": "OCR_CANCEL_REQUESTED"})
    else:
        return jsonify({"job_id": job_id, "status": "error", "message": "No cancel event found"}), 500


@ocr_bp.route('/<job_id>/retry-failed', methods=['POST'])
def retry_failed_pages(job_id):
    """Re-run OCR only on previously failed pages."""
    config = current_app.config['APP_CONFIG']

    lock = _get_job_lock(job_id)
    with lock:
        current_status = ocr_jobs.get(job_id)

    if current_status == "OCR_RUNNING":
        return jsonify({"status": "error", "message": "OCR currently running"}), 400

    # Load previous OCR result to find failed pages
    temp_dir = config.get('paths', 'temp', fallback='temp')
    ocr_result_path = Path(temp_dir) / 'jobs' / job_id / 'ocr' / 'ocr_result.json'
    if not ocr_result_path.exists():
        return jsonify({"status": "error", "message": "No previous OCR result found"}), 404

    with open(ocr_result_path, 'r', encoding='utf-8') as f:
        ocr_result = json.load(f)

    failed_pages = []
    for page in ocr_result.get('pages', []):
        if page.get('source_type') == 'OCR_FAILED':
            failed_pages.append(page['page_number'])

    if not failed_pages:
        return jsonify({"job_id": job_id, "status": "OCR_COMPLETE", "message": "No failed pages to retry"}), 200

    # Load raw extraction for reconstruction
    temp_dir = Path(config.get('paths', 'temp', fallback='temp'))
    project_root = Path(current_app.root_path).parent
    raw_ext_path = project_root / temp_dir / 'jobs' / job_id / 'extraction' / 'raw_extraction.json'
    if not raw_ext_path.exists():
        return jsonify({"status": "error", "message": "Raw extraction missing"}), 404

    with open(raw_ext_path, 'r', encoding='utf-8') as f:
        raw_extraction_dict = json.load(f)

    ocr_executor.submit(_run_ocr_background, config, job_id, raw_extraction_dict, force_pages=failed_pages)

    return jsonify({"job_id": job_id, "status": "OCR_RETRY_STARTED", "failed_pages": failed_pages})
