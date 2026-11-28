"""Supplier Masters: suppliers identified by GSTIN from extracted invoices."""
from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLineEdit, QPushButton,
                               QVBoxLayout)

from ipt.core.money import format_inr
from ipt.core.permissions import PermissionDenied, has_permission
from ipt.core.states import state_name
from ipt.services.invoice_service import InvoiceError
from ipt.ui.helpers import error, fill_table, make_table, muted, selected_id, title
from ipt.ui.pages.base import BasePage


class SuppliersPage(BasePage):
    title_text = "Supplier Masters"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("Supplier Masters"))
        self.layout_.addWidget(muted("Suppliers are added automatically when an invoice with a valid GSTIN is "
                                     "extracted. Set the Tally ledger name to speed up mapping in Phase 3."))
        bar = QHBoxLayout()
        self.btn_edit = QPushButton("Edit")
        bar.addWidget(self.btn_edit)
        bar.addStretch(1)
        self.layout_.addLayout(bar)
        self.table = make_table(["Supplier", "GSTIN", "PAN", "State", "Tally ledger", "Invoices", "Total value"])
        self.layout_.addWidget(self.table, 1)
        self.btn_edit.clicked.connect(self._edit)
        self.table.doubleClicked.connect(lambda _: self._edit())

    def refresh(self):
        self.btn_edit.setEnabled(has_permission(self.s.ctx.user.role if self.s.ctx.user else None, "invoice.edit"))
        rows = self.s.invoices.list_suppliers()
        self._data = {sup.id: sup for sup, _, _ in rows}
        fill_table(self.table, [[sup.name, sup.gstin, sup.pan, f"{sup.state_code} {state_name(sup.state_code)}",
                                 sup.tally_ledger_name, n, format_inr(total)] for sup, n, total in rows],
                   [sup.id for sup, _, _ in rows])

    def _edit(self):
        sid = selected_id(self.table)
        if not sid:
            error(self, "Select a supplier first")
            return
        sup = self._data[sid]
        dlg = QDialog(self)
        dlg.setWindowTitle("Edit supplier")
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        name, addr, ledger = QLineEdit(sup.name), QLineEdit(sup.address), QLineEdit(sup.tally_ledger_name)
        form.addRow("GSTIN", QLineEdit(sup.gstin or "", readOnly=True))
        form.addRow("Name", name)
        form.addRow("Address", addr)
        form.addRow("Tally ledger name", ledger)
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec():
            try:
                self.s.invoices.update_supplier(sid, name.text(), addr.text(), ledger.text())
            except (InvoiceError, PermissionDenied) as e:
                error(self, str(e))
            self.refresh()
