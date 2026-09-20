"""OCR for scanned invoices (image-only PDFs, and .png/.jpg/.tif files).

Tesseract returns every word with its position on the page, which is exactly what the PDF
reader already works with, so an OCR'd invoice goes through the same grid, the same label
matching and the same validation as a digital one.

Tesseract is an external program. On Windows install it once from the UB Mannheim build
(tesseract-ocr-w64-setup-*.exe) and either accept the default folder or set the path in
Settings; nothing is uploaded anywhere - OCR runs on this computer.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from .logsetup import get_logger

log = get_logger()
OCR_DPI = 300
MIN_CONF = 35                      # ignore words Tesseract is very unsure about

WINDOWS_GUESSES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


class OcrUnavailable(RuntimeError):
    pass


def tesseract_path(configured: str = "") -> str:
    if configured and Path(configured).exists():
        return configured
    found = shutil.which("tesseract")
    if found:
        return found
    if sys.platform.startswith("win"):
        for p in WINDOWS_GUESSES:
            if Path(p).exists():
                return p
    return ""


def ocr_available(configured: str = "") -> bool:
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return bool(tesseract_path(configured))


def _prepare(configured: str):
    try:
        import pytesseract
    except ImportError:
        raise OcrUnavailable("OCR needs the 'pytesseract' package (pip install -r requirements.txt).")
    exe = tesseract_path(configured)
    if not exe:
        raise OcrUnavailable(
            "This invoice is a scan, so it has to be read by OCR, and the Tesseract OCR program is not installed. "
            "Install it once from https://github.com/UB-Mannheim/tesseract/wiki (tesseract-ocr-w64-setup) and try "
            "again; if you installed it elsewhere, give the path in Settings. OCR runs on this computer only.")
    pytesseract.pytesseract.tesseract_cmd = exe
    return pytesseract


def page_images(path, dpi: int = OCR_DPI):
    """Page images for a PDF, or the image file itself."""
    path = Path(path)
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        from PIL import Image
        return [Image.open(str(path))]
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(str(path))
        return [pdf[i].render(scale=dpi / 72).to_pil() for i in range(len(pdf))]
    except ImportError:
        pass
    except Exception as e:
        log.warning("pypdfium2 render failed: %s", e)
    try:
        from pdf2image import convert_from_path
        return convert_from_path(str(path), dpi=dpi)
    except Exception as e:
        raise OcrUnavailable(
            "The scanned PDF could not be turned into images for OCR. Install Poppler (pdf2image) or the "
            f"pypdfium2 package, or save the invoice as an image and try again. ({type(e).__name__})") from e


def ocr_pages(path, configured_exe: str = "") -> list[dict]:
    """Returns the same structure the PDF reader uses: one entry per page with its text lines."""
    pytesseract = _prepare(configured_exe)
    path = Path(path)
    pages = []
    for img in page_images(path):
        scale = 72.0 / OCR_DPI if path.suffix.lower() == ".pdf" else 1.0
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        rows: dict[int, list] = {}
        for i, word in enumerate(data["text"]):
            word = (word or "").strip()
            try:
                conf = float(data["conf"][i])
            except (TypeError, ValueError):
                conf = -1
            if not word or conf < MIN_CONF:
                continue
            x0 = float(data["left"][i]) * scale
            x1 = x0 + float(data["width"][i]) * scale
            top = float(data["top"][i]) * scale
            rows.setdefault(round(top / 3.0), []).append((x0, x1, word))
        lines = [sorted(rows[k], key=lambda w: w[0]) for k in sorted(rows)]
        pages.append({"lines": lines, "width": float(img.width) * scale, "ruled": []})
    if not any(p["lines"] for p in pages):
        raise OcrUnavailable("OCR could not find any text on this scan. Try a clearer or higher-resolution copy.")
    log.info("OCR read %d page(s)", len(pages))
    return pages
