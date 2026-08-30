import os
import sys
import hashlib
import subprocess
import shutil
import logging
import threading
import time
import webbrowser
import socket
from pathlib import Path

VERSION = "1.0.1"

def _hash_requirements(req_path):
    if not os.path.exists(req_path):
        return None
    with open(req_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def ensure_dependencies():
    req_path = Path('requirements.txt')
    hash_path = Path('.venv/requirements.hash')
    
    current_hash = _hash_requirements(req_path)
    if not current_hash:
        print("[ERROR] requirements.txt not found!")
        sys.exit(1)
        
    last_hash = None
    if hash_path.exists():
        with open(hash_path, 'r') as f:
            last_hash = f.read().strip()
            
    if current_hash != last_hash:
        print("\n[INFO] Dependencies changed or not installed. Installing...")
        try:
            # We must use the current venv python
            python_exe = sys.executable
            result = subprocess.run([python_exe, '-m', 'pip', 'install', '-r', str(req_path)],
                                    check=True, capture_output=True, text=True)
            print("[OK] Dependencies installed successfully.")
            # Write hash
            with open(hash_path, 'w') as f:
                f.write(current_hash)
        except subprocess.CalledProcessError as e:
            print("\n[ERROR] Failed to install dependencies.")
            print(f"Likely network issue. Command output:\n{e.stderr}")
            print("\nPlease check your internet connection and try again.")
            sys.exit(1)
    else:
        print("[OK] Dependencies are up to date.")

def check_single_instance(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        s.close()
        return False # Port is free, we are the only instance
    except OSError:
        # Port is taken
        import urllib.request
        from urllib.error import URLError
        try:
            url = f"http://{host}:{port}/"
            # simple check to see if it's our app
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as response:
                content = response.read().decode('utf-8')
                if "Bank Statement Converter" in content:
                    print("\n[INFO] Application is already running.")
                    print(f"Opening browser to existing instance: {url}")
                    webbrowser.open(url)
                    sys.exit(0)
                else:
                    print(f"\n[ERROR] Port {port} is occupied by another unknown application.")
                    sys.exit(1)
        except URLError:
            print(f"\n[ERROR] Port {port} is occupied, but the application could not be verified.")
            sys.exit(1)

def main():
    print(f"Bank Statement Converter v{VERSION}")
    
    # 1. Dependency check
    ensure_dependencies()

    # Delay imports until after dependencies are verified!
    try:
        from app import create_app
        from app.utils.config_utils import load_config
        from app.utils.file_utils import ensure_directories
        from app.utils.logging_utils import setup_logging
        from app.database.migrations import init_db
    except ImportError as e:
        print(f"\n[ERROR] Failed to import application modules: {e}")
        print("Dependency installation might be corrupted. Delete '.venv/requirements.hash' and restart.")
        sys.exit(1)

    # 2. Config Bootstrap
    if not os.path.exists('config.ini') and os.path.exists('config.default.ini'):
        shutil.copy('config.default.ini', 'config.ini')
        print("[INFO] Created config.ini from default template.")

    try:
        config = load_config()
    except Exception as e:
        print(f"[ERROR] Failed to load config.ini: {e}")
        sys.exit(1)

    # 3. Ensure Directories
    ensure_directories(config)
    
    # Also ensure profiles and backups
    profiles_dir = Path(config.get('paths', 'profiles', fallback='profiles'))
    backups_dir = Path(config.get('paths', 'backups', fallback='data/backups'))
    profiles_dir.mkdir(exist_ok=True, parents=True)
    backups_dir.mkdir(exist_ok=True, parents=True)

    setup_logging(config)
    logger = logging.getLogger(__name__)

    # 4. Port and Instance Protection
    host = config.get('application', 'host', fallback='127.0.0.1')
    port = config.getint('application', 'port', fallback=8080)
    
    if host != '127.0.0.1':
        logger.warning(f"Configured host is {host}. Forcing to 127.0.0.1 for security.")
        host = '127.0.0.1'

    # Werkzeug reloader spawns a subprocess. We only want to check instance/browser on the MAIN process
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        check_single_instance(host, port)

    # 5. Database Initialization
    try:
        init_db(config)
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        sys.exit(1)

    # 6. OCR Readiness Check
    ocr_enabled = config.getboolean('ocr', 'enabled', fallback=True)
    ocr_status = "Ready"
    if ocr_enabled:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ = RapidOCR()
        except Exception as e:
            ocr_status = "Unavailable"
            logger.warning(f"Local OCR unavailable: {e}")
    else:
        ocr_status = "Disabled"

    log_path = Path(config.get('paths', 'logs', fallback='logs')) / 'application.log'
    
    print(f"\nLocal URL: http://{host}:{port}")
    print("Database: Ready")
    print("PDF Extraction: Ready")
    print(f"OCR: {ocr_status}")
    print(f"Logs: {log_path.resolve()}\n")

    # 7. Start App
    app = create_app(config)
    debug = config.getboolean('application', 'debug', fallback=False)
    open_browser = config.getboolean('application', 'open_browser', fallback=True)

    def open_browser_func():
        time.sleep(1.5)
        url = f"http://{host}:{port}/"
        logger.info(f"Opening browser at {url}")
        webbrowser.open(url)

    if open_browser and not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Thread(target=open_browser_func, daemon=True).start()

    logger.info(f"Starting Flask server on {host}:{port} (debug={debug}, use_reloader=False)")
    
    try:
        app.run(host=host, port=port, debug=debug, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("Application stopped by user.")
    except Exception as e:
        logger.error(f"Application crashed: {e}", exc_info=True)

if __name__ == "__main__":
    main()
