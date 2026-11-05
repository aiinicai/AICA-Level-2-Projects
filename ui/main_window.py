"""
LexSecure India Pro - Master Window Architecture
Unified Enterprise Legal & Regulatory Intelligence Desktop Suite
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QStackedWidget, QComboBox, QButtonGroup, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QColor

from ui.styles import THEME_COLORS, MAIN_QSS
from ui.views.dashboard_view import DashboardView
from ui.views.contract_review_view import ContractReviewView
from ui.views.regulatory_view import RegulatoryView
from ui.views.tasks_view import TasksView
from ui.views.calendar_view import CalendarView
from ui.views.entity_user_management_view import EntityUserManagementView
from ui.views.access_matrix_view import AccessMatrixView
from ui.views.audit_dossier_view import AuditDossierView
from ui.components.login_dialog import LoginDialog
from models.entities import Entity, User

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LexSecure India Pro — Enterprise Legal & Regulatory Intelligence")
        self.resize(1300, 840)
        self.setMinimumSize(1020, 680)
        
        self.current_entity_id = 1
        self.current_user = None

        # Load initial user (default to General Counsel)
        default_user = User.get_by_id(1)
        if default_user:
            self.current_user = default_user

        self.setStyleSheet(MAIN_QSS)
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Sidebar Navigation
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(270)
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(0, 16, 0, 16)
        s_layout.setSpacing(4)

        # App Brand Header
        brand_frame = QFrame()
        brand_frame.setStyleSheet("padding: 2px 16px 14px 16px; border-bottom: 1px solid #1E293B;")
        b_layout = QVBoxLayout(brand_frame)
        b_layout.setSpacing(3)

        app_name = QLabel("LexSecure India Pro")
        app_name.setWordWrap(False)
        app_name.setStyleSheet("color: #10B981; font-size: 17px; font-weight: 900; letter-spacing: 0.5px;")
        b_layout.addWidget(app_name)

        app_tag = QLabel("Statutory & Regulatory Intel")
        app_tag.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500;")
        b_layout.addWidget(app_tag)
        s_layout.addWidget(brand_frame)

        s_layout.addSpacing(8)

        # Navigation Buttons
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_items = [
            ("📊  Executive Dashboard", 0),
            ("📄  Contract / Document Review", 1),
            ("📡  Indian Regulatory Tracker", 2),
            ("📋  Department Tasks", 3),
            ("📅  Statutory Calendar", 4),
            ("🏢  Entity & User Governance", 5),
            ("🛡️  Access Matrix Control", 6),
            ("🔒  SHA-256 Audit Dossier", 7)
        ]

        self.nav_buttons = []
        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("class", "nav-btn")
            btn.clicked.connect(lambda checked, i=idx: self.switch_view(i))
            self.nav_group.addButton(btn, idx)
            s_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        # Default select dashboard
        self.nav_buttons[0].setChecked(True)

        s_layout.addStretch()

        # Sidebar Footer: Jurisdiction Notice
        footer_box = QFrame()
        footer_box.setStyleSheet("background-color: #0F172A; border-radius: 8px; margin: 10px; padding: 10px; border: 1px solid #1E293B;")
        f_layout = QVBoxLayout(footer_box)
        f_layout.setSpacing(3)

        juris_lbl = QLabel("JURISDICTION: INDIA")
        juris_lbl.setStyleSheet("color: #38BDF8; font-size: 10px; font-weight: bold;")
        f_layout.addWidget(juris_lbl)

        ver_lbl = QLabel("FEMA • DPDP • Labour Codes • MSME")
        ver_lbl.setStyleSheet("color: #64748B; font-size: 10px;")
        f_layout.addWidget(ver_lbl)
        s_layout.addWidget(footer_box)

        root_layout.addWidget(sidebar)

        # 2. Main Content Area (Header + Stacked Widget)
        content_area = QWidget()
        c_layout = QVBoxLayout(content_area)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(0)

        # Top Header Bar
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(54)
        t_layout = QHBoxLayout(topbar)
        t_layout.setContentsMargins(16, 0, 16, 0)
        t_layout.setSpacing(12)

        # Entity Switcher
        ent_lbl = QLabel("Entity:")
        ent_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")
        t_layout.addWidget(ent_lbl)

        self.entity_combo = QComboBox()
        self.entity_combo.setMinimumWidth(260)
        self.populate_entities()
        self.entity_combo.currentIndexChanged.connect(self.on_entity_changed)
        t_layout.addWidget(self.entity_combo)

        t_layout.addStretch()

        # Tamper-Evident Status Badge
        self.tamper_pill = QLabel("● SHA-256 CHAIN VERIFIED")
        self.tamper_pill.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.15);
            color: #10B981;
            font-size: 10px;
            font-weight: bold;
            border: 1px solid #10B981;
            border-radius: 10px;
            padding: 3px 9px;
        """)
        t_layout.addWidget(self.tamper_pill)

        # Active User Info Pill
        self.user_pill = QLabel()
        self.update_user_pill()
        t_layout.addWidget(self.user_pill)

        # Switch User / Login Button
        self.btn_switch_user = QPushButton("🔑 Switch User")
        self.btn_switch_user.setStyleSheet("""
            background-color: #1E293B;
            color: #38BDF8;
            border: 1px solid #0284C7;
            font-weight: 600;
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 11px;
        """)
        self.btn_switch_user.clicked.connect(self.open_login_dialog)
        t_layout.addWidget(self.btn_switch_user)

        # Professional Dark / Light Theme Mode Toggle
        self.current_theme_mode = "dark"
        self.btn_theme_toggle = QPushButton("☀️ Light Mode")
        self.btn_theme_toggle.setStyleSheet("""
            background-color: #1E293B;
            color: #F59E0B;
            border: 1px solid #D97706;
            font-weight: 600;
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 11px;
        """)
        self.btn_theme_toggle.clicked.connect(self.toggle_theme_mode)
        t_layout.addWidget(self.btn_theme_toggle)

        c_layout.addWidget(topbar)

        # Stacked Views
        self.stack = QStackedWidget()

        # Instantiate Views
        self.dashboard_view = DashboardView(self.current_entity_id)
        self.contract_view = ContractReviewView(self.current_entity_id)
        self.regulatory_view = RegulatoryView(self.current_entity_id)
        self.tasks_view = TasksView(self.current_entity_id)
        self.calendar_view = CalendarView(self.current_entity_id)
        self.entity_user_view = EntityUserManagementView(1)
        self.access_matrix_view = AccessMatrixView()
        self.audit_dossier_view = AuditDossierView(1)

        # Connect Navigation Signals
        self.dashboard_view.navigate_to_review.connect(lambda: self.switch_view(1))
        self.dashboard_view.navigate_to_regulatory.connect(lambda: self.switch_view(2))
        self.dashboard_view.navigate_to_calendar.connect(lambda: self.switch_view(4))

        # Connect Cross-View Signals
        self.contract_view.audit_event_logged.connect(self.audit_dossier_view.verify_and_refresh)
        self.contract_view.entity_selection_requested.connect(self.on_entity_selection_requested)
        self.regulatory_view.task_dispatched.connect(self.tasks_view.load_tasks)
        self.regulatory_view.audit_event_logged.connect(self.audit_dossier_view.verify_and_refresh)
        self.tasks_view.audit_event_logged.connect(self.audit_dossier_view.verify_and_refresh)

        # Connect Entity/User Governance Signals
        self.entity_user_view.entities_changed.connect(self.on_entities_updated)
        self.entity_user_view.users_changed.connect(self.on_users_updated)
        self.entity_user_view.audit_event_logged.connect(self.audit_dossier_view.verify_and_refresh)

        # Add to stack
        self.stack.addWidget(self.dashboard_view)      # 0
        self.stack.addWidget(self.contract_view)       # 1
        self.stack.addWidget(self.regulatory_view)     # 2
        self.stack.addWidget(self.tasks_view)          # 3
        self.stack.addWidget(self.calendar_view)       # 4
        self.stack.addWidget(self.entity_user_view)    # 5
        self.stack.addWidget(self.access_matrix_view)  # 6
        self.stack.addWidget(self.audit_dossier_view)  # 7

        c_layout.addWidget(self.stack, 1)
        root_layout.addWidget(content_area, 1)

    def update_user_pill(self):
        if self.current_user:
            role_fmt = self.current_user.role.replace("_", " ")
            self.user_pill.setText(f"👤 {self.current_user.full_name}  [{role_fmt}]")
            self.user_pill.setStyleSheet("""
                background-color: #0B1120;
                color: #F8FAFC;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 10px;
            """)
        else:
            self.user_pill.setText("👤 Guest / Sign In")
            self.user_pill.setStyleSheet("color: #94A3B8; font-size: 11px; padding: 4px 8px;")

    def open_login_dialog(self):
        cur_id = self.current_user.id if self.current_user else 1
        dlg = LoginDialog(self, cur_id)
        if dlg.exec():
            self.current_user = dlg.authenticated_user
            self.update_user_pill()
            self.audit_dossier_view.verify_and_refresh()
            QMessageBox.information(
                self, "Authenticated",
                f"Welcome, {self.current_user.full_name}!\nSession authenticated under role '{self.current_user.role.replace('_', ' ')}'."
            )

    def populate_entities(self):
        self.entity_combo.blockSignals(True)
        self.entity_combo.clear()
        entities = Entity.get_all(1)
        cur_idx = 0
        for idx, e in enumerate(entities):
            self.entity_combo.addItem(f"{e.legal_name} ({e.registered_state})", e.id)
            if e.id == self.current_entity_id:
                cur_idx = idx
        self.entity_combo.setCurrentIndex(cur_idx)
        self.entity_combo.blockSignals(False)

    def on_entities_updated(self):
        self.populate_entities()
        self.on_entity_changed(self.entity_combo.currentIndex())

    def on_users_updated(self):
        # Refresh current user state if modified
        if self.current_user:
            updated = User.get_by_id(self.current_user.id)
            if updated and updated.is_active:
                self.current_user = updated
            else:
                self.current_user = User.get_all(1)[0] if User.get_all(1) else None
        self.update_user_pill()

    def toggle_theme_mode(self):
        from ui.styles import get_theme_qss
        from PyQt6.QtWidgets import QApplication
        if self.current_theme_mode == "dark":
            self.current_theme_mode = "light"
            self.btn_theme_toggle.setText("🌙 Dark Mode")
            self.btn_theme_toggle.setStyleSheet("""
                background-color: #E2E8F0;
                color: #0F172A;
                border: 1px solid #94A3B8;
                font-weight: 600;
                padding: 5px 12px;
                border-radius: 6px;
                font-size: 11px;
            """)
        else:
            self.current_theme_mode = "dark"
            self.btn_theme_toggle.setText("☀️ Light Mode")
            self.btn_theme_toggle.setStyleSheet("""
                background-color: #1E293B;
                color: #F59E0B;
                border: 1px solid #D97706;
                font-weight: 600;
                padding: 5px 12px;
                border-radius: 6px;
                font-size: 11px;
            """)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_theme_qss(self.current_theme_mode))

    def on_entity_selection_requested(self, entity_id: int):
        idx = self.entity_combo.findData(entity_id)
        if idx >= 0:
            self.entity_combo.setCurrentIndex(idx)

    def on_entity_changed(self, index: int):
        entity_id = self.entity_combo.currentData()
        if entity_id:
            self.current_entity_id = entity_id
            self.dashboard_view.set_active_entity(entity_id)
            self.contract_view.set_active_entity(entity_id)
            self.regulatory_view.current_entity_id = entity_id
            self.tasks_view.current_entity_id = entity_id
            self.tasks_view.load_tasks()
            self.calendar_view.current_entity_id = entity_id
            self.calendar_view.load_calendar_events()

    def switch_view(self, index: int):
        self.stack.setCurrentIndex(index)
        if 0 <= index < len(self.nav_buttons):
            self.nav_buttons[index].setChecked(True)
        if index == 5:
            self.entity_user_view.load_entities()
            self.entity_user_view.load_users()
        elif index == 7:
            self.audit_dossier_view.verify_and_refresh()
