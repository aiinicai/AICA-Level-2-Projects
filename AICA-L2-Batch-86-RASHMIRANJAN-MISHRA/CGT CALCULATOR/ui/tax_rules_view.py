"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
Tax Rule Master Management View (Admin Configuration) (PyQt6)
Author: Senior Python Developer & Tax-Audit Software Architect
"""

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
    QDialog,
    QFormLayout,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt

from database import get_db_connection, seed_default_tax_rules, log_audit
from tax_rules import TaxRuleMaster


class EditTaxRuleDialog(QDialog):
    """Dialog for modifying a configurable tax rule."""

    def __init__(self, parent=None, rule_key="", rule_name="", rule_val="", v_type="str", desc=""):
        super().__init__(parent)
        self.setWindowTitle(f"Configure Tax Rule: {rule_key}")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        form.addRow("Rule Identifier:", QLabel(rule_key))
        form.addRow("Description:", QLabel(desc))
        form.addRow("Data Type:", QLabel(v_type))

        self.val_edit = QLineEdit(rule_val)
        form.addRow("Configured Value:*", self.val_edit)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_value(self) -> str:
        return self.val_edit.text().strip()


class TaxRulesView(QWidget):
    """Admin configuration view for statutory tax rules and parameters."""

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
        lbl_title = QLabel("TAX RULE MASTER & STATUTORY CONFIGURATION")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #1E3A8A;")
        lbl_sub = QLabel("Configuration-driven rules for Capital Gains rates, grandfathering thresholds, and statutory caps.")
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B;")
        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_sub)
        title_box.addLayout(vbox)
        title_box.addStretch()

        self.btn_edit = QPushButton("✏ Edit Selected Rule")
        self.btn_edit.clicked.connect(self._edit_selected_rule)
        title_box.addWidget(self.btn_edit)

        self.btn_refresh = QPushButton("🔄 Reload")
        self.btn_refresh.setProperty("class", "secondaryBtn")
        self.btn_refresh.clicked.connect(self.load_data)
        title_box.addWidget(self.btn_refresh)

        layout.addLayout(title_box)

        # Statutory Notice Box (as requested in Section 13 of prompt)
        notice_card = QFrame()
        notice_card.setStyleSheet("""
            QFrame {
                background-color: #EFF6FF;
                border: 1px solid #3B82F6;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        notice_layout = QHBoxLayout(notice_card)
        notice_lbl = QLabel("ℹ Tax calculation is based on the selected Assessment Year and applicable provisions configured in the Tax Rule Master.")
        notice_lbl.setStyleSheet("color: #1D4ED8; font-weight: 600; font-size: 12px;")
        notice_layout.addWidget(notice_lbl)
        layout.addWidget(notice_card)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Category",
            "Rule Name",
            "Rule Key",
            "Configured Value",
            "Statutory Description",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.cellDoubleClicked.connect(lambda r, c: self._edit_selected_rule())
        layout.addWidget(self.table)

        self.load_data()

    def load_data(self):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT category, rule_name, rule_key, rule_value, value_type, description FROM tax_rule_master ORDER BY category, rule_name")
            rows = cursor.fetchall()
            self.table.setRowCount(len(rows))

            for idx, r in enumerate(rows):
                self.table.setItem(idx, 0, QTableWidgetItem(r["category"]))
                self.table.setItem(idx, 1, QTableWidgetItem(r["rule_name"]))
                self.table.setItem(idx, 2, QTableWidgetItem(r["rule_key"]))

                item_val = QTableWidgetItem(r["rule_value"])
                font = item_val.font()
                font.setBold(True)
                item_val.setFont(font)
                self.table.setItem(idx, 3, item_val)

                self.table.setItem(idx, 4, QTableWidgetItem(r["description"] or ""))
                # Store type
                self.table.item(idx, 2).setData(Qt.ItemDataRole.UserRole, r["value_type"])
        finally:
            conn.close()

    def _edit_selected_rule(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a tax rule to edit.")
            return

        cat = self.table.item(row, 0).text()
        name = self.table.item(row, 1).text()
        key = self.table.item(row, 2).text()
        val = self.table.item(row, 3).text()
        desc = self.table.item(row, 4).text()
        v_type = self.table.item(row, 2).data(Qt.ItemDataRole.UserRole) or "str"

        dlg = EditTaxRuleDialog(self, rule_key=key, rule_name=name, rule_val=val, v_type=v_type, desc=desc)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_val = dlg.get_value()
            rule_mgr = TaxRuleMaster()
            try:
                rule_mgr.update_rule(key, new_val)
                self.load_data()
                QMessageBox.information(self, "Rule Updated", f"Rule '{key}' successfully updated to '{new_val}'.")
            except Exception as e:
                QMessageBox.critical(self, "Update Error", f"Failed to update rule: {str(e)}")
