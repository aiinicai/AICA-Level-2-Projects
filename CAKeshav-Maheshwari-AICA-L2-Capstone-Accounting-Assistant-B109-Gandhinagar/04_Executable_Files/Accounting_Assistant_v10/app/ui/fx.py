"""Visual effects (v10): 3D gradient tiles with sparklines, glass cards with a glowing top edge, gradient titles,
hover lift / glow. Everything is painted by Qt itself (no images, no web view), reads the active theme at paint
time, so a theme switch repaints at once.

Performance rule kept: effects go on a handful of widgets per page (tiles, summary cards) - never on tables."""
from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QEvent, QObject, QPointF, QRectF, Qt, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient)
from PyQt6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QSizePolicy, QWidget

from . import theme


def _c(hexstr: str, alpha: int | None = None) -> QColor:
    c = QColor(hexstr)
    if alpha is not None:
        c.setAlpha(alpha)
    return c


def smooth_path(points: list[QPointF]) -> QPainterPath:
    """A smooth line through the points (Catmull-Rom turned into cubic Beziers)."""
    path = QPainterPath()
    if not points:
        return path
    path.moveTo(points[0])
    if len(points) < 3:
        for p in points[1:]:
            path.lineTo(p)
        return path
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i else points[i]
        p1, p2 = points[i], points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = QPointF(p1.x() + (p2.x() - p0.x()) / 6, p1.y() + (p2.y() - p0.y()) / 6)
        c2 = QPointF(p2.x() - (p3.x() - p1.x()) / 6, p2.y() - (p3.y() - p1.y()) / 6)
        path.cubicTo(c1, c2, p2)
    return path


def paint_sparkline(p: QPainter, rect: QRectF, values: list[float], colour: str, fill: bool = True) -> None:
    """Glowing sparkline: a soft wide stroke under a crisp one, a fading area beneath."""
    vals = [float(v) for v in values] or [0.0, 0.0]
    if len(vals) == 1:
        vals = vals * 2
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    flat = hi == lo
    n = len(vals)
    pts = [QPointF(rect.left() + rect.width() * i / (n - 1),
                   rect.center().y() if flat else rect.bottom() - (v - lo) / span * rect.height())
           for i, v in enumerate(vals)]
    line = smooth_path(pts)
    if fill and not flat:
        area = QPainterPath(line)
        area.lineTo(rect.right(), rect.bottom())
        area.lineTo(rect.left(), rect.bottom())
        area.closeSubpath()
        g = QLinearGradient(0, rect.top(), 0, rect.bottom())
        g.setColorAt(0, _c(colour, 90))
        g.setColorAt(1, _c(colour, 0))
        p.fillPath(area, QBrush(g))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(_c(colour, 70), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawPath(line)
    p.setPen(QPen(_c(colour, 255), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawPath(line)
    if not flat:
        last = pts[-1]
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_c(colour, 90))
        p.drawEllipse(last, 6, 6)
        p.setBrush(QColor("white"))
        p.drawEllipse(last, 2.6, 2.6)


def shadow(widget: QWidget, colour: str = "#000000", alpha: int = 120, blur: float = 30, dy: float = 10):
    eff = QGraphicsDropShadowEffect(widget)
    eff.setColor(_c(colour, alpha))
    eff.setBlurRadius(blur)
    eff.setOffset(0, dy)
    widget.setGraphicsEffect(eff)
    return eff


class _Hover(QObject):
    """Animates a 0..1 'hover' value on enter / leave and calls back with it."""

    def __init__(self, target: QWidget, on_value, ms: int = 180):
        super().__init__(target)
        self.anim = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=ms)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(on_value)
        self.value = 0.0
        target.installEventFilter(self)

    def eventFilter(self, obj, e):
        t = e.type()
        if t in (QEvent.Type.Enter, QEvent.Type.Leave):
            self.anim.stop()
            self.anim.setStartValue(self.value)
            self.anim.setEndValue(1.0 if t == QEvent.Type.Enter else 0.0)
            self.anim.start()
        return False


class GlowTile(QWidget):
    """A 3D stat tile: gradient body, glossy bevel along the top, embossed number, live sparkline. Lifts and glows
    on hover; the whole tile is a button."""
    clicked = pyqtSignal()

    def __init__(self, label: str, link: str, slot: int = 0, parent=None):
        super().__init__(parent)
        self.label, self.link, self.slot = label, link, slot
        self.value = "–"
        self.series: list[float] = []
        self.t = 0.0
        self.setMinimumHeight(132)
        self.setMaximumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.eff = shadow(self, self._colours()[0], 90, 26, 10)
        self._hover = _Hover(self, self._set_t)

    def _colours(self):
        tiles = theme.TILES or [("#2563EB", "#1E3A8A", "#93C5FD")]
        return tiles[self.slot % len(tiles)]

    def _set_t(self, v):
        self.t = float(v)
        self._hover.value = self.t
        c1 = self._colours()[0]
        self.eff.setColor(_c(c1, int(90 + 110 * self.t)))
        self.eff.setBlurRadius(26 + 22 * self.t)
        self.eff.setOffset(0, 10 + 6 * self.t)
        self.update()

    def set_value(self, value, series=None):
        self.value = str(value)
        if series is not None:
            self.series = list(series)
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)

    def paintEvent(self, _e):
        c1, c2, spark = self._colours()
        self.eff.setColor(_c(c1, int(90 + 110 * self.t)))
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        lift = 3 * self.t
        r = QRectF(self.rect()).adjusted(6, 6 - lift, -6, -8 - lift)
        rad = 16
        body = QPainterPath()
        body.addRoundedRect(r, rad, rad)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, _c(c1).lighter(100 + int(12 * self.t)))
        g.setColorAt(1, _c(c2))
        p.fillPath(body, QBrush(g))
        # gloss: a soft light from the top-left
        p.save()
        p.setClipPath(body)
        gl = QRadialGradient(r.left() + r.width() * 0.25, r.top(), r.width() * 0.7)
        gl.setColorAt(0, QColor(255, 255, 255, 46 + int(20 * self.t)))
        gl.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(r, QBrush(gl))
        # bevel: bright top lip, dark bottom lip (reads as depth)
        top = QLinearGradient(0, r.top(), 0, r.top() + r.height() * 0.42)
        top.setColorAt(0, QColor(255, 255, 255, 34))
        top.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(QRectF(r.left(), r.top(), r.width(), r.height() * 0.42), QBrush(top))
        bot = QLinearGradient(0, r.bottom() - 18, 0, r.bottom())
        bot.setColorAt(0, QColor(0, 0, 0, 0))
        bot.setColorAt(1, QColor(0, 0, 0, 60))
        p.fillRect(QRectF(r.left(), r.bottom() - 18, r.width(), 18), QBrush(bot))
        p.restore()
        p.setPen(QPen(QColor(255, 255, 255, int(55 + 90 * self.t)), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(body)
        # embossed number
        f = QFont(self.font())
        f.setPixelSize(34)
        f.setWeight(QFont.Weight.ExtraBold)
        p.setFont(f)
        x, y = r.left() + 20, r.top() + 46
        # sparkline: top right, beside the number and above the label, so it never runs into the words
        left = max(r.left() + r.width() * 0.42, x + p.fontMetrics().horizontalAdvance(self.value) + 28)
        sr = QRectF(left, r.top() + 16, r.right() - 18 - left, 38)
        if sr.width() > 40:
            paint_sparkline(p, sr, self.series, spark)
        p.setPen(QColor(0, 0, 0, 120))
        p.drawText(QPointF(x + 1.5, y + 2.5), self.value)
        p.setPen(QColor(255, 255, 255, 255))
        p.drawText(QPointF(x, y), self.value)
        f.setPixelSize(14)
        f.setWeight(QFont.Weight.Medium)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, 225))
        p.drawText(QPointF(x, y + 26), self.label)
        f.setPixelSize(13)
        f.setWeight(QFont.Weight.Bold)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, 255))
        p.drawText(QPointF(x, r.bottom() - 16), f"{self.link}  " + "→")
        p.end()


class GlassCard(QFrame):
    """A translucent card with a glowing gradient edge along the top and a soft shadow; the border takes the accent
    and the shadow brightens on hover."""

    def __init__(self, title: str = "", accent: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.accent = accent
        self.t = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.eff = shadow(self, "#000000", 110 if theme.DARK else 28, 30, 10)
        self._hover = _Hover(self, self._set_t, 220)
        self.title_lbl = QLabel(title, objectName="section") if title else None

    def _set_t(self, v):
        self.t = float(v)
        self._hover.value = self.t
        acc = self.accent or theme.ACCENT
        base = 110 if theme.DARK else 28
        self.eff.setColor(_c(acc, int(base * (1 - self.t) + 120 * self.t)) if self.t > 0.02
                          else QColor(0, 0, 0, base))
        self.eff.setBlurRadius(30 + 14 * self.t)
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        acc = self.accent or theme.ACCENT
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath()
        clip.addRoundedRect(r, 14, 14)
        p.setClipPath(clip)
        g = QLinearGradient(r.left(), 0, r.right(), 0)
        g.setColorAt(0, _c(acc, 255))
        g.setColorAt(0.55, _c(acc, 150))
        g.setColorAt(1, _c(acc, 0))
        p.fillRect(QRectF(r.left(), r.top(), r.width(), 3), QBrush(g))
        glow = QLinearGradient(0, r.top(), 0, r.top() + 46)
        glow.setColorAt(0, _c(acc, int(30 + 30 * self.t)))
        glow.setColorAt(1, _c(acc, 0))
        p.fillRect(QRectF(r.left(), r.top(), r.width(), 46), QBrush(glow))
        if self.t > 0.02:
            p.setClipping(False)
            p.setPen(QPen(_c(acc, int(160 * self.t)), 1.2))
            p.drawRoundedRect(r, 14, 14)
        p.end()


class GradientLabel(QLabel):
    """A heading painted with the theme's accent gradient and a faint glow."""

    def __init__(self, text: str = "", px: int = 24, parent=None):
        super().__init__(text, parent)
        self.px = px
        # the app stylesheet sets every widget's font size; this heading keeps its own (set here, used in paint)
        self.setStyleSheet(f"font-size: {px}px; font-weight: 800;")
        self.setMinimumHeight(px + 14)

    def _font(self):
        f = QFont(self.font())
        f.setPixelSize(self.px)
        f.setWeight(QFont.Weight.ExtraBold)
        return f

    def fontMetrics(self):
        from PyQt6.QtGui import QFontMetrics
        return QFontMetrics(self._font())

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fm = self.fontMetrics()
        x, y = 0, (self.height() + fm.ascent() - fm.descent()) / 2
        path = QPainterPath()
        path.addText(QPointF(x, y), self._font(), self.text())
        w = max(fm.horizontalAdvance(self.text()), 1)
        g = QLinearGradient(0, 0, w, 0)
        g.setColorAt(0, QColor(theme.ACCENT2 if theme.DARK else theme.ACCENT))
        g.setColorAt(1, QColor(theme.ACCENT if theme.DARK else theme.ACCENT2))
        if theme.DARK:
            p.setPen(QPen(_c(theme.GLOW, 60), 4))
            p.drawPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.fillPath(path, QBrush(g))
        p.end()

    def sizeHint(self):
        s = super().sizeHint()
        s.setWidth(self.fontMetrics().horizontalAdvance(self.text()) + 8)
        return s
