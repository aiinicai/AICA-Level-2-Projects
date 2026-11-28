"""Small UI helpers shared by pages."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QHeaderView, QLabel, QMessageBox, QTableWidget,
                               QTableWidgetItem, QWidget)


def make_table(headers: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.setAlternatingRowColors(True)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    t.horizontalHeader().setStretchLastSection(True)
    t.setSortingEnabled(True)
    return t


def fill_table(t: QTableWidget, rows: list[list], ids: list[int] | None = None, sortable: bool = True) -> None:
    t.setSortingEnabled(False)
    t.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            item = QTableWidgetItem("" if value is None else str(value))
            if ids is not None and c == 0:
                item.setData(Qt.UserRole, ids[r])
            t.setItem(r, c, item)
    t.resizeColumnsToContents()
    t.setSortingEnabled(sortable)


def selected_id(t: QTableWidget) -> int | None:
    row = t.currentRow()
    if row < 0:
        return None
    item = t.item(row, 0)
    return item.data(Qt.UserRole) if item else None


def title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("PageTitle")
    return lbl


def muted(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Muted")
    lbl.setWordWrap(True)
    return lbl


def error(parent: QWidget, message: str) -> None:
    QMessageBox.warning(parent, "IPT", message)


def info(parent: QWidget, message: str) -> None:
    QMessageBox.information(parent, "IPT", message)


def confirm(parent: QWidget, message: str) -> bool:
    return QMessageBox.question(parent, "Please confirm", message,
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes


# ---------------------------------------------------------------- tick boxes
def make_checkable(t: QTableWidget) -> None:
    """Turn column 0 (filled with '' by the caller, holding the row id) into a tick box per row."""
    t.setSortingEnabled(False)
    for r in range(t.rowCount()):
        it = t.item(r, 0)
        if it is None:
            continue
        it.setFlags((it.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsEditable)
        it.setCheckState(Qt.Unchecked)
    t.setColumnWidth(0, 34)
    t.setSortingEnabled(True)


def checked_ids(t: QTableWidget) -> list[int]:
    out = []
    for r in range(t.rowCount()):
        it = t.item(r, 0)
        if it is not None and it.checkState() == Qt.Checked:
            out.append(it.data(Qt.UserRole))
    return out


def set_all_checked(t: QTableWidget, checked: bool, where=None) -> int:
    """Tick (or untick) every row - or only rows where where(row) is true. Returns how many are ticked."""
    n = 0
    for r in range(t.rowCount()):
        it = t.item(r, 0)
        if it is None:
            continue
        on = checked and (where is None or where(r))
        it.setCheckState(Qt.Checked if on else Qt.Unchecked)
        n += on
    return n



def install_wheel_guard(app) -> object:
    """Drop-downs and number boxes change with the mouse wheel only after they were clicked. Otherwise the wheel
    scrolls the page: scrolling over a form used to change 'Document type' or 'Place of supply' silently."""
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtWidgets import QAbstractSpinBox, QApplication, QComboBox

    class _Guard(QObject):
        def eventFilter(self, obj, ev):
            if ev.type() == QEvent.Wheel and isinstance(obj, (QComboBox, QAbstractSpinBox)) and not obj.hasFocus():
                parent = obj.parentWidget()
                if parent is not None:
                    QApplication.sendEvent(parent, ev)     # let the page scroll instead
                return True
            return False

    guard = _Guard(app)
    app.installEventFilter(guard)
    return guard
