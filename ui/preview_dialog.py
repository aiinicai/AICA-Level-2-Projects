"""
Certificate Inspector & PDF Preview Dialog for TDS & TCS Certificate PDF Auto-Renamer.
Renders high-resolution PDF page rendering and structured metadata side-by-side.
"""

from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QPlainTextEdit,
    QScrollArea,
    QFormLayout,
    QGroupBox,
    QMessageBox,
)
from PyQt6.QtGui import QPixmap, QImage

import pymupdf as fitz
from core.models import CertificateData


class CertificatePreviewDialog(QDialog):
    """Dialog allowing users to inspect extracted fields, render PDF page, and adjust names."""

    def __init__(self, cert: CertificateData, parent=None):
        super().__init__(parent)
        self.cert = cert
        self.setWindowTitle(f"Certificate Inspector - {cert.original_filename}")
        self.resize(980, 680)
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Left side: PDF Visual Renderer / Raw Text Tabs
        tabs = QTabWidget()
        self.visual_tab = self._create_visual_tab()
        self.text_tab = self._create_text_tab()
        tabs.addTab(self.visual_tab, "Document Preview")
        tabs.addTab(self.text_tab, "Extracted Text")
        main_layout.addWidget(tabs, 60)

        # Right side: Metadata Inspector & Name Editor
        right_panel = QVBoxLayout()
        meta_group = QGroupBox("Extracted Certificate Details")
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Fields
        self.act_label = QLabel(f"<b>{self.cert.act}</b>")
        self.form_label = QLabel(f"<b>{self.cert.form_type}</b> ({self.cert.category})")
        self.deductee_edit = QLineEdit(self.cert.deductee_name)
        self.pan_label = QLabel(self.cert.deductee_pan or "N/A")
        self.tan_label = QLabel(self.cert.deductor_tan or "N/A")
        self.fy_label = QLabel(self.cert.financial_year or "N/A")
        self.ay_label = QLabel(self.cert.assessment_year or "N/A")
        self.q_label = QLabel(self.cert.quarter or "N/A")
        self.cert_no_label = QLabel(self.cert.certificate_no or "N/A")
        self.status_label = QLabel(f"<b>{self.cert.status.value}</b>")

        # Proposed Filename (Editable)
        self.proposed_edit = QLineEdit(self.cert.proposed_filename)

        form_layout.addRow("Governing Act:", self.act_label)
        form_layout.addRow("Form Type:", self.form_label)
        form_layout.addRow("Deductee Name:", self.deductee_edit)
        form_layout.addRow("Deductee PAN:", self.pan_label)
        form_layout.addRow("Deductor TAN:", self.tan_label)
        form_layout.addRow("Financial Year:", self.fy_label)
        form_layout.addRow("Assessment Year:", self.ay_label)
        form_layout.addRow("Quarter:", self.q_label)
        form_layout.addRow("Certificate No:", self.cert_no_label)
        form_layout.addRow("Current Status:", self.status_label)
        form_layout.addRow("Proposed Filename:", self.proposed_edit)

        meta_group.setLayout(form_layout)
        right_panel.addWidget(meta_group)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Overrides")
        save_btn.setObjectName("PrimaryBtn")
        save_btn.clicked.connect(self._save_overrides)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(close_btn)
        right_panel.addLayout(btn_layout)

        main_layout.addLayout(right_panel, 40)

    def _create_visual_tab(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pdf_path = Path(self.cert.file_path)
        if pdf_path.exists():
            try:
                doc = fitz.open(str(pdf_path))
                if len(doc) > 0:
                    page = doc[0]
                    pix = page.get_pixmap(dpi=130)
                    img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(img)
                    img_label.setPixmap(pixmap)
                doc.close()
            except Exception as e:
                img_label.setText(f"Could not render PDF preview:\n{e}")
        else:
            img_label.setText("PDF file not found on disk.")

        scroll.setWidget(img_label)
        return scroll

    def _create_text_tab(self) -> QPlainTextEdit:
        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setObjectName("LogView")
        text_edit.setPlainText(self.cert.raw_text_snippet or "No text extracted.")
        return text_edit

    def _save_overrides(self):
        new_name = self.deductee_edit.text().strip().upper()
        new_filename = self.proposed_edit.text().strip()

        if not new_filename.lower().endswith(".pdf"):
            new_filename += ".pdf"

        self.cert.deductee_name = new_name
        self.cert.proposed_filename = new_filename
        QMessageBox.information(self, "Saved", "Certificate overrides applied successfully.")
        self.accept()
