"""
LexSecure India Pro - Granular Access Matrix & Role-Based Access Control (RBAC)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from ui.styles import THEME_COLORS
from database.db_engine import DatabaseEngine
from models.entities import AccessMatrixRule

class AccessMatrixView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseEngine.get_instance()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Top Bar
        top_bar = QFrame()
        top_bar.setStyleSheet(f"""
            background-color: {THEME_COLORS['bg_card']};
            border: 1px solid {THEME_COLORS['border']};
            border-radius: 10px;
            padding: 10px 16px;
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setSpacing(12)

        icon_title = QLabel("🛡️ ENTERPRISE ROLE-BASED ACCESS CONTROL (RBAC) MATRIX")
        icon_title.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: bold;")
        top_layout.addWidget(icon_title)

        top_layout.addStretch()

        legend = QLabel("✔ Permitted   ✖ Restricted   🔒 Sign-off Authority")
        legend.setStyleSheet("color: #94A3B8; font-size: 11px;")
        top_layout.addWidget(legend)

        main_layout.addWidget(top_bar)

        # Access Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Enterprise Role", "Target Resource", "Create", "Read", "Update", "Delete", "Sign-Off"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {THEME_COLORS['bg_card']};
                border: 1px solid {THEME_COLORS['border']};
                border-radius: 8px;
                gridline-color: #334155;
            }}
            QTableWidget::item {{
                padding: 10px;
            }}
        """)
        main_layout.addWidget(self.table, 1)

        self.load_matrix()

    def load_matrix(self):
        rules = AccessMatrixRule.get_all()
        self.table.setRowCount(len(rules))

        for row_idx, r in enumerate(rules):
            # Role
            role_item = QTableWidgetItem(r.role.replace("_", " "))
            role_item.setFont(self.font())
            role_item.setForeground(QColor("#38BDF8") if "COUNSEL" in r.role else QColor("#F8FAFC"))
            self.table.setItem(row_idx, 0, role_item)

            # Resource
            res_item = QTableWidgetItem(r.resource)
            res_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 1, res_item)

            # Actions
            actions = [r.can_create, r.can_read, r.can_update, r.can_delete, r.can_signoff]
            for col_idx, allowed in enumerate(actions, start=2):
                if col_idx == 6:  # Signoff
                    symbol = "🔒 YES" if allowed else "✖ NO"
                    color = "#10B981" if allowed else "#64748B"
                else:
                    symbol = "✔ YES" if allowed else "✖ NO"
                    color = "#10B981" if allowed else "#64748B"

                item = QTableWidgetItem(symbol)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QColor(color))
                self.table.setItem(row_idx, col_idx, item)
