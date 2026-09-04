"""Left sidebar navigation, mirrors the AI Studio UI's Sidebar.tsx."""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel, QButtonGroup, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal

from gui.app_state import AppState

SCREENS = [
    ("compile", "1. Compile Data"),
    ("export", "2. Export"),
    ("summaries", "3. Summaries"),
    ("query_builder", "4. Query Builder"),
    ("energy_audit", "5. EC Audit"),
]


class Sidebar(QFrame):
    screen_selected = pyqtSignal(str)
    new_audit_requested = pyqtSignal()

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("sidebar")
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(0)

        title = QLabel("DISCOM Audit\nData Compiler")
        title.setStyleSheet("font-size: 15px; font-weight: 700; padding: 8px 16px 20px 16px;")
        layout.addWidget(title)

        self.buttons: dict[str, QPushButton] = {}
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        for key, label in SCREENS:
            btn = QPushButton(label)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._on_click(k))
            layout.addWidget(btn)
            self.buttons[key] = btn
            self.button_group.addButton(btn)

        self.buttons["compile"].setChecked(True)

        layout.addStretch()

        new_audit_btn = QPushButton("🔄  New Audit")
        new_audit_btn.setObjectName("navButton")
        new_audit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_audit_btn.clicked.connect(self._on_new_audit_click)
        layout.addWidget(new_audit_btn)
        self.new_audit_button = new_audit_btn

        settings_btn = QPushButton("⚙  Settings")
        settings_btn.setObjectName("navButton")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(settings_btn)
        self.settings_button = settings_btn

        self._refresh_lock_state()

    def _on_new_audit_click(self):
        if not self.state.is_compiled and not self.state.uploaded_files:
            return

        res = QMessageBox.question(
            self,
            "Start New Audit Session?",
            "Are you sure you want to exit the current activity and start a new audit?\n\n"
            "This will clear the current compiled data and allow you to upload fresh division files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            self.new_audit_requested.emit()

    def _on_click(self, key: str):
        if key != "compile" and not self.state.screens_unlocked:
            # Refuse navigation, snap selection back to Compile screen
            self.buttons["compile"].setChecked(True)
            return
        self.screen_selected.emit(key)

    def _refresh_lock_state(self):
        unlocked = self.state.screens_unlocked
        for key in ("export", "summaries", "query_builder", "energy_audit"):
            btn = self.buttons[key]
            btn.setEnabled(True)  # keep clickable so we can show a hint on click, but style as locked
            if not unlocked:
                btn.setToolTip("Complete a successful compile on Screen 1 first")
            else:
                btn.setToolTip("")

    def refresh(self):
        self._refresh_lock_state()

    def select(self, key: str):
        if key in self.buttons:
            self.buttons[key].setChecked(True)
