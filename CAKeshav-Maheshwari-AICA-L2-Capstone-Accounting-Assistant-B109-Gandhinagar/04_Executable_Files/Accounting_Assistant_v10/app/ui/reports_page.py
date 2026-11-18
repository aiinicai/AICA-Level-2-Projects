"""Trial Balance, Profit & Loss and Balance Sheet read live from TallyPrime for any period, with drill-down
(group → ledgers → vouchers → voucher, with the original document) and Excel export."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
                             QSplitter, QTableWidget, QTableWidgetItem, QTabWidget, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

from ..engine import docs, reports
from ..engine.reports import Node
from . import theme
from .common import PeriodPicker, drcr, fmt_inr, page_layout, run_bg


def _fill(tree: QTreeWidget, nodes: list[Node], two_col: bool, expand_top: bool = False):
    tree.clear()
    bold = QFont()
    bold.setBold(True)

    def add(parent, n: Node, depth: int):
        if two_col:
            vals = [n.name, fmt_inr(n.dr) if n.dr else "", fmt_inr(n.cr) if n.cr else ""]
        else:
            vals = [n.name, fmt_inr(abs(n.amount)) if n.amount else ""]
        it = QTreeWidgetItem(vals)
        it.setData(0, Qt.ItemDataRole.UserRole, (n.kind, n.name))
        for c in range(1, len(vals)):
            it.setTextAlignment(c, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if n.kind in ("group", "profit", "total", "header", "carry") and depth == 0:
            for c in range(len(vals)):
                it.setFont(c, bold)
        if n.kind == "profit":
            for c in range(len(vals)):
                it.setForeground(c, Qt.GlobalColor.darkGreen if n.amount <= 0 else Qt.GlobalColor.darkRed)
        if n.kind == "ledger":
            it.setToolTip(0, "Double-click for the vouchers")
        (parent.addChild(it) if parent else tree.addTopLevelItem(it))
        for ch in n.children:
            add(it, ch, depth + 1)
        if expand_top and depth == 0:
            it.setExpanded(True)
    for n in nodes:
        add(None, n, 0)


def _tree(cols: list[str]) -> QTreeWidget:
    t = QTreeWidget()
    t.setHeaderLabels(cols)
    t.header().setStretchLastSection(False)
    t.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    for i in range(1, len(cols)):
        t.setColumnWidth(i, 130)
    t.setAlternatingRowColors(True)
    t.setUniformRowHeights(True)
    return t


class LedgerVouchers(QDialog):
    """Drill-down: every voucher of one ledger in the period; double-click for the voucher and its document."""

    def __init__(self, st, company, ledger: str, period, parent=None):
        super().__init__(parent)
        self.st, self.company, self.ledger = st, company, ledger
        self.setWindowTitle(f"{ledger} · {period.text()}")
        self.resize(980, 560)
        lay = QVBoxLayout(self)
        self.info = QLabel("Reading vouchers from Tally…", objectName="muted")
        lay.addWidget(self.info)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Date", "Type", "No.", "Particulars", "Dr", "Cr", "Doc"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for c, w in ((0, 90), (1, 110), (2, 80), (4, 110), (5, 110), (6, 50)):
            self.table.setColumnWidth(c, w)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self.open_voucher)
        lay.addWidget(self.table, 1)
        client, cname = st.client(company), company.name

        def job(progress):
            return client.vouchers_range(cname, period.start, period.end, progress=progress), "Tally (live)"

        def fail(msg):
            from sqlalchemy import select
            from ..db.models import VoucherHistory
            rows = [dict(guid=v.guid, masterid=v.masterid, date=v.date, voucher_type=v.voucher_type,
                         number=v.number, narration=v.narration, reference=v.reference, entries=v.entries)
                    for v in st.session.scalars(select(VoucherHistory).where(
                        VoucherHistory.company_id == company.id, VoucherHistory.date >= period.frm,
                        VoucherHistory.date <= period.to).order_by(VoucherHistory.date))]
            self._show(rows, f"synced copy (Tally not reachable: {msg[:80]})")
        run_bg(self, job, lambda r: self._show(*r), fail, lambda m: self.info.setText(m))

    def _show(self, vchs, source):
        rows = []
        for v in vchs:
            mine = [e for e in v["entries"] if e["ledger"] == self.ledger]
            if not mine:
                continue
            dr = sum((Decimal(e["amount"]) for e in mine if e["dr"]), Decimal(0))
            cr = sum((Decimal(e["amount"]) for e in mine if not e["dr"]), Decimal(0))
            other = [e["ledger"] for e in v["entries"] if e["ledger"] != self.ledger]
            rows.append((v, dr, cr, other[0] + (" + more" if len(other) > 1 else "") if other else ""))
        self.rows = rows
        self.table.setRowCount(len(rows))
        tdr = tcr = Decimal(0)
        for r, (v, dr, cr, part) in enumerate(rows):
            d = v["date"]
            path = docs.find_document(self.st.session, self.company.id, v.get("masterid", ""),
                                      v.get("reference", ""), d)
            vals = [f"{d[6:8]}-{d[4:6]}-{d[:4]}", v["voucher_type"], v["number"], part,
                    fmt_inr(dr) if dr else "", fmt_inr(cr) if cr else "", "📄" if path else ""]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c in (4, 5):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if c == 3:
                    it.setToolTip(v.get("narration", ""))
                self.table.setItem(r, c, it)
            tdr += dr
            tcr += cr
        self.info.setText(f"{len(rows)} voucher(s) from {source}  ·  Dr {fmt_inr(tdr)}  ·  Cr {fmt_inr(tcr)}  ·  "
                          f"double-click a voucher to see it")

    def open_voucher(self, row, _col):
        v = self.rows[row][0]
        VoucherView(self.st, self.company, v, self).exec()


class VoucherView(QDialog):
    def __init__(self, st, company, v: dict, parent=None):
        super().__init__(parent)
        d = v["date"]
        self.setWindowTitle(f"{v['voucher_type']} {v['number']} · {d[6:8]}-{d[4:6]}-{d[:4]}")
        self.resize(640, 420)
        lay = QVBoxLayout(self)
        t = QTableWidget(len(v["entries"]), 3)
        t.setHorizontalHeaderLabels(["Ledger", "Dr", "Cr"])
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        t.verticalHeader().setVisible(False)
        for r, e in enumerate(v["entries"]):
            a = Decimal(e["amount"])
            for c, val in enumerate([e["ledger"], fmt_inr(a) if e["dr"] else "", "" if e["dr"] else fmt_inr(a)]):
                it = QTableWidgetItem(val)
                if c:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                t.setItem(r, c, it)
        lay.addWidget(t, 1)
        if v.get("narration"):
            lay.addWidget(QLabel(v["narration"], wordWrap=True, objectName="muted"))
        path = docs.find_document(st.session, company.id, v.get("masterid", ""), v.get("reference", ""), d)
        row = QHBoxLayout()
        row.addStretch(1)
        b = QPushButton("Open original document" if path else "No document linked", objectName="primary")
        b.setEnabled(bool(path))
        b.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(path)))
        row.addWidget(b)
        lay.addLayout(row)


_CACHE: dict = {}          # (company id, from, to) -> (time, Reports): reports open instantly the second time


class ReportsPage(QWidget):
    def __init__(self, st):
        super().__init__(objectName="page")
        self.st = st
        self.rep = None
        root = page_layout(self, "Reports", "Trial Balance, Profit & Loss and Balance Sheet - live from TallyPrime "
                                            "for the period you pick. Double-click a ledger to see its vouchers.")
        top = QHBoxLayout()
        self.period = PeriodPicker("reports")
        self.period.changed.connect(lambda *_: self.load())
        top.addWidget(self.period)
        top.addStretch(1)
        self.status = QLabel("", objectName="muted")
        top.addWidget(self.status)
        b_load = QPushButton("Refresh from Tally", objectName="primary")
        b_load.clicked.connect(lambda: self.load(force=True))
        self.b_xl = QPushButton("Export to Excel")
        self.b_xl.clicked.connect(self.export)
        self.b_xl.setEnabled(False)
        top.addWidget(b_load)
        top.addWidget(self.b_xl)
        root.addLayout(top)
        self.tabs = QTabWidget()
        self.tb = _tree(["Particulars", "Debit", "Credit"])
        self.tb_total = QLabel("", objectName="h2")
        w = QWidget()
        wl = QVBoxLayout(w)
        wl.setContentsMargins(0, 8, 0, 0)
        wl.addWidget(self.tb, 1)
        wl.addWidget(self.tb_total)
        self.tabs.addTab(w, "Trial Balance")
        self.pl_l, self.pl_r = _tree(["Expenses", "Amount"]), _tree(["Income", "Amount"])
        self.pl_sum = QLabel("", objectName="h2")
        self.tabs.addTab(self._two(self.pl_l, self.pl_r, self.pl_sum), "Profit && Loss")
        self.bs_l, self.bs_r = _tree(["Liabilities", "Amount"]), _tree(["Assets", "Amount"])
        self.bs_sum = QLabel("", objectName="muted", wordWrap=True)
        self.tabs.addTab(self._two(self.bs_l, self.bs_r, self.bs_sum), "Balance Sheet")
        from .sch3_page import Sch3Widget
        self.sch3 = Sch3Widget(st, self.period)
        self.tabs.addTab(self.sch3, "Schedule III")
        root.addWidget(self.tabs, 1)
        for t in (self.tb, self.pl_l, self.pl_r, self.bs_l, self.bs_r):
            t.itemDoubleClicked.connect(self.drill)
        st.on_company_change(self.clear)

    def _two(self, a, b, footer) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)
        sp = QSplitter(Qt.Orientation.Horizontal)
        sp.addWidget(a)
        sp.addWidget(b)
        lay.addWidget(sp, 1)
        lay.addWidget(footer)
        return w

    def clear(self):
        self.rep = None
        for t in (self.tb, self.pl_l, self.pl_r, self.bs_l, self.bs_r):
            t.clear()
        self.status.setText("Pick a period and Refresh")
        self.b_xl.setEnabled(False)

    def showEvent(self, e):
        c = self.st.company()
        if c and (self.rep is None or getattr(self, "_shown_for", None) != (c.id, self.st.version(c.id))):
            self._shown_for = (c.id, self.st.version(c.id))
            self.load()
        super().showEvent(e)

    def load(self, force: bool = False):
        c = self.st.company()
        if not c:
            return
        p = self.period.period()
        import time as _t
        hit = _CACHE.get((c.id, p.frm, p.to))
        if hit and not force:
            self._p = p
            self._show_rep(hit[1], p)
            self.status.setText(f"From Tally at {_t.strftime('%H:%M', _t.localtime(hit[0]))} · Refresh for latest")
            return
        client, cname = self.st.client(c), c.name
        self.status.setText("Reading from Tally…")

        def job(progress):
            return reports.fetch(client, cname, p.frm, p.to, progress)

        def done(rep):
            _CACHE[(c.id, p.frm, p.to)] = (_t.time(), rep)
            self._show_rep(rep, p)
            self.status.setText("✓ Live from Tally")

        def fail(msg):
            self.status.setText("")
            QMessageBox.warning(self, "Reports", f"Couldn't read the reports from Tally:\n{msg}")
        run_bg(self, job, done, fail, lambda m: self.status.setText(m + "…"))

    def _show_rep(self, rep, p):
        if True:
            self.rep, self._p = rep, p
            _fill(self.tb, rep.trial_balance, True)
            ok = abs(rep.tb_dr - rep.tb_cr) < Decimal("0.01")
            txt = (f"Grand total   Dr {fmt_inr(rep.tb_dr)}   Cr {fmt_inr(rep.tb_cr)}   " +
                   ("✓" if ok else f"✗ difference {fmt_inr(rep.tb_dr - rep.tb_cr)}"))
            if rep.tally_tb and not rep.tb_mismatch:
                txt += "   ·   ✓ agrees with Tally's own Trial Balance"
            elif rep.tb_mismatch:
                txt += (f"\n⚠ {len(rep.tb_mismatch)} group(s) differ from Tally's own Trial Balance: " +
                        "; ".join(f"{g} (app {fmt_inr(ad - ac)}, Tally {fmt_inr(td - tc)})"
                                  for g, ad, ac, td, tc in rep.tb_mismatch[:4]) +
                        " - details saved in the diagnostics folder; please send them")
            self.tb_total.setText(txt)
            self.tb_total.setWordWrap(True)
            self.tb_total.setStyleSheet(f"color: {theme.ERR_FG if rep.tb_mismatch else theme.INK};")
            def section(title, nodes, total):
                return [Node(title, "header")] + nodes + [Node("Total", "total", total), Node("", "spacer")]
            _fill(self.pl_l, section("TRADING ACCOUNT", rep.trading_left, rep.trading_total) +
                  section("PROFIT & LOSS ACCOUNT", rep.plac_left, rep.plac_total), False, True)
            _fill(self.pl_r, section("TRADING ACCOUNT", rep.trading_right, rep.trading_total) +
                  section("PROFIT & LOSS ACCOUNT", rep.plac_right, rep.plac_total), False, True)
            np_ = rep.net_profit
            self.pl_sum.setText(f"Gross {'profit' if rep.gross_profit >= 0 else 'loss'} {fmt_inr(abs(rep.gross_profit))}"
                                f"   ·   Nett {'profit' if np_ >= 0 else 'loss'} {fmt_inr(abs(np_))}" +
                                (f"   ·   stock from {rep.stock_source}" if rep.stock_source else ""))
            self.pl_sum.setStyleSheet(f"color: {theme.OK_FG if np_ >= 0 else theme.ERR_FG};")
            _fill(self.bs_l, rep.bs_liabilities, False, True)
            _fill(self.bs_r, rep.bs_assets, False, True)
            tl = sum((abs(n.amount) for n in rep.bs_liabilities), Decimal(0))
            ta = sum((abs(n.amount) for n in rep.bs_assets), Decimal(0))
            self.bs_sum.setText(f"Liabilities {fmt_inr(tl)}   ·   Assets {fmt_inr(ta)}" +
                                ("" if not rep.notes else "\n⚠ " + " ".join(rep.notes)))
            self.b_xl.setEnabled(True)

    def drill(self, item, _col):
        kind, name = item.data(0, Qt.ItemDataRole.UserRole) or ("", "")
        if kind == "ledger" and name not in ("Opening balance",):
            LedgerVouchers(self.st, self.st.company(), name, self.period.period(), self).exec()

    def export(self):
        if not self.rep:
            return
        c = self.st.company()
        p = self.period.period()
        default = f"{c.name} - Reports {p.frm}-{p.to}.xlsx".replace("/", "-")
        path, _ = QFileDialog.getSaveFileName(self, "Export reports", default, "Excel (*.xlsx)")
        if not path:
            return
        reports.to_excel(self.rep, Path(path), c.name, p.text())
        self.st.window.toast(f"✓ Saved {path}")
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
