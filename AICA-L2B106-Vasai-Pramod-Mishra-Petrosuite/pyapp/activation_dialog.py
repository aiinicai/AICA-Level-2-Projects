from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QApplication
)
from PySide6.QtCore import Qt
from auth import check_password
from license_common import get_machine_id, verify_activation_key


class ActivationDialog(QDialog):
    """
    Shown once, on the first run on a given PC. Requires:
      1. The Admin password (proves it's the software owner/distributor doing this)
      2. A valid Activation Key for THIS machine's Machine ID
    Only on success does self.machine_id / self.activation_key get set,
    which main.py then persists to SQLite so this screen never shows again
    on this PC.
    """

    def __init__(self):
        super().__init__()
        self.machine_id = get_machine_id()
        self.activation_key = None
        self.setWindowTitle("Activate this PC")
        self.setFixedWidth(440)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        layout = QVBoxLayout(self)

        title = QLabel("Activate Petrosuite on this PC")
        title.setStyleSheet("font-size:16px;font-weight:700;margin-bottom:4px;")
        layout.addWidget(title)

        info = QLabel(
            "This PC needs to be activated once before use. Share the Machine ID "
            "below with the software administrator to receive an Activation Key."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#5B6B78;margin-bottom:8px;")
        layout.addWidget(info)

        mid_row = QHBoxLayout()
        mid_label = QLabel("Machine ID:")
        mid_label.setStyleSheet("font-weight:600;")
        self.mid_value = QLineEdit(self.machine_id)
        self.mid_value.setReadOnly(True)
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self._copy_machine_id)
        mid_row.addWidget(mid_label)
        mid_row.addWidget(self.mid_value)
        mid_row.addWidget(copy_btn)
        layout.addLayout(mid_row)

        layout.addWidget(QLabel(""))  # spacer

        self.admin_pw = QLineEdit()
        self.admin_pw.setEchoMode(QLineEdit.Password)
        self.admin_pw.setPlaceholderText("Admin Password")
        layout.addWidget(self.admin_pw)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Activation Key (e.g. ABCD-1234-EF56-7890-1234)")
        self.key_input.returnPressed.connect(self._try_activate)
        layout.addWidget(self.key_input)

        activate_btn = QPushButton("Activate")
        activate_btn.clicked.connect(self._try_activate)
        layout.addWidget(activate_btn)

    def _copy_machine_id(self):
        QApplication.clipboard().setText(self.machine_id)

    def _try_activate(self):
        if check_password(self.admin_pw.text()) != "admin":
            QMessageBox.warning(self, "Activation failed", "Incorrect Admin password.")
            self.admin_pw.clear()
            return
        key = self.key_input.text().strip()
        if not verify_activation_key(self.machine_id, key):
            QMessageBox.warning(self, "Activation failed", "Invalid Activation Key for this machine.")
            self.key_input.clear()
            return
        self.activation_key = key
        self.accept()
