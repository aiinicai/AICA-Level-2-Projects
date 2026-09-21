"""Local page OCR. PDFium is bundled by pip; Poppler is not required."""
import os
from pathlib import Path
import shutil
import pypdfium2 as pdfium
import pytesseract
from utils.validators import AppError


def find_tesseract() -> str | None:
    """Find an explicit configuration, PATH entry, or common Windows install."""
    configured = os.getenv("TESSERACT_CMD", "").strip()
    if configured:
        return configured if Path(configured).is_file() else None
    executable = shutil.which("tesseract")
    if executable:
        return executable
    if os.name == "nt":
        for root in (os.getenv("ProgramFiles"), os.getenv("LOCALAPPDATA")):
            if root:
                candidate = Path(root) / "Tesseract-OCR" / "tesseract.exe"
                if candidate.is_file():
                    return str(candidate)
    return None


def ocr_page(data: bytes, page_index: int) -> str:
    """Render a single page in memory and OCR it, cleaning all resources."""
    executable = find_tesseract()
    if executable:
        pytesseract.pytesseract.tesseract_cmd = executable
    try:
        with pdfium.PdfDocument(data) as pdf:
            page = pdf[page_index]
            try:
                width, height = page.get_size()
                if width <= 0 or height <= 0 or width * height > 4_000_000:
                    raise AppError("This PDF has unusually large pages. Re-export it at standard page size.")
                scale = min(3.0, (20_000_000 / (width * height)) ** 0.5)
                bitmap = page.render(scale=scale)
                try:
                    image = bitmap.to_pil()
                    try:
                        return pytesseract.image_to_string(
                            image, lang=os.getenv("OCR_LANGUAGE", "eng"), timeout=60
                        )
                    finally:
                        image.close()
                finally:
                    bitmap.close()
            finally:
                page.close()
    except pytesseract.TesseractNotFoundError:
        raise AppError("This notice needs scanned-text reading. Install Tesseract and set TESSERACT_CMD as described in README.md, then retry.") from None
    except AppError:
        raise
    except Exception:
        raise AppError(f"We could not reliably read scanned page {page_index + 1}. Try a clearer scan and check the installed reading language.") from None
