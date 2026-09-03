import pytest
import configparser
import os
import tempfile
from pathlib import Path

from app import create_app
from app.database.migrations import init_db

@pytest.fixture
def temp_config(tmp_path):
    """Provides a temporary config for testing."""
    config = configparser.ConfigParser()
    config['application'] = {
        'host': '127.0.0.1',
        'port': '8765',
        'open_browser': 'false',
        'debug': 'true',
        'version': '0.1.0-test'
    }
    
    # Use temporary directories
    db_file = tmp_path / 'test_database.db'
    
    config['paths'] = {
        'output': str(tmp_path / 'output'),
        'logs': str(tmp_path / 'logs'),
        'temp': str(tmp_path / 'temp'),
        'profiles': str(tmp_path / 'profiles'),
        'database': str(db_file),
        'backups': str(tmp_path / 'backups')
    }
    
    config['privacy'] = {
        'allow_external_ai': 'false',
        'allow_cloud_ocr': 'false'
    }
    
    return config

@pytest.fixture
def app(temp_config):
    """Provides a test Flask application."""
    init_db(temp_config)
    app = create_app(temp_config)
    app.config.update({
        "TESTING": True,
    })
    yield app

@pytest.fixture
def client(app):
    """Provides a test client for the app."""
    return app.test_client()

import pypdf
import os
from pathlib import Path

@pytest.fixture
def sample_pdf(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with open(pdf_path, "wb") as fp:
        writer.write(fp)
    return str(pdf_path)

@pytest.fixture
def encrypted_pdf(tmp_path):
    pdf_path = tmp_path / "encrypted.pdf"
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.encrypt("secret")
    with open(pdf_path, "wb") as fp:
        writer.write(fp)
    return str(pdf_path)

@pytest.fixture
def non_pdf(tmp_path):
    txt_path = tmp_path / "fake.pdf"
    with open(txt_path, "w") as fp:
        fp.write("This is not a pdf file.")
    return str(txt_path)

@pytest.fixture
def fake_file_storage(sample_pdf):
    class FakeFileStorage:
        def __init__(self, path):
            self.path = path
            self.filename = "test_upload.pdf"
            
        def save(self, dest):
            import shutil
            shutil.copy(self.path, dest)
            
    return FakeFileStorage(sample_pdf)

@pytest.fixture
def fake_encrypted_storage(encrypted_pdf):
    class FakeFileStorage:
        def __init__(self, path):
            self.path = path
            self.filename = "encrypted.pdf"
            
        def save(self, dest):
            import shutil
            shutil.copy(self.path, dest)
            
    return FakeFileStorage(encrypted_pdf)

@pytest.fixture
def fake_invalid_storage(non_pdf):
    class FakeFileStorage:
        def __init__(self, path):
            self.path = path
            self.filename = "fake.pdf"
            
        def save(self, dest):
            import shutil
            shutil.copy(self.path, dest)
            
    return FakeFileStorage(non_pdf)
