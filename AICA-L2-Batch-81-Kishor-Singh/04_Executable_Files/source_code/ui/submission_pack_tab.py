"""Submission Pack Builder tab: assemble a client's documents into one
indexed, Bates-numbered PDF with a manifest, ready to submit or deliver."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.submission_pack_engine import SubmissionPackConfig, SubmissionPackItem, build_submission_pack
from ui.app_context import AppContext
from ui.widgets.dialogs import show_error
from utils.database import AuditEntry
from utils.logging_utils import get_logger, log_operation
from utils.validation import ValidationError

logger = get_logger("submission_pack_tab")


class ItemCategoryDialog(QDialog):
    def __init__(self, current_category: str, current_expression: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Document Details")
        layout = QFormLayout(self)
        self.edit_category = QLineEdit(current_category)
        self.edit_category.setPlaceholderText("e.g. Invoice, Bank Statement, Reply Letter")
        layout.addRow("Category / description:", self.edit_category)
        self.edit_pages = QLineEdit(current_expression)
        self.edit_pages.setPlaceholderText("all")
        layout.addRow("Pages to include:", self.edit_pages)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class SubmissionPackTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.items: list[SubmissionPackItem] = []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        details_group = QGroupBox("Engagement Details")
        form = QFormLayout(details_group)
        self.edit_client = QLineEdit()
        form.addRow("Client name:", self.edit_client)
        self.edit_engagement = QLineEdit()
        self.edit_engagement.setPlaceholderText("e.g. GST Notice Reply - DRC-01")
        form.addRow("Engagement:", self.edit_engagement)
        self.edit_fy = QLineEdit()
        self.edit_fy.setPlaceholderText("e.g. FY 2023-24")
        form.addRow("Financial year:", self.edit_fy)
        self.edit_bates_prefix = QLineEdit()
        self.edit_bates_prefix.setPlaceholderText("e.g. KSC- (leave blank to skip Bates numbering)")
        form.addRow("Bates prefix:", self.edit_bates_prefix)
        root.addWidget(details_group)

        checklist_group = QGroupBox("Document Checklist (optional -- flags anything missing)")
        checklist_layout = QVBoxLayout(checklist_group)
        self.edit_checklist = QPlainTextEdit()
        self.edit_checklist.setPlaceholderText("One expected document category per line, e.g.\nInvoice\nBank Statement\nAudit Report")
        self.edit_checklist.setMaximumHeight(80)
        checklist_layout.addWidget(self.edit_checklist)
        root.addWidget(checklist_group)

        cover_group = QGroupBox("Cover Letter (optional)")
        cover_layout = QVBoxLayout(cover_group)
        self.edit_cover_letter = QPlainTextEdit()
        self.edit_cover_letter.setPlaceholderText("Leave blank to skip a cover letter page.")
        self.edit_cover_letter.setMaximumHeight(100)
        cover_layout.addWidget(self.edit_cover_letter)
        root.addWidget(cover_group)

        docs_group = QGroupBox("Documents (in the order they'll appear)")
        docs_layout = QVBoxLayout(docs_group)
        toolbar = QHBoxLayout()
        self.btn_add = QPushButton("Add Document(s)")
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_remove.setObjectName("SecondaryButton")
        self.btn_up = QPushButton("Move Up")
        self.btn_up.setObjectName("SecondaryButton")
        self.btn_down = QPushButton("Move Down")
        self.btn_down.setObjectName("SecondaryButton")
        for b in (self.btn_add, self.btn_remove, self.btn_up, self.btn_down):
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        docs_layout.addLayout(toolbar)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Annexure", "File Name", "Category", "Pages"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellDoubleClicked.connect(self._edit_item_details)
        docs_layout.addWidget(self.table, 1)
        docs_layout.addWidget(QLabel("Double-click a row to set its category and page selection."))
        root.addWidget(docs_group, 1)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output folder:"))
        self.edit_output = QLineEdit(self.ctx.config.settings.default_output_folder)
        output_row.addWidget(self.edit_output, 1)
        btn_browse = QPushButton("Browse...")
        btn_browse.setObjectName("SecondaryButton")
        btn_browse.clicked.connect(self._browse_output)
        output_row.addWidget(btn_browse)
        root.addLayout(output_row)

        self.btn_build = QPushButton("BUILD SUBMISSION PACK")
        self.btn_build.setMinimumHeight(40)
        root.addWidget(self.btn_build)

        self.btn_add.clicked.connect(self.add_documents)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_up.clicked.connect(lambda: self._move(-1))
        self.btn_down.clicked.connect(lambda: self._move(1))
        self.btn_build.clicked.connect(self.build_pack)

    def add_documents(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Documents", "", "PDF Files (*.pdf)")
        for path in paths:
            self.items.append(SubmissionPackItem(file_path=path))
        self._refresh_table()

    def remove_selected(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            if 0 <= r < len(self.items):
                del self.items[r]
        self._refresh_table()

    def select_all(self) -> None:
        self.table.selectAll()

    def _move(self, delta: int) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if len(rows) != 1:
            return
        row = rows[0]
        new_row = max(0, min(row + delta, len(self.items) - 1))
        if new_row == row:
            return
        self.items[row], self.items[new_row] = self.items[new_row], self.items[row]
        self._refresh_table()
        self.table.selectRow(new_row)

    def _edit_item_details(self, row: int, _col: int) -> None:
        if not (0 <= row < len(self.items)):
            return
        item = self.items[row]
        dlg = ItemCategoryDialog(item.category, item.page_expression, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            item.category = dlg.edit_category.text().strip()
            item.page_expression = dlg.edit_pages.text().strip() or "all"
            self._refresh_table()

    def _refresh_table(self) -> None:
        self.table.setRowCount(len(self.items))
        for row, item in enumerate(self.items):
            self.table.setItem(row, 0, QTableWidgetItem(item.annexure_label or "(auto)"))
            self.table.setItem(row, 1, QTableWidgetItem(Path(item.file_path).name))
            self.table.setItem(row, 2, QTableWidgetItem(item.category))
            self.table.setItem(row, 3, QTableWidgetItem(item.page_expression))

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.edit_output.text())
        if folder:
            self.edit_output.setText(folder)

    def process(self) -> None:
        self.build_pack()

    def build_pack(self) -> None:
        if not self.items:
            QMessageBox.information(self, "No Documents", "Add at least one document to the submission pack.")
            return
        if not self.edit_client.text().strip():
            QMessageBox.information(self, "Client Name Required", "Enter the client name before building the pack.")
            return

        checklist = [line.strip() for line in self.edit_checklist.toPlainText().splitlines() if line.strip()]
        base_name = f"{self.edit_client.text().strip().replace(' ', '_')}_Submission_Pack"
        config = SubmissionPackConfig(
            client_name=self.edit_client.text().strip(),
            engagement=self.edit_engagement.text().strip() or "Submission",
            financial_year=self.edit_fy.text().strip(),
            items=list(self.items),
            checklist=checklist,
            cover_letter_text=self.edit_cover_letter.toPlainText().strip(),
            bates_prefix=self.edit_bates_prefix.text().strip(),
            output_base_name=base_name,
        )

        try:
            result = build_submission_pack(config, self.edit_output.text().strip() or self.ctx.config.settings.default_output_folder)
        except ValidationError as exc:
            show_error(self, "Build Failed", str(exc))
            return

        log_operation(logger, operation="submission_pack", output_file=result.combined_pdf_path, pages=result.total_pages, result="success")
        if self.ctx.config.settings.enable_activity_register:
            from datetime import datetime

            self.ctx.database.add_audit_entry(AuditEntry(
                timestamp=datetime.now().isoformat(), operator=self.ctx.operator, operation="Submission Pack Built",
                source_document=", ".join(Path(i.file_path).name for i in self.items),
                output_document=result.combined_pdf_path, pages_processed=str(result.total_pages),
                template_used=config.engagement, result="Success",
            ))

        message = (
            f"Combined PDF: {result.combined_pdf_path}\n"
            f"Manifest: {result.manifest_path}\n"
            f"ZIP package: {result.zip_path}\n"
            f"Total pages: {result.total_pages}"
        )
        if result.missing_from_checklist:
            message += "\n\n⚠ Missing from checklist: " + ", ".join(result.missing_from_checklist)
        QMessageBox.information(self, "Submission Pack Built", message)

        if self.ctx.config.settings.open_output_folder_after_completion:
            import os
            import subprocess
            import sys

            folder = str(Path(result.combined_pdf_path).parent)
            try:
                if sys.platform == "win32":
                    os.startfile(folder)  # noqa: S606
                else:
                    subprocess.Popen(["xdg-open", folder])
            except OSError:
                pass
