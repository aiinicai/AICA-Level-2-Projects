"""
LexSecure India Pro - Web Application Launcher
Automatically finds an open dedicated port (default 8055) to prevent collisions with other local apps
"""

import sys
import os
import socket
import threading
import time
import webbrowser
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.chdir(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lexsecure_core.settings')

def is_port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False

def find_available_port(start_port=8055, max_attempts=20):
    for p in range(start_port, start_port + max_attempts):
        if is_port_free(p):
            return p
    return start_port

def open_browser_when_ready(url, delay=1.2):
    time.sleep(delay)
    print(f"\n[LexSecure] Opening browser at {url}...")
    webbrowser.open(url)

def main():
    port = find_available_port(8055)
    url = f"http://127.0.0.1:{port}/"

    print("=" * 76)
    print("             LEXSECURE INDIA PRO - ENTERPRISE LEGALTECH WEB APP")
    print("       Statutory & Regulatory Intelligence for Indian Operating Entities")
    print("=" * 76)
    print(f"\n[LexSecure] Binding to dedicated port: {port}")
    print(f"[LexSecure] Target Web URL: {url}\n")

    # Start browser opener thread
    threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True).start()

    from django.core.management import execute_from_command_line
    # Launch Django on the selected port
    execute_from_command_line(['manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload'])

if __name__ == '__main__':
    main()
