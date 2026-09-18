"""Integrity / QR tab: stamp a document ID + QR, register the final hash, and verify later.

This is a LOCAL registry (this computer's SQLite database), not a public
verification service -- the tab makes that limitation explicit rather than
implying a scanned QR proves anything to a third party.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.integrity_engine import register_final_hash, stamp_document_id, verify_file
from models.enums import PositionPreset
from ui.app_context import AppContext
from ui.widgets.dialogs import show_error
from utils.validation import ValidationError


class IntegrityTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        notice = QLabel(
            "This registry lives only on this computer's local database. A scanned QR code or Doc "
            "ID proves nothing to anyone else unless they check it against this same database -- it "
            "is a local integrity check, not a public verification service."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("color: #6b7280; font-size: 11px;")
        root.addWidget(notice)

        self.sub_tabs = QTabWidget()
        root.addWidget(self.sub_tabs, 1)
        self.sub_tabs.addTab(self._build_stamp_tab(), "Stamp Document")
        self.sub_tabs.addTab(self._build_verify_tab(), "Verify Document")
        self.sub_tabs.addTab(self._build_registry_tab(), "Local Registry")

    def process(self) -> None:
        if self.sub_tabs.currentIndex() == 0:
            self.stamp_document()
        elif self.sub_tabs.currentIndex() == 1:
            self.verify_document()

    # --------------------------------------------------------------- stamp
    def _build_stamp_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(
            "Stamp this FIRST, before any further processing (OCR, watermarking, signing). "
            "Register the final hash last, after every other step is complete."
        ))
        form = QFormLayout()
        file_row = QHBoxLayout()
        self.edit_stamp_source = QLineEdit()
        btn_browse = QPushButton("Browse...")
        btn_browse.setObjectName("SecondaryButton")
        btn_browse.clicked.connect(self._browse_stamp_source)
        file_row.addWidget(self.edit_stamp_source, 1)
        file_row.addWidget(btn_browse)
        form.addRow("Source PDF:", file_row)

        self.combo_stamp_position = QComboBox()
        self.combo_stamp_position.addItems([
            PositionPreset.BOTTOM_LEFT.value, PositionPreset.BOTTOM_RIGHT.value,
            PositionPreset.TOP_LEFT.value, PositionPreset.TOP_RIGHT.value,
        ])
        form.addRow("QR position:", self.combo_stamp_position)

        self.edit_stamp_pages = QLineEdit("last")
        form.addRow("Pages to stamp:", self.edit_stamp_pages)
        layout.addLayout(form)

        self.btn_stamp = QPushButton("STAMP DOCUMENT ID + QR")
        self.btn_stamp.setMinimumHeight(38)
        layout.addWidget(self.btn_stamp)

        register_group = QGroupBox("Step 2: Register Final Hash (after all other processing is done)")
        register_form = QFormLayout(register_group)
        self.edit_final_id = QLineEdit()
        self.edit_final_id.setPlaceholderText("Doc ID from the stamp step, e.g. 7D43AFC9C37B")
        register_form.addRow("Document ID:", self.edit_final_id)
        final_row = QHBoxLayout()
        self.edit_final_path = QLineEdit()
        btn_browse_final = QPushButton("Browse...")
        btn_browse_final.setObjectName("SecondaryButton")
        btn_browse_final.clicked.connect(self._browse_final_file)
        final_row.addWidget(self.edit_final_path, 1)
        final_row.addWidget(btn_browse_final)
        register_form.addRow("Final processed file:", final_row)
        layout.addWidget(register_group)

        self.btn_register = QPushButton("REGISTER FINAL HASH")
        layout.addWidget(self.btn_register)
        layout.addStretch(1)

        self.btn_stamp.clicked.connect(self.stamp_document)
        self.btn_register.clicked.connect(self.register_hash)
        return widget

    def _browse_stamp_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select PDF to Stamp", "", "PDF Files (*.pdf)")
        if path:
            self.edit_stamp_source.setText(path)

    def _browse_final_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Final Processed File", "", "PDF Files (*.pdf)")
        if path:
            self.edit_final_path.setText(path)

    def stamp_document(self) -> None:
        source = self.edit_stamp_source.text().strip()
        if not source:
            QMessageBox.information(self, "Select a File", "Choose a PDF to stamp first.")
            return
        default_out = str(Path(source).with_name(f"{Path(source).stem}_Stamped.pdf"))
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Stamped PDF As", default_out, "PDF Files (*.pdf)")
        if not out_path:
            return
        try:
            result = stamp_document_id(
                source, out_path,
                position=PositionPreset(self.combo_stamp_position.currentText()),
                page_rule_expression=self.edit_stamp_pages.text().strip() or "last",
            )
        except ValidationError as exc:
            show_error(self, "Stamping Failed", str(exc))
            return
        self.edit_final_id.setText(result.document_id)
        self.edit_final_path.setText(out_path)
        QMessageBox.information(
            self, "Stamped",
            f"Document ID: {result.document_id}\nSaved to: {out_path}\n\n"
            "Continue any further processing (OCR/watermark/signing) on this file, then come back "
            "and click REGISTER FINAL HASH once it is truly final.",
        )

    def register_hash(self) -> None:
        doc_id = self.edit_final_id.text().strip()
        final_path = self.edit_final_path.text().strip()
        if not doc_id or not final_path:
            QMessageBox.information(self, "Missing Information", "Enter the Document ID and select the final file.")
            return
        try:
            sha256 = register_final_hash(self.ctx.database, doc_id, final_path, operator=self.ctx.operator)
        except (ValidationError, OSError) as exc:
            show_error(self, "Registration Failed", str(exc))
            return
        QMessageBox.information(self, "Registered", f"Registered {doc_id} with hash:\n{sha256}")
        self._refresh_registry()

    # -------------------------------------------------------------- verify
    def _build_verify_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        row = QHBoxLayout()
        self.edit_verify_path = QLineEdit()
        btn_browse = QPushButton("Browse...")
        btn_browse.setObjectName("SecondaryButton")
        btn_browse.clicked.connect(self._browse_verify_file)
        row.addWidget(self.edit_verify_path, 1)
        row.addWidget(btn_browse)
        layout.addLayout(row)

        self.btn_verify = QPushButton("VERIFY DOCUMENT")
        self.btn_verify.setMinimumHeight(38)
        layout.addWidget(self.btn_verify)

        self.lbl_verify_result = QLabel("")
        self.lbl_verify_result.setWordWrap(True)
        self.lbl_verify_result.setStyleSheet("font-size: 13px; padding: 10px;")
        layout.addWidget(self.lbl_verify_result)
        layout.addStretch(1)

        self.btn_verify.clicked.connect(self.verify_document)
        return widget

    def _browse_verify_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select PDF to Verify", "", "PDF Files (*.pdf)")
        if path:
            self.edit_verify_path.setText(path)

    def verify_document(self) -> None:
        path = self.edit_verify_path.text().strip()
        if not path:
            QMessageBox.information(self, "Select a File", "Choose a PDF to verify first.")
            return
        try:
            result = verify_file(path, self.ctx.database)
        except (ValidationError, OSError) as exc:
            show_error(self, "Verification Failed", str(exc))
            return

        if result.document_id is None:
            self.lbl_verify_result.setStyleSheet("font-size: 13px; padding: 10px; color: #b58105;")
            self.lbl_verify_result.setText("No Document ID found in this file -- it was never stamped by this app.")
        elif not result.registered_locally:
            self.lbl_verify_result.setStyleSheet("font-size: 13px; padding: 10px; color: #b58105;")
            self.lbl_verify_result.setText(
                f"Document ID {result.document_id} was found, but is not registered in this computer's "
                "local registry. It may have been registered on a different computer/installation."
            )
        elif result.hash_matches:
            self.lbl_verify_result.setStyleSheet("font-size: 13px; padding: 10px; color: #1f9d55; font-weight: 600;")
            self.lbl_verify_result.setText(
                f"✓ MATCH -- Document ID {result.document_id} matches the registered hash.\n"
                f"Registered: {result.registered_at} (file: {result.registered_filename})"
            )
        else:
            self.lbl_verify_result.setStyleSheet("font-size: 13px; padding: 10px; color: #d64545; font-weight: 600;")
            self.lbl_verify_result.setText(
                f"✗ MISMATCH -- Document ID {result.document_id} was found, but this file's content does "
                f"NOT match what was registered on {result.registered_at}. The file may have been modified "
                "since it was finalized."
            )

    # ------------------------------------------------------------- registry
    def _build_registry_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.btn_refresh_registry = QPushButton("Refresh")
        self.btn_refresh_registry.setObjectName("SecondaryButton")
        layout.addWidget(self.btn_refresh_registry)
        self.registry_table = QTableWidget(0, 5)
        self.registry_table.setHorizontalHeaderLabels(["Document ID", "Filename", "SHA-256", "Operator", "Registered At"])
        self.registry_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.registry_table, 1)
        self.btn_refresh_registry.clicked.connect(self._refresh_registry)
        self._refresh_registry_widget = widget
        return widget

    def _refresh_registry(self) -> None:
        records = self.ctx.database.list_integrity_records()
        self.registry_table.setRowCount(len(records))
        for row, r in enumerate(records):
            self.registry_table.setItem(row, 0, QTableWidgetItem(r["document_id"]))
            self.registry_table.setItem(row, 1, QTableWidgetItem(r["filename"] or ""))
            self.registry_table.setItem(row, 2, QTableWidgetItem(r["sha256"][:16] + "..."))
            self.registry_table.setItem(row, 3, QTableWidgetItem(r["operator"] or ""))
            self.registry_table.setItem(row, 4, QTableWidgetItem(r["registered_at"]))
