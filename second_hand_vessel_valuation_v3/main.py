# -*- coding: utf-8 -*-
"""
Second hand vessel valuation
Secondhand ship acquisition financial model.

Start the application with:  python main.py
(install_and_run.bat installs the required library and starts the app.)
"""
import subprocess
import sys


def _ensure_pyqt5():
    """Install PyQt5 with pip automatically if it is not already available."""
    try:
        import PyQt5  # noqa: F401
    except ImportError:
        print("PyQt5 not found - installing it with pip, please wait...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "PyQt5"])


if __name__ == "__main__":
    _ensure_pyqt5()
    from app_gui import main
    main()
