import pytest
import os
from pathlib import Path
from flask import Flask
from app.routes.export_routes import export_bp

@pytest.fixture
def test_app(tmp_path):
    app = Flask(__name__)
    app.register_blueprint(export_bp)
    
    # Mock config
    app.config['APP_CONFIG'] = type('MockConfig', (), {
        'get': lambda self, sec, key, fallback=None: str(tmp_path) if sec == 'paths' and key == 'output' else fallback
    })()
    
    return app

def test_download_file_path_traversal(test_app, client):
    # Setup client
    test_client = test_app.test_client()
    
    # Try directory traversal
    response = test_client.get('/api/export/download/../config.ini')
    assert response.status_code == 404
    
    response2 = test_client.get('/api/export/download/valid_file.xlsx')
    assert response2.status_code == 404
