from pathlib import Path
from typing import Callable, Optional
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QFileDialog,
    QTabWidget,
    QTableView,
    QHeaderView,
    QMessageBox,
    QProgressBar,
)
from PyQt6.QtCore import Qt, pyqtSignal

from reconai.models.session import ReconciliationSession
from reconai.ingest.base_parser import get_excel_sheets_info
from reconai.ui.components.stat_card import StatCard
from reconai.ui.components.table_models import StatementTableModel, LedgerTableModel
from reconai.ui.workers.background_workers import ParseWorker


class IngestView(QWidget):
    """File ingestion, multi-sheet detection, and data preview view."""

    data_loaded = pyqtSignal()
    reconcile_requested = pyqtSignal()

    def __init__(self, session: ReconciliationSession, parent=None):
        super().__init__(parent)
        self.session = session
        self.stmt_model = StatementTableModel()
        self.ledger_model = LedgerTableModel()
        self._last_parsed_stmt_paths: Optional[str] = None
        self._last_parsed_ledger_key: Optional[tuple] = None
        self._cached_stmts = []
        self._cached_ledgers = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 1. Top File Selection Area (Two Cards side by side)
        top_cards_layout = QHBoxLayout()
        top_cards_layout.setSpacing(14)

        # Bank Statement Card
        stmt_group = QGroupBox("1. Bank Statement Ingestion (PDF / CSV / Excel)")
        stmt_layout = QVBoxLayout(stmt_group)
        
        stmt_file_layout = QHBoxLayout()
        self.stmt_path_edit = QLineEdit()
        self.stmt_path_edit.setPlaceholderText("Select bank statement file (.csv, .xlsx, .pdf)...")
        self.stmt_path_edit.setReadOnly(True)
        self.stmt_browse_btn = QPushButton("Browse File")
        self.stmt_browse_btn.clicked.connect(self._browse_statement)
        stmt_file_layout.addWidget(self.stmt_path_edit)
        stmt_file_layout.addWidget(self.stmt_browse_btn)

        self.stmt_stats_label = QLabel("No statement loaded")
        self.stmt_stats_label.setStyleSheet("color: #64748B; font-size: 11px;")

        stmt_layout.addLayout(stmt_file_layout)
        stmt_layout.addWidget(self.stmt_stats_label)
        top_cards_layout.addWidget(stmt_group)

        # Client Ledger Card
        ledger_group = QGroupBox("2. Client Books / Ledger Ingestion (Tally / CSV / Excel)")
        ledger_layout = QVBoxLayout(ledger_group)

        ledger_file_layout = QHBoxLayout()
        self.ledger_path_edit = QLineEdit()
        self.ledger_path_edit.setPlaceholderText("Select client ledger file (.csv, .xlsx)...")
        self.ledger_path_edit.setReadOnly(True)
        self.ledger_browse_btn = QPushButton("Browse File")
        self.ledger_browse_btn.clicked.connect(self._browse_ledger)
        ledger_file_layout.addWidget(self.ledger_path_edit)
        ledger_file_layout.addWidget(self.ledger_browse_btn)

        # Sheet Selection Row (Visible when multi-sheet Excel is detected)
        self.ledger_sheet_container = QWidget()
        sheet_layout = QHBoxLayout(self.ledger_sheet_container)
        sheet_layout.setContentsMargins(0, 2, 0, 2)
        sheet_layout.addWidget(QLabel("<b>📄 Select Account / Sheet:</b>"))
        self.ledger_sheet_combo = QComboBox()
        self.ledger_sheet_combo.setMinimumWidth(260)
        self.ledger_sheet_combo.currentIndexChanged.connect(self._on_sheet_selection_changed)
        sheet_layout.addWidget(self.ledger_sheet_combo, 1)
        self.ledger_sheet_container.setVisible(False)

        self.ledger_stats_label = QLabel("No ledger loaded")
        self.ledger_stats_label.setStyleSheet("color: #64748B; font-size: 11px;")

        ledger_layout.addLayout(ledger_file_layout)
        ledger_layout.addWidget(self.ledger_sheet_container)
        ledger_layout.addWidget(self.ledger_stats_label)
        top_cards_layout.addWidget(ledger_group)

        layout.addLayout(top_cards_layout)

        # Action Bar & Progress Bar
        action_layout = QHBoxLayout()
        self.load_btn = QPushButton("Parse & Normalize Files")
        self.load_btn.setObjectName("secondaryBtn")
        self.load_btn.clicked.connect(self._parse_files)

        self.reconcile_btn = QPushButton("▶ Run Automated Reconciliation & Audit")
        self.reconcile_btn.setObjectName("successBtn")
        self.reconcile_btn.setEnabled(False)
        self.reconcile_btn.clicked.connect(self.reconcile_requested.emit)

        self.reset_btn = QPushButton("🔄 Reset / Clear Files")
        self.reset_btn.setObjectName("secondaryBtn")
        self.reset_btn.clicked.connect(self._reset_ingest)

        action_layout.addWidget(self.load_btn)
        action_layout.addWidget(self.reconcile_btn)
        action_layout.addWidget(self.reset_btn)
        action_layout.addStretch()

        layout.addLayout(action_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # indeterminate
        layout.addWidget(self.progress_bar)

        # 2. Tabbed Preview Tables
        self.preview_tabs = QTabWidget()

        # Bank Statement Table
        self.stmt_table = QTableView()
        self.stmt_table.setModel(self.stmt_model)
        self.stmt_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.stmt_table.horizontalHeader().setStretchLastSection(True)
        self.preview_tabs.addTab(self.stmt_table, "Bank Statement Records (0)")

        # Client Ledger Table
        self.ledger_table = QTableView()
        self.ledger_table.setModel(self.ledger_model)
        self.ledger_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.ledger_table.horizontalHeader().setStretchLastSection(True)
        self.preview_tabs.addTab(self.ledger_table, "Client Books / Ledger Entries (0)")

        layout.addWidget(self.preview_tabs, 1)

    def _browse_statement(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Bank Statement File(s)",
            "",
            "All Supported Statements (*.pdf *.csv *.xlsx *.xls *.docx *.png *.jpg *.jpeg *.webp);;PDF Statements (*.pdf);;Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;Word Files (*.docx);;Scanned Images & Photos (*.png *.jpg *.jpeg *.webp);;All Files (*.*)",
        )
        if paths:
            self.stmt_path_edit.setText("; ".join(paths))
            self.stmt_stats_label.setText(f"Loading {len(paths)} statement file(s)...")
            self._parse_files()

    def _browse_ledger(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Client Books / Ledger File(s)",
            "",
            "All Supported Ledgers (*.xlsx *.xls *.csv *.docx *.png *.jpg *.jpeg *.webp);;Excel Ledgers (*.xlsx *.xls);;CSV Files (*.csv);;Word Files (*.docx);;Scanned / Handwritten Vouchers (*.png *.jpg *.jpeg *.webp);;All Files (*.*)",
        )
        if paths:
            self.ledger_path_edit.setText("; ".join(paths))
            self._update_sheet_selector(paths[0])
            self.ledger_stats_label.setText(f"Loading {len(paths)} ledger file(s)...")
            self._parse_files()

    def _update_sheet_selector(self, file_path: str):
        """Detect and populate sheets if an Excel workbook contains multiple bank accounts/sheets."""
        ext = Path(file_path).suffix.lower()
        if ext in [".xlsx", ".xls"]:
            sheets_info = get_excel_sheets_info(file_path)
            if len(sheets_info) > 1:
                self.ledger_sheet_combo.clear()
                best_idx = 0
                max_rows = -1

                stmt_acct = None
                if self.session.statements:
                    for s_tx in self.session.statements[:10]:
                        if s_tx.raw_data and s_tx.raw_data.get("account_no"):
                            stmt_acct = str(s_tx.raw_data["account_no"]).strip()
                            break

                for idx, s in enumerate(sheets_info):
                    label = f"{s['sheet_name']}"
                    if s['title']:
                        label += f": {s['title'][:45]}"
                    label += f" ({s['rows']} rows)"
                    self.ledger_sheet_combo.addItem(label, userData=s['sheet_name'])

                    combined_str = (s['sheet_name'] + " " + s['title']).lower()
                    if stmt_acct and stmt_acct in combined_str:
                        best_idx = idx
                        max_rows = 999999999  # Absolute highest priority match
                    elif s['rows'] > max_rows and max_rows < 999999999:
                        max_rows = s['rows']
                        best_idx = idx

                self.ledger_sheet_combo.setCurrentIndex(best_idx)
                self.ledger_sheet_container.setVisible(True)
                return

        self.ledger_sheet_container.setVisible(False)

    def _on_sheet_selection_changed(self, index: int):
        if self.ledger_sheet_container.isVisible() and index >= 0:
            ledger_path = self.ledger_path_edit.text().strip()
            if ledger_path:
                self._parse_files()

    def _parse_files(self):
        stmt_path = self.stmt_path_edit.text().strip() or None
        ledger_path = self.ledger_path_edit.text().strip() or None

        if not stmt_path and not ledger_path:
            QMessageBox.warning(self, "No File Selected", "Please select at least one statement or ledger file to parse.")
            return

        selected_sheet = None
        if self.ledger_sheet_container.isVisible():
            selected_sheet = self.ledger_sheet_combo.currentData()

        # Check if already cached
        cached_stmts = self._cached_stmts if (stmt_path and stmt_path == self._last_parsed_stmt_paths and self._cached_stmts) else None
        cached_ledgers = self._cached_ledgers if (ledger_path and (ledger_path, selected_sheet) == self._last_parsed_ledger_key and self._cached_ledgers) else None

        self.progress_bar.setVisible(True)
        self.load_btn.setEnabled(False)

        self.worker = ParseWorker(
            stmt_path=stmt_path,
            ledger_path=ledger_path,
            ledger_sheet=selected_sheet,
            api_key=self.session.config.reconciliation.api_key,
            cached_stmts=cached_stmts,
            cached_ledgers=cached_ledgers,
        )
        self.worker.finished.connect(self._on_parse_success)
        self.worker.error.connect(self._on_parse_error)
        self.worker.start()

    def _on_parse_success(self, stmts, ledgers):
        self.progress_bar.setVisible(False)
        self.load_btn.setEnabled(True)

        if stmts:
            self._cached_stmts = stmts
            self._last_parsed_stmt_paths = self.stmt_path_edit.text().strip()
            self.session.statements = stmts
            self.stmt_model.set_data(stmts)
            self.preview_tabs.setTabText(0, f"Bank Statement Records ({len(stmts)})")
            total_stmt_amt = sum(s.amount for s in stmts)
            self.stmt_stats_label.setText(f"✓ Parsed {len(stmts)} transactions | Total Volume: ₹ {total_stmt_amt:,.2f}")

        if ledgers:
            self._cached_ledgers = ledgers
            selected_sheet = self.ledger_sheet_combo.currentData() if self.ledger_sheet_container.isVisible() else None
            self._last_parsed_ledger_key = (self.ledger_path_edit.text().strip(), selected_sheet)
            self.session.ledger_entries = ledgers
            self.ledger_model.set_data(ledgers)
            self.preview_tabs.setTabText(1, f"Client Books / Ledger Entries ({len(ledgers)})")
            total_ledger_amt = sum(l.amount for l in ledgers)
            self.ledger_stats_label.setText(f"✓ Parsed {len(ledgers)} vouchers | Total Volume: ₹ {total_ledger_amt:,.2f}")

        # Clear any stale matches from previous datasets so tables always match current IDs
        if stmts or ledgers:
            self.session.matches = []
            self.session.audit_flags = []

        if self.session.statements and self.session.ledger_entries:
            self.reconcile_btn.setEnabled(True)

        self.session.log_event(
            "INGEST_COMPLETED",
            f"Successfully parsed {len(stmts)} statement transactions and {len(ledgers)} ledger vouchers.",
        )
        self.data_loaded.emit()

    def _on_parse_error(self, err_msg: str):
        self.progress_bar.setVisible(False)
        self.load_btn.setEnabled(True)
        QMessageBox.critical(self, "Parsing Error", f"Failed to parse source file:\n{err_msg}")

    def _reset_ingest(self):
        """Clear all active ingested statements, ledgers, and table views."""
        self.session.statements = []
        self.session.ledger_entries = []
        self.session.matches = []
        self.session.audit_flags = []
        self.stmt_path_edit.clear()
        self.ledger_path_edit.clear()
        self.stmt_stats_label.setText("No statement loaded")
        self.ledger_stats_label.setText("No ledger loaded")
        self.ledger_sheet_container.setVisible(False)
        self.stmt_model.set_data([])
        self.ledger_model.set_data([])
        self.preview_tabs.setTabText(0, "Bank Statement Records (0)")
        self.preview_tabs.setTabText(1, "Client Books / Ledger Entries (0)")
        self.reconcile_btn.setEnabled(False)

    def refresh_views(self):
        self.stmt_model.set_data(self.session.statements)
        self.ledger_model.set_data(self.session.ledger_entries)
        self.preview_tabs.setTabText(0, f"Bank Statement Records ({len(self.session.statements)})")
        self.preview_tabs.setTabText(1, f"Client Books / Ledger Entries ({len(self.session.ledger_entries)})")
        if self.session.statements and self.session.ledger_entries:
            self.reconcile_btn.setEnabled(True)
