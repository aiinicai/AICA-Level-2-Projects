import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QStatusBar,
    QMenuBar,
    QMenu,
    QMessageBox,
    QFileDialog,
    QInputDialog,
    QApplication,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon, QUndoStack

from reconai.models.session import ReconciliationSession
from reconai.config import AppConfig
from reconai.db.database import DatabaseManager
from reconai.ui.theme import apply_theme
from reconai.ui.views.ingest_view import IngestView
from reconai.ui.views.reconcile_view import ReconcileView
from reconai.ui.views.audit_view import AuditView
from reconai.ui.views.export_view import ExportView
from reconai.ui.views.settings_dialog import SettingsDialog
from reconai.ui.views.client_master_dialog import ClientMasterDialog
from reconai.ui.workers.background_workers import ReconcileWorker, AuditWorker


class MainWindow(QMainWindow):
    """Primary application window for ReconAI."""

    def __init__(self, session: ReconciliationSession, parent=None):
        super().__init__(parent)
        self.session = session
        self.db = DatabaseManager(self.session.config.get_resolved_db_path())
        self.undo_stack = QUndoStack(self)
        self._is_populating_clients = False

        self.setWindowTitle("ReconAI — Bank Reconciliation & Expense Audit Assistant")
        self.setMinimumSize(1180, 780)

        self._init_ui()
        self._populate_client_dropdown()
        self._apply_current_theme()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        # Header & Client Info Bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        app_title = QLabel("RECON<b>AI</b>")
        app_title.setStyleSheet("font-size: 20px; color: #3B82F6; font-family: 'Segoe UI'; font-weight: bold;")
        header_layout.addWidget(app_title)

        header_layout.addSpacing(10)

        header_layout.addWidget(QLabel("Client:"))
        self.client_combo = QComboBox()
        self.client_combo.setEditable(False)
        self.client_combo.setMinimumWidth(200)
        self.client_combo.setMaximumWidth(260)
        self.client_combo.currentIndexChanged.connect(self._on_client_selected)
        header_layout.addWidget(self.client_combo)

        self.client_master_btn = QPushButton("🏢 Client Master")
        self.client_master_btn.setObjectName("secondaryBtn")
        self.client_master_btn.clicked.connect(self._open_client_master)
        header_layout.addWidget(self.client_master_btn)

        header_layout.addWidget(QLabel("Bank A/c:"))
        self.bank_account_combo = QComboBox()
        self.bank_account_combo.setEditable(False)
        self.bank_account_combo.setMinimumWidth(210)
        self.bank_account_combo.setMaximumWidth(280)
        self.bank_account_combo.currentTextChanged.connect(self._on_bank_account_changed)
        header_layout.addWidget(self.bank_account_combo)

        header_layout.addWidget(QLabel("Period:"))
        self.period_edit = QLineEdit(self.session.period_label)
        self.period_edit.setFixedWidth(105)
        self.period_edit.textChanged.connect(self._on_period_changed)
        header_layout.addWidget(self.period_edit)

        header_layout.addStretch()

        # Theme & Settings Action Buttons
        self.theme_btn = QPushButton("🌙 Theme")
        self.theme_btn.setObjectName("secondaryBtn")
        self.theme_btn.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self.theme_btn)

        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.setObjectName("secondaryBtn")
        self.settings_btn.clicked.connect(self._open_settings)
        header_layout.addWidget(self.settings_btn)

        self.save_btn = QPushButton("💾 Save Session")
        self.save_btn.setObjectName("secondaryBtn")
        self.save_btn.clicked.connect(self._save_session)
        header_layout.addWidget(self.save_btn)

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setObjectName("secondaryBtn")
        self.refresh_btn.setToolTip("Refresh client master, reload active data views, and reset calculations")
        self.refresh_btn.clicked.connect(self._refresh_workspace)
        header_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(header_layout)

        # Workflow Navigation Stepper
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(4)

        self.nav_buttons: list[QPushButton] = []
        steps = [
            "1. Ingest & Load",
            "2. Reconciliation",
            "3. Expense Audit",
            "4. Report & Export",
        ]
        for idx, label in enumerate(steps):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            if idx == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, i=idx: self._switch_step(i))
            self.nav_buttons.append(btn)
            nav_layout.addWidget(btn)

        main_layout.addLayout(nav_layout)

        # View Stack
        self.stack = QStackedWidget()

        self.ingest_view = IngestView(self.session)
        self.reconcile_view = ReconcileView(self.session, self.undo_stack)
        self.audit_view = AuditView(self.session)
        self.export_view = ExportView(self.session)

        # Wire cross-view events
        self.ingest_view.reconcile_requested.connect(self._run_reconciliation_pipeline)
        self.ingest_view.data_loaded.connect(self._sync_detected_bank_account)
        self.reconcile_view.matches_changed.connect(self._on_matches_updated)

        self.stack.addWidget(self.ingest_view)
        self.stack.addWidget(self.reconcile_view)
        self.stack.addWidget(self.audit_view)
        self.stack.addWidget(self.export_view)

        main_layout.addWidget(self.stack, 1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Select statement and ledger files in Step 1.")

    def _populate_client_dropdown(self):
        """Populate the Client dropdown from saved database records and activate selected client."""
        self._is_populating_clients = True
        self.client_combo.clear()

        clients = self.db.list_clients()
        matched_idx = -1

        for idx, c in enumerate(clients):
            label = f"{c.name} ({c.pan})" if c.pan else c.name
            self.client_combo.addItem(label, userData=c)
            if self.session.client_id and c.id == self.session.client_id:
                matched_idx = idx
            elif not self.session.client_id and "sun health care" in c.name.lower():
                matched_idx = idx
            elif not self.session.client_id and matched_idx < 0 and c.name.lower() in self.session.client_name.lower():
                matched_idx = idx

        if matched_idx < 0 and clients:
            matched_idx = 0

        self._is_populating_clients = False

        if matched_idx >= 0:
            self.client_combo.setCurrentIndex(matched_idx)
            self._apply_client_profile(self.client_combo.itemData(matched_idx))
        else:
            self.client_combo.setEditText(self.session.client_name)

    def _apply_client_profile(self, client):
        if not client:
            return
        self.session.client_id = client.id
        self.session.client_name = client.name
        if client.approved_vendors:
            self.session.config.audit.approved_vendors = client.approved_vendors
        if client.default_auditor_notes and not self.session.auditor_remarks:
            self.session.auditor_remarks = client.default_auditor_notes

        self.bank_account_combo.clear()
        if client.bank_accounts:
            for b in client.bank_accounts:
                self.bank_account_combo.addItem(f"{b.bank_name} - {b.account_no} ({b.account_type})", userData=b)
        else:
            self.bank_account_combo.addItem("General Bank Account")

        # Also add any linked books
        for bk in getattr(client, "books", []):
            if bk.linked_bank_account:
                exists = any(bk.linked_bank_account in self.bank_account_combo.itemText(i) for i in range(self.bank_account_combo.count()))
                if not exists:
                    self.bank_account_combo.addItem(f"{bk.book_name} - {bk.linked_bank_account}", userData=bk)

        if self.bank_account_combo.count() > 0:
            self.bank_account_combo.setCurrentIndex(0)

        self.status_bar.showMessage(f"Active Client Master Profile: {client.name}", 4000)

    def _on_client_selected(self, index: int):
        if self._is_populating_clients or index < 0:
            return
        client = self.client_combo.itemData(index)
        if client:
            self._apply_client_profile(client)

    def _on_bank_account_changed(self, text: str):
        if not text:
            return
        self.session.log_event("BANK_ACCOUNT_SELECTED", f"Active bank account: {text}")

    def _sync_detected_bank_account(self):
        if self.session.statements:
            acct = self.session.statements[0].raw_data.get("account_no")
            if acct:
                found = False
                for i in range(self.bank_account_combo.count()):
                    if acct in self.bank_account_combo.itemText(i):
                        self.bank_account_combo.setCurrentIndex(i)
                        found = True
                        break
                if not found:
                    self.bank_account_combo.insertItem(0, f"Detected Bank A/c: {acct}")
                    self.bank_account_combo.setCurrentIndex(0)

    def _on_client_name_typed(self, text: str):
        if self._is_populating_clients:
            return
        cleaned = text.split(" (")[0].strip()
        self.session.client_name = cleaned or "Client"

    def _open_client_master(self):
        dialog = ClientMasterDialog(self.db, current_client_id=self.session.client_id, parent=self)
        if dialog.exec():
            selected = dialog.selected_client
            if selected:
                self.session.client_id = selected.id
            self._populate_client_dropdown()
            if selected:
                self._apply_client_profile(selected)

    def _switch_step(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        # Refresh target view
        if index == 0:
            self.ingest_view.refresh_views()
        elif index == 1:
            self.reconcile_view.refresh_data()
        elif index == 2:
            self.audit_view.refresh_data()
        elif index == 3:
            self.export_view.refresh_data()

    def _on_period_changed(self, text: str):
        self.session.period_label = text.strip() or "Period"

    def _toggle_theme(self):
        new_theme = "light" if self.session.config.theme == "dark" else "dark"
        self.session.config.theme = new_theme
        self._apply_current_theme()

    def _apply_current_theme(self):
        app = QApplication.instance()
        if app:
            apply_theme(app, self.session.config.theme)
        self.theme_btn.setText("☀️ Light" if self.session.config.theme == "dark" else "🌙 Dark")

    def _open_settings(self):
        dialog = SettingsDialog(self.session.config, self)
        if dialog.exec():
            self.session.config.save_to_file()
            self._apply_current_theme()
            self.status_bar.showMessage("Configuration saved.", 4000)

    def _save_session(self):
        try:
            self.db.save_session(self.session)
            self.status_bar.showMessage(f"Session saved to database ({self.session.session_id[:8]}).", 4000)
            QMessageBox.information(self, "Session Saved", f"Session saved successfully for '{self.session.client_name}'.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save session:\n{e}")

    def _run_reconciliation_pipeline(self):
        self.status_bar.showMessage("Running multi-pass reconciliation engine...")
        self.ingest_view.progress_bar.setVisible(True)

        self.recon_worker = ReconcileWorker(self.session)
        self.recon_worker.finished.connect(self._on_reconcile_completed)
        self.recon_worker.error.connect(self._on_pipeline_error)
        self.recon_worker.start()

    def _on_reconcile_completed(self, matches):
        self.session.matches = matches
        self.session.log_event(
            "AUTO_RECONCILE_COMPLETED",
            f"Generated {len(matches)} match and unmatched diagnostic records.",
        )

        self.status_bar.showMessage("Reconciliation complete. Running expense audit checks...")

        # Run Audit Pass
        self.audit_worker = AuditWorker(self.session)
        self.audit_worker.finished.connect(self._on_audit_completed)
        self.audit_worker.error.connect(self._on_pipeline_error)
        self.audit_worker.start()

    def _on_audit_completed(self, flags):
        self.ingest_view.progress_bar.setVisible(False)
        self.session.audit_flags = flags
        self.session.log_event(
            "AUDIT_COMPLETED",
            f"Audit finished with {len(flags)} findings.",
        )

        self.status_bar.showMessage("Reconciliation & Audit complete!", 5000)
        # Advance to step 2 (Reconciliation view)
        self._switch_step(1)

    def _on_pipeline_error(self, err_msg: str):
        self.ingest_view.progress_bar.setVisible(False)
        self.status_bar.showMessage("Error during processing.", 5000)
        QMessageBox.critical(self, "Processing Error", f"Error in reconciliation/audit engine:\n{err_msg}")

    def _on_matches_updated(self):
        self.export_view.refresh_data()

    def _refresh_workspace(self):
        """Refresh client dropdown, reload views, and sync workspace data."""
        self._populate_client_dropdown()
        current_step = self.stack.currentIndex()
        self._switch_step(current_step)
        self.status_bar.showMessage("Workspace and client profiles refreshed.", 4000)
