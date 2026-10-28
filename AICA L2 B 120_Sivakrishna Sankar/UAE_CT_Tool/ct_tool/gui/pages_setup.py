"""Setup pages: Project/dashboard, Currency & FX (the first step), Files."""
from __future__ import annotations

import csv
import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPlainTextEdit,
                               QPushButton, QSpinBox, QVBoxLayout, QWidget, QScrollArea)

from ..extract import list_sheets, parse_gl, parse_tb, to_iso_date
from ..fx import FXSettings, default_settings, peg_rates, validate_settings
from . import widgets as W

COMMON_CCY = ["AED", "USD", "EUR", "GBP", "SAR", "QAR", "KWD", "BHD", "OMR", "INR", "PKR", "EGP", "JOD", "CHF", "JPY", "CNY", "SGD", "AUD", "CAD", "TRY", "ZAR"]
METHODS = [("peg", "Official peg (USD only)"), ("annual", "CBUAE annual average rate (user-entered)"), ("manual", "User-entered rates (P&L / closing / equity)"),
           ("monthly", "CBUAE monthly average rates (needs GL + rate list)"), ("spot", "Spot rate on transaction date (needs GL + rate list)")]


def _scroll(widget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setWidget(widget)
    return sa


# ======================================================================================================================
class HomePage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.state = win, win.state
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.addWidget(W.heading("UAE Corporate Tax computation assistant", 15))
        lay.addWidget(W.banner("Preliminary-review tool. Nothing here is a filed tax position: only CONFIRMED adjustments enter the computation, elections and "
                               "reliefs are never applied automatically, and every figure is in AED. Start with the Currency step.", "#FDE9D9"))
        g = QGroupBox("Project")
        f = QFormLayout(g)
        self.name = QLineEdit()
        self.preparer, self.reviewer = QLineEdit(), QLineEdit()
        self.outdir, self.template, self.letterhead = QLineEdit(), QLineEdit(), QLineEdit()
        self.dta = QCheckBox("Include the optional DTA && DTL working (accounting deferred tax)")
        f.addRow("Project name", self.name)
        f.addRow("Prepared by", self.preparer)
        f.addRow("Reviewed by", self.reviewer)
        f.addRow("Output folder", self._browse(self.outdir, "dir"))
        f.addRow("Computation template (.xlsx) - blank = bundled template", self._browse(self.template, "xlsx"))
        f.addRow("Word letterhead (.docx) - optional", self._browse(self.letterhead, "docx"))
        f.addRow("", self.dta)
        lay.addWidget(g)
        row = QHBoxLayout()
        for text, fn in (("New project", self.win.action_new), ("Open project...", self.win.action_open), ("Save", self.win.action_save), ("Save as...", self.win.action_save_as)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.dash = QGroupBox("Dashboard")
        self.dash_form = QFormLayout(self.dash)
        self.dash_labels = {}
        for k in ("Entity", "Tax period", "TB currency", "Accounting profit (AED)", "Taxable income - confirmed adjustments only (AED)", "Corporate Tax payable - preliminary (AED)",
                  "Proposed adjustments awaiting decision", "Effect on taxable income if all were confirmed (AED)", "Open items", "Failed / warning checks", "Status"):
            lb = QLabel("-")
            lb.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.dash_form.addRow(k, lb)
            self.dash_labels[k] = lb
        lay.addWidget(self.dash)
        self.applic = QPlainTextEdit()
        self.applic.setReadOnly(True)
        self.applic.setMaximumHeight(170)
        lay.addWidget(QLabel("Computation sheets: included / omitted (a sheet that does not apply is not produced)"))
        lay.addWidget(self.applic)
        lay.addStretch(1)
        outer = QVBoxLayout(self)
        outer.addWidget(_scroll(inner))
        for w in (self.name, self.preparer, self.reviewer, self.outdir, self.template, self.letterhead):
            w.editingFinished.connect(self.push)
        self.dta.toggled.connect(lambda *_: (self.push(), self.state.reanalyse()))
        self.state.analysed.connect(self.refresh)
        self.refresh()

    def _browse(self, line: QLineEdit, kind: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(line)
        b = QPushButton("Browse...")

        def go():
            if kind == "dir":
                p = QFileDialog.getExistingDirectory(self, "Select folder", line.text() or str(Path.home()))
            else:
                p, _ = QFileDialog.getOpenFileName(self, "Select file", line.text() or str(Path.home()), f"*.{kind}")
            if p:
                line.setText(p)
                self.push()
        b.clicked.connect(go)
        h.addWidget(b)
        return w

    def push(self):
        p = self.state.project
        s = p.settings
        p.name = self.name.text() or p.name
        s.preparer, s.reviewer = self.preparer.text(), self.reviewer.text()
        s.output_dir, s.template_path, s.letterhead_path = self.outdir.text(), self.template.text(), self.letterhead.text()
        s.include_dta = self.dta.isChecked()
        self.state.mark_dirty()

    def pull(self):
        p = self.state.project
        s = p.settings
        for w, v in ((self.name, p.name), (self.preparer, s.preparer), (self.reviewer, s.reviewer), (self.outdir, s.output_dir), (self.template, s.template_path),
                     (self.letterhead, s.letterhead_path)):
            w.blockSignals(True)
            w.setText(v or "")
            w.blockSignals(False)
        self.dta.blockSignals(True)
        self.dta.setChecked(s.include_dta)
        self.dta.blockSignals(False)

    def refresh(self):
        self.pull()
        an = self.state.analysis
        L = self.dash_labels
        if not an:
            for k in L:
                L[k].setText("-")
            L["Status"].setText("Not analysed yet - " + (self.state.error or "complete the Currency and Files steps"))
            self.applic.setPlainText("")
            return
        c = an.comp
        pi = an.pending_impact()
        L["Entity"].setText(an.entity)
        L["Tax period"].setText(f"{an.period_start} to {an.period_end}")
        L["TB currency"].setText(an.project.fx.tb_currency + ("  (converted to AED)" if not an.project.fx.is_aed else "  (no conversion)"))
        L["Accounting profit (AED)"].setText(W.money(c.A))
        L["Taxable income - confirmed adjustments only (AED)"].setText(W.money(c.E))
        L["Corporate Tax payable - preliminary (AED)"].setText(W.money(c.payable))
        L["Proposed adjustments awaiting decision"].setText(str(pi["count"]))
        L["Effect on taxable income if all were confirmed (AED)"].setText(W.money(pi["delta_taxable"]))
        L["Open items"].setText(str(len(an.open_items)))
        L["Failed / warning checks"].setText(f"{sum(1 for x in an.checks if x.status == 'FAIL')} failed / {sum(1 for x in an.checks if x.status == 'WARN')} warnings")
        L["Status"].setText("DRAFT - preliminary")
        self.applic.setPlainText("\n".join(f"{'INCLUDED' if inc else 'omitted '}  {sh}  -  {why}" for sh, (inc, why) in an.applic.items()))


# ======================================================================================================================
class FXPage(QWidget):
    """Step 1: currency of the TB and conversion to AED. Everything else is gated on this page."""

    def __init__(self, win):
        super().__init__()
        self.win, self.state = win, win.state
        self._loading = False
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.addWidget(W.heading("Step 1 - Currency of the trial balance and conversion to AED"))
        lay.addWidget(W.hint("The balance sheet, profit and loss and the tax computation are always produced in UAE dirhams (AED). If the trial balance is in another "
                             "currency, enter the rates to convert it. Rates are never fetched online or guessed - you enter or upload them, and the source and reason are "
                             "recorded as the FTA conversion decision (Decision No. 13 of 2023) requires. The rules in config/rules.json are verified only as stated there."))
        g = QGroupBox("Currency and period")
        f = QFormLayout(g)
        self.ccy = QComboBox()
        self.ccy.setEditable(True)
        self.ccy.addItems(COMMON_CCY)
        self.ccy.setCurrentIndex(-1)
        self.ccy.lineEdit().setPlaceholderText("3-letter code, e.g. USD")
        self.ccy.lineEdit().setMaxLength(3)
        self.start, self.end = QLineEdit(), QLineEdit()
        self.start.setPlaceholderText("YYYY-MM-DD")
        self.end.setPlaceholderText("YYYY-MM-DD")
        f.addRow("In which currency is the trial balance prepared?", self.ccy)
        f.addRow("Tax period start", self.start)
        f.addRow("Tax period end", self.end)
        lay.addWidget(g)
        self.rate_box = QGroupBox("Conversion to AED")
        rf = QFormLayout(self.rate_box)
        self.method = QComboBox()
        for code, label in METHODS:
            self.method.addItem(label, code)
        self.r_pl, self.r_cl, self.r_eq = W.rate_spin(), W.rate_spin(), W.rate_spin()
        self.same = QCheckBox("Use the same rate for all three (e.g. a single annual rate)")
        self.load_csv = QPushButton("Load monthly / daily rates from CSV (columns: date or YYYY-MM, rate)...")
        self.csv_info = QLabel("")
        self.src = QLineEdit()
        self.src.setPlaceholderText("e.g. CBUAE published rates, downloaded on ...")
        self.reason = QPlainTextEdit()
        self.reason.setMaximumHeight(60)
        self.reason.setPlaceholderText("Why this method was chosen (recorded for Decision No. 13 compliance)")
        self.approve = QCheckBox("I approve showing the derived currency translation difference as a separate line in equity (if one arises)")
        rf.addRow("Method", self.method)
        rf.addRow("AED per 1 unit - P&L (average / transaction) rate", self.r_pl)
        rf.addRow("AED per 1 unit - closing rate (balance sheet)", self.r_cl)
        rf.addRow("AED per 1 unit - historical rate (equity)", self.r_eq)
        rf.addRow("", self.same)
        rf.addRow("", self.load_csv)
        rf.addRow("", self.csv_info)
        rf.addRow("Rate source", self.src)
        rf.addRow("Reason for method", self.reason)
        rf.addRow("", self.approve)
        lay.addWidget(self.rate_box)
        self.msgs = QListWidget()
        self.msgs.setMaximumHeight(130)
        lay.addWidget(QLabel("Checks"))
        lay.addWidget(self.msgs)
        row = QHBoxLayout()
        self.confirm = QPushButton("Confirm currency settings")
        self.confirm.clicked.connect(self.on_confirm)
        self.status = QLabel("")
        row.addWidget(self.confirm)
        row.addWidget(self.status, 1)
        lay.addLayout(row)
        lay.addStretch(1)
        outer = QVBoxLayout(self)
        outer.addWidget(_scroll(inner))
        self.ccy.currentTextChanged.connect(self.on_ccy)
        for w in (self.start, self.end, self.src):
            w.textChanged.connect(self.on_edit)
        self.reason.textChanged.connect(self.on_edit)
        self.method.currentIndexChanged.connect(self.on_edit)
        for s in (self.r_pl, self.r_cl, self.r_eq):
            s.valueChanged.connect(self.on_rate)
        self.same.toggled.connect(self.on_edit)
        self.approve.toggled.connect(self.on_edit)
        self.load_csv.clicked.connect(self.on_csv)
        self.state.gate_changed.connect(self.populate)
        self.populate()

    # ---------------------------------------------------------------- model <-> widgets
    def populate(self):
        fx = self.state.project.fx
        self._loading = True
        self.ccy.setCurrentText(fx.tb_currency or "")
        self.start.setText(fx.period_start or "")
        self.end.setText(fx.period_end or "")
        i = self.method.findData(fx.method)
        self.method.setCurrentIndex(max(i, 0))
        r = fx.rates.get((fx.tb_currency or "").upper(), {})
        self.r_pl.setValue(r.get("pl", 0.0))
        self.r_cl.setValue(r.get("closing", 0.0))
        self.r_eq.setValue(r.get("equity", 0.0))
        self.src.setText(fx.rate_source or "")
        self.reason.setPlainText(fx.method_reason or "")
        self.approve.setChecked(fx.translation_diff_approved)
        self.csv_info.setText(self._csv_summary(fx))
        self._loading = False
        self.update_enabled()
        self.validate()

    def _csv_summary(self, fx):
        c = (fx.tb_currency or "").upper()
        m, s = len(fx.monthly_rates.get(c, {})), len(fx.spot_rates.get(c, {}))
        return f"{m} monthly and {s} daily rate(s) loaded." if (m or s) else ""

    def collect(self) -> FXSettings:
        p = self.state.project
        fx = p.fx
        c = self.ccy.currentText().strip().upper()
        fx.tb_currency = c
        fx.functional_currency = fx.functional_currency or c
        fx.period_start, fx.period_end = self.start.text().strip(), self.end.text().strip()
        fx.method = self.method.currentData() if c and c != "AED" else "peg"
        if c == "AED":
            fx.rates = {"AED": {"pl": 1.0, "closing": 1.0, "equity": 1.0}}
        else:
            fx.rates[c] = {"pl": self.r_pl.value(), "closing": self.r_cl.value(), "equity": self.r_eq.value()}
        fx.rate_source, fx.method_reason = self.src.text().strip(), self.reason.toPlainText().strip()
        fx.translation_diff_approved = self.approve.isChecked()
        return fx

    def update_enabled(self):
        c = self.ccy.currentText().strip().upper()
        is_aed = c == "AED"
        self.rate_box.setEnabled(bool(c) and not is_aed)
        m = self.method.currentData()
        for s in (self.r_cl, self.r_eq):
            s.setEnabled(m != "peg" and not self.same.isChecked())
        self.r_pl.setEnabled(m != "peg")
        self.load_csv.setEnabled(m in ("monthly", "spot"))

    # ---------------------------------------------------------------- events
    def on_ccy(self, text):
        if self._loading:
            return
        c = text.strip().upper()
        p = self.state.project
        if len(c) == 3 and c != p.fx.tb_currency:
            fx = default_settings(c, self.start.text().strip(), self.end.text().strip())
            p.fx = fx
            p.fx_confirmed = False
            if self.state.analysis is not None:
                self.state.reanalyse()
            self.state.gate_changed.emit()
            self.populate()
            self.ccy.setCurrentText(c)
        self.on_edit()

    def on_rate(self, *_):
        if self._loading:
            return
        if self.same.isChecked():
            self._loading = True
            self.r_cl.setValue(self.r_pl.value())
            self.r_eq.setValue(self.r_pl.value())
            self._loading = False
        self.on_edit()

    def on_edit(self, *_):
        if self._loading:
            return
        self.collect()
        self.state.project.fx_confirmed = False
        if self.state.analysis is not None:
            self.state.reanalyse()          # settings changed after an analysis: the old results are stale, so lock the later steps again
        self.update_enabled()
        self.validate()
        self.state.mark_dirty()
        self.state.gate_changed.emit()

    def validate(self):
        fx = self.state.project.fx
        issues = validate_settings(fx, self.state.project.gl) if fx.tb_currency else [("ERROR", "Enter the currency of the trial balance.")]
        if fx.tb_currency and not fx.period_end:
            issues.append(("WARN", "Enter the tax period dates (they are also asked in the questionnaire)."))
        self.msgs.clear()
        for sev, m in issues:
            self.msgs.addItem(f"{sev}: {m}")
        if not issues:
            self.msgs.addItem("OK - nothing to flag." if fx.tb_currency != "AED" else "TB is in AED - no conversion needed.")
        self._errors = [m for s, m in issues if s == "ERROR"]
        self.confirm.setEnabled(not self._errors)
        self.status.setText("Confirmed" if self.state.project.fx_confirmed else ("Fix the errors above" if self._errors else "Not yet confirmed"))

    def on_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Rates CSV", str(Path.home()), "CSV (*.csv)")
        if not path:
            return
        fx = self.collect()
        c = fx.tb_currency
        monthly, spot = {}, {}
        try:
            with open(path, newline="", encoding="utf-8-sig") as fh:
                for row in csv.reader(fh):
                    if len(row) < 2:
                        continue
                    k, v = row[0].strip(), row[1].strip().replace(",", "")
                    try:
                        rate = float(v)
                    except ValueError:
                        continue                     # header row
                    if re.fullmatch(r"\d{4}-\d{2}", k):
                        monthly[k] = rate
                    else:
                        d = to_iso_date(k)
                        if d:
                            spot[d] = rate
        except Exception as e:      # noqa: BLE001
            W.warn(self, "Rates file", f"Could not read the file: {e}")
            return
        if monthly:
            fx.monthly_rates[c] = monthly
        if spot:
            fx.spot_rates[c] = spot
        self.csv_info.setText(self._csv_summary(fx))
        self.on_edit()

    def on_confirm(self):
        fx = self.collect()
        p = self.state.project
        p.fx_confirmed = True
        p.log("Currency confirmed", f"{fx.tb_currency}; method {fx.method}; source: {fx.rate_source or '-'}; reason: {fx.method_reason or '-'}; rates {fx.rates.get(fx.tb_currency)}")
        self.state.mark_dirty()
        self.validate()
        self.state.reanalyse()
        self.state.gate_changed.emit()
        self.win.goto("files")


# ======================================================================================================================
class FilesPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.state = win, win.state
        self._workers = []
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.addWidget(W.heading("Step 2 - Trial balance, general ledger and supporting files"))
        lay.addWidget(W.hint("Source files are only read - they are never changed. The trial balance can be Excel, CSV or PDF (including scanned PDFs if OCR is installed). "
                             "Review the extraction preview and confirm it before moving on."))
        # TB
        g = QGroupBox("Trial balance (required)")
        gl = QVBoxLayout(g)
        r1 = QHBoxLayout()
        self.tb_path = QLineEdit()
        b = QPushButton("Browse...")
        b.clicked.connect(self.pick_tb)
        r1.addWidget(self.tb_path, 1)
        r1.addWidget(b)
        gl.addLayout(r1)
        r2 = QHBoxLayout()
        self.tb_sheet = QComboBox()
        self.tb_header = QSpinBox()
        self.tb_header.setRange(0, 200)
        self.tb_header.setSpecialValueText("auto")
        self.ocr = QComboBox()
        self.ocr.addItems(["auto", "off", "force"])
        self.tb_load = QPushButton("Read / preview")
        self.tb_load.clicked.connect(self.load_tb)
        for lab, w in (("Sheet", self.tb_sheet), ("Header row (1-based; auto)", self.tb_header), ("OCR for PDFs", self.ocr)):
            r2.addWidget(QLabel(lab))
            r2.addWidget(w)
        r2.addWidget(self.tb_load)
        r2.addStretch(1)
        gl.addLayout(r2)
        self.tb_table = W.make_table(["Code", "Account", "Debit", "Credit", "Net (Dr +)", "Source"], stretch_col=1)
        self.tb_table.setMinimumHeight(220)
        gl.addWidget(self.tb_table)
        self.tb_info = QPlainTextEdit()
        self.tb_info.setReadOnly(True)
        self.tb_info.setMaximumHeight(90)
        gl.addWidget(self.tb_info)
        self.tb_confirm = QPushButton("The extracted trial balance is correct - confirm")
        self.tb_confirm.clicked.connect(self.confirm_tb)
        self.tb_confirm.setEnabled(False)
        gl.addWidget(self.tb_confirm)
        lay.addWidget(g)
        # GL
        g2 = QGroupBox("General ledger (optional, strongly recommended)")
        g2l = QVBoxLayout(g2)
        r3 = QHBoxLayout()
        self.gl_path = QLineEdit()
        b2 = QPushButton("Browse...")
        b2.clicked.connect(self.pick_gl)
        self.gl_sheet = QComboBox()
        self.gl_load = QPushButton("Read GL")
        self.gl_load.clicked.connect(self.load_gl)
        self.gl_clear = QPushButton("Remove GL")
        self.gl_clear.clicked.connect(self.clear_gl)
        for w in (self.gl_path, b2, QLabel("Sheet"), self.gl_sheet, self.gl_load, self.gl_clear):
            r3.addWidget(w, 1 if w is self.gl_path else 0)
        g2l.addLayout(r3)
        self.gl_info = QPlainTextEdit()
        self.gl_info.setReadOnly(True)
        self.gl_info.setMaximumHeight(90)
        g2l.addWidget(self.gl_info)
        lay.addWidget(g2)
        # prior TB
        g3 = QGroupBox("Prior-period trial balance (optional - for movement analysis)")
        g3l = QHBoxLayout(g3)
        self.pr_path = QLineEdit()
        b3 = QPushButton("Browse...")
        b3.clicked.connect(self.pick_prior)
        self.pr_load = QPushButton("Read")
        self.pr_load.clicked.connect(self.load_prior)
        self.pr_info = QLabel("")
        for w in (self.pr_path, b3, self.pr_load, self.pr_info):
            g3l.addWidget(w, 1 if w is self.pr_path else 0)
        lay.addWidget(g3)
        # supporting
        g4 = QGroupBox("Supporting documents (listed in the project and the report; not analysed by the tool)")
        g4l = QVBoxLayout(g4)
        self.sup = QListWidget()
        self.sup.setMaximumHeight(90)
        rb = QHBoxLayout()
        ba = QPushButton("Add files...")
        ba.clicked.connect(self.add_support)
        br = QPushButton("Remove selected")
        br.clicked.connect(self.rm_support)
        rb.addWidget(ba)
        rb.addWidget(br)
        rb.addStretch(1)
        g4l.addWidget(self.sup)
        g4l.addLayout(rb)
        lay.addWidget(g4)
        lay.addStretch(1)
        outer = QVBoxLayout(self)
        outer.addWidget(_scroll(inner))
        self.state.gate_changed.connect(self.refresh)
        self.state.analysed.connect(self.refresh)
        self.refresh()

    # ----------------------------------------------------------- helpers
    def _run(self, fn, args, done, label):
        self.win.busy(label)
        wk = W.Worker(fn, *args, parent=self)
        wk.done.connect(lambda r: (self.win.idle(), done(r)))
        wk.failed.connect(lambda m: (self.win.idle(), W.warn(self, "Could not read the file", m)))
        self._workers.append(wk)
        wk.start()

    def _sheets(self, path, combo):
        combo.clear()
        if Path(path).suffix.lower() in (".xlsx", ".xlsm", ".xls"):
            try:
                combo.addItems(list_sheets(path))
            except Exception as e:      # noqa: BLE001
                W.warn(self, "Workbook", str(e))
        combo.setEnabled(combo.count() > 0)

    def pick_tb(self):
        p, _ = QFileDialog.getOpenFileName(self, "Trial balance", str(Path.home()), "Trial balance (*.xlsx *.xlsm *.xls *.csv *.pdf)")
        if p:
            self.tb_path.setText(p)
            self._sheets(p, self.tb_sheet)
            self.load_tb()

    def pick_gl(self):
        p, _ = QFileDialog.getOpenFileName(self, "General ledger", str(Path.home()), "General ledger (*.xlsx *.xlsm *.xls *.csv)")
        if p:
            self.gl_path.setText(p)
            self._sheets(p, self.gl_sheet)
            self.load_gl()

    def pick_prior(self):
        p, _ = QFileDialog.getOpenFileName(self, "Prior-period trial balance", str(Path.home()), "Trial balance (*.xlsx *.xlsm *.xls *.csv *.pdf)")
        if p:
            self.pr_path.setText(p)
            self.load_prior()

    # ----------------------------------------------------------- TB
    def load_tb(self):
        path = self.tb_path.text().strip()
        if not path:
            return
        if not self.state.project.fx_confirmed:
            W.warn(self, "Currency first", "Confirm the currency settings (Step 1) before loading the trial balance.")
            return
        sheet = self.tb_sheet.currentText() or None
        hr = self.tb_header.value() - 1 if self.tb_header.value() > 0 else None
        ccy = self.state.project.fx.tb_currency

        def work():
            if hr is not None:
                return parse_tb(path, sheet, ccy, header_row=hr, ocr=self.ocr.currentText())
            return parse_tb(path, sheet, ccy, ocr=self.ocr.currentText())
        self._run(work, (), self.on_tb, "Reading trial balance...")

    def on_tb(self, tb):
        p = self.state.project
        p.tb = tb
        p.tb_confirmed = False
        p.log("TB read", f"{tb.source_file} [{tb.sheet}] {len(tb.accounts)} accounts, method {tb.extraction_method}")
        self.show_tb()
        self.state.mark_dirty()
        self.state.gate_changed.emit()

    def show_tb(self):
        tb = self.state.project.tb
        if not tb:
            self.tb_table.setRowCount(0)
            self.tb_info.setPlainText("")
            self.tb_confirm.setEnabled(False)
            return
        W.fill_table(self.tb_table, [[a.code, a.name, W.money(a.debit, 2), W.money(a.credit, 2), W.money(a.net, 2), a.source_ref] for a in tb.accounts], right_cols=(2, 3, 4))
        td, tc = sum(a.debit for a in tb.accounts), sum(a.credit for a in tb.accounts)
        lines = [f"{len(tb.accounts)} accounts; total debits {td:,.2f}; total credits {tc:,.2f}; difference {td - tc:,.2f}", f"Extraction: {tb.extraction_method}. {tb.sign_convention}"]
        if tb.title:
            lines.append(f"Text above the table: {tb.title[:160]}")
        lines += [f"WARNING: {w}" for w in tb.warnings]
        self.tb_info.setPlainText("\n".join(lines))
        self.tb_confirm.setEnabled(bool(tb.accounts))
        self.tb_confirm.setText("Trial balance confirmed" if self.state.project.tb_confirmed else "The extracted trial balance is correct - confirm")

    def confirm_tb(self):
        p = self.state.project
        p.tb_confirmed = True
        p.log("TB confirmed", f"{len(p.tb.accounts)} accounts")
        self.tb_confirm.setText("Trial balance confirmed")
        self.state.mark_dirty()
        self.state.reanalyse()
        self.state.gate_changed.emit()
        if self.state.analysis:
            self.win.goto("mapping")
        elif self.state.error:
            W.warn(self, "Analysis", self.state.error)

    # ----------------------------------------------------------- GL
    def load_gl(self):
        path = self.gl_path.text().strip()
        if not path:
            return
        sheet = self.gl_sheet.currentText() or None
        self._run(lambda: parse_gl(path, sheet), (), self.on_gl, "Reading general ledger...")

    def on_gl(self, gl):
        p = self.state.project
        p.gl = gl
        dates = sorted(l.date for l in gl.lines if l.date)
        txt = [f"{len(gl.lines):,} lines; dates {dates[0] if dates else '?'} to {dates[-1] if dates else '?'}"] + [f"WARNING: {w}" for w in gl.warnings]
        self.gl_info.setPlainText("\n".join(txt))
        p.log("GL read", f"{gl.source_file} [{gl.sheet}] {len(gl.lines)} lines")
        self.state.mark_dirty()
        self.state.reanalyse()
        self.state.gate_changed.emit()

    def clear_gl(self):
        self.state.project.gl = None
        self.gl_info.setPlainText("")
        self.state.project.log("GL removed")
        self.state.mark_dirty()
        self.state.reanalyse()

    # ----------------------------------------------------------- prior
    def load_prior(self):
        path = self.pr_path.text().strip()
        if not path:
            return
        ccy = self.state.project.fx.tb_currency
        self._run(lambda: parse_tb(path, None, ccy), (), self.on_prior, "Reading prior-period TB...")

    def on_prior(self, tb):
        self.state.project.prior_tb = tb
        self.pr_info.setText(f"{len(tb.accounts)} accounts")
        self.state.project.log("Prior TB read", tb.source_file)
        self.state.mark_dirty()
        self.state.reanalyse()

    # ----------------------------------------------------------- supporting
    def add_support(self):
        ps, _ = QFileDialog.getOpenFileNames(self, "Supporting documents", str(Path.home()))
        for p in ps:
            if p not in self.state.project.supporting_files:
                self.state.project.supporting_files.append(p)
        self.state.mark_dirty()
        self.refresh_support()

    def rm_support(self):
        for it in self.sup.selectedItems():
            if it.text() in self.state.project.supporting_files:
                self.state.project.supporting_files.remove(it.text())
        self.state.mark_dirty()
        self.refresh_support()

    def refresh_support(self):
        self.sup.clear()
        for p in self.state.project.supporting_files:
            self.sup.addItem(p)

    def refresh(self):
        p = self.state.project
        ok = p.fx_confirmed
        for w in (self.tb_load, self.tb_path):
            w.setEnabled(ok)
        if p.tb:
            self.tb_path.setText(self.tb_path.text() or p.tb.source_file)
            if not self.tb_table.rowCount():
                self.show_tb()
        if p.gl and not self.gl_info.toPlainText():
            self.gl_info.setPlainText(f"{len(p.gl.lines):,} lines from {p.gl.source_file} (loaded from the project)")
        if p.prior_tb and not self.pr_info.text():
            self.pr_info.setText(f"{len(p.prior_tb.accounts)} accounts")
        self.refresh_support()
