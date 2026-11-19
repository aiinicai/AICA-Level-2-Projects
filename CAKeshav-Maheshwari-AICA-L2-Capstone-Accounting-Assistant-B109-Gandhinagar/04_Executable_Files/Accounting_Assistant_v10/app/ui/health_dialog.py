"""Check this company: read-only comparison of the app with live Tally."""
from __future__ import annotations

import datetime as dt

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
                             QTableWidgetItem, QVBoxLayout)
from sqlalchemy import func, select

from . import theme
from .common import run_bg

ICON = {"ok": "✓", "warn": "!", "err": "✗", "info": "i"}
TYPES = ("Payment", "Receipt", "Contra", "Journal", "Purchase", "Sales", "Debit Note", "Credit Note")


class HealthDialog(QDialog):
    def __init__(self, st, parent=None):
        super().__init__(parent)
        self.st = st
        c = st.company()
        self.setWindowTitle(f"Check company - {c.name if c else ''}")
        self.resize(900, 560)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Compares the app with live Tally: day book, Trial Balance, P&L, Balance Sheet, "
                             "Schedule III, bank balances and voucher numbering. Nothing is written to Tally.",
                             wordWrap=True, objectName="muted"))
        self.capture = QCheckBox("Also save Tally's replies (to turn any problem into a test)")
        self.capture.setChecked(True)
        lay.addWidget(self.capture)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["", "Check", "Details"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 34)
        self.table.setColumnWidth(1, 330)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self.table, 1)
        self.status = QLabel("", objectName="muted")
        lay.addWidget(self.status)
        row = QHBoxLayout()
        self.b_run = QPushButton("Run check", objectName="primary")
        self.b_run.clicked.connect(self.run)
        self.b_folder = QPushButton("Open saved replies")
        self.b_folder.setEnabled(False)
        self.b_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self._dir)))
        b_close = QPushButton("Close")
        b_close.clicked.connect(self.accept)
        row.addWidget(self.b_run)
        row.addWidget(self.b_folder)
        row.addStretch(1)
        row.addWidget(b_close)
        lay.addLayout(row)
        self._dir = ""

    def run(self):
        from ..config import app_dir
        from ..db.models import MasterCache
        from ..engine import healthcheck, masters as masters_mod
        from ..engine.periods import fy_start
        c = self.st.company()
        if not c:
            return
        self.b_run.setEnabled(False)
        self.table.setRowCount(0)
        today = dt.date.today()
        fy_from, to = fy_start(today).strftime("%Y%m%d"), today.strftime("%Y%m%d")
        m = masters_mod.load(self.st.session, c.id)
        mapping = dict((c.settings or {}).get("sch3_map", {}))
        banks = healthcheck.bank_dates(self.st.session, c.id)
        vtypes = [t for t in TYPES if t in m.voucher_types]
        cap = None
        if self.capture.isChecked():
            safe = "".join(ch for ch in c.name if ch.isalnum())[:30]
            cap = app_dir() / "diagnostics" / f"capture_{safe}_{dt.datetime.now():%Y%m%d_%H%M}"
            self._dir = str(cap)
        client, cname, ledgers = self.st.client(c), c.name, dict(m.ledgers)

        def job(progress):
            return healthcheck.collect(client, cname, fy_from, to, mapping, ledgers, banks, vtypes, cap, progress)

        def done(remote):
            ids, n = healthcheck.local_state(self.st.session, c.id, fy_from, to)
            last = self.st.session.scalar(select(func.max(MasterCache.synced_at)).where(MasterCache.company_id == c.id))
            methods = {t: (m.voucher_types.get(t) or {}).get("NUMBERINGMETHOD", "") for t in vtypes}
            checks = healthcheck.evaluate(self.st.session, c, remote, ids, n, methods,
                                          last.strftime("%d-%m-%Y %H:%M") if last else "")
            self.show_checks(checks)
            self.b_run.setEnabled(True)
            self.b_folder.setEnabled(bool(self._dir))
            bad = sum(1 for k in checks if k.status == "err")
            warn = sum(1 for k in checks if k.status == "warn")
            c.settings = {**(c.settings or {}), "last_check": {
                "at": dt.datetime.now().strftime("%d-%m-%Y %H:%M"), "err": bad, "warn": warn,
                "items": [[k.status, k.title] for k in checks if k.status in ("err", "warn")]}}
            self.st.session.commit()
            self.status.setText("All checks passed." if not bad and not warn else
                                f"{bad} problem(s), {warn} warning(s).")

        def fail(msg):
            self.status.setText(f"Check stopped: {msg}")
            self.b_run.setEnabled(True)
        run_bg(self, job, done, fail, self.status.setText)

    def show_checks(self, checks):
        col = {"ok": theme.OK_FG, "warn": theme.WARN_FG, "err": theme.ERR_FG, "info": theme.INFO_FG}
        self.table.setRowCount(len(checks))
        for i, k in enumerate(checks):
            ic = QTableWidgetItem(ICON[k.status])
            ic.setForeground(QColor(col.get(k.status, theme.INFO_FG)))
            ic.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            f = ic.font()
            f.setBold(True)
            ic.setFont(f)
            self.table.setItem(i, 0, ic)
            self.table.setItem(i, 1, QTableWidgetItem(k.title))
            self.table.setItem(i, 2, QTableWidgetItem(k.detail))
        self.table.resizeRowsToContents()
