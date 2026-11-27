"""Read-only data table with number formatting and PASS/FAIL colouring."""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView

from gui.theme import STATUS_COLOURS


def fmt_amount(v, unit="lakh"):
    if v is None or v == "":
        return ""
    if isinstance(v, str):
        return v
    if unit == "lakh":
        return "{:,.2f}".format(v / 1e5)
    return "{:,.0f}".format(v)


class DataTable(QTableWidget):
    def __init__(self, parent=None, stretch_first=True):
        super().__init__(parent)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.stretch_first = stretch_first
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def load(self, headers, rows, bold_rows=(), status_cols=None):
        self.clear()
        self.setColumnCount(len(headers))
        self.setRowCount(len(rows))
        self.setHorizontalHeaderLabels([str(h) for h in headers])
        bold = QFont()
        bold.setBold(True)
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                it = QTableWidgetItem("" if v is None else str(v))
                if c > 0:
                    it.setTextAlignment(int(Qt.AlignRight | Qt.AlignVCenter))
                sv = str(v)
                if sv in STATUS_COLOURS and (status_cols is None or c in status_cols):
                    it.setBackground(QColor(STATUS_COLOURS[sv]))
                    it.setTextAlignment(int(Qt.AlignCenter))
                if r in bold_rows:
                    it.setFont(bold)
                self.setItem(r, c, it)
        hh = self.horizontalHeader()
        if self.stretch_first and headers:
            hh.setSectionResizeMode(0, QHeaderView.Stretch)
            for c in range(1, len(headers)):
                hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        else:
            hh.setSectionResizeMode(QHeaderView.ResizeToContents)
