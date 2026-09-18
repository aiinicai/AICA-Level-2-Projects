"""
CAPITAL GAINS TAX COMPARISON CALCULATOR – 12.5% vs 20%
Main Application Window & Application Controller (PyQt6)
Author: Senior Python Developer & Tax-Audit Software Architect
"""

import sys
import os
import json
import traceback
from datetime import datetime
from typing import Dict, Any

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QMessageBox,
    QStatusBar,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont

from database import init_db, get_db_connection, log_audit
from validation import validate_transaction_inputs
from capital_gain_engine import compute_capital_gains
from tax_calculator import compare_tax_methods, TaxComparisonResult
from ui.theme import APP_STYLESHEET
from ui.dashboard_view import DashboardView
from ui.calculator_view import CalculatorView
from ui.comparison_view import ComparisonView
from ui.cii_view import CIIMasterView
from ui.tax_rules_view import TaxRulesView
from ui.history_view import HistoryView


class MainWindow(QMainWindow):
    """Primary application window with sidebar navigation and stacked views."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAPITAL GAINS TAX COMPARISON – 12.5% vs 20%")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 680)

        # Initialize Database
        init_db()

        self.last_comparison: TaxComparisonResult = None
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # -------------------------------------------------------------
        # 1. SIDEBAR NAVIGATION
        # -------------------------------------------------------------
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 16, 0, 16)
        sidebar_layout.setSpacing(4)

        # Brand / App Title
        title_lbl = QLabel("TAX AUDIT SUITE")
        title_lbl.setObjectName("sidebarTitle")
        sub_lbl = QLabel("CGT 12.5% vs 20% Comparison")
        sub_lbl.setObjectName("sidebarSubtitle")
        sidebar_layout.addWidget(title_lbl)
        sidebar_layout.addWidget(sub_lbl)

        # Navigation Buttons
        self.nav_buttons = []
        nav_items = [
            ("📊  Dashboard", 0),
            ("⚡  New Calculation", 1),
            ("⚖  Comparison & Results", 2),
            ("📅  CII Master", 3),
            ("📜  Tax Rule Master", 4),
            ("🗄  Calculation History", 5),
        ]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setProperty("class", "sidebarBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, idx=index: self.switch_view(idx))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # System Info Box at bottom of sidebar
        sys_box = QFrame()
        sys_box.setStyleSheet("background: rgba(0, 0, 0, 0.2); border-radius: 6px; margin: 8px; padding: 10px;")
        sys_vbox = QVBoxLayout(sys_box)
        sys_vbox.setContentsMargins(4, 4, 4, 4)
        sys_title = QLabel("STATUTORY ENGINE")
        sys_title.setStyleSheet("color: #93C5FD; font-size: 10px; font-weight: bold;")
        sys_body = QLabel("Finance (No. 2) Act, 2024\nSection 112 Active")
        sys_body.setStyleSheet("color: #E2E8F0; font-size: 10.5px;")
        sys_vbox.addWidget(sys_title)
        sys_vbox.addWidget(sys_body)
        sidebar_layout.addWidget(sys_box)

        root_layout.addWidget(self.sidebar)

        # -------------------------------------------------------------
        # 2. STACKED CONTENT AREA
        # -------------------------------------------------------------
        self.stack = QStackedWidget()

        self.view_dashboard = DashboardView()
        self.view_calculator = CalculatorView()
        self.view_comparison = ComparisonView()
        self.view_cii = CIIMasterView()
        self.view_tax_rules = TaxRulesView()
        self.view_history = HistoryView()

        self.stack.addWidget(self.view_dashboard)    # 0
        self.stack.addWidget(self.view_calculator)   # 1
        self.stack.addWidget(self.view_comparison)   # 2
        self.stack.addWidget(self.view_cii)          # 3
        self.stack.addWidget(self.view_tax_rules)    # 4
        self.stack.addWidget(self.view_history)      # 5

        root_layout.addWidget(self.stack)

        # -------------------------------------------------------------
        # 3. STATUS BAR
        # -------------------------------------------------------------
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background-color: #FFFFFF; color: #475569; border-top: 1px solid #E2E8F0; font-size: 11px;")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready | Offline Database Connected | Professional CA Audit Engine Active")

        # -------------------------------------------------------------
        # 4. SIGNAL CONNECTIONS
        # -------------------------------------------------------------
        # Dashboard signals
        self.view_dashboard.newCalculationRequested.connect(lambda: self.switch_view(1))
        self.view_dashboard.openCiiRequested.connect(lambda: self.switch_view(3))
        self.view_dashboard.loadCalculationRequested.connect(self.load_calculation_by_id)

        # Calculator signals
        self.view_calculator.calculationRequested.connect(self.process_calculation)
        self.view_calculator.saveRequested.connect(self.save_calculation)

        # History signals
        self.view_history.loadCalculationRequested.connect(self.load_calculation_by_id)

        # Initial view
        self.switch_view(0)

    def switch_view(self, index: int):
        """Switches the active view and synchronizes sidebar button states."""
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        # Refresh views when navigated to
        if index == 0:
            self.view_dashboard.refresh_data()
        elif index == 3:
            self.view_cii.load_data()
        elif index == 4:
            self.view_tax_rules.load_data()
        elif index == 5:
            self.view_history.load_data()

    def process_calculation(self, data: Dict[str, Any]):
        """Validates inputs, executes calculation, and renders comparison screen."""
        # 1. Validation
        val_result = validate_transaction_inputs(
            assessee_name=data["assessee_name"],
            pan=data["pan"],
            assessee_type=data["assessee_type"],
            residential_status=data["residential_status"],
            asset_type=data["asset_type"],
            date_of_sale=data["date_of_sale"],
            date_of_acquisition=data["date_of_acquisition"],
            gross_sale_price=data["gross_sale_price"],
            transfer_expenses=data["transfer_expenses"],
            net_sale_already_deducted=data["net_sale_already_deducted"],
            net_sale_price_input=data["net_sale_price_input"],
            actual_cost_acq=data["actual_cost_acq"],
            fmv_2001=data["fmv_2001"],
            sdv_2001=data["sdv_2001"],
            improvements=data["improvements"],
        )

        if not val_result.is_valid:
            err_msg = "\n• " + "\n• ".join(val_result.errors)
            QMessageBox.critical(self, "Validation Errors", f"Please resolve the following errors before calculating:{err_msg}")
            return

        if val_result.warnings:
            warn_msg = "\n• " + "\n• ".join(val_result.warnings)
            self.status_bar.showMessage(f"Notice: {val_result.warnings[0]}", 8000)

        # 2. Capital Gains Computation
        try:
            cg_result = compute_capital_gains(
                assessee_name=data["assessee_name"],
                pan=data["pan"],
                assessee_type=data["assessee_type"],
                residential_status=data["residential_status"],
                assessment_year=data["assessment_year"],
                asset_type=data["asset_type"],
                date_of_sale=data["date_of_sale"],
                date_of_acquisition=data["date_of_acquisition"],
                gross_sale_price=data["gross_sale_price"],
                transfer_expenses=data["transfer_expenses"],
                net_sale_already_deducted=data["net_sale_already_deducted"],
                net_sale_price_input=data["net_sale_price_input"],
                actual_cost_acq=data["actual_cost_acq"],
                fmv_2001=data["fmv_2001"],
                sdv_2001=data["sdv_2001"],
                improvements=data["improvements"],
                transfer_expense_items=data.get("transfer_expense_items"),
            )
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Error computing capital gains: {str(e)}")
            return

        # 3. Tax Liability & Comparison
        try:
            comparison = compare_tax_methods(cg_result)
            self.last_comparison = comparison
            self.view_comparison.display_results(comparison)
            self.switch_view(2)
            self.status_bar.showMessage(f"Analysis Complete: Recommended method is {comparison.recommended_method}", 6000)
        except Exception as e:
            QMessageBox.critical(self, "Tax Comparison Error", f"Error calculating tax liabilities: {str(e)}")

    def save_calculation(self, data: Dict[str, Any]):
        """Computes and saves calculation record into SQLite database."""
        # Ensure calculated
        self.process_calculation(data)
        if not self.last_comparison:
            return

        comp = self.last_comparison
        cg = comp.cg_result
        m12 = comp.method_12_5
        m20 = comp.method_20

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO calculation_history (
                    calculation_date, assessee_name, pan, assessee_type, residential_status,
                    assessment_year, financial_year, asset_type, date_of_sale, date_of_acquisition,
                    gross_sale_price, transfer_expenses, net_sale_price, actual_cost_acq, fmv_2001,
                    adopted_cost_acq, acq_cii, sale_cii, indexed_cost_acq,
                    total_actual_improvement, total_indexed_improvement, improvements_json, transfer_expenses_json,
                    holding_period_months, asset_classification, is_20_applicable, ineligibility_reason,
                    ltcg_12_5, tax_12_5, surcharge_12_5, cess_12_5, total_tax_12_5,
                    ltcg_20, tax_20, surcharge_20, cess_20, total_tax_20,
                    recommended_method, tax_saving, notes
                ) VALUES (
                    datetime('now'), ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?
                )
            """, (
                cg.assessee_name, cg.pan, cg.assessee_type, cg.residential_status,
                cg.assessment_year, cg.financial_year_transfer, cg.asset_type, cg.date_of_sale, cg.date_of_acquisition,
                cg.gross_sale_price, cg.transfer_expenses, cg.net_sale_price, cg.actual_cost_acq, cg.fmv_2001,
                cg.adopted_cost_acq, cg.acq_cii, cg.sale_cii, cg.indexed_cost_acq,
                cg.total_actual_improvement, cg.total_indexed_improvement,
                json.dumps([{"particulars": i.particulars, "amount": i.amount, "date": i.date_of_improvement, "fy": i.fy_of_improvement} for i in cg.improvements]),
                json.dumps(cg.transfer_expense_items),
                cg.holding_period_months, cg.asset_classification, 1 if comp.is_20_applicable else 0, comp.ineligibility_reason,
                cg.ltcg_12_5, m12.basic_tax, m12.surcharge_amount, m12.cess_amount, m12.total_tax_liability,
                cg.ltcg_20 if cg.ltcg_20 is not None else 0.0,
                m20.basic_tax if m20 else 0.0,
                m20.surcharge_amount if m20 else 0.0,
                m20.cess_amount if m20 else 0.0,
                m20.total_tax_liability if m20 else 0.0,
                comp.recommended_method, comp.tax_saving, comp.recommendation_summary,
            ))
            calc_id = cursor.lastrowid
            conn.commit()

            log_audit("SAVE_CALCULATION", "CALCULATION_HISTORY", str(calc_id), f"Saved calculation for {cg.assessee_name}", conn=conn)
            QMessageBox.information(self, "Saved", f"Calculation #{calc_id} for '{cg.assessee_name}' successfully saved to Audit Trail.")
            self.view_dashboard.refresh_data()
            self.view_history.load_data()
        finally:
            conn.close()

    def load_calculation_by_id(self, calc_id: int):
        """Loads a historical calculation by ID into the calculator view."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM calculation_history WHERE id = ?", (calc_id,))
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(self, "Not Found", f"Calculation #{calc_id} not found.")
                return

            # Populate calculator view
            self.view_calculator.name_edit.setText(row["assessee_name"])
            self.view_calculator.pan_edit.setText(row["pan"] or "")
            self.view_calculator.assessee_combo.setCurrentText(row["assessee_type"])
            self.view_calculator.res_status_combo.setCurrentText(row["residential_status"])
            self.view_calculator.ay_combo.setCurrentText(row["assessment_year"])
            self.view_calculator.asset_type_combo.setCurrentText(row["asset_type"])

            # Dates
            from tax_rules import parse_date
            from PyQt6.QtCore import QDate
            d_sale = parse_date(row["date_of_sale"])
            d_acq = parse_date(row["date_of_acquisition"])
            self.view_calculator.sale_date_edit.setDate(QDate(d_sale.year, d_sale.month, d_sale.day))
            self.view_calculator.acq_date_edit.setDate(QDate(d_acq.year, d_acq.month, d_acq.day))

            self.view_calculator.gross_sale_input.setValue(row["gross_sale_price"])
            self.view_calculator.transfer_exp_input.setValue(row["transfer_expenses"])
            self.view_calculator.acq_cost_input.setValue(row["actual_cost_acq"])

            if row["fmv_2001"] > 0:
                self.view_calculator.chk_pre_2001.setChecked(True)
                self.view_calculator.fmv_input.setValue(row["fmv_2001"])
            else:
                self.view_calculator.chk_pre_2001.setChecked(False)

            # Improvements
            self.view_calculator.imp_table.setRowCount(0)
            if row["improvements_json"]:
                try:
                    imp_list = json.loads(row["improvements_json"])
                    for imp in imp_list:
                        self.view_calculator._add_improvement_row(
                            particulars=imp.get("particulars", "Improvement"),
                            date_str=imp.get("date"),
                            amount=float(imp.get("amount", 0)),
                        )
                except Exception:
                    pass

            self.view_calculator._update_net_sale()
            self.view_calculator._update_acq_display()

            # Switch to Calculator View
            self.switch_view(1)
            self.status_bar.showMessage(f"Loaded calculation #{calc_id} for {row['assessee_name']}", 5000)

        finally:
            conn.close()


def custom_excepthook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        with open("cgt_error.log", "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now().isoformat()}] Unhandled Exception:\n{err_msg}\n")
    except Exception:
        pass
    print(err_msg, file=sys.stderr)
    try:
        QMessageBox.critical(
            None,
            "Application Error",
            f"An unexpected error occurred:\n{exc_value}\n\nDetails have been logged to cgt_error.log."
        )
    except Exception:
        pass


def main():
    sys.excepthook = custom_excepthook
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)

    # Set default app font
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
