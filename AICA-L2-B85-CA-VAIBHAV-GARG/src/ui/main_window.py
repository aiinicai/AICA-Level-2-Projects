"""Main Application Window managing screen transitions, menus, and global state."""
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QStackedWidget, QMenuBar, QMenu, QMessageBox,
    QFileDialog, QWidget, QVBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon

from src.config import get_database_path, APP_NAME
from src.database.repository import Repository
from src.ui.theme import APP_STYLESHEET
from src.ui.screens.dashboard import DashboardScreen
from src.ui.screens.create_client import CreateClientScreen
from src.ui.screens.upload_financials import UploadFinancialsScreen
from src.ui.screens.results import ResultsScreen
from src.ui.dialogs.help_dialog import HelpDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Schedule III Ratio Analyser — Statutory Analytical Ratios")
        self.setMinimumSize(1100, 720)
        
        # Initialize Database & Repository
        db_path = get_database_path()
        self.repo = Repository(db_path)
        
        # Apply Global Theme
        self.setStyleSheet(APP_STYLESHEET)
        
        # Central Stacked Widget
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # Create Screens
        self.dashboard_screen = DashboardScreen(self.repo)
        self.create_client_screen = CreateClientScreen(self.repo)
        self.upload_screen = UploadFinancialsScreen()
        self.results_screen = ResultsScreen(self.repo)
        
        self.stack.addWidget(self.dashboard_screen)       # Index 0
        self.stack.addWidget(self.create_client_screen)   # Index 1
        self.stack.addWidget(self.upload_screen)          # Index 2
        self.stack.addWidget(self.results_screen)         # Index 3
        
        # Wire Screen Transitions
        self.dashboard_screen.create_new_client.connect(self.show_create_client)
        self.dashboard_screen.open_client.connect(self.on_open_existing_client)
        
        self.create_client_screen.back_to_dashboard.connect(self.show_dashboard)
        self.create_client_screen.client_created.connect(self.on_client_created)
        
        self.upload_screen.back_to_dashboard.connect(self.show_dashboard)
        self.upload_screen.analysis_completed.connect(self.on_analysis_completed)
        
        self.results_screen.back_to_dashboard.connect(self.show_dashboard)
        
        # Build Menus
        self.setup_menus()
        
        # Start at Dashboard
        self.show_dashboard()

    def setup_menus(self):
        menu_bar = self.menuBar()
        
        # File Menu
        file_menu = menu_bar.addMenu("&File")
        
        new_client_act = QAction("&New Client", self)
        new_client_act.setShortcut("Ctrl+N")
        new_client_act.triggered.connect(self.show_create_client)
        file_menu.addAction(new_client_act)
        
        file_menu.addSeparator()
        
        backup_act = QAction("&Backup Database...", self)
        backup_act.triggered.connect(self.on_backup_db)
        file_menu.addAction(backup_act)
        
        restore_act = QAction("&Restore Database...", self)
        restore_act.triggered.connect(self.on_restore_db)
        file_menu.addAction(restore_act)
        
        file_menu.addSeparator()
        
        exit_act = QAction("E&xit", self)
        exit_act.setShortcut("Ctrl+Q")
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)
        
        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        
        guide_act = QAction("&User Guide & Excel Formats", self)
        guide_act.triggered.connect(self.show_help_dialog)
        help_menu.addAction(guide_act)
        
        about_act = QAction("&About Schedule III Ratio Analyser", self)
        about_act.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_act)

    def show_dashboard(self):
        self.dashboard_screen.refresh_clients()
        self.stack.setCurrentIndex(0)

    def show_create_client(self):
        self.create_client_screen.reset_form()
        self.stack.setCurrentIndex(1)

    def on_client_created(self, client_id: int, client_name: str):
        self.upload_screen.set_client(client_id, client_name)
        self.stack.setCurrentIndex(2)

    def on_open_existing_client(self, client_id: int, client_name: str):
        self.upload_screen.set_client(client_id, client_name)
        self.stack.setCurrentIndex(2)

    def on_analysis_completed(self, payload: dict):
        self.results_screen.load_analysis_payload(payload)
        self.stack.setCurrentIndex(3)

    def on_backup_db(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Backup Database", "ScheduleIII_Backup.db", "SQLite Database (*.db)"
        )
        if file_path:
            try:
                self.repo.backup_to_file(file_path)
                QMessageBox.information(self, "Backup Successful", f"Database successfully backed up to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Backup Failed", f"Failed to backup database:\n{str(e)}")

    def on_restore_db(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Restore Database", "", "SQLite Database (*.db)"
        )
        if file_path:
            confirm = QMessageBox.question(
                self, "Confirm Restore",
                "Restoring database will replace all current client data. Are you sure you want to proceed?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                try:
                    self.repo.restore_from_file(file_path)
                    self.show_dashboard()
                    QMessageBox.information(self, "Restore Successful", "Database restored successfully.")
                except Exception as e:
                    QMessageBox.critical(self, "Restore Failed", f"Failed to restore database:\n{str(e)}")

    def show_help_dialog(self):
        dlg = HelpDialog(self)
        dlg.exec()

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "About Schedule III Ratio Analyser",
            "<b>Schedule III Ratio Analyser</b><br>"
            "Version 1.0.0<br><br>"
            "Offline desktop application for Chartered Accountants and statutory audit teams to compute "
            "and disclose Analytical Ratios mandated under Schedule III of the Companies Act, 2013.<br><br>"
            "Fully offline • No telemetry • Deterministic ambiguity resolution"
        )
