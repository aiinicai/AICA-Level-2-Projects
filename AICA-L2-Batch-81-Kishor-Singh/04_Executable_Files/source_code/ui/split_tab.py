"""Split / Demerge PDF tab: every page, ranges, extraction, every-N, equal parts, page removal."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.pdf_engine import validate_pdf_integrity
from core.split_engine import SplitEngine
from models.enums import SplitMode
from models.job import BatchResult, SigningJob
from ui.app_context import AppContext
from ui.widgets.dialogs import BatchConfirmationDialog, ProgressDialog, ReportDialog, show_error
from ui.widgets.pdf_preview_widget import PdfPreviewWidget
from utils.database import AuditEntry
from utils.file_utils import find_pdfs_in_folder
from utils.logging_utils import get_logger, log_operation
from utils.validation import ValidationError
from workers.batch_worker import BatchWorker

logger = get_logger("split_tab")


class SplitTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.jobs: list[SigningJob] = []
        self._worker: BatchWorker | None = None
        self._progress_dialog: ProgressDialog | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

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
        self.table.setHorizontalHeaderLabels(["File Name", "Pages"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.cellClicked.connect(self._on_row_clicked)
        root.addWidget(self.table, 1)

        self.preview = PdfPreviewWidget()
        self.preview.setMaximumHeight(220)
        root.addWidget(self.preview)

        mode_group = QGroupBox("Split Mode")
        mode_layout = QVBoxLayout(mode_group)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems([m.value for m in SplitMode])
        mode_layout.addWidget(self.combo_mode)

        self.param_stack = QStackedWidget()
        self._page_every = QLabel("Each page will be saved as its own PDF file.")
        self.param_stack.addWidget(self._page_every)

        self._page_ranges = QPlainTextEdit()
        self._page_ranges.setPlaceholderText("One range per line, e.g.\n1-5\n6-10\n11-20")
        self._page_ranges.setMaximumHeight(80)
        self.param_stack.addWidget(self._page_ranges)

        self._page_extract = QLineEdit()
        self._page_extract.setPlaceholderText("e.g. 1,3,7-10")
        self.param_stack.addWidget(self._page_extract)

        n_widget = QWidget()
        n_form = QFormLayout(n_widget)
        self._spin_every_n = QSpinBox()
        self._spin_every_n.setRange(1, 10000)
        self._spin_every_n.setValue(5)
        n_form.addRow("Split every N pages, N =", self._spin_every_n)
        self.param_stack.addWidget(n_widget)

        parts_widget = QWidget()
        parts_form = QFormLayout(parts_widget)
        self._spin_parts = QSpinBox()
        self._spin_parts.setRange(1, 1000)
        self._spin_parts.setValue(2)
        parts_form.addRow("Number of equal parts:", self._spin_parts)
        self.param_stack.addWidget(parts_widget)

        self._page_remove = QLineEdit()
        self._page_remove.setPlaceholderText("e.g. 2,5,8")
        self.param_stack.addWidget(self._page_remove)

        mode_layout.addWidget(self.param_stack)
        root.addWidget(mode_group)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output folder:"))
        self.edit_output_folder = QLineEdit(self.ctx.config.settings.default_output_folder)
        output_row.addWidget(self.edit_output_folder, 1)
        self.btn_browse_output = QPushButton("Browse...")
        self.btn_browse_output.setObjectName("SecondaryButton")
        output_row.addWidget(self.btn_browse_output)
        root.addLayout(output_row)

        self.btn_split = QPushButton("SPLIT PDF(s)")
        self.btn_split.setMinimumHeight(40)
        root.addWidget(self.btn_split)

        self.combo_mode.currentIndexChanged.connect(self.param_stack.setCurrentIndex)
        self.btn_add_files.clicked.connect(self.add_files)
        self.btn_add_folder.clicked.connect(self.add_folder)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_browse_output.clicked.connect(self._browse_output)
        self.btn_split.clicked.connect(self.split_all)

    # -------------------------------------------------------------- file mgmt
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
            from core.pdf_engine import get_page_count

            job = SigningJob(source_path=path)
            try:
                job.total_pages = get_page_count(path)
            except ValidationError:
                job.total_pages = 0
            self.jobs.append(job)
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
            self.table.setItem(row, 1, QTableWidgetItem(str(job.total_pages)))

    def _on_row_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self.jobs):
            try:
                self.preview.load_pdf(self.jobs[row].source_path)
            except ValidationError as exc:
                show_error(self, "Cannot Preview", str(exc))

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.edit_output_folder.text())
        if folder:
            self.edit_output_folder.setText(folder)

    def process(self) -> None:
        self.split_all()

    # ------------------------------------------------------------- splitting
    def split_all(self) -> None:
        if not self.jobs:
            QMessageBox.information(self, "No Files", "Add at least one PDF to split.")
            return
        mode = SplitMode(self.combo_mode.currentText())
        output_folder = self.edit_output_folder.text().strip() or None

        summary = [
            f"Documents selected: {len(self.jobs)}",
            f"Split mode: {mode.value}",
            f"Output folder: {output_folder or '(same as source)'}",
        ]
        dlg = BatchConfirmationDialog("Split PDF(s)", summary, f"SPLIT {len(self.jobs)} DOCUMENT(S)", self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        ranges = [r.strip() for r in self._page_ranges.toPlainText().splitlines() if r.strip()]
        extract_expr = self._page_extract.text().strip() or "all"
        remove_expr = self._page_remove.text().strip() or ""
        every_n = self._spin_every_n.value()
        num_parts = self._spin_parts.value()
        database = self.ctx.database
        operator = self.ctx.operator
        register_enabled = self.ctx.config.settings.enable_activity_register

        def process_fn(job: SigningJob) -> None:
            engine = SplitEngine(job.source_path, output_folder=output_folder)
            if mode == SplitMode.EVERY_PAGE:
                result = engine.split_every_page()
            elif mode == SplitMode.BY_RANGE:
                if not ranges:
                    raise ValidationError("No page ranges specified.")
                result = engine.split_by_ranges(ranges)
            elif mode == SplitMode.EXTRACT_PAGES:
                result = engine.extract_pages(extract_expr)
            elif mode == SplitMode.EVERY_N_PAGES:
                result = engine.split_every_n_pages(every_n)
            elif mode == SplitMode.EQUAL_PARTS:
                result = engine.split_into_equal_parts(num_parts)
            else:  # REMOVE_PAGES
                if not remove_expr:
                    raise ValidationError("No pages specified to remove.")
                result = engine.remove_pages(remove_expr)

            job.output_path = str(Path(result.output_files[0].output_path).parent) if result.output_files else ""
            job.selected_pages = f"{result.total_output_files} file(s) created"
            log_operation(logger, operation="split", input_file=job.source_path, pages=job.total_pages, result="success")
            if register_enabled:
                from datetime import datetime

                database.add_audit_entry(
                    AuditEntry(
                        timestamp=datetime.now().isoformat(),
                        operator=operator,
                        operation=f"Split PDF ({mode.value})",
                        source_document=job.source_path,
                        output_document=job.output_path,
                        pages_processed=job.selected_pages,
                        template_used="",
                        result="Success",
                    )
                )

        self._progress_dialog = ProgressDialog("Splitting Documents...", self)
        self._worker = BatchWorker(list(self.jobs), process_fn, output_folder or "")
        self._worker.progress_changed.connect(lambda c, t, name: self._progress_dialog and self._progress_dialog.update_progress(c, t, name))
        self._worker.job_finished.connect(self._on_job_finished)
        self._worker.batch_finished.connect(self._on_batch_finished)
        self._worker.fatal_error.connect(lambda msg: show_error(self, "Processing Error", msg))
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
        report = ReportDialog(result, "Split PDF", self)
        report.exec()
