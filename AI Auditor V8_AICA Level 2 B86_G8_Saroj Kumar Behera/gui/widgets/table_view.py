"""
AI Auditor V8 - Financial Table Widget
Enhanced QTableWidget with formatting, auto column resizing, sorting, and alternate row colors.
"""

from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

class FinancialTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectRows)

    def populate(self, headers: list, rows_data: list, alignment_map: dict = None):
        """
        Populates table with headers and row data.
        alignment_map: dict mapping col_idx to Qt.AlignmentFlag (e.g. {1: Qt.AlignRight})
        """
        self.clear()
        self.setColumnCount(len(headers))
        self.setRowCount(len(rows_data))
        self.setHorizontalHeaderLabels(headers)

        bold_font = QFont("Segoe UI", 9)
        bold_font.setBold(True)

        for r_idx, row in enumerate(rows_data):
            is_total = False
            if row and any(kw in str(row[0]).upper() for kw in ["TOTAL", "PROFIT FOR THE PERIOD", "NET CASH"]):
                is_total = True

            for c_idx, val in enumerate(row):
                item = QTableWidgetItem()
                align = alignment_map.get(c_idx, Qt.AlignLeft | Qt.AlignVCenter) if alignment_map else (Qt.AlignRight | Qt.AlignVCenter if isinstance(val, (int, float)) else Qt.AlignLeft | Qt.AlignVCenter)

                if isinstance(val, float):
                    item.setText(f"{val:,.2f}")
                elif isinstance(val, int):
                    item.setText(f"{val:,}")
                else:
                    item.setText(str(val) if val is not None else "")

                item.setTextAlignment(align)
                if is_total:
                    item.setFont(bold_font)
                    item.setBackground(QColor("#F1F5F9"))

                self.setItem(r_idx, c_idx, item)

        self.resizeColumnsToContents()
