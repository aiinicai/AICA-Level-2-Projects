import os
from decimal import Decimal
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QProgressBar,
    QFrame,
    QTextEdit,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont, QColor, QBrush

from reconai.models.session import ReconciliationSession
from reconai.models.transaction import TransactionType, MatchStatus
from reconai.ui.workers.background_workers import ExportWorker


class ExportView(QWidget):
    """Bank Reconciliation Statement summary & Excel/PDF export view."""

    def __init__(self, session: ReconciliationSession, parent=None):
        super().__init__(parent)
        self.session = session
        self.last_excel_path: str = ""
        self.last_pdf_path: str = ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 1. Bank Reconciliation Statement Preview Box
        brs_group = QGroupBox("Bank Reconciliation Statement (BRS) — Real-Time Computation")
        brs_layout = QVBoxLayout(brs_group)

        self.brs_table = QTableWidget(5, 2)
        self.brs_table.setHorizontalHeaderLabels(["Particulars", "Amount (INR)"])
        self.brs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.brs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.brs_table.verticalHeader().setVisible(False)
        brs_layout.addWidget(self.brs_table)

        layout.addWidget(brs_group)

        # 2. Auditor Remarks & CA Opinion Card
        remarks_group = QGroupBox("Auditor Observations & Professional CA Opinion")
        remarks_form = QVBoxLayout(remarks_group)
        remarks_form.setSpacing(6)

        remarks_form.addWidget(QLabel("<b>Auditor Findings & Material Notes (Included in Excel & PDF Deliverables):</b>"))
        self.auditor_remarks_edit = QTextEdit()
        self.auditor_remarks_edit.setMaximumHeight(60)
        self.auditor_remarks_edit.setPlaceholderText("Enter specific audit observations, timing discrepancy explanations, or client confirmation notes...")
        self.auditor_remarks_edit.setText(self.session.auditor_remarks)
        self.auditor_remarks_edit.textChanged.connect(self._on_remarks_changed)
        remarks_form.addWidget(self.auditor_remarks_edit)

        remarks_form.addWidget(QLabel("<b>Chartered Accountant Professional Opinion / Qualification:</b>"))
        self.partner_opinion_edit = QTextEdit()
        self.partner_opinion_edit.setMaximumHeight(50)
        self.partner_opinion_edit.setPlaceholderText("In our opinion, the Bank Reconciliation Statement correctly reflects the timing and direct charge differences...")
        self.partner_opinion_edit.setText(self.session.partner_opinion)
        self.partner_opinion_edit.textChanged.connect(self._on_opinion_changed)
        remarks_form.addWidget(self.partner_opinion_edit)

        layout.addWidget(remarks_group)

        # 3. Export Actions Card
        export_group = QGroupBox("Export Audit Deliverables")
        export_layout = QVBoxLayout(export_group)

        btn_layout = QHBoxLayout()
        self.export_excel_btn = QPushButton("📊 Export Audit-Grade Excel (.xlsx)")
        self.export_excel_btn.setObjectName("secondaryBtn")
        self.export_excel_btn.clicked.connect(self._export_excel)

        self.export_pdf_btn = QPushButton("📄 Export Executive Summary PDF (.pdf)")
        self.export_pdf_btn.setObjectName("secondaryBtn")
        self.export_pdf_btn.clicked.connect(self._export_pdf)

        self.export_all_btn = QPushButton("🚀 Export Both (Excel + PDF Package)")
        self.export_all_btn.setObjectName("successBtn")
        self.export_all_btn.clicked.connect(self._export_all)

        btn_layout.addWidget(self.export_excel_btn)
        btn_layout.addWidget(self.export_pdf_btn)
        btn_layout.addWidget(self.export_all_btn)
        export_layout.addLayout(btn_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        export_layout.addWidget(self.progress_bar)

        # File Links / Open Buttons
        self.status_label = QLabel("Reports ready to export.")
        self.status_label.setStyleSheet("color: #94A3B8; font-style: italic;")
        export_layout.addWidget(self.status_label)

        open_layout = QHBoxLayout()
        self.open_excel_btn = QPushButton("Open Excel Report")
        self.open_excel_btn.setVisible(False)
        self.open_excel_btn.clicked.connect(self._open_excel)

        self.open_pdf_btn = QPushButton("Open PDF Report")
        self.open_pdf_btn.setVisible(False)
        self.open_pdf_btn.clicked.connect(self._open_pdf)

        self.open_folder_btn = QPushButton("Open Containing Folder")
        self.open_folder_btn.setVisible(False)
        self.open_folder_btn.clicked.connect(self._open_folder)

        open_layout.addWidget(self.open_excel_btn)
        open_layout.addWidget(self.open_pdf_btn)
        open_layout.addWidget(self.open_folder_btn)
        open_layout.addStretch()

        export_layout.addLayout(open_layout)
        layout.addWidget(export_group)

        layout.addStretch()

    def refresh_data(self):
        stmt_closing = self.session.statements[-1].balance if self.session.statements and self.session.statements[-1].balance else Decimal("0.00")
        uncredited = sum([l.amount for l in self.session.ledger_entries if not l.matched and l.type == TransactionType.CREDIT], Decimal("0.00"))
        unpresented = sum([l.amount for l in self.session.ledger_entries if not l.matched and l.type == TransactionType.DEBIT], Decimal("0.00"))
        adjusted_balance = stmt_closing + uncredited - unpresented

        rows = [
            ("Balance as per Bank Statement (Closing)", f"₹ {stmt_closing:,.2f}"),
            ("Add: Receipts / Deposits in books not yet credited by bank", f"₹ {uncredited:,.2f}"),
            ("Less: Payments / Cheques issued in books not yet presented to bank", f"- ₹ {unpresented:,.2f}"),
            ("Estimated Adjusted Balance as per Client Books", f"₹ {adjusted_balance:,.2f}"),
            ("Total Active Audit Findings & Flags", f"{len(self.session.audit_flags)} items"),
        ]

        bold_font = QFont()
        bold_font.setBold(True)

        for i, (part, amt) in enumerate(rows):
            item_part = QTableWidgetItem(part)
            item_amt = QTableWidgetItem(amt)
            item_amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if i == 3:
                item_part.setFont(bold_font)
                item_part.setForeground(QBrush(QColor("#60A5FA")))
                item_amt.setFont(bold_font)
                item_amt.setForeground(QBrush(QColor("#60A5FA")))
            self.brs_table.setItem(i, 0, item_part)
            self.brs_table.setItem(i, 1, item_amt)

        if not self.auditor_remarks_edit.toPlainText():
            self.auditor_remarks_edit.setText(self.session.auditor_remarks)
        if not self.partner_opinion_edit.toPlainText():
            self.partner_opinion_edit.setText(self.session.partner_opinion)

    def _on_remarks_changed(self):
        self.session.auditor_remarks = self.auditor_remarks_edit.toPlainText().strip()

    def _on_opinion_changed(self):
        self.session.partner_opinion = self.partner_opinion_edit.toPlainText().strip()

    def _export_excel(self):
        default_name = f"{self.session.client_name.replace(' ', '_')}_ReconReport.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Save Excel Report", default_name, "Excel Workbook (*.xlsx)")
        if path:
            self._start_export(path)

    def _export_pdf(self):
        default_name = f"{self.session.client_name.replace(' ', '_')}_AuditSummary.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF Summary", default_name, "PDF Report (*.pdf)")
        if path:
            self._start_export(path)

    def _export_all(self):
        default_name = f"{self.session.client_name.replace(' ', '_')}_Reconciliation_Package"
        path, _ = QFileDialog.getSaveFileName(self, "Save Reconciliation Package", default_name, "Reconciliation Package (*)")
        if path:
            self._start_export(path)

    def _start_export(self, base_path: str):
        self.progress_bar.setVisible(True)
        self.status_label.setText("Generating audit-grade reports...")

        self.worker = ExportWorker(self.session, base_path)
        self.worker.finished.connect(self._on_export_finished)
        self.worker.error.connect(self._on_export_error)
        self.worker.start()

    def _on_export_finished(self, results: dict):
        self.progress_bar.setVisible(False)
        self.last_excel_path = results.get("excel", "")
        self.last_pdf_path = results.get("pdf", "")

        self.status_label.setText(f"✓ Export successful! Files saved to disk.")
        self.open_excel_btn.setVisible(bool(self.last_excel_path and Path(self.last_excel_path).exists()))
        self.open_pdf_btn.setVisible(bool(self.last_pdf_path and Path(self.last_pdf_path).exists()))
        self.open_folder_btn.setVisible(True)

        QMessageBox.information(
            self,
            "Export Complete",
            f"Audit deliverables successfully exported:\n\n"
            f"Excel: {Path(self.last_excel_path).name}\n"
            f"PDF: {Path(self.last_pdf_path).name}",
        )

    def _on_export_error(self, err_msg: str):
        self.progress_bar.setVisible(False)
        self.status_label.setText("Export encountered an error.")
        QMessageBox.critical(self, "Export Failed", f"Could not generate reports:\n{err_msg}")

    def _open_excel(self):
        if self.last_excel_path and Path(self.last_excel_path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_excel_path))

    def _open_pdf(self):
        if self.last_pdf_path and Path(self.last_pdf_path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_pdf_path))

    def _open_folder(self):
        target = self.last_excel_path or self.last_pdf_path
        if target:
            folder = str(Path(target).parent)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
