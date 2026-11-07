"""Agreement Compare - 2026 interface (PySide6 / Qt 6).   Run:  python main_qt.py"""
import os
import sys
import traceback
import warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def fail(title, text):
    """Show the problem in a window (Windows) and save it to a log file - so it is never silent."""
    log = os.path.join(HERE, "agreement_compare_error.log")
    try:
        with open(log, "w", encoding="utf-8") as f:
            f.write(f"Python {sys.version}\nExecutable: {sys.executable}\nFolder: {HERE}\n\n{text}\n")
    except OSError:
        pass
    print("\n" + title + "\n" + text + f"\n(Saved to {log})")
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"{text[-1500:]}\n\nDetails saved in:\n{log}", title, 0x10)
    except Exception:   # noqa
        pass
    return 1


def main():
    if not os.path.isfile(os.path.join(HERE, "app", "config.py")):
        return fail("Agreement Compare - wrong folder",
                    "The folder 'app' is missing next to this file. Extract the WHOLE zip first (right-click > Extract All) and run the launcher from the extracted folder - do not run it from inside the zip.\n"
                    f"Current folder: {HERE}")
    try:
        import PySide6  # noqa
    except ImportError:
        return fail("Agreement Compare - PySide6 missing", "PySide6 is not installed for this Python.\nInstall it with:\n    \"" + sys.executable + "\" -m pip install PySide6")
    try:
        if "--selfcheck" in sys.argv:
            from app.qt.selfcheck import main as sc
            return sc()
        from app.qt.window import run
        return run()
    except Exception:   # noqa
        return fail("Agreement Compare - could not start", traceback.format_exc())


if __name__ == "__main__":
    sys.exit(main())
