"""Schedule III (Division I) Balance Sheet and Statement of Profit and Loss, live from Tally, with a one-time
ledger mapping per company."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QColor, QDesktopServices, QFont
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from ..engine import sch3
from . import theme
from .common import ChoiceDelegate, choice_item, fmt_inr, run_bg


def _amt(v) -> str:
    v = Decimal(v or 0)
    if not v:
        return "-"
    return f"({fmt_inr(-v)})" if v < 0 else fmt_inr(v)


class Sch3Widget(QWidget):
    """Lives as a tab of the Reports page; uses the page's period picker."""

    def __init__(self, st, period_picker):
        super().__init__()
        self.st, self.period = st, period_picker
        self.result = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        top = QHBoxLayout()
        self.info = QLabel("Schedule III, Division I (Accounting Standards). Map each ledger once on the Mapping "
                           "tab; suggestions come from the Tally group and the ledger name.", objectName="muted",
                           wordWrap=True)
        top.addWidget(self.info, 1)
        b = QPushButton("Build from Tally", objectName="primary")
        b.clicked.connect(self.load)
        self.b_xl = QPushButton("Export to Excel")
        self.b_xl.setEnabled(False)
        self.b_xl.clicked.connect(self.export)
        top.addWidget(b)
        top.addWidget(self.b_xl)
        lay.addLayout(top)
        self.tabs = QTabWidget()
        self.bs = self._tree()
        self.pl = self._tree()
        self.tabs.addTab(self.bs, "Balance Sheet")
        self.tabs.addTab(self.pl, "Statement of Profit && Loss")
        # mapping
        mw = QWidget()
        ml = QVBoxLayout(mw)
        mt = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Find ledger…")
        self.search.textChanged.connect(self._filter)
        self.only_new = QCheckBox("Only ledgers not confirmed yet")
        self.only_new.toggled.connect(self._filter)
        b_ok = QPushButton("Confirm all shown")
        b_ok.setToolTip("Accept the suggested line items for the ledgers shown")
        b_ok.clicked.connect(self.confirm_shown)
        b_save = QPushButton("Save mapping", objectName="primary")
        b_save.clicked.connect(self.save_mapping)
        for w in (self.search, self.only_new):
            mt.addWidget(w)
        mt.addStretch(1)
        mt.addWidget(b_ok)
        mt.addWidget(b_save)
        ml.addLayout(mt)
        self.map_table = QTableWidget(0, 5)
        self.map_table.setHorizontalHeaderLabels(["Ledger", "Tally group", "Balance", "Schedule III line item", ""])
        h = self.map_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.map_table.setColumnWidth(1, 160)
        self.map_table.setColumnWidth(2, 120)
        self.map_table.setColumnWidth(4, 90)
        self.map_table.verticalHeader().setVisible(False)
        self.map_table.verticalHeader().setDefaultSectionSize(32)
        self.map_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked |
                                       QTableWidget.EditTrigger.SelectedClicked |
                                       QTableWidget.EditTrigger.EditKeyPressed)
        self._labels = [(c, f"{name}  ({'BS' if s == 'BS' else 'P&L' if s == 'PL' else '-'})")
                        for c, s, _sec, name in sch3.LINES]
        self.map_table.setItemDelegateForColumn(3, ChoiceDelegate(self.map_table, self._labels,
                                                                  lambda row, code: self._mark(row, "changed")))
        ml.addWidget(self.map_table, 1)
        self.tabs.addTab(mw, "Mapping")
        lay.addWidget(self.tabs, 1)
        self.foot = QLabel("", wordWrap=True)
        lay.addWidget(self.foot)

    @staticmethod
    def _tree() -> QTreeWidget:
        t = QTreeWidget()
        t.setHeaderLabels(["Particulars", "Note", "Current period", "Previous year"])
        t.header().setStretchLastSection(False)
        t.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        t.setColumnWidth(1, 60)
        t.setColumnWidth(2, 150)
        t.setColumnWidth(3, 150)
        return t

    # ------------------------------------------------------------------ data
    def mapping(self) -> dict:
        c = self.st.company()
        return dict((c.settings or {}).get("sch3_map", {})) if c else {}

    def load(self):
        c = self.st.company()
        if not c:
            return
        p = self.period.period()
        client, cname, m = self.st.client(c), c.name, self.st.masters(c)
        mapping = self.mapping()
        self.foot.setText("Reading from Tally…")

        def job(progress):
            return sch3.fetch(client, cname, p.frm, p.to, m.ledgers, mapping, progress)

        def done(res):
            self.result = res
            self._p = p
            self._render(res)
            self._fill_mapping(res)
            self.b_xl.setEnabled(True)

        def fail(msg):
            self.foot.setText("")
            QMessageBox.warning(self, "Schedule III", f"Couldn't read from Tally:\n{msg}")
        run_bg(self, job, done, fail, lambda s: self.foot.setText(s + "…"))

    def _render(self, r):
        bold = QFont()
        bold.setBold(True)
        t = r.totals

        def add(tree, label, note="", cur=None, prev=None, b=False, parent=None, ledgers=None):
            it = QTreeWidgetItem([label, str(note or ""), _amt(cur) if cur is not None else "",
                                  _amt(prev) if prev is not None else ""])
            for c in (1, 2, 3):
                it.setTextAlignment(c, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if b:
                for c in range(4):
                    it.setFont(c, bold)
            (parent.addChild(it) if parent else tree.addTopLevelItem(it))
            for n, lc, lp in ledgers or []:
                ch = QTreeWidgetItem([n, "", _amt(lc), _amt(lp)])
                for c in (2, 3):
                    ch.setTextAlignment(c, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    ch.setForeground(c, QColor(theme.MUTED))
                it.addChild(ch)
            return it
        self.bs.clear()
        add(self.bs, "I. EQUITY AND LIABILITIES", b=True)
        assets_started = False
        for sec, its in r.bs:
            liab = its[0].code in sch3.LIABILITY_SIDE
            if not liab and not assets_started:
                add(self.bs, "TOTAL", "", t["eq_c"], t["eq_p"], True)
                add(self.bs, "II. ASSETS", b=True)
                assets_started = True
            s = add(self.bs, f"   {sec}", b=True)
            for it in its:
                add(self.bs, f"      {it.name}", it.note, it.current, it.previous, ledgers=it.ledgers)
        add(self.bs, "TOTAL", "", t["as_c"], t["as_p"], True)
        self.pl.clear()
        items = {it.code: it for _s, its in r.pl for it in its}

        def line(label, code, b=False):
            it = items.get(code)
            add(self.pl, label, it.note if it else "", it.current if it else 0, it.previous if it else 0, b,
                ledgers=it.ledgers if it else None)
        line("I. Revenue from operations", "PL_REV")
        line("II. Other income", "PL_OI")
        add(self.pl, "III. Total income (I + II)", "", t["rev_c"], t["rev_p"], True)
        add(self.pl, "IV. Expenses", b=True)
        for code in ("PL_MAT", "PL_PUR", "PL_CHG", "PL_EMP", "PL_FIN", "PL_DEP", "PL_OTH"):
            if code in items:
                line(f"      {items[code].name}", code)
        add(self.pl, "Total expenses (IV)", "", t["exp_c"], t["exp_p"], True)
        line("VI. Exceptional items", "PL_EXC")
        add(self.pl, "VII. Profit before tax", "", t["pbt_c"], t["pbt_p"], True)
        line("      Current tax", "PL_TAX_CUR")
        line("      Deferred tax", "PL_TAX_DEF")
        add(self.pl, "IX. Profit / (Loss) for the period", "", t["pat_c"], t["pat_p"], True)
        p = self._p
        self.foot.setText(" · ".join(r.notes) if r.notes else "✓ Balance Sheet balances")
        self.foot.setStyleSheet(f"color: {theme.WARN_FG if r.notes else theme.OK_FG};")
        self.info.setText(f"Schedule III, Division I · {p.text()} · previous year: same period a year earlier "
                          f"· expand a line for its ledgers")

    def _fill_mapping(self, r):
        mapping = self.mapping()
        suggested = dict(r.unmapped)
        names = sorted(set(r.balances) | set(mapping))
        self.map_table.setRowCount(len(names))
        labels = self._labels
        self.map_table.setUpdatesEnabled(False)
        for i, n in enumerate(names):
            d = r.ledgers.get(n, {})
            for col, val in enumerate([n, d.get("_group") or d.get("_primary", ""),
                                       _amt(-(r.balances.get(n, Decimal(0))))]):
                it = QTableWidgetItem(val)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 2:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    it.setToolTip("Debit balances positive, credit balances in brackets")
                self.map_table.setItem(i, col, it)
            code = mapping.get(n) or suggested.get(n) or sch3.suggest(n, d.get("_primary", ""), d.get("_group", ""))
            confirmed = n in mapping
            ci = choice_item(labels, code)
            ci.setFlags(ci.flags() | Qt.ItemFlag.ItemIsEditable)
            if not confirmed:
                ci.setBackground(QColor(theme.WARN_BG))
            self.map_table.setItem(i, 3, ci)
            st = QTableWidgetItem("confirmed" if confirmed else "suggested")
            st.setForeground(QColor(theme.OK_FG if confirmed else theme.WARN_FG))
            st.setFlags(st.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.map_table.setItem(i, 4, st)
        self.map_table.setUpdatesEnabled(True)
        self._filter()

    def _mark(self, row, text):
        self.map_table.item(row, 4).setText(text)
        self.map_table.item(row, 3).setBackground(QColor(theme.SURFACE))

    def _filter(self, *_):
        q = self.search.text().strip().lower()
        for i in range(self.map_table.rowCount()):
            name = self.map_table.item(i, 0).text().lower()
            hide = (q and q not in name) or (self.only_new.isChecked() and
                                             self.map_table.item(i, 4).text() == "confirmed")
            self.map_table.setRowHidden(i, bool(hide))

    def confirm_shown(self):
        for i in range(self.map_table.rowCount()):
            if not self.map_table.isRowHidden(i) and self.map_table.item(i, 4).text() == "suggested":
                self._mark(i, "changed")

    def save_mapping(self):
        c = self.st.company()
        if not c:
            return
        mp = self.mapping()
        for i in range(self.map_table.rowCount()):
            if self.map_table.item(i, 4).text() in ("changed", "confirmed"):
                mp[self.map_table.item(i, 0).text()] = self.map_table.item(i, 3).data(Qt.ItemDataRole.UserRole)
        cfg = dict(c.settings or {})
        cfg["sch3_map"] = mp
        c.settings = cfg
        self.st.session.commit()
        self.st.window.toast(f"✓ Schedule III mapping saved ({len(mp)} ledgers) - shared with the office")
        self.load()

    def export(self):
        if not self.result:
            return
        c = self.st.company()
        p = self._p
        pf, pt = self.result.period[2], self.result.period[3]
        prev = f"{pt[6:8]}-{pt[4:6]}-{pt[:4]}"
        default = f"{c.name} - Schedule III {p.to}.xlsx".replace("/", "-")
        path, _ = QFileDialog.getSaveFileName(self, "Export Schedule III", default, "Excel (*.xlsx)")
        if not path:
            return
        sch3.to_excel(self.result, Path(path), c.name, p.end.strftime("%d-%m-%Y"), prev)
        self.st.window.toast(f"✓ Saved {path}")
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
