"""Screen 1: Compile Data — file upload, header detection, compilation, load log. Schema-free."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QSpinBox, QCheckBox,
    QMessageBox, QScrollArea, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from config.schema import MONTH_OPTIONS, YEAR_OPTIONS
from core.ingestion import FileIngestSpec, compile_divisions, detect_file_header
from gui.app_state import AppState, UploadedFileEntry
from gui.styles import status_pill_style, COLOR_TEXT_SECONDARY
from gui.load_log_detail_dialog import LoadLogDetailDialog


class CompileWorker(QThread):
    """Runs compile_divisions() off the UI thread so the app doesn't freeze on large files."""
    finished_ok = pyqtSignal(object)   # CompileResult
    finished_err = pyqtSignal(str)

    def __init__(self, specs: list[FileIngestSpec]):
        super().__init__()
        self.specs = specs

    def run(self):
        try:
            result = compile_divisions(self.specs)
            self.finished_ok.emit(result)
        except Exception as exc:
            self.finished_err.emit(str(exc))


class ScreenCompileData(QWidget):
    def __init__(self, state: AppState, on_compiled_callback=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.on_compiled_callback = on_compiled_callback
        self.file_rows: list[UploadedFileEntry] = []
        self._worker: CompileWorker | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        title = QLabel("Compile Data")
        title.setObjectName("screenTitle")
        outer.addWidget(title)
        subtitle = QLabel(
            "Upload division-wise Excel files for a billing period and compile them into one "
            "clean dataset. Whatever columns each file has are kept as-is — files are matched "
            "up by exact column name only, and the header row is auto-detected from row 1 or 2."
        )
        subtitle.setObjectName("screenSubtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        period_row = QHBoxLayout()
        period_row.addWidget(QLabel("Period label (for filenames only):"))
        self.month_combo = QComboBox()
        self.month_combo.addItems(MONTH_OPTIONS)
        self.month_combo.setCurrentText(self.state.billing_month)
        self.month_combo.currentTextChanged.connect(self._on_period_change)
        period_row.addWidget(self.month_combo)

        self.year_combo = QComboBox()
        self.year_combo.addItems([str(y) for y in YEAR_OPTIONS])
        self.year_combo.setCurrentText(str(self.state.billing_year))
        self.year_combo.currentTextChanged.connect(self._on_period_change)
        period_row.addWidget(self.year_combo)
        period_row.addStretch()
        outer.addLayout(period_row)

        drop_frame = QFrame()
        drop_frame.setObjectName("dropZone")
        drop_frame.setMinimumHeight(90)
        drop_layout = QVBoxLayout(drop_frame)
        drop_label = QLabel("Click 'Add Files' to select Excel files (.xlsx / .xls)")
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        drop_layout.addWidget(drop_label)

        btn_row = QHBoxLayout()
        add_files_btn = QPushButton("+ Add Files")
        add_files_btn.setObjectName("primaryButton")
        add_files_btn.clicked.connect(self._add_files)
        btn_row.addStretch()
        btn_row.addWidget(add_files_btn)
        btn_row.addStretch()
        drop_layout.addLayout(btn_row)
        outer.addWidget(drop_frame)

        table_label = QLabel("Uploaded Files")
        table_label.setObjectName("sectionHeader")
        outer.addWidget(table_label)

        self.file_table = QTableWidget(0, 6)
        self.file_table.setHorizontalHeaderLabels(
            ["File Name", "Label / Source Tag", "Header Row", "Row Count", "Status", "Action"]
        )
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.file_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.file_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.file_table.setColumnWidth(2, 90)
        self.file_table.setColumnWidth(3, 80)
        self.file_table.setColumnWidth(4, 90)
        self.file_table.setColumnWidth(5, 90)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.file_table.setMinimumHeight(160)
        self.file_table.setMaximumHeight(240)
        outer.addWidget(self.file_table)

        compile_row = QHBoxLayout()
        self.compile_btn = QPushButton("Compile All")
        self.compile_btn.setObjectName("primaryButton")
        self.compile_btn.setEnabled(False)
        self.compile_btn.clicked.connect(self._compile_all)
        compile_row.addWidget(self.compile_btn)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setObjectName("secondaryButton")
        self.clear_btn.clicked.connect(self._clear_all)
        compile_row.addWidget(self.clear_btn)
        compile_row.addStretch()
        outer.addLayout(compile_row)

        log_label = QLabel("Load Log")
        log_label.setObjectName("sectionHeader")
        outer.addWidget(log_label)

        self.log_scroll = QScrollArea()
        self.log_scroll.setWidgetResizable(True)
        self.log_scroll.setMinimumHeight(140)
        self.log_container = QWidget()
        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.setSpacing(6)
        self.log_layout.addStretch()
        self.log_scroll.setWidget(self.log_container)
        outer.addWidget(self.log_scroll)

        bottom_row = QHBoxLayout()
        self.ack_checkbox = QCheckBox("I have reviewed the load log")
        self.ack_checkbox.stateChanged.connect(self._on_ack_change)
        bottom_row.addWidget(self.ack_checkbox)
        bottom_row.addStretch()
        outer.addLayout(bottom_row)

    # ------------------------------------------------------------------
    def _on_period_change(self, *_):
        self.state.billing_month = self.month_combo.currentText()
        self.state.billing_year = int(self.year_combo.currentText())

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Excel files", "", "Excel Files (*.xlsx *.xls)"
        )
        if not paths:
            return
        for p in paths:
            try:
                header_row, confidence, headers = detect_file_header(p)
            except Exception:
                header_row, confidence, headers = 1, "error", []
            name = Path(p).stem
            entry = UploadedFileEntry(
                file_path=p, file_name=Path(p).name, detected_division=name,
                detected_header_row=header_row, header_confidence=confidence,
                status="Pending",
            )
            self.file_rows.append(entry)
        self._refresh_file_table()
        self.compile_btn.setEnabled(len(self.file_rows) > 0)

    def _refresh_file_table(self):
        self.file_table.setRowCount(len(self.file_rows))
        for i, entry in enumerate(self.file_rows):
            self.file_table.setItem(i, 0, QTableWidgetItem(entry.file_name))

            div_combo = QComboBox()
            div_combo.setEditable(True)
            div_combo.addItem(entry.detected_division)
            div_combo.setCurrentText(entry.detected_division)
            div_combo.currentTextChanged.connect(lambda text, idx=i: self._on_division_edit(idx, text))
            self.file_table.setCellWidget(i, 1, div_combo)

            header_spin = QSpinBox()
            header_spin.setMinimum(1)
            header_spin.setMaximum(2)  # header row is only ever row 1 or row 2, per design
            header_spin.setValue(min(entry.detected_header_row, 2))
            header_spin.valueChanged.connect(lambda val, idx=i: self._on_header_row_edit(idx, val))
            self.file_table.setCellWidget(i, 2, header_spin)

            self.file_table.setItem(i, 3, QTableWidgetItem(str(entry.row_count or "-")))

            status_label = QLabel(entry.status)
            status_label.setStyleSheet(status_pill_style(self._status_kind(entry.status)))
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.file_table.setCellWidget(i, 4, status_label)

            remove_btn = QPushButton("Remove")
            remove_btn.setObjectName("secondaryButton")
            remove_btn.setStyleSheet("padding: 3px 6px; font-size: 10px;")
            remove_btn.clicked.connect(lambda checked, idx=i: self._remove_file(idx))
            self.file_table.setCellWidget(i, 5, remove_btn)

    @staticmethod
    def _status_kind(status: str) -> str:
        return {"Pending": "pending", "Compiling": "pending", "Compiled": "ok", "Error": "error"}.get(status, "pending")

    def _on_division_edit(self, idx: int, text: str):
        if 0 <= idx < len(self.file_rows):
            self.file_rows[idx].detected_division = text

    def _on_header_row_edit(self, idx: int, value: int):
        if 0 <= idx < len(self.file_rows):
            self.file_rows[idx].detected_header_row = value

    def _remove_file(self, idx: int):
        if 0 <= idx < len(self.file_rows):
            del self.file_rows[idx]
            self._refresh_file_table()
            self.compile_btn.setEnabled(len(self.file_rows) > 0)

    def _clear_all(self):
        self.file_rows = []
        self._refresh_file_table()
        self.compile_btn.setEnabled(False)
        self._clear_log_panel()
        self.state.reset_compilation()

    # ------------------------------------------------------------------
    def _compile_all(self):
        if not self.file_rows:
            return
        self.compile_btn.setEnabled(False)
        self.compile_btn.setText("Compiling...")
        for entry in self.file_rows:
            entry.status = "Compiling"
        self._refresh_file_table()

        specs = [
            FileIngestSpec(file_path=e.file_path, division=e.detected_division,
                            header_row_override=e.detected_header_row)
            for e in self.file_rows
        ]
        self._worker = CompileWorker(specs)
        self._worker.finished_ok.connect(self._on_compile_success)
        self._worker.finished_err.connect(self._on_compile_error)
        self._worker.start()

    def _on_compile_success(self, result):
        self.compile_btn.setEnabled(True)
        self.compile_btn.setText("Compile All")

        for entry, log in zip(self.file_rows, result.load_logs):
            entry.row_count = log.rows_read
            entry.status = "Error" if log.notes.startswith("FAILED") else "Compiled"
        self._refresh_file_table()

        self._render_load_log(result.load_logs)

        self.state.mark_compiled(
            compiled_df=result.compiled_df,
            load_logs=result.load_logs,
            total_read=result.total_rows_read,
            total_rejected=result.total_rows_rejected,
            has_warnings=result.has_warnings_or_errors,
        )
        if self.on_compiled_callback:
            self.on_compiled_callback()

        if not result.has_warnings_or_errors:
            self.ack_checkbox.setChecked(True)

    def _on_compile_error(self, msg: str):
        self.compile_btn.setEnabled(True)
        self.compile_btn.setText("Compile All")
        QMessageBox.critical(self, "Compile failed", f"An unexpected error occurred:\n\n{msg}")

    def _on_ack_change(self, _state):
        self.state.warnings_acknowledged = self.ack_checkbox.isChecked()
        self.state.notify()

    # ------------------------------------------------------------------
    def _clear_log_panel(self):
        while self.log_layout.count() > 1:
            item = self.log_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _render_load_log(self, load_logs):
        self._clear_log_panel()
        for log in load_logs:
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)

            header_row = QHBoxLayout()
            div_label = QLabel(f"{log.division}  ({log.file_name})")
            div_label.setStyleSheet("font-weight: 600;")
            header_row.addWidget(div_label)
            header_row.addStretch()

            kind = "ok"
            if log.errors:
                kind = "warning"
            if log.header_confidence in ("low", "error") or log.notes.startswith("FAILED"):
                kind = "error"
            pill = QLabel(f"{log.rows_read:,} rows read  •  {len(log.detected_columns)} columns  •  {len(log.errors):,} warnings")
            pill.setStyleSheet(status_pill_style(kind))
            header_row.addWidget(pill)

            if log.errors:
                details_btn = QPushButton("View Details")
                details_btn.setObjectName("secondaryButton")
                details_btn.setStyleSheet("padding: 3px 10px; font-size: 10px;")
                details_btn.clicked.connect(lambda checked, l=log: self._open_log_detail(l))
                header_row.addWidget(details_btn)

            card_layout.addLayout(header_row)

            detail = QLabel(f"Header row {log.header_row_detected} (confidence: {log.header_confidence})  •  {log.notes}")
            detail.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
            detail.setWordWrap(True)
            card_layout.addWidget(detail)

            if log.detected_columns:
                cols_text = "Columns detected: " + ", ".join(log.detected_columns)
                cols_label = QLabel(cols_text)
                cols_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 10px;")
                cols_label.setWordWrap(True)
                card_layout.addWidget(cols_label)

            if log.errors:
                # Show only a short, grouped-by-column preview inline; the full
                # row-level list (which can run into the thousands) is only
                # rendered on demand via "View Details" above, to keep the
                # Compile screen responsive at large row counts.
                by_column: dict[str, int] = {}
                for e in log.errors:
                    by_column[e.field] = by_column.get(e.field, 0) + 1
                top_cols = sorted(by_column.items(), key=lambda kv: -kv[1])[:5]
                preview_text = "Most affected columns: " + ", ".join(f"{c} ({n:,})" for c, n in top_cols)
                if len(by_column) > 5:
                    preview_text += f"  •  {len(by_column) - 5} more column(s) affected"
                preview_label = QLabel(preview_text)
                preview_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 10px;")
                preview_label.setWordWrap(True)
                card_layout.addWidget(preview_label)

            self.log_layout.insertWidget(self.log_layout.count() - 1, card)

    def _open_log_detail(self, log):
        dialog = LoadLogDetailDialog(log, self)
        dialog.exec()
