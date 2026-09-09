from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class StatCard(QFrame):
    """Reusable executive KPI summary card."""

    def __init__(self, title: str, value: str = "0", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("statTitle")
        
        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.sub_label = QLabel(subtitle)
        self.sub_label.setStyleSheet("color: #64748B; font-size: 11px;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.sub_label)

    def set_value(self, value: str, subtitle: str = ""):
        self.value_label.setText(str(value))
        if subtitle:
            self.sub_label.setText(subtitle)
