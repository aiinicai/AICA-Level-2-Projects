"""
Red Flag Engine launcher.

Batch scripting is a poor place for conditional logic, so run_app.bat does one
thing only — find any Python that starts — and hands control here. Everything
that can go wrong is handled in this file, where the error messages can be
useful.

The rule this launcher follows: an interpreter is judged by whether it can
actually import what the app needs, never by its version number. An earlier
version of the launcher rejected Python 3.14 on principle and refused to start
on a machine where the entire application ran perfectly well.

Stdlib only — this must run on whatever Python happens to be installed.
"""
import os
import socket
import subprocess
import sys
import threading
import time
import venv
import webbrowser
from datetime import datetime
from urllib.request import urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(ROOT, "launch_log.txt")
VENV_DIR = os.path.join(ROOT, ".venv")
REQUIREMENTS = os.path.join(ROOT, "requirements.txt")

# Everything app.py imports, directly or through the engine.
NEEDED = [
    "streamlit", "pandas", "numpy", "plotly", "sklearn", "scipy",
    "reportlab", "openpyxl", "pdfplumber", "yaml", "xlsxwriter",
]

_log_lines = []


def say(message="", to_log=True):
    print(message, flush=True)
    if to_log:
        _log_lines.append(message)


def note(message):
    """Log-only detail, not shown on screen."""
    _log_lines.append(message)


def flush_log():
    try:
        with open(LOG_PATH, "w", encoding="utf-8") as fh:
            fh.write("Red Flag Engine launch log\n")
            fh.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
            fh.write("\n".join(_log_lines) + "\n")
    except OSError:
        pass


def find_free_port(preferred=8501, attempts=20):
    """
    Use the preferred port if it is free, otherwise the next one that is.
    A Streamlit instance left running from an earlier attempt would otherwise
    make this launch look like it failed.
    """
    for port in range(preferred, preferred + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred


def open_browser_when_ready(url, timeout=90):
    """
    Poll the server and open the browser once it answers.

    Streamlit's own auto-open is unreliable — it depends on how the process was
    started and on the headless setting, and when it does not fire the user is
    left looking at a console log with no window, which reads as a crash.
    Opening it here makes the behaviour the same every time.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 500:
                    break
        except Exception:
            time.sleep(0.7)
    else:
        note(f"server did not answer on {url} within {timeout}s")
        return
    try:
        webbrowser.open(url)
        print(f"\n  [ok] Opened {url} in your browser.\n", flush=True)
        note(f"opened {url}")
    except Exception as exc:
        note(f"could not open a browser: {exc}")


def ensure_streamlit_credentials():
    """
    On a machine that has never run Streamlit, it prints a welcome banner and
    blocks on stdin asking for an email address. In a double-clicked window
    that reads as "the app hung", and any stray keypress can end the session.

    Streamlit skips the prompt when a credentials file exists in the user's
    home directory — note that it does NOT read the copy in the project's own
    .streamlit folder. Returns False if the file could not be created, in
    which case the caller launches headless instead.
    """
    path = os.path.join(os.path.expanduser("~"), ".streamlit", "credentials.toml")
    if os.path.exists(path):
        note("streamlit credentials file already present")
        return True
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('[general]\nemail = ""\n')
        note(f"wrote {path} to suppress the Streamlit first-run email prompt")
        return True
    except OSError as exc:
        note(f"could not write {path}: {exc}")
        return False


def venv_python(directory):
    if os.name == "nt":
        return os.path.join(directory, "Scripts", "python.exe")
    return os.path.join(directory, "bin", "python")


def can_import_all(python_exe):
    """Does this interpreter have every dependency the app needs?"""
    if not os.path.exists(python_exe):
        note(f"  absent  {python_exe}")
        return False
    code = "import " + ", ".join(NEEDED)
    result = subprocess.run([python_exe, "-c", code],
                            capture_output=True, text=True)
    if result.returncode == 0:
        note(f"  ready   {python_exe}")
        return True
    note(f"  missing {python_exe}: {result.stderr.strip().splitlines()[-1:]}")
    return False


def missing_packages(python_exe):
    absent = []
    for module in NEEDED:
        result = subprocess.run([python_exe, "-c", "import " + module],
                                capture_output=True, text=True)
        if result.returncode != 0:
            absent.append(module)
    return absent


def install_into(python_exe):
    say("")
    say("Installing dependencies. The first run downloads around 150 MB —")
    say("this takes a minute or two. Progress is shown below.")
    say("")
    subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"],
                   check=False)
    result = subprocess.run([python_exe, "-m", "pip", "install", "-r", REQUIREMENTS],
                            check=False)
    note(f"pip install exit code {result.returncode}")
    return result.returncode == 0


def choose_interpreter():
    """
    Return a Python that can run the app, installing dependencies if needed,
    or None with an explanation already printed.
    """
    candidates = [
        (venv_python(VENV_DIR), "the project's own environment (.venv)"),
        (sys.executable, "the Python that started this launcher"),
    ]

    for exe, description in candidates:
        if can_import_all(exe):
            say(f"[ok] Using {description}.")
            say(f"     {exe}")
            return exe

    # Nothing is ready. Install — preferring an existing .venv, then creating one.
    say("[..] Dependencies are not installed yet.")

    target = venv_python(VENV_DIR)
    if not os.path.exists(target):
        say("[..] Creating a private environment in .venv (one time)...")
        try:
            venv.EnvBuilder(with_pip=True, clear=False).create(VENV_DIR)
        except Exception as exc:
            note(f"venv creation failed: {exc}")
            say(f"[..] Could not create .venv ({exc.__class__.__name__}).")
            say("     Installing into the current Python instead.")
            target = sys.executable

    if not os.path.exists(target):
        target = sys.executable

    if not install_into(target):
        say("")
        say("[X] Dependency installation failed.")
        say("    The pip output above names the package that could not be")
        say("    installed. If it mentions camelot, opencv or Ghostscript,")
        say("    those are optional — tell me and I will remove them.")
        return None

    if can_import_all(target):
        return target

    absent = missing_packages(target)
    say("")
    say("[X] Installation finished but these still cannot be imported:")
    say("    " + ", ".join(absent))
    say("")
    say("    Run diagnose.bat for a full report.")
    return None


def main():
    os.chdir(ROOT)

    say("===============================================================")
    say("  RED FLAG ENGINE - Forensic Accounting & Fraud-Risk Analytics")
    say("===============================================================")
    say("")
    note(f"launcher interpreter: {sys.executable} ({sys.version.split()[0]})")
    note(f"platform: {sys.platform}")
    note("--- interpreter search ---")

    python_exe = choose_interpreter()
    if python_exe is None:
        flush_log()
        say("")
        say(f"A log was written to {LOG_PATH}")
        return 1

    app = os.path.join(ROOT, "app.py")
    if not os.path.exists(app):
        say(f"[X] app.py was not found in {ROOT}")
        flush_log()
        return 1

    ensure_streamlit_credentials()
    port = find_free_port(8501)
    url = f"http://localhost:{port}"
    if port != 8501:
        note(f"port 8501 was busy; using {port}")

    say("")
    say("---------------------------------------------------------------")
    say("  THE APP IS STARTING. This window is the server.")
    say("---------------------------------------------------------------")
    say("")
    say("  It will open in your browser automatically.")
    say("  If it does not, open this address yourself:")
    say("")
    say(f"      {url}")
    if port != 8501:
        say("      (port 8501 was already in use)")
    say("")
    say("  KEEP THIS WINDOW OPEN while you use the app.")
    say("  Everything printed below is the server's normal log,")
    say("  not an error. Press Ctrl+C here when you have finished.")
    say("")
    say("---------------------------------------------------------------")
    say("")
    note("--- streamlit run ---")
    flush_log()

    # Headless, because this launcher opens the browser itself once the
    # server actually answers — Streamlit's own auto-open does not always fire.
    command = [
        python_exe, "-m", "streamlit", "run", app,
        "--server.port", str(port),
        "--server.address", "localhost",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]

    threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True).start()

    try:
        result = subprocess.run(command, check=False)
        code = result.returncode
    except KeyboardInterrupt:
        code = 0

    note(f"streamlit exited with code {code}")
    flush_log()

    if code not in (0, None):
        say("")
        say("===============================================================")
        say(f"  The server stopped with exit code {code}.")
        say("  The lines above this box are the real error — please read")
        say(f"  them. They are also in {LOG_PATH}")
        say("===============================================================")
        return code

    say("")
    say("Server stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
