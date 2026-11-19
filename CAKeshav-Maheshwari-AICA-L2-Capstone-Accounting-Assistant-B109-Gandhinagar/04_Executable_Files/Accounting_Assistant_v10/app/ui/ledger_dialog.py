"""Create a ledger (supplier, customer, expense…) in TallyPrime from the app."""
from __future__ import annotations

from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
                             QMessageBox)

from ..engine import ledgers as ledgers_mod
from ..gst_states import state_name
from ..tally.parsers import gstin_valid


class LedgerDialog(QDialog):
    def __init__(self, st, company, groups: list[str], *, name: str = "", parent_group: str = "Sundry Creditors",
                 gstin: str = "", vendor_key: str = "", parent=None):
        super().__init__(parent)
        self.st, self.company, self.vendor_key = st, company, vendor_key
        self.created_name = ""
        self.setWindowTitle("New ledger in Tally")
        self.setMinimumWidth(460)
        f = QFormLayout(self)
        f.addRow(QLabel(f"Creates the ledger directly in TallyPrime for <b>{company.name}</b>.", wordWrap=True))
        self.name = QLineEdit(name)
        self.group = QComboBox()
        self.group.setEditable(True)
        self.group.addItems(sorted(set(groups) | {"Sundry Creditors", "Sundry Debtors", "Indirect Expenses",
                                                  "Direct Expenses", "Purchase Accounts", "Fixed Assets",
                                                  "Duties & Taxes"}))
        self.group.setCurrentText(parent_group)
        self.gstin = QLineEdit(gstin)
        self.gstin.setPlaceholderText("leave blank if unregistered")
        self.state = QLineEdit(state_name(gstin[:2]) if gstin else "")
        self.pan = QLineEdit(gstin[2:12] if len(gstin) == 15 else "")
        self.billwise = QCheckBox("Maintain bill-by-bill")
        self.billwise.setChecked(parent_group in ("Sundry Creditors", "Sundry Debtors"))
        self.gstin.textChanged.connect(self._gstin_changed)
        self.group.currentTextChanged.connect(lambda g: self.billwise.setChecked(
            g in ("Sundry Creditors", "Sundry Debtors")))
        for lbl, w in (("Name", self.name), ("Under (group)", self.group), ("GSTIN", self.gstin), ("State", self.state),
                       ("PAN", self.pan), ("", self.billwise)):
            f.addRow(lbl, w)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.btn_create = b.addButton("Create in Tally", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_create.setObjectName("primary")
        b.accepted.connect(self.create)
        b.rejected.connect(self.reject)
        f.addRow(b)

    def _gstin_changed(self, t: str):
        t = t.strip().upper()
        if len(t) == 15:
            self.state.setText(state_name(t[:2]))
            self.pan.setText(t[2:12])

    def create(self):
        g = self.gstin.text().strip().upper()
        if g and not gstin_valid(g):
            QMessageBox.warning(self, "GSTIN", f"{g} fails the GSTIN check digit. Correct it or leave it blank.")
            return
        try:
            ledgers_mod.create_ledger(self.st.session, self.st.client(self.company), self.company,
                                      self.name.text(), self.group.currentText().strip(), gstin=g,
                                      pan=self.pan.text().strip().upper(), state=self.state.text().strip(),
                                      bill_wise=self.billwise.isChecked(), vendor_key=self.vendor_key,
                                      actor=self.st.actor)
        except Exception as e:
            QMessageBox.warning(self, "Tally", str(e))
            return
        self.created_name = self.name.text().strip()
        self.accept()
