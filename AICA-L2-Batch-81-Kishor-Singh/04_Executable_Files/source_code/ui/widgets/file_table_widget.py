"""The batch file table used on the Sign PDF tab.

Columns match the spec exactly: Sl. No., File Name, Folder, Pages, Selected
Pages, Signature Position, Status, Output File Name. Supports add/remove/
reorder, drag-and-drop of files/folders, and per-row status/colour updates
as a batch runs.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QAbstractItemView, QTableWidget, QTableWidgetItem

from models.enums import JobStatus
from models.job import SigningJob
from utils.file_utils import find_pdfs_in_folder

COLUMNS = [
    "Sl. No.",
    "File Name",
    "Folder",
    "Pages",
    "Selected Pages",
    "Signature Position",
    "Status",
    "Output File Name",
]

_STATUS_COLORS = {
    JobStatus.PENDING: QColor("#6b7280"),
    JobStatus.PROCESSING: QColor("#2f6fed"),
    JobStatus.SUCCESS: QColor("#1f9d55"),
    JobStatus.FAILED: QColor("#d64545"),
    JobStatus.SKIPPED: QColor("#b58105"),
    JobStatus.CANCELLED: QColor("#6b7280"),
}


class FileTableWidget(QTableWidget):
    """A drag-and-drop enabled table of :class:`SigningJob` rows."""

    files_added = Signal(list)  # list[str] of newly added file paths

    def __init__(self, parent=None):
        super().__init__(0, len(COLUMNS), parent)
        self.setHorizontalHeaderLabels(COLUMNS)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.horizontalHeader().setStretchLastSection(True)
        self.jobs: list[SigningJob] = []

    # ------------------------------------------------------------- drag/drop
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        paths: list[str] = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if not local:
                continue
            p = Path(local)
            if p.is_dir():
                paths.extend(str(f) for f in find_pdfs_in_folder(p))
            elif p.suffix.lower() == ".pdf":
                paths.append(str(p))
        if paths:
            self.files_added.emit(paths)
        event.acceptProposedAction()

    # --------------------------------------------------------------- content
    def set_jobs(self, jobs: list[SigningJob]) -> None:
        self.jobs = jobs
        self.refresh()

    def refresh(self) -> None:
        self.setRowCount(len(self.jobs))
        for row, job in enumerate(self.jobs):
            self._set_row(row, job)

    def _set_row(self, row: int, job: SigningJob) -> None:
        values = [
            str(row + 1),
            job.file_name,
            job.folder,
            str(job.total_pages) if job.total_pages else "-",
            job.selected_pages or "-",
            job.position_label or "-",
            job.status.value,
            job.output_file_name or "-",
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if col == 6:  # Status column
                item.setForeground(_STATUS_COLORS.get(job.status, QColor("black")))
            self.setItem(row, col, item)

    def update_job_row(self, job: SigningJob) -> None:
        try:
            row = self.jobs.index(job)
        except ValueError:
            return
        self._set_row(row, job)

    def selected_rows(self) -> list[int]:
        return sorted({idx.row() for idx in self.selectedIndexes()})

    def move_row(self, row: int, delta: int) -> int:
        """Move the job at ``row`` up/down by ``delta`` positions. Returns the new row index."""
        new_row = max(0, min(row + delta, len(self.jobs) - 1))
        if new_row == row:
            return row
        self.jobs[row], self.jobs[new_row] = self.jobs[new_row], self.jobs[row]
        self.refresh()
        return new_row
