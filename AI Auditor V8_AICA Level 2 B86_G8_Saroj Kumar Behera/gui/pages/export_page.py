"""
AI Auditor V8 - Report Export Page
Facilitates exporting comprehensive 12-sheet Excel workbooks and professional Word documents.
"""

import os
import subprocess
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt
from core.models import FinancialModel
from reports.excel_generator import ExcelReportGenerator
from reports.word_generator import WordReportGenerator

class ExportPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model: FinancialModel = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(20)

        # Header
        lbl_title = QLabel("Generate & Export Professional Audit Reports")
        lbl_title.setProperty("class", "page-title")
        lbl_sub = QLabel("Export complete financial models, ratio tables, and audit documentation to Excel and Word formats.")
        lbl_sub.setProperty("class", "page-subtitle")
        main_layout.addWidget(lbl_title)
        main_layout.addWidget(lbl_sub)

        # Export Cards Layout
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        # 1. Excel Report Card
        card_excel = QFrame()
        card_excel.setProperty("class", "card")
        ex_layout = QVBoxLayout(card_excel)
        ex_layout.setContentsMargins(20, 18, 20, 18)
        ex_layout.setSpacing(12)

        lbl_ex_title = QLabel("📊 Complete Excel Audit Workbook (.xlsx)")
        lbl_ex_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1E293B;")
        ex_layout.addWidget(lbl_ex_title)

        lbl_ex_desc = QLabel(
            "Includes 12 structured worksheets:\n"
            "• Executive Summary & KPIs\n"
            "• Standardized Balance Sheet & P&L\n"
            "• 30 Ratios with Benchmarks\n"
            "• Horizontal & Common-Size Trends\n"
            "• Material Variations (>= 5%)\n"
            "• Chartered Accountant Possible Reasons\n"
            "• Corroborative Evidence Checklist\n"
            "• Potential Risk & Red Flag Matrix"
        )
        lbl_ex_desc.setStyleSheet("color: #475569; font-size: 12px; line-height: 1.5;")
        ex_layout.addWidget(lbl_ex_desc)
        ex_layout.addStretch()

        self.btn_export_excel = QPushButton("Export to Excel Workbook")
        self.btn_export_excel.setProperty("class", "success-btn")
        self.btn_export_excel.clicked.connect(self._export_excel)
        ex_layout.addWidget(self.btn_export_excel)

        cards_layout.addWidget(card_excel)

        # 2. Word Report Card
        card_word = QFrame()
        card_word.setProperty("class", "card")
        wd_layout = QVBoxLayout(card_word)
        wd_layout.setContentsMargins(20, 18, 20, 18)
        wd_layout.setSpacing(12)

        lbl_wd_title = QLabel("📄 Formal Word Audit Report (.docx)")
        lbl_wd_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1E293B;")
        wd_layout.addWidget(lbl_wd_title)

        lbl_wd_desc = QLabel(
            "Executive-ready formal document:\n"
            "• Professional Cover / Title Page\n"
            "• Executive Summary Table\n"
            "• Financial Diagnostic Tables\n"
            "• Key Financial Ratio Scorecard\n"
            "• Detailed Significant Variations\n"
            "• Professional Explanatory Hypotheses\n"
            "• Substantive Audit Documents (Why Required)\n"
            "• Risk Alerts & Mandatory Disclaimer"
        )
        lbl_wd_desc.setStyleSheet("color: #475569; font-size: 12px; line-height: 1.5;")
        wd_layout.addWidget(lbl_wd_desc)
        wd_layout.addStretch()

        self.btn_export_word = QPushButton("Export to Word Document")
        self.btn_export_word.setProperty("class", "primary-btn")
        self.btn_export_word.clicked.connect(self._export_word)
        wd_layout.addWidget(self.btn_export_word)

        cards_layout.addWidget(card_word)
        main_layout.addLayout(cards_layout)

        # Disclaimer Box
        disc_frame = QFrame()
        disc_frame.setProperty("class", "card")
        d_layout = QVBoxLayout(disc_frame)
        lbl_disc_title = QLabel("Mandatory Professional Notice:")
        lbl_disc_title.setStyleSheet("font-weight: bold; color: #64748B; font-size: 11px;")
        d_layout.addWidget(lbl_disc_title)

        lbl_disc_text = QLabel(
            "Generated reports are intended to assist Chartered Accountants, internal auditors, and credit analysts "
            "in analytical review and audit planning. They do not constitute an independent statutory audit opinion "
            "under Companies Act / ISA. Primary voucher verification remains mandatory."
        )
        lbl_disc_text.setStyleSheet("color: #64748B; font-size: 11px; font-style: italic;")
        lbl_disc_text.setWordWrap(True)
        d_layout.addWidget(lbl_disc_text)

        main_layout.addWidget(disc_frame)
        main_layout.addStretch()

    def load_model(self, model: FinancialModel):
        self.model = model

    def _export_excel(self):
        if not self.model:
            QMessageBox.warning(self, "No Data", "Please upload and process a financial statement first.")
            return

        default_name = f"Audit_Report_{self.model.company_info.name.replace(' ', '_')}.xlsx"
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Excel Report", default_name, "Excel Workbook (*.xlsx)")
        if filepath:
            try:
                gen = ExcelReportGenerator(self.model)
                gen.generate(filepath)
                reply = QMessageBox.information(
                    self, "Export Successful",
                    f"Excel report saved successfully at:\n{filepath}\n\nWould you like to open it now?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    os.startfile(filepath)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to generate Excel report:\n{str(e)}")

    def _export_word(self):
        if not self.model:
            QMessageBox.warning(self, "No Data", "Please upload and process a financial statement first.")
            return

        default_name = f"Audit_Report_{self.model.company_info.name.replace(' ', '_')}.docx"
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Word Report", default_name, "Word Document (*.docx)")
        if filepath:
            try:
                gen = WordReportGenerator(self.model)
                gen.generate(filepath)
                reply = QMessageBox.information(
                    self, "Export Successful",
                    f"Word report saved successfully at:\n{filepath}\n\nWould you like to open it now?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    os.startfile(filepath)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to generate Word report:\n{str(e)}")
