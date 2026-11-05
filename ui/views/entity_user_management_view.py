"""
LexSecure India Pro - Entity & User Governance View
Add / Modify / Delete Operating Entities and Enterprise User Identities
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QDialog, QLineEdit, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from ui.styles import THEME_COLORS
from models.entities import Entity, User, Department
from database.db_engine import DatabaseEngine

class EntityUserManagementView(QWidget):
    entities_changed = pyqtSignal()
    users_changed = pyqtSignal()
    audit_event_logged = pyqtSignal()

    def __init__(self, current_org_id: int = 1):
        super().__init__()
        self.current_org_id = current_org_id
        self.db = DatabaseEngine.get_instance()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Header Title
        top_bar = QFrame()
        top_bar.setStyleSheet(f"""
            background-color: {THEME_COLORS['bg_card']};
            border: 1px solid {THEME_COLORS['border']};
            border-radius: 10px;
            padding: 12px 18px;
        """)
        top_layout = QHBoxLayout(top_bar)
        
        title_box = QVBoxLayout()
        title = QLabel("🏢 CORPORATE GOVERNANCE: ENTITY & USER MANAGEMENT")
        title.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: bold;")
        title_box.addWidget(title)

        subtitle = QLabel("Provision operating subsidiaries, manage corporate roles, set security PINs, and administer departments.")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 11px;")
        title_box.addWidget(subtitle)
        top_layout.addLayout(title_box)

        main_layout.addWidget(top_bar)

        # Tabs: Entities vs Users
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {THEME_COLORS['border']};
                background: {THEME_COLORS['bg_card']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background: #0B1120;
                color: #94A3B8;
                padding: 9px 20px;
                font-weight: bold;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {THEME_COLORS['bg_card']};
                color: #10B981;
                border-bottom: 2px solid #10B981;
            }}
        """)

        # Tab 1: Entities Management
        self.entities_tab = self.create_entities_tab()
        self.tabs.addTab(self.entities_tab, "🏢 Operating Subsidiaries & Entities")

        # Tab 2: Users Management
        self.users_tab = self.create_users_tab()
        self.tabs.addTab(self.users_tab, "👥 User Accounts & Credentials")

        main_layout.addWidget(self.tabs, 1)

        self.load_entities()
        self.load_users()

    # ==========================
    # ENTITIES TAB
    # ==========================
    def create_entities_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Action bar
        act_row = QHBoxLayout()
        add_btn = QPushButton("➕ Add New Entity")
        add_btn.setProperty("class", "btn-emerald")
        add_btn.clicked.connect(self.open_add_entity_dialog)
        act_row.addWidget(add_btn)

        edit_btn = QPushButton("✏️ Modify Selected")
        edit_btn.setProperty("class", "btn-primary")
        edit_btn.clicked.connect(self.open_edit_entity_dialog)
        act_row.addWidget(edit_btn)

        del_btn = QPushButton("🗑️ Delete Selected")
        del_btn.setProperty("class", "btn-danger")
        del_btn.clicked.connect(self.delete_selected_entity)
        act_row.addWidget(del_btn)

        act_row.addStretch()

        ref_btn = QPushButton("🔄 Refresh")
        ref_btn.setProperty("class", "btn-outline")
        ref_btn.clicked.connect(self.load_entities)
        act_row.addWidget(ref_btn)

        layout.addLayout(act_row)

        # Entity Table
        self.entity_table = QTableWidget()
        self.entity_table.setColumnCount(5)
        self.entity_table.setHorizontalHeaderLabels([
            "ID", "Legal Business Name", "Entity Structure", "Registered State (India)", "Departments"
        ])
        self.entity_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.entity_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.entity_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.entity_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.entity_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.entity_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.entity_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        layout.addWidget(self.entity_table, 1)
        return widget

    def load_entities(self):
        self.entities = Entity.get_all(self.current_org_id)
        self.entity_table.setRowCount(len(self.entities))

        for row_idx, e in enumerate(self.entities):
            # ID
            id_item = QTableWidgetItem(str(e.id))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.entity_table.setItem(row_idx, 0, id_item)

            # Name
            name_item = QTableWidgetItem(e.legal_name)
            name_item.setFont(self.font())
            self.entity_table.setItem(row_idx, 1, name_item)

            # Type
            type_item = QTableWidgetItem(e.entity_type.replace("_", " "))
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            type_item.setForeground(QColor("#38BDF8"))
            self.entity_table.setItem(row_idx, 2, type_item)

            # State
            state_item = QTableWidgetItem(e.registered_state)
            state_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.entity_table.setItem(row_idx, 3, state_item)

            # Depts
            depts = Department.get_by_entity(e.id)
            dept_item = QTableWidgetItem(f"{len(depts)} Departments")
            dept_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            dept_item.setForeground(QColor("#10B981"))
            self.entity_table.setItem(row_idx, 4, dept_item)

    def open_add_entity_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Operating Entity / Subsidiary")
        dialog.setFixedSize(480, 320)
        dialog.setStyleSheet(f"background-color: {THEME_COLORS['bg_main']}; color: #F8FAFC;")
        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(20, 20, 20, 20)
        d_layout.setSpacing(12)

        d_layout.addWidget(QLabel("<b>Legal Entity Name:</b>"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("e.g. Apex Bio-Pharma Private Limited")
        d_layout.addWidget(name_input)

        d_layout.addWidget(QLabel("<b>Entity Legal Structure:</b>"))
        type_combo = QComboBox()
        type_combo.addItems(["PVT_LTD", "PUBLIC_LTD", "LLP", "PARTNERSHIP"])
        d_layout.addWidget(type_combo)

        d_layout.addWidget(QLabel("<b>Registered State (India):</b>"))
        state_combo = QComboBox()
        states = [
            "Karnataka", "Maharashtra", "Delhi", "Telangana", "Tamil Nadu",
            "Gujarat", "Haryana", "Uttar Pradesh", "West Bengal", "Rajasthan"
        ]
        state_combo.addItems(states)
        d_layout.addWidget(state_combo)

        btn_box = QHBoxLayout()
        can_btn = QPushButton("Cancel")
        can_btn.setProperty("class", "btn-outline")
        can_btn.clicked.connect(dialog.reject)
        btn_box.addWidget(can_btn)

        save_btn = QPushButton("✔ Create Entity & Provision Departments")
        save_btn.setProperty("class", "btn-emerald")
        def save():
            name = name_input.text().strip()
            if not name:
                QMessageBox.warning(dialog, "Required", "Please provide a valid legal entity name.")
                return
            new_id = Entity.create(self.current_org_id, name, type_combo.currentText(), state_combo.currentText())
            self.load_entities()
            self.entities_changed.emit()
            self.audit_event_logged.emit()
            dialog.accept()
            QMessageBox.information(self, "Success", f"Entity '{name}' created successfully with 5 auto-provisioned departments!")

        save_btn.clicked.connect(save)
        btn_box.addWidget(save_btn)
        d_layout.addLayout(btn_box)

        dialog.exec()

    def open_edit_entity_dialog(self):
        row = self.entity_table.currentRow()
        if row < 0 or row >= len(self.entities):
            QMessageBox.warning(self, "Select Entity", "Please select an entity from the table to modify.")
            return

        entity = self.entities[row]
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Modify Entity — {entity.legal_name}")
        dialog.setFixedSize(480, 320)
        dialog.setStyleSheet(f"background-color: {THEME_COLORS['bg_main']}; color: #F8FAFC;")
        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(20, 20, 20, 20)
        d_layout.setSpacing(12)

        d_layout.addWidget(QLabel("<b>Legal Entity Name:</b>"))
        name_input = QLineEdit(entity.legal_name)
        d_layout.addWidget(name_input)

        d_layout.addWidget(QLabel("<b>Entity Legal Structure:</b>"))
        type_combo = QComboBox()
        type_combo.addItems(["PVT_LTD", "PUBLIC_LTD", "LLP", "PARTNERSHIP"])
        type_combo.setCurrentText(entity.entity_type)
        d_layout.addWidget(type_combo)

        d_layout.addWidget(QLabel("<b>Registered State (India):</b>"))
        state_combo = QComboBox()
        states = [
            "Karnataka", "Maharashtra", "Delhi", "Telangana", "Tamil Nadu",
            "Gujarat", "Haryana", "Uttar Pradesh", "West Bengal", "Rajasthan"
        ]
        state_combo.addItems(states)
        state_combo.setCurrentText(entity.registered_state)
        d_layout.addWidget(state_combo)

        btn_box = QHBoxLayout()
        can_btn = QPushButton("Cancel")
        can_btn.setProperty("class", "btn-outline")
        can_btn.clicked.connect(dialog.reject)
        btn_box.addWidget(can_btn)

        save_btn = QPushButton("✔ Save Changes")
        save_btn.setProperty("class", "btn-emerald")
        def save():
            name = name_input.text().strip()
            if not name:
                QMessageBox.warning(dialog, "Required", "Entity name cannot be empty.")
                return
            Entity.update(entity.id, name, type_combo.currentText(), state_combo.currentText())
            self.load_entities()
            self.entities_changed.emit()
            self.audit_event_logged.emit()
            dialog.accept()
            QMessageBox.information(self, "Updated", f"Entity '{name}' updated successfully.")

        save_btn.clicked.connect(save)
        btn_box.addWidget(save_btn)
        d_layout.addLayout(btn_box)

        dialog.exec()

    def delete_selected_entity(self):
        row = self.entity_table.currentRow()
        if row < 0 or row >= len(self.entities):
            QMessageBox.warning(self, "Select Entity", "Please select an entity from the table to delete.")
            return

        entity = self.entities[row]
        if len(self.entities) <= 1:
            QMessageBox.critical(self, "Action Prohibited", "Cannot delete the sole remaining operating entity of the organization.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete entity '{entity.legal_name}'?\nThis will remove all associated records from active view.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            Entity.delete(entity.id)
            self.load_entities()
            self.entities_changed.emit()
            self.audit_event_logged.emit()
            QMessageBox.information(self, "Deleted", f"Entity #{entity.id} removed successfully.")

    # ==========================
    # USERS TAB
    # ==========================
    def create_users_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Action bar
        act_row = QHBoxLayout()
        add_btn = QPushButton("➕ Add New User")
        add_btn.setProperty("class", "btn-emerald")
        add_btn.clicked.connect(self.open_add_user_dialog)
        act_row.addWidget(add_btn)

        edit_btn = QPushButton("✏️ Modify User / PIN")
        edit_btn.setProperty("class", "btn-primary")
        edit_btn.clicked.connect(self.open_edit_user_dialog)
        act_row.addWidget(edit_btn)

        del_btn = QPushButton("🗑️ Deactivate User")
        del_btn.setProperty("class", "btn-danger")
        del_btn.clicked.connect(self.deactivate_selected_user)
        act_row.addWidget(del_btn)

        act_row.addStretch()

        ref_btn = QPushButton("🔄 Refresh")
        ref_btn.setProperty("class", "btn-outline")
        ref_btn.clicked.connect(self.load_users)
        act_row.addWidget(ref_btn)

        layout.addLayout(act_row)

        # Users Table
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels([
            "ID", "Full Legal Name", "Corporate Email", "Role Authority", "Access PIN", "Status"
        ])
        self.user_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.user_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.user_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.user_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.user_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        layout.addWidget(self.user_table, 1)
        return widget

    def load_users(self):
        self.users = User.get_all(self.current_org_id)
        self.user_table.setRowCount(len(self.users))

        for row_idx, u in enumerate(self.users):
            # ID
            id_item = QTableWidgetItem(str(u.id))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.user_table.setItem(row_idx, 0, id_item)

            # Name
            name_item = QTableWidgetItem(u.full_name)
            name_item.setFont(self.font())
            self.user_table.setItem(row_idx, 1, name_item)

            # Email
            email_item = QTableWidgetItem(u.email)
            email_item.setForeground(QColor("#38BDF8"))
            self.user_table.setItem(row_idx, 2, email_item)

            # Role
            role_item = QTableWidgetItem(u.role.replace("_", " "))
            role_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            role_item.setForeground(QColor("#10B981") if "COUNSEL" in u.role else QColor("#F59E0B"))
            self.user_table.setItem(row_idx, 3, role_item)

            # PIN
            pin_val = getattr(u, 'password_hash', '1234') or '1234'
            pin_item = QTableWidgetItem(f"🔑 {pin_val}")
            pin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            pin_item.setForeground(QColor("#CBD5E1"))
            self.user_table.setItem(row_idx, 4, pin_item)

            # Status
            status_item = QTableWidgetItem("Active ✔")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setForeground(QColor("#10B981"))
            self.user_table.setItem(row_idx, 5, status_item)

    def open_add_user_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Enterprise User")
        dialog.setFixedSize(480, 380)
        dialog.setStyleSheet(f"background-color: {THEME_COLORS['bg_main']}; color: #F8FAFC;")
        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(20, 20, 20, 20)
        d_layout.setSpacing(12)

        d_layout.addWidget(QLabel("<b>Full Legal Name:</b>"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("e.g. Adv. Priya Sharma")
        d_layout.addWidget(name_input)

        d_layout.addWidget(QLabel("<b>Corporate Email Address:</b>"))
        email_input = QLineEdit()
        email_input.setPlaceholderText("e.g. priya.sharma@apexindia.com")
        d_layout.addWidget(email_input)

        d_layout.addWidget(QLabel("<b>Enterprise Role Authority:</b>"))
        role_combo = QComboBox()
        role_combo.addItems(["GENERAL_COUNSEL", "COMPLIANCE_OFFICER", "DEPT_LEAD", "AUDITOR"])
        d_layout.addWidget(role_combo)

        d_layout.addWidget(QLabel("<b>Security PIN / Password:</b>"))
        pin_input = QLineEdit("1234")
        d_layout.addWidget(pin_input)

        btn_box = QHBoxLayout()
        can_btn = QPushButton("Cancel")
        can_btn.setProperty("class", "btn-outline")
        can_btn.clicked.connect(dialog.reject)
        btn_box.addWidget(can_btn)

        save_btn = QPushButton("✔ Register User")
        save_btn.setProperty("class", "btn-emerald")
        def save():
            name = name_input.text().strip()
            email = email_input.text().strip()
            pin = pin_input.text().strip() or "1234"
            if not name or not email:
                QMessageBox.warning(dialog, "Required", "Please provide full name and email.")
                return
            new_id = User.create(self.current_org_id, email, name, role_combo.currentText(), None, pin)
            self.load_users()
            self.users_changed.emit()
            self.audit_event_logged.emit()
            dialog.accept()
            QMessageBox.information(self, "User Registered", f"User '{name}' registered with PIN '{pin}'.")

        save_btn.clicked.connect(save)
        btn_box.addWidget(save_btn)
        d_layout.addLayout(btn_box)

        dialog.exec()

    def open_edit_user_dialog(self):
        row = self.user_table.currentRow()
        if row < 0 or row >= len(self.users):
            QMessageBox.warning(self, "Select User", "Please select a user from the table to modify.")
            return

        user = self.users[row]
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Modify User — {user.full_name}")
        dialog.setFixedSize(480, 380)
        dialog.setStyleSheet(f"background-color: {THEME_COLORS['bg_main']}; color: #F8FAFC;")
        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(20, 20, 20, 20)
        d_layout.setSpacing(12)

        d_layout.addWidget(QLabel("<b>Full Legal Name:</b>"))
        name_input = QLineEdit(user.full_name)
        d_layout.addWidget(name_input)

        d_layout.addWidget(QLabel("<b>Corporate Email Address:</b>"))
        email_input = QLineEdit(user.email)
        d_layout.addWidget(email_input)

        d_layout.addWidget(QLabel("<b>Enterprise Role Authority:</b>"))
        role_combo = QComboBox()
        role_combo.addItems(["GENERAL_COUNSEL", "COMPLIANCE_OFFICER", "DEPT_LEAD", "AUDITOR"])
        role_combo.setCurrentText(user.role)
        d_layout.addWidget(role_combo)

        d_layout.addWidget(QLabel("<b>Update Security PIN / Password:</b>"))
        pin_val = getattr(user, 'password_hash', '1234') or '1234'
        pin_input = QLineEdit(pin_val)
        d_layout.addWidget(pin_input)

        btn_box = QHBoxLayout()
        can_btn = QPushButton("Cancel")
        can_btn.setProperty("class", "btn-outline")
        can_btn.clicked.connect(dialog.reject)
        btn_box.addWidget(can_btn)

        save_btn = QPushButton("✔ Save User Details")
        save_btn.setProperty("class", "btn-emerald")
        def save():
            name = name_input.text().strip()
            email = email_input.text().strip()
            pin = pin_input.text().strip() or "1234"
            if not name or not email:
                QMessageBox.warning(dialog, "Required", "Full name and email cannot be empty.")
                return
            User.update(user.id, name, email, role_combo.currentText(), user.department_id, pin)
            self.load_users()
            self.users_changed.emit()
            self.audit_event_logged.emit()
            dialog.accept()
            QMessageBox.information(self, "Updated", f"User '{name}' updated successfully.")

        save_btn.clicked.connect(save)
        btn_box.addWidget(save_btn)
        d_layout.addLayout(btn_box)

        dialog.exec()

    def deactivate_selected_user(self):
        row = self.user_table.currentRow()
        if row < 0 or row >= len(self.users):
            QMessageBox.warning(self, "Select User", "Please select a user to deactivate.")
            return

        user = self.users[row]
        if len(self.users) <= 1:
            QMessageBox.critical(self, "Action Prohibited", "Cannot deactivate the sole remaining active user.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Deactivation",
            f"Are you sure you want to deactivate user '{user.full_name}' ({user.email})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            User.delete(user.id)
            self.load_users()
            self.users_changed.emit()
            self.audit_event_logged.emit()
            QMessageBox.information(self, "Deactivated", f"User '{user.full_name}' deactivated successfully.")
