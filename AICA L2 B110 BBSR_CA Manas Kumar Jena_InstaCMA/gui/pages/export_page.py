"""Export: the CMA workbook in the built-in format and one A4 PDF of all pages."""
import os
import subprocess
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QGroupBox, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QCheckBox, QComboBox,
                             QListWidget, QListWidgetItem, QPlainTextEdit, QVBoxLayout, QFileDialog, QMessageBox,
                             QApplication)

from analysis import validator2 as V
from core.audit_trail import TRAIL
from core.models import STATEMENT_KINDS
from gui.pages.base_page import BasePage
from gui.pages.common import buttons

SHEETS = ["Covering Letter", "Assessment Note", "FORM-II", "FORM-III", "FORM-IV", "FORM-VI", "ABF", "CHECK", "RATIOS",
          "CRA-DATA", "ANALYSIS", "Profit and Loss", "Balance Sheet", "Term Loan", "CMA Tests", "DSCR",
          "Projection Basis", "FORM-V MPBF", "Cash Flow", "Break-even", "Sensitivity", "GST Cross-check", "Red Flags",
          "Projected vs Actual", "Source Mapping", "Audit Trail"]


def open_path(p):
    try:
        if sys.platform.startswith("win"):
            os.startfile(p)  # noqa
        else:
            subprocess.Popen(["xdg-open" if sys.platform != "darwin" else "open", p])
    except Exception:
        pass


def safe(name):
    return "".join(ch for ch in (name or "Client") if ch not in '\\/:*?"<>|').strip()


class ExportPage(BasePage):
    title = "Export"
    subtitle = ("Creates 'CMA data - <client>.xlsx' in the built-in format and one A4 PDF of all pages "
                "(covering letter first). The PDF is checked page by page before it is saved.")

    def build(self):
        g = QGroupBox("Output")
        f = QFormLayout(g)
        self.folder = QLineEdit()
        b = QPushButton("Browse...")
        b.setObjectName("Secondary")
        b.clicked.connect(lambda *_: self.browse())
        h = QHBoxLayout()
        h.addWidget(self.folder)
        h.addWidget(b)
        f.addRow("Folder", h)
        self.unit = QComboBox()
        self.unit.addItems(["Actual", "Thousand", "Lakh", "Crore"])
        f.addRow("Amounts in FORM sheets", self.unit)
        self.x = QCheckBox("Excel workbook (.xlsx)")
        self.x.setChecked(True)
        self.x.setEnabled(False)
        self.p = QCheckBox("PDF of all pages (A4)")
        self.p.setChecked(True)
        f.addRow("", self.x)
        f.addRow("", self.p)
        self.body.addWidget(g)
        g2 = QGroupBox("Pages in the PDF (all ticked by default)")
        v = QVBoxLayout(g2)
        self.sheets = QListWidget()
        self.sheets.setMinimumHeight(220)
        for s in SHEETS:
            it = QListWidgetItem(s)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked)
            self.sheets.addItem(it)
        v.addWidget(self.sheets)
        self.body.addWidget(g2)
        self.body.addLayout(buttons(self, [("Export now", self.export, "Accent")]))
        g3 = QGroupBox("Export log and page check")
        v3 = QVBoxLayout(g3)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(200)
        v3.addWidget(self.log)
        self.body.addWidget(g3)

    def refresh(self):
        if not self.folder.text():
            self.folder.setText(self.app.settings.get("output_folder", ""))
        self.unit.setCurrentText(self.project.intake.unit or "Actual")
        no_tl = not self.project.intake.has_tl
        for i in range(self.sheets.count()):
            it = self.sheets.item(i)
            if it.text() == "Term Loan" and no_tl:
                it.setCheckState(Qt.Unchecked)

    def browse(self):
        d = QFileDialog.getExistingDirectory(self, "Output folder", self.folder.text())
        if d:
            self.folder.setText(d)

    def export(self):
        p, r = self.project, self.result
        if not r or not r.years:
            QMessageBox.information(self, "Export", "Set the years and upload the statements first.")
            return
        checks = V.validate(p, r)
        if V.has_errors(checks):
            QMessageBox.warning(self, "Export blocked", "Fix these first:\n\n" +
                                "\n\n".join(m for lv, m in checks if lv == V.ERROR))
            self.app.goto("Checks & warnings")
            return
        p.intake.unit = self.unit.currentText()
        folder = os.path.join(self.folder.text().strip() or os.path.expanduser("~"), safe(p.intake.client_name))
        os.makedirs(folder, exist_ok=True)
        base = "CMA data - %s" % safe(p.intake.client_name)
        xlsx = os.path.join(folder, base + ".xlsx")
        self.log.clear()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            from reports.cma_writer import generate_workbook
            from analysis.engine import compute
            r = compute(p, self.app.settings.get("defaults"))
            TRAIL.log("Export", xlsx)
            generate_workbook(p, r, xlsx, self.app.settings, TRAIL.rows())
            self.log.appendPlainText("Workbook: " + xlsx)
            if self.p.isChecked():
                self._pdf(xlsx, os.path.join(folder, base + ".pdf"))
            # keep the projections for next year's projected-vs-actual comparison
            for y in r.future:
                if y["kind"] not in STATEMENT_KINDS:
                    p.history[str(y["fy"])] = {k: y.get(k) for k in ("sales", "pat", "stock", "debtors", "creditors",
                                                                     "bank_balance")}
            jf = os.path.join(folder, safe(p.intake.client_name) + ".cma.json")
            p.save(jf)
            self.app.current_file = jf
            self.log.appendPlainText("Client file (for next year): " + jf)
        except PermissionError:
            QMessageBox.warning(self, "Export", "A file is open in Excel or a PDF viewer. Close it and export again.")
            return
        except Exception as e:
            QMessageBox.critical(self, "Export", "Export failed: %s" % e)
            return
        finally:
            QApplication.restoreOverrideCursor()
        warn = [m for lv, m in checks if lv == V.WARN] + r.warnings + r.decisions
        if warn:
            self.log.appendPlainText("\nPoints to review:")
            for w in warn:
                self.log.appendPlainText(" - " + w)
        self.app.settings["output_folder"] = self.folder.text().strip()
        self.app.persist_settings()
        open_path(folder)

    def _pdf(self, xlsx, pdf):
        from reports import pdf_export
        import openpyxl
        import shutil
        import tempfile
        drop = [self.sheets.item(i).text() for i in range(self.sheets.count())
                if self.sheets.item(i).checkState() != Qt.Checked]
        src = xlsx
        if drop:
            tmp = os.path.join(tempfile.mkdtemp(), os.path.basename(xlsx))
            wb = openpyxl.load_workbook(xlsx)
            for name in drop:
                if name in wb.sheetnames:
                    wb[name].sheet_state = "hidden"
            wb.save(tmp)
            src = tmp
        try:
            out, rep = pdf_export.export_pdf(src, pdf, log=self.log.appendPlainText)
        except pdf_export.NoConverter as e:
            self.log.appendPlainText("PDF not made: neither Microsoft Excel nor LibreOffice was found (%s). Open the "
                                     "workbook in Excel and use File > Save as > PDF (Entire workbook)." % e)
            return
        if src != xlsx and not drop:
            shutil.copyfile(src, xlsx)
        self.log.appendPlainText("PDF: %s  (%d pages, made with %s)" % (out, rep["pages"], rep["engine"]))
        self.log.appendPlainText("Page check: %s" % ("all pages A4, no blank or spill-over pages" if not rep["problems"]
                                                     else "; ".join(rep["problems"])))
