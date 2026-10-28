"""Account mapping page and the dynamic questionnaire page."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QTabWidget, QTableWidget, QVBoxLayout,
                               QWidget, QGroupBox)

from ..engine import ROWS
from ..extract import to_num
from ..mapping import fs_lines, line_options
from ..questionnaire import SECTIONS, UNK, ans, visible
from . import widgets as W


# ======================================================================================================================
class MappingPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.state = win, win.state
        self._building = False
        lay = QVBoxLayout(self)
        lay.addWidget(W.heading("Step 3 - Map trial balance accounts to financial statement lines"))
        lay.addWidget(W.hint("Rules map each account by name and balance (and by the account-code convention when the balances confirm it). Anything marked 'review' or "
                             "'unmapped' needs your decision - unmapped accounts are excluded from the statements and make the balance sheet fail its check."))
        top = QHBoxLayout()
        self.filter = QComboBox()
        self.filter.addItems(["Needs review", "Unmapped only", "All accounts"])
        self.filter.currentIndexChanged.connect(self.refresh)
        self.summary = QLabel("")
        self.apply = QPushButton("Apply mapping changes")
        self.apply.clicked.connect(self.on_apply)
        self.reset = QPushButton("Clear all my overrides")
        self.reset.clicked.connect(self.on_reset)
        top.addWidget(QLabel("Show"))
        top.addWidget(self.filter)
        top.addWidget(self.summary, 1)
        top.addWidget(self.apply)
        top.addWidget(self.reset)
        lay.addLayout(top)
        self.table = W.make_table(["Code", "Account", "Net (TB ccy, Dr +)", "Net (AED, Dr +)", "Mapped to", "Method", "Review flags"], stretch_col=6)
        lay.addWidget(self.table, 1)
        self.state.analysed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        an = self.state.analysis
        self._building = True
        self.table.setRowCount(0)
        if not an:
            self.summary.setText(self.state.error or "Complete steps 1 and 2 first.")
            self._building = False
            return
        mode = self.filter.currentIndex()
        pairs = [(m, a) for m, a in zip(an.mapped, an.tr.accounts)]
        if mode == 0:
            pairs = [(m, a) for m, a in pairs if m.needs_review]
        elif mode == 1:
            pairs = [(m, a) for m, a in pairs if m.line == "UNMAPPED"]
        opts = line_options()
        lines = fs_lines()
        self.table.setRowCount(len(pairs))
        for r, (m, a) in enumerate(pairs):
            colour = "#F8CBAD" if m.line == "UNMAPPED" else ("#FFF2CC" if m.needs_review else None)
            self.table.setItem(r, 0, W.item(m.account.code, colour=colour))
            self.table.item(r, 0).setData(Qt.UserRole, m.account.key())
            self.table.setItem(r, 1, W.item(m.account.name, colour=colour))
            self.table.setItem(r, 2, W.item(W.money(m.account.net, 2), True))
            self.table.setItem(r, 3, W.item(W.money(a.net_aed, 2), True))
            cb = QComboBox()
            for k, lab in opts:
                cb.addItem(f"{lab}", k)
            cb.setCurrentIndex(max(cb.findData(m.line), 0))
            cb.currentIndexChanged.connect(lambda _i, key=m.account.key(), combo=cb: self.on_change(key, combo))
            self.table.setCellWidget(r, 4, cb)
            ovr = "override" if m.method == "override" else (m.method + (f" {m.rule_id}" if m.rule_id else "") + (" (code class)" if m.from_code else ""))
            self.table.setItem(r, 5, W.item(ovr))
            self.table.setItem(r, 6, W.item("; ".join(m.flags), tooltip="; ".join(m.flags)))
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 280)
        self.table.setColumnWidth(4, 330)
        n_unm = sum(1 for m in an.mapped if m.line == "UNMAPPED")
        n_rev = sum(1 for m in an.mapped if m.needs_review)
        diff = an.st.bs_difference
        self.summary.setText(f"{len(an.mapped)} accounts: {n_unm} unmapped, {n_rev} need review. Balance sheet difference: AED {diff:,.2f}"
                             + ("  - OK" if abs(diff) <= 0.5 else "  - DOES NOT BALANCE"))
        self._building = False

    def on_change(self, key, combo):
        if self._building:
            return
        self.state.project.mapping_overrides[key] = combo.currentData()
        self.state.project.log("Mapping override", f"{key} -> {combo.currentData()}")
        self.state.mark_dirty()
        self.apply.setStyleSheet("font-weight:bold; background:#FDC50A;")

    def on_apply(self):
        self.apply.setStyleSheet("")
        self.state.reanalyse()

    def on_reset(self):
        if W.ask(self, "Overrides", "Remove all of your mapping overrides and go back to the rule-based mapping?"):
            self.state.project.mapping_overrides.clear()
            self.state.project.log("Mapping overrides cleared")
            self.state.mark_dirty()
            self.state.reanalyse()


# ======================================================================================================================
class TableEditor(QWidget):
    """Editable table for 'table' questions. Rows come from the data (rows_from) or are added by the user."""

    def __init__(self, q, rows_ctx, value, on_change):
        super().__init__()
        self.q, self.on_change = q, on_change
        self._loading = True
        self.cols = q.columns
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.t = QTableWidget(0, len(self.cols))
        self.t.setHorizontalHeaderLabels([c["label"] for c in self.cols])
        self.t.verticalHeader().setVisible(False)
        self.fixed_rows = bool(q.rows_from)
        self._loading = True
        data = {str(r.get("account")): r for r in (value or []) if isinstance(r, dict)}
        if self.fixed_rows:
            for code, name, amt in rows_ctx or []:
                self.add_row({"account": code, "amount_aed": amt, **data.get(str(code), {})}, label=f"{code} - {name}")
        else:
            for r in value or []:
                self.add_row(r)
        self._loading = False
        self.t.itemChanged.connect(lambda *_: self.changed())
        lay.addWidget(self.t)
        self.t.setMinimumHeight(min(60 + 30 * max(self.t.rowCount(), 1), 260))
        self.t.resizeColumnsToContents()
        if not self.fixed_rows:
            h = QHBoxLayout()
            b1, b2 = QPushButton("Add row"), QPushButton("Remove selected row")
            b1.clicked.connect(lambda: (self.add_row({}), self.changed()))
            b2.clicked.connect(self.remove)
            h.addWidget(b1)
            h.addWidget(b2)
            h.addStretch(1)
            lay.addLayout(h)

    def add_row(self, vals: dict, label: str = ""):
        prev, self._loading = self._loading, True
        try:
            self._add_row(vals, label)
        finally:
            self._loading = prev

    def _add_row(self, vals: dict, label: str = ""):
        r = self.t.rowCount()
        self.t.insertRow(r)
        for c, col in enumerate(self.cols):
            k = col["id"]
            kind = col["kind"]
            if kind == "fixed":
                txt = label if k == "account" else (W.money(vals.get(k)) if isinstance(vals.get(k), (int, float)) else str(vals.get(k, "")))
                it = W.item(txt)
                it.setData(Qt.UserRole, vals.get(k))
                self.t.setItem(r, c, it)
            elif kind == "choice":
                cb = QComboBox()
                opts = col.get("options") or []
                if self.q.id == "manual_adjustments" and k == "row":
                    for key, spec in ROWS.items():
                        cb.addItem(f"{spec[2][:70]}", key)
                else:
                    for o in opts:
                        cb.addItem(o, o)
                cb.setCurrentIndex(max(cb.findData(vals.get(k)), 0) if vals.get(k) is not None else (cb.findData(UNK) if cb.findData(UNK) >= 0 else 0))
                cb.currentIndexChanged.connect(lambda *_: self.changed())
                self.t.setCellWidget(r, c, cb)
            else:
                v = vals.get(k, "")
                it = W.item("" if v in (None,) else (f"{v:g}" if isinstance(v, float) else str(v)), editable=True, align_right=(kind == "number"))
                self.t.setItem(r, c, it)

    def remove(self):
        rows = sorted({i.row() for i in self.t.selectedIndexes()}, reverse=True)
        for r in rows:
            self.t.removeRow(r)
        self.changed()

    def changed(self):
        if not self._loading:
            self.on_change(self.value())

    def value(self) -> list:
        out = []
        for r in range(self.t.rowCount()):
            row = {}
            for c, col in enumerate(self.cols):
                k, kind = col["id"], col["kind"]
                if kind == "fixed":
                    row[k] = self.t.item(r, c).data(Qt.UserRole)
                elif kind == "choice":
                    row[k] = self.t.cellWidget(r, c).currentData()
                elif kind == "number":
                    row[k] = to_num(self.t.item(r, c).text()) or 0.0
                else:
                    row[k] = self.t.item(r, c).text()
            out.append(row)
        return out


class QuestionnairePage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.state = win, win.state
        self._sig = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.state.reanalyse)
        lay = QVBoxLayout(self)
        lay.addWidget(W.heading("Step 4 - Questionnaire"))
        lay.addWidget(W.hint("Only questions relevant to this company are shown. Values marked 'prefilled / default' come from the data or a default and are NOT treated as "
                             "confirmed facts until you edit them or accept them. Leaving an item as Unknown keeps it on the open-items list - it never becomes a tax assumption."))
        top = QHBoxLayout()
        self.progress = QLabel("")
        self.accept = QPushButton("Accept all prefilled / default answers as shown")
        self.accept.clicked.connect(self.accept_prefilled)
        top.addWidget(self.progress, 1)
        top.addWidget(self.accept)
        lay.addLayout(top)
        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)
        self.state.analysed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        an = self.state.analysis
        if not an:
            self.tabs.clear()
            self._sig = None
            self.progress.setText(self.state.error or "Complete steps 1 and 2 first.")
            return
        vis = visible(an.answers, an.ctx)
        sig = (tuple(q.id for q in vis), tuple(len(an.ctx.get(q.rows_from, [])) for q in vis if q.rows_from))
        from ..questionnaire import unanswered
        self.progress.setText(f"{len(unanswered(an.answers, an.ctx))} required question(s) still unanswered or 'Unknown'.")
        if sig == self._sig:
            return
        self._sig = sig
        cur = self.tabs.currentIndex()
        self.tabs.clear()
        meta = an.answers.get("_meta", {})
        for sec, title in SECTIONS.items():
            qs = [q for q in vis if q.section == sec]
            if not qs:
                continue
            body = QWidget()
            bl = QVBoxLayout(body)
            for q in qs:
                bl.addWidget(self.question_box(q, an, meta))
            bl.addStretch(1)
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setWidget(body)
            self.tabs.addTab(sa, f"{sec}. {title}")
        if 0 <= cur < self.tabs.count():
            self.tabs.setCurrentIndex(cur)

    # ---------------------------------------------------------------- one question
    def question_box(self, q, an, meta) -> QWidget:
        box = QGroupBox()
        lay = QVBoxLayout(box)
        m = meta.get(q.id)
        tag = ""
        if q.id not in self.state.project.answers:
            tag = "  [prefilled / default - not confirmed]" if m else ("  [required]" if q.required else "")
        lab = QLabel(f"<b>{q.text}</b>{'' if q.required else ' <i>(optional)</i>'}<span style='color:#C00000'>{tag}</span>")
        lab.setWordWrap(True)
        lay.addWidget(lab)
        sub = " ".join(x for x in [q.why, f"Evidence: {q.evidence}" if q.evidence else "", m.get("note", "") if m else ""] if x)
        if sub:
            lay.addWidget(W.hint(sub))
        val = ans(an.answers, q.id)
        raw = an.answers.get(q.id)
        if isinstance(raw, dict) and "value" in raw:
            raw = raw["value"]
        lay.addWidget(self.editor(q, an, raw if raw is not None else val))
        return box

    def editor(self, q, an, value) -> QWidget:
        k = q.kind
        if k == "text" or k == "date":
            w = QLineEdit("" if value in (None,) else str(value))
            if k == "date":
                w.setPlaceholderText("YYYY-MM-DD")
            w.editingFinished.connect(lambda: self.set_answer(q.id, w.text().strip()))
            return w
        if k == "number":
            w = W.money_spin()
            w.setValue(float(value or 0.0))
            w.editingFinished.connect(lambda: self.set_answer(q.id, w.value()))
            return w
        if k == "choice":
            w = QComboBox()
            w.addItems(q.options)
            i = w.findText(str(value)) if value is not None else -1
            w.setCurrentIndex(i if i >= 0 else 0)
            w.activated.connect(lambda _i: self.set_answer(q.id, w.currentText()))
            return w
        if k == "multi":
            holder = QWidget()
            hl = QVBoxLayout(holder)
            hl.setContentsMargins(0, 0, 0, 0)
            boxes = []
            cur = set(value or [])
            for o in q.options:
                cb = QCheckBox(o)
                cb.setChecked(o in cur)
                cb.toggled.connect(lambda *_: self.set_answer(q.id, [b.text() for b in boxes if b.isChecked()]))
                boxes.append(cb)
                hl.addWidget(cb)
            return holder
        if k == "table":
            rows_ctx = an.ctx.get(q.rows_from, []) if q.rows_from else None
            return TableEditor(q, rows_ctx, value, lambda v: self.set_answer(q.id, v))
        return QLabel("(unsupported question type)")

    # ---------------------------------------------------------------- saving
    def set_answer(self, qid, value):
        p = self.state.project
        if p.answers.get(qid) == value:
            return
        p.answers[qid] = value
        p.answers.setdefault("_meta", {})[qid] = {"source": "user", "confirmed": True, "note": ""}
        p.log("Answer", f"{qid} = {str(value)[:120]}")
        self.state.mark_dirty()
        self._timer.start(900)

    def accept_prefilled(self):
        an = self.state.analysis
        if not an:
            return
        p = self.state.project
        n = 0
        for qid, meta in list(an.answers.get("_meta", {}).items()):
            if qid not in p.answers and qid in an.answers:
                p.answers[qid] = an.answers[qid]
                p.answers.setdefault("_meta", {})[qid] = {"source": meta.get("source", "prefilled"), "confirmed": True, "note": "accepted by user"}
                n += 1
        p.log("Prefilled answers accepted", f"{n} answer(s)")
        self.state.mark_dirty()
        self._sig = None
        self.state.reanalyse()
