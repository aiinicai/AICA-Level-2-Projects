from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt


class CompanyDialog(QDialog):
    """
    Lets the user pick which company/client to open, or create a new one.
    On success, self.company_id / self.company_name are set.
    """

    def __init__(self, db, allow_cancel: bool = True):
        super().__init__()
        self.db = db
        self.company_id = None
        self.company_name = None
        self.setWindowTitle("Select Company")
        self.setFixedSize(420, 420)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        if not allow_cancel:
            # First-run (no companies exist yet) — must create one to proceed.
            self.setWindowFlag(Qt.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)

        title = QLabel("Select a company to open")
        title.setStyleSheet("font-size:15px;font-weight:700;")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(lambda _: self._open_selected())
        layout.addWidget(self.list_widget)
        self._reload_list()

        open_btn = QPushButton("Open Selected Company")
        open_btn.clicked.connect(self._open_selected)
        layout.addWidget(open_btn)

        sep = QLabel("— or —")
        sep.setAlignment(Qt.AlignCenter)
        sep.setStyleSheet("color:#8A97A3;margin:6px 0;")
        layout.addWidget(sep)

        new_row = QHBoxLayout()
        self.new_name_input = QLineEdit()
        self.new_name_input.setPlaceholderText("New company / client name")
        self.new_name_input.returnPressed.connect(self._create_and_open)
        new_row.addWidget(self.new_name_input)
        create_btn = QPushButton("Create New")
        create_btn.clicked.connect(self._create_and_open)
        new_row.addWidget(create_btn)
        layout.addLayout(new_row)

    def _reload_list(self):
        self.list_widget.clear()
        for c in self.db.list_companies():
            item = QListWidgetItem(c["name"])
            item.setData(Qt.UserRole, c["id"])
            self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _open_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, "Select a company", "Choose a company from the list, or create a new one.")
            return
        self.company_id = item.data(Qt.UserRole)
        self.company_name = item.text()
        self.accept()

    def _create_and_open(self):
        name = self.new_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Name required", "Enter a name for the new company.")
            return
        try:
            new_id = self.db.create_company(name)
        except ValueError as e:
            QMessageBox.warning(self, "Could not create company", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, "Could not create company", f"A company with this name may already exist.\n({e})")
            return
        self.company_id = new_id
        self.company_name = name
        self.accept()
