"""Office: every company on one screen - what is waiting, what is due, what needs attention."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QCheckBox, QFileDialog, QHBoxLayout, QHeaderView, QPushButton, QTableWidget,
                             QTableWidgetItem, QWidget)

from . import theme
from .common import page_layout

COLS = ["Company", "Invoices", "Bank lines", "Last sync", "Check company", "TDS", "GSTR-1", "GSTR-3B", "Close",
        "Needs attention"]
# column -> page opened on click
GOTO = {0: "Home", 1: "Workbench", 2: "Bank", 5: "Compliance", 6: "Compliance", 7: "Compliance", 8: "Close"}


class OfficePage(QWidget):
    def __init__(self, st):
        super().__init__()
        self.st = st
        root = page_layout(self, "Office", "All companies on one screen. Click a figure to open that company on "
                                           "that page. Due dates are for the month just ended; ticks in the Close "
                                           "checklist mark them done.")
        top = QHBoxLayout()
        self.only = QCheckBox("Only companies that need attention")
        self.only.toggled.connect(self.load)
        b_ref = QPushButton("Refresh")
        b_ref.clicked.connect(self.load)
        b_xl = QPushButton("Export to Excel")
        b_xl.clicked.connect(self.export)
        top.addWidget(self.only)
        top.addStretch(1)
        top.addWidget(b_ref)
        top.addWidget(b_xl)
        root.addLayout(top)
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)
        for i, w in ((0, 240), (1, 66), (2, 74), (3, 92), (4, 112), (5, 112), (6, 112), (7, 112), (8, 52)):
            self.table.setColumnWidth(i, w)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.cellClicked.connect(self.open)
        root.addWidget(self.table, 1)
        self.rows = []

    def showEvent(self, e):
        self.load()
        super().showEvent(e)

    def load(self):
        from ..engine import office
        self.rows = office.build(self.st.session)
        rows = [r for r in self.rows if r.attention or r.urgent] if self.only.isChecked() else self.rows
        self._shown = rows
        col = {"ok": theme.OK_FG, "warn": theme.WARN_FG, "err": theme.ERR_FG, "info": theme.MUTED}
        t = self.table
        t.setUpdatesEnabled(False)
        t.setRowCount(len(rows))
        for i, r in enumerate(rows):
            sync = r.last_sync.strftime("%d-%m %H:%M") if r.last_sync else "never"
            chk = (f"{r.check.get('err', 0)} ✗ · {r.check.get('warn', 0)} ! · {r.check.get('at', '')[:10]}"
                   if r.check else "not run")
            chk = (f"{r.check.get('err', 0)} ✗  {r.check.get('warn', 0)} !  {r.check.get('at', '')[:5]}"
                   if r.check else "not run")
            vals = [r.name, str(r.invoices or "–"), str(r.bank_total or "–"), sync, chk] + [d.short for d in r.dues] + \
                [f"{r.close_done}/{r.close_total}", "; ".join(r.attention) or ("✓ nothing else pending" if r.urgent else "✓ nothing pending")]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c in (1, 2, 8):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if c in (5, 6, 7):
                    it.setForeground(QColor(col[r.dues[c - 5].state]))
                    it.setToolTip(r.dues[c - 5].text + f" - for {r.month[4:6]}-{r.month[:4]}")
                if c == 4 and r.check.get("err"):
                    it.setForeground(QColor(theme.ERR_FG))
                if c == 8 and r.lock_until:
                    it.setToolTip(f"Books locked up to {r.lock_until[6:8]}-{r.lock_until[4:6]}-{r.lock_until[:4]}")
                if c == 9:
                    it.setForeground(QColor(theme.WARN_FG if r.attention else theme.OK_FG))
                    it.setToolTip("\n".join([d.text for d in r.dues if d.state in ("err", "warn")] + r.attention))
                if c == 2 and r.bank:
                    it.setToolTip("\n".join(f"{b}: {n}" for b, n in r.bank.items()))
                if c == 0:
                    it.setToolTip(r.name)
                    f = it.font()
                    f.setBold(True)
                    it.setFont(f)
                t.setItem(i, c, it)
        t.resizeRowsToContents()
        t.setUpdatesEnabled(True)

    def open(self, row: int, col: int):
        r = self._shown[row]
        self.st.set_company(r.company_id)
        w = self.st.window
        if col == 4:
            w.open_health()
        elif col in GOTO:
            w.go_page(GOTO[col])

    def export(self):
        from ..engine import office
        path, _ = QFileDialog.getSaveFileName(self, "Export", "Office dashboard.xlsx", "Excel (*.xlsx)")
        if path:
            office.to_excel(self.rows, path)
