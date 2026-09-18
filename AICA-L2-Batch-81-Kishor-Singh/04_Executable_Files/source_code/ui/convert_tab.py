"""Word -> PDF tab, including the one-click "Convert & Sign" workflow."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.page_selection import describe_expression
from core.signature_engine import SignatureApplication
from core.word_converter import WordToPdfConverter, is_libreoffice_available, is_word_com_available
from models.enums import CollisionPolicy, JobStatus, NamingMode, WordEngine
from models.job import BatchResult, SigningJob
from ui.app_context import AppContext
from ui.widgets.dialogs import BatchConfirmationDialog, ProgressDialog, ReportDialog, show_error
from ui.widgets.signature_layer_widget import SignatureLayerWidget
from utils.database import AuditEntry
from utils.file_utils import TempWorkspace, atomic_replace, compute_output_path, find_word_files_in_folder
from utils.logging_utils import get_logger, log_operation
from workers.batch_worker import BatchWorker, build_retry_worker

logger = get_logger("convert_tab")


class ConvertTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.jobs: list[SigningJob] = []
        self._worker: BatchWorker | None = None
        self._progress_dialog: ProgressDialog | None = None
        self._workspace: TempWorkspace | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.btn_add_files = QPushButton("Add Word Files")
        self.btn_add_folder = QPushButton("Add Folder")
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_remove.setObjectName("SecondaryButton")
        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.setObjectName("DangerButton")
        for b in (self.btn_add_files, self.btn_add_folder, self.btn_remove, self.btn_clear):
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["File Name", "Folder", "Details", "Status"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 1)

        engine_group = QGroupBox("Conversion Engine")
        engine_form = QFormLayout(engine_group)
        self.combo_engine = QComboBox()
        self.combo_engine.addItems([e.value for e in WordEngine])
        self.combo_engine.setCurrentText(self.ctx.config.settings.word_conversion_engine)
        engine_form.addRow("Engine:", self.combo_engine)
        status = []
        status.append(f"Microsoft Word detected: {'Yes' if is_word_com_available() else 'No'}")
        status.append(f"LibreOffice detected: {'Yes' if is_libreoffice_available(self.ctx.config.settings.libreoffice_path) else 'No'}")
        engine_form.addRow(QLabel("  |  ".join(status)))
        root.addWidget(engine_group)

        output_group = QGroupBox("Output Options")
        output_form = QFormLayout(output_group)
        folder_row = QHBoxLayout()
        self.edit_output_folder = QLineEdit(self.ctx.config.settings.default_output_folder)
        self.btn_browse_output = QPushButton("Browse...")
        self.btn_browse_output.setObjectName("SecondaryButton")
        folder_row.addWidget(self.edit_output_folder, 1)
        folder_row.addWidget(self.btn_browse_output)
        output_form.addRow("Output folder:", folder_row)
        self.combo_collision = QComboBox()
        self.combo_collision.addItems([c.value for c in CollisionPolicy])
        self.combo_collision.setCurrentText(self.ctx.config.settings.collision_policy)
        output_form.addRow("If file already exists:", self.combo_collision)
        root.addWidget(output_group)

        sign_group = QGroupBox("Optional: Apply Signature After Conversion")
        sign_layout = QVBoxLayout(sign_group)
        self.chk_apply_signature_label = QLabel(
            "Configure a signature layer below to enable 'Convert & Sign All'. Leave the image blank to skip signing."
        )
        sign_layout.addWidget(self.chk_apply_signature_label)
        self.signature_layer = SignatureLayerWidget(removable=False, database=self.ctx.database)
        sign_layout.addWidget(self.signature_layer)
        root.addWidget(sign_group)

        button_row = QHBoxLayout()
        self.btn_convert_only = QPushButton("CONVERT ALL TO PDF")
        self.btn_convert_only.setMinimumHeight(40)
        self.btn_convert_and_sign = QPushButton("CONVERT & SIGN ALL")
        self.btn_convert_and_sign.setMinimumHeight(40)
        button_row.addWidget(self.btn_convert_only)
        button_row.addWidget(self.btn_convert_and_sign)
        root.addLayout(button_row)

        self.btn_add_files.clicked.connect(self.add_files)
        self.btn_add_folder.clicked.connect(self.add_folder)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_browse_output.clicked.connect(self._browse_output_folder)
        self.btn_convert_only.clicked.connect(lambda: self._start(sign_after=False))
        self.btn_convert_and_sign.clicked.connect(lambda: self._start(sign_after=True))

    # ------------------------------------------------------------- file mgmt
    def add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Word Documents", self.ctx.config.settings.last_used_folder, "Word Documents (*.docx *.doc)"
        )
        self._add_paths(paths)

    def add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", self.ctx.config.settings.last_used_folder)
        if folder:
            self._add_paths([str(p) for p in find_word_files_in_folder(folder)])

    def _add_paths(self, paths: list[str]) -> None:
        existing = {j.source_path for j in self.jobs}
        for path in paths:
            if path in existing:
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
            self.table.setItem(row, 1, QTableWidgetItem(job.folder))
            self.table.setItem(row, 2, QTableWidgetItem(self._describe(job.source_path)))
            self.table.setItem(row, 3, QTableWidgetItem(job.status.value))

    @staticmethod
    def _describe(path: str) -> str:
        from core.word_converter import inspect_word_document

        info = inspect_word_document(path)
        if not info.supported:
            return "-"
        return f"{info.paragraph_count} paragraphs, {info.table_count} tables, ~{info.approx_word_count} words"

    def _browse_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.edit_output_folder.text())
        if folder:
            self.edit_output_folder.setText(folder)

    def process(self) -> None:
        self._start(sign_after=False)

    # ------------------------------------------------------------- pipeline
    def _start(self, sign_after: bool) -> None:
        if not self.jobs:
            QMessageBox.information(self, "No Files", "Add at least one Word document first.")
            return
        image_path = self.signature_layer.edit_image_path.text().strip()
        if sign_after and not (image_path and Path(image_path).exists()):
            show_error(self, "Missing Signature", "Configure a signature image before using Convert & Sign.")
            return

        summary = [
            f"Documents selected: {len(self.jobs)}",
            f"Conversion engine: {self.combo_engine.currentText()}",
            f"Output folder: {self.edit_output_folder.text().strip() or '(same as source)'}",
        ]
        if sign_after:
            template = self.signature_layer.get_template()
            summary.append(f"Signing rule: {describe_expression(template.page_rule_expression)}")
            summary.append(f"Position: {template.position_preset.value}")
        action = "CONVERT & SIGN ALL" if sign_after else "CONVERT ALL"
        dlg = BatchConfirmationDialog(action, summary, f"{action} {len(self.jobs)} DOCUMENTS", self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        output_folder = self.edit_output_folder.text().strip() or None
        collision_policy = CollisionPolicy(self.combo_collision.currentText())
        engine = WordEngine(self.combo_engine.currentText())
        template = self.signature_layer.get_template() if sign_after else None
        self._workspace = TempWorkspace(self.ctx.config.get_temp_folder())
        database = self.ctx.database
        operator = self.ctx.operator
        register_enabled = self.ctx.config.settings.enable_activity_register
        workspace = self._workspace

        def process_fn(job: SigningJob) -> None:
            converter = WordToPdfConverter(engine, self.ctx.config.settings.libreoffice_path)
            final_output = compute_output_path(
                Path(job.source_path).with_suffix(".pdf"), output_folder, NamingMode.KEEP_ORIGINAL, "", "", collision_policy
            )
            if final_output is None:
                job.status = JobStatus.SKIPPED
                job.error_message = "Output file already exists (skipped)."
                return

            converted_temp = workspace.new_file(".pdf")
            converter.convert(job.source_path, converted_temp)

            if template is not None:
                from core.signature_engine import apply_signatures_to_pdf

                signed_temp = workspace.new_file(".pdf")
                outcome = apply_signatures_to_pdf(converted_temp, signed_temp, [SignatureApplication(template=template)])
                atomic_replace(signed_temp, final_output)
                job.total_pages = outcome.total_pages
                job.selected_pages = ", ".join(str(p) for p in outcome.signed_pages)
            else:
                atomic_replace(converted_temp, final_output)
                from core.pdf_engine import get_page_count

                job.total_pages = get_page_count(final_output)

            job.output_path = str(final_output)
            log_operation(
                logger,
                operation="convert_and_sign" if template else "convert",
                input_file=job.source_path,
                output_file=str(final_output),
                pages=job.total_pages,
                result="success",
            )
            if register_enabled:
                from datetime import datetime

                database.add_audit_entry(
                    AuditEntry(
                        timestamp=datetime.now().isoformat(),
                        operator=operator,
                        operation="Convert & Sign" if template else "Word to PDF",
                        source_document=job.source_path,
                        output_document=str(final_output),
                        pages_processed=job.selected_pages,
                        template_used=template.name if template else "",
                        result="Success",
                    )
                )
                database.add_recent_job(job.job_id, "Word to PDF", job.file_name, job.output_file_name, "Success")

        self._progress_dialog = ProgressDialog("Converting Documents...", self)
        self._worker = BatchWorker(list(self.jobs), process_fn, output_folder or "")
        self._wire_worker(self._worker)
        self._progress_dialog.btn_cancel.clicked.connect(self._worker.cancel)
        self._worker.start()
        self._progress_dialog.exec()

    def _wire_worker(self, worker: BatchWorker) -> None:
        worker.progress_changed.connect(lambda c, t, name: self._progress_dialog and self._progress_dialog.update_progress(c, t, name))
        worker.job_finished.connect(self._on_job_finished)
        worker.batch_finished.connect(self._on_batch_finished)
        worker.fatal_error.connect(lambda msg: show_error(self, "Processing Error", msg))

    def _on_job_finished(self, job: SigningJob) -> None:
        self._refresh_table()
        if self._progress_dialog:
            self._progress_dialog.note_job_result(job.status)

    def _on_batch_finished(self, result: BatchResult) -> None:
        if self._progress_dialog:
            self._progress_dialog.accept()
            self._progress_dialog = None
        if self._workspace:
            self._workspace.cleanup()
            self._workspace = None
        report = ReportDialog(result, "Word to PDF Conversion", self)
        report.btn_retry_failed.clicked.connect(lambda: self._retry_failed(result))
        report.exec()
        if self.ctx.config.settings.open_output_folder_after_completion and result.output_folder:
            self._open_folder(result.output_folder)

    def _retry_failed(self, previous_result: BatchResult) -> None:
        if self._worker is None:
            return
        retry_worker = build_retry_worker(previous_result, self._worker.process_fn)
        self._progress_dialog = ProgressDialog("Retrying Failed Documents...", self)
        self._wire_worker(retry_worker)
        self._progress_dialog.btn_cancel.clicked.connect(retry_worker.cancel)
        self._worker = retry_worker
        retry_worker.start()
        self._progress_dialog.exec()

    @staticmethod
    def _open_folder(folder: str) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # noqa: S606
            else:
                subprocess.Popen(["xdg-open", folder])
        except OSError:
            pass
