"""
TDS & TCS Certificate PDF Auto-Renamer - Application Launcher.
Supports both modern PyQt6 Desktop GUI and Headless Batch CLI modes.

Usage:
    # Desktop GUI:
    python main.py

    # Command Line Interface (CLI):
    python main.py --cli --input "C:/Certificates" --dry-run
    python main.py --cli --input "C:/Certificates" --template "{DeducteeName}_{FormType}_{Quarter}"
"""

import sys
import argparse
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from config import AppConfig
from ui.main_window import MainWindow
from core.batch_processor import BatchProcessorCLI


def run_gui(initial_folder: str = None):
    """Launch the modern PyQt6 desktop interface."""
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("TDS & TCS Certificate PDF Auto-Renamer")
    app.setOrganizationName("Indian Tax Compliance Tools")

    window = MainWindow(initial_folder=initial_folder)
    window.show()

    sys.exit(app.exec())


def run_cli(args):
    """Execute batch operations headlessly via terminal."""
    folder = Path(args.input)
    if not folder.exists():
        print(f"Error: Input directory does not exist: {folder}")
        sys.exit(1)

    config = AppConfig.load()
    if args.template:
        config.naming_template = args.template
    if args.subfolders:
        config.include_subfolders = True
    if args.output:
        config.execution_mode = "copy_to_folder"
        config.output_folder = str(args.output)

    print("=" * 70)
    print("TDS & TCS Certificate PDF Auto-Renamer (CLI Mode)")
    print("=" * 70)
    print(f"Source Folder:      {folder}")
    print(f"Naming Template:    {config.naming_template}")
    print(f"Include Subfolders: {config.include_subfolders}")
    print(f"Dry Run Mode:       {args.dry_run}")
    print("=" * 70)

    processor = BatchProcessorCLI(config=config)
    certs = processor.process_directory(folder=folder, dry_run=args.dry_run)

    valid_count = sum(1 for c in certs if c.deductee_name)
    print("=" * 70)
    print(f"Summary: {len(certs)} total files scanned, {valid_count} certificates identified.")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="TDS & TCS Certificate PDF Auto-Renamer - Income-tax Act, 1961 & 2025"
    )
    parser.add_argument("--cli", action="store_true", help="Run in headless Command Line Interface mode")
    parser.add_argument("-i", "--input", type=str, help="Input folder containing TDS/TCS PDF certificates")
    parser.add_argument("-o", "--output", type=str, help="Destination folder for copied/moved certificates")
    parser.add_argument("-t", "--template", type=str, help="Custom naming template e.g. '{DeducteeName}_{FormType}_{Quarter}'")
    parser.add_argument("-s", "--subfolders", action="store_true", help="Recursively scan subfolders")
    parser.add_argument("--dry-run", action="store_true", help="Simulate and print proposed filenames without modifying files")

    args = parser.parse_args()

    if args.cli:
        if not args.input:
            print("Error: --input argument is required in CLI mode.")
            sys.exit(1)
        run_cli(args)
    else:
        run_gui(initial_folder=args.input)
#!/usr/bin/env python3
"""
main.py
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
