"""First-run dependency bootstrap progress experience.

Uses only Python stdlib so it can run before third-party application dependencies are
available. On Windows/source installations it presents a small progress window; if Tk is
unavailable it falls back to an informative console flow.
"""
from __future__ import annotations

import queue
import threading
from pathlib import Path

from app.core.bootstrap import install_missing, missing_dependencies


def dependencies_missing(project_root: Path) -> bool:
    requirements = project_root / "requirements.txt"
    return requirements.is_file() and bool(missing_dependencies(requirements))


def run_bootstrap_progress(project_root: Path) -> None:
    """Install missing pinned dependencies while visibly reporting progress."""
    requirements = project_root / "requirements.txt"
    if not requirements.is_file():
        raise RuntimeError("IBC Expert requirements.txt is missing from the application folder.")
    if not dependencies_missing(project_root):
        return

    try:
        import tkinter as tk
        from tkinter import messagebox, ttk
    except Exception:
        install_missing(project_root, progress=print)
        return

    messages: queue.Queue[tuple[str, str]] = queue.Queue()
    state = {"done": False, "error": None}

    root = tk.Tk()
    root.title("IBC Expert — First-run setup")
    root.geometry("620x360")
    root.resizable(False, False)
    root.protocol("WM_DELETE_WINDOW", lambda: None)

    outer = ttk.Frame(root, padding=22)
    outer.pack(fill="both", expand=True)
    ttk.Label(outer, text="IBC Expert first-run setup", font=("Segoe UI", 16, "bold")).pack(anchor="w")
    ttk.Label(
        outer,
        text=("Required local components are being prepared. The application will open "
              "automatically when setup is complete."),
        wraplength=560,
    ).pack(anchor="w", pady=(8, 14))
    progress = ttk.Progressbar(outer, mode="indeterminate")
    progress.pack(fill="x")
    progress.start(12)
    status = ttk.Label(outer, text="Checking required packages …")
    status.pack(anchor="w", pady=(12, 8))
    log = tk.Text(outer, height=10, width=76, state="disabled", wrap="word")
    log.pack(fill="both", expand=True)

    def report(text: str) -> None:
        messages.put(("message", str(text)))

    def worker() -> None:
        try:
            install_missing(project_root, progress=report)
            messages.put(("done", "Dependency setup completed successfully."))
        except Exception as exc:  # shown to the user in this bootstrap-only UI
            messages.put(("error", str(exc)))

    def append(text: str) -> None:
        log.configure(state="normal")
        log.insert("end", text + "\n")
        log.see("end")
        log.configure(state="disabled")
        status.configure(text=text[:110])

    def poll() -> None:
        try:
            while True:
                kind, text = messages.get_nowait()
                append(text)
                if kind == "done":
                    state["done"] = True
                    progress.stop()
                    root.after(350, root.destroy)
                    return
                if kind == "error":
                    state["error"] = text
                    progress.stop()
                    messagebox.showerror(
                        "IBC Expert setup failed",
                        text + "\n\nThe application has not been started. Correct the dependency issue and try again.",
                    )
                    root.destroy()
                    return
        except queue.Empty:
            pass
        root.after(100, poll)

    threading.Thread(target=worker, name="IBCExpertBootstrap", daemon=True).start()
    root.after(100, poll)
    root.mainloop()
    if state["error"]:
        raise RuntimeError(str(state["error"]))
