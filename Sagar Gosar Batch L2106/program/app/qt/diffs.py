"""Differences table model, severity pills and HTML rendering of styled runs."""
from html import escape

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QRectF, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QStyledItemDelegate

from .. import report_model as rm
from .theme import SEV, icon, pal

COLS = ["", "#", "Clause", "Severity", "Category", "Nature of difference", "Pg"]


def runs_html(runs, base_size=13):
    out = []
    for text, style in runs:
        t = escape(text).replace("\n", "<br>")
        col, fill, strike, under, ital = rm.STYLE_DEF.get(style, rm.STYLE_DEF[rm.PLAIN])
        css = []
        if col:
            css.append(f"color:#{col}")
        if fill:
            css.append(f"background-color:#{fill}")
        deco = " ".join(x for x, f in (("line-through", strike), ("underline", under)) if f)
        if deco:
            css.append(f"text-decoration:{deco}")
        if ital:
            css.append("font-style:italic")
        out.append(f'<span style="{";".join(css)}">{t}</span>' if css else t)
    return f'<div style="line-height:150%;font-size:{base_size}px">' + "".join(out) + "</div>"


class DiffModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent); self.items = []; self.reviewed = set()

    def set_items(self, items):
        self.beginResetModel(); self.items = list(items); self.reviewed = set(); self.endResetModel()

    def rowCount(self, p=QModelIndex()):
        return 0 if p.isValid() else len(self.items)

    def columnCount(self, p=QModelIndex()):
        return len(COLS)

    def headerData(self, s, o, role=Qt.DisplayRole):
        if o == Qt.Horizontal and role == Qt.DisplayRole:
            return COLS[s]

    def item(self, row):
        return self.items[row]

    def toggle(self, row):
        it = self.items[row]
        (self.reviewed.discard if it.id in self.reviewed else self.reviewed.add)(it.id)
        self.dataChanged.emit(self.index(row, 0), self.index(row, len(COLS) - 1))

    def data(self, ix, role=Qt.DisplayRole):
        it = self.items[ix.row()]; c = ix.column()
        if role == Qt.UserRole:
            return it
        if role == Qt.DisplayRole:
            return ["", it.id, rm.clause_label(it), it.severity, ", ".join(it.categories), it.summary, ",".join(str(p) for p in it.pages_b)][c]
        if role == Qt.ToolTipRole and c == 5:
            return it.summary
        if role == Qt.ForegroundRole and it.id in self.reviewed:
            return QColor(pal()["muted"])
        if role == Qt.TextAlignmentRole and c in (1, 6):
            return Qt.AlignCenter


class DiffProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent); self.sev = None; self.text = ""; self.show_ocr = False; self.hide_reviewed = False; self.cat = None; self.page = None

    def set_filters(self, sev=..., text=None, show_ocr=None, hide_reviewed=None, cat=..., page=...):
        if cat is not ...:
            self.cat = cat
        if page is not ...:
            self.page = page
        if sev is not ...:
            self.sev = sev
        if text is not None:
            self.text = text.lower().strip()
        if show_ocr is not None:
            self.show_ocr = show_ocr
        if hide_reviewed is not None:
            self.hide_reviewed = hide_reviewed
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        m = self.sourceModel(); it = m.items[row]
        if it.ocr_only and not self.show_ocr:
            return False
        if self.sev and it.severity != self.sev:
            return False
        if self.hide_reviewed and it.id in m.reviewed:
            return False
        if self.cat and self.cat not in it.categories:
            return False
        if self.page is not None and self.page not in (it.pages_b or []):
            return False
        if self.text:
            blob = " ".join([it.summary, it.text_a, it.text_b, " ".join(it.categories), rm.clause_label(it)]).lower()
            if self.text not in blob:
                return False
        return True


class PillDelegate(QStyledItemDelegate):
    """Draws the review tick (column 0) and coloured severity pills (column 3)."""

    def paint(self, p, opt, ix):
        c = ix.column()
        if c not in (0, 3):
            return super().paint(p, opt, ix)
        from PySide6.QtWidgets import QStyle
        if opt.state & QStyle.State_Selected:
            p.fillRect(opt.rect, QColor(pal()["sel"]))
        p.save(); p.setRenderHint(QPainter.Antialiasing)
        it = ix.data(Qt.UserRole); model = ix.model()
        src = model.sourceModel() if hasattr(model, "sourceModel") else model
        if c == 0:
            done = it.id in src.reviewed; r = QRectF(opt.rect.center().x() - 9, opt.rect.center().y() - 9, 18, 18)
            p.setPen(QColor(pal()["ok"] if done else pal()["border"])); p.setBrush(QColor(pal()["ok"]) if done else Qt.NoBrush)
            p.drawRoundedRect(r, 6, 6)
            if done:
                ic = icon("check", "#06281C", 14, 2.6).pixmap(14, 14); p.drawPixmap(int(r.x() + 2), int(r.y() + 2), ic)
        else:
            col = QColor(SEV.get(it.severity, "#62B4FF")); txt = it.severity
            f = QFont(opt.font); f.setBold(True); f.setPointSizeF(max(8.0, f.pointSizeF() - 1.5)); p.setFont(f)
            w = p.fontMetrics().horizontalAdvance(txt) + 22; h = 22
            r = QRectF(opt.rect.left() + 8, opt.rect.center().y() - h / 2, w, h)
            bg = QColor(col); bg.setAlpha(46); p.setPen(Qt.NoPen); p.setBrush(bg); p.drawRoundedRect(r, 11, 11)
            p.setBrush(col); p.drawEllipse(QRectF(r.left() + 8, r.center().y() - 3, 6, 6))
            p.setPen(col); p.drawText(QRectF(r.left() + 18, r.top(), w - 18, h), Qt.AlignVCenter | Qt.AlignLeft, txt)
        p.restore()
