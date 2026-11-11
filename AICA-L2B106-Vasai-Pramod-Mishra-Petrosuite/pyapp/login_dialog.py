from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
from auth import check_password


class LoginDialog(QDialog):
    """Modal login gate. On success, self.role is 'admin' or 'user'."""

    def __init__(self, company_label: str = "Petrosuite"):
        super().__init__()
        self.role = None
        self.setWindowTitle("Login")
        self.setFixedWidth(360)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        layout = QVBoxLayout(self)

        title = QLabel(company_label)
        title.setStyleSheet("font-size:16px;font-weight:700;margin-bottom:4px;")
        layout.addWidget(title)

        sub = QLabel("Enter your password to continue")
        sub.setStyleSheet("color:#5B6B78;margin-bottom:10px;")
        layout.addWidget(sub)

        self.pw_input = QLineEdit()
        self.pw_input.setEchoMode(QLineEdit.Password)
        self.pw_input.setPlaceholderText("Password")
        self.pw_input.returnPressed.connect(self._try_login)
        layout.addWidget(self.pw_input)

        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self._try_login)
        layout.addWidget(self.login_btn)

        self.pw_input.setFocus()

    def _try_login(self):
        role = check_password(self.pw_input.text())
        if role is None:
            QMessageBox.warning(self, "Login failed", "Incorrect password. Please try again.")
            self.pw_input.clear()
            self.pw_input.setFocus()
            return
        self.role = role
        self.accept()
