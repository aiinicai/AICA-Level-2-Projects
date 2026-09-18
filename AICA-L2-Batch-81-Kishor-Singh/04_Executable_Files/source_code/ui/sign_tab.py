"""Sign PDF tab -- the application's flagship feature.

Workflow: drag/add PDFs -> configure one or more signature layers (with a
saved template or from scratch) -> optionally override individual files ->
SIGN ALL. See :mod:`workers.batch_worker` for how the actual signing runs
off the GUI thread.
"""
from __future__ import annotations

import copy
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.page_selection import PageSelectionRule, describe_expression
from core.pdf_engine import get_page_count, validate_pdf_integrity
from core.signature_engine import SignatureApplication, SignatureImageProcessor, apply_signatures_to_pdf, resolve_placement
from models.enums import CollisionPolicy, JobStatus, NamingMode, PageSelectionMode, PositionPreset, SignatureKind
from models.job import BatchResult, SigningJob
from models.signature_template import SignatureTemplate
from ui.app_context import AppContext
from ui.widgets.dialogs import BatchConfirmationDialog, PasswordPromptDialog, ProgressDialog, ReportDialog, show_error
from ui.widgets.file_table_widget import FileTableWidget
from ui.widgets.pdf_preview_widget import PdfPreviewWidget
from ui.widgets.signature_layer_widget import SignatureLayerWidget
from utils.database import AuditEntry
from utils.file_utils import TempWorkspace, atomic_replace, compute_output_path, find_pdfs_in_folder
from utils.logging_utils import get_logger, log_operation
from utils.validation import EncryptedPdfError, ValidationError
from workers.batch_worker import BatchWorker, build_retry_worker

logger = get_logger("sign_tab")


@dataclass
class FileOverride:
    page_rule_expression: str | None = None
    position_preset: PositionPreset | None = None


class OverrideDialog(QDialog):
    """Per-file override of the primary (first) signature layer's rule/position."""

    def __init__(self, file_name: str, current: FileOverride, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Override Rule — {file_name}")
        layout = QFormLayout(self)

        self.combo_mode = QComboBox()
        self.combo_mode.addItem("(Use global setting)")
        self.combo_mode.addItems([m.value for m in PageSelectionMode])
        self.edit_expression = QLineEdit()
        self.edit_expression.setPlaceholderText("e.g. 2  or  last  or  1,4,7  or 1,3,5-8,last")
        if current.page_rule_expression:
            self.edit_expression.setText(current.page_rule_expression)
            self.combo_mode.setCurrentText(PageSelectionMode.CUSTOM.value)

        self.combo_position = QComboBox()
        self.combo_position.addItem("(Use global setting)")
        self.combo_position.addItems([p.value for p in PositionPreset])
        if current.position_preset:
            self.combo_position.setCurrentText(current.position_preset.value)

        layout.addRow("Page rule for this file:", self.combo_mode)
        layout.addRow("Custom expression:", self.edit_expression)
        layout.addRow("Position for this file:", self.combo_position)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def result_override(self) -> FileOverride:
        mode_text = self.combo_mode.currentText()
        expr = None
        if mode_text != "(Use global setting)":
            if mode_text == PageSelectionMode.CUSTOM.value or self.edit_expression.text().strip():
                expr = self.edit_expression.text().strip() or "all"
            else:
                # Build a quick expression from a non-custom preset with no extra param.
                simple = PageSelectionRule(mode=PageSelectionMode(mode_text))
                expr = simple.to_expression()
        pos_text = self.combo_position.currentText()
        pos = PositionPreset(pos_text) if pos_text != "(Use global setting)" else None
        return FileOverride(page_rule_expression=expr, position_preset=pos)


class SignTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.jobs: list[SigningJob] = []
        self.overrides: dict[str, FileOverride] = {}
        self.passwords: dict[str, str] = {}
        self.layers: list[SignatureLayerWidget] = []
        self._worker: BatchWorker | None = None
        self._progress_dialog: ProgressDialog | None = None
        self._workspace: TempWorkspace | None = None

        self._build_ui()
        self.add_layer(SignatureKind.SIGNATURE)

    # --------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # ---- left: file list -------------------------------------------------
        left = QWidget()
        left_layout = QVBoxLayout(left)
        toolbar = QHBoxLayout()
        self.btn_add_files = QPushButton("Add Files")
        self.btn_add_folder = QPushButton("Add Folder")
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_remove.setObjectName("SecondaryButton")
        self.btn_up = QPushButton("Move Up")
        self.btn_up.setObjectName("SecondaryButton")
        self.btn_down = QPushButton("Move Down")
        self.btn_down.setObjectName("SecondaryButton")
        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.setObjectName("DangerButton")
        for b in (self.btn_add_files, self.btn_add_folder, self.btn_remove, self.btn_up, self.btn_down, self.btn_clear):
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        left_layout.addLayout(toolbar)

        self.table = FileTableWidget()
        self.table.files_added.connect(self._add_file_paths)
        self.table.itemDoubleClicked.connect(lambda *_: self.edit_override_for_selected())
        left_layout.addWidget(self.table, 1)
        left_layout.addWidget(QLabel("Tip: double-click a row to override its page rule / position individually."))
        splitter.addWidget(left)

        # ---- right: layers, preview, output, action --------------------------
        right = QScrollArea()
        right.setWidgetResizable(True)
        right_inner = QWidget()
        right_layout = QVBoxLayout(right_inner)
        right.setWidget(right_inner)

        layer_group = QGroupBox("Signature Layers")
        layer_layout = QVBoxLayout(layer_group)
        add_layer_row = QHBoxLayout()
        self.combo_new_layer_kind = QComboBox()
        self.combo_new_layer_kind.addItems([k.value for k in SignatureKind])
        self.btn_add_layer = QPushButton("Add Layer")
        add_layer_row.addWidget(QLabel("New layer:"))
        add_layer_row.addWidget(self.combo_new_layer_kind)
        add_layer_row.addWidget(self.btn_add_layer)
        add_layer_row.addStretch(1)
        layer_layout.addLayout(add_layer_row)

        layer_body = QHBoxLayout()
        self.layer_list = QListWidget()
        self.layer_list.setMaximumWidth(160)
        self.layer_stack = QStackedWidget()
        layer_body.addWidget(self.layer_list)
        layer_body.addWidget(self.layer_stack, 1)
        layer_layout.addLayout(layer_body)
        right_layout.addWidget(layer_group)

        preview_group = QGroupBox("Interactive Preview — drag the signature onto the page")
        preview_layout = QVBoxLayout(preview_group)
        preview_toolbar = QHBoxLayout()
        self.btn_load_preview = QPushButton("Load Selected File Into Preview")
        self.btn_load_preview.setObjectName("SecondaryButton")
        self.btn_use_position = QPushButton("Use This Position For Selected Layer")
        preview_toolbar.addWidget(self.btn_load_preview)
        preview_toolbar.addWidget(self.btn_use_position)
        preview_toolbar.addStretch(1)
        preview_layout.addLayout(preview_toolbar)
        self.preview = PdfPreviewWidget()
        self.preview.setMinimumHeight(320)
        preview_layout.addWidget(self.preview)
        right_layout.addWidget(preview_group)

        output_group = QGroupBox("Output Options")
        output_form = QFormLayout(output_group)
        folder_row = QHBoxLayout()
        self.edit_output_folder = QLineEdit(self.ctx.config.settings.default_output_folder)
        self.btn_browse_output = QPushButton("Browse...")
        self.btn_browse_output.setObjectName("SecondaryButton")
        folder_row.addWidget(self.edit_output_folder, 1)
        folder_row.addWidget(self.btn_browse_output)
        output_form.addRow("Output folder:", folder_row)

        self.combo_naming = QComboBox()
        self.combo_naming.addItems([m.value for m in NamingMode])
        self.combo_naming.setCurrentText(self.ctx.config.settings.naming_mode)
        output_form.addRow("Naming:", self.combo_naming)

        self.edit_suffix = QLineEdit(self.ctx.config.settings.naming_suffix)
        self.edit_prefix = QLineEdit(self.ctx.config.settings.naming_prefix)
        output_form.addRow("Suffix (Add Suffix mode):", self.edit_suffix)
        output_form.addRow("Prefix (Add Prefix mode):", self.edit_prefix)

        self.combo_collision = QComboBox()
        self.combo_collision.addItems([c.value for c in CollisionPolicy])
        self.combo_collision.setCurrentText(self.ctx.config.settings.collision_policy)
        output_form.addRow("If file already exists:", self.combo_collision)
        right_layout.addWidget(output_group)

        self.btn_sign_all = QPushButton("SIGN ALL SELECTED PDFs")
        self.btn_sign_all.setMinimumHeight(44)
        self.btn_sign_all.setStyleSheet("font-size: 15px;")
        right_layout.addWidget(self.btn_sign_all)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # ---- wiring ------------------------------------------------------
        self.btn_add_files.clicked.connect(self.add_files)
        self.btn_add_folder.clicked.connect(self.add_folder)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_up.clicked.connect(lambda: self._move_selected(-1))
        self.btn_down.clicked.connect(lambda: self._move_selected(1))
        self.btn_add_layer.clicked.connect(lambda: self.add_layer(SignatureKind(self.combo_new_layer_kind.currentText())))
        self.layer_list.currentRowChanged.connect(self.layer_stack.setCurrentIndex)
        self.layer_list.currentRowChanged.connect(lambda *_: self._refresh_preview_overlay())
        self.btn_browse_output.clicked.connect(self._browse_output_folder)
        self.btn_load_preview.clicked.connect(self._load_selected_into_preview)
        self.btn_use_position.clicked.connect(self._apply_dragged_position)
        self.btn_sign_all.clicked.connect(self.sign_all)

    # ---------------------------------------------------------------- layers
    def add_layer(self, kind: SignatureKind) -> None:
        widget = SignatureLayerWidget(kind=kind, removable=len(self.layers) >= 0, database=self.ctx.database)
        widget.remove_requested.connect(lambda w=widget: self._remove_layer(w))
        widget.changed.connect(self._refresh_preview_overlay)
        self.layers.append(widget)
        self.layer_stack.addWidget(widget)
        self.layer_list.addItem(kind.value)
        self.layer_list.setCurrentRow(self.layer_list.count() - 1)

    def _remove_layer(self, widget: SignatureLayerWidget) -> None:
        if len(self.layers) <= 1:
            QMessageBox.warning(self, "Cannot Remove", "At least one signature layer is required.")
            return
        index = self.layers.index(widget)
        self.layers.pop(index)
        self.layer_stack.removeWidget(widget)
        widget.deleteLater()
        self.layer_list.takeItem(index)

    # ------------------------------------------------------------- file mgmt
    def add_files(self) -> None:
        last_folder = self.ctx.config.settings.last_used_folder
        paths, _ = QFileDialog.getOpenFileNames(self, "Select PDF Files", last_folder, "PDF Files (*.pdf)")
        self._add_file_paths(paths)

    def add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing PDFs", self.ctx.config.settings.last_used_folder)
        if folder:
            self._remember_folder(folder)
            self._add_file_paths([str(p) for p in find_pdfs_in_folder(folder)])

    def _remember_folder(self, folder: str) -> None:
        if self.ctx.config.settings.remember_last_folder:
            self.ctx.config.settings.last_used_folder = folder
            self.ctx.config.save()

    def _add_file_paths(self, paths: list[str]) -> None:
        existing = {j.source_path for j in self.jobs}
        for path in paths:
            if path in existing:
                continue
            ok, reason = validate_pdf_integrity(path)
            if not ok:
                show_error(self, "Cannot Add File", f"'{Path(path).name}' could not be added:\n{reason}")
                continue
            password = None
            if reason == "Password protected":
                dlg = PasswordPromptDialog(Path(path).name, self)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    continue
                password = dlg.password()
                try:
                    get_page_count(path, password)
                except EncryptedPdfError as exc:
                    show_error(self, "Incorrect Password", str(exc))
                    continue
                self.passwords[path] = password
            job = SigningJob(source_path=path)
            try:
                job.total_pages = get_page_count(path, password)
            except ValidationError:
                job.total_pages = 0
            self.jobs.append(job)
            if paths:
                self._remember_folder(str(Path(path).parent))
        self.table.set_jobs(self.jobs)

    def remove_selected(self) -> None:
        rows = set(self.table.selected_rows())
        if not rows:
            return
        self.jobs = [j for i, j in enumerate(self.jobs) if i not in rows]
        self.table.set_jobs(self.jobs)

    def select_all(self) -> None:
        self.table.selectAll()

    def clear_all(self) -> None:
        self.jobs.clear()
        self.overrides.clear()
        self.passwords.clear()
        self.table.set_jobs(self.jobs)

    def _move_selected(self, delta: int) -> None:
        rows = self.table.selected_rows()
        if len(rows) != 1:
            return
        new_row = self.table.move_row(rows[0], delta)
        self.table.selectRow(new_row)

    def edit_override_for_selected(self) -> None:
        rows = self.table.selected_rows()
        if len(rows) != 1:
            return
        job = self.jobs[rows[0]]
        current = self.overrides.get(job.job_id, FileOverride())
        dlg = OverrideDialog(job.file_name, current, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            result = dlg.result_override()
            if result.page_rule_expression or result.position_preset:
                self.overrides[job.job_id] = result
            else:
                self.overrides.pop(job.job_id, None)
            self.table.refresh()

    # ---------------------------------------------------------------- preview
    def _load_selected_into_preview(self) -> None:
        rows = self.table.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select a File", "Select a file in the table first.")
            return
        job = self.jobs[rows[0]]
        try:
            self.preview.load_pdf(job.source_path, self.passwords.get(job.source_path))
        except ValidationError as exc:
            show_error(self, "Cannot Preview File", str(exc))
            return
        self._refresh_preview_overlay()

    def _current_layer(self) -> SignatureLayerWidget | None:
        row = self.layer_list.currentRow()
        return self.layers[row] if 0 <= row < len(self.layers) else None

    def _refresh_preview_overlay(self) -> None:
        layer = self._current_layer()
        if layer is None or self.preview.page_count == 0:
            return
        image_path = layer.edit_image_path.text().strip()
        if not image_path or not Path(image_path).exists():
            self.preview.remove_overlay()
            return
        template = layer.get_template()
        try:
            prepared = SignatureImageProcessor.prepare(
                image_path, autocrop=False, opacity_pct=template.opacity, rotation_degrees=template.rotation_degrees
            )
        except ValidationError:
            return
        page_w, page_h = self.preview.get_page_size_pt()
        placement = resolve_placement(template, page_w, page_h)
        x_pct = (placement.x_pt / page_w) * 100 if page_w else 0
        y_pct = (placement.y_pt / page_h) * 100 if page_h else 0
        self.preview.set_signature_overlay(prepared.png_bytes, x_pct, y_pct, template.width_pct, template.height_pct)

    def _apply_dragged_position(self) -> None:
        layer = self._current_layer()
        placement = self.preview.get_overlay_placement_pct()
        if layer is None or placement is None:
            return
        x_pct, y_pct, w_pct, h_pct = placement
        layer.combo_position.setCurrentText(PositionPreset.CUSTOM.value)
        layer.spin_custom_x.setValue(x_pct)
        layer.spin_custom_y.setValue(y_pct)
        layer.spin_width.setValue(w_pct)
        layer.spin_height.setValue(h_pct)

    # ---------------------------------------------------------------- output
    def _browse_output_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.edit_output_folder.text())
        if folder:
            self.edit_output_folder.setText(folder)

    # --------------------------------------------------------------- signing
    def process(self) -> None:
        self.sign_all()

    def sign_all(self) -> None:
        if not self.jobs:
            QMessageBox.information(self, "No Files", "Add at least one PDF before signing.")
            return
        for layer in self.layers:
            image_path = layer.edit_image_path.text().strip()
            if not image_path or not Path(image_path).exists():
                show_error(self, "Missing Signature Image", f"The '{layer.combo_kind.currentText()}' layer has no valid image selected.")
                return

        total_pages = sum(j.total_pages for j in self.jobs)
        primary_template = self.layers[0].get_template()
        summary = [
            f"Documents selected: {len(self.jobs)}",
            f"Total PDF pages: {total_pages}",
            f"Signature layers: {len(self.layers)} ({', '.join(l.combo_kind.currentText() for l in self.layers)})",
            f"Primary signing rule: {describe_expression(primary_template.page_rule_expression)}",
            f"Primary position: {primary_template.position_preset.value}",
            f"Output folder: {self.edit_output_folder.text().strip() or '(same as source)'}",
            f"Per-file overrides configured: {len(self.overrides)}",
        ]
        naming_mode = NamingMode(self.combo_naming.currentText())
        if naming_mode == NamingMode.OVERWRITE_ORIGINAL and self.ctx.config.settings.confirm_before_overwrite:
            proceed = QMessageBox.warning(
                self,
                "Overwrite Original Files?",
                f"This will REPLACE all {len(self.jobs)} original PDF file(s) with their signed versions.\n\n"
                "This cannot be undone. Consider using 'Add Suffix' instead if you want to keep the originals.\n\n"
                "Continue and overwrite the originals?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if proceed != QMessageBox.StandardButton.Yes:
                return

        dlg = BatchConfirmationDialog("Sign All Selected Documents", summary, f"SIGN ALL {len(self.jobs)} DOCUMENTS", self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            if dlg.preview_requested and self.jobs:
                self.table.selectRow(0)
                self._load_selected_into_preview()
            return

        self._run_batch()

    def _run_batch(self) -> None:
        output_folder = self.edit_output_folder.text().strip() or None
        naming_mode = NamingMode(self.combo_naming.currentText())
        suffix = self.edit_suffix.text() or "_Signed"
        prefix = self.edit_prefix.text() or "Signed_"
        collision_policy = CollisionPolicy(self.combo_collision.currentText())
        layer_templates = [layer.get_template() for layer in self.layers]
        overrides = dict(self.overrides)
        passwords = dict(self.passwords)
        self._workspace = TempWorkspace(self.ctx.config.get_temp_folder())

        process_fn = self.build_process_fn(
            output_folder, naming_mode, suffix, prefix, collision_policy, layer_templates, overrides, passwords, self._workspace
        )

        self._progress_dialog = ProgressDialog("Signing Documents...", self)
        self._worker = BatchWorker(list(self.jobs), process_fn, output_folder or "")
        self._wire_worker(self._worker)
        self._progress_dialog.btn_cancel.clicked.connect(self._worker.cancel)
        self._worker.start()
        self._progress_dialog.exec()

    def build_process_fn(
        self,
        output_folder: str | None,
        naming_mode: NamingMode,
        suffix: str,
        prefix: str,
        collision_policy: CollisionPolicy,
        layer_templates: list[SignatureTemplate],
        overrides: dict[str, FileOverride],
        passwords: dict[str, str],
        workspace: TempWorkspace,
    ):
        """Build the per-job signing closure, decoupled from any Qt dialog/thread.

        Kept as a standalone method (rather than inline in ``_run_batch``) so
        the actual signing logic can be unit-exercised directly, without
        needing to drive the confirmation/progress dialogs.
        """
        database = self.ctx.database
        operator = self.ctx.operator
        register_enabled = self.ctx.config.settings.enable_activity_register

        def process_fn(job: SigningJob) -> None:
            password = passwords.get(job.source_path)
            applications: list[SignatureApplication] = []
            override = overrides.get(job.job_id)
            for idx, template in enumerate(layer_templates):
                effective = copy.deepcopy(template)
                if idx == 0 and override:
                    if override.page_rule_expression:
                        effective.page_rule_expression = override.page_rule_expression
                    if override.position_preset:
                        effective.position_preset = override.position_preset
                applications.append(SignatureApplication(template=effective))

            final_output = compute_output_path(job.source_path, output_folder, naming_mode, suffix, prefix, collision_policy)
            if final_output is None:
                job.status = JobStatus.SKIPPED
                job.error_message = "Output file already exists (skipped per collision policy)."
                return

            temp_output = workspace.new_file(".pdf")
            outcome = apply_signatures_to_pdf(job.source_path, temp_output, applications, password)
            atomic_replace(temp_output, final_output)

            job.total_pages = outcome.total_pages
            job.selected_pages = ", ".join(str(p) for p in outcome.signed_pages)
            job.position_label = (override.position_preset.value if override and override.position_preset else layer_templates[0].position_preset.value)
            job.output_path = str(final_output)
            job.template_used = ", ".join(t.name for t in layer_templates)

            log_operation(
                logger,
                operation="sign",
                input_file=job.source_path,
                output_file=str(final_output),
                pages=job.total_pages,
                signing_pages=job.selected_pages,
                result="success",
            )
            if register_enabled:
                from datetime import datetime

                database.add_audit_entry(
                    AuditEntry(
                        timestamp=datetime.now().isoformat(),
                        operator=operator,
                        operation="Sign PDF",
                        source_document=job.source_path,
                        output_document=str(final_output),
                        pages_processed=job.selected_pages,
                        template_used=job.template_used,
                        result="Success",
                    )
                )
                database.add_recent_job(job.job_id, "Sign PDF", job.file_name, job.output_file_name, "Success")

        return process_fn

    def _wire_worker(self, worker: BatchWorker) -> None:
        worker.progress_changed.connect(lambda c, t, name: self._progress_dialog and self._progress_dialog.update_progress(c, t, name))
        worker.job_finished.connect(self._on_job_finished)
        worker.batch_finished.connect(self._on_batch_finished)
        worker.fatal_error.connect(lambda msg: show_error(self, "Processing Error", msg))

    def _on_job_finished(self, job: SigningJob) -> None:
        self.table.update_job_row(job)
        if self._progress_dialog:
            self._progress_dialog.note_job_result(job.status)
        if job.status == JobStatus.FAILED:
            log_operation(logger, operation="sign", input_file=job.source_path, result="failed", error=job.error_message)

    def _on_batch_finished(self, result: BatchResult) -> None:
        if self._progress_dialog:
            self._progress_dialog.accept()
            self._progress_dialog = None
        if self._workspace:
            self._workspace.cleanup()
            self._workspace = None

        report = ReportDialog(result, "Signing", self)
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
                os.startfile(folder)  # noqa: S606 - opening a folder the user chose, not arbitrary input
            else:
                subprocess.Popen(["xdg-open", folder])
        except OSError:
            pass
