import json
import logging
from pathlib import Path
from flask import current_app

logger = logging.getLogger(__name__)

def get_progress_path(job_id, config=None):
    if config:
        if hasattr(config, 'get') and hasattr(config, 'read'):
            temp_dir_str = config.get('paths', 'temp', fallback='temp')
        elif hasattr(config, 'get') and 'APP_CONFIG' in config:
            temp_dir_str = config['APP_CONFIG'].get('paths', 'temp', fallback='temp')
        else:
            temp_dir_str = 'temp'
    else:
        temp_dir_str = config.get('paths', 'temp', fallback='temp') if config else 'temp'
    
    project_root = Path(__file__).resolve().parent.parent.parent
        
    job_dir = project_root / temp_dir_str / 'jobs' / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir / 'progress.json'

def init_progress(job_id, config, stage, total_pages=1, message=""):
    state = {
        "stage": stage,
        "percent": 0,
        "current_page": 0,
        "total_pages": total_pages,
        "message": message,
        "completed": False,
        "error": None
    }
    _save_progress(job_id, config, state)
    return state

def update_progress(job_id, config, percent, current_page=None, message=None, completed=False, error=None, result_data=None):
    state = get_progress(job_id, config)
    if not state:
        return
        
    if percent is not None:
        state["percent"] = percent
    if current_page is not None:
        state["current_page"] = current_page
    if message is not None:
        state["message"] = message
    if completed is not None:
        state["completed"] = completed
    if error is not None:
        state["error"] = error
        state["completed"] = True
    if result_data is not None:
        state["result_data"] = result_data
        
    _save_progress(job_id, config, state)
    return state

def complete_progress(job_id, config, message="Completed", result_data=None):
    return update_progress(job_id, config, percent=100, message=message, completed=True, result_data=result_data)

def error_progress(job_id, config, error_message):
    return update_progress(job_id, config, percent=100, error=error_message, completed=True)

def get_progress(job_id, config):
    try:
        path = get_progress_path(job_id, config)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error reading progress: {e}")
    return {
        "stage": "UNKNOWN",
        "percent": 0,
        "current_page": 0,
        "total_pages": 1,
        "message": "Initializing...",
        "completed": False,
        "error": None
    }

def _save_progress(job_id, config, state):
    try:
        path = get_progress_path(job_id, config)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving progress: {e}")
