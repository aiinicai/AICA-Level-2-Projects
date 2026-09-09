"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
Side-by-Side Comparison & Results View (PyQt6)
Author: Senior Python Developer & Tax-Audit Software Architect
"""

import os
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QScrollArea,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.widgets import MetricCard, RecommendationBanner
from tax_calculator import TaxComparisonResult
from report_generator import generate_pdf_report, generate_excel_report, generate_word_report
from utils import format_inr


class ComparisonView(QWidget):
    """Side-by-side comparison dashboard and report export center."""

    exportPdfRequested = pyqtSignal()
    exportExcelRequested = pyqtSignal()
    exportWordRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_comparison: Optional[TaxComparisonResult] = None
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

        # Title
        top_bar = QHBoxLayout()
        title_vbox = QVBoxLayout()
        lbl_title = QLabel("CAPITAL GAINS TAX ANALYSIS & COMPARISON")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: 900; color: #1E3A8A;")
        lbl_sub = QLabel("Evaluation under Finance (No. 2) Act, 2024 (Section 112 amended provisions)")
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B;")
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_sub)
        top_bar.addLayout(title_vbox)
        top_bar.addStretch()

        # Export Buttons
        self.btn_pdf = QPushButton("📄 Generate PDF")
        self.btn_pdf.clicked.connect(self._export_pdf)
        top_bar.addWidget(self.btn_pdf)

        self.btn_excel = QPushButton("📊 Export to Excel")
        self.btn_excel.setProperty("class", "successBtn")
        self.btn_excel.clicked.connect(self._export_excel)
        top_bar.addWidget(self.btn_excel)

        self.btn_word = QPushButton("📝 Export to Word")
        self.btn_word.setProperty("class", "secondaryBtn")
        self.btn_word.clicked.connect(self._export_word)
        top_bar.addWidget(self.btn_word)

        layout.addLayout(top_bar)

        # 1. Prominent Recommendation Banner (Winning Option)
        self.rec_banner = RecommendationBanner()
        layout.addWidget(self.rec_banner)

        # 2. Key KPI Metric Cards
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(12)

        self.card_net_sale = MetricCard("NET SALE CONSIDERATION", "₹0", "Amount considered for CG")
        self.card_cg_12 = MetricCard("CAPITAL GAIN (12.5%)", "₹0", "Without Indexation", card_type="default")
        self.card_cg_20 = MetricCard("CAPITAL GAIN (20% INDEXED)", "₹0", "With Indexation", card_type="default")
        self.card_tax_12 = MetricCard("TAX LIABILITY (12.5%)", "₹0", "Incl. Surcharge & Cess", card_type="primary")
        self.card_tax_20 = MetricCard("TAX LIABILITY (20%)", "₹0", "Incl. Surcharge & Cess", card_type="primary")

        kpi_grid.addWidget(self.card_net_sale, 0, 0)
        kpi_grid.addWidget(self.card_cg_12, 0, 1)
        kpi_grid.addWidget(self.card_cg_20, 0, 2)
        kpi_grid.addWidget(self.card_tax_12, 1, 0)
        kpi_grid.addWidget(self.card_tax_20, 1, 1)

        self.card_saving = MetricCard("NET TAX SAVING", "₹0", "Benefit to Assessee", card_type="success")
        kpi_grid.addWidget(self.card_saving, 1, 2)

        layout.addLayout(kpi_grid)

        # 3. Side-by-Side Comparison Table
        card_table = QFrame()
        card_table.setProperty("class", "contentCard")
        table_layout = QVBoxLayout(card_table)

        lbl_tbl = QLabel("SIDE-BY-SIDE STATUTORY COMPARISON TABLE")
        lbl_tbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E3A8A;")
        table_layout.addWidget(lbl_tbl)

        self.comp_table = QTableWidget()
        self.comp_table.setColumnCount(3)
        self.comp_table.setHorizontalHeaderLabels([
            "Particulars",
            "12.5% Without Indexation",
            "20% With Indexation",
        ])
        self.comp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.comp_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.comp_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.comp_table.setMinimumHeight(380)
        table_layout.addWidget(self.comp_table)

        layout.addWidget(card_table)

        # 4. Detailed Step-by-Step Breakdown (Expandable)
        self.card_details = QFrame()
        self.card_details.setProperty("class", "contentCard")
        details_layout = QVBoxLayout(self.card_details)

        self.btn_toggle_details = QPushButton("▶ View Detailed Step-by-Step Statutory Breakdown (19 Items)")
        self.btn_toggle_details.setProperty("class", "secondaryBtn")
        self.btn_toggle_details.clicked.connect(self._toggle_detailed_view)
        details_layout.addWidget(self.btn_toggle_details)

        self.details_content = QLabel("")
        self.details_content.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 11.5px; color: #1E293B; background: #F8FAFC; padding: 12px; border-radius: 6px;")
        self.details_content.setVisible(False)
        details_layout.addWidget(self.details_content)

        layout.addWidget(self.card_details)

        # Statutory Disclaimer
        disclaimer = QLabel(
            "“This report is a calculation aid and should be reviewed with reference to the applicable provisions of the Income-tax Act, Rules, notifications and circulars for the relevant Assessment Year.”"
        )
        disclaimer.setStyleSheet("color: #64748B; font-style: italic; font-size: 11px; padding: 8px;")
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def display_results(self, comp: TaxComparisonResult):
        """Populates the view with a newly computed TaxComparisonResult."""
        self.current_comparison = comp
        cg = comp.cg_result
        m12 = comp.method_12_5
        m20 = comp.method_20

        # Update Banner
        self.rec_banner.update_result(
            recommended_method=comp.recommended_method,
            tax_saving=comp.tax_saving,
            tax_12_5=m12.total_tax_liability,
            tax_20=m20.total_tax_liability if m20 else None,
            is_20_applicable=comp.is_20_applicable,
            reason=comp.ineligibility_reason,
        )

        # Update Metric Cards
        self.card_net_sale.set_value(format_inr(cg.net_sale_price))
        self.card_cg_12.set_value(format_inr(max(0.0, cg.ltcg_12_5)))
        self.card_cg_20.set_value(format_inr(max(0.0, cg.ltcg_20 if cg.ltcg_20 is not None else 0)) if comp.is_20_applicable else "N/A")

        self.card_tax_12.set_value(format_inr(m12.total_tax_liability), f"Eff. Rate: {m12.effective_tax_rate_percent}%")
        if comp.is_20_applicable and m20:
            self.card_tax_20.set_value(format_inr(m20.total_tax_liability), f"Eff. Rate: {m20.effective_tax_rate_percent}%")
        else:
            self.card_tax_20.set_value("NOT APPLICABLE", "Disallowed by Law")

        self.card_saving.set_value(format_inr(comp.tax_saving, show_paise=True), f"Favours: {comp.recommended_method}")

        # Update Table Rows
        rows = [
            ("Gross Sale Consideration", format_inr(cg.gross_sale_price), format_inr(cg.gross_sale_price)),
            ("Less: Transfer Expenses", format_inr(cg.transfer_expenses), format_inr(cg.transfer_expenses)),
            ("Net Sale Consideration", format_inr(cg.net_sale_price), format_inr(cg.net_sale_price)),
            (f"Actual Cost of Acquisition ({'FMV' if cg.adopted_cost_acq > cg.actual_cost_acq else 'Actual'})", format_inr(cg.adopted_cost_acq), "—"),
            ("Indexed Cost of Acquisition", "—", format_inr(cg.indexed_cost_acq) if comp.is_20_applicable else "N/A"),
            ("Actual Cost of Improvement", format_inr(cg.total_actual_improvement), "—"),
            ("Indexed Cost of Improvement", "—", format_inr(cg.total_indexed_improvement) if comp.is_20_applicable else "N/A"),
            ("Taxable Long-Term Capital Gain", format_inr(max(0.0, cg.ltcg_12_5)), format_inr(max(0.0, cg.ltcg_20 if cg.ltcg_20 is not None else 0)) if comp.is_20_applicable else "N/A"),
            ("Tax Rate", f"{m12.tax_rate_percent}%", f"{m20.tax_rate_percent}%" if m20 else "N/A"),
            ("Basic Tax", format_inr(m12.basic_tax), format_inr(m20.basic_tax) if m20 else "N/A"),
            (f"Surcharge ({m12.surcharge_rate_percent}%)", format_inr(m12.surcharge_amount), format_inr(m20.surcharge_amount) if m20 else "N/A"),
            (f"Health & Education Cess ({m12.cess_rate_percent}%)", format_inr(m12.cess_amount), format_inr(m20.cess_amount) if m20 else "N/A"),
            ("TOTAL TAX LIABILITY", format_inr(m12.total_tax_liability), format_inr(m20.total_tax_liability) if m20 else "N/A"),
            ("DIFFERENCE / TAX SAVING", format_inr(comp.tax_saving, show_paise=True) if comp.recommended_method_code == "12_5" else "—", format_inr(comp.tax_saving, show_paise=True) if comp.recommended_method_code == "20" else "—"),
        ]

        self.comp_table.setRowCount(len(rows))
        for r_idx, (particulars, val1, val2) in enumerate(rows):
            item_p = QTableWidgetItem(particulars)
            item_1 = QTableWidgetItem(val1)
            item_2 = QTableWidgetItem(val2)

            item_1.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_2.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Bold highlighting for totals and savings
            if "TOTAL" in particulars or "Net" in particulars or "Taxable" in particulars or "SAVING" in particulars:
                font = item_p.font()
                font.setBold(True)
                item_p.setFont(font)
                item_1.setFont(font)
                item_2.setFont(font)

            self.comp_table.setItem(r_idx, 0, item_p)
            self.comp_table.setItem(r_idx, 1, item_1)
            self.comp_table.setItem(r_idx, 2, item_2)

        # Build Detailed Step-by-Step String (19 items from prompt Section 17)
        imp_details_str = "\n".join(
            [f"     - {imp.particulars} ({imp.date_of_improvement}, FY {imp.fy_of_improvement}): Actual: {format_inr(imp.amount)} | CII: {imp.cii_improvement} | Indexed: {format_inr(imp.indexed_amount)}" for imp in cg.improvements]
        ) if cg.improvements else "     - None incurred."

        details_text = f"""
========================================================================================
DETAILED STATUTORY COMPUTATION AUDIT TRAIL (Section 17 Analysis)
========================================================================================
1.  Gross Sale Consideration:                    {format_inr(cg.gross_sale_price)}
2.  Transfer / Selling Expenses:                 {format_inr(cg.transfer_expenses)}
3.  Net Sale Consideration:                      {format_inr(cg.net_sale_price)}
4.  Acquisition Cost (Actual / Adopted):         {format_inr(cg.adopted_cost_acq)} ({cg.pre_2001_notes or 'Standard acquisition'})
5.  Acquisition Financial Year:                  FY {cg.acq_fy}
6.  Acquisition Cost Inflation Index (CII):      {cg.acq_cii}
7.  Indexed Acquisition Cost:                    {format_inr(cg.indexed_cost_acq)}
8.  Actual Improvement Costs:                    {format_inr(cg.total_actual_improvement)}
9.  Improvement Years & Line Items:
{imp_details_str}
10. Relevant Transfer CII:                       {cg.sale_cii} (FY {cg.financial_year_transfer})
11. Total Indexed Improvement Cost:              {format_inr(cg.total_indexed_improvement)}
12. Capital Gain under each method:
    - 12.5% Unindexed Capital Gain:              {format_inr(cg.ltcg_12_5)}
    - 20% Indexed Capital Gain:                  {format_inr(cg.ltcg_20 if cg.ltcg_20 is not None else 0) if comp.is_20_applicable else 'Not Applicable'}
13. Applicable Tax Rates:                        12.5% (New) vs. 20.0% (Grandfathered)
14. Basic Tax:                                   12.5%: {format_inr(m12.basic_tax)} | 20%: {format_inr(m20.basic_tax if m20 else 0)}
15. Surcharge:                                   12.5%: {format_inr(m12.surcharge_amount)} ({m12.surcharge_rate_percent}%) | 20%: {format_inr(m20.surcharge_amount if m20 else 0)}
16. Health & Education Cess:                     12.5%: {format_inr(m12.cess_amount)} (4%) | 20%: {format_inr(m20.cess_amount if m20 else 0)}
17. Total Tax Liability:                         12.5%: {format_inr(m12.total_tax_liability)} | 20%: {format_inr(m20.total_tax_liability if m20 else 0)}
18. Tax Difference:                              {format_inr(comp.tax_saving, show_paise=True)}
19. Recommended Method for Assessee:             {comp.recommended_method}
========================================================================================
Statutory Basis: {comp.detailed_statutory_note}
========================================================================================
"""
        self.details_content.setText(details_text.strip())

    def _toggle_detailed_view(self):
        is_vis = self.details_content.isVisible()
        self.details_content.setVisible(not is_vis)
        self.btn_toggle_details.setText(
            "▼ Hide Detailed Step-by-Step Statutory Breakdown" if not is_vis else "▶ View Detailed Step-by-Step Statutory Breakdown (19 Items)"
        )

    def _export_pdf(self):
        if not self.current_comparison:
            QMessageBox.warning(self, "No Calculation", "Please calculate a transaction before generating a report.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Capital Gains PDF Report",
            f"CGT_Comparison_Report_{self.current_comparison.cg_result.assessee_name.replace(' ', '_')}.pdf",
            "PDF Files (*.pdf)",
        )
        if file_path:
            try:
                generate_pdf_report(self.current_comparison, file_path)
                QMessageBox.information(self, "Report Generated", f"PDF Report successfully saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to generate PDF: {str(e)}")

    def _export_excel(self):
        if not self.current_comparison:
            QMessageBox.warning(self, "No Calculation", "Please calculate a transaction before generating a report.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to Excel Workbook",
            f"CGT_Comparison_{self.current_comparison.cg_result.assessee_name.replace(' ', '_')}.xlsx",
            "Excel Files (*.xlsx)",
        )
        if file_path:
            try:
                generate_excel_report(self.current_comparison, file_path)
                QMessageBox.information(self, "Report Exported", f"Excel Workbook successfully saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export Excel: {str(e)}")

    def _export_word(self):
        if not self.current_comparison:
            QMessageBox.warning(self, "No Calculation", "Please calculate a transaction before generating a report.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to Word Memorandum",
            f"CGT_Comparison_Memo_{self.current_comparison.cg_result.assessee_name.replace(' ', '_')}.docx",
            "Word Documents (*.docx)",
        )
        if file_path:
            try:
                generate_word_report(self.current_comparison, file_path)
                QMessageBox.information(self, "Report Exported", f"Word Memorandum successfully saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export Word memo: {str(e)}")
