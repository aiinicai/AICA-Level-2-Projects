"""
AI Auditor V8 - Financial Ratio Analysis Page
Interactive ratio dashboard displaying 30 ratios across Liquidity, Profitability, Solvency, and Efficiency.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTabWidget,
    QScrollArea, QGridLayout, QPushButton
)
from PyQt5.QtCore import Qt
from core.models import FinancialModel

class RatioPage(QWidget):
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
        lbl_title = QLabel("Financial Ratio Analysis")
        lbl_title.setProperty("class", "page-title")
        lbl_sub = QLabel("Comprehensive calculation of 30 standard financial ratios with formulas, benchmarks, and audit interpretations.")
        lbl_sub.setProperty("class", "page-subtitle")
        header_vbox.addWidget(lbl_title)
        header_vbox.addWidget(lbl_sub)
        top_bar.addLayout(header_vbox)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        # Tabs for categories
        self.tabs = QTabWidget()
        self.tab_liquidity = self._create_scrollable_tab()
        self.tab_profitability = self._create_scrollable_tab()
        self.tab_solvency = self._create_scrollable_tab()
        self.tab_activity = self._create_scrollable_tab()
        self.tab_cashflow = self._create_scrollable_tab()

        self.tabs.addTab(self.tab_liquidity["widget"], "Liquidity Ratios")
        self.tabs.addTab(self.tab_profitability["widget"], "Profitability Ratios")
        self.tabs.addTab(self.tab_solvency["widget"], "Solvency & Leverage")
        self.tabs.addTab(self.tab_activity["widget"], "Activity & Efficiency")
        self.tabs.addTab(self.tab_cashflow["widget"], "Cash Flow & Key Metrics")

        main_layout.addWidget(self.tabs)

    def _create_scrollable_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        scroll.setWidget(container)

        return {"widget": scroll, "layout": layout}

    def load_model(self, model: FinancialModel):
        self.model = model
        if not model.ratios:
            return

        cat_map = {
            "Liquidity Ratios": self.tab_liquidity["layout"],
            "Profitability Ratios": self.tab_profitability["layout"],
            "Solvency & Leverage Ratios": self.tab_solvency["layout"],
            "Activity & Efficiency Ratios": self.tab_activity["layout"],
            "Cash Flow & Key Metrics": self.tab_cashflow["layout"]
        }

        # Clear existing
        for _, l in cat_map.items():
            while l.count():
                item = l.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        for cat_name, r_list in model.ratios.items():
            if cat_name in cat_map:
                layout = cat_map[cat_name]
                for r in r_list:
                    card = self._build_ratio_card(r)
                    layout.addWidget(card)
                layout.addStretch()

    def _build_ratio_card(self, r: dict) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # Top line: Ratio Name + Status Badge
        top_row = QHBoxLayout()
        lbl_name = QLabel(r["name"])
        lbl_name.setStyleSheet("font-size: 14px; font-weight: bold; color: #1E293B;")
        top_row.addWidget(lbl_name)
        top_row.addStretch()

        lbl_status = QLabel(f" {r['status']} ")
        status_lower = r["status"].lower()
        if "healthy" in status_lower:
            lbl_status.setStyleSheet("background-color: #DEF7EC; color: #03543F; font-size: 11px; font-weight: bold; border-radius: 4px; padding: 2px 8px;")
        elif "attention" in status_lower or "medium" in status_lower:
            lbl_status.setStyleSheet("background-color: #FEF08A; color: #854D0E; font-size: 11px; font-weight: bold; border-radius: 4px; padding: 2px 8px;")
        elif "critical" in status_lower:
            lbl_status.setStyleSheet("background-color: #FEE2E2; color: #991B1B; font-size: 11px; font-weight: bold; border-radius: 4px; padding: 2px 8px;")
        else:
            lbl_status.setStyleSheet("background-color: #F1F5F9; color: #475569; font-size: 11px; font-weight: bold; border-radius: 4px; padding: 2px 8px;")
        top_row.addWidget(lbl_status)
        layout.addLayout(top_row)

        # Formula
        lbl_form = QLabel(f"Formula: {r['formula']}")
        lbl_form.setStyleSheet("color: #64748B; font-size: 11.5px; font-style: italic;")
        layout.addWidget(lbl_form)

        # Values Row
        val_row = QHBoxLayout()
        val_row.setSpacing(20)

        p_curr = self.model.periods[0] if self.model and self.model.periods else "Current"
        p_prev = self.model.periods[1] if self.model and len(self.model.periods) > 1 else "Previous"

        val_cy_txt = f"{r['current_value']:,.2f} {r['unit']}" if r['current_value'] is not None else "N/A"
        val_py_txt = f"{r['previous_value']:,.2f} {r['unit']}" if r['previous_value'] is not None else "N/A"

        lbl_cy = QLabel(f"<b>{p_curr}:</b> {val_cy_txt}")
        lbl_cy.setStyleSheet("font-size: 13px; color: #0F172A;")
        val_row.addWidget(lbl_cy)

        lbl_py = QLabel(f"<b>{p_prev}:</b> {val_py_txt}")
        lbl_py.setStyleSheet("font-size: 13px; color: #475569;")
        val_row.addWidget(lbl_py)

        if r["absolute_change"] is not None:
            chg_txt = f"{r['absolute_change']:+,.2f}"
            lbl_chg = QLabel(f"<b>YoY Change:</b> {chg_txt}")
            lbl_chg.setStyleSheet("font-size: 13px; color: #2563EB;")
            val_row.addWidget(lbl_chg)

        lbl_bm = QLabel(f"<b>Benchmark:</b> {r['benchmark']}")
        lbl_bm.setStyleSheet("font-size: 12px; color: #64748B;")
        val_row.addWidget(lbl_bm)
        val_row.addStretch()

        layout.addLayout(val_row)

        # Interpretation
        lbl_interp = QLabel(f"<b>CA Interpretation:</b> {r['interpretation']}")
        lbl_interp.setStyleSheet("color: #334155; font-size: 12px; background-color: #F8FAFC; border-radius: 4px; padding: 6px 10px;")
        lbl_interp.setWordWrap(True)
        layout.addWidget(lbl_interp)

        return card
