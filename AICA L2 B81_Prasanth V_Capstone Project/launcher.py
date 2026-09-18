import os
import sys
import time
import webbrowser
import threading
import subprocess
import uvicorn
from pathlib import Path

# Set up paths
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from app.seed import seed_database

PORT = 8000

def free_port(port: int):
    """
    Kill any process currently listening on the given port (Windows).
    Uses netstat + taskkill — no third-party library required.
    """
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and ("LISTENING" in line or "ESTABLISHED" in line):
                parts = line.split()
                pid = parts[-1]
                if pid.isdigit() and int(pid) != os.getpid():
                    subprocess.run(
                        ["taskkill", "/F", "/PID", pid],
                        capture_output=True, timeout=5
                    )
                    print(f"  [INFO] Released port {port} (killed stale PID {pid})")
                    time.sleep(0.8)  # give OS time to release the socket
                    break
    except Exception as e:
        print(f"  [WARN] Could not free port {port}: {e}")


def open_browser():
    """Wait for server to boot then launch the default browser."""
    time.sleep(2.0)
    webbrowser.open(f"http://127.0.0.1:{PORT}")


def main():
    print("=" * 65)
    print("   ASSET TAGGING & LABEL MANAGEMENT SYSTEM (ENTERPRISE v1.0)")
    print("=" * 65)

    # Step 1 — Free port if something is already holding it
    print(f"Checking port {PORT} availability...")
    free_port(PORT)

    # Step 2 — Seed / verify database
    print("Initializing SQLite WAL Database & verifying reference schemas...")
    seed_database()
    print(f"Starting server at http://127.0.0.1:{PORT} ...")

    # Step 3 — Open browser after server comes up
    threading.Thread(target=open_browser, daemon=True).start()

    # Step 4 — Start FastAPI server
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=PORT,
        log_level="info",
        access_log=False
    )


if __name__ == "__main__":
    main()
