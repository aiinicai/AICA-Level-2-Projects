"""Screen 4: Executive Tabbed Results Screen with ratio guidance popups, multi-line reasons, and save path disclosure."""
import os
import subprocess
from typing import Dict, List, Optional, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox, QFrame, QDoubleSpinBox, QTabWidget,
    QScrollArea, QTextEdit, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QCursor

from src.core.calculator import SingleRatioResult, CalculationResultSet, compute_ratios
from src.core.components import MappingDecision
from src.core.assumptions import AssumptionItem, build_assumptions_registry
from src.core.derivations import PeriodFinancials, extract_period_financials
from src.core.variance_engine import populate_reasons_for_results
from src.core.integrity import IntegrityCheckResult, run_integrity_checks
from src.core.audit import AuditLogger
from src.database.repository import Repository
from src.exporters.word_exporter import export_ratios_to_word
from src.exporters.excel_exporter import export_ratios_to_excel
from src.ui.dialogs.workings_dialog import WorkingsDialog
from src.ui.dialogs.ratio_info_dialog import RatioInfoDialog
from src.ui.dialogs.reason_editor_dialog import ReasonEditorDialog


# Essential core components to display in the clean mappings tab (filtering out unused noise)
ESSENTIAL_MAPPING_KEYS = [
    "share_capital", "reserves_surplus", "long_term_borrowings", "short_term_borrowings",
    "trade_payables", "trade_payables_msme", "trade_payables_other", "other_current_liabilities",
    "short_term_provisions", "reported_total_eq_liab", "ppe", "inventories", "trade_receivables",
    "cash_equivalents", "short_term_loans_advances", "other_current_assets", "reported_total_assets",
    "revenue_gross", "gst", "revenue_net", "cost_of_materials", "purchases_stock_in_trade",
    "changes_in_inventories", "employee_benefits", "finance_costs", "depreciation", "other_expenses",
    "total_expenses", "pbt", "pat", "cf_proceeds_lt_borrowings", "cf_repayment_st_borrowings", "cf_interest_paid"
]


class ResultsScreen(QWidget):
    back_to_dashboard = Signal()

    def __init__(self, repo: Repository, parent=None):
        super().__init__(parent)
        self.repo = repo
        
        self.payload: Optional[Dict[str, Any]] = None
        self.client_id: Optional[int] = None
        self.client_name: str = "Client"
        self.result_set: Optional[CalculationResultSet] = None
        self.assumptions: Dict[str, AssumptionItem] = {}
        self.integrity_results: List[IntegrityCheckResult] = []
        self.audit_logger = AuditLogger()
        self.cy_closing: Optional[PeriodFinancials] = None
        self.cy_opening: Optional[PeriodFinancials] = None
        self.py_closing: Optional[PeriodFinancials] = None
        self.py_opening: Optional[PeriodFinancials] = None
        
        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(14)
        
        # 1. Top Action & Navigation Bar
        top_bar = QHBoxLayout()
        
        back_btn = QPushButton("← Dashboard")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                color: #0F172A;
            }
        """)
        back_btn.clicked.connect(self.back_to_dashboard.emit)
        top_bar.addWidget(back_btn)
        
        self.title_label = QLabel("Statutory Analytical Ratios")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #0A2540;")
        top_bar.addWidget(self.title_label, stretch=1)
        
        # Save & Export Action Buttons
        save_btn = QPushButton("💾 Save Analysis")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0F766E;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #115E59;
            }
        """)
        save_btn.clicked.connect(self.on_save_analysis)
        top_bar.addWidget(save_btn)
        
        word_btn = QPushButton("📄 Export Word (.docx)")
        word_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066CC;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #0052A3;
            }
        """)
        word_btn.clicked.connect(self.on_export_word)
        top_bar.addWidget(word_btn)
        
        excel_btn = QPushButton("📊 Export Excel (.xlsx)")
        excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #16A34A;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #15803D;
            }
        """)
        excel_btn.clicked.connect(self.on_export_excel)
        top_bar.addWidget(excel_btn)
        
        self.main_layout.addLayout(top_bar)
        
        # 2. Save Path Confirmation Banner (Initially Hidden)
        self.save_banner = QFrame()
        self.save_banner.setStyleSheet("""
            QFrame {
                background-color: #F0FDF4;
                border: 1px solid #86EFAC;
                border-left: 5px solid #16A34A;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        sb_layout = QHBoxLayout(self.save_banner)
        sb_layout.setContentsMargins(12, 6, 12, 6)
        
        self.save_banner_text = QLabel()
        self.save_banner_text.setStyleSheet("color: #166534; font-size: 13px;")
        sb_layout.addWidget(self.save_banner_text, stretch=1)
        
        self.open_folder_btn = QPushButton("📂 Open File Location")
        self.open_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #166534;
                border: 1px solid #86EFAC;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #DCFCE7;
            }
        """)
        self.open_folder_btn.clicked.connect(self.on_open_save_folder)
        sb_layout.addWidget(self.open_folder_btn)
        
        dismiss_btn = QPushButton("✕")
        dismiss_btn.setStyleSheet("background: transparent; color: #166534; font-weight: bold; border: none; font-size: 14px;")
        dismiss_btn.clicked.connect(self.save_banner.hide)
        sb_layout.addWidget(dismiss_btn)
        
        self.main_layout.addWidget(self.save_banner)
        self.save_banner.hide()
        
        # 3. Modern Multi-Tab View
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E2E8F0;
                background-color: #FFFFFF;
                border-radius: 8px;
            }
        """)
        
        # Tab 1: Ratios & Variance Analysis
        self.tab_ratios = QWidget()
        self.setup_ratios_tab()
        self.tab_widget.addTab(self.tab_ratios, "📊 Schedule III Ratios & Variances")
        
        # Tab 2: Component Mappings
        self.tab_mappings = QWidget()
        self.setup_mappings_tab()
        self.tab_widget.addTab(self.tab_mappings, "🗺️ Component Mappings")
        
        # Tab 3: Integrity & Articulation
        self.tab_integrity = QWidget()
        self.setup_integrity_tab()
        self.tab_widget.addTab(self.tab_integrity, "🛡️ Integrity & Articulation Checks")
        
        # Tab 4: Workings Drilldown
        self.tab_workings = QWidget()
        self.setup_workings_tab()
        self.tab_widget.addTab(self.tab_workings, "🔍 Line Item Workings Drilldown")
        
        self.main_layout.addWidget(self.tab_widget, stretch=1)

    def setup_ratios_tab(self):
        layout = QVBoxLayout(self.tab_ratios)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Controls Bar
        ctrl_bar = QHBoxLayout()
        ctrl_bar.addWidget(QLabel("<b>Statutory Variance Threshold:</b>"))
        
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(1.0, 100.0)
        self.threshold_spin.setValue(25.0)
        self.threshold_spin.setSuffix(" %")
        self.threshold_spin.setStyleSheet("background: white; padding: 5px; border: 1px solid #CBD5E1; border-radius: 4px;")
        self.threshold_spin.valueChanged.connect(self.on_threshold_changed)
        ctrl_bar.addWidget(self.threshold_spin)
        
        ctrl_bar.addSpacing(20)
        
        self.summary_badge = QLabel("4 / 11 Ratios Flagged (≥ 25%)")
        self.summary_badge.setStyleSheet("""
            background-color: #FEF2F2;
            color: #DC2626;
            font-weight: bold;
            padding: 5px 12px;
            border-radius: 6px;
            border: 1px solid #FECACA;
        """)
        ctrl_bar.addWidget(self.summary_badge)
        
        ctrl_bar.addStretch()
        
        hint = QLabel("💡 Click <b>ℹ️</b> on any ratio for statutory definition & audit guidance | Click <b>✏️</b> to edit reasons")
        hint.setStyleSheet("font-size: 11px; color: #64748B;")
        ctrl_bar.addWidget(hint)
        
        layout.addLayout(ctrl_bar)
        
        # Ratios Table
        self.ratio_table = QTableWidget()
        self.ratio_table.setColumnCount(9)
        self.ratio_table.setHorizontalHeaderLabels([
            "#", "Ratio Name", "Numerator", "Denominator",
            "CY Value", "PY Value", "Variance %", "Status", "Driver Explanation & Statutory Reason"
        ])
        
        # Set Header Styles and Resize Modes
        header = self.ratio_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.Stretch)
        
        self.ratio_table.verticalHeader().setVisible(False)
        self.ratio_table.setAlternatingRowColors(True)
        self.ratio_table.setStyleSheet("QTableWidget { alternate-background-color: #F8FAFC; }")
        
        layout.addWidget(self.ratio_table, stretch=1)

    def setup_mappings_tab(self):
        layout = QVBoxLayout(self.tab_mappings)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        info = QLabel("<b>Schedule III Financial Statement Component Mappings</b> — Verified line items extracted from uploaded statements:")
        info.setStyleSheet("color: #334155; font-size: 12px;")
        layout.addWidget(info)
        
        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(7)
        self.mapping_table.setHorizontalHeaderLabels([
            "Component Name", "Sheet", "Source Row", "Source Label in Workbook",
            "CY Amount", "PY Amount", "Resolution Rule / Status"
        ])
        m_hdr = self.mapping_table.horizontalHeader()
        m_hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        m_hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        m_hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        m_hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        m_hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        m_hdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        m_hdr.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        self.mapping_table.verticalHeader().setVisible(False)
        layout.addWidget(self.mapping_table)

    def setup_integrity_tab(self):
        layout = QVBoxLayout(self.tab_integrity)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        info = QLabel("<b>Automated Statutory Integrity & Articulation Checks</b> — Mathematical and cross-statement consistency checks:")
        info.setStyleSheet("color: #334155; font-size: 12px;")
        layout.addWidget(info)
        
        self.integrity_table = QTableWidget()
        self.integrity_table.setColumnCount(6)
        self.integrity_table.setHorizontalHeaderLabels([
            "Check ID", "Check Name", "Status", "Expected Value", "Actual Value", "Auditor's Assessment / Comment"
        ])
        i_hdr = self.integrity_table.horizontalHeader()
        i_hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        i_hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        i_hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        i_hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        i_hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        i_hdr.setSectionResizeMode(5, QHeaderView.Stretch)
        
        self.integrity_table.verticalHeader().setVisible(False)
        layout.addWidget(self.integrity_table)

    def setup_workings_tab(self):
        layout = QVBoxLayout(self.tab_workings)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        info = QLabel("<b>Schedule III Mathematical Workings Drilldown</b> — Numerator, denominator, and 2-year average breakdowns:")
        info.setStyleSheet("color: #334155; font-size: 12px;")
        layout.addWidget(info)
        
        self.workings_browser = QTextEdit()
        self.workings_browser.setReadOnly(True)
        self.workings_browser.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 16px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                color: #0F172A;
            }
        """)
        layout.addWidget(self.workings_browser)

    def load_analysis_payload(self, payload: Dict[str, Any]):
        self.payload = payload
        self.client_id = payload.get("client_id")
        self.client_name = payload.get("client_name", "Client")
        self.result_set = payload.get("result_set")
        self.assumptions = payload.get("assumptions", {})
        self.integrity_results = payload.get("integrity_results", [])
        self.audit_logger = payload.get("audit_logger", AuditLogger())
        self.cy_closing = payload.get("cy_closing")
        self.cy_opening = payload.get("cy_opening")
        self.py_closing = payload.get("py_closing")
        self.py_opening = payload.get("py_opening")
        
        self.title_label.setText(f"Analytical Ratios — {self.client_name} ({payload.get('fy_end_date', '')})")
        self.save_banner.hide()
        
        self.refresh_all_views()

    def refresh_all_views(self):
        self.populate_ratios_table()
        self.populate_mappings_table()
        self.populate_integrity_table()
        self.populate_workings_view()

    def populate_ratios_table(self):
        if not self.result_set:
            return
            
        ratios = self.result_set.schedule_iii_ratios
        self.ratio_table.setRowCount(len(ratios))
        
        flagged_count = sum(1 for r in ratios if r.is_flagged)
        self.summary_badge.setText(f"{flagged_count} / {len(ratios)} Ratios Flagged (≥ {self.threshold_spin.value():.0f}%)")
        
        for row_idx, r in enumerate(ratios):
            self.ratio_table.setRowHeight(row_idx, 75)
            
            # 0. ID
            id_item = QTableWidgetItem(str(r.id))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.ratio_table.setItem(row_idx, 0, id_item)
            
            # 1. Name with Info Button (ℹ️)
            name_widget = QWidget()
            nw_layout = QHBoxLayout(name_widget)
            nw_layout.setContentsMargins(6, 4, 6, 4)
            nw_layout.setSpacing(6)
            
            name_lbl = QLabel(f"<b>{r.name}</b>")
            name_lbl.setStyleSheet("color: #0A2540; font-size: 12px;")
            nw_layout.addWidget(name_lbl)
            
            info_btn = QPushButton("ℹ️")
            info_btn.setToolTip("View statutory clause, formula, and audit guidance")
            info_btn.setStyleSheet("""
                QPushButton {
                    background-color: #EFF6FF;
                    color: #0066CC;
                    border: 1px solid #BFDBFE;
                    border-radius: 12px;
                    width: 24px;
                    height: 24px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #DBEAFE;
                }
            """)
            info_btn.clicked.connect(lambda checked=False, k=r.key: self.show_ratio_info(k))
            nw_layout.addWidget(info_btn)
            nw_layout.addStretch()
            self.ratio_table.setCellWidget(row_idx, 1, name_widget)
            
            # 2. Numerator
            num_item = QTableWidgetItem(f"{r.numerator_cy:,.2f}" if r.numerator_cy is not None else "—")
            num_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.ratio_table.setItem(row_idx, 2, num_item)
            
            # 3. Denominator
            den_item = QTableWidgetItem(f"{r.denominator_cy:,.2f}" if r.denominator_cy is not None else "—")
            den_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.ratio_table.setItem(row_idx, 3, den_item)
            
            # 4. CY Value
            cy_item = QTableWidgetItem(r.value_cy_formatted)
            cy_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            cy_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.ratio_table.setItem(row_idx, 4, cy_item)
            
            # 5. PY Value
            py_item = QTableWidgetItem(r.value_py_formatted)
            py_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.ratio_table.setItem(row_idx, 5, py_item)
            
            # 6. Variance % Pill
            var_widget = QWidget()
            vw_layout = QHBoxLayout(var_widget)
            vw_layout.setContentsMargins(4, 4, 4, 4)
            vw_layout.setAlignment(Qt.AlignCenter)
            
            var_lbl = QLabel(r.variance_pct_formatted)
            if r.is_flagged:
                var_lbl.setStyleSheet("""
                    background-color: #FEF2F2;
                    color: #DC2626;
                    font-weight: bold;
                    padding: 4px 8px;
                    border-radius: 10px;
                    border: 1px solid #FECACA;
                """)
            else:
                var_lbl.setStyleSheet("""
                    background-color: #F8FAFC;
                    color: #334155;
                    font-weight: 500;
                    padding: 4px 8px;
                    border-radius: 10px;
                    border: 1px solid #E2E8F0;
                """)
            vw_layout.addWidget(var_lbl)
            self.ratio_table.setCellWidget(row_idx, 6, var_widget)
            
            # 7. Status Badge
            status_item = QTableWidgetItem(r.status)
            status_item.setTextAlignment(Qt.AlignCenter)
            if r.is_flagged:
                status_item.setForeground(QColor("#DC2626"))
                status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            else:
                status_item.setForeground(QColor("#16A34A"))
            self.ratio_table.setItem(row_idx, 7, status_item)
            
            # 8. Reason Multiline Cell with Edit Button (Fix for Issue #1)
            reason_widget = QWidget()
            rw_layout = QHBoxLayout(reason_widget)
            rw_layout.setContentsMargins(6, 4, 6, 4)
            rw_layout.setSpacing(8)
            
            reason_lbl = QLabel(r.reason_final if r.reason_final else "Variance within statutory threshold.")
            reason_lbl.setWordWrap(True)
            reason_lbl.setStyleSheet("font-size: 11px; color: #1E293B; line-height: 1.3;")
            rw_layout.addWidget(reason_lbl, stretch=1)
            
            if r.is_flagged:
                edit_btn = QPushButton("✏️ Edit")
                edit_btn.setToolTip("Expand and edit statutory reason text")
                edit_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F1F5F9;
                        color: #0F172A;
                        border: 1px solid #CBD5E1;
                        border-radius: 4px;
                        padding: 4px 8px;
                        font-size: 11px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #E2E8F0;
                    }
                """)
                edit_btn.clicked.connect(lambda checked=False, ratio=r: self.on_edit_reason(ratio))
                rw_layout.addWidget(edit_btn)
                
            self.ratio_table.setCellWidget(row_idx, 8, reason_widget)

    def populate_mappings_table(self):
        if not self.payload:
            return
            
        cy_map = self.payload.get("cy_map") or self.payload.get("cy_mapping", {})
        py_map = self.payload.get("py_map") or self.payload.get("py_mapping", {})
        
        if not cy_map:
            return
            
        # Filter clean essential components (Fix for Issue #2)
        filtered_keys = [k for k in ESSENTIAL_MAPPING_KEYS if k in cy_map]
        if not filtered_keys:
            filtered_keys = list(cy_map.keys())
            
        self.mapping_table.setRowCount(len(filtered_keys))
        
        for row_idx, key in enumerate(filtered_keys):
            cy_dec = cy_map[key]
            py_dec = py_map.get(key)
            
            self.mapping_table.setRowHeight(row_idx, 32)
            
            name_item = QTableWidgetItem(key.replace("_", " ").title())
            name_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.mapping_table.setItem(row_idx, 0, name_item)
            
            sheet_item = QTableWidgetItem(cy_dec.source_sheet)
            sheet_item.setTextAlignment(Qt.AlignCenter)
            self.mapping_table.setItem(row_idx, 1, sheet_item)
            
            row_item = QTableWidgetItem(str(cy_dec.source_row) if cy_dec.source_row else "—")
            row_item.setTextAlignment(Qt.AlignCenter)
            self.mapping_table.setItem(row_idx, 2, row_item)
            
            lbl_item = QTableWidgetItem(cy_dec.source_label)
            self.mapping_table.setItem(row_idx, 3, lbl_item)
            
            cy_val_item = QTableWidgetItem(f"{cy_dec.amount_reporting:,.2f}")
            cy_val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.mapping_table.setItem(row_idx, 4, cy_val_item)
            
            py_val_item = QTableWidgetItem(f"{py_dec.amount_reporting:,.2f}" if py_dec else "—")
            py_val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.mapping_table.setItem(row_idx, 5, py_val_item)
            
            rule_item = QTableWidgetItem(cy_dec.resolution_rule)
            self.mapping_table.setItem(row_idx, 6, rule_item)

    def populate_integrity_table(self):
        # Streamline integrity list: clean statutory checks
        clean_checks = [ic for ic in self.integrity_results if ic.check_id in ("IC-1", "IC-2", "IC-3", "IC-4", "IC-5", "IC-6", "IC-7", "IC-8", "IC-9")]
        
        self.integrity_table.setRowCount(len(clean_checks))
        self.integrity_table.setWordWrap(True)
        
        for row_idx, ic in enumerate(clean_checks):
            self.integrity_table.setRowHeight(row_idx, 55)
            
            id_item = QTableWidgetItem(ic.check_id)
            id_item.setTextAlignment(Qt.AlignCenter)
            id_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.integrity_table.setItem(row_idx, 0, id_item)
            
            name_item = QTableWidgetItem(ic.name)
            name_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.integrity_table.setItem(row_idx, 1, name_item)
            
            status_item = QTableWidgetItem(ic.status)
            status_item.setTextAlignment(Qt.AlignCenter)
            if ic.status == "Pass":
                status_item.setForeground(QColor("#16A34A"))
                status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            elif ic.status == "Fail":
                status_item.setForeground(QColor("#DC2626"))
                status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            else:
                status_item.setForeground(QColor("#0066CC"))
            self.integrity_table.setItem(row_idx, 2, status_item)
            
            exp_item = QTableWidgetItem(ic.expected)
            exp_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.integrity_table.setItem(row_idx, 3, exp_item)
            
            act_item = QTableWidgetItem(ic.actual)
            act_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.integrity_table.setItem(row_idx, 4, act_item)
            
            # Word-wrapped comment widget to avoid any ellipsis or cropping
            com_widget = QWidget()
            cw_layout = QHBoxLayout(com_widget)
            cw_layout.setContentsMargins(6, 4, 6, 4)
            
            com_lbl = QLabel(ic.comment)
            com_lbl.setWordWrap(True)
            com_lbl.setStyleSheet("font-size: 11px; color: #1E293B; line-height: 1.3;")
            cw_layout.addWidget(com_lbl)
            
            self.integrity_table.setCellWidget(row_idx, 5, com_widget)

    def populate_workings_view(self):
        if not self.result_set:
            return
            
        lines = []
        lines.append(f"SCHEDULE III MATHEMATICAL RATIO WORKINGS — {self.client_name.upper()}")
        lines.append("=" * 80)
        
        for r in self.result_set.schedule_iii_ratios:
            lines.append(f"\n[{r.id}] {r.name.upper()} ({r.clause})")
            lines.append("-" * 80)
            lines.append(f"  Formula      : {r.numerator_desc} ÷ {r.denominator_desc}")
            lines.append(f"  CY Reporting : {r.numerator_cy:,.2f} ÷ {r.denominator_cy:,.2f} = {r.value_cy_formatted}")
            lines.append(f"  PY Reporting : {r.numerator_py:,.2f} ÷ {r.denominator_py:,.2f} = {r.value_py_formatted}")
            lines.append(f"  Variance     : {r.variance_pct_formatted} | Status: {r.status}")
            if r.is_flagged:
                lines.append(f"  Reason       : {r.reason_final}")
                
        self.workings_browser.setPlainText("\n".join(lines))

    def show_ratio_info(self, ratio_key: str):
        dlg = RatioInfoDialog(ratio_key, self)
        dlg.exec()

    def on_edit_reason(self, ratio: SingleRatioResult):
        dlg = ReasonEditorDialog(ratio.name, ratio.reason_final, ratio.variance_pct_formatted, self)
        if dlg.exec():
            new_text = dlg.get_reason()
            if new_text:
                ratio.reason_final = new_text
                ratio.is_reason_edited = True
                self.populate_ratios_table()

    def on_threshold_changed(self, new_val: float):
        if not self.cy_closing or not self.py_closing or not self.result_set:
            return
        self.result_set = compute_ratios(
            self.cy_closing, self.cy_opening, self.py_closing, self.py_opening,
            self.assumptions, threshold_pct=new_val
        )
        units = self.payload.get("units", "Lacs") if self.payload else "Lacs"
        populate_reasons_for_results(
            self.result_set.schedule_iii_ratios,
            self.cy_closing, self.cy_opening, self.py_closing, self.py_opening,
            units=units
        )
        self.populate_ratios_table()

    def on_save_analysis(self):
        if not self.client_id or not self.result_set:
            QMessageBox.warning(self, "Save Analysis", "No active analysis to save.")
            return
            
        fy_label = self.payload.get("fy_end_date", "Current Year") if self.payload else "Current Year"
        threshold = self.threshold_spin.value()
        
        analysis_id = self.repo.save_analysis(
            client_id=self.client_id,
            fy_label=fy_label,
            threshold_pct=threshold,
            ratios=self.result_set.schedule_iii_ratios,
            integrity_results=self.integrity_results,
            audit_logger=self.audit_logger
        )
        
        # Display exact file path on screen (Fix for Issue #7)
        db_path = str(self.repo.db_path)
        self.save_banner_text.setText(
            f"<b>✅ Analysis Saved Successfully!</b> &nbsp;|&nbsp; <b>ID:</b> #{analysis_id} &nbsp;|&nbsp; "
            f"<b>Saved to Database:</b> <span style='font-family: Consolas;'>{db_path}</span>"
        )
        self.save_banner.show()

    def on_open_save_folder(self):
        db_dir = os.path.dirname(str(self.repo.db_path))
        if os.path.exists(db_dir):
            if hasattr(os, "startfile"):
                os.startfile(db_dir)
            else:
                subprocess.run(["explorer", db_dir])

    def on_export_word(self):
        if not self.result_set or not self.payload:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Schedule III Ratios (Word)",
            f"{self.client_name}_Schedule_III_Ratios.docx",
            "Word Documents (*.docx)"
        )
        if file_path:
            try:
                export_ratios_to_word(
                    file_path=file_path,
                    client_name=self.client_name,
                    fy_end_date=self.payload.get("fy_end_date", "31 March 2026"),
                    units=self.payload.get("units", "Lacs"),
                    result_set=self.result_set,
                    assumptions=self.assumptions,
                    integrity_results=self.integrity_results
                )
                QMessageBox.information(self, "Export Successful", f"Word report successfully saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export Word document:\n{str(e)}")

    def on_export_excel(self):
        if not self.result_set or not self.payload:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Schedule III Ratios (Excel)",
            f"{self.client_name}_Schedule_III_Ratios.xlsx",
            "Excel Workbooks (*.xlsx)"
        )
        if file_path:
            try:
                export_ratios_to_excel(
                    file_path=file_path,
                    client_name=self.client_name,
                    fy_end_date=self.payload.get("fy_end_date", "31 March 2026"),
                    units=self.payload.get("units", "Lacs"),
                    result_set=self.result_set,
                    assumptions=self.assumptions,
                    integrity_results=self.integrity_results
                )
                QMessageBox.information(self, "Export Successful", f"Excel workbook successfully saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export Excel workbook:\n{str(e)}")
