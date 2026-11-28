"""Invoice review window: document preview on the left, editable data on the right.

Colours: green = high confidence and no problem, amber = please verify,
red = missing / low confidence / validation error. Nothing is changed until Save.
"""
from __future__ import annotations

from ipt.core.timefmt import fmt

from decimal import Decimal

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QKeySequence, QPixmap, QShortcut, QTransform
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QFormLayout, QGroupBox,
                               QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QPushButton, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem,
                               QTabWidget, QVBoxLayout, QWidget)

from ipt.core.permissions import PermissionDenied, has_permission
from ipt.core.states import STATES
from ipt.services.invoice_service import DOC_TYPES, ITEM_FIELDS, InvoiceError

GREEN, AMBER, RED = "#dcfce7", "#fef3c7", "#fee2e2"
GROUPS = [
    ("Supplier", ["supplier_name", "supplier_gstin", "supplier_pan", "supplier_state_code", "supplier_address"]),
    ("Buyer", ["buyer_name", "buyer_gstin", "buyer_state_code"]),
    ("Invoice", ["doc_type", "invoice_no", "invoice_date", "place_of_supply", "reverse_charge", "po_no",
                 "original_invoice_ref", "eway_bill_no", "irn", "ack_no"]),
    ("Amounts (invoice currency)", ["taxable_total", "cgst", "sgst", "igst", "cess", "freight", "packing",
                                    "other_charges", "round_off", "tds", "tcs", "invoice_total", "amount_in_words"]),
    ("Foreign currency", ["currency", "exchange_rate"]),
]
LABELS = {"supplier_gstin": "Supplier GSTIN", "supplier_pan": "Supplier PAN", "supplier_state_code": "Supplier state",
          "buyer_gstin": "Buyer GSTIN", "buyer_state_code": "Buyer state", "doc_type": "Document type",
          "invoice_no": "Invoice no.", "po_no": "PO no.", "eway_bill_no": "E-way bill no.", "irn": "IRN",
          "ack_no": "Ack no.", "cgst": "CGST", "sgst": "SGST / UTGST", "igst": "IGST", "tds": "TDS", "tcs": "TCS",
          "original_invoice_ref": "Original invoice ref.", "exchange_rate": "Exchange rate (INR per unit)"}
ITEM_HEADERS = ["Description", "HSN/SAC", "Qty", "Unit", "Rate", "Discount", "Taxable", "GST %", "CGST", "SGST",
                "IGST", "Cess", "Total"]


def _label(name: str) -> str:
    return LABELS.get(name, name.replace("_", " ").capitalize())


def _fmt(v) -> str:
    if v is None:
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%d-%m-%Y")
    return str(v)


class _ClickImage(QLabel):
    clicked = Signal(float, float, bool)          # fraction of width, of height, shift held

    def mousePressEvent(self, e):
        pm = self.pixmap()
        if pm is not None and not pm.isNull() and e.button() == Qt.LeftButton:
            off_x = max(0, (self.width() - pm.width()) / 2)
            u = (e.position().x() - off_x) / pm.width()
            v = e.position().y() / pm.height()
            if 0 <= u <= 1 and 0 <= v <= 1:
                self.clicked.emit(u, v, bool(e.modifiers() & Qt.ShiftModifier))
        super().mousePressEvent(e)


class PreviewPane(QWidget):
    """Renders document pages with PyMuPDF (PDF) or Qt (images); zoom, rotate, page navigation.
    A click on the page emits picked(page, fx, fy, whole_line) in un-rotated page fractions."""
    picked = Signal(int, float, float, bool)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path, self.page, self.zoom, self.rotation = path, 0, 1.0, 0
        self.pages = 1
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.lbl = QLabel()
        for text, fn in (("◀", lambda: self._go(-1)), ("▶", lambda: self._go(1)), ("−", lambda: self._zoom(0.8)),
                         ("+", lambda: self._zoom(1.25)), ("⟳", self._rotate)):
            b = QPushButton(text)
            b.setFixedWidth(36)
            b.clicked.connect(fn)
            bar.addWidget(b)
        bar.addWidget(self.lbl)
        bar.addStretch(1)
        lay.addLayout(bar)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.img = _ClickImage()
        self.img.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.img.setCursor(Qt.CrossCursor)
        self.img.clicked.connect(self._clicked)
        self.scroll.setWidget(self.img)
        lay.addWidget(self.scroll, 1)
        self._render()

    def _render(self):
        if self.path is None or not self.path.is_file():
            self.img.setText("Original document not found")
            self.img.adjustSize()
            return
        if self.path.suffix.lower() == ".pdf":
            import pymupdf
            with pymupdf.open(self.path) as doc:
                self.pages = doc.page_count
                pix = doc[self.page].get_pixmap(dpi=int(110 * self.zoom))
                qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
        else:
            qimg = QImage(str(self.path))
            if self.zoom != 1.0:
                qimg = qimg.scaledToWidth(int(qimg.width() * self.zoom), Qt.SmoothTransformation)
        pm = QPixmap.fromImage(qimg).transformed(QTransform().rotate(self.rotation))
        self.img.setPixmap(pm)
        self.img.adjustSize()
        self.lbl.setText(f"Page {self.page + 1} of {self.pages}")

    def _clicked(self, u, v, shift):
        fx, fy = {0: (u, v), 90: (v, 1 - u), 180: (1 - u, 1 - v), 270: (1 - v, u)}[self.rotation]
        self.picked.emit(self.page, fx, fy, shift)

    def _go(self, d):
        self.page = max(0, min(self.pages - 1, self.page + d))
        self._render()

    def _zoom(self, f):
        self.zoom = max(0.4, min(4.0, self.zoom * f))
        self._render()

    def _rotate(self):
        self.rotation = (self.rotation + 90) % 360
        self._render()


class InvoiceReviewDialog(QDialog):
    def __init__(self, services, invoice_ids: list[int], index: int, parent=None):
        super().__init__(parent)
        self.s, self.ids, self.index = services, invoice_ids, index
        self.setWindowTitle("Review invoice")
        self.resize(1400, 860)
        self.dirty = False
        self.inputs: dict[str, QWidget] = {}
        outer = QVBoxLayout(self)
        self.header = QLabel()
        self.header.setObjectName("PageTitle")
        outer.addWidget(self.header)
        self.split = QSplitter()
        outer.addWidget(self.split, 1)
        bar = QHBoxLayout()
        self.btn_prev = QPushButton("◀ Previous")
        self.btn_next = QPushButton("Next ▶")
        self.btn_save = QPushButton("Save  (Ctrl+S)")
        self.btn_save.setObjectName("Primary")
        self.btn_validate = QPushButton("Validate")
        self.btn_approve = QPushButton("Approve")
        self.btn_reject = QPushButton("Reject")
        self.btn_delete = QPushButton("Delete")
        self.btn_reopen = QPushButton("Re-open for editing")
        for b in (self.btn_prev, self.btn_next):
            bar.addWidget(b)
        bar.addStretch(1)
        for b in (self.btn_reopen, self.btn_save, self.btn_validate, self.btn_approve, self.btn_reject,
                  self.btn_delete):
            bar.addWidget(b)
        outer.addLayout(bar)
        self.btn_prev.clicked.connect(lambda: self._move(-1))
        self.btn_next.clicked.connect(lambda: self._move(1))
        self.btn_save.clicked.connect(self._save)
        self.btn_validate.clicked.connect(self._validate)
        self.btn_approve.clicked.connect(self._approve)
        self.btn_reject.clicked.connect(self._reject)
        self.btn_delete.clicked.connect(self._delete)
        self.btn_reopen.clicked.connect(self._reopen)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._save)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=lambda: self.btn_approve.isEnabled() and self._approve())
        QShortcut(QKeySequence("Alt+Right"), self, activated=lambda: self.btn_next.isEnabled() and self._move(1))
        QShortcut(QKeySequence("Alt+Left"), self, activated=lambda: self.btn_prev.isEnabled() and self._move(-1))
        self.btn_approve.setText("Approve  (Ctrl+Enter)")
        self.btn_next.setToolTip("Alt + →")
        self.btn_prev.setToolTip("Alt + ←")
        self._target = None                  # the field the next click on the bill fills
        from PySide6.QtWidgets import QApplication
        QApplication.instance().focusChanged.connect(self._focus_changed)
        self.tip = QLabel("Tip: click a field, then click its value on the bill – it is copied in "
                          "(Shift+click = the whole line). Check it before saving.")
        self.tip.setStyleSheet("color:#64748b")
        outer.insertWidget(1, self.tip)
        self._load()

    # ------------------------------------------------------------ build
    def _load(self):
        inv = self.s.invoices.get(self.ids[self.index])
        if inv is None:
            self.reject()
            return
        self.inv = inv
        self.conf = self.s.invoices.confidence(inv)
        self.findings = self.s.invoices.findings(inv.id)
        self.bad_fields = {f.field for f in self.findings if f.severity == "error"}
        self.warn_fields = {f.field for f in self.findings if f.severity == "warning"}
        doc = self.s.documents.get(inv.document_id) if inv.document_id else None
        path = self.s.documents.absolute_path(doc) if doc else None
        while self.split.count():
            self.split.widget(0).setParent(None)
        pane = PreviewPane(path)
        self._doc_path = path
        pane.picked.connect(self._pick_value)
        if inv.page_from and inv.page_from > 1:
            pane.page = inv.page_from - 1
            pane._render()
        self.split.addWidget(pane)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._summary_tab(), "Summary")
        self.tabs.addTab(self._items_tab(), "Items")
        self.tabs.addTab(self._validation_tab(), f"Validation ({len(self.findings)})")
        self.tabs.addTab(self._history_tab(), "History")
        self.split.addWidget(self.tabs)
        self.split.setSizes([620, 780])
        pages = f" · page {inv.page_from}" + (f"-{inv.page_to}" if inv.page_to != inv.page_from else "") \
            if inv.page_from else ""
        self.header.setText(f"{inv.supplier_name or 'Unknown supplier'} – {inv.invoice_no or 'no invoice no.'}{pages}"
                            f"   [{inv.status.replace('_', ' ')}]   ({self.index + 1} of {len(self.ids)})")
        role = self.s.ctx.user.role if self.s.ctx.user else None
        # approved (not yet in Tally) can be corrected by an approver; imported bills are locked
        editable = inv.status != "imported" and has_permission(role, "invoice.edit") and \
            (inv.status != "approved" or has_permission(role, "invoice.approve"))
        self.btn_save.setEnabled(editable)
        self.btn_approve.setEnabled(inv.status not in ("approved",) and has_permission(role, "invoice.approve"))
        self.btn_reject.setEnabled(inv.status != "rejected" and has_permission(role, "invoice.approve"))
        self.btn_delete.setEnabled(inv.status != "imported" and has_permission(role, "invoice.delete") and
                                   (inv.status != "approved" or has_permission(role, "invoice.approve")))
        self.btn_reopen.setVisible(inv.status in ("approved", "rejected"))
        self.btn_reopen.setEnabled(has_permission(role, "invoice.approve"))
        self.btn_prev.setEnabled(self.index > 0)
        self.btn_next.setEnabled(self.index < len(self.ids) - 1)
        for w in self.inputs.values():
            w.setEnabled(editable)
        self.items.setEditTriggers(QAbstractItemView.AllEditTriggers if editable else QAbstractItemView.NoEditTriggers)
        self.dirty = False

    def _colour(self, name: str) -> str:
        value = getattr(self.inv, name, None)
        c = self.conf.get(name)
        if name in self.bad_fields:
            return RED
        if value is None or value == "":
            if name in self.warn_fields:
                return AMBER
            return RED if name in ("supplier_gstin", "invoice_no", "invoice_date", "taxable_total",
                                   "invoice_total") else ""
        if name in self.warn_fields or (c is not None and c < 0.9):
            return RED if c is not None and c < 0.6 else AMBER
        return GREEN

    def _summary_tab(self):
        self.inputs = {}
        w = QWidget()
        lay = QVBoxLayout(w)
        legend = QLabel("<span style='background:#dcfce7'>&nbsp;green&nbsp;</span> read with high confidence · "
                        "<span style='background:#fef3c7'>&nbsp;amber&nbsp;</span> please verify · "
                        "<span style='background:#fee2e2'>&nbsp;red&nbsp;</span> missing or wrong. "
                        "Fields you edit are marked as verified.")
        legend.setWordWrap(True)
        lay.addWidget(legend)
        for title, names in GROUPS:
            box = QGroupBox(title)
            form = QFormLayout(box)
            for name in names:
                value = getattr(self.inv, name)
                if name == "doc_type":
                    ed = QComboBox()
                    ed.addItems([d for d in DOC_TYPES if d != "other"])     # 'other' cannot go to Tally
                    ed.setCurrentText(value if value in DOC_TYPES and value != "other" else "tax_invoice")
                    ed.currentTextChanged.connect(self._mark_dirty)
                elif name in ("place_of_supply", "supplier_state_code", "buyer_state_code"):
                    ed = QComboBox()
                    ed.addItem("", None)
                    for code, st in STATES.items():
                        ed.addItem(f"{code} - {st.name}", code)
                    ed.setCurrentIndex(max(0, ed.findData(value)))
                    ed.currentIndexChanged.connect(self._mark_dirty)
                elif name == "reverse_charge":
                    ed = QComboBox()
                    ed.addItems(["", "No", "Yes"])
                    ed.setCurrentText("" if value is None else ("Yes" if value else "No"))
                    ed.currentTextChanged.connect(self._mark_dirty)
                else:
                    ed = QLineEdit(_fmt(value))
                    if name == "invoice_date":
                        ed.setPlaceholderText("DD-MM-YYYY")
                    ed.textEdited.connect(self._mark_dirty)
                colour = self._colour(name)
                if colour:
                    ed.setStyleSheet(f"background:{colour}")
                c = self.conf.get(name)
                ed.setToolTip(f"Confidence: {int(c * 100)}%" if isinstance(c, (int, float)) else "Not read")
                if name == "supplier_name" and self.conf.get("supplier_name_source"):
                    ed.setToolTip(f"Taken from the {self.conf['supplier_name_source']} with the same GSTIN")
                if name == "supplier_gstin" and self.conf.get("supplier_gstin_source"):
                    ed.setToolTip(f"OCR could not read it; {self.conf['supplier_gstin_source']} - please verify")
                elif str(self.conf.get(f"{name}_source", "")).startswith("OCR and Claude"):
                    ed.setToolTip("OCR and Claude Code read different values - check this on the page "
                                  "(see Remarks)")
                elif str(self.conf.get(f"{name}_source", "")).startswith("Claude"):
                    ed.setToolTip("Read by Claude Code from the page image and checked by IPT - please verify")
                elif str(self.conf.get(f"{name}_source", "")).startswith("learned"):
                    ed.setToolTip("Read from where this supplier usually prints it (learned from approved bills)"
                                  " - please verify")
                self.inputs[name] = ed
                form.addRow(_label(name), ed)
            lay.addWidget(box)
        if (self.inv.currency or "INR") != "INR":
            lay.addWidget(QLabel(f"Invoice currency: {self.inv.currency}. Accounting value (INR) = amount × "
                                 f"exchange rate."))
        lay.addStretch(1)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(w)
        return sc

    def _items_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        c = self.conf.get("items")
        note = QLabel(f"Line items (read with {int(c * 100)}% confidence – please check)" if isinstance(c, float)
                      and c < 1 else "Line items")
        lay.addWidget(note)
        self.items = QTableWidget(0, len(ITEM_HEADERS))
        self.items.setHorizontalHeaderLabels(ITEM_HEADERS)
        self.items.verticalHeader().setVisible(True)
        for it in self.inv.items:
            self._add_item_row([_fmt(getattr(it, k)) for k in ITEM_FIELDS])
        self.items.resizeColumnsToContents()
        self.items.horizontalHeader().setStretchLastSection(True)
        self.items.itemChanged.connect(lambda *_: (self._mark_dirty(), self._update_totals()))
        lay.addWidget(self.items, 1)
        bar = QHBoxLayout()
        add = QPushButton("Add row")
        rem = QPushButton("Delete row")
        add.clicked.connect(lambda: (self._add_item_row([""] * len(ITEM_FIELDS)), self._mark_dirty()))
        rem.clicked.connect(self._delete_item_row)
        bar.addWidget(add)
        bar.addWidget(rem)
        bar.addStretch(1)
        self.totals = QLabel()
        bar.addWidget(self.totals)
        lay.addLayout(bar)
        self._update_totals()
        return w

    def _add_item_row(self, values):
        self.items.blockSignals(True)
        r = self.items.rowCount()
        self.items.insertRow(r)
        for c, v in enumerate(values):
            self.items.setItem(r, c, QTableWidgetItem(v))
        self.items.blockSignals(False)

    def _delete_item_row(self):
        r = self.items.currentRow()
        if r >= 0:
            self.items.removeRow(r)
            self._mark_dirty()
            self._update_totals()

    def _update_totals(self):
        tot = {"taxable": Decimal(0), "tax": Decimal(0)}
        for r in range(self.items.rowCount()):
            for key, cols in (("taxable", [6]), ("tax", [8, 9, 10, 11])):
                for c in cols:
                    it = self.items.item(r, c)
                    try:
                        tot[key] += Decimal((it.text() if it else "0").replace(",", "") or "0")
                    except ArithmeticError:
                        pass
        self.totals.setText(f"Items taxable: {tot['taxable']:.2f}   Items tax: {tot['tax']:.2f}")

    def _validation_tab(self):
        lst = QListWidget()
        if not self.findings:
            lst.addItem("No problems found.")
        for f in self.findings:
            icon = "⛔" if f.severity == "error" else "⚠"
            extra = f"  (expected {f.expected}, found {f.found})" if f.expected or f.found else ""
            item = QListWidgetItem(f"{icon} {f.message}{extra}")
            item.setData(Qt.UserRole, f.field)
            lst.addItem(item)
        for msg in self._tally_readiness():
            item = QListWidgetItem(f"🔗 Tally import: {msg}")
            item.setData(Qt.UserRole, "items")
            lst.addItem(item)
        lst.itemDoubleClicked.connect(self._focus_field)
        return lst

    def _tally_readiness(self) -> list[str]:
        """What would stop this bill at Tally import (party / items / ledgers not mapped) - shown during review so
        it is fixed before approval, not discovered at import time. Only when the company is linked to Tally and
        its masters are synced."""
        try:
            c = self.s.companies.get_company(self.inv.company_id)
            if not c or not c.tally_company_name or not self.s.tally.masters("ledger"):
                return []
            built = self.s.vouchers.build(self.inv.id, "auto")
        except Exception:  # noqa: BLE001 - a preview problem must never block the review
            return []
        skip = ("not approved", "is missing", "quantity and taxable value", "no Tally stock item",
                "Items add up", "differs from taxable")          # already listed by the checks above
        return [b for b in built.blockers if not any(k in b for k in skip)]

    AMOUNT_FIELDS = {"taxable_total", "cgst", "sgst", "igst", "cess", "freight", "packing", "other_charges",
                     "round_off", "tds", "tcs", "invoice_total", "exchange_rate"}

    def _focus_changed(self, _old, new):
        if new is None:
            return
        if new is getattr(self, "items", None) or (new.parent() is not None and
                                                   new.parent() is getattr(self, "items", None)):
            self._target = "items"
            return
        for name, w in self.inputs.items():
            if w is new and isinstance(w, QLineEdit):
                self._target = name
                return

    def _pick_value(self, page, fx, fy, whole_line):
        if self._target is None:
            self.tip.setText("Click a field first (e.g. Invoice no.), then click its value on the bill.")
            return
        from PySide6.QtWidgets import QApplication
        from ipt.services.extraction.pick import text_at
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            raw = text_at(self._doc_path, page, fx, fy, whole_line) if self._doc_path else ""
        except Exception as e:  # noqa: BLE001 - reading must never crash the review
            raw = ""
            self.tip.setText(f"Could not read that spot: {e}")
        finally:
            QApplication.restoreOverrideCursor()
        if not raw:
            self.tip.setText("Nothing could be read at that spot – zoom in (+) and click on the text, or type it.")
            return
        value = self._clean_pick(self._target, raw)
        if self._target == "items":
            it = self.items.currentItem()
            if it is None:
                self.tip.setText("Select the item cell first, then click its value on the bill.")
                return
            it.setText(value)
            self._mark_dirty()
        else:
            w = self.inputs[self._target]
            if not w.isEnabled():
                return
            w.setText(value)
            w.setStyleSheet("background:#e0f2fe")          # picked by the user - shown as their entry
            self._mark_dirty()
        self.tip.setText(f"Copied '{value}' – check it against the bill before saving.")

    def _clean_pick(self, field: str, raw: str) -> str:
        import re
        t = raw.strip()
        if field in self.AMOUNT_FIELDS or (field == "items" and re.search(r"\d", t) and not re.search(r"[A-Za-z]{3}", t)):
            m = re.search(r"-?\d[\d,]*(?:\.\d+)?", t.replace("₹", ""))
            return m.group(0) if m else t
        if field == "invoice_date":
            from ipt.core.textnorm import parse_date
            d = parse_date(t)
            return d.strftime("%d-%m-%Y") if d else t
        if field in ("supplier_gstin", "buyer_gstin"):
            return re.sub(r"[^0-9A-Z]", "", t.upper())
        if field == "invoice_no":
            return t.strip(".,:;")
        return t

    def _focus_field(self, item):
        name = item.data(Qt.UserRole)
        if name == "items":
            self.tabs.setCurrentIndex(1)
        elif name in self.inputs:
            self.tabs.setCurrentIndex(0)
            self.inputs[name].setFocus()

    def _history_tab(self):
        lst = QListWidget()
        rows = [r for r in self.s.audit.recent(2000) if r.entity == "invoice" and r.entity_id == str(self.inv.id)]
        for r in rows:
            lst.addItem(f"{fmt(r.at)}  {r.username}  {r.action}  {r.remark}")
        if not rows:
            lst.addItem("No history yet")
        return lst

    # ------------------------------------------------------------ actions
    def _mark_dirty(self, *_):
        self.dirty = True

    def _collect(self):
        header = {}
        for name, ed in self.inputs.items():
            if isinstance(ed, QComboBox):
                if name == "reverse_charge":
                    header[name] = {"": None, "Yes": True, "No": False}[ed.currentText()]
                elif name == "doc_type":
                    header[name] = ed.currentText()
                else:
                    header[name] = ed.currentData()
            else:
                header[name] = ed.text().strip()
        items = []
        for r in range(self.items.rowCount()):
            row = {k: (self.items.item(r, c).text().strip() if self.items.item(r, c) else "")
                   for c, k in enumerate(ITEM_FIELDS)}
            if any(row.values()):
                items.append(row)
        return header, items

    def _save(self) -> bool:
        if not self.btn_save.isEnabled():
            return False
        header, items = self._collect()
        was_approved = self.inv.status == "approved"
        try:
            status = self.s.invoices.update(self.inv.id, header, items)
        except (InvoiceError, PermissionDenied) as e:
            QMessageBox.warning(self, "IPT", str(e))
            return False
        if was_approved and status != "approved":
            QMessageBox.warning(self, "IPT", "Saved. The edited values have an error (see the Validation tab), so the "
                                             "invoice is back in review – fix it and approve it again.")
        self._load()
        return True

    def _check_unsaved(self) -> bool:
        if not self.dirty:
            return True
        ans = QMessageBox.question(self, "Unsaved changes", "Save your changes first?",
                                   QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if ans == QMessageBox.Save:
            return self._save()
        return ans == QMessageBox.Discard

    def _move(self, d):
        if self._check_unsaved():
            self.index += d
            self._load()

    def _validate(self):
        if self.dirty and not self._save():
            return
        self.s.invoices.revalidate(self.inv.id)
        self._load()
        self.tabs.setCurrentIndex(2)

    def _approve(self):
        if not self._check_unsaved():
            return
        try:
            self.s.invoices.approve(self.inv.id)
        except InvoiceError as e:
            role = self.s.ctx.user.role if self.s.ctx.user else None
            if has_permission(role, "invoice.override") and "validation error" in str(e):
                remark, ok = QInputDialog.getText(self, "Approve with errors",
                                                  f"{e}\n\nAs admin you can approve anyway. Remark (required):")
                if ok and remark.strip():
                    try:
                        self.s.invoices.approve(self.inv.id, remark)
                    except (InvoiceError, PermissionDenied) as e2:
                        QMessageBox.warning(self, "IPT", str(e2))
            else:
                QMessageBox.warning(self, "IPT", str(e))
        except PermissionDenied as e:
            QMessageBox.warning(self, "IPT", str(e))
        self._load()

    def _reopen(self):
        remark, ok = QInputDialog.getText(self, "Re-open invoice", "Why is it re-opened? (e.g. quantity missing)",
                                          text="Correction")
        if ok:
            try:
                self.s.invoices.reopen(self.inv.id, remark)
            except (InvoiceError, PermissionDenied) as e:
                QMessageBox.warning(self, "IPT", str(e))
            self._load()

    def _reject(self):
        remark, ok = QInputDialog.getText(self, "Reject invoice", "Reason for rejection (required):")
        if ok:
            try:
                self.s.invoices.reject(self.inv.id, remark)
            except (InvoiceError, PermissionDenied) as e:
                QMessageBox.warning(self, "IPT", str(e))
            self._load()

    def _delete(self):
        if QMessageBox.question(self, "Delete invoice", "Delete this extracted invoice? The document goes back to "
                                "the queue so it can be extracted again.",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            self.s.invoices.delete(self.inv.id)
        except (InvoiceError, PermissionDenied) as e:
            QMessageBox.warning(self, "IPT", str(e))
            return
        self.ids.pop(self.index)
        if not self.ids:
            self.accept()
            return
        self.index = min(self.index, len(self.ids) - 1)
        self._load()

    def closeEvent(self, e):
        if self._check_unsaved():
            self._disconnect_focus()
            e.accept()
        else:
            e.ignore()

    def done(self, r):
        self._disconnect_focus()
        super().done(r)

    def _disconnect_focus(self):
        from PySide6.QtWidgets import QApplication
        try:
            QApplication.instance().focusChanged.disconnect(self._focus_changed)
        except (RuntimeError, TypeError):
            pass
