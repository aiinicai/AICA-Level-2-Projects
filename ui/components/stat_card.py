"""
LexSecure India Pro - Executive KPI Stat Card Component
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from ui.styles import THEME_COLORS

class StatCard(QFrame):
    def __init__(self, title: str, value: str, subtext: str, badge_text: str = "", badge_color: str = "#10B981"):
        super().__init__()
        self.setProperty("class", "card")
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME_COLORS['bg_card']};
                border: 1px solid {THEME_COLORS['border']};
                border-radius: 10px;
                padding: 14px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)

        # Header Row (Title + Badge)
        top_layout = QHBoxLayout()
        self.title_label = QLabel(title.upper())
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        top_layout.addWidget(self.title_label, 1)

        if badge_text:
            self.badge = QLabel(badge_text)
            self.badge.setStyleSheet(f"""
                background-color: {badge_color};
                color: #FFFFFF;
                font-size: 10px;
                font-weight: bold;
                border-radius: 4px;
                padding: 2px 7px;
            """)
            top_layout.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignRight)
        
        layout.addLayout(top_layout)

        # Large Value
        self.val_label = QLabel(value)
        self.val_label.setStyleSheet(f"color: {THEME_COLORS['text_primary']}; font-size: 24px; font-weight: 800;")
        layout.addWidget(self.val_label)

        # Subtext
        self.sub_label = QLabel(subtext)
        self.sub_label.setWordWrap(True)
        self.sub_label.setStyleSheet(f"color: {THEME_COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(self.sub_label)

    def update_data(self, value: str, subtext: str = "", badge_text: str = ""):
        self.val_label.setText(value)
        if subtext:
            self.sub_label.setText(subtext)
        if hasattr(self, 'badge') and badge_text:
            self.badge.setText(badge_text)
