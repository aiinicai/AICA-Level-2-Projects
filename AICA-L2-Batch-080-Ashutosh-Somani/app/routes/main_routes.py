from flask import Blueprint, render_template, current_app, request, flash, redirect, url_for
from app.services.job_state_service import get_recent_jobs

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def dashboard():
    config = current_app.config['APP_CONFIG']
    version = config.get('application', 'version', fallback='0.2.0')
    
    # System Status
    status = {
        'Application': 'Ready',
        'Local processing': 'Enabled',
        'External AI': 'Disabled',
        'Cloud OCR': 'Disabled',
        'Database': 'Ready',
        'Version': version
    }
    
    jobs = get_recent_jobs(config)
    
    return render_template('dashboard.html', status=status, jobs=jobs)

@main_bp.route('/process', methods=['GET', 'POST'])
def process():
    return render_template('base.html', 
                           error_title="Planned for later stage", 
                           error_msg="Batch processing and workflow extraction will be implemented in a future stage.")


