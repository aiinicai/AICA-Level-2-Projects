from flask import Blueprint, request, jsonify, render_template, redirect, url_for, current_app, send_file, flash
import urllib.parse
from app.services.progress_service import init_progress
from app.routes.normalization_routes import norm_executor, _run_norm_bg
import os
import io
import json
from datetime import datetime
from app.services.normalization_service import run_normalization
from app.services.profile_manager import ProfileManager
from app.database.db import get_db_connection

profile_bp = Blueprint('profiles', __name__, url_prefix='/profiles')

def get_manager():
    return ProfileManager(current_app.config['APP_CONFIG'])

@profile_bp.route('/', methods=['GET'])
def profile_list():
    manager = get_manager()
    profiles = manager.list_profiles()
    return render_template('profiles.html', profiles=profiles)
    
@profile_bp.route('/<profile_id>/edit', methods=['GET'])
def profile_edit(profile_id):
    manager = get_manager()
    prof = manager.get_profile(profile_id)
    if not prof:
        return "Profile not found", 404
        
    job_id = request.args.get('job_id')
    return render_template('profile_edit.html', profile=prof, job_id=job_id)
    
@profile_bp.route('/api/list', methods=['GET'])
def api_list_profiles():
    manager = get_manager()
    profiles = [p.to_dict() for p in manager.list_profiles()]
    return jsonify({"status": "success", "profiles": profiles})
    
@profile_bp.route('/api/create', methods=['POST'])
def api_create_profile():
    data = request.json
    name = data.get('profile_name')
    bank = data.get('bank_name')
    
    if not name or not bank:
        return jsonify({"status": "error", "message": "Name and Bank are required"}), 400
        
    manager = get_manager()
    prof = manager.create_profile(name, bank)
    return jsonify({"status": "success", "profile": prof.to_dict()})

@profile_bp.route('/create_for_job/<job_id>', methods=['GET', 'POST'])
def create_for_job(job_id):
    if request.method == 'POST':
        name = request.form.get('profile_name')
        bank = request.form.get('bank_name')
        if name and bank:
            manager = get_manager()
            prof = manager.create_profile(name, bank)
            return redirect(url_for('profiles.profile_edit', profile_id=prof.profile_id, job_id=job_id))
        
    from flask import render_template_string
    template = '''{% extends "base.html" %}
{% block content %}
<div class="card">
    <h2>Create Profile From Statement</h2>
    <form method="POST" style="margin-top:20px; text-align:left;">
        <label style="display:block; margin-bottom:5px;">Profile Name:</label>
        <input type="text" name="profile_name" required style="width:100%; max-width:400px; padding:8px; margin-bottom:15px; border:1px solid var(--border-color); border-radius:4px;"><br>
        <label style="display:block; margin-bottom:5px;">Bank Name:</label>
        <input type="text" name="bank_name" required style="width:100%; max-width:400px; padding:8px; margin-bottom:15px; border:1px solid var(--border-color); border-radius:4px;"><br>
        <button type="submit" class="btn">Continue to Builder</button>
        <a href="{{ url_for('normalization.summary', job_id=job_id) }}" class="btn" style="background:var(--background-color); color:var(--text-color); margin-left:10px;">Cancel</a>
    </form>
</div>
{% endblock %}'''
    return render_template_string(template, job_id=job_id)

@profile_bp.route('/apply/<job_id>/<profile_id>', methods=['POST'])
def apply_profile(job_id, profile_id):
    config = current_app.config['APP_CONFIG']
    
    if current_app.config.get('TESTING'):
        from app.services.normalization_service import run_normalization
        success, error = run_normalization(job_id, config, force_profile_id=profile_id)
        if success:
            flash('Profile applied and statement normalized.', 'success')
            return redirect(url_for('normalization.summary', job_id=job_id))
        else:
            flash(f'Failed to apply profile: {error}', 'error')
            return redirect(url_for('normalization.summary', job_id=job_id))

    init_progress(job_id, config, stage="NORMALIZATION", message=f"Applying profile {profile_id}...")
    norm_executor.submit(_run_norm_bg, job_id, config, profile_id)
    
    next_url = urllib.parse.quote(url_for('normalization.summary', job_id=job_id))
    error_url = urllib.parse.quote(url_for('normalization.summary', job_id=job_id))
    return redirect(url_for('progress.progress_view', job_id=job_id, title='Applying Profile', next_url=next_url, error_url=error_url))

@profile_bp.route('/api/<profile_id>', methods=['GET'])
def api_get_profile(profile_id):
    manager = get_manager()
    prof = manager.get_profile(profile_id)
    if not prof:
        return jsonify({"status": "error", "message": "Not found"}), 404
    return jsonify({"status": "success", "profile": prof.to_dict()})

@profile_bp.route('/api/<profile_id>', methods=['PUT'])
def api_update_profile(profile_id):
    data = request.json
    manager = get_manager()
    prof = manager.get_profile(profile_id)
    if not prof:
        return jsonify({"status": "error", "message": "Not found"}), 404
        
    # Security: Don't allow overwriting ID
    from app.models.profile import BankProfile
    
    # Merge updates
    updated_prof_dict = prof.to_dict()
    for k, v in data.items():
        if k not in ['profile_id', 'created_at', 'updated_at', 'revision_number']:
            updated_prof_dict[k] = v
            
    try:
        new_prof = BankProfile.from_dict(updated_prof_dict)
        # Preserve original history
        new_prof.profile_id = prof.profile_id
        new_prof.created_at = prof.created_at
        new_prof.revision_number = prof.revision_number
        
        manager.save_profile(new_prof)
        return jsonify({"status": "success", "profile": new_prof.to_dict()})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@profile_bp.route('/api/<profile_id>/deactivate', methods=['POST'])
def api_deactivate_profile(profile_id):
    manager = get_manager()
    if manager.deactivate_profile(profile_id):
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@profile_bp.route('/api/<profile_id>/export', methods=['GET'])
def api_export_profile(profile_id):
    manager = get_manager()
    prof = manager.get_profile(profile_id)
    if not prof:
        return "Not found", 404
        
    # sanitize before export just in case
    prof_dict = prof.to_dict()
    # remove local SQLite index counts if we ever added them
    
    byte_str = json.dumps(prof_dict, indent=2).encode('utf-8')
    mem_file = io.BytesIO(byte_str)
    
    safe_name = "".join(c for c in prof.profile_name if c.isalnum() or c in " _-")
    
    return send_file(
        mem_file,
        mimetype="application/json",
        as_attachment=True,
        download_name=f"{safe_name}.json"
    )

@profile_bp.route('/api/preview', methods=['POST'])
def api_preview_extraction():
    data = request.json
    job_id = data.get('job_id')
    if not job_id:
        return jsonify({"status": "error", "message": "job_id is required"}), 400
        
    from app.services.extraction_service import get_extraction_result
    from app.models.profile import BankProfile
    from app.extractors.coordinate_extractor import CoordinateExtractor
    from app.services.transaction_normalizer import TransactionNormalizer
    from app.models.extraction_result import ExtractionResult, RawPage, RawWord, RawTableCandidate
    
    # 1. Load job artifact
    manager = get_manager()
    raw_dict = get_extraction_result(job_id, manager.config)
    if not raw_dict:
        return jsonify({"status": "error", "message": "Extraction artifact not found for job"}), 404
        
    # 2. Build temporary profile from request data
    # We do NOT save this profile.
    temp_prof = BankProfile.from_dict(data.get('profile_data', {}))
    
    # 3. Build ExtractionResult
    er = ExtractionResult(**{k: v for k, v in raw_dict.items() if k != 'pages'})
    er.pages = []
    for p in raw_dict.get('pages', []):
        rp = RawPage(**{k: v for k, v in p.items() if k not in ['words', 'table_candidates']})
        rp.words = [RawWord(**w) for w in p.get('words', [])]
        rp.table_candidates = [RawTableCandidate(**tc) for tc in p.get('table_candidates', [])]
        er.pages.append(rp)
        
    # 4. Extract based on layout
    coord_extractor = CoordinateExtractor(temp_prof)
    er = coord_extractor.extract(er)
    
    # Gather candidates
    table_candidates = []
    for page in er.pages:
        table_candidates.extend([tc.to_dict() if hasattr(tc, 'to_dict') else __import__('dataclasses').asdict(tc) for tc in page.table_candidates])
        
    # 5. Run normalizer
    if hasattr(manager.config, 'get') and hasattr(manager.config, 'read'):
        date_order = manager.config.get('normalization', 'default_date_order', fallback='DMY')
    elif hasattr(manager.config, 'get') and 'APP_CONFIG' in manager.config:
        date_order = manager.config['APP_CONFIG'].get('normalization', 'default_date_order', fallback='DMY')
    else:
        date_order = 'DMY'
        
    normalizer = TransactionNormalizer(default_date_order=date_order)
    transactions, warnings = normalizer.normalize(table_candidates)
    
    return jsonify({
        "status": "success", 
        "raw_rows": table_candidates[0]['cells'][:25] if table_candidates and table_candidates[0]['cells'] else [],
        "transactions": [t.to_dict() for t in transactions[:25]]
    })

@profile_bp.route('/api/import', methods=['POST'])
def api_import_profile():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file"}), 400
        
    file = request.files['file']
    if not file.filename.endswith('.json'):
        return jsonify({"status": "error", "message": "Must be JSON"}), 400
        
    try:
        data = json.load(file)
    except Exception:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400
        
    manager = get_manager()
    success, result = manager.import_profile(data)
    if success:
        return jsonify({"status": "success", "profile_id": result})
    else:
        return jsonify({"status": "error", "message": result}), 400
