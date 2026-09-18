"""Local OCR: turn scanned PDF pages into searchable PDFs, entirely offline.

Uses Tesseract (via ``pytesseract``) -- a real external binary the user must
install, exactly like the Word/LibreOffice dependency in
:mod:`core.word_converter`. No page is ever sent anywhere for OCR; everything
runs on this machine.

A page that already has extractable text is skipped by default (no
duplicate/garbled OCR layer on top of real text), matching the "detect
existing text to avoid duplicate OCR" requirement.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from core.pdf_engine import open_pdf
from utils.logging_utils import get_logger
from utils.validation import ValidationError

logger = get_logger("ocr_engine")

#: Minimum characters of extractable text before a page is considered "already has text".
_TEXT_PRESENCE_THRESHOLD = 20

#: Tesseract language codes this app exposes in the UI; extensible if more language
#: packs are installed (`tesseract --list-langs` shows what's actually available).
SUPPORTED_LANGUAGES = {
    "English": "eng",
    "Hindi": "hin",
    "Kannada": "kan",
}


def find_tesseract(explicit_path: str = "") -> str | None:
    if explicit_path and Path(explicit_path).exists():
        return explicit_path
    candidates = [
        shutil.which("tesseract"),
        shutil.which("tesseract.exe"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def is_tesseract_available(explicit_path: str = "") -> bool:
    return find_tesseract(explicit_path) is not None


def configure_pytesseract(explicit_path: str = ""):
    import pytesseract

    found = find_tesseract(explicit_path)
    if not found:
        raise ValidationError(
            "Tesseract OCR is not installed on this computer. Install it from "
            "https://github.com/UB-Mannheim/tesseract/wiki (Windows build) and try again, "
            "or set its path in Settings -> OCR."
        )
    pytesseract.pytesseract.tesseract_cmd = found
    return pytesseract


def page_has_extractable_text(doc: fitz.Document, page_index: int) -> bool:
    text = doc[page_index].get_text().strip()
    return len(text) >= _TEXT_PRESENCE_THRESHOLD


@dataclass
class WordBox:
    text: str
    x_pt: float
    y_top_pt: float
    width_pt: float
    height_pt: float
    confidence: float


def ocr_page_words(doc: fitz.Document, page_index: int, language: str = "eng", dpi: int = 300, tesseract_path: str = "") -> list[WordBox]:
    """Run OCR on one page and return word-level bounding boxes in PDF point coordinates.

    Note: coordinates are computed for the page's default (unrotated) user
    space, which is correct for the overwhelming majority of scanned pages.
    A page with a non-zero ``/Rotate`` value inherited from the scanner may
    need its rotation normalised first (see :mod:`core.page_organizer`).
    """
    pytesseract = configure_pytesseract(tesseract_path)
    from pytesseract import Output

    page = doc[page_index]
    zoom = dpi / 72.0
    pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

    data = pytesseract.image_to_data(image, lang=language, output_type=Output.DICT)
    words: list[WordBox] = []
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        conf = float(data["conf"][i]) if data["conf"][i] not in ("-1", -1) else -1.0
        if not text or conf < 0:
            continue
        x_px, y_px = float(data["left"][i]), float(data["top"][i])
        w_px, h_px = float(data["width"][i]), float(data["height"][i])
        words.append(
            WordBox(
                text=text,
                x_pt=x_px / zoom,
                y_top_pt=y_px / zoom,
                width_pt=w_px / zoom,
                height_pt=h_px / zoom,
                confidence=conf,
            )
        )
    return words


@dataclass
class OCRResult:
    output_path: str
    pages_ocred: list[int] = field(default_factory=list)
    pages_already_had_text: list[int] = field(default_factory=list)
    average_confidence: float = 0.0
    invisible_text_layer_supported: bool = True


def make_searchable_pdf(
    source_path: str | Path,
    output_path: str | Path,
    language: str = "eng",
    dpi: int = 300,
    skip_pages_with_text: bool = True,
    tesseract_path: str = "",
    page_indices: list[int] | None = None,
) -> OCRResult:
    """Add an invisible, selectable OCR text layer to a scanned PDF, saved as a new file."""
    supports_render_mode = True  # corrected below if this PyMuPDF version lacks the parameter

    with open_pdf(source_path) as doc:
        result = OCRResult(output_path=str(output_path))
        confidences: list[float] = []
        targets = page_indices if page_indices is not None else list(range(doc.page_count))

        for page_index in targets:
            if skip_pages_with_text and page_has_extractable_text(doc, page_index):
                result.pages_already_had_text.append(page_index + 1)
                continue

            words = ocr_page_words(doc, page_index, language=language, dpi=dpi, tesseract_path=tesseract_path)
            page = doc[page_index]
            for word in words:
                confidences.append(word.confidence)
                baseline_y = word.y_top_pt + word.height_pt
                fontsize = max(1.0, word.height_pt * 0.85)
                try:
                    page.insert_text(
                        fitz.Point(word.x_pt, baseline_y),
                        word.text,
                        fontsize=fontsize,
                        fontname="helv",
                        render_mode=3,  # invisible: selectable/searchable, not painted
                    )
                except TypeError:
                    # Older PyMuPDF without render_mode support: fall back to a
                    # normal (visible) text insertion so the page remains
                    # searchable, at the cost of a faint visible text overlay.
                    supports_render_mode = False
                    page.insert_text(fitz.Point(word.x_pt, baseline_y), word.text, fontsize=fontsize, fontname="helv")
            result.pages_ocred.append(page_index + 1)

        result.invisible_text_layer_supported = supports_render_mode
        result.average_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path), garbage=3, deflate=True)

    return result


def extract_text_via_ocr(source_path: str | Path, language: str = "eng", dpi: int = 300, tesseract_path: str = "") -> str:
    """Plain-text extraction for pages with no existing text layer (used to feed AI Assistant features)."""
    with open_pdf(source_path) as doc:
        parts = []
        for i in range(doc.page_count):
            if page_has_extractable_text(doc, i):
                parts.append(doc[i].get_text())
            else:
                words = ocr_page_words(doc, i, language=language, dpi=dpi, tesseract_path=tesseract_path)
                parts.append(" ".join(w.text for w in words))
        return "\n\n".join(parts)
