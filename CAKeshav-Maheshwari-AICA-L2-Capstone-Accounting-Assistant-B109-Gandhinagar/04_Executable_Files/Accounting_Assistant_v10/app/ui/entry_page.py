"""New entry: every Tally voucher type typed in directly (Payment, Receipt, Contra, Sales, Purchase, Journal,
Debit Note, Credit Note). Tally keys work (F4-F9, Alt+F5/F6, Ctrl+A to accept), the cash/bank side is restricted
the way Tally restricts it, GST is split automatically and bills can be settled bill-wise."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout,
                             QHeaderView, QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
                             QSizePolicy, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..db.models import Company, RecurringEntry
from ..engine import entry, recurring
from ..engine.voucher import VLine, Voucher
from ..extract.parser import parse_date
from . import theme
from .bills_dialog import BillsDialog
from .common import LedgerCombo, VoucherGrid, ask_lock_reason, dec, fmt_inr, page_layout, run_bg, tone
from .ledger_dialog import LedgerDialog

GST_RATES = ["0", "0.1", "0.25", "3", "5", "12", "18", "28", "40"]
LABELS = {
    "Payment": ("Paid from", "Paid to"), "Receipt": ("Received in", "Received from"),
    "Contra": ("From (withdrawn)", "To (deposited)"),
}


class _EnterMovesOn(QObject):
    """Tally habit: Enter moves to the next field."""

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.ShortcutOverride and ev.key() == Qt.Key.Key_A and \
                ev.modifiers() == Qt.KeyboardModifier.ControlModifier:
            ev.ignore()                     # let Ctrl+A reach the "Accept & post" shortcut, as in Tally
            return True
        if ev.type() == QEvent.Type.KeyPress and ev.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) \
                and not ev.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier):
            w = obj.parentWidget() if isinstance(obj.parentWidget(), QComboBox) else obj
            if isinstance(w, QComboBox) and w.view().isVisible():
                return False
            w.focusNextChild()
            return True
        return False


def _fmt_date(d: str) -> str:
    return f"{d[6:8]}-{d[4:6]}-{d[:4]}" if len(d) == 8 else d


class EntryPage(QWidget):
    def __init__(self, st):
        super().__init__(objectName="page")
        self.st = st
        self.company: Company | None = None
        self.m = None
        self.base = "Payment"
        self.bills: list = []
        self._enter = _EnterMovesOn(self)
        root = page_layout(self, "New entry", "Type an entry the way you would in Tally - the app checks it, "
                                              "splits GST, settles bills and posts it.")
        seg = QWidget(objectName="segbar")
        sl = QHBoxLayout(seg)
        sl.setContentsMargins(3, 3, 3, 3)
        sl.setSpacing(2)
        self.type_btns = {}
        grp = QButtonGroup(self)
        for base, key, _side in entry.VOUCHER_TYPES:
            b = QPushButton(f"{base}  {key}", objectName="seg", checkable=True)
            b.setMinimumWidth(92)
            b.clicked.connect(lambda _=False, x=base: self.set_type(x))
            grp.addButton(b)
            sl.addWidget(b)
            self.type_btns[base] = b
        tr = QHBoxLayout()
        tr.addWidget(seg)
        tr.addStretch(1)
        root.addLayout(tr)

        split = QSplitter(Qt.Orientation.Horizontal)
        # ---- form
        left = QFrame(objectName="card")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(18, 14, 18, 14)
        head = QHBoxLayout()
        self.title = QLabel("", objectName="h2")
        head.addWidget(self.title)
        head.addStretch(1)
        self.vtype = QComboBox()
        self.vtype.setMinimumContentsLength(12)
        self.vtype.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        head.addWidget(QLabel("Voucher type", objectName="muted"))
        head.addWidget(self.vtype)
        ll.addLayout(head)
        scroll = QScrollArea(widgetResizable=True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.form_host = QWidget(objectName="formhost")
        self.form_host.setStyleSheet(f"QWidget#formhost {{ background: {theme.SURFACE}; }}")
        self.form_host.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.form_lay = QVBoxLayout(self.form_host)
        self.form_lay.setContentsMargins(0, 6, 6, 0)
        scroll.setWidget(self.form_host)
        ll.addWidget(scroll, 1)
        split.addWidget(left)

        # ---- preview
        right = QFrame(objectName="card")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(18, 14, 18, 14)
        rh = QHBoxLayout()
        rh.addWidget(QLabel("Entry that will go to Tally", objectName="h2"))
        rh.addStretch(1)
        self.balance_lbl = QLabel("", objectName="muted")
        rh.addWidget(self.balance_lbl)
        rl.addLayout(rh)
        self.preview = QTableWidget(0, 3)
        self.preview.setHorizontalHeaderLabels(["Ledger", "Dr", "Cr"])
        self.preview.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.preview.setColumnWidth(1, 110)
        self.preview.setColumnWidth(2, 110)
        self.preview.verticalHeader().setVisible(False)
        self.preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        rl.addWidget(self.preview, 1)
        self.problems = QLabel("", wordWrap=True)
        rl.addWidget(self.problems)
        br = QHBoxLayout()
        self.b_recurring = QPushButton("Recurring…")
        self.b_recurring.setToolTip("Rent, salary, AMC, EMI: post this every month/quarter with a reminder")
        self.b_recurring.clicked.connect(self.save_recurring)
        self.b_new_ledger = QPushButton("+ Ledger")
        self.b_new_ledger.setToolTip("Create a ledger in Tally (Alt+C)")
        self.b_new_ledger.clicked.connect(self.create_ledger)
        self.b_clear = QPushButton("Clear")
        self.b_clear.clicked.connect(lambda: self.set_type(self.base, keep=False))
        self.b_post = QPushButton("Accept && post", objectName="primary")
        self.b_post.setToolTip("Ctrl+A (or Ctrl+Enter), like Tally")
        self.b_post.setMinimumHeight(36)
        self.b_post.clicked.connect(self.post)
        for b in (self.b_recurring, self.b_new_ledger, self.b_clear):
            br.addWidget(b)
        br.addStretch(1)
        br.addWidget(self.b_post)
        rl.addLayout(br)
        split.addWidget(right)
        split.setSizes([620, 460])
        split.setChildrenCollapsible(False)
        root.addWidget(split, 1)

        self._timer = QTimer(self, singleShot=True, interval=150)
        self._timer.timeout.connect(self.refresh_preview)
        # F4-F9 / Alt+F5 / Alt+F6 are window-wide (MainWindow.new_entry), so they work from any page
        for k in ("Ctrl+A", "Ctrl+Return"):
            sc = QShortcut(QKeySequence(k), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(self.post)
        sc = QShortcut(QKeySequence("Alt+C"), self)
        sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc.activated.connect(self.create_ledger)
        st.on_company_change(self.reload)

    def showEvent(self, e):
        self.reload()
        super().showEvent(e)

    # ------------------------------------------------------------------ building the form
    def reload(self):
        c = self.st.company()
        self.company = c
        self.m = self.st.masters(c) if c else None
        self.set_type(self.base, keep=False)

    def _clear_form(self):
        def wipe(lay):
            while lay.count():
                it = lay.takeAt(0)
                if it.widget():
                    it.widget().deleteLater()
                elif it.layout():
                    wipe(it.layout())
        wipe(self.form_lay)

    def _watch(self, w):
        if isinstance(w, QComboBox):
            w.currentTextChanged.connect(self._changed)
            if w.lineEdit():
                w.lineEdit().installEventFilter(self._enter)
        elif isinstance(w, QLineEdit):
            w.textChanged.connect(self._changed)
            w.installEventFilter(self._enter)
        return w

    def _changed(self, *_):
        self._timer.start()

    def set_type(self, base: str, keep: bool = True):
        old_date = self.date.text() if keep and hasattr(self, "date") else ""
        self.base = base
        self.bills = []
        self.type_btns[base].setChecked(True)
        key = next(k for b, k, _s in entry.VOUCHER_TYPES if b == base)
        self.title.setText(f"{base}  ·  {key}")
        self._clear_form()
        for name in ("cash", "party", "amount", "ref", "ref_date", "items", "grid", "b_bills", "bills_lbl",
                     "party_info", "chk_round", "chk_items", "date"):
            self.__dict__.pop(name, None)
        if not self.company or not self.m:
            self.form_lay.addWidget(QLabel("Pick a company in the top bar (sync it first if the list is empty).",
                                           objectName="muted"))
            self.setEnabled(True)
            return
        m, c = self.m, self.company
        self.vtype.blockSignals(True)
        self.vtype.clear()
        self.vtype.addItems(entry.voucher_type_names(m, base))
        self.vtype.blockSignals(False)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setVerticalSpacing(10)
        self.date = self._watch(QLineEdit(old_date or date.today().strftime("%d-%m-%Y")))
        self.date.setMaximumWidth(130)
        self.date.setToolTip("dd-mm-yyyy")
        form.addRow("Date", self.date)
        cb = entry.cash_bank_ledgers(m, c)
        others = sorted(n for n in m.ledgers if n not in set(cb))
        self.narration = QLineEdit()
        self.narration.setPlaceholderText("Narration")
        if base in ("Payment", "Receipt", "Contra"):
            a, b = LABELS[base]
            self.cash = self._watch(LedgerCombo(cb, entry.last_cash_bank(self.st.session, c, m, base)))
            self.cash.setToolTip("Only bank, cash, CC/OD and credit-card ledgers - like Tally")
            if base == "Contra":
                self.party = self._watch(LedgerCombo(cb, ""))
            else:
                self.party = self._watch(LedgerCombo(others, ""))
            self.amount = self._watch(QLineEdit())
            self.amount.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.amount.setMaximumWidth(180)
            self.ref = self._watch(QLineEdit())
            self.ref.setPlaceholderText("Cheque / UTR (optional)")
            if base == "Contra":
                form.addRow(a, self.cash)
                form.addRow(b, self.party)
            else:
                form.addRow(b, self.party)
                form.addRow(a, self.cash)
            form.addRow("Amount", self.amount)
            form.addRow("Reference", self.ref)
            if base != "Contra":
                bl = QHBoxLayout()
                self.b_bills = QPushButton("Settle bills…")
                self.b_bills.setToolTip("Pick the bills this settles (Agst Ref). Left over goes On Account.")
                self.b_bills.clicked.connect(self.pick_bills)
                self.bills_lbl = QLabel("", objectName="muted", wordWrap=True)
                bl.addWidget(self.b_bills)
                bl.addWidget(self.bills_lbl, 1)
                form.addRow("Bills", bl)
                self.party.currentTextChanged.connect(self._party_changed)
            self.form_lay.addLayout(form)
        elif base == "Journal":
            self.form_lay.addLayout(form)
            self.grid = VoucherGrid()
            self.grid.table.setMinimumHeight(260)
            self.grid.set_voucher(Voucher("Journal", "", [VLine("", Decimal(0), True, "other", "", "amber"),
                                                         VLine("", Decimal(0), False, "other", "", "amber")]),
                                  sorted(m.ledgers))
            self.grid.changed.connect(self._changed)
            self.form_lay.addWidget(self.grid, 1)
        else:
            parties = m.names_under("Sundry Debtors", "Sundry Creditors") + \
                [n for n in others if n not in set(m.names_under("Sundry Debtors", "Sundry Creditors"))]
            self.party = self._watch(LedgerCombo(parties, ""))
            self.party.currentTextChanged.connect(self._party_changed)
            self.ref = self._watch(QLineEdit())
            self.ref.setPlaceholderText({"Sales": "Invoice no", "Purchase": "Supplier invoice no",
                                         "Debit Note": "Debit note no", "Credit Note": "Credit note no"}[base])
            self.ref_date = self._watch(QLineEdit())
            self.ref_date.setPlaceholderText("dd-mm-yyyy")
            self.ref_date.setMaximumWidth(130)
            form.addRow("Party", self.party)
            form.addRow("Reference", self.ref)
            form.addRow("Reference date", self.ref_date)
            self.party_info = QLabel("", objectName="muted", wordWrap=True)
            form.addRow("", self.party_info)
            self.form_lay.addLayout(form)
            lh = QHBoxLayout()
            lh.addWidget(QLabel("Lines", objectName="section"))
            lh.addStretch(1)
            self.chk_items = QCheckBox("Stock items (qty × rate)")
            self.chk_items.setChecked(bool((self.company.settings or {}).get(f"item_mode_{base}")))
            self.chk_items.toggled.connect(self._item_mode)
            lh.addWidget(self.chk_items)
            self.form_lay.addLayout(lh)
            self.items = QTableWidget(0, 6)
            self.items.setHorizontalHeaderLabels(["Ledger", "Stock item (optional)", "Qty", "Rate", "Taxable", "GST %"])
            h = self.items.horizontalHeader()
            h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            for col, w in ((2, 60), (3, 80), (4, 100), (5, 70)):
                self.items.setColumnWidth(col, w)
            self.items.verticalHeader().setVisible(False)
            self.items.verticalHeader().setDefaultSectionSize(34)
            self.items.setMinimumHeight(170)
            self.items.itemChanged.connect(self._item_changed)
            self.form_lay.addWidget(self.items, 1)
            ib = QHBoxLayout()
            add, rem = QPushButton("+ Line"), QPushButton("− Line")
            add.clicked.connect(lambda: self._add_item())
            rem.clicked.connect(self._remove_item)
            self.chk_round = QCheckBox("Round off to the rupee")
            self.chk_round.setChecked(True)
            self.chk_round.toggled.connect(self._changed)
            ib.addWidget(add)
            ib.addWidget(rem)
            ib.addStretch(1)
            ib.addWidget(self.chk_round)
            self.form_lay.addLayout(ib)
            self._add_item()
            self._item_mode(self.chk_items.isChecked(), save=False)
        self.form_lay.addWidget(QLabel("Narration", objectName="section"))
        self.form_lay.addWidget(self._watch(self.narration))
        self.form_lay.addStretch(1)
        self.refresh_preview()
        QTimer.singleShot(0, lambda: (self.party if hasattr(self, "party") and base != "Journal" else
                                      self.date).setFocus())

    # ---- items (sales / purchase / notes)
    def _item_ledgers(self) -> list[str]:
        m = self.m
        if self.base in ("Sales", "Credit Note"):
            pool = m.names_under("Sales Accounts", "Direct Incomes", "Indirect Incomes")
        else:
            pool = m.names_under("Purchase Accounts", "Direct Expenses", "Indirect Expenses", "Fixed Assets")
        return pool or sorted(m.ledgers)

    def _add_item(self):
        r = self.items.rowCount()
        self.items.insertRow(r)
        pool = self._item_ledgers()
        led = self._watch(LedgerCombo(pool, self._last_item_ledger()))
        itm = self._watch(LedgerCombo(sorted(self.m.stock_items), ""))
        rate = QComboBox()
        rate.setEditable(True)
        rate.addItems(GST_RATES)
        rate.setCurrentText("18")
        self._watch(rate)
        self.items.setCellWidget(r, 0, led)
        self.items.setCellWidget(r, 1, itm)
        self.items.setCellWidget(r, 5, rate)
        self.items.blockSignals(True)
        for col in (2, 3, 4):
            it = QTableWidgetItem("")
            it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.items.setItem(r, col, it)
        self.items.blockSignals(False)

    def _item_mode(self, on: bool, save: bool = True):
        for col in (1, 2, 3):
            self.items.setColumnHidden(col, not on)
        if save and self.company:
            cfg = dict(self.company.settings or {})
            cfg[f"item_mode_{self.base}"] = on
            self.company.settings = cfg
            self.st.session.commit()
        self._changed()

    def _last_item_ledger(self) -> str:
        if self.items.rowCount() > 1:
            w = self.items.cellWidget(self.items.rowCount() - 2, 0)
            return w.currentText() if w else ""
        last = (self.company.settings or {}).get("last_item_ledger", {}).get(self.base, "")
        pool = self._item_ledgers()
        return last if last in pool else (pool[0] if len(pool) == 1 else "")

    def _remove_item(self):
        r = self.items.currentRow()
        if r < 0:
            r = self.items.rowCount() - 1
        if self.items.rowCount() > 1 and r >= 0:
            self.items.removeRow(r)
            self._changed()

    def _item_changed(self, it):
        r, col = it.row(), it.column()
        if col in (2, 3):                       # qty x rate -> taxable
            q, rt = dec(self.items.item(r, 2).text()), dec(self.items.item(r, 3).text())
            if q and rt:
                self.items.blockSignals(True)
                self.items.item(r, 4).setText(f"{(q * rt).quantize(Decimal('0.01'))}")
                self.items.blockSignals(False)
        self._changed()

    def _party_changed(self, *_):
        self.bills = []
        if hasattr(self, "bills_lbl"):
            self.bills_lbl.setText("")
        if hasattr(self, "party_info") and self.m:
            p = self.party.currentText().strip()
            d = self.m.ledgers.get(p, {})
            st = entry.party_state(self.m, p)
            ours = (self.company.gstin or "")[:2]
            self.party_info.setText(("" if not d else
                                     f"{d.get('_group', '')}" + (f" · GSTIN {d.get('_gstin')}" if d.get("_gstin") else "")
                                     + (" · inter-state: IGST" if st and ours and st != ours else
                                        " · intra-state: CGST + SGST" if st else "")))
        if hasattr(self, "b_bills"):
            bw = self.m.ledgers.get(self.party.currentText().strip(), {}).get("ISBILLWISEON", "").lower() == "yes"
            self.b_bills.setEnabled(bw)
            self.b_bills.setToolTip("" if bw else "This ledger is not bill-wise in Tally")

    # ------------------------------------------------------------------ voucher
    def form(self) -> entry.EntryForm:
        b = self.base
        f = entry.EntryForm(b, self.vtype.currentText().strip() or b,
                            parse_date(self.date.text()) or date.today().strftime("%Y%m%d"),
                            narration=self.narration.text().strip())
        if b in ("Payment", "Receipt", "Contra"):
            f.cash_bank = self.cash.currentText().strip()
            f.amount = dec(self.amount.text())
            if b == "Contra":
                f.contra_to = self.party.currentText().strip()
            else:
                f.party = self.party.currentText().strip()
                f.bills = list(self.bills)
            ref = self.ref.text().strip()
            if ref and ref not in f.narration:
                f.narration = (f.narration + f" (Ref {ref})").strip()
        elif b == "Journal":
            f.journal_lines = self.grid.lines()
        else:
            f.party = self.party.currentText().strip()
            f.reference = self.ref.text().strip()
            f.reference_date = parse_date(self.ref_date.text())
            for r in range(self.items.rowCount()):
                taxable = dec(self.items.item(r, 4).text())
                led = self.items.cellWidget(r, 0).currentText().strip()
                if not taxable and not led:
                    continue
                f.items.append(entry.ItemLine(led, taxable, dec(self.items.cellWidget(r, 5).currentText()),
                                              self.items.cellWidget(r, 1).currentText().strip(),
                                              dec(self.items.item(r, 2).text()), dec(self.items.item(r, 3).text()),
                                              (self.m.stock_items.get(self.items.cellWidget(r, 1).currentText().strip(),
                                                                      {}).get("BASEUNITS") or "Nos")))
            if self.chk_round.isChecked():
                f.round_off_ledger = (self.company.settings or {}).get("round_off_ledger") or \
                    self.m.find(r"round", None)
            if not f.narration and f.reference:
                f.narration = f"Being {b.lower()} vide {f.reference}"
        return f

    def voucher(self) -> Voucher:
        return entry.build(self.form(), self.m, self.company)

    def _issues(self, v: Voucher) -> list[str]:
        out = v.problems(set(self.m.ledgers), set(self.m.stock_items))
        out += entry.check_restrictions(v, self.m, self.company)
        if self.base in ("Payment", "Receipt") and v.lines and v.lines[0].ledger == v.lines[-1].ledger:
            out.append("Party and bank are the same ledger")
        return out

    def refresh_preview(self):
        if not self.company or not self.m or "date" not in self.__dict__:
            return
        try:
            v = self.voucher()
        except Exception as e:
            self.problems.setText(f"⚠ {e}")
            return
        rows = [(l.ledger or "—", l.amount, l.dr, l.note) for l in v.lines]
        for i in v.inventory:
            rows.append((f"{i.purchase_ledger}  ·  {i.stock_item} {i.qty.normalize():f} {i.uom}", i.amount, i.dr, ""))
        self.preview.setRowCount(len(rows))
        for r, (led, amt, dr, note) in enumerate(rows):
            cells = [led, fmt_inr(amt) if dr and amt else "", fmt_inr(amt) if not dr and amt else ""]
            for c, val in enumerate(cells):
                it = QTableWidgetItem(val)
                if c:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                it.setToolTip(note)
                self.preview.setItem(r, c, it)
        ok = v.balanced
        self.balance_lbl.setText(f"Dr {fmt_inr(v.dr_total)}  ·  Cr {fmt_inr(v.cr_total)}  " +
                                 ("✓" if ok else "✗ not balanced"))
        tone(self.balance_lbl, "ok" if ok else "errb")
        started = v.dr_total > 0 or v.cr_total > 0
        probs = self._issues(v) if started else []
        lu = entry.lock_date(self.company)
        if lu and v.date <= lu:
            probs.append(f"Books are locked up to {_fmt_date(lu)} - posting will ask for a reason")
        self.problems.setText("\n".join(f"• {p}" for p in probs))
        tone(self.problems, "err")
        self.b_post.setEnabled(bool(v.lines) and v.balanced)

    # ------------------------------------------------------------------ actions
    def pick_bills(self):
        party = self.party.currentText().strip()
        amt = dec(self.amount.text())
        if not party or not amt:
            QMessageBox.information(self, "Bills", "Enter the party and the amount first.")
            return
        dlg = BillsDialog(self.st, self.company, party, amt, want_dr=(self.base == "Receipt"), parent=self)
        if dlg.exec():
            self.bills = dlg.allocation
            self.bills_lbl.setText(", ".join(f"{n or t} {fmt_inr(a)}" for n, t, a in self.bills))
            self._changed()

    def create_ledger(self):
        if not self.company:
            return
        from sqlalchemy import select
        from ..db.models import MasterCache
        groups = [r.name for r in self.st.session.scalars(select(MasterCache).where(
            MasterCache.company_id == self.company.id, MasterCache.kind == "group"))]
        parent = {"Sales": "Sundry Debtors", "Credit Note": "Sundry Debtors", "Receipt": "Sundry Debtors"}.get(
            self.base, "Sundry Creditors")
        dlg = LedgerDialog(self.st, self.company, groups, parent_group=parent, parent=self)
        if dlg.exec() and dlg.created_name:
            self.m = self.st.masters(self.company)
            name = dlg.created_name
            self.set_type(self.base)
            if hasattr(self, "party"):
                self.party.setCurrentText(name)
            self.st.window.toast(f"✓ Ledger '{name}' created in Tally")

    def post(self, override: str = ""):
        if not self.company or not self.b_post.isEnabled():
            return
        v = self.voucher()
        probs = self._issues(v)
        if probs:
            QMessageBox.warning(self, "Not ready to post", "• " + "\n• ".join(probs))
            return
        cid, base = self.company.id, self.base
        cash = getattr(self, "cash", None)
        cash_name = cash.currentText().strip() if cash and base in ("Payment", "Receipt", "Contra") else ""
        win = self.st.window
        win.progress_start(f"Posting {base}…")

        import uuid
        if not getattr(self, "_remote", ""):
            self._remote = "entry-" + uuid.uuid4().hex     # same id if this entry is posted again after a failure
        rid = self._remote

        def job(_p):
            s = self.st.Local()
            try:
                comp = s.get(Company, cid)
                res = self.st.post(s, comp, v, None, override, remote_id=rid)
                if res.ok and cash_name:
                    entry.remember_cash_bank(s, comp, base, cash_name)
                heads = [l.ledger for l in v.lines if l.kind in ("income", "expense")] or \
                    [i.purchase_ledger for i in v.inventory]
                if res.ok and heads:
                    cfg = dict(comp.settings or {})
                    cfg["last_item_ledger"] = {**cfg.get("last_item_ledger", {}), base: heads[0]}
                    comp.settings = cfg
                    s.commit()
                return res
            finally:
                s.close()

        def done(res):
            win.progress_done(res.message if res.ok else "")
            if res.locked:
                reason = ask_lock_reason(self, res.message)
                if reason:
                    self.post(reason)
                return
            if not res.ok:
                QMessageBox.warning(self, "Tally", res.message)
                return
            self._remote = ""                                  # next entry gets a new id
            self.st.session.expire_all()
            self.company = self.st.company()
            win.toast(f"✓ {base} posted: {fmt_inr(v.dr_total)}  ({res.message})")
            self._last_posted = v
            self.set_type(base)                  # fresh form, same date and type
        run_bg(self, job, done, lambda m: (win.progress_done(""), QMessageBox.warning(self, "Tally", m)))

    def save_recurring(self):
        if not self.company:
            return
        v = self.voucher()
        if not v.balanced or not v.lines:
            QMessageBox.information(self, "Recurring", "Complete a balanced entry first.")
            return
        name, ok = QInputDialog.getText(self, "Save as recurring", "Name (e.g. Office rent):",
                                        text=v.narration[:40])
        if not ok or not name.strip():
            return
        freq, ok = QInputDialog.getItem(self, "Save as recurring", "Repeats", list(recurring.STEP), 0, False)
        if not ok:
            return
        day, ok = QInputDialog.getInt(self, "Save as recurring", "Day of the month (31 = month end)",
                                      int(v.date[6:8]) if v.date else 1, 1, 31)
        if not ok:
            return
        rec = recurring.from_voucher(self.company.id, name.strip(), v, freq, day)
        if "{month}" not in rec.narration:
            rec.narration = f"{name.strip()} for {{month}} {{year}}"
        self.st.session.add(rec)
        self.st.session.commit()
        self.st.window.toast(f"✓ '{name.strip()}' saved: next due {_fmt_date(rec.next_due)} (Journals → Recurring)")
