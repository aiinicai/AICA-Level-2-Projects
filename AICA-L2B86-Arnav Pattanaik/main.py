"""
DISCOM Audit Data Compiler — desktop application entry point.

Run with:  python main.py
Or via the packaged .exe built by build_exe.bat / PyInstaller.
"""

import sys

from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.styles import APP_STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    app.setApplicationName("DISCOM Audit Data Compiler")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
