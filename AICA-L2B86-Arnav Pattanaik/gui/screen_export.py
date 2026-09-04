"""Screen 2: Export — Data-Model-ready Excel Table / CSV export (Option A)."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QFileDialog,
    QLineEdit, QRadioButton, QButtonGroup, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from core.export_engine import export_as_excel_table, export_as_csv, suggested_filename
from gui.app_state import AppState
from gui.styles import COLOR_TEXT_SECONDARY, status_pill_style


class ExportWorker(QThread):
    finished_ok = pyqtSignal(str)
    finished_err = pyqtSignal(str)

    def __init__(self, df, output_path, fmt):
        super().__init__()
        self.df = df
        self.output_path = output_path
        self.fmt = fmt

    def run(self):
        try:
            if self.fmt == "xlsx":
                path = export_as_excel_table(self.df, self.output_path)
            else:
                path = export_as_csv(self.df, self.output_path)
            self.finished_ok.emit(path)
        except Exception as exc:
            self.finished_err.emit(str(exc))


class ScreenExport(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self._worker: ExportWorker | None = None
        self._output_dir = str(Path.home() / "Downloads")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        title = QLabel("Export")
        title.setObjectName("screenTitle")
        outer.addWidget(title)
        subtitle = QLabel(
            "Export the compiled dataset as a Table/CSV formatted for direct load into "
            "Excel's Power Pivot Data Model."
        )
        subtitle.setObjectName("screenSubtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-weight: 600; padding: 8px 0;")
        outer.addWidget(self.summary_label)

        # --- Format selection ---
        fmt_card = QFrame()
        fmt_card.setObjectName("card")
        fmt_layout = QVBoxLayout(fmt_card)

        self.radio_xlsx = QRadioButton("Excel Table (.xlsx, single Table object)")
        self.radio_csv = QRadioButton("CSV (UTF-8)")
        self.radio_xlsx.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.radio_xlsx)
        group.addButton(self.radio_csv)
        self.radio_xlsx.toggled.connect(self._on_format_change)
        fmt_layout.addWidget(self.radio_xlsx)
        fmt_layout.addWidget(self.radio_csv)

        helper = QLabel(
            "Both formats load directly into Excel's Data Model via Get Data → From Table/Range "
            "or From Text/CSV → Add to Data Model. No manual pivot table needed here — build your "
            "Power Pivot report in Excel using this file as the source."
        )
        helper.setWordWrap(True)
        helper.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        fmt_layout.addWidget(helper)
        outer.addWidget(fmt_card)

        # --- Filename / destination ---
        path_row = QHBoxLayout()
        self.filename_edit = QLineEdit()
        path_row.addWidget(QLabel("File name:"))
        path_row.addWidget(self.filename_edit)
        browse_btn = QPushButton("Choose folder...")
        browse_btn.setObjectName("secondaryButton")
        browse_btn.clicked.connect(self._choose_folder)
        path_row.addWidget(browse_btn)
        outer.addLayout(path_row)

        self.dest_label = QLabel()
        self.dest_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        outer.addWidget(self.dest_label)

        # --- Preview table ---
        preview_label = QLabel("Preview (first 20 rows)")
        preview_label.setObjectName("sectionHeader")
        outer.addWidget(preview_label)

        self.preview_table = QTableWidget(0, 0)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setMinimumHeight(200)
        outer.addWidget(self.preview_table)

        # --- Export button + progress ---
        action_row = QHBoxLayout()
        self.export_btn = QPushButton("Export Now")
        self.export_btn.setObjectName("primaryButton")
        self.export_btn.clicked.connect(self._do_export)
        action_row.addWidget(self.export_btn)

        self.export_csv_btn = QPushButton("Export as CSV (fast)")
        self.export_csv_btn.setObjectName("secondaryButton")
        self.export_csv_btn.clicked.connect(self._do_export_csv_quick)
        action_row.addWidget(self.export_csv_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setMaximumWidth(200)
        action_row.addWidget(self.progress)
        action_row.addStretch()
        outer.addLayout(action_row)

        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        outer.addWidget(self.result_label)

        outer.addStretch()

    def refresh(self):
        """Called when this screen becomes visible / after a new compile."""
        df = self.state.compiled_df
        if df is None or df.empty:
            self.summary_label.setText("No compiled data available. Complete Screen 1 first.")
            self.preview_table.setRowCount(0)
            self.preview_table.setColumnCount(0)
            self.export_btn.setEnabled(False)
            return

        self.export_btn.setEnabled(True)
        self.summary_label.setText(
            f"{len(df):,} rows compiled across {self.state.total_divisions_compiled} division(s) "
            f"for {self.state.billing_month} {self.state.billing_year}."
        )
        self._update_filename()
        self._update_preview(df)
        self.dest_label.setText(f"Destination folder: {self._output_dir}")

    def _on_format_change(self, *_):
        self._update_filename()

    def _update_filename(self):
        ext = "xlsx" if self.radio_xlsx.isChecked() else "csv"
        self.filename_edit.setText(suggested_filename(self.state.billing_month, self.state.billing_year, ext))

    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose destination folder", self._output_dir)
        if folder:
            self._output_dir = folder
            self.dest_label.setText(f"Destination folder: {self._output_dir}")

    def _update_preview(self, df):
        import pandas as pd
        preview = df.head(20)
        self.preview_table.setColumnCount(len(preview.columns))
        self.preview_table.setHorizontalHeaderLabels(list(preview.columns))
        self.preview_table.setRowCount(len(preview))
        for r in range(len(preview)):
            for c, col in enumerate(preview.columns):
                val = preview.iloc[r, c]
                text = "" if (val is None or (isinstance(val, float) and pd.isna(val))) else str(val)
                self.preview_table.setItem(r, c, QTableWidgetItem(text))
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    def _do_export(self):
        df = self.state.compiled_df
        if df is None or df.empty:
            return
        filename = self.filename_edit.text().strip()
        if not filename:
            QMessageBox.warning(self, "Missing filename", "Please enter an output file name.")
            return

        output_path = str(Path(self._output_dir) / filename)
        fmt = "xlsx" if self.radio_xlsx.isChecked() else "csv"

        self.export_btn.setEnabled(False)
        self.export_csv_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.result_label.setText("")

        self._worker = ExportWorker(df, output_path, fmt)
        self._worker.finished_ok.connect(self._on_export_success)
        self._worker.finished_err.connect(self._on_export_error)
        self._worker.start()

    def _do_export_csv_quick(self):
        """One-click CSV export regardless of the radio selection above — the
        fast path, useful at large row counts where the Excel Table export
        can take minutes (see README performance notes)."""
        df = self.state.compiled_df
        if df is None or df.empty:
            return
        csv_filename = suggested_filename(self.state.billing_month, self.state.billing_year, "csv")
        output_path = str(Path(self._output_dir) / csv_filename)

        self.export_btn.setEnabled(False)
        self.export_csv_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.result_label.setText("")

        self._worker = ExportWorker(df, output_path, "csv")
        self._worker.finished_ok.connect(self._on_export_success)
        self._worker.finished_err.connect(self._on_export_error)
        self._worker.start()

    def _on_export_success(self, path: str):
        self.export_btn.setEnabled(True)
        self.export_csv_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.result_label.setText(f"✓ Export complete: {path}")
        self.result_label.setStyleSheet(status_pill_style("ok"))

    def _on_export_error(self, msg: str):
        self.export_btn.setEnabled(True)
        self.export_csv_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.result_label.setText(f"✗ Export failed: {msg}")
        self.result_label.setStyleSheet(status_pill_style("error"))
