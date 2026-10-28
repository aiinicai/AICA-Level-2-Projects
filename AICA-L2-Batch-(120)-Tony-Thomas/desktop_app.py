import os
import sys
import time
import socket
import threading
import webbrowser
import traceback

# Force UTF-8 encoding on Windows console where supported
if sys.platform.startswith("win"):
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure working directory in PyInstaller frozen bundle is the directory containing the .exe
if getattr(sys, "frozen", False):
    exe_dir = os.path.dirname(sys.executable)
    os.chdir(exe_dir)

def find_available_port(start_port=8000):
    for port in [start_port, 8001, 8002, 8080, 8888, 5000]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port

def open_browser(url):
    time.sleep(1.5)
    webbrowser.open(url)

def main():
    import multiprocessing
    multiprocessing.freeze_support()

    from main import app
    import uvicorn

    port = find_available_port(8000)
    url = f"http://127.0.0.1:{port}"

    print("=" * 65)
    print("   ALL IN ONE ACCOUNTANT - RETAIL & WHOLESALE MART")
    print("=" * 65)
    print(f" [OK] Initializing local database and Chart of Accounts...")
    print(f" [OK] Starting Web Application Server on {url}")
    print(f" [OK] Launching default web browser automatically...")
    print(f" [*]  Keep this window open while using the application.")
    print(f" [*]  Press Ctrl+C to close and exit.")
    print("=" * 65)

    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("\n" + "!" * 65)
        print("ERROR: Application failed to start!")
        traceback.print_exc()
        print("!" * 65)
        input("\nPress Enter to exit...")
