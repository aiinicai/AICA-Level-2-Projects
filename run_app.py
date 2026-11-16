"""Desktop launcher. PyInstaller turns this file into CAPracticeManager.exe.

How it works
  * The .exe starts a hidden copy of itself that runs the app server (`--serve PORT`).
  * It then opens the app in its own window (Microsoft Edge WebView2, built into Windows 10/11).
  * Closing the window stops everything.
  * If the app window can't be created, it opens the app in the normal web browser instead and shows a
    small "CA Practice Manager is running" window with a Stop button.
  * CAPM_HEADLESS=1 runs only the server (used by the automatic build check on GitHub).
"""
import os
import socket
import subprocess
import sys
import time
import traceback
import urllib.request

# These imports are not used here. They tell PyInstaller to pack everything app.py needs,
# because Streamlit runs app.py as a script that PyInstaller cannot see on its own.
import fpdf  # noqa: F401
import openpyxl  # noqa: F401
import pandas  # noqa: F401
import plotly.express  # noqa: F401
import psycopg2  # noqa: F401
import pypdf  # noqa: F401
import sqlalchemy.dialects.postgresql  # noqa: F401
import sqlalchemy.dialects.sqlite  # noqa: F401

import core.ai  # noqa: F401
import core.auth  # noqa: F401
import core.clock  # noqa: F401
import core.constants  # noqa: F401
import core.db  # noqa: F401
import core.duedates  # noqa: F401
import core.importer  # noqa: F401
import core.invoice_pdf  # noqa: F401
import core.ui  # noqa: F401
import seed  # noqa: F401
import views.account  # noqa: F401
import views.ai_assistant  # noqa: F401
import views.billing  # noqa: F401
import views.calendar_view  # noqa: F401
import views.clients  # noqa: F401
import views.common  # noqa: F401
import views.dashboard  # noqa: F401
import views.documents  # noqa: F401
import views.settings  # noqa: F401
import views.tasks  # noqa: F401
import views.team  # noqa: F401
from core import config

APP_NAME = "CA Practice Manager"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW: hide the server's console


def _log_to_file():
    """A windowed .exe has no console; send all output to a log file the user can send for support."""
    if sys.stdout is None or sys.stderr is None or config.FROZEN:
        f = open(config.LOG_FILE, "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = f


def log(msg):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [launcher] {msg}", flush=True)


def free_port(start=8501) -> int:
    for port in range(start, start + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2) as r:
            return r.read().decode().strip() == "ok"
    except Exception:
        return False


def serve(port: int):
    """Run the Streamlit server in this process."""
    os.environ["CAPM_DESKTOP"] = "1"
    os.chdir(config.CODE_DIR)  # so Streamlit finds .streamlit/config.toml (the navy theme)
    share = bool(config.local_settings().get("share_on_office_network"))
    sys.argv = ["streamlit", "run", str(config.CODE_DIR / "app.py"),
                "--global.developmentMode=false",
                f"--server.port={port}",
                f"--server.address={'0.0.0.0' if share else '127.0.0.1'}",
                "--server.headless=true",
                "--server.fileWatcherType=none",
                "--browser.gatherUsageStats=false",
                "--browser.serverAddress=localhost"]
    log(f"server starting on port {port} · {config.database_label()}")
    from streamlit.web import cli as stcli
    sys.exit(stcli.main())


def start_server_process(port: int) -> subprocess.Popen:
    cmd = [sys.executable, "--serve", str(port)] if config.FROZEN else \
        [sys.executable, os.path.abspath(__file__), "--serve", str(port)]
    logf = open(config.LOG_FILE, "a", encoding="utf-8")
    return subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                            creationflags=NO_WINDOW, env={**os.environ, "CAPM_DESKTOP": "1"})


LOADING = """<html><body style="margin:0;height:100vh;display:flex;align-items:center;justify-content:center;
background:#0B1F3A;font-family:Segoe UI,sans-serif;color:#CBD5E1"><div style="text-align:center">
<div style="width:64px;height:64px;border-radius:18px;margin:0 auto 18px;background:linear-gradient(135deg,#0D9488,#2DD4BF);
display:flex;align-items:center;justify-content:center;color:#0B1F3A;font-weight:800;font-size:22px">CA</div>
<div style="font-size:22px;color:#fff;font-weight:700">CA Practice Manager</div>
<div style="margin-top:10px">Starting up&hellip; this takes a few seconds</div></div></body></html>"""

FAILED = """<html><body style="font-family:Segoe UI,sans-serif;padding:40px;color:#0F172A">
<h2>CA Practice Manager could not start</h2><p>Please close this window and try again.
If it keeps happening, send this file to your administrator:</p><code>{log}</code></body></html>"""


def open_window(port: int, server: subprocess.Popen) -> bool:
    """Open the app in its own window. Returns False if a window couldn't be created."""
    try:
        import webview
        webview.settings["ALLOW_DOWNLOADS"] = True           # invoices, Excel exports, documents
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    except Exception:
        log("app window not available:\n" + traceback.format_exc())
        return False
    url = f"http://localhost:{port}/"
    try:
        win = webview.create_window(APP_NAME, html=LOADING, width=1440, height=920, min_size=(1024, 680),
                                    background_color="#0B1F3A", text_select=True, zoomable=True)

        def boot():
            for _ in range(240):  # up to ~2 minutes on slow PCs
                if healthy(port):
                    win.load_url(url)
                    return
                if server.poll() is not None:
                    break
                time.sleep(0.5)
            win.load_html(FAILED.format(log=config.LOG_FILE))

        webview.start(boot, private_mode=False, storage_path=str(config.DATA_DIR / "window"))
        return True
    except Exception:
        log("app window failed:\n" + traceback.format_exc())
        return False


def fallback_browser(port: int, server: subprocess.Popen):
    """No app window available: use the normal browser plus a small control window."""
    import webbrowser
    url = f"http://localhost:{port}/"
    for _ in range(240):
        if healthy(port) or server.poll() is not None:
            break
        time.sleep(0.5)
    webbrowser.open(url)
    try:
        import tkinter as tk
        root = tk.Tk()
        root.title(APP_NAME)
        root.geometry("380x170")
        root.configure(bg="#0B1F3A")
        tk.Label(root, text="CA Practice Manager is running", fg="white", bg="#0B1F3A",
                 font=("Segoe UI", 12, "bold")).pack(pady=(22, 4))
        tk.Label(root, text="It is open in your web browser.\nClose this window to stop the app.",
                 fg="#CBD5E1", bg="#0B1F3A", font=("Segoe UI", 9)).pack()
        bar = tk.Frame(root, bg="#0B1F3A")
        bar.pack(pady=14)
        tk.Button(bar, text="Open again", width=12, command=lambda: webbrowser.open(url)).pack(side="left", padx=6)
        tk.Button(bar, text="Stop app", width=12, command=root.destroy).pack(side="left", padx=6)
        root.mainloop()
    except Exception:
        log("control window failed, waiting for server:\n" + traceback.format_exc())
        server.wait()


def main():
    _log_to_file()
    if len(sys.argv) >= 3 and sys.argv[1] == "--serve":
        serve(int(sys.argv[2]))
        return
    if os.environ.get("CAPM_HEADLESS"):
        serve(int(os.environ.get("CAPM_PORT") or 8501))
        return
    port = int(os.environ.get("CAPM_PORT") or free_port(int(config.local_settings().get("port", 8501))))
    log(f"starting {APP_NAME}, data folder {config.DATA_DIR}")
    server = start_server_process(port)
    try:
        if not open_window(port, server):
            fallback_browser(port, server)
    finally:
        log("window closed, stopping server")
        server.terminate()
        try:
            server.wait(timeout=8)
        except Exception:
            server.kill()


if __name__ == "__main__":
    main()  # note: pywebview requires this to stay on the untouched main thread
