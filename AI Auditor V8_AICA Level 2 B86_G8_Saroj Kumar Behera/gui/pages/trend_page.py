"""
AI Auditor V8 - Trend & Common-Size Analysis Page
Displays horizontal YoY trends and vertical common-size statements.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt
from core.models import FinancialModel
from analysis.trend_engine import TrendEngine

class TrendPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model: FinancialModel = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header
        lbl_title = QLabel("Horizontal & Vertical Trend Analysis")
        lbl_title.setProperty("class", "page-title")
        lbl_sub = QLabel("Year-on-Year percentage movements, absolute changes, and vertical common-size analysis.")
        lbl_sub.setProperty("class", "page-subtitle")
        main_layout.addWidget(lbl_title)
        main_layout.addWidget(lbl_sub)

        # Tabs for BS, P&L, CF
        self.tabs = QTabWidget()
        self.table_bs = self._create_trend_table()
        self.table_pl = self._create_trend_table()
        self.table_cf = self._create_trend_table()

        self.tabs.addTab(self.table_pl, "Profit & Loss Trends (% of Revenue)")
        self.tabs.addTab(self.table_bs, "Balance Sheet Trends (% of Total Assets)")
        self.tabs.addTab(self.table_cf, "Cash Flow Trends")
        main_layout.addWidget(self.tabs)

    def _create_trend_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setShowGrid(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        return table

    def load_model(self, model: FinancialModel):
        self.model = model
        trends = TrendEngine.analyze_trends(model)

        self._populate_trend_table(self.table_pl, trends.get("profit_loss_trends", []))
        self._populate_trend_table(self.table_bs, trends.get("balance_sheet_trends", []))
        self._populate_trend_table(self.table_cf, trends.get("cash_flow_trends", []))

    def _populate_trend_table(self, table: QTableWidget, rows: list):
        headers = ["Particulars", "Current Period", "Previous Period", "YoY Abs Change", "YoY % Change", "Common Size %", "Movement"]
        table.clear()
        table.setColumnCount(len(headers))
        table.setRowCount(len(rows))
        table.setHorizontalHeaderLabels(headers)

        for r_idx, r in enumerate(rows):
            # Particulars
            c_part = QTableWidgetItem(r["particulars"])
            table.setItem(r_idx, 0, c_part)

            # CY
            c_cy = QTableWidgetItem(f"{r['cy_value']:,.2f}")
            c_cy.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(r_idx, 1, c_cy)

            # PY
            c_py = QTableWidgetItem(f"{r['py_value']:,.2f}" if r['py_value'] is not None else "-")
            c_py.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(r_idx, 2, c_py)

            # Abs Change
            c_df = QTableWidgetItem(f"{r['abs_change']:+,.2f}" if r['abs_change'] is not None else "-")
            c_df.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(r_idx, 3, c_df)

            # Pct Change
            c_pc = QTableWidgetItem(f"{r['pct_change']:+.1f}%" if r['pct_change'] is not None else "-")
            c_pc.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(r_idx, 4, c_pc)

            # Common size %
            c_cs = QTableWidgetItem(f"{r['common_size_cy']:.1f}%")
            c_cs.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(r_idx, 5, c_cs)

            # Direction
            c_dir = QTableWidgetItem(r["trend_direction"])
            c_dir.setTextAlignment(Qt.AlignCenter)
            table.setItem(r_idx, 6, c_dir)

        table.resizeColumnsToContents()
        table.setColumnWidth(0, 320)
