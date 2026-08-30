import os
import sys
import platform
import zipfile
import datetime
from pathlib import Path
from flask import Blueprint, render_template, current_app, request, jsonify, send_file

diagnostics_bp = Blueprint('diagnostics', __name__)

@diagnostics_bp.route('/diagnostics')
def index():
    config = current_app.config['APP_CONFIG']
    
    # Gather basic stats safely
    stats = {
        'version': config.get('application', 'version', fallback='Unknown'),
        'python_version': sys.version.split(' ')[0],
        'platform': platform.system() + " " + platform.release(),
        'app_root': str(Path(__file__).parent.parent.parent.resolve()),
        'host': config.get('application', 'host', fallback='127.0.0.1'),
        'port': config.get('application', 'port', fallback='8080'),
        'privacy_ai': config.getboolean('privacy', 'allow_external_ai', fallback=False),
        'privacy_cloud_ocr': config.getboolean('privacy', 'allow_cloud_ocr', fallback=False),
    }

    # DB Check
    db_path = Path(config.get('paths', 'database', fallback='data/bank_converter.db'))
    stats['db_status'] = "OK" if db_path.exists() else "Missing"
    
    # Folders Check
    paths = ['output', 'temp', 'logs', 'profiles', 'backups']
    folder_stats = {}
    for p in paths:
        folder_path = Path(config.get('paths', p, fallback=p))
        if folder_path.exists():
            folder_stats[p] = "OK"
        else:
            folder_stats[p] = "Missing"
    stats['folders'] = folder_stats
    
    # OCR Check
    ocr_ready = "Disabled"
    if config.getboolean('ocr', 'enabled', fallback=True):
        try:
            from rapidocr_onnxruntime import RapidOCR
            ocr_ready = "Ready (rapidocr-onnxruntime)"
        except ImportError:
            ocr_ready = "Missing Engine"
    stats['ocr_status'] = ocr_ready

    # Export Check
    try:
        import openpyxl
        stats['excel_status'] = "Ready"
    except ImportError:
        stats['excel_status'] = "Missing openpyxl"

    # Profile count
    from app.database.db import get_db_connection
    try:
        with get_db_connection(config) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM profiles")
            stats['profile_count'] = cur.fetchone()[0]
    except Exception:
        stats['profile_count'] = "Error"

    return render_template('diagnostics.html', stats=stats)

@diagnostics_bp.route('/diagnostics/run_check', methods=['POST'])
def run_check():
    config = current_app.config['APP_CONFIG']
    results = []
    
    # 1. Config Check
    results.append({"name": "Configuration", "status": "PASS", "message": "config.ini readable"})
    
    # 2. SQLite Accessible
    try:
        from app.database.db import get_db_connection
        with get_db_connection(config) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_versions'")
            if cur.fetchone():
                results.append({"name": "Database Schema", "status": "PASS", "message": "SQLite accessible and migrated"})
            else:
                results.append({"name": "Database Schema", "status": "FAIL", "message": "Schema missing"})
    except Exception as e:
        results.append({"name": "Database Schema", "status": "FAIL", "message": str(e)})

    # 3. Temp write/delete probe
    temp_dir = Path(config.get('paths', 'temp', fallback='temp'))
    try:
        temp_dir.mkdir(exist_ok=True)
        probe = temp_dir / 'probe.txt'
        probe.write_text('test')
        probe.unlink()
        results.append({"name": "Temp Directory", "status": "PASS", "message": "Writable"})
    except Exception as e:
        results.append({"name": "Temp Directory", "status": "FAIL", "message": str(e)})

    # 4. Modules
    modules = {'pdfplumber': 'PDF Extraction', 'openpyxl': 'Excel Export', 'pypdfium2': 'PDF Rendering'}
    for mod, desc in modules.items():
        try:
            __import__(mod)
            results.append({"name": f"{desc} Module", "status": "PASS", "message": f"{mod} installed"})
        except ImportError:
            results.append({"name": f"{desc} Module", "status": "FAIL", "message": f"{mod} missing"})

    return jsonify({"results": results})

@diagnostics_bp.route('/diagnostics/backup', methods=['POST'])
def create_backup():
    config = current_app.config['APP_CONFIG']
    backups_dir = Path(config.get('paths', 'backups', fallback='data/backups'))
    backups_dir.mkdir(exist_ok=True, parents=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"BankConverter_Backup_{timestamp}.zip"
    zip_path = backups_dir / zip_name
    
    # Files to backup
    db_path = Path(config.get('paths', 'database', fallback='data/bank_converter.db'))
    config_path = Path('config.ini')
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        if config_path.exists():
            zf.write(config_path, arcname='config.ini')
        if db_path.exists():
            zf.write(db_path, arcname='bank_converter.db')
        
        # Manifest
        manifest = f"version={config.get('application', 'version', fallback='Unknown')}\n"
        manifest += f"timestamp={timestamp}\n"
        zf.writestr('manifest.txt', manifest)
        
    return jsonify({"status": "success", "file": zip_name, "message": f"Backup created: {zip_name}"})

@diagnostics_bp.route('/diagnostics/restore', methods=['POST'])
def restore_backup():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400
        
    file = request.files['file']
    if not file.filename.endswith('.zip'):
        return jsonify({"status": "error", "message": "Must be a ZIP file"}), 400

    config = current_app.config['APP_CONFIG']
    temp_dir = Path(config.get('paths', 'temp', fallback='temp'))
    temp_dir.mkdir(exist_ok=True, parents=True)
    restore_zip = temp_dir / 'restore.zip'
    file.save(restore_zip)
    
    try:
        with zipfile.ZipFile(restore_zip, 'r') as zf:
            # Zip slip protection
            for name in zf.namelist():
                if name.startswith('/') or name.startswith('..') or '..' in name:
                    return jsonify({"status": "error", "message": "Invalid ZIP archive (Path Traversal attempt detected)"}), 400
                if name not in ['config.ini', 'bank_converter.db', 'manifest.txt']:
                    return jsonify({"status": "error", "message": f"Invalid file in archive: {name}"}), 400
            
            # Require manifest
            if 'manifest.txt' not in zf.namelist():
                return jsonify({"status": "error", "message": "Invalid backup (missing manifest.txt)"}), 400

            # Safe to restore! First, backup current
            backups_dir = Path(config.get('paths', 'backups', fallback='data/backups'))
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_restore_zip = backups_dir / f"PreRestore_Backup_{timestamp}.zip"
            
            db_path = Path(config.get('paths', 'database', fallback='data/bank_converter.db'))
            config_path = Path('config.ini')
            
            with zipfile.ZipFile(pre_restore_zip, 'w', zipfile.ZIP_DEFLATED) as pzf:
                if config_path.exists(): pzf.write(config_path, arcname='config.ini')
                if db_path.exists(): pzf.write(db_path, arcname='bank_converter.db')
                pzf.writestr('manifest.txt', f"type=pre-restore\ntimestamp={timestamp}")

            # Now restore
            if 'config.ini' in zf.namelist():
                zf.extract('config.ini', path='.')
            if 'bank_converter.db' in zf.namelist():
                # Make sure parent dirs exist for DB
                db_path.parent.mkdir(exist_ok=True, parents=True)
                # extract directly to the parent folder
                zf.extract('bank_converter.db', path=str(db_path.parent))
                
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if restore_zip.exists():
            restore_zip.unlink()

    return jsonify({"status": "success", "message": "Restore completed successfully. A pre-restore backup was created."})
