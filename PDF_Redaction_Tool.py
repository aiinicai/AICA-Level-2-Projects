"""PDF Redaction Tool -- Python 3.10+ / PyQt6 / PyMuPDF.

RUN: Open this file in IDLE and press F5, or run python PDF_Redaction_Tool.py.
First script run installs missing dependencies (internet needed only for setup).
After setup all PDF processing is local; no files or identifiers are uploaded.
BUILD (on Windows for Windows):
  py -m pip install PyQt6==6.10.2 PyMuPDF==1.26.6 pyinstaller
  py -m PyInstaller --onefile --windowed --name "PDF Redaction Tool" PDF_Redaction_Tool.py
A frozen build never invokes pip. Build separately for each operating system.

SECURITY / SCOPE:
Marks are a preview until Export is confirmed. Export creates a NEW document,
physically removes intersecting characters, blanks intersecting image pixels,
removes touched vector paths, then inserts opaque black PNG patches only inside
marked rectangles. No original pixels are used to create those black patches.
Other page text stays searchable. Touched vector paths/characters can extend
outside a mark, so nearby content may also be removed. Review the output.
Exports discard annotations, forms, links, attachments, outlines, scripts,
metadata and signatures; they are intentionally content-only PDFs.
Full saves with garbage collection discard unreachable objects/history. Export
checks the saved file for text remaining inside marked rectangles and verifies
that their rendered appearance is black. This is defense in depth, not proof
against every malformed/adversarial PDF, every library bug, duplicated data
elsewhere, or copies of the original. No software can promise 'at any cost'.
Smart detection uses extractable text, not OCR: scan-only identifiers require
manual marks. Bank numbers have no universal format: broad 9-18 digit candidates
require human review. Aadhaar validation is structural, not proof of issuance.
PAN detection is format-only. Mobile detection targets Indian mobile numbers.
Passwords stay in memory. Output is not encrypted. Original is never overwritten.
PyMuPDF is AGPL/commercial licensed; review licensing before distributing.
"""
import sys
import os
import re
import math
import copy
import tempfile
import subprocess
import importlib
import importlib.metadata
from pathlib import Path


def bootstrap():
    # Frozen applications use bundled imports, never pip or distribution metadata.
    if getattr(sys, "frozen", False):
        return
    dependencies = [("pymupdf", "PyMuPDF", "1.26.6"), ("PyQt6", "PyQt6", "6.10.2")]
    missing = []
    for module, package, required in dependencies:
        try:
            importlib.import_module(module)
            installed = tuple(int(n) for n in re.findall(r"\d+", importlib.metadata.version(package))[:3])
            if installed < tuple(map(int, required.split("."))):
                missing.append(package + "==" + required)
        except (ImportError, importlib.metadata.PackageNotFoundError):
            missing.append(package + "==" + required)
    if not missing:
        return
    # IDLE uses pythonw.exe on Windows; use its console sibling for pip.
    executable = sys.executable
    if os.name == "nt" and Path(executable).name.lower() == "pythonw.exe":
        executable = str(Path(executable).with_name("python.exe"))
    print("First-run setup: installing missing libraries. No PDF is uploaded.")
    try:
        subprocess.check_call([executable, "-m", "pip", "install", "--disable-pip-version-check", *missing])
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Setup failed. In Command Prompt run: " + executable +
                           " -m pip install " + " ".join(missing)) from exc
    importlib.invalidate_caches()


# Importing for automated tests can bypass installation; normal .py startup cannot.
if __name__ == "__main__":
    bootstrap()
import pymupdf as fitz
from PyQt6.QtCore import Qt, QRectF, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPixmap, QPainter, QPen, QKeySequence, QAction
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QMessageBox, QScrollArea, QSplitter, QLineEdit,
    QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialog, QDialogButtonBox, QProgressBar,
    QInputDialog)

D = ((0,1,2,3,4,5,6,7,8,9),(1,2,3,4,0,6,7,8,9,5),(2,3,4,0,1,7,8,9,5,6),
     (3,4,0,1,2,8,9,5,6,7),(4,0,1,2,3,9,5,6,7,8),(5,9,8,7,6,0,4,3,2,1),
     (6,5,9,8,7,1,0,4,3,2),(7,6,5,9,8,2,1,0,4,3),(8,7,6,5,9,3,2,1,0,4),
     (9,8,7,6,5,4,3,2,1,0))
P = ((0,1,2,3,4,5,6,7,8,9),(1,5,7,6,2,8,3,0,9,4),(5,8,0,3,7,9,6,1,4,2),
     (8,9,1,6,0,4,3,5,2,7),(9,4,5,3,1,2,6,8,7,0),(4,2,8,6,5,7,3,9,0,1),
     (2,7,9,3,8,0,6,4,1,5),(7,0,4,6,9,1,3,2,5,8))


def valid_aadhaar(value):
    value = re.sub(r"\D", "", value)
    if len(value) != 12 or value[0] not in "23456789" or len(set(value)) == 1:
        return False
    checksum = 0
    for i, digit in enumerate(reversed(value)):
        checksum = D[checksum][P[i % 8][int(digit)]]
    return checksum == 0


PATTERNS = {
    "PAN": re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{5}[0-9]{4}[A-Za-z](?![A-Za-z0-9])"),
    "Aadhaar": re.compile(r"(?<!\d)[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?!\d)"),
    "Bank account (candidate)": re.compile(r"(?<![\w])(?:\d[ -]?){8,17}\d(?![\w])"),
    "Email": re.compile(r"(?<![\w.+-])[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}(?![\w.-])"),
    "Mobile (India)": re.compile(r"(?<!\w)(?:(?:\+91|0091|91)[ -]?)?[6-9](?:[ -]?\d){9}(?!\w)")
}


def text_map(page):
    """Character positions, including line breaks; supports split text spans."""
    chars, boxes = [], []
    for block in page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                for char in span.get("chars", []):
                    for character in char["c"]:
                        chars.append(character)
                        boxes.append(char["bbox"])
            chars.append("\n")
            boxes.append(None)
    return "".join(chars), boxes


def rects_for_range(boxes, start, end):
    # Split on line breaks; no enormous rectangle across unrelated lines.
    result, current = [], None
    for box in boxes[start:end]:
        if box is None:
            if current is not None:
                result.append(tuple(current))
                current = None
        else:
            current = fitz.Rect(box) if current is None else current | fitz.Rect(box)
    if current is not None:
        result.append(tuple(current))
    return result


def scan_document(doc, kinds=None, literal=None, progress=lambda *_: None, cancelled=lambda: False):
    results, empty = [], 0
    for index, page in enumerate(doc):
        if cancelled():
            raise InterruptedError("Cancelled")
        text, boxes = text_map(page)
        if not text.strip():
            empty += 1
        if literal is not None:
            # Literal case-insensitive search; flexible PDF whitespace, no user regex.
            parts = re.split(r"\s+", literal.strip())
            regexes = [("Find", re.compile(r"\s+".join(re.escape(p) for p in parts), re.I))]
        else:
            regexes = [(kind, PATTERNS[kind]) for kind in kinds]
        for kind, regex in regexes:
            for match in regex.finditer(text):
                value = match.group()
                if kind == "Aadhaar" and not valid_aadhaar(value):
                    continue
                rectangles = rects_for_range(boxes, match.start(), match.end())
                if rectangles:
                    results.append(dict(page=index, kind=kind, value=value, rects=rectangles))
                    if len(results) > 50000:
                        raise ValueError("More than 50,000 candidates. Search fewer categories or smaller documents.")
        progress(index + 1, len(doc))
    return results, empty


def fingerprint(path):
    stat = os.stat(path)
    return (stat.st_size, stat.st_mtime_ns, stat.st_ino)


def authenticated(path, password):
    doc = fitz.open(path)
    if doc.needs_pass and not doc.authenticate(password):
        doc.close()
        raise ValueError("Incorrect PDF password.")
    if not doc.is_pdf or len(doc) == 0:
        doc.close()
        raise ValueError("Please choose a non-empty PDF document.")
    return doc


def sanitized_export(source, password, marks, destination, expected=None,
                     progress=lambda *_: None, cancelled=lambda: False):
    """Atomic, non-incremental, page-by-page export. No original PDF temp copy."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or (destination.exists() and os.path.samefile(source, destination)):
        raise ValueError("Choose a different output file. The original cannot be overwritten.")
    if expected is not None and fingerprint(source) != expected:
        raise ValueError("The source file changed. Reopen it and review the redaction marks.")
    rectangles = {}
    for mark in marks:
        rectangles.setdefault(mark["page"], []).extend(mark["rects"])
    if not rectangles:
        raise ValueError("Add at least one redaction mark first.")
    # Uniform PNG; it contains no original content, transparency or metadata.
    patch = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 8, 8), False)
    patch.clear_with(0)
    black_png = patch.tobytes("png")
    fd, temporary = tempfile.mkstemp(prefix=".redacted-", suffix=".pdf", dir=destination.parent)
    os.close(fd)
    try:
        with authenticated(source, password) as original, fitz.open() as output:
            for index in range(len(original)):
                if cancelled():
                    raise InterruptedError("Cancelled")
                # Copy only one page, without interactive objects or their values.
                with fitz.open() as one:
                    one.insert_pdf(original, from_page=index, to_page=index,
                                   links=False, annots=False, widgets=False)
                    one.scrub(attached_files=True, clean_pages=True, embedded_files=True,
                              hidden_text=False, javascript=True, metadata=True, redactions=False,
                              remove_links=True, reset_fields=True, reset_responses=True,
                              thumbnails=True, xml_metadata=True)
                    page = one[0]
                    rotation = page.rotation
                    page.set_rotation(0)
                    regions = []
                    for coordinates in rectangles.get(index, []):
                        rect = fitz.Rect(coordinates) & page.rect
                        if rect.is_empty or rect.is_infinite:
                            raise ValueError("Invalid redaction rectangle on page " + str(index + 1))
                        regions.append(rect)
                        page.add_redact_annot(rect, fill=(0,0,0), cross_out=False)
                    if regions:
                        page.apply_redactions(images=2, graphics=2, text=0)
                        # Verify removal using character boxes (including invisible text).
                        _, boxes = text_map(page)
                        if any(fitz.Rect(box).intersects(rect) for box in boxes if box for rect in regions):
                            raise ValueError("Text-removal verification failed on page " + str(index + 1))
                        for rect in regions:
                            page.insert_image(rect, stream=black_png, keep_proportion=False, overlay=True)
                    page.set_rotation(rotation)
                    # Full cleanup first, then copy only reachable sanitized page objects.
                    cleaned = one.tobytes(garbage=4, clean=True, deflate=True)
                    with fitz.open(stream=cleaned, filetype="pdf") as clean_page:
                        output.insert_pdf(clean_page, links=False, annots=False, widgets=False)
                progress(index + 1, len(original) * 2)
            output.set_metadata({})
            output.del_xml_metadata()
            output.save(temporary, garbage=4, clean=True, deflate=True, incremental=False)
        # Reopen bytes on disk: text extraction + black-pixel checks of each marked area.
        with fitz.open(temporary) as check:
            for index, page in enumerate(check):
                if cancelled():
                    raise InterruptedError("Cancelled")
                page.set_rotation(0)
                _, boxes = text_map(page)
                for coordinates in rectangles.get(index, []):
                    rect = fitz.Rect(coordinates) & page.rect
                    if any(fitz.Rect(box).intersects(rect) for box in boxes if box):
                        raise ValueError("Saved PDF contains text inside a marked area.")
                    # Sample the inner region, avoiding edge antialiasing.
                    inset = min(0.4, rect.width / 4, rect.height / 4)
                    inner = fitz.Rect(rect.x0+inset, rect.y0+inset, rect.x1-inset, rect.y1-inset)
                    pix = page.get_pixmap(matrix=fitz.Matrix(1,1), clip=inner, colorspace=fitz.csRGB, alpha=False)
                    if pix.width > 2 and pix.height > 2:
                        # Ignore the outer pixel touched by clipping/antialiasing.
                        samples = pix.samples
                        for y in range(1, pix.height-1):
                            row = samples[y*pix.stride+3:y*pix.stride+(pix.width-1)*3]
                            if any(component > 8 for component in row):
                                raise ValueError("Black-patch verification failed on page " + str(index + 1))
                progress(len(check) + index + 1, len(check) * 2)
        if expected is not None and fingerprint(source) != expected:
            raise ValueError("Source changed during export. Reopen it before exporting.")
        os.replace(temporary, destination)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


class Worker(QThread):
    progress = pyqtSignal(int, int)
    complete = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, task):
        super().__init__()
        self.task = task

    def run(self):
        try:
            result = self.task(self.progress.emit, self.isInterruptionRequested)
            self.complete.emit(result)
        except InterruptedError:
            self.failed.emit("Operation cancelled. No output file was replaced.")
        except Exception as exc:
            self.failed.emit(type(exc).__name__ + ": " + str(exc))


class PageCanvas(QWidget):
    marked = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.pixmap = None
        self.boxes = []
        self.anchor = None
        self.drag = None
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_page(self, pixmap, boxes):
        self.pixmap, self.boxes = pixmap, boxes
        self.anchor = self.drag = None
        self.setFixedSize(pixmap.size())
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.pixmap:
            painter.drawPixmap(0, 0, self.pixmap)
        painter.setPen(QPen(QColor("#e53950"), 2))
        painter.setBrush(QColor(232, 43, 70, 85))
        for rect in self.boxes:
            painter.drawRect(QRectF(*rect))
        if self.drag:
            painter.setPen(QPen(QColor("#126ce5"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(18, 108, 229, 65))
            painter.drawRect(self.drag)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.pixmap and self.isEnabled():
            self.anchor = event.position()

    def mouseMoveEvent(self, event):
        if self.anchor is not None:
            self.drag = QRectF(self.anchor, event.position()).normalized().intersected(QRectF(self.rect()))
            self.update()

    def mouseReleaseEvent(self, event):
        if self.anchor is not None and event.button() == Qt.MouseButton.LeftButton:
            rect = QRectF(self.anchor, event.position()).normalized().intersected(QRectF(self.rect()))
            self.anchor = self.drag = None
            if rect.width() >= 3 and rect.height() >= 3:
                self.marked.emit(rect)
            self.update()


class ReviewDialog(QDialog):
    def __init__(self, candidates, empty_pages, parent):
        super().__init__(parent)
        self.setWindowTitle("Review detected items")
        self.resize(820, 520)
        self.candidates = candidates
        layout = QVBoxLayout(self)
        label = QLabel(f"{len(candidates)} candidates • Tick the items to mark. Nothing is exported yet.\n"
                       f"{empty_pages} page(s) have no extractable text. Use manual marks on scanned pages.")
        label.setWordWrap(True)
        layout.addWidget(label)
        controls = QHBoxLayout()
        for title, checked in [("Select all", True), ("Deselect all", False)]:
            button = QPushButton(title)
            button.clicked.connect(lambda _, state=checked: self.select_all(state))
            controls.addWidget(button)
        layout.addLayout(controls)
        self.table = QTableWidget(len(candidates), 4)
        self.table.setHorizontalHeaderLabels(["Use", "Page", "Type", "Detected text (local only)"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for row, candidate in enumerate(candidates):
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, item)
            for col, value in enumerate([str(candidate["page"]+1), candidate["kind"], candidate["value"]], 1):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.cellDoubleClicked.connect(self.preview)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Double-click a row to preview its page. Bank candidates can include other numbers."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Add checked redaction marks")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def select_all(self, state):
        for row in range(self.table.rowCount()):
            self.table.item(row,0).setCheckState(Qt.CheckState.Checked if state else Qt.CheckState.Unchecked)

    def preview(self, row, col):
        self.parent().show_page(self.candidates[row]["page"])

    def selected(self):
        return [candidate for row, candidate in enumerate(self.candidates)
                if self.table.item(row,0).checkState() == Qt.CheckState.Checked]


STYLE = """
QMainWindow,QDialog {background:#f1f6fd;color:#162c50;}
QWidget {font-family:'Segoe UI',Arial;font-size:13px;color:#162c50;}
QPushButton {background:white;border:1px solid #cbdaf0;border-radius:7px;padding:9px 13px;font-weight:600;}
QPushButton:hover {background:#e5efff;border-color:#2475e6;}
QPushButton:disabled {color:#9aa9bd;background:#edf1f7;}
QPushButton#primary {background:#1669df;color:white;border:none;}
QPushButton#danger {background:#e33450;color:white;border:none;}
QGroupBox {background:white;border:1px solid #d7e3f4;border-radius:10px;margin-top:14px;padding:14px;}
QGroupBox::title {subcontrol-origin:margin;left:12px;padding:0 5px;font-weight:700;color:#1669df;}
QLineEdit,QSpinBox,QDoubleSpinBox {background:white;border:1px solid #cbdaf0;border-radius:5px;padding:7px;}
QTableWidget {background:white;border:1px solid #d7e3f4;gridline-color:#edf1f7;}
QHeaderView::section {background:#e9f1fe;padding:8px;border:0;font-weight:600;}
QScrollArea {background:#dce5f2;border:none;border-radius:8px;}
QProgressBar {border:0;background:#e1eafa;border-radius:4px;text-align:center;}
QProgressBar::chunk {background:#2475e6;border-radius:4px;}
QCheckBox {spacing:8px;padding:3px;}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Redaction Tool")
        self.resize(1280, 850)
        self.doc = None
        self.path = None
        self.password = ""
        self.page_index = 0
        self.zoom = 1.25
        self.marks = []
        self.history = []
        self.worker = None
        self.busy = False
        self.session = None
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20,16,20,16)
        header = QHBoxLayout()
        title = QLabel("PDF Redaction Tool")
        title.setStyleSheet("font-size:27px;font-weight:800;color:#1669df;")
        header.addWidget(title)
        header.addStretch()
        self.open_button = self.button("Open PDF", self.open_pdf, "primary")
        self.export_button = self.button("Export redacted PDF", self.export_pdf, "danger")
        header.addWidget(self.open_button)
        header.addWidget(self.export_button)
        layout.addLayout(header)
        self.filename = QLabel("Open a PDF to begin • PDF processing stays on this computer")
        layout.addWidget(self.filename)
        splitter = QSplitter()
        left = QWidget()
        panel = QVBoxLayout(left)
        panel.setContentsMargins(0,0,12,0)
        manual = QGroupBox("1   Manual redaction")
        ml = QVBoxLayout(manual)
        hint = QLabel("Drag a rectangle on the page.\nRed areas are pending marks; export makes them permanent.")
        hint.setWordWrap(True)
        ml.addWidget(hint)
        self.padding = QDoubleSpinBox()
        self.padding.setRange(0,8)
        self.padding.setValue(1)
        self.padding.setSuffix(" pt margin")
        ml.addWidget(self.padding)
        ml.addWidget(self.button("Undo last action", self.undo))
        ml.addWidget(self.button("Clear marks on this page", self.clear_page))
        panel.addWidget(manual)
        find = QGroupBox("2   Find & redact")
        fl = QVBoxLayout(find)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Enter exact text or number…")
        fl.addWidget(self.search)
        fl.addWidget(self.button("Find all → review", self.find_text, "primary"))
        panel.addWidget(find)
        smart = QGroupBox("3   Smart detection")
        sl = QVBoxLayout(smart)
        self.checks = {}
        for kind in PATTERNS:
            check = QCheckBox(kind)
            check.setChecked(True)
            self.checks[kind] = check
            sl.addWidget(check)
        sl.addWidget(self.button("Scan document → review", self.smart_scan, "primary"))
        note = QLabel("Text-layer detection only. For scans, draw manual marks. All detections require review.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#687d9a;font-size:12px;")
        sl.addWidget(note)
        panel.addWidget(smart)
        self.count_label = QLabel("0 redaction marks")
        panel.addWidget(self.count_label)
        panel.addStretch()
        panel.addWidget(self.button("Help & security details", self.help_dialog))
        left.setMinimumWidth(290)
        left.setMaximumWidth(390)
        splitter.addWidget(left)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0,0,0,0)
        nav = QHBoxLayout()
        nav.addWidget(self.button("‹ Previous", lambda: self.show_page(self.page_index-1)))
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1,1)
        self.page_spin.setKeyboardTracking(False)
        self.page_spin.valueChanged.connect(lambda value: self.show_page(value-1))
        nav.addWidget(self.page_spin)
        self.page_label = QLabel("0/0")
        nav.addWidget(self.page_label)
        nav.addWidget(self.button("Next ›", lambda: self.show_page(self.page_index+1)))
        nav.addStretch()
        nav.addWidget(self.button("−", lambda: self.set_zoom(self.zoom/1.2)))
        self.zoom_label = QLabel("125%")
        nav.addWidget(self.zoom_label)
        nav.addWidget(self.button("+", lambda: self.set_zoom(self.zoom*1.2)))
        nav.addWidget(self.button("Fit width", self.fit_width))
        rl.addLayout(nav)
        self.scroll = QScrollArea()
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.canvas = PageCanvas()
        self.canvas.marked.connect(self.manual_mark)
        self.scroll.setWidget(self.canvas)
        rl.addWidget(self.scroll)
        splitter.addWidget(right)
        splitter.setStretchFactor(1,1)
        layout.addWidget(splitter,1)
        status = QHBoxLayout()
        self.status = QLabel("Ready")
        status.addWidget(self.status,1)
        self.progress = QProgressBar()
        self.progress.setFixedWidth(210)
        self.progress.hide()
        status.addWidget(self.progress)
        self.cancel_button = self.button("Cancel operation", self.cancel_work)
        self.cancel_button.hide()
        status.addWidget(self.cancel_button)
        layout.addLayout(status)
        for sequence, callback in [("Ctrl+O", self.open_pdf),("Ctrl+Z", self.undo),("Ctrl+S", self.export_pdf)]:
            action = QAction(self)
            action.setShortcut(QKeySequence(sequence))
            action.triggered.connect(callback)
            self.addAction(action)
        self.edit_panel = left
        self.nav_panel = right

    def button(self, label, callback, name=""):
        button = QPushButton(label)
        button.setObjectName(name)
        button.clicked.connect(callback)
        return button

    def error(self, message):
        QMessageBox.warning(self, "PDF Redaction Tool", message)

    def require_doc(self):
        if self.busy:
            return False
        if self.doc is None:
            self.error("Open a PDF first.")
            return False
        try:
            if fingerprint(self.path) != self.session:
                raise ValueError("The source file changed. Reopen it before continuing.")
        except (OSError, ValueError) as exc:
            self.error(str(exc))
            return False
        return True

    def open_pdf(self):
        if self.busy:
            return
        if self.marks and QMessageBox.question(self, "Open another PDF", "Discard the pending redaction marks?") != QMessageBox.StandardButton.Yes:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF documents (*.pdf)")
        if not path:
            return
        doc = None
        try:
            doc = fitz.open(path)
            if not doc.is_pdf or not len(doc):
                raise ValueError("Choose a non-empty PDF document.")
            password = ""
            if doc.needs_pass:
                password, ok = QInputDialog.getText(self, "PDF password", "Enter password:", QLineEdit.EchoMode.Password)
                if not ok:
                    doc.close()
                    return
                if not doc.authenticate(password):
                    raise ValueError("Incorrect password.")
            if self.doc:
                self.doc.close()
            self.doc, self.path, self.password = doc, path, password
            self.session = fingerprint(path)
            self.marks, self.history = [], []
            self.page_spin.setMaximum(len(doc))
            self.filename.setText(Path(path).name)
            self.show_page(0)
            self.update_count()
            self.status.setText("Drag to mark an area, or search the document.")
        except Exception as exc:
            if doc and doc is not self.doc:
                doc.close()
            self.error(str(exc))

    def show_page(self, index):
        if self.doc is None or not 0 <= index < len(self.doc):
            return
        try:
            self.page_index = index
            page = self.doc[index]
            # Cap preview pixel count for oversized pages; export uses PDF coordinates.
            scale = min(self.zoom, math.sqrt(24000000 / max(1, page.rect.width*page.rect.height)))
            pix = page.get_pixmap(matrix=fitz.Matrix(scale,scale), colorspace=fitz.csRGB, alpha=False)
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
            self.scale_x = pix.width / page.rect.width
            self.scale_y = pix.height / page.rect.height
            boxes = []
            for mark in self.marks:
                if mark["page"] == index:
                    for coords in mark["rects"]:
                        rect = fitz.Rect(coords) * page.rotation_matrix
                        boxes.append((rect.x0*self.scale_x, rect.y0*self.scale_y,
                                      rect.width*self.scale_x, rect.height*self.scale_y))
            self.canvas.set_page(QPixmap.fromImage(image), boxes)
            self.page_spin.blockSignals(True)
            self.page_spin.setValue(index+1)
            self.page_spin.blockSignals(False)
            self.page_label.setText(f"{index+1}/{len(self.doc)}")
            self.update_count()
            self.zoom_label.setText(f"{scale*100:.0f}%")
        except Exception as exc:
            self.error("Could not render page: " + str(exc))

    def set_zoom(self, value):
        if self.busy:
            return
        self.zoom = max(.2, min(4, value))
        self.show_page(self.page_index)

    def fit_width(self):
        if self.doc and not self.busy:
            self.set_zoom((self.scroll.viewport().width()-24)/self.doc[self.page_index].rect.width)

    def manual_mark(self, view_rect):
        if not self.require_doc():
            return
        page = self.doc[self.page_index]
        rect = fitz.Rect(view_rect.left()/self.scale_x, view_rect.top()/self.scale_y,
                         view_rect.right()/self.scale_x, view_rect.bottom()/self.scale_y) * page.derotation_matrix
        self.add_marks([dict(page=self.page_index, kind="Manual", rects=[tuple(rect)])])

    def add_marks(self, items):
        if not items:
            return
        self.history.append(("add", len(self.marks)))
        pad = self.padding.value()
        for item in items:
            page = self.doc[item["page"]]
            bounds = page.rect * page.derotation_matrix
            rectangles = []
            for coordinates in item["rects"]:
                rect = fitz.Rect(coordinates)
                rect = fitz.Rect(rect.x0-pad, rect.y0-pad, rect.x1+pad, rect.y1+pad) & bounds
                if not rect.is_empty:
                    rectangles.append(tuple(rect))
            if rectangles:
                # Do not retain detected sensitive strings in mark/history records.
                self.marks.append(dict(page=item["page"], kind=item["kind"], rects=rectangles))
        self.update_count()
        self.show_page(self.page_index)

    def update_count(self):
        current = sum(mark["page"] == self.page_index for mark in self.marks)
        self.count_label.setText(f"{len(self.marks)} marks total • {current} on this page")

    def undo(self):
        if self.busy or not self.history:
            return
        kind, data = self.history.pop()
        if kind == "add":
            self.marks = self.marks[:data]
        else:
            self.marks = data
        self.update_count()
        self.show_page(self.page_index)

    def clear_page(self):
        if not self.require_doc() or not any(m["page"] == self.page_index for m in self.marks):
            return
        self.history.append(("restore", copy.deepcopy(self.marks)))
        self.marks = [m for m in self.marks if m["page"] != self.page_index]
        self.update_count()
        self.show_page(self.page_index)

    def start_work(self, task, complete, message):
        self.busy = True
        self.edit_panel.setEnabled(False)
        self.nav_panel.setEnabled(False)
        self.open_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.progress.setValue(0)
        self.progress.show()
        self.cancel_button.show()
        self.status.setText(message)
        self.worker = Worker(task)
        self.worker.progress.connect(lambda value,total: self.progress.setValue(int(value*100/max(1,total))))
        self.worker.complete.connect(complete)
        self.worker.failed.connect(self.error)
        self.worker.finished.connect(self.finish_work)
        self.worker.start()

    def finish_work(self):
        self.busy = False
        self.edit_panel.setEnabled(True)
        self.nav_panel.setEnabled(True)
        self.open_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.progress.hide()
        self.cancel_button.hide()
        self.status.setText("Ready • Review the exported PDF before sharing it.")
        self.worker.deleteLater()
        self.worker = None

    def cancel_work(self):
        if self.worker:
            self.worker.requestInterruption()
            self.status.setText("Cancelling after the current page…")

    def find_text(self):
        value = self.search.text().strip()
        if self.require_doc():
            if not value:
                self.error("Enter the text or number to find.")
            else:
                self.run_scan(literal=value)

    def smart_scan(self):
        if self.require_doc():
            kinds = [kind for kind, checkbox in self.checks.items() if checkbox.isChecked()]
            if not kinds:
                self.error("Select at least one identifier type.")
            else:
                self.run_scan(kinds=kinds)

    def run_scan(self, kinds=None, literal=None):
        path, password, expected = self.path, self.password, self.session
        def task(progress, cancelled):
            if fingerprint(path) != expected:
                raise ValueError("Source file changed. Reopen it.")
            with authenticated(path,password) as doc:
                result = scan_document(doc,kinds,literal,progress,cancelled)
            if fingerprint(path) != expected:
                raise ValueError("Source file changed while scanning. Reopen it.")
            return result
        self.start_work(task, self.review_results, "Scanning text locally…")

    def review_results(self, result):
        candidates, empty = result
        if not candidates:
            QMessageBox.information(self, "Scan complete", f"No matching text found.\n{empty} page(s) have no extractable text; use manual marks for scans.")
            return
        dialog = ReviewDialog(candidates,empty,self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.add_marks(dialog.selected())

    def export_pdf(self):
        if not self.require_doc():
            return
        if not self.marks:
            self.error("Add redaction marks first.")
            return
        answer = QMessageBox.question(self, "Confirm permanent redaction",
            f"Apply {len(self.marks)} reviewed marks to a NEW PDF?\n\n"
            "Marked text is removed, marked image pixels are blanked, and black raster patches are inserted. "
            "Touched characters/vector paths may also disappear outside a mark.\n\n"
            "The export discards forms, annotations, links, attachments, metadata and digital signatures. "
            "Text outside the redactions remains selectable. Review the saved PDF before sharing.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        default = str(Path(self.path).with_name(Path(self.path).stem + "_redacted.pdf"))
        destination, _ = QFileDialog.getSaveFileName(self,"Save new redacted PDF",default,"PDF documents (*.pdf)")
        if not destination:
            return
        if not destination.lower().endswith(".pdf"):
            destination += ".pdf"
            if Path(destination).exists() and QMessageBox.question(self, "Replace output file",
                    "This output PDF already exists. Replace it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
        path, password, marks, expected = self.path, self.password, copy.deepcopy(self.marks), self.session
        def task(progress, cancelled):
            sanitized_export(path,password,marks,destination,expected,progress,cancelled)
            return destination
        self.start_work(task, lambda saved: QMessageBox.information(self,"Export complete",
            "Saved and verified:\n" + saved + "\n\nOriginal unchanged. Open the exported PDF and review it before sharing."),
            "Removing marked content and verifying the new PDF…")

    def help_dialog(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Help & security details")
        dialog.setText("Marks are previews until you confirm Export.\n\n"
            "Manual: drag an area. The margin expands marks slightly to cover glyph edges.\n"
            "Find: matches literal text across the extractable text layer, ignoring case and flexible whitespace.\n"
            "Smart: tick patterns, scan, review candidates, tick the ones to redact. Double-click a row to preview.\n"
            "Undo reverses the last batch of marks or a page-clear action.\n\n"
            "Scans require manual marking; there is no OCR. Bank detection is deliberately broad.\n"
            "No information is uploaded. First-run package installation needs internet; PDF processing does not.\n\n"
            "Export removes content, then inserts solid black raster patches only in marked regions. "
            "Other page text is preserved where possible. It strips interactive/auxiliary content. "
            "Automatic checks cannot guarantee security against every PDF or library defect, or remove duplicates outside the marks. "
            "Always inspect your exported document.\n\n"
            "Setup/build instructions and security scope are in the comments at the top of this .py file.")
        dialog.exec()

    def closeEvent(self,event):
        if self.busy:
            self.error("Cancel or finish the current operation before closing.")
            event.ignore()
            return
        if self.marks and QMessageBox.question(self,"Close", "Close the application? Pending marks are not saved as a project.") != QMessageBox.StandardButton.Yes:
            event.ignore()
            return
        if self.doc:
            self.doc.close()
        event.accept()


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("PDF Redaction Tool")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # IDLE shows the traceback; double-click launches can also display a dialog.
        import traceback
        traceback.print_exc()
        try:
            application = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "PDF Redaction Tool", str(error))
        except Exception:
            pass
