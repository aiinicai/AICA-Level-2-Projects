from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QRadioButton, QButtonGroup, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt


class ImportBackupDialog(QDialog):
    """
    Shown after picking a backup .json file to import. Forces an explicit
    choice: bring this data in as a brand-new company, or overwrite the
    data of an existing company. Never silently imports into "whatever
    happens to be open right now".

    On success:
      self.mode == 'new'      -> self.new_company_name is set
      self.mode == 'overwrite'-> self.target_company_id is set
    """

    def __init__(self, db, suggested_name: str = ""):
        super().__init__()
        self.db = db
        self.mode = None
        self.new_company_name = None
        self.target_company_id = None

        self.setWindowTitle("Import Backup")
        self.setFixedWidth(440)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        layout = QVBoxLayout(self)

        title = QLabel("How should this backup be imported?")
        title.setStyleSheet("font-size:15px;font-weight:700;")
        layout.addWidget(title)

        self.group = QButtonGroup(self)

        # --- Option 1: New company ---
        self.radio_new = QRadioButton("Create a NEW company from this backup")
        self.radio_new.setChecked(True)
        self.group.addButton(self.radio_new)
        layout.addWidget(self.radio_new)

        self.new_name_input = QLineEdit()
        self.new_name_input.setPlaceholderText("Company name")
        if suggested_name:
            self.new_name_input.setText(suggested_name)
        layout.addWidget(self.new_name_input)

        # --- Option 2: Overwrite existing company ---
        self.radio_overwrite = QRadioButton("OVERWRITE an existing company's data with this backup")
        self.group.addButton(self.radio_overwrite)
        layout.addWidget(self.radio_overwrite)

        self.existing_combo = QComboBox()
        companies = self.db.list_companies()
        for c in companies:
            self.existing_combo.addItem(c["name"], c["id"])
        self.existing_combo.setEnabled(False)
        layout.addWidget(self.existing_combo)

        self.warning_label = QLabel(
            "⚠ This will permanently replace ALL existing data for the selected "
            "company. This cannot be undone."
        )
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color:#B91C1C;font-weight:600;")
        self.warning_label.setVisible(False)
        layout.addWidget(self.warning_label)

        self.radio_new.toggled.connect(self._on_mode_toggled)
        self.radio_overwrite.toggled.connect(self._on_mode_toggled)

        # --- Buttons ---
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        self.confirm_btn = QPushButton("Import")
        self.confirm_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(self.confirm_btn)
        layout.addLayout(btn_row)

        if not companies:
            # No existing companies at all — overwrite option is moot.
            self.radio_overwrite.setEnabled(False)
            self.existing_combo.setEnabled(False)

    def _on_mode_toggled(self):
        is_new = self.radio_new.isChecked()
        self.new_name_input.setEnabled(is_new)
        self.existing_combo.setEnabled(not is_new)
        self.warning_label.setVisible(not is_new)

    def _on_confirm(self):
        if self.radio_new.isChecked():
            name = self.new_name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "Name required", "Enter a name for the new company.")
                return
            self.mode = "new"
            self.new_company_name = name
            self.accept()
        else:
            if self.existing_combo.count() == 0:
                QMessageBox.warning(self, "No companies", "There are no existing companies to overwrite.")
                return
            company_id = self.existing_combo.currentData()
            company_name = self.existing_combo.currentText()
            confirm = QMessageBox.warning(
                self, "Confirm overwrite",
                f"This will permanently replace ALL existing data for "
                f"'{company_name}' with the contents of this backup.\n\n"
                f"This cannot be undone. Continue?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return
            self.mode = "overwrite"
            self.target_company_id = company_id
            self.accept()
