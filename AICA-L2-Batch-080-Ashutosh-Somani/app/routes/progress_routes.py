from flask import Blueprint, jsonify, current_app, render_template, request
from app.services.progress_service import get_progress

progress_bp = Blueprint('progress', __name__)

@progress_bp.route('/jobs/<job_id>/progress', methods=['GET'])
def get_job_progress(job_id):
    config = current_app.config.get('APP_CONFIG')
    if not config:
        config = current_app.config
    state = get_progress(job_id, config)
    return jsonify(state)

@progress_bp.route('/jobs/<job_id>/progress_view', methods=['GET'])
def progress_view(job_id):
    title = request.args.get('title', 'Processing...')
    next_url = request.args.get('next_url', '/')
    error_url = request.args.get('error_url', '/')
    
    return render_template('progress.html', 
                           job_id=job_id, 
                           title=title,
                           next_url=next_url,
                           error_url=error_url)
