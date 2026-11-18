"""Workbench: the one screen for daily work - queue on the left, the document in the middle, the proposed entry
on the right. Ready invoices can be posted in one go."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from decimal import Decimal
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, QSize, QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QFont, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton,
                             QScrollArea, QSizePolicy, QSpinBox, QSplitter, QStyle, QStyledItemDelegate,
                             QTabWidget, QVBoxLayout, QWidget)
from sqlalchemy import select

from ..config import app_dir
from ..db.models import Company, Invoice as InvoiceRow, Vendor
from ..engine import assess as assess_mod, intake, rules, tds as tds_mod
from ..engine.voucher import InvLine, Voucher, to_xml
from ..extract import readers
from ..extract.parser import parse_date
from ..extract.pipeline import process
from ..extract.schema import TaxRow
from ..extract.validator import validate
from ..gst_states import state_code
from . import theme
from .common import LedgerCombo, PeriodPicker, VoucherGrid, ask_lock_reason, dec, run_bg, tone
from .ledger_dialog import LedgerDialog
from ..engine import party as party_mod
import time as _time

_BAL_CACHE: dict = {}

BOOK_AS = [("Purchase", "purchase_accounting"), ("Purchase (items)", "purchase_item"), ("Journal", "journal")]

FIELDS = [("supplier_name", "Supplier"), ("supplier_gstin", "Supplier GSTIN"), ("invoice_no", "Invoice no"),
          ("invoice_date", "Invoice date"), ("place_of_supply", "Place of supply"), ("taxable_total", "Taxable value"),
          ("cgst_total", "CGST"), ("sgst_total", "SGST / UTGST"), ("igst_total", "IGST"), ("cess_total", "Cess"),
          ("tcs", "TCS"), ("round_off", "Round off"), ("grand_total", "Invoice total")]
MONEY = {"taxable_total", "cgst_total", "sgst_total", "igst_total", "cess_total", "tcs", "round_off", "grand_total"}


def fmt_date(d: str) -> str:
    return f"{d[6:8]}-{d[4:6]}-{d[:4]}" if d and len(d) == 8 else (d or "")


def fmt_money(v) -> str:
    try:
        v = Decimal(str(v or 0))
    except Exception:
        return str(v)
    # Indian grouping: 2,78,645.00
    s = f"{abs(v):.2f}"
    whole, frac = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
        whole = f"{head},{tail}"
    return ("-" if v < 0 else "") + f"₹ {whole}.{frac}"


def chip(text: str, state: str) -> QLabel:
    fg, bg = theme.STATUS.get(state, theme.STATUS["info"])
    lb = QLabel(text, objectName="chip")
    tone(lb, state)
    return lb


# ====================================================================== queue
class QueueItem(QFrame):
    def __init__(self, row, verdict):
        super().__init__(objectName="qitem")
        e = row.extraction or {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(3)
        full = e.get("supplier_name") or Path(row.file_path).name
        name = QLabel(full if len(full) <= 28 else full[:27] + "…")
        name.setStyleSheet("font-weight: 600;")
        name.setToolTip(full)
        lay.addWidget(name)
        r2 = QHBoxLayout()
        amt = QLabel(fmt_money(e.get("grand_total")) if e.get("grand_total") else "—")
        amt.setStyleSheet("font-weight: 600;")
        dt = QLabel(fmt_date(e.get("invoice_date", "")), objectName="muted")
        r2.addWidget(amt)
        r2.addStretch(1)
        r2.addWidget(dt)
        lay.addLayout(r2)
        r3 = QHBoxLayout()
        c = chip(verdict.reason, verdict.state)
        c.setToolTip(verdict.detail or verdict.reason)
        r3.addWidget(c)
        inv_no = e.get("invoice_no", "")
        src = {"gemini": "Gemini", "text": "PDF text", "ocr": "OCR", "docx": "Word", "xlsx": "Excel",
               "qr": "QR"}.get(row.extraction_source or "", "")
        meta = QLabel((inv_no[:16] + "…" if len(inv_no) > 17 else inv_no) or src, objectName="muted")
        meta.setStyleSheet("font-size: 11px;")
        meta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        meta.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        meta.setToolTip(f"Invoice {inv_no} · read by {src}" if inv_no else f"Read by {src}")
        r3.addWidget(meta, 1)
        lay.addLayout(r3)

    def set_selected(self, on: bool):
        self.setProperty("selected", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class QueueDelegate(QStyledItemDelegate):
    """Draws each invoice card directly (no widgets per invoice), so hundreds of invoices list instantly."""
    H = 78

    def sizeHint(self, option, index):
        return QSize(200, self.H)

    def paint(self, p, option, index):
        from PyQt6.QtCore import QRectF
        from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPen
        d = index.data(Qt.ItemDataRole.UserRole + 1) or {}
        r = QRectF(option.rect).adjusted(1, 1, -2, -7)
        sel = bool(option.state & QStyle.StateFlag.State_Selected)
        p.save()
        p.setRenderHint(p.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(theme.ACCENT if sel else theme.LINE), 2 if sel else 1))
        p.setBrush(QColor(theme.ACCENT_SOFT if sel else theme.SURFACE))
        p.drawRoundedRect(r, 10, 10)
        x, w = r.left() + 12, r.width() - 24
        f = QFont(option.font)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(theme.INK))
        fm = QFontMetrics(f)
        p.drawText(QRectF(x, r.top() + 7, w, 18), Qt.AlignmentFlag.AlignLeft,
                   fm.elidedText(d.get("name", ""), Qt.TextElideMode.ElideRight, int(w)))
        p.drawText(QRectF(x, r.top() + 27, w, 18), Qt.AlignmentFlag.AlignLeft, d.get("amount", ""))
        f2 = QFont(option.font)
        p.setFont(f2)
        p.setPen(QColor(theme.MUTED))
        p.drawText(QRectF(x, r.top() + 27, w, 18), Qt.AlignmentFlag.AlignRight, d.get("date", ""))
        # status chip
        fg, bg = theme.STATUS.get(d.get("state", "info"), theme.STATUS["info"])
        f3 = QFont(option.font)
        f3.setPointSizeF(max(7.0, f3.pointSizeF() - 1.5))
        f3.setBold(True)
        p.setFont(f3)
        fm3 = QFontMetrics(f3)
        text = fm3.elidedText(d.get("chip", ""), Qt.TextElideMode.ElideRight, int(w * 0.62))
        cw = fm3.horizontalAdvance(text) + 16
        chip_r = QRectF(x, r.top() + 49, cw, 18)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(bg))
        p.drawRoundedRect(chip_r, 9, 9)
        p.setPen(QColor(fg))
        p.drawText(chip_r, Qt.AlignmentFlag.AlignCenter, text)
        p.setFont(f3)
        p.setPen(QColor(theme.MUTED))
        meta_w = w - cw - 8
        p.drawText(QRectF(x + cw + 8, r.top() + 49, meta_w, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   fm3.elidedText(d.get("meta", ""), Qt.TextElideMode.ElideRight, int(meta_w)))
        p.restore()


def _card_data(row, verdict) -> dict:
    e = row.extraction or {}
    inv_no = e.get("invoice_no", "")
    src = {"gemini": "Gemini", "text": "PDF text", "ocr": "OCR", "docx": "Word", "xlsx": "Excel",
           "qr": "QR", "layout": "Learned layout"}.get(row.extraction_source or "", "")
    return {"name": e.get("supplier_name") or Path(row.file_path).name,
            "amount": fmt_money(e.get("grand_total")) if e.get("grand_total") else "—",
            "date": fmt_date(e.get("invoice_date", "")), "chip": verdict.reason, "state": verdict.state,
            "meta": inv_no or src,
            "tip": f"{e.get('supplier_name', '')}\n{verdict.detail or verdict.reason}" +
                   (f"\nInvoice {inv_no} · read by {src}" if inv_no else "")}


class QueuePanel(QWidget):
    selected = pyqtSignal(str)
    post_ready = pyqtSignal()
    FILTERS = [("attention", "Fix"), ("ready", "Ready"), ("posted", "Posted"), ("all", "All")]

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(240)
        self.setMaximumWidth(360)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 8, 14)
        lay.setSpacing(10)
        seg = QWidget(objectName="segbar")
        sl = QHBoxLayout(seg)
        sl.setContentsMargins(3, 3, 3, 3)
        sl.setSpacing(2)
        self.seg_buttons = {}
        grp = QButtonGroup(self)
        for key, label in self.FILTERS:
            b = QPushButton(label, objectName="seg", checkable=True)
            b.clicked.connect(lambda _=False, k=key: self.set_filter(k))
            grp.addButton(b)
            sl.addWidget(b)
            self.seg_buttons[key] = b
        self.period = PeriodPicker("workbench", "")
        self.period.compact(True)
        self.period.setToolTip("Invoices dated in this period (undated ones always show)")
        lay.addWidget(self.period)
        lay.addWidget(seg)
        self.list = QListWidget(objectName="queue")
        self.list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list.setItemDelegate(QueueDelegate(self.list))
        self.list.setUniformItemSizes(True)
        self.list.currentRowChanged.connect(self._picked)
        lay.addWidget(self.list, 1)
        self.empty = QLabel("", objectName="muted", alignment=Qt.AlignmentFlag.AlignCenter, wordWrap=True)
        lay.addWidget(self.empty)
        self.btn_post_ready = QPushButton("Post all ready", objectName="primary")
        self.btn_post_ready.clicked.connect(self.post_ready.emit)
        lay.addWidget(self.btn_post_ready)
        self.filter = "attention"
        self.items: list[tuple] = []          # (row, verdict, suggestion)
        self.seg_buttons["attention"].setChecked(True)

    def set_items(self, items, keep_id: str | None = None):
        self.items = items
        counts = {k: 0 for k, _ in self.FILTERS}
        for _, v, _s in items:
            k = "attention" if v.state in ("attention", "blocked") else v.state
            if k in counts:
                counts[k] += 1
        counts["all"] = len(items)
        for k, label in self.FILTERS:
            self.seg_buttons[k].setText(f"{label} {counts[k]}" if k != "all" else label)
        ready = counts["ready"]
        self.btn_post_ready.setText(f"Post all ready ({ready})")
        self.btn_post_ready.setEnabled(ready > 0)
        self._render(keep_id)

    def set_filter(self, key: str):
        self.filter = key
        self.seg_buttons[key].setChecked(True)
        self._render(None)

    def visible_ids(self) -> list[str]:
        return [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())]

    def _render(self, keep_id):
        self.list.blockSignals(True)
        self.list.clear()
        shown = [(r, v, s) for r, v, s in self.items
                 if self.filter == "all" or v.state == self.filter
                 or (self.filter == "attention" and v.state in ("attention", "blocked"))]
        self.list.setUpdatesEnabled(False)
        for r, v, _s in shown:
            it = QListWidgetItem()
            it.setData(Qt.ItemDataRole.UserRole, r.id)
            d = _card_data(r, v)
            it.setData(Qt.ItemDataRole.UserRole + 1, d)
            it.setToolTip(d["tip"])
            it.setSizeHint(QSize(200, QueueDelegate.H))
            self.list.addItem(it)
        self.list.setUpdatesEnabled(True)
        self.list.blockSignals(False)
        self.empty.setVisible(not shown)
        self.empty.setText({"attention": "Nothing to fix 🎉", "ready": "No invoices ready to post yet",
                            "posted": "Nothing posted yet", "all": "No invoices yet: click “Read new invoices”."}
                           [self.filter])
        ids = self.visible_ids()
        if keep_id in ids:
            self.list.setCurrentRow(ids.index(keep_id))
        elif ids:
            self.list.setCurrentRow(0)
        self._highlight()

    def _picked(self, i):
        self._highlight()
        if 0 <= i < self.list.count():
            self.selected.emit(self.list.item(i).data(Qt.ItemDataRole.UserRole))

    def _highlight(self):
        self.list.viewport().update()

    def step(self, d: int):
        n = self.list.count()
        if n:
            self.list.setCurrentRow(max(0, min(n - 1, self.list.currentRow() + d)))


# ====================================================================== document preview
class PreviewPanel(QTabWidget):
    def __init__(self):
        super().__init__()
        self.pix: QPixmap | None = None
        self.zoom = 1.0
        doc = QWidget()
        dl = QVBoxLayout(doc)
        dl.setContentsMargins(0, 8, 0, 0)
        bar = QHBoxLayout()
        self.title = QLabel("", objectName="muted")
        bar.addWidget(self.title, 1)
        for txt, fn in (("−", lambda: self._zoom(0.85)), ("Fit", lambda: self._zoom(None)),
                        ("+", lambda: self._zoom(1.18)), ("Open file", self.open_file),
                        ("Hide", self.hide_pane)):
            b = QPushButton(txt, objectName="ghost")
            b.clicked.connect(fn)
            bar.addWidget(b)
        dl.addLayout(bar)
        self.img = QLabel(alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.img.setStyleSheet(f"background: {theme.SURFACE}; border: 1px solid {theme.LINE}; border-radius: 8px;")
        self.scroll = QScrollArea(widgetResizable=True)
        self.scroll.setWidget(self.img)
        dl.addWidget(self.scroll, 1)
        self.text = QPlainTextEdit(readOnly=True)
        self.text.setFont(QFont("Consolas", 9))
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.trail = QPlainTextEdit(readOnly=True)
        self.addTab(doc, "Document")
        self.addTab(self.text, "Text")
        self.addTab(self.trail, "How it was read")
        self.path = ""

    def show_row(self, row):
        self.path = row.file_path
        e = row.extraction or {}
        self.title.setText(Path(row.file_path).name)
        self.text.setPlainText(e.get("_text") or "(no text)")
        self.trail.setPlainText("\n".join(e.get("_trail", [])))
        self.pix = None
        p = Path(row.file_path)
        try:
            doc = readers.read(p) if p.exists() else None
            if doc and doc.kind == "pdf" and not doc.page_images:
                doc.page_images = readers.render_pdf(p)[:1]
            if doc and doc.page_images:
                pm = QPixmap()
                pm.loadFromData(doc.page_images[0])
                self.pix = pm if not pm.isNull() else None
        except Exception:
            pass
        if self.pix:
            self.zoom = None
            self._zoom(None)
        else:
            self.img.setPixmap(QPixmap())
            self.img.setText("No page image for this file type.\nSee the Text tab, or Open file."
                             if p.exists() else "File not found (moved or deleted).")
            self.img.setStyleSheet(f"color: {theme.MUTED}; background: {theme.SURFACE}; border: 1px solid "
                                   f"{theme.LINE}; border-radius: 8px; padding: 40px;")

    def _zoom(self, f):
        if not self.pix:
            return
        base = max(200, self.scroll.viewport().width() - 24)
        self.zoom = 1.0 if f is None else max(0.4, min(3.0, (self.zoom or 1.0) * f))
        self.img.setStyleSheet(f"background: {theme.SURFACE}; border: 1px solid {theme.LINE}; border-radius: 8px;")
        self.img.setPixmap(self.pix.scaledToWidth(int(base * self.zoom), Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.pix and (self.zoom in (None, 1.0)):
            self._zoom(None)

    def hide_pane(self):
        w = self.parentWidget()
        while w is not None and not isinstance(w, Workbench):
            w = w.parentWidget()
        if w is not None:
            w.entry.btn_doc.setVisible(True)
            w.toggle_document()

    def open_file(self):
        if self.path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.path))


# ====================================================================== entry panel
class _EnterMovesOn(QObject):
    """Tally habit: Enter moves to the next field."""

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.ShortcutOverride and ev.key() == Qt.Key.Key_A and \
                ev.modifiers() == Qt.KeyboardModifier.ControlModifier:
            ev.ignore()                     # let Ctrl+A reach the "Accept & post" shortcut, as in Tally
            return True
        if ev.type() == QEvent.Type.KeyPress and ev.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) \
                and not ev.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier):
            obj.focusNextChild()
            return True
        return False


class EntryPanel(QWidget):
    posted = pyqtSignal(str)
    changed = pyqtSignal()

    def __init__(self, st):
        super().__init__()
        self.st = st
        self.row = None
        self.company = None
        self.inv = None
        self.voucher: Voucher | None = None
        self.masters = None
        self._style_choice: dict[str, str] = {}
        self.setMinimumWidth(360)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 14, 14, 14)
        outer.setSpacing(10)

        scroll = QScrollArea(widgetResizable=True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 6, 0)
        bl.setSpacing(10)

        # summary card
        sc = QFrame(objectName="card")
        sl = QGridLayout(sc)
        sl.setContentsMargins(16, 14, 16, 14)
        self.s_name = QLabel("", objectName="h2", wordWrap=True)
        self.s_state = QLabel("")
        self.s_meta = QLabel("", objectName="muted", wordWrap=True)
        self.s_total = QLabel("", objectName="money")
        self.s_tax = QLabel("", objectName="muted")
        sl.addWidget(self.s_name, 0, 0)
        sl.addWidget(self.s_state, 0, 1, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        sl.addWidget(self.s_meta, 1, 0, 1, 2)
        sl.addWidget(self.s_total, 2, 0, 1, 2)
        self.s_tax.setWordWrap(True)
        sl.addWidget(self.s_tax, 3, 0, 1, 2)
        sl.setColumnStretch(0, 1)
        bl.addWidget(sc)

        # issues
        self.issue_box = QVBoxLayout()
        self.issue_box.setSpacing(6)
        bl.addLayout(self.issue_box)

        # supplier in Tally: live balance + recent entries + copy
        pc = QFrame(objectName="card")
        pl = QVBoxLayout(pc)
        pl.setContentsMargins(16, 12, 16, 12)
        pl.setSpacing(6)
        ph = QHBoxLayout()
        ph.addWidget(QLabel("Supplier in Tally", objectName="h2"))
        ph.addStretch(1)
        self.bal_lbl = QLabel("")
        self.bal_lbl.setStyleSheet("font-weight: 700;")
        ph.addWidget(self.bal_lbl)
        self.btn_bal = QPushButton("↻", objectName="ghost")
        self.btn_bal.setToolTip("Refresh balance from Tally")
        self.btn_bal.clicked.connect(lambda: self._load_balance(force=True))
        ph.addWidget(self.btn_bal)
        pl.addLayout(ph)
        self.party_sub = QLabel("", objectName="muted", wordWrap=True)
        pl.addWidget(self.party_sub)
        self.recent_box = QVBoxLayout()
        self.recent_box.setSpacing(4)
        pl.addLayout(self.recent_box)
        bl.addWidget(pc)
        self.party_card = pc

        # details (collapsible)
        dc = QFrame(objectName="card")
        dl = QVBoxLayout(dc)
        dl.setContentsMargins(16, 10, 16, 12)
        dh = QHBoxLayout()
        self.btn_details = QPushButton("▸  Invoice details", objectName="ghost")
        self.btn_details.setStyleSheet("font-weight: 600; color: #101828; text-align: left;")
        self.btn_details.clicked.connect(lambda: self._toggle_details())
        dh.addWidget(self.btn_details, 1)
        dl.addLayout(dh)
        self.details = QWidget()
        g = QGridLayout(self.details)
        g.setContentsMargins(0, 4, 0, 0)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        self.edits: dict[str, QLineEdit] = {}
        self._labels: dict[str, QLabel] = {}
        for i, (key, label) in enumerate(FIELDS):
            e = QLineEdit()
            if key in MONEY:
                e.setAlignment(Qt.AlignmentFlag.AlignRight)
            e.editingFinished.connect(self._dirty)
            self.edits[key] = e
            lab = QLabel(label, objectName="muted")
            self._labels[key] = lab
            g.addWidget(lab, (i // 2) * 2, i % 2)
            g.addWidget(e, (i // 2) * 2 + 1, i % 2)
        opts = QHBoxLayout()
        self.chk_rcm = QCheckBox("Reverse charge")
        self.chk_blocked = QCheckBox("ITC blocked u/s 17(5)")
        self.tds_combo = QComboBox()
        self.tds_combo.addItem("No TDS", "")
        for code, cfg in tds_mod.DEFAULT_SECTIONS.items():
            self.tds_combo.addItem(f"TDS {code} – {cfg['label']}", code)
        self.tds_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.tds_combo.setMinimumContentsLength(14)
        for w in (self.chk_rcm, self.chk_blocked):
            w.toggled.connect(self._dirty)
        self.tds_combo.currentIndexChanged.connect(self._dirty)
        opts.addWidget(self.chk_rcm)
        opts.addWidget(self.chk_blocked)
        opts.addStretch(1)
        g.addWidget(self.tds_combo, 39, 0, 1, 2)
        g.addLayout(opts, 40, 0, 1, 2)
        self.btn_apply = QPushButton("Recalculate entry")
        self.btn_apply.clicked.connect(self.apply_changes)
        g.addWidget(self.btn_apply, 41, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignRight)
        dl.addWidget(self.details)
        bl.addWidget(dc)

        # entry card: a simple form first; GST / TDS / RCM / round-off shown as labels; Dr/Cr grid on demand
        ec = QFrame(objectName="card")
        el = QVBoxLayout(ec)
        el.setContentsMargins(16, 14, 16, 14)
        el.setSpacing(8)
        th = QHBoxLayout()
        th.addWidget(QLabel("Entry", objectName="h2"))
        th.addStretch(1)
        self.conf_chip = QLabel("")
        th.addWidget(self.conf_chip)
        el.addLayout(th)
        self.party_banner = QFrame(objectName="issue")
        pb = QHBoxLayout(self.party_banner)
        pb.setContentsMargins(10, 6, 10, 6)
        self.party_lbl = QLabel("", wordWrap=True)
        self.btn_create_party = QPushButton("Create supplier in Tally", objectName="primary")
        self.btn_create_party.clicked.connect(self.create_supplier)
        pb.addWidget(self.party_lbl, 1)
        pb.addWidget(self.btn_create_party)
        self.party_banner.setStyleSheet(f"QFrame#issue {{ background: {theme.WARN_BG}; }}")
        self.party_banner.setVisible(False)
        el.addWidget(self.party_banner)
        qf = QGridLayout()
        qf.setHorizontalSpacing(10)
        qf.setVerticalSpacing(8)
        self.book_as = QComboBox()
        for label, key in BOOK_AS:
            self.book_as.addItem(label, key)
        self.book_as.setToolTip("Purchase or Journal for this invoice. Remembered for this supplier when you post.")
        self.book_as.currentIndexChanged.connect(self._book_as_changed)
        self.vtype = QComboBox()
        self.vtype.setEditable(True)
        self.vtype.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.vtype.setMinimumContentsLength(8)
        self.q_party = LedgerCombo([])
        self.q_party.setToolTip("Supplier ledger in Tally (credited)")
        self.q_party.currentTextChanged.connect(self._quick_party)
        self.q_head = LedgerCombo([])
        self.q_head.setToolTip("Expense / purchase ledger (debited with the taxable value)")
        self.q_head.currentTextChanged.connect(self._quick_head)
        self.q_head_note = QLabel("", objectName="muted")
        self.date_edit = QLineEdit()
        self.date_edit.setMaximumWidth(110)
        self.credit_days = QSpinBox(maximum=365)
        self.credit_days.setSuffix(" days")
        self.q_total = QLabel("", objectName="h2")
        rows = [("Book as", self.book_as, "Voucher type", self.vtype),
                ("Supplier", self.q_party, None, None),
                ("Expense head", self.q_head, None, None),
                ("Date", self.date_edit, "Credit", self.credit_days)]
        for r, (l1, w1, l2, w2) in enumerate(rows):
            qf.addWidget(QLabel(l1, objectName="muted"), r, 0)
            if l2:
                qf.addWidget(w1, r, 1)
                qf.addWidget(QLabel(l2, objectName="muted"), r, 2)
                qf.addWidget(w2, r, 3)
            else:
                qf.addWidget(w1, r, 1, 1, 3)
        qf.addWidget(self.q_head_note, 4, 1, 1, 3)
        qf.setColumnStretch(1, 1)
        qf.setColumnStretch(3, 1)
        el.addLayout(qf)
        self.auto_row = QHBoxLayout()
        self.auto_row.setSpacing(6)
        auto_w = QWidget(objectName="autorow")
        auto_w.setStyleSheet(f"QWidget#autorow {{ background: {theme.SURFACE}; }}")
        auto_w.setLayout(self.auto_row)
        self.auto_scroll = QScrollArea(widgetResizable=True)
        self.auto_scroll.setFixedHeight(38)
        self.auto_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.auto_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.auto_scroll.setWidget(auto_w)
        el.addWidget(QLabel("Added automatically", objectName="section"))
        el.addWidget(self.auto_scroll)
        self.narration = QLineEdit()
        self.narration.setPlaceholderText("Narration")
        el.addWidget(self.narration)
        tg = QHBoxLayout()
        self.btn_grid = QPushButton("▸  Show entry (Dr / Cr)", objectName="ghost")
        self.btn_grid.setStyleSheet("font-weight: 600; text-align: left;")
        self.btn_grid.clicked.connect(lambda: self._toggle_grid())
        tg.addWidget(self.btn_grid)
        tg.addStretch(1)
        tg.addWidget(self.q_total)
        el.addLayout(tg)
        self.grid = VoucherGrid()
        self.grid.table.setMinimumHeight(210)
        self.btn_new_ledger = QPushButton("+ New ledger  Alt+C")
        self.btn_new_ledger.setToolTip("Create a ledger directly in Tally")
        self.btn_new_ledger.clicked.connect(lambda: self.create_ledger())
        self.grid.bar.insertWidget(2, self.btn_new_ledger)
        self.grid.changed.connect(self._grid_changed)
        self.grid.setVisible(False)
        el.addWidget(self.grid)
        self.inv_table = None
        self.chk_remember = QCheckBox("Remember these ledgers for this supplier")
        self.chk_remember.setChecked(True)
        el.addWidget(self.chk_remember)
        self._enter = _EnterMovesOn(self)
        for w in (self.q_party.lineEdit(), self.q_head.lineEdit(), self.date_edit, self.narration):
            w.installEventFilter(self._enter)
        bl.insertWidget(2, ec)
        bl.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        # sticky action bar
        act = QHBoxLayout()
        self.btn_doc = QPushButton("Show document")
        self.btn_doc.setVisible(False)
        self.btn_aside = QPushButton("Set aside")
        self.btn_aside.setToolTip("Move to Exceptions (Ctrl+E)")
        self.btn_export = QPushButton("Export for Claude")
        self.btn_export.setToolTip("Save a masked text file describing how this invoice was read")
        self.btn_xml = QPushButton("XML", objectName="ghost")
        self.btn_post = QPushButton("Post to Tally   Ctrl+A", objectName="primary")
        self.btn_post.setMinimumHeight(36)
        self.btn_aside.clicked.connect(self.set_aside)
        self.btn_export.clicked.connect(self.export_debug)
        self.btn_xml.clicked.connect(self.preview_xml)
        self.btn_post.clicked.connect(self.post)
        for b in (self.btn_doc, self.btn_aside, self.btn_export, self.btn_xml):
            act.addWidget(b)
        act.addStretch(1)
        act.addWidget(self.btn_post)
        outer.addLayout(act)
        self._details_open = False
        self.details.setVisible(False)
        self.setEnabled(False)

    # ------------------------------------------------------------------ load
    def _toggle_details(self, force: bool | None = None):
        self._details_open = (not self._details_open) if force is None else force
        self.details.setVisible(self._details_open)
        self.btn_details.setText(("▾" if self._details_open else "▸") + "  Invoice details")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        narrow = self.width() < 520
        self.btn_export.setText("Export" if narrow else "Export for Claude")
        if self.btn_post.isEnabled():
            self.btn_post.setText(self._post_label())
        cols = 1 if self.width() < 470 else 2
        if getattr(self, "_cols", 2) != cols:
            self._cols = cols
            g = self.details.layout()
            for i, (key, _label) in enumerate(FIELDS):
                lab = self._labels[key]
                ed = self.edits[key]
                g.removeWidget(lab)
                g.removeWidget(ed)
                r, c = ((i // 2) * 2, i % 2) if cols == 2 else (i * 2, 0)
                g.addWidget(lab, r, c)
                g.addWidget(ed, r + 1, c)

    def _dirty(self, *_):
        self.btn_apply.setObjectName("primary")
        self.btn_apply.setStyle(self.btn_apply.style())

    def load(self, row, company, masters, verdict, suggestion):
        self.setEnabled(True)
        self._toggle_grid(False)
        self.row, self.company, self.masters = row, company, masters
        self.inv = assess_mod.invoice_of(row)
        vendor = self.st.session.scalar(select(Vendor).where(Vendor.company_id == company.id,
                                                             Vendor.vendor_key == rules.vendor_key(self.inv)))
        for w in (self.chk_rcm, self.chk_blocked, self.tds_combo):
            w.blockSignals(True)
        self.tds_combo.setCurrentIndex(max(0, self.tds_combo.findData(vendor.tds_section if vendor else "")))
        self.chk_rcm.setChecked(self.inv.reverse_charge or bool(vendor and vendor.rcm))
        self.chk_blocked.setChecked(False)
        for w in (self.chk_rcm, self.chk_blocked, self.tds_combo):
            w.blockSignals(False)
        self._fill_fields()
        self._render(verdict, suggestion)
        if row.id in self._style_choice:
            self._render_entry(style=self._style_choice[row.id])
        self._toggle_details(verdict.state == "blocked" or any(
            i["level"] == "error" for i in (row.validation or {}).get("issues", [])))
        posted = row.status == "posted"
        self._verdict_state = verdict.state
        self.btn_post.setEnabled(not posted)
        self.btn_post.setText("Posted ✓" if posted else self._post_label())
        self.conf_chip.setObjectName("chip")
        self.conf_chip.setText({"ready": "✓ All checks pass", "attention": "Needs a look",
                                "blocked": "Fix before posting"}.get(verdict.state, ""))
        tone(self.conf_chip, verdict.state)

    def _fill_fields(self):
        i = self.inv
        issues = {x["field"]: x["level"] for x in (self.row.validation or {}).get("issues", [])}
        for key, e in self.edits.items():
            v = getattr(i, key)
            if key == "invoice_date":
                v = fmt_date(v)
            elif key in MONEY:
                v = f"{v:,.2f}" if v else ""
            e.setText(str(v))
            conf = i.field_confidence.get(key)
            state = "error" if issues.get(key) == "error" else "warn" if issues.get(key) == "warn" or \
                (conf is not None and conf < 0.8) else "ok"
            e.setProperty("state", state)
            e.style().unpolish(e)
            e.style().polish(e)
            e.setToolTip(f"Confidence {conf:.0%}" if conf is not None else "")
        self.btn_apply.setObjectName("")
        self.btn_apply.setStyle(self.btn_apply.style())

    def _render(self, verdict, sug):
        i = self.inv
        self.s_name.setText(i.supplier_name or Path(self.row.file_path).name)
        meta = [x for x in (i.supplier_gstin, f"Inv {i.invoice_no}" if i.invoice_no else "",
                            fmt_date(i.invoice_date)) if x]
        self.s_meta.setText("  ·  ".join(meta))
        self.s_total.setText(fmt_money(i.grand_total) if i.grand_total else "—")
        tax = [f"Taxable {fmt_money(i.taxable_total)}"] if i.taxable_total else []
        for k, lbl in (("cgst_total", "CGST"), ("sgst_total", "SGST"), ("igst_total", "IGST")):
            if getattr(i, k):
                tax.append(f"{lbl} {fmt_money(getattr(i, k))}")
        self.s_tax.setText("   ".join(tax))
        old = self.s_state
        self.s_state = chip(verdict.reason, verdict.state)
        old.parentWidget().layout().replaceWidget(old, self.s_state)
        old.deleteLater()

        while self.issue_box.count():
            w = self.issue_box.takeAt(0).widget()
            if w:
                w.deleteLater()
        msgs = [(x["level"], x["message"]) for x in (self.row.validation or {}).get("issues", [])]
        if sug:
            msgs += [("error" if f.startswith("DUPLICATE?") else "info", f) for f in sug.flags]
            if sug.tds_note:
                msgs.append(("info", "TDS: " + sug.tds_note))
        for level, msg in msgs[:6]:
            state = {"error": "red", "warn": "amber"}.get(level, "info")
            fr = QFrame(objectName="issue")
            fr.setProperty("tone", state)
            hl = QHBoxLayout(fr)
            hl.setContentsMargins(10, 7, 10, 7)
            icon = {"error": "⛔", "warn": "⚠", "info": "ℹ"}.get(level, "ℹ")
            lab = QLabel(f"{icon}  {msg}", wordWrap=True)
            lab.setProperty("tone", {"red": "err", "amber": "warn"}.get(state, "info"))
            hl.addWidget(lab)
            self.issue_box.addWidget(fr)

        self._render_entry(sug)

    def _render_entry(self, sug=None, style: str = ""):
        if sug is None:
            sug = rules.suggest(self.st.session, self.company, self.masters, self.inv, style_override=style)
        v = sug.voucher
        if self.chk_blocked.isChecked():
            rules.apply_blocked_credit(v)
        self.voucher = v
        m = self.masters
        vtypes = sorted(n for n, d in m.voucher_types.items() if d.get("_parent", n) in (v.base_type, n))
        self.vtype.clear()
        self.vtype.addItems(vtypes or [v.vtype])
        self.vtype.setCurrentText(v.vtype)
        self.date_edit.setText(fmt_date(v.date))
        party = next((l for l in v.lines if l.kind == "party"), None)
        self.credit_days.setValue(party.credit_days if party else 0)
        self.narration.setText(v.narration)
        self.narration.setCursorPosition(0)
        self.grid.set_voucher(v, sorted(m.ledgers))
        self._sync_quick(v)
        style = "journal" if v.base_type == "Journal" else ("purchase_item" if v.inventory else "purchase_accounting")
        self.book_as.blockSignals(True)
        self.book_as.setCurrentIndex(max(0, self.book_as.findData(style)))
        self.book_as.blockSignals(False)
        party = next((l for l in v.lines if l.kind == "party"), None)
        missing = party is not None and (not party.ledger or party.ledger not in m.ledgers)
        self.party_banner.setVisible(missing)
        if missing:
            who = self.inv.supplier_name or self.inv.supplier_gstin or "this supplier"
            self.party_lbl.setText(f"{who} isn't in Tally yet." + (f" Closest match: {party.ledger}."
                                                                    if party.ledger else ""))
            tone(self.party_lbl, "warn")
        self._render_party()

    # ------------------------------------------------------------------ simple form <-> grid
    HEAD_KINDS = ("expense", "purchase")

    def _rows_of(self, kinds) -> list[int]:
        return [r for r, meta in enumerate(self.grid._meta) if meta.kind in kinds]

    def _set_row_ledger(self, r: int, name: str):
        w = self.grid.table.cellWidget(r, 0)
        if w and w.currentText() != name:
            w.setCurrentText(name)

    def _sync_quick(self, v=None):
        """Fill the simple form and the 'added automatically' labels from the grid."""
        m = self.masters
        names = sorted(m.ledgers)
        lines = self.grid.lines()
        party_rows, head_rows = self._rows_of(("party",)), self._rows_of(self.HEAD_KINDS)
        for combo, rows in ((self.q_party, party_rows), (self.q_head, head_rows)):
            combo.blockSignals(True)
            combo.clear()
            combo.addItems([""] + names)
            combo.setCurrentText(lines[rows[0]].ledger if rows else "")
            combo.lineEdit().setCursorPosition(0)
            combo.blockSignals(False)
        multi = len({lines[r].ledger for r in head_rows}) > 1 or bool(v and v.inventory)
        self.q_head.setEnabled(bool(head_rows) and not multi)
        self.q_head_note.setText(("Several heads / stock items - open the entry to change them" if multi else
                                  "No expense line - open the entry" if not head_rows else ""))
        self.q_head_note.setVisible(bool(self.q_head_note.text()))
        for combo, rows in ((self.q_party, party_rows), (self.q_head, head_rows)):
            conf = lines[rows[0]].confidence if rows else "red"
            tone(combo, conf if conf in ("green", "amber") else "red", "conf")
            combo.setToolTip(lines[rows[0]].note if rows else "")
        # automatic lines as labels
        while self.auto_row.count():
            it = self.auto_row.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        auto = [l for l in lines if l.kind not in ("party",) + self.HEAD_KINDS]
        labels = {"gst_in": "", "gst_rcm_in": "RCM input ", "gst_rcm_out": "RCM liability ", "tds": "TDS ",
                  "tcs": "TCS ", "round": "Round off "}
        for l in auto:
            txt = (labels.get(l.kind, "") + (l.note.split(" - ")[0] if l.kind == "gst_in" else "")).strip() \
                or l.ledger or l.note
            b = QPushButton(f"{txt}  ₹{l.amount:,.2f}", objectName="autochip")
            b.setProperty("tone", (l.confidence if l.confidence in ("green", "amber") else "red") if l.ledger
                          else "red")
            b.setToolTip(f"{l.ledger or 'no ledger yet'}  ·  {'Dr' if l.dr else 'Cr'}\n{l.note}\nClick to edit")
            b.clicked.connect(lambda: self._toggle_grid(True))
            self.auto_row.addWidget(b)
        if not auto:
            self.auto_row.addWidget(QLabel("Nothing - only supplier and expense", objectName="muted"))
        self.auto_row.addStretch(1)
        total = sum((l.amount for l in lines if l.dr), Decimal(0))
        self.q_total.setText(f"₹ {total:,.2f}")
        need_grid = multi or any(not l.ledger or l.ledger not in m.ledgers for l in auto)
        if need_grid and not self.grid.isVisible():
            self._toggle_grid(True)

    def _toggle_grid(self, force: bool | None = None):
        on = (not self.grid.isVisible()) if force is None else force
        self.grid.setVisible(on)
        self.btn_grid.setText(("▾" if on else "▸") + "  " + ("Hide entry (Dr / Cr)" if on else "Show entry (Dr / Cr)"))

    def _quick_party(self, name: str):
        for r in self._rows_of(("party",)):
            self._set_row_ledger(r, name.strip())

    def _quick_head(self, name: str):
        for r in self._rows_of(self.HEAD_KINDS):
            self._set_row_ledger(r, name.strip())

    def _grid_changed(self):
        if getattr(self, "_syncing", False) or not self.masters:
            return
        lines = self.grid.lines()
        pr, hr = self._rows_of(("party",)), self._rows_of(self.HEAD_KINDS)
        self._syncing = True
        try:
            for combo, rows in ((self.q_party, pr), (self.q_head, hr)):
                if rows and combo.currentText() != lines[rows[0]].ledger:
                    combo.blockSignals(True)
                    combo.setCurrentText(lines[rows[0]].ledger)
                    combo.blockSignals(False)
            self.q_total.setText(f"₹ {sum((l.amount for l in lines if l.dr), Decimal(0)):,.2f}")
        finally:
            self._syncing = False

    # ------------------------------------------------------------------ supplier card
    def _party_ledger(self) -> str:
        p = next((l for l in (self.voucher.lines if self.voucher else []) if l.kind == "party"), None)
        return p.ledger if p and p.ledger in self.masters.ledgers else ""

    def _render_party(self):
        while self.recent_box.count():
            w = self.recent_box.takeAt(0).widget()
            if w:
                w.deleteLater()
        party = self._party_ledger()
        self._card_party = party
        if not party:
            self.bal_lbl.setText("")
            self.party_sub.setText("Supplier not matched to a Tally ledger yet.")
            return
        grp = self.masters.ledgers.get(party, {}).get("_group", "")
        self.party_sub.setText(f"{party}" + (f"  ·  {grp}" if grp else ""))
        self._load_balance()
        p = getattr(self, "period", None)
        rec = [pe for pe in party_mod.recent_entries(self.st.session, self.company.id, party, limit=40)
               if not p or p.contains(pe.vh.date)][:5]
        if not rec:
            self.recent_box.addWidget(QLabel("No entries for this supplier in the synced period.", objectName="muted"))
            return
        for pe in rec:
            row = QFrame(objectName="issue")
            row.setStyleSheet(f"QFrame#issue {{ background: {theme.SUBTLE}; }}")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(8, 4, 8, 4)
            v = pe.vh
            txt = QLabel(f"<b>{pe.label}</b>  {v.voucher_type} {v.number}  ·  "
                         f"{fmt_money(pe.amount)} {'Dr' if pe.party_dr else 'Cr'}")
            narr = (v.narration or "").strip()
            lines_tip = "\n".join(f"{'Dr' if e['dr'] else 'Cr'}  {e['ledger']}  {Decimal(e['amount']):,.2f}"
                                  for e in v.entries or [])
            txt.setToolTip((narr + "\n\n" if narr else "") + lines_tip)
            rl.addWidget(txt, 1)
            if not pe.party_dr:                       # an expense/purchase entry: worth copying
                b = QPushButton("Copy")
                b.setToolTip("Use the same ledgers and voucher type for this invoice")
                b.clicked.connect(lambda _=False, vh=v: self.copy_from(vh))
                rl.addWidget(b)
            self.recent_box.addWidget(row)

    def _load_balance(self, force: bool = False):
        party = getattr(self, "_card_party", "")
        if not party or not self.company:
            return
        hit = _BAL_CACHE.get((self.company.id, party, min(date.today(), getattr(self, "period", None).end)
                              if getattr(self, "period", None) else date.today()))
        if hit and not force and _time.time() - hit[0] < 120:
            self.bal_lbl.setText(hit[1])
            return
        self.bal_lbl.setText("…")
        client, cname = self.st.client(self.company), self.company.name
        from ..engine.periods import fy_start
        p = getattr(self, "period", None)
        today = min(date.today(), p.end) if p else date.today()
        fy = fy_start(today)
        key = (self.company.id, party, today)

        def job(_p):
            return client.ledger_balance(cname, party, fy.strftime("%Y%m%d"), today.strftime("%Y%m%d"))

        def done(res):
            if getattr(self, "_card_party", "") != party:
                return                                   # user moved to another invoice
            if res is None:
                self.bal_lbl.setText("not found in Tally")
                return
            text = party_mod.fmt_balance(res["closing"])
            _BAL_CACHE[key] = (_time.time(), text)
            self.bal_lbl.setText(text)
            self.bal_lbl.setToolTip(f"Live from Tally as on {today:%d-%m-%Y} "
                                    f"(opening {party_mod.fmt_balance(res['opening'])})")

        def fail(_msg):
            if getattr(self, "_card_party", "") != party:
                return
            net = party_mod.balance_from_history(self.st.session, self.company.id, party)
            self.bal_lbl.setText("Tally offline")
            self.bal_lbl.setToolTip(f"Couldn't reach Tally. Movement in synced entries: "
                                    f"{fmt_money(abs(net))} {'Dr' if net > 0 else 'Cr'} (excludes opening)")

        run_bg(self, job, done, fail)

    def copy_from(self, vh):
        party = self._party_ledger()
        v = party_mod.copy_entry(vh, self.inv, self.masters, party)
        sug = rules.Suggestion(v, None, None, [f"Copied from {vh.voucher_type} {vh.number} dated "
                                               f"{vh.date[6:8]}-{vh.date[4:6]}-{vh.date[:4]} - check the amounts"])
        self._style_choice[self.row.id] = "journal" if v.base_type == "Journal" else "purchase_accounting"
        self._render_entry(sug)
        self.st.window.toast(f"Copied {vh.voucher_type} {vh.number}: same ledgers, this invoice's amounts")

    def _book_as_changed(self, *_):
        if self.inv is not None:
            self._style_choice[self.row.id] = self.book_as.currentData()
            self._render_entry(style=self.book_as.currentData())

    def _groups(self) -> list[str]:
        from ..db.models import MasterCache
        return [r.name for r in self.st.session.scalars(select(MasterCache).where(
            MasterCache.company_id == self.company.id, MasterCache.kind == "group"))]

    def create_supplier(self):
        dlg = LedgerDialog(self.st, self.company, self._groups(), name=self.inv.supplier_name,
                           parent_group="Sundry Creditors", gstin=self.inv.supplier_gstin,
                           vendor_key=rules.vendor_key(self.inv), parent=self)
        if dlg.exec() and dlg.created_name:
            self._after_ledger_created(dlg.created_name)

    def create_ledger(self):
        if not self.company:
            return
        dlg = LedgerDialog(self.st, self.company, self._groups(), parent_group="Indirect Expenses", parent=self)
        if dlg.exec() and dlg.created_name:
            self._after_ledger_created(dlg.created_name)

    def _after_ledger_created(self, name: str):
        self.masters = self.st.masters(self.company)
        self.st.window.toast(f"✓ Ledger '{name}' created in Tally")
        self._render_entry(style=self.book_as.currentData())
        self.changed.emit()

    # ------------------------------------------------------------------ edits
    def _read_fields(self):
        i = self.inv
        for key, e in self.edits.items():
            t = e.text().strip()
            if key in MONEY:
                setattr(i, key, dec(t))
            elif key == "invoice_date":
                i.invoice_date = parse_date(t) or i.invoice_date
            elif key == "supplier_gstin":
                i.supplier_gstin = t.upper().replace(" ", "")
                i.supplier_pan = i.supplier_gstin[2:12] if len(i.supplier_gstin) == 15 else i.supplier_pan
            else:
                setattr(i, key, t)
            if t:
                i.field_confidence[key] = max(i.field_confidence.get(key, 0), 0.95)
        i.reverse_charge = self.chk_rcm.isChecked()
        tax = i.igst_total + i.cgst_total + i.sgst_total
        if i.taxable_total and tax and len(i.taxes) <= 1:
            rate = (tax * 100 / i.taxable_total).quantize(Decimal("0.01"))
            nearest = min([Decimal(x) for x in ("0.1", "0.25", "3", "5", "12", "18", "28", "40")],
                          key=lambda r: abs(r - rate))
            i.taxes = [TaxRow(nearest if abs(nearest - rate) < Decimal("0.3") else rate, i.taxable_total,
                              i.igst_total, i.cgst_total, i.sgst_total, i.cess_total)]

    def apply_changes(self):
        self._read_fields()
        s = self.st.session
        section = self.tds_combo.currentData()
        vkey = rules.vendor_key(self.inv)
        vendor = s.scalar(select(Vendor).where(Vendor.company_id == self.company.id, Vendor.vendor_key == vkey))
        if (section or self.chk_rcm.isChecked()) and vendor is None:
            vendor = Vendor(company_id=self.company.id, vendor_key=vkey, gstin=self.inv.supplier_gstin,
                            pan=self.inv.supplier_pan, names=[self.inv.supplier_name])
            s.add(vendor)
        if vendor is not None:
            vendor.tds_section = section
            vendor.rcm = self.chk_rcm.isChecked()
        val = validate(self.inv, self.company.gstin, state_code(self.company.state))
        self.row.extraction = {**(self.row.extraction or {}), **self.inv.to_json()}
        self.row.validation = val.to_json()
        s.commit()
        self.changed.emit()

    def current_voucher(self) -> Voucher:
        v = self.voucher
        lines = self.grid.lines()
        for l in lines:
            if l.kind == "party":
                l.credit_days = self.credit_days.value()
        party = next((l.ledger for l in lines if l.kind == "party"), v.party)
        return Voucher(vtype=self.vtype.currentText().strip() or v.vtype, base_type=v.base_type,
                       date=parse_date(self.date_edit.text()) or v.date, lines=lines, inventory=list(v.inventory),
                       reference=self.inv.invoice_no, reference_date=self.inv.invoice_date, party=party,
                       narration=self.narration.text().strip())

    # ------------------------------------------------------------------ actions
    def preview_xml(self):
        if not self.voucher:
            return
        v = self.current_voucher()
        probs = v.problems(set(self.masters.ledgers), set(self.masters.stock_items))
        dlg = QDialog(self)
        dlg.setWindowTitle("XML that will be sent to Tally")
        dlg.resize(900, 600)
        lay = QVBoxLayout(dlg)
        if probs:
            lb = QLabel("• " + "\n• ".join(probs))
            lb.setStyleSheet(f"color: {theme.ERR_FG};")
            lay.addWidget(lb)
        t = QPlainTextEdit(readOnly=True)
        t.setFont(QFont("Consolas", 9))
        t.setPlainText(to_xml(v).replace("><", ">\n<"))
        lay.addWidget(t)
        dlg.exec()

    def post(self, override: str = ""):
        if not self.row or self.row.status == "posted" or (not self.btn_post.isEnabled() and not override):
            return
        v = self.current_voucher()
        probs = v.problems(set(self.masters.ledgers), set(self.masters.stock_items))
        if probs:
            QMessageBox.warning(self, "Not ready to post", "• " + "\n• ".join(probs))
            return
        errs = [x["message"] for x in (self.row.validation or {}).get("issues", []) if x["level"] == "error"]
        if errs and QMessageBox.question(self, "Post with errors?", "This invoice still has errors:\n\n• " +
                                         "\n• ".join(errs[:4]) + "\n\nPost anyway?") != QMessageBox.StandardButton.Yes:
            return
        self.btn_post.setEnabled(False)
        self.btn_post.setText("Posting…")
        rid, cid, inv, remember = self.row.id, self.company.id, self.inv, self.chk_remember.isChecked()
        self.row.extraction = {**(self.row.extraction or {}), **inv.to_json()}
        self.st.session.commit()
        self._override = override
        run_bg(self, lambda _p: post_one(self.st, rid, cid, inv, v, remember, override), self._posted,
               self._post_failed)

    def _post_label(self) -> str:
        green = getattr(self, "_verdict_state", "") == "ready"
        narrow = self.width() < 520
        if green:
            return "Accept && post  Ctrl+A" if narrow else "Accept && post   Ctrl+A"
        return "Post  Ctrl+A" if narrow else "Post to Tally   Ctrl+A"

    def _posted(self, res):
        if getattr(res, "locked", False):
            self.btn_post.setEnabled(True)
            self.btn_post.setText(self._post_label())
            reason = ask_lock_reason(self, res.message)
            if reason:
                self.post(reason)
            return
        if res.ok:
            self.st.window.toast(f"✓ Posted: {res.message}")
            self.posted.emit(self.row.id)
        else:
            self.btn_post.setEnabled(True)
            self.btn_post.setText(self._post_label())
            QMessageBox.warning(self, "Tally didn't accept it", res.message)

    def _post_failed(self, msg):
        self.btn_post.setEnabled(True)
        self.btn_post.setText(self._post_label())
        QMessageBox.warning(self, "Posting failed", msg)

    def set_aside(self):
        if not self.row or self.row.status == "posted":
            return
        self.row.status = "exception"
        try:
            intake.move_after(self.row, "Exceptions")
        except OSError:
            pass
        self.st.session.commit()
        self.st.changed(self.row.company_id)
        self.posted.emit(self.row.id)

    def export_debug(self):
        if not self.row:
            return
        from ..extract.debug_bundle import export
        from ..config import desktop_dir
        out_dir = desktop_dir() / "AccountingAssistant_debug"
        p = export(self.row, self.company, out_dir)
        QMessageBox.information(self, "Exported", f"Saved to:\n{p}\n\nNames, GSTINs, PAN, bank details, phone "
                                "numbers and PIN codes are masked; amounts and layout are kept. Open the file and "
                                "check it before sending. Fill in the correct values section if you can.")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(out_dir)))


def post_one(st, rid: str, cid: str, inv, v: Voucher, remember: bool = True, override: str = ""):
    s = st.Local()
    try:
        row, comp = s.get(InvoiceRow, rid), s.get(Company, cid)
        res = st.post(s, comp, v, row, override)
        if res.ok:
            rules.learn(s, comp, inv, v, st.actor, save_rule=remember)
            try:                                       # learn this supplier's layout for offline reading
                from ..engine import layouts
                layouts.learn(s, comp.id, rules.vendor_key(inv), inv, (row.extraction or {}).get("_text", ""),
                              offline_ok=row.extraction_source == "layout")
            except Exception:
                pass
            try:
                intake.move_after(row, "Posted")
            except OSError as e:
                res.message += f" (file not moved: {e})"
            s.commit()
        return res
    finally:
        s.close()


# ====================================================================== page
class Workbench(QWidget):
    def __init__(self, st):
        super().__init__(objectName="page")
        self.st = st
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        self.split = split
        self.queue = QueuePanel()
        self.preview = PreviewPanel()
        self.entry = EntryPanel(st)
        mid = QWidget()
        ml = QVBoxLayout(mid)
        ml.setContentsMargins(6, 14, 6, 14)
        ml.addWidget(self.preview)
        split.addWidget(self.queue)
        split.addWidget(mid)
        split.addWidget(self.entry)
        split.setSizes([280, 480, 560])
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 1)
        split.setCollapsible(1, True)            # the document pane can be dragged shut on small screens
        mid.setMinimumWidth(260)
        lay.addWidget(split)
        self.entry.btn_doc.clicked.connect(self.toggle_document)
        self._narrow = None
        self.queue.selected.connect(self.open)
        self.queue.period.changed.connect(lambda *_: self.refresh())
        self.queue.post_ready.connect(self.post_all_ready)
        self.entry.posted.connect(self._after_post)
        self.entry.changed.connect(lambda: self.refresh(self.entry.row.id if self.entry.row else None))
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.entry.post)
        QShortcut(QKeySequence("Ctrl+A"), self, activated=self.entry.post)
        QShortcut(QKeySequence("Alt+C"), self, activated=lambda: self.entry.create_ledger())
        QShortcut(QKeySequence("Ctrl+E"), self, activated=self.entry.set_aside)
        QShortcut(QKeySequence("Alt+Down"), self, activated=lambda: self.queue.step(1))
        QShortcut(QKeySequence("Alt+Up"), self, activated=lambda: self.queue.step(-1))
        st.on_company_change(lambda: self.refresh())
        self._by_id = {}

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w = self.width()
        narrow = w < 1150
        if narrow != self._narrow:
            self._narrow = narrow
            q = 250 if narrow else 290
            if narrow:                      # small screen: queue + entry; document on demand
                self.split.setSizes([q, 0, w - q])
            else:
                self.split.setSizes([q, int((w - q) * 0.46), int((w - q) * 0.54)])
            self.entry.btn_doc.setVisible(narrow)
        self._sync_doc_button()

    def toggle_document(self):
        w = self.width()
        sz = self.split.sizes()
        if sz[1] == 0:
            self.split.setSizes([sz[0], int((w - sz[0]) * 0.5), int((w - sz[0]) * 0.5)])
        else:
            self.split.setSizes([sz[0], 0, sz[1] + sz[2]])
        self._sync_doc_button()

    def _sync_doc_button(self):
        self.entry.btn_doc.setText("Hide document" if self.split.sizes()[1] > 0 else "Show document")

    def refresh(self, keep_id: str | None = None):
        c = self.st.company()
        if not c:
            self.queue.set_items([])
            return
        s = self.st.session
        s.expire_all()
        self.masters = self.st.masters(c)
        p = self.queue.period.period()
        self.entry.period = p
        rows = [r for r in s.scalars(select(InvoiceRow).where(InvoiceRow.company_id == c.id))
                if not (r.extraction or {}).get("invoice_date") or p.contains((r.extraction or {})["invoice_date"])]
        items = []
        # an invoice is only re-assessed when it, the masters, the rules or the Tally history changed
        from sqlalchemy import func
        from ..db.models import MappingRule, Vendor
        from ..engine import history as hist_mod
        ctx = (id(self.masters), hist_mod.stamp(s, c.id),
               tuple(s.execute(select(func.count(), func.max(MappingRule.updated_at))
                               .where(MappingRule.company_id == c.id)).one()),
               tuple(s.execute(select(func.count(), func.max(Vendor.updated_at))
                               .where(Vendor.company_id == c.id)).one()))
        cache = self.__dict__.setdefault("_assess_cache", {})
        if cache.get("_ctx") != ctx:
            cache.clear()
            cache["_ctx"] = ctx
        for r in rows:
            key = (r.id, r.updated_at, r.status)
            hit = cache.get(key)
            if hit is None:
                try:
                    hit = assess_mod.assess(s, c, self.masters, r)
                except Exception as e:
                    hit = (assess_mod.Verdict("blocked", "Error", str(e)), None)
                cache[key] = hit
            items.append((r, hit[0], hit[1]))
        items.sort(key=lambda x: (assess_mod.ORDER[x[1].state], -(x[0].updated_at.timestamp())))
        self._by_id = {r.id: (r, v, sg) for r, v, sg in items}
        self.queue.set_items(items, keep_id or (self.entry.row.id if self.entry.row else None))
        if not self.queue.visible_ids():
            self.entry.setEnabled(False)

    def open(self, rid: str):
        if rid not in self._by_id:
            return
        r, v, sug = self._by_id[rid]
        self.preview.show_row(r)
        self.entry.load(r, self.st.company(), self.masters, v, sug)

    def _after_post(self, rid: str):
        ids = self.queue.visible_ids()
        nxt = None
        if rid in ids:
            i = ids.index(rid)
            rest = ids[i + 1:] + ids[:i]
            nxt = rest[0] if rest else None
        self.refresh(nxt)

    # ------------------------------------------------------------------ batch actions
    def read_new(self, on_progress, on_done):
        c = self.st.company()
        folder = (c.settings or {}).get("folder", "") if c else ""
        if not c or not folder or not Path(folder).is_dir():
            on_done(None)
            QMessageBox.information(self, "Invoice folder", "Set this company's invoice folder first "
                                    "(Setup → Companies → Settings).")
            return
        cid, opt, workers = c.id, self.st.extract_options(c), max(1, self.st.settings.gemini_parallel)

        def job(progress):
            s = self.st.Local()
            comp = s.get(Company, cid)
            files = intake.new_files(s, comp, Path(folder))
            progress(f"{len(files)} new file(s)")
            done = 0
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futs = {ex.submit(_safe_process, p, opt): (p, h) for p, h in files}
                for f in as_completed(futs):
                    p, h = futs[f]
                    intake.store(s, comp, p, h, f.result())
                    done += 1
                    progress(f"Read {done}/{len(files)}: {p.name}")
            s.close()
            return len(files)

        def done(n):
            on_done(n)
            self.refresh()

        run_bg(self, job, done, lambda m: (on_done(None), QMessageBox.warning(self, "Reading failed", m)),
               on_progress)

    def reread_current(self, on_progress, on_done):
        r = self.entry.row
        c = self.st.company()
        if not r or not c:
            return
        rid, opt = r.id, self.st.extract_options(c)

        def job(progress):
            s = self.st.Local()
            row = s.get(InvoiceRow, rid)
            progress(f"Re-reading {Path(row.file_path).name}")
            intake.reread(s, row, opt)
            s.close()
            return 1

        def done(n):
            on_done(n)
            self.refresh(rid)

        run_bg(self, job, done, lambda m: (on_done(None), QMessageBox.warning(self, "Re-read failed", m)),
               on_progress)

    def post_all_ready(self):
        ready = [(r, sg) for r, v, sg in self._by_id.values() if v.state == "ready" and sg]
        if not ready:
            return
        total = sum(Decimal(str((r.extraction or {}).get("grand_total", 0) or 0)) for r, _ in ready)
        if QMessageBox.question(self, "Post all ready", f"Post {len(ready)} invoice(s) to Tally, "
                                f"total {fmt_money(total)}?\n\nEach is checked again before posting.") \
                != QMessageBox.StandardButton.Yes:
            return
        cid = self.st.company().id
        jobs = [(r.id, assess_mod.invoice_of(r), sg.voucher) for r, sg in ready]
        self.queue.btn_post_ready.setEnabled(False)

        def job(progress):
            ok, failed = 0, []
            for k, (rid, inv, v) in enumerate(jobs, 1):
                progress(f"Posting {k}/{len(jobs)}")
                res = post_one(self.st, rid, cid, inv, v)
                if res.ok:
                    ok += 1
                else:
                    failed.append(f"{inv.supplier_name} {inv.invoice_no}: {res.message}")
            return ok, failed

        def done(res):
            ok, failed = res
            self.st.window.progress_done()
            self.refresh()
            msg = f"{ok} posted." + (("\n\nNot posted:\n• " + "\n• ".join(failed[:8])) if failed else "")
            (QMessageBox.information if not failed else QMessageBox.warning)(self, "Post all ready", msg)

        self.st.window.progress_start("Posting…")
        run_bg(self, job, done, lambda m: (self.st.window.progress_done(), QMessageBox.warning(self, "Posting", m)),
               self.st.window.progress_text)


def _safe_process(path, opt):
    try:
        return process(path, opt)
    except Exception as e:
        return e
