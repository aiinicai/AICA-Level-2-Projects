"""MIS Reports and Export Centre."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QLineEdit, QPushButton

from ipt.core.money import format_inr
from ipt.core.permissions import PermissionDenied, has_permission
from ipt.services.export_service import WORKBOOK_SHEETS
from ipt.services.reports_service import REPORTS
from ipt.ui import worker
from ipt.ui.helpers import error, fill_table, info, make_table, muted, title
from ipt.ui.pages.base import BasePage
from ipt.ui.pages.recon import fy_months


def _fmt(v, money: bool):
    if v is None:
        return ""
    if isinstance(v, Decimal):
        return format_inr(v) if money else f"{v.normalize():f}"
    if isinstance(v, date):
        return v.strftime("%d-%m-%Y")
    return v


class _Filters:
    """Source + month + supplier filter shared by both pages."""

    def build(self, page, bar: QHBoxLayout) -> None:
        page.source = QComboBox()
        page.source.addItem("Tally books (purchase register)", "books")
        page.source.addItem("IPT invoices", "ipt")
        page.month = QComboBox()
        for w in (muted("Source"), page.source, muted("Month"), page.month):
            bar.addWidget(w)

    @staticmethod
    def months(page) -> None:
        fy = next((f for f in page.s.companies.list_fys(page.s.ctx.company_id) if f.id == page.s.ctx.fy_id), None) \
            if page.s.ctx.company_id else None
        cur = page.month.currentData()
        page.month.blockSignals(True)
        page.month.clear()
        page.month.addItem("Whole year", None)
        for m in (fy_months(fy) if fy else []):
            page.month.addItem(f"{m:%b %Y}", m)
        page.month.setCurrentIndex(max(0, page.month.findData(cur)))
        page.month.blockSignals(False)

    @staticmethod
    def range(page):
        m = page.month.currentData()
        if m is None:
            return None, None
        nxt = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
        return m, date.fromordinal(nxt.toordinal() - 1)


class MisReportsPage(BasePage):
    title_text = "MIS Reports"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("MIS Reports"))
        bar = QHBoxLayout()
        self.report = QComboBox()
        for k, v in REPORTS.items():
            self.report.addItem(v, k)
        bar.addWidget(self.report)
        _Filters().build(self, bar)
        self.supplier = QLineEdit()
        self.supplier.setPlaceholderText("Supplier / GSTIN")
        bar.addWidget(self.supplier)
        self.btn_show = QPushButton("Show")
        self.btn_show.setObjectName("Primary")
        self.btn_xlsx, self.btn_csv, self.btn_pdf = QPushButton("Excel"), QPushButton("CSV"), QPushButton("PDF")
        for b in (self.btn_show, self.btn_xlsx, self.btn_csv, self.btn_pdf):
            bar.addWidget(b)
        bar.addStretch(1)
        self.layout_.addLayout(bar)
        self.note = muted("")
        self.layout_.addWidget(self.note)
        self.table = make_table([])
        self.layout_.addWidget(self.table, 1)
        self.rep = None
        for w in (self.report, self.source, self.month):
            w.currentIndexChanged.connect(self._show)
        self.supplier.returnPressed.connect(self._show)
        self.btn_show.clicked.connect(self._show)
        self.btn_xlsx.clicked.connect(lambda: self._export("xlsx"))
        self.btn_csv.clicked.connect(lambda: self._export("csv"))
        self.btn_pdf.clicked.connect(lambda: self._export("pdf"))

    def refresh(self) -> None:
        role = self.s.ctx.user.role if self.s.ctx.user else None
        for b in (self.btn_xlsx, self.btn_csv, self.btn_pdf):
            b.setEnabled(has_permission(role, "export.run"))
        _Filters.months(self)
        self._show()

    def _show(self) -> None:
        if not self.s.ctx.fy_id:
            return
        start, end = _Filters.range(self)
        try:
            self.rep = self.s.reports.report(self.report.currentData(), self.source.currentData(), start, end,
                                             self.supplier.text())
        except PermissionDenied as e:
            error(self, str(e))
            return
        money = set(self.rep.money_columns())
        self.table.setColumnCount(len(self.rep.headers))
        self.table.setHorizontalHeaderLabels(self.rep.headers)
        rows = [[_fmt(v, i in money) for i, v in enumerate(r)] for r in self.rep.rows]
        if self.rep.totals:
            rows.append([_fmt(v, i in money) for i, v in enumerate(self.rep.totals)])
        fill_table(self.table, rows)
        self.table.setSortingEnabled(False)
        self.note.setText(f"{len(self.rep.rows)} row(s). {self.rep.note}")

    def _export(self, kind: str) -> None:
        if self.rep is None:
            return
        ext = {"xlsx": "Excel (*.xlsx)", "csv": "CSV (*.csv)", "pdf": "PDF (*.pdf)"}[kind]
        name = self.rep.title.split(" – ")[0].replace(" ", "_") + "." + kind
        path, _ = QFileDialog.getSaveFileName(self, "Save report", name, ext)
        if not path:
            return
        try:
            if kind == "xlsx":
                self.s.exports.report_xlsx(self.rep, Path(path))
            elif kind == "csv":
                self.s.exports.report_csv(self.rep, Path(path))
            else:
                company = self.s.companies.get_company(self.s.ctx.company_id)
                self.s.exports.report_pdf(self.rep, Path(path), company.name if company else "", self.month.currentText())
        except (PermissionDenied, OSError) as e:
            error(self, str(e))
            return
        info(self, f"Saved {path}")


class ExportCentrePage(BasePage):
    title_text = "Export Centre"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("Export Centre"))
        self.layout_.addWidget(muted("Full workbook: " + ", ".join(WORKBOOK_SHEETS) + ". Single reports (Excel, CSV, PDF) "
                                     "are in MIS Reports. Every export is recorded in the audit trail."))
        bar = QHBoxLayout()
        _Filters().build(self, bar)
        self.btn_wb = QPushButton("Export 12-sheet workbook…")
        self.btn_wb.setObjectName("Primary")
        bar.addWidget(self.btn_wb)
        bar.addStretch(1)
        self.layout_.addLayout(bar)
        self.layout_.addWidget(title("Tally XML batch"))
        self.layout_.addWidget(muted("One import file with the vouchers of the selected approved, fully mapped invoices "
                                     "– for importing in Tally yourself (Import → Vouchers). Invoices that are not "
                                     "ready are skipped and listed."))
        xb = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItem("Item invoice (with stock items)", "inventory")
        self.mode.addItem("Accounting invoice (ledgers only)", "accounting")
        self.btn_xml = QPushButton("Save XML for selected invoices…")
        xb.addWidget(self.mode)
        xb.addWidget(self.btn_xml)
        xb.addStretch(1)
        self.layout_.addLayout(xb)
        self.table = make_table(["Supplier", "Invoice no", "Date", "Total", "Status"])
        self.table.setSelectionMode(self.table.SelectionMode.ExtendedSelection)
        self.layout_.addWidget(self.table, 1)
        self.layout_.addWidget(muted("Other accounting software (Tally ERP 9 older formats, Zoho Books, Marg): not "
                                     "included – their exact import formats have not been verified, so IPT does not "
                                     "produce them."))
        self.status = muted("")
        self.layout_.addWidget(self.status)
        self.btn_wb.clicked.connect(self._workbook)
        self.btn_xml.clicked.connect(self._xml)

    def refresh(self) -> None:
        role = self.s.ctx.user.role if self.s.ctx.user else None
        self.btn_wb.setEnabled(has_permission(role, "export.run"))
        self.btn_xml.setEnabled(has_permission(role, "export.run"))
        _Filters.months(self)
        invs = [i for i in self.s.invoices.list_invoices() if i.status in ("approved", "imported")]
        fill_table(self.table, [[i.supplier_name, i.invoice_no, i.invoice_date.strftime("%d-%m-%Y")
                                 if i.invoice_date else "", format_inr(i.invoice_total), i.status] for i in invs],
                   [i.id for i in invs])

    def _workbook(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save workbook", "IPT_Export.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        start, end = _Filters.range(self)
        self.btn_wb.setEnabled(False)

        def done(p):
            self.btn_wb.setEnabled(True)
            self.status.setText("")
            info(self, f"Saved {p}")

        def failed(msg):
            self.btn_wb.setEnabled(True)
            self.status.setText("")
            error(self, msg)

        self._job = worker.start(worker.Job(self.s.exports.workbook, Path(path), self.source.currentData(), start, end,
                                            with_progress=True), done, failed, self.status.setText)

    def _xml(self) -> None:
        from PySide6.QtCore import Qt
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        ids = [self.table.item(r, 0).data(Qt.UserRole) for r in rows]
        if not ids:
            error(self, "Select one or more invoices")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Tally XML", "IPT_vouchers.xml", "XML (*.xml)")
        if not path:
            return
        try:
            n, skipped = self.s.exports.tally_xml_batch(ids, Path(path), self.mode.currentData())
        except (ValueError, PermissionDenied) as e:
            error(self, str(e))
            return
        msg = f"{n} voucher(s) saved to {path}."
        if skipped:
            msg += "\n\nSkipped:\n" + "\n".join(skipped[:10])
        info(self, msg)
