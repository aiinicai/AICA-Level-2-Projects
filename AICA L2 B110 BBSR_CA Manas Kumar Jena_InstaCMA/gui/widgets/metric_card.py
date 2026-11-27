"""Dashboard metric card."""
from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout

from gui.theme import STATUS_COLOURS


class MetricCard(QFrame):
    def __init__(self, title, value="-", sub="", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumHeight(96)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        self.t = QLabel(title)
        self.t.setObjectName("CardTitle")
        self.v = QLabel(value)
        self.v.setObjectName("CardValue")
        self.s = QLabel(sub)
        self.s.setObjectName("CardSub")
        self.s.setWordWrap(True)
        lay.addWidget(self.t)
        lay.addWidget(self.v)
        lay.addWidget(self.s)

    def set(self, value, sub="", status=None):
        self.v.setText(str(value))
        self.s.setText(sub)
        colour = STATUS_COLOURS.get(status or "", None)
        if colour:
            self.setStyleSheet("QFrame#Card { background: %s; border: 1px solid #DDE3EC; border-radius: 8px; }"
                               % colour)
        else:
            self.setStyleSheet("")
