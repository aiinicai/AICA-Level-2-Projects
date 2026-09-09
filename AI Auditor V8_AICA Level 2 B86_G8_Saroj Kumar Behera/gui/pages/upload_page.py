"""
AI Auditor V8 - Upload & Extraction Page
Drag-and-drop file upload, format detection, unit scale configuration, and background extraction worker.
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QComboBox, QCheckBox, QProgressBar, QMessageBox, QGroupBox, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

from extraction.excel_extractor import ExcelExtractor
from extraction.pdf_extractor import PDFExtractor
from extraction.ocr_engine import OCREngine
from analysis.mapper import TaxonomyMapper
from analysis.ratio_engine import RatioEngine
from analysis.trend_engine import TrendEngine
from analysis.variance_engine import VarianceEngine
from analysis.risk_engine import RiskEngine
from config.constants import UNITS_MAP
from core.models import FinancialModel

class ExtractionWorker(QThread):
    finished = pyqtSignal(object)  # returns FinancialModel
    error = pyqtSignal(str)
    progress = pyqtSignal(str, int)

    def __init__(self, filepath: str, unit_label: str, use_ocr: bool, threshold: float):
        super().__init__()
        self.filepath = filepath
        self.unit_label = unit_label
        self.use_ocr = use_ocr
        self.threshold = threshold

    def run(self):
        try:
            self.progress.emit("Reading file and detecting structure...", 20)
            ext = os.path.splitext(self.filepath)[1].lower()

            if ext in [".xlsx", ".xls", ".xlsm"]:
                extractor = ExcelExtractor(self.filepath)
                model = extractor.extract()
            elif ext == ".pdf":
                self.progress.emit("Extracting tables and text from PDF...", 35)
                extractor = PDFExtractor(self.filepath, use_ocr_if_needed=self.use_ocr)
                model = extractor.extract()
            else:
                self.error.emit(f"Unsupported file extension: {ext}. Please upload an Excel or PDF file.")
                return

            if self.unit_label in UNITS_MAP:
                model.company_info.unit_label = self.unit_label
                model.company_info.unit_multiplier = UNITS_MAP[self.unit_label]

            self.progress.emit("Classifying line items & taxonomy mapping...", 55)
            TaxonomyMapper.map_model(model)

            self.progress.emit("Computing 30 standard financial ratios...", 75)
            RatioEngine.calculate_all_ratios(model)

            self.progress.emit("Performing trend & variance analysis...", 90)
            VarianceEngine.analyze_variations(model, threshold_pct=self.threshold)
            RiskEngine.evaluate_risks(model)

            self.progress.emit("Analysis complete!", 100)
            self.finished.emit(model)
        except Exception as e:
            self.error.emit(f"Extraction failed: {str(e)}")


class UploadPage(QWidget):
    model_loaded = pyqtSignal(object)  # Signal when model is ready

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.selected_filepath = None
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        # Page Title
        lbl_title = QLabel("Upload Financial Statements")
        lbl_title.setProperty("class", "page-title")
        lbl_sub = QLabel("Select or drag-and-drop your Balance Sheet & Profit & Loss files (Excel .xlsx / .xls or PDF).")
        lbl_sub.setProperty("class", "page-subtitle")
        main_layout.addWidget(lbl_title)
        main_layout.addWidget(lbl_sub)

        # 1. Drop Zone Card
        self.drop_card = QFrame()
        self.drop_card.setProperty("class", "card")
        self.drop_card.setStyleSheet("""
            QFrame.card {
                border: 2px dashed #94A3B8;
                border-radius: 10px;
                background-color: #F8FAFC;
                padding: 30px;
            }
            QFrame.card:hover {
                border-color: #2563EB;
                background-color: #EFF6FF;
            }
        """)
        d_layout = QVBoxLayout(self.drop_card)
        d_layout.setAlignment(Qt.AlignCenter)
        d_layout.setSpacing(12)

        lbl_icon = QLabel("📁")
        lbl_icon.setStyleSheet("font-size: 38px;")
        lbl_icon.setAlignment(Qt.AlignCenter)
        d_layout.addWidget(lbl_icon)

        self.lbl_drop_text = QLabel("Drag & Drop your Excel (.xlsx / .xls) or PDF file here\nor click Browse below")
        self.lbl_drop_text.setAlignment(Qt.AlignCenter)
        self.lbl_drop_text.setStyleSheet("font-size: 14px; font-weight: 500; color: #334155;")
        d_layout.addWidget(self.lbl_drop_text)

        btn_browse = QPushButton("Browse File from Computer")
        btn_browse.setProperty("class", "primary-btn")
        btn_browse.setFixedWidth(240)
        btn_browse.clicked.connect(self._choose_file)
        d_layout.addWidget(btn_browse, alignment=Qt.AlignCenter)

        main_layout.addWidget(self.drop_card)

        # 2. Options Grid
        opt_group = QGroupBox("Extraction & Analysis Configuration")
        opt_layout = QHBoxLayout(opt_group)
        opt_layout.setContentsMargins(16, 16, 16, 16)
        opt_layout.setSpacing(20)

        # Unit Scale
        unit_vbox = QVBoxLayout()
        unit_vbox.addWidget(QLabel("Currency & Reporting Unit:"))
        self.combo_unit = QComboBox()
        for u in UNITS_MAP.keys():
            self.combo_unit.addItem(u)
        self.combo_unit.setCurrentText("₹ in Lakhs (1,00,00,000)" if "₹ in Lakhs" in self.combo_unit.currentText() else "₹ in Lakhs (1,00,000)")
        unit_vbox.addWidget(self.combo_unit)
        opt_layout.addLayout(unit_vbox)

        # OCR Checkbox
        self.chk_ocr = QCheckBox("Enable OCR for scanned/image PDFs (Tesseract)")
        self.chk_ocr.setChecked(True)
        opt_layout.addWidget(self.chk_ocr)

        main_layout.addWidget(opt_group)

        # 3. Selected File Info & Process Button
        self.info_card = QFrame()
        self.info_card.setProperty("class", "card")
        i_layout = QHBoxLayout(self.info_card)
        
        self.lbl_selected_file = QLabel("No file selected yet.")
        self.lbl_selected_file.setStyleSheet("font-weight: 500; color: #0F172A;")
        i_layout.addWidget(self.lbl_selected_file, 1)

        self.btn_process = QPushButton("Extract & Analyze Statement")
        self.btn_process.setProperty("class", "success-btn")
        self.btn_process.setEnabled(False)
        self.btn_process.clicked.connect(self._start_extraction)
        i_layout.addWidget(self.btn_process)

        main_layout.addWidget(self.info_card)

        # 4. Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #2563EB; font-weight: 500;")
        main_layout.addWidget(self.lbl_status)

        main_layout.addStretch()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            filepath = urls[0].toLocalFile()
            self._set_selected_file(filepath)

    def _choose_file(self):
        file_filter = "Financial Statement Files (*.xlsx *.xls *.xlsm *.pdf);;Excel Files (*.xlsx *.xls *.xlsm);;PDF Files (*.pdf)"
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Financial Statement File", "", file_filter)
        if filepath:
            self._set_selected_file(filepath)

    def _set_selected_file(self, filepath: str):
        if not os.path.exists(filepath):
            return
        self.selected_filepath = filepath
        self.lbl_selected_file.setText(f"Selected: {os.path.basename(filepath)} ({round(os.path.getsize(filepath)/1024, 1)} KB)")
        self.lbl_drop_text.setText(f"Selected File: {os.path.basename(filepath)}")
        self.btn_process.setEnabled(True)

    def _start_extraction(self):
        if not self.selected_filepath:
            return

        self.btn_process.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        self.lbl_status.setText("Initiating extraction engine...")

        self.worker = ExtractionWorker(
            filepath=self.selected_filepath,
            unit_label=self.combo_unit.currentText(),
            use_ocr=self.chk_ocr.isChecked(),
            threshold=5.0
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, msg: str, val: int):
        self.lbl_status.setText(msg)
        self.progress_bar.setValue(val)

    def _on_finished(self, model: FinancialModel):
        self.lbl_status.setText("Extraction and analysis completed successfully!")
        self.btn_process.setEnabled(True)
        self.model_loaded.emit(model)
        QMessageBox.information(self, "Extraction Successful", f"Successfully analyzed financial statements for {model.company_info.name}!")

    def _on_error(self, err_msg: str):
        self.lbl_status.setText(f"Error: {err_msg}")
        self.progress_bar.setVisible(False)
        self.btn_process.setEnabled(True)
        QMessageBox.critical(self, "Extraction Error", err_msg)
