"""
LexSecure India Pro - Indian Statutory Compliance Calendar
Real-time Countdown Timers & Penalty Risk Surveillance
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from datetime import datetime
from ui.styles import THEME_COLORS
from models.entities import StatutoryCalendarEvent

class CalendarView(QWidget):
    def __init__(self, current_entity_id: int = 1):
        super().__init__()
        self.current_entity_id = current_entity_id
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # Top Control Bar
        top_bar = QFrame()
        top_bar.setStyleSheet(f"""
            background-color: {THEME_COLORS['bg_card']};
            border: 1px solid {THEME_COLORS['border']};
            border-radius: 10px;
            padding: 10px 16px;
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setSpacing(12)

        icon_title = QLabel("📅 INDIAN STATUTORY CALENDAR & PENALTY RISK SURVEILLANCE")
        icon_title.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: bold;")
        top_layout.addWidget(icon_title)

        top_layout.addStretch()

        legend = QLabel("🔴 Overdue/Critical (≤7d)   🟡 Approaching (≤30d)   🟢 Safe (>30d)")
        legend.setStyleSheet("color: #94A3B8; font-size: 11px;")
        top_layout.addWidget(legend)

        main_layout.addWidget(top_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Statutory Body", "Mandatory Statutory Filing / Return", "Due Date",
            "Countdown", "Frequency", "Statutory Penalty Risk Clause"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {THEME_COLORS['bg_card']};
                border: 1px solid {THEME_COLORS['border']};
                border-radius: 8px;
                gridline-color: #334155;
            }}
            QTableWidget::item {{
                padding: 12px;
            }}
        """)
        main_layout.addWidget(self.table, 1)

        self.load_calendar_events()

    def load_calendar_events(self):
        events = StatutoryCalendarEvent.get_by_entity(self.current_entity_id)
        self.table.setRowCount(len(events))
        now = datetime.now().date()

        for row_idx, ev in enumerate(events):
            # Body
            body_item = QTableWidgetItem(ev.statutory_body)
            body_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            body_item.setForeground(Qt.GlobalColor.white)
            self.table.setItem(row_idx, 0, body_item)

            # Name
            name_item = QTableWidgetItem(ev.compliance_name)
            name_item.setFont(self.font())
            self.table.setItem(row_idx, 1, name_item)

            # Date
            date_item = QTableWidgetItem(ev.due_date)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 2, date_item)

            # Countdown Calculation
            try:
                due_dt = datetime.strptime(ev.due_date, "%Y-%m-%d").date()
                days_left = (due_dt - now).days
                if days_left < 0:
                    badge_color = "#EF4444"
                    txt = f"OVERDUE ({abs(days_left)}d)"
                elif days_left <= 7:
                    badge_color = "#EF4444"
                    txt = f"{days_left} DAYS LEFT"
                elif days_left <= 30:
                    badge_color = "#F59E0B"
                    txt = f"{days_left} DAYS LEFT"
                else:
                    badge_color = "#10B981"
                    txt = f"{days_left} DAYS LEFT"
            except Exception:
                badge_color = "#0D9488"
                txt = "SCHEDULED"

            cd_item = QTableWidgetItem(txt)
            cd_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            cd_item.setForeground(Qt.GlobalColor.white)
            cd_item.setBackground(QColor(badge_color))
            self.table.setItem(row_idx, 3, cd_item)

            # Freq
            freq_item = QTableWidgetItem(ev.recurring_freq)
            freq_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 4, freq_item)

            # Penalty
            pen_item = QTableWidgetItem(ev.penalty_clause)
            pen_item.setForeground(QColor("#FCA5A5"))
            self.table.setItem(row_idx, 5, pen_item)
