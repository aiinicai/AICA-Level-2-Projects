"""Screen 5: Energy Charge Audit & Verification — compares billed EC against OERC slab formulas."""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QComboBox,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from core.energy_charge_calculator import run_energy_charge_audit, find_column_by_candidates
from core.export_engine import export_filtered_list_to_excel
from gui.app_state import AppState
from gui.styles import COLOR_TEXT_SECONDARY, COLOR_ACCENT, COLOR_ERROR, COLOR_SUCCESS


def _fmt_num(val) -> str:
    try:
        return f"{val:,.2f}"
    except (TypeError, ValueError):
        return str(val)


class ScreenEnergyAudit(QWidget):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self._output_dir = str(Path.home() / "Downloads")
        self._discrepancy_df = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        title = QLabel("Energy Charge Audit")
        title.setObjectName("screenTitle")
        outer.addWidget(title)
        subtitle = QLabel(
            "Verify billed energy charges against official OERC tariff slab rates. "
            "Computes expected charges and highlights ONLY rows with tariff discrepancies."
        )
        subtitle.setObjectName("screenSubtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        self.empty_label = QLabel("No compiled data available. Complete Screen 1 first.")
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; padding: 24px;")
        outer.addWidget(self.empty_label)

        self.body = QWidget()
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(12)

        # Control card
        control_card = QFrame()
        control_card.setObjectName("card")
        control_layout = QHBoxLayout(control_card)
        control_layout.setContentsMargins(12, 10, 12, 10)
        control_layout.setSpacing(10)

        control_layout.addWidget(QLabel("Tariff Category:"))
        self.cat_combo = QComboBox()
        self.cat_combo.addItem("All Categories", "All")
        control_layout.addWidget(self.cat_combo, 2)

        control_layout.addWidget(QLabel("Tolerance Threshold (₹):"))
        self.tolerance_spin = QDoubleSpinBox()
        self.tolerance_spin.setRange(0.0, 100.0)
        self.tolerance_spin.setDecimals(2)
        self.tolerance_spin.setValue(1.00)
        control_layout.addWidget(self.tolerance_spin, 1)

        run_btn = QPushButton("Run Energy Charge Audit")
        run_btn.setObjectName("primaryButton")
        run_btn.clicked.connect(self._run_audit)
        control_layout.addWidget(run_btn)

        control_layout.addStretch()
        body_layout.addWidget(control_card)

        # Metrics cards row
        self.metrics_row = QHBoxLayout()
        self.metrics_row.setSpacing(10)
        body_layout.addLayout(self.metrics_row)

        # Results header
        result_header = QHBoxLayout()
        self.status_label = QLabel("Click 'Run Energy Charge Audit' to verify billed charges.")
        self.status_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        result_header.addWidget(self.status_label)
        result_header.addStretch()

        export_btn = QPushButton("Export Discrepancies to Excel")
        export_btn.setObjectName("primaryButton")
        export_btn.clicked.connect(self._export_discrepancies)
        result_header.addWidget(export_btn)

        body_layout.addLayout(result_header)

        # Discrepancy table
        self.results_table = QTableWidget(0, 0)
        self.results_table.verticalHeader().setVisible(False)
        body_layout.addWidget(self.results_table)

        self.export_result_label = QLabel()
        body_layout.addWidget(self.export_result_label)

        outer.addWidget(self.body)
        self.body.setVisible(False)

    def refresh(self):
        df = self.state.compiled_df
        has_data = df is not None and not df.empty
        self.empty_label.setVisible(not has_data)
        self.body.setVisible(has_data)

        if not has_data:
            return

        cat_col = find_column_by_candidates(df, ["CAT_CODE", "TARIFF", "RATE_CATEGORY", "CATEGORY"])
        self.cat_combo.blockSignals(True)
        self.cat_combo.clear()
        self.cat_combo.addItem("All Categories", "All")
        if cat_col and cat_col in df.columns:
            unique_cats = sorted([str(c) for c in df[cat_col].dropna().unique() if str(c).strip()])
            for c in unique_cats:
                self.cat_combo.addItem(c, c)
        self.cat_combo.blockSignals(False)

        self._run_audit()

    def _run_audit(self):
        df = self.state.compiled_df
        if df is None or df.empty:
            return

        selected_cat = self.cat_combo.currentData() or "All"
        tolerance = self.tolerance_spin.value()

        try:
            discrepancy_df, metrics = run_energy_charge_audit(df, selected_cat, tolerance)
        except Exception as exc:
            QMessageBox.warning(self, "Audit Error", str(exc))
            return

        self._discrepancy_df = discrepancy_df
        self._render_metrics(metrics)
        self._render_table(discrepancy_df)

    def _render_metrics(self, metrics: dict):
        while self.metrics_row.count():
            item = self.metrics_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cards = [
            ("Total Audited Rows", f"{metrics['total_audited']:,}", COLOR_ACCENT),
            ("Mismatched Rows", f"{metrics['total_mismatched']:,} ({metrics['mismatch_pct']:.1f}%)", COLOR_ERROR if metrics['total_mismatched'] > 0 else COLOR_SUCCESS),
            ("Under-Billed Amount", f"₹ {_fmt_num(metrics['underbilled_amt'])}", COLOR_ERROR),
            ("Over-Billed Amount", f"₹ {_fmt_num(metrics['overbilled_amt'])}", COLOR_ACCENT),
        ]

        for title, val, color in cards:
            card = QFrame()
            card.setObjectName("card")
            cl = QVBoxLayout(card)
            v = QLabel(val)
            v.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {color};")
            l = QLabel(title)
            l.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
            cl.addWidget(v)
            cl.addWidget(l)
            self.metrics_row.addWidget(card)

        if metrics["total_mismatched"] == 0:
            self.status_label.setText("✓ All audited rows match expected tariff calculations perfectly!")
        else:
            self.status_label.setText(
                f"⚠ Found {metrics['total_mismatched']:,} rows with energy charge discrepancies "
                f"(Total difference: ₹ {_fmt_num(metrics['net_discrepancy_amt'])})"
            )

    def _render_table(self, df):
        if df is None or df.empty:
            self.results_table.setRowCount(0)
            self.results_table.setColumnCount(0)
            return

        preview = df.head(1000)
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
                text = _fmt_num(val) if isinstance(val, (int, float)) else ("" if val is None else str(val))
                item = QTableWidgetItem(text)
                if isinstance(val, (int, float)):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.results_table.setItem(r, c, item)

        self.results_table.setUpdatesEnabled(True)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

    def _export_discrepancies(self):
        if self._discrepancy_df is None or self._discrepancy_df.empty:
            QMessageBox.information(self, "Nothing to export", "No discrepancy rows found.")
            return

        folder = QFileDialog.getExistingDirectory(self, "Choose destination folder", self._output_dir)
        if not folder:
            return
        self._output_dir = folder
        output_path = str(Path(folder) / "Energy_Charge_Discrepancies_Report.xlsx")
        try:
            export_filtered_list_to_excel(self._discrepancy_df, output_path)
            self.export_result_label.setText(f"✓ Exported {len(self._discrepancy_df):,} discrepancy rows to {output_path}")
        except Exception as exc:
            self.export_result_label.setText(f"✗ Export failed: {exc}")
