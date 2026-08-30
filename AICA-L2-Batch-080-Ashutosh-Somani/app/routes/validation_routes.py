from flask import Blueprint, request, current_app, jsonify, render_template, redirect, url_for, abort, flash
from app.services.validation_service import ValidationService, get_validation_result
from app.services.job_state_service import get_job
import logging

logger = logging.getLogger(__name__)
validation_bp = Blueprint('validation', __name__)

@validation_bp.route('/jobs/<job_id>/validate', methods=['POST'])
def trigger_validation(job_id):
    config = current_app.config['APP_CONFIG']
    job = get_job(config, job_id)
    
    if not job:
        abort(404, description="Job not found")
        
    service = ValidationService(config)
    success, error = service.validate_job(job_id)
    
    if success:
        flash("Statement validation complete.", "success")
        return redirect(url_for('validation.summary', job_id=job_id))
    else:
        flash(f"Validation failed: {error}", "error")
        return redirect(url_for('normalization.summary', job_id=job_id))

@validation_bp.route('/jobs/<job_id>/validation')
def summary(job_id):
    config = current_app.config['APP_CONFIG']
    job = get_job(config, job_id)
    
    if not job:
        abort(404, description="Job not found")
        
    result = get_validation_result(job_id, config)
    if not result:
        flash("Validation result not found. Please run validation first.", "warning")
        return redirect(url_for('normalization.summary', job_id=job_id))
        
    return render_template('validation_summary.html', job=job, result=result)

@validation_bp.route('/jobs/<job_id>/exceptions')
def view_exceptions(job_id):
    config = current_app.config['APP_CONFIG']
    job = get_job(config, job_id)
    result = get_validation_result(job_id, config)
    
    if not job or not result:
        abort(404)
        
    page = int(request.args.get('page', 1))
    per_page = 50
    exceptions = result.get('exceptions', [])
    
    # Sort exceptions by severity priority
    severity_order = {"CRITICAL": 0, "ERROR": 1, "WARNING": 2, "INFO": 3}
    exceptions.sort(key=lambda x: severity_order.get(x.get('severity'), 4))
    
    total_pages = (len(exceptions) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    
    page_data = exceptions[start:end]
    
    return render_template('exceptions.html', 
                           job=job, 
                           exceptions=page_data,
                           current_page=page,
                           total_pages=total_pages,
                           total_count=len(exceptions),
                           transactions=result.get('transactions', []))
