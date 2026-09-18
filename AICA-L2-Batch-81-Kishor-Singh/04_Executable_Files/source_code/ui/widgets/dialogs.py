"""Shared dialogs: pre-batch confirmation, progress + cancel, and the post-batch report.

Centralising these means every tab (Sign, Convert, Merge, Split, Organize,
Workflow) gets identical, predictable batch UX for free.
"""
from __future__ import annotations

import csv

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from models.enums import JobStatus
from models.job import BatchResult


class BatchConfirmationDialog(QDialog):
    """The "Documents selected: 47 / Signing Rule: Last Page / ... / SIGN ALL" screen.

    Shown immediately before any bulk operation runs, so a mistake in the
    configuration is caught before 50-100 files are touched.
    """

    def __init__(self, title: str, summary_lines: list[str], action_label: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        heading = QLabel(title)
        heading.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(heading)

        for line in summary_lines:
            lbl = QLabel(line)
            lbl.setWordWrap(True)
            layout.addWidget(lbl)

        button_row = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("SecondaryButton")
        self.btn_preview = QPushButton("Preview")
        self.btn_preview.setObjectName("SecondaryButton")
        self.btn_confirm = QPushButton(action_label)
        button_row.addWidget(self.btn_cancel)
        button_row.addWidget(self.btn_preview)
        button_row.addStretch(1)
        button_row.addWidget(self.btn_confirm)
        layout.addLayout(button_row)

        self.preview_requested = False
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_confirm.clicked.connect(self.accept)
        self.btn_preview.clicked.connect(self._on_preview)

    def _on_preview(self) -> None:
        self.preview_requested = True
        self.reject()


class ProgressDialog(QDialog):
    """Live progress with per-file status, a cancel button, and no frozen UI."""

    def __init__(self, title: str = "Processing...", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self.setModal(True)

        layout = QVBoxLayout(self)
        self.lbl_current = QLabel("Starting...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.lbl_counts = QLabel("Completed: 0   Pending: 0   Failed: 0")
        self.btn_cancel = QPushButton("Cancel Processing")
        self.btn_cancel.setObjectName("DangerButton")

        layout.addWidget(self.lbl_current)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.lbl_counts)
        layout.addWidget(self.btn_cancel)

        self._succeeded = 0
        self._failed = 0

    def update_progress(self, completed: int, total: int, current_filename: str) -> None:
        pct = int((completed / total) * 100) if total else 0
        self.progress_bar.setValue(pct)
        remaining = total - completed
        self.lbl_current.setText(f"Processing: {current_filename}  ({completed}/{total})")
        self.lbl_counts.setText(
            f"Completed: {completed}   Remaining: {remaining}   Succeeded: {self._succeeded}   Failed: {self._failed}"
        )

    def note_job_result(self, status: JobStatus) -> None:
        if status == JobStatus.SUCCESS:
            self._succeeded += 1
        elif status == JobStatus.FAILED:
            self._failed += 1


class ReportDialog(QDialog):
    """Post-batch summary: totals, per-file failure reasons, CSV export, retry."""

    def __init__(self, result: BatchResult, operation_name: str = "Processing", parent=None):
        super().__init__(parent)
        self.result = result
        self.setWindowTitle(f"{operation_name} Report")
        self.setMinimumSize(700, 420)
        layout = QVBoxLayout(self)

        summary = QLabel(
            f"<b>Total Documents:</b> {result.total} &nbsp;&nbsp; "
            f"<b>Successful:</b> {result.succeeded} &nbsp;&nbsp; "
            f"<b>Failed:</b> {result.failed} &nbsp;&nbsp; "
            f"<b>Skipped:</b> {result.skipped}<br/>"
            f"<b>Output Folder:</b> {result.output_folder}"
        )
        summary.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(summary)

        table = QTableWidget(len(result.jobs), 4)
        table.setHorizontalHeaderLabels(["File Name", "Status", "Output File", "Error / Notes"])
        table.horizontalHeader().setStretchLastSection(True)
        for row, job in enumerate(result.jobs):
            table.setItem(row, 0, QTableWidgetItem(job.file_name))
            table.setItem(row, 1, QTableWidgetItem(job.status.value))
            table.setItem(row, 2, QTableWidgetItem(job.output_file_name))
            table.setItem(row, 3, QTableWidgetItem(job.error_message))
        table.resizeColumnsToContents()
        layout.addWidget(table)

        button_row = QHBoxLayout()
        self.btn_export_csv = QPushButton("Export Report to CSV")
        self.btn_export_csv.setObjectName("SecondaryButton")
        self.btn_retry_failed = QPushButton("Retry Failed")
        self.btn_close = QPushButton("Close")
        button_row.addWidget(self.btn_export_csv)
        button_row.addWidget(self.btn_retry_failed)
        button_row.addStretch(1)
        button_row.addWidget(self.btn_close)
        layout.addLayout(button_row)

        self.btn_retry_failed.setEnabled(result.failed > 0)
        self.btn_export_csv.clicked.connect(self._export_csv)
        self.btn_close.clicked.connect(self.accept)

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Report", "processing_report.csv", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["File Name", "Status", "Output File", "Error / Notes"])
            for job in self.result.jobs:
                writer.writerow([job.file_name, job.status.value, job.output_file_name, job.error_message])
        QMessageBox.information(self, "Export Complete", f"Report saved to:\n{path}")


class PasswordPromptDialog(QDialog):
    """Prompts for a PDF's open password when an encrypted file is added to a batch."""

    def __init__(self, file_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password Required")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"'{file_name}' is password protected.\nEnter the password to continue:"))
        self.edit_password = QLineEdit()
        self.edit_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.edit_password)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def password(self) -> str:
        return self.edit_password.text()


def show_error(parent, title: str, message: str) -> None:
    """Non-technical error dialog -- every engine raises ValidationError with
    a message already written for a non-programmer, so this is a thin wrapper."""
    QMessageBox.critical(parent, title, message)
