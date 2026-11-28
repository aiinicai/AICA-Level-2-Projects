"""Exception Management: one inbox for invoice errors, failed Tally imports and open reconciliation differences."""
from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QPushButton

from ipt.core.permissions import PermissionDenied, has_permission
from ipt.core.timefmt import fmt
from ipt.services.recon.recon_service import ReconError
from ipt.ui.helpers import error, fill_table, make_table, muted, title
from ipt.ui.invoice_review import InvoiceReviewDialog
from ipt.ui.pages.base import BasePage
from ipt.ui.pages.recon import ActionDialog, nice

KINDS = {"invoice": "Invoice check", "import": "Tally import", "recon": "Reconciliation"}


class ExceptionsPage(BasePage):
    title_text = "Exception Management"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("Exception Management"))
        self.layout_.addWidget(muted("Everything that still needs a person: invoices with errors or low-confidence "
                                     "fields, Tally imports that failed or could not be verified, and reconciliation "
                                     "differences that are not yet Resolved or Accepted."))
        bar = QHBoxLayout()
        self.kind = QComboBox()
        self.kind.addItem("All", None)
        for k, v in KINDS.items():
            self.kind.addItem(v, k)
        self.btn_open = QPushButton("Open / act on selected")
        self.btn_open.setObjectName("Primary")
        bar.addWidget(self.kind)
        bar.addWidget(self.btn_open)
        bar.addStretch(1)
        self.summary = muted("")
        bar.addWidget(self.summary)
        self.layout_.addLayout(bar)
        self.table = make_table(["Area", "Reference", "Supplier", "Problem", "Status", "Since / action"])
        self.layout_.addWidget(self.table, 1)
        self.kind.currentIndexChanged.connect(self.refresh)
        self.btn_open.clicked.connect(self._open)
        self.table.doubleClicked.connect(lambda _: self._open())
        self.items: list[dict] = []

    def _collect(self) -> list[dict]:
        out = []
        if not self.s.ctx.fy_id:
            return out
        for inv in self.s.invoices.list_invoices("needs_review"):
            errs = [f.message for f in self.s.invoices.findings(inv.id) if f.severity == "error"]
            out.append({"kind": "invoice", "id": inv.id, "ref": inv.invoice_no or f"IPT #{inv.id}",
                        "supplier": inv.supplier_name or "", "problem": errs[0] if errs else
                        "Fields with low confidence – check against the document", "status": "Needs review",
                        "extra": f"{len(errs)} error(s)"})
        for imp in self.s.imports.history():
            if imp.status in ("failed", "unverified"):
                out.append({"kind": "import", "id": imp.id, "ref": f"Import #{imp.id}", "supplier": imp.tally_company,
                            "problem": (imp.line_errors or "Created but not found again in Tally")[:200],
                            "status": imp.status.title(), "extra": fmt(imp.at)})
        for r in self.s.recon.exceptions():
            reasons = json.loads(r.reasons_json or "[]")
            out.append({"kind": "recon", "id": r.id, "ref": r.doc_no, "supplier": r.supplier_name,
                        "problem": f"{nice(r.status)}: {reasons[0] if reasons else ''}", "status": r.action_status,
                        "extra": r.suggested_action})
        return out

    def refresh(self) -> None:
        role = self.s.ctx.user.role if self.s.ctx.user else None
        self.items = self._collect()
        k = self.kind.currentData()
        shown = [x for x in self.items if k is None or x["kind"] == k]
        fill_table(self.table, [[KINDS[x["kind"]], x["ref"], x["supplier"], x["problem"], x["status"], x["extra"]]
                                for x in shown], list(range(len(shown))))
        self._shown = shown
        counts = {v: sum(1 for x in self.items if x["kind"] == key) for key, v in KINDS.items()}
        self.summary.setText(" · ".join(f"{k}: {v}" for k, v in counts.items()))
        self.btn_open.setEnabled(has_permission(role, "invoice.view"))

    def _open(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            error(self, "Select an item")
            return
        x = self._shown[self.table.item(row, 0).data(Qt.UserRole)]
        if x["kind"] == "invoice":
            ids = [i["id"] for i in self._shown if i["kind"] == "invoice"]
            InvoiceReviewDialog(self.s, ids, ids.index(x["id"]), self).exec()
        elif x["kind"] == "recon":
            r = self.s.recon.get_row(x["id"])
            dlg = ActionDialog(r.action_status, r.remarks, self)
            if dlg.exec() == QDialog.Accepted:
                try:
                    self.s.recon.update_action(r.id, dlg.status.currentText(), dlg.remarks.toPlainText())
                except (ReconError, PermissionDenied) as e:
                    error(self, str(e))
        else:
            error(self, "Open 'XML Import' and use 'Re-check in Tally' for this import.")
        self.refresh()
