"""Review & group: every line read, its CMA head and group; tally of each statement year; lock."""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QHBoxLayout, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
                             QVBoxLayout, QCheckBox, QLabel, QInputDialog, QMessageBox)

from analysis import mapper
from analysis.layout import SINGLE_HEADS, group_of, EXPENSE_HEADS
from config.constants import HEAD_LABEL, PL_KEYS, LIAB_KEYS, ASSET_KEYS
from core.audit_trail import TRAIL
from core.models import SourceLine, fy_label
from gui.pages.base_page import BasePage
from gui.pages.common import buttons, rs
from gui.widgets.table_view import DataTable

CHOICES = [("ignore", "(ignore - total / heading)"), ("_reported_net_profit", "(net profit as reported - check)"),
           ("", "(not mapped)")] + \
    [(k, "P&L: " + HEAD_LABEL[k]) for k in PL_KEYS] + \
    [(k, "Liability: " + HEAD_LABEL[k]) for k in LIAB_KEYS if k != "new_term_loan"] + \
    [(k, "Asset: " + HEAD_LABEL[k]) for k in ASSET_KEYS] + \
    [("drawings", "Capital a/c: drawings / dividend"), ("capital_introduced", "Capital a/c: capital introduced")]
KEYS = [k for k, _ in CHOICES]


class ReviewPage(BasePage):
    title = "Review & group"
    subtitle = ("Each line read from the statements with its CMA head and group (Schedule III for companies, T-form "
                "for others). Change a head from the list, correct an amount by double-clicking it, add a missed line. "
                "Amber rows need a look. Every statement year must tally before projections are built.")
    scroll = False

    def build(self):
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Year:"))
        self.year = QComboBox()
        self.year.currentIndexChanged.connect(lambda *_: self.fill())
        bar.addWidget(self.year)
        self.doubt = QCheckBox("Only lines that need a look")
        self.doubt.stateChanged.connect(lambda *_: self.fill())
        bar.addWidget(self.doubt)
        self.learn = QCheckBox("Remember my changes on this PC")
        self.learn.setChecked(True)
        bar.addWidget(self.learn)
        self.lock = QCheckBox("Lock the actual years")
        self.lock.stateChanged.connect(lambda *_: self.toggle_lock())
        bar.addWidget(self.lock)
        bar.addStretch()
        self.body.addLayout(bar)
        self.body.addLayout(buttons(self, [("Add line", self.add_line, "Secondary"),
                                           ("Delete line", self.delete_line, "Secondary"),
                                           ("Apply and recalculate", self.apply, "Accent")]))
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Stmt", "Line as in the books", "Amount (Rs)", "CMA head",
                                              "Trading / P&L", "Group", "Confidence / source"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.body.addWidget(self.table, 3)
        g = QGroupBox("Tally of the statement years")
        v = QVBoxLayout(g)
        self.tally = DataTable()
        self.tally.setMaximumHeight(190)
        v.addWidget(self.tally)
        self.body.addWidget(g, 1)
        self._rows = []

    def refresh(self):
        years = sorted({s.year for s in self.project.source_lines})
        cur = self.year.currentData()
        self.year.blockSignals(True)
        self.year.clear()
        for y in years:
            self.year.addItem("FY " + fy_label(y), y)
        if cur in years:
            self.year.setCurrentIndex(years.index(cur))
        self.year.blockSignals(False)
        self.lock.blockSignals(True)
        self.lock.setChecked(self.project.locked)
        self.lock.blockSignals(False)
        self.fill()
        self.fill_tally()

    def fill(self):
        fy = self.year.currentData()
        lines = [s for s in self.project.source_lines if s.year == fy]
        if self.doubt.isChecked():
            lines = [s for s in lines if not s.head or s.confidence < 70 or s.head == "misc_exp"]
        self._rows = lines
        t = self.table
        t.setRowCount(len(lines))
        company = self.project.intake.is_company
        for r, s in enumerate(lines):
            t.setItem(r, 0, QTableWidgetItem(s.statement))
            t.setItem(r, 1, QTableWidgetItem(s.label))
            a = QTableWidgetItem("{:,.2f}".format(s.amount))
            a.setTextAlignment(int(Qt.AlignRight | Qt.AlignVCenter))
            t.setItem(r, 2, a)
            cb = QComboBox()
            for k, lab in CHOICES:
                cb.addItem(lab, k)
            cb.setCurrentIndex(KEYS.index(s.head) if s.head in KEYS else 2)
            t.setCellWidget(r, 3, cb)
            sec = QComboBox()
            sec.addItems(["", "trading", "pl"])
            sec.setCurrentText(s.section)
            t.setCellWidget(r, 4, sec)
            t.setItem(r, 5, QTableWidgetItem(group_of(s.head, company, s.section)))
            t.setItem(r, 6, QTableWidgetItem("%s%% | %s | %s" % (s.confidence, s.note, s.source)))
            if not s.head or s.confidence < 70 or s.head == "misc_exp":
                for cc in (0, 1, 2, 5, 6):
                    t.item(r, cc).setBackground(QColor("#FFEB9C"))
            if self.project.locked:
                for cc in (0, 1, 2):
                    t.item(r, cc).setFlags(t.item(r, cc).flags() & ~Qt.ItemIsEditable)
                cb.setEnabled(False)
                sec.setEnabled(False)

    def _collect(self):
        if self.project.locked:
            return
        for r, s in enumerate(self._rows):
            head = self.table.cellWidget(r, 3).currentData()
            sec = self.table.cellWidget(r, 4).currentText()
            label = self.table.item(r, 1).text()
            st = "BS" if self.table.item(r, 0).text().upper().startswith("B") else "PL"
            try:
                amt = float(self.table.item(r, 2).text().replace(",", ""))
            except ValueError:
                amt = s.amount
            if head != s.head:
                TRAIL.log("Head changed", "%s: %s -> %s" % (s.label, s.head or "-", head or "-"))
                if self.learn.isChecked() and head:
                    try:
                        mapper.learn(label, st, head)
                    except OSError:
                        pass
                s.head, s.confidence, s.note = head, 100, "set by user"
            if abs(amt - s.amount) > 0.001:
                TRAIL.log("Amount corrected", "%s FY %s: %s -> %s" % (s.label, s.year, s.amount, amt))
                s.amount = amt
            s.section, s.label, s.statement = sec, label, st

    def apply(self):
        self._collect()
        self.project.build_lines_from_sources(SINGLE_HEADS)
        self.app.recompute()

    def toggle_lock(self):
        if self.lock.isChecked():
            self._collect()
            self.project.build_lines_from_sources(SINGLE_HEADS)
            self.app.recompute()
            errs = [m for lv, m in self.app.checks if lv == "ERROR" and "balance sheet" in m.lower()]
            if errs:
                QMessageBox.warning(self, "Lock", "Cannot lock - a statement year does not tally:\n\n" + errs[0])
                self.lock.setChecked(False)
                return
            self.project.locked = True
            TRAIL.log("Actual years locked")
        else:
            self.project.locked = False
            TRAIL.log("Actual years unlocked")
        self.fill()

    def add_line(self):
        if self.project.locked:
            return
        fy = self.year.currentData()
        if fy is None:
            fy, ok = QInputDialog.getInt(self, "Add line", "Year ending March:", 2026, 2001, 2100)
            if not ok:
                return
        self._collect()
        self.project.source_lines.append(SourceLine(year=fy, statement="BS", label="New line", amount=0.0,
                                                    confidence=100, source="added by user"))
        TRAIL.log("Line added", "FY ending %s" % fy)
        self.refresh()

    def delete_line(self):
        r = self.table.currentRow()
        if self.project.locked or r < 0 or r >= len(self._rows):
            return
        s = self._rows[r]
        if QMessageBox.question(self, "Delete", "Delete '%s'?" % s.label) != QMessageBox.Yes:
            return
        self._collect()
        self.project.source_lines.remove(s)
        TRAIL.log("Line deleted", s.label)
        self.apply()

    def fill_tally(self):
        r = self.result
        rows = []
        if r is not None:
            for y in r.statement:
                rep = self.project.reported_net_profit(y["fy"])
                rows.append([y["label"] + " " + y["kind"], rs(y["total_liabilities"]), rs(y["total_assets"]),
                             rs(y["difference"]), "PASS" if abs(y["difference"]) < 1 else "FAIL", rs(y["pat"]),
                             rs(rep) if rep is not None else "-", rs(y["sales"])])
        self.tally.load(["Year", "Liabilities", "Assets", "Difference", "Tally", "Net profit (lines)",
                         "Net profit (reported)", "Sales"], rows)
