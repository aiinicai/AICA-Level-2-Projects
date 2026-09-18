#!/usr/bin/env python3
"""Entry point for PDF Office Utility.

Run with:

    python app.py

See README.md for setup, dependencies, and how to build a standalone
Windows .exe with PyInstaller.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is importable regardless of the working directory
# the app was launched from (important once bundled by PyInstaller too).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication

from config.app_config import APP_NAME
from ui.app_context import AppContext
from ui.main_window import MainWindow
from ui.theme import apply_theme
from utils.logging_utils import setup_logging


def main() -> int:
    ctx = AppContext.create()
    setup_logging(ctx.config.get_log_dir())

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    apply_theme(app, ctx.config.settings.theme)

    window = MainWindow(ctx)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
