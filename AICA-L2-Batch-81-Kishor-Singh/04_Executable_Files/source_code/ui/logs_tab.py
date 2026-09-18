"""Logs tab: application log tail, recent jobs, and the local audit trail (activity register)."""
from __future__ import annotations

import csv

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.app_context import AppContext


class LogsTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_export_audit = QPushButton("Export Audit Trail to CSV")
        self.btn_export_audit.setObjectName("SecondaryButton")
        toolbar.addWidget(self.btn_refresh)
        toolbar.addWidget(self.btn_export_audit)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.tabs.addTab(self.log_view, "Application Log")

        self.audit_table = QTableWidget(0, 8)
        self.audit_table.setHorizontalHeaderLabels(
            ["Timestamp", "Operator", "Operation", "Source Document", "Output Document", "Pages", "Template Used", "Result"]
        )
        self.audit_table.horizontalHeader().setStretchLastSection(True)
        self.tabs.addTab(self.audit_table, "Activity Register (Audit Trail)")

        self.recent_table = QTableWidget(0, 5)
        self.recent_table.setHorizontalHeaderLabels(["Operation", "Source", "Output", "Status", "Date"])
        self.recent_table.horizontalHeader().setStretchLastSection(True)
        self.tabs.addTab(self.recent_table, "Recent Jobs")

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_export_audit.clicked.connect(self.export_audit_csv)

    def refresh(self) -> None:
        log_path = self.ctx.config.get_log_dir() / "pdf_office_utility.log"
        if log_path.exists():
            try:
                text = log_path.read_text(encoding="utf-8", errors="replace")
                self.log_view.setPlainText(text[-100_000:])  # keep the view responsive on huge logs
                self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())
            except OSError:
                self.log_view.setPlainText("(Could not read log file)")
        else:
            self.log_view.setPlainText("(No log file yet)")

        entries = self.ctx.database.list_audit_entries()
        self.audit_table.setRowCount(len(entries))
        for row, e in enumerate(entries):
            values = [e["timestamp"], e["operator"], e["operation"], e["source_document"], e["output_document"], e["pages_processed"], e["template_used"], e["result"]]
            for col, v in enumerate(values):
                self.audit_table.setItem(row, col, QTableWidgetItem(str(v or "")))

        jobs = self.ctx.database.list_recent_jobs()
        self.recent_table.setRowCount(len(jobs))
        for row, j in enumerate(jobs):
            values = [j["operation"], j["source_name"], j["output_name"], j["status"], j["created_at"]]
            for col, v in enumerate(values):
                self.recent_table.setItem(row, col, QTableWidgetItem(str(v or "")))

    def export_audit_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Audit Trail", "audit_trail.csv", "CSV Files (*.csv)")
        if not path:
            return
        entries = self.ctx.database.list_audit_entries()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Operator", "Operation", "Source Document", "Output Document", "Pages Processed", "Template Used", "Result"])
            for e in entries:
                writer.writerow([e["timestamp"], e["operator"], e["operation"], e["source_document"], e["output_document"], e["pages_processed"], e["template_used"], e["result"]])
        QMessageBox.information(self, "Export Complete", f"Audit trail exported to:\n{path}")
