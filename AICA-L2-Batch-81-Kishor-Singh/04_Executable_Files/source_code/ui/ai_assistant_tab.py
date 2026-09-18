"""AI Assistant tab: classification, summarization, structured extraction, and Ask Document.

Every action here is triggered explicitly by a button click -- nothing runs
automatically, and every document sent to a cloud provider is exactly what
the user selected, never anything more.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.ai_provider import AIProviderError
from core.document_intelligence import DocumentChunk, ask_document, classify_document, summarize_document
from core.extraction_engine import ExtractionKind, extract_structured, verify_invoice_totals
from core.ocr_engine import extract_text_via_ocr, is_tesseract_available, page_has_extractable_text
from core.pdf_engine import open_pdf, validate_pdf_integrity
from ui.ai_helper import get_configured_provider, is_ai_ready
from ui.app_context import AppContext
from ui.widgets.dialogs import show_error
from utils.validation import ValidationError


def _extract_document_text(path: str, tesseract_path: str = "") -> str:
    """Prefer the real text layer; fall back to OCR only for pages that need it."""
    with open_pdf(path) as doc:
        needs_ocr = any(not page_has_extractable_text(doc, i) for i in range(doc.page_count))
    if needs_ocr and is_tesseract_available(tesseract_path):
        return extract_text_via_ocr(path, tesseract_path=tesseract_path)
    with open_pdf(path) as doc:
        return "\n\n".join(doc[i].get_text() for i in range(doc.page_count))


def _document_chunks(path: str, tesseract_path: str = "") -> list[DocumentChunk]:
    name = Path(path).name
    with open_pdf(path) as doc:
        chunks = []
        for i in range(doc.page_count):
            if page_has_extractable_text(doc, i):
                text = doc[i].get_text()
            elif is_tesseract_available(tesseract_path):
                text = extract_text_via_ocr(path, tesseract_path=tesseract_path)
            else:
                text = ""
            chunks.append(DocumentChunk(document_name=name, page_number=i + 1, text=text))
        return chunks


class AIAssistantTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.loaded_documents: list[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        self.lbl_status = QLabel()
        self.lbl_status.setWordWrap(True)
        root.addWidget(self.lbl_status)
        self._refresh_status()

        doc_row = QHBoxLayout()
        self.btn_add_docs = QPushButton("Add Document(s)")
        self.btn_clear_docs = QPushButton("Clear")
        self.btn_clear_docs.setObjectName("SecondaryButton")
        doc_row.addWidget(self.btn_add_docs)
        doc_row.addWidget(self.btn_clear_docs)
        doc_row.addStretch(1)
        root.addLayout(doc_row)

        self.doc_list = QListWidget()
        self.doc_list.setMaximumHeight(90)
        root.addWidget(self.doc_list)

        self.sub_tabs = QTabWidget()
        root.addWidget(self.sub_tabs, 1)
        self.sub_tabs.addTab(self._build_classify_tab(), "Classify & Summarize")
        self.sub_tabs.addTab(self._build_extract_tab(), "Extract Data")
        self.sub_tabs.addTab(self._build_ask_tab(), "Ask Document")

        self.btn_add_docs.clicked.connect(self.add_documents)
        self.btn_clear_docs.clicked.connect(self.clear_documents)

    def _refresh_status(self) -> None:
        if is_ai_ready(self.ctx):
            self.lbl_status.setText(f"AI provider: {self.ctx.config.settings.ai_provider} (configured in Settings -> AI Assistant).")
            self.lbl_status.setStyleSheet("color: #1f9d55;")
        else:
            self.lbl_status.setText(
                f"AI provider '{self.ctx.config.settings.ai_provider}' is not configured. "
                "Go to Settings -> AI Assistant to add an API key (or select Ollama for a fully local, offline model)."
            )
            self.lbl_status.setStyleSheet("color: #d64545; font-weight: 600;")

    # ------------------------------------------------------------- documents
    def add_documents(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Documents", "", "PDF Files (*.pdf)")
        for path in paths:
            ok, reason = validate_pdf_integrity(path)
            if not ok:
                show_error(self, "Cannot Add File", f"'{Path(path).name}': {reason}")
                continue
            if path not in self.loaded_documents:
                self.loaded_documents.append(path)
                self.doc_list.addItem(QListWidgetItem(Path(path).name))
        self._populate_document_combos()

    def clear_documents(self) -> None:
        self.loaded_documents.clear()
        self.doc_list.clear()
        self._populate_document_combos()

    def _populate_document_combos(self) -> None:
        for combo in (self.combo_classify_doc, self.combo_extract_doc):
            current = combo.currentText()
            combo.clear()
            combo.addItems([Path(p).name for p in self.loaded_documents])
            if current:
                idx = combo.findText(current)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

    def _path_for_name(self, name: str) -> str | None:
        for p in self.loaded_documents:
            if Path(p).name == name:
                return p
        return None

    # ------------------------------------------------------- classify/summarize
    def _build_classify_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        row = QHBoxLayout()
        self.combo_classify_doc = QComboBox()
        self.btn_classify = QPushButton("Classify Document")
        self.btn_summarize = QPushButton("Summarize Document")
        row.addWidget(QLabel("Document:"))
        row.addWidget(self.combo_classify_doc, 1)
        row.addWidget(self.btn_classify)
        row.addWidget(self.btn_summarize)
        layout.addLayout(row)

        self.classify_output = QPlainTextEdit()
        self.classify_output.setReadOnly(True)
        layout.addWidget(self.classify_output, 1)

        self.btn_classify.clicked.connect(self.run_classify)
        self.btn_summarize.clicked.connect(self.run_summarize)
        return widget

    def _selected_text(self, combo: QComboBox) -> tuple[str, str] | None:
        name = combo.currentText()
        path = self._path_for_name(name) if name else None
        if not path:
            QMessageBox.information(self, "Select a Document", "Add and select a document first.")
            return None
        try:
            text = _extract_document_text(path, self.ctx.config.settings.tesseract_path)
        except ValidationError as exc:
            show_error(self, "Could Not Read Document", str(exc))
            return None
        if not text.strip():
            show_error(self, "No Text Found", "This document has no extractable text and Tesseract OCR is not available to read it.")
            return None
        return path, text

    def run_classify(self) -> None:
        selected = self._selected_text(self.combo_classify_doc)
        if not selected:
            return
        _, text = selected
        try:
            provider = get_configured_provider(self.ctx)
            result = classify_document(text, provider)
        except (AIProviderError, ValidationError) as exc:
            show_error(self, "Classification Failed", str(exc))
            return
        self.classify_output.setPlainText(
            f"Category: {result.category.value}\nConfidence: {result.confidence:.0f}%\nRationale: {result.rationale}"
        )

    def run_summarize(self) -> None:
        selected = self._selected_text(self.combo_classify_doc)
        if not selected:
            return
        _, text = selected
        try:
            provider = get_configured_provider(self.ctx)
            result = summarize_document(text, provider)
        except (AIProviderError, ValidationError) as exc:
            show_error(self, "Summarization Failed", str(exc))
            return
        lines = [
            f"Summary: {result.summary_text}", "",
            f"Parties: {', '.join(result.parties) or '(none found)'}",
            f"Key Dates: {', '.join(result.key_dates) or '(none found)'}",
            f"Amounts: {', '.join(result.amounts) or '(none found)'}",
            f"Issues: {', '.join(result.issues) or '(none found)'}",
            f"Missing Information: {', '.join(result.missing_information) or '(none noted)'}",
            f"Proposed Next Actions: {', '.join(result.proposed_next_actions) or '(none noted)'}",
        ]
        if result.possible_deadline:
            lines.append("")
            lines.append(
                f"⚠ Possible deadline mentioned: {result.possible_deadline} "
                "-- REVIEW MANUALLY before relying on this date; nothing was auto-scheduled."
            )
        self.classify_output.setPlainText("\n".join(lines))

    # ------------------------------------------------------------------ extract
    def _build_extract_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        row = QHBoxLayout()
        self.combo_extract_doc = QComboBox()
        self.combo_extract_kind = QComboBox()
        self.combo_extract_kind.addItems([k.value for k in ExtractionKind])
        self.btn_extract = QPushButton("Extract")
        row.addWidget(QLabel("Document:"))
        row.addWidget(self.combo_extract_doc, 1)
        row.addWidget(QLabel("Type:"))
        row.addWidget(self.combo_extract_kind)
        row.addWidget(self.btn_extract)
        layout.addLayout(row)

        self.extract_table = QTableWidget(0, 2)
        self.extract_table.setHorizontalHeaderLabels(["Field", "Value"])
        self.extract_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.extract_table, 1)

        self.extract_warnings = QLabel("")
        self.extract_warnings.setWordWrap(True)
        self.extract_warnings.setStyleSheet("color: #d64545;")
        layout.addWidget(self.extract_warnings)

        export_row = QHBoxLayout()
        self.btn_export_extract = QPushButton("Export to JSON")
        self.btn_export_extract.setObjectName("SecondaryButton")
        export_row.addWidget(self.btn_export_extract)
        export_row.addStretch(1)
        layout.addLayout(export_row)

        self.btn_extract.clicked.connect(self.run_extract)
        self.btn_export_extract.clicked.connect(self.export_extract)
        self._last_extraction = None
        return widget

    def run_extract(self) -> None:
        selected = self._selected_text(self.combo_extract_doc)
        if not selected:
            return
        _, text = selected
        kind = ExtractionKind(self.combo_extract_kind.currentText())
        try:
            provider = get_configured_provider(self.ctx)
            outcome = extract_structured(text, kind, provider)
        except (AIProviderError, ValidationError) as exc:
            show_error(self, "Extraction Failed", str(exc))
            return

        self._last_extraction = outcome
        data = outcome.model.model_dump()
        rows = [(k, v) for k, v in data.items() if not isinstance(v, list)]
        self.extract_table.setRowCount(len(rows))
        for i, (key, value) in enumerate(rows):
            key_item = QTableWidgetItem(key)
            value_item = QTableWidgetItem("(missing -- please review)" if value is None else str(value))
            if value is None:
                value_item.setForeground(QColor("#d64545"))
            self.extract_table.setItem(i, 0, key_item)
            self.extract_table.setItem(i, 1, value_item)

        warnings = []
        if kind == ExtractionKind.INVOICE:
            warnings = verify_invoice_totals(outcome.model)
        if outcome.missing_fields:
            warnings.append(f"{len(outcome.missing_fields)} field(s) could not be found and need manual review.")
        self.extract_warnings.setText("\n".join(warnings))

    def export_extract(self) -> None:
        if not self._last_extraction:
            QMessageBox.information(self, "Nothing to Export", "Run an extraction first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Extraction", "extraction.json", "JSON Files (*.json)")
        if not path:
            return
        Path(path).write_text(self._last_extraction.model.model_dump_json(indent=2), encoding="utf-8")
        QMessageBox.information(self, "Exported", f"Saved to:\n{path}")

    # -------------------------------------------------------------- ask document
    def _build_ask_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Ask a question across all documents added above:"))
        row = QHBoxLayout()
        self.edit_question = QLineEdit()
        self.edit_question.setPlaceholderText("e.g. What is the demand amount in the GST notice?")
        self.btn_ask = QPushButton("Ask")
        row.addWidget(self.edit_question, 1)
        row.addWidget(self.btn_ask)
        layout.addLayout(row)

        self.ask_answer = QPlainTextEdit()
        self.ask_answer.setReadOnly(True)
        layout.addWidget(self.ask_answer, 1)

        layout.addWidget(QLabel("Citations:"))
        self.citations_list = QListWidget()
        layout.addWidget(self.citations_list)

        self.btn_ask.clicked.connect(self.run_ask)
        return widget

    def run_ask(self) -> None:
        question = self.edit_question.text().strip()
        if not question:
            return
        if not self.loaded_documents:
            QMessageBox.information(self, "No Documents", "Add at least one document first.")
            return
        try:
            chunks: list[DocumentChunk] = []
            for path in self.loaded_documents:
                chunks.extend(_document_chunks(path, self.ctx.config.settings.tesseract_path))
            provider = get_configured_provider(self.ctx)
            result = ask_document(question, chunks, provider)
        except (AIProviderError, ValidationError) as exc:
            show_error(self, "Ask Document Failed", str(exc))
            return

        prefix = "⚠ The AI is not confident in this answer:\n\n" if result.is_uncertain else ""
        self.ask_answer.setPlainText(prefix + result.answer)
        self.citations_list.clear()
        for c in result.citations:
            self.citations_list.addItem(QListWidgetItem(f"{c.document_name}, page {c.page_number}: \"{c.excerpt}\""))
