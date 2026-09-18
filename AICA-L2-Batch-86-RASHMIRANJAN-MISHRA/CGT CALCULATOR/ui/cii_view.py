"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
CII Master Management View (PyQt6)
Author: Senior Python Developer & Tax-Audit Software Architect
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFileDialog,
    QDialog,
    QFormLayout,
    QSpinBox,
    QCheckBox,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt

from cii_master import get_all_cii, add_or_update_cii, delete_cii, export_cii_to_excel, import_cii_from_excel, normalize_fy


class CIIDialog(QDialog):
    """Dialog for adding or editing a CII record."""

    def __init__(self, parent=None, fy: str = "", cii: int = 100, notified: bool = True, ref: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Edit CII Record" if fy else "Add New CII Record")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.fy_edit = QLineEdit(fy)
        self.fy_edit.setPlaceholderText("e.g. 2026-27")
        if fy:
            self.fy_edit.setReadOnly(True)
        form.addRow("Financial Year (YYYY-YY):*", self.fy_edit)

        self.cii_spin = QSpinBox()
        self.cii_spin.setRange(1, 100000)
        self.cii_spin.setValue(cii)
        form.addRow("CII Value:*", self.cii_spin)

        self.notified_chk = QCheckBox("Officially Notified by CBDT")
        self.notified_chk.setChecked(notified)
        form.addRow("Notification Status:", self.notified_chk)

        self.ref_edit = QLineEdit(ref)
        self.ref_edit.setPlaceholderText("e.g. CBDT Notification No. XX/YYYY")
        form.addRow("Notification Ref:", self.ref_edit)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _validate_and_accept(self):
        fy = normalize_fy(self.fy_edit.text().strip())
        if not fy or len(fy) != 7 or "-" not in fy:
            QMessageBox.warning(self, "Invalid FY", "Please enter a valid Financial Year format: YYYY-YY (e.g. 2026-27).")
            return
        self.accept()

    def get_data(self):
        return (
            normalize_fy(self.fy_edit.text().strip()),
            self.cii_spin.value(),
            1 if self.notified_chk.isChecked() else 0,
            self.ref_edit.text().strip(),
        )


class CIIMasterView(QWidget):
    """Interactive management table for Cost Inflation Index (CII) master data."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Title
        title_box = QHBoxLayout()
        vbox = QVBoxLayout()
        lbl_title = QLabel("COST INFLATION INDEX (CII) MASTER")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #1E3A8A;")
        lbl_sub = QLabel("Official notifications under Section 48 Explanation (v) of the Income-tax Act, 1961.")
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B;")
        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_sub)
        title_box.addLayout(vbox)
        title_box.addStretch()

        # Action Buttons
        self.btn_add = QPushButton("➕ Add CII")
        self.btn_add.clicked.connect(self._add_cii)
        title_box.addWidget(self.btn_add)

        self.btn_edit = QPushButton("✏ Edit")
        self.btn_edit.setProperty("class", "secondaryBtn")
        self.btn_edit.clicked.connect(self._edit_selected_cii)
        title_box.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("🗑 Delete")
        self.btn_delete.setProperty("class", "dangerBtn")
        self.btn_delete.clicked.connect(self._delete_selected_cii)
        title_box.addWidget(self.btn_delete)

        self.btn_import = QPushButton("📥 Import from Excel")
        self.btn_import.setProperty("class", "secondaryBtn")
        self.btn_import.clicked.connect(self._import_excel)
        title_box.addWidget(self.btn_import)

        self.btn_export = QPushButton("📤 Export to Excel")
        self.btn_export.setProperty("class", "successBtn")
        self.btn_export.clicked.connect(self._export_excel)
        title_box.addWidget(self.btn_export)

        layout.addLayout(title_box)

        # Search / Filter Bar
        search_box = QHBoxLayout()
        search_box.addWidget(QLabel("Search Financial Year:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type FY (e.g. 2015-16)...")
        self.search_edit.textChanged.connect(self._filter_table)
        search_box.addWidget(self.search_edit)
        search_box.addStretch()
        layout.addLayout(search_box)

        # CII Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Financial Year",
            "Cost Inflation Index (CII)",
            "Notification Status",
            "CBDT Notification Reference",
            "Last Updated",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.cellDoubleClicked.connect(lambda r, c: self._edit_selected_cii())
        layout.addWidget(self.table)

        self.load_data()

    def load_data(self):
        records = get_all_cii()
        self.all_records = records
        self._populate_table(records)

    def _populate_table(self, records):
        self.table.setRowCount(len(records))
        for r_idx, r in enumerate(records):
            item_fy = QTableWidgetItem(r["financial_year"])
            item_fy.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 0, item_fy)

            item_cii = QTableWidgetItem(str(r["cii_value"]))
            item_cii.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            font = item_cii.font()
            font.setBold(True)
            item_cii.setFont(font)
            self.table.setItem(r_idx, 1, item_cii)

            is_notif = r["is_notified"] == 1
            item_status = QTableWidgetItem("Notified" if is_notif else "Provisional / User Added")
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 2, item_status)

            self.table.setItem(r_idx, 3, QTableWidgetItem(r["notification_ref"] or "—"))
            self.table.setItem(r_idx, 4, QTableWidgetItem(str(r["updated_at"])[:16]))

    def _filter_table(self, query: str):
        q = query.strip().lower()
        if not q:
            self._populate_table(self.all_records)
            return
        filtered = [r for r in self.all_records if q in r["financial_year"].lower() or q in str(r["cii_value"])]
        self._populate_table(filtered)

    def _add_cii(self):
        dlg = CIIDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            fy, cii, notif, ref = dlg.get_data()
            try:
                add_or_update_cii(fy, cii, notif, ref)
                self.load_data()
                QMessageBox.information(self, "Success", f"CII for FY {fy} successfully saved with value {cii}.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _edit_selected_cii(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a CII row to edit.")
            return

        fy = self.table.item(row, 0).text()
        cii = int(self.table.item(row, 1).text())
        notif = "Notified" in self.table.item(row, 2).text()
        ref = self.table.item(row, 3).text()

        dlg = CIIDialog(self, fy=fy, cii=cii, notified=notif, ref=ref)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            _, new_cii, new_notif, new_ref = dlg.get_data()
            try:
                add_or_update_cii(fy, new_cii, new_notif, new_ref)
                self.load_data()
                QMessageBox.information(self, "Updated", f"CII for FY {fy} updated to {new_cii}.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _delete_selected_cii(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a CII row to delete.")
            return

        fy = self.table.item(row, 0).text()
        res = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the Cost Inflation Index for FY {fy}?\n"
            f"Calculations relying on this year may fail if not re-added.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            delete_cii(fy)
            self.load_data()
            QMessageBox.information(self, "Deleted", f"CII for FY {fy} deleted.")

    def _export_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export CII Master to Excel", "CII_Master_Table.xlsx", "Excel Files (*.xlsx)")
        if file_path:
            try:
                export_cii_to_excel(file_path)
                QMessageBox.information(self, "Export Successful", f"CII Master successfully exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")

    def _import_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import CII from Excel", "", "Excel Files (*.xlsx *.xls)")
        if file_path:
            count, errors = import_cii_from_excel(file_path)
            self.load_data()
            if errors:
                err_msg = "\n".join(errors[:10])
                QMessageBox.warning(self, "Import Completed with Warnings", f"Imported {count} records.\nErrors:\n{err_msg}")
            else:
                QMessageBox.information(self, "Import Successful", f"Successfully imported/updated {count} CII records.")
