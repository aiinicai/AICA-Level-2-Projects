"""
Band Baaja Baraati - Wedding Planning, Costing & Customer Management

>>> RUN THIS FILE:   double-click it, or run   python Band_Baaja_Baraati.py

On first start it installs any missing packages automatically (internet required).
If something fails, a message box (and a log file) tells you why instead of closing silently.
"""
import os
import subprocess
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
os.chdir(HERE)

REQUIRED = {"PySide6": "PySide6", "sqlalchemy": "SQLAlchemy", "alembic": "alembic", "reportlab": "reportlab"}
LOG = Path(os.environ.get("WP_DATA_DIR") or Path.home() / ".wedding_planner") / "startup_error.log"


def show_error(title: str, text: str) -> None:
    """Show the problem in a window if possible, always print it, and keep the console open."""
    print(f"\n*** {title} ***\n{text}\n")
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        LOG.write_text(f"{title}\n\n{text}\n", encoding="utf-8")
        print(f"(details saved to {LOG})")
    except OSError:
        pass
    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror(title, text[-1500:])
        root.destroy()
    except Exception:
        try:
            input("Press Enter to close...")
        except EOFError:
            pass


def missing_packages() -> list:
    import importlib.util
    return [pip for mod, pip in REQUIRED.items() if importlib.util.find_spec(mod) is None]


def install(packages: list) -> None:
    print("Installing required packages (first start only): " + ", ".join(packages))
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"] + packages
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(
            "Could not install: " + ", ".join(packages) + ".\n\n"
            f"Python in use: {sys.version.split()[0]} ({sys.executable}).\n"
            "Check your internet connection. PySide6 supports Python 3.9 to 3.13; "
            "if you have a newer Python, install Python 3.12 from python.org and try again.")


def run() -> int:
    if sys.version_info < (3, 9):
        raise RuntimeError(f"Python 3.9 or newer is required (you have {sys.version.split()[0]}).")
    todo = missing_packages()
    if todo:
        install(todo)
        todo = missing_packages()
        if todo:
            raise RuntimeError("Packages still missing after installation: " + ", ".join(todo))
    from weddingplanner.__main__ import main
    return main()


if __name__ == "__main__":
    try:
        code = run()
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 0
    except BaseException:
        show_error("Band Baaja Baraati could not start", traceback.format_exc())
        code = 1
    sys.exit(code)
