"""Client & years: borrower details and the type of every year (Audited / Provisional / Estimated / Projected)."""
import datetime as dt

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (QGroupBox, QFormLayout, QLineEdit, QComboBox, QDateEdit, QTableWidget, QSpinBox,
                             QCheckBox, QVBoxLayout, QHBoxLayout, QLabel, QHeaderView, QMessageBox)

from config.constants import CONSTITUTIONS, NATURES
from core.models import YearDef, YEAR_KINDS, MAX_YEARS, fy_label
from core.audit_trail import TRAIL
from gui.pages.base_page import BasePage
from gui.pages.common import buttons

TITLES = {"Proprietorship": "Proprietor", "Partnership Firm": "Partner", "LLP": "Designated Partner",
          "Private Limited Company": "Director", "Public Limited Company": "Director", "HUF": "Karta",
          "Trust / Society": "Authorised Signatory"}


class ClientPage(BasePage):
    title = "Client & years"
    subtitle = ("Borrower details, and the type of each year. Audited and Provisional years come from the "
                "statements you upload; Estimated and Projected years are built by the tool, or taken from the "
                "client's own figures if you tick the box.")

    def build(self):
        g = QGroupBox("Borrower")
        f = QFormLayout(g)
        self.w = {}
        for key, lab in [("client_name", "Name (as on statements)"), ("signatory_name", "Proprietor / partner / director"),
                         ("address", "Address"), ("pan", "PAN"), ("gstin", "GSTIN"), ("bank_name", "Bank"),
                         ("branch", "Branch"), ("place", "Place (for signatures)")]:
            self.w[key] = QLineEdit()
            f.addRow(lab, self.w[key])
        self.constitution = QComboBox()
        self.constitution.addItems(CONSTITUTIONS)
        self.title_box = QLineEdit()
        self.constitution.currentTextChanged.connect(lambda t: self.title_box.setText(TITLES.get(t, "Proprietor")))
        self.nature = QComboBox()
        self.nature.addItems(["Trading", "Manufacturing", "Service", "Contractor"])
        self.case = QComboBox()
        self.case.addItems(["Fresh", "Renewal", "Enhancement"])
        self.prep = QDateEdit()
        self.prep.setCalendarPopup(True)
        self.prep.setDisplayFormat("dd-MM-yyyy")
        f.addRow("Constitution", self.constitution)
        f.addRow("Signs as", self.title_box)
        f.addRow("Nature of business", self.nature)
        f.addRow("Case", self.case)
        f.addRow("Date of preparation", self.prep)
        self.body.addWidget(g)

        g2 = QGroupBox("Years (maximum %d, consecutive, oldest first)" % MAX_YEARS)
        v = QVBoxLayout(g2)
        quick = QHBoxLayout()
        quick.addWidget(QLabel("Quick set - first year ending March:"))
        self.q_first = QSpinBox()
        self.q_first.setRange(2000, 2100)
        self.q_first.setValue(dt.date.today().year - 2)
        quick.addWidget(self.q_first)
        self.q = {}
        for k, lab, dflt in (("Audited", "audited", 0), ("Actual", "actual", 2), ("Provisional", "provisional", 1),
                             ("Estimated", "estimated", 1), ("Projected", "projected", 3)):
            quick.addWidget(QLabel(lab))
            sp = QSpinBox()
            sp.setRange(0, MAX_YEARS)
            sp.setValue(dflt)
            self.q[k] = sp
            quick.addWidget(sp)
        v.addLayout(quick)
        v.addLayout(buttons(self, [("Fill the year table", self.quick_fill, "Secondary"),
                                   ("Add year", self.add_year, "Secondary"), ("Remove last year", self.remove_year,
                                                                               "Secondary")]))
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Financial year", "Type", "Use client's own figures (est./proj.)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMinimumHeight(240)
        v.addWidget(self.table)
        self.body.addWidget(g2)
        self.body.addLayout(buttons(self, [("Apply", self.apply, "Accent")]))
        self.body.addStretch()

    def refresh(self):
        it = self.project.intake
        for key, wdg in self.w.items():
            wdg.setText(getattr(it, key) or "")
        self.constitution.setCurrentText(it.constitution)
        self.title_box.setText(it.signatory_title)
        self.nature.setCurrentText(it.nature)
        self.case.setCurrentText(it.case_type)
        d = it.prep_date
        self.prep.setDate(QDate(d.year, d.month, d.day))
        self._fill(self.project.year_list())

    def _fill(self, years):
        t = self.table
        t.setRowCount(len(years))
        for r, y in enumerate(years):
            sp = QSpinBox()
            sp.setRange(2001, 2100)
            sp.setValue(y.fy)
            sp.setPrefix("Year ending 31-03-")
            t.setCellWidget(r, 0, sp)
            cb = QComboBox()
            cb.addItems(YEAR_KINDS)
            cb.setCurrentText(y.kind)
            t.setCellWidget(r, 1, cb)
            ch = QCheckBox("client figures")
            ch.setChecked(bool(y.use_client_figures))
            t.setCellWidget(r, 2, ch)

    def _read(self):
        out = []
        for r in range(self.table.rowCount()):
            fy = self.table.cellWidget(r, 0).value()
            kind = self.table.cellWidget(r, 1).currentText()
            cf = self.table.cellWidget(r, 2).isChecked() and kind in ("Estimated", "Projected")
            out.append(YearDef(fy=fy, kind=kind, use_client_figures=cf))
        return out

    def quick_fill(self):
        years, fy = [], self.q_first.value()
        for k in ("Audited", "Actual", "Provisional", "Estimated", "Projected"):
            for _ in range(self.q[k].value()):
                years.append(YearDef(fy=fy, kind=k))
                fy += 1
        if len(years) > MAX_YEARS:
            QMessageBox.warning(self, "Years", "At most %d years fit the CMA format." % MAX_YEARS)
            years = years[:MAX_YEARS]
        self._fill(years)

    def add_year(self):
        ys = self._read()
        if len(ys) >= MAX_YEARS:
            return
        nxt = (ys[-1].fy + 1) if ys else self.q_first.value()
        ys.append(YearDef(fy=nxt, kind="Projected" if ys else "Audited"))
        self._fill(ys)

    def remove_year(self):
        ys = self._read()
        self._fill(ys[:-1])

    def apply(self):
        it = self.project.intake
        for key, wdg in self.w.items():
            setattr(it, key, wdg.text().strip())
        it.constitution = self.constitution.currentText()
        it.signatory_title = self.title_box.text().strip() or TITLES.get(it.constitution, "Proprietor")
        it.nature = self.nature.currentText()
        it.case_type = self.case.currentText()
        q = self.prep.date()
        it.preparation_date = dt.date(q.year(), q.month(), q.day()).isoformat()
        ys = sorted(self._read(), key=lambda y: y.fy)
        fys = [y.fy for y in ys]
        if len(set(fys)) != len(fys):
            QMessageBox.warning(self, "Years", "The same year appears twice.")
            return
        self.project.years = ys
        TRAIL.log("Client & years set", "%s: %s" % (it.client_name, ", ".join("%s %s" % (fy_label(y.fy), y.kind)
                                                                               for y in ys)))
        self.app.recompute()
        stmt = [fy_label(y.fy) for y in ys if y.from_statement]
        self.app.status("Saved. Upload the statements for: " + ", ".join(stmt))
