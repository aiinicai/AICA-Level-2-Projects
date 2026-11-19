"""Bank: import a statement, review the suggested ledger for each line, post Payment / Receipt / Contra."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from PyQt6.QtCore import QMimeData, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget)
from sqlalchemy import select

from ..db.models import BankLine, BankMapping, Company
from ..engine import bank, entry
from . import theme
from .bills_dialog import BillsDialog
from .common import LedgerCombo, PeriodPicker, ask_lock_reason, page_layout, run_bg
from .ledger_dialog import LedgerDialog

COLS = ["Date", "Narration", "Withdrawal", "Deposit", "Ledger", "Type", "Status"]


def _fmt(v: float) -> str:
    return f"{v:,.2f}" if v else ""


FIELDS = [("date", "Date *"), ("narration", "Narration *"), ("withdrawal", "Withdrawal / Debit"),
          ("deposit", "Deposit / Credit"), ("amount", "Amount (single column)"), ("drcr", "Dr / Cr marker"),
          ("ref", "Cheque / Ref"), ("balance", "Balance"), ("value_date", "Value date")]


class _ColumnList(QListWidget):
    """The statement's columns as chips you drag onto the Tally fields."""

    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setSpacing(2)

    def mimeData(self, items):
        md = QMimeData()
        md.setText(str(items[0].data(Qt.ItemDataRole.UserRole)))
        return md


class _Target(QLabel):
    dropped = pyqtSignal(str, int)

    def __init__(self, key: str):
        super().__init__("drop a column here")
        self.key = key
        self.setAcceptDrops(True)
        self.setMinimumHeight(30)
        self.setStyleSheet(f"QLabel {{ border: 1px dashed #98A2B3; border-radius: 8px; padding: 4px 10px; "
                           f"color: {theme.MUTED}; background: {theme.SUBTLE}; }}")

    def dragEnterEvent(self, e):
        if e.mimeData().hasText():
            e.acceptProposedAction()

    def dropEvent(self, e):
        self.dropped.emit(self.key, int(e.mimeData().text()))
        e.acceptProposedAction()

    def show_col(self, label: str):
        self.setText(label or "drop a column here")
        self.setStyleSheet(f"QLabel {{ border: 1px solid {'#A6F4C5' if label else '#98A2B3'}; border-radius: 8px; "
                           f"padding: 4px 10px; color: {theme.INK if label else theme.MUTED}; "
                           f"background: {theme.OK_BG if label else theme.SUBTLE}; }}")


class MappingDialog(QDialog):
    """Any Indian bank: drag the statement's columns onto Tally's banking fields. Saved for that bank's layout,
    so the next statement from the same bank imports without asking."""

    def __init__(self, path: Path, current: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Map statement columns")
        self.resize(1000, 640)
        self.rows, self.hdr = bank.preview(path)
        self.map: dict[str, int] = dict(current or {})
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Drag each column from the left onto the matching field. Fields with * are needed, plus "
                             "either Withdrawal + Deposit or a single Amount column (with a Dr/Cr marker if the "
                             "bank uses one).", wordWrap=True, objectName="muted"))
        hr = QHBoxLayout()
        hr.addWidget(QLabel("Header is on row"))
        self.hdr_spin = QSpinBox(minimum=1, maximum=max(1, len(self.rows)))
        self.hdr_spin.setValue(self.hdr + 1)
        self.hdr_spin.valueChanged.connect(self._header_changed)
        hr.addWidget(self.hdr_spin)
        hr.addSpacing(20)
        hr.addWidget(QLabel("Bank name (for your reference)"))
        self.name = QLineEdit(Path(path).stem[:40])
        hr.addWidget(self.name, 1)
        lay.addLayout(hr)
        mid = QHBoxLayout()
        self.cols = _ColumnList()
        self.cols.setMinimumWidth(320)
        mid.addWidget(self.cols, 1)
        form = QFormLayout()
        self.targets: dict[str, _Target] = {}
        for key, label in FIELDS:
            t = _Target(key)
            t.dropped.connect(self._drop)
            clr = QPushButton("×", objectName="ghost")
            clr.setFixedWidth(28)
            clr.clicked.connect(lambda _=False, k=key: self._drop(k, -1))
            row = QHBoxLayout()
            row.addWidget(t, 1)
            row.addWidget(clr)
            form.addRow(label, row)
            self.targets[key] = t
        fw = QWidget()
        fw.setLayout(form)
        mid.addWidget(fw, 1)
        lay.addLayout(mid, 1)
        lay.addWidget(QLabel("Preview", objectName="section"))
        self.prev = QTableWidget(0, 5)
        self.prev.setHorizontalHeaderLabels(["Date", "Narration", "Withdrawal", "Deposit", "Balance"])
        self.prev.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.prev.verticalHeader().setVisible(False)
        self.prev.setMaximumHeight(200)
        lay.addWidget(self.prev)
        self.err = QLabel("", objectName="muted")
        lay.addWidget(self.err)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Use and remember this mapping")
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.path = Path(path)
        self._header_changed(self.hdr + 1, auto=not current)

    def header(self) -> list[str]:
        return [str(x) for x in self.rows[self.hdr]] if self.rows else []

    def _header_changed(self, v: int, auto: bool = True):
        self.hdr = v - 1
        h = self.header()
        if auto:
            self.map = bank.detect_mapping(h)
        self.cols.clear()
        sample = self.rows[self.hdr + 1] if self.hdr + 1 < len(self.rows) else []
        for i, name in enumerate(h):
            ex = str(sample[i]) if i < len(sample) and sample[i] not in (None, "") else ""
            it = QListWidgetItem(f"{i + 1}. {name or '(blank)'}" + (f"   e.g. {ex[:28]}" if ex else ""))
            it.setData(Qt.ItemDataRole.UserRole, i)
            self.cols.addItem(it)
        self._render()

    def _drop(self, key: str, col: int):
        if col < 0:
            self.map.pop(key, None)
        else:
            for k in [k for k, v in self.map.items() if v == col]:
                self.map.pop(k)
            self.map[key] = col
        self._render()

    def _render(self):
        h = self.header()
        for key, t in self.targets.items():
            c = self.map.get(key)
            t.show_col(f"{c + 1}. {h[c]}" if c is not None and c < len(h) else "")
        try:
            st = bank.parse(self.path, self.mapping(), header_index=self.hdr)
            txns = st.txns[:10]
            self.err.setText(f"{len(st.txns)} transactions found" + (" · " + st.warnings[0] if st.warnings else ""))
        except Exception as e:
            txns = []
            self.err.setText(str(e))
        self.prev.setRowCount(len(txns))
        for r, t in enumerate(txns):
            vals = [f"{t.date[6:8]}-{t.date[4:6]}-{t.date[:4]}", t.narration, _fmt(float(t.withdrawal)),
                    _fmt(float(t.deposit)), _fmt(float(t.balance)) if t.balance is not None else ""]
            for c, v in enumerate(vals):
                self.prev.setItem(r, c, QTableWidgetItem(v))

    def mapping(self) -> dict:
        return {k: v for k, v in self.map.items() if v is not None}

    def _ok(self):
        try:
            st = bank.parse(self.path, self.mapping(), header_index=self.hdr)
        except Exception as e:
            self.err.setText(f"✗ {e}")
            return
        if not st.txns:
            self.err.setText("✗ No transactions with this mapping")
            return
        self.statement = st
        self.accept()


class ImportReview(QDialog):
    """Before importing: what is new, what was imported before, what is already in Tally."""
    LABEL = {"new": ("New", "green"), "dup_imported": ("Duplicate - skipped", "posted"),
             "in_tally": ("Already in Tally - won't be posted", "posted"), "possible": ("Possibly in Tally", "amber")}

    def __init__(self, verdicts, warnings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Check before importing")
        self.resize(980, 560)
        lay = QVBoxLayout(self)
        n = {k: sum(1 for v in verdicts if v.kind == k) for k in self.LABEL}
        head = QLabel(f"<b>{n['new']}</b> new  ·  <b>{n['dup_imported']}</b> duplicate(s) of lines imported earlier  ·  "
                      f"<b>{n['in_tally']}</b> already in Tally  ·  <b>{n['possible']}</b> possibly in Tally")
        lay.addWidget(head)
        lay.addWidget(QLabel("Checked on date, amount, direction, narration, cheque / UTR and running balance. "
                             "Duplicates are left out; lines already in Tally are kept for the balance check but "
                             "never posted.", objectName="muted", wordWrap=True))
        t = QTableWidget(len(verdicts), 5)
        t.setHorizontalHeaderLabels(["Date", "Narration", "Withdrawal", "Deposit", "Check"])
        t.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        t.setColumnWidth(4, 330)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        order = {"possible": 0, "new": 1, "in_tally": 2, "dup_imported": 3}
        for r, v in enumerate(sorted(verdicts, key=lambda v: (order[v.kind], v.txn.date))):
            tx = v.txn
            label, state = self.LABEL[v.kind]
            vals = [f"{tx.date[6:8]}-{tx.date[4:6]}-{tx.date[:4]}", tx.narration, _fmt(float(tx.withdrawal)),
                    _fmt(float(tx.deposit)), v.reason or label]
            fg, bg = theme.STATUS[state]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c in (2, 3):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if c == 4:
                    it.setForeground(QColor(fg))
                    it.setBackground(QColor(bg))
                t.setItem(r, c, it)
        lay.addWidget(t, 1)
        if warnings:
            w = QLabel("⚠ " + " · ".join(warnings[:3]), wordWrap=True)
            w.setStyleSheet(f"color: {theme.WARN_FG};")
            lay.addWidget(w)
        self.chk_possible = QCheckBox("Import 'possibly in Tally' lines as to post (untick to mark them as already "
                                      "in Tally)")
        self.chk_possible.setChecked(True)
        self.chk_possible.setVisible(n["possible"] > 0)
        lay.addWidget(self.chk_possible)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText(
            f"Import {n['new'] + n['possible'] + n['in_tally']} line(s)")
        bb.button(QDialogButtonBox.StandardButton.Ok).setEnabled(n["new"] + n["possible"] + n["in_tally"] > 0)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


class BalanceDialog(QDialog):
    def __init__(self, chk, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bank balance: statement vs Tally")
        self.resize(820, 520)
        lay = QVBoxLayout(self)
        d = chk.as_on
        lay.addWidget(QLabel(f"As on {d[6:8]}-{d[4:6]}-{d[:4]}:  statement {_fmt(float(chk.statement or 0))}  ·  "
                             f"Tally {_fmt(float(chk.tally or 0))}  ·  difference {_fmt(float(chk.difference or 0))}",
                             objectName="h2"))
        rows = [("On the statement, not yet in Tally", f"{l.date[6:8]}-{l.date[4:6]}", l.narration,
                 l.deposit - l.withdrawal) for l in chk.pending_lines]
        rows += [("In Tally, not on the statement", f"{v.date[6:8]}-{v.date[4:6]}",
                  f"{v.voucher_type} {v.number} {v.narration or ''}", float(amt) if dr else -float(amt))
                 for v, amt, dr in chk.tally_only]
        t = QTableWidget(len(rows), 4)
        t.setHorizontalHeaderLabels(["", "Date", "Particulars", "Effect"])
        t.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        t.setColumnWidth(0, 230)
        t.verticalHeader().setVisible(False)
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                it = QTableWidgetItem(f"{val:,.2f}" if c == 3 else str(val))
                if c == 3:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                t.setItem(r, c, it)
        lay.addWidget(t, 1)
        left = (chk.difference or 0) - chk.explained
        lay.addWidget(QLabel(f"Explained by these items: {_fmt(float(chk.explained)) or '0.00'}" +
                             ("   ·   ✓ fully explained" if abs(left) < Decimal("0.01") else
                              f"   ·   unexplained {left:,.2f} (sync Tally, or check opening balance / earlier "
                              f"months)"), wordWrap=True))
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


class MatchDialog(QDialog):
    """Match a bank line to voucher(s) already in Tally instead of posting a new entry."""

    def __init__(self, matches, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Match with Tally")
        self.resize(620, 320)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("These entries already in Tally add up to this bank line. Pick one to mark the line as "
                             "already in Tally (nothing is posted).", wordWrap=True, objectName="muted"))
        self.list = QListWidget()
        for m in matches:
            narr = "; ".join((v.narration or "")[:40] for v in m.vouchers)
            self.list.addItem(f"{m.description}   ·   {narr}")
        self.list.setCurrentRow(0)
        lay.addWidget(self.list, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Mark as matched")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


class BankPage(QWidget):
    FILTERS = [("todo", "To post"), ("ready", "Ready"), ("in_tally", "Already in Tally"), ("posted", "Posted"),
               ("all", "All")]

    def __init__(self, st):
        super().__init__(objectName="page")
        self.st = st
        root = page_layout(self, "Bank", "Import a bank statement (Excel, CSV or text PDF). Each line gets a suggested "
                                         "ledger from your past entries; lines already in Tally are detected.")
        top = QHBoxLayout()
        top.addWidget(QLabel("Bank ledger"))
        self.bank_combo = QComboBox()
        self.bank_combo.setMinimumWidth(260)
        self.bank_combo.currentIndexChanged.connect(lambda *_: self.reload())
        top.addWidget(self.bank_combo)
        b_imp = QPushButton("Import statement…", objectName="primary")
        b_imp.clicked.connect(lambda: self.import_statement())
        b_map = QPushButton("Map columns…")
        b_map.setToolTip("For a bank whose layout isn't recognised, or to correct a saved mapping")
        b_map.clicked.connect(lambda: self.import_statement(force_map=True))
        top.addWidget(b_imp)
        top.addWidget(b_map)
        top.addStretch(1)
        self.summary = QLabel("", objectName="muted")
        top.addWidget(self.summary)
        root.addLayout(top)

        seg = QWidget(objectName="segbar")
        sl = QHBoxLayout(seg)
        sl.setContentsMargins(3, 3, 3, 3)
        grp = QButtonGroup(self)
        self.seg = {}
        for key, label in self.FILTERS:
            b = QPushButton(label, objectName="seg", checkable=True)
            b.clicked.connect(lambda _=False, k=key: self.set_filter(k))
            grp.addButton(b)
            sl.addWidget(b)
            self.seg[key] = b
        fl = QHBoxLayout()
        fl.addWidget(seg)
        fl.addStretch(1)
        self.period = PeriodPicker("bank")
        self.period.changed.connect(lambda *_: self.reload())
        fl.addWidget(self.period)
        root.addLayout(fl)
        self.allocs: dict[str, list] = {}        # bank line id -> bill allocation

        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 92)
        self.table.setColumnWidth(2, 104)
        self.table.setColumnWidth(3, 104)
        self.table.setColumnWidth(4, 240)
        self.table.setColumnWidth(5, 84)
        self.table.setColumnWidth(6, 150)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked |
                                   QAbstractItemView.EditTrigger.SelectedClicked |
                                   QAbstractItemView.EditTrigger.EditKeyPressed)
        from .common import LedgerDelegate
        LedgerDelegate(self.table, lambda: sorted(self.m.ledgers) if getattr(self, "m", None) else [],
                       on_commit=lambda row, text: self._ledger_changed(row, text)).attach(self.table, 4)
        root.addWidget(self.table, 1)
        bal = QHBoxLayout()
        self.bal_lbl = QLabel("", wordWrap=True)
        b_bal = QPushButton("Check balance with Tally")
        b_bal.setToolTip("Statement closing balance vs the Tally bank ledger on the same date")
        b_bal.clicked.connect(self.check_balance)
        self.b_bal_det = QPushButton("Details…")
        self.b_bal_det.clicked.connect(lambda: BalanceDialog(self._bal, self).exec() if self._bal else None)
        self.b_bal_det.setEnabled(False)
        bal.addWidget(self.bal_lbl, 1)
        bal.addWidget(b_bal)
        bal.addWidget(self.b_bal_det)
        root.addLayout(bal)
        self._bal = None

        act = QHBoxLayout()
        self.chk_learn = QCheckBox("Remember")
        self.chk_learn.setToolTip("Remember the ledger for similar narrations next time")
        self.chk_learn.setChecked(True)
        b_new = QPushButton("+ Ledger")
        b_new.setToolTip("Create a ledger in Tally")
        b_new.clicked.connect(self.new_ledger)
        b_skip = QPushButton("Skip")
        b_skip.setToolTip("Skip the selected lines (not posted)")
        b_skip.clicked.connect(self.skip_selected)
        b_match = QPushButton("Match…")
        b_match.setToolTip("Mark the selected line as already in Tally: one voucher, or several that add up to it")
        b_match.clicked.connect(self.match_selected)
        b_bills = QPushButton("Bills…")
        b_bills.setToolTip("Pick the bills the selected payment / receipt settles (Agst Ref)")
        b_bills.clicked.connect(self.bills_selected)
        self.b_post_sel = QPushButton("Post selected")
        self.b_post_sel.clicked.connect(lambda: self.post(selected_only=True))
        self.b_post_ready = QPushButton("Post all ready", objectName="primary")
        self.b_post_ready.clicked.connect(lambda: self.post(selected_only=False))
        act.addWidget(self.chk_learn)
        act.addStretch(1)
        for b in (b_new, b_match, b_bills, b_skip, self.b_post_sel, self.b_post_ready):
            act.addWidget(b)
        root.addLayout(act)
        self.filter = "todo"
        self.seg["todo"].setChecked(True)
        self.rows: list[tuple] = []
        st.on_company_change(self.load_banks)

    def showEvent(self, e):
        self.load_banks()
        super().showEvent(e)

    # ------------------------------------------------------------------ data
    def load_banks(self):
        c = self.st.company()
        self.bank_combo.blockSignals(True)
        cur = self.bank_combo.currentText()
        self.bank_combo.clear()
        if c:
            self.m = self.st.masters(c)
            order = {"Bank Accounts": 0, "Bank OD A/c": 1}
            banks = sorted((n for n in entry.cash_bank_ledgers(self.m, c)
                            if self.m.ledgers.get(n, {}).get("_primary") != "Cash-in-Hand"),
                           key=lambda n: (order.get(self.m.ledgers.get(n, {}).get("_primary", ""), 2), n))
            self.bank_combo.addItems(banks)
            last = (c.settings or {}).get("last_bank", "")
            self.bank_combo.setCurrentText(cur if cur in banks else last if last in banks else (banks[0] if banks else ""))
        self.bank_combo.blockSignals(False)
        self.reload()

    def set_filter(self, k):
        self.filter = k
        self.seg[k].setChecked(True)
        self.render()

    def reload(self):
        c = self.st.company()
        bl = self.bank_combo.currentText()
        self.rows = []
        if not c or not bl:
            self.render()
            return
        s = self.st.session
        s.expire_all()
        self.m = self.st.masters(c)
        p = self.period.period()
        # entries made since the import (e.g. a Contra posted from another bank's statement) mark lines here
        rechecked = bank.recheck_new_lines(s, c.id, bl)
        if rechecked:
            self._ctx_dirty = True
            self.st.window.toast(f"{len(rechecked)} line(s) found already in Tally since import: "
                          + "; ".join(f"{ln.date[6:8]}-{ln.date[4:6]} {ln.deposit or ln.withdrawal:,.2f} = {d}"
                                      for ln, d in rechecked[:3]) + ("..." if len(rechecked) > 3 else ""))
        lines = list(s.scalars(select(BankLine).where(BankLine.company_id == c.id, BankLine.bank_ledger == bl,
                                                      BankLine.date >= p.frm, BankLine.date <= p.to)
                               .order_by(BankLine.date, BankLine.updated_at)))
        key = (c.id, bl, len(self.m.ledgers))
        if getattr(self, "_ctx_key", None) != key or getattr(self, "_ctx_dirty", True):
            self._ctx = bank.SuggestContext(s, c, self.m, bl)
            self._ctx_key, self._ctx_dirty = key, False
            self._sug_cache = {}
        for ln in lines:
            sug = None
            if ln.status == "new":
                sug = self._sug_cache.get(ln.id)
                if sug is None:
                    sug = bank.suggest(s, c, self.m, bl, bank.txn_of(ln), self._ctx)
                    self._sug_cache[ln.id] = sug
            self.rows.append((ln, sug))
        self.render()

    def _state(self, ln, sug) -> str:
        if ln.status == "posted":
            return "posted"
        if ln.status in ("in_tally", "skipped"):
            return "in_tally"
        if sug and sug.in_tally:
            return "in_tally"
        if sug and sug.ledger and sug.confidence == "green":
            return "ready"
        return "todo"

    def render(self):
        counts = {k: 0 for k, _ in self.FILTERS}
        for ln, sug in self.rows:
            st = self._state(ln, sug)
            counts[st] = counts.get(st, 0) + 1
            if st == "ready":
                counts["todo"] += 0
        counts["todo"] += counts["ready"]
        counts["all"] = len(self.rows)
        for k, label in self.FILTERS:
            self.seg[k].setText(f"{label} {counts.get(k, 0)}")
        shown = [(ln, sug) for ln, sug in self.rows if self.filter == "all" or self._state(ln, sug) == self.filter
                 or (self.filter == "todo" and self._state(ln, sug) in ("todo", "ready"))]
        self.shown = shown
        self.table.setRowCount(len(shown))
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        for r, (ln, sug) in enumerate(shown):
            state = self._state(ln, sug)
            d = ln.date
            vals = [f"{d[6:8]}-{d[4:6]}-{d[:4]}", ln.narration, _fmt(ln.withdrawal), _fmt(ln.deposit)]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c in (2, 3):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if c == 1:
                    it.setToolTip(ln.narration + (f"\nRef: {ln.reference}" if ln.reference else ""))
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c, it)
            if ln.status == "new" and state != "in_tally":
                led = QTableWidgetItem(sug.ledger if sug and sug.ledger else "")
                led.setFlags(led.flags() | Qt.ItemFlag.ItemIsEditable)
                bg = {"green": theme.OK_BG, "amber": theme.WARN_BG}.get(sug.confidence if sug else "", theme.ERR_BG)
                led.setBackground(QColor(bg))
                led.setToolTip((sug.note + "\n" if sug and sug.note else "") + "Double-click or type to change")
                if not (sug and sug.ledger):
                    led.setForeground(QColor(theme.MUTED))
                self.table.setItem(r, 4, led)
            else:
                it4 = QTableWidgetItem("")
                it4.setFlags(it4.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, 4, it4)
            vt = sug.vtype if sug else ("Payment" if ln.withdrawal else "Receipt")
            it5 = QTableWidgetItem(vt)
            it5.setFlags(it5.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 5, it5)
            label = {"posted": "Posted", "in_tally": (f"In Tally: {sug.in_tally}" if sug and sug.in_tally else
                                                      "Skipped" if ln.status == "skipped" else
                                                      "Matched with Tally" if ln.status == "in_tally" else
                                                      "Already in Tally / skipped"),
                     "ready": "Ready", "todo": "Pick ledger" if not (sug and sug.ledger) else "Confirm"}[state]
            it = QTableWidgetItem(label)
            it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            fg, bgc = theme.STATUS.get({"todo": "amber", "ready": "green", "in_tally": "posted",
                                        "posted": "posted"}[state])
            it.setForeground(QColor(fg))
            it.setBackground(QColor(bgc))
            it.setToolTip(sug.note if sug else label)
            if ln.id in self.allocs:
                it.setText(label + " · bills set")
                it.setToolTip(", ".join(f"{n or t} {a:,.2f}" for n, t, a in self.allocs[ln.id]))
            self.table.setItem(r, 6, it)
        self.table.blockSignals(False)
        self.table.setUpdatesEnabled(True)
        withdraw = sum(ln.withdrawal for ln, _ in self.rows)
        deposit = sum(ln.deposit for ln, _ in self.rows)
        self.summary.setText(f"{len(self.rows)} lines")
        self.summary.setToolTip(f"Out {withdraw:,.2f} · In {deposit:,.2f}")

    def _ledger_changed(self, row: int, text: str):
        ln, sug = self.shown[row]
        if sug is None:
            return
        sug.ledger = text.strip()
        if self.m and sug.ledger in self.m.ledgers:
            self.table.item(row, 4).setBackground(QColor(theme.OK_BG))
        sug.vtype = "Contra" if entry.is_cash_bank(self.m, self.st.company(), sug.ledger) else \
            ("Payment" if ln.withdrawal else "Receipt")
        self.allocs.pop(ln.id, None)
        self.table.item(row, 5).setText(sug.vtype)

    # ------------------------------------------------------------------ actions
    def _saved_mappings(self) -> dict:
        return {r.signature: r.mapping for r in self.st.session.scalars(select(BankMapping))}

    def import_statement(self, force_map: bool = False):
        c = self.st.company()
        bl = self.bank_combo.currentText()
        if not c or not bl:
            QMessageBox.information(self, "Bank", "Pick the bank ledger first (sync the company if the list is empty).")
            return
        p, _ = QFileDialog.getOpenFileName(self, "Bank statement", "", "Statements (*.xlsx *.xls *.csv *.pdf)")
        if not p:
            return
        path = Path(p)
        stmt = None
        if not force_map or path.suffix.lower() == ".pdf":
            try:
                stmt = bank.parse(path, saved=self._saved_mappings())
            except ValueError as e:
                if path.suffix.lower() == ".pdf" or "header row" not in str(e):
                    QMessageBox.warning(self, "Bank statement", str(e))
                    return
        if stmt is not None and stmt.warnings and path.suffix.lower() != ".pdf":
            if QMessageBox.question(self, "Bank statement", "\n".join(stmt.warnings[:3]) +
                                    "\n\nOpen the column mapping to check it?") == QMessageBox.StandardButton.Yes:
                stmt = None
        if stmt is None:
            dlg = MappingDialog(path, None, self)
            if not dlg.exec():
                return
            stmt = dlg.statement
            sig = stmt.signature
            if sig:
                row = self.st.session.scalar(select(BankMapping).where(BankMapping.signature == sig))
                if row is None:
                    row = BankMapping(signature=sig)
                    self.st.session.add(row)
                row.name, row.header, row.mapping = dlg.name.text().strip(), dlg.header(), dlg.mapping()
                self.st.session.commit()
        verdicts = bank.classify_import(self.st.session, c.id, bl, stmt)
        dlg = ImportReview(verdicts, stmt.warnings, self)
        if not dlg.exec():
            return
        counts = bank.store_classified(self.st.session, c, bl, verdicts, dlg.chk_possible.isChecked())
        c.settings = {**(c.settings or {}), "last_bank": bl}
        self.st.session.commit()
        self.st.window.toast(f"Imported {counts['new'] + counts['possible']} line(s) · skipped {counts['dup_imported']} "
                             f"duplicate(s) · {counts['in_tally']} already in Tally")
        self._ctx_dirty = True
        self.reload()
        self.check_balance()

    def check_balance(self):
        c = self.st.company()
        bl = self.bank_combo.currentText()
        if not c or not bl:
            return
        lines = list(self.st.session.scalars(select(BankLine).where(BankLine.company_id == c.id,
                                                                    BankLine.bank_ledger == bl)
                                             .order_by(BankLine.date, BankLine.updated_at)))
        as_on, closing = bank.statement_closing(lines)
        if not as_on:
            self.bal_lbl.setText("")
            return
        self.bal_lbl.setText("Checking the balance in Tally…")
        client, cname, cid = self.st.client(c), c.name, c.id
        from datetime import date as _date
        from ..engine.periods import fy_start
        d = _date(int(as_on[:4]), int(as_on[4:6]), int(as_on[6:8]))

        def job(_p):
            r = client.ledger_balance(cname, bl, fy_start(d).strftime("%Y%m%d"), as_on)
            return r["closing"] if r else None

        def done(tally_closing):
            chk = bank.balance_check(self.st.session, cid, bl, tally_closing, as_on)
            self._show_balance(chk)

        def fail(msg):
            chk = bank.balance_check(self.st.session, cid, bl, None, as_on)
            self._show_balance(chk, f"Tally not reachable ({msg[:60]})")
        run_bg(self, job, done, fail)

    def _show_balance(self, chk, err: str = ""):
        self._bal = chk
        d = chk.as_on
        on = f"{d[6:8]}-{d[4:6]}-{d[:4]}"
        if chk.statement is None:
            self.bal_lbl.setText(chk.note)
            self.b_bal_det.setEnabled(False)
            return
        if chk.tally is None:
            self.bal_lbl.setText(f"Statement closing on {on}: {chk.statement:,.2f}  ·  {err or 'Tally balance unknown'}")
            self.b_bal_det.setEnabled(False)
            return
        diff = chk.difference
        ok = abs(diff) < Decimal("0.01")
        if ok:
            tail = "✓ matches"
        elif abs(diff - chk.explained) < Decimal("0.01"):
            tail = (f"difference {diff:,.2f} is fully explained by {len(chk.pending_lines)} statement line(s) not "
                    f"yet posted" + (f" and {len(chk.tally_only)} Tally entr(ies) not on the statement"
                                     if chk.tally_only else "") + " - post them and it will match")
        else:
            tail = (f"difference {diff:,.2f} - {len(chk.pending_lines)} line(s) not yet in Tally, "
                    f"{len(chk.tally_only)} Tally entr(ies) not on the statement (Details…)")
        txt = f"As on {on}:  statement {chk.statement:,.2f}  ·  Tally {chk.tally:,.2f}  ·  " + tail
        self.bal_lbl.setText(txt)
        self.bal_lbl.setStyleSheet(f"color: {theme.OK_FG if ok else theme.WARN_FG}; font-weight: 600;")
        self.b_bal_det.setEnabled(not ok)

    def match_selected(self):
        sel = self._selected()
        if len(sel) != 1:
            QMessageBox.information(self, "Match", "Select one bank line.")
            return
        ln, _ = sel[0]
        if ln.status != "new":
            return
        c = self.st.company()
        ms = bank.match_candidates(self.st.session, c.id, ln.bank_ledger, bank.txn_of(ln))
        if not ms:
            QMessageBox.information(self, "Match", "No Tally voucher (or 2-3 vouchers within a week) through this "
                                                   "bank adds up to this amount. Sync Tally if it was entered "
                                                   "recently.")
            return
        dlg = MatchDialog(ms, self)
        if dlg.exec() and dlg.list.currentRow() >= 0:
            bank.mark_matched(self.st.session, ln, ms[dlg.list.currentRow()])
            self.reload()

    def bills_selected(self):
        sel = self._selected()
        if len(sel) != 1:
            QMessageBox.information(self, "Bills", "Select one bank line.")
            return
        ln, sg = sel[0]
        if ln.status != "new" or not sg or not sg.ledger:
            QMessageBox.information(self, "Bills", "Pick the party ledger for this line first.")
            return
        if self.m.ledgers.get(sg.ledger, {}).get("ISBILLWISEON", "").lower() != "yes":
            QMessageBox.information(self, "Bills", f"'{sg.ledger}' is not bill-wise in Tally - it posts as is.")
            return
        t = bank.txn_of(ln)
        dlg = BillsDialog(self.st, self.st.company(), sg.ledger, t.amount, want_dr=(t.direction == "in"),
                          parent=self)
        if dlg.exec():
            self.allocs[ln.id] = dlg.allocation
            self.render()

    def _selected(self):
        return [self.shown[i] for i in sorted({ix.row() for ix in self.table.selectedIndexes()})]

    def skip_selected(self):
        for ln, _ in self._selected():
            if ln.status == "new":
                ln.status = "skipped"
        self.st.session.commit()
        self.reload()

    def new_ledger(self):
        c = self.st.company()
        if not c:
            return
        from ..db.models import MasterCache
        groups = [r.name for r in self.st.session.scalars(select(MasterCache).where(
            MasterCache.company_id == c.id, MasterCache.kind == "group"))]
        dlg = LedgerDialog(self.st, c, groups, parent_group="Indirect Expenses", parent=self)
        if dlg.exec() and dlg.created_name:
            self.reload()

    def post(self, selected_only: bool, override: str = ""):
        c = self.st.company()
        bl = self.bank_combo.currentText()
        if not c:
            return
        pick = self._selected() if selected_only else [(ln, sg) for ln, sg in self.rows
                                                       if self._state(ln, sg) == "ready"]
        jobs, problems = [], []
        for ln, sg in pick:
            if ln.status != "new" or sg is None:
                continue
            if sg.in_tally and not selected_only:
                continue
            if not sg.ledger or sg.ledger not in self.m.ledgers:
                problems.append(f"{ln.date[6:8]}-{ln.date[4:6]} {ln.narration[:40]}: pick a ledger")
                continue
            t = bank.txn_of(ln)
            jobs.append((ln.id, t, sg.ledger, sg.vtype, self.allocs.get(ln.id, [])))
        if problems and not jobs:
            QMessageBox.information(self, "Bank", "• " + "\n• ".join(problems[:10]))
            return
        if not jobs:
            QMessageBox.information(self, "Bank", "Nothing to post. Lines already in Tally are never posted again.")
            return
        total = sum((j[1].amount for j in jobs), Decimal(0))
        if not override and QMessageBox.question(
                self, "Post bank entries", f"Post {len(jobs)} entr{'y' if len(jobs) == 1 else 'ies'} to Tally "
                f"(total {total:,.2f})?") != QMessageBox.StandardButton.Yes:
            return
        cid, learn = c.id, self.chk_learn.isChecked()
        win = self.st.window
        win.progress_start("Posting bank entries…")

        def job(progress):
            s = self.st.Local()
            ok, failed, locked = 0, [], ""
            try:
                comp = s.get(Company, cid)
                from ..engine import masters as masters_mod
                m = masters_mod.load(s, cid)
                for k, (lid, t, ledger, vtype, alloc) in enumerate(jobs, 1):
                    progress(f"Posting {k}/{len(jobs)}")
                    v = bank.build_voucher(comp, m, bl, t, ledger, vtype)
                    if alloc:
                        for l in v.lines:
                            if l.ledger == ledger:
                                l.bills, l.bill_type = list(alloc), ""
                    res = self.st.post(s, comp, v, None, override, remote_id=f"bank-{lid}")
                    ln = s.get(BankLine, lid)
                    if res.locked:
                        locked = res.message
                        continue
                    if res.ok:
                        ln.status = "posted"
                        ok += 1
                        if learn:
                            bank.learn(s, comp, bl, t, ledger)
                    else:
                        failed.append(f"{t.date[6:8]}-{t.date[4:6]} {t.narration[:40]}: {res.message}")
                    s.commit()
            finally:
                s.close()
            return ok, failed, locked

        def done(res):
            ok, failed, locked = res
            win.progress_done(f"{ok} bank entr{'y' if ok == 1 else 'ies'} posted")
            if ok:
                self.check_balance()
            for lid, *_ in jobs:
                if ok:
                    self.allocs.pop(lid, None)
            self._ctx_dirty = True
            self.reload()
            if locked:
                reason = ask_lock_reason(self, locked + "\n(Some lines fall in the locked period.)")
                if reason:
                    self.post(selected_only, reason)
                return
            if failed or problems:
                QMessageBox.warning(self, "Bank", f"{ok} posted.\n\nNot posted:\n• " + "\n• ".join((failed + problems)[:10]))

        run_bg(self, job, done, lambda m: (win.progress_done(""), QMessageBox.warning(self, "Bank", m)),
               win.progress_text)
