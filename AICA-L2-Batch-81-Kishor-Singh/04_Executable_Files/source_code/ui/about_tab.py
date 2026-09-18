"""About tab: branding, version, offline/security statement, signature disclaimer."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from config.app_config import APP_ICON_PATH, APP_NAME, APP_TAGLINE, APP_VERSION, ORGANIZATION_NAME, SIGNATURE_DISCLAIMER


class AboutTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        if APP_ICON_PATH.exists():
            icon_label = QLabel()
            pixmap = QPixmap(str(APP_ICON_PATH)).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pixmap)
            layout.addWidget(icon_label)

        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)

        tagline = QLabel(APP_TAGLINE)
        tagline.setStyleSheet("color: #2f6fed; font-weight: 600;")
        tagline.setWordWrap(True)
        layout.addWidget(tagline)

        layout.addWidget(QLabel(f"Version {APP_VERSION}"))
        layout.addWidget(QLabel(f"Provided by: {ORGANIZATION_NAME}"))

        offline = QLabel(
            "Every PDF operation (signing, merge, split, page organizing, watermarking, redaction, "
            "OCR, comparison) runs entirely on this computer -- no document is ever uploaded to any "
            "server. Temporary files created during processing are deleted automatically once each "
            "job finishes.\n\n"
            "The AI Assistant features (document classification, summarization and structured data "
            "extraction) are opt-in: they only activate once you configure a cloud AI provider in "
            "Settings, and the app clearly shows which provider is active whenever an AI feature is "
            "used. No document is sent to an AI provider unless you explicitly trigger that feature."
        )
        offline.setWordWrap(True)
        layout.addWidget(offline)

        disclaimer_title = QLabel("Visible Signature vs. Digital Signature")
        disclaimer_title.setStyleSheet("font-weight: 700; margin-top: 10px;")
        layout.addWidget(disclaimer_title)
        disclaimer = QLabel(SIGNATURE_DISCLAIMER)
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        credits = QLabel(
            "Built with PySide6, PyMuPDF, Pillow, pikepdf, pyHanko and pytesseract/Tesseract OCR. "
            "Word-to-PDF conversion uses Microsoft Word (COM automation) when available, with "
            "LibreOffice as an optional offline fallback. AI features support Anthropic, OpenAI, "
            "Google Gemini and local Ollama models, configured under Settings -> AI Assistant. "
            "API keys are stored using the Windows Credential Manager, never in plain text."
        )
        credits.setWordWrap(True)
        credits.setStyleSheet("color: #6b7280; margin-top: 10px;")
        layout.addWidget(credits)

        layout.addStretch(1)
