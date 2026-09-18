"""Merge PDF tab: reorder files, per-file page ranges, combine into one PDF."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.merge_engine import MergeItem, merge_pdfs
from core.pdf_engine import get_page_count, validate_pdf_integrity
from ui.app_context import AppContext
from ui.widgets.dialogs import show_error
from ui.widgets.pdf_preview_widget import PdfPreviewWidget
from utils.database import AuditEntry
from utils.file_utils import find_pdfs_in_folder, human_size
from utils.logging_utils import get_logger, log_operation
from utils.validation import ValidationError

logger = get_logger("merge_tab")


class MergeTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.files: list[str] = []
        self.page_expressions: dict[str, str] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

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
        root.addLayout(toolbar)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["File Name", "Pages", "File Size", "Pages to Include"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self._on_item_changed)
        root.addWidget(self.table, 1)
        root.addWidget(QLabel('"Pages to Include" accepts: all, 1-5, 2,4,6-8, first, last, etc. Double-click to edit.'))

        self.preview = PdfPreviewWidget()
        self.preview.setMaximumHeight(260)
        root.addWidget(self.preview)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output file name:"))
        self.edit_output_name = QLineEdit("Merged.pdf")
        output_row.addWidget(self.edit_output_name, 1)
        self.btn_browse_output = QPushButton("Choose Output Location...")
        self.btn_browse_output.setObjectName("SecondaryButton")
        output_row.addWidget(self.btn_browse_output)
        root.addLayout(output_row)
        self.output_dir = self.ctx.config.settings.default_output_folder

        self.btn_merge = QPushButton("MERGE PDFs")
        self.btn_merge.setMinimumHeight(40)
        root.addWidget(self.btn_merge)

        self.btn_add_files.clicked.connect(self.add_files)
        self.btn_add_folder.clicked.connect(self.add_folder)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_up.clicked.connect(lambda: self._move(-1))
        self.btn_down.clicked.connect(lambda: self._move(1))
        self.table.cellDoubleClicked.connect(self._on_row_activated)
        self.btn_browse_output.clicked.connect(self._browse_output)
        self.btn_merge.clicked.connect(self.merge_all)

    # -------------------------------------------------------------- file mgmt
    def add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select PDF Files", self.ctx.config.settings.last_used_folder, "PDF Files (*.pdf)")
        self._add_paths(paths)

    def add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", self.ctx.config.settings.last_used_folder)
        if folder:
            self._add_paths([str(p) for p in find_pdfs_in_folder(folder)])

    def _add_paths(self, paths: list[str]) -> None:
        for path in paths:
            if path in self.files:
                continue
            ok, reason = validate_pdf_integrity(path)
            if not ok:
                show_error(self, "Cannot Add File", f"'{Path(path).name}': {reason}")
                continue
            self.files.append(path)
            self.page_expressions[path] = "all"
        self._refresh_table()

    def remove_selected(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            if 0 <= r < len(self.files):
                del self.files[r]
        self._refresh_table()

    def select_all(self) -> None:
        self.table.selectAll()

    def clear_all(self) -> None:
        self.files.clear()
        self.page_expressions.clear()
        self._refresh_table()

    def _move(self, delta: int) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if len(rows) != 1:
            return
        row = rows[0]
        new_row = max(0, min(row + delta, len(self.files) - 1))
        if new_row == row:
            return
        self.files[row], self.files[new_row] = self.files[new_row], self.files[row]
        self._refresh_table()
        self.table.selectRow(new_row)

    def _refresh_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.files))
        for row, path in enumerate(self.files):
            name_item = QTableWidgetItem(Path(path).name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)
            try:
                pages = get_page_count(path)
            except ValidationError:
                pages = 0
            page_item = QTableWidgetItem(str(pages))
            page_item.setFlags(page_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, page_item)
            size_item = QTableWidgetItem(human_size(Path(path).stat().st_size))
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, size_item)
            self.table.setItem(row, 3, QTableWidgetItem(self.page_expressions.get(path, "all")))
        self.table.blockSignals(False)

    def _on_item_changed(self, item) -> None:
        if item.column() == 3 and 0 <= item.row() < len(self.files):
            self.page_expressions[self.files[item.row()]] = item.text().strip() or "all"

    def _on_row_activated(self, row: int, column: int) -> None:
        if 0 <= row < len(self.files):
            try:
                self.preview.load_pdf(self.files[row])
            except ValidationError as exc:
                show_error(self, "Cannot Preview", str(exc))

    def _browse_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Merged PDF As", str(Path(self.output_dir) / self.edit_output_name.text()), "PDF Files (*.pdf)")
        if path:
            self.output_dir = str(Path(path).parent)
            self.edit_output_name.setText(Path(path).name)

    def process(self) -> None:
        self.merge_all()

    def merge_all(self) -> None:
        if not self.files:
            QMessageBox.information(self, "No Files", "Add at least two PDF files to merge.")
            return
        output_name = self.edit_output_name.text().strip() or "Merged.pdf"
        if not output_name.lower().endswith(".pdf"):
            output_name += ".pdf"
        output_path = Path(self.output_dir) / output_name

        items = [MergeItem(f, self.page_expressions.get(f, "all")) for f in self.files]
        try:
            result = merge_pdfs(items, output_path)
        except ValidationError as exc:
            show_error(self, "Merge Failed", str(exc))
            return

        log_operation(logger, operation="merge", output_file=str(output_path), pages=result.total_pages, result="success")
        if self.ctx.config.settings.enable_activity_register:
            from datetime import datetime

            self.ctx.database.add_audit_entry(
                AuditEntry(
                    timestamp=datetime.now().isoformat(),
                    operator=self.ctx.operator,
                    operation="Merge PDF",
                    source_document=", ".join(Path(f).name for f in self.files),
                    output_document=str(output_path),
                    pages_processed=str(result.total_pages),
                    template_used="",
                    result="Success",
                )
            )
        QMessageBox.information(self, "Merge Complete", f"Merged {result.source_count} files ({result.total_pages} pages) into:\n{output_path}")
        if self.ctx.config.settings.open_output_folder_after_completion:
            self._open_folder(str(output_path.parent))

    @staticmethod
    def _open_folder(folder: str) -> None:
        import os
        import subprocess
        import sys

        try:
            if sys.platform == "win32":
                os.startfile(folder)  # noqa: S606
            else:
                subprocess.Popen(["xdg-open", folder])
        except OSError:
            pass
