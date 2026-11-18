"""Home: one look at the company - money position live from Tally, what's due, and what's waiting in the app."""
from __future__ import annotations

from decimal import Decimal

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
                             QVBoxLayout, QWidget)

from ..engine import dashboard
from . import fx, theme
from .common import PeriodPicker, drcr, fmt_inr, run_bg, tone


def _card(title: str, colour: str = ""):
    f = fx.GlassCard(title, colour)
    lay = QVBoxLayout(f)
    lay.setContentsMargins(18, 16, 18, 14)
    lay.setSpacing(4)
    t = QLabel(title, objectName="section")
    if colour:
        t.setStyleSheet(f"color: {colour}; letter-spacing: 1px;")
    lay.addWidget(t)
    return f, lay


def _kind(name: str) -> str:
    n = name.lower()
    return "card" if "card" in n else "cash" if n.strip() == "cash" or "cash" in n.split() else \
        "od" if (" cc" in f" {n}" or "od" in n.split() or "overdraft" in n) else "bank"


class HomePage(QWidget):
    def __init__(self, st):
        super().__init__(objectName="page")
        self.st = st
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 18, 26, 14)
        root.setSpacing(12)
        self.sub = fx.GradientLabel("Home", 26)
        root.addWidget(self.sub)
        top = QHBoxLayout()
        self.period = PeriodPicker("home")
        self.period.changed.connect(lambda *_: self.load())
        top.addWidget(self.period)
        top.addStretch(1)
        self.status = QLabel("", objectName="livepill")
        self.status.setVisible(False)
        top.addWidget(self.status)
        b = QPushButton("⟳  Refresh", objectName="primary")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(self.load)
        top.addWidget(b)
        root.addLayout(top)

        scroll = QScrollArea(widgetResizable=True)
        host = QWidget()
        host.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.grid = QGridLayout(host)
        self.grid.setContentsMargins(0, 0, 8, 12)
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(14)
        scroll.setWidget(host)
        root.addWidget(scroll, 1)

        # tiles: to-do counts, each with a 14-day activity line
        self.t_inv = fx.GlowTile("Invoices waiting", "Open Workbench", 0)
        self.t_bank = fx.GlowTile("Bank lines to post", "Open Bank", 1)
        self.t_rec = fx.GlowTile("Recurring due (7 days)", "Open Journals", 2)
        for i, (t, page) in enumerate(((self.t_inv, "Workbench"), (self.t_bank, "Bank"), (self.t_rec, "Journals"))):
            t.clicked.connect(lambda pg=page: self.st.window.go_page(pg))
            self.grid.addWidget(t, 0, i)
        self.t_inv.setToolTip("Invoices read but not yet posted · line: invoices handled per day, last 14 days")
        self.t_bank.setToolTip("Statement lines not yet posted · line: statement lines per day, last 14 days")
        self.c_cash, self.l_cash = _card("CASH & BANK  ·  LIVE FROM TALLY", theme.MODULE["Bank"])
        self.c_tax, self.l_tax = _card("TAX POSITION", theme.MODULE["Compliance"])
        self.c_pay, self.l_pay = _card("PAYABLES DUE THIS WEEK", theme.MODULE["Red flags"])
        self.c_rec, self.l_rec = _card("RECEIVABLES OVERDUE", theme.MODULE["Reports"])
        self.grid.addWidget(self.c_cash, 1, 0, 1, 2)
        self.grid.addWidget(self.c_tax, 1, 2)
        self.grid.addWidget(self.c_pay, 2, 0, 1, 2)
        self.grid.addWidget(self.c_rec, 2, 2)
        for c in range(3):
            self.grid.setColumnStretch(c, 1)
        self.grid.setRowStretch(3, 1)
        st.on_company_change(self.load)
        self._loaded_for = None

    def _spark(self, c):
        try:
            a = dashboard.activity(self.st.session, c.id)
        except Exception:
            return
        self.t_inv.set_value(self.t_inv.value, a["invoices"])
        self.t_bank.set_value(self.t_bank.value, a["bank"])
        self.t_rec.set_value(self.t_rec.value, a["posted"])
        self.t_rec.setToolTip("Recurring entries due in the next 7 days · line: entries posted per day, last 14 days")

    def showEvent(self, e):
        """Counts are local and cheap: always fresh. Tally figures reload when anything was posted / synced /
        cleared since the last load, or after 2 minutes (entries typed directly in Tally)."""
        import time as _t
        c = self.st.company()
        if c:
            key = (c.id, self.st.version(c.id))
            if self._loaded_for != key or _t.time() - getattr(self, "_loaded_at", 0) > 120:
                self.load()
            else:
                self._show_counts(dashboard.local_counts(self.st.session, c.id, self.period.period()))
        super().showEvent(e)

    @staticmethod
    def _clear(lay):
        while lay.count() > 1:
            w = lay.takeAt(1).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def _figure(self, lay, label: str, value: str, tone_: str = ""):
        """A headline figure: small label over a large number (fits any card width)."""
        w = QFrame(objectName="netrow")
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(0)
        v.addWidget(QLabel(label, objectName="muted"))
        b = QLabel(value, objectName="bigamt")
        if tone_:
            tone(b, tone_)
        v.addWidget(b)
        lay.addWidget(w)

    def _row(self, lay, left: str, right: str, tone_: str = "", dot: str = "", chip: tuple | None = None,
             net: bool = False):
        w = QFrame(objectName="netrow" if net else "hrow")
        h = QHBoxLayout(w)
        h.setContentsMargins(10 if net else 4, 6 if net else 3, 10 if net else 4, 6 if net else 3)
        h.setSpacing(8)
        if dot:
            d = QLabel("●", objectName="dot")
            tone(d, dot)
            h.addWidget(d)
        a = QLabel(left, objectName="rowname")
        a.setWordWrap(not net)
        a.setMinimumWidth(80)
        h.addWidget(a, 1)
        if chip:
            c = QLabel(chip[0], objectName="duechip")
            tone(c, chip[1])
            c.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            h.addWidget(c, 0, Qt.AlignmentFlag.AlignVCenter)
        b = QLabel(right, objectName="bigamt" if net else "rowamt")
        if tone_:
            tone(b, tone_)
        b.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        h.addWidget(b)
        lay.addWidget(w)

    def load(self):
        c = self.st.company()
        if not c:
            self.sub.setText("Home")
            return
        import time as _t
        self._loaded_for, self._loaded_at = (c.id, self.st.version(c.id)), _t.time()
        self.st.session.expire_all()
        self.sub.setText(c.name)
        self.sub.updateGeometry()
        p = self.period.period()
        local = dashboard.local_counts(self.st.session, c.id, p)
        self._show_counts(local)
        self._spark(c)
        self._set_status("Reading from Tally…", "busy")
        client, m = self.st.client(c), self.st.masters(c)
        cid = c.id

        def job(progress):
            s = self.st.Local()
            try:
                from ..db.models import Company
                return dashboard.fetch(client, s, s.get(Company, cid), m, p, progress=progress)
            finally:
                s.close()

        run_bg(self, job, self._show, lambda msg: self._set_status(f"Tally not reachable: {msg[:80]}", "err"),
               lambda msg: self._set_status(msg + "…", "busy"))

    def _set_status(self, text: str, state: str = "ok"):
        self.status.setText(("●  " if state == "ok" else "") + text)
        self.status.setObjectName("livepill" if state == "ok" else "pillWarn" if state == "busy" else "pillBad")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.status.setVisible(bool(text))

    def _show_counts(self, d):
        self.t_inv.set_value(d.pending_invoices)
        self.t_bank.set_value(d.pending_bank)
        self.t_rec.set_value(len(d.recurring_due))
        if d.recurring_due:
            self.t_rec.setToolTip("\n".join(f"{n}: {x[6:8]}-{x[4:6]}-{x[:4]}" for n, x in d.recurring_due))

    def _show(self, d):
        from datetime import date as _date
        self._show_counts(d)
        for lay in (self.l_cash, self.l_tax, self.l_pay, self.l_rec):
            self._clear(lay)
        dots = {"bank": "teal", "cash": "amber", "card": "pink", "od": "violet"}
        if d.cash_bank:
            total = sum((v for _, v in d.cash_bank), Decimal(0))
            for n, v in d.cash_bank:
                self._row(self.l_cash, n, drcr(v), "err" if v > 0 else "", dot=dots[_kind(n)])
            self._row(self.l_cash, "<b>Net position</b>", drcr(total), "err" if total > 0 else "", net=True)
        else:
            self.l_cash.addWidget(QLabel("No cash/bank balances (or Tally offline).", objectName="muted"))
        if d.gst_payable is not None:
            g = d.gst_payable
            self._figure(self.l_tax, "GST  ·  output less input", f"{fmt_inr(abs(g))} " +
                         ("payable" if g > 0 else "credit" if g < 0 else ""), "warn" if g > 0 else "ok")
            self._row(self.l_tax, "TDS deducted, not yet paid", fmt_inr(max(d.tds_payable or 0, 0)),
                      "warn" if (d.tds_payable or 0) > 0 else "")
            note = QLabel("Estimate from ledger balances - check before filing.", objectName="muted")
            note.setWordWrap(True)
            self.l_tax.addWidget(note)
        today = _date.today().strftime("%Y%m%d")
        for lay, items, empty in ((self.l_pay, d.payables_week, "✓  Nothing due in the next 7 days."),
                                  (self.l_rec, d.receivables_overdue, "✓  No overdue receivables.")):
            if not items:
                e = QLabel(empty, objectName="muted")
                tone(e, "ok")
                lay.addWidget(e)
            for party, bill, due, amt in items[:8]:
                late = due and due < today
                self._row(lay, f"{party}  <span style='color:{theme.MUTED}'>·  {bill}</span>", fmt_inr(amt),
                          chip=(("overdue " if late else "due ") + f"{due[6:8]}-{due[4:6]}",
                                "red" if late else "amber"))
            if len(items) > 8:
                more = QLabel(f"+ {len(items) - 8} more", objectName="muted")
                tone(more, "info")
                lay.addWidget(more)
        self._set_status("Live from Tally" + (" · " + "; ".join(d.errors)[:120] if d.errors else ""),
                         "ok" if not d.errors else "busy")
