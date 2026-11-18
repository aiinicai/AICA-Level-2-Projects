"""Claims: employee reimbursements and petty cash in bulk - folder of bills (+ optional expense sheet) ->
reviewed entries -> Tally."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QWidget)
from sqlalchemy import select

from . import theme
from .common import LedgerDelegate, ask_lock_reason, fmt_inr, page_layout, run_bg

COLS = ["", "Date", "Employee", "Supplier", "Bill no", "Description", "Amount", "GST", "Expense ledger", "Status"]
EDITABLE = {1: "date", 2: "employee", 5: "description", 6: "amount"}


class ClaimsPage(QWidget):
    def __init__(self, st):
        super().__init__()
        self.st = st
        root = page_layout(self, "Claims", "Employee reimbursements and petty cash in bulk. Pick the folder of "
                                           "bills (photos / PDFs) and, if you have it, the expense sheet. Check the "
                                           "ledgers, then post - one entry per bill.")
        r1 = QHBoxLayout()
        self.kind = QComboBox()
        self.kind.addItem("Employee reimbursement (Journal)", "reimb")
        self.kind.addItem("Petty cash (Payment from Cash)", "petty")
        self.kind.currentIndexChanged.connect(self.reload)
        self.batch = QLineEdit(f"Claims {date.today():%b %Y}")
        self.batch.setMaximumWidth(180)
        self.batch.setToolTip("Name for this lot of bills, e.g. 'Claims Oct 2026'")
        self.employee = QLineEdit()
        self.employee.setPlaceholderText("Employee (if no sheet)")
        self.employee.setMaximumWidth(170)
        b_folder = QPushButton("Read bills folder…", objectName="primary")
        b_folder.clicked.connect(self.read_folder)
        b_sheet = QPushButton("Add expense sheet…")
        b_sheet.clicked.connect(self.add_sheet)
        for w in (QLabel("Type"), self.kind, QLabel("Batch"), self.batch, self.employee, b_folder, b_sheet):
            r1.addWidget(w)
        r1.addStretch(1)
        root.addLayout(r1)
        r2 = QHBoxLayout()
        self.show_all = QCheckBox("Show posted / skipped")
        self.show_all.toggled.connect(self.reload)
        self.batch_filter = QComboBox()
        self.batch_filter.currentIndexChanged.connect(self.reload)
        self.credit_lbl = QLabel("", objectName="muted")
        r2.addWidget(QLabel("Showing"))
        r2.addWidget(self.batch_filter)
        r2.addWidget(self.show_all)
        r2.addStretch(1)
        r2.addWidget(self.credit_lbl)
        root.addLayout(r2)

        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        for i, w in ((0, 28), (1, 84), (2, 104), (3, 128), (4, 82), (6, 86), (7, 92), (8, 180), (9, 150)):
            self.table.setColumnWidth(i, w)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed |
                                   QTableWidget.EditTrigger.SelectedClicked)
        LedgerDelegate(self.table, lambda: sorted(self.m.ledgers) if getattr(self, "m", None) else [],
                       on_commit=self._ledger_set).attach(self.table, 8)
        self.table.itemChanged.connect(self._edited)
        root.addWidget(self.table, 1)
        bot = QHBoxLayout()
        self.totals = QLabel("", wordWrap=True)
        b_gst = QPushButton("GST on / off")
        b_gst.setToolTip("Claim input GST on the selected bills, or add it to the expense")
        b_gst.clicked.connect(self.toggle_gst)
        b_skip = QPushButton("Skip selected")
        b_skip.clicked.connect(lambda: self.set_status("skipped"))
        b_post = QPushButton("Post ticked to Tally", objectName="primary")
        b_post.clicked.connect(self.post)
        bot.addWidget(self.totals, 1)
        for b in (b_gst, b_skip, b_post):
            bot.addWidget(b)
        root.addLayout(bot)
        self.lines = []
        self._loading = False

    # ---------------------------------------------------------------- data
    def showEvent(self, e):
        self.reload()
        super().showEvent(e)

    def _q(self):
        from ..db.models import ClaimLine
        c = self.st.company()
        return select(ClaimLine).where(ClaimLine.company_id == c.id).order_by(ClaimLine.date, ClaimLine.updated_at)

    def reload(self):
        from ..engine import claims, masters as masters_mod
        c = self.st.company()
        if not c:
            return
        self.m = masters_mod.load(self.st.session, c.id)
        kind = self.kind.currentData()
        cred = claims.reimbursement_ledger(self.m, c) if kind == "reimb" else claims.cash_ledger(self.m)
        missing = "" if cred in self.m.ledgers else "  (not in Tally - create it first)"
        self.credit_lbl.setText(f"Credit: {cred}{missing}")
        allrows = [l for l in self.st.session.scalars(self._q()) if l.kind == kind]
        batches = sorted({l.batch for l in allrows}, reverse=True)
        cur = self.batch_filter.currentData()
        self.batch_filter.blockSignals(True)
        self.batch_filter.clear()
        self.batch_filter.addItem("All batches", "")
        for b in batches:
            self.batch_filter.addItem(b, b)
        self.batch_filter.setCurrentIndex(max(0, self.batch_filter.findData(cur)))
        self.batch_filter.blockSignals(False)
        cur = self.batch_filter.currentData()
        self.lines = [l for l in allrows if (not cur or l.batch == cur) and
                      (self.show_all.isChecked() or l.status == "new")]
        self.render()

    def render(self):
        from ..engine import claims
        self._loading = True
        t = self.table
        t.setUpdatesEnabled(False)
        t.setRowCount(len(self.lines))
        for i, l in enumerate(self.lines):
            tick = QTableWidgetItem("")
            tick.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            ready = l.status == "new" and l.expense_ledger in self.m.ledgers
            tick.setCheckState(Qt.CheckState.Checked if ready and not l.data.get("dup") else Qt.CheckState.Unchecked)
            t.setItem(i, 0, tick)
            tax = claims.dec(l.cgst) + claims.dec(l.sgst) + claims.dec(l.igst)
            vals = [f"{l.date[6:8]}-{l.date[4:6]}-{l.date[:4]}" if l.date else "", l.employee, l.supplier, l.bill_no,
                    l.description, fmt_inr(claims.dec(l.amount)),
                    (f"claim {fmt_inr(tax)}" if l.gst_claim else (f"in exp. {fmt_inr(tax)}" if tax else "–")),
                    l.expense_ledger]
            for c, v in enumerate(vals, 1):
                it = QTableWidgetItem(v)
                if c not in EDITABLE and c != 8:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if c in (6, 7):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if c == 8:
                    it.setBackground(QColor(theme.SURFACE if l.expense_ledger in self.m.ledgers else theme.WARN_BG))
                    it.setToolTip(l.data.get("why", ""))
                t.setItem(i, c, it)
            msg = {"posted": "✓ posted" + (f" (#{l.tally_id})" if l.tally_id else ""), "skipped": "skipped"}.get(
                l.status, "; ".join(([f"Possible duplicate: {l.data['dup']}"] if l.data.get("dup") else []) +
                                    list(l.issues or [])) or "ready")
            st = QTableWidgetItem(msg)
            st.setFlags(st.flags() & ~Qt.ItemFlag.ItemIsEditable)
            st.setForeground(QColor(theme.OK_FG if l.status == "posted" or msg == "ready" else theme.WARN_FG))
            st.setToolTip(msg + (f"\n{l.file_path}" if l.file_path else ""))
            t.setItem(i, 9, st)
        t.setUpdatesEnabled(True)
        self._loading = False
        self._totals()

    def _totals(self):
        from ..engine import claims
        by = claims.summary([l for l in self.lines if l.status == "new"])
        tot = sum(by.values(), Decimal(0))
        self.totals.setText(f"{sum(1 for l in self.lines if l.status == 'new')} bill(s), total {fmt_inr(tot)}" +
                            ("   ·   " + "   ".join(f"{e}: {fmt_inr(a)}" for e, a in sorted(by.items())) if by else ""))

    # ---------------------------------------------------------------- reading
    def read_folder(self):
        c = self.st.company()
        if not c:
            return
        folder = QFileDialog.getExistingDirectory(self, "Folder with the bills",
                                                  (c.settings or {}).get("claims", {}).get("folder", ""))
        if not folder:
            return
        cfg = dict(c.settings or {})
        cfg["claims"] = {**cfg.get("claims", {}), "folder": folder}
        c.settings = cfg
        self.st.session.commit()
        self._read(Path(folder))

    def _read(self, folder: Path, sheet=None):
        from ..db.models import ClaimLine, Company
        from ..engine import claims, masters as masters_mod
        from ..extract import readers
        from ..extract.pipeline import process
        c = self.st.company()
        kind, batch, emp = self.kind.currentData(), self.batch.text().strip() or "Claims", self.employee.text().strip()
        opt = self.st.extract_options(c)
        known = set(self.st.session.scalars(select(ClaimLine.file_hash).where(ClaimLine.company_id == c.id)))
        files = [p for p in sorted(folder.iterdir()) if p.is_file() and p.suffix.lower() in readers.SUPPORTED
                 and not p.name.startswith("~$")]
        win = self.st.window
        win.progress_start(f"Reading {len(files)} bill(s)…")
        cid = c.id

        def job(progress):
            s = self.st.Local()
            new = 0
            try:
                comp = s.get(Company, cid)
                m = masters_mod.load(s, cid)
                cred = claims.reimbursement_ledger(m, comp) if kind == "reimb" else claims.cash_ledger(m)
                learned = claims.learn_from_history(s, cid, cred)
                remembered = (comp.settings or {}).get("claims", {}).get("suppliers", {})
                made = []
                for k, p in enumerate(files, 1):
                    h = readers.file_hash(p)
                    if h in known:
                        continue
                    progress(f"Reading bill {k}/{len(files)}: {p.name}")
                    try:
                        res = process(p, opt)
                        cl = claims.line_from_invoice(comp, res.invoice, kind, batch, p, h)
                    except Exception as e:
                        cl = ClaimLine(company_id=cid, kind=kind, batch=batch, file_path=str(p), file_hash=h)
                        cl.issues = [f"Could not read the bill: {str(e)[:120]}"]
                    cl.employee = cl.employee or emp
                    made.append(cl)
                if sheet:
                    made += claims.match_sheet(made, sheet, comp, kind, batch)
                    for cl in made:
                        cl.employee = cl.employee or emp
                for cl in made:
                    led, why = claims.suggest_ledger(cl, m, learned, remembered)
                    cl.expense_ledger, cl.data = led, {"why": why}
                    s.add(cl)
                    s.flush()
                    dup = claims.duplicate_of(s, cl)
                    if dup:
                        cl.data = {**cl.data, "dup": dup}
                    new += 1
                s.commit()
            finally:
                s.close()
            return new

        def done(n):
            win.progress_done(f"{n} bill(s) added to {batch}")
            self.st.session.expire_all()
            self.reload()
        run_bg(self, job, done, lambda msg: (win.progress_done(""), QMessageBox.warning(self, "Claims", msg)),
               win.progress_text)

    def add_sheet(self):
        from ..engine import claims
        c = self.st.company()
        if not c:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Expense sheet", "", "Excel / CSV (*.xlsx *.xlsm *.csv)")
        if not path:
            return
        try:
            sheet = claims.read_sheet(Path(path))
        except Exception as e:
            QMessageBox.warning(self, "Claims", f"Could not read the sheet: {e}")
            return
        folder = QFileDialog.getExistingDirectory(self, "Folder with the bills for this sheet (Cancel = sheet only)",
                                                  (c.settings or {}).get("claims", {}).get("folder", ""))
        if folder:
            self._read(Path(folder), sheet)
        else:
            self._sheet_only(sheet)

    def _sheet_only(self, sheet):
        from ..engine import claims
        c = self.st.company()
        kind, batch = self.kind.currentData(), self.batch.text().strip() or "Claims"
        learned = claims.learn_from_history(self.st.session, c.id, claims.reimbursement_ledger(self.m, c))
        remembered = (c.settings or {}).get("claims", {}).get("suppliers", {})
        for cl in claims.match_sheet([], sheet, c, kind, batch):
            cl.issues = []
            cl.employee = cl.employee or self.employee.text().strip()
            led, why = claims.suggest_ledger(cl, self.m, learned, remembered)
            cl.expense_ledger, cl.data = led, {"why": why}
            self.st.session.add(cl)
            self.st.session.flush()
            dup = claims.duplicate_of(self.st.session, cl)
            if dup:
                cl.data = {**cl.data, "dup": dup}
        self.st.session.commit()
        self.reload()

    # ---------------------------------------------------------------- editing
    def _ledger_set(self, row, text):
        from ..engine import claims
        l = self.lines[row]
        l.expense_ledger = text
        if l.status == "new":
            claims.remember(self.st.company(), l)
        self.st.session.commit()
        it = self.table.item(row, 8)
        it.setBackground(QColor(theme.SURFACE if text in self.m.ledgers else theme.WARN_BG))
        self.table.item(row, 0).setCheckState(Qt.CheckState.Checked if text in self.m.ledgers
                                              else Qt.CheckState.Unchecked)

    def _edited(self, it):
        from ..engine import claims
        if self._loading or it.column() not in EDITABLE:
            return
        l = self.lines[it.row()]
        txt = it.text().strip()
        f = EDITABLE[it.column()]
        if f == "date":
            l.date = claims._ymd(txt) or l.date
        elif f == "amount":
            l.amount = str(claims.dec(txt).quantize(Decimal("0.01")))
            if not (claims.dec(l.cgst) + claims.dec(l.sgst) + claims.dec(l.igst)):
                l.taxable = l.amount
        else:
            setattr(l, f, txt)
        self.st.session.commit()
        self._loading = True
        self.render()

    def _selected(self):
        return sorted({i.row() for i in self.table.selectedIndexes()})

    def toggle_gst(self):
        from ..engine import claims
        for r in self._selected():
            l = self.lines[r]
            if claims.dec(l.cgst) + claims.dec(l.sgst) + claims.dec(l.igst):
                l.gst_claim = not l.gst_claim
        self.st.session.commit()
        self.render()

    def set_status(self, status):
        for r in self._selected():
            if self.lines[r].status == "new":
                self.lines[r].status = status
        self.st.session.commit()
        self.reload()

    # ---------------------------------------------------------------- posting
    def post(self, _=False, override: str = ""):
        from ..db.models import ClaimLine, Company
        from ..engine import claims, masters as masters_mod
        c = self.st.company()
        if not c:
            return
        rows = [i for i in range(self.table.rowCount())
                if self.table.item(i, 0).checkState() == Qt.CheckState.Checked and self.lines[i].status == "new"]
        problems = [f"{self.lines[i].supplier or self.lines[i].description}: pick an expense ledger" for i in rows
                    if self.lines[i].expense_ledger not in self.m.ledgers]
        rows = [i for i in rows if self.lines[i].expense_ledger in self.m.ledgers]
        kind = self.kind.currentData()
        cred = claims.reimbursement_ledger(self.m, c) if kind == "reimb" else claims.cash_ledger(self.m)
        if cred not in self.m.ledgers:
            QMessageBox.warning(self, "Claims", f"Ledger '{cred}' is not in Tally. Create it (e.g. under Current "
                                                f"Liabilities) and Sync, or pick it in Setup.")
            return
        if not rows:
            QMessageBox.information(self, "Claims", "Nothing ticked and ready." + ("\n\n" + "\n".join(problems[:8])
                                                                                  if problems else ""))
            return
        total = sum((claims.dec(self.lines[i].amount) for i in rows), Decimal(0))
        if not override and QMessageBox.question(
                self, "Post claims", f"Post {len(rows)} entr{'y' if len(rows) == 1 else 'ies'} to Tally "
                                     f"(total {fmt_inr(total)}, credit {cred})?") != QMessageBox.StandardButton.Yes:
            return
        ids, cid, win = [self.lines[i].id for i in rows], c.id, self.st.window
        win.progress_start("Posting claims…")

        def job(progress):
            s = self.st.Local()
            ok, failed, locked = 0, [], ""
            try:
                comp = s.get(Company, cid)
                m = masters_mod.load(s, cid)
                for k, lid in enumerate(ids, 1):
                    progress(f"Posting {k}/{len(ids)}")
                    cl = s.get(ClaimLine, lid)
                    v = claims.build_voucher(cl, m, comp)
                    res = self.st.post(s, comp, v, None, override, remote_id=f"claim-{lid}")
                    if res.locked:
                        locked = res.message
                        continue
                    if res.ok:
                        cl.status, cl.tally_id = "posted", res.tally_id or ""
                        claims.remember(comp, cl)
                        ok += 1
                    else:
                        failed.append(f"{cl.supplier or cl.description} {cl.amount}: {res.message}")
                    s.commit()
            finally:
                s.close()
            return ok, failed, locked

        def done(res):
            ok, failed, locked = res
            win.progress_done(f"{ok} claim entr{'y' if ok == 1 else 'ies'} posted")
            self.st.session.expire_all()
            self.reload()
            if locked:
                reason = ask_lock_reason(self, locked)
                if reason:
                    self.post(override=reason)
                return
            if failed or problems:
                QMessageBox.warning(self, "Claims", f"{ok} posted.\n\nNot posted:\n• " +
                                    "\n• ".join((failed + problems)[:10]))
        run_bg(self, job, done, lambda m: (win.progress_done(""), QMessageBox.warning(self, "Claims", m)),
               win.progress_text)
