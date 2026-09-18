"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
Calculation History & Audit Trail View (PyQt6)
Author: Senior Python Developer & Tax-Audit Software Architect
"""

import json
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
    QTextEdit,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
import pandas as pd

from database import get_db_connection, log_audit
from utils import format_inr


class AuditDetailDialog(QDialog):
    """Shows complete audit parameters of a historical calculation."""

    def __init__(self, record_dict: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Audit Trail Record #{record_dict.get('id')} - {record_dict.get('assessee_name')}")
        self.resize(650, 500)

        layout = QVBoxLayout(self)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setStyleSheet("font-family: 'Consolas', monospace; font-size: 11.5px; background: #F8FAFC;")

        # Format details
        lines = [
            "=" * 65,
            f"AUDIT TRAIL CERTIFICATE | CALCULATION #{record_dict.get('id')}",
            "=" * 65,
            f"Timestamp:              {record_dict.get('calculation_date')}",
            f"Assessee Name:          {record_dict.get('assessee_name')}",
            f"PAN:                    {record_dict.get('pan') or 'Not Disclosed'}",
            f"Assessee Category:      {record_dict.get('assessee_type')}",
            f"Residential Status:     {record_dict.get('residential_status')}",
            f"Assessment Year:        AY {record_dict.get('assessment_year')}",
            f"Transfer FY:            FY {record_dict.get('financial_year')}",
            f"Asset Type:             {record_dict.get('asset_type')}",
            f"Holding Period:         {record_dict.get('holding_period_months')} Months ({record_dict.get('asset_classification')})",
            "",
            "--- CONSIDERATION & EXPENSES ---",
            f"Gross Sale Consideration: {format_inr(record_dict.get('gross_sale_price'))}",
            f"Transfer Expenses:        {format_inr(record_dict.get('transfer_expenses'))}",
            f"Net Consideration:        {format_inr(record_dict.get('net_sale_price'))}",
            "",
            "--- ACQUISITION & CII DETAILS ---",
            f"Date of Acquisition:      {record_dict.get('date_of_acquisition')}",
            f"Actual Cost:              {format_inr(record_dict.get('actual_cost_acq'))}",
            f"Adopted Cost (Pre-2001):  {format_inr(record_dict.get('adopted_cost_acq'))}",
            f"Acquisition CII Used:     {record_dict.get('acq_cii')}",
            f"Transfer CII Used:        {record_dict.get('sale_cii')}",
            f"Indexed Acquisition Cost: {format_inr(record_dict.get('indexed_cost_acq'))}",
            "",
            "--- IMPROVEMENTS ---",
            f"Total Actual Improvement: {format_inr(record_dict.get('total_actual_improvement'))}",
            f"Total Indexed Improvement: {format_inr(record_dict.get('total_indexed_improvement'))}",
            "",
            "--- COMPARATIVE RESULTS ---",
            f"LTCG (12.5% Method):     {format_inr(record_dict.get('ltcg_12_5'))}",
            f"Total Tax (12.5% Method): {format_inr(record_dict.get('total_tax_12_5'))}",
            f"20% Indexed Applicable:   {'YES' if record_dict.get('is_20_applicable') else 'NO - ' + str(record_dict.get('ineligibility_reason'))}",
            f"LTCG (20% Indexed):       {format_inr(record_dict.get('ltcg_20')) if record_dict.get('is_20_applicable') else 'N/A'}",
            f"Total Tax (20% Indexed):  {format_inr(record_dict.get('total_tax_20')) if record_dict.get('is_20_applicable') else 'N/A'}",
            "",
            f"RECOMMENDED OPTION:       {record_dict.get('recommended_method')}",
            f"TAX SAVING TO ASSESSEE:   {format_inr(record_dict.get('tax_saving'))}",
            "=" * 65,
        ]

        txt.setText("\n".join(lines))
        layout.addWidget(txt)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)


class HistoryView(QWidget):
    """Searchable audit trail and history of all past calculations."""

    loadCalculationRequested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        title_box = QHBoxLayout()
        vbox = QVBoxLayout()
        lbl_title = QLabel("CALCULATION AUDIT TRAIL & HISTORY")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #1E3A8A;")
        lbl_sub = QLabel("Complete record of client computations, statutory rules applied, and recommendations.")
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B;")
        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_sub)
        title_box.addLayout(vbox)
        title_box.addStretch()

        self.btn_load = QPushButton("📂 Load into Calculator")
        self.btn_load.clicked.connect(self._load_selected)
        title_box.addWidget(self.btn_load)

        self.btn_details = QPushButton("🔍 View Audit Details")
        self.btn_details.setProperty("class", "secondaryBtn")
        self.btn_details.clicked.connect(self._view_details)
        title_box.addWidget(self.btn_details)

        self.btn_delete = QPushButton("🗑 Delete")
        self.btn_delete.setProperty("class", "dangerBtn")
        self.btn_delete.clicked.connect(self._delete_selected)
        title_box.addWidget(self.btn_delete)

        self.btn_export = QPushButton("📤 Export History to Excel")
        self.btn_export.setProperty("class", "successBtn")
        self.btn_export.clicked.connect(self._export_excel)
        title_box.addWidget(self.btn_export)

        layout.addLayout(title_box)

        # Search box
        search_box = QHBoxLayout()
        search_box.addWidget(QLabel("Filter by Assessee / PAN:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type name or PAN...")
        self.search_edit.textChanged.connect(self.load_data)
        search_box.addWidget(self.search_edit)
        search_box.addStretch()
        layout.addLayout(search_box)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Date & Time",
            "Assessee Name",
            "PAN",
            "Asset Type",
            "Net Consideration",
            "Tax (12.5%)",
            "Tax (20% Indexed)",
            "Recommended Method",
        ])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for c in [0, 1, 3, 4, 5, 6, 7, 8]:
            self.table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.cellDoubleClicked.connect(lambda r, c: self._load_selected())
        layout.addWidget(self.table)

        self.load_data()

    def load_data(self):
        query = self.search_edit.text().strip().lower()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if query:
                cursor.execute("""
                    SELECT * FROM calculation_history
                    WHERE LOWER(assessee_name) LIKE ? OR LOWER(pan) LIKE ?
                    ORDER BY id DESC
                """, (f"%{query}%", f"%{query}%"))
            else:
                cursor.execute("SELECT * FROM calculation_history ORDER BY id DESC")

            rows = cursor.fetchall()
            self.cached_rows = [dict(r) for r in rows]
            self.table.setRowCount(len(self.cached_rows))

            for idx, r in enumerate(self.cached_rows):
                self.table.setItem(idx, 0, QTableWidgetItem(str(r["id"])))
                self.table.setItem(idx, 1, QTableWidgetItem(str(r["calculation_date"])[:16]))
                self.table.setItem(idx, 2, QTableWidgetItem(r["assessee_name"]))
                self.table.setItem(idx, 3, QTableWidgetItem(r["pan"] or "—"))
                self.table.setItem(idx, 4, QTableWidgetItem(r["asset_type"]))

                i_sale = QTableWidgetItem(format_inr(r["net_sale_price"]))
                i_sale.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(idx, 5, i_sale)

                i_12 = QTableWidgetItem(format_inr(r["total_tax_12_5"]))
                i_12.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(idx, 6, i_12)

                tax_20_str = format_inr(r["total_tax_20"]) if r["is_20_applicable"] else "N/A"
                i_20 = QTableWidgetItem(tax_20_str)
                i_20.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(idx, 7, i_20)

                i_rec = QTableWidgetItem(r["recommended_method"])
                font = i_rec.font()
                font.setBold(True)
                i_rec.setFont(font)
                self.table.setItem(idx, 8, i_rec)

        finally:
            conn.close()

    def _get_selected_record(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.cached_rows):
            return None
        return self.cached_rows[row]

    def _load_selected(self):
        rec = self._get_selected_record()
        if not rec:
            QMessageBox.warning(self, "No Selection", "Please select a calculation record to load.")
            return
        self.loadCalculationRequested.emit(rec["id"])

    def _view_details(self):
        rec = self._get_selected_record()
        if not rec:
            QMessageBox.warning(self, "No Selection", "Please select a record to view details.")
            return
        dlg = AuditDetailDialog(rec, self)
        dlg.exec()

    def _delete_selected(self):
        rec = self._get_selected_record()
        if not rec:
            QMessageBox.warning(self, "No Selection", "Please select a record to delete.")
            return

        res = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete calculation #{rec['id']} for '{rec['assessee_name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            conn = get_db_connection()
            try:
                conn.execute("DELETE FROM calculation_history WHERE id = ?", (rec["id"],))
                conn.commit()
                log_audit("DELETE_CALCULATION", "CALCULATION_HISTORY", str(rec["id"]), f"Deleted calculation for {rec['assessee_name']}", conn=conn)
                self.load_data()
                QMessageBox.information(self, "Deleted", "Calculation record deleted.")
            finally:
                conn.close()

    def _export_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Calculation History to Excel", "CGT_Calculation_History.xlsx", "Excel Files (*.xlsx)")
        if file_path and self.cached_rows:
            try:
                df = pd.DataFrame(self.cached_rows)
                df.to_excel(file_path, index=False, sheet_name="Calculation History")
                QMessageBox.information(self, "Export Successful", f"History exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")
