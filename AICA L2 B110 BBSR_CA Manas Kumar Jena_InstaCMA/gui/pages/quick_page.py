"""Quick CMA: pick the file, type the loan figures, press one button."""
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QFormLayout, QHBoxLayout, QLineEdit, QPushButton, QFileDialog, QComboBox, QSpinBox,
                             QPlainTextEdit, QMessageBox, QApplication, QGroupBox, QLabel, QCheckBox)

from gui.pages.base_page import BasePage
from gui.pages.common import money, pct
from gui.pages.export_page import open_path


class QuickPage(BasePage):
    title = "Quick CMA"
    subtitle = ("Choose the client's P&L and balance sheet file (Excel or PDF) and type the loan figures. Then press "
                "1. Calculate (bank tests shown below), 2. Make Excel, and 3. Make PDF - each asks where to save. "
                "Use the other pages only if you want to change something.")

    def build(self):
        self.paths = []
        g = QGroupBox("1. Client's statements")
        f = QFormLayout(g)
        row = QHBoxLayout()
        self.file = QLineEdit()
        self.file.setReadOnly(True)
        self.file.setPlaceholderText("Excel or PDF with the P&L and balance sheet (one or more files)")
        b = QPushButton("Choose file...")
        b.clicked.connect(lambda *_: self.pick())
        row.addWidget(self.file)
        row.addWidget(b)
        f.addRow("File", row)
        self.name = QLineEdit()
        self.name.setPlaceholderText("read from the file")
        f.addRow("Client name", self.name)
        self.body.addWidget(g)

        g = QGroupBox("2. Loan")
        f = QFormLayout(g)
        self.cc = money()
        self.cc_rate = pct()
        self.cc_rate.setValue(10)
        self.tl = money()
        self.tl_rate = pct()
        self.tl_rate.setValue(10)
        self.tl_months = QSpinBox()
        self.tl_months.setRange(6, 240)
        self.tl_months.setValue(60)
        self.tl_months.setSuffix(" months")
        self.tl_method = QComboBox()
        self.tl_method.addItems(["Equal EMI", "Equal Principal"])
        self.tl_use = QComboBox()
        self.tl_use.addItems(["Capex", "Working capital"])
        f.addRow("Cash credit limit (Rs)", self.cc)
        f.addRow("Cash credit interest %", self.cc_rate)
        f.addRow("Term loan amount (Rs, 0 = none)", self.tl)
        f.addRow("Term loan interest %", self.tl_rate)
        f.addRow("Term loan tenure", self.tl_months)
        f.addRow("Repayment", self.tl_method)
        f.addRow("Term loan used for", self.tl_use)
        self.proj = QSpinBox()
        self.proj.setRange(1, 5)
        self.proj.setValue(2)
        self.proj.setSuffix(" projected year(s)")
        f.addRow("Projected years", self.proj)
        self.fit = QCheckBox("Keep DSCR within the bank's range (adjusts estimated / projected gross profit only)")
        self.fit.setChecked(True)
        f.addRow("DSCR", self.fit)
        self.fit_to = QCheckBox("Keep turnover in the green (raises estimated / projected sales growth where needed)")
        self.fit_to.setChecked(True)
        f.addRow("Turnover", self.fit_to)
        self.unit = QComboBox()
        self.unit.addItems(["Actual", "Thousand", "Lakh", "Crore"])
        f.addRow("Show figures in", self.unit)
        self.body.addWidget(g)

        row = QHBoxLayout()
        self.b_calc = QPushButton("1. Calculate")
        self.b_xl = QPushButton("2. Make Excel")
        self.b_pdf = QPushButton("3. Make PDF")
        for b, fn in ((self.b_calc, self.calculate), (self.b_xl, self.make_excel), (self.b_pdf, self.make_pdf)):
            b.setObjectName("Accent")
            b.setMinimumHeight(44)
            b.clicked.connect(lambda *_, f=fn: f())
            row.addWidget(b)
        self.body.addLayout(row)
        self.kind_box = QGroupBox("Type of each actual year (change if needed - no need to calculate again)")
        self.kind_lay = QHBoxLayout(self.kind_box)
        self.kind_box.setVisible(False)
        self.body.addWidget(self.kind_box)
        self.kind_combos = {}
        self.last_paths = None
        self.b_xl.setEnabled(False)
        self.b_pdf.setEnabled(False)
        self.p = self.r = self.xlsx = None
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(220)
        self.body.addWidget(QLabel("Result"))
        self.body.addWidget(self.log)

    def pick(self):
        ps, _ = QFileDialog.getOpenFileNames(self, "Client's statements", self.app.settings.get("last_folder", ""),
                                             "Statements (*.xlsx *.xlsm *.xls *.pdf *.png *.jpg *.jpeg)")
        if not ps:
            return
        self.paths = ps
        self.file.setText("; ".join(os.path.basename(p) for p in ps))
        self.app.settings["last_folder"] = os.path.dirname(ps[0])
        from core.quick import read_heading
        self.name.setText(read_heading(ps).get("name", ""))

    def say(self, msg):
        self.log.appendPlainText(msg)
        QApplication.processEvents()

    def _folder(self):
        from core import quick
        return os.path.join(os.path.dirname(self.paths[0]), "CMA - " + quick.safe(self.p.intake.client_name))

    def calculate(self):
        """Read the file, tally, fit DSCR, run the bank tests - no files yet."""
        from core import quick
        from analysis.engine import compute
        if not self.paths:
            QMessageBox.information(self, "Quick CMA", "Choose the client's file first.")
            return
        if self.cc.value() <= 0 and self.tl.value() <= 0:
            QMessageBox.information(self, "Quick CMA", "Enter the cash credit limit or the term loan amount.")
            return
        opts = dict(client_name=self.name.text().strip(), cc_limit=self.cc.value(), cc_rate=self.cc_rate.value(),
                    tl_amount=self.tl.value(), tl_rate=self.tl_rate.value(), tl_months=self.tl_months.value(),
                    tl_method=self.tl_method.currentText(), tl_use=self.tl_use.currentText(),
                    projected=self.proj.value(), unit=self.unit.currentText())
        if self.last_paths == list(self.paths) and self.app.project is not None:
            # same client: keep the year types chosen here or on the Client & years page
            opts["kinds"] = {y.fy: y.kind for y in self.app.project.years if y.from_statement}
        self.log.clear()
        self.b_xl.setEnabled(False)
        self.b_pdf.setEnabled(False)
        self.p = self.r = self.xlsx = None
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            p, left = quick.build(self.paths, opts, self.app.settings, log=self.say)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Quick CMA", "Could not read the file: %s" % e)
            return
        QApplication.restoreOverrideCursor()
        if left:
            txt = "\n".join("FY %d-%02d: Rs %s" % (fy - 1, fy % 100, format(int(round(abs(d))), ","))
                            for fy, d in left)
            ans = QMessageBox.question(
                self, "Client's balance sheet does not tally",
                "The client's own balance sheet does not tally:\n\n%s\n\nYes = continue, showing the difference "
                "as a separate line 'Difference in client's balance sheet (to be checked)'.\nNo = stop, so I can "
                "correct the client's file (or fix it on the Review page)." % txt)
            if ans != QMessageBox.Yes:
                self.app.project = p
                self.app.recompute()
                self.say("Stopped. Correct the client's file and press Calculate again, or use Review & group.")
                return
            quick.carry_difference(p, left, self.say)
        self.say("")
        self.say("Adjustments (audited / actual / provisional figures are not changed):")
        notes = quick.fit(p, self.app.settings, log=lambda m: self.say("  " + m),
                          turnover=self.fit_to.isChecked(), dscr=self.fit.isChecked())
        if not notes:
            self.say("  Nothing needed - all bank rules already met.")
        r = compute(p, self.app.settings.get("defaults"))
        self.app.project = p
        self.app.current_file = None
        self.app.recompute()
        self.p, self.r = p, r
        self.say("")
        self.say("Bank tests:")
        for line in quick.summary(r):
            self.say("  " + line)
        pts = r.warnings + r.decisions + ([] if self.fit.isChecked() else quick.capacity_note(p, r, self.app.settings))
        if pts:
            self.say("")
            self.say("Points to look at:")
            for w in pts:
                self.say("  - " + w)
        self.say("")
        self.say("Calculated. Press 2. Make Excel.")
        self.last_paths = list(self.paths)
        self._show_kinds()
        self.b_xl.setEnabled(True)

    def _show_kinds(self):
        from core.models import STATEMENT_KINDS
        while self.kind_lay.count():
            w = self.kind_lay.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        self.kind_combos = {}
        for y in self.p.year_list():
            if not y.from_statement:
                continue
            self.kind_lay.addWidget(QLabel("FY %s" % y.label))
            cb = QComboBox()
            cb.addItems(list(STATEMENT_KINDS))
            cb.setCurrentText(y.kind)
            cb.currentTextChanged.connect(lambda txt, fy=y.fy: self._set_kind(fy, txt))
            self.kind_combos[y.fy] = cb
            self.kind_lay.addWidget(cb)
        self.kind_lay.addStretch(1)
        self.kind_box.setVisible(True)

    def _set_kind(self, fy, kind):
        for y in self.p.years:
            if y.fy == fy:
                y.kind = kind
        self.app.recompute()
        self.say("FY %d-%02d set as %s. Press 2. Make Excel." % (fy - 1, fy % 100, kind))

    def make_excel(self):
        from core import quick
        if self.p is None:
            QMessageBox.information(self, "Quick CMA", "Press 1. Calculate first.")
            return
        start = os.path.join(self.app.settings.get("cma_save_folder") or os.path.dirname(self.paths[0]),
                             "CMA data - %s.xlsx" % quick.safe(self.p.intake.client_name))
        xlsx, _ = QFileDialog.getSaveFileName(self, "Save the CMA Excel file as", start, "Excel workbook (*.xlsx)")
        if not xlsx:
            return
        if not xlsx.lower().endswith(".xlsx"):
            xlsx += ".xlsx"
        folder = os.path.dirname(xlsx)
        self.p.intake.unit = self.unit.currentText()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            xlsx, _, r, _ = quick.export(self.p, folder, self.app.settings, log=self.say, pdf=False,
                                         xlsx_path=xlsx, save_json=False)
        except PermissionError:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Quick CMA", "The CMA Excel file is open. Close it and press Make Excel again.")
            return
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Quick CMA", "Could not make the Excel file:\n\n%s" % e)
            return
        QApplication.restoreOverrideCursor()
        self.xlsx = xlsx
        self.app.settings["cma_save_folder"] = folder
        self.app.persist_settings()
        self.b_pdf.setEnabled(True)
        self.say("Excel ready. Check it if you wish, then press 3. Make PDF.")

    def make_pdf(self):
        from reports import pdf_export
        if not self.xlsx or not os.path.exists(self.xlsx):
            QMessageBox.information(self, "Quick CMA", "Press 2. Make Excel first.")
            return
        pdf, _ = QFileDialog.getSaveFileName(self, "Save the PDF as", os.path.splitext(self.xlsx)[0] + ".pdf",
                                             "PDF (*.pdf)")
        if not pdf:
            return
        if not pdf.lower().endswith(".pdf"):
            pdf += ".pdf"
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            out, rep = pdf_export.export_pdf(self.xlsx, pdf, log=lambda *a: None)
        except PermissionError:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Quick CMA", "Close the Excel file and the PDF, then press Make PDF again.")
            return
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Quick CMA", "PDF not made: %s\n\nOpen the Excel file and use File > Save as "
                                                    "> PDF." % e)
            return
        QApplication.restoreOverrideCursor()
        self.say("PDF: %s (%d pages)" % (out, rep["pages"]))
