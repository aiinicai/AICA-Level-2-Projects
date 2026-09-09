"""
AI Auditor V8 - Desktop Application Entry Point
Starts the PyQt5 application, configures High-DPI scaling, and launches MainWindow.
"""

import sys
import os

# Enable High DPI scaling
from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtWidgets import QApplication, QMessageBox
from gui.main_window import MainWindow

def main():
    # Configure Qt High DPI support
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("AI Auditor V8")
    app.setOrganizationName("AuditAI")
    app.setApplicationVersion("8.0.0")

    window = MainWindow()
    window.show()

    # Optional: If file path passed as argument, auto-load it
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        window.page_upload._set_selected_file(sys.argv[1])
        window.page_upload._start_extraction()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
