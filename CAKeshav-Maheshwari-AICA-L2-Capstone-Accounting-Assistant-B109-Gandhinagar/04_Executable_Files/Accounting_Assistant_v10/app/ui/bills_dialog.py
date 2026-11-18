"""Bill-wise settlement: tick the open bills a payment / receipt settles (Agst Ref). Part payment allowed;
anything left over goes On Account (advance)."""
from __future__ import annotations

from decimal import Decimal

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView,
                             QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..engine import entry
from .common import dec, fmt_inr, run_bg


class BillsDialog(QDialog):
    def __init__(self, st, company, party: str, total: Decimal, want_dr: bool | None = None, parent=None):
        """want_dr: True = show receivables (for receipts), False = payables (for payments), None = all."""
        super().__init__(parent)
        self.st, self.company, self.party, self.total = st, company, party, Decimal(total)
        self.want_dr = want_dr
        self.bills: list[entry.OpenBill] = []
        self.allocation: list[tuple] = []
        self.setWindowTitle(f"Settle bills · {party}")
        self.resize(640, 440)
        lay = QVBoxLayout(self)
        self.head = QLabel(f"Amount {fmt_inr(self.total)} · loading open bills from Tally…", objectName="h2")
        lay.addWidget(self.head)
        self.src = QLabel("", objectName="muted", wordWrap=True)
        lay.addWidget(self.src)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["", "Bill", "Date", "Pending", "Settle now"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 34)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.itemChanged.connect(self._item_changed)
        lay.addWidget(self.table, 1)
        self.foot = QLabel("", objectName="muted")
        lay.addWidget(self.foot)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Use these bills")
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        client, cname = st.client(company), company.name

        def job(_p):
            return client.bills(cname, party)

        def done(rows):
            self.bills = [entry.OpenBill(b["name"], b["date"][:8], abs(b["amount"]), b["amount"] < 0, b["due"])
                          for b in rows]
            self.src.setText("Live from Tally.")
            self._fill()

        def fail(msg):
            self.bills = entry.open_bills_from_history(st.session, company.id, party)
            self.src.setText("Tally not reachable - open bills worked out from the synced entries (opening bills "
                             "of earlier years are not included).")
            self._fill()
        run_bg(self, job, done, fail)

    def _fill(self):
        bills = [b for b in self.bills if self.want_dr is None or b.dr == self.want_dr] or self.bills
        bills.sort(key=lambda b: b.date)
        self.shown = bills
        self.table.blockSignals(True)
        self.table.setRowCount(len(bills))
        left = self.total
        for r, b in enumerate(bills):
            take = min(left, b.amount) if left > 0 else Decimal(0)   # oldest first, like Tally's auto-allocation
            ck = QTableWidgetItem("")
            ck.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            ck.setCheckState(Qt.CheckState.Checked if take > 0 else Qt.CheckState.Unchecked)
            self.table.setItem(r, 0, ck)
            for c, v in enumerate([b.name, f"{b.date[6:8]}-{b.date[4:6]}-{b.date[:4]}" if b.date else "",
                                   fmt_inr(b.amount)], start=1):
                it = QTableWidgetItem(v)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if c == 3:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(r, c, it)
            amt = QTableWidgetItem(f"{take:.2f}" if take else "")
            amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r, 4, amt)
            left -= take
        self.table.blockSignals(False)
        self.head.setText(f"Amount {fmt_inr(self.total)} · {len(bills)} open bill(s)" if bills else
                          f"Amount {fmt_inr(self.total)} · no open bills - it will go On Account")
        self._update()

    def _item_changed(self, it):
        if it.column() == 0:
            self.table.blockSignals(True)
            self._toggle(it.row(), it.checkState() == Qt.CheckState.Checked)
            self.table.blockSignals(False)
        self._update()

    def _toggle(self, row: int, on: bool):
        b = self.shown[row]
        used = sum((dec(self.table.item(r, 4).text()) for r in range(self.table.rowCount()) if r != row),
                   Decimal(0))
        self.table.item(row, 4).setText(f"{min(b.amount, max(self.total - used, Decimal(0))):.2f}" if on else "")

    def picked(self) -> dict:
        return {self.shown[r].name: dec(self.table.item(r, 4).text()) for r in range(self.table.rowCount())
                if dec(self.table.item(r, 4).text()) > 0}

    def _update(self):
        used = sum(self.picked().values(), Decimal(0))
        rest = self.total - used
        txt = f"Against bills {fmt_inr(used)}"
        if rest > 0:
            txt += f"   ·   On Account / advance {fmt_inr(rest)}"
        elif rest < 0:
            txt += f"   ·   ✗ {fmt_inr(-rest)} more than the amount"
        self.foot.setText(txt)

    def _ok(self):
        if sum(self.picked().values(), Decimal(0)) > self.total + Decimal("0.005"):
            self.foot.setText("Bills ticked exceed the amount - reduce one of them")
            return
        self.allocation = entry.allocate(self.shown, self.picked(), self.total)
        self.accept()
