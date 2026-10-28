import os
import sys
import socket
import webbrowser
import threading
import time
import traceback


def pause_and_exit(code=1):
    """Keep the console window open so the message can be read when double-clicked."""
    try:
        input("\nPress Enter to close this window...")
    except Exception:
        pass
    sys.exit(code)


# Support PyInstaller resource path
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    APP_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = BASE_DIR
    # Make sure "backend" is importable even when started by double-click from another folder
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    os.chdir(BASE_DIR)

# Set database path in writable directory
os.environ["BRS_DB_PATH"] = os.path.join(APP_DIR, "data", "brs.db")

try:
    import uvicorn
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    from backend.database import init_db
    from backend.seed_data import seed_database
    from backend.api import router as api_router
except ImportError as e:
    print("=" * 70)
    print(" BRS Tool could not start: a required Python package is missing.")
    print(f" Details: {e}")
    print()
    print(" Fix: open a Command Prompt in this folder and run:")
    print("      python -m pip install -r requirements.txt")
    print("=" * 70)
    pause_and_exit(1)
except Exception:
    print("=" * 70)
    print(" BRS Tool failed while loading. Full error below:")
    print("=" * 70)
    traceback.print_exc()
    pause_and_exit(1)

app = FastAPI(title="BRS Tool - Enterprise Bank Reconciliation System", version="2.0")

# Mount API
app.include_router(api_router)

# Mount Static Files
static_dir = os.path.join(BASE_DIR, "frontend", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_root():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "BRS Tool", "version": "2.0"}


def get_lan_ip():
    """Detects primary LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def find_free_port(preferred=8000, attempts=20):
    """Returns the preferred port, or the next free one if it is already in use
    (for example by an older BRS Tool window that is still running)."""
    for port in range(preferred, preferred + attempts):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("0.0.0.0", port))
            s.close()
            return port
        except OSError:
            s.close()
    return None


def open_browser(port):
    time.sleep(1.5)
    url = f"http://localhost:{port}"
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main():
    # Initialize DB & Seed Demo Data
    init_db()
    seed_database(force=False)

    preferred = int(os.environ.get("BRS_PORT", "8000"))
    port = find_free_port(preferred)
    if port is None:
        print(f"No free network port found between {preferred} and {preferred + 19}.")
        print("Close other BRS Tool windows (or BRS_Tool.exe in Task Manager) and try again.")
        pause_and_exit(1)

    lan_ip = get_lan_ip()

    print("=" * 70)
    print("   BRS TOOL - ENTERPRISE BANK RECONCILIATION APPLICATION")
    print("=" * 70)
    if port != preferred:
        print(f" NOTE: port {preferred} is already in use (an older BRS Tool may still be running).")
        print(f"       Using port {port} instead.")
    print(f" * Local Access URL:      http://localhost:{port}")
    print(f" * LAN Access (Same Wi-Fi): http://{lan_ip}:{port}")
    print("=" * 70)
    print(f" Share 'http://{lan_ip}:{port}' with colleagues on the same LAN network!")
    print(" Press Ctrl+C in this console window to stop the server.")
    print("=" * 70)

    # Automatically open browser in thread
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    # Run Uvicorn server on all network interfaces (0.0.0.0)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except SystemExit:
        raise
    except Exception:
        print("=" * 70)
        print(" BRS Tool stopped because of an error. Full details below:")
        print("=" * 70)
        traceback.print_exc()
        pause_and_exit(1)
