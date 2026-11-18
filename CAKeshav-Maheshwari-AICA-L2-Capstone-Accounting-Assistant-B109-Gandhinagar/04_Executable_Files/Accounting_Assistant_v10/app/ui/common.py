"""Shared UI pieces: background worker, cards, pills, the Dr/Cr voucher grid."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QComboBox, QCompleter, QFrame, QHBoxLayout, QHeaderView, QLabel, QPushButton,
                             QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..engine.voucher import VLine, Voucher

CONF_COLOURS = {"green": "#F6FEF9", "amber": "#FFFAEB", "red": "#FEF3F2"}


class Worker(QObject):
    done = pyqtSignal(object)
    failed = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn(self.progress.emit))
        except Exception as e:  # surfaced to the user, never swallowed
            import traceback
            traceback.print_exc()
            self.failed.emit(str(e))


def run_bg(owner, fn, on_done, on_fail, on_progress=None):
    th, w = QThread(owner), Worker(fn)
    w.moveToThread(th)
    th.started.connect(w.run)
    w.done.connect(on_done)
    w.failed.connect(on_fail)
    if on_progress:
        w.progress.connect(on_progress)
    for sig in (w.done, w.failed):
        sig.connect(th.quit)
    th.finished.connect(w.deleteLater)
    owner._jobs = [j for j in getattr(owner, "_jobs", []) if j[0].isRunning()] + [(th, w)]
    th.start()


def card(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    f = QFrame(objectName="card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(18, 16, 18, 16)
    lay.setSpacing(10)
    if title:
        lay.addWidget(QLabel(title, objectName="cardTitle"))
    return f, lay


def set_pill(lbl: QLabel, text: str, kind: str) -> None:
    lbl.setText(text)
    lbl.setObjectName({"ok": "pillOk", "green": "pillOk", "bad": "pillBad", "red": "pillBad",
                       "warn": "pillWarn", "amber": "pillWarn"}.get(kind, "pillWarn"))
    lbl.setStyle(lbl.style())


def page_layout(widget: QWidget, title: str, subtitle: str = "") -> QVBoxLayout:
    root = QVBoxLayout(widget)
    root.setContentsMargins(28, 22, 28, 22)
    root.setSpacing(14)
    root.addWidget(QLabel(title, objectName="h1"))
    if subtitle:
        s = QLabel(subtitle, objectName="muted", wordWrap=True)
        root.addWidget(s)
    return root


def dec(text: str) -> Decimal:
    try:
        return Decimal((text or "0").replace(",", "").strip() or "0")
    except InvalidOperation:
        return Decimal(0)


def tone(w, value: str, prop: str = "tone"):
    """Colour a widget through a property matched by the global stylesheet. Much cheaper than a per-widget
    setStyleSheet, which re-styles the widget from scratch (20-50 ms each on Windows)."""
    if w.property(prop) == value:
        return
    w.setProperty(prop, value)
    st = w.style()
    st.unpolish(w)
    st.polish(w)


class _SelectAllOnFocus(QObject):
    """Landing on a ledger field (Tab or click) selects the whole name, so one keystroke replaces it."""

    def eventFilter(self, obj, ev):
        from PyQt6.QtCore import QEvent, QTimer
        if ev.type() == QEvent.Type.FocusIn:
            QTimer.singleShot(0, obj.selectAll)
        elif ev.type() == QEvent.Type.MouseButtonPress and not obj.hasFocus():
            obj.setFocus()
            QTimer.singleShot(0, obj.selectAll)
            return True
        return False


_SELECT_ALL = None


class LedgerCombo(QComboBox):
    """Searchable ledger field: reachable with Tab, whole text selected on focus, matching ledgers pop up as soon
    as you type (anywhere in the name). All combos with the same ledger list share one model, so creating many
    of them is cheap."""

    def __init__(self, names: list[str], current: str = ""):
        global _SELECT_ALL
        super().__init__()
        self.setEditable(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMaxVisibleItems(14)
        self._names: list[str] = []
        self._use(list(names))
        self.setCurrentText(current)
        if _SELECT_ALL is None:
            _SELECT_ALL = _SelectAllOnFocus()
        self.lineEdit().installEventFilter(_SELECT_ALL)

    def _use(self, names: list[str]):
        names = [n for n in names if n]
        self._names = names
        mdl = ledger_model(names)
        text = self.currentText() if self.lineEdit() else ""
        self.setModel(mdl)
        comp = QCompleter(mdl, self)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        comp.setMaxVisibleItems(12)
        self.setCompleter(comp)
        self.setCurrentText(text)

    def addItems(self, texts):
        self._use(self._names + [t for t in texts if t])

    def clear(self):                         # never clear the shared model
        self._names = []
        self.setModel(QStringListModel([""]))
        self.setEditText("")

    def wheelEvent(self, e):                 # don't change ledgers by accident while scrolling a page
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


class _GridTable(QTableWidget):
    """Tab walks ledger -> Dr/Cr -> next line, like Tally's voucher screen."""

    def __init__(self, grid, *a):
        super().__init__(*a)
        self.grid = grid

    def focusNextPrevChild(self, nxt: bool) -> bool:
        if self.grid.tab(nxt):
            return True
        return super().focusNextPrevChild(nxt)

    def closeEditor(self, editor, hint):
        from PyQt6.QtWidgets import QAbstractItemDelegate
        H = QAbstractItemDelegate.EndEditHint
        if hint in (H.EditNextItem, H.EditPreviousItem):
            super().closeEditor(editor, H.NoHint)
            if not self.grid.tab(hint == H.EditNextItem):
                self.parentWidget().focusNextChild()
            return
        super().closeEditor(editor, hint)


class _ComboTab(QObject):
    def __init__(self, grid):
        super().__init__()
        self.grid = grid

    def eventFilter(self, obj, ev):
        from PyQt6.QtCore import QEvent
        if ev.type() == QEvent.Type.KeyPress and ev.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            if self.grid.completer_open(obj):
                return False
            row = self.grid.row_of(obj)
            if row >= 0:
                self.grid.table.setCurrentCell(row, 0)
                if self.grid.tab(ev.key() == Qt.Key.Key_Tab):
                    return True
        return False


class VoucherGrid(QWidget):
    """Editable Dr/Cr grid. Ledger cells are searchable combos over live Tally ledgers.
    Lines come and go by themselves: while Dr and Cr differ, Tab past the last line adds a line carrying the
    difference on the short side; a line left empty disappears when you move off it."""
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ledger_names: list[str] = []
        self._meta: list[VLine] = []
        self._combo_tab = _ComboTab(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.table = _GridTable(self, 0, 4)
        self.table.setHorizontalHeaderLabels(["Ledger", "Dr", "Cr", "Why"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 96)
        self.table.setColumnWidth(2, 96)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnHidden(3, True)          # reason shown as tooltip; row colour shows confidence
        self.table.setWordWrap(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(lambda *_: self._update_totals())
        self.table.currentCellChanged.connect(self._cell_moved)
        lay.addWidget(self.table)
        bar = QHBoxLayout()
        add, rem = QPushButton("+ Line"), QPushButton("− Line")
        add.setToolTip("Lines are added automatically: press Tab on the last line while Dr and Cr differ")
        rem.setToolTip("A line left empty disappears by itself")
        add.clicked.connect(lambda: self._add_row(VLine("", Decimal(0), True, "other", "Added manually", "amber")))
        rem.clicked.connect(self._remove_row)
        self.totals = QLabel("", objectName="muted")
        bar.addWidget(add)
        bar.addWidget(rem)
        self.bar = bar
        bar.addStretch(1)
        bar.addWidget(self.totals)
        lay.addLayout(bar)

    def set_voucher(self, v: Voucher, ledger_names: list[str]):
        self.ledger_names = ledger_names
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self._meta = []
        for l in v.lines:
            self._add_row(l)
        self.table.blockSignals(False)
        self._update_totals()

    def _add_row(self, l: VLine):
        # build the whole row with signals off: a 'changed' fired half-way (item 1 set, item 2 not yet, no meta)
        # made listeners read a half-built row -> exception -> PyQt6 closed the app ("+ Line" crash)
        was = self.table.blockSignals(True)
        try:
            self._build_row(l)
        finally:
            self.table.blockSignals(was)
        self._update_totals()

    def _build_row(self, l: VLine):
        r = self.table.rowCount()
        self.table.insertRow(r)
        combo = LedgerCombo(self.ledger_names, l.ledger)
        combo.lineEdit().setCursorPosition(0)
        combo.setToolTip(f"{l.ledger}\n{l.note}" if l.ledger else l.note)
        combo.currentTextChanged.connect(lambda *_: self._update_totals())
        combo.lineEdit().installEventFilter(self._combo_tab)
        self.table.setCellWidget(r, 0, combo)
        dr = QTableWidgetItem(f"{l.amount:,.2f}" if l.dr and l.amount else "")
        cr = QTableWidgetItem(f"{l.amount:,.2f}" if not l.dr and l.amount else "")
        for it in (dr, cr):
            it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        why = QTableWidgetItem(l.note)
        why.setFlags(why.flags() & ~Qt.ItemFlag.ItemIsEditable)
        why.setToolTip(l.note)
        bg = QColor(CONF_COLOURS.get(l.confidence, "#ffffff"))
        for it in (dr, cr, why):
            it.setBackground(bg)
        combo.setProperty("cell", "true")
        tone(combo, l.confidence if l.confidence in ("green", "amber", "red") else "green", "conf")
        self.table.setItem(r, 1, dr)
        self.table.setItem(r, 2, cr)
        self.table.setItem(r, 3, why)
        self._meta.append(l)

    # ---- automatic lines
    def row_of(self, editor) -> int:
        for r in range(self.table.rowCount()):
            w = self.table.cellWidget(r, 0)
            if w is not None and (w is editor or w.lineEdit() is editor):
                return r
        return -1

    @staticmethod
    def completer_open(editor) -> bool:
        c = editor.completer() if hasattr(editor, "completer") else None
        return bool(c and c.popup() and c.popup().isVisible())

    def _row_empty(self, r: int) -> bool:
        """Nothing entered by the user: no ledger, and either no amount or only the amount the grid filled in."""
        w = self.table.cellWidget(r, 0)
        if w and w.currentText().strip():
            return False
        auto = r < len(self._meta) and self._meta[r].note == "Added automatically"
        txt = lambda c: (self.table.item(r, c).text().strip() if self.table.item(r, c) else "")
        return auto or (not dec(txt(1)) and not dec(txt(2)))

    def _diff(self) -> Decimal:
        dr = sum((dec(self.table.item(r, 1).text()) for r in range(self.table.rowCount()) if self.table.item(r, 1)),
                 Decimal(0))
        cr = sum((dec(self.table.item(r, 2).text()) for r in range(self.table.rowCount()) if self.table.item(r, 2)),
                 Decimal(0))
        return dr - cr

    def _focus_cell(self, r: int, c: int):
        self.table.setCurrentCell(r, c)
        if c == 0:
            w = self.table.cellWidget(r, 0)
            if w:
                w.setFocus()
                w.lineEdit().selectAll()
        else:
            self.table.setFocus()
            self.table.editItem(self.table.item(r, c))

    def tab(self, forward: bool = True) -> bool:
        """Move like Tally. Returns False when focus should leave the grid."""
        n = self.table.rowCount()
        r, c = self.table.currentRow(), self.table.currentColumn()
        if n == 0:
            return False
        r = max(r, 0)
        if not forward:
            if c > 0:
                self._focus_cell(r, 0)
                return True
            if r > 0:
                prev_amt = 1 if dec(self.table.item(r - 1, 1).text() if self.table.item(r - 1, 1) else '') else 2
                self._focus_cell(r - 1, prev_amt)
                return True
            return False
        if c <= 0:
            meta_dr = self._meta[r].dr if r < len(self._meta) else True
            has_cr = bool(dec(self.table.item(r, 2).text() if self.table.item(r, 2) else ''))
            self._focus_cell(r, 2 if has_cr or (not meta_dr and not dec(self.table.item(r, 1).text())) else 1)
            return True
        if c == 1 and not dec(self.table.item(r, 1).text()):
            self._focus_cell(r, 2)
            return True
        # leaving the amounts: next line, or a new one while unbalanced
        if r + 1 < n:
            self._focus_cell(r + 1, 0)
            return True
        diff = self._diff()
        if abs(diff) >= Decimal("0.005") and not self._row_empty(r):
            self._add_row(VLine("", abs(diff), diff < 0, "other", "Added automatically", "amber"))
            self._focus_cell(r + 1, 0)
            return True
        return False

    def _cell_moved(self, row, col, prev_row, prev_col):
        if prev_row < 0 or prev_row == row or prev_row >= self.table.rowCount():
            return
        if self.table.rowCount() > 2 and self._row_empty(prev_row):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda pr=prev_row: self._drop_if_empty(pr))

    def _drop_if_empty(self, r: int):
        if 0 <= r < self.table.rowCount() and self.table.rowCount() > 2 and self._row_empty(r) \
                and r != self.table.currentRow():
            self.table.removeRow(r)
            self._meta.pop(r)
            self._update_totals()

    def _remove_row(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r)
            self._meta.pop(r)
            self._update_totals()

    def lines(self) -> list[VLine]:
        out = []
        txt = lambda r, c: self.table.item(r, c).text() if self.table.item(r, c) else ""
        for r in range(self.table.rowCount()):
            meta = self._meta[r] if r < len(self._meta) else VLine("", Decimal(0), True, "other", "", "amber")
            w = self.table.cellWidget(r, 0)
            ledger = w.currentText().strip() if w else ""
            dr, cr = dec(txt(r, 1)), dec(txt(r, 2))
            amt, is_dr = (dr, True) if dr else (cr, False)
            out.append(VLine(ledger, amt, is_dr, meta.kind, meta.note, meta.confidence, meta.bill_ref,
                             meta.credit_days, getattr(meta, "bill_type", ""), list(getattr(meta, "bills", []))))
        return out

    def _update_totals(self):
        if not hasattr(self, "totals"):
            return
        dr = sum((dec(self.table.item(r, 1).text()) for r in range(self.table.rowCount())
                  if self.table.item(r, 1)), Decimal(0))
        cr = sum((dec(self.table.item(r, 2).text()) for r in range(self.table.rowCount())
                  if self.table.item(r, 2)), Decimal(0))
        ok = abs(dr - cr) < Decimal("0.005")
        self.totals.setText(f"Dr {dr:,.2f}   Cr {cr:,.2f}   " + ("✓ balanced" if ok else f"✗ diff {dr - cr:,.2f}"))
        tone(self.totals, "ok" if ok else "errb")
        self.changed.emit()


# ---------------------------------------------------------------------- period picker
class PeriodPicker(QWidget):
    """Default = current FY. Quick picks: This month / Last month / This quarter / This FY / Last FY / Custom.
    The last choice is remembered per page (key)."""
    changed = pyqtSignal(object)            # Period

    def __init__(self, key: str = "", label: str = "Period"):
        super().__init__()
        from PyQt6.QtCore import QDate, QSettings
        from PyQt6.QtWidgets import QDateEdit
        from ..engine import periods
        self._periods = periods
        self.key = key
        self._qs = QSettings("AccountingAssistant", "periods")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        if label:
            lay.addWidget(QLabel(label, objectName="muted"))
        self.combo = QComboBox()
        self.combo.addItems(periods.QUICK)
        self.d1, self.d2 = QDateEdit(calendarPopup=True), QDateEdit(calendarPopup=True)
        for d in (self.d1, self.d2):
            d.setDisplayFormat("dd-MM-yyyy")
            d.setFixedWidth(112)
        self.to_lbl = QLabel("to", objectName="muted")
        self.info = QLabel("", objectName="muted")
        for w in (self.combo, self.d1, self.to_lbl, self.d2, self.info):
            lay.addWidget(w)
        saved = self._qs.value(f"{key}/choice", "This FY") if key else "This FY"
        self.combo.setCurrentText(saved if saved in periods.QUICK else "This FY")
        if saved == "Custom" and key:
            for d, k in ((self.d1, "from"), (self.d2, "to")):
                v = self._qs.value(f"{key}/{k}", "")
                if v:
                    d.setDate(QDate.fromString(v, "yyyyMMdd"))
        self._QDate = QDate
        self.combo.currentTextChanged.connect(self._pick)
        self.d1.dateChanged.connect(self._custom)
        self.d2.dateChanged.connect(self._custom)
        self._pick(self.combo.currentText(), emit=False)

    def period(self):
        from datetime import date as _d
        if self.combo.currentText() == "Custom":
            a, b = self.d1.date(), self.d2.date()
            s, e = _d(a.year(), a.month(), a.day()), _d(b.year(), b.month(), b.day())
            if e < s:
                s, e = e, s
            return self._periods.Period(s, e, "Custom")
        return self._periods.quick(self.combo.currentText())

    def _pick(self, name: str, emit: bool = True):
        custom = name == "Custom"
        for w in (self.d1, self.to_lbl, self.d2):
            w.setVisible(custom)
        if not custom:
            p = self._periods.quick(name)
            for d, v in ((self.d1, p.start), (self.d2, p.end)):
                d.blockSignals(True)
                d.setDate(self._QDate(v.year, v.month, v.day))
                d.blockSignals(False)
        self.info.setText("" if custom else self.period().text())
        self.info.setVisible(not custom)
        self._save()
        if emit:
            self.changed.emit(self.period())

    def _custom(self, *_):
        if self.combo.currentText() == "Custom":
            self._save()
            self.changed.emit(self.period())

    def _save(self):
        if not self.key:
            return
        self._qs.setValue(f"{self.key}/choice", self.combo.currentText())
        p = self.period()
        self._qs.setValue(f"{self.key}/from", p.frm)
        self._qs.setValue(f"{self.key}/to", p.to)

    def compact(self, on: bool):
        self.info.setVisible(not on and self.combo.currentText() != "Custom")


def fmt_inr(v) -> str:
    """Indian grouping: 2,78,645.00"""
    try:
        v = Decimal(str(v or 0))
    except Exception:
        return str(v)
    s = f"{abs(v):.2f}"
    whole, frac = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
        whole = f"{head},{tail}"
    return ("-" if v < 0 else "") + f"{whole}.{frac}"


def drcr(v) -> str:
    """Tally sign -> '1,180.00 Dr' / 'Cr'."""
    v = Decimal(str(v or 0))
    if not v:
        return "0.00"
    return f"{fmt_inr(abs(v))} {'Dr' if v < 0 else 'Cr'}"


def ask_lock_reason(parent, message: str) -> str:
    from PyQt6.QtWidgets import QInputDialog
    text, ok = QInputDialog.getText(parent, "Period locked", message + "\n\nReason for posting anyway "
                                                                        "(saved in the audit log):")
    return text.strip() if ok else ""


# ---------------------------------------------------------------------- fast tables: no widget per row
# A widget per table row (combo, checkbox) costs ~50 ms each to create and style on Windows, so a 150-line
# bank statement took 15 s to show. Tables instead keep plain text items and open a combo only for the cell
# being edited (double-click, F2 or just start typing).
from PyQt6.QtCore import QStringListModel
from PyQt6.QtWidgets import QStyledItemDelegate

_LEDGER_MODELS: dict = {}


def ledger_model(names: list[str]) -> QStringListModel:
    """One shared model per ledger list (for completers), instead of a copy in every combo."""
    key = hash(tuple(names))
    mdl = _LEDGER_MODELS.get(key)
    if mdl is None:
        if len(_LEDGER_MODELS) > 12:
            _LEDGER_MODELS.clear()
        mdl = QStringListModel([""] + list(names))
        _LEDGER_MODELS[key] = mdl
    return mdl


class LedgerDelegate(QStyledItemDelegate):
    """Ledger column: plain text until edited, then a searchable LedgerCombo (whole text selected)."""

    def __init__(self, parent, names_fn, on_commit=None, editable_fn=None):
        super().__init__(parent)
        self.names_fn, self.on_commit, self.editable_fn = names_fn, on_commit, editable_fn

    def createEditor(self, parent, option, index):
        if self.editable_fn and not self.editable_fn(index.row()):
            return None
        names = self.names_fn()
        cb = LedgerCombo([], "")
        cb.setParent(parent)
        cb.setModel(ledger_model(names))
        comp = QCompleter(ledger_model(names), cb)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        cb.setCompleter(comp)
        self._last_editor = cb
        return cb

    def setEditorData(self, editor, index):
        if getattr(editor, "_started", False):
            return                                   # editor opened by typing: keep what was typed
        editor.setCurrentText(index.data(Qt.ItemDataRole.EditRole) or "")
        editor.lineEdit().selectAll()

    def eventFilter(self, obj, ev):
        from PyQt6.QtCore import QEvent
        if ev.type() == QEvent.Type.KeyPress and ev.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            comp = obj.completer() if hasattr(obj, "completer") else None
            if comp is not None and comp.popup().isVisible():
                # Enter takes the highlighted match (or the first one) and moves on, in one keystroke
                idx = comp.popup().currentIndex()
                if not idx.isValid():
                    idx = comp.completionModel().index(0, 0)
                if idx.isValid():
                    obj.setCurrentText(idx.data())
                comp.popup().hide()
            table = self.parent()
            row, col = table.currentRow(), table.currentColumn()
            self.commitData.emit(obj)
            self.closeEditor.emit(obj, QStyledItemDelegate.EndEditHint.NoHint)
            if row + 1 < table.rowCount():           # like Tally: Enter moves to the next line's ledger
                table.setCurrentCell(row + 1, col)
            return True
        return super().eventFilter(obj, ev)

    def attach(self, table, col: int):
        """Tally-style ledger column: landing on the cell (Tab, arrows, Enter) opens it with the whole name
        selected, so typing straight away replaces the old ledger - no need to delete it first."""
        from PyQt6.QtCore import QEvent, QObject, QTimer
        self._table, self._col = table, col
        table.setItemDelegateForColumn(col, self)

        def landed(r, c, *_):
            if c == col and r >= 0 and table.hasFocus():
                it = table.item(r, c)
                if it is not None and it.flags() & Qt.ItemFlag.ItemIsEditable and \
                        (not self.editable_fn or self.editable_fn(r)):
                    QTimer.singleShot(0, lambda: table.state() != table.State.EditingState and
                                      table.currentRow() == r and table.currentColumn() == c and
                                      table.edit(table.model().index(r, c)))
        table.currentCellChanged.connect(landed)

        class _TypeToEdit(QObject):
            def eventFilter(_s, obj, ev):
                if ev.type() == QEvent.Type.KeyPress and table.currentColumn() == col and ev.text() and \
                        ev.text().isprintable() and not ev.modifiers() & ~Qt.KeyboardModifier.ShiftModifier and \
                        table.state() != table.State.EditingState:
                    idx = table.currentIndex()
                    if not idx.isValid() or (self.editable_fn and not self.editable_fn(idx.row())):
                        return False
                    ch = ev.text()
                    self._typed = ch
                    self._last_editor = None
                    table.edit(idx)
                    ed = self._last_editor
                    if ed is not None:
                        ed._started = True
                        ed.setCurrentText(ch)
                        le = ed.lineEdit()
                        QTimer.singleShot(0, lambda: (le.deselect(), le.setCursorPosition(len(le.text())),
                                                      ed.completer() and ed.completer().complete()))
                    return True
                return False
        self._typer = _TypeToEdit(table)
        table.installEventFilter(self._typer)
        return self

    def setModelData(self, editor, model, index):
        text = editor.currentText().strip()
        if text != (index.data(Qt.ItemDataRole.EditRole) or ""):
            model.setData(index, text, Qt.ItemDataRole.EditRole)
            if self.on_commit:
                self.on_commit(index.row(), text)


class ChoiceDelegate(QStyledItemDelegate):
    """A fixed list of (code, text) choices; the cell shows the text, a combo opens only while editing."""

    def __init__(self, parent, choices: list[tuple], on_commit=None):
        super().__init__(parent)
        self.choices, self.on_commit = choices, on_commit

    def createEditor(self, parent, option, index):
        cb = QComboBox(parent)
        for code, text in self.choices:
            cb.addItem(text, code)
        cb.activated.connect(lambda *_: self.commitData.emit(cb))
        return cb

    def setEditorData(self, editor, index):
        code = index.data(Qt.ItemDataRole.UserRole)
        editor.setCurrentIndex(max(0, editor.findData(code)))
        editor.showPopup()

    def setModelData(self, editor, model, index):
        code, text = editor.currentData(), editor.currentText()
        if code != index.data(Qt.ItemDataRole.UserRole):
            model.setData(index, code, Qt.ItemDataRole.UserRole)
            model.setData(index, text, Qt.ItemDataRole.DisplayRole)
            if self.on_commit:
                self.on_commit(index.row(), code)


def choice_item(choices: list[tuple], code) -> "QTableWidgetItem":
    text = next((t for c, t in choices if c == code), "— choose —")
    it = QTableWidgetItem(text)
    it.setData(Qt.ItemDataRole.UserRole, code)
    it.setToolTip("Double-click to change")
    return it
