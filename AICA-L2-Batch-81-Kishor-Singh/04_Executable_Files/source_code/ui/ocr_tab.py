"""OCR/Scan tab: make scanned PDFs searchable, entirely offline (Tesseract)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.ocr_engine import SUPPORTED_LANGUAGES, is_tesseract_available, make_searchable_pdf
from core.pdf_engine import validate_pdf_integrity
from models.job import BatchResult, SigningJob
from ui.app_context import AppContext
from ui.widgets.dialogs import BatchConfirmationDialog, ProgressDialog, ReportDialog, show_error
from utils.database import AuditEntry
from utils.file_utils import compute_output_path, find_pdfs_in_folder
from utils.logging_utils import get_logger, log_operation
from workers.batch_worker import BatchWorker
from models.enums import CollisionPolicy, NamingMode

logger = get_logger("ocr_tab")


class OCRTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.jobs: list[SigningJob] = []
        self._worker: BatchWorker | None = None
        self._progress_dialog: ProgressDialog | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        if not is_tesseract_available(self.ctx.config.settings.tesseract_path):
            warn = QLabel(
                "Tesseract OCR was not detected on this computer. Install it from "
                "https://github.com/UB-Mannheim/tesseract/wiki, or set its path in Settings -> OCR, "
                "then reopen this tab."
            )
            warn.setWordWrap(True)
            warn.setStyleSheet("color: #d64545; font-weight: 600;")
            root.addWidget(warn)

        toolbar = QHBoxLayout()
        self.btn_add_files = QPushButton("Add Files")
        self.btn_add_folder = QPushButton("Add Folder")
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_remove.setObjectName("SecondaryButton")
        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.setObjectName("DangerButton")
        for b in (self.btn_add_files, self.btn_add_folder, self.btn_remove, self.btn_clear):
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["File Name", "Status"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 1)

        options_group = QGroupBox("OCR Options")
        form = QFormLayout(options_group)
        self.combo_language = QComboBox()
        self.combo_language.addItems(list(SUPPORTED_LANGUAGES.keys()))
        form.addRow("Language:", self.combo_language)
        self.spin_dpi = QSpinBox()
        self.spin_dpi.setRange(72, 600)
        self.spin_dpi.setSingleStep(50)
        self.spin_dpi.setValue(self.ctx.config.settings.ocr_default_dpi)
        form.addRow("Render DPI:", self.spin_dpi)
        self.chk_skip_text = QCheckBox("Skip pages that already have extractable text")
        self.chk_skip_text.setChecked(self.ctx.config.settings.ocr_skip_pages_with_text)
        form.addRow(self.chk_skip_text)
        root.addWidget(options_group)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output folder:"))
        self.edit_output_folder = QLineEdit(self.ctx.config.settings.default_output_folder)
        output_row.addWidget(self.edit_output_folder, 1)
        self.btn_browse_output = QPushButton("Browse...")
        self.btn_browse_output.setObjectName("SecondaryButton")
        output_row.addWidget(self.btn_browse_output)
        root.addLayout(output_row)

        self.btn_run = QPushButton("MAKE SEARCHABLE")
        self.btn_run.setMinimumHeight(40)
        root.addWidget(self.btn_run)

        self.btn_add_files.clicked.connect(self.add_files)
        self.btn_add_folder.clicked.connect(self.add_folder)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_browse_output.clicked.connect(self._browse_output)
        self.btn_run.clicked.connect(self.run_ocr)

    def add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select PDF Files", self.ctx.config.settings.last_used_folder, "PDF Files (*.pdf)")
        self._add_paths(paths)

    def add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", self.ctx.config.settings.last_used_folder)
        if folder:
            self._add_paths([str(p) for p in find_pdfs_in_folder(folder)])

    def _add_paths(self, paths: list[str]) -> None:
        existing = {j.source_path for j in self.jobs}
        for path in paths:
            if path in existing:
                continue
            ok, reason = validate_pdf_integrity(path)
            if not ok:
                show_error(self, "Cannot Add File", f"'{Path(path).name}': {reason}")
                continue
            self.jobs.append(SigningJob(source_path=path))
        self._refresh_table()

    def remove_selected(self) -> None:
        rows = {i.row() for i in self.table.selectedIndexes()}
        self.jobs = [j for i, j in enumerate(self.jobs) if i not in rows]
        self._refresh_table()

    def select_all(self) -> None:
        self.table.selectAll()

    def clear_all(self) -> None:
        self.jobs.clear()
        self._refresh_table()

    def _refresh_table(self) -> None:
        self.table.setRowCount(len(self.jobs))
        for row, job in enumerate(self.jobs):
            self.table.setItem(row, 0, QTableWidgetItem(job.file_name))
            self.table.setItem(row, 1, QTableWidgetItem(job.status.value))

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.edit_output_folder.text())
        if folder:
            self.edit_output_folder.setText(folder)

    def process(self) -> None:
        self.run_ocr()

    def run_ocr(self) -> None:
        if not self.jobs:
            QMessageBox.information(self, "No Files", "Add at least one PDF to OCR.")
            return
        if not is_tesseract_available(self.ctx.config.settings.tesseract_path):
            show_error(self, "Tesseract Not Found", "Install Tesseract OCR (see Settings -> OCR) before using this tab.")
            return

        language_code = SUPPORTED_LANGUAGES[self.combo_language.currentText()]
        dpi = self.spin_dpi.value()
        skip_existing = self.chk_skip_text.isChecked()
        output_folder = self.edit_output_folder.text().strip() or None
        tesseract_path = self.ctx.config.settings.tesseract_path

        summary = [
            f"Documents selected: {len(self.jobs)}",
            f"Language: {self.combo_language.currentText()}",
            f"Render DPI: {dpi}",
            f"Output folder: {output_folder or '(same as source)'}",
        ]
        dlg = BatchConfirmationDialog("Make PDFs Searchable (OCR)", summary, f"MAKE {len(self.jobs)} DOCUMENTS SEARCHABLE", self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        database = self.ctx.database
        operator = self.ctx.operator
        register_enabled = self.ctx.config.settings.enable_activity_register

        def process_fn(job: SigningJob) -> None:
            final_output = compute_output_path(
                job.source_path, output_folder, NamingMode.ADD_SUFFIX, "_Searchable", "", CollisionPolicy.RENAME
            )
            if final_output is None:
                from models.enums import JobStatus

                job.status = JobStatus.SKIPPED
                job.error_message = "Output file already exists (skipped)."
                return

            result = make_searchable_pdf(
                job.source_path, final_output, language=language_code, dpi=dpi,
                skip_pages_with_text=skip_existing, tesseract_path=tesseract_path,
            )
            job.output_path = str(final_output)
            job.selected_pages = f"{len(result.pages_ocred)} page(s) OCR'd, {len(result.pages_already_had_text)} already searchable"
            job.total_pages = len(result.pages_ocred) + len(result.pages_already_had_text)

            log_operation(logger, operation="ocr", input_file=job.source_path, output_file=str(final_output), result="success")
            if register_enabled:
                from datetime import datetime

                database.add_audit_entry(
                    AuditEntry(
                        timestamp=datetime.now().isoformat(), operator=operator, operation="OCR / Make Searchable",
                        source_document=job.source_path, output_document=str(final_output),
                        pages_processed=job.selected_pages, template_used="", result="Success",
                    )
                )

        self._progress_dialog = ProgressDialog("Running OCR...", self)
        self._worker = BatchWorker(list(self.jobs), process_fn, output_folder or "")
        self._worker.progress_changed.connect(lambda c, t, name: self._progress_dialog and self._progress_dialog.update_progress(c, t, name))
        self._worker.job_finished.connect(self._on_job_finished)
        self._worker.batch_finished.connect(self._on_batch_finished)
        self._worker.fatal_error.connect(lambda msg: show_error(self, "OCR Error", msg))
        self._progress_dialog.btn_cancel.clicked.connect(self._worker.cancel)
        self._worker.start()
        self._progress_dialog.exec()

    def _on_job_finished(self, job: SigningJob) -> None:
        self._refresh_table()
        if self._progress_dialog:
            self._progress_dialog.note_job_result(job.status)

    def _on_batch_finished(self, result: BatchResult) -> None:
        if self._progress_dialog:
            self._progress_dialog.accept()
            self._progress_dialog = None
        ReportDialog(result, "OCR", self).exec()
