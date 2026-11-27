"""Inputs: cash credit, term loan, existing loans, year-wise projections, norms & DSCR, GST turnover."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QTabWidget, QWidget, QFormLayout, QCheckBox, QComboBox, QLineEdit, QSpinBox,
                             QTableWidget, QTableWidgetItem, QVBoxLayout, QHeaderView, QLabel)

from config.constants import FA_CLASSES
from core.audit_trail import TRAIL
from core.models import fy_label, norm, tax_rate
from gui.pages.base_page import BasePage
from gui.pages.common import money, pct, times, buttons, opt_get, opt_set

YCOLS = [("growth", "Sales growth % (blank = default)", 100), ("stock_days", "Stock days", 1),
         ("debtor_days", "Debtor days (blank = solved for DP)", 1), ("creditor_days", "Creditor days", 1),
         ("cc_limit", "CC limit Rs (blank = proposed limit)", 1), ("drawings", "Drawings / dividend Rs (blank = last actual)", 1),
         ("capital_introduced", "Capital introduced Rs", 1)]


class InputsPage(BasePage):
    title = "Inputs"
    subtitle = ("Facility, rates and year-wise assumptions. Anything left at 'default' uses the bank norms in "
                "Settings (DSCR 1.5-2.5, turnover 4x / 5x, margins 25%, growth 20%, debtor days cap 90).")

    def build(self):
        self.tabs = QTabWidget()
        self.body.addWidget(self.tabs)
        # --- cash credit
        w = QWidget()
        f = QFormLayout(w)
        self.has_cc = QCheckBox("Cash credit proposed")
        self.cc_exist = money()
        self.cc_limit = money()
        self.cc_rate = pct(30, special="default")
        self.sm = pct(special="default")
        self.dm = pct(special="default")
        self.deduct = QCheckBox("Deduct sundry creditors from stock")
        self.ex90 = QCheckBox("Exclude debtors older than 90 days")
        self.p90 = pct()
        for lab, wd in [("", self.has_cc), ("Existing CC limit (Rs)", self.cc_exist), ("Proposed CC limit (Rs)", self.cc_limit),
                        ("Rate of interest", self.cc_rate), ("Drawing power margin - stock", self.sm),
                        ("Drawing power margin - debtors", self.dm), ("", self.deduct), ("", self.ex90),
                        ("Share of debtors over 90 days", self.p90)]:
            f.addRow(lab, wd)
        self.tabs.addTab(w, "Cash credit")
        # --- term loan
        w = QWidget()
        f = QFormLayout(w)
        self.has_tl = QCheckBox("Term loan proposed")
        self.tl_amt = money()
        self.tl_rate = pct(30, special="default")
        self.tl_ten = QSpinBox()
        self.tl_ten.setRange(1, 120)
        self.tl_ten.setSuffix(" months")
        self.tl_mor = QSpinBox()
        self.tl_mor.setRange(0, 60)
        self.tl_mor.setSuffix(" months")
        self.tl_meth = QComboBox()
        self.tl_meth.addItems(["Equal EMI", "Equal Principal"])
        self.tl_purpose = QLineEdit()
        self.tl_use = QComboBox()
        self.tl_use.addItems(["Capex", "Working capital"])
        self.tl_cls = QComboBox()
        for k, lab, _ in FA_CLASSES:
            self.tl_cls.addItem(lab.replace(" (WDV)", ""), k)
        for lab, wd in [("", self.has_tl), ("Amount (Rs)", self.tl_amt), ("Rate of interest", self.tl_rate),
                        ("Tenure (incl. moratorium)", self.tl_ten), ("Moratorium", self.tl_mor),
                        ("Repayment method", self.tl_meth), ("Purpose", self.tl_purpose), ("Use", self.tl_use),
                        ("Asset bought (if capex)", self.tl_cls)]:
            f.addRow(lab, wd)
        self.tabs.addTab(w, "Term loan")
        # --- existing loans
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("One row for each existing term loan found in the balance sheet. The yearly principal "
                           "and interest are worked out from the EMI, rate and end date (editable later on the "
                           "CMA Tests sheet)."))
        self.loans = QTableWidget()
        self.loans.setColumnCount(6)
        self.loans.setHorizontalHeaderLabels(["Loan (as in books)", "Lender", "Outstanding (last actual)",
                                              "Monthly EMI", "Rate % p.a.", "End date (yyyy-mm-dd)"])
        self.loans.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(self.loans)
        self.tabs.addTab(w, "Existing loans")
        # --- projections
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Blank cells use the defaults: growth from Settings, days from the last actual year, "
                           "debtor days solved so that drawing power exceeds the CC limit."))
        self.ytab = QTableWidget()
        v.addWidget(self.ytab)
        self.tabs.addTab(w, "Projections")
        # --- norms & DSCR
        w = QWidget()
        f = QFormLayout(w)
        self.dmin = times(10, "default")
        self.dmax = times(10, "default")
        self.ddraw = QCheckBox("Deduct drawings / dividend while calculating DSCR (banks normally do not)")
        self.tfail = times(20, "default")
        self.tpass = times(20, "default")
        self.buf = pct(20)
        self.cap = QSpinBox()
        self.cap.setRange(0, 365)
        self.cap.setSuffix(" days")
        self.auto_stock = QCheckBox("If debtor days at the cap are not enough, raise stock days for drawing power")
        self.growth = pct(200, 1, "default")
        self.tax = pct(60, special="default")
        self.ul = pct(30)
        self.unit = QComboBox()
        self.unit.addItems(["Actual", "Thousand", "Lakh", "Crore"])
        for lab, wd in [("DSCR minimum", self.dmin), ("DSCR maximum", self.dmax), ("", self.ddraw),
                        ("Turnover / limit - fail below", self.tfail), ("Turnover / limit - pass from", self.tpass),
                        ("Drawing power buffer over limit", self.buf), ("Debtor days cap", self.cap), ("", self.auto_stock),
                        ("Default sales growth", self.growth), ("Income-tax rate in P&L", self.tax),
                        ("Interest on unsecured loans", self.ul), ("Amounts in FORM sheets", self.unit)]:
            f.addRow(lab, wd)
        self.tabs.addTab(w, "Norms & DSCR")
        # --- GST
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Turnover as per GSTR-3B for each actual year (for the turnover cross-check sheet)."))
        self.gst = QTableWidget()
        self.gst.setColumnCount(2)
        self.gst.setHorizontalHeaderLabels(["Financial year", "GSTR-3B turnover (Rs)"])
        self.gst.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(self.gst)
        self.tabs.addTab(w, "GST turnover")
        self.body.addLayout(buttons(self, [("Apply and recalculate", self.apply, "Accent")]))

    # ------------------------------------------------------------
    def refresh(self):
        it = self.project.intake
        sd = self.app.settings.get("defaults", {})
        self.has_cc.setChecked(it.has_cc)
        self.cc_exist.setValue(it.cc_existing_limit)
        self.cc_limit.setValue(it.cc_limit)
        opt_set(self.cc_rate, it.cc_rate, 100)
        opt_set(self.sm, it.stock_margin, 100)
        opt_set(self.dm, it.debtor_margin, 100)
        self.deduct.setChecked(it.deduct_creditors)
        self.ex90.setChecked(it.exclude_over90)
        self.p90.setValue(it.debtors_over_90_pct * 100)
        self.has_tl.setChecked(it.has_tl)
        self.tl_amt.setValue(it.tl_amount)
        opt_set(self.tl_rate, it.tl_rate, 100)
        self.tl_ten.setValue(int(it.tl_tenure_months))
        self.tl_mor.setValue(int(it.tl_moratorium_months))
        self.tl_meth.setCurrentText(it.tl_method)
        self.tl_purpose.setText(it.tl_purpose)
        self.tl_use.setCurrentText(it.tl_use)
        self.tl_cls.setCurrentIndex(max(self.tl_cls.findData(it.tl_capex_class), 0))
        opt_set(self.dmin, it.dscr_min)
        opt_set(self.dmax, it.dscr_max)
        self.ddraw.setChecked(it.dscr_deduct_drawings)
        opt_set(self.tfail, it.turnover_fail_below)
        opt_set(self.tpass, it.turnover_pass_from)
        self.buf.setValue(it.dp_buffer * 100)
        self.cap.setValue(int(it.debtor_days_cap))
        self.auto_stock.setChecked(it.auto_raise_stock)
        opt_set(self.growth, it.default_growth, 100)
        opt_set(self.tax, it.tax_rate, 100)
        self.ul.setValue(it.unsecured_loan_rate * 100)
        self.unit.setCurrentText(it.unit)
        self._fill_loans()
        self._fill_years()
        self._fill_gst()

    def _fill_loans(self):
        from analysis.engine import ensure_loans
        ensure_loans(self.project)
        stmt = [y.fy for y in self.project.statement_years()]
        t = self.loans
        t.setRowCount(len(self.project.loans))
        for r, ln in enumerate(self.project.loans):
            line = self.project.line(ln.line_id)
            vals = [line.label if line else "?", ln.lender, "{:,.0f}".format(line.v(stmt[-1]) if (line and stmt) else 0),
                    "%.0f" % ln.emi, "%.2f" % (ln.rate * 100), ln.end_date]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                if c in (0, 2):
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                t.setItem(r, c, it)

    def _fill_years(self):
        tool = self.project.tool_years()
        t = self.ytab
        t.setColumnCount(len(tool))
        t.setRowCount(len(YCOLS))
        t.setHorizontalHeaderLabels(["%s %s" % (fy_label(y.fy), y.kind) for y in tool])
        t.setVerticalHeaderLabels([lab for _, lab, _ in YCOLS])
        res = self.result
        for c, y in enumerate(tool):
            yi = self.project.year_input(y.fy)
            ry = res.year(y.fy) if res else None
            for r, (k, _, scale) in enumerate(YCOLS):
                v = getattr(yi, k)
                txt = "" if v is None or (k == "capital_introduced" and not v) else (
                    "%.2f" % (v * scale) if k == "growth" else "%.0f" % v)
                item = QTableWidgetItem(txt)
                item.setTextAlignment(int(Qt.AlignRight | Qt.AlignVCenter))
                if not txt and ry is not None:
                    used = {"growth": ry.get("growth", 0) * 100, "stock_days": ry.get("stock_days"),
                            "debtor_days": ry.get("debtor_days"), "creditor_days": ry.get("creditor_days"),
                            "cc_limit": ry.get("cc_limit_input"), "drawings": ry.get("drawings")}.get(k)
                    if used is not None:
                        item.setToolTip("Default in use: %s" % format(round(used, 2), ","))
                t.setItem(r, c, item)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def _fill_gst(self):
        stmt = self.project.statement_years()
        self.gst.setRowCount(len(stmt))
        for r, y in enumerate(stmt):
            a = QTableWidgetItem("FY " + fy_label(y.fy))
            a.setFlags(a.flags() & ~Qt.ItemIsEditable)
            a.setData(Qt.UserRole, y.fy)
            self.gst.setItem(r, 0, a)
            v = self.project.intake.gst_turnover.get(str(y.fy))
            self.gst.setItem(r, 1, QTableWidgetItem("" if v is None else "%.0f" % v))

    @staticmethod
    def _num(txt):
        t = (txt or "").replace(",", "").strip()
        if not t:
            return None
        try:
            return float(t)
        except ValueError:
            return None

    def apply(self):
        it = self.project.intake
        it.has_cc = self.has_cc.isChecked()
        it.cc_existing_limit = self.cc_exist.value()
        it.cc_limit = self.cc_limit.value()
        it.cc_rate = opt_get(self.cc_rate, 100)
        it.stock_margin = opt_get(self.sm, 100)
        it.debtor_margin = opt_get(self.dm, 100)
        it.deduct_creditors = self.deduct.isChecked()
        it.exclude_over90 = self.ex90.isChecked()
        it.debtors_over_90_pct = self.p90.value() / 100
        it.has_tl = self.has_tl.isChecked()
        it.tl_amount = self.tl_amt.value()
        it.tl_rate = opt_get(self.tl_rate, 100)
        it.tl_tenure_months = self.tl_ten.value()
        it.tl_moratorium_months = min(self.tl_mor.value(), max(self.tl_ten.value() - 1, 0))
        it.tl_method = self.tl_meth.currentText()
        it.tl_purpose = self.tl_purpose.text().strip()
        it.tl_use = self.tl_use.currentText()
        it.tl_capex_class = self.tl_cls.currentData()
        it.dscr_min = opt_get(self.dmin)
        it.dscr_max = opt_get(self.dmax)
        it.dscr_deduct_drawings = self.ddraw.isChecked()
        it.turnover_fail_below = opt_get(self.tfail)
        it.turnover_pass_from = opt_get(self.tpass)
        it.dp_buffer = self.buf.value() / 100
        it.debtor_days_cap = self.cap.value()
        it.auto_raise_stock = self.auto_stock.isChecked()
        it.default_growth = opt_get(self.growth, 100)
        it.tax_rate = opt_get(self.tax, 100)
        it.unsecured_loan_rate = self.ul.value() / 100
        it.unit = self.unit.currentText()
        for r, ln in enumerate(self.project.loans):
            ln.lender = self.loans.item(r, 1).text().strip()
            ln.emi = self._num(self.loans.item(r, 3).text()) or 0.0
            ln.rate = (self._num(self.loans.item(r, 4).text()) or 10.0) / 100
            ln.end_date = self.loans.item(r, 5).text().strip()
        for c, y in enumerate(self.project.tool_years()):
            yi = self.project.year_input(y.fy)
            for r, (k, _, scale) in enumerate(YCOLS):
                item = self.ytab.item(r, c)
                v = self._num(item.text() if item else "")
                if k == "growth":
                    yi.growth = None if v is None else v / 100
                elif k == "capital_introduced":
                    yi.capital_introduced = v or 0.0
                else:
                    setattr(yi, k, v)
        for r in range(self.gst.rowCount()):
            fy = self.gst.item(r, 0).data(Qt.UserRole)
            v = self._num(self.gst.item(r, 1).text() if self.gst.item(r, 1) else "")
            if v is None:
                it.gst_turnover.pop(str(fy), None)
            else:
                it.gst_turnover[str(fy)] = v
        TRAIL.log("Inputs updated", "CC %s, TL %s" % (it.cc_limit if it.has_cc else "-", it.tl_amount if it.has_tl else "-"))
        self.app.recompute()
