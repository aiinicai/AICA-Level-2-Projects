"""Red flags repository: suspicious-transaction indicators, party risk scores, related parties, thresholds."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                             QFormLayout, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
                             QPlainTextEdit, QPushButton, QSpinBox, QSplitter, QTableWidget, QTableWidgetItem,
                             QTabWidget, QVBoxLayout, QWidget)

from ..engine import redflags
from . import theme
from .common import LedgerCombo, PeriodPicker, fmt_inr, page_layout, run_bg

SEV = {"high": ("High", theme.ERR_FG, theme.ERR_BG), "medium": ("Medium", theme.WARN_FG, theme.WARN_BG),
       "low": ("Low", theme.INFO_FG, theme.INFO_BG)}
STATUS = {"open": "Open", "explained": "Explained", "false_positive": "False positive"}


def _fmt(s: str) -> str:
    return f"{s[6:8]}-{s[4:6]}-{s[:4]}" if s and len(s) >= 8 else ""


class RedFlagsPage(QWidget):
    def __init__(self, st):
        super().__init__(objectName="page")
        self.st = st
        self.flags: list = []
        root = page_layout(self, "Red flags", "")
        root.itemAt(0).widget().setToolTip("Suspicious-transaction indicators from the books, bank statements and "
                                           "invoices. Indicators for review, not conclusions.")
        top = QHBoxLayout()
        self.period = PeriodPicker("redflags")
        top.addWidget(self.period)
        top.addStretch(1)
        self.status = QLabel("", objectName="muted")
        top.addWidget(self.status)
        b_th = QPushButton("Thresholds…")
        b_th.clicked.connect(self.edit_thresholds)
        b_xl = QPushButton("Export to Excel")
        b_xl.clicked.connect(self.export)
        b_run = QPushButton("Run checks", objectName="primary")
        b_run.clicked.connect(self.run)
        for b in (b_th, b_xl, b_run):
            top.addWidget(b)
        root.addLayout(top)

        # summary tiles (compact)
        tiles = QHBoxLayout()
        tiles.setSpacing(8)
        self.tiles = {}
        for key, label, colour in (("high", "High", theme.ERR_FG), ("medium", "Medium", theme.WARN_FG),
                                   ("low", "Low", theme.INFO_FG), ("closed", "Reviewed", theme.OK_FG)):
            f = QFrame(objectName="tile")
            f.setStyleSheet(f"QFrame#tile {{ background: {theme.SURFACE}; border: 1px solid {theme.LINE}; "
                            f"border-left: 4px solid {colour}; border-radius: 10px; }}")
            lay = QHBoxLayout(f)
            lay.setContentsMargins(12, 4, 12, 4)
            n = QLabel("–")
            n.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {colour};")
            lay.addWidget(n)
            lay.addWidget(QLabel(label, objectName="muted"))
            lay.addStretch(1)
            tiles.addWidget(f)
            self.tiles[key] = n
        root.addLayout(tiles)

        self.tabs = QTabWidget()
        # --- flags
        w = QWidget()
        wl = QVBoxLayout(w)
        wl.setContentsMargins(0, 8, 0, 0)
        fl = QHBoxLayout()
        self.f_group = QComboBox()
        self.f_group.addItem("All groups", "")
        for k, v in redflags.GROUP_NAMES.items():
            self.f_group.addItem(f"{k} · {v}", k)
        self.f_sev = QComboBox()
        self.f_sev.addItems(["All severities", "High", "Medium", "Low"])
        self.f_status = QComboBox()
        self.f_status.addItems(["Open", "All", "Explained", "False positive"])
        self.f_text = QLineEdit()
        self.f_text.setPlaceholderText("Find party / text…")
        for wdg in (self.f_group, self.f_sev, self.f_status):
            wdg.currentIndexChanged.connect(self.render)
            fl.addWidget(wdg)
        self.f_text.textChanged.connect(self.render)
        fl.addWidget(self.f_text, 1)
        wl.addLayout(fl)
        sp = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Severity", "Rule", "Flag", "Party", "Date", "Amount", "Status"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for c, wd in ((0, 76), (1, 50), (3, 170), (4, 90), (5, 110), (6, 100)):
            self.table.setColumnWidth(c, wd)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.show_detail)
        sp.addWidget(self.table)
        det = QFrame(objectName="card")
        outer_d = QHBoxLayout(det)
        outer_d.setContentsMargins(14, 10, 14, 10)
        dleft, dright = QVBoxLayout(), QVBoxLayout()
        outer_d.addLayout(dleft, 3)
        outer_d.addLayout(dright, 2)
        dl = dleft
        self.d_title = QLabel("Select a flag", objectName="h2", wordWrap=True)
        self.d_body = QLabel("", wordWrap=True)
        self.d_body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.d_law = QLabel("", objectName="muted", wordWrap=True)
        self.d_refs = QPlainTextEdit(readOnly=True)
        self.d_refs.setMaximumHeight(120)
        self.d_note = QLineEdit()
        self.d_note.setPlaceholderText("Reviewer's note (why it's fine / what was done)")
        self.d_all = QCheckBox("Same rule for this party: don't flag again")
        br = QHBoxLayout()
        b_ok = QPushButton("Explained", objectName="primary")
        b_fp = QPushButton("False positive")
        b_re = QPushButton("Reopen")
        b_ok.clicked.connect(lambda: self.set_status("explained"))
        b_fp.clicked.connect(lambda: self.set_status("false_positive"))
        b_re.clicked.connect(lambda: self.set_status("open"))
        for b in (b_ok, b_fp, b_re):
            br.addWidget(b)
        self.d_rev = QLabel("", objectName="muted")
        for wdg in (self.d_title, self.d_body, self.d_law):
            dleft.addWidget(wdg)
        dleft.addStretch(1)
        for wdg in (QLabel("Evidence", objectName="section"), self.d_refs, self.d_note, self.d_all):
            dright.addWidget(wdg)
        dright.addLayout(br)
        dright.addWidget(self.d_rev)
        self.d_refs.setMaximumHeight(70)
        sp.addWidget(det)
        sp.setSizes([300, 200])
        wl.addWidget(sp, 1)
        self.tabs.addTab(w, "Flags")
        # --- party risk
        self.scores = QTableWidget(0, 4)
        self.scores.setHorizontalHeaderLabels(["Party", "Risk score", "Open flags", "Groups"])
        self.scores.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.scores.verticalHeader().setVisible(False)
        self.scores.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.scores.cellDoubleClicked.connect(self._party_filter)
        self.tabs.addTab(self.scores, "Party risk")
        # --- related parties
        self.rp = RelatedPartiesWidget(st, self.period)
        self.tabs.addTab(self.rp, "Related parties")
        root.addWidget(self.tabs, 1)
        st.on_company_change(self._clear)

    def _clear(self):
        self.flags = []
        self.render()
        self.status.setText("Pick a period and Run checks")
        self.rp.reload()

    def showEvent(self, e):
        c = self.st.company()
        if c and (not self.flags or getattr(self, "_ran_for", None) != (c.id, self.st.version(c.id))):
            self._ran_for = (c.id, self.st.version(c.id))
            self.run()
        super().showEvent(e)

    # ------------------------------------------------------------------ run
    def run(self):
        c = self.st.company()
        if not c:
            return
        p = self.period.period()
        m = self.st.masters(c)
        client, cname, cid = self.st.client(c), c.name, c.id
        self.status.setText("Running checks…")
        from datetime import date as _date
        from ..engine.periods import fy_start
        to = min(_date.today(), p.end)

        def job(progress):
            bills = closings = None
            try:
                progress("Reading bills and balances from Tally")
                bills = client.bills(cname)
                closings = client.ledger_closings(cname, fy_start(to).strftime("%Y%m%d"), to.strftime("%Y%m%d"))
            except Exception:
                pass
            progress("Applying the rules")
            s = self.st.Local()
            try:
                from ..db.models import Company
                return redflags.run(s, s.get(Company, cid), m, p, bills=bills, closings=closings), bills is not None
            finally:
                s.close()

        def done(res):
            self.flags, live = res
            self.st.session.expire_all()
            self.render()
            self._scores()
            self.status.setText(f"{len(self.flags)} indicator(s)" +
                                ("" if live else " · Tally offline: bill-based rules use synced entries"))

        def fail(msg):
            self.status.setText("")
            QMessageBox.warning(self, "Red flags", msg)
        run_bg(self, job, done, fail, lambda m_: self.status.setText(m_ + "…"))

    def visible(self) -> list:
        g = self.f_group.currentData()
        sev = self.f_sev.currentText().lower()
        st = {"Open": "open", "Explained": "explained", "False positive": "false_positive"}.get(
            self.f_status.currentText(), "")
        q = self.f_text.text().strip().lower()
        out = []
        for f in self.flags:
            if g and f.group != g:
                continue
            if sev in ("high", "medium", "low") and f.severity != sev:
                continue
            if st and f.status != st:
                continue
            if q and q not in f"{f.party} {f.title} {f.detail}".lower():
                continue
            out.append(f)
        return sorted(out, key=lambda f: (-redflags.SEV_SCORE[f.severity], f.rule, f.date))

    def render(self, *_):
        rows = self.visible()
        self.shown = rows
        self.table.setRowCount(len(rows))
        for r, f in enumerate(rows):
            lab, fg, bg = SEV[f.severity]
            vals = [lab, f.rule, f.title, f.party, _fmt(f.date), fmt_inr(f.amount) if f.amount else "",
                    STATUS.get(f.status, f.status)]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c == 0:
                    it.setForeground(QColor(fg))
                    it.setBackground(QColor(bg))
                if c == 5:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if c == 6 and f.status != "open":
                    it.setForeground(QColor(theme.OK_FG))
                it.setToolTip(f.detail)
                self.table.setItem(r, c, it)
        opn = [f for f in self.flags if f.status == "open"]
        for k in ("high", "medium", "low"):
            self.tiles[k].setText(str(sum(1 for f in opn if f.severity == k)))
        self.tiles["closed"].setText(str(sum(1 for f in self.flags if f.status != "open")))

    def _scores(self):
        sc = redflags.party_scores(self.flags)
        self.scores.setRowCount(len(sc))
        for r, (p, score, n, groups) in enumerate(sc):
            for c, v in enumerate([p, str(score), str(n), " ".join(groups)]):
                it = QTableWidgetItem(v)
                if c == 1:
                    colour = theme.ERR_FG if score >= 20 else theme.WARN_FG if score >= 10 else theme.INFO_FG
                    it.setForeground(QColor(colour))
                self.scores.setItem(r, c, it)

    def _party_filter(self, row, _col):
        self.f_text.setText(self.scores.item(row, 0).text())
        self.tabs.setCurrentIndex(0)

    def current(self):
        r = self.table.currentRow()
        return self.shown[r] if 0 <= r < len(getattr(self, "shown", [])) else None

    def show_detail(self):
        f = self.current()
        if not f:
            return
        lab, fg, _bg = SEV[f.severity]
        self.d_title.setText(f"{f.rule} · {f.title}")
        self.d_title.setStyleSheet(f"color: {fg};")
        bits = [f"<b>Party:</b> {f.party}" if f.party else "", f"<b>Date:</b> {_fmt(f.date)}" if f.date else "",
                f"<b>Amount:</b> ₹ {fmt_inr(f.amount)}" if f.amount else "", f.detail]
        self.d_body.setText("<br>".join(b for b in bits if b))
        self.d_law.setText(f"{redflags.GROUP_NAMES.get(f.group, '')} · {f.law}")
        self.d_refs.setPlainText("\n".join(map(str, f.refs)) or "(see detail)")
        self.d_note.setText(f.note)
        self.d_rev.setText(f"{STATUS.get(f.status, f.status)}" + (f" by {f.reviewer}" if f.reviewer else ""))

    def set_status(self, status: str):
        f = self.current()
        if not f:
            return
        if status != "open" and not self.d_note.text().strip():
            QMessageBox.information(self, "Red flags", "Write a short note first - it stays with the flag for review.")
            return
        redflags.review(self.st.session, self.st.company(), f, status, self.d_note.text().strip(), self.st.actor,
                        self.d_all.isChecked())
        f.status, f.note, f.reviewer = status, self.d_note.text().strip(), self.st.actor
        if self.d_all.isChecked():
            for x in self.flags:
                if x.rule == f.rule and x.party == f.party:
                    x.status, x.note, x.reviewer = status, f.note, self.st.actor
        row = self.table.currentRow()
        self.render()
        self._scores()
        if self.table.rowCount():
            self.table.selectRow(min(row, self.table.rowCount() - 1))

    def export(self):
        if not self.flags:
            return
        c = self.st.company()
        p = self.period.period()
        path, _ = QFileDialog.getSaveFileName(self, "Red flags", f"{c.name} - Red flags {p.frm}-{p.to}.xlsx"
                                              .replace("/", "-"), "Excel (*.xlsx)")
        if path:
            redflags.to_excel(self.flags, Path(path), c.name, p.text())
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def edit_thresholds(self):
        c = self.st.company()
        if not c:
            return
        cur = {**redflags.DEFAULTS, **(c.settings or {}).get("redflag_thresholds", {})}
        dlg = QDialog(self)
        dlg.setWindowTitle("Red flag thresholds")
        dlg.resize(520, 640)
        lay = QVBoxLayout(dlg)
        from PyQt6.QtWidgets import QScrollArea
        sc = QScrollArea(widgetResizable=True)
        inner = QWidget()
        form = QFormLayout(inner)
        boxes = {}
        for k, v in cur.items():
            sb = QSpinBox(maximum=1_000_000_000)
            sb.setValue(int(v))
            sb.setGroupSeparatorShown(True)
            form.addRow(k.replace("_", " ").capitalize(), sb)
            boxes[k] = sb
        sc.setWidget(inner)
        lay.addWidget(sc, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec():
            c.settings = {**(c.settings or {}), "redflag_thresholds": {k: b.value() for k, b in boxes.items()}}
            self.st.session.commit()
            self.run()


class RelatedPartiesWidget(QWidget):
    """The user's list of related parties per company, and every transaction with them."""

    def __init__(self, st, period):
        super().__init__()
        self.st, self.period = st, period
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        left = QFrame(objectName="card")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(12, 10, 12, 10)
        ll.addWidget(QLabel("Related parties (per company)", objectName="h2"))
        self.list = QTableWidget(0, 3)
        self.list.setHorizontalHeaderLabels(["Name", "Relation", "Tally ledger(s)"])
        self.list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.list.verticalHeader().setVisible(False)
        self.list.itemSelectionChanged.connect(self.show_txns)
        ll.addWidget(self.list, 1)
        br = QHBoxLayout()
        b_add = QPushButton("+ Add")
        b_add.clicked.connect(self.add)
        b_del = QPushButton("Remove")
        b_del.clicked.connect(self.remove)
        b_imp = QPushButton("Import Excel…")
        b_imp.setToolTip("Columns: Name, Relation, Ledger (one row per ledger)")
        b_imp.clicked.connect(self.import_xl)
        for b in (b_add, b_del, b_imp):
            br.addWidget(b)
        ll.addLayout(br)
        lay.addWidget(left, 2)
        right = QFrame(objectName="card")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(12, 10, 12, 10)
        self.t_title = QLabel("Transactions", objectName="h2")
        rl.addWidget(self.t_title)
        self.txns = QTableWidget(0, 5)
        self.txns.setHorizontalHeaderLabels(["Date", "Voucher", "Narration", "Dr", "Cr"])
        self.txns.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.txns.verticalHeader().setVisible(False)
        self.txns.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        rl.addWidget(self.txns, 1)
        self.t_sum = QLabel("", objectName="muted")
        rl.addWidget(self.t_sum)
        lay.addWidget(right, 3)
        self.reload()

    def parties(self) -> list:
        c = self.st.company()
        return list((c.settings or {}).get("related_parties", [])) if c else []

    def save(self, rows: list):
        c = self.st.company()
        c.settings = {**(c.settings or {}), "related_parties": rows}
        self.st.session.commit()
        self.reload()

    def reload(self):
        rows = self.parties()
        self.list.setRowCount(len(rows))
        for r, p in enumerate(rows):
            for col, v in enumerate([p.get("name", ""), p.get("relation", ""), ", ".join(p.get("ledgers", []))]):
                self.list.setItem(r, col, QTableWidgetItem(v))
        self.txns.setRowCount(0)

    def add(self):
        c = self.st.company()
        if not c:
            return
        m = self.st.masters(c)
        dlg = QDialog(self)
        dlg.setWindowTitle("Related party")
        f = QFormLayout(dlg)
        name = QLineEdit()
        rel = QComboBox()
        rel.setEditable(True)
        rel.addItems(["Director", "Relative of director", "KMP", "Partner", "Holding company", "Subsidiary",
                      "Associate", "Group company", "Firm in which director is interested", "Shareholder > 20%"])
        led1, led2 = LedgerCombo(sorted(m.ledgers)), LedgerCombo(sorted(m.ledgers))
        f.addRow("Name", name)
        f.addRow("Relation", rel)
        f.addRow("Tally ledger", led1)
        f.addRow("Another ledger (optional)", led2)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec() and (name.text().strip() or led1.currentText().strip()):
            leds = [x for x in (led1.currentText().strip(), led2.currentText().strip()) if x]
            self.save(self.parties() + [{"name": name.text().strip() or leds[0], "relation": rel.currentText().strip(),
                                         "ledgers": leds}])

    def remove(self):
        r = self.list.currentRow()
        rows = self.parties()
        if 0 <= r < len(rows):
            rows.pop(r)
            self.save(rows)

    def import_xl(self):
        p, _ = QFileDialog.getOpenFileName(self, "Related parties", "", "Excel (*.xlsx)")
        if not p:
            return
        from openpyxl import load_workbook
        rows = {}
        ws = load_workbook(p, read_only=True, data_only=True).active
        for i, r in enumerate(ws.iter_rows(values_only=True)):
            if i == 0 or not r or not r[0]:
                continue
            name = str(r[0]).strip()
            d = rows.setdefault(name, {"name": name, "relation": str(r[1] or "").strip() if len(r) > 1 else "",
                                       "ledgers": []})
            led = str(r[2]).strip() if len(r) > 2 and r[2] else name
            if led not in d["ledgers"]:
                d["ledgers"].append(led)
        self.save(self.parties() + list(rows.values()))

    def show_txns(self):
        r = self.list.currentRow()
        rows = self.parties()
        if not (0 <= r < len(rows)):
            return
        rp = rows[r]
        c = self.st.company()
        allt = redflags.related_transactions(self.st.session, c, self.st.masters(c), self.period.period())
        items = [(v, e) for led in rp.get("ledgers", []) for v, e in allt.get(led, [])]
        items.sort(key=lambda x: x[0].date)
        self.txns.setRowCount(len(items))
        dr = cr = Decimal(0)
        for i, (v, e) in enumerate(items):
            a = Decimal(e["amount"])
            dr += a if e["dr"] else 0
            cr += 0 if e["dr"] else a
            for col, val in enumerate([_fmt(v.date), f"{v.voucher_type} {v.number}", (v.narration or e["ledger"])[:90],
                                       fmt_inr(a) if e["dr"] else "", "" if e["dr"] else fmt_inr(a)]):
                it = QTableWidgetItem(val)
                if col >= 3:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.txns.setItem(i, col, it)
        self.t_title.setText(f"{rp.get('name')} · {rp.get('relation')}")
        self.t_sum.setText(f"{len(items)} transaction(s) · Dr {fmt_inr(dr)} · Cr {fmt_inr(cr)} · "
                           f"{self.period.period().text()}")
