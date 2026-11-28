"""GST Reconciliation: run, status chips, grid with the three sources, compare view, actions, manual match."""
from __future__ import annotations

import html
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QInputDialog, QLineEdit, QPlainTextEdit, QPushButton, QSpinBox, QSplitter,
                               QTextBrowser)

from ipt.core.money import format_inr
from ipt.core.permissions import PermissionDenied, has_permission
from ipt.core.timefmt import fmt
from ipt.services.recon.engine import MODE_LABEL, SOURCE_LABEL, STATUS_ORDER, Settings
from ipt.services.recon.recon_service import ACTION_STATUSES, ReconError
from ipt.ui import worker
from ipt.ui.helpers import error, fill_table, info, make_table, muted, title
from ipt.ui.pages.base import BasePage

STATUS_COLOUR = {"MATCHED": "#dcfce7", "PARTIALLY_MATCHED": "#fef9c3", "NOT_IN_IPT": "#e0f2fe",
                 "AMOUNT_MISMATCH": "#fee2e2", "GSTIN_MISMATCH": "#fee2e2", "NOT_IN_2B": "#ffedd5",
                 "NOT_IN_BOOKS": "#ffedd5", "DUPLICATE": "#fecaca", "AMENDED": "#ede9fe", "CDN_DIFFERENCE": "#fee2e2"}


def nice(status: str) -> str:
    return status.replace("_", " ").title().replace("2B", "2B").replace("Ipt", "IPT").replace("In 2B", "in 2B")


def fy_months(fy) -> list[date]:
    out, y, m = [], fy.start_date.year, fy.start_date.month
    while date(y, m, 1) <= fy.end_date:
        out.append(date(y, m, 1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


class SettingsDialog(QDialog):
    def __init__(self, st: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reconciliation tolerances")
        f = QFormLayout(self)
        self.taxable, self.tax, self.total = QDoubleSpinBox(), QDoubleSpinBox(), QDoubleSpinBox()
        for w, v in ((self.taxable, st.taxable_tol), (self.tax, st.tax_tol), (self.total, st.total_tol)):
            w.setRange(0, 100000)
            w.setDecimals(2)
            w.setValue(float(v))
            w.setPrefix("₹ ")
        self.days = QSpinBox()
        self.days.setRange(0, 365)
        self.days.setValue(st.date_tol_days)
        self.sim = QSpinBox()
        self.sim.setRange(50, 100)
        self.sim.setSuffix(" %")
        self.sim.setValue(st.similarity)
        f.addRow(muted("Conservative defaults: ₹1 on each amount, same date, 90% invoice-number similarity."))
        f.addRow("Taxable value", self.taxable)
        f.addRow("Each tax head (CGST/SGST/IGST/Cess)", self.tax)
        f.addRow("Invoice total", self.total)
        f.addRow("Date difference (days)", self.days)
        f.addRow("Invoice-number similarity", self.sim)
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        f.addRow(b)

    def value(self) -> Settings:
        q = lambda w: Decimal(str(round(w.value(), 2)))  # noqa: E731
        return Settings(q(self.taxable), q(self.tax), q(self.total), self.days.value(), self.sim.value())


class ActionDialog(QDialog):
    def __init__(self, status: str, remarks: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Action")
        f = QFormLayout(self)
        self.status = QComboBox()
        self.status.addItems(ACTION_STATUSES)
        self.status.setCurrentText(status)
        self.remarks = QPlainTextEdit(remarks)
        f.addRow("Action status", self.status)
        f.addRow("Remarks", self.remarks)
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        f.addRow(b)


class ReconPage(BasePage):
    title_text = "GST Reconciliation"
    COLS = ["Status", "Supplier", "GSTIN", "Invoice no", "Date", "IPT taxable", "Tally taxable", "2B taxable",
            "Tally tax", "2B tax", "Tax diff (2B − Tally)", "Main reason", "Suggested action", "Action", "Remarks"]

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("GST Reconciliation"))
        run = QHBoxLayout()
        self.mode = QComboBox()
        for k, v in MODE_LABEL.items():
            self.mode.addItem(v, k)
        self.month_from, self.month_to = QComboBox(), QComboBox()
        self.btn_settings = QPushButton("Tolerances…")
        self.btn_run = QPushButton("Run reconciliation")
        self.btn_run.setObjectName("Primary")
        for w in (self.mode, muted("From"), self.month_from, muted("To"), self.month_to, self.btn_settings, self.btn_run):
            run.addWidget(w)
        run.addStretch(1)
        self.run_info = muted("")
        run.addWidget(self.run_info)
        self.layout_.addLayout(run)
        self.avail = muted("")
        self.layout_.addWidget(self.avail)
        self.chips = QHBoxLayout()
        self.layout_.addLayout(self.chips)
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search supplier, GSTIN or invoice no.")
        self.btn_action = QPushButton("Set action / remarks…")
        self.btn_link = QPushButton("Manual match (select 2–3 rows)")
        self.btn_unlink = QPushButton("Unmatch")
        self.btn_export = QPushButton("Export view to Excel")
        self.btn_follow = QPushButton("Supplier follow-up list…")
        self.btn_follow.setToolTip("Bills in your books that are missing or different in GSTR-2B, supplier-wise")
        bar.addWidget(self.search, 1)
        for b in (self.btn_action, self.btn_link, self.btn_unlink, self.btn_export, self.btn_follow):
            bar.addWidget(b)
        self.layout_.addLayout(bar)
        split = QSplitter(Qt.Vertical)
        self.table = make_table(self.COLS)
        self.table.setSelectionMode(self.table.SelectionMode.ExtendedSelection)
        split.addWidget(self.table)
        self.detail = QTextBrowser()
        split.addWidget(self.detail)
        split.setSizes([480, 220])
        self.layout_.addWidget(split, 1)
        self.filter_status: str | None = None
        self.rows = []
        self.btn_run.clicked.connect(self._run)
        self.btn_settings.clicked.connect(self._settings)
        self.search.returnPressed.connect(self._fill)
        self.btn_action.clicked.connect(self._action)
        self.btn_link.clicked.connect(self._link)
        self.btn_unlink.clicked.connect(self._unlink)
        self.btn_export.clicked.connect(self._export)
        self.btn_follow.clicked.connect(self._followup)
        self.table.itemSelectionChanged.connect(self._show_detail)
        self.table.doubleClicked.connect(lambda _: self._action())

    # ---------------------------------------------------------------- data
    def refresh(self) -> None:
        role = self.s.ctx.user.role if self.s.ctx.user else None
        self.btn_run.setEnabled(has_permission(role, "recon.run"))
        self.btn_settings.setEnabled(has_permission(role, "recon.run"))
        for b in (self.btn_action, self.btn_link, self.btn_unlink):
            b.setEnabled(has_permission(role, "recon.edit"))
        fy = next((f for f in self.s.companies.list_fys(self.s.ctx.company_id) if f.id == self.s.ctx.fy_id), None) \
            if self.s.ctx.company_id else None
        for box in (self.month_from, self.month_to):
            box.blockSignals(True)
            box.clear()
            box.addItem("Whole year", None)
            for m in (fy_months(fy) if fy else []):
                box.addItem(f"{m:%b %Y}", m)
            box.blockSignals(False)
        a = self.s.recon.availability() if self.s.ctx.fy_id else {"ipt": 0, "pr": 0, "2b": 0}
        self.avail.setText(f"Loaded for this year: IPT invoices {a['ipt']} · Tally books {a['pr']} · GSTR-2B "
                           f"{a['2b']} documents")
        run = self.s.recon.latest_run() if self.s.ctx.fy_id else None
        if run:
            self.run_info.setText(f"Last run: {MODE_LABEL.get(run.mode, run.mode)} · {fmt(run.run_at)} by {run.run_by}")
            self.mode.setCurrentIndex(max(0, self.mode.findData(run.mode)))
        else:
            self.run_info.setText("Not run yet")
        self.rows = self.s.recon.rows() if run else []
        self._chips()
        self._fill()

    def _chips(self) -> None:
        while self.chips.count():
            w = self.chips.takeAt(0).widget()
            if w:
                w.deleteLater()
        counts: dict[str, int] = {}
        for r in self.rows:
            counts[r.status] = counts.get(r.status, 0) + 1
        btn = QPushButton(f"All  {len(self.rows)}")
        btn.setCheckable(True)
        btn.setChecked(self.filter_status is None)
        btn.clicked.connect(lambda: self._set_filter(None))
        self.chips.addWidget(btn)
        for st in STATUS_ORDER:
            if st in counts:
                b = QPushButton(f"{nice(st)}  {counts[st]}")
                b.setCheckable(True)
                b.setChecked(self.filter_status == st)
                b.setStyleSheet(f"background:{STATUS_COLOUR.get(st, '#fff')}; color:#111;")
                b.clicked.connect(lambda _=False, s=st: self._set_filter(s))
                self.chips.addWidget(b)
        self.chips.addStretch(1)

    def _set_filter(self, status) -> None:
        self.filter_status = status
        self._chips()
        self._fill()

    def _visible(self):
        t = self.search.text().strip().lower()
        return [r for r in self.rows if (self.filter_status is None or r.status == self.filter_status)
                and (not t or t in f"{r.supplier_name} {r.supplier_gstin} {r.doc_no}".lower())]

    def _fill(self) -> None:
        rows = self._visible()
        data = []
        for r in rows:
            d = json.loads(r.differences_json or "{}")
            amt = lambda h, s: d.get(h, {}).get(s)  # noqa: E731
            tax = lambda s: (sum(Decimal(amt(h, s)) for h in ("igst", "cgst", "sgst", "cess") if amt(h, s) is not None)  # noqa: E731
                             if any(amt(h, s) is not None for h in ("igst", "cgst", "sgst", "cess")) else None)
            t_pr, t_2b = tax("pr"), tax("2b")
            reasons = json.loads(r.reasons_json or "[]")
            data.append([nice(r.status), r.supplier_name, r.supplier_gstin, r.doc_no,
                         r.doc_date.strftime("%d-%m-%Y") if r.doc_date else "",
                         format_inr(amt("taxable", "ipt")), format_inr(amt("taxable", "pr")),
                         format_inr(amt("taxable", "2b")), format_inr(t_pr), format_inr(t_2b),
                         format_inr(t_2b - t_pr) if t_pr is not None and t_2b is not None else "",
                         reasons[0] if reasons else "", r.suggested_action, r.action_status, r.remarks])
        fill_table(self.table, data, [r.id for r in rows])
        status_of = {r.id: r.status for r in rows}
        for i in range(self.table.rowCount()):          # rows may be re-ordered by sorting: colour by id
            item = self.table.item(i, 0)
            if item:
                item.setBackground(QColor(STATUS_COLOUR.get(status_of.get(item.data(Qt.UserRole)), "#ffffff")))
                item.setForeground(QColor("#111111"))
        self.detail.setHtml("<i>Select a row to compare IPT, Tally and GSTR-2B side by side.</i>")

    def _selected_ids(self) -> list[int]:
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self.table.item(r, 0).data(Qt.UserRole) for r in rows]

    def _show_detail(self) -> None:
        ids = self._selected_ids()
        if len(ids) != 1:
            return
        r = self.s.recon.get_row(ids[0])
        if r is None:
            return
        src = self.s.recon.sources_of(r)
        run = self.s.recon.latest_run()
        from ipt.services.recon.engine import MODES
        shown = [x for x in ("ipt", "pr", "2b") if x in MODES.get(run.mode if run else "three_way", ())]
        fields = ["Supplier", "GSTIN", "Invoice no", "Date", "Taxable", "CGST", "SGST", "IGST", "Cess", "Total"]
        extra = sorted({k for v in src.values() for k in v} - set(fields))
        head = "".join(f"<th>{SOURCE_LABEL[s]}</th>" for s in shown)

        def cell(v):
            if v is None:
                return "—"
            if isinstance(v, date):
                return v.strftime("%d-%m-%Y")
            if isinstance(v, Decimal):
                return format_inr(v)
            return html.escape(str(v))

        body = ""
        for f in fields + extra:
            vals = [src.get(s, {}).get(f) for s in shown]
            present = [v for s, v in zip(shown, vals) if s in src]
            differs = len({str(v) for v in present}) > 1 and f not in ("Supplier",)
            style = " style='background:#fee2e2'" if differs else ""
            body += f"<tr{style}><td><b>{f}</b></td>" + "".join(
                f"<td>{cell(v) if s in src else '<i>not found</i>'}</td>" for s, v in zip(shown, vals)) + "</tr>"
        reasons = "".join(f"<li>{html.escape(x)}</li>" for x in json.loads(r.reasons_json or "[]"))
        self.detail.setHtml(
            f"<b>{nice(r.status)}</b> · stage {r.match_stage or '—'} · confidence "
            f"{r.confidence if r.confidence is not None else '—'}{' · manual' if r.is_manual else ''}"
            f"<table border=1 cellspacing=0 cellpadding=4><tr><th></th>{head}</tr>{body}</table>"
            f"<p><b>Reasons</b><ul>{reasons or '<li>None</li>'}</ul><b>Suggested action:</b> "
            f"{html.escape(r.suggested_action or '—')}</p>")

    # ---------------------------------------------------------------- actions
    def _settings(self) -> None:
        dlg = SettingsDialog(self.s.recon.settings(), self)
        if dlg.exec() == QDialog.Accepted:
            try:
                self.s.recon.save_settings(dlg.value())
            except (ReconError, PermissionDenied) as e:
                error(self, str(e))

    def _run(self) -> None:
        a, b = self.month_from.currentData(), self.month_to.currentData()
        start = a
        end = None
        if b is not None:
            nxt = date(b.year + (b.month == 12), b.month % 12 + 1, 1)
            end = date.fromordinal(nxt.toordinal() - 1)
        if start and end and start > end:
            error(self, "'From' month is after 'To' month")
            return
        self.btn_run.setEnabled(False)
        self.run_info.setText("Reconciling…")

        def done(_):
            self.btn_run.setEnabled(True)
            self.filter_status = None
            self.refresh()

        def failed(msg):
            self.btn_run.setEnabled(True)
            self.refresh()
            error(self, msg)

        self._job = worker.start(worker.Job(self.s.recon.run, self.mode.currentData(), start, end), done, failed)

    def _action(self) -> None:
        ids = self._selected_ids()
        if not ids:
            error(self, "Select a row")
            return
        first = self.s.recon.get_row(ids[0])
        dlg = ActionDialog(first.action_status, first.remarks, self)
        if dlg.exec() != QDialog.Accepted:
            return
        try:
            for i in ids:
                self.s.recon.update_action(i, dlg.status.currentText(), dlg.remarks.toPlainText())
        except (ReconError, PermissionDenied) as e:
            error(self, str(e))
        self.refresh()

    def _link(self) -> None:
        ids = self._selected_ids()
        if len(ids) < 2:
            error(self, "Select the 2 or 3 rows that are the same document (one per source)")
            return
        remark, ok = QInputDialog.getText(self, "Manual match", "Why are these the same document? (required)")
        if not ok:
            return
        try:
            row = self.s.recon.manual_link(ids, remark)
        except (ReconError, PermissionDenied) as e:
            error(self, str(e))
            return
        self.refresh()
        info(self, f"Linked. Status after comparing the records: {nice(row.status)}")

    def _unlink(self) -> None:
        ids = self._selected_ids()
        if len(ids) != 1:
            error(self, "Select one row")
            return
        remark, ok = QInputDialog.getText(self, "Unmatch", "Why is this not the same document? (required)")
        if not ok:
            return
        try:
            self.s.recon.unlink(ids[0], remark)
        except (ReconError, PermissionDenied) as e:
            error(self, str(e))
            return
        self.refresh()

    def _followup(self) -> None:
        if not self.rows:
            error(self, "Run a reconciliation first")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Supplier follow-up list", "Supplier_followup.xlsx",
                                              "Excel (*.xlsx)")
        if not path:
            return
        try:
            self.s.recon.export_followup(Path(path))
        except PermissionDenied as e:
            error(self, str(e))
            return
        info(self, f"Saved {path}\n\nOne sheet per supplier summary (ITC at stake) and the bill-wise list with what to "
                   "ask each supplier.")

    def _export(self) -> None:
        if not self.rows:
            error(self, "Run a reconciliation first")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export reconciliation", "GST_Reconciliation.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        visible = {r.id for r in self._visible()}
        try:
            self.s.recon.export_xlsx(Path(path), [r for r in self.rows if r.id in visible])
        except PermissionDenied as e:
            error(self, str(e))
            return
        info(self, f"Saved {path}")
