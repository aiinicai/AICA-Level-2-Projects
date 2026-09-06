"""
CAPITAL GAINS TAX COMPARISON CALCULATOR (12.5% vs 20%)
Executive Dashboard View (PyQt6)
Author: Senior Python Developer & Tax-Audit Software Architect
"""

from typing import List, Dict, Any
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
)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.widgets import MetricCard
from database import get_db_connection
from utils import format_inr


class DashboardView(QWidget):
    """Executive summary and recent activity dashboard."""

    newCalculationRequested = pyqtSignal()
    loadCalculationRequested = pyqtSignal(int)
    openCiiRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
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

        # Welcome Banner
        banner = QFrame()
        banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #2563EB);
                border-radius: 10px;
                padding: 16px;
            }
        """)
        b_layout = QVBoxLayout(banner)
        b_title = QLabel("CAPITAL GAINS TAX COMPARISON – 12.5% vs 20%")
        b_title.setStyleSheet("font-size: 20px; font-weight: 900; color: #FFFFFF;")
        b_sub = QLabel(
            "Dual Statutory Assessment Engine under the Income-tax Act, 1961 (Finance (No. 2) Act, 2024 Regime)\n"
            "Evaluates Section 112 unindexed flat 12.5% rate against the grandfathered 20% indexed method to determine optimal assessee relief."
        )
        b_sub.setStyleSheet("font-size: 11.5px; color: #DBEAFE; margin-top: 4px;")
        b_layout.addWidget(b_title)
        b_layout.addWidget(b_sub)

        # Quick action buttons inside banner
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.btn_new = QPushButton("➕ Start New Calculation")
        self.btn_new.setStyleSheet("background-color: #FFFFFF; color: #1E3A8A; font-weight: bold; padding: 8px 18px;")
        self.btn_new.clicked.connect(self.newCalculationRequested.emit)
        btn_layout.addWidget(self.btn_new)

        self.btn_cii = QPushButton("📅 Cost Inflation Index (CII) Master")
        self.btn_cii.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); color: #FFFFFF; font-weight: bold; border: 1px solid #FFFFFF; padding: 8px 18px;")
        self.btn_cii.clicked.connect(self.openCiiRequested.emit)
        btn_layout.addWidget(self.btn_cii)

        btn_layout.addStretch()
        b_layout.addLayout(btn_layout)

        layout.addWidget(banner)

        # Summary Metric Cards
        metric_grid = QGridLayout()
        metric_grid.setSpacing(12)

        self.card_total_calc = MetricCard("TOTAL CALCULATIONS", "0", "Evaluated in this system")
        self.card_12_favoured = MetricCard("12.5% METHOD FAVOURED", "0", "Lower tax without indexation", card_type="default")
        self.card_20_favoured = MetricCard("20% INDEXED FAVOURED", "0", "Indexation benefit preserved", card_type="primary")
        self.card_total_savings = MetricCard("TOTAL TAX SAVINGS IDENTIFIED", "₹0", "Cumulative client benefit", card_type="success")

        metric_grid.addWidget(self.card_total_calc, 0, 0)
        metric_grid.addWidget(self.card_12_favoured, 0, 1)
        metric_grid.addWidget(self.card_20_favoured, 0, 2)
        metric_grid.addWidget(self.card_total_savings, 0, 3)

        layout.addLayout(metric_grid)

        # Recent Calculations Section
        rec_card = QFrame()
        rec_card.setProperty("class", "contentCard")
        rec_layout = QVBoxLayout(rec_card)

        hdr_layout = QHBoxLayout()
        lbl_recent = QLabel("RECENT CAPITAL GAINS CALCULATIONS")
        lbl_recent.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E3A8A;")
        hdr_layout.addWidget(lbl_recent)
        hdr_layout.addStretch()

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setProperty("class", "secondaryBtn")
        self.btn_refresh.clicked.connect(self.refresh_data)
        hdr_layout.addWidget(self.btn_refresh)
        rec_layout.addLayout(hdr_layout)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(8)
        self.recent_table.setHorizontalHeaderLabels([
            "Date",
            "Assessee Name",
            "Asset Type",
            "Net Sale Price",
            "Tax (12.5%)",
            "Tax (20% Indexed)",
            "Recommended Option",
            "Tax Saving",
        ])
        self.recent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in [0, 2, 3, 4, 5, 6, 7]:
            self.recent_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.recent_table.setMinimumHeight(240)
        self.recent_table.cellDoubleClicked.connect(self._on_row_double_clicked)
        rec_layout.addWidget(self.recent_table)

        layout.addWidget(rec_card)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self.refresh_data()

    def refresh_data(self):
        """Fetches latest metrics and history from the SQLite database."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Summary Metrics
            cursor.execute("SELECT COUNT(*) FROM calculation_history")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM calculation_history WHERE recommended_method LIKE '%12.5%'")
            count_12 = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM calculation_history WHERE recommended_method LIKE '%20%'")
            count_20 = cursor.fetchone()[0]

            cursor.execute("SELECT SUM(tax_saving) FROM calculation_history")
            sum_savings = cursor.fetchone()[0] or 0.0

            self.card_total_calc.set_value(str(total))
            self.card_12_favoured.set_value(str(count_12))
            self.card_20_favoured.set_value(str(count_20))
            self.card_total_savings.set_value(format_inr(sum_savings))

            # Recent Table (Last 10)
            cursor.execute("""
                SELECT id, calculation_date, assessee_name, asset_type, net_sale_price,
                       total_tax_12_5, total_tax_20, is_20_applicable, recommended_method, tax_saving
                FROM calculation_history
                ORDER BY id DESC LIMIT 10
            """)
            rows = cursor.fetchall()
            self.recent_table.setRowCount(len(rows))

            for idx, r in enumerate(rows):
                self.recent_table.setItem(idx, 0, QTableWidgetItem(str(r["calculation_date"])[:16]))
                self.recent_table.setItem(idx, 1, QTableWidgetItem(r["assessee_name"]))
                self.recent_table.setItem(idx, 2, QTableWidgetItem(r["asset_type"]))

                item_sale = QTableWidgetItem(format_inr(r["net_sale_price"]))
                item_sale.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.recent_table.setItem(idx, 3, item_sale)

                item_12 = QTableWidgetItem(format_inr(r["total_tax_12_5"]))
                item_12.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.recent_table.setItem(idx, 4, item_12)

                tax_20_str = format_inr(r["total_tax_20"]) if r["is_20_applicable"] else "N/A"
                item_20 = QTableWidgetItem(tax_20_str)
                item_20.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.recent_table.setItem(idx, 5, item_20)

                item_rec = QTableWidgetItem(r["recommended_method"])
                font = item_rec.font()
                font.setBold(True)
                item_rec.setFont(font)
                self.recent_table.setItem(idx, 6, item_rec)

                item_sav = QTableWidgetItem(format_inr(r["tax_saving"]))
                item_sav.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.recent_table.setItem(idx, 7, item_sav)

                # Store ID in hidden user role
                self.recent_table.item(idx, 0).setData(Qt.ItemDataRole.UserRole, r["id"])

        finally:
            conn.close()

    def _on_row_double_clicked(self, row: int, col: int):
        item = self.recent_table.item(row, 0)
        if item:
            calc_id = item.data(Qt.ItemDataRole.UserRole)
            if calc_id:
                self.loadCalculationRequested.emit(calc_id)
