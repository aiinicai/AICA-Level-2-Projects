"""
GS Stock Audit Tracker Launcher
Lead Partner: CA Gaurav Chaudhary
Safe, robust launcher ready for Python IDLE, Command Prompt, or direct execution.
"""

import os
import sys
import socket
import webbrowser
import time
import subprocess

def get_free_port(start_port=8501):
    """Finds the first available TCP port starting from 8501."""
    for p in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', p)) != 0:
                return p
    return 8501

def main():
    print("==================================================================")
    print("      GS STOCK AUDIT TRACKER (LEAD PARTNER: CA GAURAV CHAUDHARY)  ")
    print("==================================================================")
    
    # 1. Initialize Database & Seed
    try:
        import database as db
        import auth
        import seed_sample_data
        
        db.init_db()
        auth.create_default_users()
        seed_sample_data.seed()
        print("✓ Database and default user accounts verified.")
    except Exception as e:
        print("Notice during database check:", e)

    # 2. Determine App Path & Free Port
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    port = get_free_port(8501)
    url = f"http://localhost:{port}"
    
    print(f"\n🚀 Launching GS Stock Audit Tracker on: {url}")
    print("Press Ctrl+C to stop the server at any time.\n")
    
    # 3. Launch Streamlit
    try:
        from streamlit.web import cli as stcli
        sys.argv = [
            "streamlit",
            "run",
            app_path,
            f"--server.port={port}",
            "--server.headless=false",
            "--browser.gatherUsageStats=false"
        ]
        stcli.main()
    except Exception as err:
        print("In-process launch failed, falling back to subprocess launcher:", err)
        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            app_path,
            f"--server.port={port}",
            "--server.headless=false",
            "--browser.gatherUsageStats=false"
        ]
        subprocess.run(cmd)

if __name__ == "__main__":
    main()
