"""Page selector (with thumbnails) and the Ctrl+K command palette."""
from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QListView)

from . import theme
from .theme import icon, pal
from .widgets import label


class _Thumbs(QThread):
    thumb = Signal(int, QImage)

    def __init__(self, path, total, parent=None):
        super().__init__(parent); self.path, self.total, self._stop = path, total, False

    def run(self):
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(self.path)
            for i in range(self.total):
                if self._stop:
                    break
                im = pdf[i].render(scale=0.26).to_pil().convert("RGB")
                qi = QImage(im.tobytes("raw", "RGB"), im.width, im.height, 3 * im.width, QImage.Format_RGB888).copy()
                self.thumb.emit(i + 1, qi)
            pdf.close()
        except Exception:
            pass

    def stop(self):
        self._stop = True


class PageSelectDialog(QDialog):
    def __init__(self, parent, path, total, preselected=None):
        super().__init__(parent)
        self.setWindowTitle("Select pages of the executed copy"); self.resize(980, 720)
        self.total, self.selected = total, None
        v = QVBoxLayout(self); v.setContentsMargins(22, 20, 22, 18); v.setSpacing(12)
        v.addWidget(label("Choose the pages to compare", "title"))
        v.addWidget(label("Untick stamp-paper, cover, blank or annexure pages. Click a page to tick / untick it.", "muted", True))
        bar = QHBoxLayout(); bar.setSpacing(8)
        self.rng = QLineEdit(); self.rng.setPlaceholderText("Type a range, e.g. 3-14, 16, 20-22"); self.rng.returnPressed.connect(self._apply_range)
        bar.addWidget(self.rng, 1)
        ap = QPushButton("Apply range"); ap.clicked.connect(self._apply_range); bar.addWidget(ap)
        for t, cb in (("All", lambda: self._set(lambda p: True)), ("None", lambda: self._set(lambda p: False)),
                      ("Invert", lambda: self._set(lambda p: not self._on(p))), ("Odd", lambda: self._set(lambda p: p % 2 == 1)),
                      ("Even", lambda: self._set(lambda p: p % 2 == 0))):
            b = QPushButton(t); b.setProperty("kind", "ghost"); b.clicked.connect(cb); bar.addWidget(b)
        v.addLayout(bar)
        self.lw = QListWidget(); self.lw.setViewMode(QListView.IconMode); self.lw.setIconSize(QSize(120, 160)); self.lw.setResizeMode(QListView.Adjust)
        self.lw.setMovement(QListView.Static); self.lw.setSpacing(10); self.lw.setUniformItemSizes(True); self.lw.setWordWrap(True)
        self.lw.setGridSize(QSize(146, 206))
        ph = QPixmap(120, 160); ph.fill(Qt.transparent)
        sel = set(preselected) if preselected else set(range(1, total + 1))
        for p in range(1, total + 1):
            it = QListWidgetItem(QIcon(ph), f"Page {p}"); it.setData(Qt.UserRole, p)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Checked if p in sel else Qt.Unchecked)
            it.setTextAlignment(Qt.AlignHCenter); self.lw.addItem(it)
        self.lw.itemClicked.connect(self._toggle); self.lw.itemChanged.connect(lambda *_: self._count())
        v.addWidget(self.lw, 1)
        foot = QHBoxLayout(); self.cnt = label("", "muted"); foot.addWidget(self.cnt, 1)
        c = QPushButton("Cancel"); c.clicked.connect(self.reject); foot.addWidget(c)
        ok = QPushButton("Use these pages"); ok.setProperty("kind", "primary"); ok.clicked.connect(self._ok); foot.addWidget(ok)
        v.addLayout(foot); self._count()
        self._th = None
        if str(path).lower().endswith(".pdf"):
            self._th = _Thumbs(path, total, self); self._th.thumb.connect(self._thumb); self._th.start()

    def _thumb(self, p, qi):
        it = self.lw.item(p - 1)
        if it:
            it.setIcon(QIcon(QPixmap.fromImage(qi)))

    def _on(self, p):
        return self.lw.item(p - 1).checkState() == Qt.Checked

    def _toggle(self, it):
        it.setCheckState(Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked)

    def _set(self, fn):
        self.lw.blockSignals(True)
        for p in range(1, self.total + 1):
            self.lw.item(p - 1).setCheckState(Qt.Checked if fn(p) else Qt.Unchecked)
        self.lw.blockSignals(False); self._count()

    def _apply_range(self):
        from ..pages import parse_pages
        try:
            keep = set(parse_pages(self.rng.text(), self.total))
        except Exception:
            self.cnt.setText("Could not read that range – use a format like 3-14,16"); return
        if keep:
            self._set(lambda p: p in keep)

    def _count(self):
        n = sum(1 for p in range(1, self.total + 1) if self._on(p))
        self.cnt.setText(f"{n} of {self.total} page(s) selected")

    def _ok(self):
        self.selected = [p for p in range(1, self.total + 1) if self._on(p)]
        if not self.selected:
            self.cnt.setText("Tick at least one page."); return
        self.accept()

    def done(self, r):
        if self._th:
            self._th.stop(); self._th.wait(1500)
        super().done(r)


class CommandPalette(QDialog):
    def __init__(self, parent, commands):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose); self.commands = commands; self.setModal(True)
        c = pal()
        self.setStyleSheet(f"QDialog{{background:{c['surface']};border:1px solid {c['primary']};border-radius:18px;}}")
        v = QVBoxLayout(self); v.setContentsMargins(14, 14, 14, 12); v.setSpacing(8)
        self.ed = QLineEdit(); self.ed.setPlaceholderText("Type a command…  (Enter to run, Esc to close)"); self.ed.textChanged.connect(self._fill)
        v.addWidget(self.ed)
        self.lw = QListWidget(); self.lw.setIconSize(QSize(18, 18)); self.lw.itemActivated.connect(self._run); self.lw.itemClicked.connect(self._run)
        v.addWidget(self.lw); self.resize(580, 420); self._fill("")
        self.ed.installEventFilter(self)
        if parent:
            g = parent.geometry(); self.move(g.center().x() - 290, g.top() + 110)

    def eventFilter(self, o, e):
        from PySide6.QtCore import QEvent
        if o is self.ed and e.type() == QEvent.KeyPress:
            if e.key() in (Qt.Key_Down, Qt.Key_Up):
                r = self.lw.currentRow() + (1 if e.key() == Qt.Key_Down else -1)
                self.lw.setCurrentRow(max(0, min(self.lw.count() - 1, r))); return True
            if e.key() in (Qt.Key_Return, Qt.Key_Enter):
                if self.lw.currentItem():
                    self._run(self.lw.currentItem())
                return True
        return super().eventFilter(o, e)

    def _fill(self, text):
        self.lw.clear(); toks = text.lower().split()
        for name, hint, ic, fn in self.commands:
            if all(t in name.lower() for t in toks):
                it = QListWidgetItem(icon(ic, pal()["text"], 18), f"{name}" + (f"      {hint}" if hint else "")); it.setData(Qt.UserRole, fn)
                self.lw.addItem(it)
        if self.lw.count():
            self.lw.setCurrentRow(0)

    def _run(self, it):
        fn = it.data(Qt.UserRole); self.close(); fn()
