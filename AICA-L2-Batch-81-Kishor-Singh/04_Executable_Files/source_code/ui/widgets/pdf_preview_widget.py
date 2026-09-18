"""Interactive PDF preview: render a page and let the user drag/resize a signature overlay.

This is the widget behind "drag the signature onto the page visually" in the
Sign PDF tab, and the read-only preview used by Merge/Split/Organize.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.pdf_engine import open_pdf, render_page_to_png_bytes

_HANDLE_SIZE = 12


class _ResizeHandle(QGraphicsRectItem):
    """Small square at the bottom-right corner of the overlay used to resize it.

    Deliberately implemented with plain mouse events rather than
    ``ItemIsMovable`` + ``itemChange`` -- the handle's own position is always
    fully derived from the overlay's current size (see
    ``SignatureOverlayItem._sync_handle_position``), so letting Qt's move
    machinery drive it independently would fight with that and risk
    re-entrant ``itemChange`` calls.
    """

    def __init__(self, parent_item: "SignatureOverlayItem"):
        super().__init__(-_HANDLE_SIZE / 2, -_HANDLE_SIZE / 2, _HANDLE_SIZE, _HANDLE_SIZE, parent_item)
        self.overlay = parent_item
        self.setBrush(QBrush(QColor("#2f6fed")))
        self.setPen(QPen(QColor("white"), 1))
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setZValue(10)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self._dragging = False

    def mousePressEvent(self, event) -> None:
        self._dragging = True
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if not self._dragging:
            return
        # event.pos() is in this handle's local coordinates; translate to the
        # overlay's local coordinates (handle is centred on the overlay's
        # bottom-right corner) to get the new target size directly.
        scene_pt = event.scenePos()
        overlay_local = self.overlay.mapFromScene(scene_pt)
        self.overlay.resize_to(overlay_local.x(), overlay_local.y())
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._dragging = False
        event.accept()


class SignatureOverlayItem(QGraphicsPixmapItem):
    """A movable, resizable signature image placed on top of the rendered page."""

    def __init__(self, pixmap: QPixmap):
        super().__init__(pixmap)
        self._original_pixmap = pixmap
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.handle = _ResizeHandle(self)
        self._sync_handle_position()

    def _sync_handle_position(self) -> None:
        rect = self.boundingRect()
        self.handle.setPos(rect.width(), rect.height())

    def resize_to(self, width: float, height: float) -> None:
        width = max(20.0, width)
        height = max(10.0, height)
        scaled = self._original_pixmap.scaled(
            int(width), int(height), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)
        self._sync_handle_position()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene() is not None:
            new_pos = value
            scene_rect = self.scene().sceneRect()
            rect = self.boundingRect()
            new_pos.setX(min(max(0.0, new_pos.x()), max(0.0, scene_rect.width() - rect.width())))
            new_pos.setY(min(max(0.0, new_pos.y()), max(0.0, scene_rect.height() - rect.height())))
            return new_pos
        return super().itemChange(change, value)


class PdfPreviewWidget(QWidget):
    """Renders one page of a PDF at a time with pan/zoom and an optional
    draggable/resizable signature overlay for interactive placement."""

    placement_changed = Signal(float, float, float, float)  # x_pct, y_pct, w_pct, h_pct
    page_changed = Signal(int, int)  # current (1-based), total

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._doc = None
        self._page_index = 0
        self._zoom = 1.5
        self._page_pixmap_item: QGraphicsPixmapItem | None = None
        self._overlay: SignatureOverlayItem | None = None
        self._page_size_pt = (595.0, 842.0)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setObjectName("PreviewCanvas")
        self.view.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)

        toolbar = QHBoxLayout()
        self.btn_prev = QToolButton(text="◀ Prev")
        self.btn_next = QToolButton(text="Next ▶")
        self.btn_zoom_in = QToolButton(text="Zoom +")
        self.btn_zoom_out = QToolButton(text="Zoom −")
        self.btn_fit_page = QToolButton(text="Fit Page")
        self.btn_fit_width = QToolButton(text="Fit Width")
        self.lbl_page = QLabel("No document loaded")
        for b in (self.btn_prev, self.btn_next, self.btn_zoom_in, self.btn_zoom_out, self.btn_fit_page, self.btn_fit_width):
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        toolbar.addWidget(self.lbl_page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(toolbar)
        layout.addWidget(self.view)

        self.btn_prev.clicked.connect(self.previous_page)
        self.btn_next.clicked.connect(self.next_page)
        self.btn_zoom_in.clicked.connect(lambda: self._set_zoom(self._zoom * 1.25))
        self.btn_zoom_out.clicked.connect(lambda: self._set_zoom(self._zoom / 1.25))
        self.btn_fit_page.clicked.connect(self.fit_page)
        self.btn_fit_width.clicked.connect(self.fit_width)

    # ------------------------------------------------------------------ loading
    def load_pdf(self, path: str | Path, password: str | None = None) -> None:
        self.close_document()
        self._doc = open_pdf(path, password)
        self._page_index = 0
        self._render_current_page()

    def close_document(self) -> None:
        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:
                pass
            self._doc = None
        self.scene.clear()
        self._page_pixmap_item = None
        self._overlay = None

    @property
    def page_count(self) -> int:
        return self._doc.page_count if self._doc else 0

    def go_to_page(self, index_0based: int) -> None:
        if not self._doc:
            return
        self._page_index = max(0, min(index_0based, self._doc.page_count - 1))
        self._render_current_page()

    def next_page(self) -> None:
        self.go_to_page(self._page_index + 1)

    def previous_page(self) -> None:
        self.go_to_page(self._page_index - 1)

    def _render_current_page(self) -> None:
        if not self._doc:
            return
        png_bytes = render_page_to_png_bytes(self._doc, self._page_index, zoom=self._zoom)
        pixmap = QPixmap()
        pixmap.loadFromData(png_bytes, "PNG")

        page = self._doc[self._page_index]
        self._page_size_pt = (page.rect.width, page.rect.height)

        # Preserve overlay's percentage placement across page/zoom changes.
        overlay_pct = self._get_overlay_percentages() if self._overlay else None

        self.scene.clear()
        self._overlay = None
        self._page_pixmap_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))

        if overlay_pct:
            pixmap, x, y, w, h = overlay_pct
            self._place_overlay_pixmap(pixmap, x, y, w, h)

        self.lbl_page.setText(f"Page {self._page_index + 1} of {self._doc.page_count}")
        self.page_changed.emit(self._page_index + 1, self._doc.page_count)

    # --------------------------------------------------------------------- zoom
    def _set_zoom(self, zoom: float) -> None:
        self._zoom = max(0.3, min(zoom, 6.0))
        self._render_current_page()

    def fit_page(self) -> None:
        if self._page_pixmap_item:
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def fit_width(self) -> None:
        if self._page_pixmap_item:
            rect = self.scene.sceneRect()
            view_width = self.view.viewport().width()
            if rect.width() > 0:
                factor = view_width / rect.width()
                self.view.resetTransform()
                self.view.scale(factor, factor)

    # ---------------------------------------------------------------- overlay
    def set_signature_overlay(self, png_bytes: bytes, x_pct: float, y_pct: float, w_pct: float, h_pct: float) -> None:
        """Place (or move) the draggable signature preview at the given page-relative percentages."""
        pixmap = QPixmap()
        pixmap.loadFromData(png_bytes, "PNG")
        self._place_overlay_pixmap(pixmap, x_pct, y_pct, w_pct, h_pct)

    def _place_overlay_pixmap(self, pixmap: QPixmap, x_pct: float, y_pct: float, w_pct: float, h_pct: float) -> None:
        if not self._page_pixmap_item:
            return
        page_w = self.scene.sceneRect().width()
        page_h = self.scene.sceneRect().height()
        target_w = max(20.0, page_w * (w_pct / 100.0))
        target_h = max(10.0, page_h * (h_pct / 100.0))
        scaled = pixmap.scaled(
            int(target_w), int(target_h), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
        )

        if self._overlay is not None:
            self.scene.removeItem(self._overlay)
        self._overlay = SignatureOverlayItem(scaled)
        self._overlay_source_pixmap = pixmap
        self.scene.addItem(self._overlay)
        self._overlay.setPos(page_w * (x_pct / 100.0), page_h * (y_pct / 100.0))
        self._overlay.setZValue(5)

    def _get_overlay_percentages(self) -> tuple[QPixmap, float, float, float, float] | None:
        if not self._overlay or not self._page_pixmap_item:
            return None
        page_w = self.scene.sceneRect().width()
        page_h = self.scene.sceneRect().height()
        if page_w <= 0 or page_h <= 0:
            return None
        pos = self._overlay.pos()
        rect = self._overlay.boundingRect()
        return (
            self._overlay_source_pixmap,
            (pos.x() / page_w) * 100.0,
            (pos.y() / page_h) * 100.0,
            (rect.width() / page_w) * 100.0,
            (rect.height() / page_h) * 100.0,
        )

    def get_overlay_placement_pct(self) -> tuple[float, float, float, float] | None:
        """Returns (x_pct, y_pct, width_pct, height_pct) of the current overlay, or None."""
        result = self._get_overlay_percentages()
        return result[1:] if result else None

    def remove_overlay(self) -> None:
        if self._overlay is not None:
            self.scene.removeItem(self._overlay)
            self._overlay = None

    def get_page_size_pt(self) -> tuple[float, float]:
        return self._page_size_pt
