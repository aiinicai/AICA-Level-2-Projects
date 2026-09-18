"""Settings tab: bound directly to :class:`utils.config_manager.AppSettings`."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.ocr_engine import SUPPORTED_LANGUAGES, is_tesseract_available
from models.enums import CollisionPolicy, NamingMode, ThemeMode, WordEngine
from ui.app_context import AppContext
from ui.theme import apply_theme
from ui.widgets.ai_settings_widget import AISettingsWidget


class SettingsTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._build_ui()
        self._load_from_settings()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        root = QVBoxLayout(inner)

        general_group = QGroupBox("General")
        general_form = QFormLayout(general_group)

        folder_row = QHBoxLayout()
        self.edit_output_folder = QLineEdit()
        self.btn_browse_output = QPushButton("Browse...")
        self.btn_browse_output.setObjectName("SecondaryButton")
        folder_row.addWidget(self.edit_output_folder, 1)
        folder_row.addWidget(self.btn_browse_output)
        general_form.addRow("Default output folder:", folder_row)

        self.edit_default_signature = QLineEdit()
        btn_browse_sig = QPushButton("Browse...")
        btn_browse_sig.setObjectName("SecondaryButton")
        sig_row = QHBoxLayout()
        sig_row.addWidget(self.edit_default_signature, 1)
        sig_row.addWidget(btn_browse_sig)
        general_form.addRow("Default signature image:", sig_row)
        btn_browse_sig.clicked.connect(self._browse_signature)

        self.combo_naming = QComboBox()
        self.combo_naming.addItems([m.value for m in NamingMode])
        general_form.addRow("Default naming pattern:", self.combo_naming)
        self.edit_suffix = QLineEdit()
        general_form.addRow("Default suffix:", self.edit_suffix)
        self.edit_prefix = QLineEdit()
        general_form.addRow("Default prefix:", self.edit_prefix)

        self.combo_collision = QComboBox()
        self.combo_collision.addItems([c.value for c in CollisionPolicy])
        general_form.addRow("If output file exists:", self.combo_collision)

        self.chk_remember_folder = QCheckBox("Remember last used folder")
        general_form.addRow(self.chk_remember_folder)
        self.chk_confirm_overwrite = QCheckBox("Confirm before overwriting the original file")
        general_form.addRow(self.chk_confirm_overwrite)
        self.chk_open_output = QCheckBox("Open output folder after completion")
        general_form.addRow(self.chk_open_output)
        self.chk_activity_register = QCheckBox("Maintain local activity register (audit trail)")
        general_form.addRow(self.chk_activity_register)

        self.edit_operator = QLineEdit()
        general_form.addRow("Operator name (for audit trail):", self.edit_operator)
        root.addWidget(general_group)

        conversion_group = QGroupBox("Word Conversion")
        conversion_form = QFormLayout(conversion_group)
        self.combo_word_engine = QComboBox()
        self.combo_word_engine.addItems([e.value for e in WordEngine])
        conversion_form.addRow("Engine:", self.combo_word_engine)
        self.edit_libreoffice_path = QLineEdit()
        lo_row = QHBoxLayout()
        lo_row.addWidget(self.edit_libreoffice_path, 1)
        btn_browse_lo = QPushButton("Browse...")
        btn_browse_lo.setObjectName("SecondaryButton")
        lo_row.addWidget(btn_browse_lo)
        conversion_form.addRow("LibreOffice path (optional override):", lo_row)
        btn_browse_lo.clicked.connect(self._browse_libreoffice)
        root.addWidget(conversion_group)

        appearance_group = QGroupBox("Appearance")
        appearance_form = QFormLayout(appearance_group)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems([t.value for t in ThemeMode])
        appearance_form.addRow("Theme:", self.combo_theme)
        root.addWidget(appearance_group)

        temp_group = QGroupBox("Storage")
        temp_form = QFormLayout(temp_group)
        self.edit_temp_folder = QLineEdit()
        temp_row = QHBoxLayout()
        temp_row.addWidget(self.edit_temp_folder, 1)
        btn_browse_temp = QPushButton("Browse...")
        btn_browse_temp.setObjectName("SecondaryButton")
        temp_row.addWidget(btn_browse_temp)
        temp_form.addRow("Temporary file folder (blank = system default):", temp_row)
        btn_browse_temp.clicked.connect(self._browse_temp)
        root.addWidget(temp_group)

        ocr_group = QGroupBox("OCR")
        ocr_form = QFormLayout(ocr_group)
        tesseract_status = "detected" if is_tesseract_available() else "NOT detected -- install from github.com/UB-Mannheim/tesseract/wiki"
        ocr_form.addRow(QLabel(f"Tesseract OCR: {tesseract_status}"))
        self.edit_tesseract_path = QLineEdit()
        tess_row = QHBoxLayout()
        tess_row.addWidget(self.edit_tesseract_path, 1)
        btn_browse_tesseract = QPushButton("Browse...")
        btn_browse_tesseract.setObjectName("SecondaryButton")
        tess_row.addWidget(btn_browse_tesseract)
        ocr_form.addRow("tesseract.exe path (optional override):", tess_row)
        btn_browse_tesseract.clicked.connect(self._browse_tesseract)
        self.combo_ocr_language = QComboBox()
        self.combo_ocr_language.addItems(list(SUPPORTED_LANGUAGES.keys()))
        ocr_form.addRow("Default OCR language:", self.combo_ocr_language)
        self.spin_ocr_dpi = QSpinBox()
        self.spin_ocr_dpi.setRange(72, 600)
        self.spin_ocr_dpi.setSingleStep(50)
        ocr_form.addRow("OCR render DPI:", self.spin_ocr_dpi)
        self.chk_ocr_skip_text = QCheckBox("Skip pages that already have extractable text")
        ocr_form.addRow(self.chk_ocr_skip_text)
        root.addWidget(ocr_group)

        self.ai_settings = AISettingsWidget(self.ctx)
        root.addWidget(self.ai_settings)

        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setMinimumHeight(36)
        root.addWidget(self.btn_save)
        root.addStretch(1)

        self.btn_browse_output.clicked.connect(self._browse_output)
        self.btn_save.clicked.connect(self.save)

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Default Output Folder", self.edit_output_folder.text())
        if folder:
            self.edit_output_folder.setText(folder)

    def _browse_signature(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Default Signature", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.edit_default_signature.setText(path)

    def _browse_libreoffice(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select soffice.exe", "C:/Program Files", "Executable (*.exe)")
        if path:
            self.edit_libreoffice_path.setText(path)

    def _browse_temp(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Temporary File Folder", "")
        if folder:
            self.edit_temp_folder.setText(folder)

    def _browse_tesseract(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select tesseract.exe", "C:/Program Files", "Executable (*.exe)")
        if path:
            self.edit_tesseract_path.setText(path)

    def _load_from_settings(self) -> None:
        s = self.ctx.config.settings
        self.edit_output_folder.setText(s.default_output_folder)
        self.edit_default_signature.setText(s.default_signature_image)
        self.combo_naming.setCurrentText(s.naming_mode)
        self.edit_suffix.setText(s.naming_suffix)
        self.edit_prefix.setText(s.naming_prefix)
        self.combo_collision.setCurrentText(s.collision_policy)
        self.chk_remember_folder.setChecked(s.remember_last_folder)
        self.chk_confirm_overwrite.setChecked(s.confirm_before_overwrite)
        self.chk_open_output.setChecked(s.open_output_folder_after_completion)
        self.chk_activity_register.setChecked(s.enable_activity_register)
        self.edit_operator.setText(s.operator_name)
        self.combo_word_engine.setCurrentText(s.word_conversion_engine)
        self.edit_libreoffice_path.setText(s.libreoffice_path)
        self.combo_theme.setCurrentText(s.theme)
        self.edit_temp_folder.setText(s.temp_folder)
        self.edit_tesseract_path.setText(s.tesseract_path)
        language_name = next((name for name, code in SUPPORTED_LANGUAGES.items() if code == s.ocr_default_language), "English")
        self.combo_ocr_language.setCurrentText(language_name)
        self.spin_ocr_dpi.setValue(s.ocr_default_dpi)
        self.chk_ocr_skip_text.setChecked(s.ocr_skip_pages_with_text)

    def save(self) -> None:
        s = self.ctx.config.settings
        s.default_output_folder = self.edit_output_folder.text().strip() or s.default_output_folder
        s.default_signature_image = self.edit_default_signature.text().strip()
        s.naming_mode = self.combo_naming.currentText()
        s.naming_suffix = self.edit_suffix.text()
        s.naming_prefix = self.edit_prefix.text()
        s.collision_policy = self.combo_collision.currentText()
        s.remember_last_folder = self.chk_remember_folder.isChecked()
        s.confirm_before_overwrite = self.chk_confirm_overwrite.isChecked()
        s.open_output_folder_after_completion = self.chk_open_output.isChecked()
        s.enable_activity_register = self.chk_activity_register.isChecked()
        s.operator_name = self.edit_operator.text().strip()
        s.word_conversion_engine = self.combo_word_engine.currentText()
        s.libreoffice_path = self.edit_libreoffice_path.text().strip()
        s.theme = self.combo_theme.currentText()
        s.temp_folder = self.edit_temp_folder.text().strip()
        s.tesseract_path = self.edit_tesseract_path.text().strip()
        s.ocr_default_language = SUPPORTED_LANGUAGES.get(self.combo_ocr_language.currentText(), "eng")
        s.ocr_default_dpi = self.spin_ocr_dpi.value()
        s.ocr_skip_pages_with_text = self.chk_ocr_skip_text.isChecked()
        self.ai_settings.save_to_settings()
        self.ctx.config.save()
        self.ctx.operator = s.operator_name

        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            apply_theme(app, s.theme)

        QMessageBox.information(self, "Settings Saved", "Your settings have been saved.")
