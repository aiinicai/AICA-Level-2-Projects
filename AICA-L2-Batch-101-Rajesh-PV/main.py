"""Judgement Insights Analyser - application entry point.

Run with:  python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

MIN_PYTHON = (3, 10)
APP_DIR = Path(__file__).resolve().parent

REQUIRED_MODULES = {
    "customtkinter": "customtkinter",
    "pymupdf": "PyMuPDF",
    "google.genai": "google-genai",
    "docx": "python-docx",
    "reportlab": "reportlab",
    "PIL": "Pillow",
    "keyring": "keyring",
    "pytesseract": "pytesseract",
    "dotenv": "python-dotenv",
    "openpyxl": "openpyxl",
}
if sys.platform.startswith("win"):
    REQUIRED_MODULES["win32com.client"] = "pywin32"


def _fatal(message: str) -> None:
    """Show a startup error even if the GUI toolkit is unavailable."""
    print(f"\n[Judgement Insights Analyser] {message}\n", file=sys.stderr)
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("Judgement Insights Analyser", message)
        root.destroy()
    except Exception:
        pass
    sys.exit(1)


def _check_environment() -> None:
    if sys.version_info < MIN_PYTHON:
        _fatal(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer is required "
               f"(you have {sys.version.split()[0]}).")
    try:
        import tkinter  # noqa: F401
    except ImportError:
        _fatal("Tkinter is not available. On Linux install it with e.g. 'sudo apt install python3-tk'. "
               "On Windows/macOS reinstall Python from python.org with Tcl/Tk enabled.")
    missing, broken = _find_missing_packages()
    if missing:
        # Offer to install into *this* interpreter - the usual cause of a
        # "still missing after pip install" loop is that pip belonged to a
        # different Python installation than the one running the app.
        if _ask_to_install(missing) and _install_requirements():
            missing, broken = _find_missing_packages()
        if missing:
            _fatal(
                "These packages are not installed for the Python that runs this app:\n    "
                + ", ".join(missing)
                + f"\n\nThis app is running on:\n    {sys.executable}\n\n"
                "Install them for THIS Python by running (copy the whole line):\n"
                f'    "{sys.executable}" -m pip install -r "{APP_DIR / "requirements.txt"}"\n\n'
                "Note: plain 'pip install' may belong to a different Python installation."
            )
    if broken:
        details = "\n".join(f"  • {pkg}: {err}" for pkg, err in broken)
        _fatal(
            "Some packages are installed but failed to load:\n" + details
            + "\n\nTry reinstalling them for this Python:\n"
            f'    "{sys.executable}" -m pip install --force-reinstall -r "{APP_DIR / "requirements.txt"}"\n\n'
            "On Windows, if the error mentions a DLL, install the latest Microsoft Visual C++ "
            "Redistributable (x64) from Microsoft and restart."
        )


def _find_missing_packages() -> tuple[list[str], list[tuple[str, str]]]:
    """Return (not-installed packages, [(package, error)] for packages that fail to import)."""
    import importlib
    import importlib.util

    importlib.invalidate_caches()
    missing: list[str] = []
    broken: list[tuple[str, str]] = []
    for module, package in REQUIRED_MODULES.items():
        try:
            importlib.import_module(module)
        except ModuleNotFoundError as exc:
            # Distinguish "not installed" from "installed but a dependency is missing".
            root = module.split(".")[0]
            if exc.name and (exc.name == module or exc.name == root or module.startswith(exc.name + ".")):
                missing.append(package)
            else:
                broken.append((package, f"{type(exc).__name__}: {exc}"))
        except Exception as exc:  # DLL load failures, version conflicts, etc.
            broken.append((package, f"{type(exc).__name__}: {exc}"))
    return missing, broken


def _ask_to_install(missing: list[str]) -> bool:
    message = ("Some required packages are not installed for the Python running this app:\n\n    "
               + ", ".join(missing)
               + f"\n\nPython: {sys.executable}\n\nInstall them now? (Needs an internet connection; "
               "this can take a few minutes.)")
    print(f"\n[Judgement Insights Analyser] {message}\n")
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        answer = messagebox.askyesno("Judgement Insights Analyser - setup", message)
        root.destroy()
        return bool(answer)
    except Exception:
        return False


def _install_requirements() -> bool:
    """pip-install requirements.txt into the running interpreter, showing a small status window."""
    import subprocess
    import threading

    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r",
           str(APP_DIR / "requirements.txt")]
    print("Running:", " ".join(cmd))
    result: dict = {}

    def run():
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # no flashing console on Windows
            proc = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)
            result["ok"] = proc.returncode == 0
            result["output"] = (proc.stdout or "") + (proc.stderr or "")
        except Exception as exc:
            result["ok"], result["output"] = False, str(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    try:
        import tkinter

        win = tkinter.Tk()
        win.title("Judgement Insights Analyser - installing")
        win.geometry("460x120")
        tkinter.Label(win, text="Installing required packages...\nPlease wait, this can take a few minutes.",
                      font=("Segoe UI", 11), pady=30).pack()

        def poll():
            if worker.is_alive():
                win.after(300, poll)
            else:
                win.destroy()

        poll()
        win.mainloop()
    except Exception:
        worker.join()
    worker.join()

    output = result.get("output", "")
    print(output[-4000:])
    if not result.get("ok"):
        tail = "\n".join(output.strip().splitlines()[-12:])
        _show_error("Automatic installation failed. Last lines of the installer output:\n\n" + tail
                    + "\n\nIf you are behind a corporate proxy or firewall, ask IT to allow access to "
                      "pypi.org, or install the packages manually (see README).")
        return False
    return True


def _show_error(message: str) -> None:
    print(f"\n[Judgement Insights Analyser] {message}\n", file=sys.stderr)
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("Judgement Insights Analyser", message)
        root.destroy()
    except Exception:
        pass


def main() -> None:
    _check_environment()
    sys.path.insert(0, str(APP_DIR))

    from dotenv import load_dotenv

    load_dotenv(APP_DIR / ".env", override=False)

    import logging

    from judgment_analyzer.config import load_settings, migrate_legacy_data
    from judgment_analyzer.logging_setup import setup_logging
    from judgment_analyzer.ui.app import JudgmentAnalyzerApp

    migrated = migrate_legacy_data()  # before logging, so the log folder is created in the new place
    log_file = setup_logging()
    log = logging.getLogger("main")
    log.info("Starting Judgement Insights Analyser (Python %s)", sys.version.split()[0])
    if migrated:
        log.info("Copied earlier data to the new data folder: %s", ", ".join(migrated))
    settings = load_settings()
    try:
        app = JudgmentAnalyzerApp(settings, log_file=log_file)
        app.mainloop()
    except Exception as exc:  # last-resort handler
        log.exception("Fatal error")
        _fatal(f"The application stopped unexpectedly: {exc}\n\nSee the log file: {log_file}")


if __name__ == "__main__":
    main()
