import logging
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from pathlib import Path
import configparser
import queue
import atexit

_listener = None
_logging_initialized = False

def setup_logging(config: configparser.ConfigParser):
    global _listener, _logging_initialized
    
    if _logging_initialized:
        return
        
    log_dir_str = config.get('paths', 'logs', fallback='logs')
    project_root = Path(__file__).resolve().parent.parent.parent
    p_dir = Path(log_dir_str)
    log_dir = p_dir if p_dir.is_absolute() else project_root / p_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / 'application.log'
    
    debug = config.getboolean('application', 'debug', fallback=False)
    log_level = logging.DEBUG if debug else logging.INFO
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    # Base handlers that actually write
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers if any
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # Set up Queue logging
    log_queue = queue.Queue(-1)
    queue_handler = QueueHandler(log_queue)
    root_logger.addHandler(queue_handler)
    
    # Set up listener to write from queue to actual handlers
    _listener = QueueListener(log_queue, file_handler, console_handler, respect_handler_level=True)
    _listener.start()
    
    # Register shutdown
    atexit.register(stop_logging)
    
    # Silence third-party noisy loggers
    noisy_loggers = [
        'pdfminer', 
        'pdfplumber', 
        'pypdf', 
        'PIL', 
        'urllib3', 
        'werkzeug', 
        'onnxruntime', 
        'rapidocr'
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
        
    _logging_initialized = True

def stop_logging():
    global _listener
    if _listener is not None:
        _listener.stop()
        _listener = None
