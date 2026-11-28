"""PDF Redaction Tool - offline, secure, review-first PDF redaction for Windows.

Run this file directly from IDLE or a terminal.  On first .py run it installs
PyQt6 and PyMuPDF if needed.  Packaged executables skip that install step.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


def install_missing_packages() -> None:
    """Install only absent dependencies for source-script use; never in an EXE."""
    if getattr(sys, "frozen", False):
        return
    packages = {"PyQt6": "PyQt6", "fitz": "PyMuPDF"}
    missing = [pip_name for module, pip_name in packages.items()
               if importlib.util.find_spec(module) is None]
    if missing:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", *missing])


install_missing_packages()

import fitz  # PyMuPDF
from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget,
)


@dataclass
class Redaction:
    page: int
    rect: fitz.Rect
    label: str = "Manual"


def verhoeff_valid(number: str) -> bool:
    """Validate a 12-digit Aadhaar candidate using the Verhoeff checksum."""
    digits = re.sub(r"\D", "", number)
    if len(digits) != 12 or len(set(digits)) == 1:
        return False
    d = ((0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
         (2, 3, 4, 0, 1, 7, 8, 9, 5, 6), (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
         (4, 0, 1, 2, 3, 9, 5, 6, 7, 8), (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
         (6, 5, 9, 8, 7, 1, 0, 4, 3, 2), (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
         (8, 7, 6, 5, 9, 3, 2, 1, 0, 4), (9, 8, 7, 6, 5, 4, 3, 2, 1, 0))
    p = ((0, 1, 2, 3, 4, 5, 6, 7, 8, 9), (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
         (5, 8, 0, 3, 7, 9, 6, 1, 4, 2), (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
         (9, 4, 5, 3, 1, 2, 6, 8, 7, 0), (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
         (2, 7, 9, 3, 8, 0, 6, 4, 1, 5), (7, 0, 4, 6, 9, 1, 3, 2, 5, 8))
    check = 0
    for i, digit in enumerate(reversed(digits)):
        check = d[check][p[i % 8][int(digit)]]
    return check == 0


class PageCanvas(QLabel):
    selection_made = pyqtSignal(QRect)

    def __init__(self) -> None:
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._start = None
        self._rubber = None
        self._overlay_rects: list[fitz.Rect] = []
        self.scale = 1.5

    def set_page(self, page: fitz.Page, scale: float, redactions: list[fitz.Rect]) -> None:
        self.scale, self._overlay_rects = scale, redactions
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
        result = QPixmap.fromImage(image)
        painter = QPainter(result)
        painter.setPen(QPen(QColor("#e21b3c"), max(2, int(scale))))
        painter.setBrush(QColor(226, 27, 60, 65))
        for rect in redactions:
            painter.drawRect(QRect(round(rect.x0 * scale), round(rect.y0 * scale),
                                   round(rect.width * scale), round(rect.height * scale)))
        painter.end()
        self.setPixmap(result)
        self.resize(result.size())

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.position().toPoint()
            self._rubber = QRect(self._start, self._start)
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._start:
            self._rubber = QRect(self._start, event.position().toPoint()).normalized()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._start:
            rect = QRect(self._start, event.position().toPoint()).normalized()
            self._start = self._rubber = None
            self.update()
            if rect.width() > 4 and rect.height() > 4:
                self.selection_made.emit(rect)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._rubber:
            painter = QPainter(self)
            painter.setPen(QPen(QColor("#e21b3c"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(226, 27, 60, 55))
            painter.drawRect(self._rubber)


class RedactionTool(QMainWindow):
    PATTERNS = {
        "PAN": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I),
        "GSTIN": re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[A-Z0-9]\b", re.I),
        "Aadhaar": re.compile(r"\b(?:\d{4}[ -]?){2}\d{4}\b"),
        "Email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
        "Mobile": re.compile(r"(?<!\d)(?:\+91[ -]?)?[6-9]\d{4}[ -]?\d{5}(?!\d)"),
        "Bank account": re.compile(r"(?<!\d)\d{9,18}(?!\d)"),
    }

    def __init__(self) -> None:
        super().__init__()
        self.doc: fitz.Document | None = None
        self.path: Path | None = None
        self.current = 0
        self.zoom = 1.5
        self.redactions: list[Redaction] = []
        self.setWindowTitle("PDF Redaction Tool")
        self.resize(1250, 820)
        self._build()

    def _build(self) -> None:
        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(15, 12, 15, 15); outer.setSpacing(10)
        header = QHBoxLayout()
        title = QLabel("PDF <span style='color:#e21b3c'>REDACTION</span> TOOL")
        title.setObjectName("title"); header.addWidget(title); header.addStretch()
        header.addWidget(self.button("Open PDF", self.open_pdf, True)); outer.addLayout(header)
        nav = QHBoxLayout()
        nav.addWidget(self.button("◀ Previous", lambda: self.goto(self.current - 1)))
        nav.addWidget(self.button("Next ▶", lambda: self.goto(self.current + 1)))
        nav.addSpacing(15); nav.addWidget(QLabel("Page")); self.page_jump = QSpinBox(); self.page_jump.setMinimum(1); self.page_jump.valueChanged.connect(lambda n: self.goto(n - 1)); nav.addWidget(self.page_jump)
        self.page_label = QLabel("0 / 0"); nav.addWidget(self.page_label); nav.addStretch()
        nav.addWidget(self.button("− Zoom", lambda: self.change_zoom(-.25)))
        nav.addWidget(self.button("+ Zoom", lambda: self.change_zoom(.25)))
        nav.addWidget(self.button("Undo", self.undo)); nav.addWidget(self.button("Clear This Page", self.clear_page)); outer.addLayout(nav)
        split = QSplitter(Qt.Orientation.Horizontal)
        viewer = QWidget(); view_layout = QVBoxLayout(viewer); view_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = PageCanvas(); self.canvas.selection_made.connect(self.manual_selection)
        self.scroll = QScrollArea(); self.scroll.setWidget(self.canvas); self.scroll.setWidgetResizable(False); self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter); view_layout.addWidget(self.scroll)
        split.addWidget(viewer)
        side = QFrame(); side.setObjectName("side"); panel = QVBoxLayout(side); panel.setSpacing(10)
        panel.addWidget(QLabel("FIND & REDACT", objectName="section"))
        self.search = QLineEdit(); self.search.setPlaceholderText("Text to find (one term per line)"); self.search.setMinimumHeight(62); panel.addWidget(self.search)
        panel.addWidget(self.button("Find Text", self.find_text, True))
        panel.addWidget(QLabel("SMART DETECTION", objectName="section"))
        panel.addWidget(QLabel("Scan for PAN, GSTIN, validated Aadhaar, bank accounts, emails and mobile numbers."))
        panel.addWidget(self.button("Scan Document", self.smart_scan, True))
        panel.addWidget(QLabel("Review candidates - tick only those to redact:", objectName="section"))
        self.candidates = QTableWidget(0, 4); self.candidates.setHorizontalHeaderLabels(["Use", "Page", "Type", "Matched text"]); self.candidates.horizontalHeader().setStretchLastSection(True); panel.addWidget(self.candidates, 1)
        panel.addWidget(self.button("Add Selected Candidates", self.accept_candidates))
        panel.addWidget(self.button("Create Secure Redacted PDF", self.save_redacted, True))
        self.status = QTextEdit(readOnly=True); self.status.setFixedHeight(95); panel.addWidget(self.status)
        split.addWidget(side); split.setSizes([850, 360]); outer.addWidget(split, 1)
        self.log("Offline mode: your documents never leave this computer.")

    def button(self, text, action, accent=False):
        b = QPushButton(text); b.clicked.connect(action); b.setObjectName("accent" if accent else ""); return b

    def log(self, text: str) -> None:
        self.status.append(text)

    def require_doc(self) -> bool:
        if not self.doc:
            QMessageBox.information(self, "PDF Redaction Tool", "Open a PDF file first.")
            return False
        return True

    def open_pdf(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF files (*.pdf)")
        if not name: return
        try:
            if self.doc: self.doc.close()
            self.doc, self.path, self.current = fitz.open(name), Path(name), 0
            if self.doc.needs_pass:
                self.doc.close(); self.doc = None
                raise ValueError("Password-protected PDFs are not supported. Save an unlocked copy first.")
            self.redactions.clear(); self.candidates.setRowCount(0)
            self.page_jump.blockSignals(True); self.page_jump.setRange(1, max(1, len(self.doc))); self.page_jump.setValue(1); self.page_jump.blockSignals(False)
            self.render(); self.log(f"Opened {self.path.name} ({len(self.doc)} pages).")
        except Exception as exc: self.error(str(exc))

    def render(self) -> None:
        if not self.doc: return
        page = self.doc[self.current]
        marks = [r.rect for r in self.redactions if r.page == self.current]
        self.canvas.set_page(page, self.zoom, marks)
        self.page_label.setText(f"{self.current + 1} / {len(self.doc)}")
        self.page_jump.blockSignals(True); self.page_jump.setValue(self.current + 1); self.page_jump.blockSignals(False)

    def goto(self, page: int) -> None:
        if self.doc and 0 <= page < len(self.doc): self.current = page; self.render()

    def change_zoom(self, amount: float) -> None:
        if self.require_doc(): self.zoom = max(.5, min(3.5, self.zoom + amount)); self.render()

    def manual_selection(self, qrect: QRect) -> None:
        if not self.doc: return
        rect = fitz.Rect(qrect.left() / self.zoom, qrect.top() / self.zoom, qrect.right() / self.zoom, qrect.bottom() / self.zoom)
        self.redactions.append(Redaction(self.current, rect, "Manual")); self.render(); self.log(f"Marked manual redaction on page {self.current + 1}.")

    def undo(self) -> None:
        if self.redactions: self.redactions.pop(); self.render(); self.log("Removed last redaction mark.")

    def clear_page(self) -> None:
        if self.require_doc():
            old = len(self.redactions); self.redactions = [r for r in self.redactions if r.page != self.current]
            self.render(); self.log(f"Cleared {old - len(self.redactions)} mark(s) from this page.")

    def add_candidate(self, page: int, rect: fitz.Rect, kind: str, text: str) -> None:
        row = self.candidates.rowCount(); self.candidates.insertRow(row)
        check = QCheckBox(); check.setChecked(True); self.candidates.setCellWidget(row, 0, check)
        self.candidates.setItem(row, 1, QTableWidgetItem(str(page + 1)))
        self.candidates.setItem(row, 2, QTableWidgetItem(kind))
        item = QTableWidgetItem(text); item.setData(Qt.ItemDataRole.UserRole, (page, (rect.x0, rect.y0, rect.x1, rect.y1), kind)); self.candidates.setItem(row, 3, item)

    def find_hits(self, text: str, kind: str) -> int:
        count = 0
        for number, page in enumerate(self.doc):
            for rect in page.search_for(text, quads=False):
                self.add_candidate(number, rect, kind, text); count += 1
        return count

    def find_text(self) -> None:
        if not self.require_doc(): return
        terms = [x.strip() for x in self.search.text().splitlines() if x.strip()]
        if not terms: return self.error("Enter one or more search terms, each on a new line.")
        self.candidates.setRowCount(0); total = sum(self.find_hits(term, "Find") for term in terms)
        self.log(f"Found {total} occurrence(s). Review the checked candidates before adding them.")

    def smart_scan(self) -> None:
        if not self.require_doc(): return
        self.candidates.setRowCount(0); total = 0
        for number, page in enumerate(self.doc):
            text = page.get_text("text")
            seen: set[tuple[str, str]] = set()
            for kind, pattern in self.PATTERNS.items():
                for match in pattern.finditer(text):
                    value = match.group().strip()
                    if kind == "Aadhaar" and not verhoeff_valid(value): continue
                    key = (kind, value)
                    if key in seen: continue
                    seen.add(key)
                    for rect in page.search_for(value):
                        self.add_candidate(number, rect, kind, value); total += 1
        self.log(f"Smart scan found {total} candidate(s). Nothing is redacted until you review and add selected items.")

    def accept_candidates(self) -> None:
        if not self.require_doc(): return
        added = 0
        existing = {(r.page, tuple(round(x, 2) for x in r.rect), r.label) for r in self.redactions}
        for row in range(self.candidates.rowCount()):
            check = self.candidates.cellWidget(row, 0)
            if not check.isChecked(): continue
            page, coords, kind = self.candidates.item(row, 3).data(Qt.ItemDataRole.UserRole)
            rect = fitz.Rect(coords); key = (page, tuple(round(x, 2) for x in rect), kind)
            if key not in existing: self.redactions.append(Redaction(page, rect, kind)); added += 1
        self.render(); self.log(f"Added {added} approved redaction mark(s).")

    def save_redacted(self) -> None:
        if not self.require_doc(): return
        if not self.redactions: return self.error("Mark at least one area or approve a candidate first.")
        default = self.path.with_stem(self.path.stem + "_REDACTED")
        destination, _ = QFileDialog.getSaveFileName(self, "Save secure redacted PDF", str(default), "PDF files (*.pdf)")
        if not destination: return
        try:
            # Work on a newly opened copy: source remains completely unchanged.
            out = fitz.open(str(self.path))
            by_page: dict[int, list[fitz.Rect]] = {}
            for mark in self.redactions: by_page.setdefault(mark.page, []).append(mark.rect)
            for page_number, rects in by_page.items():
                page = out[page_number]
                for rect in rects:
                    # Redaction annotations delete overlapping text / images / vectors from the content stream.
                    page.add_redact_annot(rect, fill=(0, 0, 0), cross_out=False)
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE, graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED)
                # Render only the already-redacted patches and replace their area with PNG patches.
                # This keeps non-redacted page objects selectable while making each patch a raster image.
                for rect in rects:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect, alpha=False)
                    page.insert_image(rect, stream=pix.tobytes("png"), overlay=True)
            out.save(destination, garbage=4, deflate=True, clean=True)
            out.close()
            self.log("Secure redacted copy created. Original PDF was not changed.")
            QMessageBox.information(self, "Success", "Secure redacted PDF saved successfully. The original file remains untouched.")
        except Exception as exc: self.error(f"Could not create redacted PDF: {exc}")

    def error(self, message: str) -> None:
        self.log("Error: " + message)
        text = message.lower()
        if "password" in text or "protected" in text:
            explanation = "This PDF is password-protected. Save an unlocked copy first, then open it in the redaction tool."
        elif "permission denied" in text or "access is denied" in text:
            explanation = "Windows blocked access to this file or folder. Choose a different output folder and make sure the PDF is not open elsewhere."
        elif "ocr" in text or "tesseract" in text:
            explanation = "OCR could not read this scanned page. Try a clearer scan, then run the redaction scan again."
        elif "no pages" in text:
            explanation = "The selected PDF has no readable pages. Choose another PDF file and try again."
        else:
            explanation = "Confirm that the PDF is valid and that you can write to the selected output folder. Expand Technical details below for the exact system message."
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("PDF Redaction Tool - Help with this error")
        dialog.setText(f"The requested redaction task could not be completed.\n\nHow to fix it:\n{explanation}")
        dialog.setInformativeText("Use Show Details below only if you need the exact technical error message.")
        dialog.setDetailedText(f"Technical details:\n{message}")
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.exec()


STYLE = """
QMainWindow { background: #edf5ff; } QLabel { color: #17395e; font-size: 13px; } QLabel#title { font: bold 26px 'Segoe UI'; color: #0c4b8e; letter-spacing: 1px; } QLabel#section { font-weight: bold; color: #0c4b8e; font-size: 14px; }
QFrame#side { background: white; border: 1px solid #c7ddf4; border-radius: 10px; padding: 8px; } QScrollArea { background: #b9d8f2; border: 1px solid #87b8e6; }
QPushButton { background: #1479c9; color: white; border: none; border-radius: 7px; padding: 9px 12px; font-weight: 600; } QPushButton:hover { background: #0d5fa8; } QPushButton#accent { background: #e21b3c; } QPushButton#accent:hover { background: #bd1230; }
QLineEdit, QSpinBox, QTableWidget, QTextEdit { background: white; border: 1px solid #aac9e7; border-radius: 6px; padding: 6px; color: #183d63; } QHeaderView::section { background: #0c4b8e; color: white; padding: 6px; border: none; } QTextEdit { background: #f7fbff; }
"""


def main() -> None:
    app = QApplication(sys.argv); app.setStyleSheet(STYLE)
    window = RedactionTool(); window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
