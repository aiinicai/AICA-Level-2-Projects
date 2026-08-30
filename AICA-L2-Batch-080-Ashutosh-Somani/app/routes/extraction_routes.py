from flask import Blueprint, request, current_app, jsonify, render_template, redirect, url_for, abort, flash
from app.services.extraction_service import run_extraction, get_extraction_result
from app.services.job_state_service import get_job
import logging

logger = logging.getLogger(__name__)

import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from app.services.progress_service import init_progress, complete_progress, error_progress

extract_executor = ThreadPoolExecutor(max_workers=1)

def _run_extract_bg(job_id, config):
    try:
        from app.services.extraction_service import run_extraction
        # Flask current_app proxy cannot be used outside app context directly.
        success, error = run_extraction(job_id, config)
        if success:
            complete_progress(job_id, config, "Extraction complete")
        else:
            error_progress(job_id, config, f"Extraction failed: {error}")
    except Exception as e:
        error_progress(job_id, config, f"Extraction failed: {str(e)}")

extraction_bp = Blueprint('extraction', __name__)

@extraction_bp.route('/jobs/<job_id>/extract', methods=['POST'])
def trigger_extraction(job_id):
    config = current_app.config['APP_CONFIG']
    job = get_job(config, job_id)
    
    if not job:
        abort(404, description="Job not found")
        
    if current_app.config.get('TESTING'):
        success, error = run_extraction(job_id, config)
        if success:
            flash("Digital extraction complete.", "success")
            return redirect(url_for('extraction.diagnostics', job_id=job_id))
        else:
            flash(f"Extraction failed: {error}", "error")
            return redirect(url_for('upload.preview', job_id=job_id))

    init_progress(job_id, config, stage="DIGITAL_EXTRACTION", total_pages=job.get('page_count', 1) if isinstance(job, dict) else getattr(job, 'page_count', 1), message="Starting digital analysis...")
    
    # We must not pass current_app directly; we pass config.
    extract_executor.submit(_run_extract_bg, job_id, config)
    
    next_url = urllib.parse.quote(url_for('extraction.diagnostics', job_id=job_id))
    error_url = urllib.parse.quote(url_for('upload.preview', job_id=job_id))
    
    return redirect(url_for('progress.progress_view', job_id=job_id, title='Analyzing Digital PDF', next_url=next_url, error_url=error_url))

@extraction_bp.route('/jobs/<job_id>/diagnostics')
def diagnostics(job_id):
    config = current_app.config['APP_CONFIG']
    job = get_job(config, job_id)
    
    if not job:
        abort(404, description="Job not found")
        
    result = get_extraction_result(job_id, config)
    if not result:
        flash("Extraction result not found. Please run extraction first.", "warning")
        return redirect(url_for('upload.preview', job_id=job_id))
        
    from app.services.ocr_eligibility_service import OcrEligibilityService
    from app.models.extraction_result import ExtractionResult, RawPage, RawWord
    
    pages = []
    for p in result.get('pages', []):
        words = [RawWord(**w) for w in p.get('words', [])]
        p_copy = p.copy()
        if 'words' in p_copy: del p_copy['words']
        if 'table_candidates' in p_copy: del p_copy['table_candidates']
        pages.append(RawPage(words=words, **p_copy))
        
    ext_copy = result.copy()
    if 'pages' in ext_copy: del ext_copy['pages']
    ext_obj = ExtractionResult(pages=pages, **ext_copy)
    
    eligibility_svc = OcrEligibilityService(config)
    ocr_assessment = eligibility_svc.assess_job(ext_obj)
        
    return render_template('extraction_diagnostics.html', job=job, result=result, ocr_assessment=ocr_assessment)

@extraction_bp.route('/jobs/<job_id>/diagnostics/raw_text')
def diagnostic_raw_text(job_id):
    config = current_app.config['APP_CONFIG']
    job = get_job(config, job_id)
    result = get_extraction_result(job_id, config)
    
    if not job or not result:
        abort(404)
        
    return render_template('diagnostic_raw_text.html', job=job, result=result)

@extraction_bp.route('/jobs/<job_id>/diagnostics/geometry')
def diagnostic_geometry(job_id):
    config = current_app.config['APP_CONFIG']
    job = get_job(config, job_id)
    result = get_extraction_result(job_id, config)
    
    if not job or not result:
        abort(404)
        
    page = int(request.args.get('page', 1))
    
    # Ensure page is within bounds
    if page < 1 or (result['pages'] and page > len(result['pages'])):
        page = 1
        
    page_data = next((p for p in result['pages'] if p['page_number'] == page), None)
    
    return render_template('diagnostic_geometry.html', job=job, result=result, current_page=page, page_data=page_data)

@extraction_bp.route('/jobs/<job_id>/diagnostics/tables')
def diagnostic_tables(job_id):
    config = current_app.config['APP_CONFIG']
    job = get_job(config, job_id)
    result = get_extraction_result(job_id, config)
    
    if not job or not result:
        abort(404)
        
    return render_template('diagnostic_tables.html', job=job, result=result)
