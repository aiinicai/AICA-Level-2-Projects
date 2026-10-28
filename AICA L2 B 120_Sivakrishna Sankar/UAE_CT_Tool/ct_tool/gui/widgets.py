"""Small reusable Qt helpers."""
from __future__ import annotations

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDoubleSpinBox, QFrame, QHeaderView, QLabel, QMessageBox, QPlainTextEdit, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

RISK_COLOURS = {"High": "#F8CBAD", "Medium": "#FFF2CC", "Low": "#E2EFDA"}
STATUS_COLOURS = {"Confirmed": "#E2EFDA", "Proposed": "#FFF2CC", "Rejected": "#EDEDED", "Potential adjustment": "#FFF2CC",
                  "Information required": "#FCE4D6", "Technical review required": "#DDEBF7", "PASS": "#E2EFDA", "FAIL": "#F8CBAD", "WARN": "#FFF2CC", "INFO": "#DDEBF7"}


class Worker(QThread):
    """Runs fn(*args) off the GUI thread."""
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args, parent=None):
        super().__init__(parent)
        self.fn, self.args = fn, args

    def run(self):
        try:
            self.done.emit(self.fn(*self.args))
        except Exception as e:     # noqa: BLE001 - surfaced to the user
            self.failed.emit(f"{type(e).__name__}: {e}")


def money(x, dp=0):
    if x is None or x == "":
        return ""
    try:
        if abs(x) < 0.5 * 10 ** -dp:
            x = 0.0
        return f"{x:,.{dp}f}" if x >= 0 else f"({-x:,.{dp}f})"
    except Exception:
        return str(x)


def item(text="", align_right=False, colour=None, editable=False, tooltip=None, bold=False):
    it = QTableWidgetItem("" if text is None else str(text))
    if align_right:
        it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    if colour:
        it.setBackground(QBrush(QColor(colour)))
    if not editable:
        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    if tooltip:
        it.setToolTip(str(tooltip))
    if bold:
        f = it.font()
        f.setBold(True)
        it.setFont(f)
    return it


def make_table(headers, stretch_col=None, select_rows=True) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    t.setSelectionBehavior(QAbstractItemView.SelectRows if select_rows else QAbstractItemView.SelectItems)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    t._wide_col = stretch_col          # this column gets the most room (see fill_table)
    t.setWordWrap(True)
    return t


def fill_table(t: QTableWidget, rows, colour_col=None, colours=None, right_cols=()):
    t.setSortingEnabled(False)
    t.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            col = (colours or STATUS_COLOURS).get(str(v)) if colour_col == c else None
            t.setItem(r, c, item(v, align_right=c in right_cols, colour=col))
    t.resizeColumnsToContents()
    wide = getattr(t, "_wide_col", None)
    for c in range(t.columnCount()):
        cap = 520 if c == wide else 280
        floor = 360 if c == wide else 0
        t.setColumnWidth(c, max(floor, min(t.columnWidth(c), cap)))
    t.resizeRowsToContents()


def heading(text, size=13) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(f"font-size:{size}pt; font-weight:bold; color:#283A4A;")
    return l


def hint(text) -> QLabel:
    l = QLabel(text)
    l.setWordWrap(True)
    l.setStyleSheet("color:#595959;")
    return l


def banner(text, colour="#FFF2CC") -> QLabel:
    l = QLabel(text)
    l.setWordWrap(True)
    l.setStyleSheet(f"background:{colour}; padding:6px; border:1px solid #BBBBBB;")
    return l


def hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setFrameShadow(QFrame.Sunken)
    return f


def rate_spin() -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setDecimals(6)
    s.setRange(0.0, 1_000_000.0)
    s.setSingleStep(0.0001)
    s.setGroupSeparatorShown(False)
    return s


def money_spin() -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setDecimals(2)
    s.setRange(-1e13, 1e13)
    s.setGroupSeparatorShown(True)
    return s


def info(parent, title, text):
    QMessageBox.information(parent, title, text)


def warn(parent, title, text):
    QMessageBox.warning(parent, title, text)


def ask(parent, title, text) -> bool:
    return QMessageBox.question(parent, title, text, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes


def readonly_text(h=120) -> QPlainTextEdit:
    t = QPlainTextEdit()
    t.setReadOnly(True)
    t.setMaximumHeight(h)
    return t


def vbox(*widgets, margins=6) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(margins, margins, margins, margins)
    for x in widgets:
        lay.addWidget(x)
    return w
