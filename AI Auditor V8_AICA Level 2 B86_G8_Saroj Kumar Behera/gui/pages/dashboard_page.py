"""
AI Auditor V8 - Dashboard Page
Overview screen displaying entity header, key KPI metric cards, performance charts, and audit summary status.
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QPushButton, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont

from gui.widgets.metric_card import MetricCard
from core.models import FinancialModel
from reports.chart_generator import ChartGenerator

class DashboardPage(QWidget):
    navigate_requested = pyqtSignal(str)  # signal to switch page

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model: FinancialModel = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Page Header
        top_bar = QHBoxLayout()
        header_vbox = QVBoxLayout()
        self.lbl_title = QLabel("Executive Dashboard")
        self.lbl_title.setProperty("class", "page-title")
        self.lbl_subtitle = QLabel("Overview of financial health, key performance indicators, and audit review status.")
        self.lbl_subtitle.setProperty("class", "page-subtitle")
        header_vbox.addWidget(self.lbl_title)
        header_vbox.addWidget(self.lbl_subtitle)
        top_bar.addLayout(header_vbox)
        top_bar.addStretch()

        self.btn_upload = QPushButton("Upload New File")
        self.btn_upload.setProperty("class", "primary-btn")
        self.btn_upload.clicked.connect(lambda: self.navigate_requested.emit("upload"))
        top_bar.addWidget(self.btn_upload)
        main_layout.addLayout(top_bar)

        # Scroll Area for Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(16)

        # 1. Company Banner Card
        self.banner_card = QFrame()
        self.banner_card.setProperty("class", "card-highlight")
        b_layout = QGridLayout(self.banner_card)
        b_layout.setContentsMargins(16, 12, 16, 12)
        b_layout.setHorizontalSpacing(24)
        b_layout.setVerticalSpacing(6)

        self.lbl_comp_name = QLabel("No Financial Statement Loaded")
        self.lbl_comp_name.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E293B;")
        b_layout.addWidget(self.lbl_comp_name, 0, 0, 1, 2)

        self.lbl_meta_period = QLabel("Period: -")
        self.lbl_meta_period.setStyleSheet("color: #64748B; font-size: 12px;")
        b_layout.addWidget(self.lbl_meta_period, 1, 0)

        self.lbl_meta_unit = QLabel("Unit: -")
        self.lbl_meta_unit.setStyleSheet("color: #64748B; font-size: 12px;")
        b_layout.addWidget(self.lbl_meta_unit, 1, 1)

        self.lbl_meta_file = QLabel("File: -")
        self.lbl_meta_file.setStyleSheet("color: #64748B; font-size: 12px;")
        b_layout.addWidget(self.lbl_meta_file, 1, 2)

        self.content_layout.addWidget(self.banner_card)

        # 2. KPI Cards Grid
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(12)

        self.card_rev = MetricCard("Revenue from Operations", "-", "-", "Normal")
        self.card_ebitda = MetricCard("EBITDA", "-", "-", "Normal")
        self.card_pat = MetricCard("Profit After Tax (PAT)", "-", "-", "Normal")
        self.card_cr = MetricCard("Current Ratio", "-", "-", "Normal")

        self.kpi_grid.addWidget(self.card_rev, 0, 0)
        self.kpi_grid.addWidget(self.card_ebitda, 0, 1)
        self.kpi_grid.addWidget(self.card_pat, 0, 2)
        self.kpi_grid.addWidget(self.card_cr, 0, 3)

        self.content_layout.addLayout(self.kpi_grid)

        # 3. Charts & Findings Section
        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)

        # Chart Frame
        self.chart_frame = QFrame()
        self.chart_frame.setProperty("class", "card")
        c_layout = QVBoxLayout(self.chart_frame)
        c_layout.setContentsMargins(12, 12, 12, 12)
        lbl_c_title = QLabel("Financial Performance Trajectory")
        lbl_c_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        c_layout.addWidget(lbl_c_title)
        
        self.lbl_chart_img = QLabel("Performance chart will be rendered once data is loaded.")
        self.lbl_chart_img.setAlignment(Qt.AlignCenter)
        self.lbl_chart_img.setMinimumHeight(220)
        self.lbl_chart_img.setStyleSheet("color: #94A3B8; font-style: italic;")
        c_layout.addWidget(self.lbl_chart_img)
        mid_row.addWidget(self.chart_frame, 3)

        # Audit Findings Summary Card
        self.findings_card = QFrame()
        self.findings_card.setProperty("class", "card")
        f_layout = QVBoxLayout(self.findings_card)
        f_layout.setContentsMargins(16, 14, 16, 14)
        f_layout.setSpacing(10)

        lbl_f_title = QLabel("Audit Diagnostics Summary")
        lbl_f_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        f_layout.addWidget(lbl_f_title)

        self.lbl_var_count = QLabel("• Significant Variations: -")
        self.lbl_var_count.setStyleSheet("color: #475569; font-size: 12.5px;")
        f_layout.addWidget(self.lbl_var_count)

        self.lbl_risk_count = QLabel("• Potential Risk Areas: -")
        self.lbl_risk_count.setStyleSheet("color: #475569; font-size: 12.5px;")
        f_layout.addWidget(self.lbl_risk_count)

        self.lbl_audit_doc_count = QLabel("• Audit Verification Requirements: -")
        self.lbl_audit_doc_count.setStyleSheet("color: #475569; font-size: 12.5px;")
        f_layout.addWidget(self.lbl_audit_doc_count)

        f_layout.addStretch()

        btn_view_report = QPushButton("Export Full Report (Excel / Word)")
        btn_view_report.setProperty("class", "secondary-btn")
        btn_view_report.clicked.connect(lambda: self.navigate_requested.emit("export"))
        f_layout.addWidget(btn_view_report)

        mid_row.addWidget(self.findings_card, 2)
        self.content_layout.addLayout(mid_row)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def load_model(self, model: FinancialModel):
        self.model = model
        self.lbl_comp_name.setText(model.company_info.name)
        
        periods = model.periods
        p_curr = periods[0] if periods else "FY 2023-24"
        p_prev = periods[1] if len(periods) > 1 else "FY 2022-23"

        self.lbl_meta_period.setText(f"Period: {p_curr} vs {p_prev}")
        self.lbl_meta_unit.setText(f"Unit: {model.company_info.unit_label}")
        self.lbl_meta_file.setText(f"File: {model.company_info.source_file or 'Uploaded Statement'}")

        # Update KPI Cards
        rev_cy = model.profit_loss.get_value_by_key("revenue_operations", p_curr, 0.0)
        rev_py = model.profit_loss.get_value_by_key("revenue_operations", p_prev, 0.0)
        rev_diff = rev_cy - rev_py
        rev_pct = (rev_diff / abs(rev_py) * 100) if rev_py != 0 else 0
        self.card_rev.update_data(
            f"{rev_cy:,.1f}",
            f"{rev_pct:+.1f}% YoY ({rev_diff:+,.1f})" if rev_py else "Current Period",
            "Growth" if rev_diff >= 0 else "Decline"
        )

        pbt_cy = model.profit_loss.get_value_by_key("profit_before_tax", p_curr, 0.0)
        fin_cy = model.profit_loss.get_value_by_key("finance_costs", p_curr, 0.0)
        dep_cy = model.profit_loss.get_value_by_key("depreciation_amortisation", p_curr, 0.0)
        ebitda_cy = pbt_cy + fin_cy + dep_cy
        self.card_ebitda.update_data(f"{ebitda_cy:,.1f}", "Operating Cash Profit", "Healthy" if ebitda_cy > 0 else "Loss")

        pat_cy = model.profit_loss.get_value_by_key("profit_after_tax", p_curr, 0.0)
        pat_py = model.profit_loss.get_value_by_key("profit_after_tax", p_prev, 0.0)
        pat_diff = pat_cy - pat_py
        self.card_pat.update_data(
            f"{pat_cy:,.1f}",
            f"Net Margin: {round(pat_cy/rev_cy*100, 1) if rev_cy else 0}%",
            "Healthy" if pat_cy > 0 else "Critical"
        )

        # Current Ratio
        cr_val = "-"
        cr_tag = "Normal"
        if "Liquidity Ratios" in model.ratios:
            for r in model.ratios["Liquidity Ratios"]:
                if r["name"] == "Current Ratio":
                    if r["current_value"] is not None:
                        cr_val = f"{r['current_value']:.2f}x"
                        cr_tag = r["status"]

        self.card_cr.update_data(cr_val, "Benchmark: >= 1.33x", cr_tag)

        # Findings Counts
        num_v = len(model.variations)
        num_r = len(model.risks)
        total_docs = sum(len(v.get("audit_verification", [])) for v in model.variations)

        self.lbl_var_count.setText(f"• Significant Variations: {num_v} line items (>= 5% threshold)")
        self.lbl_risk_count.setText(f"• Potential Risk Areas: {num_r} alerts flagged")
        self.lbl_audit_doc_count.setText(f"• Audit Verification Evidence: {total_docs} required items mapped")

        # Generate & Display Chart
        try:
            charts = ChartGenerator.generate_all_charts(model, "temp_charts")
            if "performance" in charts and os.path.exists(charts["performance"]):
                pixmap = QPixmap(charts["performance"]).scaled(520, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.lbl_chart_img.setPixmap(pixmap)
        except Exception as e:
            print(f"Error loading dashboard chart: {e}")
