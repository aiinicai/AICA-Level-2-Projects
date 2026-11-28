"""Master Mapping: approve which Tally ledgers / stock items an invoice uses."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPushButton, QSplitter, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from ipt.core.permissions import has_permission
from ipt.services.tally.mapping import ENTITY_LABELS
from ipt.services.tally.client import TallyError
from ipt.ui.helpers import confirm, error, fill_table, make_table, muted, selected_id, title
from ipt.ui.pages.base import BasePage


class MappingPage(BasePage):
    title_text = "Master Mapping"

    def __init__(self, services, parent=None):
        super().__init__(services, parent)
        self.layout_.addWidget(title("Master Mapping"))
        self.layout_.addWidget(muted("Pick the Tally ledger / stock item for each part of an approved invoice. "
                                     "Approved choices are remembered for the next invoice. Green = strong match.\n"
                                     "Bills you do not enter item-wise (e.g. electrical repairs): choose a ledger in "
                                     "'Book this supplier to a ledger' – that supplier's bills are then imported "
                                     "without items, debited to that ledger."))
        tabs = QTabWidget()
        # ---------------- per invoice
        w = QWidget()
        lay = QVBoxLayout(w)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Mode"))
        self.mode = QComboBox()
        self.mode.addItem("Auto (per supplier)", "auto")
        self.mode.addItem("Inventory (item invoice)", "inventory")
        self.mode.addItem("Accounting (ledgers only)", "accounting")
        bar.addWidget(self.mode)
        bar.addStretch(1)
        lay.addLayout(bar)
        split = QSplitter()
        self.invoices = make_table(["Supplier", "Invoice no", "Date", "Total", "Mapping"])
        split.addWidget(self.invoices)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        self.grid = QTableWidget(0, 4)
        self.grid.setHorizontalHeaderLabels(["What", "From invoice", "Tally master", "Why suggested"])
        self.grid.verticalHeader().setVisible(False)
        self.grid.horizontalHeader().setStretchLastSection(True)
        rl.addWidget(self.grid, 1)
        b2 = QHBoxLayout()
        self.btn_save = QPushButton("Approve mapping")
        self.btn_save.setObjectName("Primary")
        b2.addWidget(self.btn_save)
        self.btn_create = QPushButton("Create in Tally…")
        self.btn_create.setToolTip("Select a 'Party' or 'Stock item' row whose master is not in Tally yet")
        b2.addWidget(self.btn_create)
        b2.addStretch(1)
        self.msg = muted("")
        rl.addLayout(b2)
        rl.addWidget(self.msg)
        split.addWidget(right)
        split.setSizes([450, 850])
        lay.addWidget(split, 1)
        tabs.addTab(w, "Approved invoices")
        # ---------------- memory
        m = QWidget()
        ml = QVBoxLayout(m)
        self.rules = make_table(["What", "From", "Tally master", "Used", "Approved by"])
        ml.addWidget(self.rules, 1)
        b3 = QHBoxLayout()
        self.btn_del = QPushButton("Delete selected rule")
        b3.addWidget(self.btn_del)
        b3.addStretch(1)
        ml.addLayout(b3)
        tabs.addTab(m, "Mapping memory")
        self.layout_.addWidget(tabs, 1)
        self.invoices.itemSelectionChanged.connect(self._load_lines)
        self.mode.currentIndexChanged.connect(lambda _: self.refresh())
        self.btn_save.clicked.connect(self._save)
        self.btn_create.clicked.connect(self._create)
        self.btn_del.clicked.connect(self._delete_rule)

    def refresh(self):
        role = self.s.ctx.user.role if self.s.ctx.user else None
        can = has_permission(role, "mapping.edit")
        self.btn_save.setEnabled(can)
        self.btn_del.setEnabled(can)
        self.btn_create.setEnabled(has_permission(role, "tally.import"))
        invs = self.s.invoices.list_invoices("approved")
        rows = []
        for i in invs:
            _, missing = self.s.mapping.resolved(i.id, self.mode.currentData())
            rows.append([i.supplier_name, i.invoice_no, i.invoice_date.strftime("%d-%m-%Y") if i.invoice_date else "",
                         f"{i.invoice_total or ''}", "Complete" if not missing else f"{len(missing)} to map"])
        fill_table(self.invoices, rows, [i.id for i in invs])
        rules = self.s.mapping.rules()
        fill_table(self.rules, [[ENTITY_LABELS.get(r.entity, r.entity), r.source_key, r.tally_name, r.times_used,
                                 r.approved_by] for r in rules], [r.id for r in rules])
        if not self.s.tally.masters("ledger"):
            self.msg.setText("Tally masters are not synced yet – open Tally Integration and click Sync masters.")
        self._load_lines()

    def _load_lines(self):
        iid = selected_id(self.invoices)
        self.grid.setRowCount(0)
        self._lines = self.s.mapping.lines_for(iid, self.mode.currentData()) if iid else []
        for r, ln in enumerate(self._lines):
            self.grid.insertRow(r)
            self.grid.setItem(r, 0, QTableWidgetItem(ENTITY_LABELS[ln.entity]))
            self.grid.setItem(r, 1, QTableWidgetItem(ln.source_label))
            cb = QComboBox()
            cb.setEditable(True)
            cb.addItem("")
            names = self.s.mapping.master_names(ln.entity)
            for c in ln.candidates:
                cb.addItem(f"{c.name}", c.name)
            cb.insertSeparator(cb.count())
            for n in names:
                cb.addItem(n, n)
            choice = ln.approved or (ln.best.name if ln.best and ln.best.score >= 70 else "")
            cb.setCurrentText(choice)
            colour = "#dcfce7" if ln.approved else ("#fef3c7" if choice else "#fee2e2")
            cb.setStyleSheet(f"background:{colour}")
            self.grid.setCellWidget(r, 2, cb)
            why = "Approved" if ln.approved else (f"{ln.best.reason} ({ln.best.score})" if ln.best else "No match – pick")
            self.grid.setItem(r, 3, QTableWidgetItem(why))
        self.grid.resizeColumnsToContents()

    def _save(self):
        if not self._lines:
            error(self, "Select an approved invoice first")
            return
        problems = []
        for r, ln in enumerate(self._lines):
            name = self.grid.cellWidget(r, 2).currentText().strip()
            if not name:
                if ln.entity not in ("round_off", "debit_ledger"):
                    problems.append(f"{ENTITY_LABELS[ln.entity]}: not chosen")
                continue
            try:
                self.s.mapping.approve(ln.entity, ln.source_key, name)
            except ValueError as e:
                problems.append(str(e))
        self.msg.setText("Mapping saved." if not problems else "Saved, except: " + "; ".join(problems))
        sel = selected_id(self.invoices)
        self.refresh()
        for r in range(self.invoices.rowCount()):
            if self.invoices.item(r, 0).data(Qt.UserRole) == sel:
                self.invoices.selectRow(r)

    def _delete_rule(self):
        rid = selected_id(self.rules)
        if rid and confirm(self, "Delete this remembered mapping?"):
            self.s.mapping.delete_rule(rid)
            self.refresh()

    def _create(self):
        row = self.grid.currentRow()
        if row < 0 or row >= len(self._lines) or self._lines[row].entity not in ("party", "stock_item"):
            error(self, "Select the 'Party' or 'Stock item' row that needs a new Tally master")
            return
        ln = self._lines[row]
        inv = self.s.invoices.get(selected_id(self.invoices))
        dlg = QDialog(self)
        dlg.setWindowTitle("Create in Tally")
        f = QFormLayout(dlg)
        name = QLineEdit()
        f.addRow("Name", name)
        if ln.entity == "party":
            name.setText((inv.supplier_name or "").strip())
            gstin = QLineEdit(inv.supplier_gstin or "")
            f.addRow("GSTIN", gstin)
            f.addRow(muted("Created under Sundry Creditors, GST Regular, state from the GSTIN, bill-wise on."))
        else:
            from ipt.services.tally.mapping import norm_desc
            item = next((it for it in inv.items if norm_desc(it.description) == ln.source_key),
                        inv.items[0] if inv.items else None)
            name.setText(" ".join((item.description or "").split()).title() if item else "")
            unit = QComboBox()
            unit.setEditable(True)
            units = [m.name for m in self.s.tally.masters("unit")]
            unit.addItems(units)
            if item and item.unit:
                unit.setCurrentText(next((u for u in units if u.lower() == item.unit.lower()), item.unit))
            hsn = QLineEdit(item.hsn_sac if item and item.hsn_sac else "")
            rate = QDoubleSpinBox()
            rate.setRange(0, 40)
            rate.setDecimals(2)
            rate.setSuffix(" %")
            if inv.taxable_total:
                tax = (inv.cgst or 0) + (inv.sgst or 0) + (inv.igst or 0)
                guess = round(float(tax) / float(inv.taxable_total) * 100 * 4) / 4
                rate.setValue(min((0, 0.25, 1.5, 3, 5, 12, 18, 28, 40), key=lambda r: abs(r - guess)))
            f.addRow("Unit", unit)
            f.addRow("HSN", hsn)
            f.addRow("GST rate", rate)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec() != QDialog.Accepted:
            return
        c = self.s.companies.get_company(self.s.ctx.company_id)
        what = "supplier ledger" if ln.entity == "party" else "stock item"
        if QMessageBox.question(self, "Create in Tally", f"Create {what} '{name.text().strip()}' in Tally company "
                                f"'{c.tally_company_name}'?\n\nThis writes to your Tally books.",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            if ln.entity == "party":
                made = self.s.tally.create_master("ledger", name.text(), gstin=gstin.text())
            else:
                from decimal import Decimal
                made = self.s.tally.create_master("stock_item", name.text(), unit=unit.currentText().strip(),
                                                  hsn=hsn.text(), gst_rate=Decimal(str(rate.value())))
        except (TallyError, Exception) as e:      # noqa: BLE001 - shown to the user
            error(self, str(e))
            return
        self.s.mapping.approve(ln.entity, ln.source_key, made)
        self.msg.setText(f"Created '{made}' in Tally (checked by reading it back) and chose it for this invoice.")
        self._load_lines()
