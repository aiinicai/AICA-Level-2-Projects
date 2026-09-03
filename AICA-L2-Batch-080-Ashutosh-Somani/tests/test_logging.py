import pytest
import logging
import threading
import queue
from app.utils.logging_utils import setup_logging
import configparser
from pathlib import Path
import time
import os

@pytest.fixture(autouse=True)
def reset_logging():
    import app.utils.logging_utils
    # Reset before each test
    if app.utils.logging_utils._listener:
        app.utils.logging_utils.stop_logging()
    app.utils.logging_utils._logging_initialized = False
    
    # Store old root handlers
    root_logger = logging.getLogger()
    old_handlers = root_logger.handlers[:]
    
    yield
    
    # Cleanup
    if app.utils.logging_utils._listener:
        app.utils.logging_utils.stop_logging()
    app.utils.logging_utils._logging_initialized = False
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    for h in old_handlers:
        root_logger.addHandler(h)

def test_idempotent_logging(tmp_path):
    config = configparser.ConfigParser()
    config.add_section('paths')
    config.set('paths', 'logs', str(tmp_path))
    config.add_section('application')
    config.set('application', 'debug', 'false')
    
    setup_logging(config)
    setup_logging(config)  # Call twice
    
    root_logger = logging.getLogger()
    # Should only have ONE QueueHandler
    handlers = root_logger.handlers
    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.handlers.QueueHandler)

def test_logging_multithreaded_rotation(tmp_path):
    config = configparser.ConfigParser()
    config.add_section('paths')
    config.set('paths', 'logs', str(tmp_path))
    config.add_section('application')
    config.set('application', 'debug', 'false')
    
    setup_logging(config)
    
    # Force small rotation size on the file handler directly for testing
    import app.utils.logging_utils
    file_handler = None
    for h in app.utils.logging_utils._listener.handlers:
        if isinstance(h, logging.handlers.RotatingFileHandler):
            file_handler = h
            break
            
    assert file_handler
    # Small size to trigger fast rotation
    file_handler.maxBytes = 1000
    file_handler.backupCount = 3
    
    logger = logging.getLogger('test_threads')
    
    def worker():
        for i in range(100):
            logger.info("A" * 50)
            
    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    time.sleep(0.5)  # Let queue process
    
    # Verify rotation happened without WinError 32
    log_files = list(tmp_path.glob('application.log*'))
    assert len(log_files) > 1

def test_pdfminer_logging_suppressed(tmp_path, monkeypatch):
    config = configparser.ConfigParser()
    config.add_section('paths')
    config.set('paths', 'logs', str(tmp_path))
    config.add_section('application')
    config.set('application', 'debug', 'false')
    
    setup_logging(config)
    
    pdfminer_logger = logging.getLogger('pdfminer.psparser')
    assert pdfminer_logger.level == logging.WARNING or logging.getLogger('pdfminer').level == logging.WARNING
