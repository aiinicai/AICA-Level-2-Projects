"""
Main Desktop Application Window for TDS & TCS Certificate PDF Auto-Renamer.
Features complete batch workflow, live statistics cards, filterable data grid,
non-blocking QThread execution, real-time logging, and Excel/CSV report exports.
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from PyQt6.QtCore import Qt, QItemSelectionModel
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QTableView,
    QProgressBar,
    QPlainTextEdit,
    QFileDialog,
    QMessageBox,
    QHeaderView,
    QSplitter,
    QMenu,
    QFrame,
)
from PyQt6.QtGui import QAction, QIcon

import csv
import openpyxl

from config import AppConfig, ACT_1961, ACT_2025
from core.models import CertificateData, ProcessingStatus
from core.batch_processor import BatchWorkerThread
from core.undo_manager import UndoManager
from ui.table_model import CertificateTableModel, CertificateFilterProxyModel
from ui.preview_dialog import CertificatePreviewDialog
from ui.settings_dialog import SettingsDialog
from ui.styles import APP_STYLESHEET


class MainWindow(QMainWindow):
    """Primary application window for the TDS & TCS Certificate PDF Auto-Renamer."""

    def __init__(self, initial_folder: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("TDS & TCS Certificate PDF Auto-Renamer")
        self.resize(1300, 840)
        self.setMinimumSize(950, 600)
        self.setStyleSheet(APP_STYLESHEET)

        self.config = AppConfig.load()
        self.source_folder: Optional[Path] = Path(initial_folder) if initial_folder else None
        self.undo_manager = UndoManager()
        self.worker: Optional[BatchWorkerThread] = None

        self._init_ui()

        if self.source_folder and self.source_folder.exists():
            self.folder_input.setText(str(self.source_folder))
            self._start_analysis()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # ----------------------------------------------------------------------
        # 1. Header Card Banner
        # ----------------------------------------------------------------------
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        hdr_layout = QVBoxLayout(header_card)
        hdr_layout.setContentsMargins(16, 12, 16, 12)

        hdr_title = QLabel("TDS & TCS Certificate PDF Auto-Renamer")
        hdr_title.setObjectName("HeaderTitle")
        hdr_sub = QLabel(
            "TRACES Compliance Automation • Income-tax Act, 1961 (Forms 16, 16A, 16B, 16C, 16D, 27D) & Income-tax Act, 2025 (Forms 130, 131, 132, 133)"
        )
        hdr_sub.setObjectName("HeaderSubtitle")
        hdr_layout.addWidget(hdr_title)
        hdr_layout.addWidget(hdr_sub)
        main_layout.addWidget(header_card)

        # ----------------------------------------------------------------------
        # 2. Metric Statistics Cards
        # ----------------------------------------------------------------------
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)

        self.card_total = self._create_metric_card("Total Files", "0")
        self.card_valid = self._create_metric_card("Extracted", "0")
        self.card_1961 = self._create_metric_card("1961 Act", "0")
        self.card_2025 = self._create_metric_card("2025 Act", "0")
        self.card_renamed = self._create_metric_card("Renamed", "0")
        self.card_errors = self._create_metric_card("Issues", "0")

        stats_layout.addWidget(self.card_total)
        stats_layout.addWidget(self.card_valid)
        stats_layout.addWidget(self.card_1961)
        stats_layout.addWidget(self.card_2025)
        stats_layout.addWidget(self.card_renamed)
        stats_layout.addWidget(self.card_errors)
        main_layout.addLayout(stats_layout)

        # ----------------------------------------------------------------------
        # 3. Source Folder Selection & Action Bar
        # ----------------------------------------------------------------------
        folder_bar = QHBoxLayout()
        folder_bar.setSpacing(8)

        folder_label = QLabel("<b>Source Folder:</b>")
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Select folder containing TDS/TCS certificate PDF files...")
        self.browse_btn = QPushButton("Browse Folder...")
        self.browse_btn.clicked.connect(self._on_browse_folder)

        self.subfolders_check = QCheckBox("Include Subfolders")
        self.subfolders_check.setChecked(self.config.include_subfolders)
        self.subfolders_check.stateChanged.connect(self._on_subfolder_toggle)

        self.settings_btn = QPushButton("Settings...")
        self.settings_btn.clicked.connect(self._open_settings)

        folder_bar.addWidget(folder_label)
        folder_bar.addWidget(self.folder_input, 1)
        folder_bar.addWidget(self.browse_btn)
        folder_bar.addWidget(self.subfolders_check)
        folder_bar.addWidget(self.settings_btn)
        main_layout.addLayout(folder_bar)

        # ----------------------------------------------------------------------
        # 4. Action Command Buttons
        # ----------------------------------------------------------------------
        cmd_bar = QHBoxLayout()
        cmd_bar.setSpacing(10)

        self.analyze_btn = QPushButton("1. Scan & Analyze (Preview)")
        self.analyze_btn.setObjectName("PrimaryBtn")
        self.analyze_btn.clicked.connect(self._start_analysis)

        self.rename_btn = QPushButton("2. Execute Renaming")
        self.rename_btn.setObjectName("SuccessBtn")
        self.rename_btn.setEnabled(False)
        self.rename_btn.clicked.connect(self._start_renaming)

        self.undo_btn = QPushButton("Undo Last Batch")
        self.undo_btn.setObjectName("WarningBtn")
        self.undo_btn.clicked.connect(self._rollback_batch)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_worker)

        self.export_btn = QPushButton("Export Report...")
        self.export_btn.clicked.connect(self._export_report)

        cmd_bar.addWidget(self.analyze_btn)
        cmd_bar.addWidget(self.rename_btn)
        cmd_bar.addWidget(self.undo_btn)
        cmd_bar.addWidget(self.cancel_btn)
        cmd_bar.addStretch()
        cmd_bar.addWidget(self.export_btn)
        main_layout.addLayout(cmd_bar)

        # ----------------------------------------------------------------------
        # 5. Filter & Search Controls
        # ----------------------------------------------------------------------
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by Name, PAN, TAN, Form, or File...")
        self.search_input.textChanged.connect(self._on_search_text_changed)

        self.act_combo = QComboBox()
        self.act_combo.addItems(["All Acts", ACT_1961, ACT_2025])
        self.act_combo.currentIndexChanged.connect(self._on_act_filter_changed)

        self.form_combo = QComboBox()
        self.form_combo.addItems([
            "All Forms",
            "Form 16", "Form 16A", "Form 16B", "Form 16C", "Form 16D", "Form 16E", "Form 27D",
            "Form 130", "Form 131", "Form 132", "Form 133",
        ])
        self.form_combo.currentIndexChanged.connect(self._on_form_filter_changed)

        self.status_combo = QComboBox()
        self.status_combo.addItems([
            "All Statuses",
            "Pending", "Extracted", "Preview Ready", "Renamed", "Copied", "Skipped", "Error",
        ])
        self.status_combo.currentIndexChanged.connect(self._on_status_filter_changed)

        filter_bar.addWidget(QLabel("Filter:"))
        filter_bar.addWidget(self.search_input, 1)
        filter_bar.addWidget(self.act_combo)
        filter_bar.addWidget(self.form_combo)
        filter_bar.addWidget(self.status_combo)
        main_layout.addLayout(filter_bar)

        # ----------------------------------------------------------------------
        # 6. Central Table & Splitter for Activity Log
        # ----------------------------------------------------------------------
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Certificate Data Table
        self.table_view = QTableView()
        self.source_model = CertificateTableModel()
        self.proxy_model = CertificateFilterProxyModel()
        self.proxy_model.setSourceModel(self.source_model)
        self.table_view.setModel(self.proxy_model)

        # Table Appearance & Behavior
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.doubleClicked.connect(self._on_table_double_clicked)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_context_menu)

        splitter.addWidget(self.table_view)

        # Activity Log Box
        log_panel = QWidget()
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(0, 4, 0, 0)
        log_layout.setSpacing(4)

        log_hdr = QHBoxLayout()
        log_hdr.addWidget(QLabel("<b>Real-time Activity Log:</b>"))
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self._clear_log)
        log_hdr.addStretch()
        log_hdr.addWidget(clear_log_btn)
        log_layout.addLayout(log_hdr)

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(200)
        log_layout.addWidget(self.log_view)

        splitter.addWidget(log_panel)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter, 1)

        # ----------------------------------------------------------------------
        # 7. Progress Bar & Status Bar
        # ----------------------------------------------------------------------
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready. Select a folder and click 'Scan & Analyze'.")
        self.statusBar().addWidget(self.status_label, 1)

    def _create_metric_card(self, label: str, init_val: str) -> QFrame:
        """Create a styled metric card widget."""
        card = QFrame()
        card.setProperty("class", "MetricCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(8, 6, 8, 6)
        c_layout.setSpacing(2)

        lbl = QLabel(label)
        lbl.setProperty("class", "MetricLabel")
        val = QLabel(init_val)
        val.setProperty("class", "MetricValue")
        val.setObjectName(f"val_{label.replace(' ', '_')}")

        c_layout.addWidget(lbl)
        c_layout.addWidget(val)
        return card

    def _update_metrics(self):
        """Recalculate and update the stat cards."""
        certs = self.source_model.get_all()
        total = len(certs)
        valid = sum(1 for c in certs if c.deductee_name)
        act1961 = sum(1 for c in certs if "1961" in c.act)
        act2025 = sum(1 for c in certs if "2025" in c.act)
        renamed = sum(1 for c in certs if c.status in (ProcessingStatus.RENAMED, ProcessingStatus.COPIED, ProcessingStatus.MOVED))
        errors = sum(1 for c in certs if c.status == ProcessingStatus.ERROR)

        self.card_total.findChild(QLabel, "val_Total_Files").setText(str(total))
        self.card_valid.findChild(QLabel, "val_Extracted").setText(str(valid))
        self.card_1961.findChild(QLabel, "val_1961_Act").setText(str(act1961))
        self.card_2025.findChild(QLabel, "val_2025_Act").setText(str(act2025))
        self.card_renamed.findChild(QLabel, "val_Renamed").setText(str(renamed))
        self.card_errors.findChild(QLabel, "val_Issues").setText(str(errors))

    # ==========================================================================
    # WORKFLOW ACTIONS: ANALYZE, RENAME, ROLLBACK
    # ==========================================================================

    def _on_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select TDS/TCS PDF Certificates Folder")
        if folder:
            self.source_folder = Path(folder)
            self.folder_input.setText(folder)
            self._start_analysis()

    def _on_subfolder_toggle(self, state):
        self.config.include_subfolders = (state == Qt.CheckState.Checked.value)
        self.config.save()

    def _open_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self._append_log("INFO", "Settings updated. Re-evaluating planned filenames...")
            certs = self.source_model.get_all()
            if certs:
                from core.renamer import CertificateRenamer
                renamer = CertificateRenamer(
                    template=self.config.naming_template,
                    collision_policy=self.config.collision_policy,
                    execution_mode=self.config.execution_mode,
                    output_folder=Path(self.config.output_folder) if self.config.output_folder else None,
                    max_length=self.config.max_filename_length,
                )
                renamer.plan_batch(certs)
                self.source_model.set_data(certs)
                self._update_metrics()

    def _start_analysis(self):
        folder_str = self.folder_input.text().strip()
        if not folder_str or not Path(folder_str).exists():
            QMessageBox.warning(self, "Invalid Folder", "Please select a valid folder containing PDF files.")
            return

        folder = Path(folder_str)
        pattern = "**/*.pdf" if self.subfolders_check.isChecked() else "*.pdf"
        pdf_files = list(folder.glob(pattern))

        if not pdf_files:
            QMessageBox.information(self, "No PDFs Found", f"No PDF files found in:\n{folder}")
            return

        self.source_model.clear()
        self._update_metrics()
        self._set_ui_processing_state(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(pdf_files))
        self.progress_bar.setValue(0)

        self._append_log("INFO", f"Discovered {len(pdf_files)} PDF files in {folder}")

        self.worker = BatchWorkerThread(
            files=pdf_files,
            config=self.config,
            phase="analyze",
            parent=self,
        )
        self.worker.progress_changed.connect(self._on_worker_progress)
        self.worker.item_analyzed.connect(self._on_item_analyzed)
        self.worker.log_message.connect(self._append_log)
        self.worker.batch_finished.connect(self._on_analysis_finished)
        self.worker.start()

    def _on_item_analyzed(self, cert: CertificateData):
        self.source_model.update_item(cert)
        self._update_metrics()

    def _on_analysis_finished(self, summary: dict):
        self._set_ui_processing_state(False)
        self.progress_bar.setVisible(False)
        self.rename_btn.setEnabled(summary.get("success", 0) > 0)
        self.status_label.setText(
            f"Analysis complete: {summary['processed']} analyzed, {summary['success']} ready to rename, {summary['errors']} issues."
        )

    def _start_renaming(self):
        certs = self.source_model.get_all()
        ready_certs = [c for c in certs if c.status != ProcessingStatus.ERROR and c.proposed_filename]

        if not ready_certs:
            QMessageBox.information(self, "No Files Ready", "No certificates ready for renaming.")
            return

        msg = (
            f"You are about to execute renaming on {len(ready_certs)} files.\n"
            f"Mode: {self.config.execution_mode.replace('_', ' ').title()}\n"
            f"Template: {self.config.naming_template}\n\n"
            f"Do you want to proceed?"
        )
        reply = QMessageBox.question(self, "Confirm Batch Rename", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._set_ui_processing_state(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(ready_certs))
        self.progress_bar.setValue(0)

        self.worker = BatchWorkerThread(
            files=[],
            config=self.config,
            phase="rename",
            existing_certs=ready_certs,
            parent=self,
        )
        self.worker.progress_changed.connect(self._on_worker_progress)
        self.worker.item_renamed.connect(self._on_item_renamed)
        self.worker.log_message.connect(self._append_log)
        self.worker.batch_finished.connect(self._on_rename_finished)
        self.worker.start()

    def _on_item_renamed(self, cert: CertificateData):
        self.source_model.update_item(cert)
        self._update_metrics()

    def _on_rename_finished(self, summary: dict):
        self._set_ui_processing_state(False)
        self.progress_bar.setVisible(False)
        self.rename_btn.setEnabled(False)
        self.status_label.setText(
            f"Rename finished: {summary.get('renamed', 0)} renamed, {summary.get('skipped', 0)} skipped, {summary.get('errors', 0)} errors."
        )
        QMessageBox.information(
            self,
            "Batch Complete",
            f"Batch operation completed!\n\n"
            f"Renamed: {summary.get('renamed', 0)}\n"
            f"Skipped: {summary.get('skipped', 0)}\n"
            f"Errors: {summary.get('errors', 0)}\n"
            f"Undo Checkpoint: {summary.get('session_id', 'None')}",
        )

    def _rollback_batch(self):
        last_session = self.undo_manager.get_last_session()
        if not last_session:
            QMessageBox.information(self, "No Undo Available", "No recorded batch rename sessions found to undo.")
            return

        session_id = last_session["session_id"]
        count = last_session["operations_count"]
        timestamp = last_session["timestamp"]

        msg = f"Rollback previous batch ({session_id})?\nRecorded: {timestamp}\nFiles to restore: {count}"
        reply = QMessageBox.question(self, "Confirm Undo", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        succ, errs, logs = self.undo_manager.rollback_session(session_id)
        for line in logs:
            self._append_log("INFO", line)

        QMessageBox.information(
            self,
            "Rollback Finished",
            f"Rollback results:\nRestored: {succ} files\nErrors: {errs}",
        )
        self._start_analysis()

    def _cancel_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self._append_log("WARNING", "Cancellation requested...")

    def _on_worker_progress(self, current: int, total: int, filename: str):
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Processing ({current}/{total}): {filename}")

    def _set_ui_processing_state(self, is_running: bool):
        self.analyze_btn.setEnabled(not is_running)
        self.browse_btn.setEnabled(not is_running)
        self.settings_btn.setEnabled(not is_running)
        self.undo_btn.setEnabled(not is_running)
        self.cancel_btn.setEnabled(is_running)

    # ==========================================================================
    # LOGGING & REPORTING
    # ==========================================================================

    def _append_log(self, level: str, message: str):
        now_str = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{now_str}] [{level:7s}] {message}"
        self.log_view.appendPlainText(formatted)

    def _clear_log(self):
        self.log_view.clear()

    def _export_report(self):
        certs = self.source_model.get_all()
        if not certs:
            QMessageBox.warning(self, "No Data", "No certificate data available to export.")
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Certificate Reconciliation Report",
            f"TDS_TCS_Renaming_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Workbook (*.xlsx);;CSV File (*.csv)",
        )
        if not file_path:
            return

        try:
            records = [c.to_dict() for c in certs]
            if not records:
                return

            if file_path.endswith(".csv") or "CSV" in selected_filter:
                fieldnames = list(records[0].keys())
                with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(records)
            else:
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "TDS_TCS_Certificates"
                headers = list(records[0].keys())
                ws.append(headers)
                for r in records:
                    ws.append([str(r.get(h, "")) for h in headers])
                wb.save(file_path)

            self._append_log("SUCCESS", f"Exported reconciliation report to: {file_path}")
            QMessageBox.information(self, "Export Successful", f"Report saved successfully:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export report:\n{str(e)}")

    # ==========================================================================
    # TABLE INTERACTIONS & CONTEXT MENU
    # ==========================================================================

    def _on_search_text_changed(self, text: str):
        self.proxy_model.set_search_text(text)

    def _on_act_filter_changed(self, index: int):
        self.proxy_model.set_act_filter(self.act_combo.currentText())

    def _on_form_filter_changed(self, index: int):
        self.proxy_model.set_form_filter(self.form_combo.currentText())

    def _on_status_filter_changed(self, index: int):
        self.proxy_model.set_status_filter(self.status_combo.currentText())

    def _on_table_double_clicked(self, proxy_index):
        source_index = self.proxy_model.mapToSource(proxy_index)
        cert = self.source_model.get_certificate(source_index.row())
        if cert:
            dlg = CertificatePreviewDialog(cert, self)
            if dlg.exec():
                self.source_model.update_item(cert)

    def _show_context_menu(self, pos):
        proxy_index = self.table_view.indexAt(pos)
        if not proxy_index.isValid():
            return

        source_index = self.proxy_model.mapToSource(proxy_index)
        cert = self.source_model.get_certificate(source_index.row())
        if not cert:
            return

        menu = QMenu(self)
        view_action = menu.addAction("Inspect / Edit Details...")
        open_file_action = menu.addAction("Open PDF in Default Viewer")
        open_folder_action = menu.addAction("Show in File Explorer")

        chosen = menu.exec(self.table_view.viewport().mapToGlobal(pos))
        if chosen == view_action:
            dlg = CertificatePreviewDialog(cert, self)
            if dlg.exec():
                self.source_model.update_item(cert)
        elif chosen == open_file_action:
            p = cert.final_filepath if (cert.final_filepath and cert.final_filepath.exists()) else cert.file_path
            if p and Path(p).exists():
                os.startfile(str(p))
        elif chosen == open_folder_action:
            p = cert.final_filepath if (cert.final_filepath and cert.final_filepath.exists()) else cert.file_path
            if p and Path(p).exists():
                subprocess.run(["explorer", f"/select,{str(Path(p).resolve())}"])
