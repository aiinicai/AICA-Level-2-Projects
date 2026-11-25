"""Start or stop the app without a console window (run with pythonw.exe).

    pythonw -m app.launcher            start the app (or just open the browser if it is running)
    pythonw -m app.launcher --demo     the same for the demo copy (synthetic data, port 8001)
    pythonw -m app.launcher --stop     stop it (add --demo for the demo)

The server runs hidden; its messages go to <instance>/logs/app.log. Problems are shown in a
Windows message box. The very first Admin is created in the browser (/setup) - no console needed.
"""
from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLE = "Cash Flow Forecast"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DETACHED = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


def demo_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "CashFlowForecast" / "demo"


def message(text: str, error: bool = False) -> None:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, TITLE + (" - problem" if error else ""),
                                         0x10 if error else 0x40)
    except Exception:                                        # not Windows / no GUI: fall back to stderr
        print(text, file=sys.stderr)


def configure(demo: bool) -> None:
    if demo:
        os.environ["CFF_INSTANCE_DIR"] = str(demo_dir())
        os.environ["CFF_HOST"] = "127.0.0.1"
        os.environ["CFF_PORT"] = os.environ.get("CFF_DEMO_PORT", "8001")


def app_url(s) -> str:
    host = "localhost" if s.host in ("0.0.0.0", "::", "127.0.0.1") else s.host
    return f"{'https' if s.https_enabled else 'http'}://{host}:{s.port}"


def responding(url: str, timeout: float = 1.5) -> bool:
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE   # only "is it up?" on this PC
    try:
        with urllib.request.urlopen(url + "/healthz", timeout=timeout, context=ctx) as r:
            return r.status == 200
    except Exception:
        return False


def _pythonw() -> str:
    exe = Path(sys.executable)
    w = exe.with_name("pythonw.exe")
    return str(w if w.exists() else exe)


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True,
                             creationflags=NO_WINDOW).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start(demo: bool = False, open_browser: bool = True, wait_seconds: int = 60) -> str:
    configure(demo)
    from app.core.config import get_settings
    s = get_settings()
    url = app_url(s)
    if responding(url):
        if open_browser:
            webbrowser.open(url)
        return url
    s.check_network_safety()
    logs = s.instance_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    if demo and not (s.instance_dir / "demo_users.txt").exists():
        seed = subprocess.run([_pythonw(), str(ROOT / "scripts" / "seed_demo.py")], cwd=ROOT, env=env,
                              capture_output=True, text=True, creationflags=NO_WINDOW)
        (logs / "demo_seed.log").write_text((seed.stdout or "") + (seed.stderr or ""), encoding="utf-8")
        if seed.returncode != 0:
            raise RuntimeError(f"Loading the demo data failed. Details: {logs / 'demo_seed.log'}")
    log_path = logs / "app.log"
    if log_path.exists():
        log_path.replace(logs / "app.previous.log")
    log = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen([_pythonw(), str(ROOT / "run.py")], cwd=ROOT, env=env, stdout=log,
                            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                            creationflags=NO_WINDOW | DETACHED, close_fds=True)
    (s.instance_dir / "app.pid").write_text(json.dumps({"pid": proc.pid, "url": url, "started": time.time()}))
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if responding(url):
            if open_browser:
                webbrowser.open(url)
            return url
        if proc.poll() is not None:
            log.close()
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-1200:]
            raise RuntimeError(f"The app stopped while starting.\n\n{tail}\n\nFull log: {log_path}")
        time.sleep(0.5)
    raise RuntimeError(f"The app did not answer within {wait_seconds} seconds. See {log_path}")


def stop(demo: bool = False) -> bool:
    configure(demo)
    from app.core.config import get_settings
    s = get_settings()
    pid_file = s.instance_dir / "app.pid"
    if not pid_file.exists():
        return False
    pid = json.loads(pid_file.read_text()).get("pid")
    stopped = False
    if pid and _pid_alive(pid):
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, creationflags=NO_WINDOW)
        else:
            os.kill(pid, 15)
        stopped = True
    pid_file.unlink(missing_ok=True)
    return stopped


def main(argv: list[str] | None = None) -> None:
    args = set(argv if argv is not None else sys.argv[1:])
    demo = "--demo" in args
    name = "The demo" if demo else "The app"
    try:
        if "--stop" in args:
            message(f"{name} has been stopped." if stop(demo) else f"{name} was not running (started by this launcher).")
        else:
            start(demo, open_browser="--no-browser" not in args)
    except Exception as exc:
        message(str(exc), error=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
