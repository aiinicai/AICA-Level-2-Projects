"""
Settings and Preferences Dialog for TDS & TCS Certificate PDF Auto-Renamer.
Configures renaming templates, collision policies, execution modes, and OCR settings.
"""

from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QRadioButton,
    QButtonGroup,
    QGroupBox,
    QCheckBox,
    QFileDialog,
    QSpinBox,
    QMessageBox,
)

from config import (
    AppConfig,
    NAMING_TEMPLATES,
    COLLISION_AUTO_INCREMENT,
    COLLISION_DISAMBIGUATE,
    COLLISION_SKIP,
    MODE_RENAME_IN_PLACE,
    MODE_COPY_TO_FOLDER,
    MODE_MOVE_TO_FOLDER,
)
from core.models import CertificateData
from core.renamer import CertificateRenamer


class SettingsDialog(QDialog):
    """Settings modal allowing interactive template building and operational preferences."""

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings & Naming Preferences")
        self.resize(680, 580)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # ----------------------------------------------------------------------
        # 1. Naming Template Configuration
        # ----------------------------------------------------------------------
        template_group = QGroupBox("Renaming Format Template")
        tmpl_layout = QVBoxLayout()

        # Preset selection
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset Template:"))
        self.preset_combo = QComboBox()
        for p in NAMING_TEMPLATES:
            self.preset_combo.addItem(p["name"], p["template"])
        self.preset_combo.addItem("Custom Template...", "CUSTOM")
        preset_row.addWidget(self.preset_combo, 1)
        tmpl_layout.addLayout(preset_row)

        # Template string input
        self.template_input = QLineEdit(self.config.naming_template)
        tmpl_layout.addWidget(QLabel("Active Template Pattern:"))
        tmpl_layout.addWidget(self.template_input)

        # Token Insertion Buttons
        token_label = QLabel("Click to insert metadata placeholder:")
        tmpl_layout.addWidget(token_label)

        token_btn_row = QHBoxLayout()
        tokens = [
            "{DeducteeName}",
            "{PAN}",
            "{FormType}",
            "{Quarter}",
            "{FinancialYear}",
            "{CertificateNo}",
            "{Act}",
        ]
        for t in tokens:
            btn = QPushButton(t)
            btn.setStyleSheet("padding: 3px 8px; font-size: 11px;")
            btn.clicked.connect(lambda checked, tok=t: self._insert_token(tok))
            token_btn_row.addWidget(btn)
        tmpl_layout.addLayout(token_btn_row)

        # Live Sample Preview
        preview_box = QHBoxLayout()
        preview_box.addWidget(QLabel("<b>Example Output:</b>"))
        self.sample_preview = QLabel()
        self.sample_preview.setStyleSheet("color: #2563EB; font-weight: bold; font-size: 13px;")
        preview_box.addWidget(self.sample_preview, 1)
        tmpl_layout.addLayout(preview_box)

        template_group.setLayout(tmpl_layout)
        layout.addWidget(template_group)

        # ----------------------------------------------------------------------
        # 2. Collision & Duplicate Policy
        # ----------------------------------------------------------------------
        collision_group = QGroupBox("Duplicate Filename Handling")
        coll_layout = QVBoxLayout()

        self.collision_btn_group = QButtonGroup(self)
        self.radio_auto_inc = QRadioButton("Auto-Increment: Append (1), (2), (3) (Recommended)")
        self.radio_disambiguate = QRadioButton("Smart Disambiguation: Append Quarter and PAN (e.g. NAME_Q2_ABCDE1234F)")
        self.radio_skip = QRadioButton("Skip File: Do not rename if target already exists")

        self.collision_btn_group.addButton(self.radio_auto_inc, 1)
        self.collision_btn_group.addButton(self.radio_disambiguate, 2)
        self.collision_btn_group.addButton(self.radio_skip, 3)

        if self.config.collision_policy == COLLISION_DISAMBIGUATE:
            self.radio_disambiguate.setChecked(True)
        elif self.config.collision_policy == COLLISION_SKIP:
            self.radio_skip.setChecked(True)
        else:
            self.radio_auto_inc.setChecked(True)

        coll_layout.addWidget(self.radio_auto_inc)
        coll_layout.addWidget(self.radio_disambiguate)
        coll_layout.addWidget(self.radio_skip)
        collision_group.setLayout(coll_layout)
        layout.addWidget(collision_group)

        # ----------------------------------------------------------------------
        # 3. Execution Mode & Output Path
        # ----------------------------------------------------------------------
        mode_group = QGroupBox("File Operation Mode")
        mode_layout = QVBoxLayout()

        self.mode_btn_group = QButtonGroup(self)
        self.radio_inplace = QRadioButton("Rename In-Place (Replace original files directly in their folder)")
        self.radio_copy = QRadioButton("Copy to Output Folder (Preserve originals untouched, create renamed copies)")
        self.radio_move = QRadioButton("Move to Output Folder (Relocate and rename into separate folder)")

        self.mode_btn_group.addButton(self.radio_inplace, 1)
        self.mode_btn_group.addButton(self.radio_copy, 2)
        self.mode_btn_group.addButton(self.radio_move, 3)

        if self.config.execution_mode == MODE_COPY_TO_FOLDER:
            self.radio_copy.setChecked(True)
        elif self.config.execution_mode == MODE_MOVE_TO_FOLDER:
            self.radio_move.setChecked(True)
        else:
            self.radio_inplace.setChecked(True)

        mode_layout.addWidget(self.radio_inplace)
        mode_layout.addWidget(self.radio_copy)
        mode_layout.addWidget(self.radio_move)

        # Output folder picker
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output Folder:"))
        self.output_dir_input = QLineEdit(self.config.output_folder)
        self.browse_out_btn = QPushButton("Browse...")
        self.browse_out_btn.clicked.connect(self._browse_output_dir)
        out_row.addWidget(self.output_dir_input, 1)
        out_row.addWidget(self.browse_out_btn)
        mode_layout.addLayout(out_row)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # ----------------------------------------------------------------------
        # 4. Other Options (OCR, Length Limit)
        # ----------------------------------------------------------------------
        other_group = QGroupBox("Advanced Settings")
        oth_layout = QHBoxLayout()

        self.ocr_check = QCheckBox("Enable OCR Fallback for scanned certificates")
        self.ocr_check.setChecked(self.config.enable_ocr_fallback)
        oth_layout.addWidget(self.ocr_check)

        oth_layout.addSpacing(20)
        oth_layout.addWidget(QLabel("Max Name Length:"))
        self.max_len_spin = QSpinBox()
        self.max_len_spin.setRange(40, 200)
        self.max_len_spin.setValue(self.config.max_filename_length)
        oth_layout.addWidget(self.max_len_spin)
        oth_layout.addStretch()

        other_group.setLayout(oth_layout)
        layout.addWidget(other_group)

        # ----------------------------------------------------------------------
        # Dialog Action Buttons
        # ----------------------------------------------------------------------
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("PrimaryBtn")
        save_btn.clicked.connect(self._save_and_close)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        # Connections
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        self.template_input.textChanged.connect(self._update_preview)

        self._select_initial_preset()
        self._update_preview()

    def _select_initial_preset(self):
        cur_tmpl = self.config.naming_template
        for i in range(self.preset_combo.count()):
            if self.preset_combo.itemData(i) == cur_tmpl:
                self.preset_combo.setCurrentIndex(i)
                return
        self.preset_combo.setCurrentIndex(self.preset_combo.count() - 1)

    def _on_preset_selected(self, index: int):
        val = self.preset_combo.itemData(index)
        if val != "CUSTOM":
            self.template_input.setText(val)

    def _insert_token(self, token: str):
        self.template_input.insert(token)

    def _update_preview(self):
        mock_cert = CertificateData(
            file_path=Path("cert.pdf"),
            original_filename="raw_f16a.pdf",
            act="Income-tax Act, 1961",
            form_type="Form 16A",
            form_code="16A",
            deductee_name="TATA CONSULTANCY SERVICES LIMITED",
            deductee_pan="AAACT1234K",
            deductor_tan="DELB56789G",
            financial_year="2024-25",
            assessment_year="2025-26",
            quarter="Q2",
            certificate_no="TR16A99281",
        )
        tmpl = self.template_input.text().strip() or "{DeducteeName}"
        renamer = CertificateRenamer(template=tmpl)
        preview_name = renamer.format_filename(mock_cert)
        self.sample_preview.setText(preview_name)

    def _browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder:
            self.output_dir_input.setText(folder)

    def _save_and_close(self):
        # Update config object
        self.config.naming_template = self.template_input.text().strip() or "{DeducteeName}"

        if self.radio_disambiguate.isChecked():
            self.config.collision_policy = COLLISION_DISAMBIGUATE
        elif self.radio_skip.isChecked():
            self.config.collision_policy = COLLISION_SKIP
        else:
            self.config.collision_policy = COLLISION_AUTO_INCREMENT

        if self.radio_copy.isChecked():
            self.config.execution_mode = MODE_COPY_TO_FOLDER
        elif self.radio_move.isChecked():
            self.config.execution_mode = MODE_MOVE_TO_FOLDER
        else:
            self.config.execution_mode = MODE_RENAME_IN_PLACE

        self.config.output_folder = self.output_dir_input.text().strip()
        self.config.enable_ocr_fallback = self.ocr_check.isChecked()
        self.config.max_filename_length = self.max_len_spin.value()

        # Save to disk
        self.config.save()
        self.accept()
