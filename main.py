"""
BharatBill Enterprise GST – Main Application Entrypoint.
Production-ready Indian GST Billing, Invoicing, Inventory, and Accounting Application.
"""
from __future__ import annotations
import sys
import os
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont

from billing_app.database.connection import init_database, get_db_session
from billing_app.services.auth_service import AuthService
from billing_app.database.demo_data import seed_demo_data_if_needed
from billing_app.ui.theme import PROFESSIONAL_LIGHT_THEME
from billing_app.ui.login_screen import LoginScreen
from billing_app.ui.main_window import MainWindow
from billing_app.utils.logger import get_logger

logger = get_logger("Main")


def main():
    # Configure High DPI scaling
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("BharatBill Enterprise GST")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("BharatBill")
    app.setOrganizationDomain("bharatbill.in")

    # Set default modern font and theme stylesheet
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(PROFESSIONAL_LIGHT_THEME)

    # Initialize Database Schema & Initial Data
    try:
        init_database()
        with get_db_session() as session:
            AuthService.ensure_default_admin(session)
            seed_demo_data_if_needed(session)
        logger.info("Database and initial data ready.")
    except Exception as e:
        logger.error("Initialization error: %s", e)

    # Display Login Screen
    login_dialog = LoginScreen()
    authenticated_user = None

    def on_login_success(user):
        nonlocal authenticated_user
        authenticated_user = user

    login_dialog.login_success.connect(on_login_success)

    if login_dialog.exec() == LoginScreen.Accepted and authenticated_user:
        # Launch Main Window
        main_win = MainWindow(current_user=authenticated_user)
        main_win.showMaximized()
        return app.exec()
    else:
        # Cancelled login
        return 0


if __name__ == "__main__":
    sys.exit(main())
