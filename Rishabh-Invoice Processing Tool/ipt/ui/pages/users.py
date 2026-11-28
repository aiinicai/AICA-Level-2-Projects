"""User management (admin only)."""
from __future__ import annotations

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QInputDialog,
                               QLineEdit, QPushButton, QVBoxLayout)

from ipt.core.permissions import ROLES, PermissionDenied, has_permission
from ipt.services.auth_service import AuthError
from ipt.ui.helpers import confirm, error, fill_table, make_table, muted, selected_id, title
from ipt.ui.pages.base import BasePage


class UserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add user")
        lay = QVBoxLayout(self); form = QFormLayout()
        self.full_name = QLineEdit(); self.username = QLineEdit()
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password)
        self.role = QComboBox(); self.role.addItems(ROLES); self.role.setCurrentText("accountant")
        form.addRow("Full name", self.full_name); form.addRow("Username", self.username)
        form.addRow("Password (min 8)", self.password); form.addRow("Role", self.role)
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)


class UsersPage(BasePage):
    title_text = "Users"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("Users & Roles"))
        self.layout_.addWidget(muted("Admin: everything. Accountant: process, map, import, reconcile. "
                                     "Reviewer: view, approve and add remarks only."))
        bar = QHBoxLayout()
        self.btn_add = QPushButton("Add user"); self.btn_add.setObjectName("Primary")
        self.btn_role = QPushButton("Change role")
        self.btn_pwd = QPushButton("Reset password")
        self.btn_active = QPushButton("Activate / Deactivate")
        for b in (self.btn_add, self.btn_role, self.btn_pwd, self.btn_active):
            bar.addWidget(b)
        bar.addStretch(1)
        self.layout_.addLayout(bar)
        self.table = make_table(["Username", "Full name", "Role", "Status", "Last login"])
        self.layout_.addWidget(self.table, 1)
        self.btn_add.clicked.connect(self._add)
        self.btn_role.clicked.connect(self._role)
        self.btn_pwd.clicked.connect(self._pwd)
        self.btn_active.clicked.connect(self._active)

    def refresh(self):
        can = has_permission(self.s.ctx.user.role if self.s.ctx.user else None, "user.manage")
        for b in (self.btn_add, self.btn_role, self.btn_pwd, self.btn_active):
            b.setEnabled(can)
        us = self.s.auth.list_users() if can else []
        fill_table(self.table, [[u.username, u.full_name, u.role, "Active" if u.is_active else "Inactive",
                                 u.last_login_at.strftime("%d-%m-%Y %H:%M") if u.last_login_at else "-"]
                                for u in us], [u.id for u in us])

    def _run(self, fn):
        try:
            fn(); self.refresh()
        except (AuthError, PermissionDenied) as e:
            error(self, str(e))

    def _add(self):
        dlg = UserDialog(self)
        if dlg.exec():
            self._run(lambda: self.s.auth.create_user(dlg.username.text(), dlg.password.text(),
                                                      dlg.role.currentText(), dlg.full_name.text(), self.s.ctx.user))

    def _role(self):
        uid = selected_id(self.table)
        if not uid:
            error(self, "Select a user first"); return
        role, ok = QInputDialog.getItem(self, "Change role", "New role", list(ROLES), 0, False)
        if ok:
            self._run(lambda: self.s.auth.set_role(uid, role, self.s.ctx.user))

    def _pwd(self):
        uid = selected_id(self.table)
        if not uid:
            error(self, "Select a user first"); return
        pwd, ok = QInputDialog.getText(self, "Reset password", "New password (min 8)", QLineEdit.Password)
        if ok:
            self._run(lambda: self.s.auth.reset_password(uid, pwd, self.s.ctx.user))

    def _active(self):
        uid = selected_id(self.table)
        if not uid:
            error(self, "Select a user first"); return
        row = self.table.currentRow()
        active = self.table.item(row, 3).text() == "Active"
        if confirm(self, ("Deactivate" if active else "Activate") + " this user?"):
            self._run(lambda: self.s.auth.set_active(uid, not active, self.s.ctx.user))
