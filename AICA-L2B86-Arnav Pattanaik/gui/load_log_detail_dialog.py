"""
Load-log detail dialog — shows the full list of warnings/errors for one
compiled file, grouped by column so a file with thousands of warnings
concentrated in a handful of columns (e.g. alphanumeric ID columns that
were mostly-numeric and got coerced) is still scannable at a glance,
with the option to drill into the full row-level list per column.
"""

from collections import defaultdict

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QComboBox, QAbstractItemView,
)
from PyQt6.QtCore import Qt

from gui.styles import COLOR_TEXT_SECONDARY, status_pill_style


class LoadLogDetailDialog(QDialog):
    def __init__(self, log, parent=None):
        super().__init__(parent)
        self.log = log
        self.setWindowTitle(f"Load Log Detail — {log.division} ({log.file_name})")
        self.resize(900, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel(f"{log.division}  —  {log.file_name}")
        title.setObjectName("screenTitle")
        layout.addWidget(title)

        summary = QLabel(
            f"{log.rows_read:,} rows read  •  {len(log.detected_columns)} columns detected  •  "
            f"{len(log.errors):,} warning(s)/error(s)  •  "
            f"header row {log.header_row_detected} (confidence: {log.header_confidence})"
        )
        summary.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        if log.notes and log.notes != "OK":
            notes_label = QLabel(log.notes)
            notes_label.setStyleSheet(status_pill_style("warning"))
            notes_label.setWordWrap(True)
            layout.addWidget(notes_label)

        # --- Group warnings by column so the user sees which columns are
        # actually affected, rather than scrolling through thousands of
        # rows one at a time ---
        by_column: dict[str, list] = defaultdict(list)
        for e in log.errors:
            by_column[e.field].append(e)

        if by_column:
            filter_row = QHBoxLayout()
            filter_row.addWidget(QLabel("Filter by column:"))
            self.column_filter = QComboBox()
            self.column_filter.addItem(f"All columns ({len(log.errors):,} total)", None)
            for col, items in sorted(by_column.items(), key=lambda kv: -len(kv[1])):
                self.column_filter.addItem(f"{col}  ({len(items):,})", col)
            self.column_filter.currentIndexChanged.connect(self._refresh_table)
            filter_row.addWidget(self.column_filter, 1)
            layout.addLayout(filter_row)

            self._by_column = by_column
            self.detail_table = QTableWidget(0, 4)
            self.detail_table.setHorizontalHeaderLabels(["Row #", "Column", "Issue", "Raw Value"])
            self.detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            self.detail_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            self.detail_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            self.detail_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            self.detail_table.verticalHeader().setVisible(False)
            self.detail_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.detail_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.detail_table.setSortingEnabled(True)
            layout.addWidget(self.detail_table, 1)

            self._refresh_table()
        else:
            no_errors = QLabel("No warnings or errors for this file.")
            no_errors.setStyleSheet(status_pill_style("ok"))
            layout.addWidget(no_errors)
            layout.addStretch()

        if log.detected_columns:
            cols_label = QLabel("Columns detected: " + ", ".join(log.detected_columns))
            cols_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 10px;")
            cols_label.setWordWrap(True)
            layout.addWidget(cols_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primaryButton")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _refresh_table(self, *_):
        selected_col = self.column_filter.currentData()
        if selected_col is None:
            rows = self.log.errors
        else:
            rows = self._by_column.get(selected_col, [])

        # Cap the rendered rows for UI responsiveness at very large counts;
        # the column filter lets the user narrow down instead of scrolling
        # through everything at once.
        MAX_RENDER = 2000
        display_rows = rows[:MAX_RENDER]

        self.detail_table.setSortingEnabled(False)
        self.detail_table.setRowCount(len(display_rows))
        for i, e in enumerate(display_rows):
            self.detail_table.setItem(i, 0, QTableWidgetItem(str(e.row_number)))
            self.detail_table.setItem(i, 1, QTableWidgetItem(e.field))
            issue_item = QTableWidgetItem(f"[{e.severity}] {e.issue}")
            self.detail_table.setItem(i, 2, issue_item)
            self.detail_table.setItem(i, 3, QTableWidgetItem(str(e.raw_value)))
        self.detail_table.setSortingEnabled(True)

        if len(rows) > MAX_RENDER:
            self.setWindowTitle(
                f"Load Log Detail — {self.log.division} ({self.log.file_name}) "
                f"[showing first {MAX_RENDER:,} of {len(rows):,}]"
            )
