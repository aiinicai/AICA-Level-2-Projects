import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QMessageBox, QApplication)
from PyQt5.QtCore import Qt
from app.license_manager import activate_license, load_config
from app.gui.styles import MAIN_STYLESHEET

class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PuruNiti Smart Billing system - Software Activation")
        self.resize(450, 220)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint) # Remove ? help button
        self.setStyleSheet(MAIN_STYLESHEET)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title Label
        title = QLabel("Product Activation")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Prompt Text
        desc = QLabel(
            "An active License Key is required to run this application.\n"
            "Please enter your 16-character license key below:"
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #475569; font-size: 13px; font-weight: normal;")
        layout.addWidget(desc)

        # License Input
        self.txt_key = QLineEdit()
        self.txt_key.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.txt_key.setAlignment(Qt.AlignCenter)
        self.txt_key.setStyleSheet(
            "font-size: 16px; letter-spacing: 2px; font-weight: bold; padding: 8px;"
        )
        layout.addWidget(self.txt_key)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.btn_exit = QPushButton("Exit App")
        self.btn_exit.setObjectName("btnDanger")
        self.btn_exit.setProperty("danger", True)
        self.btn_exit.clicked.connect(self.reject)

        self.btn_activate = QPushButton("Activate Software")
        self.btn_activate.setObjectName("btnPrimary")
        self.btn_activate.setProperty("primary", True)
        self.btn_activate.clicked.connect(self.handle_activation)

        buttons_layout.addWidget(self.btn_exit, 1)
        buttons_layout.addWidget(self.btn_activate, 2)
        layout.addLayout(buttons_layout)

    def handle_activation(self):
        key = self.txt_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Activation Error", "License Key field cannot be empty.")
            self.txt_key.setFocus()
            return

        success, msg = activate_license(key)
        if success:
            QMessageBox.information(self, "Activation Successful", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "Invalid Key", msg)
            self.txt_key.clear()
            self.txt_key.setFocus()
