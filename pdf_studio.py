"""PDF Studio - a colorful desktop toolkit for common PDF tasks on Windows."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import traceback
import uuid
import importlib
from io import BytesIO
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea,
    QInputDialog, QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)
from pypdf import PdfReader, PdfWriter


PDF_FILTER = "PDF files (*.pdf)"
OFFICE_FILTER = "Office files (*.doc *.docx *.xls *.xlsx *.ppt *.pptx)"
IMAGE_FILTER = "Image files (*.jpg *.jpeg *.png *.bmp *.tif *.tiff)"


class DropLineEdit(QLineEdit):
    """A path field that accepts files or folders dropped from Windows Explorer."""
    paths_dropped = pyqtSignal(list)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: event.ignore()

    def dropEvent(self, event) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.paths_dropped.emit(paths)
            event.acceptProposedAction()
        else: event.ignore()


class DropListWidget(QListWidget):
    """A list that accepts one or more dropped files."""
    paths_dropped = pyqtSignal(list)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: event.ignore()

    def dropEvent(self, event) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.paths_dropped.emit(paths)
            event.acceptProposedAction()
        else: event.ignore()


class PDFStudio(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDF Studio - Merge, Split & Convert")
        self.resize(960, 700)
        self.setMinimumSize(820, 600)
        self.pdf_passwords: dict[str, str] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 22, 28, 25)
        layout.setSpacing(14)

        heading = QLabel("PDF <span style='color:#ffcb4c'>STUDIO</span>")
        heading.setObjectName("title")
        heading.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(heading)
        sub = QLabel("Your bright, simple desktop workspace for PDF files")
        sub.setObjectName("subtitle")
        layout.addWidget(sub)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._merge_tab(), "  Merge PDFs  ")
        self.tabs.addTab(self._split_tab(), "  Split PDF  ")
        self.tabs.addTab(self._convert_tab(), "  Convert  ")
        self.tabs.addTab(self._compress_tab(), "  Compress  ")
        layout.addWidget(self.tabs, 1)

        self.status = QTextEdit(readOnly=True)
        self.status.setObjectName("status")
        self.status.setFixedHeight(86)
        layout.addWidget(self.status)
        self.log("Ready. Choose a tool above to get started.")

    def _card(self) -> tuple[QWidget, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        box = QVBoxLayout(card)
        box.setContentsMargins(22, 20, 22, 20)
        box.setSpacing(12)
        return card, box

    def _button(self, text: str, handler, accent: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(38)
        button.clicked.connect(handler)
        if accent:
            button.setObjectName("accent")
        return button

    def _choose_file(self, field: QLineEdit, filter_text: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose a file", "", filter_text)
        if path:
            field.setText(path)

    def _choose_folder(self, field: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if path:
            field.setText(path)

    def _merge_tab(self) -> QWidget:
        card, box = self._card()
        box.addWidget(QLabel("Merge PDFs in the order shown"))
        self.merge_list = DropListWidget()
        self.merge_list.paths_dropped.connect(self.add_merge_paths)
        self.merge_list.setToolTip("Select items and use the buttons to reorder or remove them.")
        box.addWidget(self.merge_list, 1)
        row = QHBoxLayout()
        row.addWidget(self._button("+ Add PDFs", self.add_merge_files))
        row.addWidget(self._button("Move Up", lambda: self.move_merge(-1)))
        row.addWidget(self._button("Move Down", lambda: self.move_merge(1)))
        row.addWidget(self._button("Remove", self.remove_merge_file))
        row.addStretch()
        box.addLayout(row)
        self.merge_output = DropLineEdit()
        self.merge_output.setPlaceholderText("Output PDF path (choose where to save)")
        self.merge_output.paths_dropped.connect(lambda paths: self.set_dropped_output(self.merge_output, paths, "merged.pdf"))
        out = QHBoxLayout()
        out.addWidget(self.merge_output, 1)
        out.addWidget(self._button("Save As...", self.choose_merge_output))
        box.addLayout(out)
        box.addWidget(self._button("Merge PDFs", self.merge_pdfs, True))
        return card

    def _split_tab(self) -> QWidget:
        card, box = self._card()
        self.split_input = DropLineEdit()
        self.split_input.paths_dropped.connect(lambda paths: self.set_dropped_file(self.split_input, paths, {".pdf"}))
        self.split_input.setPlaceholderText("Select one PDF to split")
        row = QHBoxLayout(); row.addWidget(self.split_input, 1); row.addWidget(self._button("Browse...", lambda: self._choose_file(self.split_input, PDF_FILTER)))
        box.addWidget(QLabel("Source PDF")); box.addLayout(row)
        box.addWidget(QLabel("Page ranges (examples: 1-3, 5, 7-9). Leave empty to create one PDF per page."))
        self.page_ranges = QLineEdit()
        self.page_ranges.setPlaceholderText("Example: 1-3, 5, 7-9")
        box.addWidget(self.page_ranges)
        self.split_folder = DropLineEdit(); self.split_folder.setPlaceholderText("Choose an output folder or drop a folder here")
        self.split_folder.paths_dropped.connect(lambda paths: self.set_dropped_folder(self.split_folder, paths))
        folder = QHBoxLayout(); folder.addWidget(self.split_folder, 1); folder.addWidget(self._button("Output Folder...", lambda: self._choose_folder(self.split_folder)))
        box.addLayout(folder)
        box.addWidget(self._button("Split PDF", self.split_pdf, True))
        box.addStretch()
        return card

    def _convert_tab(self) -> QWidget:
        card, box = self._card()
        box.addWidget(QLabel("Convert documents"))
        self.convert_input = DropLineEdit(); self.convert_input.setPlaceholderText("Select or drop a PDF or Microsoft Office file")
        self.convert_input.paths_dropped.connect(lambda paths: self.set_dropped_file(self.convert_input, paths, {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}))
        row = QHBoxLayout(); row.addWidget(self.convert_input, 1); row.addWidget(self._button("Browse...", lambda: self._choose_file(self.convert_input, PDF_FILTER + ";;" + OFFICE_FILTER)))
        box.addLayout(row)
        grid = QGridLayout()
        actions = [("PDF to Editable Word (.docx)", "docx"), ("PDF to Excel (.xlsx)", "xlsx"),
                   ("PDF to Editable PowerPoint (.pptx)", "pptx"), ("PDF to Images (JPEG)", "jpg"),
                   ("Office to PDF", "pdf")]
        for i, (label, target) in enumerate(actions):
            grid.addWidget(self._button(label, lambda checked=False, t=target: self.convert(t), True), i // 2, i % 2)
        box.addLayout(grid)
        priority = QHBoxLayout()
        priority.addWidget(QLabel("Word/PPT conversion priority:"))
        self.office_conversion_mode = QComboBox()
        self.office_conversion_mode.addItem("Preserve original format (best visual match)", "layout")
        self.office_conversion_mode.addItem("Editable text (best editing, layout may vary)", "editable")
        self.office_conversion_mode.setToolTip("A PDF cannot always retain its exact design and remain fully editable. Choose which result matters most.")
        priority.addWidget(self.office_conversion_mode, 1)
        box.addLayout(priority)
        excel_options = QHBoxLayout()
        excel_options.addWidget(QLabel("PDF to Excel layout:"))
        self.excel_layout = QComboBox()
        self.excel_layout.addItem("Single worksheet - combine all tables", "single")
        self.excel_layout.addItem("Multiple worksheets - one table per sheet", "multiple")
        self.excel_layout.setToolTip("Choose the layout used only by PDF to Excel conversion.")
        excel_options.addWidget(self.excel_layout, 1)
        box.addLayout(excel_options)
        self.convert_folder = DropLineEdit(); self.convert_folder.setPlaceholderText("Output folder (or drop a folder here)")
        self.convert_folder.paths_dropped.connect(lambda paths: self.set_dropped_folder(self.convert_folder, paths))
        folder = QHBoxLayout(); folder.addWidget(self.convert_folder, 1); folder.addWidget(self._button("Output Folder...", lambda: self._choose_folder(self.convert_folder)))
        box.addLayout(folder)
        box.addWidget(QLabel("Combine JPEG/images into one PDF (files are used in the displayed order):"))
        self.image_pdf_list = DropListWidget()
        self.image_pdf_list.paths_dropped.connect(self.add_image_paths)
        self.image_pdf_list.setMaximumHeight(90)
        box.addWidget(self.image_pdf_list)
        image_buttons = QHBoxLayout()
        image_buttons.addWidget(self._button("+ Add Images", self.add_images_for_pdf))
        image_buttons.addWidget(self._button("Move Up", lambda: self.move_image(-1)))
        image_buttons.addWidget(self._button("Move Down", lambda: self.move_image(1)))
        image_buttons.addWidget(self._button("Remove", self.remove_image))
        image_buttons.addStretch()
        box.addLayout(image_buttons)
        self.image_pdf_output = DropLineEdit(); self.image_pdf_output.setPlaceholderText("Combined image PDF output path")
        self.image_pdf_output.paths_dropped.connect(lambda paths: self.set_dropped_output(self.image_pdf_output, paths, "images_combined.pdf"))
        image_output = QHBoxLayout(); image_output.addWidget(self.image_pdf_output, 1); image_output.addWidget(self._button("Save As...", self.choose_image_pdf_output))
        box.addLayout(image_output)
        box.addWidget(self._button("Combine Images to PDF", self.images_to_pdf, True))
        note = QLabel("Preserve-original-format mode keeps the PDF appearance most closely, but pages may remain image-based. Editable-text mode uses PDF text or OCR and may need layout adjustment. JPEG export creates one image per PDF page. Excel extracts detected tables using the selected layout. Office-to-PDF requires LibreOffice installed.")
        note.setWordWrap(True); note.setObjectName("hint"); box.addWidget(note)
        box.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(card)
        return scroll

    def _compress_tab(self) -> QWidget:
        card, box = self._card()
        box.addWidget(QLabel("Compress PDF"))
        self.compress_input = DropLineEdit(); self.compress_input.setPlaceholderText("Select or drop a PDF to compress")
        self.compress_input.paths_dropped.connect(lambda paths: self.set_dropped_file(self.compress_input, paths, {".pdf"}))
        row = QHBoxLayout(); row.addWidget(self.compress_input, 1); row.addWidget(self._button("Browse...", lambda: self._choose_file(self.compress_input, PDF_FILTER)))
        box.addLayout(row)
        self.compress_output = DropLineEdit(); self.compress_output.setPlaceholderText("Output PDF path (choose where to save)")
        self.compress_output.paths_dropped.connect(lambda paths: self.set_dropped_output(self.compress_output, paths, "compressed.pdf"))
        out = QHBoxLayout(); out.addWidget(self.compress_output, 1); out.addWidget(self._button("Save As...", self.choose_compress_output))
        box.addLayout(out)
        target = QHBoxLayout()
        target.addWidget(QLabel("Reduce file size by:"))
        self.compress_target = QDoubleSpinBox()
        self.compress_target.setRange(1.0, 95.0)
        self.compress_target.setValue(50.0)
        self.compress_target.setDecimals(0)
        self.compress_target.setSuffix(" %")
        self.compress_target.setToolTip("The app tries to reduce the original file by this percentage.")
        target.addWidget(self.compress_target)
        target.addStretch()
        box.addLayout(target)
        note = QLabel("The app uses Ghostscript when available, then an offline image-based fallback if needed. The fallback reaches smaller sizes but makes pages image-based rather than searchable. Exact reduction is not always possible for already-optimized PDFs.")
        note.setWordWrap(True); note.setObjectName("hint")
        box.addWidget(note)
        box.addWidget(self._button("Compress PDF", self.compress_pdf, True))
        box.addStretch()
        return card

    def log(self, message: str) -> None:
        self.status.append(message)
        self.status.verticalScrollBar().setValue(self.status.verticalScrollBar().maximum())

    def error(self, message: str) -> None:
        self.log("Error: " + message)
        explanation = self.error_explanation(message)
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("PDF Studio - Help with this error")
        dialog.setText(f"The requested PDF task could not be completed.\n\nHow to fix it:\n{explanation}")
        dialog.setInformativeText("Use Show Details below only if you need the exact technical error message.")
        dialog.setDetailedText(f"Technical details:\n{message}")
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.exec()

    @staticmethod
    def error_explanation(message: str) -> str:
        text = message.lower()
        if "permission denied" in text or "access is denied" in text:
            return "Windows or OneDrive blocked access to this location. Choose a different output folder, close any program using the file, and try again."
        if "libreoffice" in text:
            return "Office-to-PDF needs LibreOffice. Choose Install when prompted, then reopen PDF Studio and repeat the conversion."
        if "tesseract" in text or "ocr" in text:
            return "This scanned PDF needs OCR. Choose Install when prompted, then try the editable Word or PowerPoint conversion again."
        if "password" in text or "encrypted" in text:
            return "This PDF is password-protected. Enter the correct password when prompted, or use an unlocked copy of the file."
        if "no module named" in text or "conversion package" in text:
            return "A required conversion component is missing. Choose Install when prompted, then repeat the task after installation completes."
        if "no tables" in text:
            return "No readable tables were found in the PDF. Try a PDF with selectable table text, or convert a scanned PDF after OCR."
        if "output" in text and "path" in text:
            return "Choose a valid output file or folder. Do not use the same path as the source PDF."
        return "Check that the selected files exist, are not open in another program, and that you can write to the output folder. Expand Technical details below if you need the exact system message."

    def set_dropped_file(self, field: QLineEdit, paths: list[str], allowed: set[str]) -> None:
        path = Path(paths[0]) if paths else None
        if not path or not path.is_file() or path.suffix.lower() not in allowed:
            self.error(f"Drop a supported file: {', '.join(sorted(allowed))}")
            return
        field.setText(str(path))
        self.log(f"Added by drag and drop: {path.name}")

    def set_dropped_folder(self, field: QLineEdit, paths: list[str]) -> None:
        path = Path(paths[0]) if paths else None
        if not path:
            return
        folder = path if path.is_dir() else path.parent
        if not folder.is_dir():
            self.error("Drop a valid folder or a file from the desired output folder.")
            return
        field.setText(str(folder))
        self.log(f"Output folder selected by drag and drop: {folder}")

    def set_dropped_output(self, field: QLineEdit, paths: list[str], default_name: str) -> None:
        path = Path(paths[0]) if paths else None
        if not path:
            return
        if path.is_dir():
            field.setText(str(path / default_name))
        elif path.parent.is_dir():
            field.setText(str(path.with_suffix(".pdf")))
        else:
            self.error("Drop a folder or a file from the desired output location.")
            return
        self.log(f"Output location selected by drag and drop: {field.text()}")

    def add_merge_paths(self, paths: list[str]) -> None:
        added = 0
        for value in paths:
            path = Path(value)
            if path.is_file() and path.suffix.lower() == ".pdf":
                self.merge_list.addItem(str(path)); added += 1
        if added:
            self.log(f"Added {added} PDF file(s) by drag and drop.")
        else:
            self.error("Drop one or more PDF files to merge.")

    def add_image_paths(self, paths: list[str]) -> None:
        allowed = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
        added = 0
        for value in paths:
            path = Path(value)
            if path.is_file() and path.suffix.lower() in allowed:
                self.image_pdf_list.addItem(str(path)); added += 1
        if added:
            self.log(f"Added {added} image file(s) by drag and drop.")
        else:
            self.error("Drop one or more JPEG, PNG, BMP, or TIFF image files.")

    def optional_module(self, module_name: str, package_name: str):
        """Load a conversion package, offering a one-time install for .py runs."""
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError:
            if getattr(sys, "frozen", False):
                raise RuntimeError(f"The bundled application is missing {package_name}. Rebuild the EXE with this package included.")
            choice = QMessageBox.question(
                self, "Install conversion component",
                f"{package_name} is needed for this conversion and is not installed.\n\nInstall it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if choice != QMessageBox.StandardButton.Yes:
                raise RuntimeError(f"{package_name} was not installed. Run: {sys.executable} -m pip install {package_name}")
            self.log(f"Installing {package_name}; this only happens once.")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f"Could not install {package_name}. Check your internet connection, then run: {sys.executable} -m pip install {package_name}") from exc
            return importlib.import_module(module_name)

    def add_merge_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Choose PDFs", "", PDF_FILTER)
        if paths:
            self.add_merge_paths(paths)

    def remove_merge_file(self) -> None:
        for item in self.merge_list.selectedItems():
            self.merge_list.takeItem(self.merge_list.row(item))

    def move_merge(self, delta: int) -> None:
        row = self.merge_list.currentRow()
        dest = row + delta
        if row >= 0 and 0 <= dest < self.merge_list.count():
            item = self.merge_list.takeItem(row)
            self.merge_list.insertItem(dest, item)
            self.merge_list.setCurrentRow(dest)

    def choose_merge_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save merged PDF", "merged.pdf", PDF_FILTER)
        if path: self.merge_output.setText(self.ensure_suffix(path, ".pdf"))

    def choose_compress_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save compressed PDF", "compressed.pdf", PDF_FILTER)
        if path: self.compress_output.setText(self.ensure_suffix(path, ".pdf"))

    def add_images_for_pdf(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Choose images", "", IMAGE_FILTER)
        if paths:
            self.add_image_paths(paths)

    def remove_image(self) -> None:
        for item in self.image_pdf_list.selectedItems():
            self.image_pdf_list.takeItem(self.image_pdf_list.row(item))

    def move_image(self, delta: int) -> None:
        row = self.image_pdf_list.currentRow()
        destination = row + delta
        if row >= 0 and 0 <= destination < self.image_pdf_list.count():
            item = self.image_pdf_list.takeItem(row)
            self.image_pdf_list.insertItem(destination, item)
            self.image_pdf_list.setCurrentRow(destination)

    def choose_image_pdf_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save combined image PDF", "images_combined.pdf", PDF_FILTER)
        if path: self.image_pdf_output.setText(self.ensure_suffix(path, ".pdf"))

    @staticmethod
    def ensure_suffix(path: str, suffix: str) -> str:
        return path if path.lower().endswith(suffix) else path + suffix

    @staticmethod
    def check_file(value: str, extension: str | None = None) -> Path:
        path = Path(value.strip())
        if not path.is_file(): raise ValueError("Please choose an existing file.")
        if extension and path.suffix.lower() != extension: raise ValueError(f"Please choose a {extension} file.")
        return path

    def pdf_password(self, path: Path) -> str | None:
        """Return and validate a PDF password only when the selected PDF needs one."""
        key = str(path.resolve())
        reader = PdfReader(str(path))
        if not reader.is_encrypted:
            return None
        if key in self.pdf_passwords:
            return self.pdf_passwords[key]
        password, accepted = QInputDialog.getText(
            self, "Password-protected PDF", f"Enter the password for:\n{path.name}",
            QLineEdit.EchoMode.Password,
        )
        if not accepted or not password:
            raise ValueError("A password is required to open this protected PDF.")
        if not reader.decrypt(password):
            raise ValueError("The PDF password is incorrect.")
        self.pdf_passwords[key] = password
        return password

    def open_pdf_reader(self, path: Path) -> PdfReader:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            password = self.pdf_password(path)
            if not password or not reader.decrypt(password):
                raise ValueError("The PDF password is incorrect.")
        return reader

    def open_fitz_pdf(self, fitz, path: Path):
        document = fitz.open(str(path))
        if document.needs_pass:
            password = self.pdf_password(path)
            if not password or not document.authenticate(password):
                document.close()
                raise ValueError("The PDF password is incorrect.")
        return document

    def merge_pdfs(self) -> None:
        try:
            paths = [Path(self.merge_list.item(i).text()) for i in range(self.merge_list.count())]
            if len(paths) < 2: raise ValueError("Add at least two PDF files to merge.")
            if not all(p.is_file() and p.suffix.lower() == ".pdf" for p in paths): raise ValueError("All selected files must be existing PDFs.")
            output = Path(self.merge_output.text().strip())
            if not output.name: raise ValueError("Choose an output PDF path.")
            output = Path(self.ensure_suffix(str(output), ".pdf")); output.parent.mkdir(parents=True, exist_ok=True)
            writer = PdfWriter()
            for path in paths: writer.append(self.open_pdf_reader(path))
            with output.open("wb") as f: writer.write(f)
            self.log(f"Merged {len(paths)} files successfully: {output}")
        except Exception as exc: self.error(str(exc))

    def parse_ranges(self, text: str, page_count: int) -> list[tuple[int, int]]:
        if not text.strip(): return [(i, i) for i in range(1, page_count + 1)]
        result = []
        for part in text.split(","):
            match = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", part)
            if not match: raise ValueError(f"Invalid page range: '{part.strip()}'.")
            start, end = int(match.group(1)), int(match.group(2) or match.group(1))
            if start < 1 or end < start or end > page_count: raise ValueError(f"Range '{part.strip()}' is outside 1-{page_count}.")
            result.append((start, end))
        return result

    def split_pdf(self) -> None:
        try:
            source = self.check_file(self.split_input.text(), ".pdf")
            folder_text = self.split_folder.text().strip()
            if not folder_text: raise ValueError("Choose an output folder.")
            folder = Path(folder_text)
            folder.mkdir(parents=True, exist_ok=True)
            reader = self.open_pdf_reader(source)
            ranges = self.parse_ranges(self.page_ranges.text(), len(reader.pages))
            for index, (start, end) in enumerate(ranges, 1):
                writer = PdfWriter()
                for number in range(start - 1, end): writer.add_page(reader.pages[number])
                target = folder / f"{source.stem}_pages_{start}-{end}.pdf"
                with target.open("wb") as f: writer.write(f)
            self.log(f"Created {len(ranges)} split PDF file(s) in: {folder}")
        except Exception as exc: self.error(str(exc))

    def conversion_output(self, source: Path, suffix: str) -> Path:
        folder = Path(self.convert_folder.text().strip()) if self.convert_folder.text().strip() else source.parent
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{source.stem}_converted{suffix}"

    def convert(self, target: str) -> None:
        try:
            source = self.check_file(self.convert_input.text())
            if target == "pdf":
                if source.suffix.lower() not in {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}: raise ValueError("Office to PDF accepts Word, Excel, or PowerPoint files.")
                output = self.office_to_pdf(source)
            else:
                if source.suffix.lower() != ".pdf": raise ValueError("PDF conversion buttons require a PDF source file.")
                output = {"docx": self.pdf_to_docx, "xlsx": self.pdf_to_xlsx,
                          "pptx": self.pdf_to_pptx, "jpg": self.pdf_to_jpegs}[target](source)
            self.log(f"Conversion complete: {output}")
        except ImportError as exc:
            self.error(f"A conversion package is missing: {exc}. Run: pip install -r requirements.txt")
        except Exception as exc:
            self.log(traceback.format_exc(limit=1))
            self.error(str(exc))

    def pdf_to_docx(self, source: Path) -> Path:
        if self.office_conversion_mode.currentData() == "layout":
            return self.pdf_to_docx_layout(source)
        fitz = self.optional_module("fitz", "PyMuPDF")
        Document = self.optional_module("docx", "python-docx").Document
        folder = Path(self.convert_folder.text().strip()) if self.convert_folder.text().strip() else source.parent
        folder.mkdir(parents=True, exist_ok=True)
        output = folder / f"{source.stem}_editable.docx"
        pdf = self.open_fitz_pdf(fitz, source)
        word = Document()
        used_ocr = False
        try:
            for page_number, page in enumerate(pdf, 1):
                text = page.get_text("text").strip()
                if not text:
                    text = self.ocr_page_to_text(page)
                    used_ocr = True
                for paragraph in text.split("\n\n"):
                    cleaned = paragraph.strip()
                    if cleaned:
                        word.add_paragraph(cleaned)
                if page_number < len(pdf):
                    word.add_page_break()
            word.save(str(output))
        finally:
            pdf.close()
        method = "OCR text" if used_ocr else "selectable PDF text"
        self.log(f"Created a text-only editable Word document using {method}. No PDF page images were inserted.")
        return output

    def pdf_to_docx_layout(self, source: Path) -> Path:
        """Use pdf2docx's layout-focused converter for the closest Word appearance."""
        Converter = self.optional_module("pdf2docx", "pdf2docx").Converter
        folder = Path(self.convert_folder.text().strip()) if self.convert_folder.text().strip() else source.parent
        folder.mkdir(parents=True, exist_ok=True)
        output = folder / f"{source.stem}_format_preserved.docx"
        converter = Converter(str(source), password=self.pdf_password(source))
        try:
            converter.convert(str(output))
        finally:
            converter.close()
        self.log("Created a format-preserved Word document. Complex or scanned PDF areas can remain image-based to keep their original appearance.")
        return output

    def ocr_page_to_text(self, page) -> str:
        """OCR an image-only page into editable text, without putting that image into Word."""
        executable = self.find_tesseract()
        if not executable:
            choice = QMessageBox.question(
                self, "Install OCR support",
                "This scanned PDF needs Tesseract OCR to create editable Word text.\n\n"
                "Install Tesseract OCR now? This is a one-time setup.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if choice != QMessageBox.StandardButton.Yes:
                raise RuntimeError("OCR support was not installed. Select PDF to Editable Word again and choose Install when prompted.")
            self.log("Installing Tesseract OCR. Please wait; this only happens once.")
            try:
                result = subprocess.run(
                    ["winget", "install", "--id", "UB-Mannheim.TesseractOCR", "-e",
                     "--accept-package-agreements", "--accept-source-agreements"],
                    capture_output=True, text=True, timeout=300,
                )
            except FileNotFoundError as exc:
                raise RuntimeError("Windows App Installer (winget) is unavailable. Install Tesseract OCR from https://github.com/UB-Mannheim/tesseract/wiki, then try again.") from exc
            if result.returncode:
                detail = (result.stderr or result.stdout or "Windows could not complete the installation.").strip()
                raise RuntimeError(f"Tesseract OCR could not be installed: {detail}")
            executable = self.find_tesseract()
            if not executable:
                raise RuntimeError("Tesseract was installed but is not yet available. Close and reopen PDF Studio, then try again.")
        pytesseract = self.optional_module("pytesseract", "pytesseract")
        Image = self.optional_module("PIL.Image", "Pillow")
        pytesseract.pytesseract.tesseract_cmd = executable
        pixmap = page.get_pixmap(dpi=200, alpha=False)
        image = Image.open(BytesIO(pixmap.tobytes("png")))
        text = pytesseract.image_to_string(image, lang="eng")
        if not text.strip():
            raise RuntimeError("OCR could not detect readable text on this page. Try a clearer scan at higher resolution.")
        return text

    @staticmethod
    def find_tesseract() -> str | None:
        executable = shutil.which("tesseract")
        standard_location = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        return executable or (str(standard_location) if standard_location.is_file() else None)

    def pdf_to_xlsx(self, source: Path) -> Path:
        pdfplumber = self.optional_module("pdfplumber", "pdfplumber")
        Workbook = self.optional_module("openpyxl", "openpyxl").Workbook
        Font = self.optional_module("openpyxl.styles", "openpyxl").Font
        PatternFill = self.optional_module("openpyxl.styles", "openpyxl").PatternFill
        get_column_letter = self.optional_module("openpyxl.utils", "openpyxl").get_column_letter
        output = self.conversion_output(source, ".xlsx")
        layout = self.excel_layout.currentData()
        book = Workbook()
        combined = book.active
        combined.title = "All Tables"
        if layout == "multiple":
            book.remove(combined)
        found = 0
        with pdfplumber.open(str(source), password=self.pdf_password(source)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                for table_num, table in enumerate(tables, 1):
                    if layout == "multiple":
                        sheet = book.create_sheet(f"Page {page_num} Table {table_num}"[:31])
                    else:
                        sheet = combined
                        heading = sheet.cell(row=sheet.max_row + 1, column=1,
                                             value=f"Page {page_num} - Table {table_num}")
                        heading.font = Font(bold=True, color="FFFFFF")
                        heading.fill = PatternFill("solid", fgColor="305496")
                    for row in table: sheet.append([cell or "" for cell in row])
                    if layout == "single":
                        sheet.append([])  # Separate consecutive tables clearly.
                    found += 1
        if not found: raise ValueError("No tables were detected in this PDF. Try a PDF containing clear, selectable tables.")
        for sheet in book.worksheets:
            for column in range(1, sheet.max_column + 1):
                widest = max((len(str(sheet.cell(row, column).value or "")) for row in range(1, sheet.max_row + 1)), default=0)
                sheet.column_dimensions[get_column_letter(column)].width = min(max(widest + 2, 10), 45)
        book.save(str(output)); return output

    def pdf_to_pptx(self, source: Path) -> Path:
        if self.office_conversion_mode.currentData() == "layout":
            return self.pdf_to_pptx_layout(source)
        fitz = self.optional_module("fitz", "PyMuPDF")
        Presentation = self.optional_module("pptx", "python-pptx").Presentation
        pptx_util = self.optional_module("pptx.util", "python-pptx")
        RGBColor = self.optional_module("pptx.dml.color", "python-pptx").RGBColor
        Inches, Pt = pptx_util.Inches, pptx_util.Pt
        output = self.conversion_output(source, ".pptx")
        doc = self.open_fitz_pdf(fitz, source); presentation = Presentation()
        presentation.slide_width, presentation.slide_height = Inches(13.333), Inches(7.5)
        blank = presentation.slide_layouts[6]
        for page in doc:
            slide = presentation.slides.add_slide(blank)
            page_width, page_height = page.rect.width / 72, page.rect.height / 72
            slide_width, slide_height = presentation.slide_width / 914400, presentation.slide_height / 914400
            scale = min(slide_width / page_width, slide_height / page_height)
            offset_x = (slide_width - page_width * scale) / 2
            offset_y = (slide_height - page_height * scale) / 2
            text_dict = page.get_text("dict")
            spans = [span for block in text_dict["blocks"] if block["type"] == 0
                     for line in block["lines"] for span in line["spans"] if span["text"].strip()]

            # Render all non-text page artwork as the exact original background.
            # Text objects are removed first, then re-created as editable PowerPoint text.
            background = fitz.open()
            background.insert_pdf(doc, from_page=page.number, to_page=page.number)
            background_page = background[0]
            for span in spans:
                background_page.add_redact_annot(fitz.Rect(span["bbox"]), fill=None, cross_out=False)
            if spans:
                background_page.apply_redactions(images=0, graphics=0)
            background_pixmap = background_page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            slide.shapes.add_picture(
                BytesIO(background_pixmap.tobytes("png")), Inches(offset_x), Inches(offset_y),
                width=Inches(page_width * scale), height=Inches(page_height * scale),
            )
            background.close()

            if not spans:
                # OCR text is still editable. The original scan stays visible as the background.
                spans = [{"bbox": (36, 36, page.rect.width - 36, page.rect.height - 36),
                          "text": self.ocr_page_to_text(page), "size": 12, "font": "Arial", "color": 0}]
            for span in spans:
                x0, y0, x1, y1 = span["bbox"]
                text = span["text"].strip()
                box = slide.shapes.add_textbox(
                    Inches(offset_x + (x0 / 72) * scale),
                    Inches(offset_y + (y0 / 72) * scale),
                    Inches(max(.15, ((x1 - x0) / 72) * scale)),
                    Inches(max(.15, ((y1 - y0) / 72) * scale)),
                )
                frame = box.text_frame
                frame.clear()
                frame.word_wrap = True
                paragraph = frame.paragraphs[0]
                paragraph.text = text
                font = paragraph.font
                font.size = Pt(max(6, min(40, span.get("size", 12) * scale)))
                font.name = span.get("font", "Arial")
                font.bold = "bold" in span.get("font", "").lower()
                font.italic = "italic" in span.get("font", "").lower()
                colour = span.get("color", 0)
                font.color.rgb = RGBColor((colour >> 16) & 255, (colour >> 8) & 255, colour & 255)
        if not doc.page_count: raise ValueError("The PDF has no pages.")
        presentation.save(str(output)); doc.close()
        self.log("Created a format-preserving editable PowerPoint. Original non-text artwork is retained as the slide background, and PDF text is recreated as editable text boxes.")
        return output

    def pdf_to_pptx_layout(self, source: Path) -> Path:
        """Create visually identical slides for users prioritizing original formatting."""
        fitz = self.optional_module("fitz", "PyMuPDF")
        Presentation = self.optional_module("pptx", "python-pptx").Presentation
        Inches = self.optional_module("pptx.util", "python-pptx").Inches
        output = self.conversion_output(source, ".pptx").with_name(f"{source.stem}_format_preserved.pptx")
        doc, presentation = self.open_fitz_pdf(fitz, source), Presentation()
        try:
            presentation.slide_width, presentation.slide_height = Inches(13.333), Inches(7.5)
            blank = presentation.slide_layouts[6]
            for page in doc:
                slide = presentation.slides.add_slide(blank)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(1.8, 1.8), alpha=False)
                slide.shapes.add_picture(BytesIO(pixmap.tobytes("png")), 0, 0,
                                         width=presentation.slide_width, height=presentation.slide_height)
            if not len(doc):
                raise ValueError("The PDF has no pages.")
            presentation.save(str(output))
        finally:
            doc.close()
        self.log("Created a format-preserved PowerPoint. Slides use page images so they look like the PDF; choose Editable text mode when you need to modify text.")
        return output

    def pdf_to_jpegs(self, source: Path) -> Path:
        fitz = self.optional_module("fitz", "PyMuPDF")
        Image = self.optional_module("PIL.Image", "Pillow")
        folder = Path(self.convert_folder.text().strip()) if self.convert_folder.text().strip() else source.parent
        folder.mkdir(parents=True, exist_ok=True)
        doc = self.open_fitz_pdf(fitz, source)
        page_count = len(doc)
        try:
            if not page_count:
                raise ValueError("The PDF has no pages.")
            for page_number, page in enumerate(doc, 1):
                pixmap = page.get_pixmap(dpi=200, alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                image.save(str(folder / f"{source.stem}_page_{page_number:03d}.jpg"), "JPEG", quality=95, optimize=True)
        finally:
            doc.close()
        self.log(f"Exported {page_count} JPEG image(s) to: {folder}")
        return folder

    def images_to_pdf(self) -> None:
        try:
            paths = [Path(self.image_pdf_list.item(i).text()) for i in range(self.image_pdf_list.count())]
            if not paths:
                raise ValueError("Add one or more JPEG/image files first.")
            if not all(path.is_file() for path in paths):
                raise ValueError("One or more selected image files cannot be found.")
            output = Path(self.image_pdf_output.text().strip())
            if not output.name:
                raise ValueError("Choose where to save the combined PDF.")
            output = Path(self.ensure_suffix(str(output), ".pdf"))
            output.parent.mkdir(parents=True, exist_ok=True)
            Image = self.optional_module("PIL.Image", "Pillow")
            images = []
            try:
                for path in paths:
                    with Image.open(path) as image:
                        images.append(image.convert("RGB"))
                images[0].save(str(output), "PDF", resolution=150.0, save_all=True, append_images=images[1:])
            finally:
                for image in images:
                    image.close()
            self.log(f"Combined {len(paths)} image(s) into PDF: {output}")
        except Exception as exc:
            self.error(str(exc))

    def office_to_pdf(self, source: Path) -> Path:
        libreoffice = self.find_libreoffice()
        if not libreoffice:
            choice = QMessageBox.question(
                self, "Install LibreOffice",
                "LibreOffice is needed to convert Word, Excel, and PowerPoint files to PDF.\n\n"
                "Install LibreOffice now? This is a one-time setup.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if choice != QMessageBox.StandardButton.Yes:
                raise RuntimeError("LibreOffice was not installed. Select Office to PDF again and choose Install when prompted.")
            self.log("Installing LibreOffice. Please wait; this only happens once.")
            try:
                result = subprocess.run(
                    ["winget", "install", "--id", "TheDocumentFoundation.LibreOffice", "-e",
                     "--accept-package-agreements", "--accept-source-agreements"],
                    capture_output=True, text=True, timeout=600,
                )
            except FileNotFoundError as exc:
                raise RuntimeError("Windows App Installer (winget) is unavailable. Install LibreOffice from https://www.libreoffice.org/download/, then try again.") from exc
            if result.returncode:
                detail = (result.stderr or result.stdout or "Windows could not complete the installation.").strip()
                raise RuntimeError(f"LibreOffice could not be installed: {detail}")
            libreoffice = self.find_libreoffice()
            if not libreoffice:
                raise RuntimeError("LibreOffice was installed but is not yet available. Close and reopen PDF Studio, then try again.")
        output = self.conversion_output(source, ".pdf")
        # A fresh visible folder avoids OneDrive/Windows locks on a reused hidden folder.
        temp_dir = output.parent / f"PDFStudio_LibreOffice_{uuid.uuid4().hex}"
        try:
            temp_dir.mkdir(parents=True, exist_ok=False)
            result = subprocess.run(
                [libreoffice, "--headless", "--convert-to", "pdf", "--outdir", str(temp_dir), str(source)],
                capture_output=True, text=True, timeout=180,
            )
            generated = temp_dir / f"{source.stem}.pdf"
            if result.returncode or not generated.exists():
                raise RuntimeError("LibreOffice could not convert this file: " + (result.stderr or result.stdout).strip())
            shutil.move(str(generated), str(output))
            return output
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def find_libreoffice() -> str | None:
        candidates = [
            shutil.which("soffice"), shutil.which("libreoffice"),
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        return next((path for path in candidates if path and Path(path).is_file()), None)

    def compress_pdf(self) -> None:
        try:
            source = self.check_file(self.compress_input.text(), ".pdf")
            output = Path(self.compress_output.text().strip())
            if not output.name: raise ValueError("Choose an output PDF path.")
            output = Path(self.ensure_suffix(str(output), ".pdf")); output.parent.mkdir(parents=True, exist_ok=True)
            if source.resolve() == output.resolve():
                raise ValueError("Choose a different output name so the original PDF is kept safe.")
            reduction = self.compress_target.value()
            target_bytes = int(source.stat().st_size * (1 - reduction / 100))
            self.log(f"Trying to reduce the original file by {reduction:.0f}%. This can take a moment for large PDFs.")
            actual_size, method, hit_target = self.compress_to_target(source, output, target_bytes)
            size_mb = actual_size / 1024 / 1024
            actual_reduction = (1 - actual_size / source.stat().st_size) * 100
            message = f"Compressed with {method}: {size_mb:.2f} MB ({actual_reduction:.1f}% smaller) - {output}"
            if not hit_target:
                message += f" (closest achievable result; requested reduction was {reduction:.0f}%)"
            self.log(message)
        except Exception as exc: self.error(str(exc))

    @staticmethod
    def _register_candidate(candidate: Path, best: Path | None, best_size: int | None,
                            target_bytes: int) -> tuple[Path, int, bool]:
        size = candidate.stat().st_size
        if size <= target_bytes:
            return candidate, size, True
        if best is None or size < best_size:
            return candidate, size, False
        return best, best_size, False

    def compress_to_target(self, source: Path, output: Path, target_bytes: int) -> tuple[int, str, bool]:
        """Create candidates, stopping at the first one meeting the user target."""
        import fitz
        best: Path | None = None
        best_size: int | None = None
        best_method = "optimized PDF save"
        # Candidate PDFs live beside the output rather than in Windows' restricted
        # temporary folders. They are removed after the chosen result is copied.
        run_id = uuid.uuid4().hex
        temp = output.parent
        try:
            # First, losslessly repack the original file. This preserves text and links.
            optimized = temp / f"pdfstudio_{run_id}_optimized.pdf"
            document = self.open_fitz_pdf(fitz, source)
            try:
                document.save(str(optimized), garbage=4, deflate=True, deflate_images=True,
                              deflate_fonts=True, use_objstms=1)
            finally:
                document.close()
            best, best_size, met = self._register_candidate(optimized, best, best_size, target_bytes)
            if met:
                shutil.copy2(best, output); return best_size, "optimized PDF save", True

            ghostscript = shutil.which("gswin64c") or shutil.which("gswin32c") or shutil.which("gs")
            if ghostscript:
                for dpi, quality in ((150, 85), (120, 75), (96, 65), (72, 55)):
                    candidate = temp / f"pdfstudio_{run_id}_ghostscript_{dpi}.pdf"
                    command = [ghostscript, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
                               "-dNOPAUSE", "-dQUIET", "-dBATCH", "-dAutoRotatePages=/None",
                               "-dDownsampleColorImages=true", "-dDownsampleGrayImages=true",
                               "-dDownsampleMonoImages=true", f"-dColorImageResolution={dpi}",
                               f"-dGrayImageResolution={dpi}", "-dMonoImageResolution=150",
                               f"-dJPEGQ={quality}", f"-sOutputFile={candidate}", str(source)]
                    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
                    if result.returncode or not candidate.exists():
                        continue
                    selected, size, met = self._register_candidate(candidate, best, best_size, target_bytes)
                    if selected == candidate: best, best_size, best_method = candidate, size, f"Ghostscript at {dpi} DPI"
                    if met:
                        shutil.copy2(candidate, output); return size, f"Ghostscript at {dpi} DPI", True

            # Offline final fallback: re-render each page as a JPEG. It gives predictable
            # size reduction but intentionally trades selectable text for compact pages.
            for dpi, quality in ((150, 82), (120, 70), (100, 60), (85, 50), (72, 40)):
                candidate = temp / f"pdfstudio_{run_id}_raster_{dpi}.pdf"
                original, rebuilt = self.open_fitz_pdf(fitz, source), fitz.open()
                try:
                    for page in original:
                        new_page = rebuilt.new_page(width=page.rect.width, height=page.rect.height)
                        pixmap = page.get_pixmap(dpi=dpi, alpha=False)
                        new_page.insert_image(new_page.rect, stream=pixmap.tobytes("jpeg", jpg_quality=quality))
                    rebuilt.save(str(candidate), garbage=4, deflate=True, use_objstms=1)
                finally:
                    rebuilt.close(); original.close()
                selected, size, met = self._register_candidate(candidate, best, best_size, target_bytes)
                if selected == candidate: best, best_size, best_method = candidate, size, f"offline raster compression at {dpi} DPI"
                if met:
                    shutil.copy2(candidate, output); return size, f"offline raster compression at {dpi} DPI", True

            if best is None or best_size is None:
                raise RuntimeError("No compressed output could be created from this PDF.")
            shutil.copy2(best, output)
            return best_size, best_method, False
        finally:
            for candidate in temp.glob(f"pdfstudio_{run_id}_*.pdf"):
                try:
                    candidate.unlink()
                except OSError:
                    pass


STYLE = """
QMainWindow { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #25154a, stop:.48 #163b72, stop:1 #0e776f); }
QLabel { color: #f8f6ff; font-size: 14px; } QLabel#title { font: bold 30px 'Segoe UI'; letter-spacing: 2px; } QLabel#subtitle, QLabel#hint { color: #d3d9ef; }
QFrame#card { background: rgba(13, 20, 57, 220); border: 1px solid #5968a5; border-radius: 16px; }
QTabWidget::pane { border: 0; } QTabBar::tab { background: #263562; color: #e9edff; padding: 11px 17px; border-radius: 8px; margin-right: 5px; } QTabBar::tab:selected { background: #f36ca4; color: white; font-weight: bold; }
QLineEdit, QListWidget, QTextEdit { background: #101a3d; color: #f7f8ff; border: 1px solid #56669c; border-radius: 8px; padding: 9px; selection-background-color: #f36ca4; }
QPushButton { background: #3d5290; color: white; border: 0; border-radius: 8px; padding: 10px 14px; font-weight: 600; } QPushButton:hover { background: #5970b8; } QPushButton#accent { background: #f2649e; } QPushButton#accent:hover { background: #ff8b49; }
QTextEdit#status { background: rgba(7, 11, 33, 205); border: 1px solid #42517f; color: #c9f6de; font-family: Consolas; font-size: 11px; }
"""


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    app.setFont(QFont("Segoe UI", 10))
    window = PDFStudio(); window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
