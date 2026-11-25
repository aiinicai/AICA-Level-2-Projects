"""NOTICE-MATE desktop launcher (Windows).

Opens NOTICE-MATE in its own app window, with no Command Prompt windows to manage:
  * starts the engine (FastAPI, port 8000) and the screen (Streamlit, port 8501) hidden in the background;
  * waits until both answer, then opens a separate Microsoft Edge app window (own profile, no tabs or address bar);
  * when that window is closed, stops both servers;
  * if NOTICE-MATE is already running, simply opens another window onto it.

Run through "NOTICE-MATE.vbs" (no console) or:  pythonw scripts\\desktop_launcher.py
Stop everything:                                pythonw scripts\\desktop_launcher.py --stop   (or "Close NOTICE-MATE.vbs")
Uses the normal configuration (.env / workspace). It never reads or logs API-key values.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE_PORT = int(os.getenv("NOTICEMATE_API_PORT", "8000"))
UI_PORT = int(os.getenv("NOTICEMATE_UI_PORT", "8501"))
ENGINE_URL = f"http://127.0.0.1:{ENGINE_PORT}/health"
UI_URL = f"http://127.0.0.1:{UI_PORT}"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW


def _data_dir() -> Path:
    sys.path.insert(0, str(ROOT))
    try:
        from noticemate.core.config import get_settings

        return Path(get_settings().data_dir)
    except Exception:  # config problems are reported by the engine itself
        return ROOT / "workspace"


DATA = _data_dir()
STATE = DATA / "logs" / "desktop_launcher.json"
LOG = DATA / "logs" / "desktop_launcher.log"


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def alive(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # local addresses only
            return r.status < 500
    except Exception:
        return False


def message(text: str, title: str = "NOTICE-MATE") -> None:
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, text, title, 0x40)
            return
        except Exception:
            pass
    print(text)


def python_exe(windowless: bool = True) -> str:
    exe = Path(sys.executable)
    if os.name == "nt":
        # prefer python.exe for the child servers (pythonw has no stdout, which uvicorn/streamlit can dislike)
        cand = exe.with_name("python.exe")
        if cand.exists():
            return str(cand)
    return str(exe)


def start_servers() -> list[subprocess.Popen]:
    (DATA / "logs").mkdir(parents=True, exist_ok=True)
    py = python_exe()
    procs = []
    specs = [
        ("engine", [py, "-m", "noticemate.api.main"]),
        ("screen", [py, "-m", "streamlit", "run", str(ROOT / "frontend" / "app.py"), "--server.address", "127.0.0.1",
                    "--server.port", str(UI_PORT), "--server.headless", "true", "--browser.gatherUsageStats", "false"]),
    ]
    for name, cmd in specs:
        out = open(DATA / "logs" / f"{name}.log", "a", encoding="utf-8")
        p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             creationflags=NO_WINDOW)
        procs.append(p)
        log(f"started {name} pid={p.pid}")
    STATE.write_text(json.dumps({"pids": [p.pid for p in procs], "started": time.time()}), encoding="utf-8")
    return procs


def wait_ready(procs: list[subprocess.Popen], seconds: int = 90) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if any(p.poll() is not None for p in procs):
            return False
        if alive(ENGINE_URL) and alive(UI_URL):
            return True
        time.sleep(0.7)
    return False


def kill_pid(pid: int) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, creationflags=NO_WINDOW)
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception:
        pass


def stop_servers(procs: list[subprocess.Popen] | None = None) -> None:
    pids = [p.pid for p in procs or []]
    if not pids and STATE.exists():
        try:
            pids = json.loads(STATE.read_text(encoding="utf-8")).get("pids", [])
        except Exception:
            pids = []
    for pid in pids:
        kill_pid(pid)
    STATE.unlink(missing_ok=True)
    log(f"stopped pids={pids}")


def find_edge() -> str | None:
    for base in (os.getenv("ProgramFiles(x86)"), os.getenv("ProgramFiles"), os.getenv("LOCALAPPDATA")):
        if base:
            p = Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if p.exists():
                return str(p)
    return shutil.which("msedge")


def open_window(wait: bool) -> bool:
    """Open the app window. Returns True if we waited for it to close."""
    edge = find_edge()
    if edge:
        profile = DATA / "desktop-window-profile"  # a separate profile, so the window is its own process
        cmd = [edge, f"--app={UI_URL}", f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
               "--window-size=1440,900", "--disable-features=Translate"]
        p = subprocess.Popen(cmd, creationflags=NO_WINDOW)
        if wait:
            p.wait()
            # Edge may hand the window to an already-running process of the same profile; keep watching it.
            while _profile_in_use(profile):
                time.sleep(1.5)
            return True
        return False
    webbrowser.open(UI_URL)
    return False


def _profile_in_use(profile: Path) -> bool:
    if os.name != "nt":
        return False
    try:
        out = subprocess.run(["wmic", "process", "where", "name='msedge.exe'", "get", "CommandLine"], capture_output=True,
                             text=True, creationflags=NO_WINDOW, timeout=10).stdout
    except Exception:
        try:
            ps = ("Get-CimInstance Win32_Process -Filter \"name='msedge.exe'\" | Select-Object -ExpandProperty CommandLine")
            out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                                 creationflags=NO_WINDOW, timeout=15).stdout
        except Exception:
            return False
    return str(profile).lower() in (out or "").lower()


def main() -> int:
    if "--stop" in sys.argv:
        stop_servers()
        message("NOTICE-MATE has been closed.")
        return 0
    if alive(ENGINE_URL) and alive(UI_URL):
        log("already running — opening another window")
        open_window(wait=False)
        return 0
    if alive(ENGINE_URL) or alive(UI_URL):
        message("Another program is already using NOTICE-MATE's ports "
                f"({ENGINE_PORT} or {UI_PORT}). Close any older NOTICE-MATE windows (or run 'Close NOTICE-MATE'), then try again.")
        return 1
    procs = start_servers()
    if not wait_ready(procs):
        stop_servers(procs)
        message("NOTICE-MATE could not start. Details are in:\n" + str(DATA / "logs" / "engine.log") + "\n"
                + str(DATA / "logs" / "screen.log"))
        return 1
    log("ready")
    waited = open_window(wait=True)
    if waited:
        stop_servers(procs)
        return 0
    # No Edge found: the default browser was opened. Keep the servers until 'Close NOTICE-MATE' is used.
    message("NOTICE-MATE is open in your browser.\n\nWhen you have finished, double-click 'Close NOTICE-MATE' to stop it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
