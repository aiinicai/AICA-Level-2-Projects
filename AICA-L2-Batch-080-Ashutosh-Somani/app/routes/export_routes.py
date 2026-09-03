from flask import Blueprint, jsonify, request, send_file, current_app
from pathlib import Path
from app.services.export_service import ExportService

import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from app.services.progress_service import init_progress, complete_progress, error_progress
from flask import url_for

export_executor = ThreadPoolExecutor(max_workers=1)

def _run_export_bg(job_id, config):
    try:
        def _progress(percent, msg):
            from app.services.progress_service import update_progress
            update_progress(job_id, config, percent, message=msg)

        svc = ExportService(config)
        filepath = svc.export_excel(job_id, progress_callback=_progress)
        download_url = f"/api/export/download/{filepath.name}"
        complete_progress(job_id, config, "Export complete", result_data={"download_url": download_url})
    except Exception as e:
        error_progress(job_id, config, f"Export failed: {str(e)}")

import os

export_bp = Blueprint('export', __name__, url_prefix='/api/export')

@export_bp.route('/<job_id>', methods=['POST'])
def export_job(job_id):
    try:
        config = current_app.config['APP_CONFIG']
        
        init_progress(job_id, config, stage="EXPORT", message="Generating Excel file...")
        export_executor.submit(_run_export_bg, job_id, config)
        
        next_url = urllib.parse.quote(url_for('main.dashboard'))
        error_url = urllib.parse.quote(url_for('main.dashboard'))
        progress_url = f"/jobs/{job_id}/progress_view?title=Exporting%20Statement&next_url={next_url}&error_url={error_url}"
        
        return jsonify({
            "status": "processing",
            "progress_url": progress_url
        })
    except Exception as e:
        current_app.logger.error(f"Export failed for {job_id}: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to generate export."}), 500

@export_bp.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    config = current_app.config['APP_CONFIG']
    output_dir = Path(config.get('paths', 'output')).resolve()
    
    # Path traversal protection via resolve
    filepath = (output_dir / filename).resolve()
    try:
        filepath.relative_to(output_dir)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid filename"}), 400
    
    if not filepath.exists():
        return jsonify({"status": "error", "message": "File not found"}), 404
        
    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
