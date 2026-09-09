"""
AI Auditor V8 - Significant Variation & Possible Reasons Page
Interactive variance screening with configurable threshold (default 5%) and CA audit reason inspection.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QSplitter
)
from PyQt5.QtCore import Qt
from core.models import FinancialModel
from analysis.variance_engine import VarianceEngine

class VariancePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model: FinancialModel = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        header_vbox = QVBoxLayout()
        lbl_title = QLabel("Significant Variation & Possible Reasons Analysis")
        lbl_title.setProperty("class", "page-title")
        lbl_sub = QLabel("Filter line items exceeding variance threshold, view professional possible reasons, and review verification steps.")
        lbl_sub.setProperty("class", "page-subtitle")
        header_vbox.addWidget(lbl_title)
        header_vbox.addWidget(lbl_sub)
        top_bar.addLayout(header_vbox)
        top_bar.addStretch()

        # Threshold Filter Control
        thresh_box = QHBoxLayout()
        thresh_box.addWidget(QLabel("<b>Variance Threshold:</b>"))
        self.spin_thresh = QDoubleSpinBox()
        self.spin_thresh.setRange(0.1, 100.0)
        self.spin_thresh.setValue(5.0)
        self.spin_thresh.setSingleStep(1.0)
        self.spin_thresh.setSuffix(" %")
        self.spin_thresh.valueChanged.connect(self._on_threshold_changed)
        thresh_box.addWidget(self.spin_thresh)
        top_bar.addLayout(thresh_box)

        main_layout.addLayout(top_bar)

        # Splitter: Table on top, Details on bottom
        splitter = QSplitter(Qt.Vertical)

        # 1. Variance Table
        self.table_var = QTableWidget()
        self.table_var.setAlternatingRowColors(True)
        self.table_var.setShowGrid(True)
        self.table_var.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_var.horizontalHeader().setStretchLastSection(True)
        self.table_var.verticalHeader().setVisible(False)
        self.table_var.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_var.itemSelectionChanged.connect(self._on_row_selected)
        splitter.addWidget(self.table_var)

        # 2. Detail Card
        detail_card = QFrame()
        detail_card.setProperty("class", "card")
        d_layout = QVBoxLayout(detail_card)
        d_layout.setContentsMargins(14, 12, 14, 12)
        d_layout.setSpacing(8)

        self.lbl_detail_title = QLabel("Select a line item above to inspect Possible Reasons and Audit Evidence Requirements.")
        self.lbl_detail_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        d_layout.addWidget(self.lbl_detail_title)

        self.txt_details = QTextEdit()
        self.txt_details.setReadOnly(True)
        self.txt_details.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; font-size: 12.5px; padding: 8px;")
        d_layout.addWidget(self.txt_details)

        splitter.addWidget(detail_card)
        splitter.setSizes([350, 220])

        main_layout.addWidget(splitter)

    def load_model(self, model: FinancialModel):
        self.model = model
        self._refresh_table()

    def _on_threshold_changed(self, val: float):
        if self.model:
            VarianceEngine.analyze_variations(self.model, threshold_pct=val)
            self._refresh_table()

    def _refresh_table(self):
        if not self.model or not self.model.variations:
            self.table_var.clear()
            self.table_var.setRowCount(0)
            self.txt_details.setText("No line items meet the current variance threshold.")
            return

        headers = ["Statement", "Particulars", "Previous Period", "Current Period", "Absolute Change", "YoY % Change", "Movement", "Risk Level"]
        self.table_var.clear()
        self.table_var.setColumnCount(len(headers))
        self.table_var.setRowCount(len(self.model.variations))
        self.table_var.setHorizontalHeaderLabels(headers)

        for r_idx, v in enumerate(self.model.variations):
            self.table_var.setItem(r_idx, 0, QTableWidgetItem(v["statement"]))
            self.table_var.setItem(r_idx, 1, QTableWidgetItem(v["particulars"]))

            c_py = QTableWidgetItem(f"{v['previous_period_amount']:,.2f}")
            c_py.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_var.setItem(r_idx, 2, c_py)

            c_cy = QTableWidgetItem(f"{v['current_period_amount']:,.2f}")
            c_cy.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_var.setItem(r_idx, 3, c_cy)

            c_df = QTableWidgetItem(f"{v['absolute_change']:+,.2f}")
            c_df.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_var.setItem(r_idx, 4, c_df)

            c_pc = QTableWidgetItem(f"{v['percentage_change']:+.1f}%")
            c_pc.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_var.setItem(r_idx, 5, c_pc)

            c_dir = QTableWidgetItem(v["direction"])
            c_dir.setTextAlignment(Qt.AlignCenter)
            self.table_var.setItem(r_idx, 6, c_dir)

            c_rk = QTableWidgetItem(v["risk_level"])
            c_rk.setTextAlignment(Qt.AlignCenter)
            self.table_var.setItem(r_idx, 7, c_rk)

        self.table_var.resizeColumnsToContents()
        self.table_var.setColumnWidth(1, 280)

        # Select first row by default
        if self.table_var.rowCount() > 0:
            self.table_var.selectRow(0)

    def _on_row_selected(self):
        sel = self.table_var.selectedItems()
        if not sel:
            return
        row = sel[0].row()
        if row < len(self.model.variations):
            v = self.model.variations[row]
            self.lbl_detail_title.setText(f"Analytical Breakdown: {v['particulars']} ({v['statement']}) — {v['direction']} of {v['percentage_change']:+.1f}%")

            reasons_html = "<b>POSSIBLE REASONS (Professional Hypotheses):</b><br><ul>"
            for r in v["possible_reasons"]:
                reasons_html += f"<li>{r}</li>"
            reasons_html += "</ul><br>"

            docs_html = "<b>AUDIT VERIFICATION REQUIREMENTS (Documents & Rationale):</b><br><ul>"
            for d in v["audit_verification"]:
                docs_html += f"<li><b>{d['doc']}</b>: {d['why']}</li>"
            docs_html += "</ul>"

            html = f"""
            <div style="font-family: 'Segoe UI', Arial; color: #1E293B; line-height: 1.4;">
                <p style="color: #64748B; font-style: italic; font-size: 11px;">
                    Note: Explanations are based strictly upon available financial trends and do not represent confirmed facts. Independent verification of primary records is required.
                </p>
                {reasons_html}
                {docs_html}
            </div>
            """
            self.txt_details.setHtml(html)
