"""Editor panel for one signature layer's image, size/position and page rule.

Reused by the Sign PDF tab (one instance per layer: Signature / Initial /
Stamp / Seal) and by the Templates tab (editing a saved template).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from models.enums import PageSelectionMode, PositionPreset, SignatureKind
from models.signature_template import SignatureTemplate


class SignatureLayerWidget(QGroupBox):
    """A self-contained editor for one :class:`SignatureTemplate`."""

    changed = Signal()
    remove_requested = Signal()

    def __init__(
        self,
        kind: SignatureKind = SignatureKind.SIGNATURE,
        removable: bool = True,
        database=None,
        parent: QWidget | None = None,
    ):
        super().__init__(kind.value, parent)
        self.database = database
        self._current_template_id: str | None = None
        self._build_ui(removable)
        self.set_kind(kind)
        self._wire_signals()
        if self.database is not None:
            self._refresh_template_list()

    def _build_ui(self, removable: bool) -> None:
        outer = QVBoxLayout(self)

        top_row = QHBoxLayout()
        self.combo_kind = QComboBox()
        self.combo_kind.addItems([k.value for k in SignatureKind])
        top_row.addWidget(QLabel("Layer type:"))
        top_row.addWidget(self.combo_kind)
        top_row.addStretch(1)
        if removable:
            self.btn_remove = QPushButton("Remove Layer")
            self.btn_remove.setObjectName("DangerButton")
            self.btn_remove.clicked.connect(self.remove_requested.emit)
            top_row.addWidget(self.btn_remove)
        outer.addLayout(top_row)

        if self.database is not None:
            template_row = QHBoxLayout()
            self.combo_template = QComboBox()
            self.combo_template.setPlaceholderText("Saved templates...")
            self.btn_apply_template = QPushButton("Apply")
            self.btn_apply_template.setObjectName("SecondaryButton")
            self.btn_save_template = QPushButton("Save As Template")
            self.btn_save_template.setObjectName("SecondaryButton")
            self.btn_delete_template = QPushButton("Delete")
            self.btn_delete_template.setObjectName("DangerButton")
            template_row.addWidget(QLabel("Template:"))
            template_row.addWidget(self.combo_template, 1)
            template_row.addWidget(self.btn_apply_template)
            template_row.addWidget(self.btn_save_template)
            template_row.addWidget(self.btn_delete_template)
            outer.addLayout(template_row)
            self.btn_apply_template.clicked.connect(self._apply_selected_template)
            self.btn_save_template.clicked.connect(self._save_as_template)
            self.btn_delete_template.clicked.connect(self._delete_selected_template)

        image_row = QHBoxLayout()
        self.lbl_thumb = QLabel("No image")
        self.lbl_thumb.setFixedSize(120, 50)
        self.lbl_thumb.setStyleSheet("border: 1px solid #ccd2db; background: white;")
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit_image_path = QLineEdit()
        self.edit_image_path.setPlaceholderText("Signature image (PNG/JPG/JPEG)...")
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.setObjectName("SecondaryButton")
        image_row.addWidget(self.lbl_thumb)
        image_row.addWidget(self.edit_image_path, 1)
        image_row.addWidget(self.btn_browse)
        outer.addLayout(image_row)

        image_tools_row = QHBoxLayout()
        self.btn_autocrop = QPushButton("Remove White Margins (Auto-Crop)")
        self.btn_autocrop.setObjectName("SecondaryButton")
        self.btn_preview_signature = QPushButton("Preview Signature")
        self.btn_preview_signature.setObjectName("SecondaryButton")
        image_tools_row.addWidget(self.btn_autocrop)
        image_tools_row.addWidget(self.btn_preview_signature)
        image_tools_row.addStretch(1)
        outer.addLayout(image_tools_row)

        form = QFormLayout()

        self.combo_position = QComboBox()
        self.combo_position.addItems([p.value for p in PositionPreset])
        self.combo_position.setCurrentText(PositionPreset.BOTTOM_RIGHT.value)  # most common default
        form.addRow("Position:", self.combo_position)

        custom_row = QHBoxLayout()
        self.spin_custom_x = QDoubleSpinBox()
        self.spin_custom_x.setRange(0, 100)
        self.spin_custom_x.setSuffix(" % X")
        self.spin_custom_y = QDoubleSpinBox()
        self.spin_custom_y.setRange(0, 100)
        self.spin_custom_y.setSuffix(" % Y")
        custom_row.addWidget(self.spin_custom_x)
        custom_row.addWidget(self.spin_custom_y)
        form.addRow("Custom position:", custom_row)

        size_row = QHBoxLayout()
        self.spin_width = QDoubleSpinBox()
        self.spin_width.setRange(1, 100)
        self.spin_width.setValue(20)
        self.spin_width.setSuffix(" % width")
        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(1, 100)
        self.spin_height.setValue(8)
        self.spin_height.setSuffix(" % height")
        self.chk_aspect = QCheckBox("Lock aspect ratio")
        self.chk_aspect.setChecked(True)
        size_row.addWidget(self.spin_width)
        size_row.addWidget(self.spin_height)
        size_row.addWidget(self.chk_aspect)
        form.addRow("Size:", size_row)

        self.spin_margin = QDoubleSpinBox()
        self.spin_margin.setRange(0, 100)
        self.spin_margin.setValue(10)
        self.spin_margin.setSuffix(" mm")
        form.addRow("Margin:", self.spin_margin)

        opacity_row = QHBoxLayout()
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(100)
        self.lbl_opacity = QLabel("100%")
        opacity_row.addWidget(self.slider_opacity)
        opacity_row.addWidget(self.lbl_opacity)
        form.addRow("Opacity:", opacity_row)

        self.spin_rotation = QDoubleSpinBox()
        self.spin_rotation.setRange(-180, 180)
        self.spin_rotation.setValue(0)
        self.spin_rotation.setSuffix(" °")
        form.addRow("Rotation:", self.spin_rotation)

        self.combo_page_mode = QComboBox()
        self.combo_page_mode.addItems([m.value for m in PageSelectionMode])
        self.combo_page_mode.setCurrentText(PageSelectionMode.LAST_PAGE.value)
        form.addRow("Apply to pages:", self.combo_page_mode)

        self.edit_page_param = QLineEdit()
        self.edit_page_param.setPlaceholderText("e.g. 1,3,5-8,last  or 2  or 2-10  or 2 (every Nth) ...")
        self.edit_page_param.setVisible(False)
        form.addRow("Page detail:", self.edit_page_param)

        outer.addLayout(form)

    def _wire_signals(self) -> None:
        self.btn_browse.clicked.connect(self._browse_image)
        self.btn_autocrop.clicked.connect(self._autocrop_image)
        self.btn_preview_signature.clicked.connect(self._preview_signature)
        self.combo_position.currentTextChanged.connect(self._on_position_changed)
        self.combo_page_mode.currentTextChanged.connect(self._on_page_mode_changed)
        self.slider_opacity.valueChanged.connect(lambda v: self.lbl_opacity.setText(f"{v}%"))
        self.edit_image_path.textChanged.connect(self._update_thumbnail)
        for widget in (
            self.combo_kind,
            self.combo_position,
            self.spin_custom_x,
            self.spin_custom_y,
            self.spin_width,
            self.spin_height,
            self.chk_aspect,
            self.spin_margin,
            self.slider_opacity,
            self.spin_rotation,
            self.combo_page_mode,
            self.edit_page_param,
        ):
            signal = getattr(widget, "currentTextChanged", None) or getattr(widget, "valueChanged", None) or getattr(
                widget, "stateChanged", None
            ) or getattr(widget, "textChanged", None)
            if signal:
                signal.connect(lambda *_: self.changed.emit())
        self._on_position_changed(self.combo_position.currentText())
        self._on_page_mode_changed(self.combo_page_mode.currentText())

    def _on_position_changed(self, text: str) -> None:
        self.spin_custom_x.setEnabled(text == PositionPreset.CUSTOM.value)
        self.spin_custom_y.setEnabled(text == PositionPreset.CUSTOM.value)

    def _on_page_mode_changed(self, text: str) -> None:
        needs_param = text in (
            PageSelectionMode.SINGLE_PAGE.value,
            PageSelectionMode.MULTIPLE_PAGES.value,
            PageSelectionMode.PAGE_RANGE.value,
            PageSelectionMode.EVERY_NTH_PAGE.value,
            PageSelectionMode.LAST_N_PAGES.value,
            PageSelectionMode.CUSTOM.value,
        )
        self.edit_page_param.setVisible(needs_param)
        hints = {
            PageSelectionMode.SINGLE_PAGE.value: "e.g. 3",
            PageSelectionMode.MULTIPLE_PAGES.value: "e.g. 1,3,5",
            PageSelectionMode.PAGE_RANGE.value: "e.g. 2-10",
            PageSelectionMode.EVERY_NTH_PAGE.value: "e.g. 2 (every 2nd page)",
            PageSelectionMode.LAST_N_PAGES.value: "e.g. 2 (last 2 pages)",
            PageSelectionMode.CUSTOM.value: "e.g. 1,3,5-8,last",
        }
        self.edit_page_param.setPlaceholderText(hints.get(text, ""))

    def _browse_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Signature Image", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.edit_image_path.setText(path)

    def _autocrop_image(self) -> None:
        """Trim unnecessary white/transparent margins and save a new, cropped
        copy alongside the original -- the source image file is never
        overwritten, matching the app-wide "never touch the original" rule."""
        from PySide6.QtWidgets import QMessageBox

        from core.signature_engine import SignatureImageProcessor
        from utils.validation import ValidationError

        path_text = self.edit_image_path.text().strip()
        if not path_text or not Path(path_text).exists():
            QMessageBox.information(self, "No Image", "Select a signature image first.")
            return
        try:
            img = SignatureImageProcessor.load(path_text)
            cropped = SignatureImageProcessor.autocrop(img)
        except ValidationError as exc:
            QMessageBox.critical(self, "Crop Failed", str(exc))
            return
        source = Path(path_text)
        output_path = source.with_name(f"{source.stem}_cropped.png")
        cropped.save(output_path)
        self.edit_image_path.setText(str(output_path))
        QMessageBox.information(
            self, "Margins Removed", f"Saved a cropped copy to:\n{output_path}\n\nThe original image was not modified."
        )

    def _preview_signature(self) -> None:
        """Show the fully prepared (cropped/resized/opacity/rotation-applied)
        signature exactly as it will be embedded, independent of any PDF page."""
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QDialog, QLabel as _QLabel, QMessageBox, QVBoxLayout as _QVBoxLayout

        from core.signature_engine import SignatureImageProcessor
        from utils.validation import ValidationError

        path_text = self.edit_image_path.text().strip()
        if not path_text or not Path(path_text).exists():
            QMessageBox.information(self, "No Image", "Select a signature image first.")
            return
        try:
            prepared = SignatureImageProcessor.prepare(
                path_text,
                autocrop=False,
                opacity_pct=self.slider_opacity.value(),
                rotation_degrees=self.spin_rotation.value(),
            )
        except ValidationError as exc:
            QMessageBox.critical(self, "Preview Failed", str(exc))
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Signature Preview")
        layout = _QVBoxLayout(dialog)
        pixmap = QPixmap()
        pixmap.loadFromData(prepared.png_bytes, "PNG")
        label = _QLabel()
        label.setStyleSheet("background: repeating-conic-gradient(#ddd 0% 25%, white 0% 50%) 50% / 16px 16px;")
        label.setPixmap(pixmap.scaled(400, 250, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(label)
        dialog.exec()

    def _update_thumbnail(self, path: str) -> None:
        if path and Path(path).exists():
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.lbl_thumb.setPixmap(
                    pixmap.scaled(114, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
                return
        self.lbl_thumb.setText("No image")
        self.lbl_thumb.setPixmap(QPixmap())

    def set_kind(self, kind: SignatureKind) -> None:
        self.combo_kind.setCurrentText(kind.value)
        self.setTitle(kind.value)
        self.combo_kind.currentTextChanged.connect(self.setTitle)

    # ------------------------------------------------------------ template IO
    def _current_page_expression(self) -> str:
        from core.page_selection import PageSelectionRule

        mode = PageSelectionMode(self.combo_page_mode.currentText())
        rule = PageSelectionRule(mode=mode)
        param = self.edit_page_param.text().strip()
        if mode == PageSelectionMode.SINGLE_PAGE and param.isdigit():
            rule.single_page = int(param)
        elif mode == PageSelectionMode.MULTIPLE_PAGES and param:
            rule.multiple_pages = param
        elif mode == PageSelectionMode.PAGE_RANGE and "-" in param:
            a, b = param.split("-", 1)
            if a.strip().isdigit() and b.strip().isdigit():
                rule.range_start, rule.range_end = int(a), int(b)
        elif mode == PageSelectionMode.EVERY_NTH_PAGE and param.isdigit():
            rule.nth = int(param)
        elif mode == PageSelectionMode.LAST_N_PAGES and param.isdigit():
            rule.last_n = int(param)
        elif mode == PageSelectionMode.CUSTOM:
            rule.custom_expression = param or "all"
        return rule.to_expression()

    def get_template(self, name: str = "") -> SignatureTemplate:
        return SignatureTemplate(
            name=name or self.combo_kind.currentText(),
            kind=SignatureKind(self.combo_kind.currentText()),
            image_path=self.edit_image_path.text().strip(),
            position_preset=PositionPreset(self.combo_position.currentText()),
            custom_x_pct=self.spin_custom_x.value(),
            custom_y_pct=self.spin_custom_y.value(),
            width_pct=self.spin_width.value(),
            height_pct=self.spin_height.value(),
            maintain_aspect_ratio=self.chk_aspect.isChecked(),
            margin_mm=self.spin_margin.value(),
            opacity=float(self.slider_opacity.value()),
            rotation_degrees=self.spin_rotation.value(),
            page_rule_expression=self._current_page_expression(),
        )

    def load_template(self, template: SignatureTemplate) -> None:
        from core.page_selection import PageSelectionRule

        self.combo_kind.setCurrentText(template.kind.value)
        self.edit_image_path.setText(template.image_path)
        self.combo_position.setCurrentText(template.position_preset.value)
        self.spin_custom_x.setValue(template.custom_x_pct)
        self.spin_custom_y.setValue(template.custom_y_pct)
        self.spin_width.setValue(template.width_pct)
        self.spin_height.setValue(template.height_pct)
        self.chk_aspect.setChecked(template.maintain_aspect_ratio)
        self.spin_margin.setValue(template.margin_mm)
        self.slider_opacity.setValue(int(template.opacity))
        self.spin_rotation.setValue(template.rotation_degrees)

        rule = PageSelectionRule.from_expression(template.page_rule_expression)
        self.combo_page_mode.setCurrentText(rule.mode.value)
        param_map = {
            PageSelectionMode.SINGLE_PAGE: str(rule.single_page),
            PageSelectionMode.MULTIPLE_PAGES: rule.multiple_pages,
            PageSelectionMode.PAGE_RANGE: f"{rule.range_start}-{rule.range_end}",
            PageSelectionMode.EVERY_NTH_PAGE: str(rule.nth),
            PageSelectionMode.LAST_N_PAGES: str(rule.last_n),
            PageSelectionMode.CUSTOM: rule.custom_expression,
        }
        self.edit_page_param.setText(param_map.get(rule.mode, ""))
        self._current_template_id = template.template_id

    # --------------------------------------------------------- template store
    def _refresh_template_list(self) -> None:
        if self.database is None:
            return
        self.combo_template.blockSignals(True)
        self.combo_template.clear()
        self._templates_by_label: dict[str, SignatureTemplate] = {}
        for tmpl in self.database.list_templates():
            label = f"{tmpl.name}  ({tmpl.kind.value})"
            self._templates_by_label[label] = tmpl
            self.combo_template.addItem(label)
        self.combo_template.blockSignals(False)

    def _apply_selected_template(self) -> None:
        label = self.combo_template.currentText()
        tmpl = getattr(self, "_templates_by_label", {}).get(label)
        if tmpl:
            self.load_template(tmpl)
            self.changed.emit()

    def _save_as_template(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        default_name = self.combo_kind.currentText()
        name, ok = QInputDialog.getText(self, "Save Template", "Template name:", text=default_name)
        if not ok or not name.strip():
            return
        template = self.get_template(name=name.strip())
        if self._current_template_id:
            template.template_id = self._current_template_id
        self.database.save_template(template)
        self._current_template_id = template.template_id
        self._refresh_template_list()
        self.combo_template.setCurrentText(f"{template.name}  ({template.kind.value})")

    def _delete_selected_template(self) -> None:
        label = self.combo_template.currentText()
        tmpl = getattr(self, "_templates_by_label", {}).get(label)
        if tmpl:
            self.database.delete_template(tmpl.template_id)
            self._refresh_template_list()
