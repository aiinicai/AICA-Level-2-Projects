"""Shared UI helpers: blue-and-white theme, tables, number formatting, busy dialog, error handling."""
from __future__ import annotations

import datetime as dt
import traceback
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QDate, QEventLoop, Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QFrame, QHeaderView, QLabel, QLineEdit, QMessageBox,
                               QProgressDialog, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..engine import EngineError
from ..store import StoreError
from ..tally import TallyConfigError

BLUE = '#1F4E9C'
STYLE = f"""
QWidget {{ font-family: 'Segoe UI','Helvetica Neue',Arial; font-size: 10.5pt; color:#1b2a41; background:#ffffff; }}
QMainWindow, QStackedWidget > QWidget {{ background:#f4f8fd; }}
#Sidebar {{ background:{BLUE}; }}
#Sidebar QListWidget {{ background:{BLUE}; border:none; color:white; outline:0; }}
#Sidebar QListWidget::item {{ padding:12px 18px; }}
#Sidebar QListWidget::item:selected {{ background:#2f6bd0; color:white; border-left:4px solid #9cc4ff; }}
#Sidebar QLabel {{ color:white; background:transparent; font-size:13pt; font-weight:600; padding:18px; }}
QPushButton {{ background:{BLUE}; color:white; border:none; border-radius:6px; padding:7px 16px; }}
QPushButton:hover {{ background:#2f6bd0; }}
QPushButton:disabled {{ background:#b9c7df; }}
QPushButton[flat="true"], QPushButton#secondary {{ background:#e6effb; color:{BLUE}; }}
QLineEdit, QComboBox, QDateEdit, QSpinBox, QTextEdit, QPlainTextEdit {{ border:1px solid #b9c7df; border-radius:5px; padding:4px 6px; background:white; }}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{ border:1px solid {BLUE}; }}
QTableWidget {{ gridline-color:#dce6f5; alternate-background-color:#f1f6fd; selection-background-color:#cfe0fb; selection-color:#10233f; border:1px solid #c9d6ea; }}
QHeaderView::section {{ background:{BLUE}; color:white; padding:6px; border:none; font-weight:600; }}
QGroupBox {{ border:1px solid #c9d6ea; border-radius:8px; margin-top:14px; padding:10px; background:white; }}
QGroupBox::title {{ subcontrol-origin:margin; left:12px; color:{BLUE}; font-weight:700; }}
QTabWidget::pane {{ border:1px solid #c9d6ea; background:white; }}
QTabBar::tab {{ background:#e6effb; padding:8px 16px; margin-right:2px; }}
QTabBar::tab:selected {{ background:white; color:{BLUE}; font-weight:700; }}
#Card {{ background:white; border:1px solid #c9d6ea; border-radius:10px; }}
#CardValue {{ font-size:18pt; font-weight:700; color:{BLUE}; }}
#Title {{ font-size:16pt; font-weight:700; color:{BLUE}; background:transparent; }}
#Hint {{ color:#5a6b85; background:transparent; }}
"""


def money(x) -> str:
    try:
        return f'{Decimal(x):,.2f}'
    except (InvalidOperation, TypeError, ValueError):
        return str(x)


def title(text, hint=''):
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 6)
    t = QLabel(text); t.setObjectName('Title')
    lay.addWidget(t)
    if hint:
        h = QLabel(hint); h.setObjectName('Hint'); h.setWordWrap(True)
        lay.addWidget(h)
    return box


def make_table(headers, stretch_last=True):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setAlternatingRowColors(True)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(stretch_last)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    return t


def fill_table(t, rows, num_cols=(), colors=None):
    """rows: list of lists of str/Decimal/date. num_cols: indexes right-aligned and formatted with thousands separators."""
    t.setRowCount(0)
    t.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            txt = money(v) if (c in num_cols and v not in (None, '')) else ('' if v is None else str(v))
            it = QTableWidgetItem(txt)
            if c in num_cols:
                it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if isinstance(v, Decimal) and v < 0:
                    it.setForeground(QColor('#b42318'))
            if colors and colors.get(r):
                it.setBackground(QColor(colors[r]))
            t.setItem(r, c, it)
    t.resizeColumnsToContents()


def card(label, value):
    f = QFrame(); f.setObjectName('Card')
    lay = QVBoxLayout(f)
    a = QLabel(label); a.setObjectName('Hint')
    b = QLabel(value); b.setObjectName('CardValue')
    lay.addWidget(a); lay.addWidget(b)
    f.value_label = b
    return f


def qdate(d: dt.date | None) -> QDate:
    return QDate(d.year, d.month, d.day) if d else QDate.currentDate()


def pydate(w: QDateEdit) -> dt.date:
    q = w.date()
    return dt.date(q.year(), q.month(), q.day())


def date_edit(d=None):
    w = QDateEdit(qdate(d))
    w.setCalendarPopup(True)
    w.setDisplayFormat('yyyy-MM-dd')
    return w


def dec_of(le: QLineEdit, name: str, default='0') -> Decimal:
    txt = le.text().strip().replace(',', '') or default
    try:
        return Decimal(txt)
    except InvalidOperation:
        raise ValueError(f'"{name}" must be a number (for example 1250.50). You entered "{le.text()}".')


def combo(items, current=None):
    c = QComboBox()
    for it in items:
        if isinstance(it, tuple):
            c.addItem(it[1], it[0])
        else:
            c.addItem(it, it)
    if current is not None:
        i = c.findData(current)
        if i >= 0:
            c.setCurrentIndex(i)
    return c


class Worker(QThread):
    finished_with = Signal(object, object)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.finished_with.emit(self.fn(), None)
        except Exception as e:      # noqa: BLE001 – surfaced to the user by run_busy
            self.finished_with.emit(None, e)


def run_busy(parent, text, fn):
    """Run fn in a worker thread behind a modal progress dialog (UI stays responsive); re-raises worker exceptions."""
    dlg = QProgressDialog(text, None, 0, 0, parent)
    dlg.setWindowTitle('Please wait')
    dlg.setWindowModality(Qt.WindowModality.WindowModal)
    dlg.setMinimumDuration(0)
    dlg.show()
    box = {}
    loop = QEventLoop()
    w = Worker(fn)

    def fin(r, e):
        box['r'], box['e'] = r, e
        loop.quit()
    w.finished_with.connect(fin)
    w.start()
    loop.exec()
    w.wait()
    dlg.close()
    if box.get('e') is not None:
        raise box['e']
    return box.get('r')


def guarded(parent, fn, *a, **k):
    """Call fn; show friendly dialogs for expected errors. Returns (ok, result)."""
    try:
        return True, fn(*a, **k)
    except (EngineError, StoreError, TallyConfigError, ValueError) as e:
        QMessageBox.warning(parent, 'Please check', str(e))
    except Exception as e:    # noqa: BLE001
        QMessageBox.critical(parent, 'Unexpected error', f'{type(e).__name__}: {e}\n\n{traceback.format_exc(limit=3)}')
    return False, None


def confirm(parent, text, title_='Confirm') -> bool:
    return QMessageBox.question(parent, title_, text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes
