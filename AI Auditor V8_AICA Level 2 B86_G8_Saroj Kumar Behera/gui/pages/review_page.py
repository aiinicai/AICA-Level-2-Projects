"""
AI Auditor V8 - Financial Data Review & Manual Mapping Page
Allows the auditor to review extracted data, edit figures, override taxonomy classifications, and add custom lines.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QComboBox, QHeaderView,
    QMessageBox, QInputDialog, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from core.models import FinancialModel, LineItem
from analysis.mapper import TaxonomyMapper
from analysis.ratio_engine import RatioEngine
from analysis.variance_engine import VarianceEngine
from analysis.risk_engine import RiskEngine
from config.constants import BS_TAXONOMY, PL_TAXONOMY, CF_TAXONOMY

class ReviewPage(QWidget):
    data_recalculated = pyqtSignal(object)  # Emits updated FinancialModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model: FinancialModel = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        header_vbox = QVBoxLayout()
        lbl_title = QLabel("Financial Data Review & Taxonomy Mapping")
        lbl_title.setProperty("class", "page-title")
        lbl_sub = QLabel("Review extracted figures, adjust taxonomy mappings, and correct values before generating reports.")
        lbl_sub.setProperty("class", "page-subtitle")
        header_vbox.addWidget(lbl_title)
        header_vbox.addWidget(lbl_sub)
        top_bar.addLayout(header_vbox)
        top_bar.addStretch()

        self.btn_recalculate = QPushButton("Save Adjustments & Recalculate")
        self.btn_recalculate.setProperty("class", "primary-btn")
        self.btn_recalculate.clicked.connect(self._recalculate_all)
        top_bar.addWidget(self.btn_recalculate)
        main_layout.addLayout(top_bar)

        # Statement Tabs
        self.tabs = QTabWidget()
        self.table_bs = self._create_editable_table("Balance Sheet")
        self.table_pl = self._create_editable_table("Profit and Loss")
        self.table_cf = self._create_editable_table("Cash Flow Statement")

        self.tabs.addTab(self.table_bs, "Balance Sheet")
        self.tabs.addTab(self.table_pl, "Profit & Loss")
        self.tabs.addTab(self.table_cf, "Cash Flow Statement")
        main_layout.addWidget(self.tabs)

        # Bottom actions
        bot_bar = QHBoxLayout()
        btn_add_row = QPushButton("+ Add Custom Line Item")
        btn_add_row.setProperty("class", "secondary-btn")
        btn_add_row.clicked.connect(self._add_custom_row)
        bot_bar.addWidget(btn_add_row)
        bot_bar.addStretch()
        main_layout.addLayout(bot_bar)

    def _create_editable_table(self, stmt_type: str) -> QTableWidget:
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setShowGrid(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        return table

    def load_model(self, model: FinancialModel):
        self.model = model
        self._populate_table(self.table_bs, model.balance_sheet, BS_TAXONOMY)
        self._populate_table(self.table_pl, model.profit_loss, PL_TAXONOMY)
        self._populate_table(self.table_cf, model.cash_flow, CF_TAXONOMY)

    def _populate_table(self, table: QTableWidget, stmt, taxonomy: dict):
        periods = stmt.periods if stmt.periods else self.model.periods
        headers = ["Line Item / Particulars", "Standard Classification (Taxonomy)"] + periods + ["Confidence"]
        
        table.clear()
        table.setColumnCount(len(headers))
        table.setRowCount(len(stmt.line_items))
        table.setHorizontalHeaderLabels(headers)

        options = TaxonomyMapper.get_taxonomy_labels_for_statement(stmt.statement_type)

        for r_idx, item in enumerate(stmt.line_items):
            # Particulars (Editable)
            c_name = QTableWidgetItem(item.original_name)
            table.setItem(r_idx, 0, c_name)

            # Taxonomy Dropdown
            combo = QComboBox()
            for key, label in options:
                combo.addItem(label, key)
            
            # Select matching option
            match_idx = 0
            if item.standard_key:
                for opt_idx, (k, _) in enumerate(options):
                    if k == item.standard_key:
                        match_idx = opt_idx
                        break
            combo.setCurrentIndex(match_idx)
            table.setCellWidget(r_idx, 1, combo)

            # Period values (Editable)
            for p_idx, p in enumerate(periods, 2):
                val = item.get_value(p, 0.0)
                c_val = QTableWidgetItem(f"{val:.2f}")
                c_val.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(r_idx, p_idx, c_val)

            # Confidence score
            score_txt = f"{int(item.confidence_score * 100)}%" if item.confidence_score else "Manual"
            c_score = QTableWidgetItem(score_txt)
            c_score.setTextAlignment(Qt.AlignCenter)
            c_score.setFlags(Qt.ItemIsEnabled)  # Read-only
            table.setItem(r_idx, len(headers) - 1, c_score)

        table.resizeColumnsToContents()
        table.setColumnWidth(0, 320)
        table.setColumnWidth(1, 300)

    def _add_custom_row(self):
        if not self.model:
            return
        
        current_tab_idx = self.tabs.currentIndex()
        if current_tab_idx == 0:
            stmt = self.model.balance_sheet
            tbl = self.table_bs
            tax = BS_TAXONOMY
        elif current_tab_idx == 1:
            stmt = self.model.profit_loss
            tbl = self.table_pl
            tax = PL_TAXONOMY
        else:
            stmt = self.model.cash_flow
            tbl = self.table_cf
            tax = CF_TAXONOMY

        name, ok = QInputDialog.getText(self, "Add Line Item", "Enter new line item particulars:")
        if ok and name.strip():
            periods = stmt.periods if stmt.periods else self.model.periods
            val_dict = {p: 0.0 for p in periods}
            new_item = LineItem(original_name=name.strip(), statement_type=stmt.statement_type, values=val_dict, confidence_score=1.0, user_overridden=True)
            stmt.line_items.append(new_item)
            self._populate_table(tbl, stmt, tax)

    def _recalculate_all(self):
        if not self.model:
            return

        # 1. Update Balance Sheet from Table
        self._sync_table_to_statement(self.table_bs, self.model.balance_sheet)
        # 2. Update P&L from Table
        self._sync_table_to_statement(self.table_pl, self.model.profit_loss)
        # 3. Update Cash Flow from Table
        self._sync_table_to_statement(self.table_cf, self.model.cash_flow)

        # 4. Recompute Ratios, Trends, Variances & Risks
        RatioEngine.calculate_all_ratios(self.model)
        VarianceEngine.analyze_variations(self.model, threshold_pct=5.0)
        RiskEngine.evaluate_risks(self.model)

        self.data_recalculated.emit(self.model)
        QMessageBox.information(self, "Success", "All adjustments saved! Ratios, variances, and audit checklists have been recalculated.")

    def _sync_table_to_statement(self, table: QTableWidget, stmt):
        periods = stmt.periods if stmt.periods else self.model.periods
        for r in range(table.rowCount()):
            if r < len(stmt.line_items):
                item = stmt.line_items[r]
                # Particulars
                name_cell = table.item(r, 0)
                if name_cell:
                    item.original_name = name_cell.text().strip()

                # Standard Key from Dropdown
                combo = table.cellWidget(r, 1)
                if isinstance(combo, QComboBox):
                    selected_key = combo.currentData()
                    if selected_key and selected_key != "unclassified":
                        item.standard_key = selected_key
                        item.user_overridden = True

                # Values
                for p_idx, p in enumerate(periods, 2):
                    val_cell = table.item(r, p_idx)
                    if val_cell:
                        try:
                            num = float(val_cell.text().replace(",", "").strip())
                            item.set_value(p, num)
                        except ValueError:
                            pass
