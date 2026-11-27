"""Upload & read: PDF (normal / scanned), Excel (any layout) or photos."""
import os
import shutil

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout, QListWidget, QFormLayout, QSpinBox, QCheckBox, QComboBox,
                             QPlainTextEdit, QFileDialog, QMessageBox, QApplication, QLabel)

from ai.providers import ai_enabled
from analysis.layout import SINGLE_HEADS
from extraction.reader import read_files
from gui.pages.base_page import BasePage
from gui.pages.common import buttons
from reports.master_template import resource_path


class UploadPage(BasePage):
    title = "Upload statements"
    subtitle = ("Add the P&L and Balance Sheet of every Audited / Provisional year (and of estimated / projected "
                "years if you chose the client's own figures). Excel is read directly; PDFs and photos are read by "
                "the AI model set in Settings, or by OCR if no model is set.")

    def build(self):
        g = QGroupBox("Files")
        v = QVBoxLayout(g)
        self.files = QListWidget()
        self.files.setMinimumHeight(140)
        v.addWidget(self.files)
        v.addLayout(buttons(self, [("Add files...", self.add, None), ("Remove selected", self.remove, "Secondary"),
                                   ("Clear", self.files.clear, "Secondary"),
                                   ("Save blank CMA Input Template...", self.template, "Secondary")]))
        self.body.addWidget(g)
        g2 = QGroupBox("Reading options")
        f = QFormLayout(g2)
        self.ai = QCheckBox("Read PDFs and photos with the AI model")
        self.ai_note = QLabel("")
        f.addRow(self.ai, self.ai_note)
        self.year = QSpinBox()
        self.year.setRange(2001, 2100)
        self.year.setValue(2026)
        self.use_year = QCheckBox("Use this year ending 31 March when a file does not show its year")
        f.addRow(self.year, self.use_year)
        self.st = QComboBox()
        self.st.addItems(["Detect automatically", "Profit & Loss only", "Balance Sheet only"])
        f.addRow("Statement", self.st)
        self.replace = QCheckBox("Replace lines already read for the same year(s)")
        self.replace.setChecked(True)
        f.addRow("", self.replace)
        self.body.addWidget(g2)
        self.body.addLayout(buttons(self, [("Read files and group heads", self.read, "Accent")]))
        g3 = QGroupBox("Reading log")
        v3 = QVBoxLayout(g3)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(200)
        v3.addWidget(self.log)
        self.body.addWidget(g3)
        self.body.addStretch()

    def refresh(self):
        on = ai_enabled(self.app.settings)
        self.ai.setEnabled(on)
        self.ai.setChecked(on and self.app.settings.get("use_ai_for_pdf", True))
        self.ai_note.setText("" if on else "No AI model set - see Settings (OCR will be used)")

    def add(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select statements", "",
                                                "Statements (*.pdf *.xlsx *.xls *.xlsm *.png *.jpg *.jpeg *.tif *.tiff)")
        for p in paths:
            self.files.addItem(p)

    def remove(self):
        for it in self.files.selectedItems():
            self.files.takeItem(self.files.row(it))

    def template(self):
        dst, _ = QFileDialog.getSaveFileName(self, "Save template", "CMA_Input_Template.xlsx", "Excel (*.xlsx)")
        if dst:
            shutil.copyfile(resource_path("samples", "CMA_Input_Template.xlsx"), dst)
            self.app.status("Template saved: " + dst)

    def read(self):
        paths = [self.files.item(i).text() for i in range(self.files.count())]
        if not paths:
            QMessageBox.information(self, "Upload", "Add at least one file.")
            return
        if self.project.locked and QMessageBox.question(
                self, "Locked", "The actual years are locked. Unlock and read again?") != QMessageBox.Yes:
            return
        self.project.locked = False
        self.log.clear()
        force = {0: None, 1: "PL", 2: "BS"}[self.st.currentIndex()]
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            lines = read_files(paths, self.app.settings, self.ai.isChecked(),
                               self.year.value() if self.use_year.isChecked() else None, force,
                               log=lambda m: (self.log.appendPlainText(m), QApplication.processEvents()))
        finally:
            QApplication.restoreOverrideCursor()
        if not lines:
            self.log.appendPlainText("Nothing was read. Set the year option, or use the CMA Input Template.")
            return
        years = sorted({ln.year for ln in lines})
        if self.replace.isChecked():
            self.project.source_lines = [s for s in self.project.source_lines if s.year not in years]
        self.project.source_lines += lines
        self.project.build_lines_from_sources(SINGLE_HEADS)
        known = {y.fy for y in self.project.years}
        missing = [y for y in years if y not in known]
        if missing:
            self.log.appendPlainText("\nNote: year(s) %s are not in the year table - add them on Client & years."
                                     % ", ".join(str(m) for m in missing))
        doubt = sum(1 for s in lines if not s.head or s.confidence < 70 or s.head == "misc_exp")
        self.log.appendPlainText("\n%d values read for year(s) ending %s; %d need a look on the Review page." % (
            len(lines), ", ".join(str(y) for y in years), doubt))
        self.app.recompute()
        self.app.goto("Review & group")
