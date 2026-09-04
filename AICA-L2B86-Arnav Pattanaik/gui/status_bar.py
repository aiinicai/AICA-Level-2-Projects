"""Persistent bottom status bar, mirrors the AI Studio UI's status strip under the sidebar."""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel
from gui.app_state import AppState


class StatusBar(QFrame):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("statusBar")
        self.setFixedHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)

        self.label = QLabel()
        self.label.setObjectName("statusLabel")
        layout.addWidget(self.label)
        layout.addStretch()

        self.refresh()

    def refresh(self):
        s = self.state
        if not s.is_compiled:
            text = f"Period: {s.billing_month} {s.billing_year}  •  No data compiled yet"
        else:
            text = (
                f"Period: {s.billing_month} {s.billing_year}  •  "
                f"{s.total_divisions_compiled} division(s) compiled  •  "
                f"{s.total_rows_read - s.total_rows_rejected:,} consumer rows  •  "
                f"Last compiled: {s.compile_timestamp}"
            )
        self.label.setText(text)
