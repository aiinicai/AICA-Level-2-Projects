"""
AI Auditor V8 - Metric KPI Card Widget
Custom card widget displaying KPI value, delta, benchmark, and health badge.
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class MetricCard(QFrame):
    def __init__(self, title: str, value: str, subtext: str = "", tag: str = "Normal", parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setMinimumHeight(105)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        # Header Row: Title + Tag Pill
        top_row = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: #64748B; font-size: 11.5px; font-weight: 600; text-transform: uppercase;")
        top_row.addWidget(self.lbl_title)
        top_row.addStretch()

        self.lbl_tag = QLabel(f" {tag} ")
        self._set_tag_style(tag)
        top_row.addWidget(self.lbl_tag)
        layout.addLayout(top_row)

        # Value Label
        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet("color: #0F172A; font-size: 20px; font-weight: bold;")
        layout.addWidget(self.lbl_value)

        # Subtext / Delta
        self.lbl_subtext = QLabel(subtext)
        self.lbl_subtext.setStyleSheet("color: #64748B; font-size: 11px;")
        layout.addWidget(self.lbl_subtext)

    def update_data(self, value: str, subtext: str = "", tag: str = "Normal"):
        self.lbl_value.setText(value)
        self.lbl_subtext.setText(subtext)
        self.lbl_tag.setText(f" {tag} ")
        self._set_tag_style(tag)

    def _set_tag_style(self, tag: str):
        t = tag.lower()
        if "healthy" in t or "growth" in t or "low" in t:
            self.lbl_tag.setStyleSheet("background-color: #DEF7EC; color: #03543F; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px 6px;")
        elif "attention" in t or "medium" in t or "decline" in t:
            self.lbl_tag.setStyleSheet("background-color: #FEF08A; color: #854D0E; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px 6px;")
        elif "critical" in t or "high" in t or "loss" in t:
            self.lbl_tag.setStyleSheet("background-color: #FEE2E2; color: #991B1B; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px 6px;")
        else:
            self.lbl_tag.setStyleSheet("background-color: #F1F5F9; color: #475569; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px 6px;")
