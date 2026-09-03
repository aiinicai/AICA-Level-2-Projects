from flask import Blueprint, request, current_app, jsonify, render_template, redirect, url_for, abort, flash
from app.services.normalization_service import run_normalization, get_normalization_result
from app.services.job_state_service import get_job
import logging

logger = logging.getLogger(__name__)

import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from app.services.progress_service import init_progress, complete_progress, error_progress

norm_executor = ThreadPoolExecutor(max_workers=1)

def _run_norm_bg(job_id, config, force_profile_id=None):
    try:
        from app.services.normalization_service import run_normalization
        success, error = run_normalization(job_id, config, force_profile_id=force_profile_id)
        if success:
            complete_progress(job_id, config, "Normalization complete")
        else:
            error_progress(job_id, config, f"Normalization failed: {error}")
    except Exception as e:
        error_progress(job_id, config, f"Normalization failed: {str(e)}")

normalization_bp = Blueprint('normalization', __name__)

@normalization_bp.route('/jobs/<job_id>/normalize', methods=['POST'])
def trigger_normalization(job_id):
    config = current_app.config['APP_CONFIG']
    job = get_job(config, job_id)
    
    if not job:
        abort(404, description="Job not found")
        
    force_profile_id = request.args.get('profile_id')
    
    if current_app.config.get('TESTING'):
        from app.services.normalization_service import run_normalization
        success, error = run_normalization(job_id, config, force_profile_id=force_profile_id)
        if success:
            flash("Statement normalization complete.", "success")
            return redirect(url_for('normalization.summary', job_id=job_id))
        else:
            flash(f"Normalization failed: {error}", "error")
            return redirect(url_for('extraction.diagnostics', job_id=job_id))

    init_progress(job_id, config, stage="NORMALIZATION", total_pages=job.get('page_count', 1) if isinstance(job, dict) else getattr(job, 'page_count', 1), message="Detecting bank and applying profile...")
    norm_executor.submit(_run_norm_bg, job_id, config, force_profile_id)
    
    next_url = urllib.parse.quote(url_for('normalization.summary', job_id=job_id))
    error_url = urllib.parse.quote(url_for('extraction.diagnostics', job_id=job_id))
    return redirect(url_for('progress.progress_view', job_id=job_id, title='Detect Bank & Normalize', next_url=next_url, error_url=error_url))

@normalization_bp.route('/jobs/<job_id>/normalization')
def summary(job_id):
    config = current_app.config['APP_CONFIG']
    job = get_job(config, job_id)
    
    if not job:
        abort(404, description="Job not found")
        
    result = get_normalization_result(job_id, config)
    if not result:
        flash("Normalization result not found. Please run normalization first.", "warning")
        return redirect(url_for('extraction.diagnostics', job_id=job_id))
        
    return render_template('normalization_summary.html', job=job, result=result)

@normalization_bp.route('/jobs/<job_id>/transactions')
def preview_transactions(job_id):
    config = current_app.config['APP_CONFIG']
    job = get_job(config, job_id)
    result = get_normalization_result(job_id, config)
    
    if not job or not result:
        abort(404)
        
    page = int(request.args.get('page', 1))
    per_page = 50
    transactions = result.get('transactions', [])
    
    total_pages = (len(transactions) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    
    page_data = transactions[start:end]
    
    return render_template('normalized_transactions.html', 
                           job=job, 
                           transactions=page_data,
                           current_page=page,
                           total_pages=total_pages,
                           total_count=len(transactions))
