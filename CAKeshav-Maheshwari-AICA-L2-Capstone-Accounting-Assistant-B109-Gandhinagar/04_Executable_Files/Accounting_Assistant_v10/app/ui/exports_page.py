"""Exports: foreign-currency invoices, realisation, FIRC / e-BRC, LUT, exchange differences, revaluation."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
                             QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from . import theme
from .common import ask_lock_reason, fmt_inr, page_layout, run_bg

INV_COLS = ["Invoice", "Date", "Client", "Foreign", "Booked rate", "Received", "Outstanding", "Exchange diff",
            "In Tally", "To enter", "Realise by", "Status"]
REC_COLS = ["Date", "Client", "Foreign", "Rate", "INR", "Bank", "FIRC no", "FIRC date", "e-BRC no", "e-BRC date",
            "Narration"]
REC_EDIT = {6: "firc_no", 7: "firc_date", 8: "ebrc_no", 9: "ebrc_date"}


def _d(s):
    return f"{s[6:8]}-{s[4:6]}-{s[:4]}" if s else ""


def _ymd(t: str) -> str:
    from ..engine.claims import _ymd as y
    return y(t)


def _num(x: Decimal, places=2) -> str:
    return f"{x:,.{places}f}"


class ExportsPage(QWidget):
    def __init__(self, st):
        super().__init__()
        self.st = st
        root = page_layout(self, "Exports", "Foreign-currency invoices and their realisation, read from the synced "
                                            "day book (Sync first). Bank advices are read on this PC only.")
        lut = QHBoxLayout()
        self.lut_no = QLineEdit()
        self.lut_no.setPlaceholderText("LUT ARN / no.")
        self.lut_from, self.lut_to = QLineEdit(), QLineEdit()
        self.lut_from.setPlaceholderText("from dd-mm-yyyy")
        self.lut_to.setPlaceholderText("to dd-mm-yyyy")
        for w in (self.lut_no, self.lut_from, self.lut_to):
            w.setMaximumWidth(170)
        b_lut = QPushButton("Save LUT")
        b_lut.clicked.connect(self.save_lut)
        self.lut_lbl = QLabel("", objectName="muted")
        for w in (QLabel("LUT"), self.lut_no, self.lut_from, self.lut_to, b_lut, self.lut_lbl):
            lut.addWidget(w)
        lut.addStretch(1)
        b_xl = QPushButton("Export to Excel")
        b_xl.clicked.connect(self.export)
        lut.addWidget(b_xl)
        root.addLayout(lut)
        self.summary = QLabel("", wordWrap=True)
        root.addWidget(self.summary)

        tabs = QTabWidget()
        # invoices
        w1 = QWidget()
        v1 = QVBoxLayout(w1)
        self.inv = self._table(INV_COLS, 2)
        for i, w in ((0, 130), (1, 84), (3, 104), (4, 80), (5, 90), (6, 90), (7, 92), (8, 84), (9, 84), (10, 84),
                     (11, 86)):
            self.inv.setColumnWidth(i, w)
        v1.addWidget(self.inv, 1)
        r = QHBoxLayout()
        b_prop = QPushButton("Enter exchange differences…", objectName="primary")
        b_prop.setToolTip("For realised invoices whose exchange gain/loss is not yet in Tally: a 'Forex' entry "
                          "against the invoice, as your office does")
        b_prop.clicked.connect(self.post_diffs)
        r.addStretch(1)
        r.addWidget(b_prop)
        v1.addLayout(r)
        tabs.addTab(w1, "Invoices")
        # receipts
        w2 = QWidget()
        v2 = QVBoxLayout(w2)
        v2.addWidget(QLabel("Type FIRC / e-BRC numbers and dates in the grey columns; they are saved at once.",
                            objectName="muted"))
        self.rec = self._table(REC_COLS, 10)
        for i, w in ((0, 84), (1, 170), (2, 104), (3, 70), (4, 104), (5, 110), (6, 110), (7, 84), (8, 110), (9, 84)):
            self.rec.setColumnWidth(i, w)
        self.rec.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed |
                                 QTableWidget.EditTrigger.AnyKeyPressed)
        self.rec.itemChanged.connect(self._rec_edited)
        v2.addWidget(self.rec, 1)
        tabs.addTab(w2, "Receipts / FIRC")
        # revaluation
        w3 = QWidget()
        v3 = QVBoxLayout(w3)
        rr = QHBoxLayout()
        self.rate = QLineEdit()
        self.rate.setPlaceholderText("Closing rate ₹ per unit")
        self.rate.setMaximumWidth(170)
        self.on = QLineEdit()
        self.on.setPlaceholderText("Month-end date")
        self.on.setMaximumWidth(140)
        b_show = QPushButton("Work out")
        b_show.clicked.connect(self.reval_show)
        b_post = QPushButton("Post revaluation…", objectName="primary")
        b_post.clicked.connect(self.reval_post)
        for w in (QLabel("Rate"), self.rate, QLabel("as on"), self.on, b_show, b_post):
            rr.addWidget(w)
        rr.addStretch(1)
        v3.addLayout(rr)
        self.reval = self._table(["Client", "Outstanding (foreign)", "Booked value", "At closing rate",
                                  "Gain (+) / loss (-)"], 0)
        v3.addWidget(self.reval, 1)
        v3.addWidget(QLabel("Unrealised difference on what is still outstanding at month-end. Many offices reverse "
                            "it on the 1st of the next month; the actual difference is entered when the money comes "
                            "in (Invoices tab).", wordWrap=True, objectName="muted"))
        tabs.addTab(w3, "Month-end revaluation")
        root.addWidget(tabs, 1)
        self.invoices, self.receipts = [], []
        self._loading = False

    def _table(self, cols, stretch):
        t = QTableWidget(0, len(cols))
        t.setHorizontalHeaderLabels(cols)
        t.horizontalHeader().setSectionResizeMode(stretch, QHeaderView.ResizeMode.Stretch)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(30)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return t

    def showEvent(self, e):
        self.load()
        super().showEvent(e)

    def load(self):
        from ..engine import exports, masters as masters_mod
        c = self.st.company()
        if not c:
            return
        self.m = masters_mod.load(self.st.session, c.id)
        l = exports.lut(c)
        self.lut_no.setText(l.get("no", ""))
        self.lut_from.setText(_d(l.get("from", "")))
        self.lut_to.setText(_d(l.get("to", "")))
        self.lut_lbl.setText(exports.lut_status(c))
        fxr = (c.settings or {}).get("fx_rates", {})
        if fxr and not self.rate.text():
            last = sorted(fxr)[-1]
            self.rate.setText(str(fxr[last]))
        if not self.on.text():
            first = date.today().replace(day=1)
            from datetime import timedelta
            self.on.setText(_d((first - timedelta(days=1)).strftime("%Y%m%d")))
        self.invoices, self.receipts = exports.register(self.st.session, c, self.m)
        self.render()

    def render(self):
        today = date.today()
        col = {"realised": theme.OK_FG, "overdue": theme.ERR_FG, "due soon": theme.WARN_FG}
        t = self.inv
        t.setRowCount(len(self.invoices))
        for i, x in enumerate(self.invoices):
            st = x.status(today)
            vals = [x.key, _d(x.date), x.party, f"{x.cur} {_num(x.fc)}", _num(x.rate, 4), _num(x.received_fc),
                    _num(x.outstanding_fc), fmt_inr(x.diff), fmt_inr(x.booked_diff), fmt_inr(x.pending_diff),
                    _d(x.due_9m), st]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if 3 <= c <= 9:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if c == 11:
                    it.setForeground(QColor(col.get(st, theme.INK)))
                if c in (0, 2):
                    it.setToolTip(v)
                if c == 9 and x.pending_diff and x.received_fc:
                    it.setForeground(QColor(theme.WARN_FG))
                t.setItem(i, c, it)
        self._loading = True
        r = self.rec
        r.setRowCount(len(self.receipts))
        for i, x in enumerate(self.receipts):
            rec = x.record
            vals = [_d(x.date), x.party, f"{x.cur} {_num(x.fc)}", _num(x.rate, 4), fmt_inr(x.inr), x.bank,
                    rec.firc_no if rec else "", _d(rec.firc_date) if rec else "", rec.ebrc_no if rec else "",
                    _d(rec.ebrc_date) if rec else "", x.narration]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c in REC_EDIT:
                    it.setBackground(QColor(theme.SUBTLE))
                else:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if c == 6 and not v:
                    it.setToolTip("FIRC / bank advice number")
                r.setItem(i, c, it)
        self._loading = False
        out_fc = sum((x.outstanding_fc for x in self.invoices), Decimal(0))
        overdue = [x for x in self.invoices if x.status(today) == "overdue"]
        soon = [x for x in self.invoices if x.status(today) == "due soon"]
        pend = [x for x in self.invoices if x.pending_diff and x.received_fc]
        no_firc = [x for x in self.receipts if not (x.record and (x.record.firc_no or x.record.ebrc_no))]
        self.summary.setText(
            f"{len(self.invoices)} invoice(s) · outstanding {_num(out_fc)} in foreign currency"
            + (f" · <b style='color:{theme.ERR_FG}'>{len(overdue)} past 9 months</b>" if overdue else "")
            + (f" · {len(soon)} due within 30 days" if soon else "")
            + (f" · {len(pend)} exchange difference(s) to enter" if pend else "")
            + (f" · {len(no_firc)} receipt(s) without FIRC / e-BRC" if no_firc else "")
            + ("" if self.invoices else " - no foreign-currency invoices in the synced day book (Sync Tally first)"))

    # ---------------------------------------------------------------- edits
    def save_lut(self):
        c = self.st.company()
        cfg = dict(c.settings or {})
        cfg["lut"] = {"no": self.lut_no.text().strip(), "from": _ymd(self.lut_from.text()),
                      "to": _ymd(self.lut_to.text())}
        c.settings = cfg
        self.st.session.commit()
        self.load()

    def _rec_edited(self, it):
        from ..engine import exports
        if self._loading or it.column() not in REC_EDIT:
            return
        x = self.receipts[it.row()]
        f = REC_EDIT[it.column()]
        val = _ymd(it.text()) if f.endswith("date") else it.text().strip()
        x.record = exports.save_record(self.st.session, self.st.company().id, x.guid, **{f: val})

    def export(self):
        from ..engine import exports
        path, _ = QFileDialog.getSaveFileName(self, "Export", "Export receivables.xlsx", "Excel (*.xlsx)")
        if path:
            exports.to_excel(self.invoices, self.receipts, path)

    # ---------------------------------------------------------------- entries
    def _post(self, vouchers: list, title: str, override: str = ""):
        c = self.st.company()
        from ..db.models import Company
        cid, win = c.id, self.st.window
        win.progress_start(f"{title}…")

        def job(progress):
            s = self.st.Local()
            ok, failed, locked = 0, [], ""
            try:
                comp = s.get(Company, cid)
                for k, v in enumerate(vouchers, 1):
                    progress(f"{title} {k}/{len(vouchers)}")
                    import hashlib
                    key = f"{v.vtype}|{v.date}|{v.party}|{v.narration}|{sum(l.amount for l in v.lines)}"
                    res = self.st.post(s, comp, v, None, override,
                                       remote_id="fx-" + hashlib.sha1(key.encode()).hexdigest()[:24])
                    if res.locked:
                        locked = res.message
                    elif res.ok:
                        ok += 1
                    else:
                        failed.append(f"{v.narration[:60]}: {res.message}")
            finally:
                s.close()
            return ok, failed, locked

        def done(res):
            ok, failed, locked = res
            win.progress_done(f"{ok} entr{'y' if ok == 1 else 'ies'} posted")
            self.st.session.expire_all()
            self.load()
            if locked:
                reason = ask_lock_reason(self, locked)
                if reason:
                    self._post(vouchers, title, reason)
                return
            if failed:
                QMessageBox.warning(self, "Exports", f"{ok} posted.\n\nNot posted:\n• " + "\n• ".join(failed[:8]))
        run_bg(self, job, done, lambda m: (win.progress_done(""), QMessageBox.warning(self, "Exports", m)),
               win.progress_text)

    def post_diffs(self):
        from ..engine import exports
        c = self.st.company()
        todo = [x for x in self.invoices if x.received_fc and abs(x.pending_diff) >= Decimal("0.01")]
        if not todo:
            QMessageBox.information(self, "Exports", "No exchange differences waiting to be entered.")
            return
        vs = [exports.forex_voucher(self.m, c, x.party, x.cur, x.pending_diff, max(r[1] for r in x.receipts), x.key)
              for x in todo]
        led = exports.gain_loss_ledger(self.m)
        lines = "\n".join(f"{x.key}: {'gain' if x.pending_diff > 0 else 'loss'} {fmt_inr(abs(x.pending_diff))}"
                          for x in todo[:15])
        if QMessageBox.question(self, "Exchange differences",
                                f"Post {len(vs)} '{vs[0].vtype}' entr{'y' if len(vs) == 1 else 'ies'} against "
                                f"'{led}'?\n\n{lines}") == QMessageBox.StandardButton.Yes:
            self._post(vs, "Posting exchange differences")

    def _reval_rows(self):
        from ..engine import exports
        try:
            rate = Decimal(self.rate.text().replace(",", "").strip())
        except Exception:
            QMessageBox.warning(self, "Revaluation", "Type the closing rate (₹ per unit), e.g. 88.45")
            return None, None
        return rate, exports.revaluation(self.invoices, rate)

    def reval_show(self):
        rate, res = self._reval_rows()
        if res is None:
            return
        t = self.reval
        t.setRowCount(len(res))
        for i, (party, g) in enumerate(sorted(res.items())):
            out_fc = sum((x.outstanding_fc for x in self.invoices if x.party == party), Decimal(0))
            book = sum((x.outstanding_fc * x.rate for x in self.invoices if x.party == party), Decimal(0))
            for c, v in enumerate([party, _num(out_fc), fmt_inr(book), fmt_inr(out_fc * rate), fmt_inr(g)]):
                it = QTableWidgetItem(v)
                if c:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                t.setItem(i, c, it)
        c = self.st.company()
        on = _ymd(self.on.text())
        cfg = dict(c.settings or {})
        cfg["fx_rates"] = {**cfg.get("fx_rates", {}), on[:6] or "last": str(rate)}
        c.settings = cfg
        self.st.session.commit()

    def reval_post(self):
        from ..engine import exports
        rate, res = self._reval_rows()
        if not res:
            if res is not None:
                QMessageBox.information(self, "Revaluation", "Nothing outstanding in foreign currency.")
            return
        on = _ymd(self.on.text())
        if not on:
            QMessageBox.warning(self, "Revaluation", "Type the month-end date.")
            return
        c = self.st.company()
        cur = {x.party: x.cur for x in self.invoices}
        vs = [exports.forex_voucher(self.m, c, p, cur[p], g, on, "",
                                    f"Revaluation of outstanding {cur[p]} at {rate} as on {_d(on)}")
              for p, g in res.items() if abs(g) >= Decimal("0.01")]
        if vs and QMessageBox.question(self, "Revaluation", f"Post {len(vs)} revaluation entr"
                                       f"{'y' if len(vs) == 1 else 'ies'} dated {_d(on)}?") == \
                QMessageBox.StandardButton.Yes:
            self._post(vs, "Posting revaluation")
