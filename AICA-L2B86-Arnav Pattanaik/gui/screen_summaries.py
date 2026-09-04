"""Screen 3: Summaries — dynamic group-by / cross-tab views built from whatever columns exist."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QFrame, QPushButton, QLineEdit,
)
from PyQt6.QtCore import Qt

from core.summaries import classify_columns, group_summary, cross_tab_matrix, overall_totals
from core.query_engine import evaluate_filters, FilterRow, detect_column_type, get_operators_for_type
from gui.excel_filter_dropdown import ExcelFilterDropdown
from gui.app_state import AppState
from gui.styles import COLOR_TEXT_SECONDARY, COLOR_ACCENT


def _fmt_num(val) -> str:
    """Currency-style formatting (commas, 2 decimals) — used for aggregated
    totals in Group Summary / Cross-tab / Overall Totals, where these really
    are sums of money-like measures the user chose."""
    try:
        return f"{val:,.2f}"
    except (TypeError, ValueError):
        return str(val)


def _fmt_cell_value(val) -> str:
    """
    Show the value exactly as it is — no reformatting. A blank/NaN cell
    displays as empty; everything else is shown via its own natural string
    form, whatever type it already is (the ingestion module preserves
    each cell's original type from the source Excel file).
    """
    if val is None:
        return ""
    if isinstance(val, float) and val != val:  # NaN check
        return ""
    return str(val)


class SummaryFilterRowWidget(QFrame):
    def __init__(self, columns: list[str], get_df_fn, on_remove, on_change, parent=None):
        super().__init__(parent)
        self.get_df_fn = get_df_fn
        self.on_remove = on_remove
        self.on_change = on_change

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        self.field_combo = QComboBox()
        self.field_combo.addItems(columns)
        self.field_combo.currentIndexChanged.connect(self._on_field_change)
        layout.addWidget(self.field_combo, 2)

        self.op_combo = QComboBox()
        self.op_combo.currentIndexChanged.connect(self._on_op_change)
        layout.addWidget(self.op_combo, 2)

        # Excel filter dropdown widget
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

        # Update operators based on column type
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

    def update_columns(self, columns: list[str]):
        current = self.field_combo.currentText()
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        self.field_combo.addItems(columns)
        if current in columns:
            self.field_combo.setCurrentText(current)
        self.field_combo.blockSignals(False)
        self._on_field_change()

    def to_filter_row(self) -> FilterRow | None:
        field = self.field_combo.currentText()
        operator = self.op_combo.currentData() or "equals"

        # Check excel dropdown first, otherwise fallback to text edit
        drop_val = self.excel_dropdown.get_selected_text()
        value = drop_val if drop_val else self.value_edit.text().strip()

        # For multi-selection list via dropdown
        if drop_val and len(self.excel_dropdown.get_selected()) > 1:
            operator = "in"

        if not value or not field:
            return None
        return FilterRow(field=field, operator=operator, value=value,
                          secondary_value=self.value2_edit.text().strip() or None)


class ScreenSummaries(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.criteria_widgets: list[SummaryFilterRowWidget] = []
        self._filtered_df = None
        self._columns: list[str] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        title = QLabel("Summaries")
        title.setObjectName("screenTitle")
        outer.addWidget(title)
        subtitle = QLabel(
            "Build summary views from whatever columns your compiled data actually has — "
            "pick what to group by and which numeric column(s) to total."
        )
        subtitle.setObjectName("screenSubtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        self.empty_label = QLabel("No compiled data available. Complete Screen 1 first.")
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; padding: 24px;")
        outer.addWidget(self.empty_label)

        # --- Selection Criteria / Filter Bar ---
        self.criteria_card = QFrame()
        self.criteria_card.setObjectName("card")
        self.criteria_card.setVisible(False)
        criteria_main_layout = QVBoxLayout(self.criteria_card)
        criteria_main_layout.setContentsMargins(12, 10, 12, 10)
        criteria_main_layout.setSpacing(8)

        criteria_header = QHBoxLayout()
        criteria_title = QLabel("Selection Criteria")
        criteria_title.setStyleSheet("font-weight: 600; font-size: 13px;")
        criteria_header.addWidget(criteria_title)
        self.criteria_status_label = QLabel("Showing all rows")
        self.criteria_status_label.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 11px; font-weight: 600;")
        criteria_header.addWidget(self.criteria_status_label)
        criteria_header.addStretch()

        add_criteria_btn = QPushButton("+ Add Criteria")
        add_criteria_btn.setObjectName("secondaryButton")
        add_criteria_btn.clicked.connect(self._add_criteria_row)
        criteria_header.addWidget(add_criteria_btn)

        clear_criteria_btn = QPushButton("Clear Criteria")
        clear_criteria_btn.setObjectName("secondaryButton")
        clear_criteria_btn.clicked.connect(self._clear_criteria)
        criteria_header.addWidget(clear_criteria_btn)

        criteria_main_layout.addLayout(criteria_header)

        self.criteria_rows_container = QWidget()
        self.criteria_rows_layout = QVBoxLayout(self.criteria_rows_container)
        self.criteria_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.criteria_rows_layout.setSpacing(4)
        criteria_main_layout.addWidget(self.criteria_rows_container)

        outer.addWidget(self.criteria_card)

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        outer.addWidget(self.tabs)
        self.tabs.setVisible(False)

        # --- Tab 0: Compiled Data (the raw output of Screen 1, browsable here too) ---
        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        data_control_row = QHBoxLayout()
        self.data_row_count_label = QLabel()
        self.data_row_count_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        data_control_row.addWidget(self.data_row_count_label)
        data_control_row.addStretch()
        data_control_row.addWidget(QLabel("Page:"))
        self.data_page_combo = QComboBox()
        self.data_page_combo.currentIndexChanged.connect(self._refresh_compiled_data_tab)
        data_control_row.addWidget(self.data_page_combo)
        data_layout.addLayout(data_control_row)
        self.compiled_data_table = self._make_table()
        data_layout.addWidget(self.compiled_data_table)
        self.tabs.addTab(data_widget, "Compiled Data")

        # --- Tab 1: Group Summary ---
        group_widget = QWidget()
        group_layout = QVBoxLayout(group_widget)
        control_row = QHBoxLayout()
        control_row.addWidget(QLabel("Group by:"))
        self.group_by_combo = QComboBox()
        self.group_by_combo.currentIndexChanged.connect(self._refresh_group_summary)
        control_row.addWidget(self.group_by_combo)
        control_row.addWidget(QLabel("Total column:"))
        self.measure_combo = QComboBox()
        self.measure_combo.currentIndexChanged.connect(self._refresh_group_summary)
        control_row.addWidget(self.measure_combo)
        control_row.addStretch()
        group_layout.addLayout(control_row)
        self.group_table = self._make_table()
        group_layout.addWidget(self.group_table)
        self.tabs.addTab(group_widget, "Group Summary")

        # --- Tab 2: Cross-tab Matrix ---
        matrix_widget = QWidget()
        matrix_layout = QVBoxLayout(matrix_widget)
        matrix_control_row = QHBoxLayout()
        matrix_control_row.addWidget(QLabel("Rows:"))
        self.matrix_row_combo = QComboBox()
        self.matrix_row_combo.currentIndexChanged.connect(self._refresh_matrix)
        matrix_control_row.addWidget(self.matrix_row_combo)
        matrix_control_row.addWidget(QLabel("Columns:"))
        self.matrix_col_combo = QComboBox()
        self.matrix_col_combo.currentIndexChanged.connect(self._refresh_matrix)
        matrix_control_row.addWidget(self.matrix_col_combo)
        matrix_control_row.addWidget(QLabel("Measure:"))
        self.matrix_measure_combo = QComboBox()
        self.matrix_measure_combo.currentIndexChanged.connect(self._refresh_matrix)
        matrix_control_row.addWidget(self.matrix_measure_combo)
        matrix_control_row.addWidget(QLabel("Aggregation:"))
        self.matrix_agg_combo = QComboBox()
        self.matrix_agg_combo.addItem("Sum", "sum")
        self.matrix_agg_combo.addItem("Count", "count")
        self.matrix_agg_combo.currentIndexChanged.connect(self._refresh_matrix)
        matrix_control_row.addWidget(self.matrix_agg_combo)
        matrix_control_row.addStretch()
        matrix_layout.addLayout(matrix_control_row)
        self.matrix_table = self._make_table()
        matrix_layout.addWidget(self.matrix_table)
        self.tabs.addTab(matrix_widget, "Cross-tab Matrix")

        # --- Tab 3: Overall Totals ---
        totals_widget = QWidget()
        totals_layout = QVBoxLayout(totals_widget)
        self.totals_cards_row = QHBoxLayout()
        totals_layout.addLayout(self.totals_cards_row)
        totals_layout.addStretch()
        self.tabs.addTab(totals_widget, "Overall Totals")

    @staticmethod
    def _make_table() -> QTableWidget:
        t = QTableWidget(0, 0)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return t

    def _add_criteria_row(self):
        cols = list(self.state.compiled_df.columns) if self.state.compiled_df is not None else []
        widget = SummaryFilterRowWidget(cols, get_df_fn=lambda: self.state.compiled_df, on_remove=self._remove_criteria_row, on_change=self._apply_criteria)
        self.criteria_widgets.append(widget)
        self.criteria_rows_layout.addWidget(widget)
        self._apply_criteria()

    def _remove_criteria_row(self, widget: SummaryFilterRowWidget):
        if widget in self.criteria_widgets:
            self.criteria_widgets.remove(widget)
            widget.deleteLater()
            self._apply_criteria()

    def _clear_criteria(self):
        for w in self.criteria_widgets:
            w.deleteLater()
        self.criteria_widgets = []
        self._apply_criteria()

    def _apply_criteria(self, *_):
        df = self.state.compiled_df
        if df is None or df.empty:
            self._filtered_df = None
            return

        filter_rows = [w.to_filter_row() for w in self.criteria_widgets]
        filter_rows = [f for f in filter_rows if f is not None]

        if not filter_rows:
            self._filtered_df = df
            self.criteria_status_label.setText(f"Active Selection: All {len(df):,} rows")
        else:
            try:
                self._filtered_df = evaluate_filters(df, filter_rows)
                pct = (len(self._filtered_df) / len(df)) * 100 if len(df) > 0 else 0
                self.criteria_status_label.setText(
                    f"Active Selection: {len(self._filtered_df):,} of {len(df):,} rows ({pct:.1f}%)"
                )
            except Exception as exc:
                self.criteria_status_label.setText(f"Filter error: {exc}")
                self._filtered_df = df

        numeric_cols, categorical_cols = classify_columns(self._filtered_df)
        self._refresh_group_summary()
        self._refresh_matrix()
        self._refresh_totals(self._filtered_df, numeric_cols)
        self._setup_compiled_data_tab(self._filtered_df)

    def refresh(self):
        df = self.state.compiled_df
        if df is None or df.empty:
            self.empty_label.setVisible(True)
            self.criteria_card.setVisible(False)
            self.tabs.setVisible(False)
            return
        self.empty_label.setVisible(False)
        self.criteria_card.setVisible(True)
        self.tabs.setVisible(True)

        new_columns = list(df.columns)
        if new_columns != self._columns:
            self._columns = new_columns
            for w in self.criteria_widgets:
                w.update_columns(new_columns)

        numeric_cols, categorical_cols = classify_columns(df)

        self._populate_combo(self.group_by_combo, categorical_cols)
        self._populate_combo(self.measure_combo, numeric_cols)
        self._populate_combo(self.matrix_row_combo, categorical_cols)
        self._populate_combo(self.matrix_col_combo, categorical_cols)
        self._populate_combo(self.matrix_measure_combo, numeric_cols)

        # Default the matrix column-selector to a different column than the
        # row-selector when possible, so the first render isn't row==col.
        if len(categorical_cols) > 1 and self.matrix_col_combo.currentText() == self.matrix_row_combo.currentText():
            self.matrix_col_combo.setCurrentIndex(1)

        self._apply_criteria()

    @staticmethod
    def _populate_combo(combo: QComboBox, items: list[str]):
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(items)
        if current in items:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _refresh_group_summary(self, *_):
        df = getattr(self, "_filtered_df", None)
        if df is None:
            df = self.state.compiled_df
        if df is None or df.empty:
            self.group_table.setRowCount(0)
            self.group_table.setColumnCount(0)
            return
        group_col = self.group_by_combo.currentText()
        measure_col = self.measure_combo.currentText()
        if not group_col:
            self.group_table.setRowCount(0)
            self.group_table.setColumnCount(0)
            return

        measures = [measure_col] if measure_col else None
        summ = group_summary(df, group_col, measures)
        if summ.empty:
            self.group_table.setRowCount(0)
            self.group_table.setColumnCount(0)
            return

        cols = list(summ.columns)
        self.group_table.setColumnCount(len(cols))
        self.group_table.setHorizontalHeaderLabels(cols)
        self.group_table.setRowCount(len(summ))
        for r in range(len(summ)):
            for c, col in enumerate(cols):
                val = summ.iloc[r][col]
                text = _fmt_num(val) if col != group_col and col != "Row Count" else str(val)
                item = QTableWidgetItem(text)
                if col != group_col:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.group_table.setItem(r, c, item)

    def _refresh_matrix(self, *_):
        df = getattr(self, "_filtered_df", None)
        if df is None:
            df = self.state.compiled_df
        if df is None or df.empty:
            self.matrix_table.setRowCount(0)
            self.matrix_table.setColumnCount(0)
            return
        row_col = self.matrix_row_combo.currentText()
        col_col = self.matrix_col_combo.currentText()
        measure_col = self.matrix_measure_combo.currentText()
        agg = self.matrix_agg_combo.currentData() or "sum"

        if not row_col or not col_col or not measure_col:
            self.matrix_table.setRowCount(0)
            self.matrix_table.setColumnCount(0)
            return

        if row_col == col_col:
            self.matrix_table.setRowCount(0)
            self.matrix_table.setColumnCount(1)
            self.matrix_table.setHorizontalHeaderLabels(["Notice"])
            self.matrix_table.setRowCount(1)
            self.matrix_table.setItem(0, 0, QTableWidgetItem("Choose two different columns for Rows and Columns."))
            return

        matrix = cross_tab_matrix(df, row_col, col_col, measure_col, agg)
        rows, columns = matrix["rows"], matrix["columns"]
        if not rows or not columns:
            self.matrix_table.setRowCount(0)
            self.matrix_table.setColumnCount(0)
            return

        self.matrix_table.setColumnCount(len(columns) + 2)
        self.matrix_table.setHorizontalHeaderLabels([row_col] + columns + ["Row Total"])
        self.matrix_table.setRowCount(len(rows) + 1)

        for r, rowval in enumerate(rows):
            self.matrix_table.setItem(r, 0, QTableWidgetItem(rowval))
            for c, colval in enumerate(columns, start=1):
                val = matrix["values"][rowval][colval]
                item = QTableWidgetItem(_fmt_num(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.matrix_table.setItem(r, c, item)
            total_item = QTableWidgetItem(_fmt_num(matrix["rowTotals"][rowval]))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            font = total_item.font()
            font.setBold(True)
            total_item.setFont(font)
            self.matrix_table.setItem(r, len(columns) + 1, total_item)

        gt_row = len(rows)
        self.matrix_table.setItem(gt_row, 0, QTableWidgetItem("Column Total"))
        for c, colval in enumerate(columns, start=1):
            item = QTableWidgetItem(_fmt_num(matrix["colTotals"][colval]))
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.matrix_table.setItem(gt_row, c, item)
        gt_item = QTableWidgetItem(_fmt_num(matrix["grandTotal"]))
        gt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.matrix_table.setItem(gt_row, len(columns) + 1, gt_item)

    def _refresh_totals(self, df, numeric_cols):
        while self.totals_cards_row.count():
            item = self.totals_cards_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        totals = overall_totals(df, numeric_cols)

        row_card = QFrame()
        row_card.setObjectName("card")
        rc_layout = QVBoxLayout(row_card)
        v = QLabel(f"{totals['totalRows']:,}")
        v.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {COLOR_ACCENT};")
        l = QLabel("Total Rows")
        l.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        rc_layout.addWidget(v)
        rc_layout.addWidget(l)
        self.totals_cards_row.addWidget(row_card)

        for col, total in totals["totals"].items():
            card = QFrame()
            card.setObjectName("card")
            cl = QVBoxLayout(card)
            v = QLabel(_fmt_num(total))
            v.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLOR_ACCENT};")
            l = QLabel(col)
            l.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
            l.setWordWrap(True)
            cl.addWidget(v)
            cl.addWidget(l)
            self.totals_cards_row.addWidget(card)

        self.totals_cards_row.addStretch()

    # ------------------------------------------------------------------
    # Compiled Data tab — paginated raw view of Screen 1's output
    # ------------------------------------------------------------------
    MAX_CELLS_PER_PAGE = 40_000  # keeps rendering responsive regardless of column count

    def _setup_compiled_data_tab(self, df):
        self._compiled_data_df = df
        self._compiled_data_rendered = False  # lazy: only render once the tab is actually opened
        n_cols = max(1, len(df.columns))
        page_size = max(50, self.MAX_CELLS_PER_PAGE // n_cols)
        self._compiled_data_page_size = page_size

        total_rows = len(df)
        n_pages = max(1, (total_rows + page_size - 1) // page_size)

        self.data_page_combo.blockSignals(True)
        self.data_page_combo.clear()
        for p in range(n_pages):
            start = p * page_size + 1
            end = min((p + 1) * page_size, total_rows)
            self.data_page_combo.addItem(f"Rows {start:,}–{end:,}")
        self.data_page_combo.blockSignals(False)

        self.data_row_count_label.setText(
            f"{total_rows:,} total rows  •  {len(df.columns)} columns  •  {page_size:,} rows per page"
        )
        # Don't render yet — wait for the tab to actually be selected (see
        # _on_tab_changed), since Summaries.refresh() runs on every
        # navigation to this screen and eagerly rendering 40k+ cells here
        # even when the user is looking at a different tab is what caused
        # the UI freeze on wide (170+ column) real files.
        if self.tabs.currentIndex() == 0:
            self._refresh_compiled_data_tab()

    def _on_tab_changed(self, index: int):
        if index == 0 and not getattr(self, "_compiled_data_rendered", False):
            self._refresh_compiled_data_tab()

    def _refresh_compiled_data_tab(self, *_):
        df = getattr(self, "_compiled_data_df", None)
        if df is None or df.empty:
            self.compiled_data_table.setRowCount(0)
            self.compiled_data_table.setColumnCount(0)
            return

        page_size = getattr(self, "_compiled_data_page_size", 500)
        page = max(0, self.data_page_combo.currentIndex())
        start = page * page_size
        end = start + page_size
        page_df = df.iloc[start:end]

        # Performance: disable repainting/sorting while we bulk-populate —
        # QTableWidget recalculates layout on every setItem() call otherwise,
        # which is what made this freeze the UI at 170+ columns x 500 rows.
        self.compiled_data_table.setUpdatesEnabled(False)
        self.compiled_data_table.setSortingEnabled(False)

        self.compiled_data_table.setColumnCount(len(page_df.columns))
        self.compiled_data_table.setHorizontalHeaderLabels([str(c) for c in page_df.columns])
        self.compiled_data_table.setRowCount(len(page_df))

        # .values is a single numpy array pull for the whole page — far
        # fewer, cheaper accesses than calling .iloc[r, c] repeatedly.
        values = page_df.values
        for r in range(values.shape[0]):
            row = values[r]
            for c in range(values.shape[1]):
                item = QTableWidgetItem(_fmt_cell_value(row[c]))
                self.compiled_data_table.setItem(r, c, item)

        self.compiled_data_table.setUpdatesEnabled(True)
        self.compiled_data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._compiled_data_rendered = True
