"""
launcher.pyw
------------
Double-click THIS file to run the whole Income Tax Return Download
tool. No command prompt, no manual Chrome command.

What it does, in order:
  0. First time ever on a given computer only: creates a Python
     virtual environment and installs everything from
     requirements.txt (plus Playwright's Chromium), so you don't
     need to run pip/playwright install commands yourself.
  1. Starts a real Chrome window in the background with the
     remote-debugging port the automation needs (this is the step
     that used to be a manual command from README.md). That Chrome
     window is fully hidden (headless) - you never see it.
  2. Starts the FastAPI/uvicorn server in the background.
  3. Opens your normal browser at http://localhost:8001.

A small status window stays open so you can see what's happening
and read any error. You can minimize it; the server keeps running
even if you close this window (close the little Chrome icon in
your taskbar / Task Manager if you ever need to fully stop it).

If something fails, the status window will say exactly what and
why - read that message before asking for help.
"""

import http.client
import os
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CHROME_PROFILE_DIR = BASE_DIR / "chrome-automation-profile"
CDP_HOST, CDP_PORT = "localhost", 9222
APP_HOST, APP_PORT = "localhost", 8001

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe"),
]


VENV_DIR = BASE_DIR / "venv"
SETUP_LOG_PATH = BASE_DIR / "setup.log"


def _venv_python_path():
    # Windows venv layout first (this project targets Windows), then the
    # Unix layout just in case this ever runs elsewhere.
    for c in (VENV_DIR / "Scripts" / "python.exe", VENV_DIR / "bin" / "python"):
        if c.exists():
            return c
    return None


def _run_setup_step(cmd, log, label):
    """
    Run one setup command, with its full output appended to setup.log
    (pip/playwright output is long), and only a short status plus the
    last few lines surfaced in the status window on failure.
    """
    log(label)
    with open(SETUP_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n$ {' '.join(str(c) for c in cmd)}\n")
        f.flush()
        result = subprocess.run(
            cmd, cwd=str(BASE_DIR), stdout=f, stderr=subprocess.STDOUT, text=True
        )
    if result.returncode != 0:
        tail = SETUP_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-15:]
        log("ERROR: " + label + " failed. Last lines of setup.log:")
        for line in tail:
            log("    " + line)
        return False
    return True


def _find_base_python():
    """
    A base/system Python to create the venv with (this project needs
    3.12 or similar - not 3.14, where Playwright's dependencies don't
    yet have prebuilt wheels). Prefer the Windows Python launcher's
    3.12 if present, otherwise fall back to whatever "python" is on
    PATH and hope it's compatible.
    """
    for candidate in (["py", "-3.12"], ["python3.12"], ["python"], ["py"]):
        try:
            subprocess.run(candidate + ["--version"], check=True,
                            capture_output=True, cwd=str(BASE_DIR))
            return candidate
        except Exception:
            continue
    return None


def ensure_venv(log):
    """
    Double-clicking a .pyw file runs it with whichever Python Windows
    has associated with that file type - usually the system/base
    Python, NOT a project venv (where fastapi/uvicorn/playwright are
    actually installed). On a computer that has never run this tool
    before, there IS no venv yet - so create one, install
    requirements.txt into it, and install Playwright's Chromium,
    all automatically, the first time. Later runs just reuse it.
    """
    existing = _venv_python_path()
    if existing:
        return str(existing)

    log("First run on this computer - setting up Python packages "
        "(fastapi, uvicorn, playwright). This can take a few minutes, "
        "only on this first run...")

    base_python = _find_base_python()
    if not base_python:
        log("ERROR: No Python installation found on this computer. "
            "Install Python 3.12 from python.org first, then try again.")
        return None

    if not _run_setup_step(base_python + ["-m", "venv", str(VENV_DIR)], log,
                            "Creating a Python environment for this tool..."):
        return None

    venv_python = _venv_python_path()
    if not venv_python:
        log("ERROR: Virtual environment was created but python.exe is missing.")
        return None

    req_file = BASE_DIR / "requirements.txt"
    if not _run_setup_step(
        [str(venv_python), "-m", "pip", "install", "-r", str(req_file)],
        log, "Installing required packages (fastapi, uvicorn, playwright)...",
    ):
        return None

    if not _run_setup_step(
        [str(venv_python), "-m", "playwright", "install", "chromium"],
        log, "Installing Chromium for Playwright (one-time, a few hundred MB)...",
    ):
        return None

    log("Setup complete.")
    return str(venv_python)


def _port_open(host, port, timeout=0.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_alive(host, port, path="/", timeout=1.0):
    conn = None
    try:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("GET", path)
        conn.getresponse()
        return True
    except Exception:
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def find_chrome():
    for c in CHROME_CANDIDATES:
        if c and Path(c).exists():
            return c
    return None


def ensure_debug_chrome(log):
    if _port_open(CDP_HOST, CDP_PORT):
        log("Automation Chrome is already running - reusing it.")
        return True

    chrome_path = find_chrome()
    if not chrome_path:
        log(
            "ERROR: Could not find chrome.exe in the usual install "
            "locations. Open launcher.pyw in a text editor and add "
            "your Chrome's exact path to CHROME_CANDIDATES."
        )
        return False

    log("Starting Chrome for automation (fully hidden - no window at all)...")
    CHROME_PROFILE_DIR.mkdir(exist_ok=True)
    try:
        subprocess.Popen(
            [
                chrome_path,
                f"--remote-debugging-port={CDP_PORT}",
                f"--user-data-dir={CHROME_PROFILE_DIR}",
                # "--headless=new" is the modern headless mode: it renders the
                # page fully and normally (so Playwright can still see and
                # click elements, unlike --start-minimized which breaks
                # rendering) but never creates a visible window at all - not
                # even an off-screen one. It also does NOT add the automation
                # fingerprints that got Playwright-launched browsers blocked
                # before (that block came from Playwright's own launch flags,
                # not from being headless).
                "--headless=new",
                "--window-size=1920,1080",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        log(f"ERROR: Could not launch Chrome: {exc}")
        return False

    for _ in range(30):
        if _port_open(CDP_HOST, CDP_PORT):
            log("Automation Chrome is ready.")
            return True
        time.sleep(0.5)

    log("ERROR: Chrome did not open the debug port in time.")
    return False


def ensure_server(log):
    if _http_alive(APP_HOST, APP_PORT):
        log(f"Server is already running on port {APP_PORT} - reusing it.")
        return True

    python_exe = ensure_venv(log)
    if not python_exe:
        return False
    log(f"Starting the Income Tax Return Download server (using {python_exe})...")
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    log_path = BASE_DIR / "server.log"
    log_file = open(log_path, "a", encoding="utf-8")
    try:
        subprocess.Popen(
            [python_exe, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(APP_PORT)],
            cwd=str(BASE_DIR),
            stdout=log_file,
            stderr=log_file,
            creationflags=creationflags,
        )
    except Exception as exc:
        log(f"ERROR: Could not start the server: {exc}")
        return False

    for _ in range(40):
        if _http_alive(APP_HOST, APP_PORT):
            log("Server is ready.")
            return True
        time.sleep(0.5)

    log(f"ERROR: Server did not start in time. Check server.log in this folder for details.")
    return False


def main():
    root = tk.Tk()
    root.title("Income Tax Return Download")
    root.geometry("480x240")
    root.resizable(False, False)

    text = tk.Text(root, wrap="word", state="disabled", bg="#f6f6f6", relief="flat", padx=10, pady=10)
    text.pack(fill="both", expand=True, padx=10, pady=10)

    def log(msg):
        def _write():
            text.configure(state="normal")
            text.insert("end", msg + "\n")
            text.see("end")
            text.configure(state="disabled")
        root.after(0, _write)

    def worker():
        log("Income Tax Return Download - starting up...")
        if not ensure_debug_chrome(log):
            log("\nFix the error above, then close this window and double-click launcher.pyw again.")
            return
        if not ensure_server(log):
            log("\nFix the error above, then close this window and double-click launcher.pyw again.")
            return
        log("Opening your browser...")
        webbrowser.open(f"http://{APP_HOST}:{APP_PORT}")
        log("")
        log("Ready. You can minimize this window.")
        log("(Closing this window does not stop the server or Chrome.)")

    threading.Thread(target=worker, daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    main()
