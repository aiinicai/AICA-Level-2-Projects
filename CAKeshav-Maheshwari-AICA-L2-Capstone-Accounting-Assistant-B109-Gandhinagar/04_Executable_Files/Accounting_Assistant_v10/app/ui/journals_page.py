"""Journals: clone a recurring entry, run a template, or build salary from the register."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSplitter,
                             QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)
from sqlalchemy import select

from ..db.models import Company, JournalTemplate, RecurringEntry
from ..engine import journals, recurring
from ..engine.voucher import Voucher
from ..extract.parser import parse_date
from .common import LedgerCombo, PeriodPicker, VoucherGrid, ask_lock_reason, card, dec, fmt_inr, page_layout, run_bg
from .inbox import CompanyPicker


class JournalsPage(QWidget):
    def __init__(self, st):
        super().__init__(objectName="page")
        self.st = st
        self.base: Voucher | None = None
        root = page_layout(self, "Journals", "Multi-ledger entries from your own Tally history: clone last month, "
                                             "use a template, or build salary from the register.")
        top = QHBoxLayout()
        self.picker = CompanyPicker(st)
        self.picker.hide()                       # the company switcher lives in the top bar
        self.period = PeriodPicker("journals", "History period")
        self.period.setToolTip("Which Tally entries the Clone list looks at")
        self.period.changed.connect(lambda *_: self.reload())
        top.addWidget(self.period)
        top.addStretch(1)
        root.addLayout(top)
        self.rec_current: RecurringEntry | None = None

        split = QSplitter(Qt.Orientation.Horizontal)
        self.tabs = QTabWidget()
        # -- recurring (scheduled)
        w0 = QWidget()
        l0 = QVBoxLayout(w0)
        l0.addWidget(QLabel("Scheduled entries (rent, salary, AMC, EMI). Due ones are pre-filled on the right; "
                            "check the amounts and post. Save any entry as recurring from New entry or here.",
                            objectName="muted", wordWrap=True))
        self.rec_list = QListWidget()
        self.rec_list.currentRowChanged.connect(self.pick_scheduled)
        l0.addWidget(self.rec_list, 1)
        rb = QHBoxLayout()
        b_rec_save = QPushButton("Save right side as recurring…")
        b_rec_save.clicked.connect(self.save_scheduled)
        b_rec_pause = QPushButton("Pause / resume")
        b_rec_pause.clicked.connect(self.pause_scheduled)
        b_rec_skip = QPushButton("Skip this time")
        b_rec_skip.clicked.connect(self.skip_scheduled)
        for b in (b_rec_save, b_rec_pause, b_rec_skip):
            rb.addWidget(b)
        l0.addLayout(rb)
        self.tabs.addTab(w0, "Recurring")
        # -- clone
        w1 = QWidget()
        l1 = QVBoxLayout(w1)
        self.recurring = QListWidget()
        self.recurring.currentRowChanged.connect(self.pick_recurring)
        l1.addWidget(QLabel("Journals that repeat across months (from the last 12 months in Tally):", objectName="muted",
                            wordWrap=True))
        l1.addWidget(self.recurring)
        self.tabs.addTab(w1, "Clone")
        # -- templates
        w2 = QWidget()
        l2 = QVBoxLayout(w2)
        self.templates = QListWidget()
        self.templates.currentRowChanged.connect(self.pick_template)
        b_learn = QPushButton("Learn templates from Tally history")
        b_learn.clicked.connect(self.learn)
        self.inputs_form = QFormLayout()
        self.input_edits: dict[str, QLineEdit] = {}
        b_calc = QPushButton("Calculate", objectName="primary")
        b_calc.clicked.connect(self.calc_template)
        l2.addWidget(self.templates, 1)
        l2.addWidget(b_learn)
        l2.addLayout(self.inputs_form)
        l2.addWidget(b_calc)
        self.tabs.addTab(w2, "Templates")
        # -- salary
        w3 = QWidget()
        l3 = QVBoxLayout(w3)
        b_file = QPushButton("Choose salary register (Excel/CSV)…")
        b_file.clicked.connect(self.load_register)
        self.reg_lbl = QLabel("", objectName="muted", wordWrap=True)
        self.map_table = QTableWidget(0, 4)
        self.map_table.setHorizontalHeaderLabels(["Register column", "Total", "Ledger", "Side"])
        self.map_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.map_table.verticalHeader().setVisible(False)
        prow = QHBoxLayout()
        self.payable = LedgerCombo([])
        prow.addWidget(QLabel("Balance to"))
        prow.addWidget(self.payable, 1)
        b_build = QPushButton("Build salary journal", objectName="primary")
        b_build.clicked.connect(self.build_salary)
        l3.addWidget(b_file)
        l3.addWidget(self.reg_lbl)
        l3.addWidget(self.map_table, 1)
        l3.addLayout(prow)
        l3.addWidget(b_build)
        self.tabs.addTab(w3, "Salary register")
        split.addWidget(self.tabs)

        right, rl = card("Entry")
        hr = QHBoxLayout()
        self.vtype = QComboBox()
        self.vtype.setEditable(True)
        self.date_edit = QLineEdit(date.today().strftime("%d-%m-%Y"))
        self.date_edit.setMaximumWidth(110)
        hr.addWidget(QLabel("Voucher type"))
        hr.addWidget(self.vtype, 1)
        hr.addWidget(QLabel("Date"))
        hr.addWidget(self.date_edit)
        rl.addLayout(hr)
        self.grid = VoucherGrid()
        rl.addWidget(self.grid, 1)
        nr = QHBoxLayout()
        self.narration = QLineEdit()
        nr.addWidget(QLabel("Narration"))
        nr.addWidget(self.narration, 1)
        rl.addLayout(nr)
        br = QHBoxLayout()
        b_save_t = QPushButton("Save as template")
        b_save_t.clicked.connect(self.save_as_template)
        self.b_post = QPushButton("Post to Tally", objectName="primary")
        self.b_post.clicked.connect(self.post)
        br.addWidget(b_save_t)
        br.addStretch(1)
        br.addWidget(self.b_post)
        rl.addLayout(br)
        split.addWidget(right)
        split.setSizes([420, 820])
        root.addWidget(split, 1)
        st.on_company_change(self.reload)

    def showEvent(self, e):
        self.picker.reload()
        self.reload()
        super().showEvent(e)

    # ------------------------------------------------------------------ data
    def reload(self):
        c = self.st.company()
        self.recurring.clear()
        self.templates.clear()
        if not c:
            return
        self.m = self.st.masters(c)
        names = sorted(self.m.ledgers)
        p = self.period.period()
        self.groups = [g for g in journals.recurring_vouchers(self.st.session, c.id) if p.contains(g["latest"].date)
                       or any(p.contains(v.date) for v in g["all"])]
        self._reload_scheduled()
        for g in self.groups:
            lv = g["latest"]
            self.recurring.addItem(f"{lv.narration or ', '.join(g['ledgers'][:3])}   ·   {g['months']} months, "
                                   f"last {lv.date[6:8]}-{lv.date[4:6]}-{lv.date[:4]}")
        self.tmpls = list(self.st.session.scalars(select(JournalTemplate).where(JournalTemplate.company_id == c.id)))
        for t in self.tmpls:
            self.templates.addItem(f"{t.name}   ({'learned' if t.origin == 'learned' else 'saved'})")
        self.payable.clear()
        self.payable.addItems([""] + names)
        self.payable.setCurrentText((c.settings or {}).get("salary_payable", ""))
        vts = sorted(n for n, d in self.m.voucher_types.items() if d.get("_parent") in ("Journal", n)
                     and "journal" in (d.get("_parent", "") + n).lower())
        self.vtype.clear()
        self.vtype.addItems(vts or ["Journal"])

    # ------------------------------------------------------------------ scheduled recurring entries
    def _reload_scheduled(self):
        c = self.st.company()
        self.rec_list.blockSignals(True)
        self.rec_list.clear()
        self.recs = list(self.st.session.scalars(select(RecurringEntry).where(RecurringEntry.company_id == c.id)
                                                 .order_by(RecurringEntry.next_due))) if c else []
        today = date.today().strftime("%Y%m%d")
        for r in self.recs:
            total = sum((Decimal(str(l["amount"])) for l in r.lines or [] if l["dr"]), Decimal(0))
            due = r.next_due
            state = "paused" if not r.active else ("DUE" if due <= today else "upcoming")
            it = QListWidgetItem(f"{'● ' if state == 'DUE' else ''}{r.name}   ·   {fmt_inr(total)}   ·   "
                                 f"{r.frequency}   ·   {state} {due[6:8]}-{due[4:6]}-{due[:4]}")
            if state == "DUE":
                it.setForeground(Qt.GlobalColor.darkRed)
            elif state == "paused":
                it.setForeground(Qt.GlobalColor.gray)
            self.rec_list.addItem(it)
        self.rec_list.blockSignals(False)
        due_n = sum(1 for r in self.recs if r.active and r.next_due <= today)
        self.tabs.setTabText(0, f"Recurring ({due_n} due)" if due_n else "Recurring")

    def pick_scheduled(self, i):
        if 0 <= i < len(self.recs):
            self.rec_current = self.recs[i]
            self._show(recurring.make_voucher(self.rec_current))

    def save_scheduled(self):
        c = self.st.company()
        if not c:
            return
        from PyQt6.QtWidgets import QInputDialog
        v = Voucher(vtype=self.vtype.currentText().strip() or "Journal", base_type="Journal", date=self._date(),
                    lines=self.grid.lines(), narration=self.narration.text().strip())
        if not v.lines or not v.balanced:
            QMessageBox.information(self, "Recurring", "Put a balanced entry on the right first.")
            return
        name, ok = QInputDialog.getText(self, "Recurring", "Name (e.g. Office rent):", text=v.narration[:40])
        if not ok or not name.strip():
            return
        freq, ok = QInputDialog.getItem(self, "Recurring", "Repeats", list(recurring.STEP), 0, False)
        if not ok:
            return
        day, ok = QInputDialog.getInt(self, "Recurring", "Day of the month (31 = month end)", int(v.date[6:8]), 1, 31)
        if not ok:
            return
        rec = recurring.from_voucher(c.id, name.strip(), v, freq, day)
        rec.narration = f"{name.strip()} for {{month}} {{year}}"
        self.st.session.add(rec)
        self.st.session.commit()
        self._reload_scheduled()

    def pause_scheduled(self):
        r = self.rec_current
        if r:
            r.active = not r.active
            self.st.session.commit()
            self._reload_scheduled()

    def skip_scheduled(self):
        r = self.rec_current
        if r:
            r.next_due = recurring.advance(r)
            self.st.session.commit()
            self._reload_scheduled()

    def _show(self, v: Voucher):
        self.base = v
        self.vtype.setCurrentText(v.vtype)
        self.date_edit.setText(f"{v.date[6:8]}-{v.date[4:6]}-{v.date[:4]}")
        self.narration.setText(v.narration)
        self.grid.set_voucher(v, sorted(self.m.ledgers))

    def _date(self) -> str:
        return parse_date(self.date_edit.text()) or date.today().strftime("%Y%m%d")

    # ------------------------------------------------------------------ clone
    def pick_recurring(self, i):
        self.rec_current = None
        if 0 <= i < len(self.groups):
            src = self.groups[i]["latest"]
            # default date: same day next month
            y, mth = int(src.date[:4]), int(src.date[4:6]) + 1
            y, mth = (y + 1, 1) if mth == 13 else (y, mth)
            day = min(int(src.date[6:8]), 28 if mth == 2 else 30 if mth in (4, 6, 9, 11) else 31)
            self._show(journals.clone(src, f"{y}{mth:02d}{day:02d}"))

    # ------------------------------------------------------------------ templates
    def learn(self):
        c = self.st.company()
        if not c:
            return
        made = journals.learn_templates(self.st.session, c.id)
        QMessageBox.information(self, "Templates", f"{len(made)} new template(s) learned from recurring journals." +
                                ("" if made else " (Needs a journal with the same ledgers in 3+ months.)"))
        self.reload()

    def pick_template(self, i):
        while self.inputs_form.rowCount():
            self.inputs_form.removeRow(0)
        self.input_edits = {}
        if 0 <= i < len(self.tmpls):
            for key in journals.template_inputs(self.tmpls[i].lines):
                e = QLineEdit()
                e.setAlignment(Qt.AlignmentFlag.AlignRight)
                self.input_edits[key] = e
                self.inputs_form.addRow(key, e)

    def calc_template(self):
        i = self.templates.currentRow()
        if not (0 <= i < len(self.tmpls)):
            return
        t = self.tmpls[i]
        lines = journals.evaluate(t.lines, {k: dec(e.text()) for k, e in self.input_edits.items()})
        self._show(Voucher(vtype=t.voucher_type, base_type="Journal", date=self._date(), lines=lines,
                           narration=journals.roll_narration(t.narration, 1) if t.narration else t.name))

    def save_as_template(self):
        c = self.st.company()
        lines = self.grid.lines()
        if not c or not lines:
            return
        tl = []
        bal = max(range(len(lines)), key=lambda i: (not lines[i].dr, lines[i].amount))
        for i, l in enumerate(lines):
            expr = {"type": "balance"} if i == bal else {"type": "input", "key": l.ledger}
            tl.append({"ledger": l.ledger, "side": "Dr" if l.dr else "Cr", "expr": expr})
        name = self.narration.text().strip()[:60] or "Saved journal"
        self.st.session.add(JournalTemplate(company_id=c.id, name=name, voucher_type=self.vtype.currentText(),
                                            lines=tl, narration=self.narration.text(), origin="user"))
        self.st.session.commit()
        self.reload()
        QMessageBox.information(self, "Template", f"Saved '{name}'. The largest credit is the balancing line; edit "
                                                  "other lines' amounts each time.")

    # ------------------------------------------------------------------ salary
    def load_register(self):
        p, _ = QFileDialog.getOpenFileName(self, "Salary register", "", "Excel/CSV (*.xlsx *.xlsm *.csv)")
        if not p:
            return
        try:
            cols, totals, n = journals.read_register(Path(p))
        except Exception as e:
            QMessageBox.warning(self, "Salary register", f"Could not read it: {e}")
            return
        self.reg_totals = totals
        self.reg_lbl.setText(f"{Path(p).name}: {n} employee rows, {len(cols)} numeric columns")
        saved = (self.st.company().settings or {}).get("salary_mapping", {})
        names = sorted(self.m.ledgers)
        self.map_table.setRowCount(len(cols))
        for r, col in enumerate(cols):
            self.map_table.setItem(r, 0, QTableWidgetItem(col))
            it = QTableWidgetItem(f"{totals[col]:,.2f}")
            it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.map_table.setItem(r, 1, it)
            ledger, side = saved.get(col, ("", "Dr"))
            self.map_table.setCellWidget(r, 2, LedgerCombo(names, ledger))
            sc = QComboBox()
            sc.addItems(["Dr", "Cr", "Ignore"])
            sc.setCurrentText(side if ledger else ("Ignore" if col.lower() in ("net", "net pay", "net salary",
                                                                                "days", "emp", "sr") else side))
            self.map_table.setCellWidget(r, 3, sc)

    def build_salary(self):
        c = self.st.company()
        if not c or not getattr(self, "reg_totals", None):
            QMessageBox.information(self, "Salary", "Choose the salary register first.")
            return
        mapping = {}
        for r in range(self.map_table.rowCount()):
            col = self.map_table.item(r, 0).text()
            ledger = self.map_table.cellWidget(r, 2).currentText().strip()
            side = self.map_table.cellWidget(r, 3).currentText()
            if side != "Ignore" and ledger:
                mapping[col] = (ledger, side)
        payable = self.payable.currentText().strip()
        if not payable:
            QMessageBox.information(self, "Salary", "Pick the 'Balance to' ledger (e.g. Salary Payable).")
            return
        c.settings = {**(c.settings or {}), "salary_mapping": {k: list(v) for k, v in mapping.items()},
                      "salary_payable": payable}
        self.st.session.commit()
        d = self._date()
        mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(d[4:6]) - 1]
        v = journals.salary_journal(self.reg_totals, mapping, payable, d, f"Being salary for {mon}-{d[2:4]}",
                                    self.vtype.currentText() or "Journal")
        self._show(v)

    # ------------------------------------------------------------------ post
    def post(self, override: str = ""):
        c = self.st.company()
        if not c:
            return
        v = Voucher(vtype=self.vtype.currentText().strip() or "Journal", base_type="Journal", date=self._date(),
                    lines=self.grid.lines(), narration=self.narration.text().strip())
        probs = v.problems(set(self.m.ledgers))
        if probs:
            QMessageBox.warning(self, "Can't post yet", "• " + "\n• ".join(probs))
            return
        self.b_post.setEnabled(False)
        cid = c.id
        rec = self.rec_current
        rec_id = rec.id if rec is not None and rec.next_due == v.date else (rec.id if rec is not None else None)

        def job(_p):
            s = self.st.Local()
            try:
                res = self.st.post(s, s.get(Company, cid), v, None, override,
                                   remote_id=f"rec-{rec_id}-{v.date}" if rec_id else "")
                if res.ok and rec_id:
                    r = s.get(RecurringEntry, rec_id)
                    recurring.mark_posted(s, r, v.date, {l.ledger: l.amount for l in v.lines})
                return res
            finally:
                s.close()

        def done(res):
            self.b_post.setEnabled(True)
            if res.locked:
                reason = ask_lock_reason(self, res.message)
                if reason:
                    self.post(reason)
                return
            (QMessageBox.information if res.ok else QMessageBox.warning)(self, "Tally", res.message)
            if res.ok and rec_id:
                self.st.session.expire_all()
                self.rec_current = None
                self._reload_scheduled()

        def fail(msg):
            self.b_post.setEnabled(True)
            QMessageBox.warning(self, "Posting failed", msg)

        run_bg(self, job, done, fail)
