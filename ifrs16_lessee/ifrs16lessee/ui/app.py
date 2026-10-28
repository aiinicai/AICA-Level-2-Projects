"""Main window and entry point."""
from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel, QListWidget, QMainWindow, QStackedWidget, QVBoxLayout, QWidget)

from ..store import Store
from .common import STYLE
from .pages import Dashboard, LeaseForm, Schedule
from .workspaces import EventWorkspace, JournalsPage, ReportsPage, TallyPage

NAV = ['Dashboard', 'Lease entry', 'Calculation schedule', 'Reassessment / modification', 'Termination', 'Journals', 'Reports', 'Tally connector']


def default_db_path():
    p = os.environ.get('IFRS16_DB')
    if p:
        return p
    d = os.path.join(os.path.expanduser('~'), '.ifrs16_lessee')
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'lessee.db')


class MainWindow(QMainWindow):
    def __init__(self, store: Store):
        super().__init__()
        self.store, self.ref = store, None
        self.setWindowTitle('IFRS 16 Lessee Accounting')
        self.resize(1380, 860)
        root = QWidget(); self.setCentralWidget(root)
        h = QHBoxLayout(root); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        side = QWidget(); side.setObjectName('Sidebar'); side.setFixedWidth(240)
        sl = QVBoxLayout(side); sl.setContentsMargins(0, 0, 0, 0)
        sl.addWidget(QLabel('IFRS 16 Lessee'))
        self.nav = QListWidget(); self.nav.addItems(NAV); sl.addWidget(self.nav, 1)
        note = QLabel('Local only – no data leaves this computer'); note.setStyleSheet('color:#cfe0fb;font-size:8.5pt;padding:10px;background:transparent;'); note.setWordWrap(True)
        sl.addWidget(note)
        h.addWidget(side)
        main = QWidget(); ml = QVBoxLayout(main)
        bar = QHBoxLayout(); bar.addWidget(QLabel('Current lease:'))
        self.sel = QComboBox(); self.sel.setMinimumWidth(260); self.sel.currentTextChanged.connect(self.on_select)
        bar.addWidget(self.sel); bar.addStretch(1)
        ml.addLayout(bar)
        self.stack = QStackedWidget(); ml.addWidget(self.stack, 1)
        h.addWidget(main, 1)
        self.pages = {
            'Dashboard': Dashboard(self), 'Lease entry': LeaseForm(self), 'Calculation schedule': Schedule(self),
            'Reassessment / modification': EventWorkspace(self, 'reassess'), 'Termination': EventWorkspace(self, 'termination'),
            'Journals': JournalsPage(self), 'Reports': ReportsPage(self), 'Tally connector': TallyPage(self),
        }
        for n in NAV:
            self.stack.addWidget(self.pages[n])
        self.nav.currentRowChanged.connect(self.on_nav)
        self.nav.setCurrentRow(0)
        self.setStyleSheet(STYLE)
        self.reload_leases()

    def on_nav(self, i):
        self.stack.setCurrentIndex(i)
        self.pages[NAV[i]].refresh()

    def goto(self, name):
        self.nav.setCurrentRow(NAV.index(name))

    def reload_leases(self):
        self.sel.blockSignals(True)
        self.sel.clear()
        refs = [l['ref'] for l in self.store.list_leases()]
        self.sel.addItems(refs)
        if self.ref in refs:
            self.sel.setCurrentText(self.ref)
        else:
            self.ref = refs[0] if refs else None
        self.sel.blockSignals(False)

    def on_select(self, text):
        self.ref = text or None
        self.pages[NAV[self.stack.currentIndex()]].refresh()

    def set_lease(self, ref):
        self.ref = ref
        self.reload_leases()

    def new_lease(self):
        self.pages['Lease entry'].clear()
        self.goto('Lease entry')

    def refresh_all(self):
        self.reload_leases()
        self.pages[NAV[self.stack.currentIndex()]].refresh()


def main(argv=None):
    app = QApplication(argv or sys.argv)
    store = Store(default_db_path())
    w = MainWindow(store)
    w.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
