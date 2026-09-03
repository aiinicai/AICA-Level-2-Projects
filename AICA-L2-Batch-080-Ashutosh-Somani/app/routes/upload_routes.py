from flask import Blueprint, request, current_app, jsonify, render_template, redirect, url_for, send_file, abort, flash
import os
from app.services.pdf_intake_service import process_uploaded_pdf, verify_pdf_password, get_job_pdf_path, cleanup_job
from app.services.job_state_service import create_job, get_job, update_job_status, delete_job
import logging

logger = logging.getLogger(__name__)
upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    config = current_app.config['APP_CONFIG']
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Unsupported file extension. Only PDF is allowed.'}), 400
        
    # Check size limit
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    file.seek(0, 0)
    
    max_mb = config.getint('upload', 'max_pdf_size_mb', fallback=100)
    if file_length > max_mb * 1024 * 1024:
        return jsonify({'error': f'File exceeds {max_mb} MB limit.'}), 400
        
    try:
        metadata = process_uploaded_pdf(file, config)
        create_job(config, metadata)
        
        return jsonify({
            'success': True,
            'job_id': metadata['job_id'],
            'redirect': url_for('upload.preview', job_id=metadata['job_id'])
        })
    except Exception as e:
        logger.error(f"Upload processing failed: {e}")
        return jsonify({'error': 'Failed to process upload.'}), 500

@upload_bp.route('/jobs/<job_id>/preview')
def preview(job_id):
    config = current_app.config['APP_CONFIG']
    job = get_job(config, job_id)
    
    if not job:
        abort(404, description="Job not found")
        
    return render_template('preview.html', job=job)

@upload_bp.route('/jobs/<job_id>/password', methods=['POST'])
def check_password(job_id):
    config = current_app.config['APP_CONFIG']
    password = request.form.get('password', '')
    
    job = get_job(config, job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
        
    if verify_pdf_password(job_id, password, config):
        import pypdf
        # Update job with page count now that we can read it
        try:
            path = get_job_pdf_path(job_id, config)
            reader = pypdf.PdfReader(path)
            update_job_status(config, job_id, 'ready_for_preview', page_count=len(reader.pages))
        except:
            pass # fallback, ignore error
            
        return redirect(url_for('upload.preview', job_id=job_id))
    else:
        flash('Incorrect password.', 'error')
        return redirect(url_for('upload.preview', job_id=job_id))

@upload_bp.route('/jobs/<job_id>/pdf')
def serve_pdf(job_id):
    config = current_app.config['APP_CONFIG']
    job = get_job(config, job_id)
    
    if not job:
        abort(404, description="Job not found")
        
    pdf_path = get_job_pdf_path(job_id, config)
    if not pdf_path or not pdf_path.exists():
        abort(404, description="PDF file not found")
        
    return send_file(pdf_path, mimetype='application/pdf', conditional=True)

@upload_bp.route('/jobs/<job_id>/delete', methods=['POST'])
def delete_job_route(job_id):
    config = current_app.config['APP_CONFIG']
    cleanup_job(job_id, config)
    delete_job(config, job_id)
    flash("Job cancelled and removed.", "success")
    return redirect(url_for('main.dashboard'))
