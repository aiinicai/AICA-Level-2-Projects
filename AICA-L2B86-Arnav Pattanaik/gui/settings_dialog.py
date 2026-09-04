"""Settings modal — default ED/DPS rates, firm name, DISCOM name."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
    QPushButton, QFrame, QComboBox, QApplication,
)

from gui.app_state import AppState
from gui.styles import THEMES, get_theme_stylesheet


class SettingsDialog(QDialog):
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.setWindowTitle("Settings")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Settings")
        title.setObjectName("screenTitle")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        # UI Theme
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("App Theme"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        current_theme = getattr(self.state.settings, "theme_name", "Dark")
        if current_theme in THEMES:
            self.theme_combo.setCurrentText(current_theme)
        theme_row.addWidget(self.theme_combo)
        card_layout.addLayout(theme_row)

        # Firm name
        card_layout.addWidget(QLabel("Audit Firm Name"))
        self.firm_edit = QLineEdit(self.state.settings.audit_firm_name)
        card_layout.addWidget(self.firm_edit)

        # DISCOM name
        card_layout.addWidget(QLabel("DISCOM Name"))
        self.discom_edit = QLineEdit(self.state.settings.discom_name)
        card_layout.addWidget(self.discom_edit)

        # Electricity Duty rate
        ed_row = QHBoxLayout()
        ed_row.addWidget(QLabel("Default Electricity Duty Rate (%)"))
        self.ed_spin = QDoubleSpinBox()
        self.ed_spin.setRange(0, 100)
        self.ed_spin.setDecimals(2)
        self.ed_spin.setValue(self.state.settings.default_electricity_duty_rate)
        ed_row.addWidget(self.ed_spin)
        card_layout.addLayout(ed_row)

        ed_note = QLabel(
            "Not specified in most tariff orders — set this per the applicable "
            "state Electricity Duty Act notification."
        )
        ed_note.setWordWrap(True)
        ed_note.setStyleSheet("font-size: 10px; color: #94a3b8;")
        card_layout.addWidget(ed_note)

        # DPS rate
        dps_row = QHBoxLayout()
        dps_row.addWidget(QLabel("Default DPS Rate (% per month)"))
        self.dps_spin = QDoubleSpinBox()
        self.dps_spin.setRange(0, 100)
        self.dps_spin.setDecimals(2)
        self.dps_spin.setValue(self.state.settings.default_dps_rate)
        dps_row.addWidget(self.dps_spin)
        card_layout.addLayout(dps_row)

        layout.addWidget(card)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _save(self):
        selected_theme = self.theme_combo.currentText()
        self.state.settings.theme_name = selected_theme
        self.state.settings.audit_firm_name = self.firm_edit.text().strip()
        self.state.settings.discom_name = self.discom_edit.text().strip()
        self.state.settings.default_electricity_duty_rate = self.ed_spin.value()
        self.state.settings.default_dps_rate = self.dps_spin.value()

        # Update application stylesheet live
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_theme_stylesheet(selected_theme))

        # Save session to persist settings
        try:
            from core.session_manager import save_session
            save_session(self.state)
        except Exception:
            pass

        self.accept()
