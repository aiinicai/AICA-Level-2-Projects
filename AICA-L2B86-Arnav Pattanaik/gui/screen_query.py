"""Screen 4: Query Builder — multi-criteria filter built from whatever columns exist."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QComboBox,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox, QScrollArea,
)

from core.query_engine import evaluate_filters, FilterRow, detect_column_type, get_operators_for_type
from core.export_engine import export_filtered_list_to_excel, default_filtered_filename
from gui.excel_filter_dropdown import ExcelFilterDropdown
from gui.app_state import AppState
from gui.styles import COLOR_TEXT_SECONDARY


class FilterRowWidget(QFrame):
    def __init__(self, columns: list[str], get_df_fn, on_remove, on_change, parent=None):
        super().__init__(parent)
        self.get_df_fn = get_df_fn
        self.on_remove = on_remove
        self.on_change = on_change

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.field_combo = QComboBox()
        self.field_combo.addItems(columns)
        self.field_combo.currentIndexChanged.connect(self._on_field_change)
        layout.addWidget(self.field_combo, 2)

        self.op_combo = QComboBox()
        self.op_combo.currentIndexChanged.connect(self._on_op_change)
        layout.addWidget(self.op_combo, 2)

        self.excel_dropdown = ExcelFilterDropdown()
        self.excel_dropdown.selection_changed.connect(self.on_change)
        layout.addWidget(self.excel_dropdown, 2)

        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("or type value...")
        self.value_edit.textChanged.connect(self.on_change)
        layout.addWidget(self.value_edit, 2)

        self.value2_edit = QLineEdit()
        self.value2_edit.setPlaceholderText("and date/value...")
        self.value2_edit.setVisible(False)
        self.value2_edit.textChanged.connect(self.on_change)
        layout.addWidget(self.value2_edit, 1)

        remove_btn = QPushButton("✕")
        remove_btn.setObjectName("secondaryButton")
        remove_btn.setFixedWidth(32)
        remove_btn.clicked.connect(lambda: self.on_remove(self))
        layout.addWidget(remove_btn)

        self._on_field_change()

    def _on_field_change(self, *_):
        col = self.field_combo.currentText()
        df = self.get_df_fn()

        if df is not None and not df.empty and col in df.columns:
            col_type = detect_column_type(df[col], col)
            unique_vals = list(df[col].dropna().unique())
            self.excel_dropdown.set_items(unique_vals)
        else:
            col_type = "text"
            self.excel_dropdown.set_items([])

        ops = get_operators_for_type(col_type)
        self.op_combo.blockSignals(True)
        self.op_combo.clear()
        for key, label in ops:
            self.op_combo.addItem(label, key)
        self.op_combo.blockSignals(False)

        self._on_op_change()

    def _on_op_change(self, *_):
        op = self.op_combo.currentData()
        self.value2_edit.setVisible(op in ("between", "date_between"))
        self.on_change()

    def to_filter_row(self) -> FilterRow | None:
        field = self.field_combo.currentText()
        operator = self.op_combo.currentData() or "equals"

        drop_val = self.excel_dropdown.get_selected_text()
        value = drop_val if drop_val else self.value_edit.text().strip()

        if drop_val and len(self.excel_dropdown.get_selected()) > 1:
            operator = "in"

        if not value or not field:
            return None
        return FilterRow(field=field, operator=operator, value=value,
                          secondary_value=self.value2_edit.text().strip() or None)


class ScreenQueryBuilder(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.filter_widgets: list[FilterRowWidget] = []
        self._output_dir = str(Path.home() / "Downloads")
        self._columns: list[str] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        title = QLabel("Query Builder")
        title.setObjectName("screenTitle")
        outer.addWidget(title)
        subtitle = QLabel("Filter the compiled data by any column (combined with AND).")
        subtitle.setObjectName("screenSubtitle")
        outer.addWidget(subtitle)

        self.empty_label = QLabel("No compiled data available. Complete Screen 1 first.")
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; padding: 24px;")
        outer.addWidget(self.empty_label)

        self.body = QWidget()
        body_layout = QHBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.body)
        self.body.setVisible(False)

        left_panel = QFrame()
        left_panel.setObjectName("card")
        left_panel.setFixedWidth(360)
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Filters"))

        self.filters_scroll = QScrollArea()
        self.filters_scroll.setWidgetResizable(True)
        self.filters_container = QWidget()
        self.filters_layout = QVBoxLayout(self.filters_container)
        self.filters_layout.addStretch()
        self.filters_scroll.setWidget(self.filters_container)
        left_layout.addWidget(self.filters_scroll)

        btn_row = QHBoxLayout()
        add_filter_btn = QPushButton("+ Add Filter")
        add_filter_btn.setObjectName("secondaryButton")
        add_filter_btn.clicked.connect(lambda: self._add_filter_row())
        btn_row.addWidget(add_filter_btn)
        clear_btn = QPushButton("Clear All")
        clear_btn.setObjectName("secondaryButton")
        clear_btn.clicked.connect(self._clear_filters)
        btn_row.addWidget(clear_btn)
        left_layout.addLayout(btn_row)

        body_layout.addWidget(left_panel)

        right_panel = QVBoxLayout()
        result_header = QHBoxLayout()
        self.match_count_label = QLabel("0 rows match")
        self.match_count_label.setStyleSheet("font-weight: 600;")
        result_header.addWidget(self.match_count_label)
        result_header.addStretch()
        right_panel.addLayout(result_header)

        self.results_table = QTableWidget(0, 0)
        self.results_table.verticalHeader().setVisible(False)
        right_panel.addWidget(self.results_table)

        export_row = QHBoxLayout()
        export_btn = QPushButton("Export Filtered List to Excel")
        export_btn.setObjectName("primaryButton")
        export_btn.clicked.connect(self._export_filtered)
        export_row.addWidget(export_btn)
        export_row.addStretch()
        right_panel.addLayout(export_row)

        self.export_result_label = QLabel()
        right_panel.addWidget(self.export_result_label)

        body_layout.addLayout(right_panel)

        self._filtered_df = None

    def refresh(self):
        df = self.state.compiled_df
        has_data = df is not None and not df.empty
        self.empty_label.setVisible(not has_data)
        self.body.setVisible(has_data)
        if not has_data:
            return

        new_columns = list(df.columns)
        if new_columns != self._columns:
            self._columns = new_columns
            self._clear_filters()
            self._add_filter_row()
        self._apply_filters()

    def _add_filter_row(self):
        widget = FilterRowWidget(self._columns, get_df_fn=lambda: self.state.compiled_df, on_remove=self._remove_filter_row, on_change=self._apply_filters)
        self.filter_widgets.append(widget)
        self.filters_layout.insertWidget(self.filters_layout.count() - 1, widget)
        self._apply_filters()

    def _remove_filter_row(self, widget: FilterRowWidget):
        if widget in self.filter_widgets:
            self.filter_widgets.remove(widget)
            widget.deleteLater()
            self._apply_filters()

    def _clear_filters(self):
        for w in self.filter_widgets:
            w.deleteLater()
        self.filter_widgets = []
        self._apply_filters()

    def _apply_filters(self, *_):
        df = self.state.compiled_df
        if df is None or df.empty:
            return
        filter_rows = [w.to_filter_row() for w in self.filter_widgets]
        filter_rows = [f for f in filter_rows if f is not None]

        try:
            result = evaluate_filters(df, filter_rows)
        except Exception as exc:
            self.match_count_label.setText(f"Filter error: {exc}")
            return

        self._filtered_df = result
        self.match_count_label.setText(f"{len(result):,} rows match")
        self._render_results(result)

    def _render_results(self, df):
        import pandas as pd
        preview = df.head(500)
        
        self.results_table.setUpdatesEnabled(False)
        self.results_table.setSortingEnabled(False)

        self.results_table.setColumnCount(len(preview.columns))
        self.results_table.setHorizontalHeaderLabels([str(c) for c in preview.columns])
        self.results_table.setRowCount(len(preview))

        values = preview.values
        for r in range(values.shape[0]):
            row = values[r]
            for c in range(values.shape[1]):
                val = row[c]
                text = "" if (val is None or (isinstance(val, float) and pd.isna(val))) else str(val)
                self.results_table.setItem(r, c, QTableWidgetItem(text))

        self.results_table.setUpdatesEnabled(True)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

    def _export_filtered(self):
        if self._filtered_df is None or self._filtered_df.empty:
            QMessageBox.information(self, "Nothing to export", "No rows match the current filters.")
            return
        folder = QFileDialog.getExistingDirectory(self, "Choose destination folder", self._output_dir)
        if not folder:
            return
        self._output_dir = folder
        filename = default_filtered_filename()
        output_path = str(Path(folder) / filename)
        try:
            export_filtered_list_to_excel(self._filtered_df, output_path)
            self.export_result_label.setText(f"✓ Exported {len(self._filtered_df):,} rows to {output_path}")
        except Exception as exc:
            self.export_result_label.setText(f"✗ Export failed: {exc}")
