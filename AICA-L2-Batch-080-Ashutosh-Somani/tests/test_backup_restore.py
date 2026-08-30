import os
import sys
import tempfile
import zipfile
import json
from pathlib import Path
import pytest
from app.routes.diagnostics_routes import diagnostics_bp

def test_backup_creation(app, client, tmp_path):
    # Mock config
    config = app.config['APP_CONFIG']
    config.set('paths', 'backups', str(tmp_path / 'backups'))
    config.set('paths', 'database', str(tmp_path / 'fake_db.sqlite'))
    
    # Create fake db and config
    (tmp_path / 'fake_db.sqlite').write_text("fake db content")
    
    # Temporarily create a config.ini in the root for backup testing
    original_cwd = os.getcwd()
    os.chdir(str(tmp_path))
    Path('config.ini').write_text("fake config content")
    
    try:
        response = client.post('/diagnostics/backup')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['file'].endswith('.zip')
        
        # Verify ZIP contents
        zip_path = tmp_path / 'backups' / data['file']
        assert zip_path.exists()
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            files = zf.namelist()
            assert 'config.ini' in files
            assert 'bank_converter.db' in files
            assert 'manifest.txt' in files
            
            manifest = zf.read('manifest.txt').decode()
            assert 'timestamp=' in manifest
    finally:
        os.chdir(original_cwd)

def test_restore_zip_slip_protection(app, client, tmp_path):
    # Create malicious ZIP
    zip_path = tmp_path / 'malicious.zip'
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr('../../../evil.txt', 'evil content')
        zf.writestr('manifest.txt', 'fake manifest')
        
    with open(zip_path, 'rb') as f:
        response = client.post('/diagnostics/restore', data={'file': (f, 'malicious.zip')})
        
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'Path Traversal' in data['message']
