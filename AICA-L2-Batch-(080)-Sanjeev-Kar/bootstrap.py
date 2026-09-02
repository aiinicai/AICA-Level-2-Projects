"""
bootstrap.py
-------------
First-run dependency bootstrapper.

Per project convention, third-party dependencies must be detected and
installed automatically on first execution, with the installation log
visible to the user (never a silent background install). This module has
NO third-party imports of its own (stdlib only), so it can run before any
dependency is available, and it is skipped entirely when running from a
frozen PyInstaller .exe (which already bundles every dependency at build
time, and has no `pip` to call anyway).
"""

from __future__ import annotations

import importlib
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext
from typing import List, Tuple

# (import_name, pip_spec) - import_name is what we `import` to test
# presence; pip_spec is what we hand to `pip install`. Keep this in sync
# with requirements.txt.
REQUIRED_PACKAGES: List[Tuple[str, str]] = [
    ("argon2", "argon2-cffi>=23.1.0"),
    ("cryptography", "cryptography>=42.0.0"),
    ("numpy", "numpy>=1.24.0"),
    ("PIL", "Pillow>=10.0.0"),
    ("cv2", "opencv-contrib-python>=4.9.0"),
]


def _is_frozen() -> bool:
    """True when running inside a PyInstaller-built .exe."""
    return bool(getattr(sys, "frozen", False))


def _missing_packages() -> List[Tuple[str, str]]:
    missing = []
    for import_name, pip_spec in REQUIRED_PACKAGES:
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append((import_name, pip_spec))
    return missing


def ensure_dependencies() -> bool:
    """Ensures every required package is importable, installing whatever is
    missing (with a visible log window) if needed.

    Returns True if the app should proceed to start normally in THIS
    process. Returns False if the user cancelled or an install failed.
    Raises _RestartRequired if packages were installed and the process
    must be restarted (a freshly-started interpreter is the only reliable
    way to pick up a just-installed C-extension package)."""
    if _is_frozen():
        return True

    missing = _missing_packages()
    if not missing:
        return True

    ok = _run_installer_ui(missing)
    if not ok:
        return False

    still_missing = _missing_packages()
    if still_missing:
        return False

    raise _RestartRequired()


class _RestartRequired(Exception):
    """Signals that dependencies were freshly installed and the app must
    restart in a new process to import them cleanly."""


def _run_installer_ui(missing: List[Tuple[str, str]]) -> bool:
    root = tk.Tk()
    root.title("Folder Lock - First-Time Setup")
    root.geometry("640x420")
    root.resizable(False, False)

    tk.Label(
        root,
        text=f"Installing {len(missing)} required package(s) for first-time use...",
        font=("Segoe UI", 11, "bold"),
        pady=8,
    ).pack()

    log_box = scrolledtext.ScrolledText(root, width=76, height=20, state="disabled", font=("Consolas", 9))
    log_box.pack(padx=10, pady=6, fill="both", expand=True)

    status_var = tk.StringVar(value="Starting installation...")
    tk.Label(root, textvariable=status_var, anchor="w", padx=10).pack(fill="x")

    result = {"ok": False}
    close_btn = tk.Button(root, text="Close", state="disabled", command=root.destroy)
    close_btn.pack(pady=(0, 10))

    log_queue: "queue.Queue" = queue.Queue()
    current_proc: dict = {"proc": None}
    cancelled = threading.Event()

    def append_log(line: str) -> None:
        log_box.config(state="normal")
        log_box.insert("end", line)
        log_box.see("end")
        log_box.config(state="disabled")

    def worker() -> None:
        all_ok = True
        for import_name, pip_spec in missing:
            if cancelled.is_set():
                all_ok = False
                break
            log_queue.put(("status", f"Installing {pip_spec} ..."))
            log_queue.put(("log", f"\n$ {sys.executable} -m pip install {pip_spec}\n"))
            try:
                proc = subprocess.Popen(
                    [sys.executable, "-m", "pip", "install", pip_spec],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                current_proc["proc"] = proc
                for line in proc.stdout:
                    log_queue.put(("log", line))
                proc.wait()
                current_proc["proc"] = None
                if cancelled.is_set():
                    all_ok = False
                    break
                if proc.returncode != 0:
                    all_ok = False
                    log_queue.put(("log", f"\n[FAILED] {pip_spec} (exit code {proc.returncode})\n"))
            except Exception as exc:
                all_ok = False
                log_queue.put(("log", f"\n[ERROR] Could not run pip for {pip_spec}: {exc}\n"))
        log_queue.put(("done", all_ok))

    threading.Thread(target=worker, daemon=True).start()

    def poll() -> None:
        if not root.winfo_exists():
            return
        try:
            while True:
                kind, payload = log_queue.get_nowait()
                if kind == "log":
                    append_log(payload)
                elif kind == "status":
                    status_var.set(payload)
                elif kind == "done":
                    result["ok"] = bool(payload)
                    status_var.set(
                        "All packages installed successfully. Restarting..."
                        if result["ok"]
                        else "One or more packages failed to install. See log above."
                    )
                    close_btn.config(state="normal")
                    if result["ok"]:
                        root.after(1200, root.destroy)
                    return
        except queue.Empty:
            pass
        root.after(80, poll)

    def on_close() -> None:
        cancelled.set()
        proc = current_proc["proc"]
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.after(80, poll)
    root.mainloop()

    return result["ok"]
