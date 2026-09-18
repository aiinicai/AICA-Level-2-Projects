"""Templates tab: browse, create, edit and delete saved signature/stamp templates."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.signature_template import SignatureTemplate
from ui.app_context import AppContext
from ui.widgets.signature_layer_widget import SignatureLayerWidget


class TemplateEditorDialog(QDialog):
    def __init__(self, database, template: SignatureTemplate | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Template" if template else "New Template")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        self.editor = SignatureLayerWidget(removable=False, database=None)
        if template:
            self.editor.load_template(template)
        layout.addWidget(self.editor)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._existing_id = template.template_id if template else None

    def get_template(self, name: str) -> SignatureTemplate:
        template = self.editor.get_template(name=name)
        if self._existing_id:
            template.template_id = self._existing_id
        return template


class TemplatesTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.btn_new = QPushButton("Save New Template")
        self.btn_edit = QPushButton("Edit Template")
        self.btn_edit.setObjectName("SecondaryButton")
        self.btn_delete = QPushButton("Delete Template")
        self.btn_delete.setObjectName("DangerButton")
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setObjectName("SecondaryButton")
        for b in (self.btn_new, self.btn_edit, self.btn_delete, self.btn_refresh):
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Position", "Size", "Page Rule", "Image"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 1)

        self.btn_new.clicked.connect(self.create_template)
        self.btn_edit.clicked.connect(self.edit_selected)
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_refresh.clicked.connect(self.refresh)
        self.table.doubleClicked.connect(lambda *_: self.edit_selected())

    def refresh(self) -> None:
        templates = self.ctx.database.list_templates()
        self._templates = templates
        self.table.setRowCount(len(templates))
        for row, t in enumerate(templates):
            self.table.setItem(row, 0, QTableWidgetItem(t.name))
            self.table.setItem(row, 1, QTableWidgetItem(t.kind.value))
            self.table.setItem(row, 2, QTableWidgetItem(t.position_preset.value))
            self.table.setItem(row, 3, QTableWidgetItem(f"{t.width_pct:.0f}% x {t.height_pct:.0f}%"))
            self.table.setItem(row, 4, QTableWidgetItem(t.page_rule_expression))
            self.table.setItem(row, 5, QTableWidgetItem(t.image_path))

    def _selected_template(self) -> SignatureTemplate | None:
        rows = {i.row() for i in self.table.selectedIndexes()}
        if len(rows) != 1:
            return None
        return self._templates[next(iter(rows))]

    def create_template(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        dlg = TemplateEditorDialog(self.ctx.database, None, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name, ok = QInputDialog.getText(self, "Template Name", "Enter a name for this template:")
        if not ok or not name.strip():
            return
        self.ctx.database.save_template(dlg.get_template(name.strip()))
        self.refresh()

    def edit_selected(self) -> None:
        template = self._selected_template()
        if not template:
            QMessageBox.information(self, "Select a Template", "Select exactly one template to edit.")
            return
        dlg = TemplateEditorDialog(self.ctx.database, template, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self.ctx.database.save_template(dlg.get_template(template.name))
        self.refresh()

    def delete_selected(self) -> None:
        template = self._selected_template()
        if not template:
            QMessageBox.information(self, "Select a Template", "Select exactly one template to delete.")
            return
        if QMessageBox.question(self, "Delete Template", f"Delete template '{template.name}'?") != QMessageBox.StandardButton.Yes:
            return
        self.ctx.database.delete_template(template.template_id)
        self.refresh()
