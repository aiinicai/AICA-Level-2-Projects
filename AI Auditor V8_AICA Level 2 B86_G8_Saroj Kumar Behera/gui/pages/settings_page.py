"""
AI Auditor V8 - Settings & Configuration Page
Allows the user to adjust variance thresholds, materiality cut-offs, default units, and audit preferences.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QDoubleSpinBox,
    QComboBox, QCheckBox, QPushButton, QMessageBox, QGroupBox, QLineEdit
)
from config.settings import AppSettings
from config.constants import UNITS_MAP

class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = AppSettings.load()
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        # Header
        lbl_title = QLabel("Application Settings & Thresholds")
        lbl_title.setProperty("class", "page-title")
        lbl_sub = QLabel("Configure variance analysis sensitivity, default currency units, and analytical preferences.")
        lbl_sub.setProperty("class", "page-subtitle")
        main_layout.addWidget(lbl_title)
        main_layout.addWidget(lbl_sub)

        # Settings Form Group
        group = QGroupBox("Analytical Threshold Configuration")
        g_layout = QVBoxLayout(group)
        g_layout.setContentsMargins(20, 20, 20, 20)
        g_layout.setSpacing(16)

        # 1. Variance Threshold
        row1 = QHBoxLayout()
        lbl1 = QLabel("<b>Default Variance Threshold:</b><br><span style='color:#64748B;font-size:11px;'>Flags any line item where current vs prior period movement exceeds this percentage.</span>")
        self.spin_var = QDoubleSpinBox()
        self.spin_var.setRange(0.5, 100.0)
        self.spin_var.setValue(self.settings.variance_threshold)
        self.spin_var.setSuffix(" %")
        self.spin_var.setFixedWidth(120)
        row1.addWidget(lbl1, 1)
        row1.addWidget(self.spin_var)
        g_layout.addLayout(row1)

        # 2. Materiality Threshold
        row2 = QHBoxLayout()
        lbl2 = QLabel("<b>Minimum Materiality Absolute Amount:</b><br><span style='color:#64748B;font-size:11px;'>Filters out nominal changes even if percentage change is high.</span>")
        self.spin_mat = QDoubleSpinBox()
        self.spin_mat.setRange(0.0, 10000000.0)
        self.spin_mat.setValue(self.settings.materiality_threshold)
        self.spin_mat.setFixedWidth(120)
        row2.addWidget(lbl2, 1)
        row2.addWidget(self.spin_mat)
        g_layout.addLayout(row2)

        # 3. Default Unit
        row3 = QHBoxLayout()
        lbl3 = QLabel("<b>Default Currency & Unit Scale:</b><br><span style='color:#64748B;font-size:11px;'>Preselected multiplier when opening new statements.</span>")
        self.combo_unit = QComboBox()
        for u in UNITS_MAP.keys():
            self.combo_unit.addItem(u)
        self.combo_unit.setCurrentText(self.settings.default_unit)
        self.combo_unit.setFixedWidth(240)
        row3.addWidget(lbl3, 1)
        row3.addWidget(self.combo_unit)
        g_layout.addLayout(row3)

        # 4. Fuzzy Mapping
        self.chk_fuzzy = QCheckBox("Enable RapidFuzz automated taxonomy classification for unusual line names")
        self.chk_fuzzy.setChecked(self.settings.enable_fuzzy_mapping)
        g_layout.addWidget(self.chk_fuzzy)

        main_layout.addWidget(group)

        # Save Button
        btn_save = QPushButton("Save Settings")
        btn_save.setProperty("class", "primary-btn")
        btn_save.setFixedWidth(180)
        btn_save.clicked.connect(self._save_settings)
        main_layout.addWidget(btn_save)

        main_layout.addStretch()

    def _save_settings(self):
        self.settings.variance_threshold = self.spin_var.value()
        self.settings.materiality_threshold = self.spin_mat.value()
        self.settings.default_unit = self.combo_unit.currentText()
        self.settings.enable_fuzzy_mapping = self.chk_fuzzy.isChecked()
        self.settings.save()
        QMessageBox.information(self, "Settings Saved", "Preferences updated successfully!")
