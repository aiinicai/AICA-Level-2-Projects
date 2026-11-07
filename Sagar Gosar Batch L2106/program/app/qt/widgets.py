"""Reusable custom widgets: switches, drop cards, charts, zoomable scan viewer, toast, workers."""
import threading

from PySide6.QtCore import (QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QThread, QTimer, QVariantAnimation, Signal, Property)
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QFrame, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from . import theme
from .theme import SEV, icon, pal


def pil_to_pixmap(img):
    img = img.convert("RGBA")
    w, h = img.size
    qi = QImage(img.tobytes("raw", "RGBA"), w, h, 4 * w, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(qi)


def label(text, role=None, wrap=False):
    l = QLabel(text)
    if role:
        l.setProperty("role", role)
    l.setWordWrap(wrap)
    return l


def repolish(w):
    w.style().unpolish(w); w.style().polish(w)


# --------------------------------------------------------------------------------------------- switch
class Toggle(QCheckBox):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self._pos = 1.0 if self.isChecked() else 0.0
        self._anim = QVariantAnimation(self, duration=140, valueChanged=self._step)
        self.toggled.connect(self._go)

    def _step(self, v):
        self._pos = v; self.update()

    def _go(self, on):
        self._anim.stop(); self._anim.setStartValue(self._pos); self._anim.setEndValue(1.0 if on else 0.0); self._anim.start()

    def setChecked(self, on):
        super().setChecked(on); self._pos = 1.0 if on else 0.0; self.update()

    def sizeHint(self):
        return QSize(46 + (8 + self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0), 26)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        c = pal(); w, h = 42, 24
        y = (self.height() - h) / 2
        track = QRectF(1, y, w, h)
        off, on = QColor(c["border"]), QColor(c["primary"])
        col = QColor(int(off.red() + (on.red() - off.red()) * self._pos), int(off.green() + (on.green() - off.green()) * self._pos),
                     int(off.blue() + (on.blue() - off.blue()) * self._pos))
        p.setPen(Qt.NoPen); p.setBrush(col); p.drawRoundedRect(track, h / 2, h / 2)
        x = 1 + 3 + (w - h) * self._pos
        p.setBrush(QColor(c["gold"]) if self._pos > 0.5 else QColor("#FFFFFF"))
        p.drawEllipse(QRectF(x, y + 3, h - 6, h - 6))
        if self.text():
            p.setPen(QColor(c["text"] if self.isEnabled() else c["muted"]))
            p.drawText(QRectF(w + 12, 0, self.width() - w - 12, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())


# --------------------------------------------------------------------------------------------- drop card
class DropCard(QFrame):
    fileChosen = Signal(str)

    def __init__(self, title, hint, icon_name, exts, parent=None):
        super().__init__(parent)
        self.setObjectName("drop"); self.setAcceptDrops(True); self.setCursor(Qt.PointingHandCursor)
        self.exts, self.title, self.hint, self.icon_name, self.path = tuple(e.lower() for e in exts), title, hint, icon_name, ""
        lay = QHBoxLayout(self); lay.setContentsMargins(22, 18, 22, 18); lay.setSpacing(16)
        self.badge = QLabel(); self.badge.setFixedSize(58, 58); self.badge.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.badge)
        col = QVBoxLayout(); col.setSpacing(3)
        self.t = label(title, "h2"); self.sub = label(hint, "muted", True); self.meta = label("", "small")
        for w in (self.t, self.sub, self.meta):
            col.addWidget(w)
        lay.addLayout(col, 1)
        self.btn = QPushButton("Browse"); self.btn.setIcon(icon("folder", pal()["text"], 18)); self.btn.clicked.connect(self.browse)
        lay.addWidget(self.btn)
        self.refresh_theme()

    def refresh_theme(self):
        c = pal()
        self.badge.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {c['primary']},stop:1 {c['primary2']});border-radius:18px;")
        self.badge.setPixmap(icon(self.icon_name, "#FFFFFF", 28).pixmap(28, 28))
        self.btn.setIcon(icon("folder", c["text"], 18))

    def set_path(self, p):
        import os
        self.path = p
        self.setProperty("filled", bool(p)); repolish(self)
        if p:
            self.t.setText(os.path.basename(p)); self.sub.setText(os.path.dirname(p) or p)
            try:
                self.meta.setText(f"{os.path.getsize(p) / 1024:,.0f} KB")
            except OSError:
                self.meta.setText("")
        else:
            self.t.setText(self.title); self.sub.setText(self.hint); self.meta.setText("")

    def browse(self):
        flt = " ".join("*" + e for e in self.exts)
        p, _ = QFileDialog.getOpenFileName(self, self.title, "", f"Supported ({flt});;All files (*.*)")
        if p:
            self.set_path(p); self.fileChosen.emit(p)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.btn.geometry().contains(e.position().toPoint()):
            self.browse()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith(self.exts) for u in e.mimeData().urls()):
            e.acceptProposedAction(); self.setProperty("hover", True); repolish(self)

    def dragLeaveEvent(self, e):
        self.setProperty("hover", False); repolish(self)

    def dropEvent(self, e):
        self.setProperty("hover", False); repolish(self)
        for u in e.mimeData().urls():
            f = u.toLocalFile()
            if f.lower().endswith(self.exts):
                self.set_path(f); self.fileChosen.emit(f); e.acceptProposedAction(); return


# --------------------------------------------------------------------------------------------- KPI card
class StatCard(QFrame):
    def __init__(self, title, color, parent=None):
        super().__init__(parent)
        self.setObjectName("card"); self.color = color; self._v = 0
        lay = QVBoxLayout(self); lay.setContentsMargins(20, 16, 18, 14); lay.setSpacing(2)
        self.t = label(title, "small"); self.v = label("0", "kpi"); self.s = label("", "small")
        for w in (self.t, self.v, self.s):
            lay.addWidget(w)
        self.v.setStyleSheet(f"color:{color};")
        self._anim = QVariantAnimation(self, duration=650, valueChanged=lambda x: self.v.setText(f"{int(x):,}"))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def set_value(self, n, sub=""):
        self._anim.stop(); self._anim.setStartValue(0); self._anim.setEndValue(int(n)); self._anim.start(); self.s.setText(sub)

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setPen(Qt.NoPen); p.setBrush(QColor(self.color))
        p.drawRoundedRect(QRectF(0, 18, 4, self.height() - 36), 2, 2)


# --------------------------------------------------------------------------------------------- charts
class DonutChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {}; self._t = 1.0; self.setMinimumSize(210, 210)
        self._anim = QVariantAnimation(self, duration=900, valueChanged=self._step); self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def _step(self, v):
        self._t = v; self.update()

    def set_data(self, d):
        self.data = dict(d); self._anim.stop(); self._anim.setStartValue(0.0); self._anim.setEndValue(1.0); self._anim.start()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        c = pal(); side = min(self.width(), self.height()) - 16
        r = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        th = side * 0.14
        inner = r.adjusted(th / 2, th / 2, -th / 2, -th / 2)
        pen = QPen(QColor(c["surface2"]), th); pen.setCapStyle(Qt.FlatCap); p.setPen(pen); p.drawArc(inner, 0, 360 * 16)
        total = sum(self.data.values())
        if total:
            start = 90 * 16
            for k in ("Critical", "Major", "Minor", "Info"):
                v = self.data.get(k, 0)
                if not v:
                    continue
                span = -int(v / total * 360 * 16 * self._t)
                pen = QPen(QColor(SEV[k]), th); pen.setCapStyle(Qt.FlatCap); p.setPen(pen)
                p.drawArc(inner, start, span - (0 if span == 0 else -0)); start += span
        p.setPen(QColor(c["text"])); f = QFont(self.font()); f.setPointSize(26); f.setWeight(QFont.ExtraBold); p.setFont(f)
        p.drawText(r.adjusted(0, -10, 0, 0), Qt.AlignCenter, str(int(total * self._t)))
        f.setPointSize(9); f.setWeight(QFont.Medium); p.setFont(f); p.setPen(QColor(c["muted"]))
        p.drawText(r.adjusted(0, 44, 0, 0), Qt.AlignCenter, "differences")


class BarList(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []; self._t = 1.0; self.setMinimumHeight(180)
        self._anim = QVariantAnimation(self, duration=800, valueChanged=self._step); self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def _step(self, v):
        self._t = v; self.update()

    def set_rows(self, rows):
        self.rows = rows[:8]; self.setMinimumHeight(max(120, 34 * len(self.rows) + 8))
        self._anim.stop(); self._anim.setStartValue(0.0); self._anim.setEndValue(1.0); self._anim.start()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); c = pal()
        if not self.rows:
            p.setPen(QColor(c["muted"])); p.drawText(self.rect(), Qt.AlignCenter, "No data yet"); return
        mx = max(v for _, v in self.rows) or 1; lw = 150; y = 4
        for name, v in self.rows:
            p.setPen(QColor(c["muted"])); p.drawText(QRectF(0, y, lw - 8, 26), Qt.AlignVCenter | Qt.AlignRight, name)
            w = (self.width() - lw - 46) * (v / mx) * self._t
            g = QRectF(lw, y + 5, max(4.0, w), 16)
            p.setPen(Qt.NoPen); p.setBrush(QColor(c["surface2"])); p.drawRoundedRect(QRectF(lw, y + 5, self.width() - lw - 46, 16), 8, 8)
            from PySide6.QtGui import QLinearGradient
            gr = QLinearGradient(g.left(), 0, g.right(), 0); gr.setColorAt(0, QColor(c["primary"])); gr.setColorAt(1, QColor(c["gold"]))
            p.setBrush(QBrush(gr)); p.drawRoundedRect(g, 8, 8)
            p.setPen(QColor(c["text"])); p.drawText(QRectF(g.right() + 8, y, 40, 26), Qt.AlignVCenter | Qt.AlignLeft, str(v))
            y += 34


class Ring(QWidget):
    """Small progress ring used for 'reviewed' progress."""
    def __init__(self, parent=None):
        super().__init__(parent); self.v = 0.0; self.setFixedSize(64, 64)

    def set_value(self, f):
        self.v = max(0.0, min(1.0, f)); self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); c = pal()
        r = QRectF(7, 7, 50, 50)
        p.setPen(QPen(QColor(c["surface2"]), 6)); p.drawArc(r, 0, 360 * 16)
        pen = QPen(QColor(c["ok"]), 6); pen.setCapStyle(Qt.RoundCap); p.setPen(pen); p.drawArc(r, 90 * 16, -int(self.v * 360 * 16))
        p.setPen(QColor(c["text"])); p.drawText(self.rect(), Qt.AlignCenter, f"{int(self.v * 100)}%")


# --------------------------------------------------------------------------------------------- zoomable scan view
class ZoomView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self)); self.item = None; self.autofit = True; self._focus = 0.0
        self.setDragMode(QGraphicsView.ScrollHandDrag); self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setFrameShape(QFrame.NoFrame); self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def clear_msg(self, text):
        self.scene().clear(); self.item = None
        t = self.scene().addText(text); t.setDefaultTextColor(QColor(pal()["muted"])); t.setTextWidth(max(160, self.viewport().width() - 40))
        self.resetTransform(); self.setSceneRect(self.scene().itemsBoundingRect())

    def set_image(self, img, focus_y=0.0):
        pm = pil_to_pixmap(img)
        self.scene().clear(); self.item = self.scene().addPixmap(pm); self.item.setTransformationMode(Qt.SmoothTransformation)
        self.setSceneRect(QRectF(pm.rect())); self._focus = focus_y; self.autofit = True
        self.fit(); self.centerOn(pm.width() / 2, max(focus_y, self.viewport().height() / 2 / max(self.transform().m11(), 0.01)))

    def fit(self):
        if not self.item:
            return
        self.resetTransform()
        s = max(0.05, (self.width() - 22) / self.item.pixmap().width()); self.scale(s, s)

    def zoom(self, f):
        self.autofit = False; self.scale(f, f)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            self.zoom(1.15 if e.angleDelta().y() > 0 else 1 / 1.15)
        else:
            super().wheelEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.autofit and self.item and e.size().width() != e.oldSize().width():
            c = self.mapToScene(self.viewport().rect().center()); self.fit(); self.centerOn(c)


class ScanPanel(QFrame):
    """ZoomView + toolbar (zoom, fit, rotate page)."""
    rotateRequested = Signal(int)

    def __init__(self, title="Scan preview", rotate=True, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        v = QVBoxLayout(self); v.setContentsMargins(14, 12, 14, 12); v.setSpacing(8)
        bar = QHBoxLayout(); bar.setSpacing(6)
        self.title = label(title, "h2"); bar.addWidget(self.title); bar.addStretch(1)
        self.btns = []
        def mk(name, tip, cb):
            b = QPushButton(); b.setProperty("kind", "ghost"); b.setToolTip(tip); b.setFixedSize(34, 34); b.clicked.connect(cb); b._ic = name
            bar.addWidget(b); self.btns.append(b); return b
        self.view = ZoomView()
        mk("zin", "Zoom in", lambda: self.view.zoom(1.2)); mk("zout", "Zoom out", lambda: self.view.zoom(1 / 1.2))
        mk("fit", "Fit width", lambda: (setattr(self.view, "autofit", True), self.view.fit()))
        if rotate:
            bar.addSpacing(8)
            mk("rotl", "Rotate page 90° anti-clockwise and re-read it", lambda: self.rotateRequested.emit(-90))
            mk("rotr", "Rotate page 90° clockwise and re-read it", lambda: self.rotateRequested.emit(90))
            mk("rot180", "Turn page upside-down and re-read it", lambda: self.rotateRequested.emit(180))
        v.addLayout(bar); v.addWidget(self.view, 1)
        self.caption = label("", "small"); v.addWidget(self.caption)
        self.refresh_theme()

    def refresh_theme(self):
        for b in self.btns:
            b.setIcon(icon(b._ic, pal()["text"], 18))


# --------------------------------------------------------------------------------------------- toast
class Toast(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter); self.hide(); self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._t = QTimer(self, singleShot=True, timeout=self.hide)

    def show_msg(self, text, kind="ok"):
        c = pal()
        col = {"ok": c["ok"], "err": "#FF5C7A", "info": c["primary"]}.get(kind, c["primary"])
        self.setStyleSheet(f"background:{c['surface2']};border:1px solid {col};border-radius:14px;padding:10px 18px;font-weight:600;color:{c['text']};")
        self.setText(text); self.adjustSize()
        p = self.parentWidget()
        self.move((p.width() - self.width()) // 2, p.height() - self.height() - 40); self.raise_(); self.show(); self._t.start(3200)


# --------------------------------------------------------------------------------------------- background worker
class Worker(QThread):
    progress = Signal(float, str)
    succeeded = Signal(object)
    failed = Signal(str, str)
    cancelled = Signal()

    def __init__(self, fn, parent=None, cancel_exc=None):
        super().__init__(parent)
        self.fn, self.cancel_event, self.cancel_exc = fn, threading.Event(), cancel_exc

    def run(self):
        try:
            res = self.fn(lambda f, m: self.progress.emit(float(f), str(m)), self.cancel_event)
            self.succeeded.emit(res)
        except BaseException as ex:   # noqa
            if self.cancel_exc and isinstance(ex, self.cancel_exc):
                self.cancelled.emit()
            else:
                import traceback
                self.failed.emit(str(ex), traceback.format_exc())

    def cancel(self):
        self.cancel_event.set()
