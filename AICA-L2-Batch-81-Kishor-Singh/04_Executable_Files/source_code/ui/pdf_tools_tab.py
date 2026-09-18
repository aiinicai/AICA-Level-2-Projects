"""PDF Power-Tools tab: Compress, Scan Enhance, Forms, Bates Numbering, Repair."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
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
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.compression_engine import CompressionPreset, compress_pdf
from core.form_engine import export_form_data, fill_form, flatten_form, list_form_fields
from core.pdf_engine import repair_pdf, validate_pdf_integrity
from core.scan_enhancement_engine import EnhancementOptions, enhance_pdf
from core.watermark_engine import BatesNumberingOptions, add_bates_numbering
from models.enums import PositionPreset
from models.job import BatchResult, SigningJob
from ui.app_context import AppContext
from ui.widgets.dialogs import BatchConfirmationDialog, ProgressDialog, ReportDialog, show_error
from utils.database import AuditEntry
from utils.file_utils import find_pdfs_in_folder, human_size
from utils.logging_utils import get_logger, log_operation
from utils.validation import ValidationError
from workers.batch_worker import BatchWorker

logger = get_logger("pdf_tools_tab")


def _pdf_batch_toolbar(add_files, add_folder, remove, clear):
    row = QHBoxLayout()
    btn_add_files = QPushButton("Add Files")
    btn_add_folder = QPushButton("Add Folder")
    btn_remove = QPushButton("Remove Selected")
    btn_remove.setObjectName("SecondaryButton")
    btn_clear = QPushButton("Clear All")
    btn_clear.setObjectName("DangerButton")
    btn_add_files.clicked.connect(add_files)
    btn_add_folder.clicked.connect(add_folder)
    btn_remove.clicked.connect(remove)
    btn_clear.clicked.connect(clear)
    for b in (btn_add_files, btn_add_folder, btn_remove, btn_clear):
        row.addWidget(b)
    row.addStretch(1)
    return row


class PDFToolsTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        self.sub_tabs = QTabWidget()
        root.addWidget(self.sub_tabs)
        self.sub_tabs.addTab(self._build_compress_tab(), "Compress")
        self.sub_tabs.addTab(self._build_scan_enhance_tab(), "Scan Enhance")
        self.sub_tabs.addTab(self._build_forms_tab(), "Forms")
        self.sub_tabs.addTab(self._build_bates_tab(), "Bates Numbering")
        self.sub_tabs.addTab(self._build_repair_tab(), "Repair PDF")

    def process(self) -> None:
        current = self.sub_tabs.currentWidget()
        method = getattr(current, "run", None)
        if callable(method):
            method()

    # ============================================================ Compress
    def _build_compress_tab(self) -> QWidget:
        widget = QWidget()
        widget.jobs = []
        layout = QVBoxLayout(widget)
        layout.addLayout(_pdf_batch_toolbar(
            lambda: self._add_files(widget), lambda: self._add_folder(widget),
            lambda: self._remove_selected(widget), lambda: self._clear_all(widget),
        ))
        widget.table = QTableWidget(0, 2)
        widget.table.setHorizontalHeaderLabels(["File Name", "Status"])
        widget.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(widget.table, 1)

        options_group = QGroupBox("Compression Preset")
        form = QFormLayout(options_group)
        widget.combo_preset = QComboBox()
        widget.combo_preset.addItems([p.value for p in CompressionPreset])
        widget.combo_preset.setCurrentText(CompressionPreset.STANDARD.value)
        form.addRow("Preset:", widget.combo_preset)
        layout.addWidget(options_group)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output folder:"))
        widget.edit_output = QLineEdit(self.ctx.config.settings.default_output_folder)
        output_row.addWidget(widget.edit_output, 1)
        btn_browse = QPushButton("Browse...")
        btn_browse.setObjectName("SecondaryButton")
        btn_browse.clicked.connect(lambda: self._browse_output(widget))
        output_row.addWidget(btn_browse)
        layout.addLayout(output_row)

        widget.btn_run = QPushButton("COMPRESS")
        widget.btn_run.setMinimumHeight(38)
        layout.addWidget(widget.btn_run)
        widget.run = lambda: self._run_compress(widget)
        widget.btn_run.clicked.connect(widget.run)
        widget.process = widget.run
        return widget

    def _run_compress(self, widget) -> None:
        if not widget.jobs:
            QMessageBox.information(self, "No Files", "Add at least one PDF to compress.")
            return
        preset = CompressionPreset(widget.combo_preset.currentText())
        output_folder = widget.edit_output.text().strip() or None
        summary = [f"Documents: {len(widget.jobs)}", f"Preset: {preset.value}", f"Output folder: {output_folder or '(same as source)'}"]
        dlg = BatchConfirmationDialog("Compress PDFs", summary, f"COMPRESS {len(widget.jobs)} DOCUMENTS", self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        database, operator, register_enabled = self.ctx.database, self.ctx.operator, self.ctx.config.settings.enable_activity_register

        def process_fn(job: SigningJob) -> None:
            from utils.file_utils import compute_output_path
            from models.enums import NamingMode, CollisionPolicy

            final_output = compute_output_path(job.source_path, output_folder, NamingMode.ADD_SUFFIX, "_Compressed", "", CollisionPolicy.RENAME)
            if final_output is None:
                from models.enums import JobStatus
                job.status = JobStatus.SKIPPED
                job.error_message = "Output file already exists (skipped)."
                return
            result = compress_pdf(job.source_path, final_output, preset)
            job.output_path = str(final_output)
            job.selected_pages = f"{human_size(result.original_size_bytes)} -> {human_size(result.compressed_size_bytes)} ({result.reduction_percent:.0f}% smaller)"
            log_operation(logger, operation="compress", input_file=job.source_path, output_file=str(final_output), result="success")
            if register_enabled:
                from datetime import datetime
                database.add_audit_entry(AuditEntry(
                    timestamp=datetime.now().isoformat(), operator=operator, operation="Compress PDF",
                    source_document=job.source_path, output_document=str(final_output),
                    pages_processed=job.selected_pages, template_used="", result="Success",
                ))

        self._run_batch(widget, process_fn, output_folder, "Compressing PDFs...", "Compression")

    # ======================================================= Scan Enhance
    def _build_scan_enhance_tab(self) -> QWidget:
        widget = QWidget()
        widget.jobs = []
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(
            "Best for scanned pages (rasterizes and reprocesses each page) -- do not run this on "
            "digitally-created PDFs with real text, since it will convert their text to an image."
        ))
        layout.addLayout(_pdf_batch_toolbar(
            lambda: self._add_files(widget), lambda: self._add_folder(widget),
            lambda: self._remove_selected(widget), lambda: self._clear_all(widget),
        ))
        widget.table = QTableWidget(0, 2)
        widget.table.setHorizontalHeaderLabels(["File Name", "Status"])
        widget.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(widget.table, 1)

        options_group = QGroupBox("Enhancement Options")
        form = QFormLayout(options_group)
        widget.chk_orientation = QCheckBox("Fix orientation (needs Tesseract)")
        widget.chk_orientation.setChecked(True)
        widget.chk_deskew = QCheckBox("Deskew")
        widget.chk_deskew.setChecked(True)
        widget.chk_denoise = QCheckBox("Denoise")
        widget.chk_denoise.setChecked(True)
        widget.chk_trim = QCheckBox("Trim borders")
        widget.chk_trim.setChecked(True)
        for chk in (widget.chk_orientation, widget.chk_deskew, widget.chk_denoise, widget.chk_trim):
            form.addRow(chk)
        layout.addWidget(options_group)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output folder:"))
        widget.edit_output = QLineEdit(self.ctx.config.settings.default_output_folder)
        output_row.addWidget(widget.edit_output, 1)
        btn_browse = QPushButton("Browse...")
        btn_browse.setObjectName("SecondaryButton")
        btn_browse.clicked.connect(lambda: self._browse_output(widget))
        output_row.addWidget(btn_browse)
        layout.addLayout(output_row)

        widget.btn_run = QPushButton("ENHANCE SCANS")
        widget.btn_run.setMinimumHeight(38)
        layout.addWidget(widget.btn_run)
        widget.run = lambda: self._run_enhance(widget)
        widget.btn_run.clicked.connect(widget.run)
        widget.process = widget.run
        return widget

    def _run_enhance(self, widget) -> None:
        if not widget.jobs:
            QMessageBox.information(self, "No Files", "Add at least one scanned PDF to enhance.")
            return
        options = EnhancementOptions(
            fix_orientation=widget.chk_orientation.isChecked(), deskew=widget.chk_deskew.isChecked(),
            denoise=widget.chk_denoise.isChecked(), trim_borders=widget.chk_trim.isChecked(),
        )
        output_folder = widget.edit_output.text().strip() or None
        summary = [f"Documents: {len(widget.jobs)}", f"Output folder: {output_folder or '(same as source)'}"]
        dlg = BatchConfirmationDialog("Enhance Scanned PDFs", summary, f"ENHANCE {len(widget.jobs)} DOCUMENTS", self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        tesseract_path = self.ctx.config.settings.tesseract_path
        database, operator, register_enabled = self.ctx.database, self.ctx.operator, self.ctx.config.settings.enable_activity_register

        def process_fn(job: SigningJob) -> None:
            from utils.file_utils import compute_output_path
            from models.enums import NamingMode, CollisionPolicy

            final_output = compute_output_path(job.source_path, output_folder, NamingMode.ADD_SUFFIX, "_Enhanced", "", CollisionPolicy.RENAME)
            if final_output is None:
                from models.enums import JobStatus
                job.status = JobStatus.SKIPPED
                job.error_message = "Output file already exists (skipped)."
                return
            reports = enhance_pdf(job.source_path, final_output, options, tesseract_path=tesseract_path)
            job.output_path = str(final_output)
            job.total_pages = len(reports)
            job.selected_pages = f"{sum(1 for r in reports if r.borders_trimmed)} trimmed, {sum(1 for r in reports if abs(r.deskew_angle_applied) > 0.1)} deskewed"
            log_operation(logger, operation="scan_enhance", input_file=job.source_path, output_file=str(final_output), result="success")
            if register_enabled:
                from datetime import datetime
                database.add_audit_entry(AuditEntry(
                    timestamp=datetime.now().isoformat(), operator=operator, operation="Scan Enhance",
                    source_document=job.source_path, output_document=str(final_output),
                    pages_processed=job.selected_pages, template_used="", result="Success",
                ))

        self._run_batch(widget, process_fn, output_folder, "Enhancing Scans...", "Scan Enhancement")

    # ================================================================ Forms
    def _build_forms_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        file_row = QHBoxLayout()
        widget.edit_path = QLineEdit()
        widget.edit_path.setPlaceholderText("Open a fillable PDF...")
        btn_open = QPushButton("Open PDF")
        file_row.addWidget(widget.edit_path, 1)
        file_row.addWidget(btn_open)
        layout.addLayout(file_row)

        widget.table = QTableWidget(0, 3)
        widget.table.setHorizontalHeaderLabels(["Field Name", "Type", "Value"])
        widget.table.horizontalHeader().setStretchLastSection(True)
        widget.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        layout.addWidget(widget.table, 1)

        button_row = QHBoxLayout()
        btn_fill = QPushButton("Save Filled PDF")
        btn_flatten = QPushButton("Save Flattened PDF")
        btn_flatten.setObjectName("SecondaryButton")
        btn_export = QPushButton("Export Field Data (JSON)")
        btn_export.setObjectName("SecondaryButton")
        button_row.addWidget(btn_fill)
        button_row.addWidget(btn_flatten)
        button_row.addWidget(btn_export)
        layout.addLayout(button_row)

        btn_open.clicked.connect(lambda: self._forms_open(widget))
        btn_fill.clicked.connect(lambda: self._forms_save_filled(widget))
        btn_flatten.clicked.connect(lambda: self._forms_save_flattened(widget))
        btn_export.clicked.connect(lambda: self._forms_export(widget))
        widget.run = lambda: self._forms_save_filled(widget)
        widget.process = widget.run
        return widget

    def _forms_open(self, widget) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Fillable PDF", "", "PDF Files (*.pdf)")
        if not path:
            return
        try:
            fields = list_form_fields(path)
        except ValidationError as exc:
            show_error(self, "Cannot Read Form", str(exc))
            return
        widget.edit_path.setText(path)
        widget.table.setRowCount(len(fields))
        for row, f in enumerate(fields):
            name_item = QTableWidgetItem(f.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            widget.table.setItem(row, 0, name_item)
            type_item = QTableWidgetItem(f.field_type)
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            widget.table.setItem(row, 1, type_item)
            widget.table.setItem(row, 2, QTableWidgetItem(f.current_value))
        if not fields:
            QMessageBox.information(self, "No Fields Found", "This PDF has no fillable AcroForm fields.")

    def _collect_form_values(self, widget) -> dict[str, str]:
        values = {}
        for row in range(widget.table.rowCount()):
            name = widget.table.item(row, 0).text()
            value = widget.table.item(row, 2).text() if widget.table.item(row, 2) else ""
            values[name] = value
        return values

    def _forms_save_filled(self, widget) -> None:
        if not widget.edit_path.text():
            QMessageBox.information(self, "No Form Open", "Open a fillable PDF first.")
            return
        out, _ = QFileDialog.getSaveFileName(self, "Save Filled PDF As", "", "PDF Files (*.pdf)")
        if not out:
            return
        try:
            updated = fill_form(widget.edit_path.text(), out, self._collect_form_values(widget))
        except ValidationError as exc:
            show_error(self, "Fill Failed", str(exc))
            return
        QMessageBox.information(self, "Saved", f"{updated} field(s) filled. Saved to:\n{out}")

    def _forms_save_flattened(self, widget) -> None:
        if not widget.edit_path.text():
            QMessageBox.information(self, "No Form Open", "Open a fillable PDF first.")
            return
        temp_filled = Path(widget.edit_path.text()).with_name("_temp_filled_for_flatten.pdf")
        out, _ = QFileDialog.getSaveFileName(self, "Save Flattened PDF As", "", "PDF Files (*.pdf)")
        if not out:
            return
        try:
            fill_form(widget.edit_path.text(), temp_filled, self._collect_form_values(widget))
            count = flatten_form(temp_filled, out)
        except ValidationError as exc:
            show_error(self, "Flatten Failed", str(exc))
            return
        finally:
            temp_filled.unlink(missing_ok=True)
        QMessageBox.information(self, "Saved", f"{count} field(s) flattened into static content. Saved to:\n{out}")

    def _forms_export(self, widget) -> None:
        if not widget.edit_path.text():
            QMessageBox.information(self, "No Form Open", "Open a fillable PDF first.")
            return
        out, _ = QFileDialog.getSaveFileName(self, "Export Field Data", "form_data.json", "JSON Files (*.json)")
        if not out:
            return
        import json

        data = export_form_data(widget.edit_path.text())
        Path(out).write_text(json.dumps(data, indent=2), encoding="utf-8")
        QMessageBox.information(self, "Exported", f"Saved to:\n{out}")

    # ======================================================= Bates Numbering
    def _build_bates_tab(self) -> QWidget:
        widget = QWidget()
        widget.jobs = []
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Applies continuous numbering (e.g. ABC-000001) across all selected files, in the order shown."))
        layout.addLayout(_pdf_batch_toolbar(
            lambda: self._add_files(widget), lambda: self._add_folder(widget),
            lambda: self._remove_selected(widget), lambda: self._clear_all(widget),
        ))
        widget.table = QTableWidget(0, 2)
        widget.table.setHorizontalHeaderLabels(["File Name", "Status"])
        widget.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(widget.table, 1)

        options_group = QGroupBox("Numbering Options")
        form = QFormLayout(options_group)
        widget.edit_prefix = QLineEdit()
        widget.edit_prefix.setPlaceholderText("e.g. KSC-")
        form.addRow("Prefix:", widget.edit_prefix)
        widget.spin_start = QSpinBox()
        widget.spin_start.setRange(1, 999999)
        widget.spin_start.setValue(1)
        form.addRow("Start number:", widget.spin_start)
        widget.spin_digits = QSpinBox()
        widget.spin_digits.setRange(1, 10)
        widget.spin_digits.setValue(6)
        form.addRow("Digit count:", widget.spin_digits)
        widget.combo_position = QComboBox()
        widget.combo_position.addItems([p.value for p in PositionPreset if p != PositionPreset.CUSTOM])
        widget.combo_position.setCurrentText(PositionPreset.BOTTOM_RIGHT.value)
        form.addRow("Position:", widget.combo_position)
        layout.addWidget(options_group)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output folder:"))
        widget.edit_output = QLineEdit(self.ctx.config.settings.default_output_folder)
        output_row.addWidget(widget.edit_output, 1)
        btn_browse = QPushButton("Browse...")
        btn_browse.setObjectName("SecondaryButton")
        btn_browse.clicked.connect(lambda: self._browse_output(widget))
        output_row.addWidget(btn_browse)
        layout.addLayout(output_row)

        widget.btn_run = QPushButton("APPLY BATES NUMBERING")
        widget.btn_run.setMinimumHeight(38)
        layout.addWidget(widget.btn_run)
        widget.run = lambda: self._run_bates(widget)
        widget.btn_run.clicked.connect(widget.run)
        widget.process = widget.run
        return widget

    def _run_bates(self, widget) -> None:
        if not widget.jobs:
            QMessageBox.information(self, "No Files", "Add at least one PDF.")
            return
        output_folder = widget.edit_output.text().strip() or self.ctx.config.settings.default_output_folder
        prefix = widget.edit_prefix.text()
        digits = widget.spin_digits.value()
        position = PositionPreset(widget.combo_position.currentText())
        summary = [f"Documents: {len(widget.jobs)}", f"Prefix: {prefix or '(none)'}", f"Starting at: {str(widget.spin_start.value()).zfill(digits)}"]
        dlg = BatchConfirmationDialog("Apply Bates Numbering", summary, f"NUMBER {len(widget.jobs)} DOCUMENTS", self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        # Sequential and stateful (each file continues where the last left off) --
        # run directly rather than through the generic parallel-friendly BatchWorker
        # process_fn pattern, since ordering and shared counter state matter here.
        current = widget.spin_start.value()
        results = []
        from utils.file_utils import compute_output_path
        from models.enums import NamingMode, CollisionPolicy, JobStatus

        progress = ProgressDialog("Applying Bates Numbering...", self)
        progress.show()
        for i, job in enumerate(widget.jobs):
            progress.update_progress(i, len(widget.jobs), job.file_name)
            QApplication.processEvents()
            try:
                final_output = compute_output_path(job.source_path, output_folder, NamingMode.ADD_SUFFIX, "_Bates", "", CollisionPolicy.RENAME)
                if final_output is None:
                    job.status = JobStatus.SKIPPED
                    job.error_message = "Output file already exists (skipped)."
                else:
                    result = add_bates_numbering(job.source_path, final_output, BatesNumberingOptions(
                        prefix=prefix, digit_count=digits, start_number=current, position=position,
                    ))
                    current = result.next_start_number
                    job.output_path = str(final_output)
                    job.selected_pages = f"{prefix}{str(result.first_number).zfill(digits)} - {prefix}{str(result.last_number).zfill(digits)}"
                    job.status = JobStatus.SUCCESS
            except ValidationError as exc:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)
            results.append(job)
        progress.update_progress(len(widget.jobs), len(widget.jobs), "")
        progress.accept()

        batch_result = BatchResult(jobs=results, output_folder=output_folder)
        ReportDialog(batch_result, "Bates Numbering", self).exec()
        self._refresh_table(widget)

    # ================================================================ Repair
    def _build_repair_tab(self) -> QWidget:
        widget = QWidget()
        widget.jobs = []
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Rewrites a PDF's internal structure via a repair pass -- useful for files that "
                                 "behave oddly in some viewers even though they appear to open normally."))
        layout.addLayout(_pdf_batch_toolbar(
            lambda: self._add_files(widget), lambda: self._add_folder(widget),
            lambda: self._remove_selected(widget), lambda: self._clear_all(widget),
        ))
        widget.table = QTableWidget(0, 2)
        widget.table.setHorizontalHeaderLabels(["File Name", "Status"])
        widget.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(widget.table, 1)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output folder:"))
        widget.edit_output = QLineEdit(self.ctx.config.settings.default_output_folder)
        output_row.addWidget(widget.edit_output, 1)
        btn_browse = QPushButton("Browse...")
        btn_browse.setObjectName("SecondaryButton")
        btn_browse.clicked.connect(lambda: self._browse_output(widget))
        output_row.addWidget(btn_browse)
        layout.addLayout(output_row)

        widget.btn_run = QPushButton("REPAIR")
        widget.btn_run.setMinimumHeight(38)
        layout.addWidget(widget.btn_run)
        widget.run = lambda: self._run_repair(widget)
        widget.btn_run.clicked.connect(widget.run)
        widget.process = widget.run
        return widget

    def _run_repair(self, widget) -> None:
        if not widget.jobs:
            QMessageBox.information(self, "No Files", "Add at least one PDF to repair.")
            return
        output_folder = widget.edit_output.text().strip() or None
        summary = [f"Documents: {len(widget.jobs)}", f"Output folder: {output_folder or '(same as source)'}"]
        dlg = BatchConfirmationDialog("Repair PDFs", summary, f"REPAIR {len(widget.jobs)} DOCUMENTS", self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        database, operator, register_enabled = self.ctx.database, self.ctx.operator, self.ctx.config.settings.enable_activity_register

        def process_fn(job: SigningJob) -> None:
            from utils.file_utils import compute_output_path
            from models.enums import NamingMode, CollisionPolicy

            final_output = compute_output_path(job.source_path, output_folder, NamingMode.ADD_SUFFIX, "_Repaired", "", CollisionPolicy.RENAME)
            if final_output is None:
                from models.enums import JobStatus
                job.status = JobStatus.SKIPPED
                job.error_message = "Output file already exists (skipped)."
                return
            result = repair_pdf(job.source_path, final_output)
            job.output_path = str(final_output)
            job.total_pages = result.page_count
            job.selected_pages = "Repaired" if result.repaired else "No repair needed"
            log_operation(logger, operation="repair", input_file=job.source_path, output_file=str(final_output), result="success")
            if register_enabled:
                from datetime import datetime
                database.add_audit_entry(AuditEntry(
                    timestamp=datetime.now().isoformat(), operator=operator, operation="Repair PDF",
                    source_document=job.source_path, output_document=str(final_output),
                    pages_processed=job.selected_pages, template_used="", result="Success",
                ))

        self._run_batch(widget, process_fn, output_folder, "Repairing PDFs...", "Repair")

    # ============================================================ shared bits
    def _add_files(self, widget) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select PDF Files", self.ctx.config.settings.last_used_folder, "PDF Files (*.pdf)")
        self._add_paths(widget, paths)

    def _add_folder(self, widget) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", self.ctx.config.settings.last_used_folder)
        if folder:
            self._add_paths(widget, [str(p) for p in find_pdfs_in_folder(folder)])

    def _add_paths(self, widget, paths: list[str]) -> None:
        existing = {j.source_path for j in widget.jobs}
        for path in paths:
            if path in existing:
                continue
            ok, reason = validate_pdf_integrity(path)
            if not ok:
                show_error(self, "Cannot Add File", f"'{Path(path).name}': {reason}")
                continue
            widget.jobs.append(SigningJob(source_path=path))
        self._refresh_table(widget)

    def _remove_selected(self, widget) -> None:
        rows = {i.row() for i in widget.table.selectedIndexes()}
        widget.jobs = [j for i, j in enumerate(widget.jobs) if i not in rows]
        self._refresh_table(widget)

    def _clear_all(self, widget) -> None:
        widget.jobs.clear()
        self._refresh_table(widget)

    def _refresh_table(self, widget) -> None:
        widget.table.setRowCount(len(widget.jobs))
        for row, job in enumerate(widget.jobs):
            widget.table.setItem(row, 0, QTableWidgetItem(job.file_name))
            status_text = job.status.value if not job.selected_pages else f"{job.status.value} ({job.selected_pages})"
            widget.table.setItem(row, 1, QTableWidgetItem(status_text))

    def _browse_output(self, widget) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", widget.edit_output.text())
        if folder:
            widget.edit_output.setText(folder)

    def _run_batch(self, widget, process_fn, output_folder, progress_title, report_title) -> None:
        progress_dialog = ProgressDialog(progress_title, self)

        def on_job_finished(job: SigningJob) -> None:
            self._refresh_table(widget)
            progress_dialog.note_job_result(job.status)

        def on_batch_finished(result: BatchResult) -> None:
            progress_dialog.accept()
            ReportDialog(result, report_title, self).exec()

        worker = BatchWorker(list(widget.jobs), process_fn, output_folder or "")
        worker.progress_changed.connect(lambda c, t, name: progress_dialog.update_progress(c, t, name))
        worker.job_finished.connect(on_job_finished)
        worker.batch_finished.connect(on_batch_finished)
        worker.fatal_error.connect(lambda msg: show_error(self, "Processing Error", msg))
        progress_dialog.btn_cancel.clicked.connect(worker.cancel)
        worker.start()
        progress_dialog.exec()
