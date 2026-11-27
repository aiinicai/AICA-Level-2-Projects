"""Projections, Term loan, Bank tests and Checks pages."""
from PyQt5.QtWidgets import (QTabWidget, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QComboBox,
                             QHeaderView, QGroupBox, QLabel, QMessageBox, QDoubleSpinBox)

from analysis.engine import suggest_tl_amount
from analysis.layout import basis_of, rate_of, EXPENSE_HEADS
from config.constants import FA_KEYS
from core.audit_trail import TRAIL
from core.models import fy_label
from gui.pages.base_page import BasePage
from gui.pages.common import buttons, lakh, rs
from gui.widgets.table_view import DataTable

PL_ROWS = [("sales", "Sales"), ("other_income", "Other income"), ("opening_stock", "Opening stock"),
           ("purchases", "Purchases"), ("direct_total", "Direct expenses"), ("closing_stock", "Closing stock"),
           ("gross_profit", "Gross profit"), ("indirect_total", "Indirect expenses"), ("interest", "Interest"),
           ("depreciation", "Depreciation"), ("tax", "Tax"), ("pat", "Net profit"), ("drawings", "Drawings / dividend")]
BS_ROWS = [("owners", "Capital / net worth"), ("cc", "Cash credit"), ("term_loans", "Existing term loans"),
           ("new_tl", "Proposed term loan"), ("unsecured", "Unsecured loans"), ("creditors", "Creditors"),
           ("statutory", "Statutory dues"), ("other_cl", "Other current liabilities"),
           ("total_liabilities", "TOTAL LIABILITIES"), ("fa_net", "Net fixed assets"), ("investments", "Investments"),
           ("stock", "Stock"), ("debtors", "Debtors"), ("loans_adv", "Loans, advances & deposits"),
           ("other_ca", "Other current assets"), ("cash_in_hand", "Cash in hand"), ("bank_balance", "Cash at bank"),
           ("total_assets", "TOTAL ASSETS"), ("difference", "Difference")]


def _hdr(r):
    return ["Particulars"] + ["%s\n%s" % (y["label"], y["kind"]) for y in r.years]


class ProjectionPage(BasePage):
    title = "Projections"
    subtitle = "Rs lakh. Statement years as read; estimated / projected years built by the CMA rules."
    scroll = False

    def build(self):
        self.tabs = QTabWidget()
        self.pl, self.bs = DataTable(), DataTable()
        self.tabs.addTab(self.pl, "Profit and Loss")
        self.tabs.addTab(self.bs, "Balance Sheet")
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("V = varies with sales (previous ratio to sales); F = fixed. S = scales with sales; "
                           "H = held. Rate = WDV depreciation rate for fixed assets."))
        self.basis = QTableWidget()
        self.basis.setColumnCount(3)
        self.basis.setHorizontalHeaderLabels(["Line (as in books)", "Switch", "Rate (WDV) %"])
        self.basis.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        v.addWidget(self.basis)
        v.addLayout(buttons(self, [("Apply switches and recalculate", self.apply, "Accent")]))
        self.tabs.addTab(w, "Projection basis")
        self.body.addWidget(self.tabs)
        self._lines = []

    def refresh(self):
        r = self.result
        if not r or not r.years:
            self.pl.load([], [])
            self.bs.load([], [])
            return
        for table, spec in ((self.pl, PL_ROWS), (self.bs, BS_ROWS)):
            rows = [[lab] + [lakh(y.get(k, 0)) for y in r.years] for k, lab in spec]
            table.load(_hdr(r), rows, bold_rows=[i for i, (k, _) in enumerate(spec) if k.startswith("total") or
                                                 k in ("pat", "gross_profit")])
        p = self.project
        self._lines = [ln for ln in p.lines if ln.head in EXPENSE_HEADS + ["other_income"] or
                       ln.head in ("unsecured_loans", "statutory_dues", "other_cl", "investments", "loans_advances",
                                   "other_ca", "cash_in_hand") or ln.head in FA_KEYS]
        t = self.basis
        t.setRowCount(len(self._lines))
        for i, ln in enumerate(self._lines):
            t.setItem(i, 0, QTableWidgetItem(ln.label))
            if ln.head in FA_KEYS:
                sp = QDoubleSpinBox()
                sp.setRange(0, 100)
                sp.setSuffix(" %")
                sp.setValue(rate_of(ln) * 100)
                t.setCellWidget(i, 2, sp)
                t.setItem(i, 1, QTableWidgetItem("-"))
            else:
                cb = QComboBox()
                cb.addItems(["V", "F"] if ln.statement == "PL" else ["S", "H"])
                b = basis_of(ln) if ln.head != "cash_in_hand" else (ln.basis or "S")
                cb.setCurrentText(b)
                t.setCellWidget(i, 1, cb)

    def apply(self):
        for i, ln in enumerate(self._lines):
            if ln.head in FA_KEYS:
                ln.rate = self.basis.cellWidget(i, 2).value() / 100
            else:
                ln.basis = self.basis.cellWidget(i, 1).currentText()
        TRAIL.log("Projection basis changed")
        self.app.recompute()


class TermLoanPage(BasePage):
    title = "Term loan"
    subtitle = "Repayment schedule for the method chosen on the Inputs page (Equal EMI or Equal Principal)."

    def build(self):
        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.body.addWidget(self.info)
        self.body.addLayout(buttons(self, [("Highest loan that keeps DSCR above the minimum", self.suggest,
                                            "Secondary")]))
        g = QGroupBox("Year-wise (Rs)")
        v = QVBoxLayout(g)
        self.fy = DataTable()
        self.fy.setMinimumHeight(180)
        v.addWidget(self.fy)
        self.body.addWidget(g)
        g2 = QGroupBox("Monthly schedule (Rs)")
        v2 = QVBoxLayout(g2)
        self.sch = DataTable(stretch_first=False)
        self.sch.setMinimumHeight(320)
        v2.addWidget(self.sch)
        self.body.addWidget(g2)

    def refresh(self):
        r, it = self.result, self.project.intake
        if not r or not it.has_tl or not r.tl_schedule.get("tenure"):
            self.info.setText("No term loan proposed (tick 'Term loan proposed' on the Inputs page).")
            self.fy.load([], [])
            self.sch.load([], [])
            return
        s = r.tl_schedule
        self.info.setText("Rs %s | %d months incl. %d moratorium | %s | EMI Rs %s | from %s | %s" % (
            rs(it.tl_amount), s["tenure"], s["moratorium"], it.tl_method, rs(s["emi"]),
            it.facility_start.strftime("%b-%Y"), "clears in full" if r.summary.get("tl_principal_check") else "CHECK"))
        rows = [[fy_label(fy), rs(t["instalments"]), rs(t["interest"]), rs(t["principal"]), rs(t["closing"]),
                 rs(t["next_principal"])] for fy, t in sorted(r.tl_fy.items()) if t["instalments"] or t["closing"]]
        self.fy.load(["FY", "Instalments", "Interest", "Principal", "Closing", "Due next FY"], rows)
        rows = [[m["n"], m["date"].strftime("%b-%Y"), fy_label(m["fy_end"]), rs(m["sel_open"]), rs(m["sel_interest"]),
                 rs(m["sel_principal"]), rs(m["sel_instalment"]), rs(m["sel_close"])]
                for m in s["rows"] if m["n"] <= s["tenure"]]
        self.sch.load(["No.", "Month", "FY", "Opening", "Interest", "Principal", "Instalment", "Closing"], rows)

    def suggest(self):
        amt = suggest_tl_amount(self.project, self.app.settings.get("defaults"))
        QMessageBox.information(self, "Term loan", "No term loan proposed." if amt is None else
                                "Highest loan (steps of Rs 50,000) keeping DSCR at or above the minimum in every "
                                "year: Rs %s.\n\nA guide only - enter it on the Inputs page to use it." % rs(amt))


class BankTestsPage(BasePage):
    title = "Bank tests"
    subtitle = "Drawing power, turnover, DSCR and MPBF for the estimated / projected years (Rs lakh)."

    def build(self):
        self.t = {}
        for k, title in (("dp", "Drawing power"), ("to", "Turnover"), ("dscr", "DSCR"), ("mpbf", "MPBF (Tandon II)")):
            g = QGroupBox(title)
            v = QVBoxLayout(g)
            self.t[k] = DataTable()
            self.t[k].setMinimumHeight(190)
            v.addWidget(self.t[k])
            self.body.addWidget(g)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        self.body.addWidget(self.note)

    def refresh(self):
        r = self.result
        if not r or not r.future:
            for t in self.t.values():
                t.load([], [])
            return
        fut = r.future
        hdr = ["Particulars"] + ["%s %s" % (y["label"], y["kind"]) for y in fut]

        def row(lab, fn):
            return [lab] + [fn(y) for y in fut]
        self.t["dp"].load(hdr, [row("Stock", lambda y: lakh(y["stock"])), row("Creditors", lambda y: lakh(y["creditors"])),
                                row("DP on stock", lambda y: lakh(y["dp_stock"])), row("Debtors", lambda y: lakh(y["debtors"])),
                                row("DP on debtors", lambda y: lakh(y["dp_debtors"])),
                                row("DRAWING POWER", lambda y: lakh(y["drawing_power"])),
                                row("CC limit", lambda y: lakh(y["cc_limit"])), row("Status", lambda y: y["dp_status"]),
                                row("Debtor days", lambda y: "%.0f" % y["debtor_days_calc"])], bold_rows=(5,))
        self.t["to"].load(hdr, [row("Sales", lambda y: lakh(y["sales"])), row("CC limit", lambda y: lakh(y["cc_limit"])),
                                row("Sales / limit", lambda y: ("%.2fx" % y["turnover_multiple"]) if y["turnover_multiple"] else "-"),
                                row("Status", lambda y: y["turnover_status"])])
        self.t["dscr"].load(hdr, [row("Gross cash accruals", lambda y: lakh(y["pat"] + y["depreciation"] + y["interest"])),
                                  row("Drawings", lambda y: lakh(y["drawings"])),
                                  row("Debt service", lambda y: lakh(y.get("dscr_denominator", 0))),
                                  row("DSCR (main)", lambda y: ("%.2f" % y["dscr"]) if y.get("dscr") is not None else "-"),
                                  row("DSCR after drawings", lambda y: ("%.2f" % y["dscr_net"]) if y.get("dscr_net") is not None else "-"),
                                  row("Status", lambda y: y.get("dscr_status", "-"))], bold_rows=(3,))
        self.t["mpbf"].load(hdr, [row("Current assets", lambda y: lakh(y["current_assets"])),
                                  row("Working capital gap", lambda y: lakh(y["wc_gap"])),
                                  row("MPBF", lambda y: lakh(y["mpbf"])), row("Cash credit", lambda y: lakh(y["cc"]))])
        avg = r.summary.get("dscr_avg")
        self.note.setText("Average DSCR %s - %s. %s" % (("%.2f" % avg) if avg is not None else "-",
                                                         r.summary.get("dscr_status", "-"), " ".join(r.decisions)))


class ChecksPage(BasePage):
    title = "Checks & warnings"
    subtitle = "ERROR lines block the export. WARN lines and decisions are printed in the assessment note."

    def build(self):
        self.c = DataTable()
        self.c.setMinimumHeight(300)
        self.body.addWidget(self.c)
        self.w = DataTable()
        self.w.setMinimumHeight(220)
        self.body.addWidget(self.w)

    def refresh(self):
        self.c.load(["Check", "Result"], [[m, lv] for lv, m in self.app.checks], status_cols=(1,))
        r = self.result
        rows = ([[w, "WARN"] for w in r.warnings] + [[d, "DECISION"] for d in r.decisions]) if r else []
        self.w.load(["Projection warnings and decisions", "Type"], rows)
