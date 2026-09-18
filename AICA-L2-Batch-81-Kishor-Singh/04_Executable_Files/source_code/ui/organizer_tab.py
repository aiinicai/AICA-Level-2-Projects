"""Visual PDF page organizer: thumbnail grid with reorder/delete/rotate/duplicate/insert."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.page_organizer import PageOrganizer
from ui.app_context import AppContext
from ui.widgets.dialogs import show_error
from utils.validation import ValidationError

_THUMB_SIZE = QSize(140, 180)


class OrganizerTab(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.organizer: PageOrganizer | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.btn_open = QPushButton("Open PDF")
        self.btn_insert_blank = QPushButton("Insert Blank Page")
        self.btn_insert_blank.setObjectName("SecondaryButton")
        self.btn_insert_pdf = QPushButton("Insert Other PDF")
        self.btn_insert_pdf.setObjectName("SecondaryButton")
        self.btn_save_as = QPushButton("Save As New PDF")
        for b in (self.btn_open, self.btn_insert_blank, self.btn_insert_pdf, self.btn_save_as):
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self.lbl_hint = QLabel(
            "Open a PDF, then drag thumbnails to reorder. Right-click a page for delete / rotate / "
            "duplicate / extract. The original file is never modified until you choose Save As."
        )
        self.lbl_hint.setWordWrap(True)
        root.addWidget(self.lbl_hint)

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListView.ViewMode.IconMode)
        self.list_widget.setIconSize(_THUMB_SIZE)
        self.list_widget.setResizeMode(QListView.ResizeMode.Adjust)
        self.list_widget.setMovement(QListView.Movement.Snap)
        self.list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list_widget.setSpacing(10)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)
        root.addWidget(self.list_widget, 1)

        self.btn_open.clicked.connect(self.open_pdf)
        self.btn_insert_blank.clicked.connect(self.insert_blank_page)
        self.btn_insert_pdf.clicked.connect(self.insert_other_pdf)
        self.btn_save_as.clicked.connect(self.save_as)

    # -------------------------------------------------------------- loading
    def open_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", self.ctx.config.settings.last_used_folder, "PDF Files (*.pdf)")
        if not path:
            return
        if self.organizer:
            self.organizer.close()
        try:
            self.organizer = PageOrganizer(path)
        except ValidationError as exc:
            show_error(self, "Cannot Open File", str(exc))
            return
        self._refresh_thumbnails()

    def _refresh_thumbnails(self) -> None:
        self.list_widget.clear()
        if not self.organizer:
            return
        for thumb in self.organizer.get_thumbnails():
            pixmap = QPixmap()
            pixmap.loadFromData(thumb.png_bytes, "PNG")
            item = QListWidgetItem(QIcon(pixmap), f"Page {thumb.position + 1}")
            item.setData(Qt.ItemDataRole.UserRole, thumb.position)
            self.list_widget.addItem(item)

    # -------------------------------------------------------------- reorder
    def _on_rows_moved(self, *_args) -> None:
        if not self.organizer:
            return
        new_order = [self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list_widget.count())]
        try:
            self.organizer.reorder(new_order)
        except ValidationError as exc:
            show_error(self, "Reorder Failed", str(exc))
            return
        self._refresh_thumbnails()

    # ------------------------------------------------------------- actions
    def _selected_positions(self) -> list[int]:
        return sorted(self.list_widget.row(item) for item in self.list_widget.selectedItems())

    def _show_context_menu(self, point) -> None:
        if not self.organizer or not self.list_widget.selectedItems():
            return
        menu = QMenu(self)
        act_delete = menu.addAction("Delete Selected Page(s)")
        act_rotate_left = menu.addAction("Rotate Left 90°")
        act_rotate_right = menu.addAction("Rotate Right 90°")
        act_duplicate = menu.addAction("Duplicate Page")
        act_extract = menu.addAction("Extract Selected Page(s) to New PDF")
        action = menu.exec(self.list_widget.viewport().mapToGlobal(point))
        positions = self._selected_positions()
        if action == act_delete:
            self._delete_pages(positions)
        elif action == act_rotate_left:
            self._rotate_pages(positions, -90)
        elif action == act_rotate_right:
            self._rotate_pages(positions, 90)
        elif action == act_duplicate and len(positions) == 1:
            self.organizer.duplicate_page(positions[0])
            self._refresh_thumbnails()
        elif action == act_extract:
            self._extract_pages(positions)

    def _delete_pages(self, positions: list[int]) -> None:
        try:
            self.organizer.delete_pages(positions)
        except ValidationError as exc:
            show_error(self, "Cannot Delete", str(exc))
            return
        self._refresh_thumbnails()

    def _rotate_pages(self, positions: list[int], degrees: int) -> None:
        for pos in positions:
            self.organizer.rotate_page(pos, degrees)
        self._refresh_thumbnails()

    def _extract_pages(self, positions: list[int]) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Extract Pages To", str(Path(self.ctx.config.settings.default_output_folder) / "Extracted.pdf"), "PDF Files (*.pdf)")
        if not path:
            return
        try:
            self.organizer.extract_pages(positions, path)
        except ValidationError as exc:
            show_error(self, "Extract Failed", str(exc))
            return
        QMessageBox.information(self, "Extracted", f"Saved {len(positions)} page(s) to:\n{path}")

    def insert_blank_page(self) -> None:
        if not self.organizer:
            return
        positions = self._selected_positions()
        insert_at = positions[0] if positions else self.list_widget.count()
        self.organizer.insert_blank_page(insert_at)
        self._refresh_thumbnails()

    def insert_other_pdf(self) -> None:
        if not self.organizer:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Select PDF To Insert", "", "PDF Files (*.pdf)")
        if not path:
            return
        positions = self._selected_positions()
        insert_at = positions[0] if positions else self.list_widget.count()
        try:
            self.organizer.insert_pdf(insert_at, path)
        except ValidationError as exc:
            show_error(self, "Insert Failed", str(exc))
            return
        self._refresh_thumbnails()

    def save_as(self) -> None:
        if not self.organizer:
            QMessageBox.information(self, "No Document", "Open a PDF first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save As New PDF", self.ctx.config.settings.default_output_folder, "PDF Files (*.pdf)")
        if not path:
            return
        try:
            self.organizer.save_as(path)
        except ValidationError as exc:
            show_error(self, "Save Failed", str(exc))
            return
        QMessageBox.information(self, "Saved", f"Document saved to:\n{path}\n\nThe original file was not modified.")
