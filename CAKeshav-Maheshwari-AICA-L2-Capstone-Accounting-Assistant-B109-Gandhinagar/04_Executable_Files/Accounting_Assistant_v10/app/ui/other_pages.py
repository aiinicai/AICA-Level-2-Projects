"""2B reconciliation and Rules & memory pages."""
from __future__ import annotations

from collections import Counter
from decimal import Decimal
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
                             QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QWidget)
from sqlalchemy import select

from ..db.models import Invoice as InvoiceRow, MappingRule, Vendor
from ..engine import gstr2b, tds as tds_mod
from .common import ChoiceDelegate, card, choice_item, page_layout
from .inbox import CompanyPicker

MATCH_COLOURS = {"matched": "#e3f5ea", "amount_mismatch": "#fff4dc", "not_in_2b": "#fde8e8",
                 "in_2b_not_booked": "#eef2fb"}


class ReconPage(QWidget):
    def __init__(self, st):
        super().__init__(objectName="page")
        self.st = st
        root = page_layout(self, "GSTR-2B reconciliation",
                           "Load the 2B JSON or Excel downloaded from the GST portal. Status is shown on each invoice; "
                           "posting is never blocked by it.")
        top = QHBoxLayout()
        self.picker = CompanyPicker(st)
        from .common import PeriodPicker
        self.period = PeriodPicker("gstr2b", "Invoices dated")
        self.period.setToolTip("Only invoices dated in this period are matched against the 2B file")
        top.addWidget(self.period)
        b = QPushButton("Load 2B file and match", objectName="primary")
        b.clicked.connect(self.run)
        self.summary = QLabel("", objectName="muted")
        self.picker.hide()                       # the company switcher lives in the top bar
        top.addWidget(b)
        top.addWidget(self.summary, 1)
        root.addLayout(top)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Status", "Supplier GSTIN", "Invoice no", "In app", "In 2B", "Note"])
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        root.addWidget(self.table, 1)

    def showEvent(self, e):
        self.picker.reload()
        super().showEvent(e)

    def run(self):
        c = self.st.company()
        if not c:
            return
        p, _ = QFileDialog.getOpenFileName(self, "GSTR-2B file", "", "GSTR-2B (*.json *.xlsx *.zip)")
        if not p:
            return
        try:
            path = Path(p)
            if path.suffix.lower() == ".zip":
                import tempfile
                import zipfile
                d = Path(tempfile.mkdtemp())
                zipfile.ZipFile(path).extractall(d)
                path = next(d.rglob("*.json"))
            recs = gstr2b.load(path)
        except Exception as e:
            QMessageBox.warning(self, "2B", f"Could not read the file: {e}")
            return
        s = self.st.session
        per = self.period.period()
        rows = [r for r in s.scalars(select(InvoiceRow).where(InvoiceRow.company_id == c.id))
                if not (r.extraction or {}).get("invoice_date") or per.contains((r.extraction or {})["invoice_date"])]
        books = []
        for r in rows:
            e = r.extraction or {}
            if e.get("supplier_gstin") and e.get("invoice_no"):
                tax = sum(Decimal(str(e.get(k, 0) or 0)) for k in ("igst_total", "cgst_total", "sgst_total",
                                                                   "cess_total"))
                books.append({"id": r.id, "supplier_gstin": e["supplier_gstin"], "invoice_no": e["invoice_no"],
                              "grand_total": str(e.get("grand_total", 0) or 0), "tax_total": str(tax)})
        matches = gstr2b.reconcile(books, recs)
        by_id = {r.id: r for r in rows}
        for m in matches:
            if m.invoice_id in by_id:
                by_id[m.invoice_id].status_2b = m.status
        s.commit()
        self.table.setRowCount(len(matches))
        for i, m in enumerate(sorted(matches, key=lambda m: m.status)):
            vals = [m.status.replace("_", " "), m.gstin, m.inv_no,
                    f"{m.book_total:,.2f}" if m.book_total is not None else "",
                    f"{m.b2b_total:,.2f}" if m.b2b_total is not None else "", m.note]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setBackground(QColor(MATCH_COLOURS.get(m.status, "#fff")))
                self.table.setItem(i, j, it)
        cnt = Counter(m.status for m in matches)
        self.summary.setText(f"{len(recs)} records in 2B  ·  matched {cnt['matched']}  ·  mismatch "
                             f"{cnt['amount_mismatch']}  ·  not in 2B {cnt['not_in_2b']}  ·  in 2B, not in app "
                             f"{cnt['in_2b_not_booked']}")


class RulesPage(QWidget):
    def __init__(self, st):
        super().__init__(objectName="page")
        self.st = st
        root = page_layout(self, "Rules & memory", "What the app has learned for each company. Pausing a rule stops "
                                                   "it being suggested; vendor settings drive TDS and RCM.")
        top = QHBoxLayout()
        self.picker = CompanyPicker(st)
        self.picker.hide()                       # the company switcher lives in the top bar
        top.addStretch(1)
        root.addLayout(top)
        tabs = QTabWidget()
        # rules
        w1 = QWidget()
        from PyQt6.QtWidgets import QVBoxLayout
        l1 = QVBoxLayout(w1)
        self.rules = QTableWidget(0, 7)
        self.rules.setHorizontalHeaderLabels(["Vendor", "HSN", "Ledger / item", "Approvals", "Overrides", "Source",
                                              "Active"])
        self.rules.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.rules.verticalHeader().setVisible(False)
        self.rules.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rules.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        br = QHBoxLayout()
        for txt, fn in (("Pause / resume", self.toggle), ("Delete", self.delete)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            br.addWidget(b)
        br.addStretch(1)
        l1.addWidget(self.rules)
        l1.addLayout(br)
        tabs.addTab(w1, "Ledger rules")
        # vendors
        w2 = QWidget()
        l2 = QVBoxLayout(w2)
        self.vendors = QTableWidget(0, 9)
        self.vendors.setHorizontalHeaderLabels(["Vendor key", "Name", "Party ledger", "TDS section", "RCM",
                                                "Credit days", "Book as", "TDS learned", "Offline reading"])
        self.vendors.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.vendors.verticalHeader().setVisible(False)
        from ..engine import tds_map
        self.SEC_CHOICES = [("", "—")] + [(k, k) for k in tds_mod.DEFAULT_SECTIONS] + \
            [(k, k) for k in tds_map.SEED if k not in tds_mod.DEFAULT_SECTIONS]
        self.RCM_CHOICES = [("No", "No"), ("Yes", "Yes")]
        self.STYLE_CHOICES = [("", "Company default"), ("journal", "Journal"), ("purchase_accounting", "Purchase"),
                              ("purchase_item", "Purchase (items)")]
        for col, ch in ((3, self.SEC_CHOICES), (4, self.RCM_CHOICES), (6, self.STYLE_CHOICES)):
            self.vendors.setItemDelegateForColumn(col, ChoiceDelegate(self.vendors, ch))
        b_save = QPushButton("Save vendor settings", objectName="primary")
        b_save.clicked.connect(self.save_vendors)
        l2.addWidget(self.vendors)
        l2.addWidget(b_save, alignment=Qt.AlignmentFlag.AlignRight)
        tabs.addTab(w2, "Vendors")
        root.addWidget(tabs, 1)
        st.on_company_change(self.reload)

    def showEvent(self, e):
        self.picker.reload()
        self.reload()
        super().showEvent(e)

    def reload(self):
        c = self.st.company()
        if not c:
            return
        s = self.st.session
        names = {v.vendor_key: (v.names or [v.party_ledger or ""])[0] for v in
                 s.scalars(select(Vendor).where(Vendor.company_id == c.id))}
        self._rules = list(s.scalars(select(MappingRule).where(MappingRule.company_id == c.id,
                                                               MappingRule.source != "deleted")
                                     .order_by(MappingRule.hits.desc())))
        self.rules.setRowCount(len(self._rules))
        for i, r in enumerate(self._rules):
            vals = [names.get(r.vendor_key) or r.vendor_key, r.hsn, r.target_name, str(r.hits), str(r.overrides),
                    "Tally history" if r.source == "warm_start" else "approvals", "yes" if r.active else "paused"]
            for j, v in enumerate(vals):
                self.rules.setItem(i, j, QTableWidgetItem(v))
        self._vendors = list(s.scalars(select(Vendor).where(Vendor.company_id == c.id)))
        from ..engine import layouts
        offline = layouts.offline_ready(s, c.id)
        self.vendors.setRowCount(len(self._vendors))
        for i, v in enumerate(self._vendors):
            for j, val in enumerate([v.vendor_key, ", ".join(v.names or []), v.party_ledger]):
                it = QTableWidgetItem(val)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.vendors.setItem(i, j, it)
            self.vendors.setItem(i, 3, choice_item(self.SEC_CHOICES, v.tds_section or ""))
            self.vendors.setItem(i, 4, choice_item(self.RCM_CHOICES, "Yes" if v.rcm else "No"))
            self.vendors.setItem(i, 5, QTableWidgetItem(str(v.credit_days or "")))
            self.vendors.setItem(i, 6, choice_item(self.STYLE_CHOICES, v.voucher_style or ""))
            tl = QTableWidgetItem(f"{v.tds_rate:g}% → {v.tds_ledger}" if v.tds_ledger and v.tds_rate else "")
            tl.setFlags(tl.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.vendors.setItem(i, 7, tl)
            smp, ok = offline.get(v.vendor_key, (0, 0))
            off = QTableWidgetItem(f"✓ read offline {ok}×" if ok else f"✓ learned ({smp})" if smp else "")
            off.setToolTip("Layout learned from approved invoices: next ones are read without Gemini when every "
                           "check passes" if smp else "Not learned yet - post one invoice from this supplier")
            off.setFlags(off.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.vendors.setItem(i, 8, off)

    def _selected(self) -> MappingRule | None:
        r = self.rules.currentRow()
        return self._rules[r] if 0 <= r < len(self._rules) else None

    def toggle(self):
        r = self._selected()
        if r:
            r.active = not r.active
            self.st.session.commit()
            self.reload()

    def delete(self):
        r = self._selected()
        if r and QMessageBox.question(self, "Delete rule", f"Delete the rule for '{r.target_name}'?") == \
                QMessageBox.StandardButton.Yes:
            r.active, r.source = False, "deleted"      # soft delete so it syncs to other PCs
            self.st.session.commit()
            self.reload()

    def save_vendors(self):
        for i, v in enumerate(self._vendors):
            v.tds_section = self.vendors.item(i, 3).data(Qt.ItemDataRole.UserRole) or ""
            v.rcm = self.vendors.item(i, 4).data(Qt.ItemDataRole.UserRole) == "Yes"
            txt = (self.vendors.item(i, 5).text() if self.vendors.item(i, 5) else "").strip()
            v.credit_days = int(txt) if txt.isdigit() else 0
            v.voucher_style = self.vendors.item(i, 6).data(Qt.ItemDataRole.UserRole) or ""
        self.st.session.commit()
        QMessageBox.information(self, "Vendors", "Saved.")
