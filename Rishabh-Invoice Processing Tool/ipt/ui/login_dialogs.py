"""First-run admin setup and login dialogs."""
from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout)

from ipt.services.auth_service import AuthError, AuthService
from ipt.ui.helpers import muted, title


class FirstRunDialog(QDialog):
    """Shown once, when no users exist: creates the first admin."""

    def __init__(self, auth: AuthService, parent=None):
        super().__init__(parent)
        self.auth = auth
        self.setWindowTitle("IPT - First-time setup")
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        lay.addWidget(title("Create the administrator account"))
        lay.addWidget(muted("This account manages users, companies and settings. Keep the password safe; "
                            "it cannot be recovered."))
        form = QFormLayout()
        self.full_name = QLineEdit()
        self.username = QLineEdit("admin")
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password)
        self.confirm = QLineEdit(); self.confirm.setEchoMode(QLineEdit.Password)
        form.addRow("Full name", self.full_name)
        form.addRow("Username", self.username)
        form.addRow("Password (min 8)", self.password)
        form.addRow("Confirm password", self.confirm)
        lay.addLayout(form)
        self.err = QLabel(); self.err.setObjectName("ErrorText")
        lay.addWidget(self.err)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._create)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _create(self):
        if self.password.text() != self.confirm.text():
            self.err.setText("Passwords do not match")
            return
        try:
            self.auth.create_user(self.username.text(), self.password.text(), "admin", self.full_name.text())
        except AuthError as e:
            self.err.setText(str(e))
            return
        self.accept()


class LoginDialog(QDialog):
    def __init__(self, auth: AuthService, parent=None):
        super().__init__(parent)
        self.auth = auth
        self.user = None
        self.setWindowTitle("IPT - Login")
        self.setMinimumWidth(360)
        lay = QVBoxLayout(self)
        lay.addWidget(title("IPT - Invoice Processing Tool"))
        lay.addWidget(muted("Sign in to continue"))
        form = QFormLayout()
        self.username = QLineEdit()
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password)
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        lay.addLayout(form)
        self.err = QLabel(); self.err.setObjectName("ErrorText")
        lay.addWidget(self.err)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Sign in")
        bb.accepted.connect(self._login)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.password.returnPressed.connect(self._login)

    def _login(self):
        try:
            self.user = self.auth.authenticate(self.username.text(), self.password.text())
        except AuthError as e:
            self.err.setText(str(e))
            self.password.clear()
            return
        self.accept()
