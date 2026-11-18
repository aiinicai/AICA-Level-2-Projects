"""Compliance: TDS tracker, GST control panel, AP/AR ageing (v7). Close checklist and global search live here
too as their own pages."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QSplitter,
                             QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from ..engine import compliance
from . import theme
from .common import ChoiceDelegate, PeriodPicker, choice_item, fmt_inr, page_layout, run_bg


def _d(s: str) -> str:
    return f"{s[6:8]}-{s[4:6]}-{s[:4]}" if s and len(s) >= 8 else ""


def _table(headers: list[str], stretch: int = 0) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.horizontalHeader().setSectionResizeMode(stretch, QHeaderView.ResizeMode.Stretch)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    t.setAlternatingRowColors(True)
    return t


def _fill(t: QTableWidget, rows: list[list], money_cols=(), colours: list | None = None):
    t.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            txt = fmt_inr(v) if c in money_cols and v is not None and v != "" else ("" if v is None else str(v))
            it = QTableWidgetItem(txt)
            it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if c in money_cols:
                it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if colours and colours[r]:
                it.setForeground(QColor(colours[r]))
            t.setItem(r, c, it)


class CompliancePage(QWidget):
    def __init__(self, st):
        super().__init__(objectName="page")
        self.st = st
        root = page_layout(self, "Compliance", "TDS, GST and outstanding bills for the period - from your Tally "
                                               "entries. Nothing here blocks posting.")
        top = QHBoxLayout()
        self.period = PeriodPicker("compliance")
        self.period.changed.connect(lambda *_: self.load())
        top.addWidget(self.period)
        top.addStretch(1)
        self.status = QLabel("", objectName="muted")
        top.addWidget(self.status)
        b = QPushButton("Refresh", objectName="primary")
        b.clicked.connect(self.load)
        top.addWidget(b)
        root.addLayout(top)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # --- TDS
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)
        self.tds_sum = QLabel("", objectName="h2")
        lay.addWidget(self.tds_sum)
        sp = QSplitter(Qt.Orientation.Vertical)
        self.tds_months = _table(["Section", "Month", "Deducted", "Deposited", "Unpaid", "Due date", "Status"], 6)
        self.tds_near = _table(["Party (no TDS yet this FY)", "Section (change or Not applicable)",
                                "Credited this FY", "Yearly limit", ""], 0)
        self.tds_near.setColumnWidth(1, 300)
        self.tds_near.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked |
                                      QTableWidget.EditTrigger.SelectedClicked |
                                      QTableWidget.EditTrigger.EditKeyPressed)
        self.tds_near.setItemDelegateForColumn(1, ChoiceDelegate(
            self.tds_near, self._sec_choices(),
            lambda row, code: self._set_section(self._near_parties[row], code)))
        box = QWidget()
        bl = QVBoxLayout(box)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(QLabel("Challans: deducted vs deposited", objectName="section"))
        bl.addWidget(self.tds_months)
        box2 = QWidget()
        bl2 = QVBoxLayout(box2)
        bl2.setContentsMargins(0, 0, 0, 0)
        bl2.addWidget(QLabel("Parties nearing the TDS limit (80% or more) with no TDS deducted", objectName="section"))
        bl2.addWidget(self.tds_near)
        sp.addWidget(box)
        sp.addWidget(box2)
        lay.addWidget(sp, 1)
        br = QHBoxLayout()
        br.addWidget(QLabel("Section comes from Company settings → TDS ledgers, or from the ledger name "
                            "(e.g. 'TDS Payable 194J'). Verify rates and section codes under the Income-tax Act "
                            "2025 before filing.", objectName="muted", wordWrap=True), 1)
        bsec = QPushButton("Party TDS sections…")
        bsec.setToolTip("Set the section (or Not applicable) for every supplier, once")
        bsec.clicked.connect(self.party_sections)
        br.addWidget(bsec)
        b26 = QPushButton("Export 26Q data (Excel)")
        b26.clicked.connect(self.export_26q)
        br.addWidget(b26)
        lay.addLayout(br)
        self.tabs.addTab(w, "TDS tracker")

        # --- GST
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)
        self.gst_sum = QLabel("", objectName="h2", wordWrap=True)
        lay.addWidget(self.gst_sum)
        self.gst_tabs = QTabWidget()
        self.g_rev = _table(["Supplier", "Bill", "Bill date", "Days", "Unpaid", "GST to reverse"], 0)
        self.g_rcm = _table(["Date", "Voucher", "RCM ledger", "Liability"], 2)
        self.g_blk = _table(["Date", "Supplier", "Invoice", "GST (blocked)"], 1)
        self.g_2b = _table(["2B status", "Supplier", "Invoice", "Invoice total"], 1)
        for t, name in ((self.g_rev, "ITC reversal (180 days unpaid)"), (self.g_rcm, "RCM liability"),
                        (self.g_blk, "Blocked credit 17(5)"), (self.g_2b, "2B mismatches")):
            self.gst_tabs.addTab(t, name)
        lay.addWidget(self.gst_tabs, 1)
        lay.addWidget(QLabel("Rule 37: ITC of a bill not paid within 180 days of the invoice date is reversed (and "
                             "re-claimed when paid). Each supplier's actual ledger balance is matched to its newest "
                             "bills first, so payments entered On Account still count. Hover a row for the working.",
                             objectName="muted", wordWrap=True))
        self.tabs.addTab(w, "GST control")

        # --- Ageing
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)
        ar = QHBoxLayout()
        self.age_kind = QComboBox()
        self.age_kind.addItems(["Receivables (debtors)", "Payables (creditors)"])
        self.age_kind.currentIndexChanged.connect(lambda *_: self._render_ageing())
        ar.addWidget(self.age_kind)
        ar.addStretch(1)
        self.b_remind = QPushButton("Draft reminder…")
        self.b_remind.setToolTip("Drafts an email for the selected party - you send it yourself")
        self.b_remind.clicked.connect(self.draft_reminder)
        self.b_age_xl = QPushButton("Export to Excel")
        self.b_age_xl.clicked.connect(self.export_ageing)
        ar.addWidget(self.b_remind)
        ar.addWidget(self.b_age_xl)
        lay.addLayout(ar)
        self.age = _table(["Party", "Total"] + [b[0] + " days" for b in compliance.BUCKETS], 0)
        self.age.cellDoubleClicked.connect(lambda r, _c: self.draft_reminder())
        lay.addWidget(self.age, 1)
        self.age_sum = QLabel("", objectName="muted")
        lay.addWidget(self.age_sum)
        self.tabs.addTab(w, "Ageing (AP / AR)")
        st.on_company_change(self.load)
        self.bills = None
        self._loaded = None

    def showEvent(self, e):
        c = self.st.company()
        if c and self._loaded != (c.id, self.st.version(c.id)):
            self.load()
        super().showEvent(e)

    # ------------------------------------------------------------------ data
    def load(self):
        c = self.st.company()
        if not c:
            return
        self._loaded = (c.id, self.st.version(c.id))
        self.m = self.st.masters(c)
        p = self.period.period()
        self.rep = compliance.tds_tracker(self.st.session, c, self.m, p)
        self._render_tds()
        self.status.setText("Reading bills from Tally…")
        client, cname = self.st.client(c), c.name

        def done(bills):
            self.bills = bills
            self.status.setText("✓ Bills live from Tally")
            self._render_gst()
            self._render_ageing()

        def fail(msg):
            self.bills = None
            self.status.setText(f"Tally not reachable - bills not shown ({msg[:60]})")
            self._render_gst()
            self._render_ageing()
        from ..engine.periods import fy_start
        to = min(date.today(), p.end)
        frm = fy_start(to).strftime("%Y%m%d")

        def job(_p):
            bills = client.bills(cname)
            try:
                self.closings = client.ledger_closings(cname, frm, to.strftime("%Y%m%d"))
            except Exception:
                self.closings = None
            return bills
        run_bg(self, job, done, fail)

    def _render_tds(self):
        r = self.rep
        today = date.today().strftime("%Y%m%d")
        rows, cols = [], []
        for mo in r.months:
            late = mo.unpaid and mo.due < today
            from ..engine import tds_map
            rows.append([tds_map.label(mo.section, mo.month + "01"), f"{mo.month[4:6]}-{mo.month[:4]}", mo.deducted,
                         mo.paid, mo.unpaid, _d(mo.due),
                         "OVERDUE - pay with interest" if late else ("Due" if mo.unpaid else "✓ Deposited")])
            cols.append(theme.ERR_FG if late else (theme.WARN_FG if mo.unpaid else ""))
        _fill(self.tds_months, rows, (2, 3, 4), cols)
        _fill(self.tds_near, [[p, "", a, l, {"set": "set by you", "vendor": "supplier setting",
                                             "guess": "guessed"}.get(src, "unknown")]
                              for p, s, a, l, src in r.near_threshold], (2, 3))
        self._near_parties = [x[0] for x in r.near_threshold]
        for row, (p, sec, _a, _l, _src) in enumerate(r.near_threshold):
            it = choice_item(self._sec_choices(), sec)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsEditable)
            self.tds_near.setItem(row, 1, it)
        t = r.totals
        self.tds_sum.setText(f"Deducted {fmt_inr(t['deducted'])}  ·  Deposited {fmt_inr(t['paid'])}  ·  "
                             f"Overdue {fmt_inr(t['overdue'])}  ·  {len(r.near_threshold)} part(ies) near the limit")
        self.tds_sum.setStyleSheet(f"color: {theme.ERR_FG if t['overdue'] else theme.INK};")

    @staticmethod
    def _sec_choices() -> list:
        from ..engine import tds_map
        return [("", "— choose —")] + tds_map.choices()

    def _section_combo(self, party: str, code: str) -> QComboBox:
        from ..engine import tds_map
        cb = QComboBox()
        cb.addItem("— choose —", "")
        for k, txt in tds_map.choices():
            cb.addItem(txt, k)
        cb.setCurrentIndex(max(0, cb.findData(code)))
        cb.currentIndexChanged.connect(lambda _i, p=party, c=cb: self._set_section(p, c.currentData()))
        return cb

    def _set_section(self, party: str, code: str):
        if not code:
            return
        compliance.set_party_section(self.st.session, self.st.company(), party, code)
        self.st.window.toast(f"✓ {party}: TDS {('Not applicable' if code == 'NA' else code)} - remembered")

    def party_sections(self):
        c = self.st.company()
        if not c:
            return
        secs = compliance.party_sections(self.st.session, c, self.m)
        dlg = QDialog(self)
        dlg.setWindowTitle("Party TDS sections")
        dlg.resize(820, 600)
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel("Guessed from the expense ledgers each supplier is booked against. Change any - it is "
                             "remembered for this company and used in the tracker and in invoice suggestions.",
                             objectName="muted", wordWrap=True))
        t = _table(["Supplier", "Section", "Source"], 0)
        t.setColumnWidth(1, 330)
        parties = sorted(p for p in secs if self.m.ledgers.get(p, {}).get("_primary") == "Sundry Creditors")
        t.setRowCount(len(parties))
        t.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.SelectedClicked |
                          QTableWidget.EditTrigger.EditKeyPressed)
        t.setItemDelegateForColumn(1, ChoiceDelegate(t, self._sec_choices(),
                                                     lambda row, code: self._set_section(parties[row], code)))
        for r, p in enumerate(parties):
            code, src = secs[p]
            pi = QTableWidgetItem(p)
            pi.setFlags(pi.flags() & ~Qt.ItemFlag.ItemIsEditable)
            t.setItem(r, 0, pi)
            it = choice_item(self._sec_choices(), code)
            t.setItem(r, 1, it)
            t.setItem(r, 2, QTableWidgetItem({"set": "set by you", "vendor": "supplier setting",
                                              "guess": "guessed"}.get(src, "unknown")))
        lay.addWidget(t, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        dlg.exec()
        self.load()

    def _render_gst(self):
        c = self.st.company()
        p = compliance.gst_panel(self.st.session, c, self.m, self.period.period(), self.bills,
                                 closings=getattr(self, "closings", None))
        _fill(self.g_rev, [[a, b, _d(cdt), days, amt, gst if gst is not None else "not in app"]
                           for a, b, cdt, days, amt, gst, _w in p.reversal_180], (4, 5))
        for r, row in enumerate(p.reversal_180):
            for col in range(6):
                if self.g_rev.item(r, col):
                    self.g_rev.item(r, col).setToolTip(row[6])
        _fill(self.g_rcm, [[_d(d), v, l, a] for d, v, l, a in p.rcm], (3,))
        _fill(self.g_blk, [[_d(d), s, n, g] for d, s, n, g in p.blocked], (3,))
        _fill(self.g_2b, [[st.replace("_", " "), s, n, t] for st, s, n, t in p.b2b_rows], (3,))
        t = p.totals
        b2b = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in sorted(p.b2b.items())) or "no invoices"
        self.gst_sum.setText(f"To reverse (Rule 37): {len(p.reversal_180)} bill(s), GST {fmt_inr(t['reversal_gst'])}"
                             f"  ·  RCM liability {fmt_inr(t['rcm'])}  ·  Blocked 17(5) {fmt_inr(t['blocked'])}"
                             f"  ·  2B: {b2b}" + ("" if self.bills is not None else "  ·  (Tally offline: Rule 37 "
                                                                                    "needs live bills)"))

    def _render_ageing(self):
        if self.bills is None:
            self.age.setRowCount(0)
            self.age_sum.setText("Bills come live from Tally - connect Tally and Refresh.")
            return
        rec = self.age_kind.currentIndex() == 0
        self.age_rows = compliance.ageing(self.bills, self.m, rec)
        _fill(self.age, [[r.party, r.total] + r.buckets for r in self.age_rows],
              tuple(range(1, 2 + len(compliance.BUCKETS))))
        tot = sum((r.total for r in self.age_rows), Decimal(0))
        old = sum((r.buckets[-1] for r in self.age_rows), Decimal(0))
        self.age_sum.setText(f"{len(self.age_rows)} part(ies) · total {fmt_inr(tot)} · over 180 days {fmt_inr(old)}"
                             f" · double-click a party to draft a reminder")
        self.b_remind.setText("Draft reminder…" if rec else "Payment schedule…")

    # ------------------------------------------------------------------ actions
    def export_26q(self):
        c = self.st.company()
        if not c:
            return
        p = self.period.period()
        path, _ = QFileDialog.getSaveFileName(self, "26Q data", f"{c.name} - TDS {p.frm}-{p.to}.xlsx".replace("/", "-"),
                                              "Excel (*.xlsx)")
        if path:
            compliance.export_26q(self.rep, Path(path), c.name, p.text())
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def export_ageing(self):
        if not getattr(self, "age_rows", None):
            return
        c = self.st.company()
        path, _ = QFileDialog.getSaveFileName(self, "Ageing", f"{c.name} - Ageing.xlsx".replace("/", "-"),
                                              "Excel (*.xlsx)")
        if not path:
            return
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append([c.name, self.age_kind.currentText(), f"as on {date.today():%d-%m-%Y}"])
        ws.append(["Party", "Total"] + [b[0] for b in compliance.BUCKETS])
        for r in self.age_rows:
            ws.append([r.party, float(r.total)] + [float(x) for x in r.buckets])
        ws2 = wb.create_sheet("Bills")
        ws2.append(["Party", "Bill", "Date", "Days", "Amount"])
        for r in self.age_rows:
            for n, d, days, a in r.bills:
                ws2.append([r.party, n, _d(d), days, float(a)])
        ws.column_dimensions["A"].width = 40
        wb.save(path)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def draft_reminder(self):
        r = self.age.currentRow()
        if r < 0 or not getattr(self, "age_rows", None):
            QMessageBox.information(self, "Reminder", "Select a party first.")
            return
        row = self.age_rows[r]
        subj, body = compliance.reminder_text(self.st.company().name, row, self.age_kind.currentIndex() == 0)
        ReminderDialog(subj, body, self).exec()


class ReminderDialog(QDialog):
    """Drafted, never sent automatically: copy it or open it in your mail app."""

    def __init__(self, subject: str, body: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Draft")
        self.resize(640, 520)
        lay = QVBoxLayout(self)
        self.to = QLineEdit()
        self.to.setPlaceholderText("To (email)")
        self.subj = QLineEdit(subject)
        self.body = QPlainTextEdit(body)
        lay.addWidget(self.to)
        lay.addWidget(self.subj)
        lay.addWidget(self.body, 1)
        br = QHBoxLayout()
        bc = QPushButton("Copy")
        bc.clicked.connect(lambda: QApplication.clipboard().setText(f"{self.subj.text()}\n\n{self.body.toPlainText()}"))
        bm = QPushButton("Open in mail app", objectName="primary")
        bm.clicked.connect(self.open_mail)
        br.addWidget(QLabel("Nothing is sent from here.", objectName="muted"))
        br.addStretch(1)
        br.addWidget(bc)
        br.addWidget(bm)
        lay.addLayout(br)

    def open_mail(self):
        from urllib.parse import quote
        QDesktopServices.openUrl(QUrl(f"mailto:{self.to.text().strip()}?subject={quote(self.subj.text())}"
                                      f"&body={quote(self.body.toPlainText())}"))


# ====================================================================== close checklist
class ClosePage(QWidget):
    def __init__(self, st):
        super().__init__(objectName="page")
        self.st = st
        root = page_layout(self, "Month-end close", "One checklist per company and month. The app ticks what it can "
                                                    "see; you tick the rest. Everyone in the office sees the same "
                                                    "list.")
        top = QHBoxLayout()
        top.addWidget(QLabel("Month", objectName="muted"))
        self.month = QComboBox()
        t = date.today()
        for i in range(0, 15):
            y, m = t.year, t.month - i
            while m <= 0:
                m += 12
                y -= 1
            self.month.addItem(date(y, m, 1).strftime("%B %Y"), f"{y}{m:02d}")
        self.month.setCurrentIndex(1 if t.day <= 20 else 0)
        self.month.currentIndexChanged.connect(lambda *_: self.load())
        top.addWidget(self.month)
        top.addStretch(1)
        self.summary = QLabel("", objectName="h2")
        top.addWidget(self.summary)
        root.addLayout(top)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Done", "Step", "What the app sees", "Ticked by", "Note"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 56)
        self.table.setColumnWidth(3, 170)
        self.table.setColumnWidth(4, 180)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.itemChanged.connect(self._note_changed)
        root.addWidget(self.table, 1)
        st.on_company_change(self.load)

    def showEvent(self, e):
        self.load()
        super().showEvent(e)

    def load(self):
        c = self.st.company()
        if not c:
            return
        self.items = compliance.close_status(self.st.session, c, self.st.masters(c), self.month.currentData())
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.items))
        for r, it in enumerate(self.items):
            chk = QCheckBox()
            chk.setChecked(it.done)
            chk.setStyleSheet("margin-left: 18px;")
            chk.toggled.connect(lambda on, key=it.key: self._tick(key, on))
            self.table.setCellWidget(r, 0, chk)
            auto = {"ok": ("✓ ", theme.OK_FG), "pending": ("● ", theme.WARN_FG), "n/a": ("", theme.MUTED)}[it.auto]
            for col, val in ((1, it.label), (2, auto[0] + it.detail),
                             (3, f"{it.by} · {it.at}" if it.done else ""), (4, it.note)):
                cell = QTableWidgetItem(val)
                if col != 4:
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 2:
                    cell.setForeground(QColor(auto[1]))
                self.table.setItem(r, col, cell)
        self.table.blockSignals(False)
        done = sum(1 for i in self.items if i.done)
        self.summary.setText(f"{done} of {len(self.items)} done")

    def _tick(self, key: str, on: bool):
        c = self.st.company()
        row = next(i for i, it in enumerate(self.items) if it.key == key)
        note = self.table.item(row, 4).text() if self.table.item(row, 4) else ""
        compliance.set_close(self.st.session, c, self.month.currentData(), key, on, self.st.actor, note)
        self.load()

    def _note_changed(self, item):
        if item.column() != 4:
            return
        it = self.items[item.row()]
        compliance.set_close(self.st.session, self.st.company(), self.month.currentData(), it.key, it.done,
                             self.st.actor if it.done else "", item.text())


# ====================================================================== global search
class SearchPage(QWidget):
    def __init__(self, st):
        super().__init__(objectName="page")
        self.st = st
        root = page_layout(self, "Search", "Across all companies on this PC: amount, bill / invoice no., party, "
                                           "GSTIN, narration. Double-click a result to open it.")
        top = QHBoxLayout()
        self.q = QLineEdit()
        self.q.setPlaceholderText("Type an amount (e.g. 11800), a bill no., a party name or a GSTIN…")
        self.q.returnPressed.connect(self.run)
        b = QPushButton("Search", objectName="primary")
        b.clicked.connect(self.run)
        top.addWidget(self.q, 1)
        top.addWidget(b)
        root.addLayout(top)
        self.table = _table(["Company", "Type", "Date", "Details", "Amount"], 3)
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(2, 96)
        self.table.setColumnWidth(4, 120)
        self.table.cellDoubleClicked.connect(self.open)
        root.addWidget(self.table, 1)
        self.info = QLabel("", objectName="muted")
        root.addWidget(self.info)
        self.hits = []

    def start(self, text: str = ""):
        if text:
            self.q.setText(text)
            self.run()
        self.q.setFocus()
        self.q.selectAll()

    def run(self):
        self.hits = compliance.search(self.st.session, self.q.text())
        _fill(self.table, [[h.company, h.kind, _d(h.date), h.text, h.amount] for h in self.hits], (4,))
        self.info.setText(f"{len(self.hits)} result(s)" + (" (first 300)" if len(self.hits) >= 300 else ""))

    def open(self, row, _col):
        h = self.hits[row]
        win = self.st.window
        if self.st.company_id != h.company_id:
            self.st.set_company(h.company_id)
        if h.kind == "Invoice":
            win.go_page("Workbench")
            win.workbench.queue.set_filter("all")
            win.workbench.refresh(h.ref.id)
        elif h.kind == "Voucher":
            from .reports_page import VoucherView
            v = h.ref
            VoucherView(self.st, self.st.company(), dict(guid=v.guid, masterid=v.masterid, date=v.date,
                                                         voucher_type=v.voucher_type, number=v.number,
                                                         narration=v.narration, reference=v.reference,
                                                         entries=v.entries), self).exec()
        elif h.kind == "Bank line":
            win.go_page("Bank")
            win.bank.bank_combo.setCurrentText(h.ref.bank_ledger)
            win.bank.set_filter("all")
        else:
            QMessageBox.information(self, "Ledger", h.text)
