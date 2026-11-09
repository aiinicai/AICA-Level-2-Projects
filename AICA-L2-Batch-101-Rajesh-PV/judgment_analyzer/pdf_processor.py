"""PDF validation and text extraction (with OCR fallback for scanned pages).

Text-based pages are read directly with PyMuPDF. Pages that contain little or
no extractable text (typical of scanned judgments) are rendered to an image and
read locally with Tesseract OCR. Nothing in this module sends data anywhere.
"""

from __future__ import annotations

import io
import logging
import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pymupdf as fitz  # PyMuPDF

log = logging.getLogger(__name__)

# A page with fewer meaningful characters than this is treated as "scanned".
MIN_TEXT_CHARS_PER_PAGE = 40
OCR_DPI = 300

ProgressFn = Callable[[int, int, str], None]  # (done, total, message)


class PDFError(Exception):
    """User-facing error about the selected PDF."""


class OCRUnavailableError(PDFError):
    """Tesseract is needed but not installed / not found."""


class CancelledError(Exception):
    """Raised when the user cancels a long-running operation."""


@dataclass
class PageText:
    page_number: int  # 1-based
    text: str
    ocr_used: bool = False


@dataclass
class DocumentInfo:
    path: Path
    file_name: str
    file_size_bytes: int
    page_count: int
    title: str = ""

    @property
    def file_size_display(self) -> str:
        return format_file_size(self.file_size_bytes)


@dataclass
class ExtractedDocument:
    info: DocumentInfo
    pages: list[PageText] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ocr_page_count(self) -> int:
        return sum(1 for p in self.pages if p.ocr_used)

    @property
    def total_chars(self) -> int:
        return sum(len(p.text) for p in self.pages)

    def full_text(self, with_page_markers: bool = True) -> str:
        parts = []
        for page in self.pages:
            if not page.text.strip():
                continue
            if with_page_markers:
                parts.append(f"[Page {page.page_number}]\n{page.text.strip()}")
            else:
                parts.append(page.text.strip())
        return "\n\n".join(parts)


def format_file_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("bytes", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "bytes" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"  # pragma: no cover


def _open_pdf(path: Path) -> fitz.Document:
    try:
        doc = fitz.open(path)
    except Exception as exc:
        raise PDFError(
            "This file could not be opened as a PDF. It may be corrupted or incomplete - "
            "try downloading it again."
        ) from exc
    if not doc.is_pdf:
        doc.close()
        raise PDFError("The selected file is not a PDF document.")
    if doc.needs_pass and not doc.authenticate(""):
        doc.close()
        raise PDFError(
            "This PDF is password-protected. Please remove the password (or print it to a new PDF) "
            "and try again."
        )
    return doc


def validate_pdf(path: str | Path, max_size_mb: int = 200) -> DocumentInfo:
    """Validate the file and return basic information, or raise ``PDFError``."""
    if not path:
        raise PDFError("No file was selected.")
    path = Path(path)
    if not path.exists() or not path.is_file():
        raise PDFError("The selected file could not be found.")
    if path.suffix.lower() != ".pdf":
        raise PDFError("Unsupported file type. Please choose a PDF (.pdf) file.")

    size = path.stat().st_size
    if size == 0:
        raise PDFError("The selected PDF is empty (0 bytes).")
    if size > max_size_mb * 1024 * 1024:
        raise PDFError(f"The PDF is larger than the {max_size_mb} MB limit set in Settings.")

    with path.open("rb") as fh:
        head = fh.read(1024)
    if b"%PDF-" not in head:
        raise PDFError("The file does not look like a valid PDF (missing PDF header). It may be corrupted.")

    doc = _open_pdf(path)
    try:
        page_count = doc.page_count
        if page_count == 0:
            raise PDFError("The PDF contains no pages.")
        # Touch the first page to detect structural corruption early.
        try:
            doc.load_page(0).get_text("text")
        except Exception as exc:
            raise PDFError("The PDF appears to be damaged and its pages cannot be read.") from exc
        title = (doc.metadata or {}).get("title", "") or ""
    finally:
        doc.close()

    return DocumentInfo(
        path=path, file_name=path.name, file_size_bytes=size, page_count=page_count, title=title.strip()
    )


def tesseract_available() -> bool:
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _windows_tesseract_paths() -> list[str]:
    """Common install locations for the UB Mannheim Windows build of Tesseract."""
    import os

    roots = [os.environ.get("ProgramFiles", r"C:\Program Files"),
             os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
             os.environ.get("LOCALAPPDATA", "")]
    paths = [os.path.join(r, "Tesseract-OCR", "tesseract.exe") for r in roots if r]
    paths.append(os.path.join(os.path.expanduser("~"), "scoop", "apps", "tesseract", "current", "tesseract.exe"))
    paths.append(r"C:\ProgramData\chocolatey\bin\tesseract.exe")
    return paths


def configure_tesseract(cmd_path: str | None = None) -> None:
    """Point pytesseract at tesseract: explicit path, else PATH, else common Windows locations."""
    try:
        import pytesseract
    except ImportError:
        return
    if cmd_path and Path(cmd_path).is_file():
        pytesseract.pytesseract.tesseract_cmd = cmd_path
        return
    if shutil.which("tesseract"):
        pytesseract.pytesseract.tesseract_cmd = "tesseract"
        return
    for candidate in _windows_tesseract_paths():
        if Path(candidate).is_file():
            pytesseract.pytesseract.tesseract_cmd = candidate
            return


def text_layer_ratio(info: DocumentInfo, sample_pages: int = 5) -> float:
    """Fraction of sampled pages that have a usable text layer (0.0 = looks scanned)."""
    doc = _open_pdf(info.path)
    try:
        count = min(sample_pages, doc.page_count)
        if count == 0:
            return 0.0
        step = max(1, doc.page_count // count)
        indices = list(range(0, doc.page_count, step))[:count]
        with_text = sum(
            1 for i in indices
            if len(doc.load_page(i).get_text("text").replace(" ", "").strip()) >= MIN_TEXT_CHARS_PER_PAGE
        )
        return with_text / len(indices)
    finally:
        doc.close()


def _ocr_page(page: fitz.Page, language: str) -> str:
    import pytesseract
    from PIL import Image

    pix = page.get_pixmap(dpi=OCR_DPI)
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    try:
        return pytesseract.image_to_string(image, lang=language)
    except pytesseract.TesseractError as exc:
        if "Failed loading language" in str(exc) or "Error opening data file" in str(exc):
            raise PDFError(
                f"Tesseract OCR language data '{language}' is not installed. "
                "Install the language pack or change the OCR language in Analysis Options."
            ) from exc
        raise


def clean_text(text: str) -> str:
    """Normalise whitespace while keeping paragraph breaks."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = text.replace("­", "")  # soft hyphen
    lines = [" ".join(line.split()) for line in text.split("\n")]
    out: list[str] = []
    blank = 0
    for line in lines:
        if line:
            blank = 0
            out.append(line)
        else:
            blank += 1
            if blank == 1:
                out.append("")
    return "\n".join(out).strip()


def extract_text(
    info: DocumentInfo,
    ocr_mode: str = "Auto",
    ocr_language: str = "eng",
    progress: ProgressFn | None = None,
    cancel_event: threading.Event | None = None,
) -> ExtractedDocument:
    """Extract text page by page. ``ocr_mode`` is 'Auto', 'Always' or 'Off'."""
    result = ExtractedDocument(info=info)
    doc = _open_pdf(info.path)
    ocr_ok: bool | None = None  # determined lazily
    ocr_skipped_pages: list[int] = []

    try:
        total = doc.page_count
        for index in range(total):
            if cancel_event is not None and cancel_event.is_set():
                raise CancelledError()
            page = doc.load_page(index)
            number = index + 1
            try:
                text = clean_text(page.get_text("text", sort=True))
            except Exception as exc:
                log.warning("Text layer unreadable on page %d: %s", number, exc)
                text = ""

            needs_ocr = ocr_mode == "Always" or (
                ocr_mode == "Auto" and len(text.replace(" ", "")) < MIN_TEXT_CHARS_PER_PAGE
            )
            used_ocr = False
            if needs_ocr:
                if ocr_ok is None:
                    ocr_ok = tesseract_available()
                if ocr_ok:
                    if progress:
                        progress(index, total, f"Running OCR on page {number} of {total}...")
                    ocr_text = clean_text(_ocr_page(page, ocr_language))
                    if len(ocr_text) >= len(text):
                        text, used_ocr = ocr_text, True
                else:
                    ocr_skipped_pages.append(number)

            result.pages.append(PageText(page_number=number, text=text, ocr_used=used_ocr))
            if progress:
                progress(number, total, f"Read page {number} of {total}")
    finally:
        doc.close()

    if ocr_skipped_pages:
        if result.total_chars < MIN_TEXT_CHARS_PER_PAGE:
            raise OCRUnavailableError(
                "This PDF appears to be scanned (it has no text layer), and Tesseract OCR was not found. "
                "Install Tesseract OCR (see README) and try again."
            )
        result.warnings.append(
            f"{len(ocr_skipped_pages)} page(s) had little or no text and OCR is unavailable: "
            f"{_compress_ranges(ocr_skipped_pages)}. Content from those pages may be missing."
        )

    if result.total_chars < MIN_TEXT_CHARS_PER_PAGE:
        raise PDFError(
            "No readable text could be extracted from this PDF. If it is a scanned image, "
            "check the OCR settings and image quality."
        )
    if result.ocr_page_count:
        result.warnings.append(
            f"OCR was used on {result.ocr_page_count} page(s). OCR can misread names, numbers and "
            "citations - verify critical details against the original."
        )
    log.info(
        "Extracted %d pages (%d via OCR), %d characters.",
        len(result.pages), result.ocr_page_count, result.total_chars,
    )
    return result


def _compress_ranges(numbers: list[int]) -> str:
    """[1,2,3,7,9,10] -> '1-3, 7, 9-10'"""
    if not numbers:
        return ""
    numbers = sorted(set(numbers))
    ranges = []
    start = prev = numbers[0]
    for n in numbers[1:]:
        if n == prev + 1:
            prev = n
            continue
        ranges.append(f"{start}-{prev}" if start != prev else str(start))
        start = prev = n
    ranges.append(f"{start}-{prev}" if start != prev else str(start))
    return ", ".join(ranges)
