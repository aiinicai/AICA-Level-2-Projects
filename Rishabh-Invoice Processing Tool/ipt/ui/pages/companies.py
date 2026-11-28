"""Company & Financial Year management."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSpinBox, QSplitter,
                               QVBoxLayout, QWidget)

from ipt.core.gstin import normalize, validate_gstin
from ipt.core.permissions import PermissionDenied, has_permission
from ipt.core.states import STATES, state_name
from ipt.services.company_service import CompanyInput, ValidationError
from ipt.ui.helpers import confirm, error, fill_table, make_table, muted, selected_id, title
from ipt.ui.pages.base import BasePage


class CompanyDialog(QDialog):
    def __init__(self, parent=None, company=None):
        super().__init__(parent)
        self.setWindowTitle("Edit company" if company else "Add company")
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit()
        self.gstin = QLineEdit(); self.gstin.setMaxLength(15); self.gstin.setPlaceholderText("Leave blank if unregistered")
        self.gstin_msg = QLabel()
        self.state = QComboBox()
        for code, st in STATES.items():
            self.state.addItem(f"{code} - {st.name}", code)
        self.address = QPlainTextEdit(); self.address.setFixedHeight(60)
        self.currency = QLineEdit("INR"); self.currency.setMaxLength(3)
        self.tally_name = QLineEdit(); self.tally_name.setPlaceholderText("Exact company name as shown in Tally")
        self.tally_version = QLineEdit(); self.tally_version.setPlaceholderText("Detected automatically in Phase 3")
        self.tally_host = QLineEdit("localhost")
        self.tally_port = QSpinBox(); self.tally_port.setRange(1, 65535); self.tally_port.setValue(9000)
        form.addRow("Company name *", self.name)
        form.addRow("GSTIN", self.gstin)
        form.addRow("", self.gstin_msg)
        form.addRow("State *", self.state)
        form.addRow("Address", self.address)
        form.addRow("Currency", self.currency)
        form.addRow("Tally company name", self.tally_name)
        form.addRow("Tally version", self.tally_version)
        form.addRow("Tally host", self.tally_host)
        form.addRow("Tally port", self.tally_port)
        lay.addLayout(form)
        self.err = QLabel(); self.err.setObjectName("ErrorText"); self.err.setWordWrap(True)
        lay.addWidget(self.err)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.gstin.textChanged.connect(self._gstin_changed)
        if company:
            self.name.setText(company.name)
            self.gstin.setText(company.gstin or "")
            self.state.setCurrentIndex(max(0, self.state.findData(company.state_code)))
            self.address.setPlainText(company.address)
            self.currency.setText(company.currency)
            self.tally_name.setText(company.tally_company_name)
            self.tally_version.setText(company.tally_version)
            self.tally_host.setText(company.tally_host)
            self.tally_port.setValue(company.tally_port)
        else:
            self.state.setCurrentIndex(max(0, self.state.findData("08")))

    def _gstin_changed(self, text: str):
        g = normalize(text)
        if not g:
            self.gstin_msg.setText(""); return
        res = validate_gstin(g)
        self.gstin_msg.setObjectName("OkText" if res.valid else "ErrorText")
        self.gstin_msg.setStyleSheet("color: %s" % ("#15803d" if res.valid else "#b91c1c"))
        self.gstin_msg.setText(res.message)
        if res.state_code and res.state_code in STATES:
            self.state.setCurrentIndex(self.state.findData(res.state_code))

    def data(self) -> CompanyInput:
        return CompanyInput(name=self.name.text(), gstin=self.gstin.text(), state_code=self.state.currentData(),
                            address=self.address.toPlainText(), currency=self.currency.text(),
                            tally_company_name=self.tally_name.text(), tally_version=self.tally_version.text(),
                            tally_host=self.tally_host.text(), tally_port=self.tally_port.value())


class FyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add financial year")
        lay = QVBoxLayout(self)
        form = QFormLayout()
        today = date.today()
        default_start = today.year if today.month >= 4 else today.year - 1
        self.year = QSpinBox(); self.year.setRange(2017, 2100); self.year.setValue(default_start)
        self.label = QLabel()
        self.books = QDateEdit(); self.books.setCalendarPopup(True); self.books.setDisplayFormat("dd-MM-yyyy")
        form.addRow("FY starting year", self.year)
        form.addRow("Financial year", self.label)
        form.addRow("Books beginning date", self.books)
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.year.valueChanged.connect(self._update)
        self._update(self.year.value())

    def _update(self, y: int):
        self.label.setText(f"{y}-{(y + 1) % 100:02d}  (01-04-{y} to 31-03-{y + 1})")
        self.books.setDate(QDate(y, 4, 1))

    def values(self) -> tuple[int, date]:
        d = self.books.date()
        return self.year.value(), date(d.year(), d.month(), d.day())


class CompaniesPage(BasePage):
    title_text = "Company Settings"
    companies_changed = Signal()

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("Companies & Financial Years"))
        self.layout_.addWidget(muted("Each company's suppliers, invoices, vouchers, GSTR-2B and reconciliation "
                                     "data are kept completely separate."))
        split = QSplitter()
        # companies
        left = QWidget(); ll = QVBoxLayout(left); ll.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.btn_add = QPushButton("Add company"); self.btn_add.setObjectName("Primary")
        self.btn_edit = QPushButton("Edit")
        self.btn_toggle = QPushButton("Enable / Disable")
        for b in (self.btn_add, self.btn_edit, self.btn_toggle):
            bar.addWidget(b)
        bar.addStretch(1)
        ll.addLayout(bar)
        self.table = make_table(["Company", "GSTIN", "State", "Tally company", "Port", "Status"])
        ll.addWidget(self.table)
        # FYs
        right = QWidget(); rl = QVBoxLayout(right); rl.setContentsMargins(0, 0, 0, 0)
        fbar = QHBoxLayout()
        self.btn_fy_add = QPushButton("Add financial year")
        self.btn_fy_lock = QPushButton("Lock / Unlock")
        fbar.addWidget(self.btn_fy_add); fbar.addWidget(self.btn_fy_lock); fbar.addStretch(1)
        rl.addLayout(fbar)
        self.fy_table = make_table(["FY", "From", "To", "Books from", "Locked"])
        rl.addWidget(self.fy_table)
        split.addWidget(left); split.addWidget(right)
        split.setSizes([700, 400])
        self.layout_.addWidget(split, 1)

        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_toggle.clicked.connect(self._toggle)
        self.btn_fy_add.clicked.connect(self._add_fy)
        self.btn_fy_lock.clicked.connect(self._lock_fy)
        self.table.itemSelectionChanged.connect(self._load_fys)
        self.table.doubleClicked.connect(lambda _: self._edit())

    def refresh(self) -> None:
        can = has_permission(self.s.ctx.user.role if self.s.ctx.user else None, "company.manage")
        for b in (self.btn_add, self.btn_edit, self.btn_toggle, self.btn_fy_add, self.btn_fy_lock):
            b.setEnabled(can)
        current = selected_id(self.table)
        cs = self.s.companies.list_companies()
        fill_table(self.table, [[c.name, c.gstin or "-", f"{c.state_code} {state_name(c.state_code)}",
                                 c.tally_company_name, c.tally_port, "Active" if c.is_active else "Disabled"]
                                for c in cs], [c.id for c in cs])
        target = current or self.s.ctx.company_id
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).data(Qt.UserRole) == target:
                self.table.selectRow(r)
                break
        self._load_fys()

    def _load_fys(self):
        cid = selected_id(self.table)
        fys = self.s.companies.list_fys(cid) if cid else []
        fill_table(self.fy_table, [[f.label, f.start_date.strftime("%d-%m-%Y"), f.end_date.strftime("%d-%m-%Y"),
                                    f.books_begin_date.strftime("%d-%m-%Y"), "Yes" if f.is_locked else "No"]
                                   for f in fys], [f.id for f in fys])

    def _run(self, fn) -> bool:
        try:
            fn()
            return True
        except (ValidationError, PermissionDenied) as e:
            error(self, str(e))
            return False

    def _add(self):
        dlg = CompanyDialog(self)
        while dlg.exec():
            if self._run(lambda: self.s.companies.create_company(dlg.data(), self.s.ctx.user)):
                self.refresh(); self.companies_changed.emit(); return

    def _edit(self):
        cid = selected_id(self.table)
        if not cid:
            error(self, "Select a company first"); return
        dlg = CompanyDialog(self, self.s.companies.get_company(cid))
        while dlg.exec():
            if self._run(lambda: self.s.companies.update_company(cid, dlg.data(), self.s.ctx.user)):
                self.refresh(); self.companies_changed.emit(); return

    def _toggle(self):
        cid = selected_id(self.table)
        if not cid:
            error(self, "Select a company first"); return
        c = self.s.companies.get_company(cid)
        verb = "disable" if c.is_active else "enable"
        if confirm(self, f"Do you want to {verb} '{c.name}'? Disabled companies are hidden from the switcher; "
                         f"no data is deleted."):
            if self._run(lambda: self.s.companies.set_company_active(cid, not c.is_active, self.s.ctx.user)):
                self.refresh(); self.companies_changed.emit()

    def _add_fy(self):
        cid = selected_id(self.table)
        if not cid:
            error(self, "Select a company first"); return
        dlg = FyDialog(self)
        if dlg.exec():
            year, books = dlg.values()
            if self._run(lambda: self.s.companies.create_fy(cid, year, self.s.ctx.user, books)):
                self._load_fys(); self.companies_changed.emit()

    def _lock_fy(self):
        fid = selected_id(self.fy_table)
        cid = selected_id(self.table)
        if not fid or not cid:
            error(self, "Select a financial year first"); return
        fy = next(f for f in self.s.companies.list_fys(cid) if f.id == fid)
        verb = "unlock" if fy.is_locked else "lock"
        if confirm(self, f"Do you want to {verb} FY {fy.label}? Locked years cannot be changed by imports."):
            if self._run(lambda: self.s.companies.set_fy_locked(fid, not fy.is_locked, self.s.ctx.user)):
                self._load_fys()
