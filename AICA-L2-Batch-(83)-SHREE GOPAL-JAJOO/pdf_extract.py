"""
pdf_extract.py
--------------
Extracts plain text from a text-based LC PDF.

Only text-based PDFs are supported (i.e. PDFs where the text can normally be
selected/copied in a PDF viewer - this covers the great majority of bank
issued / SWIFT-generated LC copies). Scanned image-only PDFs are not
supported in this version and will raise a PDFTextNotFoundError with a
clear message so the GUI can show it to the user.
"""

from __future__ import annotations

import os


class PDFExtractError(Exception):
    """Raised when the PDF cannot be opened at all."""


class PDFTextNotFoundError(Exception):
    """Raised when the PDF opens fine but contains no extractable text
    (most likely a scanned/image-only PDF, which is not supported)."""


def _extract_with_pymupdf(pdf_path: str) -> Optional[str]:
    """Try extracting text using PyMuPDF (natively handles encrypted/AES PDFs)."""
    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        pages_text = []
        for page in doc:
            pages_text.append(page.get_text() or "")
        full = "\f".join(pages_text)
        if full.strip():
            return full
    except Exception:
        pass
    return None


def _extract_with_pypdf(pdf_path: str) -> Optional[str]:
    """Extract text using pypdf, attempting empty-password decryption for encrypted PDFs."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception:
                pass
        pages_text = []
        for page in reader.pages:
            try:
                pages_text.append(page.extract_text() or "")
            except Exception:
                pages_text.append("")
        full = "\f".join(pages_text)
        if full.strip():
            return full
    except Exception:
        pass
    return None


def _extract_with_ocr(pdf_path: str) -> Optional[str]:
    """Fallback OCR extraction for scanned/image-only PDFs using Windows native OCR."""
    try:
        import io
        from PIL import Image
        import pymupdf
        import winocr

        doc = pymupdf.open(pdf_path)
        pages_text = []
        for page in doc:
            pix = page.get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            res = winocr.recognize_pil_sync(img, lang="en")
            t = res.get("text", "") if isinstance(res, dict) else ""
            pages_text.append(t)
        full = "\f".join(pages_text)
        if full.strip():
            return full
    except Exception:
        pass
    return None


def extract_text(pdf_path: str) -> str:
    """
    Extract and return the full text of a PDF, page by page, separated by
    a form-feed marker so downstream code can still tell where pages
    changed if it ever needs to.
    
    Supports:
      1. PyMuPDF (fast, robust, natively handles AES/encrypted bank PDFs)
      2. pypdf (with decryption support)
      3. Windows native OCR fallback for scanned/image-only PDFs
    """
    if not os.path.isfile(pdf_path):
        raise PDFExtractError(f"File not found: {pdf_path}")

    # Strategy 1: PyMuPDF
    text = _extract_with_pymupdf(pdf_path)
    if text and text.strip():
        return text

    # Strategy 2: pypdf
    text = _extract_with_pypdf(pdf_path)
    if text and text.strip():
        return text

    # Strategy 3: OCR for scanned PDFs
    text = _extract_with_ocr(pdf_path)
    if text and text.strip():
        return text

    raise PDFTextNotFoundError(
        "No selectable or recognizable text could be found in this PDF. "
        "It looks like a corrupted, encrypted, or unsupported scanned document. "
        "Please supply a standard text-based or clear scanned PDF copy."
    )


def normalise_text(raw_text: str) -> str:
    """
    Light cleanup that keeps line structure (important for field-tag
    parsing) while collapsing odd whitespace artefacts PDF extraction
    sometimes introduces, and stripping page number footers.
    """
    import re
    text = raw_text.replace("\f", "\n")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Clean out standalone page numbering lines like "Page 1 of 5", "Page 1 of \n 5"
    text = re.sub(r"(?im)^\s*Page\s+\d+\s+of(?:\s+\d+|\s*\n\s*\d+)?\s*$", "", text)

    # collapse runs of 3+ blank lines to a single blank line
    lines = text.split("\n")
    cleaned = []
    blank_run = 0
    for line in lines:
        stripped = line.rstrip()
        if stripped.strip() == "":
            blank_run += 1
            if blank_run <= 1:
                cleaned.append("")
        else:
            blank_run = 0
            cleaned.append(stripped)
    return "\n".join(cleaned).strip("\n")
