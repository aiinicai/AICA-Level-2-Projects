"""Dashboard tab: quick actions, recent jobs, saved templates at a glance."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.app_config import APP_NAME, APP_TAGLINE, SIGNATURE_DISCLAIMER
from ui.app_context import AppContext


class _QuickActionCard(QWidget):
    clicked = Signal()

    def __init__(self, title: str, description: str, button_text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("DashboardCard")
        layout = QVBoxLayout(self)
        title_label = QLabel(title)
        title_label.setProperty("cardTitle", True)
        layout.addWidget(title_label)
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        button = QPushButton(button_text)
        button.clicked.connect(self.clicked.emit)
        layout.addWidget(button)
        layout.addStretch(1)


class DashboardTab(QWidget):
    navigate_requested = Signal(str)  # tab name to switch to

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        heading = QLabel(APP_NAME)
        heading.setStyleSheet("font-size: 20px; font-weight: 700;")
        root.addWidget(heading)
        tagline = QLabel(APP_TAGLINE)
        tagline.setStyleSheet("color: #2f6fed; font-size: 12px; font-weight: 600;")
        root.addWidget(tagline)
        disclaimer = QLabel(SIGNATURE_DISCLAIMER)
        disclaimer.setWordWrap(True)
        disclaimer.setStyleSheet("color: #6b7280; font-size: 11px;")
        root.addWidget(disclaimer)

        grid = QGridLayout()
        cards = [
            ("Sign PDFs", "Drag in PDFs, pick a saved signature, and sign 1 or 100 documents in one click.", "Go to Sign PDF", "Sign PDF"),
            ("Convert Word to PDF", "Convert single or bulk Word documents, optionally signing them immediately.", "Go to Word → PDF", "Word → PDF"),
            ("Merge PDFs", "Combine multiple PDFs, with optional per-file page ranges, into one document.", "Go to Merge PDF", "Merge PDF"),
            ("Split PDF", "Split by page, range, every N pages, equal parts, or remove specific pages.", "Go to Split PDF", "Split PDF"),
            ("OCR / Scan", "Make scanned PDFs searchable, entirely offline, with Tesseract OCR.", "Go to OCR / Scan", "OCR / Scan"),
            ("AI Assistant", "Classify, summarize, and extract structured data (invoices, GST/IT notices) with AI.", "Go to AI Assistant", "AI Assistant"),
            ("Submission Pack", "Assemble client documents into one indexed, Bates-numbered pack with a manifest.", "Go to Submission Pack", "Submission Pack"),
        ]
        for i, (title, desc, btn_text, tab_name) in enumerate(cards):
            card = _QuickActionCard(title, desc, btn_text)
            card.clicked.connect(lambda tab=tab_name: self.navigate_requested.emit(tab))
            grid.addWidget(card, i // 2, i % 2)
        root.addLayout(grid)

        lists_row = QHBoxLayout()

        recent_group = QGroupBox("Recent Jobs")
        recent_layout = QVBoxLayout(recent_group)
        self.recent_table = QTableWidget(0, 4)
        self.recent_table.setHorizontalHeaderLabels(["Operation", "Source", "Status", "Date"])
        self.recent_table.horizontalHeader().setStretchLastSection(True)
        recent_layout.addWidget(self.recent_table)
        lists_row.addWidget(recent_group)

        templates_group = QGroupBox("Saved Templates")
        templates_layout = QVBoxLayout(templates_group)
        self.templates_table = QTableWidget(0, 3)
        self.templates_table.setHorizontalHeaderLabels(["Name", "Type", "Position"])
        self.templates_table.horizontalHeader().setStretchLastSection(True)
        templates_layout.addWidget(self.templates_table)
        lists_row.addWidget(templates_group)

        root.addLayout(lists_row, 1)

    def refresh(self) -> None:
        jobs = self.ctx.database.list_recent_jobs(limit=15)
        self.recent_table.setRowCount(len(jobs))
        for row, j in enumerate(jobs):
            self.recent_table.setItem(row, 0, QTableWidgetItem(j["operation"]))
            self.recent_table.setItem(row, 1, QTableWidgetItem(j["source_name"]))
            self.recent_table.setItem(row, 2, QTableWidgetItem(j["status"]))
            self.recent_table.setItem(row, 3, QTableWidgetItem(j["created_at"]))

        templates = self.ctx.database.list_templates()
        self.templates_table.setRowCount(len(templates))
        for row, t in enumerate(templates):
            self.templates_table.setItem(row, 0, QTableWidgetItem(t.name))
            self.templates_table.setItem(row, 1, QTableWidgetItem(t.kind.value))
            self.templates_table.setItem(row, 2, QTableWidgetItem(t.position_preset.value))
