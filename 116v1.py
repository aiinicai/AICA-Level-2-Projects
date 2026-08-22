#!/usr/bin/env python3
"""
main.py
=======
Entry point for the Ind AS 116 Lease Accounting Suite (GUI edition).

On first run (or whenever a required package is missing), a live
installation log window is shown while pandas / openpyxl /
python-dateutil are installed automatically. On subsequent runs,
with dependencies already present, the app starts straight into the
main window.

Run with:
    python main.py
"""

import sys
from pathlib import Path

# Ensure the package directory is importable when run as a plain script
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ind_as_116.gui import launch_app  # noqa: E402  (import after sys.path setup)


def main():
    try:
        launch_app()
    except ImportError as exc:
        # tkinter itself missing (rare: some minimal Linux Python builds
        # ship without it). This cannot be pip-installed — it requires
        # a system package.
        print("ERROR: Could not start the GUI.")
        print(f"Details: {exc}")
        print()
        print("If this mentions 'tkinter', install it via your OS package")
        print("manager, e.g. on Debian/Ubuntu:  sudo apt install python3-tk")
        print("then re-run:  python main.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
