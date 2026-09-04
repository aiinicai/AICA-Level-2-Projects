"""
Excel-Style Searchable Multi-Select Checkbox Dropdown Widget.
"""

from PyQt6.QtWidgets import (
    QPushButton, QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QCheckBox, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint


class ExcelFilterDialog(QDialog):
    def __init__(self, items: list[str], selected: list[str], parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("excelFilterPopup")
        self.setFixedWidth(280)
        self.setFixedHeight(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Search box
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search values...")
        self.search_edit.textChanged.connect(self._filter_list)
        layout.addWidget(self.search_edit)

        # Select all checkbox
        self.select_all_cb = QCheckBox("(Select All)")
        self.select_all_cb.setTristate(False)
        self.select_all_cb.stateChanged.connect(self._on_select_all_changed)
        layout.addWidget(self.select_all_cb)

        # List widget
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        self._all_items = sorted([str(it) for it in items if it is not None and str(it).strip() != ""])
        selected_set = set(selected)

        self.list_items: list[QListWidgetItem] = []
        for val in self._all_items:
            item = QListWidgetItem(val, self.list_widget)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            check_state = Qt.CheckState.Checked if (not selected or val in selected_set) else Qt.CheckState.Unchecked
            item.setCheckState(check_state)
            self.list_items.append(item)

        self.list_widget.itemChanged.connect(self._on_item_changed)

        # Buttons row
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)
        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("primaryButton")
        ok_btn.setFixedHeight(28)
        ok_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setFixedHeight(28)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self._update_select_all_state()

    def _filter_list(self, text: str):
        query = text.strip().lower()
        for item in self.list_items:
            item.setHidden(bool(query and query not in item.text().lower()))

    def _on_select_all_changed(self, state):
        checked = (state == Qt.CheckState.Checked.value or state == Qt.CheckState.Checked)
        self.list_widget.blockSignals(True)
        for item in self.list_items:
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.list_widget.blockSignals(False)

    def _on_item_changed(self, item):
        self._update_select_all_state()

    def _update_select_all_state(self):
        visible_items = [item for item in self.list_items if not item.isHidden()]
        if not visible_items:
            return
        checked_count = sum(1 for item in visible_items if item.checkState() == Qt.CheckState.Checked)
        self.select_all_cb.blockSignals(True)
        if checked_count == len(visible_items):
            self.select_all_cb.setCheckState(Qt.CheckState.Checked)
        elif checked_count == 0:
            self.select_all_cb.setCheckState(Qt.CheckState.Unchecked)
        else:
            self.select_all_cb.setCheckState(Qt.CheckState.PartiallyChecked)
        self.select_all_cb.blockSignals(False)

    def get_selected(self) -> list[str]:
        return [item.text() for item in self.list_items if item.checkState() == Qt.CheckState.Checked]


class ExcelFilterDropdown(QPushButton):
    selection_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("secondaryButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(160)

        self._all_items: list[str] = []
        self._selected_items: list[str] = []
        self.clicked.connect(self._show_popup)
        self.update_display()

    def set_items(self, items: list[str]):
        self._all_items = sorted(list({str(it) for it in items if it is not None and str(it).strip() != ""}))
        self._selected_items = []
        self.update_display()

    def set_selected(self, selected: list[str]):
        self._selected_items = [str(s) for s in selected if str(s) in self._all_items]
        self.update_display()

    def get_selected(self) -> list[str]:
        return self._selected_items

    def get_selected_text(self) -> str:
        if not self._selected_items or len(self._selected_items) == len(self._all_items):
            return ""
        return ", ".join(self._selected_items)

    def update_display(self):
        if not self._all_items:
            self.setText("Select Values... ▾")
            return
        if not self._selected_items or len(self._selected_items) == len(self._all_items):
            self.setText(f"(All {len(self._all_items)} values) ▾")
        elif len(self._selected_items) == 1:
            self.setText(f"{self._selected_items[0]} ▾")
        else:
            self.setText(f"{len(self._selected_items)} values selected ▾")

    def _show_popup(self):
        if not self._all_items:
            return

        dialog = ExcelFilterDialog(self._all_items, self._selected_items, self)
        pos = self.mapToGlobal(QPoint(0, self.height()))
        dialog.move(pos)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._selected_items = dialog.get_selected()
            self.update_display()
            self.selection_changed.emit()
