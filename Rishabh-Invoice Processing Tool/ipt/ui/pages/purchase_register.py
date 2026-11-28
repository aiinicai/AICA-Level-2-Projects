"""Purchase Register: fetch purchase vouchers from Tally, or import a register Excel with a mapping wizard."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QSplitter,
                               QVBoxLayout, QWidget)

from ipt.core.money import format_inr
from ipt.core.permissions import PermissionDenied, has_permission
from ipt.core.timefmt import fmt
from ipt.services.recon.purchase_register import (AMOUNT_FIELDS, PR_FIELDS, PurchaseRegisterError, guess_header_row,
                                                  guess_mapping, read_rows)
from ipt.ui import worker
from ipt.ui.helpers import error, fill_table, info, make_table, muted, selected_id, title
from ipt.ui.pages.base import BasePage


def _col_name(i: int) -> str:
    s, n = "", i + 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


class PrImportDialog(QDialog):
    """File -> sheet + header row (preview) -> column mapping (can be saved as a template)."""

    def __init__(self, services, path: Path, parent=None):
        super().__init__(parent)
        self.s, self.path = services, path
        self.setWindowTitle(f"Import purchase register – {path.name}")
        self.resize(1100, 700)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.sheet = QComboBox()
        self.header = QSpinBox()
        self.header.setRange(1, 200)
        self.template = QComboBox()
        self.template.addItem("(no template)", None)
        for t in self.s.purchases.templates():
            self.template.addItem(t.name, t)
        top.addWidget(QLabel("Sheet"))
        top.addWidget(self.sheet)
        top.addWidget(QLabel("Header row"))
        top.addWidget(self.header)
        top.addWidget(QLabel("Use saved mapping"))
        top.addWidget(self.template)
        top.addStretch(1)
        lay.addLayout(top)
        split = QSplitter(Qt.Vertical)
        self.preview = make_table([])
        self.preview.setSortingEnabled(False)
        split.addWidget(self.preview)
        mapw = QWidget()
        grid = QGridLayout(mapw)
        grid.addWidget(QLabel("<b>IPT field</b>"), 0, 0)
        grid.addWidget(QLabel("<b>Column</b>"), 0, 1)
        grid.addWidget(QLabel("<b>+ add column</b> (amounts split over several columns)"), 0, 2)
        self.combos: dict[str, list[QComboBox]] = {}
        for r, (fld, label) in enumerate(PR_FIELDS.items(), 1):
            grid.addWidget(QLabel(label), r, 0)
            boxes = [QComboBox()]
            if fld in AMOUNT_FIELDS:
                boxes.append(QComboBox())
            for c, b in enumerate(boxes, 1):
                grid.addWidget(b, r, c)
            self.combos[fld] = boxes
        split.addWidget(mapw)
        lay.addWidget(split, 1)
        bottom = QHBoxLayout()
        self.save_as = QLineEdit()
        self.save_as.setPlaceholderText("Save this mapping as (optional), e.g. 'Tally purchase register'")
        bottom.addWidget(self.save_as, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Import")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        bottom.addWidget(buttons)
        lay.addLayout(bottom)
        names, rows = read_rows(path, limit=40)
        self.sheet.addItems(names)
        self.sheet.currentTextChanged.connect(lambda _: self._load(True))
        self.header.valueChanged.connect(lambda _: self._columns(False))
        self.template.currentIndexChanged.connect(self._apply_template)
        self.rows: list[list] = []
        self._load(True)

    def _load(self, guess: bool) -> None:
        try:
            _, self.rows = read_rows(self.path, self.sheet.currentText(), limit=40)
        except PurchaseRegisterError as e:
            error(self, str(e))
            return
        width = max((len(r) for r in self.rows), default=0)
        self.preview.setColumnCount(width)
        self.preview.setHorizontalHeaderLabels([_col_name(i) for i in range(width)])
        fill_table(self.preview, [[("" if v is None else v) for v in r] for r in self.rows[:25]])
        self.preview.setVerticalHeaderLabels([str(i) for i in range(1, len(self.rows) + 1)])
        self.preview.verticalHeader().setVisible(True)
        if guess:
            self.header.blockSignals(True)
            self.header.setValue(guess_header_row(self.rows))
            self.header.blockSignals(False)
        self._columns(guess)

    def _headers(self) -> list[str]:
        h = self.header.value()
        return [str(v or "") for v in self.rows[h - 1]] if 0 < h <= len(self.rows) else []

    def _columns(self, guess: bool) -> None:
        heads = self._headers()
        for boxes in self.combos.values():
            for b in boxes:
                cur = b.currentData()
                b.blockSignals(True)
                b.clear()
                b.addItem("—", None)
                for i, hname in enumerate(heads):
                    b.addItem(f"{_col_name(i)}: {hname}"[:60], i)
                if cur is not None:
                    b.setCurrentIndex(max(0, b.findData(cur)))
                b.blockSignals(False)
        if guess:
            self._set_mapping(guess_mapping(heads))

    def _set_mapping(self, mapping: dict[str, list[int]]) -> None:
        for fld, boxes in self.combos.items():
            cols = mapping.get(fld, [])
            for k, b in enumerate(boxes):
                b.setCurrentIndex(max(0, b.findData(cols[k])) if k < len(cols) else 0)

    def _apply_template(self) -> None:
        t = self.template.currentData()
        if t is None:
            return
        if t.sheet and self.sheet.findText(t.sheet) >= 0:
            self.sheet.setCurrentText(t.sheet)
        self.header.setValue(t.header_row)
        self._columns(False)
        self._set_mapping({k: v for k, v in json.loads(t.mapping_json).items()})
        self.save_as.setText(t.name)

    def mapping(self) -> dict[str, list[int]]:
        out = {}
        for fld, boxes in self.combos.items():
            cols = [b.currentData() for b in boxes if b.currentData() is not None]
            if cols:
                out[fld] = list(dict.fromkeys(cols))
        return out

    def _accept(self) -> None:
        try:
            self.result_upload = self.s.purchases.import_excel(self.path, self.sheet.currentText(), self.header.value(),
                                                               self.mapping(), self.save_as.text().strip())
        except (PurchaseRegisterError, PermissionDenied, ValueError) as e:
            error(self, str(e))
            return
        self.accept()


class FetchDialog(QDialog):
    def __init__(self, fy, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fetch purchase register from Tally")
        f = QFormLayout(self)
        self.start, self.end = QDateEdit(), QDateEdit()
        for d, v in ((self.start, fy.start_date), (self.end, fy.end_date)):
            d.setCalendarPopup(True)
            d.setDisplayFormat("dd-MM-yyyy")
            d.setDate(QDate(v.year, v.month, v.day))
        f.addRow(muted("Reads every voucher with an input GST ledger (Purchase, Journal, Payment, Debit Note...) from "
                       "the open Tally company; vouchers without GST are left out. Reverse-charge (RCM) entries are "
                       "marked and kept out of the reconciliation. Nothing is written to Tally."))
        f.addRow("From", self.start)
        f.addRow("To", self.end)
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        b.button(QDialogButtonBox.Ok).setText("Fetch")
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        f.addRow(b)


class PurchaseRegisterPage(BasePage):
    title_text = "Purchase Register"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("Purchase Register"))
        self.layout_.addWidget(muted("The books side of the reconciliation. Fetch it straight from Tally (recommended) "
                                     "or import the purchase register exported to Excel. A new register replaces the "
                                     "current one for the same period; older ones are kept as history."))
        bar = QHBoxLayout()
        self.btn_tally = QPushButton("Fetch from Tally…")
        self.btn_tally.setObjectName("Primary")
        self.btn_excel = QPushButton("Import Excel…")
        self.btn_rejects = QPushButton("Export rejected rows")
        self.history = QCheckBox("Show history")
        for w in (self.btn_tally, self.btn_excel, self.btn_rejects, self.history):
            bar.addWidget(w)
        bar.addStretch(1)
        self.progress = muted("")
        bar.addWidget(self.progress)
        self.layout_.addLayout(bar)
        split = QSplitter(Qt.Vertical)
        self.uploads = make_table(["Source", "File / company", "From", "To", "Rows", "Rejected", "Current", "By", "At"])
        split.addWidget(self.uploads)
        self.records = make_table(["Date", "Voucher", "Type", "Party", "GSTIN", "Supplier inv no", "Inv date",
                                   "Taxable", "IGST", "CGST", "SGST", "Cess", "Total", "Purchase ledger"])
        split.addWidget(self.records)
        split.setSizes([180, 500])
        self.layout_.addWidget(split, 1)
        self.summary = muted("")
        self.layout_.addWidget(self.summary)
        self.btn_tally.clicked.connect(self._fetch)
        self.btn_excel.clicked.connect(self._excel)
        self.btn_rejects.clicked.connect(self._export_rejects)
        self.history.toggled.connect(self.refresh)
        self.uploads.itemSelectionChanged.connect(self._load_records)

    def refresh(self) -> None:
        role = self.s.ctx.user.role if self.s.ctx.user else None
        busy = getattr(self, "_fetching", False)
        for b in (self.btn_tally, self.btn_excel):
            b.setEnabled(has_permission(role, "gst.upload") and not busy)   # never two loads at once
        ups = self.s.purchases.uploads(self.history.isChecked())
        rows = [["Tally" if u.source == "tally" else "Excel", u.file_name,
                 u.period_from.strftime("%d-%m-%Y") if u.period_from else "",
                 u.period_to.strftime("%d-%m-%Y") if u.period_to else "", u.rows_ok, u.rows_rejected,
                 "Yes" if u.is_current else "Replaced", u.uploaded_by, fmt(u.uploaded_at)] for u in ups]
        fill_table(self.uploads, rows, [u.id for u in ups])
        self._load_records()

    def _select_upload(self, upload_id: int) -> None:
        for r in range(self.uploads.rowCount()):
            it = self.uploads.item(r, 0)
            if it is not None and it.data(Qt.UserRole) == upload_id:
                self.uploads.setCurrentCell(r, 0)
                self.uploads.selectRow(r)
                self._load_records()
                return

    def _load_records(self) -> None:
        sel = selected_id(self.uploads)
        recs = self.s.purchases.records(sel)
        d = lambda x: x.strftime("%d-%m-%Y") if x else ""  # noqa: E731
        fill_table(self.records, [[d(r.voucher_date), r.voucher_no, r.voucher_type, r.party_name, r.supplier_gstin,
                                   r.supplier_invoice_no, d(r.supplier_invoice_date), format_inr(r.taxable_value),
                                   format_inr(r.igst), format_inr(r.cgst), format_inr(r.sgst), format_inr(r.cess),
                                   format_inr(r.invoice_total), r.purchase_ledger] for r in recs],
                   [r.id for r in recs])
        tx = sum((r.taxable_value or 0) for r in recs)
        tax = sum((r.igst or 0) + (r.cgst or 0) + (r.sgst or 0) + (r.cess or 0) for r in recs)
        scope = "selected load" if sel else "all current periods together"
        self.summary.setText(f"{len(recs)} voucher(s) · taxable {format_inr(tx)} · tax {format_inr(tax)}  ({scope})")

    def _fetch(self) -> None:
        fy = next((f for f in self.s.companies.list_fys(self.s.ctx.company_id) if f.id == self.s.ctx.fy_id), None)
        if fy is None:
            return
        dlg = FetchDialog(fy, self)
        if dlg.exec() != QDialog.Accepted:
            return
        a, b = dlg.start.date().toPython(), dlg.end.date().toPython()
        if a > b:
            error(self, f"'From' ({a:%d-%m-%Y}) is after 'To' ({b:%d-%m-%Y}). Choose the dates again.")
            return
        self._fetching = True
        self.btn_tally.setEnabled(False)
        self.btn_excel.setEnabled(False)
        self.progress.setText("Connecting to Tally…")

        def done(up):
            self._fetching = False
            self.btn_tally.setEnabled(True)
            self.progress.setText("")
            self.refresh()
            self._select_upload(up.id)          # show this fetch only, not every current period together
            info(self, f"{up.rows_ok} voucher(s) with input GST read from Tally for {a:%d-%m-%Y} to {b:%d-%m-%Y}."
                       "\n\nThe table shows this fetch. Other periods fetched earlier stay in use for the "
                       "reconciliation; clear the selection above to see all of them together.")

        def failed(msg):
            self._fetching = False
            self.refresh()
            self.progress.setText("")
            error(self, msg)

        self._job = worker.start(worker.Job(self.s.purchases.fetch_from_tally, a, b, with_progress=True), done, failed,
                                 self.progress.setText)

    def _excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Purchase register file", "", "Excel / CSV (*.xlsx *.xlsm *.csv)")
        if not path:
            return
        try:
            dlg = PrImportDialog(self.s, Path(path), self)
        except PurchaseRegisterError as e:
            error(self, str(e))
            return
        if dlg.exec() != QDialog.Accepted:
            return
        up = dlg.result_upload
        self.refresh()
        msg = f"{up.rows_ok} row(s) imported."
        if up.rows_rejected:
            msg += f" {up.rows_rejected} row(s) rejected – select the import and click 'Export rejected rows'."
        info(self, msg)

    def _export_rejects(self) -> None:
        uid = selected_id(self.uploads)
        if uid is None:
            error(self, "Select an import first")
            return
        if not self.s.purchases.rejects(uid):
            info(self, "This import has no rejected rows.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save rejected rows", "rejected_rows.xlsx", "Excel (*.xlsx)")
        if path:
            self.s.purchases.export_rejects(uid, Path(path))
            info(self, f"Saved {path}")
