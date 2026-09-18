"""
GS Stock Audit Tracker - Network Server Runner
Binds to 0.0.0.0:8501 so all team members on the office LAN/Wi-Fi can access.
"""

import os
import sys
import subprocess
import socket

def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def run_server():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(base_dir, "app.py")
    log_path = os.path.join(base_dir, "server.log")
    
    # Initialize DB & users
    try:
        import database as db
        import auth
        import seed_sample_data
        db.init_db()
        auth.create_default_users()
        seed_sample_data.seed()
    except Exception as e:
        pass
        
    host_ip = get_host_ip()
    port = 8501
    
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"\n--- Server started on http://{host_ip}:{port} ---\n")
        
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        app_path,
        f"--server.port={port}",
        "--server.address=0.0.0.0",
        "--server.headless=true",
        "--browser.gatherUsageStats=false"
    ]
    
    with open(log_path, "a", encoding="utf-8") as log_file:
        subprocess.run(cmd, stdout=log_file, stderr=log_file)

if __name__ == "__main__":
    run_server()
