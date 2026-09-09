"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
Main Transaction & Calculator View (PyQt6)
Author: Senior Python Developer & Tax-Audit Software Architect
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

from PyQt6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QScrollArea,
    QMessageBox,
    QFileDialog,
    QDialog,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QTimer

from ui.widgets import IndianCurrencyInput, create_date_picker
from cii_master import get_cii_for_date, date_to_fy, fy_to_ay, CIINotFoundError
from utils import format_inr, parse_inr


class TransferExpensesDialog(QDialog):
    """Dialog for itemized entry of transfer / selling expenses."""

    def __init__(self, parent=None, initial_data=None):
        super().__init__(parent)
        self.setWindowTitle("Direct Cost / Cost of Transfer Breakdown")
        self.setMinimumWidth(450)
        self.items: List[Dict[str, Any]] = initial_data or []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        info_lbl = QLabel("Enter directly attributable transfer expenses (Section 48(i)):")
        info_lbl.setStyleSheet("font-weight: 600; color: #1E3A8A;")
        layout.addWidget(info_lbl)

        grid = QGridLayout()
        self.inputs = {}
        fields = [
            ("Brokerage & Commission", "brokerage"),
            ("Legal & Professional Expenses", "legal"),
            ("Sale Commission & Facilitation", "commission"),
            ("Registration / Documentation Expenses", "registration"),
            ("Other Attributable Transfer Expenses", "other"),
        ]

        for idx, (label_text, key) in enumerate(fields):
            lbl = QLabel(label_text + ":")
            inp = IndianCurrencyInput()
            grid.addWidget(lbl, idx, 0)
            grid.addWidget(inp, idx, 1)
            self.inputs[key] = inp
            inp.valueChanged.connect(self.update_total)

        layout.addLayout(grid)

        # Total label
        self.total_lbl = QLabel("Total Transfer Expenses: ₹0")
        self.total_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E3A8A; margin-top: 10px;")
        layout.addWidget(self.total_lbl)

        # Pre-fill if provided
        if self.items:
            for itm in self.items:
                k = itm.get("key")
                if k in self.inputs:
                    self.inputs[k].setValue(float(itm.get("amount", 0)))
            self.update_total()

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def update_total(self):
        tot = sum(inp.value() for inp in self.inputs.values())
        self.total_lbl.setText(f"Total Transfer Expenses: {format_inr(tot, show_paise=True)}")

    def get_data(self) -> (float, List[Dict[str, Any]]):
        tot = sum(inp.value() for inp in self.inputs.values())
        item_list = []
        for k, inp in self.inputs.items():
            if inp.value() > 0:
                item_list.append({"key": k, "amount": inp.value()})
        return tot, item_list


class CalculatorView(QWidget):
    """Primary input screen for Capital Gains transactions."""

    calculationRequested = pyqtSignal(dict)
    saveRequested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.transfer_expense_items: List[Dict[str, Any]] = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # -------------------------------------------------------------
        # 1. SECTION A: ASSET / TRANSACTION DETAILS
        # -------------------------------------------------------------
        sec_a = QFrame()
        sec_a.setProperty("class", "contentCard")
        sec_a_layout = QVBoxLayout(sec_a)

        lbl_a = QLabel("SECTION A: ASSET & TRANSACTION DETAILS")
        lbl_a.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E3A8A;")
        sec_a_layout.addWidget(lbl_a)

        grid_a = QGridLayout()
        grid_a.setHorizontalSpacing(15)
        grid_a.setVerticalSpacing(10)

        # Name & PAN
        grid_a.addWidget(QLabel("Name of Assessee:*"), 0, 0)
        self.name_edit = QLineEdit("Shri Rajesh Sharma")
        grid_a.addWidget(self.name_edit, 0, 1)

        grid_a.addWidget(QLabel("PAN (Optional):"), 0, 2)
        self.pan_edit = QLineEdit("ABCPS1234F")
        self.pan_edit.setMaxLength(10)
        grid_a.addWidget(self.pan_edit, 0, 3)

        # Assessee Category & Residential Status
        grid_a.addWidget(QLabel("Assessee Category:"), 1, 0)
        self.assessee_combo = QComboBox()
        self.assessee_combo.addItems(["Individual", "HUF", "Firm / LLP", "Company", "AOP / BOI", "Other"])
        grid_a.addWidget(self.assessee_combo, 1, 1)

        grid_a.addWidget(QLabel("Residential Status:"), 1, 2)
        self.res_status_combo = QComboBox()
        self.res_status_combo.addItems(["Resident", "Non-Resident", "Resident but Not Ordinarily Resident"])
        grid_a.addWidget(self.res_status_combo, 1, 3)

        # Assessment Year & Asset Type
        grid_a.addWidget(QLabel("Assessment Year:"), 2, 0)
        self.ay_combo = QComboBox()
        self.ay_combo.addItems(["2027-28", "2026-27", "2025-26", "2028-29"])
        grid_a.addWidget(self.ay_combo, 2, 1)

        grid_a.addWidget(QLabel("Type of Capital Asset:"), 2, 2)
        self.asset_type_combo = QComboBox()
        self.asset_type_combo.addItems([
            "Land & Building",
            "Land",
            "Building",
            "Shares (Unlisted)",
            "Securities (Listed)",
            "Other Capital Asset",
        ])
        grid_a.addWidget(self.asset_type_combo, 2, 3)

        # Date of Sale & FY
        grid_a.addWidget(QLabel("Date of Sale / Transfer:*"), 3, 0)
        self.sale_date_edit = create_date_picker(QDate(2026, 6, 15))
        self.sale_date_edit.dateChanged.connect(self._on_sale_date_changed)
        grid_a.addWidget(self.sale_date_edit, 3, 1)

        self.sale_fy_cii_lbl = QLabel("FY: 2026-27 | CII: 392")
        self.sale_fy_cii_lbl.setStyleSheet("color: #1E40AF; font-weight: 600;")
        grid_a.addWidget(self.sale_fy_cii_lbl, 3, 2, 1, 2)

        # Consideration
        grid_a.addWidget(QLabel("Gross Sale Consideration (₹):"), 4, 0)
        self.gross_sale_input = IndianCurrencyInput(default_val=10000000.0)
        self.gross_sale_input.valueChanged.connect(self._update_net_sale)
        grid_a.addWidget(self.gross_sale_input, 4, 1)

        # Transfer expenses & button
        exp_layout = QHBoxLayout()
        self.transfer_exp_input = IndianCurrencyInput(default_val=200000.0)
        self.transfer_exp_input.valueChanged.connect(self._update_net_sale)
        exp_layout.addWidget(self.transfer_exp_input)

        self.btn_breakdown_exp = QPushButton("Breakdown...")
        self.btn_breakdown_exp.setProperty("class", "secondaryBtn")
        self.btn_breakdown_exp.clicked.connect(self._open_transfer_expenses_dialog)
        exp_layout.addWidget(self.btn_breakdown_exp)

        grid_a.addWidget(QLabel("Less: Transfer Expenses (₹):"), 4, 2)
        grid_a.addLayout(exp_layout, 4, 3)

        # Checkbox: Net Sale Price already after transfer expenses
        self.chk_net_sale_deducted = QCheckBox("Net Sale Price already after transfer expenses")
        self.chk_net_sale_deducted.toggled.connect(self._on_net_deducted_toggled)
        grid_a.addWidget(self.chk_net_sale_deducted, 5, 0, 1, 2)

        # Amount finally considered display
        self.net_sale_display = QLabel("Amount Considered for Capital Gain (Net Sale): ₹98,00,000")
        self.net_sale_display.setStyleSheet("font-size: 12.5px; font-weight: bold; color: #047857; padding: 4px;")
        grid_a.addWidget(self.net_sale_display, 5, 2, 1, 2)

        sec_a_layout.addLayout(grid_a)
        layout.addWidget(sec_a)

        # -------------------------------------------------------------
        # 2. SECTION B: COST OF ACQUISITION
        # -------------------------------------------------------------
        sec_b = QFrame()
        sec_b.setProperty("class", "contentCard")
        sec_b_layout = QVBoxLayout(sec_b)

        lbl_b = QLabel("SECTION B: COST OF ACQUISITION")
        lbl_b.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E3A8A;")
        sec_b_layout.addWidget(lbl_b)

        grid_b = QGridLayout()
        grid_b.setHorizontalSpacing(15)
        grid_b.setVerticalSpacing(10)

        grid_b.addWidget(QLabel("Original Cost of Acquisition (₹):*"), 0, 0)
        self.acq_cost_input = IndianCurrencyInput(default_val=2000000.0)
        self.acq_cost_input.valueChanged.connect(self._update_acq_display)
        grid_b.addWidget(self.acq_cost_input, 0, 1)

        grid_b.addWidget(QLabel("Date of Acquisition:*"), 0, 2)
        self.acq_date_edit = create_date_picker(QDate(2005, 6, 15))
        self.acq_date_edit.dateChanged.connect(self._on_acq_date_changed)
        grid_b.addWidget(self.acq_date_edit, 0, 3)

        self.acq_fy_cii_lbl = QLabel("Acq FY: 2005-06 | CII: 117")
        self.acq_fy_cii_lbl.setStyleSheet("color: #1E40AF; font-weight: 600;")
        grid_b.addWidget(self.acq_fy_cii_lbl, 1, 0, 1, 2)

        self.indexed_cost_preview_lbl = QLabel("Indexed Cost of Acquisition: ₹67,00,855")
        self.indexed_cost_preview_lbl.setStyleSheet("color: #047857; font-weight: bold;")
        grid_b.addWidget(self.indexed_cost_preview_lbl, 1, 2, 1, 2)

        # Grandfathering Pre-2001 checkbox
        self.chk_pre_2001 = QCheckBox("Apply pre-01/04/2001 grandfathering / special transitional provision (Section 55(2)(b))")
        self.chk_pre_2001.toggled.connect(self._on_pre_2001_toggled)
        grid_b.addWidget(self.chk_pre_2001, 2, 0, 1, 4)

        # Pre-2001 inputs (Initially hidden or disabled)
        self.lbl_fmv = QLabel("Fair Market Value as of 01-04-2001 (₹):")
        self.fmv_input = IndianCurrencyInput(default_val=0.0)
        self.fmv_input.valueChanged.connect(self._update_acq_display)
        grid_b.addWidget(self.lbl_fmv, 3, 0)
        grid_b.addWidget(self.fmv_input, 3, 1)

        self.lbl_sdv = QLabel("Stamp Duty Value as of 01-04-2001 (₹):")
        self.sdv_input = IndianCurrencyInput(default_val=0.0)
        self.sdv_input.valueChanged.connect(self._update_acq_display)
        grid_b.addWidget(self.lbl_sdv, 3, 2)
        grid_b.addWidget(self.sdv_input, 3, 3)

        self._set_pre_2001_visible(False)

        sec_b_layout.addLayout(grid_b)
        layout.addWidget(sec_b)

        # -------------------------------------------------------------
        # 3. SECTION C: COST OF IMPROVEMENT
        # -------------------------------------------------------------
        sec_c = QFrame()
        sec_c.setProperty("class", "contentCard")
        sec_c_layout = QVBoxLayout(sec_c)

        header_c = QHBoxLayout()
        lbl_c = QLabel("SECTION C: COST OF IMPROVEMENT (Multiple entries supported)")
        lbl_c.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E3A8A;")
        header_c.addWidget(lbl_c)
        header_c.addStretch()

        self.btn_add_imp = QPushButton("+ Add Cost of Improvement")
        self.btn_add_imp.clicked.connect(lambda: self._add_improvement_row())
        header_c.addWidget(self.btn_add_imp)

        self.btn_import_imp = QPushButton("Import from Excel...")
        self.btn_import_imp.setProperty("class", "secondaryBtn")
        self.btn_import_imp.clicked.connect(self._import_improvements_excel)
        header_c.addWidget(self.btn_import_imp)

        sec_c_layout.addLayout(header_c)

        # Table for Improvements
        self.imp_table = QTableWidget()
        self.imp_table.setColumnCount(5)
        self.imp_table.setHorizontalHeaderLabels([
            "Particulars of Improvement",
            "Date (DD/MM/YYYY)",
            "Financial Year",
            "Amount (₹)",
            "Action",
        ])
        self.imp_table.verticalHeader().setDefaultSectionSize(40)
        self.imp_table.verticalHeader().setMinimumSectionSize(36)
        self.imp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.imp_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.imp_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.imp_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.imp_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.imp_table.setColumnWidth(1, 145)
        self.imp_table.setColumnWidth(2, 110)
        self.imp_table.setColumnWidth(3, 160)
        self.imp_table.setColumnWidth(4, 95)
        self.imp_table.setMinimumHeight(150)
        sec_c_layout.addWidget(self.imp_table)

        # Summary of Improvements
        summary_c_layout = QHBoxLayout()
        self.imp_total_actual_lbl = QLabel("Total Actual Cost of Improvement: ₹10,00,000")
        self.imp_total_actual_lbl.setStyleSheet("font-weight: bold; color: #1E293B;")
        summary_c_layout.addWidget(self.imp_total_actual_lbl)

        self.imp_total_indexed_lbl = QLabel("Total Indexed Cost of Improvement: ₹19,60,000")
        self.imp_total_indexed_lbl.setStyleSheet("font-weight: bold; color: #047857;")
        summary_c_layout.addWidget(self.imp_total_indexed_lbl)

        sec_c_layout.addLayout(summary_c_layout)
        layout.addWidget(sec_c)

        # -------------------------------------------------------------
        # 4. ACTION BAR (Buttons at bottom)
        # -------------------------------------------------------------
        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)

        self.btn_calculate = QPushButton("⚡ CALCULATE & COMPARE (12.5% vs 20%)")
        self.btn_calculate.setStyleSheet("font-size: 14px; font-weight: 800; padding: 12px 24px; background-color: #2563EB;")
        self.btn_calculate.clicked.connect(self._trigger_calculate)
        action_layout.addWidget(self.btn_calculate)

        self.btn_save = QPushButton("💾 Save Calculation")
        self.btn_save.setProperty("class", "successBtn")
        self.btn_save.clicked.connect(self._trigger_save)
        action_layout.addWidget(self.btn_save)

        self.btn_load_sample = QPushButton("📋 Load Prompt Test Case")
        self.btn_load_sample.setProperty("class", "secondaryBtn")
        self.btn_load_sample.clicked.connect(self.load_prompt_sample_case)
        action_layout.addWidget(self.btn_load_sample)

        self.btn_reset = QPushButton("🔄 Reset Form")
        self.btn_reset.setProperty("class", "dangerBtn")
        self.btn_reset.clicked.connect(self.reset_form)
        action_layout.addWidget(self.btn_reset)

        action_layout.addStretch()
        layout.addLayout(action_layout)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Initialize default row in improvement table
        self.load_prompt_sample_case()

    # -------------------------------------------------------------
    # Logic & Event Handlers
    # -------------------------------------------------------------
    def _on_sale_date_changed(self, qdate: QDate):
        try:
            d = qdate.toPyDate()
            cii, fy = get_cii_for_date(d, is_acquisition=False)
            self.sale_fy_cii_lbl.setText(f"FY: {fy} | CII: {cii}")
            ay = fy_to_ay(fy)
            idx = self.ay_combo.findText(ay)
            if idx >= 0:
                self.ay_combo.setCurrentIndex(idx)
        except Exception as e:
            self.sale_fy_cii_lbl.setText(f"CII Error: {str(e)}")
        self._update_acq_display()

    def _on_acq_date_changed(self, qdate: QDate):
        try:
            d = qdate.toPyDate()
            cii, fy = get_cii_for_date(d, is_acquisition=True)
            self.acq_fy_cii_lbl.setText(f"Acq FY: {fy} | CII: {cii}")
            if d < datetime(2001, 4, 1).date():
                self.chk_pre_2001.setChecked(True)
        except Exception as e:
            self.acq_fy_cii_lbl.setText(f"CII Error: {str(e)}")
        self._update_acq_display()

    def _update_net_sale(self):
        gross = self.gross_sale_input.value()
        exp = self.transfer_exp_input.value()
        if self.chk_net_sale_deducted.isChecked():
            net = gross
        else:
            net = max(0.0, gross - exp)
        self.net_sale_display.setText(f"Amount Considered for Capital Gain (Net Sale): {format_inr(net)}")

    def _on_net_deducted_toggled(self, checked: bool):
        self._update_net_sale()

    def _on_pre_2001_toggled(self, checked: bool):
        self._set_pre_2001_visible(checked)
        self._update_acq_display()

    def _set_pre_2001_visible(self, visible: bool):
        self.lbl_fmv.setVisible(visible)
        self.fmv_input.setVisible(visible)
        self.lbl_sdv.setVisible(visible)
        self.sdv_input.setVisible(visible)

    def _update_acq_display(self):
        cost = self.acq_cost_input.value()
        if self.chk_pre_2001.isChecked():
            fmv = self.fmv_input.value()
            sdv = self.sdv_input.value()
            effective_fmv = min(fmv, sdv) if sdv > 0 else fmv
            cost = max(cost, effective_fmv)

        try:
            d_sale = self.sale_date_edit.date().toPyDate()
            d_acq = self.acq_date_edit.date().toPyDate()
            sale_cii, _ = get_cii_for_date(d_sale, is_acquisition=False)
            acq_cii, _ = get_cii_for_date(d_acq, is_acquisition=True)
            indexed = (cost * sale_cii) / acq_cii if acq_cii > 0 else cost
            self.indexed_cost_preview_lbl.setText(f"Indexed Cost of Acquisition: {format_inr(indexed)}")
        except Exception:
            self.indexed_cost_preview_lbl.setText("Indexed Cost: Pending valid dates/CII")

    def _open_transfer_expenses_dialog(self):
        dlg = TransferExpensesDialog(self, initial_data=self.transfer_expense_items)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            tot, items = dlg.get_data()
            self.transfer_exp_input.setValue(tot)
            self.transfer_expense_items = items
            self._update_net_sale()

    def _add_improvement_row(self, particulars="Construction", date_str="15/06/2012", amount=1000000.0):
        if isinstance(particulars, bool) or not particulars:
            particulars = "Improvement"

        row_idx = self.imp_table.rowCount()
        self.imp_table.insertRow(row_idx)

        # Particulars
        p_item = QLineEdit(str(particulars))
        self.imp_table.setCellWidget(row_idx, 0, p_item)

        # Date Picker
        d_picker = create_date_picker()
        if date_str:
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(str(date_str).strip(), fmt).date()
                    d_picker.setDate(QDate(dt.year, dt.month, dt.day))
                    break
                except ValueError:
                    pass
        self.imp_table.setCellWidget(row_idx, 1, d_picker)

        # FY label
        fy_lbl = QLabel(date_to_fy(d_picker.date().toPyDate()))
        fy_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.imp_table.setCellWidget(row_idx, 2, fy_lbl)

        d_picker.dateChanged.connect(lambda qd, lbl=fy_lbl: lbl.setText(date_to_fy(qd.toPyDate())))
        d_picker.dateChanged.connect(self._recalculate_improvement_totals)

        # Amount Input (Clean single-line without duplicate preview label)
        try:
            amt_val = float(amount) if amount is not None else 0.0
        except (ValueError, TypeError):
            amt_val = 0.0
        amt_inp = IndianCurrencyInput(default_val=amt_val, show_preview=False)
        amt_inp.valueChanged.connect(self._recalculate_improvement_totals)
        self.imp_table.setCellWidget(row_idx, 3, amt_inp)

        # Delete Button Container (Neatly centered with proper margins)
        action_container = QWidget()
        action_layout = QHBoxLayout(action_container)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_del = QPushButton("Delete")
        btn_del.setProperty("class", "dangerBtn")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                min-width: 58px;
                max-width: 68px;
                min-height: 22px;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
        """)
        action_layout.addWidget(btn_del)
        btn_del.clicked.connect(lambda _, c=action_container: self._on_delete_improvement_clicked(c))
        self.imp_table.setCellWidget(row_idx, 4, action_container)

        self._recalculate_improvement_totals()

    def _on_delete_improvement_clicked(self, container_widget: QWidget):
        """Safely disables the container and defers row removal to the next event loop tick."""
        container_widget.setEnabled(False)
        QTimer.singleShot(0, lambda: self._remove_improvement_row(container_widget))

    def _remove_improvement_row(self, target_widget: QWidget):
        """Removes the row containing target_widget safely with error handling."""
        try:
            for r in range(self.imp_table.rowCount()):
                cell_w = self.imp_table.cellWidget(r, 4)
                if cell_w == target_widget or (cell_w and cell_w.findChild(QPushButton) == target_widget):
                    self.imp_table.removeRow(r)
                    break
            self._recalculate_improvement_totals()
        except Exception as e:
            print(f"Error removing improvement row: {e}")

    def _recalculate_improvement_totals(self):
        total_actual = 0.0
        total_indexed = 0.0

        try:
            d_sale = self.sale_date_edit.date().toPyDate()
            sale_cii, _ = get_cii_for_date(d_sale, is_acquisition=False)
        except Exception:
            sale_cii = 392

        cut_off_2001 = datetime(2001, 4, 1).date()

        for r in range(self.imp_table.rowCount()):
            amt_w = self.imp_table.cellWidget(r, 3)
            date_w = self.imp_table.cellWidget(r, 1)
            if amt_w and date_w:
                amt = amt_w.value()
                d_imp = date_w.date().toPyDate()
                if d_imp >= cut_off_2001:
                    total_actual += amt
                    try:
                        imp_cii, _ = get_cii_for_date(d_imp, is_acquisition=False)
                        total_indexed += (amt * sale_cii) / imp_cii
                    except Exception:
                        total_indexed += amt

        self.imp_total_actual_lbl.setText(f"Total Actual Cost of Improvement: {format_inr(total_actual)}")
        self.imp_total_indexed_lbl.setText(f"Total Indexed Cost of Improvement: {format_inr(total_indexed)}")

    def _import_improvements_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Cost of Improvement from Excel",
            "",
            "Excel Files (*.xlsx *.xls)",
        )
        if not file_path:
            return

        try:
            df = pd.read_excel(file_path)
            imported_count = 0
            # Identify columns
            part_col = df.columns[0]
            date_col = df.columns[1] if len(df.columns) > 1 else None
            amt_col = df.columns[-1]

            for _, row in df.iterrows():
                p = str(row[part_col])
                d_val = str(row[date_col]) if date_col else "15/06/2015"
                amt = float(row[amt_col]) if not pd.isna(row[amt_col]) else 0.0
                if amt > 0:
                    self._add_improvement_row(particulars=p, date_str=d_val, amount=amt)
                    imported_count += 1

            QMessageBox.information(self, "Import Successful", f"Successfully imported {imported_count} improvement entries.")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import Excel data: {str(e)}")

    def load_prompt_sample_case(self):
        """Loads Section 15 example test case from prompt."""
        self.name_edit.setText("Shri Rajesh Sharma")
        self.pan_edit.setText("ABCPS1234F")
        self.asset_type_combo.setCurrentText("Land & Building")
        self.assessee_combo.setCurrentText("Individual")
        self.res_status_combo.setCurrentText("Resident")
        self.ay_combo.setCurrentText("2027-28")

        self.sale_date_edit.setDate(QDate(2026, 6, 15))
        self.gross_sale_input.setValue(10000000.0)
        self.transfer_exp_input.setValue(200000.0)
        self.chk_net_sale_deducted.setChecked(False)

        self.acq_cost_input.setValue(2000000.0)
        self.acq_date_edit.setDate(QDate(2005, 6, 15))
        self.chk_pre_2001.setChecked(False)

        # Clear improvements table and set Section 15 row
        self.imp_table.setRowCount(0)
        self._add_improvement_row(particulars="Construction", date_str="15/06/2012", amount=1000000.0)

        self._update_net_sale()
        self._update_acq_display()

    def reset_form(self):
        res = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to clear all inputs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            self.name_edit.clear()
            self.pan_edit.clear()
            self.gross_sale_input.setValue(0.0)
            self.transfer_exp_input.setValue(0.0)
            self.acq_cost_input.setValue(0.0)
            self.imp_table.setRowCount(0)
            self.chk_pre_2001.setChecked(False)
            self.transfer_expense_items = []
            self._update_net_sale()
            self._update_acq_display()

    def get_form_data(self) -> Dict[str, Any]:
        """Collects and packages all current inputs into a dictionary."""
        improvements = []
        for r in range(self.imp_table.rowCount()):
            p_widget = self.imp_table.cellWidget(r, 0)
            d_widget = self.imp_table.cellWidget(r, 1)
            a_widget = self.imp_table.cellWidget(r, 3)
            if p_widget and d_widget and a_widget:
                improvements.append({
                    "particulars": p_widget.text(),
                    "date": d_widget.date().toString("dd/MM/yyyy"),
                    "amount": a_widget.value(),
                })

        return {
            "assessee_name": self.name_edit.text().strip(),
            "pan": self.pan_edit.text().strip().upper(),
            "assessee_type": self.assessee_combo.currentText(),
            "residential_status": self.res_status_combo.currentText(),
            "assessment_year": self.ay_combo.currentText(),
            "asset_type": self.asset_type_combo.currentText(),
            "date_of_sale": self.sale_date_edit.date().toString("dd/MM/yyyy"),
            "date_of_acquisition": self.acq_date_edit.date().toString("dd/MM/yyyy"),
            "gross_sale_price": self.gross_sale_input.value(),
            "transfer_expenses": self.transfer_exp_input.value(),
            "net_sale_already_deducted": self.chk_net_sale_deducted.isChecked(),
            "net_sale_price_input": self.gross_sale_input.value() if self.chk_net_sale_deducted.isChecked() else None,
            "actual_cost_acq": self.acq_cost_input.value(),
            "is_pre_2001": self.chk_pre_2001.isChecked(),
            "fmv_2001": self.fmv_input.value() if self.chk_pre_2001.isChecked() else 0.0,
            "sdv_2001": self.sdv_input.value() if self.chk_pre_2001.isChecked() else None,
            "improvements": improvements,
            "transfer_expense_items": self.transfer_expense_items,
        }

    def _trigger_calculate(self):
        data = self.get_form_data()
        self.calculationRequested.emit(data)

    def _trigger_save(self):
        data = self.get_form_data()
        self.saveRequested.emit(data)
