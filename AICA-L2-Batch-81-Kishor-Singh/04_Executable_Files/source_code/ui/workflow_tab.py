"""Batch Workflow tab: chain Convert -> Merge -> Sign -> Watermark/Seal -> Save into one pipeline.

Example from the spec: Word Agreement.docx + Annexure.pdf -> Merge -> Sign
last page -> Add CA seal -> Save as Agreement_Final.pdf. The same configured
pipeline can be run over many source documents at once.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.watermark_engine import ImageWatermarkOptions, PageNumberOptions, TextWatermarkOptions
from core.workflow_engine import WorkflowEngine, WorkflowStep, WorkflowStepKind
from core.signature_engine import SignatureApplication
from models.job import BatchResult, SigningJob
from ui.app_context import AppContext
from ui.widgets.dialogs import BatchConfirmationDialog, ProgressDialog, ReportDialog, show_error
from ui.widgets.signature_layer_widget import SignatureLayerWidget
from utils.file_utils import TempWorkspace, compute_output_path
from utils.logging_utils import get_logger, log_operation
from workers.batch_worker import BatchWorker
from models.enums import CollisionPolicy, NamingMode, WordEngine

logger = get_logger("workflow_tab")


class StepConfigDialog(QDialog):
    """Configures the parameters for one workflow step, form adapting to the kind."""

    def __init__(self, kind: WorkflowStepKind, database, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setWindowTitle(f"Configure Step: {kind.value}")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        self.merge_file_edit: QLineEdit | None = None
        self.signature_widget: SignatureLayerWidget | None = None
        self.text_edit: QLineEdit | None = None

        if kind == WorkflowStepKind.CONVERT_WORD_TO_PDF:
            layout.addWidget(QLabel("This step converts the current Word document to PDF. No configuration needed."))
        elif kind == WorkflowStepKind.MERGE_WITH:
            form = QFormLayout()
            row = QHBoxLayout()
            self.merge_file_edit = QLineEdit()
            btn = QPushButton("Browse...")
            btn.setObjectName("SecondaryButton")
            btn.clicked.connect(self._browse_merge_file)
            row.addWidget(self.merge_file_edit, 1)
            row.addWidget(btn)
            form.addRow("Additional PDF to append:", row)
            layout.addLayout(form)
        elif kind == WorkflowStepKind.SIGN:
            self.signature_widget = SignatureLayerWidget(removable=False, database=database)
            layout.addWidget(self.signature_widget)
        elif kind == WorkflowStepKind.ADD_WATERMARK_TEXT:
            form = QFormLayout()
            self.text_edit = QLineEdit("CONFIDENTIAL")
            form.addRow("Watermark text:", self.text_edit)
            layout.addLayout(form)
        elif kind == WorkflowStepKind.ADD_WATERMARK_IMAGE:
            self.signature_widget = SignatureLayerWidget(removable=False, database=database)
            layout.addWidget(QLabel("Configure the seal/stamp image, size, position and pages below:"))
            layout.addWidget(self.signature_widget)
        elif kind == WorkflowStepKind.ADD_PAGE_NUMBERS:
            form = QFormLayout()
            self.text_edit = QLineEdit("Page {n} of {total}")
            form.addRow("Format:", self.text_edit)
            layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_merge_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if path:
            self.merge_file_edit.setText(path)

    def build_step(self) -> WorkflowStep:
        if self.kind == WorkflowStepKind.MERGE_WITH:
            return WorkflowStep(self.kind, {"additional_files": [self.merge_file_edit.text().strip()]})
        if self.kind == WorkflowStepKind.SIGN:
            template = self.signature_widget.get_template()
            return WorkflowStep(self.kind, {"applications": [SignatureApplication(template=template)]})
        if self.kind == WorkflowStepKind.ADD_WATERMARK_TEXT:
            return WorkflowStep(self.kind, {"options": TextWatermarkOptions(text=self.text_edit.text().strip() or "DRAFT")})
        if self.kind == WorkflowStepKind.ADD_WATERMARK_IMAGE:
            template = self.signature_widget.get_template()
            options = ImageWatermarkOptions(
                image_path=template.image_path,
                width_pct=template.width_pct,
                height_pct=template.height_pct,
                opacity=template.opacity,
                rotation_degrees=template.rotation_degrees,
                position_preset=template.position_preset,
                pages_expression=template.page_rule_expression,
            )
            return WorkflowStep(self.kind, {"options": options})
        if self.kind == WorkflowStepKind.ADD_PAGE_NUMBERS:
            return WorkflowStep(self.kind, {"options": PageNumberOptions(format=self.text_edit.text().strip() or "Page {n} of {total}")})
        return WorkflowStep(self.kind, {})


class WorkflowTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.source_files: list[str] = []
        self.steps: list[WorkflowStep] = []
        self._worker: BatchWorker | None = None
        self._progress_dialog: ProgressDialog | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.addWidget(QLabel(
            "Build a repeatable pipeline (e.g. Convert Word to PDF -> Merge with Annexure -> Sign Last Page -> "
            "Add Seal) and run it over one or many source documents in one click."
        ))

        source_row = QHBoxLayout()
        self.btn_add_sources = QPushButton("Add Source Document(s)")
        self.btn_clear_sources = QPushButton("Clear")
        self.btn_clear_sources.setObjectName("SecondaryButton")
        source_row.addWidget(self.btn_add_sources)
        source_row.addWidget(self.btn_clear_sources)
        source_row.addStretch(1)
        root.addLayout(source_row)

        self.source_table = QTableWidget(0, 1)
        self.source_table.setHorizontalHeaderLabels(["Source Document"])
        self.source_table.horizontalHeader().setStretchLastSection(True)
        self.source_table.setMaximumHeight(120)
        root.addWidget(self.source_table)

        step_row = QHBoxLayout()
        self.combo_new_step = QComboBox()
        self.combo_new_step.addItems([k.value for k in WorkflowStepKind])
        self.btn_add_step = QPushButton("Add Step")
        self.btn_edit_step = QPushButton("Edit Step")
        self.btn_edit_step.setObjectName("SecondaryButton")
        self.btn_remove_step = QPushButton("Remove Step")
        self.btn_remove_step.setObjectName("DangerButton")
        self.btn_step_up = QPushButton("Move Up")
        self.btn_step_up.setObjectName("SecondaryButton")
        self.btn_step_down = QPushButton("Move Down")
        self.btn_step_down.setObjectName("SecondaryButton")
        step_row.addWidget(QLabel("Add step:"))
        step_row.addWidget(self.combo_new_step)
        step_row.addWidget(self.btn_add_step)
        step_row.addWidget(self.btn_edit_step)
        step_row.addWidget(self.btn_remove_step)
        step_row.addWidget(self.btn_step_up)
        step_row.addWidget(self.btn_step_down)
        root.addLayout(step_row)

        self.step_list = QListWidget()
        root.addWidget(self.step_list, 1)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output folder:"))
        self.edit_output_folder = QLineEdit(self.ctx.config.settings.default_output_folder)
        output_row.addWidget(self.edit_output_folder, 1)
        btn_browse = QPushButton("Browse...")
        btn_browse.setObjectName("SecondaryButton")
        btn_browse.clicked.connect(self._browse_output)
        output_row.addWidget(btn_browse)
        root.addLayout(output_row)

        suffix_row = QHBoxLayout()
        suffix_row.addWidget(QLabel("Output suffix:"))
        self.edit_suffix = QLineEdit("_Final")
        suffix_row.addWidget(self.edit_suffix)
        root.addLayout(suffix_row)

        self.btn_run = QPushButton("RUN WORKFLOW")
        self.btn_run.setMinimumHeight(40)
        root.addWidget(self.btn_run)

        self.btn_add_sources.clicked.connect(self.add_sources)
        self.btn_clear_sources.clicked.connect(self.clear_sources)
        self.btn_add_step.clicked.connect(self.add_step)
        self.btn_edit_step.clicked.connect(self.edit_step)
        self.btn_remove_step.clicked.connect(self.remove_step)
        self.btn_step_up.clicked.connect(lambda: self._move_step(-1))
        self.btn_step_down.clicked.connect(lambda: self._move_step(1))
        self.btn_run.clicked.connect(self.run_workflow)

    # ------------------------------------------------------------- sources
    def add_sources(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Source Documents", "", "Documents (*.pdf *.docx *.doc)")
        for p in paths:
            if p not in self.source_files:
                self.source_files.append(p)
        self._refresh_sources()

    def clear_sources(self) -> None:
        self.source_files.clear()
        self._refresh_sources()

    def _refresh_sources(self) -> None:
        self.source_table.setRowCount(len(self.source_files))
        for row, path in enumerate(self.source_files):
            self.source_table.setItem(row, 0, QTableWidgetItem(path))

    # --------------------------------------------------------------- steps
    def add_step(self) -> None:
        kind = WorkflowStepKind(self.combo_new_step.currentText())
        dlg = StepConfigDialog(kind, self.ctx.database, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        step = dlg.build_step()
        self.steps.append(step)
        self.step_list.addItem(QListWidgetItem(step.label()))

    def edit_step(self) -> None:
        row = self.step_list.currentRow()
        if row < 0:
            return
        step = self.steps[row]
        dlg = StepConfigDialog(step.kind, self.ctx.database, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self.steps[row] = dlg.build_step()

    def remove_step(self) -> None:
        row = self.step_list.currentRow()
        if row < 0:
            return
        self.steps.pop(row)
        self.step_list.takeItem(row)

    def _move_step(self, delta: int) -> None:
        row = self.step_list.currentRow()
        new_row = row + delta
        if row < 0 or not (0 <= new_row < len(self.steps)):
            return
        self.steps[row], self.steps[new_row] = self.steps[new_row], self.steps[row]
        item = self.step_list.takeItem(row)
        self.step_list.insertItem(new_row, item)
        self.step_list.setCurrentRow(new_row)

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.edit_output_folder.text())
        if folder:
            self.edit_output_folder.setText(folder)

    def process(self) -> None:
        self.run_workflow()

    # ------------------------------------------------------------ execution
    def run_workflow(self) -> None:
        if not self.source_files:
            QMessageBox.information(self, "No Source Documents", "Add at least one source document.")
            return
        if not self.steps:
            QMessageBox.information(self, "No Steps", "Add at least one workflow step.")
            return

        summary = [
            f"Source documents: {len(self.source_files)}",
            f"Steps: {' -> '.join(s.label() for s in self.steps)}",
            f"Output folder: {self.edit_output_folder.text().strip() or '(same as source)'}",
        ]
        dlg = BatchConfirmationDialog("Run Batch Workflow", summary, f"RUN WORKFLOW ON {len(self.source_files)} DOCUMENT(S)", self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        output_folder = self.edit_output_folder.text().strip() or None
        suffix = self.edit_suffix.text().strip() or "_Final"
        steps = list(self.steps)
        jobs = [SigningJob(source_path=p) for p in self.source_files]

        def process_fn(job: SigningJob) -> None:
            final_output = compute_output_path(
                Path(job.source_path).with_suffix(".pdf"), output_folder, NamingMode.ADD_SUFFIX, suffix, "", CollisionPolicy.RENAME
            )
            with TempWorkspace(self.ctx.config.get_temp_folder()) as ws:
                engine = WorkflowEngine(
                    word_engine=WordEngine(self.ctx.config.settings.word_conversion_engine),
                    libreoffice_path=self.ctx.config.settings.libreoffice_path,
                )
                result_path = engine.run(job.source_path, steps, ws, final_output)
            job.output_path = result_path
            from core.pdf_engine import get_page_count

            job.total_pages = get_page_count(result_path)
            log_operation(logger, operation="workflow", input_file=job.source_path, output_file=result_path, pages=job.total_pages, result="success")

        self._progress_dialog = ProgressDialog("Running Workflow...", self)
        self._worker = BatchWorker(jobs, process_fn, output_folder or "")
        self._worker.progress_changed.connect(lambda c, t, name: self._progress_dialog and self._progress_dialog.update_progress(c, t, name))
        self._worker.job_finished.connect(lambda job: self._progress_dialog and self._progress_dialog.note_job_result(job.status))
        self._worker.batch_finished.connect(self._on_finished)
        self._worker.fatal_error.connect(lambda msg: show_error(self, "Workflow Error", msg))
        self._progress_dialog.btn_cancel.clicked.connect(self._worker.cancel)
        self._worker.start()
        self._progress_dialog.exec()

    def _on_finished(self, result: BatchResult) -> None:
        if self._progress_dialog:
            self._progress_dialog.accept()
            self._progress_dialog = None
        ReportDialog(result, "Batch Workflow", self).exec()
