from decimal import Decimal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QLineEdit,
    QComboBox,
    QPushButton,
    QDialogButtonBox,
    QLabel,
)
from PyQt6.QtCore import Qt

from reconai.config import AppConfig


class SettingsDialog(QDialog):
    """Configuration modal dialog for thresholds, compliance toggles, and API keys."""

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("ReconAI — Settings & Threshold Configuration")
        self.setMinimumWidth(540)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # 1. Reconciliation Tolerances
        recon_group = QGroupBox("Reconciliation Rules & Tolerances")
        recon_form = QFormLayout(recon_group)

        self.date_tol_spin = QSpinBox()
        self.date_tol_spin.setRange(0, 30)
        self.date_tol_spin.setValue(self.config.reconciliation.date_tolerance_days)
        self.date_tol_spin.setSuffix(" days")
        recon_form.addRow("Date Difference Window:", self.date_tol_spin)

        self.amt_tol_spin = QDoubleSpinBox()
        self.amt_tol_spin.setRange(0.0, 1000.0)
        self.amt_tol_spin.setValue(float(self.config.reconciliation.amount_tolerance))
        self.amt_tol_spin.setPrefix("₹ ")
        recon_form.addRow("Allowed Amount Discrepancy:", self.amt_tol_spin)

        self.fuzzy_spin = QDoubleSpinBox()
        self.fuzzy_spin.setRange(40.0, 100.0)
        self.fuzzy_spin.setValue(self.config.reconciliation.fuzzy_narration_threshold)
        self.fuzzy_spin.setSuffix(" %")
        recon_form.addRow("Narration Similarity Threshold:", self.fuzzy_spin)

        layout.addWidget(recon_group)

        # 2. Expense Audit Rules & Thresholds
        audit_group = QGroupBox("Expense Audit Rules & Thresholds")
        audit_form = QFormLayout(audit_group)

        self.round_amt_spin = QDoubleSpinBox()
        self.round_amt_spin.setRange(1000.0, 10000000.0)
        self.round_amt_spin.setValue(float(self.config.audit.round_amount_threshold))
        self.round_amt_spin.setPrefix("₹ ")
        self.round_amt_spin.setSingleStep(5000.0)
        audit_form.addRow("Round Amount Threshold:", self.round_amt_spin)

        self.appr_amt_spin = QDoubleSpinBox()
        self.appr_amt_spin.setRange(1000.0, 10000000.0)
        self.appr_amt_spin.setValue(float(self.config.audit.high_value_approval_threshold))
        self.appr_amt_spin.setPrefix("₹ ")
        self.appr_amt_spin.setSingleStep(10000.0)
        audit_form.addRow("High Value Approval Threshold:", self.appr_amt_spin)

        self.weekend_chk = QCheckBox("Flag Saturday / Sunday Transactions")
        self.weekend_chk.setChecked(self.config.audit.flag_weekend_transactions)
        audit_form.addRow("Weekend Checks:", self.weekend_chk)

        self.gst_tds_chk = QCheckBox("Enable Indian Statutory GSTIN & TDS Validation")
        self.gst_tds_chk.setChecked(self.config.audit.enable_gst_tds_compliance)
        audit_form.addRow("Statutory Compliance:", self.gst_tds_chk)

        layout.addWidget(audit_group)

        # 3. AI & Theme Settings
        ai_group = QGroupBox("AI Assistant & Application Preferences")
        ai_form = QFormLayout(ai_group)

        self.ai_enabled_chk = QCheckBox("Enable AI Semantic Matching & Forensic Insights")
        self.ai_enabled_chk.setChecked(self.config.reconciliation.enable_ai_matcher)
        ai_form.addRow("AI Assistant:", self.ai_enabled_chk)

        self.ai_model_combo = QComboBox()
        self.ai_model_combo.setEditable(True)
        self.ai_model_combo.addItems([
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-1.5-flash",
            "claude-3-5-sonnet-20241022",
            "claude-3-haiku-20240307",
        ])
        current_model = self.config.reconciliation.ai_model or "gemini-2.5-flash"
        model_idx = self.ai_model_combo.findText(current_model)
        if model_idx >= 0:
            self.ai_model_combo.setCurrentIndex(model_idx)
        else:
            self.ai_model_combo.setEditText(current_model)
        ai_form.addRow("AI Model (Gemini / Claude):", self.ai_model_combo)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setText(self.config.reconciliation.api_key or "")
        self.api_key_edit.setPlaceholderText("Enter Gemini (AIza...) or Claude (sk-ant-...) API Key")
        ai_form.addRow("API Key (Gemini / Claude):", self.api_key_edit)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark (Slate / Deep Navy)", "Light (Clean Financial)"])
        self.theme_combo.setCurrentIndex(0 if self.config.theme == "dark" else 1)
        ai_form.addRow("UI Appearance Theme:", self.theme_combo)

        layout.addWidget(ai_group)

        # 4. Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _save_and_accept(self):
        # Update config
        self.config.reconciliation.date_tolerance_days = self.date_tol_spin.value()
        self.config.reconciliation.amount_tolerance = Decimal(str(self.amt_tol_spin.value()))
        self.config.reconciliation.fuzzy_narration_threshold = self.fuzzy_spin.value()
        self.config.reconciliation.enable_ai_matcher = self.ai_enabled_chk.isChecked()
        
        api_key = self.api_key_edit.text().strip()
        self.config.reconciliation.api_key = api_key if api_key else None
        self.config.reconciliation.ai_model = self.ai_model_combo.currentText().strip()

        self.config.audit.round_amount_threshold = Decimal(str(self.round_amt_spin.value()))
        self.config.audit.high_value_approval_threshold = Decimal(str(self.appr_amt_spin.value()))
        self.config.audit.flag_weekend_transactions = self.weekend_chk.isChecked()
        self.config.audit.enable_gst_tds_compliance = self.gst_tds_chk.isChecked()
        self.config.audit.enable_ai_audit = self.ai_enabled_chk.isChecked()

        self.config.theme = "dark" if self.theme_combo.currentIndex() == 0 else "light"

        self.accept()
