"""
LexSecure India Pro - Main Application Entrypoint
Enterprise Legal & Regulatory Intelligence Desktop Suite for Indian Business Entities
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from database.db_engine import DatabaseEngine
from data.seed_data import seed_enterprise_data
from ui.main_window import MainWindow

def main():
    # 1. Initialize SQLite Database & ensure seeded enterprise data
    db = DatabaseEngine.get_instance()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM organizations")
        count = cursor.fetchone()[0]
        if count == 0:
            print("[LexSecure India Pro] First run detected. Initializing Enterprise Database...")
            seed_enterprise_data(reset=False)

    # 2. Configure Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("LexSecure India Pro")
    app.setOrganizationName("LexSecure Enterprise LegalTech")

    # Set modern system typography
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # 3. Launch Master Window
    window = MainWindow()
    window.show()

    # 4. Start Event Loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
