from __future__ import annotations

import os
import subprocess
import threading
import traceback

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QFileDialog, QFrame, QHBoxLayout,
                               QHeaderView, QLabel, QMessageBox, QProgressDialog, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ..paths import human_size, ts_to_iso

STYLE = """
QMainWindow, QWidget#Page, QDialog { background: #f5f6f8; }
QWidget { font-family: 'Segoe UI'; font-size: 10pt; color: #1f2937; }
QListWidget#Nav { background: #1e293b; color: #e2e8f0; border: none; font-size: 11pt; padding-top: 8px; }
QListWidget#Nav::item { padding: 10px 16px; }
QListWidget#Nav::item:selected { background: #2563eb; color: white; }
QListWidget#Nav::item:disabled { color: #64748b; }
QFrame#ContextBar { background: white; border-bottom: 1px solid #d6dae1; }
QLabel#CtxProject { font-size: 13pt; font-weight: 600; }
QLabel#CtxPath { color: #374151; font-family: Consolas; }
QFrame#ScanPanel { background: #eef4ff; border-bottom: 1px solid #c7d7f5; }
QFrame#Card { background: white; border: 1px solid #d6dae1; border-radius: 6px; }
QLabel#CardValue { font-size: 18pt; font-weight: 600; color: #111827; }
QLabel#CardTitle { color: #6b7280; }
QLabel#H1 { font-size: 14pt; font-weight: 600; }
QLabel#Hint { color: #6b7280; }
QLabel#Warn { background: #fff7e6; border: 1px solid #f5c26b; padding: 6px; border-radius: 4px; }
QLabel#Danger { background: #fdecec; border: 1px solid #e69a9a; padding: 6px; border-radius: 4px; }
QPushButton { background: white; border: 1px solid #b8c0cc; border-radius: 4px; padding: 5px 12px; }
QPushButton:hover { background: #eef2f7; }
QPushButton:disabled { color: #9ca3af; border-color: #d6dae1; }
QPushButton#Primary { background: #2563eb; color: white; border-color: #1d4ed8; }
QPushButton#Primary:hover { background: #1d4ed8; }
QPushButton#Primary:disabled { background: #93b4f5; }
QPushButton#DangerBtn { background: #b91c1c; color: white; border-color: #991b1b; }
QPushButton#DangerBtn:disabled { background: #e5a3a3; }
QTableWidget, QTableView, QTreeWidget { background: white; gridline-color: #e5e7eb; alternate-background-color: #f9fafb;
    selection-background-color: #dbeafe; selection-color: #111827; }
QHeaderView::section { background: #eef0f3; padding: 4px; border: none; border-right: 1px solid #d6dae1; font-weight: 600; }
QTabBar::tab { padding: 6px 14px; }
QTabBar::tab:selected { font-weight: 600; }
"""

KIND_COLORS = {"New": "#15803d", "Modified": "#b45309", "Deleted": "#b91c1c", "Moved": "#1d4ed8",
               "Possible move": "#7c3aed", "Unverified": "#6b7280"}
STATUS_COLORS = {"Completed": "#15803d", "Incomplete": "#b45309", "Cancelled": "#6b7280", "Failed": "#b91c1c",
                 "Running": "#1d4ed8", "Interrupted": "#6b7280"}


class Worker(QThread):
    """Runs fn(cancel_event, progress_callback) off the UI thread.
    Every signal carries the project id the task belongs to, so a window showing another project
    can ignore it."""
    progressed = Signal(str, object)
    done = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, project_id: str, fn, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.fn = fn
        self.cancel = threading.Event()

    def run(self):
        try:
            res = self.fn(self.cancel, lambda p: self.progressed.emit(self.project_id, p))
            self.done.emit(self.project_id, res)
        except Exception as e:  # noqa
            self.failed.emit(self.project_id, f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")


def run_with_progress(parent, project_id: str, title: str, fn, cancellable=True):
    """Run fn(cancel, progress) in a worker while a modal progress dialog is shown.
    progress(i, n, text). Returns (ok, result_or_error)."""
    dlg = QProgressDialog(title, "Cancel" if cancellable else None, 0, 0, parent)
    dlg.setWindowTitle(title)
    dlg.setWindowModality(Qt.WindowModal)
    dlg.setMinimumDuration(0)
    dlg.setMinimumWidth(520)
    state = {}

    def body(cancel, emit):
        return fn(cancel, lambda i, n, t="": emit((i, n, t)))

    w = Worker(project_id, body, parent)

    def on_prog(_pid, p):
        i, n, t = p
        dlg.setMaximum(max(n, 1))
        dlg.setValue(min(i, max(n, 1)))
        dlg.setLabelText(f"{title}\n{t[-90:]}")

    w.progressed.connect(on_prog)
    w.done.connect(lambda _pid, r: state.update(ok=True, res=r))
    w.failed.connect(lambda _pid, e: state.update(ok=False, res=e))
    w.finished.connect(dlg.reset)
    w.finished.connect(dlg.close)
    if cancellable:
        dlg.canceled.connect(w.cancel.set)
    w.start()
    dlg.exec()
    w.wait()
    return state.get("ok", False), state.get("res")


def table(headers: list[str], stretch_col: int | None = None, sortable=True, multi=False) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.ExtendedSelection if multi else QAbstractItemView.SingleSelection)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(24)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    if stretch_col is not None:
        t.horizontalHeader().setSectionResizeMode(stretch_col, QHeaderView.Stretch)
    t.setSortingEnabled(sortable)
    t.setWordWrap(False)
    return t


class NumItem(QTableWidgetItem):
    def __init__(self, value, text=None):
        super().__init__(text if text is not None else (f"{value:,}" if isinstance(value, int) else str(value)))
        self.value = value
        self.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def __lt__(self, other):
        if isinstance(other, NumItem):
            try:
                return (self.value or 0) < (other.value or 0)
            except TypeError:
                return str(self.value) < str(other.value)
        return super().__lt__(other)


def sel_row(t) -> int:
    """Selected row (works for mouse, keyboard and accessibility-tool selection), else current row."""
    rows = t.selectionModel().selectedRows() if t.selectionModel() else []
    if rows:
        return rows[0].row()
    idx = t.selectedIndexes() if hasattr(t, "selectedIndexes") else []
    return idx[0].row() if idx else t.currentRow()


def size_item(n):
    return NumItem(n or 0, human_size(n) if n is not None else "")


def date_item(ts):
    return NumItem(ts or 0, ts_to_iso(ts))


def fill(t: QTableWidget, rows: list[list], colors: dict[int, str] | None = None):
    t.setSortingEnabled(False)
    t.setRowCount(0)
    t.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            it = v if isinstance(v, QTableWidgetItem) else QTableWidgetItem("" if v is None else str(v))
            if colors and c in colors and isinstance(v, str):
                col = KIND_COLORS.get(v) or STATUS_COLORS.get(v)
                if col:
                    it.setForeground(QColor(col))
            t.setItem(r, c, it)
    t.setSortingEnabled(True)
    t.resizeColumnsToContents()
    for c in range(t.columnCount()):
        if t.columnWidth(c) > 520:
            t.setColumnWidth(c, 520)


def label(text: str, name: str | None = None, wrap=False) -> QLabel:
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    lb.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return lb


def card(title: str, value: str, acc: str) -> tuple[QFrame, QLabel]:
    f = QFrame()
    f.setObjectName("Card")
    v = QVBoxLayout(f)
    v.setContentsMargins(14, 10, 14, 10)
    t = QLabel(title)
    t.setObjectName("CardTitle")
    val = QLabel(value)
    val.setObjectName("CardValue")
    val.setAccessibleDescription(acc)
    val.setTextInteractionFlags(Qt.TextSelectableByMouse)
    v.addWidget(t)
    v.addWidget(val)
    return f, val


def hbox(*widgets, stretch_end=True, margins=(0, 0, 0, 0)) -> QHBoxLayout:
    h = QHBoxLayout()
    h.setContentsMargins(*margins)
    for w in widgets:
        if w is None:
            h.addStretch(1)
        elif isinstance(w, QWidget):
            h.addWidget(w)
        else:
            h.addLayout(w)
    if stretch_end:
        h.addStretch(1)
    return h


def info(parent, title, text):
    QMessageBox.information(parent, title, text)


def error(parent, title, text):
    QMessageBox.critical(parent, title, text)


def ask(parent, title, text, yes="Yes", no="Cancel") -> bool:
    mb = QMessageBox(QMessageBox.Question, title, text, parent=parent)
    y = mb.addButton(yes, QMessageBox.AcceptRole)
    mb.addButton(no, QMessageBox.RejectRole)
    mb.setDefaultButton(y)
    mb.exec()
    return mb.clickedButton() is y


def dialog_options():
    if os.environ.get("AICA_FSM_QT_DIALOGS") == "1":
        return QFileDialog.DontUseNativeDialog
    return QFileDialog.Options()


def save_path(parent, title: str, default_name: str) -> str | None:
    path, flt = QFileDialog.getSaveFileName(parent, title, os.path.join(os.path.expanduser("~"), "Documents", default_name),
                                            "Excel workbook (*.xlsx);;CSV (*.csv)", options=dialog_options())
    if not path:
        return None
    if not path.lower().endswith((".xlsx", ".csv")):
        path += ".csv" if "csv" in (flt or "").lower() else ".xlsx"
    return path


def pick_folder(parent, title: str, start: str = "") -> str | None:
    p = QFileDialog.getExistingDirectory(parent, title, start or os.path.expanduser("~"), options=dialog_options())
    return os.path.normpath(p) if p else None


def open_path(path: str):
    if os.path.exists(path):
        os.startfile(path)  # noqa
        return True
    return False


def open_containing(path: str):
    if os.path.exists(path):
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
        return True
    d = os.path.dirname(path)
    if os.path.isdir(d):
        os.startfile(d)  # noqa
        return True
    return False


class ResultsDialog(QDialog):
    def __init__(self, parent, title: str, summary: str, rows: list[list], headers: list[str]):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1000, 520)
        v = QVBoxLayout(self)
        v.addWidget(label(summary, "H1", wrap=True))
        t = table(headers, stretch_col=0)
        fill(t, rows)
        v.addWidget(t)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)
        v.addWidget(bb)
