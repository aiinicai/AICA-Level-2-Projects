"""Inbox: pick company + folder, read new invoices, see them by status."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
                             QMessageBox, QProgressBar, QPushButton, QTableWidget, QTableWidgetItem, QWidget)
from sqlalchemy import select

from ..db.models import Company, Invoice as InvoiceRow
from ..engine import intake
from .common import card, page_layout, run_bg

STATUS_COLOURS = {"green": "#1d7a45", "amber": "#9a6400", "red": "#b42323"}


class CompanyPicker(QComboBox):
    """Company selector shared across pages (keeps AppState.company_id in sync)."""

    def __init__(self, st):
        super().__init__()
        self.st = st
        self.setMinimumWidth(320)
        self.reload()
        self.currentIndexChanged.connect(self._picked)
        st.on_company_change(self._external)

    def reload(self):
        self.blockSignals(True)
        self.clear()
        for c in self.st.companies():
            self.addItem(c.name, c.id)
        idx = self.findData(self.st.company_id)
        if idx < 0 and self.count():
            idx = 0
            self.st.company_id = self.itemData(0)
        self.setCurrentIndex(idx)
        self.blockSignals(False)

    def _picked(self, i):
        if i >= 0:
            self.st.set_company(self.itemData(i))

    def _external(self):
        idx = self.findData(self.st.company_id)
        if idx >= 0 and idx != self.currentIndex():
            self.blockSignals(True)
            self.setCurrentIndex(idx)
            self.blockSignals(False)


class InboxPage(QWidget):
    open_invoice = pyqtSignal(str)

    def __init__(self, st):
        super().__init__(objectName="page")
        self.st = st
        root = page_layout(self, "Inbox", "New invoices in the company's folder are read and queued for review. "
                                          "Double-click a row to review it.")
        top, tl = card()
        row = QHBoxLayout()
        self.picker = CompanyPicker(st)
        self.folder_lbl = QLabel("", objectName="muted")
        btn_folder = QPushButton("Choose folder…")
        btn_folder.clicked.connect(self.choose_folder)
        self.btn_scan = QPushButton("Read new invoices", objectName="primary")
        self.btn_scan.clicked.connect(self.scan)
        row.addWidget(QLabel("Company"))
        row.addWidget(self.picker)
        row.addWidget(btn_folder)
        row.addWidget(self.folder_lbl, 1)
        row.addWidget(self.btn_scan)
        tl.addLayout(row)
        prow = QHBoxLayout()
        self.progress = QProgressBar(visible=False)
        self.progress_lbl = QLabel("", objectName="muted")
        prow.addWidget(self.progress_lbl, 1)
        prow.addWidget(self.progress, 1)
        tl.addLayout(prow)
        root.addWidget(top)

        lst, ll = card()
        frow = QHBoxLayout()
        self.filter = QComboBox()
        self.filter.addItems(["To review", "Posted", "Exceptions", "All"])
        self.filter.currentIndexChanged.connect(self.refresh)
        self.counts = QLabel("", objectName="muted")
        frow.addWidget(QLabel("Show"))
        frow.addWidget(self.filter)
        self.btn_reread = QPushButton("Re-read selected")
        self.btn_reread.setToolTip("Run extraction again (after an app update, or after adding a Gemini key)")
        self.btn_reread.clicked.connect(self.reread)
        frow.addWidget(self.btn_reread)
        frow.addStretch(1)
        frow.addWidget(self.counts)
        ll.addLayout(frow)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(["", "File", "Supplier", "Invoice no", "Date", "Total", "Read by",
                                              "2B", "Status"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(lambda r, _c: self.open_invoice.emit(self.table.item(r, 1).data(
            Qt.ItemDataRole.UserRole)))
        ll.addWidget(self.table)
        root.addWidget(lst, 1)
        st.on_company_change(self.refresh)
        self.refresh()

    def showEvent(self, e):
        self.picker.reload()
        self.refresh()
        super().showEvent(e)

    def _folder(self, c: Company) -> str:
        return (c.settings or {}).get("folder", "")

    def choose_folder(self):
        c = self.st.company()
        if not c:
            QMessageBox.information(self, "Inbox", "Sync a company from Tally first (Companies page).")
            return
        d = QFileDialog.getExistingDirectory(self, "Invoice folder for " + c.name, self._folder(c))
        if d:
            c.settings = {**(c.settings or {}), "folder": d}
            self.st.session.commit()
            self.refresh()

    def scan(self):
        c = self.st.company()
        if not c or not self._folder(c) or not Path(self._folder(c)).is_dir():
            QMessageBox.information(self, "Inbox", "Choose the invoice folder for this company first.")
            return
        cid, folder, opt = c.id, Path(self._folder(c)), self.st.extract_options(c)
        self.btn_scan.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(0)

        def job(progress):
            s = self.st.Local()
            comp = s.get(Company, cid)
            files = intake.new_files(s, comp, folder)
            progress(f"{len(files)} new file(s)")
            for i, (p, h) in enumerate(files, 1):
                progress(f"Reading {i}/{len(files)}: {p.name}")
                intake.ingest(s, comp, p, h, opt)
            s.close()
            return len(files)

        run_bg(self, job, self._scanned, self._failed, self.progress_lbl.setText)

    def reread(self):
        c = self.st.company()
        ids = [self.table.item(r, 1).data(Qt.ItemDataRole.UserRole)
               for r in sorted({i.row() for i in self.table.selectedIndexes()})]
        if not c or not ids:
            QMessageBox.information(self, "Re-read", "Select one or more invoices first (Ctrl+A for all).")
            return
        opt = self.st.extract_options(c)
        self.btn_reread.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(0)

        def job(progress):
            s = self.st.Local()
            n = 0
            for k, rid in enumerate(ids, 1):
                row = s.get(InvoiceRow, rid)
                if row and row.status != "posted":
                    progress(f"Re-reading {k}/{len(ids)}: {Path(row.file_path).name}")
                    try:
                        intake.reread(s, row, opt)
                        n += 1
                    except Exception as e:
                        progress(f"{Path(row.file_path).name}: {e}")
            s.close()
            return n

        def done(n):
            self.btn_reread.setEnabled(True)
            self._scanned(n)
            self.progress_lbl.setText(f"{n} invoice(s) re-read")

        def fail(msg):
            self.btn_reread.setEnabled(True)
            self._failed(msg)

        run_bg(self, job, done, fail, self.progress_lbl.setText)

    def _scanned(self, n):
        self.btn_scan.setEnabled(True)
        self.progress.setVisible(False)
        self.progress_lbl.setText(f"{n} new invoice(s) read" if n else "No new files")
        self.st.session.expire_all()
        self.refresh()

    def _failed(self, msg):
        self.btn_scan.setEnabled(True)
        self.progress.setVisible(False)
        QMessageBox.warning(self, "Inbox", msg)

    def rows(self, which: str | None = None) -> list[InvoiceRow]:
        c = self.st.company()
        if not c:
            return []
        q = select(InvoiceRow).where(InvoiceRow.company_id == c.id)
        which = which or self.filter.currentText()
        if which == "To review":
            q = q.where(InvoiceRow.status.in_(["review", "approved"]))
        elif which == "Posted":
            q = q.where(InvoiceRow.status == "posted")
        elif which == "Exceptions":
            q = q.where(InvoiceRow.status == "exception")
        return list(self.st.session.scalars(q.order_by(InvoiceRow.updated_at.desc())))

    def refresh(self):
        c = self.st.company()
        self.folder_lbl.setText(self._folder(c) if c and self._folder(c) else "No folder chosen")
        rows = self.rows()
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            e, v = row.extraction or {}, row.validation or {}
            status = v.get("status", "red")
            d = e.get("invoice_date", "")
            cells = ["●", Path(row.file_path).name, e.get("supplier_name", ""), e.get("invoice_no", ""),
                     f"{d[6:8]}-{d[4:6]}-{d[:4]}" if len(d) == 8 else d,
                     f"{float(e.get('grand_total', 0) or 0):,.2f}", row.extraction_source or "",
                     row.status_2b.replace("_", " "), row.status]
            for col, val in enumerate(cells):
                it = QTableWidgetItem(val)
                if col == 0:
                    it.setForeground(QColor(STATUS_COLOURS.get(status, "#888")))
                    it.setToolTip(f"{status}, confidence {v.get('confidence', 0):.2f}")
                if col == 1:
                    it.setData(Qt.ItemDataRole.UserRole, row.id)
                if col == 5:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(r, col, it)
        if c:
            all_rows = self.rows("All")
            n = lambda s: sum(1 for x in all_rows if x.status == s)
            self.counts.setText(f"To review {n('review') + n('approved')}  ·  Posted {n('posted')}  ·  "
                                f"Exceptions {n('exception')}")

    def queue_ids(self) -> list[str]:
        return [r.id for r in self.rows("To review")]
