"""XML Import log: every voucher sent to Tally with Tally's exact answer."""
from __future__ import annotations

from ipt.core.timefmt import fmt

from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit, QPushButton

from ipt.core.permissions import PermissionDenied
from ipt.services.tally.client import TallyError
from ipt.ui.helpers import error, info

from ipt.ui.helpers import fill_table, make_table, muted, selected_id, title
from ipt.ui.pages.base import BasePage


class ImportsPage(BasePage):
    title_text = "XML Import"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("Tally Import Log"))
        self.layout_.addWidget(muted("Success means Tally created the voucher AND IPT found it again in Tally. "
                                     "Failed imports keep the invoice approved so it can be fixed and retried."))
        bar = QHBoxLayout()
        self.btn_recheck = QPushButton("Re-check in Tally")
        bar.addWidget(self.btn_recheck)
        bar.addStretch(1)
        self.layout_.addLayout(bar)
        self.btn_recheck.clicked.connect(self._recheck)
        self.table = make_table(["When", "Invoice", "Tally company", "Status", "Created", "Errors", "Tally ID", "User",
                                 "Remark"])
        self.layout_.addWidget(self.table, 1)
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(180)
        self.layout_.addWidget(self.detail)
        self.table.itemSelectionChanged.connect(self._show)

    def refresh(self):
        self._rows = {r.id: r for r in self.s.imports.history()}
        rows = []
        for r in self._rows.values():
            inv = self.s.invoices.get(r.invoice_id) if r.invoice_id else None
            rows.append([fmt(r.at), f"{inv.supplier_name} {inv.invoice_no}" if inv else r.invoice_id,
                         r.tally_company, {"success": "✅ success", "failed": "⛔ failed",
                                           "unverified": "⚠ not found again",
                                           "removed": "🗑 deleted in Tally"}.get(r.status, r.status),
                         r.created, r.errors, r.tally_master_id, r.username, r.remark])
        fill_table(self.table, rows, list(self._rows))

    def _show(self):
        r = self._rows.get(selected_id(self.table))
        self.detail.setPlainText("" if r is None else
                                 f"Request saved at: {r.request_xml_path}\n\nTally errors:\n{r.line_errors or '-'}"
                                 f"\n\nTally response:\n{r.response_xml}")

    def _recheck(self):
        rid = selected_id(self.table)
        r = self._rows.get(rid)
        if r is None:
            error(self, "Select an import first")
            return
        if r.status == "removed":
            error(self, "This voucher was already found deleted in Tally. Import the invoice again from "
                        "Purchase Vouchers.")
            return
        try:
            rec = self.s.imports.recheck(rid)
        except (TallyError, PermissionDenied) as e:
            error(self, str(e))
            return
        self.refresh()
        if rec.status == "removed":
            info(self, "This voucher is no longer in Tally (it was deleted there). The invoice is back to "
                        "'approved' and can be imported again from Purchase Vouchers.")
        elif r.status == "success" and rec.status == "success":
            info(self, "Checked: the voucher is still in Tally.")
        elif rec.status != "success":
            error(self, "The voucher was still not found in Tally for that date, party and invoice no.")
