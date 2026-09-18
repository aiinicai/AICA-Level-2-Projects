"""Compare tab: text and rendered-page differences between two document versions."""
from __future__ import annotations

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from core.comparison_engine import ComparisonResult, compare_text, render_page_diff_image
from ui.app_context import AppContext
from ui.widgets.dialogs import show_error
from utils.validation import ValidationError


class CompareTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.path_a: str | None = None
        self.path_b: str | None = None
        self.result: ComparisonResult | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        pick_row = QHBoxLayout()
        self.edit_a = QLineEdit()
        self.edit_a.setPlaceholderText("Version A (original)...")
        btn_a = QPushButton("Browse...")
        btn_a.setObjectName("SecondaryButton")
        self.edit_b = QLineEdit()
        self.edit_b.setPlaceholderText("Version B (revised)...")
        btn_b = QPushButton("Browse...")
        btn_b.setObjectName("SecondaryButton")
        pick_row.addWidget(QLabel("A:"))
        pick_row.addWidget(self.edit_a, 1)
        pick_row.addWidget(btn_a)
        root.addLayout(pick_row)
        pick_row2 = QHBoxLayout()
        pick_row2.addWidget(QLabel("B:"))
        pick_row2.addWidget(self.edit_b, 1)
        pick_row2.addWidget(btn_b)
        root.addLayout(pick_row2)

        self.btn_compare = QPushButton("COMPARE DOCUMENTS")
        self.btn_compare.setMinimumHeight(36)
        root.addWidget(self.btn_compare)

        self.lbl_summary = QLabel("")
        root.addWidget(self.lbl_summary)

        splitter = QSplitter()
        self.page_list = QListWidget()
        self.page_list.setMaximumWidth(220)
        splitter.addWidget(self.page_list)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.text_diff_view = QPlainTextEdit()
        self.text_diff_view.setReadOnly(True)
        right_layout.addWidget(QLabel("Text differences (- removed / + added):"))
        right_layout.addWidget(self.text_diff_view, 1)
        self.image_diff_label = QLabel("Visual diff appears here (changed regions highlighted in red).")
        self.image_diff_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_diff_label.setMinimumHeight(300)
        self.image_diff_label.setStyleSheet("border: 1px solid #ccd2db; background: white;")
        right_layout.addWidget(self.image_diff_label, 1)
        splitter.addWidget(right)
        root.addWidget(splitter, 1)

        self.btn_export = QPushButton("Export Report")
        self.btn_export.setObjectName("SecondaryButton")
        root.addWidget(self.btn_export)

        btn_a.clicked.connect(lambda: self._browse(self.edit_a))
        btn_b.clicked.connect(lambda: self._browse(self.edit_b))
        self.btn_compare.clicked.connect(self.compare)
        self.page_list.currentRowChanged.connect(self._on_page_selected)
        self.btn_export.clicked.connect(self.export_report)

    def _browse(self, target: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if path:
            target.setText(path)

    def process(self) -> None:
        self.compare()

    def compare(self) -> None:
        self.path_a = self.edit_a.text().strip()
        self.path_b = self.edit_b.text().strip()
        if not self.path_a or not self.path_b:
            QMessageBox.information(self, "Select Both Files", "Choose both Version A and Version B to compare.")
            return
        try:
            self.result = compare_text(self.path_a, self.path_b)
        except ValidationError as exc:
            show_error(self, "Comparison Failed", str(exc))
            return

        if self.result.identical:
            self.lbl_summary.setText(f"Documents are identical ({self.result.document_a_pages} pages).")
        else:
            self.lbl_summary.setText(
                f"A: {self.result.document_a_pages} pages, B: {self.result.document_b_pages} pages -- "
                f"{len(self.result.pages_with_changes)} page(s) with changes."
            )

        self.page_list.clear()
        for diff in self.result.page_diffs:
            label = f"Page {diff.page_number} — {'unchanged' if diff.unchanged else 'CHANGED'}"
            item = QListWidgetItem(label)
            self.page_list.addItem(item)
        if self.page_list.count():
            self.page_list.setCurrentRow(0)

    def _on_page_selected(self, row: int) -> None:
        if not self.result or row < 0 or row >= len(self.result.page_diffs):
            return
        diff = self.result.page_diffs[row]
        lines = [f"- {line}" for line in diff.removed_lines] + [f"+ {line}" for line in diff.added_lines]
        self.text_diff_view.setPlainText("\n".join(lines) if lines else "(no text differences on this page)")

        try:
            png_bytes = render_page_diff_image(self.path_a, self.path_b, row)
            pixmap = QPixmap()
            pixmap.loadFromData(png_bytes, "PNG")
            self.image_diff_label.setPixmap(
                pixmap.scaledToWidth(self.image_diff_label.width() or 500, Qt.TransformationMode.SmoothTransformation)
            )
        except IndexError:
            self.image_diff_label.setText("This page does not exist in one of the two documents.")

    def export_report(self) -> None:
        if not self.result:
            QMessageBox.information(self, "Nothing to Export", "Run a comparison first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Comparison Report", "comparison_report.txt", "Text Files (*.txt)")
        if not path:
            return
        lines = [
            "Comparison Report",
            f"Document A: {self.path_a} ({self.result.document_a_pages} pages)",
            f"Document B: {self.path_b} ({self.result.document_b_pages} pages)",
            f"Pages with changes: {self.result.pages_with_changes or 'None'}",
            "",
        ]
        for diff in self.result.page_diffs:
            lines.append(f"--- Page {diff.page_number} ({'unchanged' if diff.unchanged else 'CHANGED'}) ---")
            for line in diff.removed_lines:
                lines.append(f"- {line}")
            for line in diff.added_lines:
                lines.append(f"+ {line}")
            lines.append("")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        QMessageBox.information(self, "Exported", f"Report saved to:\n{path}")
