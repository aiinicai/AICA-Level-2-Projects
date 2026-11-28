"""Processed Invoices: list, filter, open review, bulk approve/reject, export to Excel."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLineEdit, QMessageBox, QPushButton

from ipt.core.money import format_inr
from ipt.core.permissions import PermissionDenied, has_permission
from ipt.services.invoice_service import STATUSES, InvoiceError
from ipt.ui.helpers import (checked_ids, confirm, error, info, fill_table, make_checkable, make_table, muted,
                            set_all_checked, title)
from ipt.ui.invoice_review import InvoiceReviewDialog
from ipt.ui.pages.base import BasePage


class ProcessedInvoicesPage(BasePage):
    title_text = "Processed Invoices"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("Processed Invoices"))
        self.layout_.addWidget(muted("Double-click an invoice to review it next to the original document."))
        bar = QHBoxLayout()
        self.status = QComboBox()
        self.status.addItem("All statuses", None)
        for st in STATUSES:
            self.status.addItem(st.replace("_", " ").capitalize(), st)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search supplier, GSTIN or invoice no.")
        self.btn_open = QPushButton("Review")
        self.btn_open.setObjectName("Primary")
        self.btn_all = QPushButton("Select all")
        self.btn_select_ok = QPushButton("Select validated")
        self.btn_select_ok.setToolTip("Select every invoice read with confidence and no errors (status 'validated')")
        self.btn_approve = QPushButton("Approve ticked")
        self.btn_reject = QPushButton("Reject ticked")
        self.btn_delete = QPushButton("Delete ticked")
        self.btn_export = QPushButton("Export to Excel")
        self.btn_claude = QPushButton("Check ticked with Claude Code")
        self.btn_claude.setToolTip("Send the ticked bills that need review to Claude Code (Settings: Claude Code "
                                   "check). IPT checks every value it returns; you still approve.")
        bar.addWidget(self.status)
        bar.addWidget(self.search, 1)
        for b in (self.btn_open, self.btn_all, self.btn_select_ok, self.btn_approve, self.btn_reject, self.btn_delete,
                  self.btn_claude, self.btn_export):
            bar.addWidget(b)
        self.layout_.addLayout(bar)
        self.table = make_table(["", "Supplier", "GSTIN", "Invoice no", "Date", "Type", "Taxable", "GST", "Total",
                                 "Status", "Errors", "Warnings", "Tally"])
        self.layout_.addWidget(self.table, 1)
        self.summary = muted("")
        self.layout_.addWidget(self.summary)
        self.status.currentIndexChanged.connect(self.refresh)
        self.search.returnPressed.connect(self.refresh)
        self.table.doubleClicked.connect(lambda _: self._open())
        self.btn_open.clicked.connect(self._open)
        self.btn_approve.clicked.connect(self._approve)
        self.btn_select_ok.clicked.connect(self._select_validated)
        self.btn_all.clicked.connect(self._toggle_all)
        self.table.itemChanged.connect(lambda _: self._update_count())
        self.btn_reject.clicked.connect(self._reject)
        self.btn_delete.clicked.connect(self._delete)
        self.btn_export.clicked.connect(self._export)
        self.btn_claude.clicked.connect(self._claude)

    def refresh(self) -> None:
        role = self.s.ctx.user.role if self.s.ctx.user else None
        self.btn_approve.setEnabled(has_permission(role, "invoice.approve"))
        self.btn_reject.setEnabled(has_permission(role, "invoice.approve"))
        self.btn_delete.setEnabled(has_permission(role, "invoice.delete"))
        from ipt.services import claude_assist
        self.btn_claude.setVisible(claude_assist.mode(self.s.settings, self.s.ctx.company_id) != "off")
        invs = self.s.invoices.list_invoices(self.status.currentData(), self.search.text())
        rows = []
        c = self.s.companies.get_company(self.s.ctx.company_id) if self.s.ctx.company_id else None
        linked = bool(c and c.tally_company_name and self.s.tally.masters("ledger"))
        for i in invs:
            fs = self.s.invoices.findings(i.id)
            gst = sum(v for v in (i.cgst, i.sgst, i.igst, i.cess) if v is not None) if any(
                v is not None for v in (i.cgst, i.sgst, i.igst, i.cess)) else None
            rows.append(["", i.supplier_name, i.supplier_gstin, i.invoice_no,
                         i.invoice_date.strftime("%d-%m-%Y") if i.invoice_date else "",
                         i.doc_type.replace("_", " "), format_inr(i.taxable_total), format_inr(gst),
                         format_inr(i.invoice_total), i.status.replace("_", " "),
                         sum(f.severity == "error" for f in fs), sum(f.severity == "warning" for f in fs),
                         self.s.vouchers.readiness(i.id, i.status) if linked else ""])
        self.table.blockSignals(True)
        fill_table(self.table, rows, [i.id for i in invs])
        from PySide6.QtGui import QColor
        col = self.table.columnCount() - 1                      # 'Tally': red when something must be mapped
        for r in range(self.table.rowCount()):
            cell = self.table.item(r, col)
            if cell is not None and cell.text().startswith(("Map:", "Fix:")):
                cell.setForeground(QColor("#b91c1c"))
                cell.setToolTip("Open Purchase Vouchers (preview) or Master Mapping to see what is missing")
            elif cell is not None and cell.text().startswith("Ready"):
                cell.setForeground(QColor("#15803d"))
        make_checkable(self.table)
        self.table.blockSignals(False)
        self._update_count()

    def _claude(self) -> None:
        from ipt.services import claude_assist
        ids = self._ids()
        if not ids:
            error(self, "Tick the bills to check first")
            return
        n = claude_assist.export_cases(self.s, ids)
        waiting = {int(c.name.split("-", 1)[1]) for c in claude_assist.pending(self.s.data_root)}
        already = len([i for i in ids if i in waiting]) - n
        lines = [f"{n} bill(s) newly sent to Claude Code."]
        if already > 0:
            lines.append(f"{already} ticked bill(s) were already waiting for Claude Code (sent after extraction).")
        if not n and not already:
            lines.append("Only bills that need review are sent – the ticked ones are validated / approved.")
        if waiting:
            if claude_assist.mode(self.s.settings, self.s.ctx.company_id) == "auto":
                lines.append(claude_assist.launch(self.s.data_root))
            elif claude_assist.find_claude():
                lines.append(f"{len(waiting)} bill(s) wait in {claude_assist.queue_dir(self.s.data_root)} – run "
                             "Claude Code there, or Settings → 'Check waiting bills now'.")
            else:
                lines.append(f"{len(waiting)} bill(s) are waiting. Claude Code is not installed on this PC: ask Claude "
                             "in your chat to check the waiting bills, or install Claude Code.")
        info(self, "\n".join(lines))

    def _ids(self, selected_only=True) -> list[int]:
        """Ticked invoices (else the highlighted row) - or every listed invoice."""
        if not selected_only:
            return [self.table.item(r, 0).data(Qt.UserRole) for r in range(self.table.rowCount())]
        ticked = checked_ids(self.table)
        if ticked:
            return ticked
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self.table.item(r, 0).data(Qt.UserRole) for r in rows]

    def _update_count(self):
        n = len(checked_ids(self.table))
        self.btn_all.setText("Deselect all" if n and n == self.table.rowCount() else "Select all")
        self.summary.setText(f"{self.table.rowCount()} invoice(s)" + (f" · {n} ticked" if n else ""))

    def _toggle_all(self):
        self.table.blockSignals(True)
        set_all_checked(self.table, self.btn_all.text() == "Select all")
        self.table.blockSignals(False)
        self._update_count()

    def _open(self):
        row = self.table.currentRow()
        sel = [self.table.item(row, 0).data(Qt.UserRole)] if row >= 0 else self._ids()
        if not sel:
            error(self, "Select an invoice first")
            return
        all_ids = self._ids(selected_only=False)
        InvoiceReviewDialog(self.s, all_ids, all_ids.index(sel[0]), self).exec()
        self.refresh()

    def _select_validated(self):
        self.table.blockSignals(True)
        n = set_all_checked(self.table, True,
                            lambda r: self.table.item(r, 9) is not None and self.table.item(r, 9).text() == "validated")
        self.table.blockSignals(False)
        self._update_count()
        if not n:
            error(self, "No invoice has the status 'validated'.")

    def _approve(self):
        ids = self._ids()
        if not ids:
            error(self, "Select invoices first")
            return
        status = {i.id: i.status for i in self.s.invoices.list_invoices(None, "")}
        ok_ids = [i for i in ids if status.get(i) == "validated"]
        other = [i for i in ids if status.get(i) not in ("validated", "approved", "imported")]
        remark = ""
        if other:
            with_errors = [i for i in other if any(f.severity == "error" for f in self.s.invoices.findings(i))]
            box = QMessageBox(self)
            box.setWindowTitle("Approve ticked")
            box.setIcon(QMessageBox.Warning)
            box.setText(f"{len(ok_ids)} ticked invoice(s) are validated. {len(other)} still need review"
                        + (f" ({len(with_errors)} with errors)" if with_errors else
                           " (no errors – some values were read with low confidence)") + ".")
            box.setInformativeText("Approve the ones that need review too? You take responsibility for their values; "
                                   "your reason is kept in the remarks and the audit trail.")
            b_all = box.addButton(f"Approve all {len(ok_ids) + len(other)}", QMessageBox.AcceptRole)
            b_ok = box.addButton(f"Only the {len(ok_ids)} validated", QMessageBox.ActionRole) if ok_ids else None
            box.addButton(QMessageBox.Cancel)
            box.exec()
            clicked = box.clickedButton()
            if clicked is b_all:
                remark, ok = QInputDialog.getText(self, "Approve without review",
                                                  f"Reason for approving {len(other)} invoice(s) that need review "
                                                  "(kept in the audit trail):", text="Checked against the bills")
                if not ok or not remark.strip():
                    return
                ids = ok_ids + other
            elif b_ok is not None and clicked is b_ok:
                ids = ok_ids
            else:
                return
        elif ok_ids and confirm(self, f"Approve {len(ok_ids)} validated invoice(s)?"):
            ids = ok_ids
        else:
            return
        failed = []
        for iid in ids:
            try:
                self.s.invoices.approve(iid, remark if iid in other else "")
            except (InvoiceError, PermissionDenied) as e:
                failed.append(f"#{iid}: {e}")
        self.refresh()
        if failed:
            error(self, "Not approved:\n" + "\n".join(failed[:10]))
        else:
            info(self, f"{len(ids)} invoice(s) approved.")

    def _reject(self):
        ids = self._ids()
        if not ids:
            error(self, "Select invoices first")
            return
        remark, ok = QInputDialog.getText(self, "Reject", f"Reason for rejecting {len(ids)} invoice(s):")
        if ok:
            try:
                for iid in ids:
                    self.s.invoices.reject(iid, remark)
            except (InvoiceError, PermissionDenied) as e:
                error(self, str(e))
            self.refresh()

    def _delete(self):
        ids = self._ids()
        if not ids:
            error(self, "Select invoices first")
            return
        if not confirm(self, f"Delete {len(ids)} extracted invoice(s)? This cannot be undone. Their pages go "
                             "back to the extraction queue so they can be read again."):
            return
        done, failed = 0, []
        for iid in ids:
            try:
                self.s.invoices.delete(iid)
                done += 1
            except (InvoiceError, PermissionDenied) as e:
                failed.append(str(e))
        self.refresh()
        self.summary.setText(f"Deleted {done} invoice(s)." + (f" Not deleted: {len(failed)} – {failed[0]}"
                                                              if failed else ""))

    def _export(self):
        ids = self._ids() or self._ids(selected_only=False)
        if not ids:
            error(self, "There are no invoices to export")
            return
        default = str(Path.home() / f"IPT_Invoices_{datetime.now():%Y%m%d_%H%M}.xlsx")
        path, _ = QFileDialog.getSaveFileName(self, "Export invoices", default, "Excel (*.xlsx)")
        if path:
            try:
                self.s.invoices.export_xlsx(ids, Path(path))
                self.summary.setText(f"Exported {len(ids)} invoice(s) to {path}")
            except (PermissionDenied, OSError) as e:
                error(self, str(e))
